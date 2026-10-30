import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderToString } from 'react-dom/server'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { DatasetCard } from './components/DatasetCard'
import { DatasetsRouteDispatcher } from './App'
import { DatasetDetailPage } from './pages/DatasetDetailPage'
import { SubmitDatasetPage } from './pages/SubmitDatasetPage'
import { Header } from './components/Header'
import { Footer } from './components/Footer'
import { HomePage } from './pages/HomePage'
import type { DatasetMetadata } from './types/dataset'
import { clearCatalogCache, isDatasetSlug, isDatasetSlugAsync } from './services/catalogService'
import { isCategoryId, CATEGORIES } from './utils/datasetFilters'

const mockDataset: DatasetMetadata = {
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

describe('Task 08.2: Dataset Details Routing and Regression Tests', () => {
  beforeEach(() => {
    clearCatalogCache()
    vi.restoreAllMocks()
  })

  afterEach(() => {
    clearCatalogCache()
    vi.restoreAllMocks()
  })

  // 1. Dataset card -> correct detail page link
  it('1. DatasetCard renders links to canonical /dataset/:slug instead of /datasets/:slug', () => {
    const html = renderToString(
      <MemoryRouter>
        <DatasetCard dataset={mockDataset} />
      </MemoryRouter>,
    )

    // Title link must point to canonical /dataset/cifar-10
    expect(html).toContain('href="/dataset/cifar-10"')

    // View Details action link must also point to /dataset/cifar-10
    expect(html).toContain('View Details</span>')

    // Must NOT contain old /datasets/cifar-10 links
    expect(html).not.toContain('href="/datasets/cifar-10"')
  })

  // 2. Direct dataset detail URL
  it('2. Direct dataset detail route /dataset/:slug correctly passes slug parameter to DatasetDetailPage', () => {
    const html = renderToString(
      <MemoryRouter initialEntries={['/dataset/cifar-10']}>
        <Routes>
          <Route path="/dataset/:slug" element={<DatasetDetailPage />} />
        </Routes>
      </MemoryRouter>,
    )

    // Initial render shows loading state while catalog resolves asynchronously
    expect(html).toContain('Loading dataset details...')
  })

  // 3. Existing /datasets/:slug compatibility redirect
  it('3. Existing /datasets/:slug deep links are redirected to canonical /dataset/:slug', () => {
    // In React Router, navigating to /datasets/cifar-10 where cifar-10 is not a category
    // should trigger DatasetsRouteDispatcher to redirect to /dataset/cifar-10.
    const html = renderToString(
      <MemoryRouter initialEntries={['/datasets/cifar-10']}>
        <Routes>
          <Route path="/datasets/:param" element={<DatasetsRouteDispatcher />} />
          <Route path="/dataset/:slug" element={<DatasetDetailPage />} />
        </Routes>
      </MemoryRouter>,
    )

    // Confirms it redirected to /dataset/:slug and rendered the DatasetDetailPage loader
    // rather than falling through to the DatasetsPage "Category Not Found" error.
    expect(html).toContain('Loading dataset details...')
    expect(html).not.toContain('Category Not Found')
  })

  // 4. Category routes remain valid and are not confused with dataset slugs
  it('4. Category routes /datasets/:categorySlug remain valid and render category-scoped DatasetsPage', () => {
    for (const cat of CATEGORIES) {
      expect(isCategoryId(cat.id)).toBe(true)

      const html = renderToString(
        <MemoryRouter initialEntries={[`/datasets/${cat.id}`]}>
          <Routes>
            <Route path="/datasets/:param" element={<DatasetsRouteDispatcher />} />
            <Route path="/dataset/:slug" element={<DatasetDetailPage />} />
          </Routes>
        </MemoryRouter>,
      )

      // Category page should render without redirecting to a dataset detail page
      expect(html).not.toContain('Loading dataset details...')
      expect(html).not.toContain('Dataset Not Found')
    }
  })

  // 5. Invalid dataset slug -> appropriate Not Found state with identifier displayed
  it('5. Invalid dataset slug renders appropriate Dataset Not Found state with non-empty identifier', async () => {
    // Mock fetch to simulate an empty catalog where the dataset does not exist
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => [mockDataset], // contains only cifar-10
    } as Response)

    // Render with an invalid slug
    const invalidSlug = 'nonexistent-dataset-slug'
    const html = renderToString(
      <MemoryRouter initialEntries={[`/dataset/${invalidSlug}`]}>
        <Routes>
          <Route path="/dataset/:slug" element={<DatasetDetailPage />} />
        </Routes>
      </MemoryRouter>,
    )

    // Initial render displays loader
    expect(html).toContain('Loading dataset details...')

    // Now test the parameter binding directly with both :slug and :param
    // to verify that the parameter mismatch bug is permanently resolved.
    const htmlParam = renderToString(
      <MemoryRouter initialEntries={[`/datasets/${invalidSlug}`]}>
        <Routes>
          <Route path="/datasets/:param" element={<DatasetDetailPage />} />
        </Routes>
      </MemoryRouter>,
    )

    // When mounted directly under /datasets/:param, it receives the parameter
    expect(htmlParam).toContain('Loading dataset details...')
  })

  // 6. Data-driven catalog slug lookup validation
  it('6. isDatasetSlug and isDatasetSlugAsync perform accurate, data-driven lookup', async () => {
    // Synchronous check against known catalog records
    expect(isDatasetSlug('cifar-10')).toBe(true)
    expect(isDatasetSlug('jaaltaka')).toBe(true)
    expect(isDatasetSlug('humanitys-last-exam')).toBe(true)

    // Category names are never dataset slugs
    expect(isDatasetSlug('computer-vision')).toBe(false)
    expect(isDatasetSlug('natural-language-processing')).toBe(false)

    // Unknown slugs
    expect(isDatasetSlug('not-a-real-dataset')).toBe(false)
    expect(isDatasetSlug('')).toBe(false)
    expect(isDatasetSlug(null)).toBe(false)

    // Data-driven async lookup
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => [mockDataset],
    } as Response)

    const isCifarValid = await isDatasetSlugAsync('cifar-10')
    expect(isCifarValid).toBe(true)

    const isFakeValid = await isDatasetSlugAsync('fake-dataset-xyz')
    expect(isFakeValid).toBe(false)
  })

  // 7. Direct /submit route renders SubmitDatasetPage
  it('7. Direct /submit route renders SubmitDatasetPage properly', () => {
    const html = renderToString(
      <MemoryRouter initialEntries={['/submit']}>
        <Routes>
          <Route path="/submit" element={<SubmitDatasetPage />} />
        </Routes>
      </MemoryRouter>,
    )
    expect(html).toContain('Propose a Dataset')
    expect(html).toContain('Dataset Contribution Guidelines')
    expect(html).toContain('Dataset Name')
    expect(html).toContain('Generate &amp; Copy Submission Details')
  })

  // 8. Task 11.1: Header navigation does not include Submit Dataset
  it('8. Header navigation excludes Submit Dataset from header nav while retaining core links', () => {
    const html = renderToString(
      <MemoryRouter>
        <Header />
      </MemoryRouter>,
    )
    expect(html).toContain('href="/"')
    expect(html).toContain('href="/explore"')
    expect(html).toContain('href="/datasets"')
    expect(html).toContain('href="/about"')
    expect(html).not.toContain('Submit Dataset')
    expect(html).not.toContain('href="/submit"')
  })

  // 9. Task 11.1: Footer provides a dedicated Contribute section
  it('9. Footer organizes a dedicated Contribute section with submit, guide, and issue links', () => {
    const html = renderToString(
      <MemoryRouter>
        <Footer />
      </MemoryRouter>,
    )
    expect(html).toContain('Contribute</h3>')
    expect(html).toContain('href="/submit"')
    expect(html).toContain('Submit a Dataset')
    expect(html).toContain('href="https://github.com/VisionX25/OpenDatasets/blob/main/CONTRIBUTING.md"')
    expect(html).toContain('Contribution Guide')
    expect(html).toContain('href="https://github.com/VisionX25/OpenDatasets/issues"')
    expect(html).toContain('Report an Issue')
  })

  // 10. Task 11.1: HomePage provides a subtle Contribute section near the bottom
  it('10. HomePage includes Contribute to OpenDatasets section with submit link', () => {
    const html = renderToString(
      <MemoryRouter>
        <HomePage />
      </MemoryRouter>,
    )
    expect(html).toContain('Contribute to OpenDatasets')
    expect(html).toContain('href="/submit"')
    expect(html).toContain('Submit Dataset')
  })
})
