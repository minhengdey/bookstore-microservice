"""
inference_utils.py
═════════════════════════════════════════════════════════════════════════════
Load trained model + encoders and make predictions on new user sequences.

Usage:
    from inference_utils import UserBehaviorPredictor
    
    predictor = UserBehaviorPredictor(
        model_path="models/model_best.keras",
        encoder_path="models/encoders.pkl"
    )
    
    # Prepare a sequence of user events
    sequence = [
        {"action": "view", "category": "electronics", "device": "mobile", ...},
        {"action": "click", "category": "electronics", "device": "mobile", ...},
        ...
    ]
    
    pred = predictor.predict(sequence)
    print(pred)  # {"action": "purchase", "confidence": 0.85}
"""

import os
import pickle
import numpy as np
import pandas as pd
import tensorflow as tf
from typing import List, Dict, Tuple


@tf.keras.utils.register_keras_serializable(package="Custom", name="MultiHeadSelfAttention")
class MultiHeadSelfAttention(tf.keras.layers.Layer):
    """Custom attention layer used by the saved next-action model."""

    def __init__(self, d_model: int, num_heads: int, **kwargs):
        super().__init__(**kwargs)
        self.d_model = d_model
        self.num_heads = num_heads
        if d_model % num_heads != 0:
            raise ValueError("d_model must be divisible by num_heads")
        self.depth = d_model // num_heads
        self.Wq = tf.keras.layers.Dense(d_model, name="Wq")
        self.Wk = tf.keras.layers.Dense(d_model, name="Wk")
        self.Wv = tf.keras.layers.Dense(d_model, name="Wv")
        self.out = tf.keras.layers.Dense(d_model, name="out")

    def get_config(self):
        config = super().get_config()
        config.update({"d_model": self.d_model, "num_heads": self.num_heads})
        return config

    def build(self, input_shape):
        self.Wq.build(input_shape)
        self.Wk.build(input_shape)
        self.Wv.build(input_shape)
        self.out.build((*input_shape[:-1], self.d_model))
        super().build(input_shape)

    def split_heads(self, x):
        batch_size = tf.shape(x)[0]
        x = tf.reshape(x, (batch_size, -1, self.num_heads, self.depth))
        return tf.transpose(x, perm=[0, 2, 1, 3])

    def call(self, x):
        q = self.split_heads(self.Wq(x))
        k = self.split_heads(self.Wk(x))
        v = self.split_heads(self.Wv(x))

        dk = tf.cast(tf.shape(k)[-1], tf.float32)
        scores = tf.matmul(q, k, transpose_b=True) / tf.math.sqrt(dk)
        weights = tf.nn.softmax(scores, axis=-1)
        context = tf.matmul(weights, v)

        context = tf.transpose(context, perm=[0, 2, 1, 3])
        batch_size = tf.shape(context)[0]
        context = tf.reshape(context, (batch_size, -1, self.d_model))
        return self.out(context)


class UserBehaviorPredictor:
    """Load and use trained GRU/LSTM/BiLSTM model for next-action prediction."""
    
    def __init__(self, model_path: str, encoder_path: str):
        """
        Load model and encoders.
        
        Args:
            model_path: Path to model_best.keras
            encoder_path: Path to encoders.pkl
        """
        self.model = tf.keras.models.load_model(
            model_path,
            custom_objects={"MultiHeadSelfAttention": MultiHeadSelfAttention},
            compile=False,
        )
        with open(encoder_path, "rb") as f:
            self.enc_dict = pickle.load(f)
        
        self.encoders = {k: v for k, v in self.enc_dict.items() 
                        if hasattr(v, 'transform')}
        self.seq_len = self.enc_dict["SEQ_LEN"]
        self.n_feat = self.enc_dict["N_FEAT"]
        self.actions = self.enc_dict["ACTIONS"]
        
        print(f"✓ Model loaded: {model_path}")
        print(f"  Seq length: {self.seq_len} | Features: {self.n_feat}")
        print(f"  Classes: {list(self.actions)}")

    @staticmethod
    def _series(df: pd.DataFrame, column: str, default):
        if column in df.columns:
            return df[column]
        return pd.Series([default] * len(df), index=df.index)

    @staticmethod
    def _numeric_product_id(value) -> float:
        raw = str(value or "0").strip()
        if raw.upper().startswith("P") and raw[1:].isdigit():
            return float(int(raw[1:]))
        try:
            return float(raw)
        except ValueError:
            return 0.0
    
    def prepare_sequence(self, df_user: pd.DataFrame) -> np.ndarray:
        """
        Prepare a single user's sequence for prediction.
        
        Expected columns: action, category, device, product_id, price_tier,
                         hour, day_of_week, timestamp, session_id, purchase_count, goal (optional).
        
        Returns:
            X: shape (seq_len, n_feat) or None if insufficient data.
        """
        if "timestamp" not in df_user.columns and "event_time" in df_user.columns:
            df_user = df_user.rename(columns={"event_time": "timestamp"})

        if "timestamp" not in df_user.columns:
            df_user = df_user.copy()
            df_user["timestamp"] = pd.Timestamp.utcnow()

        df_user = df_user.sort_values("timestamp").reset_index(drop=True)
        df_user["timestamp"] = pd.to_datetime(df_user["timestamp"], errors="coerce")
        df_user = df_user.tail(self.seq_len).reset_index(drop=True)
        timestamp_fallback = pd.Timestamp.utcnow()
        timestamps = df_user["timestamp"].fillna(timestamp_fallback)
        
        # Encode categorical
        acts = np.array([
            self.encoders["action"].transform(["add_to_cart" if a == "cart_add" else a])[0]
            if ("add_to_cart" if a == "cart_add" else a) in self.encoders["action"].classes_ else 0
            for a in df_user["action"]
        ])
        cats = np.array([
            self.encoders["category"].transform([c])[0]
            if c in self.encoders["category"].classes_ else 0
            for c in self._series(df_user, "category", "books")
        ])
        devs = np.array([
            self.encoders["device"].transform([d])[0]
            if d in self.encoders["device"].classes_ else 0
            for d in self._series(df_user, "device", "desktop")
        ])
        prices = np.array([
            self.encoders["price_tier"].transform([p])[0]
            if p in self.encoders["price_tier"].classes_ else 0
            for p in self._series(df_user, "price_tier", "low")
        ])
        
        # Normalize continuous
        if "hour" in df_user.columns:
            hours_raw = pd.to_numeric(df_user["hour"], errors="coerce").fillna(0)
        else:
            hours_raw = timestamps.dt.hour
        if "day_of_week" in df_user.columns:
            dows_raw = pd.to_numeric(df_user["day_of_week"], errors="coerce").fillna(0)
        else:
            dows_raw = timestamps.dt.dayofweek
        hours = (hours_raw.to_numpy(dtype=np.float32) / 23.0).astype(np.float32)
        dows = (dows_raw.to_numpy(dtype=np.float32) / 6.0).astype(np.float32)
        
        # Product + Purchase normalization
        prods = self._series(df_user, "product_id", 0).map(self._numeric_product_id).to_numpy(dtype=np.float32)
        max_p = max(prods.max(), 1)
        prods = prods / max_p
        
        if "purchase_count" in df_user.columns:
            purchase_counts = pd.to_numeric(df_user["purchase_count"], errors="coerce").fillna(0).to_numpy(dtype=np.float32)
        else:
            purchase_counts = (df_user["action"].astype(str).str.lower() == "purchase").cumsum().to_numpy(dtype=np.float32)
        max_purchase = max(purchase_counts.max(), 1) + 1
        purchases = purchase_counts / max_purchase
        
        # Session step ratio
        if "session_id" not in df_user.columns:
            df_user = df_user.copy()
            df_user["session_id"] = "session-0"

        df_user["session_step"] = df_user.groupby("session_id").cumcount().values
        df_user["session_len"] = df_user.groupby("session_id")["session_id"].transform("count").values
        step_ratio = (df_user["session_step"] / df_user["session_len"].clip(lower=1)).values.astype(np.float32)
        
        # Goal (if available)
        has_goal = "goal" in self.enc_dict and self.enc_dict["goal"] is not None
        if has_goal and "goal" in df_user.columns:
            goals = np.array([self.encoders.get("goal", {}).transform([g])[0]
                             if "goal" in self.encoders and g in self.encoders["goal"].classes_ else 0
                             for g in df_user["goal"]])
            max_g = max(goals.max(), 1)
            goals = goals / max_g
        else:
            goals = np.zeros(len(df_user), dtype=np.float32)
        
        # Build feature matrix
        num_classes = len(self.actions)
        X = []
        for i in range(self.seq_len):
            if i >= len(df_user):
                X.append(np.zeros(self.n_feat, dtype=np.float32))
                continue

            oh = np.eye(num_classes)[acts[i]]
            extra = [
                cats[i] / max(len(self.encoders["category"].classes_) - 1, 1),
                devs[i] / max(len(self.encoders["device"].classes_) - 1, 1),
                prices[i] / max(len(self.encoders["price_tier"].classes_) - 1, 1),
                hours[i],
                dows[i],
                prods[i],
                i / (self.seq_len - 1),  # recency
                purchases[i],
                step_ratio[i],
            ]
            if has_goal:
                extra.append(goals[i])
            X.append(np.concatenate([oh, extra]))
        
        return np.array(X, dtype=np.float32)
    
    def predict(self, df_user: pd.DataFrame) -> Dict:
        """
        Predict next action for a user.
        
        Args:
            df_user: DataFrame with user's event history.
        
        Returns:
            {
                "action": predicted action name,
                "confidence": float [0, 1],
                "probs": dict of all action → probability
            }
        """
        X = self.prepare_sequence(df_user)
        if X is None:
            return None
        
        # Add batch dimension
        X = np.expand_dims(X, 0)  # (1, seq_len, n_feat)
        
        # Predict
        logits = self.model.predict(X, verbose=0)  # (1, num_classes)
        probs = logits[0]
        pred_idx = np.argmax(probs)
        pred_action = self.actions[pred_idx]
        confidence = probs[pred_idx]
        
        return {
            "action": pred_action,
            "confidence": float(confidence),
            "probs": {self.actions[i]: float(probs[i]) for i in range(len(self.actions))}
        }
    
    def predict_batch(self, df: pd.DataFrame, user_id_col: str = "user_id") -> List[Dict]:
        """
        Predict for multiple users.
        
        Args:
            df: DataFrame with events from multiple users.
            user_id_col: Column name for user ID.
        
        Returns:
            List of prediction dicts, one per user.
        """
        results = []
        for uid, grp in df.groupby(user_id_col):
            pred = self.predict(grp)
            if pred is not None:
                pred["user_id"] = uid
                results.append(pred)
        return results


# ─────────────────────────────────────────────────────────────────────────────
# Example usage
if __name__ == "__main__":
    # Test: load a sample and predict
    import sys
    
    # Assume model is in current dir or you pass paths
    model_path = "models/model_best.keras"
    encoder_path = "models/encoders.pkl"
    
    if not os.path.exists(model_path) or not os.path.exists(encoder_path):
        print("❌ Model or encoders not found. Train first with train_models_v5.py")
        sys.exit(1)
    
    print("\n" + "="*70)
    print("UserBehaviorPredictor — Demo")
    print("="*70 + "\n")
    
    predictor = UserBehaviorPredictor(model_path, encoder_path)
    
    # Create dummy sequence for testing
    # (In real use, load from your database/CSV)
    try:
        df = pd.read_csv("data_user500.csv")
        print(f"Loaded {len(df):,} events from data_user500.csv\n")
        
        # Pick first user
        uid = df["user_id"].iloc[0]
        df_user = df[df["user_id"] == uid].copy()
        print(f"User {uid}: {len(df_user)} events")
        
        pred = predictor.predict(df_user)
        if pred:
            print(f"\n→ Next action: {pred['action']}")
            print(f"  Confidence: {pred['confidence']:.2%}")
            print(f"\n  All probabilities:")
            for action, prob in sorted(pred["probs"].items(), 
                                       key=lambda x: x[1], reverse=True):
                print(f"    {action:15} {prob:6.2%}")
    except FileNotFoundError:
        print("⚠ data_user500.csv not found. Skipping demo.")
        print("\nTo use in your project:")
        print("  1. Copy this file to your project")
        print("  2. Copy models/model_best.keras and models/encoders.pkl")
        print("  3. from inference_utils import UserBehaviorPredictor")
        print("  4. predictor = UserBehaviorPredictor(model_path, encoder_path)")
        print("  5. pred = predictor.predict(your_user_df)")
