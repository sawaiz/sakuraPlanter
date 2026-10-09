#!/usr/bin/env bash
# Render the full assembly film of one set: every model in order, then join the clips into render/out/<set>.mp4.
# usage: render/render_all.sh 40725|10280 [extra blender_anim.py options, e.g. --samples 64 --res 1280x720 --preview]
# Needs Blender 4.2+ on PATH (or BLENDER=/path/to/blender), or the `bpy` pip module, plus ffmpeg.
set -euo pipefail
SET=$1; shift
HERE=$(cd "$(dirname "$0")" && pwd)
case "$SET" in
  40725) MODELS="branch_white branch_pink final" ;;
  10280) MODELS="daisy rose_head rose_stem_curved rose_stem_straight roses poppy grass snap_head snap_stem_curved snap_stem_straight snapdragons big_leaf lavender aster bouquet" ;;
  *) echo "unknown set $SET" >&2; exit 1 ;;
esac
run() {  # run blender_anim.py with Blender if there is one, else with the bpy module
  if command -v "${BLENDER:-blender}" >/dev/null 2>&1; then "${BLENDER:-blender}" -b -P "$HERE/blender_anim.py" -- "$@"
  else python3 "$HERE/blender_anim.py" "$@"; fi
}
OUT="$HERE/out"; mkdir -p "$OUT"; : > "$OUT/$SET.txt"
for M in $MODELS; do
  DIR="$HERE/frames/$SET/$M"
  if [ -f "$DIR.mp4" ]; then echo "skip $M (done)"; else
    run --set "$SET" --model "$M" --out "$DIR" "$@"
    "$HERE/make_video.sh" "$SET" "$DIR"
  fi
  echo "file '$DIR.mp4'" >> "$OUT/$SET.txt"
done
ffmpeg -y -loglevel error -f concat -safe 0 -i "$OUT/$SET.txt" -c copy "$OUT/$SET.mp4" && echo "wrote $OUT/$SET.mp4"
