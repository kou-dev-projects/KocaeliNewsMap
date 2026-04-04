import { authorizeScrapeOpsRequest } from "@/lib/scrape-ops-auth";

const BACKEND_BASE_URL =
  process.env.API_INTERNAL_URL ??
  process.env.NEXT_PUBLIC_API_URL ??
  "http://localhost:8000";

function getScrapeApiKey() {
  return (
    process.env.SCRAPE_EVENTS_API_KEY ||
    process.env.SCRAPE_TRIGGER_API_KEY ||
    ""
  ).trim();
}

export function buildScrapeBackendUrl(pathname: string) {
  return new URL(pathname, BACKEND_BASE_URL);
}

export function createScrapeProxyHeaders() {
  const headers = new Headers();
  const apiKey = getScrapeApiKey();

  if (apiKey) {
    headers.set("X-API-Key", apiKey);
  }

  return headers;
}

export function authorizeScrapeControlRequest(request: Request) {
  return authorizeScrapeOpsRequest(request, { isApi: true });
}
