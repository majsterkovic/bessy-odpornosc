import { render, screen, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { buildSectorBarsOption, peAssessmentLabel } from '../charts/sectorChart'
import { buildTwinsOption } from '../charts/twinsChart'
import { Md } from '../components/Md'
import { sample } from '../testData'
import { StepSectors } from './StepSectors'
import { leadTwins, StepTwins } from './StepTwins'

vi.mock('../charts/Chart', () => ({ Chart: () => <div data-testid="chart" /> }))

describe('step 3', () => {
  it('twins lead names the number of twins from data', () => {
    expect(leadTwins(sample.series.twins.length)).toContain('Najbliższa')
    expect(leadTwins(4)).toContain('Cztery')
  })
  it('twins chart has one series per twin plus today on a day axis', () => {
    const opt = buildTwinsOption(sample.series.twins, sample.series.today) as any
    expect(opt.series).toHaveLength(2)
    expect(opt.series.map((s: any) => s.name)).toEqual(['1973-01-11', 'dziś'])
    expect(opt.xAxis.type).toBe('value')
  })
  it('shows a dash for missing distance and one row per seasonality month', () => {
    render(<StepTwins twins={sample.twins} market={sample.market} series={sample.series} />)
    const factors = screen.getByRole('table', { name: 'Czynniki makro' })
    expect(within(factors).getAllByRole('row')[1].textContent).toContain('–')
    expect(within(screen.getByRole('table', { name: 'Sezonowość midterms' })).getAllByRole('row')).toHaveLength(1 + sample.twins.seasonality_monthly.length)
    expect(factors.textContent).toContain('+124%')
  })
})

describe('Md', () => {
  it('renders bold and list items without raw markdown markers', () => {
    render(<Md text={'- **1973-01-11** (bessa)\n- druga linia'} />)
    expect(screen.getAllByRole('listitem')).toHaveLength(2)
    expect(screen.getByText('1973-01-11').tagName).toBe('STRONG')
    expect(document.body.textContent).not.toContain('**')
  })
})

describe('step 4', () => {
  it('keeps sector order and signed labels in the bars option', () => {
    const opt = buildSectorBarsOption(sample.sectors.behavior_a, sample.sectors.behavior_b) as any
    expect(opt.yAxis.data).toEqual(['Utilities', 'Technology'])
    expect(opt.series[0].label.formatter({ value: 0.12 })).toBe('+12,0 pp')
    expect(opt.series[0].label.formatter({ value: -0.027 })).toBe('-2,7 pp')
  })
  it('flags low coverage as indicative', () => {
    expect(peAssessmentLabel(sample.sectors.pe[1])).toEqual({ text: 'tani (orientacyjne)', lowCoverage: true })
    expect(peAssessmentLabel(sample.sectors.pe[0])).toEqual({ text: 'tani', lowCoverage: false })
    expect(peAssessmentLabel({ ...sample.sectors.pe[1], ocena: 'tani (niskie pokrycie)' }).text).toBe('tani (orientacyjne)')
  })
  it('renders the P/E table with the indicative label', () => {
    render(<StepSectors sectors={sample.sectors} />)
    expect(screen.getByText('tani (orientacyjne)')).toBeInTheDocument()
  })
})
