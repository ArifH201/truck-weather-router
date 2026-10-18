import { useEffect } from 'react'
import L from 'leaflet'
import { CircleMarker, MapContainer, Polyline, Popup, TileLayer, Tooltip, useMap } from 'react-leaflet'
import HeatmapLayer from './HeatmapLayer'
import { RISK } from '../lib/risk'
import { fmtDateTime, fmtDuration } from '../lib/format'

function FitBounds({ routes }) {
  const map = useMap()
  useEffect(() => {
    if (!routes) return
    map.fitBounds(L.latLngBounds(routes.flatMap((r) => r.geometry)), { padding: [30, 30] })
  }, [routes, map])
  return null
}

function Checkpoints({ route }) {
  return route.checkpoints.map((c) => (
    <CircleMarker key={`${route.index}-${c.mile}`} center={[c.lat, c.lon]} radius={6}
                  pathOptions={{ color: '#fff', weight: 2, fillColor: RISK[c.risk_level].color, fillOpacity: 1 }}>
      <Popup>
        <b>Route {route.index + 1} · mile {c.mile}</b><br />
        ETA {fmtDateTime(c.eta)}<br />
        Risk: <b style={{ color: RISK[c.risk_level].color }}>{RISK[c.risk_level].name}</b><br />
        Wind {c.wind_mph} mph · Rain {c.rain_in_hr} in/hr · Snow {c.snow_in_hr} in/hr
      </Popup>
    </CircleMarker>
  ))
}

export default function MapView({ data, selected, onSelect, showAll, heat, hour }) {
  const routes = data?.routes
  // Draw the selected route last so it sits on top.
  const ordered = routes ? [...routes].sort((a, b) => (a.index === selected) - (b.index === selected)) : []

  return (
    <MapContainer center={[39.5, -98.35]} zoom={4} className="map" preferCanvas>
      <TileLayer attribution="&copy; OpenStreetMap contributors"
                 url="https://tile.openstreetmap.org/{z}/{x}/{y}.png" />
      <HeatmapLayer data={heat} hour={hour} />
      {routes && <FitBounds routes={routes} />}
      {ordered.map((r) => {
        const active = r.index === selected
        return (
          <Polyline key={r.index} positions={r.geometry}
                    pathOptions={active
                      ? { color: '#1f5fbf', weight: 6, opacity: 0.95 }
                      : { color: '#6b7785', weight: 4, opacity: 0.8, dashArray: '8 8' }}
                    eventHandlers={{ click: () => onSelect(r.index) }}>
            <Tooltip sticky>
              Route {r.index + 1}{r.recommended ? ' ★' : ''} · {r.distance_miles} mi · {fmtDuration(r.duration_hours)}
            </Tooltip>
          </Polyline>
        )
      })}
      {routes?.filter((r) => showAll || r.index === selected).map((r) => <Checkpoints key={r.index} route={r} />)}
      {data && [['Origin', data.origin], ['Destination', data.destination]].map(([label, p]) => (
        <CircleMarker key={label} center={[p.lat, p.lon]} radius={9}
                      pathOptions={{ color: '#fff', weight: 3, fillColor: '#111', fillOpacity: 1 }}>
          <Tooltip permanent direction="top" offset={[0, -8]}>{label}</Tooltip>
        </CircleMarker>
      ))}
    </MapContainer>
  )
}
