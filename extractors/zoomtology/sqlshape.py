"""이어붙인 SQL 모양 문자열에서 테이블 토큰·연산·조인만 뽑는다. 문자열 자체는 호출자가 바로 버린다 (ADR 0003).

입력은 php.py 가 `$sql` 데이터플로로 만든 텍스트다. 변수·함수 호출 자리는 `?` 로 와 있다.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

STMT_KEYWORDS = {"select", "insert", "replace", "update", "delete", "truncate", "show", "describe", "desc", "set", "alter",
                 "create", "drop", "call", "with", "optimize", "explain", "lock", "unlock", "start", "commit", "rollback"}
# 테이블 자리에 올 수 없는 낱말
NOT_TABLE = STMT_KEYWORDS | {
    "from", "join", "into", "where", "on", "using", "as", "set", "values", "value", "left", "right", "inner", "outer", "cross",
    "natural", "straight_join", "order", "group", "by", "limit", "having", "union", "all", "distinct", "and", "or", "not", "in",
    "is", "null", "like", "between", "exists", "case", "when", "then", "else", "end", "duplicate", "key", "ignore", "low_priority",
    "delayed", "high_priority", "quick", "table", "temporary", "if", "outfile", "dumpfile", "for", "lock", "share", "mode",
    "sql_calc_found_rows", "sql_no_cache", "sql_cache", "partition", "force", "use", "index", "ignore", "offset", "asc", "desc",
    "with", "rollup", "interval", "default", "true", "false", "div", "mod", "xor", "regexp", "rlike", "match", "against", "boolean",
}
IDENT_RE = re.compile(r"^[a-z_][a-z0-9_]*$")
SQL_TOK_RE = re.compile(r"[a-z_][a-z0-9_]*(?:\.[a-z_*][a-z0-9_]*)?|\?|[(),=]")


@dataclass
class SqlShape:
    stmt: str | None                      # select | insert | … | None (SQL 모양이 아님)
    tables: dict[str, set[str]] = field(default_factory=dict)   # table → {op}
    joins: set[tuple[str, str]] = field(default_factory=set)    # 같은 문장의 테이블 쌍 (정렬)
    on_pairs: list[tuple[tuple[str, str], tuple[str, str]]] = field(default_factory=list)   # ((t, col), (t, col))
    dynamic: bool = False                 # FROM/JOIN/INTO/UPDATE 뒤가 변수(`?`)
    candidates: list[str] = field(default_factory=list)   # 키워드 자리에 온 식별자 전부 (검증 전)


def shape(text: str) -> SqlShape:
    low = text.lower().replace("`", "")
    toks = SQL_TOK_RE.findall(low)
    stmt = next((t for t in toks if t in STMT_KEYWORDS and t not in ("set", "with")), None)
    if stmt is None:
        stmt = next((t for t in toks if t in ("set", "with")), None)
    out = SqlShape(stmt)
    if stmt is None:
        return out
    alias: dict[str, str] = {}

    def add(name: str, op: str) -> None:
        out.candidates.append(name)
        out.tables.setdefault(name, set()).add(op)

    i = 0
    n = len(toks)
    while i < n:
        kw = toks[i]
        role: str | None = None
        multi = False
        if kw == "from":
            role = "delete" if stmt == "delete" else "select"
            multi = True
        elif kw == "join":
            role = "select"
        elif kw == "into" and stmt in ("insert", "replace"):
            role = stmt
        elif kw == "update" and stmt == "update" and i == toks.index("update"):
            role = "update"
            multi = True
        elif kw == "truncate":
            role = "truncate"
            if i + 1 < n and toks[i + 1] == "table":
                i += 1
        elif kw == "table" and stmt in ("alter", "create", "drop") and i > 0 and toks[i - 1] in ("table", "temporary", "alter", "create", "drop", "exists"):
            role = "ddl"
        if role is None:
            i += 1
            continue
        j = i + 1
        if j < n and toks[j] == "if":       # DROP TABLE IF EXISTS
            j += 1
            if j < n and toks[j] == "exists":
                j += 1
        while j < n:
            t = toks[j]
            if t == "(":
                break
            if t == "?":
                out.dynamic = True
                break
            if not IDENT_RE.match(t.split(".")[-1]) or t.split(".")[-1] in NOT_TABLE:
                break
            name = t.split(".")[-1] if "." in t else t
            if name.endswith("_"):          # `zoom_coupon_" . $type` — 접미사가 변수인 테이블명
                out.dynamic = True
                break
            add(name, role)
            j += 1
            if j < n and toks[j] == "as":
                j += 1
            if j < n and IDENT_RE.match(toks[j]) and toks[j] not in NOT_TABLE and "." not in toks[j]:
                alias[toks[j]] = name
                j += 1
            if multi and j < n and toks[j] == ",":
                j += 1
                continue
            break
        i = max(j, i + 1)

    # ON / WHERE 의 `a.c = b.d` (별칭은 테이블명으로 푼다)
    for k in range(1, n - 1):
        if toks[k] == "=" and "." in toks[k - 1] and "." in toks[k + 1]:
            l, r = toks[k - 1].split(".", 1), toks[k + 1].split(".", 1)
            lt, rt = alias.get(l[0], l[0]), alias.get(r[0], r[0])
            if lt in out.tables and rt in out.tables and lt != rt and IDENT_RE.match(l[1] or "") and IDENT_RE.match(r[1] or ""):
                out.on_pairs.append(((lt, l[1]), (rt, r[1])))
    names = sorted(out.tables)
    for a in range(len(names)):
        for b in range(a + 1, len(names)):
            out.joins.add((names[a], names[b]))
    return out
