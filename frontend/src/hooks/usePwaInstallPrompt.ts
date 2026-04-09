"use client";

import { useEffect, useMemo, useState } from "react";

type InstallPromptOutcome = "accepted" | "dismissed" | "unavailable";

type BeforeInstallPromptEvent = Event & {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed"; platform: string }>;
};

const DISMISS_STORAGE_KEY = "pulse.pwa.install.dismissed";

export function usePwaInstallPrompt() {
  const [deferredPrompt, setDeferredPrompt] =
    useState<BeforeInstallPromptEvent | null>(null);
  const [isStandalone, setIsStandalone] = useState(false);
  const [isDismissed, setIsDismissed] = useState(() => {
    if (typeof window === "undefined") {
      return false;
    }

    return window.sessionStorage.getItem(DISMISS_STORAGE_KEY) === "true";
  });

  useEffect(() => {
    const mediaQuery = window.matchMedia("(display-mode: standalone)");
    const updateStandalone = () => {
      const iosStandalone =
        (window.navigator as Navigator & { standalone?: boolean }).standalone ===
        true;
      setIsStandalone(mediaQuery.matches || iosStandalone);
    };

    updateStandalone();
    const onBeforeInstallPrompt = (event: Event) => {
      event.preventDefault();
      setDeferredPrompt(event as BeforeInstallPromptEvent);
    };

    const onInstalled = () => {
      window.sessionStorage.removeItem(DISMISS_STORAGE_KEY);
      setDeferredPrompt(null);
      setIsDismissed(false);
      updateStandalone();
    };

    mediaQuery.addEventListener("change", updateStandalone);
    window.addEventListener(
      "beforeinstallprompt",
      onBeforeInstallPrompt as EventListener,
    );
    window.addEventListener("appinstalled", onInstalled);

    return () => {
      mediaQuery.removeEventListener("change", updateStandalone);
      window.removeEventListener(
        "beforeinstallprompt",
        onBeforeInstallPrompt as EventListener,
      );
      window.removeEventListener("appinstalled", onInstalled);
    };
  }, []);

  const canPrompt = useMemo(
    () => Boolean(deferredPrompt) && !isStandalone && !isDismissed,
    [deferredPrompt, isStandalone, isDismissed],
  );

  async function promptInstall(): Promise<InstallPromptOutcome> {
    if (!deferredPrompt) {
      return "unavailable";
    }

    await deferredPrompt.prompt();
    const result = await deferredPrompt.userChoice;
    setDeferredPrompt(null);

    if (result.outcome === "dismissed") {
      dismissPrompt();
    }

    return result.outcome;
  }

  function dismissPrompt(): void {
    window.sessionStorage.setItem(DISMISS_STORAGE_KEY, "true");
    setIsDismissed(true);
  }

  return {
    canPrompt,
    isDismissed,
    isStandalone,
    promptInstall,
    dismissPrompt,
  };
}
