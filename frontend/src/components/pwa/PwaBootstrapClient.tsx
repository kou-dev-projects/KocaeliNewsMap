"use client";

import { useEffect, useState } from "react";

import { PwaBootstrap } from "@/components/pwa/PwaBootstrap";

export function PwaBootstrapClient() {
  const [isMounted, setIsMounted] = useState(false);

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      setIsMounted(true);
    }, 0);

    return () => {
      window.clearTimeout(timeoutId);
    };
  }, []);

  if (!isMounted) {
    return null;
  }

  return <PwaBootstrap />;
}
