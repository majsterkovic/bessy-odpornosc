import * as echarts from 'echarts'
import { useEffect, useRef } from 'react'

export function Chart({ option, height = 360, label }: { option: echarts.EChartsOption; height?: number; label: string }) {
  const ref = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (!ref.current) return
    const chart = echarts.init(ref.current, undefined, { renderer: 'svg' })
    chart.setOption(option)
    const ro = typeof ResizeObserver !== 'undefined' ? new ResizeObserver(() => chart.resize()) : null
    ro?.observe(ref.current)
    return () => { ro?.disconnect(); chart.dispose() }
  }, [option])
  return <div className="chart-box"><div ref={ref} role="img" aria-label={label} style={{ width: '100%', height }} /></div>
}

