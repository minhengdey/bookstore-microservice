"""
retriever.py
------------
Legacy compatibility shim.

Trong v2, logic retrieval được tích hợp trực tiếp vào rag_pipeline.py
thông qua class HybridRetriever. File này chỉ còn giữ lại như
backward-compatible wrapper nếu có code cũ import từ đây.

Để dùng retriever: import trực tiếp từ rag_pipeline.py
    from rag_pipeline import HybridRetriever
"""

import warnings

# Re-export để backward-compatible với code cũ import retriever.py
from rag_pipeline import (
    HybridRetriever as ServiceRetriever,
    RetrievedChunk  as RetrievedService,
)

warnings.warn(
    "retriever.py là module cũ (v1). "
    "Import trực tiếp từ rag_pipeline.py: "
    "`from rag_pipeline import HybridRetriever`",
    DeprecationWarning,
    stacklevel=2,
)
