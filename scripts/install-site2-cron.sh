#!/usr/bin/env bash
set -Eeuo pipefail

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
runner="$repo_dir/scripts/run-site2-local.sh"
env_file="${AUTO_CHECKIN_ENV:-$HOME/.config/auto-checkin/site2.env}"
log_dir="${AUTO_CHECKIN_LOG_DIR:-$HOME/.local/state/auto-checkin}"
cron_expr="${AUTO_CHECKIN_CRON:-30 0 * * *}"
marker="# auto-checkin-site2-local"

if [[ ! -f "$env_file" ]]; then
  echo "Missing env file: $env_file" >&2
  echo "Create it from config/site2.env.example before installing cron." >&2
  exit 2
fi

mkdir -p "$log_dir"
chmod +x "$runner"

cron_line="$cron_expr AUTO_CHECKIN_ENV=\"$env_file\" \"$runner\" >> \"$log_dir/site2.log\" 2>&1 $marker"

tmp_file="$(mktemp)"
trap 'rm -f "$tmp_file"' EXIT

(crontab -l 2>/dev/null | grep -Fv "$marker"; echo "$cron_line") > "$tmp_file"
crontab "$tmp_file"

echo "Installed cron:"
echo "$cron_line"
