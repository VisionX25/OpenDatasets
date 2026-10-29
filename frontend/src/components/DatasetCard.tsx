import React, { useState, useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'
import {
  ShieldCheck,
  AlertCircle,
  HelpCircle,
  ArrowRight,
  Building2,
  Scale,
} from 'lucide-react'
import type { DatasetMetadata } from '../types/dataset'

interface DatasetCardProps {
  dataset: DatasetMetadata
  animateOnScroll?: boolean
}

export const DatasetCard: React.FC<DatasetCardProps> = ({ dataset, animateOnScroll = true }) => {
  // Initialize visibility state: if animateOnScroll is disabled, in non-browser/SSR
  // environments, or if reduced-motion is requested, render immediately visible.
  const [isVisible, setIsVisible] = useState(() => {
    if (!animateOnScroll) return true
    if (typeof window === 'undefined' || typeof IntersectionObserver === 'undefined') {
      return true
    }
    if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) {
      return true
    }
    return false
  })

  const cardRef = useRef<HTMLElement>(null)

  useEffect(() => {
    if (isVisible || !animateOnScroll) return
    if (typeof IntersectionObserver === 'undefined') return

    const node = cardRef.current
    if (!node) return

    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            setIsVisible(true)
            observer.unobserve(entry.target)
          }
        }
      },
      {
        rootMargin: '40px 0px',
        threshold: 0.05,
      },
    )

    observer.observe(node)

    return () => {
      observer.disconnect()
    }
  }, [isVisible, animateOnScroll])

  if (!dataset || !dataset.id || !dataset.slug) {
    return null
  }

  const renderVerificationBadge = (status?: string) => {
    switch (status) {
      case 'verified':
        return (
          <span
            title="Metadata checked against cited documentation; underlying data has not been audited"
            className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800"
          >
            <ShieldCheck className="w-3 h-3 text-emerald-500" />
            Metadata checked
          </span>
        )
      case 'provisional':
        return (
          <span
            title="Metadata is provisional and pending review"
            className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-amber-50 text-amber-700 dark:bg-amber-950/60 dark:text-amber-300 border border-amber-200 dark:border-amber-800"
          >
            <AlertCircle className="w-3 h-3 text-amber-500" />
            Review pending
          </span>
        )
      default:
        return (
          <span
            title="Metadata has not been verified"
            className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300 border border-slate-200 dark:border-slate-700"
          >
            <HelpCircle className="w-3 h-3 text-slate-400" />
            Not reviewed
          </span>
        )
    }
  }

  const renderLicenseBadge = (license?: DatasetMetadata['license']) => {
    if (!license) {
      return (
        <span
          title="License unspecified"
          className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium border bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300 border-slate-200 dark:border-slate-700"
        >
          <Scale className="w-3 h-3 opacity-70" />
          <span className="truncate max-w-[140px]">Unspecified</span>
        </span>
      )
    }

    const isVerifiedOpen = license.status === 'verified_open'
    const isUnspecifiedOrUnknown =
      license.status === 'unspecified_by_source' || license.status === 'unknown'
    const badgeLabel =
      license.spdx_id ||
      license.name ||
      (license.status === 'unspecified_by_source' ? 'Unspecified' : 'Unknown')

    return (
      <span
        title={license.notes || license.name || (isUnspecifiedOrUnknown ? 'License unspecified' : 'License details')}
        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium border ${
          isVerifiedOpen
            ? 'bg-blue-50 text-blue-700 dark:bg-blue-950/60 dark:text-blue-300 border-blue-200 dark:border-blue-800'
            : isUnspecifiedOrUnknown
              ? 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300 border-slate-200 dark:border-slate-700'
              : 'bg-purple-50 text-purple-700 dark:bg-purple-950/60 dark:text-purple-300 border-purple-200 dark:border-purple-800'
        }`}
      >
        <Scale className="w-3 h-3 opacity-70" />
        <span className="truncate max-w-[140px]">{badgeLabel}</span>
      </span>
    )
  }

  const modalities = Array.isArray(dataset.modalities) ? dataset.modalities : []
  const tasks = Array.isArray(dataset.tasks) ? dataset.tasks : []
  const tags = Array.isArray(dataset.tags) ? dataset.tags : []
  const publisherName = dataset.publisher?.name || 'Unknown Publisher'
  const verificationStatus = dataset.verification?.status || 'unverified'

  return (
    <article
      ref={cardRef}
      onFocusCapture={() => setIsVisible(true)}
      data-testid={`dataset-card-${dataset.id}`}
      data-revealed={isVisible ? 'true' : 'false'}
      className={`group min-w-0 flex flex-col justify-between p-6 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/60 hover:border-indigo-400 dark:hover:border-indigo-600 transition-all duration-300 ease-out hover:-translate-y-0.5 hover:shadow-md motion-reduce:transition-none motion-reduce:transform-none motion-reduce:opacity-100 ${
        isVisible
          ? 'opacity-100 translate-y-0'
          : 'opacity-0 translate-y-2.5'
      }`}
    >
      <div>
        {/* Top Badges */}
        <div className="flex items-center justify-between gap-2 mb-3 flex-wrap">
          <div className="flex items-center gap-1.5 flex-wrap">
            {modalities.map((modality) => (
              <span
                key={modality}
                className="px-2 py-0.5 rounded text-xs font-semibold uppercase tracking-wider bg-indigo-50 text-indigo-700 dark:bg-indigo-950/60 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800"
              >
                {modality}
              </span>
            ))}
            {renderLicenseBadge(dataset.license)}
          </div>
          {renderVerificationBadge(verificationStatus)}
        </div>

        {/* Dataset Title & Publisher */}
        <h3 className="text-xl font-bold text-slate-900 dark:text-white group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors">
          <Link to={`/dataset/${dataset.slug}`} className="focus:outline-hidden focus:underline">
            {dataset.name}
          </Link>
        </h3>

        <div className="flex items-center gap-1.5 text-xs text-slate-500 dark:text-slate-400 mt-1 mb-3">
          <Building2 className="w-3.5 h-3.5 shrink-0" />
          <span className="truncate">{publisherName}</span>
        </div>

        {/* Short Description */}
        <p className="text-sm text-slate-600 dark:text-slate-300 line-clamp-3 leading-relaxed mb-4">
          {dataset.description}
        </p>

        {/* Tasks and Tags */}
        <div className="flex flex-wrap gap-1.5 mb-5">
          {tasks.map((task) => (
            <span
              key={task}
              className="px-2 py-0.5 rounded text-xs bg-slate-100 text-slate-700 dark:bg-slate-800/80 dark:text-slate-300"
            >
              #{task}
            </span>
          ))}
          {tags.slice(0, 3).map((tag) => (
            <span
              key={tag}
              className="px-2 py-0.5 rounded text-xs bg-slate-50 text-slate-500 dark:bg-slate-800/40 dark:text-slate-400 border border-slate-200 dark:border-slate-800"
            >
              {tag}
            </span>
          ))}
        </div>
      </div>

      {/* Card Action Link */}
      <div className="pt-4 border-t border-slate-100 dark:border-slate-800/80 flex flex-wrap gap-3 items-center justify-between text-xs">
        <span className="text-slate-400 font-mono break-all">id: {dataset.id}</span>
        <Link
          to={`/dataset/${dataset.slug}`}
          aria-label={`View details for ${dataset.name}`}
          className="inline-flex items-center gap-1 font-semibold text-indigo-600 dark:text-indigo-400 hover:gap-1.5 transition-all"
        >
          <span>View Details</span>
          <ArrowRight className="w-3.5 h-3.5" />
        </Link>
      </div>
    </article>
  )
}
