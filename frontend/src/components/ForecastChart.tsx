import type { SeriesForecast } from '../api'

interface Props {
  series: SeriesForecast
  label: string
  lastDay: number
}

const W = 460
const H = 170
const PAD = { l: 44, r: 10, t: 10, b: 24 }

// Small hand-made SVG chart: observed dots, fitted line, uncertainty band, threshold.
export default function ForecastChart({ series, label, lastDay }: Props) {
  const pts = series.projected
  const maxDay = pts[pts.length - 1]?.day ?? 1
  const maxY = Math.max(...series.observed.map(([, v]) => v), ...pts.map((p) => p.hi), series.threshold) * 1.05
  const x = (d: number) => PAD.l + (d / maxDay) * (W - PAD.l - PAD.r)
  const y = (v: number) => H - PAD.b - (v / maxY) * (H - PAD.t - PAD.b)

  const band =
    pts.map((p) => `${x(p.day)},${y(p.hi)}`).join(' ') +
    ' ' +
    [...pts].reverse().map((p) => `${x(p.day)},${y(p.lo)}`).join(' ')
  const line = pts.map((p) => `${x(p.day)},${y(p.mid)}`).join(' ')
  const ticks = [0, 0.25, 0.5, 0.75, 1].map((f) => Math.round(maxY * f * 100) / 100)

  return (
    <figure className="chart">
      <figcaption>
        {label}: now {series.current} (safe ≤ {series.threshold})
        {series.cross_day != null && (
          <> · crosses day {series.cross_day}
            {series.cross_lo != null && <> ({series.cross_lo}–{series.cross_hi})</>}</>
        )}
      </figcaption>
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`${label} forecast`}>
        {ticks.map((t) => (
          <g key={t}>
            <line x1={PAD.l} x2={W - PAD.r} y1={y(t)} y2={y(t)} stroke="#e5e7eb" />
            <text x={PAD.l - 4} y={y(t) + 3} textAnchor="end" fontSize="9" fill="#667">{t}</text>
          </g>
        ))}
        <polygon points={band} fill="#2b7bb9" opacity={0.18} />
        <polyline points={line} fill="none" stroke="#2b7bb9" strokeWidth={2} />
        {series.observed.map(([d, v]) => (
          <circle key={d} cx={x(d)} cy={y(v)} r={1.8} fill="#14202e" />
        ))}
        <line x1={PAD.l} x2={W - PAD.r} y1={y(series.threshold)} y2={y(series.threshold)}
          stroke="#2e9d57" strokeDasharray="5 4" strokeWidth={1.5} />
        <line x1={x(lastDay)} x2={x(lastDay)} y1={PAD.t} y2={H - PAD.b} stroke="#999" strokeDasharray="2 3" />
        <text x={x(lastDay) + 3} y={PAD.t + 9} fontSize="9" fill="#667">today</text>
        {series.cross_day != null && (
          <circle cx={x(series.cross_day)} cy={y(series.threshold)} r={4} fill="#2e9d57" />
        )}
        <text x={W - PAD.r} y={H - 6} textAnchor="end" fontSize="9" fill="#667">day {maxDay}</text>
        <text x={PAD.l} y={H - 6} fontSize="9" fill="#667">day 0</text>
      </svg>
    </figure>
  )
}
