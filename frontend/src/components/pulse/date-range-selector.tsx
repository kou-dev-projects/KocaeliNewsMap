"use client"

import { AnimatePresence, motion } from "framer-motion"
import { CalendarDays, ChevronDown, RotateCcw } from "lucide-react"
import { useMemo, useState } from "react"

import { cn } from "@/lib/utils"

interface DateRangeSelectorProps {
  dateFrom: string
  dateTo: string
  onDateFromChange: (value: string) => void
  onDateToChange: (value: string) => void
  onResetToDefault: () => void
}

function formatLabel(dateFrom: string, dateTo: string) {
  if (!dateFrom || !dateTo) {
    return "Tarih seçin"
  }

  const formatter = new Intl.DateTimeFormat("tr-TR", {
    day: "2-digit",
    month: "short",
  })

  const from = new Date(`${dateFrom}T00:00:00`)
  const to = new Date(`${dateTo}T00:00:00`)

  if (Number.isNaN(from.getTime()) || Number.isNaN(to.getTime())) {
    return "Tarih seçin"
  }

  return `${formatter.format(from)} - ${formatter.format(to)}`
}

export function DateRangeSelector({
  dateFrom,
  dateTo,
  onDateFromChange,
  onDateToChange,
  onResetToDefault,
}: DateRangeSelectorProps) {
  const [isOpen, setIsOpen] = useState(false)

  const triggerLabel = useMemo(() => formatLabel(dateFrom, dateTo), [dateFrom, dateTo])

  return (
    <div className="relative">
      <motion.button
        type="button"
        className={cn(
          "flex h-[42px] min-w-[218px] items-center gap-2 rounded-xl px-4",
          "bg-transparent text-sm font-medium leading-none transition-colors hover:bg-secondary/60",
        )}
        onClick={() => setIsOpen((value) => !value)}
        whileHover={{ scale: 1.02 }}
        whileTap={{ scale: 0.98 }}
      >
        <CalendarDays className="h-4 w-4 shrink-0 text-primary" />
        <span className="truncate text-sm font-medium leading-none text-foreground">{triggerLabel}</span>
        <motion.div animate={{ rotate: isOpen ? 180 : 0 }} transition={{ duration: 0.2 }}>
          <ChevronDown className="h-4 w-4" />
        </motion.div>
      </motion.button>

      <AnimatePresence>
        {isOpen ? (
          <>
            <motion.div
              className="fixed inset-0 z-40"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setIsOpen(false)}
            />

            <motion.div
              className="absolute bottom-full left-0 z-50 mb-2 w-[320px] rounded-xl border border-border shadow-xl glass"
              initial={{ opacity: 0, y: 10, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 10, scale: 0.95 }}
              transition={{ type: "spring", stiffness: 300, damping: 25 }}
            >
              <div className="border-b border-border bg-card/90 p-3 backdrop-blur-sm">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-foreground">Tarih Aralığı</p>
                    <p className="mt-1 text-xs text-muted-foreground">Varsayılan görünüm son 3 gündür.</p>
                  </div>

                  <button
                    type="button"
                    className="inline-flex items-center gap-1 rounded-lg bg-secondary/70 px-2.5 py-1.5 text-xs font-medium text-foreground transition hover:bg-secondary"
                    onClick={onResetToDefault}
                  >
                    <RotateCcw className="h-3.5 w-3.5" />
                    Son 3 Gün
                  </button>
                </div>
              </div>

              <div className="grid gap-3 p-3">
                <div>
                  <label htmlFor="date-from" className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                    Başlangıç
                  </label>
                  <input
                    id="date-from"
                    type="date"
                    value={dateFrom}
                    onChange={(event) => onDateFromChange(event.target.value)}
                    className="mt-2 w-full rounded-lg border border-border bg-background/80 px-3 py-2 text-sm text-foreground outline-none transition focus:border-primary/50 focus:ring-2 focus:ring-primary/20"
                  />
                </div>

                <div>
                  <label htmlFor="date-to" className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                    Bitiş
                  </label>
                  <input
                    id="date-to"
                    type="date"
                    value={dateTo}
                    onChange={(event) => onDateToChange(event.target.value)}
                    className="mt-2 w-full rounded-lg border border-border bg-background/80 px-3 py-2 text-sm text-foreground outline-none transition focus:border-primary/50 focus:ring-2 focus:ring-primary/20"
                  />
                </div>
              </div>
            </motion.div>
          </>
        ) : null}
      </AnimatePresence>
    </div>
  )
}
