"use client"

import { motion, AnimatePresence } from "framer-motion"
import { cn } from "@/lib/utils"
import { Terminal, CheckCircle2, AlertCircle, Loader2, Database, Globe } from "lucide-react"
import { useRef, useEffect } from "react"

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
      className="glass rounded-xl border border-border/50 overflow-hidden"
      initial={{ opacity: 0, height: 0 }}
      animate={{
        opacity: 1,
        height: isExpanded ? "auto" : 48,
      }}
      transition={{ type: "spring", stiffness: 200, damping: 25 }}
    >
      <div className="flex items-center gap-2 px-4 py-2 border-b border-border/50 bg-secondary/30">
        <motion.div
          animate={{ rotate: [0, 360] }}
          transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
        >
          <Terminal className="w-4 h-4 text-primary" />
        </motion.div>
        <span className="text-sm font-medium">Canli Tarama Gunlugu</span>
        <motion.div
          className="ml-auto flex items-center gap-1.5"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
        >
          <Database className="w-3 h-3 text-muted-foreground" />
          <span className="text-xs text-muted-foreground">{logs.length} kayit</span>
        </motion.div>
      </div>

      <AnimatePresence>
        {isExpanded && (
          <motion.div
            ref={scrollRef}
            className="max-h-48 overflow-y-auto p-2 space-y-1 font-mono text-xs"
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
                    className={cn(
                      "flex items-start gap-2 px-2 py-1.5 rounded-md",
                      config.bg,
                    )}
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
                      <Icon className={cn("w-3.5 h-3.5 mt-0.5 shrink-0", config.color)} />
                    </motion.div>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-muted-foreground">
                          {log.timestamp.toLocaleTimeString("tr-TR")}
                        </span>
                        {log.source && (
                          <span className="px-1.5 py-0.5 bg-secondary rounded text-[10px] uppercase tracking-wide">
                            {log.source}
                          </span>
                        )}
                      </div>
                      <p className={cn("text-foreground break-words", config.color)}>
                        {log.message}
                      </p>
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
                className="w-1.5 h-1.5 rounded-full bg-primary"
                animate={{ scale: [1, 1.5, 1] }}
                transition={{ duration: 0.6, repeat: Infinity, delay: 0 }}
              />
              <motion.span
                className="w-1.5 h-1.5 rounded-full bg-primary"
                animate={{ scale: [1, 1.5, 1] }}
                transition={{ duration: 0.6, repeat: Infinity, delay: 0.2 }}
              />
              <motion.span
                className="w-1.5 h-1.5 rounded-full bg-primary"
                animate={{ scale: [1, 1.5, 1] }}
                transition={{ duration: 0.6, repeat: Infinity, delay: 0.4 }}
              />
              <span className="text-muted-foreground ml-1">Dinleniyor...</span>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}
