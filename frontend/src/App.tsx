import { useCallback, useEffect, useState } from 'react'
import {
  api, api2, STATUS_COLOR, STATUS_LABEL,
  type ForecastSummary, type GroupResult, type Health, type MigratePlan,
  type ReadingOut, type VerifyResult, type Zone, type ZoneOptions,
} from './api'
import ChainStatus from './components/ChainStatus'
import ForecastPanel from './components/ForecastPanel'
import MigratePanel, { waveColor } from './components/MigratePanel'
import PilotPanel from './components/PilotPanel'
import ReadingsPanel from './components/ReadingsPanel'
import ZoneMap from './components/ZoneMap'
import './App.css'

type Tab = 'prove' | 'forecast' | 'pilot' | 'migrate'
const TABS: { id: Tab; label: string }[] = [
  { id: 'prove', label: '1. Prove' },
  { id: 'forecast', label: '2. Forecast' },
  { id: 'pilot', label: '3. Pilot' },
  { id: 'migrate', label: '4. Migrate' },
]

export default function App() {
  const [tab, setTab] = useState<Tab>('prove')
  const [zones, setZones] = useState<Zone[]>([])
  const [selected, setSelected] = useState<string | null>(null)
  const [readings, setReadings] = useState<ReadingOut[]>([])
  const [result, setResult] = useState<VerifyResult | null>(null)
  const [health, setHealth] = useState<Health | null>(null)
  const [fc, setFc] = useState<ForecastSummary | null>(null)
  const [opts, setOpts] = useState<ZoneOptions[] | null>(null)
  const [group, setGroup] = useState<GroupResult | null>(null)
  const [plan, setPlan] = useState<MigratePlan | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    try {
      const [z, v, h, f, o, g, p] = await Promise.all([
        api.zones(), api.verify(), api.health(),
        api2.forecast(), api2.pilotOptions(), api2.pilotGroup(), api2.migratePlan(),
      ])
      setZones(z); setResult(v); setHealth(h)
      setFc(f); setOpts(o); setGroup(g); setPlan(p)
      if (selected) setReadings(await api.readings(selected))
      setError(null)
    } catch (e) {
      setError(`Cannot load data from the backend (port 8000). ${String(e)}`)
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

  const fcBy = new Map(fc?.zones.map((z) => [z.zone_id, z]) ?? [])
  const optBy = new Map(opts?.map((o) => [o.zone_id, o]) ?? [])

  function colorFor(z: Zone): string {
    if (tab === 'forecast') {
      const f = fcBy.get(z.zone_id)
      if (!f?.ok || f.safe_day == null) return '#8a8f98'
      return f.safe_day <= f.last_day ? '#2e9d57' : '#e0a32e'
    }
    if (tab === 'migrate') return waveColor(plan?.zone_open_wave[z.zone_id])
    if (tab === 'pilot') return optBy.get(z.zone_id)?.recommended ? '#2b7bb9' : '#8a8f98'
    return STATUS_COLOR[z.status]
  }

  function labelFor(z: Zone): string {
    if (tab === 'forecast') {
      const f = fcBy.get(z.zone_id)
      return f?.safe_date ?? (f?.ok ? 'not within 1 yr' : 'no data')
    }
    if (tab === 'migrate') {
      const w = plan?.zone_open_wave[z.zone_id]
      return w == null ? 'not open' : `wave ${w}`
    }
    if (tab === 'pilot') return optBy.get(z.zone_id)?.recommended ?? 'none'
    return STATUS_LABEL[z.status]
  }

  return (
    <div className="app">
      <header>
        <h1>Ascent</h1>
        <span>Trust math, not the Directorate.</span>
        <nav>
          {TABS.map((t) => (
            <button key={t.id} className={tab === t.id ? 'tab active' : 'tab'} onClick={() => setTab(t.id)}>
              {t.label}
            </button>
          ))}
        </nav>
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
        <ZoneMap zones={zones} selected={selected} onSelect={setSelected} colorFor={colorFor} labelFor={labelFor} />
        <aside>
          {tab === 'prove' && <ReadingsPanel zoneId={selected} readings={readings} />}
          {tab === 'forecast' && <ForecastPanel data={fc} zoneId={selected} />}
          {tab === 'pilot' && <PilotPanel options={opts} group={group} zoneId={selected} />}
          {tab === 'migrate' && <MigratePanel plan={plan} />}
        </aside>
      </main>
      <footer>Safety thresholds and weights are illustrative, not medical advice. All data is synthetic.</footer>
    </div>
  )
}
