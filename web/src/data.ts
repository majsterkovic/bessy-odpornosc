import type { AllData } from './types'

export class DataError extends Error {}

export const HINT = 'Uruchom: cd badania/bessy && .venv/bin/python -m bessy.export_web'
const NAMES = ['meta', 'market', 'episodes', 'twins', 'sectors', 'funnel', 'validation', 'lists', 'series'] as const
type Name = (typeof NAMES)[number]

/** Klucze najwyższego poziomu, które każdy plik musi mieć, żeby kroki się wyrenderowały. */
const REQUIRED: Record<Name, string[]> = {
  meta: ['as_of', 'generated_at', 'version'],
  market: ['indices', 'factors', 'summary', 'state_text'],
  episodes: ['rows', 'brief_text'],
  twins: ['text', 'seasonality_monthly', 'after_election', 'after_election_text'],
  sectors: ['behavior_a', 'behavior_b', 'pe', 'pe_text'],
  funnel: ['steps', 'pe_rejected', 'pe_passed'],
  validation: ['oos', 'sensitivity', 'text'],
  lists: ['stocks_a', 'stocks_b', 'etf_a', 'etf_b'],
  series: ['sp500', 'sox', 'twins', 'today'],
}

function checkShape(name: Name, value: unknown): void {
  if (value === null || typeof value !== 'object') throw new DataError(`Plik ${name}.json ma zły kształt. ${HINT}`)
  const missing = REQUIRED[name].filter((k) => !(k in (value as object)))
  if (missing.length) throw new DataError(`Plik ${name}.json nie ma pól: ${missing.join(', ')}. ${HINT}`)
}

export async function loadAll(base = './data'): Promise<AllData> {
  const out: Record<string, unknown> = {}
  for (const name of NAMES) {
    let res: Response
    try {
      res = await fetch(`${base}/${name}.json`)
    } catch {
      throw new DataError(`Nie udało się pobrać pliku ${name}.json. ${HINT}`)
    }
    if (!res.ok) throw new DataError(`Brak pliku ${name}.json (HTTP ${res.status}). ${HINT}`)
    try {
      out[name] = await res.json()
    } catch {
      throw new DataError(`Plik ${name}.json nie jest poprawnym JSON (serwer zwrócił inną treść). ${HINT}`)
    }
    if (name === 'meta') {
      const v = (out.meta as { version?: number } | null)?.version
      if (v !== 1) throw new DataError(`Nieobsługiwana wersja danych (${v}). ${HINT}`)
    }
    checkShape(name, out[name])
  }
  return out as unknown as AllData
}
