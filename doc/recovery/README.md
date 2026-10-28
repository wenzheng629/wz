# 循环本构文件恢复与备份（2026-10-28）

本提交是从本会话的用户上传附件恢复的备份，不是胡锦方论文单次循环复现完成版。

环境恢复后，`/workspace/wz` 只有初始提交 `0ed0aed585cca8db053a0b86b2db234d419282ec`，工作区无修改、未跟踪或忽略的成果文件。原 `test/tests/hu2025_gp/` 和 `/workspace/hu2025_gp_single_cycle.zip` 均不存在；搜索工作区、临时目录和 Git 不可达对象也未找到它们。无法仅凭这一现象确定丢失原因。

## 已恢复

- `include/materials/Zhu2014Core.h`、`RockfillGeneralizedPlasticity.h`、`src/materials/RockfillGeneralizedPlasticity.C`：用户最后上传的三份本构源码，逐字节保留。
- `test/tests/recovered_uploads/basic/`：等向压缩、三轴压缩、单次循环的输入、用户计算结果 CSV 和检查脚本。
- `test/tests/recovered_uploads/cycle100/`：100 次循环的历史、分段统计和运行统计 CSV。对应的完整输入文件未在本次可恢复附件中找到。
- `test/tests/recovered_uploads/peak_checks/`：围压和历史峰值分支检查的输入、诊断配置、案例元数据和 CSV。
- `tools/recovered_stage1/`：用户上传的 Python 材料点程序、CSV、元数据和验证图 PDF。

`manifest.json` 给出全部 35 个恢复附件的路径、字节数和 SHA-256。结果是用户历史计算输出，本次没有重新运行 MOOSE 生成这些结果。原仓库 `.gitignore` 会忽略 CSV、JSON、PDF，本次仅显式保留列出的必要数据，不修改全局忽略规则。

## 本次验证

- 35 份文件与下载附件逐字节一致；总大小 8,391,831 字节，单文件均低于 GitHub 100 MiB 限制。
- 扫描常见私钥、GitHub token、AWS access key 和明文凭据模式，未发现匹配；这不是全面的安全审计。
- 两份 Python 文件语法解析、JSON 解析、CSV 非空检查通过。
- `python test/tests/recovered_uploads/basic/check_moose.py` 对历史 CSV 检查通过，闭合循环塑性体变为 `0.0006825587654538997`。
- C++17 独立编译并执行了包含 `Zhu2014Core.h`、构造模型及验证默认参数的最小程序。这只是核心头文件编译检查，不是循环模型验证。
- 本次未编译 MOOSE 应用、未重新运行有限元算例，也未验证胡文图 2 复现。

## 使用

在具备匹配 MOOSE 依赖的环境中，先启用 solid_mechanics 模块，例如从仓库根目录运行 `make SOLID_MECHANICS=yes -j2`。本次没有改写原 Makefile。MOOSE 版本接口兼容性仍需实际编译检查。

在 `test/tests/recovered_uploads/basic/` 中运行编译后的 `moosex-opt -i isotropic.i`、`triaxial.i`、`cycle.i`，会重新生成相应输出。为保留本次备份，建议在另一个工作副本中运行。`check_moose.py` 读取其所在目录中的三个 CSV。

材料点程序可运行 `python tools/recovered_stage1/test1.py --out /tmp/zhu2014-new-results`，输出到新目录，避免覆盖历史数据；绘图需要相应 Python 科学计算依赖。

## 未恢复或未纳入

- `test/tests/hu2025_gp/` 和 `hu2025_gp_single_cycle.zip`：当前文件系统及 Git 中找不到，不能报告已备份。需要旧环境快照或原压缩包才能恢复原版本。
- 早先未上传为附件的 Lode 变体、阶段工具和说明：当前工作区找不到，没有根据对话描述重新生成并冒充原文件。
- `cycle100.log`：附件下载服务明确报告超过 32 MiB 传输上限，无法取回。本限制来自附件工具，不是 GitHub 单文件限制。
- Exodus `.e` 输出未纳入此次恢复，已保留用于检查的 CSV；这不是完整场数据备份。
- 论文 PDF 和原邓肯模型参考文件不属于本次新增循环本构备份，未上传。
- 未提交编译产物、Python 缓存或临时文件。

本提交保留现有项目文件，不替换 `main`。分支沿用用户指定的 `feat/hu2025-gp-single-cycle`，但分支名称不代表胡文复现文件已恢复。
