"use client";

import { AnimatePresence, motion } from "framer-motion";
import {
  Activity,
  Database,
  Filter,
  Globe,
  Menu,
  Moon,
  Search,
  Sun,
  Wifi,
  X,
  Zap,
} from "lucide-react";
import { useTheme } from "next-themes";
import { useEffect, useRef, useSyncExternalStore, useState } from "react";

interface EnterpriseHeaderProps {
  searchQuery: string;
  onSearchChange?: (query: string) => void;
  onMenuToggle?: () => void;
  isMenuOpen?: boolean;
  totalNews: number;
  liveCount: number;
}

function isEditableTarget(target: EventTarget | null) {
  if (!(target instanceof HTMLElement)) {
    return false;
  }

  if (target.isContentEditable) {
    return true;
  }

  const tagName = target.tagName.toLowerCase();
  return tagName === "input" || tagName === "textarea" || tagName === "select";
}

export function EnterpriseHeader({
  searchQuery,
  onSearchChange,
  onMenuToggle,
  isMenuOpen,
  totalNews,
  liveCount,
}: EnterpriseHeaderProps) {
  const { resolvedTheme, setTheme } = useTheme();
  const mounted = useSyncExternalStore(
    () => () => {},
    () => true,
    () => false,
  );
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [currentTime, setCurrentTime] = useState(new Date());
  const desktopSearchRef = useRef<HTMLInputElement | null>(null);
  const mobileSearchRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    const timer = window.setInterval(() => {
      setCurrentTime(new Date());
    }, 1_000);

    return () => {
      window.clearInterval(timer);
    };
  }, []);

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (
        event.key !== "/" ||
        event.ctrlKey ||
        event.metaKey ||
        event.altKey ||
        isEditableTarget(event.target)
      ) {
        return;
      }

      event.preventDefault();
      const targetInput = window.innerWidth >= 1024 ? desktopSearchRef.current : mobileSearchRef.current;
      if (window.innerWidth < 1024) {
        setIsSearchOpen(true);
      }
      targetInput?.focus();
      targetInput?.select();
    };

    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setIsSearchOpen(false);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    window.addEventListener("keydown", handleEscape);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
      window.removeEventListener("keydown", handleEscape);
    };
  }, []);

  const currentTheme = mounted && resolvedTheme === "dark" ? "dark" : "light";

  return (
    <header className="absolute inset-x-0 top-0 z-30">
      <motion.div
        initial={{ opacity: 0, y: -16 }}
        animate={{ opacity: 1, y: 0 }}
        className="border-b border-border bg-card/82 px-4 py-1.5 text-xs backdrop-blur-sm"
      >
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <motion.div
                className="h-2 w-2 rounded-full bg-emerald-500"
                animate={{ scale: [1, 1.2, 1], opacity: [1, 0.6, 1] }}
                transition={{ duration: 1, repeat: Infinity }}
              />
              <span className="font-mono text-muted-foreground">SİSTEM AKTİF</span>
            </div>

            <div className="hidden items-center gap-2 text-muted-foreground md:flex">
              <Database className="h-3 w-3" />
              <span className="font-mono">{totalNews.toLocaleString("tr-TR")} KAYIT</span>
            </div>

            <div className="hidden items-center gap-2 text-muted-foreground md:flex">
              <Wifi className="h-3 w-3 text-emerald-500" />
              <span className="font-mono">CANLI: {liveCount.toLocaleString("tr-TR")}</span>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <div className="hidden items-center gap-2 text-muted-foreground sm:flex">
              <Globe className="h-3 w-3" />
              <span className="font-mono">TR-41 KOCAELİ</span>
            </div>

            <div
              className="flex items-center gap-1 font-mono text-foreground"
              suppressHydrationWarning
            >
              <span suppressHydrationWarning>
                {currentTime.toLocaleDateString("tr-TR", {
                  day: "2-digit",
                  month: "short",
                  year: "numeric",
                })}
              </span>
              <span className="text-muted-foreground">|</span>
              <span className="font-semibold text-primary" suppressHydrationWarning>
                {currentTime.toLocaleTimeString("tr-TR")}
              </span>
            </div>
          </div>
        </div>
      </motion.div>

      <div className="mx-4 mt-3 overflow-hidden rounded-2xl glass">
        <div className="flex items-center justify-between gap-4 px-5 py-4">
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            className="flex items-center gap-4"
          >
            <div className="relative">
              <motion.div
                className="absolute inset-0 rounded-xl bg-primary/20"
                animate={{ scale: [1, 1.3, 1], opacity: [0.45, 0, 0.45] }}
                transition={{ duration: 2, repeat: Infinity }}
              />
              <motion.div
                className="absolute inset-0 rounded-xl bg-primary/20"
                animate={{ scale: [1, 1.3, 1], opacity: [0.45, 0, 0.45] }}
                transition={{ duration: 2, repeat: Infinity, delay: 0.5 }}
              />
              <div className="relative flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-primary to-primary/80 shadow-lg">
                <motion.div
                  animate={{ rotate: 360 }}
                  transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
                  className="absolute inset-1 rounded-lg border border-primary-foreground/20"
                />
                <span className="text-xl font-bold tracking-tighter text-primary-foreground">P</span>
              </div>
              <motion.span
                className="absolute -right-1 -top-1 flex h-4 w-4 items-center justify-center rounded-full border-2 border-background bg-emerald-500"
                animate={{ scale: [1, 1.08, 1] }}
                transition={{ duration: 1, repeat: Infinity }}
              >
                <Zap className="h-2 w-2 text-white" />
              </motion.span>
            </div>

            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xl font-bold tracking-tight text-foreground">PULSE</h1>
                <span className="rounded-md bg-primary/10 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-primary">
                  Sistem
                </span>
              </div>
              <p className="mt-0.5 text-xs tracking-wide text-muted-foreground">
                Kocaeli Yerel Haber İzleme Sistemi
              </p>
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="hidden max-w-2xl flex-1 items-center gap-4 lg:flex"
          >
            <div className="relative flex-1">
              <Search className="absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <input
                ref={desktopSearchRef}
                type="search"
                placeholder="Haber, konum veya kaynak ara..."
                value={searchQuery}
                onChange={(event) => onSearchChange?.(event.target.value)}
                className="w-full rounded-xl border border-border bg-secondary/50 py-3 pl-11 pr-14 text-sm transition-all placeholder:text-muted-foreground focus:border-primary/50 focus:outline-none focus:ring-2 focus:ring-primary/30"
              />
              <div className="absolute right-3 top-1/2 flex -translate-y-1/2 items-center gap-1">
                <kbd className="rounded bg-muted px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground">
                  /
                </kbd>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2 rounded-lg border border-emerald-500/20 bg-emerald-500/10 px-3 py-2">
                <Activity className="h-4 w-4 text-emerald-500" />
                <span className="text-sm font-semibold text-emerald-600 dark:text-emerald-400">
                  {liveCount.toLocaleString("tr-TR")}
                </span>
                <span className="text-xs text-emerald-600/70 dark:text-emerald-400/70">Canlı</span>
              </div>

              <div className="flex items-center gap-2 rounded-lg border border-primary/20 bg-primary/10 px-3 py-2">
                <Database className="h-4 w-4 text-primary" />
                <span className="text-sm font-semibold text-primary">
                  {totalNews.toLocaleString("tr-TR")}
                </span>
                <span className="text-xs text-primary/70">Toplam</span>
              </div>
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.2 }}
            className="flex items-center gap-2"
          >
            <button
              type="button"
              onClick={() => setIsSearchOpen((current) => !current)}
              className="rounded-xl border border-border/50 bg-secondary/50 p-2.5 transition-colors hover:bg-secondary lg:hidden"
              aria-label={isSearchOpen ? "Aramayı kapat" : "Aramayı aç"}
            >
              {isSearchOpen ? (
                <X className="h-5 w-5 text-foreground" />
              ) : (
                <Search className="h-5 w-5 text-foreground" />
              )}
            </button>

            <motion.button
              type="button"
              whileHover={{ scale: 1.04 }}
              whileTap={{ scale: 0.96 }}
              onClick={() => setTheme(currentTheme === "dark" ? "light" : "dark")}
              className="rounded-xl border border-border/50 bg-secondary/50 p-2.5 transition-colors hover:bg-secondary"
              aria-label={currentTheme === "dark" ? "Açık temaya geç" : "Koyu temaya geç"}
            >
              {currentTheme === "dark" ? (
                <Moon className="h-5 w-5 text-foreground" />
              ) : (
                <Sun className="h-5 w-5 text-foreground" />
              )}
            </motion.button>

            <button
              type="button"
              onClick={onMenuToggle}
              aria-label={isMenuOpen ? "Kontrol panelini kapat" : "Kontrol panelini aç"}
              data-testid="control-panel-toggle"
              className="rounded-xl bg-primary p-2.5 transition-colors hover:bg-primary/90"
            >
              {isMenuOpen ? (
                <X className="h-5 w-5 text-primary-foreground" />
              ) : (
                <>
                  <Filter className="hidden h-5 w-5 text-primary-foreground sm:block" />
                  <Menu className="h-5 w-5 text-primary-foreground sm:hidden" />
                </>
              )}
            </button>
          </motion.div>
        </div>
      </div>

      <AnimatePresence>
        {isSearchOpen ? (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="mx-4 overflow-hidden lg:hidden"
          >
            <div className="pt-2">
              <div className="rounded-xl glass">
                <div className="relative">
                  <Search className="absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                  <input
                    ref={mobileSearchRef}
                    type="search"
                    placeholder="Haber veya konum ara..."
                    value={searchQuery}
                    onChange={(event) => onSearchChange?.(event.target.value)}
                    className="w-full rounded-xl bg-transparent py-3.5 pl-11 pr-4 text-sm placeholder:text-muted-foreground focus:outline-none"
                  />
                </div>
              </div>
            </div>
          </motion.div>
        ) : null}
      </AnimatePresence>
    </header>
  );
}
