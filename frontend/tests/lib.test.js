import { describe, expect, it } from 'vitest'
import { heatRadiusMeters, hourSummary, milesByRisk } from '../src/lib/risk'
import { fmtDuration } from '../src/lib/format'

describe('milesByRisk', () => {
  it('sums segment miles per level', () => {
    const cps = [
      { risk_level: 0, segment_miles: 30 }, { risk_level: 3, segment_miles: 10 },
      { risk_level: 3, segment_miles: 5 }, { risk_level: 4, segment_miles: 1 },
    ]
    expect(milesByRisk(cps)).toEqual([30, 0, 0, 15, 1])
  })
})

describe('heatRadiusMeters', () => {
  it('scales with spacing and respects clamps', () => {
    const near = [{ lat: 0, lon: 0 }, { lat: 0, lon: 0.0001 }]
    const far = [{ lat: 0, lon: 0 }, { lat: 0, lon: 20 }]
    const mid = [{ lat: 0, lon: 0 }, { lat: 0, lon: 0.2 }]    // ~22 km apart
    expect(heatRadiusMeters(near)[0]).toBe(6000)
    expect(heatRadiusMeters(far)[0]).toBe(60000)
    expect(heatRadiusMeters(mid)[0]).toBeGreaterThan(15000)
    expect(heatRadiusMeters(mid)[0]).toBeLessThan(20000)
    expect(heatRadiusMeters([{ lat: 1, lon: 1 }])).toEqual([15000])
  })
})

describe('fmtDuration', () => {
  it('formats hours and minutes', () => {
    expect(fmtDuration(5.5)).toBe('5h 30m')
    expect(fmtDuration(0.25)).toBe('15m')
    expect(fmtDuration(2)).toBe('2h 00m')
  })
})

describe('hourSummary', () => {
  it('reports the worst risk and peak conditions at the chosen hour', () => {
    const pts = [
      { wind: [10, 40], rain: [0, 0.3], snow: [0, 0], risk: [0, 3] },
      { wind: [12, 20], rain: [0, 0.1], snow: [0, 0.6], risk: [0, 1] },
    ]
    expect(hourSummary(pts, 0)).toEqual({ wind: 12, rain: 0, snow: 0, worst: 0 })
    expect(hourSummary(pts, 1)).toEqual({ wind: 40, rain: 0.3, snow: 0.6, worst: 3 })
  })
})
