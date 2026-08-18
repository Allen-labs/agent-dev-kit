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


def run_agent_kit(*args, json_mode=False):
    """运行 agent-kit.py，返回 (returncode, stdout)。"""
    cmd = [PY, SCRIPT]
    if json_mode:
        cmd.append("--json")
    cmd.extend(args)
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    return result.returncode, result.stdout


class TestInitCheck(unittest.TestCase):
    """测试 init + check。"""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="agent-kit-test-")
        self.canonical = os.path.join(self.tmpdir, "canonical")

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_init_creates_canonical(self):
        """init 应该创建 canonical 仓库，含 AGENTS.md / flow.md / skills/。"""
        rc, out = run_agent_kit("init", self.canonical)
        self.assertEqual(rc, 0, "init 应该成功")
        self.assertTrue(os.path.isfile(os.path.join(self.canonical, "AGENTS.md")))
        self.assertTrue(os.path.isfile(os.path.join(self.canonical, "flow.md")))
        self.assertTrue(os.path.isdir(os.path.join(self.canonical, "skills")))
        self.assertTrue(os.path.isfile(os.path.join(self.canonical, "mcp", "mcp.servers.json")))

    def test_check_after_init(self):
        """init 后 check 应该返回 overall: ok。"""
        run_agent_kit("init", self.canonical)
        rc, out = run_agent_kit("check", "--canonical", self.canonical, json_mode=True)
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
        os.makedirs(self.fake_tool)
        run_agent_kit("init", self.canonical)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_apply_dry_run_no_write(self):
        """apply 不带 --write 不应该落盘。"""
        rc, out = run_agent_kit("apply", "--canonical", self.canonical,
                                "--tool", "workbuddy")
        self.assertEqual(rc, 0)
        self.assertIn("DRY-RUN", out)

    def test_backup_creates_backup_dir(self):
        """backup 应该创建备份目录。"""
        # 创建一个假的工具目录
        fake_codex = os.path.join(self.tmpdir, "fake-codex")
        os.makedirs(os.path.join(fake_codex, "skills"))
        with open(os.path.join(fake_codex, "config.toml"), "w") as f:
            f.write("[test]\nkey = \"value\"\n")
        # 临时替换 TOOL_DIRS
        backup_dir = os.path.join(self.tmpdir, "backup")
        rc, out = run_agent_kit("backup", "--tool", "workbuddy", "--dir", backup_dir)
        self.assertEqual(rc, 0)
        # backup 至少备份了 skills 目录
        data = json.loads(out) if out.strip().startswith("{") else None
        # 非_json 模式，检查文件
        self.assertTrue(os.path.isdir(os.path.join(backup_dir, "skills")) or
                        os.path.isfile(os.path.join(backup_dir, "config.toml")))


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
