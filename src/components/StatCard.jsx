import AnimatedCounter from './AnimatedCounter'
import { TrendingUp, TrendingDown } from 'lucide-react'
import './StatCard.css'

export default function StatCard({ icon: Icon, label, value, suffix = '', prefix = '', trend, trendLabel, color = 'saffron', delay = 0 }) {
  const isPositive = trend > 0
  const TrendIcon = isPositive ? TrendingUp : TrendingDown

  return (
    <div className={`stat-card animate-slide-up`} style={{ animationDelay: `${delay}ms` }}>
      <div className="stat-card-header">
        <div className={`stat-icon-wrapper ${color}`}>
          <Icon size={20} />
        </div>
        {trend !== undefined && (
          <div className={`stat-trend ${isPositive ? 'positive' : 'negative'}`}>
            <TrendIcon size={14} />
            <span>{Math.abs(trend)}%</span>
          </div>
        )}
      </div>
      <div className="stat-value">
        <AnimatedCounter end={value} prefix={prefix} suffix={suffix} decimals={suffix === '%' ? 1 : 0} />
      </div>
      <div className="stat-label">{label}</div>
      {trendLabel && (
        <div className="stat-trend-label">{trendLabel}</div>
      )}
      <div className={`stat-glow ${color}`} />
    </div>
  )
}
