"""
intent_router.py — Phân loại ý định hội thoại chatbot (rule-based, nhanh).
"""
import re
from enum import Enum


class ChatIntent(str, Enum):
    SEARCH = "search_product"
    RECOMMEND = "recommend"
    COMPARE = "compare"
    FOLLOW_UP = "follow_up"
    POLICY = "policy"
    GREETING = "greeting"
    GENERAL = "general_chat"


_POLICY_PATTERNS = (
    r"đổi\s*trả", r"hoàn\s*tiền", r"giao\s*hàng", r"vận\s*chuyển", r"ship\b",
    r"thanh\s*toán", r"cod\b", r"bảo\s*hành", r"chính\s*sách", r"phí\s*ship",
)
_GREETING_PATTERNS = (r"xin\s*chào", r"^chào\b", r"^hi\b", r"^hello\b", r"hey\b")
_RECOMMEND_PATTERNS = (
    r"gợi\s*ý", r"goi\s*y", r"đề\s*xuất", r"nên\s*mua", r"recommend",
    r"phù\s*hợp", r"hot\b", r"bán\s*chạy", r"mới\s*về",
)
_COMPARE_PATTERNS = (r"so\s*sánh", r"khác\s*nhau", r"hơn\s*loại", r"tốt\s*hơn", r"nên\s*chọn")
_FOLLOW_UP_PATTERNS = (
    r"rẻ\s*hơn", r"đắt\s*hơn", r"dưới\s*\d", r"trên\s*\d", r"trong\s*tầm",
    r"còn\s*hàng", r"size\b", r"màu\b", r"loại\s*khác", r"thêm\s*nữa", r"nữa\s*đi",
    r"cái\s*kia", r"món\s*đó", r"sản\s*phẩm\s*đó", r"còn\s*gì",
)
_SEARCH_HINTS = (
    r"tìm\b", r"mua\b", r"cần\b", r"muốn\b", r"son\b", r"kem\b", r"áo\b",
    r"quần\b", r"giày\b", r"điện\s*thoại", r"laptop\b", r"tai\s*nghe",
    r"nồi\b", r"máy\b", r"thảm\b", r"serum\b", r"sữa\s*rửa",
)


def _has_pattern(text: str, patterns: tuple) -> bool:
    return any(re.search(p, text, re.IGNORECASE) for p in patterns)


def _history_text(history: list, max_turns: int = 6) -> str:
    parts = []
    for item in (history or [])[-max_turns:]:
        if isinstance(item, (list, tuple)) and len(item) >= 2:
            parts.append(str(item[1]))
        elif isinstance(item, dict) and item.get("content"):
            parts.append(str(item["content"]))
    return " ".join(parts).lower()


def classify_intent(message: str, history: list | None = None) -> ChatIntent:
    msg = str(message or "").strip().lower()
    hist = _history_text(history or [])

    if not msg:
        return ChatIntent.GENERAL

    if _has_pattern(msg, _POLICY_PATTERNS):
        return ChatIntent.POLICY

    if _has_pattern(msg, _GREETING_PATTERNS) and len(msg.split()) <= 6:
        return ChatIntent.GREETING

    if _has_pattern(msg, _COMPARE_PATTERNS) and hist:
        return ChatIntent.COMPARE

    if _has_pattern(msg, _FOLLOW_UP_PATTERNS) and hist:
        return ChatIntent.FOLLOW_UP

    if _has_pattern(msg, _RECOMMEND_PATTERNS) and not _has_pattern(msg, _SEARCH_HINTS):
        return ChatIntent.RECOMMEND

    if _has_pattern(msg, _SEARCH_HINTS) or len(msg.split()) >= 2:
        return ChatIntent.SEARCH

    if hist and len(msg.split()) <= 8:
        return ChatIntent.FOLLOW_UP

    return ChatIntent.GENERAL


def build_retrieval_query(message: str, history: list | None = None) -> str:
    """Gộp ngữ cảnh hội thoại để hybrid search hiểu follow-up."""
    user_turns = []
    for item in (history or [])[-6:]:
        if isinstance(item, (list, tuple)) and len(item) >= 2 and item[0] == "user":
            user_turns.append(str(item[1]).strip())
        elif isinstance(item, dict) and item.get("role") == "user":
            user_turns.append(str(item.get("content", "")).strip())
    user_turns.append(str(message or "").strip())
    user_turns = [t for t in user_turns if t]
    if not user_turns:
        return str(message or "").strip()
    if len(user_turns) == 1:
        return user_turns[0]
    return " ".join(user_turns[-3:])
