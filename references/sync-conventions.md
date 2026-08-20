# canonical 同步约定

> 给开发者看的（不是给 agent）。同步 skill 开发版到 canonical 时必须遵守。

## 禁止 `cp -r src dst`（dst 已存在时）

POSIX 语义下 dst 已存在会生成 `dst/src/` 嵌套，且顶层文件不会被更新。

## 正确做法（三选一）

```bash
# ① 先删目标再拷（最常用）
rm -rf dst && cp -r src dst
# ② rsync（推荐，--delete 清理多余文件）
rsync -a --delete src/ dst/
# ③ 沙箱环境用 python（os 层删除，绕开回收站钩子）
shutil.copytree(src, dst, dirs_exist_ok=True)
```

## 同步后必须验证

`grep` 新函数名 / 新文件存在 / `git status` 干净——防止"拷了但没更新"的静默失败。
