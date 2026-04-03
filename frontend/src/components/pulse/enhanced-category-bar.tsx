"use client"

import { motion } from "framer-motion"
import { Calendar, Car, Flame, MapPin, ShieldAlert, Zap } from "lucide-react"

import { cn } from "@/lib/utils"

interface EnhancedCategoryBarProps {
  selectedCategory: string | null
  onCategoryChange: (category: string | null) => void
  categoryCounts: Record<string, number>
  className?: string
  embedded?: boolean
}

const categories = [
  { id: null, label: "Tümü", icon: MapPin, color: "from-primary to-primary/80", textColor: "text-primary", minWidth: "xl:min-w-[112px]" },
  { id: "breaking", label: "Son Dakika", icon: Zap, color: "from-red-500 to-red-600", textColor: "text-red-500", minWidth: "xl:min-w-[128px]" },
  { id: "traffic", label: "Trafik Kazası", icon: Car, color: "from-amber-500 to-amber-600", textColor: "text-amber-500", minWidth: "xl:min-w-[136px]" },
  { id: "fire", label: "Yangın", icon: Flame, color: "from-red-600 to-red-700", textColor: "text-red-600", minWidth: "xl:min-w-[112px]" },
  { id: "outage", label: "Elektrik Kesintisi", icon: Zap, color: "from-yellow-500 to-yellow-600", textColor: "text-yellow-600", minWidth: "xl:min-w-[170px]" },
  { id: "theft", label: "Hırsızlık", icon: ShieldAlert, color: "from-violet-500 to-violet-600", textColor: "text-violet-500", minWidth: "xl:min-w-[118px]" },
  { id: "event", label: "Kültürel Etkinlikler", icon: Calendar, color: "from-emerald-500 to-emerald-600", textColor: "text-emerald-500", minWidth: "xl:min-w-[200px]" },
]

export function EnhancedCategoryBar({
  selectedCategory,
  onCategoryChange,
  categoryCounts,
  className,
  embedded = false,
}: EnhancedCategoryBarProps) {
  const totalCount = Object.values(categoryCounts).reduce((sum, value) => sum + value, 0)

  const content = (
    <div className="grid grid-cols-2 gap-1 md:grid-cols-4 xl:flex xl:flex-nowrap xl:items-stretch xl:gap-1">
      {categories.map((category, index) => {
        const isSelected = selectedCategory === category.id
        const count = category.id ? (categoryCounts[category.id] || 0) : totalCount
        const Icon = category.icon

        return (
          <motion.button
            key={category.id || "all"}
            type="button"
            data-testid={`category-chip-${category.id || "all"}`}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.35 + index * 0.04 }}
            onClick={() => onCategoryChange(category.id)}
            className={cn(
              "relative flex h-[42px] min-w-0 items-center justify-center gap-2 rounded-xl px-4",
              "text-sm font-medium leading-none transition-all xl:flex-1",
              category.minWidth,
              isSelected ? "text-white shadow-lg" : "text-foreground hover:bg-secondary/80",
            )}
            whileHover={{ scale: 1.02, y: -1 }}
            whileTap={{ scale: 0.98 }}
          >
            {isSelected ? (
              <motion.div
                layoutId="category-bg"
                className={`absolute inset-0 rounded-xl bg-gradient-to-r ${category.color}`}
                transition={{ type: "spring", stiffness: 400, damping: 30 }}
              />
            ) : null}

            <span className={cn("relative z-10 flex h-full items-center", isSelected ? "text-white" : category.textColor)}>
              <Icon className="h-4 w-4" />
            </span>

            <span
              className={cn(
                "relative z-10 flex h-full items-center whitespace-nowrap text-sm font-medium leading-none",
                isSelected ? "text-white" : "text-foreground",
              )}
            >
              {category.label}
            </span>

            {count > 0 ? (
              <motion.span
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                className={cn(
                  "relative z-10 inline-flex h-5 shrink-0 items-center rounded-md px-2 text-[11px] font-medium leading-none",
                  isSelected ? "bg-white/20 text-white" : "bg-muted text-muted-foreground",
                )}
              >
                {count}
              </motion.span>
            ) : null}

            {category.id === "breaking" && count > 0 && !isSelected ? (
              <motion.span
                className="absolute right-1 top-1 h-2 w-2 rounded-full bg-red-500"
                animate={{ scale: [1, 1.3, 1], opacity: [1, 0.5, 1] }}
                transition={{ duration: 0.8, repeat: Infinity }}
              />
            ) : null}
          </motion.button>
        )
      })}
    </div>
  )

  return (
    <div className={cn("w-full", className)}>
      <motion.div
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3, type: "spring", stiffness: 200 }}
        className={embedded ? "min-h-[58px]" : "glass rounded-2xl p-2 shadow-2xl"}
      >
        {embedded ? content : <div>{content}</div>}
      </motion.div>
    </div>
  )
}
