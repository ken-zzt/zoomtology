#!/usr/bin/env bash
# "스크립트 하나": 빌드 → 커밋(build/latest, state) → 태그 → 노트북 배포. 4단계(ZDV-348)에서 완성.
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
"$HERE/scripts/build.sh"
echo "TODO(ZDV-348): git add build/latest state && git commit && git tag bundle/<version> && scripts/deploy-laptop.sh build/dist/<bundle>" >&2
exit 2
