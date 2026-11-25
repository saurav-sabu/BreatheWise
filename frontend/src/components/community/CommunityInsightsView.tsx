import { useCallback, useEffect, useState } from 'react'
import {
  Users,
  ThumbsUp,
  Flag,
  MessageSquarePlus,
  AlertTriangle,
  CheckCircle2,
  Loader2,
  Eye,
  Lightbulb,
  HandHeart,
} from 'lucide-react'
import {
  ApiError,
  createCommunityPost,
  getCommunityPosts,
  getCommunitySummary,
  reportCommunityPost,
  upvoteCommunityPost,
} from '../../lib/api'
import type {
  CommunityFeedResponse,
  CommunityPostType,
  CommunitySummaryResponse,
  LocationOption,
  ReportReason,
} from '../../types/api'
import { EmptyStateCard, ErrorBannerCard } from '../ui/StateCards'

interface CommunityInsightsViewProps {
  location: LocationOption
}

const TYPE_META: Record<CommunityPostType, { label: string; cls: string; Icon: typeof Eye }> = {
  observation: { label: 'Observation', cls: 'bg-amber-50 text-amber-800 border-amber-200', Icon: Eye },
  tip: { label: 'Clean-Air Tip', cls: 'bg-teal-50 text-teal-800 border-teal-200', Icon: Lightbulb },
  pledge: { label: 'Action Pledge', cls: 'bg-emerald-50 text-emerald-800 border-emerald-200', Icon: HandHeart },
}

export function CommunityInsightsView({ location }: CommunityInsightsViewProps) {
  const [filterType, setFilterType] = useState<CommunityPostType | 'all'>('all')
  const [feed, setFeed] = useState<CommunityFeedResponse | null>(null)
  const [summary, setSummary] = useState<CommunitySummaryResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [alias, setAlias] = useState('')
  const [neighborhood, setNeighborhood] = useState('')
  const [postType, setPostType] = useState<CommunityPostType>('pledge')
  const [title, setTitle] = useState('')
  const [body, setBody] = useState('')
  const [actionTag, setActionTag] = useState('metro_commute')
  const [submitting, setSubmitting] = useState(false)
  const [feedback, setFeedback] = useState<{ type: 'ok' | 'err'; text: string } | null>(null)

  const [reportingId, setReportingId] = useState<number | null>(null)
  const [reportReason, setReportReason] = useState<ReportReason>('misinformation')

  const loadCommunity = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [fRes, sRes] = await Promise.all([
        getCommunityPosts(location.name, filterType === 'all' ? null : filterType),
        getCommunitySummary(location.name),
      ])
      setFeed(fRes)
      setSummary(sRes)
    } catch (err: unknown) {
      setError(err instanceof ApiError ? err.detail : 'Unable to load community feed.')
    } finally {
      setLoading(false)
    }
  }, [location.name, filterType])

  useEffect(() => {
    void loadCommunity()
  }, [loadCommunity])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSubmitting(true)
    setFeedback(null)
    try {
      await createCommunityPost({
        city: location.name,
        neighborhood: neighborhood.trim() || 'Citywide',
        author_alias: alias.trim() || 'Resident',
        post_type: postType,
        title: title.trim(),
        body: body.trim(),
        action_tag: actionTag || null,
      })
      setTitle('')
      setBody('')
      setFeedback({ type: 'ok', text: `Published to ${location.name} community feed.` })
      await loadCommunity()
    } catch (err: unknown) {
      setFeedback({
        type: 'err',
        text: err instanceof ApiError ? err.detail : 'Failed to publish post.',
      })
    } finally {
      setSubmitting(false)
    }
  }

  const handleUpvote = async (postId: number) => {
    try {
      await upvoteCommunityPost(postId)
      await loadCommunity()
    } catch {
      // Ignore transient upvote error
    }
  }

  const handleReport = async (postId: number) => {
    try {
      const res = await reportCommunityPost(postId, reportReason)
      setReportingId(null)
      setFeedback({ type: 'ok', text: res.message })
      await loadCommunity()
    } catch (err: unknown) {
      setFeedback({
        type: 'err',
        text: err instanceof ApiError ? err.detail : 'Unable to submit moderation report.',
      })
    }
  }

  return (
    <div className="space-y-6">
      {/* Unverified User-Contributed Provenance Notice */}
      <div className="flex items-start gap-3 rounded-2xl border border-amber-300 bg-amber-50 px-5 py-3.5 text-xs text-amber-950">
        <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-700" />
        <div>
          <p className="font-bold">Resident-Contributed Feed — Separate from Official AQI Data</p>
          <p className="mt-0.5">
            Posts below are unverified observations, clean-air tips, and pledges submitted by residents.
            Personal emails, phone numbers, HTML, and medical cure claims are automatically blocked.
          </p>
        </div>
      </div>

      {/* City Community Summary */}
      {summary && (
        <section className="rounded-2xl border border-teal-100 bg-white p-6 shadow-sm">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="flex items-center gap-2 text-lg font-bold text-slate-900">
                <Users className="h-5 w-5 text-teal-600" />
                {location.name} Community Insights
              </h2>
              <p className="mt-0.5 text-xs text-slate-500">{summary.disclaimer}</p>
            </div>
            <div className="flex gap-1.5">
              {(['all', 'observation', 'tip', 'pledge'] as const).map((t) => (
                <button
                  key={t}
                  type="button"
                  onClick={() => setFilterType(t)}
                  className={`rounded-full px-3 py-1 text-xs font-semibold capitalize transition ${
                    filterType === t
                      ? 'bg-teal-600 text-white'
                      : 'bg-teal-50 text-teal-800 hover:bg-teal-100'
                  }`}
                >
                  {t}
                </button>
              ))}
            </div>
          </div>

          <div className="mt-4 grid gap-3 sm:grid-cols-4">
            <div className="rounded-xl border border-slate-200 bg-slate-50 p-3.5">
              <p className="text-[11px] text-slate-500">Published Posts</p>
              <p className="mt-1 text-2xl font-extrabold text-slate-900">{summary.total_published_posts}</p>
            </div>
            <div className="rounded-xl border border-emerald-200 bg-emerald-50/70 p-3.5">
              <p className="text-[11px] text-emerald-800">Action Pledges</p>
              <p className="mt-1 text-2xl font-extrabold text-emerald-950">{summary.pledges_count}</p>
            </div>
            <div className="rounded-xl border border-teal-200 bg-teal-50/70 p-3.5">
              <p className="text-[11px] text-teal-800">Clean-Air Tips</p>
              <p className="mt-1 text-2xl font-extrabold text-teal-950">{summary.tips_count}</p>
            </div>
            <div className="rounded-xl border border-amber-200 bg-amber-50/70 p-3.5">
              <p className="text-[11px] text-amber-800">Observations / Upvotes</p>
              <p className="mt-1 text-2xl font-extrabold text-amber-950">
                {summary.observations_count} / {summary.total_upvotes}
              </p>
            </div>
          </div>
        </section>
      )}

      {feedback && (
        <div
          className={`flex items-center gap-2 rounded-xl border px-4 py-3 text-xs ${
            feedback.type === 'ok'
              ? 'border-emerald-200 bg-emerald-50 text-emerald-900'
              : 'border-rose-200 bg-rose-50 text-rose-900'
          }`}
        >
          {feedback.type === 'ok' ? (
            <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-600" />
          ) : (
            <AlertTriangle className="h-4 w-4 shrink-0 text-rose-600" />
          )}
          <span>{feedback.text}</span>
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-12">
        {/* Post Composer */}
        <section className="rounded-2xl border border-teal-100 bg-white p-6 shadow-sm lg:col-span-5">
          <h3 className="flex items-center gap-2 text-base font-bold text-slate-900">
            <MessageSquarePlus className="h-4 w-4 text-teal-600" />
            Share Observation, Tip, or Pledge
          </h3>
          <form onSubmit={handleSubmit} className="mt-4 space-y-3.5">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-slate-700">Public Alias</label>
                <input
                  type="text"
                  required
                  minLength={2}
                  maxLength={80}
                  value={alias}
                  onChange={(e) => setAlias(e.target.value)}
                  placeholder="e.g., GreenCommuter"
                  className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-xs focus:border-teal-500 focus:outline-none"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-700">Neighborhood</label>
                <input
                  type="text"
                  maxLength={120}
                  value={neighborhood}
                  onChange={(e) => setNeighborhood(e.target.value)}
                  placeholder="e.g., Indirapuram"
                  className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-xs focus:border-teal-500 focus:outline-none"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-slate-700">Post Type</label>
                <select
                  value={postType}
                  onChange={(e) => setPostType(e.target.value as CommunityPostType)}
                  className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-xs focus:border-teal-500 focus:outline-none"
                >
                  <option value="pledge">Action Pledge</option>
                  <option value="tip">Clean-Air Tip</option>
                  <option value="observation">Local Observation</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-700">Action Tag</label>
                <select
                  value={actionTag}
                  onChange={(e) => setActionTag(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-xs focus:border-teal-500 focus:outline-none"
                >
                  <option value="metro_commute">Metro Commute</option>
                  <option value="no_waste_burning">No Waste Burning</option>
                  <option value="hepa_clean_room">HEPA Clean Room</option>
                  <option value="carpool">Carpooling</option>
                  <option value="dust_control">Water Sprinkling / Dust</option>
                </select>
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-700">Title</label>
              <input
                type="text"
                required
                minLength={4}
                maxLength={180}
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g., Switching 3 days/week to Metro this winter"
                className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-xs focus:border-teal-500 focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-700">Details</label>
              <textarea
                required
                minLength={8}
                maxLength={1200}
                rows={3}
                value={body}
                onChange={(e) => setBody(e.target.value)}
                placeholder="Share a practical local tip, smog observation, or pledge (no emails/phone numbers)."
                className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-xs focus:border-teal-500 focus:outline-none"
              />
            </div>

            <button
              type="submit"
              disabled={submitting}
              className="flex w-full items-center justify-center gap-2 rounded-xl bg-teal-600 px-4 py-2.5 text-xs font-semibold text-white hover:bg-teal-700 disabled:opacity-50"
            >
              {submitting && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
              Publish to {location.name} Feed
            </button>
          </form>
        </section>

        {/* Community Feed */}
        <section className="space-y-3 lg:col-span-7">
          {error ? (
            <ErrorBannerCard title="Community Feed Unavailable" message={error} onRetry={() => void loadCommunity()} />
          ) : loading && !feed ? (
            <div className="h-64 animate-pulse rounded-2xl bg-white" />
          ) : !feed || feed.posts.length === 0 ? (
            <EmptyStateCard
              title={`No Community Posts Yet for ${location.name}`}
              description="Be the first resident to share a clean-air tip, local observation, or winter commute pledge."
            />
          ) : (
            feed.posts.map((post) => {
              const meta = TYPE_META[post.post_type]
              const TypeIcon = meta.Icon
              return (
                <article key={post.id} className="rounded-2xl border border-teal-100 bg-white p-5 shadow-xs">
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-[11px] font-semibold ${meta.cls}`}>
                        <TypeIcon className="h-3 w-3" />
                        {meta.label}
                      </span>
                      <span className="text-[11px] font-medium text-slate-500">
                        {post.neighborhood} • by <strong className="text-slate-700">{post.author_alias}</strong>
                      </span>
                    </div>
                    {post.action_tag && (
                      <span className="rounded bg-slate-100 px-2 py-0.5 font-mono text-[10px] text-slate-600">
                        #{post.action_tag}
                      </span>
                    )}
                  </div>

                  <h4 className="mt-2.5 text-sm font-bold text-slate-900">{post.title}</h4>
                  <p className="mt-1.5 text-xs leading-relaxed text-slate-700">{post.body}</p>

                  <div className="mt-3 flex flex-wrap items-center justify-between gap-2 border-t border-slate-100 pt-2.5 text-xs">
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={() => void handleUpvote(post.id)}
                        className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 px-2.5 py-1 text-[11px] font-semibold text-slate-700 hover:bg-teal-50"
                      >
                        <ThumbsUp className="h-3 w-3 text-teal-600" />
                        {post.upvotes}
                      </button>
                      <button
                        type="button"
                        onClick={() => setReportingId(reportingId === post.id ? null : post.id)}
                        className="inline-flex items-center gap-1 rounded-lg px-2 py-1 text-[11px] text-slate-500 hover:bg-rose-50 hover:text-rose-700"
                      >
                        <Flag className="h-3 w-3" />
                        Report
                      </button>
                    </div>
                    <span className="text-[10px] text-slate-400">
                      {new Date(post.created_at).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' })}
                    </span>
                  </div>

                  {reportingId === post.id && (
                    <div className="mt-3 flex flex-wrap items-center gap-2 rounded-xl border border-rose-200 bg-rose-50/70 p-2.5 text-xs">
                      <select
                        value={reportReason}
                        onChange={(e) => setReportReason(e.target.value as ReportReason)}
                        className="rounded-lg border border-rose-200 bg-white px-2 py-1 text-xs"
                      >
                        <option value="misinformation">Misinformation</option>
                        <option value="medical_claim">Unsupported Medical Claim</option>
                        <option value="spam">Spam</option>
                        <option value="abusive">Abusive Content</option>
                        <option value="pii_leak">Personal Data Leak</option>
                      </select>
                      <button
                        type="button"
                        onClick={() => void handleReport(post.id)}
                        className="rounded-lg bg-rose-600 px-3 py-1 text-xs font-semibold text-white hover:bg-rose-700"
                      >
                        Submit Report
                      </button>
                    </div>
                  )}
                </article>
              )
            })
          )}
        </section>
      </div>
    </div>
  )
}
