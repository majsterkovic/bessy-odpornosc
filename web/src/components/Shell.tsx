import type { ReactNode } from 'react'
import { useActiveStep } from '../hooks/useActiveStep'
import { STEP_IDS, STEPS } from '../steps/steps'
import type { Meta } from '../types'
import { DisclaimerBar } from './DisclaimerBar'
import { StepSection as StepWrapper } from './StepSection'

export function Shell({ meta, bodies }: { meta: Meta; bodies: Partial<Record<string, { lead?: ReactNode; body?: ReactNode }>> }) {
  const active = useActiveStep(STEP_IDS)
  return (
    <div className="shell">
      <nav aria-label="Kroki" className="toc">
        <div className="toc-title">Odporność na bessę</div>
        {STEPS.map((s, i) => (
          <a key={s.id} href={`#${s.id}`} aria-current={active === s.id ? 'step' : undefined}
             onClick={(e) => { e.preventDefault(); document.getElementById(s.id)?.scrollIntoView({ behavior: 'smooth' }) }}>
            <span className="step-num">{i + 1}</span> {s.title}
          </a>
        ))}
      </nav>
      <main className="content">
        <DisclaimerBar />
        {STEPS.map((s, i) => (
          <StepWrapper key={s.id} id={s.id} index={i + 1} title={s.title} lead={bodies[s.id]?.lead}>{bodies[s.id]?.body}</StepWrapper>
        ))}
        <footer className="footer">Dane do {meta.as_of}, wygenerowano {meta.generated_at}. Źródło: badanie bess (baza marketdata, tylko odczyt).</footer>
      </main>
    </div>
  )
}
