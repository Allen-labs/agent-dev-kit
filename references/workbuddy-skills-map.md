# WorkBuddy 内置 skill 映射（flow.md 调用说明书）

本套件不重复造轮子：`flow.md` 的每一步直接调用 WorkBuddy 已内置的成熟 skill。下面按"开发固定节奏"列出映射，写 flow.md 时直接引用。

## 四层框架 ↔ 内置 skill

| 框架层 | 对应内置 skill | 它解决什么 |
|---|---|---|
| 规范与 Spec 沉淀 | `spec-driven-development`、`context-engineering` | 先写 spec 再写码；优化 Agent 上下文/会话加载 |
| 上下文工程 | `context-engineering`、`doc-coauthoring` | 渐进式披露、会话边界、稳定上下文供给 |
| 流程编排（Plan-First） | `brainstorming` / `idea-refine`、`writing-plans`、`planning-and-task-breakdown`、`subagent-driven-development`、`incremental-implementation`、`using-git-worktrees` | 探索→规划→实现→验证固定节奏 + 并行化 |
| 自动化护栏 | `tdd` / `test-driven-development`、`verification-before-completion`、`code-review` / `requesting-code-review` / `receiving-code-review`、`git-workflow-and-versioning`、`finishing-a-development-branch` | Lint/单测/编译阻断、独立评审、回滚、PR 闸门 |

## 标准组合（非平凡功能落地时这么走；小型变更走快路径，见 flow.md）

1. `brainstorming` / `idea-refine` —— 先把模糊需求问清楚
2. `writing-plans` —— 产出结构化 spec / plan（单一真相源）
3. `writing-plans` + `executing-plans` —— plan 转可验收实施计划与任务清单
4. `subagent-driven-development`（配合 `using-git-worktrees`）—— 并行隔离执行
5. `test-driven-development` + `verification-before-completion` —— 测试先行、完成前强制校验
6. `requesting-code-review` / `receiving-code-review` —— 独立评审闸门，再 `finishing-a-development-branch` 收口

> 注：`spec-driven-development` / `planning-and-task-breakdown` / `tdd` 是更专的同类 skill，
> 但本套配置未启用（在 `disabled/`），上面统一改用已启用的等价 skill，避免流程指向失效技能。

## 缺口与本套件的补位

现有内置 skill 里**没有专门"一键生成项目宪法 AGENTS.md"的 skill**——`spec-driven-development` 产的是功能级 spec，不是项目级常驻指令文件。这正是 `agent-dev-kit` 的 ① Constitution 模块补的位：用 `agents-md-principles.md` 的方法论 + `scaffold.py` 的脚手架，生成 AGENTS.md + .agents/。

## 用法提示

- 这些是"被本套件编排"的能力，用户不需要手动一个个点；flow.md 写明本项目用哪几步即可。
- 角色化（Planner/Generator/Evaluator）可用 `subagent-driven-development` 实现并行隔离，Evaluator 必须与 Generator 物理/逻辑隔离，杜绝自评自审放水。
