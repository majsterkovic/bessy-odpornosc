import type { ListRow } from '../types'

export type SortKey = 'rank' | 'n_bessy' | 'med_alpha' | 'downside_beta' | 'med_max_dd' | 'win_rate' | 'n_valid' | 'ticker'
export type Dir = 'asc' | 'desc'
export const DEFAULT_SORT: { key: SortKey; dir: Dir } = { key: 'rank', dir: 'asc' }

/** Sortuje kopię; wartości puste (null) zawsze na końcu. */
export function sortRows(rows: ListRow[], key: SortKey, dir: Dir): ListRow[] {
  const sign = dir === 'asc' ? 1 : -1
  return [...rows].sort((a, b) => {
    const x = a[key], y = b[key]
    if (x == null && y == null) return 0
    if (x == null) return 1
    if (y == null) return -1
    return (x < y ? -1 : x > y ? 1 : 0) * sign
  })
}

export interface Filters { query?: string; klass?: string | null; onlyWithPe?: boolean }

export function filterRows(rows: ListRow[], f: Filters): ListRow[] {
  const q = f.query?.trim().toLowerCase()
  return rows.filter((r) =>
    (!q || r.ticker.toLowerCase().includes(q) || r.name.toLowerCase().includes(q)) &&
    (!f.klass || r.klass === f.klass) &&
    (!f.onlyWithPe || r.pe != null))
}

export const EUROPE_LISTED = '(notowany w Europie)'

export function flagsOf(r: ListRow): string[] {
  const flags: string[] = []
  if (r.note) flags.push(r.note)
  if (r.klass != null && !r.ucits) flags.push('brak odpowiednika UCITS')
  return flags
}
