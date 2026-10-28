"""mysqldump DDL(`--no-data`)에서 Database·Table·Column·FK·코멘트 enum 을 뽑는다. SQL 본문은 보관하지 않는다.

입력 둘: 로컬 devenv 덤프(최신, build/inputs/local_zzt-*.sql)와 문서 허브 덤프(reference/schema/*.sql).
둘 다 파싱해 합치고, 허브에만 있는 테이블·컬럼은 `missing-from-source` 로 표시한다(허브 덤프가 더 오래됐다).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from . import model
from .collect import Collector, edge_rec, node_rec

SOURCE = "schema@1"
DEFAULT_DB = "zzt"

TABLE_RE = re.compile(r"CREATE TABLE `(?P<name>[^`]+)` \((?P<body>.*?)\n\)(?P<tail>[^;]*);", re.S)
COL_RE = re.compile(r"^\s*`(?P<name>[^`]+)`\s+(?P<rest>.*?),?$")
TYPE_RE = re.compile(r"^(?P<type>[a-z]+(?:\([^)]*\))?(?:\s+unsigned)?(?:\s+zerofill)?)", re.I)
COMMENT_RE = re.compile(r"COMMENT '((?:[^']|'')*)'")
TABLE_COMMENT_RE = re.compile(r"COMMENT='((?:[^']|'')*)'")
PK_RE = re.compile(r"PRIMARY KEY \(([^)]*)\)")
FK_RE = re.compile(r"CONSTRAINT `(?P<fk>[^`]+)` FOREIGN KEY \(`(?P<col>[^`]+)`\) REFERENCES `(?P<rtable>[^`]+)` \(`(?P<rcol>[^`]+)`\)")
ENGINE_RE = re.compile(r"ENGINE=(\w+)")

# 코멘트에서 enum 을 읽는 두 가지 꼴
PAIR_RE = re.compile(r"(?<![\w가-힣])(?P<k>[A-Za-z0-9_]{1,24})\s*[:=]\s*(?P<v>[^,;/()\[\]]+?)(?=\s*[,;/)\]]|\s*$)")
LIST_TOKEN_RE = re.compile(r"^[a-z][a-z0-9_]*$")


@dataclass
class ColumnDef:
    name: str
    type: str
    nullable: bool
    comment: str | None
    ordinal: int
    is_pk: bool = False


@dataclass
class TableDef:
    name: str
    comment: str | None
    engine: str | None
    columns: list[ColumnDef] = field(default_factory=list)
    fks: list[tuple[str, str, str, str]] = field(default_factory=list)   # (col, ref_table, ref_col, fk_name)


def parse_dump(path: Path) -> dict[str, TableDef]:
    text = path.read_text(encoding="utf-8", errors="replace")
    tables: dict[str, TableDef] = {}
    for m in TABLE_RE.finditer(text):
        name, body, tail = m.group("name"), m.group("body"), m.group("tail")
        tcm = TABLE_COMMENT_RE.search(tail)
        eng = ENGINE_RE.search(tail)
        tdef = TableDef(name=name, comment=_unq(tcm.group(1)) if tcm else None, engine=eng.group(1) if eng else None)
        pk: set[str] = set()
        ordinal = 0
        for line in body.split("\n"):
            s = line.strip()
            if not s:
                continue
            if s.startswith("`"):
                cm = COL_RE.match(s)
                if not cm:
                    continue
                rest = cm.group("rest")
                tm = TYPE_RE.match(rest)
                ctype = tm.group("type").lower() if tm else rest.split()[0].lower()
                ccm = COMMENT_RE.search(rest)
                ordinal += 1
                tdef.columns.append(ColumnDef(
                    name=cm.group("name"), type=ctype, nullable="NOT NULL" not in rest,
                    comment=_unq(ccm.group(1)) if ccm else None, ordinal=ordinal,
                ))
            elif s.startswith("PRIMARY KEY"):
                pm = PK_RE.search(s)
                if pm:
                    pk = {c.strip("` ") for c in pm.group(1).split(",")}
            elif s.startswith("CONSTRAINT"):
                fm = FK_RE.search(s)
                if fm:
                    tdef.fks.append((fm.group("col"), fm.group("rtable"), fm.group("rcol"), fm.group("fk")))
        for c in tdef.columns:
            c.is_pk = c.name in pk
        tables[name] = tdef
    return tables


def _unq(s: str) -> str:
    return s.replace("''", "'").strip()


def enum_from_comment(comment: str | None, col_type: str) -> list[tuple[str, str | None]]:
    """`0: 대기, 1: 완료` 꼴 → [(값, 뜻)], `pending, recording, canceled` 꼴(문자열 컬럼) → [(값, None)]. 아니면 []."""
    if not comment:
        return []
    pairs = [(m.group("k"), m.group("v").strip()) for m in PAIR_RE.finditer(comment)]
    pairs = [(k, v) for k, v in pairs if v and len(v) <= 60]
    if len(pairs) >= 2 and len({k for k, _ in pairs}) == len(pairs):
        return pairs
    if col_type.startswith(("varchar", "char", "enum", "set")):
        tokens = [t.strip() for t in comment.split(",")]
        if len(tokens) >= 2 and all(LIST_TOKEN_RE.match(t) for t in tokens):
            return [(t, None) for t in tokens]
    return []


def extract(col: Collector, primary: Path | None, secondary: Path | None, db: str = DEFAULT_DB) -> dict[str, str]:
    """노드·관계를 col 에 넣고, 입력 메타(파일명·테이블 수)를 돌려준다."""
    meta: dict[str, str] = {}
    prim = parse_dump(primary) if primary else {}
    sec = parse_dump(secondary) if secondary else {}
    if primary:
        meta["primary"] = f"{primary.name} ({len(prim)} tables)"
    if secondary:
        meta["secondary"] = f"{secondary.name} ({len(sec)} tables)"
    if not prim and not sec:
        col.warn(SOURCE, "no schema dump found — skipping schema extraction")
        return meta

    col.node(node_rec(model.db_uid(db), "Database", db, SOURCE,
                      summary="운영 DB (Aurora MySQL). 레거시·신규 전부 이 DB 를 쓴다",
                      props={"handle": "$this->db", "engine": "MySQL"},
                      source_ref=primary.name if primary else secondary.name))

    names = sorted(set(prim) | set(sec))
    only_sec = [n for n in names if n not in prim and n in sec]
    only_prim = [n for n in names if n in prim and n not in sec]
    if secondary and primary:
        if only_sec:
            col.warn(SOURCE, f"{len(only_sec)} tables only in {secondary.name} (marked missing-from-source): {', '.join(only_sec[:20])}{' …' if len(only_sec) > 20 else ''}")
        if only_prim:
            col.warn(SOURCE, f"{len(only_prim)} tables only in {primary.name} (new since hub dump): {', '.join(only_prim[:20])}{' …' if len(only_prim) > 20 else ''}")

    for name in names:
        tdef = prim.get(name) or sec[name]
        ref_file = (primary if name in prim else secondary).name
        status = "active" if (name in prim or not primary) else "missing-from-source"
        tuid = model.table_uid(name)
        col.node(node_rec(tuid, "Table", name, SOURCE, summary=tdef.comment or None,
                          props={"db": db, "engine": tdef.engine, "comment": tdef.comment, "columnCount": len(tdef.columns)},
                          status=status, source_ref=f"{ref_file}:{name}"))
        col.edge(edge_rec(model.db_uid(db), "CONTAINS", tuid, SOURCE, status=status))
        sec_cols = {c.name for c in sec[name].columns} if name in sec else set()
        prim_cols = {c.name for c in prim[name].columns} if name in prim else set()
        cols = list(tdef.columns)
        # 허브에만 있는 컬럼(지워진 컬럼)도 missing-from-source 로 남긴다
        if name in prim and name in sec:
            for c in sec[name].columns:
                if c.name not in prim_cols:
                    cols.append(c)
        for c in cols:
            cstatus = status
            if name in prim and c.name not in prim_cols:
                cstatus = "missing-from-source"
            cuid = model.col_uid(name, c.name)
            props = {"type": c.type, "nullable": c.nullable, "isPk": c.is_pk, "ordinal": c.ordinal}
            if c.comment:
                props["comment"] = c.comment
            col.node(node_rec(cuid, "Column", c.name, SOURCE, props=props, status=cstatus, source_ref=f"{ref_file}:{name}.{c.name}"))
            col.edge(edge_rec(tuid, "HAS_COLUMN", cuid, SOURCE, props={"ordinal": c.ordinal}, status=cstatus))
            for value, meaning in enum_from_comment(c.comment, c.type):
                euid = model.enum_uid(name, c.name, value)
                eprops = {"value": value, "origin": "ddl-comment"}
                if meaning:
                    eprops["meaning"] = meaning
                col.node(node_rec(euid, "EnumValue", value, SOURCE, summary=meaning, props=eprops, status=cstatus,
                                  source_ref=f"{ref_file}:{name}.{c.name} COMMENT"))
                col.edge(edge_rec(cuid, "HAS_VALUE", euid, SOURCE, status=cstatus))
        for (c, rtable, rcol, fkname) in tdef.fks:
            col.edge(edge_rec(model.col_uid(name, c), "REFERENCES", model.col_uid(rtable, rcol), SOURCE,
                              props={"kind": "fk", "fkName": fkname}, status=status, source_ref=f"{ref_file}:{name} {fkname}"))
    meta["tables"] = str(len(names))
    return meta
