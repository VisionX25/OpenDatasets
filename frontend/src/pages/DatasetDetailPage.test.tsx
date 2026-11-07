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
})
