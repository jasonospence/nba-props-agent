#!/usr/bin/env bash
set -euo pipefail

BEGIN_MARK="# >>> nba-props-agent daily schedule >>>"
END_MARK="# <<< nba-props-agent daily schedule <<<"

current_cron="$(crontab -l 2>/dev/null || true)"
cleaned_cron="$(printf "%s\n" "${current_cron}" | sed "/${BEGIN_MARK//\//\\/}/,/${END_MARK//\//\\/}/d")"

printf "%s\n" "${cleaned_cron}" | crontab -

echo "Removed nba-props-agent daily schedule (if it existed)."
echo "Verify with: crontab -l"
