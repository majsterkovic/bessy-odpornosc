import type { ReactNode } from 'react'

export function StepSection({ id, index, title, lead, children }: { id: string; index: number; title: string; lead?: ReactNode; children?: ReactNode }) {
  return (
    <section id={id} className="step" aria-labelledby={`${id}-h`}>
      <h2 id={`${id}-h`}><span className="step-num">{index}</span> {title}</h2>
      {lead ? <p className="lead">{lead}</p> : null}
      {children}
    </section>
  )
}
