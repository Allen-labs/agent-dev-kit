---
name: commit
description: 提交前自查 + 规范化提交。用户说"提交一下/commit"时使用。
argument-hint: "[提交说明]"
---

# Commit

提交前对本次改动做自查，再按规范提交。

## 自查清单（发现问题先列出，询问是否继续）

- [ ] 改动的文件里有没有遗留 `TODO` / `FIXME`（属于本次任务的除外）
- [ ] 有没有 `console.log` / `print` / `debugger` 调试残留
- [ ] 有没有被注释掉的旧代码块
- [ ] 有没有忘记关闭的测试开关（`it.only` / `test.skip` / `@pytest.mark.skip`）
- [ ] `git status` 里有没有意外文件（.env、构建产物、临时文件）

## 提交

- 若无问题，用 Conventional Commits 格式提交：`<type>: <简述>`
- 类型：`feat` / `fix` / `refactor` / `docs` / `test` / `chore` / `perf`
- 简述用中文或英文均可，但要具体（如 `fix: 修正登录 token 刷新`），不要写"更新代码"
- 提交说明：$ARGUMENTS（未提供则根据改动自动生成）
