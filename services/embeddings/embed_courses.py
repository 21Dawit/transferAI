"""
embed_courses.py — Generate and store embeddings for all De Anza courses

Uses sentence-transformers/all-MiniLM-L6-v2 (runs locally, no API key needed).
Reads courses from Supabase, embeds them, writes vectors back via the
Supabase REST API.

Usage:
    python services/embeddings/embed_courses.py           # embed all missing
    python services/embeddings/embed_courses.py --force   # re-embed everything

Install deps first (once):
    pip install sentence-transformers supabase python-dotenv

The first run downloads the model (~90 MB). Subsequent runs use the cache.
"""

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from supabase import create_client

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

load_dotenv(Path(__file__).resolve().parents[2] / ".env.local")

SUPABASE_URL = os.environ["NEXT_PUBLIC_SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SECRET_KEY"]

DE_ANZA_SCHOOL_ID = "00000000-0000-0000-0000-000000000001"

# all-MiniLM-L6-v2: 384 dimensions, fast, excellent for semantic search.
# Must match the vector(384) column in 002_pgvector.sql.
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

# Number of courses to embed in one batch (balances memory vs. speed)
BATCH_SIZE = 32


# ---------------------------------------------------------------------------
# Text prep
# ---------------------------------------------------------------------------

def build_embedding_text(course: dict) -> str:
    """
    Combine fields into a single string for embedding.
    Richer text = better semantic retrieval.
    Format: "DEPT NUMBER: Title. Description."
    """
    parts = [f"{course['department']} {course['number']}: {course['title']}."]
    if course.get("description"):
        parts.append(course["description"])
    return " ".join(parts)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Embed De Anza courses into pgvector")
    parser.add_argument("--force", action="store_true", help="Re-embed courses that already have embeddings")
    args = parser.parse_args()

    db = create_client(SUPABASE_URL, SUPABASE_KEY)

    # Fetch courses
    print("Fetching courses from Supabase...")
    query = db.table("courses").select("id, department, number, title, description, embedding").eq("school_id", DE_ANZA_SCHOOL_ID)

    if not args.force:
        # Only fetch rows where embedding IS NULL
        # Supabase REST: filter by null
        query = query.is_("embedding", "null")

    result = query.execute()
    courses = result.data or []

    if not courses:
        print("No courses to embed (all already have embeddings). Use --force to re-embed.")
        return

    print(f"Found {len(courses)} courses to embed.")

    # Load model (downloads on first run, ~90 MB)
    print(f"\nLoading model: {MODEL_NAME}")
    print("(First run downloads ~90 MB — subsequent runs use cache.)")
    model = SentenceTransformer(MODEL_NAME)
    print("Model loaded.\n")

    # Embed in batches
    texts = [build_embedding_text(c) for c in courses]
    ids   = [c["id"] for c in courses]

    total_upserted = 0

    for i in range(0, len(texts), BATCH_SIZE):
        batch_texts = texts[i : i + BATCH_SIZE]
        batch_ids   = ids[i : i + BATCH_SIZE]
        batch_courses = courses[i : i + BATCH_SIZE]

        print(f"Embedding batch {i // BATCH_SIZE + 1} / {-(-len(texts) // BATCH_SIZE)} ({len(batch_texts)} courses)...")

        # encode() returns a numpy array; convert to nested Python list for JSON
        embeddings = model.encode(batch_texts, show_progress_bar=False)

        # Update each row in Supabase
        for course, embedding in zip(batch_courses, embeddings):
            db.table("courses").update(
                {"embedding": embedding.tolist()}
            ).eq("id", course["id"]).execute()
            total_upserted += 1

        print(f"  ✓ {total_upserted} courses embedded so far.")

    print(f"\nDone. {total_upserted} courses now have embeddings in pgvector.")


if __name__ == "__main__":
    main()
