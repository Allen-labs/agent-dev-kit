# Codex CLI 适配器（薄层）

canonical 真相源在 Codex CLI 的薄适配层。改动只改 canonical，再重新扇出（幂等）。

- `AGENTS.md`：原生读取（放在仓库根或 canonical 指向）
- skill：`~/.codex/skills/` ← `canonical/skills/`
- MCP：`~/.codex/config.toml` 的 `[mcp_servers.name]` 段（TOML 格式）
- 密钥：`env` 用 `${KEY}` 占位，从 `.env` 注入
- 复原计划：`bootstrap.py --canonical <repo> --tool codex --write`
