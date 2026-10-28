#!/usr/bin/env bash
# 메인 Mac 에서 실행: 형제 저장소(../)·문서 허브·스키마 덤프·curated/ 에서 그래프 번들을 만든다.
#   scripts/build.sh            → build/dist/zoomtology-<version>.tar.gz, build/latest/{manifest.json,report.md}, state/
#   scripts/build.sh --no-state 상태(first-seen·uids)를 갱신하지 않는다 (시험 빌드)
# 전제: extractors/ 에 uv 환경(`uv sync --extra dev`), extractors/ts 에 `npm install`, build/inputs/ 에 최신 local_zzt 덤프
#       (`zzt-env exec mysql mysqldump --no-data … local_zzt > build/inputs/local_zzt-<날짜>.sql`).
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
cd "$HERE/extractors"
uv run pytest -q
cd "$HERE"
uv run --project extractors zoomtology build "$@"
