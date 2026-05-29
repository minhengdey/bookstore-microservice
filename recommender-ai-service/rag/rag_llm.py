"""
rag_llm.py — Groq API + KB_Graph context.
"""
import os, json, pickle, textwrap
import urllib.request, urllib.error
import pandas as pd
import networkx as nx
import requests
from dotenv import load_dotenv
from rag.retriever import RAGSystem
from app.services.recommender_service import RecommenderService

# Load .env from ROOT
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE, ".env"))
# Also try one level up for project root
load_dotenv(os.path.join(os.path.dirname(BASE), ".env"))

def _load():
    data_path = os.path.join(BASE, "data", "data_user500.csv")
    df = pd.read_csv(data_path)
    
    rag_pkl_path = os.path.join(BASE, "rag", "rag_system.pkl")
    try:
        with open(rag_pkl_path, "rb") as f:
            rag = pickle.load(f)
        print("[rag_llm] Loaded RAG system from pickle.")
    except Exception as e:
        print(f"[rag_llm] Failed to load pickle ({e}). Rebuilding RAG system from CSV...")
        # Fallback: Rebuild Graph and RAGSystem
        G = nx.MultiDiGraph()
        # Add Product nodes
        for _, row in df[["product_id","product_name","category"]].drop_duplicates("product_id").iterrows():
            G.add_node(row["product_id"], label="Product", name=row["product_name"], category=row["category"])
        # Add User nodes
        for uid in df["user_id"].unique(): G.add_node(uid, label="User")
        # Add Category nodes
        for cat in df["category"].unique(): G.add_node(cat, label="Category")
        # Add Edges
        for _, row in df.iterrows():
            G.add_edge(row["user_id"], row["product_id"], relation="PERFORMED", action=row["action"], timestamp=row.get("timestamp"))
            G.add_edge(row["product_id"], row["category"], relation="BELONGS_TO")
        
        rag = RAGSystem(G, df)
        print("[rag_llm] RAG system rebuilt successfully.")
    
    return df, rag

_df, _rag = _load()

GROQ_API_URL = os.getenv("GROQ_API_URL", "https://api.groq.com/openai/v1/chat/completions")
GROQ_MODEL   = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
GROQ_API_KEY = os.getenv("GROQ_API_KEY") # No default for security
PRODUCT_SERVICE_URL = os.getenv("PRODUCT_SERVICE_URL", "http://product-service:8000")

def call_groq(system_prompt: str, user_message: str, max_tokens: int = 512) -> str:
    payload = json.dumps({
        "model": GROQ_MODEL,
        "max_tokens": max_tokens,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ],
    }).encode("utf-8")
    headers = {
        "Content-Type": "application/json", 
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    req = urllib.request.Request(GROQ_API_URL, data=payload, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"].strip()
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace")
        print(f"[Groq API Error {e.code}]: {error_body}")
        return None
    except Exception as e:
        print(f"[Groq Connection Error]: {e}")
        return None

class RAGChatLLM:
    def __init__(self, rag, df):
        self.rag = rag
        self.df  = df
        self.recommender = RecommenderService()

    def chat(self, user_id: str, message: str, history: list = None, recent_behaviors: list = None) -> dict:
        customer_id = self._to_customer_id(user_id)
        if customer_id is not None:
            # Use the same recommendation pipeline as /recommendations/<customer_id>/.
            v_history = []
            rec_payload = self.recommender.recommend_with_prediction(customer_id, limit=5)
            rec_ids = rec_payload.get("recommended_product_ids", [])
            next_action_prediction = rec_payload.get("next_action_prediction")
        else:
            # Legacy fallback for seeded RAG users like U001..U500.
            v_history = self.rag.retrieve_user_history(user_id, top_k=5)
            recs = self.rag.recommend_products(user_id)
            rec_items = recs.get("recommendations", []) if isinstance(recs, dict) else []
            rec_ids = [
                item.get("product_id")
                for item in rec_items
                if isinstance(item, dict) and item.get("product_id") is not None
            ]
            next_action_prediction = None
        live_products = self._fetch_live_products(rec_ids)
        
        # Build behavior context
        behavior_txt = ""
        if recent_behaviors:
            behavior_txt = f"\nRecent user behaviors: {recent_behaviors}"
        
        context_text = (
            f"User Profile: {user_id}\n"
            f"Purchase/View History: {v_history}\n"
            f"Recommended (live catalog): {live_products}"
            f"\nNext action prediction: {next_action_prediction}"
            f"{behavior_txt}"
        )
        
        system_prompt = textwrap.dedent("""
            Bạn là 'Mochi', trợ lý tư vấn mua sắm thân thiện của hệ thống thương mại điện tử.
            Phong cách của bạn:
            - Trả lời tự nhiên, ngắn gọn, dễ hiểu, thân thiện.
            - Có thể dùng icon vừa phải (ví dụ: ✨, 🛍️, 💡) để tạo cảm giác gần gũi, nhưng không lạm dụng.
            - Gọi người dùng là 'bạn' hoặc 'khách hàng'.
            - Ưu tiên tư vấn sản phẩm, so sánh lựa chọn, gợi ý theo nhu cầu/giá/phân khúc.
            - Nếu thấy người dùng vừa xem hoặc thêm sản phẩm vào giỏ (recent behaviors), hãy tận dụng thông tin đó để cá nhân hóa tư vấn.
            - Không giới hạn theo sách; hỗ trợ mọi danh mục sản phẩm có trong hệ thống.
            - Trả lời bằng tiếng Việt.
        """).strip()

        full_message = f"Context: {context_text}\nUser message: {message}"

        answer = call_groq(system_prompt, full_message)
        if not answer:
            answer = "Mochi đang gặp trục trặc kết nối tạm thời. Bạn thử lại sau ít giây nhé, hoặc xem các sản phẩm gợi ý bên dưới nha! ✨"

        return {
            "user_id": user_id, 
            "answer": answer,
            "products": live_products[:5],
            "context_used": context_text,
            "next_action_prediction": next_action_prediction,
        }

    def _to_customer_id(self, user_id) -> int | None:
        if user_id is None:
            return None
        raw = str(user_id).strip()
        if not raw:
            return None
        if raw.isdigit():
            return int(raw)
        return None

    def _fetch_live_products(self, product_ids: list) -> list:
        products = []
        seen = set()
        for pid in product_ids:
            try:
                pid_int = int(pid)
            except (TypeError, ValueError):
                continue
            if pid_int in seen:
                continue
            seen.add(pid_int)
            try:
                r = requests.get(f"{PRODUCT_SERVICE_URL}/products/{pid_int}/", timeout=4)
                if r.status_code != 200:
                    continue
                data = r.json()
                if not isinstance(data, dict) or data.get("id") is None:
                    continue
                products.append({
                    "product_id": int(data.get("id")),
                    "name": data.get("name", ""),
                    "sku": data.get("sku", ""),
                    "price": data.get("price", 0),
                    "category_id": data.get("category_id"),
                })
            except requests.exceptions.RequestException:
                continue
        return products

_rag_llm = None
def get_rag_llm():
    global _rag_llm
    if _rag_llm is None: _rag_llm = RAGChatLLM(_rag, _df)
    return _rag_llm

if __name__ == "__main__":
    llm = get_rag_llm()
    # Avoid printing non-ASCII in CLI demo on Windows
    print("Testing RAG Chat...")
    res = llm.chat("U001", "Hello")
    print("Success")
