import React, { useEffect, useState, useMemo, useCallback } from 'react'
import { useParams, useSearchParams, Link } from 'react-router-dom'
import {
  Search,
  Filter,
  Layers,
  X,
  RotateCcw,
  Loader2,
  AlertTriangle,
  ChevronRight,
  Calendar,
  ArrowUp,
} from 'lucide-react'
import type { DatasetMetadata, LicenseStatus, CategoryId } from '../types/dataset'
import { fetchCatalog } from '../services/catalogService'
import {
  filterDatasets,
  getAvailableModalities,
  getAvailableTasks,
  getAvailableLicenseStatuses,
  getAvailablePublicationYears,
  formatLicenseLabel,
  parseFilterParams,
  serializeFilterParams,
  CATEGORIES,
  CATEGORY_ACCENTS,
  isCategoryId,
  getCategoryById,
} from '../utils/datasetFilters'
import type { FilterState } from '../utils/datasetFilters'
import { DatasetCard } from '../components/DatasetCard'

const PAGE_SIZE = 24

export const DatasetsPage: React.FC = () => {
  const params = useParams<{ categorySlug?: string; param?: string }>()
  const rawCategorySlug = params.categorySlug || params.param
  const isCategoryScoped = Boolean(rawCategorySlug)
  const isValidCategory = isCategoryScoped ? isCategoryId(rawCategorySlug) : true
  const currentCategory = isCategoryScoped && isValidCategory ? getCategoryById(rawCategorySlug) : undefined
  const categoryAccent =
    isCategoryScoped && isValidCategory && rawCategorySlug
      ? CATEGORY_ACCENTS[rawCategorySlug as CategoryId]
      : undefined

  const [catalog, setCatalog] = useState<DatasetMetadata[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchParams, setSearchParams] = useSearchParams()

  const [visibleCount, setVisibleCount] = useState(PAGE_SIZE)

  // Accessible Back to Top control for long result pages
  const [showBackToTop, setShowBackToTop] = useState(false)

  useEffect(() => {
    const handleScroll = () => {
      setShowBackToTop(window.scrollY > 400)
    }
    window.addEventListener('scroll', handleScroll, { passive: true })
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

  const handleScrollToTop = () => {
    const isReducedMotion =
      typeof window !== 'undefined' &&
      window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
    window.scrollTo({ top: 0, behavior: isReducedMotion ? 'auto' : 'smooth' })
  }

  useEffect(() => {
    let ignore = false
    fetchCatalog()
      .then((data) => {
        if (!ignore) {
          setCatalog(data)
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
    fetchCatalog({ forceReload: true })
      .then((data) => {
        setCatalog(data)
        setLoading(false)
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : 'Failed to load dataset catalog.')
        setLoading(false)
      })
  }

  // Active filter state derived directly from URL search parameters
  const activeFilters = useMemo(() => parseFilterParams(searchParams), [searchParams])

  // Synchronize local search input state with URL parameter without cascading effect
  const [prevSearchQuery, setPrevSearchQuery] = useState(activeFilters.searchQuery)
  const [searchInput, setSearchInput] = useState(activeFilters.searchQuery)

  if (activeFilters.searchQuery !== prevSearchQuery) {
    setPrevSearchQuery(activeFilters.searchQuery)
    setSearchInput(activeFilters.searchQuery)
  }

  const updateFilters = useCallback(
    (updates: Partial<FilterState>, replace = false) => {
      setSearchParams(
        (prev) => serializeFilterParams({ ...parseFilterParams(prev), ...updates }, prev),
        { replace },
      )
    },
    [setSearchParams],
  )

  const handleSearchChange = (value: string) => {
    setSearchInput(value)
    updateFilters({ searchQuery: value }, true)
  }

  // Reset visibleCount whenever any filter or category context changes
  const filterKey = `${rawCategorySlug || ''}:${searchParams.toString()}`
  const [prevFilterKey, setPrevFilterKey] = useState(filterKey)

  if (filterKey !== prevFilterKey) {
    setPrevFilterKey(filterKey)
    setVisibleCount(PAGE_SIZE)
  }

  // Available filter facet options
  const availableModalities = useMemo(() => getAvailableModalities(catalog), [catalog])
  const availableTasks = useMemo(() => getAvailableTasks(catalog), [catalog])
  const availableLicenses = useMemo(() => getAvailableLicenseStatuses(catalog), [catalog])
  const availableYears = useMemo(() => getAvailablePublicationYears(catalog), [catalog])

  // Effective category constraint: locked to URL slug if scoped, otherwise from search params
  const effectiveCategory: CategoryId | null = isCategoryScoped
    ? (rawCategorySlug as CategoryId)
    : activeFilters.category

  // Filtered dataset result
  const filteredDatasets = useMemo(() => {
    return filterDatasets(catalog, {
      searchQuery: activeFilters.searchQuery,
      category: effectiveCategory,
      modality: activeFilters.modality || null,
      task: activeFilters.task || null,
      license: activeFilters.license || null,
      year: activeFilters.year || null,
    })
  }, [catalog, activeFilters, effectiveCategory])

  const displayedDatasets = useMemo(() => {
    return filteredDatasets.slice(0, visibleCount)
  }, [filteredDatasets, visibleCount])

  const hasActiveFilters = Boolean(
    activeFilters.searchQuery.trim() ||
      (!isCategoryScoped && activeFilters.category) ||
      activeFilters.modality ||
      activeFilters.task ||
      activeFilters.license ||
      activeFilters.year,
  )

  const handleResetFilters = useCallback(() => {
    setSearchParams((prev) =>
      serializeFilterParams(
        {
          searchQuery: '',
          category: isCategoryScoped ? null : null,
          modality: '',
          task: '',
          license: '',
          year: '',
        },
        prev,
      ),
    )
    setSearchInput('')
  }, [setSearchParams, isCategoryScoped])

  const activeCategoryName = !isCategoryScoped && activeFilters.category
    ? CATEGORIES.find((c) => c.id === activeFilters.category)?.name
    : null

  // Invalid Category State
  if (isCategoryScoped && !isValidCategory) {
    return (
      <div className="flex-1 py-16 px-4 max-w-3xl mx-auto text-center">
        <div className="w-14 h-14 rounded-2xl bg-amber-100 dark:bg-amber-950/60 text-amber-600 dark:text-amber-400 flex items-center justify-center mx-auto mb-4">
          <AlertTriangle className="w-7 h-7" />
        </div>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white">
          Category Not Found
        </h1>
        <p className="mt-2 text-sm text-slate-600 dark:text-slate-400 max-w-md mx-auto">
          The category &ldquo;{rawCategorySlug}&rdquo; does not exist in OpenDatasets.
        </p>
        <div className="mt-6 flex items-center justify-center gap-3">
          <Link
            to="/explore"
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-semibold transition-colors cursor-pointer"
          >
            <Layers className="w-4 h-4" />
            <span>Explore Categories</span>
          </Link>
          <Link
            to="/datasets"
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800 text-sm font-medium transition-colors cursor-pointer"
          >
            <span>Browse All Datasets</span>
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="flex-1 py-8 md:py-12">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header and Breadcrumbs */}
        <div className="border-b border-slate-200 dark:border-slate-800 pb-6 mb-8">
          <nav
            className="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400 mb-3"
            aria-label="Breadcrumb"
          >
            <Link
              to="/explore"
              className="hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors"
            >
              Explore
            </Link>
            <ChevronRight className="w-3.5 h-3.5 text-slate-400" />
            <span className="font-semibold text-slate-900 dark:text-white">
              {isCategoryScoped ? currentCategory?.name : 'All Datasets'}
            </span>
          </nav>

          {isCategoryScoped && currentCategory ? (
            <div>
              <div className="flex items-center gap-2 mb-2">
                <span
                  className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold ${categoryAccent?.selectedBadge || 'bg-indigo-100 text-indigo-800'}`}
                >
                  {categoryAccent?.colorName || 'Category'}
                </span>
                <span className="text-xs text-slate-500 dark:text-slate-400">
                  {filteredDatasets.length} {filteredDatasets.length === 1 ? 'dataset' : 'datasets'}
                </span>
              </div>
              <h1 className="text-3xl sm:text-4xl font-extrabold text-slate-900 dark:text-white tracking-tight">
                {currentCategory.name}
              </h1>
              <p className="mt-2 text-base text-slate-600 dark:text-slate-400 max-w-3xl">
                {currentCategory.description}
              </p>
            </div>
          ) : (
            <div>
              <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-indigo-600 dark:text-indigo-400 mb-2">
                <Layers className="w-4 h-4" />
                <span>Dataset Catalog</span>
              </div>
              <h1 className="text-3xl sm:text-4xl font-extrabold text-slate-900 dark:text-white tracking-tight">
                All Datasets
              </h1>
              <p className="mt-2 text-base text-slate-600 dark:text-slate-400 max-w-3xl">
                Browse dataset metadata across computer vision, NLP, audio, tabular, and benchmark domains. Check each record’s sources and access conditions.
              </p>
            </div>
          )}
        </div>

        {/* Loading State */}
        {loading && (
          <div className="py-20 flex flex-col items-center justify-center text-center">
            <Loader2 className="w-8 h-8 text-indigo-600 animate-spin mb-4" />
            <p className="text-sm font-medium text-slate-600 dark:text-slate-400">
              Loading dataset catalog...
            </p>
          </div>
        )}

        {/* Error State */}
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
              className="mt-4 inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-rose-600 hover:bg-rose-700 text-white text-xs font-semibold transition-colors cursor-pointer"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>Retry</span>
            </button>
          </div>
        )}

        {/* Search and Filters Controls */}
        {!loading && !error && (
          <>
            <div className="bg-white dark:bg-slate-900/80 rounded-xl border border-slate-200 dark:border-slate-800 p-4 sm:p-5 mb-8 shadow-xs">
              <div className="flex flex-col md:flex-row gap-3 flex-wrap">
                {/* Search Input */}
                <div className="relative flex-1 min-w-[200px]">
                  <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
                  <input
                    type="text"
                    value={searchInput}
                    onChange={(e) => handleSearchChange(e.target.value)}
                    placeholder={
                      isCategoryScoped
                        ? `Search within ${currentCategory?.name}...`
                        : 'Search by dataset name, description, publisher, task, or tag...'
                    }
                    aria-label={
                      isCategoryScoped
                        ? `Search within ${currentCategory?.name}`
                        : 'Search all datasets'
                    }
                    className="w-full pl-10 pr-9 py-2.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 text-sm text-slate-900 dark:text-slate-100 placeholder:text-slate-400 focus:outline-hidden focus:ring-2 focus:ring-indigo-500 transition-colors"
                  />
                  {searchInput && (
                    <button
                      type="button"
                      onClick={() => handleSearchChange('')}
                      aria-label="Clear search input"
                      className="absolute right-3 top-1/2 -translate-y-1/2 p-1 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 rounded cursor-pointer"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  )}
                </div>

                {/* Category Filter Dropdown (only shown on global /datasets) */}
                {!isCategoryScoped && (
                  <div className="w-full md:w-48">
                    <div className="relative">
                      <select
                        value={activeFilters.category || ''}
                        onChange={(e) =>
                          updateFilters({ category: (e.target.value as CategoryId) || null })
                        }
                        aria-label="Filter by category"
                        className="w-full px-3 py-2.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 text-sm text-slate-700 dark:text-slate-200 focus:outline-hidden focus:ring-2 focus:ring-indigo-500 appearance-none pr-8 cursor-pointer"
                      >
                        <option value="">All Categories</option>
                        {CATEGORIES.map((cat) => (
                          <option key={cat.id} value={cat.id}>
                            {cat.name}
                          </option>
                        ))}
                      </select>
                      <Filter className="absolute right-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-400 pointer-events-none" />
                    </div>
                  </div>
                )}

                {/* Modality Filter */}
                <div className="w-full md:w-44">
                  <div className="relative">
                    <select
                      value={activeFilters.modality}
                      onChange={(e) => updateFilters({ modality: e.target.value })}
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
                <div className="w-full md:w-44">
                  <div className="relative">
                    <select
                      value={activeFilters.task}
                      onChange={(e) => updateFilters({ task: e.target.value })}
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

                {/* License Filter */}
                <div className="w-full md:w-44">
                  <div className="relative">
                    <select
                      value={activeFilters.license}
                      onChange={(e) =>
                        updateFilters({ license: e.target.value as LicenseStatus | '' })
                      }
                      aria-label="Filter by license"
                      className="w-full px-3 py-2.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 text-sm text-slate-700 dark:text-slate-200 focus:outline-hidden focus:ring-2 focus:ring-indigo-500 appearance-none pr-8 cursor-pointer"
                    >
                      <option value="">All Licenses</option>
                      {availableLicenses.map((lic) => (
                        <option key={lic} value={lic}>
                          {formatLicenseLabel(lic)}
                        </option>
                      ))}
                    </select>
                    <Filter className="absolute right-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-400 pointer-events-none" />
                  </div>
                </div>

                {/* Published Year Filter */}
                <div className="w-full md:w-36">
                  <div className="relative">
                    <select
                      value={activeFilters.year}
                      onChange={(e) => updateFilters({ year: e.target.value })}
                      aria-label="Filter by publication year"
                      className="w-full px-3 py-2.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 text-sm text-slate-700 dark:text-slate-200 focus:outline-hidden focus:ring-2 focus:ring-indigo-500 appearance-none pr-8 cursor-pointer"
                    >
                      <option value="">All Years</option>
                      {availableYears.map((yr) => (
                        <option key={yr} value={yr}>
                          {yr}
                        </option>
                      ))}
                    </select>
                    <Calendar className="absolute right-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-400 pointer-events-none" />
                  </div>
                </div>

                {/* Reset Filters Button */}
                {hasActiveFilters && (
                  <button
                    type="button"
                    onClick={handleResetFilters}
                    className="inline-flex items-center justify-center gap-1.5 px-3 py-2.5 rounded-lg border border-slate-300 dark:border-slate-700 text-sm font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors shrink-0 cursor-pointer"
                  >
                    <RotateCcw className="w-3.5 h-3.5" />
                    <span>Reset</span>
                  </button>
                )}
              </div>

              {/* Active Filter Chips */}
              {hasActiveFilters && (
                <div className="flex items-center gap-2 flex-wrap pt-3 mt-3 border-t border-slate-100 dark:border-slate-800/80 text-xs">
                  <span className="text-slate-500 font-medium">Active filters:</span>
                  {!isCategoryScoped && activeCategoryName && (
                    <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-indigo-100 text-indigo-800 dark:bg-indigo-950/70 dark:text-indigo-300">
                      Category: {activeCategoryName}
                      <button
                        type="button"
                        onClick={() => updateFilters({ category: null })}
                        aria-label={`Remove ${activeCategoryName} category filter`}
                        className="hover:text-indigo-950 dark:hover:text-white cursor-pointer"
                      >
                        <X className="w-3 h-3" />
                      </button>
                    </span>
                  )}
                  {activeFilters.searchQuery && (
                    <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-slate-200 text-slate-800 dark:bg-slate-800 dark:text-slate-200">
                      Search: &ldquo;{activeFilters.searchQuery}&rdquo;
                      <button
                        type="button"
                        onClick={() => handleSearchChange('')}
                        aria-label="Remove search query filter"
                        className="hover:text-slate-950 dark:hover:text-white cursor-pointer"
                      >
                        <X className="w-3 h-3" />
                      </button>
                    </span>
                  )}
                  {activeFilters.modality && (
                    <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-indigo-100 text-indigo-800 dark:bg-indigo-950/70 dark:text-indigo-300">
                      Modality: {activeFilters.modality}
                      <button
                        type="button"
                        onClick={() => updateFilters({ modality: '' })}
                        aria-label="Remove modality filter"
                        className="hover:text-indigo-950 dark:hover:text-white cursor-pointer"
                      >
                        <X className="w-3 h-3" />
                      </button>
                    </span>
                  )}
                  {activeFilters.task && (
                    <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-indigo-100 text-indigo-800 dark:bg-indigo-950/70 dark:text-indigo-300">
                      Task: {activeFilters.task}
                      <button
                        type="button"
                        onClick={() => updateFilters({ task: '' })}
                        aria-label="Remove task filter"
                        className="hover:text-indigo-950 dark:hover:text-white cursor-pointer"
                      >
                        <X className="w-3 h-3" />
                      </button>
                    </span>
                  )}
                  {activeFilters.license && (
                    <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-indigo-100 text-indigo-800 dark:bg-indigo-950/70 dark:text-indigo-300">
                      License: {formatLicenseLabel(activeFilters.license)}
                      <button
                        type="button"
                        onClick={() => updateFilters({ license: '' })}
                        aria-label="Remove license filter"
                        className="hover:text-indigo-950 dark:hover:text-white cursor-pointer"
                      >
                        <X className="w-3 h-3" />
                      </button>
                    </span>
                  )}
                  {activeFilters.year && (
                    <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-indigo-100 text-indigo-800 dark:bg-indigo-950/70 dark:text-indigo-300">
                      Year: {activeFilters.year}
                      <button
                        type="button"
                        onClick={() => updateFilters({ year: '' })}
                        aria-label="Remove year filter"
                        className="hover:text-indigo-950 dark:hover:text-white cursor-pointer"
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
              <p role="status" aria-live="polite" aria-atomic="true" className="text-sm text-slate-600 dark:text-slate-400">
                Showing{' '}
                <span className="font-bold text-slate-900 dark:text-white">
                  {displayedDatasets.length}
                </span>{' '}
                of{' '}
                <span className="font-bold text-slate-900 dark:text-white">
                  {filteredDatasets.length}
                </span>{' '}
                {isCategoryScoped ? `${currentCategory?.name} datasets` : 'datasets'}
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
                  No datasets match your active search and filter settings. Try adjusting your query or resetting filters.
                </p>
                <button
                  type="button"
                  onClick={handleResetFilters}
                  className="mt-5 inline-flex items-center gap-2 px-4 py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold shadow-xs transition-colors cursor-pointer"
                >
                  <RotateCcw className="w-3.5 h-3.5" />
                  <span>Reset All Filters</span>
                </button>
              </div>
            )}

            {/* Dataset Cards Grid */}
            {filteredDatasets.length > 0 && (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {displayedDatasets.map((dataset) => (
                  <DatasetCard key={dataset.id} dataset={dataset} />
                ))}
              </div>
            )}

            {/* Load More Button */}
            {displayedDatasets.length < filteredDatasets.length && (
              <div className="mt-10 flex flex-col items-center justify-center">
                <button
                  type="button"
                  onClick={() => setVisibleCount((prev) => prev + PAGE_SIZE)}
                  className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 hover:border-indigo-500 dark:hover:border-indigo-400 text-slate-800 dark:text-slate-200 text-sm font-semibold shadow-xs hover:shadow-md transition-all cursor-pointer focus:outline-hidden focus-visible:ring-2 focus-visible:ring-indigo-500"
                >
                  <span>Load More Datasets</span>
                  <span className="text-xs text-slate-500 dark:text-slate-400">
                    ({filteredDatasets.length - displayedDatasets.length} remaining)
                  </span>
                </button>
              </div>
            )}
          </>
        )}
      </div>

      {/* Accessible Back to Top Floating Button */}
      {showBackToTop && (
        <button
          type="button"
          onClick={handleScrollToTop}
          aria-label="Back to top"
          className="fixed bottom-6 right-6 z-40 p-3 rounded-full bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200 border border-slate-200 dark:border-slate-700 shadow-md hover:shadow-lg hover:border-indigo-400 dark:hover:border-indigo-500 hover:text-indigo-600 dark:hover:text-indigo-400 transition-all duration-200 motion-reduce:transition-none cursor-pointer focus:outline-hidden focus-visible:ring-2 focus-visible:ring-indigo-500"
        >
          <ArrowUp className="w-5 h-5" />
        </button>
      )}
    </div>
  )
}
