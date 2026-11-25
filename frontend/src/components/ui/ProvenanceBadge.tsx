import { Radio, Cpu, TrendingUp, FlaskConical } from 'lucide-react'
import type { DataProvenance } from '../../types/api'
import { getProvenanceMeta } from '../../lib/aqiUtils'

interface ProvenanceBadgeProps {
  provenance: DataProvenance
  cached?: boolean
  compact?: boolean
}

export function ProvenanceBadge({ provenance, cached = false, compact = false }: ProvenanceBadgeProps) {
  const meta = getProvenanceMeta(provenance)

  const Icon =
    provenance === 'measured'
      ? Radio
      : provenance === 'modeled_current'
        ? Cpu
        : provenance === 'forecast'
          ? TrendingUp
          : FlaskConical

  return (
    <span
      title={meta.description}
      className={`inline-flex items-center gap-1.5 rounded-full border font-medium ${meta.bgClass} ${meta.textClass} ${meta.borderClass} ${
        compact ? 'px-2.5 py-0.5 text-[11px]' : 'px-3 py-1 text-xs'
      }`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${meta.dotClass}`} />
      <Icon className="h-3.5 w-3.5" />
      <span>{meta.label}</span>
      {cached && !compact && (
        <span className="ml-1 rounded bg-white/70 px-1.5 py-0.2 text-[10px] font-semibold uppercase tracking-wide">
          Cached
        </span>
      )}
    </span>
  )
}
