import argparse
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path

from farlog import getLogger
from funshell import run_shell

logger = getLogger("funrun")

TASK_SUFFIXES = {".cpp", ".h", ".sh", ".slurm", ".f90", ".dat", ".json"}


class TaskCommandError(RuntimeError):
    """外部任务命令执行失败。"""


def _run_command(command: str, cwd: Path, action: str) -> None:
    result = run_shell(command, cwd=str(cwd))
    if result != "0":
        raise TaskCommandError(
            f"{action}失败，退出状态={result}，工作目录={cwd}，命令={command}"
        )


def run(source_dir: Path | None = None, workbench_dir: Path | None = None) -> bool:
    """复制并提交指定目录中的 Slurm 或 C++ 任务。

    Args:
        source_dir: 任务源目录，默认使用当前目录。
        workbench_dir: 任务工作目录根路径，默认使用 ``~/workbench``。

    Returns:
        找到并提交任务时返回 True，没有任务入口文件时返回 False。

    Raises:
        OSError: 创建目录或复制任务文件失败。
        TaskCommandError: Slurm、编译或启动命令失败。
        ValueError: C++ 任务名称为空或包含不安全字符。
    """
    source_dir = source_dir or Path.cwd()
    slurm_file = source_dir / "config.slurm"
    cpp_file = source_dir / "main.cpp"
    if not slurm_file.exists() and not cpp_file.exists():
        logger.error("找不到 config.slurm 或 main.cpp")
        return False

    timestamp = datetime.now(UTC).astimezone().strftime("%Y%m%d%H%M%S")
    task_dir = (workbench_dir or Path.home() / "workbench") / timestamp
    logger.info("任务主目录：{}", task_dir)
    task_dir.mkdir(parents=True, exist_ok=True)
    for path in source_dir.iterdir():
        if path.is_file() and path.suffix in TASK_SUFFIXES:
            shutil.copy2(path, task_dir / path.name)

    if slurm_file.exists():
        logger.info("检测到 config.slurm，提交 Slurm 任务")
        _run_command("sbatch config.slurm", task_dir, "提交 Slurm 任务")
        return True

    task_suffix = input("请输入任务名字").strip()
    if not task_suffix or any(
        char not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
        for char in task_suffix
    ):
        raise ValueError("任务名称只能包含字母、数字、连字符和下划线")

    task_name = f"lbm-{task_suffix}"
    app_name = f"{task_name}-task.app"
    logger.info("检测到 main.cpp，开始编译")
    _run_command(f"g++ main.cpp -o {app_name}", task_dir, "编译 C++ 任务")
    logger.info("编译完成，开始后台执行")
    _run_command(f"nohup ./{app_name} > output.log 2>&1 &", task_dir, "启动 C++ 任务")
    (task_dir / "task.json").write_text(
        json.dumps({"task_name": task_name}, indent=2), encoding="utf-8"
    )
    return True


def run_task() -> int:
    """启动 funrun 命令行入口，并在任务失败时返回非零退出码。"""
    parser = argparse.ArgumentParser(description="提交 Slurm 或 C++ 任务")
    parser.parse_args()
    try:
        return 0 if run() else 1
    except (OSError, TaskCommandError, ValueError) as exc:
        logger.error("任务提交失败：{}", exc)
        return 1
