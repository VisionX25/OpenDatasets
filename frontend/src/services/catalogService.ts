import type { DatasetMetadata } from '../types/dataset'

let catalogCache: DatasetMetadata[] | null = null
let inflightPromise: Promise<DatasetMetadata[]> | null = null

/**
 * Fetch the dataset catalog from /data/catalog.json.
 * Caches the response in-memory for subsequent requests.
 */
export async function fetchCatalog(): Promise<DatasetMetadata[]> {
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
          `Failed to load dataset catalog: HTTP ${response.status} (${response.statusText})`,
        )
      }

      const data = await response.json()
      if (!Array.isArray(data)) {
        throw new Error('Malformed dataset catalog: expected JSON array.')
      }

      catalogCache = data as DatasetMetadata[]
      return catalogCache
    } finally {
      inflightPromise = null
    }
  })()

  return inflightPromise
}

/**
 * Find a dataset in the catalog by its URL slug.
 */
export async function getDatasetBySlug(
  slug: string,
): Promise<DatasetMetadata | null> {
  const catalog = await fetchCatalog()
  const found = catalog.find((item) => item.slug === slug)
  return found ?? null
}

/**
 * Invalidate the memory cache (primarily for tests).
 */
export function clearCatalogCache(): void {
  catalogCache = null
  inflightPromise = null
}
