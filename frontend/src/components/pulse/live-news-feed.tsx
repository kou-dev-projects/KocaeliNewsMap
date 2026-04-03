"use client"

import { motion, AnimatePresence } from "framer-motion"
import {
  Zap,
  Car,
  AlertTriangle,
  Cloud,
  Calendar,
  TrendingUp,
  Trophy,
  Heart,
  MapPin,
  Clock,
  ChevronRight,
  Radio,
} from "lucide-react"
import type { NewsMapItem } from "@/components/map/MapView"

export type LiveNewsFeedItem = NewsMapItem & {
  pulseCategory: "traffic" | "crime" | "weather" | "event" | "economy" | "sports" | "health" | "breaking"
  timeLabel: string
  isRecent?: boolean
}

interface LiveNewsFeedProps {
  news: LiveNewsFeedItem[]
  onNewsClick: (news: NewsMapItem) => void
  collapsed?: boolean
}

const categoryConfig: Record<string, { bgColor: string; icon: React.ReactNode }> = {
  breaking: { bgColor: "bg-red-500", icon: <Zap className="w-3.5 h-3.5" /> },
  traffic: { bgColor: "bg-amber-500", icon: <Car className="w-3.5 h-3.5" /> },
  crime: { bgColor: "bg-red-600", icon: <AlertTriangle className="w-3.5 h-3.5" /> },
  weather: { bgColor: "bg-sky-500", icon: <Cloud className="w-3.5 h-3.5" /> },
  event: { bgColor: "bg-emerald-500", icon: <Calendar className="w-3.5 h-3.5" /> },
  economy: { bgColor: "bg-violet-500", icon: <TrendingUp className="w-3.5 h-3.5" /> },
  sports: { bgColor: "bg-orange-500", icon: <Trophy className="w-3.5 h-3.5" /> },
  health: { bgColor: "bg-pink-500", icon: <Heart className="w-3.5 h-3.5" /> },
}

export function LiveNewsFeed({ news, onNewsClick, collapsed = false }: LiveNewsFeedProps) {
  return (
    <motion.div
      initial={{ opacity: 0, x: -30 }}
      animate={{ opacity: collapsed ? 0 : 1, x: collapsed ? -30 : 0, pointerEvents: collapsed ? "none" : "auto" }}
      transition={{ delay: 0.4 }}
      className="absolute top-36 left-4 z-20 hidden w-full max-w-xs xl:block"
    >
      <div className="w-full glass rounded-t-xl px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="relative">
            <Radio className="w-5 h-5 text-primary" />
            <motion.span
              className="absolute -top-0.5 -right-0.5 w-2 h-2 bg-emerald-500 rounded-full"
              animate={{ scale: [1, 1.3, 1], opacity: [1, 0.5, 1] }}
              transition={{ duration: 1, repeat: Infinity }}
            />
          </div>
          <div className="text-left">
            <span className="font-semibold text-sm text-foreground">Canlı Haber Akışı</span>
            <p className="text-xs text-muted-foreground">{news.length} haber</p>
          </div>
        </div>
        <ChevronRight className="w-5 h-5 text-muted-foreground" />
      </div>

      <AnimatePresence>
        <motion.div
          initial={{ height: 0, opacity: 0 }}
          animate={{ height: "auto", opacity: 1 }}
          exit={{ height: 0, opacity: 0 }}
          transition={{ duration: 0.3 }}
          className="glass rounded-b-xl border-t border-border overflow-hidden"
        >
          <div className="p-2 space-y-2 max-h-80 overflow-y-auto">
            {news.length === 0 ? (
              <div className="rounded-lg border border-dashed border-border/70 bg-card/40 px-4 py-6 text-center text-sm text-muted-foreground">
                Aktif filtrelere göre gösterilecek canlı haber yok.
              </div>
            ) : news.map((item, index) => {
              const config = categoryConfig[item.pulseCategory] || categoryConfig.breaking

              return (
                <motion.button
                  key={item.id}
                  type="button"
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.05 }}
                  onClick={() => onNewsClick(item)}
                  className="w-full text-left p-3 rounded-lg hover:bg-secondary/50 transition-all group relative"
                >
                  <div className="flex items-start gap-3">
                    <div
                      className={`${config.bgColor} w-8 h-8 rounded-lg flex items-center justify-center text-white shrink-0`}
                    >
                      {config.icon}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-foreground line-clamp-2 group-hover:text-primary transition-colors">
                        {item.title}
                      </p>
                      <div className="flex items-center gap-2 mt-1.5 text-[10px] text-muted-foreground">
                        <div className="flex items-center gap-0.5">
                          <MapPin className="w-2.5 h-2.5" />
                          <span>{item.district || "Bilinmeyen"}</span>
                        </div>
                        <span className="text-border">|</span>
                        <div className="flex items-center gap-0.5">
                          <Clock className="w-2.5 h-2.5" />
                          <span>{item.timeLabel}</span>
                        </div>
                      </div>
                    </div>
                  </div>

                  {item.isRecent && (
                    <motion.div
                      className="absolute top-2 right-2 px-1.5 py-0.5 rounded text-[8px] font-bold bg-primary text-primary-foreground"
                      animate={{ opacity: [1, 0.7, 1] }}
                      transition={{ duration: 1, repeat: Infinity }}
                    >
                      YENİ
                    </motion.div>
                  )}
                </motion.button>
              )
            })}
          </div>
        </motion.div>
      </AnimatePresence>
    </motion.div>
  )
}
