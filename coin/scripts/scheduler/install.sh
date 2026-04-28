#!/usr/bin/env bash
# Idempotent installer for the COIN-SCHEDULER launchd job.
# Re-running this safely reloads the plist with any edits.
set -euo pipefail

PLIST_SRC="$(cd "$(dirname "$0")" && pwd)/co.lifestory.coin.discover.plist"
PLIST_DST="$HOME/Library/LaunchAgents/co.lifestory.coin.discover.plist"

if launchctl list | grep -q co.lifestory.coin.discover ; then
  echo "Unloading existing job..."
  launchctl unload "$PLIST_DST" 2>/dev/null || true
fi

mkdir -p "$HOME/Library/LaunchAgents"
cp "$PLIST_SRC" "$PLIST_DST"
launchctl load -w "$PLIST_DST"

if launchctl list | grep -q co.lifestory.coin.discover ; then
  echo "✓ Installed: co.lifestory.coin.discover"
  echo "  Plist: $PLIST_DST"
  echo "  Next fire: 7:00 AM local time daily"
  echo
  echo "Test now: launchctl start co.lifestory.coin.discover"
  echo "  (this is also what '/coin scheduler test' does)"
else
  echo "✗ Install failed — job not in launchctl list"
  exit 1
fi
