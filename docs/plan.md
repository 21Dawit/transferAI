# CCC Transfer Navigator — Project Plan

An AI-powered transfer planning assistant for California Community College students, consolidating ASSIST, UC TAP, CVC Exchange, IGETC/CSU GE, catalogs, and professor data into a single conversational workspace.

---

## 1. Product description

**CCC Transfer Navigator** is an LLM-powered transfer planning copilot built specifically for California Community College students aiming to transfer to UC, CSU, and select private universities. Where ASSIST answers "does course X articulate to Y?" and UC TAP answers "am I on track for this one UC?", Transfer Navigator answers the question students actually ask: *"Given who I am, where I am, and where I want to go — what should I take next semester, and why?"*

The product ingests a student's CCC, completed coursework, GPA, intended major, target universities, and life constraints, then produces a personalized, term-by-term plan grounded in official articulation data and major preparation requirements. Every recommendation carries a citation to its source (ASSIST agreement, UC/CSU catalog page, IGETC worksheet) and an explicit disclaimer that the final word belongs to a human counselor.

The core bet: students don't need another data source. They need a reasoning layer on top of the twelve they already have.

---

## 2. User personas

**Maya — First-gen, undecided, overwhelmed.** Sophomore at a suburban CCC. Family pressure to transfer "somewhere good." Has 24 units done but no major declared. Needs the product to reduce the universe of choices and translate jargon (TAG, IGETC, ADT) into plain English.

**Diego — STEM-focused, UC-bound, high-achieving.** Wants UCLA or Berkeley CS. Already has a 3.8, took CS 1 and calc. Needs the product to catch missed major prep (discrete math, linear algebra sequencing), surface realistic admit rates, and warn him when his plan front-loads risk.

**Priya — Working adult, part-time, time-constrained.** 28, works 30 hrs/week, can do max 9 units/term, summers available. Needs the product to build a 4-year plan that respects her load cap and flags when CVC Exchange online sections could unlock otherwise-impossible scheduling.

**Jordan — Private school aspirant.** Targeting USC, Santa Clara, Stanford. Needs the product to handle non-ASSIST articulation (private schools don't always publish agreements), explain portfolio/essay weight, and model the tradeoff between UC-style major prep and holistic-review prep.

**Alex — Late-declared major switcher.** Was pre-nursing, now wants econ. 45 units done, many now wasted. Needs the product to do a "sunk cost" audit: what already counts, what transfers as elective, and whether a 2-year or 3-year timeline is more realistic.

---

## 3. Key features ranked by importance

Tier 1 — must exist for the product to be credible:

1. **ASSIST articulation checker** — wrong articulation data is worse than no product. This is the trust anchor.
2. **Personalized term-by-term planner** — the headline output. Everything else feeds this.
3. **Chat-based AI transfer counselor** — the interaction model. Without conversation, it's just another form.
4. **Major preparation checklist** — the single biggest reason students get rejected with high GPAs.
5. **Source citations on every recommendation** — non-negotiable for trust and for your portfolio story.

Tier 2 — make the product noticeably better:

6. **Multi-school comparison view** — students almost always apply to 3+ schools; showing one plan that works across them is the real unlock.
7. **IGETC / CSU GE checker** — mechanical but high-value; GE mistakes cost semesters.
8. **Transfer risk detector** — the "you're missing CHEM 1B and your target major requires it" warning.
9. **Student profile / dashboard memory** — persistent state; otherwise students re-explain everything each session.
10. **Application deadline tracker** — lightweight but high utility around Nov 30 (UC) and Nov 30/Feb 1 windows.

Tier 3 — differentiators and nice-to-haves:

11. **Course availability finder** (current term offerings at their CCC + CVC Exchange cross-reference)
12. **Professor and workload insights** (aggregated, with heavy disclaimers)
13. **GPA / admissions competitiveness estimate** (show ranges, not predictions)
14. **Clear verify-with-counselor disclaimers throughout**

---

## 4. Realistic MVP

The MVP exists to prove two things: *articulation data can be served accurately through an LLM*, and *students will trust a plan that cites its sources*. Everything else is scope creep until those are proven.

**MVP scope (ship in 6–8 weeks):**

- Onboarding flow capturing: CCC, completed courses, GPA, intended major, 1–3 target UC/CSU schools, transfer year
- ASSIST articulation lookup for the student's CCC → target school → major combination, cached locally
- Major prep checklist auto-generated from ASSIST + catalog data
- IGETC checker (CSU GE can wait)
- Chat interface with retrieval over cached articulation + catalog data
- One generated plan: remaining terms until transfer, with courses placed by term
- Every plan item links to its ASSIST agreement or catalog page
- Disclaimer banner + counselor-verification CTA on every plan

**Explicitly out of MVP:** private schools, professor ratings, competitiveness scoring, CVC Exchange, deadline tracker, multi-school diff view, account system beyond magic-link email.

Pick 1 CCC and 2 target schools for launch. Depth beats breadth here — a product that works perfectly for De Anza → UC Davis CS is more impressive than one that half-works for 50 combinations.

---

## 5. Full version roadmap

**Phase 1: MVP (weeks 1–8).** Single CCC, 2–3 targets, articulation + plan + citations.

**Phase 2: Breadth (weeks 9–16).** 10–15 CCCs, all UCs, top 10 CSUs. CSU GE. Multi-school comparison view. Student dashboard with saved plans.

**Phase 3: Depth (weeks 17–24).** CVC Exchange integration for online course discovery. Professor/workload layer (Rate My Professor + course rigor heuristics, aggregated). Competitiveness ranges based on published admit data by major.

**Phase 4: Scale (weeks 25–40).** All 116 CCCs. Private schools via catalog scraping where ASSIST isn't authoritative. Mobile-optimized PWA. Counselor-facing view (invitation-only beta).

**Phase 5: Community + Intelligence (ongoing).** Anonymous aggregate: "students with your profile typically take X next." Peer review of plans. Counselor export (PDF). SMS deadline reminders.

---

## 6. Recommended tech stack

**Frontend:** Next.js 14 with the App Router, TypeScript, Tailwind, shadcn/ui. Server components for the plan-rendering pages (fast, SEO-friendly); client components for the chat. Vercel for hosting.

**Backend:** Next.js route handlers for most endpoints. A separate Python FastAPI service for the RAG/agent layer — Python's LLM ecosystem (LangChain, LlamaIndex, Instructor for structured output) is more mature than JS equivalents, and you want that maturity on the reasoning path. Deploy the Python service on Railway or Fly.io.

**Database:** Postgres via Supabase. Use pgvector for embeddings (avoids running a separate vector DB for MVP). Supabase Auth handles login. Row-level security for profile data.

**LLM layer:** Claude API. Use Claude Opus 4.7 for the main counselor chat and plan generation where reasoning depth matters; Claude Haiku 4.5 for cheap operations like classifying user intent, extracting course codes from free text, and summarizing search results. Anthropic's tool use (function calling) is what drives the agent.

**Scraping / ingestion:** Playwright for ASSIST (dynamic JS site), plain `requests` + BeautifulSoup for static catalog pages. Run as scheduled jobs (GitHub Actions cron or Supabase Edge Functions) to refresh caches nightly/weekly.

**Observability:** Langfuse (open source, self-hostable) or LangSmith for LLM traces — critical when debugging why the agent picked the wrong course. Sentry for app errors. PostHog for product analytics.

**Auth + payments (later):** Clerk if Supabase Auth becomes limiting. Stripe for eventual monetization (if ever).

**Why this stack:** it's what companies actually use in 2026, it's free or cheap at student scale, and every piece is something you can defend in an internship interview.

---

## 7. Database schema

Core tables, with the important relationships called out:

```
users
  id, email, created_at, current_ccc_id, intended_transfer_year

profiles
  user_id (FK), intended_major, gpa, unit_load_preference,
  work_hours_per_week, summer_available, winter_available

schools
  id, name, type (CCC | UC | CSU | PRIVATE), ipeds_id, canonical_url

courses
  id, school_id (FK), department, number, title, units,
  description, catalog_url, last_seen_at

completed_courses
  user_id (FK), course_id (FK), grade, term_taken

target_schools
  user_id (FK), school_id (FK), priority (1..n)

major_requirements
  id, school_id (FK), major_name, requirement_type
    (major_prep | lower_div | ge | elective),
  course_constraint (JSON: e.g. "any of CSE 11, CSE 15"),
  source_url

articulation_agreements
  id, from_ccc_id (FK), to_school_id (FK), major_name,
  effective_year, source_url, last_fetched_at

articulation_rows
  agreement_id (FK), from_course_id (FK), to_course_id (FK),
  relationship (direct | series | no_articulation | with_other),
  notes, raw_payload (JSONB)  -- keep the unprocessed ASSIST data

plans
  id, user_id (FK), created_at, name, status (draft | active)

plan_terms
  id, plan_id (FK), term_label ("Fall 2026"), term_order,
  target_units

plan_courses
  plan_term_id (FK), course_id (FK), rationale,
  citations (JSONB array of source URLs with timestamps)

conversations
  id, user_id (FK), created_at, title

messages
  id, conversation_id (FK), role (user | assistant | tool),
  content, tool_calls (JSONB), citations (JSONB), created_at

professors
  id, school_id (FK), name, department

professor_ratings_cache
  professor_id (FK), source, avg_rating, difficulty,
  sample_size, last_fetched_at, disclaimer_shown_version

deadlines
  school_id (FK), cycle_year, type (app_open | app_due | tag_due),
  date, source_url

audit_log
  user_id, action, target_table, target_id, timestamp
  -- for any write to plans or profile, for debugging & trust
```

Two schema principles worth internalizing: (1) cache every external source with `last_fetched_at` and `source_url` so every claim is traceable; (2) store raw payloads in JSONB alongside parsed fields so when ASSIST changes format, you can reparse without re-scraping.

---

## 8. AI / RAG architecture

The naive version — stuff articulation data into a prompt and ask Claude — will fail for the same reason every naive RAG fails: the model will hallucinate course codes and invent articulations when the retrieval misses. Here is the non-naive architecture.

**Retrieval has two modes, and the agent picks between them:**

*Precise retrieval* (SQL) for anything articulation-related. If a user says "does CIS 22A at De Anza count for CS 31 at Berkeley?", the agent should never use vector search. It should call a `lookup_articulation(from_school, from_course, to_school, to_course)` tool that hits Postgres directly and returns a ground-truth row or `no_agreement_found`. Vector search on articulation data is the single fastest way to ship a product that is confidently wrong.

*Semantic retrieval* (pgvector) for fuzzy questions: "what classes should I take if I like econ and data?", "explain IGETC Area 3", "what does this major emphasize?". Embed catalog descriptions, major pages, and IGETC/GE explanations; use hybrid BM25 + dense with a reranker (Cohere Rerank or a small cross-encoder).

**Agent loop.** Claude with tool use. Tools exposed to the model:

- `get_student_profile()` — current profile, completed courses, targets
- `lookup_articulation(from_school, from_course, to_school_major)` — SQL
- `get_major_requirements(school, major)` — SQL
- `check_ge_completion(framework, completed_courses)` — computes IGETC/CSU GE
- `search_catalog(query, school)` — semantic search
- `lookup_professor(school, name)` — cached aggregate
- `validate_plan(plan_draft)` — runs a rule engine over a candidate plan and returns violations (prereq order, unit cap, missing major prep, articulation gaps)
- `get_deadlines(schools, cycle_year)` — SQL

**Plan generation is a two-pass process.** Pass 1: Claude drafts a plan from profile + requirements. Pass 2: `validate_plan` runs deterministic checks and hands violations back to Claude for revision. Repeat up to 3 times. This is the pattern that distinguishes "LLM that sometimes outputs a good plan" from "LLM that reliably outputs a valid plan."

**Grounding and citations.** Every fact in an assistant response must be traceable to a retrieval call. Enforce this at prompt-level ("cite the source URL for every requirement you mention") and at output-level (structured output where each claim has a `source_id` field). When a citation is missing, the UI should visibly flag the claim as unverified rather than rendering it as confident advice.

**Model routing.** Classify the user turn with Haiku (intent: articulation lookup / plan request / general question / off-topic). Route articulation-only turns to a Haiku-powered fast path with tool use. Route plan generation and ambiguous counseling questions to Opus. This alone will cut your API spend by ~70%.

**Guardrails.** A pre-generation check that refuses to give plan advice if the profile is missing critical fields (no target school, no major). A post-generation check that scans the assistant output for patterns like "guaranteed admission" or "this will definitely transfer" and rewrites them — the product is not allowed to promise outcomes.

---

## 9. Data sources and responsible use

**ASSIST.org.** The authoritative source for CA public articulation. Dynamic site — use Playwright. Respect their robots.txt and ToS; they exist to serve students and counselors, and Anthropic-style scraping etiquette applies: identify your user agent, rate limit aggressively (one request per few seconds), cache everything, and don't re-fetch on every user session. Consider reaching out to ASSIST directly about API access once your prototype is working — they have been collaborative with student projects historically.

**UC TAP / UC Transfer Pathways.** Public UC pages, structured enough to parse. Cache by major.

**CSU major preparation pages.** Each CSU campus publishes its own major prep. Scrape per campus, per major. Be prepared for inconsistent formats.

**IGETC and CSU GE worksheets.** Published as PDFs by each CCC and by the UC/CSU systems. Parse once, structure into your `major_requirements` table with `requirement_type = 'ge'`.

**CCC catalogs.** Each college publishes a yearly catalog, usually PDF or HTML. Parse for course descriptions, prereqs, units. This is where semantic search earns its keep.

**CVC Exchange.** California Virtual Campus has an API for cross-college online courses. Use it for the course availability finder.

**Rate My Professor.** Sensitive. The data is noisy, self-selected, and sometimes unfair to instructors. If you use it: aggregate only, require a minimum sample size (20+), display heavy disclaimers, never show individual comments, and give instructors a way to request removal. Consider whether you need it at all for MVP.

**Reddit / Discord / student forums.** Do not scrape. If you want student-perspective data, build an opt-in "share your experience" feature with your own users.

**FERPA considerations.** You are storing student educational information (completed courses, grades). You are not a school so FERPA technically doesn't apply to you directly, but treat the data as if it did: encryption at rest, auth-gated access, explicit consent on signup, delete-my-data endpoint. This is both the right thing and a great thing to talk about in interviews.

**A PII inventory is worth keeping.** What you store, why, who can access it, how long you keep it. Write this in your README.

---

## 10. Risks and limitations

**Hallucinated articulation is the existential risk.** A plan that confidently tells a student CIS 22A covers CS 31 when it doesn't can cost them a semester. This is why the architecture forces articulation lookups through SQL with `no_agreement_found` as a first-class return value, not through the LLM's memory.

**Data staleness.** Articulation agreements update annually; catalogs shift each term. Build freshness into the UI: every citation shows "last updated" and the plan shows a banner when any underlying source is >90 days stale.

**Scope creep toward being a counselor.** You are not a counselor. You are a tool that helps students prepare for counselor conversations. Every output should end with "verify with your CCC counselor before enrolling." Make this structural, not just a footer.

**Legal / ToS risk on scraping.** Read each source's terms. Rate-limit. Cache. Don't republish raw copyrighted catalog text — store and index it, but in the UI show short excerpts with links back to the source.

**Equity risk.** An AI counselor that works best for students who already know which questions to ask will widen the gap, not close it. Design onboarding for students who have never heard "IGETC" in their lives. Test with actual first-gen students before scaling.

**Over-reliance.** Some students will take the plan as gospel and skip counselor appointments. Mitigate with explicit prompts to book a counselor meeting after plan generation, and with "things to ask your counselor about" lists generated alongside each plan.

**Cost.** Opus calls are not cheap. Budget $50–$150/month for a pre-revenue beta with 20–50 active users. Model routing (Haiku for classification, Opus for reasoning) is what keeps this sustainable.

---

## 11. UI/UX layout

The product has three primary surfaces, and the hierarchy between them is important.

**The Dashboard** is the home. On it: a progress ring showing "requirements complete / total requirements" for the top-priority target school, a timeline visualizing completed terms + planned terms + transfer semester, a warnings panel surfacing the top 3 risks detected, and entry points to the chat and the plan editor. This is what a student sees every time they log in.

**The Chat + Plan split view** is where most of the work happens. Left pane: conversation with the AI counselor. Right pane: the live plan, which updates as the conversation progresses. When the AI makes a plan change ("I'm moving MATH 1B to Spring"), the right pane animates the change and shows the citation that justifies it. This split-pane pattern is what makes the product feel like a tool rather than a chatbot.

**The Plan Editor** is a standalone view for serious editing — drag courses between terms, lock specific courses, see articulation status inline as chips (green = articulates, yellow = articulates via series, red = no agreement), view unit totals per term, and see a diff against the AI's recommended plan.

Visual principles: dense information with generous whitespace (ASSIST-style density, Linear-style whitespace). Citations always visible — never hide them behind a "sources" toggle. Color warnings meaningfully: red for "this will delay transfer," yellow for "verify with counselor," blue for informational. Mobile: collapse split view into tabs; the chat stays full-width.

Accessibility is not optional for a product serving CCC students, many of whom use assistive tech. Hit WCAG AA from day one, not at "polish phase."

---

## 12. Example user flows

**Flow 1: New user, first plan.** Maya signs up → completes a 7-field onboarding (CCC, completed courses via course-code autocomplete, GPA, two target schools, intended major "Business or Econ — not sure," transfer year 2027, unit cap 12) → lands on the dashboard with a ghost plan and a prompt: "Let's figure out which major. I'll ask 3 questions." → chats with the AI, which narrows econ vs business based on her interests → the AI generates a 3-term plan → Maya clicks a course, sees the articulation agreement and why it's included → saves the plan → gets an email reminder in 6 weeks to revisit.

**Flow 2: Returning user, plan revision.** Diego logs in → dashboard shows he got a B- in Calc 2, below the typical admit threshold for Berkeley CS → warning banner: "Your Berkeley CS competitiveness shifted. Want to revise?" → clicks yes → chat: "Here are three ways to strengthen your application: retake for a better grade, add a stats course to show trend, strengthen your other major prep. Want to see plans for each?" → picks "stats course" → AI adjusts the plan → Diego compares against his saved version → saves as "v2."

**Flow 3: Edge case, major switch.** Alex tells the chat: "I was pre-nursing, now I want to do econ. What already counts?" → AI calls `get_completed_courses` + `get_major_requirements(school, major=econ)` + diffs them → returns: "Of your 45 units, 22 apply to econ directly, 15 count as GE or elective, 8 won't count. Here's a realistic timeline — 3 terms to transfer-ready, or 4 if you want to retake the B-." → Alex asks "what would my counselor say about this?" → AI generates a bulleted question list for the counselor meeting.

**Flow 4: The uncomfortable truth flow.** Priya's current plan assumes she can do 12 units/term. Based on her 30 hrs/week work schedule, the AI flags this as high-risk and suggests 9 units with a longer timeline. Priya pushes back: "I need to transfer in 2 years." AI: "I hear you. Here's what 12 units + 30 hours of work typically looks like in terms of GPA impact, based on published load-vs-GPA research. Still want to proceed? I'll build that plan, but flag terms where CVC Exchange online options could ease the commute."

---

## 13. Example prompts the assistant should handle

Articulation-direct: *"Does MATH 1A at Santa Monica College transfer to UCLA as Math 31A?"* *"What's the ASSIST agreement between Mt. SAC and UC Irvine for CS?"*

Planning: *"Build me a plan to transfer to San Diego State as an accounting major by Fall 2027."* *"I can only do 9 units and I need to finish in 2 years. Is that realistic?"* *"Rearrange my plan to put all my hard classes in separate terms."*

Comparative: *"Compare what I'd need for UC Davis vs Cal Poly SLO for mechanical engineering."* *"Which of my target schools is the safest admit given my GPA?"*

Diagnostic: *"Am I missing any major prep for psych at UCSD?"* *"What's my biggest risk right now?"* *"Why did you put BIOL 2A in spring instead of fall?"*

GE-focused: *"Am I done with IGETC?"* *"What's the shortest path to finishing CSU GE?"* *"Can ENGL 1C double-count for Areas 1A and 3B?"*

Exploratory: *"I like writing and people. What majors should I look at?"* *"What does 'impacted major' mean and does it apply to me?"* *"Explain TAG in plain English."*

Logistical: *"Any of my required classes on CVC Exchange this summer?"* *"When's the UC application deadline?"* *"What do I ask my counselor about at my next appointment?"*

Off-topic (should redirect): *"Write me a personal statement."* — the product can offer feedback but should not ghostwrite application materials; surface the UC/CSU essay guidance and recommend the CCC's Transfer Center.

---

## 14. Resume bullet points

Use numbers wherever possible. Update these as the project evolves.

- Built CCC Transfer Navigator, a full-stack AI transfer advising platform that unifies ASSIST articulation, IGETC/CSU GE worksheets, and UC/CSU major prep requirements into a personalized term-by-term planner; serves [N] California Community College students across [M] CCCs.
- Designed a two-tier retrieval architecture combining Postgres + SQL for authoritative articulation lookups with pgvector hybrid search for catalog semantic queries, eliminating LLM hallucination on articulation facts (validated on [N] test cases with 0 false-positive articulations).
- Implemented a plan-validate-repair agent loop using Claude tool use and a deterministic rule engine for prereq ordering and unit caps, producing valid plans on [X]% of generations vs [Y]% for single-pass generation.
- Cut per-conversation LLM cost by ~70% via a Haiku-classifies / Opus-reasons model routing strategy while maintaining response quality on a 100-prompt eval set.
- Built a citation-first UX where every plan recommendation links to its source (ASSIST agreement, catalog URL, IGETC worksheet) with last-updated timestamps and stale-data warnings.
- Ingested and parsed [N] ASSIST agreements and [M] catalog pages via Playwright scrapers with rate limiting, source attribution, and nightly refresh jobs.
- Stack: Next.js 14, TypeScript, FastAPI, Postgres + pgvector, Supabase, Claude API (Opus 4.7 + Haiku 4.5), Playwright, Langfuse.

---

## 15. Three-month build plan

**Month 1 — Foundations and data.**

Week 1: Repo setup, Next.js + Supabase + FastAPI scaffolding, auth working, Claude API hello-world. Write the README with your PII inventory and disclaimers up front.

Week 2: Schema migrations, seed data for 1 CCC + 2 target schools + 1 major. ASSIST scraper v1 for that triple. Manual validation against the live ASSIST site — you cannot skip this; it's how you build trust in your own data.

Week 3: Catalog scraper for the chosen CCC. Ingest course descriptions. Set up pgvector, write the embedding pipeline, verify retrieval works on real queries.

Week 4: Parse IGETC worksheet for the chosen CCC into structured requirements. Build the rule-engine skeleton for `validate_plan`. Write 20+ unit tests on articulation lookup before touching the LLM.

**Month 2 — The agent and the plan.**

Week 5: First tool-using agent loop with Claude. Just two tools: `lookup_articulation` and `get_major_requirements`. Get the agent to answer "does X articulate to Y?" with citations. Instrument with Langfuse.

Week 6: Add `validate_plan`. Build the plan-draft → validate → repair loop. Target: produce one valid plan end-to-end from a hardcoded profile.

Week 7: Frontend — onboarding flow, dashboard skeleton, chat UI with message streaming, plan-render component. Wire to the backend. Make it ugly but real.

Week 8: Frontend polish pass. Citations rendered as chips. Warnings as colored banners. Mobile responsive. Start dogfooding with 3–5 friends at your CCC.

**Month 3 — Trust, breadth, and portfolio polish.**

Week 9: Eval harness. Write 50–100 test prompts with expected behaviors. Track accuracy on articulation, hallucination rate on plans, latency, cost per conversation. This is the week that turns the project from "cool" to "credible."

Week 10: Expand to 3–5 CCCs and 5 target schools. Most of this is data ingestion and making scrapers resilient.

Week 11: User testing with 10 CCC students recruited from your network. Record the sessions (with consent). Fix the top 5 confusion points.

Week 12: Write a proper landing page, a technical blog post explaining your architecture decisions (this is the piece recruiters will read), deploy to a real domain, record a 3-minute demo video. Open-source the repo with a thorough README.

---

## 16. What would make this project impressive

Most student LLM projects are "I wrapped GPT in a UI." What makes this one different, and what you should emphasize:

**The architectural honesty.** You can articulate why you do not let the LLM answer articulation questions from memory, and you can point to the code that enforces it. Interviewers love this because 90% of the AI projects they see ignore this problem.

**The eval culture.** You have a test set, you track hallucination and accuracy over time, and you can show the chart. This is what separates hobbyist AI work from production AI work.

**The data plumbing.** Scraping ASSIST and parsing catalogs is genuinely hard, and the fact that you did it — with rate limiting, caching, attribution, and refresh logic — demonstrates skills that transfer directly to any enterprise AI role.

**The responsible-AI story.** FERPA-equivalent handling, citation-first UX, refuse-to-promise guardrails, counselor-not-replacement framing. This is increasingly table-stakes for AI roles and most students don't think about it at all.

**The domain specificity.** A general-purpose chatbot competes with ChatGPT. A tool that knows more about CA transfer than any general model, and is used by real CCC students, competes with nothing. Write up the problem in a way that makes the reader understand why the system they'd naively design (single RAG over scraped pages) would fail.

**The user research.** Ten real student interviews is more impressive than a thousand GitHub stars. Quote the students in your write-up (with permission). Show before/after plans. Tell the story of a specific student.

**The portfolio artifacts to produce:**

1. Live demo at a real domain
2. Open-source repo with excellent README (problem, architecture diagram, eval numbers, setup instructions)
3. Technical blog post: "Why we built a SQL layer into our RAG system" or "What we learned from evaluating a transfer-advising LLM"
4. 3-minute demo video showing a real flow
5. Eval dashboard screenshot (public)
6. One-pager PDF for transfer applications / scholarship applications
7. Short Twitter/LinkedIn thread explaining the hardest problem you solved

For internships, lead with the blog post and the eval numbers. For transfer applications, lead with the problem statement and a user quote. Same project, two different stories.

---

## Appendix: Claude Desktop + Cowork + Claude Code setup for this project

The three Anthropic tools solve different parts of the build. Here is the division of labor that actually works.

### What each tool is best for

**Claude Desktop** is your thinking partner. Architecture discussions, reviewing scraper output, debating tradeoffs, drafting PRDs, reviewing your eval results. Connect MCP servers here so Claude can read your local files and repos while you talk to it. Model: Sonnet/Opus for the hard conversations.

**Claude Code** is your implementation partner. Runs in your terminal or inside the Code tab of the Desktop app. You delegate whole tasks: "scaffold the Next.js project with Supabase auth and Tailwind," "write the Playwright scraper for ASSIST," "add a citation chip component." It writes and edits files directly.

**Cowork** is the file- and task-automation agent — it's aimed at non-developer workflows (organizing research, handling documents, multi-step desktop tasks). For this project, use Cowork for the *research and ops* layer: organizing scraped HTML samples into folders, renaming downloaded PDFs (catalogs, IGETC worksheets) into a consistent scheme, batch-processing screenshots for your demo video, organizing the user-research recordings from week 11. You do not build the app with Cowork. You keep your project operationally sane with it.

### Step-by-step setup

**Step 1 — Install Claude Desktop.** Download from Anthropic's site for macOS or Windows (Linux isn't supported). Sign in. If you're on Pro, you get Sonnet; Max unlocks full Opus access and Cowork.

**Step 2 — Install the MCP extensions you actually need.** In Claude Desktop, go to Settings → Extensions → Browse extensions. Install:

- **Filesystem** — point it at your project directory (`~/code/ccc-navigator` or wherever) so Claude can read your repo during conversations
- **GitHub** — so Claude can read issues, review PRs, and inspect commits
- **Postgres** (community extension, or add via custom connector) — so Claude can query your dev database during debugging conversations
- **Puppeteer/Playwright MCP** — useful for inspecting scraper targets (ASSIST, catalog pages) without leaving chat

Don't install 20 of them. Each one is a subprocess and they slow startup. Three to five is the right number.

**Step 3 — Enable Cowork.** Requires Pro or Max. In Claude Desktop, look for the Cowork entry point (it's surfaced from the main app chrome). First task for Cowork: point it at a `~/ccc-navigator-research/` folder and say "organize this into subfolders by source: assist-samples, catalog-pdfs, igetc-worksheets, user-interviews." This is exactly the kind of grunt work Cowork is good at, and you will have a lot of it.

**Step 4 — Install Claude Code.** Easiest path: open the Code tab inside Claude Desktop. It gives you a graphical interface over Claude Code with parallel sessions, Git worktree isolation, integrated terminal, and visual diff review. If you prefer pure terminal, install via `npm install -g @anthropic-ai/claude-code` and run `claude` in your project directory.

**Step 5 — Initialize the project with Claude Code.** In the project directory:

```
claude
> Create a Next.js 14 app with TypeScript, Tailwind, shadcn/ui, and
  Supabase auth. Scaffold the route structure I'll describe next.
```

Let it work, review the diff, accept. Then iterate. A few prompts that tend to work well on this project specifically:

- "Set up a FastAPI service in `services/agent/` with endpoints `/chat`, `/plan/generate`, `/articulation/lookup`. Use Anthropic Python SDK. Mock the Postgres calls for now."
- "Write a Playwright scraper for ASSIST that takes a `from_ccc`, `to_school`, and `major`, and returns structured articulation rows. Cache results to a local JSON file during development."
- "Generate a Postgres migration for the schema in `docs/schema.md`."
- "Write Jest tests for the articulation rule engine in `packages/validator/`."

**Step 6 — Set up the working loop.** The pattern that saves the most time:

1. In Claude Desktop (Chat, not Code), discuss the next piece of work. Argue about the schema. Sketch the API. This is thinking mode.
2. When you know what you want built, switch to the Code tab (or terminal Claude Code) and paste a task-sized prompt. This is building mode.
3. Review the diff. Accept or reject. Claude Code keeps Git state clean, so rejection is cheap.
4. Run tests, run the app, iterate.
5. When you accumulate research files, scraped samples, or user-interview recordings, hand them to Cowork to organize.

**Step 7 — Keep an Anthropic API key for the app itself.** Separate from your Claude.ai subscription. Get it from console.anthropic.com. Put it in `.env.local` as `ANTHROPIC_API_KEY`. The app you're *building* calls the API directly; the Claude products (Desktop, Code, Cowork) are for *building it*, not for running it.

**Step 8 — Instrument from day one.** Set up Langfuse early, even if it feels premature. When your agent starts making weird decisions in week 6, you will want the traces.

### One honest caveat

These Claude products update frequently. The general shape above is stable, but specific menu items, extension names, and plan-gating may have shifted by the time you set this up. If something in this section doesn't match what you see in the app, the app is right and this document is stale. Check `support.claude.com` or the in-app Settings for the current state.
