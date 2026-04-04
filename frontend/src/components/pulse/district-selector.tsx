"use client"

import { AnimatePresence, motion } from "framer-motion"
import { Check, ChevronDown, MapPin } from "lucide-react"
import { useMemo, useState } from "react"

import { cn } from "@/lib/utils"

export interface DistrictOption {
  id: string
  name: string
  newsCount: number
}

interface DistrictSelectorProps {
  districts: DistrictOption[]
  selected: string[]
  onChange: (districts: string[]) => void
}

export function DistrictSelector({ districts, selected, onChange }: DistrictSelectorProps) {
  const [isOpen, setIsOpen] = useState(false)

  const toggleDistrict = (id: string) => {
    if (selected.includes(id)) {
      if (selected.length === 1) {
        return
      }
      onChange(selected.filter((district) => district !== id))
      return
    }

    onChange([...selected, id])
  }

  const selectAll = () => {
    onChange(districts.map((district) => district.id))
  }

  const selectedNames = useMemo(
    () =>
      districts
        .filter((district) => selected.includes(district.id))
        .map((district) => district.name)
        .slice(0, 3),
    [districts, selected],
  )

  const selectedNewsCount = useMemo(
    () =>
      districts
        .filter((district) => selected.includes(district.id))
        .reduce((sum, district) => sum + district.newsCount, 0),
    [districts, selected],
  )

  const triggerLabel =
    selected.length === 0
      ? "İlçe seçin"
      : selected.length === districts.length
        ? "Tüm ilçeler"
        : `${selectedNames.join(", ")}${selected.length > 3 ? ` +${selected.length - 3}` : ""}`

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
                    <p className="text-sm font-semibold text-foreground">Kocaeli İlçeleri</p>
                    <p className="text-xs text-muted-foreground">Haritayı ilçe bazında daraltın.</p>
                  </div>

                  <button
                    type="button"
                    onClick={selectAll}
                    className="inline-flex h-8 items-center rounded-full border border-border/70 bg-secondary/80 px-3 text-[11px] font-semibold text-foreground transition hover:bg-secondary"
                  >
                    Tümünü seç
                  </button>
                </div>

                <div className="max-h-60 space-y-1 overflow-y-auto">
                  {districts.map((district) => {
                    const isSelected = selected.includes(district.id)

                    return (
                      <button
                        key={district.id}
                        type="button"
                        onClick={() => toggleDistrict(district.id)}
                        className={cn(
                          "flex w-full items-center justify-between rounded-xl px-3 py-2.5 text-left transition-colors",
                          isSelected ? "bg-primary/10 text-primary" : "hover:bg-secondary/60",
                        )}
                      >
                        <div className="flex min-w-0 items-center gap-3">
                          <span
                            className={cn(
                              "flex h-5 w-5 shrink-0 items-center justify-center rounded-md border-2 transition-colors",
                              isSelected ? "border-primary bg-primary" : "border-border bg-card/80",
                            )}
                          >
                            {isSelected ? <Check className="h-3 w-3 text-primary-foreground" /> : null}
                          </span>
                          <span className="truncate text-sm font-medium">{district.name}</span>
                        </div>

                        <span
                          className={cn(
                            "shrink-0 rounded-full px-2 py-0.5 text-xs font-medium",
                            isSelected
                              ? "bg-primary text-primary-foreground"
                              : "bg-secondary/90 text-secondary-foreground",
                          )}
                        >
                          {district.newsCount}
                        </span>
                      </button>
                    )
                  })}
                </div>

                <div className="flex items-center justify-between border-t border-border/60 pt-3 text-xs text-muted-foreground">
                  <span>{selected.length} ilçe aktif</span>
                  <span>{selectedNewsCount} haber</span>
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
            <MapPin className="h-4 w-4" />
          </div>
          <div className="min-w-0">
            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
              İlçe
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
