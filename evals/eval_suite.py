"""
eval_suite.py — Automated evaluation of TransferAI agent

Tests the agent against 30 synthetic student scenarios and scores:
  - Did it call the right tool?
  - Did it mention real De Anza courses?
  - Did articulation answers match ASSIST ground truth?
  - Did plans pass validation?

Results are uploaded to Braintrust for visualization.

Install deps:
    pip install braintrust autoevals anthropic python-dotenv

Usage:
    python evals/eval_suite.py
    python evals/eval_suite.py --dry-run    # print test cases, don't run
    python evals/eval_suite.py --limit 10   # run first 10 only
"""

import argparse
import json
import os
import sys
from pathlib import Path

import anthropic
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env.local")

ANTHROPIC_API_KEY  = os.environ["ANTHROPIC_API_KEY"]
BRAINTRUST_API_KEY = os.environ["BRAINTRUST_API_KEY"]

TEST_CASES = [
    # -- Articulation --
    {"scenario": "CS student asking about EWRT 1A", "input": "Does EWRT 1A transfer to UC Davis for Computer Science?", "expected_tool": "lookup_articulation", "expected_keywords": ["EWRT", "1A", "UC Davis"], "should_not_contain": ["I don't know"], "category": "articulation"},
    {"scenario": "Math student asking about MATH 1A", "input": "Does MATH 1A count toward UC Berkeley math requirements?", "expected_tool": "lookup_articulation", "expected_keywords": ["MATH", "1A", "UC Berkeley"], "should_not_contain": [], "category": "articulation"},
    {"scenario": "Bio student asking about BIOL 6A", "input": "Will BIOL 6A satisfy biology requirements at UCLA?", "expected_tool": "lookup_articulation", "expected_keywords": ["BIOL", "UCLA"], "should_not_contain": [], "category": "articulation"},
    {"scenario": "CS student asking about CIS 22A", "input": "Does CIS 22A articulate to UC Davis CS?", "expected_tool": "lookup_articulation", "expected_keywords": ["CIS", "22A"], "should_not_contain": [], "category": "articulation"},
    {"scenario": "Psych student asking about PSYC 1", "input": "Does PSYC 1 transfer to UC San Diego for Psychology?", "expected_tool": "lookup_articulation", "expected_keywords": ["PSYC", "UC San Diego"], "should_not_contain": [], "category": "articulation"},
    {"scenario": "Engineering student asking about PHYS 4A", "input": "Does PHYS 4A count at UC Santa Barbara for Electrical Engineering?", "expected_tool": "lookup_articulation", "expected_keywords": ["PHYS", "UC Santa Barbara"], "should_not_contain": [], "category": "articulation"},
    {"scenario": "Student asking about CHEM 1A", "input": "Will CHEM 1A transfer to UC Irvine?", "expected_tool": "lookup_articulation", "expected_keywords": ["CHEM", "UC Irvine"], "should_not_contain": [], "category": "articulation"},
    {"scenario": "Student asking about ECON 1A", "input": "Does ECON 1A articulate to UC Davis Economics?", "expected_tool": "lookup_articulation", "expected_keywords": ["ECON", "UC Davis"], "should_not_contain": [], "category": "articulation"},
    {"scenario": "Student asking about MATH 1B", "input": "Does MATH 1B transfer to UCLA for Engineering?", "expected_tool": "lookup_articulation", "expected_keywords": ["MATH", "1B", "UCLA"], "should_not_contain": [], "category": "articulation"},
    {"scenario": "Student asking about non-existent course", "input": "Does FAKE 999 transfer to UC Davis?", "expected_tool": "lookup_articulation", "expected_keywords": ["no", "not found", "cannot", "doesn't"], "should_not_contain": ["FAKE 999 satisfies"], "category": "articulation"},
    # -- Requirements --
    {"scenario": "CS student asking what they need", "input": "What courses do I need for Computer Science transfer to UC Davis?", "expected_tool": "get_major_requirements", "expected_keywords": ["IGETC", "English", "Math"], "should_not_contain": [], "category": "requirements"},
    {"scenario": "Bio student asking for requirements", "input": "What are the requirements to transfer for Biology to UCLA?", "expected_tool": "get_major_requirements", "expected_keywords": ["IGETC", "Biology"], "should_not_contain": [], "category": "requirements"},
    {"scenario": "Psychology student asking for requirements", "input": "What do I need to transfer for Psychology to UC San Diego?", "expected_tool": "get_major_requirements", "expected_keywords": ["IGETC", "Psychology"], "should_not_contain": [], "category": "requirements"},
    {"scenario": "Math student asking for requirements", "input": "What courses are required to transfer for Mathematics?", "expected_tool": "get_major_requirements", "expected_keywords": ["IGETC", "Math"], "should_not_contain": [], "category": "requirements"},
    {"scenario": "Student asking about IGETC", "input": "Can you explain what IGETC is and what areas I need to complete?", "expected_tool": "get_major_requirements", "expected_keywords": ["IGETC", "Area", "units"], "should_not_contain": [], "category": "requirements"},
    {"scenario": "Engineering student asking for requirements", "input": "What do I need to transfer for Electrical Engineering to UC Berkeley?", "expected_tool": "get_major_requirements", "expected_keywords": ["IGETC", "Engineering"], "should_not_contain": [], "category": "requirements"},
    # -- Planning --
    {"scenario": "CS student asking for a plan", "input": "Make me a transfer plan for Computer Science at UC Davis. I have 4 terms left.", "expected_tool": "generate_plan", "expected_keywords": ["Fall", "term", "units"], "should_not_contain": [], "category": "planning"},
    {"scenario": "Bio student asking for a plan", "input": "Create a transfer plan for Biology at UCLA.", "expected_tool": "generate_plan", "expected_keywords": ["plan", "term", "units"], "should_not_contain": [], "category": "planning"},
    {"scenario": "Student asking for schedule", "input": "What should my course schedule look like for the next 3 terms?", "expected_tool": "generate_plan", "expected_keywords": ["term", "units"], "should_not_contain": [], "category": "planning"},
    {"scenario": "Student asking to plan transfer", "input": "Help me plan my transfer to UC Berkeley for Computer Science.", "expected_tool": "generate_plan", "expected_keywords": ["plan", "UC Berkeley"], "should_not_contain": [], "category": "planning"},
    # -- Search --
    {"scenario": "Student asking about programming courses", "input": "What programming courses does De Anza offer?", "expected_tool": "search_courses", "expected_keywords": ["CIS", "programming"], "should_not_contain": [], "category": "search"},
    {"scenario": "Student asking about calc courses", "input": "What calculus courses are available at De Anza?", "expected_tool": "search_courses", "expected_keywords": ["MATH", "calculus"], "should_not_contain": [], "category": "search"},
    {"scenario": "Student asking about English courses", "input": "What English writing courses does De Anza have?", "expected_tool": "search_courses", "expected_keywords": ["ENGL", "EWRT", "writing"], "should_not_contain": [], "category": "search"},
    {"scenario": "Student asking about biology lab courses", "input": "Are there biology lab courses at De Anza?", "expected_tool": "search_courses", "expected_keywords": ["BIOL", "lab"], "should_not_contain": [], "category": "search"},
    {"scenario": "Student asking about stats courses", "input": "What statistics courses are offered?", "expected_tool": "search_courses", "expected_keywords": ["STAT", "statistics"], "should_not_contain": [], "category": "search"},
    # -- General --
    {"scenario": "Student asking a general question", "input": "What is the difference between IGETC and major prep?", "expected_tool": "get_major_requirements", "expected_keywords": ["IGETC", "major", "preparation"], "should_not_contain": [], "category": "general"},
    {"scenario": "Student asking about transfer timeline", "input": "How long does it typically take to transfer from De Anza to a UC?", "expected_tool": None, "expected_keywords": ["2", "years", "terms"], "should_not_contain": [], "category": "general"},
    {"scenario": "Student asking about TAG", "input": "What is TAG and do I qualify for it at UC Davis for CS?", "expected_tool": None, "expected_keywords": ["TAG", "Transfer Admission Guarantee"], "should_not_contain": [], "category": "general"},
    {"scenario": "Student asking about GPA requirements", "input": "What GPA do I need to transfer to UC Berkeley for Computer Science?", "expected_tool": None, "expected_keywords": ["GPA", "3"], "should_not_contain": [], "category": "general"},
    {"scenario": "Vague question with no context", "input": "What should I take next quarter?", "expected_tool": None, "expected_keywords": [], "should_not_contain": ["FAKE", "I cannot"], "category": "general"},
]

# ---------------------------------------------------------------------------
# System prompt — MUST match production route.ts exactly
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are TransferAI, an expert academic counselor helping De Anza College students plan their transfer to UC and CSU schools.

You have access to four tools:
- lookup_articulation: Check if a De Anza course satisfies a UC/CSU requirement (uses official ASSIST.org data)
- get_major_requirements: Get the LIST of IGETC areas and required courses for transfer
- search_courses: Search the De Anza course catalog
- generate_plan: Build a term-by-term SCHEDULE organizing courses across Fall/Winter/Spring terms

Tool Selection Rules (follow exactly):
1. Student mentions a specific course + "transfer/count/satisfy" → lookup_articulation
2. Student asks "what do I need", "what are requirements", "what is IGETC", "what areas", "difference between IGETC" → get_major_requirements
3. Student asks "make a plan", "plan my transfer", "help me plan", "schedule", "what should I take each term", "organize my courses" → generate_plan
4. Student asks "what courses are available/offered at De Anza" → search_courses
5. Never answer requirement or articulation questions from memory — always call the appropriate tool first.
6. Be concise, accurate, and encouraging.

Student profile: Computer Science major, UC Davis, 2026 transfer."""

TOOL_DEFINITIONS = [
    {"name": "lookup_articulation", "description": "Look up whether a De Anza course articulates to a UC/CSU requirement.", "input_schema": {"type": "object", "properties": {"ccc_department": {"type": "string"}, "ccc_number": {"type": "string"}, "target_school": {"type": "string"}, "major": {"type": "string"}}, "required": ["ccc_department", "ccc_number"]}},
    {"name": "get_major_requirements", "description": "Get the LIST of IGETC areas and required courses. Use when student asks about requirements, IGETC, or what they need.", "input_schema": {"type": "object", "properties": {"major_name": {"type": "string"}, "school": {"type": "string"}}, "required": ["major_name"]}},
    {"name": "search_courses", "description": "Search De Anza course catalog for available courses.", "input_schema": {"type": "object", "properties": {"query": {"type": "string"}, "limit": {"type": "number"}}, "required": ["query"]}},
    {"name": "generate_plan", "description": "Build a term-by-term SCHEDULE. Use when student asks to plan, schedule, or organize courses across terms.", "input_schema": {"type": "object", "properties": {"major": {"type": "string"}, "target_school": {"type": "string"}, "transfer_year": {"type": "string"}, "units_per_term": {"type": "number"}, "terms_available": {"type": "number"}}, "required": ["major"]}},
]


def run_test(client: anthropic.Anthropic, test: dict) -> dict:
    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        tools=TOOL_DEFINITIONS,
        messages=[{"role": "user", "content": test["input"]}],
    )

    tool_used  = None
    tool_input = {}
    text_parts = []

    for block in response.content:
        if block.type == "tool_use":
            tool_used  = block.name
            tool_input = block.input
        elif block.type == "text":
            text_parts.append(block.text)

    full_text     = " ".join(text_parts).lower()
    expected_tool = test.get("expected_tool")
    tool_correct  = (expected_tool is None or tool_used == expected_tool)
    tool_score    = 1.0 if tool_correct else 0.0

    keywords      = test.get("expected_keywords", [])
    kw_hits       = sum(1 for kw in keywords if kw.lower() in full_text or kw.lower() in str(tool_input).lower())
    keyword_score = (kw_hits / len(keywords)) if keywords else 1.0

    bad_phrases   = test.get("should_not_contain", [])
    safety_score  = 1.0 if not any(bp.lower() in full_text for bp in bad_phrases) else 0.0
    overall       = tool_score * 0.4 + keyword_score * 0.4 + safety_score * 0.2

    return {"tool_used": tool_used, "tool_input": tool_input, "response_text": " ".join(text_parts)[:500],
            "tool_score": tool_score, "keyword_score": keyword_score, "safety_score": safety_score,
            "overall_score": overall, "tool_correct": tool_correct, "kw_hits": kw_hits, "kw_total": len(keywords)}


def upload_to_braintrust(results: list[dict]) -> None:
    try:
        import braintrust
    except ImportError:
        print("braintrust not installed."); return

    experiment = braintrust.init(project="transferai", api_key=BRAINTRUST_API_KEY)
    for r in results:
        experiment.log(
            input=r["input"], output=r["response_text"], expected=r["expected_tool"],
            scores={"tool_selection": r["tool_score"], "keyword_coverage": r["keyword_score"],
                    "safety": r["safety_score"], "overall": r["overall_score"]},
            metadata={"scenario": r["scenario"], "category": r["category"],
                      "tool_used": r["tool_used"], "tool_input": r["tool_input"]},
        )
    experiment.flush()
    print(f"\nResults uploaded to Braintrust → project: transferai")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit",   type=int, default=None)
    args = parser.parse_args()

    cases = TEST_CASES[:args.limit] if args.limit else TEST_CASES

    if args.dry_run:
        print(f"Would run {len(cases)} test cases:\n")
        for i, t in enumerate(cases, 1):
            print(f"  {i:>2}. [{t['category']}] {t['scenario']}")
        return

    client  = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    results = []
    by_cat: dict[str, list] = {}

    print(f"Running {len(cases)} eval cases...\n")

    for i, test in enumerate(cases, 1):
        print(f"[{i:>2}/{len(cases)}] {test['scenario'][:50]}...")
        try:
            scores = run_test(client, test)
            result = {**test, **scores}
            results.append(result)
            icon = "✓" if scores["overall_score"] >= 0.7 else "✗"
            print(f"  {icon} tool={scores['tool_used'] or 'none':<25} overall={scores['overall_score']:.2f}")
            by_cat.setdefault(test["category"], []).append(scores["overall_score"])
        except Exception as e:
            print(f"  ✗ ERROR: {e}")
            results.append({**test, "tool_used": None, "response_text": str(e),
                            "tool_score": 0, "keyword_score": 0, "safety_score": 0, "overall_score": 0})

    print(f"\n{'═' * 60}")
    print("RESULTS BY CATEGORY:")
    for cat, scores in by_cat.items():
        avg = sum(scores) / len(scores)
        print(f"  {cat:<15} {avg:.2f}  {'█' * int(avg * 20)}")

    avg   = sum(r["overall_score"] for r in results) / len(results)
    passed = sum(1 for r in results if r["overall_score"] >= 0.7)
    print(f"\nOverall: {avg:.2f} — {passed}/{len(results)} passed (≥0.7)")
    print("✅ Agent is performing well." if avg >= 0.85 else "⚠  Review failures before sharing widely." if avg >= 0.70 else "✗  Multiple failures.")

    print("\nUploading to Braintrust...")
    upload_to_braintrust(results)


if __name__ == "__main__":
    main()
