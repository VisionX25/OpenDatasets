import React from 'react'
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
}

export const DatasetCard: React.FC<DatasetCardProps> = ({ dataset }) => {
  const renderVerificationBadge = (status: string) => {
    switch (status) {
      case 'verified':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800">
            <ShieldCheck className="w-3 h-3 text-emerald-500" />
            Verified
          </span>
        )
      case 'provisional':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-amber-50 text-amber-700 dark:bg-amber-950/60 dark:text-amber-300 border border-amber-200 dark:border-amber-800">
            <AlertCircle className="w-3 h-3 text-amber-500" />
            Provisional
          </span>
        )
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300 border border-slate-200 dark:border-slate-700">
            <HelpCircle className="w-3 h-3 text-slate-400" />
            Unverified
          </span>
        )
    }
  }

  const renderLicenseBadge = (license: DatasetMetadata['license']) => {
    const isVerifiedOpen = license.status === 'verified_open'
    const isUnspecified = license.status === 'unspecified_by_source'

    return (
      <span
        title={license.notes || license.name}
        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium border ${
          isVerifiedOpen
            ? 'bg-blue-50 text-blue-700 dark:bg-blue-950/60 dark:text-blue-300 border-blue-200 dark:border-blue-800'
            : isUnspecified
              ? 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300 border-slate-200 dark:border-slate-700'
              : 'bg-purple-50 text-purple-700 dark:bg-purple-950/60 dark:text-purple-300 border-purple-200 dark:border-purple-800'
        }`}
      >
        <Scale className="w-3 h-3 opacity-70" />
        <span className="truncate max-w-[140px]">{license.spdx_id || license.name}</span>
      </span>
    )
  }

  return (
    <article className="group flex flex-col justify-between p-6 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/60 hover:border-indigo-400 dark:hover:border-indigo-600 transition-all hover:shadow-md">
      <div>
        {/* Top Badges */}
        <div className="flex items-center justify-between gap-2 mb-3">
          <div className="flex items-center gap-1.5 flex-wrap">
            {dataset.modalities.map((modality) => (
              <span
                key={modality}
                className="px-2 py-0.5 rounded text-xs font-semibold uppercase tracking-wider bg-indigo-50 text-indigo-700 dark:bg-indigo-950/60 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800"
              >
                {modality}
              </span>
            ))}
            {renderLicenseBadge(dataset.license)}
          </div>
          {renderVerificationBadge(dataset.verification.status)}
        </div>

        {/* Dataset Title & Publisher */}
        <h3 className="text-xl font-bold text-slate-900 dark:text-white group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors">
          <Link to={`/datasets/${dataset.slug}`} className="focus:outline-hidden focus:underline">
            {dataset.name}
          </Link>
        </h3>

        <div className="flex items-center gap-1.5 text-xs text-slate-500 dark:text-slate-400 mt-1 mb-3">
          <Building2 className="w-3.5 h-3.5 shrink-0" />
          <span className="truncate">{dataset.publisher.name}</span>
        </div>

        {/* Short Description */}
        <p className="text-sm text-slate-600 dark:text-slate-300 line-clamp-3 leading-relaxed mb-4">
          {dataset.description}
        </p>

        {/* Tasks and Tags */}
        <div className="flex flex-wrap gap-1.5 mb-5">
          {dataset.tasks.map((task) => (
            <span
              key={task}
              className="px-2 py-0.5 rounded text-xs bg-slate-100 text-slate-700 dark:bg-slate-800/80 dark:text-slate-300"
            >
              #{task}
            </span>
          ))}
          {dataset.tags.slice(0, 3).map((tag) => (
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
      <div className="pt-4 border-t border-slate-100 dark:border-slate-800/80 flex items-center justify-between text-xs">
        <span className="text-slate-400 font-mono">id: {dataset.id}</span>
        <Link
          to={`/datasets/${dataset.slug}`}
          className="inline-flex items-center gap-1 font-semibold text-indigo-600 dark:text-indigo-400 hover:gap-1.5 transition-all"
        >
          <span>View Details</span>
          <ArrowRight className="w-3.5 h-3.5" />
        </Link>
      </div>
    </article>
  )
}
