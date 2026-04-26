"""
retry_failed.py — Retry ASSIST scraping with longer delays for rate-limited requests

Run after batch_assist_scraper.py to fill in the gaps.

Usage:
    python services/scrapers/retry_failed.py
"""

import json
import sys
import time
from pathlib import Path

import requests

BASE_URL   = "https://assist.org"
USER_AGENT = "TransferAI-StudentResearch/1.0 (student research project)"
OUTPUT_DIR = Path(__file__).resolve().parents[2] / "data" / "assist_raw"

ACADEMIC_YEAR_IDS = {"2023-2024": 74}
DE_ANZA_ID        = 113

TARGET_SCHOOLS = {
    "UC Davis":         89,
    "UC Berkeley":      79,
    "UCLA":             117,
    "UC San Diego":     7,
    "UC Santa Barbara": 128,
    "UC Irvine":        120,
    "UC Santa Cruz":    132,
    "UC Riverside":     46,
    "UC Merced":        144,
    "Cal Poly SLO":     11,
}

TARGET_MAJORS = [
    "Computer Science",
    "Biology",
    "Mathematics",
    "Business Administration",
    "Psychology",
    "Electrical Engineering",
    "Mechanical Engineering",
    "Chemistry",
    "Economics",
    "Political Science",
]

DELAY = 5  # longer delay to avoid rate limits


def make_session():
    s = requests.Session()
    s.headers.update({"User-Agent": USER_AGENT, "Accept": "application/json", "Referer": BASE_URL})
    s.get(BASE_URL, timeout=15)
    token = s.cookies.get("X-XSRF-TOKEN")
    if token:
        s.headers["X-XSRF-TOKEN"] = token
    return s


def fetch_key(session, recv_id, send_id, year_id, major):
    r = session.get(f"{BASE_URL}/api/agreements",
        params={"receivingInstitutionId": recv_id, "sendingInstitutionId": send_id,
                "academicYearId": year_id, "categoryCode": "major"}, timeout=30)
    r.raise_for_status()
    reports = r.json().get("reports", [])
    match = next((rep for rep in reports if major.lower() in rep.get("label", "").lower()), None)
    return (match["key"], match["label"]) if match else None


def fetch_detail(session, key):
    r = session.get(f"{BASE_URL}/api/articulation/Agreements", params={"Key": key}, timeout=30)
    r.raise_for_status()
    payload = r.json()
    if not payload.get("isSuccessful"):
        return None
    result = payload["result"]
    for k in list(result.keys()):
        val = result[k]
        if isinstance(val, str) and val and val[0] in ("{", "["):
            try:
                result[k] = json.loads(val)
            except Exception:
                pass
    return result


def main():
    year_id = 74
    session = make_session()
    saved = 0
    failed = 0

    for school_name, school_id in TARGET_SCHOOLS.items():
        for major in TARGET_MAJORS:
            school_slug = school_name.lower().replace(" ", "").replace(",", "")
            major_slug  = major.lower().replace(" ", "")
            out_path    = OUTPUT_DIR / f"deanzacollege_{school_slug}_{major_slug}_20232024.json"

            if out_path.exists():
                continue  # already have it

            print(f"→ {school_name} / {major}")
            time.sleep(DELAY)

            try:
                match = fetch_key(session, school_id, DE_ANZA_ID, year_id, major)
                if not match:
                    print(f"  ✗ No agreement found")
                    failed += 1
                    continue

                key, label = match
                print(f"  Matched: '{label}'")
                time.sleep(DELAY)

                data = fetch_detail(session, key)
                if not data:
                    print(f"  ✗ Failed to fetch detail")
                    failed += 1
                    continue

                with open(out_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                print(f"  ✓ Saved → {out_path.name}")
                saved += 1

            except Exception as e:
                print(f"  ✗ Error: {e}")
                failed += 1
                time.sleep(10)  # extra wait after error

    print(f"\nDone: {saved} saved, {failed} failed")
    if saved > 0:
        print("Now run: python services/parsers/ingest_assist.py")


if __name__ == "__main__":
    main()
