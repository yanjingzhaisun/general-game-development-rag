---
id: authority-model
keywords_en: [authority, code, design, graph, evidence]
keywords_zh: [权威, 代码, 设计, 图谱, 证据]
summary: 确立代码权威的功能记忆与保留设计意图的双层关系模型。
---

# 代码与设计的权威关系

功能记忆是当前代码的解释和入口；设计记忆是目标、理由与约束。
功能描述与真实实现冲突时修正文档；设计与实现偏离时需要决定改代码还是设计。
AI 对代码的解释仍然可能错误，应区分代码证据与解释结果。

```rag
kind: design
sources:
  - path: src/general_game_development_rag/graph.py
  - path: src/general_game_development_rag/documents.py
```

图关系：功能文档 DESCRIBES 代码；设计文档 IMPLEMENTED_BY 代码；文档 ASSERTS
断言；断言 ABOUT 业务实体；功能探针 SUPPORTED_BY 代码；问题 AFFECTS 相关节点。
代码节点只存路径和指纹。持久结论进入 Markdown，SQLite 是可重建投影。

每个采用项目独立拥有 ForAI/rag 内的运行源码、uv 依赖锁、环境和数据库。
general-game-development-rag 只开发和分发 skill。skill 初始化时复制一个运行时快照；
后续查询和维护不依赖中央仓库，不共享项目数据库。项目可以独立修改该快照；
升级时显式合并差异，不能自动覆盖本地适配。

指纹变化意味着待核验，不意味着功能变化。自然语言功能摘要不能替代真实代码
来判定设计偏差。静态探针只读字面量，不推断运行时环境、覆盖或副作用。

查询和扫描以当前工作树为范围；v0.1 每次重建，避免切分支后沿用旧图。
文件内作用域条件由维护者显式记录，未提供的语义条件不能由检查器猜测。

参考：[Datawhale 第九章图 RAG 架构](https://datawhalechina.github.io/all-in-rag/#/chapter9/01_graph_rag_architecture)。
采用显式关系和图检索思路；当前实现没有部署教程中的 Neo4j/Milvus 服务。
