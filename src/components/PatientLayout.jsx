import { Outlet } from 'react-router-dom'
import { HelpCircle } from 'lucide-react'
import './PatientLayout.css'

export default function PatientLayout() {
  return (
    <div className="patient-layout">
      <header className="patient-header">
        <a href="/patient" className="ph-logo">
          <div className="ph-logo-icon">🌿</div>
          <div className="ph-logo-text">
            <span>AYUSH Wellness</span>
            <span>Ministry of Ayush</span>
          </div>
        </a>
        <button className="ph-help-btn">
          <HelpCircle size={15} />
          Help
        </button>
      </header>
      <main className="patient-content">
        <Outlet />
      </main>
      <footer className="patient-footer">
        <p>© 2026 AYUSH AI Platform — Ministry of Ayush, Government of India</p>
      </footer>
    </div>
  )
}
