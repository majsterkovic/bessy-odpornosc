import { useMemo } from 'react'
import { Chart } from '../charts/Chart'
import { buildFunnelOption } from '../charts/funnelChart'
import { fmtInt } from '../format'
import type { Funnel, PeReason } from '../types'

export function leadFunnel(f: Funnel): string {
  const first = f.steps.find((s) => s.key === 'kandydaci') ?? f.steps[0]
  const last = f.steps[f.steps.length - 1]
  return `Z ${fmtInt(first.n)} kupowalnych spółek zostawiamy ${fmtInt(last.n)}. Każdy etap odrzuca spółki, które nie dają dowodów odporności albo są zbyt drogie względem własnej historii.`
}

function ReasonTable({ name, rows }: { name: string; rows: PeReason[] }) {
  return (
    <table className="data" aria-label={name}>
      <caption>{name}</caption>
      <thead><tr><th>Powód</th><th>Liczba</th></tr></thead>
      <tbody>{rows.map((r, i) => <tr key={i}><td>{r.reason ?? '–'}</td><td>{fmtInt(r.n)}</td></tr>)}</tbody>
    </table>
  )
}

export function StepFunnel({ funnel }: { funnel: Funnel }) {
  const opt = useMemo(() => buildFunnelOption(funnel.steps), [funnel])
  return (
    <>
      <Chart option={opt} height={320} label="Lejek selekcji spółek" />
      <ul className="funnel-notes">
        {funnel.steps.map((s) => <li key={s.key}><strong>{s.label}:</strong> {fmtInt(s.n)}{s.note ? ` – ${s.note}` : ''}</li>)}
      </ul>
      <h3>Filtr P/E: kogo odrzucił i kto przeszedł (spółki po etapie wygranych)</h3>
      <ReasonTable name="Odrzucone przez filtr P/E" rows={funnel.pe_rejected} />
      <ReasonTable name="Przeszły filtr P/E" rows={funnel.pe_passed} />
    </>
  )
}
