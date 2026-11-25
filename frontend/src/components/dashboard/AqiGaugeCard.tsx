import { Info, Clock, MapPin } from 'lucide-react'
import { getSeverityStyle, getStandardLabel } from '../../lib/aqiUtils'
import type { AqiStandard, CurrentAQIResponse } from '../../types/api'
import { ProvenanceBadge } from '../ui/ProvenanceBadge'

interface AqiGaugeCardProps {
  data: CurrentAQIResponse
  activeStandard: AqiStandard
  onChangeStandard: (std: AqiStandard) => void
}

export function AqiGaugeCard({ data, activeStandard, onChangeStandard }: AqiGaugeCardProps) {
  const primary = activeStandard === 'CPCB_NAQI' ? data.indian_naqi : data.us_epa_aqi
  const secondary = activeStandard === 'CPCB_NAQI' ? data.us_epa_aqi : data.indian_naqi
  const severity = getSeverityStyle(primary.category, primary.aqi)
  const secondaryStyle = getSeverityStyle(secondary.category, secondary.aqi)

  // Semi-circle SVG arc calculation (0..500 scale)
  const clampedValue = Math.max(0, Math.min(500, primary.aqi ?? 0))
  const ratio = primary.aqi === null ? 0 : clampedValue / 500
  const radius = 84
  const circumference = Math.PI * radius
  const dashOffset = circumference * (1 - ratio)

  const observedFormatted = new Date(data.observed_at).toLocaleString(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  })

  return (
    <section className="flex flex-col justify-between rounded-2xl border border-teal-100 bg-white p-6 shadow-sm">
      <div>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <div className="flex items-center gap-2">
              <MapPin className="h-4 w-4 text-teal-600" />
              <h2 className="text-lg font-bold text-slate-900">
                {data.location_name}
                {data.country ? `, ${data.country}` : ''}
              </h2>
            </div>
            <p className="mt-0.5 text-xs text-slate-500">
              {data.station_name ? `Station: ${data.station_name}` : data.source_name}
            </p>
          </div>
          <ProvenanceBadge provenance={data.provenance} cached={data.cached} />
        </div>

        {/* Standard Switcher: Indian CPCB NAQI vs US EPA AQI strictly separated */}
        <div className="mt-4 inline-flex rounded-xl border border-slate-200 bg-slate-50 p-1">
          <button
            type="button"
            onClick={() => onChangeStandard('CPCB_NAQI')}
            className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
              activeStandard === 'CPCB_NAQI'
                ? 'bg-white text-teal-800 shadow-xs'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            Indian CPCB NAQI
          </button>
          <button
            type="button"
            onClick={() => onChangeStandard('US_EPA_AQI')}
            className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
              activeStandard === 'US_EPA_AQI'
                ? 'bg-white text-teal-800 shadow-xs'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            US EPA AQI (2024)
          </button>
        </div>

        {/* Semi-circular Gauge */}
        <div className="mt-5 flex flex-col items-center">
          <div className="relative flex w-60 flex-col items-center">
            <svg viewBox="0 0 220 125" className="w-full overflow-visible" role="img" aria-label={`AQI Gauge showing ${primary.aqi ?? 'Insufficient data'}`}>
              <path
                d="M 26 110 A 84 84 0 0 1 194 110"
                fill="none"
                stroke="#e2e8f0"
                strokeWidth="16"
                strokeLinecap="round"
              />
              <path
                d="M 26 110 A 84 84 0 0 1 194 110"
                fill="none"
                stroke={severity.strokeHex}
                strokeWidth="16"
                strokeLinecap="round"
                strokeDasharray={circumference}
                strokeDashoffset={dashOffset}
                className="transition-all duration-700 ease-out"
              />
              <text
                x="110"
                y="84"
                textAnchor="middle"
                className="fill-slate-900 text-4xl font-extrabold"
              >
                {primary.aqi !== null ? primary.aqi : '—'}
              </text>
              <text
                x="110"
                y="105"
                textAnchor="middle"
                className="fill-slate-500 text-[11px] font-medium"
              >
                {getStandardLabel(primary.standard)}
              </text>
              <text x="20" y="124" textAnchor="middle" className="fill-slate-400 text-[10px]">
                0
              </text>
              <text x="110" y="16" textAnchor="middle" className="fill-slate-400 text-[10px]">
                250
              </text>
              <text x="200" y="124" textAnchor="middle" className="fill-slate-400 text-[10px]">
                500
              </text>
            </svg>

            <div className="mt-2 flex flex-wrap items-center justify-center gap-2">
              <span
                className={`inline-flex items-center rounded-full border px-3 py-1 text-xs font-bold ${severity.badgeBg} ${severity.badgeText} ${severity.badgeBorder}`}
              >
                {severity.label}
              </span>
              {primary.dominant_pollutant && (
                <span className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs font-medium text-slate-700">
                  Dominant: <strong className="text-slate-900">{primary.dominant_pollutant}</strong>
                </span>
              )}
            </div>
          </div>

          <p className="mt-3 text-center text-xs leading-relaxed text-slate-600">
            {severity.summaryText}
          </p>
        </div>

        {/* Parallel comparison card for the alternate standard (never mixed) */}
        <div className="mt-5 flex items-center justify-between rounded-xl border border-slate-200 bg-slate-50/80 px-4 py-3">
          <div>
            <p className="text-[11px] font-medium uppercase tracking-wide text-slate-500">
              Parallel {getStandardLabel(secondary.standard)}
            </p>
            <p className="text-xs text-slate-600">
              Calculated independently on same pollutant concentrations
            </p>
          </div>
          <div className="text-right">
            <span className="text-lg font-bold text-slate-900">{secondary.aqi ?? '—'}</span>
            <span
              className={`ml-2 inline-block rounded-full border px-2 py-0.5 text-[11px] font-semibold ${secondaryStyle.badgeBg} ${secondaryStyle.badgeText} ${secondaryStyle.badgeBorder}`}
            >
              {secondaryStyle.label}
            </span>
          </div>
        </div>
      </div>

      <div className="mt-4 space-y-2 border-t border-slate-100 pt-3 text-[11px] text-slate-500">
        <div className="flex items-center justify-between gap-2">
          <span className="inline-flex items-center gap-1">
            <Clock className="h-3.5 w-3.5 text-teal-600" />
            Observed: {observedFormatted}
          </span>
          <span className="font-mono text-[10px]">Basis: {primary.averaging_basis}</span>
        </div>
        <div className="flex items-start gap-1.5 rounded-lg bg-slate-50 p-2 text-[11px] text-slate-600">
          <Info className="mt-0.5 h-3.5 w-3.5 shrink-0 text-teal-600" />
          <span>{data.disclaimer}</span>
        </div>
      </div>
    </section>
  )
}
