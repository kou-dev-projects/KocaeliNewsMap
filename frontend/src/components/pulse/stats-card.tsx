"use client"

import { motion } from "framer-motion"
import { cn } from "@/lib/utils"
import { TrendingUp, TrendingDown, Minus } from "lucide-react"
import { useEffect, useState } from "react"

interface StatsCardProps {
  title: string
  value: number | string
  previousValue?: number
  suffix?: string
  icon: React.ReactNode
  color?: string
  delay?: number
}

export function StatsCard({
  title,
  value,
  previousValue,
  suffix = "",
  icon,
  color = "bg-primary",
  delay = 0,
}: StatsCardProps) {
  const isNumericValue = typeof value === "number"
  const [displayValue, setDisplayValue] = useState(isNumericValue ? value : 0)

  useEffect(() => {
    if (!isNumericValue) {
      return
    }

    const duration = 1500
    const steps = 60
    const increment = value / steps
    let current = 0
    let step = 0

    const timer = setInterval(() => {
      step++
      current = Math.min(Math.round(increment * step), value)
      setDisplayValue(current)

      if (step >= steps) {
        clearInterval(timer)
        setDisplayValue(value)
      }
    }, duration / steps)

    return () => clearInterval(timer)
  }, [isNumericValue, value])

  const change = isNumericValue && previousValue ? ((value - previousValue) / previousValue) * 100 : 0
  const trend = change > 0 ? "up" : change < 0 ? "down" : "neutral"

  return (
    <motion.div
      className="relative p-4 rounded-xl bg-card border border-border overflow-hidden group"
      initial={{ opacity: 0, y: 20, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{
        type: "spring",
        stiffness: 200,
        damping: 20,
        delay,
      }}
      whileHover={{ scale: 1.02, y: -2 }}
    >
      <motion.div
        className={cn("absolute -right-8 -top-8 w-24 h-24 rounded-full opacity-10", color)}
        initial={{ scale: 0 }}
        animate={{ scale: 1 }}
        transition={{ delay: delay + 0.2, type: "spring" }}
      />

      <div className="relative">
        <div className="flex items-center justify-between mb-3">
          <motion.div
            className={cn("p-2 rounded-lg", color, "text-white")}
            whileHover={{ rotate: [0, -10, 10, 0] }}
            transition={{ duration: 0.4 }}
          >
            {icon}
          </motion.div>

          {isNumericValue && previousValue && (
            <motion.div
              className={cn(
                "flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium",
                trend === "up" && "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400",
                trend === "down" && "bg-red-500/10 text-red-600 dark:text-red-400",
                trend === "neutral" && "bg-secondary text-secondary-foreground",
              )}
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ delay: delay + 0.4, type: "spring" }}
            >
              {trend === "up" && <TrendingUp className="w-3 h-3" />}
              {trend === "down" && <TrendingDown className="w-3 h-3" />}
              {trend === "neutral" && <Minus className="w-3 h-3" />}
              <span>{Math.abs(change).toFixed(1)}%</span>
            </motion.div>
          )}
        </div>

        <motion.div
          className="text-3xl font-bold text-card-foreground mb-1"
          key={isNumericValue ? displayValue : value}
        >
          {isNumericValue ? displayValue.toLocaleString("tr-TR") : value}
          {suffix && isNumericValue ? <span className="text-lg text-muted-foreground ml-1">{suffix}</span> : null}
        </motion.div>

        <p className="text-sm text-muted-foreground">{title}</p>

        <motion.div
          className="absolute bottom-0 left-0 right-0 h-1 bg-secondary overflow-hidden rounded-b-xl"
        >
          <motion.div
            className={cn("h-full", color)}
            initial={{ width: 0 }}
            animate={{ width: "100%" }}
            transition={{ duration: 1.5, delay: delay, ease: "easeOut" }}
          />
        </motion.div>
      </div>

      <motion.div
        className="absolute inset-0 bg-gradient-to-r from-transparent via-white/5 to-transparent -translate-x-full group-hover:translate-x-full transition-transform duration-700"
      />
    </motion.div>
  )
}
