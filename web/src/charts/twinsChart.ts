import type { EChartsOption } from 'echarts'
import type { Series } from '../types'
import { COLORS } from './colors'

const PALETTE = ['#6cb6ff', '#d2a8ff', '#f0883e', '#57ab5a', '#e5534b']

export function buildTwinsOption(twins: Series['twins'], today: Series['today']): EChartsOption {
  const lines = twins.map((t, i) => ({ name: t.episode_id, type: 'line' as const, showSymbol: false, data: t.path, lineStyle: { width: 1.5, color: PALETTE[i % PALETTE.length] } }))
  lines.push({ name: 'dziś', type: 'line', showSymbol: false, data: today.path, lineStyle: { width: 3.5, color: '#ffffff' } })
  return {
    animation: false,
    legend: { top: 0, textStyle: { color: COLORS.text } },
    grid: { left: 48, right: 16, top: 36, bottom: 40 },
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'value', name: 'dni od szczytu', nameLocation: 'middle', nameGap: 26, axisLabel: { color: COLORS.muted } },
    yAxis: { type: 'value', scale: true, name: 'szczyt = 100', axisLabel: { color: COLORS.muted }, splitLine: { lineStyle: { color: 'rgba(139,148,158,0.2)' } } },
    series: lines,
  }
}
