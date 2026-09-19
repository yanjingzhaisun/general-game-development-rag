---
id: embedding-setup-policy
keywords_en: [embedding, setup, provider, privacy, gitignore]
keywords_zh: [向量模型, 安装, 配置, 隐私, 忽略规则]
summary: 规定安装时由用户选择 embedding 服务，并隔离项目本地配置与向量缓存。
---

# 用户选择 embedding

```rag
kind: design
sources:
  - path: src/general_game_development_rag/embeddings.py
  - path: tools/install_project.py
```

用户需要安装时得到 embedding 提示，并自行选择 API 或本地模型。默认 unconfigured，
无网络请求；用户可明确 disabled 暂缓。安装器提供结构化提示，install.md 和 skill
要求 agent 向用户呈现选择。配置存在不等于连接成功，以 doctor 检查为准。

API 使用兼容 OpenAI 的格式，本地模型由 Ollama 在 loopback 服务中运行。
不自动下载权重，不替用户选择付费 API，不写入密钥。查询与功能/设计文档片段
可发往用户选择的服务；原始代码文件不进入向量化通道。

配置放 ForAI/rag/embedding.toml 并忽略。embedding.example.toml 和 uv.lock 进入 Git，
环境、模型缓存、向量/图数据库、日志及 .env 文件忽略。每个项目独立管理这些文件。

embedding 只增强召回，不参与权威裁决。已配置服务故障不能静默降级；用户可用
--keyword-only 显式继续关键词检索。图扫描不依赖模型服务，保持可离线核验。
