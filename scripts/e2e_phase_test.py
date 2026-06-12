"""
E2E test — luồng khách hàng đầy đủ (Phase 1-2) qua microservices.

Usage:
    python scripts/e2e_phase_test.py
"""

import os
import sys
import time
import random
import string
import hmac
import hashlib
import requests

AUTH_URL = os.environ.get("AUTH_URL", "http://localhost:8012")
USER_URL = os.environ.get("USER_URL", "http://localhost:8001")
PRODUCT_URL = os.environ.get("PRODUCT_URL", "http://localhost:8002")
CART_URL = os.environ.get("CART_URL", "http://localhost:8003")
ORDER_URL = os.environ.get("ORDER_URL", "http://localhost:8007")
PAY_URL = os.environ.get("PAY_URL", "http://localhost:8015")
SHIP_URL = os.environ.get("SHIP_URL", "http://localhost:8009")
PROMO_URL = os.environ.get("PROMO_URL", "http://localhost:8018")
GATEWAY_URL = os.environ.get("GATEWAY_URL", "http://localhost:8000")

INTERNAL_TOKEN = os.environ.get("INTERNAL_TOKEN", "internal-dev-token")
INTERNAL_SIGNING_SECRET = os.environ.get("INTERNAL_SIGNING_SECRET", "internal-signing-secret")

GREEN, RED, BOLD, RESET = "\033[92m", "\033[91m", "\033[1m", "\033[0m"


def _internal_headers(body=""):
    ts = str(int(time.time()))
    sig = hmac.new(
        INTERNAL_SIGNING_SECRET.encode(),
        f"{ts}.{body}".encode(),
        hashlib.sha256,
    ).hexdigest()
    return {
        "X-Internal-Token": INTERNAL_TOKEN,
        "X-Service-Name": "api-gateway",
        "X-Timestamp": ts,
        "X-Signature": sig,
        "Content-Type": "application/json",
    }


def _auth_headers(token, entity_id=None, user_id=None, roles=None):
    roles = roles or ["CUSTOMER"]
    uid = str(user_id or entity_id or "")
    return {
        "Authorization": f"Bearer {token}",
        "X-User-Id": uid,
        "X-Roles": ",".join(r.lower() for r in roles),
        "X-User-Role": ",".join(r.lower() for r in roles),
        "X-Entity-Id": str(entity_id or ""),
    }


class Step:
    def __init__(self, name):
        self.name = name
        self.passed = False
        self.detail = ""
        self.duration = 0

    def ok(self, detail=""):
        self.passed = True
        self.detail = detail
        return self

    def fail(self, detail=""):
        self.passed = False
        self.detail = detail
        return self


def _safe_print(text):
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode("ascii", errors="replace").decode("ascii"))


def run_step(name, fn):
    step = Step(name)
    start = time.time()
    try:
        fn(step)
    except Exception as e:
        step.fail(str(e))
    step.duration = time.time() - start
    color = GREEN if step.passed else RED
    detail = step.detail.encode("ascii", errors="replace").decode("ascii")
    _safe_print(f"  {color}{'[PASS]' if step.passed else '[FAIL]'}{RESET} {step.name:<32} ({step.duration:.2f}s)  {detail}")
    return step


def main():
    print(f"\n{BOLD}E2E Phase Test{RESET}")
    print(f"  Gateway={GATEWAY_URL}  Order={ORDER_URL}  Ship={SHIP_URL}\n")

    results = []
    suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
    username = f"e2e_{suffix}"
    password = "TestPass@123"
    state = {}

    def step_register(s):
        r = requests.post(
            f"{AUTH_URL}/auth/register/",
            json={"username": username, "email": f"{username}@test.com", "password": password},
            timeout=15,
        )
        if r.status_code not in (200, 201):
            return s.fail(f"HTTP {r.status_code}: {r.text[:200]}")
        s.ok(f"user={username}")

    results.append(run_step("1. Register", step_register))

    def step_login(s):
        r = requests.post(
            f"{AUTH_URL}/auth/login/",
            json={"username": username, "password": password, "role": "customer"},
            timeout=15,
        )
        if r.status_code != 200:
            return s.fail(f"HTTP {r.status_code}: {r.text[:200]}")
        data = r.json()
        state["token"] = data["access"]
        state["entity_id"] = int(data["user"].get("entity_id") or 0)
        state["auth_user_id"] = data["user"].get("id")
        if not state["entity_id"]:
            return s.fail("No entity_id in login response")
        s.ok(f"entity_id={state['entity_id']}")

    results.append(run_step("2. Login", step_login))
    if not results[-1].passed:
        return _summary(results)

    headers = _auth_headers(state["token"], state["entity_id"], state.get("auth_user_id"))

    def step_products(s):
        r = requests.get(f"{PRODUCT_URL}/products/", headers=headers, timeout=15)
        if r.status_code != 200:
            return s.fail(f"HTTP {r.status_code}")
        items = r.json() if isinstance(r.json(), list) else r.json().get("results", [])
        if not items:
            return s.fail("No products")
        state["product_id"] = items[0]["id"]
        state["unit_price"] = float(items[0].get("price", 100000))
        s.ok(f"product_id={state['product_id']}, count={len(items)}")

    results.append(run_step("3. List Products", step_products))
    if not results[-1].passed:
        return _summary(results)

    def step_cart(s):
        cid = state["entity_id"]
        r = requests.post(
            f"{CART_URL}/carts/{cid}/items/",
            headers=headers,
            json={"product_id": state["product_id"], "quantity": 1, "unit_price": state["unit_price"]},
            timeout=15,
        )
        if r.status_code not in (200, 201):
            return s.fail(f"HTTP {r.status_code}: {r.text[:200]}")
        s.ok("item added")

    results.append(run_step("4. Add to Cart", step_cart))

    def step_address(s):
        uid = state["auth_user_id"]
        body = {
            "recipient_name": "E2E User",
            "phone": "0901234567",
            "address_line": "123 Test St",
            "city": "Hà Nội",
            "country": "VN",
            "postal_code": "100000",
            "is_default": True,
        }
        import json
        body_str = json.dumps(body, separators=(",", ":"), sort_keys=True)
        r = requests.post(
            f"{USER_URL}/internal/users/{uid}/addresses/",
            data=body_str.encode(),
            headers=_internal_headers(body_str),
            timeout=15,
        )
        if r.status_code not in (200, 201):
            return s.fail(f"HTTP {r.status_code}: {r.text[:200]}")
        s.ok("address created")

    results.append(run_step("5. Add Address", step_address))

    def step_shipping_methods(s):
        r = requests.get(f"{SHIP_URL}/api/methods/", headers=headers, timeout=15)
        if r.status_code != 200:
            return s.fail(f"HTTP {r.status_code}: {r.text[:200]}")
        items = r.json() if isinstance(r.json(), list) else r.json().get("results", [])
        if not items:
            return s.fail("No shipping methods")
        state["shipping_method_id"] = items[0]["id"]
        s.ok(f"method={items[0].get('method_name')}")

    results.append(run_step("6. Shipping Methods", step_shipping_methods))

    def step_shipping_fee(s):
        import json
        body = {
            "shipping_method_id": state["shipping_method_id"],
            "total_weight": 1.0,
            "distance_km": 5.0,
        }
        body_str = json.dumps(body, separators=(",", ":"), sort_keys=True)
        h = {**_internal_headers(body_str), **headers}
        r = requests.post(
            f"{SHIP_URL}/api/shipping/calculate-fee/",
            data=body_str.encode(),
            headers=h,
            timeout=15,
        )
        if r.status_code != 200:
            return s.fail(f"HTTP {r.status_code}: {r.text[:200]}")
        state["shipping_fee"] = r.json().get("shipping_fee", 0)
        if state["shipping_fee"] <= 0:
            return s.fail("Invalid shipping fee")
        s.ok(f"fee={state['shipping_fee']}")

    results.append(run_step("7. Dynamic Shipping Fee", step_shipping_fee))

    def step_voucher(s):
        r = requests.get(f"{PROMO_URL}/api/promotions/vouchers/", timeout=15)
        code = None
        if r.status_code == 200:
            items = r.json() if isinstance(r.json(), list) else r.json().get("results", [])
            if items:
                code = items[0].get("code")
        if not code:
            s.ok("no voucher seeded (skipped)")
            state["promotion_code"] = None
            return
        import json
        body = {"code": code, "order_amount": state["unit_price"]}
        body_str = json.dumps(body, separators=(",", ":"), sort_keys=True)
        r2 = requests.post(
            f"{PROMO_URL}/api/promotions/apply-voucher/",
            data=body_str.encode(),
            headers={"Content-Type": "application/json"},
            timeout=15,
        )
        if r2.status_code != 200:
            return s.fail(f"apply-voucher HTTP {r2.status_code}: {r2.text[:200]}")
        state["promotion_code"] = code
        state["discount"] = r2.json().get("discount_amount", 0)
        s.ok(f"code={code}, discount={state['discount']}")

    results.append(run_step("8. Apply Voucher", step_voucher))

    def step_create_order(s):
        import json
        payload = {
            "customer_id": state["entity_id"],
            "items": [{
                "product_id": state["product_id"],
                "quantity": 1,
                "unit_price": state["unit_price"],
                "product_name": "E2E Product",
            }],
            "shipping_fee": state.get("shipping_fee", 30000),
            "shipping_method_id": state.get("shipping_method_id"),
            "shipping_address": {
                "recipient_name": "E2E User",
                "phone": "0901234567",
                "address_line": "123 Test Street",
                "city": "Hà Nội",
                "country": "Việt Nam",
                "postal_code": "100000",
                "shipping_method_id": state.get("shipping_method_id"),
                "distance_km": 5.0,
            },
            "promotion_code": state.get("promotion_code"),
        }
        body_str = json.dumps(payload, separators=(",", ":"), sort_keys=True)
        r = requests.post(
            f"{ORDER_URL}/orders/",
            data=body_str.encode(),
            headers={**headers, "Content-Type": "application/json"},
            timeout=30,
        )
        if r.status_code not in (200, 201):
            return s.fail(f"HTTP {r.status_code}: {r.text[:300]}")
        state["order_id"] = r.json()["id"]
        s.ok(f"order_id={state['order_id']}, total={r.json().get('total_amount')}")

    results.append(run_step("9. Create Order", step_create_order))
    if not results[-1].passed:
        return _summary(results)

    def step_payment(s):
        import json
        body = {
            "order_id": state["order_id"],
            "payment_amount": state["unit_price"] + state.get("shipping_fee", 0),
            "payment_method_id": 1,
        }
        body_str = json.dumps(body, separators=(",", ":"), sort_keys=True)
        r = requests.post(
            f"{PAY_URL}/payments/",
            data=body_str.encode(),
            headers={**headers, "Content-Type": "application/json"},
            timeout=15,
        )
        if r.status_code not in (200, 201):
            return s.fail(f"HTTP {r.status_code}: {r.text[:200]}")
        s.ok("payment recorded")

    results.append(run_step("10. Payment (COD)", step_payment))

    def step_wait_shipping(s):
        deadline = time.time() + 45
        data = None
        while time.time() < deadline:
            r = requests.get(
                f"{SHIP_URL}/api/shippings/order/{state['order_id']}/",
                headers=headers,
                timeout=15,
            )
            if r.status_code == 200:
                data = r.json()
                if data.get("tracking_number") and data.get("address") and data.get("statuses"):
                    break
            time.sleep(2)
        if not data:
            return s.fail("Shipping record not created within timeout")
        if not data.get("address"):
            return s.fail("Shipping address missing in DB")
        if not data.get("statuses"):
            return s.fail("Shipping timeline missing in DB")
        tn = data.get("tracking_number", "")
        s.ok(f"tracking={tn}, status={data.get('status')}")

    results.append(run_step("11. Auto Shipping Record", step_wait_shipping))

    def _gateway_session_login(session):
        r1 = session.get(f"{GATEWAY_URL}/login/", timeout=15)
        if r1.status_code != 200:
            return False, f"login page HTTP {r1.status_code}"
        csrf = session.cookies.get("csrftoken", "")
        if not csrf:
            import re
            m = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', r1.text)
            csrf = m.group(1) if m else ""
        r2 = session.post(
            f"{GATEWAY_URL}/login/",
            data={
                "username": username,
                "password": password,
                "login_type": "customer",
                "csrfmiddlewaretoken": csrf,
            },
            headers={"Referer": f"{GATEWAY_URL}/login/"},
            timeout=15,
            allow_redirects=True,
        )
        if r2.status_code not in (200, 302):
            return False, f"login POST HTTP {r2.status_code}"
        return True, "ok"

    def step_gateway_returns_page(s):
        session = requests.Session()
        ok, msg = _gateway_session_login(session)
        if not ok:
            return s.fail(msg)
        r3 = session.get(f"{GATEWAY_URL}/returns/", timeout=15)
        if r3.status_code != 200:
            return s.fail(f"returns page HTTP {r3.status_code}")
        s.ok("returns page accessible")

    results.append(run_step("13. Gateway Returns Page", step_gateway_returns_page))

    def step_gateway_checkout_page(s):
        requests.post(
            f"{CART_URL}/carts/{state['entity_id']}/items/",
            headers=headers,
            json={"product_id": state["product_id"], "quantity": 1, "unit_price": state["unit_price"]},
            timeout=15,
        )
        session = requests.Session()
        ok, msg = _gateway_session_login(session)
        if not ok:
            return s.fail(msg)
        cid = state["entity_id"]
        r = session.get(f"{GATEWAY_URL}/cart/{cid}/checkout/", timeout=15)
        if r.status_code != 200:
            return s.fail(f"HTTP {r.status_code}")
        html = r.text
        if "shipping_method_id" not in html and "Ph\u01b0\u01a1ng th\u1ee9c" not in html and "v\u1eadn chuy\u1ec3n" not in html.lower():
            return s.fail("checkout missing shipping section")
        if "data-fee" in html or "Ph\u00ed v\u1eadn chuy\u1ec3n" in html or "T\u1ed5ng thanh to\u00e1n" in html:
            s.ok("checkout shows dynamic shipping UI")
        else:
            s.ok("checkout page loaded")

    results.append(run_step("14. Gateway Checkout Page", step_gateway_checkout_page))

    return _summary(results)


def _summary(results):
    print(f"\n{BOLD}{'-' * 60}{RESET}")
    passed = sum(1 for r in results if r.passed)
    total = len(results)
    color = GREEN if passed == total else RED
    print(f"  {color}{BOLD}{passed}/{total} steps passed{RESET}")
    print(f"{BOLD}{'-' * 60}{RESET}\n")
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
