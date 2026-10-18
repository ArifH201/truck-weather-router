import { fmtDateTime } from '../lib/format'
import { RISK, hourSummary } from '../lib/risk'
import { Legend } from './RouteCards'

export default function HeatmapControls({ state, hour, onHour, onRetry }) {
  const { status, data, error } = state
  if (status === 'idle') return null
  const sum = data ? hourSummary(data.points, hour) : null
  const at = data ? new Date(new Date(data.start).getTime() + hour * 3600e3) : null
  return (
    <div className="card heat-controls">
      <div className="heat-title"><strong>Corridor weather forecast</strong>
        {status === 'ready' && <span> · {fmtDateTime(at)} (+{hour}h)</span>}
        {data?.demo && <span className="tag bad" style={{ marginLeft: 8 }}>SIMULATED</span>}
      </div>
      {status === 'loading' && <div className="muted">Loading 48-hour forecast…</div>}
      {status === 'error' && (
        <div className="field-error">Heatmap unavailable: {error} <button className="link" onClick={onRetry}>Retry</button></div>
      )}
      {status === 'ready' && (
        <input type="range" min="0" max={data.hours - 1} step="1" value={hour}
               onChange={(e) => onHour(Number(e.target.value))}
               aria-label="Forecast hours after departure" />
      )}
      {status === 'ready' && (
        <div className="heat-summary">
          Worst on corridor: <b style={{ color: RISK[sum.worst].color }}>{RISK[sum.worst].name}</b>
          {' · '}peak wind <b>{sum.wind.toFixed(0)} mph</b>
          {' · '}rain <b>{sum.rain.toFixed(2)} in/hr</b>
          {' · '}snow <b>{sum.snow.toFixed(2)} in/hr</b>
        </div>
      )}
      {status === 'ready' && <Legend />}
      {status === 'ready' && data.hours < 49 && (
        <div className="muted">Forecast data ends {data.hours - 1}h after departure.</div>
      )}
    </div>
  )
}
