import React, { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import {
  ArrowLeft,
  ExternalLink,
  ShieldCheck,
  AlertCircle,
  AlertTriangle,
  HelpCircle,
  Building2,
  Calendar,
  HardDrive,
  BarChart3,
  Scale,
  FileText,
  Copy,
  Check,
  BookOpen,
  Info,
  Loader2,
  RotateCcw,
} from 'lucide-react'
import type { DatasetMetadata } from '../types/dataset'
import { getDatasetBySlug } from '../services/catalogService'
import { copyTextToClipboard } from '../utils/clipboard'

export const DatasetDetailPage: React.FC = () => {
  const { slug } = useParams<{ slug: string }>()
  const [dataset, setDataset] = useState<DatasetMetadata | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [copiedBibtex, setCopiedBibtex] = useState(false)
  const [copyError, setCopyError] = useState(false)

  useEffect(() => {
    let ignore = false

    getDatasetBySlug(slug)
      .then((found) => {
        if (!ignore) {
          setDataset(found)
          setError(null)
          setLoading(false)
        }
      })
      .catch((err) => {
        if (!ignore) {
          setDataset(null)
          setError(err instanceof Error ? err.message : 'Failed to load dataset details.')
          setLoading(false)
        }
      })

    return () => {
      ignore = true
    }
  }, [slug])

  const handleRetry = () => {
    if (!slug || !slug.trim()) {
      return
    }
    setLoading(true)
    setError(null)
    getDatasetBySlug(slug, { forceReload: true })
      .then((found) => {
        setDataset(found)
        setError(null)
        setLoading(false)
      })
      .catch((err) => {
        setDataset(null)
        setError(err instanceof Error ? err.message : 'Failed to load dataset details.')
        setLoading(false)
      })
  }

  const handleCopyBibtex = async (text: string) => {
    const success = await copyTextToClipboard(text)
    if (success) {
      setCopyError(false)
      setCopiedBibtex(true)
      setTimeout(() => setCopiedBibtex(false), 2000)
    } else {
      setCopiedBibtex(false)
      setCopyError(true)
      setTimeout(() => setCopyError(false), 2000)
    }
  }

  if (loading) {
    return (
      <div className="flex-1 py-20 flex flex-col items-center justify-center text-center">
        <Loader2 className="w-8 h-8 text-indigo-600 animate-spin mb-4" />
        <p className="text-sm font-medium text-slate-600 dark:text-slate-400">
          Loading dataset details...
        </p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex-1 py-16 px-4 max-w-3xl mx-auto text-center">
        <div className="rounded-xl border border-rose-200 dark:border-rose-900/60 bg-rose-50/50 dark:bg-rose-950/20 p-6 text-center my-8">
          <AlertTriangle className="w-8 h-8 text-rose-500 mx-auto mb-2" />
          <h2 className="text-base font-bold text-slate-900 dark:text-white">
            Unable to Load Dataset
          </h2>
          <p className="text-sm text-rose-600 dark:text-rose-400 mt-1 max-w-md mx-auto">
            {error}
          </p>
          <div className="mt-4 flex items-center justify-center gap-3">
            <button
              type="button"
              onClick={handleRetry}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-rose-600 hover:bg-rose-700 text-white text-xs font-semibold transition-colors"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>Retry</span>
            </button>
            <Link
              to="/explore"
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800 text-xs font-medium transition-colors"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              <span>Return to Catalog</span>
            </Link>
          </div>
        </div>
      </div>
    )
  }

  if (!dataset) {
    return (
      <div className="flex-1 py-16 px-4 max-w-3xl mx-auto text-center">
        <div className="w-14 h-14 rounded-2xl bg-amber-100 dark:bg-amber-950/60 text-amber-600 dark:text-amber-400 flex items-center justify-center mx-auto mb-4">
          <HelpCircle className="w-7 h-7" />
        </div>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white">
          Dataset Not Found
        </h1>
        <p className="mt-2 text-sm text-slate-600 dark:text-slate-400 max-w-md mx-auto">
          No dataset matching the identifier &ldquo;{slug || ''}&rdquo; was found in the OpenDatasets catalog.
        </p>
        <div className="mt-6">
          <Link
            to="/explore"
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-semibold transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Return to Catalog</span>
          </Link>
        </div>
      </div>
    )
  }

  const renderVerificationBadge = (status: string) => {
    switch (status) {
      case 'verified':
        return (
          <span
            title="Metadata verified against authoritative documentation"
            className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 dark:bg-emerald-950/70 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800"
          >
            <ShieldCheck className="w-4 h-4 text-emerald-500" />
            Verified Metadata
          </span>
        )
      case 'provisional':
        return (
          <span
            title="Metadata is provisional and pending full verification"
            className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-amber-50 text-amber-700 dark:bg-amber-950/70 dark:text-amber-300 border border-amber-200 dark:border-amber-800"
          >
            <AlertCircle className="w-4 h-4 text-amber-500" />
            Provisional Metadata
          </span>
        )
      default:
        return (
          <span
            title="Metadata has not been verified"
            className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300 border border-slate-200 dark:border-slate-700"
          >
            <HelpCircle className="w-4 h-4 text-slate-400" />
            Unverified Metadata
          </span>
        )
    }
  }

  return (
    <div className="flex-1 py-8 md:py-12">
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Breadcrumb Navigation */}
        <nav aria-label="Breadcrumb" className="flex items-center gap-2 text-xs text-slate-500 mb-6">
          <Link to="/" className="hover:text-indigo-600 dark:hover:text-indigo-400">
            Home
          </Link>
          <span>/</span>
          <Link to="/explore" className="hover:text-indigo-600 dark:hover:text-indigo-400">
            Explore
          </Link>
          <span>/</span>
          <span className="text-slate-800 dark:text-slate-200 font-medium truncate max-w-xs">
            {dataset.name}
          </span>
        </nav>

        {/* Header Block */}
        <div className="border-b border-slate-200 dark:border-slate-800 pb-8 mb-8">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-4">
            <div className="flex items-center gap-2 flex-wrap">
              {(dataset.modalities || []).map((mod) => (
                <span
                  key={mod}
                  className="px-2.5 py-1 rounded-md text-xs font-bold uppercase tracking-wider bg-indigo-50 text-indigo-700 dark:bg-indigo-950/60 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800"
                >
                  {mod}
                </span>
              ))}
              <span className="text-xs font-mono text-slate-400">id: {dataset.id}</span>
            </div>
            {renderVerificationBadge(dataset.verification.status)}
          </div>

          <h1 className="text-3xl sm:text-4xl font-extrabold text-slate-900 dark:text-white tracking-tight">
            {dataset.name}
          </h1>

          <div className="mt-3 flex flex-wrap items-center gap-y-2 gap-x-6 text-sm text-slate-600 dark:text-slate-400">
            <div className="flex items-center gap-1.5">
              <Building2 className="w-4 h-4 text-slate-400 shrink-0" />
              <span>
                {dataset.publisher.name} ({dataset.publisher.type})
              </span>
            </div>
            {dataset.dates?.published && (
              <div className="flex items-center gap-1.5">
                <Calendar className="w-4 h-4 text-slate-400 shrink-0" />
                <span>Published: {dataset.dates.published}</span>
              </div>
            )}
          </div>

          <div className="mt-6 flex flex-wrap items-center gap-3">
            <a
              href={dataset.homepage_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-semibold shadow-xs transition-colors"
            >
              <span>Official Website</span>
              <ExternalLink className="w-3.5 h-3.5" />
            </a>
            {dataset.citation?.paper_url && (
              <a
                href={dataset.citation.paper_url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800 text-sm font-medium transition-colors"
              >
                <BookOpen className="w-3.5 h-3.5 text-slate-400" />
                <span>Research Paper</span>
                <ExternalLink className="w-3.5 h-3.5 opacity-60" />
              </a>
            )}
          </div>
        </div>

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {/* Left Column: Description & Citations */}
          <div className="md:col-span-2 space-y-8">
            {/* Description */}
            <section className="bg-white dark:bg-slate-900/60 p-6 rounded-xl border border-slate-200 dark:border-slate-800">
              <h2 className="text-lg font-bold text-slate-900 dark:text-white mb-3">
                Dataset Overview
              </h2>
              <p className="text-slate-700 dark:text-slate-300 text-sm sm:text-base leading-relaxed whitespace-pre-line">
                {dataset.description}
              </p>

              {/* Tasks & Tags */}
              <div className="mt-6 pt-6 border-t border-slate-100 dark:border-slate-800/80">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-2">
                  Supported Tasks & Tags
                </h3>
                <div className="flex flex-wrap gap-1.5">
                  {(dataset.tasks || []).map((task) => (
                    <span
                      key={task}
                      className="px-2.5 py-1 rounded text-xs font-medium bg-indigo-50 text-indigo-700 dark:bg-indigo-950/60 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800"
                    >
                      task: {task}
                    </span>
                  ))}
                  {(dataset.tags || []).map((tag) => (
                    <span
                      key={tag}
                      className="px-2.5 py-1 rounded text-xs bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300"
                    >
                      #{tag}
                    </span>
                  ))}
                </div>
              </div>
            </section>

            {/* Provenance & Collection */}
            {dataset.provenance && (
              <section className="bg-white dark:bg-slate-900/60 p-6 rounded-xl border border-slate-200 dark:border-slate-800">
                <h2 className="text-lg font-bold text-slate-900 dark:text-white mb-3">
                  Provenance & Curation
                </h2>
                {dataset.provenance.collection_method && (
                  <div className="mb-3">
                    <span className="text-xs font-semibold text-slate-500 uppercase">
                      Collection Method
                    </span>
                    <p className="text-sm text-slate-700 dark:text-slate-300 mt-0.5">
                      {dataset.provenance.collection_method}
                    </p>
                  </div>
                )}
                {dataset.provenance.curation_notes && (
                  <div>
                    <span className="text-xs font-semibold text-slate-500 uppercase">
                      Curation Notes
                    </span>
                    <p className="text-sm text-slate-700 dark:text-slate-300 mt-0.5">
                      {dataset.provenance.curation_notes}
                    </p>
                  </div>
                )}
              </section>
            )}

            {/* Source References */}
            <section className="bg-white dark:bg-slate-900/60 p-6 rounded-xl border border-slate-200 dark:border-slate-800">
              <h2 className="text-lg font-bold text-slate-900 dark:text-white mb-3">
                Source References
              </h2>
              <ul className="space-y-3">
                {(dataset.source_references || []).map((ref, idx) => (
                  <li
                    key={idx}
                    className="p-3 rounded-lg bg-slate-50 dark:bg-slate-800/40 border border-slate-100 dark:border-slate-800 text-sm flex items-start justify-between gap-3"
                  >
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-slate-900 dark:text-white">
                          {ref.title}
                        </span>
                        <span className="text-[10px] px-1.5 py-0.5 rounded uppercase font-bold bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-300">
                          {ref.type.replace(/_/g, ' ')}
                        </span>
                      </div>
                      {ref.notes && (
                        <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                          {ref.notes}
                        </p>
                      )}
                    </div>
                    <a
                      href={ref.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="p-1.5 text-indigo-600 dark:text-indigo-400 hover:bg-slate-200 dark:hover:bg-slate-700 rounded transition-colors"
                      aria-label={`Open link to ${ref.title}`}
                    >
                      <ExternalLink className="w-4 h-4" />
                    </a>
                  </li>
                ))}
              </ul>
            </section>

            {/* BibTeX Citation */}
            {dataset.citation?.bibtex && (
              <section className="bg-white dark:bg-slate-900/60 p-6 rounded-xl border border-slate-200 dark:border-slate-800">
                <div className="flex items-center justify-between mb-3">
                  <h2 className="text-lg font-bold text-slate-900 dark:text-white flex items-center gap-2">
                    <FileText className="w-5 h-5 text-indigo-500" />
                    <span>Academic Citation</span>
                  </h2>
                  <button
                    type="button"
                    onClick={() => handleCopyBibtex(dataset.citation?.bibtex || '')}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-semibold bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 transition-colors"
                  >
                    {copiedBibtex ? (
                      <>
                        <Check className="w-3.5 h-3.5 text-emerald-500" />
                        <span>Copied!</span>
                      </>
                    ) : copyError ? (
                      <>
                        <AlertCircle className="w-3.5 h-3.5 text-rose-500" />
                        <span>Copy Failed</span>
                      </>
                    ) : (
                      <>
                        <Copy className="w-3.5 h-3.5" />
                        <span>Copy BibTeX</span>
                      </>
                    )}
                  </button>
                </div>
                <pre className="p-4 rounded-lg bg-slate-950 text-slate-200 font-mono text-xs overflow-x-auto leading-relaxed border border-slate-800">
                  {dataset.citation.bibtex}
                </pre>
              </section>
            )}
          </div>

          {/* Right Column: Key Specifications & Legal Metadata */}
          <div className="space-y-6">
            {/* Legal & Licensing Info */}
            <div className="p-5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/60">
              <h2 className="text-sm font-bold uppercase tracking-wider text-slate-500 mb-4 flex items-center gap-2">
                <Scale className="w-4 h-4 text-indigo-500" />
                <span>Licensing & Permissions</span>
              </h2>
              <div className="space-y-3 text-sm">
                <div>
                  <span className="text-xs text-slate-500">License Name</span>
                  <p className="font-semibold text-slate-900 dark:text-white">
                    {dataset.license.name || 'Unspecified License'}
                  </p>
                </div>

                <div>
                  <span className="text-xs text-slate-500">License Status</span>
                  <p className="font-medium text-slate-700 dark:text-slate-300 capitalize">
                    {(dataset.license.status || 'unknown').replace(/_/g, ' ')}
                  </p>
                </div>

                <div>
                  <span className="text-xs text-slate-500">Commercial Usage</span>
                  <p className="font-medium text-slate-700 dark:text-slate-300 capitalize">
                    {dataset.license.commercial_use
                      ? dataset.license.commercial_use.replace(/_/g, ' ')
                      : 'Unknown'}
                  </p>
                </div>

                {dataset.license.notes ? (
                  <div className="pt-2 border-t border-slate-100 dark:border-slate-800 text-xs text-slate-500 dark:text-slate-400 leading-relaxed">
                    {dataset.license.notes}
                  </div>
                ) : (dataset.license.status === 'unspecified_by_source' ||
                     dataset.license.status === 'unknown') ? (
                  <div className="pt-2 border-t border-slate-100 dark:border-slate-800 text-xs text-slate-500 dark:text-slate-400 leading-relaxed italic">
                    The upstream source does not declare a standardized open license. Review source terms before production use.
                  </div>
                ) : null}

                {dataset.license.url && (
                  <div className="pt-2">
                    <a
                      href={dataset.license.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1.5 text-xs font-semibold text-indigo-600 dark:text-indigo-400 hover:underline"
                    >
                      <span>Read Full License</span>
                      <ExternalLink className="w-3 h-3" />
                    </a>
                  </div>
                )}
              </div>
            </div>

            {/* Dataset Statistics */}
            <div className="p-5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/60">
              <h2 className="text-sm font-bold uppercase tracking-wider text-slate-500 mb-4 flex items-center gap-2">
                <BarChart3 className="w-4 h-4 text-indigo-500" />
                <span>Dataset Specifications</span>
              </h2>

              <div className="space-y-4 text-sm">
                {/* Sample count */}
                <div>
                  <span className="text-xs text-slate-500">Sample Count</span>
                  {dataset.sample_count ? (
                    <div>
                      <p className="text-xl font-extrabold text-slate-900 dark:text-white">
                        {dataset.sample_count.total?.toLocaleString() ?? 'Unspecified'}{' '}
                        <span className="text-xs font-normal text-slate-500">
                          {dataset.sample_count.unit || 'items'}
                        </span>
                      </p>
                      {dataset.sample_count.splits && (
                        <div className="mt-1 flex flex-wrap gap-2 text-xs text-slate-600 dark:text-slate-400">
                          {Object.entries(dataset.sample_count.splits).map(([split, count]) => (
                            <span key={split} className="bg-slate-100 dark:bg-slate-800 px-2 py-0.5 rounded">
                              {split}: {count.toLocaleString()}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  ) : (
                    <p className="text-xs text-slate-500 italic">Unspecified</p>
                  )}
                </div>

                {/* Size */}
                <div className="pt-3 border-t border-slate-100 dark:border-slate-800">
                  <div className="flex items-center gap-1.5 mb-1">
                    <HardDrive className="w-3.5 h-3.5 text-slate-400" />
                    <span className="text-xs text-slate-500">Dataset Size</span>
                  </div>
                  {dataset.size?.amount ? (
                    <div>
                      <p className="text-base font-bold text-slate-900 dark:text-white">
                        {dataset.size.amount} {dataset.size.unit}
                      </p>
                      {dataset.size.file_formats && (
                        <p className="text-xs text-slate-500">
                          Formats: {dataset.size.file_formats.join(', ')}
                        </p>
                      )}
                    </div>
                  ) : (
                    <p className="text-xs text-slate-500 italic">Unspecified</p>
                  )}
                </div>
              </div>
            </div>

            {/* Verification Audit Trail */}
            <div className="p-5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/60">
              <h2 className="text-sm font-bold uppercase tracking-wider text-slate-500 mb-3 flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-emerald-500" />
                <span>Metadata Audit</span>
              </h2>
              <div className="space-y-2 text-xs text-slate-600 dark:text-slate-400">
                <p>
                  <span className="font-semibold text-slate-700 dark:text-slate-300">Status:</span>{' '}
                  <span className="capitalize">{dataset.verification.status}</span>
                </p>
                {dataset.verification.verified_by && (
                  <p>
                    <span className="font-semibold text-slate-700 dark:text-slate-300">Verified By:</span>{' '}
                    {dataset.verification.verified_by}
                  </p>
                )}
                {dataset.verification.verified_date && (
                  <p>
                    <span className="font-semibold text-slate-700 dark:text-slate-300">Date:</span>{' '}
                    {dataset.verification.verified_date}
                  </p>
                )}
                {dataset.verification.notes && (
                  <p className="text-slate-500 mt-2 leading-relaxed">
                    {dataset.verification.notes}
                  </p>
                )}
              </div>
            </div>

            {/* Quality & Legal Disclaimer Notice */}
            <div className="p-4 rounded-xl border border-indigo-100 dark:border-indigo-950/60 bg-indigo-50/50 dark:bg-indigo-950/20 text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
              <div className="flex items-center gap-1.5 font-semibold text-indigo-700 dark:text-indigo-300 mb-1">
                <Info className="w-4 h-4 shrink-0" />
                <span>OpenDatasets Disclaimer</span>
              </div>
              <p>
                Metadata verification confirms that metadata attributes were checked against authoritative documentation. It does not imply a legal guarantee of dataset quality, model safety, or commercial rights.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
