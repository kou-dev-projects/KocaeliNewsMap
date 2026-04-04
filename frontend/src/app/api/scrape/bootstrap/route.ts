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

  let upstream: Response;

  try {
    upstream = await fetch(buildScrapeBackendUrl("/api/v1/scrape/bootstrap"), {
      method: "POST",
      headers: createScrapeProxyHeaders(),
      cache: "no-store",
    });
  } catch {
    return Response.json(
      { detail: "Bootstrap scrape is unavailable." },
      { status: 502 },
    );
  }

  const contentType = upstream.headers.get("content-type") ?? "";

  if (!contentType.includes("application/json")) {
    return Response.json(
      { detail: "Unexpected bootstrap scrape response." },
      { status: upstream.status || 502 },
    );
  }

  const payload = await upstream.json();
  return Response.json(payload, { status: upstream.status });
}
