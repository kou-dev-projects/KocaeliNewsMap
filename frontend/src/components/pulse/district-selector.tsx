"use client"

import { AnimatePresence, motion } from "framer-motion"
import { Check, ChevronDown, MapPin } from "lucide-react"
import { useState } from "react"

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

  const selectedNames = districts
    .filter((district) => selected.includes(district.id))
    .map((district) => district.name)
    .slice(0, 3)

  const triggerLabel =
    selected.length === 0
      ? "İlçe seçin"
      : selected.length === districts.length
        ? "Tüm ilçeler"
        : `${selectedNames.join(", ")}${selected.length > 3 ? ` +${selected.length - 3}` : ""}`

  return (
    <div className="relative">
      <motion.button
        type="button"
        className={cn(
          "flex h-[42px] min-w-[196px] items-center gap-2 rounded-xl px-4",
          "bg-transparent text-sm font-medium leading-none transition-colors hover:bg-secondary/60",
        )}
        onClick={() => setIsOpen((value) => !value)}
        whileHover={{ scale: 1.02 }}
        whileTap={{ scale: 0.98 }}
      >
        <MapPin className="h-4 w-4 shrink-0 text-primary" />
        <span className="max-w-[180px] truncate text-sm font-medium leading-none text-foreground">
          {triggerLabel}
        </span>
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
              className="absolute bottom-full left-0 z-50 mb-2 max-h-80 w-72 overflow-y-auto rounded-xl border border-border shadow-xl glass"
              initial={{ opacity: 0, y: 10, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 10, scale: 0.95 }}
              transition={{ type: "spring", stiffness: 300, damping: 25 }}
            >
              <div className="sticky top-0 border-b border-border bg-card/90 p-3 backdrop-blur-sm">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">Kocaeli İlçeleri</span>
                  <button
                    type="button"
                    className="text-xs text-primary hover:underline"
                    onClick={selectAll}
                  >
                    Tümünü seç
                  </button>
                </div>
              </div>

              <div className="p-2">
                {districts.map((district, index) => {
                  const isSelected = selected.includes(district.id)

                  return (
                    <motion.button
                      key={district.id}
                      type="button"
                      className={cn(
                        "flex w-full items-center justify-between rounded-lg px-3 py-2 text-left transition-colors",
                        isSelected ? "bg-primary/10 text-primary" : "hover:bg-secondary",
                      )}
                      onClick={() => toggleDistrict(district.id)}
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: index * 0.02 }}
                      whileHover={{ x: 4 }}
                    >
                      <div className="flex items-center gap-3">
                        <motion.div
                          className={cn(
                            "flex h-5 w-5 items-center justify-center rounded-md border-2",
                            isSelected ? "border-primary bg-primary" : "border-border",
                          )}
                          animate={{ scale: isSelected ? [1, 1.2, 1] : 1 }}
                          transition={{ duration: 0.2 }}
                        >
                          <AnimatePresence>
                            {isSelected ? (
                              <motion.div initial={{ scale: 0 }} animate={{ scale: 1 }} exit={{ scale: 0 }}>
                                <Check className="h-3 w-3 text-primary-foreground" />
                              </motion.div>
                            ) : null}
                          </AnimatePresence>
                        </motion.div>
                        <span className="text-sm font-medium">{district.name}</span>
                      </div>

                      <motion.span
                        className={cn(
                          "rounded-full px-2 py-0.5 text-xs",
                          isSelected ? "bg-primary text-primary-foreground" : "bg-secondary text-secondary-foreground",
                        )}
                        key={district.newsCount}
                        initial={{ scale: 0.8 }}
                        animate={{ scale: 1 }}
                      >
                        {district.newsCount}
                      </motion.span>
                    </motion.button>
                  )
                })}
              </div>

              <div className="sticky bottom-0 border-t border-border bg-card/90 p-3 backdrop-blur-sm">
                <div className="flex items-center justify-between text-xs text-muted-foreground">
                  <span>{selected.length} ilçe aktif</span>
                  <span>
                    {districts
                      .filter((district) => selected.includes(district.id))
                      .reduce((sum, district) => sum + district.newsCount, 0)}{" "}
                    haber
                  </span>
                </div>
              </div>
            </motion.div>
          </>
        ) : null}
      </AnimatePresence>
    </div>
  )
}
