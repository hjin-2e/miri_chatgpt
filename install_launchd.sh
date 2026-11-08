#!/bin/bash
# 매일 09:00에 review_watcher.py check 실행. 맥이 잠자기였다면 깨어난 뒤 실행됩니다.
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
PY="$(command -v python3)"
LABEL="com.miri.review-watcher"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
case "${1:-install}" in
  uninstall) launchctl unload "$PLIST" 2>/dev/null || true; rm -f "$PLIST"; echo "제거했습니다."; exit 0 ;;
esac
mkdir -p "$HOME/Library/LaunchAgents" "$DIR/output"
cat > "$PLIST" <<PL
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key><array><string>$PY</string><string>$DIR/review_watcher.py</string><string>check</string></array>
  <key>WorkingDirectory</key><string>$DIR</string>
  <key>StartCalendarInterval</key><dict><key>Hour</key><integer>9</integer><key>Minute</key><integer>0</integer></dict>
  <key>StandardOutPath</key><string>$DIR/output/watcher.log</string>
  <key>StandardErrorPath</key><string>$DIR/output/watcher.log</string>
</dict></plist>
PL
launchctl unload "$PLIST" 2>/dev/null || true
launchctl load "$PLIST"
echo "설치 완료: 매일 09:00 실행, 매일 확인. 로그: $DIR/output/watcher.log"
