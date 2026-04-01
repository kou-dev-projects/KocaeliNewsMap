import { NextRequest } from "next/server";

export const dynamic = "force-dynamic";

function buildBackendUrl(request: NextRequest): URL {
  const backendBaseUrl =
    process.env.API_INTERNAL_URL ??
    process.env.NEXT_PUBLIC_API_URL ??
    "http://localhost:8000";
  const backendUrl = new URL("/api/v1/scrape/events", backendBaseUrl);

  const jobId = request.nextUrl.searchParams.get("job_id");
  if (jobId) {
    backendUrl.searchParams.set("job_id", jobId);
  }

  return backendUrl;
}

export async function GET(request: NextRequest): Promise<Response> {
  const backendUrl = buildBackendUrl(request);
  const headers = new Headers({
    Accept: "text/event-stream",
    "Cache-Control": "no-cache",
  });

  const lastEventId = request.headers.get("last-event-id");
  if (lastEventId) {
    headers.set("Last-Event-ID", lastEventId);
  }

  const apiKey =
    process.env.SCRAPE_EVENTS_API_KEY ?? process.env.SCRAPE_TRIGGER_API_KEY;
  if (apiKey) {
    headers.set("X-API-Key", apiKey);
  }

  let upstream: Response;
  try {
    upstream = await fetch(backendUrl, {
      method: "GET",
      headers,
      cache: "no-store",
      signal: request.signal,
    });
  } catch {
    return Response.json(
      {
        detail: "Scrape event stream is unavailable.",
        status: 502,
      },
      { status: 502 },
    );
  }

  if (!upstream.ok || !upstream.body) {
    const detail =
      upstream.status === 401
        ? "Scrape event stream is not authorized."
        : "Scrape event stream is unavailable.";

    return Response.json(
      {
        detail,
        status: upstream.status,
      },
      { status: upstream.status || 502 },
    );
  }

  return new Response(upstream.body, {
    status: upstream.status,
    headers: {
      "Content-Type": "text/event-stream; charset=utf-8",
      "Cache-Control": "no-cache, no-store, must-revalidate",
      Connection: "keep-alive",
      "X-Accel-Buffering": "no",
    },
  });
}
