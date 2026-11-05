import type { ReactNode } from 'react'

export function Collapsible({ title = 'Jak to policzono', children }: { title?: string; children: ReactNode }) {
  return (
    <details className="collapsible">
      <summary>{title}</summary>
      <div className="collapsible-body">{children}</div>
    </details>
  )
}
