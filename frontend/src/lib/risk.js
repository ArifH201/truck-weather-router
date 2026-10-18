export const RISK = [
  { name: 'Low', color: '#2e9e5b' },
  { name: 'Moderate', color: '#e6c229' },
  { name: 'High', color: '#f28c28' },
  { name: 'Severe', color: '#d9342b' },
  { name: 'No Travel', color: '#6a1b9a' },
]

/** Miles of road at each risk level (index = level 0..4) for one route. */
export function milesByRisk(checkpoints) {
  const out = [0, 0, 0, 0, 0]
  for (const c of checkpoints) out[c.risk_level] += c.segment_miles
  return out
}

const R = 6371000
function haversineM(a, b) {
  const rad = (d) => (d * Math.PI) / 180
  const dLat = rad(b.lat - a.lat)
  const dLon = rad(b.lon - a.lon)
  const h =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(rad(a.lat)) * Math.cos(rad(b.lat)) * Math.sin(dLon / 2) ** 2
  return 2 * R * Math.asin(Math.sqrt(h))
}

/**
 * Heatmap blob radius per point: ~80% of the distance to its nearest neighbour,
 * so neighbouring blobs merge into a continuous band without swallowing each other.
 */
export function heatRadiusMeters(points, min = 6000, max = 60000) {
  if (points.length < 2) return points.map(() => 15000)
  return points.map((p, i) => {
    let nearest = Infinity
    points.forEach((q, j) => {
      if (i !== j) nearest = Math.min(nearest, haversineM(p, q))
    })
    return Math.min(max, Math.max(min, nearest * 0.8))
  })
}

/** Corridor-wide summary at one forecast hour: worst risk and peak conditions. */
export function hourSummary(points, hour) {
  const out = { wind: 0, rain: 0, snow: 0, worst: 0 }
  for (const p of points) {
    out.wind = Math.max(out.wind, p.wind[hour] ?? 0)
    out.rain = Math.max(out.rain, p.rain[hour] ?? 0)
    out.snow = Math.max(out.snow, p.snow[hour] ?? 0)
    out.worst = Math.max(out.worst, p.risk[hour] ?? 0)
  }
  return out
}
