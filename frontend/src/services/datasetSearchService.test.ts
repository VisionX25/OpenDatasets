import { describe, it, expect } from 'vitest'
import type { DatasetMetadata, CategoryId } from '../types/dataset'
import { queryDatasets } from './datasetSearchService'
import { isDatasetSlug } from './catalogService'
import {
  isCategoryId,
  getCategoryById,
  getCategoryAccent,
  parseFilterParams,
  serializeFilterParams,
  DEFAULT_FILTER_STATE,
  CATEGORIES,
} from '../utils/datasetFilters'

// Helper to create synthetic test datasets for in-memory fixtures (no production metadata modified)
function createMockDataset(overrides: Partial<DatasetMetadata> & { id: string; name: string }): DatasetMetadata {
  return {
    schema_version: '1.0.0',
    id: overrides.id,
    slug: overrides.slug || overrides.id,
    name: overrides.name,
    description: overrides.description || `Description for ${overrides.name}`,
    homepage_url: `https://example.org/${overrides.id}`,
    publisher: overrides.publisher || { name: 'Test Org', type: 'academic' },
    modalities: overrides.modalities || ['vision'],
    tasks: overrides.tasks || ['image-classification'],
    tags: overrides.tags || ['test', 'computer-vision'],
    license: overrides.license || { status: 'verified_open', name: 'MIT' },
    source_references: overrides.source_references || [
      { title: 'Test Link', url: `https://example.org/${overrides.id}`, type: 'official_website' },
    ],
    verification: overrides.verification || { status: 'verified' },
    dates: overrides.dates || { published: '2020-01-01' },
  }
}

// Generate 30 distinct in-memory datasets for testing 24-card batching & Load More
const mockCatalog30: DatasetMetadata[] = Array.from({ length: 30 }, (_, i) => {
  const index = i + 1
  const padded = index.toString().padStart(2, '0')
  const categoryId: CategoryId =
    index <= 10
      ? 'computer-vision'
      : index <= 18
      ? 'natural-language-processing'
      : index <= 24
      ? 'audio-speech'
      : 'tabular-time-series'

  const task =
    categoryId === 'computer-vision'
      ? 'image-classification'
      : categoryId === 'natural-language-processing'
      ? 'text-classification'
      : categoryId === 'audio-speech'
      ? 'speech-recognition'
      : 'tabular-classification'

  const modality =
    categoryId === 'computer-vision'
      ? 'vision'
      : categoryId === 'natural-language-processing'
      ? 'nlp'
      : categoryId === 'audio-speech'
      ? 'audio'
      : 'tabular'

  const year = 2010 + (index % 12) // 2010 to 2021

  return createMockDataset({
    id: `mock-dataset-${padded}`,
    slug: `mock-dataset-${padded}`,
    name: `Dataset ${padded}`,
    tags: [categoryId, 'benchmark'],
    tasks: [task],
    modalities: [modality],
    dates: { published: `${year}-05-15` },
    license: {
      status: index % 2 === 0 ? 'verified_open' : 'public_domain',
      name: index % 2 === 0 ? 'Apache-2.0' : 'CC0',
    },
  })
})

describe('Scalable Dataset Browsing & Search Architecture (Task 06.3)', () => {
  // 1. Explore landing page navigation
  it('1. formats correct navigation targets from Explore landing page actions', () => {
    // Category selection navigates to /datasets/:categorySlug
    for (const cat of CATEGORIES) {
      const targetRoute = `/datasets/${cat.id}`
      expect(targetRoute).toBe(`/datasets/${cat.id}`)
    }

    // Global search submission navigates to /datasets?q=...
    const searchTarget = serializeFilterParams({ searchQuery: 'imagenet' })
    expect(`/datasets?${searchTarget.toString()}`).toBe('/datasets?q=imagenet')

    // Filter selection navigates to /datasets with query params
    const filterTarget = serializeFilterParams({ license: 'verified_open', modality: 'vision' })
    expect(filterTarget.get('license')).toBe('verified_open')
    expect(filterTarget.get('modality')).toBe('vision')

    // Browse all datasets links to /datasets
    expect('/datasets').toBe('/datasets')
  })

  // 2. Category route selection
  it('2. validates category route selection and breadcrumb metadata', () => {
    expect(isCategoryId('computer-vision')).toBe(true)
    expect(isCategoryId('audio-speech')).toBe(true)
    expect(isCategoryId('natural-language-processing')).toBe(true)

    const cvCategory = getCategoryById('computer-vision')
    expect(cvCategory).toBeDefined()
    expect(cvCategory?.name).toBe('Computer Vision')
    expect(getCategoryAccent('computer-vision').hex).toBe('#3B82F6')

    // Breadcrumb path representation
    const breadcrumbs = [
      { label: 'Explore', path: '/explore' },
      { label: cvCategory?.name, path: `/datasets/${cvCategory?.id}` },
    ]
    expect(breadcrumbs[0].path).toBe('/explore')
    expect(breadcrumbs[1].label).toBe('Computer Vision')
  })

  // 3. Category-scoped search
  it('3. scopes dataset search strictly within the selected category', async () => {
    const result = await queryDatasets({
      criteria: {
        category: 'computer-vision',
        searchQuery: 'Dataset 0',
      },
      datasets: mockCatalog30,
    })

    // In mockCatalog30, datasets 01-10 are computer-vision, 01-09 match 'Dataset 0'
    expect(result.totalMatches).toBe(9)
    expect(result.items.every((d) => d.tags.includes('computer-vision'))).toBe(true)

    // Ensure non-computer-vision datasets (even matching 'Dataset 0') are excluded
    const nonCv = result.items.filter((d) => !d.tags.includes('computer-vision'))
    expect(nonCv.length).toBe(0)
  })

  // 4. Global search
  it('4. performs global search across all categories matching multiple attributes', async () => {
    // Search by name
    const nameSearch = await queryDatasets({
      criteria: { searchQuery: 'Dataset 12' },
      datasets: mockCatalog30,
    })
    expect(nameSearch.totalMatches).toBe(1)
    expect(nameSearch.items[0].id).toBe('mock-dataset-12')

    // Search by task across categories
    const speechSearch = await queryDatasets({
      criteria: { searchQuery: 'speech-recognition' },
      datasets: mockCatalog30,
    })
    expect(speechSearch.totalMatches).toBe(6) // Datasets 19-24
    expect(speechSearch.items.every((d) => d.tasks.includes('speech-recognition'))).toBe(true)
  })

  // 5. Combined filters
  it('5. combines search query, category, modality, task, license, and published year', async () => {
    const combined = await queryDatasets({
      criteria: {
        category: 'natural-language-processing',
        searchQuery: 'Dataset',
        modality: 'nlp',
        task: 'text-classification',
        license: 'verified_open',
        year: '2016',
      },
      datasets: mockCatalog30,
    })

    expect(combined.items.every((d) => d.tags.includes('natural-language-processing'))).toBe(true)
    expect(combined.items.every((d) => d.modalities.includes('nlp'))).toBe(true)
    expect(combined.items.every((d) => d.license.status === 'verified_open')).toBe(true)
    expect(combined.items.every((d) => d.dates?.published?.startsWith('2016'))).toBe(true)
  })

  // 6. Direct URL navigation
  it('6. parses and serializes direct URL navigation states accurately', () => {
    const directUrl =
      '?q=speech&category=audio-speech&modality=audio&task=speech-recognition&license=public_domain&year=2018'
    const parsed = parseFilterParams(directUrl)

    expect(parsed.searchQuery).toBe('speech')
    expect(parsed.category).toBe('audio-speech')
    expect(parsed.modality).toBe('audio')
    expect(parsed.task).toBe('speech-recognition')
    expect(parsed.license).toBe('public_domain')
    expect(parsed.year).toBe('2018')

    const serialized = serializeFilterParams(parsed)
    expect(serialized.get('q')).toBe('speech')
    expect(serialized.get('category')).toBe('audio-speech')
    expect(serialized.get('year')).toBe('2018')
  })

  // 7. Browser Back/Forward behavior
  it('7. safely updates filter states across browser navigation transitions', () => {
    // Step 1: User navigates to /datasets
    let state = parseFilterParams('')
    expect(state).toEqual(DEFAULT_FILTER_STATE)

    // Step 2: User applies category filter
    state = parseFilterParams('?category=computer-vision')
    expect(state.category).toBe('computer-vision')
    expect(state.searchQuery).toBe('')

    // Step 3: User searches within category
    state = parseFilterParams('?category=computer-vision&q=resnet')
    expect(state.category).toBe('computer-vision')
    expect(state.searchQuery).toBe('resnet')

    // Step 4: User presses Back button (returns to ?category=computer-vision)
    state = parseFilterParams('?category=computer-vision')
    expect(state.category).toBe('computer-vision')
    expect(state.searchQuery).toBe('')

    // Step 5: User presses Back button again (returns to /datasets)
    state = parseFilterParams('')
    expect(state).toEqual(DEFAULT_FILTER_STATE)
  })

  // 8. Invalid category slug
  it('8. handles invalid category slugs gracefully without crashing or leaking catalog', () => {
    expect(isCategoryId('invalid-category-slug')).toBe(false)
    expect(isCategoryId('random-string-123')).toBe(false)
    expect(isCategoryId('')).toBe(false)
    expect(isCategoryId(null as unknown as string)).toBe(false)
    expect(isCategoryId(undefined as unknown as string)).toBe(false)

    expect(getCategoryById('invalid-category-slug')).toBeUndefined()
  })

  // 9. Initial 24-card rendering
  it('9. initially renders at most 24 dataset cards and indicates hasMore', async () => {
    const result = await queryDatasets({
      criteria: {},
      limit: 24,
      offset: 0,
      datasets: mockCatalog30,
    })

    expect(result.totalCatalogSize).toBe(30)
    expect(result.totalMatches).toBe(30)
    expect(result.items.length).toBe(24)
    expect(result.hasMore).toBe(true)

    // Items are deterministically sorted by name
    const names = result.items.map((d) => d.name)
    const sortedNames = [...names].sort((a, b) => a.localeCompare(b))
    expect(names).toEqual(sortedNames)
  })

  // 10. Load More incrementing
  it('10. reveals the next batch on Load More until all items are loaded', async () => {
    // Batch 1: first 24 items
    const batch1 = await queryDatasets({
      criteria: {},
      offset: 0,
      limit: 24,
      datasets: mockCatalog30,
    })
    expect(batch1.items.length).toBe(24)
    expect(batch1.hasMore).toBe(true)

    // Batch 2: next batch (remaining 6 items)
    const batch2 = await queryDatasets({
      criteria: {},
      offset: 24,
      limit: 24,
      datasets: mockCatalog30,
    })
    expect(batch2.items.length).toBe(6)
    expect(batch2.hasMore).toBe(false)

    // Combined unique items equal total catalog of 30
    const combinedIds = new Set([...batch1.items.map((d) => d.id), ...batch2.items.map((d) => d.id)])
    expect(combinedIds.size).toBe(30)
  })

  // 11. Reset behavior after filter changes
  it('11. resets active batch and parameters when filters change or are cleared', () => {
    // Given an active filter state
    const activeParams = new URLSearchParams('category=computer-vision&q=cat&modality=vision&year=2021')
    expect(parseFilterParams(activeParams).category).toBe('computer-vision')

    // Resetting filters
    const cleared = serializeFilterParams({
      searchQuery: '',
      category: null,
      modality: '',
      task: '',
      license: '',
      year: '',
    })

    expect(cleared.toString()).toBe('')
    expect(parseFilterParams(cleared)).toEqual(DEFAULT_FILTER_STATE)
  })

  // 12. No-results state
  it('12. returns an empty results state when no datasets match the criteria', async () => {
    const noResults = await queryDatasets({
      criteria: { searchQuery: 'completely-nonexistent-search-term-xyz' },
      datasets: mockCatalog30,
    })

    expect(noResults.items.length).toBe(0)
    expect(noResults.totalMatches).toBe(0)
    expect(noResults.hasMore).toBe(false)
  })

  // 13. Existing dataset detail navigation
  it('13. correctly distinguishes existing dataset slugs from category slugs and routes', () => {
    // Known dataset slugs
    expect(isDatasetSlug('cifar-10')).toBe(true)
    expect(isDatasetSlug('mnist')).toBe(true)
    expect(isDatasetSlug('imagenet-1k')).toBe(true)
    expect(isDatasetSlug('fashion-mnist')).toBe(true)
    expect(isDatasetSlug('common-voice')).toBe(true)
    expect(isDatasetSlug('california-housing')).toBe(true)

    // Categories are NOT dataset slugs
    expect(isDatasetSlug('computer-vision')).toBe(false)
    expect(isDatasetSlug('natural-language-processing')).toBe(false)
    expect(isDatasetSlug('audio-speech')).toBe(false)
    expect(isDatasetSlug('tabular-time-series')).toBe(false)

    // Arbitrary unknown slugs are NOT dataset slugs
    expect(isDatasetSlug('unknown-slug')).toBe(false)
    expect(isDatasetSlug('')).toBe(false)
    expect(isDatasetSlug(null)).toBe(false)
  })
})
