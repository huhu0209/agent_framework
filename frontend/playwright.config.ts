import { readFileSync } from 'fs'
import { defineConfig, devices } from '@playwright/test'

// 从 frontend/.env 读 API_KEY（须与 backend APP_API_KEY 一致），避免硬编码
function envKey(key: string): string {
  try {
    const m = readFileSync('.env', 'utf-8').match(new RegExp(`^${key}=(.+)$`, 'm'))
    return m ? m[1].trim() : ''
  } catch {
    return ''
  }
}
const API_KEY = process.env.E2E_API_KEY ?? envKey('VITE_APP_API_KEY')
const BACKEND_DIR = '/Users/huhu/project/agent_framework/backend'

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
      command: `cd ${BACKEND_DIR} && APP_API_KEY=${API_KEY} APP_LLM_API_KEY=test APP_WS_TOKEN=devtoken APP_WS_ENABLED=true APP_AGENT_BACKEND=stub .venv/bin/python -m uvicorn main:app --port 30002`,
      port: 30002,
      timeout: 30_000,
      reuseExistingServer: true,
    },
    {
      command: 'npm run dev',
      port: 30001,
      timeout: 30_000,
      reuseExistingServer: true,
    },
  ],
})
