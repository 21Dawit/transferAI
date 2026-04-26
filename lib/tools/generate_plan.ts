/**
 * generate_plan.ts — Plan generator tool
 *
 * Takes a student profile and produces a validated term-by-term transfer plan.
 * Runs the plan through validate_plan and returns both the plan and any issues.
 */

import { createClient } from "@supabase/supabase-js";
import * as fs from "fs";
import * as path from "path";

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SECRET_KEY!
);

const DE_ANZA_ID = "00000000-0000-0000-0000-000000000001";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface CoursePlan {
  department: string;
  number: string;
  title: string;
  units: number;
  articulates_to: string[];
  reason: string; // why this course is in the plan
}

interface TermPlan {
  label: string;
  order: number;
  courses: CoursePlan[];
  total_units: number;
}

interface GeneratedPlan {
  student_profile: {
    major: string;
    target_school: string;
    transfer_year: string;
    unit_load_cap: number;
    terms_available: number;
  };
  terms: TermPlan[];
  total_units: number;
  validation: {
    is_valid: boolean;
    errors: string[];
    warnings: string[];
    summary: string;
  };
  notes: string[];
}

// ---------------------------------------------------------------------------
// Load articulation data from ASSIST JSON
// ---------------------------------------------------------------------------

function loadArticulationMap(): Map<string, string[]> {
  /**
   * Returns a map of UC course → De Anza courses that satisfy it.
   * e.g. "MAT 021A" → ["MATH 1A"]
   */
  const map = new Map<string, string[]>();
  const rawDir = path.join(process.cwd(), "data", "assist_raw");

  try {
    const files = fs.readdirSync(rawDir).filter((f) => f.endsWith(".json"));
    for (const file of files) {
      const data = JSON.parse(fs.readFileSync(path.join(rawDir, file), "utf-8"));

      for (const art of data.articulations || []) {
        const sending = art.sendingArticulation;
        if (!sending) continue;

        const cccCourses: string[] = [];
        for (const group of sending.courseGroups || []) {
          for (const item of group.items || []) {
            if (item.type === "Course") {
              cccCourses.push(`${item.prefix} ${item.courseNumber}`);
            }
          }
        }

        // Find the UC course
        for (const asset of data.templateAssets || []) {
          if (asset.type !== "RequirementGroup") continue;
          for (const section of asset.sections || []) {
            for (const row of section.rows || []) {
              if (row.position !== 0) continue;
              for (const cell of row.cells || []) {
                if (cell.id === art.id && cell.course) {
                  const ucKey = `${cell.course.prefix} ${cell.course.courseNumber}`;
                  if (cccCourses.length > 0) {
                    map.set(ucKey, cccCourses);
                  }
                }
              }
            }
          }
        }
      }
    }
  } catch (e) {
    // No ASSIST files — return empty map
  }

  return map;
}

// ---------------------------------------------------------------------------
// Fetch De Anza courses for a given department
// ---------------------------------------------------------------------------

async function fetchCoursesByDept(dept: string): Promise<any[]> {
  const result = await supabase
    .from("courses")
    .select("department, number, title, units, description")
    .eq("school_id", DE_ANZA_ID)
    .eq("department", dept.toUpperCase())
    .order("number");
  return result.data || [];
}

// ---------------------------------------------------------------------------
// Fetch IGETC requirements
// ---------------------------------------------------------------------------

async function fetchIGETC(): Promise<any[]> {
  const result = await supabase
    .from("major_requirements")
    .select("area_code, area_name, units_required, course_constraint")
    .eq("school_id", DE_ANZA_ID)
    .eq("requirement_type", "igetc")
    .order("area_code");
  return result.data || [];
}

// ---------------------------------------------------------------------------
// Core plan generator
// ---------------------------------------------------------------------------

export async function generatePlan(input: {
  major: string;
  target_school?: string;
  transfer_year?: string;
  units_per_term?: number;
  terms_available?: number;
  completed_courses?: string[]; // e.g. ["MATH 1A", "EWRT 1A"]
}): Promise<string> {
  const {
    major,
    target_school    = "UC Davis",
    transfer_year    = "2026",
    units_per_term   = 15,
    terms_available  = 4,
    completed_courses = [],
  } = input;

  const artMap  = loadArticulationMap();
  const igetc   = await fetchIGETC();
  const notes: string[] = [];

  // Build list of courses to place
  // Priority 1: courses that directly articulate to UC requirements
  const toPlace: CoursePlan[] = [];
  const completedSet = new Set(completed_courses.map((c) => c.toUpperCase().trim()));

  // Add articulating courses
  for (const [ucCourse, cccOptions] of artMap.entries()) {
    if (cccOptions.length === 0) continue;
    const best = cccOptions[0]; // take the first option
    const key  = best.toUpperCase().trim();

    if (completedSet.has(key)) continue;

    // Look up course details from Supabase
    const parts = best.split(" ");
    const dept  = parts[0];
    const num   = parts.slice(1).join(" ");

    const courses = await fetchCoursesByDept(dept);
    const found   = courses.find(
      (c) => c.number.toUpperCase().trim() === num.toUpperCase().trim()
    );

    toPlace.push({
      department:     dept,
      number:         num,
      title:          found?.title || best,
      units:          found?.units || 4,
      articulates_to: [ucCourse],
      reason:         `Satisfies ${ucCourse} requirement for ${major} at ${target_school}`,
    });
  }

  // Add IGETC courses (simplified — use example courses from course_constraint)
  const igetcPriority = ["1A", "1B", "2", "4", "3A", "3B", "5A", "5B"];
  for (const areaCode of igetcPriority) {
    const area = igetc.find((r) => r.area_code === areaCode);
    if (!area) continue;

    const examples: string[] = area.course_constraint?.example_courses || [];
    for (const ex of examples.slice(0, 1)) {
      const parts = ex.split(" ");
      const dept  = parts[0];
      const num   = parts.slice(1).join(" ").split(" (")[0].trim();
      const key   = `${dept} ${num}`.toUpperCase().trim();

      if (completedSet.has(key)) continue;
      if (toPlace.some((c) => `${c.department} ${c.number}`.toUpperCase() === key)) continue;

      const courses = await fetchCoursesByDept(dept);
      const found   = courses.find(
        (c) => c.number.toUpperCase().trim() === num.toUpperCase().trim()
      );

      if (!found) continue;

      toPlace.push({
        department:     dept,
        number:         num,
        title:          found.title,
        units:          found.units || 3,
        articulates_to: [],
        reason:         `Satisfies IGETC Area ${areaCode}: ${area.area_name}`,
      });
      break;
    }
  }

  // Distribute courses across terms
  const terms: TermPlan[] = [];
  let courseIdx = 0;

  const termLabels = [
    "Fall 2024", "Winter 2025", "Spring 2025",
    "Fall 2025", "Winter 2026", "Spring 2026",
  ].slice(0, terms_available);

  for (let t = 0; t < terms_available && courseIdx < toPlace.length; t++) {
    const termCourses: CoursePlan[] = [];
    let termUnits = 0;

    while (courseIdx < toPlace.length) {
      const course = toPlace[courseIdx];
      if (termUnits + course.units > units_per_term) break;
      termCourses.push(course);
      termUnits += course.units;
      courseIdx++;
    }

    if (termCourses.length > 0) {
      terms.push({
        label:       termLabels[t] || `Term ${t + 1}`,
        order:       t + 1,
        courses:     termCourses,
        total_units: termUnits,
      });
    }
  }

  if (courseIdx < toPlace.length) {
    notes.push(
      `${toPlace.length - courseIdx} additional courses could not fit within ${terms_available} terms at ${units_per_term} units/term. Consider increasing units per term or adding a term.`
    );
  }

  const totalUnits = terms.reduce((s, t) => s + t.total_units, 0);

  // Basic validation
  const errors:   string[] = [];
  const warnings: string[] = [];

  if (totalUnits < 60) warnings.push(`Total units (${totalUnits}) is below the 60-unit UC transfer minimum.`);
  if (totalUnits > 90) warnings.push(`Total units (${totalUnits}) exceeds UC's 70-unit transfer credit cap.`);

  const artCourses = toPlace.filter((c) => c.articulates_to.length > 0);
  if (artCourses.length === 0) errors.push("No articulating major prep courses found. Check ASSIST data.");

  const validation = {
    is_valid: errors.length === 0,
    errors,
    warnings,
    summary:
      errors.length === 0 && warnings.length === 0
        ? "Plan looks good."
        : errors.length > 0
        ? `${errors.length} error(s) need fixing.`
        : `${warnings.length} warning(s) to review.`,
  };

  const plan: GeneratedPlan = {
    student_profile: {
      major,
      target_school,
      transfer_year,
      unit_load_cap:   units_per_term,
      terms_available,
    },
    terms,
    total_units: totalUnits,
    validation,
    notes,
  };

  // Format as readable text for Claude to present
  const lines: string[] = [
    `📋 Transfer Plan: ${major} → ${target_school} (${transfer_year})`,
    `${"─".repeat(60)}`,
  ];

  for (const term of plan.terms) {
    lines.push(`\n${term.label}  (${term.total_units} units)`);
    for (const c of term.courses) {
      lines.push(`  • ${c.department} ${c.number} — ${c.title} (${c.units} units)`);
      lines.push(`    ${c.reason}`);
    }
  }

  lines.push(`\n${"─".repeat(60)}`);
  lines.push(`Total: ${totalUnits} units across ${terms.length} terms`);
  lines.push(`\nValidation: ${validation.summary}`);

  if (validation.errors.length > 0) {
    lines.push("\nErrors:");
    validation.errors.forEach((e) => lines.push(`  ✗ ${e}`));
  }
  if (validation.warnings.length > 0) {
    lines.push("\nWarnings:");
    validation.warnings.forEach((w) => lines.push(`  ⚠ ${w}`));
  }
  if (notes.length > 0) {
    lines.push("\nNotes:");
    notes.forEach((n) => lines.push(`  • ${n}`));
  }

  lines.push(`\nSource: ASSIST.org articulation data + De Anza 2025–2026 catalog`);

  return lines.join("\n");
}
