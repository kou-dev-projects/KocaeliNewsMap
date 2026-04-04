"use client";

import { useEffect, useMemo, useState } from "react";
import { Bell, Download, ShieldCheck, WifiOff, X } from "lucide-react";

import { useOnlineStatus } from "@/hooks/useOnlineStatus";
import { usePwaInstallPrompt } from "@/hooks/usePwaInstallPrompt";
import { useWebPushSubscription } from "@/hooks/useWebPushSubscription";

type BannerMode = "offline" | "install" | "push";

type BannerConfig = {
  mode: BannerMode;
  eyebrow: string;
  title: string;
  description: string;
  accentClass: string;
  icon: typeof Download;
};

export function PwaBootstrap() {
  const [isMounted, setIsMounted] = useState(false);
  const [hiddenBannerMode, setHiddenBannerMode] = useState<BannerMode | null>(null);
  const isOnline = useOnlineStatus();
  const shouldRegisterServiceWorker =
    process.env.NODE_ENV === "production" ||
    process.env.NEXT_PUBLIC_ENABLE_PWA_IN_DEV === "true";
  const { canPrompt, isStandalone, promptInstall, dismissPrompt } =
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

  const showPushControls =
    isOnline &&
    isPushEnabled &&
    isPushConfigured &&
    isPushSupported &&
    (pushPermission !== "granted" || isSubscribed);

  const banner = useMemo<BannerConfig | null>(() => {
    if (!isOnline) {
      return {
        mode: "offline",
        eyebrow: "Offline mode",
        title: "Bağlantı olmadan da devam",
        description:
          "Son görülen ekranlar ve önbellekteki veriler kullanılmaya devam eder.",
        accentClass:
          "border-amber-500/20 bg-amber-500/10 text-amber-700 dark:text-amber-300",
        icon: WifiOff,
      };
    }

    if (canPrompt && !isStandalone) {
      return {
        mode: "install",
        eyebrow: "PWA hazır",
        title: "PULSE'u ana ekrana ekleyin",
        description:
          "Uygulamayı tek dokunuşta açın, daha hızlı yükleyin ve sahada tarayıcı sekmesine bağlı kalmayın.",
        accentClass:
          "border-sky-500/20 bg-sky-500/10 text-sky-700 dark:text-sky-300",
        icon: Download,
      };
    }

    if (showPushControls) {
      return {
        mode: "push",
        eyebrow: "Bildirimler",
        title:
          pushPermission === "granted"
            ? isSubscribed
              ? "Bildirimler aktif"
              : "Bildirim aboneliğini tamamlayın"
            : "Tarama ve saha uyarılarını açın",
        description:
          pushPermission === "denied"
            ? "Bildirim izni tarayıcı ayarlarında engelli. Önce izin vermeniz gerekiyor."
            : pushPermission === "granted"
              ? isSubscribed
                ? isPushTestEnabled
                  ? "Test bildirimi gönderebilirsiniz."
                  : "Bildirimler teslim edilmeye hazır."
                : "İzin verildi. Teslimat için aboneliği tamamlayın."
              : "Scrape ve kritik haber akışını anlık almak için bildirimleri etkinleştirin.",
        accentClass:
          "border-emerald-500/20 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300",
        icon: isSubscribed ? ShieldCheck : Bell,
      };
    }

    return null;
  }, [canPrompt, isOnline, isPushTestEnabled, isStandalone, isSubscribed, pushPermission, showPushControls]);

  const isBannerHidden = Boolean(banner && hiddenBannerMode === banner.mode);

  if (!isMounted || !banner || isBannerHidden) {
    return null;
  }

  const BannerIcon = banner.icon;

  return (
    <div className="pointer-events-none fixed inset-x-4 bottom-24 z-50 flex justify-center md:inset-x-auto md:right-6 md:top-24 md:bottom-auto md:justify-end">
      <div className="pointer-events-auto w-full max-w-[380px] rounded-[26px] glass-strong p-4 text-foreground shadow-[0_24px_70px_rgba(15,23,42,0.22)]">
        <div className="flex items-start gap-3">
          <div
            className={[
              "flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl border",
              banner.accentClass,
            ].join(" ")}
          >
            <BannerIcon className="h-5 w-5" />
          </div>

          <div className="min-w-0 flex-1">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-muted-foreground">
                  {banner.eyebrow}
                </p>
                <h3 className="mt-1 text-base font-semibold text-foreground">
                  {banner.title}
                </h3>
              </div>

              <button
                type="button"
                onClick={() => {
                  if (banner.mode === "install") {
                    dismissPrompt();
                  }
                  setHiddenBannerMode(banner.mode);
                }}
                className="rounded-xl border border-border/70 bg-background/70 p-2 text-muted-foreground transition hover:bg-secondary hover:text-foreground"
                aria-label="PWA kartını kapat"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <p className="mt-2 text-sm leading-6 text-muted-foreground">
              {banner.description}
            </p>

            {banner.mode === "push" && pushMessage ? (
              <p className="mt-2 text-xs font-medium text-muted-foreground">
                {pushMessage}
              </p>
            ) : null}
          </div>
        </div>

        <div className="mt-4 flex flex-wrap gap-3">
          {banner.mode === "install" ? (
            <>
              <button
                type="button"
                onClick={async () => {
                  setIsPromptPending(true);
                  const outcome = await promptInstall();
                  setIsPromptPending(false);

                  if (outcome === "dismissed") {
                    setHiddenBannerMode("install");
                  }
                }}
                className="rounded-2xl bg-primary px-4 py-2.5 text-sm font-semibold text-primary-foreground transition hover:bg-primary/90"
              >
                {isPromptPending ? "Hazırlanıyor..." : "Ana ekrana ekle"}
              </button>
              <button
                type="button"
                onClick={() => {
                  dismissPrompt();
                  setHiddenBannerMode("install");
                }}
                className="rounded-2xl border border-border/70 bg-background/70 px-4 py-2.5 text-sm font-semibold text-foreground transition hover:bg-secondary"
              >
                Şimdi değil
              </button>
            </>
          ) : null}

          {banner.mode === "push" ? (
            <>
              {!isSubscribed ? (
                <button
                  type="button"
                  onClick={async () => {
                    await subscribe();
                  }}
                  disabled={isPushBusy || pushPermission === "denied"}
                  className="rounded-2xl bg-emerald-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {pushPermission === "denied"
                    ? "Bildirimler engelli"
                    : isPushBusy
                      ? "Etkinleştiriliyor..."
                      : "Bildirimleri aç"}
                </button>
              ) : isPushTestEnabled ? (
                <button
                  type="button"
                  onClick={async () => {
                    await sendTestNotification();
                  }}
                  disabled={isPushBusy}
                  className="rounded-2xl bg-emerald-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {isPushBusy ? "Gönderiliyor..." : "Test bildirimi gönder"}
                </button>
              ) : null}

              <button
                type="button"
                onClick={() => setHiddenBannerMode("push")}
                className="rounded-2xl border border-border/70 bg-background/70 px-4 py-2.5 text-sm font-semibold text-foreground transition hover:bg-secondary"
              >
                Kapat
              </button>
            </>
          ) : null}

          {banner.mode === "offline" ? (
            <button
              type="button"
              onClick={() => setHiddenBannerMode("offline")}
              className="rounded-2xl border border-border/70 bg-background/70 px-4 py-2.5 text-sm font-semibold text-foreground transition hover:bg-secondary"
            >
              Anladım
            </button>
          ) : null}
        </div>
      </div>
    </div>
  );
}
