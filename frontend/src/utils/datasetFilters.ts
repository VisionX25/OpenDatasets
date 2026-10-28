import type {
  CategoryId,
  CategoryDefinition,
  DatasetMetadata,
  DatasetModality,
  LicenseStatus,
} from '../types/dataset'

export const CATEGORIES: CategoryDefinition[] = [
  {
    id: 'computer-vision',
    name: 'Computer Vision',
    description: 'Image classification, object detection, segmentation, and video streams.',
  },
  {
    id: 'natural-language-processing',
    name: 'Natural Language Processing',
    description: 'Instruction tuning, question answering, summarization, and multilingual corpora.',
  },
  {
    id: 'audio-speech',
    name: 'Audio & Speech',
    description: 'Speech recognition, acoustic classification, and musical synthesis.',
  },
  {
    id: 'tabular-time-series',
    name: 'Tabular & Time-Series',
    description: 'Structured financial records, sensor logs, telemetry, and forecasting sets.',
  },
  {
    id: 'multimodal-generative',
    name: 'Multimodal & Generative',
    description: 'Vision-language paired data, diffusion prompts, and multi-sensor datasets.',
  },
  {
    id: 'evaluation-benchmarks',
    name: 'Evaluation & Benchmarks',
    description: 'Standardized evaluation datasets, human preference benchmarks, and safety audits.',
  },
]

export interface CategoryAccent {
  id: CategoryId
  name: string
  colorName: string
  hex: string
  selectedCardBg: string
  selectedCardBorder: string
  selectedIconBg: string
  selectedCheckBg: string
  selectedBadge: string
  focusRing: string
  hoverCardBorder: string
  hoverCardBg: string
  hoverIconBg: string
}

/**
 * Centralized mapping of category-specific accent colors and styling tokens.
 * Consistent across light and dark themes.
 */
export const CATEGORY_ACCENTS: Record<CategoryId, CategoryAccent> = {
  'computer-vision': {
    id: 'computer-vision',
    name: 'Computer Vision',
    colorName: 'Blue',
    hex: '#3B82F6',
    selectedCardBg: 'bg-blue-50/70 dark:bg-blue-950/40',
    selectedCardBorder: 'border-blue-500 dark:border-blue-400',
    selectedIconBg: 'bg-blue-600 text-white dark:bg-blue-500',
    selectedCheckBg: 'bg-blue-600 text-white dark:bg-blue-500',
    selectedBadge: 'bg-blue-100 text-blue-800 dark:bg-blue-900/60 dark:text-blue-300',
    focusRing: 'focus-visible:ring-blue-500',
    hoverCardBorder:
      'hover:border-blue-400 dark:hover:border-blue-500 focus-visible:border-blue-400 dark:focus-visible:border-blue-500',
    hoverCardBg: 'hover:bg-blue-50/50 dark:hover:bg-blue-950/20',
    hoverIconBg:
      'group-hover:bg-blue-100 group-hover:text-blue-700 dark:group-hover:bg-blue-900/50 dark:group-hover:text-blue-300 group-focus-visible:bg-blue-100 group-focus-visible:text-blue-700 dark:group-focus-visible:bg-blue-900/50 dark:group-focus-visible:text-blue-300',
  },
  'natural-language-processing': {
    id: 'natural-language-processing',
    name: 'Natural Language Processing',
    colorName: 'Purple',
    hex: '#A78BFA',
    selectedCardBg: 'bg-violet-50/70 dark:bg-violet-950/40',
    selectedCardBorder: 'border-violet-500 dark:border-violet-400',
    selectedIconBg: 'bg-violet-600 text-white dark:bg-violet-500',
    selectedCheckBg: 'bg-violet-600 text-white dark:bg-violet-500',
    selectedBadge: 'bg-violet-100 text-violet-800 dark:bg-violet-900/60 dark:text-violet-300',
    focusRing: 'focus-visible:ring-violet-500',
    hoverCardBorder:
      'hover:border-violet-400 dark:hover:border-violet-500 focus-visible:border-violet-400 dark:focus-visible:border-violet-500',
    hoverCardBg: 'hover:bg-violet-50/50 dark:hover:bg-violet-950/20',
    hoverIconBg:
      'group-hover:bg-violet-100 group-hover:text-violet-700 dark:group-hover:bg-violet-900/50 dark:group-hover:text-violet-300 group-focus-visible:bg-violet-100 group-focus-visible:text-violet-700 dark:group-focus-visible:bg-violet-900/50 dark:group-focus-visible:text-violet-300',
  },
  'audio-speech': {
    id: 'audio-speech',
    name: 'Audio & Speech',
    colorName: 'Amber',
    hex: '#F59E0B',
    selectedCardBg: 'bg-amber-50/70 dark:bg-amber-950/40',
    selectedCardBorder: 'border-amber-500 dark:border-amber-400',
    selectedIconBg: 'bg-amber-600 text-white dark:bg-amber-500',
    selectedCheckBg: 'bg-amber-600 text-white dark:bg-amber-500',
    selectedBadge: 'bg-amber-100 text-amber-800 dark:bg-amber-900/60 dark:text-amber-300',
    focusRing: 'focus-visible:ring-amber-500',
    hoverCardBorder:
      'hover:border-amber-400 dark:hover:border-amber-500 focus-visible:border-amber-400 dark:focus-visible:border-amber-500',
    hoverCardBg: 'hover:bg-amber-50/50 dark:hover:bg-amber-950/20',
    hoverIconBg:
      'group-hover:bg-amber-100 group-hover:text-amber-700 dark:group-hover:bg-amber-900/50 dark:group-hover:text-amber-300 group-focus-visible:bg-amber-100 group-focus-visible:text-amber-700 dark:group-focus-visible:bg-amber-900/50 dark:group-focus-visible:text-amber-300',
  },
  'tabular-time-series': {
    id: 'tabular-time-series',
    name: 'Tabular & Time-Series',
    colorName: 'Emerald',
    hex: '#10B981',
    selectedCardBg: 'bg-emerald-50/70 dark:bg-emerald-950/40',
    selectedCardBorder: 'border-emerald-500 dark:border-emerald-400',
    selectedIconBg: 'bg-emerald-600 text-white dark:bg-emerald-500',
    selectedCheckBg: 'bg-emerald-600 text-white dark:bg-emerald-500',
    selectedBadge: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/60 dark:text-emerald-300',
    focusRing: 'focus-visible:ring-emerald-500',
    hoverCardBorder:
      'hover:border-emerald-400 dark:hover:border-emerald-500 focus-visible:border-emerald-400 dark:focus-visible:border-emerald-500',
    hoverCardBg: 'hover:bg-emerald-50/50 dark:hover:bg-emerald-950/20',
    hoverIconBg:
      'group-hover:bg-emerald-100 group-hover:text-emerald-700 dark:group-hover:bg-emerald-900/50 dark:group-hover:text-emerald-300 group-focus-visible:bg-emerald-100 group-focus-visible:text-emerald-700 dark:group-focus-visible:bg-emerald-900/50 dark:group-focus-visible:text-emerald-300',
  },
  'multimodal-generative': {
    id: 'multimodal-generative',
    name: 'Multimodal & Generative',
    colorName: 'Pink',
    hex: '#EC4899',
    selectedCardBg: 'bg-pink-50/70 dark:bg-pink-950/40',
    selectedCardBorder: 'border-pink-500 dark:border-pink-400',
    selectedIconBg: 'bg-pink-600 text-white dark:bg-pink-500',
    selectedCheckBg: 'bg-pink-600 text-white dark:bg-pink-500',
    selectedBadge: 'bg-pink-100 text-pink-800 dark:bg-pink-900/60 dark:text-pink-300',
    focusRing: 'focus-visible:ring-pink-500',
    hoverCardBorder:
      'hover:border-pink-400 dark:hover:border-pink-500 focus-visible:border-pink-400 dark:focus-visible:border-pink-500',
    hoverCardBg: 'hover:bg-pink-50/50 dark:hover:bg-pink-950/20',
    hoverIconBg:
      'group-hover:bg-pink-100 group-hover:text-pink-700 dark:group-hover:bg-pink-900/50 dark:group-hover:text-pink-300 group-focus-visible:bg-pink-100 group-focus-visible:text-pink-700 dark:group-focus-visible:bg-pink-900/50 dark:group-focus-visible:text-pink-300',
  },
  'evaluation-benchmarks': {
    id: 'evaluation-benchmarks',
    name: 'Evaluation & Benchmarks',
    colorName: 'Cyan',
    hex: '#06B6D4',
    selectedCardBg: 'bg-cyan-50/70 dark:bg-cyan-950/40',
    selectedCardBorder: 'border-cyan-500 dark:border-cyan-400',
    selectedIconBg: 'bg-cyan-600 text-white dark:bg-cyan-500',
    selectedCheckBg: 'bg-cyan-600 text-white dark:bg-cyan-500',
    selectedBadge: 'bg-cyan-100 text-cyan-800 dark:bg-cyan-900/60 dark:text-cyan-300',
    focusRing: 'focus-visible:ring-cyan-500',
    hoverCardBorder:
      'hover:border-cyan-400 dark:hover:border-cyan-500 focus-visible:border-cyan-400 dark:focus-visible:border-cyan-500',
    hoverCardBg: 'hover:bg-cyan-50/50 dark:hover:bg-cyan-950/20',
    hoverIconBg:
      'group-hover:bg-cyan-100 group-hover:text-cyan-700 dark:group-hover:bg-cyan-900/50 dark:group-hover:text-cyan-300 group-focus-visible:bg-cyan-100 group-focus-visible:text-cyan-700 dark:group-focus-visible:bg-cyan-900/50 dark:group-focus-visible:text-cyan-300',
  },
}

export function getCategoryAccent(categoryId: CategoryId): CategoryAccent {
  return CATEGORY_ACCENTS[categoryId]
}

export function isCategoryId(slug: string | null | undefined): slug is CategoryId {
  if (!slug) return false
  return CATEGORIES.some((c) => c.id === slug)
}

export function getCategoryById(
  id: CategoryId | string | null | undefined,
): CategoryDefinition | undefined {
  if (!id) return undefined
  return CATEGORIES.find((c) => c.id === id)
}

const BENCHMARK_TAGS = new Set([
  'benchmark',
  'evaluation',
  'eval',
  'benchmark-dataset',
  'gold-standard',
  'leaderboard',
])

export const VALID_LICENSE_STATUSES: readonly LicenseStatus[] = [
  'verified_open',
  'public_domain',
  'verified_non_commercial',
  'custom_permissive',
  'unspecified_by_source',
  'proprietary',
  'unknown',
] as const

export const LICENSE_LABELS: Record<LicenseStatus, string> = {
  verified_open: 'Verified Open',
  public_domain: 'Public Domain',
  verified_non_commercial: 'Non-Commercial',
  custom_permissive: 'Custom Permissive',
  unspecified_by_source: 'Unspecified by Source',
  proprietary: 'Proprietary',
  unknown: 'Unknown License',
}

export function formatLicenseLabel(status: LicenseStatus | string): string {
  if (status in LICENSE_LABELS) {
    return LICENSE_LABELS[status as LicenseStatus]
  }
  return status
    .split('_')
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ')
}

/**
 * Determine if a dataset belongs to a specific discovery category.
 * A dataset may belong to multiple categories simultaneously.
 */
export function matchesCategory(
  dataset: DatasetMetadata,
  category: CategoryId | null,
): boolean {
  if (!category) {
    return true
  }

  const modalities = Array.isArray(dataset.modalities) ? dataset.modalities : []
  const tags = Array.isArray(dataset.tags) ? dataset.tags : []
  const tasks = Array.isArray(dataset.tasks) ? dataset.tasks : []

  switch (category) {
    case 'computer-vision':
      return modalities.includes('vision')

    case 'natural-language-processing':
      return modalities.includes('nlp')

    case 'audio-speech':
      return modalities.includes('audio')

    case 'tabular-time-series':
      return (
        modalities.includes('tabular') ||
        modalities.includes('time-series')
      )

    case 'multimodal-generative':
      return modalities.includes('multimodal')

    case 'evaluation-benchmarks': {
      // Documented purpose-based criteria using tags and tasks
      const hasBenchmarkTag = tags.some((tag) =>
        typeof tag === 'string' && BENCHMARK_TAGS.has(tag.toLowerCase()),
      )
      const hasBenchmarkTask = tasks.some((task) => {
        if (typeof task !== 'string') return false
        const lower = task.toLowerCase()
        return (
          lower === 'benchmark' ||
          lower === 'evaluation' ||
          lower.endsWith('-benchmark') ||
          lower.endsWith('-evaluation')
        )
      })
      return hasBenchmarkTag || hasBenchmarkTask
    }

    default:
      return false
  }
}

/**
 * Case-insensitive search across name, description, publisher, tasks, and tags.
 */
export function matchesSearch(dataset: DatasetMetadata, query: string): boolean {
  const cleanQuery = query.trim().toLowerCase()
  if (!cleanQuery) {
    return true
  }

  const name = typeof dataset.name === 'string' ? dataset.name : ''
  if (name.toLowerCase().includes(cleanQuery)) {
    return true
  }

  const description = typeof dataset.description === 'string' ? dataset.description : ''
  if (description.toLowerCase().includes(cleanQuery)) {
    return true
  }

  const publisherName =
    dataset.publisher && typeof dataset.publisher.name === 'string'
      ? dataset.publisher.name
      : ''
  if (publisherName.toLowerCase().includes(cleanQuery)) {
    return true
  }

  const tasks = Array.isArray(dataset.tasks) ? dataset.tasks : []
  if (tasks.some((task) => typeof task === 'string' && task.toLowerCase().includes(cleanQuery))) {
    return true
  }

  const tags = Array.isArray(dataset.tags) ? dataset.tags : []
  if (tags.some((tag) => typeof tag === 'string' && tag.toLowerCase().includes(cleanQuery))) {
    return true
  }

  return false
}

export function matchesModality(
  dataset: DatasetMetadata,
  modality: DatasetModality | string | null,
): boolean {
  if (!modality) {
    return true
  }
  const modalities = Array.isArray(dataset.modalities) ? dataset.modalities : []
  return modalities.includes(modality as DatasetModality)
}

export function matchesTask(dataset: DatasetMetadata, task: string | null): boolean {
  if (!task) {
    return true
  }
  const tasks = Array.isArray(dataset.tasks) ? dataset.tasks : []
  return tasks.includes(task)
}

/**
 * Determine if a dataset matches a selected license status filter.
 * Accurately differentiates between open, non-commercial, public domain,
 * custom permissive, proprietary, and unspecified/unknown statuses.
 */
export function matchesLicense(
  dataset: DatasetMetadata,
  licenseStatus: LicenseStatus | string | null,
): boolean {
  if (!licenseStatus) {
    return true
  }
  const status = dataset.license?.status
  if (!status) {
    return licenseStatus === 'unknown' || licenseStatus === 'unspecified_by_source'
  }
  return status === licenseStatus
}

/**
 * Determine if a dataset matches a selected publication year filter.
 * Uses the verified dates.published field. If no year filter is provided,
 * returns true (records with missing years remain visible when no year filter is active).
 * When a year filter is active, only records with verified matching publication year are included.
 */
export function matchesYear(dataset: DatasetMetadata, year: string | null): boolean {
  if (!year) {
    return true
  }
  const published = dataset.dates?.published
  if (!published || typeof published !== 'string') {
    return false
  }
  return published.startsWith(year)
}

export interface DatasetFilterCriteria {
  searchQuery?: string
  category?: CategoryId | null
  modality?: string | null
  task?: string | null
  license?: LicenseStatus | string | null
  year?: string | null
}

/**
 * Filter a list of datasets applying search, category, modality, task, license, and year constraints together.
 */
export function filterDatasets(
  datasets: DatasetMetadata[],
  criteria: DatasetFilterCriteria,
): DatasetMetadata[] {
  const {
    searchQuery = '',
    category = null,
    modality = null,
    task = null,
    license = null,
    year = null,
  } = criteria

  return datasets.filter((dataset) => {
    if (!matchesSearch(dataset, searchQuery)) {
      return false
    }
    if (!matchesCategory(dataset, category)) {
      return false
    }
    if (!matchesModality(dataset, modality)) {
      return false
    }
    if (!matchesTask(dataset, task)) {
      return false
    }
    if (!matchesLicense(dataset, license)) {
      return false
    }
    if (!matchesYear(dataset, year)) {
      return false
    }
    return true
  })
}

/**
 * Calculate the count of datasets belonging to each category.
 */
export function countDatasetsPerCategory(
  datasets: DatasetMetadata[],
): Record<CategoryId, number> {
  const counts: Record<CategoryId, number> = {
    'computer-vision': 0,
    'natural-language-processing': 0,
    'audio-speech': 0,
    'tabular-time-series': 0,
    'multimodal-generative': 0,
    'evaluation-benchmarks': 0,
  }

  for (const ds of datasets) {
    for (const cat of CATEGORIES) {
      if (matchesCategory(ds, cat.id)) {
        counts[cat.id] += 1
      }
    }
  }

  return counts
}

export function getAvailableModalities(datasets: DatasetMetadata[]): string[] {
  const set = new Set<string>()
  for (const ds of datasets) {
    if (Array.isArray(ds.modalities)) {
      for (const m of ds.modalities) {
        if (m) set.add(m)
      }
    }
  }
  return Array.from(set).sort()
}

export function getAvailableTasks(datasets: DatasetMetadata[]): string[] {
  const set = new Set<string>()
  for (const ds of datasets) {
    if (Array.isArray(ds.tasks)) {
      for (const t of ds.tasks) {
        if (t) set.add(t)
      }
    }
  }
  return Array.from(set).sort()
}

/**
 * Derive available license statuses directly from the catalog metadata.
 */
export function getAvailableLicenseStatuses(datasets: DatasetMetadata[]): LicenseStatus[] {
  const set = new Set<LicenseStatus>()
  for (const ds of datasets) {
    if (ds.license?.status) {
      set.add(ds.license.status)
    } else {
      set.add('unknown')
    }
  }

  const preferredOrder: LicenseStatus[] = [
    'verified_open',
    'public_domain',
    'verified_non_commercial',
    'custom_permissive',
    'unspecified_by_source',
    'proprietary',
    'unknown',
  ]

  const result: LicenseStatus[] = []
  for (const status of preferredOrder) {
    if (set.has(status)) {
      result.push(status)
      set.delete(status)
    }
  }
  const remaining = Array.from(set).sort()
  return [...result, ...remaining]
}

/**
 * Extract available publication years from catalog datasets.
 * Returns unique 4-digit years sorted in descending chronological order.
 */
export function getAvailablePublicationYears(datasets: DatasetMetadata[]): string[] {
  const yearSet = new Set<string>()
  for (const ds of datasets) {
    const published = ds.dates?.published
    if (published && typeof published === 'string' && /^[0-9]{4}/.test(published)) {
      yearSet.add(published.slice(0, 4))
    }
  }
  return Array.from(yearSet).sort((a, b) => b.localeCompare(a))
}

export interface FilterState {
  searchQuery: string
  category: CategoryId | null
  modality: string
  task: string
  license: LicenseStatus | ''
  year: string
}

export const DEFAULT_FILTER_STATE: FilterState = {
  searchQuery: '',
  category: null,
  modality: '',
  task: '',
  license: '',
  year: '',
}

/**
 * Determine whether any valid discovery criteria are currently active.
 * Used by Explore and Results pages to conditionally display dataset results.
 */
export function hasActiveFilterCriteria(filters: FilterState): boolean {
  return Boolean(
    filters.searchQuery.trim().length > 0 ||
      Boolean(filters.category) ||
      Boolean(filters.modality) ||
      Boolean(filters.task) ||
      Boolean(filters.license) ||
      Boolean(filters.year),
  )
}

/**
 * Safely parse and sanitize URL search parameters into a valid FilterState.
 * Invalid or unknown parameter values are ignored or sanitized to their defaults.
 */
export function parseFilterParams(
  searchParams: URLSearchParams | string,
): FilterState {
  const params =
    typeof searchParams === 'string'
      ? new URLSearchParams(searchParams)
      : searchParams

  // 1. Search Query
  const rawQ = params.get('q')
  const searchQuery = rawQ && rawQ.trim().length > 0 ? rawQ : ''

  // 2. Category
  const rawCategory = params.get('category')?.trim().toLowerCase()
  const category =
    rawCategory && CATEGORIES.some((c) => c.id === rawCategory)
      ? (rawCategory as CategoryId)
      : null

  // 3. Modality (lowercase alphanumeric and hyphens)
  const rawModality = params.get('modality')?.trim().toLowerCase()
  const modality =
    rawModality && /^[a-z0-9-]+$/.test(rawModality) ? rawModality : ''

  // 4. Task (lowercase alphanumeric and hyphens)
  const rawTask = params.get('task')?.trim().toLowerCase()
  const task =
    rawTask && /^[a-z0-9-]+$/.test(rawTask) ? rawTask : ''

  // 5. License (must be a recognized LicenseStatus)
  const rawLicense = params.get('license')?.trim().toLowerCase()
  const license =
    rawLicense && (VALID_LICENSE_STATUSES as readonly string[]).includes(rawLicense)
      ? (rawLicense as LicenseStatus)
      : ''

  // 6. Published Year (4-digit string)
  const rawYear = params.get('year')?.trim()
  const year = rawYear && /^[0-9]{4}$/.test(rawYear) ? rawYear : ''

  return {
    searchQuery,
    category,
    modality,
    task,
    license,
    year,
  }
}

/**
 * Serialize FilterState into URLSearchParams, preserving unrelated query parameters
 * and removing empty/default parameters.
 */
export function serializeFilterParams(
  filters: Partial<FilterState>,
  existingParams?: URLSearchParams | string,
): URLSearchParams {
  const params = new URLSearchParams(
    typeof existingParams === 'string'
      ? existingParams
      : existingParams?.toString() || '',
  )

  // 1. Search Query
  if (filters.searchQuery !== undefined) {
    if (filters.searchQuery.trim().length > 0) {
      params.set('q', filters.searchQuery)
    } else {
      params.delete('q')
    }
  }

  // 2. Category
  if (filters.category !== undefined) {
    if (filters.category && CATEGORIES.some((c) => c.id === filters.category)) {
      params.set('category', filters.category)
    } else {
      params.delete('category')
    }
  }

  // 3. Modality
  if (filters.modality !== undefined) {
    if (filters.modality && filters.modality.trim().length > 0) {
      params.set('modality', filters.modality.trim().toLowerCase())
    } else {
      params.delete('modality')
    }
  }

  // 4. Task
  if (filters.task !== undefined) {
    if (filters.task && filters.task.trim().length > 0) {
      params.set('task', filters.task.trim().toLowerCase())
    } else {
      params.delete('task')
    }
  }

  // 5. License
  if (filters.license !== undefined) {
    if (
      filters.license &&
      (VALID_LICENSE_STATUSES as readonly string[]).includes(filters.license)
    ) {
      params.set('license', filters.license)
    } else {
      params.delete('license')
    }
  }

  // 6. Year
  if (filters.year !== undefined) {
    if (filters.year && /^[0-9]{4}$/.test(filters.year.trim())) {
      params.set('year', filters.year.trim())
    } else {
      params.delete('year')
    }
  }

  return params
}
