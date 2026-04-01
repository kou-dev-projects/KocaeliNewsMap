import { mkdtemp, readFile } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import assert from "node:assert/strict";

import { createPushSubscriptionStore } from "../src/lib/pwa/server/pushSubscriptionStore.ts";

const sampleA = {
  endpoint: "https://example.com/a",
  expirationTime: null,
  keys: {
    auth: "auth-a",
    p256dh: "p256dh-a",
  },
};

const sampleB = {
  endpoint: "https://example.com/b",
  expirationTime: null,
  keys: {
    auth: "auth-b",
    p256dh: "p256dh-b",
  },
};

test("push subscription store keeps concurrent writes", async () => {
  const tempDir = await mkdtemp(path.join(os.tmpdir(), "pulse-push-store-"));
  const storePath = path.join(tempDir, "push-subscriptions.json");
  const store = createPushSubscriptionStore(storePath);

  await Promise.all([
    store.savePushSubscription(sampleA),
    store.savePushSubscription(sampleB),
  ]);

  const subscriptions = await store.readPushSubscriptions();
  assert.equal(subscriptions.length, 2);
  assert.deepEqual(
    subscriptions.map((entry) => entry.endpoint).sort(),
    [sampleA.endpoint, sampleB.endpoint],
  );

  const raw = JSON.parse(await readFile(storePath, "utf-8")) as Array<{ endpoint: string }>;
  assert.equal(raw.length, 2);
});

test("push subscription store removes a saved subscription", async () => {
  const tempDir = await mkdtemp(path.join(os.tmpdir(), "pulse-push-store-"));
  const store = createPushSubscriptionStore(path.join(tempDir, "push-subscriptions.json"));

  await store.savePushSubscription(sampleA);
  await store.removePushSubscription(sampleA.endpoint);

  const subscriptions = await store.readPushSubscriptions();
  assert.deepEqual(subscriptions, []);
});
