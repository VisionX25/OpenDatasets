import React from 'react'
import { Database, Heart } from 'lucide-react'
import { Link } from 'react-router-dom'
import { GithubIcon } from './icons/GithubIcon'

export const Footer: React.FC = () => {
  return (
    <footer className="mt-auto border-t border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 text-slate-600 dark:text-slate-400">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 md:py-12">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-8">
          {/* Brand Info */}
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <div className="flex items-center justify-center w-7 h-7 rounded-md bg-indigo-600 text-white">
                <Database className="w-4 h-4" />
              </div>
              <span className="font-bold text-slate-900 dark:text-white text-lg">
                OpenDatasets
              </span>
            </div>
            <p className="text-sm text-slate-500 dark:text-slate-400">
              An independent open-source catalog for discovering machine learning datasets and inspecting their metadata.
            </p>
          </div>

          {/* Quick Links */}
          <div className="space-y-3">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-900 dark:text-white">
              Navigation
            </h3>
            <ul className="space-y-2 text-sm">
              <li>
                <Link to="/" className="hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors">
                  Home
                </Link>
              </li>
              <li>
                <Link to="/explore" className="hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors">
                  Explore Datasets
                </Link>
              </li>
              <li>
                <Link to="/about" className="hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors">
                  About & Roadmap
                </Link>
              </li>
            </ul>
          </div>

          {/* Contribute */}
          <div className="space-y-3">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-900 dark:text-white">
              Contribute
            </h3>
            <ul className="space-y-2 text-sm">
              <li>
                <Link to="/submit" className="hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors">
                  Submit a Dataset
                </Link>
              </li>
              <li>
                <a
                  href="https://github.com/VisionX25/OpenDatasets/blob/main/CONTRIBUTING.md"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors"
                >
                  Contribution Guide
                </a>
              </li>
              <li>
                <a
                  href="https://github.com/VisionX25/OpenDatasets/issues"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors"
                >
                  Report an Issue
                </a>
              </li>
            </ul>
          </div>

          {/* Community & Open Source */}
          <div className="space-y-3">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-900 dark:text-white">
              Community & Project
            </h3>
            <ul className="space-y-2 text-sm">
              <li>
                <a
                  href="https://github.com/VisionX25/OpenDatasets"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors"
                >
                  <GithubIcon className="w-4 h-4" />
                  GitHub Repository
                </a>
              </li>
              <li className="text-xs text-slate-500">
                Maintained by <span className="font-medium text-slate-700 dark:text-slate-300">VisionX25</span>
              </li>
            </ul>
          </div>
        </div>

        <div className="mt-8 pt-6 border-t border-slate-200 dark:border-slate-800 flex flex-col sm:flex-row items-center justify-between text-xs text-slate-500 dark:text-slate-400 gap-4">
          <p>© 2026 VisionX25. Application code: MIT. Dataset licenses vary.</p>
          <p className="inline-flex items-center gap-1">
            Built with <Heart className="w-3.5 h-3.5 text-rose-500 fill-rose-500" /> for the Machine Learning community
          </p>
        </div>
      </div>
    </footer>
  )
}
