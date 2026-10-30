import { describe, it, expect } from 'vitest'
import {
  normalizeUrl,
  normalizeText,
  normalizeDoi,
  findPotentialDuplicates,
} from './duplicateDetector'
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
      paper_title: 'Learning Multiple Layers of Features from Tiny Images',
      paper_url: 'https://www.cs.toronto.edu/~kriz/learning-features-2009-TR.pdf',
      authors: ['Alex Krizhevsky'],
      doi: '10.1.1.222.9220',
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
    source_references: [{ title: 'Repo', url: 'https://data.mendeley.com/datasets/tsdvtzwwpn/1', type: 'repository' }],
    verification: { status: 'verified' },
    citation: {
      doi: '10.17632/tsdvtzwwpn.1',
      authors: ['Rahul Chandra Shil'],
      paper_title: 'Bangla Grammar QA',
    },
  },
]

describe('duplicateDetector utils', () => {
  it('normalizes URLs correctly', () => {
    expect(normalizeUrl('https://www.cs.toronto.edu/~kriz/cifar.html/')).toBe('cs.toronto.edu/~kriz/cifar.html')
    expect(normalizeUrl('http://data.mendeley.com/datasets/tsdvtzwwpn/1')).toBe('data.mendeley.com/datasets/tsdvtzwwpn/1')
    expect(normalizeUrl('')).toBe('')
    expect(normalizeUrl(undefined)).toBe('')
  })

  it('normalizes text and titles correctly', () => {
    expect(normalizeText('CIFAR-10: Dataset!')).toBe('cifar 10 dataset')
    expect(normalizeText('  Bangla   Grammar  QA  ')).toBe('bangla grammar qa')
    expect(normalizeText('')).toBe('')
  })

  it('normalizes DOIs correctly', () => {
    expect(normalizeDoi('https://doi.org/10.17632/tsdvtzwwpn.1')).toBe('10.17632/tsdvtzwwpn.1')
    expect(normalizeDoi('doi: 10.17632/tsdvtzwwpn.1/')).toBe('10.17632/tsdvtzwwpn.1')
    expect(normalizeDoi('')).toBe('')
  })

  it('detects exact name matches', () => {
    const matches = findPotentialDuplicates({ name: 'CIFAR-10' }, mockCatalog)
    expect(matches).toHaveLength(1)
    expect(matches[0].slug).toBe('cifar-10')
    expect(matches[0].reasons).toContain('Exact or identical dataset name')
  })

  it('detects matching source URL', () => {
    const matches = findPotentialDuplicates(
      { name: 'My New Dataset', sourceUrl: 'https://data.mendeley.com/datasets/tsdvtzwwpn/1/' },
      mockCatalog,
    )
    expect(matches).toHaveLength(1)
    expect(matches[0].slug).toBe('bangla-grammar-qa')
    expect(matches[0].reasons).toContain('Matching source or repository URL')
  })

  it('detects matching DOI', () => {
    const matches = findPotentialDuplicates(
      { name: 'Different Name', doi: 'https://doi.org/10.17632/tsdvtzwwpn.1' },
      mockCatalog,
    )
    expect(matches).toHaveLength(1)
    expect(matches[0].slug).toBe('bangla-grammar-qa')
    expect(matches[0].reasons.some((r) => r.includes('Matching DOI'))).toBe(true)
  })

  it('returns empty array when no matches are found', () => {
    const matches = findPotentialDuplicates(
      {
        name: 'Brand New Unique Speech Dataset 2026',
        sourceUrl: 'https://unique-university.edu/datasets/speech-2026',
        doi: '10.9999/unique.doi.1',
      },
      mockCatalog,
    )
    expect(matches).toHaveLength(0)
  })

  it('returns empty array when query is empty or too short', () => {
    expect(findPotentialDuplicates({}, mockCatalog)).toHaveLength(0)
    expect(findPotentialDuplicates({ name: 'ab' }, mockCatalog)).toHaveLength(0)
  })
})
