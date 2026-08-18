# 开发流程（本项目定制）
last_verified: YYYY-MM-DD

## 固定节奏
1. 探索：先读 AGENTS.md + 相关 memory，不动手
2. 规划：先写 Spec（目标/验收/约束），再拆任务清单
3. 实现：单任务单分支（worktree 隔离），TDD 先行
4. 验证：lint/test/build 全绿才算完
5. 评审：独立 review 闸门，不过不合并
6. 收口：更新 memory/sessions，再 finishing-branch

## 角色分工（复杂任务）
- Planner：只规划，定规范与验收，不写实现
- Generator：严格按指令实现单子任务，不越权
- Evaluator：与 Generator 物理隔离，独立评估，不达标退回

## 个性化约定（你的特殊要求，逐条列出）
- [如：所有接口必须先出 OpenAPI 再实现]
- [如：数据库变更必须带迁移脚本 + 回滚脚本]
- [如：UI 改动须附截图对比]
- [如：对外 PR 必须过 CI + 至少 1 人 review]
