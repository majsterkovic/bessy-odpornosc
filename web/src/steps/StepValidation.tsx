import { useMemo } from 'react'
import { Chart } from '../charts/Chart'
import { buildQuintileOption } from '../charts/funnelChart'
import { Collapsible } from '../components/Collapsible'
import { Md } from '../components/Md'
import { fmtNum, fmtPct, fmtPp } from '../format'
import type { Validation } from '../types'

export function leadValidation(v: Validation, topN = 15): string {
  const q = v.oos.kwintyle
  const worst = q[0], best = q[q.length - 1]
  return `Ranking zbudowany na dawnych okresach przewidywał późniejsze wyniki: korelacja rang ${fmtNum(v.oos.spearman, 2)}, `
    + `najlepszy kwintyl miał medianę alfy ${fmtPp(best?.test_med_alpha)}, a najgorszy ${fmtPp(worst?.test_med_alpha)}. `
    + `Po zmianie zbioru bliźniaków ${v.sensitivity.overlap15} z ${topN} spółek zostaje na liście.`
}

export function StepValidation({ validation }: { validation: Validation }) {
  const opt = useMemo(() => buildQuintileOption(validation.oos), [validation])
  const { oos, sensitivity } = validation
  return (
    <>
      <Chart option={opt} height={280} label="Mediana alfy w okresach testowych według kwintyli wyniku" />
      <p>Najlepszy decyl pokonywał S&P 500 w {fmtPct(oos.top_decile_win, 0)} okresów testowych, wszystkie spółki w {fmtPct(oos.all_win, 0)}. Próba: {fmtNum(oos.n, 0)} spółek.</p>
      <p>Stały trzon (spółki, które zostają po zmianie zbioru bliźniaków): {sensitivity.both.join(', ') || '–'}. Pozostałe pozycje zależą od doboru okresów, więc traktuj je jako mniej pewne.</p>
      <Collapsible><Md text={validation.text} /></Collapsible>
    </>
  )
}
