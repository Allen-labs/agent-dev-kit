# Claude Code 适配器（薄层）

canonical 真相源在 Claude Code 的薄适配层。改动只改 canonical，再重新扇出（幂等）。

- `CLAUDE.md`：写一行 `@AGENTS.md`（指向 canonical），或薄摘要 + 链接
- skill：`~/.claude/skills/` ← `canonical/skills/`
- MCP：`claude mcp add` 命令，或项目 `.mcp.json`（`mcpServers` JSON，同 Cursor）
- 密钥：`claude mcp add --env KEY=value my-server -e npx -a "-y @server/cli"`
- 复原计划：`bootstrap.py --canonical <repo> --tool claude --write`
