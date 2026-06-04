import { useState } from 'react'
import type { AgentBlock } from '../types'

const MAX_PARAMS_DISPLAY = 200
const MAX_RESULT_DISPLAY = 300

interface ToolCallBlockProps {
  block: AgentBlock
  result?: AgentBlock
}

export function ToolCallBlock({ block, result }: ToolCallBlockProps) {
  const [collapsed, setCollapsed] = useState(true)
  const [paramsExpanded, setParamsExpanded] = useState(false)
  const [resultExpanded, setResultExpanded] = useState(false)
  if (block.kind !== 'tool_call') return null

  const json = JSON.stringify(block.params, null, 2)
  const needsParamsTruncation = json.length > MAX_PARAMS_DISPLAY
  const paramsText = paramsExpanded || !needsParamsTruncation
    ? json
    : json.slice(0, MAX_PARAMS_DISPLAY) + '…'

  const resultContent = result?.kind === 'tool_result' ? result.content : null
  const needsResultTruncation = resultContent != null && resultContent.length > MAX_RESULT_DISPLAY
  const resultText = resultExpanded || !needsResultTruncation
    ? resultContent
    : resultContent?.slice(0, MAX_RESULT_DISPLAY) + '…'

  return (
    <div className="cursor-pointer select-none"
      onClick={() => setCollapsed(!collapsed)}
      role="button"
      tabIndex={0}
      aria-expanded={!collapsed}
      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') setCollapsed(!collapsed) }}>
      <div className="flex items-center gap-1.5 text-sm"
        style={{ color: 'var(--text-tertiary)' }}>
        <svg className={`w-3.5 h-3.5 transition-transform ${collapsed ? '' : 'rotate-90'}`}
          fill="currentColor" viewBox="0 0 20 20">
          <path d="M6 4l8 6-8 6V4z" />
        </svg>
        <span style={{ color: 'var(--accent-terracotta)', fontFamily: 'var(--font-mono)' }}>
          {block.toolName}
        </span>
        <span>{collapsed ? '工具调用…' : ''}</span>
      </div>

      {!collapsed && (
        <div className="mt-1.5 ml-5 flex flex-col gap-2" onClick={(e) => e.stopPropagation()}>
          <pre className="text-xs leading-relaxed whitespace-pre-wrap break-all"
            style={{ color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)' }}>
            {paramsText}
          </pre>
          {needsParamsTruncation && (
            <button className="text-xs hover:underline w-fit"
              style={{ color: 'var(--accent-coral)' }}
              onClick={() => setParamsExpanded(!paramsExpanded)}>
              {paramsExpanded ? '收起参数' : '展开参数'}
            </button>
          )}

          {resultContent != null && (
            <div className="rounded-lg px-3 py-2 text-sm leading-relaxed"
              style={{ backgroundColor: 'var(--bg-parchment)', color: 'var(--text-secondary)' }}>
              <div className="text-xs mb-1" style={{ color: 'var(--text-tertiary)' }}>返回结果</div>
              <pre className="whitespace-pre-wrap break-words"
                style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8125rem' }}>
                {resultText}
              </pre>
              {needsResultTruncation && (
                <button className="text-xs mt-1 hover:underline"
                  style={{ color: 'var(--accent-coral)' }}
                  onClick={() => setResultExpanded(!resultExpanded)}>
                  {resultExpanded ? '收起结果' : '展开结果'}
                </button>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
