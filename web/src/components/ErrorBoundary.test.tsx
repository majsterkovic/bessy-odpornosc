import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { ErrorBoundary } from './ErrorBoundary'

function Boom(): never { throw new Error('zły kształt danych') }

describe('ErrorBoundary', () => {
  it('shows the exporter hint instead of a blank page when a step throws', () => {
    vi.spyOn(console, 'error').mockImplementation(() => {})
    render(<ErrorBoundary><Boom /></ErrorBoundary>)
    expect(screen.getByRole('alert').textContent).toMatch(/bessy\.export_web/)
  })
})
