import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderToString } from 'react-dom/server'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { DatasetsPage } from './DatasetsPage'
import { CATEGORIES } from '../utils/datasetFilters'
import * as catalogService from '../services/catalogService'
import type { DatasetMetadata } from '../types/dataset'

const mockCatalog: DatasetMetadata[] = [
  {
    schema_version: '1.0.0',
    id: 'cifar-10',
    slug: 'cifar-10',
    name: 'CIFAR-10',
    description: 'Image dataset',
    homepage_url: 'https://example.com/cifar-10',
    publisher: { name: 'Toronto', type: 'academic' },
    modalities: ['vision'],
    tasks: ['image-classification'],
    tags: ['benchmark'],
    license: { status: 'public_domain', name: 'Public Domain' },
    source_references: [{ title: 'Home', url: 'https://example.com', type: 'official_website' }],
    verification: { status: 'verified' },
  },
  {
    schema_version: '1.0.0',
    id: 'squad-2',
    slug: 'squad-2',
    name: 'SQuAD 2.0',
    description: 'Question answering dataset',
    homepage_url: 'https://example.com/squad-2',
    publisher: { name: 'Stanford', type: 'academic' },
    modalities: ['nlp'],
    tasks: ['question-answering'],
    tags: ['benchmark'],
    license: { status: 'public_domain', name: 'Public Domain' },
    source_references: [{ title: 'Home', url: 'https://example.com', type: 'official_website' }],
    verification: { status: 'verified' },
  },
  {
    schema_version: '1.0.0',
    id: 'librispeech',
    slug: 'librispeech',
    name: 'LibriSpeech',
    description: 'Audio speech corpus',
    homepage_url: 'https://example.com/librispeech',
    publisher: { name: 'OpenSLR', type: 'academic' },
    modalities: ['audio'],
    tasks: ['speech-recognition'],
    tags: ['benchmark'],
    license: { status: 'public_domain', name: 'Public Domain' },
    source_references: [{ title: 'Home', url: 'https://example.com', type: 'official_website' }],
    verification: { status: 'verified' },
  },
  {
    schema_version: '1.0.0',
    id: 'adult-census',
    slug: 'adult-census',
    name: 'Adult Census',
    description: 'Tabular dataset',
    homepage_url: 'https://example.com/adult',
    publisher: { name: 'UCI', type: 'academic' },
    modalities: ['tabular'],
    tasks: ['classification'],
    tags: ['benchmark'],
    license: { status: 'public_domain', name: 'Public Domain' },
    source_references: [{ title: 'Home', url: 'https://example.com', type: 'official_website' }],
    verification: { status: 'verified' },
  },
  {
    schema_version: '1.0.0',
    id: 'coco-multimodal',
    slug: 'coco-multimodal',
    name: 'MS COCO',
    description: 'Multimodal vision language dataset',
    homepage_url: 'https://example.com/coco',
    publisher: { name: 'COCO', type: 'academic' },
    modalities: ['multimodal'],
    tasks: ['captioning'],
    tags: ['benchmark'],
    license: { status: 'public_domain', name: 'Public Domain' },
    source_references: [{ title: 'Home', url: 'https://example.com', type: 'official_website' }],
    verification: { status: 'verified' },
  },
]

describe('DatasetsPage Dataset Card Compare Action and Bookmarks', () => {
  let mockStorage: Record<string, string> = {}
  let mockLocalStorage: Record<string, string> = {}
  const originalSessionStorage = globalThis.sessionStorage
  const originalLocalStorage = globalThis.localStorage
  const originalWindow = globalThis.window

  beforeEach(() => {
    vi.restoreAllMocks()
    vi.spyOn(catalogService, 'fetchCatalog').mockResolvedValue(mockCatalog)
    mockStorage = {}
    mockLocalStorage = {}
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

    const fakeLocalStorage = {
      getItem: vi.fn((key: string) => mockLocalStorage[key] ?? null),
      setItem: vi.fn((key: string, val: string) => {
        mockLocalStorage[key] = val
      }),
      removeItem: vi.fn((key: string) => {
        delete mockLocalStorage[key]
      }),
      clear: vi.fn(() => {
        mockLocalStorage = {}
      }),
      length: 0,
      key: vi.fn(() => null),
    }

    const fakeWindow = {
      sessionStorage: fakeSessionStorage,
      localStorage: fakeLocalStorage,
      dispatchEvent: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      scrollTo: vi.fn(),
      scrollY: 0,
    }

    Object.defineProperty(globalThis, 'sessionStorage', {
      value: fakeSessionStorage,
      writable: true,
      configurable: true,
    })
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
    vi.restoreAllMocks()
    Object.defineProperty(globalThis, 'sessionStorage', {
      value: originalSessionStorage,
      writable: true,
      configurable: true,
    })
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
  })

  it('1. All Datasets page does not show any Compare action buttons or selection toolbar', () => {
    const html = renderToString(
      <MemoryRouter initialEntries={['/datasets']}>
        <Routes>
          <Route path="/datasets" element={<DatasetsPage initialCatalog={mockCatalog} />} />
        </Routes>
      </MemoryRouter>,
    )
    expect(html).not.toContain('Add CIFAR-10 to comparison')
    expect(html).not.toContain('<span>Compare</span>')
    expect(html).not.toContain('Exit Compare')
    expect(html).not.toContain('Compare Mode:')
    expect(html).not.toContain('type="checkbox"')
  })

  it('2. Each of the six category pages displays the Compare action on dataset cards and no header toggle', () => {
    for (const cat of CATEGORIES) {
      const html = renderToString(
        <MemoryRouter initialEntries={[`/datasets/${cat.id}`]}>
          <Routes>
            <Route path="/datasets/:param" element={<DatasetsPage initialCatalog={mockCatalog} />} />
          </Routes>
        </MemoryRouter>,
      )
      // Card footer contains Compare action button
      expect(html).toContain('<span>Compare</span>')
      // No checkboxes
      expect(html).not.toContain('type="checkbox"')
      // No category-header toggle button
      expect(html).not.toContain('Compare Datasets</button>')
      expect(html).not.toContain('Exit Compare</button>')
    }
  })

  it('3. displays comparison selection toolbar only when at least one dataset is selected', () => {
    // When 0 selected: toolbar is not rendered
    const htmlNone = renderToString(
      <MemoryRouter initialEntries={['/datasets/computer-vision']}>
        <Routes>
          <Route path="/datasets/:param" element={<DatasetsPage initialCatalog={mockCatalog} />} />
        </Routes>
      </MemoryRouter>,
    )
    expect(htmlNone).not.toContain('aria-label="Category dataset comparison toolbar"')

    // When mock storage has 1 selected
    sessionStorage.setItem('opendatasets_compare_selection', JSON.stringify(['cifar-10']))
    const htmlOne = renderToString(
      <MemoryRouter initialEntries={['/datasets/computer-vision']}>
        <Routes>
          <Route path="/datasets/:param" element={<DatasetsPage initialCatalog={mockCatalog} />} />
        </Routes>
      </MemoryRouter>,
    )
    expect(htmlOne).toContain('aria-label="Category dataset comparison toolbar"')
    expect(htmlOne).toContain('1 of 3 selected')
    expect(htmlOne).toContain('Clear selection')
    expect(htmlOne).toContain('Compare Selected')
    sessionStorage.clear()
  })

  it('4. enforces maximum selection limit of three datasets', () => {
    sessionStorage.setItem(
      'opendatasets_compare_selection',
      JSON.stringify(['cifar-10', 'squad-2', 'librispeech']),
    )
    const html = renderToString(
      <MemoryRouter initialEntries={['/datasets/computer-vision']}>
        <Routes>
          <Route path="/datasets/:param" element={<DatasetsPage initialCatalog={mockCatalog} />} />
        </Routes>
      </MemoryRouter>,
    )
    expect(html).toContain('3 of 3 selected')
    expect(html).toContain('Compare Selected (3)')
    expect(html).toContain('Selected</span>')
    sessionStorage.clear()
  })

  it('5. filters catalog to saved datasets only when ?saved=true parameter is present', () => {
    localStorage.setItem('opendatasets_saved_bookmarks', JSON.stringify(['cifar-10']))
    const html = renderToString(
      <MemoryRouter initialEntries={['/datasets?saved=true']}>
        <Routes>
          <Route path="/datasets" element={<DatasetsPage initialCatalog={mockCatalog} />} />
        </Routes>
      </MemoryRouter>,
    )
    expect(html).toContain('CIFAR-10')
    expect(html).not.toContain('SQuAD 2.0')
    expect(html).not.toContain('LibriSpeech')
    expect(html).toContain('Saved Datasets')
    expect(html).toContain('Showing')
    expect(html).toContain('class="font-bold text-slate-900 dark:text-white">1</span>')
    localStorage.clear()
  })

  it('6. displays specialized empty state when ?saved=true is active and no datasets are bookmarked', () => {
    const html = renderToString(
      <MemoryRouter initialEntries={['/datasets?saved=true']}>
        <Routes>
          <Route path="/datasets" element={<DatasetsPage initialCatalog={mockCatalog} />} />
        </Routes>
      </MemoryRouter>,
    )
    expect(html).toContain('No Saved Datasets')
    expect(html).toContain('Browse All Datasets')
    expect(html).toContain('You haven&#x27;t bookmarked any datasets yet')
  })

  it('7. renders bookmark button on all dataset cards with accurate saved states', () => {
    localStorage.setItem('opendatasets_saved_bookmarks', JSON.stringify(['cifar-10']))
    const html = renderToString(
      <MemoryRouter initialEntries={['/datasets']}>
        <Routes>
          <Route path="/datasets" element={<DatasetsPage initialCatalog={mockCatalog} />} />
        </Routes>
      </MemoryRouter>,
    )
    // Bookmarked dataset
    expect(html).toContain('aria-label="Remove CIFAR-10 from bookmarks"')
    expect(html).toContain('title="Saved to bookmarks"')
    // Unbookmarked dataset
    expect(html).toContain('aria-label="Bookmark SQuAD 2.0"')
    expect(html).toContain('title="Save dataset"')
    localStorage.clear()
  })

  it('8. renders Saved toggle button in filter bar with count badge', () => {
    localStorage.setItem('opendatasets_saved_bookmarks', JSON.stringify(['cifar-10', 'squad-2']))
    const html = renderToString(
      <MemoryRouter initialEntries={['/datasets']}>
        <Routes>
          <Route path="/datasets" element={<DatasetsPage initialCatalog={mockCatalog} />} />
        </Routes>
      </MemoryRouter>,
    )
    expect(html).toContain('Saved (2)')
    localStorage.clear()
  })

  it('9. renders Sort By dropdown with all sort options in catalog filter bar', () => {
    const html = renderToString(
      <MemoryRouter initialEntries={['/datasets']}>
        <Routes>
          <Route path="/datasets" element={<DatasetsPage initialCatalog={mockCatalog} />} />
        </Routes>
      </MemoryRouter>,
    )
    expect(html).toContain('aria-label="Sort datasets"')
    expect(html).toContain('Default Order')
    expect(html).toContain('Name (A–Z)')
    expect(html).toContain('Name (Z–A)')
    expect(html).toContain('Newest Publication')
    expect(html).toContain('Oldest Publication')
    expect(html).toContain('Largest Sample Count')
    expect(html).toContain('Smallest Sample Count')
  })

  it('10. renders active sort chip when ?sort= parameter is present and sorts cards', () => {
    const html = renderToString(
      <MemoryRouter initialEntries={['/datasets?sort=name-asc']}>
        <Routes>
          <Route path="/datasets" element={<DatasetsPage initialCatalog={mockCatalog} />} />
        </Routes>
      </MemoryRouter>,
    )
    expect(html).toContain('Sort: Name (A–Z)')
    expect(html).toContain('aria-label="Reset sort order"')

    // Verify ordering: Adult Census -> CIFAR-10 -> LibriSpeech -> MS COCO -> SQuAD 2.0
    const idxAdult = html.indexOf('Adult Census')
    const idxCifar = html.indexOf('CIFAR-10')
    const idxLibri = html.indexOf('LibriSpeech')
    const idxCoco = html.indexOf('MS COCO')
    const idxSquad = html.indexOf('SQuAD 2.0')

    expect(idxAdult).toBeLessThan(idxCifar)
    expect(idxCifar).toBeLessThan(idxLibri)
    expect(idxLibri).toBeLessThan(idxCoco)
    expect(idxCoco).toBeLessThan(idxSquad)
  })
})
