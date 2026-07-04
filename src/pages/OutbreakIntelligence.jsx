import { useState } from 'react'
import {
  AlertTriangle, MapPin, TrendingUp, TrendingDown,
  Calendar, Filter, ChevronDown, Eye, Bell,
  Thermometer, Droplets, Bug, Wind, Shield, Zap
} from 'lucide-react'
import {
  AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer,
  BarChart, Bar, Cell, LineChart, Line
} from 'recharts'
import './OutbreakIntelligence.css'

const outbreakData = [
  { week: 'W22', dengue: 120, influenza: 340, chikungunya: 45, malaria: 80 },
  { week: 'W23', dengue: 180, influenza: 380, chikungunya: 52, malaria: 75 },
  { week: 'W24', dengue: 290, influenza: 320, chikungunya: 68, malaria: 90 },
  { week: 'W25', dengue: 410, influenza: 410, chikungunya: 85, malaria: 65 },
  { week: 'W26', dengue: 580, influenza: 480, chikungunya: 92, malaria: 55 },
  { week: 'W27', dengue: 720, influenza: 520, chikungunya: 78, malaria: 48 },
  { week: 'W28', dengue: 847, influenza: 590, chikungunya: 65, malaria: 42 },
]

const predictionData = [
  { day: 'Today', probability: 72 },
  { day: '+1d', probability: 76 },
  { day: '+2d', probability: 81 },
  { day: '+3d', probability: 84 },
  { day: '+4d', probability: 78 },
  { day: '+5d', probability: 73 },
  { day: '+6d', probability: 68 },
  { day: '+7d', probability: 62 },
]

const regionData = [
  { region: 'Rajasthan', cases: 847, severity: 'critical', diseases: ['Dengue', 'Chikungunya'], trend: 23 },
  { region: 'Maharashtra', cases: 1243, severity: 'high', diseases: ['Influenza', 'H1N1'], trend: 15 },
  { region: 'Kerala', cases: 523, severity: 'high', diseases: ['Dengue', 'Leptospirosis'], trend: 12 },
  { region: 'Uttar Pradesh', cases: 412, severity: 'medium', diseases: ['Malaria', 'Dengue'], trend: 8 },
  { region: 'Tamil Nadu', cases: 289, severity: 'medium', diseases: ['Dengue'], trend: 5 },
  { region: 'West Bengal', cases: 178, severity: 'low', diseases: ['Influenza'], trend: -3 },
  { region: 'Odisha', cases: 156, severity: 'low', diseases: ['Malaria'], trend: -5 },
  { region: 'Karnataka', cases: 134, severity: 'low', diseases: ['Chikungunya'], trend: -2 },
]

const anomalyTimeline = [
  { date: 'Jun 15', event: 'Unusual spike in fever cases — Jaipur', type: 'anomaly', severity: 'high' },
  { date: 'Jun 18', event: 'Dengue cluster detected — Jodhpur dist.', type: 'cluster', severity: 'critical' },
  { date: 'Jun 22', event: 'Outbreak alert triggered — Rajasthan', type: 'alert', severity: 'critical' },
  { date: 'Jun 25', event: 'Influenza surge predicted — Mumbai', type: 'prediction', severity: 'high' },
  { date: 'Jun 28', event: 'Containment measures effective — Jodhpur', type: 'resolution', severity: 'low' },
  { date: 'Jul 01', event: 'New cluster emerging — Udaipur', type: 'anomaly', severity: 'medium' },
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

export default function OutbreakIntelligence() {
  const [activeDisease, setActiveDisease] = useState('all')
  const diseases = ['All', 'Dengue', 'Influenza', 'Chikungunya', 'Malaria']

  return (
    <div className="outbreak-page animate-fade-in">
      <div className="page-header">
        <h1>Outbreak Intelligence</h1>
        <p>AI-powered disease surveillance, anomaly detection, and outbreak prediction across India</p>
      </div>

      {/* Stats Row */}
      <div className="grid-4 mb-24">
        <div className="outbreak-stat-card critical">
          <div className="os-icon"><AlertTriangle size={20} /></div>
          <div className="os-data">
            <span className="os-value">3</span>
            <span className="os-label">Critical Alerts</span>
          </div>
        </div>
        <div className="outbreak-stat-card high">
          <div className="os-icon"><Thermometer size={20} /></div>
          <div className="os-data">
            <span className="os-value">12,847</span>
            <span className="os-label">Active Cases</span>
          </div>
        </div>
        <div className="outbreak-stat-card medium">
          <div className="os-icon"><MapPin size={20} /></div>
          <div className="os-data">
            <span className="os-value">23</span>
            <span className="os-label">Affected Districts</span>
          </div>
        </div>
        <div className="outbreak-stat-card low">
          <div className="os-icon"><Shield size={20} /></div>
          <div className="os-data">
            <span className="os-value">89%</span>
            <span className="os-label">Detection Accuracy</span>
          </div>
        </div>
      </div>

      {/* Disease Filter Tabs */}
      <div className="disease-filters mb-24">
        {diseases.map((d) => (
          <button
            key={d}
            className={`disease-filter-btn ${activeDisease === d.toLowerCase() ? 'active' : ''}`}
            onClick={() => setActiveDisease(d.toLowerCase())}
          >
            {d}
          </button>
        ))}
      </div>

      {/* Main Content */}
      <div className="outbreak-grid mb-24">
        {/* Trend Chart */}
        <div className="glass-card no-hover">
          <div className="section-header">
            <div>
              <div className="section-title">Disease Trend Analysis</div>
              <div className="section-subtitle">Weekly case count by disease type</div>
            </div>
          </div>
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={outbreakData}>
              <defs>
                <linearGradient id="dengueGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#EF4444" stopOpacity={0.2} />
                  <stop offset="100%" stopColor="#EF4444" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="fluGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#3B82F6" stopOpacity={0.2} />
                  <stop offset="100%" stopColor="#3B82F6" stopOpacity={0} />
                </linearGradient>
              </defs>
              <XAxis dataKey="week" axisLine={false} tickLine={false} />
              <YAxis axisLine={false} tickLine={false} />
              <Tooltip content={<CustomTooltip />} />
              <Area type="monotone" dataKey="dengue" stroke="#EF4444" strokeWidth={2} fill="url(#dengueGrad)" name="Dengue" />
              <Area type="monotone" dataKey="influenza" stroke="#3B82F6" strokeWidth={2} fill="url(#fluGrad)" name="Influenza" />
              <Area type="monotone" dataKey="chikungunya" stroke="#F4C430" strokeWidth={2} fill="transparent" name="Chikungunya" />
              <Area type="monotone" dataKey="malaria" stroke="#4A9D6E" strokeWidth={2} fill="transparent" name="Malaria" />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Prediction Panel */}
        <div className="glass-card no-hover">
          <div className="section-header">
            <div>
              <div className="section-title">AI Outbreak Prediction</div>
              <div className="section-subtitle">7-day forecast — Dengue, Rajasthan</div>
            </div>
            <div className="badge badge-critical">High Risk</div>
          </div>

          <div className="prediction-highlight">
            <div className="ph-value">84%</div>
            <div className="ph-label">Peak probability on Day 3</div>
            <div className="ph-detail">Based on spatiotemporal graph neural network analysis</div>
          </div>

          <ResponsiveContainer width="100%" height={180}>
            <LineChart data={predictionData}>
              <XAxis dataKey="day" axisLine={false} tickLine={false} />
              <YAxis domain={[0, 100]} axisLine={false} tickLine={false} />
              <Tooltip content={<CustomTooltip />} />
              <Line
                type="monotone"
                dataKey="probability"
                stroke="#EF4444"
                strokeWidth={2.5}
                dot={{ fill: '#EF4444', r: 4, strokeWidth: 0 }}
                name="Probability %"
              />
            </LineChart>
          </ResponsiveContainer>

          <div className="prediction-factors">
            <h5>Contributing Factors</h5>
            <div className="factor-list">
              <div className="factor-item">
                <Droplets size={14} />
                <span>Heavy rainfall last 2 weeks</span>
                <span className="factor-weight">32%</span>
              </div>
              <div className="factor-item">
                <Thermometer size={14} />
                <span>Temp above 35°C for 5+ days</span>
                <span className="factor-weight">28%</span>
              </div>
              <div className="factor-item">
                <Bug size={14} />
                <span>Vector density increase</span>
                <span className="factor-weight">22%</span>
              </div>
              <div className="factor-item">
                <TrendingUp size={14} />
                <span>Historical seasonal pattern</span>
                <span className="factor-weight">18%</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Second Row */}
      <div className="outbreak-grid mb-24">
        {/* Region-wise Breakdown */}
        <div className="glass-card no-hover">
          <div className="section-header">
            <div>
              <div className="section-title">Region-wise Breakdown</div>
              <div className="section-subtitle">Active cases by state</div>
            </div>
          </div>
          <div className="region-table">
            <div className="region-header-row">
              <span>Region</span>
              <span>Cases</span>
              <span>Diseases</span>
              <span>Trend</span>
              <span>Severity</span>
            </div>
            {regionData.map((r, i) => (
              <div key={i} className="region-row">
                <span className="region-name">
                  <MapPin size={14} />
                  {r.region}
                </span>
                <span className="region-cases">{r.cases.toLocaleString()}</span>
                <span className="region-diseases">
                  {r.diseases.map((d, j) => (
                    <span key={j} className="tag">{d}</span>
                  ))}
                </span>
                <span className={`region-trend ${r.trend > 0 ? 'up' : 'down'}`}>
                  {r.trend > 0 ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
                  {Math.abs(r.trend)}%
                </span>
                <span className={`badge badge-${r.severity}`}>{r.severity}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Anomaly Timeline */}
        <div className="glass-card no-hover">
          <div className="section-header">
            <div>
              <div className="section-title">Anomaly Detection Timeline</div>
              <div className="section-subtitle">AI-detected events</div>
            </div>
          </div>
          <div className="anomaly-timeline">
            {anomalyTimeline.map((item, i) => (
              <div key={i} className="timeline-item">
                <div className="timeline-line">
                  <div className={`timeline-dot ${item.severity}`} />
                  {i < anomalyTimeline.length - 1 && <div className="timeline-connector" />}
                </div>
                <div className="timeline-content">
                  <div className="timeline-date">{item.date}</div>
                  <div className="timeline-event">{item.event}</div>
                  <div className="timeline-meta">
                    <span className={`badge badge-${item.severity}`}>{item.type}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
