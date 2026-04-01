import { handlePushTest } from "../../../../lib/pwa/server/pushRouteHandlers";
import {
  readPushSubscriptions,
  removePushSubscription,
} from "../../../../lib/pwa/server/pushSubscriptionStore";
import {
  configureWebPush,
  sendWebPushNotification,
} from "../../../../lib/pwa/server/webPush";
import {
  isPushTestAuthorized,
  normalizePushTestPayload,
  readOptionalPushTestPayload,
} from "../../../../lib/pwa/server/pushRouteUtils";

export const runtime = "nodejs";

export async function POST(request: Request): Promise<Response> {
  return handlePushTest(request, {
    configureWebPush,
    isPushTestAuthorized,
    normalizePushTestPayload,
    readOptionalPushTestPayload,
    readPushSubscriptions,
    removePushSubscription,
    sendWebPushNotification,
  });
}
