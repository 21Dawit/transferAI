import { createClient } from "@supabase/supabase-js";
import * as fs from "fs";
import * as path from "path";
import { generatePlan } from "./generate_plan";

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SECRET_KEY!
);

const DE_ANZA_ID = "00000000-0000-0000-0000-000000000001";

// -----------------------------------------------------------------------
// Tool: lookup_articulation
// -----------------------------------------------------------------------

export async function lookupArticulation(input: {
  ccc_department: string;
  ccc_number: string;
  target_school?: string;
  major?: string;
}): Promise<string> {
  const { ccc_department, ccc_number, target_school, major } = input;
  const dept = ccc_department.toUpperCase().trim();
  const num  = ccc_number.toUpperCase().trim();

  const rawDir = path.join(process.cwd(), "data", "assist_raw");
  let assistData: any[] = [];

  try {
    const files = fs.readdirSync(rawDir).filter((f) => f.endsWith(".json"));
    for (const file of files) {
      const data = JSON.parse(fs.readFileSync(path.join(rawDir, file), "utf-8"));
      assistData.push({ file, data });
    }
  } catch (e) {
    return "Error reading ASSIST data files.";
  }

  const matches: string[] = [];

  for (const { data } of assistData) {
    const majorName = data.name || "Unknown Major";
    const year      = data.academicYear?.code || "";

    for (const art of data.articulations || []) {
      const sending = art.sendingArticulation;
      if (!sending) continue;

      const cccCourses: { dept: string; number: string; title: string }[] = [];
      for (const group of sending.courseGroups || []) {
        for (const item of group.items || []) {
          if (item.type === "Course") {
            cccCourses.push({ dept: item.prefix || "", number: item.courseNumber || "", title: item.courseTitle || "" });
          }
        }
      }

      const found = cccCourses.some(
        (c) =>
          c.dept.toUpperCase() === dept &&
          c.number.toUpperCase().replace(/\s/g, "") === num.replace(/\s/g, "")
      );
      if (!found) continue;

      let ucCourse = { dept: "", number: "", title: "" };
      for (const asset of data.templateAssets || []) {
        if (asset.type !== "RequirementGroup") continue;
        for (const section of asset.sections || []) {
          for (const row of section.rows || []) {
            if (row.position !== 0) continue;
            for (const cell of row.cells || []) {
              if (cell.id === art.id) {
                ucCourse = { dept: cell.course?.prefix || "", number: cell.course?.courseNumber || "", title: cell.course?.courseTitle || "" };
              }
            }
          }
        }
      }

      const cccStr = cccCourses.map((c) => `${c.dept} ${c.number} (${c.title})`).join(" OR ");
      const ucStr  = ucCourse.dept ? `${ucCourse.dept} ${ucCourse.number} — ${ucCourse.title}` : "a requirement in this major";

      matches.push(
        `✓ ${dept} ${num} satisfies ${ucStr} for ${majorName} (${year}) at UC Davis.\n` +
        `  CCC options: ${cccStr}\n  Source: assist.org`
      );
    }
  }

  if (matches.length === 0) {
    return (
      `No articulation found for ${dept} ${num} in ASSIST data for ${target_school || "UC Davis"}${major ? ` (${major})` : ""}.\n` +
      `This could mean:\n  • No direct articulation agreement\n  • May satisfy as an elective\n  • ASSIST data not yet loaded\nVerify at: https://assist.org`
    );
  }

  return matches.join("\n\n");
}

// -----------------------------------------------------------------------
// Tool: get_major_requirements
// -----------------------------------------------------------------------

export async function getMajorRequirements(input: {
  major_name: string;
  school?: string;
}): Promise<string> {
  const { major_name } = input;

  const igetcResult = await supabase
    .from("major_requirements")
    .select("area_code, area_name, units_required, notes, course_constraint")
    .eq("school_id", DE_ANZA_ID)
    .eq("requirement_type", "igetc")
    .order("area_code");

  if (igetcResult.error) return `Error fetching IGETC requirements: ${igetcResult.error.message}`;

  const rawDir = path.join(process.cwd(), "data", "assist_raw");
  const majorPrep: string[] = [];

  try {
    const files = fs.readdirSync(rawDir).filter((f) => f.endsWith(".json"));
    for (const file of files) {
      const data = JSON.parse(fs.readFileSync(path.join(rawDir, file), "utf-8"));
      for (const art of data.articulations || []) {
        const recv = art.receivingAttributes;
        if (!recv) continue;
        const isRequired = (recv.courseAttributes || []).some((a: any) => a.content?.toLowerCase().includes("required"));
        if (!isRequired) continue;
        for (const asset of data.templateAssets || []) {
          if (asset.type !== "RequirementGroup") continue;
          for (const section of asset.sections || []) {
            for (const row of section.rows || []) {
              if (row.position !== 0) continue;
              for (const cell of row.cells || []) {
                if (cell.id === art.id && cell.course) {
                  majorPrep.push(`${cell.course.prefix} ${cell.course.courseNumber} — ${cell.course.courseTitle}`);
                }
              }
            }
          }
        }
      }
    }
  } catch (e) {}

  const igetcLines = (igetcResult.data || []).map(
    (r: any) => `  Area ${r.area_code}: ${r.area_name} (${r.units_required} units) — ${r.notes}`
  );

  const sections: string[] = [`=== IGETC Requirements (for ${major_name} at UC Davis) ===`, ...igetcLines];
  if (majorPrep.length > 0) {
    sections.push(`\n=== Major Preparation (Required for Admission) ===`);
    sections.push(...majorPrep.map((m) => `  ${m}`));
  }
  sections.push(`\nSource: assist.org + igetc.assist.org`);
  return sections.join("\n");
}

// -----------------------------------------------------------------------
// Tool: search_courses
// -----------------------------------------------------------------------

export async function searchCourses(input: { query: string; limit?: number }): Promise<string> {
  const { query, limit = 5 } = input;

  const textResult = await supabase
    .from("courses")
    .select("department, number, title, units, description")
    .eq("school_id", DE_ANZA_ID)
    .ilike("title", `%${query}%`)
    .limit(limit);

  if (textResult.error || !textResult.data?.length) {
    return `No courses found matching "${query}".`;
  }

  return textResult.data
    .map((c: any) => `${c.department} ${c.number} — ${c.title} (${c.units} units)\n  ${c.description || "No description available."}`)
    .join("\n\n");
}

// -----------------------------------------------------------------------
// Tool definitions
// -----------------------------------------------------------------------

export const TOOL_DEFINITIONS = [
  {
    name: "lookup_articulation",
    description:
      "Look up whether a De Anza College course articulates to a UC or CSU requirement. " +
      "Use this whenever the student asks if a specific course 'counts', 'transfers', or 'satisfies' a requirement. Returns official ASSIST.org data.",
    input_schema: {
      type: "object",
      properties: {
        ccc_department: { type: "string", description: "De Anza department code, e.g. 'CIS', 'MATH', 'EWRT'" },
        ccc_number:     { type: "string", description: "Course number, e.g. '22A', '1A', '1B'" },
        target_school:  { type: "string", description: "Target university, e.g. 'UC Davis'" },
        major:          { type: "string", description: "Target major, e.g. 'Computer Science'" },
      },
      required: ["ccc_department", "ccc_number"],
    },
  },
  {
    name: "get_major_requirements",
    description:
      "Get the IGETC general education requirements and major preparation courses needed to transfer. " +
      "Use when student asks what classes they need or how to prepare for transfer.",
    input_schema: {
      type: "object",
      properties: {
        major_name: { type: "string", description: "Major name, e.g. 'Computer Science'" },
        school:     { type: "string", description: "Target school, e.g. 'UC Davis'" },
      },
      required: ["major_name"],
    },
  },
  {
    name: "search_courses",
    description:
      "Search the De Anza College course catalog. Use when student asks 'what courses cover X' or needs to find courses for a requirement.",
    input_schema: {
      type: "object",
      properties: {
        query: { type: "string", description: "Natural language search, e.g. 'intro to programming python'" },
        limit: { type: "number", description: "Max results (default 5)" },
      },
      required: ["query"],
    },
  },
  {
    name: "generate_plan",
    description:
      "Generate a complete term-by-term transfer plan for a student. Automatically places articulating major prep courses and IGETC requirements across terms. " +
      "Use when student asks 'make me a plan', 'what should my schedule look like', or 'plan my transfer'. " +
      "Returns a validated plan with any errors or warnings.",
    input_schema: {
      type: "object",
      properties: {
        major:             { type: "string",  description: "Target major, e.g. 'Computer Science'" },
        target_school:     { type: "string",  description: "Target UC/CSU, e.g. 'UC Davis'" },
        transfer_year:     { type: "string",  description: "Intended transfer year, e.g. '2026'" },
        units_per_term:    { type: "number",  description: "Max units per term (default 15)" },
        terms_available:   { type: "number",  description: "Number of terms remaining (default 4)" },
        completed_courses: { type: "array", items: { type: "string" }, description: "Courses already completed, e.g. ['MATH 1A', 'EWRT 1A']" },
      },
      required: ["major"],
    },
  },
];

// -----------------------------------------------------------------------
// Dispatcher
// -----------------------------------------------------------------------

export async function dispatchTool(toolName: string, toolInput: any): Promise<string> {
  switch (toolName) {
    case "lookup_articulation":   return await lookupArticulation(toolInput);
    case "get_major_requirements": return await getMajorRequirements(toolInput);
    case "search_courses":        return await searchCourses(toolInput);
    case "generate_plan":         return await generatePlan(toolInput);
    default:                      return `Unknown tool: ${toolName}`;
  }
}
