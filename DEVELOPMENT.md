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
DOCKER_INSTALL_PLAYWRIGHT_BROWSER=false
```

### Dependency Profiles

The backend requirements are split by intent:

- `backend/requirements.txt`: lean runtime dependencies
- `backend/requirements-dev.txt`: runtime + local test/lint tooling
- `backend/requirements-full.txt`: runtime + optional ML + dev/test + legacy integrations
- `backend/requirements/optional-ml.txt`: heavyweight local inference providers, install only when needed
- `backend/requirements/optional-integrations.txt`: experimental / legacy integrations, not part of the default dev path

This keeps local Docker images and default virtualenvs smaller by default while preserving
an explicit full install path for experimentation.

Docker image caching notes:

- `backend/requirements/torch-cpu.txt` pins the heavyweight Torch wheel separately from the rest of the ML stack.
- The backend Dockerfile installs runtime, Torch, optional ML, dev tools, and legacy integrations in separate cached layers.
- `playwright install` now runs before `app/` is copied into the runtime stage, so ordinary backend code changes no longer force Chromium to download again.
- These cache mounts require Docker BuildKit, which is enabled by default in modern Docker Desktop builds.

### Versioned ML Base Image

The dedicated `ml` service now builds from a separate prebuilt ML base image instead of
resolving Torch on every everyday Compose build.

Default tag:

```env
ML_BASE_IMAGE=kocaelinewsmap-ml-base:py313-torch210-cpu-v3
```

Build or refresh the heavy ML base image only when one of these changes:

- `backend/requirements/torch-cpu.txt`
- `backend/requirements/optional-ml.txt`
- the Python base image in `backend/Dockerfile.ml-base`

Build it with:

```powershell
./backend/scripts/build_ml_base.ps1
```

Then rebuild or start the ML service normally:

```powershell
docker compose build ml
docker compose up -d ml backend worker scheduler
```

When you intentionally change heavyweight ML dependencies, bump `ML_BASE_IMAGE` to a new
tag before rebuilding so old local images stay reusable and explicit.

Default local flow keeps model preload out of the image build. Build the dependency base first:

```powershell
powershell -ExecutionPolicy Bypass -File .\backend\scripts\build_ml_base.ps1
```

Then warm real models into the persistent `ml_hf_cache` volume only when you need them:

```powershell
powershell -ExecutionPolicy Bypass -File .\backend\scripts\warm_ml_models.ps1
```

### Scrape Control Plane

The scrape control plane is now closed by default:

- Backend `/api/v1/scrape/*` routes are open in local development; trigger endpoints still keep rate limiting.
- Frontend `/api/scrape/*` proxy routes and `/scrape-log` no longer require server-side Basic Auth.
- Docker Compose still places an `edge` Nginx reverse proxy in front of the frontend on `FRONTEND_EDGE_PORT`, but scrape routes are no longer gated by a CIDR allowlist there.
- The public home page now embeds scrape controls directly, and `/scrape-log` remains available as a dedicated monitoring view.

### Dedicated ML Service

ML-heavy inference now belongs in a separate container:

```powershell
docker compose up -d ml backend worker scheduler
```

Notes:
- `ml` is built from the backend codebase with `INSTALL_ML=true`.
- `backend`, `worker`, and `scheduler` stay on the lean backend image.
- Inside Docker Compose, backend processes talk to `http://ml:8010`.
- This keeps `torch`, transformers, and embedding model dependencies out of the
  main API image by default.

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
