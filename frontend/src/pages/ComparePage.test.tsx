import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderToString } from 'react-dom/server'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { ComparePage } from './ComparePage'
import type { DatasetMetadata } from '../types/dataset'
import * as catalogService from '../services/catalogService'

const mockDatasetA: DatasetMetadata = {
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
  sample_count: {
    total: 60000,
    unit: 'images',
    status: 'verified',
    splits: {
      train: 50000,
      test: 10000,
    },
  },
  size: {
    amount: 163,
    unit: 'MB',
    file_formats: ['bin', 'python-pickle'],
    status: 'verified',
  },
  license: {
    status: 'custom_permissive',
    name: 'MIT License',
    spdx_id: 'MIT',
    commercial_use: 'allowed',
    notes: 'Free for academic and commercial use with attribution.',
    url: 'https://example.com/license',
  },
  citation: {
    paper_title: 'Learning Multiple Layers of Features from Tiny Images',
    doi: '10.1.1.222.9220',
    paper_url: 'https://example.com/paper.pdf',
  },
  dates: {
    published: '2009-04-08',
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
    verified_by: 'OpenDatasets Reviewer',
    verified_date: '2026-01-15',
  },
}

const mockDatasetB: DatasetMetadata = {
  schema_version: '1.0.0',
  id: 'mnist',
  slug: 'mnist',
  name: 'MNIST',
  description: '70,000 handwritten digits.',
  homepage_url: 'https://yann.lecun.com/exdb/mnist/',
  publisher: {
    name: 'Yann LeCun and Corinna Cortes',
    type: 'academic',
  },
  modalities: ['vision'],
  tasks: ['digit-recognition'],
  tags: ['handwritten-digits'],
  sample_count: {
    total: 70000,
    unit: 'images',
    status: 'estimated',
    // No splits declared
  },
  size: {
    amount: 12,
    unit: 'MB',
    status: 'estimated',
  },
  license: {
    status: 'unspecified_by_source',
    name: 'Unspecified',
    commercial_use: 'unknown',
  },
  dates: {
    published: '1998-11-01',
  },
  source_references: [
    {
      title: 'Official Page',
      url: 'https://yann.lecun.com/exdb/mnist/',
      type: 'official_website',
    },
  ],
  verification: {
    status: 'provisional',
  },
}

const mockDatasetC: DatasetMetadata = {
  schema_version: '1.0.0',
  id: 'imagenet-1k',
  slug: 'imagenet-1k',
  name: 'ImageNet-1K',
  description: '1.28M labeled images across 1,000 object categories.',
  homepage_url: 'https://www.image-net.org/',
  publisher: {
    name: 'Stanford Vision Lab',
    type: 'academic',
  },
  modalities: ['vision'],
  tasks: ['image-classification'],
  tags: ['large-scale-vision'],
  sample_count: {
    total: 1281167,
    unit: 'images',
    status: 'verified',
    splits: {
      train: 1281167,
      val: 50000,
    },
  },
  size: {
    amount: 150,
    unit: 'GB',
    status: 'verified',
  },
  license: {
    status: 'custom_permissive',
    name: 'Custom Research License',
    commercial_use: 'forbidden',
    notes: 'Non-commercial research and educational use only.',
  },
  dates: {
    published: '2009-06-20',
  },
  source_references: [
    {
      title: 'Homepage',
      url: 'https://www.image-net.org/',
      type: 'official_website',
    },
  ],
  verification: {
    status: 'verified',
  },
}

const mockCatalog: DatasetMetadata[] = [mockDatasetA, mockDatasetB, mockDatasetC]

describe('ComparePage component', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    vi.spyOn(catalogService, 'fetchCatalog').mockResolvedValue(mockCatalog)
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('1. renders initial loading state when catalog is pending', () => {
    vi.spyOn(catalogService, 'fetchCatalog').mockReturnValue(new Promise(() => {}))
    const html = renderToString(
      <MemoryRouter initialEntries={['/compare']}>
        <Routes>
          <Route path="/compare" element={<ComparePage />} />
        </Routes>
      </MemoryRouter>,
    )
    expect(html).toContain('Loading comparison data...')
  })

  it('2. renders empty state when no datasets are selected', () => {
    const html = renderToString(
      <MemoryRouter initialEntries={['/compare']}>
        <Routes>
          <Route path="/compare" element={<ComparePage initialCatalog={mockCatalog} />} />
        </Routes>
      </MemoryRouter>,
    )
    expect(html).toContain('Select at Least 2 Datasets')
    expect(html).toContain('Browse Dataset Catalog')
  })

  it('3. renders informative state when exactly 1 dataset is selected', () => {
    const html = renderToString(
      <MemoryRouter initialEntries={['/compare?datasets=cifar-10']}>
        <Routes>
          <Route path="/compare" element={<ComparePage initialCatalog={mockCatalog} />} />
        </Routes>
      </MemoryRouter>,
    )
    expect(html).toContain('Select Another Dataset to Compare')
    expect(html).toContain('Selected:')
    expect(html).toContain('CIFAR-10')
  })

  it('4. renders side-by-side comparison matrix for 2 datasets', () => {
    const html = renderToString(
      <MemoryRouter initialEntries={['/compare?datasets=cifar-10,mnist']}>
        <Routes>
          <Route path="/compare" element={<ComparePage initialCatalog={mockCatalog} />} />
        </Routes>
      </MemoryRouter>,
    )

    // Table Header contains both dataset titles
    expect(html).toContain('CIFAR-10')
    expect(html).toContain('MNIST')
    expect(html).toContain('href="/dataset/cifar-10"')
    expect(html).toContain('href="/dataset/mnist"')

    // Attributes column header
    expect(html).toContain('Attributes')
    expect(html).toContain('General Information &amp; Scope')

    // Scale attributes
    expect(html).toContain('60,000')
    expect(html).toContain('70,000')
    expect(html).toContain('(estimated)')

    // Splits breakdown
    expect(html).toContain('train')
    expect(html).toContain('50,000')
    expect(html).toContain('Not documented in catalog')

    // Licensing & Commercial permissions
    expect(html).toContain('MIT License')
    expect(html).toContain('Allowed')
    expect(html).toContain('Unknown (Review source terms)')
    expect(html).toContain('SPDX: MIT')

    // Academic Citations
    expect(html).toContain('Learning Multiple Layers of Features from Tiny Images')
    expect(html).toContain('10.1.1.222.9220')
  })

  it('5. renders commercial forbidden badge accurately', () => {
    const html = renderToString(
      <MemoryRouter initialEntries={['/compare?datasets=cifar-10,imagenet-1k']}>
        <Routes>
          <Route path="/compare" element={<ComparePage initialCatalog={mockCatalog} />} />
        </Routes>
      </MemoryRouter>,
    )
    expect(html).toContain('Allowed')
    expect(html).toContain('Forbidden')
    expect(html).toContain('ImageNet-1K')
  })

  it('6. renders warning alert when query contains unknown dataset slug', () => {
    const html = renderToString(
      <MemoryRouter initialEntries={['/compare?datasets=cifar-10,nonexistent-slug']}>
        <Routes>
          <Route path="/compare" element={<ComparePage initialCatalog={mockCatalog} />} />
        </Routes>
      </MemoryRouter>,
    )
    expect(html).toContain('Dataset not found')
    expect(html).toContain('nonexistent-slug')
  })

  it('7. renders action buttons: Share Comparison, Clear, Back to Datasets', () => {
    const html = renderToString(
      <MemoryRouter initialEntries={['/compare?datasets=cifar-10,mnist']}>
        <Routes>
          <Route path="/compare" element={<ComparePage initialCatalog={mockCatalog} />} />
        </Routes>
      </MemoryRouter>,
    )
    expect(html).toContain('Share Comparison')
    expect(html).toContain('Clear')
    expect(html).toContain('Back to Datasets')
  })

  it('8. provides accessible remove buttons for each dataset column', () => {
    const html = renderToString(
      <MemoryRouter initialEntries={['/compare?datasets=cifar-10,mnist']}>
        <Routes>
          <Route path="/compare" element={<ComparePage initialCatalog={mockCatalog} />} />
        </Routes>
      </MemoryRouter>,
    )
    expect(html).toContain('aria-label="Remove CIFAR-10 from comparison"')
    expect(html).toContain('aria-label="Remove MNIST from comparison"')
  })
})
