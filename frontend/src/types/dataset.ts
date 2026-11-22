/**
 * TypeScript type definitions corresponding to schemas/dataset.v1.schema.json.
 */

export type DatasetModality =
  | 'vision'
  | 'nlp'
  | 'audio'
  | 'tabular'
  | 'multimodal'
  | 'reinforcement-learning'
  | 'graph'
  | 'time-series'
  | 'sensor'
  | '3d'
  | 'other'

export type PublisherType =
  | 'academic'
  | 'industry'
  | 'government'
  | 'community'
  | 'individual'
  | 'unknown'

export interface Publisher {
  name: string
  type: PublisherType
  url?: string
}

export type LicenseStatus =
  | 'verified_open'
  | 'verified_non_commercial'
  | 'custom_permissive'
  | 'unspecified_by_source'
  | 'proprietary'
  | 'public_domain'
  | 'unknown'

export type CommercialUseStatus = 'allowed' | 'forbidden' | 'unknown'

export interface DatasetLicense {
  status: LicenseStatus
  name: string
  spdx_id?: string | null
  url?: string
  notes?: string
  commercial_use?: CommercialUseStatus
}

export type ReferenceType =
  | 'official_website'
  | 'original_paper'
  | 'repository'
  | 'dataset_card'
  | 'documentation'
  | 'archive'
  | 'other'

export interface SourceReference {
  title: string
  url: string
  type: ReferenceType
  notes?: string
}

export type VerificationStatus = 'verified' | 'provisional' | 'unverified'

export interface DatasetVerification {
  status: VerificationStatus
  verified_by?: string | null
  verified_date?: string | null
  notes?: string
}

export type DataSizeUnit = 'B' | 'KB' | 'MB' | 'GB' | 'TB' | 'PB'
export type SizeStatus = 'verified' | 'estimated' | 'unknown'

export interface DatasetSize {
  amount?: number
  unit?: DataSizeUnit
  file_formats?: string[]
  status: SizeStatus
  notes?: string
}

export type SampleCountStatus = 'verified' | 'estimated' | 'unknown'

export interface DatasetBreakdownItem {
  label: string
  value: number
  unit?: string
}

export interface DatasetSampleCount {
  total?: number
  splits?: Record<string, number>
  unit?: string
  status: SampleCountStatus
  breakdown?: DatasetBreakdownItem[]
  partition_completeness?: 'complete' | 'partial' | 'unspecified'
  partition_overlap?: 'disjoint' | 'overlapping' | 'unspecified'
}

export interface DatasetDates {
  published?: string
  last_updated?: string
}

export interface DatasetCitation {
  paper_title?: string
  paper_url?: string
  authors?: string[]
  bibtex?: string
  doi?: string
}

export interface DatasetProvenance {
  collection_method?: string
  curation_notes?: string
  data_sources?: string[]
}

export interface DatasetMetadata {
  schema_version: string
  id: string
  slug: string
  name: string
  description: string
  homepage_url: string
  publisher: Publisher
  modalities: DatasetModality[]
  tasks: string[]
  tags: string[]
  license: DatasetLicense
  source_references: SourceReference[]
  verification: DatasetVerification
  size?: DatasetSize
  sample_count?: DatasetSampleCount
  languages?: string[]
  dates?: DatasetDates
  citation?: DatasetCitation
  geographic_coverage?: string[]
  provenance?: DatasetProvenance
  breakdown?: DatasetBreakdownItem[]
}

export type CategoryId =
  | 'computer-vision'
  | 'natural-language-processing'
  | 'audio-speech'
  | 'tabular-time-series'
  | 'multimodal-generative'
  | 'evaluation-benchmarks'

export interface CategoryDefinition {
  id: CategoryId
  name: string
  description: string
}

/**
 * Safely aggregates quantitative breakdown items from both root-level
 * and sample_count breakdown properties without duplicates or data loss.
 */
export function getDatasetBreakdowns(dataset: Partial<DatasetMetadata>): DatasetBreakdownItem[] {
  const rootItems = dataset.breakdown || []
  const sampleCountItems = dataset.sample_count?.breakdown || []

  if (rootItems.length === 0) return sampleCountItems
  if (sampleCountItems.length === 0) return rootItems

  const combined = [...rootItems]
  const seen = new Set(rootItems.map((it) => `${it.label.toLowerCase()}::${it.value}`))

  for (const item of sampleCountItems) {
    const key = `${item.label.toLowerCase()}::${item.value}`
    if (!seen.has(key)) {
      seen.add(key)
      combined.push(item)
    }
  }
  return combined
}

