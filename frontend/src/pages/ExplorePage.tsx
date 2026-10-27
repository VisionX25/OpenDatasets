import React, { useEffect, useState, useMemo } from 'react'
import {
  Search,
  Filter,
  Layers,
  X,
  RotateCcw,
  Loader2,
  AlertTriangle,
} from 'lucide-react'
import type { CategoryId, DatasetMetadata } from '../types/dataset'
import { fetchCatalog } from '../services/catalogService'
import {
  countDatasetsPerCategory,
  filterDatasets,
  getAvailableModalities,
  getAvailableTasks,
  CATEGORIES,
} from '../utils/datasetFilters'
import { CategoryGrid } from '../components/CategoryGrid'
import { DatasetCard } from '../components/DatasetCard'

export const ExplorePage: React.FC = () => {
  const [datasets, setDatasets] = useState<DatasetMetadata[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Filters state
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedCategory, setSelectedCategory] = useState<CategoryId | null>(null)
  const [selectedModality, setSelectedModality] = useState<string>('')
  const [selectedTask, setSelectedTask] = useState<string>('')

  useEffect(() => {
    let ignore = false
    fetchCatalog()
      .then((data) => {
        if (!ignore) {
          setDatasets(data)
          setLoading(false)
        }
      })
      .catch((err) => {
        if (!ignore) {
          setError(err instanceof Error ? err.message : 'Failed to load dataset catalog.')
          setLoading(false)
        }
      })
    return () => {
      ignore = true
    }
  }, [])

  const handleRetry = () => {
    setLoading(true)
    setError(null)
    fetchCatalog()
      .then((data) => {
        setDatasets(data)
        setLoading(false)
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : 'Failed to load dataset catalog.')
        setLoading(false)
      })
  }

  // Derived available filter options based on full catalog
  const availableModalities = useMemo(() => getAvailableModalities(datasets), [datasets])
  const availableTasks = useMemo(() => getAvailableTasks(datasets), [datasets])
  const categoryCounts = useMemo(() => countDatasetsPerCategory(datasets), [datasets])

  // Filtered dataset result
  const filteredDatasets = useMemo(() => {
    return filterDatasets(datasets, {
      searchQuery,
      category: selectedCategory,
      modality: selectedModality || null,
      task: selectedTask || null,
    })
  }, [datasets, searchQuery, selectedCategory, selectedModality, selectedTask])

  const hasActiveFilters = Boolean(
    searchQuery.trim() || selectedCategory || selectedModality || selectedTask,
  )

  const handleResetFilters = () => {
    setSearchQuery('')
    setSelectedCategory(null)
    setSelectedModality('')
    setSelectedTask('')
  }

  const activeCategoryName = selectedCategory
    ? CATEGORIES.find((c) => c.id === selectedCategory)?.name
    : null

  return (
    <div className="flex-1 py-8 md:py-12">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Page Header */}
        <div className="border-b border-slate-200 dark:border-slate-800 pb-6 mb-8">
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-indigo-600 dark:text-indigo-400 mb-2">
            <Layers className="w-4 h-4" />
            <span>Dataset Catalog</span>
          </div>
          <h1 className="text-3xl sm:text-4xl font-extrabold text-slate-900 dark:text-white tracking-tight">
            Explore Datasets
          </h1>
          <p className="mt-2 text-base text-slate-600 dark:text-slate-400 max-w-3xl">
            Discover verified Machine Learning datasets across computer vision, NLP, tabular data, and evaluation benchmarks.
          </p>
        </div>

        {/* Loading state */}
        {loading && (
          <div className="py-20 flex flex-col items-center justify-center text-center">
            <Loader2 className="w-8 h-8 text-indigo-600 animate-spin mb-4" />
            <p className="text-sm font-medium text-slate-600 dark:text-slate-400">
              Loading dataset catalog...
            </p>
          </div>
        )}

        {/* Error state */}
        {!loading && error && (
          <div className="rounded-xl border border-rose-200 dark:border-rose-900/60 bg-rose-50/50 dark:bg-rose-950/20 p-6 text-center my-8">
            <AlertTriangle className="w-8 h-8 text-rose-500 mx-auto mb-2" />
            <h2 className="text-base font-bold text-slate-900 dark:text-white">
              Unable to Load Catalog
            </h2>
            <p className="text-sm text-rose-600 dark:text-rose-400 mt-1 max-w-md mx-auto">
              {error}
            </p>
            <button
              type="button"
              onClick={handleRetry}
              className="mt-4 inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-rose-600 hover:bg-rose-700 text-white text-xs font-semibold transition-colors"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>Retry</span>
            </button>
          </div>
        )}

        {/* Main Content when loaded */}
        {!loading && !error && (
          <>
            {/* Category Cards Section */}
            <CategoryGrid
              activeCategory={selectedCategory}
              onSelectCategory={setSelectedCategory}
              categoryCounts={categoryCounts}
            />

            {/* Search and Filters Controls */}
            <div className="bg-white dark:bg-slate-900/80 rounded-xl border border-slate-200 dark:border-slate-800 p-4 sm:p-5 mb-6 shadow-xs">
              <div className="flex flex-col md:flex-row gap-3">
                {/* Search Input */}
                <div className="relative flex-1">
                  <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Search by dataset name, description, publisher, task, or tag..."
                    aria-label="Search datasets"
                    className="w-full pl-10 pr-9 py-2.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 text-sm text-slate-900 dark:text-slate-100 placeholder:text-slate-400 focus:outline-hidden focus:ring-2 focus:ring-indigo-500 transition-colors"
                  />
                  {searchQuery && (
                    <button
                      type="button"
                      onClick={() => setSearchQuery('')}
                      aria-label="Clear search input"
                      className="absolute right-3 top-1/2 -translate-y-1/2 p-1 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 rounded"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  )}
                </div>

                {/* Modality Filter */}
                <div className="w-full md:w-48">
                  <div className="relative">
                    <select
                      value={selectedModality}
                      onChange={(e) => setSelectedModality(e.target.value)}
                      aria-label="Filter by modality"
                      className="w-full px-3 py-2.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 text-sm text-slate-700 dark:text-slate-200 focus:outline-hidden focus:ring-2 focus:ring-indigo-500 appearance-none pr-8 cursor-pointer"
                    >
                      <option value="">All Modalities</option>
                      {availableModalities.map((mod) => (
                        <option key={mod} value={mod}>
                          {mod.charAt(0).toUpperCase() + mod.slice(1)}
                        </option>
                      ))}
                    </select>
                    <Filter className="absolute right-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-400 pointer-events-none" />
                  </div>
                </div>

                {/* Task Filter */}
                <div className="w-full md:w-48">
                  <div className="relative">
                    <select
                      value={selectedTask}
                      onChange={(e) => setSelectedTask(e.target.value)}
                      aria-label="Filter by ML task"
                      className="w-full px-3 py-2.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 text-sm text-slate-700 dark:text-slate-200 focus:outline-hidden focus:ring-2 focus:ring-indigo-500 appearance-none pr-8 cursor-pointer"
                    >
                      <option value="">All ML Tasks</option>
                      {availableTasks.map((t) => (
                        <option key={t} value={t}>
                          {t}
                        </option>
                      ))}
                    </select>
                    <Filter className="absolute right-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-400 pointer-events-none" />
                  </div>
                </div>

                {/* Reset Filters Button */}
                {hasActiveFilters && (
                  <button
                    type="button"
                    onClick={handleResetFilters}
                    className="inline-flex items-center justify-center gap-1.5 px-3 py-2.5 rounded-lg border border-slate-300 dark:border-slate-700 text-sm font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors shrink-0"
                  >
                    <RotateCcw className="w-3.5 h-3.5" />
                    <span>Reset</span>
                  </button>
                )}
              </div>

              {/* Active Filter Pills Indicator */}
              {hasActiveFilters && (
                <div className="flex items-center gap-2 flex-wrap pt-3 mt-3 border-t border-slate-100 dark:border-slate-800/80 text-xs">
                  <span className="text-slate-500 font-medium">Active filters:</span>
                  {activeCategoryName && (
                    <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-indigo-100 text-indigo-800 dark:bg-indigo-950/70 dark:text-indigo-300">
                      Category: {activeCategoryName}
                      <button
                        type="button"
                        onClick={() => setSelectedCategory(null)}
                        aria-label={`Remove ${activeCategoryName} category filter`}
                        className="hover:text-indigo-950 dark:hover:text-white"
                      >
                        <X className="w-3 h-3" />
                      </button>
                    </span>
                  )}
                  {searchQuery && (
                    <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-slate-200 text-slate-800 dark:bg-slate-800 dark:text-slate-200">
                      Search: &ldquo;{searchQuery}&rdquo;
                      <button
                        type="button"
                        onClick={() => setSearchQuery('')}
                        aria-label="Remove search query filter"
                        className="hover:text-slate-950 dark:hover:text-white"
                      >
                        <X className="w-3 h-3" />
                      </button>
                    </span>
                  )}
                  {selectedModality && (
                    <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-indigo-100 text-indigo-800 dark:bg-indigo-950/70 dark:text-indigo-300">
                      Modality: {selectedModality}
                      <button
                        type="button"
                        onClick={() => setSelectedModality('')}
                        aria-label="Remove modality filter"
                        className="hover:text-indigo-950 dark:hover:text-white"
                      >
                        <X className="w-3 h-3" />
                      </button>
                    </span>
                  )}
                  {selectedTask && (
                    <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-indigo-100 text-indigo-800 dark:bg-indigo-950/70 dark:text-indigo-300">
                      Task: {selectedTask}
                      <button
                        type="button"
                        onClick={() => setSelectedTask('')}
                        aria-label="Remove task filter"
                        className="hover:text-indigo-950 dark:hover:text-white"
                      >
                        <X className="w-3 h-3" />
                      </button>
                    </span>
                  )}
                </div>
              )}
            </div>

            {/* Results Count Header */}
            <div className="flex items-center justify-between mb-4">
              <p className="text-sm text-slate-600 dark:text-slate-400">
                Showing{' '}
                <span className="font-bold text-slate-900 dark:text-white">
                  {filteredDatasets.length}
                </span>{' '}
                of{' '}
                <span className="font-bold text-slate-900 dark:text-white">
                  {datasets.length}
                </span>{' '}
                datasets
              </p>
            </div>

            {/* Empty State */}
            {filteredDatasets.length === 0 && (
              <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/40 p-12 text-center my-6">
                <Search className="w-10 h-10 text-slate-400 mx-auto mb-3 opacity-60" />
                <h3 className="text-lg font-bold text-slate-900 dark:text-white">
                  No Datasets Found
                </h3>
                <p className="text-sm text-slate-500 dark:text-slate-400 mt-1 max-w-md mx-auto leading-relaxed">
                  No datasets match your active search and filter settings. Try adjusting your query or resetting all filters.
                </p>
                <button
                  type="button"
                  onClick={handleResetFilters}
                  className="mt-5 inline-flex items-center gap-2 px-4 py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold shadow-xs transition-colors"
                >
                  <RotateCcw className="w-3.5 h-3.5" />
                  <span>Reset All Filters</span>
                </button>
              </div>
            )}

            {/* Dataset Cards Grid */}
            {filteredDatasets.length > 0 && (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {filteredDatasets.map((dataset) => (
                  <DatasetCard key={dataset.id} dataset={dataset} />
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
