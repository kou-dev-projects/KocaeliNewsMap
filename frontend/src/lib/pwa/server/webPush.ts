import webpush from "web-push";

export type WebPushPayload = {
  title: string;
  body: string;
  url?: string;
  tag?: string;
};

export function configureWebPush(): { enabled: boolean } {
  const subject = (process.env.VAPID_SUBJECT || "").trim();
  const publicKey = (
    process.env.NEXT_PUBLIC_VAPID_PUBLIC_KEY ||
    process.env.VAPID_PUBLIC_KEY ||
    ""
  ).trim();
  const privateKey = (process.env.VAPID_PRIVATE_KEY || "").trim();

  if (!subject || !publicKey || !privateKey) {
    return { enabled: false };
  }

  webpush.setVapidDetails(subject, publicKey, privateKey);
  return { enabled: true };
}

export async function sendWebPushNotification(
  subscription: webpush.PushSubscription,
  payload: WebPushPayload,
): Promise<void> {
  await webpush.sendNotification(subscription, JSON.stringify(payload));
}
