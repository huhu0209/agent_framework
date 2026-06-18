import { test, expect } from '@playwright/test'

test('观测面板: 启动拉 config + 打开见 config + 工具链增长', async ({ page }) => {
  await page.goto('/')

  // 发消息触发 agent（stub factory 产生固定工具序列）
  const composer = page.getByPlaceholder('给助手发消息')
  await composer.fill('e2e hello')
  await composer.press('Enter')

  // ModelChip 启动即拉 config（发消息后 sessionId 落定，WS 拉 config）
  const modelChip = page.getByRole('button', { name: '当前模型' })
  await expect.poll(async () => await modelChip.textContent(), {
    timeout: 20_000,
  }).toContain('stub-model')

  // 打开观测面板
  await page.getByRole('button', { name: '观测面板' }).click()

  // 连接状态徽章：已连接
  await expect(page.getByText('已连接', { exact: true })).toBeVisible({ timeout: 10_000 })

  // 工具调用链：stub 产生 search 工具调用（step 号 #1）
  await expect(page.getByText('#1').first()).toBeVisible({ timeout: 10_000 })
})
