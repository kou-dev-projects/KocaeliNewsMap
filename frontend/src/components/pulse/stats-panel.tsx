"use client";

import { motion } from "framer-motion";
import { Activity, BarChart3, Clock, MapPin } from "lucide-react";

interface StatsPanelProps {
  totalNews: number;
  liveCount: number;
  topDistrict: string;
  avgNewsPerHour: number;
  hidden?: boolean;
}

const CARD_CONFIG = [
  {
    key: "total",
    label: "Aktif Gorunum",
    icon: BarChart3,
    color: "text-primary",
    bgColor: "bg-primary/10",
  },
  {
    key: "live",
    label: "Son 6 Saat",
    icon: Activity,
    color: "text-emerald-500",
    bgColor: "bg-emerald-500/10",
  },
  {
    key: "district",
    label: "Yogun Bolge",
    icon: MapPin,
    color: "text-amber-500",
    bgColor: "bg-amber-500/10",
  },
  {
    key: "cadence",
    label: "Saatlik Tempo",
    icon: Clock,
    color: "text-sky-500",
    bgColor: "bg-sky-500/10",
  },
] as const;

export function StatsPanel({
  totalNews,
  liveCount,
  topDistrict,
  avgNewsPerHour,
  hidden = false,
}: StatsPanelProps) {
  const cards = [
    {
      ...CARD_CONFIG[0],
      value: totalNews.toLocaleString("tr-TR"),
      helper: "Filtrelenen haber",
    },
    {
      ...CARD_CONFIG[1],
      value: liveCount.toLocaleString("tr-TR"),
      helper: "Yeni haber hacmi",
    },
    {
      ...CARD_CONFIG[2],
      value: topDistrict,
      helper: "En yogun ilce",
    },
    {
      ...CARD_CONFIG[3],
      value: avgNewsPerHour.toLocaleString("tr-TR"),
      helper: "Ortalama saatlik akis",
    },
  ];

  return (
    <motion.div
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: hidden ? 0 : 1, y: hidden ? -8 : 0, pointerEvents: hidden ? "none" : "auto" }}
      transition={{ delay: 0.5 }}
      className="absolute right-4 top-36 z-10 hidden xl:block"
    >
      <div className="w-64 space-y-3 rounded-xl glass p-4">
        <div className="mb-4 flex items-center justify-between">
          <span className="text-sm font-semibold text-foreground">Gorunum Ozeti</span>
          <motion.div
            className="h-2 w-2 rounded-full bg-emerald-500"
            animate={{ scale: [1, 1.2, 1], opacity: [1, 0.7, 1] }}
            transition={{ duration: 1, repeat: Infinity }}
          />
        </div>

        {cards.map((card, index) => {
          const Icon = card.icon;

          return (
            <motion.div
              key={card.key}
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.6 + index * 0.08 }}
              className="rounded-lg bg-secondary/30 p-3 transition-colors hover:bg-secondary/50"
            >
              <div className="flex items-center gap-3">
                <div className={`flex h-9 w-9 items-center justify-center rounded-lg ${card.bgColor}`}>
                  <Icon className={`h-4 w-4 ${card.color}`} />
                </div>
                <div className="min-w-0">
                  <p className="text-xs text-muted-foreground">{card.label}</p>
                  <p className="truncate font-semibold text-foreground">{card.value}</p>
                </div>
              </div>
              <p className="mt-2 text-[11px] uppercase tracking-[0.14em] text-muted-foreground">
                {card.helper}
              </p>
            </motion.div>
          );
        })}
      </div>
    </motion.div>
  );
}
