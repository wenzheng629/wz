# 云端环境配置备份与 MOOSE 重建说明

本目录保存 Codex 云端环境的配置快照，供 Linux、Windows/WSL2 或其他云端环境重建时参考。应用源码保持不变。安装脚本只完成部分准备工作，不是经过验证的完整 MOOSE 安装器。

## 文件与目录

- `install.sh`：原样复制自 `/workspace/.cloud-setup/install.sh`，安装固定版本 Micromamba、检出 MOOSE、安装并验证 ARS-Codex 技能。
- `start-skill.md`：通过 Codex 环境配置接口完整读取的 `start_skill` 原文。它记录当时的状态，包含历史路径和网络故障说明，不代表新环境的实时状态。
- `/workspace/.cloud-setup/`：脚本创建的外部依赖与下载缓存目录，不属于本仓库。
- `/workspace/.cloud-setup/moose/`：MOOSE 依赖源码。
- `$HOME/.agents/skills/academic-research-suite/`：ARS 技能安装目录；构建 MOOSE 应用本身不依赖该技能。

启动说明还提到了 Nature Skills 和外部 `install-nature.sh`。本次备份的原始 `install.sh` 不安装 Nature Skills，也未备份该独立脚本；它们不是应用构建依赖。不要仅凭启动说明假定这些组件已在新环境安装。

## 平台与前置依赖

原始脚本面向 Linux x86_64，下载的是 `linux-64` Micromamba。Windows 请在 WSL2 的 Ubuntu 内操作，建议将仓库放在 Linux 文件系统；不能直接在 PowerShell 或原生 Windows 中运行。其他架构需要另行适配下载包及校验值。

准备 Bash、Git、curl、tar/bzip2、sha256sum、Python 3、GNU make 和受信任的 CA 证书。Ubuntu 可先安装基础工具：

```bash
sudo apt-get update
sudo apt-get install -y git curl ca-certificates bzip2 tar coreutils python3 build-essential
```

需要访问 GitHub、conda-forge（`conda.anaconda.org`）及 MOOSE 官方依赖源（`https://conda.software.inl.gov/public/`）。使用代理时保留正确代理和 CA 配置，不要关闭 TLS 校验。密码和访问令牌应由环境或凭据管理器提供。

## 运行准备脚本

原始脚本固定使用 `/workspace/.cloud-setup`，保留此逻辑以便追溯。先确保当前用户可以写入 `/workspace`；新建该目录如需管理员权限，可由管理员创建并分配权限。下列示例假定仓库检出在 `/workspace/wz`，使用其他位置时相应调整 `cd` 路径：

```bash
cd /workspace/wz
bash cloud-setup/install.sh
```

脚本固定 Micromamba 2.9.0 并检查 SHA-256；MOOSE 固定到 `2025-09-05-release` / `832d6f35e1f6c687880270d8bcb23156974cc031`；ARS 固定到 `71528d9349bcdacfbe94111f06d9e2d82215a44d`。已有 MOOSE 提交不匹配或技能文件不同会导致检查失败；应检查错误并保留现有文件，不要直接覆盖。

脚本中的部分稀疏检出尚不足以提供完整依赖安装材料；例如查阅官方 `conda/moose-dev` 配方时，需要在外部 MOOSE 检出中额外获取该目录。安装脚本不会自动安装 libMesh、PETSc、WASP，也不会创建完整的 MOOSE Conda 环境。

## 安装剩余 MOOSE 依赖

备份时环境启动说明记载：官方依赖源曾返回代理 CONNECT 403，依赖安装和应用构建尚未完成，回归测试与单元测试没有运行。这是历史记录，重建时应重新检查网络和版本兼容性。

1. 查阅上述 MOOSE 固定版本的官方安装说明和 `conda/moose-dev` 配方。原环境记录的目标是 `moose-dev 2025.04.22`（mpich）；先核对该版本配方及官方渠道可用性，再选择匹配的依赖。
2. 使用 Micromamba/Conda 按官方配方安装编译器、MPI、libMesh、PETSc、WASP 等依赖。将 `MAMBA_ROOT_PREFIX` 和依赖环境保存在 `/workspace/.cloud-setup` 下、仓库之外。
3. 激活依赖环境，检查编译器、MPI、`LIBMESH_DIR` 和 `WASP_DIR` 的实际路径。激活步骤和完整安装命令在原环境中尚未验证，因此此处不提供未经验证的一键依赖安装命令。

## 构建与验证应用

以下命令须在匹配的依赖环境已激活后执行：

```bash
export MOOSE_DIR=/workspace/.cloud-setup/moose
export METHOD=opt
cd /workspace/wz
make -j4
./run_tests
cd unit
make -j4
cd ..
./unit/run_tests
git status --short
```

`-j4` 对应原云端实例的 4 CPU 配额，可根据新环境资源调整。确认回归测试实际执行并通过（包括 diffusion / Exodus gold-file 对比），以及 GoogleTests 实际运行；不能仅以脚本退出或发现测试目录作为成功依据。构建前如遇依赖缺失，应先修复环境，不要通过更改应用源码或跳过测试规避问题。

## 保存范围

仅提交本目录的脚本和文档。不要加入 MOOSE 依赖源码、Conda 环境、下载缓存、编译产物或已安装 Skills 目录。环境配置中的历史用户名、绝对路径需要按新机器调整；本目录没有保存凭据。`start-skill.md` 是说明快照，在本地不会自动执行或自动注册为 Codex 技能。
