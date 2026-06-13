# -*- coding: utf-8 -*-
"""Generate CHUONG3_TAI_LIEU_AI_SERVICE.md per thesis outline 3.1-3.14."""
from pathlib import Path

OUT = Path(__file__).parent / "CHUONG3_TAI_LIEU_AI_SERVICE.md"

TOC = r"""# CHƯƠNG 3: THIẾT KẾ VÀ TRIỂN KHAI AI-SERVICE

> **Phạm vi:** Toàn bộ nội dung chương này được đối chiếu trực tiếp với mã nguồn trong thư mục `recommender-ai-service/`, `model-serving-service/`, tích hợp `api-gateway/` và cấu hình `docker-compose.yml`. Khi một thành phần không tồn tại trong repository, chương ghi rõ: **"Không tìm thấy trong source code dự án"**.

---

## MỤC LỤC CHƯƠNG 3

| Mục | Tiêu đề |
|-----|---------|
| **3.1** | Phân tích yêu cầu AI-Service |
| 3.1.1 | Bài toán thực tế |
| 3.1.2 | Mục tiêu của AI-Service |
| **3.2** | Kiến trúc tổng thể AI-Service |
| **3.3** | Knowledge Base |
| **3.4** | Vector Database |
| **3.5** | RAG (Retrieval Augmented Generation) |
| **3.6** | Graph RAG (GraphRAG) |
| **3.7** | Neo4j Knowledge Graph |
| **3.8** | Deep Learning Model |
| 3.8.1 | Recommendation Model |
| 3.8.2 | Deep Learning Architecture |
| 3.8.3 | CODE STRUCTURE |
| **3.9** | Dữ liệu thực nghiệm |
| 3.9.1 | Kết quả thực nghiệm |
| 3.9.2 | Nhận xét kết quả |
| **3.10** | Deploy AI Service |
| **3.11** | Tích hợp Chat + Deep Learning |
| **3.12** | Tích hợp AI vào hệ thống E-Commerce |
| **3.13** | AI Recommender System |
| **3.14** | Đánh giá AI-Service |

---"""


def main():
    from build_chapter3_sections import (
        SEC_31, SEC_32, SEC_33, SEC_34, SEC_35, SEC_36, SEC_37,
        SEC_38, SEC_39, SEC_310, SEC_311, SEC_312, SEC_313, SEC_314,
    )
    from build_chapter3_supplement import EXPANSIONS

    SEC_33 = SEC_33 + EXPANSIONS.get("SEC_33", "")
    SEC_35 = SEC_35 + EXPANSIONS.get("SEC_35", "")
    SEC_36 = SEC_36 + EXPANSIONS.get("SEC_36", "")
    SEC_37 = SEC_37 + EXPANSIONS.get("SEC_37", "")
    SEC_38 = SEC_38 + EXPANSIONS.get("SEC_38", "")
    SEC_312 = SEC_312 + EXPANSIONS.get("SEC_312", "")
    SEC_313 = SEC_313 + EXPANSIONS.get("SEC_313", "")
    SEC_314 = SEC_314 + EXPANSIONS.get("SEC_314", "")

    from build_chapter3_supplement import SEC_APPENDIX

    sections = [
        TOC,
        SEC_31, SEC_32, SEC_33, SEC_34, SEC_35, SEC_36, SEC_37,
        SEC_38, SEC_39, SEC_310, SEC_311, SEC_312, SEC_313, SEC_314,
        SEC_APPENDIX,
    ]
    content = "\n\n".join(sections)
    OUT.write_text(content, encoding="utf-8")
    import re
    words = len(re.findall(r"\w+", content))
    lines = len(content.splitlines())
    print(f"Written {OUT}")
    print(f"Lines: {lines}, Words: {words}")


if __name__ == "__main__":
    main()
