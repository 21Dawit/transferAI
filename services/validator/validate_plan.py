"""
validate_plan.py — Deterministic rule engine for transfer plan validation

This is called from the agent AFTER Claude drafts a plan. It runs hard rules
and returns structured violations. Claude then revises the plan to fix them.

Rules enforced:
  1. Unit cap per term (respects user's unit_load_preference)
  2. Articulation gaps (courses in plan that don't articulate to target major)
  3. Missing major prep (required courses not in any term)
  4. Duplicate courses (same course in multiple terms)
  5. Total units reasonable for transfer timeline

Usage:
    from services.validator.validate_plan import validate_plan, PlanInput
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


# ---------------------------------------------------------------------------
# Data types — these mirror what the agent will construct
# ---------------------------------------------------------------------------

@dataclass
class PlannedCourse:
    department: str
    number: str
    title: str
    units: float
    catalog_url: str | None = None
    articulates_to: list[str] = field(default_factory=list)
    # e.g. ["ECS 032 @ UC Davis"] — populated from ASSIST lookup


@dataclass
class PlanTerm:
    label: str          # e.g. "Fall 2025"
    order: int          # 1, 2, 3... for sequencing
    courses: list[PlannedCourse] = field(default_factory=list)

    @property
    def total_units(self) -> float:
        return sum(c.units for c in self.courses)


@dataclass
class PlanInput:
    """Everything the validator needs to check a plan."""
    terms: list[PlanTerm]
    unit_load_cap: int               # from user profile
    required_major_prep: list[str]   # e.g. ["CIS 22A", "MATH 1A", "MATH 1B"]
    target_school: str               # e.g. "UC Davis"
    target_major: str                # e.g. "Computer Science"


# ---------------------------------------------------------------------------
# Violation types
# ---------------------------------------------------------------------------

ViolationSeverity = Literal["error", "warning"]

@dataclass
class Violation:
    rule:        str                # machine-readable rule ID
    severity:    ViolationSeverity
    term_label:  str | None        # which term (None = plan-level)
    message:     str               # human-readable description
    suggestion:  str               # what to do about it


# ---------------------------------------------------------------------------
# Individual rule checkers
# ---------------------------------------------------------------------------

def check_unit_caps(terms: list[PlanTerm], cap: int) -> list[Violation]:
    """Flag any term that exceeds the student's unit load cap."""
    violations = []
    for term in terms:
        if term.total_units > cap:
            violations.append(Violation(
                rule="UNIT_CAP_EXCEEDED",
                severity="error",
                term_label=term.label,
                message=(
                    f"{term.label} has {term.total_units:.1f} units, "
                    f"but your load cap is {cap} units."
                ),
                suggestion=(
                    f"Move one course from {term.label} to a later term, "
                    f"or increase your unit cap in your profile if your schedule allows."
                )
            ))
    return violations


def check_duplicates(terms: list[PlanTerm]) -> list[Violation]:
    """Flag the same course appearing in more than one term."""
    seen: dict[str, str] = {}   # course_key → first term label
    violations = []
    for term in terms:
        for course in term.courses:
            key = f"{course.department} {course.number}"
            if key in seen:
                violations.append(Violation(
                    rule="DUPLICATE_COURSE",
                    severity="error",
                    term_label=term.label,
                    message=f"{key} appears in both {seen[key]} and {term.label}.",
                    suggestion=f"Remove {key} from one of those terms."
                ))
            else:
                seen[key] = term.label
    return violations


def check_missing_major_prep(
    terms: list[PlanTerm],
    required: list[str],
    target_school: str,
    target_major: str,
) -> list[Violation]:
    """
    Flag major prep courses that are required but not in any term.
    `required` is a list of course strings like "CIS 22A" or "MATH 1A".
    """
    planned = {
        f"{c.department} {c.number}"
        for term in terms
        for c in term.courses
    }
    violations = []
    for req in required:
        if req not in planned:
            violations.append(Violation(
                rule="MISSING_MAJOR_PREP",
                severity="error",
                term_label=None,
                message=(
                    f"{req} is required for {target_major} at {target_school} "
                    f"but is not in any term of your plan."
                ),
                suggestion=f"Add {req} to an appropriate term before your transfer semester."
            ))
    return violations


def check_articulation_gaps(terms: list[PlanTerm], target_school: str) -> list[Violation]:
    """
    Flag courses that have no articulation to the target school.
    A course with an empty articulates_to list may be wasted units.
    """
    violations = []
    for term in terms:
        for course in term.courses:
            key = f"{course.department} {course.number}"
            if not course.articulates_to:
                violations.append(Violation(
                    rule="NO_ARTICULATION",
                    severity="warning",
                    term_label=term.label,
                    message=(
                        f"{key} has no confirmed articulation to {target_school}. "
                        f"It may count as an elective or not transfer at all."
                    ),
                    suggestion=(
                        f"Verify {key} on ASSIST.org for {target_school}. "
                        f"If it doesn't articulate, consider replacing it with a course that does."
                    )
                ))
    return violations


def check_total_units(terms: list[PlanTerm]) -> list[Violation]:
    """
    Warn if the plan has fewer than 60 units total (typical UC transfer minimum)
    or more than 90 (diminishing returns, may count against TAG).
    """
    total = sum(t.total_units for t in terms)
    violations = []
    if total < 60:
        violations.append(Violation(
            rule="INSUFFICIENT_TOTAL_UNITS",
            severity="warning",
            term_label=None,
            message=f"Plan total is {total:.1f} units. UC transfer typically requires 60 transferable units.",
            suggestion="Add courses to reach at least 60 units before your transfer semester."
        ))
    elif total > 90:
        violations.append(Violation(
            rule="EXCESSIVE_TOTAL_UNITS",
            severity="warning",
            term_label=None,
            message=f"Plan total is {total:.1f} units, which is high. UC limits unit transfer credit.",
            suggestion=(
                "Review whether all courses are necessary. "
                "UC accepts a maximum of 70 semester units from a CCC."
            )
        ))
    return violations


def check_empty_terms(terms: list[PlanTerm]) -> list[Violation]:
    """Flag terms with no courses (usually a planning mistake)."""
    return [
        Violation(
            rule="EMPTY_TERM",
            severity="warning",
            term_label=term.label,
            message=f"{term.label} has no courses.",
            suggestion=f"Add courses to {term.label} or remove the term from the plan."
        )
        for term in terms
        if not term.courses
    ]


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

@dataclass
class ValidationResult:
    is_valid: bool               # True only if zero errors (warnings allowed)
    errors: list[Violation]
    warnings: list[Violation]
    summary: str                 # One-line summary for the agent prompt

    @classmethod
    def from_violations(cls, violations: list[Violation]) -> "ValidationResult":
        errors   = [v for v in violations if v.severity == "error"]
        warnings = [v for v in violations if v.severity == "warning"]
        is_valid = len(errors) == 0

        if is_valid and not warnings:
            summary = "Plan is valid with no issues."
        elif is_valid:
            summary = f"Plan is valid but has {len(warnings)} warning(s) to review."
        else:
            summary = (
                f"Plan has {len(errors)} error(s) and {len(warnings)} warning(s). "
                f"Must fix errors before finalizing."
            )
        return cls(is_valid=is_valid, errors=errors, warnings=warnings, summary=summary)


def validate_plan(plan: PlanInput) -> ValidationResult:
    """
    Run all rules against a plan and return a ValidationResult.

    Called by the agent after Claude drafts a plan:
        result = validate_plan(plan_input)
        if not result.is_valid:
            # feed result back to Claude for revision
    """
    violations: list[Violation] = []

    violations += check_unit_caps(plan.terms, plan.unit_load_cap)
    violations += check_duplicates(plan.terms)
    violations += check_missing_major_prep(
        plan.terms, plan.required_major_prep,
        plan.target_school, plan.target_major
    )
    violations += check_articulation_gaps(plan.terms, plan.target_school)
    violations += check_total_units(plan.terms)
    violations += check_empty_terms(plan.terms)

    return ValidationResult.from_violations(violations)


# ---------------------------------------------------------------------------
# Pretty-print helper (for debugging / logging)
# ---------------------------------------------------------------------------

def format_result(result: ValidationResult) -> str:
    lines = [result.summary, ""]
    if result.errors:
        lines.append("ERRORS:")
        for v in result.errors:
            term = f"[{v.term_label}] " if v.term_label else ""
            lines.append(f"  ✗ {term}{v.message}")
            lines.append(f"    → {v.suggestion}")
    if result.warnings:
        lines.append("WARNINGS:")
        for v in result.warnings:
            term = f"[{v.term_label}] " if v.term_label else ""
            lines.append(f"  ⚠ {term}{v.message}")
            lines.append(f"    → {v.suggestion}")
    return "\n".join(lines)
