"use client";

import { useCallback, useState, useSyncExternalStore } from "react";

import {
  clearStoredScrapeControlToken,
  getStoredScrapeControlToken,
  setStoredScrapeControlToken,
  subscribeToScrapeControlToken,
} from "@/lib/scrape-control";

function subscribeHydration() {
  return () => {};
}

export function useScrapeControlTokenState() {
  const storedToken = useSyncExternalStore(
    subscribeToScrapeControlToken,
    getStoredScrapeControlToken,
    () => "",
  );
  const isHydrated = useSyncExternalStore(
    subscribeHydration,
    () => true,
    () => false,
  );
  const [draftToken, setDraftToken] = useState("");
  const [hasDraftOverride, setHasDraftOverride] = useState(false);

  const controlTokenInput = hasDraftOverride ? draftToken : storedToken;
  const hasControlAccess = Boolean(storedToken);

  const setControlTokenInput = useCallback((value: string) => {
    setDraftToken(value);
    setHasDraftOverride(true);
  }, []);

  const unlock = useCallback((token: string) => {
    const normalizedToken = setStoredScrapeControlToken(token);
    setDraftToken(normalizedToken);
    setHasDraftOverride(false);
    return normalizedToken;
  }, []);

  const lock = useCallback(() => {
    clearStoredScrapeControlToken();
    setDraftToken("");
    setHasDraftOverride(false);
  }, []);

  return {
    isHydrated,
    controlTokenInput,
    setControlTokenInput,
    hasControlAccess,
    unlock,
    lock,
  };
}
