---
id: embedding-release-v0.2.0
keywords_en:
- embedding
- release
- installation
- gitignore
keywords_zh:
- 向量模型
- 发布
- 安装
- 忽略规则
summary: 记录 v0.2.0 的 embedding 管线、安装配置提示和本地文件忽略规则。
---

# v0.2.0

增加 API/Ollama embedding、项目本地 TOML 配置与 doctor；实现按内容缓存、模型空间隔离、语义与关键词 RRF 融合。安装与 skill 提示用户选择服务或暂缓；密钥通过环境变量提供。

同步分发包和项目自有运行源码。补充 .gitignore：环境、图/向量数据库、模型缓存、日志、.env、实际 embedding.toml 不入库；示例、源码和依赖锁正常提交。安装保留用户已有配置，沿用冲突预检。

53 项测试覆盖 API/Ollama HTTP 协议、语义召回、缓存失效、维度和错误处理、安装提示、忽略规则与既有记忆行为。配置和 Markdown 文档变更也属于本次发布，见 install.md 和 modules/embeddings.md。

```rag
kind: change
covers:
- path: ForAI/rag/src/general_game_development_rag/__init__.py
  sha256: 58413eee118b3f4f7ee44f841163cc8f0a4d49c0f47916ee6a611daee973b10e
  reason: 增加或同步 embedding 配置、语义检索、安装提示与相应验证；详见 ForAI/modules/embeddings.md。
- path: ForAI/rag/src/general_game_development_rag/cli.py
  sha256: 9903401e0801aa764734ca7fbdc73396661d86b1bcc9776d6eb28bebb3bad3d5
  reason: 增加或同步 embedding 配置、语义检索、安装提示与相应验证；详见 ForAI/modules/embeddings.md。
- path: ForAI/rag/src/general_game_development_rag/documents.py
  sha256: b691a14f55f3af5b99d5d9c5deb81119b977369626f60133f922c5533131bf31
  reason: 增加或同步 embedding 配置、语义检索、安装提示与相应验证；详见 ForAI/modules/embeddings.md。
- path: ForAI/rag/src/general_game_development_rag/embeddings.py
  sha256: 6e168e898536b8d092595e45acc71e11febdce6383c81843bdb1a9413c52bc94
  reason: 增加或同步 embedding 配置、语义检索、安装提示与相应验证；详见 ForAI/modules/embeddings.md。
- path: ForAI/rag/src/general_game_development_rag/graph.py
  sha256: 102b7dbcd139e657cc4e1f05f8b7c18194b2625733fde6883d044d2fe47898f3
  reason: 增加或同步 embedding 配置、语义检索、安装提示与相应验证；详见 ForAI/modules/embeddings.md。
- path: skills/project-code-memory/assets/runtime/src/general_game_development_rag/__init__.py
  sha256: 58413eee118b3f4f7ee44f841163cc8f0a4d49c0f47916ee6a611daee973b10e
  reason: 增加或同步 embedding 配置、语义检索、安装提示与相应验证；详见 ForAI/modules/embeddings.md。
- path: skills/project-code-memory/assets/runtime/src/general_game_development_rag/cli.py
  sha256: 9903401e0801aa764734ca7fbdc73396661d86b1bcc9776d6eb28bebb3bad3d5
  reason: 增加或同步 embedding 配置、语义检索、安装提示与相应验证；详见 ForAI/modules/embeddings.md。
- path: skills/project-code-memory/assets/runtime/src/general_game_development_rag/documents.py
  sha256: b691a14f55f3af5b99d5d9c5deb81119b977369626f60133f922c5533131bf31
  reason: 增加或同步 embedding 配置、语义检索、安装提示与相应验证；详见 ForAI/modules/embeddings.md。
- path: skills/project-code-memory/assets/runtime/src/general_game_development_rag/embeddings.py
  sha256: 6e168e898536b8d092595e45acc71e11febdce6383c81843bdb1a9413c52bc94
  reason: 增加或同步 embedding 配置、语义检索、安装提示与相应验证；详见 ForAI/modules/embeddings.md。
- path: skills/project-code-memory/assets/runtime/src/general_game_development_rag/graph.py
  sha256: 102b7dbcd139e657cc4e1f05f8b7c18194b2625733fde6883d044d2fe47898f3
  reason: 增加或同步 embedding 配置、语义检索、安装提示与相应验证；详见 ForAI/modules/embeddings.md。
- path: skills/project-code-memory/scripts/bootstrap.py
  sha256: 4fd49e5ff0a052e6bec0fc742794f89e35797e311c37f657e9c5dda3873d3c6a
  reason: 增加或同步 embedding 配置、语义检索、安装提示与相应验证；详见 ForAI/modules/embeddings.md。
- path: src/general_game_development_rag/__init__.py
  sha256: 58413eee118b3f4f7ee44f841163cc8f0a4d49c0f47916ee6a611daee973b10e
  reason: 增加或同步 embedding 配置、语义检索、安装提示与相应验证；详见 ForAI/modules/embeddings.md。
- path: src/general_game_development_rag/cli.py
  sha256: 9903401e0801aa764734ca7fbdc73396661d86b1bcc9776d6eb28bebb3bad3d5
  reason: 增加或同步 embedding 配置、语义检索、安装提示与相应验证；详见 ForAI/modules/embeddings.md。
- path: src/general_game_development_rag/documents.py
  sha256: b691a14f55f3af5b99d5d9c5deb81119b977369626f60133f922c5533131bf31
  reason: 增加或同步 embedding 配置、语义检索、安装提示与相应验证；详见 ForAI/modules/embeddings.md。
- path: src/general_game_development_rag/embeddings.py
  sha256: 6e168e898536b8d092595e45acc71e11febdce6383c81843bdb1a9413c52bc94
  reason: 增加或同步 embedding 配置、语义检索、安装提示与相应验证；详见 ForAI/modules/embeddings.md。
- path: src/general_game_development_rag/graph.py
  sha256: 102b7dbcd139e657cc4e1f05f8b7c18194b2625733fde6883d044d2fe47898f3
  reason: 增加或同步 embedding 配置、语义检索、安装提示与相应验证；详见 ForAI/modules/embeddings.md。
- path: tests/test_distribution.py
  sha256: 1567e3f9051208fdf69ab11c906b1b94a553a35a3ee6fd90f8868077f89a118c
  reason: 增加或同步 embedding 配置、语义检索、安装提示与相应验证；详见 ForAI/modules/embeddings.md。
- path: tests/test_embeddings.py
  sha256: 97838b82938d3b0b27acdea1ee377d008795484b51b998e84cd56f8157211ec6
  reason: 增加或同步 embedding 配置、语义检索、安装提示与相应验证；详见 ForAI/modules/embeddings.md。
- path: tools/build_skill_runtime.py
  sha256: 8a96f4a70187ac220710d0e7170c2440d0f5dfce0ad441017ceeb7dff36f9fe8
  reason: 增加或同步 embedding 配置、语义检索、安装提示与相应验证；详见 ForAI/modules/embeddings.md。
- path: tools/install_project.py
  sha256: 36d074c33539aa96ff6b3d7ce3805514470c3aecbb105d24d5324312e616daa3
  reason: 增加或同步 embedding 配置、语义检索、安装提示与相应验证；详见 ForAI/modules/embeddings.md。
```
