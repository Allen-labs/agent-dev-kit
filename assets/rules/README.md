# rules/ — 作用域规则资产（极简）

**设计原则：不预置规则库。** 业界验证（The Prompt Shelf 138 仓库研究 / Anthropic 指南）：通用规则价值低，规则必须项目特定才有用。所以这里只放**结构约定 + 写法示例**，规则内容由项目在 AGENTS.md 或本项目录里自己写。

## 用法

1. 项目级规则优先写进 `AGENTS.md`（五段式，<150 行）——这是跨工具真相源。
2. 只有"按文件类型/目录作用域"的规则才拆到这里（避免全局规则稀释）。
3. 每个规则一个文件，frontmatter 声明 glob 作用域。

## 写法示例（frontmatter 声明作用域，厂商中立）

```markdown
---
name: frontend
description: React/TS 组件约定，仅对前端文件生效
scope: "**/*.{ts,tsx}"
---

- 函数组件优先，类组件仅用于错误边界
- 组件 props 用类型别名，不用内联对象
```

## 分发映射（apply 时翻译）

| 这里的规则 | 分发到 |
|---|---|
| `scope` 字段 | Cursor `.cursor/rules/*.mdc` 的 `globs` / Copilot `.github/instructions/*.instructions.md` 的 `applyTo` |
| 全局规则 | AGENTS.md 段 / Cursor `global.mdc`（alwaysApply: true） |

> 通用安全护栏（密钥扫描等）由 `hooks/` 管，不写在这里。
