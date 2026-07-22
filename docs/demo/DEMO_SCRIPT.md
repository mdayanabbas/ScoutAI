# ScoutAI Demo Script

## Opening
ScoutAI is a job-search intelligence platform for finding and acting on early-stage startup opportunities.

## Problem
Startup job search is scattered. The best roles can appear on remote boards, Hacker News, YC company pages, Ashby boards, founder posts, or company career pages. Then there is the second half of the work: matching the role to your profile, checking remote eligibility, tailoring the resume, preparing outreach, following up, and tracking the pipeline.

## Solution
ScoutAI turns that into one workflow: discover, score, review, prepare, outreach, follow up, and track.

## Walkthrough
Start in the Command Center. This is the daily operating loop. It tells me what needs attention today: discovery, recommendations, resume tasks, cold DMs, follow-ups, applications, and watched companies.

Next, open Discovery Control Center. Daily Scout can run multiple sources, but the key is that it does not treat every source equally. ScoutAI shows source diagnostics, run history, source quality, warnings, and top recommendations. If a source is noisy, that is visible.

Now open the Review Queue. This is where recommendations become decisions. I can save a job, skip it, mark it as needing resume work, route it to cold outreach, or open the Action Center.

In the Action Center, ScoutAI helps turn a job into application material. It can generate an application packet, show resume gaps, suggest improvements, create a cold DM draft, and export a Markdown pack. Nothing is sent automatically; this is a review-gated workflow.

Then I move into Follow-ups and Pipeline. Follow-ups track manually sent outreach and reminders. Pipeline shows saved, interested, resume-needed, cold-DM-needed, applied, interviewing, rejected, and offer stages.

Finally, Analytics shows the funnel: jobs reviewed, saved, applied, interviewing, rejected, cold DMs drafted or sent, follow-ups due, source performance, weekly trends, bottlenecks, and next actions.

## Technical Depth
ScoutAI uses a FastAPI backend with PostgreSQL, source-specific discovery adapters, deterministic enrichment and matching, and source diagnostics. The frontend is a Next.js application with local-first workflow tracking for drafts, follow-ups, resume-fit cache, daily operating loop state, and export tools.

## Close
ScoutAI is not just a job board. It is an operating system for running a focused startup job search.
