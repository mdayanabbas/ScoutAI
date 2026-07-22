# Final QA Checklist

## Backend
- Health endpoint works.
- Migrations are current.
- Discovery run succeeds or returns partial with useful diagnostics.
- Job matches list works.
- Job decisions endpoints work.
- Company watchlist endpoints work.
- Active resume endpoint works.
- Application packet endpoint works.
- Resume improvement endpoint works.

## Frontend
- `/applications/command-center` loads.
- `/discovery/control-center` loads.
- Daily Scout run or payload preview works.
- Review Queue renders.
- Action Center opens.
- Application Pack exports Markdown.
- Cold DM Draft Builder works.
- `/applications/follow-ups` loads.
- `/jobs/pipeline` loads.
- `/companies/watchlist` loads.
- `/applications/analytics` loads.
- Resume page loads.
- Navigation active state is correct.
- No dead links in main navigation.
- Empty states explain what to do next.
- Partial API failures do not crash the page.

## Demo Recovery
- Existing recommendations are available if live discovery is weak.
- At least one job workspace can be opened.
- At least one application packet can be shown or generated.
- At least one follow-up can be shown.
- Analytics has non-empty funnel or outreach data.
