export type StoredPushSubscription = {
  endpoint: string;
  expirationTime?: number | null;
  keys: {
    auth: string;
    p256dh: string;
  };
};

export type PushSubscriptionPayload = {
  endpoint?: string;
  expirationTime?: number | null;
  keys?: {
    auth?: string;
    p256dh?: string;
  };
};

export type PushTestPayload = {
  title?: string;
  body?: string;
  url?: string;
  tag?: string;
};

export type NormalizedPushTestPayload = {
  title: string;
  body: string;
  url: string;
  tag: string;
};

export type PushSubscribeHandlerDeps = {
  isValidPushSubscriptionPayload: (
    payload: PushSubscriptionPayload,
  ) => boolean;
  savePushSubscription: (subscription: StoredPushSubscription) => Promise<void>;
};

export type PushTestHandlerDeps = {
  configureWebPush: () => { enabled: boolean };
  isPushTestAuthorized: (request: Request) => boolean;
  normalizePushTestPayload: (
    payload: PushTestPayload,
  ) => NormalizedPushTestPayload;
  readOptionalPushTestPayload: (
    request: Request,
  ) => Promise<PushTestPayload>;
  readPushSubscriptions: () => Promise<StoredPushSubscription[]>;
  removePushSubscription: (endpoint: string) => Promise<void>;
  sendWebPushNotification: (
    subscription: StoredPushSubscription,
    payload: NormalizedPushTestPayload,
  ) => Promise<void>;
};

export async function handlePushSubscribe(
  request: Request,
  deps: PushSubscribeHandlerDeps,
): Promise<Response> {
  let payload: PushSubscriptionPayload;
  try {
    payload = (await request.json()) as PushSubscriptionPayload;
  } catch {
    return Response.json(
      {
        detail: "Invalid JSON payload.",
        status: 400,
      },
      { status: 400 },
    );
  }

  if (!deps.isValidPushSubscriptionPayload(payload)) {
    return Response.json(
      {
        detail: "Invalid push subscription payload.",
        status: 400,
      },
      { status: 400 },
    );
  }

  await deps.savePushSubscription({
    endpoint: payload.endpoint!,
    expirationTime: payload.expirationTime ?? null,
    keys: {
      auth: payload.keys!.auth!,
      p256dh: payload.keys!.p256dh!,
    },
  });

  return Response.json(
    {
      detail: "Push subscription saved.",
      endpoint: payload.endpoint,
      status: 201,
    },
    { status: 201 },
  );
}

export async function handlePushTest(
  request: Request,
  deps: PushTestHandlerDeps,
): Promise<Response> {
  if (!deps.isPushTestAuthorized(request)) {
    return Response.json(
      {
        detail: "Push test endpoint is disabled or unauthorized.",
        status: 403,
      },
      { status: 403 },
    );
  }

  const { enabled } = deps.configureWebPush();
  if (!enabled) {
    return Response.json(
      {
        detail: "Web push is not configured.",
        status: 503,
      },
      { status: 503 },
    );
  }

  const subscriptions = await deps.readPushSubscriptions();
  if (subscriptions.length === 0) {
    return Response.json(
      {
        detail: "No push subscriptions are stored.",
        status: 404,
      },
      { status: 404 },
    );
  }

  const requestedPayload = await deps.readOptionalPushTestPayload(request);
  const payload = deps.normalizePushTestPayload(requestedPayload);

  let delivered = 0;
  let removed = 0;

  await Promise.all(
    subscriptions.map(async (subscription) => {
      try {
        await deps.sendWebPushNotification(subscription, payload);
        delivered += 1;
      } catch (error) {
        const statusCode = (error as { statusCode?: number }).statusCode;
        if (statusCode === 404 || statusCode === 410) {
          removed += 1;
          await deps.removePushSubscription(subscription.endpoint);
          return;
        }
        throw error;
      }
    }),
  );

  return Response.json(
    {
      detail: "Push delivery attempt finished.",
      delivered,
      removed,
      payload,
      status: 200,
    },
    { status: 200 },
  );
}
