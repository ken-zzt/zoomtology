"""`zoomtology validate <nodes.jsonl> <edges.jsonl>` — 번들 검증. `zoomtology build` — 추출·병합·번들 생성."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .schema import Schema


def _read_jsonl(path: Path):
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                yield json.loads(line)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="zoomtology")
    sub = parser.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("validate", help="nodes.jsonl / edges.jsonl 을 schema.yaml 로 검증")
    v.add_argument("nodes", type=Path)
    v.add_argument("edges", type=Path)
    b = sub.add_parser("build", help="추출 → 병합 → 검증 → 번들(build/dist) + build/latest + state")
    b.add_argument("--out", type=Path, default=None)
    b.add_argument("--no-state", action="store_true", help="state/ 를 갱신하지 않는다")
    sub.add_parser("check-sources", help="입력 저장소가 메인 브랜치인지, 커밋하지 않은 변경이 없는지 경고한다 (항상 0 으로 끝난다)")
    args = parser.parse_args(argv)

    if args.cmd == "validate":
        schema = Schema.load()
        problems = schema.check_bundle(_read_jsonl(args.nodes), _read_jsonl(args.edges))
        for p in problems:
            print(p, file=sys.stderr)
        print(f"{'FAIL' if problems else 'OK'}: {len(problems)} problem(s)")
        return 1 if problems else 0
    if args.cmd == "check-sources":
        from .build import source_state, source_warnings
        for w in source_warnings(source_state()):
            print(f"경고: {w}. 그래프에 메인에 없는 코드가 섞일 수 있습니다.", file=sys.stderr)
        return 0
    if args.cmd == "build":
        from .build import BuildError, run
        try:
            result = run(out_dir=args.out, update_state=not args.no_state)
        except BuildError as e:
            print(f"BUILD FAILED: {e}", file=sys.stderr)
            return 1
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
