# ScoutAI Demo Guide

## One-liner
ScoutAI is a job-search intelligence workspace for discovering, ranking, preparing, and tracking early-stage startup opportunities.

## Problem
Startup job search is scattered across remote boards, Hacker News posts, YC companies, company job boards, resumes, cold outreach, follow-ups, and spreadsheets. The hard part is not only finding jobs; it is turning noisy signals into a focused daily operating loop.

## Target User
ScoutAI is built for a technical candidate looking for remote-friendly startup roles, especially AI, ML, software engineering, and founder-adjacent roles.

## Core Workflow
1. Discover jobs from remote/startup sources.
2. Enrich companies and job details.
3. Score jobs against a user profile.
4. Review recommendations.
5. Rank jobs with the active resume.
6. Generate application materials.
7. Draft cold outreach.
8. Track follow-ups, pipeline status, watched companies, and analytics.

## Demo Route Order
1. `/applications/command-center`
2. `/discovery/control-center`
3. Run Daily Scout or use a saved preset.
4. Daily Scout Review Queue.
5. Application Action Center.
6. Resume Fit / Rank with Resume.
7. Export Application Pack.
8. Cold DM Draft Builder.
9. `/applications/follow-ups`
10. `/jobs/pipeline`
11. `/companies/watchlist`
12. `/applications/analytics`

## What To Click And Say
### 1. Command Center
Click: Open `/applications/command-center`.

Say: "This is the daily operating loop. ScoutAI tells me what to do next: run discovery, review jobs, tailor resumes, draft outreach, update the pipeline, and follow up."

Expected result: Summary cards, Daily Operating Loop, Demo Readiness, Demo Shortcuts, and priority tasks are visible.

### 2. Discovery Control Center
Click: Discovery Control, then Run Daily Scout or a preset.

Say: "Daily Scout runs multiple sources and keeps source diagnostics visible, so noisy feeds do not silently pollute the workflow."

Expected result: Source results, run history, source quality guidance, and top recommendations.

### 3. Review Queue
Click: Review Queue after the run.

Say: "The review queue is the triage step. Jobs can be saved, skipped, routed to resume work, or routed to cold outreach."

Expected result: Job cards with scores, match tiers, eligibility, and actions.

### 4. Resume Ranking
Click: Rank with Resume.

Say: "The generic match score is useful, but the resume-aware ranking helps decide what is worth applying to first."

Expected result: Resume fit section with strengths, gaps, action recommendation, and fit tier.

### 5. Application Action Center
Click: Open Action Center on a job.

Say: "This is where a recommendation becomes application material: packet, resume suggestions, prep notes, export pack, and cold DM draft."

Expected result: Application Packet, Resume Improvement, Cold DM, and export tools are available.

### 6. Export Application Pack
Click: Copy or Download Markdown.

Say: "The pack is intentionally portable. I can move it into my notes, a GitHub issue, or a manual application workflow."

Expected result: Markdown export succeeds without submitting anything automatically.

### 7. Follow-ups, Pipeline, Watchlist, Analytics
Click: Follow-ups, Pipeline, Watchlist, Analytics.

Say: "ScoutAI closes the loop: it tracks outreach, application status, companies I care about, and conversion analytics."

Expected result: Each page has clear state, actions, and cross-links.

## Fallbacks For Weak Live Results
- If live discovery is slow: show source diagnostics and run history, then use existing recommendations.
- If Hacker News is noisy: explain that HN is intentionally conservative and often requires enrichment/manual judgment.
- If no top recommendations return: open Recommended Jobs or Pipeline to show previously scored jobs.
- If no active resume exists: show the Resume page and explain generic ranking still works.
- If an external API fails: show partial-data warnings and Source Quality Advisor.
