import { useState } from 'react'
import {
  Building2, Users, AlertTriangle, HeartPulse,
  Activity, Stethoscope, Mic, BarChart3,
  ArrowRight, Clock, MapPin, Sparkles,
  Pill, Apple, PersonStanding
} from 'lucide-react'
import {
  AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, BarChart, Bar
} from 'recharts'
import StatCard from '../components/StatCard'
import './Dashboard.css'

// Mock data
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

const recentActivity = [
  { type: 'ehr', text: 'New EHR created for Patient #12847', time: '2 min ago', icon: Mic, color: 'saffron' },
  { type: 'alert', text: 'Dengue outbreak alert — Rajasthan (High)', time: '15 min ago', icon: AlertTriangle, color: 'high' },
  { type: 'treatment', text: 'Treatment plan generated for Hypertension case', time: '32 min ago', icon: Stethoscope, color: 'sage' },
  { type: 'ehr', text: 'Voice EHR recorded in Hindi — 3 records', time: '1 hr ago', icon: Mic, color: 'saffron' },
  { type: 'alert', text: 'Seasonal flu prediction — Maharashtra (Medium)', time: '2 hr ago', icon: AlertTriangle, color: 'medium' },
  { type: 'treatment', text: 'Yoga regimen prescribed for Obesity patient', time: '3 hr ago', icon: PersonStanding, color: 'lotus' },
]

const outbreakAlerts = [
  { disease: 'Dengue Fever', region: 'Rajasthan', severity: 'critical', cases: 847, change: '+23%' },
  { disease: 'Seasonal Influenza', region: 'Maharashtra', severity: 'high', cases: 1243, change: '+15%' },
  { disease: 'Chikungunya', region: 'Kerala', severity: 'medium', cases: 312, change: '+8%' },
  { disease: 'Malaria', region: 'Odisha', severity: 'low', cases: 156, change: '-5%' },
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
  return (
    <div className="dashboard animate-fade-in">
      {/* Page Header */}
      <div className="page-header">
        <h1>Dashboard Overview</h1>
        <p>Real-time insights across 12,000+ AYUSH centres nationwide</p>
      </div>

      {/* Stats Row */}
      <div className="grid-4 mb-24">
        <StatCard
          icon={Building2}
          label="Active Centers"
          value={12847}
          trend={4.2}
          trendLabel="vs last month"
          color="saffron"
          delay={0}
        />
        <StatCard
          icon={Users}
          label="Patients Today"
          value={34521}
          trend={12.8}
          trendLabel="vs yesterday"
          color="sage"
          delay={80}
        />
        <StatCard
          icon={AlertTriangle}
          label="Active Alerts"
          value={7}
          trend={-18}
          trendLabel="resolved this week"
          color="gold"
          delay={160}
        />
        <StatCard
          icon={HeartPulse}
          label="Treatment Success"
          value={94.2}
          suffix="%"
          trend={2.1}
          trendLabel="improvement"
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
        {/* Activity Feed */}
        <div className="glass-card no-hover">
          <div className="section-header">
            <div>
              <div className="section-title">Recent Activity</div>
              <div className="section-subtitle">Latest system actions</div>
            </div>
            <button className="btn btn-ghost">View All <ArrowRight size={14} /></button>
          </div>
          <div className="activity-feed">
            {recentActivity.map((item, i) => (
              <div key={i} className="activity-item">
                <div className={`activity-icon ${item.color}`}>
                  <item.icon size={16} />
                </div>
                <div className="activity-content">
                  <span className="activity-text">{item.text}</span>
                  <span className="activity-time">
                    <Clock size={12} />
                    {item.time}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Outbreak Alerts */}
        <div className="glass-card no-hover">
          <div className="section-header">
            <div>
              <div className="section-title">Outbreak Alerts</div>
              <div className="section-subtitle">Active disease monitoring</div>
            </div>
          </div>
          <div className="alerts-list">
            {outbreakAlerts.map((alert, i) => (
              <div key={i} className="alert-row">
                <div className="alert-left">
                  <span className={`pulse-dot ${alert.severity}`} />
                  <div>
                    <div className="alert-disease">{alert.disease}</div>
                    <div className="alert-region">
                      <MapPin size={12} />
                      {alert.region}
                    </div>
                  </div>
                </div>
                <div className="alert-right">
                  <span className="alert-cases">{alert.cases.toLocaleString()}</span>
                  <span className={`badge badge-${alert.severity}`}>{alert.change}</span>
                </div>
              </div>
            ))}
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
      <div className="grid-3 mb-24">
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
            <p>Monitor real-time disease surveillance across India</p>
          </div>
          <ArrowRight size={18} className="qa-arrow" />
        </a>
        <a href="/treatment" className="quick-action-card">
          <div className="qa-icon sage"><Sparkles size={24} /></div>
          <div className="qa-content">
            <h4>Generate Treatment Plan</h4>
            <p>AI-powered personalized AYUSH recommendations</p>
          </div>
          <ArrowRight size={18} className="qa-arrow" />
        </a>
      </div>
    </div>
  )
}
