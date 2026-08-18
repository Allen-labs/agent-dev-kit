# MCP 最佳集合（canonical）

> 由 `agent-dev-kit` 维护，跨工具通过 `bootstrap.py` 扇出。
> **密钥一律占位（`${...}`），绝不写死；真实值从本地 `.env` / 密钥管理器注入。**

## 选型原则（2026 共识）
- **数量封顶 5–7 个**：每个 server 都会把工具 schema 注入会话上下文，过多会让 agent 变慢、选错工具。
- **按需启用**：日常保留 3–5 个；数据库 / 浏览器按任务临时加。
- **只读优先**：数据库用只读账号 / 读副本；绝不给生产写权限。
- **vendor 维护优先**：生产相关只用官方 / 厂商维护的 server，社区 server 先审权限。
- **警惕项目级 MCP 投毒**：克隆仓库后先审 `.mcp.json` / `mcp_settings.json` 再运行。

## 推荐常开（3 个，覆盖大多数价值）
| server | 用途 | 依赖 |
|---|---|---|
| `context7` | 实时、版本正确的库文档，杜绝幻觉 API | 无（免费档免 key） |
| `github` | issue / PR / 分支流转，评审收口自动化 | `GITHUB_PERSONAL_ACCESS_TOKEN` |
| `playwright` | 真实浏览器驱动，E2E / 截图对比 | 本地，无 key |

## 按任务补充
| server | 用途 | 依赖 |
|---|---|---|
| `filesystem` | 跨项目访问指定目录（默认文件工具已够用时可省） | `ALLOWED_DIR`（绝对路径，见下） |
| `memory` | 跨会话知识图谱记忆 | 无 |
| `postgres` | 直查 Postgres schema / 数据（只读账号） | `DATABASE_URI`（读副本连接串） |
| `sqlite` | 查本地 SQLite 文件 | `SQLITE_DB`（db 文件路径） |

## 各 server 安装 / 接线要点
- **context7**：`npx -y @upstash/context7-mcp`；可选远程端点 `https://mcp.context7.com/mcp`（需免费 API key 提限额）。
- **github**：官方 `ghcr.io/github/github-mcp-server`（Docker stdio，便于跨工具平移）。
  令牌用 **fine-grained PAT，最小权限（repo + read-only 起步）**。也可用托管端点 `https://api.githubcopilot.com/mcp`（OAuth，但 bootstrap 的 TOML 翻译只处理 stdio，故 canonical 用 docker 形式）。
- **playwright**：`npx -y @playwright/mcp@latest`；首次会自动装浏览器。
- **filesystem**：`-y @modelcontextprotocol/server-filesystem <绝对路径>`。
  ⚠ 允许目录是**位置参数**，多数 MCP 客户端**不会展开 args 里的 `${ALLOWED_DIR}`**——
  扇出后请把 `${ALLOWED_DIR}` 直接替换为你的工作区绝对路径（如 `C:/Users/liuaj/code`）。
- **postgres**：`@modelcontextprotocol/server-postgres <连接串>`（参考实现已归档但仍可用；
  若需 EXPLAIN 分析 / 索引调优 / 受限模式，改用 `crystaldba/postgres-mcp`）。**务必只读账号。**
- **sqlite**：`@modelcontextprotocol/server-sqlite --db-path <文件>`。

## 安全清单（扇出前自查）
- [ ] 所有 `${...}` 已替换为真实值（从 `.env` 注入，不提交）。
- [ ] 数据库用只读账号 / 读副本。
- [ ] GitHub token 最小权限，且可随时吊销。
- [ ] `doctor.py` 泄密扫描通过（仓库内无真实密钥）。
