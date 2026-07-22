# Demo Data Guide

Use the app whenever possible so the demo reflects the real workflow.

## Create Demo Data Through The UI
1. Open `/discovery/control-center`.
2. Run a reliable remote-focused source selection, such as Himalayas, Remotive, and We Work Remotely.
3. Run Hacker News Startup Signals only if you want to show noisy startup-source diagnostics.
4. Open the Review Queue.
5. Save 2-3 jobs.
6. Mark one job as Needs Resume.
7. Mark one job as Needs Cold DM.
8. Watch one company from a job card or workspace.
9. Upload and activate a resume from `/profile/resume`.
10. Open a job workspace or Action Center.
11. Generate one Application Packet.
12. Generate one Cold DM draft.
13. Copy or save the draft.
14. Track one follow-up in `/applications/follow-ups`.
15. Move one job to Applied in `/jobs/pipeline`.
16. Move one job to Interviewing.
17. Open `/applications/analytics` and confirm metrics are non-empty.

## Existing Backend-backed Curl Examples
Use only endpoints that exist in the app.

```bash
curl http://127.0.0.1:8000/api/v1/health
```

```bash
curl "http://127.0.0.1:8000/api/v1/job-matches?order_by=recommended&limit=10"
```

```bash
curl "http://127.0.0.1:8000/api/v1/job-decisions?limit=20&include_archived=true"
```

```bash
curl "http://127.0.0.1:8000/api/v1/discovery/runs?limit=10"
```

```bash
curl "http://127.0.0.1:8000/api/v1/company-watchlist?limit=20"
```

Avoid creating demo data with curl unless you have checked the current API payload shape in the app.
