#!/usr/bin/env python3
"""agent-kit.py - agent 配置生命周期管理（统一入口）。

五个命令，覆盖从初始化到日常运维的全生命周期：
  init    初始化 canonical 仓库（从当前环境快照）
  push    把 canonical 推到目标工具（skills + mcp + hooks + 指令文件）
  pull    把工具的新增 skill 回灌到 canonical
  status  查看各工具与 canonical 的同步状态（drift 检测）
  check   体检 canonical 健康（质量 + 泄密 + skill 引用完整性）

脚本与 agent 互相依托：
  - 脚本做 agent 做不了的事（文件操作、checksum、格式翻译）
  - 输出 JSON（--json）供 agent 直接消费
  - SKILL.md 是 agent 的操作手册，告诉它何时调什么命令

用法：
  python agent-kit.py init <path>
  python agent-kit.py push --canonical <path> --tool <workbuddy|claude|cursor|codex|opencode|zed> [--write]
  python agent-kit.py pull --canonical <path> --tool <tool> [--write]
  python agent-kit.py status --canonical <path> [--tool <tool>]
  python agent-kit.py check --canonical <path>
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import sys
from datetime import datetime

HOME = os.path.expanduser("~")
SKILLS_DIR = os.path.join(HOME, ".workbuddy", "skills")
MCP_PATH = os.path.join(HOME, ".workbuddy", "mcp.json")
ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets")
TOOL_DIRS = {
    "workbuddy": os.path.join(HOME, ".workbuddy"),
    "claude": os.path.join(HOME, ".claude"),
    "cursor": os.path.join(HOME, ".cursor"),
    "codex": os.path.join(HOME, ".codex"),
    "opencode": os.path.join(HOME, ".config", "opencode"),
    "zed": os.path.join(HOME, ".config", "zed"),
}
MANIFEST_PATH = ".sync/manifest.json"


# ─── 工具函数 ────────────────────────────────────────────

def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _scan_files(root, dirs=("skills", "hooks", "mcp", "adapters")):
    """扫描 canonical 下的核心目录，返回 {relpath: sha256}。"""
    result = {}
    for d in dirs:
        base = os.path.join(root, d)
        if not os.path.isdir(base):
            continue
        for dirpath, _, files in os.walk(base):
            if ".git" in dirpath:
                continue
            for fn in files:
                fp = os.path.join(dirpath, fn)
                rel = os.path.relpath(fp, root)
                try:
                    result[rel.replace("\\", "/")] = _sha256(fp)
                except Exception:
                    pass
    for fn in ("AGENTS.md", "flow.md", "user.md"):
        fp = os.path.join(root, fn)
        if os.path.isfile(fp):
            result[fn] = _sha256(fp)
    return result


def _load_manifest(canonical):
    p = os.path.join(canonical, MANIFEST_PATH)
    if os.path.isfile(p):
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"version": 1, "files": {}, "tools": {}}


def _save_manifest(canonical, manifest):
    p = os.path.join(canonical, MANIFEST_PATH)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    manifest["generated_at"] = datetime.now().isoformat()
    with open(p, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)


def _load_env(canonical):
    """从 canonical/.env 加载密钥（不入仓库）。"""
    env = {}
    p = os.path.join(canonical, ".env")
    if os.path.isfile(p):
        with open(p, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    k, v = line.split("=", 1)
                    env[k.strip()] = v.strip()
    return env


def _inject_env(text, env):
    """把 ${KEY} 占位替换成 .env 里的真实值。"""
    for k, v in env.items():
        text = text.replace("${" + k + "}", v)
    return text


def _load_mcp(canonical):
    p = os.path.join(canonical, "mcp", "mcp.servers.json")
    if os.path.isfile(p):
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def _translate_mcp(servers, tool, env):
    """把 canonical MCP 定义翻译成目标工具格式，注入真实密钥。"""
    if tool in ("workbuddy", "claude", "cursor"):
        return {"mcpServers": _inject_env_dict(servers, env)}
    if tool == "codex":
        out = {}
        for name, sdef in servers.items():
            out[name] = {
                "command": sdef.get("command"),
                "args": sdef.get("args", []),
                "env": _inject_env_dict(sdef.get("env", {}), env),
            }
        return out
    if tool == "opencode":
        out = {}
        for name, sdef in servers.items():
            cmd = [sdef.get("command")] + list(sdef.get("args", []))
            out[name] = {
                "type": "local",
                "command": cmd,
                "enabled": True,
                "environment": _inject_env_dict(sdef.get("env", {}), env),
            }
        return out
    if tool == "zed":
        out = {}
        for name, sdef in servers.items():
            out[name] = {
                "command": sdef.get("command"),
                "args": sdef.get("args", []),
                "env": _inject_env_dict(sdef.get("env", {}), env),
            }
        return out
    return {"mcpServers": servers}


def _inject_env_dict(d, env):
    return {k: _inject_env(str(v), env) for k, v in d.items()}


def _mcp_to_toml(servers):
    """Codex TOML 格式（env 值已注入真实密钥，不再有 ${}）。"""
    lines = ["[mcp_servers]"]
    for name, sdef in servers.items():
        lines.append(f"[mcp_servers.{name}]")
        lines.append(f'command = "{sdef.get("command")}"')
        args_str = ", ".join(f'"{a}"' for a in sdef.get("args", []))
        lines.append(f"args = [{args_str}]")
        if sdef.get("env"):
            env_items = ", ".join(f'{k} = "{v}"' for k, v in sdef["env"].items())
            lines.append(f"env = {{ {env_items} }}")
    return "\n".join(lines) + "\n"


def _instruction_file(tool, canonical):
    """返回目标工具的指令文件路径 + 内容。
    这是修缺口 1 的核心：apply 时真正创建 CLAUDE.md / .cursorrules 等。"""
    ag = os.path.join(canonical, "AGENTS.md")
    if not os.path.isfile(ag):
        return None, None
    tool_dir = TOOL_DIRS[tool]
    if tool == "claude":
        return os.path.join(tool_dir, "CLAUDE.md"), "@%s" % ag.replace("\\", "/")
    if tool == "cursor":
        return os.path.join(tool_dir, ".cursorrules"), "See: %s/AGENTS.md" % canonical.replace("\\", "/")
    if tool == "codex":
        return os.path.join(tool_dir, "AGENTS.md"), open(ag, encoding="utf-8").read()
    if tool in ("opencode", "zed", "workbuddy"):
        return os.path.join(tool_dir, "AGENTS.md"), open(ag, encoding="utf-8").read()
    return None, None


def _backup(dst):
    if os.path.exists(dst):
        bak = dst + ".bak." + str(int(os.path.getmtime(dst)))
        shutil.copy2(dst, bak)
        return bak
    return None


# ─── init ───────────────────────────────────────────────

def cmd_init(args):
    """初始化 canonical 仓库：从当前 WorkBuddy 环境快照。"""
    dest = args.path
    if os.path.exists(dest) and os.listdir(dest):
        _err("目标已存在且非空: %s" % dest)
        return 1
    os.makedirs(dest, exist_ok=True)
    changes = {"skills": 0, "mcp": 0, "files": []}

    dst_skills = os.path.join(dest, "skills")
    os.makedirs(dst_skills, exist_ok=True)
    if os.path.isdir(SKILLS_DIR):
        for name in sorted(os.listdir(SKILLS_DIR)):
            src = os.path.join(SKILLS_DIR, name)
            d = os.path.join(dst_skills, name)
            if os.path.isdir(src):
                shutil.copytree(src, d,
                    ignore=shutil.ignore_patterns(".git", ".gitmodules", ".svn", ".hg"))
                changes["skills"] += 1

    mcp_dir = os.path.join(dest, "mcp")
    os.makedirs(mcp_dir, exist_ok=True)
    if os.path.isfile(MCP_PATH):
        with open(MCP_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        servers = data.get("mcpServers", {})
        masked = {}
        for sname, sdef in servers.items():
            env = sdef.get("env", {})
            masked[sname] = {
                "command": sdef.get("command"),
                "args": sdef.get("args"),
                "env": {k: "${%s}" % k for k in env},
            }
            changes["mcp"] += 1
        with open(os.path.join(mcp_dir, "mcp.servers.json"), "w", encoding="utf-8") as f:
            json.dump(masked, f, indent=2, ensure_ascii=False)

    for fn, src_name in [("flow.md", "agents-dir/memory/flow.md"),
                          ("AGENTS.md", "AGENTS.personal.md"),
                          ("user.md", "user.md")]:
        src = os.path.join(ASSETS_DIR, src_name)
        if os.path.exists(src):
            shutil.copy(src, os.path.join(dest, fn))
            changes["files"].append(fn)

    adir = os.path.join(ASSETS_DIR, "adapters")
    if os.path.isdir(adir):
        dst_ad = os.path.join(dest, "adapters")
        os.makedirs(dst_ad, exist_ok=True)
        for fn in os.listdir(adir):
            shutil.copy(os.path.join(adir, fn), os.path.join(dst_ad, fn))

    manifest = {"version": 1, "files": _scan_files(dest), "tools": {}}
    _save_manifest(dest, manifest)

    _emit(args, "init", dest, changes)
    return 0


# ─── push ───────────────────────────────────────────────

def cmd_push(args):
    """把 canonical 推到目标工具（幂等：checksum 对比，相同则 skip）。"""
    canonical = args.canonical
    tool = args.tool
    env = _load_env(canonical)
    manifest = _load_manifest(canonical)
    current = _scan_files(canonical)
    tool_dir = TOOL_DIRS[tool]
    plan = {"new": [], "modified": [], "skipped": [], "instructions": []}

    os.makedirs(tool_dir, exist_ok=True)

    src_skills = os.path.join(canonical, "skills")
    if os.path.isdir(src_skills):
        dst_skills = os.path.join(tool_dir, "skills")
        os.makedirs(dst_skills, exist_ok=True)
        for name in os.listdir(src_skills):
            src = os.path.join(src_skills, name)
            dst = os.path.join(dst_skills, name)
            if not os.path.isdir(src) or name == "disabled":
                continue
            key = "skills/%s" % name
            src_hash = current.get(key, "")
            dst_hash = manifest.get("files", {}).get(key, "")
            if src_hash == dst_hash and os.path.isdir(dst):
                plan["skipped"].append(key)
                continue
            if os.path.exists(dst):
                if not args.force:
                    plan["skipped"].append(key + " (exists, --force)")
                    continue
                _backup(dst)
                shutil.rmtree(dst)
            shutil.copytree(src, dst,
                ignore=shutil.ignore_patterns(".git", ".gitmodules"))
            plan["new" if dst_hash == "" else "modified"].append(key)

    servers = _load_mcp(canonical)
    if servers:
        translated = _translate_mcp(servers, tool, env)
        if tool == "codex":
            mcp_dst = os.path.join(tool_dir, "config.toml")
            content = _mcp_to_toml(translated)
            _write_or_backup(mcp_dst, content, args, plan, "mcp/config.toml")
        elif tool == "opencode":
            _merge_json_file(os.path.join(tool_dir, "opencode.json"),
                             "mcp", translated, args, plan, "mcp/opencode.json")
        elif tool == "zed":
            _merge_json_file(os.path.join(tool_dir, "settings.json"),
                             "context_servers", translated, args, plan, "mcp/zed.json")
        else:
            mcp_dst = os.path.join(tool_dir, "mcp.json")
            content = json.dumps(translated, indent=2, ensure_ascii=False)
            _write_or_backup(mcp_dst, content, args, plan, "mcp/mcp.json")

    instr_path, instr_content = _instruction_file(tool, canonical)
    if instr_path and instr_content:
        _write_or_backup(instr_path, instr_content, args, plan, "instruction")

    src_hk = os.path.join(canonical, "hooks")
    if os.path.isdir(src_hk):
        dst_hk = os.path.join(tool_dir, "hooks")
        os.makedirs(dst_hk, exist_ok=True)
        for fn in os.listdir(src_hk):
            src = os.path.join(src_hk, fn)
            dst = os.path.join(dst_hk, fn)
            if os.path.isfile(src):
                _write_or_backup(dst, open(src, encoding="utf-8").read(),
                                 args, plan, "hooks/%s" % fn)

    manifest["files"] = current
    manifest.setdefault("tools", {})[tool] = {
        "last_push": datetime.now().isoformat(),
        "synced": len(plan["new"]) + len(plan["modified"]),
        "skipped": len(plan["skipped"]),
    }
    _save_manifest(canonical, manifest)

    plan["summary"] = "%d new, %d modified, %d skipped" % (
        len(plan["new"]), len(plan["modified"]), len(plan["skipped"]))
    _emit(args, "push", tool_dir, plan)
    return 0


def _write_or_backup(dst, content, args, plan, label):
    if os.path.exists(dst) and not args.force:
        plan["skipped"].append(label + " (exists)")
        return
    if os.path.exists(dst):
        _backup(dst)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with open(dst, "w", encoding="utf-8") as f:
        f.write(content)
    plan["new" if not os.path.exists(dst + ".bak") else "modified"].append(label)


def _merge_json_file(dst, key, obj, args, plan, label):
    existing = {}
    if os.path.exists(dst):
        if not args.force:
            plan["skipped"].append(label + " (exists)")
            return
        try:
            with open(dst, encoding="utf-8") as f:
                existing = json.load(f)
        except Exception:
            existing = {}
    existing[key] = obj
    _write_or_backup(dst, json.dumps(existing, indent=2, ensure_ascii=False),
                     args, plan, label)


# ─── pull ───────────────────────────────────────────────

def cmd_pull(args):
    """把工具的新增 skill 回灌到 canonical。"""
    canonical = args.canonical
    tool = args.tool
    tool_dir = TOOL_DIRS[tool]
    src_skills = os.path.join(tool_dir, "skills")
    dst_skills = os.path.join(canonical, "skills")
    plan = {"collected": [], "skipped": []}

    if not os.path.isdir(src_skills):
        _emit(args, "pull", tool_dir, {"error": "工具 skills 目录不存在", "collected": [], "skipped": []})
        return 0

    os.makedirs(dst_skills, exist_ok=True)
    for name in sorted(os.listdir(src_skills)):
        src = os.path.join(src_skills, name)
        dst = os.path.join(dst_skills, name)
        if not os.path.isdir(src):
            continue
        if os.path.isdir(dst):
            plan["skipped"].append(name)
            continue
        if not args.write:
            plan["collected"].append(name + " (dry-run)")
            continue
        shutil.copytree(src, dst,
            ignore=shutil.ignore_patterns(".git", ".gitmodules"))
        plan["collected"].append(name)

    if plan["collected"] and args.write:
        manifest = _load_manifest(canonical)
        manifest["files"] = _scan_files(canonical)
        _save_manifest(canonical, manifest)

    plan["summary"] = "%d collected, %d skipped" % (
        len(plan["collected"]), len(plan["skipped"]))
    _emit(args, "pull", tool_dir, plan)
    return 0


# ─── status ──────────────────────────────────────────────

def cmd_status(args):
    """查看各工具与 canonical 的同步状态（drift 检测）。"""
    canonical = args.canonical
    manifest = _load_manifest(canonical)
    canonical_files = _scan_files(canonical)

    if args.tool and args.tool != "all":
        tools = {args.tool: TOOL_DIRS[args.tool]}
    else:
        tools = TOOL_DIRS

    result = {}
    for tool, tool_dir in tools.items():
        dst_skills = os.path.join(tool_dir, "skills")
        synced = drifted = missing = extra = 0
        if os.path.isdir(dst_skills):
            for name in os.listdir(dst_skills):
                dst = os.path.join(dst_skills, name)
                if not os.path.isdir(dst) or name == "disabled":
                    continue
                ck = "skills/%s" % name
                if ck not in canonical_files:
                    extra += 1
                else:
                    dst_hash = _dir_hash(dst)
                    if dst_hash == manifest.get("files", {}).get(ck, ""):
                        synced += 1
                    else:
                        drifted += 1
            for name in canonical_files:
                if name.startswith("skills/"):
                    sname = name.split("/", 1)[1].split("/")[0]
                    if not os.path.isdir(os.path.join(dst_skills, sname)):
                        missing += 1
        result[tool] = {
            "synced": synced, "drifted": drifted,
            "missing": missing, "extra": extra,
            "last_push": manifest.get("tools", {}).get(tool, {}).get("last_push", "never"),
        }

    _emit(args, "status", canonical, result)
    return 0


def _dir_hash(path):
    h = hashlib.sha256()
    for dirpath, _, files in os.walk(path):
        if ".git" in dirpath:
            continue
        for fn in sorted(files):
            fp = os.path.join(dirpath, fn)
            try:
                h.update(fp.encode())
                with open(fp, "rb") as f:
                    h.update(f.read())
            except Exception:
                pass
    return h.hexdigest()


# ─── check ──────────────────────────────────────────────

SECRET_PATTERNS = [
    re.compile(r"sk-[a-zA-Z0-9]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"(?i)api[_-]?key\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{20,}"),
    re.compile(r"(?i)token\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{20,}"),
    re.compile(r"(?i)password\s*[:=]\s*['\"]?.{8,}"),
]
FALSE_POSITIVES = ("${{", "secrets.", "example", "your_", "your-", "xxxx",
                   "mypassword", "secret123", "changeme", "placeholder",
                   "<", ">", "process.env", "os.environ", "${",
                   "await ", "hash(", "const ", "var ", "let ",
                   "plaintext", "salt_ro", "salt=", "sALT")
KNOWN_BAD_SKILL_REFS = {
    "spec-driven-development", "planning-and-task-breakdown", "tdd", "code-review",
}


def cmd_check(args):
    """体检 canonical 健康。"""
    canonical = args.canonical
    result = {"agents_md": [], "secrets": [], "skill_refs": [], "required_files": []}

    ag = os.path.join(canonical, "AGENTS.md")
    if not os.path.exists(ag):
        result["agents_md"].append("AGENTS.md 缺失")
    else:
        with open(ag, "r", encoding="utf-8") as f:
            lines = f.readlines()
        if len(lines) > 150:
            result["agents_md"].append("AGENTS.md 过长 (%d > 150)" % len(lines))
        if len(lines) < 10:
            result["agents_md"].append("AGENTS.md 过短")
        if not any("`" in ln for ln in lines):
            result["agents_md"].append("AGENTS.md 缺少反引号命令")

    for root, _, files in os.walk(canonical):
        if ".git" in root or ".sync" in root:
            continue
        for fn in files:
            if not fn.endswith((".md", ".json", ".toml", ".yaml", ".yml", ".env")):
                continue
            fp = os.path.join(root, fn)
            try:
                text = open(fp, "r", encoding="utf-8", errors="ignore").read()
            except Exception:
                continue
            for pat in SECRET_PATTERNS:
                for m in pat.finditer(text):
                    snip = m.group(0)
                    if len(snip) > 6 and not any(t in snip.lower() for t in FALSE_POSITIVES):
                        result["secrets"].append({"file": fp, "snippet": snip[:40]})

    known_skills = set()
    for d in ("skills", "skills-optional"):
        p = os.path.join(canonical, d)
        if os.path.isdir(p):
            for n in os.listdir(p):
                if os.path.isdir(os.path.join(p, n)):
                    known_skills.add(n)
    for fn in ("flow.md", "AGENTS.md"):
        fp = os.path.join(canonical, fn)
        if not os.path.isfile(fp):
            continue
        text = open(fp, "r", encoding="utf-8", errors="ignore").read()
        for bad in KNOWN_BAD_SKILL_REFS:
            if "`%s`" % bad in text:
                result["skill_refs"].append("%s: 含已禁用 skill `%s`" % (fn, bad))
        for m in re.finditer(r"`([a-z0-9]+(?:-[a-z0-9]+)+)`", text):
            tok = m.group(1)
            if tok not in known_skills and tok not in KNOWN_BAD_SKILL_REFS:
                pass  # 通用检查太吵，只报黑名单命中

    for f in ["AGENTS.md", "flow.md", "mcp/mcp.servers.json"]:
        fp = os.path.join(canonical, f)
        result["required_files"].append({"file": f, "exists": os.path.exists(fp)})

    all_ok = all(not v for v in [result["agents_md"], result["secrets"],
                                  result["skill_refs"]])
    result["overall"] = "ok" if all_ok else "issues"
    _emit(args, "check", canonical, result)
    return 0 if all_ok else 1


# ─── 输出 ────────────────────────────────────────────────

def _emit(args, cmd, target, data):
    if args.json:
        print(json.dumps({"cmd": cmd, "target": target, "data": data},
                         indent=2, ensure_ascii=False))
    else:
        print("[%s] target: %s" % (cmd, target))
        if isinstance(data, dict):
            for k, v in data.items():
                if isinstance(v, list):
                    print("  %s (%d):" % (k, len(v)))
                    for item in v:
                        print("    - %s" % item)
                elif isinstance(v, dict):
                    print("  %s:" % k)
                    for k2, v2 in v.items():
                        print("    %s: %s" % (k2, v2))
                else:
                    print("  %s: %s" % (k, v))
        else:
            print("  %s" % data)


def _err(msg):
    print("[ERROR] %s" % msg, file=sys.stderr)


# ─── CLI ────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(
        prog="agent-kit",
        description="agent 配置生命周期管理",
    )
    ap.add_argument("--json", action="store_true", help="输出 JSON 供 agent 消费")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init", help="初始化 canonical 仓库")
    p_init.add_argument("path", help="canonical 仓库路径")

    p_push = sub.add_parser("push", help="推 canonical 到工具")
    p_push.add_argument("--canonical", required=True)
    p_push.add_argument("--tool", required=True, choices=list(TOOL_DIRS.keys()))
    p_push.add_argument("--write", action="store_true", help="真正落盘（默认 dry-run）")
    p_push.add_argument("--force", action="store_true", help="覆盖已有文件")

    p_pull = sub.add_parser("pull", help="回灌工具 skill 到 canonical")
    p_pull.add_argument("--canonical", required=True)
    p_pull.add_argument("--tool", required=True, choices=list(TOOL_DIRS.keys()))
    p_pull.add_argument("--write", action="store_true")

    p_status = sub.add_parser("status", help="查看同步状态")
    p_status.add_argument("--canonical", required=True)
    p_status.add_argument("--tool", default="all", choices=list(TOOL_DIRS.keys()) + ["all"])

    p_check = sub.add_parser("check", help="体检 canonical")
    p_check.add_argument("--canonical", required=True)

    args = ap.parse_args()
    if args.cmd == "init":
        return cmd_init(args)
    if args.cmd == "push":
        if not args.write:
            print("[push] DRY-RUN（加 --write 落盘）")
        return cmd_push(args)
    if args.cmd == "pull":
        if not args.write:
            print("[pull] DRY-RUN（加 --write 落盘）")
        return cmd_pull(args)
    if args.cmd == "status":
        return cmd_status(args)
    if args.cmd == "check":
        return cmd_check(args)


if __name__ == "__main__":
    sys.exit(main())
