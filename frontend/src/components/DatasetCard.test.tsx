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

  // 8. Task 21C: DatasetCard compare action button (no checkboxes)
  it('8. renders accessible comparison button and responds to selection state', () => {
    // When onToggleSelect is provided
    const htmlUnselected = renderToString(
      <MemoryRouter>
        <DatasetCard
          dataset={mockDataset}
          isSelected={false}
          onToggleSelect={() => {}}
        />
      </MemoryRouter>,
    )
    expect(htmlUnselected).toContain('aria-label="Add CIFAR-10 to comparison"')
    expect(htmlUnselected).toContain('Compare</span>')
    expect(htmlUnselected).not.toContain('type="checkbox"')
    expect(htmlUnselected).toContain('aria-pressed="false"')

    // When isSelected is true
    const htmlSelected = renderToString(
      <MemoryRouter>
        <DatasetCard
          dataset={mockDataset}
          isSelected={true}
          onToggleSelect={() => {}}
        />
      </MemoryRouter>,
    )
    expect(htmlSelected).toContain('aria-label="Remove CIFAR-10 from comparison"')
    expect(htmlSelected).toContain('aria-pressed="true"')
    expect(htmlSelected).toContain('Selected</span>')
    expect(htmlSelected).toContain('ring-2 ring-indigo-500/30')
    expect(htmlSelected).not.toContain('type="checkbox"')

    // When selection is disabled because max compare count reached
    const htmlDisabled = renderToString(
      <MemoryRouter>
        <DatasetCard
          dataset={mockDataset}
          isSelected={false}
          isSelectionDisabled={true}
          onToggleSelect={() => {}}
        />
      </MemoryRouter>,
    )
    expect(htmlDisabled).toContain('disabled=""')
    expect(htmlDisabled).toContain('Maximum of 3 datasets can be compared')
  })

  // 9. Task 21C: Dataset ID removed and Compare hidden when inactive
  it('9. does not render technical dataset id and hides comparison control when inactive', () => {
    const html = renderToString(
      <MemoryRouter>
        <DatasetCard dataset={mockDataset} />
      </MemoryRouter>,
    )
    // Dataset ID must not be visible on the card
    expect(html).not.toContain('id: cifar-10')
    expect(html).not.toContain('id: ')

    // Compare button must not be rendered when onToggleSelect is omitted
    expect(html).not.toContain('Add CIFAR-10 to comparison')
    expect(html).not.toContain('Compare</span>')
    expect(html).not.toContain('type="checkbox"')

    // View Details link remains present
    expect(html).toContain('View Details')
  })

  // 10. Bookmark button accessibility and visual states
  it('10. renders bookmark button with appropriate outline/fill styling and accessible labels', () => {
    // Unbookmarked state
    const htmlUnbookmarked = renderToString(
      <MemoryRouter>
        <DatasetCard dataset={mockDataset} isBookmarked={false} onToggleBookmark={() => {}} />
      </MemoryRouter>,
    )
    expect(htmlUnbookmarked).toContain('aria-label="Bookmark CIFAR-10"')
    expect(htmlUnbookmarked).toContain('aria-pressed="false"')
    expect(htmlUnbookmarked).toContain('title="Save dataset"')
    expect(htmlUnbookmarked).not.toContain('fill-amber-500')

    // Bookmarked state
    const htmlBookmarked = renderToString(
      <MemoryRouter>
        <DatasetCard dataset={mockDataset} isBookmarked={true} onToggleBookmark={() => {}} />
      </MemoryRouter>,
    )
    expect(htmlBookmarked).toContain('aria-label="Remove CIFAR-10 from bookmarks"')
    expect(htmlBookmarked).toContain('aria-pressed="true"')
    expect(htmlBookmarked).toContain('title="Saved to bookmarks"')
    expect(htmlBookmarked).toContain('fill-amber-500')
    expect(htmlBookmarked).toContain('text-amber-500')
  })

  // 11. Compare button displays GitCompareArrows when unselected and Check when selected
  it('11. renders GitCompareArrows icon when unselected and Check icon when selected', () => {
    const htmlUnselected = renderToString(
      <MemoryRouter>
        <DatasetCard dataset={mockDataset} isSelected={false} onToggleSelect={() => {}} />
      </MemoryRouter>,
    )
    expect(htmlUnselected).toContain('lucide-git-compare-arrows')
    expect(htmlUnselected).not.toContain('lucide-check')

    const htmlSelected = renderToString(
      <MemoryRouter>
        <DatasetCard dataset={mockDataset} isSelected={true} onToggleSelect={() => {}} />
      </MemoryRouter>,
    )
    expect(htmlSelected).toContain('lucide-check')
    expect(htmlSelected).not.toContain('lucide-git-compare-arrows')
  })

  // 12. Task 21E: Fixed bookmark position and visual hierarchy under extreme content conditions
  it('12. maintains fixed top-right bookmark positioning and content spacing for long titles, descriptions, and multiple badges', () => {
    const complexDataset: DatasetMetadata = {
      ...mockDataset,
      name: 'Extremely Long Dataset Title For Benchmarking Complex Multi-Modal Reasoning Across Multiple Modalities and Tasks Under Distribution Shift',
      description:
        'This is an exceptionally long dataset description designed to simulate datasets with verbose documentation, extensive corpus explanations, benchmark evaluation splits, detailed annotation methodologies, preprocessing pipelines, and licensing caveats across hundreds of words to verify line-clamping and vertical layout stability.',
      modalities: ['vision', 'nlp', 'audio', 'multimodal'],
      tasks: ['image-classification', 'question-answering', 'speech-recognition', 'object-detection'],
      tags: ['benchmark', 'computer-vision', 'nlp', 'multimodal', 'speech'],
    }

    const html = renderToString(
      <MemoryRouter>
        <DatasetCard
          dataset={complexDataset}
          isBookmarked={true}
          onToggleBookmark={() => {}}
          isSelected={true}
          onToggleSelect={() => {}}
        />
      </MemoryRouter>,
    )

    // Card has relative container and fixed corner bookmark button
    expect(html).toContain('group relative')
    expect(html).toContain('absolute top-3 right-3')
    expect(html).toContain('w-8 h-8 rounded-lg')

    // Top badges container reserves right-side padding to prevent overlap with bookmark button
    expect(html).toContain('pr-10')

    // Long description retains line-clamp
    expect(html).toContain('line-clamp-3')

    // Footer maintains subtle selected compare state and view details link
    expect(html).toContain('Selected</span>')
    expect(html).toContain('View Details</span>')
    expect(html).toContain('mt-auto min-h-[42px]')
  })

  // 13. Task 21F: Minimal, non-boxy action styling for Bookmark and Compare
  it('13. renders Bookmark and Compare actions without visible rectangular boxes, borders, or filled button containers', () => {
    const htmlUnselected = renderToString(
      <MemoryRouter>
        <DatasetCard
          dataset={mockDataset}
          isBookmarked={false}
          onToggleBookmark={() => {}}
          isSelected={false}
          onToggleSelect={() => {}}
        />
      </MemoryRouter>,
    )

    // Bookmark button: icon-only, no visible box/border classes
    const bookmarkStart = htmlUnselected.indexOf('aria-label="Bookmark CIFAR-10"')
    const bookmarkEnd = htmlUnselected.indexOf('</button>', bookmarkStart)
    const bookmarkHtml = htmlUnselected.slice(bookmarkStart, bookmarkEnd)
    expect(bookmarkHtml).not.toContain('border')
    expect(bookmarkHtml).not.toContain('bg-white')
    expect(bookmarkHtml).not.toContain('bg-amber')

    // Compare action: matching typography and sizing of View Details without rectangular border/background
    const compareStart = htmlUnselected.indexOf('aria-label="Add CIFAR-10 to comparison"')
    const compareEnd = htmlUnselected.indexOf('</button>', compareStart)
    const compareHtml = htmlUnselected.slice(compareStart, compareEnd)
    expect(compareHtml).toContain('font-semibold text-xs')
    expect(compareHtml).not.toContain('border')
    expect(compareHtml).not.toContain('bg-indigo')
    expect(compareHtml).not.toContain('bg-slate')
    expect(compareHtml).toContain('Compare</span>')

    const htmlSelected = renderToString(
      <MemoryRouter>
        <DatasetCard
          dataset={mockDataset}
          isBookmarked={true}
          onToggleBookmark={() => {}}
          isSelected={true}
          onToggleSelect={() => {}}
        />
      </MemoryRouter>,
    )

    // Selected compare action: clean text + icon, no filled button container
    const selectedCompareStart = htmlSelected.indexOf('aria-label="Remove CIFAR-10 from comparison"')
    const selectedCompareEnd = htmlSelected.indexOf('</button>', selectedCompareStart)
    const selectedCompareHtml = htmlSelected.slice(selectedCompareStart, selectedCompareEnd)
    expect(selectedCompareHtml).toContain('Selected</span>')
    expect(selectedCompareHtml).not.toContain('border')
    expect(selectedCompareHtml).not.toContain('bg-indigo')

    // Disabled state
    const htmlDisabled = renderToString(
      <MemoryRouter>
        <DatasetCard
          dataset={mockDataset}
          isSelected={false}
          isSelectionDisabled={true}
          onToggleSelect={() => {}}
        />
      </MemoryRouter>,
    )
    expect(htmlDisabled).toContain('cursor-not-allowed')
    expect(htmlDisabled).toContain('opacity-50')
  })
})
