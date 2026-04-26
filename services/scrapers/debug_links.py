"""
debug_links.py — Dump all rendered links from the Elumen page to find dept slugs
"""
from playwright.sync_api import sync_playwright
import time

BASE = "https://deanza.elumenapp.com"
ENTRY = f"{BASE}/catalog/2025-2026/accounting-courses"

with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto(ENTRY, wait_until="networkidle", timeout=30000)
    time.sleep(3)

    # Scroll down in the page to trigger lazy nav rendering
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    time.sleep(1)

    # Also try scrolling any scrollable sidebar
    page.evaluate("""
        document.querySelectorAll('*').forEach(el => {
            if (el.scrollHeight > el.clientHeight && el.clientHeight > 100) {
                el.scrollTop = el.scrollHeight;
            }
        });
    """)
    time.sleep(1)

    # Dump every unique link
    print("=== ALL LINKS IN RENDERED PAGE ===")
    links = page.query_selector_all("a[href]")
    seen = set()
    for a in links:
        href = a.get_attribute("href") or ""
        text = a.inner_text().strip()[:60]
        if href not in seen:
            seen.add(href)
            print(f"{href:<60}  |  {text}")

    browser.close()
