# .agents/ 目录结构与职责

来自 `agent-folder-init`（shipshitdev）的脚手架思路，移植到 WorkBuddy 约定。整套结构可随仓库走（项目规范不丢），也可进 canonical 仓库（个人环境可迁移）。

## 目录布局

```
.agents/
├── README.md              # 导航中枢：这里有什么、何时读什么
├── memory/                # 一主题一文件，带 last_verified 日期（可验证、防过期）
│   ├── README.md
│   ├── architecture.md    # 系统分层、模块边界、关键依赖、数据流、设计决策
│   ├── conventions.md     # 命名/目录/ownership（不靠代码推断的约定）
│   ├── deployment.md      # 部署步骤、环境变量、回滚命令、已知坑
│   ├── data-model.md      # 核心实体/表/字段语义、状态机、外键
│   ├── tech-debt.md       # 已知技术债清单（描述+影响+建议修复）
│   └── flow.md            # 个性化研发流程（见 flow-template.md）
└── sessions/              # 一天一文件，记录当天任务/决策/上下文
    ├── README.md
    └── TEMPLATE.md        # 新建会话记录的模板
```

## 每文件职责

| 文件 | 写什么（高信号内容） |
|---|---|
| `README.md` | 整本"说明书"的目录，告诉 Agent 每个子文档何时读、是否当前需要 |
| `architecture.md` | 哪些"为什么这么设计"的决策；模块边界；外部依赖如何接入 |
| `conventions.md` | 命名规范、目录约定、各模块 ownership、import 顺序等无法从代码推断的约定 |
| `deployment.md` | 部署/CI-CD 步骤、必须的环境变量、回滚命令、启动顺序坑 |
| `data-model.md` | 核心实体语义、状态机、外键关系（对应代码注释补不全的部分） |
| `tech-debt.md` | 技术债常态化治理：每条债的描述 + 影响 + 建议修复；定期扫描补充 |
| `flow.md` | 本项目定制研发节奏 + 角色分工 + 个性化约定（Agent 的"调用说明书"） |
| `sessions/YYYY-MM-DD.md` | 当天任务、关键决策、未决问题；跨会话 continuity |

## 约定纪律

- **memory 一主题一文件**，顶部带 `last_verified: YYYY-MM-DD`；过期比没有更危险，定期用审计清单核对。
- **sessions 一天一文件**，别堆成一个巨型日志。
- **任务追踪**用 GitHub Issues / 项目看板，不在本地写任务文件（避免和工具自带系统打架）。
- 根 `AGENTS.md` 只放"地图 + 最高频命令 + 禁区"，细节全部 `@.agents/memory/xxx.md` 引用。

## 与 WorkBuddy 内置 skill 的衔接

`spec-driven-development` 产的是功能级 Spec，`memory/` 是项目级常驻上下文——二者互补：Spec 驱动单次实现，memory 提供跨次背景。Agent 动手前先读 `AGENTS.md` + 相关 memory，再决定要不要开新会话。
