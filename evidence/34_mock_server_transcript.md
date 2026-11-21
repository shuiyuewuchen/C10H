### 推理桩服务端完整请求日志（真实 stderr 摘录）
### 来源：受管后台任务 T3XzLl（scripts/mock_inference_server.py --port 8765）的 stdout/stderr

[C10H mock] listening http://127.0.0.1:8765/v1  mode=plain
[06:42:40] GET  /v1/models                    200
[06:42:40] GET  /__e2e__/prompts              200
[06:42:50] GET  /v1/models                    200
[06:42:50] POST /api/show                     404   <- Hermes 探测 Ollama 风格端点
[06:42:50] POST /v1/chat/completions          200   <- 最终走 OpenAI 兼容协议
[06:43:00] GET  /__e2e__/requests             200
[06:43:06] POST /v1/chat/completions          200
[06:44:08] POST /api/show                     404
[06:44:08] POST /v1/chat/completions          200   <- model=local-mock-model
[06:44:09] POST /api/show                     404
[06:44:09] POST /v1/chat/completions          200   <- model=local-mock-model-alt
[06:44:10] POST /v1/chat/completions          200
[06:48:46] GET  /api/v1/models                404   <- 网关启动时的协议探测
[06:48:46] GET  /api/tags                     404
[06:48:46] GET  /v1/props                     404
[06:48:46] GET  /props                        404
[06:48:46] GET  /version                      404
[06:48:46] GET  /v1/models                    200   <- 最终确认 OpenAI 兼容
[06:48:46] POST /api/show                     404
[06:48:46] POST /v1/chat/completions          200

### 观察结论（额外发现，非计划内）
1. Hermes 在建立 custom provider 会话前，会先做**协议探测**：
   `/api/show`(Ollama)、`/api/tags`、`/version`、`/v1/props`、`/props`、`/api/v1/models`。
   说明它需要判断对端是 OpenAI 兼容 / Ollama / 其他方言，再决定用哪套调用约定。
   这些 404 是**正常发现行为**，不是错误。
2. 最终所有真实推理请求都落在 `POST /v1/chat/completions`（200），
   与 OpenAI 兼容契约一致 —— 这也是我选择实现该端点作为推理桩的依据。
3. 该日志同时反证：请求确实跨进程到达了推理桩，不是客户端自说自话。

### 可复核
- 完整请求体（含 17 个工具 schema、system prompt、messages）：evidence/mock_logs/requests.jsonl
- 客户端回复：evidence/11_first_conversation.txt、13_model_A.txt、14_model_B.txt、15_cross_session_memory.txt
- 服务端结构化摘要：curl http://127.0.0.1:8765/__e2e__/requests
