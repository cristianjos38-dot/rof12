#!/usr/bin/env bash
set -euo pipefail

# macOS screen capture at 30 FPS. No timer is used: type CONFIRM_INCIDENT
# followed by Enter in this terminal only after the incident is resolved.
output="${HOME}/Desktop/ROF12_DEMO_FINAL.mp4"
input_device="${ROF12_CAPTURE_INPUT:-1:none}"
mkdir -p "$(dirname "$output")"
echo "[REC] 30 FPS -> $output"
echo "[REC] Stop condition: type CONFIRM_INCIDENT and press Enter after resolution."
ffmpeg -hide_banner -loglevel warning -f avfoundation -framerate 30 \
  -capture_cursor 1 -i "$input_device" -r 30 -c:v libx264 -pix_fmt yuv420p "$output" &
ffmpeg_pid=$!
trap 'kill -INT "$ffmpeg_pid" 2>/dev/null || true; wait "$ffmpeg_pid" 2>/dev/null || true' EXIT INT TERM
while IFS= read -r command; do
  if [[ "$command" == "CONFIRM_INCIDENT" ]]; then
    kill -INT "$ffmpeg_pid"
    wait "$ffmpeg_pid" || true
    trap - EXIT INT TERM
    echo "[REC] Saved $output"
    exit 0
  fi
  echo "[REC] Ignored input; expected CONFIRM_INCIDENT."
done
