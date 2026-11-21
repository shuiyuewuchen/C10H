#!/usr/bin/env python3
"""
mock_inference_server.py — C10H 离线可复现推理桩（OpenAI 兼容）

用途
----
本机没有可用的 LLM API Key，为了在**不伪造任何真实 LLM 输出**的前提下，
真实跑通 Hermes Agent 的「CLI → Gateway → Provider → 工具调用 → 回复」完整链路，
本脚本实现一个确定性的、可审计的 OpenAI 兼容推理服务。

它是 Hermes Agent 官方仓库 tests-js/scripts/mock-server.ts 的最小化 Python 移植：
- GET  /v1/models             返回模型清单
- POST /v1/chat/completions   支持流式(SSE) / 非流式
- GET  /__e2e__/prompts       返回本服务收到的全部用户 prompt（用于验证链路真的走通）
- GET  /__e2e__/requests      返回本服务收到的全部请求摘要（工具数量、模型名等）
- 每个请求体完整落盘到 --log-dir/requests.jsonl，便于复核

行为由环境变量 MOCK_MODE 控制：
  plain  (默认)  直接返回一段确定性文本
  tool   (脚本)  第 1 轮返回一个 tool_call，收到 tool 结果后第 2 轮给最终答复
                  由 --tool-name / --tool-args-json 指定

用法
----
  python3 mock_inference_server.py --port 8765 --log-dir ./mock_logs
  # 另开终端：
  hermes chat -q "你好" --provider custom \
      --base-url http://127.0.0.1:8765/v1 --api-key local-mock-key -Q

诚实声明
--------
本服务返回的文本是**预置的确定性字符串**，不是大语言模型的生成结果。
它只用于验证 Hermes Agent 的集成、工具调用与会话链路是否真实工作；
它不能用来评估模型质量。接入真实模型请改用 `hermes model` 配置 OpenRouter / Nous Portal。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

RECEIVED_PROMPTS: list[str] = []
RECEIVED_REQUESTS: list[dict] = []
LOG_DIR = Path(".")

PLAIN_REPLY = (
    "已收到并通过本地 mock provider 完成一次真实会话往返。"
    "当前链路：CLI → Gateway → custom provider (/v1/chat/completions) → 回复渲染。"
    "注意：这段文本是确定性桩输出，不是 LLM 生成内容；"
    "接入 OpenRouter 后同样的命令会返回真实模型回答。"
)
TOOL_FINAL_REPLY = (
    "工具调用已成功执行：我发起了 1 次 tool_call，Hermes 真实执行了该工具并把结果回传，"
    "随后本轮给出最终答复。这证明 agent loop（模型→工具→结果→回复）在本机完整可用。"
)


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()) + "Z"


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):  # 只打到 stderr 一行
        print(f"[{_now()}] {self.address_string()} - {fmt % args}", file=sys.stderr)

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")

    def _json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self):
        if self.path == "/v1/models":
            return self._json({
                "object": "list",
                "data": [
                    {"id": "local-mock-model", "object": "model", "created": 0, "owned_by": "c10h-local"},
                    {"id": "local-mock-model-alt", "object": "model", "created": 0, "owned_by": "c10h-local"},
                ],
            })
        if self.path == "/__e2e__/prompts":
            return self._json({"receivedPrompts": RECEIVED_PROMPTS})
        if self.path == "/__e2e__/requests":
            return self._json({"requests": RECEIVED_REQUESTS})
        if self.path == "/":
            return self._json({"detail": "C10H local mock inference server; see /v1/models"})
        return self._json({"error": {"message": "Not Found"}}, 404)

    def do_POST(self):
        if not self.path.startswith("/v1/chat/completions"):
            return self._json({"error": {"message": "Not Found"}}, 404)
        length = int(self.headers.get("Content-Length", "0") or "0")
        raw = self.rfile.read(length) if length else b"{}"
        try:
            body = json.loads(raw.decode("utf-8"))
        except Exception:
            body = {}

        # 完整落盘，便于事后复核（含 Hermes 传来的工具 schema）
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        with (LOG_DIR / "requests.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps({"ts": _now(), "body": body}, ensure_ascii=False) + "\n")

        model = body.get("model", "local-mock-model")
        stream = bool(body.get("stream"))
        messages = body.get("messages", []) or []
        tools = body.get("tools", []) or []

        user_text = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                c = m.get("content")
                if isinstance(c, str):
                    user_text = c
                elif isinstance(c, list):
                    user_text = "\n".join(
                        p.get("text", "") for p in c if isinstance(p, dict) and p.get("type") == "text"
                    )
                break
        RECEIVED_PROMPTS.append(user_text)
        RECEIVED_REQUESTS.append({
            "ts": _now(), "model": model, "stream": stream,
            "message_count": len(messages), "tool_count": len(tools),
            "has_tool_result": any(m.get("role") == "tool" for m in messages),
            "user_text": user_text[:500],
        })

        has_tool_result = any(m.get("role") == "tool" for m in messages)
        mode = os.environ.get("MOCK_MODE", "plain")

        # 第 1 轮：若处于 tool 模式且用户 prompt 带标记，则返回一个真实 tool_call
        want_tool = (
            mode == "tool" and not has_tool_result and "[TOOL_DEMO]" in user_text
        )
        if want_tool:
            tool_name = os.environ.get("TOOL_NAME", "memory")
            args = json.loads(os.environ.get("TOOL_ARGS_JSON", "{}"))
            call_id = "call_" + uuid.uuid4().hex[:12]
            content = ""
            tool_calls = [{
                "id": call_id, "type": "function",
                "function": {"name": tool_name, "arguments": json.dumps(args, ensure_ascii=False)},
            }]
            finish = "tool_calls"
        else:
            content = TOOL_FINAL_REPLY if has_tool_result else PLAIN_REPLY
            tool_calls = None
            finish = "stop"

        resp_id = "chatcmpl-" + uuid.uuid4().hex[:16]
        created = int(time.time())
        message = {"role": "assistant", "content": content}
        if tool_calls:
            message["tool_calls"] = tool_calls

        if stream:
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "close")
            self._cors()
            self.end_headers()
            try:
                first = {
                    "id": resp_id, "object": "chat.completion.chunk", "created": created,
                    "model": model,
                    "choices": [{"index": 0, "delta": {"role": "assistant"}, "finish_reason": None}],
                }
                self.wfile.write(f"data: {json.dumps(first, ensure_ascii=False)}\n\n".encode())
                if tool_calls:
                    chunk = {
                        "id": resp_id, "object": "chat.completion.chunk", "created": created,
                        "model": model,
                        "choices": [{"index": 0, "delta": {
                            "tool_calls": [{
                                "index": 0, "id": tool_calls[0]["id"], "type": "function",
                                "function": {"name": tool_calls[0]["function"]["name"],
                                             "arguments": tool_calls[0]["function"]["arguments"]},
                            }]
                        }, "finish_reason": None}],
                    }
                    self.wfile.write(f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n".encode())
                else:
                    # 分片输出，模拟流式 token
                    step = 24
                    for i in range(0, len(content), step):
                        chunk = {
                            "id": resp_id, "object": "chat.completion.chunk", "created": created,
                            "model": model,
                            "choices": [{"index": 0, "delta": {"content": content[i:i + step]},
                                         "finish_reason": None}],
                        }
                        self.wfile.write(f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n".encode())
                final = {
                    "id": resp_id, "object": "chat.completion.chunk", "created": created,
                    "model": model,
                    "choices": [{"index": 0, "delta": {}, "finish_reason": finish}],
                }
                self.wfile.write(f"data: {json.dumps(final, ensure_ascii=False)}\n\n".encode())
                self.wfile.write(b"data: [DONE]\n\n")
                self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass
        else:
            self._json({
                "id": resp_id, "object": "chat.completion", "created": created, "model": model,
                "choices": [{"index": 0, "message": message, "finish_reason": finish}],
                "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            })


def main():
    global LOG_DIR
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--log-dir", default="./mock_logs")
    a = ap.parse_args()
    LOG_DIR = Path(a.log_dir)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    srv = ThreadingHTTPServer((a.host, a.port), Handler)
    print(f"[C10H mock] listening http://{a.host}:{a.port}/v1  mode={os.environ.get('MOCK_MODE','plain')}", flush=True)
    try:
        srv.serve_forever(poll_interval=0.2)
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()


if __name__ == "__main__":
    main()
