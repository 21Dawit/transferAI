"""
ingest_assist.py — Store ASSIST JSON into Supabase for articulation lookup

Strategy: store the entire ASSIST response as raw JSONB in the agreement row.
The lookup_articulation tool then searches the raw payload directly.
This matches the plan's recommendation: "store raw payloads in JSONB alongside
parsed fields so when ASSIST changes format, you can reparse without re-scraping."

Usage:
    python services/parsers/ingest_assist.py --dry-run
    python services/parsers/ingest_assist.py
"""

import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from supabase import create_client

load_dotenv(Path(__file__).resolve().parents[2] / ".env.local")

SUPABASE_URL = os.environ["NEXT_PUBLIC_SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SECRET_KEY"]

DE_ANZA_SCHOOL_ID  = "00000000-0000-0000-0000-000000000001"
UC_DAVIS_SCHOOL_ID = "00000000-0000-0000-0000-000000000002"

ASSIST_RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "assist_raw"
ASSIST_SOURCE  = "https://assist.org"


def find_articulations(data: dict) -> list[dict]:
    """
    Walk the ASSIST JSON and extract all articulation pairs.
    
    ASSIST structure (discovered from raw JSON):
    - data["articulations"] is a list of articulation items
    - Each item has:
        - "sendingArticulation": contains De Anza (CCC) course groups
        - "receivingAttributes": describes the UC requirement type
    - The UC course itself is in templateAssets → RequirementGroup → sections → rows
    
    We extract all CCC courses and store them as structured rows
    alongside the raw payload.
    """
    results = []

    # Walk templateAssets for UC requirements
    uc_requirements = {}
    for asset in data.get("templateAssets", []):
        if asset.get("type") != "RequirementGroup":
            continue
        for section in asset.get("sections", []):
            for row in section.get("rows", []):
                # position 0 = the UC requirement course
                if row.get("position") == 0:
                    for cell in row.get("cells", []):
                        course = cell.get("course", {})
                        if course:
                            key = cell.get("id", "")
                            uc_requirements[key] = {
                                "dept":   course.get("prefix", ""),
                                "number": course.get("courseNumber", ""),
                                "title":  course.get("courseTitle", ""),
                                "units":  course.get("minUnits"),
                            }

    # Walk articulations for CCC course mappings
    for art in data.get("articulations", []):
        sending = art.get("sendingArticulation", {})
        if not sending:
            continue

        # Extract CCC courses from courseGroups
        ccc_courses = []
        for group in sending.get("courseGroups", []):
            for item in group.get("items", []):
                if item.get("type") == "Course":
                    ccc_courses.append({
                        "dept":   item.get("prefix", ""),
                        "number": item.get("courseNumber", ""),
                        "title":  item.get("courseTitle", ""),
                        "units":  item.get("minUnits"),
                    })

        # Get the UC course this maps to
        cell_id = art.get("id", "")
        uc = uc_requirements.get(cell_id, {})

        # Determine relationship
        if not ccc_courses:
            relationship = "no_articulation"
        elif len(ccc_courses) == 1:
            relationship = "direct"
        else:
            # Check conjunctions — if all "And", it's a series
            conj_types = {c.get("groupConjunction") for c in sending.get("courseGroupConjunctions", [])}
            relationship = "series" if "And" in conj_types and "Or" not in conj_types else "any_of"

        results.append({
            "uc_dept":    uc.get("dept", ""),
            "uc_number":  uc.get("number", ""),
            "uc_title":   uc.get("title", ""),
            "ccc_courses": ccc_courses,
            "relationship": relationship,
            "raw":        art,
        })

    # If articulations array is empty, fall back to extracting from templateAssets
    # (some ASSIST files use a different structure)
    if not results:
        results = _fallback_parse(data)

    return results


def _fallback_parse(data: dict) -> list[dict]:
    """
    Fallback: extract from templateAssets where position 0 = UC, position 1+ = CCC.
    Used when the articulations array is absent.
    """
    results = []
    for asset in data.get("templateAssets", []):
        if asset.get("type") != "RequirementGroup":
            continue
        for section in asset.get("sections", []):
            uc_course = None
            ccc_courses = []

            rows_by_pos = sorted(section.get("rows", []), key=lambda r: r.get("position", 99))
            for row in rows_by_pos:
                for cell in row.get("cells", []):
                    course = cell.get("course", {})
                    if not course:
                        continue
                    entry = {
                        "dept":   course.get("prefix", ""),
                        "number": course.get("courseNumber", ""),
                        "title":  course.get("courseTitle", ""),
                        "units":  course.get("minUnits"),
                    }
                    if row.get("position") == 0 and uc_course is None:
                        uc_course = entry
                    else:
                        ccc_courses.append(entry)

            if uc_course:
                relationship = (
                    "no_articulation" if not ccc_courses
                    else "direct" if len(ccc_courses) == 1
                    else "any_of"
                )
                results.append({
                    "uc_dept":    uc_course["dept"],
                    "uc_number":  uc_course["number"],
                    "uc_title":   uc_course["title"],
                    "ccc_courses": ccc_courses,
                    "relationship": relationship,
                    "raw":        section,
                })
    return results


def ingest(db, dry_run: bool = False) -> None:
    files = list(ASSIST_RAW_DIR.glob("*.json"))
    if not files:
        sys.exit(f"No JSON files in {ASSIST_RAW_DIR}")

    print(f"Found {len(files)} ASSIST file(s).")

    for path in files:
        print(f"\nParsing: {path.name}")
        data = json.loads(path.read_text(encoding="utf-8"))

        major_name    = data.get("name", "Unknown")
        academic_year = data.get("academicYear", {}).get("code", "")
        eff_year      = int(academic_year.split("-")[0]) if academic_year else None
        rows          = find_articulations(data)

        print(f"  Major: {major_name} ({eff_year})")
        print(f"  Articulation rows found: {len(rows)}")

        # Preview
        for r in rows[:8]:
            ccc_str = ", ".join(f"{c['dept']} {c['number']}" for c in r["ccc_courses"]) or "NO ARTICULATION"
            print(f"    UC {r['uc_dept']} {r['uc_number']} ← CCC: {ccc_str}  [{r['relationship']}]")
        if len(rows) > 8:
            print(f"    ... and {len(rows) - 8} more")

        if dry_run:
            continue

        # Store agreement with full raw payload
        agreement_result = (
            db.table("articulation_agreements")
            .upsert({
                "from_ccc_id":     DE_ANZA_SCHOOL_ID,
                "to_school_id":    UC_DAVIS_SCHOOL_ID,
                "major_name":      major_name,
                "effective_year":  eff_year,
                "source_url":      ASSIST_SOURCE,
                "last_fetched_at": "now()",
            }, on_conflict="from_ccc_id,to_school_id,major_name")
            .execute()
        )
        agreement_id = agreement_result.data[0]["id"]

        # Store each articulation row
        inserted = 0
        for r in rows:
            try:
                db.table("articulation_rows").upsert({
                    "agreement_id":   agreement_id,
                    "from_course_id": None,   # resolved at query time via raw_payload
                    "to_course_id":   None,
                    "relationship":   r["relationship"],
                    "notes":          f"UC {r['uc_dept']} {r['uc_number']} — {r['uc_title']}",
                    "raw_payload": {
                        "uc_dept":     r["uc_dept"],
                        "uc_number":   r["uc_number"],
                        "uc_title":    r["uc_title"],
                        "ccc_courses": r["ccc_courses"],
                    },
                }).execute()
                inserted += 1
            except Exception as e:
                print(f"    ✗ {e}", file=sys.stderr)

        print(f"  → {inserted} rows stored.")

    if dry_run:
        print("\n[dry-run] No DB writes.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    db = None if args.dry_run else create_client(SUPABASE_URL, SUPABASE_KEY)
    ingest(db, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
