"use client"

import { useState, type ReactNode } from "react"
import { AnimatePresence, motion } from "framer-motion"
import {
  Car,
  ChevronDown,
  Clock,
  Flame,
  GripHorizontal,
  MapPin,
  Music2,
  Radio,
  Star,
  VenetianMask,
  Zap,
} from "lucide-react"

import type { NewsMapItem } from "@/components/map/MapView"

export type LiveNewsFeedItem = NewsMapItem & {
  pulseCategory: "traffic" | "fire" | "outage" | "theft" | "event" | "breaking"
  timeLabel: string
  isRecent?: boolean
}

interface LiveNewsFeedProps {
  news: LiveNewsFeedItem[]
  onNewsClick: (news: NewsMapItem) => void
  hidden?: boolean
}

const categoryConfig: Record<string, { bgColor: string; icon: ReactNode }> = {
  breaking: { bgColor: "bg-sky-600", icon: <Star className="h-3.5 w-3.5" /> },
  traffic: { bgColor: "bg-amber-500", icon: <Car className="h-3.5 w-3.5" /> },
  fire: { bgColor: "bg-red-600", icon: <Flame className="h-3.5 w-3.5" /> },
  outage: { bgColor: "bg-yellow-500", icon: <Zap className="h-3.5 w-3.5" /> },
  theft: { bgColor: "bg-violet-500", icon: <VenetianMask className="h-3.5 w-3.5" /> },
  event: { bgColor: "bg-emerald-500", icon: <Music2 className="h-3.5 w-3.5" /> },
}

export function LiveNewsFeed({ news, onNewsClick, hidden = false }: LiveNewsFeedProps) {
  const [isCollapsed, setIsCollapsed] = useState(false)

  return (
    <motion.div
      initial={{ opacity: 0, x: -30 }}
      animate={{ opacity: hidden ? 0 : 1, x: hidden ? -30 : 0, pointerEvents: hidden ? "none" : "auto" }}
      transition={{ delay: 0.4 }}
      className="absolute top-36 left-4 z-20 hidden w-full max-w-xs xl:block"
      drag
      dragMomentum={false}
      dragElastic={0.08}
      whileDrag={{ scale: 1.01 }}
    >
      <div className="flex w-full cursor-grab items-center justify-between rounded-t-xl glass px-4 py-3 active:cursor-grabbing">
        <div className="min-w-0 flex items-center gap-3">
          <div className="relative">
            <Radio className="h-5 w-5 text-primary" />
            <motion.span
              className="absolute -right-0.5 -top-0.5 h-2 w-2 rounded-full bg-emerald-500"
              animate={{ scale: [1, 1.3, 1], opacity: [1, 0.5, 1] }}
              transition={{ duration: 1, repeat: Infinity }}
            />
          </div>
          <div className="text-left">
            <span className="text-sm font-semibold text-foreground">Canlı Haber Akışı</span>
            <p className="text-xs text-muted-foreground">{news.length} haber</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <GripHorizontal className="h-4 w-4 text-muted-foreground" />
          <button
            type="button"
            onClick={() => setIsCollapsed((current) => !current)}
            className="rounded-lg p-1 text-muted-foreground transition-colors hover:bg-secondary/60 hover:text-foreground"
            aria-label={isCollapsed ? "Canlı haber akışını aç" : "Canlı haber akışını kapat"}
          >
            <motion.span
              animate={{ rotate: isCollapsed ? -90 : 0 }}
              transition={{ duration: 0.2 }}
              className="block"
            >
              <ChevronDown className="h-5 w-5" />
            </motion.span>
          </button>
        </div>
      </div>

      <AnimatePresence>
        {!isCollapsed ? (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3 }}
            className="overflow-hidden rounded-b-xl border-t border-border glass"
          >
            <div className="max-h-[calc(100vh-12rem)] space-y-2 overflow-y-auto p-2">
              {news.length === 0 ? (
                <div className="rounded-lg border border-dashed border-border/70 bg-card/40 px-4 py-6 text-center text-sm text-muted-foreground">
                  Aktif filtrelere göre gösterilecek canlı haber yok.
                </div>
              ) : (
                news.map((item, index) => {
                  const config = categoryConfig[item.pulseCategory] || categoryConfig.breaking

                  return (
                    <motion.button
                      key={item.id}
                      type="button"
                      initial={{ opacity: 0, y: -10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: index * 0.05 }}
                      onClick={() => onNewsClick(item)}
                      className="group relative w-full rounded-lg p-3 text-left transition-all hover:bg-secondary/50"
                    >
                      <div className="flex items-start gap-3">
                        <div
                          className={`${config.bgColor} flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-white`}
                        >
                          {config.icon}
                        </div>
                        <div className="min-w-0 flex-1">
                          <p className="line-clamp-2 text-sm font-medium text-foreground transition-colors group-hover:text-primary">
                            {item.title}
                          </p>
                          <div className="mt-1.5 flex items-center gap-2 text-[10px] text-muted-foreground">
                            <div className="flex items-center gap-0.5">
                              <MapPin className="h-2.5 w-2.5" />
                              <span>{item.district || "Bilinmeyen"}</span>
                            </div>
                            <span className="text-border">|</span>
                            <div className="flex items-center gap-0.5">
                              <Clock className="h-2.5 w-2.5" />
                              <span>{item.timeLabel}</span>
                            </div>
                          </div>
                        </div>
                      </div>

                      {item.isRecent ? (
                        <motion.div
                          className="absolute right-2 top-2 rounded bg-primary px-1.5 py-0.5 text-[8px] font-bold text-primary-foreground"
                          animate={{ opacity: [1, 0.7, 1] }}
                          transition={{ duration: 1, repeat: Infinity }}
                        >
                          YENİ
                        </motion.div>
                      ) : null}
                    </motion.button>
                  )
                })
              )}
            </div>
          </motion.div>
        ) : null}
      </AnimatePresence>
    </motion.div>
  )
}
