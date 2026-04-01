import { handlePushSubscribe } from "../../../../lib/pwa/server/pushRouteHandlers";
import { savePushSubscription } from "../../../../lib/pwa/server/pushSubscriptionStore";
import { isValidPushSubscriptionPayload } from "../../../../lib/pwa/server/pushRouteUtils";

export const runtime = "nodejs";

export async function POST(request: Request): Promise<Response> {
  return handlePushSubscribe(request, {
    isValidPushSubscriptionPayload,
    savePushSubscription,
  });
}
