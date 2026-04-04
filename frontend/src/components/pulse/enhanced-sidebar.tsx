'use client'

import type { ReactNode } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { X } from 'lucide-react'

interface EnhancedSidebarProps {
  isOpen: boolean
  onClose: () => void
  title: string
  subtitle?: string
  children: ReactNode
}

export function EnhancedSidebar({
  isOpen,
  onClose,
  title,
  subtitle,
  children,
}: EnhancedSidebarProps) {
  return (
    <AnimatePresence>
      {isOpen ? (
        <>
          <button
            type="button"
            aria-label="Kontrol paneli arka planı"
            onClick={onClose}
            className="fixed inset-0 z-40 bg-transparent"
          />

          <motion.aside
            initial={{ opacity: 0, x: 28, scale: 0.98 }}
            animate={{ opacity: 1, x: 0, scale: 1 }}
            exit={{ opacity: 0, x: 20, scale: 0.98 }}
            transition={{ type: 'spring', stiffness: 280, damping: 28 }}
            className="fixed right-3 top-24 bottom-3 z-50 flex w-[min(25.5rem,calc(100vw-1rem))] max-w-[25.5rem] min-h-0 flex-col overflow-hidden rounded-[24px] border border-border/70 bg-background/92 shadow-[0_24px_80px_rgba(15,23,42,0.18)] backdrop-blur-xl"
          >
            <div className="border-b border-border/70 bg-background/85 px-5 py-4">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <h2 className="text-xl font-bold text-foreground">{title}</h2>
                  {subtitle ? (
                    <p className="mt-1 text-sm text-muted-foreground">{subtitle}</p>
                  ) : null}
                </div>

                <button
                  type="button"
                  onClick={onClose}
                  className="rounded-xl bg-secondary/70 p-2.5 transition-colors hover:bg-secondary"
                  aria-label="Kontrol panelini kapat"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
            </div>

            <div className="min-h-0 flex-1 overflow-y-auto p-4">
              {children}
            </div>
          </motion.aside>
        </>
      ) : null}
    </AnimatePresence>
  )
}
