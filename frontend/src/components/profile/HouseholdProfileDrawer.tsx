import { useEffect, useState } from 'react'
import { X, Users, Loader2, CheckCircle2, AlertCircle, Search } from 'lucide-react'
import { ApiError, getProfile, saveProfile } from '../../lib/api'
import type {
  BudgetTier,
  CommuteMode,
  CookingFuel,
  HomeType,
  HouseholdProfileCreate,
  HouseholdProfileOut,
  LocationOption,
} from '../../types/api'

interface HouseholdProfileDrawerProps {
  open: boolean
  onClose: () => void
  profile: HouseholdProfileOut | null
  onProfileLoaded: (profile: HouseholdProfileOut) => void
  activeLocation: LocationOption
}

export function HouseholdProfileDrawer({
  open,
  onClose,
  profile,
  onProfileLoaded,
  activeLocation,
}: HouseholdProfileDrawerProps) {
  const [lookupId, setLookupId] = useState(profile?.id ?? 'default-family')
  const [loadingLookup, setLoadingLookup] = useState(false)
  const [saving, setSaving] = useState(false)
  const [statusMessage, setStatusMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  const [form, setForm] = useState<HouseholdProfileCreate>({
    id: profile?.id ?? 'default-family',
    name: profile?.name ?? 'My Urban Household',
    city: profile?.city ?? activeLocation.name,
    country: profile?.country ?? activeLocation.country,
    latitude: profile?.latitude ?? activeLocation.latitude,
    longitude: profile?.longitude ?? activeLocation.longitude,
    household_size: profile?.household_size ?? 4,
    has_children: profile?.has_children ?? true,
    has_seniors: profile?.has_seniors ?? false,
    respiratory_conditions: profile?.respiratory_conditions ?? [],
    commute_mode: profile?.commute_mode ?? 'car',
    home_type: profile?.home_type ?? 'apartment',
    has_hepa_purifier: profile?.has_hepa_purifier ?? false,
    cooking_fuel: profile?.cooking_fuel ?? 'lpg',
    budget_tier: profile?.budget_tier ?? 'moderate',
  })

  useEffect(() => {
    if (profile) {
      setLookupId(profile.id)
      setForm({
        id: profile.id,
        name: profile.name,
        city: profile.city,
        country: profile.country,
        latitude: profile.latitude,
        longitude: profile.longitude,
        household_size: profile.household_size,
        has_children: profile.has_children,
        has_seniors: profile.has_seniors,
        respiratory_conditions: profile.respiratory_conditions,
        commute_mode: profile.commute_mode,
        home_type: profile.home_type,
        has_hepa_purifier: profile.has_hepa_purifier,
        cooking_fuel: profile.cooking_fuel,
        budget_tier: profile.budget_tier,
      })
    }
  }, [profile])

  if (!open) return null

  const handleFetchProfile = async () => {
    const id = lookupId.trim()
    if (!id) {
      setStatusMessage({ type: 'error', text: 'Enter a profile ID to look up.' })
      return
    }
    setLoadingLookup(true)
    setStatusMessage(null)
    try {
      const loaded = await getProfile(id)
      onProfileLoaded(loaded)
      setStatusMessage({ type: 'success', text: `Loaded saved profile '${loaded.id}'.` })
    } catch (err: unknown) {
      const msg =
        err instanceof ApiError
          ? err.status === 404
            ? `Profile '${id}' does not exist yet. Fill out the form below and save to create it.`
            : err.detail
          : 'Unable to reach profile service.'
      setStatusMessage({ type: 'error', text: msg })
    } finally {
      setLoadingLookup(false)
    }
  }

  const handleSaveProfile = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    setStatusMessage(null)
    try {
      const saved = await saveProfile({
        ...form,
        id: form.id?.trim() || undefined,
      })
      onProfileLoaded(saved)
      setStatusMessage({ type: 'success', text: `Profile '${saved.id}' saved to database.` })
    } catch (err: unknown) {
      setStatusMessage({
        type: 'error',
        text: err instanceof ApiError ? err.detail : 'Failed to save household profile.',
      })
    } finally {
      setSaving(false)
    }
  }

  const toggleSensitivity = (tag: string) => {
    setForm((prev) => {
      const exists = prev.respiratory_conditions.includes(tag)
      return {
        ...prev,
        respiratory_conditions: exists
          ? prev.respiratory_conditions.filter((x) => x !== tag)
          : [...prev.respiratory_conditions, tag],
      }
    })
  }

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs" onClick={onClose} />
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Household Profile Drawer"
        className="relative z-10 flex h-full w-full max-w-md flex-col bg-white shadow-2xl"
      >
        <div className="flex items-center justify-between border-b border-teal-100 px-6 py-4">
          <div className="flex items-center gap-2.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-teal-50 text-teal-700">
              <Users className="h-4 w-4" />
            </div>
            <div>
              <h2 className="text-base font-bold text-slate-900">Household Profile</h2>
              <p className="text-xs text-slate-500">Tailors exposure &amp; routine guidance</p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
            aria-label="Close profile drawer"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="flex-1 space-y-5 overflow-y-auto px-6 py-5">
          {/* Load existing profile via GET /api/v1/profiles/{profile_id} */}
          <div className="rounded-xl border border-teal-100 bg-teal-50/50 p-4">
            <label className="block text-xs font-semibold text-teal-900">
              Load Existing Profile by ID
            </label>
            <div className="mt-2 flex gap-2">
              <input
                type="text"
                value={lookupId}
                onChange={(e) => setLookupId(e.target.value)}
                placeholder="e.g., default-family"
                className="w-full rounded-lg border border-teal-200 bg-white px-3 py-1.5 text-xs text-slate-900 focus:border-teal-500 focus:outline-none"
              />
              <button
                type="button"
                onClick={handleFetchProfile}
                disabled={loadingLookup}
                className="inline-flex shrink-0 items-center gap-1.5 rounded-lg bg-teal-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-teal-700 disabled:opacity-50"
              >
                {loadingLookup ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Search className="h-3.5 w-3.5" />}
                Load
              </button>
            </div>
          </div>

          {statusMessage && (
            <div
              className={`flex items-start gap-2 rounded-xl border p-3 text-xs ${
                statusMessage.type === 'success'
                  ? 'border-emerald-200 bg-emerald-50 text-emerald-900'
                  : 'border-rose-200 bg-rose-50 text-rose-900'
              }`}
            >
              {statusMessage.type === 'success' ? (
                <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" />
              ) : (
                <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-rose-600" />
              )}
              <span>{statusMessage.text}</span>
            </div>
          )}

          <form onSubmit={handleSaveProfile} className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-slate-700">Profile ID</label>
                <input
                  type="text"
                  value={form.id ?? ''}
                  onChange={(e) => setForm({ ...form, id: e.target.value })}
                  pattern="[a-zA-Z0-9_\-]+"
                  placeholder="default-family"
                  className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-xs focus:border-teal-500 focus:outline-none"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-700">Household Name</label>
                <input
                  type="text"
                  required
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-xs focus:border-teal-500 focus:outline-none"
                />
              </div>
            </div>

            <div className="flex items-center justify-between rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs">
              <span className="text-slate-600">
                City: <strong className="text-slate-900">{form.city}</strong>
              </span>
              <button
                type="button"
                onClick={() =>
                  setForm((prev) => ({
                    ...prev,
                    city: activeLocation.name,
                    country: activeLocation.country,
                    latitude: activeLocation.latitude,
                    longitude: activeLocation.longitude,
                  }))
                }
                className="font-semibold text-teal-700 hover:underline"
              >
                Sync with {activeLocation.name}
              </button>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-slate-700">Household Size</label>
                <input
                  type="number"
                  min={1}
                  max={20}
                  value={form.household_size}
                  onChange={(e) => setForm({ ...form, household_size: Number(e.target.value) || 1 })}
                  className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-xs focus:border-teal-500 focus:outline-none"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-700">Commute Mode</label>
                <select
                  value={form.commute_mode}
                  onChange={(e) => setForm({ ...form, commute_mode: e.target.value as CommuteMode })}
                  className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-xs focus:border-teal-500 focus:outline-none"
                >
                  <option value="car">Petrol / Diesel Car</option>
                  <option value="two_wheeler">Two-Wheeler</option>
                  <option value="metro">Metro Rail</option>
                  <option value="bus">Public Bus</option>
                  <option value="cycle_walk">Cycle / Walk</option>
                  <option value="wfh">Work From Home</option>
                </select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-slate-700">Home Type</label>
                <select
                  value={form.home_type}
                  onChange={(e) => setForm({ ...form, home_type: e.target.value as HomeType })}
                  className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-xs focus:border-teal-500 focus:outline-none"
                >
                  <option value="apartment">Apartment</option>
                  <option value="independent_house">Independent House</option>
                  <option value="high_rise">High-Rise</option>
                  <option value="shared_housing">Shared Housing</option>
                </select>
              </div>
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
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-700">Budget Preference</label>
              <select
                value={form.budget_tier}
                onChange={(e) => setForm({ ...form, budget_tier: e.target.value as BudgetTier })}
                className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-xs focus:border-teal-500 focus:outline-none"
              >
                <option value="zero_cost">Zero-cost habits only</option>
                <option value="low">Low-cost (DIY / masks)</option>
                <option value="moderate">Moderate (HEPA filter)</option>
                <option value="flexible">Flexible</option>
              </select>
            </div>

            <div className="space-y-2 rounded-xl border border-slate-200 p-3">
              <p className="text-xs font-semibold text-slate-800">Vulnerable Groups &amp; Equipment</p>
              <label className="flex items-center gap-2 text-xs text-slate-700">
                <input
                  type="checkbox"
                  checked={form.has_children}
                  onChange={(e) => setForm({ ...form, has_children: e.target.checked })}
                  className="rounded border-slate-300 text-teal-600"
                />
                Children / infants in household
              </label>
              <label className="flex items-center gap-2 text-xs text-slate-700">
                <input
                  type="checkbox"
                  checked={form.has_seniors}
                  onChange={(e) => setForm({ ...form, has_seniors: e.target.checked })}
                  className="rounded border-slate-300 text-teal-600"
                />
                Older adults (60+) in household
              </label>
              <label className="flex items-center gap-2 text-xs text-slate-700">
                <input
                  type="checkbox"
                  checked={form.has_hepa_purifier}
                  onChange={(e) => setForm({ ...form, has_hepa_purifier: e.target.checked })}
                  className="rounded border-slate-300 text-teal-600"
                />
                Has HEPA / MERV-13 air purifier
              </label>
            </div>

            <div>
              <p className="text-xs font-medium text-slate-700">Respiratory Sensitivities</p>
              <div className="mt-2 flex flex-wrap gap-2">
                {['asthma', 'allergic_rhinitis', 'copd', 'cardiovascular'].map((tag) => {
                  const selected = form.respiratory_conditions.includes(tag)
                  return (
                    <button
                      key={tag}
                      type="button"
                      onClick={() => toggleSensitivity(tag)}
                      className={`rounded-full border px-2.5 py-1 text-[11px] font-medium transition ${
                        selected
                          ? 'border-teal-600 bg-teal-600 text-white'
                          : 'border-slate-200 bg-slate-50 text-slate-700 hover:bg-slate-100'
                      }`}
                    >
                      {tag.replace('_', ' ')}
                    </button>
                  )
                })}
              </div>
            </div>

            <button
              type="submit"
              disabled={saving}
              className="flex w-full items-center justify-center gap-2 rounded-xl bg-teal-600 px-4 py-2.5 text-xs font-semibold text-white shadow-sm transition hover:bg-teal-700 disabled:opacity-50"
            >
              {saving && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
              Save Household Profile
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}
