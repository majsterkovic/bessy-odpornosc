import { describe, expect, it } from 'vitest'
import { fmtDate, fmtInt, fmtNum, fmtPct, fmtPp } from './format'

describe('format', () => {
  it('formats signed percent with Polish comma', () => {
    expect(fmtPct(1.238, 0, true)).toBe('+124%')
    expect(fmtPct(-0.018181, 1)).toBe('-1,8%')
  })
  it('normalises negative zero', () => {
    expect(fmtPct(-0.0004, 1)).toBe('0,0%')
    expect(fmtPct(-0.0004, 1, true)).toBe('0,0%')
  })
  it('returns dash for missing values', () => {
    for (const v of [null, undefined, NaN]) {
      expect(fmtNum(v as number)).toBe('–')
      expect(fmtPct(v as number)).toBe('–')
      expect(fmtPp(v as number)).toBe('–')
      expect(fmtInt(v as number)).toBe('–')
    }
    expect(fmtDate(null)).toBe('–')
  })
  it('groups thousands with spaces', () => {
    expect(fmtNum(1234567, 0)).toBe('1 234 567')
    expect(fmtInt(4778)).toBe('4 778')
  })
  it('formats percentage-point differences with sign', () => {
    expect(fmtPp(0.176)).toBe('+17,6 pp')
    expect(fmtPp(-0.069)).toBe('-6,9 pp')
  })
})
