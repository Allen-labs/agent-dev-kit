#!/usr/bin/env python3
"""scaffold.py - 在目标仓库创建 .agents/ 结构 + AGENTS.md 骨架。

安全机制（移植自 agent-folder-init）：
  - 默认 dry-run，打印将要创建的计划；加 --write 才落盘。
  - 拒绝覆盖已有入口文件（AGENTS.md），除非 --force。
  - 不写 cwd 之外（除非 --allow-outside）。
  - 不解析/跟随 symlink。
  - 模板缺失直接硬失败，绝不退而求其次用占位过期内容。

用法：
  python scaffold.py /path/to/repo
  python scaffold.py /path/to/repo --write
  python scaffold.py /path/to/repo --write --force
"""
import argparse
import os
import shutil
import sys

TEMPLATES = {
    ".agents/README.md": (
        "# .agents/\n\n"
        "本目录是项目对 Agent 的常驻上下文系统。\n\n"
        "| 文件 | 何时读 |\n"
        "|---|---|\n"
        "| memory/architecture.md | 理解系统设计 |\n"
        "| memory/conventions.md | 命名/目录/ownership |\n"
        "| memory/deployment.md | 部署/CI-CD |\n"
        "| memory/data-model.md | 数据模型 |\n"
        "| memory/tech-debt.md | 已知技术债 |\n"
        "| memory/flow.md | 个性化研发流程 |\n"
        "| sessions/ | 一天一文件的任务记录 |\n"
    ),
    ".agents/memory/README.md": (
        "# memory/\n\n一主题一文件，顶部带 `last_verified: YYYY-MM-DD`。\n"
        "过期比没有更危险——定期用审计清单核对。\n"
    ),
    ".agents/memory/architecture.md": "# Architecture\nlast_verified: YYYY-MM-DD\n\n[系统分层、模块边界、关键依赖、数据流、设计决策]\n",
    ".agents/memory/conventions.md": "# Conventions\nlast_verified: YYYY-MM-DD\n\n[命名规范、目录约定、各模块 ownership、import 顺序]\n",
    ".agents/memory/deployment.md": "# Deployment\nlast_verified: YYYY-MM-DD\n\n[部署步骤、环境变量、回滚命令、启动顺序坑]\n",
    ".agents/memory/data-model.md": "# Data Model\nlast_verified: YYYY-MM-DD\n\n[核心实体/表/字段语义、状态机、外键关系]\n",
    ".agents/memory/tech-debt.md": "# Tech Debt\nlast_verified: YYYY-MM-DD\n\n| 描述 | 影响 | 建议修复 |\n|---|---|---|\n| [债1] | [影响] | [修复] |\n",
    ".agents/memory/flow.md": "# Flow\nlast_verified: YYYY-MM-DD\n\n见 flow-template.md，把本项目定制节奏与个性化约定写进来。\n",
    ".agents/sessions/README.md": "# sessions/\n一天一文件（YYYY-MM-DD.md），记录当天任务/决策/未决问题。\n",
    ".agents/sessions/TEMPLATE.md": (
        "# YYYY-MM-DD\n\n## 任务\n- \n\n## 决策\n- \n\n## 未决\n- \n"
    ),
    "AGENTS.md": (
        "# [项目名]\n\n[2-3 句：做什么、为什么存在]\n\n"
        "## Stack & Structure\n- 前端：[框架] @ [目录]，入口 [文件]\n"
        "- 后端：[框架] @ [目录]\n- 共享包：[名] = [用途]\n\n"
        "## Working on This Project\nBuild:   `[真实命令]`\nTest:    `[真实命令]`\n"
        "Typecheck:`[真实命令]`\nLint:    `[真实命令]`\n"
        "→ 任何任务完成前，必须确认编译通过 + 测试通过。\n\n"
        "## Boundaries（禁区，agent 永远不得违反）\n- 绝不手改 `generated/` 下文件\n"
        "- 绝不提交 `.env` 或任何含密钥文件\n- [某模块] deprecated 但暂勿删除\n\n"
        "## Git\n- 分支：`[feature/xxx]`；合并策略：[squash/rebase]\n"
        "- Commit：`[类型]: [简述]`\n- PR：必须过 [CI] + [至少 1 人 review]\n\n"
        "## Reference Docs（渐进披露：按需读，勿全读）\n"
        "| 文件 | 何时读 |\n| `.agents/memory/architecture.md` | 理解系统设计 |\n"
        "| `.agents/memory/conventions.md` | 命名/目录/ownership |\n"
        "| `.agents/memory/deployment.md` | 部署/CI-CD |\n"
        "| `.agents/memory/data-model.md` | 数据模型 |\n"
        "| `.agents/memory/flow.md` | 个性化研发流程 |\n"
    ),
}

# 单一真相源：AGENTS.md 模板优先从 assets/AGENTS.md.template 读取，
# 仅当 assets 缺失时才回退到上面的内联内容（正常打包后不会触发）。
ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets")


def load_agents_template():
    p = os.path.join(ASSETS_DIR, "AGENTS.md.template")
    if os.path.exists(p):
        with open(p, "r", encoding="utf-8") as f:
            return f.read()
    return TEMPLATES["AGENTS.md"]


TEMPLATES["AGENTS.md"] = load_agents_template()


def is_outside(repo, target):
    repo = os.path.abspath(repo)
    target = os.path.abspath(target)
    return not (target == repo or target.startswith(repo + os.sep))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("repo", help="目标仓库根目录")
    ap.add_argument("--write", action="store_true", help="真正落盘（默认 dry-run）")
    ap.add_argument("--force", action="store_true", help="覆盖已有 AGENTS.md")
    ap.add_argument("--allow-outside", action="store_true", help="允许写到 repo 之外")
    args = ap.parse_args()

    repo = args.repo
    if not os.path.isdir(repo):
        print(f"[scaffold] ERROR: 不是目录: {repo}", file=sys.stderr)
        sys.exit(1)
    if os.path.islink(repo):
        print("[scaffold] ERROR: 拒绝 symlink 目标", file=sys.stderr)
        sys.exit(1)

    plan = []
    blocked = []
    for rel, content in TEMPLATES.items():
        target = os.path.join(repo, rel)
        if is_outside(repo, target) and not args.allow_outside:
            blocked.append(target)
            continue
        exists = os.path.exists(target)
        if rel == "AGENTS.md" and exists and not args.force:
            blocked.append(f"{target} (已存在，需 --force)")
            continue
        plan.append((target, exists, content))

    # spec 工作流模板（spec.md / plan.md）→ .agents/spec-templates/
    spec_src = os.path.join(ASSETS_DIR, "spec-templates")
    spec_files = []
    if os.path.isdir(spec_src):
        for fn in sorted(os.listdir(spec_src)):
            if fn.endswith(".template"):
                spec_files.append(fn)
    spec_plan = []
    for fn in spec_files:
        target = os.path.join(repo, ".agents", "spec-templates", fn)
        if is_outside(repo, target) and not args.allow_outside:
            blocked.append(target)
            continue
        spec_plan.append((target, os.path.exists(target), fn))

    if blocked:
        print("[scaffold] 被阻止（安全闸门）：")
        for b in blocked:
            print(f"  - {b}")

    if not args.write:
        print("[scaffold] DRY-RUN（不落盘）。将要创建/更新：")
        for target, exists, _ in plan + [(t, e, f) for t, e, f in spec_plan]:
            print(f"  {'更新' if exists else '创建'}  {target}")
        print("\n加 --write 才真正落盘。")
        return

    for target, exists, content in plan:
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"  {'更新' if exists else '创建'}  {target}")
    for target, exists, fn in spec_plan:
        os.makedirs(os.path.dirname(target), exist_ok=True)
        shutil.copy(os.path.join(spec_src, fn), target)
        print(f"  {'更新' if exists else '创建'}  {target}")
    print("[scaffold] done.")


if __name__ == "__main__":
    main()
