import { useMemo, useState } from 'react'
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { TrendingUp, Sun, AlertCircle } from 'lucide-react'
import type { AqiStandard, ForecastAQIResponse } from '../../types/api'
import { ProvenanceBadge } from '../ui/ProvenanceBadge'
import { EmptyStateCard } from '../ui/StateCards'

interface ForecastChartProps {
  forecast: ForecastAQIResponse | null
  activeStandard: AqiStandard
  error: string | null
}

export function ForecastChart({ forecast, activeStandard, error }: ForecastChartProps) {
  const [showPm25, setShowPm25] = useState(true)

  const chartData = useMemo(() => {
    if (!forecast?.hourly?.length) return []
    return forecast.hourly.map((pt) => {
      const aqi = activeStandard === 'CPCB_NAQI' ? pt.indian_naqi.aqi : pt.us_epa_aqi.aqi
      const date = new Date(pt.timestamp)
      return {
        hour: date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        fullTime: date.toLocaleString([], { weekday: 'short', hour: '2-digit', minute: '2-digit' }),
        aqi: aqi ?? 0,
        pm25: pt.pollutants.pm2_5_ug_m3 !== null ? Number(pt.pollutants.pm2_5_ug_m3.toFixed(1)) : null,
      }
    })
  }, [forecast, activeStandard])

  const insights = useMemo(() => {
    if (chartData.length === 0) return null
    const sorted = [...chartData].sort((a, b) => a.aqi - b.aqi)
    return {
      best: sorted[0],
      peak: sorted[sorted.length - 1],
    }
  }, [chartData])

  if (error) {
    return (
      <section className="rounded-2xl border border-amber-200 bg-white p-6 shadow-sm">
        <div className="flex items-center gap-2 text-sm font-semibold text-amber-900">
          <AlertCircle className="h-4 w-4 text-amber-600" />
          24-Hour Forecast Unavailable
        </div>
        <p className="mt-1 text-xs text-slate-600">{error}</p>
      </section>
    )
  }

  if (!forecast || chartData.length === 0) {
    return (
      <section className="rounded-2xl border border-teal-100 bg-white p-6 shadow-sm">
        <EmptyStateCard
          title="No Hourly Forecast Points Returned"
          description="Hourly atmospheric forecast points are not currently available for this location."
        />
      </section>
    )
  }

  return (
    <section className="rounded-2xl border border-teal-100 bg-white p-6 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="flex items-center gap-2 text-base font-bold text-slate-900">
              <TrendingUp className="h-4 w-4 text-teal-600" />
              24-Hour Air Quality Trajectory
            </h3>
            <ProvenanceBadge provenance={forecast.provenance} cached={forecast.cached} compact />
          </div>
          <p className="mt-1 text-xs text-slate-500">
            Showing {activeStandard === 'CPCB_NAQI' ? 'Indian CPCB NAQI' : 'US EPA AQI (2024)'} over the next{' '}
            {forecast.hours_returned} hours • {forecast.source_name}
          </p>
        </div>

        <label className="inline-flex cursor-pointer items-center gap-2 rounded-xl border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs font-medium text-slate-700">
          <input
            type="checkbox"
            checked={showPm25}
            onChange={(e) => setShowPm25(e.target.checked)}
            className="h-3.5 w-3.5 rounded border-slate-300 text-teal-600 focus:ring-teal-500"
          />
          <span>Overlay PM2.5 (µg/m³)</span>
        </label>
      </div>

      {insights && (
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          <div className="flex items-center justify-between rounded-xl border border-emerald-200 bg-emerald-50/70 px-4 py-2.5 text-xs">
            <span className="flex items-center gap-2 font-medium text-emerald-900">
              <Sun className="h-4 w-4 text-emerald-600" />
              Lowest Forecast Window
            </span>
            <span className="font-bold text-emerald-900">
              {insights.best.hour} ({insights.best.aqi} AQI)
            </span>
          </div>
          <div className="flex items-center justify-between rounded-xl border border-rose-200 bg-rose-50/70 px-4 py-2.5 text-xs">
            <span className="font-medium text-rose-900">Peak Smog Window</span>
            <span className="font-bold text-rose-900">
              {insights.peak.hour} ({insights.peak.aqi} AQI)
            </span>
          </div>
        </div>
      )}

      <div className="mt-5 h-72 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={chartData} margin={{ top: 10, right: 16, left: -10, bottom: 0 }}>
            <defs>
              <linearGradient id="aqiGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#0d9488" stopOpacity={0.35} />
                <stop offset="95%" stopColor="#0d9488" stopOpacity={0.02} />
              </linearGradient>
              <linearGradient id="pm25Gradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#10b981" stopOpacity={0.2} />
                <stop offset="95%" stopColor="#10b981" stopOpacity={0.0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
            <XAxis dataKey="hour" tick={{ fontSize: 11, fill: '#64748b' }} tickMargin={8} />
            <YAxis tick={{ fontSize: 11, fill: '#64748b' }} />
            <Tooltip
              contentStyle={{
                borderRadius: '0.75rem',
                borderColor: '#ccfbf1',
                fontSize: '12px',
              }}
              labelFormatter={(_, payload) => payload?.[0]?.payload?.fullTime ?? ''}
            />
            <Area
              type="monotone"
              dataKey="aqi"
              name={activeStandard === 'CPCB_NAQI' ? 'Indian NAQI' : 'US EPA AQI'}
              stroke="#0d9488"
              strokeWidth={2.5}
              fill="url(#aqiGradient)"
            />
            {showPm25 && (
              <Area
                type="monotone"
                dataKey="pm25"
                name="PM2.5 (µg/m³)"
                stroke="#059669"
                strokeWidth={2}
                strokeDasharray="4 4"
                fill="url(#pm25Gradient)"
              />
            )}
          </AreaChart>
        </ResponsiveContainer>
      </div>

      <p className="mt-3 text-[11px] text-slate-500">{forecast.disclaimer}</p>
    </section>
  )
}
