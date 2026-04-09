import {
  authorizeScrapeControlRequest,
  buildScrapeBackendUrl,
  createScrapeProxyHeaders,
} from "../_proxy";

export const dynamic = "force-dynamic";

const EMPTY_LATEST_RUN = {
  job_id: null,
  status: "idle",
  source: null,
  trigger_type: null,
  started_at: null,
  updated_at: null,
  event_count: 0,
  events: [],
};

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
    return Response.json(EMPTY_LATEST_RUN, { status: 200 });
  }

  const contentType = upstream.headers.get("content-type") ?? "";

  if (!contentType.includes("application/json")) {
    return Response.json(EMPTY_LATEST_RUN, { status: 200 });
  }

  const payload = await upstream.json();
  if (!upstream.ok) {
    return Response.json(EMPTY_LATEST_RUN, { status: 200 });
  }

  return Response.json(payload, { status: 200 });
}
