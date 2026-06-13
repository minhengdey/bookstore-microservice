# -*- coding: utf-8 -*-
"""Append adapted legacy content for word count target."""
import re
from pathlib import Path

CH3 = Path(__file__).parent / "CHUONG3_TAI_LIEU_AI_SERVICE.md"
OLD = Path(r"C:\Users\dlmin\.cursor\projects\d-Study-Nam4-Ky2-KTVHTPM-ai-ktmp-e-commerce\uploads\d__Study_Nam4_Ky2_KTVHTPM_ai-ktmp_e-commerce_docs_CHUONG3_TAI_LIEU_AI_SERVICE-L1-L1396-0.md")

HEADER = """
---

## PHỤ LỤC KỸ THUẬT A — NỘI DUNG CHI TIẾT TỪ QUÁ TRÌNH PHÁT TRIỂN (ĐÃ CHUẨN HÓA THEO FORM 3.1–3.14)

> **Chú thích:** Phụ lục này tổng hợp chi tiết kỹ thuật từ quá trình phát triển model và tích hợp, đã được **ánh xạ lại** vào cấu trúc Chương 3 mới. Các script training (`train_models_v5.py`, `generate_data_v4.py`) được nhắc trong phụ lục — **Không tìm thấy trong source code dự án** tại thời điểm đối chiếu; artifact `model_best.keras` và metrics trong `models/model_best_evaluation.txt` **có trong repo**.

"""

# Sections to extract from old doc (line-based) and remap headers
REMAP = [
    (r"^## 3\.2 ", "### PHỤ LỤC A.1 — Deep Learning (ánh xạ mục 3.8)\n\n"),
    (r"^### 3\.2\.1", "#### A.1.1"),
    (r"^### 3\.2\.2", "#### A.1.2"),
    (r"^### 3\.2\.3", "#### A.1.3"),
    (r"^### 3\.2\.4", "#### A.1.4"),
    (r"^### 3\.2\.5", "#### A.1.5"),
    (r"^### 3\.2\.6", "#### A.1.6"),
    (r"^### 3\.2\.7", "#### A.1.7"),
    (r"^### 3\.2\.8", "#### A.1.8"),
    (r"^### 3\.2\.9", "#### A.1.9"),
    (r"^## 3\.3 Deploy", "### PHỤ LỤC A.2 — Deploy (ánh xạ mục 3.10)\n\n"),
    (r"^### 3\.3\.", "#### A.2."),
    (r"^## 3\.4 RAG", "### PHỤ LỤC A.3 — RAG Chatbot (ánh xạ mục 3.5, 3.11)\n\n"),
    (r"^### 3\.4\.", "#### A.3."),
    (r"^## 3\.5 Tích hợp", "### PHỤ LỤC A.4 — Hybrid Engine & E-commerce (ánh xạ mục 3.12, 3.13)\n\n"),
    (r"^### 3\.5\.", "#### A.4."),
]

def adapt_old(text: str) -> str:
    # Take from old 3.2 through end, skip old 3.1 intro
    start = text.find("## 3.2 Deep Learning")
    if start < 0:
        start = text.find("### 3.2.1")
    if start < 0:
        return ""
    chunk = text[start:]
    # Remove old top-level headers that conflict
    for pat, repl in REMAP:
        chunk = re.sub(pat, repl, chunk, flags=re.MULTILINE)
    # Fix old wrong paths
    chunk = chunk.replace("rag/rag_system.py", "rag/retriever.py")
    chunk = chunk.replace("train_ai", "ensure_recommender_models (train_ai Không tìm thấy)")
    return chunk

def main():
    base = CH3.read_text(encoding="utf-8")
    if "PHỤ LỤC KỸ THUẬT A" in base:
        base = base.split("## PHỤ LỤC KỸ THUẬT A")[0].rstrip()
    old = OLD.read_text(encoding="utf-8") if OLD.exists() else ""
    appendix = HEADER + adapt_old(old)
    merged = base + "\n\n" + appendix
    CH3.write_text(merged, encoding="utf-8")
    print(f"Words: {len(re.findall(r'\w+', merged))}, Lines: {len(merged.splitlines())}")

if __name__ == "__main__":
    main()
