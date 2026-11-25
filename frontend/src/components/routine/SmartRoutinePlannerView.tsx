import { useCallback, useEffect, useState } from 'react'
import { CalendarClock, AlertTriangle, Sun, Flame, Leaf, RefreshCw, ShieldCheck } from 'lucide-react'
import { ApiError, getRoutinePlan } from '../../lib/api'
import type { HouseholdProfileOut, LocationOption, RoutinePlanResponse, RoutineSlot } from '../../types/api'
import { CitationsPanel } from '../ui/CitationsPanel'
import { ProvenanceBadge } from '../ui/ProvenanceBadge'
import { DashboardSkeleton, ErrorBannerCard } from '../ui/StateCards'

interface SmartRoutinePlannerViewProps {
  location: LocationOption
  profile: HouseholdProfileOut | null
  demoMode: boolean
}

const SETTING_BADGES: Record<RoutineSlot['setting'], { label: string; cls: string }> = {
  indoor_filtered: { label: 'Indoor Filtered', cls: 'bg-teal-50 text-teal-800 border-teal-200' },
  indoor_cooking_vented: { label: 'Vented Indoor Cooking', cls: 'bg-amber-50 text-amber-800 border-amber-200' },
  transit_low_emission: { label: 'Low-Emission Transit', cls: 'bg-emerald-50 text-emerald-800 border-emerald-200' },
  outdoor_masked: { label: 'Outdoor (N95/FFP2)', cls: 'bg-orange-50 text-orange-800 border-orange-200' },
  outdoor_cautious: { label: 'Lower-Window Outdoor', cls: 'bg-cyan-50 text-cyan-800 border-cyan-200' },
}

export function SmartRoutinePlannerView({ location, profile, demoMode }: SmartRoutinePlannerViewProps) {
  const [workMode, setWorkMode] = useState<'office' | 'hybrid' | 'wfh'>('hybrid')
  const [commuteDistanceKm, setCommuteDistanceKm] = useState(15)
  const [plan, setPlan] = useState<RoutinePlanResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const loadRoutine = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await getRoutinePlan({
        city: location.name,
        country: location.country,
        latitude: location.latitude,
        longitude: location.longitude,
        profile_id: profile?.id ?? null,
        work_mode: workMode,
        commute_mode: profile?.commute_mode ?? 'car',
        commute_distance_km: commuteDistanceKm,
        has_children: profile?.has_children ?? true,
        has_seniors: profile?.has_seniors ?? false,
        demo_mode: demoMode,
      })
      setPlan(res)
    } catch (err: unknown) {
      setError(err instanceof ApiError ? err.detail : 'Unable to build daily routine.')
    } finally {
      setLoading(false)
    }
  }, [location.name, location.country, location.latitude, location.longitude, profile, workMode, commuteDistanceKm, demoMode])

  useEffect(() => {
    void loadRoutine()
  }, [loadRoutine])

  return (
    <div className="space-y-6">
      <section className="rounded-2xl border border-teal-100 bg-white p-6 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h2 className="flex items-center gap-2 text-lg font-bold text-slate-900">
              <CalendarClock className="h-5 w-5 text-teal-600" />
              Smart Daily Routine Planner
            </h2>
            <p className="mt-1 text-xs text-slate-600">
              Aligns daily errands, school runs, cooking, and transit with modeled hourly smog dips and low-emission swaps.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <select
              value={workMode}
              onChange={(e) => setWorkMode(e.target.value as 'office' | 'hybrid' | 'wfh')}
              aria-label="Work mode"
              className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs text-slate-800 focus:border-teal-500 focus:outline-none"
            >
              <option value="office">Office Commute</option>
              <option value="hybrid">Hybrid Schedule</option>
              <option value="wfh">Work From Home</option>
            </select>

            <label className="flex items-center gap-2 text-xs text-slate-700">
              <span>Commute (km):</span>
              <input
                type="number"
                min={0}
                max={200}
                value={commuteDistanceKm}
                onChange={(e) => setCommuteDistanceKm(Math.max(0, Number(e.target.value) || 0))}
                className="w-16 rounded-lg border border-slate-200 px-2 py-1 text-xs focus:border-teal-500 focus:outline-none"
              />
            </label>

            <button
              type="button"
              onClick={() => void loadRoutine()}
              disabled={loading}
              className="inline-flex items-center gap-1.5 rounded-xl bg-teal-600 px-3.5 py-1.5 text-xs font-semibold text-white hover:bg-teal-700 disabled:opacity-50"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
              Update Timeline
            </button>
          </div>
        </div>
      </section>

      {loading && !plan ? (
        <DashboardSkeleton />
      ) : error && !plan ? (
        <ErrorBannerCard title="Routine Planner Error" message={error} onRetry={() => void loadRoutine()} />
      ) : !plan ? null : (
        <>
          {/* Forecast Caveat — Never guarantee a forecast window is safe */}
          <div className="flex items-start gap-3 rounded-2xl border border-amber-300 bg-amber-50 px-5 py-3.5 text-xs text-amber-950">
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-700" />
            <div>
              <p className="font-bold">Forecast Uncertainty Notice</p>
              <p className="mt-0.5 leading-relaxed">{plan.forecast_caveat}</p>
            </div>
          </div>

          <section className="grid gap-4 md:grid-cols-3">
            <div className="rounded-2xl border border-teal-100 bg-white p-4 shadow-xs">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-slate-500">Current Context</span>
                <ProvenanceBadge provenance={plan.aqi_provenance} compact />
              </div>
              <p className="mt-2 text-sm font-bold text-slate-900">{plan.headline}</p>
            </div>

            <div className="rounded-2xl border border-emerald-200 bg-emerald-50/50 p-4">
              <p className="flex items-center gap-1.5 text-xs font-semibold text-emerald-900">
                <Sun className="h-4 w-4 text-emerald-600" />
                Lowest Modeled Window
              </p>
              <p className="mt-2 text-sm font-bold text-emerald-950">{plan.lowest_forecast_window}</p>
            </div>

            <div className="rounded-2xl border border-rose-200 bg-rose-50/50 p-4">
              <p className="flex items-center gap-1.5 text-xs font-semibold text-rose-900">
                <Flame className="h-4 w-4 text-rose-600" />
                Peak Smog Window
              </p>
              <p className="mt-2 text-sm font-bold text-rose-950">{plan.peak_smog_window}</p>
            </div>
          </section>

          {/* Hourly Activity Timeline */}
          <section className="space-y-3">
            {plan.slots.map((slot) => {
              const badge = SETTING_BADGES[slot.setting]
              return (
                <article
                  key={slot.time_window}
                  className="rounded-2xl border border-teal-100 bg-white p-5 shadow-xs"
                >
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="rounded-lg bg-slate-900 px-2.5 py-1 font-mono text-xs font-bold text-white">
                          {slot.time_window}
                        </span>
                        <span className={`rounded-full border px-2.5 py-0.5 text-[11px] font-semibold ${badge.cls}`}>
                          {badge.label}
                        </span>
                      </div>
                      <h3 className="mt-2.5 text-base font-bold text-slate-900">{slot.activity}</h3>
                    </div>

                    <div className="flex flex-wrap gap-2 text-xs">
                      <span className="rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1">
                        NAQI: <strong>{slot.forecast_indian_naqi ?? '—'}</strong>
                      </span>
                      <span className="rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1">
                        US EPA: <strong>{slot.forecast_us_epa_aqi ?? '—'}</strong>
                      </span>
                      <span className="rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1">
                        PM2.5: <strong>{slot.forecast_pm25_ug_m3 !== null ? `${slot.forecast_pm25_ug_m3} µg/m³` : '—'}</strong>
                      </span>
                    </div>
                  </div>

                  <p className="mt-3 text-xs leading-relaxed text-slate-700">{slot.guidance}</p>

                  <div className="mt-3 grid gap-2.5 md:grid-cols-2">
                    <div className="rounded-xl bg-teal-50/60 p-3 text-xs text-teal-950">
                      <span className="flex items-center gap-1.5 font-semibold">
                        <ShieldCheck className="h-3.5 w-3.5 text-teal-700" />
                        Exposure Rationale
                      </span>
                      <p className="mt-1 text-teal-900">{slot.exposure_explanation}</p>
                    </div>
                    {slot.low_emission_swap && (
                      <div className="rounded-xl bg-emerald-50/60 p-3 text-xs text-emerald-950">
                        <span className="flex items-center gap-1.5 font-semibold">
                          <Leaf className="h-3.5 w-3.5 text-emerald-700" />
                          Low-Emission Alternative
                        </span>
                        <p className="mt-1 text-emerald-900">{slot.low_emission_swap}</p>
                      </div>
                    )}
                  </div>

                  <p className="mt-2 text-[11px] text-slate-500">Note: {slot.confidence_note}</p>
                </article>
              )
            })}
          </section>

          <CitationsPanel citations={plan.citations} />
        </>
      )}
    </div>
  )
}
