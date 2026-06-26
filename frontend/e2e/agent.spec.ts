import { test, expect } from '@playwright/test'

// E2E happy path：Agent 管理 → 创建 agent 文件 → Chat 选用 → stub 响应 200。
// agents_dir 由 playwright.config 的 APP_AGENTS_DIR 隔离到 worktree 内临时目录，
// 避免污染真实 ~/.agent-framework/agents。
test.describe('agent 管理', () => {
  test('新建 agent 并在 chat 选用', async ({ page }) => {
    await page.goto('/')

    // 切到 Agent view
    await page.getByRole('button', { name: 'Agent', exact: true }).click()

    // 新建（名字为必填；persona 字段是 div 标签+textarea，无 <label> 关联，此处按定位填）
    await page.getByRole('button', { name: /新建 agent/ }).click()
    await page.getByLabel('名字').fill('e2e-reviewer')
    await page.getByLabel('描述').fill('E2E 审查员')
    await page.getByRole('button', { name: '保存' }).click()

    // 列表出现该 agent
    await expect(page.getByRole('button', { name: /e2e-reviewer/ })).toBeVisible({ timeout: 5_000 })

    // 切到 Chat，选该 agent
    await page.getByRole('button', { name: 'Chat', exact: true }).click()
    await page.getByRole('combobox', { name: /选择 agent/ }).selectOption('e2e-reviewer')

    // 发消息（stub backend 200，固定输出 "stub done"）
    const composer = page.getByPlaceholder('给助手发消息')
    await composer.fill('hello')
    await composer.press('Enter')

    // stub done 出现（stub 固定事件序列末步文本）
    await expect(page.getByText('stub done').first()).toBeVisible({ timeout: 15_000 })
  })
})
