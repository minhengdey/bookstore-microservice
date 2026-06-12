"""
rag_llm.py — Groq API + KB_Graph context.
"""
import os, json, pickle, textwrap, re
import urllib.request, urllib.error
import pandas as pd
import networkx as nx
import requests
from dotenv import load_dotenv
from rag.retriever import RAGSystem
from rag.hybrid_retriever import get_hybrid_retriever, DEFAULT_TOP_K
from rag.intent_router import ChatIntent, classify_intent, build_retrieval_query
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
        
        try:
            with open(rag_pkl_path, "wb") as f:
                pickle.dump(rag, f)
            print("[rag_llm] Saved rebuilt RAG system to pickle.")
        except Exception as save_err:
            print(f"[rag_llm] Failed to save pickle: {save_err}")
    
    return df, rag

_df, _rag = _load()

GROQ_API_URL = os.getenv("GROQ_API_URL", "https://api.groq.com/openai/v1/chat/completions")
PRODUCT_SERVICE_URL = os.getenv("PRODUCT_SERVICE_URL", "http://product-service:8000")

def _groq_config():
    return os.getenv("GROQ_API_KEY", "").strip(), os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

def call_groq(
    system_prompt: str,
    user_message: str,
    history: list = None,
    max_tokens: int = 512,
) -> str:
    api_key, model = _groq_config()
    if not api_key:
        print("[Groq] GROQ_API_KEY is not set — skipping LLM call.")
        return None

    messages = [{"role": "system", "content": system_prompt}]
    for item in (history or [])[-10:]:
        role, content = None, None
        if isinstance(item, (list, tuple)) and len(item) >= 2:
            role = "user" if item[0] == "user" else "assistant"
            content = str(item[1] or "").strip()
        elif isinstance(item, dict):
            raw_role = str(item.get("role", "")).strip().lower()
            if raw_role in ("user", "assistant"):
                role = raw_role
                content = str(item.get("content", "")).strip()
        if role and content:
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": user_message})

    payload = json.dumps({
        "model": model,
        "max_tokens": max_tokens,
        "messages": messages,
    }).encode("utf-8")
    headers = {
        "Content-Type": "application/json", 
        "Authorization": f"Bearer {api_key}",
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
        self.hybrid = get_hybrid_retriever()

    def chat(self, user_id: str, message: str, history: list = None, recent_behaviors: list = None) -> dict:
        history = history or []
        intent = classify_intent(message, history)
        customer_id = self._to_customer_id(user_id)
        v_history = []
        rec_ids = []
        next_action_prediction = None
        retrieval_query = build_retrieval_query(message, history)

        hybrid_products, hybrid_score = self.hybrid.hybrid_search(
            retrieval_query, top_k=DEFAULT_TOP_K
        )
        keyword_products, keyword_score = self._search_catalog_with_score(
            retrieval_query, limit=DEFAULT_TOP_K, recent_behaviors=recent_behaviors
        )
        if hybrid_products:
            search_products = hybrid_products
            search_score = max(keyword_score, 1)
        elif keyword_products:
            search_products = keyword_products
            search_score = keyword_score
        else:
            search_products = []
            search_score = 0
        search_products = self._apply_price_filter(search_products, message)
        search_products = self._boost_viewed_products(search_products, recent_behaviors)
        search_products = self._align_with_history_context(search_products, history)

        cf_products = []
        if customer_id is not None:
            rec_payload = self.recommender.recommend_with_prediction(customer_id, limit=DEFAULT_TOP_K)
            rec_ids = rec_payload.get("recommended_product_ids", [])
            next_action_prediction = rec_payload.get("next_action_prediction")
            cf_products = self.hybrid.fetch_products_by_ids(rec_ids, limit=DEFAULT_TOP_K)
            if not cf_products:
                cf_products = self._fetch_live_products(rec_ids)
        elif not self._is_anonymous_user(user_id):
            v_history = self.rag.retrieve_user_history(user_id, top_k=5)
            recs = self.rag.recommend_products(user_id)
            rec_items = recs.get("recommendations", []) if isinstance(recs, dict) else []
            rec_ids = [
                item.get("product_id")
                for item in rec_items
                if isinstance(item, dict) and item.get("product_id") is not None
            ]
            cf_products = self.hybrid.fetch_products_by_ids(rec_ids, limit=DEFAULT_TOP_K)

        live_products = self._resolve_products_for_intent(
            intent=intent,
            message=message,
            history=history,
            search_products=search_products,
            search_score=search_score,
            cf_products=cf_products,
            user_id=user_id,
        )

        behavior_txt = ""
        if recent_behaviors:
            behavior_txt = f"\nrecent_behaviors: {recent_behaviors}"

        product_block = self._format_products_for_prompt(live_products)
        policy_block = self._policy_context() if intent == ChatIntent.POLICY else ""

        context_text = (
            f"intent: {intent.value}\n"
            f"customer_id: {user_id}\n"
            f"purchase_view_history: {v_history}\n"
            f"suggested_products:\n{product_block}\n"
            f"{policy_block}"
            f"next_action_prediction: {next_action_prediction}"
            f"{behavior_txt}"
        )

        system_prompt = self._build_system_prompt(intent)
        user_prompt = context_text
        if intent != ChatIntent.POLICY:
            user_prompt += f"\n\nCâu hỏi khách: {message}"
        else:
            user_prompt += f"\n\nKhách hỏi về chính sách: {message}"

        answer = call_groq(system_prompt, user_prompt, history=history)
        if not answer:
            answer = self._local_fallback_answer(message, live_products, user_id, intent)
        else:
            answer = self._postprocess_answer(answer, live_products, message)

        return {
            "user_id": user_id,
            "answer": answer,
            "products": live_products[:DEFAULT_TOP_K],
            "intent": intent.value,
            "context_used": context_text,
            "next_action_prediction": next_action_prediction,
        }

    def _build_system_prompt(self, intent: ChatIntent) -> str:
        base = textwrap.dedent("""
            Bạn là Mochi — nhân viên tư vấn mua sắm online thân thiện, nói chuyện tự nhiên như chat với bạn bè.
            Quy tắc bắt buộc:
            - Trả lời tiếng Việt, ấm áp, ngắn gọn (3–6 câu), xưng "mình" với khách.
            - Nhớ ngữ cảnh hội thoại trước đó; nếu khách hỏi tiếp ("còn gì rẻ hơn", "loại khác") hãy bám theo chủ đề đang nói.
            - TUYỆT ĐỐI KHÔNG nhắc: "hệ thống", "danh mục", "dữ liệu", "context", "AI", "Lưu ý:", hay thuật ngữ kỹ thuật nội bộ.
            - KHÔNG hỏi vòng vo — nếu đã có sản phẩm phù hợp thì gợi ý luôn.
            - CHỈ gợi ý sản phẩm có trong suggested_products; không bịa tên/thương hiệu.
            - Mỗi sản phẩm cụ thể BẮT BUỘC có link: [Tên](/products/ID/). Ví dụ đúng: [Son dưỡng ColorPop](/products/16/)
            - Dùng mô tả/giá/tồn kho trong suggested_products; không suy diễn quá xa.
            - Icon nhẹ (✨, 💄) tối đa 1–2 cái.
        """).strip()

        if intent == ChatIntent.POLICY:
            return base + "\n- Trả lời câu hỏi chính sách dựa policy_notes; không gợi ý sản phẩm trừ khi khách hỏi mua hàng."
        if intent == ChatIntent.COMPARE:
            return base + "\n- So sánh ngắn gọn 2–3 sản phẩm trong suggested_products (giá, điểm khác biệt từ mô tả)."
        if intent == ChatIntent.GREETING:
            return base + "\n- Chào hỏi thân thiện; nếu có suggested_products có thể gợi ý nhẹ 1–2 món."
        if intent == ChatIntent.GENERAL:
            return base + "\n- Trả lời tự nhiên; chỉ gợi ý sản phẩm khi thật sự phù hợp."
        return base

    def _policy_context(self) -> str:
        return textwrap.dedent("""
            policy_notes:
            - Đổi trả trong 7 ngày nếu sản phẩm lỗi hoặc không đúng mô tả.
            - Giao hàng toàn quốc; phí ship tính theo khu vực khi checkout.
            - Thanh toán: COD, chuyển khoản, ví điện tử (tùy cổng thanh toán).
            - Hỗ trợ theo dõi đơn tại trang Đơn hàng sau khi đăng nhập.
        """).strip() + "\n"

    def _resolve_products_for_intent(
        self,
        intent: ChatIntent,
        message: str,
        history: list,
        search_products: list,
        search_score: float,
        cf_products: list,
        user_id: str,
    ) -> list:
        if intent == ChatIntent.POLICY:
            return []

        if intent in (ChatIntent.SEARCH, ChatIntent.FOLLOW_UP, ChatIntent.COMPARE):
            if search_score > 0 and search_products:
                return search_products
            hist_ids = self._extract_product_ids_from_history(history)
            if hist_ids:
                from_hist = self.hybrid.fetch_products_by_ids(hist_ids, limit=DEFAULT_TOP_K)
                if from_hist:
                    return from_hist

        if intent == ChatIntent.RECOMMEND and cf_products:
            return cf_products

        if search_score > 0 and search_products:
            return search_products

        if cf_products:
            return cf_products

        if self._is_anonymous_user(user_id):
            return self._default_catalog_products(DEFAULT_TOP_K)
        return search_products or cf_products

    def _extract_product_ids_from_history(self, history: list) -> list:
        ids = []
        seen = set()
        for item in reversed(history or []):
            text = ""
            if isinstance(item, (list, tuple)) and len(item) >= 2:
                text = str(item[1])
            elif isinstance(item, dict):
                text = str(item.get("content", ""))
            for pid in re.findall(r"/products/(\d+)/", text):
                try:
                    n = int(pid)
                except ValueError:
                    continue
                if n not in seen:
                    seen.add(n)
                    ids.append(n)
        return ids

    def _apply_price_filter(self, products: list, message: str) -> list:
        if not products:
            return products
        msg = str(message or "").lower()
        ceiling = None
        floor = None

        m = re.search(r"dưới\s*(\d+(?:[.,]\d+)?)\s*(k|nghìn|ngàn|triệu|tr|đ)?", msg)
        if m:
            val = float(m.group(1).replace(",", "."))
            unit = (m.group(2) or "").lower()
            if unit in ("triệu", "tr"):
                val *= 1_000_000
            elif unit in ("k", "nghìn", "ngàn", ""):
                if val < 1000:
                    val *= 1000
            ceiling = val

        m = re.search(r"trên\s*(\d+(?:[.,]\d+)?)\s*(k|nghìn|ngàn|triệu|tr|đ)?", msg)
        if m:
            val = float(m.group(1).replace(",", "."))
            unit = (m.group(2) or "").lower()
            if unit in ("triệu", "tr"):
                val *= 1_000_000
            elif unit in ("k", "nghìn", "ngàn", ""):
                if val < 1000:
                    val *= 1000
            floor = val

        if ceiling is None and floor is None:
            return products

        filtered = []
        for p in products:
            try:
                price = float(p.get("effective_price") or p.get("price") or 0)
            except (TypeError, ValueError):
                continue
            if ceiling is not None and price > ceiling:
                continue
            if floor is not None and price < floor:
                continue
            filtered.append(p)
        return filtered or products

    def _align_with_history_context(self, products: list, history: list) -> list:
        """Giữ chủ đề hội thoại (vd: đang nói son dưỡng thì không nhảy sang yến mạch)."""
        if not products or not history:
            return products
        hist_ids = self._extract_product_ids_from_history(history)
        if not hist_ids:
            return products
        anchors = self.hybrid.fetch_products_by_ids(hist_ids[:2], limit=2)
        if not anchors:
            return products
        anchor_cats = {(a.get("category_name") or "").strip().lower() for a in anchors if a.get("category_name")}
        anchor_names = " ".join((a.get("name") or "") for a in anchors).lower()
        anchor_tokens = [t for t in re.split(r"\W+", anchor_names) if len(t) >= 3]

        scored = []
        for p in products:
            score = 0
            cat = (p.get("category_name") or "").strip().lower()
            name = (p.get("name") or "").lower()
            if cat and cat in anchor_cats:
                score += 5
            for t in anchor_tokens:
                if t in name:
                    score += 2
            if p.get("product_id") in hist_ids:
                score += 8
            scored.append((score, p))
        scored.sort(key=lambda row: -row[0])
        if scored and scored[0][0] > 0:
            return [p for s, p in scored if s > 0] or products
        return products

    def _boost_viewed_products(self, products: list, recent_behaviors: list) -> list:
        if not products or not recent_behaviors:
            return products
        viewed = set()
        for b in recent_behaviors:
            if isinstance(b, str) and b.startswith("view_product_"):
                try:
                    viewed.add(int(b.split("_")[-1]))
                except (TypeError, ValueError):
                    pass
        if not viewed:
            return products
        boosted = []
        rest = []
        for p in products:
            if p.get("product_id") in viewed:
                boosted.append(p)
            else:
                rest.append(p)
        return boosted + rest

    def _format_price_vnd(self, value) -> str:
        try:
            return f"{float(value):,.0f}₫".replace(",", ".")
        except (TypeError, ValueError):
            return str(value) if value else ""

    def _format_products_for_prompt(self, products: list) -> str:
        if not products:
            return "(chưa có sản phẩm phù hợp — hãy hỏi thêm nhu cầu của khách)"
        lines = []
        for p in products[:DEFAULT_TOP_K]:
            pid = p.get("product_id")
            name = (p.get("name") or "").strip()
            if not pid or not name:
                continue
            price = self._format_price_vnd(p.get("effective_price") or p.get("price"))
            sku = (p.get("sku") or "").strip()
            brand = (p.get("brand_name") or "").strip()
            category = (p.get("category_name") or "").strip()
            desc = (p.get("description") or "").strip()[:160]
            stock = p.get("stock")
            stock_txt = "còn hàng" if stock is None or int(stock or 0) > 0 else "hết hàng"
            meta_parts = [f"giá {price}"] if price else []
            if category:
                meta_parts.append(f"danh mục {category}")
            if brand:
                meta_parts.append(f"thương hiệu {brand}")
            if sku:
                meta_parts.append(f"SKU {sku}")
            meta_parts.append(stock_txt)
            if desc:
                meta_parts.append(f"mô tả: {desc}")
            lines.append(
                f"- id={pid} | {name} | {' | '.join(meta_parts)} | link: [{name}](/products/{pid}/)"
            )
        return "\n".join(lines) if lines else "(chưa có sản phẩm phù hợp)"

    def _product_links_markdown(self, products: list, limit: int = 4) -> str:
        links = []
        for p in products[:limit]:
            pid = p.get("product_id")
            name = (p.get("name") or "").strip()
            if pid and name:
                links.append(f"[{name}](/products/{pid}/)")
        return ", ".join(links)

    def _is_anonymous_user(self, user_id) -> bool:
        raw = str(user_id or "").strip().lower()
        return raw in ("", "anonymous", "null", "none", "guest")

    def _extract_search_terms(self, message: str) -> list:
        raw = str(message or "").lower()
        stop_words = {
            "tìm", "tim", "mua", "cần", "can", "cho", "tôi", "toi", "mình", "minh", "bạn", "ban",
            "em", "anh", "chị", "chi", "ạ", "nha", "nhé", "giúp", "giup", "muốn", "muon",
            "có", "co", "không", "khong", "gì", "gi", "đó", "do", "nào", "nao", "về", "ve",
            "loại", "loai", "sản", "san", "phẩm", "pham", "hàng", "hang", "xin", "chào", "chao",
            "hello", "hi", "help", "tư", "tu", "vấn", "van", "gợi", "goi", "ý", "y", "một", "mot",
            "vài", "vai", "some", "the", "and", "or", "là", "la", "của", "cua",
        }
        tokens = [t for t in re.split(r"[^\wàáảãạăắằẳẵặâấầẩẫậèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵđ]+", raw) if len(t) >= 2 and t not in stop_words]
        terms = []
        if tokens:
            terms.append(" ".join(tokens))
            for n in range(min(4, len(tokens)), 1, -1):
                for i in range(len(tokens) - n + 1):
                    phrase = " ".join(tokens[i : i + n])
                    if phrase not in terms:
                        terms.append(phrase)
            for token in tokens:
                if token not in terms:
                    terms.append(token)
        return terms[:10]

    def _fetch_product_items(self, search: str = None, page_size: int = 100) -> list:
        try:
            params = {"page_size": page_size}
            if search:
                params["search"] = search
            r = requests.get(
                f"{PRODUCT_SERVICE_URL.rstrip('/')}/products/",
                params=params,
                timeout=6,
            )
            if r.status_code != 200:
                return []
            data = r.json()
            items = data.get("results", data) if isinstance(data, dict) else data
            return items if isinstance(items, list) else []
        except requests.exceptions.RequestException:
            return []

    def _score_product_item(self, raw: dict, message: str, viewed_ids: set) -> int:
        terms = self._extract_search_terms(message)
        msg_tokens = [t for phrase in terms for t in phrase.split() if len(t) >= 2]
        if not msg_tokens:
            msg_tokens = [t for t in str(message or "").lower().split() if len(t) >= 2]

        name = str(raw.get("name") or "").lower()
        description = str(raw.get("description") or "").lower()
        category = raw.get("category") or {}
        category_name = str(category.get("name") if isinstance(category, dict) else "").lower()
        sku = str(raw.get("sku") or "").lower()

        score = 0
        for phrase in terms:
            phrase = phrase.strip()
            if len(phrase) >= 3 and phrase in name:
                score += 12
            if len(phrase) >= 3 and phrase in description:
                score += 4
        for token in msg_tokens:
            if token in name:
                score += 3
            if token in category_name:
                score += 2
            if token in description:
                score += 1
            if token in sku:
                score += 1

        try:
            pid = int(raw["id"])
            if pid in viewed_ids:
                score += 5
        except (TypeError, ValueError, KeyError):
            pass
        return score

    def _rank_product_items(self, items: list, message: str, recent_behaviors: list = None, limit: int = 5) -> tuple[list, int]:
        if not items:
            return [], 0

        viewed_ids = set()
        if recent_behaviors:
            for behavior in recent_behaviors:
                if not isinstance(behavior, str):
                    continue
                if behavior.startswith("view_product_"):
                    try:
                        viewed_ids.add(int(behavior.split("_")[-1]))
                    except (TypeError, ValueError):
                        continue

        ranked = []
        for raw in items:
            if not isinstance(raw, dict) or raw.get("id") is None:
                continue
            score = self._score_product_item(raw, message, viewed_ids)
            ranked.append((score, int(raw["id"]), raw))

        ranked.sort(key=lambda row: (-row[0], row[1]))
        max_score = ranked[0][0] if ranked else 0
        positive = [row for row in ranked if row[0] > 0]
        chosen = positive if positive else ([] if len(items) > 20 else ranked)

        products = []
        for _, _, raw in chosen[:limit]:
            category = raw.get("category") or {}
            brand = raw.get("brand") or {}
            products.append({
                "product_id": int(raw.get("id")),
                "name": raw.get("name", ""),
                "sku": raw.get("sku", ""),
                "price": raw.get("price", 0),
                "effective_price": raw.get("effective_price", raw.get("price", 0)),
                "description": raw.get("description", ""),
                "stock": raw.get("stock", 0),
                "category_id": raw.get("category_id") or (category.get("id") if isinstance(category, dict) else None),
                "category_name": category.get("name", "") if isinstance(category, dict) else "",
                "brand_name": brand.get("name", "") if isinstance(brand, dict) else "",
            })
        return products, max_score

    def _search_catalog_with_score(self, message: str, limit: int = 5, recent_behaviors: list = None) -> tuple[list, int]:
        try:
            items = []
            matched_term = None
            for term in self._extract_search_terms(message):
                items = self._fetch_product_items(search=term)
                if items:
                    matched_term = term
                    break
            if not items:
                return [], 0

            products, max_score = self._rank_product_items(items, message, recent_behaviors, limit)
            if products and max_score > 0:
                return products, max_score
            if matched_term and len(items) <= 20:
                return products, max_score
            return [], 0
        except Exception as exc:
            print(f"[rag_llm] catalog search failed: {exc}")
            return [], 0

    def _search_catalog(self, message: str, limit: int = 5, recent_behaviors: list = None) -> list:
        products, score = self._search_catalog_with_score(message, limit, recent_behaviors)
        if products:
            return products
        return self._default_catalog_products(limit) if score == 0 else []

    def _postprocess_answer(self, answer: str, products: list, message: str) -> str:
        text = str(answer or "").strip()
        if not text:
            return text

        text = re.sub(r"(?is)\s*lưu ý\s*:.*$", "", text).strip()
        text = re.sub(r"(?is)dựa trên (danh mục|hệ thống|sản phẩm có sẵn).*?$", "", text).strip()
        text = re.sub(r"(?is)bạn có muốn (tôi|mình).*?$", "", text).strip()
        text = re.sub(r"(?is)\s*bạn cần gì thêm\??\s*$", "", text).strip()
        text = re.sub(
            r"\[/products/(\d+)/\]\(([^)]+)\)",
            r"[\2](/products/\1/)",
            text,
        )

        valid_ids = {int(p["product_id"]) for p in products if p.get("product_id") is not None}
        mentioned_ids = {int(m) for m in re.findall(r"/products/(\d+)/", text)}
        if valid_ids and mentioned_ids and not mentioned_ids.issubset(valid_ids):
            for bad_id in mentioned_ids - valid_ids:
                text = re.sub(rf"\[([^\]]+)\]\(/products/{bad_id}/\)", r"\1", text)
                text = re.sub(rf"/products/{bad_id}/", "", text)

        if valid_ids:
            kept_lines = []
            for line in text.split("\n"):
                stripped = line.strip()
                if re.match(r"^[-*•]", stripped) and not re.search(r"/products/\d+/", stripped):
                    continue
                kept_lines.append(line)
            text = "\n".join(kept_lines).strip()

        if products and not re.search(r"\(/products/\d+/\)", text):
            if "Mình gợi ý" in text or "gợi ý vài món" in text:
                text = re.sub(r"(?is)\n*Mình gợi ý vài món này cho bạn nha:.*$", "", text).strip()
            lines = ["", "Mình gợi ý mấy món này nha:"]
            for p in products[:4]:
                pid = p.get("product_id")
                name = (p.get("name") or "").strip()
                price = self._format_price_vnd(p.get("price"))
                if pid and name:
                    price_part = f" — {price}" if price else ""
                    lines.append(f"• [{name}](/products/{pid}/){price_part}")
            text = text.rstrip() + "\n".join(lines)

        return text.strip()

    def _default_catalog_products(self, limit: int = 5) -> list:
        try:
            r = requests.get(
                f"{PRODUCT_SERVICE_URL.rstrip('/')}/products/",
                params={"page_size": max(limit, 8), "sort_by": "newest"},
                timeout=6,
            )
            if r.status_code != 200:
                return []
            data = r.json()
            items = data.get("results", data) if isinstance(data, dict) else data
            if not isinstance(items, list):
                return []
            products = []
            for raw in items[:limit]:
                if not isinstance(raw, dict) or raw.get("id") is None:
                    continue
                category = raw.get("category") or {}
                brand = raw.get("brand") or {}
                products.append({
                    "product_id": int(raw.get("id")),
                    "name": raw.get("name", ""),
                    "sku": raw.get("sku", ""),
                    "price": raw.get("price", 0),
                    "effective_price": raw.get("effective_price", raw.get("price", 0)),
                    "description": raw.get("description", ""),
                    "stock": raw.get("stock", 0),
                    "category_id": raw.get("category_id") or (category.get("id") if isinstance(category, dict) else None),
                    "category_name": category.get("name", "") if isinstance(category, dict) else "",
                    "brand_name": brand.get("name", "") if isinstance(brand, dict) else "",
                })
            return products
        except requests.exceptions.RequestException:
            return []

    def _local_fallback_answer(self, message: str, products: list, user_id: str, intent: ChatIntent = None) -> str:
        if intent == ChatIntent.POLICY:
            return (
                "Mình tóm tắt nhanh nha: đổi trả trong 7 ngày nếu lỗi/sai mô tả, "
                "giao toàn quốc, thanh toán COD hoặc online. Chi tiết xem ở trang Đơn hàng sau khi đặt nha! ✨"
            )
        msg = str(message or "").strip().lower()
        product_links = self._product_links_markdown(products, limit=4)
        login_hint = (
            " Đăng nhập để mình gợi ý chuẩn hơn theo gu của bạn nha!"
            if self._is_anonymous_user(user_id)
            else ""
        )

        if any(kw in msg for kw in ("xin chào", "hello", "hi", "chào")):
            if product_links:
                return (
                    f"Chào bạn nè! Mình là Mochi 🌸 Hôm nay bạn muốn săn món gì? "
                    f"Mình có vài gợi ý hot: {product_links}.{login_hint}"
                )
            return f"Chào bạn nè! Mình là Mochi 🌸 Bạn đang tìm sản phẩm gì, kể mình nghe nha!{login_hint}"

        if product_links:
            return (
                f"Mình tìm được vài món có vẻ hợp với bạn: {product_links}. "
                f"Bấm vào tên để xem chi tiết nha! ✨{login_hint}"
            )
        return (
            "Hơi bận một chút rồi — bạn mô tả thêm nhu cầu (giá, thương hiệu, công dụng) "
            "để mình gợi ý chính xác hơn nha! ✨"
        )

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
                category = data.get("category") or {}
                brand = data.get("brand") or {}
                products.append({
                    "product_id": int(data.get("id")),
                    "name": data.get("name", ""),
                    "sku": data.get("sku", ""),
                    "price": data.get("price", 0),
                    "effective_price": data.get("effective_price", data.get("price", 0)),
                    "description": data.get("description", ""),
                    "stock": data.get("stock", 0),
                    "category_id": data.get("category_id"),
                    "category_name": category.get("name", "") if isinstance(category, dict) else "",
                    "brand_name": brand.get("name", "") if isinstance(brand, dict) else "",
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
