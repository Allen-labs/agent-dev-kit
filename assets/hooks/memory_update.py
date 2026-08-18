#!/usr/bin/env python3
"""memory_update.py - 任务结束自动回写关键决策到 .agents/memory。

用法：
  python memory_update.py --topic "DB迁移" --note "user 表加了 idx_email"
  echo "note text" | python memory_update.py --topic "约定"

默认写入 ./.agents/memory/YYYY-MM-DD.md（不存在则创建），带时间戳。
避免规范漂移：把"这次定的约定"固化下来，下次会话直接读。
"""
import argparse
import os
import sys
from datetime import datetime


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--topic", default="note")
    ap.add_argument("--note", default=None)
    ap.add_argument("--dir", default=".agents/memory")
    args = ap.parse_args()
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
