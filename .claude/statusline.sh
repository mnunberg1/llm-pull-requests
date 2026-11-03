#!/bin/sh
# AI generated. Status bar: shows the active config (symlink active-config.cfg).
cd "$(dirname "$0")/.." || exit 0
cat >/dev/null  # status line JSON on stdin, unused
if [ -L active-config.cfg ] && [ -f active-config.cfg ]; then
  name=$(readlink active-config.cfg)
  repo=$(sed -n 's/^repo=//p' active-config.cfg | head -1)
  slug=$(grep -o 'github\.com/[A-Za-z0-9_.-]*/[A-Za-z0-9_.-]*' "$repo" 2>/dev/null | head -1 | sed 's|github\.com/||')
  printf '\033[1;32m● %s\033[0m  %s  %s' "$name" "$repo" "$slug"
else
  printf '\033[1;31m○ NO ACTIVE CONFIG\033[0m  (ln -sfn <name>.cfg active-config.cfg)'
fi
