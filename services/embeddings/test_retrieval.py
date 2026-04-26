"""
test_retrieval.py — Verify that pgvector semantic search works on real queries

Run this after embed_courses.py has populated embeddings.

Usage:
    python services/embeddings/test_retrieval.py

It runs a set of test queries and prints the top results for each.
If retrieval is working, you'll see relevant courses for each query —
not random noise.
"""

import os
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
MODEL_NAME        = "sentence-transformers/all-MiniLM-L6-v2"

# ---------------------------------------------------------------------------
# Test queries
# These reflect real questions students ask — good retrieval should surface
# relevant courses for each.
# ---------------------------------------------------------------------------

TEST_QUERIES = [
    "intro to programming python",
    "calculus for engineers",
    "data structures algorithms",
    "english composition writing",
    "linear algebra matrices",
    "biology lab science",
    "economics micro macro",
    "statistics probability",
    "discrete math logic",
    "transfer requirements general education",
]


# ---------------------------------------------------------------------------
# Run tests
# ---------------------------------------------------------------------------

def run_retrieval(query: str, model, db, top_k: int = 5) -> list[dict]:
    """Embed a query and call the semantic_search_courses RPC."""
    embedding = model.encode(query).tolist()

    result = db.rpc(
        "semantic_search_courses",
        {
            "query_embedding": embedding,
            "school_uuid":     DE_ANZA_SCHOOL_ID,
            "match_count":     top_k,
        },
    ).execute()

    return result.data or []


def main() -> None:
    db = create_client(SUPABASE_URL, SUPABASE_KEY)

    print(f"Loading model: {MODEL_NAME}...")
    model = SentenceTransformer(MODEL_NAME)
    print("Model loaded.\n")

    passed = 0
    failed = 0

    for query in TEST_QUERIES:
        print(f"{'─' * 60}")
        print(f"Query: \"{query}\"")
        results = run_retrieval(query, model, db)

        if not results:
            print("  ✗ No results returned — check that embeddings exist.")
            failed += 1
            continue

        for rank, r in enumerate(results, 1):
            dept    = r.get("department", "?")
            number  = r.get("number", "?")
            title   = r.get("title", "?")
            sim     = r.get("similarity", 0.0)
            print(f"  {rank}. {dept} {number} — {title}  (similarity: {sim:.3f})")

        # Simple sanity check: top result should have similarity > 0.2
        top_sim = results[0].get("similarity", 0.0)
        if top_sim >= 0.2:
            passed += 1
        else:
            print(f"  ⚠ Low similarity ({top_sim:.3f}) — retrieval may need tuning.")
            failed += 1

    print(f"\n{'═' * 60}")
    print(f"Results: {passed} passed / {failed} failed / {len(TEST_QUERIES)} total")

    if failed == 0:
        print("✅ Retrieval is working. You're ready for Week 4.")
    elif failed <= 2:
        print("⚠  A few queries returned weak results — likely courses with missing descriptions.")
        print("   Re-run the catalog scraper with --dept to fill in descriptions, then re-embed.")
    else:
        print("✗  Multiple failures. Check that:")
        print("   1. 002_pgvector.sql was run in Supabase (extension + function)")
        print("   2. embed_courses.py ran successfully (at least some rows have embeddings)")
        print("   3. SUPABASE_SECRET_KEY in .env.local is the service-role key, not the anon key")


if __name__ == "__main__":
    main()
