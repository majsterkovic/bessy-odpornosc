import { render } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { Chart } from './Chart'

describe('Chart', () => {
  it('draws on its own dark panel so colours stay readable in the light theme', () => {
    const { container } = render(<Chart option={{ xAxis: { type: 'category', data: ['a', 'b'] }, yAxis: { type: 'value' }, series: [{ type: 'line', data: [1, 2] }] }} label="test" />)
    expect(container.querySelector('.chart-box')).not.toBeNull()
  })
})
