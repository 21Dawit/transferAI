import Anthropic from "@anthropic-ai/sdk";
import { createClient } from "@/lib/supabase/server";
import { TOOL_DEFINITIONS, dispatchTool } from "@/lib/tools";

const client = new Anthropic({
  apiKey: process.env.ANTHROPIC_API_KEY,
});

function buildSystemPrompt(profile?: {
  intended_major:       string | null;
  transfer_year:        number | null;
  unit_load_preference: number | null;
} | null, targetSchool?: string | null): string {
  const profileSection = profile?.intended_major
    ? `
## Student Profile
- Major: ${profile.intended_major}
- Target school: ${targetSchool || "UC Davis"}
- Transfer year: ${profile.transfer_year || "2026"}
- Units per term: ${profile.unit_load_preference || 15}

Use this profile as context for all responses. When the student says "my major" or "my plan", refer to this profile. When generating plans, use these exact values unless the student specifies otherwise.`
    : "";

  return `You are TransferAI, an expert academic counselor helping De Anza College students plan their transfer to UC and CSU schools.

You have access to four tools:
- lookup_articulation: Check if a De Anza course satisfies a UC/CSU requirement (uses official ASSIST.org data)
- get_major_requirements: Get IGETC and major prep requirements for a specific major
- search_courses: Search the De Anza course catalog
- generate_plan: Generate a complete term-by-term transfer plan
${profileSection}
## Rules
- ALWAYS use tools to answer questions about articulation, requirements, or courses. Never guess or answer from memory.
- ALWAYS cite your source (ASSIST.org or the De Anza catalog) when providing articulation information.
- When a student asks if a course transfers or counts, ALWAYS call lookup_articulation first.
- When a student asks what classes they need, what requirements exist, what IGETC is, or how to prepare for transfer — ALWAYS call get_major_requirements first. Never explain IGETC or requirements from memory.
- When a student asks for a plan, schedule, or what to take next — ALWAYS call generate_plan first.
- When a student asks what courses are available or offered at De Anza — ALWAYS call search_courses first.
- Never answer requirement or articulation questions without calling the appropriate tool first.
- Be concise, accurate, and encouraging. Students are often stressed — be their expert guide.`;
}

export async function POST(request: Request) {
  const { message, history = [] } = await request.json();

  if (!message || typeof message !== "string") {
    return new Response(JSON.stringify({ error: "message field is required" }), {
      status: 400,
      headers: { "Content-Type": "application/json" },
    });
  }

  // Load user profile
  let profile      = null;
  let targetSchool = null;

  try {
    const supabase = createClient();
    const { data: { user } } = await supabase.auth.getUser();

    if (user) {
      const { data: profileData } = await supabase
        .from("profiles")
        .select("intended_major, transfer_year, unit_load_preference")
        .eq("user_id", user.id)
        .single();

      profile = profileData;

      const { data: targetData } = await supabase
        .from("target_schools")
        .select("schools(name)")
        .eq("user_id", user.id)
        .order("priority", { ascending: false })
        .limit(1)
        .single();

      targetSchool = (targetData?.schools as any)?.name || "UC Davis";
    }
  } catch (e) {
    // No auth — continue without profile
  }

  const systemPrompt = buildSystemPrompt(profile, targetSchool);

  const messages: any[] = [
    ...history,
    { role: "user", content: message },
  ];

  const encoder = new TextEncoder();

  const readable = new ReadableStream({
    async start(controller) {
      try {
        let continueLoop = true;

        while (continueLoop) {
          const response = await client.messages.create({
            model:      "claude-sonnet-4-5",
            max_tokens: 4096,
            system:     systemPrompt,
            tools:      TOOL_DEFINITIONS as any,
            messages,
          });

          for (const block of response.content) {
            if (block.type === "text") {
              controller.enqueue(encoder.encode(block.text));
            }
          }

          if (response.stop_reason === "tool_use") {
            const toolResults: any[] = [];

            for (const block of response.content) {
              if (block.type !== "tool_use") continue;
              controller.enqueue(encoder.encode(`\n[Checking ${block.name}...]\n`));
              const result = await dispatchTool(block.name, block.input);
              toolResults.push({ type: "tool_result", tool_use_id: block.id, content: result });
            }

            messages.push({ role: "assistant", content: response.content });
            messages.push({ role: "user",      content: toolResults });
          } else {
            continueLoop = false;
            messages.push({ role: "assistant", content: response.content });
          }
        }

        controller.close();
      } catch (err: any) {
        controller.enqueue(encoder.encode(`\nError: ${err.message || "Unknown error"}`));
        controller.close();
      }
    },
  });

  return new Response(readable, {
    headers: {
      "Content-Type":           "text/plain; charset=utf-8",
      "Transfer-Encoding":      "chunked",
      "X-Content-Type-Options": "nosniff",
    },
  });
}
