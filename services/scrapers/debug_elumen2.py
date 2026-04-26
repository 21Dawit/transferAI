"""
debug_elumen2.py — Inspect the /catalog/api/courses endpoint
"""
import requests, json

BASE = "https://deanza.elumenapp.com"
YEAR = "2025-2026"

s = requests.Session()
s.headers.update({
    "User-Agent": "TransferAI-StudentResearch/1.0",
    "Accept": "application/json, */*",
    "Referer": f"{BASE}/catalog/{YEAR}/accounting-courses",
})

url = f"{BASE}/catalog/api/courses"
r = s.get(url, timeout=20)

print(f"Status:       {r.status_code}")
print(f"Content-Type: {r.headers.get('Content-Type')}")
print()

try:
    data = r.json()
    print(f"Type: {type(data)}")
    if isinstance(data, list):
        print(f"Count: {len(data)}")
        print("First item:")
        print(json.dumps(data[0], indent=2))
        print("Second item:")
        print(json.dumps(data[1], indent=2))
    elif isinstance(data, dict):
        print("Keys:", list(data.keys()))
        print(json.dumps(data, indent=2)[:2000])
except Exception as e:
    print("Not JSON:", e)
    print(r.text[:2000])
