import { CRITERION_COLOR } from '../api'

interface Props {
  contributions: Record<string, number>
  max?: number // value that fills the whole bar
}

// Stacked bar: each piece is weight x normalized value for one criterion.
export default function ContribBar({ contributions, max = 1 }: Props) {
  return (
    <div className="cbar" title={Object.entries(contributions).map(([k, v]) => `${k}: ${v.toFixed(3)}`).join('\n')}>
      {Object.entries(contributions).map(([k, v]) => (
        <div key={k} style={{ width: `${(v / max) * 100}%`, background: CRITERION_COLOR[k] ?? '#999' }} />
      ))}
    </div>
  )
}

export function Legend({ keys }: { keys: string[] }) {
  return (
    <div className="legend">
      {keys.map((k) => (
        <span key={k}>
          <i style={{ background: CRITERION_COLOR[k] ?? '#999' }} /> {k.replace('_', ' ')}
        </span>
      ))}
    </div>
  )
}
