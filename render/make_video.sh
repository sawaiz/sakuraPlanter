#!/usr/bin/env bash
# Turn rendered frame folders into mp4s, laying the transparent frames over the set's page colour.
# usage: render/make_video.sh <set> <frames-dir> [<frames-dir> ...]      (FPS=30 CRF=16 to change)
set -euo pipefail
SET=$1; shift
FPS=${FPS:-30}; CRF=${CRF:-16}
case "$SET" in 40725) BG=0xD6EAF8 ;; 10280) BG=0x898F95 ;; *) echo "unknown set $SET" >&2; exit 1 ;; esac
for DIR in "$@"; do
  FIRST=$(ls "$DIR"/frame_*.png | head -1)
  SIZE=$(ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=s=x:p=0 "$FIRST")
  ffmpeg -y -loglevel error -f lavfi -i "color=c=$BG:s=$SIZE:r=$FPS" -framerate "$FPS" -start_number "$(basename "$FIRST" .png | sed 's/frame_0*//; s/^$/0/')" -i "$DIR/frame_%05d.png" \
    -filter_complex "[0][1]overlay=shortest=1,format=yuv420p" -c:v libx264 -crf "$CRF" -preset slow -movflags +faststart "${DIR%/}.mp4"
  echo "wrote ${DIR%/}.mp4"
done
