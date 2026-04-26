"""
parse_igetc.py — Parse IGETC requirements into the major_requirements table

IGETC (Intersegmental General Education Transfer Curriculum) is a set of
general education courses that fulfill lower-division GE requirements at
all UC and most CSU campuses.

This script uses the official IGETC standard (same for all CCCs) and
seeds the major_requirements table with structured IGETC area requirements.

Source: https://www.assist.org/transfer/IGETC

Usage:
    python services/parsers/parse_igetc.py
    python services/parsers/parse_igetc.py --dry-run
"""

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from supabase import create_client

load_dotenv(Path(__file__).resolve().parents[2] / ".env.local")

SUPABASE_URL = os.environ["NEXT_PUBLIC_SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SECRET_KEY"]

# De Anza's school_id (the CCC offering IGETC-certified courses)
DE_ANZA_SCHOOL_ID = "00000000-0000-0000-0000-000000000001"

IGETC_SOURCE_URL = "https://www.assist.org/transfer/IGETC"

# ---------------------------------------------------------------------------
# IGETC Structure (2024-2025 standard)
# Each area has a code, name, units required, and notes.
# The course_constraint is left open (any approved course counts) —
# we store which De Anza courses satisfy each area separately via
# catalog data + ASSIST articulation.
# ---------------------------------------------------------------------------

IGETC_AREAS = [
    {
        "area_code":       "1A",
        "area_name":       "English Composition",
        "units_required":  3,
        "notes":           "One course, minimum 3 semester units. Must be English composition.",
        "course_constraint": {
            "type": "any_of",
            "description": "Any IGETC-approved English composition course",
            "example_courses": ["ENGL 1A", "EWRT 1A"]
        }
    },
    {
        "area_code":       "1B",
        "area_name":       "Critical Thinking and Composition",
        "units_required":  3,
        "notes":           "One course emphasizing critical thinking and argumentative writing.",
        "course_constraint": {
            "type": "any_of",
            "description": "Any IGETC-approved critical thinking course",
            "example_courses": ["ENGL 1C", "PHIL 1"]
        }
    },
    {
        "area_code":       "1C",
        "area_name":       "Oral Communication (CSU only)",
        "units_required":  3,
        "notes":           "Required for CSU only, not UC. One oral communication course.",
        "course_constraint": {
            "type": "any_of",
            "description": "Any IGETC-approved oral communication course (CSU only)",
            "example_courses": ["COMM 1A"]
        }
    },
    {
        "area_code":       "2",
        "area_name":       "Mathematical Concepts and Quantitative Reasoning",
        "units_required":  3,
        "notes":           "One course, minimum 3 semester units. Precalculus or higher recommended for STEM.",
        "course_constraint": {
            "type": "any_of",
            "description": "Any IGETC-approved math course",
            "example_courses": ["MATH 1A", "MATH 10", "STAT 1"]
        }
    },
    {
        "area_code":       "3A",
        "area_name":       "Arts",
        "units_required":  3,
        "notes":           "Arts and Humanities combined minimum 9 units from Areas 3A, 3B. At least one from each.",
        "course_constraint": {
            "type": "any_of",
            "description": "Any IGETC-approved arts course",
            "example_courses": ["ARTS 1", "MUSI 1", "THEA 1"]
        }
    },
    {
        "area_code":       "3B",
        "area_name":       "Humanities",
        "units_required":  3,
        "notes":           "Combined with 3A for 9-unit humanities requirement.",
        "course_constraint": {
            "type": "any_of",
            "description": "Any IGETC-approved humanities course",
            "example_courses": ["ENGL 2", "HIST 1", "PHIL 2"]
        }
    },
    {
        "area_code":       "4",
        "area_name":       "Social and Behavioral Sciences",
        "units_required":  9,
        "notes":           "Minimum 9 units from at least 2 disciplines.",
        "course_constraint": {
            "type": "any_of",
            "description": "Any IGETC-approved social/behavioral science course, at least 2 disciplines",
            "example_courses": ["ECON 1A", "PSYC 1", "SOC 1"]
        }
    },
    {
        "area_code":       "5A",
        "area_name":       "Physical Science",
        "units_required":  3,
        "notes":           "Physical and Biological Sciences combined 7-9 units. At least one lab. At least one from 5A and one from 5B.",
        "course_constraint": {
            "type": "any_of",
            "description": "Any IGETC-approved physical science course",
            "example_courses": ["CHEM 1A", "PHYS 1", "ASTR 1"]
        }
    },
    {
        "area_code":       "5B",
        "area_name":       "Biological Science",
        "units_required":  3,
        "notes":           "Combined with 5A for science requirement. At least one lab required.",
        "course_constraint": {
            "type": "any_of",
            "description": "Any IGETC-approved biological science course",
            "example_courses": ["BIOL 6A", "BIOL 10"]
        }
    },
    {
        "area_code":       "5C",
        "area_name":       "Science Laboratory",
        "units_required":  0,
        "notes":           "Lab requirement fulfilled when a lab course is taken in 5A or 5B. No additional units needed if the course includes a lab.",
        "course_constraint": {
            "type": "any_of",
            "description": "Lab component of a 5A or 5B course",
            "example_courses": ["CHEM 1A (includes lab)", "BIOL 6A (includes lab)"]
        }
    },
    {
        "area_code":       "6",
        "area_name":       "Languages Other Than English (LOTE)",
        "units_required":  0,
        "notes":           "UC only. Proficiency equivalent to 2 years of high school LOTE. Can be satisfied by exam, high school coursework, or college course. Not a unit requirement per se.",
        "course_constraint": {
            "type": "any_of",
            "description": "Proficiency in a language other than English",
            "example_courses": ["SPAN 1", "JAPN 1", "MAND 1"]
        }
    },
]

# ---------------------------------------------------------------------------
# Total IGETC unit summary (for reference / validation)
# ---------------------------------------------------------------------------
# Area 1:  6 units (1A + 1B); 1C is CSU-only
# Area 2:  3 units
# Area 3:  9 units (3A + 3B, with remaining from either)
# Area 4:  9 units
# Area 5:  7-9 units (5A + 5B, at least one lab)
# Area 6:  0 units (proficiency requirement)
# Total:   ~34-36 units

IGETC_TOTAL_NOTE = (
    "Complete IGETC requires approximately 34-36 units: "
    "Area 1 (6 units), Area 2 (3 units), Area 3 (9 units), "
    "Area 4 (9 units), Area 5 (7-9 units + lab), Area 6 (proficiency). "
    "Verify current requirements at igetc.assist.org."
)


# ---------------------------------------------------------------------------
# Insert into Supabase
# ---------------------------------------------------------------------------

def seed_igetc(db, dry_run: bool = False) -> None:
    rows = []
    for area in IGETC_AREAS:
        rows.append({
            "school_id":          DE_ANZA_SCHOOL_ID,
            "major_name":         "IGETC",   # applies to all majors
            "requirement_type":   "igetc",
            "area_code":          area["area_code"],
            "area_name":          area["area_name"],
            "units_required":     area["units_required"],
            "course_constraint":  area["course_constraint"],
            "notes":              area["notes"],
            "source_url":         IGETC_SOURCE_URL,
        })

    print(f"Prepared {len(rows)} IGETC area rows.")

    if dry_run:
        for r in rows:
            print(f"  [{r['area_code']}] {r['area_name']} — {r['units_required']} units")
        print("[dry-run] No DB write.")
        return

    result = (
        db.table("major_requirements")
        .upsert(rows, on_conflict="school_id,major_name,area_code")
        .execute()
    )
    print(f"Upserted {len(result.data)} rows into major_requirements.")
    print(f"\nNote: {IGETC_TOTAL_NOTE}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Seed IGETC requirements")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    db = None if args.dry_run else create_client(SUPABASE_URL, SUPABASE_KEY)
    seed_igetc(db, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
