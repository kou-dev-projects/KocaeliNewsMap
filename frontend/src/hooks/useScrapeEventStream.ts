"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { ScrapeEventStreamClient } from "@/lib/scrape/ScrapeEventStreamClient";
import { adaptScrapeEvent } from "@/lib/scrape/scrapeEventAdapter";
import type {
  ScrapeLogEntry,
  ScrapeStreamConnectionState,
} from "@/lib/scrape/types";

const MAX_VISIBLE_EVENTS = 200;

type UseScrapeEventStreamOptions = {
  jobId?: string;
  enabled?: boolean;
  authorizationHeader?: string;
};

export function useScrapeEventStream({
  jobId,
  enabled = true,
  authorizationHeader,
}: UseScrapeEventStreamOptions = {}) {
  const [events, setEvents] = useState<ScrapeLogEntry[]>([]);
  const [connectionState, setConnectionState] =
    useState<ScrapeStreamConnectionState>("idle");
  const [reconnectAttempt, setReconnectAttempt] = useState(0);
  const [lastActivityAt, setLastActivityAt] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const replaceEvents = useCallback((nextEvents: ScrapeLogEntry[]) => {
    setEvents(nextEvents.slice(-MAX_VISIBLE_EVENTS));
  }, []);
  const clearEvents = useCallback(() => {
    setEvents([]);
  }, []);

  useEffect(() => {
    if (!enabled) {
      return;
    }

    const client = new ScrapeEventStreamClient({
      url: "/api/scrape/events",
      jobId,
      authorizationHeader,
      maxReconnectAttempts: 3,
      onStateChange: (nextState) => {
        if (nextState === "connected") {
          setErrorMessage(null);
        }
        setConnectionState(nextState);
      },
      onReconnectAttemptChange: (attempt) => {
        setReconnectAttempt(attempt);
      },
      onHeartbeat: () => {
        setErrorMessage(null);
        setLastActivityAt(new Date().toISOString());
      },
      onError: (message) => {
        setErrorMessage(message);
      },
      onEvent: (event, frameId) => {
        setErrorMessage(null);
        setLastActivityAt(new Date().toISOString());
        setEvents((currentEvents) => {
          const nextEvents = [...currentEvents, adaptScrapeEvent(event, frameId)];
          return nextEvents.slice(-MAX_VISIBLE_EVENTS);
        });
      },
    });

    client.connect();
    return () => {
      client.disconnect();
    };
  }, [authorizationHeader, enabled, jobId]);

  const lastActivityLabel = useMemo(() => {
    if (!lastActivityAt) {
      return "Henüz akış aktivitesi yok";
    }

    return new Intl.DateTimeFormat("tr-TR", {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    }).format(new Date(lastActivityAt));
  }, [lastActivityAt]);

  return {
    events,
    connectionState: enabled ? connectionState : "idle",
    reconnectAttempt: enabled ? reconnectAttempt : 0,
    lastActivityLabel,
    errorMessage: enabled ? errorMessage : null,
    clearEvents,
    replaceEvents,
  };
}
