import { useState, useRef, useEffect } from 'react'
import { Search, Bell, Globe, Zap, X, Check } from 'lucide-react'
import { useLocation } from 'react-router-dom'
import './TopBar.css'

const pageTitles = {
  '/': 'Dashboard',
  '/ehr': 'Voice EHR Creator',
  '/outbreak': 'Outbreak Intelligence',
  '/treatment': 'Treatment Engine',
  '/analytics': 'Analytics & Explainability',
}

const languages = [
  { code: 'en', label: 'English', native: 'English' },
  { code: 'hi', label: 'Hindi', native: 'हिन्दी' },
  { code: 'ta', label: 'Tamil', native: 'தமிழ்' },
  { code: 'te', label: 'Telugu', native: 'తెలుగు' },
  { code: 'bn', label: 'Bengali', native: 'বাংলা' },
  { code: 'mr', label: 'Marathi', native: 'मराठी' },
]

const notifications = [
  { id: 1, text: 'Dengue outbreak alert — Rajasthan escalated to Critical', time: '5 min ago', read: false },
  { id: 2, text: 'New treatment model v3.2.2 available for deployment', time: '1 hr ago', read: false },
  { id: 3, text: 'Weekly analytics report generated successfully', time: '3 hr ago', read: false },
  { id: 4, text: 'Patient EHR batch upload completed — 142 records', time: '6 hr ago', read: true },
  { id: 5, text: 'System maintenance scheduled for Sunday 2 AM IST', time: '1 day ago', read: true },
]

export default function TopBar() {
  const location = useLocation()
  const currentPage = pageTitles[location.pathname] || 'Dashboard'
  const [showLangDropdown, setShowLangDropdown] = useState(false)
  const [showNotifications, setShowNotifications] = useState(false)
  const [selectedLang, setSelectedLang] = useState('en')
  const [notifs, setNotifs] = useState(notifications)

  const langRef = useRef(null)
  const notifRef = useRef(null)

  // Close dropdowns on outside click
  useEffect(() => {
    const handleClick = (e) => {
      if (langRef.current && !langRef.current.contains(e.target)) setShowLangDropdown(false)
      if (notifRef.current && !notifRef.current.contains(e.target)) setShowNotifications(false)
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [])

  const unreadCount = notifs.filter(n => !n.read).length

  const markAllRead = () => {
    setNotifs(prev => prev.map(n => ({ ...n, read: true })))
  }

  return (
    <header className="topbar">
      <div className="topbar-left">
        <div className="breadcrumbs">
          <span className="breadcrumb-root">AYUSH AI</span>
          <span className="breadcrumb-sep">/</span>
          <span className="breadcrumb-current">{currentPage}</span>
        </div>
      </div>

      <div className="topbar-center">
        <div className="search-wrapper">
          <Search size={16} className="search-icon" />
          <input
            type="text"
            className="search-input"
            placeholder="Search patients, reports, alerts..."
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                alert(`Search for "${e.target.value}" will be implemented in v2.0`);
              }
            }}
          />
          <kbd className="search-shortcut">⌘K</kbd>
        </div>
      </div>

      <div className="topbar-right">
        <div className="topbar-status">
          <Zap size={14} />
          <span>AI Online</span>
        </div>

        {/* Language Selector */}
        <div className="topbar-dropdown-wrapper" ref={langRef}>
          <button
            className={`topbar-btn ${showLangDropdown ? 'active' : ''}`}
            title="Language"
            onClick={() => {
              setShowLangDropdown(!showLangDropdown)
              setShowNotifications(false)
            }}
          >
            <Globe size={18} />
          </button>
          {showLangDropdown && (
            <div className="topbar-dropdown lang-dropdown">
              <div className="dropdown-header">
                <span>Display Language</span>
              </div>
              {languages.map(lang => (
                <button
                  key={lang.code}
                  className={`dropdown-item ${selectedLang === lang.code ? 'selected' : ''}`}
                  onClick={() => {
                    setSelectedLang(lang.code)
                    setShowLangDropdown(false)
                  }}
                >
                  <span className="dropdown-item-text">
                    <span>{lang.native}</span>
                    <span className="dropdown-item-sub">{lang.label}</span>
                  </span>
                  {selectedLang === lang.code && <Check size={14} className="dropdown-check" />}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Notifications */}
        <div className="topbar-dropdown-wrapper" ref={notifRef}>
          <button
            className={`topbar-btn notification-btn ${showNotifications ? 'active' : ''}`}
            title="Notifications"
            onClick={() => {
              setShowNotifications(!showNotifications)
              setShowLangDropdown(false)
            }}
          >
            <Bell size={18} />
            {unreadCount > 0 && <span className="notification-badge">{unreadCount}</span>}
          </button>
          {showNotifications && (
            <div className="topbar-dropdown notif-dropdown">
              <div className="dropdown-header">
                <span>Notifications</span>
                {unreadCount > 0 && (
                  <button className="mark-all-btn" onClick={markAllRead}>
                    Mark all read
                  </button>
                )}
              </div>
              <div className="notif-list">
                {notifs.map(n => (
                  <div key={n.id} className={`notif-item ${n.read ? 'read' : ''}`}>
                    {!n.read && <span className="notif-dot" />}
                    <div className="notif-content">
                      <p className="notif-text">{n.text}</p>
                      <span className="notif-time">{n.time}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  )
}
