import { useMemo, useState } from 'react'
import { Chart } from '../charts/Chart'
import { buildSpOption } from '../charts/spChart'
import { Collapsible } from '../components/Collapsible'
import { fmtDate, fmtInt, fmtPct } from '../format'
import type { Episodes, Series } from '../types'

type Key = 'peak_date' | 'depth' | 'days_to_trough'

export function StepEpisodes({ episodes, series }: { episodes: Episodes; series: Series }) {
  const [log, setLog] = useState(true)
  const [sort, setSort] = useState<{ key: Key; dir: 1 | -1 }>({ key: 'peak_date', dir: -1 })
  const opt = useMemo(() => buildSpOption(series.sp500, episodes.rows, { logScale: log }), [series, episodes, log])
  const rows = useMemo(() => [...episodes.rows].sort((a, b) => {
    const x = a[sort.key], y = b[sort.key]
    if (x == null) return 1
    if (y == null) return -1
    return (x < y ? -1 : x > y ? 1 : 0) * sort.dir
  }), [episodes, sort])
  const head = (key: Key, label: string) => (
    <th scope="col" aria-sort={sort.key === key ? (sort.dir === 1 ? 'ascending' : 'descending') : 'none'}>
      <button onClick={() => setSort((s) => ({ key, dir: s.key === key ? (s.dir === 1 ? -1 : 1) : 1 }))}>{label}</button>
    </th>
  )
  return (
    <>
      <label className="toggle"><input type="checkbox" checked={log} onChange={(e) => setLog(e.target.checked)} /> skala logarytmiczna</label>
      <Chart option={opt} height={380} label="Wykres S&P 500 z zaznaczonymi bessami i korektami" />
      <p className="legend"><span className="sw bear" /> bessa (≥20%) <span className="sw corr" /> korekta (15–20%)</p>
      <table className="data">
        <thead><tr>{head('peak_date', 'Szczyt')}<th scope="col">Dołek</th><th scope="col">Rodzaj</th>{head('depth', 'Głębokość')}{head('days_to_trough', 'Dni do dołka')}<th scope="col">Dni do odbudowy</th><th scope="col">Czynniki</th><th scope="col">W rankingu A</th><th scope="col">Bliźniak</th></tr></thead>
        <tbody>
          {rows.map((e) => (
            <tr key={e.episode_id} className={e.kind}>
              <td>{e.episode_id}</td><td>{fmtDate(e.trough_date)}</td><td>{e.kind}</td><td>{fmtPct(e.depth, 1)}</td>
              <td>{fmtInt(e.days_to_trough)}</td><td>{fmtInt(e.days_to_recovery)}</td><td>{fmtInt(e.n_factors)}</td><td>{e.in_ranking_a ? 'tak' : '–'}</td><td>{e.twin ? 'tak' : '–'}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <Collapsible><p>{episodes.brief_text}</p></Collapsible>
    </>
  )
}
