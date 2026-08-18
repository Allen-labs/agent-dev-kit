#!/usr/bin/env python3
"""scan_env.py - 扫描当前 WorkBuddy 环境，导出 canonical 报告。

提取：已安装的 skills、mcp.json 里的 server 定义（密钥一律屏蔽）。
用法：
  python scan_env.py                 # 打印到 stdout
  python scan_env.py --out report.json
密钥只显示占位（***），绝不打印真实值，可安全进 canonical 仓库。
"""
import argparse
import json
import os
import shutil
import sys

HOME = os.path.expanduser("~")
SKILLS_DIR = os.path.join(HOME, ".workbuddy", "skills")
MCP_PATH = os.path.join(HOME, ".workbuddy", "mcp.json")
ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets")


def mask(value):
    if value is None:
        return None
    s = str(value)
    if s == "":
        return ""
    return "***"


def list_skills():
    if not os.path.isdir(SKILLS_DIR):
        return []
    out = []
    for name in sorted(os.listdir(SKILLS_DIR)):
        p = os.path.join(SKILLS_DIR, name)
        if os.path.isdir(p):
            skill_md = os.path.join(p, "SKILL.md")
            has = os.path.exists(skill_md)
            out.append({"name": name, "path": p, "has_skill_md": has})
    return out


def read_mcp():
    if not os.path.exists(MCP_PATH):
        return {"exists": False, "servers": []}
    try:
        with open(MCP_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        return {"exists": True, "error": str(e), "servers": []}
    servers = data.get("mcpServers", {})
    masked = []
    for sname, sdef in servers.items():
        env = sdef.get("env", {})
        masked.append({
            "name": sname,
            "command": sdef.get("command"),
            "args": sdef.get("args"),
            "env_keys": list(env.keys()),
            "env_values_masked": {k: mask(v) for k, v in env.items()},
            "url": sdef.get("url"),
            "headers_keys": list(sdef.get("headers", {}).keys()),
        })
    return {"exists": True, "servers": masked}


def materialize(dest):
    """把当前环境 materialize 成 canonical 仓库骨架（密钥屏蔽）。"""
    if os.path.exists(dest) and os.listdir(dest):
        print(f"[scan_env] ERROR: 目标已存在且非空: {dest}", file=sys.stderr)
        sys.exit(1)
    os.makedirs(dest, exist_ok=True)

    # skills 复制
    dst_skills = os.path.join(dest, "skills")
    os.makedirs(dst_skills, exist_ok=True)
    n = 0
    for s in list_skills():
        src = s["path"]
        d = os.path.join(dst_skills, s["name"])
        if os.path.isdir(src):
            shutil.copytree(src, d)
            n += 1
    print(f"  skills/  ({n} 个) -> {dst_skills}")

    # mcp 屏蔽后写入
    mcp = read_mcp()
    mcp_dir = os.path.join(dest, "mcp")
    os.makedirs(mcp_dir, exist_ok=True)
    servers = {}
    for s in mcp.get("servers", []):
        servers[s["name"]] = {
            "command": s.get("command"),
            "args": s.get("args"),
            "url": s.get("url"),
            "env": {k: "${%s}" % k for k in s.get("env_keys", [])},
            "headers": {k: "${%s}" % k for k in s.get("headers_keys", [])},
        }
    with open(os.path.join(mcp_dir, "mcp.servers.json"), "w", encoding="utf-8") as f:
        json.dump(servers, f, indent=2, ensure_ascii=False)
    print(f"  mcp/mcp.servers.json ({len(servers)} 个 server，密钥已占位) -> {mcp_dir}")

    # flow.md / user.md / adapters 从 assets 模板复制
    src_flow = os.path.join(ASSETS_DIR, "agents-dir", "memory", "flow.md")
    if os.path.exists(src_flow):
        shutil.copy(src_flow, os.path.join(dest, "flow.md"))
        print(f"  flow.md -> {dest}")
    with open(os.path.join(dest, "user.md"), "w", encoding="utf-8") as f:
        f.write("# User\n\n[个人偏好、常用约定、城市/时区等]\n")
    adir = os.path.join(ASSETS_DIR, "adapters")
    if os.path.isdir(adir):
        dst_ad = os.path.join(dest, "adapters")
        os.makedirs(dst_ad, exist_ok=True)
        for fn in os.listdir(adir):
            shutil.copy(os.path.join(adir, fn), os.path.join(dst_ad, fn))
        print(f"  adapters/ -> {dst_ad}")
    print(f"[scan_env] canonical 仓库已生成: {dest}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", help="输出报告路径 (json)")
    ap.add_argument("--materialize", help="把当前环境 materialize 成 canonical 仓库到指定目录")
    args = ap.parse_args()

    if args.materialize:
        materialize(args.materialize)
        return

    report = {
        "tool": "workbuddy",
        "home": HOME,
        "skills_dir": SKILLS_DIR,
        "mcp_path": MCP_PATH,
        "skills": list_skills(),
        "mcp": read_mcp(),
    }

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"[scan_env] wrote report -> {args.out}")
    else:
        print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
