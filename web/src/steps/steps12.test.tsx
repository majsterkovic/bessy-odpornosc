import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { buildRelativeOption, buildSpOption } from '../charts/spChart'
import { sample } from '../testData'
import { leadWhere, StepWhere } from './StepWhere'
import { StepEpisodes } from './StepEpisodes'

vi.mock('../charts/Chart', () => ({ Chart: () => <div data-testid="chart" /> }))

describe('step 1', () => {
  it('lead text takes its numbers from the data', () => {
    const changed = structuredClone(sample.market)
    changed.indices[0].od_ath = -0.099
    expect(leadWhere(sample.market)).toContain('1,8%')
    expect(leadWhere(changed)).toContain('9,9%')
    expect(leadWhere(changed)).not.toContain('1,8%')
    expect(leadWhere(sample.market)).toContain('zdrożała o 124%')
    const cheaper = structuredClone(sample.market)
    cheaper.indices[4].r_12m = -0.2
    expect(leadWhere(cheaper)).toContain('potaniała o 20%')
    expect(leadWhere(cheaper)).not.toContain('-')
  })
  it('does not claim "no bear" when the S&P 500 is already 20% below its peak', () => {
    const bear = structuredClone(sample.market)
    bear.indices[0].od_ath = -0.25
    expect(leadWhere(sample.market)).toContain('nie reakcja na trwającą')
    expect(leadWhere(bear)).not.toContain('nie reakcja na trwającą')
  })
  it('shows five main index cards first and the rest in a second row', () => {
    render(<StepWhere market={sample.market} series={sample.series} />)
    const main = screen.getByTestId('cards-primary')
    for (const n of ['S&P 500', 'Nasdaq 100', 'Półprzewodniki (SOX)', 'WIG20', 'Brent (indeks BCOMCO)']) {
      expect(within(main).getByText(n)).toBeInTheDocument()
    }
    expect(within(screen.getByTestId('cards-secondary')).getByText('VIX')).toBeInTheDocument()
  })
})

describe('step 2', () => {
  it('builds one markArea per episode with different colours for bear markets and corrections', () => {
    const opt = buildSpOption(sample.series.sp500, sample.episodes.rows, { logScale: true }) as any
    const areas = opt.series[0].markArea.data
    expect(areas).toHaveLength(3)
    const colour = (i: number) => areas[i][0].itemStyle.color
    expect(colour(1)).not.toEqual(colour(2))
    expect(opt.yAxis.type).toBe('log')
  })
  it('snaps episode boundaries to weekly category labels so every band can be drawn', () => {
    const labels: [string, number][] = [['2018-09-21', 1], ['2018-09-28', 1], ['2018-12-28', 1], ['2022-01-07', 1]]
    const eps = [{ ...sample.episodes.rows[2], peak_date: '2018-09-20', trough_date: '2018-12-24' }]
    const areas = (buildSpOption(labels, eps, { logScale: false }) as any).series[0].markArea.data
    const names = labels.map((l) => l[0])
    expect(names).toContain(areas[0][0].xAxis)
    expect(names).toContain(areas[0][1].xAxis)
  })
  it('relative option has one point per shared date', () => {
    const opt = buildRelativeOption([['2026-01-02', 10], ['2026-01-09', 9]], [['2026-01-02', 100], ['2026-01-09', 100], ['2026-01-16', 100]]) as any
    expect(opt.series[0].data).toHaveLength(2)
  })
  it('marks episodes counted in ranking A', () => {
    render(<StepEpisodes episodes={sample.episodes} series={sample.series} />)
    const rows = screen.getAllByRole('row').slice(1)
    const byId = (id: string) => rows.find((r) => r.textContent?.includes(id))!
    expect(byId('1973-01-11').textContent).toContain('tak')
    expect(byId('1929-09-16').textContent).not.toContain('tak')
  })
  it('shows time to recovery', () => {
    render(<StepEpisodes episodes={sample.episodes} series={sample.series} />)
    const r = screen.getAllByRole('row').find((x) => x.textContent?.includes('1973-01-11'))!
    expect(r.textContent).toContain('2 114')
    expect(screen.getByRole('columnheader', { name: 'Dni do odbudowy' })).toBeInTheDocument()
  })
  it('sorts by depth when the header is clicked', async () => {
    render(<StepEpisodes episodes={sample.episodes} series={sample.series} />)
    await userEvent.click(screen.getByRole('button', { name: /Głębokość/ }))
    const first = screen.getAllByRole('row')[1].textContent
    expect(first).toContain('1973-01-11')
  })
})
