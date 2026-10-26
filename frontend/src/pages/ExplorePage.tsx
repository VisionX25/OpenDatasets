import React from 'react'
import {
  Search,
  Filter,
  Sparkles,
  Layers,
  Image,
  FileText,
  Volume2,
  Table,
  Cpu,
  Clock,
} from 'lucide-react'

export const ExplorePage: React.FC = () => {
  const plannedModalities = [
    {
      name: 'Computer Vision',
      icon: Image,
      description: 'Image classification, object detection, segmentation, and video streams.',
      count: 'Planned',
    },
    {
      name: 'Natural Language Processing',
      icon: FileText,
      description: 'Instruction tuning, question answering, summarization, and multilingual corpora.',
      count: 'Planned',
    },
    {
      name: 'Audio & Speech',
      icon: Volume2,
      description: 'Speech recognition, acoustic classification, and musical synthesis.',
      count: 'Planned',
    },
    {
      name: 'Tabular & Time-Series',
      icon: Table,
      description: 'Structured financial records, sensor logs, telemetry, and forecasting sets.',
      count: 'Planned',
    },
    {
      name: 'Multimodal & Generative',
      icon: Cpu,
      description: 'Vision-language paired data, diffusion prompts, and multi-sensor datasets.',
      count: 'Planned',
    },
    {
      name: 'Evaluation & Benchmarks',
      icon: Layers,
      description: 'Standardized evaluation datasets, human preference benchmarks, and safety audits.',
      count: 'Planned',
    },
  ]

  return (
    <div className="flex-1 py-10 md:py-16">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Page Header */}
        <div className="border-b border-slate-200 dark:border-slate-800 pb-8 mb-8">
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-indigo-600 dark:text-indigo-400 mb-2">
            <Layers className="w-4 h-4" />
            <span>Dataset Catalog</span>
          </div>
          <h1 className="text-3xl sm:text-4xl font-extrabold text-slate-900 dark:text-white tracking-tight">
            Explore Datasets
          </h1>
          <p className="mt-2 text-base text-slate-600 dark:text-slate-400 max-w-3xl">
            Browse verified Machine Learning datasets with rich schema previews, license validation, and quality metrics.
          </p>
        </div>

        {/* Placeholder Notice */}
        <div className="rounded-xl border border-indigo-200 dark:border-indigo-900/60 bg-indigo-50/50 dark:bg-indigo-950/20 p-6 sm:p-8 mb-10">
          <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4">
            <div className="w-12 h-12 rounded-lg bg-indigo-600 text-white flex items-center justify-center shrink-0 shadow-sm">
              <Sparkles className="w-6 h-6" />
            </div>
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <h2 className="text-lg font-bold text-slate-900 dark:text-white">
                  Exploration Engine Under Construction
                </h2>
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-semibold bg-amber-100 text-amber-800 dark:bg-amber-900/60 dark:text-amber-300">
                  <Clock className="w-3 h-3" />
                  Upcoming Milestone
                </span>
              </div>
              <p className="mt-1 text-sm text-slate-600 dark:text-slate-300 leading-relaxed">
                Task 01 initializes the foundational application shell. Dynamic dataset browsing, faceted search, filtering by task/license, and interactive dataset schema visualizers will be introduced in subsequent incremental tasks.
              </p>
            </div>
          </div>
        </div>

        {/* Mock Search & Filter Bar (Disabled / Visual Preview) */}
        <div className="opacity-70 pointer-events-none mb-10">
          <div className="flex flex-col sm:flex-row gap-3">
            <div className="relative flex-1">
              <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
              <input
                type="text"
                disabled
                placeholder="Search datasets by title, task, domain, or author (coming soon)..."
                className="w-full pl-10 pr-4 py-2.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-sm placeholder:text-slate-400 cursor-not-allowed"
              />
            </div>
            <div className="flex gap-2">
              <button
                type="button"
                disabled
                className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-sm font-medium text-slate-600 dark:text-slate-300 cursor-not-allowed"
              >
                <Filter className="w-4 h-4" />
                <span>Filters</span>
              </button>
            </div>
          </div>
        </div>

        {/* Planned Modalities Preview Grid */}
        <div>
          <h2 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">
            Planned Dataset Modalities
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {plannedModalities.map((item) => {
              const Icon = item.icon
              return (
                <div
                  key={item.name}
                  className="p-5 rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/50 hover:border-slate-300 dark:hover:border-slate-700 transition-colors"
                >
                  <div className="flex items-center justify-between mb-3">
                    <div className="w-10 h-10 rounded-md bg-slate-100 dark:bg-slate-800 flex items-center justify-center text-slate-700 dark:text-slate-300">
                      <Icon className="w-5 h-5 text-indigo-500" />
                    </div>
                    <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400">
                      {item.count}
                    </span>
                  </div>
                  <h3 className="font-semibold text-slate-900 dark:text-white text-base">
                    {item.name}
                  </h3>
                  <p className="mt-1 text-xs text-slate-500 dark:text-slate-400 leading-relaxed">
                    {item.description}
                  </p>
                </div>
              )
            })}
          </div>
        </div>
      </div>
    </div>
  )
}
