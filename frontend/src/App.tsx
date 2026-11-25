import { lazy, Suspense, useCallback, useEffect, useState } from 'react'
import { ApiError, getCurrentAqi, getForecastAqi } from './lib/api'
import { PRESET_LOCATIONS } from './lib/aqiUtils'
import type {
  AqiStandard,
  CurrentAQIResponse,
  ForecastAQIResponse,
  HouseholdProfileOut,
  LocationOption,
} from './types/api'
import { AirQualityDashboard } from './components/dashboard/AirQualityDashboard'
import { Header } from './components/layout/Header'
import { Sidebar, type NavSection } from './components/layout/Sidebar'
import { HouseholdProfileDrawer } from './components/profile/HouseholdProfileDrawer'
import { DashboardSkeleton } from './components/ui/StateCards'

const LazyAiRecommendationsView = lazy(() =>
  import('./components/advisor/AiRecommendationsView').then((m) => ({ default: m.AiRecommendationsView })),
)
const LazyIndoorAirAdvisorView = lazy(() =>
  import('./components/advisor/IndoorAirAdvisorView').then((m) => ({ default: m.IndoorAirAdvisorView })),
)
const LazySmartRoutinePlannerView = lazy(() =>
  import('./components/routine/SmartRoutinePlannerView').then((m) => ({
    default: m.SmartRoutinePlannerView,
  })),
)
const LazySustainabilityTrackerView = lazy(() =>
  import('./components/impact/SustainabilityTrackerView').then((m) => ({
    default: m.SustainabilityTrackerView,
  })),
)
const LazyBreatheWiseCopilotView = lazy(() =>
  import('./components/assistant/BreatheWiseCopilotView').then((m) => ({
    default: m.BreatheWiseCopilotView,
  })),
)
const LazyCommunityInsightsView = lazy(() =>
  import('./components/community/CommunityInsightsView').then((m) => ({
    default: m.CommunityInsightsView,
  })),
)

export function App() {
  const [selectedLocation, setSelectedLocation] = useState<LocationOption>(PRESET_LOCATIONS[0])
  const [activeStandard, setActiveStandard] = useState<AqiStandard>('CPCB_NAQI')
  const [activeSection, setActiveSection] = useState<NavSection>('dashboard')
  const [demoMode, setDemoMode] = useState(false)
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const [profileDrawerOpen, setProfileDrawerOpen] = useState(false)

  const [currentAqi, setCurrentAqi] = useState<CurrentAQIResponse | null>(null)
  const [forecastAqi, setForecastAqi] = useState<ForecastAQIResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [currentError, setCurrentError] = useState<string | null>(null)
  const [forecastError, setForecastError] = useState<string | null>(null)
  const [refreshTick, setRefreshTick] = useState(0)

  const [profile, setProfile] = useState<HouseholdProfileOut | null>(null)

  const fetchDashboardData = useCallback(
    async (loc: LocationOption, isDemo: boolean, signal: AbortSignal) => {
      setLoading(true)
      setCurrentError(null)
      setForecastError(null)

      const [curRes, fcRes] = await Promise.allSettled([
        getCurrentAqi(
          {
            lat: loc.latitude,
            lon: loc.longitude,
            city: loc.name,
            country: loc.country,
            demoMode: isDemo,
          },
          signal,
        ),
        getForecastAqi(
          {
            lat: loc.latitude,
            lon: loc.longitude,
            city: loc.name,
            country: loc.country,
            hours: 24,
            demoMode: isDemo,
          },
          signal,
        ),
      ])

      if (signal.aborted) return

      if (curRes.status === 'fulfilled') {
        setCurrentAqi(curRes.value)
      } else {
        const err = curRes.reason
        if (!(err instanceof DOMException && err.name === 'AbortError')) {
          setCurrentAqi(null)
          setCurrentError(err instanceof ApiError ? err.detail : 'Failed to fetch current AQI.')
        }
      }

      if (fcRes.status === 'fulfilled') {
        setForecastAqi(fcRes.value)
      } else {
        const err = fcRes.reason
        if (!(err instanceof DOMException && err.name === 'AbortError')) {
          setForecastAqi(null)
          setForecastError(err instanceof ApiError ? err.detail : 'Failed to fetch 24h forecast.')
        }
      }

      setLoading(false)
    },
    [],
  )

  useEffect(() => {
    const controller = new AbortController()
    void fetchDashboardData(selectedLocation, demoMode, controller.signal)
    return () => controller.abort()
  }, [selectedLocation, demoMode, refreshTick, fetchDashboardData])

  const handleSelectLocation = (loc: LocationOption) => {
    setSelectedLocation(loc)
    setActiveStandard(loc.country.toLowerCase() === 'india' ? 'CPCB_NAQI' : 'US_EPA_AQI')
  }

  return (
    <div className="flex min-h-screen bg-gradient-to-br from-teal-50/60 via-white to-emerald-50/50 text-slate-900">
      <Sidebar
        activeSection={activeSection}
        onSelectSection={setActiveSection}
        mobileOpen={mobileMenuOpen}
        onCloseMobile={() => setMobileMenuOpen(false)}
        selectedLocation={selectedLocation}
        activeStandard={activeStandard}
        profile={profile}
        onOpenProfile={() => setProfileDrawerOpen(true)}
      />

      <div className="flex min-w-0 flex-1 flex-col">
        <Header
          selectedLocation={selectedLocation}
          onSelectLocation={handleSelectLocation}
          demoMode={demoMode}
          onToggleDemoMode={() => setDemoMode((prev) => !prev)}
          onRefresh={() => setRefreshTick((t) => t + 1)}
          loading={loading}
          provenance={currentAqi?.provenance}
          cached={currentAqi?.cached}
          profile={profile}
          onOpenProfile={() => setProfileDrawerOpen(true)}
          onOpenMobileMenu={() => setMobileMenuOpen(true)}
        />

        <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-6 sm:px-6">
          <Suspense fallback={<DashboardSkeleton />}>
            {activeSection === 'dashboard' && (
              <AirQualityDashboard
                currentAqi={currentAqi}
                forecastAqi={forecastAqi}
                loading={loading}
                currentError={currentError}
                forecastError={forecastError}
                activeStandard={activeStandard}
                onChangeStandard={setActiveStandard}
                demoMode={demoMode}
                onEnableDemoMode={() => setDemoMode(true)}
                onDisableDemoMode={() => setDemoMode(false)}
                onRetry={() => setRefreshTick((t) => t + 1)}
                profile={profile}
                onOpenProfile={() => setProfileDrawerOpen(true)}
              />
            )}

            {activeSection === 'recommendations' && (
              <LazyAiRecommendationsView
                location={selectedLocation}
                profile={profile}
                demoMode={demoMode}
              />
            )}

            {activeSection === 'indoor' && (
              <LazyIndoorAirAdvisorView
                location={selectedLocation}
                profile={profile}
                demoMode={demoMode}
              />
            )}

            {activeSection === 'routine' && (
              <LazySmartRoutinePlannerView
                location={selectedLocation}
                profile={profile}
                demoMode={demoMode}
              />
            )}

            {activeSection === 'impact' && <LazySustainabilityTrackerView profile={profile} />}

            {activeSection === 'assistant' && (
              <LazyBreatheWiseCopilotView
                location={selectedLocation}
                currentAqi={currentAqi}
                profile={profile}
                demoMode={demoMode}
              />
            )}

            {activeSection === 'community' && (
              <LazyCommunityInsightsView location={selectedLocation} />
            )}
          </Suspense>
        </main>
      </div>

      <HouseholdProfileDrawer
        open={profileDrawerOpen}
        onClose={() => setProfileDrawerOpen(false)}
        profile={profile}
        onProfileLoaded={(loaded) => setProfile(loaded)}
        activeLocation={selectedLocation}
      />
    </div>
  )
}

export default App
