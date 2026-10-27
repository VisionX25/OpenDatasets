import type {
  CategoryId,
  CategoryDefinition,
  DatasetMetadata,
  DatasetModality,
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

export interface DatasetFilterCriteria {
  searchQuery?: string
  category?: CategoryId | null
  modality?: string | null
  task?: string | null
}

/**
 * Filter a list of datasets applying search, category, modality, and task constraints together.
 */
export function filterDatasets(
  datasets: DatasetMetadata[],
  criteria: DatasetFilterCriteria,
): DatasetMetadata[] {
  const { searchQuery = '', category = null, modality = null, task = null } = criteria

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
