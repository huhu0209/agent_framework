# LLM Adapter 参考文档设计

## 概述

基于 `_template.html` 模板，为 LLM Adapter 层生成完整的可视化参考文档。
覆盖源码解读、设计决策、面试准备三个维度。

## 输出

- 单个 HTML 文件：`/Users/huhu/resources/learning_note/7_agent_framework/辅助理解/llm-adapter.html`
- 使用 Claude/Anthropic warm 设计系统
- 三个 Tab：源码解读 / 设计决策 / 实战反思

## 内容规划

### Header

- PHASE: `Phase 2 · LLM Adapter`
- TITLE: `LLM Adapter 层`
- SUBTITLE: `统一接口 · 格式转换 · 弹性调用`

### Tab 1: 源码解读（A-D 四组折叠）

**A. 宏观认知（默认展开）**
1. 解决什么问题 — 三家 API 差异 + 统一接口的价值
2. 在框架中的位置 — Pipeline 图
3. 最小使用示例 — create_adapter() 代码
4. 表面流程 — 3 步流程

**B. 内部解剖**
5. 模块拆解 — 6 子模块 grid
6. 核心 API — 表格
7. 核心类/函数 — method cards
8. 主流程调用链 — 8 步 + state diagram

**C. 深入细节**
9. 核心数据结构 — model cards
10. 生命周期和扩展点 — state diagram
11. 异常处理和边界情况 — 表格 + cards

**D. 阅读指南**
12. 源码阅读顺序 — flow steps
13. 可跳过的细节 — card
14. 新手易误解 — decision items
15. 一句话设计思想 — quote
16. 理解检查问题 — Q&A cards

### Tab 2: 设计决策

- 设计模式：Adapter / Decorator / Strategy / Factory（4 个卡片）
- 亮点解析：ContentBlock Union / DeepSeek 复用 / Anthropic 并行流 / provider_extras
- 决策记录：5 条关键决策及其原因

### Tab 3: 实战反思

- 高频面试题：6 个 Q&A
- 话术模板：30s / 1min / 3min
- 追问预判：4 个方向

## 数据来源

基于 `framework/agent_framework/llm/` 目录下的 15 个源文件：
- types.py, base.py (接口与类型)
- transform/ (4 个文件，格式转换)
- providers/ (3 个文件，Provider 实现)
- streaming.py (SSE 解析与流收集)
- retry.py (重试与 Circuit Breaker)
- resilient.py (弹性包装 + 工厂函数)
