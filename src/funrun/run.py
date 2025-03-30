"""
#!/bin/bash
task_root='/work/home/liuc12/workbench'
timestamp=$(date +"%Y%m%d%H%M%S")
task_dir="$task_root/task_$timestamp"

mkdir "$task_dir"
cp -r *.cpp *.h *.sh *.slurm *.f90 *.dat  $task_dir 2>/dev/null
cd "$task_dir"
pwd
#ls -al
sbatch config.slurm
"""

import json
import os
from datetime import datetime

import click
from funbuild.shell import run_shell
from funutil import getLogger

logger = getLogger("funbuild")


@click.command()
def run_task():
    task_dir = os.path.join(
        os.path.expanduser("~"), "workbench", datetime.now().strftime("%Y%m%d%H%M%S")
    )
    logger.info(f"任务主目录：{task_dir}")
    os.makedirs(task_dir, exist_ok=True)
    logger.info(f"step1: 复制文件到任务主目录：{task_dir}")
    run_shell(f"cp -r *.cpp *.h *.sh *.slurm *.f90 *.dat {task_dir} 2>/dev/null")

    task_name = "lbm-" + input("请输入任务名字")

    if os.path.exists("config.slurm"):
        logger.info("step2: 检测到config.slurm文件，提交任务")
        run_shell(f"cd {task_dir} && sbatch config.slurm")
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

    else:
        logger.error("找不到需要提交的任务")
    logger.info("任务提交完成")
