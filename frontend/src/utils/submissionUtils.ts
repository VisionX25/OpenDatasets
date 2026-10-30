import { CATEGORIES } from './datasetFilters'

export interface SubmissionFormData {
  name: string
  sourceUrl: string
  category: string
  task: string
  description: string
  doi: string
  license: string
  paperUrl: string
  notes: string
}

export const INITIAL_SUBMISSION_FORM: SubmissionFormData = {
  name: '',
  sourceUrl: '',
  category: '',
  task: '',
  description: '',
  doi: '',
  license: '',
  paperUrl: '',
  notes: '',
}

export function isValidHttpUrl(candidate: string): boolean {
  if (!candidate || typeof candidate !== 'string') return false
  try {
    const parsed = new URL(candidate)
    return parsed.protocol === 'http:' || parsed.protocol === 'https:'
  } catch {
    return false
  }
}

export function formatSubmissionMarkdown(data: SubmissionFormData): string {
  const categoryDef = CATEGORIES.find((c) => c.id === data.category)
  const categoryName = categoryDef ? categoryDef.name : data.category || 'Unspecified'

  return [
    '### Dataset name',
    data.name.trim(),
    '',
    '### Original publisher or official dataset URL',
    data.sourceUrl.trim(),
    '',
    '### Modality, task, and usefulness',
    `**Category:** ${categoryName}`,
    `**Primary Task:** ${data.task.trim()}`,
    '**Description:**',
    data.description.trim(),
    '',
    '### License and access conditions',
    data.license.trim() || 'Unknown / Not specified by publisher',
    '',
    '### Additional evidence and limitations',
    `- **DOI:** ${data.doi.trim() || 'N/A'}`,
    `- **Supporting Paper URL:** ${data.paperUrl.trim() || 'N/A'}`,
    '- **Additional Notes / Limitations:**',
    data.notes.trim() || 'None provided',
  ].join('\n')
}

export const DEFAULT_MAX_URL_LENGTH = 2000

export interface GitHubIssueUrlResult {
  url: string
  isFallback: boolean
  urlLength: number
  fieldValues: {
    template: string
    title: string
    name: string
    source: string
    usefulness: string
    license: string
    evidence: string
  }
}

export function buildGitHubIssueUrl(
  data: SubmissionFormData,
  maxLength: number = DEFAULT_MAX_URL_LENGTH,
): GitHubIssueUrlResult {
  const categoryDef = CATEGORIES.find((c) => c.id === data.category)
  const categoryName = categoryDef ? categoryDef.name : data.category || 'Unspecified'

  const cleanName = data.name.trim()
  const title = cleanName.startsWith('[Dataset]:')
    ? cleanName
    : `[Dataset]: ${cleanName || 'New Dataset Suggestion'}`
  const name = cleanName
  const source = data.sourceUrl.trim()

  const usefulness = [
    `**Category:** ${categoryName}`,
    `**Primary Task:** ${data.task.trim() || 'Unspecified'}`,
    '',
    '**Description:**',
    data.description.trim() || 'No description provided',
  ].join('\n')

  const license = data.license.trim() || 'Unknown / Not specified by publisher'

  const evidence = [
    `- **DOI:** ${data.doi.trim() || 'N/A'}`,
    `- **Supporting Paper URL:** ${data.paperUrl.trim() || 'N/A'}`,
    '- **Additional Notes / Limitations:**',
    data.notes.trim() || 'None provided',
  ].join('\n')

  const baseUrl = 'https://github.com/VisionX25/OpenDatasets/issues/new'

  const fullParams = new URLSearchParams()
  fullParams.set('template', 'dataset_suggestion.yml')
  fullParams.set('title', title)
  fullParams.set('name', name)
  fullParams.set('source', source)
  fullParams.set('usefulness', usefulness)
  fullParams.set('license', license)
  fullParams.set('evidence', evidence)

  const fullUrl = `${baseUrl}?${fullParams.toString()}`

  const fieldValues = {
    template: 'dataset_suggestion.yml',
    title,
    name,
    source,
    usefulness,
    license,
    evidence,
  }

  if (fullUrl.length <= maxLength) {
    return {
      url: fullUrl,
      isFallback: false,
      urlLength: fullUrl.length,
      fieldValues,
    }
  }

  // Graceful fallback URL: retain template and title to avoid 414 URI Too Long error
  const fallbackParams = new URLSearchParams()
  fallbackParams.set('template', 'dataset_suggestion.yml')
  fallbackParams.set('title', title)

  const fallbackUrl = `${baseUrl}?${fallbackParams.toString()}`

  return {
    url: fallbackUrl,
    isFallback: true,
    urlLength: fullUrl.length,
    fieldValues,
  }
}
