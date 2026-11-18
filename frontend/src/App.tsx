import { useCallback, useEffect, useState } from 'react'
import { api, type Health, type ReadingOut, type VerifyResult, type Zone } from './api'
import ChainStatus from './components/ChainStatus'
import ReadingsPanel from './components/ReadingsPanel'
import ZoneMap from './components/ZoneMap'
import './App.css'

export default function App() {
  const [zones, setZones] = useState<Zone[]>([])
  const [selected, setSelected] = useState<string | null>(null)
  const [readings, setReadings] = useState<ReadingOut[]>([])
  const [result, setResult] = useState<VerifyResult | null>(null)
  const [health, setHealth] = useState<Health | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    try {
      const [z, v, h] = await Promise.all([api.zones(), api.verify(), api.health()])
      setZones(z)
      setResult(v)
      setHealth(h)
      if (selected) setReadings(await api.readings(selected))
      setError(null)
    } catch (e) {
      setError(`Cannot reach the backend. Is it running on port 8000? (${String(e)})`)
    }
  }, [selected])

  useEffect(() => {
    void refresh()
  }, [refresh])

  async function run(action: () => Promise<unknown>) {
    setBusy(true)
    try {
      await action()
      await refresh()
    } catch (e) {
      setError(String(e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="app">
      <header>
        <h1>Ascent</h1>
        <span>Prove: trust math, not the Directorate.</span>
      </header>
      <ChainStatus
        result={result}
        health={health}
        busy={busy}
        onVerify={() => void run(async () => {})}
        onTamper={() => void run(api.tamper)}
        onReset={() => void run(api.reset)}
      />
      {error && <p className="error">{error}</p>}
      <main>
        <ZoneMap zones={zones} selected={selected} onSelect={setSelected} />
        <aside>
          <ReadingsPanel zoneId={selected} readings={readings} />
        </aside>
      </main>
      <footer>Safety thresholds are illustrative, not medical advice. All data is synthetic.</footer>
    </div>
  )
}
