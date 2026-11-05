import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import App from '../App'
import { DataError } from '../data'
import { sample } from '../testData'

describe('App shell', () => {
  it('shows the exporter hint when data cannot be loaded', async () => {
    render(<App loader={() => Promise.reject(new DataError('Brak pliku. Uruchom: python -m bessy.export_web'))} />)
    expect(await screen.findByText(/bessy\.export_web/)).toBeInTheDocument()
  })
  it('renders seven steps in the table of contents and the as_of footer', async () => {
    render(<App loader={async () => sample} />)
    const nav = await screen.findByRole('navigation', { name: 'Kroki' })
    expect(nav.querySelectorAll('a')).toHaveLength(7)
    expect(screen.getByText(/Dane do 2026-10-26/)).toBeInTheDocument()
  })
  it('keeps the disclaimer bar with XTB and UCITS caveats visible', async () => {
    render(<App loader={async () => sample} />)
    const bar = await screen.findByRole('note', { name: 'Zastrzeżenia' })
    expect(bar.textContent).toMatch(/XTB/)
    expect(bar.textContent).toMatch(/UCITS/)
  })
})
