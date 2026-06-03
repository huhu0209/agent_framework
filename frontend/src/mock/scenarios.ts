import type { MockScenario } from '../types';

export const scenarios: MockScenario[] = [
  {
    userMessage: '帮我查一下今天的天气',
    events: [
      { kind: 'thinking', text: '用户需要天气信息，我需要调用搜索工具来获取实时天气数据。' },
      { kind: 'tool_call', toolName: 'web_search', params: { query: 'today weather' } },
      { kind: 'tool_result', content: '北京：晴，气温 22°C，湿度 45%，东南风 2级。紫外线指数中等，建议涂防晒霜。' },
      { kind: 'text_response', text: '今天天气晴朗，气温 22°C，湿度适中。东南风 2 级，整体非常舒适。紫外线中等，建议出门涂防晒霜。' },
    ],
    delays: [600, 800, 500, 400],
  },
  {
    userMessage: '对比一下 Claude 和 GPT 的优缺点',
    events: [
      { kind: 'thinking', text: '需要分别搜索两个模型的信息，然后进行对比分析。先搜索 Claude 的特点。' },
      { kind: 'tool_call', toolName: 'web_search', params: { query: 'Claude AI features pros cons 2025' } },
      { kind: 'tool_result', content: 'Claude (Anthropic): 优点 — 长上下文窗口（200K tokens）、安全性强、写作质量高、遵循指令好。缺点 — 知识截止较早、代码能力略逊于 GPT、插件生态较小。' },
      { kind: 'thinking', text: '已获取 Claude 信息，现在搜索 GPT 的特点。' },
      { kind: 'tool_call', toolName: 'web_search', params: { query: 'GPT-4 features pros cons 2025' } },
      { kind: 'tool_result', content: 'GPT-4 (OpenAI): 优点 — 多模态能力强、代码生成优秀、插件生态丰富、知识更新快。缺点 — 上下文窗口较小（128K）、偶尔幻觉、价格较高、安全边界较宽松。' },
      { kind: 'text_response', text: '## Claude vs GPT 对比\n\n**Claude 优势：**\n- 超长上下文窗口（200K tokens）\n- 安全性和对齐方面更严谨\n- 写作和文本质量更自然\n\n**GPT 优势：**\n- 多模态能力（图片、语音）\n- 代码生成更强\n- 生态系统更丰富\n\n**总结：** 如果注重安全和长文本处理，选 Claude；如果需要多模态和插件生态，选 GPT。' },
    ],
    delays: [600, 800, 500, 400, 800, 500, 600],
  },
];

export const defaultScenario: MockScenario = {
  userMessage: '__default__',
  events: [
    { kind: 'thinking', text: '让我想想这个问题...' },
    { kind: 'text_response', text: '你好！我是一个 Agent 助手。目前处于演示模式，可以回答一些预设问题。试试输入"帮我查一下今天的天气"或"对比一下 Claude 和 GPT 的优缺点"。' },
  ],
  delays: [800, 400],
};
