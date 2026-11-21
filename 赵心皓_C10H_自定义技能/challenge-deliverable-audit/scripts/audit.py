#!/usr/bin/env python3
"""
audit.py — 课程挑战交付物审计器（challenge-deliverable-audit 技能的辅助脚本）

用法:
  python3 audit.py <资料包目录> <提交目录> [--json] [--out report.md]

设计要点:
  - 优先读 rubric.json；退化读 challenge.json 里的 rubric_dimensions（可能是 JSON 字符串）
  - 必需交付物用「关键词子串」匹配（*安装记录* → 安装记录），不做精确相等
  - 0 字节文件判为缺失
  - 全程 pathlib + UTF-8，兼容中文/空格路径
  - 只报告磁盘上真实存在的文件，找不到就标 MISSING
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SKIP_NAMES = {".DS_Store", "Thumbs.db"}
SKIP_DIRS = {".git", "__pycache__", "node_modules", ".venv"}

# rubric 维度 → 用于判断「是否有证据」的信号词（文件名或文件内容命中即算）
DIMENSION_SIGNALS = {
    "mastery": ["安装记录", "排错", "扩展", "tools", "doctor", "配置说明", "troubleshoot"],
    "integration": ["配置说明", "config", "集成", "可复现", "crontab", "cron", "脚本"],
    "artifactCompleteness": ["README", "demo", "安装记录", "配置说明", "AI日志", "拿来说明", "使用说明"],
    "aiUsage": ["AI日志", "prompt", "迭代", "工作流", "日志", "AAR"],
    "reflectionQuality": ["AAR", "复盘", "反思", "失败", "改进", "迭代"],
}

RED_FLAG_CHECKS = {
    "missing_artifacts": "核心交付物缺失",
    "no_ai_log": "无 AI 使用记录/AAR",
    "one_shot_ai": "一句话指令直接提交、无迭代",
}


def load_pack(pack: Path) -> dict:
    info: dict = {"patterns": [], "dimensions": [], "red_flags": [], "naming": None, "title": ""}
    rubric_p = pack / "rubric.json"
    challenge_p = pack / "challenge.json"
    md_p = pack / "CHALLENGE.md"

    if rubric_p.exists():
        d = json.loads(rubric_p.read_text(encoding="utf-8"))
        info["dimensions"] = d.get("dimensions", [])
        info["red_flags"] = d.get("red_flags", [])

    if challenge_p.exists():
        c = json.loads(challenge_p.read_text(encoding="utf-8"))
        info["title"] = c.get("title", "")
        for key in ("deliverables_pattern", "required_deliverables", "deliverables", "required_files"):
            raw = c.get(key)
            if not raw:
                continue
            for piece in re.split(r"[,，;；\n]", str(raw)):
                kw = piece.strip().strip("*").strip()
                if kw and len(kw) < 40:
                    info["patterns"].append(kw)
        if not info["dimensions"]:
            rd = c.get("rubric_dimensions")
            if isinstance(rd, str):
                try:
                    info["dimensions"] = json.loads(rd).get("dimensions", [])
                except json.JSONDecodeError:
                    pass
        if not info["red_flags"]:
            rf = c.get("red_flags")
            if isinstance(rf, str):
                try:
                    info["red_flags"] = json.loads(rf).get("flags", [])
                except json.JSONDecodeError:
                    pass

    # 权威来源：challenge.json 的 required_deliverables / deliverables_pattern。
    # 只用这两个字段拆分出的模式串，绝不扫描 Markdown 正文表格（会误抓无关单元格）。
    canonical = []
    if challenge_p.exists():
        c = json.loads(challenge_p.read_text(encoding="utf-8"))
        for key in ("deliverables_pattern", "required_deliverables"):
            raw = c.get(key)
            if not raw:
                continue
            for piece in re.split(r"[,，;；\n]", str(raw)):
                kw = piece.strip().strip("*").strip()
                kw = re.sub(r"[（(].*", "", kw).strip()  # 去掉「（必须）」等注释
                if kw and 1 < len(kw) < 30:
                    canonical.append(kw)

    if md_p.exists():
        text = md_p.read_text(encoding="utf-8", errors="replace")
        # 命名规范行含 emoji 与 ** 强调，用宽松匹配取第一个反引号内容
        m = re.search(r"命名规范[^\n`]*`([^`]+)`", text)
        if m:
            info["naming"] = m.group(1)
        # 只解析「必须提交的文件」这一节，且取「命名格式」列（第 2 列）里的
        # 反引号文件名，剥掉 `姓名_C10H_` 前缀与扩展名，得到真正应匹配的文件名关键词。
        sec = re.search(r"##\s*必须提交的文件(.*?)(?=\n##\s|\Z)", text, re.S)
        if sec:
            for line in sec.group(1).splitlines():
                if not line.strip().startswith("|"):
                    continue
                cells = [c.strip() for c in line.strip().strip("|").split("|")]
                if len(cells) < 2 or set(cells[0]) <= set("-: "):
                    continue
                for tmpl in re.findall(r"`([^`]+)`", cells[1]):
                    stem = tmpl.split(".")[0].rstrip("/")
                    stem = re.sub(r"^姓名(拼音)?_C\d+[A-Za-z]?_", "", stem)
                    if stem and 1 < len(stem) < 30:
                        canonical.append(stem)

    # 归一 + 去重；过滤表头/长句噪声
    stop = {"文件", "说明", "命名格式", "配置说明文件"}
    seen, pats = set(), []
    for p in canonical:
        p2 = re.sub(r"\s+", "", p)
        if p2 and p2 not in seen and p2 not in stop and "+" not in p2 and len(p2) < 25:
            seen.add(p2)
            pats.append(p2)
    info["patterns"] = pats
    return info


def scan(submission: Path) -> list[dict]:
    out = []
    if not submission.exists():
        return out
    for p in sorted(submission.rglob("*")):
        if not p.is_file() or p.name in SKIP_NAMES:
            continue
        if any(part in SKIP_DIRS for part in p.relative_to(submission).parts):
            continue
        try:
            size = p.stat().st_size
            text = p.read_text(encoding="utf-8", errors="replace")[:20000] if size < 2_000_000 else ""
        except OSError:
            size, text = 0, ""
        out.append({
            "path": str(p.relative_to(submission)),
            "name": p.name,
            "size": size,
            "text": text,
        })
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("pack")
    ap.add_argument("submission")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--out")
    a = ap.parse_args()

    pack, submission = Path(a.pack), Path(a.submission)
    info = load_pack(pack)
    files = scan(submission)
    nonempty = [f for f in files if f["size"] > 0]
    blob = "\n".join(f["name"] + "\n" + f["text"] for f in nonempty)

    # 1. 必需交付物
    deliverable_rows = []
    missing_deliverables = []
    for kw in info["patterns"]:
        k = kw.lower().replace(" ", "")
        # 目录型交付物（如 `姓名_C10H_自定义技能/`）按相对路径匹配，
        # 文件型交付物按文件名或相对路径匹配，两者都支持。
        hits = [f["path"] for f in nonempty
                if k in f["name"].lower().replace(" ", "")
                or k in f["path"].lower().replace(" ", "")]
        ok = bool(hits)
        deliverable_rows.append({"keyword": kw, "ok": ok, "evidence": hits})
        if not ok:
            missing_deliverables.append(kw)

    # 2. rubric 维度证据
    dim_rows = []
    for d in info["dimensions"]:
        did = d.get("id", "")
        sigs = DIMENSION_SIGNALS.get(did, []) + [s for s in d.get("signals", []) if isinstance(s, str)]
        hits = sorted({s for s in sigs if s and (s.lower() in blob.lower())})
        dim_rows.append({
            "id": did, "label": d.get("label", did),
            "maxPoints": d.get("maxPoints", d.get("weight", "")),
            "signals_matched": hits, "has_evidence": bool(hits),
        })

    # 3. 红旗
    # 注意：「无迭代记录」这种否定句里也含「迭代」，只看关键词会误判成有迭代。
    # 因此 one_shot_ai 用「强信号」判定：轮次编号 / 版本号 / 明确的迭代动作，
    # 并先剔除否定短语，避免反向测试出现假阴性。
    has_ai_log = any("AI日志" in f["name"] or "ai日志" in f["name"].lower() for f in nonempty)
    has_aar = any(k in blob for k in ("AAR", "复盘", "反思"))
    negated = re.sub(r"无(迭代|多轮|prompt|工作流)[^\s，。；]*", "", blob)
    strong_iteration = [
        r"轮次\s*\d", r"第\s*\d+\s*轮", r"第一轮", r"第二轮", r"第三轮",
        r"\bv[123]\b", r"prompt\s*优化", r"多轮迭代", r"方案修正", r"版本\s*v\d",
        r"迭代过程", r"三次修正", r"\d+\s*次修正",
    ]
    has_iteration = any(re.search(p, negated, re.I) for p in strong_iteration)
    rf_state = {
        "missing_artifacts": len(missing_deliverables) > 0,
        "no_ai_log": not (has_ai_log and has_aar),
        "one_shot_ai": not has_iteration,
    }
    triggered = [k for k, v in rf_state.items() if v]

    # 4. 命名规范
    # 只检查「提交根目录直接下的交付文档」。
    # 子目录里的文件不受挑战命名规范约束：evidence/、scripts/、config_snapshots/
    # 是支撑文件；技能目录里的 SKILL.md / scripts/*.py 遵循 agentskills.io 规范
    # （要求固定名 SKILL.md），强行加姓名前缀反而会破坏兼容性。
    SKIP_NAMING = {"README.md", "LICENSE", "requirements.txt"}

    naming_ok, naming_bad = None, []
    naming_rule = info["naming"]
    if naming_rule:
        # 形如 `姓名拼音_C10H_内容描述.扩展名`；取出挑战编号 token
        m = re.search(r"(C\d+[A-Za-z]?)", naming_rule)
        token = m.group(1) if m else None
        if token:
            named = [f for f in nonempty
                     if re.search(r"\.(md|txt|py|json|yaml|mp4|png|sh)$", f["name"])
                     and "/" not in f["path"]          # 仅根目录文件
                     and f["name"] not in SKIP_NAMING]
            naming_bad = [f["path"] for f in named if token not in f["name"]]
            naming_ok = len(naming_bad) == 0

    result = {
        "challenge_title": info["title"],
        "pack": str(pack), "submission": str(submission),
        "files_scanned": len(files), "nonempty_files": len(nonempty),
        "empty_files": [f["path"] for f in files if f["size"] == 0],
        "naming_rule": info["naming"], "naming_ok": naming_ok, "naming_violations": naming_bad,
        "deliverables": deliverable_rows, "missing_deliverables": missing_deliverables,
        "dimensions": dim_rows,
        "red_flags": [{"id": k, "desc": RED_FLAG_CHECKS.get(k, k), "triggered": rf_state[k]} for k in RED_FLAG_CHECKS],
        "triggered_red_flags": triggered,
    }

    if a.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        lines = [
            f"# 交付物审计报告：{result['challenge_title'] or '(未识别标题)'}", "",
            f"- 资料包：`{pack}`", f"- 提交目录：`{submission}`",
            f"- 扫描文件 {len(files)} 个，非空 {len(nonempty)} 个，空文件 {len(result['empty_files'])} 个", "",
            "## 1. 必需交付物", "",
            "| 关键词 | 状态 | 证据 |", "|---|---|---|",
        ]
        for r in deliverable_rows:
            lines.append(f"| {r['keyword']} | {'OK' if r['ok'] else '**MISSING**'} | {', '.join(r['evidence']) or '—'} |")
        lines += ["", "## 2. rubric 维度证据覆盖", "", "| 维度 | 分值 | 命中信号 | 有证据 |", "|---|---|---|---|"]
        for d in dim_rows:
            lines.append(f"| {d['label']} ({d['id']}) | {d['maxPoints']} | {', '.join(d['signals_matched']) or '—'} | {'是' if d['has_evidence'] else '**否**'} |")
        lines += ["", "## 3. 红旗检查（触发即封顶/扣分）", "", "| 红旗 | 说明 | 状态 |", "|---|---|---|"]
        for r in result["red_flags"]:
            lines.append(f"| `{r['id']}` | {r['desc']} | {'**触发**' if r['triggered'] else '未触发'} |")
        lines += ["", "## 4. 命名规范", ""]
        lines.append(f"- 规范：`{info['naming']}`" if info["naming"] else "- 未在 CHALLENGE.md 中解析到命名规范")
        lines.append("- 检查范围：仅提交根目录直接下的交付文档（子目录为支撑文件/技能包，README.md 为通用入口，均不参与）")
        if naming_ok is not None:
            lines.append(f"- 是否含挑战编号 `{token}`：{'是，合规' if naming_ok else '否'}；不合规文件 {len(naming_bad)} 个")
            for b in naming_bad[:20]:
                lines.append(f"  - `{b}`")
            lines.append("- 说明：资料包内部对姓名写法不一致（适用原则写「姓名拼音」，"
                         "「必须提交的文件」表写「姓名」）。历史提交中 "
                         "`赵心皓_C4D_*` 与 `ZhaoXinhao_C2G_*` 两种都存在，"
                         "故本审计只强制校验挑战编号 token，不强制姓名用字。")
        lines += ["", "## 5. 补齐优先级", "", "- **P0**：`AI日志` 与 `AAR 复盘`（缺失直接触发红旗）", "- **P1**：所有 MISSING 的必需交付物", "- **P2**：命名不合规文件重命名、空文件填充内容", ""]
        report = "\n".join(lines)
        print(report)
        if a.out:
            Path(a.out).write_text(report, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
