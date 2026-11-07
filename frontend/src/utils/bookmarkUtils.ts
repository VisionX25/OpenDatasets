/**
 * Safe client-side bookmark utilities for saving and managing bookmarked dataset slugs.
 * Stored in browser localStorage under a stable key, with graceful error handling
 * for private browsing, quota limits, and SSR environments.
 */

export const BOOKMARK_STORAGE_KEY = 'opendatasets_saved_bookmarks'
export const BOOKMARK_EVENT_NAME = 'opendatasets-bookmarks-updated'

function getLocalStorage(): Storage | null {
  try {
    if (typeof globalThis !== 'undefined' && 'localStorage' in globalThis && globalThis.localStorage) {
      return globalThis.localStorage
    }
  } catch {
    // Ignore access denial (e.g., in sandboxed iframes or disabled storage)
  }
  return null
}

/**
 * Retrieve all bookmarked dataset slugs from localStorage safely.
 */
export function getBookmarkedSlugs(): string[] {
  const storage = getLocalStorage()
  if (!storage) {
    return []
  }
  try {
    const raw = storage.getItem(BOOKMARK_STORAGE_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw)
    if (!Array.isArray(parsed)) return []
    return Array.from(
      new Set(
        parsed
          .filter((item): item is string => typeof item === 'string' && item.trim().length > 0)
          .map((item) => item.trim()),
      ),
    )
  } catch {
    return []
  }
}

/**
 * Save bookmarked dataset slugs to localStorage safely and notify listeners.
 */
export function saveBookmarkedSlugs(slugs: string[]): void {
  const storage = getLocalStorage()
  const cleanSlugs = Array.from(
    new Set(
      slugs
        .filter((item): item is string => typeof item === 'string' && item.trim().length > 0)
        .map((item) => item.trim()),
    ),
  )

  if (storage) {
    try {
      if (cleanSlugs.length === 0) {
        storage.removeItem(BOOKMARK_STORAGE_KEY)
      } else {
        storage.setItem(BOOKMARK_STORAGE_KEY, JSON.stringify(cleanSlugs))
      }
    } catch {
      // Ignore quota exceeded or storage disabled
    }
  }

  // Dispatch custom event for cross-component reactivity
  if (typeof window !== 'undefined' && typeof window.dispatchEvent === 'function') {
    try {
      window.dispatchEvent(new CustomEvent(BOOKMARK_EVENT_NAME, { detail: cleanSlugs }))
    } catch {
      // Ignore event dispatch failure
    }
  }
}

/**
 * Toggle a dataset bookmark by slug. Returns the updated array of bookmarked slugs.
 */
export function toggleBookmarkSlug(slug: string): string[] {
  const trimmed = slug.trim()
  if (!trimmed) return getBookmarkedSlugs()

  const current = getBookmarkedSlugs()
  const exists = current.includes(trimmed)
  const next = exists ? current.filter((s) => s !== trimmed) : [...current, trimmed]
  saveBookmarkedSlugs(next)
  return next
}

/**
 * Check if a dataset slug is currently bookmarked.
 */
export function isDatasetBookmarked(slug: string, bookmarkedSlugs: string[]): boolean {
  if (!slug) return false
  return bookmarkedSlugs.includes(slug.trim())
}
