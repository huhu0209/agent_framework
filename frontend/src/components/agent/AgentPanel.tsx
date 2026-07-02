import { useEffect, useRef, useState } from 'react'
import { Check, Plus, Trash, X } from '@phosphor-icons/react'
import { useChatStore } from '../../store'
import type { AgentDetail } from '../../types'

const EMPTY: AgentDetail = {
  name: '', description: '', model: null, skills: null, tools: null,
  permission_mode: 'ask', soul: '', identity: '', agents_rules: '', tool_guidance: '',
}

const PERSONA_FIELDS: { key: keyof AgentDetail; label: string }[] = [
  { key: 'soul', label: '灵魂 (soul)' },
  { key: 'identity', label: '身份 (identity)' },
  { key: 'agents_rules', label: '行为规则 (agents)' },
  { key: 'tool_guidance', label: '工具指引 (tool_guidance)' },
]

export function AgentPanel() {
  const agents = useChatStore((s) => s.agents)
  const skills = useChatStore((s) => s.skills)
  const activeAgentName = useChatStore((s) => s.activeAgentName)
  const loadAgents = useChatStore((s) => s.loadAgents)
  const loadSkills = useChatStore((s) => s.loadSkills)
  const getAgent = useChatStore((s) => s.getAgent)
  const createAgent = useChatStore((s) => s.createAgent)
  const updateAgent = useChatStore((s) => s.updateAgent)
  const deleteAgent = useChatStore((s) => s.deleteAgent)
  const setActiveAgentName = useChatStore((s) => s.setActiveAgentName)

  const [draft, setDraft] = useState<AgentDetail | null>(null)
  const [isNew, setIsNew] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState(false)
  const reqIdRef = useRef(0)

  useEffect(() => {
    loadAgents()
    loadSkills()
  }, [loadAgents, loadSkills])

  useEffect(() => {
    if (!activeAgentName || isNew) return
    // LOW#5: 请求版本号 guard — 快切 agent 时,旧 promise 后 resolve 不覆盖新 draft
    const myId = ++reqIdRef.current
    getAgent(activeAgentName).then((d) => {
      if (myId === reqIdRef.current && d) setDraft(d)
    })
  }, [activeAgentName, isNew, getAgent])

  function startNew() {
    setIsNew(true)
    setActiveAgentName(null)
    setDraft({ ...EMPTY })
    setConfirmDelete(false)
  }

  function selectAgent(name: string) {
    setIsNew(false)
    setActiveAgentName(name)
    setConfirmDelete(false)
  }

  async function save() {
    if (!draft || !draft.name.trim()) return
    if (isNew) {
      await createAgent(draft)
      setIsNew(false)
      setActiveAgentName(draft.name)
    } else if (activeAgentName) {
      await updateAgent(activeAgentName, draft)
    }
  }

  function toggleSkill(name: string) {
    if (!draft) return
    const cur = draft.skills ?? []
    const next = cur.includes(name) ? cur.filter((n) => n !== name) : [...cur, name]
    setDraft({ ...draft, skills: next })
  }

  return (
    <div className="flex h-full">
      <aside className="flex flex-col h-full overflow-hidden" style={{ width: 260, minWidth: 260, borderRight: '1px solid var(--border)' }}>
        <div className="flex items-center gap-2 p-3" style={{ borderBottom: '1px solid var(--border)' }}>
          <button onClick={startNew} className="flex-1 flex items-center justify-center gap-1 px-3 py-1.5 rounded-md text-[13px]"
            style={{ border: '1px solid var(--border)', color: 'var(--text-2)' }}>
            <Plus size={16} style={{ color: 'var(--brand)' }} /> 新建 agent
          </button>
        </div>
        <nav className="flex-1 overflow-y-auto p-2">
          {agents.length === 0 && <div className="text-xs px-2 py-4" style={{ color: 'var(--text-3)' }}>暂无 agent</div>}
          {agents.map((a) => (
            <button key={a.name} onClick={() => selectAgent(a.name)}
              className="w-full text-left px-3 py-2 rounded-md text-[13px]"
              style={{
                backgroundColor: a.name === activeAgentName ? 'var(--sand)' : 'transparent',
                color: a.name === activeAgentName ? 'var(--text)' : 'var(--text-3)',
              }}>
              <div className="font-medium">{a.name}</div>
              {a.description && <div className="text-[11px] truncate" style={{ color: 'var(--text-3)' }}>{a.description}</div>}
            </button>
          ))}
        </nav>
      </aside>

      <div className="flex-1 overflow-y-auto p-5">
        {!draft ? (
          <div className="flex h-full items-center justify-center text-sm" style={{ color: 'var(--text-3)' }}>
            选择左侧 agent 或点「新建 agent」
          </div>
        ) : (
          <div className="flex flex-col gap-4 max-w-2xl">
            <h2 className="text-base font-semibold" style={{ color: 'var(--text)' }}>
              {isNew ? '新建 agent' : `编辑 ${activeAgentName}`}
            </h2>

            <LabeledInput label="名字" value={draft.name} disabled={!isNew}
              onChange={(v) => setDraft({ ...draft, name: v })} placeholder="code-reviewer" />
            <LabeledInput label="描述" value={draft.description}
              onChange={(v) => setDraft({ ...draft, description: v })} placeholder="一句话介绍" />
            <LabeledInput label="模型(留空=默认)" value={draft.model ?? ''}
              onChange={(v) => setDraft({ ...draft, model: v || null })} placeholder="claude-sonnet-4-6" />

            <div>
              <div className="text-[12px] mb-1" style={{ color: 'var(--text-3)' }}>技能</div>
              <div className="flex flex-wrap gap-2">
                {skills.length === 0 && <span className="text-[12px]" style={{ color: 'var(--text-3)' }}>无可用 skill</span>}
                {skills.map((s) => {
                  const on = (draft.skills ?? []).includes(s.name)
                  return (
                    <button key={s.name} type="button" onClick={() => toggleSkill(s.name)}
                      className="px-2 py-1 rounded-md text-[12px]"
                      style={{
                        border: '1px solid var(--border)',
                        backgroundColor: on ? 'var(--brand)' : 'transparent',
                        color: on ? '#fff' : 'var(--text-2)',
                      }}
                      title={s.description}>
                      {s.name}
                    </button>
                  )
                })}
              </div>
            </div>

            {PERSONA_FIELDS.map(({ key, label }) => (
              <div key={key}>
                <div className="text-[12px] mb-1" style={{ color: 'var(--text-3)' }}>{label}</div>
                <textarea rows={4} value={String(draft[key] ?? '')}
                  onChange={(e) => setDraft({ ...draft, [key]: e.target.value })}
                  className="w-full p-2 rounded-md text-[13px] font-mono"
                  style={{ border: '1px solid var(--border)', color: 'var(--text)', backgroundColor: 'var(--surface)' }} />
              </div>
            ))}

            <div className="flex items-center gap-2">
              <button onClick={save} className="px-4 py-1.5 rounded-md text-[13px] font-medium"
                style={{ backgroundColor: 'var(--brand)', color: '#fff' }}>保存</button>
              {!isNew && activeAgentName && (
                confirmDelete ? (
                  <div className="flex items-center gap-1 text-[13px]">
                    <span style={{ color: 'var(--text-3)' }}>确认?</span>
                    <button onClick={() => { deleteAgent(activeAgentName); setDraft(null); setConfirmDelete(false) }}
                      className="flex items-center gap-1 px-3 py-1.5 rounded-md"
                      style={{ border: '1px solid var(--border)', color: 'var(--danger)' }}
                      aria-label="确认删除">
                      <Check size={16} /> 删除
                    </button>
                    <button onClick={() => setConfirmDelete(false)}
                      className="flex items-center gap-1 px-3 py-1.5 rounded-md"
                      style={{ border: '1px solid var(--border)', color: 'var(--text-2)' }}
                      aria-label="取消删除">
                      <X size={16} /> 取消
                    </button>
                  </div>
                ) : (
                  <button onClick={() => setConfirmDelete(true)}
                    className="flex items-center gap-1 px-3 py-1.5 rounded-md text-[13px]"
                    style={{ border: '1px solid var(--border)', color: 'var(--danger)' }}>
                    <Trash size={16} /> 删除
                  </button>
                )
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

function LabeledInput({ label, value, onChange, placeholder, disabled }: {
  label: string; value: string; onChange: (v: string) => void; placeholder?: string; disabled?: boolean
}) {
  const id = label.replace(/\s+/g, '-')
  return (
    <div>
      <label htmlFor={id} className="block text-[12px] mb-1" style={{ color: 'var(--text-3)' }}>{label}</label>
      <input id={id} value={value} disabled={disabled} placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)}
        className="w-full px-2 py-1.5 rounded-md text-[13px]"
        style={{ border: '1px solid var(--border)', color: 'var(--text)', backgroundColor: 'var(--surface)' }} />
    </div>
  )
}
