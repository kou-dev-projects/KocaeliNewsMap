"use client"

import type { ReactNode } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { cn } from "@/lib/utils"
import { Check } from "lucide-react"

export interface PulseCategoryOption {
  id: string
  label: string
  icon: ReactNode
  color: string
}

interface CategoryFilterProps {
  selected: string[]
  onChange: (categories: string[]) => void
  options: PulseCategoryOption[]
}

export function CategoryFilter({ selected, onChange, options }: CategoryFilterProps) {
  const toggleCategory = (category: string) => {
    if (selected.includes(category)) {
      if (selected.length === 1) {
        return
      }
      onChange(selected.filter((c) => c !== category))
    } else {
      onChange([...selected, category])
    }
  }

  const selectAll = () => {
    onChange(options.map((c) => c.id))
  }

  return (
    <motion.div
      className="flex flex-wrap items-center gap-2"
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ staggerChildren: 0.05 }}
    >
      <motion.button
        type="button"
        className={cn(
          "px-3 py-1.5 rounded-full text-sm font-medium transition-all",
          "border border-border",
          selected.length === options.length
            ? "bg-primary text-primary-foreground border-primary"
            : "bg-card text-card-foreground hover:bg-secondary",
        )}
        onClick={selectAll}
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
        initial={{ opacity: 0, scale: 0.8 }}
        animate={{ opacity: 1, scale: 1 }}
      >
        Tümü
      </motion.button>

      {options.map((category, index) => {
        const isSelected = selected.includes(category.id)

        return (
          <motion.button
            key={category.id}
            type="button"
            className={cn(
              "relative px-3 py-1.5 rounded-full text-sm font-medium transition-all overflow-hidden",
              "border",
              isSelected
                ? `${category.color} text-white border-transparent`
                : "bg-card text-card-foreground border-border hover:bg-secondary",
            )}
            onClick={() => toggleCategory(category.id)}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            initial={{ opacity: 0, scale: 0.8, x: -20 }}
            animate={{ opacity: 1, scale: 1, x: 0 }}
            transition={{ delay: index * 0.05 }}
          >
            <AnimatePresence>
              {isSelected && (
                <motion.div
                  className={cn("absolute inset-0", category.color)}
                  initial={{ scale: 0, borderRadius: "100%" }}
                  animate={{ scale: 1, borderRadius: "0%" }}
                  exit={{ scale: 0, borderRadius: "100%" }}
                  transition={{ duration: 0.3 }}
                />
              )}
            </AnimatePresence>

            <span className="relative flex items-center gap-1.5">
              <motion.span
                initial={false}
                animate={{
                  rotate: isSelected ? [0, -10, 10, -10, 0] : 0,
                  scale: isSelected ? [1, 1.2, 1] : 1,
                }}
                transition={{ duration: 0.4 }}
              >
                {category.icon}
              </motion.span>
              <span>{category.label}</span>

              <AnimatePresence>
                {isSelected && (
                  <motion.span
                    initial={{ scale: 0, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    exit={{ scale: 0, opacity: 0 }}
                    transition={{ type: "spring", stiffness: 500, damping: 20 }}
                  >
                    <Check className="w-3 h-3" />
                  </motion.span>
                )}
              </AnimatePresence>
            </span>
          </motion.button>
        )
      })}

      <motion.span
        className="text-sm text-muted-foreground ml-2"
        key={selected.length}
        initial={{ scale: 0.8, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ type: "spring", stiffness: 400 }}
      >
        {selected.length} / {options.length} aktif
      </motion.span>
    </motion.div>
  )
}
