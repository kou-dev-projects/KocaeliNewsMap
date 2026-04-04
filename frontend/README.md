# PULSE Frontend

Next.js App Router frontend for the Kocaeli news map, operator-only scrape monitor, and PWA shell.

## Local Development

From `frontend/`:

```bash
npm install
npm run dev
```

The app runs on `http://localhost:3000`.

When Docker Compose is used, `http://localhost:3000` is now served by the edge
reverse proxy instead of the raw Next.js container.

## Required Environment

The frontend reads most configuration from the repo-root `.env`.

Important values:

- `NEXT_PUBLIC_API_URL`: browser-facing backend URL, usually `http://localhost:8000`
- `API_INTERNAL_URL`: server-side route handlers use this when proxying to the backend
- `SCRAPE_OPS_USERNAME`, `SCRAPE_OPS_PASSWORD`: browser Basic Auth for `/scrape-log` and frontend `/api/scrape/*`
- `SCRAPE_OPS_ALLOWED_CIDRS`: comma-separated CIDRs allowed through the edge proxy for `/scrape-log` and `/api/scrape/*`
- `FRONTEND_EDGE_PORT`: host port exposed by the edge proxy, usually `3000`
- `NEXT_PUBLIC_ENABLE_PWA_IN_DEV`: enables service worker registration during local development
- `NEXT_PUBLIC_ENABLE_PUSH_TEST`, `ENABLE_PUSH_TEST_ENDPOINT`, `PUSH_TEST_API_KEY`: local push QA controls
- `NEXT_PUBLIC_VAPID_PUBLIC_KEY`, `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`, `VAPID_SUBJECT`: web push setup

## Quality Checks

```bash
npm run lint
npm test
npm run build
```

PWA / UI smoke checks:

```bash
npm run qa:map:smoke
npm run qa:map:smoke:mock
npm run qa:pwa:offline
npm run qa:pwa:lighthouse
```

Generated QA artifacts such as `map-smoke-summary.json`, `map-smoke-failure.png`,
and Lighthouse reports are local-only outputs and are gitignored.

## Key Routes

- `/`: primary public news map
- `/scrape-log`: Basic-Auth-protected scrape operations monitor
- `/api/scrape/*`: server-side proxy routes to the backend scrape control plane
- `/api/push/*`: push subscription and test endpoints

## Notes

- The main app entry is `src/app/page.tsx`.
- Scrape bootstrap is no longer triggered automatically on page load.
- Public users never see scrape controls on `/`; operators use `/scrape-log` after browser authentication.
- Docker Compose adds a second gate in front of ops routes: the edge proxy only forwards `/scrape-log` and `/api/scrape/*` from IPs allowed by `SCRAPE_OPS_ALLOWED_CIDRS`.
- PWA bootstrap logic lives under `src/components/pwa/`.
- Map rendering uses MapLibre + DeckGL under `src/components/map/`.
