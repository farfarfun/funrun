import argparse
import json
import os
from datetime import datetime

from funshell import run_shell
from farlog import getLogger

logger = getLogger("funrun")


def run() -> bool:
    """复制并提交当前目录中的 Slurm 或 C++ 任务。

    Returns:
        找到并提交任务时返回 True，否则返回 False。
    """
    task_dir = os.path.join(
        os.path.expanduser("~"), "workbench", datetime.now().strftime("%Y%m%d%H%M%S")
    )
    logger.info(f"任务主目录：{task_dir}")
    os.makedirs(task_dir, exist_ok=True)
    logger.info(f"step1: 复制文件到任务主目录：{task_dir}")
    run_shell(f"cp -r *.cpp *.h *.sh *.slurm *.f90 *.dat *.json {task_dir} 2>/dev/null")

    task_name = "lbm-" + input("请输入任务名字")

    if os.path.exists("config.slurm"):
        logger.info("step2: 检测到config.slurm文件，提交任务")
        run_shell(f"cd {task_dir} && sbatch config.slurm")
        return True
    elif os.path.exists("main.cpp"):
        logger.info("step2: 检测到main.cpp文件，编译")
        run_shell(f"cd {task_dir} && g++ main.cpp -o {task_name}-task.app")
        logger.info("step3: 编译完成，开始执行")
        run_shell(
            f"""cd {task_dir} && nohup ./{task_name}-task.app > output.log 2>&1 &"""
        )
        config = {"task_name": task_name}
        with open(f"{task_dir}/task.json", "w") as fw:
            fw.write(json.dumps(config, indent=2))
        return True

    else:
        logger.error("找不到需要提交的任务")
        return False


def run_task() -> int:
    """启动 funrun 命令行入口，并在任务失败时返回非零退出码。"""

    parser = argparse.ArgumentParser(description="提交 Slurm 或 C++ 任务")
    parser.parse_args()
    return 0 if run() else 1
