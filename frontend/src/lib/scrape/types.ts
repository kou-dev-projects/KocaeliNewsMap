export type RawScrapeEvent = {
  event: string;
  message: string;
  timestamp?: number;
  job_id?: string;
  source?: string;
  trigger_type?: string;
  status?: string;
  attempt_count?: number;
  details?: Record<string, unknown>;
};

export type ScrapeLogTone = "info" | "success" | "warning" | "error" | "muted";

export type ScrapeLogDetail = {
  label: string;
  value: string;
};

export type ScrapeLogEntry = {
  id: string;
  event: string;
  title: string;
  message: string;
  timestampLabel: string;
  tone: ScrapeLogTone;
  metadata: string[];
  details: ScrapeLogDetail[];
  jobId?: string;
  source?: string;
  triggerType?: string;
  status?: string;
};

export type ScrapeStreamConnectionState =
  | "idle"
  | "connecting"
  | "connected"
  | "reconnecting"
  | "disconnected"
  | "closed";
