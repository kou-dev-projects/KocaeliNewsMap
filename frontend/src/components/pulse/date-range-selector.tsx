"use client"

import { AnimatePresence, motion } from "framer-motion"
import { CalendarDays, ChevronDown, RotateCcw } from "lucide-react"
import { useId, useMemo, useState } from "react"

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
  const dateFromInputId = useId()
  const dateToInputId = useId()

  const triggerLabel = useMemo(() => formatLabel(dateFrom, dateTo), [dateFrom, dateTo])

  return (
    <div className="relative w-full">
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
              className="absolute bottom-[calc(100%-1px)] left-0 z-50 w-full overflow-hidden rounded-t-2xl border border-b-0 border-border/70 glass"
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.24, ease: "easeOut" }}
            >
              <div className="space-y-3 p-3">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <p className="text-sm font-semibold text-foreground">Tarih Aralığı</p>
                    <p className="text-xs text-muted-foreground">Varsayılan görünüm son 3 gündür.</p>
                  </div>

                  <button
                    type="button"
                    onClick={onResetToDefault}
                    className="inline-flex h-8 items-center gap-1.5 rounded-full border border-border/70 bg-secondary/80 px-3 text-[11px] font-semibold text-foreground transition hover:bg-secondary"
                  >
                    <RotateCcw className="h-3.5 w-3.5" />
                    Son 3 Gün
                  </button>
                </div>

                <div className="space-y-2">
                  <label
                    htmlFor={dateFromInputId}
                    className="block text-[11px] font-semibold uppercase tracking-[0.18em] text-muted-foreground"
                  >
                    Başlangıç
                  </label>
                  <input
                    id={dateFromInputId}
                    type="date"
                    value={dateFrom}
                    onChange={(event) => onDateFromChange(event.target.value)}
                    aria-label="Başlangıç tarihi"
                    title="Başlangıç tarihi"
                    className="h-10 w-full rounded-xl border border-border/70 bg-card/92 px-3 text-sm text-foreground outline-none transition focus:border-primary/50 focus:ring-2 focus:ring-primary/20"
                  />
                </div>

                <div className="space-y-2">
                  <label
                    htmlFor={dateToInputId}
                    className="block text-[11px] font-semibold uppercase tracking-[0.18em] text-muted-foreground"
                  >
                    Bitiş
                  </label>
                  <input
                    id={dateToInputId}
                    type="date"
                    value={dateTo}
                    onChange={(event) => onDateToChange(event.target.value)}
                    aria-label="Bitiş tarihi"
                    title="Bitiş tarihi"
                    className="h-10 w-full rounded-xl border border-border/70 bg-card/92 px-3 text-sm text-foreground outline-none transition focus:border-primary/50 focus:ring-2 focus:ring-primary/20"
                  />
                </div>
              </div>
            </motion.div>
          </>
        ) : null}
      </AnimatePresence>

      <button
        type="button"
        onClick={() => setIsOpen((value) => !value)}
        className={cn(
          "relative z-[60] flex h-[58px] w-full items-center justify-between gap-3 border border-border/70 glass px-4 text-left transition-colors",
          isOpen ? "rounded-b-2xl rounded-t-none border-t-0" : "rounded-2xl hover:bg-card/92",
        )}
      >
        <div className="flex min-w-0 items-center gap-3">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-primary/12 text-primary">
            <CalendarDays className="h-4 w-4" />
          </div>
          <div className="min-w-0">
            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
              Tarih
            </p>
            <p className="truncate text-sm font-semibold text-foreground">{triggerLabel}</p>
          </div>
        </div>

        <motion.span
          animate={{ rotate: isOpen ? 180 : 0 }}
          transition={{ duration: 0.2 }}
          className="shrink-0 text-muted-foreground"
        >
          <ChevronDown className="h-5 w-5" />
        </motion.span>
      </button>
    </div>
  )
}
