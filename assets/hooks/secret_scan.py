#!/usr/bin/env python3
"""secret_scan.py - 提交/工具前密钥泄露扫描。命中真实密钥则退出码 1（阻断）。

用法：
  python secret_scan.py <file1> [file2 ...]
  cat file | python secret_scan.py -        # 从 stdin 读

设计：判定逻辑与 doctor.py 对齐，但作为独立 hook 便于各工具接线。
误报过滤：命中 ${...} / <...> / example / your_ 等占位即放行，避免文档示例误伤。
"""
import os
import re
import sys

PATTERNS = [
    re.compile(r"sk-[a-zA-Z0-9]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"(?i)api[_-]?key\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{20,}"),
    re.compile(r"(?i)(ghp|gho|ghu|ghs|ghr)_[a-zA-Z0-9]{36,}"),
    re.compile(r"(?i)token\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{20,}"),
    re.compile(r"(?i)password\s*[:=]\s*['\"]?.{8,}"),
]
FALSE = (
    "${{", "secrets.", "example", "your_", "your-", "xxxx", "xxxxx",
    "mypassword", "secret123", "changeme", "placeholder", "<", ">",
    "plaintext", "hash(", "await ", "const ", "var ", "let ",
    "process.env", "os.environ", "${",
)


def is_fp(snippet):
    s = snippet.lower()
    return any(tok in s for tok in FALSE)


def scan_text(text):
    hits = []
    for pat in PATTERNS:
        for m in pat.finditer(text):
            snip = m.group(0)
            if len(snip) > 6 and not is_fp(snip):
                hits.append(snip[:50])
    return hits


def main():
    files = sys.argv[1:] or ["-"]
    all_hits = []
    for f in files:
        if f == "-":
            txt = sys.stdin.read()
            all_hits += [("<stdin>", h) for h in scan_text(txt)]
        elif os.path.isfile(f):
            try:
                with open(f, "r", encoding="utf-8", errors="ignore") as fh:
                    txt = fh.read()
            except Exception:
                continue
            all_hits += [(f, h) for h in scan_text(txt)]
    if all_hits:
        print("[secret-scan] 发现疑似真实密钥，阻断：")
        for f, h in all_hits:
            print(f"  {f}: {h}...")
        sys.exit(1)
    print("[secret-scan] ok: 未发现真实密钥")
    sys.exit(0)


if __name__ == "__main__":
    main()
