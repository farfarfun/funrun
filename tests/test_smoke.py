"""轻量冒烟测试（smoke tests）——非详尽单测。

funrun 是一个很小的 CLI 工具包：唯一的功能模块 `funrun.run` 会把当前目录下的任务文件
拷贝到 ~/workbench/<timestamp> 下，然后根据是否存在 config.slurm / main.cpp 决定
提交 slurm 作业或编译并后台运行可执行文件。这些行为涉及真实的 shell 命令执行、
文件系统写入、以及交互式 input()，因此本测试通过 unittest.mock 打桩，避免真正
执行 shell 命令 / 写入用户目录 / 阻塞在 input() 上。

覆盖范围：
1. 顶层包 / 子模块可以正常 import。
2. CLI 入口（`funrun` = funrun.run:run_task）在 --help 下能正常退出。
3. 核心函数 run() 在三种分支（有 config.slurm / 有 main.cpp / 都没有）下，
   在打桩掉所有外部副作用（run_shell、os.makedirs、input、文件写入）后可以正常跑完，
   不抛异常。
"""

import subprocess
import sys
from unittest import mock

import pytest


def test_import_top_level_package():
    """顶层包 funrun 可以正常导入。"""
    import funrun

    assert funrun is not None


def test_import_run_submodule():
    """核心子模块 funrun.run 可以正常导入，且公开函数存在。"""
    from funrun import run as run_module

    assert callable(run_module.run)
    assert callable(run_module.run_task)


def test_cli_entrypoint_help():
    """[project.scripts] 声明的 `funrun` CLI 入口在 --help 下能正常退出（exit code 0）。"""
    result = subprocess.run(
        [sys.executable, "-c", "from funrun.run import run_task; run_task()", "--help"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, (
        f"CLI --help 未能正常退出，stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    assert "Usage" in result.stdout


def test_run_no_task_files_found(monkeypatch, tmp_path):
    """run(): 当当前目录既没有 config.slurm 也没有 main.cpp 时，应记录错误但不抛异常。

    打桩掉 run_shell（避免真实 shell 拷贝）、os.makedirs（避免写用户目录）、
    input（避免阻塞等待终端输入）以及 os.path.exists（模拟“找不到任务文件”）。
    """
    from funrun import run as run_module

    monkeypatch.setattr(run_module, "run_shell", mock.Mock())
    monkeypatch.setattr(run_module.os, "makedirs", mock.Mock())
    monkeypatch.setattr("builtins.input", lambda *_a, **_k: "test-task")
    monkeypatch.setattr(run_module.os.path, "exists", lambda *_a, **_k: False)

    logger_mock = mock.Mock()
    monkeypatch.setattr(run_module, "logger", logger_mock)

    run_module.run()

    logger_mock.error.assert_called_once()
    run_module.run_shell.assert_called_once()


def test_run_config_slurm_branch(monkeypatch):
    """run(): 检测到 config.slurm 时应走 sbatch 提交分支，且只调用一次 run_shell 做拷贝
    + 一次 run_shell 做 sbatch 提交（共两次），不触碰真实文件系统/shell。
    """
    from funrun import run as run_module

    run_shell_mock = mock.Mock()
    monkeypatch.setattr(run_module, "run_shell", run_shell_mock)
    monkeypatch.setattr(run_module.os, "makedirs", mock.Mock())
    monkeypatch.setattr("builtins.input", lambda *_a, **_k: "test-task")
    monkeypatch.setattr(
        run_module.os.path, "exists", lambda path: path == "config.slurm"
    )

    logger_mock = mock.Mock()
    monkeypatch.setattr(run_module, "logger", logger_mock)

    run_module.run()

    assert run_shell_mock.call_count == 2
    logger_mock.error.assert_not_called()


def test_run_main_cpp_branch(monkeypatch):
    """run(): 检测到 main.cpp 时应走编译 + 后台执行分支，并写出 task.json。

    打桩掉 run_shell（编译/执行命令）与 open()（写 task.json），避免真实副作用。
    """
    from funrun import run as run_module

    run_shell_mock = mock.Mock()
    monkeypatch.setattr(run_module, "run_shell", run_shell_mock)
    monkeypatch.setattr(run_module.os, "makedirs", mock.Mock())
    monkeypatch.setattr("builtins.input", lambda *_a, **_k: "test-task")
    monkeypatch.setattr(run_module.os.path, "exists", lambda path: path == "main.cpp")

    logger_mock = mock.Mock()
    monkeypatch.setattr(run_module, "logger", logger_mock)

    write_mock = mock.mock_open()
    with mock.patch("builtins.open", write_mock):
        run_module.run()

    # 拷贝 + g++ 编译 + nohup 后台执行，共三次 run_shell 调用
    assert run_shell_mock.call_count == 3
    write_mock().write.assert_called_once()
    logger_mock.error.assert_not_called()


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
