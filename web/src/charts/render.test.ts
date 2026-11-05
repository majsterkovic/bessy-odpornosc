import * as echarts from 'echarts'
import { describe, expect, it } from 'vitest'
import { sample } from '../testData'
import { buildFunnelOption, buildQuintileOption } from './funnelChart'
import { buildSectorBarsOption } from './sectorChart'
import { buildRelativeOption, buildSpOption } from './spChart'
import { buildTwinsOption } from './twinsChart'

// Renderowanie po stronie serwera (SVG) sprawdza, ze ECharts przyjmuje opcje i rysuje niepusty wykres.
function svgOf(option: echarts.EChartsOption): string {
  const chart = echarts.init(null, undefined, { renderer: 'svg', ssr: true, width: 800, height: 400 })
  chart.setOption(option)
  const svg = chart.renderToSVGString()
  chart.dispose()
  return svg
}

describe('chart options render in ECharts', () => {
  const cases: [string, echarts.EChartsOption][] = [
    ['S&P 500 z epizodami (log)', buildSpOption(sample.series.sp500, sample.episodes.rows, { logScale: true })],
    ['S&P 500 z epizodami (lin)', buildSpOption(sample.series.sp500, sample.episodes.rows, { logScale: false })],
    ['SOX / S&P', buildRelativeOption([['2026-01-02', 10], ['2026-01-09', 9]], [['2026-01-02', 100], ['2026-01-09', 100]])],
    ['bliźniaki', buildTwinsOption(sample.series.twins, sample.series.today)],
    ['sektory', buildSectorBarsOption(sample.sectors.behavior_a, sample.sectors.behavior_b)],
    ['lejek', buildFunnelOption(sample.funnel.steps)],
    ['kwintyle', buildQuintileOption(sample.validation.oos)],
  ]
  it.each(cases)('%s', (_name, option) => {
    const svg = svgOf(option)
    expect(svg.startsWith('<svg')).toBe(true)
    expect(svg.length).toBeGreaterThan(500)
  })
})
