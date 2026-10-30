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
