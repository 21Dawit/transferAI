"""
catalog_scraper.py — Scrape De Anza College catalog (Elumen Angular SPA)

Uses Playwright. Dept slugs are hardcoded from the rendered nav (discovered
via debug_links.py). Course cards on each dept page contain dept, number,
title, and units — so we only visit individual pages for descriptions.

Install once:
    pip install playwright
    playwright install chromium

Usage:
    python services/scrapers/catalog_scraper.py --dept CIS --dry-run
    python services/scrapers/catalog_scraper.py --dry-run        # all depts, no DB
    python services/scrapers/catalog_scraper.py                  # full run + DB
    python services/scrapers/catalog_scraper.py --no-descriptions  # fast, cards only
    python services/scrapers/catalog_scraper.py --start-from HIST  # resume from dept
"""

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, Page
from supabase import create_client, Client

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

load_dotenv(Path(__file__).resolve().parents[2] / ".env.local")

SUPABASE_URL = os.environ["NEXT_PUBLIC_SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SECRET_KEY"]

DE_ANZA_SCHOOL_ID = "00000000-0000-0000-0000-000000000001"

CATALOG_BASE = "https://deanza.elumenapp.com/catalog"
CATALOG_YEAR = "2025-2026"

OUTPUT_DIR  = Path(__file__).resolve().parents[2] / "data" / "catalog_raw"
OUTPUT_FILE = OUTPUT_DIR / "deanza_courses.json"

RATE_LIMIT_SEC = 1.0

DEPT_SLUGS = [
    ("ACCT", "accounting-courses"),
    ("ADMJ", "admj-administration-of-justice-courses"),
    ("AFAM", "afam-african-american-studies-courses"),
    ("ANTH", "anth-anthropology-courses"),
    ("APRN", "aprn-automotive-apprenticeship-courses"),
    ("ARTS", "arts-art-courses"),
    ("ASAM", "asam-asian-american-and-asian-studies-courses"),
    ("ASTR", "astr-astronomy-courses"),
    ("ATMG", "atmg-auto-management-courses"),
    ("AUTO", "automotive-technology-courses"),
    ("BIOL", "biol-biology-courses"),
    ("BUS",  "bus-business-courses"),
    ("CD",   "cd-child-development-courses"),
    ("CETH", "ceth-comparative-ethnic-studies-courses"),
    ("CHEM", "chem-chemistry-courses"),
    ("CHLX", "chlx-chicanx-latinx-studies-courses"),
    ("CIS",  "cis-computer-sceince-and-information-systems-courses"),
    ("CLP",  "clp-career-life-planning-courses"),
    ("COMM", "comm-communication-studies-courses"),
    ("COUN", "coun-counseling-courses"),
    ("DANC", "danc-dance-courses"),
    ("DMT",  "dmt-design-and-manufacturing-technologies-courses"),
    ("ECON", "econ-economics-courses"),
    ("EDAC", "edac-educational-access-courses"),
    ("EDUC", "educ-education-courses"),
    ("ELIT", "elit-english-literature-courses"),
    ("ENGL", "engl-english-courses"),
    ("ENGR", "engr-engineering-courses"),
    ("ES",   "es-environmental-studies-courses"),
    ("ESCI", "esci-environmental-science-courses"),
    ("ESL",  "esl-english-as-a-second-language-courses"),
    ("EWRT", "ewrt-english-writing-courses"),
    ("FTV",  "ftv-film-and-television-production-courses"),
    ("FREN", "fren-french-courses"),
    ("GEO",  "geo-geography-courses"),
    ("GEOL", "geol-geology-courses"),
    ("GERM", "germ-german-courses"),
    ("HIST", "hist-history-courses"),
    ("HLTH", "hlth-health-courses"),
    ("HNDI", "hndi-hindi-courses"),
    ("HTEC", "htec-health-technologies-courses"),
    ("HUMA", "huma-human-development-courses"),
    ("HUMI", "humi-humanities-courses"),
    ("ICS",  "ics-intercultural-studies-courses"),
    ("INTL", "intl-international-studies-courses"),
    ("ITAL", "ital-italian-courses"),
    ("JAPN", "japn-japanese-courses"),
    ("JOUR", "jour-journalism-courses"),
    ("KNES", "knes-kinesiology-courses"),
    ("KORE", "kore-korean-courses"),
    ("LART", "lart-language-arts-courses"),
    ("LIB",  "lib-library-courses"),
    ("LING", "ling-linguistics-courses"),
    ("LRNA", "lrna-learning-assistance-courses"),
    ("LS",   "ls-learning-strategies-courses"),
    ("MAND", "mand-mandarin-courses"),
    ("MATH", "math-mathematics-courses"),
    ("MET",  "met-meteorology-courses"),
    ("MUSI", "musi-music-courses"),
    ("NAIS", "nais-native-american-and-indigenous-studies-courses"),
    ("NURS", "nurs-nursing-courses"),
    ("NUTR", "nutr-nutrition-courses"),
    ("PARA", "para-paralegal-studies-courses"),
    ("PE",   "pe-physical-education-courses"),
    ("PEA",  "pea-physical-education-adapted-courses"),
    ("PERS", "pers-persian-courses"),
    ("PHIL", "phil-philosophy-courses"),
    ("PHTG", "phtg-photography-courses"),
    ("PHYS", "phys-physics-courses"),
    ("POLI", "poli-political-science-courses"),
    ("POLS", "pols-political-science-courses"),
    ("PSYC", "psyc-psychology-courses"),
    ("READ", "read-reading-courses"),
    ("REST", "rest-real-estate-courses"),
    ("RUSS", "russ-russian-courses"),
    ("SIGN", "sign-sign-language-courses"),
    ("SKIL", "skil-skills-courses"),
    ("SOC",  "soc-sociology-courses"),
    ("SOSC", "sosc-social-science-courses"),
    ("SPAN", "span-spanish-courses"),
    ("STAT", "stat-statistics-courses"),
    ("THEA", "thea-theatre-arts-courses"),
    ("VIET", "viet-vietnamese-language-courses"),
    ("WMST", "wmst-womens-studies-courses"),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def dept_url(slug: str) -> str:
    return f"{CATALOG_BASE}/{CATALOG_YEAR}/{slug}"

def course_url(href: str) -> str:
    href = href.split("#")[0]
    if href.startswith("http"):
        return href
    return f"{CATALOG_BASE}/{href.lstrip('/')}"

def goto(page: Page, url: str, wait_for: str = None, timeout: int = 30000):
    time.sleep(RATE_LIMIT_SEC)
    page.goto(url, wait_until="networkidle", timeout=timeout)
    if wait_for:
        try:
            page.wait_for_selector(wait_for, timeout=8000)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Parse course cards
# ---------------------------------------------------------------------------

def parse_cards(page: Page, dept_code: str) -> list[dict]:
    courses = []
    try:
        page.wait_for_selector("a[href*='course/']", timeout=8000)
    except Exception:
        return []

    for card in page.query_selector_all("a[href*='course/']"):
        href = card.get_attribute("href") or ""
        if "course/" not in href:
            continue

        text  = card.inner_text().strip()
        lines = [l.strip() for l in text.splitlines() if l.strip()]

        code_line = next((l for l in lines if re.match(r"[A-Z][A-Z0-9/]+ \S+", l)), None)
        if not code_line:
            continue

        m = re.match(r"([A-Z][A-Z0-9/]+)\s+(\S+)", code_line)
        if not m:
            continue

        department = m.group(1)
        number     = m.group(2)
        title_lines = [l for l in lines if l != code_line and not re.search(r"[Uu]nits?", l)]
        title = title_lines[-1] if title_lines else ""
        if not title:
            continue

        units_match = re.search(r"(\d+(?:\.\d+)?)\s*[Uu]nits?", text)
        units = float(units_match.group(1)) if units_match else None

        courses.append({
            "department":  department,
            "number":      number,
            "title":       title,
            "units":       units,
            "description": None,
            "catalog_url": course_url(href),
        })

    return courses


# ---------------------------------------------------------------------------
# Fetch description — with retry on timeout
# ---------------------------------------------------------------------------

def fetch_description(page: Page, url: str, retries: int = 2) -> str | None:
    for attempt in range(retries + 1):
        try:
            goto(page, url, wait_for="h1", timeout=25000)
            for p in page.query_selector_all("p"):
                t = p.inner_text().strip()
                if len(t) > 40:
                    return t
            return None
        except Exception as e:
            if attempt < retries:
                print(f"    ⟳ timeout, retrying ({attempt + 1}/{retries})...")
                time.sleep(3)
            else:
                print(f"    ✗ gave up: {e}", file=sys.stderr)
                return None


# ---------------------------------------------------------------------------
# Supabase upsert
# ---------------------------------------------------------------------------

def upsert_courses(db: Client, courses: list[dict]) -> int:
    if not courses:
        return 0
    rows = [
        {
            "school_id":    DE_ANZA_SCHOOL_ID,
            "department":   c["department"],
            "number":       c["number"],
            "title":        c["title"],
            "units":        c["units"],
            "description":  c["description"],
            "catalog_url":  c["catalog_url"],
            "last_seen_at": "now()",
        }
        for c in courses
        if c.get("department") and c.get("number") and c.get("title")
    ]
    result = (
        db.table("courses")
        .upsert(rows, on_conflict="school_id,department,number")
        .execute()
    )
    return len(result.data) if result.data else 0


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run",         action="store_true")
    parser.add_argument("--dept",            type=str, help="Single dept e.g. CIS")
    parser.add_argument("--start-from",      type=str, help="Resume from dept e.g. HIST")
    parser.add_argument("--headed",          action="store_true")
    parser.add_argument("--no-descriptions", action="store_true")
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    db = None if args.dry_run else create_client(SUPABASE_URL, SUPABASE_KEY)

    target_depts = DEPT_SLUGS

    if args.dept:
        target_depts = [(c, s) for c, s in DEPT_SLUGS if c.upper() == args.dept.upper()]
        if not target_depts:
            sys.exit(f"Dept '{args.dept}' not found.")
    elif args.start_from:
        codes = [c for c, _ in DEPT_SLUGS]
        if args.start_from.upper() not in codes:
            sys.exit(f"Dept '{args.start_from}' not found.")
        idx = codes.index(args.start_from.upper())
        target_depts = DEPT_SLUGS[idx:]
        print(f"Resuming from {args.start_from} ({len(target_depts)} depts remaining).")

    # Load existing JSON if resuming (append mode)
    all_courses: list[dict] = []
    if args.start_from and OUTPUT_FILE.exists():
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            all_courses = json.load(f)
        print(f"Loaded {len(all_courses)} existing courses from JSON.")

    print(f"Scraping {len(target_depts)} department(s).")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=not args.headed)
        page    = browser.new_page()

        for dept_code, slug in target_depts:
            url = dept_url(slug)
            print(f"\n[{dept_code}] {url}")
            goto(page, url)

            courses = parse_cards(page, dept_code)
            print(f"  {len(courses)} courses found on cards.")

            if not courses:
                print(f"  ⚠ No cards — check slug: {slug}")
                continue

            if not args.no_descriptions:
                for c in courses:
                    desc = fetch_description(page, c["catalog_url"])
                    c["description"] = desc
                    print(f"  {'✓' if desc else '–'} {c['department']} {c['number']} — {c['title']}")
            else:
                for c in courses:
                    print(f"  • {c['department']} {c['number']} — {c['title']}")

            all_courses.extend(courses)

            if not args.dry_run and db and courses:
                n = upsert_courses(db, courses)
                print(f"  → {n} rows upserted.")

            # Save progress after every dept so crashes don't lose work
            with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                json.dump(all_courses, f, indent=2, ensure_ascii=False)

        browser.close()

    print(f"\n✅ Done. {len(all_courses)} total courses → {OUTPUT_FILE}")
    if args.dry_run:
        print("[dry-run] DB write skipped.")


if __name__ == "__main__":
    main()
