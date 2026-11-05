import type { EChartsOption } from 'echarts'
import type { EpisodeRow } from '../types'
import { COLORS } from './colors'

/** Pierwsza etykieta tygodniowa >= data (ISO, więc porównanie tekstowe); poza zakresem: ostatnia. */
export function snapToLabel(labels: string[], date: string): string {
  let lo = 0, hi = labels.length - 1
  if (hi < 0 || date > labels[hi]) return labels[hi] ?? date
  while (lo < hi) {
    const mid = (lo + hi) >> 1
    if (labels[mid] >= date) hi = mid
    else lo = mid + 1
  }
  return labels[lo]
}

export function buildSpOption(series: [string, number][], episodes: EpisodeRow[], opts: { logScale: boolean }): EChartsOption {
  const labels = series.map((p) => p[0])
  const areas = episodes.map((e) => [
    { name: `${e.episode_id} (${e.kind})`, xAxis: snapToLabel(labels, e.peak_date), itemStyle: { color: e.kind === 'bessa' ? 'rgba(229,83,75,0.25)' : 'rgba(217,164,65,0.22)' } },
    { xAxis: snapToLabel(labels, e.trough_date) },
  ])
  return {
    animation: false,
    grid: { left: 56, right: 16, top: 16, bottom: 56 },
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: labels, axisLabel: { color: COLORS.muted } },
    yAxis: { type: opts.logScale ? 'log' : 'value', scale: true, axisLabel: { color: COLORS.muted }, splitLine: { lineStyle: { color: 'rgba(139,148,158,0.2)' } } },
    dataZoom: [{ type: 'inside' }, { type: 'slider', height: 20, bottom: 8 }],
    series: [{ name: 'S&P 500', type: 'line', showSymbol: false, data: series.map((p) => p[1]), lineStyle: { width: 1.5, color: COLORS.line }, markArea: { silent: false, data: areas as any } }],
  }
}

/** Stosunek SOX do S&P 500 (wspólne daty), znormalizowany do maksimum = 100. */
export function buildRelativeOption(sox: [string, number][], sp: [string, number][]): EChartsOption {
  const spMap = new Map(sp)
  const pairs = sox.filter(([d]) => spMap.has(d)).map(([d, v]) => [d, v / spMap.get(d)!] as [string, number])
  const max = Math.max(...pairs.map((p) => p[1]))
  return {
    animation: false,
    grid: { left: 48, right: 16, top: 16, bottom: 32 },
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: pairs.map((p) => p[0]), axisLabel: { color: COLORS.muted } },
    yAxis: { type: 'value', scale: true, axisLabel: { color: COLORS.muted }, splitLine: { lineStyle: { color: 'rgba(139,148,158,0.2)' } } },
    series: [{ name: 'SOX / S&P 500 (maks. = 100)', type: 'line', showSymbol: false, data: pairs.map((p) => +(p[1] / max * 100).toFixed(2)), lineStyle: { width: 1.5, color: COLORS.accent } }],
  }
}
