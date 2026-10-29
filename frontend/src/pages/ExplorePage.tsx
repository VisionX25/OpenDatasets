import React, { useEffect, useState, useMemo } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import {
  Search,
  Filter,
  Layers,
  X,
  Loader2,
  AlertTriangle,
  RotateCcw,
  ArrowRight,
  Calendar,
} from 'lucide-react'
import type { DatasetMetadata, LicenseStatus, CategoryId } from '../types/dataset'
import { fetchCatalog } from '../services/catalogService'
import {
  countDatasetsPerCategory,
  getAvailableModalities,
  getAvailableTasks,
  getAvailableLicenseStatuses,
  getAvailablePublicationYears,
  formatLicenseLabel,
  serializeFilterParams,
} from '../utils/datasetFilters'
import { CategoryGrid } from '../components/CategoryGrid'

export const ExplorePage: React.FC = () => {
  const navigate = useNavigate()
  const [catalog, setCatalog] = useState<DatasetMetadata[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Local filter form state on Explore landing page (does NOT navigate on every keystroke)
  const [searchQuery, setSearchQuery] = useState('')
  const [modality, setModality] = useState('')
  const [task, setTask] = useState('')
  const [license, setLicense] = useState<LicenseStatus | ''>('')
  const [year, setYear] = useState('')

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

  // Available filter options based on catalog
  const availableModalities = useMemo(() => getAvailableModalities(catalog), [catalog])
  const availableTasks = useMemo(() => getAvailableTasks(catalog), [catalog])
  const availableLicenses = useMemo(() => getAvailableLicenseStatuses(catalog), [catalog])
  const availableYears = useMemo(() => getAvailablePublicationYears(catalog), [catalog])
  const categoryCounts = useMemo(() => countDatasetsPerCategory(catalog), [catalog])

  // Submitting search navigates to /datasets?q=...
  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const params = serializeFilterParams({
      searchQuery,
      modality,
      task,
      license,
      year,
    })
    navigate(`/datasets${params.toString() ? `?${params.toString()}` : ''}`)
  }

  // Selecting a filter navigates to /datasets with relevant query params
  const handleFilterChange = (
    field: 'modality' | 'task' | 'license' | 'year',
    value: string,
  ) => {
    const nextState = {
      searchQuery,
      modality,
      task,
      license,
      year,
      [field]: value,
    }

    if (field === 'modality') setModality(value)
    if (field === 'task') setTask(value)
    if (field === 'license') setLicense(value as LicenseStatus | '')
    if (field === 'year') setYear(value)

    const params = serializeFilterParams(nextState)
    navigate(`/datasets${params.toString() ? `?${params.toString()}` : ''}`)
  }

  // Clicking a category navigates directly to /datasets/:categorySlug
  const handleCategorySelect = (catId: CategoryId | null) => {
    if (catId) {
      navigate(`/datasets/${catId}`)
    }
  }

  return (
    <div className="flex-1 py-8 md:py-12">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* 1. Explore Datasets heading */}
        <div className="border-b border-slate-200 dark:border-slate-800 pb-6 mb-8">
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-indigo-600 dark:text-indigo-400 mb-2">
            <Layers className="w-4 h-4" />
            <span>Dataset Catalog</span>
          </div>
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h1 className="text-3xl sm:text-4xl font-extrabold text-slate-900 dark:text-white tracking-tight">
                Explore Datasets
              </h1>
              <p className="mt-2 text-base text-slate-600 dark:text-slate-400 max-w-3xl">
                Discover machine learning datasets and their documented metadata across computer vision, NLP, tabular data, and evaluation benchmarks.
              </p>
            </div>
            <Link
              to="/datasets"
              className="inline-flex items-center gap-1.5 px-4 py-2.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-200 hover:border-indigo-500 hover:text-indigo-600 dark:hover:text-indigo-400 text-xs font-semibold shrink-0 shadow-2xs transition-colors"
            >
              <span>Browse All Datasets</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>
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
              className="mt-4 inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-rose-600 hover:bg-rose-700 text-white text-xs font-semibold transition-colors cursor-pointer"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>Retry</span>
            </button>
          </div>
        )}

        {/* 2. Search and Filters section & 3. Six category cards */}
        {!loading && !error && (
          <>
            {/* Search and Filters Controls Card */}
            <form
              onSubmit={handleSearchSubmit}
              className="bg-white dark:bg-slate-900/80 rounded-xl border border-slate-200 dark:border-slate-800 p-4 sm:p-5 mb-8 shadow-xs"
            >
              <div className="flex flex-col md:flex-row gap-3 flex-wrap">
                {/* Search Input */}
                <div className="relative flex-1 min-w-[200px]">
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
                      className="absolute right-3 top-1/2 -translate-y-1/2 p-1 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 rounded cursor-pointer"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  )}
                </div>

                {/* Modality Filter */}
                <div className="w-full md:w-44">
                  <div className="relative">
                    <select
                      value={modality}
                      onChange={(e) => handleFilterChange('modality', e.target.value)}
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
                      value={task}
                      onChange={(e) => handleFilterChange('task', e.target.value)}
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
                      value={license}
                      onChange={(e) => handleFilterChange('license', e.target.value)}
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
                      value={year}
                      onChange={(e) => handleFilterChange('year', e.target.value)}
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

                {/* Submit Search Button */}
                <button
                  type="submit"
                  className="inline-flex items-center justify-center gap-1.5 px-5 py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-semibold transition-colors cursor-pointer shadow-xs shrink-0"
                >
                  <Search className="w-4 h-4" />
                  <span>Search</span>
                </button>
              </div>
            </form>

            {/* 3. Six category cards */}
            <CategoryGrid
              activeCategory={null}
              onSelectCategory={handleCategorySelect}
              categoryCounts={categoryCounts}
            />

            {/* Subtle Browse All Datasets Footer Banner */}
            <div className="p-6 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/40 flex flex-col sm:flex-row items-center justify-between gap-4 mt-2 shadow-2xs">
              <div>
                <h2 className="text-sm font-bold text-slate-900 dark:text-white">
                  Looking for all available machine learning data?
                </h2>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                  Explore the full catalog of {catalog.length} dataset records with filters and search.
                </p>
              </div>
              <Link
                to="/datasets"
                className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold shrink-0 transition-colors cursor-pointer shadow-xs"
              >
                <span>Browse All Datasets</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
