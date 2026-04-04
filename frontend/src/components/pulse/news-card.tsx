"use client"

import { motion } from "framer-motion"
import { cn } from "@/lib/utils"
import { Clock, MapPin, ExternalLink } from "lucide-react"

export type PulseNewsCategory = "traffic" | "crime" | "weather" | "event" | "economy"

interface NewsCardProps {
  title: string
  summary: string
  category: PulseNewsCategory
  district: string
  time: string
  source: string
  isNew?: boolean
  index?: number
  onClick?: () => void
}

const categoryConfig = {
  traffic: {
    bg: "bg-amber-500/10 dark:bg-amber-500/20",
    border: "border-amber-500/30",
    badge: "bg-amber-500 text-white",
    label: "Trafik",
  },
  crime: {
    bg: "bg-red-500/10 dark:bg-red-500/20",
    border: "border-red-500/30",
    badge: "bg-red-500 text-white",
    label: "Asayiş",
  },
  weather: {
    bg: "bg-blue-500/10 dark:bg-blue-500/20",
    border: "border-blue-500/30",
    badge: "bg-blue-500 text-white",
    label: "Hava",
  },
  event: {
    bg: "bg-emerald-500/10 dark:bg-emerald-500/20",
    border: "border-emerald-500/30",
    badge: "bg-emerald-500 text-white",
    label: "Etkinlik",
  },
  economy: {
    bg: "bg-purple-500/10 dark:bg-purple-500/20",
    border: "border-purple-500/30",
    badge: "bg-purple-500 text-white",
    label: "Ekonomi",
  },
}

export function NewsCard({
  title,
  summary,
  category,
  district,
  time,
  source,
  isNew = false,
  index = 0,
  onClick,
}: NewsCardProps) {
  const config = categoryConfig[category]

  return (
    <motion.div
      className={cn(
        "relative p-4 rounded-xl border cursor-pointer overflow-hidden",
        "bg-card hover:bg-card/80 transition-colors",
        config.border,
        isNew && "ring-2 ring-primary ring-offset-2 ring-offset-background",
      )}
      initial={{ opacity: 0, x: 100, rotateY: -15 }}
      animate={{ opacity: 1, x: 0, rotateY: 0 }}
      transition={{
        duration: 0.5,
        delay: index * 0.1,
        type: "spring",
        stiffness: 100,
      }}
      whileHover={{ scale: 1.02, y: -2 }}
      whileTap={{ scale: 0.98 }}
      onClick={onClick}
    >
      {isNew && (
        <motion.div
          className="absolute top-2 right-2"
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ type: "spring", delay: 0.3 }}
        >
          <span className="relative flex h-3 w-3">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75"></span>
            <span className="relative inline-flex rounded-full h-3 w-3 bg-primary"></span>
          </span>
        </motion.div>
      )}

      <motion.div
        className={cn("absolute inset-0 opacity-0", config.bg)}
        initial={{ opacity: 0 }}
        whileHover={{ opacity: 1 }}
        transition={{ duration: 0.3 }}
      />

      <div className="relative z-10">
        <motion.span
          className={cn("inline-block px-2 py-0.5 text-xs font-medium rounded-full mb-2", config.badge)}
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ type: "spring", delay: index * 0.1 + 0.2 }}
        >
          {config.label}
        </motion.span>

        <h3 className="font-semibold text-card-foreground mb-1 line-clamp-2 text-balance">
          {title}
        </h3>

        <p className="text-sm text-muted-foreground mb-3 line-clamp-2">
          {summary}
        </p>

        <div className="flex items-center gap-3 text-xs text-muted-foreground">
          <span className="flex items-center gap-1">
            <MapPin className="w-3 h-3" />
            {district}
          </span>
          <span className="flex items-center gap-1">
            <Clock className="w-3 h-3" />
            {time}
          </span>
          <span className="flex items-center gap-1 ml-auto">
            <ExternalLink className="w-3 h-3" />
            {source}
          </span>
        </div>
      </div>

      <motion.div
        className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent -translate-x-full"
        whileHover={{ translateX: "100%" }}
        transition={{ duration: 0.5 }}
      />
    </motion.div>
  )
}
