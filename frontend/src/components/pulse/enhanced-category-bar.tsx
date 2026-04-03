"use client"

import { motion } from "framer-motion"
import {
  MapPin,
  Car,
  AlertTriangle,
  Cloud,
  Calendar,
  TrendingUp,
  Trophy,
  Heart,
  Zap,
  Filter,
} from "lucide-react"

interface EnhancedCategoryBarProps {
  selectedCategory: string | null
  onCategoryChange: (category: string | null) => void
  categoryCounts: Record<string, number>
}

const categories = [
  { id: null, label: "Tümü", icon: MapPin, color: "from-primary to-primary/80", textColor: "text-primary" },
  { id: "breaking", label: "Son Dakika", icon: Zap, color: "from-red-500 to-red-600", textColor: "text-red-500" },
  { id: "traffic", label: "Trafik", icon: Car, color: "from-amber-500 to-amber-600", textColor: "text-amber-500" },
  { id: "crime", label: "Asayiş", icon: AlertTriangle, color: "from-red-600 to-red-700", textColor: "text-red-600" },
  { id: "weather", label: "Hava", icon: Cloud, color: "from-sky-500 to-sky-600", textColor: "text-sky-500" },
  { id: "event", label: "Etkinlik", icon: Calendar, color: "from-emerald-500 to-emerald-600", textColor: "text-emerald-500" },
  { id: "economy", label: "Gündem", icon: TrendingUp, color: "from-violet-500 to-violet-600", textColor: "text-violet-500" },
  { id: "sports", label: "Spor", icon: Trophy, color: "from-orange-500 to-orange-600", textColor: "text-orange-500" },
  { id: "health", label: "Sağlık", icon: Heart, color: "from-pink-500 to-pink-600", textColor: "text-pink-500" },
]

export function EnhancedCategoryBar({ selectedCategory, onCategoryChange, categoryCounts }: EnhancedCategoryBarProps) {
  const totalCount = Object.values(categoryCounts).reduce((a, b) => a + b, 0)

  return (
    <div className="absolute bottom-4 left-1/2 -translate-x-1/2 z-20 w-full max-w-5xl px-4">
      <motion.div
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3, type: "spring", stiffness: 200 }}
        className="glass rounded-2xl p-2 shadow-2xl"
      >
        <div className="flex items-center gap-1 overflow-x-auto scrollbar-hide pb-1">
          <div className="hidden lg:flex items-center gap-2 px-3 py-2 text-muted-foreground border-r border-border mr-2">
            <Filter className="w-4 h-4" />
            <span className="text-xs font-medium uppercase tracking-wider">Filtrele</span>
          </div>

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
                className={`relative flex items-center gap-2 px-4 py-2.5 rounded-xl transition-all whitespace-nowrap ${
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

                <span className={`relative z-10 font-medium text-sm ${index > 3 ? "hidden md:inline" : ""}`}>
                  {category.label}
                </span>

                {count > 0 && (
                  <motion.span
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    className={`relative z-10 text-xs px-2 py-0.5 rounded-md font-semibold ${
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
