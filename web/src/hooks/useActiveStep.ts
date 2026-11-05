import { useEffect, useState } from 'react'

export interface StepEntry { id: string; ratio: number; top: number }
export const FIRST_STEP = 'gdzie'

/** Krok o największym widocznym udziale; remis wygrywa wyższa sekcja; brak widocznych = pierwszy krok. */
export function pickActiveStep(entries: StepEntry[]): string {
  const visible = entries.filter((e) => e.ratio > 0)
  if (visible.length === 0) return FIRST_STEP
  return visible.reduce((best, e) => (e.ratio > best.ratio || (e.ratio === best.ratio && e.top < best.top) ? e : best)).id
}

export function useActiveStep(ids: string[]): string {
  const [active, setActive] = useState(FIRST_STEP)
  useEffect(() => {
    if (typeof IntersectionObserver === 'undefined') return
    const state = new Map<string, StepEntry>()
    const io = new IntersectionObserver(
      (items) => {
        for (const it of items) {
          state.set(it.target.id, { id: it.target.id, ratio: it.intersectionRatio, top: it.boundingClientRect.top })
        }
        setActive(pickActiveStep([...state.values()]))
      },
      { threshold: [0, 0.1, 0.25, 0.5, 0.75, 1] },
    )
    for (const id of ids) {
      const el = document.getElementById(id)
      if (el) io.observe(el)
    }
    return () => io.disconnect()
  }, [ids])
  return active
}
