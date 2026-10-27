import { describe, it, expect } from 'vitest'
import type { DatasetMetadata } from '../types/dataset'
import {
  matchesSearch,
  matchesCategory,
  matchesModality,
  matchesTask,
  filterDatasets,
  countDatasetsPerCategory,
  getAvailableModalities,
  getAvailableTasks,
} from './datasetFilters'

const mockCifar: DatasetMetadata = {
  schema_version: '1.0.0',
  id: 'cifar-10',
  slug: 'cifar-10',
  name: 'CIFAR-10',
  description: 'The CIFAR-10 dataset consists of 60,000 32x32 colour images in 10 classes.',
  homepage_url: 'https://www.cs.toronto.edu/~kriz/cifar.html',
  publisher: {
    name: 'University of Toronto',
    type: 'academic',
  },
  modalities: ['vision'],
  tasks: ['image-classification'],
  tags: ['computer-vision', 'benchmark', 'tiny-images'],
  license: {
    status: 'unspecified_by_source',
    name: 'Unspecified',
  },
  source_references: [
    {
      title: 'Official Homepage',
      url: 'https://www.cs.toronto.edu/~kriz/cifar.html',
      type: 'official_website',
    },
  ],
  verification: {
    status: 'verified',
  },
}

const mockIris: DatasetMetadata = {
  schema_version: '1.0.0',
  id: 'iris',
  slug: 'iris',
  name: 'Iris Plants Database',
  description: 'Contains 150 instances across 4 measurements for three iris plant species.',
  homepage_url: 'https://archive.ics.uci.edu/dataset/53/iris',
  publisher: {
    name: 'UCI Machine Learning Repository',
    type: 'academic',
  },
  modalities: ['tabular'],
  tasks: ['tabular-classification'],
  tags: ['tabular', 'biology', 'benchmark'],
  license: {
    status: 'verified_open',
    name: 'CC-BY-4.0',
  },
  source_references: [
    {
      title: 'UCI ML Repository: Iris',
      url: 'https://archive.ics.uci.edu/dataset/53/iris',
      type: 'official_website',
    },
  ],
  verification: {
    status: 'verified',
  },
}

const mockNlpDataset: DatasetMetadata = {
  schema_version: '1.0.0',
  id: 'sst2',
  slug: 'sst2',
  name: 'Stanford Sentiment Treebank',
  description: 'Corpus with fully labeled parse trees for sentiment analysis.',
  homepage_url: 'https://nlp.stanford.edu/sentiment/',
  publisher: {
    name: 'Stanford NLP Group',
    type: 'academic',
  },
  modalities: ['nlp'],
  tasks: ['text-classification'],
  tags: ['sentiment', 'linguistics'],
  license: {
    status: 'verified_open',
    name: 'Custom',
  },
  source_references: [
    {
      title: 'Stanford Sentiment Homepage',
      url: 'https://nlp.stanford.edu/sentiment/',
      type: 'official_website',
    },
  ],
  verification: {
    status: 'verified',
  },
}

const testCatalog: DatasetMetadata[] = [mockCifar, mockIris, mockNlpDataset]

describe('Dataset Search and Filtering Logic', () => {
  // 1. Search by name
  it('searches datasets by name', () => {
    expect(matchesSearch(mockCifar, 'CIFAR')).toBe(true)
    expect(matchesSearch(mockIris, 'Iris')).toBe(true)
    expect(matchesSearch(mockIris, 'CIFAR')).toBe(false)
  })

  // 2. Search by publisher, task, and tags
  it('searches datasets by publisher name', () => {
    expect(matchesSearch(mockCifar, 'University of Toronto')).toBe(true)
    expect(matchesSearch(mockIris, 'UCI')).toBe(true)
    expect(matchesSearch(mockNlpDataset, 'Stanford')).toBe(true)
  })

  it('searches datasets by ML tasks', () => {
    expect(matchesSearch(mockCifar, 'image-classification')).toBe(true)
    expect(matchesSearch(mockIris, 'tabular-classification')).toBe(true)
    expect(matchesSearch(mockNlpDataset, 'text-classification')).toBe(true)
    expect(matchesSearch(mockCifar, 'tabular-classification')).toBe(false)
  })

  it('searches datasets by tags', () => {
    expect(matchesSearch(mockCifar, 'tiny-images')).toBe(true)
    expect(matchesSearch(mockIris, 'biology')).toBe(true)
    expect(matchesSearch(mockNlpDataset, 'sentiment')).toBe(true)
  })

  // 3. Case-insensitive search
  it('performs case-insensitive search with leading/trailing whitespace', () => {
    expect(matchesSearch(mockCifar, '  cifar-10  ')).toBe(true)
    expect(matchesSearch(mockCifar, 'CiFaR')).toBe(true)
    expect(matchesSearch(mockIris, 'PLANTS')).toBe(true)
  })

  // 4. Category-based filtering
  it('filters by category correctly', () => {
    expect(matchesCategory(mockCifar, 'computer-vision')).toBe(true)
    expect(matchesCategory(mockIris, 'computer-vision')).toBe(false)

    expect(matchesCategory(mockIris, 'tabular-time-series')).toBe(true)
    expect(matchesCategory(mockCifar, 'tabular-time-series')).toBe(false)

    expect(matchesCategory(mockNlpDataset, 'natural-language-processing')).toBe(true)
    expect(matchesCategory(mockCifar, 'natural-language-processing')).toBe(false)
  })

  // 5. Multi-category matching
  it('supports multi-category matching (e.g. computer vision AND benchmark)', () => {
    // CIFAR-10 has modality 'vision' and tag 'benchmark'
    expect(matchesCategory(mockCifar, 'computer-vision')).toBe(true)
    expect(matchesCategory(mockCifar, 'evaluation-benchmarks')).toBe(true)

    // Iris has modality 'tabular' and tag 'benchmark'
    expect(matchesCategory(mockIris, 'tabular-time-series')).toBe(true)
    expect(matchesCategory(mockIris, 'evaluation-benchmarks')).toBe(true)

    // mockNlpDataset has no benchmark tag or task
    expect(matchesCategory(mockNlpDataset, 'evaluation-benchmarks')).toBe(false)
  })

  // 6. Combined search and filters
  it('combines category, modality, task, and search query together', () => {
    // Matches CIFAR-10
    const result1 = filterDatasets(testCatalog, {
      category: 'computer-vision',
      modality: 'vision',
      task: 'image-classification',
      searchQuery: 'Toronto',
    })
    expect(result1.length).toBe(1)
    expect(result1[0].id).toBe('cifar-10')

    // Conflicting criteria: category computer-vision with modality tabular -> 0 results
    const result2 = filterDatasets(testCatalog, {
      category: 'computer-vision',
      modality: 'tabular',
    })
    expect(result2.length).toBe(0)
  })

  // 7. Reset filters / empty criteria returns all
  it('returns all datasets when all filters are empty or null', () => {
    const result = filterDatasets(testCatalog, {
      category: null,
      modality: null,
      task: null,
      searchQuery: '',
    })
    expect(result.length).toBe(3)
  })

  // 8. Empty result handling
  it('returns empty array when search query matches nothing', () => {
    const result = filterDatasets(testCatalog, {
      searchQuery: 'nonexistent-query-string-xyz',
    })
    expect(result.length).toBe(0)
  })

  // 9. Modality and Task filter helpers
  it('filters by modality and task individually', () => {
    expect(matchesModality(mockCifar, 'vision')).toBe(true)
    expect(matchesModality(mockCifar, 'nlp')).toBe(false)
    expect(matchesModality(mockCifar, null)).toBe(true)

    expect(matchesTask(mockCifar, 'image-classification')).toBe(true)
    expect(matchesTask(mockCifar, 'speech-recognition')).toBe(false)
    expect(matchesTask(mockCifar, null)).toBe(true)
  })

  // 10. Category counts
  it('calculates counts per category accurately', () => {
    const counts = countDatasetsPerCategory(testCatalog)
    expect(counts['computer-vision']).toBe(1)
    expect(counts['tabular-time-series']).toBe(1)
    expect(counts['natural-language-processing']).toBe(1)
    expect(counts['evaluation-benchmarks']).toBe(2) // CIFAR-10 and Iris both have benchmark tag
    expect(counts['audio-speech']).toBe(0)
    expect(counts['multimodal-generative']).toBe(0)
  })

  // 11. Extract unique modalities and tasks
  it('extracts unique modalities and tasks from catalog', () => {
    const modalities = getAvailableModalities(testCatalog)
    expect(modalities).toEqual(['nlp', 'tabular', 'vision'])

    const tasks = getAvailableTasks(testCatalog)
    expect(tasks).toEqual(['image-classification', 'tabular-classification', 'text-classification'])
  })
})
