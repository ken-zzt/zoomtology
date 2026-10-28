#!/usr/bin/env bash
# "스크립트 하나": 빌드 → build/latest·state 커밋 → 태그 bundle/<version> → 노트북 배포 (ADR 0002).
#   scripts/rebuild-and-deploy.sh            빌드 + 커밋 + 태그 + 배포
#   scripts/rebuild-and-deploy.sh --no-deploy 노트북 배포는 건너뛴다
# 커밋은 build/latest 와 state 만 담는다. 추출기·curated 변경은 따로 커밋해 둔다(작업 트리가 더러우면 멈춘다).
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
cd "$HERE"
DEPLOY=1
[ "${1:-}" = "--no-deploy" ] && DEPLOY=0
if [ -n "$(git status --porcelain --untracked-files=no | grep -v -E '^ M (build/latest/|state/)' || true)" ]; then
  echo "build/latest·state 말고 커밋하지 않은 변경이 있습니다. 먼저 커밋하세요." >&2
  git status --short >&2
  exit 1
fi
scripts/build.sh
VERSION="$(python3 -c "import json;print(json.load(open('build/latest/manifest.json'))['version'])")"
BUNDLE="build/dist/zoomtology-$VERSION.tar.gz"
git add build/latest state
if git diff --cached --quiet; then
  echo "그래프가 바뀌지 않았습니다 ($VERSION)."
else
  git commit -q -m "build: $VERSION" -m "$(python3 -c "import json;c=json.load(open('build/latest/manifest.json'))['counts'];print('nodes', sum(c['nodes'].values()), 'edges', sum(c['edges'].values()))")"
fi
git tag -f "bundle/$VERSION" >/dev/null
echo "번들: $BUNDLE (태그 bundle/$VERSION)"
if [ "$DEPLOY" = 1 ]; then
  scripts/deploy-laptop.sh "$BUNDLE"
fi
