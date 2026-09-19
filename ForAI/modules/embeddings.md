---
id: embedding-runtime
keywords_en:
- embedding
- API
- Ollama
- hybrid
- cache
keywords_zh:
- 向量模型
- 接口
- 本地模型
- 混合检索
- 缓存
summary: 描述 API 和 Ollama embedding 配置、向量缓存、混合召回及安装提示。
---

# Embedding 与混合检索

每个项目使用 ForAI/rag/embedding.toml 配置 provider、model、endpoint、api_key_env、revision、超时、批量大小、分块参数、前缀和可选 dimensions。实际配置忽略，安全示例提交。

API provider 使用 OpenAI-compatible POST 格式，按响应 index 恢复输入顺序；Ollama 使用 /api/embed，禁用截断且只连接 loopback。API 密钥在请求时从指定环境变量读取，不写入配置或错误信息。HTTP 错误不回显服务响应，拒绝重定向。

安装器及 init 返回明确的 setup_required 和用户提示。agent 应询问用户使用 API、本地模型或暂缓。doctor 只发送连接测试文本，检查服务与向量维度；不证明模型检索质量。安装不自动下载权重，不选择付费 API。

向量化对象是导航、功能和设计文档的摘要、关键词与正文，移除 frontmatter 和 rag 机器块。代码节点、变更流水、生成报告和原始代码文件不送入 embedding；正文已有代码片段仍属于文档输入。

文档按字符滑窗分块，默认 1200 字符/150 重叠；16 条一批。以内容和 provider/endpoint/model/revision/dimensions/前缀/分块设置生成缓存键。重建时仅计算缺失块，删除已移除块；失败保留上一份向量缓存，查询不会拿旧缓存掩盖错误。凭据环境变量名、超时和批量大小不改变向量空间。

向量归一化后以 SQLite 持久化，查询使用精确余弦相似度，每文档取最佳片段，再与关键词排名用 RRF(k=60) 融合，最后扩展关系图。提供路径、相关片段和相似度；不自动生成最终答案，不裁决设计冲突。

unconfigured/disabled 产生明确的关键词模式说明；已配置服务出错时返回错误。用户可显式 --keyword-only 跳过。图 scan 不调用模型；sync/query 更新向量。模型同名更换权重时用户应更新 revision，无法自动识别远端权重替换。

检查有限非零向量、数量、API 索引和维度一致性。默认不保证字符分块符合每个模型的 token 上限；应调整配置并运行 doctor/sync。适用于单写入者和中小规模精确检索，无 ANN 后端。

测试使用本地 HTTP 协议夹具验证 API/Ollama、语义路径和错误边界；未使用付费 API，也未为测试自动下载用户未选择的模型。

```rag
kind: functional
sources:
- path: ForAI/rag/src/general_game_development_rag/cli.py
  sha256: 9903401e0801aa764734ca7fbdc73396661d86b1bcc9776d6eb28bebb3bad3d5
- path: ForAI/rag/src/general_game_development_rag/embeddings.py
  sha256: 6e168e898536b8d092595e45acc71e11febdce6383c81843bdb1a9413c52bc94
- path: ForAI/rag/src/general_game_development_rag/graph.py
  sha256: 102b7dbcd139e657cc4e1f05f8b7c18194b2625733fde6883d044d2fe47898f3
- path: skills/project-code-memory/assets/runtime/src/general_game_development_rag/cli.py
  sha256: 9903401e0801aa764734ca7fbdc73396661d86b1bcc9776d6eb28bebb3bad3d5
- path: skills/project-code-memory/assets/runtime/src/general_game_development_rag/embeddings.py
  sha256: 6e168e898536b8d092595e45acc71e11febdce6383c81843bdb1a9413c52bc94
- path: skills/project-code-memory/assets/runtime/src/general_game_development_rag/graph.py
  sha256: 102b7dbcd139e657cc4e1f05f8b7c18194b2625733fde6883d044d2fe47898f3
- path: skills/project-code-memory/scripts/bootstrap.py
  sha256: 4fd49e5ff0a052e6bec0fc742794f89e35797e311c37f657e9c5dda3873d3c6a
- path: src/general_game_development_rag/cli.py
  sha256: 9903401e0801aa764734ca7fbdc73396661d86b1bcc9776d6eb28bebb3bad3d5
- path: src/general_game_development_rag/embeddings.py
  sha256: 6e168e898536b8d092595e45acc71e11febdce6383c81843bdb1a9413c52bc94
- path: src/general_game_development_rag/graph.py
  sha256: 102b7dbcd139e657cc4e1f05f8b7c18194b2625733fde6883d044d2fe47898f3
- path: tests/test_distribution.py
  sha256: 1567e3f9051208fdf69ab11c906b1b94a553a35a3ee6fd90f8868077f89a118c
- path: tests/test_embeddings.py
  sha256: 97838b82938d3b0b27acdea1ee377d008795484b51b998e84cd56f8157211ec6
- path: tools/install_project.py
  sha256: 36d074c33539aa96ff6b3d7ce3805514470c3aecbb105d24d5324312e616daa3
```
