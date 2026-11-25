import { useCallback, useEffect, useState } from 'react'
import { Sparkles, RefreshCw, ArrowRightLeft, Cpu, ShieldCheck } from 'lucide-react'
import { ApiError, getRecommendations } from '../../lib/api'
import type {
  HouseholdProfileOut,
  LocationOption,
  RecommendationsResponse,
  RetrievalMode,
} from '../../types/api'
import { CitationsPanel } from '../ui/CitationsPanel'
import { ProvenanceBadge } from '../ui/ProvenanceBadge'
import { MedicalDisclaimerBanner, RecommendationCard } from '../ui/RecommendationCard'
import { DashboardSkeleton, EmptyStateCard, ErrorBannerCard } from '../ui/StateCards'

interface AiRecommendationsViewProps {
  location: LocationOption
  profile: HouseholdProfileOut | null
  demoMode: boolean
}

export function AiRecommendationsView({ location, profile, demoMode }: AiRecommendationsViewProps) {
  const [commuteDistanceKm, setCommuteDistanceKm] = useState(15)
  const [retrievalMode, setRetrievalMode] = useState<RetrievalMode>('hybrid')
  const [data, setData] = useState<RecommendationsResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchAdvisory = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await getRecommendations({
        city: location.name,
        country: location.country,
        latitude: location.latitude,
        longitude: location.longitude,
        profile_id: profile?.id ?? null,
        commute_distance_km: commuteDistanceKm,
        retrieval_mode: retrievalMode,
        top_k: 5,
        demo_mode: demoMode,
      })
      setData(res)
    } catch (err: unknown) {
      setError(err instanceof ApiError ? err.detail : 'Unable to generate AI recommendations.')
    } finally {
      setLoading(false)
    }
  }, [location.name, location.country, location.latitude, location.longitude, profile?.id, commuteDistanceKm, retrievalMode, demoMode])

  useEffect(() => {
    void fetchAdvisory()
  }, [fetchAdvisory])

  return (
    <div className="space-y-6">
      {/* Controls Header */}
      <section className="rounded-2xl border border-teal-100 bg-white p-6 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h2 className="flex items-center gap-2 text-lg font-bold text-slate-900">
              <Sparkles className="h-5 w-5 text-teal-600" />
              Personalized AI Recommendations
            </h2>
            <p className="mt-1 text-xs text-slate-600">
              LangGraph + Qdrant RAG advisory tailored to {location.name}
              {profile ? ` (${profile.name})` : ''}, distinguishing personal exposure reduction from community emissions reduction.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <label className="flex items-center gap-2 text-xs text-slate-700">
              <span>Daily commute (km):</span>
              <input
                type="number"
                min={0}
                max={200}
                value={commuteDistanceKm}
                onChange={(e) => setCommuteDistanceKm(Math.max(0, Number(e.target.value) || 0))}
                className="w-16 rounded-lg border border-slate-200 px-2 py-1 text-xs focus:border-teal-500 focus:outline-none"
              />
            </label>

            <select
              value={retrievalMode}
              onChange={(e) => setRetrievalMode(e.target.value as RetrievalMode)}
              aria-label="Retrieval mode"
              className="rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1.5 text-xs text-slate-700 focus:border-teal-500 focus:outline-none"
            >
              <option value="hybrid">Hybrid RAG</option>
              <option value="bm25">BM25 Keyword</option>
              <option value="dense">Dense Qdrant</option>
            </select>

            <button
              type="button"
              onClick={() => void fetchAdvisory()}
              disabled={loading}
              className="inline-flex items-center gap-1.5 rounded-xl bg-teal-600 px-3.5 py-1.5 text-xs font-semibold text-white shadow-xs transition hover:bg-teal-700 disabled:opacity-50"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
              Refresh Plan
            </button>
          </div>
        </div>
      </section>

      {loading && !data ? (
        <DashboardSkeleton />
      ) : error && !data ? (
        <ErrorBannerCard
          title="Advisory Pipeline Unavailable"
          message={error}
          onRetry={() => void fetchAdvisory()}
        />
      ) : !data ? (
        <EmptyStateCard
          title="No Recommendations Generated"
          description="Select a location or click Refresh Plan to run the LangGraph advisory pipeline."
        />
      ) : (
        <>
          {/* Summary & Context Strip */}
          <section className="rounded-2xl border border-teal-100 bg-gradient-to-r from-teal-50/70 to-emerald-50/70 p-5">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex flex-wrap items-center gap-2">
                <ProvenanceBadge provenance={data.aqi_provenance} />
                <span className="rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-semibold text-slate-800">
                  Risk Tier: <strong className="uppercase">{data.risk_tier}</strong>
                </span>
                {data.grap_stage_reference && (
                  <span className="rounded-full border border-amber-300 bg-amber-50 px-3 py-1 text-xs font-semibold text-amber-900">
                    {data.grap_stage_reference}
                  </span>
                )}
              </div>

              <div className="flex items-center gap-2 text-[11px] text-slate-600">
                <Cpu className="h-3.5 w-3.5 text-teal-700" />
                <span>
                  Mode: <strong>{data.observability.generation_mode}</strong> ({data.observability.retrieval_mode_used})
                </span>
              </div>
            </div>

            <p className="mt-3 text-sm font-medium leading-relaxed text-slate-800">{data.summary}</p>
            <div className="mt-3 flex flex-wrap gap-4 text-xs text-slate-600">
              <span>
                Indian CPCB NAQI: <strong>{data.indian_naqi.aqi ?? '—'}</strong> ({data.indian_naqi.category})
              </span>
              <span>
                US EPA AQI: <strong>{data.us_epa_aqi.aqi ?? '—'}</strong> ({data.us_epa_aqi.category})
              </span>
            </div>
          </section>

          {/* Deterministic Commute Emissions Swap Callout */}
          {data.transport_swap_estimate?.co2e_kg_avoided_per_week !== undefined && (
            <section className="rounded-2xl border border-emerald-200 bg-white p-5 shadow-sm">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <h3 className="flex items-center gap-2 text-sm font-bold text-slate-900">
                    <ArrowRightLeft className="h-4 w-4 text-emerald-600" />
                    Deterministic Commute Swap Impact ({data.transport_swap_estimate.from_mode} →{' '}
                    {data.transport_swap_estimate.to_mode})
                  </h3>
                  <p className="mt-1 text-xs text-slate-600">
                    {data.transport_swap_estimate.distinction_note}
                  </p>
                </div>
                <div className="flex gap-4">
                  <div className="rounded-xl bg-emerald-50 px-4 py-2 text-center">
                    <span className="block text-lg font-extrabold text-emerald-800">
                      {data.transport_swap_estimate.co2e_kg_avoided_per_week} kg
                    </span>
                    <span className="text-[11px] font-medium text-emerald-700">CO2e / week</span>
                  </div>
                  <div className="rounded-xl bg-teal-50 px-4 py-2 text-center">
                    <span className="block text-lg font-extrabold text-teal-800">
                      {data.transport_swap_estimate.pm25_g_avoided_per_week} g
                    </span>
                    <span className="text-[11px] font-medium text-teal-700">PM2.5 / week</span>
                  </div>
                </div>
              </div>
            </section>
          )}

          {/* Recommendation Cards */}
          <div className="grid gap-5 lg:grid-cols-2">
            {data.recommendations.map((item, idx) => (
              <RecommendationCard key={`${item.title}-${idx}`} item={item} />
            ))}
          </div>

          <CitationsPanel citations={data.citations} />

          <div className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-[11px] text-slate-500">
            <span className="flex items-center gap-1.5">
              <ShieldCheck className="h-3.5 w-3.5 text-teal-600" />
              LangGraph nodes: {data.observability.nodes_executed.join(' → ')}
            </span>
            <span>Total pipeline latency: {data.observability.total_latency_ms} ms</span>
          </div>

          <MedicalDisclaimerBanner text={data.medical_disclaimer} />
        </>
      )}
    </div>
  )
}
