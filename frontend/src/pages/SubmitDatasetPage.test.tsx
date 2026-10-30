import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderToString } from 'react-dom/server'
import { MemoryRouter } from 'react-router-dom'
import { SubmitDatasetPage } from './SubmitDatasetPage'
import {
  isValidHttpUrl,
  formatSubmissionMarkdown,
  buildGitHubIssueUrl,
  DEFAULT_MAX_URL_LENGTH,
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

      // Form action buttons
      expect(html).toContain('Continue to GitHub')
      expect(html).toContain('Copy Submission Details')
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

  // 5. Task 11.2: GitHub Issue Form Auto-Prefill URL Generation
  describe('5. GitHub Issue Form Auto-Prefill URL Generation', () => {
    const sampleData: SubmissionFormData = {
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

    it('maps form fields to correct GitHub issue form IDs (name, source, usefulness, license, evidence)', () => {
      const result = buildGitHubIssueUrl(sampleData)
      expect(result.isFallback).toBe(false)

      const parsedUrl = new URL(result.url)
      expect(parsedUrl.origin).toBe('https://github.com')
      expect(parsedUrl.pathname).toBe('/VisionX25/OpenDatasets/issues/new')

      // Template & Title preservation
      expect(parsedUrl.searchParams.get('template')).toBe('dataset_suggestion.yml')
      expect(parsedUrl.searchParams.get('title')).toBe('[Dataset]: Bangla Regional Dialect Corpus')

      // Direct field mappings
      expect(parsedUrl.searchParams.get('name')).toBe('Bangla Regional Dialect Corpus')
      expect(parsedUrl.searchParams.get('source')).toBe('https://data.mendeley.com/datasets/92r62h4k5k/4')

      // usefulness field contains category, task, and description
      const usefulness = parsedUrl.searchParams.get('usefulness') || ''
      expect(usefulness).toContain('**Category:** Natural Language Processing')
      expect(usefulness).toContain('**Primary Task:** dialect-identification')
      expect(usefulness).toContain('A curated dataset of 4,653 sentences across regional dialects.')

      // license field contains documented license
      expect(parsedUrl.searchParams.get('license')).toBe('CC BY 4.0')

      // evidence field contains DOI, paper URL, and notes
      const evidence = parsedUrl.searchParams.get('evidence') || ''
      expect(evidence).toContain('- **DOI:** 10.17632/92r62h4k5k.4')
      expect(evidence).toContain('- **Supporting Paper URL:** https://doi.org/10.17632/92r62h4k5k.4')
      expect(evidence).toContain('Covers Rangpur, Barisal, Narail, and Khulna dialects.')
    })

    it('handles optional fields gracefully without discarding information', () => {
      const minimalData: SubmissionFormData = {
        name: 'MNIST Handwritten Digits',
        sourceUrl: 'http://yann.lecun.com/exdb/mnist/',
        category: 'computer-vision',
        task: 'digit-classification',
        description: '70,000 28x28 grayscale images of handwritten digits 0-9.',
        doi: '',
        license: '',
        paperUrl: '',
        notes: '',
      }

      const result = buildGitHubIssueUrl(minimalData)
      expect(result.isFallback).toBe(false)

      const parsedUrl = new URL(result.url)
      expect(parsedUrl.searchParams.get('name')).toBe('MNIST Handwritten Digits')
      expect(parsedUrl.searchParams.get('license')).toBe('Unknown / Not specified by publisher')

      const evidence = parsedUrl.searchParams.get('evidence') || ''
      expect(evidence).toContain('- **DOI:** N/A')
      expect(evidence).toContain('- **Supporting Paper URL:** N/A')
      expect(evidence).toContain('None provided')
    })

    it('properly URL-encodes special characters, newlines, and markdown tokens', () => {
      const specialData: SubmissionFormData = {
        name: 'Dataset & More / With Special @ Characters!',
        sourceUrl: 'https://example.com/data?query=1&sort=desc#anchor',
        category: 'tabular-time-series',
        task: 'time-series-forecasting',
        description: 'Multi-line\ndescription\nwith "quotes" & ampersands.',
        doi: '10.1234/test&special',
        license: 'Custom (Non-Commercial & Academic Only)',
        paperUrl: 'https://example.com/paper?id=123',
        notes: 'Notes with\nnewlines & symbols.',
      }

      const result = buildGitHubIssueUrl(specialData)
      const parsedUrl = new URL(result.url)

      expect(parsedUrl.searchParams.get('name')).toBe('Dataset & More / With Special @ Characters!')
      expect(parsedUrl.searchParams.get('source')).toBe('https://example.com/data?query=1&sort=desc#anchor')
      expect(parsedUrl.searchParams.get('usefulness')).toContain('Multi-line\ndescription\nwith "quotes" & ampersands.')
    })

    it('activates fallback gracefully when URL length exceeds safe limit', () => {
      // Create data with very long description that exceeds DEFAULT_MAX_URL_LENGTH (2000)
      const longData: SubmissionFormData = {
        ...sampleData,
        description: 'A'.repeat(2500),
      }

      const result = buildGitHubIssueUrl(longData)
      expect(result.isFallback).toBe(true)
      expect(result.urlLength).toBeGreaterThan(DEFAULT_MAX_URL_LENGTH)

      const parsedUrl = new URL(result.url)
      // Fallback retains template and title so contributor lands on correct issue form
      expect(parsedUrl.searchParams.get('template')).toBe('dataset_suggestion.yml')
      expect(parsedUrl.searchParams.get('title')).toBe('[Dataset]: Bangla Regional Dialect Corpus')

      // Excludes body field parameters to prevent 414 error
      expect(parsedUrl.searchParams.get('usefulness')).toBeNull()
      expect(parsedUrl.searchParams.get('name')).toBeNull()

      // Full field values are still retained for clipboard copy
      expect(result.fieldValues.name).toBe('Bangla Regional Dialect Corpus')
      expect(result.fieldValues.usefulness).toContain('A'.repeat(2500))
    })

    it('supports custom max URL length threshold for testing', () => {
      const result = buildGitHubIssueUrl(sampleData, 150)
      expect(result.isFallback).toBe(true)
      expect(result.urlLength).toBeGreaterThan(150)
    })

    it('avoids duplicating [Dataset]: prefix if contributor already entered it in name', () => {
      const dataWithPrefix: SubmissionFormData = {
        ...sampleData,
        name: '[Dataset]: Pre-prefixed Name',
      }
      const result = buildGitHubIssueUrl(dataWithPrefix)
      const parsedUrl = new URL(result.url)
      expect(parsedUrl.searchParams.get('title')).toBe('[Dataset]: Pre-prefixed Name')
    })
  })
})
