// Types mirror backend/app/models.py. Keep them in sync.

export type EntryStatus = 'verified' | 'tampered' | 'untrusted_after_break'

export interface Reading {
  probe_id: string
  zone_id: string
  ts: string
  pm25_ugm3: number
  o2_pct: number
  co_ppm: number
  radiation_usv_h: number
  temp_c: number
  machine_contacts: number
}

export interface ReadingOut {
  index: number
  reading: Reading
  signature: string
  prev_hash: string
  entry_hash: string
  status: EntryStatus
}

export interface Zone {
  zone_id: string
  name: string
  lat: number
  lon: number
  status: EntryStatus
  latest: ReadingOut | null
}

export interface VerifyResult {
  ok: boolean
  total: number
  checked: number
  first_bad_index: number | null
  reason: string | null
  untrusted_count: number
}

export interface EntryCheck {
  index: number
  signature_valid: boolean
  prev_link_valid: boolean
  entry_hash_valid: boolean
  status: EntryStatus
  chain_intact: boolean
  first_bad_index: number | null
  message: string
}

export interface Health {
  ok: boolean
  demo_mode: boolean
  entries: number
}

async function request<T>(path: string, method = 'GET'): Promise<T> {
  const res = await fetch(`/api${path}`, { method })
  if (!res.ok) {
    const body = await res.text()
    throw new Error(`${method} ${path} failed (${res.status}): ${body}`)
  }
  return (await res.json()) as T
}

export const api = {
  health: () => request<Health>('/health'),
  zones: () => request<Zone[]>('/zones'),
  readings: (zoneId: string, limit = 20) =>
    request<ReadingOut[]>(`/readings?zone_id=${encodeURIComponent(zoneId)}&limit=${limit}`),
  verify: () => request<VerifyResult>('/verify'),
  verifyOne: (index: number) => request<EntryCheck>(`/verify/${index}`),
  tamper: () => request<{ index: number }>('/demo/tamper', 'POST'),
  reset: () => request<{ ok: boolean }>('/demo/reset', 'POST'),
}

export const STATUS_COLOR: Record<EntryStatus, string> = {
  verified: '#2e9d57',
  tampered: '#d63a3a',
  untrusted_after_break: '#8a8f98',
}

export const STATUS_LABEL: Record<EntryStatus, string> = {
  verified: 'Verified',
  tampered: 'Tampered',
  untrusted_after_break: 'Untrusted',
}

// ---------------- Forecast ----------------
export interface BandPoint { day: number; mid: number; lo: number; hi: number }

export interface SeriesForecast {
  metric: 'pm25_ugm3' | 'radiation_usv_h'
  threshold: number
  observed: [number, number][]
  projected: BandPoint[]
  fit: Record<string, number>
  current: number
  cross_day: number | null
  cross_lo: number | null
  cross_hi: number | null
}

export interface ZoneForecast {
  zone_id: string
  name: string
  ok: boolean
  message: string
  days_used: number
  last_day: number
  pm25: SeriesForecast | null
  radiation: SeriesForecast | null
  safe_day: number | null
  safe_day_lo: number | null
  safe_day_hi: number | null
  safe_date: string | null
}

export interface ForecastSummary {
  zones: ZoneForecast[]
  first_safe_zone: string | null
  ranking: string[]
  note: string
}

// ---------------- Pilot ----------------
export interface OptionScore {
  option: string
  total: number
  viable: boolean
  contributions: Record<string, number>
  normalized: Record<string, number>
  raw: Record<string, number>
}

export interface ZoneOptions {
  zone_id: string
  recommended: string | null
  options: OptionScore[]
  weights: Record<string, number>
  note: string
}

export interface Candidate {
  person_id: string
  age: number
  health: number
  skill: string
  level: number
  years_below: number
  volunteer: boolean
}

export interface ChosenPerson { person: Candidate; score: number; contributions: Record<string, number> }

export interface GroupResult {
  selected: ChosenPerson[]
  pool_size: number
  eligible: number
  excluded: Record<string, number>
  band_size: number
  band_cutoff: number
  weights: Record<string, number>
  seed: number
  method: string
}

// ---------------- Migrate ----------------
export interface WaveRow { wave: number; day: number; date: string; level: number; destination: string; population: number }

export interface MigratePlan {
  rows: WaveRow[]
  zone_open_wave: Record<string, number | null>
  placed: number
  unplaced: Record<string, number>
  total_population: number
  wave_totals: Record<string, number>
  limits: Record<string, number>
  method: string
}

export const api2 = {
  forecast: () => request<ForecastSummary>('/forecast'),
  pilotOptions: () => request<ZoneOptions[]>('/pilot/options'),
  pilotGroup: () => request<GroupResult>('/pilot/group'),
  migratePlan: () => request<MigratePlan>('/migrate/plan'),
}

// One color per scoring criterion, shared by all bar charts.
export const CRITERION_COLOR: Record<string, string> = {
  safety: '#2b7bb9',
  cost: '#e0a32e',
  capacity: '#7a5cc2',
  time: '#3aa38f',
  health: '#2b7bb9',
  skill: '#e0a32e',
  depth: '#c2553a',
  years_below: '#7a5cc2',
}
