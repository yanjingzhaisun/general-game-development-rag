---
id: project-memory
keywords_en: [project, memory, navigation]
keywords_zh: [项目, 记忆, 导航]
summary: 项目 AI 阅读入口，连接实现记忆与设计记忆。
---

# 项目记忆

功能说明以当前代码和配置为准；设计要求保存意图，不因代码变化自动改写。

- [架构决策](decisions/authority.md)：两类记忆、关系和权威规则。
- [当前实现](modules/runtime.md)：CLI、图索引、扫描与覆盖检查。
- [Embedding 检索](modules/embeddings.md)：API/本地配置、向量缓存和混合召回。
- [后续路线](decisions/roadmap.md)：增量索引、语言适配与定期审计。
- [初始化变更](changes/bootstrap.md)：本轮代码变更与证据哈希。
- [v0.2 变更](changes/embeddings-v0.2.0.md)：embedding 安装提示和 Git 忽略规则。
- [v0.3 变更](changes/probe-plugin.md)：probe 插件化路由，Python/TS-JS/Kotlin/XML 静态读取。

使用 `uv run ggrag query "关键词"` 检索后阅读来源。代码指纹变化只表示需要核验，
不能证明行为变化。运行 `uv run ggrag scan --fail-on-issues` 核验明确关系和断言。

```rag
kind: index
```
