import { NextRequest, NextResponse } from "next/server";

import {
  createScrapeOpsDisabledResponse,
  createScrapeOpsUnauthorizedResponse,
  isScrapeOpsConfigured,
  isScrapeOpsRequestAuthorized,
} from "@/lib/scrape-ops-auth";

function isApiPath(pathname: string): boolean {
  return pathname.startsWith("/api/");
}

export function proxy(request: NextRequest) {
  const apiRequest = isApiPath(request.nextUrl.pathname);

  if (!isScrapeOpsConfigured()) {
    return createScrapeOpsDisabledResponse({ isApi: apiRequest });
  }

  if (!isScrapeOpsRequestAuthorized(request.headers)) {
    return createScrapeOpsUnauthorizedResponse({ isApi: apiRequest });
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/scrape-log/:path*", "/api/scrape/:path*"],
};
