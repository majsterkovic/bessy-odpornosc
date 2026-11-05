import type { EChartsOption } from 'echarts'
import { fmtInt, fmtPct, fmtPp } from '../format'
import type { FunnelStep, Oos } from '../types'
import { COLORS } from './colors'

/** Lejek zaczyna się od kandydatów; cała baza (49 841 instrumentów) to inna skala i zgniotłaby resztę. */
export function buildFunnelOption(allSteps: FunnelStep[]): EChartsOption {
  const steps = allSteps.filter((s) => s.key !== 'akcje_w_bazie')
  // Szerokość = kolejny krok (nie liczność), żeby małe etapy (671, 562, 15) były widoczne; liczności są w etykietach.
  const data = steps.map((s, i) => ({ name: s.label, value: steps.length - i, n: s.n, share: i === 0 ? null : s.n / steps[i - 1].n }))
  return {
    animation: false,
    tooltip: { trigger: 'item', formatter: (p: any) => `${p.name}: ${fmtInt(p.data.n)}` },
    series: [{
      type: 'funnel', sort: 'none', min: 0, minSize: '6%', left: '4%', right: '4%', top: 8, bottom: 8, gap: 3,
      label: { show: true, position: 'inside', color: '#fff', fontWeight: 600, formatter: (p: any) => `${fmtInt(p.data.n)}${p.data.share != null ? ` (${fmtPct(p.data.share, 0)} poprz.)` : ''}` },
      itemStyle: { borderWidth: 0 }, data,
    }],
  }
}

export function buildQuintileOption(oos: Oos): EChartsOption {
  return {
    animation: false,
    grid: { left: 56, right: 16, top: 16, bottom: 36 },
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', name: 'kwintyl wyniku (1 = najgorszy)', nameLocation: 'middle', nameGap: 26, data: oos.kwintyle.map((q) => String(q.kwintyl)), axisLabel: { color: COLORS.muted } },
    yAxis: { type: 'value', axisLabel: { color: COLORS.muted, formatter: (v: number) => fmtPp(v, 0) }, splitLine: { lineStyle: { color: 'rgba(139,148,158,0.2)' } } },
    series: [{
      name: 'Mediana alfy w okresach testowych', type: 'bar', data: oos.kwintyle.map((q) => q.test_med_alpha),
      itemStyle: { color: (p: any) => (p.value >= 0 ? COLORS.accent : COLORS.bear) },
      label: { show: true, position: 'top', color: COLORS.text, formatter: (p: any) => fmtPp(p.value) },
    }],
  }
}
