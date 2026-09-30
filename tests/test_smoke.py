"""funrun 公共 API 的轻量测试。

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
并验证没有任务时 CLI 返回失败状态。
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
        check=False,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, (
        f"CLI --help 未能正常退出，stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    assert "usage:" in result.stdout


def test_run_no_task_files_found(monkeypatch, tmp_path):
    """没有任务入口文件时返回 False，且不创建工作目录或执行命令。"""
    from funrun import run as run_module

    run_shell_mock = mock.Mock()
    monkeypatch.setattr(run_module, "run_shell", run_shell_mock)
    workbench = tmp_path / "workbench"

    assert run_module.run(tmp_path, workbench) is False
    assert not workbench.exists()
    run_shell_mock.assert_not_called()


def test_run_config_slurm_branch(monkeypatch, tmp_path):
    """Slurm 分支复制任务文件，并在任务目录执行 sbatch。"""
    from funrun import run as run_module

    source = tmp_path / "source"
    source.mkdir()
    (source / "config.slurm").write_text("#!/bin/bash", encoding="utf-8")
    run_shell_mock = mock.Mock(return_value="0")
    monkeypatch.setattr(run_module, "run_shell", run_shell_mock)

    assert run_module.run(source, tmp_path / "workbench") is True

    task_dir = next((tmp_path / "workbench").iterdir())
    assert (task_dir / "config.slurm").exists()
    run_shell_mock.assert_called_once_with("sbatch config.slurm", cwd=str(task_dir))


def test_run_main_cpp_branch(monkeypatch, tmp_path):
    """C++ 分支依次编译、启动并写出 task.json。"""
    from funrun import run as run_module

    source = tmp_path / "source"
    source.mkdir()
    (source / "main.cpp").write_text("int main() {}", encoding="utf-8")
    (source / "input.dat").write_text("data", encoding="utf-8")
    run_shell_mock = mock.Mock(return_value="0")
    monkeypatch.setattr(run_module, "run_shell", run_shell_mock)
    monkeypatch.setattr("builtins.input", lambda *_a, **_k: "test-task")

    assert run_module.run(source, tmp_path / "workbench") is True

    task_dir = next((tmp_path / "workbench").iterdir())
    assert (task_dir / "input.dat").read_text(encoding="utf-8") == "data"
    assert '"task_name": "lbm-test-task"' in (task_dir / "task.json").read_text()
    assert run_shell_mock.call_args_list == [
        mock.call("g++ main.cpp -o lbm-test-task-task.app", cwd=str(task_dir)),
        mock.call(
            "nohup ./lbm-test-task-task.app > output.log 2>&1 &",
            cwd=str(task_dir),
        ),
    ]


def test_run_reports_copy_failure(monkeypatch, tmp_path):
    """复制失败必须保留 OSError 并停止执行。"""
    from funrun import run as run_module

    (tmp_path / "main.cpp").write_text("int main() {}", encoding="utf-8")
    monkeypatch.setattr(
        run_module.shutil, "copy2", mock.Mock(side_effect=OSError("disk full"))
    )

    with pytest.raises(OSError, match="disk full"):
        run_module.run(tmp_path, tmp_path / "workbench")


def test_run_reports_slurm_failure(monkeypatch, tmp_path):
    """sbatch 非零状态必须抛出带步骤和状态的异常。"""
    from funrun import run as run_module

    (tmp_path / "config.slurm").write_text("#!/bin/bash", encoding="utf-8")
    monkeypatch.setattr(run_module, "run_shell", mock.Mock(return_value="2"))

    with pytest.raises(run_module.TaskCommandError, match="提交 Slurm.*退出状态=2"):
        run_module.run(tmp_path, tmp_path / "workbench")


@pytest.mark.parametrize(
    ("results", "message"),
    [(["3"], "编译 C\\+\\+ 任务失败"), (["0", "4"], "启动 C\\+\\+ 任务失败")],
)
def test_run_reports_cpp_command_failures(monkeypatch, tmp_path, results, message):
    """编译和启动任一步骤失败都必须立即停止。"""
    from funrun import run as run_module

    (tmp_path / "main.cpp").write_text("int main() {}", encoding="utf-8")
    monkeypatch.setattr("builtins.input", lambda *_a, **_k: "test")
    monkeypatch.setattr(run_module, "run_shell", mock.Mock(side_effect=results))

    with pytest.raises(run_module.TaskCommandError, match=message):
        run_module.run(tmp_path, tmp_path / "workbench")


def test_run_task_returns_nonzero_on_command_failure(monkeypatch):
    """CLI 将外部命令异常转换为非零退出状态。"""
    from funrun import run as run_module

    monkeypatch.setattr(
        run_module,
        "run",
        mock.Mock(side_effect=run_module.TaskCommandError("sbatch failed")),
    )
    monkeypatch.setattr(sys, "argv", ["funrun"])

    assert run_module.run_task() == 1


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
