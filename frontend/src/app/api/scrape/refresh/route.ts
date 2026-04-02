import { buildScrapeBackendUrl, createScrapeProxyHeaders } from "../_proxy";

export const dynamic = "force-dynamic";

export async function POST(): Promise<Response> {
  let upstream: Response;

  try {
    upstream = await fetch(buildScrapeBackendUrl("/api/v1/scrape/refresh"), {
      method: "POST",
      headers: createScrapeProxyHeaders(),
      cache: "no-store",
    });
  } catch {
    return Response.json(
      { detail: "Refresh scrape is unavailable." },
      { status: 502 },
    );
  }

  const contentType = upstream.headers.get("content-type") ?? "";

  if (!contentType.includes("application/json")) {
    return Response.json(
      { detail: "Unexpected refresh scrape response." },
      { status: upstream.status || 502 },
    );
  }

  const payload = await upstream.json();
  return Response.json(payload, { status: upstream.status });
}
