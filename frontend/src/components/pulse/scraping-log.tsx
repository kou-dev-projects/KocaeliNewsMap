"use client"

import { AnimatePresence, motion } from "framer-motion"
import { AlertCircle, CheckCircle2, Database, Globe, Loader2, Terminal } from "lucide-react"
import { useEffect, useRef } from "react"

import { cn } from "@/lib/utils"

export interface PulseLogEntry {
  id: string
  type: "info" | "success" | "error" | "warning"
  message: string
  source?: string
  timestamp: Date
}

interface ScrapingLogProps {
  logs: PulseLogEntry[]
  isExpanded?: boolean
}

const typeConfig: Record<string, { icon: typeof Globe; color: string; bg: string; animate?: boolean }> = {
  info: {
    icon: Globe,
    color: "text-blue-500",
    bg: "bg-blue-500/10",
    animate: false,
  },
  success: {
    icon: CheckCircle2,
    color: "text-emerald-500",
    bg: "bg-emerald-500/10",
    animate: false,
  },
  error: {
    icon: AlertCircle,
    color: "text-red-500",
    bg: "bg-red-500/10",
    animate: false,
  },
  warning: {
    icon: Loader2,
    color: "text-amber-500",
    bg: "bg-amber-500/10",
    animate: true,
  },
}

export function ScrapingLog({ logs, isExpanded = true }: ScrapingLogProps) {
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [logs])

  return (
    <motion.div
      className="glass overflow-hidden rounded-xl border border-border/50"
      initial={{ opacity: 0, height: 0 }}
      animate={{
        opacity: 1,
        height: isExpanded ? "auto" : 48,
      }}
      transition={{ type: "spring", stiffness: 200, damping: 25 }}
    >
      <div className="flex items-center gap-2 border-b border-border/50 bg-secondary/30 px-4 py-2">
        <motion.div
          animate={{ rotate: [0, 360] }}
          transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
        >
          <Terminal className="h-4 w-4 text-primary" />
        </motion.div>
        <span className="text-sm font-medium">Canlı Tarama Günlüğü</span>
        <motion.div
          className="ml-auto flex items-center gap-1.5"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
        >
          <Database className="h-3 w-3 text-muted-foreground" />
          <span className="text-xs text-muted-foreground">{logs.length} kayıt</span>
        </motion.div>
      </div>

      <AnimatePresence>
        {isExpanded ? (
          <motion.div
            ref={scrollRef}
            className="max-h-48 space-y-1 overflow-y-auto p-2 font-mono text-xs"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <AnimatePresence mode="popLayout">
              {logs.map((log, index) => {
                const config = typeConfig[log.type]
                const Icon = config.icon

                return (
                  <motion.div
                    key={log.id}
                    className={cn("flex items-start gap-2 rounded-md px-2 py-1.5", config.bg)}
                    initial={{ opacity: 0, x: -20, height: 0 }}
                    animate={{ opacity: 1, x: 0, height: "auto" }}
                    exit={{ opacity: 0, x: 20, height: 0 }}
                    transition={{
                      type: "spring",
                      stiffness: 300,
                      damping: 20,
                      delay: index * 0.02,
                    }}
                    layout
                  >
                    <motion.div
                      animate={config.animate ? { rotate: 360 } : {}}
                      transition={
                        config.animate
                          ? { duration: 1, repeat: Infinity, ease: "linear" }
                          : {}
                      }
                    >
                      <Icon className={cn("mt-0.5 h-3.5 w-3.5 shrink-0", config.color)} />
                    </motion.div>

                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <span className="text-muted-foreground">
                          {log.timestamp.toLocaleTimeString("tr-TR")}
                        </span>
                        {log.source ? (
                          <span className="rounded bg-secondary px-1.5 py-0.5 text-[10px] uppercase tracking-wide">
                            {log.source}
                          </span>
                        ) : null}
                      </div>
                      <p className={cn("break-words text-foreground", config.color)}>{log.message}</p>
                    </div>
                  </motion.div>
                )
              })}
            </AnimatePresence>

            <motion.div
              className="flex items-center gap-1 px-2 py-1"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
            >
              <motion.span
                className="h-1.5 w-1.5 rounded-full bg-primary"
                animate={{ scale: [1, 1.5, 1] }}
                transition={{ duration: 0.6, repeat: Infinity, delay: 0 }}
              />
              <motion.span
                className="h-1.5 w-1.5 rounded-full bg-primary"
                animate={{ scale: [1, 1.5, 1] }}
                transition={{ duration: 0.6, repeat: Infinity, delay: 0.2 }}
              />
              <motion.span
                className="h-1.5 w-1.5 rounded-full bg-primary"
                animate={{ scale: [1, 1.5, 1] }}
                transition={{ duration: 0.6, repeat: Infinity, delay: 0.4 }}
              />
              <span className="ml-1 text-muted-foreground">Dinleniyor...</span>
            </motion.div>
          </motion.div>
        ) : null}
      </AnimatePresence>
    </motion.div>
  )
}
