#!/usr/bin/env python3
"""bootstrap.py - 把 canonical 仓库扇出到目标工具目录。

把唯一真相源（canonical）的配置复制/symlink 到目标工具的目录，并把
MCP 定义翻译成目标格式。默认 dry-run，加 --write 才落盘。

用法：
  python bootstrap.py --canonical /path/to/canonical --tool workbuddy
  python bootstrap.py --canonical /path/to/canonical --tool workbuddy --write
  python bootstrap.py --canonical /path/to/canonical --tool claude --write
"""
import argparse
import json
import os
import shutil
import sys

HOME = os.path.expanduser("~")
TOOL_DIRS = {
    "workbuddy": os.path.join(HOME, ".workbuddy"),
    "claude": os.path.join(HOME, ".claude"),
    "cursor": os.path.join(HOME, ".cursor"),
    "codex": os.path.join(HOME, ".codex"),
    "opencode": os.path.join(HOME, ".config", "opencode"),
    "zed": os.path.join(HOME, ".config", "zed"),
}


def load_canonical_mcp(canonical):
    p = os.path.join(canonical, "mcp", "mcp.servers.json")
    if not os.path.exists(p):
        return None
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def translate_mcp(servers, tool):
    """把工具无关的标准定义翻译成目标格式。密钥用 env 占位，不写死。"""
    if tool in ("workbuddy", "claude", "cursor"):
        return {"mcpServers": servers}
    if tool == "codex":
        out = {}
        for name, sdef in servers.items():
            out[name] = {
                "command": sdef.get("command"),
                "args": sdef.get("args", []),
                "env": {k: f"${{{k}}}" for k in sdef.get("env", {}).keys()},
            }
        return out
    if tool == "opencode":
        # OpenCode: command 是数组（npx+参数合并），env 键叫 environment
        out = {}
        for name, sdef in servers.items():
            cmd = [sdef.get("command")] + list(sdef.get("args", []))
            out[name] = {
                "type": "local",
                "command": cmd,
                "enabled": True,
                "environment": {k: f"${{{k}}}" for k in sdef.get("env", {}).keys()},
            }
        return out
    if tool == "zed":
        # Zed: command 是字符串，键叫 context_servers
        out = {}
        for name, sdef in servers.items():
            out[name] = {
                "command": sdef.get("command"),
                "args": sdef.get("args", []),
                "env": {k: f"${{{k}}}" for k in sdef.get("env", {}).keys()},
            }
        return out
    return {"mcpServers": servers}


def _write_file(dst, content, args):
    """写入文件：存在且非 --force 则跳过；否则先备份再写。"""
    if os.path.exists(dst) and not args.force:
        print(f"  skip (exists, --force to overwrite): {dst}")
        return
    if os.path.exists(dst):
        bak = dst + ".bak." + str(int(os.path.getmtime(dst)))
        shutil.copy(dst, bak)
        print(f"  backup -> {bak}")
    with open(dst, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  wrote -> {dst}")


def _merge_json(dst, key, obj, args):
    """把 obj 合并进已有 JSON 的 key 下（保留其他键），写入前备份。"""
    existing = {}
    if os.path.exists(dst):
        if not args.force:
            print(f"  skip merge (exists, --force to merge): {dst}")
            return
        try:
            with open(dst, encoding="utf-8") as f:
                existing = json.load(f)
        except Exception:
            existing = {}
    existing[key] = obj
    content = json.dumps(existing, indent=2, ensure_ascii=False)
    _write_file(dst, content, args)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--canonical", required=True, help="canonical 仓库路径")
    ap.add_argument("--tool", required=True, choices=list(TOOL_DIRS.keys()))
    ap.add_argument("--write", action="store_true", help="真正落盘（默认 dry-run）")
    ap.add_argument("--force", action="store_true", help="覆盖目标已有文件")
    args = ap.parse_args()

    if not os.path.isdir(args.canonical):
        print(f"[bootstrap] ERROR: canonical 不存在: {args.canonical}", file=sys.stderr)
        sys.exit(1)

    tool_dir = TOOL_DIRS[args.tool]
    plan = []

    # skills
    src_skills = os.path.join(args.canonical, "skills")
    if os.path.isdir(src_skills):
        dst_skills = os.path.join(tool_dir, "skills")
        plan.append((f"skills/ -> {dst_skills}", "dir"))

    # mcp（计划阶段确定目标文件与格式）
    servers = load_canonical_mcp(args.canonical)
    mcp_dst = None
    if servers is not None:
        if args.tool == "codex":
            mcp_dst = os.path.join(tool_dir, "config.toml")
            mcp_label = "TOML"
        elif args.tool == "opencode":
            mcp_dst = os.path.join(tool_dir, "opencode.json")
            mcp_label = "JSON(merge 'mcp')"
        elif args.tool == "zed":
            mcp_dst = os.path.join(tool_dir, "settings.json")
            mcp_label = "JSON(merge 'context_servers')"
        else:
            mcp_dst = os.path.join(tool_dir, "mcp.json")
            mcp_label = "JSON"
        plan.append((f"mcp -> {mcp_dst} ({mcp_label})", "file"))

    # AGENTS.md / CLAUDE.md 薄适配器
    if args.tool == "claude":
        plan.append((f"CLAUDE.md -> 指向 canonical AGENTS.md", "file"))

    # hooks（若存在）
    if os.path.isdir(os.path.join(args.canonical, "hooks")):
        plan.append((f"hooks/ -> {os.path.join(tool_dir, 'hooks')}", "dir"))

    print(f"[bootstrap] 目标工具: {args.tool}  ({tool_dir})")
    if not args.write:
        print("[bootstrap] DRY-RUN（不落盘）。计划：")
        for desc, kind in plan:
            print(f"  - {desc}")
        print("\n加 --write 才真正落盘。")
        return

    os.makedirs(tool_dir, exist_ok=True)

    # skills
    if os.path.isdir(src_skills):
        dst_skills = os.path.join(tool_dir, "skills")
        os.makedirs(dst_skills, exist_ok=True)
        for name in os.listdir(src_skills):
            s = os.path.join(src_skills, name)
            d = os.path.join(dst_skills, name)
            if os.path.exists(d) and not args.force:
                print(f"  skip (exists): {d}")
                continue
            if os.path.isdir(s):
                if os.path.exists(d):
                    shutil.rmtree(d)
                shutil.copytree(s, d)
            print(f"  skills -> {d}")

    # mcp
    if servers is not None:
        translated = translate_mcp(servers, args.tool)
        if args.tool == "codex":
            dst_mcp = os.path.join(tool_dir, "config.toml")
            lines = ["[mcp_servers]"]
            for name, sdef in translated.items():
                lines.append(f"[mcp_servers.{name}]")
                lines.append(f'command = "{sdef.get("command")}"')
                args_str = ", ".join(f'"{a}"' for a in sdef.get("args", []))
                lines.append(f"args = [{args_str}]")
                if sdef.get("env"):
                    env_str = ", ".join(f'{k} = "{v}"' for k, v in sdef["env"].items())
                    lines.append(f"env = {{ {env_str} }}")
            content = "\n".join(lines) + "\n"
            _write_file(dst_mcp, content, args)
        elif args.tool == "opencode":
            _merge_json(os.path.join(tool_dir, "opencode.json"), "mcp", translated, args)
        elif args.tool == "zed":
            _merge_json(os.path.join(tool_dir, "settings.json"), "context_servers", translated, args)
        else:
            content = json.dumps(translated, indent=2, ensure_ascii=False)
            _write_file(os.path.join(tool_dir, "mcp.json"), content, args)

    # adapters（若存在）
    src_ad = os.path.join(args.canonical, "adapters")
    if os.path.isdir(src_ad):
        dst_ad = os.path.join(tool_dir, "adapters")
        os.makedirs(dst_ad, exist_ok=True)
        for fn in os.listdir(src_ad):
            s = os.path.join(src_ad, fn)
            d = os.path.join(dst_ad, fn)
            if os.path.exists(d) and not args.force:
                print(f"  skip (exists): {d}")
                continue
            shutil.copy(s, d)
            print(f"  adapters -> {d}")

    # hooks（若存在）：复制脚本 + hooks.json，接线见 hooks/README.md
    src_hk = os.path.join(args.canonical, "hooks")
    if os.path.isdir(src_hk):
        dst_hk = os.path.join(tool_dir, "hooks")
        os.makedirs(dst_hk, exist_ok=True)
        for fn in os.listdir(src_hk):
            s = os.path.join(src_hk, fn)
            d = os.path.join(dst_hk, fn)
            if os.path.exists(d) and not args.force:
                print(f"  skip (exists): {d}")
                continue
            shutil.copy(s, d)
            print(f"  hooks -> {d}")

    print("[bootstrap] done. 用本地 .env 回填密钥后再启动目标工具；hooks 按 hooks/README.md 接线。")


if __name__ == "__main__":
    main()
