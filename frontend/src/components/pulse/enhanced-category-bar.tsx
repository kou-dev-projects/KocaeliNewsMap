"use client"

import { motion } from "framer-motion"
import {
  MapPin,
  Car,
  Flame,
  Zap,
  ShieldAlert,
  Calendar,
} from "lucide-react"

interface EnhancedCategoryBarProps {
  selectedCategory: string | null
  onCategoryChange: (category: string | null) => void
  categoryCounts: Record<string, number>
}

const categories = [
  { id: null, label: "Tümü", icon: MapPin, color: "from-primary to-primary/80", textColor: "text-primary" },
  { id: "breaking", label: "Son Dakika", icon: Zap, color: "from-red-500 to-red-600", textColor: "text-red-500" },
  { id: "traffic", label: "Trafik Kazası", icon: Car, color: "from-amber-500 to-amber-600", textColor: "text-amber-500" },
  { id: "fire", label: "Yangın", icon: Flame, color: "from-red-600 to-red-700", textColor: "text-red-600" },
  { id: "outage", label: "Elektrik Kesintisi", icon: Zap, color: "from-yellow-500 to-yellow-600", textColor: "text-yellow-600" },
  { id: "theft", label: "Hırsızlık", icon: ShieldAlert, color: "from-violet-500 to-violet-600", textColor: "text-violet-500" },
  { id: "event", label: "Kültürel Etkinlikler", icon: Calendar, color: "from-emerald-500 to-emerald-600", textColor: "text-emerald-500" },
]

export function EnhancedCategoryBar({ selectedCategory, onCategoryChange, categoryCounts }: EnhancedCategoryBarProps) {
  const totalCount = Object.values(categoryCounts).reduce((a, b) => a + b, 0)

  return (
    <div className="absolute bottom-4 left-1/2 -translate-x-1/2 z-20 w-full max-w-6xl px-4">
      <motion.div
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3, type: "spring", stiffness: 200 }}
        className="glass rounded-2xl p-2 shadow-2xl"
      >
        <div className="grid grid-cols-2 gap-1 md:grid-cols-4 xl:grid-cols-7">
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
                className={`relative flex min-w-0 items-center justify-center gap-2 px-3 py-2 rounded-xl transition-all ${
                  isSelected ? "text-white shadow-lg" : "hover:bg-secondary/80 text-foreground"
                }`}
                whileHover={{ scale: 1.02, y: -1 }}
                whileTap={{ scale: 0.98 }}
              >
                {isSelected && (
                  <motion.div
                    layoutId="category-bg"
                    className={`absolute inset-0 rounded-xl bg-gradient-to-r ${category.color}`}
                    transition={{ type: "spring", stiffness: 400, damping: 30 }}
                  />
                )}

                <span className={`relative z-10 ${isSelected ? "text-white" : category.textColor}`}>
                  <Icon className="w-4 h-4" />
                </span>

                <span className="relative z-10 text-center text-[12px] font-normal leading-tight xl:text-[13px]">
                  {category.label}
                </span>

                {count > 0 && (
                  <motion.span
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    className={`relative z-10 text-[11px] px-2 py-0.5 rounded-md font-medium ${
                      isSelected ? "bg-white/20 text-white" : "bg-muted text-muted-foreground"
                    }`}
                  >
                    {count}
                  </motion.span>
                )}

                {category.id === "breaking" && count > 0 && !isSelected && (
                  <motion.span
                    className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full"
                    animate={{ scale: [1, 1.3, 1], opacity: [1, 0.5, 1] }}
                    transition={{ duration: 0.8, repeat: Infinity }}
                  />
                )}
              </motion.button>
            )
          })}
        </div>
      </motion.div>
    </div>
  )
}
