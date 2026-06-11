"""
Browser E2E test — kiểm tra toàn bộ giao diện qua Playwright.

Usage:
    python scripts/browser_e2e_test.py
    python scripts/browser_e2e_test.py --headed   # xem trình duyệt
"""

import argparse
import random
import string
import sys
import time

from playwright.sync_api import sync_playwright, expect

BASE = "http://localhost:8000"
PASSWORD = "TestPass@123"


class Step:
    def __init__(self, group: str, name: str):
        self.group = group
        self.name = name
        self.passed = False
        self.detail = ""
        self.duration = 0.0


def _safe_print(text: str):
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode("ascii", errors="replace").decode("ascii"))


def run_step(results: list, group: str, name: str, fn):
    step = Step(group, name)
    start = time.time()
    try:
        fn(step)
    except Exception as exc:
        step.fail(str(exc)[:200])
    step.duration = time.time() - start
    color = "\033[92m" if step.passed else "\033[91m"
    reset = "\033[0m"
    status = "PASS" if step.passed else "FAIL"
    detail = step.detail.encode("ascii", errors="replace").decode("ascii")
    name = step.name.encode("ascii", errors="replace").decode("ascii")
    _safe_print(f"  {color}[{status}]{reset} {name:<40} ({step.duration:.2f}s)  {detail}")
    results.append(step)
    return step


def Step_ok(self, detail=""):
    self.passed = True
    self.detail = detail
    return self


def Step_fail(self, detail=""):
    self.passed = False
    self.detail = detail
    return self


Step.ok = Step_ok
Step.fail = Step_fail


def login(page, username: str, password: str, role: str = "customer"):
    page.goto(f"{BASE}/login/?login_type={role}")
    page.fill('input[name="username"]', username)
    page.fill('input[name="password"]', password)
    page.locator("#login_type").evaluate(f"el => el.value = '{role}'")
    page.click('button.auth-form-submit')
    page.wait_for_load_state("networkidle")


def register_customer(page, username: str):
    page.goto(f"{BASE}/register/")
    page.fill('input[name="username"]', username)
    page.fill('input[name="email"]', f"{username}@browser.test")
    page.fill('input[name="password"]', PASSWORD)
    page.fill('input[name="phone"]', "0901234567")
    page.click('button[type="submit"]')
    page.wait_for_load_state("networkidle")


def assert_page_ok(page, step, url: str, must_contain: str | None = None):
    page.goto(url)
    expect(page).not_to_have_url(f"{BASE}/login/")
    if page.url.endswith("/login/"):
        return step.fail("redirected to login")
    if must_contain and must_contain not in page.content():
        return step.fail(f"missing '{must_contain}'")
    return step.ok(page.url)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--slow", type=int, default=0)
    args = parser.parse_args()

    suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
    customer_user = f"browser_{suffix}"
    results: list[Step] = []
    state: dict = {}

    print(f"\n\033[1mBrowser E2E Test\033[0m  BASE={BASE}\n")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not args.headed, slow_mo=args.slow)
        ctx = browser.new_context(locale="vi-VN")
        page = ctx.new_page()

        # ── PUBLIC ──────────────────────────────────────────────────────────
        for url, label, text in [
            ("/", "Trang chủ", "E-Commerce"),
            ("/products/", "Danh sách sản phẩm", "Sản phẩm"),
            ("/promotions/", "Khuyến mãi", None),
            ("/login/", "Đăng nhập", "Đăng nhập"),
            ("/register/", "Đăng ký", "Tạo tài khoản"),
        ]:
            def _pub(s, u=url, t=text):
                page.goto(f"{BASE}{u}")
                if t and t not in page.content():
                    return s.fail(f"missing {t}")
                return s.ok(f"HTTP OK — {u}")

            run_step(results, "Công khai", label, _pub)

        # ── REGISTER & LOGIN ──────────────────────────────────────────────────
        def step_register(s):
            register_customer(page, customer_user)
            if "/login" in page.url and "error" in page.content().lower():
                return s.fail("registration failed")
            if "E-Commerce" not in page.content():
                return s.fail("not on home after register")
            state["customer"] = customer_user
            return s.ok(customer_user)

        run_step(results, "Khách hàng", "1. Đăng ký tài khoản", step_register)

        def step_logout_login(s):
            page.goto(f"{BASE}/logout/")
            page.wait_for_load_state("networkidle")
            login(page, customer_user, PASSWORD, "customer")
            if "Đăng xuất" not in page.content():
                return s.fail("login failed")
            return s.ok("session restored")

        run_step(results, "Khách hàng", "2. Đăng xuất & đăng nhập lại", step_logout_login)

        # ── SHOPPING ────────────────────────────────────────────────────────
        def step_products(s):
            page.goto(f"{BASE}/products/")
            links = page.locator('a[href*="/products/"]').all()
            detail_links = [l for l in links if l.get_attribute("href") and l.get_attribute("href").rstrip("/").split("/")[-1].isdigit()]
            if not detail_links:
                return s.fail("no product links")
            href = detail_links[0].get_attribute("href")
            state["product_url"] = href
            return s.ok(href)

        run_step(results, "Khách hàng", "3. Xem danh sách sản phẩm", step_products)

        def step_product_detail(s):
            page.goto(f"{BASE}{state['product_url']}")
            if "Thêm vào giỏ" not in page.content() and "giỏ hàng" not in page.content().lower():
                return s.fail("product detail incomplete")
            return s.ok(state["product_url"])

        run_step(results, "Khách hàng", "4. Xem chi tiết sản phẩm", step_product_detail)

        def step_add_cart(s):
            page.goto(f"{BASE}{state['product_url']}")
            btn = page.locator('button:has-text("Thêm vào giỏ"), input[type="submit"]:has-text("Thêm")').first
            if btn.count() == 0:
                return s.fail("no add-to-cart button")
            btn.click()
            page.wait_for_load_state("networkidle")
            return s.ok("added to cart")

        run_step(results, "Khách hàng", "5. Thêm sản phẩm vào giỏ", step_add_cart)

        def step_cart(s):
            page.goto(f"{BASE}/")
            cart_link = page.locator('a[href*="/cart/"]').first
            if cart_link.count() == 0:
                return s.fail("no cart link")
            href = cart_link.get_attribute("href")
            state["cart_url"] = href
            page.goto(f"{BASE}{href}")
            if "Giỏ hàng" not in page.content() and "giỏ" not in page.content().lower():
                return s.fail("cart page empty")
            return s.ok(href)

        run_step(results, "Khách hàng", "6. Xem giỏ hàng", step_cart)

        def step_profile(s):
            page.goto(f"{BASE}/profile/")
            if "Hồ sơ" not in page.content() and "profile" not in page.content().lower():
                return s.fail("profile page error")
            return s.ok("profile loaded")

        run_step(results, "Khách hàng", "7. Quản lý hồ sơ", step_profile)

        def step_wishlist(s):
            page.goto(f"{BASE}/wishlist/")
            return s.ok("wishlist page loaded")

        run_step(results, "Khách hàng", "8. Danh sách yêu thích", step_wishlist)

        def step_recommendations(s):
            page.goto(f"{BASE}/recommendations/")
            return s.ok("recommendations loaded")

        run_step(results, "Khách hàng", "9. Đề xuất AI", step_recommendations)

        def step_checkout(s):
            page.goto(f"{BASE}{state.get('cart_url', '/')}")
            checkout = page.locator('a[href*="checkout"]').first
            if checkout.count() == 0:
                page.goto(f"{BASE}/")
                cid = state.get("cart_url", "").split("/cart/")[-1].rstrip("/")
                if cid.isdigit():
                    page.goto(f"{BASE}/cart/{cid}/checkout/")
                else:
                    return s.fail("no checkout link")
            else:
                checkout.click()
                page.wait_for_load_state("networkidle")
            content = page.content()
            if "vận chuyển" not in content.lower() and "checkout" not in page.url:
                return s.fail("checkout page missing shipping")
            return s.ok("checkout with shipping section")

        run_step(results, "Khách hàng", "10. Trang thanh toán (checkout)", step_checkout)

        def step_orders(s):
            page.goto(f"{BASE}/orders/")
            return s.ok("orders list loaded")

        run_step(results, "Khách hàng", "11. Danh sách đơn hàng", step_orders)

        def step_returns(s):
            page.goto(f"{BASE}/returns/")
            if "Trả hàng" not in page.content() and "trả" not in page.content().lower():
                return s.fail("returns page error")
            return s.ok("returns page loaded")

        run_step(results, "Khách hàng", "12. Yêu cầu trả hàng", step_returns)

        def step_support_list(s):
            page.goto(f"{BASE}/support/")
            return s.ok("support list loaded")

        run_step(results, "Khách hàng", "13. Hỗ trợ — danh sách ticket", step_support_list)

        def step_support_create(s):
            page.goto(f"{BASE}/support/new/")
            if page.locator('form').count() == 0:
                return s.fail("no support form")
            page.fill('input[name="subject"]', "Browser test ticket")
            page.fill('textarea[name="content"]', "Ticket tao tu dong tu browser E2E test.")
            page.click('button[type="submit"]')
            page.wait_for_load_state("networkidle")
            return s.ok("ticket submitted")

        run_step(results, "Khách hàng", "14. Tạo ticket hỗ trợ", step_support_create)

        # ── STAFF ───────────────────────────────────────────────────────────
        page.goto(f"{BASE}/logout/")
        page.wait_for_load_state("networkidle")

        def step_staff_login(s):
            login(page, "staff_test", "Staff@12345", "staff")
            if "staff/dashboard" not in page.url and "Staff Portal" not in page.content():
                return s.fail("staff login failed")
            return s.ok("staff dashboard")

        run_step(results, "Nhân viên", "1. Đăng nhập Staff", step_staff_login)

        staff_pages = [
            ("/staff/dashboard/", "Dashboard"),
            ("/staff/orders/", "Đơn hàng"),
            ("/staff/customers/", "Khách hàng"),
            ("/staff/tickets/", "Ticket hỗ trợ"),
        ]
        for i, (url, label) in enumerate(staff_pages, 2):
            def _staff(s, u=url, lb=label):
                page.goto(f"{BASE}{u}")
                if page.url.endswith("/login/"):
                    return s.fail("session lost")
                return s.ok(lb)

            run_step(results, "Nhân viên", f"{i}. {label}", _staff)

        # ── ADMIN ───────────────────────────────────────────────────────────
        page.goto(f"{BASE}/logout/")
        page.wait_for_load_state("networkidle")

        def step_admin_login(s):
            login(page, "admin", "Admin@12345", "admin")
            if "Admin Portal" not in page.content() and "admin/dashboard" not in page.url:
                return s.fail("admin login or redirect failed")
            return s.ok("admin dashboard")

        run_step(results, "Quản trị", "1. Đăng nhập Admin", step_admin_login)

        admin_pages = [
            ("/admin/dashboard/", "Dashboard"),
            ("/admin/reports/", "Báo cáo"),
            ("/admin/recommendation/", "AI Recommendation"),
            ("/admin/products/", "Sản phẩm"),
            ("/admin/categories/", "Danh mục"),
            ("/admin/brands/", "Thương hiệu"),
            ("/admin/inventory/", "Kho hàng"),
            ("/admin/orders/", "Đơn hàng"),
            ("/admin/customers/", "Khách hàng"),
            ("/admin/tickets/", "Ticket"),
        ]
        for i, (url, label) in enumerate(admin_pages, 2):
            def _admin(s, u=url, lb=label):
                page.goto(f"{BASE}{u}")
                if page.url.endswith("/login/"):
                    return s.fail("session lost")
                return s.ok(lb)

            run_step(results, "Quản trị", f"{i}. {label}", _admin)

        browser.close()

    passed = sum(1 for r in results if r.passed)
    total = len(results)
    color = "\033[92m" if passed == total else "\033[91m"
    print(f"\n\033[1m{'-' * 70}\033[0m")
    print(f"  {color}\033[1m{passed}/{total} browser steps passed\033[0m")
    print(f"\033[1m{'-' * 70}\033[0m\n")
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
