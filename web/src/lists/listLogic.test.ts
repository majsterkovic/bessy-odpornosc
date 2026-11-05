import { describe, expect, it } from 'vitest'
import { row } from '../testData'
import { DEFAULT_SORT, filterRows, flagsOf, sortRows } from './listLogic'

const rows = [row({ ticker: 'A', med_alpha: 0.1 }), row({ ticker: 'B', med_alpha: null }), row({ ticker: 'C', med_alpha: 0.3 })]

describe('sortRows', () => {
  it('puts null values last in both directions', () => {
    expect(sortRows(rows, 'med_alpha', 'desc').map((r) => r.ticker)).toEqual(['C', 'A', 'B'])
    expect(sortRows(rows, 'med_alpha', 'asc').map((r) => r.ticker)).toEqual(['A', 'C', 'B'])
  })
  it('does not mutate the input', () => {
    const copy = [...rows]
    sortRows(rows, 'ticker', 'desc')
    expect(rows).toEqual(copy)
  })
})

describe('filterRows', () => {
  const data = [row({ ticker: 'BBB.SW', name: 'Swiss Bank', klass: 'akcje', pe: 18 }), row({ ticker: 'CCC.US', name: 'Gold', klass: 'surowce i waluty', pe: null })]
  it('matches query on ticker and name case-insensitively', () => {
    expect(filterRows(data, { query: 'swiss' })).toHaveLength(1)
    expect(filterRows(data, { query: 'ccc' })).toHaveLength(1)
  })
  it('filters by class and by P/E presence', () => {
    expect(filterRows(data, { klass: 'surowce i waluty' }).map((r) => r.ticker)).toEqual(['CCC.US'])
    expect(filterRows(data, { onlyWithPe: true }).map((r) => r.ticker)).toEqual(['BBB.SW'])
  })
})

describe('flagsOf', () => {
  it('returns the note as a flag', () => {
    expect(flagsOf(row({ note: 'brak danych EPS' }))).toEqual(['brak danych EPS'])
    expect(flagsOf(row({ note: null }))).toEqual([])
  })
  it('flags ETFs without a UCITS equivalent but not those listed in Europe', () => {
    expect(flagsOf(row({ klass: 'akcje', ucits: null, note: null }))).toEqual(['brak odpowiednika UCITS'])
    expect(flagsOf(row({ klass: 'akcje', ucits: '(notowany w Europie)', note: null }))).toEqual([])
    expect(flagsOf(row({ klass: 'akcje', ucits: 'IQQ0.XETRA (0.92)', note: null }))).toEqual([])
  })
})

describe('default order', () => {
  it('is the ranking order (rank ascending)', () => {
    expect(DEFAULT_SORT).toEqual({ key: 'rank', dir: 'asc' })
    const r = [row({ rank: 3, ticker: 'C' }), row({ rank: 1, ticker: 'A' }), row({ rank: 2, ticker: 'B' })]
    expect(sortRows(r, DEFAULT_SORT.key, DEFAULT_SORT.dir).map((x) => x.ticker)).toEqual(['A', 'B', 'C'])
  })
})
