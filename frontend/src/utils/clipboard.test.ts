import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { copyTextToClipboard } from './clipboard'

describe('Clipboard Utility (copyTextToClipboard)', () => {
  const originalNavigator = globalThis.navigator
  const originalDocument = globalThis.document

  beforeEach(() => {
    vi.restoreAllMocks()
  })

  afterEach(() => {
    // Restore globals
    Object.defineProperty(globalThis, 'navigator', {
      value: originalNavigator,
      writable: true,
      configurable: true,
    })
    Object.defineProperty(globalThis, 'document', {
      value: originalDocument,
      writable: true,
      configurable: true,
    })
  })

  it('returns false for empty or non-string input without calling clipboard APIs', async () => {
    const writeTextMock = vi.fn()
    Object.defineProperty(globalThis, 'navigator', {
      value: { clipboard: { writeText: writeTextMock } },
      writable: true,
      configurable: true,
    })

    expect(await copyTextToClipboard('')).toBe(false)
    expect(await copyTextToClipboard(null as unknown as string)).toBe(false)
    expect(await copyTextToClipboard(undefined as unknown as string)).toBe(false)
    expect(writeTextMock).not.toHaveBeenCalled()
  })

  it('successfully writes text via modern navigator.clipboard.writeText and returns true', async () => {
    const writeTextMock = vi.fn().mockResolvedValue(undefined)
    Object.defineProperty(globalThis, 'navigator', {
      value: { clipboard: { writeText: writeTextMock } },
      writable: true,
      configurable: true,
    })

    const sampleBibtex = '@article{test, title={OpenDatasets}}'
    const result = await copyTextToClipboard(sampleBibtex)

    expect(result).toBe(true)
    expect(writeTextMock).toHaveBeenCalledWith(sampleBibtex)
  })

  it('falls back to document.execCommand when navigator.clipboard.writeText rejects', async () => {
    const writeTextMock = vi.fn().mockRejectedValue(new Error('Permission denied'))
    const execCommandMock = vi.fn().mockReturnValue(true)

    const appendChildMock = vi.fn()
    const removeChildMock = vi.fn()
    const dummyElement = {
      value: '',
      setAttribute: vi.fn(),
      style: {},
      focus: vi.fn(),
      select: vi.fn(),
    }

    Object.defineProperty(globalThis, 'navigator', {
      value: { clipboard: { writeText: writeTextMock } },
      writable: true,
      configurable: true,
    })

    Object.defineProperty(globalThis, 'document', {
      value: {
        execCommand: execCommandMock,
        createElement: vi.fn().mockReturnValue(dummyElement),
        body: {
          appendChild: appendChildMock,
          removeChild: removeChildMock,
        },
      },
      writable: true,
      configurable: true,
    })

    const result = await copyTextToClipboard('test copy content')
    expect(result).toBe(true)
    expect(writeTextMock).toHaveBeenCalledTimes(1)
    expect(execCommandMock).toHaveBeenCalledWith('copy')
    expect(removeChildMock).toHaveBeenCalledWith(dummyElement)
  })

  it('returns false when modern clipboard fails and document.execCommand is unavailable', async () => {
    const writeTextMock = vi.fn().mockRejectedValue(new Error('Write failed'))
    Object.defineProperty(globalThis, 'navigator', {
      value: { clipboard: { writeText: writeTextMock } },
      writable: true,
      configurable: true,
    })
    Object.defineProperty(globalThis, 'document', {
      value: undefined,
      writable: true,
      configurable: true,
    })

    const result = await copyTextToClipboard('test string')
    expect(result).toBe(false)
  })

  it('works via document.execCommand when navigator.clipboard is absent', async () => {
    const execCommandMock = vi.fn().mockReturnValue(true)
    const dummyElement = {
      value: '',
      setAttribute: vi.fn(),
      style: {},
      focus: vi.fn(),
      select: vi.fn(),
    }

    Object.defineProperty(globalThis, 'navigator', {
      value: {},
      writable: true,
      configurable: true,
    })

    Object.defineProperty(globalThis, 'document', {
      value: {
        execCommand: execCommandMock,
        createElement: vi.fn().mockReturnValue(dummyElement),
        body: {
          appendChild: vi.fn(),
          removeChild: vi.fn(),
        },
      },
      writable: true,
      configurable: true,
    })

    const result = await copyTextToClipboard('legacy fallback test')
    expect(result).toBe(true)
    expect(execCommandMock).toHaveBeenCalledWith('copy')
  })

  it('returns false when document.execCommand returns false', async () => {
    const execCommandMock = vi.fn().mockReturnValue(false)
    const dummyElement = {
      value: '',
      setAttribute: vi.fn(),
      style: {},
      focus: vi.fn(),
      select: vi.fn(),
    }

    Object.defineProperty(globalThis, 'navigator', {
      value: {},
      writable: true,
      configurable: true,
    })

    Object.defineProperty(globalThis, 'document', {
      value: {
        execCommand: execCommandMock,
        createElement: vi.fn().mockReturnValue(dummyElement),
        body: {
          appendChild: vi.fn(),
          removeChild: vi.fn(),
        },
      },
      writable: true,
      configurable: true,
    })

    const result = await copyTextToClipboard('legacy failure test')
    expect(result).toBe(false)
  })
})
