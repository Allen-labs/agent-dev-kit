# 个性化研发流程模板（flow.md）

把"必要的开发项目要求和规范 + 个性化流程管理"变成 Agent 可执行的明文。`flow.md` 是 WorkBuddy 内置 skill 的"调用说明书"——写明本项目走哪几步、谁先谁后、什么不过不合并。

## 推荐结构

```markdown
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
```

## 与内置 skill 的映射（写 flow.md 时直接引用）

| 流程动作 | 调用 WorkBuddy 内置 skill |
|---|---|
| 澄清模糊需求 | `brainstorming` / `idea-refine` |
| 写功能级 Spec | `spec-driven-development` |
| Spec → 实施计划 | `writing-plans` + `planning-and-task-breakdown` |
| 并行隔离执行 | `subagent-driven-development` + `using-git-worktrees` |
| 测试先行 | `tdd` / `test-driven-development` |
| 完成前校验 | `verification-before-completion` |
| 独立评审闸门 | `code-review` / `requesting-code-review` |
| 收口合并 | `finishing-a-development-branch` / `git-workflow-and-versioning` |

## 写 flow.md 的注意

- 不要照搬上面模板的"通用节奏"就交差。真正有价值的是**个性化约定**那一块——把你反复口头叮嘱的、跨会话讲了第二遍的东西，全部 codify 进来。
- 节奏要让 Agent"可判断当前在哪一步、下一步该调哪个 skill"，而不是一段漂亮但无法执行的散文。
- `last_verified` 必须真实：流程变了就改日期并重审，过期规则会被 Agent 忠实执行成错误行为。
