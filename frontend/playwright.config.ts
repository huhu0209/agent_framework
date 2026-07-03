import { readFileSync } from 'fs'
import { resolve, dirname } from 'path'
import { fileURLToPath } from 'url'
import { defineConfig, devices } from '@playwright/test'

const __dirname = dirname(fileURLToPath(import.meta.url))

// 从 frontend/.env 读 API_KEY（须与 backend APP_API_KEY 一致），避免硬编码
function envKey(key: string): string {
  try {
    const m = readFileSync('.env', 'utf-8').match(new RegExp(`^${key}=(.+)$`, 'm'))
    return m ? m[1].trim() : ''
  } catch {
    return ''
  }
}
// 优先用 E2E_API_KEY / .env 中的 VITE_APP_API_KEY；worktree .env 常为空（gitignored），
// 兜底一个固定的 E2E key，确保干净 worktree 也能起 stub backend（前后端共享此值）。
// 注意 ?? 不捕获空串，故显式 || 兜底。
const API_KEY = process.env.E2E_API_KEY || envKey('VITE_APP_API_KEY') || 'e2e-stub-key'
// 解析到本 worktree 的 backend（agents CRUD router 已合入 main，worktree 与主仓库均可）
const BACKEND_DIR = resolve(__dirname, '..', 'backend')
// E2E 创建的 agent 文件隔离到 worktree 内临时目录，避免污染真实 ~/.agent-framework/agents
const AGENTS_DIR = resolve(__dirname, '..', 'backend', 'data', 'e2e-agents')

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false, // 单 backend 实例，串行避免 session 串扰
  retries: 0,
  workers: 1,
  reporter: 'list',
  use: {
    baseURL: 'http://localhost:30001',
    trace: 'on-first-retry',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: [
    {
      // L-5: 用绝对路径调 python + --app-dir,避免 cd(某些 CI/sandbox 下 cd 会触发权限提示)
      command: `APP_API_KEY=${API_KEY} APP_LLM_API_KEY=test APP_WS_TOKEN=devtoken APP_WS_ENABLED=true APP_AGENT_BACKEND=stub APP_AGENTS_DIR=${AGENTS_DIR} ${BACKEND_DIR}/.venv/bin/python -m uvicorn main:app --app-dir ${BACKEND_DIR} --port 30002`,
      port: 30002,
      timeout: 30_000,
      reuseExistingServer: true,
    },
    {
      // 透传 API_KEY 给前端 vite（VITE_APP_API_KEY 需与后端 APP_API_KEY 一致）；
      // worktree .env 为空时由此兜底。
      command: `VITE_APP_API_KEY=${API_KEY} npm run dev`,
      port: 30001,
      timeout: 30_000,
      reuseExistingServer: true,
    },
  ],
})
