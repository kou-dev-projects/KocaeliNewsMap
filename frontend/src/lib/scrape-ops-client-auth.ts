"use client"

const STORAGE_KEY = "pulse.scrape.ops.auth"
const EMPTY_SNAPSHOT: ScrapeOpsAuthSnapshot = null

export type ScrapeOpsAuthSnapshot = {
  username: string
  authorizationHeader: string
} | null

type StoredCredentials = {
  username: string
  password: string
}

const listeners = new Set<() => void>()
let cachedRawCredentials: string | null | undefined
let cachedSnapshot: ScrapeOpsAuthSnapshot = EMPTY_SNAPSHOT

function notifyListeners() {
  listeners.forEach((listener) => listener())
}

function isBrowser() {
  return typeof window !== "undefined"
}

function encodeBasicAuth(username: string, password: string) {
  return `Basic ${window.btoa(`${username}:${password}`)}`
}

function parseStoredCredentials(raw: string | null): StoredCredentials | null {
  if (!raw) {
    return null
  }

  try {
    const parsed = JSON.parse(raw) as Partial<StoredCredentials>
    const username = (parsed.username || "").trim()
    const password = parsed.password || ""
    if (!username || !password) {
      window.sessionStorage.removeItem(STORAGE_KEY)
      return null
    }

    return { username, password }
  } catch {
    if (isBrowser()) {
      window.sessionStorage.removeItem(STORAGE_KEY)
    }
    return null
  }
}

export function getScrapeOpsAuthSnapshot(): ScrapeOpsAuthSnapshot {
  if (!isBrowser()) {
    return EMPTY_SNAPSHOT
  }

  const raw = window.sessionStorage.getItem(STORAGE_KEY)
  if (raw === cachedRawCredentials) {
    return cachedSnapshot
  }

  const stored = parseStoredCredentials(raw)
  cachedRawCredentials = stored ? raw : null

  if (!stored) {
    cachedSnapshot = EMPTY_SNAPSHOT
    return cachedSnapshot
  }

  cachedSnapshot = {
    username: stored.username,
    authorizationHeader: encodeBasicAuth(stored.username, stored.password),
  }

  return cachedSnapshot
}

export function subscribeScrapeOpsAuth(listener: () => void) {
  listeners.add(listener)
  return () => {
    listeners.delete(listener)
  }
}

export function setScrapeOpsCredentials(username: string, password: string) {
  if (!isBrowser()) {
    return
  }

  const normalizedUsername = username.trim()
  if (!normalizedUsername || !password) {
    throw new Error("Eksik ops kimlik bilgisi.")
  }

  window.sessionStorage.setItem(
    STORAGE_KEY,
    JSON.stringify({
      username: normalizedUsername,
      password,
    } satisfies StoredCredentials),
  )
  cachedRawCredentials = undefined
  notifyListeners()
}

export function clearScrapeOpsCredentials() {
  if (!isBrowser()) {
    return
  }

  window.sessionStorage.removeItem(STORAGE_KEY)
  cachedRawCredentials = undefined
  notifyListeners()
}
