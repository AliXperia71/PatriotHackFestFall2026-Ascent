import type { Health, VerifyResult } from '../api'

interface Props {
  result: VerifyResult | null
  health: Health | null
  busy: boolean
  onTamper: () => void
  onReset: () => void
  onVerify: () => void
}

export default function ChainStatus({ result, health, busy, onTamper, onReset, onVerify }: Props) {
  const ok = result?.ok
  return (
    <div className={`banner ${result == null ? '' : ok ? 'ok' : 'bad'}`}>
      <div className="banner-text">
        {result == null && 'Checking the log...'}
        {result && ok && (
          <>All {result.total} readings verified. Signatures valid, hash chain intact.</>
        )}
        {result && !ok && (
          <>
            CHAIN BROKEN at entry #{result.first_bad_index} ({result.reason}).{' '}
            {result.untrusted_count} later entries are untrusted.
          </>
        )}
      </div>
      <div className="banner-buttons">
        <button onClick={onVerify} disabled={busy}>Verify all</button>
        {health?.demo_mode && (
          <>
            <button onClick={onTamper} disabled={busy} className="danger">Tamper</button>
            <button onClick={onReset} disabled={busy}>Reset</button>
          </>
        )}
      </div>
    </div>
  )
}
