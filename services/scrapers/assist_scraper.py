"""
assist_scraper.py — Fetch articulation agreements from ASSIST.org

Usage:
    python services/scrapers/assist_scraper.py \
        --from-school "De Anza College" \
        --to-school "UC Davis" \
        --major "Computer Science"

How the ASSIST.org API works (reverse-engineered from the Angular SPA):
  1. GET https://assist.org  → sets XSRF-TOKEN and X-XSRF-TOKEN cookies
  2. All API calls must send the X-XSRF-TOKEN *cookie value* as the
     X-XSRF-TOKEN *request header* (ASP.NET anti-forgery pattern).
  3. GET /api/agreements?...&categoryCode=major  → returns a list of
     {label, key, ownerInstitutionId} objects.
  4. GET /api/articulation/Agreements?Key=<key>  → returns the full
     articulation detail. The "articulations" field is a JSON string
     (double-encoded) that must be parsed separately.
"""

import argparse
import json
import time
from pathlib import Path

import requests

# ---------------------------------------------------------------------------
# School / year lookup tables
# IDs sourced directly from the ASSIST.org API (/api/institutions,
# /api/AcademicYears). Note: academicYearId maps to the *fall* year,
# so 2023-2024 = fallYear 2023 = id 74.
# ---------------------------------------------------------------------------
SCHOOL_IDS = {
    "de anza college": 113,
    "uc davis": 89,
    "san jose state university": 174,
}

ACADEMIC_YEAR_IDS = {
    "2023-2024": 74,
    "2024-2025": 75,
}

DEFAULT_ACADEMIC_YEAR = "2023-2024"

USER_AGENT = (
    "TransferAI-StudentResearch/1.0 "
    "(articulation data for academic planning; student research project)"
)

OUTPUT_DIR = Path(__file__).resolve().parents[2] / "data" / "assist_raw"

BASE_URL = "https://assist.org"


# ---------------------------------------------------------------------------
# Session helpers
# ---------------------------------------------------------------------------

def make_session() -> requests.Session:
    """
    Create an authenticated requests.Session for ASSIST.org.

    ASSIST uses ASP.NET anti-forgery: the server sets both XSRF-TOKEN and
    X-XSRF-TOKEN cookies on the first page load. The X-XSRF-TOKEN cookie
    value must be echoed back as the X-XSRF-TOKEN request header on every
    subsequent API call.
    """
    session = requests.Session()
    session.headers.update({
        "User-Agent": USER_AGENT,
        "Accept": "application/json, text/plain, */*",
        "Referer": f"{BASE_URL}/",
        "Origin": BASE_URL,
    })

    print("Seeding session (obtaining XSRF tokens)...")
    session.get(BASE_URL, timeout=15)

    token = session.cookies.get("X-XSRF-TOKEN")
    if not token:
        raise RuntimeError(
            "Did not receive X-XSRF-TOKEN cookie from ASSIST.org. "
            "The site may have changed its auth flow."
        )
    session.headers["X-XSRF-TOKEN"] = token
    return session


# ---------------------------------------------------------------------------
# API calls
# ---------------------------------------------------------------------------

def fetch_agreement_key(
    session: requests.Session,
    receiving_id: int,
    sending_id: int,
    year_id: int,
    major: str,
) -> tuple[str, str]:
    """
    Fetch the major listing and return (key, exact_label) for the best match.
    Raises SystemExit if no match is found and prints available majors.
    """
    r = session.get(
        f"{BASE_URL}/api/agreements",
        params={
            "receivingInstitutionId": receiving_id,
            "sendingInstitutionId": sending_id,
            "academicYearId": year_id,
            "categoryCode": "major",    # must be lowercase
        },
        timeout=30,
    )
    r.raise_for_status()
    reports = r.json().get("reports", [])

    major_lower = major.lower()
    match = next(
        (rep for rep in reports if major_lower in rep.get("label", "").lower()),
        None,
    )

    if match is None:
        labels = [rep.get("label", "") for rep in reports]
        raise SystemExit(
            f"No agreement found for major '{major}'.\n"
            f"Available majors ({len(labels)}):\n"
            + "\n".join(f"  - {lbl}" for lbl in sorted(labels))
        )

    return match["key"], match["label"]


def fetch_articulation_detail(session: requests.Session, key: str) -> dict:
    """Fetch the full articulation detail for a given agreement key."""
    r = session.get(
        f"{BASE_URL}/api/articulation/Agreements",
        params={"Key": key},
        timeout=30,
    )
    r.raise_for_status()
    payload = r.json()

    if not payload.get("isSuccessful"):
        raise RuntimeError(
            f"ASSIST API returned isSuccessful=false: {payload.get('validationFailure')}"
        )

    result = payload["result"]

    # All nested objects in the result are double-encoded JSON strings.
    # Parse any string-valued field that looks like a JSON object or array.
    for key in list(result.keys()):
        val = result[key]
        if isinstance(val, str) and val and val[0] in ("{", "["):
            try:
                result[key] = json.loads(val)
            except json.JSONDecodeError:
                pass

    return result


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def print_articulation_rows(result: dict) -> None:
    """Pretty-print all articulation rows from a parsed agreement result."""
    label          = result.get("name", "Unknown Major")
    recv           = result.get("receivingInstitution") or {}
    send           = result.get("sendingInstitution") or {}
    receiving_inst = (recv.get("names") or [{}])[0].get("name", "?")
    sending_inst   = (send.get("names") or [{}])[0].get("name", "?")
    acad_year      = result.get("academicYear") or {}
    year_label     = acad_year.get("code", "?")

    print(f"\n{'=' * 70}")
    print(f"  {label}")
    print(f"  {sending_inst}  ->  {receiving_inst}  ({year_label})")
    print(f"{'=' * 70}")

    articulations = result.get("articulations", [])
    if not articulations:
        print("  (no articulation rows returned)")
        return

    for row in articulations:
        art = row.get("articulation", {})
        recv_course = art.get("course", {})
        sending_art = art.get("sendingArticulation", {})

        recv_str = _fmt_course(recv_course) if recv_course else "(no receiving course)"

        no_art_reason = sending_art.get("noArticulationReason")
        if no_art_reason:
            send_str = f"No articulation — {no_art_reason}"
        else:
            items = sending_art.get("items", [])
            group_strs = []
            for group in items:
                conjunction = group.get("courseConjunction", "And")
                courses = group.get("items", [])
                course_strs = [_fmt_course(c) for c in courses if c.get("type") == "Course"]
                joiner = f" {conjunction} "
                group_strs.append(joiner.join(course_strs) if course_strs else "(empty group)")
            send_str = "  OR  ".join(group_strs) if group_strs else "(none)"

        print(f"\n  UC Davis : {recv_str}")
        print(f"  De Anza  : {send_str}")


def _fmt_course(c: dict) -> str:
    prefix  = c.get("prefix", "")
    number  = c.get("courseNumber", "")
    title   = c.get("courseTitle", "")
    min_u   = c.get("minUnits")
    max_u   = c.get("maxUnits")
    units   = (
        f"{min_u:.1f}" if min_u == max_u
        else f"{min_u:.1f}-{max_u:.1f}"
    ) + " units" if min_u is not None else ""
    return f"{prefix} {number} — {title} ({units})"


def save_raw(data: dict, from_school: str, to_school: str, major: str, year: str) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    slug = "_".join([
        from_school.lower().replace(" ", ""),
        to_school.lower().replace(" ", ""),
        major.lower().replace(" ", ""),
        year.replace("-", ""),
    ])
    out_path = OUTPUT_DIR / f"{slug}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"\nRaw JSON saved -> {out_path}")
    return out_path


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch articulation agreements from ASSIST.org"
    )
    parser.add_argument("--from-school", required=True, help='Sending CCC, e.g. "De Anza College"')
    parser.add_argument("--to-school",   required=True, help='Receiving institution, e.g. "UC Davis"')
    parser.add_argument("--major",       required=True, help='Major name, e.g. "Computer Science"')
    parser.add_argument(
        "--year",
        default=DEFAULT_ACADEMIC_YEAR,
        help=f"Academic year (default: {DEFAULT_ACADEMIC_YEAR})",
    )
    args = parser.parse_args()

    sending_id   = SCHOOL_IDS.get(args.from_school.lower())
    receiving_id = SCHOOL_IDS.get(args.to_school.lower())
    year_id      = ACADEMIC_YEAR_IDS.get(args.year)

    if sending_id is None:
        raise SystemExit(
            f"Unknown --from-school '{args.from_school}'. "
            f"Known: {list(SCHOOL_IDS.keys())}"
        )
    if receiving_id is None:
        raise SystemExit(
            f"Unknown --to-school '{args.to_school}'. "
            f"Known: {list(SCHOOL_IDS.keys())}"
        )
    if year_id is None:
        raise SystemExit(
            f"Unknown --year '{args.year}'. "
            f"Known: {list(ACADEMIC_YEAR_IDS.keys())}"
        )

    print(f"Waiting 2 seconds before request (rate limiting)...")
    time.sleep(2)

    session = make_session()

    print(f"\nFetching major listing for {args.from_school} -> {args.to_school} ({args.year})...")
    key, exact_label = fetch_agreement_key(session, receiving_id, sending_id, year_id, args.major)
    print(f"Matched major: '{exact_label}'  (key: {key})")

    print(f"\nFetching articulation detail...")
    result = fetch_articulation_detail(session, key)

    save_raw(result, args.from_school, args.to_school, args.major, args.year)
    print_articulation_rows(result)


if __name__ == "__main__":
    main()
