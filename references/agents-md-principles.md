# 写好 AGENTS.md 的 6 条原则 + 审计清单

改编自 HumanLayer(Kyle)《Writing a good CLAUDE.md》，泛化到开放的 `agents.md` 标准（Codex / Cursor / Gemini CLI / Copilot / Zed 等 30+ agent 原生读取）。核心认知：**规则是上下文不是强制开关，质量取决于"只写高信号、不可推断的信息"。**

## 6 条原则

1. **少即是多（Less is more）**
   目标 < 150 行，理想 50–100 行。Agent 上下文窗口有限，越长越稀释关键指令。把细节下沉到 `.agents/memory/` 子文档，主文件只放地图。

2. **只写普适规则（Universal rules only）**
   每条指令必须对"这个仓库里任何任务"都成立。只针对某子任务的指令，放进 memory 子文档或任务 Spec，别污染全局。

3. **渐进披露（Progressive disclosure）**
   主文件用 `@path/to/file` 引用子文档（架构、测试、API 约定分文件）。Agent 按需加载，避免一次塞爆上下文。

4. **别把 linter 当指令（Don't make it a linter）**
   代码风格交给确定性工具（ESLint/Prettier/ruff）。AGENTS.md 写"运行 `pnpm lint`"，不写"用 2 空格缩进、禁止 var"——那是工具的事。

5. **手写而非自动生成（Write, don't generate）**
   永远把自动生成的初稿当草稿重写。Agent 生成的 AGENTS.md 往往是泛泛而谈的样板，必须人工提炼成你项目的真实命令与禁区。

6. **理解 Agent 为何跳过指令**
   Agent 会"判断这条指令是否与当前任务相关"，觉得无关就跳过。所以每条都要"有用且具体"（写真实命令，而非"请测试"）。抽象的哲学式指令最容易被忽略。

## 审计清单（写完用这个自检）

| 检查项 | 问自己 |
|---|---|
| 普适性 | 这条规则对所有任务都成立吗？否则下沉 |
| 长度 | 是否 < 150 行？能不能更短 |
| 越权当 linter | 有没有把代码风格写进去？删掉，交给工具 |
| 过期代码片段 | 有没有会随版本失效的具体命令/API？去掉或加 `last_verified` |
| 指令条数 | 是不是堆了一堆"热补丁"？精简成原则 |
| 像不像自动生成物 | 读起来像样板吗？重写成本项目真实内容 |
| 渐进披露 | 长内容是否拆到子文档？ |
| 漂移风险 | 多工具时是否只维护一份真内容，其余做薄指针？ |

## 跨工具兼容矩阵

单一真相源 = `AGENTS.md`，其余只做薄适配器，避免三份拷贝漂移：

| 工具 | 读的文件 | 适配器做法 |
|---|---|---|
| Codex / Cursor / Gemini / Copilot / Zed | `AGENTS.md` | 原生读取，无需适配 |
| Claude Code | `CLAUDE.md` | 一行 `@AGENTS.md`（指向）或薄摘要 |
| Cursor（细粒度） | `.cursor/rules/*.mdc` | 按文件类型作用域的薄指针 |

> 关键：两份拷贝会漂移，过时规则比没有更危险（Agent 会"忠实"地执行谎言）。
