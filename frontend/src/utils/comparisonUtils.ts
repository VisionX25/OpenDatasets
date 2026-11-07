/**
 * Utility functions for dataset comparison selection state, URL parameters,
 * and sessionStorage synchronization.
 */

export const MAX_COMPARE_COUNT = 3
export const MIN_COMPARE_COUNT = 2
export const COMPARE_STORAGE_KEY = 'opendatasets_compare_selection'

function getSessionStorage(): Storage | null {
  try {
    if (typeof globalThis !== 'undefined' && 'sessionStorage' in globalThis && globalThis.sessionStorage) {
      return globalThis.sessionStorage
    }
  } catch {
    // Ignore access denial (e.g., in sandboxed iframes or SSR)
  }
  return null
}

/**
 * Read the list of selected dataset slugs from sessionStorage safely.
 * Returns an array of up to MAX_COMPARE_COUNT valid strings, or [] if none.
 */
export function getStoredComparisonSlugs(): string[] {
  const storage = getSessionStorage()
  if (!storage) {
    return []
  }
  try {
    const raw = storage.getItem(COMPARE_STORAGE_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw)
    if (!Array.isArray(parsed)) return []
    const cleanSlugs = parsed
      .filter((item): item is string => typeof item === 'string' && item.trim().length > 0)
      .map((item) => item.trim())
    // Deduplicate and enforce max count
    return Array.from(new Set(cleanSlugs)).slice(0, MAX_COMPARE_COUNT)
  } catch {
    return []
  }
}

/**
 * Save the list of selected dataset slugs to sessionStorage safely.
 */
export function saveStoredComparisonSlugs(slugs: string[]): void {
  const storage = getSessionStorage()
  if (!storage) {
    return
  }
  try {
    const cleanSlugs = slugs
      .filter((item): item is string => typeof item === 'string' && item.trim().length > 0)
      .map((item) => item.trim())
    const uniqueSlugs = Array.from(new Set(cleanSlugs)).slice(0, MAX_COMPARE_COUNT)
    if (uniqueSlugs.length === 0) {
      storage.removeItem(COMPARE_STORAGE_KEY)
    } else {
      storage.setItem(COMPARE_STORAGE_KEY, JSON.stringify(uniqueSlugs))
    }
  } catch {
    // Gracefully ignore storage quota / sandbox security errors
  }
}

/**
 * Parse dataset slugs from URL query string (e.g., ?datasets=mnist,cifar-10).
 */
export function parseCompareSlugsFromUrl(search: string): string[] {
  if (!search) return []
  try {
    const searchString = search.startsWith('?') ? search.slice(1) : search
    const params = new URLSearchParams(searchString)
    const datasetsParam = params.get('datasets')
    if (!datasetsParam) return []
    const rawSlugs = datasetsParam
      .split(',')
      .map((s) => s.trim())
      .filter((s) => s.length > 0)
    return Array.from(new Set(rawSlugs)).slice(0, MAX_COMPARE_COUNT)
  } catch {
    return []
  }
}

/**
 * Build a compare page URL from an array of slugs.
 */
export function buildCompareUrl(slugs: string[]): string {
  const clean = Array.from(new Set(slugs.filter(Boolean))).slice(0, MAX_COMPARE_COUNT)
  if (clean.length === 0) return '/compare'
  return `/compare?datasets=${clean.join(',')}`
}
