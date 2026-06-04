import type { AgentBlock } from '../types'
import { scenarios, defaultScenario } from './scenarios'

let _blockId = 0
function blockId(): string {
  return `blk-${++_blockId}`
}

export function resetBlockIdCounter() {
  _blockId = 0
}

function matchScenario(userMessage: string) {
  for (const s of scenarios) {
    if (userMessage.includes(s.userMessage)) {
      return s
    }
  }
  return { ...defaultScenario, userMessage }
}

export async function* streamMockResponse(userMessage: string): AsyncGenerator<AgentBlock> {
  const scenario = matchScenario(userMessage)

  for (let i = 0; i < scenario.events.length; i++) {
    const delay = scenario.delays[i] ?? 300
    await new Promise((resolve) => setTimeout(resolve, delay))
    yield { ...scenario.events[i], id: blockId() } as AgentBlock
  }
}
