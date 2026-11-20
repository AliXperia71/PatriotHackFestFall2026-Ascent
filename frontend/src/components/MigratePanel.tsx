import type { MigratePlan } from '../api'

export const WAVE_COLORS = ['#1b9e77', '#66a61e', '#e6ab02', '#d95f02', '#7570b3', '#e7298a', '#a6761d']

export function waveColor(w: number | null | undefined): string {
  return w == null ? '#8a8f98' : WAVE_COLORS[(w - 1) % WAVE_COLORS.length]
}

interface Props {
  plan: MigratePlan | null
}

export default function MigratePanel({ plan }: Props) {
  if (!plan) return <p className="hint">Loading plan...</p>
  const waves = Object.entries(plan.wave_totals).filter(([, n]) => n > 0)
  const maxW = plan.limits.supply_per_wave
  return (
    <div>
      <h3>Migration waves</h3>
      <p>
        <b>{plan.placed.toLocaleString()}</b> of {plan.total_population.toLocaleString()} people placed in{' '}
        {waves.length} waves.{' '}
        {Object.keys(plan.unplaced).length > 0 && (
          <span className="error">Still waiting: {Object.values(plan.unplaced).reduce((a, b) => a + b, 0).toLocaleString()}</span>
        )}
      </p>
      <p className="hint">
        {plan.method} Limits: {plan.limits.supply_per_wave.toLocaleString()} people per wave, {' '}
        {plan.limits.zone_intake_per_wave.toLocaleString()} per zone per wave, {' '}
        {plan.limits.zone_capacity.toLocaleString()} per zone total. A zone opens after the late end of its safe-date range.
      </p>
      <h4>People moved per wave (bar = supply limit)</h4>
      {waves.map(([w, n]) => (
        <div key={w} className="wave-row">
          <span>Wave {w}</span>
          <div className="cbar"><div style={{ width: `${(n / maxW) * 100}%`, background: waveColor(Number(w)) }} /></div>
          <span>{n.toLocaleString()}</span>
        </div>
      ))}
      <h4>Zones open in wave</h4>
      <p>
        {Object.entries(plan.zone_open_wave).map(([z, w]) => (
          <span key={z} className="badge" style={{ background: waveColor(w), marginRight: 4 }}>
            {z}: {w ?? 'not yet'}
          </span>
        ))}
      </p>
      <h4>Schedule</h4>
      <table>
        <thead><tr><th>Wave</th><th>Date</th><th>From level</th><th>To zone</th><th>People</th></tr></thead>
        <tbody>
          {plan.rows.map((r, i) => (
            <tr key={i}>
              <td><span className="badge" style={{ background: waveColor(r.wave) }}>{r.wave}</span></td>
              <td>{r.date}</td>
              <td>{r.level}{r.level === 8 ? ' (deepest)' : ''}</td>
              <td>{r.destination}</td>
              <td>{r.population.toLocaleString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
