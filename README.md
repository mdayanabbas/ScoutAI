# ScoutAI

ScoutAI is a job-search intelligence workspace for discovering, ranking, preparing, and tracking early-stage startup opportunities.

## Problem
Startup job search is fragmented across job boards, Hacker News, YC company pages, Ashby boards, company career pages, resumes, cold DMs, follow-ups, and spreadsheets. ScoutAI brings those steps into one focused workflow.

## Core Features
- Daily Scout discovery across remote and startup sources.
- Source diagnostics and source quality guidance.
- Company and job enrichment.
- Deterministic job matching for role, seniority, experience, remote eligibility, and actionability.
- Daily Scout Review Queue.
- Resume-aware ranking.
- Application Action Center.
- Application Packet Markdown export.
- Cold DM Draft Builder.
- Follow-up Tracker.
- Application Pipeline.
- Company Watchlist.
- Job Search Analytics.

## Architecture
- Frontend: Next.js and React Query in `frontend/`.
- Backend: FastAPI in `backend/app/`.
- Database: PostgreSQL with Alembic migrations.
- Workflow storage: selected UI helpers use localStorage for drafts, follow-ups, resume-fit cache, and daily loop state.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full data flow.

## Tech Stack
- Python, FastAPI, SQLAlchemy, Alembic, PostgreSQL
- TypeScript, Next.js, React, React Query, Tailwind CSS
- Source adapters for Himalayas, We Work Remotely, Remotive, Hacker News, Y Combinator, Ashby, and first-party job pages

## Local Setup
1. Create and activate a Python environment.
2. Install backend dependencies from the backend project configuration.
3. Install frontend dependencies:

```bash
cd frontend
npm install
```

4. Copy environment examples and fill local values:

```bash
cp .env.example .env
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

5. Start PostgreSQL, then apply migrations:

```bash
cd backend
alembic upgrade head
```

## Running Locally
Backend:

```bash
cd backend
uvicorn app.main:app --reload
```

Frontend:

```bash
cd frontend
npm run dev
```

Open the frontend URL printed by Next.js, usually `http://localhost:3000` or `http://localhost:3001`.

## Demo Flow
Recommended route order:

1. `/applications/command-center`
2. `/discovery/control-center`
3. Daily Scout Review Queue
4. Application Action Center
5. Resume Fit / Rank with Resume
6. Export Application Pack
7. Cold DM Draft Builder
8. `/applications/follow-ups`
9. `/jobs/pipeline`
10. `/companies/watchlist`
11. `/applications/analytics`

See:
- [docs/demo/SCOUTAI_DEMO_GUIDE.md](docs/demo/SCOUTAI_DEMO_GUIDE.md)
- [docs/demo/DEMO_SCRIPT.md](docs/demo/DEMO_SCRIPT.md)
- [docs/demo/DEMO_CHECKLIST.md](docs/demo/DEMO_CHECKLIST.md)
- [docs/demo/FINAL_QA_CHECKLIST.md](docs/demo/FINAL_QA_CHECKLIST.md)

## Screenshots
Screenshots are not committed yet. Suggested captures:
- Command Center
- Discovery Control Center
- Review Queue
- Action Center
- Pipeline
- Analytics

## Tests
Backend tests are run from `backend/`:

```bash
python -m pytest
```

Frontend currently uses TypeScript checking:

```bash
cd frontend
npm.cmd exec tsc -- --noEmit
```

## Limitations
ScoutAI does not automatically apply to jobs, send emails, send DMs, scrape private platforms, or integrate with LinkedIn/X. Some workflow state is localStorage-only. External sources may be noisy or unavailable.

See [docs/LIMITATIONS.md](docs/LIMITATIONS.md).

## Roadmap
Near-term roadmap includes backend persistence for follow-ups/drafts, auth/user profiles, richer source analytics, better resume parsing, and saved search profiles.

See [docs/ROADMAP.md](docs/ROADMAP.md).
