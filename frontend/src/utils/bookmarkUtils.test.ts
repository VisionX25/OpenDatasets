import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import {
  BOOKMARK_STORAGE_KEY,
  BOOKMARK_EVENT_NAME,
  getBookmarkedSlugs,
  saveBookmarkedSlugs,
  toggleBookmarkSlug,
  isDatasetBookmarked,
} from './bookmarkUtils'

describe('bookmarkUtils', () => {
  let mockStorage: Record<string, string> = {}
  const originalLocalStorage = globalThis.localStorage
  const originalWindow = globalThis.window
  let fakeWindow: { localStorage: unknown; dispatchEvent: ReturnType<typeof vi.fn> }

  beforeEach(() => {
    mockStorage = {}
    const fakeLocalStorage = {
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

    fakeWindow = {
      localStorage: fakeLocalStorage,
      dispatchEvent: vi.fn(),
    }

    Object.defineProperty(globalThis, 'localStorage', {
      value: fakeLocalStorage,
      writable: true,
      configurable: true,
    })
    Object.defineProperty(globalThis, 'window', {
      value: fakeWindow,
      writable: true,
      configurable: true,
    })
  })

  afterEach(() => {
    Object.defineProperty(globalThis, 'localStorage', {
      value: originalLocalStorage,
      writable: true,
      configurable: true,
    })
    Object.defineProperty(globalThis, 'window', {
      value: originalWindow,
      writable: true,
      configurable: true,
    })
    vi.restoreAllMocks()
  })

  it('1. returns empty array when nothing is stored', () => {
    expect(getBookmarkedSlugs()).toEqual([])
  })

  it('2. reads and parses bookmarked slugs safely', () => {
    mockStorage[BOOKMARK_STORAGE_KEY] = JSON.stringify(['cifar-10', 'mnist'])
    expect(getBookmarkedSlugs()).toEqual(['cifar-10', 'mnist'])
  })

  it('3. filters invalid, empty, or duplicate entries', () => {
    mockStorage[BOOKMARK_STORAGE_KEY] = JSON.stringify(['cifar-10', '', '  ', null, 'cifar-10', 'mnist'])
    expect(getBookmarkedSlugs()).toEqual(['cifar-10', 'mnist'])
  })

  it('4. handles malformed JSON without crashing', () => {
    mockStorage[BOOKMARK_STORAGE_KEY] = '{not-valid-json'
    expect(getBookmarkedSlugs()).toEqual([])
  })

  it('5. saves clean slugs to localStorage and dispatches event', () => {
    const dispatchSpy = vi.spyOn(window, 'dispatchEvent')
    saveBookmarkedSlugs(['cifar-10', 'squad-2'])

    expect(JSON.parse(mockStorage[BOOKMARK_STORAGE_KEY])).toEqual(['cifar-10', 'squad-2'])
    expect(dispatchSpy).toHaveBeenCalled()
    const event = dispatchSpy.mock.calls[0][0] as CustomEvent
    expect(event.type).toBe(BOOKMARK_EVENT_NAME)
  })

  it('6. removes storage item when saving empty array', () => {
    mockStorage[BOOKMARK_STORAGE_KEY] = JSON.stringify(['cifar-10'])
    saveBookmarkedSlugs([])
    expect(mockStorage[BOOKMARK_STORAGE_KEY]).toBeUndefined()
  })

  it('7. toggleBookmarkSlug adds and removes slugs correctly', () => {
    const afterAdd = toggleBookmarkSlug('cifar-10')
    expect(afterAdd).toEqual(['cifar-10'])
    expect(isDatasetBookmarked('cifar-10', afterAdd)).toBe(true)

    const afterSecondAdd = toggleBookmarkSlug('mnist')
    expect(afterSecondAdd).toEqual(['cifar-10', 'mnist'])

    const afterRemove = toggleBookmarkSlug('cifar-10')
    expect(afterRemove).toEqual(['mnist'])
    expect(isDatasetBookmarked('cifar-10', afterRemove)).toBe(false)
  })

  it('8. handles empty or whitespace-only slug in toggle gracefully', () => {
    mockStorage[BOOKMARK_STORAGE_KEY] = JSON.stringify(['cifar-10'])
    const result = toggleBookmarkSlug('   ')
    expect(result).toEqual(['cifar-10'])
  })
})
