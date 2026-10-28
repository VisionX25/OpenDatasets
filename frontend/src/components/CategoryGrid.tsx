import React from 'react'
import {
  Image,
  FileText,
  Volume2,
  Table,
  Cpu,
  Layers,
  Check,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import type { CategoryId } from '../types/dataset'
import { CATEGORIES, CATEGORY_ACCENTS } from '../utils/datasetFilters'

interface CategoryGridProps {
  activeCategory: CategoryId | null
  onSelectCategory: (categoryId: CategoryId | null) => void
  categoryCounts: Record<CategoryId, number>
}

const CATEGORY_ICONS: Record<CategoryId, LucideIcon> = {
  'computer-vision': Image,
  'natural-language-processing': FileText,
  'audio-speech': Volume2,
  'tabular-time-series': Table,
  'multimodal-generative': Cpu,
  'evaluation-benchmarks': Layers,
}

export const CategoryGrid: React.FC<CategoryGridProps> = ({
  activeCategory,
  onSelectCategory,
  categoryCounts,
}) => {
  const hasSelection = activeCategory !== null

  return (
    <div className="mb-10">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-lg font-bold text-slate-900 dark:text-white">
            Explore by Category
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            Select a modality or purpose to narrow down datasets
          </p>
        </div>
        {activeCategory && (
          <button
            type="button"
            onClick={() => onSelectCategory(null)}
            className="text-xs font-semibold text-indigo-600 dark:text-indigo-400 hover:underline cursor-pointer focus:outline-hidden focus-visible:ring-2 focus-visible:ring-indigo-500 rounded"
          >
            Show All Categories
          </button>
        )}
      </div>

      <div
        className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4"
        role="group"
        aria-label="Dataset categories"
      >
        {CATEGORIES.map((cat) => {
          const Icon = CATEGORY_ICONS[cat.id] || Layers
          const isActive = activeCategory === cat.id
          const isDimmed = hasSelection && !isActive
          const accent = CATEGORY_ACCENTS[cat.id]
          const count = categoryCounts[cat.id] ?? 0

          return (
            <button
              key={cat.id}
              type="button"
              data-testid={`category-card-${cat.id}`}
              data-category-id={cat.id}
              data-active={isActive ? 'true' : 'false'}
              aria-pressed={isActive}
              onClick={() => onSelectCategory(isActive ? null : cat.id)}
              className={`group p-4 rounded-xl text-left transition-all duration-200 motion-reduce:transition-none flex flex-col justify-between cursor-pointer focus:outline-hidden focus-visible:ring-2 ${accent.focusRing} ${
                isActive
                  ? `border ${accent.selectedCardBorder} ${accent.selectedCardBg} shadow-xs`
                  : isDimmed
                    ? `border border-slate-200/80 dark:border-slate-800/80 bg-white/70 dark:bg-slate-900/40 opacity-75 hover:opacity-100 ${accent.hoverCardBorder} ${accent.hoverCardBg} focus-visible:opacity-100`
                    : `border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/50 opacity-100 ${accent.hoverCardBorder} ${accent.hoverCardBg}`
              }`}
            >
              <div>
                <div className="flex items-center justify-between mb-2">
                  <div
                    className={`w-9 h-9 rounded-lg flex items-center justify-center transition-all duration-200 motion-reduce:transition-none ${
                      isActive
                        ? accent.selectedIconBg
                        : `bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 ${accent.hoverIconBg}`
                    }`}
                  >
                    <Icon className="w-4 h-4" />
                  </div>
                  <div className="flex items-center gap-1.5">
                    {isActive && (
                      <span
                        aria-hidden="true"
                        className={`flex items-center justify-center w-5 h-5 rounded-full ${accent.selectedCheckBg} text-[10px] shadow-2xs`}
                      >
                        <Check className="w-3 h-3 text-white" strokeWidth={2.5} />
                      </span>
                    )}
                    <span
                      className={`text-xs font-bold px-2 py-0.5 rounded-full transition-colors ${
                        isActive
                          ? accent.selectedBadge
                          : count > 0
                            ? 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300'
                            : 'bg-slate-100 text-slate-400 dark:bg-slate-800/60 dark:text-slate-500'
                      }`}
                    >
                      {count} {count === 1 ? 'dataset' : 'datasets'}
                    </span>
                  </div>
                </div>
                <h3 className="font-bold text-slate-900 dark:text-white text-base">
                  {cat.name}
                </h3>
                <p
                  className={`mt-1 text-xs line-clamp-2 ${
                    isActive
                      ? 'text-slate-600 dark:text-slate-300'
                      : 'text-slate-500 dark:text-slate-400'
                  }`}
                >
                  {cat.description}
                </p>
              </div>
            </button>
          )
        })}
      </div>
    </div>
  )
}
