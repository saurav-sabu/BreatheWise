import { Wind } from 'lucide-react'
import { computeWhoRatio, WHO_GUIDELINES_UG_M3 } from '../../lib/aqiUtils'
import type { AqiStandard, CurrentAQIResponse } from '../../types/api'

interface PollutantGridProps {
  data: CurrentAQIResponse
  activeStandard: AqiStandard
}

interface PollutantCardDescriptor {
  code: string
  label: string
  valueUgM3: number | null
  secondaryUnit?: string
}

export function PollutantGrid({ data, activeStandard }: PollutantGridProps) {
  const index = activeStandard === 'CPCB_NAQI' ? data.indian_naqi : data.us_epa_aqi
  const p = data.pollutants

  const items: PollutantCardDescriptor[] = [
    { code: 'PM2.5', label: 'Fine Particulate Matter', valueUgM3: p.pm2_5_ug_m3 },
    { code: 'PM10', label: 'Coarse Particulate Matter', valueUgM3: p.pm10_ug_m3 },
    {
      code: 'NO2',
      label: 'Nitrogen Dioxide',
      valueUgM3: p.no2_ug_m3,
      secondaryUnit: p.no2_ppb !== null ? `${p.no2_ppb.toFixed(1)} ppb` : undefined,
    },
    {
      code: 'O3',
      label: 'Ground-Level Ozone',
      valueUgM3: p.o3_ug_m3,
      secondaryUnit: p.o3_ppm !== null ? `${p.o3_ppm.toFixed(3)} ppm` : undefined,
    },
    {
      code: 'CO',
      label: 'Carbon Monoxide',
      valueUgM3: p.co_ug_m3,
      secondaryUnit:
        p.co_mg_m3 !== null
          ? `${p.co_mg_m3.toFixed(2)} mg/m³${p.co_ppm !== null ? ` • ${p.co_ppm.toFixed(2)} ppm` : ''}`
          : undefined,
    },
    {
      code: 'SO2',
      label: 'Sulfur Dioxide',
      valueUgM3: p.so2_ug_m3,
      secondaryUnit: p.so2_ppb !== null ? `${p.so2_ppb.toFixed(1)} ppb` : undefined,
    },
  ]

  return (
    <section className="rounded-2xl border border-teal-100 bg-white p-6 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h3 className="flex items-center gap-2 text-base font-bold text-slate-900">
            <Wind className="h-4 w-4 text-teal-600" />
            Pollutant Breakdown
          </h3>
          <p className="mt-0.5 text-xs text-slate-500">
            Canonical µg/m³ concentrations compared with WHO 2021 guidelines &amp;{' '}
            {activeStandard === 'CPCB_NAQI' ? 'CPCB NAQI' : 'US EPA'} sub-indices
          </p>
        </div>
      </div>

      <div className="mt-5 grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {items.map((item) => {
          const subIndex = index.sub_indices[item.code]
          const whoRatio = computeWhoRatio(item.code, item.valueUgM3)
          const whoRef = WHO_GUIDELINES_UG_M3[item.code]
          const barPct = whoRatio !== null ? Math.min(100, Math.round((whoRatio / 4) * 100)) : 0
          const barColor =
            whoRatio === null
              ? 'bg-slate-300'
              : whoRatio <= 1
                ? 'bg-emerald-500'
                : whoRatio <= 2
                  ? 'bg-amber-500'
                  : whoRatio <= 4
                    ? 'bg-orange-500'
                    : 'bg-rose-600'

          return (
            <div
              key={item.code}
              className="flex flex-col justify-between rounded-xl border border-slate-200 bg-slate-50/50 p-4 transition hover:border-teal-200 hover:bg-white"
            >
              <div>
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <span className="text-sm font-bold text-slate-900">{item.code}</span>
                    <p className="text-[11px] text-slate-500">{item.label}</p>
                  </div>
                  {subIndex !== undefined ? (
                    <span className="rounded-lg bg-teal-50 px-2 py-0.5 text-[11px] font-semibold text-teal-800">
                      Sub-index: {subIndex}
                    </span>
                  ) : (
                    <span className="rounded-lg bg-slate-100 px-2 py-0.5 text-[11px] text-slate-500">
                      N/A
                    </span>
                  )}
                </div>

                <div className="mt-3">
                  <div className="flex items-baseline gap-1.5">
                    <span className="text-2xl font-bold tracking-tight text-slate-900">
                      {item.valueUgM3 !== null ? item.valueUgM3.toFixed(1) : '—'}
                    </span>
                    <span className="text-xs font-medium text-slate-500">µg/m³</span>
                  </div>
                  {item.secondaryUnit && (
                    <p className="mt-0.5 text-[11px] font-mono text-slate-500">{item.secondaryUnit}</p>
                  )}
                </div>
              </div>

              <div className="mt-4">
                <div className="flex items-center justify-between gap-2 text-[11px] text-slate-600">
                  <span>{whoRef.window}: {whoRef.limit >= 1000 ? `${whoRef.limit / 1000} mg/m³` : `${whoRef.limit} µg/m³`}</span>
                  <span className="font-semibold">
                    {whoRatio !== null ? `${whoRatio}×` : 'Not reported'}
                  </span>
                </div>
                <div className="mt-1.5 h-1.5 w-full overflow-hidden rounded-full bg-slate-200">
                  <div className={`h-full rounded-full ${barColor}`} style={{ width: `${barPct}%` }} />
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </section>
  )
}
