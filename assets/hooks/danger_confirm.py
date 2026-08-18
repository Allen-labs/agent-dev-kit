#!/usr/bin/env python3
"""danger_confirm.py - 危险命令确认护栏（pre-tool-use）。

用法：
  python danger_confirm.py "<command>"

命中危险模式则打印警告并以退出码 2 阻断（交由 harness 决定是否需要确认）。
非交互 hook 下默认阻断；确信无误时可用 --allow 放行。
"""
import re
import sys

DANGER = [
    re.compile(r"\brm\s+-rf?\b"),
    re.compile(r"\bgit\s+push\s+.*--force\b"),
    re.compile(r"\bgit\s+reset\s+--hard\b"),
    re.compile(r"\bdrop\s+table\b", re.I),
    re.compile(r"\bdrop\s+database\b", re.I),
    re.compile(r"\btruncate\b", re.I),
    re.compile(r":\(\)\s*\{.*\};:"),
    re.compile(r"\bchmod\s+-R\s+777\b"),
]


def main():
    if len(sys.argv) < 2:
        print('[danger-confirm] 用法: python danger_confirm.py "<command>"')
        sys.exit(0)
    cmd = " ".join(sys.argv[1:])
    for pat in DANGER:
        if pat.search(cmd):
            print(f"[danger-confirm] 危险操作被拦截: 命中 {pat.pattern}")
            print(f"  命令: {cmd}")
            print("  如需执行，请先确认影响范围与回滚方案，再显式放行。")
            sys.exit(2)
    sys.exit(0)


if __name__ == "__main__":
    main()
