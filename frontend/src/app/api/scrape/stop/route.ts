import { type NextRequest } from "next/server";

import {
  authorizeScrapeControlRequest,
  buildScrapeBackendUrl,
  createScrapeProxyHeaders,
} from "../_proxy";

export const dynamic = "force-dynamic";

export async function POST(request: NextRequest): Promise<Response> {
  const authError = authorizeScrapeControlRequest(request);
  if (authError) {
    return authError;
  }

  const upstreamUrl = buildScrapeBackendUrl("/api/v1/scrape/stop");
  const jobId = request.nextUrl.searchParams.get("job_id")?.trim();
  if (jobId) {
    upstreamUrl.searchParams.set("job_id", jobId);
  }

  let upstream: Response;
  try {
    upstream = await fetch(upstreamUrl, {
      method: "POST",
      headers: createScrapeProxyHeaders(),
      cache: "no-store",
    });
  } catch {
    return Response.json(
      { detail: "Scrape stop request is unavailable." },
      { status: 502 },
    );
  }

  const contentType = upstream.headers.get("content-type") ?? "";
  if (!contentType.includes("application/json")) {
    return Response.json(
      { detail: "Unexpected stop response." },
      { status: upstream.status || 502 },
    );
  }

  const payload = await upstream.json();
  return Response.json(payload, { status: upstream.status });
}
