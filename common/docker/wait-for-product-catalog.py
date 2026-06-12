#!/usr/bin/env python3
"""Chờ product-service có đủ sản phẩm trước khi seed phụ thuộc (promotion, recommender, ...)."""
import json
import os
import sys
import time
import urllib.error
import urllib.request


def main() -> int:
    base = os.environ.get("PRODUCT_SERVICE_URL", "http://product-service:8000").rstrip("/")
    min_count = int(
        os.environ.get("MOCK_PRODUCT_MIN")
        or os.environ.get("MOCK_PRODUCT_COUNT", "50")
    )
    max_wait = int(os.environ.get("MOCK_CATALOG_WAIT_SEC", "240"))
    interval = float(os.environ.get("MOCK_CATALOG_WAIT_INTERVAL", "3"))
    url = f"{base}/products/?page_size=1"

    deadline = time.time() + max_wait
    attempt = 0
    while time.time() < deadline:
        attempt += 1
        try:
            with urllib.request.urlopen(url, timeout=8) as resp:
                payload = json.loads(resp.read().decode())
            count = int(payload.get("count") or 0)
            if count >= min_count:
                print(f"[mock-seed] Product catalog ready: {count} items (need >= {min_count})")
                return 0
            print(f"[mock-seed] Waiting for catalog ({count}/{min_count}) attempt {attempt}...")
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError) as exc:
            print(f"[mock-seed] Product-service not ready ({exc}), retry {attempt}...")

        time.sleep(interval)

    print(
        f"[mock-seed] Timed out after {max_wait}s waiting for >= {min_count} products at {url}",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
