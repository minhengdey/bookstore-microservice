"""
E2E Test Script – Kiểm thử end-to-end toàn bộ luồng mua hàng.

Sử dụng:
    python scripts/e2e_test.py
    python scripts/e2e_test.py --dry-run
    BASE_URL=http://localhost:8000 python scripts/e2e_test.py
"""

import os
import sys
import time
import random
import string
import argparse
from collections import namedtuple

import requests

# ── Hằng số ──────────────────────────────────────────────────────────────────

BASE_URL = os.environ.get("BASE_URL", "http://localhost:8000")
MAX_POLL = 10
POLL_INTERVAL = 2

GREEN = "\033[92m"
RED   = "\033[91m"
RESET = "\033[0m"
BOLD  = "\033[1m"

# ── StepResult ────────────────────────────────────────────────────────────────

StepResult = namedtuple("StepResult", ["name", "passed", "duration", "detail"])

# ── Helpers ───────────────────────────────────────────────────────────────────

def random_user():
    """Sinh username ngẫu nhiên 8 ký tự và email tương ứng."""
    suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
    username = f"user_{suffix}"
    email = f"{username}@test.com"
    return username, email


def print_step(result: StepResult) -> None:
    """In kết quả PASS/FAIL của một bước kèm tên và thời gian thực thi."""
    if result.passed:
        status = f"{GREEN}{BOLD}[PASS]{RESET}"
    else:
        status = f"{RED}{BOLD}[FAIL]{RESET}"
    print(f"  {status} {result.name:<30} ({result.duration:.2f}s)  {result.detail}")


def print_summary(results: list) -> None:
    """In bảng tổng kết tất cả các bước."""
    print()
    print(f"{BOLD}{'─' * 60}{RESET}")
    print(f"{BOLD}  SUMMARY{RESET}")
    print(f"{BOLD}{'─' * 60}{RESET}")
    for r in results:
        print_step(r)
    print(f"{BOLD}{'─' * 60}{RESET}")
    passed = sum(1 for r in results if r.passed)
    total = len(results)
    color = GREEN if passed == total else RED
    print(f"  {color}{BOLD}{passed}/{total} steps passed{RESET}")
    print(f"{BOLD}{'─' * 60}{RESET}")
    print()

# ── Các bước kiểm thử ─────────────────────────────────────────────────────────

def step_register(session: requests.Session, dry_run: bool = False):
    """
    Bước 1: Đăng ký người dùng mới.
    Trả về (username, password, StepResult).
    """
    name = "Register"
    username, email = random_user()
    password = "TestPass@123"
    url = f"{BASE_URL}/auth/register/"

    if dry_run:
        print(f"  [DRY-RUN] Would POST {url}")
        return username, password, StepResult(name=name, passed=True, duration=0, detail="dry-run")

    start = time.time()
    try:
        resp = session.post(
            url,
            json={"username": username, "email": email, "password": password},
            timeout=10,
        )
        duration = time.time() - start
        if resp.status_code in (200, 201):
            result = StepResult(name=name, passed=True, duration=duration,
                                detail=f"username={username}")
        else:
            result = StepResult(name=name, passed=False, duration=duration,
                                detail=f"HTTP {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        duration = time.time() - start
        result = StepResult(name=name, passed=False, duration=duration, detail=str(e))

    return username, password, result


def step_login(session: requests.Session, username: str, password: str, dry_run: bool = False):
    """
    Bước 2: Đăng nhập và lấy JWT access token.
    Trả về (access_token, customer_id, StepResult).
    """
    name = "Login"
    url = f"{BASE_URL}/auth/login/"

    if dry_run:
        print(f"  [DRY-RUN] Would POST {url}")
        return "dry-run-token", 1, StepResult(name=name, passed=True, duration=0, detail="dry-run")

    start = time.time()
    try:
        resp = session.post(
            url,
            json={"username": username, "password": password},
            timeout=10,
        )
        duration = time.time() - start
        if resp.status_code == 200:
            data = resp.json()
            access_token = data.get("access") or data.get("access_token") or data.get("token", "")
            customer_id = (
                data.get("customer_id")
                or data.get("user", {}).get("customer_id")
                or data.get("id")
                or 1
            )
            # Gắn token vào session cho các bước tiếp theo
            session.headers.update({"Authorization": f"Bearer {access_token}"})
            result = StepResult(name=name, passed=True, duration=duration,
                                detail=f"customer_id={customer_id}")
        else:
            access_token, customer_id = "", 1
            result = StepResult(name=name, passed=False, duration=duration,
                                detail=f"HTTP {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        duration = time.time() - start
        access_token, customer_id = "", 1
        result = StepResult(name=name, passed=False, duration=duration, detail=str(e))

    return access_token, customer_id, result


def step_get_products(session: requests.Session, dry_run: bool = False):
    """
    Bước 3: Lấy danh sách sản phẩm và chọn sản phẩm đầu tiên.
    Trả về (product_id, StepResult).
    """
    name = "Get Products"
    url = f"{BASE_URL}/products/"

    if dry_run:
        print(f"  [DRY-RUN] Would GET {url}")
        return 1, StepResult(name=name, passed=True, duration=0, detail="dry-run")

    start = time.time()
    try:
        resp = session.get(url, timeout=10)
        duration = time.time() - start
        if resp.status_code == 200:
            data = resp.json()
            # Hỗ trợ cả list trực tiếp và paginated response
            items = data if isinstance(data, list) else data.get("results", data.get("products", []))
            if items:
                product_id = items[0].get("id") or items[0].get("product_id") or 1
                result = StepResult(name=name, passed=True, duration=duration,
                                    detail=f"product_id={product_id}, total={len(items)}")
            else:
                product_id = 1
                result = StepResult(name=name, passed=False, duration=duration,
                                    detail="No products found")
        else:
            product_id = 1
            result = StepResult(name=name, passed=False, duration=duration,
                                detail=f"HTTP {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        duration = time.time() - start
        product_id = 1
        result = StepResult(name=name, passed=False, duration=duration, detail=str(e))

    return product_id, result


def step_add_to_cart(session: requests.Session, customer_id, product_id, dry_run: bool = False):
    """
    Bước 4: Thêm sản phẩm vào giỏ hàng.
    Trả về StepResult.
    """
    name = "Add to Cart"
    url = f"{BASE_URL}/carts/{customer_id}/items/"

    if dry_run:
        print(f"  [DRY-RUN] Would POST {url}")
        return StepResult(name=name, passed=True, duration=0, detail="dry-run")

    start = time.time()
    try:
        resp = session.post(
            url,
            json={"product_id": product_id, "quantity": 1},
            timeout=10,
        )
        duration = time.time() - start
        if resp.status_code in (200, 201):
            result = StepResult(name=name, passed=True, duration=duration,
                                detail=f"product_id={product_id} added")
        else:
            result = StepResult(name=name, passed=False, duration=duration,
                                detail=f"HTTP {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        duration = time.time() - start
        result = StepResult(name=name, passed=False, duration=duration, detail=str(e))

    return result


def step_checkout(session: requests.Session, customer_id, product_id, dry_run: bool = False):
    """
    Bước 5: Tạo đơn hàng.
    Trả về (order_id, StepResult).
    """
    name = "Checkout"
    url = f"{BASE_URL}/orders/"

    if dry_run:
        print(f"  [DRY-RUN] Would POST {url}")
        return 1, StepResult(name=name, passed=True, duration=0, detail="dry-run")

    start = time.time()
    try:
        resp = session.post(
            url,
            json={
                "customer_id": customer_id,
                "items": [{"product_id": product_id, "quantity": 1}],
                "shipping_fee": 0,
            },
            timeout=10,
        )
        duration = time.time() - start
        if resp.status_code in (200, 201):
            data = resp.json()
            order_id = data.get("id") or data.get("order_id") or 1
            result = StepResult(name=name, passed=True, duration=duration,
                                detail=f"order_id={order_id}")
        else:
            order_id = 1
            result = StepResult(name=name, passed=False, duration=duration,
                                detail=f"HTTP {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        duration = time.time() - start
        order_id = 1
        result = StepResult(name=name, passed=False, duration=duration, detail=str(e))

    return order_id, result


def step_pay(session: requests.Session, order_id, dry_run: bool = False):
    """
    Bước 6: Thanh toán đơn hàng.
    Trả về StepResult.
    """
    name = "Pay"
    url = f"{BASE_URL}/payments/"

    if dry_run:
        print(f"  [DRY-RUN] Would POST {url}")
        return StepResult(name=name, passed=True, duration=0, detail="dry-run")

    start = time.time()
    try:
        resp = session.post(
            url,
            json={
                "order_id": order_id,
                "payment_amount": 100000,
                "payment_method_id": 1,
            },
            timeout=10,
        )
        duration = time.time() - start
        if resp.status_code in (200, 201):
            result = StepResult(name=name, passed=True, duration=duration,
                                detail=f"order_id={order_id} payment initiated")
        else:
            result = StepResult(name=name, passed=False, duration=duration,
                                detail=f"HTTP {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        duration = time.time() - start
        result = StepResult(name=name, passed=False, duration=duration, detail=str(e))

    return result


def step_poll_payment(session: requests.Session, order_id, dry_run: bool = False):
    """
    Bước 7: Poll trạng thái thanh toán tối đa MAX_POLL lần.
    Pass khi payment_status == "completed".
    Trả về StepResult.
    """
    name = "Poll Payment"
    url = f"{BASE_URL}/payments/?order_id={order_id}"

    if dry_run:
        print(f"  [DRY-RUN] Would GET {url}")
        return StepResult(name=name, passed=True, duration=0, detail="dry-run")

    start = time.time()
    try:
        for attempt in range(MAX_POLL):
            resp = session.get(url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                # Hỗ trợ cả list và paginated response
                items = data if isinstance(data, list) else data.get("results", [])
                if items:
                    payment_status = items[0].get("payment_status") or items[0].get("status", "")
                    if payment_status == "completed":
                        duration = time.time() - start
                        return StepResult(name=name, passed=True, duration=duration,
                                          detail=f"payment_status=completed (attempt {attempt + 1})")
            if attempt < MAX_POLL - 1:
                time.sleep(POLL_INTERVAL)
        duration = time.time() - start
        result = StepResult(name=name, passed=False, duration=duration,
                            detail=f"Timeout after {MAX_POLL} attempts")
    except Exception as e:
        duration = time.time() - start
        result = StepResult(name=name, passed=False, duration=duration, detail=str(e))

    return result


def step_poll_shipping(session: requests.Session, order_id, dry_run: bool = False):
    """
    Bước 8: Poll trạng thái giao hàng tối đa MAX_POLL lần.
    Pass khi status in ["shipped", "processing", "delivered"].
    Trả về StepResult.
    """
    name = "Poll Shipping"
    url = f"{BASE_URL}/shippings/?order_id={order_id}"
    valid_statuses = {"shipped", "processing", "delivered"}

    if dry_run:
        print(f"  [DRY-RUN] Would GET {url}")
        return StepResult(name=name, passed=True, duration=0, detail="dry-run")

    start = time.time()
    try:
        for attempt in range(MAX_POLL):
            resp = session.get(url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                items = data if isinstance(data, list) else data.get("results", [])
                if items:
                    shipping_status = items[0].get("status", "")
                    if shipping_status in valid_statuses:
                        duration = time.time() - start
                        return StepResult(name=name, passed=True, duration=duration,
                                          detail=f"status={shipping_status} (attempt {attempt + 1})")
            if attempt < MAX_POLL - 1:
                time.sleep(POLL_INTERVAL)
        duration = time.time() - start
        result = StepResult(name=name, passed=False, duration=duration,
                            detail=f"Timeout after {MAX_POLL} attempts")
    except Exception as e:
        duration = time.time() - start
        result = StepResult(name=name, passed=False, duration=duration, detail=str(e))

    return result

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="E2E test script cho hệ thống e-commerce")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Bỏ qua tất cả HTTP calls, chỉ in kế hoạch thực thi",
    )
    args = parser.parse_args()
    dry_run = args.dry_run

    if dry_run:
        print(f"\n{BOLD}[DRY-RUN MODE] Không thực hiện HTTP calls thực tế.{RESET}\n")
    else:
        print(f"\n{BOLD}E2E Test – BASE_URL={BASE_URL}{RESET}\n")

    session = requests.Session()
    results = []

    # ── Bước 1: Đăng ký ──────────────────────────────────────────────────────
    username, password, reg_result = step_register(session, dry_run=dry_run)
    results.append(reg_result)
    print_step(reg_result)
    if not reg_result.passed and not dry_run:
        print_summary(results)
        sys.exit(1)

    # ── Bước 2: Đăng nhập ────────────────────────────────────────────────────
    access_token, customer_id, login_result = step_login(session, username, password, dry_run=dry_run)
    results.append(login_result)
    print_step(login_result)
    if not login_result.passed and not dry_run:
        print_summary(results)
        sys.exit(1)

    # ── Bước 3: Lấy sản phẩm ─────────────────────────────────────────────────
    product_id, products_result = step_get_products(session, dry_run=dry_run)
    results.append(products_result)
    print_step(products_result)
    if not products_result.passed and not dry_run:
        print_summary(results)
        sys.exit(1)

    # ── Bước 4: Thêm vào giỏ hàng ────────────────────────────────────────────
    cart_result = step_add_to_cart(session, customer_id, product_id, dry_run=dry_run)
    results.append(cart_result)
    print_step(cart_result)
    if not cart_result.passed and not dry_run:
        print_summary(results)
        sys.exit(1)

    # ── Bước 5: Tạo đơn hàng ─────────────────────────────────────────────────
    order_id, checkout_result = step_checkout(session, customer_id, product_id, dry_run=dry_run)
    results.append(checkout_result)
    print_step(checkout_result)
    if not checkout_result.passed and not dry_run:
        print_summary(results)
        sys.exit(1)

    # ── Bước 6: Thanh toán ────────────────────────────────────────────────────
    pay_result = step_pay(session, order_id, dry_run=dry_run)
    results.append(pay_result)
    print_step(pay_result)
    if not pay_result.passed and not dry_run:
        print_summary(results)
        sys.exit(1)

    # ── Bước 7: Poll trạng thái thanh toán ───────────────────────────────────
    poll_payment_result = step_poll_payment(session, order_id, dry_run=dry_run)
    results.append(poll_payment_result)
    print_step(poll_payment_result)
    if not poll_payment_result.passed and not dry_run:
        print_summary(results)
        sys.exit(1)

    # ── Bước 8: Poll trạng thái giao hàng ────────────────────────────────────
    poll_shipping_result = step_poll_shipping(session, order_id, dry_run=dry_run)
    results.append(poll_shipping_result)
    print_step(poll_shipping_result)

    # ── Tổng kết ──────────────────────────────────────────────────────────────
    print_summary(results)

    all_passed = all(r.passed for r in results)
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
