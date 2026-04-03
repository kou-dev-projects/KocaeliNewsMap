import { type NextRequest } from "next/server";

import {
  authorizeScrapeControlRequest,
  buildScrapeBackendUrl,
  createScrapeProxyHeaders,
} from "../_proxy";

export const dynamic = "force-dynamic";

export async function GET(request: NextRequest): Promise<Response> {
  const authError = authorizeScrapeControlRequest(request);
  if (authError) {
    return authError;
  }

  const jobId = request.nextUrl.searchParams.get("job_id")?.trim();

  if (!jobId) {
    return Response.json(
      { detail: "job_id is required." },
      { status: 400 },
    );
  }

  let upstream: Response;
  try {
    upstream = await fetch(
      buildScrapeBackendUrl(`/api/v1/scrape/jobs/${jobId}`),
      {
        method: "GET",
        headers: createScrapeProxyHeaders(),
        cache: "no-store",
      },
    );
  } catch {
    return Response.json(
      { detail: "Scrape job status is unavailable." },
      { status: 502 },
    );
  }

  const contentType = upstream.headers.get("content-type") ?? "";

  if (!contentType.includes("application/json")) {
    return Response.json(
      { detail: "Unexpected scrape job response." },
      { status: upstream.status || 502 },
    );
  }

  const payload = await upstream.json();
  return Response.json(payload, { status: upstream.status });
}
