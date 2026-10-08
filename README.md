# farrun

`farrun` 是一个用于提交 Slurm 任务或编译并后台运行 C++ 任务的命令行工具。

> PyPI 上的 `funrun` 已被他人占用。本项目统一使用 **`farrun`** 作为仓库、PyPI
> 发布包、导入包和 CLI 命令名称。

## 安装

```bash
pip install farrun
```

## 最小示例

在工作目录准备 `main.cpp`，然后运行：

```bash
farrun
```

工具会将任务文件复制到 `~/workbench/<时间戳>/`，编译并后台启动程序；若目录中存在
`config.slurm`，则改为提交 `sbatch config.slurm`。没有 `main.cpp` 或 `config.slurm` 时，
命令以非零状态退出。

也可以直接使用 Python API：

```python
from farrun.run import run

if not run():
    raise SystemExit(1)
```

## 任务文件

- `config.slurm`：使用 Slurm 提交任务。
- `main.cpp`：使用 `g++` 编译并后台运行。
- 同目录的 `.h`、`.sh`、`.slurm`、`.f90`、`.dat`、`.json` 会随任务复制。

---

## 关于 farfarfun

[farfarfun](https://github.com/farfarfun) 是一个专注于实用工具库的开源组织，
涵盖云存储、数据处理、AI、多媒体与开发工具链等方向。

- 🏠 组织主页：<https://github.com/farfarfun>
- 📦 PyPI：<https://pypi.org/user/niuliangtao/>
- 📧 联系：farfarfun@qq.com

本项目基于 [MIT](LICENSE) 协议开源。

## 从 ffunrun 迁移

`ffunrun` 已停止维护。请卸载旧包并安装 `farrun`：

```bash
pip uninstall ffunrun
pip install farrun
```

将脚本中的 `funrun` 导入和命令替换为 `farrun`；其余 Python API 保持不变。
