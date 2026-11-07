import React, { useEffect, useState, useMemo, useCallback } from 'react'
import { useSearchParams, Link, useNavigate } from 'react-router-dom'
import {
  ChevronRight,
  ArrowLeft,
  ArrowRight,
  X,
  ExternalLink,
  ShieldCheck,
  AlertCircle,
  HelpCircle,
  Building2,
  Calendar,
  HardDrive,
  BookOpen,
  Share2,
  Check,
  RotateCcw,
  Loader2,
  AlertTriangle,
  Layers,
} from 'lucide-react'
import type { DatasetMetadata } from '../types/dataset'
import { fetchCatalog } from '../services/catalogService'
import {
  MAX_COMPARE_COUNT,
  MIN_COMPARE_COUNT,
  parseCompareSlugsFromUrl,
  saveStoredComparisonSlugs,
  getStoredComparisonSlugs,
} from '../utils/comparisonUtils'
import { copyTextToClipboard } from '../utils/clipboard'

export interface ComparePageProps {
  initialCatalog?: DatasetMetadata[]
}

export const ComparePage: React.FC<ComparePageProps> = ({ initialCatalog }) => {
  const [searchParams, setSearchParams] = useSearchParams()
  const navigate = useNavigate()

  const [catalog, setCatalog] = useState<DatasetMetadata[]>(() => initialCatalog || [])
  const [loading, setLoading] = useState(() => !initialCatalog)
  const [error, setError] = useState<string | null>(null)
  const [copiedShareLink, setCopiedShareLink] = useState(false)

  // Load catalog
  useEffect(() => {
    if (initialCatalog && initialCatalog.length > 0) {
      return
    }
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
  }, [initialCatalog])

  // Derive current comparison slugs: prioritize URL query params, fallback to sessionStorage
  const activeSlugs = useMemo(() => {
    const fromUrl = parseCompareSlugsFromUrl(searchParams.toString())
    if (fromUrl.length > 0) {
      return fromUrl
    }
    return getStoredComparisonSlugs()
  }, [searchParams])

  // Sync back to URL and sessionStorage when activeSlugs are read from storage
  useEffect(() => {
    const fromUrl = parseCompareSlugsFromUrl(searchParams.toString())
    if (fromUrl.length === 0 && activeSlugs.length > 0) {
      setSearchParams({ datasets: activeSlugs.join(',') }, { replace: true })
    }
  }, [searchParams, activeSlugs, setSearchParams])

  // Matched datasets and missing slugs
  const { datasets, missingSlugs } = useMemo(() => {
    if (catalog.length === 0) {
      return { datasets: [], missingSlugs: [] }
    }
    const found: DatasetMetadata[] = []
    const missing: string[] = []

    for (const slug of activeSlugs) {
      const match = catalog.find((d) => d.slug === slug)
      if (match) {
        found.push(match)
      } else {
        missing.push(slug)
      }
    }

    return { datasets: found.slice(0, MAX_COMPARE_COUNT), missingSlugs: missing }
  }, [catalog, activeSlugs])

  // Handlers
  const handleRemoveDataset = useCallback(
    (slugToRemove: string) => {
      const nextSlugs = activeSlugs.filter((s) => s !== slugToRemove)
      saveStoredComparisonSlugs(nextSlugs)
      if (nextSlugs.length > 0) {
        setSearchParams({ datasets: nextSlugs.join(',') })
      } else {
        setSearchParams({})
      }
    },
    [activeSlugs, setSearchParams],
  )

  const handleClearAll = useCallback(() => {
    saveStoredComparisonSlugs([])
    setSearchParams({})
  }, [setSearchParams])

  const handleShare = useCallback(async () => {
    if (typeof window === 'undefined') return
    const success = await copyTextToClipboard(window.location.href)
    if (success) {
      setCopiedShareLink(true)
      setTimeout(() => setCopiedShareLink(false), 2500)
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

  // Verification Badge Renderer
  const renderVerificationBadge = (status?: string) => {
    switch (status) {
      case 'verified':
        return (
          <span
            title="Metadata checked against cited documentation; underlying data has not been audited"
            className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800"
          >
            <ShieldCheck className="w-3 h-3 text-emerald-500 shrink-0" />
            <span>Metadata checked</span>
          </span>
        )
      case 'provisional':
        return (
          <span
            title="Metadata is provisional and pending review"
            className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-amber-50 text-amber-700 dark:bg-amber-950/60 dark:text-amber-300 border border-amber-200 dark:border-amber-800"
          >
            <AlertCircle className="w-3 h-3 text-amber-500 shrink-0" />
            <span>Review pending</span>
          </span>
        )
      default:
        return (
          <span
            title="Metadata has not been verified"
            className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300 border border-slate-200 dark:border-slate-700"
          >
            <HelpCircle className="w-3 h-3 text-slate-400 shrink-0" />
            <span>Not reviewed</span>
          </span>
        )
    }
  }

  // Commercial Use Badge Renderer
  const renderCommercialBadge = (status?: string) => {
    switch (status) {
      case 'allowed':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-semibold bg-emerald-50 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800">
            Allowed
          </span>
        )
      case 'forbidden':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-semibold bg-rose-50 text-rose-700 dark:bg-rose-950/60 dark:text-rose-300 border border-rose-200 dark:border-rose-800">
            Forbidden
          </span>
        )
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-semibold bg-amber-50 text-amber-700 dark:bg-amber-950/60 dark:text-amber-300 border border-amber-200 dark:border-amber-800">
            Unknown (Review source terms)
          </span>
        )
    }
  }

  // Loading state
  if (loading) {
    return (
      <div className="flex-1 py-20 flex flex-col items-center justify-center text-center">
        <Loader2 className="w-8 h-8 text-indigo-600 animate-spin mb-4" />
        <p className="text-sm font-medium text-slate-600 dark:text-slate-400">
          Loading comparison data...
        </p>
      </div>
    )
  }

  // Error state
  if (error) {
    return (
      <div className="flex-1 py-16 px-4 max-w-3xl mx-auto text-center">
        <div className="rounded-xl border border-rose-200 dark:border-rose-900/60 bg-rose-50/50 dark:bg-rose-950/20 p-6 text-center my-8">
          <AlertTriangle className="w-8 h-8 text-rose-500 mx-auto mb-2" />
          <h2 className="text-base font-bold text-slate-900 dark:text-white">
            Unable to Load Comparison
          </h2>
          <p className="text-sm text-rose-600 dark:text-rose-400 mt-1 max-w-md mx-auto">
            {error}
          </p>
          <div className="mt-4 flex items-center justify-center gap-3">
            <button
              type="button"
              onClick={handleRetry}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-rose-600 hover:bg-rose-700 text-white text-xs font-semibold transition-colors cursor-pointer"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>Retry</span>
            </button>
            <Link
              to="/datasets"
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800 text-xs font-medium transition-colors cursor-pointer"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              <span>Return to Datasets</span>
            </Link>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="flex-1 py-8 md:py-12">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Breadcrumb Navigation */}
        <nav
          className="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400 mb-4"
          aria-label="Breadcrumb"
        >
          <Link
            to="/explore"
            className="hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors"
          >
            Explore
          </Link>
          <ChevronRight className="w-3.5 h-3.5 text-slate-400" />
          <Link
            to="/datasets"
            className="hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors"
          >
            Datasets
          </Link>
          <ChevronRight className="w-3.5 h-3.5 text-slate-400" />
          <span className="font-semibold text-slate-900 dark:text-white">
            Compare Datasets
          </span>
        </nav>

        {/* Page Header */}
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 border-b border-slate-200 dark:border-slate-800 pb-6 mb-8">
          <div>
            <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-indigo-600 dark:text-indigo-400 mb-2">
              <Layers className="w-4 h-4" />
              <span>Research Matrix</span>
            </div>
            <h1 className="text-3xl sm:text-4xl font-extrabold text-slate-900 dark:text-white tracking-tight">
              Dataset Comparison
            </h1>
            <p className="mt-2 text-base text-slate-600 dark:text-slate-400 max-w-3xl">
              Side-by-side comparison of metadata, scale, licensing, and citations for 2–3 selected datasets.
            </p>
          </div>

          <div className="flex items-center gap-2.5 flex-wrap">
            {datasets.length >= MIN_COMPARE_COUNT && (
              <button
                type="button"
                onClick={handleShare}
                className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800 text-xs font-semibold shadow-xs transition-colors cursor-pointer"
                aria-label="Share comparison link"
              >
                {copiedShareLink ? (
                  <>
                    <Check className="w-3.5 h-3.5 text-emerald-500" />
                    <span className="text-emerald-600 dark:text-emerald-400">Link Copied!</span>
                  </>
                ) : (
                  <>
                    <Share2 className="w-3.5 h-3.5 text-slate-400" />
                    <span>Share Comparison</span>
                  </>
                )}
              </button>
            )}

            {datasets.length > 0 && (
              <button
                type="button"
                onClick={handleClearAll}
                className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800 text-xs font-semibold shadow-xs transition-colors cursor-pointer"
              >
                <span>Clear</span>
              </button>
            )}

            <Link
              to="/datasets"
              className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold shadow-xs transition-colors cursor-pointer"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              <span>Back to Datasets</span>
            </Link>
          </div>
        </div>

        {/* Missing Slugs Warning */}
        {missingSlugs.length > 0 && (
          <div
            role="alert"
            className="mb-6 rounded-xl border border-amber-200 dark:border-amber-900/60 bg-amber-50 dark:bg-amber-950/20 p-4 text-xs text-amber-800 dark:text-amber-300 flex items-start gap-2.5"
          >
            <AlertCircle className="w-4 h-4 text-amber-500 shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold">Dataset not found</p>
              <p className="mt-0.5">
                The following {missingSlugs.length === 1 ? 'dataset was' : 'datasets were'} not found in the catalog:{' '}
                <span className="font-mono font-medium">{missingSlugs.join(', ')}</span>.
              </p>
            </div>
          </div>
        )}

        {/* Insufficient Selection State (< 2 datasets) */}
        {datasets.length < MIN_COMPARE_COUNT && (
          <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/40 p-8 sm:p-12 text-center max-w-2xl mx-auto my-8">
            <div className="w-12 h-12 rounded-2xl bg-indigo-50 dark:bg-indigo-950/70 text-indigo-600 dark:text-indigo-400 flex items-center justify-center mx-auto mb-4">
              <Layers className="w-6 h-6" />
            </div>

            <h2 className="text-xl font-bold text-slate-900 dark:text-white">
              {datasets.length === 1 ? 'Select Another Dataset to Compare' : 'Select at Least 2 Datasets'}
            </h2>

            <p className="mt-2 text-sm text-slate-600 dark:text-slate-400 max-w-md mx-auto leading-relaxed">
              {datasets.length === 1
                ? 'You have selected 1 dataset. Choose 1 or 2 more from the catalog to compare their modalities, sample scale, licensing, and citations.'
                : 'Select 2 to 3 datasets from the catalog using the Compare option on each dataset card to view an evidence-based comparison matrix.'}
            </p>

            {datasets.length === 1 && (
              <div className="mt-6 inline-flex items-center gap-2 px-3.5 py-1.5 rounded-xl bg-indigo-50 dark:bg-indigo-950/60 border border-indigo-200 dark:border-indigo-800 text-xs font-medium text-indigo-900 dark:text-indigo-200">
                <span>Selected:</span>
                <span className="font-bold">{datasets[0].name}</span>
                <button
                  type="button"
                  onClick={() => handleRemoveDataset(datasets[0].slug)}
                  aria-label={`Remove ${datasets[0].name}`}
                  className="hover:text-rose-600 dark:hover:text-rose-400 cursor-pointer"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>
            )}

            <div className="mt-8 flex items-center justify-center gap-3">
              <button
                type="button"
                onClick={() => navigate('/datasets')}
                className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold shadow-xs transition-colors cursor-pointer"
              >
                <span>Browse Dataset Catalog</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}

        {/* Full Comparison Table Matrix (>= 2 datasets) */}
        {datasets.length >= MIN_COMPARE_COUNT && (
          <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-sm">
                {/* Table Header: Datasets Overview */}
                <thead>
                  <tr className="border-b border-slate-200 dark:border-slate-800 bg-slate-50/80 dark:bg-slate-950/50">
                    <th
                      scope="col"
                      className="sticky left-0 z-20 w-52 sm:w-64 min-w-[180px] p-4 sm:p-5 bg-slate-50 dark:bg-slate-950 border-r border-slate-200 dark:border-slate-800 text-xs font-bold uppercase tracking-wider text-slate-500"
                    >
                      <span>Attributes</span>
                    </th>
                    {datasets.map((dataset) => (
                      <th
                        key={dataset.id}
                        scope="col"
                        className="w-72 sm:w-80 min-w-[260px] p-4 sm:p-5 align-top border-r last:border-r-0 border-slate-200 dark:border-slate-800"
                      >
                        <div className="flex flex-col justify-between h-full space-y-3">
                          <div className="flex items-start justify-between gap-2">
                            <div className="flex items-center gap-1.5 flex-wrap">
                              {(dataset.modalities || []).map((m) => (
                                <span
                                  key={m}
                                  className="px-2 py-0.5 rounded text-xs font-semibold uppercase tracking-wider bg-indigo-50 text-indigo-700 dark:bg-indigo-950/60 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800"
                                >
                                  {m}
                                </span>
                              ))}
                            </div>
                            <button
                              type="button"
                              onClick={() => handleRemoveDataset(dataset.slug)}
                              aria-label={`Remove ${dataset.name} from comparison`}
                              className="p-1 text-slate-400 hover:text-rose-600 dark:hover:text-rose-400 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors cursor-pointer shrink-0"
                            >
                              <X className="w-4 h-4" />
                            </button>
                          </div>

                          <div>
                            <h2 className="text-lg font-bold text-slate-900 dark:text-white leading-snug">
                              <Link
                                to={`/dataset/${dataset.slug}`}
                                className="hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors"
                              >
                                {dataset.name}
                              </Link>
                            </h2>
                            <div className="flex items-center gap-1.5 text-xs text-slate-500 dark:text-slate-400 mt-1">
                              <Building2 className="w-3.5 h-3.5 shrink-0" />
                              <span className="truncate">{dataset.publisher?.name || 'Unknown Publisher'}</span>
                            </div>
                          </div>

                          <div className="pt-2 flex items-center justify-between gap-2">
                            {renderVerificationBadge(dataset.verification?.status)}
                            <Link
                              to={`/dataset/${dataset.slug}`}
                              className="inline-flex items-center gap-1 text-xs font-semibold text-indigo-600 dark:text-indigo-400 hover:underline"
                            >
                              <span>View Details</span>
                              <ArrowRight className="w-3 h-3" />
                            </Link>
                          </div>
                        </div>
                      </th>
                    ))}
                  </tr>
                </thead>

                <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
                  {/* SECTION 1: IDENTITY & TAXONOMY */}
                  <tr className="bg-slate-100/60 dark:bg-slate-950/40">
                    <th
                      colSpan={datasets.length + 1}
                      scope="colgroup"
                      className="px-4 sm:px-5 py-2.5 text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300"
                    >
                      General Information &amp; Scope
                    </th>
                  </tr>

                  {/* Description */}
                  <tr>
                    <th
                      scope="row"
                      className="sticky left-0 z-10 p-4 sm:p-5 bg-white dark:bg-slate-900 border-r border-slate-200 dark:border-slate-800 text-xs font-semibold text-slate-500"
                    >
                      Description
                    </th>
                    {datasets.map((dataset) => (
                      <td
                        key={dataset.id}
                        className="p-4 sm:p-5 align-top border-r last:border-r-0 border-slate-200 dark:border-slate-800 text-xs text-slate-600 dark:text-slate-300 leading-relaxed"
                      >
                        <p className="line-clamp-4">{dataset.description}</p>
                      </td>
                    ))}
                  </tr>

                  {/* Tasks */}
                  <tr>
                    <th
                      scope="row"
                      className="sticky left-0 z-10 p-4 sm:p-5 bg-white dark:bg-slate-900 border-r border-slate-200 dark:border-slate-800 text-xs font-semibold text-slate-500"
                    >
                      Primary Tasks
                    </th>
                    {datasets.map((dataset) => (
                      <td
                        key={dataset.id}
                        className="p-4 sm:p-5 align-top border-r last:border-r-0 border-slate-200 dark:border-slate-800 text-xs"
                      >
                        {Array.isArray(dataset.tasks) && dataset.tasks.length > 0 ? (
                          <div className="flex flex-wrap gap-1">
                            {dataset.tasks.map((task) => (
                              <span
                                key={task}
                                className="px-2 py-0.5 rounded bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300"
                              >
                                #{task}
                              </span>
                            ))}
                          </div>
                        ) : (
                          <span className="text-slate-400 italic">Unspecified</span>
                        )}
                      </td>
                    ))}
                  </tr>

                  {/* Publisher & Type */}
                  <tr>
                    <th
                      scope="row"
                      className="sticky left-0 z-10 p-4 sm:p-5 bg-white dark:bg-slate-900 border-r border-slate-200 dark:border-slate-800 text-xs font-semibold text-slate-500"
                    >
                      Publisher
                    </th>
                    {datasets.map((dataset) => (
                      <td
                        key={dataset.id}
                        className="p-4 sm:p-5 align-top border-r last:border-r-0 border-slate-200 dark:border-slate-800 text-xs text-slate-700 dark:text-slate-200"
                      >
                        <div className="font-medium">{dataset.publisher?.name || 'Unknown'}</div>
                        <div className="text-slate-500 capitalize text-2xs mt-0.5">
                          {`Type: ${dataset.publisher?.type || 'unknown'}`}
                        </div>
                      </td>
                    ))}
                  </tr>

                  {/* Publication Date */}
                  <tr>
                    <th
                      scope="row"
                      className="sticky left-0 z-10 p-4 sm:p-5 bg-white dark:bg-slate-900 border-r border-slate-200 dark:border-slate-800 text-xs font-semibold text-slate-500"
                    >
                      Published Date
                    </th>
                    {datasets.map((dataset) => (
                      <td
                        key={dataset.id}
                        className="p-4 sm:p-5 align-top border-r last:border-r-0 border-slate-200 dark:border-slate-800 text-xs text-slate-700 dark:text-slate-300"
                      >
                        {dataset.dates?.published ? (
                          <div className="flex items-center gap-1.5">
                            <Calendar className="w-3.5 h-3.5 text-slate-400" />
                            <span>{dataset.dates.published}</span>
                          </div>
                        ) : (
                          <span className="text-slate-400 italic">Unspecified</span>
                        )}
                      </td>
                    ))}
                  </tr>

                  {/* SECTION 2: SCALE & SPLITS */}
                  <tr className="bg-slate-100/60 dark:bg-slate-950/40">
                    <th
                      colSpan={datasets.length + 1}
                      scope="colgroup"
                      className="px-4 sm:px-5 py-2.5 text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300"
                    >
                      Scale &amp; Dataset Structure
                    </th>
                  </tr>

                  {/* Sample Count */}
                  <tr>
                    <th
                      scope="row"
                      className="sticky left-0 z-10 p-4 sm:p-5 bg-white dark:bg-slate-900 border-r border-slate-200 dark:border-slate-800 text-xs font-semibold text-slate-500"
                    >
                      Sample Count
                    </th>
                    {datasets.map((dataset) => (
                      <td
                        key={dataset.id}
                        className="p-4 sm:p-5 align-top border-r last:border-r-0 border-slate-200 dark:border-slate-800 text-xs"
                      >
                        {dataset.sample_count?.total !== undefined ? (
                          <div>
                            <span className="text-base font-bold text-slate-900 dark:text-white">
                              {dataset.sample_count.total.toLocaleString('en-US')}
                            </span>
                            <span className="text-slate-500 text-xs ml-1">
                              {dataset.sample_count.unit || 'items'}
                            </span>
                            {dataset.sample_count.status === 'estimated' && (
                              <span className="block text-2xs text-amber-600 dark:text-amber-400 mt-0.5">
                                (estimated)
                              </span>
                            )}
                          </div>
                        ) : (
                          <span className="text-slate-400 italic">Unspecified</span>
                        )}
                      </td>
                    ))}
                  </tr>

                  {/* Splits */}
                  <tr>
                    <th
                      scope="row"
                      className="sticky left-0 z-10 p-4 sm:p-5 bg-white dark:bg-slate-900 border-r border-slate-200 dark:border-slate-800 text-xs font-semibold text-slate-500"
                    >
                      Splits Breakdown
                    </th>
                    {datasets.map((dataset) => (
                      <td
                        key={dataset.id}
                        className="p-4 sm:p-5 align-top border-r last:border-r-0 border-slate-200 dark:border-slate-800 text-xs"
                      >
                        {dataset.sample_count?.splits &&
                        Object.keys(dataset.sample_count.splits).length > 0 ? (
                          <div className="space-y-1">
                            {Object.entries(dataset.sample_count.splits).map(([split, count]) => (
                              <div
                                key={split}
                                className="flex items-center justify-between gap-2 px-2 py-0.5 rounded bg-slate-50 dark:bg-slate-800/60 border border-slate-200/60 dark:border-slate-700/60 text-2xs"
                              >
                                <span className="font-medium text-slate-600 dark:text-slate-400 uppercase tracking-wider">
                                  {split}
                                </span>
                                <span className="font-semibold text-slate-900 dark:text-slate-100 font-mono">
                                  {count.toLocaleString('en-US')}
                                </span>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <span className="text-slate-400 italic">Not documented in catalog</span>
                        )}
                      </td>
                    ))}
                  </tr>

                  {/* Download Size & Formats */}
                  <tr>
                    <th
                      scope="row"
                      className="sticky left-0 z-10 p-4 sm:p-5 bg-white dark:bg-slate-900 border-r border-slate-200 dark:border-slate-800 text-xs font-semibold text-slate-500"
                    >
                      Download Size
                    </th>
                    {datasets.map((dataset) => (
                      <td
                        key={dataset.id}
                        className="p-4 sm:p-5 align-top border-r last:border-r-0 border-slate-200 dark:border-slate-800 text-xs"
                      >
                        {dataset.size?.amount !== undefined ? (
                          <div>
                            <div className="font-semibold text-slate-900 dark:text-white flex items-center gap-1.5">
                              <HardDrive className="w-3.5 h-3.5 text-slate-400" />
                              <span>
                                {dataset.size.amount} {dataset.size.unit || 'MB'}
                              </span>
                            </div>
                            {Array.isArray(dataset.size.file_formats) &&
                              dataset.size.file_formats.length > 0 && (
                                <div className="text-2xs text-slate-500 mt-1 font-mono">
                                  Formats: {dataset.size.file_formats.join(', ')}
                                </div>
                              )}
                            {dataset.size.status === 'estimated' && (
                              <span className="block text-2xs text-amber-600 dark:text-amber-400 mt-0.5">
                                (estimated)
                              </span>
                            )}
                          </div>
                        ) : (
                          <span className="text-slate-400 italic">Unspecified</span>
                        )}
                      </td>
                    ))}
                  </tr>

                  {/* SECTION 3: LEGAL & LICENSING */}
                  <tr className="bg-slate-100/60 dark:bg-slate-950/40">
                    <th
                      colSpan={datasets.length + 1}
                      scope="colgroup"
                      className="px-4 sm:px-5 py-2.5 text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300"
                    >
                      Licensing &amp; Commercial Permissions
                    </th>
                  </tr>

                  {/* License Name & SPDX */}
                  <tr>
                    <th
                      scope="row"
                      className="sticky left-0 z-10 p-4 sm:p-5 bg-white dark:bg-slate-900 border-r border-slate-200 dark:border-slate-800 text-xs font-semibold text-slate-500"
                    >
                      License Name
                    </th>
                    {datasets.map((dataset) => (
                      <td
                        key={dataset.id}
                        className="p-4 sm:p-5 align-top border-r last:border-r-0 border-slate-200 dark:border-slate-800 text-xs"
                      >
                        <div className="font-semibold text-slate-900 dark:text-white">
                          {dataset.license?.name || 'Unspecified'}
                        </div>
                        {dataset.license?.spdx_id && (
                          <div className="text-2xs text-slate-500 font-mono mt-0.5">
                            {`SPDX: ${dataset.license.spdx_id}`}
                          </div>
                        )}
                      </td>
                    ))}
                  </tr>

                  {/* Commercial Use Status */}
                  <tr>
                    <th
                      scope="row"
                      className="sticky left-0 z-10 p-4 sm:p-5 bg-white dark:bg-slate-900 border-r border-slate-200 dark:border-slate-800 text-xs font-semibold text-slate-500"
                    >
                      Commercial Use
                    </th>
                    {datasets.map((dataset) => (
                      <td
                        key={dataset.id}
                        className="p-4 sm:p-5 align-top border-r last:border-r-0 border-slate-200 dark:border-slate-800 text-xs"
                      >
                        {renderCommercialBadge(dataset.license?.commercial_use)}
                      </td>
                    ))}
                  </tr>

                  {/* License Notes */}
                  <tr>
                    <th
                      scope="row"
                      className="sticky left-0 z-10 p-4 sm:p-5 bg-white dark:bg-slate-900 border-r border-slate-200 dark:border-slate-800 text-xs font-semibold text-slate-500"
                    >
                      License Notes
                    </th>
                    {datasets.map((dataset) => (
                      <td
                        key={dataset.id}
                        className="p-4 sm:p-5 align-top border-r last:border-r-0 border-slate-200 dark:border-slate-800 text-xs text-slate-600 dark:text-slate-400 leading-relaxed"
                      >
                        {dataset.license?.notes ? (
                          <p>{dataset.license.notes}</p>
                        ) : dataset.license?.status === 'unspecified_by_source' ||
                          dataset.license?.status === 'unknown' ? (
                          <p className="italic text-slate-400">
                            The upstream source does not declare a standardized license. Review terms before use.
                          </p>
                        ) : (
                          <span className="text-slate-400 italic">None declared</span>
                        )}

                        {dataset.license?.url && (
                          <div className="mt-2">
                            <a
                              href={dataset.license.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="inline-flex items-center gap-1 font-semibold text-indigo-600 dark:text-indigo-400 hover:underline text-2xs"
                            >
                              <span>Review License URL</span>
                              <ExternalLink className="w-3 h-3" />
                            </a>
                          </div>
                        )}
                      </td>
                    ))}
                  </tr>

                  {/* SECTION 4: CITATION & SOURCES */}
                  <tr className="bg-slate-100/60 dark:bg-slate-950/40">
                    <th
                      colSpan={datasets.length + 1}
                      scope="colgroup"
                      className="px-4 sm:px-5 py-2.5 text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300"
                    >
                      Academic Citations &amp; Source Links
                    </th>
                  </tr>

                  {/* Research Paper */}
                  <tr>
                    <th
                      scope="row"
                      className="sticky left-0 z-10 p-4 sm:p-5 bg-white dark:bg-slate-900 border-r border-slate-200 dark:border-slate-800 text-xs font-semibold text-slate-500"
                    >
                      Cited Paper
                    </th>
                    {datasets.map((dataset) => (
                      <td
                        key={dataset.id}
                        className="p-4 sm:p-5 align-top border-r last:border-r-0 border-slate-200 dark:border-slate-800 text-xs"
                      >
                        {dataset.citation?.paper_title ? (
                          <div>
                            <div className="font-medium text-slate-900 dark:text-white leading-snug">
                              {dataset.citation.paper_title}
                            </div>
                            {dataset.citation.paper_url && (
                              <a
                                href={dataset.citation.paper_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="mt-1 inline-flex items-center gap-1 text-2xs font-semibold text-indigo-600 dark:text-indigo-400 hover:underline"
                              >
                                <BookOpen className="w-3 h-3" />
                                <span>Read Paper</span>
                                <ExternalLink className="w-2.5 h-2.5" />
                              </a>
                            )}
                          </div>
                        ) : (
                          <span className="text-slate-400 italic">Unspecified</span>
                        )}
                      </td>
                    ))}
                  </tr>

                  {/* DOI */}
                  <tr>
                    <th
                      scope="row"
                      className="sticky left-0 z-10 p-4 sm:p-5 bg-white dark:bg-slate-900 border-r border-slate-200 dark:border-slate-800 text-xs font-semibold text-slate-500"
                    >
                      DOI Link
                    </th>
                    {datasets.map((dataset) => (
                      <td
                        key={dataset.id}
                        className="p-4 sm:p-5 align-top border-r last:border-r-0 border-slate-200 dark:border-slate-800 text-xs font-mono"
                      >
                        {dataset.citation?.doi ? (
                          <a
                            href={
                              dataset.citation.doi.startsWith('http')
                                ? dataset.citation.doi
                                : `https://doi.org/${dataset.citation.doi}`
                            }
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1 text-indigo-600 dark:text-indigo-400 hover:underline break-all"
                          >
                            <span>{dataset.citation.doi}</span>
                            <ExternalLink className="w-3 h-3 shrink-0" />
                          </a>
                        ) : (
                          <span className="text-slate-400 italic font-sans">Unspecified</span>
                        )}
                      </td>
                    ))}
                  </tr>

                  {/* Official Website */}
                  <tr>
                    <th
                      scope="row"
                      className="sticky left-0 z-10 p-4 sm:p-5 bg-white dark:bg-slate-900 border-r border-slate-200 dark:border-slate-800 text-xs font-semibold text-slate-500"
                    >
                      Official Homepage
                    </th>
                    {datasets.map((dataset) => (
                      <td
                        key={dataset.id}
                        className="p-4 sm:p-5 align-top border-r last:border-r-0 border-slate-200 dark:border-slate-800 text-xs"
                      >
                        {dataset.homepage_url ? (
                          <a
                            href={dataset.homepage_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1.5 font-semibold text-indigo-600 dark:text-indigo-400 hover:underline break-all"
                          >
                            <span className="truncate max-w-[220px]">{dataset.homepage_url}</span>
                            <ExternalLink className="w-3 h-3 shrink-0" />
                          </a>
                        ) : (
                          <span className="text-slate-400 italic">Unspecified</span>
                        )}
                      </td>
                    ))}
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
