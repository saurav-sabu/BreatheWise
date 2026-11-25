import { Shield, Leaf, Layers, AlertCircle, Gauge, Wallet, Info } from 'lucide-react'
import type { RecommendationItem } from '../../types/api'

interface RecommendationCardProps {
  item: RecommendationItem
}

const PRIORITY_STYLES: Record<RecommendationItem['priority'], string> = {
  urgent: 'border-rose-200 bg-rose-50 text-rose-800',
  high: 'border-orange-200 bg-orange-50 text-orange-800',
  medium: 'border-amber-200 bg-amber-50 text-amber-800',
  low: 'border-slate-200 bg-slate-100 text-slate-700',
}

const COST_LABELS: Record<RecommendationItem['estimated_cost'], string> = {
  free: 'Free',
  low_cost: 'Low Cost',
  moderate: 'Moderate Cost',
  investment: 'Investment',
}

export function RecommendationCard({ item }: RecommendationCardProps) {
  const benefitBadge =
    item.benefit_type === 'exposure_reduction'
      ? {
          label: 'Exposure Reduction',
          cls: 'border-teal-200 bg-teal-50 text-teal-800',
          Icon: Shield,
        }
      : item.benefit_type === 'emissions_reduction'
        ? {
            label: 'Emissions Reduction',
            cls: 'border-emerald-200 bg-emerald-50 text-emerald-800',
            Icon: Leaf,
          }
        : {
            label: 'Exposure + Emissions',
            cls: 'border-cyan-200 bg-cyan-50 text-cyan-900',
            Icon: Layers,
          }

  const BenefitIcon = benefitBadge.Icon

  return (
    <article className="flex flex-col justify-between rounded-2xl border border-teal-100 bg-white p-5 shadow-xs transition hover:border-teal-200">
      <div>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex flex-wrap items-center gap-2">
            <span
              className={`rounded-full border px-2.5 py-0.5 text-[11px] font-bold uppercase tracking-wide ${PRIORITY_STYLES[item.priority]}`}
            >
              {item.priority}
            </span>
            <span
              className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-[11px] font-semibold ${benefitBadge.cls}`}
            >
              <BenefitIcon className="h-3 w-3" />
              {benefitBadge.label}
            </span>
          </div>

          <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-[11px] font-medium text-slate-600">
            Confidence: <strong className="capitalize text-slate-800">{item.confidence}</strong>
          </span>
        </div>

        <h3 className="mt-3 text-base font-bold text-slate-900">{item.title}</h3>
        <p className="mt-2 text-xs leading-relaxed text-slate-700">{item.explanation}</p>

        <div className="mt-3 grid gap-2.5 rounded-xl border border-slate-100 bg-slate-50/80 p-3 text-xs">
          <div>
            <span className="font-semibold text-teal-900">Expected Benefit: </span>
            <span className="text-slate-700">{item.expected_benefit}</span>
          </div>
          <div>
            <span className="font-semibold text-slate-800">Supporting Evidence: </span>
            <span className="text-slate-600">{item.supporting_evidence}</span>
          </div>
        </div>
      </div>

      <div className="mt-4 space-y-2.5 border-t border-slate-100 pt-3">
        <div className="flex flex-wrap items-center gap-2 text-[11px] text-slate-600">
          <span className="inline-flex items-center gap-1 rounded-lg bg-slate-100 px-2.5 py-1 font-medium">
            <Gauge className="h-3 w-3 text-teal-600" />
            Effort: <strong className="capitalize">{item.effort_level}</strong>
          </span>
          <span className="inline-flex items-center gap-1 rounded-lg bg-slate-100 px-2.5 py-1 font-medium">
            <Wallet className="h-3 w-3 text-emerald-600" />
            Cost: <strong>{COST_LABELS[item.estimated_cost]}</strong>
          </span>
          {item.citation_doc_ids.map((docId) => (
            <span
              key={docId}
              className="rounded-lg border border-teal-200 bg-teal-50/70 px-2 py-0.5 font-mono text-[10px] font-semibold text-teal-800"
            >
              {docId}
            </span>
          ))}
        </div>

        <p className="flex items-start gap-1.5 text-[11px] text-slate-500">
          <Info className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-600" />
          <span>
            <strong>Limitations:</strong> {item.limitations}
          </span>
        </p>
      </div>
    </article>
  )
}

export function MedicalDisclaimerBanner({ text }: { text: string }) {
  return (
    <div className="flex items-start gap-2.5 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-xs text-slate-600">
      <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-teal-600" />
      <span>{text}</span>
    </div>
  )
}
