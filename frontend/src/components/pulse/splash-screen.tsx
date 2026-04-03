'use client'

import { AnimatePresence, motion } from 'framer-motion'
import { useEffect, useState } from 'react'

interface SplashScreenProps {
  onComplete?: () => void
}

export function SplashScreen({ onComplete }: SplashScreenProps) {
  const [progress, setProgress] = useState(0)
  const [loadingText, setLoadingText] = useState('Sistem baslatiliyor')
  const [isComplete, setIsComplete] = useState(false)

  useEffect(() => {
    const texts = [
      'Sistem baslatiliyor',
      'Veri kaynaklari baglaniyor',
      'Harita yukleniyor',
      'Canli akis hazirlaniyor',
      'PULSE hazir',
    ]

    const interval = window.setInterval(() => {
      setProgress((prev) => {
        const newProgress = Math.min(prev + Math.random() * 15 + 5, 100)

        const textIndex = Math.min(
          Math.floor((newProgress / 100) * texts.length),
          texts.length - 1,
        )
        setLoadingText(texts[textIndex])

        if (newProgress >= 100) {
          window.clearInterval(interval)
          window.setTimeout(() => {
            setIsComplete(true)
            window.setTimeout(() => onComplete?.(), 450)
          }, 450)
        }

        return newProgress
      })
    }, 200)

    return () => window.clearInterval(interval)
  }, [onComplete])

  return (
    <AnimatePresence>
      {!isComplete && (
        <motion.div
          className="fixed inset-0 z-[120] flex items-center justify-center bg-background"
          initial={{ opacity: 1 }}
          exit={{ opacity: 0, scale: 1.06, filter: 'blur(8px)' }}
          transition={{ duration: 0.45 }}
        >
          <div className="flex flex-col items-center">
            <motion.div
              className="relative mb-8 h-32 w-32"
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ type: 'spring', stiffness: 200, damping: 15 }}
            >
              <motion.div
                className="absolute inset-0"
                animate={{ rotate: 360 }}
                transition={{ duration: 8, repeat: Infinity, ease: 'linear' }}
              >
                <svg viewBox="0 0 128 128" className="h-full w-full">
                  <circle
                    cx="64"
                    cy="64"
                    r="60"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1"
                    strokeDasharray="8 8"
                    className="text-border"
                  />
                </svg>
              </motion.div>

              <svg viewBox="0 0 128 128" className="absolute inset-0 h-full w-full">
                <motion.circle
                  cx="64"
                  cy="64"
                  r="50"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="3"
                  className="text-primary"
                  initial={{ pathLength: 0 }}
                  animate={{ pathLength: progress / 100 }}
                  transition={{ duration: 0.3 }}
                  strokeLinecap="round"
                  transform="rotate(-90 64 64)"
                />
              </svg>

              {[0, 1, 2].map((i) => (
                <motion.div
                  key={i}
                  className="absolute inset-0 flex items-center justify-center"
                  initial={{ scale: 0.5, opacity: 0 }}
                  animate={{ scale: [0.5, 1.2], opacity: [0.6, 0] }}
                  transition={{
                    duration: 2,
                    repeat: Infinity,
                    delay: i * 0.6,
                    ease: 'easeOut',
                  }}
                >
                  <div className="h-16 w-16 rounded-full border-2 border-primary" />
                </motion.div>
              ))}

              <div className="absolute inset-0 flex items-center justify-center">
                <motion.div
                  className="text-3xl font-bold text-primary"
                  animate={{ scale: [1, 1.1, 1] }}
                  transition={{ duration: 1.5, repeat: Infinity }}
                >
                  {Math.round(progress)}
                </motion.div>
              </div>
            </motion.div>

            <motion.h1
              className="mb-4 text-4xl font-bold tracking-wider"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.25 }}
            >
              {'PULSE'.split('').map((letter, i) => (
                <motion.span
                  key={i}
                  className="inline-block text-foreground"
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.25 + i * 0.08 }}
                >
                  {letter}
                </motion.span>
              ))}
            </motion.h1>

            <motion.p
              className="mb-8 text-sm text-muted-foreground"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.7 }}
            >
              Kocaeli Sehir Istihbarat Platformu
            </motion.p>

            <motion.div
              className="h-1 w-64 overflow-hidden rounded-full bg-secondary"
              initial={{ opacity: 0, width: 0 }}
              animate={{ opacity: 1, width: 256 }}
              transition={{ delay: 0.45 }}
            >
              <motion.div
                className="h-full rounded-full bg-primary"
                initial={{ width: 0 }}
                animate={{ width: `${progress}%` }}
                transition={{ duration: 0.3 }}
              />
            </motion.div>

            <motion.p
              className="mt-4 text-sm text-muted-foreground"
              key={loadingText}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
            >
              {loadingText}
              <motion.span
                animate={{ opacity: [0, 1, 0] }}
                transition={{ duration: 1, repeat: Infinity }}
              >
                ...
              </motion.span>
            </motion.p>
          </div>

          <div className="pointer-events-none absolute inset-0 overflow-hidden">
            <motion.div
              className="absolute inset-0 opacity-5"
              style={{
                backgroundImage:
                  'linear-gradient(to right, currentColor 1px, transparent 1px), linear-gradient(to bottom, currentColor 1px, transparent 1px)',
                backgroundSize: '50px 50px',
              }}
              animate={{ backgroundPosition: ['0px 0px', '50px 50px'] }}
              transition={{ duration: 20, repeat: Infinity, ease: 'linear' }}
            />
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
