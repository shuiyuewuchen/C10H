---
name: challenge-deliverable-audit
description: 审计课程挑战（Elite/C10H 等）交付物是否齐全、命名是否合规、rubric 覆盖是否有证据。读取 challenge.json / rubric.json，扫描提交目录，输出可复核的 Markdown 评分报告与缺口清单。Use when the user asks to check, audit, self-grade, or package a challenge submission, verify deliverables, or prepare 姓名_挑战编号_* files.
version: 1.0.0
author: 赵心皓
license: MIT
platforms: [macos, linux, windows]
metadata:
  hermes:
    tags: [Education, Challenges, Rubric, Deliverables, Audit, Compliance]
    related_skills: [systematic-debugging, test-driven-development]
---

# Challenge Deliverable Audit（课程挑战交付物审计）

## When to Use

- 用户说「帮我检查这次挑战的交付物齐不齐」「对照 rubric 自查」「打包提交前过一遍」
- 提交物命名规范要求 `姓名拼音_挑战编号_内容描述.扩展名`（如 Elite 20 的 C2/C3/C4/C5/C10H 系列）
- 需要确认 `AI日志` 这类**必须提交**的文件没有缺失（缺失 = 不予评审）
- 需要一份可复核的、带证据路径的自查报告，而不是口头结论

## Why This Exists

课程挑战资料包通常包含 `challenge.json`、`rubric.json`、`CHALLENGE.md`、`README.md`。
人工核对容易漏掉三类东西：① `required_deliverables` 里的模式串；② rubric 每个维度
是否都有对应证据文件；③ `red_flags`（一票扣分/封顶项）。本技能把这三项机械化了。

## Quick Reference

| 命令 | 作用 |
|------|------|
| `python3 scripts/audit.py <资料包目录> <提交目录>` | 完整审计，输出 Markdown 报告 |
| `python3 scripts/audit.py <资料包目录> <提交目录> --json` | 输出结构化 JSON，便于二次处理 |
| `python3 scripts/audit.py <资料包目录> <提交目录> --out report.md` | 报告落盘 |

## Procedure

1. **定位资料包**：找到 `challenge.json` 与 `rubric.json`（可能在子目录 `materials/` 之外）。
   若只有 `CHALLENGE.md`，退化为从 Markdown 的「必须提交的文件」表格解析。
2. **解析硬约束**：
   - `required_deliverables` / `deliverables_pattern` → 拆成关键词（如 `*安装记录*`, `*AI日志*`）。
   - `red_flags` → 记录每个红旗影响的维度与 `maxScore` 封顶值。
   - `rubric.dimensions` → 维度 id、label、maxPoints、signals、negativeSignals。
   - 从 `CHALLENGE.md` 提取命名规范（正则 `姓名拼音_挑战编号_...`）。
3. **扫描提交目录**：递归收集所有文件（跳过 `.DS_Store`、`.git`、`__pycache__`），
   记录相对路径、字节数、扩展名。
4. **逐项核验**：
   - 每个必需交付物关键词 → 是否有至少一个文件命中（大小写不敏感，支持中文）。
   - 每个 rubric 维度 → 是否有文件名或文件内容信号词命中（如「复盘」「AAR」「迭代」）。
   - 红旗项 → 是否触发（缺 AI 日志、缺核心产物、无迭代痕迹）。
   - 命名规范 → 是否符合 `姓名拼音_挑战编号_` 前缀；给出不合规清单。
   - 空文件检测 → 0 字节文件直接判为缺失。
5. **产出报告**：`AI 使用记录`、`复盘/AAR`、产物完整性、命名合规、红旗检查，
   每项附**具体证据路径**；最后给出「补齐优先级 P0/P1/P2」清单。

## Pitfalls

- **不要把模式串当文件名**：`*安装记录*` 是通配关键词，实际文件名可能是
  `zhaoxinhao_C10H_安装记录.md`；用子串匹配而非精确相等。
- **不要只数文件数**：0 字节占位文件必须判缺失，否则产物完整性会虚高。
- **rubric 有版本差异**：`challenge.json` 里的 `rubric` 可能是字符串，
  `rubric_dimensions` 是 JSON 字符串（需二次 `json.loads`）；`rubric.json` 才是结构化版本。
  两者都要能读，优先用 `rubric.json`。
- **中文路径**：macOS/Windows 下路径含空格与中文，脚本必须全程用 `pathlib` + UTF-8，
  不要拼 shell 命令。
- **不要伪造证据**：报告只陈述磁盘上真实存在的文件；找不到的就明确标 MISSING。

## Verification

- 运行 `python3 scripts/audit.py <资料包> <提交目录>`，退出码 0 表示审计完成（不代表通过）。
- 报告中 `必需交付物` 一节全部为 `OK`，且 `红旗检查` 全部为 `未触发`。
- 用 `--json` 输出做机器复核：`missing_deliverables == []` 且 `triggered_red_flags == []`。
- 至少做一次「故意删掉 AI 日志」的反向测试，确认脚本能报出 `no_ai_log` 红旗。

## 与 agentskills.io 标准的兼容性

本技能使用标准 frontmatter（`name` / `description` / `version` / `author` / `license` /
`platforms` / `metadata`），正文为纯 Markdown 指令 + 可选 `scripts/` 辅助脚本，
符合 agentskills.io progressive disclosure 约定：frontmatter 常驻索引，正文按需加载。
`metadata.hermes.*` 为 Hermes 专属扩展字段，不影响其他 Agent 读取。
