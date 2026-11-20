import type { ForecastSummary } from '../api'
import ForecastChart from './ForecastChart'

interface Props {
  data: ForecastSummary | null
  zoneId: string | null
}

export default function ForecastPanel({ data, zoneId }: Props) {
  if (!data) return <p className="hint">Loading forecast...</p>
  const z = data.zones.find((q) => q.zone_id === (zoneId ?? data.first_safe_zone)) ?? data.zones[0]
  return (
    <div>
      <h3>Recovery forecast</h3>
      {data.first_safe_zone && (
        <p className="callout">First zone safe: <b>{data.first_safe_zone}</b></p>
      )}
      <table>
        <thead><tr><th>Zone</th><th>Safe date</th><th>Range (days)</th><th>Data</th></tr></thead>
        <tbody>
          {data.zones.map((q) => (
            <tr key={q.zone_id} className={q.zone_id === z?.zone_id ? 'sel' : ''}>
              <td>{q.zone_id}</td>
              <td>{q.ok ? (q.safe_date ?? 'not within 1 yr') : 'n/a'}</td>
              <td>{q.safe_day_lo != null ? `${q.safe_day_lo}–${q.safe_day_hi}` : '—'}</td>
              <td>{q.days_used} days</td>
            </tr>
          ))}
        </tbody>
      </table>
      {z && (
        <>
          <h4>{z.name} ({z.zone_id})</h4>
          <p className={z.ok ? '' : 'error'}>{z.message}</p>
          {z.pm25 && <ForecastChart series={z.pm25} label="PM2.5 µg/m³" lastDay={z.last_day} />}
          {z.radiation && <ForecastChart series={z.radiation} label="Radiation µSv/h" lastDay={z.last_day} />}
        </>
      )}
      <p className="hint">Click a zone on the map to see its curves. {data.note}</p>
    </div>
  )
}
