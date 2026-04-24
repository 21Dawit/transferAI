# CCC Transfer Navigator

> **AI-powered transfer planning for California Community College students.**
> Not a counselor. Not a guarantee. A tool that helps you show up to your counselor appointment with a better plan.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Status: In Development](https://img.shields.io/badge/Status-In%20Development-yellow)]()

---

## Table of Contents

1. [What This Is](#what-this-is)
2. [What This Is Not](#what-this-is-not)
3. [Features](#features)
4. [Tech Stack](#tech-stack)
5. [Getting Started](#getting-started)
6. [Project Structure](#project-structure)
7. [PII Inventory](#pii-inventory)
8. [Disclaimers](#disclaimers)
9. [Data Sources](#data-sources)
10. [Contributing](#contributing)
11. [License](#license)

---

## What This Is

CCC Transfer Navigator is an LLM-powered transfer planning assistant for students at California Community Colleges who are planning to transfer to UC, CSU, or private universities.

It consolidates data from ASSIST, UC TAP, IGETC/CSU GE worksheets, and college catalogs into a single conversational interface. You tell it who you are, where you are, and where you want to go — it produces a personalized, term-by-term plan grounded in official articulation data, with a source citation on every recommendation.

**The core problem it solves:** students don't need another data source. They need a reasoning layer on top of the twelve they already have.

---

## What This Is Not

- ❌ **Not a licensed counselor.** Every plan this tool generates must be verified with a human counselor before you act on it.
- ❌ **Not an admissions predictor.** Competitiveness estimates shown are ranges based on published data, not promises.
- ❌ **Not a substitute for official sources.** ASSIST.org, your college catalog, and your counselor are authoritative. This tool is a preparation layer.
- ❌ **Not affiliated with the UC system, CSU system, ASSIST, or any California community college.**

---

## Features

**MVP (current scope)**

- Onboarding flow: CCC, completed courses, GPA, intended major, 1–3 target schools, transfer year
- ASSIST articulation lookup for your specific CCC → school → major combination
- Major preparation checklist auto-generated from ASSIST + catalog data
- IGETC completion checker
- Conversational AI counselor with retrieval-augmented responses
- Term-by-term transfer plan with citations on every course recommendation
- Transfer risk detector ("you're missing CHEM 1B and your target major requires it")

**Planned (post-MVP)**

- Multi-school comparison view
- CSU GE checker
- Course availability via CVC Exchange
- Student dashboard with saved plans and progress tracking
- Application deadline tracker
- Professor and workload insights (aggregated, with heavy disclaimers)

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14 (App Router), TypeScript, Tailwind CSS, shadcn/ui |
| Backend | Next.js route handlers + Python FastAPI (agent/RAG service) |
| Database | Postgres via Supabase, pgvector for embeddings |
| Auth | Supabase Auth (magic link) |
| LLM | Anthropic Claude (Sonnet for chat, Haiku for classification) |
| Scraping | Playwright (ASSIST), requests + BeautifulSoup (catalogs) |
| Observability | Langfuse for LLM traces, Sentry for app errors |
| Hosting | Vercel (frontend), Railway (FastAPI service) |

---

## Getting Started

### Prerequisites

- Node.js 18+
- Python 3.11+
- A Supabase account (free tier works)
- An Anthropic API key (console.anthropic.com)

### Installation

```bash
# Clone the repo
git clone https://github.com/your-username/transferAI.git
cd transferAI

# Install frontend dependencies
npm install

# Install Python dependencies (agent service)
cd services/agent
pip install -r requirements.txt
cd ../..

# Set up environment variables
cp .env.example .env.local
# Fill in NEXT_PUBLIC_SUPABASE_URL, NEXT_PUBLIC_SUPABASE_ANON_KEY, ANTHROPIC_API_KEY
```

### Running locally

```bash
# Start the Next.js app
npm run dev

# In a second terminal, start the FastAPI agent service
cd services/agent
uvicorn main:app --reload --port 8000
```

Visit `http://localhost:3000` to see the app.

### Environment variables

| Variable | Required | Description |
|---|---|---|
| `NEXT_PUBLIC_SUPABASE_URL` | ✅ | Your Supabase project URL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | ✅ | Supabase anon/public key |
| `SUPABASE_SERVICE_ROLE_KEY` | ✅ | Supabase service role key (server-side only, never expose to client) |
| `ANTHROPIC_API_KEY` | ✅ | Anthropic API key for Claude |
| `LANGFUSE_SECRET_KEY` | ⬜ | For LLM observability (optional in dev) |
| `LANGFUSE_PUBLIC_KEY` | ⬜ | For LLM observability (optional in dev) |

**Never commit `.env.local` to version control.** It is in `.gitignore` by default.

---

## Project Structure

```
transferAI/
├── app/                    # Next.js App Router pages
│   ├── (auth)/             # Login, signup flows
│   ├── dashboard/          # Main student dashboard
│   ├── chat/               # Chat + plan split view
│   ├── plan/               # Standalone plan editor
│   └── api/                # Route handlers
│       ├── chat/           # Streaming chat endpoint
│       ├── plan/           # Plan generation endpoint
│       └── articulation/   # Articulation lookup endpoint
├── components/             # Reusable UI components
├── lib/                    # Supabase client, utilities
├── services/
│   └── agent/              # Python FastAPI service (RAG + agent)
│       ├── tools/          # Claude tool definitions
│       ├── retrieval/      # SQL + pgvector retrieval logic
│       └── scrapers/       # ASSIST + catalog scrapers
├── docs/                   # Architecture notes, plan, schema
├── tests/                  # Eval harness + unit tests
└── scripts/                # DB migrations, seed data, ingestion jobs
```

---

## PII Inventory

This section documents every category of personal data the application stores, why it's stored, who can access it, how long it's retained, and how it can be deleted. This inventory is maintained as a first-class part of the codebase and updated any time the schema changes.

> **Philosophy:** We store the minimum data needed to generate a useful plan. We do not sell data, share it with third parties, or use it to train models. We treat this data as if FERPA applied, even though as a non-institutional tool it technically doesn't.

### Data categories

| Data | Table | Why stored | Who can access | Retention | Deletable? |
|---|---|---|---|---|---|
| Email address | `users` | Account identity, magic link auth | User only (RLS enforced) | Until account deleted | ✅ Yes |
| Completed courses (course codes + grades) | `completed_courses` | Core input for plan generation and articulation matching | User only (RLS enforced) | Until account deleted | ✅ Yes |
| GPA | `profiles` | Competitiveness context for plan recommendations | User only (RLS enforced) | Until account deleted | ✅ Yes |
| Target schools | `target_schools` | Determines which articulation agreements to load | User only (RLS enforced) | Until account deleted | ✅ Yes |
| Intended major | `profiles` | Determines major prep requirements | User only (RLS enforced) | Until account deleted | ✅ Yes |
| Unit load preference | `profiles` | Pacing the term-by-term plan | User only (RLS enforced) | Until account deleted | ✅ Yes |
| Work hours per week | `profiles` | Surfacing realistic load warnings | User only (RLS enforced) | Until account deleted | ✅ Yes |
| Transfer year | `profiles` | Timeline calculation | User only (RLS enforced) | Until account deleted | ✅ Yes |
| Saved plans | `plans`, `plan_terms`, `plan_courses` | Persistent plan state between sessions | User only (RLS enforced) | Until account deleted | ✅ Yes |
| Conversation history | `conversations`, `messages` | Continuity across sessions | User only (RLS enforced) | Until account deleted | ✅ Yes |
| LLM traces | Langfuse (external) | Debugging agent behavior | Developer only | 90 days | ⬜ Partial (via Langfuse) |
| Error logs | Sentry (external) | App error monitoring | Developer only | 30 days | ⬜ No (anonymized) |

### What we do NOT store

- Social Security numbers
- FAFSA or financial aid data
- Student ID numbers from any institution
- Unofficial or official transcripts (courses are manually entered by the user)
- Any data from browser cookies beyond session state
- IP addresses beyond what Supabase/Vercel log by default

### Row-level security

All user data tables enforce Postgres row-level security (RLS) via Supabase. A user can only read and write their own rows. The service role key (used only in server-side API routes) is never exposed to the client.

### Your right to delete your data

Users can permanently delete their account and all associated data from **Settings → Delete Account**. This triggers a cascade delete across all tables. There is no "soft delete" or recovery window — deletion is immediate and permanent. LLM traces in Langfuse are not covered by in-app deletion; contact the developer directly to request trace removal.

---

## Disclaimers

### Academic advice disclaimer

CCC Transfer Navigator is a **planning tool**, not a licensed academic counselor. All plans, articulation lookups, and requirement checks generated by this application are based on publicly available data that may be incomplete, outdated, or incorrectly parsed.

**You must verify every recommendation with a human counselor at your California Community College before making enrollment decisions.** Articulation agreements, major requirements, GPA thresholds, and application deadlines change. This tool cannot guarantee that its data reflects the most current version of any agreement or requirement.

Enrolling in a course based solely on this tool's recommendation, without counselor verification, is done at your own risk.

### Articulation data disclaimer

Articulation data is sourced from ASSIST.org and is cached locally. Cached data may be up to 90 days old. The "last updated" date is shown on every plan item. If a plan item shows stale data, treat that recommendation as unverified until you confirm it on ASSIST.org directly.

The tool will explicitly return "no articulation agreement found" when it cannot confirm an articulation, rather than guessing. If you see this, it means no confirmed agreement exists in the cache — it does not necessarily mean no articulation exists. Check ASSIST.org directly.

### Admissions disclaimer

Any competitiveness estimates, admit range references, or GPA comparisons shown in this application are informational only. They are based on published, historical, aggregate data from UC and CSU systems. They are not predictions of your individual admission outcome. Admission decisions are made by universities, not by this tool.

### No affiliation disclaimer

This project is not affiliated with, endorsed by, or in any way connected to the University of California system, the California State University system, ASSIST.org, the California Community Colleges Chancellor's Office, or any individual college or university.

### AI-generated content disclaimer

Responses from the AI counselor are generated by a large language model (Claude, by Anthropic). While the system is designed to ground responses in retrieved data and cite sources, LLMs can make mistakes. Treat AI-generated responses as a starting point for research, not as authoritative guidance.

---

## Data Sources

| Source | Use | Notes |
|---|---|---|
| [ASSIST.org](https://assist.org) | Articulation agreements | Scraped with Playwright; rate-limited, cached, attributed |
| UC TAP / UC Transfer Pathways | UC major prep requirements | Public pages, parsed per major |
| CSU major preparation pages | CSU major prep requirements | Per campus, per major |
| CCC course catalogs | Course descriptions, prereqs, units | Parsed yearly; stored with source URL |
| IGETC worksheets | GE requirement mapping | Parsed from official PDFs |
| CVC Exchange API | Online course availability | API (used in post-MVP) |

All scrapers identify their user agent, respect `robots.txt`, rate-limit aggressively, and cache results. Raw scraped content is stored with `source_url` and `last_fetched_at` on every row so every claim is traceable to its origin.

---

## Contributing

This is a solo portfolio project for now. If you're a CCC student who wants to give feedback, reach out — user research is the most valuable contribution at this stage.

If you open a PR, please:
- Update the PII inventory if you're changing the schema
- Add tests for any articulation logic (see `tests/`)
- Never commit API keys, `.env` files, or scraped data files

---

## License

MIT — see [LICENSE](LICENSE).

---

*Built by a CCC student, for CCC students.*
