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
import { CATEGORIES } from '../utils/datasetFilters'

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
            className="text-xs font-semibold text-indigo-600 dark:text-indigo-400 hover:underline"
          >
            Show All Categories
          </button>
        )}
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4" role="group" aria-label="Dataset categories">
        {CATEGORIES.map((cat) => {
          const Icon = CATEGORY_ICONS[cat.id] || Layers
          const isActive = activeCategory === cat.id
          const count = categoryCounts[cat.id] ?? 0

          return (
            <button
              key={cat.id}
              type="button"
              aria-pressed={isActive}
              onClick={() => onSelectCategory(isActive ? null : cat.id)}
              className={`p-4 rounded-xl border text-left transition-all flex flex-col justify-between cursor-pointer focus:outline-hidden focus:ring-2 focus:ring-indigo-500 ${
                isActive
                  ? 'border-indigo-600 bg-indigo-50/70 dark:bg-indigo-950/40 dark:border-indigo-500 shadow-xs'
                  : 'border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/50 hover:border-slate-300 dark:hover:border-slate-700'
              }`}
            >
              <div>
                <div className="flex items-center justify-between mb-2">
                  <div
                    className={`w-9 h-9 rounded-lg flex items-center justify-center transition-colors ${
                      isActive
                        ? 'bg-indigo-600 text-white'
                        : 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300'
                    }`}
                  >
                    <Icon className="w-4 h-4" />
                  </div>
                  <div className="flex items-center gap-1.5">
                    {isActive && (
                      <span className="flex items-center justify-center w-5 h-5 rounded-full bg-indigo-600 text-white text-[10px]">
                        <Check className="w-3 h-3" />
                      </span>
                    )}
                    <span
                      className={`text-xs font-bold px-2 py-0.5 rounded-full ${
                        count > 0
                          ? 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900/60 dark:text-indigo-300'
                          : 'bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-500'
                      }`}
                    >
                      {count} {count === 1 ? 'dataset' : 'datasets'}
                    </span>
                  </div>
                </div>
                <h3 className="font-bold text-slate-900 dark:text-white text-base">
                  {cat.name}
                </h3>
                <p className="mt-1 text-xs text-slate-500 dark:text-slate-400 line-clamp-2">
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
