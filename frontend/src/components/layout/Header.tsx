import { useEffect, useRef, useState } from 'react'
import {
  Search,
  Menu,
  RefreshCw,
  UserCheck,
  FlaskConical,
  Loader2,
  MapPin,
  X,
} from 'lucide-react'
import { ApiError, searchLocations } from '../../lib/api'
import { PRESET_LOCATIONS } from '../../lib/aqiUtils'
import type { DataProvenance, HouseholdProfileOut, LocationOption } from '../../types/api'
import { ProvenanceBadge } from '../ui/ProvenanceBadge'

interface HeaderProps {
  selectedLocation: LocationOption
  onSelectLocation: (loc: LocationOption) => void
  demoMode: boolean
  onToggleDemoMode: () => void
  onRefresh: () => void
  loading: boolean
  provenance?: DataProvenance
  cached?: boolean
  profile: HouseholdProfileOut | null
  onOpenProfile: () => void
  onOpenMobileMenu: () => void
}

export function Header({
  selectedLocation,
  onSelectLocation,
  demoMode,
  onToggleDemoMode,
  onRefresh,
  loading,
  provenance,
  cached,
  profile,
  onOpenProfile,
  onOpenMobileMenu,
}: HeaderProps) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<LocationOption[]>([])
  const [searching, setSearching] = useState(false)
  const [searchError, setSearchError] = useState<string | null>(null)
  const [dropdownOpen, setDropdownOpen] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handleOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setDropdownOpen(false)
      }
    }
    document.addEventListener('mousedown', handleOutside)
    return () => document.removeEventListener('mousedown', handleOutside)
  }, [])

  useEffect(() => {
    const trimmed = query.trim()
    if (trimmed.length < 2) {
      setResults([])
      setSearchError(null)
      setSearching(false)
      return
    }

    const controller = new AbortController()
    const timer = window.setTimeout(async () => {
      setSearching(true)
      setSearchError(null)
      try {
        const res = await searchLocations(trimmed, 6, controller.signal)
        setResults(res.results)
        setDropdownOpen(true)
      } catch (err: unknown) {
        if (err instanceof DOMException && err.name === 'AbortError') return
        setSearchError(err instanceof ApiError ? err.detail : 'City search unavailable')
        setResults([])
        setDropdownOpen(true)
      } finally {
        setSearching(false)
      }
    }, 300)

    return () => {
      window.clearTimeout(timer)
      controller.abort()
    }
  }, [query])

  const pickLocation = (loc: LocationOption) => {
    onSelectLocation(loc)
    setQuery('')
    setDropdownOpen(false)
  }

  return (
    <header className="sticky top-0 z-30 border-b border-teal-100 bg-white/95 backdrop-blur">
      <div className="mx-auto flex max-w-7xl flex-col gap-3 px-4 py-3.5 sm:px-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <button
              type="button"
              onClick={onOpenMobileMenu}
              className="rounded-xl border border-slate-200 p-2 text-slate-600 hover:bg-slate-50 lg:hidden"
              aria-label="Open navigation menu"
            >
              <Menu className="h-5 w-5" />
            </button>

            <div ref={containerRef} className="relative w-64 sm:w-80">
              <div className="flex items-center rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 focus-within:border-teal-500 focus-within:bg-white focus-within:ring-2 focus-within:ring-teal-500/20">
                <Search className="h-4 w-4 shrink-0 text-slate-400" />
                <input
                  type="text"
                  value={query}
                  onChange={(e) => {
                    setQuery(e.target.value)
                    if (e.target.value.trim().length >= 2) setDropdownOpen(true)
                  }}
                  onFocus={() => {
                    if (query.trim().length >= 2 || results.length > 0) setDropdownOpen(true)
                  }}
                  placeholder="Search city (e.g., Delhi, Noida, London)..."
                  aria-label="Search city"
                  className="ml-2 w-full bg-transparent text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none"
                />
                {searching && <Loader2 className="h-4 w-4 animate-spin text-teal-600" />}
                {query && !searching && (
                  <button
                    type="button"
                    onClick={() => {
                      setQuery('')
                      setResults([])
                      setDropdownOpen(false)
                    }}
                    className="ml-1 text-slate-400 hover:text-slate-600"
                    aria-label="Clear city search"
                  >
                    <X className="h-3.5 w-3.5" />
                  </button>
                )}
              </div>

              {dropdownOpen && (
                <div className="absolute left-0 right-0 top-full z-40 mt-1.5 overflow-hidden rounded-xl border border-teal-100 bg-white shadow-lg">
                  {searchError ? (
                    <div className="px-4 py-3 text-xs text-rose-600">{searchError}</div>
                  ) : results.length === 0 && !searching ? (
                    <div className="px-4 py-3 text-xs text-slate-500">
                      No matching locations found for &ldquo;{query}&rdquo;.
                    </div>
                  ) : (
                    <ul className="max-h-64 divide-y divide-slate-100 overflow-y-auto">
                      {results.map((loc, idx) => (
                        <li key={`${loc.name}-${loc.latitude}-${idx}`}>
                          <button
                            type="button"
                            onClick={() => pickLocation(loc)}
                            className="flex w-full items-center justify-between px-4 py-2.5 text-left text-xs transition hover:bg-teal-50"
                          >
                            <span className="flex items-center gap-2 font-medium text-slate-900">
                              <MapPin className="h-3.5 w-3.5 text-teal-600" />
                              <span>
                                {loc.name}
                                {loc.admin1 ? `, ${loc.admin1}` : ''}
                              </span>
                            </span>
                            <span className="text-[11px] text-slate-500">{loc.country}</span>
                          </button>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              )}
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {provenance && <ProvenanceBadge provenance={provenance} cached={cached} />}

            <button
              type="button"
              onClick={onToggleDemoMode}
              aria-pressed={demoMode}
              className={`inline-flex items-center gap-1.5 rounded-xl border px-3 py-1.5 text-xs font-semibold transition ${
                demoMode
                  ? 'border-amber-300 bg-amber-50 text-amber-900 hover:bg-amber-100'
                  : 'border-slate-200 bg-white text-slate-700 hover:bg-slate-50'
              }`}
              title="Toggle explicit synthetic demo data vs live API queries"
            >
              <FlaskConical className="h-3.5 w-3.5" />
              <span>{demoMode ? 'Demo Mode: ON' : 'Demo Mode: OFF'}</span>
            </button>

            <button
              type="button"
              onClick={onRefresh}
              disabled={loading}
              className="inline-flex items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 transition hover:bg-slate-50 disabled:opacity-50"
              aria-label="Refresh air quality data"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin text-teal-600' : ''}`} />
              <span className="hidden sm:inline">Refresh</span>
            </button>

            <button
              type="button"
              onClick={onOpenProfile}
              className="inline-flex items-center gap-1.5 rounded-xl bg-teal-600 px-3.5 py-1.5 text-xs font-semibold text-white shadow-sm transition hover:bg-teal-700"
            >
              <UserCheck className="h-3.5 w-3.5" />
              <span>{profile ? profile.name : 'Household Profile'}</span>
            </button>
          </div>
        </div>

        <div className="flex items-center gap-1.5 overflow-x-auto pb-0.5">
          <span className="shrink-0 text-[11px] font-medium text-slate-500">Quick cities:</span>
          {PRESET_LOCATIONS.map((preset) => {
            const active =
              preset.name.toLowerCase() === selectedLocation.name.toLowerCase() &&
              Math.abs(preset.latitude - selectedLocation.latitude) < 0.2
            return (
              <button
                key={preset.name}
                type="button"
                onClick={() => onSelectLocation(preset)}
                className={`shrink-0 rounded-full px-2.5 py-1 text-[11px] font-medium transition ${
                  active
                    ? 'bg-teal-600 text-white'
                    : 'bg-teal-50/70 text-teal-800 hover:bg-teal-100'
                }`}
              >
                {preset.name}
              </button>
            )
          })}
        </div>
      </div>
    </header>
  )
}
