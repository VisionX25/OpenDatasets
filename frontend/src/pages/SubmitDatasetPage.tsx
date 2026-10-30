import React, { useState, useEffect, useMemo, useId } from 'react'
import { Link } from 'react-router-dom'
import {
  FilePlus2,
  AlertTriangle,
  CheckCircle2,
  Copy,
  ExternalLink,
  Info,
  ShieldCheck,
  ArrowRight,
  BookOpen,
  Sparkles,
} from 'lucide-react'
import { GithubIcon } from '../components/icons/GithubIcon'
import { CATEGORIES } from '../utils/datasetFilters'
import { fetchCatalog } from '../services/catalogService'
import type { DatasetMetadata } from '../types/dataset'
import { findPotentialDuplicates } from '../utils/duplicateDetector'
import { copyTextToClipboard } from '../utils/clipboard'
import {
  type SubmissionFormData,
  INITIAL_SUBMISSION_FORM,
  isValidHttpUrl,
  formatSubmissionMarkdown,
  buildGitHubIssueUrl,
} from '../utils/submissionUtils'

export const SubmitDatasetPage: React.FC = () => {
  const [formData, setFormData] = useState<SubmissionFormData>(INITIAL_SUBMISSION_FORM)
  const [catalog, setCatalog] = useState<DatasetMetadata[]>([])
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [copied, setCopied] = useState(false)
  const [generatedMarkdown, setGeneratedMarkdown] = useState<string | null>(null)
  const [hasAttemptedSubmit, setHasAttemptedSubmit] = useState(false)

  const nameId = useId()
  const sourceUrlId = useId()
  const categoryId = useId()
  const taskId = useId()
  const descriptionId = useId()
  const doiId = useId()
  const licenseId = useId()
  const paperUrlId = useId()
  const notesId = useId()

  // Load catalog for advisory duplicate detection
  useEffect(() => {
    let isMounted = true
    fetchCatalog()
      .then((records) => {
        if (isMounted) setCatalog(records)
      })
      .catch(() => {
        // Non-blocking: duplicate detection is an advisory enhancement
      })
    return () => {
      isMounted = false
    }
  }, [])

  // Derived duplicate matches using useMemo (no cascading setState in effects)
  const duplicates = useMemo(() => {
    if (catalog.length === 0) return []
    return findPotentialDuplicates(
      {
        name: formData.name,
        sourceUrl: formData.sourceUrl,
        doi: formData.doi,
        paperUrl: formData.paperUrl,
      },
      catalog,
    )
  }, [formData.name, formData.sourceUrl, formData.doi, formData.paperUrl, catalog])

  const validateField = (field: keyof SubmissionFormData, value: string): string | null => {
    switch (field) {
      case 'name':
        if (!value.trim()) return 'Dataset name is required.'
        if (value.trim().length < 2) return 'Dataset name must be at least 2 characters.'
        return null
      case 'sourceUrl':
        if (!value.trim()) return 'Official dataset URL is required.'
        if (!isValidHttpUrl(value.trim())) return 'Please enter a valid HTTP or HTTPS URL.'
        return null
      case 'category':
        if (!value.trim()) return 'Please select a primary category.'
        return null
      case 'task':
        if (!value.trim()) return 'Research task or intended use is required.'
        return null
      case 'description':
        if (!value.trim()) return 'Short description is required.'
        if (value.trim().length < 10) return 'Description must be at least 10 characters.'
        return null
      case 'paperUrl':
        if (value.trim() && !isValidHttpUrl(value.trim())) {
          return 'Supporting paper URL must be a valid HTTP or HTTPS URL.'
        }
        return null
      default:
        return null
    }
  }

  const validateAll = (): boolean => {
    const newErrors: Record<string, string> = {}
    ;(Object.keys(formData) as Array<keyof SubmissionFormData>).forEach((field) => {
      const err = validateField(field, formData[field])
      if (err) {
        newErrors[field] = err
      }
    })
    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>,
  ) => {
    const { name, value } = e.target
    const updated = { ...formData, [name]: value }
    setFormData(updated)
    setGeneratedMarkdown(null)
    setCopied(false)

    if (hasAttemptedSubmit) {
      const err = validateField(name as keyof SubmissionFormData, value)
      setErrors((prev) => {
        const next = { ...prev }
        if (err) {
          next[name] = err
        } else {
          delete next[name]
        }
        return next
      })
    }
  }

  const handleSubmitAndContinue = async (e: React.FormEvent) => {
    e.preventDefault()
    setHasAttemptedSubmit(true)

    if (!validateAll()) {
      return
    }

    const md = formatSubmissionMarkdown(formData)
    setGeneratedMarkdown(md)

    const success = await copyTextToClipboard(md)
    if (success) {
      setCopied(true)
      setTimeout(() => setCopied(false), 3000)
    }

    const issueResult = buildGitHubIssueUrl(formData)

    // Attempt to open GitHub in a new tab if supported
    if (typeof window !== 'undefined' && typeof window.open === 'function') {
      window.open(issueResult.url, '_blank', 'noopener,noreferrer')
    }

    setTimeout(() => {
      document.getElementById('submission-handoff')?.scrollIntoView({ behavior: 'smooth' })
    }, 100)
  }

  const handleCopyOnly = async () => {
    setHasAttemptedSubmit(true)

    if (!validateAll()) {
      return
    }

    const md = formatSubmissionMarkdown(formData)
    setGeneratedMarkdown(md)

    const success = await copyTextToClipboard(md)
    if (success) {
      setCopied(true)
      setTimeout(() => setCopied(false), 3000)
    }

    setTimeout(() => {
      document.getElementById('submission-handoff')?.scrollIntoView({ behavior: 'smooth' })
    }, 100)
  }

  const handleCopyAgain = async () => {
    if (!generatedMarkdown) return
    const success = await copyTextToClipboard(generatedMarkdown)
    if (success) {
      setCopied(true)
      setTimeout(() => setCopied(false), 3000)
    }
  }

  const githubIssueResult = useMemo(() => {
    return buildGitHubIssueUrl(formData)
  }, [formData])

  return (
    <div className="flex-1 py-10 md:py-16">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="border-b border-slate-200 dark:border-slate-800 pb-8 mb-8">
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-indigo-600 dark:text-indigo-400 mb-2">
            <FilePlus2 className="w-4 h-4" />
            <span>Contributor Portal</span>
          </div>
          <h1 className="text-3xl sm:text-4xl font-extrabold text-slate-900 dark:text-white tracking-tight">
            Propose a Dataset
          </h1>
          <p className="mt-2 text-base text-slate-600 dark:text-slate-400 leading-relaxed">
            Suggest a new dataset for indexing in OpenDatasets. Fill out the details below to
            generate a formatted proposal ready for review by community maintainers.
          </p>
        </div>

        {/* Contributor Guidance Banner */}
        <div className="bg-indigo-50/60 dark:bg-indigo-950/30 border border-indigo-200/80 dark:border-indigo-900/60 rounded-xl p-5 mb-8">
          <div className="flex items-start gap-3">
            <div className="p-2 rounded-lg bg-indigo-100 dark:bg-indigo-900/60 text-indigo-700 dark:text-indigo-300 shrink-0 mt-0.5">
              <Info className="w-5 h-5" />
            </div>
            <div className="space-y-2 text-xs sm:text-sm text-slate-700 dark:text-slate-300">
              <h2 className="font-bold text-slate-900 dark:text-white text-sm sm:text-base">
                Dataset Contribution Guidelines
              </h2>
              <ul className="list-disc list-inside space-y-1 text-slate-600 dark:text-slate-400">
                <li>
                  <strong>Original Sources:</strong> Provide links to original publishers (Mendeley Data, Zenodo, HuggingFace, Kaggle, university portals).
                </li>
                <li>
                  <strong>Metadata Only:</strong> OpenDatasets indexes dataset metadata. Never upload raw data files, patient records, or private credentials.
                </li>
                <li>
                  <strong>Licensing:</strong> Note verified licenses (e.g., CC BY 4.0, MIT, Non-Commercial). If terms are unspecified, state &ldquo;Unknown&rdquo;.
                </li>
                <li>
                  <strong>Public Peer Review:</strong> Submissions are reviewed publicly via GitHub issues. A free GitHub account is required to open an issue.
                </li>
              </ul>
              <div className="pt-1">
                <a
                  href="https://github.com/VisionX25/OpenDatasets/blob/main/CONTRIBUTING.md"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 font-semibold text-indigo-600 dark:text-indigo-400 hover:underline"
                >
                  <BookOpen className="w-3.5 h-3.5" />
                  <span>Read full CONTRIBUTING.md guide</span>
                  <ExternalLink className="w-3 h-3 ml-0.5 opacity-70" />
                </a>
              </div>
            </div>
          </div>
        </div>

        {/* Advisory Duplicate Warning */}
        {duplicates.length > 0 && (
          <div
            role="region"
            aria-label="Advisory duplicate warning"
            className="mb-8 p-5 rounded-xl border border-amber-300 dark:border-amber-700/80 bg-amber-50/70 dark:bg-amber-950/30 text-amber-900 dark:text-amber-200"
          >
            <div className="flex items-start gap-3">
              <AlertTriangle className="w-5 h-5 text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" />
              <div className="space-y-2 flex-1">
                <h3 className="font-bold text-sm sm:text-base text-amber-900 dark:text-amber-100">
                  Advisory: Similar Dataset(s) Found in Catalog ({duplicates.length})
                </h3>
                <p className="text-xs sm:text-sm text-amber-800 dark:text-amber-300">
                  The OpenDatasets catalog already includes matching or similar records. Please
                  review before submitting to prevent unintentional duplicates:
                </p>
                <div className="space-y-1.5 pt-1">
                  {duplicates.map((match) => (
                    <div
                      key={match.slug}
                      className="flex flex-col sm:flex-row sm:items-center justify-between text-xs bg-white/80 dark:bg-slate-900/80 p-2.5 rounded-lg border border-amber-200 dark:border-amber-800/80 gap-2"
                    >
                      <div>
                        <Link
                          to={`/dataset/${match.slug}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="font-bold text-indigo-600 dark:text-indigo-400 hover:underline inline-flex items-center gap-1"
                        >
                          <span>{match.name}</span>
                          <ExternalLink className="w-3 h-3 opacity-60" />
                        </Link>
                        <p className="text-[11px] text-slate-500 dark:text-slate-400">
                          Match reason: {match.reasons.join(' • ')}
                        </p>
                      </div>
                      <Link
                        to={`/dataset/${match.slug}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 px-2.5 py-1 text-[11px] font-semibold text-slate-700 dark:text-slate-200 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 rounded transition-colors shrink-0"
                      >
                        <span>View existing</span>
                        <ArrowRight className="w-3 h-3" />
                      </Link>
                    </div>
                  ))}
                </div>
                <p className="text-[11px] text-amber-700 dark:text-amber-400 pt-1">
                  If your proposal updates an existing dataset, consider submitting a Metadata
                  Correction issue on GitHub instead.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Main Submission Form */}
        <form onSubmit={handleSubmitAndContinue} noValidate className="space-y-6">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-6 sm:p-8 space-y-6 shadow-xs">
            <h2 className="text-lg font-bold text-slate-900 dark:text-white border-b border-slate-100 dark:border-slate-800 pb-3">
              Dataset Metadata
            </h2>

            {/* Dataset Name */}
            <div>
              <label
                htmlFor={nameId}
                className="block text-sm font-semibold text-slate-900 dark:text-slate-100 mb-1"
              >
                Dataset Name <span className="text-rose-500" aria-hidden="true">*</span>
              </label>
              <input
                id={nameId}
                type="text"
                name="name"
                value={formData.name}
                onChange={handleChange}
                placeholder="e.g. Bangla Grammar QA or ImageNet-1K"
                aria-required="true"
                aria-invalid={Boolean(errors.name)}
                aria-describedby={errors.name ? `${nameId}-error` : `${nameId}-desc`}
                className={`w-full px-3.5 py-2.5 rounded-lg border text-sm bg-white dark:bg-slate-800/80 text-slate-900 dark:text-white transition-colors focus:outline-indigo-500 ${
                  errors.name
                    ? 'border-rose-400 dark:border-rose-600 focus:border-rose-500'
                    : 'border-slate-300 dark:border-slate-700 focus:border-indigo-500'
                }`}
              />
              <p id={`${nameId}-desc`} className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                Official human-readable name of the dataset.
              </p>
              {errors.name && (
                <p id={`${nameId}-error`} role="alert" className="mt-1 text-xs font-semibold text-rose-500">
                  {errors.name}
                </p>
              )}
            </div>

            {/* Official Source URL */}
            <div>
              <label
                htmlFor={sourceUrlId}
                className="block text-sm font-semibold text-slate-900 dark:text-slate-100 mb-1"
              >
                Official Dataset / Source URL <span className="text-rose-500" aria-hidden="true">*</span>
              </label>
              <input
                id={sourceUrlId}
                type="url"
                name="sourceUrl"
                value={formData.sourceUrl}
                onChange={handleChange}
                placeholder="https://data.mendeley.com/datasets/... or https://..."
                aria-required="true"
                aria-invalid={Boolean(errors.sourceUrl)}
                aria-describedby={errors.sourceUrl ? `${sourceUrlId}-error` : `${sourceUrlId}-desc`}
                className={`w-full px-3.5 py-2.5 rounded-lg border text-sm bg-white dark:bg-slate-800/80 text-slate-900 dark:text-white transition-colors focus:outline-indigo-500 ${
                  errors.sourceUrl
                    ? 'border-rose-400 dark:border-rose-600 focus:border-rose-500'
                    : 'border-slate-300 dark:border-slate-700 focus:border-indigo-500'
                }`}
              />
              <p id={`${sourceUrlId}-desc`} className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                Canonical publisher, repository (Mendeley, Zenodo, HuggingFace), or archive page.
              </p>
              {errors.sourceUrl && (
                <p id={`${sourceUrlId}-error`} role="alert" className="mt-1 text-xs font-semibold text-rose-500">
                  {errors.sourceUrl}
                </p>
              )}
            </div>

            {/* Category & Task Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
              {/* Category */}
              <div>
                <label
                  htmlFor={categoryId}
                  className="block text-sm font-semibold text-slate-900 dark:text-slate-100 mb-1"
                >
                  Primary Category <span className="text-rose-500" aria-hidden="true">*</span>
                </label>
                <select
                  id={categoryId}
                  name="category"
                  value={formData.category}
                  onChange={handleChange}
                  aria-required="true"
                  aria-invalid={Boolean(errors.category)}
                  aria-describedby={errors.category ? `${categoryId}-error` : undefined}
                  className={`w-full px-3.5 py-2.5 rounded-lg border text-sm bg-white dark:bg-slate-800/80 text-slate-900 dark:text-white transition-colors focus:outline-indigo-500 ${
                    errors.category
                      ? 'border-rose-400 dark:border-rose-600 focus:border-rose-500'
                      : 'border-slate-300 dark:border-slate-700 focus:border-indigo-500'
                  }`}
                >
                  <option value="">Select a category...</option>
                  {CATEGORIES.map((cat) => (
                    <option key={cat.id} value={cat.id}>
                      {cat.name}
                    </option>
                  ))}
                </select>
                {errors.category && (
                  <p id={`${categoryId}-error`} role="alert" className="mt-1 text-xs font-semibold text-rose-500">
                    {errors.category}
                  </p>
                )}
              </div>

              {/* Research Task */}
              <div>
                <label
                  htmlFor={taskId}
                  className="block text-sm font-semibold text-slate-900 dark:text-slate-100 mb-1"
                >
                  Research Task / Intended Use <span className="text-rose-500" aria-hidden="true">*</span>
                </label>
                <input
                  id={taskId}
                  type="text"
                  name="task"
                  value={formData.task}
                  onChange={handleChange}
                  placeholder="e.g. image-classification, question-answering"
                  aria-required="true"
                  aria-invalid={Boolean(errors.task)}
                  aria-describedby={errors.task ? `${taskId}-error` : `${taskId}-desc`}
                  className={`w-full px-3.5 py-2.5 rounded-lg border text-sm bg-white dark:bg-slate-800/80 text-slate-900 dark:text-white transition-colors focus:outline-indigo-500 ${
                    errors.task
                      ? 'border-rose-400 dark:border-rose-600 focus:border-rose-500'
                      : 'border-slate-300 dark:border-slate-700 focus:border-indigo-500'
                  }`}
                />
                <p id={`${taskId}-desc`} className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                  Supported Machine Learning tasks.
                </p>
                {errors.task && (
                  <p id={`${taskId}-error`} role="alert" className="mt-1 text-xs font-semibold text-rose-500">
                    {errors.task}
                  </p>
                )}
              </div>
            </div>

            {/* Short Description */}
            <div>
              <label
                htmlFor={descriptionId}
                className="block text-sm font-semibold text-slate-900 dark:text-slate-100 mb-1"
              >
                Short Description <span className="text-rose-500" aria-hidden="true">*</span>
              </label>
              <textarea
                id={descriptionId}
                name="description"
                rows={4}
                value={formData.description}
                onChange={handleChange}
                placeholder="Comprehensive summary describing the dataset, its contents, collection methodology, and scientific purpose..."
                aria-required="true"
                aria-invalid={Boolean(errors.description)}
                aria-describedby={errors.description ? `${descriptionId}-error` : `${descriptionId}-desc`}
                className={`w-full px-3.5 py-2.5 rounded-lg border text-sm bg-white dark:bg-slate-800/80 text-slate-900 dark:text-white transition-colors focus:outline-indigo-500 ${
                  errors.description
                    ? 'border-rose-400 dark:border-rose-600 focus:border-rose-500'
                    : 'border-slate-300 dark:border-slate-700 focus:border-indigo-500'
                }`}
              />
              <p id={`${descriptionId}-desc`} className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                Minimum 10 characters. Summarize contents, sample counts, and collection context.
              </p>
              {errors.description && (
                <p id={`${descriptionId}-error`} role="alert" className="mt-1 text-xs font-semibold text-rose-500">
                  {errors.description}
                </p>
              )}
            </div>
          </div>

          {/* Optional Documentation & Evidence */}
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-6 sm:p-8 space-y-6 shadow-xs">
            <div className="border-b border-slate-100 dark:border-slate-800 pb-3 flex items-center justify-between">
              <h2 className="text-lg font-bold text-slate-900 dark:text-white">
                Optional Citations & Access Details
              </h2>
              <span className="text-xs text-slate-400">Optional</span>
            </div>

            {/* DOI & License Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
              {/* DOI */}
              <div>
                <label
                  htmlFor={doiId}
                  className="block text-sm font-semibold text-slate-900 dark:text-slate-100 mb-1"
                >
                  DOI Identifier
                </label>
                <input
                  id={doiId}
                  type="text"
                  name="doi"
                  value={formData.doi}
                  onChange={handleChange}
                  placeholder="e.g. 10.17632/tsdvtzwwpn.1"
                  className="w-full px-3.5 py-2.5 rounded-lg border border-slate-300 dark:border-slate-700 text-sm bg-white dark:bg-slate-800/80 text-slate-900 dark:text-white focus:outline-indigo-500"
                />
                <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                  Digital Object Identifier if published.
                </p>
              </div>

              {/* License */}
              <div>
                <label
                  htmlFor={licenseId}
                  className="block text-sm font-semibold text-slate-900 dark:text-slate-100 mb-1"
                >
                  License / Access Conditions
                </label>
                <input
                  id={licenseId}
                  type="text"
                  name="license"
                  value={formData.license}
                  onChange={handleChange}
                  placeholder="e.g. CC BY 4.0, MIT, Non-commercial, or Unknown"
                  className="w-full px-3.5 py-2.5 rounded-lg border border-slate-300 dark:border-slate-700 text-sm bg-white dark:bg-slate-800/80 text-slate-900 dark:text-white focus:outline-indigo-500"
                />
                <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                  Documented license terms. Write &ldquo;Unknown&rdquo; if not established.
                </p>
              </div>
            </div>

            {/* Supporting Paper URL */}
            <div>
              <label
                htmlFor={paperUrlId}
                className="block text-sm font-semibold text-slate-900 dark:text-slate-100 mb-1"
              >
                Supporting Research Paper URL
              </label>
              <input
                id={paperUrlId}
                type="url"
                name="paperUrl"
                value={formData.paperUrl}
                onChange={handleChange}
                placeholder="https://doi.org/... or https://arxiv.org/abs/..."
                aria-invalid={Boolean(errors.paperUrl)}
                aria-describedby={errors.paperUrl ? `${paperUrlId}-error` : undefined}
                className={`w-full px-3.5 py-2.5 rounded-lg border text-sm bg-white dark:bg-slate-800/80 text-slate-900 dark:text-white transition-colors focus:outline-indigo-500 ${
                  errors.paperUrl
                    ? 'border-rose-400 dark:border-rose-600 focus:border-rose-500'
                    : 'border-slate-300 dark:border-slate-700 focus:border-indigo-500'
                }`}
              />
              <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                Link to published journal article, conference paper, or preprint.
              </p>
              {errors.paperUrl && (
                <p id={`${paperUrlId}-error`} role="alert" className="mt-1 text-xs font-semibold text-rose-500">
                  {errors.paperUrl}
                </p>
              )}
            </div>

            {/* Additional Notes */}
            <div>
              <label
                htmlFor={notesId}
                className="block text-sm font-semibold text-slate-900 dark:text-slate-100 mb-1"
              >
                Additional Evidence, Sample Counts, or Limitations
              </label>
              <textarea
                id={notesId}
                name="notes"
                rows={3}
                value={formData.notes}
                onChange={handleChange}
                placeholder="e.g. 10,000 samples (8,000 train, 2,000 test), Bengali language only, non-diagnostic disclaimer..."
                className="w-full px-3.5 py-2.5 rounded-lg border border-slate-300 dark:border-slate-700 text-sm bg-white dark:bg-slate-800/80 text-slate-900 dark:text-white focus:outline-indigo-500"
              />
              <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                Any splits, size metrics, language codes, or research safeguards.
              </p>
            </div>
          </div>

          {/* Form Action Buttons */}
          <div className="flex flex-col sm:flex-row items-center gap-4 pt-2">
            <button
              type="submit"
              className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-6 py-3 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-sm shadow-sm transition-colors cursor-pointer focus:ring-2 focus:ring-indigo-500 focus:outline-hidden"
            >
              <GithubIcon className="w-4 h-4" />
              <span>Continue to GitHub</span>
            </button>

            <button
              type="button"
              onClick={handleCopyOnly}
              className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-5 py-3 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700 text-slate-800 dark:text-slate-200 font-semibold text-sm transition-colors cursor-pointer"
            >
              <Copy className="w-4 h-4 text-slate-500" />
              <span>Copy Submission Details</span>
            </button>

            <a
              href="https://github.com/VisionX25/OpenDatasets/blob/main/CONTRIBUTING.md"
              target="_blank"
              rel="noopener noreferrer"
              className="w-full sm:w-auto inline-flex items-center justify-center gap-1.5 px-4 py-3 rounded-lg text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 text-sm font-medium transition-colors"
            >
              <BookOpen className="w-4 h-4 text-slate-400" />
              <span>Contribution Guidelines</span>
            </a>
          </div>
        </form>

        {/* Formatted Submission Box & Next Steps */}
        {generatedMarkdown && (
          <div
            id="submission-handoff"
            role="region"
            aria-label="Submission handoff and GitHub link"
            className="mt-10 p-6 sm:p-8 rounded-2xl border-2 border-indigo-200 dark:border-indigo-800 bg-white dark:bg-slate-900 shadow-md space-y-6"
          >
            {/* Status notification */}
            <div className="flex items-start gap-3 p-4 rounded-xl bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800/80 text-emerald-900 dark:text-emerald-200">
              <CheckCircle2 className="w-5 h-5 text-emerald-600 dark:text-emerald-400 shrink-0 mt-0.5" />
              <div>
                <h3 className="font-bold text-sm sm:text-base text-emerald-900 dark:text-emerald-100">
                  {copied ? 'Details Copied & Ready for GitHub' : 'Submission Details Ready'}
                </h3>
                <p className="text-xs sm:text-sm text-emerald-800 dark:text-emerald-300 mt-0.5">
                  Your dataset details have been formatted and copied to your clipboard. Review the next steps below to complete submission on GitHub.
                </p>
              </div>
            </div>

            {/* Critical Action Notice: Do not claim submission before GitHub issue is created */}
            <div className="p-3.5 rounded-xl bg-amber-50/80 dark:bg-amber-950/40 border border-amber-300 dark:border-amber-700/80 text-amber-900 dark:text-amber-200 text-xs sm:text-sm flex items-start gap-2.5">
              <AlertTriangle className="w-4 h-4 text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" />
              <div>
                <span className="font-bold text-amber-950 dark:text-amber-100">
                  Action Required on GitHub:
                </span>{' '}
                <span>
                  OpenDatasets is a static site and cannot create GitHub issues automatically. To complete your proposal, review the prefilled fields in GitHub and click <strong>Submit new issue</strong>.
                </span>
              </div>
            </div>

            {/* Auto-Prefill status or Fallback notification */}
            {githubIssueResult.isFallback ? (
              <div
                role="alert"
                className="p-4 rounded-xl bg-amber-50 dark:bg-amber-950/40 border border-amber-300 dark:border-amber-700/80 text-amber-900 dark:text-amber-200 text-xs sm:text-sm space-y-1"
              >
                <div className="flex items-center gap-2 font-semibold text-amber-950 dark:text-amber-100">
                  <AlertTriangle className="w-4 h-4 text-amber-600 dark:text-amber-400 shrink-0" />
                  <span>Submission Exceeds Safe URL Limit ({githubIssueResult.urlLength} characters)</span>
                </div>
                <p className="text-amber-800 dark:text-amber-300">
                  To prevent browser or server URL truncation errors (HTTP 414), GitHub form fields cannot be prefilled via the URL. Your full formatted proposal has been copied to your clipboard. Click &ldquo;Open GitHub Issue Form&rdquo; below and paste your submission into the issue form.
                </p>
              </div>
            ) : (
              <div className="p-3.5 rounded-xl bg-indigo-50/70 dark:bg-indigo-950/40 border border-indigo-200 dark:border-indigo-800/80 text-xs text-indigo-900 dark:text-indigo-200 flex items-start gap-2.5">
                <CheckCircle2 className="w-4 h-4 text-indigo-600 dark:text-indigo-400 shrink-0 mt-0.5" />
                <div>
                  <p className="font-semibold text-slate-900 dark:text-white">
                    Auto-Prefill Configured
                  </p>
                  <p className="mt-0.5 text-slate-600 dark:text-slate-300">
                    Form fields are prefilled in GitHub&apos;s issue form. Review the prefilled values in the opened tab (or click &ldquo;Open GitHub Issue Form&rdquo; below) and click <strong>Submit new issue</strong> on GitHub.
                  </p>
                </div>
              </div>
            )}

            {/* Step-by-step handoff */}
            <div className="space-y-4">
              <h3 className="font-bold text-slate-900 dark:text-white text-base flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-indigo-500" />
                <span>Next Steps to Complete Submission</span>
              </h3>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs sm:text-sm">
                <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700">
                  <span className="inline-block w-6 h-6 rounded-full bg-indigo-600 text-white font-bold text-center leading-6 text-xs mb-2">
                    1
                  </span>
                  <h4 className="font-semibold text-slate-900 dark:text-white mb-1">
                    {githubIssueResult.isFallback ? 'Details Copied' : 'Details Copied & Prefilled'}
                  </h4>
                  <p className="text-slate-600 dark:text-slate-400 text-xs">
                    {githubIssueResult.isFallback
                      ? 'The formatted markdown is in your clipboard ready to paste into GitHub.'
                      : 'Fields are encoded in the URL to prefill GitHub, and copied to clipboard as a backup.'}
                  </p>
                </div>

                <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700">
                  <span className="inline-block w-6 h-6 rounded-full bg-indigo-600 text-white font-bold text-center leading-6 text-xs mb-2">
                    2
                  </span>
                  <h4 className="font-semibold text-slate-900 dark:text-white mb-1">Open GitHub Issue</h4>
                  <p className="text-slate-600 dark:text-slate-400 text-xs">
                    {githubIssueResult.isFallback
                      ? 'Click &ldquo;Open GitHub Issue Form&rdquo; to open the issue template.'
                      : 'Switch to the opened tab, or click &ldquo;Open GitHub Issue Form&rdquo; below.'}
                  </p>
                </div>

                <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700">
                  <span className="inline-block w-6 h-6 rounded-full bg-indigo-600 text-white font-bold text-center leading-6 text-xs mb-2">
                    3
                  </span>
                  <h4 className="font-semibold text-slate-900 dark:text-white mb-1">
                    {githubIssueResult.isFallback ? 'Paste & Submit' : 'Review & Submit'}
                  </h4>
                  <p className="text-slate-600 dark:text-slate-400 text-xs">
                    {githubIssueResult.isFallback
                      ? 'Paste details into the form and click &ldquo;Submit new issue&rdquo; on GitHub.'
                      : 'Review the prefilled fields, edit if needed, and click &ldquo;Submit new issue&rdquo;.'}
                  </p>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 pt-2">
                <a
                  href={githubIssueResult.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center justify-center gap-2 px-6 py-3 rounded-lg bg-slate-900 hover:bg-slate-800 dark:bg-white dark:hover:bg-slate-100 text-white dark:text-slate-900 font-bold text-sm shadow-sm transition-colors"
                >
                  <GithubIcon className="w-4 h-4" />
                  <span>
                    {githubIssueResult.isFallback
                      ? 'Open GitHub Issue (Manual Paste)'
                      : 'Open GitHub Issue Form'}
                  </span>
                  <ExternalLink className="w-3.5 h-3.5 opacity-70" />
                </a>

                <button
                  type="button"
                  onClick={handleCopyAgain}
                  className="inline-flex items-center justify-center gap-2 px-4 py-3 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700 text-slate-800 dark:text-slate-200 font-semibold text-sm transition-colors cursor-pointer"
                >
                  <Copy className="w-4 h-4 text-slate-500" />
                  <span>{copied ? 'Copied!' : 'Copy Formatted Text Again'}</span>
                </button>
              </div>

              {/* Submission Transparency Reminder */}
              <p className="text-xs text-slate-500 dark:text-slate-400 flex items-center gap-1.5">
                <Info className="w-3.5 h-3.5 shrink-0 text-indigo-500" />
                <span>
                  GitHub issues require explicit submission. Clicking &ldquo;Open GitHub Issue Form&rdquo; opens the issue form in your browser for your final review before submitting.
                </span>
              </p>

              {/* Formatted Markdown Preview */}
              <div className="space-y-2 pt-2">
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300">
                  Generated Submission Markdown:
                </label>
                <textarea
                  readOnly
                  rows={10}
                  value={generatedMarkdown}
                  className="w-full p-3.5 font-mono text-xs bg-slate-50 dark:bg-slate-950 text-slate-800 dark:text-slate-200 border border-slate-200 dark:border-slate-800 rounded-lg focus:outline-hidden selection:bg-indigo-500 selection:text-white"
                />
              </div>

              {/* Transparency Notice */}
              <div className="p-3.5 rounded-lg bg-slate-100/70 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700/80 text-xs text-slate-600 dark:text-slate-400 space-y-1">
                <p className="font-semibold text-slate-800 dark:text-slate-200 flex items-center gap-1.5">
                  <ShieldCheck className="w-4 h-4 text-emerald-500" />
                  <span>Transparency & Data Notice</span>
                </p>
                <p>
                  OpenDatasets is an open-source, fully static website hosted on GitHub Pages. No form data
                  is sent to third-party tracking services or private servers. Your proposal is submitted
                  directly to the public GitHub repository where maintainers review it. Creating an
                  issue requires signing in with a free GitHub account.
                </p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
