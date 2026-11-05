import { useMemo } from 'react'
import { Chart } from '../charts/Chart'
import { buildSectorBarsOption, peAssessmentLabel } from '../charts/sectorChart'
import { Collapsible } from '../components/Collapsible'
import { Md } from '../components/Md'
import { fmtNum, fmtPct } from '../format'
import type { Sectors } from '../types'

export function StepSectors({ sectors }: { sectors: Sectors }) {
  const opt = useMemo(() => buildSectorBarsOption(sectors.behavior_a, sectors.behavior_b), [sectors])
  return (
    <>
      <h3>Jak sektory zachowywały się w bessach (mediana alfy wobec S&P 500)</h3>
      <Chart option={opt} height={420} label="Słupki: mediana alfy sektorów w bessach" />
      <h3>Wycena sektorów (P/E)</h3>
      <table className="data" aria-label="P/E sektorów">
        <thead><tr><th>Sektor</th><th>P/E dziś</th><th>Mediana 10 lat</th><th>Percentyl 10 lat</th><th>Kompresja w bessach</th><th>Pokrycie</th><th>Ocena</th></tr></thead>
        <tbody>
          {sectors.pe.map((r) => {
            const a = peAssessmentLabel(r)
            return (
              <tr key={r.sector} className={a.lowCoverage ? 'low' : undefined}>
                <td>{r.sector}</td><td>{fmtNum(r.pe_teraz, 1)}</td><td>{fmtNum(r.med_10l, 1)}</td><td>{fmtNum(r.perc_10l, 0)}</td>
                <td>{fmtPct(r.kompresja, 1, true)}</td><td>{fmtPct(r.pokrycie, 0)}</td><td>{a.text}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
      <Collapsible><Md text={sectors.pe_text} /></Collapsible>
    </>
  )
}
