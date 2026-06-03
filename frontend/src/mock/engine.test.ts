import { describe, it, expect } from 'vitest'
import { streamMockResponse } from './engine'

async function collectBlocks(userMessage: string) {
  const blocks = []
  for await (const block of streamMockResponse(userMessage)) {
    blocks.push(block)
  }
  return blocks
}

describe('streamMockResponse', () => {
  it('returns weather scenario for weather query', async () => {
    const blocks = await collectBlocks('帮我查一下今天的天气')
    expect(blocks).toHaveLength(4)
    expect(blocks[0]).toEqual({ kind: 'thinking', text: expect.any(String) })
    expect(blocks[1]).toEqual({ kind: 'tool_call', toolName: 'web_search', params: expect.any(Object) })
    expect(blocks[2]).toEqual({ kind: 'tool_result', content: expect.any(String) })
    expect(blocks[3]).toEqual({ kind: 'text_response', text: expect.any(String) })
  })

  it('returns multi-step scenario for comparison query', async () => {
    const blocks = await collectBlocks('对比一下 Claude 和 GPT 的优缺点')
    expect(blocks).toHaveLength(7)
    expect(blocks[0].kind).toBe('thinking')
    expect(blocks[1].kind).toBe('tool_call')
    expect(blocks[3].kind).toBe('thinking')
    expect(blocks[6].kind).toBe('text_response')
  })

  it('returns default response for unknown messages', async () => {
    const blocks = await collectBlocks('随便说点什么')
    expect(blocks).toHaveLength(2)
    expect(blocks[0].kind).toBe('thinking')
    expect(blocks[1].kind).toBe('text_response')
  })
})
