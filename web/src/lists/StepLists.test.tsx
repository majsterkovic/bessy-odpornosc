import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { sample } from '../testData'
import { StepLists } from '../steps/StepLists'

vi.mock('../charts/Chart', () => ({ Chart: () => <div data-testid="chart" /> }))

describe('StepLists', () => {
  it('shows four list tabs and starts on stocks for every bear', () => {
    render(<StepLists lists={sample.lists} />)
    expect(screen.getAllByRole('tab')).toHaveLength(4)
    expect(screen.getByRole('tab', { selected: true }).textContent).toMatch(/Spółki.*każdą bessę/)
  })
  it('never prints NaN, null or undefined, and shows a dash for a missing P/E', () => {
    render(<StepLists lists={sample.lists} />)
    const text = document.body.textContent ?? ''
    expect(text).not.toMatch(/NaN|null|undefined/)
    const r = screen.getAllByRole('row').find((x) => x.textContent?.includes('AAA.US'))!
    expect(within(r).getAllByText('–').length).toBeGreaterThan(0)
  })
  it('switches to ETF lists and shows UCITS equivalents', async () => {
    render(<StepLists lists={sample.lists} />)
    await userEvent.click(screen.getByRole('tab', { name: /ETF.*każdą bessę/ }))
    expect(screen.getByText('IQQ0.XETRA (0.92)')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('tab', { name: /ETF.*obecny/ }))
    expect(screen.getByText('brak odpowiednika UCITS')).toBeInTheDocument()
  })
  it('opens a details panel with the reasoning and per-period alpha on row click', async () => {
    render(<StepLists lists={sample.lists} />)
    await userEvent.click(screen.getByRole('button', { name: /AAA\.US/ }))
    const panel = screen.getByRole('region', { name: 'Szczegóły AAA.US' })
    expect(panel.textContent).toContain('pokonał S&P 500 w 7/7 okresach')
    expect(panel.textContent).toContain('2022-01-03')
    expect(panel.textContent).toContain('+20,0 pp')
  })
  it('lists in ranking order, with the bear count column and the SOX trend columns on list B', async () => {
    render(<StepLists lists={sample.lists} />)
    const rows = screen.getAllByRole('row').slice(1)
    expect(rows[0].textContent).toContain('AAA.US')
    expect(screen.getByRole('columnheader', { name: 'W tym bessy' })).toBeInTheDocument()
    await userEvent.click(screen.getByRole('tab', { name: /Spółki.*obecny/ }))
    expect(screen.getByRole('columnheader', { name: 'Alfa od szczytu SOX' })).toBeInTheDocument()
    expect(screen.getByRole('columnheader', { name: 'Alfa 63 sesje' })).toBeInTheDocument()
  })
  it('filters rows by the search box', async () => {
    render(<StepLists lists={sample.lists} />)
    await userEvent.type(screen.getByRole('searchbox'), 'beta')
    expect(screen.queryByText('AAA.US')).not.toBeInTheDocument()
    expect(screen.getByText('BBB.SW')).toBeInTheDocument()
  })
})
