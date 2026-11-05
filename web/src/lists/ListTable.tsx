import { useState } from 'react'
import { fmtNum, fmtPct, fmtPp } from '../format'
import type { ListRow } from '../types'
import { DEFAULT_SORT, flagsOf, sortRows, type Dir, type SortKey } from './listLogic'

export function ListTable({ rows, etf, trend = false, selected, onSelect }: { rows: ListRow[]; etf: boolean; trend?: boolean; selected: string | null; onSelect: (t: string | null) => void }) {
  const [sort, setSort] = useState<{ key: SortKey; dir: Dir }>(DEFAULT_SORT)
  const sorted = sortRows(rows, sort.key, sort.dir)
  const head = (key: SortKey, label: string) => (
    <th scope="col" aria-sort={sort.key === key ? (sort.dir === 'asc' ? 'ascending' : 'descending') : 'none'}>
      <button onClick={() => setSort((s) => ({ key, dir: s.key === key && s.dir === 'desc' ? 'asc' : 'desc' }))}>{label}</button>
    </th>
  )
  return (
    <table className="data lists">
      <thead>
        <tr>
          {head('rank', '#')}{head('ticker', 'Ticker')}<th scope="col">Nazwa</th>
          {etf ? <><th scope="col">Klasa</th><th scope="col">Kor. z S&P</th></> : <><th scope="col">Sektor</th><th scope="col">Giełda</th></>}
          {head('n_valid', 'Okresy')}{head('n_bessy', 'W tym bessy')}{head('med_alpha', 'Alfa (med.)')}{head('downside_beta', 'Downside β')}{head('med_max_dd', 'Max DD (med.)')}{head('win_rate', 'Wygrane')}
          {trend && <><th scope="col">Alfa od szczytu SOX</th><th scope="col">Alfa 63 sesje</th></>}
          {etf ? <th scope="col">Odpowiedniki UCITS</th> : <><th scope="col">P/E</th><th scope="col">P/E perc.</th></>}
          <th scope="col">Do sprawdzenia</th>
        </tr>
      </thead>
      <tbody>
        {sorted.map((r) => (
          <tr key={r.instrument_id} className={selected === r.ticker ? 'selected' : undefined}>
            <td>{r.rank}</td>
            <td><button className="link" aria-label={r.ticker} onClick={() => onSelect(selected === r.ticker ? null : r.ticker)}>{r.ticker}</button></td>
            <td>{r.name}</td>
            {etf ? <><td>{r.klass ?? '–'}</td><td>{fmtNum(r.corr_spx, 2)}</td></> : <><td>{r.sector ?? '–'}</td><td>{r.exchange ?? '–'}</td></>}
            <td>{r.n_valid == null ? '–' : r.n_valid}</td><td>{r.n_bessy == null ? '–' : r.n_bessy}</td><td>{fmtPp(r.med_alpha)}</td><td>{fmtNum(r.downside_beta, 2)}</td><td>{fmtPct(r.med_max_dd, 1)}</td><td>{fmtPct(r.win_rate, 0)}</td>
            {trend && <><td>{fmtPp(r.alpha_sox)}</td><td>{fmtPp(r.alpha_63d)}</td></>}
            {etf ? <td>{r.ucits ?? "–"}</td> : <><td>{fmtNum(r.pe, 1)}</td><td>{fmtNum(r.pe_pct, 0)}</td></>}
            <td>{flagsOf(r).join('; ') || '–'}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
