import type { DatasetMetadata } from '../types/dataset'

export interface SubmissionQuery {
  name?: string
  sourceUrl?: string
  doi?: string
  paperUrl?: string
}

export interface DuplicateMatch {
  id: string
  slug: string
  name: string
  homepage_url: string
  reasons: string[]
}

/**
 * Normalizes a URL for canonical matching (lowercases, removes protocol, www., and trailing slashes).
 */
export function normalizeUrl(url?: string): string {
  if (!url || typeof url !== 'string') return ''
  return url
    .trim()
    .toLowerCase()
    .replace(/^https?:\/\//, '')
    .replace(/^www\./, '')
    .replace(/\/+$/, '')
}

/**
 * Normalizes a string for loose title comparison (alphanumeric only, lowercase, collapsed spaces).
 */
export function normalizeText(text?: string): string {
  if (!text || typeof text !== 'string') return ''
  return text
    .trim()
    .toLowerCase()
    .replace(/[^\p{L}\p{N}\s]/gu, ' ')
    .replace(/\s+/g, ' ')
    .trim()
}

/**
 * Normalizes a DOI string (strips URL prefixes and lowercases).
 */
export function normalizeDoi(doi?: string): string {
  if (!doi || typeof doi !== 'string') return ''
  return doi
    .trim()
    .toLowerCase()
    .replace(/^https?:\/\/(dx\.)?doi\.org\//, '')
    .replace(/^doi:\s*/, '')
    .replace(/\/+$/, '')
}

/**
 * Checks a submitted dataset proposal against the existing catalog to detect potential duplicates.
 * This is an advisory, non-blocking check.
 */
export function findPotentialDuplicates(
  query: SubmissionQuery,
  catalog: DatasetMetadata[],
  maxResults = 5,
): DuplicateMatch[] {
  if (!catalog || catalog.length === 0) return []

  const normName = normalizeText(query.name)
  const normSourceUrl = normalizeUrl(query.sourceUrl)
  const normDoi = normalizeDoi(query.doi)
  const normPaperUrl = normalizeUrl(query.paperUrl)

  // Must have at least some meaningful query input
  const hasName = normName.length >= 3
  const hasSource = normSourceUrl.length >= 6
  const hasDoi = normDoi.length >= 5
  const hasPaper = normPaperUrl.length >= 6

  if (!hasName && !hasSource && !hasDoi && !hasPaper) {
    return []
  }

  const results: DuplicateMatch[] = []

  for (const dataset of catalog) {
    const reasons: string[] = []
    const dsNormName = normalizeText(dataset.name)
    const dsNormSlug = normalizeText(dataset.slug.replace(/-/g, ' '))
    const dsNormId = normalizeText(dataset.id.replace(/[-_]/g, ' '))
    const dsNormHome = normalizeUrl(dataset.homepage_url)
    const dsNormDoi = normalizeDoi(dataset.citation?.doi)

    // 1. Source URL match
    if (hasSource) {
      if (dsNormHome && (dsNormHome === normSourceUrl || dsNormHome.includes(normSourceUrl) || normSourceUrl.includes(dsNormHome))) {
        reasons.push('Matching source or repository URL')
      } else if (dataset.source_references?.some((ref) => {
        const refNorm = normalizeUrl(ref.url)
        return refNorm && (refNorm === normSourceUrl || refNorm.includes(normSourceUrl) || normSourceUrl.includes(refNorm))
      })) {
        reasons.push('Referenced by an existing dataset source link')
      }
    }

    // 2. DOI match
    if (hasDoi) {
      if (dsNormDoi && (dsNormDoi === normDoi || dsNormDoi.includes(normDoi) || normDoi.includes(dsNormDoi))) {
        reasons.push(`Matching DOI identifier (${dataset.citation?.doi || query.doi})`)
      } else if (dataset.source_references?.some((ref) => normalizeDoi(ref.url).includes(normDoi))) {
        reasons.push('Matching DOI in source references')
      }
    }

    // 3. Paper URL match
    if (hasPaper) {
      const paperNorm = normalizeUrl(dataset.citation?.paper_url)
      if (paperNorm && (paperNorm === normPaperUrl || paperNorm.includes(normPaperUrl) || normPaperUrl.includes(paperNorm))) {
        reasons.push('Matching citation paper URL')
      } else if (dataset.source_references?.some((ref) => {
        const refNorm = normalizeUrl(ref.url)
        return refNorm && (refNorm === normPaperUrl || refNorm.includes(normPaperUrl) || normPaperUrl.includes(paperNorm))
      })) {
        reasons.push('Matching research paper in source references')
      }
    }

    // 4. Name match
    if (hasName) {
      if (dsNormName === normName || dsNormSlug === normName || dsNormId === normName) {
        reasons.push('Exact or identical dataset name')
      } else if (
        (normName.length >= 5 && dsNormName.includes(normName)) ||
        (dsNormName.length >= 5 && normName.includes(dsNormName)) ||
        (normName.length >= 4 && dsNormSlug === normName)
      ) {
        reasons.push('Very similar dataset title or slug')
      }
    }

    if (reasons.length > 0) {
      results.push({
        id: dataset.id,
        slug: dataset.slug,
        name: dataset.name,
        homepage_url: dataset.homepage_url,
        reasons,
      })
    }

    if (results.length >= maxResults) {
      break
    }
  }

  return results
}
