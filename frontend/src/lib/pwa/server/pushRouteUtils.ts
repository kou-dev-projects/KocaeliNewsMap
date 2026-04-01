export type PushSubscriptionKeys = {
  auth?: string;
  p256dh?: string;
};

export type PushSubscriptionPayload = {
  endpoint?: string;
  expirationTime?: number | null;
  keys?: PushSubscriptionKeys;
};

export type PushTestPayload = {
  title?: string;
  body?: string;
  url?: string;
  tag?: string;
};

export function isValidPushSubscriptionPayload(
  payload: PushSubscriptionPayload,
): boolean {
  return Boolean(
    payload.endpoint &&
      typeof payload.endpoint === "string" &&
      payload.keys?.auth &&
      payload.keys?.p256dh,
  );
}

export function isPushTestAuthorized(
  request: Request,
  env: NodeJS.ProcessEnv = process.env,
): boolean {
  const localQaEnabled =
    env.ENABLE_PUSH_TEST_ENDPOINT === "true" && env.NODE_ENV !== "production";
  if (localQaEnabled) {
    return true;
  }

  const expectedKey = (env.PUSH_TEST_API_KEY || "").trim();
  if (!expectedKey) {
    return false;
  }

  const providedKey = (request.headers.get("x-push-test-key") || "").trim();
  return providedKey.length > 0 && providedKey === expectedKey;
}

export async function readOptionalPushTestPayload(
  request: Request,
): Promise<PushTestPayload> {
  const contentType = request.headers.get("content-type") || "";
  if (!contentType.includes("application/json")) {
    return {};
  }

  try {
    return (await request.json()) as PushTestPayload;
  } catch {
    return {};
  }
}

export function normalizePushTestPayload(requestedPayload: PushTestPayload) {
  return {
    title: requestedPayload.title?.trim() || "PULSE",
    body:
      requestedPayload.body?.trim() ||
      "Test push notification delivered successfully.",
    url: requestedPayload.url?.trim() || "/",
    tag: requestedPayload.tag?.trim() || "pulse-test-notification",
  };
}
