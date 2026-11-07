import { describe, it, expect, vi } from 'vitest'
import type { DatasetMetadata } from '../types/dataset'
import {
  cleanDoi,
  extractPublicationYear,
  parseAuthorName,
  formatAuthorsApa,
  formatAuthorsIeee,
  generateApaCitation,
  generateIeeeCitation,
  generateBibtexCitation,
  formatCitation,
  downloadCitationFile,
} from './citationUtils'

const createMockDataset = (overrides?: Partial<DatasetMetadata>): DatasetMetadata => {
  return {
    id: 'test-dataset-01',
    slug: 'test-dataset',
    name: 'Test Dataset for Benchmarking',
    description: 'A comprehensive dataset for testing academic citations.',
    category: 'nlp',
    homepage_url: 'https://example.org/dataset',
    license: {
      name: 'MIT',
      status: 'standard_open',
    },
    sample_count: {
      total: 10000,
      unit: 'samples',
    },
    dates: {
      published: '2021-06-15',
    },
    citation: {
      authors: ['Alice Smith', 'Bob J. Jones', 'Carol White'],
      paper_title: 'Benchmarking Multi-Format Citations in AI Research',
      doi: '10.1000/182',
      paper_url: 'https://example.org/paper.pdf',
    },
    audit: {
      status: 'verified',
      verified_at: '2024-01-01',
    },
    ...overrides,
  } as DatasetMetadata
}

describe('citationUtils', () => {
  describe('cleanDoi', () => {
    it('returns null for undefined, null, or empty string', () => {
      expect(cleanDoi(undefined)).toBeNull()
      expect(cleanDoi('')).toBeNull()
      expect(cleanDoi('   ')).toBeNull()
    })

    it('removes https://doi.org/ prefix', () => {
      expect(cleanDoi('https://doi.org/10.1145/12345')).toBe('10.1145/12345')
    })

    it('removes http://dx.doi.org/ prefix', () => {
      expect(cleanDoi('http://dx.doi.org/10.1145/12345')).toBe('10.1145/12345')
    })

    it('removes doi: prefix', () => {
      expect(cleanDoi('doi: 10.1145/12345')).toBe('10.1145/12345')
      expect(cleanDoi('doi:10.1145/12345')).toBe('10.1145/12345')
    })

    it('returns bare DOI as is with whitespace trimmed', () => {
      expect(cleanDoi('  10.1145/12345  ')).toBe('10.1145/12345')
    })
  })

  describe('extractPublicationYear', () => {
    it('extracts year from dates.published', () => {
      const dataset = createMockDataset({ dates: { published: '2022-09-01' } })
      expect(extractPublicationYear(dataset)).toBe('2022')
    })

    it('extracts year from dates.published when only year is given', () => {
      const dataset = createMockDataset({ dates: { published: '2019' } })
      expect(extractPublicationYear(dataset)).toBe('2019')
    })

    it('falls back to extracting year from BibTeX when dates.published is absent', () => {
      const dataset = createMockDataset({
        dates: {},
        citation: {
          bibtex: '@article{test, year = {2018}, title = {Paper}}',
        },
      })
      expect(extractPublicationYear(dataset)).toBe('2018')
    })

    it('returns null when no year can be extracted', () => {
      const dataset = createMockDataset({
        dates: {},
        citation: {},
      })
      expect(extractPublicationYear(dataset)).toBeNull()
    })
  })

  describe('parseAuthorName', () => {
    it('handles empty input gracefully', () => {
      expect(parseAuthorName('')).toEqual({ firstNames: '', lastName: '', initials: '' })
      expect(parseAuthorName('   ')).toEqual({ firstNames: '', lastName: '', initials: '' })
    })

    it('parses single name or organization', () => {
      expect(parseAuthorName('OpenAI')).toEqual({ firstNames: '', lastName: 'OpenAI', initials: '' })
    })

    it('parses "First Last"', () => {
      expect(parseAuthorName('John Doe')).toEqual({ firstNames: 'John', lastName: 'Doe', initials: 'J.' })
    })

    it('parses "First Middle Last"', () => {
      expect(parseAuthorName('John Fitzgerald Kennedy')).toEqual({
        firstNames: 'John Fitzgerald',
        lastName: 'Kennedy',
        initials: 'J. F.',
      })
    })

    it('parses "Last, First"', () => {
      expect(parseAuthorName('Doe, John')).toEqual({
        firstNames: 'John',
        lastName: 'Doe',
        initials: 'J.',
      })
    })

    it('parses "Last, First Middle"', () => {
      expect(parseAuthorName('Cerdeira, António Paulo')).toEqual({
        firstNames: 'António Paulo',
        lastName: 'Cerdeira',
        initials: 'A. P.',
      })
    })
  })

  describe('formatAuthorsApa', () => {
    it('returns empty string for empty author list', () => {
      expect(formatAuthorsApa([])).toBe('')
    })

    it('formats single author', () => {
      expect(formatAuthorsApa(['John Doe'])).toBe('Doe, J.')
      expect(formatAuthorsApa(['OpenAI'])).toBe('OpenAI')
    })

    it('formats two authors with ampersand', () => {
      expect(formatAuthorsApa(['John Doe', 'Jane Smith'])).toBe('Doe, J., & Smith, J.')
    })

    it('formats 3 to 20 authors with serial comma and ampersand', () => {
      expect(formatAuthorsApa(['John Doe', 'Jane Smith', 'Bob Wilson'])).toBe(
        'Doe, J., Smith, J., & Wilson, B.'
      )
    })

    it('formats >20 authors using APA 7th ellipsis rule', () => {
      const authors = Array.from({ length: 22 }, (_, i) => `Author${i + 1} Last${i + 1}`)
      const result = formatAuthorsApa(authors)
      expect(result).toContain('Last1, A.')
      expect(result).toContain('Last19, A.')
      expect(result).toContain('... Last22, A.')
      expect(result).not.toContain('Last20, A.')
    })
  })

  describe('formatAuthorsIeee', () => {
    it('returns empty string for empty author list', () => {
      expect(formatAuthorsIeee([])).toBe('')
    })

    it('formats single author', () => {
      expect(formatAuthorsIeee(['John Doe'])).toBe('J. Doe')
      expect(formatAuthorsIeee(['OpenAI'])).toBe('OpenAI')
    })

    it('formats two authors with "and"', () => {
      expect(formatAuthorsIeee(['John Doe', 'Jane Smith'])).toBe('J. Doe and J. Smith')
    })

    it('formats 3 to 6 authors with serial comma and "and"', () => {
      expect(formatAuthorsIeee(['John Doe', 'Jane Smith', 'Bob Wilson'])).toBe(
        'J. Doe, J. Smith, and B. Wilson'
      )
    })

    it('formats >6 authors with first author and "et al."', () => {
      const authors = ['A. Smith', 'B. Jones', 'C. White', 'D. Black', 'E. Grey', 'F. Brown', 'G. Green']
      expect(formatAuthorsIeee(authors)).toBe('A. Smith et al.')
    })
  })

  describe('generateApaCitation', () => {
    it('formats complete APA citation with DOI', () => {
      const dataset = createMockDataset()
      const result = generateApaCitation(dataset)
      expect(result.warning).toBeNull()
      expect(result.citationText).toBe(
        'Smith, A., Jones, B. J., & White, C. (2021). Benchmarking Multi-Format Citations in AI Research. https://doi.org/10.1000/182'
      )
    })

    it('falls back to URL when DOI is absent', () => {
      const dataset = createMockDataset({
        citation: {
          authors: ['Alice Smith'],
          paper_title: 'Paper Title',
          paper_url: 'https://example.org/paper',
        },
      })
      const result = generateApaCitation(dataset)
      expect(result.citationText).toBe('Smith, A. (2021). Paper Title. https://example.org/paper')
    })

    it('returns warning when neither authors nor paper_title are available', () => {
      const dataset = createMockDataset({
        citation: {},
      })
      const result = generateApaCitation(dataset)
      expect(result.citationText).toBeNull()
      expect(result.warning).toContain('Author and publication metadata are not specified')
    })
  })

  describe('generateIeeeCitation', () => {
    it('formats complete IEEE citation with DOI', () => {
      const dataset = createMockDataset()
      const result = generateIeeeCitation(dataset)
      expect(result.warning).toBeNull()
      expect(result.citationText).toBe(
        'A. Smith, B. J. Jones, and C. White, "Benchmarking Multi-Format Citations in AI Research," 2021. doi: 10.1000/182.'
      )
    })

    it('falls back to URL when DOI is absent', () => {
      const dataset = createMockDataset({
        citation: {
          authors: ['Alice Smith'],
          paper_title: 'Paper Title',
          paper_url: 'https://example.org/paper',
        },
      })
      const result = generateIeeeCitation(dataset)
      expect(result.citationText).toBe(
        'A. Smith, "Paper Title," 2021. [Online]. Available: https://example.org/paper.'
      )
    })

    it('returns warning when neither authors nor paper_title are available', () => {
      const dataset = createMockDataset({
        citation: {},
      })
      const result = generateIeeeCitation(dataset)
      expect(result.citationText).toBeNull()
      expect(result.warning).toContain('Author and publication metadata are not specified')
    })
  })

  describe('generateBibtexCitation', () => {
    it('returns existing declared bibtex when present', () => {
      const customBibtex = '@article{custom2021, title={Custom Title}}'
      const dataset = createMockDataset({
        citation: {
          bibtex: customBibtex,
        },
      })
      const result = generateBibtexCitation(dataset)
      expect(result.citationText).toBe(customBibtex)
      expect(result.isSynthesized).toBe(false)
      expect(result.warning).toBeNull()
    })

    it('synthesizes bibtex when bibtex is missing but metadata exists', () => {
      const dataset = createMockDataset({
        citation: {
          authors: ['Alice Smith', 'Bob Jones'],
          paper_title: 'Synthesized Title',
          doi: '10.1000/182',
        },
      })
      const result = generateBibtexCitation(dataset)
      expect(result.isSynthesized).toBe(true)
      expect(result.citationText).toContain('@misc{test-dataset,')
      expect(result.citationText).toContain('author = {Alice Smith and Bob Jones}')
      expect(result.citationText).toContain('title = {Synthesized Title}')
      expect(result.citationText).toContain('doi = {10.1000/182}')
    })

    it('returns warning when insufficient metadata to synthesize BibTeX', () => {
      const dataset = createMockDataset({
        citation: {},
      })
      const result = generateBibtexCitation(dataset)
      expect(result.citationText).toBeNull()
      expect(result.warning).toContain('BibTeX entry is not declared and sufficient author/title metadata is unavailable')
    })
  })

  describe('formatCitation', () => {
    const dataset = createMockDataset()

    it('dispatches to bibtex', () => {
      const result = formatCitation(dataset, 'bibtex')
      expect(result.citationText).toBeDefined()
    })

    it('dispatches to apa', () => {
      const result = formatCitation(dataset, 'apa')
      expect(result.citationText).toContain('Smith, A.')
    })

    it('dispatches to ieee', () => {
      const result = formatCitation(dataset, 'ieee')
      expect(result.citationText).toContain('A. Smith')
    })

    it('handles unknown format', () => {
      // @ts-expect-error Testing invalid runtime value
      const result = formatCitation(dataset, 'chicago')
      expect(result.citationText).toBeNull()
      expect(result.warning).toContain('Unsupported citation format')
    })
  })

  describe('downloadCitationFile', () => {
    it('safely handles non-browser environments where document is undefined', () => {
      expect(() => downloadCitationFile('test.bib', '@article{test}')).not.toThrow()
    })

    it('creates blob, triggers download click, and cleans up URL and DOM node in browser environment', () => {
      const createdUrl = 'blob:http://localhost/fake-blob-uuid'
      let revokedUrl: string | null = null

      const fakeLink = {
        href: '',
        download: '',
        click: vi.fn(),
      }

      const fakeDocument = {
        createElement: vi.fn((tag: string) => {
          if (tag === 'a') return fakeLink
          return {}
        }),
        body: {
          appendChild: vi.fn(),
          removeChild: vi.fn(),
        },
      }

      const fakeUrl = {
        createObjectURL: vi.fn(() => createdUrl),
        revokeObjectURL: vi.fn((url: string) => {
          revokedUrl = url
        }),
      }

      // Temporarily define window and document
      const origWindow = globalThis.window
      const origDoc = globalThis.document
      const origUrl = globalThis.URL

      try {
        Object.defineProperty(globalThis, 'window', { value: {}, writable: true, configurable: true })
        Object.defineProperty(globalThis, 'document', { value: fakeDocument, writable: true, configurable: true })
        Object.defineProperty(globalThis, 'URL', { value: fakeUrl, writable: true, configurable: true })

        downloadCitationFile('dataset.bib', '@article{test}')

        expect(fakeUrl.createObjectURL).toHaveBeenCalledTimes(1)
        expect(fakeLink.download).toBe('dataset.bib')
        expect(fakeLink.click).toHaveBeenCalledTimes(1)
        expect(fakeDocument.body.appendChild).toHaveBeenCalledWith(fakeLink)
        expect(fakeDocument.body.removeChild).toHaveBeenCalledWith(fakeLink)
        expect(fakeUrl.revokeObjectURL).toHaveBeenCalledWith(createdUrl)
        expect(revokedUrl).toBe(createdUrl)
      } finally {
        Object.defineProperty(globalThis, 'window', { value: origWindow, writable: true, configurable: true })
        Object.defineProperty(globalThis, 'document', { value: origDoc, writable: true, configurable: true })
        Object.defineProperty(globalThis, 'URL', { value: origUrl, writable: true, configurable: true })
      }
    })
  })
})
