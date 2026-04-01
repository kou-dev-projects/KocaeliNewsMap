import assert from "node:assert/strict";
import test from "node:test";

import {
  isPushTestAuthorized,
  isValidPushSubscriptionPayload,
  normalizePushTestPayload,
} from "../src/lib/pwa/server/pushRouteUtils.ts";

test("push subscription payload validator rejects incomplete payloads", () => {
  assert.equal(
    isValidPushSubscriptionPayload({
      endpoint: "https://example.com/sub",
    }),
    false,
  );
});

test("push subscription payload validator accepts valid payloads", () => {
  assert.equal(
    isValidPushSubscriptionPayload({
      endpoint: "https://example.com/sub",
      keys: {
        auth: "auth",
        p256dh: "p256dh",
      },
    }),
    true,
  );
});

test("push test auth is forbidden by default", () => {
  const request = new Request("http://localhost/api/push/test", {
    method: "POST",
  });
  assert.equal(
    isPushTestAuthorized(request, {
      NODE_ENV: "production",
    }),
    false,
  );
});

test("push test auth allows explicit local QA mode", () => {
  const request = new Request("http://localhost/api/push/test", {
    method: "POST",
  });
  assert.equal(
    isPushTestAuthorized(request, {
      NODE_ENV: "development",
      ENABLE_PUSH_TEST_ENDPOINT: "true",
    }),
    true,
  );
});

test("push test auth accepts a matching secret header", () => {
  const request = new Request("http://localhost/api/push/test", {
    method: "POST",
    headers: {
      "x-push-test-key": "secret-123",
    },
  });
  assert.equal(
    isPushTestAuthorized(request, {
      NODE_ENV: "production",
      PUSH_TEST_API_KEY: "secret-123",
    }),
    true,
  );
});

test("push test payload normalization fills safe defaults", () => {
  assert.deepEqual(normalizePushTestPayload({}), {
    title: "PULSE",
    body: "Test push notification delivered successfully.",
    url: "/",
    tag: "pulse-test-notification",
  });
});
