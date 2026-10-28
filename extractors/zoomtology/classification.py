"""AgentPrism classification/tables.yaml → Table.summary(desc)·Column.piiRule·Table.pii. 부분 레코드만 낸다(노드를 새로 만들지 않는다)."""

from __future__ import annotations

from pathlib import Path

import yaml

from . import model
from .collect import Collector, node_rec

SOURCE = "classification@1"


def extract(col: Collector, path: Path) -> dict[str, str]:
    if not path.exists():
        col.warn(SOURCE, f"classification file not found: {path}")
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    ref = f"AgentPrism/classification/{path.name}"
    excluded = data.get("excluded") or {}
    for table, reason in excluded.items():
        col.node(node_rec(model.table_uid(table), "Table", table, SOURCE, summary=None,
                          props={"pii": "excluded", "piiExcludedReason": str(reason)}, source_ref=ref), partial=True)
    tables = data.get("tables") or {}
    for table, spec in tables.items():
        spec = spec or {}
        rules = spec.get("columns") or {}
        kinds = set()
        for column, rule in rules.items():
            if isinstance(rule, dict):
                r, desc = rule.get("rule", "pass"), rule.get("desc")
            else:
                r, desc = str(rule), None
            kinds.add(r)
            props = {"piiRule": r}
            if desc:
                props["meaning"] = desc
            col.node(node_rec(model.col_uid(table, column), "Column", column, SOURCE, props=props, source_ref=ref), partial=True)
        pii = "none" if kinds <= {"pass"} else ("masked" if "hide" not in kinds else "hidden-columns")
        tprops = {"pii": pii, "piiAuto": bool(spec.get("auto"))}
        col.node(node_rec(model.table_uid(table), "Table", table, SOURCE, summary=spec.get("desc") or None,
                          props=tprops, source_ref=ref), partial=True)
    return {"classified": str(len(tables)), "excluded": str(len(excluded))}
