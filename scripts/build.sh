#!/usr/bin/env bash
# 메인 Mac 에서 실행: 형제 저장소(../)·문서 허브·스키마 덤프·curated/ 에서 그래프 번들을 만든다.
#   scripts/build.sh            → build/dist/zoomtology-<version>.tar.gz, build/latest/{manifest.json,report.md}, state/
#   scripts/build.sh --no-state 상태(first-seen·uids)를 갱신하지 않는다 (시험 빌드)
# 전제: extractors/ 에 uv 환경(`uv sync --extra dev`), extractors/ts 에 `npm install`, build/inputs/ 에 최신 local_zzt 덤프
#       (`zzt-env exec mysql mysqldump --no-data … local_zzt > build/inputs/local_zzt-<날짜>.sql`).
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
# 스키마 덤프 신선도 — build/inputs/local_zzt-<YYYY-MM-DD>.sql 이 없거나 90일 넘으면 경고 (빌드는 계속한다)
DUMP="$(ls -1 "$HERE"/build/inputs/local_zzt-*.sql 2>/dev/null | sort | tail -1 || true)"
if [ -z "$DUMP" ]; then
  echo "경고: build/inputs/ 에 local_zzt 덤프가 없습니다 — 허브 덤프만 씁니다. 만들기: zzt-env exec mysql mysqldump --no-data -uroot local_zzt > build/inputs/local_zzt-$(date +%F).sql" >&2
else
  DUMP_DATE="$(basename "$DUMP" | sed -E 's/local_zzt-([0-9-]+)\.sql/\1/')"
  AGE=$(( ( $(date +%s) - $(date -j -f %Y-%m-%d "$DUMP_DATE" +%s 2>/dev/null || date -d "$DUMP_DATE" +%s) ) / 86400 ))
  if [ "$AGE" -gt 90 ]; then
    echo "경고: 스키마 덤프가 ${AGE}일 됐습니다 ($DUMP). 로컬 DB 를 갱신하고 덤프를 다시 뜨세요." >&2
  fi
fi
cd "$HERE/extractors"
uv run pytest -q
cd "$HERE"
uv run --project extractors zoomtology build "$@"
