import { Component, type ErrorInfo, type ReactNode } from 'react'
import { HINT } from '../data'

export class ErrorBoundary extends Component<{ children: ReactNode }, { error: Error | null }> {
  state = { error: null as Error | null }
  static getDerivedStateFromError(error: Error) { return { error } }
  componentDidCatch(error: Error, info: ErrorInfo) { console.error(error, info.componentStack) }
  render() {
    if (this.state.error) {
      return <p role="alert" className="status error">Strona nie mogła się wyrenderować: {this.state.error.message}. Dane mogą pochodzić ze starszej wersji eksportera. {HINT}</p>
    }
    return this.props.children
  }
}
