import React from 'react'
import { BrowserRouter, Routes, Route, Navigate, useParams } from 'react-router-dom'
import { Layout } from './components/Layout'
import { HomePage } from './pages/HomePage'
import { ExplorePage } from './pages/ExplorePage'
import { DatasetsPage } from './pages/DatasetsPage'
import { DatasetDetailPage } from './pages/DatasetDetailPage'
import { AboutPage } from './pages/AboutPage'
import { SubmitDatasetPage } from './pages/SubmitDatasetPage'
import { isCategoryId } from './utils/datasetFilters'

/**
 * Route dispatcher for legacy /datasets/:param URLs:
 * - If :param matches a known category ID (e.g. /datasets/computer-vision), renders DatasetsPage.
 * - Otherwise redirects to the canonical /dataset/:slug detail page, preserving existing
 *   /datasets/:slug deep links and query parameters without depending on a hardcoded slug list.
 */
export const DatasetsRouteDispatcher: React.FC = () => {
  const { param } = useParams<{ param: string }>()

  if (!param) {
    return <Navigate to="/datasets" replace />
  }

  if (isCategoryId(param)) {
    return <DatasetsPage />
  }

  // Compatible routing for legacy /datasets/:slug deep links:
  // Renders DatasetDetailPage directly (effectiveSlug binds to :param).
  return <DatasetDetailPage />
}

export const App: React.FC = () => {
  return (
    <BrowserRouter basename={import.meta.env.BASE_URL.replace(/\/$/, '') || '/'}>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<HomePage />} />
          <Route path="explore" element={<ExplorePage />} />
          <Route path="datasets" element={<DatasetsPage />} />
          <Route path="datasets/:param" element={<DatasetsRouteDispatcher />} />
          <Route path="dataset/:slug" element={<DatasetDetailPage />} />
          <Route path="submit" element={<SubmitDatasetPage />} />
          <Route path="about" element={<AboutPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App
