import type { DatasetMetadata } from '../types/dataset'
import { matchesCategory, CATEGORIES } from './datasetFilters'

export const MIN_RELATED_SCORE = 15

export interface ScoredDataset {
  dataset: DatasetMetadata
  score: number
  reasons: string[]
}

/**
 * Normalize an identifier or slug for family stem extraction.
 * Strips release version suffixes (e.g. -v1, -v2, -10, -100, -1k, -21k, -mini, -tiny, -subset, -benchmark, -2024).
 */
export function extractFamilyStem(slugOrId: string): string {
  const clean = slugOrId.toLowerCase().trim()
  return clean
    .replace(
      /[-_](v?\d+(\.\d+)?k?|\d+k?|benchmark|subset|full|train|test|val|mini|tiny|base|large|part\d+|edition|\d{4})$/i,
      '',
    )
    .trim()
}

/**
 * Normalize URLs for comparison (case-insensitive, strip trailing slashes).
 */
function normalizeUrl(url: string | undefined): string {
  if (!url) return ''
  try {
    const parsed = new URL(url)
    return `${parsed.hostname.toLowerCase()}${parsed.pathname.replace(/\/+$/, '').toLowerCase()}`
  } catch {
    return url.trim().toLowerCase().replace(/\/+$/, '')
  }
}

/**
 * Normalize DOI string for comparison.
 */
function normalizeDoi(doi: string | undefined): string {
  if (!doi) return ''
  return doi
    .trim()
    .toLowerCase()
    .replace(/^https?:\/\/(dx\.)?doi\.org\//i, '')
    .replace(/\/+$/, '')
}

/**
 * Compute the relatedness score between a target dataset and a candidate dataset.
 * Returns 0 if candidate is the target or if score is below MIN_RELATED_SCORE.
 */
export function computeRelatednessScore(
  target: DatasetMetadata,
  candidate: DatasetMetadata,
): { score: number; reasons: string[] } {
  // Exclude self
  if (
    candidate.id === target.id ||
    candidate.slug === target.slug ||
    (target.id && candidate.id && candidate.id.toLowerCase() === target.id.toLowerCase())
  ) {
    return { score: 0, reasons: [] }
  }

  let score = 0
  const reasons: string[] = []

  // 1. Explicitly related dataset families and versions
  const targetStem = extractFamilyStem(target.slug || target.id)
  const candidateStem = extractFamilyStem(candidate.slug || candidate.id)

  if (targetStem.length >= 3 && targetStem === candidateStem) {
    score += 40
    reasons.push(`Shared dataset family stem: ${targetStem}`)
  } else if (
    (target.slug &&
      candidate.slug &&
      (candidate.slug.startsWith(target.slug + '-') || target.slug.startsWith(candidate.slug + '-'))) ||
    (target.id &&
      candidate.id &&
      (candidate.id.startsWith(target.id + '-') || target.id.startsWith(candidate.id + '-')))
  ) {
    score += 35
    reasons.push('Direct prefix family match')
  }

  // Citation DOI match
  const targetDoi = normalizeDoi(target.citation?.doi)
  const candidateDoi = normalizeDoi(candidate.citation?.doi)
  if (targetDoi && candidateDoi && targetDoi === candidateDoi) {
    score += 50
    reasons.push(`Shared citation DOI: ${targetDoi}`)
  }

  // Citation paper URL match
  const targetPaperUrl = normalizeUrl(target.citation?.paper_url)
  const candidatePaperUrl = normalizeUrl(candidate.citation?.paper_url)
  if (targetPaperUrl && candidatePaperUrl && targetPaperUrl === candidatePaperUrl) {
    score += 45
    reasons.push('Shared primary paper URL')
  }

  // Shared source references (repository, archive, or documentation)
  const targetRefUrls = new Set(
    (target.source_references || [])
      .map((r) => normalizeUrl(r.url))
      .filter(
        (u) =>
          u &&
          u !== 'github.com' &&
          u !== 'huggingface.co' &&
          !u.endsWith('github.com/') &&
          !u.endsWith('huggingface.co/'),
      ),
  )
  if (targetRefUrls.size > 0) {
    for (const ref of candidate.source_references || []) {
      const norm = normalizeUrl(ref.url)
      if (norm && targetRefUrls.has(norm)) {
        score += 30
        reasons.push('Shared reference repository/archive URL')
        break
      }
    }
  }

  // 2. Matching research tasks
  const targetTasks = new Set((target.tasks || []).map((t) => t.toLowerCase()))
  const sharedTasks: string[] = []
  for (const t of candidate.tasks || []) {
    if (targetTasks.has(t.toLowerCase())) {
      sharedTasks.push(t)
    }
  }
  if (sharedTasks.length > 0) {
    score += sharedTasks.length * 15
    reasons.push(`Shared tasks: ${sharedTasks.join(', ')}`)
  }

  // 3. Matching modalities
  const targetModalities = new Set((target.modalities || []).map((m) => m.toLowerCase()))
  const sharedModalities: string[] = []
  for (const m of candidate.modalities || []) {
    if (targetModalities.has(m.toLowerCase())) {
      sharedModalities.push(m)
    }
  }
  if (sharedModalities.length > 0) {
    score += sharedModalities.length * 8
    reasons.push(`Shared modalities: ${sharedModalities.join(', ')}`)
  }

  // 4. Matching categories
  const targetCategories = CATEGORIES.map((c) => c.id).filter((catId) =>
    matchesCategory(target, catId),
  )
  const sharedCategories = targetCategories.filter((catId) =>
    matchesCategory(candidate, catId),
  )
  if (sharedCategories.length > 0) {
    score += sharedCategories.length * 5
    reasons.push(`Shared categories: ${sharedCategories.join(', ')}`)
  }

  // 5. Matching publisher (only if publisher is named and there is some functional overlap)
  const targetPub = target.publisher?.name?.trim().toLowerCase()
  const candidatePub = candidate.publisher?.name?.trim().toLowerCase()
  if (
    targetPub &&
    candidatePub &&
    targetPub === candidatePub &&
    targetPub !== 'unknown' &&
    targetPub !== 'community'
  ) {
    // Only give publisher points if they also share at least a modality, task, or family
    if (sharedModalities.length > 0 || sharedTasks.length > 0 || score >= 35) {
      score += 10
      reasons.push(`Shared publisher: ${target.publisher.name}`)
    }
  }

  // 6. Matching tags
  const GENERIC_TAGS = new Set([
    'dataset',
    'open-data',
    'machine-learning',
    'ml',
    'benchmark',
    'evaluation',
  ])
  const targetTags = new Set(
    (target.tags || []).map((t) => t.toLowerCase()).filter((t) => !GENERIC_TAGS.has(t)),
  )
  const sharedTags: string[] = []
  for (const t of candidate.tags || []) {
    const lower = t.toLowerCase()
    if (!GENERIC_TAGS.has(lower) && targetTags.has(lower)) {
      sharedTags.push(t)
    }
  }
  if (sharedTags.length > 0) {
    score += sharedTags.length * 3
    reasons.push(`Shared tags: ${sharedTags.join(', ')}`)
  }

  return { score, reasons }
}

/**
 * Get up to `maxRecommendations` related datasets for a target dataset from the catalog.
 * Excludes target, prevents duplicates, enforces MIN_RELATED_SCORE threshold,
 * and uses deterministic ranking (score desc, name asc, slug asc).
 */
export function getRelatedDatasets(
  target: DatasetMetadata,
  catalog: DatasetMetadata[],
  maxRecommendations: number = 4,
): DatasetMetadata[] {
  if (!target || !catalog || catalog.length === 0) {
    return []
  }

  const scoredList: ScoredDataset[] = []
  const seenSlugs = new Set<string>()

  for (const candidate of catalog) {
    if (!candidate || seenSlugs.has(candidate.slug)) {
      continue
    }
    seenSlugs.add(candidate.slug)

    const { score, reasons } = computeRelatednessScore(target, candidate)
    if (score >= MIN_RELATED_SCORE) {
      scoredList.push({ dataset: candidate, score, reasons })
    }
  }

  // Deterministic sort:
  // 1. Score descending
  // 2. Name ascending (case-insensitive)
  // 3. Slug ascending
  scoredList.sort((a, b) => {
    if (b.score !== a.score) {
      return b.score - a.score
    }
    const cmp = a.dataset.name.localeCompare(b.dataset.name, undefined, { sensitivity: 'base' })
    if (cmp !== 0) {
      return cmp
    }
    return a.dataset.slug.localeCompare(b.dataset.slug)
  })

  return scoredList.slice(0, maxRecommendations).map((item) => item.dataset)
}
