# 赵心皓 · C10H demo 说明

> 演示文件：`赵心皓_C10H_demo.mp4`（H.264，1400×900，48 秒，约 896 KB）
> 配套截图：`evidence/screenshots/01..12_*.png`（12 张，同内容单帧，便于逐张细看）
> 生成脚本：`scripts/render_terminal_shots.py`

---

## 诚实声明（先看这个）

视频里的每一屏都是把 `evidence/*.txt` 中**本机真实采集的命令输出**
按等宽终端样式排版生成的，页脚标注了来源证据文件，可逐张回到原始 stdout 复核。

- ✅ 真实：`hermes --version` / `hermes tools list` / `hermes doctor` /
  `hermes cron list` / `hermes gateway status` 等命令的 stdout，以及
  provider 服务端收到的请求序列。
- ✅ 真实：`memory` 与 `terminal` 工具调用的 tool result（Hermes 真的执行了命令）。
- ⚠️ 非真实 LLM：会话回复来自 `scripts/mock_inference_server.py` 的**确定性预置文本**，
  因为本机没有 API Key。桩的返回文案里自带「这段文本是确定性桩输出，
  不是 LLM 生成内容」的声明。
- ❌ 没有：摆拍的 UI 界面、伪造的模型对话、假装连上的 Telegram/Discord。

---

## 逐帧导航（12 屏，每屏 4–5 秒）

| # | 时间 | 画面 | 想证明什么 | 复核文件 |
|---|---|---|---|---|
| 01 | 00:00 | `hermes --version` | 安装成功，v0.23.3 / Python 3.14.9 | `evidence/01_version.txt` |
| 02 | 00:04 | `hermes tools list` | 24 个 toolset，17 启用 | `evidence/02_tools_list.txt` |
| 03 | 00:09 | 首次 CLI 对话 | CLI → Gateway → provider → 回复全链路 | `evidence/11_first_conversation.txt` |
| 04 | 00:13 | memory 工具调用 | 2 次请求（tool_call → tool result）+ MEMORY.md 落盘 | `evidence/12_tool_call_demo.txt` |
| 05 | 00:18 | 模型切换 | `local-mock-model` vs `local-mock-model-alt`，服务端字段真实不同 | `evidence/13,14_model_*.txt` |
| 06 | 00:23 | `hermes doctor` | 44 项检查，唯一待办是缺 API Key | `evidence/05_doctor.txt` |
| 07 | 00:27 | cron 任务 | 2 个任务 + `Ran now: succeeded` + runs 记录 | `evidence/16,17,18,25_cron*` |
| 08 | 00:32 | 自定义技能 | `1 local — 44 enabled`，技能进入 `<available_skills>` | `evidence/26_skills_list_final.txt` |
| 09 | 00:37 | 本地网关 | `state: ready` / `running (PID 82491)` / WebSocket URL | `evidence/27,28,29_gateway*` |
| 10 | 00:41 | SOUL.md 与记忆 | 定制人格 + MEMORY.md + USER.md + 系统提示注入验证 | `evidence/19_user_memory_tool.txt` |
| 11 | 00:46 | 排错记录 | SSL 重试 + 宿主读保护 + 拆阶段修复 | `/tmp/hermes_install_logs/*.log` |
| 12 | 00:51 | 红旗自查 | 补齐前 → 补齐后 → 反向测试 | `evidence/audit_before.md`、`audit_final.md` |

（时间轴为按 4 秒/屏估算，实际以 48.04 秒总时长为准。）

---

## 怎么自己重新生成

```bash
D="/Users/a0532/Desktop/C10H 安装并驾驭 Hermes Agent"
cd "$D"

# 1) 装 Pillow（本机用 --target 隔离，不污染系统 Python）
python3 -m pip install --target /tmp/pyimg pillow

# 2) 重新渲染 12 张截图（读 evidence/*.txt 的真实输出）
PYTHONPATH=/tmp/pyimg python3 scripts/render_terminal_shots.py

# 3) 重新合成 mp4
FF="$HOME/.local/bin/ffmpeg"   # Hermes 安装时自带的 ffmpeg 9.0.1
# frames 清单用绝对路径，然后：
"$FF" -y -f concat -safe 0 -i /tmp/c10h_frames.txt \
  -vf "fps=25,format=yuv420p" -c:v libx264 -crf 22 \
  -movflags +faststart 赵心皓_C10H_demo.mp4
```

验证视频有效：

```bash
ffprobe -v error -show_entries format=duration -of csv=p=0 赵心皓_C10H_demo.mp4
# 48.040000
```

---

## 为什么用「渲染截图」而不是录屏

1. **可复核**：每张图绑定一个 `evidence/*.txt`，评审可以直接打开原始 stdout 比对，
   而录屏里的文字无法检索、无法复制、无法 diff。
2. **可复现**：别人拿到 `scripts/` 和 `evidence/` 能一键重生成，不依赖本机显示环境。
3. **不误导**：自动化环境没有真实 GUI 终端可截；硬做录屏反而容易变成摆拍。
   明确标注「真实输出的排版渲染」比含糊说「截图」更诚实。

---

## 演示覆盖了挑战的哪些要求

| 挑战要求 | 覆盖画面 |
|---|---|
| L1 安装截图 + 对话截图 | 01、03、11 |
| L1 三问（记忆位置 / SOUL.md / 工具数） | 02、10（详见《安装记录》§5） |
| L2 工具探索 | 02、04、08 |
| L2 cron 任务 | 07 |
| L2 平台接入（本地网关） | 09 |
| L3 SOUL.md 定制 + 记忆 | 10、04 |
| L3 模型切换 | 05 |
| L3 自定义技能 | 08 |
| 排错能力 | 11 |
| 自查与红旗规避 | 12 |

**未覆盖**（如实）：真实 Telegram/Discord 消息界面、真实 LLM 回答、
自动技能创建弹窗、subagent 并行视图 —— 受限于无 Key 与无 bot token，
见《AAR》§5。
