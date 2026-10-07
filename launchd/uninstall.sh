#!/bin/bash
# Stops the weekly portfolio rebuild and removes it from launchd.
set -euo pipefail

LABEL="com.eriklokkegaard.portfolio-build"

launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
rm -f "$HOME/Library/LaunchAgents/$LABEL.plist"
echo "Removed $LABEL"
