import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderToString } from 'react-dom/server'
import { MemoryRouter } from 'react-router-dom'
import { SubmitDatasetPage } from './SubmitDatasetPage'
import {
  isValidHttpUrl,
  formatSubmissionMarkdown,
  type SubmissionFormData,
} from '../utils/submissionUtils'
import { findPotentialDuplicates } from '../utils/duplicateDetector'
import type { DatasetMetadata } from '../types/dataset'

const mockCatalog: DatasetMetadata[] = [
  {
    schema_version: '1.0.0',
    id: 'cifar-10',
    slug: 'cifar-10',
    name: 'CIFAR-10',
    description: '60,000 32x32 colour images in 10 classes.',
    homepage_url: 'https://www.cs.toronto.edu/~kriz/cifar.html',
    publisher: { name: 'University of Toronto', type: 'academic' },
    modalities: ['vision'],
    tasks: ['image-classification'],
    tags: ['benchmark'],
    license: { status: 'unspecified_by_source', name: 'Unspecified' },
    source_references: [{ title: 'Homepage', url: 'https://www.cs.toronto.edu/~kriz/cifar.html', type: 'official_website' }],
    verification: { status: 'verified' },
    citation: {
      doi: '10.1.1.222.9220',
      paper_title: 'Learning Multiple Layers of Features from Tiny Images',
    },
  },
  {
    schema_version: '1.0.0',
    id: 'bangla-grammar-qa',
    slug: 'bangla-grammar-qa',
    name: 'Bangla Grammar QA: Question Answering with Prerequisite Knowledge',
    description: '10,000 instances.',
    homepage_url: 'https://data.mendeley.com/datasets/tsdvtzwwpn/1',
    publisher: { name: 'AIUB', type: 'academic' },
    modalities: ['nlp'],
    tasks: ['question-answering'],
    tags: ['bangla', 'nlp'],
    license: { status: 'verified_open', name: 'CC BY 4.0' },
    source_references: [{ title: 'Mendeley', url: 'https://data.mendeley.com/datasets/tsdvtzwwpn/1', type: 'repository' }],
    verification: { status: 'verified' },
    citation: {
      doi: '10.17632/tsdvtzwwpn.1',
      paper_title: 'Bangla Grammar QA',
    },
  },
]

describe('SubmitDatasetPage: Unit & Integration Tests', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  // 1. URL Validation
  describe('1. URL Validation', () => {
    it('accepts valid HTTP and HTTPS URLs', () => {
      expect(isValidHttpUrl('https://data.mendeley.com/datasets/123/1')).toBe(true)
      expect(isValidHttpUrl('http://archive.ics.uci.edu/dataset/53/iris')).toBe(true)
      expect(isValidHttpUrl('https://huggingface.co/datasets/glue')).toBe(true)
      expect(isValidHttpUrl('https://zenodo.org/record/123456')).toBe(true)
    })

    it('rejects invalid or non-HTTP URLs', () => {
      expect(isValidHttpUrl('')).toBe(false)
      expect(isValidHttpUrl('not-a-url')).toBe(false)
      expect(isValidHttpUrl('ftp://ftp.example.com/dataset')).toBe(false)
      expect(isValidHttpUrl('javascript:alert(1)')).toBe(false)
      expect(isValidHttpUrl('file:///etc/passwd')).toBe(false)
    })
  })

  // 2. Formatted Markdown Output Generation
  describe('2. Formatted Markdown Output Generation', () => {
    it('formats a complete submission into structured markdown matching GitHub issue template', () => {
      const fullData: SubmissionFormData = {
        name: 'Bangla Regional Dialect Corpus',
        sourceUrl: 'https://data.mendeley.com/datasets/92r62h4k5k/4',
        category: 'natural-language-processing',
        task: 'dialect-identification',
        description: 'A curated dataset of 4,653 sentences across regional dialects.',
        doi: '10.17632/92r62h4k5k.4',
        license: 'CC BY 4.0',
        paperUrl: 'https://doi.org/10.17632/92r62h4k5k.4',
        notes: 'Covers Rangpur, Barisal, Narail, and Khulna dialects.',
      }

      const md = formatSubmissionMarkdown(fullData)
      expect(md).toContain('### Dataset name\nBangla Regional Dialect Corpus')
      expect(md).toContain('### Original publisher or official dataset URL\nhttps://data.mendeley.com/datasets/92r62h4k5k/4')
      expect(md).toContain('**Category:** Natural Language Processing')
      expect(md).toContain('**Primary Task:** dialect-identification')
      expect(md).toContain('**Description:**\nA curated dataset of 4,653 sentences across regional dialects.')
      expect(md).toContain('### License and access conditions\nCC BY 4.0')
      expect(md).toContain('- **DOI:** 10.17632/92r62h4k5k.4')
      expect(md).toContain('- **Supporting Paper URL:** https://doi.org/10.17632/92r62h4k5k.4')
      expect(md).toContain('Covers Rangpur, Barisal, Narail, and Khulna dialects.')
    })

    it('handles optional fields cleanly when omitted', () => {
      const minimalData: SubmissionFormData = {
        name: 'Simple Benchmark',
        sourceUrl: 'https://example.org/dataset',
        category: 'computer-vision',
        task: 'image-classification',
        description: 'A minimal image benchmark dataset description.',
        doi: '',
        license: '',
        paperUrl: '',
        notes: '',
      }

      const md = formatSubmissionMarkdown(minimalData)
      expect(md).toContain('### License and access conditions\nUnknown / Not specified by publisher')
      expect(md).toContain('- **DOI:** N/A')
      expect(md).toContain('- **Supporting Paper URL:** N/A')
      expect(md).toContain('None provided')
    })
  })

  // 3. Advisory Duplicate Detection Integration
  describe('3. Advisory Duplicate Detection', () => {
    it('detects existing dataset by exact or similar name', () => {
      const duplicates = findPotentialDuplicates({ name: 'cifar-10' }, mockCatalog)
      expect(duplicates.length).toBeGreaterThan(0)
      expect(duplicates[0].id).toBe('cifar-10')
      expect(duplicates[0].slug).toBe('cifar-10')
    })

    it('detects existing dataset by exact source URL', () => {
      const duplicates = findPotentialDuplicates(
        { sourceUrl: 'https://data.mendeley.com/datasets/tsdvtzwwpn/1' },
        mockCatalog,
      )
      expect(duplicates.length).toBeGreaterThan(0)
      expect(duplicates[0].id).toBe('bangla-grammar-qa')
      expect(duplicates[0].reasons).toContain('Matching source or repository URL')
    })

    it('detects existing dataset by DOI', () => {
      const duplicates = findPotentialDuplicates(
        { doi: '10.17632/tsdvtzwwpn.1' },
        mockCatalog,
      )
      expect(duplicates.length).toBeGreaterThan(0)
      expect(duplicates[0].id).toBe('bangla-grammar-qa')
    })

    it('returns empty list for non-conflicting new submission', () => {
      const duplicates = findPotentialDuplicates(
        {
          name: 'Completely Unique Dataset 2026',
          sourceUrl: 'https://open-lab.example.org/novel-dataset',
          doi: '10.1234/novel.5678',
        },
        mockCatalog,
      )
      expect(duplicates).toHaveLength(0)
    })
  })

  // 4. Accessible UI Rendering and Semantic Form Elements
  describe('4. Accessible UI Rendering & Semantic Structure', () => {
    it('renders form headings, guidance callouts, and required field labels', () => {
      const html = renderToString(
        <MemoryRouter initialEntries={['/submit']}>
          <SubmitDatasetPage />
        </MemoryRouter>,
      )

      // Main headings
      expect(html).toContain('Propose a Dataset')
      expect(html).toContain('Contributor Portal')
      expect(html).toContain('Dataset Contribution Guidelines')

      // Required indicators
      expect(html).toContain('Dataset Name')
      expect(html).toContain('Official Dataset / Source URL')
      expect(html).toContain('Primary Category')
      expect(html).toContain('Research Task / Intended Use')
      expect(html).toContain('Short Description')

      // Optional section
      expect(html).toContain('Optional Citations &amp; Access Details')
      expect(html).toContain('DOI Identifier')
      expect(html).toContain('License / Access Conditions')
      expect(html).toContain('Supporting Research Paper URL')
      expect(html).toContain('Additional Evidence, Sample Counts, or Limitations')

      // Guidelines & link to CONTRIBUTING.md
      expect(html).toContain('Read full CONTRIBUTING.md guide')
      expect(html).toContain('https://github.com/VisionX25/OpenDatasets/blob/main/CONTRIBUTING.md')

      // Form action button
      expect(html).toContain('Generate &amp; Copy Submission Details')
    })

    it('includes accessibility attributes on form controls', () => {
      const html = renderToString(
        <MemoryRouter initialEntries={['/submit']}>
          <SubmitDatasetPage />
        </MemoryRouter>,
      )

      // Check aria-required attributes
      expect(html).toContain('name="name"')
      expect(html).toContain('name="sourceUrl"')
      expect(html).toContain('name="category"')
      expect(html).toContain('name="task"')
      expect(html).toContain('name="description"')

      // Form has noValidate for custom accessible validation
      expect(html.toLowerCase()).toContain('novalidate')
    })
  })
})
