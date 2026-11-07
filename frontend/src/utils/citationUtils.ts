import type { DatasetMetadata } from '../types/dataset'

export type CitationFormat = 'bibtex' | 'apa' | 'ieee'

export interface CitationResult {
  citationText: string | null
  warning: string | null
  isSynthesized?: boolean
}

/**
 * Normalizes DOI to bare format without URL prefix.
 */
export function cleanDoi(rawDoi?: string): string | null {
  if (!rawDoi || typeof rawDoi !== 'string') return null
  const trimmed = rawDoi.trim()
  if (!trimmed) return null
  return trimmed.replace(/^https?:\/\/(?:dx\.)?doi\.org\//i, '').replace(/^doi:\s*/i, '')
}

/**
 * Extracts a 4-digit publication year from dataset metadata or embedded BibTeX.
 */
export function extractPublicationYear(dataset: DatasetMetadata): string | null {
  if (dataset.dates?.published) {
    const match = dataset.dates.published.match(/\b(\d{4})\b/)
    if (match) return match[1]
  }

  if (dataset.citation?.bibtex) {
    const match = dataset.citation.bibtex.match(/year\s*=\s*[{"]?(\d{4})[}"]?/i)
    if (match) return match[1]
  }

  return null
}

/**
 * Parses author string into components, handling both "First Last" and "Last, First".
 */
export function parseAuthorName(authorStr: string): { firstNames: string; lastName: string; initials: string } {
  const trimmed = authorStr.trim()
  if (!trimmed) return { firstNames: '', lastName: '', initials: '' }

  // Case 1: "Last, First [Middle]"
  if (trimmed.includes(',')) {
    const parts = trimmed.split(',')
    const lastName = parts[0].trim()
    const firstNames = parts.slice(1).join(' ').trim()
    const tokens = firstNames.split(/\s+/).filter(Boolean)
    const initials = tokens
      .map((t) => (t.endsWith('.') ? t : `${t.charAt(0).toUpperCase()}.`))
      .join(' ')
    return { firstNames, lastName, initials }
  }

  // Case 2: "First [Middle] Last" or single token (organization)
  const tokens = trimmed.split(/\s+/).filter(Boolean)
  if (tokens.length === 1) {
    return { firstNames: '', lastName: tokens[0], initials: '' }
  }

  const lastName = tokens[tokens.length - 1]
  const givenTokens = tokens.slice(0, -1)
  const firstNames = givenTokens.join(' ')
  const initials = givenTokens
    .map((t) => (t.endsWith('.') ? t : `${t.charAt(0).toUpperCase()}.`))
    .join(' ')

  return { firstNames, lastName, initials }
}

/**
 * Formats author list according to APA 7th edition rules.
 */
export function formatAuthorsApa(authors: string[]): string {
  const clean = authors.map((a) => a.trim()).filter(Boolean)
  if (clean.length === 0) return ''

  const formatted = clean.map((author) => {
    const { lastName, initials } = parseAuthorName(author)
    if (!initials) return lastName
    return `${lastName}, ${initials}`
  })

  if (formatted.length === 1) return formatted[0]
  if (formatted.length === 2) return `${formatted[0]}, & ${formatted[1]}`
  if (formatted.length <= 20) {
    return `${formatted.slice(0, -1).join(', ')}, & ${formatted[formatted.length - 1]}`
  }

  // APA 7th for > 20 authors: list first 19, ellipsis, then final author
  return `${formatted.slice(0, 19).join(', ')}, ... ${formatted[formatted.length - 1]}`
}

/**
 * Formats author list according to IEEE rules.
 */
export function formatAuthorsIeee(authors: string[]): string {
  const clean = authors.map((a) => a.trim()).filter(Boolean)
  if (clean.length === 0) return ''

  // IEEE rule: if more than 6 authors, list first author followed by "et al."
  if (clean.length > 6) {
    const { lastName, initials } = parseAuthorName(clean[0])
    const firstAuthor = initials ? `${initials} ${lastName}` : lastName
    return `${firstAuthor} et al.`
  }

  const formatted = clean.map((author) => {
    const { lastName, initials } = parseAuthorName(author)
    if (!initials) return lastName
    return `${initials} ${lastName}`
  })

  if (formatted.length === 1) return formatted[0]
  if (formatted.length === 2) return `${formatted[0]} and ${formatted[1]}`
  return `${formatted.slice(0, -1).join(', ')}, and ${formatted[formatted.length - 1]}`
}

/**
 * Generates an APA 7th edition citation string.
 */
export function generateApaCitation(dataset: DatasetMetadata): CitationResult {
  const citation = dataset.citation
  const authors = citation?.authors?.filter(Boolean) || []
  const title = citation?.paper_title || dataset.name
  const year = extractPublicationYear(dataset)
  const doi = cleanDoi(citation?.doi)
  const url = citation?.paper_url || dataset.homepage_url

  if (authors.length === 0 && !citation?.paper_title) {
    return {
      citationText: null,
      warning:
        'Author and publication metadata are not specified for this record. An authoritative APA 7th citation cannot be reliably generated.',
    }
  }

  const authorPart = authors.length > 0 ? formatAuthorsApa(authors) : (dataset.publisher?.name || dataset.name)
  const yearPart = year ? `(${year})` : '(n.d.)'
  const titlePart = title.endsWith('.') ? title : `${title}.`

  let sourcePart = ''
  if (doi) {
    sourcePart = ` https://doi.org/${doi}`
  } else if (url) {
    sourcePart = ` ${url}`
  }

  const citationText = `${authorPart} ${yearPart}. ${titlePart}${sourcePart}`.trim()
  return { citationText, warning: null }
}

/**
 * Generates an IEEE citation string.
 */
export function generateIeeeCitation(dataset: DatasetMetadata): CitationResult {
  const citation = dataset.citation
  const authors = citation?.authors?.filter(Boolean) || []
  const title = citation?.paper_title || dataset.name
  const year = extractPublicationYear(dataset)
  const doi = cleanDoi(citation?.doi)
  const url = citation?.paper_url || dataset.homepage_url

  if (authors.length === 0 && !citation?.paper_title) {
    return {
      citationText: null,
      warning:
        'Author and publication metadata are not specified for this record. An authoritative IEEE citation cannot be reliably generated.',
    }
  }

  const authorPart = authors.length > 0 ? formatAuthorsIeee(authors) : (dataset.publisher?.name || dataset.name)
  const cleanTitle = title.replace(/[.,"“”]+$/, '')
  const titlePart = `"${cleanTitle},"`
  const yearPart = year ? ` ${year}.` : ''

  let sourcePart = ''
  if (doi) {
    sourcePart = ` doi: ${doi}.`
  } else if (url) {
    sourcePart = ` [Online]. Available: ${url}.`
  }

  const citationText = `${authorPart}, ${titlePart}${yearPart}${sourcePart}`.trim()
  return { citationText, warning: null }
}

/**
 * Retrieves existing BibTeX or synthesizes a minimal fallback if authors and title exist.
 */
export function generateBibtexCitation(dataset: DatasetMetadata): CitationResult {
  if (dataset.citation?.bibtex && dataset.citation.bibtex.trim().length > 0) {
    return {
      citationText: dataset.citation.bibtex.trim(),
      warning: null,
      isSynthesized: false,
    }
  }

  const authors = dataset.citation?.authors?.filter(Boolean) || []
  const title = dataset.citation?.paper_title || dataset.name
  const year = extractPublicationYear(dataset)
  const url = dataset.citation?.paper_url || dataset.homepage_url
  const doi = cleanDoi(dataset.citation?.doi)

  if (authors.length === 0 && !dataset.citation?.paper_title) {
    return {
      citationText: null,
      warning:
        'BibTeX entry is not declared and sufficient author/title metadata is unavailable to generate one.',
    }
  }

  const authorString = authors.length > 0 ? authors.join(' and ') : dataset.publisher?.name || 'Unknown'
  const lines = [
    `@misc{${dataset.slug},`,
    `  title = {${title}},`,
    `  author = {${authorString}},`,
  ]

  if (year) {
    lines.push(`  year = {${year}},`)
  }
  if (doi) {
    lines.push(`  doi = {${doi}},`)
  }
  if (url) {
    lines.push(`  url = {${url}},`)
  }

  lines.push(`  howpublished = {\\url{${url || dataset.homepage_url}}}`)
  lines.push('}')

  return {
    citationText: lines.join('\n'),
    warning: null,
    isSynthesized: true,
  }
}

/**
 * Universal dispatcher for academic citation export across formats.
 */
export function formatCitation(dataset: DatasetMetadata, format: CitationFormat): CitationResult {
  switch (format) {
    case 'bibtex':
      return generateBibtexCitation(dataset)
    case 'apa':
      return generateApaCitation(dataset)
    case 'ieee':
      return generateIeeeCitation(dataset)
    default:
      return { citationText: null, warning: `Unsupported citation format: ${format}` }
  }
}

/**
 * Triggers browser download of citation text with the appropriate file extension.
 */
export function downloadCitationFile(filename: string, content: string): void {
  if (typeof window === 'undefined' || typeof document === 'undefined') return

  const blob = new Blob([content], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}
