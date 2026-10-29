import React from 'react'
import {
  Info,
  Shield,
  Layers,
  Code,
  HeartHandshake,
  CheckCircle,
  ExternalLink,
} from 'lucide-react'
import { GithubIcon } from '../components/icons/GithubIcon'

export const AboutPage: React.FC = () => {
  return (
    <div className="flex-1 py-10 md:py-16">
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="border-b border-slate-200 dark:border-slate-800 pb-8 mb-10">
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-indigo-600 dark:text-indigo-400 mb-2">
            <Info className="w-4 h-4" />
            <span>About The Platform</span>
          </div>
          <h1 className="text-3xl sm:text-4xl font-extrabold text-slate-900 dark:text-white tracking-tight">
            About OpenDatasets
          </h1>
          <p className="mt-2 text-base text-slate-600 dark:text-slate-400 leading-relaxed">
            An open-source initiative by <span className="font-semibold text-slate-900 dark:text-slate-200">VisionX25</span> to make machine learning dataset information easier to discover and inspect.
          </p>
        </div>

        {/* Mission Statement */}
        <div className="prose dark:prose-invert max-w-none mb-12">
          <h2 className="text-xl font-bold text-slate-900 dark:text-white mb-3">
            Our Mission
          </h2>
          <p className="text-slate-600 dark:text-slate-300 leading-relaxed mb-4">
            High-quality datasets are the bedrock of reliable Machine Learning and Artificial Intelligence models. However, discovering trustworthy datasets, understanding their licensing nuances, and evaluating their internal quality often requires navigating disjointed repositories and manual inspection.
          </p>
          <p className="text-slate-600 dark:text-slate-300 leading-relaxed">
            OpenDatasets brings dataset descriptions, source references, license information, and documented counts into one searchable catalog. It catalogs metadata and links to publishers; it does not host the underlying datasets, calculate distribution statistics, or audit label accuracy.
          </p>
        </div>

        {/* Guiding Principles */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
          <div className="p-5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900">
            <div className="w-10 h-10 rounded-lg bg-indigo-50 dark:bg-indigo-950/60 flex items-center justify-center text-indigo-600 dark:text-indigo-400 mb-3">
              <Shield className="w-5 h-5" />
            </div>
            <h3 className="font-bold text-slate-900 dark:text-white text-base mb-1">
              Metadata Checks
            </h3>
            <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
              Metadata is reviewed against cited sources. Automated checks validate structure and URL syntax without downloading data or testing source availability.
            </p>
          </div>

          <div className="p-5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900">
            <div className="w-10 h-10 rounded-lg bg-violet-50 dark:bg-violet-950/60 flex items-center justify-center text-violet-600 dark:text-violet-400 mb-3">
              <Layers className="w-5 h-5" />
            </div>
            <h3 className="font-bold text-slate-900 dark:text-white text-base mb-1">
              Open & Reproducible
            </h3>
            <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
              The application code uses the MIT license. Each external dataset retains its own license and access conditions.
            </p>
          </div>

          <div className="p-5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900">
            <div className="w-10 h-10 rounded-lg bg-emerald-50 dark:bg-emerald-950/60 flex items-center justify-center text-emerald-600 dark:text-emerald-400 mb-3">
              <HeartHandshake className="w-5 h-5" />
            </div>
            <h3 className="font-bold text-slate-900 dark:text-white text-base mb-1">
              Community First
            </h3>
            <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
              Researchers, engineers, and educators can suggest datasets, correct metadata, and contribute through GitHub issues and pull requests.
            </p>
          </div>
        </div>

        {/* Technology Stack */}
        <div className="bg-slate-100/70 dark:bg-slate-900/70 rounded-xl p-6 sm:p-8 border border-slate-200 dark:border-slate-800 mb-12">
          <div className="flex items-center gap-2 mb-4">
            <Code className="w-5 h-5 text-indigo-500" />
            <h2 className="text-lg font-bold text-slate-900 dark:text-white">
              Technology Stack
            </h2>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm">
            <div className="space-y-2">
              <span className="font-semibold text-slate-900 dark:text-white">Frontend (Current)</span>
              <ul className="space-y-1.5 text-xs text-slate-600 dark:text-slate-400">
                <li className="flex items-center gap-2">
                  <CheckCircle className="w-3.5 h-3.5 text-emerald-500" />
                  <span>React 19 + TypeScript</span>
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle className="w-3.5 h-3.5 text-emerald-500" />
                  <span>Vite Build System</span>
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle className="w-3.5 h-3.5 text-emerald-500" />
                  <span>Tailwind CSS</span>
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle className="w-3.5 h-3.5 text-emerald-500" />
                  <span>React Router</span>
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle className="w-3.5 h-3.5 text-emerald-500" />
                  <span>Lucide React Icons</span>
                </li>
              </ul>
            </div>
            <div className="space-y-2">
              <span className="font-semibold text-slate-900 dark:text-white">Current Checks & Planned Work</span>
              <ul className="space-y-1.5 text-xs text-slate-600 dark:text-slate-400">
                <li className="flex items-center gap-2">
                  <span className="w-3.5 h-3.5 rounded-full bg-slate-300 dark:bg-slate-700 flex items-center justify-center text-[9px] text-slate-600">●</span>
                  <span>Python + FastAPI (future task)</span>
                </li>
                <li className="flex items-center gap-2">
                  <span className="w-3.5 h-3.5 rounded-full bg-slate-300 dark:bg-slate-700 flex items-center justify-center text-[9px] text-slate-600">●</span>
                  <span>Python metadata validation (available)</span>
                </li>
                <li className="flex items-center gap-2">
                  <span className="w-3.5 h-3.5 rounded-full bg-slate-300 dark:bg-slate-700 flex items-center justify-center text-[9px] text-slate-600">●</span>
                  <span>GitHub Actions CI (available)</span>
                </li>
              </ul>
            </div>
          </div>
        </div>

        {/* Contributing & Repository */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between p-6 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 gap-4">
          <div>
            <h3 className="font-bold text-slate-900 dark:text-white text-base">
              Get Involved
            </h3>
            <p className="text-xs text-slate-600 dark:text-slate-400 mt-1">
              OpenDatasets is developed in the open. Contributions, feature suggestions, and dataset submissions are welcome.
            </p>
          </div>
          <a
            href="https://github.com/VisionX25/OpenDatasets"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-slate-900 hover:bg-slate-800 dark:bg-white dark:hover:bg-slate-100 text-white dark:text-slate-900 text-sm font-medium transition-colors shrink-0"
          >
            <GithubIcon className="w-4 h-4" />
            <span>GitHub Repository</span>
            <ExternalLink className="w-3.5 h-3.5 opacity-60" />
          </a>
        </div>
      </div>
    </div>
  )
}
