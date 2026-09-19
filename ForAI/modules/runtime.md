---
id: runtime-behavior
keywords_en:
- runtime
- CLI
- graph
- coverage
- probe
keywords_zh:
- 运行器
- 命令行
- 图索引
- 覆盖
- 探针
summary: 描述当前 CLI、文档解析、图构建、确定性扫描与 Git 覆盖检查行为。
---

# 当前运行器

`tools/install_project.py` 为 agent 安装项目级 skill 与运行时，预检冲突后复制，保留并追加 AGENTS.md，写入 install.json 来源记录。完整步骤见根目录 install.md。

每个项目复用 skill 初始化独立运行时；运行代码、uv 依赖锁、环境和 SQLite 均位于自己的 ForAI/rag。项目维护使用 `uv run --directory ForAI/rag python manage.py ...`，不依赖分发仓库。

`tools/build_skill_runtime.py` 生成 skill 携带的源码快照；bootstrap 先预检所有目标文件，再复制缺失文件，拒绝覆盖不同的本地版本。JSON 输出固定 UTF-8，避免 Windows 管道乱码。

- `documents.py` 校验紧凑 frontmatter 和一个 rag YAML 正文块，拒绝重复文档 ID、无效字段与越界来源路径。
- `graph.py` 将文档、代码引用、断言、实体与问题投影至 SQLite；原始代码不入库。
- `sync`、`query`、`scan` 每次完整重建当前工作树图；输入无效时保留已有投影。连接显式关闭，支持 Windows 删除缓存后重建。
- `query` 对关键词按子串计分，进行双向有界图扩展；返回来源路径、关系、结构化断言和相关问题。没有向量召回、中文自动分词或模型调用。
- 功能文档无来源产生 unverified_description；无核验哈希或指纹变化产生 needs_review；不存在的文件产生 missing_source。
- 相同类型、主体、属性与 scope 的 active 断言值不一致时产生候选冲突。proposed/superseded 不参与扫描；没有自动单位转换。
- Python 探针用 AST 读取唯一顶层字面量赋值；额外写入或绑定会保守返回 unresolved。不导入执行项目，不证明变量在生产环境实际生效。
- 探针与 functional 声明不同产生 description_drift；与 design 要求不同产生 design_deviation。不会自动改写任何代码、功能说明或设计。
- `coverage --staged` 仅读取暂存区；`--base REF` 读取 REF 到 HEAD 的聚合差异。变更记录必须在相应差异中，覆盖哈希必须匹配代码 blob；删除使用 deleted。
- 覆盖检查当前使用内置代码后缀集合，不覆盖配置/资源和任意其他语言，不验证变更原因的语义真实性。
- `scan --write-report` 写 ForAI/conflicts/scan.md；report 文档不回流检索。问题 ID 稳定，但处理历史需另存文档。
- CLI 退出码 0 表示成功执行，1 表示覆盖失败或严格扫描有发现，2 表示输入/运行错误。

测试覆盖代码权威与设计偏差分离、指纹变化、范围隔离、幂等重建、删除重命名、查询刷新、暂存区隔离、删除提交和解析失败时保留索引。

v0.1 适用于本地单写入者；并行扫描和原子多文件快照尚未协调。文档 SHA-256 是本轮阅读实现和通过测试后的证据记录，不是自动语义证明。

```rag
kind: functional
sources:
- path: ForAI/rag/manage.py
  sha256: b790a235e2feade1e8c2c41a227a5bb6e14241f3cc820359813b16c2d67381bc
- path: ForAI/rag/src/general_game_development_rag/__init__.py
  sha256: 155a9b2342576f18f516bbc513c252568300e431f3e82f70fca35d2d71db131c
- path: ForAI/rag/src/general_game_development_rag/cli.py
  sha256: e7e651f93d1feaceeb9151f4cf34ac8098e004e643c2595cf01b52c65ebd8797
- path: ForAI/rag/src/general_game_development_rag/coverage.py
  sha256: 26cdc0b26bfb199ae3da06718abc4ba0071c2e4f1acbe9590cf46b18c445ab7c
- path: ForAI/rag/src/general_game_development_rag/documents.py
  sha256: f28d0c09805762bfbe1301dd192b646a0f0bae412d7dbc0429a504a380459bd0
- path: ForAI/rag/src/general_game_development_rag/graph.py
  sha256: b6b7901702453d737da388fed46b4c1ace083c837a5c61646bb4908cf284f6a5
- path: skills/project-code-memory/assets/runtime/manage.py
  sha256: b790a235e2feade1e8c2c41a227a5bb6e14241f3cc820359813b16c2d67381bc
- path: skills/project-code-memory/assets/runtime/src/general_game_development_rag/__init__.py
  sha256: 155a9b2342576f18f516bbc513c252568300e431f3e82f70fca35d2d71db131c
- path: skills/project-code-memory/assets/runtime/src/general_game_development_rag/cli.py
  sha256: e7e651f93d1feaceeb9151f4cf34ac8098e004e643c2595cf01b52c65ebd8797
- path: skills/project-code-memory/assets/runtime/src/general_game_development_rag/coverage.py
  sha256: 26cdc0b26bfb199ae3da06718abc4ba0071c2e4f1acbe9590cf46b18c445ab7c
- path: skills/project-code-memory/assets/runtime/src/general_game_development_rag/documents.py
  sha256: f28d0c09805762bfbe1301dd192b646a0f0bae412d7dbc0429a504a380459bd0
- path: skills/project-code-memory/assets/runtime/src/general_game_development_rag/graph.py
  sha256: b6b7901702453d737da388fed46b4c1ace083c837a5c61646bb4908cf284f6a5
- path: skills/project-code-memory/scripts/bootstrap.py
  sha256: 9cd08aeff5cf2ed8ff9d909cfafca208858a1d5736e2347296d0419f8375f6d1
- path: src/general_game_development_rag/__init__.py
  sha256: 155a9b2342576f18f516bbc513c252568300e431f3e82f70fca35d2d71db131c
- path: src/general_game_development_rag/cli.py
  sha256: e7e651f93d1feaceeb9151f4cf34ac8098e004e643c2595cf01b52c65ebd8797
- path: src/general_game_development_rag/coverage.py
  sha256: 26cdc0b26bfb199ae3da06718abc4ba0071c2e4f1acbe9590cf46b18c445ab7c
- path: src/general_game_development_rag/documents.py
  sha256: f28d0c09805762bfbe1301dd192b646a0f0bae412d7dbc0429a504a380459bd0
- path: src/general_game_development_rag/graph.py
  sha256: b6b7901702453d737da388fed46b4c1ace083c837a5c61646bb4908cf284f6a5
- path: tests/test_distribution.py
  sha256: d14f0c836318a85f227df0b638c94231c2b265c0478426be1fdf4ade06a5da2d
- path: tests/test_memory.py
  sha256: eea3a0b814f5352b8dd1157d0765211e99c41c0dac92ad03b49ed80a1110090c
- path: tools/build_skill_runtime.py
  sha256: 2d72bb59443aa2a79f5786bf8352d63b8678b5586ce4dc63f90b57b259787f18
- path: tools/install_project.py
  sha256: 1b7ad5bcaf7bea4c6fcc7837966954134c53c260df45dc32d75cd5a9275b592f
```
