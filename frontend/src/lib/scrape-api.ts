import type { RawScrapeEvent } from "@/lib/scrape/types";

export type ScrapeBootstrapResponse =
  | {
      status: "already_initialized";
      reason: string;
    }
  | ScrapeQueuedResponse;

export type ScrapeQueuedResponse = {
  job_id: string;
  status: "pending";
  status_url: string;
  details?: {
    reset?: {
      deleted_counts: Record<string, number>;
      total_deleted: number;
    };
  };
};

export type ScrapeJobStatusResponse = {
  job_id: string;
  status: "pending" | "running" | "completed" | "failed";
  source: string | null;
  trigger_type: string;
  created_at: number;
  attempt_count: number;
  started_at?: number;
  completed_at?: number;
  last_heartbeat_at?: number;
  result?: Record<string, unknown>;
  error?: string;
};

export type LatestScrapeRunResponse = {
  job_id: string | null;
  status: "idle" | "pending" | "running" | "completed" | "failed" | string;
  source: string | null;
  trigger_type: string | null;
  started_at: number | null;
  updated_at: number | null;
  event_count: number;
  events: RawScrapeEvent[];
};

async function readErrorDetail(response: Response, fallback: string) {
  try {
    const payload = (await response.json()) as { detail?: string };
    return payload.detail || fallback;
  } catch {
    return fallback;
  }
}

function buildScrapeRequestHeaders(authorizationHeader?: string) {
  const headers = new Headers();
  if (authorizationHeader) {
    headers.set("Authorization", authorizationHeader);
  }
  return headers;
}

type ScrapeRequestOptions = {
  authorizationHeader?: string;
  reset?: boolean;
};

async function postScrapeTrigger<T>(
  path: string,
  options?: ScrapeRequestOptions,
): Promise<T> {
  const response = await fetch(path, {
    method: "POST",
    cache: "no-store",
    headers: buildScrapeRequestHeaders(options?.authorizationHeader),
  });

  if (!response.ok) {
    throw new Error(
      await readErrorDetail(response, `Scrape request failed with status ${response.status}`),
    );
  }

  return (await response.json()) as T;
}

export async function bootstrapScrape(options?: ScrapeRequestOptions) {
  return postScrapeTrigger<ScrapeBootstrapResponse>(
    options?.reset ? `/api/scrape/bootstrap?reset=true` : "/api/scrape/bootstrap",
    options,
  );
}

export async function refreshScrape(options?: ScrapeRequestOptions) {
  return postScrapeTrigger<ScrapeQueuedResponse>(
    options?.reset ? `/api/scrape/refresh?reset=true` : "/api/scrape/refresh",
    options,
  );
}

export async function fetchScrapeJobStatus(
  jobId: string,
  authorizationHeader?: string,
) {
  const response = await fetch(
    `/api/scrape/job-status?job_id=${encodeURIComponent(jobId)}`,
    {
      method: "GET",
      cache: "no-store",
      headers: buildScrapeRequestHeaders(authorizationHeader),
    },
  );

  if (!response.ok) {
    throw new Error(
      await readErrorDetail(response, `Scrape status request failed with status ${response.status}`),
    );
  }

  return (await response.json()) as ScrapeJobStatusResponse;
}

export async function fetchLatestScrapeRun(authorizationHeader?: string) {
  const response = await fetch("/api/scrape/latest", {
    method: "GET",
    cache: "no-store",
    headers: buildScrapeRequestHeaders(authorizationHeader),
  });

  if (!response.ok) {
    throw new Error(
      await readErrorDetail(
        response,
        `Latest scrape request failed with status ${response.status}`,
      ),
    );
  }

  return (await response.json()) as LatestScrapeRunResponse;
}
