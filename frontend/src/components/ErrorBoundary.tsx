import { Component, type ErrorInfo, type ReactNode } from 'react'

type ErrorBoundaryProps = {
  children: ReactNode
}

type ErrorBoundaryState = {
  hasError: boolean
}

export default class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = {
    hasError: false,
  }

  static getDerivedStateFromError(): ErrorBoundaryState {
    return { hasError: true }
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Unhandled React error:', error, errorInfo)
    // Report to external monitoring (e.g. Sentry, Datadog)
    if (typeof window !== 'undefined' && (window as any).__ERROR_REPORTER__) {
      (window as any).__ERROR_REPORTER__(error, errorInfo)
    }
  }

  handleGoHome = () => {
    window.location.href = '/'
  }

  handleGoBack = () => {
    window.history.back()
  }

  handleReload = () => {
    window.location.reload()
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-[50vh] flex items-center justify-center p-6">
          <div className="surface-card w-full max-w-md rounded-2xl p-8 text-center dark:bg-slate-900 dark:text-slate-100">
            <h2 className="text-xl font-display font-semibold text-slate-900 dark:text-slate-100">Something went wrong</h2>
            <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">An unexpected error occurred in this section. You can try one of the actions below.</p>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-3 mt-5">
              <button className="btn-primary" onClick={this.handleReload}>
                Reload Page
              </button>
              <button className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 dark:hover:bg-slate-800" onClick={this.handleGoBack}>
                Go Back
              </button>
              <button className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 dark:hover:bg-slate-800" onClick={this.handleGoHome}>
                Go to Dashboard
              </button>
            </div>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}
