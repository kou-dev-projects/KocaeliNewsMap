import {
  authorizeScrapeControlRequest,
  buildScrapeBackendUrl,
  createScrapeProxyHeaders,
} from "../_proxy";

export const dynamic = "force-dynamic";

export async function GET(request: Request): Promise<Response> {
  const authError = authorizeScrapeControlRequest(request);
  if (authError) {
    return authError;
  }

  let upstream: Response;
  try {
    upstream = await fetch(buildScrapeBackendUrl("/api/v1/scrape/latest"), {
      method: "GET",
      headers: createScrapeProxyHeaders(),
      cache: "no-store",
    });
  } catch {
    return Response.json(
      { detail: "Latest scrape run is unavailable." },
      { status: 502 },
    );
  }

  const contentType = upstream.headers.get("content-type") ?? "";

  if (!contentType.includes("application/json")) {
    return Response.json(
      { detail: "Unexpected latest scrape response." },
      { status: upstream.status || 502 },
    );
  }

  const payload = await upstream.json();
  return Response.json(payload, { status: upstream.status });
}
