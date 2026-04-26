"""
batch_assist_scraper.py — Scrape multiple ASSIST agreements in one run

Scrapes De Anza → multiple UC/CSU schools for multiple majors.
Saves raw JSON files and ingests them into Supabase.

Usage:
    python services/scrapers/batch_assist_scraper.py --dry-run   # show what would be scraped
    python services/scrapers/batch_assist_scraper.py             # scrape + ingest all
    python services/scrapers/batch_assist_scraper.py --school "UC Berkeley"  # one school only
    python services/scrapers/batch_assist_scraper.py --major "Biology"       # one major only
"""

import argparse
import json
import sys
import time
from pathlib import Path

import requests

BASE_URL   = "https://assist.org"
USER_AGENT = "TransferAI-StudentResearch/1.0 (student research project)"
OUTPUT_DIR = Path(__file__).resolve().parents[2] / "data" / "assist_raw"

ACADEMIC_YEAR_IDS = {
    "2023-2024": 74,
    "2024-2025": 75,
}
DEFAULT_YEAR = "2023-2024"

# De Anza College
DE_ANZA_ID = 113

# All target schools with their ASSIST IDs
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
    "San Jose State":   174,
}

# Majors to scrape — these are search strings matched against ASSIST major labels
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


# ---------------------------------------------------------------------------
# Session
# ---------------------------------------------------------------------------

def make_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent": USER_AGENT,
        "Accept": "application/json, text/plain, */*",
        "Referer": f"{BASE_URL}/",
        "Origin": BASE_URL,
    })
    s.get(BASE_URL, timeout=15)
    token = s.cookies.get("X-XSRF-TOKEN")
    if not token:
        raise RuntimeError("Could not get XSRF token from ASSIST.org")
    s.headers["X-XSRF-TOKEN"] = token
    return s


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------

def fetch_agreement_key(session, receiving_id: int, sending_id: int,
                         year_id: int, major: str) -> tuple[str, str] | None:
    """Returns (key, exact_label) or None if no match."""
    try:
        r = session.get(
            f"{BASE_URL}/api/agreements",
            params={
                "receivingInstitutionId": receiving_id,
                "sendingInstitutionId":   sending_id,
                "academicYearId":         year_id,
                "categoryCode":           "major",
            },
            timeout=30,
        )
        r.raise_for_status()
        reports = r.json().get("reports", [])
    except Exception as e:
        print(f"    ✗ API error fetching major list: {e}")
        return None

    major_lower = major.lower()
    match = next(
        (rep for rep in reports if major_lower in rep.get("label", "").lower()),
        None,
    )
    return (match["key"], match["label"]) if match else None


def fetch_articulation_detail(session, key: str) -> dict | None:
    try:
        r = session.get(
            f"{BASE_URL}/api/articulation/Agreements",
            params={"Key": key},
            timeout=30,
        )
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
                except json.JSONDecodeError:
                    pass
        return result
    except Exception as e:
        print(f"    ✗ API error fetching detail: {e}")
        return None


# ---------------------------------------------------------------------------
# Save + ingest
# ---------------------------------------------------------------------------

def save_raw(data: dict, school_slug: str, major_slug: str, year: str) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    fname = f"deanzacollege_{school_slug}_{major_slug}_{year.replace('-', '')}.json"
    out   = OUTPUT_DIR / fname
    with open(out, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return out


def ingest_file(path: Path) -> None:
    """Run the ingest_assist script on a single file."""
    import subprocess
    result = subprocess.run(
        [sys.executable, "services/parsers/ingest_assist.py"],
        capture_output=True, text=True,
        cwd=Path(__file__).resolve().parents[2]
    )
    if result.returncode != 0:
        print(f"    ⚠ Ingest warning: {result.stderr[:200]}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--school",  type=str, help="Scrape one school only")
    parser.add_argument("--major",   type=str, help="Scrape one major only")
    parser.add_argument("--year",    type=str, default=DEFAULT_YEAR)
    args = parser.parse_args()

    year_id = ACADEMIC_YEAR_IDS.get(args.year)
    if not year_id:
        sys.exit(f"Unknown year '{args.year}'. Known: {list(ACADEMIC_YEAR_IDS.keys())}")

    # Filter
    schools = {k: v for k, v in TARGET_SCHOOLS.items()
               if not args.school or args.school.lower() in k.lower()}
    majors  = [m for m in TARGET_MAJORS
               if not args.major or args.major.lower() in m.lower()]

    if not schools:
        sys.exit(f"No schools matched '{args.school}'")
    if not majors:
        sys.exit(f"No majors matched '{args.major}'")

    total = len(schools) * len(majors)
    print(f"Plan: {len(schools)} schools × {len(majors)} majors = {total} combinations")
    print(f"Year: {args.year}")
    if args.dry_run:
        print("\n[dry-run] Would scrape:")
        for school in schools:
            for major in majors:
                print(f"  De Anza → {school} : {major}")
        return

    print("\nStarting scrape (2s delay between requests)...\n")

    session   = make_session()
    succeeded = 0
    skipped   = 0
    failed    = 0

    for school_name, school_id in schools.items():
        for major in majors:
            school_slug = school_name.lower().replace(" ", "").replace(",", "")
            major_slug  = major.lower().replace(" ", "")
            out_path    = OUTPUT_DIR / f"deanzacollege_{school_slug}_{major_slug}_{args.year.replace('-', '')}.json"

            if out_path.exists():
                print(f"  ⏭ {school_name} / {major} — already exists, skipping")
                skipped += 1
                continue

            print(f"  → {school_name} / {major}")
            time.sleep(2)

            match = fetch_agreement_key(session, school_id, DE_ANZA_ID, year_id, major)
            if not match:
                print(f"    ✗ No agreement found")
                failed += 1
                continue

            key, label = match
            print(f"    Matched: '{label}'")
            time.sleep(2)

            data = fetch_articulation_detail(session, key)
            if not data:
                print(f"    ✗ Failed to fetch detail")
                failed += 1
                continue

            saved = save_raw(data, school_slug, major_slug, args.year)
            print(f"    ✓ Saved → {saved.name}")
            succeeded += 1

    print(f"\n{'=' * 50}")
    print(f"Done: {succeeded} saved, {skipped} skipped, {failed} failed")
    print(f"\nNow run the ingester to load into Supabase:")
    print(f"  python services/parsers/ingest_assist.py")


if __name__ == "__main__":
    main()
