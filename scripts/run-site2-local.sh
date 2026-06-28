#!/usr/bin/env bash
set -Eeuo pipefail

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
env_file="${AUTO_CHECKIN_ENV:-$HOME/.config/auto-checkin/site2.env}"
venv_dir="${AUTO_CHECKIN_VENV:-$repo_dir/.venv}"

if [[ ! -f "$env_file" ]]; then
  echo "Missing env file: $env_file" >&2
  echo "Create it from config/site2.env.example and fill local credentials." >&2
  exit 2
fi

cd "$repo_dir"

if [[ ! -x "$venv_dir/bin/python" ]]; then
  python3 -m venv "$venv_dir"
fi

"$venv_dir/bin/python" -m pip install --disable-pip-version-check -q -r requirements.txt
"$venv_dir/bin/python" -m playwright install chromium >/dev/null

set -a
# shellcheck disable=SC1090
. "$env_file"
set +a

export CHECKIN_TARGETS="${CHECKIN_TARGETS:-site2}"

if command -v xvfb-run >/dev/null 2>&1; then
  exec xvfb-run --auto-servernum "$venv_dir/bin/python" checkin.py
fi

exec "$venv_dir/bin/python" checkin.py
