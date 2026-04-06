"""
rag_pipeline.py  (v2 — Production-grade)
-----------------------------------------
Nâng cấp theo báo cáo:

1. Anti-hallucination RAG
   - Grounding: LLM PHẢI dùng context được cung cấp
   - Citation: trích dẫn nguồn rõ ràng
   - Freshness: metadata timestamp để ưu tiên thông tin mới nhất

2. Hybrid Retrieval
   - Text search (semantic)
   - DL model scores (behavioral)
   - DL model re-ranking với Dueling DQN output

3. Chunking Strategy
   - Chunk service description thành multiple chunks
   - Overlap để không mất context

4. Multi-turn Memory
   - Conversation history
   - User profile context

5. Structured Output
   - JSON-structured response với citations
   - Confidence score
   - Fallback khi không tìm thấy context
"""

import os
import sys
import json
import textwrap
import re
from typing import Optional, List
from dataclasses import dataclass, field

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "kb"))
from vector_store import HybridVectorStore, MultiModalEncoder, TEXT_INDEX, DL_INDEX, META_PATH


# ═══════════════════════════════════════════════
# 1. Data Structures
# ═══════════════════════════════════════════════

@dataclass
class RetrievedChunk:
    """Một chunk đã được retrieve."""
    service_id   : str
    service_name : str
    category     : str
    description  : str
    document     : str
    score        : float
    tags         : List[str] = field(default_factory=list)
    price_range  : str = ""


@dataclass
class RAGResponse:
    """Structured response từ RAG pipeline."""
    answer       : str
    sources      : List[RetrievedChunk]
    confidence   : float    # 0-1
    query        : str
    citations    : List[str] = field(default_factory=list)
    is_grounded  : bool = True   # False nếu LLM phải hallucinate


# ═══════════════════════════════════════════════
# 2. Anti-Hallucination Prompt Templates
# ═══════════════════════════════════════════════

SYSTEM_PROMPT = textwrap.dedent("""
    Bạn là chatbot tư vấn sách cho website bookstore.

    =====================
    NHIỆM VỤ
    - Trả lời câu hỏi dựa trên [CONTEXT] (được truy xuất từ hệ thống RAG).
    - Chỉ sử dụng thông tin liên quan nhất từ [CONTEXT].

    =====================
    NGUỒN DỮ LIỆU
    [CONTEXT]:
    {context}

    [CÂU HỎI NGƯỜI DÙNG]:
    {question}

    =====================
    QUY TẮC BẮT BUỘC
    1. CHỈ sử dụng thông tin có trong [CONTEXT].
    2. KHÔNG bịa hoặc suy đoán thêm.
    3. KHÔNG sử dụng kiến thức bên ngoài.
    4. Nếu [CONTEXT] không chứa thông tin phù hợp:
       -> Trả lời: "Tôi không tìm thấy sách phù hợp trong dữ liệu hiện có."
    5. Luôn trích dẫn TÊN SÁCH khi đề xuất.
    6. Không lặp lại nguyên văn toàn bộ context.

    =====================
    ƯU TIÊN THÔNG TIN
    - Ưu tiên đoạn context có độ liên quan cao nhất.
    - Nếu có nhiều sách phù hợp -> chọn tối đa 3 sách tốt nhất.

    =====================
    PHONG CÁCH TRẢ LỜI
    - Tối đa 3 dòng hoặc 3 bullet points
    - Ngắn gọn, trực tiếp
    - Không giải thích dài dòng
    - Không emoji

    =====================
    THIẾU THÔNG TIN
    - Nếu câu hỏi mơ hồ:
      -> Hỏi lại đúng 1 câu ngắn để làm rõ

    =====================
    OUTPUT
    - Dạng danh sách:
      • Tên sách 1
      • Tên sách 2

    - Hoặc câu trả lời ngắn gọn đúng trọng tâm
""").strip()


def build_grounded_prompt(
    query        : str,
    context      : str,
    user_profile : Optional[dict] = None,
    history      : Optional[List] = None,
) -> List[dict]:
    """
    Xây dựng prompt với grounding instructions để tránh hallucination.
    Tương tự kiến trúc RAG trong báo cáo: Context Window = context + prompt gốc.
    """
    messages = []

    # Conversation history
    if history:
        for role, content in history[-6:]:   # Giới hạn 6 turns để tránh overflow
            messages.append({"role": role, "content": content})

    # Build user message
    parts = []

    if user_profile:
        profile_str = _format_profile(user_profile)
        parts.append(f"[THÔNG TIN NGƯỜI DÙNG]\n{profile_str}")

    # Context block — quan trọng nhất, đặt trước query
    parts.append(f"[CONTEXT]\n{context}")

    parts.append(f"[CÂU HỎI NGƯỜI DÙNG]\n{query}")

    parts.append(
        "[YÊU CẦU TRẢ LỜI]\n"
        "Dựa CHỈ vào thông tin sách trên, hãy:\n"
        "1. Trả lời đúng trọng tâm câu hỏi của khách, ngắn gọn, trực tiếp\n"
        "2. Nếu cần đề xuất, chỉ đề xuất 1-3 sách/sản phẩm phù hợp nhất (trích dẫn tên)\n"
        "3. Mỗi gợi ý chỉ nêu lý do ngắn (1 ý)\n"
        "4. Nếu không có gợi ý phù hợp -> nói rõ"
    )

    messages.append({"role": "user", "content": "\n\n".join(parts)})
    return messages


def _format_profile(profile: dict) -> str:
    lines = []
    field_names = {
        "age": "Tuổi", "gender": "Giới tính", "location": "Địa điểm",
        "interests": "Sở thích", "purchase_history": "Lịch sử mua",
        "income_range": "Thu nhập", "family_status": "Tình trạng gia đình",
    }
    for k, v in profile.items():
        label = field_names.get(k, k)
        if isinstance(v, list):
            v = ", ".join(str(x) for x in v)
        lines.append(f"  {label}: {v}")
    return "\n".join(lines)


def _format_context(chunks: List[RetrievedChunk]) -> str:
    """Format retrieved chunks thành context block cho LLM."""
    if not chunks:
        return "Không tìm thấy sách phù hợp."

    parts = []
    for i, c in enumerate(chunks, 1):
        tags = ", ".join(c.tags[:5]) if c.tags else "N/A"
        parts.append(
            f"[{i}] TÊN SÁCH/SẢN PHẨM: {c.service_name}\n"
            f"    LOẠI: {c.category}\n"
            f"    MÔ TẢ: {c.description}\n"
            f"    GIÁ: {c.price_range or 'N/A'}\n"
            f"    TAGS: {tags}\n"
            f"    ĐỘ LIÊN QUAN: {c.score:.3f}"
        )
    return "\n\n".join(parts)


# ═══════════════════════════════════════════════
# 3. Confidence Estimation
# ═══════════════════════════════════════════════

def estimate_confidence(chunks: List[RetrievedChunk],
                        query: str) -> float:
    """
    Ước tính confidence dựa trên:
    - Max retrieval score
    - Số chunks có score cao
    - Query length (ngắn → ít context → thấp hơn)
    """
    if not chunks:
        return 0.0

    top_score = chunks[0].score
    high_count = sum(1 for c in chunks if c.score > 0.5)
    query_factor = min(1.0, len(query.split()) / 8)   # normalize

    confidence = (0.6 * top_score
                  + 0.3 * (high_count / max(len(chunks), 1))
                  + 0.1 * query_factor)
    return min(1.0, confidence)


# ═══════════════════════════════════════════════
# 4. LLM Backends (Anthropic → OpenAI → Mock)
# ═══════════════════════════════════════════════

# Groq model options (cập nhật theo model còn hỗ trợ)
GROQ_MODELS = {
    "fast"    : "llama-3.1-8b-instant",     # nhanh, chi phí thấp
    "balanced": "llama-3.3-70b-versatile",  # chất lượng cao, ổn định
    "best"    : "llama-3.3-70b-versatile",  # giữ alias cũ để tương thích
}


def call_llm(messages: List[dict], system: str,
             chunks: List[RetrievedChunk] = None,
             backend: str = "auto") -> str:
    """
    Ưu tiên:  groq → anthropic → openai → mock
    'auto' tự detect dựa trên env vars có sẵn.
    """
    # ── Groq (FREE — ưu tiên đầu tiên trong auto) ──────────
    groq_error = None
    if backend == "groq" or (
        backend == "auto" and os.environ.get("GROQ_API_KEY")
    ):
        try:
            return _call_groq(messages, system)
        except Exception as e:
            groq_error = str(e)
            print(f"[WARN] Groq: {e}")

    # ── Anthropic ───────────────────────────────────────────
    if backend == "anthropic" or (
        backend == "auto" and os.environ.get("ANTHROPIC_API_KEY")
    ):
        try:
            return _call_anthropic(messages, system)
        except Exception as e:
            print(f"[WARN] Anthropic: {e}")

    # ── OpenAI ──────────────────────────────────────────────
    if backend == "openai" or (
        backend == "auto" and os.environ.get("OPENAI_API_KEY")
    ):
        try:
            return _call_openai(messages, system)
        except Exception as e:
            print(f"[WARN] OpenAI: {e}")

    # ── Mock fallback ───────────────────────────────────────
    return _mock_llm(messages, chunks, groq_error=groq_error)


def _call_groq(messages, system,
               model: str = None,
               max_tokens: int = 1024,
               temperature: float = 0.7) -> str:
    """
    Gọi Groq API — tương thích hoàn toàn với OpenAI SDK.
    Lấy key miễn phí tại: https://console.groq.com

    Model mặc định: llama-3.1-8b-instant
    Đổi model qua env: GROQ_MODEL=balanced hoặc GROQ_MODEL=best
    """
    from openai import OpenAI   # Groq dùng OpenAI-compatible SDK

    # Chọn model qua env var hoặc default
    model_key = os.environ.get("GROQ_MODEL", "fast")
    selected  = model or GROQ_MODELS.get(model_key, GROQ_MODELS["fast"])

    client = OpenAI(
        api_key  = os.environ["GROQ_API_KEY"],
        base_url = "https://api.groq.com/openai/v1",
    )

    resp = client.chat.completions.create(
        model       = selected,
        messages    = [{"role": "system", "content": system}] + messages,
        max_tokens  = max_tokens,
        temperature = temperature,
    )

    answer = resp.choices[0].message.content

    # Log usage (Groq trả về token count — hữu ích để monitor quota)
    usage = resp.usage
    print(f"  [Groq/{selected}] "
          f"prompt={usage.prompt_tokens} | "
          f"completion={usage.completion_tokens} | "
          f"total={usage.total_tokens} tokens")

    return answer


def _call_anthropic(messages, system, model="claude-opus-4-5", max_tokens=1024):
    import anthropic
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    resp   = client.messages.create(
        model=model, max_tokens=max_tokens,
        system=system, messages=messages,
    )
    return resp.content[0].text


def _call_openai(messages, system, model="gpt-4o-mini", max_tokens=1024):
    from openai import OpenAI
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    resp   = client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": system}] + messages,
        max_tokens=max_tokens, temperature=0.7,
    )
    return resp.choices[0].message.content


def _mock_llm(messages, chunks=None, groq_error: Optional[str] = None) -> str:
    """Template-based mock — không cần API key."""
    query = ""
    for m in reversed(messages):
        if m["role"] == "user":
            match = re.search(r"\[CÂU HỎI NGƯỜI DÙNG\]\n(.+?)(\n|$)", m["content"])
            if match:
                query = match.group(1).strip()
            break

    if not chunks:
        return (
            "Xin lỗi, hiện tại tôi không tìm thấy sách phù hợp với yêu cầu của bạn. "
            "Hãy cung cấp thêm thông tin để tôi có thể hỗ trợ tốt hơn."
        )

    top3  = chunks[:3]
    lines = []
    for i, c in enumerate(top3, 1):
        lines.append(f"{i}. **{c.service_name}** ({c.category}): {c.description[:100]}…")

    if os.environ.get("GROQ_API_KEY"):
        footer = "_(Fallback response — Groq tạm thời lỗi, hệ thống đang dùng chế độ dự phòng)_"
        if groq_error:
            footer += f"\n_(Chi tiết kỹ thuật: {groq_error})_"
    else:
        footer = "_(Mock response — Chưa phát hiện GROQ_API_KEY)_"

    return textwrap.dedent(f"""
        Dựa trên nhu cầu của bạn về "{query}", tôi đề xuất các sách/sản phẩm sau:

        {chr(10).join(lines)}

        Các gợi ý trên đều được chọn dựa trên dữ liệu bookstore hiện có.
        Bạn muốn mình phân tích kỹ hơn gợi ý nào?

        {footer}
    """).strip()


# ═══════════════════════════════════════════════
# 5. Retriever
# ═══════════════════════════════════════════════

class HybridRetriever:
    """
    Retrieve services dùng Hybrid Vector Store.
    Tích hợp text + DL embeddings như báo cáo đề xuất.
    """

    def __init__(self, text_index: str = TEXT_INDEX,
                 dl_index: str = DL_INDEX,
                 meta_path: str = META_PATH,
                 model_name: str = "all-MiniLM-L6-v2"):
        self.encoder = MultiModalEncoder(model_name)
        try:
            self.store = HybridVectorStore.load(text_index, dl_index, meta_path)
            print(f"Loaded vector store: {len(self.store.text_index)} services")
        except Exception as e:
            print(f"[WARN] Could not load vector store: {e}")
            self.store = None

    def retrieve(
        self,
        query        : str,
        top_k        : int = 5,
        user_profile : Optional[dict] = None,
        user_embedding : Optional = None,    # numpy array từ DL model
        score_threshold : float = 0.0,
    ) -> List[RetrievedChunk]:
        """Retrieve top-k services với hybrid scoring."""
        if self.store is None:
            print("[WARN] No vector store loaded — returning empty results")
            return []

        enriched = self._enrich_query(query, user_profile)
        q_vecs   = self.encoder.encode_query(enriched, user_embedding)
        raw      = self.store.search(q_vecs, top_k=top_k * 2)

        results = []
        for score, svc in raw:
            if score < score_threshold:
                continue
            results.append(RetrievedChunk(
                service_id   = svc.get("service_id",   ""),
                service_name = svc.get("service_name", ""),
                category     = svc.get("category",     ""),
                description  = svc.get("description",  ""),
                document     = svc.get("document",     ""),
                score        = score,
                tags         = svc.get("tags",         []),
                price_range  = svc.get("price_range",  ""),
            ))

        return results[:top_k]

    def _enrich_query(self, query: str, profile: Optional[dict]) -> str:
        if not profile:
            return query
        hints = []
        if "age" in profile:
            hints.append(f"người {profile['age']} tuổi")
        if "interests" in profile:
            hints.append(", ".join(profile["interests"][:3]))
        if "location" in profile:
            hints.append(f"tại {profile['location']}")
        prefix = " | ".join(hints)
        return f"{prefix} | {query}" if hints else query

    def format_context(self, chunks: List[RetrievedChunk]) -> str:
        return _format_context(chunks)


# ═══════════════════════════════════════════════
# 6. RAG Pipeline
# ═══════════════════════════════════════════════

class RAGPipeline:
    """
    Full RAG pipeline với anti-hallucination và hybrid retrieval.

    Tuân thủ kiến trúc RAG trong báo cáo:
    Query → Vector DB → top-k Context → LLM → Answer
    """

    def __init__(
        self,
        retriever    : Optional[HybridRetriever] = None,
        top_k        : int   = 5,
        llm_backend  : str   = "auto",
        score_threshold: float = 0.0,
    ):
        self.retriever       = retriever or HybridRetriever()
        self.top_k           = top_k
        self.llm_backend     = llm_backend
        self.score_threshold = score_threshold
        self.history         : List[tuple] = []

    def chat(
        self,
        query          : str,
        user_profile   : Optional[dict] = None,
        user_embedding : Optional = None,
        dl_service_scores : Optional[dict] = None,   # {service_id: float} từ DL model
        return_full    : bool = True,
    ) -> RAGResponse:
        """
        Main RAG turn.

        Args:
            query             : User question
            user_profile      : User metadata dict
            user_embedding    : numpy array từ DL UserTower (optional)
            dl_service_scores : DL model recommendation scores để re-rank (optional)
            return_full       : Include sources in response
        """
        # ── Step 1: Retrieve ─────────────────────────────────
        chunks = self.retriever.retrieve(
            query        = query,
            top_k        = self.top_k,
            user_profile = user_profile,
            user_embedding = user_embedding,
            score_threshold = self.score_threshold,
        )

        # ── Step 2: DL Re-ranking (nếu có scores từ DL model) ─
        if dl_service_scores and chunks:
            chunks = self._rerank_with_dl(chunks, dl_service_scores)

        # ── Step 3: Estimate confidence ──────────────────────
        confidence = estimate_confidence(chunks, query)

        # ── Step 4: Build context ────────────────────────────
        context = _format_context(chunks)

        # ── Step 5: Build prompt ─────────────────────────────
        messages = build_grounded_prompt(
            query        = query,
            context      = context,
            user_profile = user_profile,
            history      = self.history,
        )

        # ── Step 6: Generate ─────────────────────────────────
        answer = call_llm(
            messages    = messages,
            system      = SYSTEM_PROMPT,
            chunks      = chunks,
            backend     = self.llm_backend,
        )

        # ── Step 7: Extract citations ─────────────────────────
        citations = [c.service_name for c in chunks
                     if c.service_name.lower() in answer.lower()]

        # ── Step 8: Update history ───────────────────────────
        self.history.append(("user",      query))
        self.history.append(("assistant", answer))

        return RAGResponse(
            answer      = answer,
            sources     = chunks if return_full else [],
            confidence  = confidence,
            query       = query,
            citations   = citations,
            is_grounded = len(chunks) > 0,
        )

    def reset(self):
        self.history = []

    def _rerank_with_dl(self, chunks: List[RetrievedChunk],
                        dl_scores: dict) -> List[RetrievedChunk]:
        """
        Re-rank chunks bằng cách blend FAISS score + DL score.
        Tương tự Re-ranking stage trong Multi-stage Pipeline.
        blend = 0.55 * text_score + 0.45 * dl_score
        """
        import math
        for c in chunks:
            dl_raw  = dl_scores.get(c.service_id, 0.0)
            dl_norm = 1 / (1 + math.exp(-dl_raw))   # sigmoid → [0, 1]
            c.score = 0.55 * c.score + 0.45 * dl_norm
        chunks.sort(key=lambda x: x.score, reverse=True)
        return chunks


# ═══════════════════════════════════════════════
# 7. Demo + Interactive Chat
# ═══════════════════════════════════════════════

def _detect_backend() -> str:
    """Tự động phát hiện backend khả dụng và thông báo."""
    if os.environ.get("GROQ_API_KEY"):
        model_key = os.environ.get("GROQ_MODEL", "fast")
        model     = GROQ_MODELS.get(model_key, GROQ_MODELS["fast"])
        print(f"Backend: Groq ({model})  [FREE]")
        return "groq"
    if os.environ.get("ANTHROPIC_API_KEY"):
        print("Backend: Anthropic Claude")
        return "anthropic"
    if os.environ.get("OPENAI_API_KEY"):
        print("Backend: OpenAI")
        return "openai"
    print("Backend: Mock (set GROQ_API_KEY để dùng Groq miễn phí)")
    return "auto"


def run_demo():
    """Chạy demo nhanh với 3 câu hỏi mẫu."""
    backend = _detect_backend()
    pipeline = RAGPipeline(top_k=4, llm_backend=backend)
    profile  = {
        "age"           : 26,
        "gender"        : "nữ",
        "location"      : "Hà Nội",
        "interests"     : ["tiểu thuyết", "kinh doanh", "self-help"],
        "family_status" : "độc thân",
    }

    questions = [
        "Mình muốn tìm tiểu thuyết trinh thám dễ đọc.",
        "Có sách self-help nào giúp quản lý thời gian không?",
        "Gợi ý sách kinh doanh cho người mới khởi nghiệp.",
    ]

    print()
    for q in questions:
        print(f"{'─'*55}")
        resp = pipeline.chat(q, user_profile=profile)
        print(f"👤 {q}")
        print(f"\n🤖 {resp.answer}")
        print(f"\n   Confidence : {resp.confidence:.2f}")
        print(f"   Grounded   : {resp.is_grounded}")
        print(f"   Citations  : {resp.citations}")
        print(f"   Sources    : {[s.service_name for s in resp.sources]}")


def run_interactive():
    """
    Interactive chat loop — gõ tự do, Ctrl+C để thoát.
    Hỗ trợ multi-turn (nhớ lịch sử hội thoại).
    """
    backend = _detect_backend()
    pipeline = RAGPipeline(top_k=4, llm_backend=backend)

    # Nhập profile nhanh (tuỳ chọn)
    print("\nNhập profile (Enter để bỏ qua):")
    age    = input("  Tuổi: ").strip()
    loc    = input("  Địa điểm: ").strip()
    inter  = input("  Sở thích (cách nhau bởi dấu phẩy): ").strip()

    profile = {}
    if age:
        try:
            profile["age"] = int(age)
        except ValueError:
            pass
    if loc:
        profile["location"] = loc
    if inter:
        profile["interests"] = [x.strip() for x in inter.split(",")]

    print(f"\nProfile: {profile or 'Không có'}")
    print("Gõ 'reset' để xoá lịch sử | Ctrl+C để thoát\n")
    print("═" * 55)

    while True:
        try:
            query = input("\n👤 Bạn: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nTạm biệt!")
            break

        if not query:
            continue

        if query.lower() == "reset":
            pipeline.reset()
            print("[Đã xoá lịch sử hội thoại]")
            continue

        resp = pipeline.chat(query, user_profile=profile or None)

        print(f"\n🤖 Tư vấn viên:\n{resp.answer}")

        if resp.sources:
            names = [s.service_name for s in resp.sources[:3]]
            print(f"\n   📎 Nguồn: {' | '.join(names)}")

        print(f"   📊 Confidence: {resp.confidence:.0%}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="RAG Chatbot với Groq")
    parser.add_argument("--demo",        action="store_true", help="Chạy demo 3 câu hỏi mẫu")
    parser.add_argument("--interactive", action="store_true", help="Chạy interactive chat")
    parser.add_argument("--model",       choices=["fast", "balanced", "best"],
                        default="fast",  help="Groq model tier")
    args = parser.parse_args()

    # Set model tier nếu chỉ định
    if args.model:
        os.environ.setdefault("GROQ_MODEL", args.model)

    print("═" * 55)
    print("  RAG Chatbot v2 — Powered by Groq (Free)  ")
    print("═" * 55)

    if args.interactive:
        run_interactive()
    else:
        # Mặc định chạy demo
        run_demo()
        print("\n" + "═"*55)
        print("Chạy với --interactive để chat trực tiếp")