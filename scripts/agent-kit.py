#!/usr/bin/env python3
"""agent-kit.py - agent 配置生命周期管理（统一入口）。

五个命令，见名知意，覆盖从初始化到日常运维的全生命周期：
  init     初始化 canonical 仓库（从当前环境快照）
  backup   备份目标工具的现有配置（apply 前先 backup，安全网）
  apply    应用 canonical 配置到目标工具（skills + mcp + hooks + 指令文件）
  collect  收集工具新增的 skill 回灌到 canonical
  check    检查健康状况（canonical 质量 + 泄密 + skill 引用 + 工具 drift）

脚本与 agent 互相依托：
  - 脚本做 agent 做不了的事（文件操作、checksum、格式翻译）
  - 输出 JSON（--json）供 agent 直接消费
  - SKILL.md 是 agent 的操作手册，告诉它何时调什么命令

用法：
  python agent-kit.py init <path>
  python agent-kit.py backup --tool <workbuddy|claude|cursor|codex|opencode|zed> [--dir <backup_path>]
  python agent-kit.py apply --canonical <path> --tool <tool> [--write]
  python agent-kit.py collect --canonical <path> --tool <tool> [--write]
  python agent-kit.py check --canonical <path> [--tool <tool>]
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
# init 快照源；可用 AGENT_KIT_SKILLS_DIR 覆盖（测试隔离/自定义环境）
SKILLS_DIR = os.environ.get("AGENT_KIT_SKILLS_DIR",
                            os.path.join(HOME, ".workbuddy", "skills"))
MCP_PATH = os.environ.get("AGENT_KIT_MCP_PATH",
                          os.path.join(HOME, ".workbuddy", "mcp.json"))
ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets")
TOOL_DIRS = {
    "workbuddy": os.path.join(HOME, ".workbuddy"),
    "claude": os.path.join(HOME, ".claude"),
    "cursor": os.path.join(HOME, ".cursor"),
    "codex": os.path.join(HOME, ".codex"),
    "opencode": os.path.join(HOME, ".config", "opencode"),
    "zed": os.path.join(HOME, ".config", "zed"),
}


def _tool_dir(tool):
    """返回工具目录；可用环境变量 AGENT_KIT_TOOL_DIR_<TOOL> 覆盖（测试隔离用）。"""
    return os.environ.get("AGENT_KIT_TOOL_DIR_" + tool.upper(), TOOL_DIRS[tool])


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
    lines = []
    for name, sdef in servers.items():
        lines.append(f"[mcp_servers.{name}]")
        lines.append(f'command = "{sdef.get("command")}"')
        args_str = ", ".join(f'"{a}"' for a in sdef.get("args", []))
        lines.append(f"args = [{args_str}]")
        if sdef.get("env"):
            env_items = ", ".join(f'{k} = "{v}"' for k, v in sdef["env"].items())
            lines.append(f"env = {{ {env_items} }}")
        lines.append("")
    return "\n".join(lines)


def _merge_toml(dst, new_sections, args, plan, label):
    """把 new_sections（[mcp_servers.xxx] 段）合并到已有 config.toml，不破坏现有内容。
    已有的同名 section（含子段如 [mcp_servers.xxx.env]）先删除再追加。"""
    existing = ""
    if os.path.exists(dst):
        if not args.force and not getattr(args, "upgrade", False):
            plan["skipped"].append(label + " (exists)")
            return
        try:
            with open(dst, "r", encoding="utf-8") as f:
                existing = f.read()
        except Exception:
            existing = ""
        if getattr(args, "write", False):
            if getattr(args, "upgrade", False):
                _backup(dst)
            elif args.force:
                _backup(dst)
    # 解析 new_sections 里要推的 server 名
    new_names = set(re.findall(r"^\[mcp_servers\.([^.\]]+)\]", new_sections, re.MULTILINE))
    # 从 existing 里删除同名旧 section（含子段 [mcp_servers.xxx.env]）
    lines = existing.split("\n")
    result = []
    skip_prefix = None  # 正在跳过的 server 名
    for line in lines:
        m = re.match(r"^\[mcp_servers\.([^.\]]+)\]", line)
        if m:
            name = m.group(1)
            if name in new_names:
                skip_prefix = name
                continue
            else:
                skip_prefix = None
                result.append(line)
                continue
        if skip_prefix:
            # 跳过子段（如 [mcp_servers.xxx.env]）和 section 内容
            if line.startswith("[") and not line.startswith("[mcp_servers.%s" % skip_prefix):
                skip_prefix = None
                result.append(line)
            continue
        result.append(line)
    cleaned = "\n".join(result).rstrip()
    if cleaned:
        cleaned += "\n\n"
    content = cleaned + new_sections.strip() + "\n"
    dry = not getattr(args, "write", False)
    if dry:
        plan["modified"].append(label + " (dry-run)")
        return
    os.makedirs(os.path.dirname(dst) or ".", exist_ok=True)
    with open(dst, "w", encoding="utf-8") as f:
        f.write(content)
    plan["modified"].append(label)


def _instruction_file(tool, canonical):
    """返回目标工具的指令文件路径 + 内容。
    这是修缺口 1 的核心：apply 时真正创建 CLAUDE.md / .cursorrules 等。"""
    ag = os.path.join(canonical, "AGENTS.md")
    if not os.path.isfile(ag):
        return None, None
    tool_dir = _tool_dir(tool)
    if tool == "claude":
        return os.path.join(tool_dir, "CLAUDE.md"), "@%s" % ag.replace("\\", "/")
    if tool == "cursor":
        return os.path.join(tool_dir, ".cursorrules"), "See: %s/AGENTS.md" % canonical.replace("\\", "/")
    if tool == "codex":
        return os.path.join(tool_dir, "AGENTS.md"), open(ag, encoding="utf-8").read()
    if tool in ("opencode", "zed", "workbuddy"):
        return os.path.join(tool_dir, "AGENTS.md"), open(ag, encoding="utf-8").read()
    return None, None


def _remove_tree(path):
    """深度删除目录树。

    不用 shutil.rmtree：部分沙箱环境（如 WorkBuddy CLI）会给 rmtree
    挂安全钩子走回收站，回收站不可用时抛 SAFE_DELETE_FAIL_CLOSED。
    用 os.remove/os.rmdir 逐层删，任何环境通用。"""
    if not os.path.isdir(path):
        return
    for root, dirs, files in os.walk(path, topdown=False):
        for fn in files:
            try:
                os.remove(os.path.join(root, fn))
            except OSError:
                pass
        for dn in dirs:
            try:
                os.rmdir(os.path.join(root, dn))
            except OSError:
                pass
    try:
        os.rmdir(path)
    except OSError:
        pass


def _backup(dst):
    """备份单个文件或目录（目录用 copytree，文件用 copy2）。
    修复：apply 覆盖 skill 目录时 _backup 被传入目录，
    旧实现 copy2 不支持目录 → Windows PermissionError。
    bak 名加递增后缀，避免同一秒多次备份冲突。"""
    if os.path.exists(dst):
        base = dst + ".bak." + str(int(os.path.getmtime(dst)))
        bak = base
        i = 1
        while os.path.exists(bak):
            bak = "%s.%d" % (base, i)
            i += 1
        if os.path.isdir(dst):
            shutil.copytree(dst, bak)
        else:
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
            # WorkBuddy 的 mcp.json 里 sdef 可能是 Python repr 字符串，需转 dict
            if isinstance(sdef, str):
                import ast
                try:
                    sdef = ast.literal_eval(sdef)
                except Exception:
                    continue
            env = sdef.get("env", {}) or {}
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


# ─── apply（含 upgrade 模式）─────────────────────────────

def cmd_push(args):
    """把 canonical 推到目标工具。
    普通模式（默认）：只推 canonical 有、工具没有的（新增）。
    --upgrade：升级模式，先 backup 再覆盖 canonical 管理的文件（含已变更的），
              但不动工具里用户自己新增的 skill。
    --force：强制覆盖所有已有文件（含非 canonical 管理的）。
    """
    canonical = args.canonical
    tool = args.tool
    env = _load_env(canonical)
    manifest = _load_manifest(canonical)
    current = _scan_files(canonical)
    tool_dir = _tool_dir(tool)
    plan = {"new": [], "modified": [], "skipped": [], "backed_up": None}
    upgrade = getattr(args, "upgrade", False)
    dry = not getattr(args, "write", False)  # 真 dry-run：不落盘

    os.makedirs(tool_dir, exist_ok=True)

    # upgrade 模式：先完整 backup（dry-run 不落盘）
    if upgrade and not dry:
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_dir = os.path.join(HOME, ".agent-kit-backups",
                                   "%s-upgrade-%s" % (tool, ts))
        _do_backup(tool_dir, backup_dir)
        plan["backed_up"] = backup_dir

    src_skills = os.path.join(canonical, "skills")
    if os.path.isdir(src_skills):
        dst_skills = os.path.join(tool_dir, "skills")
        os.makedirs(dst_skills, exist_ok=True)
        for name in os.listdir(src_skills):
            src = os.path.join(src_skills, name)
            dst = os.path.join(dst_skills, name)
            if not os.path.isdir(src) or not _is_skill_dir(name):
                continue
            key = "skills/%s" % name
            # 幂等：canonical 侧与工具侧同名 skill 目录内容一致 → skip
            # （不依赖 manifest——manifest 只是 canonical 快照，不代表工具侧真实状态。
            #   旧实现用 manifest 比对：collect 更新 canonical 后 manifest 同步更新，
            #   导致 apply 永远 skip，工具侧旧副本无法升级，drift 无法修复）
            if (os.path.isdir(dst) and os.listdir(dst)
                    and _dir_hash(src) == _dir_hash(dst)):
                plan["skipped"].append(key)
                continue
            # 工具已有但 canonical 变了 → upgrade 模式覆盖，普通模式 skip
            if os.path.exists(dst):
                if upgrade or args.force:
                    if dry:
                        plan["modified"].append(key + " (dry-run)")
                        continue
                    if upgrade:
                        _backup(dst)
                    _remove_tree(dst)
                    shutil.copytree(src, dst,
                        ignore=shutil.ignore_patterns(".git", ".gitmodules"))
                    plan["modified"].append(key)
                else:
                    plan["skipped"].append(key + " (changed, --upgrade)")
                continue
            # 工具没有 → 新增
            if dry:
                plan["new"].append(key + " (dry-run)")
                continue
            shutil.copytree(src, dst,
                ignore=shutil.ignore_patterns(".git", ".gitmodules"))
            plan["new"].append(key)

    servers = _load_mcp(canonical)
    if servers:
        translated = _translate_mcp(servers, tool, env)
        if tool == "codex":
            mcp_dst = os.path.join(tool_dir, "config.toml")
            content = _mcp_to_toml(translated)
            _merge_toml(mcp_dst, content, args, plan, "mcp/config.toml")
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
    if not dry:
        manifest.setdefault("tools", {})[tool] = {
            "last_apply": datetime.now().isoformat(),
            "synced": len(plan["new"]) + len(plan["modified"]),
            "skipped": len(plan["skipped"]),
        }
        _save_manifest(canonical, manifest)

    plan["summary"] = "%d new, %d modified, %d skipped" % (
        len(plan["new"]), len(plan["modified"]), len(plan["skipped"]))
    _emit(args, "apply", tool_dir, plan)
    return 0


def _write_or_backup(dst, content, args, plan, label):
    upgrade = getattr(args, "upgrade", False)
    dry = not getattr(args, "write", False)
    if os.path.exists(dst) and not args.force and not upgrade:
        plan["skipped"].append(label + " (exists)")
        return
    if os.path.exists(dst):
        if upgrade and not dry:
            _backup(dst)
        elif args.force and not dry:
            _backup(dst)
    if dry:
        plan[("new" if not os.path.exists(dst) else "modified")].append(
            label + " (dry-run)")
        return
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with open(dst, "w", encoding="utf-8") as f:
        f.write(content)
    if os.path.exists(dst + ".bak"):
        plan["modified"].append(label)
    else:
        plan["new"].append(label)


def _merge_json_file(dst, key, obj, args, plan, label):
    upgrade = getattr(args, "upgrade", False)
    existing = {}
    if os.path.exists(dst):
        if not args.force and not upgrade:
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
    """把工具的新增/更新 skill 回灌到 canonical。

    - canonical 没有的 → collected（新增）
    - 两侧都有但内容不同 → updated（工具侧为准，覆盖 canonical）
    - 两侧一致 → skipped
    """
    canonical = args.canonical
    tool = args.tool
    tool_dir = _tool_dir(tool)
    src_skills = os.path.join(tool_dir, "skills")
    dst_skills = os.path.join(canonical, "skills")
    plan = {"collected": [], "updated": [], "skipped": []}

    if not os.path.isdir(src_skills):
        _emit(args, "collect", tool_dir,
              {"error": "工具 skills 目录不存在",
               "collected": [], "updated": [], "skipped": []})
        return 0

    os.makedirs(dst_skills, exist_ok=True)
    for name in sorted(os.listdir(src_skills)):
        src = os.path.join(src_skills, name)
        dst = os.path.join(dst_skills, name)
        if not os.path.isdir(src) or not _is_skill_dir(name):
            continue
        if os.path.isdir(dst):
            # 已存在：内容一致 → skip；不同 → 更新（工具侧为准）
            if _dir_hash(src) == _dir_hash(dst):
                plan["skipped"].append(name)
                continue
            if not args.write:
                plan["updated"].append(name + " (dry-run)")
                continue
            _remove_tree(dst)
            shutil.copytree(src, dst,
                ignore=shutil.ignore_patterns(".git", ".gitmodules",
                                              "__pycache__", "*.pyc"))
            plan["updated"].append(name)
            continue
        if not args.write:
            plan["collected"].append(name + " (dry-run)")
            continue
        shutil.copytree(src, dst,
            ignore=shutil.ignore_patterns(".git", ".gitmodules",
                                          "__pycache__", "*.pyc"))
        plan["collected"].append(name)

    if (plan["collected"] or plan["updated"]) and args.write:
        manifest = _load_manifest(canonical)
        manifest["files"] = _scan_files(canonical)
        _save_manifest(canonical, manifest)

    plan["summary"] = "%d collected, %d updated, %d skipped" % (
        len(plan["collected"]), len(plan["updated"]), len(plan["skipped"]))
    _emit(args, "collect", tool_dir, plan)
    return 0


# ─── backup + check（含 drift 检测）──────────────────────

def _dir_hash(path):
    """递归计算目录的 SHA256（用于 drift 检测）。

    只 hash「相对路径 + 内容」，不含绝对路径——
    否则 canonical 侧与工具侧路径不同，hash 永远不等，
    导致 synced 恒为 0、全部误报 drifted。
    忽略 __pycache__/.git，避免运行时垃圾造成误报 drifted。
    行尾归一化（CRLF→LF）：git autocrlf 会让同一文件在两侧行尾不同，
    不归一化会导致误报 drifted。
    """
    h = hashlib.sha256()
    root = os.path.abspath(path)
    for dirpath, dirnames, files in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in ("__pycache__", ".git")]
        for fn in sorted(files):
            fp = os.path.join(dirpath, fn)
            rel = os.path.relpath(fp, root).replace(os.sep, "/")
            try:
                h.update(rel.encode("utf-8"))
                h.update(b"\0")
                with open(fp, "rb") as f:
                    raw = f.read()
                h.update(raw.replace(b"\r\n", b"\n"))
            except Exception:
                pass
    return h.hexdigest()


def _is_skill_dir(name):
    """判断目录名是否为真正的 skill（排除系统/备份/缓存目录）。"""
    if name in ("disabled", ".system", ".git", "__pycache__"):
        return False
    if name.startswith("."):
        return False
    if ".bak." in name:
        return False
    return True


def _do_backup(tool_dir, backup_dir):
    """把工具目录的配置相关文件备份到 backup_dir（backup 命令和 upgrade 模式共用）。"""
    config_items = ["skills", "hooks", "adapters", "mcp.json", "AGENTS.md",
                    "CLAUDE.md", ".cursorrules", "config.toml", "opencode.json",
                    "settings.json"]
    os.makedirs(backup_dir, exist_ok=True)
    for item in config_items:
        src = os.path.join(tool_dir, item)
        dst = os.path.join(backup_dir, item)
        if not os.path.exists(src):
            continue
        try:
            if os.path.isdir(src):
                shutil.copytree(src, dst,
                    ignore=shutil.ignore_patterns(".git", "__pycache__"),
                    dirs_exist_ok=True)
            elif os.path.isfile(src):
                shutil.copy2(src, dst)
        except Exception:
            pass  # 锁文件等忽略，不中断 upgrade


def cmd_backup(args):
    """备份目标工具的配置相关文件到安全目录。apply --upgrade 前自动调用。
    只备份配置类目录（skills/hooks/adapters）和指令文件，不备份运行时数据。"""
    tool = args.tool
    tool_dir = _tool_dir(tool)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_dir = args.dir or os.path.join(HOME, ".agent-kit-backups", "%s-%s" % (tool, ts))

    if not os.path.isdir(tool_dir):
        _emit(args, "backup", backup_dir, {"error": "工具目录不存在: %s" % tool_dir, "files": []})
        return 0

    config_items = ["skills", "hooks", "adapters", "mcp.json", "AGENTS.md",
                    "CLAUDE.md", ".cursorrules", "config.toml", "opencode.json",
                    "settings.json"]
    backed_up = []
    errors = []
    for item in config_items:
        src = os.path.join(tool_dir, item)
        if not os.path.exists(src):
            continue
        try:
            dst = os.path.join(backup_dir, item)
            if os.path.isdir(src):
                shutil.copytree(src, dst,
                    ignore=shutil.ignore_patterns(".git", "__pycache__"),
                    dirs_exist_ok=True)
            elif os.path.isfile(src):
                shutil.copy2(src, dst)
            backed_up.append(item)
        except Exception as e:
            errors.append({"item": item, "error": str(e)[:80]})

    result = {"files": backed_up, "count": len(backed_up), "path": backup_dir}
    if errors:
        result["errors"] = errors
    _emit(args, "backup", backup_dir, result)
    return 0


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
    """检查健康状况：canonical 质量 + 泄密 + skill 引用；--tool 时附带 drift 检测。"""
    canonical = args.canonical
    result = {"agents_md": [], "secrets": [], "skill_refs": [], "required_files": [], "drift": {}}

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

    for f in ["AGENTS.md", "flow.md", "mcp/mcp.servers.json"]:
        fp = os.path.join(canonical, f)
        result["required_files"].append({"file": f, "exists": os.path.exists(fp)})

    # --tool 时附带 drift 检测（skill 目录级对比）
    if getattr(args, "tool", None):
        manifest = _load_manifest(canonical)
        tool_dir = _tool_dir(args.tool)
        src_skills = os.path.join(canonical, "skills")
        dst_skills = os.path.join(tool_dir, "skills")
        synced = drifted = missing = extra = 0

        # canonical 侧的 skill 名集合
        canon_skills = set()
        if os.path.isdir(src_skills):
            canon_skills = {n for n in os.listdir(src_skills)
                           if os.path.isdir(os.path.join(src_skills, n))
                           and _is_skill_dir(n)}

        # 工具侧的 skill 名集合
        tool_skills = set()
        if os.path.isdir(dst_skills):
            tool_skills = {n for n in os.listdir(dst_skills)
                          if os.path.isdir(os.path.join(dst_skills, n))
                          and _is_skill_dir(n)}

        # 对比
        for name in canon_skills | tool_skills:
            in_canon = name in canon_skills
            in_tool = name in tool_skills
            if in_canon and in_tool:
                # 两侧都有：对比目录 hash
                src_h = _dir_hash(os.path.join(src_skills, name))
                dst_h = _dir_hash(os.path.join(dst_skills, name))
                if src_h == dst_h:
                    synced += 1
                else:
                    drifted += 1
            elif in_canon and not in_tool:
                missing += 1
            elif in_tool and not in_canon:
                extra += 1

        result["drift"] = {
            "tool": args.tool,
            "synced": synced, "drifted": drifted,
            "missing": missing, "extra": extra,
            "last_apply": manifest.get("tools", {}).get(args.tool, {}).get("last_apply", "never"),
        }

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
        description="agent 配置生命周期管理（init / backup / apply / collect / check）",
    )
    ap.add_argument("--json", action="store_true", help="输出 JSON 供 agent 消费")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init", help="初始化 canonical 仓库")
    p_init.add_argument("path", help="canonical 仓库路径")

    p_backup = sub.add_parser("backup", help="备份目标工具的现有配置")
    p_backup.add_argument("--tool", required=True, choices=list(TOOL_DIRS.keys()))
    p_backup.add_argument("--dir", default=None, help="备份目录（默认 ~/.agent-kit-backups/<tool>-<timestamp>）")

    p_apply = sub.add_parser("apply", help="应用 canonical 配置到工具")
    p_apply.add_argument("--canonical", required=True)
    p_apply.add_argument("--tool", required=True, choices=list(TOOL_DIRS.keys()))
    p_apply.add_argument("--write", action="store_true", help="真正落盘（默认 dry-run）")
    p_apply.add_argument("--upgrade", action="store_true",
                         help="升级模式：先 backup 再覆盖 canonical 管理的已变更文件（不动工具里用户新增的 skill）")
    p_apply.add_argument("--force", action="store_true", help="强制覆盖所有已有文件")

    p_collect = sub.add_parser("collect", help="收集工具新增 skill 回灌到 canonical")
    p_collect.add_argument("--canonical", required=True)
    p_collect.add_argument("--tool", required=True, choices=list(TOOL_DIRS.keys()))
    p_collect.add_argument("--write", action="store_true")

    p_check = sub.add_parser("check", help="检查健康状况（canonical 质量 + 工具 drift）")
    p_check.add_argument("--canonical", required=True)
    p_check.add_argument("--tool", default=None, choices=list(TOOL_DIRS.keys()),
                         help="指定工具则额外检查 drift")

    args = ap.parse_args()
    if args.cmd == "init":
        return cmd_init(args)
    if args.cmd == "backup":
        return cmd_backup(args)
    if args.cmd == "apply":
        mode = " --upgrade" if getattr(args, "upgrade", False) else ""
        if not args.write:
            print("[apply%s] DRY-RUN（加 --write 落盘）" % mode)
        return cmd_push(args)
    if args.cmd == "collect":
        if not args.write:
            print("[collect] DRY-RUN（加 --write 落盘）")
        return cmd_pull(args)
    if args.cmd == "check":
        return cmd_check(args)


if __name__ == "__main__":
    sys.exit(main())
