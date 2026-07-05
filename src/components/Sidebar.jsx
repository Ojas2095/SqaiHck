import { useState, useEffect } from 'react'
import { NavLink, useLocation, useNavigate } from 'react-router-dom'
import {
  LayoutDashboard,
  Mic,
  AlertTriangle,
  Stethoscope,
  BarChart3,
  ChevronLeft,
  ChevronRight,
  Leaf,
  Settings,
  HelpCircle,
  LogOut,
  Users,
  X,
  Bell,
  Shield,
  Moon,
  Sun,
  Globe,
  Database,
  Lock,
  Mail,
  MessageSquare,
  BookOpen,
  ExternalLink
} from 'lucide-react'
import './Sidebar.css'

const navItems = [
  { path: '/', label: 'Dashboard', icon: LayoutDashboard, description: 'Overview & Analytics' },
  { path: '/ehr', label: 'Voice EHR', icon: Mic, description: 'Create Health Records' },
  { path: '/outbreak', label: 'Outbreak Intel', icon: AlertTriangle, description: 'Early Warning System' },
  { path: '/treatment', label: 'Treatment AI', icon: Stethoscope, description: 'AYUSH Recommendations' },
  { path: '/analytics', label: 'Analytics', icon: BarChart3, description: 'Model Performance' },
]

export default function Sidebar() {
  const [collapsed, setCollapsed] = useState(false)
  const [showSettings, setShowSettings] = useState(false)
  const [showHelp, setShowHelp] = useState(false)
  const location = useLocation()
  const navigate = useNavigate()

  return (
    <>
      <aside className={`sidebar ${collapsed ? 'collapsed' : ''}`}>
        {/* Brand */}
        <div className="sidebar-brand">
          <div className="brand-icon">
            <Leaf size={22} />
          </div>
          {!collapsed && (
            <div className="brand-text">
              <span className="brand-name">AYUSH AI</span>
              <span className="brand-sub">Intelligence Platform</span>
            </div>
          )}
        </div>

        {/* Navigation */}
        <nav className="sidebar-nav">
          <div className="nav-label">{!collapsed && 'MAIN MENU'}</div>
          {navItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) =>
                `nav-item ${isActive ? 'active' : ''}`
              }
              end={item.path === '/'}
              title={collapsed ? item.label : ''}
            >
              <div className="nav-icon-wrapper">
                <item.icon size={20} />
              </div>
              {!collapsed && (
                <div className="nav-text">
                  <span className="nav-label-text">{item.label}</span>
                  <span className="nav-desc">{item.description}</span>
                </div>
              )}
              {!collapsed && location.pathname === item.path && (
                <div className="nav-active-dot" />
              )}
            </NavLink>
          ))}

          {/* Patient Portal Link */}
          <div className="nav-label nav-label-section">{!collapsed && 'PATIENT'}</div>
          <NavLink
            to="/patient"
            className={({ isActive }) => `nav-item nav-item-patient ${isActive ? 'active' : ''}`}
            title={collapsed ? 'Patient Portal' : ''}
          >
            <div className="nav-icon-wrapper patient-icon-wrapper">
              <Users size={20} />
            </div>
            {!collapsed && (
              <div className="nav-text">
                <span className="nav-label-text">Patient Portal</span>
                <span className="nav-desc">Onboarding & Intake</span>
              </div>
            )}
          </NavLink>
        </nav>

        {/* Bottom Actions */}
        <div className="sidebar-footer">
          <button
            className="nav-item footer-item"
            title={collapsed ? 'Settings' : ''}
            onClick={() => setShowSettings(true)}
          >
            <div className="nav-icon-wrapper"><Settings size={18} /></div>
            {!collapsed && <span className="nav-label-text">Settings</span>}
          </button>
          <button
            className="nav-item footer-item"
            title={collapsed ? 'Help' : ''}
            onClick={() => setShowHelp(true)}
          >
            <div className="nav-icon-wrapper"><HelpCircle size={18} /></div>
            {!collapsed && <span className="nav-label-text">Help Center</span>}
          </button>

          {/* User Profile */}
          {!collapsed && (
            <div className="sidebar-user">
              <div className="user-avatar">DR</div>
              <div className="user-info">
                <span className="user-name">Dr. Rajesh Kumar</span>
                <span className="user-role">AYUSH Practitioner</span>
              </div>
              <LogOut
                size={16}
                className="user-logout"
                onClick={() => {
                  if (window.confirm('Are you sure you want to log out?')) {
                    navigate('/')
                  }
                }}
              />
            </div>
          )}
        </div>

        {/* Collapse Toggle */}
        <button
          className="sidebar-toggle"
          onClick={() => setCollapsed(!collapsed)}
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {collapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
        </button>
      </aside>

      {/* ── Settings Modal ── */}
      {showSettings && (
        <div className="modal-overlay" onClick={() => setShowSettings(false)}>
          <div className="modal-panel" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h3><Settings size={18} /> Settings</h3>
              <button className="modal-close" onClick={() => setShowSettings(false)}>
                <X size={18} />
              </button>
            </div>
            <div className="modal-body">
              <div className="settings-group">
                <h4 className="settings-group-title">General</h4>
                <div className="setting-item">
                  <div className="setting-info">
                    <Globe size={16} />
                    <div>
                      <span className="setting-label">Language</span>
                      <span className="setting-desc">Platform display language</span>
                    </div>
                  </div>
                  <select className="setting-select">
                    <option>English</option>
                    <option>हिन्दी</option>
                    <option>தமிழ்</option>
                    <option>తెలుగు</option>
                  </select>
                </div>
                <div className="setting-item">
                  <div className="setting-info">
                    <Moon size={16} />
                    <div>
                      <span className="setting-label">Dark Mode</span>
                      <span className="setting-desc">Toggle dark/light theme</span>
                    </div>
                  </div>
                  <label className="toggle-switch">
                    <input 
                      type="checkbox" 
                      checked={isDarkMode} 
                      onChange={(e) => setIsDarkMode(e.target.checked)} 
                    />
                    <span className="toggle-slider" />
                  </label>
                </div>
              </div>

              <div className="settings-group">
                <h4 className="settings-group-title">Notifications</h4>
                <div className="setting-item">
                  <div className="setting-info">
                    <Bell size={16} />
                    <div>
                      <span className="setting-label">Outbreak Alerts</span>
                      <span className="setting-desc">Get notified on new outbreaks</span>
                    </div>
                  </div>
                  <label className="toggle-switch">
                    <input type="checkbox" defaultChecked />
                    <span className="toggle-slider" />
                  </label>
                </div>
                <div className="setting-item">
                  <div className="setting-info">
                    <Mail size={16} />
                    <div>
                      <span className="setting-label">Email Reports</span>
                      <span className="setting-desc">Weekly summary to your email</span>
                    </div>
                  </div>
                  <label className="toggle-switch">
                    <input type="checkbox" />
                    <span className="toggle-slider" />
                  </label>
                </div>
              </div>

              <div className="settings-group">
                <h4 className="settings-group-title">Data & Privacy</h4>
                <div className="setting-item">
                  <div className="setting-info">
                    <Database size={16} />
                    <div>
                      <span className="setting-label">Data Retention</span>
                      <span className="setting-desc">How long to keep records</span>
                    </div>
                  </div>
                  <select className="setting-select">
                    <option>1 Year</option>
                    <option>2 Years</option>
                    <option>5 Years</option>
                    <option>Forever</option>
                  </select>
                </div>
                <div className="setting-item">
                  <div className="setting-info">
                    <Lock size={16} />
                    <div>
                      <span className="setting-label">Two-Factor Auth</span>
                      <span className="setting-desc">Extra security for your account</span>
                    </div>
                  </div>
                  <label className="toggle-switch">
                    <input type="checkbox" defaultChecked />
                    <span className="toggle-slider" />
                  </label>
                </div>
              </div>
            </div>
            <div className="modal-footer">
              <button className="modal-btn-secondary" onClick={() => setShowSettings(false)}>Cancel</button>
              <button className="modal-btn-primary" onClick={() => setShowSettings(false)}>Save Changes</button>
            </div>
          </div>
        </div>
      )}

      {/* ── Help Center Modal ── */}
      {showHelp && (
        <div className="modal-overlay" onClick={() => setShowHelp(false)}>
          <div className="modal-panel" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h3><HelpCircle size={18} /> Help Center</h3>
              <button className="modal-close" onClick={() => setShowHelp(false)}>
                <X size={18} />
              </button>
            </div>
            <div className="modal-body">
              <div className="help-search-wrapper">
                <input
                  type="text"
                  className="help-search"
                  placeholder="Search help articles..."
                />
              </div>

              <div className="help-cards">
                <a href="#" className="help-card" onClick={e => e.preventDefault()}>
                  <div className="help-card-icon">
                    <BookOpen size={20} />
                  </div>
                  <div>
                    <h5>Getting Started</h5>
                    <p>Learn the basics of the AYUSH AI platform</p>
                  </div>
                </a>
                <a href="#" className="help-card" onClick={e => e.preventDefault()}>
                  <div className="help-card-icon">
                    <Mic size={20} />
                  </div>
                  <div>
                    <h5>Voice EHR Guide</h5>
                    <p>How to create records using voice input</p>
                  </div>
                </a>
                <a href="#" className="help-card" onClick={e => e.preventDefault()}>
                  <div className="help-card-icon">
                    <AlertTriangle size={20} />
                  </div>
                  <div>
                    <h5>Outbreak Alerts</h5>
                    <p>Understanding the early warning system</p>
                  </div>
                </a>
                <a href="#" className="help-card" onClick={e => e.preventDefault()}>
                  <div className="help-card-icon">
                    <Shield size={20} />
                  </div>
                  <div>
                    <h5>Data Privacy</h5>
                    <p>How we protect patient data</p>
                  </div>
                </a>
              </div>

              <div className="help-section">
                <h4 className="settings-group-title">Frequently Asked Questions</h4>
                <details className="faq-item">
                  <summary>How accurate is the AI treatment recommendation?</summary>
                  <p>Our model achieves 94.2% accuracy on multi-class classification across AYUSH systems, validated against a panel of expert practitioners.</p>
                </details>
                <details className="faq-item">
                  <summary>Which languages does Voice EHR support?</summary>
                  <p>Currently English, Hindi, Tamil, Telugu, Bengali, Marathi, Gujarati, and Kannada are supported for voice-to-text EHR creation.</p>
                </details>
                <details className="faq-item">
                  <summary>How is patient data protected?</summary>
                  <p>All data is encrypted at rest (AES-256) and in transit (TLS 1.3). We comply with India's Digital Personal Data Protection Act 2023.</p>
                </details>
              </div>

              <div className="help-contact">
                <p>Still need help?</p>
                <div className="help-contact-buttons">
                  <button className="modal-btn-secondary" onClick={() => alert('Live Chat feature will be available in v2.0!')}>
                    <MessageSquare size={14} /> Live Chat
                  </button>
                  <button className="modal-btn-secondary" onClick={() => alert('Support email copied to clipboard! (support@ayushai.com)')}>
                    <Mail size={14} /> Email Support
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
