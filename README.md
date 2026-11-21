# C10H 安装并驾驭 Hermes Agent — 交付目录

> 提交人：**赵心皓** ｜ 挑战 ID：`ch-20260717031609-rnur5a`
> 执行日期：2026-11-21 ｜ 环境：macOS (Darwin 25.3.0) / arm64
> 安装版本：**Hermes Agent v0.23.3 (2026.9.24) · stable** · Python 3.14.9

---

## 一句话结论

本机**真实安装并跑通**了 Hermes Agent：首次 CLI 对话、真实工具调用与记忆落盘、
跨会话记忆注入、模型切换、cron 定时执行、本地网关、SOUL.md 个性化、
兼容 agentskills.io 的自定义技能 —— 全部有可复核的原始输出。
唯一硬缺口是**本机没有 LLM API Key**，因此用可复现的本地推理桩验证「链路」，
**没有伪造任何真实模型输出**（详见《AAR》与各文档中的诚实声明）。

---

## 交付物清单（对照 CHALLENGE.md「必须提交的文件」）

| 要求 | 本目录文件 | 状态 |
|---|---|---|
| 安装记录 `姓名_C10H_安装记录.md` | `赵心皓_C10H_安装记录.md` | ✅ 含 7 类真实排错 + Level 1 三问 |
| 使用演示 `姓名_C10H_demo.mp4` 或截图 | `赵心皓_C10H_demo.mp4`（48 秒）+ `evidence/screenshots/*.png`（12 张） | ✅ |
| 配置说明 `姓名_C10H_配置说明.md` | `赵心皓_C10H_配置说明.md` | ✅ |
| 技能文件 `姓名_C10H_自定义技能/` | `赵心皓_C10H_自定义技能/challenge-deliverable-audit/` | ✅ 含 SKILL.md + 可运行 audit.py |
| ⚡ **AI 日志（必须）** | `赵心皓_C10H_AI日志.md` | ✅ 13 轮真实迭代 |
| 拿来说明 `姓名_C10H_拿来说明.md` | `赵心皓_C10H_拿来说明.md` | ✅ |

**额外交付（对应 rubric 加分项）**

| 文件 | 作用 |
|---|---|
| `赵心皓_C10H_AAR.md` | After Action Review：7 个失败经验 + P0/P1/P2 改进方案 |
| `赵心皓_C10H_工具探索报告.md` | 24 个 toolset 全表 + 8 个重点工具深度分析 |
| `赵心皓_C10H_模型对比报告.md` | 双模型路由验证（已做）+ 质量补测方案（待 Key） |
| `赵心皓_C10H_demo说明.md` | 演示视频逐帧导航与复核方法 |
| `evidence/` | 40+ 份原始命令 stdout / 请求体 jsonl |
| `scripts/` | 4 个可独立运行的脚本 |
| `config_snapshots/` | SOUL.md 原始/定制版 + config.yaml 快照 |

---

## 目录结构

```
C10H 安装并驾驭 Hermes Agent/
├── README.md                          ← 本文件（入口）
├── 赵心皓_C10H_安装记录.md
├── 赵心皓_C10H_配置说明.md
├── 赵心皓_C10H_AI日志.md              ← 必须项
├── 赵心皓_C10H_拿来说明.md
├── 赵心皓_C10H_AAR.md
├── 赵心皓_C10H_工具探索报告.md
├── 赵心皓_C10H_模型对比报告.md
├── 赵心皓_C10H_demo说明.md
├── 赵心皓_C10H_demo.mp4               ← 48 秒演示
├── 赵心皓_C10H_自定义技能/
│   └── challenge-deliverable-audit/
│       ├── SKILL.md                   ← agentskills.io 标准
│       └── scripts/audit.py           ← 可运行
├── config_snapshots/
│   ├── SOUL.md.original               ← 出厂人格（667 字节）
│   ├── SOUL.md.custom                 ← 定制「砚」
│   └── config.yaml.after_install      ← v54 配置快照
├── scripts/
│   ├── mock_inference_server.py       ← 本地 OpenAI 兼容推理桩
│   ├── daily_digest.sh                ← cron no-agent 脚本
│   ├── render_terminal_shots.py       ← 真实输出 → PNG
│   └── (audit.py 在技能目录内)
└── evidence/
    ├── 01..33_*.txt                   ← 原始 stdout（按编号）
    ├── audit_before.md / audit_final.md
    ├── digest_sample.txt
    ├── mock_logs*/requests.jsonl      ← provider 收到的完整请求
    └── screenshots/01..12_*.png       ← 12 张可读终端截图
```

---

## 快速复核（3 条命令）

```bash
D="/Users/a0532/Desktop/C10H 安装并驾驭 Hermes Agent"

# ① 确认 Hermes 真的装着
hermes --version && hermes doctor

# ② 用自带审计脚本自查交付物（应输出 0 个 missing、0 个红旗）
python3 "$D/赵心皓_C10H_自定义技能/challenge-deliverable-audit/scripts/audit.py" \
  "/Users/a0532/Desktop/未完成的挑战/挑战_C10H 安装并驾驭 Hermes Agent_rnur5a_完整资料" \
  "$D" --out "$D/evidence/audit_final.md"

# ③ 零凭据重跑首次对话（推理桩 + Hermes）
python3 "$D/scripts/mock_inference_server.py" --port 8765 --log-dir "$D/evidence/mock_logs" &
hermes chat -q "你好 Hermes" --provider custom \
  --base-url http://127.0.0.1:8765/v1 --api-key local-mock-key -Q
```

---

## 证据地图（想验哪条结论，看哪个文件）

| 结论 | 证据 |
|---|---|
| 安装成功、版本、Python 3.14.9 | `evidence/01_version.txt`、`screenshots/01_install_version.png` |
| 24 个 toolset（17 启用） | `evidence/02_tools_list.txt`、`screenshots/02_tools_list.png` |
| 首次 CLI 对话真实往返 | `evidence/11_first_conversation.txt`、`evidence/mock_logs/requests.jsonl` |
| 真实工具调用 + 记忆落盘 | `evidence/12_tool_call_demo.txt`、`evidence/mock_logs_tool/requests.jsonl`、`~/.hermes/memories/MEMORY.md` |
| 跨会话记忆注入 | `evidence/15_cross_session_memory.txt`（system prompt 含 `MEMORY ... [3% — 75/2,200 chars]`） |
| 模型切换真的改了 model 字段 | `evidence/13_model_A.txt`、`14_model_B.txt`、`screenshots/05_model_switch.png` |
| USER.md 写入 + SOUL.md 注入 | `evidence/19_user_memory_tool.txt`、`screenshots/10_soul_memory.png` |
| terminal 工具真实执行命令 | `evidence/33_terminal_tool_demo.txt`、`evidence/mock_logs_terminal/requests.jsonl` |
| 44 项诊断 / 唯一待办是缺 Key | `evidence/05_doctor.txt`、`screenshots/06_doctor.png` |
| cron 创建 + 真实触发成功 | `evidence/16_cron_create.txt`、`17_cron_list_after.txt`、`18_cron_run.txt`、`25_cron_runs.txt` |
| 自定义技能进入技能索引 | `evidence/26_skills_list_final.txt`、`screenshots/08_custom_skill.png` |
| 本地网关 running + WebSocket 端点 | `evidence/27_gateway_ensure.txt`、`28`、`29`、`screenshots/09_gateway.png` |
| 安装期真实报错与拆阶段修复 | `screenshots/11_troubleshooting.png`、`/tmp/hermes_install_logs/*.log` |
| 8 次会话 / 2 次工具调用 | `evidence/31_insights.txt`、`30_sessions.txt` |

---

## 评分维度对照（自评见《AAR》§6）

| 维度 | 分值 | 主要支撑材料 |
|---|---|---|
| mastery 驾驭程度 | 25 | 安装记录（7 类排错）、工具探索报告、自定义技能 |
| integration 集成质量 | 20 | 配置说明、config_snapshots、可复现脚本、无环境冲突 |
| artifactCompleteness 产物完整性 | 15 | 本 README、6 类必需交付物、demo.mp4、12 截图、可运行脚本 |
| aiUsage AI 使用质量 | 20 | AI 日志（13 轮 / 双向测试 / prompt v1→v3）、请求体落盘 |
| reflectionQuality 复盘质量 | 20 | AAR（7 个失败经验、P0/P1/P2、迭代留痕、缺口如实） |
| **红旗** | — | 核心交付物齐全 ✅ / AI 日志存在 ✅ / 非 one-shot ✅ |

---

## 诚实声明汇总

1. **没有 LLM API Key**：所有 provider 均 `✗ (not set)`（`evidence/24_status_full.txt`）。
2. **推理桩不是 LLM**：`scripts/mock_inference_server.py` 返回确定性预置文本，
   桩源码与返回文案里都写明「不是 LLM 生成内容」。它验证的是集成链路与 agent loop。
3. **未做的 L2/L3/L4 项**：真实平台消息收发（缺 bot token）、自动技能创建与
   subagent（需模型主动决策）、3 天连续使用（单日完成）、L4 全部 ——
   均在《AAR》§5 与《配置说明》§10 列明，并给出补齐命令。
4. **截图来源**：`evidence/screenshots/*.png` 由 `scripts/render_terminal_shots.py`
   把 `evidence/*.txt` 的**真实 stdout** 按等宽字体排版生成，每张标注来源文件；
   不是伪造的 UI 界面，也不是摆拍的模型对话。
5. **人的事实**：姓名「赵心皓」取自用户本人陈述；未从文件、git config 或 API 反推。

---

## 下一步（拿到 Key 后）

见《AAR》§4 与《配置说明》§10。最短路径：

```bash
echo 'OPENROUTER_API_KEY=sk-or-v1-...' >> ~/.hermes/.env && chmod 600 ~/.hermes/.env
hermes setup && hermes doctor && hermes chat -q "用一句话介绍你自己" -Q
```
