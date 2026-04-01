import type {
  RawScrapeEvent,
  ScrapeLogEntry,
  ScrapeLogTone,
} from "@/lib/scrape/types";

const eventTitles: Record<string, string> = {
  job_submitted: "Job queued",
  job_started: "Job started",
  job_heartbeat: "Job heartbeat",
  job_retrying: "Retry scheduled",
  job_failed: "Job failed",
  job_completed: "Job completed",
  job_stale_ack: "Stale job acknowledged",
  scheduler_job_skipped: "Scheduler skipped duplicate work",
  scheduler_submit_failed: "Scheduler submission failed",
};

function getTone(event: RawScrapeEvent): ScrapeLogTone {
  if (event.status === "failed" || event.event.includes("failed")) {
    return "error";
  }
  if (event.status === "completed") {
    return "success";
  }
  if (event.event.includes("retry") || event.event.includes("skipped")) {
    return "warning";
  }
  if (event.event.includes("heartbeat")) {
    return "muted";
  }
  return "info";
}

function formatTimestamp(timestamp?: number): string {
  if (!timestamp) {
    return "--:--:--";
  }

  return new Intl.DateTimeFormat("en-GB", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(new Date(timestamp * 1000));
}

function buildMetadata(event: RawScrapeEvent): string[] {
  const metadata: string[] = [];

  if (event.job_id) {
    metadata.push(`Job ${event.job_id.slice(0, 8)}`);
  }

  if (event.source) {
    metadata.push(`Source ${event.source}`);
  }

  if (event.trigger_type) {
    metadata.push(`Trigger ${event.trigger_type}`);
  }

  if (typeof event.attempt_count === "number") {
    metadata.push(`Attempt ${event.attempt_count}`);
  }

  const error =
    typeof event.details?.error === "string" ? event.details.error : undefined;
  if (error) {
    metadata.push(error);
  }

  return metadata;
}

export function adaptScrapeEvent(
  rawEvent: RawScrapeEvent,
  id: string,
): ScrapeLogEntry {
  return {
    id,
    event: rawEvent.event,
    title: eventTitles[rawEvent.event] ?? "Scrape update",
    message: rawEvent.message,
    timestampLabel: formatTimestamp(rawEvent.timestamp),
    tone: getTone(rawEvent),
    metadata: buildMetadata(rawEvent),
  };
}
