import {
  LayoutDashboard,
  Sparkles,
  Home,
  CalendarClock,
  Leaf,
  Bot,
  Users,
  MessageSquareHeart,
  X,
  MapPin,
  ShieldCheck,
} from 'lucide-react'
import type { AqiStandard, HouseholdProfileOut, LocationOption } from '../../types/api'

export type NavSection =
  | 'dashboard'
  | 'recommendations'
  | 'indoor'
  | 'routine'
  | 'impact'
  | 'assistant'
  | 'community'

interface SidebarProps {
  activeSection: NavSection
  onSelectSection: (section: NavSection) => void
  mobileOpen: boolean
  onCloseMobile: () => void
  selectedLocation: LocationOption
  activeStandard: AqiStandard
  profile: HouseholdProfileOut | null
  onOpenProfile: () => void
}

const NAV_ITEMS: Array<{
  id: NavSection
  label: string
  icon: typeof LayoutDashboard
}> = [
  { id: 'dashboard', label: 'Air Quality Dashboard', icon: LayoutDashboard },
  { id: 'recommendations', label: 'AI Recommendations', icon: Sparkles },
  { id: 'indoor', label: 'Indoor Air Advisor', icon: Home },
  { id: 'routine', label: 'Smart Routine Planner', icon: CalendarClock },
  { id: 'impact', label: 'Sustainability Tracker', icon: Leaf },
  { id: 'assistant', label: 'BreatheWise Copilot', icon: Bot },
  { id: 'community', label: 'Community Insights', icon: MessageSquareHeart },
]

export function Sidebar({
  activeSection,
  onSelectSection,
  mobileOpen,
  onCloseMobile,
  selectedLocation,
  activeStandard,
  profile,
  onOpenProfile,
}: SidebarProps) {
  const sidebarBody = (
    <div className="flex h-full flex-col justify-between bg-white px-4 py-5">
      <div>
        <div className="flex items-center justify-between px-2">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-teal-600 to-emerald-500 text-white shadow-sm">
              <Leaf className="h-5 w-5" />
            </div>
            <div>
              <span className="block text-base font-bold tracking-tight text-slate-900">BreatheWise</span>
              <span className="block text-[11px] font-medium text-teal-700">Urban Air Assistant</span>
            </div>
          </div>
          <button
            type="button"
            onClick={onCloseMobile}
            className="rounded-lg p-1.5 text-slate-500 hover:bg-slate-100 lg:hidden"
            aria-label="Close navigation menu"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="mt-6 rounded-xl border border-teal-100 bg-teal-50/60 p-3">
          <div className="flex items-center gap-2 text-xs font-semibold text-teal-900">
            <MapPin className="h-3.5 w-3.5 text-teal-600" />
            <span className="truncate">
              {selectedLocation.name}, {selectedLocation.country}
            </span>
          </div>
          <p className="mt-1 text-[11px] text-teal-700">
            Active Scale: {activeStandard === 'CPCB_NAQI' ? 'Indian CPCB NAQI' : 'US EPA AQI'}
          </p>
        </div>

        <nav className="mt-6 space-y-1" aria-label="Primary navigation">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon
            const isActive = activeSection === item.id
            return (
              <button
                key={item.id}
                type="button"
                onClick={() => {
                  onSelectSection(item.id)
                  onCloseMobile()
                }}
                className={`flex w-full items-center justify-between rounded-xl px-3 py-2.5 text-left text-sm font-medium transition ${
                  isActive
                    ? 'bg-teal-600 text-white shadow-sm'
                    : 'text-slate-700 hover:bg-teal-50 hover:text-teal-900'
                }`}
              >
                <span className="flex items-center gap-2.5">
                  <Icon className="h-4 w-4 shrink-0" />
                  <span>{item.label}</span>
                </span>
              </button>
            )
          })}
        </nav>
      </div>

      <div className="space-y-3 border-t border-slate-100 pt-4">
        <button
          type="button"
          onClick={() => {
            onOpenProfile()
            onCloseMobile()
          }}
          className="flex w-full items-center gap-3 rounded-xl border border-slate-200 bg-slate-50/80 p-3 text-left transition hover:border-teal-300 hover:bg-teal-50/50"
        >
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-emerald-100 text-emerald-700">
            <Users className="h-4 w-4" />
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate text-xs font-semibold text-slate-900">
              {profile ? profile.name : 'No Household Profile'}
            </p>
            <p className="truncate text-[11px] text-slate-500">
              {profile
                ? `${profile.household_size} members • ${profile.commute_mode}`
                : 'Load or create profile'}
            </p>
          </div>
        </button>

        <div className="flex items-center gap-2 px-2 text-[11px] text-slate-500">
          <ShieldCheck className="h-3.5 w-3.5 text-emerald-600" />
          <span>WHO / CPCB / US EPA grounded</span>
        </div>
      </div>
    </div>
  )

  return (
    <>
      <aside className="hidden w-72 shrink-0 border-r border-teal-100 bg-white lg:block">
        {sidebarBody}
      </aside>

      {mobileOpen && (
        <div className="fixed inset-0 z-50 flex lg:hidden">
          <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs" onClick={onCloseMobile} />
          <aside className="relative z-10 w-72 max-w-[85vw] border-r border-teal-100 bg-white shadow-xl">
            {sidebarBody}
          </aside>
        </div>
      )}
    </>
  )
}
