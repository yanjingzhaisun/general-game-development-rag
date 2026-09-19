# 给项目内 agent 的安装说明

将这套管线安装到**你正在协助的项目**。本仓库只分发 skill 与运行时快照；
每个项目独立拥有源码、依赖锁、文档和数据库。安装后不依赖本仓库所在目录。

## 安装结果

```text
<目标项目>/
├── AGENTS.md                              # 保留原内容，追加记忆工作流入口
├── .agents/skills/project-code-memory/    # 项目自己的完整 skill
└── ForAI/
    ├── index.md                           # AI 阅读入口
    ├── modules/                           # 当前功能说明
    ├── decisions/                         # 设计要求与决策
    ├── changes/                           # 代码变更覆盖记录
    ├── conflicts/                         # 当前报告与处理记录
    └── rag/
        ├── manage.py                      # 自动绑定当前项目根目录
        ├── src/                           # 项目拥有的运行源码
        ├── pyproject.toml
        ├── uv.lock
        ├── install.json                   # 上游版本与来源提交
        ├── .venv/                         # 项目独立环境，不提交
        └── .cache/graph.sqlite3            # 项目独立索引，不提交
```

`.agents/skills/` 是本安装器的项目级存储位置。若你的工具不自动发现此目录，
直接读取其中的 SKILL.md；可以在已有工具入口中添加链接，不需要移动或共享数据库。

## 1. 确认目标和前置条件

阅读目标项目现有的 agent 指令。确定项目根目录：Git 项目可运行
`git rev-parse --show-toplevel`，多项目仓库应使用用户指定的实际项目根。
不要把下载本安装说明所用的临时目录当成目标项目。

需要 Git、uv 和可用的 Python 3.12。首次 `uv run` 可能下载 Python、构建依赖和
PyYAML；目标项目自己的应用无需使用 Python。缺少 uv 时按其
[官方安装文档](https://docs.astral.sh/uv/getting-started/installation/)准备环境。

以下 `<临时目录>`、`<项目绝对路径>` 均由你替换为实际路径；包含空格时加引号。
使用系统临时目录下载发行版，不要往目标项目添加上游 Git remote。

## 2. 获取固定版本并安装

默认使用发行标签 `v0.1.0`；不要默默跟随 main。需要其他版本时使用用户指定的
标签或完整提交，并记录实际解析出的提交 ID。

```text
git clone --depth 1 --branch v0.1.0 https://github.com/yanjingzhaisun/general-game-development-rag.git <临时目录>
git -C <临时目录> rev-parse HEAD
uv run --python 3.12 --no-project <临时目录>/tools/install_project.py --project <项目绝对路径>
```

安装器只复制项目级 skill 和独立运行时，并向 AGENTS.md 追加指定的入口块。
它不安装全局 skill、不推送提交、不设置后台任务，也不覆盖内容不同的现有文件。
如遇冲突，阅读差异并决定迁移；不要删掉已有 ForAI 来绕过检查。

切换到目标项目根目录后运行：

```text
uv run --directory ForAI/rag python manage.py init
uv run --directory ForAI/rag python manage.py sync
uv run --directory ForAI/rag python manage.py scan --write-report --fail-on-issues
```

后续命令只使用目标项目里的文件。安装用的临时克隆不承担运行服务。

## 3. 建立项目自己的第一份记忆

读取 `.agents/skills/project-code-memory/SKILL.md` 和其
`references/document-contract.md`。初始化只生成入口，不会自动理解整个项目。

先阅读项目结构与关键代码，按实际模块创建 ForAI 功能文档、设计文档和变更记录。
每份 Markdown 都包含简短的 `id`、`keywords_en`、`keywords_zh`、`summary`
frontmatter；关系和断言放正文的 rag YAML 块中。不要把上游仓库自身的 ForAI
文档复制成目标项目知识。

功能说明以当前代码和配置为准。先阅读来源，再用本地命令取得指纹并写入文档：

```text
uv run --directory ForAI/rag python manage.py hash src/example.py
uv run --directory ForAI/rag python manage.py query "模块关键词"
uv run --directory ForAI/rag python manage.py scan --write-report
```

设计文档保存目标与约束；实现偏离设计时记录待决事项，不自动把设计改成实现。
第一版只自动核验显式来源、结构化断言和 Python 静态字面值；其他语义需要你阅读
代码判断。新项目初始扫描无问题仅表示骨架有效，不表示项目已被完整建模。

## 4. 纳入目标项目版本控制

保留现有 `.gitignore` 规则；运行时自带规则忽略 `.venv/`、`.cache/` 和字节码。
项目级 skill、运行源码、依赖锁、install.json、AI 文档与入口应进入项目 Git。
若 `.agents` 被项目规则整体忽略，按项目约定加入精准例外，不全局修改 Git 忽略规则。

安装所添加的 Python 运行代码同样需要变更记录：在 `ForAI/changes/` 中记录其来源、
安装版本、代码路径和 SHA-256。格式见 skill 的 document-contract.md；不需要为
分发的每个函数写单独功能文档，可以用一份“项目记忆管线”功能说明关联来源。

在用户授权的提交流程中暂存对应文件后检查：

```text
uv run --directory ForAI/rag python manage.py coverage --staged
```

覆盖检查只认可暂存区里的变更记录与代码 blob。若 Git 会转换换行，记录的哈希
必须与暂存 blob 一致；不要拿未暂存的文档或不同换行的工作文件冒充覆盖。

## 5. 开发后的日常维护

1. 开始任务：读 ForAI/index.md，检索并回到代码证据。
2. 修改代码：更新受影响的功能文档，必要时更新已确认的设计决策。
3. 核验来源后更新指纹和变更覆盖，运行本地 sync 与 scan。
4. 提交前检查 coverage；不要把“指纹变化待核验”直接当作功能冲突。
5. 合并后重新扫描。定期扫描需要项目自行配置 CI 或调度器；本版不自动启用。

退出码 0 表示命令成功，1 表示覆盖失败或严格扫描有问题，2 表示输入或运行错误。
出现问题时报告具体证据和未完成项，不宣称完成语义一致性验证。

## 6. 升级与移除

每个项目可独立固定版本和修改运行源码。升级时读取 install.json，取得新版本，
比较 `.agents/skills/project-code-memory/` 与 `ForAI/rag/` 的代码和依赖差异。
安装器会拒绝覆盖不同文件；显式合并后验证并更新版本记录，不覆盖目标项目的
功能文档、设计决策或冲突处理历史。

移除时先确认哪些文件曾被本地修改，仅移除该管线专属文件和 AGENTS.md 中带
`project-code-memory` 标记的入口块。ForAI 内的项目知识由项目保留。
