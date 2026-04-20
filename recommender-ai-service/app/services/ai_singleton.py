"""
ai_singleton.py
---------------
Singleton quản lý KTMP RAG LLM (từ ai-ktmp).
Được tích hợp để thay thế hệ thống cũ.
"""

import os
from rag.rag_llm import get_rag_llm as get_ktmp_llm_instance


class AIModelSingleton:
    """
    Thread-safe singleton cho KTMP RAG LLM.
    """

    _ktmp_rag_llm = None

    @classmethod
    def get_ktmp_rag_llm(cls):
        """
        Trả về KTMP RAG LLM instance (Groq-based).
        """
        if cls._ktmp_rag_llm is None:
            print("[AI Singleton] Initializing KTMP RAG LLM ...")
            cls._ktmp_rag_llm = get_ktmp_llm_instance()
        return cls._ktmp_rag_llm
