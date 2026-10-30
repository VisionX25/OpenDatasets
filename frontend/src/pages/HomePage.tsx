import React from 'react'
import { Link } from 'react-router-dom'
import {
  ArrowRight,
  Database,
  ShieldCheck,
  Layers,
  Sparkles,
  GitBranch,
  Terminal,
  FileCheck,
  CheckCircle2,
} from 'lucide-react'

export const HomePage: React.FC = () => {
  return (
    <div className="flex-1">
      {/* Hero Section */}
      <section className="relative overflow-hidden pt-12 pb-16 md:pt-20 md:pb-28">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          {/* Badge */}
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-medium bg-indigo-50 dark:bg-indigo-950/70 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800 mb-6 shadow-xs">
            <Sparkles className="w-3.5 h-3.5 text-indigo-500" />
            <span>Open-source dataset metadata catalog</span>
          </div>

          {/* Heading */}
          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold text-slate-900 dark:text-white tracking-tight max-w-4xl mx-auto leading-tight">
            Discover & Explore{' '}
            <span className="bg-gradient-to-r from-indigo-600 to-violet-600 dark:from-indigo-400 dark:to-violet-400 bg-clip-text text-transparent">
              Machine Learning Datasets
            </span>
          </h1>

          {/* Subtitle */}
          <p className="mt-6 text-lg sm:text-xl text-slate-600 dark:text-slate-300 max-w-2xl mx-auto leading-relaxed">
            Find machine learning datasets with structured metadata, source references, and documented license information.
          </p>

          {/* CTA Buttons */}
          <div className="mt-8 flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link
              to="/explore"
              className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-6 py-3 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white font-medium shadow-sm transition-all hover:shadow hover:gap-3"
            >
              <span>Explore Datasets</span>
              <ArrowRight className="w-4 h-4" />
            </Link>
            <Link
              to="/about"
              className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-6 py-3 rounded-lg bg-white dark:bg-slate-800 hover:bg-slate-100 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 font-medium border border-slate-300 dark:border-slate-700 transition-colors"
            >
              <span>About OpenDatasets</span>
            </Link>
          </div>
        </div>
      </section>

      {/* Feature Pillars */}
      <section className="py-12 bg-white dark:bg-slate-900 border-y border-slate-200 dark:border-slate-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-2xl mx-auto mb-12">
            <h2 className="text-2xl sm:text-3xl font-bold text-slate-900 dark:text-white">
              Built for Modern Machine Learning Workflows
            </h2>
            <p className="mt-3 text-slate-600 dark:text-slate-400 text-sm sm:text-base">
              Explore documented dataset information and follow the cited sources to evaluate suitability for your work.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {/* Card 1 */}
            <div className="p-6 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/80 hover:border-indigo-300 dark:hover:border-indigo-700 transition-colors">
              <div className="w-12 h-12 rounded-lg bg-indigo-100 dark:bg-indigo-900/50 flex items-center justify-center text-indigo-600 dark:text-indigo-400 mb-4">
                <Database className="w-6 h-6" />
              </div>
              <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-2">
                Curated Discovery
              </h3>
              <p className="text-sm text-slate-600 dark:text-slate-400 leading-relaxed">
                Locate datasets across vision, NLP, audio, and other domains. Review license and access information, including explicitly unknown terms.
              </p>
            </div>

            {/* Card 2 */}
            <div className="p-6 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/80 hover:border-indigo-300 dark:hover:border-indigo-700 transition-colors">
              <div className="w-12 h-12 rounded-lg bg-violet-100 dark:bg-violet-900/50 flex items-center justify-center text-violet-600 dark:text-violet-400 mb-4">
                <ShieldCheck className="w-6 h-6" />
              </div>
              <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-2">
                Metadata Validation
              </h3>
              <p className="text-sm text-slate-600 dark:text-slate-400 leading-relaxed">
                Offline checks validate metadata structure, URL syntax, unique identifiers, and catalog consistency. They do not inspect the underlying data or test live links.
              </p>
            </div>

            {/* Card 3 */}
            <div className="p-6 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/80 hover:border-indigo-300 dark:hover:border-indigo-700 transition-colors">
              <div className="w-12 h-12 rounded-lg bg-emerald-100 dark:bg-emerald-900/50 flex items-center justify-center text-emerald-600 dark:text-emerald-400 mb-4">
                <Layers className="w-6 h-6" />
              </div>
              <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-2">
                Interactive Exploration
              </h3>
              <p className="text-sm text-slate-600 dark:text-slate-400 leading-relaxed">
                Browse categories, search descriptions and tasks, and inspect publisher references and documented counts without downloading the datasets.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Tech Stack & Architecture Overview */}
      <section className="py-12 md:py-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="bg-gradient-to-br from-indigo-50 to-slate-100 dark:from-slate-900 dark:to-slate-800/70 rounded-2xl p-6 sm:p-10 border border-indigo-100 dark:border-slate-700/80">
            <div className="max-w-3xl">
              <span className="text-xs font-bold uppercase tracking-wider text-indigo-600 dark:text-indigo-400">
                Architecture & Roadmap
              </span>
              <h2 className="mt-2 text-2xl font-bold text-slate-900 dark:text-white">
                Incremental, Open Development
              </h2>
              <p className="mt-3 text-slate-600 dark:text-slate-300 text-sm sm:text-base leading-relaxed">
                The current app provides search, category browsing, dataset details, and automated metadata checks in CI. Data profiling, distribution metrics, and a FastAPI service remain planned work.
              </p>

              <div className="mt-6 grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
                <div className="flex items-center gap-2 text-slate-700 dark:text-slate-300">
                  <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0" />
                  <span>React 19 + TypeScript frontend shell</span>
                </div>
                <div className="flex items-center gap-2 text-slate-700 dark:text-slate-300">
                  <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0" />
                  <span>Tailwind CSS & Lucide React icons</span>
                </div>
                <div className="flex items-center gap-2 text-slate-700 dark:text-slate-300">
                  <GitBranch className="w-4 h-4 text-indigo-500 shrink-0" />
                  <span>Client-side routing via React Router</span>
                </div>
                <div className="flex items-center gap-2 text-slate-700 dark:text-slate-300">
                  <Terminal className="w-4 h-4 text-indigo-500 shrink-0" />
                  <span>Strict TypeScript & ESLint verification</span>
                </div>
              </div>

              <div className="mt-6 pt-6 border-t border-indigo-200/60 dark:border-slate-700/60 flex items-center gap-4 text-xs text-slate-500 dark:text-slate-400">
                <FileCheck className="w-4 h-4 text-slate-400" />
                <span>OpenDatasets by VisionX25 • MIT Licensed Open Source</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Contribute to OpenDatasets Section */}
      <section className="pb-16 md:pb-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-800/50 p-6 sm:p-8 md:p-10 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-6 shadow-xs">
            <div className="max-w-2xl">
              <span className="text-xs font-bold uppercase tracking-wider text-indigo-600 dark:text-indigo-400">
                Community
              </span>
              <h2 className="mt-1 text-xl sm:text-2xl font-bold text-slate-900 dark:text-white">
                Contribute to OpenDatasets
              </h2>
              <p className="mt-2 text-sm sm:text-base text-slate-600 dark:text-slate-300 leading-relaxed">
                Know of an open machine learning dataset with clear documentation and licensing? Suggest it to help expand our verified metadata catalog.
              </p>
            </div>
            <Link
              to="/submit"
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white font-medium text-sm transition-colors shrink-0"
            >
              <span>Submit Dataset</span>
              <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
        </div>
      </section>
    </div>
  )
}
