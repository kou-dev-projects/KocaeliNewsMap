"use client"

import { motion, AnimatePresence } from "framer-motion"
import { cn } from "@/lib/utils"
import { MapPin, ChevronDown, Check } from "lucide-react"
import { useState } from "react"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

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
      onChange(selected.filter((d) => d !== id))
    } else {
      onChange([...selected, id])
    }
  }

  const selectAll = () => {
    onChange(districts.map((d) => d.id))
  }

  const applyPreset = (value: string) => {
    if (value === "all") {
      selectAll()
      return
    }

    if (value === "top5") {
      onChange(districts.slice(0, 5).map((d) => d.id))
      return
    }

    if (value === "izmit") {
      const izmit = districts.find((d) => d.id === "izmit")
      if (izmit) {
        onChange([izmit.id])
      }
    }
  }

  const selectedNames = districts
    .filter((d) => selected.includes(d.id))
    .map((d) => d.name)
    .slice(0, 3)

  return (
    <div className="relative">
      <motion.button
        type="button"
        className={cn(
          "flex items-center gap-2 px-4 py-2 rounded-xl",
          "bg-card border border-border",
          "hover:bg-secondary transition-colors",
          "text-sm font-medium",
        )}
        onClick={() => setIsOpen(!isOpen)}
        whileHover={{ scale: 1.02 }}
        whileTap={{ scale: 0.98 }}
      >
        <MapPin className="w-4 h-4 text-primary" />
        <span className="max-w-[180px] truncate">
          {selected.length === 0
            ? "Ilce secin"
            : selected.length === districts.length
              ? "Tum ilceler"
              : `${selectedNames.join(", ")}${selected.length > 3 ? ` +${selected.length - 3}` : ""}`}
        </span>
        <motion.div
          animate={{ rotate: isOpen ? 180 : 0 }}
          transition={{ duration: 0.2 }}
        >
          <ChevronDown className="w-4 h-4" />
        </motion.div>
      </motion.button>

      <AnimatePresence>
        {isOpen && (
          <>
            <motion.div
              className="fixed inset-0 z-40"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setIsOpen(false)}
            />

            <motion.div
              className="absolute top-full left-0 mt-2 w-72 max-h-80 overflow-y-auto glass rounded-xl border border-border shadow-xl z-50"
              initial={{ opacity: 0, y: -10, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -10, scale: 0.95 }}
              transition={{ type: "spring", stiffness: 300, damping: 25 }}
            >
              <div className="sticky top-0 p-3 border-b border-border bg-card/90 backdrop-blur-sm">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">Kocaeli Ilceleri</span>
                  <button
                    type="button"
                    className="text-xs text-primary hover:underline"
                    onClick={selectAll}
                  >
                    Tumunu sec
                  </button>
                </div>

                <div className="mt-2">
                  <Select onValueChange={applyPreset}>
                    <SelectTrigger className="h-8 bg-background/70 text-xs">
                      <SelectValue placeholder="Hazir secim" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">Tum ilceler</SelectItem>
                      <SelectItem value="top5">En aktif 5 ilce</SelectItem>
                      <SelectItem value="izmit">Sadece Izmit</SelectItem>
                    </SelectContent>
                  </Select>
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
                        "w-full flex items-center justify-between px-3 py-2 rounded-lg",
                        "transition-colors text-left",
                        isSelected
                          ? "bg-primary/10 text-primary"
                          : "hover:bg-secondary",
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
                            "w-5 h-5 rounded-md border-2 flex items-center justify-center",
                            isSelected
                              ? "bg-primary border-primary"
                              : "border-border",
                          )}
                          animate={{ scale: isSelected ? [1, 1.2, 1] : 1 }}
                          transition={{ duration: 0.2 }}
                        >
                          <AnimatePresence>
                            {isSelected && (
                              <motion.div
                                initial={{ scale: 0 }}
                                animate={{ scale: 1 }}
                                exit={{ scale: 0 }}
                              >
                                <Check className="w-3 h-3 text-primary-foreground" />
                              </motion.div>
                            )}
                          </AnimatePresence>
                        </motion.div>
                        <span className="text-sm font-medium">{district.name}</span>
                      </div>

                      <motion.span
                        className={cn(
                          "px-2 py-0.5 text-xs rounded-full",
                          isSelected
                            ? "bg-primary text-primary-foreground"
                            : "bg-secondary text-secondary-foreground",
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

              <div className="sticky bottom-0 p-3 border-t border-border bg-card/90 backdrop-blur-sm">
                <div className="flex items-center justify-between text-xs text-muted-foreground">
                  <span>{selected.length} ilce aktif</span>
                  <span>
                    {districts
                      .filter((d) => selected.includes(d.id))
                      .reduce((sum, d) => sum + d.newsCount, 0)} haber
                  </span>
                </div>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  )
}
