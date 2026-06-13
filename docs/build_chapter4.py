# -*- coding: utf-8 -*-
"""Generate CHUONG4 per outline 4.1-4.16."""
from pathlib import Path

OUT = Path(__file__).parent / "CHUONG4_TAI_LIEU_TICH_HOP_VA_TRIEN_KHAI.md"

TOC = r"""# CHƯƠNG 4: XÂY DỰNG VÀ TÍCH HỢP TOÀN BỘ HỆ THỐNG

> **Phạm vi:** Mọi mô tả trong chương này đối chiếu trực tiếp với repository `e-commerce` — `docker-compose.yml`, `api-gateway/`, 14+ microservice Django, `nginx/`, `common/`, `recommender-ai-service/`. Thành phần không có trong code được ghi: **"Không tìm thấy trong source code dự án"**.

---

## MỤC LỤC CHƯƠNG 4

| Mục | Tiêu đề |
|-----|---------|
| **4.1** | Tổng quan quá trình xây dựng hệ thống |
| **4.2** | Kiến trúc triển khai thực tế |
| **4.3** | Cấu trúc source code |
| **4.4** | Công nghệ sử dụng |
| **4.5** | Xây dựng Backend |
| **4.6** | Xây dựng AI Service |
| **4.7** | Tích hợp AI và hệ thống thương mại điện tử |
| **4.8** | Triển khai Knowledge Base |
| **4.9** | Triển khai Graph Database |
| **4.10** | Triển khai Recommendation System |
| **4.11** | Triển khai Chatbot |
| **4.12** | Triển khai hệ thống bằng Docker |
| **4.13** | Triển khai API |
| **4.14** | Thể hiện kết quả hệ thống |
| 4.14.1–4.14.11 | Các màn hình chi tiết |
| **4.15** | Đánh giá kết quả triển khai |
| **4.16** | Nhận xét chương |

---"""


def main():
    from build_chapter4_sections import (
        SEC_41, SEC_42, SEC_43, SEC_44, SEC_45, SEC_46, SEC_47,
        SEC_48, SEC_49, SEC_410, SEC_411, SEC_412, SEC_413,
        SEC_414, SEC_415, SEC_416,
    )
    parts = [TOC, SEC_41, SEC_42, SEC_43, SEC_44, SEC_45, SEC_46, SEC_47,
             SEC_48, SEC_49, SEC_410, SEC_411, SEC_412, SEC_413,
             SEC_414, SEC_415, SEC_416]
    content = "\n\n".join(parts)
    OUT.write_text(content, encoding="utf-8")
    import re
    print(f"Written {OUT}")
    print(f"Words: {len(re.findall(r'[\\wÀ-ỹ]+', content, re.UNICODE))}, Lines: {len(content.splitlines())}")


if __name__ == "__main__":
    main()
