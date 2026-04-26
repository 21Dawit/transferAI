"""
test_validate_plan.py — Unit tests for the validate_plan rule engine

Run with:
    cd C:\\Users\\dawit\\code\\transferAI
    python -m pytest tests/test_validate_plan.py -v

Or without pytest:
    python tests/test_validate_plan.py
"""

import sys
from pathlib import Path

# Allow imports from project root
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.validator.validate_plan import (
    PlannedCourse,
    PlanInput,
    PlanTerm,
    ValidationResult,
    validate_plan,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_course(dept: str, number: str, units: float = 4.0,
                articulates_to: list[str] = None) -> PlannedCourse:
    return PlannedCourse(
        department=dept,
        number=number,
        title=f"{dept} {number}",
        units=units,
        articulates_to=articulates_to or [],
    )


def make_term(label: str, order: int, courses: list[PlannedCourse]) -> PlanTerm:
    return PlanTerm(label=label, order=order, courses=courses)


def make_plan(terms: list[PlanTerm], cap: int = 16,
              required: list[str] = None) -> PlanInput:
    return PlanInput(
        terms=terms,
        unit_load_cap=cap,
        required_major_prep=required or [],
        target_school="UC Davis",
        target_major="Computer Science",
    )


def errors(result: ValidationResult) -> list[str]:
    return [v.rule for v in result.errors]


def warnings(result: ValidationResult) -> list[str]:
    return [v.rule for v in result.warnings]


# ---------------------------------------------------------------------------
# 1. UNIT_CAP_EXCEEDED
# ---------------------------------------------------------------------------

def test_unit_cap_ok():
    term = make_term("Fall 2025", 1, [
        make_course("CIS", "22A", 4.5),
        make_course("MATH", "1A", 5.0),
        make_course("ENGL", "1A", 5.0),
    ])
    result = validate_plan(make_plan([term], cap=16))
    assert "UNIT_CAP_EXCEEDED" not in errors(result)


def test_unit_cap_exceeded():
    term = make_term("Fall 2025", 1, [
        make_course("CIS", "22A", 5.0),
        make_course("MATH", "1A", 5.0),
        make_course("ENGL", "1A", 5.0),
        make_course("PHYS", "4A", 5.0),
    ])
    result = validate_plan(make_plan([term], cap=16))
    assert "UNIT_CAP_EXCEEDED" in errors(result)


def test_unit_cap_exact_boundary():
    term = make_term("Fall 2025", 1, [
        make_course("CIS", "22A", 8.0),
        make_course("MATH", "1A", 8.0),
    ])
    result = validate_plan(make_plan([term], cap=16))
    assert "UNIT_CAP_EXCEEDED" not in errors(result)


def test_unit_cap_multiple_terms_only_one_over():
    t1 = make_term("Fall 2025", 1, [make_course("MATH", "1A", 10.0), make_course("CIS", "22A", 8.0)])
    t2 = make_term("Winter 2026", 2, [make_course("ENGL", "1A", 5.0)])
    result = validate_plan(make_plan([t1, t2], cap=16))
    assert "UNIT_CAP_EXCEEDED" in errors(result)
    cap_errors = [v for v in result.errors if v.rule == "UNIT_CAP_EXCEEDED"]
    assert len(cap_errors) == 1
    assert cap_errors[0].term_label == "Fall 2025"


def test_unit_cap_low_cap():
    term = make_term("Fall 2025", 1, [
        make_course("CIS", "22A", 4.5),
        make_course("MATH", "1A", 5.0),
    ])
    result = validate_plan(make_plan([term], cap=9))
    assert "UNIT_CAP_EXCEEDED" in errors(result)


# ---------------------------------------------------------------------------
# 2. DUPLICATE_COURSE
# ---------------------------------------------------------------------------

def test_no_duplicates():
    t1 = make_term("Fall 2025", 1, [make_course("CIS", "22A")])
    t2 = make_term("Winter 2026", 2, [make_course("CIS", "22B")])
    result = validate_plan(make_plan([t1, t2]))
    assert "DUPLICATE_COURSE" not in errors(result)


def test_duplicate_across_terms():
    t1 = make_term("Fall 2025", 1, [make_course("MATH", "1A")])
    t2 = make_term("Winter 2026", 2, [make_course("MATH", "1A")])
    result = validate_plan(make_plan([t1, t2]))
    assert "DUPLICATE_COURSE" in errors(result)


def test_duplicate_same_term():
    """Two sections of the same course in the same term — also a duplicate."""
    t1 = make_term("Fall 2025", 1, [
        make_course("ENGL", "1A"),
        make_course("ENGL", "1A"),
    ])
    result = validate_plan(make_plan([t1]))
    assert "DUPLICATE_COURSE" in errors(result)


def test_no_false_positive_similar_numbers():
    """CIS 22A and CIS 22B are different courses — should not flag."""
    t1 = make_term("Fall 2025", 1, [make_course("CIS", "22A")])
    t2 = make_term("Winter 2026", 2, [make_course("CIS", "22B")])
    result = validate_plan(make_plan([t1, t2]))
    assert "DUPLICATE_COURSE" not in errors(result)


# ---------------------------------------------------------------------------
# 3. MISSING_MAJOR_PREP
# ---------------------------------------------------------------------------

def test_all_major_prep_present():
    t1 = make_term("Fall 2025", 1, [make_course("CIS", "22A")])
    t2 = make_term("Winter 2026", 2, [make_course("MATH", "1A")])
    result = validate_plan(make_plan([t1, t2], required=["CIS 22A", "MATH 1A"]))
    assert "MISSING_MAJOR_PREP" not in errors(result)


def test_missing_one_major_prep():
    t1 = make_term("Fall 2025", 1, [make_course("CIS", "22A")])
    result = validate_plan(make_plan([t1], required=["CIS 22A", "MATH 1A"]))
    missing = [v for v in result.errors if v.rule == "MISSING_MAJOR_PREP"]
    assert len(missing) == 1
    assert "MATH 1A" in missing[0].message


def test_missing_multiple_major_prep():
    t1 = make_term("Fall 2025", 1, [make_course("ENGL", "1A")])
    result = validate_plan(make_plan([t1], required=["CIS 22A", "MATH 1A", "MATH 1B"]))
    missing = [v for v in result.errors if v.rule == "MISSING_MAJOR_PREP"]
    assert len(missing) == 3


def test_no_major_prep_required():
    t1 = make_term("Fall 2025", 1, [make_course("ENGL", "1A")])
    result = validate_plan(make_plan([t1], required=[]))
    assert "MISSING_MAJOR_PREP" not in errors(result)


# ---------------------------------------------------------------------------
# 4. NO_ARTICULATION (warning)
# ---------------------------------------------------------------------------

def test_all_courses_articulate():
    t1 = make_term("Fall 2025", 1, [
        make_course("CIS", "22A", articulates_to=["ECS 032 @ UC Davis"]),
        make_course("MATH", "1A", articulates_to=["MAT 021A @ UC Davis"]),
    ])
    result = validate_plan(make_plan([t1]))
    assert "NO_ARTICULATION" not in warnings(result)


def test_course_with_no_articulation():
    t1 = make_term("Fall 2025", 1, [
        make_course("CIS", "22A", articulates_to=[]),
    ])
    result = validate_plan(make_plan([t1]))
    assert "NO_ARTICULATION" in warnings(result)


def test_mixed_articulation():
    t1 = make_term("Fall 2025", 1, [
        make_course("CIS", "22A", articulates_to=["ECS 032 @ UC Davis"]),
        make_course("DANC", "1A", articulates_to=[]),
    ])
    result = validate_plan(make_plan([t1]))
    art_warnings = [v for v in result.warnings if v.rule == "NO_ARTICULATION"]
    assert len(art_warnings) == 1
    assert "DANC" in art_warnings[0].message


# ---------------------------------------------------------------------------
# 5. INSUFFICIENT / EXCESSIVE TOTAL UNITS
# ---------------------------------------------------------------------------

def test_total_units_ok():
    # 4 terms × 4 courses × 4 units = 64 units
    terms = [
        make_term(f"Term {i}", i, [make_course("CIS", f"{i}{j}", 4.0) for j in range(4)])
        for i in range(1, 5)
    ]
    result = validate_plan(make_plan(terms))
    assert "INSUFFICIENT_TOTAL_UNITS" not in warnings(result)
    assert "EXCESSIVE_TOTAL_UNITS" not in warnings(result)


def test_insufficient_units():
    t1 = make_term("Fall 2025", 1, [make_course("CIS", "22A", 4.0)])
    result = validate_plan(make_plan([t1]))
    assert "INSUFFICIENT_TOTAL_UNITS" in warnings(result)


def test_excessive_units():
    terms = [
        make_term(f"Term {i}", i, [make_course("CIS", f"{i}{j}", 5.0) for j in range(5)])
        for i in range(1, 5)
    ]  # 4 × 5 × 5 = 100 units
    result = validate_plan(make_plan(terms))
    assert "EXCESSIVE_TOTAL_UNITS" in warnings(result)


# ---------------------------------------------------------------------------
# 6. EMPTY_TERM
# ---------------------------------------------------------------------------

def test_no_empty_terms():
    t1 = make_term("Fall 2025", 1, [make_course("CIS", "22A")])
    result = validate_plan(make_plan([t1]))
    assert "EMPTY_TERM" not in warnings(result)


def test_empty_term_flagged():
    t1 = make_term("Fall 2025", 1, [make_course("CIS", "22A")])
    t2 = make_term("Winter 2026", 2, [])
    result = validate_plan(make_plan([t1, t2]))
    assert "EMPTY_TERM" in warnings(result)


# ---------------------------------------------------------------------------
# 7. is_valid semantics
# ---------------------------------------------------------------------------

def test_valid_plan():
    t1 = make_term("Fall 2025", 1, [
        make_course("CIS", "22A", 4.5, articulates_to=["ECS 032 @ UC Davis"]),
        make_course("MATH", "1A", 5.0, articulates_to=["MAT 021A @ UC Davis"]),
    ])
    t2 = make_term("Winter 2026", 2, [
        make_course("CIS", "22B", 4.5, articulates_to=["ECS 036 @ UC Davis"]),
        make_course("MATH", "1B", 5.0, articulates_to=["MAT 021B @ UC Davis"]),
    ])
    t3 = make_term("Spring 2026", 3, [
        make_course("CIS", "22C", 4.5, articulates_to=["ECS 040 @ UC Davis"]),
        make_course("ENGL", "1A", 5.0, articulates_to=["UWP 001 @ UC Davis"]),
    ])
    result = validate_plan(make_plan(
        [t1, t2, t3], cap=12,
        required=["CIS 22A", "MATH 1A"]
    ))
    assert result.is_valid


def test_warnings_dont_make_plan_invalid():
    """Warnings alone should not set is_valid = False."""
    t1 = make_term("Fall 2025", 1, [
        make_course("CIS", "22A", articulates_to=[]),  # no articulation → warning
    ])
    result = validate_plan(make_plan([t1]))
    # will have INSUFFICIENT_TOTAL_UNITS and NO_ARTICULATION warnings
    # but no errors → still valid
    assert result.is_valid


def test_one_error_makes_plan_invalid():
    t1 = make_term("Fall 2025", 1, [make_course("CIS", "22A", 20.0)])
    result = validate_plan(make_plan([t1], cap=16))
    assert not result.is_valid


# ---------------------------------------------------------------------------
# Run without pytest
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    tests = [
        test_unit_cap_ok,
        test_unit_cap_exceeded,
        test_unit_cap_exact_boundary,
        test_unit_cap_multiple_terms_only_one_over,
        test_unit_cap_low_cap,
        test_no_duplicates,
        test_duplicate_across_terms,
        test_duplicate_same_term,
        test_no_false_positive_similar_numbers,
        test_all_major_prep_present,
        test_missing_one_major_prep,
        test_missing_multiple_major_prep,
        test_no_major_prep_required,
        test_all_courses_articulate,
        test_course_with_no_articulation,
        test_mixed_articulation,
        test_total_units_ok,
        test_insufficient_units,
        test_excessive_units,
        test_no_empty_terms,
        test_empty_term_flagged,
        test_valid_plan,
        test_warnings_dont_make_plan_invalid,
        test_one_error_makes_plan_invalid,
    ]

    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            print(f"  ✓ {t.__name__}")
            passed += 1
        except Exception as e:
            print(f"  ✗ {t.__name__}: {e}")
            failed += 1

    print(f"\n{'═' * 50}")
    print(f"{passed} passed / {failed} failed / {len(tests)} total")
    if failed == 0:
        print("✅ All tests pass. Rule engine is solid.")
    else:
        print("✗  Fix failures before proceeding to Week 5.")
