"""ontology/schema.yaml 로 노드·관계 레코드를 검증한다.

빌드(build.py)와 테스트가 쓴다. Prism 로더는 같은 규칙을 TypeScript(zod)로 다시 검사한다.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import yaml

SCHEMA_PATH = Path(__file__).resolve().parents[2] / "ontology" / "schema.yaml"
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


@dataclass(frozen=True)
class Problem:
    where: str      # uid 또는 "from -TYPE-> to"
    message: str

    def __str__(self) -> str:
        return f"{self.where}: {self.message}"


class Schema:
    def __init__(self, raw: dict[str, Any]):
        self.raw = raw
        self.version: int = raw["schemaVersion"]
        self.labels: dict[str, dict[str, Any]] = raw["labels"]
        self.edges: dict[str, dict[str, Any]] = raw["edges"]
        self.governance: dict[str, dict[str, Any]] = raw["governance"]
        self.reserved: list[str] = raw.get("reserved_prefixes", [])
        self._uid_re = {label: re.compile(spec["uid"]) for label, spec in self.labels.items()}
        self._source_re = re.compile(self.governance["source"]["pattern"])
        guard = raw.get("content_guard", {})
        self.max_prop_length: int = guard.get("max_prop_length", 2000)
        self._deny_re = [re.compile(p) for p in guard.get("deny_patterns", [])]
        self.deny_paths: list[str] = guard.get("deny_paths", [])

    @classmethod
    def load(cls, path: Path = SCHEMA_PATH) -> "Schema":
        with path.open(encoding="utf-8") as fh:
            return cls(yaml.safe_load(fh))

    # --- 노드 -----------------------------------------------------------------

    def check_node(self, rec: dict[str, Any]) -> list[Problem]:
        uid = str(rec.get("uid", "<no uid>"))
        problems: list[Problem] = []
        label = rec.get("label")
        if label not in self.labels:
            return [Problem(uid, f"unknown label {label!r}")]
        if any(uid.startswith(p) for p in self.reserved):
            problems.append(Problem(uid, "reserved prefix — not allowed in v1"))
        if not self._uid_re[label].match(uid):
            problems.append(Problem(uid, f"uid does not match {label} pattern {self.labels[label]['uid']}"))
        if not rec.get("name"):
            problems.append(Problem(uid, "name is required"))
        props = rec.get("props") or {}
        if not isinstance(props, dict):
            problems.append(Problem(uid, "props must be an object"))
            props = {}
        for key in self.labels[label].get("required", []):
            if key not in props:
                problems.append(Problem(uid, f"missing required prop {key!r}"))
        for key in self.labels[label].get("forbidden_props", []):
            if key in props:
                problems.append(Problem(uid, f"forbidden prop {key!r}"))
        kinds = self.labels[label].get("kinds")
        if kinds and "kind" in props and props["kind"] not in kinds:
            problems.append(Problem(uid, f"kind {props['kind']!r} not in {kinds}"))
        origins = self.labels[label].get("origins")
        if origins and "origin" in props and props["origin"] not in origins:
            problems.append(Problem(uid, f"origin {props['origin']!r} not in {origins}"))
        problems += self._check_governance(uid, rec)
        problems += self.check_content(uid, props)
        for key in ("name", "summary"):
            if rec.get(key):
                problems += self.check_content(uid, {key: rec[key]})
        return problems

    # --- 관계 -----------------------------------------------------------------

    def check_edge(self, rec: dict[str, Any], labels_by_uid: dict[str, str] | None = None) -> list[Problem]:
        etype = rec.get("type")
        where = f"{rec.get('from')} -{etype}-> {rec.get('to')}"
        if etype not in self.edges:
            return [Problem(where, f"unknown edge type {etype!r}")]
        problems: list[Problem] = []
        spec = self.edges[etype]
        for end in ("from", "to"):
            if not rec.get(end):
                problems.append(Problem(where, f"{end} is required"))
        if labels_by_uid is not None:
            for end in ("from", "to"):
                uid = rec.get(end)
                label = labels_by_uid.get(uid)
                if label is None:
                    problems.append(Problem(where, f"{end} uid not found in nodes"))
                elif label not in spec[end]:
                    problems.append(Problem(where, f"{end} label {label} not allowed for {etype} (allowed: {spec[end]})"))
            pairs = spec.get("pairs")
            if pairs and not problems:
                pair = [labels_by_uid[rec["from"]], labels_by_uid[rec["to"]]]
                if pair not in pairs:
                    problems.append(Problem(where, f"label pair {pair} not allowed for {etype}"))
        problems += self._check_governance(where, rec)
        problems += self.check_content(where, rec.get("props") or {})
        return problems

    # --- 공통 -----------------------------------------------------------------

    def _check_governance(self, where: str, rec: dict[str, Any]) -> list[Problem]:
        problems: list[Problem] = []
        for key, spec in self.governance.items():
            value = rec.get(key)
            if value in (None, ""):
                if spec.get("required"):
                    problems.append(Problem(where, f"missing governance field {key!r}"))
                continue
            if "enum" in spec and value not in spec["enum"]:
                problems.append(Problem(where, f"{key}={value!r} not in {spec['enum']}"))
            if spec.get("type") == "date" and not DATE_RE.match(str(value)):
                problems.append(Problem(where, f"{key} must be YYYY-MM-DD, got {value!r}"))
        if rec.get("source") and not self._source_re.match(str(rec["source"])):
            problems.append(Problem(where, f"source {rec['source']!r} does not match pattern"))
        if rec.get("confidence") == "verified" and not rec.get("lastVerifiedAt"):
            problems.append(Problem(where, "confidence=verified requires lastVerifiedAt"))
        return problems

    def check_content(self, where: str, props: dict[str, Any]) -> list[Problem]:
        """코드 본문·SQL·비밀 값이 섞이지 않았는지 (content_guard)."""
        problems: list[Problem] = []
        for key, value in _walk_strings(props):
            if len(value) > self.max_prop_length:
                problems.append(Problem(where, f"prop {key} longer than {self.max_prop_length} chars"))
            for rx in self._deny_re:
                if rx.search(value):
                    problems.append(Problem(where, f"prop {key} matches denied pattern {rx.pattern[:40]!r}"))
                    break
        return problems

    def check_bundle(self, nodes: Iterable[dict[str, Any]], edges: Iterable[dict[str, Any]]) -> list[Problem]:
        problems: list[Problem] = []
        labels_by_uid: dict[str, str] = {}
        for rec in nodes:
            problems += self.check_node(rec)
            uid = rec.get("uid")
            if uid in labels_by_uid:
                problems.append(Problem(str(uid), "duplicate uid"))
            labels_by_uid[uid] = rec.get("label")
        seen: set[tuple[str, str, str]] = set()
        for rec in edges:
            problems += self.check_edge(rec, labels_by_uid)
            key = (rec.get("from"), rec.get("type"), rec.get("to"))
            if key in seen:
                problems.append(Problem(f"{key[0]} -{key[1]}-> {key[2]}", "duplicate edge"))
            seen.add(key)
        return problems


def _walk_strings(value: Any, prefix: str = "") -> Iterable[tuple[str, str]]:
    if isinstance(value, str):
        yield prefix or "<value>", value
    elif isinstance(value, dict):
        for k, v in value.items():
            yield from _walk_strings(v, f"{prefix}.{k}" if prefix else str(k))
    elif isinstance(value, (list, tuple)):
        for i, v in enumerate(value):
            yield from _walk_strings(v, f"{prefix}[{i}]")
