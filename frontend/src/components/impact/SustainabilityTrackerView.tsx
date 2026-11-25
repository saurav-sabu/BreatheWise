import { lazy, Suspense, useCallback, useEffect, useMemo, useState } from 'react'
import { Leaf, PlusCircle, Trash2, Info, Shield, Loader2, BarChart3 } from 'lucide-react'
import {
  ApiError,
  deleteImpactAction,
  getImpactCatalog,
  getImpactSummary,
  logImpactAction,
} from '../../lib/api'
import type {
  HouseholdProfileOut,
  ImpactCatalogItem,
  ImpactSummaryResponse,
} from '../../types/api'
import { EmptyStateCard, ErrorBannerCard } from '../ui/StateCards'

const LazyProgressChart = lazy(() => import('./SustainabilityProgressChart'))

interface SustainabilityTrackerViewProps {
  profile: HouseholdProfileOut | null
}

type PeriodTab = 'daily' | 'weekly' | 'monthly' | 'all_time'

export function SustainabilityTrackerView({ profile }: SustainabilityTrackerViewProps) {
  const activeProfileId = profile?.id ?? 'default-family'

  const [catalog, setCatalog] = useState<ImpactCatalogItem[]>([])
  const [summary, setSummary] = useState<ImpactSummaryResponse | null>(null)
  const [period, setPeriod] = useState<PeriodTab>('weekly')
  const [selectedKey, setSelectedKey] = useState('metro_commute_15km')
  const [quantity, setQuantity] = useState(1)
  const [notes, setNotes] = useState('')
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const loadData = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [catRes, sumRes] = await Promise.all([
        getImpactCatalog(),
        getImpactSummary(activeProfileId),
      ])
      setCatalog(catRes)
      setSummary(sumRes)
      if (catRes.length > 0 && !catRes.some((c) => c.action_key === selectedKey)) {
        setSelectedKey(catRes[0].action_key)
      }
    } catch (err: unknown) {
      setError(err instanceof ApiError ? err.detail : 'Unable to load sustainability tracker.')
    } finally {
      setLoading(false)
    }
  }, [activeProfileId, selectedKey])

  useEffect(() => {
    void loadData()
  }, [loadData])

  const selectedSpec = useMemo(
    () => catalog.find((c) => c.action_key === selectedKey) ?? null,
    [catalog, selectedKey],
  )

  const handleLog = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedSpec) return
    setSubmitting(true)
    setError(null)
    try {
      await logImpactAction({
        profile_id: activeProfileId,
        action_key: selectedSpec.action_key,
        quantity,
        notes: notes.trim() || null,
      })
      setNotes('')
      const updated = await getImpactSummary(activeProfileId)
      setSummary(updated)
    } catch (err: unknown) {
      setError(err instanceof ApiError ? err.detail : 'Failed to log action.')
    } finally {
      setSubmitting(false)
    }
  }

  const handleDelete = async (id: number) => {
    try {
      await deleteImpactAction(id)
      const updated = await getImpactSummary(activeProfileId)
      setSummary(updated)
    } catch (err: unknown) {
      setError(err instanceof ApiError ? err.detail : 'Failed to delete log.')
    }
  }

  const periodTotals = summary ? summary[period] : null

  return (
    <div className="space-y-6">
      <section className="rounded-2xl border border-teal-100 bg-white p-6 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="flex items-center gap-2 text-lg font-bold text-slate-900">
              <Leaf className="h-5 w-5 text-emerald-600" />
              Sustainability &amp; Exposure Impact Tracker
            </h2>
            <p className="mt-1 text-xs text-slate-600">
              Deterministic CO2e, PM2.5 emissions avoided, and personal exposure hours protected for profile{' '}
              <strong className="font-mono text-teal-800">{activeProfileId}</strong>.
            </p>
          </div>

          <div className="inline-flex rounded-xl border border-slate-200 bg-slate-50 p-1 text-xs">
            {(
              [
                ['daily', '24h'],
                ['weekly', '7 Days'],
                ['monthly', '30 Days'],
                ['all_time', 'All Time'],
              ] as const
            ).map(([key, label]) => (
              <button
                key={key}
                type="button"
                onClick={() => setPeriod(key)}
                className={`rounded-lg px-3 py-1.5 font-semibold transition ${
                  period === key ? 'bg-white text-teal-800 shadow-xs' : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                {label}
              </button>
            ))}
          </div>
        </div>

        {periodTotals && (
          <div className="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <div className="rounded-xl border border-emerald-200 bg-emerald-50/70 p-4">
              <p className="text-[11px] font-medium text-emerald-800">CO2e Emissions Avoided</p>
              <p className="mt-1 text-2xl font-extrabold text-emerald-950">
                {periodTotals.co2e_kg_avoided.toFixed(2)} kg
              </p>
            </div>
            <div className="rounded-xl border border-teal-200 bg-teal-50/70 p-4">
              <p className="text-[11px] font-medium text-teal-800">PM2.5 Emissions Prevented</p>
              <p className="mt-1 text-2xl font-extrabold text-teal-950">
                {periodTotals.pm25_g_avoided.toFixed(2)} g
              </p>
            </div>
            <div className="rounded-xl border border-cyan-200 bg-cyan-50/70 p-4">
              <p className="text-[11px] font-medium text-cyan-800">Exposure Hours Protected</p>
              <p className="mt-1 text-2xl font-extrabold text-cyan-950">
                {periodTotals.exposure_hours_saved.toFixed(1)} hrs
              </p>
            </div>
            <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
              <p className="text-[11px] font-medium text-slate-600">Actions Logged</p>
              <p className="mt-1 text-2xl font-extrabold text-slate-900">{periodTotals.actions_count}</p>
            </div>
          </div>
        )}
      </section>

      {error && (
        <ErrorBannerCard title="Sustainability Tracker Issue" message={error} onRetry={() => void loadData()} />
      )}

      <div className="grid gap-6 lg:grid-cols-12">
        {/* Action Logger */}
        <section className="rounded-2xl border border-teal-100 bg-white p-6 shadow-sm lg:col-span-5">
          <h3 className="flex items-center gap-2 text-base font-bold text-slate-900">
            <PlusCircle className="h-4 w-4 text-teal-600" />
            Log Low-Emission / Protective Action
          </h3>
          <form onSubmit={handleLog} className="mt-4 space-y-4">
            <div>
              <label className="block text-xs font-medium text-slate-700">Action Catalogue</label>
              <select
                value={selectedKey}
                onChange={(e) => setSelectedKey(e.target.value)}
                className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-xs focus:border-teal-500 focus:outline-none"
              >
                {catalog.map((item) => (
                  <option key={item.action_key} value={item.action_key}>
                    {item.label}
                  </option>
                ))}
              </select>
            </div>

            {selectedSpec && (
              <div className="rounded-xl border border-slate-200 bg-slate-50/80 p-3 text-xs text-slate-600">
                <div className="flex items-center justify-between font-semibold text-slate-800">
                  <span>Per {selectedSpec.unit}:</span>
                  <span>
                    {selectedSpec.co2e_kg_per_unit} kg CO2e • {selectedSpec.pm25_g_per_unit} g PM2.5 •{' '}
                    {selectedSpec.exposure_hours_saved_per_unit}h shield
                  </span>
                </div>
                <p className="mt-1.5 text-[11px] text-slate-500">{selectedSpec.methodology_note}</p>
              </div>
            )}

            <div className="grid grid-cols-3 gap-3">
              <div>
                <label className="block text-xs font-medium text-slate-700">
                  Quantity ({selectedSpec?.unit ?? 'units'})
                </label>
                <input
                  type="number"
                  min={0.5}
                  max={500}
                  step={0.5}
                  value={quantity}
                  onChange={(e) => setQuantity(Math.max(0.5, Number(e.target.value) || 1))}
                  className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-xs focus:border-teal-500 focus:outline-none"
                />
              </div>
              <div className="col-span-2">
                <label className="block text-xs font-medium text-slate-700">Notes (optional)</label>
                <input
                  type="text"
                  maxLength={300}
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="e.g., Blue Line Metro instead of driving"
                  className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-xs focus:border-teal-500 focus:outline-none"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={submitting || !selectedSpec}
              className="flex w-full items-center justify-center gap-2 rounded-xl bg-emerald-600 px-4 py-2.5 text-xs font-semibold text-white shadow-sm transition hover:bg-emerald-700 disabled:opacity-50"
            >
              {submitting && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
              Log Impact Action
            </button>
          </form>
        </section>

        {/* 7-Day Progress Chart */}
        <section className="rounded-2xl border border-teal-100 bg-white p-6 shadow-sm lg:col-span-7">
          <div className="flex items-center justify-between">
            <h3 className="flex items-center gap-2 text-base font-bold text-slate-900">
              <BarChart3 className="h-4 w-4 text-teal-600" />
              7-Day Emissions &amp; Exposure Progress
            </h3>
          </div>
          <div className="mt-4">
            {loading && !summary ? (
              <div className="h-64 animate-pulse rounded-xl bg-slate-100" />
            ) : summary && summary.daily_series.length > 0 ? (
              <Suspense fallback={<div className="h-64 animate-pulse rounded-xl bg-slate-100" />}>
                <LazyProgressChart series={summary.daily_series} />
              </Suspense>
            ) : (
              <EmptyStateCard
                title="No Impact History Yet"
                description="Log your first low-emission or exposure-protection action to view 7-day progress."
              />
            )}
          </div>
          {summary && (
            <div className="mt-3 flex items-start gap-2 rounded-xl bg-slate-50 p-3 text-[11px] text-slate-600">
              <Shield className="mt-0.5 h-3.5 w-3.5 shrink-0 text-teal-600" />
              <span>{summary.distinction_note}</span>
            </div>
          )}
        </section>
      </div>

      {/* Logged Actions & Methodology Assumptions */}
      {summary && (
        <div className="grid gap-6 lg:grid-cols-12">
          <section className="rounded-2xl border border-teal-100 bg-white p-6 shadow-sm lg:col-span-8">
            <h3 className="text-sm font-bold text-slate-900">Recent Persisted Action Logs</h3>
            {summary.recent_logs.length === 0 ? (
              <div className="mt-4">
                <EmptyStateCard
                  title="No Actions Logged for This Profile"
                  description="Use the form above to record commuting swaps, clean cooking, or overnight HEPA protection."
                />
              </div>
            ) : (
              <div className="mt-3 divide-y divide-slate-100">
                {summary.recent_logs.map((log) => (
                  <div key={log.id} className="flex items-center justify-between gap-3 py-3 text-xs">
                    <div>
                      <p className="font-semibold text-slate-900">
                        {log.action_label} ({log.quantity} {log.unit})
                      </p>
                      <p className="text-[11px] text-slate-500">
                        {log.co2e_kg_avoided} kg CO2e • {log.pm25_g_avoided} g PM2.5 • {log.exposure_hours_saved}h shield
                        {log.notes ? ` — "${log.notes}"` : ''}
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={() => void handleDelete(log.id)}
                      className="rounded-lg p-1.5 text-slate-400 hover:bg-rose-50 hover:text-rose-600"
                      aria-label={`Delete action ${log.id}`}
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </section>

          <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm lg:col-span-4">
            <h3 className="flex items-center gap-1.5 text-sm font-bold text-slate-900">
              <Info className="h-4 w-4 text-teal-600" />
              Calculation Assumptions
            </h3>
            <ul className="mt-3 space-y-2 text-[11px] leading-relaxed text-slate-600">
              {summary.methodology_assumptions.map((m, idx) => (
                <li key={idx}>• {m}</li>
              ))}
            </ul>
          </section>
        </div>
      )}
    </div>
  )
}
