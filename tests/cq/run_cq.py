#!/usr/bin/env python3
"""역량 질문 러너 — Prism MCP(Streamable HTTP, stateless)에 kg_* 도구를 호출해 기대값을 확인한다.

  PRISM_URL=http://localhost:4300/mcp PRISM_TOKEN=prt_... python tests/cq/run_cq.py [--stage 1] [--only 2,19]

표준 라이브러리만 쓴다(uv 없이도 돌게). 결과 본문은 출력하지 않고 통과/실패와 짧은 이유만 적는다.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from pathlib import Path

import yaml  # extractors venv: `uv run --project extractors python tests/cq/run_cq.py`

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def call_tool(url: str, token: str, name: str, args: dict) -> dict:
    body = {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": name, "arguments": args}}
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST", headers={
        "Content-Type": "application/json", "Accept": "application/json, text/event-stream",
        "X-Prism-Token": token, "MCP-Protocol-Version": "2025-06-18",
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read().decode("utf-8")
        ctype = resp.headers.get("Content-Type", "")
    if "text/event-stream" in ctype:
        data_lines = [l[5:].strip() for l in raw.splitlines() if l.startswith("data:")]
        raw = data_lines[-1] if data_lines else "{}"
    msg = json.loads(raw)
    if "error" in msg:
        raise RuntimeError(f"rpc error: {msg['error']}")
    result = msg["result"]
    text = "".join(c.get("text", "") for c in result.get("content", []) if c.get("type") == "text")
    return {"isError": result.get("isError", False), "text": text, "json": _try_json(text)}


def _try_json(text: str):
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", type=int, default=99)
    ap.add_argument("--only", default="")
    a = ap.parse_args()
    url = os.environ.get("PRISM_URL", "http://localhost:4300/mcp")
    token = os.environ.get("PRISM_TOKEN")
    if not token:
        print("PRISM_TOKEN 이 필요합니다 (kg:read 스코프)", file=sys.stderr)
        return 2
    only = {int(x) for x in a.only.split(",") if x.strip()}
    manifest = json.loads((ROOT / "build" / "latest" / "manifest.json").read_text(encoding="utf-8"))
    qs = yaml.safe_load((HERE / "questions.yaml").read_text(encoding="utf-8"))
    failed = 0
    for q in qs:
        if q["stage"] > a.stage or (only and q["id"] not in only):
            continue
        try:
            r = call_tool(url, token, q["tool"], q.get("args") or {})
        except Exception as e:  # noqa: BLE001
            print(f"CQ{q['id']:>3} FAIL  {q['tool']} — {e}")
            failed += 1
            continue
        reasons = []
        if r["isError"]:
            reasons.append(f"tool error: {r['text'][:120]}")
        text = r["text"]
        for m in q.get("must", []):
            if m not in text:
                reasons.append(f"missing {m!r}")
        if "must_first" in q:
            hits = (r["json"] or {}).get("hits") or []
            first = hits[0]["uid"] if hits else None
            if first != q["must_first"]:
                reasons.append(f"first hit {first!r} != {q['must_first']!r}")
        if "min_enum_values" in q:
            n = len((r["json"] or {}).get("enumValues") or [])
            if n < q["min_enum_values"]:
                reasons.append(f"enumValues {n} < {q['min_enum_values']}")
        if "must_match_manifest" in q:
            key = q["must_match_manifest"]
            if manifest.get(key) not in text:
                reasons.append(f"manifest {key}={manifest.get(key)!r} not in result")
        if reasons:
            failed += 1
            print(f"CQ{q['id']:>3} FAIL  {q['tool']} — " + "; ".join(reasons))
        else:
            print(f"CQ{q['id']:>3} ok    {q['tool']}")
    print(f"{'FAIL' if failed else 'OK'}: {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
