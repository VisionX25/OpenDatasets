import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import {
  MAX_COMPARE_COUNT,
  MIN_COMPARE_COUNT,
  COMPARE_STORAGE_KEY,
  getStoredComparisonSlugs,
  saveStoredComparisonSlugs,
  parseCompareSlugsFromUrl,
  buildCompareUrl,
} from './comparisonUtils'

describe('comparisonUtils', () => {
  let mockStorage: Record<string, string> = {}
  const originalSessionStorage = globalThis.sessionStorage

  beforeEach(() => {
    mockStorage = {}
    const fakeSessionStorage = {
      getItem: vi.fn((key: string) => mockStorage[key] ?? null),
      setItem: vi.fn((key: string, val: string) => {
        mockStorage[key] = val
      }),
      removeItem: vi.fn((key: string) => {
        delete mockStorage[key]
      }),
      clear: vi.fn(() => {
        mockStorage = {}
      }),
      length: 0,
      key: vi.fn(() => null),
    }

    Object.defineProperty(globalThis, 'sessionStorage', {
      value: fakeSessionStorage,
      writable: true,
      configurable: true,
    })
  })

  afterEach(() => {
    Object.defineProperty(globalThis, 'sessionStorage', {
      value: originalSessionStorage,
      writable: true,
      configurable: true,
    })
    vi.restoreAllMocks()
  })

  it('exposes expected limits', () => {
    expect(MAX_COMPARE_COUNT).toBe(3)
    expect(MIN_COMPARE_COUNT).toBe(2)
  })

  describe('sessionStorage management', () => {
    it('returns empty array when storage is empty', () => {
      expect(getStoredComparisonSlugs()).toEqual([])
    })

    it('saves and retrieves slugs up to maximum of 3', () => {
      saveStoredComparisonSlugs(['cifar-10', 'mnist'])
      expect(getStoredComparisonSlugs()).toEqual(['cifar-10', 'mnist'])

      // Adding 4th slug should cap at 3
      saveStoredComparisonSlugs(['cifar-10', 'mnist', 'imagenet-1k', 'squad'])
      expect(getStoredComparisonSlugs()).toEqual(['cifar-10', 'mnist', 'imagenet-1k'])
    })

    it('deduplicates slugs and trims whitespace', () => {
      saveStoredComparisonSlugs([' cifar-10 ', 'mnist', 'cifar-10'])
      expect(getStoredComparisonSlugs()).toEqual(['cifar-10', 'mnist'])
    })

    it('clears storage when empty array is saved', () => {
      saveStoredComparisonSlugs(['cifar-10'])
      expect(getStoredComparisonSlugs()).toEqual(['cifar-10'])

      saveStoredComparisonSlugs([])
      expect(getStoredComparisonSlugs()).toEqual([])
      expect(globalThis.sessionStorage.getItem(COMPARE_STORAGE_KEY)).toBeNull()
    })

    it('handles malformed JSON in storage gracefully', () => {
      globalThis.sessionStorage.setItem(COMPARE_STORAGE_KEY, '{invalid json')
      expect(getStoredComparisonSlugs()).toEqual([])
    })

    it('handles unavailable sessionStorage gracefully', () => {
      Object.defineProperty(globalThis, 'sessionStorage', {
        value: undefined,
        writable: true,
        configurable: true,
      })
      expect(getStoredComparisonSlugs()).toEqual([])
      expect(() => saveStoredComparisonSlugs(['cifar-10'])).not.toThrow()
    })
  })

  describe('URL parsing and building', () => {
    it('parses comma-separated slugs from search string', () => {
      const search = '?datasets=cifar-10,mnist'
      expect(parseCompareSlugsFromUrl(search)).toEqual(['cifar-10', 'mnist'])
    })

    it('handles search string without leading question mark', () => {
      const search = 'datasets=cifar-10,mnist'
      expect(parseCompareSlugsFromUrl(search)).toEqual(['cifar-10', 'mnist'])
    })

    it('deduplicates and limits to max 3 slugs from URL', () => {
      const search = '?datasets=cifar-10,mnist,cifar-10,imagenet-1k,squad'
      expect(parseCompareSlugsFromUrl(search)).toEqual(['cifar-10', 'mnist', 'imagenet-1k'])
    })

    it('returns empty array if datasets parameter is absent or empty', () => {
      expect(parseCompareSlugsFromUrl('')).toEqual([])
      expect(parseCompareSlugsFromUrl('?other=value')).toEqual([])
      expect(parseCompareSlugsFromUrl('?datasets=')).toEqual([])
    })

    it('builds canonical compare URL', () => {
      expect(buildCompareUrl(['cifar-10', 'mnist'])).toBe('/compare?datasets=cifar-10,mnist')
      expect(buildCompareUrl(['cifar-10'])).toBe('/compare?datasets=cifar-10')
      expect(buildCompareUrl([])).toBe('/compare')
    })
  })
})
