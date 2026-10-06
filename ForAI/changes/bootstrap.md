---
id: bootstrap-implementation
keywords_en:
- bootstrap
- change
- validation
keywords_zh:
- 初始化
- 变更
- 验证
summary: 记录首版 uv Python 图记忆运行器与测试的代码变更覆盖。
---

# 初始实现

新增根目录 install.md 与完整项目安装器，固定 v0.1.0 获取方式；加入 Windows/Linux CI 和分发仓库每周扫描。准备发布 Public GitHub 仓库。

建立 uv Python 包、ggrag CLI、SQLite 图投影、确定性核验与 Git 变更覆盖检查。
增加复用 skill、数据约定与本仓库 ForAI 文档。采用本地运行，无模型凭据和外部数据库服务。
修复 Windows SQLite 连接未关闭导致缓存无法删除的问题。对重复赋值及额外变量写入保守报告探针不确定。

验证：27 项 pytest 测试通过；Ruff 检查通过。实现说明见 ../modules/runtime.md；未来能力见 ../decisions/roadmap.md。

补充实现项目自有运行时分发：skill 包含源码、uv 配置与锁文件；bootstrap 不覆盖本地修改；新增双项目独立环境和数据库测试。CLI 修复 Windows 非 UTF-8 控制台输出，增加回归测试。

以下条目记录本次代码的最终内容指纹；配置、skill 和文档本身也在本次仓库变更中。

```rag
kind: change
covers:
- path: ForAI/rag/manage.py
  sha256: b790a235e2feade1e8c2c41a227a5bb6e14241f3cc820359813b16c2d67381bc
  reason: 初始化项目自有图记忆运行器、安装管线、skill 分发和行为验证；见 ForAI/modules/runtime.md。
- path: ForAI/rag/src/general_game_development_rag/__init__.py
  sha256: 85e85624e6fc79febcaf2dfda1b289cd223434f2c81562b6c81a330b78ed3195
  reason: 初始化项目自有图记忆运行器、安装管线、skill 分发和行为验证；见 ForAI/modules/runtime.md。
- path: ForAI/rag/src/general_game_development_rag/cli.py
  sha256: e7e651f93d1feaceeb9151f4cf34ac8098e004e643c2595cf01b52c65ebd8797
  reason: 初始化项目自有图记忆运行器、安装管线、skill 分发和行为验证；见 ForAI/modules/runtime.md。
- path: ForAI/rag/src/general_game_development_rag/coverage.py
  sha256: 26cdc0b26bfb199ae3da06718abc4ba0071c2e4f1acbe9590cf46b18c445ab7c
  reason: 初始化项目自有图记忆运行器、安装管线、skill 分发和行为验证；见 ForAI/modules/runtime.md。
- path: ForAI/rag/src/general_game_development_rag/documents.py
  sha256: f28d0c09805762bfbe1301dd192b646a0f0bae412d7dbc0429a504a380459bd0
  reason: 初始化项目自有图记忆运行器、安装管线、skill 分发和行为验证；见 ForAI/modules/runtime.md。
- path: ForAI/rag/src/general_game_development_rag/graph.py
  sha256: b6b7901702453d737da388fed46b4c1ace083c837a5c61646bb4908cf284f6a5
  reason: 初始化项目自有图记忆运行器、安装管线、skill 分发和行为验证；见 ForAI/modules/runtime.md。
- path: skills/project-code-memory/assets/runtime/manage.py
  sha256: b790a235e2feade1e8c2c41a227a5bb6e14241f3cc820359813b16c2d67381bc
  reason: 初始化项目自有图记忆运行器、安装管线、skill 分发和行为验证；见 ForAI/modules/runtime.md。
- path: skills/project-code-memory/assets/runtime/src/general_game_development_rag/__init__.py
  sha256: 85e85624e6fc79febcaf2dfda1b289cd223434f2c81562b6c81a330b78ed3195
  reason: 初始化项目自有图记忆运行器、安装管线、skill 分发和行为验证；见 ForAI/modules/runtime.md。
- path: skills/project-code-memory/assets/runtime/src/general_game_development_rag/cli.py
  sha256: e7e651f93d1feaceeb9151f4cf34ac8098e004e643c2595cf01b52c65ebd8797
  reason: 初始化项目自有图记忆运行器、安装管线、skill 分发和行为验证；见 ForAI/modules/runtime.md。
- path: skills/project-code-memory/assets/runtime/src/general_game_development_rag/coverage.py
  sha256: 26cdc0b26bfb199ae3da06718abc4ba0071c2e4f1acbe9590cf46b18c445ab7c
  reason: 初始化项目自有图记忆运行器、安装管线、skill 分发和行为验证；见 ForAI/modules/runtime.md。
- path: skills/project-code-memory/assets/runtime/src/general_game_development_rag/documents.py
  sha256: f28d0c09805762bfbe1301dd192b646a0f0bae412d7dbc0429a504a380459bd0
  reason: 初始化项目自有图记忆运行器、安装管线、skill 分发和行为验证；见 ForAI/modules/runtime.md。
- path: skills/project-code-memory/assets/runtime/src/general_game_development_rag/graph.py
  sha256: b6b7901702453d737da388fed46b4c1ace083c837a5c61646bb4908cf284f6a5
  reason: 初始化项目自有图记忆运行器、安装管线、skill 分发和行为验证；见 ForAI/modules/runtime.md。
- path: skills/project-code-memory/scripts/bootstrap.py
  sha256: 9cd08aeff5cf2ed8ff9d909cfafca208858a1d5736e2347296d0419f8375f6d1
  reason: 初始化项目自有图记忆运行器、安装管线、skill 分发和行为验证；见 ForAI/modules/runtime.md。
- path: src/general_game_development_rag/__init__.py
  sha256: 85e85624e6fc79febcaf2dfda1b289cd223434f2c81562b6c81a330b78ed3195
  reason: 初始化项目自有图记忆运行器、安装管线、skill 分发和行为验证；见 ForAI/modules/runtime.md。
- path: src/general_game_development_rag/cli.py
  sha256: e7e651f93d1feaceeb9151f4cf34ac8098e004e643c2595cf01b52c65ebd8797
  reason: 初始化项目自有图记忆运行器、安装管线、skill 分发和行为验证；见 ForAI/modules/runtime.md。
- path: src/general_game_development_rag/coverage.py
  sha256: 26cdc0b26bfb199ae3da06718abc4ba0071c2e4f1acbe9590cf46b18c445ab7c
  reason: 初始化项目自有图记忆运行器、安装管线、skill 分发和行为验证；见 ForAI/modules/runtime.md。
- path: src/general_game_development_rag/documents.py
  sha256: f28d0c09805762bfbe1301dd192b646a0f0bae412d7dbc0429a504a380459bd0
  reason: 初始化项目自有图记忆运行器、安装管线、skill 分发和行为验证；见 ForAI/modules/runtime.md。
- path: src/general_game_development_rag/graph.py
  sha256: b6b7901702453d737da388fed46b4c1ace083c837a5c61646bb4908cf284f6a5
  reason: 初始化项目自有图记忆运行器、安装管线、skill 分发和行为验证；见 ForAI/modules/runtime.md。
- path: tests/test_distribution.py
  sha256: d14f0c836318a85f227df0b638c94231c2b265c0478426be1fdf4ade06a5da2d
  reason: 初始化项目自有图记忆运行器、安装管线、skill 分发和行为验证；见 ForAI/modules/runtime.md。
- path: tests/test_memory.py
  sha256: eea3a0b814f5352b8dd1157d0765211e99c41c0dac92ad03b49ed80a1110090c
  reason: 初始化项目自有图记忆运行器、安装管线、skill 分发和行为验证；见 ForAI/modules/runtime.md。
- path: tools/build_skill_runtime.py
  sha256: dc9ebb6175aaab6087e47358bfbb362f5c1c4f1d5c61cbf8d66dd8ab7ca498ee
  reason: 初始化项目自有图记忆运行器、安装管线、skill 分发和行为验证；见 ForAI/modules/runtime.md。
- path: tools/install_project.py
  sha256: e426c40d126b639f857e387878a5a39ef44a97f059ad21494262edde6d06f68c
  reason: 初始化项目自有图记忆运行器、安装管线、skill 分发和行为验证；见 ForAI/modules/runtime.md。
```
