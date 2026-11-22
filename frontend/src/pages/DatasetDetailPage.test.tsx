import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderToString } from 'react-dom/server'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { DatasetDetailPage } from './DatasetDetailPage'
import * as catalogService from '../services/catalogService'
import type { DatasetMetadata } from '../types/dataset'

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

describe('DatasetDetailPage (Task 21C Dataset ID Cleanup)', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    vi.spyOn(catalogService, 'getDatasetBySlug').mockResolvedValue(mockDataset)
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('1. renders initial loading state while resolving', () => {
    const html = renderToString(
      <MemoryRouter initialEntries={['/dataset/cifar-10']}>
        <Routes>
          <Route path="/dataset/:slug" element={<DatasetDetailPage />} />
        </Routes>
      </MemoryRouter>,
    )
    expect(html).toContain('Loading dataset details...')
  })

  it('2. does not render dataset id in prominent header block', () => {
    const html = renderToString(
      <MemoryRouter initialEntries={['/dataset/cifar-10']}>
        <Routes>
          <Route
            path="/dataset/:slug"
            element={<DatasetDetailPage initialDataset={mockDataset} />}
          />
        </Routes>
      </MemoryRouter>,
    )
    // The prominent header has modalities badges, but must not display 'id: cifar-10'
    expect(html).not.toContain('<span class="text-xs font-mono text-slate-400">id: cifar-10</span>')
    expect(html).not.toContain('id: cifar-10')
  })

  it('3. renders collapsible Technical Metadata section with ID, Slug, and copy controls', () => {
    const html = renderToString(
      <MemoryRouter initialEntries={['/dataset/cifar-10']}>
        <Routes>
          <Route
            path="/dataset/:slug"
            element={<DatasetDetailPage initialDataset={mockDataset} />}
          />
        </Routes>
      </MemoryRouter>,
    )
    // Disclosure element
    expect(html).toContain('<details')
    expect(html).toContain('Technical Metadata')

    // Contains labels and values
    expect(html).toContain('Dataset ID:')
    expect(html).toContain('cifar-10')
    expect(html).toContain('URL Slug:')

    // Accessible copy buttons
    expect(html).toContain('aria-label="Copy dataset ID"')
    expect(html).toContain('aria-label="Copy URL slug"')
    expect(html).toContain('Copy ID')
    expect(html).toContain('Copy Slug')
  })

  it('4. renders multi-format academic citation section with tabs and export controls', () => {
    const datasetWithCitation: DatasetMetadata = {
      ...mockDataset,
      citation: {
        bibtex: '@article{krizhevsky2009learning,\n  title={Learning Multiple Layers of Features from Tiny Images},\n  author={Krizhevsky, Alex}\n}',
        authors: ['Alex Krizhevsky'],
        paper_title: 'Learning Multiple Layers of Features from Tiny Images',
        doi: '10.1145/12345',
      },
    }

    const html = renderToString(
      <MemoryRouter initialEntries={['/dataset/cifar-10']}>
        <Routes>
          <Route
            path="/dataset/:slug"
            element={<DatasetDetailPage initialDataset={datasetWithCitation} />}
          />
        </Routes>
      </MemoryRouter>,
    )

    expect(html).toContain('Academic Citation')
    expect(html).toContain('BibTeX')
    expect(html).toContain('APA 7th')
    expect(html).toContain('IEEE')
    expect(html).toContain('Learning Multiple Layers of Features')
    expect(html).toContain('Copy Citation')
    expect(html).toContain('Download (.bib)')
  })

  it('5. renders limitation notice when citation metadata is absent', () => {
    const datasetWithoutCitation: DatasetMetadata = {
      ...mockDataset,
      citation: undefined,
    }

    const html = renderToString(
      <MemoryRouter initialEntries={['/dataset/cifar-10']}>
        <Routes>
          <Route
            path="/dataset/:slug"
            element={<DatasetDetailPage initialDataset={datasetWithoutCitation} />}
          />
        </Routes>
      </MemoryRouter>,
    )

    expect(html).toContain('Academic Citation')
    expect(html).toContain('BibTeX entry is not declared and sufficient author/title metadata is unavailable')
  })

  it('6. renders Research & Provenance Details section with scope, access, and audit timeline', () => {
    const datasetWithProvenance: DatasetMetadata = {
      ...mockDataset,
      geographic_coverage: ['Global', 'North America'],
      languages: ['en'],
      license: {
        status: 'verified_open',
        name: 'MIT License',
        commercial_use: 'allowed',
        notes: 'Permitted for research and commercial development.',
      },
      provenance: {
        collection_method: 'Extracted from 80 million tiny images database.',
        curation_notes: '10 classes independently verified by student annotators.',
        data_sources: ['80 Million Tiny Images Archive'],
      },
      dates: {
        published: '2009-04-08',
        last_updated: '2009-04-08',
      },
    }

    const html = renderToString(
      <MemoryRouter initialEntries={['/dataset/cifar-10']}>
        <Routes>
          <Route
            path="/dataset/:slug"
            element={<DatasetDetailPage initialDataset={datasetWithProvenance} />}
          />
        </Routes>
      </MemoryRouter>,
    )

    expect(html).toContain('Research &amp; Provenance Details')
    expect(html).toContain('Intended Use &amp; Domain Scope')
    expect(html).toContain('Global, North America')
    expect(html).toContain('Access Requirements &amp; Known Restrictions')
    expect(html).toContain('Permitted under declared terms')
    expect(html).toContain('Permitted for research and commercial development.')
    expect(html).toContain('Provenance &amp; Methodology')
    expect(html).toContain('Extracted from 80 million tiny images database.')
    expect(html).toContain('10 classes independently verified by student annotators.')
    expect(html).toContain('80 Million Tiny Images Archive')
    expect(html).toContain('Version &amp; Audit Timeline')
    expect(html).toContain('2009-04-08')
  })

  it('7. renders Related Datasets section with clear empty state when no related datasets exist', () => {
    const html = renderToString(
      <MemoryRouter initialEntries={['/dataset/cifar-10']}>
        <Routes>
          <Route
            path="/dataset/:slug"
            element={<DatasetDetailPage initialDataset={mockDataset} initialCatalog={[mockDataset]} />}
          />
        </Routes>
      </MemoryRouter>,
    )

    expect(html).toContain('Related Datasets')
    expect(html).toContain('No sufficiently related datasets found in the catalog at this time.')
  })

  it('8. renders up to 4 Related Datasets cards and excludes viewed dataset', () => {
    const mockCifar100: DatasetMetadata = {
      ...mockDataset,
      id: 'cifar-100',
      slug: 'cifar-100',
      name: 'CIFAR-100',
      description: '100 classes variant of CIFAR.',
    }
    const mockSvhn: DatasetMetadata = {
      ...mockDataset,
      id: 'svhn',
      slug: 'svhn',
      name: 'SVHN',
      description: 'Street View House Numbers.',
    }

    const html = renderToString(
      <MemoryRouter initialEntries={['/dataset/cifar-10']}>
        <Routes>
          <Route
            path="/dataset/:slug"
            element={
              <DatasetDetailPage
                initialDataset={mockDataset}
                initialCatalog={[mockDataset, mockCifar100, mockSvhn]}
              />
            }
          />
        </Routes>
      </MemoryRouter>,
    )

    expect(html).toContain('Related Datasets')
    expect(html).toContain('CIFAR-100')
    expect(html).toContain('SVHN')
    // Must not show empty state when cards are present
    expect(html).not.toContain('No sufficiently related datasets found in the catalog at this time.')
  })

  it('9. renders Dataset Splits under their own heading with unit', () => {
    const datasetWithSplits: DatasetMetadata = {
      ...mockDataset,
      sample_count: {
        total: 60000,
        unit: 'images',
        status: 'verified',
        splits: {
          train: 50000,
          test: 10000,
        },
      },
    }

    const html = renderToString(
      <MemoryRouter initialEntries={['/dataset/cifar-10']}>
        <Routes>
          <Route
            path="/dataset/:slug"
            element={<DatasetDetailPage initialDataset={datasetWithSplits} />}
          />
        </Routes>
      </MemoryRouter>,
    )

    expect(html).toContain('Dataset Splits')
    expect(html).toContain('train:')
    expect(html).toContain('50,000')
    expect(html).toContain('test:')
    expect(html).toContain('10,000')
    expect(html).toContain('images')
  })

  it('10. renders Quantitative Breakdown separately with labels, values and units', () => {
    const datasetWithBreakdown: DatasetMetadata = {
      ...mockDataset,
      sample_count: {
        total: 44,
        unit: 'sequences',
        status: 'verified',
      },
      breakdown: [
        {
          label: 'total driving distance',
          value: 350,
          unit: 'km',
        },
        {
          label: 'driving sequences',
          value: 44,
          unit: 'sequences',
        },
      ],
    }

    const html = renderToString(
      <MemoryRouter initialEntries={['/dataset/cifar-10']}>
        <Routes>
          <Route
            path="/dataset/:slug"
            element={<DatasetDetailPage initialDataset={datasetWithBreakdown} />}
          />
        </Routes>
      </MemoryRouter>,
    )

    expect(html).toContain('Quantitative Breakdown')
    expect(html).toContain('total driving distance')
    expect(html).toContain('350')
    expect(html).toContain('km')
    expect(html).toContain('driving sequences')
    expect(html).toContain('44')
    expect(html).toContain('sequences')
  })

  it('11. does not render missing sample count or breakdown information as zero', () => {
    const datasetWithMissingCount: DatasetMetadata = {
      ...mockDataset,
      sample_count: {
        status: 'unknown',
      },
    }

    const html = renderToString(
      <MemoryRouter initialEntries={['/dataset/cifar-10']}>
        <Routes>
          <Route
            path="/dataset/:slug"
            element={<DatasetDetailPage initialDataset={datasetWithMissingCount} />}
          />
        </Routes>
      </MemoryRouter>,
    )

    expect(html).toContain('Unspecified')
    // Must not display "0 items" or "0"
    expect(html).not.toContain('<p className="text-xl font-extrabold text-slate-900 dark:text-white">0')
  })

  it('12. renders both root-level and sample_count breakdown items without silently hiding data', () => {
    const datasetWithBothBreakdowns: DatasetMetadata = {
      ...mockDataset,
      sample_count: {
        total: 5000,
        unit: 'images',
        status: 'verified',
        breakdown: [
          {
            label: 'fine annotations',
            value: 5000,
            unit: 'images',
          },
        ],
      },
      breakdown: [
        {
          label: 'coarse annotations',
          value: 20000,
          unit: 'images',
        },
      ],
    }

    const html = renderToString(
      <MemoryRouter initialEntries={['/dataset/cifar-10']}>
        <Routes>
          <Route
            path="/dataset/:slug"
            element={<DatasetDetailPage initialDataset={datasetWithBothBreakdowns} />}
          />
        </Routes>
      </MemoryRouter>,
    )

    expect(html).toContain('Quantitative Breakdown')
    expect(html).toContain('fine annotations')
    expect(html).toContain('5,000')
    expect(html).toContain('coarse annotations')
    expect(html).toContain('20,000')
  })
})
