import type { GroupResult, ZoneOptions } from '../api'
import ContribBar, { Legend } from './ContribBar'

interface Props {
  options: ZoneOptions[] | null
  group: GroupResult | null
  zoneId: string | null
}

export default function PilotPanel({ options, group, zoneId }: Props) {
  if (!options || !group) return <p className="hint">Loading pilot...</p>
  const zo = options.find((o) => o.zone_id === zoneId) ?? options[0]
  return (
    <div>
      <h3>Which option works? ({zo?.zone_id})</h3>
      <Legend keys={Object.keys(zo?.weights ?? {})} />
      <p className="hint">
        Weights: {Object.entries(zo?.weights ?? {}).map(([k, v]) => `${k} ${v}`).join(' · ')}
      </p>
      {zo && zo.options.length === 0 && <p className="error">{zo.note}</p>}
      <table>
        <tbody>
          {zo?.options.map((o) => (
            <tr key={o.option} className={o.option === zo.recommended ? 'sel' : ''}>
              <td style={{ width: 80 }}>
                <b>{o.option}</b>
                {o.option === zo.recommended && <div className="badge" style={{ background: '#2e9d57' }}>best</div>}
                {!o.viable && <div className="badge" style={{ background: '#d63a3a' }}>not safe</div>}
              </td>
              <td><ContribBar contributions={o.contributions} /></td>
              <td style={{ width: 44 }}>{o.total.toFixed(2)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="hint">Click another zone on the map to compare. {zo?.note}</p>

      <h3>Who goes first?</h3>
      <p>
        {group.pool_size} people → {group.eligible} eligible → top {group.band_size} band → {group.selected.length} picked.
      </p>
      <p className="hint">
        Excluded: {Object.entries(group.excluded).map(([k, v]) => `${k.replace(/_/g, ' ')} ${v}`).join(' · ')}
        <br />{group.method} Seed {group.seed}.
      </p>
      <Legend keys={Object.keys(group.weights)} />
      <table>
        <thead><tr><th>ID</th><th>Age</th><th>Skill</th><th>Level</th><th>Why chosen</th><th>Score</th></tr></thead>
        <tbody>
          {group.selected.map((c) => (
            <tr key={c.person.person_id}>
              <td>{c.person.person_id}</td>
              <td>{c.person.age}</td>
              <td>{c.person.skill}</td>
              <td>{c.person.level}</td>
              <td style={{ minWidth: 140 }}><ContribBar contributions={c.contributions} /></td>
              <td>{c.score.toFixed(2)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
