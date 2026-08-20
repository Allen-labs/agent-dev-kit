#!/usr/bin/env python3
"""test_agent_kit.py - agent-kit.py 回归测试。

测试核心路径：init → check → apply → collect → check --tool
用临时目录做 fixture，不碰真实环境。

用法：
  python test_agent_kit.py
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

PY = sys.executable
SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "agent-kit.py")


def run_agent_kit(*args, json_mode=False, env=None):
    """运行 agent-kit.py，返回 (returncode, stdout)。env 可覆盖 AGENT_KIT_TOOL_DIR_*。"""
    cmd = [PY, SCRIPT]
    if json_mode:
        cmd.append("--json")
    cmd.extend(args)
    full_env = os.environ.copy()
    if env:
        full_env.update(env)
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60, env=full_env)
    return result.returncode, result.stdout


class TestInitCheck(unittest.TestCase):
    """测试 init + check。"""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="agent-kit-test-")
        self.canonical = os.path.join(self.tmpdir, "canonical")
        # 迷你 fake skills 源：init 用它快照，避免复制真实 ~/.workbuddy/skills
        self.fake_skills = os.path.join(self.tmpdir, "fake-skills")
        os.makedirs(os.path.join(self.fake_skills, "mini-skill"))
        with open(os.path.join(self.fake_skills, "mini-skill", "SKILL.md"),
                  "w", encoding="utf-8") as f:
            f.write("---\nname: mini-skill\ndescription: mini\n---\n# mini\n")
        self.env = {"AGENT_KIT_SKILLS_DIR": self.fake_skills}

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_init_creates_canonical(self):
        """init 应该创建 canonical 仓库，含 AGENTS.md / flow.md / skills/。"""
        rc, out = run_agent_kit("init", self.canonical, env=self.env)
        self.assertEqual(rc, 0, "init 应该成功")
        self.assertTrue(os.path.isfile(os.path.join(self.canonical, "AGENTS.md")))
        self.assertTrue(os.path.isfile(os.path.join(self.canonical, "flow.md")))
        self.assertTrue(os.path.isdir(os.path.join(self.canonical, "skills")))
        self.assertTrue(os.path.isfile(os.path.join(self.canonical, "mcp", "mcp.servers.json")))

    def test_check_after_init(self):
        """init 后 check 应该返回 overall: ok。"""
        run_agent_kit("init", self.canonical, env=self.env)
        rc, out = run_agent_kit("check", "--canonical", self.canonical,
                                json_mode=True, env=self.env)
        self.assertEqual(rc, 0, "check 应该成功")
        data = json.loads(out)
        self.assertEqual(data["data"]["overall"], "ok",
                         "init 后 canonical 应该健康")

    def test_check_detects_missing_agents_md(self):
        """check 应该检测到 AGENTS.md 缺失。"""
        os.makedirs(self.canonical)
        rc, out = run_agent_kit("check", "--canonical", self.canonical, json_mode=True)
        data = json.loads(out)
        self.assertIn("AGENTS.md 缺失", data["data"]["agents_md"])
        self.assertEqual(data["data"]["overall"], "issues")


class TestApplyCollect(unittest.TestCase):
    """测试 apply + collect（用临时工具目录模拟）。"""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="agent-kit-test-")
        self.canonical = os.path.join(self.tmpdir, "canonical")
        self.fake_tool = os.path.join(self.tmpdir, "fake-tool")
        os.makedirs(os.path.join(self.fake_tool, "skills"))
        # 迷你 fake skills 源（init 快照用），避免复制真实环境
        self.fake_skills = os.path.join(self.tmpdir, "fake-skills")
        os.makedirs(os.path.join(self.fake_skills, "mini-skill"))
        with open(os.path.join(self.fake_skills, "mini-skill", "SKILL.md"),
                  "w", encoding="utf-8") as f:
            f.write("---\nname: mini-skill\ndescription: mini\n---\n# mini\n")
        self.env = {"AGENT_KIT_TOOL_DIR_WORKBUDDY": self.fake_tool,
                    "AGENT_KIT_SKILLS_DIR": self.fake_skills}
        run_agent_kit("init", self.canonical, env=self.env)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _add_skill(self, name, content):
        sk = os.path.join(self.canonical, "skills", name)
        os.makedirs(sk)
        with open(os.path.join(sk, "SKILL.md"), "w", encoding="utf-8") as f:
            f.write(content)
        return sk

    def test_apply_dry_run_no_write(self):
        """apply 不带 --write 不应该落盘（regression: 假 dry-run bug）。"""
        self._add_skill("dryrun-probe",
                        "---\nname: dryrun-probe\ndescription: probe\n---\n# probe\n")
        rc, out = run_agent_kit("apply", "--canonical", self.canonical,
                                "--tool", "workbuddy", env=self.env)
        self.assertEqual(rc, 0)
        self.assertIn("DRY-RUN", out)
        # 关键断言：dry-run 后工具目录里不该出现新 skill
        self.assertFalse(
            os.path.exists(os.path.join(self.fake_tool, "skills", "dryrun-probe")),
            "dry-run 不应落盘新 skill")

    def test_apply_upgrade_updates_stale_skill(self):
        """canonical 更新后，apply --upgrade 应覆盖工具侧旧副本
        （regression: manifest 幂等 bug——旧实现用 manifest 比对，
        manifest 刷新后 apply 永远 skip 旧副本）。"""
        # 1. canonical 放 v1 skill，apply 到 fake tool
        sk = self._add_skill("stale-probe",
                             "---\nname: stale-probe\ndescription: v1\n---\nv1 content\n")
        rc, _ = run_agent_kit("apply", "--canonical", self.canonical,
                              "--tool", "workbuddy", "--write", env=self.env)
        self.assertEqual(rc, 0)
        dst = os.path.join(self.fake_tool, "skills", "stale-probe", "SKILL.md")
        self.assertTrue(os.path.isfile(dst), "apply --write 应创建 skill")
        self.assertIn("v1 content", open(dst, encoding="utf-8").read())

        # 2. canonical 更新为 v2（canonical 是真相源，直接改）
        with open(os.path.join(sk, "SKILL.md"), "w", encoding="utf-8") as f:
            f.write("---\nname: stale-probe\ndescription: v2\n---\nv2 content\n")

        # 3. apply --upgrade：工具侧还是 v1，应被覆盖为 v2
        rc, out = run_agent_kit("apply", "--canonical", self.canonical,
                                "--tool", "workbuddy", "--upgrade", "--write",
                                env=self.env)
        self.assertEqual(rc, 0)
        self.assertIn("modified", out, "upgrade 应把旧副本标记为 modified")
        content = open(dst, encoding="utf-8").read()
        self.assertIn("v2 content", content)
        self.assertNotIn("v1 content", content)

    def test_collect_updates_existing_skill(self):
        """工具侧内容与 canonical 不同时，collect 应更新 canonical（工具侧为准）。"""
        # 1. canonical v1 → apply 到 tool
        self._add_skill("upd-probe",
                        "---\nname: upd-probe\ndescription: v1\n---\nv1 content\n")
        run_agent_kit("apply", "--canonical", self.canonical,
                      "--tool", "workbuddy", "--write", env=self.env)
        # 2. 工具侧改 v2（模拟在工具里开发/修改）
        tsk = os.path.join(self.fake_tool, "skills", "upd-probe", "SKILL.md")
        with open(tsk, "w", encoding="utf-8") as f:
            f.write("---\nname: upd-probe\ndescription: v2\n---\nv2 content\n")
        # 3. collect 应把 v2 回灌 canonical
        rc, out = run_agent_kit("collect", "--canonical", self.canonical,
                                "--tool", "workbuddy", "--write", env=self.env)
        self.assertEqual(rc, 0)
        self.assertIn("updated", out)
        csk = os.path.join(self.canonical, "skills", "upd-probe", "SKILL.md")
        self.assertIn("v2 content", open(csk, encoding="utf-8").read(),
                      "collect 应把工具侧的新内容更新到 canonical")

    def test_collect_ignores_pycache(self):
        """collect 不应把 __pycache__/*.pyc 收进 canonical。"""
        sk = os.path.join(self.fake_tool, "skills", "pycache-probe")
        os.makedirs(os.path.join(sk, "scripts", "__pycache__"))
        with open(os.path.join(sk, "SKILL.md"), "w", encoding="utf-8") as f:
            f.write("---\nname: pycache-probe\ndescription: probe\n---\n# probe\n")
        with open(os.path.join(sk, "scripts", "__pycache__", "x.pyc"), "wb") as f:
            f.write(b"\x00")
        rc, _ = run_agent_kit("collect", "--canonical", self.canonical,
                              "--tool", "workbuddy", "--write", env=self.env)
        self.assertEqual(rc, 0)
        self.assertTrue(
            os.path.isdir(os.path.join(self.canonical, "skills", "pycache-probe")))
        self.assertFalse(
            os.path.exists(os.path.join(self.canonical, "skills", "pycache-probe",
                                        "scripts", "__pycache__")),
            "collect 不应带 __pycache__ 垃圾")

    def test_apply_distributes_commands(self):
        """apply 应把 commands 资产分发到各工具（claude/cursor/codex）。"""
        # init 已把 assets/commands 复制进 canonical
        cmds = os.path.join(self.canonical, "commands")
        self.assertTrue(os.path.isdir(cmds), "init 应带 commands 资产")
        # claude → .claude/commands/
        env = dict(self.env)
        env["AGENT_KIT_TOOL_DIR_CLAUDE"] = self.fake_tool
        rc, _ = run_agent_kit("apply", "--canonical", self.canonical,
                              "--tool", "claude", "--write", env=env)
        self.assertEqual(rc, 0)
        dst = os.path.join(self.fake_tool, "commands")
        self.assertTrue(os.path.isfile(os.path.join(dst, "commit.md")),
                        "claude 应有 commit 命令")
        self.assertTrue(os.path.isfile(os.path.join(dst, "review.md")))
        self.assertTrue(os.path.isfile(os.path.join(dst, "test.md")))

    def test_init_from_url(self):
        """init --from 应从远程/本地 git 仓库引导下载 canonical（新机器复原）。"""
        # 建一个"远程"仓库（本地 git 仓库模拟），放一个文件 + commit
        remote = os.path.join(self.tmpdir, "remote-canonical")
        os.makedirs(os.path.join(remote, "skills", "seed"))
        with open(os.path.join(remote, "skills", "seed", "SKILL.md"), "w") as f:
            f.write("---\nname: seed\ndescription: seed\n---\n# seed\n")
        with open(os.path.join(remote, "AGENTS.md"), "w") as f:
            f.write("# Demo\n\n## Commands\n- `test`\n")
        subprocess.run(["git", "init", "-q", remote], check=True)
        subprocess.run(["git", "-C", remote, "add", "-A"], check=True)
        subprocess.run(["git", "-C", remote, "-c", "user.name=t", "-c",
                        "user.email=t@t", "commit", "-qm", "seed"], check=True)
        # init --from 到新目录
        target = os.path.join(self.tmpdir, "bootstrapped")
        rc, out = run_agent_kit("init", target, "--from", remote)
        self.assertEqual(rc, 0, "init --from 应成功: " + out)
        self.assertTrue(os.path.isfile(os.path.join(target, "AGENTS.md")),
                        "引导下载应包含远程文件")
        self.assertTrue(os.path.isfile(os.path.join(target, "skills", "seed", "SKILL.md")))
        # 目标非空应拒绝
        rc2, _ = run_agent_kit("init", target, "--from", remote)
        self.assertNotEqual(rc2, 0, "非空目标应拒绝")

    def test_apply_tool_all(self):
        """apply --tool all 应遍历分发到全部 6 个工具（regression: SKILL.md 声称但缺失）。"""
        env = dict(self.env)
        for t in ("workbuddy", "claude", "cursor", "codex", "opencode", "zed"):
            env["AGENT_KIT_TOOL_DIR_" + t.upper()] = os.path.join(self.tmpdir, "fake-" + t)
        rc, _ = run_agent_kit("apply", "--canonical", self.canonical,
                              "--tool", "all", "--write", env=env)
        self.assertEqual(rc, 0, "apply --tool all 应成功")
        for t in ("claude", "cursor", "codex"):
            cmds = os.path.join(self.tmpdir, "fake-" + t,
                                "commands" if t != "codex" else "prompts")
            self.assertTrue(os.path.isfile(os.path.join(cmds, "commit.md")),
                            "%s 应收到命令" % t)

    def test_apply_distributes_agents(self):
        """apply 应把 agents 子代理资产分发到 Claude 的 .claude/agents/。"""
        # init 已把 assets/agents 复制进 canonical
        agents = os.path.join(self.canonical, "agents")
        self.assertTrue(os.path.isdir(agents), "init 应带 agents 资产")
        env = dict(self.env)
        env["AGENT_KIT_TOOL_DIR_CLAUDE"] = self.fake_tool
        rc, _ = run_agent_kit("apply", "--canonical", self.canonical,
                              "--tool", "claude", "--write", env=env)
        self.assertEqual(rc, 0)
        dst = os.path.join(self.fake_tool, "agents")
        self.assertTrue(os.path.isfile(os.path.join(dst, "code-reviewer.md")),
                        "claude 应有 code-reviewer 子代理")
        self.assertTrue(os.path.isfile(os.path.join(dst, "verification-runner.md")),
                        "claude 应有 verification-runner 子代理")

    def test_apply_rules_to_cursor_mdc(self):
        """canonical/rules 的作用域规则应翻译为 .cursor/rules/*.mdc（scope→globs）。"""
        # canonical/rules 加一个作用域规则
        os.makedirs(os.path.join(self.canonical, "rules"), exist_ok=True)
        with open(os.path.join(self.canonical, "rules", "frontend.md"),
                  "w", encoding="utf-8") as f:
            f.write('---\nname: frontend\ndescription: React 组件约定\n'
                    'scope: "**/*.{ts,tsx}"\n---\n\n- 函数组件优先\n')
        env = dict(self.env)
        fake_cursor = os.path.join(self.tmpdir, "fake-cursor")
        env["AGENT_KIT_TOOL_DIR_CURSOR"] = fake_cursor
        rc, _ = run_agent_kit("apply", "--canonical", self.canonical,
                              "--tool", "cursor", "--write", env=env)
        self.assertEqual(rc, 0)
        mdc = os.path.join(fake_cursor, "rules", "frontend.mdc")
        self.assertTrue(os.path.isfile(mdc), "作用域规则应翻译成 .mdc")
        content = open(mdc, encoding="utf-8").read()
        self.assertIn('globs: ["**/*.{ts,tsx}"]', content,
                      "scope 应翻译为 globs")

    def test_backup_creates_backup_dir(self):
        """backup 应该创建备份目录（用 fake 工具目录，隔离真实环境）。"""
        # fake tool 里放点内容
        os.makedirs(os.path.join(self.fake_tool, "skills", "demo"), exist_ok=True)
        with open(os.path.join(self.fake_tool, "skills", "demo", "SKILL.md"),
                  "w", encoding="utf-8") as f:
            f.write("---\nname: demo\ndescription: demo\n---\n# demo\n")
        backup_dir = os.path.join(self.tmpdir, "backup")
        rc, out = run_agent_kit("backup", "--tool", "workbuddy",
                                "--dir", backup_dir, env=self.env)
        self.assertEqual(rc, 0)
        # 备份目录里应有 skills/demo
        self.assertTrue(
            os.path.isfile(os.path.join(backup_dir, "skills", "demo", "SKILL.md")),
            "backup 应备份 fake tool 的 skills")


class TestSecretScan(unittest.TestCase):
    """测试 check 的泄密扫描。"""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="agent-kit-test-")
        self.canonical = os.path.join(self.tmpdir, "canonical")
        os.makedirs(self.canonical)
        # 创建最小 AGENTS.md
        with open(os.path.join(self.canonical, "AGENTS.md"), "w") as f:
            f.write("# Test\n\n`make build`\n")

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_detects_real_secret(self):
        """check 应该检测到真实密钥。"""
        with open(os.path.join(self.canonical, "config.json"), "w") as f:
            f.write('{"api_key": "sk-abcdefghijklmnopqrstuvwxyz1234567890"}')
        rc, out = run_agent_kit("check", "--canonical", self.canonical, json_mode=True)
        data = json.loads(out)
        self.assertGreater(len(data["data"]["secrets"]), 0, "应该检测到密钥")

    def test_ignores_placeholder(self):
        """check 应该忽略占位符（${KEY} / example 等）。"""
        with open(os.path.join(self.canonical, "config.json"), "w") as f:
            f.write('{"api_key": "${API_KEY}"}')
        rc, out = run_agent_kit("check", "--canonical", self.canonical, json_mode=True)
        data = json.loads(out)
        self.assertEqual(len(data["data"]["secrets"]), 0, "不应该误报占位符")


class TestSkillRefCheck(unittest.TestCase):
    """测试 check 的 skill 引用校验。"""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="agent-kit-test-")
        self.canonical = os.path.join(self.tmpdir, "canonical")
        os.makedirs(self.canonical)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_detects_bad_skill_ref(self):
        """check 应该检测到引用了已禁用的 skill。"""
        with open(os.path.join(self.canonical, "AGENTS.md"), "w") as f:
            f.write("# Test\n\n用 `spec-driven-development` 做规划。\n")
        with open(os.path.join(self.canonical, "flow.md"), "w") as f:
            f.write("# Flow\n\n用 `tdd` 先行。\n")
        rc, out = run_agent_kit("check", "--canonical", self.canonical, json_mode=True)
        data = json.loads(out)
        self.assertGreater(len(data["data"]["skill_refs"]), 0,
                           "应该检测到已禁用 skill 引用")


if __name__ == "__main__":
    unittest.main(verbosity=2)
