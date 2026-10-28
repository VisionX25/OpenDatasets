import React from 'react'
import { BrowserRouter, Routes, Route, Navigate, useParams } from 'react-router-dom'
import { Layout } from './components/Layout'
import { HomePage } from './pages/HomePage'
import { ExplorePage } from './pages/ExplorePage'
import { DatasetsPage } from './pages/DatasetsPage'
import { DatasetDetailPage } from './pages/DatasetDetailPage'
import { AboutPage } from './pages/AboutPage'
import { isDatasetSlug } from './services/catalogService'

/**
 * Route dispatcher for /datasets/:param:
 * - If :param matches a known dataset record, renders DatasetDetailPage.
 * - Otherwise renders DatasetsPage (which validates categorySlug and handles category results or invalid category state).
 */
const DatasetsRouteDispatcher: React.FC = () => {
  const { param } = useParams<{ param: string }>()
  if (isDatasetSlug(param)) {
    return <DatasetDetailPage />
  }
  return <DatasetsPage />
}

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<HomePage />} />
          <Route path="explore" element={<ExplorePage />} />
          <Route path="datasets" element={<DatasetsPage />} />
          <Route path="datasets/:param" element={<DatasetsRouteDispatcher />} />
          <Route path="dataset/:slug" element={<DatasetDetailPage />} />
          <Route path="about" element={<AboutPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App
