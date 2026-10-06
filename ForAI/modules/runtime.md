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
- `query` 对关键词按子串计分，与配置的 embedding 余弦召回做 RRF 融合，再进行双向有界图扩展；返回来源路径、关系、语义命中和相关问题。没有中文自动分词或自动答案生成。
- `embedding configure/status/doctor` 管理项目本地配置和连接检查。安装与 init 提示用户选择 API 或本地 Ollama；密钥只通过环境变量读取。未配置时明确标记关键词模式，已配置服务失败则报错，`--keyword-only` 显式跳过。
- `sync` 和 `query` 复用未变化的文档向量，按内容和模型配置隔离缓存。`scan` 不请求 embedding。详见 [embedding 实现](embeddings.md)。
- 功能文档无来源产生 unverified_description；无核验哈希或指纹变化产生 needs_review；不存在的文件产生 missing_source。
- 相同类型、主体、属性与 scope 的 active 断言值不一致时产生候选冲突。proposed/superseded 不参与扫描；没有自动单位转换。
- Probe 只接受 capability、language、reader 统一写法；出现 type 字段明确报错并提示 capability: literal with language: python。reader 注册项声明 kind、模块/入口、precision、能力和语言。builtin-python 的 Python AST、可选 tree-sitter TS/JS 与 Kotlin reader、标准库 XML reader 均仅静态读取，不导入执行项目。未安装、未启用、不兼容、冲突或无法判定均产生带 action 的 probe_unresolved；所有成功探针都记录 reader、版本、precision、language、capability 和 dependencies。
- 探针与 functional 声明不同产生 description_drift；与 design 要求不同产生 design_deviation。不会自动改写任何代码、功能说明或设计。
- `coverage --staged` 仅读取暂存区；`--base REF` 读取 REF 到 HEAD 的聚合差异。变更记录必须在相应差异中，覆盖哈希必须匹配代码 blob；删除使用 deleted。
- TS/JS literal reader 依赖可选 `readers` extra；无该依赖时不会静默跳过探针。
- Android literal reader：`ts-kotlin` 通过可选 tree-sitter-kotlin grammar 读取 `.kt`/`.kts`，与 TS/JS 共用声明遍历；支持 const val、类型注解及 Gradle KTS DSL 块内的 versionCode/compileSdk 等简单赋值。跳过函数/类声明体，动态值或多重写入仍 unresolved，不执行 Kotlin/Gradle、不推断构建变体。缺失 grammar 依赖使用 install_reader。
- `builtin-xml` 仅用标准库 ElementTree 读取 `.xml` 属性，name 可用局部属性名或文档声明的命名空间前缀。按文档序返回第一个字符串值；evidence 总是记录 matches，多个匹配且值不同才记录 ambiguous: true。找不到属性使用 inspect_code；畸形 XML 使用 inspect_reader，不解析资源引用。Python reader 可通过 reports_evidence 选择接收额外的 evidence 字典，不改变原有返回值契约或其它 reader 的证据形状。
- 未注册的 reader 名使用 inspect_reader，只有已注册但未启用的 reader 使用 enable_reader。所有成功 probe_evidence 的 dependencies 按 reader 声明的依赖包名读取已安装版本元数据；缺失的版本留空，不编造。未预期的 reader 异常统一使用 inspect_reader；静态代码读取错误仍使用 inspect_code。
- CI 的 Ubuntu/Windows 矩阵**钉住 runner 镜像**（`ubuntu-24.04` / `windows-2025`，刻意不用 `-latest`，免得镜像在脚下换代）与 uv 0.12.23；sync 与 run 显式选择 readers extra 并校验锁文件，再运行 Ruff、pytest、项目 runtime 扫描与构建。push 到任意分支与 pull_request 都触发（自有仓库，每次推送都要 CI 反馈）。**dev 分支上 validate 两个矩阵全绿后，promote job 自动把 main 快进到 dev**（ff-only；main 若存在 dev 没有的提交则报错停下，绝不覆盖）。测试通过模拟 tree_sitter 导入失败验证 install_reader，失败 claim 不产生 observed 或成功证据。
- 覆盖检查当前使用内置代码后缀集合，不覆盖配置/资源和任意其他语言，不验证变更原因的语义真实性。
- `scan --write-report` 写 ForAI/conflicts/scan.md；report 文档不回流检索。问题 ID 稳定，但处理历史需另存文档。
- CLI 退出码 0 表示成功执行，1 表示覆盖失败、严格扫描有发现或 doctor 尚无可用配置，2 表示输入/运行错误。

测试覆盖代码权威与设计偏差分离、指纹变化、范围隔离、幂等重建、删除重命名、查询刷新、暂存区隔离、删除提交和解析失败时保留索引。

v0.2 适用于本地单写入者；并行扫描和原子多文件快照尚未协调。文档 SHA-256 是本轮阅读实现和通过测试后的证据记录，不是自动语义证明。

```rag
kind: functional
sources:
- path: skills/project-code-memory/references/document-contract.md
  sha256: 43a7864b7f820ac24da83f78d9fdb3f0a54f1abdd77e82824f4de66b113a0608
- path: .github/workflows/ci.yml
  sha256: 9bc690b5de8736fff1b9407ad5eb52fb795f56ab517c6a01d9db2cab503662c9
- path: ForAI/rag/pyproject.toml
  sha256: df66471724b89aa511d0377d1a909fe7f1c0a22411f0bf828f97c3721a97b936
- path: ForAI/rag/uv.lock
  sha256: 8e4fc73a4986bd763bce722b3b9849e3e4d8327597cb82c05688d61ad956bdc3
- path: ForAI/rag/manage.py
  sha256: b790a235e2feade1e8c2c41a227a5bb6e14241f3cc820359813b16c2d67381bc
- path: ForAI/rag/src/general_game_development_rag/__init__.py
  sha256: 85e85624e6fc79febcaf2dfda1b289cd223434f2c81562b6c81a330b78ed3195
- path: ForAI/rag/src/general_game_development_rag/cli.py
  sha256: 9903401e0801aa764734ca7fbdc73396661d86b1bcc9776d6eb28bebb3bad3d5
- path: ForAI/rag/src/general_game_development_rag/coverage.py
  sha256: 26cdc0b26bfb199ae3da06718abc4ba0071c2e4f1acbe9590cf46b18c445ab7c
- path: ForAI/rag/src/general_game_development_rag/documents.py
  sha256: 082c05a9866284b07a1ce0de0a884b2a4663d9b3fcfcb4fd0b73789ad2f938c2
- path: ForAI/rag/src/general_game_development_rag/embeddings.py
  sha256: 6e168e898536b8d092595e45acc71e11febdce6383c81843bdb1a9413c52bc94
- path: ForAI/rag/src/general_game_development_rag/graph.py
  sha256: 482b45b6696bc72ad08c8008b9eabba9556ca9ab0eaa673bdd7dc15eb5c16b41
- path: ForAI/rag/src/general_game_development_rag/readers.py
  sha256: 3837ecb01aaf766ee9e008c7a824fe26637f5d75127487fb1b5868b0bf768ae3
- path: skills/project-code-memory/assets/runtime/manage.py
  sha256: b790a235e2feade1e8c2c41a227a5bb6e14241f3cc820359813b16c2d67381bc
- path: skills/project-code-memory/assets/runtime/src/general_game_development_rag/__init__.py
  sha256: 85e85624e6fc79febcaf2dfda1b289cd223434f2c81562b6c81a330b78ed3195
- path: skills/project-code-memory/assets/runtime/src/general_game_development_rag/cli.py
  sha256: 9903401e0801aa764734ca7fbdc73396661d86b1bcc9776d6eb28bebb3bad3d5
- path: skills/project-code-memory/assets/runtime/src/general_game_development_rag/coverage.py
  sha256: 26cdc0b26bfb199ae3da06718abc4ba0071c2e4f1acbe9590cf46b18c445ab7c
- path: skills/project-code-memory/assets/runtime/src/general_game_development_rag/documents.py
  sha256: 082c05a9866284b07a1ce0de0a884b2a4663d9b3fcfcb4fd0b73789ad2f938c2
- path: skills/project-code-memory/assets/runtime/src/general_game_development_rag/embeddings.py
  sha256: 6e168e898536b8d092595e45acc71e11febdce6383c81843bdb1a9413c52bc94
- path: skills/project-code-memory/assets/runtime/src/general_game_development_rag/graph.py
  sha256: 482b45b6696bc72ad08c8008b9eabba9556ca9ab0eaa673bdd7dc15eb5c16b41
- path: skills/project-code-memory/assets/runtime/src/general_game_development_rag/readers.py
  sha256: 3837ecb01aaf766ee9e008c7a824fe26637f5d75127487fb1b5868b0bf768ae3
- path: skills/project-code-memory/scripts/bootstrap.py
  sha256: 4fd49e5ff0a052e6bec0fc742794f89e35797e311c37f657e9c5dda3873d3c6a
- path: src/general_game_development_rag/__init__.py
  sha256: 85e85624e6fc79febcaf2dfda1b289cd223434f2c81562b6c81a330b78ed3195
- path: src/general_game_development_rag/cli.py
  sha256: 9903401e0801aa764734ca7fbdc73396661d86b1bcc9776d6eb28bebb3bad3d5
- path: src/general_game_development_rag/coverage.py
  sha256: 26cdc0b26bfb199ae3da06718abc4ba0071c2e4f1acbe9590cf46b18c445ab7c
- path: src/general_game_development_rag/documents.py
  sha256: 082c05a9866284b07a1ce0de0a884b2a4663d9b3fcfcb4fd0b73789ad2f938c2
- path: src/general_game_development_rag/embeddings.py
  sha256: 6e168e898536b8d092595e45acc71e11febdce6383c81843bdb1a9413c52bc94
- path: src/general_game_development_rag/graph.py
  sha256: 482b45b6696bc72ad08c8008b9eabba9556ca9ab0eaa673bdd7dc15eb5c16b41
- path: src/general_game_development_rag/readers.py
  sha256: 3837ecb01aaf766ee9e008c7a824fe26637f5d75127487fb1b5868b0bf768ae3
- path: tests/test_distribution.py
  sha256: 1567e3f9051208fdf69ab11c906b1b94a553a35a3ee6fd90f8868077f89a118c
- path: tests/test_embeddings.py
  sha256: 97838b82938d3b0b27acdea1ee377d008795484b51b998e84cd56f8157211ec6
- path: tests/test_memory.py
  sha256: 657f1e79be60cfffbe0e726b58573ec9f226d49902a40d58999e9b79c787a453
- path: tools/build_skill_runtime.py
  sha256: 6d768a407c558198f0bfc6728bdb415cf57f91a6604fa4b573d9c9f36e0ad549
- path: pyproject.toml
  sha256: 9b36b0d8cba18fad369e083d8eea1c512a3dcd0da482b0f5f0054b53257f6471
- path: uv.lock
  sha256: f20fdc282ae2eeab778efb7ff4a52d37d2ed72641429076c6e8d02072982cd3c
- path: skills/project-code-memory/assets/runtime/pyproject.toml
  sha256: df66471724b89aa511d0377d1a909fe7f1c0a22411f0bf828f97c3721a97b936
- path: tools/install_project.py
  sha256: e426c40d126b639f857e387878a5a39ef44a97f059ad21494262edde6d06f68c
```
