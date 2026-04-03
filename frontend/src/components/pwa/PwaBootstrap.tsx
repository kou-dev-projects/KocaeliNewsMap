"use client";

import { useEffect, useMemo, useState } from "react";

import { useOnlineStatus } from "@/hooks/useOnlineStatus";
import { usePwaInstallPrompt } from "@/hooks/usePwaInstallPrompt";
import { useWebPushSubscription } from "@/hooks/useWebPushSubscription";

export function PwaBootstrap() {
  const [isMounted, setIsMounted] = useState(false);
  const isOnline = useOnlineStatus();
  const shouldRegisterServiceWorker =
    process.env.NODE_ENV === "production" ||
    process.env.NEXT_PUBLIC_ENABLE_PWA_IN_DEV === "true";
  const { canPrompt, isDismissed, isStandalone, promptInstall, dismissPrompt } =
    usePwaInstallPrompt();
  const {
    isEnabled: isPushEnabled,
    isBusy: isPushBusy,
    isConfigured: isPushConfigured,
    isSubscribed,
    isSupported: isPushSupported,
    isTestEnabled: isPushTestEnabled,
    message: pushMessage,
    permission: pushPermission,
    sendTestNotification,
    subscribe,
  } = useWebPushSubscription(shouldRegisterServiceWorker);
  const [isPromptPending, setIsPromptPending] = useState(false);

  useEffect(() => {
    const frameId = window.requestAnimationFrame(() => {
      setIsMounted(true);
    });

    return () => {
      window.cancelAnimationFrame(frameId);
    };
  }, []);

  useEffect(() => {
    if (!("serviceWorker" in navigator)) {
      return;
    }

    if (!shouldRegisterServiceWorker) {
      void navigator.serviceWorker.getRegistrations().then((registrations) => {
        registrations.forEach((registration) => {
          const urls = [
            registration.installing?.scriptURL,
            registration.waiting?.scriptURL,
            registration.active?.scriptURL,
          ].filter(Boolean);
          if (urls.some((scriptUrl) => scriptUrl?.endsWith("/sw.js"))) {
            void registration.unregister();
          }
        });
      });
      return;
    }

    if (!window.isSecureContext) {
      return;
    }

    void navigator.serviceWorker
      .register("/sw.js", { scope: "/" })
      .then((registration) => registration.update())
      .catch(() => undefined);
  }, [shouldRegisterServiceWorker]);

  const installCopy = useMemo(() => {
    if (isStandalone) {
      return null;
    }

    if (isPromptPending) {
      return "Kurulum istegi hazirlaniyor.";
    }

    if (isDismissed) {
      return "Kurulum bildirimi simdilik ertelendi.";
    }

    if (!canPrompt) {
      return null;
    }

    return "PULSE'u ana ekrana ekleyerek daha hizli acilis ve cevrimdisi destek alabilirsiniz.";
  }, [canPrompt, isDismissed, isPromptPending, isStandalone]);

  const showPushControls =
    isOnline &&
    isPushEnabled &&
    isPushConfigured &&
    isPushSupported &&
    (pushPermission !== "granted" || isSubscribed);
  const showBanner =
    !isOnline || isDismissed || (canPrompt && !isStandalone) || showPushControls;
  if (!isMounted || !showBanner) {
    return null;
  }

  return (
    <div className="pointer-events-none fixed inset-x-0 bottom-24 z-50 flex justify-center px-4 md:bottom-4 md:justify-end">
      <div className="pointer-events-auto w-full max-w-md rounded-[22px] border border-slate-900/10 bg-white/95 p-4 text-slate-900 shadow-[0_24px_60px_rgba(15,23,42,0.22)] backdrop-blur">
        <div className="flex items-start justify-between gap-4">
          <div className="space-y-2">
            {!isOnline ? (
              <>
                <p className="text-xs font-semibold uppercase tracking-[0.22em] text-amber-600">
                  Offline mod
                </p>
                <p className="text-sm leading-6 text-slate-700">
                  Baglanti yokken onbellekteki harita ve son gorulen ekranlar
                  kullanilmaya devam eder.
                </p>
              </>
            ) : null}

            {canPrompt && installCopy ? (
              <>
                <p className="text-xs font-semibold uppercase tracking-[0.22em] text-sky-700">
                  Uygulama hazir
                </p>
                <p className="text-sm leading-6 text-slate-700">{installCopy}</p>
              </>
            ) : null}

            {!canPrompt && isDismissed ? (
              <>
                <p className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">
                  Kurulum bildirimi
                </p>
                <p className="text-sm leading-6 text-slate-700">{installCopy}</p>
              </>
            ) : null}

            {showPushControls ? (
              <>
                <p className="text-xs font-semibold uppercase tracking-[0.22em] text-emerald-700">
                  Bildirimler
                </p>
                <p className="text-sm leading-6 text-slate-700">
                  {pushPermission === "denied"
                    ? "Bildirimler tarayici ayarlarinda engellenmis. Uyari almak icin once izin verin."
                    : pushPermission === "granted"
                    ? isSubscribed
                      ? isPushTestEnabled
                        ? "Bildirimler aktif. Test bildirimi gonderebilirsiniz."
                        : "Bildirimler aktif."
                      : "Bildirim izni verildi. Teslimati acmak icin aboneligi tamamlayin."
                    : "Saha uyarilari ve scrape guncellemeleri icin bildirimleri acin."}
                </p>
                {pushMessage ? (
                  <p className="text-xs font-medium text-slate-500">{pushMessage}</p>
                ) : null}
              </>
            ) : null}
          </div>

          {!isOnline ? (
            <span className="rounded-full border border-amber-200 bg-amber-50 px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-amber-700">
              Offline
            </span>
          ) : (
            <span className="rounded-full border border-sky-200 bg-sky-50 px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-sky-700">
              PWA
            </span>
          )}
        </div>

        {canPrompt ? (
          <div className="mt-4 flex flex-wrap gap-3">
            <button
              type="button"
              onClick={async () => {
                setIsPromptPending(true);
                const outcome = await promptInstall();
                setIsPromptPending(false);
                if (outcome === "unavailable") {
                  return;
                }
              }}
              className="rounded-full bg-slate-950 px-4 py-2 text-sm font-semibold text-white transition hover:bg-slate-800"
            >
              Ana ekrana ekle
            </button>
            <button
              type="button"
              onClick={() => {
                dismissPrompt();
              }}
              className="rounded-full border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
            >
              Simdi degil
            </button>
          </div>
        ) : null}

        {showPushControls ? (
          <div className="mt-4 flex flex-wrap gap-3">
            {!isSubscribed ? (
              <button
                type="button"
                onClick={async () => {
                  await subscribe();
                }}
                disabled={isPushBusy || pushPermission === "denied"}
                className="rounded-full bg-emerald-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {pushPermission === "denied"
                  ? "Bildirimler engelli"
                  : isPushBusy
                    ? "Etkinlestiriliyor..."
                    : "Bildirimleri ac"}
              </button>
            ) : isPushTestEnabled ? (
              <button
                type="button"
                onClick={async () => {
                  await sendTestNotification();
                }}
                disabled={isPushBusy}
                className="rounded-full bg-emerald-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {isPushBusy ? "Gonderiliyor..." : "Test bildirimi gonder"}
              </button>
            ) : null}
          </div>
        ) : null}
      </div>
    </div>
  );
}
