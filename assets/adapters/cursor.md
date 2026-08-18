# Cursor 适配器（薄层）

canonical 真相源在 Cursor 的薄适配层。改动只改 canonical，再重新扇出（幂等）。

- 全局规范：`~/.cursor/rules/global.mdc`（`description: always`，`alwaysApply: true`），内容指向 canonical `AGENTS.md`
- 细粒度规则：按目录/文件类型拆 `.mdc`，只对该范围生效
- MCP：`.cursor/mcp.json`（`mcpServers` JSON）
- Cursor 也原生读仓库根 `AGENTS.md`，可零适配
- 复原计划：`bootstrap.py --canonical <repo> --tool cursor --write`
