# Demo Commands

## Start Backend
```bash
cd backend
uvicorn app.main:app --reload
```

## Start Frontend
```bash
cd frontend
npm run dev
```

## Apply Migrations
```bash
cd backend
alembic upgrade head
```

## Check Health
```bash
curl http://127.0.0.1:8000/api/v1/health
```

## Fetch Top Matches
```bash
curl "http://127.0.0.1:8000/api/v1/job-matches?order_by=recommended&limit=10"
```

## Fetch Discovery Runs
```bash
curl "http://127.0.0.1:8000/api/v1/discovery/runs?limit=10"
```

## Run Focused Backend Tests
```bash
cd backend
python -m pytest tests/test_remote_job_discovery_orchestrator_service.py tests/test_job_matching_service.py -v
```

## Run Frontend Type Check
```bash
cd frontend
npm.cmd exec tsc -- --noEmit
```

## Open psql
```bash
psql "postgresql://scoutai:scoutai@localhost:5433/scoutai"
```
