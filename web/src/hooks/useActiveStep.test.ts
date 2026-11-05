import { describe, expect, it } from 'vitest'
import { pickActiveStep } from './useActiveStep'

describe('pickActiveStep', () => {
  it('picks the entry with the largest visible ratio', () => {
    expect(pickActiveStep([{ id: 'a', ratio: 0.2, top: 10 }, { id: 'b', ratio: 0.7, top: 400 }])).toBe('b')
  })
  it('breaks ties in favour of the higher section', () => {
    expect(pickActiveStep([{ id: 'a', ratio: 0.5, top: 300 }, { id: 'b', ratio: 0.5, top: 10 }])).toBe('b')
  })
  it('falls back to the first step when nothing is visible', () => {
    expect(pickActiveStep([])).toBe('gdzie')
    expect(pickActiveStep([{ id: 'b', ratio: 0, top: 50 }])).toBe('gdzie')
  })
})
