"""Mo trinh duyet headed de demo localhost."""
import time
from playwright.sync_api import sync_playwright

BASE = "http://localhost:8000"
PAGES = ["/", "/products/", "/promotions/", "/login/"]

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, slow_mo=400)
    page = browser.new_page()
    for path in PAGES:
        page.goto(f"{BASE}{path}")
        page.wait_for_load_state("networkidle")
        time.sleep(2)
    print("Browser demo done. Close the browser window when finished.")
    time.sleep(30)
    browser.close()
