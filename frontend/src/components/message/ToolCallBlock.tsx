import { useState } from 'react'
import { Wrench, CheckCircle } from '@phosphor-icons/react'
import type { AgentBlock } from '../../types'

const MAX_PARAMS = 200
const MAX_RESULT = 300

export function ToolCallBlock({ block, result }: { block: AgentBlock; result?: AgentBlock }) {
  const [paramsExpanded, setParamsExpanded] = useState(false)
  const [resultExpanded, setResultExpanded] = useState(false)
  if (block.kind !== 'tool_call') return null

  const json = JSON.stringify(block.params, null, 2)
  const needsParamsTrunc = json.length > MAX_PARAMS
  const paramsText = paramsExpanded || !needsParamsTrunc ? json : json.slice(0, MAX_PARAMS) + '…'

  const resultContent = result?.kind === 'tool_result' ? result.content : null
  const needsResultTrunc = resultContent != null && resultContent.length > MAX_RESULT
  const resultText = resultExpanded || !needsResultTrunc ? resultContent : resultContent?.slice(0, MAX_RESULT) + '…'

  return (
    <div className="flex items-start gap-2.5 px-3.5 py-2.5 rounded-lg mb-3" style={{ backgroundColor: 'var(--surface)', border: '1px solid var(--border-2)', borderLeft: '3px solid var(--brand)' }}>
      <Wrench size={16} className="mt-0.5 shrink-0" style={{ color: 'var(--brand)' }} />
      <div className="flex-1 min-w-0">
        <div className="text-[13.5px] font-semibold" style={{ color: 'var(--text)', fontFamily: 'var(--font-mono)' }}>{block.toolName}</div>
        <pre className="text-[13px] mt-0.5 whitespace-pre-wrap break-all" style={{ color: 'var(--text-2)', fontFamily: 'var(--font-mono)' }}>{paramsText}</pre>
        {needsParamsTrunc && (
          <button className="text-xs hover:underline" style={{ color: 'var(--coral)' }} onClick={() => setParamsExpanded(!paramsExpanded)}>{paramsExpanded ? '收起参数' : '展开参数'}</button>
        )}
        {resultContent != null && (
          <div className="rounded-lg px-3 py-2 text-sm mt-2" style={{ backgroundColor: 'var(--bg)', color: 'var(--text-2)' }}>
            <div className="text-xs mb-1" style={{ color: 'var(--text-3)' }}>返回结果</div>
            <pre className="whitespace-pre-wrap break-words" style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8125rem' }}>{resultText}</pre>
            {needsResultTrunc && (
              <button className="text-xs mt-1 hover:underline" style={{ color: 'var(--coral)' }} onClick={() => setResultExpanded(!resultExpanded)}>{resultExpanded ? '收起结果' : '展开结果'}</button>
            )}
          </div>
        )}
        {resultContent != null && (
          <div className="inline-flex items-center gap-1 text-xs mt-1" style={{ color: 'var(--success)' }}><CheckCircle size={13} /> 完成</div>
        )}
      </div>
    </div>
  )
}
