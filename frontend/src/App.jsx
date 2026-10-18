import { useCallback, useEffect, useRef, useState } from 'react'
import TripForm from './components/TripForm'
import RouteCards from './components/RouteCards'
import MapView from './components/MapView'
import HeatmapControls from './components/HeatmapControls'
import { analyze, heatmap, health, ApiError } from './lib/api'

export default function App() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [fieldErrors, setFieldErrors] = useState({})
  const [data, setData] = useState(null)
  const [selected, setSelected] = useState(null)
  const [showAll, setShowAll] = useState(false)
  const [heat, setHeat] = useState({ status: 'idle' })
  const [hour, setHour] = useState(0)
  const [demoEnabled, setDemoEnabled] = useState(false)
  const request = useRef({ trip: null, heat: null, params: null })

  useEffect(() => {
    health().then((h) => setDemoEnabled(Boolean(h.demo_enabled))).catch(() => {})
  }, [])

  const loadHeatmap = useCallback(async (result, params) => {
    request.current.heat?.abort()
    const ctl = (request.current.heat = new AbortController())
    setHeat({ status: 'loading' })
    setHour(0)
    try {
      const h = await heatmap({
        geometries: result.routes.map((r) => r.geometry),
        departure: params.departure,
        load_lb: params.load_lb,
        ...(params.demo ? { demo: true } : {}),
      }, ctl.signal)
      setHeat({ status: 'ready', data: h })
    } catch (e) {
      if (e.name !== 'AbortError') setHeat({ status: 'error', error: e.message })
    }
  }, [])

  async function onSubmit(params) {
    request.current.trip?.abort()
    const ctl = (request.current.trip = new AbortController())
    request.current.params = params
    setLoading(true); setError(null); setFieldErrors({})
    try {
      const result = await analyze(params, ctl.signal)
      setData(result)
      setSelected(result.recommended_index)
      loadHeatmap(result, params)          // map + cards show now; heatmap follows
    } catch (e) {
      if (e.name === 'AbortError') return
      setError(e.message)
      if (e instanceof ApiError) setFieldErrors(e.fields)
    } finally {
      if (request.current.trip === ctl) setLoading(false)
    }
  }

  return (
    <div className="app">
      <aside className="sidebar">
        <h1>Weather-Aware Truck Routing</h1>
        <TripForm onSubmit={onSubmit} loading={loading} fieldErrors={fieldErrors} demoEnabled={demoEnabled} />
        {error && <div className="banner warn" role="alert">{error}</div>}
        {data?.demo && (
          <div className="banner demo" role="status">
            <strong>DEMO MODE: simulated weather.</strong> Routes are real; the forecast is a made-up storm for testing.
          </div>
        )}
        {data && <RouteCards data={data} selected={selected} onSelect={setSelected} />}
        {data && (
          <label className="check">
            <input type="checkbox" checked={showAll} onChange={(e) => setShowAll(e.target.checked)} />
            Show checkpoints for all routes
          </label>
        )}
      </aside>
      <main className="mapwrap">
        <MapView data={data} selected={selected} onSelect={setSelected} showAll={showAll}
                 heat={heat.status === 'ready' ? heat.data : null} hour={hour} />
        {data && (
          <HeatmapControls state={heat} hour={hour} onHour={setHour}
                           onRetry={() => loadHeatmap(data, request.current.params)} />
        )}
        {loading && <div className="overlay">Finding routes and checking weather…</div>}
      </main>
    </div>
  )
}
