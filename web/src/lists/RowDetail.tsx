import { fmtPp } from '../format'
import type { ListRow } from '../types'
import { flagsOf } from './listLogic'

export function RowDetail({ row, onClose }: { row: ListRow; onClose: () => void }) {
  const flags = flagsOf(row)
  const max = Math.max(0.01, ...row.per_episode.map((e) => Math.abs(e.alpha)))
  return (
    <section role="region" aria-label={`Szczegóły ${row.ticker}`} className="detail">
      <header><h3>{row.ticker} · {row.name}</h3><button onClick={onClose} aria-label="Zamknij szczegóły">×</button></header>
      <p>{row.why}.</p>
      {flags.length > 0 && <p className="flags">Do sprawdzenia: {flags.join('; ')}.</p>}
      <p className="muted">Waluta notowania: {row.currency ?? '–'} · giełda: {row.exchange ?? '–'}. Wyniki w USD; dostępność w XTB sprawdź przed zakupem.</p>
      <table className="data" aria-label="Alfa w poszczególnych okresach">
        <thead><tr><th>Okres (szczyt)</th><th>Alfa wobec S&P 500</th><th /></tr></thead>
        <tbody>
          {row.per_episode.length === 0 && <tr><td colSpan={3}>–</td></tr>}
          {row.per_episode.map((e) => (
            <tr key={e.episode_id}>
              <td>{e.episode_id}</td><td>{fmtPp(e.alpha)}</td>
              <td><span className={`bar ${e.alpha >= 0 ? 'pos' : 'neg'}`} style={{ width: `${Math.abs(e.alpha) / max * 100}%` }} /></td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  )
}
