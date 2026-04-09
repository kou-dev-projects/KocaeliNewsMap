import type { RawScrapeEvent } from "@/lib/scrape/types";

export type ScrapeBootstrapResponse =
  | {
      status: "already_initialized";
      reason: string;
    }
  | ScrapeQueuedResponse;

export type ScrapeQueuedResponse = {
  job_id: string;
  status: "pending" | "running";
  status_url: string;
  reason?: string;
  source?: string | null;
  trigger_type?: string | null;
  details?: {
    reset?: {
      deleted_counts: Record<string, number>;
      total_deleted: number;
    };
  };
};

export type ScrapeJobStatusResponse = {
  job_id: string;
  status: "pending" | "running" | "completed" | "failed" | "cancelled";
  source: string | null;
  trigger_type: string;
  created_at: number;
  attempt_count: number;
  started_at?: number;
  completed_at?: number;
  last_heartbeat_at?: number;
  cancel_requested?: boolean;
  cancel_requested_at?: number;
  result?: Record<string, unknown>;
  error?: string;
};

export type ScrapeResetResponse = {
  status: "completed";
  deleted_counts: Record<string, number>;
  total_deleted: number;
};

export type ScrapeStopResponse = {
  job_id: string;
  status: "pending" | "running" | "cancelled";
  status_url: string;
  source: string | null;
  trigger_type: string | null;
  cancel_requested: boolean;
  cancel_requested_at?: number;
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

const EMPTY_LATEST_SCRAPE_RUN: LatestScrapeRunResponse = {
  job_id: null,
  status: "idle",
  source: null,
  trigger_type: null,
  started_at: null,
  updated_at: null,
  event_count: 0,
  events: [],
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

export async function resetScrapeWorkspace(authorizationHeader?: string) {
  return postScrapeTrigger<ScrapeResetResponse>("/api/scrape/reset", {
    authorizationHeader,
  });
}

export async function stopScrape(
  options?: { authorizationHeader?: string; jobId?: string | null },
) {
  const path = options?.jobId
    ? `/api/scrape/stop?job_id=${encodeURIComponent(options.jobId)}`
    : "/api/scrape/stop";
  return postScrapeTrigger<ScrapeStopResponse>(path, {
    authorizationHeader: options?.authorizationHeader,
  });
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
  try {
    const response = await fetch("/api/scrape/latest", {
      method: "GET",
      cache: "no-store",
      headers: buildScrapeRequestHeaders(authorizationHeader),
    });

    if (!response.ok) {
      return EMPTY_LATEST_SCRAPE_RUN;
    }

    return (await response.json()) as LatestScrapeRunResponse;
  } catch {
    return EMPTY_LATEST_SCRAPE_RUN;
  }
}
