import { describe, it, expect } from 'vitest'
import type { DatasetMetadata } from '../types/dataset'
import {
  matchesSearch,
  matchesCategory,
  matchesModality,
  matchesTask,
  matchesLicense,
  filterDatasets,
  countDatasetsPerCategory,
  getAvailableModalities,
  getAvailableTasks,
  getAvailableLicenseStatuses,
  formatLicenseLabel,
  parseFilterParams,
  serializeFilterParams,
  DEFAULT_FILTER_STATE,
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

const mockImageNet: DatasetMetadata = {
  schema_version: '1.0.0',
  id: 'imagenet-1k',
  slug: 'imagenet-1k',
  name: 'ImageNet (ILSVRC 2012)',
  description: '1000 class image recognition challenge dataset.',
  homepage_url: 'https://www.image-net.org/',
  publisher: {
    name: 'Stanford Vision Lab',
    type: 'academic',
  },
  modalities: ['vision'],
  tasks: ['image-classification'],
  tags: ['computer-vision', 'benchmark', 'object-recognition'],
  license: {
    status: 'verified_non_commercial',
    name: 'ImageNet Terms of Access',
    commercial_use: 'forbidden',
  },
  source_references: [
    {
      title: 'ImageNet Portal',
      url: 'https://www.image-net.org/',
      type: 'official_website',
    },
  ],
  verification: {
    status: 'verified',
  },
}

const mockCommonVoice: DatasetMetadata = {
  schema_version: '1.0.0',
  id: 'common-voice',
  slug: 'common-voice',
  name: 'Mozilla Common Voice',
  description: 'Multilingual speech corpus of crowdsourced voice recordings.',
  homepage_url: 'https://commonvoice.mozilla.org/',
  publisher: {
    name: 'Mozilla Foundation',
    type: 'community',
  },
  modalities: ['audio'],
  tasks: ['speech-recognition'],
  tags: ['audio', 'speech-recognition', 'asr'],
  license: {
    status: 'public_domain',
    name: 'CC0-1.0',
    commercial_use: 'allowed',
  },
  source_references: [
    {
      title: 'Common Voice',
      url: 'https://commonvoice.mozilla.org/',
      type: 'official_website',
    },
  ],
  verification: {
    status: 'verified',
  },
}

const mockProprietary: DatasetMetadata = {
  schema_version: '1.0.0',
  id: 'proprietary-market',
  slug: 'proprietary-market',
  name: 'Proprietary Market Telemetry',
  description: 'Proprietary financial dataset with commercial license restrictions.',
  homepage_url: 'https://example.com/market-data',
  publisher: {
    name: 'FinTech Corp',
    type: 'industry',
  },
  modalities: ['tabular', 'time-series'],
  tasks: ['tabular-classification'],
  tags: ['finance', 'telemetry'],
  license: {
    status: 'proprietary',
    name: 'Commercial Proprietary License',
    commercial_use: 'forbidden',
  },
  source_references: [
    {
      title: 'Data Portal',
      url: 'https://example.com/market-data',
      type: 'official_website',
    },
  ],
  verification: {
    status: 'provisional',
  },
}

const mockUnknownLic: DatasetMetadata = {
  schema_version: '1.0.0',
  id: 'experimental-nlp',
  slug: 'experimental-nlp',
  name: 'Experimental NLP Scrapes',
  description: 'Uncategorized text scrapes without clear licensing declaration.',
  homepage_url: 'https://example.com/scrapes',
  publisher: {
    name: 'Independent Research',
    type: 'unknown',
  },
  modalities: ['nlp'],
  tasks: ['text-classification'],
  tags: ['nlp', 'scrapes'],
  license: {
    status: 'unknown',
    name: 'Unknown License',
    commercial_use: 'unknown',
  },
  source_references: [
    {
      title: 'Portal',
      url: 'https://example.com/scrapes',
      type: 'official_website',
    },
  ],
  verification: {
    status: 'unverified',
  },
}

const mockMissingLic: DatasetMetadata = {
  schema_version: '1.0.0',
  id: 'legacy-tabular',
  slug: 'legacy-tabular',
  name: 'Legacy Tabular Archive',
  description: 'Legacy archive record with omitted license field.',
  homepage_url: 'https://example.com/legacy',
  publisher: {
    name: 'Archive Curator',
    type: 'unknown',
  },
  modalities: ['tabular'],
  tasks: ['tabular-regression'],
  tags: ['legacy'],
  license: null as unknown as DatasetMetadata['license'],
  source_references: [
    {
      title: 'Portal',
      url: 'https://example.com/legacy',
      type: 'archive',
    },
  ],
  verification: {
    status: 'unverified',
  },
}

const testCatalog: DatasetMetadata[] = [mockCifar, mockIris, mockNlpDataset]
const extendedCatalog: DatasetMetadata[] = [
  mockCifar,
  mockIris,
  mockNlpDataset,
  mockImageNet,
  mockCommonVoice,
  mockProprietary,
  mockUnknownLic,
  mockMissingLic,
]

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

  // 12. License filtering
  it('filters datasets by license status accurately', () => {
    // verified_open
    expect(matchesLicense(mockIris, 'verified_open')).toBe(true)
    expect(matchesLicense(mockCifar, 'verified_open')).toBe(false)
    expect(matchesLicense(mockImageNet, 'verified_open')).toBe(false)

    // verified_non_commercial
    expect(matchesLicense(mockImageNet, 'verified_non_commercial')).toBe(true)
    expect(matchesLicense(mockIris, 'verified_non_commercial')).toBe(false)

    // public_domain
    expect(matchesLicense(mockCommonVoice, 'public_domain')).toBe(true)
    expect(matchesLicense(mockIris, 'public_domain')).toBe(false)

    // proprietary
    expect(matchesLicense(mockProprietary, 'proprietary')).toBe(true)
    expect(matchesLicense(mockIris, 'proprietary')).toBe(false)

    // null or empty license status returns true (all licenses)
    expect(matchesLicense(mockIris, null)).toBe(true)
    expect(matchesLicense(mockIris, '')).toBe(true)

    // filterDatasets with license criterion
    const openDatasets = filterDatasets(extendedCatalog, { license: 'verified_open' })
    expect(openDatasets.map((d) => d.id)).toEqual(['iris', 'sst2'])

    const nonCommercial = filterDatasets(extendedCatalog, { license: 'verified_non_commercial' })
    expect(nonCommercial.map((d) => d.id)).toEqual(['imagenet-1k'])

    const publicDomain = filterDatasets(extendedCatalog, { license: 'public_domain' })
    expect(publicDomain.map((d) => d.id)).toEqual(['common-voice'])

    const proprietary = filterDatasets(extendedCatalog, { license: 'proprietary' })
    expect(proprietary.map((d) => d.id)).toEqual(['proprietary-market'])
  })

  // 13. Unknown and unspecified license statuses
  it('handles unspecified, unknown, and missing license statuses correctly', () => {
    // unspecified_by_source
    expect(matchesLicense(mockCifar, 'unspecified_by_source')).toBe(true)
    expect(matchesLicense(mockIris, 'unspecified_by_source')).toBe(false)

    // unknown
    expect(matchesLicense(mockUnknownLic, 'unknown')).toBe(true)
    expect(matchesLicense(mockIris, 'unknown')).toBe(false)

    // dataset with missing or null license field
    expect(matchesLicense(mockMissingLic, 'unknown')).toBe(true)
    expect(matchesLicense(mockMissingLic, 'unspecified_by_source')).toBe(true)
    expect(matchesLicense(mockMissingLic, 'verified_open')).toBe(false)
    expect(matchesLicense(mockMissingLic, 'verified_non_commercial')).toBe(false)

    const unspecified = filterDatasets(extendedCatalog, { license: 'unspecified_by_source' })
    expect(unspecified.map((d) => d.id)).toEqual(['cifar-10', 'legacy-tabular'])

    const unknown = filterDatasets(extendedCatalog, { license: 'unknown' })
    expect(unknown.map((d) => d.id)).toEqual(['experimental-nlp', 'legacy-tabular'])
  })

  it('formats license labels and extracts available license statuses', () => {
    expect(formatLicenseLabel('verified_open')).toBe('Verified Open')
    expect(formatLicenseLabel('verified_non_commercial')).toBe('Non-Commercial')
    expect(formatLicenseLabel('public_domain')).toBe('Public Domain')
    expect(formatLicenseLabel('unspecified_by_source')).toBe('Unspecified by Source')
    expect(formatLicenseLabel('proprietary')).toBe('Proprietary')
    expect(formatLicenseLabel('unknown')).toBe('Unknown License')

    const statuses = getAvailableLicenseStatuses(extendedCatalog)
    expect(statuses).toEqual([
      'verified_open',
      'public_domain',
      'verified_non_commercial',
      'unspecified_by_source',
      'proprietary',
      'unknown',
    ])
  })

  // 14. Combining all filter types
  it('combines search, category, modality, task, and license constraints together', () => {
    // Match ImageNet: category computer-vision, modality vision, task image-classification, license verified_non_commercial
    const matched = filterDatasets(extendedCatalog, {
      category: 'computer-vision',
      modality: 'vision',
      task: 'image-classification',
      license: 'verified_non_commercial',
      searchQuery: 'recognition',
    })
    expect(matched.length).toBe(1)
    expect(matched[0].id).toBe('imagenet-1k')

    // Conflicting criteria: category computer-vision but license public_domain -> 0
    const conflicting = filterDatasets(extendedCatalog, {
      category: 'computer-vision',
      license: 'public_domain',
    })
    expect(conflicting.length).toBe(0)

    // Tabular + verified_open -> Iris
    const tabularOpen = filterDatasets(extendedCatalog, {
      category: 'tabular-time-series',
      license: 'verified_open',
    })
    expect(tabularOpen.length).toBe(1)
    expect(tabularOpen[0].id).toBe('iris')

    // Tabular + proprietary -> Proprietary Market Telemetry
    const tabularProprietary = filterDatasets(extendedCatalog, {
      category: 'tabular-time-series',
      license: 'proprietary',
    })
    expect(tabularProprietary.length).toBe(1)
    expect(tabularProprietary[0].id).toBe('proprietary-market')
  })

  // 15. URL parameter parsing
  it('parses valid URL search parameters into FilterState', () => {
    const parsed = parseFilterParams(
      '?q=speech&category=audio-speech&modality=audio&task=speech-recognition&license=public_domain',
    )
    expect(parsed).toEqual({
      searchQuery: 'speech',
      category: 'audio-speech',
      modality: 'audio',
      task: 'speech-recognition',
      license: 'public_domain',
    })

    // URLSearchParams instance input
    const params = new URLSearchParams()
    params.set('q', 'mnist')
    params.set('category', 'computer-vision')
    params.set('license', 'verified_open')
    const parsedFromParams = parseFilterParams(params)
    expect(parsedFromParams.searchQuery).toBe('mnist')
    expect(parsedFromParams.category).toBe('computer-vision')
    expect(parsedFromParams.license).toBe('verified_open')
    expect(parsedFromParams.modality).toBe('')
    expect(parsedFromParams.task).toBe('')

    // Empty parameters returns default state
    expect(parseFilterParams('')).toEqual(DEFAULT_FILTER_STATE)
  })

  // 16. URL serialization
  it('serializes FilterState to URLSearchParams, omitting defaults and preserving extra params', () => {
    // Basic serialization
    const serialized = serializeFilterParams({
      searchQuery: 'mnist',
      category: 'computer-vision',
      license: 'verified_open',
    })
    expect(serialized.get('q')).toBe('mnist')
    expect(serialized.get('category')).toBe('computer-vision')
    expect(serialized.get('license')).toBe('verified_open')
    expect(serialized.has('modality')).toBe(false)
    expect(serialized.has('task')).toBe(false)

    // Preserves unrelated query parameters
    const existing = new URLSearchParams('theme=dark&ref=docs&category=audio-speech')
    const updated = serializeFilterParams(
      {
        category: 'computer-vision',
        searchQuery: 'cifar',
      },
      existing,
    )
    expect(updated.get('theme')).toBe('dark')
    expect(updated.get('ref')).toBe('docs')
    expect(updated.get('category')).toBe('computer-vision')
    expect(updated.get('q')).toBe('cifar')

    // Removes cleared filter parameters
    const cleared = serializeFilterParams(
      {
        category: null,
        searchQuery: '',
      },
      updated,
    )
    expect(cleared.has('category')).toBe(false)
    expect(cleared.has('q')).toBe(false)
    expect(cleared.get('theme')).toBe('dark')
    expect(cleared.get('ref')).toBe('docs')
  })

  // 17. Invalid URL parameters handling
  it('safely sanitizes and ignores invalid or malicious URL parameters', () => {
    const parsed = parseFilterParams(
      '?category=nonexistent-category&license=fake_license&q=%20%20&modality=INVALID$CHARS&task=INVALID#CHARS',
    )
    expect(parsed.category).toBeNull()
    expect(parsed.license).toBe('')
    expect(parsed.searchQuery).toBe('')
    expect(parsed.modality).toBe('')
    expect(parsed.task).toBe('')

    // Case normalization for valid values
    const upperCaseParsed = parseFilterParams(
      '?category=COMPUTER-VISION&license=VERIFIED_OPEN&modality=VISION&task=IMAGE-CLASSIFICATION',
    )
    expect(upperCaseParsed.category).toBe('computer-vision')
    expect(upperCaseParsed.license).toBe('verified_open')
    expect(upperCaseParsed.modality).toBe('vision')
    expect(upperCaseParsed.task).toBe('image-classification')
  })

  // 18. Reset behavior
  it('clears all active filter parameters upon reset while preserving unrelated params', () => {
    const existingParams = new URLSearchParams(
      '?q=test&category=computer-vision&modality=vision&task=image-classification&license=verified_open&sort=date',
    )

    const resetParams = serializeFilterParams(
      {
        searchQuery: '',
        category: null,
        modality: '',
        task: '',
        license: '',
      },
      existingParams,
    )

    expect(resetParams.has('q')).toBe(false)
    expect(resetParams.has('category')).toBe(false)
    expect(resetParams.has('modality')).toBe(false)
    expect(resetParams.has('task')).toBe(false)
    expect(resetParams.has('license')).toBe(false)
    expect(resetParams.get('sort')).toBe('date')

    // Filter datasets with reset criteria returns full catalog
    const allDatasets = filterDatasets(extendedCatalog, {
      searchQuery: '',
      category: null,
      modality: null,
      task: null,
      license: null,
    })
    expect(allDatasets.length).toBe(extendedCatalog.length)
  })

  // 19. Back/Forward navigation simulation
  it('correctly reflects browser navigation state transitions', () => {
    // Step 1: Initial empty state
    const history: string[] = ['']
    let currentFilters = parseFilterParams(history[history.length - 1])
    expect(currentFilters).toEqual(DEFAULT_FILTER_STATE)

    // Step 2: User filters by category computer-vision
    const step2Params = serializeFilterParams({ category: 'computer-vision' }, history[history.length - 1])
    history.push(step2Params.toString())
    currentFilters = parseFilterParams(history[history.length - 1])
    expect(currentFilters.category).toBe('computer-vision')

    // Step 3: User also filters by verified_open license
    const step3Params = serializeFilterParams({ license: 'verified_open' }, history[history.length - 1])
    history.push(step3Params.toString())
    currentFilters = parseFilterParams(history[history.length - 1])
    expect(currentFilters.category).toBe('computer-vision')
    expect(currentFilters.license).toBe('verified_open')

    // Step 4: User navigates Back to Step 2
    history.pop()
    currentFilters = parseFilterParams(history[history.length - 1])
    expect(currentFilters.category).toBe('computer-vision')
    expect(currentFilters.license).toBe('')

    // Step 5: User navigates Back to Step 1
    history.pop()
    currentFilters = parseFilterParams(history[history.length - 1])
    expect(currentFilters).toEqual(DEFAULT_FILTER_STATE)
  })
})
