#!/usr/bin/env bash
# C10H 每日晨间摘要（no-agent cron 脚本）：真实执行、零 LLM 成本
set -u
OUT="${C10H_DIGEST_OUT:-$HOME/.hermes/logs/c10h_daily_digest.txt}"
{
  echo "C10H 每日摘要 — $(date '+%Y-%m-%d %H:%M:%S %Z')"
  echo "主机: $(uname -s) $(uname -m)"
  echo "Hermes 版本: $(hermes --version 2>/dev/null | head -1)"
  echo "已装技能: $(hermes skills list 2>/dev/null | grep -oE '[0-9]+ builtin' | head -1 || echo n/a)"
  echo "定时任务数: $(hermes cron list 2>/dev/null | grep -c '\[active\]')"
  echo "记忆条目: $(wc -c < "$HOME/.hermes/memories/MEMORY.md" 2>/dev/null || echo 0) 字节"
} > "$OUT"
cat "$OUT"
