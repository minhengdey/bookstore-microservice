"""
train_models_v2.py - Premium High-End Visualizations (Radar Chart, Neon Dark Style).
"""
import os, warnings, pickle, time
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import (classification_report, confusion_matrix, accuracy_score, f1_score, precision_score, recall_score)
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import (SimpleRNN, LSTM, Bidirectional, Dense, Dropout, BatchNormalization)
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau
from tensorflow.keras.utils import to_categorical

# ── Colors & Styling ──────────────────────────────────────────────────────────
DARK   = "#05060a"; SURF = "#0f1118"; BORD = "#1f2230"; TEXT = "#e0e6ed"; MUTED = "#6b7280"
ACC1   = "#00f2ff"; ACC2 = "#ff007f"; ACC3 = "#7000ff"; ACC4 = "#00ff9f"
COLS   = {"RNN": ACC1, "LSTM": ACC2, "BiLSTM": ACC3}

def style_glass(ax):
    ax.set_facecolor(SURF)
    ax.tick_params(colors=TEXT, labelsize=9)
    for sp in ax.spines.values(): sp.set_edgecolor(BORD)
    ax.xaxis.label.set_color(MUTED); ax.yaxis.label.set_color(MUTED); ax.title.set_color(TEXT)
    ax.grid(color=BORD, linestyle='--', alpha=0.3)

# ── Load & Prepare ────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
data_path = os.path.join(BASE_DIR, "data", "data_user500.csv")
df = pd.read_csv(data_path)
print(f"[OK] Loading data: {len(df)} records")

enc = {}
for col in ["action","category","device"]:
    le = LabelEncoder()
    df[f"{col}_code"] = le.fit_transform(df[col])
    enc[col] = le

NUM_CLASSES = df["action_code"].nunique()
ACTIONS     = enc["action"].classes_
SEQ_LEN = 6

def make_sequences(df, seq_len):
    X, y = [], []
    for uid, grp in df.sort_values("timestamp").groupby("user_id"):
        acts, cats, devs = grp["action_code"].values, grp["category_code"].values, grp["device_code"].values
        if len(acts) <= seq_len: continue
        for i in range(len(acts) - seq_len):
            seq = [np.concatenate([np.eye(NUM_CLASSES)[acts[i+t]], [cats[i+t]/max(1,NUM_CLASSES-1), devs[i+t]/2]]) for t in range(seq_len)]
            X.append(seq); y.append(acts[i+seq_len])
    return np.array(X, dtype=np.float32), np.array(y)

X, y = make_sequences(df, SEQ_LEN)
y_cat = to_categorical(y, NUM_CLASSES)
X_tr, X_te, y_tr, y_te = train_test_split(X, y_cat, test_size=0.2, random_state=42, stratify=y)
y_te_lbl = np.argmax(y_te, axis=1)

# ── Training ──────────────────────────────────────────────────────────────────
def build_m(type):
    if type == "RNN": layers = [SimpleRNN(128, input_shape=(SEQ_LEN, X.shape[2]), return_sequences=True), BatchNormalization(), Dropout(0.2), SimpleRNN(64)]
    elif type == "LSTM": layers = [LSTM(128, input_shape=(SEQ_LEN, X.shape[2]), return_sequences=True), BatchNormalization(), Dropout(0.2), LSTM(64)]
    else: layers = [Bidirectional(LSTM(128, return_sequences=True), input_shape=(SEQ_LEN, X.shape[2])), BatchNormalization(), Dropout(0.2), Bidirectional(LSTM(64))]
    m = Sequential(layers + [Dense(64, activation="relu"), Dropout(0.2), Dense(NUM_CLASSES, activation="softmax")], name=type)
    m.compile(optimizer=tf.keras.optimizers.Adam(3e-4), loss="categorical_crossentropy", metrics=["accuracy"])
    return m

results = {}
for name in ["RNN","LSTM","BiLSTM"]:
    print(f"  > Training {name}...")
    m = build_m(name)
    start = time.time()
    h = m.fit(X_tr, y_tr, epochs=30, batch_size=128, validation_split=0.15, verbose=0, callbacks=[EarlyStopping(patience=5)])
    t_time = time.time() - start
    preds = np.argmax(m.predict(X_te, verbose=0), axis=1)
    results[name] = {
        "model":m, "history":h.history, "preds":preds,
        "acc":accuracy_score(y_te_lbl, preds),
        "f1": f1_score(y_te_lbl, preds, average="macro", zero_division=0),
        "pre": precision_score(y_te_lbl, preds, average="macro", zero_division=0),
        "rec": recall_score(y_te_lbl, preds, average="macro", zero_division=0),
        "time": t_time
    }
    print(f"  > {name} Acc={results[name]['acc']:.4f} | Time={t_time:.1f}s")

best_name = max(results, key=lambda n: results[n]["acc"])
print(f"[OK] Best Model: {best_name}")

# ── Visualization ────────────────────────────────────────────────────────────
plots_dir = os.path.join(BASE_DIR, "plots")
os.makedirs(plots_dir, exist_ok=True)

# 1. Advanced Training Curves
fig, axes = plt.subplots(1, 3, figsize=(18, 6), facecolor=DARK)
for i, (name, res) in enumerate(results.items()):
    ax = axes[i]; style_glass(ax); h = res["history"]; c = COLS[name]
    ax.plot(h["accuracy"], color=c, lw=2.5, label="Training")
    ax.plot(h["val_accuracy"], color=c, lw=2, ls="--", alpha=0.5, label="Validation")
    ax.fill_between(range(len(h["accuracy"])), h["accuracy"], h["val_accuracy"], color=c, alpha=0.05)
    ax.set_title(f"{name} Stability", fontsize=13, fontweight='bold', pad=15)
    ax.legend(facecolor=BORD, edgecolor=BORD, labelcolor=TEXT)
plt.tight_layout(); plt.savefig(os.path.join(plots_dir, "training_curves.png"), facecolor=DARK, dpi=140); plt.close()

# 2. Radar Chart
labels = np.array(['Accuracy', 'F1-Score', 'Precision', 'Recall', 'Efficiency'])
num_vars = len(labels)
angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
angles += angles[:1]
fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True), facecolor=DARK)
ax.set_facecolor(SURF)
for name, res in results.items():
    values = [res["acc"], res["f1"], res["pre"], res["rec"], 1 - (min(res["time"], 60)/120)]
    values += values[:1]
    ax.plot(angles, values, color=COLS[name], linewidth=2, label=name)
    ax.fill(angles, values, color=COLS[name], alpha=0.12)
ax.set_xticks(angles[:-1]); ax.set_xticklabels(labels, color=TEXT, size=11, fontweight='bold')
ax.set_yticklabels([]); ax.spines['polar'].set_color(BORD); ax.grid(color=BORD, alpha=0.4)
plt.title("Model DNA Comparison", color=ACC1, size=16, fontweight='bold', pad=25)
plt.legend(loc='lower right', facecolor=BORD, labelcolor=TEXT)
plt.savefig(os.path.join(plots_dir, "model_comparison.png"), facecolor=DARK, dpi=140); plt.close()

# 3. Confusion Matrix
cm = confusion_matrix(y_te_lbl, results[best_name]["preds"])
plt.figure(figsize=(10, 9), facecolor=DARK)
sns.heatmap(cm/np.sum(cm)*100, annot=True, fmt=".1f", cmap="magma", xticklabels=ACTIONS, yticklabels=ACTIONS, cbar=False)
plt.title(f"Confusion Matrix Spectrum ({best_name})", color=TEXT, size=15, pad=20)
plt.tight_layout(); plt.savefig(os.path.join(plots_dir, "confusion_matrix_best.png"), facecolor=DARK, dpi=140); plt.close()

# 4. F1 per Class
f1s = f1_score(y_te_lbl, results[best_name]["preds"], average=None, zero_division=0)
fig, ax = plt.subplots(figsize=(12, 5), facecolor=DARK); style_glass(ax)
ax.bar(ACTIONS, f1s, color=plt.cm.plasma(f1s), edgecolor=ACC1, linewidth=1, alpha=0.8)
ax.set_title(f"F1-Score Distribution — {best_name}", color=TEXT, size=14, weight='bold')
ax.set_ylim(0, 1.1); plt.xticks(rotation=20); plt.tight_layout()
plt.savefig(os.path.join(plots_dir, "f1_per_class.png"), facecolor=DARK, dpi=140); plt.close()

# 5. NEW: Performance Multi-Grid
metrics = ['acc', 'f1', 'pre', 'rec']
m_labels = ['Accuracy', 'F1-Score', 'Precision', 'Recall']
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 6), facecolor=DARK)
x_axis = np.arange(len(m_labels)); width = 0.22
for i, name in enumerate(results.keys()):
    vals = [results[name][m] for m in metrics]
    ax1.bar(x_axis + i*width, vals, width, color=COLS[name], label=name, edgecolor=BORD, alpha=0.85)
style_glass(ax1); ax1.set_xticks(x_axis + width); ax1.set_xticklabels(m_labels, weight='bold')
ax1.set_title("Holistic Performance Comparison", color=ACC1, size=14, weight='bold'); ax1.legend()
for name in results.keys():
    ax2.scatter(results[name]['time'], results[name]['acc'], color=COLS[name], s=250, label=name, edgecolors=TEXT, lw=1.2)
    ax2.text(results[name]['time'] + 0.5, results[name]['acc'], name, color=TEXT, size=9, weight='bold')
style_glass(ax2); ax2.set_xlabel("Training Duration (s)"); ax2.set_ylabel("Accuracy (%)")
ax2.set_title("Architecture Efficiency (Speed vs Accuracy)", color=ACC4, size=14, weight='bold')
plt.tight_layout(); plt.savefig(os.path.join(plots_dir, "model_performance_summary.png"), facecolor=DARK, dpi=140); plt.close()

results[best_name]["model"].save(os.path.join(BASE_DIR, "models", "model_best.keras"))
with open(os.path.join(BASE_DIR, "models", "encoders.pkl"),"wb") as f:
    enc.update({"SEQ_LEN":SEQ_LEN, "N_FEAT":X.shape[2], "ACTIONS":list(ACTIONS)})
    pickle.dump(enc, f)
print(f"[OK] Visualizations generated in {plots_dir}")