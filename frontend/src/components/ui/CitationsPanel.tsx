import { BookOpen, ExternalLink } from 'lucide-react'
import type { Citation } from '../../types/api'

interface CitationsPanelProps {
  citations: Citation[]
  title?: string
}

export function CitationsPanel({ citations, title = 'Authoritative Evidence & Citations' }: CitationsPanelProps) {
  if (!citations.length) return null

  return (
    <section className="rounded-2xl border border-teal-100 bg-white p-5 shadow-sm">
      <h3 className="flex items-center gap-2 text-sm font-bold text-slate-900">
        <BookOpen className="h-4 w-4 text-teal-600" />
        {title}
      </h3>
      <div className="mt-4 grid gap-3 md:grid-cols-2">
        {citations.map((c) => (
          <div
            key={c.chunk_id}
            className="flex flex-col justify-between rounded-xl border border-slate-200 bg-slate-50/70 p-3.5 text-xs"
          >
            <div>
              <div className="flex items-start justify-between gap-2">
                <span className="font-semibold text-slate-900">{c.title}</span>
                <span className="shrink-0 rounded bg-teal-50 px-2 py-0.5 font-mono text-[10px] font-semibold text-teal-800">
                  {c.doc_id}
                </span>
              </div>
              <p className="mt-0.5 text-[11px] font-medium text-teal-700">
                {c.source_org} • v{c.doc_version}
              </p>
              <p className="mt-2 line-clamp-3 leading-relaxed text-slate-600">{c.excerpt}</p>
            </div>

            <div className="mt-2.5 flex items-center justify-between border-t border-slate-200/70 pt-2 text-[11px] text-slate-500">
              <span>Score: {c.relevance_score.toFixed(2)}</span>
              {c.source_url && (
                <a
                  href={c.source_url}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1 font-semibold text-teal-700 hover:underline"
                >
                  Source
                  <ExternalLink className="h-3 w-3" />
                </a>
              )}
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}
