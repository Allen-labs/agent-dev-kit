# Zed 适配器

Zed 的 MCP 配置在 `~/.config/zed/settings.json`（全局）或 `.zed/settings.json`（项目）。
注意 Zed 用 **`context_servers`** 键（不是 `mcpServers`）。

## 适配要点
- **MCP**：放在 `"context_servers"` 键下，本地 server 格式为：
  ```json
  {
    "context_servers": {
      "context7": {
        "command": "npx",
        "args": ["-y", "@upstash/context7-mcp"],
        "env": { "KEY": "${KEY}" }
      }
    }
  }
  ```
  - 注意 `command` 是**字符串**，`args` 是数组，`env` 与环境变量键值。
  - `bootstrap.py` 已按此格式翻译并**合并**进已有 `settings.json`
    （不会清空你其他的 Zed 设置）。
- **Skills**：Zed 无 skills 文件夹；用 `/context` 自定义上下文文件替代。
  把 `AGENTS.md` 放到 `~/.config/zed/AGENTS.md` 并在 Agent 面板引用。
- **Hooks**：Zed 通过 `settings.json` 的 `features` / agent 配置间接支持命令；
  本套 `hooks/*.py` 需以 shell 命令方式自行接线（参考 `hooks/README.md`）。
- **密钥**：`env` 的值用 `${VAR}` 占位，从本地 `.env`/shell 注入。
