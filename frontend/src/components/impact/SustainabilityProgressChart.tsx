import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { DailyImpactPoint } from '../../types/api'

interface SustainabilityProgressChartProps {
  series: DailyImpactPoint[]
}

export function SustainabilityProgressChart({ series }: SustainabilityProgressChartProps) {
  return (
    <div className="h-64 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={series} margin={{ top: 10, right: 12, left: -12, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
          <XAxis dataKey="date_label" tick={{ fontSize: 11, fill: '#64748b' }} />
          <YAxis tick={{ fontSize: 11, fill: '#64748b' }} />
          <Tooltip
            contentStyle={{
              borderRadius: '0.75rem',
              borderColor: '#ccfbf1',
              fontSize: '12px',
            }}
          />
          <Legend wrapperStyle={{ fontSize: '12px' }} />
          <Bar dataKey="co2e_kg_avoided" name="CO2e Avoided (kg)" fill="#059669" radius={[6, 6, 0, 0]} />
          <Bar
            dataKey="exposure_hours_saved"
            name="Exposure Protected (hrs)"
            fill="#0d9488"
            radius={[6, 6, 0, 0]}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

export default SustainabilityProgressChart
