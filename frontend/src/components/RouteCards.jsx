import { RISK, milesByRisk } from '../lib/risk'
import { fmtDateTime, fmtDuration } from '../lib/format'

function RiskBar({ checkpoints }) {
  const miles = milesByRisk(checkpoints)
  const total = miles.reduce((a, b) => a + b, 0) || 1
  return (
    <div className="riskbar" role="img"
         aria-label={miles.map((m, i) => `${RISK[i].name} ${m.toFixed(0)} miles`).join(', ')}>
      {miles.map((m, i) => m > 0 && (
        <span key={i} style={{ width: `${(m / total) * 100}%`, background: RISK[i].color }}
              title={`${RISK[i].name}: ${m.toFixed(0)} mi`} />
      ))}
    </div>
  )
}

export default function RouteCards({ data, selected, onSelect }) {
  const routes = [...data.routes].sort((a, b) => a.rank - b.rank)
  const allBlocked = data.routes.every((r) => r.metrics.has_no_travel)
  return (
    <section>
      <div className={`banner ${allBlocked ? 'warn' : 'ok'}`}>
        {allBlocked && <strong>Every route has No Travel conditions. </strong>}
        {data.recommendation_reason}
      </div>
      {routes.map((r) => (
        <button key={r.index} className={`card route ${selected === r.index ? 'selected' : ''}`}
                onClick={() => onSelect(r.index)} aria-pressed={selected === r.index}>
          <div className="route-head">
            <strong>Route {r.index + 1}</strong>
            {r.recommended && <span className="tag good">★ Recommended</span>}
            {r.metrics.has_no_travel && <span className="tag bad">No Travel</span>}
          </div>
          <div className="route-meta">
            {r.distance_miles.toLocaleString()} mi · {fmtDuration(r.duration_hours)} · arrive {fmtDateTime(r.arrival)}
          </div>
          <RiskBar checkpoints={r.checkpoints} />
          <div className="route-stats">
            <span>Severe <b>{r.metrics.severe_miles} mi</b></span>
            <span>High <b>{r.metrics.high_miles} mi</b></span>
            <span>Avg risk <b>{r.metrics.avg_risk.toFixed(2)}</b>/4</span>
          </div>
        </button>
      ))}
      <Legend />
    </section>
  )
}

export function Legend() {
  return (
    <div className="legend">
      {RISK.map((r) => (
        <span key={r.name}><i style={{ background: r.color }} />{r.name}</span>
      ))}
    </div>
  )
}
