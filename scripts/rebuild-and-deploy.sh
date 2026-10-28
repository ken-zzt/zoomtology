#!/usr/bin/env bash
# "스크립트 하나": 빌드 → build/latest·state 커밋 → 태그 bundle/<version> → 노트북 배포 (ADR 0002).
#   scripts/rebuild-and-deploy.sh            빌드 + 커밋 + 태그 + 배포 (그래프가 안 바뀌었으면 커밋·태그·배포를 건너뛴다)
#   scripts/rebuild-and-deploy.sh --no-deploy 노트북 배포는 건너뛴다
#   scripts/rebuild-and-deploy.sh --force     그래프가 안 바뀌었어도 커밋·태그·배포한다
# 커밋은 build/latest 와 state 만 담는다. 추출기·curated 변경은 따로 커밋해 둔다(작업 트리가 더러우면 멈춘다).
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
cd "$HERE"
DEPLOY=1
FORCE=0
for a in "$@"; do
  [ "$a" = "--no-deploy" ] && DEPLOY=0
  [ "$a" = "--force" ] && FORCE=1
done
if [ -n "$(git status --porcelain --untracked-files=no | grep -v -E '^ M (build/latest/|state/)' || true)" ]; then
  echo "build/latest·state 말고 커밋하지 않은 변경이 있습니다. 먼저 커밋하세요." >&2
  git status --short >&2
  exit 1
fi
# 커밋되지 않은 build/latest·state 는 이번 빌드가 다시 만든다 — 버려서 버전이 -dirty 로 찍히지 않게 한다
git checkout -q -- build/latest state 2>/dev/null || true
PREV_SHA="$(python3 -c "import json,sys;print(json.load(open('build/latest/manifest.json')).get('contentSha256',''))" 2>/dev/null || true)"
scripts/build.sh
VERSION="$(python3 -c "import json;print(json.load(open('build/latest/manifest.json'))['version'])")"
NEW_SHA="$(python3 -c "import json;print(json.load(open('build/latest/manifest.json')).get('contentSha256',''))")"
BUNDLE="build/dist/zoomtology-$VERSION.tar.gz"
if [ -n "$PREV_SHA" ] && [ "$PREV_SHA" = "$NEW_SHA" ] && [ "$FORCE" = 0 ]; then
  echo "그래프 내용이 바뀌지 않았습니다 (contentSha256 같음). 커밋·태그·배포를 건너뜁니다. 강제: --force"
  git checkout -q -- build/latest state 2>/dev/null || true
  exit 0
fi
git add build/latest state
git commit -q -m "build: $VERSION" -m "$(python3 -c "import json;m=json.load(open('build/latest/manifest.json'));c=m['counts'];print('nodes', sum(c['nodes'].values()), 'edges', sum(c['edges'].values()), 'contentSha256', m['contentSha256'][:12])")"
git tag -f "bundle/$VERSION" >/dev/null
echo "번들: $BUNDLE (태그 bundle/$VERSION)"
if [ "$DEPLOY" = 1 ]; then
  scripts/deploy-laptop.sh "$BUNDLE"
fi
