import React from 'react'
import { Link } from 'react-router-dom'
import { X, ArrowRight, Layers } from 'lucide-react'
import type { DatasetMetadata } from '../types/dataset'
import {
  MAX_COMPARE_COUNT,
  MIN_COMPARE_COUNT,
  buildCompareUrl,
} from '../utils/comparisonUtils'

export interface CategoryCompareToolbarProps {
  selectedSlugs: string[]
  catalog?: DatasetMetadata[]
  onRemoveSlug: (slug: string) => void
  onClear: () => void
  onExit?: () => void
}

export const CategoryCompareToolbar: React.FC<CategoryCompareToolbarProps> = ({
  selectedSlugs,
  catalog = [],
  onRemoveSlug,
  onClear,
  onExit,
}) => {
  const canCompare = selectedSlugs.length >= MIN_COMPARE_COUNT
  const compareUrl = buildCompareUrl(selectedSlugs)

  const getDatasetName = (slug: string): string => {
    const dataset = catalog.find((d) => d.slug === slug)
    return dataset?.name || slug
  }

  return (
    <div
      role="region"
      aria-label="Category dataset comparison toolbar"
      className="mb-6 rounded-xl border border-indigo-200 dark:border-indigo-800/80 bg-indigo-50/60 dark:bg-indigo-950/30 p-3.5 sm:px-4 sm:py-3 transition-colors"
    >
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-3">
        {/* Selection summary and item chips */}
        <div className="flex items-center gap-2 flex-wrap min-w-0">
          <div className="flex items-center gap-1.5 text-xs font-bold text-indigo-900 dark:text-indigo-200 shrink-0">
            <Layers className="w-4 h-4 text-indigo-600 dark:text-indigo-400" />
            <span>Compare Mode:</span>
            <span className="font-semibold text-slate-600 dark:text-slate-400">
              {`${selectedSlugs.length} of ${MAX_COMPARE_COUNT} selected`}
            </span>
          </div>

          {selectedSlugs.length > 0 ? (
            <div className="flex items-center gap-1.5 flex-wrap">
              {selectedSlugs.map((slug) => {
                const name = getDatasetName(slug)
                return (
                  <span
                    key={slug}
                    className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-md text-xs font-medium bg-white dark:bg-slate-900 text-indigo-950 dark:text-indigo-200 border border-indigo-200 dark:border-indigo-800 shadow-2xs max-w-[180px]"
                  >
                    <span className="truncate" title={name}>
                      {name}
                    </span>
                    <button
                      type="button"
                      onClick={() => onRemoveSlug(slug)}
                      aria-label={`Remove ${name} from comparison`}
                      className="p-0.5 hover:bg-slate-100 dark:hover:bg-slate-800 rounded text-slate-400 hover:text-rose-600 dark:hover:text-rose-400 transition-colors cursor-pointer"
                    >
                      <X className="w-3 h-3" />
                    </button>
                  </span>
                )
              })}
            </div>
          ) : (
            <span className="text-xs text-slate-500 italic ml-1">
              Select 2 or 3 datasets below to compare
            </span>
          )}
        </div>

        {/* Action buttons */}
        <div className="flex items-center gap-2 self-end md:self-auto shrink-0">
          <button
            type="button"
            onClick={onClear}
            disabled={selectedSlugs.length === 0}
            aria-label="Clear selection"
            className={`px-2.5 py-1.5 text-xs font-medium transition-colors ${
              selectedSlugs.length === 0
                ? 'text-slate-400 dark:text-slate-600 cursor-not-allowed'
                : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white cursor-pointer'
            }`}
          >
            Clear selection
          </button>

          {canCompare ? (
            <Link
              to={compareUrl}
              className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 active:bg-indigo-800 text-white text-xs font-semibold shadow-xs hover:shadow-md transition-all cursor-pointer focus:outline-hidden focus-visible:ring-2 focus-visible:ring-indigo-500"
            >
              <span>{`Compare Selected (${selectedSlugs.length})`}</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          ) : (
            <button
              type="button"
              disabled
              title="Select at least 2 datasets to compare"
              className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-slate-100 dark:bg-slate-800 text-slate-400 dark:text-slate-500 text-xs font-semibold cursor-not-allowed border border-slate-200 dark:border-slate-700"
            >
              <span>Compare Selected</span>
            </button>
          )}

          {onExit && (
            <button
              type="button"
              onClick={onExit}
              className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 text-xs font-medium transition-colors cursor-pointer"
            >
              <span>Exit Compare</span>
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
