import { render, screen, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { buildFunnelOption, buildQuintileOption } from '../charts/funnelChart'
import { sample } from '../testData'
import { leadFunnel, StepFunnel } from './StepFunnel'
import { leadValidation, StepValidation } from './StepValidation'

vi.mock('../charts/Chart', () => ({ Chart: () => <div data-testid="chart" /> }))

describe('step 5', () => {
  it('funnel keeps stage order and adds the share of the previous stage', () => {
    const opt = buildFunnelOption(sample.funnel.steps) as any
    const data = opt.series[0].data
    expect(data.map((d: any) => d.name)).toEqual(sample.funnel.steps.map((s) => s.label))
    expect(opt.series[0].label.formatter({ data: { ...data[1] } })).toContain('72%')
    expect(opt.series[0].label.formatter({ data: { ...data[0] } })).not.toContain('%')
  })
  it('drops the whole-database stage and uses equal-step widths so small stages stay visible', () => {
    const steps = [{ key: 'akcje_w_bazie', label: 'Baza', n: 49841, note: '' }, ...sample.funnel.steps]
    const data = (buildFunnelOption(steps) as any).series[0].data
    expect(data.map((d: any) => d.name)).not.toContain('Baza')
    const v = data.map((d: any) => d.value)
    expect(v.every((x: number, i: number) => i === 0 || x < v[i - 1])).toBe(true)
    expect(v[v.length - 1]).toBeGreaterThan(0)
  })
  it('lead text follows the data', () => {
    const changed = structuredClone(sample.funnel)
    changed.steps[0].n = 5000
    expect(leadFunnel(sample.funnel)).toContain('4 778')
    expect(leadFunnel(changed)).toContain('5 000')
    expect(leadFunnel(sample.funnel)).toContain('15')
  })
  it('renders rejected and passed P/E reasons in separate tables and a dash for a missing reason', () => {
    const f = structuredClone(sample.funnel)
    f.pe_rejected.push({ reason: null as unknown as string, n: 2 })
    render(<StepFunnel funnel={f} />)
    expect(within(screen.getByRole('table', { name: 'Odrzucone przez filtr P/E' })).getByText('ujemny zysk (EPS)')).toBeInTheDocument()
    expect(within(screen.getByRole('table', { name: 'Przeszły filtr P/E' })).getByText('przeszło bez uwag')).toBeInTheDocument()
    expect(screen.getByText('–')).toBeInTheDocument()
  })
})

describe('step 6', () => {
  it('quintile chart has one bar per quintile', () => {
    const opt = buildQuintileOption(sample.validation.oos) as any
    expect(opt.series[0].data).toHaveLength(2)
  })
  it('lead text uses rank correlation, quintile alphas and overlap from the data', () => {
    const t = leadValidation(sample.validation)
    expect(t).toContain('0,48')
    expect(t).toContain('+7,4 pp')
    expect(t).toContain('-6,8 pp')
    expect(t).toContain('8 z 15')
    const changed = structuredClone(sample.validation)
    changed.sensitivity.overlap15 = 11
    expect(leadValidation(changed)).toContain('11 z 15')
    expect(leadValidation(sample.validation, 12)).toContain('8 z 12')
  })
  it('lists the stable core tickers', () => {
    render(<StepValidation validation={sample.validation} />)
    expect(screen.getByText(/BEKN\.SW/)).toBeInTheDocument()
  })
})
