"use client";

const STORAGE_KEY = "pulse.scrape.control.token";

const listeners = new Set<() => void>();
let cachedToken: string | undefined;

function isBrowser() {
  return typeof window !== "undefined";
}

function notifyListeners() {
  listeners.forEach((listener) => listener());
}

export function subscribeToScrapeControlToken(listener: () => void) {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

export function getStoredScrapeControlToken(): string {
  if (!isBrowser()) {
    return "";
  }

  const token = window.localStorage.getItem(STORAGE_KEY) ?? "";
  if (cachedToken === token) {
    return token;
  }

  cachedToken = token;
  return token;
}

export function setStoredScrapeControlToken(token: string): string {
  const normalizedToken = token.trim();

  if (!isBrowser()) {
    return normalizedToken;
  }

  if (normalizedToken) {
    window.localStorage.setItem(STORAGE_KEY, normalizedToken);
  } else {
    window.localStorage.removeItem(STORAGE_KEY);
  }

  cachedToken = undefined;
  notifyListeners();
  return normalizedToken;
}

export function clearStoredScrapeControlToken() {
  if (!isBrowser()) {
    return;
  }

  window.localStorage.removeItem(STORAGE_KEY);
  cachedToken = undefined;
  notifyListeners();
}
