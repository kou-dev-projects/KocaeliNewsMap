'use client'

import type { ReactNode } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { RefreshCw, X } from 'lucide-react'

interface EnhancedSidebarProps {
  isOpen: boolean
  onClose: () => void
  title: string
  subtitle?: string
  onRefresh?: () => void
  refreshDisabled?: boolean
  isRefreshing?: boolean
  children: ReactNode
}

export function EnhancedSidebar({
  isOpen,
  onClose,
  title,
  subtitle,
  onRefresh,
  refreshDisabled = false,
  isRefreshing = false,
  children,
}: EnhancedSidebarProps) {
  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 z-40 bg-background/60 backdrop-blur-sm lg:hidden"
          />

          <motion.aside
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', stiffness: 300, damping: 30 }}
            className="fixed right-0 top-0 bottom-0 z-50 flex w-full max-w-md flex-col border-l border-border glass-strong shadow-2xl"
          >
            <div className="border-b border-border bg-card/70 px-5 py-4 backdrop-blur-sm">
              <div className="mb-3 flex items-start justify-between gap-3">
                <div>
                  <h2 className="text-xl font-bold text-foreground">{title}</h2>
                  {subtitle ? <p className="mt-0.5 text-xs text-muted-foreground">{subtitle}</p> : null}
                </div>

                <div className="flex items-center gap-2">
                  {onRefresh ? (
                    <motion.button
                      type="button"
                      onClick={onRefresh}
                      disabled={refreshDisabled}
                      animate={{ rotate: isRefreshing ? 360 : 0 }}
                      transition={{ duration: 0.55 }}
                      className="rounded-xl bg-secondary/60 p-2.5 transition-colors hover:bg-secondary disabled:cursor-not-allowed disabled:opacity-55"
                    >
                      <RefreshCw className="h-4 w-4" />
                    </motion.button>
                  ) : null}

                  <button
                    type="button"
                    onClick={onClose}
                    className="rounded-xl bg-secondary/60 p-2.5 transition-colors hover:bg-secondary"
                    aria-label="Kontrol panelini kapat"
                  >
                    <X className="h-4 w-4" />
                  </button>
                </div>
              </div>
            </div>

            <div className="flex-1 overflow-y-auto px-4 py-4">{children}</div>
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  )
}
