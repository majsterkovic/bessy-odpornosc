import { useMemo } from 'react'
import { Chart } from '../charts/Chart'
import { buildTwinsOption } from '../charts/twinsChart'
import { Collapsible } from '../components/Collapsible'
import { Md } from '../components/Md'
import { fmtNum, fmtPct } from '../format'
import type { Market, Series, Twins } from '../types'

const COUNT_WORDS: Record<number, string> = { 2: 'Dwie', 3: 'Trzy', 4: 'Cztery' }

export function leadTwins(n: number): string {
  const tail = 'najbliższe dzisiejszemu układowi czynników: ropa, technologie i rok wyborów połówkowych.'
  if (n === 1) return `Najbliższa bessa ${tail.replace('najbliższe', 'najbliższa')}`
  const word = COUNT_WORDS[n]
  return word ? `${word} bessy ${tail}` : `${n} bess ${tail}`
}

export function StepTwins({ twins, market, series }: { twins: Twins; market: Market; series: Series }) {
  const opt = useMemo(() => buildTwinsOption(series.twins, series.today), [series])
  return (
    <>
      <Md text={twins.text} />
      <Chart option={opt} height={340} label="Ścieżki S&P 500 od szczytu: bliźniacze bessy i dziś" />
      <h3>Czynniki: dziś i w bliźniakach</h3>
      <table className="data" aria-label="Czynniki makro">
        <thead><tr><th>Okres</th><th>Ropa: największa zmiana 12 mies.</th><th>Nasdaq/S&P 24 mies.</th><th>Wybory połówkowe</th><th>Czynniki</th><th>Odległość od dziś</th></tr></thead>
        <tbody>
          {market.factors.map((f) => (
            <tr key={f.okres}><td>{f.okres}</td><td>{fmtPct(f.ropa, 0, true)}</td><td>{fmtPct(f.tech, 0, true)}</td><td>{f.wybory}</td><td>{fmtNum(f.czynniki, 0)}</td><td>{fmtNum(f.odleglosc, 2)}</td></tr>
          ))}
        </tbody>
      </table>
      <h3>Sezonowość wyborów połówkowych</h3>
      <Md text={twins.after_election_text} />
      <table className="data" aria-label="Sezonowość midterms">
        <thead><tr><th>Miesiąc</th><th>Średnia (rok wyborów)</th><th>Mediana (rok wyborów)</th><th>Średnia (pozostałe lata)</th><th>Mediana (pozostałe lata)</th></tr></thead>
        <tbody>
          {twins.seasonality_monthly.map((r) => (
            <tr key={r.miesiac}><td>{r.miesiac}</td><td>{fmtPct(r.mean_wybory, 1, true)}</td><td>{fmtPct(r.median_wybory, 1, true)}</td><td>{fmtPct(r.mean_inne, 1, true)}</td><td>{fmtPct(r.median_inne, 1, true)}</td></tr>
          ))}
        </tbody>
      </table>
      <Collapsible title="Zwrot S&P 500 po dniu wyborów połówkowych">
        <table className="data" aria-label="Po wyborach">
          <thead><tr><th>Rok</th><th>Dzień wyborów</th><th>3 mies.</th><th>6 mies.</th><th>12 mies.</th></tr></thead>
          <tbody>{twins.after_election.map((r) => <tr key={r.year}><td>{r.year}</td><td>{r.election_date ?? '–'}</td><td>{fmtPct(r.r3m, 1, true)}</td><td>{fmtPct(r.r6m, 1, true)}</td><td>{fmtPct(r.r12m, 1, true)}</td></tr>)}</tbody>
        </table>
      </Collapsible>
    </>
  )
}
