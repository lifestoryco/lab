#!/usr/bin/env bash
# Removes the COIN-SCHEDULER launchd job. Idempotent.
set -euo pipefail

PLIST_DST="$HOME/Library/LaunchAgents/co.lifestory.coin.discover.plist"
if launchctl list | grep -q co.lifestory.coin.discover ; then
  launchctl unload "$PLIST_DST"
fi
rm -f "$PLIST_DST"
echo "✓ Uninstalled: co.lifestory.coin.discover"
