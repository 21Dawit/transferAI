"""
find_school_ids.py — Look up ASSIST.org institution IDs for new schools

Run once to find IDs, then add them to assist_scraper.py SCHOOL_IDS.

Usage:
    python services/scrapers/find_school_ids.py
    python services/scrapers/find_school_ids.py --search "berkeley"
"""

import argparse
import requests

BASE_URL   = "https://assist.org"
USER_AGENT = "TransferAI-StudentResearch/1.0"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--search", type=str, default="", help="Filter by name")
    args = parser.parse_args()

    s = requests.Session()
    s.headers.update({"User-Agent": USER_AGENT, "Accept": "application/json"})
    s.get(BASE_URL, timeout=15)
    token = s.cookies.get("X-XSRF-TOKEN")
    if token:
        s.headers["X-XSRF-TOKEN"] = token

    r = s.get(f"{BASE_URL}/api/institutions", timeout=20)
    r.raise_for_status()
    institutions = r.json()

    query = args.search.lower()
    for inst in institutions:
        name = inst.get("names", [{}])[0].get("name", "")
        iid  = inst.get("id")
        if not query or query in name.lower():
            print(f"{iid:>6}  {name}")

if __name__ == "__main__":
    main()
