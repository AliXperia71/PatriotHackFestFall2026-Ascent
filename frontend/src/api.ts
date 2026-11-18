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
