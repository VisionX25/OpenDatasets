import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import type { DatasetMetadata } from '../types/dataset'
import {
  fetchCatalog,
  getDatasetBySlug,
  clearCatalogCache,
  isValidDatasetRecord,
  validateCatalog,
} from './catalogService'

const validDataset: DatasetMetadata = {
  schema_version: '1.0.0',
  id: 'cifar-10',
  slug: 'cifar-10',
  name: 'CIFAR-10',
  description: '60,000 32x32 colour images in 10 classes.',
  homepage_url: 'https://www.cs.toronto.edu/~kriz/cifar.html',
  publisher: {
    name: 'University of Toronto',
    type: 'academic',
  },
  modalities: ['vision'],
  tasks: ['image-classification'],
  tags: ['benchmark', 'computer-vision'],
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

const validDataset2: DatasetMetadata = {
  schema_version: '1.0.0',
  id: 'iris',
  slug: 'iris',
  name: 'Iris Plants Database',
  description: '150 instances with 4 attributes.',
  homepage_url: 'https://archive.ics.uci.edu/dataset/53/iris',
  publisher: {
    name: 'UCI ML Repository',
    type: 'academic',
  },
  modalities: ['tabular'],
  tasks: ['tabular-classification'],
  tags: ['tabular', 'benchmark'],
  license: {
    status: 'verified_open',
    name: 'CC-BY-4.0',
  },
  source_references: [
    {
      title: 'UCI Page',
      url: 'https://archive.ics.uci.edu/dataset/53/iris',
      type: 'official_website',
    },
  ],
  verification: {
    status: 'verified',
  },
}

describe('Runtime Catalog Validation', () => {
  it('validates a complete valid dataset record', () => {
    expect(isValidDatasetRecord(validDataset)).toBe(true)
    expect(isValidDatasetRecord(validDataset2)).toBe(true)
  })

  it('rejects non-object candidates', () => {
    expect(isValidDatasetRecord(null)).toBe(false)
    expect(isValidDatasetRecord(undefined)).toBe(false)
    expect(isValidDatasetRecord('not-an-object')).toBe(false)
    expect(isValidDatasetRecord(12345)).toBe(false)
    expect(isValidDatasetRecord([])).toBe(false)
  })

  it('rejects records missing id, slug, or name', () => {
    expect(isValidDatasetRecord({ ...validDataset, id: '' })).toBe(false)
    expect(isValidDatasetRecord({ ...validDataset, id: '   ' })).toBe(false)
    expect(isValidDatasetRecord({ ...validDataset, slug: '' })).toBe(false)
    expect(isValidDatasetRecord({ ...validDataset, slug: undefined })).toBe(false)
    expect(isValidDatasetRecord({ ...validDataset, name: '' })).toBe(false)
    expect(isValidDatasetRecord({ ...validDataset, name: null })).toBe(false)
  })

  it('rejects records with missing or invalid publisher', () => {
    expect(isValidDatasetRecord({ ...validDataset, publisher: null })).toBe(false)
    expect(isValidDatasetRecord({ ...validDataset, publisher: {} })).toBe(false)
    expect(isValidDatasetRecord({ ...validDataset, publisher: { name: '' } })).toBe(false)
  })

  it('rejects records with empty or invalid modalities', () => {
    expect(isValidDatasetRecord({ ...validDataset, modalities: [] })).toBe(false)
    expect(isValidDatasetRecord({ ...validDataset, modalities: 'vision' })).toBe(false)
    expect(isValidDatasetRecord({ ...validDataset, modalities: null })).toBe(false)
  })

  it('rejects records with invalid tasks, tags, or source_references arrays', () => {
    expect(isValidDatasetRecord({ ...validDataset, tasks: null })).toBe(false)
    expect(isValidDatasetRecord({ ...validDataset, tags: 'not-an-array' })).toBe(false)
    expect(isValidDatasetRecord({ ...validDataset, source_references: {} })).toBe(false)
  })

  it('rejects records with invalid license or verification structures', () => {
    expect(isValidDatasetRecord({ ...validDataset, license: null })).toBe(false)
    expect(isValidDatasetRecord({ ...validDataset, license: { name: 'MIT' } })).toBe(false)
    expect(isValidDatasetRecord({ ...validDataset, verification: null })).toBe(false)
    expect(isValidDatasetRecord({ ...validDataset, verification: {} })).toBe(false)
  })

  it('validateCatalog accepts a valid array of datasets', () => {
    const catalog = validateCatalog([validDataset, validDataset2])
    expect(catalog.length).toBe(2)
  })

  it('validateCatalog throws on non-array catalog payloads', () => {
    expect(() => validateCatalog(null)).toThrow('Malformed dataset catalog: expected JSON array.')
    expect(() => validateCatalog({ datasets: [validDataset] })).toThrow(
      'Malformed dataset catalog: expected JSON array.',
    )
    expect(() => validateCatalog('invalid')).toThrow('Malformed dataset catalog: expected JSON array.')
  })

  it('validateCatalog throws when a catalog record is malformed', () => {
    const malformed = [validDataset, { id: 'bad' }]
    expect(() => validateCatalog(malformed)).toThrow(
      'Malformed dataset catalog: record at index 1 is missing essential dataset properties.',
    )
  })
})

describe('Catalog Service Fetch and Error Handling', () => {
  beforeEach(() => {
    clearCatalogCache()
    vi.restoreAllMocks()
  })

  afterEach(() => {
    clearCatalogCache()
    vi.restoreAllMocks()
  })

  it('successfully fetches and caches dataset catalog', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => [validDataset, validDataset2],
    })
    vi.stubGlobal('fetch', fetchMock)

    const first = await fetchCatalog()
    expect(first.length).toBe(2)
    expect(first[0].id).toBe('cifar-10')
    expect(fetchMock).toHaveBeenCalledTimes(1)

    // Second call should hit the cache without re-fetching
    const second = await fetchCatalog()
    expect(second).toBe(first)
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it('handles failed catalog requests (HTTP 404 / 500 error)', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
      statusText: 'Not Found',
    })
    vi.stubGlobal('fetch', fetchMock)

    await expect(fetchCatalog()).rejects.toThrow(
      'Failed to load dataset catalog: HTTP 404 (Not Found)',
    )
  })

  it('handles network-level fetch failures', async () => {
    const fetchMock = vi.fn().mockRejectedValue(new Error('Network connection timeout'))
    vi.stubGlobal('fetch', fetchMock)

    await expect(fetchCatalog()).rejects.toThrow('Network connection timeout')
  })

  it('handles malformed JSON response bodies', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => {
        throw new SyntaxError('Unexpected token < in JSON at position 0')
      },
    })
    vi.stubGlobal('fetch', fetchMock)

    await expect(fetchCatalog()).rejects.toThrow('Failed to parse dataset catalog:')
  })

  it('handles malformed catalog responses (non-array response)', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ error: 'Service Unavailable' }),
    })
    vi.stubGlobal('fetch', fetchMock)

    await expect(fetchCatalog()).rejects.toThrow('Malformed dataset catalog: expected JSON array.')
  })

  it('retries successfully when forceReload is requested or after failure', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: false,
        status: 503,
        statusText: 'Service Unavailable',
      })
      .mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => [validDataset],
      })
    vi.stubGlobal('fetch', fetchMock)

    // First attempt fails
    await expect(fetchCatalog()).rejects.toThrow('Failed to load dataset catalog: HTTP 503')

    // Second attempt (retry) succeeds because cache was not poisoned
    const retryResult = await fetchCatalog()
    expect(retryResult.length).toBe(1)
    expect(retryResult[0].id).toBe('cifar-10')
    expect(fetchMock).toHaveBeenCalledTimes(2)

    // Using forceReload explicitly calls fetch again
    await fetchCatalog({ forceReload: true })
    expect(fetchMock).toHaveBeenCalledTimes(3)
  })
})

describe('getDatasetBySlug Lookup Behavior', () => {
  beforeEach(() => {
    clearCatalogCache()
    vi.restoreAllMocks()
  })

  afterEach(() => {
    clearCatalogCache()
    vi.restoreAllMocks()
  })

  it('finds existing dataset by slug', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => [validDataset, validDataset2],
    })
    vi.stubGlobal('fetch', fetchMock)

    const dataset = await getDatasetBySlug('cifar-10')
    expect(dataset).not.toBeNull()
    expect(dataset?.name).toBe('CIFAR-10')
  })

  it('trims whitespace when searching by slug', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => [validDataset, validDataset2],
    })
    vi.stubGlobal('fetch', fetchMock)

    const dataset = await getDatasetBySlug('  iris  ')
    expect(dataset).not.toBeNull()
    expect(dataset?.id).toBe('iris')
  })

  it('returns null when dataset slug is missing or not found in catalog', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => [validDataset],
    })
    vi.stubGlobal('fetch', fetchMock)

    const notFound = await getDatasetBySlug('nonexistent-slug')
    expect(notFound).toBeNull()
  })

  it('returns null immediately without fetching for missing/empty slugs', async () => {
    const fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock)

    expect(await getDatasetBySlug('')).toBeNull()
    expect(await getDatasetBySlug('   ')).toBeNull()
    expect(await getDatasetBySlug(undefined)).toBeNull()
    expect(await getDatasetBySlug(null)).toBeNull()

    // No network requests should have been initiated
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('propagates catalog loading failures so callers can distinguish errors from 404', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      statusText: 'Internal Server Error',
    })
    vi.stubGlobal('fetch', fetchMock)

    await expect(getDatasetBySlug('cifar-10')).rejects.toThrow(
      'Failed to load dataset catalog: HTTP 500 (Internal Server Error)',
    )
  })
})
