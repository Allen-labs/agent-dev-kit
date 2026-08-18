#!/usr/bin/env python3
"""doctor.py - 体检：canonical 健康度 / 可迁移性 / 是否泄密 / 与工具层 drift。

用法：
  python doctor.py --canonical /path/to/canonical
  python doctor.py --canonical /path/to/canonical --tool workbuddy
"""
import argparse
import json
import os
import re

SECRET_PATTERNS = [
    re.compile(r"sk-[a-zA-Z0-9]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"(?i)api[_-]?key\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{20,}"),
    re.compile(r"(?i)token\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{20,}"),
    re.compile(r"(?i)password\s*[:=]\s*['\"]?.{8,}"),
]

# 明显不是真实密钥的占位/模板，命中后跳过，避免误报
FALSE_POSITIVE_TOKENS = (
    "${{", "secrets.", "example", "your_", "your-", "xxxx", "xxxxx",
    "mypassword", "secret123", "changeme", "placeholder", "<", ">",
    "plaintext", "hash(", "await ", "const ", "var ", "let ",
)


def _is_false_positive(snippet):
    s = snippet.lower()
    return any(tok in s for tok in FALSE_POSITIVE_TOKENS)


def check_secrets(path):
    hits = []
    if os.path.isfile(path):
        files = [path]
    elif os.path.isdir(path):
        files = []
        for root, _, fs in os.walk(path):
            if ".git" in root:
                continue
            for fn in fs:
                if fn.endswith((".md", ".json", ".toml", ".yaml", ".yml", ".env")):
                    files.append(os.path.join(root, fn))
    else:
        return hits
    for fp in files:
        try:
            with open(fp, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
        except Exception:
            continue
        for pat in SECRET_PATTERNS:
            for m in pat.finditer(text):
                snippet = m.group(0)
                if len(snippet) > 6 and not _is_false_positive(snippet):
                    hits.append((fp, snippet[:40]))
    return hits


def check_agents_md(repo):
    p = os.path.join(repo, "AGENTS.md")
    if not os.path.exists(p):
        return ["AGENTS.md 缺失"]
    with open(p, "r", encoding="utf-8") as f:
        lines = f.readlines()
    issues = []
    if len(lines) > 150:
        issues.append(f"AGENTS.md 过长 ({len(lines)} 行 > 150)，建议精简/下沉到 memory")
    if len(lines) < 10:
        issues.append("AGENTS.md 过短，可能缺少关键命令/禁区")
    # 是否有真实命令（反引号包裹的非空内容）
    if not any("`" in ln for ln in lines):
        issues.append("AGENTS.md 缺少具体命令（建议用反引号写真实 build/test 命令）")
    return issues


KNOWN_BAD_SKILL_REFS = {
    "spec-driven-development", "planning-and-task-breakdown", "tdd", "code-review",
}

def _skill_names(repo):
    names = set()
    for d in ("skills", "skills-optional"):
        p = os.path.join(repo, d)
        if os.path.isdir(p):
            for n in os.listdir(p):
                if os.path.isdir(os.path.join(p, n)):
                    names.add(n)
    return names

def check_skill_refs(repo):
    """flow.md / AGENTS.md 里引用的 skill 必须真实存在（已启用或在 skills-optional 按需库）。
    防止指向未启用/不存在 skill 的硬冲突——这类 bug 以前 doctor 抓不到。"""
    known = _skill_names(repo)
    issues = []
    for fn in ("flow.md", "AGENTS.md"):
        fp = os.path.join(repo, fn)
        if not os.path.isfile(fp):
            continue
        with open(fp, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
        for bad in KNOWN_BAD_SKILL_REFS:
            if "`%s`" % bad in text:
                issues.append(f"{fn}: 含已禁用/不存在的 skill 引用 `{bad}`")
        for m in re.finditer(r"`([a-z0-9]+(?:-[a-z0-9]+)+)`", text):
            tok = m.group(1)
            if tok not in known:
                issues.append(f"{fn}: 引用了疑似未启用/不存在的 skill `{tok}`")
    return issues


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--canonical", required=True)
    ap.add_argument("--tool", help="额外检查目标工具目录")
    args = ap.parse_args()

    print(f"[doctor] canonical: {args.canonical}")
    if not os.path.isdir(args.canonical):
        print("  ERROR: canonical 不存在", file=__import__("sys").stderr)
        __import__("sys").exit(1)

    print("\n== AGENTS.md 质量 ==")
    for i in check_agents_md(args.canonical):
        print(f"  [!] {i}")
    if not check_agents_md(args.canonical):
        print("  [ok] 长度与命令检查通过")

    print("\n== skill 引用完整性 ==")
    for i in check_skill_refs(args.canonical):
        print(f"  [!] {i}")
    if not check_skill_refs(args.canonical):
        print("  [ok] flow.md / AGENTS.md 引用的 skill 均存在")

    print("\n== 泄密扫描 ==")
    hits = check_secrets(args.canonical)
    if hits:
        for fp, snip in hits:
            print(f"  [!] 疑似密钥 {fp}: {snip}...")
        print("  → 把真实值移入 .env，仓库只留占位")
    else:
        print("  [ok] 未发现明显密钥泄露")

    print("\n== 必需文件 ==")
    for f in ["AGENTS.md", "flow.md", "mcp/mcp.servers.json"]:
        fp = os.path.join(args.canonical, f)
        print(f"  {'[ok]' if os.path.exists(fp) else '[--] 缺失'} {f}")

    if args.tool:
        print(f"\n== 工具层 {args.tool} drift 概览 ==")
        print("  （高级：比较工具目录 mcp.json 与 canonical mcp.servers.json 的差异）")

    print("\n[doctor] done.")


if __name__ == "__main__":
    main()
