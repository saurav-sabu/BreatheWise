import { lazy, Suspense } from 'react'
import { AlertTriangle, FlaskConical, ShieldAlert } from 'lucide-react'
import type {
  AqiStandard,
  CurrentAQIResponse,
  ForecastAQIResponse,
  HouseholdProfileOut,
} from '../../types/api'
import { AqiGaugeCard } from './AqiGaugeCard'
import { PollutantGrid } from './PollutantGrid'
import { DashboardSkeleton, EmptyStateCard, ErrorBannerCard } from '../ui/StateCards'

const LazyForecastChart = lazy(() =>
  import('./ForecastChart').then((mod) => ({ default: mod.ForecastChart })),
)

interface AirQualityDashboardProps {
  currentAqi: CurrentAQIResponse | null
  forecastAqi: ForecastAQIResponse | null
  loading: boolean
  currentError: string | null
  forecastError: string | null
  activeStandard: AqiStandard
  onChangeStandard: (std: AqiStandard) => void
  demoMode: boolean
  onEnableDemoMode: () => void
  onDisableDemoMode: () => void
  onRetry: () => void
  profile: HouseholdProfileOut | null
  onOpenProfile: () => void
}

export function AirQualityDashboard({
  currentAqi,
  forecastAqi,
  loading,
  currentError,
  forecastError,
  activeStandard,
  onChangeStandard,
  demoMode,
  onEnableDemoMode,
  onDisableDemoMode,
  onRetry,
  profile,
  onOpenProfile,
}: AirQualityDashboardProps) {
  if (loading && !currentAqi) {
    return <DashboardSkeleton />
  }

  if (currentError && !currentAqi) {
    return (
      <ErrorBannerCard
        title="Unable to Load Air Quality Data"
        message={currentError}
        onRetry={onRetry}
        onEnableDemo={!demoMode ? onEnableDemoMode : undefined}
      />
    )
  }

  if (!currentAqi) {
    return (
      <EmptyStateCard
        title="No Air Quality Snapshot Loaded"
        description="Search for a city or choose a preset location above to inspect current conditions and 24-hour forecasts."
      />
    )
  }

  const activeIndex = activeStandard === 'CPCB_NAQI' ? currentAqi.indian_naqi : currentAqi.us_epa_aqi
  const isElevated = (activeIndex.aqi ?? 0) > 100
  const hasSensitiveGroup =
    profile && (profile.has_children || profile.has_seniors || profile.respiratory_conditions.length > 0)

  return (
    <div className="space-y-6">
      {currentAqi.provenance === 'demo' && (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-amber-300 bg-amber-50 px-5 py-3.5 text-xs text-amber-950 shadow-xs">
          <div className="flex items-start gap-2.5">
            <FlaskConical className="mt-0.5 h-4 w-4 shrink-0 text-amber-700" />
            <div>
              <p className="font-bold">Demo Snapshot Active — Synthetic Winter Smog Data</p>
              <p className="mt-0.5 text-amber-900">
                Displayed figures are explicitly synthetic demonstration values, not live ambient readings.
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onDisableDemoMode}
            className="rounded-xl border border-amber-400 bg-white px-3 py-1.5 font-semibold text-amber-900 transition hover:bg-amber-100"
          >
            Switch Back to Live API
          </button>
        </div>
      )}

      {currentError && (
        <div className="flex items-center gap-2 rounded-xl border border-rose-200 bg-rose-50 px-4 py-2.5 text-xs text-rose-800">
          <AlertTriangle className="h-4 w-4 shrink-0" />
          <span>Latest refresh failed ({currentError}). Showing last fetched snapshot.</span>
        </div>
      )}

      {isElevated && (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-teal-200 bg-gradient-to-r from-teal-50 to-emerald-50 px-5 py-3.5 text-xs text-teal-950">
          <div className="flex items-start gap-2.5">
            <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0 text-teal-700" />
            <div>
              <p className="font-semibold">
                {hasSensitiveGroup
                  ? `Sensitive Household Alert (${profile.name})`
                  : 'Elevated Particulate Exposure Advisory'}
              </p>
              <p className="mt-0.5 text-teal-800">
                {hasSensitiveGroup
                  ? `Household flags active (${[
                      profile.has_children ? 'children' : null,
                      profile.has_seniors ? 'seniors' : null,
                      ...profile.respiratory_conditions,
                    ]
                      .filter(Boolean)
                      .join(', ')}). Keep indoor air filtered and limit outdoor exertion during peak smog.`
                  : 'Limit prolonged outdoor exertion during morning/evening inversions and consider loading a household profile.'}
              </p>
            </div>
          </div>
          {!profile && (
            <button
              type="button"
              onClick={onOpenProfile}
              className="rounded-xl bg-teal-600 px-3 py-1.5 font-semibold text-white hover:bg-teal-700"
            >
              Set Household Profile
            </button>
          )}
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-12">
        <div className="lg:col-span-5">
          <AqiGaugeCard
            data={currentAqi}
            activeStandard={activeStandard}
            onChangeStandard={onChangeStandard}
          />
        </div>
        <div className="lg:col-span-7">
          <PollutantGrid data={currentAqi} activeStandard={activeStandard} />
        </div>
      </div>

      <Suspense fallback={<div className="h-72 animate-pulse rounded-2xl border border-teal-100 bg-white" />}>
        <LazyForecastChart
          forecast={forecastAqi}
          activeStandard={activeStandard}
          error={forecastError}
        />
      </Suspense>
    </div>
  )
}
