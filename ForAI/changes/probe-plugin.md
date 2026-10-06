---
id: probe-plugin-implementation
keywords_en: [probe, reader, plugin, typescript, javascript, kotlin, xml, android]
keywords_zh: [探针, reader, 插件, 类型脚本, JavaScript, 安卓]
summary: 记录可扩展 probe reader 路由与 Python、TS/JS、Kotlin 和 XML 的静态读取实现。
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

第四轮全量验证（Linux、Python 3.12.13、uv 0.12.23）：
`uv run --locked --extra readers pytest -q` 实际输出为 `83 passed in 8.33s`；
uv 在 PATH 中，双项目 runtime 集成测试也执行通过。CI 的项目 runtime 命令使用
--locked --extra readers 执行严格 scan，输出 issues: []。Windows 矩阵保留，
本地 Linux 环境未执行 Windows 作业，仍需 GitHub Actions 实跑确认。
Ruff check 输出 `All checks passed!`，format check 为 `47 files already formatted`。
本轮已运行 tools/build_skill_runtime.py 重新生成 bundle，并审阅同步到 ForAI/rag；
三份源码逐字节一致。使用 ggrag hash 取得源码和测试的新指纹，更新相关 functional
sources 与以下 covers。精确指纹与影响理由如下。

第五轮扩展 Android APK 项目静态探针，范围按用户决策限定为 Kotlin 和 XML。
新增 ts-kotlin，`.kt`/`.kts` 按 Kotlin 路由；tree-sitter grammar 按语言选择，
与 TS/JS 共用遍历和字面值读取，没有复制另一套解析器。支持 const val 与类型注解，
Gradle KTS DSL 中 compileSdk/versionCode 的简单赋值；多重写入、动态表达式和缺失
名称均显式 unresolved。不导入或执行目标项目，也不运行 Gradle。
新增 builtin-xml，仅使用标准库 ElementTree，无 XML 新依赖；局部名及文档命名空间
前缀匹配属性。返回文档序第一个字符串值，证据带 matches；不同值的重复属性增加
ambiguous: true，不把歧义隐藏成唯一值。缺失属性 inspect_code，畸形 XML 显式
inspect_reader。reports_evidence 是 reader 注册的可选扩展，现有 `(path, name)`
入口与 JSON 值返回契约不变，只有选择该扩展的 reader 接收额外 evidence 字典。
唯一新增依赖 tree-sitter-kotlin 放在 readers extra；同步根配置、生成器内嵌配置与
项目 runtime 配置，两份 lock 使用官方 PyPI、未使用 --upgrade，不包含国内镜像。
新增测试覆盖 Kotlin 三种路由、顶层常量的完整版本证据、两个 Gradle KTS 属性、
动态/缺失/多重写入拒绝、grammar 缺失的 install_reader（显式及后缀路由），以及
XML 单匹配、前缀匹配、重复同值与不同值证据、找不到与畸形 XML。
Kotlin 解码单独保留原始字符串反斜杠，区分关键字与同名引用，字符串内容不套用
TS 断言剥除/布尔替换；原始字符串拼接仍属于动态表达式，必须 unresolved。

第五轮验证（Linux、Python 3.12.13、uv 0.12.23）：新增 26 个参数化测试用例，
既有用例全部保留；`uv run --locked --extra readers pytest -q` 实际输出
`109 passed in 8.94s`。Ruff check 为 `All checks passed!`，format check 为
`47 files already formatted`。项目 runtime 严格 scan 返回 `issues: []`；两份 lock
的 `grep -c tuna` 均为 0。已运行构建脚本并逐文件比较三份源码，全部一致；
生成 bundle 与 ForAI/rag 的 pyproject 也一致。相关 functional sources 与 covers
均使用阅读后的 ggrag hash 结果更新；未 commit、未 push。Windows 尚需 CI 实跑。

```rag
kind: change
covers:
- path: skills/project-code-memory/references/document-contract.md
  sha256: 43a7864b7f820ac24da83f78d9fdb3f0a54f1abdd77e82824f4de66b113a0608
  reason: 补充 Kotlin/Gradle KTS 和 XML 属性示例，明确匹配数、歧义证据、可选依赖与失败动作。
- path: .github/workflows/ci.yml
  sha256: 2aaa56e829fe73faf0b96285a8070dc4693d96224ead6079ee5a6b2fd42413c9
  reason: CI uv 固定 0.12.23，sync/run 显式启用 readers 并校验锁文件，覆盖双系统矩阵；记录工作树中已有的全分支 push 触发范围，本轮未改 CI 行为。
- path: ForAI/rag/src/general_game_development_rag/documents.py
  sha256: 082c05a9866284b07a1ce0de0a884b2a4663d9b3fcfcb4fd0b73789ad2f938c2
  reason: 只接受统一能力型 probe，拒绝任何 type 字段并提供改写指引；必要路径/符号校验不变。
- path: ForAI/rag/src/general_game_development_rag/graph.py
  sha256: 482b45b6696bc72ad08c8008b9eabba9556ca9ab0eaa673bdd7dc15eb5c16b41
  reason: 合并 reader 自报的额外证据，XML matches/ambiguous 随 claim 保存；既有 provenance 和失败分类不变。
- path: ForAI/rag/src/general_game_development_rag/readers.py
  sha256: 3837ecb01aaf766ee9e008c7a824fe26637f5d75127487fb1b5868b0bf768ae3
  reason: 新增 Kotlin 与标准库 XML reader，共享 tree-sitter 遍历，记录 XML 匹配数与歧义；保留原有 reader 契约和失败动作。
- path: ForAI/rag/pyproject.toml
  sha256: e39f08d4df44b6b86add27ae147237b0eda39cd37adfe76305b460f005b5ca5c
  reason: 可选 readers extra 新增 tree-sitter-kotlin；同步根配置、生成器和两份 runtime 配置，不新增主依赖。
- path: ForAI/rag/uv.lock
  sha256: 8e4fc73a4986bd763bce722b3b9849e3e4d8327597cb82c05688d61ad956bdc3
  reason: 用官方 PyPI 增量锁定 tree-sitter-kotlin 1.1.0；未使用 --upgrade，其它依赖版本保持原样。
- path: skills/project-code-memory/assets/runtime/src/general_game_development_rag/documents.py
  sha256: 082c05a9866284b07a1ce0de0a884b2a4663d9b3fcfcb4fd0b73789ad2f938c2
  reason: 由 runtime 构建脚本生成，分发文档校验与核心源码一致。
- path: skills/project-code-memory/assets/runtime/src/general_game_development_rag/graph.py
  sha256: 482b45b6696bc72ad08c8008b9eabba9556ca9ab0eaa673bdd7dc15eb5c16b41
  reason: 合并 reader 自报的额外证据，XML matches/ambiguous 随 claim 保存；既有 provenance 和失败分类不变。
- path: skills/project-code-memory/assets/runtime/src/general_game_development_rag/readers.py
  sha256: 3837ecb01aaf766ee9e008c7a824fe26637f5d75127487fb1b5868b0bf768ae3
  reason: 新增 Kotlin 与标准库 XML reader，共享 tree-sitter 遍历，记录 XML 匹配数与歧义；保留原有 reader 契约和失败动作。
- path: skills/project-code-memory/assets/runtime/pyproject.toml
  sha256: e39f08d4df44b6b86add27ae147237b0eda39cd37adfe76305b460f005b5ca5c
  reason: 可选 readers extra 新增 tree-sitter-kotlin；同步根配置、生成器和两份 runtime 配置，不新增主依赖。
- path: src/general_game_development_rag/documents.py
  sha256: 082c05a9866284b07a1ce0de0a884b2a4663d9b3fcfcb4fd0b73789ad2f938c2
  reason: 只接受统一能力型 probe，拒绝任何 type 字段并提供改写指引；必要路径/符号校验不变。
- path: src/general_game_development_rag/graph.py
  sha256: 482b45b6696bc72ad08c8008b9eabba9556ca9ab0eaa673bdd7dc15eb5c16b41
  reason: 合并 reader 自报的额外证据，XML matches/ambiguous 随 claim 保存；既有 provenance 和失败分类不变。
- path: src/general_game_development_rag/readers.py
  sha256: 3837ecb01aaf766ee9e008c7a824fe26637f5d75127487fb1b5868b0bf768ae3
  reason: 新增 Kotlin 与标准库 XML reader，共享 tree-sitter 遍历，记录 XML 匹配数与歧义；保留原有 reader 契约和失败动作。
- path: pyproject.toml
  sha256: 540dec735486f854f8d6b3cb96fac3af8dfba8d6e13a59290b099778ce5d8f45
  reason: 可选 readers extra 新增 tree-sitter-kotlin；同步根配置、生成器和两份 runtime 配置，不新增主依赖。
- path: uv.lock
  sha256: f20fdc282ae2eeab778efb7ff4a52d37d2ed72641429076c6e8d02072982cd3c
  reason: 用官方 PyPI 增量锁定 tree-sitter-kotlin 1.1.0；未使用 --upgrade，其它依赖版本保持原样。
- path: tests/test_memory.py
  sha256: 657f1e79be60cfffbe0e726b58573ec9f226d49902a40d58999e9b79c787a453
  reason: 新增 Kotlin 路由/版本证据、Gradle KTS 字面量和缺失依赖测试；覆盖 XML 属性、命名空间、重复匹配与解析失败，未削弱既有测试。
- path: tools/build_skill_runtime.py
  sha256: 40adfd95eced54f5810bd77145b5a446c2afac14d0e8342c6789e8d72dfab8c9
  reason: 可选 readers extra 新增 tree-sitter-kotlin；同步根配置、生成器和两份 runtime 配置，不新增主依赖。
```
