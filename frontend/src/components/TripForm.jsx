import { useState } from 'react'
import { defaultDeparture } from '../lib/format'

export default function TripForm({ onSubmit, loading, fieldErrors = {}, demoEnabled = false }) {
  const [origin, setOrigin] = useState('')
  const [destination, setDestination] = useState('')
  const [departure, setDeparture] = useState(defaultDeparture)
  const [load, setLoad] = useState(42000)
  const [interval, setInterval] = useState('')
  const [demo, setDemo] = useState(false)

  function submit(e) {
    e.preventDefault()
    onSubmit({
      origin: origin.trim(),
      destination: destination.trim(),
      departure: new Date(departure).toISOString(),
      load_lb: Number(load),
      ...(interval ? { interval_miles: Number(interval) } : {}),
      ...(demo ? { demo: true } : {}),
    })
  }

  const err = (k) => fieldErrors[k] && <div className="field-error">{fieldErrors[k]}</div>

  return (
    <form className="card form" onSubmit={submit}>
      <label>
        Origin
        <input value={origin} onChange={(e) => setOrigin(e.target.value)}
               placeholder="e.g. Chicago, IL" required />
        {err('origin')}
      </label>
      <label>
        Destination
        <input value={destination} onChange={(e) => setDestination(e.target.value)}
               placeholder="e.g. Denver, CO" required />
        {err('destination')}
      </label>
      <label>
        Departure (your local time)
        <input type="datetime-local" value={departure}
               onChange={(e) => setDeparture(e.target.value)} required />
        {err('departure')}
      </label>
      <div className="row">
        <label>
          Load weight (lb)
          <input type="number" min="1" max="80000" step="1" value={load}
                 onChange={(e) => setLoad(e.target.value)} required />
          {err('load_lb')}
        </label>
        <label>
          Weather sampling
          <select value={interval} onChange={(e) => setInterval(e.target.value)}>
            <option value="">Auto</option>
            <option value="10">Every 10 mi</option>
            <option value="25">Every 25 mi</option>
            <option value="50">Every 50 mi</option>
          </select>
          {err('interval_miles')}
        </label>
      </div>
      {demoEnabled && (
        <label className="demo-check">
          <input type="checkbox" checked={demo} onChange={(e) => setDemo(e.target.checked)} />
          <span>Demo mode: simulated storm (not real weather)</span>
        </label>
      )}
      <button type="submit" disabled={loading}>
        {loading ? 'Analyzing routes…' : 'Find safest route'}
      </button>
    </form>
  )
}
