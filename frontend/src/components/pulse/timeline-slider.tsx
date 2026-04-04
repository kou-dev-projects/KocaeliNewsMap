"use client"

import { motion } from "framer-motion"
import { cn } from "@/lib/utils"
import { Play, Pause, SkipBack, SkipForward, Clock } from "lucide-react"
import { useState, useEffect, useCallback } from "react"
import { Button } from "@/components/ui/button"

interface TimelineSliderProps {
  onTimeChange?: (time: Date) => void
  duration?: number
}

export function TimelineSlider({ onTimeChange, duration = 72 }: TimelineSliderProps) {
  const [isPlaying, setIsPlaying] = useState(false)
  const [progress, setProgress] = useState(100)
  const [speed, setSpeed] = useState(1)
  const [hoveredTime, setHoveredTime] = useState<string | null>(null)
  const [hoverPosition, setHoverPosition] = useState(0)
  const [nowAnchor, setNowAnchor] = useState(() => Date.now())

  useEffect(() => {
    const interval = setInterval(() => {
      setNowAnchor(Date.now())
    }, 30_000)

    return () => clearInterval(interval)
  }, [])

  const formatTime = useCallback(
    (progressPercent: number) => {
      const now = new Date(nowAnchor)
      const hoursAgo = ((100 - progressPercent) / 100) * duration
      const targetTime = new Date(now.getTime() - hoursAgo * 60 * 60 * 1000)
      return targetTime.toLocaleString("tr-TR", {
        day: "2-digit",
        month: "short",
        hour: "2-digit",
        minute: "2-digit",
      })
    },
    [duration, nowAnchor],
  )

  useEffect(() => {
    if (!isPlaying) {
      return
    }

    const interval = setInterval(() => {
      setProgress((prev) => {
        const newProgress = Math.min(prev + 0.5 * speed, 100)
        if (newProgress >= 100) {
          setIsPlaying(false)
        }
        return newProgress
      })
    }, 100)

    return () => clearInterval(interval)
  }, [isPlaying, speed])

  useEffect(() => {
    if (!onTimeChange) {
      return
    }

    const now = new Date(nowAnchor)
    const hoursAgo = ((100 - progress) / 100) * duration
    const targetTime = new Date(now.getTime() - hoursAgo * 60 * 60 * 1000)
    onTimeChange(targetTime)
  }, [duration, nowAnchor, onTimeChange, progress])

  const handleTrackHover = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect()
    const x = e.clientX - rect.left
    const percentage = (x / rect.width) * 100
    setHoverPosition(percentage)
    setHoveredTime(formatTime(percentage))
  }

  const ticks = Array.from({ length: 13 }, (_, i) => i * (100 / 12))

  return (
    <motion.div
      className="glass rounded-2xl p-4 border border-border/50"
      initial={{ opacity: 0, y: 50 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ type: "spring", stiffness: 200, damping: 20 }}
    >
      <div className="flex items-center gap-4">
        <motion.div
          className="flex items-center gap-2 min-w-[140px]"
          key={progress}
          initial={{ scale: 0.95 }}
          animate={{ scale: 1 }}
          transition={{ type: "spring", stiffness: 400 }}
        >
          <Clock className="w-4 h-4 text-primary" />
          <span className="text-sm font-mono font-medium">
            {formatTime(progress)}
          </span>
        </motion.div>

        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8"
            onClick={() => setProgress(0)}
          >
            <SkipBack className="w-4 h-4" />
          </Button>

          <motion.div whileTap={{ scale: 0.9 }}>
            <Button
              variant="default"
              size="icon"
              className="h-10 w-10 rounded-full"
              onClick={() => setIsPlaying(!isPlaying)}
            >
              <motion.div
                initial={false}
                animate={{ rotate: isPlaying ? 0 : 0 }}
                transition={{ type: "spring", stiffness: 300 }}
              >
                {isPlaying ? (
                  <Pause className="w-4 h-4" />
                ) : (
                  <Play className="w-4 h-4 ml-0.5" />
                )}
              </motion.div>
            </Button>
          </motion.div>

          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8"
            onClick={() => setProgress(100)}
          >
            <SkipForward className="w-4 h-4" />
          </Button>
        </div>

        <div className="flex-1 relative">
          <div
            className="relative h-8 cursor-pointer group"
            onMouseMove={handleTrackHover}
            onMouseLeave={() => setHoveredTime(null)}
            onClick={(e) => {
              const rect = e.currentTarget.getBoundingClientRect()
              const x = e.clientX - rect.left
              setProgress((x / rect.width) * 100)
            }}
          >
            <div className="absolute top-1/2 -translate-y-1/2 left-0 right-0 h-2 bg-secondary rounded-full overflow-hidden">
              <motion.div
                className="absolute inset-y-0 left-0 bg-primary rounded-full"
                initial={false}
                animate={{ width: `${progress}%` }}
                transition={{ type: "spring", stiffness: 300, damping: 30 }}
              />

              <motion.div
                className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent"
                animate={{ x: ["-100%", "100%"] }}
                transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
                style={{ width: `${progress}%` }}
              />
            </div>

            {ticks.map((tick, i) => (
              <div
                key={i}
                className="absolute top-0 w-px h-2 bg-muted-foreground/30"
                style={{ left: `${tick}%` }}
              />
            ))}

            <motion.div
              className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 w-4 h-4 bg-primary rounded-full shadow-lg border-2 border-primary-foreground"
              style={{ left: `${progress}%` }}
              whileHover={{ scale: 1.3 }}
              transition={{ type: "spring", stiffness: 400, damping: 15 }}
            >
              <motion.div
                className="absolute inset-0 rounded-full bg-primary"
                animate={{ scale: [1, 1.5, 1], opacity: [0.5, 0, 0.5] }}
                transition={{ duration: 2, repeat: Infinity }}
              />
            </motion.div>

            {hoveredTime && (
              <motion.div
                className="absolute -top-8 px-2 py-1 bg-popover text-popover-foreground text-xs rounded shadow-lg whitespace-nowrap pointer-events-none"
                style={{ left: `${hoverPosition}%`, transform: "translateX(-50%)" }}
                initial={{ opacity: 0, y: 5 }}
                animate={{ opacity: 1, y: 0 }}
              >
                {hoveredTime}
              </motion.div>
            )}
          </div>

          <div className="flex justify-between mt-1 text-xs text-muted-foreground">
            <span>72 saat önce</span>
            <span>48 saat</span>
            <span>24 saat</span>
            <span>Şimdi</span>
          </div>
        </div>

        <div className="flex items-center gap-1">
          {[1, 2, 4].map((s) => (
            <motion.button
              key={s}
              className={cn(
                "px-2 py-1 text-xs font-medium rounded-md transition-colors",
                speed === s
                  ? "bg-primary text-primary-foreground"
                  : "bg-secondary text-secondary-foreground hover:bg-secondary/80",
              )}
              onClick={() => setSpeed(s)}
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              {s}x
            </motion.button>
          ))}
        </div>
      </div>
    </motion.div>
  )
}
