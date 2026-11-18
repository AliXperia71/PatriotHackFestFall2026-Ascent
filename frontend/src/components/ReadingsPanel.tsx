import { useState } from 'react'
import { api, STATUS_COLOR, STATUS_LABEL, type EntryCheck, type ReadingOut } from '../api'

interface Props {
  zoneId: string | null
  readings: ReadingOut[]
}

export default function ReadingsPanel({ zoneId, readings }: Props) {
  const [checks, setChecks] = useState<Record<number, EntryCheck>>({})
  const [error, setError] = useState<string | null>(null)

  if (!zoneId) return <p className="hint">Click a zone on the map.</p>

  async function verify(index: number) {
    try {
      const c = await api.verifyOne(index)
      setChecks((prev) => ({ ...prev, [index]: c }))
      setError(null)
    } catch (e) {
      setError(String(e))
    }
  }

  return (
    <div>
      <h3>Latest readings: {zoneId}</h3>
      {error && <p className="error">{error}</p>}
      <table>
        <thead>
          <tr>
            <th>#</th>
            <th>Time</th>
            <th>PM2.5</th>
            <th>Rad</th>
            <th>Badge</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {readings.map((r) => {
            const c = checks[r.index]
            return (
              <tr key={r.index}>
                <td>{r.index}</td>
                <td>{r.reading.ts.replace('T', ' ').replace('Z', '')}</td>
                <td>{r.reading.pm25_ugm3}</td>
                <td>{r.reading.radiation_usv_h}</td>
                <td>
                  <span className="badge" style={{ background: STATUS_COLOR[r.status] }}>
                    {STATUS_LABEL[r.status]}
                  </span>
                </td>
                <td>
                  <button onClick={() => verify(r.index)}>Verify</button>
                  {c && (
                    <div className="check" title={c.message}>
                      sig {c.signature_valid ? 'OK' : 'BAD'} · link {c.prev_link_valid ? 'OK' : 'BAD'} ·
                      hash {c.entry_hash_valid ? 'OK' : 'BAD'}
                      <br />
                      {c.message}
                    </div>
                  )}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
