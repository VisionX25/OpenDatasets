import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderToString } from 'react-dom/server'
import { MemoryRouter } from 'react-router-dom'
import { HomePage } from './HomePage'

describe('HomePage (Task 45 Dynamic Catalog Statistics)', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('renders dynamic milestone count when initialCount is provided', () => {
    const html = renderToString(
      <MemoryRouter>
        <HomePage initialCount={625} />
      </MemoryRouter>,
    )

    expect(html).toContain('Milestone reached: 625 research dataset records · November 2026')
    expect(html).not.toContain('600 research dataset records')
  })

  it('renders fallback milestone text when count is not yet loaded', () => {
    const html = renderToString(
      <MemoryRouter>
        <HomePage />
      </MemoryRouter>,
    )

    expect(html).toContain('Milestone reached: research dataset records · November 2026')
  })

  it('preserves existing hero, feature pillars, architecture roadmap, and submit sections', () => {
    const html = renderToString(
      <MemoryRouter>
        <HomePage initialCount={625} />
      </MemoryRouter>,
    )

    expect(html).toContain('Discover &amp; Explore')
    expect(html).toContain('Machine Learning Datasets')
    expect(html).toContain('Explore Datasets')
    expect(html).toContain('About OpenDatasets')
    expect(html).toContain('Built for Modern Machine Learning Workflows')
    expect(html).toContain('Curated Discovery')
    expect(html).toContain('Metadata Validation')
    expect(html).toContain('Interactive Exploration')
    expect(html).toContain('Architecture &amp; Roadmap')
    expect(html).toContain('Contribute to OpenDatasets')
    expect(html).toContain('Submit Dataset')
  })
})
