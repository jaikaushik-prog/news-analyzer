import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import SignalFeed from './pages/SignalFeed'
import SectorView from './pages/SectorView'
import SearchResults from './pages/SearchResults'

function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<SignalFeed />} />
        <Route path="sector/:sectorName" element={<SectorView />} />
        <Route path="search" element={<SearchResults />} />
      </Route>
    </Routes>
  )
}

export default App
