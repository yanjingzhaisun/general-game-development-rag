# general-game-development-rag

面向 AI 辅助开发的项目内图记忆系统，基于 uv + Python 3.12 + SQLite。
支持游戏项目，也可用于其他代码仓库。

**项目内 agent 从 [install.md](install.md) 开始安装。** 每个项目得到自己的 skill、
运行代码、uv 环境和数据库；无需共享中央运行服务。

**代码和生效配置是当前功能的权威；设计文档保存目标与约束。** 数据库索引
文档、代码位置及其关系，不复制项目代码，不把设计要求自动改成当前实现。

## 开始使用

```powershell
uv sync
uv run ggrag query "authority 代码"
uv run ggrag scan --write-report --fail-on-issues
uv run pytest -q
```

## 每个项目独立采用

此仓库开发和分发 skill，不充当其他项目的运行服务。每个项目复用 skill 后，
在自己的 `ForAI/rag/` 中拥有运行代码、uv 依赖锁、虚拟环境和数据库。
初始化后无需本仓库路径，也不共享其他项目的记忆。

将 `skills/project-code-memory/` 作为一个完整 skill 安装到所用 AI 工具的技能目录。
首次采用时执行该 skill 的 bootstrap 脚本，例如在本地分发仓库中：

```powershell
uv run python skills/project-code-memory/scripts/bootstrap.py E:/Repo/your-project
# 随后进入目标项目，所有维护命令使用项目自己的运行器：
cd E:/Repo/your-project
uv run --directory ForAI/rag python manage.py init
uv run --directory ForAI/rag python manage.py query "会话"
uv run --directory ForAI/rag python manage.py scan --write-report
```

`ForAI/rag/src/`、`manage.py`、`pyproject.toml`、`uv.lock` 提交到目标项目 Git；
`.venv/` 和 `.cache/` 忽略。代码可以随项目独立演进；重新执行 bootstrap 遇到不同
内容会停止，升级需要显式比较和合并。此仓库初始化没有安装全局工具或个人 skill。

## 已实现的 v0.2

- ForAI Markdown frontmatter 校验，正文结构化关系与断言。
- SQLite 图投影；代码仅保存路径和 SHA-256；缓存可删除重建。
- 关键词召回与有界图扩展，返回来源、关系与相关问题。
- API / 本地 Ollama embedding、文档分块、内容缓存和模型版本隔离。
- 余弦语义召回与关键词排名融合；安装时提示用户选择模型和填写本地配置。
- 源文件消失、指纹变化、同范围断言分歧检查。
- 静态字面值探针，覆盖 Python、TypeScript/JavaScript、Kotlin（含 Gradle `.kts`）与 XML：
  按能力 / 语言 / reader 三层声明，语言可按文件后缀推断；语法级精度显式标注，
  失败一律给出明确动作而不静默降级；区分功能描述过期与设计偏差，不执行目标代码。
- 暂存区或提交范围的代码变更覆盖检查，匹配精确代码哈希。
- 可复用的 [project-code-memory skill](skills/project-code-memory/SKILL.md)。

图索引每次完整重建，向量按内容与模型配置增量计算。尚未实现增量图索引、任意自然语言语义判断、
跨语言语义级符号解析（字面值探针已跨语言，但尚不解析符号引用）、自动冲突历史管理或目标项目后台定时扫描。检索由调用方 AI 用来阅读原文
并生成回答；CLI 只调用用户配置的 embedding 模型。扫描通过不等于证明设计与实现完全一致。

安装器和 init 会提示 embedding 配置。选择 API 或本地 Ollama 后运行
`uv run --directory ForAI/rag python manage.py embedding doctor` 检查连接。
配置说明见 [embedding 指南](skills/project-code-memory/references/embeddings.md)。
实际配置、数据库、环境和密钥文件被忽略，示例配置与 uv.lock 正常提交。

## 命令

```text
ggrag [--root PROJECT] init
ggrag [--root PROJECT] hash FILE...
ggrag [--root PROJECT] sync
ggrag [--root PROJECT] embedding status|configure|doctor
ggrag [--root PROJECT] query TEXT [--limit 5] [--hops 2] [--max-nodes 40] [--keyword-only]
ggrag [--root PROJECT] scan [--write-report] [--fail-on-issues]
ggrag [--root PROJECT] coverage [--staged | --base REF]
```

所有输出为 JSON。退出码：0 成功；1 覆盖失败或严格扫描发现问题；2 输入或运行错误。
文档结构见 [数据约定](skills/project-code-memory/references/document-contract.md)，
实现与设计入口见 [ForAI/index.md](ForAI/index.md)。

## 开发与检查

以下 `uv run ggrag` 是本分发仓库的源码开发入口；采用者使用上面的项目内 manage.py。
更新核心实现后，重新生成 skill 的运行时代码，再同步本仓库的 ForAI/rag 副本。

```powershell
uv run ruff check .
uv run ruff format --check .
uv run pytest -q
uv run python tools/build_skill_runtime.py
uv lock --directory skills/project-code-memory/assets/runtime
uv run ggrag scan --fail-on-issues
# 在准备提交并暂存之后：
uv run ggrag coverage --staged
uv build
```

变更需要同步 ForAI 功能文档与变更记录。哈希确认前先阅读代码；不能为消除警告
盲目刷新。覆盖检查当前只枚举内置代码后缀，配置和资产变更另行人工审查。
钩子、远程仓库、定时器不由初始化命令自动创建。

本分发仓库的 GitHub CI 在 push、PR 和每周一 UTC 01:00 运行 Windows/Linux
测试、构建及记忆扫描；PR 另检查代码变更覆盖。

`main` 是稳定线，`dev` 是长期开发分支：`dev` 上 CI 全绿后，`promote` job 自动把
`main` 快进到 `dev`（仅快进——若 `main` 存在 `dev` 没有的提交，则报错停下而不覆盖）。
目标项目按自身工作流接入。
