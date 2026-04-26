"""
debug_elumen.py — Probe the Elumen API to find course data endpoints

Run this once to discover the API, then we'll update the real scraper.
"""
import requests, json

BASE = "https://deanza.elumenapp.com"
YEAR = "2025-2026"

s = requests.Session()
s.headers.update({
    "User-Agent": "TransferAI-StudentResearch/1.0",
    "Accept": "application/json, text/html, */*",
    "Referer": f"{BASE}/catalog/{YEAR}/accounting-courses",
})

# 1. Fetch the raw HTML of a dept page and print the first 3000 chars
print("=== RAW HTML (first 3000 chars) ===")
r = s.get(f"{BASE}/catalog/{YEAR}/accounting-courses", timeout=20)
print(r.text[:3000])
print("\n\n")

# 2. Try common Elumen API endpoints
CANDIDATES = [
    f"{BASE}/api/catalog/courses?year={YEAR}",
    f"{BASE}/api/catalog/{YEAR}/courses",
    f"{BASE}/api/courses?catalog={YEAR}",
    f"{BASE}/catalog/api/courses",
    f"{BASE}/api/v1/courses",
]

print("=== API PROBE ===")
for url in CANDIDATES:
    try:
        r2 = s.get(url, timeout=10)
        print(f"{r2.status_code}  {url}")
        if r2.status_code == 200 and "application/json" in r2.headers.get("Content-Type", ""):
            print("  --> JSON found! First 500 chars:")
            print(r2.text[:500])
    except Exception as e:
        print(f"ERR  {url}  ({e})")
