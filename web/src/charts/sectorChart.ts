import type { EChartsOption } from 'echarts'
import { fmtPp } from '../format'
import type { SectorBehavior, SectorPe } from '../types'
import { COLORS } from './colors'

export function buildSectorBarsOption(a: SectorBehavior[], b: SectorBehavior[]): EChartsOption {
  const order = a.map((r) => r.sector)
  const bBy = new Map(b.map((r) => [r.sector, r.med_alpha]))
  const label = { show: true, color: COLORS.text, formatter: (p: any) => fmtPp(p.value) }
  return {
    animation: false,
    legend: { top: 0, textStyle: { color: COLORS.text } },
    grid: { left: 150, right: 60, top: 36, bottom: 24 },
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    xAxis: { type: 'value', axisLabel: { color: COLORS.muted, formatter: (v: number) => fmtPp(v, 0) } },
    yAxis: { type: 'category', inverse: true, data: order, axisLabel: { color: COLORS.text } },
    series: [
      { name: 'Wszystkie okresy od 1962', type: 'bar', data: a.map((r) => r.med_alpha), label, itemStyle: { color: '#6cb6ff' } },
      { name: 'Bliźniacze bessy', type: 'bar', data: order.map((s) => bBy.get(s) ?? null), label, itemStyle: { color: '#d2a8ff' } },
    ],
  }
}

export const LOW_COVERAGE = 0.35

export function peAssessmentLabel(r: SectorPe): { text: string; lowCoverage: boolean } {
  const low = r.pokrycie != null && r.pokrycie < LOW_COVERAGE
  const base = r.ocena.replace(/\s*\(niskie pokrycie\)/, '')
  return { text: low ? `${base} (orientacyjne)` : base, lowCoverage: low }
}
