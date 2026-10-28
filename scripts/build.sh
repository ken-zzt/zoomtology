#!/usr/bin/env bash
# 메인 Mac 에서 실행: 형제 저장소(../)와 문서 허브·스키마 덤프·curated/ 에서 그래프 번들을 만든다.
#   scripts/build.sh            → build/dist/zoomtology-<version>.tar.gz, build/latest/{manifest.json,report.md}
# 추출·빌드 명령은 1단계(ZDV-345)에서 붙는다. 지금은 스키마 검증만 한다.
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
cd "$HERE/extractors"
uv run pytest -q
uv run zoomtology validate ../tests/fixtures/nodes.jsonl ../tests/fixtures/edges.jsonl
echo "TODO(ZDV-345): extract → build → bundle" >&2
exit 2
