import type { AqiStandard, DataProvenance, LocationOption } from '../types/api'

export interface SeverityStyle {
  label: string
  badgeBg: string
  badgeText: string
  badgeBorder: string
  strokeHex: string
  summaryText: string
}

export const PRESET_LOCATIONS: LocationOption[] = [
  {
    name: 'Delhi',
    country: 'India',
    admin1: 'Delhi NCT',
    latitude: 28.6139,
    longitude: 77.209,
    timezone: 'Asia/Kolkata',
  },
  {
    name: 'Gurugram',
    country: 'India',
    admin1: 'Haryana',
    latitude: 28.4595,
    longitude: 77.0266,
    timezone: 'Asia/Kolkata',
  },
  {
    name: 'Noida',
    country: 'India',
    admin1: 'Uttar Pradesh',
    latitude: 28.5355,
    longitude: 77.391,
    timezone: 'Asia/Kolkata',
  },
  {
    name: 'Mumbai',
    country: 'India',
    admin1: 'Maharashtra',
    latitude: 19.076,
    longitude: 72.8777,
    timezone: 'Asia/Kolkata',
  },
  {
    name: 'Bengaluru',
    country: 'India',
    admin1: 'Karnataka',
    latitude: 12.9716,
    longitude: 77.5946,
    timezone: 'Asia/Kolkata',
  },
  {
    name: 'London',
    country: 'United Kingdom',
    admin1: 'England',
    latitude: 51.5072,
    longitude: -0.1276,
    timezone: 'Europe/London',
  },
]

export function getSeverityStyle(category: string, aqi: number | null): SeverityStyle {
  if (aqi === null || category === 'Insufficient Data') {
    return {
      label: 'Insufficient Data',
      badgeBg: 'bg-slate-100',
      badgeText: 'text-slate-700',
      badgeBorder: 'border-slate-200',
      strokeHex: '#64748b',
      summaryText: 'Minimum pollutant criteria not met for an official composite reading.',
    }
  }

  switch (category) {
    case 'Good':
      return {
        label: 'Good',
        badgeBg: 'bg-emerald-50',
        badgeText: 'text-emerald-800',
        badgeBorder: 'border-emerald-200',
        strokeHex: '#10b981',
        summaryText: 'Minimal air pollution impact; outdoor activities are suitable for most people.',
      }
    case 'Satisfactory':
      return {
        label: 'Satisfactory',
        badgeBg: 'bg-teal-50',
        badgeText: 'text-teal-800',
        badgeBorder: 'border-teal-200',
        strokeHex: '#14b8a6',
        summaryText: 'Minor breathing discomfort possible only for unusually sensitive individuals.',
      }
    case 'Moderate':
    case 'Moderately Polluted':
      return {
        label: category,
        badgeBg: 'bg-amber-50',
        badgeText: 'text-amber-800',
        badgeBorder: 'border-amber-200',
        strokeHex: '#f59e0b',
        summaryText: 'Sensitive groups (children, seniors, asthma) should limit prolonged intense outdoor exertion.',
      }
    case 'Unhealthy for Sensitive Groups':
    case 'Poor':
      return {
        label: category,
        badgeBg: 'bg-orange-50',
        badgeText: 'text-orange-800',
        badgeBorder: 'border-orange-200',
        strokeHex: '#f97316',
        summaryText: 'Elevated respiratory irritation risk; reduce outdoor duration and use fitted N95/FFP2 in traffic.',
      }
    case 'Unhealthy':
    case 'Very Poor':
      return {
        label: category,
        badgeBg: 'bg-rose-50',
        badgeText: 'text-rose-800',
        badgeBorder: 'border-rose-200',
        strokeHex: '#e11d48',
        summaryText: 'High particulate/smog load; keep windows sealed, run HEPA filtration, and avoid outdoor exercise.',
      }
    default:
      return {
        label: category,
        badgeBg: 'bg-purple-50',
        badgeText: 'text-purple-900',
        badgeBorder: 'border-purple-200',
        strokeHex: '#7e22ce',
        summaryText: 'Severe pollution episode; remain indoors with clean-air filtration and follow local GRAP advisories.',
      }
  }
}

export interface ProvenanceMeta {
  label: string
  description: string
  bgClass: string
  textClass: string
  borderClass: string
  dotClass: string
}

export function getProvenanceMeta(provenance: DataProvenance): ProvenanceMeta {
  switch (provenance) {
    case 'measured':
      return {
        label: 'Measured Station',
        description: 'Direct ground-station measurement reported via official CPCB / data.gov.in feed.',
        bgClass: 'bg-emerald-50',
        textClass: 'text-emerald-800',
        borderClass: 'border-emerald-200',
        dotClass: 'bg-emerald-500',
      }
    case 'modeled_current':
      return {
        label: 'Modeled Current',
        description: 'Current-hour atmospheric model estimate (Open-Meteo CAMS), not a physical ground sensor.',
        bgClass: 'bg-teal-50',
        textClass: 'text-teal-800',
        borderClass: 'border-teal-200',
        dotClass: 'bg-teal-500',
      }
    case 'forecast':
      return {
        label: 'Forecast Trajectory',
        description: 'Hourly atmospheric forecast from Open-Meteo; local street conditions may vary.',
        bgClass: 'bg-cyan-50',
        textClass: 'text-cyan-800',
        borderClass: 'border-cyan-200',
        dotClass: 'bg-cyan-500',
      }
    case 'demo':
      return {
        label: 'Demo Snapshot',
        description: 'Explicit synthetic winter-smog dataset for offline demonstration; NOT live readings.',
        bgClass: 'bg-amber-50',
        textClass: 'text-amber-900',
        borderClass: 'border-amber-300',
        dotClass: 'bg-amber-500',
      }
  }
}

export function getStandardLabel(standard: AqiStandard): string {
  return standard === 'CPCB_NAQI' ? 'Indian CPCB NAQI' : 'US EPA AQI (2024)'
}

export const WHO_GUIDELINES_UG_M3: Record<string, { limit: number; window: string }> = {
  'PM2.5': { limit: 15, window: '24h WHO 2021' },
  PM10: { limit: 45, window: '24h WHO 2021' },
  NO2: { limit: 25, window: '24h WHO 2021' },
  SO2: { limit: 40, window: '24h WHO 2021' },
  O3: { limit: 100, window: '8h WHO 2021' },
  CO: { limit: 4000, window: '24h WHO 2021 (4 mg/m³)' },
}

export function computeWhoRatio(pollutantCode: string, ugM3Value: number | null): number | null {
  if (ugM3Value === null) return null
  const ref = WHO_GUIDELINES_UG_M3[pollutantCode]
  if (!ref || ref.limit <= 0) return null
  return Number((ugM3Value / ref.limit).toFixed(2))
}
