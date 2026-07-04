import { useState, Fragment } from 'react'
import {
  BarChart3, Target, Activity, Cpu, Clock, Zap,
  Database, RefreshCw, CheckCircle2, XCircle, TrendingUp, Server
} from 'lucide-react'
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip,
  RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  LineChart, Line, AreaChart, Area
} from 'recharts'
import ConfidenceGauge from '../components/ConfidenceGauge'
import './Analytics.css'

const performanceMetrics = [
  { name: 'Accuracy', value: 94.2, color: 'var(--sage)' },
  { name: 'Precision', value: 91.8, color: 'var(--saffron)' },
  { name: 'Recall', value: 89.5, color: 'var(--sky)' },
  { name: 'F1 Score', value: 90.6, color: 'var(--gold)' },
  { name: 'AUC-ROC', value: 96.1, color: 'var(--lotus)' },
]

const confusionMatrix = [
  [847, 23, 15, 8],
  [31, 912, 18, 12],
  [12, 21, 768, 34],
  [5, 14, 28, 891],
]

const matrixLabels = ['Ayurveda', 'Yoga', 'Unani', 'Siddha']

const featureImportance = [
  { feature: 'Prakriti Type', importance: 92 },
  { feature: 'Age Group', importance: 78 },
  { feature: 'Comorbidities', importance: 75 },
  { feature: 'Symptom Severity', importance: 71 },
  { feature: 'Treatment History', importance: 68 },
  { feature: 'BMI Category', importance: 62 },
  { feature: 'Regional Climate', importance: 55 },
  { feature: 'Dietary Habits', importance: 48 },
]

const radarData = [
  { metric: 'Accuracy', value: 94, fullMark: 100 },
  { metric: 'Speed', value: 88, fullMark: 100 },
  { metric: 'Coverage', value: 82, fullMark: 100 },
  { metric: 'Explainability', value: 91, fullMark: 100 },
  { metric: 'Fairness', value: 87, fullMark: 100 },
  { metric: 'Robustness', value: 85, fullMark: 100 },
]

const latencyData = [
  { time: '00:00', latency: 120, cost: 0.002 },
  { time: '04:00', latency: 95, cost: 0.0015 },
  { time: '08:00', latency: 180, cost: 0.003 },
  { time: '12:00', latency: 250, cost: 0.004 },
  { time: '16:00', latency: 210, cost: 0.0035 },
  { time: '20:00', latency: 155, cost: 0.0025 },
  { time: '24:00', latency: 130, cost: 0.002 },
]

const outcomeTracking = [
  { month: 'M1', baseline: 100, treated: 100 },
  { month: 'M2', baseline: 98, treated: 92 },
  { month: 'M3', baseline: 97, treated: 82 },
  { month: 'M4', baseline: 96, treated: 71 },
  { month: 'M5', baseline: 95, treated: 63 },
  { month: 'M6', baseline: 94, treated: 58 },
]

const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    return (
      <div className="custom-tooltip">
        <p className="tooltip-label">{label}</p>
        {payload.map((entry, i) => (
          <p key={i} style={{ color: entry.color }}>
            {entry.name}: {typeof entry.value === 'number' && entry.value < 1 ? `$${entry.value}` : entry.value}
          </p>
        ))}
      </div>
    )
  }
  return null
}

export default function Analytics() {
  return (
    <div className="analytics-page animate-fade-in">
      <div className="page-header">
        <h1>Analytics & Explainability</h1>
        <p>Model performance monitoring, feature importance, and system health metrics</p>
      </div>

      {/* Performance Gauges */}
      <div className="glass-card no-hover mb-24">
        <div className="section-header">
          <div>
            <div className="section-title">Model Performance Metrics</div>
            <div className="section-subtitle">Treatment recommendation model — v3.2.1</div>
          </div>
          <div className="flex gap-8">
            <div className="badge badge-sage">Production</div>
            <div className="badge badge-sky">Last updated: 2h ago</div>
          </div>
        </div>
        <div className="gauges-row">
          {performanceMetrics.map((metric) => (
            <div key={metric.name} className="gauge-wrapper">
              <ConfidenceGauge
                value={metric.value}
                size={110}
                color={metric.color}
                label={metric.name}
              />
              <span className="gauge-metric-name">{metric.name}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Two Column Grid */}
      <div className="analytics-grid mb-24">
        {/* Confusion Matrix */}
        <div className="glass-card no-hover">
          <div className="section-header">
            <div>
              <div className="section-title">Confusion Matrix</div>
              <div className="section-subtitle">Multi-class classification results</div>
            </div>
          </div>
          <div className="confusion-matrix">
            <div className="matrix-corner" />
            {matrixLabels.map((label, i) => (
              <div key={i} className="matrix-col-label">{label}</div>
            ))}
            {confusionMatrix.map((row, i) => (
              <Fragment key={`row-${i}`}>
                <div key={`label-${i}`} className="matrix-row-label">{matrixLabels[i]}</div>
                {row.map((val, j) => {
                  const isCorrect = i === j
                  const maxVal = Math.max(...confusionMatrix.flat())
                  const intensity = val / maxVal
                  return (
                    <div
                      key={`${i}-${j}`}
                      className={`matrix-cell ${isCorrect ? 'correct' : 'incorrect'}`}
                      style={{
                        backgroundColor: isCorrect
                          ? `rgba(74, 157, 110, ${intensity * 0.6})`
                          : `rgba(239, 68, 68, ${intensity * 0.3})`,
                      }}
                    >
                      {val}
                    </div>
                  )
                })}
              </Fragment>
            ))}
          </div>
          <div className="matrix-legend">
            <span className="ml-item"><span className="ml-dot correct" /> True Positive (Diagonal)</span>
            <span className="ml-item"><span className="ml-dot incorrect" /> Misclassification</span>
          </div>
        </div>

        {/* Radar Chart */}
        <div className="glass-card no-hover">
          <div className="section-header">
            <div>
              <div className="section-title">Responsible AI Assessment</div>
              <div className="section-subtitle">Multi-dimensional model evaluation</div>
            </div>
          </div>
          <ResponsiveContainer width="100%" height={320}>
            <RadarChart data={radarData}>
              <PolarGrid stroke="var(--border-color)" />
              <PolarAngleAxis dataKey="metric" tick={{ fill: 'var(--text-secondary)', fontSize: 12 }} />
              <PolarRadiusAxis
                angle={90}
                domain={[0, 100]}
                tick={{ fill: 'var(--text-tertiary)', fontSize: 10 }}
              />
              <Radar
                name="Score"
                dataKey="value"
                stroke="#FF6B35"
                fill="#FF6B35"
                fillOpacity={0.15}
                strokeWidth={2}
              />
            </RadarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Feature Importance & Outcome Tracking */}
      <div className="analytics-grid mb-24">
        {/* Feature Importance */}
        <div className="glass-card no-hover">
          <div className="section-header">
            <div>
              <div className="section-title">Feature Importance</div>
              <div className="section-subtitle">SHAP-based feature attribution</div>
            </div>
          </div>
          <div className="feature-bars">
            {featureImportance.map((f, i) => (
              <div key={i} className="feature-item">
                <div className="feature-info">
                  <span className="feature-name">{f.feature}</span>
                  <span className="feature-value">{f.importance}%</span>
                </div>
                <div className="progress-bar">
                  <div
                    className="progress-fill"
                    style={{
                      width: `${f.importance}%`,
                      background: `linear-gradient(90deg, var(--saffron), var(--gold))`,
                      transition: `width 1s ease ${i * 0.1}s`,
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Patient Outcome Tracking */}
        <div className="glass-card no-hover">
          <div className="section-header">
            <div>
              <div className="section-title">Treatment Outcome Tracking</div>
              <div className="section-subtitle">Symptom severity index over time</div>
            </div>
          </div>
          <ResponsiveContainer width="100%" height={280}>
            <AreaChart data={outcomeTracking}>
              <defs>
                <linearGradient id="baselineGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="var(--text-tertiary)" stopOpacity={0.2} />
                  <stop offset="100%" stopColor="var(--text-tertiary)" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="treatedGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#4A9D6E" stopOpacity={0.3} />
                  <stop offset="100%" stopColor="#4A9D6E" stopOpacity={0} />
                </linearGradient>
              </defs>
              <XAxis dataKey="month" axisLine={false} tickLine={false} />
              <YAxis domain={[0, 110]} axisLine={false} tickLine={false} />
              <Tooltip content={<CustomTooltip />} />
              <Area type="monotone" dataKey="baseline" stroke="var(--text-tertiary)" strokeWidth={2} strokeDasharray="5 5" fill="url(#baselineGrad)" name="Baseline (No Treatment)" />
              <Area type="monotone" dataKey="treated" stroke="#4A9D6E" strokeWidth={2.5} fill="url(#treatedGrad)" name="AYUSH Treatment" />
            </AreaChart>
          </ResponsiveContainer>
          <div className="outcome-legend">
            <span><span className="ol-line dashed" /> Baseline (No intervention)</span>
            <span><span className="ol-line solid" /> With AYUSH Treatment</span>
          </div>
        </div>
      </div>

      {/* System Health */}
      <div className="glass-card no-hover mb-24">
        <div className="section-header">
          <div>
            <div className="section-title">System Health & Infrastructure</div>
            <div className="section-subtitle">Real-time monitoring</div>
          </div>
        </div>
        <div className="system-health-grid">
          <div className="health-metric">
            <div className="hm-icon sage"><Server size={18} /></div>
            <div className="hm-data">
              <span className="hm-value">99.7%</span>
              <span className="hm-label">Uptime (30d)</span>
            </div>
          </div>
          <div className="health-metric">
            <div className="hm-icon saffron"><Zap size={18} /></div>
            <div className="hm-data">
              <span className="hm-value">142ms</span>
              <span className="hm-label">Avg Latency</span>
            </div>
          </div>
          <div className="health-metric">
            <div className="hm-icon gold"><Cpu size={18} /></div>
            <div className="hm-data">
              <span className="hm-value">$0.003</span>
              <span className="hm-label">Cost/Inference</span>
            </div>
          </div>
          <div className="health-metric">
            <div className="hm-icon sky"><Database size={18} /></div>
            <div className="hm-data">
              <span className="hm-value">2.4M</span>
              <span className="hm-label">Records Processed</span>
            </div>
          </div>
          <div className="health-metric">
            <div className="hm-icon lotus"><RefreshCw size={18} /></div>
            <div className="hm-data">
              <span className="hm-value">v3.2.1</span>
              <span className="hm-label">Model Version</span>
            </div>
          </div>
          <div className="health-metric">
            <div className="hm-icon sage"><CheckCircle2 size={18} /></div>
            <div className="hm-data">
              <span className="hm-value">12,847</span>
              <span className="hm-label">Active Centers</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
