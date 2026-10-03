# 更新日志

## [未发布]

### 修复

- 撤销此前误将仓库 `funrun` 整体改名为 `farrun` 的提交：GitHub 仓库名仍是
  `funrun`，源码目录、导入名、CLI 命令统一改回 `funrun`，PyPI 发布名恢复为已占用
  收尾前实际发布中的 `ffunrun`（`funrun` 在 PyPI 上属于他人），并把 `pyproject.toml`
  的 Repository/Releases/Homepage 和 `tool.hatch.build.targets.wheel.packages`
  同步指回 `funrun`/`ffunrun`。
- 补全 `.gitignore`：新增 `*.db`、`*.rar`、`.run/`、`logs/`、`.idea/`、`.vscode/`，
  覆盖 SPEC 要求的构建产物与运行时文件忽略规则。

## [0.1.16] - 2026-09-21

### 新增

- 增加可复现的 `uv.lock` 依赖锁定文件。

### 修复

- 修正发布包名、组织日志依赖和无任务时的非零失败退出。
- 复制、Slurm、编译或启动失败时立即停止，并让 CLI 返回非零状态。

### 变更

- 补充项目安装、任务文件和最小运行示例。
- 任务文件复制改用 Python 标准库，外部命令在任务目录中执行。

### 废弃

- 无。
