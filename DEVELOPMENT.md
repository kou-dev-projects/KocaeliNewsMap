# Development Modes

## Docker Local Database Mode

Use this mode when Atlas access is unstable or blocked by network policy.

### Environment

Set the active backend database target with:

```env
MONGO_URL=mongodb://localhost:27017
MONGO_DOCKER_URL=mongodb://mongodb:27017
MONGO_DB=kocaeli_news
```

Notes:
- `MONGO_URL` is the host-side value used when you run the backend outside Docker.
- `MONGO_DOCKER_URL` is injected into Docker services, so containers talk to the `mongodb` service instead of `localhost`.
- `MONGO_URI` may stay in `.env` as a backup/reference value, but it is not used by the current backend settings.
- `mongodb` is the Docker Compose service name, so it must be used instead of `localhost` when the backend runs inside Docker.

### Automatic Init

`docker-compose.yml` mounts:

```yaml
./mongo-init:/docker-entrypoint-initdb.d
```

This means:
- Mongo still applies `mongo-init/database.js` automatically on a fresh volume
- and the `mongo-migrate` service replays the same script against an existing volume before app services start

### Start Services

For the refactored backend flow, the useful local stack is:

```powershell
docker compose up -d mongodb redis mongo-migrate backend worker scheduler
```

Notes:
- `backend` serves the API.
- `worker` consumes queued scrape jobs.
- `scheduler` submits scheduled crawl jobs.
- Frontend is optional for backend-only work.
- `backend`, `worker`, and `scheduler` now share a single Docker image tag instead of
  generating three separate backend-sized images.
- Optional heavyweight dependency groups are off by default. If you explicitly need
  ML providers or legacy integrations inside Docker, set these before rebuilding:

```env
DOCKER_INSTALL_ML=true
DOCKER_INSTALL_DEV_TOOLS=true
DOCKER_INSTALL_OPTIONAL_INTEGRATIONS=true
```

### Dependency Profiles

The backend requirements are split by intent:

- `backend/requirements.txt`: lean runtime dependencies
- `backend/requirements-dev.txt`: runtime + optional ML + dev/test + legacy integrations

This keeps local Docker images small by default while preserving a full install path
for explicit development or experimentation.

### Verify Local Mongo Mode

After startup:

```powershell
docker exec -it kocaeli-news_map_backend printenv MONGO_URL
```

Expected output:

```text
mongodb://mongodb:27017
```

Then verify the API:

- `http://localhost:8000/livez`
- `http://localhost:8000/readyz`

Expected:
- `/livez` should return `{"status": "ok"}`
- `/readyz` should report both Mongo and Redis as available

Current note:
- The app currently exposes `http://localhost:8000/docs` and the news API routes, not
  dedicated `/livez` or `/readyz` endpoints.
- For a real runtime check, prefer:
  - `http://localhost:8000/docs`
  - `http://localhost:8000/api/v1/news/stats`

### Frontend QA

Frontend smoke checks now default to the live local backend instead of fixture mocks:

```powershell
cd frontend
npm run qa:map:smoke
npm run qa:pwa:offline
```

The Playwright smoke server starts on `http://127.0.0.1:3101` by default, so backend
`CORS_ORIGINS` should include `http://127.0.0.1:3101` for live QA.

If you need the old deterministic fixture harness for UI-only debugging, use:

```powershell
npm run qa:map:smoke:mock
```

## Manual Fallback

If the Mongo volume already exists, the Mongo entrypoint init script will not rerun automatically.

### Option 1: Recreate local Mongo volume

```powershell
docker compose down
docker volume ls
docker volume rm kocaelinewsmap_mongo_data
docker compose up -d mongodb redis mongo-migrate backend worker scheduler
```

Note:
- confirm the actual volume name with `docker volume ls` before deleting

### Option 2: Reapply schema without dropping the volume

```powershell
docker compose up -d --force-recreate mongo-migrate
```

This is useful when:
- the schema changes
- you do not want to destroy the local volume

## Atlas Mode

To switch back to Atlas:

```env
MONGO_URL=mongodb+srv://...
MONGO_DB=kocaeli_news
```

Then restart the containers that use the backend settings:

```powershell
docker compose up -d --build backend worker scheduler
```
