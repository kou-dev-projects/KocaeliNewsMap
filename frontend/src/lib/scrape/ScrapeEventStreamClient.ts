"use client";

import { parseSseFrames } from "@/lib/scrape/parseSseFrames";
import type {
  RawScrapeEvent,
  ScrapeStreamConnectionState,
} from "@/lib/scrape/types";

const RECONNECT_BASE_DELAY_MS = 1000;
const RECONNECT_MAX_DELAY_MS = 5000;
const LIVENESS_TIMEOUT_MS = 45000;

type ScrapeEventStreamCallbacks = {
  onStateChange?: (state: ScrapeStreamConnectionState) => void;
  onEvent?: (event: RawScrapeEvent, frameId: string) => void;
  onHeartbeat?: () => void;
  onReconnectAttemptChange?: (attempt: number) => void;
  onError?: (message: string) => void;
};

type ScrapeEventStreamOptions = {
  url: string;
  jobId?: string;
  maxReconnectAttempts?: number;
} & ScrapeEventStreamCallbacks;

export class ScrapeEventStreamClient {
  private readonly url: string;
  private readonly jobId?: string;
  private readonly maxReconnectAttempts: number;
  private readonly callbacks: ScrapeEventStreamCallbacks;

  private state: ScrapeStreamConnectionState = "idle";
  private abortController: AbortController | null = null;
  private reconnectTimer: number | null = null;
  private livenessTimer: number | null = null;
  private reconnectAttempt = 0;
  private lastEventId: string | null = null;
  private intentionalClose = false;

  constructor(options: ScrapeEventStreamOptions) {
    this.url = options.url;
    this.jobId = options.jobId;
    this.maxReconnectAttempts = options.maxReconnectAttempts ?? 3;
    this.callbacks = options;
  }

  connect(): void {
    if (this.state === "connecting" || this.state === "connected") {
      return;
    }

    this.intentionalClose = false;
    this.reconnectAttempt = 0;
    this.callbacks.onReconnectAttemptChange?.(0);
    void this.openStream(false);
  }

  disconnect(): void {
    this.intentionalClose = true;
    this.clearReconnectTimer();
    this.clearLivenessTimer();
    this.abortController?.abort();
    this.abortController = null;
    this.setState("closed");
  }

  private setState(nextState: ScrapeStreamConnectionState): void {
    if (this.state === nextState) {
      return;
    }

    this.state = nextState;
    this.callbacks.onStateChange?.(nextState);
  }

  private resetLivenessTimer(): void {
    this.clearLivenessTimer();
    this.livenessTimer = window.setTimeout(() => {
      this.abortController?.abort();
    }, LIVENESS_TIMEOUT_MS);
  }

  private clearLivenessTimer(): void {
    if (this.livenessTimer !== null) {
      window.clearTimeout(this.livenessTimer);
      this.livenessTimer = null;
    }
  }

  private clearReconnectTimer(): void {
    if (this.reconnectTimer !== null) {
      window.clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
  }

  private buildRequestUrl(): string {
    const url = new URL(this.url, window.location.origin);
    if (this.jobId) {
      url.searchParams.set("job_id", this.jobId);
    }
    return url.toString();
  }

  private async openStream(isReconnect: boolean): Promise<void> {
    this.clearReconnectTimer();
    this.clearLivenessTimer();
    this.abortController = new AbortController();
    this.setState(isReconnect ? "reconnecting" : "connecting");

    const headers = new Headers({
      Accept: "text/event-stream",
      "Cache-Control": "no-cache",
    });

    if (this.lastEventId) {
      headers.set("Last-Event-ID", this.lastEventId);
    }

    try {
      const response = await fetch(this.buildRequestUrl(), {
        method: "GET",
        headers,
        cache: "no-store",
        signal: this.abortController.signal,
      });

      if (!response.ok || !response.body) {
        if ([401, 403, 404].includes(response.status)) {
          this.callbacks.onError?.("The scrape log stream was rejected.");
          this.setState("disconnected");
          return;
        }

        throw new Error(`Stream request failed with HTTP ${response.status}`);
      }

      this.reconnectAttempt = 0;
      this.callbacks.onReconnectAttemptChange?.(0);
      this.setState("connected");
      this.resetLivenessTimer();

      await this.readStream(response.body);

      if (!this.intentionalClose) {
        throw new Error("The scrape log stream ended unexpectedly.");
      }
    } catch (error) {
      if (this.intentionalClose) {
        return;
      }

      const message =
        error instanceof Error ? error.message : "The scrape log stream failed.";
      this.callbacks.onError?.(message);
      this.scheduleReconnect();
    }
  }

  private async readStream(body: ReadableStream<Uint8Array>): Promise<void> {
    const reader = body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) {
          break;
        }

        buffer += decoder.decode(value, { stream: true });
        const { frames, remaining } = parseSseFrames(buffer);
        buffer = remaining;

        for (const frame of frames) {
          this.resetLivenessTimer();

          if (frame.id) {
            this.lastEventId = frame.id;
          }

          if (frame.isComment) {
            this.callbacks.onHeartbeat?.();
            continue;
          }

          if (!frame.data) {
            continue;
          }

          try {
            const parsedEvent = JSON.parse(frame.data) as RawScrapeEvent;
            this.callbacks.onEvent?.(parsedEvent, frame.id ?? crypto.randomUUID());
          } catch {
            this.callbacks.onError?.(
              "The scrape log stream returned invalid event data.",
            );
          }
        }
      }
    } finally {
      reader.releaseLock();
    }
  }

  private scheduleReconnect(): void {
    this.clearLivenessTimer();

    if (this.reconnectAttempt >= this.maxReconnectAttempts) {
      this.setState("disconnected");
      return;
    }

    this.reconnectAttempt += 1;
    this.callbacks.onReconnectAttemptChange?.(this.reconnectAttempt);
    this.setState("reconnecting");

    const delay = Math.min(
      RECONNECT_BASE_DELAY_MS * 2 ** (this.reconnectAttempt - 1),
      RECONNECT_MAX_DELAY_MS,
    );

    this.reconnectTimer = window.setTimeout(() => {
      void this.openStream(true);
    }, delay);
  }
}
