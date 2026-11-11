#!/usr/bin/env bash
# Render examples/input.txt to examples/out/. Extra args go to `latex2img batch`.
# --lang zh: Noto Serif CJK covers English, Vietnamese and Chinese (needs fonts-noto-cjk).
# Each equation gets 2 variants with random scale, padding, wrap width and a readable fg/bg pair (WCAG >= 4.5).
set -euo pipefail
cd "$(dirname "$0")"
latex2img batch input.txt -o out --lang zh \
  --variants 2 --seed 2410 \
  --scale-range 1.5,3 \
  --padding-range 2,16 \
  --wrap-text-range 15,30 \
  --color-mode random --min-contrast 4.5 \
  "$@"
