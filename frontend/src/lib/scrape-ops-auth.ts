const SCRAPE_OPS_REALM = "PULSE Scrape Ops";

function normalize(value: string | undefined): string {
  return (value || "").trim();
}

function secureCompare(left: string, right: string): boolean {
  if (left.length !== right.length) {
    return false;
  }

  let mismatch = 0;
  for (let index = 0; index < left.length; index += 1) {
    mismatch |= left.charCodeAt(index) ^ right.charCodeAt(index);
  }

  return mismatch === 0;
}

function decodeBasicAuthHeader(value: string | null): {
  username: string;
  password: string;
} | null {
  if (!value || !value.startsWith("Basic ")) {
    return null;
  }

  try {
    const encoded = value.slice("Basic ".length).trim();
    const decoded = atob(encoded);
    const separatorIndex = decoded.indexOf(":");
    if (separatorIndex < 0) {
      return null;
    }

    return {
      username: decoded.slice(0, separatorIndex),
      password: decoded.slice(separatorIndex + 1),
    };
  } catch {
    return null;
  }
}

export function isScrapeOpsConfigured(): boolean {
  return Boolean(
    normalize(process.env.SCRAPE_OPS_USERNAME) &&
      normalize(process.env.SCRAPE_OPS_PASSWORD),
  );
}

export function isScrapeOpsRequestAuthorized(headers: Headers): boolean {
  const expectedUsername = normalize(process.env.SCRAPE_OPS_USERNAME);
  const expectedPassword = normalize(process.env.SCRAPE_OPS_PASSWORD);
  if (!expectedUsername || !expectedPassword) {
    return false;
  }

  const credentials = decodeBasicAuthHeader(headers.get("authorization"));
  if (!credentials) {
    return false;
  }

  return (
    secureCompare(credentials.username, expectedUsername) &&
    secureCompare(credentials.password, expectedPassword)
  );
}

export function createScrapeOpsDisabledResponse(options: {
  isApi: boolean;
}): Response {
  const { isApi } = options;
  const headers = {
    "Cache-Control": "no-store",
  };
  if (isApi) {
    return Response.json(
      { detail: "Scrape operations are disabled." },
      { status: 404, headers },
    );
  }

  return new Response("Not Found", { status: 404, headers });
}

export function createScrapeOpsUnauthorizedResponse(options: {
  isApi: boolean;
}): Response {
  const { isApi } = options;
  const headers = {
    "WWW-Authenticate": `Basic realm="${SCRAPE_OPS_REALM}"`,
    "Cache-Control": "no-store",
  };

  if (isApi) {
    return Response.json(
      { detail: "Scrape operations require authentication." },
      { status: 401, headers },
    );
  }

  return new Response("Authentication required", {
    status: 401,
    headers,
  });
}

export function authorizeScrapeOpsRequest(
  request: Request,
  options: {
    isApi: boolean;
  },
): Response | null {
  const { isApi } = options;
  if (!isScrapeOpsConfigured()) {
    return createScrapeOpsDisabledResponse({ isApi });
  }

  if (!isScrapeOpsRequestAuthorized(request.headers)) {
    return createScrapeOpsUnauthorizedResponse({ isApi });
  }

  return null;
}
