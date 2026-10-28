"""추출기가 읽지 않는 경로와, 산출물에 넣기 전 값 검사. 규칙은 ontology/schema.yaml `content_guard` 가 원본."""

from __future__ import annotations

from fnmatch import fnmatch
from pathlib import PurePosixPath

from .schema import Schema


def is_denied_path(rel_path: str, schema: Schema) -> bool:
    """저장소 루트 기준 경로(`zoomzoom-admin/scripts/x.sh`)가 거부 목록에 걸리는지."""
    p = PurePosixPath(rel_path).as_posix()
    for pattern in schema.deny_paths:
        if fnmatch(p, pattern):
            return True
        # fnmatch 의 `*` 는 `/` 도 먹지만, `**/x` 가 루트의 `x` 도 잡도록 한 번 더
        if pattern.startswith("**/") and fnmatch(p, pattern[3:]):
            return True
    return False
