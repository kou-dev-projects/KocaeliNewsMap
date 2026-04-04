"use client"

import { motion } from "framer-motion"
import { Car, Flame, MapPin, Music2, Star, VenetianMask, Zap } from "lucide-react"

import { cn } from "@/lib/utils"

interface EnhancedCategoryBarProps {
  selectedCategory: string | null
  onCategoryChange: (category: string | null) => void
  categoryCounts: Record<string, number>
  className?: string
  embedded?: boolean
}

const categories = [
  { id: null, label: "Tumu", icon: MapPin, color: "from-primary to-primary/80", textColor: "text-primary", weight: 0.95 },
  { id: "breaking", label: "Gundem", icon: Star, color: "from-sky-500 to-blue-600", textColor: "text-sky-600", weight: 1.05 },
  { id: "traffic", label: "Trafik Kazasi", icon: Car, color: "from-amber-500 to-amber-600", textColor: "text-amber-500", weight: 1.2 },
  { id: "fire", label: "Yangin", icon: Flame, color: "from-red-600 to-red-700", textColor: "text-red-600", weight: 0.95 },
  { id: "outage", label: "Elektrik Kesintisi", icon: Zap, color: "from-yellow-500 to-yellow-600", textColor: "text-yellow-600", weight: 1.45 },
  { id: "theft", label: "Hirsizlik", icon: VenetianMask, color: "from-violet-500 to-violet-600", textColor: "text-violet-500", weight: 1.05 },
  { id: "event", label: "Kulturel Etkinlikler", icon: Music2, color: "from-emerald-500 to-emerald-600", textColor: "text-emerald-500", weight: 1.55 },
] as const

export function EnhancedCategoryBar({
  selectedCategory,
  onCategoryChange,
  categoryCounts,
  className,
  embedded = false,
}: EnhancedCategoryBarProps) {
  const totalCount = Object.values(categoryCounts).reduce((sum, value) => sum + value, 0)
  const gridTemplateColumns = categories.map((category) => `${category.weight}fr`).join(" ")

  const content = (
    <div className="grid h-full gap-2" style={{ gridTemplateColumns }}>
      {categories.map((category, index) => {
        const isSelected = selectedCategory === category.id
        const count = category.id ? (categoryCounts[category.id] || 0) : totalCount
        const Icon = category.icon

        return (
          <motion.button
            key={category.id || "all"}
            type="button"
            data-testid={`category-chip-${category.id || "all"}`}
            title={category.label}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.35 + index * 0.04 }}
            onClick={() => onCategoryChange(category.id)}
            className={cn(
              "relative flex h-[64px] min-w-0 items-center gap-3 rounded-2xl px-3.5 pr-11 text-left",
              "border border-border/60 bg-card/82 shadow-sm backdrop-blur-xl transition-all",
              isSelected ? "text-white shadow-lg" : "text-foreground hover:bg-card/96",
            )}
            whileHover={{ scale: 1.01, y: -1 }}
            whileTap={{ scale: 0.99 }}
          >
            {isSelected ? (
              <motion.div
                layoutId="category-bg"
                className={`absolute inset-0 rounded-2xl bg-gradient-to-r ${category.color}`}
                transition={{ type: "spring", stiffness: 400, damping: 30 }}
              />
            ) : null}

            <div className="relative z-10 flex min-w-0 items-center gap-2.5">
              <div
                className={cn(
                  "flex h-7 w-7 shrink-0 items-center justify-center rounded-xl",
                  isSelected ? "bg-white/16 text-white" : "bg-secondary/90",
                  !isSelected && category.textColor,
                )}
              >
                <Icon className="h-3.5 w-3.5" />
              </div>
              <span
                className={cn(
                  "line-clamp-2 text-[11px] font-semibold leading-[1.15] 2xl:text-[12px]",
                  isSelected ? "text-white" : "text-foreground",
                )}
              >
                {category.label}
              </span>
            </div>

            {count > 0 ? (
              <motion.span
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                className={cn(
                  "absolute right-2.5 top-2.5 z-10 inline-flex h-5 min-w-5 items-center justify-center rounded-full px-1.5 text-[10px] font-semibold leading-none",
                  isSelected ? "bg-white/18 text-white" : "bg-muted text-muted-foreground",
                )}
              >
                {count}
              </motion.span>
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
        className={embedded ? "h-full" : "glass rounded-2xl p-2 shadow-2xl"}
      >
        {embedded ? content : <div>{content}</div>}
      </motion.div>
    </div>
  )
}
