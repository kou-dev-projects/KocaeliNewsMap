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

async function readErrorDetail(response: Response, fallback: string) {
  try {
    const payload = (await response.json()) as { detail?: string };
    return payload.detail || fallback;
  } catch {
    return fallback;
  }
}

async function postScrapeTrigger<T>(path: string): Promise<T> {
  const response = await fetch(path, {
    method: "POST",
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(
      await readErrorDetail(response, `Scrape request failed with status ${response.status}`),
    );
  }

  return (await response.json()) as T;
}

export async function bootstrapScrape() {
  return postScrapeTrigger<ScrapeBootstrapResponse>("/api/scrape/bootstrap");
}

export async function refreshScrape() {
  return postScrapeTrigger<ScrapeQueuedResponse>("/api/scrape/refresh");
}

export async function fetchScrapeJobStatus(jobId: string) {
  const response = await fetch(
    `/api/scrape/job-status?job_id=${encodeURIComponent(jobId)}`,
    {
      method: "GET",
      cache: "no-store",
    },
  );

  if (!response.ok) {
    throw new Error(
      await readErrorDetail(response, `Scrape status request failed with status ${response.status}`),
    );
  }

  return (await response.json()) as ScrapeJobStatusResponse;
}
