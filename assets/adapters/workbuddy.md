# WorkBuddy 适配器（薄层）

本文件是 canonical 真相源在 WorkBuddy 的薄适配层。改动只改 canonical，再重新扇出（幂等）。

- 项目规范：仓库根 `AGENTS.md`（WorkBuddy 原生读取项目级指令）
- 个人 skill：`~/.workbuddy/skills/` ← `canonical/skills/`
- MCP：`~/.workbuddy/mcp.json` ← `canonical/mcp/mcp.servers.json`（格式一致，无需翻译）
- 密钥：从本地 `.env` 注入，`env` 字段引用变量名，绝不写死
- 复原计划：`bootstrap.py --canonical <repo> --tool workbuddy --write`
