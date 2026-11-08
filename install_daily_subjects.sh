#!/bin/bash
# 매일 오전 09:00 새 Subject 10개를 준비합니다. 심사 확인(09:00) 작업과 별개입니다.
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
PY="$(command -v python3)"
LABEL="com.miri.daily-subjects"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
if [[ "${1:-install}" == "uninstall" ]]; then
  launchctl unload "$PLIST" 2>/dev/null || true
  rm -f "$PLIST"
  echo "일일 Subject 작업 제거 완료"
  exit 0
fi
mkdir -p "$HOME/Library/LaunchAgents" "$DIR/output"
cat > "$PLIST" <<PL
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key><array><string>$PY</string><string>$DIR/daily_subject_generator.py</string></array>
  <key>WorkingDirectory</key><string>$DIR</string>
  <key>StartCalendarInterval</key><dict><key>Hour</key><integer>9</integer><key>Minute</key><integer>0</integer></dict>
  <key>StandardOutPath</key><string>$DIR/output/daily_subjects.log</string>
  <key>StandardErrorPath</key><string>$DIR/output/daily_subjects_error.log</string>
</dict></plist>
PL
launchctl unload "$PLIST" 2>/dev/null || true
launchctl load "$PLIST"
echo "설치 완료: 매일 오전 09:00 신규 Subject 10개 준비"
echo "로그: $DIR/output/daily_subjects.log"
