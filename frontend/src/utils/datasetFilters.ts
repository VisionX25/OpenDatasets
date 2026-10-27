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

export interface DatasetFilterCriteria {
  searchQuery?: string
  category?: CategoryId | null
  modality?: string | null
  task?: string | null
  license?: LicenseStatus | string | null
}

/**
 * Filter a list of datasets applying search, category, modality, task, and license constraints together.
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

export interface FilterState {
  searchQuery: string
  category: CategoryId | null
  modality: string
  task: string
  license: LicenseStatus | ''
}

export const DEFAULT_FILTER_STATE: FilterState = {
  searchQuery: '',
  category: null,
  modality: '',
  task: '',
  license: '',
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

  return {
    searchQuery,
    category,
    modality,
    task,
    license,
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

  return params
}
