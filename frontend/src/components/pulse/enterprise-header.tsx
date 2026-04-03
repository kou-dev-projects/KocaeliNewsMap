"use client"

import { motion } from "framer-motion"
import { Filter, Menu, Moon, Sun, X, Zap } from "lucide-react"
import { useTheme } from "next-themes"
import { useSyncExternalStore } from "react"

interface EnterpriseHeaderProps {
  onMenuToggle?: () => void
  isMenuOpen?: boolean
}

export function EnterpriseHeader({
  onMenuToggle,
  isMenuOpen,
}: EnterpriseHeaderProps) {
  const { resolvedTheme, setTheme } = useTheme()
  const mounted = useSyncExternalStore(
    () => () => {},
    () => true,
    () => false,
  )

  const currentTheme = mounted && resolvedTheme === "dark" ? "dark" : "light"

  return (
    <header className="absolute inset-x-0 top-0 z-30">
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
                  Enterprise
                </span>
              </div>
              <p className="mt-0.5 text-xs tracking-wide text-muted-foreground">
                Kocaeli Yerel Haber İzleme Sistemi
              </p>
            </div>
          </motion.div>

          <div className="hidden flex-1 lg:block" />

          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.2 }}
            className="flex items-center gap-2"
          >
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
    </header>
  )
}
