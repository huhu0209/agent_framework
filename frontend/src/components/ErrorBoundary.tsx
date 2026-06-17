import { Component, type ErrorInfo, type ReactNode } from 'react'

interface Props {
  children: ReactNode
}
interface State {
  hasError: boolean
  error: Error | null
}

/**H-FE4: 全局错误边界，捕获子树渲染期异常，防白屏。*/
export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('[ErrorBoundary]', error, info.componentStack)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div
          style={{
            minHeight: '100vh',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '1rem',
            backgroundColor: 'var(--bg, #faf7f0)',
            color: 'var(--text, #2d2a26)',
            fontFamily: 'system-ui, sans-serif',
            padding: '2rem',
            textAlign: 'center',
          }}
        >
          <h1 style={{ fontSize: '1.5rem', margin: 0 }}>出错了</h1>
          <p style={{ margin: 0, color: 'var(--text-2, #6b6358)' }}>
            页面渲染时发生异常。
          </p>
          {this.state.error && (
            <pre
              style={{
                maxWidth: '600px',
                overflow: 'auto',
                fontSize: '0.8rem',
                color: 'var(--text-3, #9a9088)',
                background: 'var(--surface, #f0ebe0)',
                padding: '0.75rem',
                borderRadius: '6px',
              }}
            >
              {this.state.error.message}
            </pre>
          )}
          <button
            onClick={() => window.location.reload()}
            style={{
              padding: '0.5rem 1.25rem',
              border: '1px solid var(--border-2, #d4cab8)',
              borderRadius: '6px',
              background: 'transparent',
              color: 'var(--text, #2d2a26)',
              cursor: 'pointer',
            }}
          >
            刷新页面
          </button>
        </div>
      )
    }
    return this.props.children
  }
}
