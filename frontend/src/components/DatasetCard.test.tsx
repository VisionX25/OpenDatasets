import { describe, it, expect } from 'vitest'
import { renderToString } from 'react-dom/server'
import { MemoryRouter } from 'react-router-dom'
import { DatasetCard } from './DatasetCard'
import { CategoryGrid } from './CategoryGrid'
import type { DatasetMetadata, CategoryId } from '../types/dataset'
import {
  CATEGORIES,
  CATEGORY_ACCENTS,
  getCategoryAccent,
} from '../utils/datasetFilters'

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

describe('Task 06.3.1: Category Hover Colors & Dataset Reveal Animations', () => {
  // 1. Category hover/focus styling in centralized configuration
  it('1. configures category-specific hover colors and focus tokens for all six categories', () => {
    for (const cat of CATEGORIES) {
      const accent = getCategoryAccent(cat.id)

      expect(accent.hoverCardBorder).toBeDefined()
      expect(accent.hoverCardBorder).toContain('hover:border-')
      expect(accent.hoverCardBorder).toContain('focus-visible:border-')

      expect(accent.hoverCardBg).toBeDefined()
      expect(accent.hoverCardBg).toContain('hover:bg-')
      expect(accent.hoverCardBg).toContain('dark:hover:bg-')

      expect(accent.hoverIconBg).toBeDefined()
      expect(accent.hoverIconBg).toContain('group-hover:bg-')
      expect(accent.hoverIconBg).toContain('group-focus-visible:bg-')
    }

    // Verify exact color tokens
    expect(CATEGORY_ACCENTS['computer-vision'].hoverCardBorder).toContain('blue-400')
    expect(CATEGORY_ACCENTS['natural-language-processing'].hoverCardBorder).toContain('violet-400')
    expect(CATEGORY_ACCENTS['audio-speech'].hoverCardBorder).toContain('amber-400')
    expect(CATEGORY_ACCENTS['tabular-time-series'].hoverCardBorder).toContain('emerald-400')
    expect(CATEGORY_ACCENTS['multimodal-generative'].hoverCardBorder).toContain('pink-400')
    expect(CATEGORY_ACCENTS['evaluation-benchmarks'].hoverCardBorder).toContain('cyan-400')
  })

  // 2. CategoryGrid rendering with hover transitions
  it('2. renders CategoryGrid with group class, 200ms transitions, and hover accent styles', () => {
    const counts: Record<CategoryId, number> = {
      'computer-vision': 4,
      'natural-language-processing': 3,
      'audio-speech': 2,
      'tabular-time-series': 2,
      'multimodal-generative': 1,
      'evaluation-benchmarks': 1,
    }

    const html = renderToString(
      <CategoryGrid
        activeCategory={null}
        onSelectCategory={() => {}}
        categoryCounts={counts}
      />,
    )

    // Contains group and 200ms transition duration (180-250ms requirement)
    expect(html).toContain('group')
    expect(html).toContain('duration-200')
    expect(html).toContain('motion-reduce:transition-none')

    // Contains hover classes
    expect(html).toContain('hover:border-blue-400')
    expect(html).toContain('hover:bg-blue-50/50')
    expect(html).toContain('group-hover:bg-blue-100')
  })

  // 3. Category selection maintains interactive dimmed cards
  it('3. maintains readable, interactive dimmed cards with hover feedback when a category is selected', () => {
    const counts: Record<CategoryId, number> = {
      'computer-vision': 4,
      'natural-language-processing': 3,
      'audio-speech': 2,
      'tabular-time-series': 2,
      'multimodal-generative': 1,
      'evaluation-benchmarks': 1,
    }

    const html = renderToString(
      <CategoryGrid
        activeCategory="computer-vision"
        onSelectCategory={() => {}}
        categoryCounts={counts}
      />,
    )

    // Active category card has selected styling
    expect(html).toContain('data-active="true"')
    expect(html).toContain('border-blue-500')

    // Dimmed cards retain 75% opacity and hover to 100%
    expect(html).toContain('opacity-75')
    expect(html).toContain('hover:opacity-100')
    expect(html).toContain('focus-visible:opacity-100')
  })

  // 4. DatasetCard scroll-reveal animation classes
  it('4. includes subtle scroll-reveal classes with 300ms duration and 10px upward movement', () => {
    const html = renderToString(
      <MemoryRouter>
        <DatasetCard dataset={mockDataset} />
      </MemoryRouter>,
    )

    // 300ms duration (within 250-350ms requirement)
    expect(html).toContain('duration-300')
    expect(html).toContain('ease-out')

    // Motion reduction styles
    expect(html).toContain('motion-reduce:transition-none')
    expect(html).toContain('motion-reduce:transform-none')
    expect(html).toContain('motion-reduce:opacity-100')

    // Hover elevation polish
    expect(html).toContain('hover:-translate-y-0.5')
    expect(html).toContain('hover:shadow-md')
  })

  // 5. No-IntersectionObserver fallback
  it('5. renders dataset cards immediately visible when IntersectionObserver is not available', () => {
    // In Node.js environment without DOM IntersectionObserver, fallback triggers immediately
    const html = renderToString(
      <MemoryRouter>
        <DatasetCard dataset={mockDataset} />
      </MemoryRouter>,
    )

    expect(html).toContain('data-revealed="true"')
    expect(html).toContain('opacity-100')
    expect(html).toContain('translate-y-0')
  })

  // 6. DatasetCard disabled animation
  it('6. renders immediately visible when animateOnScroll={false}', () => {
    const html = renderToString(
      <MemoryRouter>
        <DatasetCard dataset={mockDataset} animateOnScroll={false} />
      </MemoryRouter>,
    )

    expect(html).toContain('data-revealed="true"')
    expect(html).toContain('opacity-100')
    expect(html).toContain('translate-y-0')
  })

  // 7. DatasetCard handles invalid input gracefully
  it('7. renders null without crashing when dataset is invalid or missing required keys', () => {
    const emptyHtml = renderToString(
      <MemoryRouter>
        <DatasetCard dataset={null as unknown as DatasetMetadata} />
      </MemoryRouter>,
    )
    expect(emptyHtml).toBe('')

    const missingSlugHtml = renderToString(
      <MemoryRouter>
        <DatasetCard dataset={{ ...mockDataset, slug: '' }} />
      </MemoryRouter>,
    )
    expect(missingSlugHtml).toBe('')
  })
})
