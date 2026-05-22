const BACKEND_BASE_URL =
  process.env.API_INTERNAL_URL ??
  process.env.NEXT_PUBLIC_API_URL ??
  "http://localhost:8000";

export function buildScrapeBackendUrl(pathname: string) {
  return new URL(pathname, BACKEND_BASE_URL);
}

export function createScrapeProxyHeaders() {
  return new Headers();
}

export function authorizeScrapeControlRequest(request: Request) {
  void request;
  return null;
}
