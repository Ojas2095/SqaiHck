import { BrowserRouter, Routes, Route, Outlet } from 'react-router-dom'
import Sidebar from './components/Sidebar'
import TopBar from './components/TopBar'
import Dashboard from './pages/Dashboard'
import EHRCreator from './pages/EHRCreator'
import OutbreakIntelligence from './pages/OutbreakIntelligence'
import TreatmentEngine from './pages/TreatmentEngine'
import Analytics from './pages/Analytics'
import PatientLayout from './components/PatientLayout'
import PatientOnboarding from './pages/PatientOnboarding'

const PractitionerLayout = () => (
  <div className="app-layout">
    <Sidebar />
    <div className="main-content">
      <TopBar />
      <div className="page-content">
        <Outlet />
      </div>
    </div>
    <div className="noise-overlay" />
  </div>
)

function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Patient App (Light Theme) */}
        <Route path="/patient" element={<PatientLayout />}>
          <Route index element={<PatientOnboarding />} />
        </Route>

        {/* Practitioner App (Dark Theme) */}
        <Route path="/" element={<PractitionerLayout />}>
          <Route index element={<Dashboard />} />
          <Route path="ehr" element={<EHRCreator />} />
          <Route path="outbreak" element={<OutbreakIntelligence />} />
          <Route path="treatment" element={<TreatmentEngine />} />
          <Route path="analytics" element={<Analytics />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App
