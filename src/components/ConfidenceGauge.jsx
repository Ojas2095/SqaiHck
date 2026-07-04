import './ConfidenceGauge.css'

export default function ConfidenceGauge({ value, size = 100, label, color = 'var(--saffron)' }) {
  const radius = (size - 12) / 2
  const circumference = 2 * Math.PI * radius
  const offset = circumference - (value / 100) * circumference

  return (
    <div className="confidence-gauge" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="gauge-svg">
        {/* Background circle */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="var(--border-color)"
          strokeWidth="6"
        />
        {/* Progress circle */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth="6"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          className="gauge-progress"
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
        />
      </svg>
      <div className="gauge-content">
        <span className="gauge-value" style={{ color }}>{Math.round(value)}%</span>
        {label && <span className="gauge-label">{label}</span>}
      </div>
    </div>
  )
}
