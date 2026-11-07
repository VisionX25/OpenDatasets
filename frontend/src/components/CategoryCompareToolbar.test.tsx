import { describe, it, expect } from 'vitest'
import { renderToString } from 'react-dom/server'
import { MemoryRouter } from 'react-router-dom'
import { CategoryCompareToolbar } from './CategoryCompareToolbar'
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
    id: 'mnist',
    slug: 'mnist',
    name: 'MNIST',
    description: 'Digit dataset',
    homepage_url: 'https://example.com/mnist',
    publisher: { name: 'NYU', type: 'academic' },
    modalities: ['vision'],
    tasks: ['image-classification'],
    tags: ['benchmark'],
    license: { status: 'custom_permissive', name: 'Custom' },
    source_references: [{ title: 'Home', url: 'https://example.com', type: 'official_website' }],
    verification: { status: 'verified' },
  },
]

describe('CategoryCompareToolbar component', () => {
  it('1. renders toolbar with 0 items selected and instructions', () => {
    const html = renderToString(
      <MemoryRouter>
        <CategoryCompareToolbar
          selectedSlugs={[]}
          catalog={mockCatalog}
          onRemoveSlug={() => {}}
          onClear={() => {}}
        />
      </MemoryRouter>,
    )
    expect(html).toContain('Compare Mode:')
    expect(html).toContain('0 of 3 selected')
    expect(html).toContain('Select 2 or 3 datasets below to compare')
    expect(html).toContain('Clear selection')
    expect(html).toContain('Compare Selected')
    expect(html).not.toContain('Exit Compare')
    expect(html).not.toContain('href="/compare')
  })

  it('2. renders toolbar with 1 item, chips, and disabled compare button', () => {
    const html = renderToString(
      <MemoryRouter>
        <CategoryCompareToolbar
          selectedSlugs={['cifar-10']}
          catalog={mockCatalog}
          onRemoveSlug={() => {}}
          onClear={() => {}}
        />
      </MemoryRouter>,
    )
    expect(html).toContain('1 of 3 selected')
    expect(html).toContain('CIFAR-10')
    expect(html).toContain('Compare Selected')
    expect(html).toContain('Clear selection')
    expect(html).not.toContain('Exit Compare')
    expect(html).not.toContain('href="/compare')
  })

  it('3. renders toolbar with 2 items and enabled link to compare page', () => {
    const html = renderToString(
      <MemoryRouter>
        <CategoryCompareToolbar
          selectedSlugs={['cifar-10', 'mnist']}
          catalog={mockCatalog}
          onRemoveSlug={() => {}}
          onClear={() => {}}
        />
      </MemoryRouter>,
    )
    expect(html).toContain('2 of 3 selected')
    expect(html).toContain('CIFAR-10')
    expect(html).toContain('MNIST')
    expect(html).toContain('Compare Selected (2)')
    expect(html).toContain('href="/compare?datasets=cifar-10,mnist"')
  })

  it('4. falls back to slug when dataset is not found in catalog', () => {
    const html = renderToString(
      <MemoryRouter>
        <CategoryCompareToolbar
          selectedSlugs={['unknown-slug']}
          catalog={mockCatalog}
          onRemoveSlug={() => {}}
          onClear={() => {}}
        />
      </MemoryRouter>,
    )
    expect(html).toContain('unknown-slug')
  })

  it('5. optionally renders Exit Compare button when onExit callback is provided', () => {
    const html = renderToString(
      <MemoryRouter>
        <CategoryCompareToolbar
          selectedSlugs={['cifar-10']}
          catalog={mockCatalog}
          onRemoveSlug={() => {}}
          onClear={() => {}}
          onExit={() => {}}
        />
      </MemoryRouter>,
    )
    expect(html).toContain('Exit Compare')
  })
})
