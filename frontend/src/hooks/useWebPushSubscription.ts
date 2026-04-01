"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { urlBase64ToUint8Array } from "@/lib/pwa/pushClient";

type SubscribeResult = {
  success: boolean;
  message: string;
};

const PUBLIC_VAPID_KEY = (process.env.NEXT_PUBLIC_VAPID_PUBLIC_KEY || "").trim();
const PUSH_TEST_ENABLED = process.env.NEXT_PUBLIC_ENABLE_PUSH_TEST === "true";

export function useWebPushSubscription(enabled = true) {
  const [permission, setPermission] = useState<NotificationPermission>(() =>
    typeof Notification === "undefined" ? "default" : Notification.permission,
  );
  const [isSubscribed, setIsSubscribed] = useState(false);
  const [isBusy, setIsBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const browserSupportsPush = useMemo(
    () =>
      typeof window !== "undefined" &&
      "Notification" in window &&
      "serviceWorker" in navigator &&
      "PushManager" in window,
    [],
  );

  const isConfigured = PUBLIC_VAPID_KEY.length > 0;
  const isSupported = enabled && browserSupportsPush;

  const refreshSubscriptionState = useCallback(async () => {
    if (!enabled || !browserSupportsPush || !isConfigured) {
      setIsSubscribed(false);
      return;
    }

    const registration = await navigator.serviceWorker.ready;
    const subscription = await registration.pushManager.getSubscription();
    setPermission(Notification.permission);
    setIsSubscribed(Boolean(subscription));
  }, [browserSupportsPush, enabled, isConfigured]);

  useEffect(() => {
    if (!enabled || !browserSupportsPush || !isConfigured) {
      setIsSubscribed(false);
      setMessage(null);
      return;
    }

    let isMounted = true;
    void refreshSubscriptionState()
      .then(() => {
        if (!isMounted) {
          return;
        }
      })
      .catch(() => {
        if (isMounted) {
          setMessage("Unable to load push subscription status.");
        }
      });

    return () => {
      isMounted = false;
    };
  }, [browserSupportsPush, enabled, isConfigured, refreshSubscriptionState]);

  async function subscribe(): Promise<SubscribeResult> {
    if (!enabled) {
      return {
        success: false,
        message: "Push notifications are disabled in this environment.",
      };
    }

    if (!browserSupportsPush) {
      return {
        success: false,
        message: "Push notifications are not supported in this browser.",
      };
    }

    if (!isConfigured) {
      return {
        success: false,
        message: "Push notifications are not configured yet.",
      };
    }

    setIsBusy(true);
    setMessage(null);

    try {
      const nextPermission = await Notification.requestPermission();
      setPermission(nextPermission);

      if (nextPermission !== "granted") {
        const deniedMessage = "Notification permission was not granted.";
        setMessage(deniedMessage);
        return { success: false, message: deniedMessage };
      }

      const registration = await navigator.serviceWorker.ready;
      const existingSubscription =
        await registration.pushManager.getSubscription();

      const subscription =
        existingSubscription ||
        (await registration.pushManager.subscribe({
          userVisibleOnly: true,
          applicationServerKey:
            urlBase64ToUint8Array(PUBLIC_VAPID_KEY) as BufferSource,
        }));

      const response = await fetch("/api/push/subscribe", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(subscription),
      });

      const payload = (await response.json()) as { detail?: string };
      if (!response.ok) {
        const failureMessage =
          payload.detail || "Push subscription could not be saved.";
        setMessage(failureMessage);
        return { success: false, message: failureMessage };
      }

      await refreshSubscriptionState();
      const successMessage = payload.detail || "Push notifications enabled.";
      setMessage(successMessage);
      return { success: true, message: successMessage };
    } catch {
      const errorMessage = "Push subscription failed.";
      setMessage(errorMessage);
      return { success: false, message: errorMessage };
    } finally {
      setIsBusy(false);
    }
  }

  async function sendTestNotification(): Promise<SubscribeResult> {
    if (!PUSH_TEST_ENABLED) {
      return {
        success: false,
        message: "Push test delivery is disabled in this environment.",
      };
    }

    setIsBusy(true);
    setMessage(null);

    try {
      const response = await fetch("/api/push/test", {
        method: "POST",
      });
      const payload = (await response.json()) as { detail?: string };
      const detail =
        payload.detail ||
        (response.ok
          ? "Test notification triggered."
          : "Test notification failed.");
      setMessage(detail);
      return { success: response.ok, message: detail };
    } catch {
      const errorMessage = "Test notification request failed.";
      setMessage(errorMessage);
      return { success: false, message: errorMessage };
    } finally {
      setIsBusy(false);
    }
  }

  return {
    isEnabled: enabled,
    isBusy,
    isConfigured,
    isSubscribed,
    isSupported,
    isTestEnabled: PUSH_TEST_ENABLED,
    message,
    permission,
    sendTestNotification,
    subscribe,
  };
}
