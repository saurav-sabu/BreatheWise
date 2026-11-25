import { describe, expect, it } from 'vitest'
import {
  computeWhoRatio,
  getProvenanceMeta,
  getSeverityStyle,
  getStandardLabel,
} from '../lib/aqiUtils'

describe('aqiUtils', () => {
  it('classifies CPCB NAQI and US EPA categories cleanly', () => {
    expect(getSeverityStyle('Good', 32).label).toBe('Good')
    expect(getSeverityStyle('Very Poor', 337).label).toBe('Very Poor')
    expect(getSeverityStyle('Insufficient Data', null).label).toBe('Insufficient Data')
  })

  it('distinguishes all four provenance states', () => {
    expect(getProvenanceMeta('measured').label).toBe('Measured Station')
    expect(getProvenanceMeta('modeled_current').label).toBe('Modeled Current')
    expect(getProvenanceMeta('forecast').label).toBe('Forecast Trajectory')
    expect(getProvenanceMeta('demo').label).toBe('Demo Snapshot')
  })

  it('computes WHO 2021 guideline ratios and standard labels', () => {
    expect(computeWhoRatio('PM2.5', 45)).toBe(3)
    expect(computeWhoRatio('PM2.5', null)).toBeNull()
    expect(getStandardLabel('CPCB_NAQI')).toBe('Indian CPCB NAQI')
    expect(getStandardLabel('US_EPA_AQI')).toBe('US EPA AQI (2024)')
  })
})
