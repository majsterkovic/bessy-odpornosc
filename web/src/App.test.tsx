import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import App from './App'
import { STEPS } from './steps/steps'
import { sample } from './testData'

vi.mock('./charts/Chart', () => ({ Chart: () => <div data-testid="chart" /> }))

describe('whole page', () => {
  it('renders all seven step headings and the footer date', async () => {
    render(<App loader={async () => sample} />)
    for (const s of STEPS) {
      expect(await screen.findByRole('heading', { level: 2, name: new RegExp(s.title) })).toBeInTheDocument()
    }
    expect(screen.getByText(/Dane do 2026-10-26/)).toBeInTheDocument()
  })
  it('never leaks NaN, undefined or null into the page', async () => {
    render(<App loader={async () => sample} />)
    await screen.findByRole('heading', { level: 2, name: /Listy Top/ })
    expect(document.body.textContent).not.toMatch(/NaN|undefined|\bnull\b/)
  })
})
