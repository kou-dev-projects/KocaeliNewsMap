# Development Modes

## Docker Local Database Mode

Use this mode when Atlas access is unstable or blocked by network policy.

### Environment

Set the active backend database target with:

```env
MONGO_URL=mongodb://mongodb:27017
MONGO_DB=kocaeli_news
```

Notes:
- `MONGO_URL` is the active variable used by the backend.
- `MONGO_URI` may stay in `.env` as a backup/reference value, but it is not used by the current backend settings.
- `mongodb` is the Docker Compose service name, so it must be used instead of `localhost` when the backend runs inside Docker.

### Automatic Init

`docker-compose.yml` mounts:

```yaml
./mongo-init:/docker-entrypoint-initdb.d
```

This means:
- `mongo-init/database.js` is applied automatically
- but only when the Mongo data volume is initialized from scratch

### Start Services

For the refactored backend flow, the useful local stack is:

```powershell
docker compose up -d mongodb redis backend worker scheduler
```

Notes:
- `backend` serves the API.
- `worker` consumes queued scrape jobs.
- `scheduler` submits scheduled crawl jobs.
- Frontend is optional for backend-only work.

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

## Manual Fallback

If the Mongo volume already exists, the init script will not rerun automatically.

### Option 1: Recreate local Mongo volume

```powershell
docker compose down
docker volume ls
docker volume rm kocaelinewsmap_mongo_data
docker compose up -d mongodb redis backend worker scheduler
```

Note:
- confirm the actual volume name with `docker volume ls` before deleting

### Option 2: Reapply schema manually

```powershell
docker exec -it kocaeli-news_map_mongodb mongosh
```

Inside `mongosh`:

```javascript
load("/docker-entrypoint-initdb.d/database.js")
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
