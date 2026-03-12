#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNNER="${REPO_DIR}/scripts/run_daily_report.sh"
BEGIN_MARK="# >>> nba-props-agent daily schedule >>>"
END_MARK="# <<< nba-props-agent daily schedule <<<"

if [[ ! -x "${RUNNER}" ]]; then
  chmod +x "${RUNNER}"
fi

current_cron="$(crontab -l 2>/dev/null || true)"
cleaned_cron="$(printf "%s\n" "${current_cron}" | sed "/${BEGIN_MARK//\//\\/}/,/${END_MARK//\//\\/}/d")"

block="$(cat <<EOF
${BEGIN_MARK}
CRON_TZ=America/New_York
0 11 * * * /bin/bash "${RUNNER}"
${END_MARK}
EOF
)"

{
  printf "%s\n" "${cleaned_cron}"
  printf "%s\n" "${block}"
} | awk 'NF || p{print; p=1}' | crontab -

echo "Installed daily schedule: 11:00 AM America/New_York"
echo "Verify with: crontab -l"
