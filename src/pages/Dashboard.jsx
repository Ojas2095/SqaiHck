import { useState, useEffect } from 'react'
import {
  Building2, Users, AlertTriangle, HeartPulse,
  Activity, Stethoscope, Mic, BarChart3,
  ArrowRight, Clock, MapPin, Sparkles,
  Pill, Apple, PersonStanding, Database, Cpu
} from 'lucide-react'
import {
  AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, BarChart, Bar
} from 'recharts'
import StatCard from '../components/StatCard'
import './Dashboard.css'

// Static chart data (trend/distribution are illustrative)
const trendData = [
  { month: 'Jan', patients: 2400, alerts: 12 },
  { month: 'Feb', patients: 3200, alerts: 18 },
  { month: 'Mar', patients: 2800, alerts: 8 },
  { month: 'Apr', patients: 4100, alerts: 24 },
  { month: 'May', patients: 3800, alerts: 15 },
  { month: 'Jun', patients: 5200, alerts: 31 },
  { month: 'Jul', patients: 4900, alerts: 22 },
]

const systemDistribution = [
  { name: 'Ayurveda', value: 42, color: '#FF6B35' },
  { name: 'Yoga', value: 22, color: '#4A9D6E' },
  { name: 'Unani', value: 12, color: '#3B82F6' },
  { name: 'Siddha', value: 14, color: '#F4C430' },
  { name: 'Homeopathy', value: 10, color: '#E91E8C' },
]

const weeklyData = [
  { day: 'Mon', records: 42 },
  { day: 'Tue', records: 58 },
  { day: 'Wed', records: 35 },
  { day: 'Thu', records: 72 },
  { day: 'Fri', records: 61 },
  { day: 'Sat', records: 28 },
  { day: 'Sun', records: 15 },
]

const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    return (
      <div className="custom-tooltip">
        <p className="tooltip-label">{label}</p>
        {payload.map((entry, i) => (
          <p key={i} style={{ color: entry.color }}>
            {entry.name}: {entry.value.toLocaleString()}
          </p>
        ))}
      </div>
    )
  }
  return null
}

export default function Dashboard() {
  const [stats, setStats] = useState({
    total_patients: 0,
    total_ehr: 0,
    total_treatments: 0,
    active_alerts: 0,
  })
  const [alerts, setAlerts] = useState([])
  const [kbInfo, setKbInfo] = useState({})
  const [models, setModels] = useState({})
  const [topHerbs, setTopHerbs] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchDashboard()
  }, [])

  async function fetchDashboard() {
    try {
      const res = await fetch('/api/dashboard')
      if (!res.ok) throw new Error('Dashboard API unreachable')
      const d = await res.json()
      
      setStats({
        total_patients: d.total_patients || 0,
        total_ehr: d.total_ehr || 0,
        total_treatments: d.total_treatments || 0,
        active_alerts: d.active_alerts || 0,
      })
      setAlerts(d.recent_alerts || [])
      setKbInfo(d.knowledge_base || {})
      setModels(d.models || {})
      setTopHerbs(d.top_herbs || [])
    } catch (err) {
      console.warn('Dashboard fetch failed (backend may not be running):', err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="dashboard animate-fade-in">
      {/* Page Header */}
      <div className="page-header">
        <h1>Dashboard Overview</h1>
        <p>Real-time insights across AYUSH centres nationwide</p>
      </div>

      {/* Stats Row — now from the real backend */}
      <div className="grid-4 mb-24">
        <StatCard
          icon={Users}
          label="Patients on Record"
          value={stats.total_patients}
          trend={4.2}
          trendLabel="registered"
          color="saffron"
          delay={0}
        />
        <StatCard
          icon={Mic}
          label="EHR Records"
          value={stats.total_ehr}
          trend={12.8}
          trendLabel="visits logged"
          color="sage"
          delay={80}
        />
        <StatCard
          icon={AlertTriangle}
          label="Active Alerts"
          value={stats.active_alerts}
          trend={-18}
          trendLabel="anomalies detected"
          color="gold"
          delay={160}
        />
        <StatCard
          icon={HeartPulse}
          label="Treatment Plans"
          value={stats.total_treatments}
          trend={2.1}
          trendLabel="plans issued"
          color="lotus"
          delay={240}
        />
      </div>

      {/* Main Content Grid */}
      <div className="grid-dashboard mb-24">
        {/* Patient Trends Chart */}
        <div className="glass-card no-hover">
          <div className="section-header">
            <div>
              <div className="section-title">Patient Volume & Alerts</div>
              <div className="section-subtitle">7-month trend across all centers</div>
            </div>
            <div className="tabs">
              <button className="tab active">Monthly</button>
              <button className="tab">Weekly</button>
              <button className="tab">Daily</button>
            </div>
          </div>
          <div className="chart-container">
            <ResponsiveContainer width="100%" height={280}>
              <AreaChart data={trendData}>
                <defs>
                  <linearGradient id="patientGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#FF6B35" stopOpacity={0.3} />
                    <stop offset="100%" stopColor="#FF6B35" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="alertGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#E91E8C" stopOpacity={0.3} />
                    <stop offset="100%" stopColor="#E91E8C" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <XAxis dataKey="month" axisLine={false} tickLine={false} />
                <YAxis axisLine={false} tickLine={false} />
                <Tooltip content={<CustomTooltip />} />
                <Area
                  type="monotone"
                  dataKey="patients"
                  stroke="#FF6B35"
                  strokeWidth={2.5}
                  fill="url(#patientGrad)"
                  name="Patients"
                />
                <Area
                  type="monotone"
                  dataKey="alerts"
                  stroke="#E91E8C"
                  strokeWidth={2}
                  fill="url(#alertGrad)"
                  name="Alerts"
                  yAxisId={0}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* AYUSH System Distribution */}
        <div className="glass-card no-hover">
          <div className="section-header">
            <div>
              <div className="section-title">AYUSH Distribution</div>
              <div className="section-subtitle">Treatment system usage</div>
            </div>
          </div>
          <div className="pie-container">
            <ResponsiveContainer width="100%" height={200}>
              <PieChart>
                <Pie
                  data={systemDistribution}
                  cx="50%"
                  cy="50%"
                  innerRadius={55}
                  outerRadius={85}
                  paddingAngle={3}
                  dataKey="value"
                  strokeWidth={0}
                >
                  {systemDistribution.map((entry, index) => (
                    <Cell key={index} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="pie-legend">
            {systemDistribution.map((item) => (
              <div key={item.name} className="legend-item">
                <span className="legend-dot" style={{ background: item.color }} />
                <span className="legend-name">{item.name}</span>
                <span className="legend-value">{item.value}%</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Second Row */}
      <div className="grid-dashboard mb-24">
        {/* Knowledge Base & Model Status */}
        <div className="glass-card no-hover">
          <div className="section-header">
            <div>
              <div className="section-title">Knowledge Base & AI Models</div>
              <div className="section-subtitle">Engine status from the backend</div>
            </div>
          </div>
          <div className="kb-status-grid">
            <div className="kb-stat-item">
              <Database size={16} className="kb-icon" />
              <span className="kb-label">Corpus Records</span>
              <span className="kb-value">{(kbInfo.records || 0).toLocaleString()}</span>
            </div>
            <div className="kb-stat-item">
              <Activity size={16} className="kb-icon" />
              <span className="kb-label">Diseases Indexed</span>
              <span className="kb-value">{kbInfo.diseases || 0}</span>
            </div>
            <div className="kb-stat-item">
              <Pill size={16} className="kb-icon" />
              <span className="kb-label">Herbs Indexed</span>
              <span className="kb-value">{kbInfo.herbs || 0}</span>
            </div>
            <div className="kb-stat-item">
              <Cpu size={16} className="kb-icon" />
              <span className="kb-label">RAG Backend</span>
              <span className="kb-value">{models.rag_backend || 'N/A'}</span>
            </div>
            <div className="kb-stat-item">
              <Stethoscope size={16} className="kb-icon" />
              <span className="kb-label">LLM Status</span>
              <span className={`kb-value ${models.llm_loaded ? 'status-on' : 'status-off'}`}>
                {models.llm_loaded ? '● Loaded' : '○ Template Fallback'}
              </span>
            </div>
            <div className="kb-stat-item">
              <Mic size={16} className="kb-icon" />
              <span className="kb-label">Speech Engine</span>
              <span className={`kb-value ${models.speech_faster_whisper ? 'status-on' : 'status-off'}`}>
                {models.speech_faster_whisper ? '● Active' : '○ Off'}
              </span>
            </div>
          </div>
          {topHerbs.length > 0 && (
            <div className="top-herbs-bar">
              <span className="kb-label">Top Herbs Prescribed:</span>
              {topHerbs.map(([herb, count], i) => (
                <span key={i} className="badge badge-sage" style={{ marginLeft: 6 }}>
                  {herb} ({count})
                </span>
              ))}
            </div>
          )}
        </div>

        {/* Outbreak Alerts from the real API */}
        <div className="glass-card no-hover">
          <div className="section-header">
            <div>
              <div className="section-title">Outbreak Alerts</div>
              <div className="section-subtitle">IsolationForest + DBSCAN anomalies</div>
            </div>
          </div>
          <div className="alerts-list">
            {alerts.length > 0 ? alerts.map((alert, i) => (
              <div key={i} className="alert-row">
                <div className="alert-left">
                  <span className={`pulse-dot ${alert.severity?.toLowerCase()}`} />
                  <div>
                    <div className="alert-disease">{alert.disease}</div>
                    <div className="alert-region">
                      <MapPin size={12} />
                      {alert.district}
                      {alert.regional_cluster && <span className="badge badge-gold" style={{ marginLeft: 6 }}>Regional</span>}
                    </div>
                  </div>
                </div>
                <div className="alert-right">
                  <span className="alert-cases">{(alert.cases || 0).toLocaleString()}</span>
                  <span className={`badge badge-${alert.severity?.toLowerCase()}`}>{alert.severity}</span>
                </div>
              </div>
            )) : (
              <div className="activity-item" style={{ justifyContent: 'center', opacity: 0.5 }}>
                {loading ? 'Loading...' : 'No active anomalies detected'}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="section-header">
        <div>
          <div className="section-title">Quick Actions</div>
          <div className="section-subtitle">Jump to key workflows</div>
        </div>
      </div>
      <div className="grid-4 mb-24">
        <a href="/patient" className="quick-action-card">
          <div className="qa-icon sky"><Users size={24} /></div>
          <div className="qa-content">
            <h4>Patient Onboarding</h4>
            <p>Voice-assisted multi-step patient intake</p>
          </div>
          <ArrowRight size={18} className="qa-arrow" />
        </a>
        <a href="/ehr" className="quick-action-card">
          <div className="qa-icon saffron"><Mic size={24} /></div>
          <div className="qa-content">
            <h4>Create Voice EHR</h4>
            <p>Record patient data using voice in any Indian language</p>
          </div>
          <ArrowRight size={18} className="qa-arrow" />
        </a>
        <a href="/outbreak" className="quick-action-card">
          <div className="qa-icon gold"><AlertTriangle size={24} /></div>
          <div className="qa-content">
            <h4>View Outbreak Map</h4>
            <p>Monitor real-time disease surveillance</p>
          </div>
          <ArrowRight size={18} className="qa-arrow" />
        </a>
        <a href="/treatment" className="quick-action-card">
          <div className="qa-icon sage"><Sparkles size={24} /></div>
          <div className="qa-content">
            <h4>Treatment Plan</h4>
            <p>AI-powered personalized AYUSH recommendations</p>
          </div>
          <ArrowRight size={18} className="qa-arrow" />
        </a>
      </div>
    </div>
  )
}
