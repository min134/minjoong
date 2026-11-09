#!/usr/bin/env bash
set -euo pipefail

PROFILE="${1:-640x480-500}"
HOST="${VIDEO_HOST:-192.168.0.153}"
PORT="${VIDEO_PORT:-5000}"

case "$PROFILE" in
  720p-2000) WIDTH=1280; HEIGHT=720; BITRATE=2000 ;;
  640x480-500) WIDTH=640; HEIGHT=480; BITRATE=500 ;;
  720p-4000) WIDTH=1280; HEIGHT=720; BITRATE=4000 ;;
  *)
    echo "usage: $0 {720p-2000|640x480-500|720p-4000}" >&2
    exit 2
    ;;
esac

exec gst-launch-1.0 libcamerasrc \
  ! "video/x-raw,width=${WIDTH},height=${HEIGHT},framerate=30/1" \
  ! videoconvert \
  ! x264enc tune=zerolatency speed-preset=ultrafast bitrate="${BITRATE}" \
  ! rtph264pay config-interval=1 pt=96 \
  ! udpsink host="${HOST}" port="${PORT}" sync=false
