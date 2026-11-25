import { AlertTriangle, RefreshCw, FlaskConical, Inbox } from 'lucide-react'

export function DashboardSkeleton() {
  return (
    <div className="space-y-6 animate-pulse" aria-label="Loading air quality data">
      <div className="grid gap-6 lg:grid-cols-12">
        <div className="h-72 rounded-2xl border border-teal-100 bg-white p-6 lg:col-span-5">
          <div className="h-4 w-40 rounded bg-slate-200" />
          <div className="mx-auto mt-8 h-32 w-56 rounded-t-full bg-slate-100" />
          <div className="mt-6 h-4 w-3/4 rounded bg-slate-100" />
        </div>
        <div className="h-72 rounded-2xl border border-teal-100 bg-white p-6 lg:col-span-7">
          <div className="h-4 w-48 rounded bg-slate-200" />
          <div className="mt-6 grid grid-cols-2 gap-4 sm:grid-cols-3">
            {Array.from({ length: 6 }).map((_, idx) => (
              <div key={idx} className="h-24 rounded-xl bg-slate-100" />
            ))}
          </div>
        </div>
      </div>
      <div className="h-72 rounded-2xl border border-teal-100 bg-white p-6">
        <div className="h-4 w-52 rounded bg-slate-200" />
        <div className="mt-6 h-48 rounded-xl bg-slate-100" />
      </div>
    </div>
  )
}

interface ErrorBannerCardProps {
  title: string
  message: string
  onRetry: () => void
  onEnableDemo?: () => void
}

export function ErrorBannerCard({ title, message, onRetry, onEnableDemo }: ErrorBannerCardProps) {
  return (
    <div className="rounded-2xl border border-rose-200 bg-white p-6 shadow-sm">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex items-start gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-rose-50 text-rose-600">
            <AlertTriangle className="h-5 w-5" />
          </div>
          <div>
            <h3 className="text-base font-semibold text-slate-900">{title}</h3>
            <p className="mt-1 text-sm text-slate-600">{message}</p>
            <p className="mt-2 text-xs text-slate-500">
              BreatheWise never fabricates live readings when upstream providers are unreachable.
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          <button
            type="button"
            onClick={onRetry}
            className="inline-flex items-center gap-1.5 rounded-xl bg-teal-600 px-4 py-2 text-xs font-semibold text-white shadow-sm transition hover:bg-teal-700"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            Retry Live Data
          </button>
          {onEnableDemo && (
            <button
              type="button"
              onClick={onEnableDemo}
              className="inline-flex items-center gap-1.5 rounded-xl border border-amber-300 bg-amber-50 px-4 py-2 text-xs font-semibold text-amber-900 transition hover:bg-amber-100"
            >
              <FlaskConical className="h-3.5 w-3.5" />
              View Demo Snapshot
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

interface EmptyStateCardProps {
  title: string
  description: string
}

export function EmptyStateCard({ title, description }: EmptyStateCardProps) {
  return (
    <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-teal-200 bg-teal-50/30 px-6 py-10 text-center">
      <div className="flex h-11 w-11 items-center justify-center rounded-full bg-teal-100 text-teal-700">
        <Inbox className="h-5 w-5" />
      </div>
      <h3 className="mt-3 text-sm font-semibold text-slate-900">{title}</h3>
      <p className="mt-1 max-w-md text-xs text-slate-600">{description}</p>
    </div>
  )
}
