import type { DatasetMetadata, LicenseStatus, CategoryId } from '../types/dataset'
import { fetchCatalog } from './catalogService'
import {
  filterDatasets,
  getAvailableModalities,
  getAvailableTasks,
  getAvailableLicenseStatuses,
  getAvailablePublicationYears,
  countDatasetsPerCategory,
  type DatasetFilterCriteria,
} from '../utils/datasetFilters'

export interface SearchFacetOptions {
  availableModalities: string[]
  availableTasks: string[]
  availableLicenses: LicenseStatus[]
  availableYears: string[]
  categoryCounts: Record<CategoryId, number>
}

export interface DatasetQueryOptions {
  criteria: DatasetFilterCriteria
  offset?: number
  limit?: number
  forceReload?: boolean
  datasets?: DatasetMetadata[]
}

export interface PaginatedDatasetResult {
  items: DatasetMetadata[]
  totalMatches: number
  totalCatalogSize: number
  hasMore: boolean
  facets: SearchFacetOptions
}

/**
 * Data-access abstraction layer for searching, filtering, and paginating datasets.
 * Currently backed by the static catalog, but designed so a future backend API
 * or remote search index can replace the data source without rewriting page UI components.
 */
export async function queryDatasets(
  options: DatasetQueryOptions,
): Promise<PaginatedDatasetResult> {
  const catalog =
    options.datasets ?? (await fetchCatalog({ forceReload: options.forceReload }))

  // Deterministic stable sort by dataset name
  const sortedCatalog = [...catalog].sort((a, b) => a.name.localeCompare(b.name))

  const filtered = filterDatasets(sortedCatalog, options.criteria)
  const offset = options.offset ?? 0
  const limit = options.limit ?? 24

  const items = filtered.slice(offset, offset + limit)
  const hasMore = offset + items.length < filtered.length

  const facets: SearchFacetOptions = {
    availableModalities: getAvailableModalities(catalog),
    availableTasks: getAvailableTasks(catalog),
    availableLicenses: getAvailableLicenseStatuses(catalog),
    availableYears: getAvailablePublicationYears(catalog),
    categoryCounts: countDatasetsPerCategory(catalog),
  }

  return {
    items,
    totalMatches: filtered.length,
    totalCatalogSize: catalog.length,
    hasMore,
    facets,
  }
}
