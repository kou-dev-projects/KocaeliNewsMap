import { mkdir, open, readFile, rename, unlink, writeFile } from "node:fs/promises";
import path from "node:path";

import { MongoClient } from "mongodb";

export type StoredPushSubscription = {
  endpoint: string;
  expirationTime?: number | null;
  keys: {
    auth: string;
    p256dh: string;
  };
};

type PushSubscriptionStore = {
  readPushSubscriptions: () => Promise<StoredPushSubscription[]>;
  writePushSubscriptions: (
    subscriptions: StoredPushSubscription[],
  ) => Promise<void>;
  savePushSubscription: (subscription: StoredPushSubscription) => Promise<void>;
  removePushSubscription: (endpoint: string) => Promise<void>;
};

const DEFAULT_DATA_DIR = path.join(process.cwd(), ".data");
const DEFAULT_STORE_PATH =
  process.env.PUSH_SUBSCRIPTIONS_STORE_PATH ||
  path.join(DEFAULT_DATA_DIR, "push-subscriptions.json");
const DEFAULT_COLLECTION_NAME =
  process.env.PUSH_SUBSCRIPTIONS_COLLECTION || "push_subscriptions";

let sharedMongoClient: MongoClient | null = null;
let sharedIndexPromise: Promise<void> | null = null;
let defaultStore: PushSubscriptionStore | null = null;

function isStoredPushSubscription(entry: unknown): entry is StoredPushSubscription {
  return Boolean(
    entry &&
      typeof entry === "object" &&
      "endpoint" in entry &&
      typeof entry.endpoint === "string" &&
      "keys" in entry &&
      entry.keys &&
      typeof entry.keys === "object" &&
      "auth" in entry.keys &&
      typeof entry.keys.auth === "string" &&
      "p256dh" in entry.keys &&
      typeof entry.keys.p256dh === "string",
  );
}

function getMongoConfig(env: NodeJS.ProcessEnv = process.env) {
  const mongoUrl = (
    env.PUSH_SUBSCRIPTIONS_MONGO_URL ||
    env.MONGO_URL ||
    env.mongo_url ||
    ""
  ).trim();
  const mongoDb = (
    env.PUSH_SUBSCRIPTIONS_MONGO_DB ||
    env.MONGO_DB ||
    env.mongo_db ||
    ""
  ).trim();
  const collectionName = (
    env.PUSH_SUBSCRIPTIONS_COLLECTION ||
    DEFAULT_COLLECTION_NAME
  ).trim();

  if (!mongoUrl || !mongoDb) {
    return null;
  }

  return {
    collectionName: collectionName || DEFAULT_COLLECTION_NAME,
    mongoDb,
    mongoUrl,
  };
}

async function getSharedMongoCollection(config: NonNullable<ReturnType<typeof getMongoConfig>>) {
  if (sharedMongoClient === null) {
    sharedMongoClient = new MongoClient(config.mongoUrl, {
      maxPoolSize: 10,
      serverSelectionTimeoutMS: 3000,
    });
    await sharedMongoClient.connect();
  }

  const collection = sharedMongoClient
    .db(config.mongoDb)
    .collection<StoredPushSubscription & { createdAt: Date; updatedAt: Date }>(
      config.collectionName,
    );

  if (sharedIndexPromise === null) {
    sharedIndexPromise = collection
      .createIndex({ endpoint: 1 }, { unique: true, name: "unique_endpoint" })
      .then(() => undefined);
  }
  await sharedIndexPromise;

  return collection;
}

function createFilePushSubscriptionStore(storePath = DEFAULT_STORE_PATH): PushSubscriptionStore {
  const dataDir = path.dirname(storePath);
  const lockPath = `${storePath}.lock`;
  let writeQueue = Promise.resolve();

  async function ensureStoreDir(): Promise<void> {
    await mkdir(dataDir, { recursive: true });
  }

  async function readPushSubscriptions(): Promise<StoredPushSubscription[]> {
    try {
      const raw = await readFile(storePath, "utf-8");
      const parsed = JSON.parse(raw) as unknown;
      if (!Array.isArray(parsed)) {
        return [];
      }

      return parsed.filter(isStoredPushSubscription);
    } catch (error) {
      const nodeError = error as NodeJS.ErrnoException;
      if (nodeError.code === "ENOENT") {
        return [];
      }
      throw error;
    }
  }

  async function writePushSubscriptions(
    subscriptions: StoredPushSubscription[],
  ): Promise<void> {
    await ensureStoreDir();
    const tempPath = `${storePath}.tmp`;
    await writeFile(tempPath, JSON.stringify(subscriptions, null, 2), "utf-8");
    await rename(tempPath, storePath);
  }

  async function withCrossProcessLock<T>(
    operation: () => Promise<T>,
    timeoutMs = 5000,
  ): Promise<T> {
    const deadline = Date.now() + timeoutMs;

    while (true) {
      try {
        await ensureStoreDir();
        const lockHandle = await open(lockPath, "wx");
        try {
          return await operation();
        } finally {
          await lockHandle.close().catch(() => undefined);
          await unlink(lockPath).catch(() => undefined);
        }
      } catch (error) {
        const nodeError = error as NodeJS.ErrnoException;
        if (nodeError.code !== "EEXIST" || Date.now() >= deadline) {
          throw error;
        }
        await new Promise((resolve) => setTimeout(resolve, 25));
      }
    }
  }

  async function withWriteLock<T>(operation: () => Promise<T>): Promise<T> {
    const run = writeQueue.then(
      () => withCrossProcessLock(operation),
      () => withCrossProcessLock(operation),
    );
    writeQueue = run.then(
      () => undefined,
      () => undefined,
    );
    return run;
  }

  async function savePushSubscription(
    subscription: StoredPushSubscription,
  ): Promise<void> {
    await withWriteLock(async () => {
      const subscriptions = await readPushSubscriptions();
      const nextSubscriptions = subscriptions.filter(
        (entry) => entry.endpoint !== subscription.endpoint,
      );
      nextSubscriptions.push(subscription);
      await writePushSubscriptions(nextSubscriptions);
    });
  }

  async function removePushSubscription(endpoint: string): Promise<void> {
    await withWriteLock(async () => {
      const subscriptions = await readPushSubscriptions();
      const nextSubscriptions = subscriptions.filter(
        (entry) => entry.endpoint !== endpoint,
      );
      await writePushSubscriptions(nextSubscriptions);
    });
  }

  return {
    readPushSubscriptions,
    writePushSubscriptions,
    savePushSubscription,
    removePushSubscription,
  };
}

function createMongoPushSubscriptionStore(
  config: NonNullable<ReturnType<typeof getMongoConfig>>,
): PushSubscriptionStore {
  async function readPushSubscriptions(): Promise<StoredPushSubscription[]> {
    const collection = await getSharedMongoCollection(config);
    const docs = await collection
      .find({}, { projection: { _id: 0, endpoint: 1, expirationTime: 1, keys: 1 } })
      .toArray();
    return docs.filter(isStoredPushSubscription);
  }

  async function writePushSubscriptions(
    subscriptions: StoredPushSubscription[],
  ): Promise<void> {
    const collection = await getSharedMongoCollection(config);

    if (subscriptions.length === 0) {
      await collection.deleteMany({});
      return;
    }

    const endpoints = subscriptions.map((entry) => entry.endpoint);
    await collection.deleteMany({ endpoint: { $nin: endpoints } });
    await collection.bulkWrite(
      subscriptions.map((subscription) => ({
        updateOne: {
          filter: { endpoint: subscription.endpoint },
          update: {
            $set: {
              endpoint: subscription.endpoint,
              expirationTime: subscription.expirationTime ?? null,
              keys: {
                auth: subscription.keys.auth,
                p256dh: subscription.keys.p256dh,
              },
              updatedAt: new Date(),
            },
            $setOnInsert: {
              createdAt: new Date(),
            },
          },
          upsert: true,
        },
      })),
      { ordered: false },
    );
  }

  async function savePushSubscription(
    subscription: StoredPushSubscription,
  ): Promise<void> {
    const collection = await getSharedMongoCollection(config);
    await collection.updateOne(
      { endpoint: subscription.endpoint },
      {
        $set: {
          endpoint: subscription.endpoint,
          expirationTime: subscription.expirationTime ?? null,
          keys: {
            auth: subscription.keys.auth,
            p256dh: subscription.keys.p256dh,
          },
          updatedAt: new Date(),
        },
        $setOnInsert: {
          createdAt: new Date(),
        },
      },
      { upsert: true },
    );
  }

  async function removePushSubscription(endpoint: string): Promise<void> {
    const collection = await getSharedMongoCollection(config);
    await collection.deleteOne({ endpoint });
  }

  return {
    readPushSubscriptions,
    writePushSubscriptions,
    savePushSubscription,
    removePushSubscription,
  };
}

function getDefaultStore(): PushSubscriptionStore {
  if (defaultStore !== null) {
    return defaultStore;
  }

  const mongoConfig = getMongoConfig();
  defaultStore =
    mongoConfig === null
      ? createFilePushSubscriptionStore(DEFAULT_STORE_PATH)
      : createMongoPushSubscriptionStore(mongoConfig);
  return defaultStore;
}

export function createPushSubscriptionStore(storePath = DEFAULT_STORE_PATH) {
  return createFilePushSubscriptionStore(storePath);
}

export function createProductionPushSubscriptionStore(
  env: NodeJS.ProcessEnv = process.env,
) {
  const mongoConfig = getMongoConfig(env);
  if (mongoConfig === null) {
    return createFilePushSubscriptionStore(
      env.PUSH_SUBSCRIPTIONS_STORE_PATH || DEFAULT_STORE_PATH,
    );
  }
  return createMongoPushSubscriptionStore(mongoConfig);
}

export async function readPushSubscriptions() {
  return getDefaultStore().readPushSubscriptions();
}

export async function writePushSubscriptions(
  subscriptions: StoredPushSubscription[],
) {
  return getDefaultStore().writePushSubscriptions(subscriptions);
}

export async function savePushSubscription(subscription: StoredPushSubscription) {
  return getDefaultStore().savePushSubscription(subscription);
}

export async function removePushSubscription(endpoint: string) {
  return getDefaultStore().removePushSubscription(endpoint);
}
