import { useEffect, useRef } from 'react'
import L from 'leaflet'
import { useMap } from 'react-leaflet'
import { RISK, heatRadiusMeters } from '../lib/risk'

/**
 * Corridor weather "heatmap". Each sampled point is a soft circle coloured by its
 * risk level at the chosen forecast hour. Circles are created once per dataset;
 * moving the slider only restyles them, with no network call and no re-render.
 * A CSS blur on the dedicated pane merges neighbours into one continuous band.
 */
export default function HeatmapLayer({ data, hour }) {
  const map = useMap()
  const circles = useRef([])

  useEffect(() => {
    if (!data) return undefined
    if (!map.getPane('heat')) {
      const pane = map.createPane('heat')
      pane.style.zIndex = 350            // above tiles, below routes and markers
      pane.style.filter = 'blur(9px)'
      pane.style.pointerEvents = 'none'
    }
    const radii = heatRadiusMeters(data.points)
    circles.current = data.points.map((p, i) =>
      L.circle([p.lat, p.lon], {
        pane: 'heat', radius: radii[i], stroke: false, interactive: false, fillOpacity: 0.35,
      }).addTo(map))
    return () => circles.current.forEach((c) => c.remove())
  }, [data, map])

  useEffect(() => {
    if (!data) return
    circles.current.forEach((c, i) => {
      const level = data.points[i].risk[hour] ?? 0
      c.setStyle({ fillColor: RISK[level].color, fillOpacity: 0.45 + 0.07 * level })
    })
  }, [data, hour])

  return null
}
