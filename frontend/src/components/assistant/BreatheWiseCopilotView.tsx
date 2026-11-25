import { useState } from 'react'
import { Bot, Send, RotateCcw, Loader2, Sparkles, MapPin, Users } from 'lucide-react'
import { ApiError, sendChatMessage } from '../../lib/api'
import type {
  ChatResponse,
  Citation,
  CurrentAQIResponse,
  HouseholdProfileOut,
  LocationOption,
} from '../../types/api'
import { CitationsPanel } from '../ui/CitationsPanel'
import { ProvenanceBadge } from '../ui/ProvenanceBadge'
import { MedicalDisclaimerBanner } from '../ui/RecommendationCard'

interface BreatheWiseCopilotViewProps {
  location: LocationOption
  currentAqi: CurrentAQIResponse | null
  profile: HouseholdProfileOut | null
  demoMode: boolean
}

interface UiMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  citations?: Citation[]
  followups?: string[]
  generationMode?: string
  retrievalMode?: string
}

const QUICK_PROMPTS = [
  'Should children play outdoors right now given current AQI?',
  'How do I size a HEPA purifier or Corsi-Rosenthal box for a bedroom?',
  'When is the lowest-pollution window to air out our apartment?',
  'How much CO2e and PM2.5 does switching from car to metro avoid?',
]

export function BreatheWiseCopilotView({
  location,
  currentAqi,
  profile,
  demoMode,
}: BreatheWiseCopilotViewProps) {
  const [threadId, setThreadId] = useState<string>(() => `thread-${Date.now().toString(36)}`)
  const [messages, setMessages] = useState<UiMessage[]>([])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [latestResponse, setLatestResponse] = useState<ChatResponse | null>(null)

  const handleSend = async (promptText?: string) => {
    const text = (promptText ?? input).trim()
    if (!text || sending) return

    const userMsg: UiMessage = {
      id: `u-${Date.now()}`,
      role: 'user',
      content: text,
    }
    const nextHistory = [...messages, userMsg]
    setMessages(nextHistory)
    if (!promptText) setInput('')
    setSending(true)
    setError(null)

    try {
      const res = await sendChatMessage({
        message: text,
        thread_id: threadId,
        city: location.name,
        country: location.country,
        latitude: location.latitude,
        longitude: location.longitude,
        profile_id: profile?.id ?? null,
        history: nextHistory.slice(-8).map((m) => ({ role: m.role, content: m.content })),
        retrieval_mode: 'hybrid',
        top_k: 4,
        demo_mode: demoMode,
      })
      setLatestResponse(res)
      setMessages((prev) => [
        ...prev,
        {
          id: `a-${Date.now()}`,
          role: 'assistant',
          content: res.answer,
          citations: res.citations,
          followups: res.suggested_followups,
          generationMode: res.observability.generation_mode,
          retrievalMode: res.observability.retrieval_mode_used,
        },
      ])
    } catch (err: unknown) {
      setError(err instanceof ApiError ? err.detail : 'Unable to reach BreatheWise Copilot.')
    } finally {
      setSending(false)
    }
  }

  const handleNewThread = () => {
    setThreadId(`thread-${Date.now().toString(36)}`)
    setMessages([])
    setLatestResponse(null)
    setError(null)
  }

  return (
    <div className="space-y-5">
      {/* Context Bar (excludes sensitive health strings) */}
      <section className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-teal-100 bg-white px-5 py-4 shadow-sm">
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-teal-600 text-white">
            <Bot className="h-5 w-5" />
          </div>
          <div>
            <h2 className="text-base font-bold text-slate-900">BreatheWise AI Copilot</h2>
            <div className="mt-0.5 flex flex-wrap items-center gap-2 text-[11px] text-slate-600">
              <span className="inline-flex items-center gap-1">
                <MapPin className="h-3 w-3 text-teal-600" />
                {location.name}
              </span>
              {currentAqi && (
                <>
                  <span>• NAQI {currentAqi.indian_naqi.aqi ?? '—'}</span>
                  <span>• US EPA {currentAqi.us_epa_aqi.aqi ?? '—'}</span>
                  <ProvenanceBadge provenance={currentAqi.provenance} compact />
                </>
              )}
              {profile && (
                <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-0.5 font-medium text-emerald-800">
                  <Users className="h-3 w-3" />
                  Profile: {profile.household_size} members ({profile.commute_mode})
                </span>
              )}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="hidden rounded-lg bg-slate-100 px-2.5 py-1 font-mono text-[10px] text-slate-600 sm:inline">
            {threadId}
          </span>
          <button
            type="button"
            onClick={handleNewThread}
            className="inline-flex items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50"
          >
            <RotateCcw className="h-3.5 w-3.5" />
            New Thread
          </button>
        </div>
      </section>

      {/* Chat Transcript */}
      <section className="flex min-h-[420px] flex-col justify-between rounded-2xl border border-teal-100 bg-white p-5 shadow-sm">
        <div className="space-y-4">
          {messages.length === 0 ? (
            <div className="py-8 text-center">
              <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-teal-50 text-teal-600">
                <Sparkles className="h-6 w-6" />
              </div>
              <h3 className="mt-3 text-sm font-bold text-slate-900">
                Ask about {location.name} air quality, HEPA sizing, or low-emission routines
              </h3>
              <p className="mx-auto mt-1 max-w-md text-xs text-slate-500">
                Responses are grounded in WHO 2021, CPCB GRAP, US EPA, and ASHRAE documents with explicit source citations.
              </p>

              <div className="mx-auto mt-5 grid max-w-2xl gap-2 sm:grid-cols-2">
                {QUICK_PROMPTS.map((q) => (
                  <button
                    key={q}
                    type="button"
                    onClick={() => void handleSend(q)}
                    className="rounded-xl border border-teal-100 bg-teal-50/50 px-3.5 py-2.5 text-left text-xs font-medium text-teal-900 transition hover:border-teal-300 hover:bg-teal-50"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-[88%] rounded-2xl px-4 py-3 text-xs leading-relaxed ${
                    msg.role === 'user'
                      ? 'bg-teal-600 text-white'
                      : 'border border-slate-200 bg-slate-50/80 text-slate-800'
                  }`}
                >
                  <p className="whitespace-pre-wrap">{msg.content}</p>

                  {msg.role === 'assistant' && (
                    <div className="mt-2.5 space-y-2 border-t border-slate-200/80 pt-2">
                      <div className="flex flex-wrap items-center gap-1.5 text-[10px] text-slate-500">
                        <span>
                          Mode: <strong>{msg.generationMode}</strong> ({msg.retrievalMode})
                        </span>
                        {msg.citations?.map((c) => (
                          <span
                            key={c.chunk_id}
                            className="rounded bg-teal-50 px-1.5 py-0.5 font-mono font-semibold text-teal-800"
                          >
                            {c.doc_id}
                          </span>
                        ))}
                      </div>

                      {msg.followups && msg.followups.length > 0 && (
                        <div className="flex flex-wrap gap-1.5 pt-1">
                          {msg.followups.map((f) => (
                            <button
                              key={f}
                              type="button"
                              onClick={() => void handleSend(f)}
                              className="rounded-lg border border-teal-200 bg-white px-2.5 py-1 text-[11px] font-medium text-teal-800 hover:bg-teal-50"
                            >
                              {f}
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            ))
          )}

          {sending && (
            <div className="flex items-center gap-2 text-xs text-slate-500">
              <Loader2 className="h-4 w-4 animate-spin text-teal-600" />
              <span>Retrieving authoritative evidence and checking safety guardrails...</span>
            </div>
          )}

          {error && (
            <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-2.5 text-xs text-rose-800">
              {error}
            </div>
          )}
        </div>

        <form
          onSubmit={(e) => {
            e.preventDefault()
            void handleSend()
          }}
          className="mt-5 flex gap-2 border-t border-slate-100 pt-4"
        >
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={`Ask BreatheWise Copilot about ${location.name}...`}
            aria-label="Ask BreatheWise Copilot"
            className="flex-1 rounded-xl border border-slate-200 bg-slate-50 px-4 py-2.5 text-xs text-slate-900 focus:border-teal-500 focus:bg-white focus:outline-none"
          />
          <button
            type="submit"
            disabled={sending || !input.trim()}
            className="inline-flex items-center gap-1.5 rounded-xl bg-teal-600 px-4 py-2.5 text-xs font-semibold text-white shadow-xs transition hover:bg-teal-700 disabled:opacity-50"
          >
            <Send className="h-3.5 w-3.5" />
            Send
          </button>
        </form>
      </section>

      {latestResponse && latestResponse.citations.length > 0 && (
        <CitationsPanel citations={latestResponse.citations} title="Latest Response Citations" />
      )}

      <MedicalDisclaimerBanner
        text={
          latestResponse?.medical_disclaimer ??
          'Educational environmental guidance based on WHO, CPCB, US EPA, and ASHRAE references; consult a qualified clinician for personal medical advice.'
        }
      />
    </div>
  )
}
