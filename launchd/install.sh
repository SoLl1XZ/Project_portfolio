#!/bin/bash
# Installs (or reinstalls) the weekly portfolio rebuild as a launchd agent for the current user.
set -euo pipefail

LABEL="com.eriklokkegaard.portfolio-build"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TARGET="$HOME/Library/LaunchAgents/$LABEL.plist"

# launchd does not create missing folders for its log file.
mkdir -p "$SCRIPT_DIR/../logs"
# Unload an older version first; on the very first install there is nothing to unload.
launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
# A copy rather than a symlink: launchd reads LaunchAgents early and should not depend on ~/Documents.
cp "$SCRIPT_DIR/$LABEL.plist" "$TARGET"
launchctl bootstrap "gui/$(id -u)" "$TARGET"
echo "Installed $LABEL (runs every Monday at 09:00)"
