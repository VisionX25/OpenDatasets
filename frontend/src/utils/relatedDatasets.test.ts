import { describe, it, expect } from 'vitest'
import type { DatasetMetadata } from '../types/dataset'
import {
  extractFamilyStem,
  computeRelatednessScore,
  getRelatedDatasets,
} from './relatedDatasets'

function makeTestDataset(overrides: Partial<DatasetMetadata> & { id: string; name: string }): DatasetMetadata {
  return {
    schema_version: '1.0.0',
    id: overrides.id,
    slug: overrides.slug || overrides.id,
    name: overrides.name,
    description: overrides.description || `Description for ${overrides.name}`,
    homepage_url: overrides.homepage_url || `https://example.org/${overrides.id}`,
    publisher: overrides.publisher || { name: 'Test Lab', type: 'academic' },
    modalities: overrides.modalities || ['vision'],
    tasks: overrides.tasks || ['image-classification'],
    tags: overrides.tags || ['vision-test'],
    license: overrides.license || { status: 'verified_open', name: 'MIT' },
    source_references: overrides.source_references || [],
    verification: overrides.verification || { status: 'verified' },
    dates: overrides.dates || { published: '2023-01-01' },
    citation: overrides.citation,
  }
}

describe('relatedDatasets utility', () => {
  describe('extractFamilyStem', () => {
    it('strips common version, count, and split suffixes', () => {
      expect(extractFamilyStem('cifar-10')).toBe('cifar')
      expect(extractFamilyStem('cifar-100')).toBe('cifar')
      expect(extractFamilyStem('imagenet-1k')).toBe('imagenet')
      expect(extractFamilyStem('imagenet-21k')).toBe('imagenet')
      expect(extractFamilyStem('squad-v2')).toBe('squad')
      expect(extractFamilyStem('argoverse-2')).toBe('argoverse')
      expect(extractFamilyStem('glue-benchmark')).toBe('glue')
      expect(extractFamilyStem('custom_dataset_mini')).toBe('custom_dataset')
    })

    it('preserves stems when no common suffix is present', () => {
      expect(extractFamilyStem('mnist')).toBe('mnist')
      expect(extractFamilyStem('celeba')).toBe('celeba')
    })
  })

  describe('computeRelatednessScore', () => {
    const baseTarget = makeTestDataset({
      id: 'cifar-10',
      slug: 'cifar-10',
      name: 'CIFAR-10',
      publisher: { name: 'University of Toronto', type: 'academic' },
      modalities: ['vision'],
      tasks: ['image-classification'],
      tags: ['benchmark', 'tiny-images'],
      citation: {
        doi: '10.1234/cifar.2009',
        paper_url: 'https://example.org/cifar-paper.pdf',
      },
      source_references: [
        {
          title: 'Repo',
          url: 'https://example.org/toronto/cifar-repo',
          type: 'repository',
        },
      ],
    })

    it('returns score 0 when comparing dataset to itself (by id or slug)', () => {
      const sameId = makeTestDataset({ id: 'cifar-10', name: 'CIFAR-10' })
      expect(computeRelatednessScore(baseTarget, sameId).score).toBe(0)

      const sameSlug = makeTestDataset({ id: 'cifar-other-id', slug: 'cifar-10', name: 'Different' })
      expect(computeRelatednessScore(baseTarget, sameSlug).score).toBe(0)
    })

    it('awards high score for shared family stem and direct prefix', () => {
      const familyCandidate = makeTestDataset({
        id: 'cifar-100',
        slug: 'cifar-100',
        name: 'CIFAR-100',
        publisher: { name: 'University of Toronto', type: 'academic' },
        modalities: ['vision'],
        tasks: ['image-classification'],
      })

      const result = computeRelatednessScore(baseTarget, familyCandidate)
      expect(result.score).toBeGreaterThanOrEqual(40)
      expect(result.reasons.some((r) => r.includes('Shared dataset family stem'))).toBe(true)
    })

    it('awards points for shared citation DOI and paper URL', () => {
      const sharedDoi = makeTestDataset({
        id: 'other-ds-1',
        name: 'Other Dataset 1',
        citation: { doi: 'https://doi.org/10.1234/cifar.2009' },
      })
      const resultDoi = computeRelatednessScore(baseTarget, sharedDoi)
      expect(resultDoi.score).toBeGreaterThanOrEqual(50)
      expect(resultDoi.reasons.some((r) => r.includes('Shared citation DOI'))).toBe(true)

      const sharedPaper = makeTestDataset({
        id: 'other-ds-2',
        name: 'Other Dataset 2',
        citation: { paper_url: 'https://example.org/cifar-paper.pdf/' },
      })
      const resultPaper = computeRelatednessScore(baseTarget, sharedPaper)
      expect(resultPaper.score).toBeGreaterThanOrEqual(45)
      expect(resultPaper.reasons.some((r) => r.includes('Shared primary paper URL'))).toBe(true)
    })

    it('awards points for shared non-generic source references', () => {
      const sharedRepo = makeTestDataset({
        id: 'other-ds-repo',
        name: 'Other Dataset Repo',
        source_references: [
          {
            title: 'Same Repo',
            url: 'https://example.org/toronto/cifar-repo/',
            type: 'repository',
          },
        ],
      })
      const result = computeRelatednessScore(baseTarget, sharedRepo)
      expect(result.score).toBeGreaterThanOrEqual(30)
      expect(result.reasons.some((r) => r.includes('Shared reference repository/archive URL'))).toBe(true)
    })

    it('awards points for matching research tasks, modalities, and categories', () => {
      const taskCandidate = makeTestDataset({
        id: 'svhn',
        name: 'SVHN',
        publisher: { name: 'Stanford', type: 'academic' },
        modalities: ['vision'],
        tasks: ['image-classification'],
      })
      const result = computeRelatednessScore(baseTarget, taskCandidate)
      // Task (15) + Modality (8) + Category computer-vision (5) = 28
      expect(result.score).toBe(28)
      expect(result.reasons.some((r) => r.includes('Shared tasks: image-classification'))).toBe(true)
      expect(result.reasons.some((r) => r.includes('Shared modalities: vision'))).toBe(true)
    })

    it('awards publisher points when functional domain overlap exists', () => {
      const samePublisherSameModality = makeTestDataset({
        id: 'toronto-faces',
        name: 'Toronto Faces',
        publisher: { name: 'University of Toronto', type: 'academic' },
        modalities: ['vision'],
        tasks: ['face-detection'],
      })
      const result = computeRelatednessScore(baseTarget, samePublisherSameModality)
      // Modality (8) + Category (5) + Publisher (10) = 23
      expect(result.reasons.some((r) => r.includes('Shared publisher'))).toBe(true)
      expect(result.score).toBe(23)
    })
  })

  describe('getRelatedDatasets', () => {
    const target = makeTestDataset({
      id: 'cifar-10',
      slug: 'cifar-10',
      name: 'CIFAR-10',
      publisher: { name: 'University of Toronto', type: 'academic' },
      modalities: ['vision'],
      tasks: ['image-classification'],
      tags: ['tiny-images'],
    })

    const cifar100 = makeTestDataset({
      id: 'cifar-100',
      slug: 'cifar-100',
      name: 'CIFAR-100',
      publisher: { name: 'University of Toronto', type: 'academic' },
      modalities: ['vision'],
      tasks: ['image-classification'],
      tags: ['tiny-images'],
    })

    const svhn = makeTestDataset({
      id: 'svhn',
      slug: 'svhn',
      name: 'SVHN',
      publisher: { name: 'Stanford', type: 'academic' },
      modalities: ['vision'],
      tasks: ['image-classification'],
    })

    const stl10 = makeTestDataset({
      id: 'stl-10',
      slug: 'stl-10',
      name: 'STL-10',
      publisher: { name: 'Stanford', type: 'academic' },
      modalities: ['vision'],
      tasks: ['image-classification'],
    })

    const imagenet = makeTestDataset({
      id: 'imagenet-1k',
      slug: 'imagenet-1k',
      name: 'ImageNet-1K',
      publisher: { name: 'Stanford', type: 'academic' },
      modalities: ['vision'],
      tasks: ['image-classification'],
    })

    const flowers102 = makeTestDataset({
      id: 'flowers-102',
      slug: 'flowers-102',
      name: 'Oxford Flowers 102',
      publisher: { name: 'Oxford', type: 'academic' },
      modalities: ['vision'],
      tasks: ['image-classification'],
    })

    const unrelatedAudio = makeTestDataset({
      id: 'librispeech',
      slug: 'librispeech',
      name: 'LibriSpeech',
      publisher: { name: 'OpenSLR', type: 'community' },
      modalities: ['audio'],
      tasks: ['speech-recognition'],
    })

    it('recommends at most maxRecommendations (default 4)', () => {
      const catalog = [
        target,
        cifar100,
        svhn,
        stl10,
        imagenet,
        flowers102,
        unrelatedAudio,
      ]

      const related = getRelatedDatasets(target, catalog)
      expect(related.length).toBe(4)
    })

    it('excludes the currently viewed target dataset', () => {
      const catalog = [target, cifar100, svhn]
      const related = getRelatedDatasets(target, catalog)
      expect(related.some((d) => d.id === target.id || d.slug === target.slug)).toBe(false)
    })

    it('prioritizes explicitly related dataset family (cifar-100 ranks top for cifar-10)', () => {
      const catalog = [flowers102, svhn, cifar100, imagenet]
      const related = getRelatedDatasets(target, catalog)
      expect(related[0].id).toBe('cifar-100')
    })

    it('never recommends the same dataset twice', () => {
      // Duplicate items in input catalog
      const catalog = [cifar100, cifar100, svhn, svhn]
      const related = getRelatedDatasets(target, catalog)
      const ids = related.map((d) => d.id)
      const uniqueIds = Array.from(new Set(ids))
      expect(ids.length).toBe(uniqueIds.length)
    })

    it('provides deterministic ranking when scores are equal (sorts alphabetically by name, then slug)', () => {
      // Both have identical scores
      const candidateA = makeTestDataset({
        id: 'candidate-b-id',
        slug: 'candidate-b-slug',
        name: 'Dataset B',
        modalities: ['vision'],
        tasks: ['image-classification'],
      })
      const candidateB = makeTestDataset({
        id: 'candidate-a-id',
        slug: 'candidate-a-slug',
        name: 'Dataset A',
        modalities: ['vision'],
        tasks: ['image-classification'],
      })

      const catalog = [candidateA, candidateB]
      const related = getRelatedDatasets(target, catalog)
      expect(related[0].name).toBe('Dataset A')
      expect(related[1].name).toBe('Dataset B')
    })

    it('returns an empty array when no sufficiently relevant datasets exist (below MIN_RELATED_SCORE)', () => {
      const catalog = [target, unrelatedAudio]
      const related = getRelatedDatasets(target, catalog)
      expect(related).toEqual([])
    })

    it('handles empty or null catalog gracefully', () => {
      expect(getRelatedDatasets(target, [])).toEqual([])
      expect(getRelatedDatasets(target, null as unknown as DatasetMetadata[])).toEqual([])
    })
  })
})
