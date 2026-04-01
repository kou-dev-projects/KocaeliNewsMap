import assert from "node:assert/strict";
import test from "node:test";

function createPushTestDeps(
  overrides: Partial<import("../src/lib/pwa/server/pushRouteHandlers.ts").PushTestHandlerDeps> =
    {},
): import("../src/lib/pwa/server/pushRouteHandlers.ts").PushTestHandlerDeps {
  return {
    configureWebPush: () => ({ enabled: true }),
    isPushTestAuthorized: () => true,
    normalizePushTestPayload: (payload) => ({
      title: payload.title?.trim() || "PULSE",
      body:
        payload.body?.trim() ||
        "Test push notification delivered successfully.",
      url: payload.url?.trim() || "/",
      tag: payload.tag?.trim() || "pulse-test-notification",
    }),
    readOptionalPushTestPayload: async () => ({}),
    readPushSubscriptions: async () => [],
    removePushSubscription: async () => undefined,
    sendWebPushNotification: async () => undefined,
    ...overrides,
  };
}

test("push subscribe route rejects invalid JSON", async () => {
  const { handlePushSubscribe } = await import(
    "../src/lib/pwa/server/pushRouteHandlers.ts"
  );
  const request = new Request("http://localhost/api/push/subscribe", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: "{invalid",
  });

  const response = await handlePushSubscribe(request, {
    isValidPushSubscriptionPayload: () => true,
    savePushSubscription: async () => undefined,
  });
  const payload = (await response.json()) as { detail: string; status: number };

  assert.equal(response.status, 400);
  assert.equal(payload.detail, "Invalid JSON payload.");
});

test("push subscribe route persists a valid subscription", async () => {
  const { handlePushSubscribe } = await import(
    "../src/lib/pwa/server/pushRouteHandlers.ts"
  );
  let savedEndpoint = "";

  const response = await handlePushSubscribe(
    new Request("http://localhost/api/push/subscribe", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        endpoint: "https://example.com/sub",
        expirationTime: null,
        keys: {
          auth: "auth",
          p256dh: "p256dh",
        },
      }),
    }),
    {
      isValidPushSubscriptionPayload: (payload) =>
        Boolean(payload.endpoint && payload.keys?.auth && payload.keys?.p256dh),
      savePushSubscription: async (subscription) => {
        savedEndpoint = subscription.endpoint;
      },
    },
  );
  const payload = (await response.json()) as { endpoint: string; status: number };

  assert.equal(response.status, 201);
  assert.equal(savedEndpoint, "https://example.com/sub");
  assert.equal(payload.endpoint, "https://example.com/sub");
});

test("push test route rejects unauthorized requests", async () => {
  const { handlePushTest } = await import(
    "../src/lib/pwa/server/pushRouteHandlers.ts"
  );
  const response = await handlePushTest(
    new Request("http://localhost/api/push/test", { method: "POST" }),
    createPushTestDeps({
      isPushTestAuthorized: () => false,
    }),
  );
  const payload = (await response.json()) as { detail: string; status: number };

  assert.equal(response.status, 403);
  assert.equal(payload.detail, "Push test endpoint is disabled or unauthorized.");
});

test("push test route returns 503 when authorized but web push is not configured", async () => {
  const { handlePushTest } = await import(
    "../src/lib/pwa/server/pushRouteHandlers.ts"
  );
  const response = await handlePushTest(
    new Request("http://localhost/api/push/test", { method: "POST" }),
    createPushTestDeps({
      isPushTestAuthorized: () => true,
      configureWebPush: () => ({ enabled: false }),
    }),
  );
  const payload = (await response.json()) as { detail: string; status: number };

  assert.equal(response.status, 503);
  assert.equal(payload.detail, "Web push is not configured.");
});

test("push test route removes expired subscriptions and reports delivery counts", async () => {
  const { handlePushTest } = await import(
    "../src/lib/pwa/server/pushRouteHandlers.ts"
  );
  const removedEndpoints: string[] = [];
  const sentEndpoints: string[] = [];

  const response = await handlePushTest(
    new Request("http://localhost/api/push/test", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        title: "QA Push",
      }),
    }),
    createPushTestDeps({
      isPushTestAuthorized: () => true,
      configureWebPush: () => ({ enabled: true }),
      readPushSubscriptions: async () =>
        [
          {
            endpoint: "https://example.com/alive",
            expirationTime: null,
            keys: {
              auth: "auth-a",
              p256dh: "p256dh-a",
            },
          },
          {
            endpoint: "https://example.com/gone",
            expirationTime: null,
            keys: {
              auth: "auth-b",
              p256dh: "p256dh-b",
            },
          },
        ] as const,
      sendWebPushNotification: async (subscription) => {
        if (subscription.endpoint.endsWith("/gone")) {
          throw { statusCode: 410 };
        }
        sentEndpoints.push(subscription.endpoint);
      },
      removePushSubscription: async (endpoint) => {
        removedEndpoints.push(endpoint);
      },
      readOptionalPushTestPayload: async () => ({
        title: "QA Push",
      }),
    }),
  );
  const payload = (await response.json()) as {
    delivered: number;
    removed: number;
    payload: { title: string; body: string; url: string; tag: string };
    status: number;
  };

  assert.equal(response.status, 200);
  assert.equal(payload.delivered, 1);
  assert.equal(payload.removed, 1);
  assert.deepEqual(sentEndpoints, ["https://example.com/alive"]);
  assert.deepEqual(removedEndpoints, ["https://example.com/gone"]);
  assert.equal(payload.payload.title, "QA Push");
});
