import { NextRequest, NextResponse } from "next/server";

export function proxy(request: NextRequest) {
  void request;
  return NextResponse.next();
}

export const config = {
  matcher: ["/api/scrape/:path*"],
};
