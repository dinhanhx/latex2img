#!/usr/bin/env bash
# Generate random formulas (en + vi + zh \text{} words) into examples/amok.txt, then render to examples/amok_out/.
# Usage: ./amok.sh [COUNT_PER_LANG] [extra `latex2img batch` args...]
set -euo pipefail
cd "$(dirname "$0")"
n="${1:-10}"
shift || true
seed=2410
for lang in en vi zh; do  # own seed per lang, else all langs share the same formula shapes
  latex2img amok "$n" --seed "$((seed++))" --lang "$lang" --depth 3
done > amok.txt
# --lang zh: Noto Serif CJK covers English, Vietnamese and Chinese (needs fonts-noto-cjk).
latex2img batch amok.txt -o amok_out --lang zh \
  --variants 5 --seed 2410 \
  --scale-range 1.2,3 \
  --padding-range 2,16 \
  --wrap-text-range 15,30 \
  --color-mode random --min-contrast 4.5 \
  --continue-on-error \
  --workers 4 \
  "$@"
