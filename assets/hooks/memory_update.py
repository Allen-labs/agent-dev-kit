#!/usr/bin/env python3
"""memory_update.py - 把关键决策/约定回写 .agents/memory（由 agent 在任务中显式调用）。

用法：
  python memory_update.py --topic "DB迁移" --note "user 表加了 idx_email"
  echo "note text" | python memory_update.py --topic "约定"

注意：本脚本不会"自动"抓取决策；agent 需在任务里用 --note/管道喂入内容。
空的 note 会跳过（避免写入无意义行）。post-task 触发器若无内容传入，等同 no-op。
默认写入 <项目根>/.agents/memory/YYYY-MM-DD.md（不存在则创建），带时间戳。
项目根 = 向上找到首个含 .git 或 .agents 的目录，避免子目录运行时记忆落错地方。
"""
import argparse
import os
import sys
from datetime import datetime


def _project_root(start=None):
    d = os.path.abspath(start or os.getcwd())
    while True:
        if os.path.isdir(os.path.join(d, ".git")) or os.path.isdir(os.path.join(d, ".agents")):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            return os.getcwd()
        d = parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--topic", default="note")
    ap.add_argument("--note", default=None)
    ap.add_argument("--dir", default=None,
                    help="记忆目录，默认 <项目根>/.agents/memory")
    args = ap.parse_args()
    args.dir = args.dir or os.path.join(_project_root(), ".agents", "memory")
    note = args.note
    if note is None:
        note = sys.stdin.read().strip()
    if not note:
        print("[memory-update] 无内容，跳过")
        return
    os.makedirs(args.dir, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    path = os.path.join(args.dir, f"{today}.md")
    ts = datetime.now().strftime("%H:%M")
    line = f"- [{ts}] **{args.topic}**: {note}\n"
    with open(path, "a", encoding="utf-8") as f:
        if os.path.getsize(path) == 0:
            f.write(f"# Memory {today}\n\n")
        f.write(line)
    print(f"[memory-update] 已追加到 {path}")


if __name__ == "__main__":
    main()
