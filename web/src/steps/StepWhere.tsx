import { useMemo } from 'react'
import { Chart } from '../charts/Chart'
import { buildRelativeOption } from '../charts/spChart'
import { Collapsible } from '../components/Collapsible'
import { fmtNum, fmtPct } from '../format'
import type { IndexRow, Market, Series } from '../types'

const PRIMARY = ['GSPC.INDX', 'NDX.INDX', 'SOX.INDX', 'WIG20.INDX', 'BCOMCO.INDX']
const find = (m: Market, t: string) => m.indices.find((i) => i.ticker === t)

/** Wprowadzenie do kroku 1: liczby z danych, nie z ręki. */
export function leadWhere(m: Market): string {
  const sp = find(m, 'GSPC.INDX'), sox = find(m, 'SOX.INDX'), oil = find(m, 'BCOMCO.INDX')
  const oilMove = oil?.r_12m == null ? 'zmieniła się o –' : oil.r_12m >= 0 ? `zdrożała o ${fmtPct(oil.r_12m, 0)}` : `potaniała o ${fmtPct(-oil.r_12m, 0)}`
  const inBear = sp?.od_ath != null && sp.od_ath <= -0.2
  return `S&P 500 jest ${fmtPct(sp ? -(sp.od_ath ?? NaN) : null)} poniżej szczytu, półprzewodniki (SOX) ${fmtPct(sox ? -(sox.od_ath ?? NaN) : null)}, `
    + `a ropa (Brent) ${oilMove} w 12 miesięcy. `
    + (inBear ? 'S&P 500 jest już w bessie (spadek co najmniej 20%), więc ta strona opisuje, jak zachowywały się spółki w podobnych okresach.' : 'To przygotowanie na możliwą bessę, nie reakcja na trwającą.')
}

function Card({ r }: { r: IndexRow }) {
  return (
    <div className="card">
      <div className="card-name">{r.indeks}</div>
      <div className="card-value">{fmtPct(r.od_ath, 1)}</div>
      <div className="card-sub">od szczytu ({r.data_ath ?? '–'}) · 3 mies. {fmtPct(r.r_3m, 1, true)} · 12 mies. {fmtPct(r.r_12m, 1, true)} · poziom {fmtNum(r.poziom, 1)}</div>
    </div>
  )
}

export function StepWhere({ market, series }: { market: Market; series: Series }) {
  const primary = PRIMARY.map((t) => find(market, t)).filter((x): x is IndexRow => !!x)
  const rest = market.indices.filter((i) => !PRIMARY.includes(i.ticker))
  const opt = useMemo(() => buildRelativeOption(series.sox, series.sp500), [series])
  return (
    <>
      <p>{market.summary}</p>
      <div className="cards" data-testid="cards-primary">{primary.map((r) => <Card key={r.ticker} r={r} />)}</div>
      <div className="cards small" data-testid="cards-secondary">{rest.map((r) => <Card key={r.ticker} r={r} />)}</div>
      <h3>Półprzewodniki względem S&P 500</h3>
      <Chart option={opt} height={240} label="Wykres: SOX względem S&P 500" />
      <Collapsible title="Jak to policzono">
        <p>{market.state_text}</p>
      </Collapsible>
    </>
  )
}
