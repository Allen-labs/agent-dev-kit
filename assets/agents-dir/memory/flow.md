# 研发流程（个性化，对接 WorkBuddy 内置 skill）
last_verified: 2026-08-18

## 固定节奏（6 步，Plan-First）
1. **探索 Explore**：读 `AGENTS.md` + `.agents/memory/*`，理解系统与约定，不动手。
2. **规划 Plan**：用 `spec-driven-development` 产出 Spec（目标 / 验收 / 约束）。
3. **拆解 Tasks**：用 `planning-and-task-breakdown` / `writing-plans` 拆有序、可验收任务。
4. **实现 Implement**：复杂任务用 `subagent-driven-development` + `using-git-worktrees`
   多 agent 并行隔离；单任务单分支；`tdd` 先行（红→绿）。
5. **验证 Verify**：`verification-before-completion` —— lint / 单测 / 构建全绿才算完。
6. **评审 Review + 收口**：`code-review` 独立评审闸门；过审后 `finishing-a-development-branch`
   更新 memory / sessions 再合并。

## 角色分工（复杂任务）
- **Planner**：只规划，定规范与验收，不写实现。
- **Generator**：严格按指令实现单子任务，不越权。
- **Evaluator**：与 Generator 物理隔离，独立评估，不达标退回重做。

## 自动化护栏（由 `hooks/` 实现，详见 `hooks/README.md`）
- 提交前 **密钥泄露扫描**：命中真实密钥即阻断（pre-commit）。
- **危险命令确认**：`rm -rf` / `git push --force` / `DROP` 等需显式确认（pre-tool-use）。
- 任务结束 **记忆自动回写**：把关键决策 / 约定写入 `.agents/memory/`（post-task）。
- 验证闸门：lint / 单测 / 构建未全绿，不得请求 review。

## 个性化约定（按需逐条增删）
- 所有对外接口先出 OpenAPI / 契约，再实现。
- 数据库变更必须带迁移脚本 + 回滚脚本。
- UI 改动须附前后截图对比。
- 生产库操作只读优先；写操作需带回滚且经确认。

## MCP 对流程的支撑（详见 `mcp/README.md`）
- **Context7**：实现时注入实时、版本正确的库文档，减少幻觉 API。
- **Playwright**：验证阶段驱动真实浏览器做 E2E / 截图对比。
- **GitHub**：评审 / 收口阶段直接操作 issue / PR / 分支。
- **Postgres / SQLite**：验证阶段直查数据与 schema。
- **Filesystem / Memory**：跨项目取文件、跨会话取长期记忆。
