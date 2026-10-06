---
id: probe-plugin-implementation
keywords_en: [probe, reader, plugin, typescript, javascript]
keywords_zh: [探针, reader, 插件, 类型脚本, JavaScript]
summary: 记录可扩展 probe reader 路由和 TS/JS 静态字面量读取实现。
---

# Probe 插件化

将 probe 路由统一为 capability、language 和 reader；拒绝已废弃的 type 字段，
增加 Python AST 与命令 reader 契约，以及可选 tree-sitter TS/JS reader。结果显式记录
reader、实现版本与精度；失败统一为带动作的 `probe_unresolved`。分发 skill runtime，
同步 ForAI/rag 项目副本和可选依赖锁文件。测试覆盖显式/隐式路由、失败动作、TS 声明
形式、废弃字段报错、所有成功探针的 provenance 和 bundle 一致性。

前两轮验收修正（历史，保留旧格式的要求已由第四轮取代）：未注册 reader 名及无匹配注册项改为 inspect_reader，enable_reader 仅用于
注册项存在但未启用。新格式 probe_evidence 增加 reader 自报的 dependencies，使用
已安装发行包版本元数据记录 tree-sitter、tree-sitter-typescript；缺少元数据的包不填
版本，全部取不到时保留空映射。旧 python_literal 的 claim JSON 不增字段。
新增图级测试分别检查未注册与已注册未启用的动作；TS 路由测试精确断言两项依赖版本，
缺少元数据测试覆盖空映射与部分已知版本，旧格式测试加强为完整 JSON 的逐字节比较。

第三轮修正 CI：Ubuntu/Windows 矩阵将 setup-uv 固定为生成锁文件的 0.12.23，
sync 与后续 run 均显式选择 --extra readers 和 --locked。Linux 独立临时环境实测：
uv sync --locked --extra readers 安装两项依赖后，默认 uv run pytest 的 JS reader
测试输出 1 passed in 0.27s，随后两包仍可导入；此版本默认 run 未卸载 extra。
最终 CI 使用显式 extra 参数，独立环境再执行 --locked --extra readers 的缺失依赖
测试得到 2 passed in 0.24s，且测试后真实依赖仍在。缺失依赖测试只模拟 tree_sitter
导入失败，覆盖显式 reader 与按后缀路由，断言 probe_unresolved/install_reader，
claim 没有 observed、没有成功 probe_evidence，也不产生 description_drift。
uv 0.12.23 下主项目 uv sync --locked --extra readers 退出码 0；uv build 成功生成
dist/general_game_development_rag-0.2.0.tar.gz 和对应 py3-none-any.whl。

第四轮由用户明确决定取消 legacy probe 兼容，以消除两套路由及证据形状带来的技术债。
documents.py 拒绝任何包含 type 的 probe，错误明确提示改写为 capability: literal with
language: python；readers.py 删除 legacy 分支，保留 builtin-python 的统一能力/语言路由。
graph.py 删除所有按 type 条件分流的 evidence 和漂移元数据写入逻辑，所有成功探针
都带 reader、版本、精度、语言及依赖版本。未知插件异常兜底统一 inspect_reader，
其它错误分类、读取实现与路由规则保持原样。测试 helper 改用统一字段，旧形状测试
改为 Python 三种路由的完整 evidence 字节校验；新增废弃 type 的拒绝/改写提示测试、
所有 Python/TS/JS 成功 claim 的 provenance 测试和未知异常 action 回归测试。

本轮全量验证（Linux、Python 3.12.13、uv 0.12.23）：
`uv run --locked --extra readers pytest -q` 实际输出为 `83 passed in 8.33s`；
uv 在 PATH 中，双项目 runtime 集成测试也执行通过。CI 的项目 runtime 命令使用
--locked --extra readers 执行严格 scan，输出 issues: []。Windows 矩阵保留，
本地 Linux 环境未执行 Windows 作业，仍需 GitHub Actions 实跑确认。
Ruff check 输出 `All checks passed!`，format check 为 `47 files already formatted`。
本轮已运行 tools/build_skill_runtime.py 重新生成 bundle，并审阅同步到 ForAI/rag；
三份源码逐字节一致。使用 ggrag hash 取得源码和测试的新指纹，更新相关 functional
sources 与以下 covers。精确指纹与影响理由如下。

```rag
kind: change
covers:
- path: .github/workflows/ci.yml
  sha256: 2aaa56e829fe73faf0b96285a8070dc4693d96224ead6079ee5a6b2fd42413c9
  reason: CI uv 固定 0.12.23，sync/run 显式启用 readers 并校验锁文件，覆盖双系统矩阵；记录工作树中已有的全分支 push 触发范围，本轮未改 CI 行为。
- path: ForAI/rag/src/general_game_development_rag/documents.py
  sha256: 082c05a9866284b07a1ce0de0a884b2a4663d9b3fcfcb4fd0b73789ad2f938c2
  reason: 只接受统一能力型 probe，拒绝任何 type 字段并提供改写指引；必要路径/符号校验不变。
- path: ForAI/rag/src/general_game_development_rag/graph.py
  sha256: a48dc01dc4b850797aeb828f2b8952626ed39012421cd00437dc36abd069f13e
  reason: 删除 legacy 条件，统一记录所有成功探针的 provenance 和漂移元数据；未知异常统一 inspect_reader。
- path: ForAI/rag/src/general_game_development_rag/readers.py
  sha256: 09e8674657b4c030450204d0b655d5bb8e8b8bfcdc70814285ea9e58cb8cf83e
  reason: 移除 legacy 直达分支，保留 builtin-python 经统一能力/语言/reader 路由，其余插件逻辑不变。
- path: ForAI/rag/pyproject.toml
  sha256: a78f5a6a016bdb86d8f692426967ffc477bf23d3be7976f1c646f07fccd38d6d
  reason: ForAI/rag runtime 新增可选 readers extra，不把 tree-sitter 加入主依赖。
- path: ForAI/rag/uv.lock
  sha256: 4e53dfa5f4f38329c2032ad72707a5d2eadac713588c2e293ae702c5343cd358
  reason: 锁定 ForAI/rag 可选 tree-sitter reader 依赖及传递依赖。
- path: skills/project-code-memory/assets/runtime/src/general_game_development_rag/documents.py
  sha256: 082c05a9866284b07a1ce0de0a884b2a4663d9b3fcfcb4fd0b73789ad2f938c2
  reason: 由 runtime 构建脚本生成，分发文档校验与核心源码一致。
- path: skills/project-code-memory/assets/runtime/src/general_game_development_rag/graph.py
  sha256: a48dc01dc4b850797aeb828f2b8952626ed39012421cd00437dc36abd069f13e
  reason: 由 runtime 构建脚本生成，分发图投影与核心源码一致。
- path: skills/project-code-memory/assets/runtime/src/general_game_development_rag/readers.py
  sha256: 09e8674657b4c030450204d0b655d5bb8e8b8bfcdc70814285ea9e58cb8cf83e
  reason: 由 runtime 构建脚本生成，将 reader 插件实现纳入可分发 runtime。
- path: skills/project-code-memory/assets/runtime/pyproject.toml
  sha256: a78f5a6a016bdb86d8f692426967ffc477bf23d3be7976f1c646f07fccd38d6d
  reason: 生成 bundle 的可选依赖声明与项目根依赖配置一致。
- path: src/general_game_development_rag/documents.py
  sha256: 082c05a9866284b07a1ce0de0a884b2a4663d9b3fcfcb4fd0b73789ad2f938c2
  reason: 只接受统一能力型 probe，拒绝任何 type 字段并提供改写指引；必要路径/符号校验不变。
- path: src/general_game_development_rag/graph.py
  sha256: a48dc01dc4b850797aeb828f2b8952626ed39012421cd00437dc36abd069f13e
  reason: 删除 legacy 条件，统一记录所有成功探针的 provenance 和漂移元数据；未知异常统一 inspect_reader。
- path: src/general_game_development_rag/readers.py
  sha256: 09e8674657b4c030450204d0b655d5bb8e8b8bfcdc70814285ea9e58cb8cf83e
  reason: 移除 legacy 直达分支，保留 builtin-python 经统一能力/语言/reader 路由，其余插件逻辑不变。
- path: pyproject.toml
  sha256: a7c60fb1852d60d1f4cc31b8d6f184e6e559d93f902aaf4fc0694b92f0f585d6
  reason: 声明可选 readers extra，并兼容当前与既有 Ruff 对可执行位规则的差异。
- path: uv.lock
  sha256: e3f1b1cb8a5ee7d1289756d4c3d549298a09b9e40795299dd2e816af9d38de29
  reason: 锁定仓库开发环境中可选 TS/JS reader 的 tree-sitter 依赖。
- path: tests/test_memory.py
  sha256: dc499c428c7e0922fd7415c3dcab8477a628c7d5eade5ce99a9d0316bad28aa1
  reason: 统一 helper 格式；验证 type 拒绝与改写指引、所有成功 claim 的完整 evidence、未知异常 inspect_reader，保留缺失依赖回归。
- path: tools/build_skill_runtime.py
  sha256: ca5327d6f69dc53a7f5a06599859ab76cc92a6be99786e4b1c1684ddef35b812
  reason: 生成的分发 pyproject 同步可选 readers extra。
```
