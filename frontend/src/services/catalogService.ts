import type { DatasetMetadata } from '../types/dataset'

export interface FetchCatalogOptions {
  forceReload?: boolean
}

let catalogCache: DatasetMetadata[] | null = null
let inflightPromise: Promise<DatasetMetadata[]> | null = null

/**
 * Lightweight runtime validation of essential dataset properties before rendering.
 * The Python JSON Schema (schemas/dataset.v1.schema.json) remains the canonical
 * full schema validation system.
 */
export function isValidDatasetRecord(record: unknown): record is DatasetMetadata {
  if (typeof record !== 'object' || record === null || Array.isArray(record)) {
    return false
  }

  const candidate = record as Record<string, unknown>

  // Essential string identifiers and titles
  if (typeof candidate.id !== 'string' || candidate.id.trim().length === 0) {
    return false
  }
  if (typeof candidate.slug !== 'string' || candidate.slug.trim().length === 0) {
    return false
  }
  if (typeof candidate.name !== 'string' || candidate.name.trim().length === 0) {
    return false
  }
  if (typeof candidate.description !== 'string') {
    return false
  }
  if (typeof candidate.homepage_url !== 'string') {
    return false
  }

  // Publisher object
  if (
    typeof candidate.publisher !== 'object' ||
    candidate.publisher === null ||
    Array.isArray(candidate.publisher)
  ) {
    return false
  }
  const publisher = candidate.publisher as Record<string, unknown>
  if (typeof publisher.name !== 'string' || publisher.name.trim().length === 0) {
    return false
  }

  // Modalities array (must contain at least one modality)
  if (!Array.isArray(candidate.modalities) || candidate.modalities.length === 0) {
    return false
  }

  // Tasks and tags arrays
  if (!Array.isArray(candidate.tasks)) {
    return false
  }
  if (!Array.isArray(candidate.tags)) {
    return false
  }

  // License object
  if (
    typeof candidate.license !== 'object' ||
    candidate.license === null ||
    Array.isArray(candidate.license)
  ) {
    return false
  }
  const license = candidate.license as Record<string, unknown>
  if (typeof license.status !== 'string' || typeof license.name !== 'string') {
    return false
  }

  // Source references array
  if (!Array.isArray(candidate.source_references)) {
    return false
  }

  // Verification object
  if (
    typeof candidate.verification !== 'object' ||
    candidate.verification === null ||
    Array.isArray(candidate.verification)
  ) {
    return false
  }
  const verification = candidate.verification as Record<string, unknown>
  if (typeof verification.status !== 'string') {
    return false
  }

  return true
}

/**
 * Validates that data is a non-null array of valid dataset records.
 * Throws a descriptive Error if the data structure is malformed.
 */
export function validateCatalog(data: unknown): DatasetMetadata[] {
  if (!Array.isArray(data)) {
    throw new Error('Malformed dataset catalog: expected JSON array.')
  }

  for (let i = 0; i < data.length; i++) {
    const item = data[i]
    if (!isValidDatasetRecord(item)) {
      throw new Error(
        `Malformed dataset catalog: record at index ${i} is missing essential dataset properties.`,
      )
    }
  }

  return data as DatasetMetadata[]
}

/**
 * Fetch the dataset catalog from /data/catalog.json.
 * Validates the response at runtime and caches the result in-memory.
 */
export async function fetchCatalog(
  options: FetchCatalogOptions = {},
): Promise<DatasetMetadata[]> {
  if (options.forceReload) {
    catalogCache = null
  }

  if (catalogCache !== null) {
    return catalogCache
  }

  if (inflightPromise !== null) {
    return inflightPromise
  }

  inflightPromise = (async () => {
    try {
      const response = await fetch('/data/catalog.json', {
        headers: {
          Accept: 'application/json',
        },
      })

      if (!response.ok) {
        throw new Error(
          `Failed to load dataset catalog: HTTP ${response.status} (${response.statusText || 'Error'})`,
        )
      }

      let data: unknown
      try {
        data = await response.json()
      } catch (parseErr) {
        throw new Error(
          `Failed to parse dataset catalog: ${parseErr instanceof Error ? parseErr.message : 'Invalid JSON'}`,
          { cause: parseErr },
        )
      }

      const validated = validateCatalog(data)
      catalogCache = validated
      return catalogCache
    } finally {
      inflightPromise = null
    }
  })()

  return inflightPromise
}

/**
 * Find a dataset in the catalog by its URL slug.
 * Returns null if the slug is empty or dataset is not found in the catalog.
 * Propagates fetch errors so callers can distinguish loading errors from 404 (not found).
 */
export async function getDatasetBySlug(
  slug: string | undefined | null,
  options: FetchCatalogOptions = {},
): Promise<DatasetMetadata | null> {
  if (!slug || typeof slug !== 'string' || !slug.trim()) {
    return null
  }

  const catalog = await fetchCatalog(options)
  const normalizedSlug = slug.trim()
  const found = catalog.find((item) => item.slug === normalizedSlug)
  return found ?? null
}

/**
 * Invalidate the memory cache (primarily for tests or manual refresh).
 */
export function clearCatalogCache(): void {
  catalogCache = null
  inflightPromise = null
}

const KNOWN_DATASET_SLUGS = new Set([
  'adult-census-income',
  'ai2-arc',
  'bangladeshi-banknote-serial',
  'bangladeshi-currency-recognition',
  'california-housing',
  'celeba',
  'cifar-10',
  'common-voice',
  'dolma',
  'esc-50',
  'fashion-mnist',
  'fineweb-2',
  'glue-benchmark',
  'gsm8k',
  'humanitys-last-exam',
  'imagenet-1k',
  'imdb-reviews',
  'iris',
  'jaaltaka',
  'librispeech',
  'mnist',
  'ms-coco',
  'open-images-v7',
  'squad-2',
  'ultrachat-200k',
  'wider-face',
  'wine-quality',
])

/**
 * Checks whether a given slug matches a known dataset record.
 */
export function isDatasetSlug(slug: string | null | undefined): boolean {
  if (!slug) return false
  const trimmed = slug.trim()
  if (KNOWN_DATASET_SLUGS.has(trimmed)) return true
  if (catalogCache) {
    return catalogCache.some((d) => d.slug === trimmed || d.id === trimmed)
  }
  return false
}
