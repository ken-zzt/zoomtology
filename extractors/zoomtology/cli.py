"""`zoomtology validate <nodes.jsonl> <edges.jsonl>` — 번들 검증. 추출·빌드 명령은 1단계(ZDV-345)에서 붙는다."""

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
    args = parser.parse_args(argv)

    if args.cmd == "validate":
        schema = Schema.load()
        problems = schema.check_bundle(_read_jsonl(args.nodes), _read_jsonl(args.edges))
        for p in problems:
            print(p, file=sys.stderr)
        print(f"{'FAIL' if problems else 'OK'}: {len(problems)} problem(s)")
        return 1 if problems else 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
