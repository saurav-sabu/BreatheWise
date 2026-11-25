import { useCallback, useEffect, useState } from 'react'
import { Home, Wind, ShieldAlert, CheckCircle2, Info, Loader2 } from 'lucide-react'
import { ApiError, assessIndoorAir } from '../../lib/api'
import type {
  CookingFuel,
  HouseholdProfileOut,
  IndoorAdvisorRequest,
  IndoorAdvisorResponse,
  LocationOption,
} from '../../types/api'
import { CitationsPanel } from '../ui/CitationsPanel'
import { ProvenanceBadge } from '../ui/ProvenanceBadge'
import { RecommendationCard } from '../ui/RecommendationCard'
import { ErrorBannerCard } from '../ui/StateCards'

interface IndoorAirAdvisorViewProps {
  location: LocationOption
  profile: HouseholdProfileOut | null
  demoMode: boolean
}

export function IndoorAirAdvisorView({ location, profile, demoMode }: IndoorAirAdvisorViewProps) {
  const [form, setForm] = useState<Omit<IndoorAdvisorRequest, 'city' | 'country' | 'latitude' | 'longitude' | 'demo_mode'>>({
    room_area_sqft: 250,
    ceiling_height_ft: 9.5,
    occupants: profile?.household_size ?? 4,
    has_sensitive_occupants:
      profile ? profile.has_children || profile.has_seniors || profile.respiratory_conditions.length > 0 : true,
    cooking_fuel: (profile?.cooking_fuel as CookingFuel) ?? 'lpg',
    has_exhaust_hood: true,
    has_hepa_purifier: profile?.has_hepa_purifier ?? false,
    current_purifier_cadr_m3h: null,
    window_sealing_quality: 'average',
    burns_incense_or_candles: false,
  })

  const [result, setResult] = useState<IndoorAdvisorResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const runAssessment = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await assessIndoorAir({
        ...form,
        city: location.name,
        country: location.country,
        latitude: location.latitude,
        longitude: location.longitude,
        demo_mode: demoMode,
      })
      setResult(res)
    } catch (err: unknown) {
      setError(err instanceof ApiError ? err.detail : 'Indoor assessment failed.')
    } finally {
      setLoading(false)
    }
  }, [form, location.name, location.country, location.latitude, location.longitude, demoMode])

  useEffect(() => {
    void runAssessment()
  }, [location.name, location.latitude, location.longitude, demoMode])

  const riskBadgeClass =
    result?.indoor_risk_level === 'High'
      ? 'bg-rose-50 text-rose-800 border-rose-200'
      : result?.indoor_risk_level === 'Elevated'
        ? 'bg-orange-50 text-orange-800 border-orange-200'
        : result?.indoor_risk_level === 'Moderate'
          ? 'bg-amber-50 text-amber-800 border-amber-200'
          : 'bg-emerald-50 text-emerald-800 border-emerald-200'

  return (
    <div className="space-y-6">
      <div className="grid gap-6 lg:grid-cols-12">
        {/* Interactive Room & Pollution Source Form */}
        <section className="rounded-2xl border border-teal-100 bg-white p-6 shadow-sm lg:col-span-5">
          <h2 className="flex items-center gap-2 text-lg font-bold text-slate-900">
            <Home className="h-5 w-5 text-teal-600" />
            Indoor Air Quality Advisor
          </h2>
          <p className="mt-1 text-xs text-slate-600">
            Deterministic CADR, ACH, and indoor risk calculator tailored to {location.name}.
          </p>

          <form
            onSubmit={(e) => {
              e.preventDefault()
              void runAssessment()
            }}
            className="mt-5 space-y-4"
          >
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-slate-700">Room Area (sq ft)</label>
                <input
                  type="number"
                  min={40}
                  max={10000}
                  value={form.room_area_sqft}
                  onChange={(e) => setForm({ ...form, room_area_sqft: Number(e.target.value) || 40 })}
                  className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-xs focus:border-teal-500 focus:outline-none"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-700">Ceiling Height (ft)</label>
                <input
                  type="number"
                  step="0.5"
                  min={6.5}
                  max={25}
                  value={form.ceiling_height_ft}
                  onChange={(e) => setForm({ ...form, ceiling_height_ft: Number(e.target.value) || 8 })}
                  className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-xs focus:border-teal-500 focus:outline-none"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-slate-700">Cooking Fuel</label>
                <select
                  value={form.cooking_fuel}
                  onChange={(e) => setForm({ ...form, cooking_fuel: e.target.value as CookingFuel })}
                  className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-xs focus:border-teal-500 focus:outline-none"
                >
                  <option value="lpg">LPG Cylinder</option>
                  <option value="png_piped">Piped Natural Gas</option>
                  <option value="induction">Induction</option>
                  <option value="electric">Electric</option>
                  <option value="biomass">Biomass / Wood</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-700">Window Sealing</label>
                <select
                  value={form.window_sealing_quality}
                  onChange={(e) =>
                    setForm({
                      ...form,
                      window_sealing_quality: e.target.value as 'leaky' | 'average' | 'well_sealed',
                    })
                  }
                  className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-xs focus:border-teal-500 focus:outline-none"
                >
                  <option value="leaky">Leaky Frames</option>
                  <option value="average">Average Sealing</option>
                  <option value="well_sealed">Well Sealed</option>
                </select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-slate-700">Occupants</label>
                <input
                  type="number"
                  min={1}
                  max={30}
                  value={form.occupants}
                  onChange={(e) => setForm({ ...form, occupants: Number(e.target.value) || 1 })}
                  className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-xs focus:border-teal-500 focus:outline-none"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-700">Current Purifier CADR (m³/h)</label>
                <input
                  type="number"
                  min={20}
                  max={2500}
                  placeholder="Optional"
                  value={form.current_purifier_cadr_m3h ?? ''}
                  onChange={(e) =>
                    setForm({
                      ...form,
                      current_purifier_cadr_m3h: e.target.value ? Number(e.target.value) : null,
                    })
                  }
                  className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-xs focus:border-teal-500 focus:outline-none"
                />
              </div>
            </div>

            <div className="space-y-2 rounded-xl border border-slate-200 bg-slate-50/60 p-3 text-xs text-slate-700">
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={form.has_sensitive_occupants}
                  onChange={(e) => setForm({ ...form, has_sensitive_occupants: e.target.checked })}
                  className="rounded border-slate-300 text-teal-600"
                />
                Sensitive occupants (children, seniors, asthma)
              </label>
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={form.has_exhaust_hood}
                  onChange={(e) => setForm({ ...form, has_exhaust_hood: e.target.checked })}
                  className="rounded border-slate-300 text-teal-600"
                />
                Externally vented kitchen exhaust hood
              </label>
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={form.has_hepa_purifier}
                  onChange={(e) => setForm({ ...form, has_hepa_purifier: e.target.checked })}
                  className="rounded border-slate-300 text-teal-600"
                />
                HEPA / MERV-13 purifier currently running
              </label>
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={form.burns_incense_or_candles}
                  onChange={(e) => setForm({ ...form, burns_incense_or_candles: e.target.checked })}
                  className="rounded border-slate-300 text-teal-600"
                />
                Burns incense, dhoop, or candles indoors
              </label>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="flex w-full items-center justify-center gap-2 rounded-xl bg-teal-600 px-4 py-2.5 text-xs font-semibold text-white shadow-sm transition hover:bg-teal-700 disabled:opacity-50"
            >
              {loading && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
              Calculate CADR &amp; Indoor Risk
            </button>
          </form>
        </section>

        {/* CADR / ACH Results Panel */}
        <section className="space-y-4 rounded-2xl border border-teal-100 bg-white p-6 shadow-sm lg:col-span-7">
          {error ? (
            <ErrorBannerCard title="Indoor Advisor Error" message={error} onRetry={() => void runAssessment()} />
          ) : !result ? (
            <div className="py-16 text-center text-xs text-slate-500">Calculating indoor sizing...</div>
          ) : (
            <>
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <Wind className="h-4 w-4 text-teal-600" />
                  <h3 className="text-base font-bold text-slate-900">
                    Purifier Sizing &amp; Risk Metrics ({result.city})
                  </h3>
                </div>
                <div className="flex items-center gap-2">
                  <ProvenanceBadge provenance={result.aqi_provenance} compact />
                  <span className={`rounded-full border px-3 py-1 text-xs font-bold ${riskBadgeClass}`}>
                    Indoor Risk: {result.indoor_risk_score}/100 ({result.indoor_risk_level})
                  </span>
                </div>
              </div>

              <div className="grid gap-3 sm:grid-cols-3">
                <div className="rounded-xl border border-teal-100 bg-teal-50/60 p-4">
                  <p className="text-[11px] font-medium text-teal-800">Recommended CADR</p>
                  <p className="mt-1 text-2xl font-extrabold text-teal-950">{result.recommended_cadr_m3h} m³/h</p>
                  <p className="text-[11px] text-teal-700">{result.recommended_cadr_cfm} CFM</p>
                </div>
                <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                  <p className="text-[11px] font-medium text-slate-600">Target Air Changes</p>
                  <p className="mt-1 text-2xl font-extrabold text-slate-900">{result.target_ach.toFixed(1)} ACH</p>
                  <p className="text-[11px] text-slate-500">
                    {result.current_achieved_ach !== null
                      ? `Current: ${result.current_achieved_ach} ACH (${Math.round((result.cadr_adequacy_ratio ?? 0) * 100)}%)`
                      : 'ASHRAE / EPA clean room'}
                  </p>
                </div>
                <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                  <p className="text-[11px] font-medium text-slate-600">Room Volume</p>
                  <p className="mt-1 text-2xl font-extrabold text-slate-900">{result.room_volume_m3} m³</p>
                  <p className="text-[11px] text-slate-500">{result.room_volume_ft3} ft³</p>
                </div>
              </div>

              <div className="rounded-xl border border-amber-200 bg-amber-50/70 p-3.5 text-xs text-amber-950">
                <div className="flex items-start gap-2">
                  <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0 text-amber-700" />
                  <span>{result.scope_clarification}</span>
                </div>
              </div>

              <div className="rounded-xl border border-emerald-200 bg-emerald-50/50 p-4">
                <h4 className="flex items-center gap-1.5 text-xs font-bold text-emerald-950">
                  <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" />
                  Ventilation Window Guidance
                </h4>
                <ul className="mt-2 space-y-1 text-xs text-emerald-900">
                  {result.safe_ventilation_windows.map((win, idx) => (
                    <li key={idx}>• {win}</li>
                  ))}
                </ul>
              </div>

              <div className="rounded-xl border border-slate-200 bg-slate-50/70 p-4">
                <h4 className="flex items-center gap-1.5 text-xs font-bold text-slate-800">
                  <Info className="h-3.5 w-3.5 text-teal-600" />
                  Transparent Calculation Assumptions
                </h4>
                <ul className="mt-2 space-y-1 text-[11px] text-slate-600">
                  {result.assumptions.map((a, idx) => (
                    <li key={idx}>• {a}</li>
                  ))}
                </ul>
              </div>
            </>
          )}
        </section>
      </div>

      {result && (
        <>
          <div className="grid gap-5 lg:grid-cols-2">
            {result.guidance_items.map((item, idx) => (
              <RecommendationCard key={`${item.title}-${idx}`} item={item} />
            ))}
          </div>
          <CitationsPanel citations={result.citations} />
        </>
      )}
    </div>
  )
}
