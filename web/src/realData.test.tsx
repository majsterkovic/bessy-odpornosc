import { existsSync, readFileSync } from 'node:fs'
import { join } from 'node:path'
import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import App from './App'
import { buildSpOption } from './charts/spChart'
import type { AllData } from './types'

vi.mock('./charts/Chart', () => ({ Chart: () => <div data-testid="chart" /> }))

const dir = join(__dirname, '..', 'public', 'data')
const NAMES = ['meta', 'market', 'episodes', 'twins', 'sectors', 'funnel', 'validation', 'lists', 'series']

// Test dymny na prawdziwych danych: pomijany, gdy nie wygenerowano `python -m bessy.export_web`.
describe.skipIf(!existsSync(join(dir, 'meta.json')))('real exported data', () => {
  it('renders the page without NaN/undefined/null and with all list tabs populated', async () => {
    const data = Object.fromEntries(NAMES.map((n) => [n, JSON.parse(readFileSync(join(dir, `${n}.json`), 'utf-8'))])) as unknown as AllData
    render(<App loader={async () => data} />)
    await screen.findByRole('heading', { level: 2, name: /Listy Top/ })
    expect(document.body.textContent).not.toMatch(/NaN|undefined|\bnull\b/)
    expect(data.lists.stocks_a.length).toBeGreaterThanOrEqual(10)
    expect(screen.getAllByRole('row').length).toBeGreaterThan(40)
  })
  it('draws every episode band on an existing weekly label (no band silently dropped)', () => {
    const read = (n: string) => JSON.parse(readFileSync(join(dir, `${n}.json`), 'utf-8'))
    const series = read('series'), episodes = read('episodes')
    const opt = buildSpOption(series.sp500, episodes.rows, { logScale: true }) as any
    const labels = new Set<string>(series.sp500.map((p: [string, number]) => p[0]))
    const areas = opt.series[0].markArea.data
    expect(areas.length).toBe(episodes.rows.length)
    for (const [a, b] of areas) {
      expect(labels.has(a.xAxis)).toBe(true)
      expect(labels.has(b.xAxis)).toBe(true)
    }
  })
})
