"""추출기 출력을 모으고 같은 uid/관계를 병합한다. 우선순위 manual > doc > extractor (ADR 0005)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

Record = dict[str, Any]


def precedence(source: str) -> int:
    if source == "manual":
        return 3
    if source.startswith("doc:"):
        return 2
    return 1


def _merge_props(dst: dict[str, Any], src: dict[str, Any], dst_wins: bool) -> None:
    for key, value in src.items():
        if key not in dst or dst[key] in (None, "", [], {}):
            dst[key] = value
        elif isinstance(dst[key], list) and isinstance(value, list):
            for item in value:
                if item not in dst[key]:
                    dst[key].append(item)
        elif isinstance(dst[key], dict) and isinstance(value, dict):
            _merge_props(dst[key], value, dst_wins)
        elif not dst_wins and dst[key] != value:
            dst[key] = value


@dataclass
class Warning_:
    extractor: str
    message: str


@dataclass
class Collector:
    nodes: dict[str, Record] = field(default_factory=dict)
    edges: dict[tuple[str, str, str], Record] = field(default_factory=dict)
    warnings: list[Warning_] = field(default_factory=list)
    # 노드가 없을 때 만들지 않고 버린 부분 레코드(uid, source)
    dropped_partials: list[tuple[str, str]] = field(default_factory=list)

    def warn(self, extractor: str, message: str) -> None:
        self.warnings.append(Warning_(extractor, message))

    def node(self, rec: Record, partial: bool = False) -> None:
        """partial=True 면 이미 있는 노드에 props/summary 만 보탠다. 없으면 버린다(빌드 끝에 report)."""
        uid = rec["uid"]
        rec.setdefault("props", {})
        existing = self.nodes.get(uid)
        if existing is None:
            if partial:
                self.dropped_partials.append((uid, rec.get("source", "?")))
                return
            self.nodes[uid] = rec
            return
        self._merge_node(existing, rec)

    def _merge_node(self, dst: Record, src: Record) -> None:
        """값 우선순위는 manual > doc > extractor. 노드의 source/sourceRef 는 처음 만든 쪽(보통 추출기)을 유지하고,
        우선순위가 높은 쪽이 바꾼 값은 props.alt[<밀린 source>] 에 이전 값을 남긴다."""
        if dst.get("label") != src.get("label"):
            self.warn(src.get("source", "?"), f"{dst['uid']}: label conflict {dst.get('label')} vs {src.get('label')} — kept {dst.get('label')}")
        pd, ps = precedence(dst.get("source", "")), precedence(src.get("source", ""))
        if ps > pd:
            overridden = {}
            for key in ("summary", "status", "confidence", "lastVerifiedAt"):
                if src.get(key) not in (None, "") and dst.get(key) not in (None, "") and dst[key] != src[key]:
                    overridden[key] = dst[key]
                if src.get(key) not in (None, ""):
                    dst[key] = src[key]
            for key, value in src["props"].items():
                if key in dst["props"] and dst["props"][key] not in (None, "", [], {}) and dst["props"][key] != value and not isinstance(value, (list, dict)):
                    overridden.setdefault("props", {})[key] = dst["props"][key]
            _merge_props(dst["props"], src["props"], dst_wins=False)
            if overridden:
                dst["props"].setdefault("alt", {})[dst.get("source", "?")] = overridden
            dst["props"].setdefault("docRefs", [])
            if src.get("sourceRef") and src["sourceRef"] not in dst["props"]["docRefs"]:
                dst["props"]["docRefs"].append(src["sourceRef"])
            return
        if ps < pd:
            overridden = {}
            for key in ("summary", "status"):
                if src.get(key) not in (None, "") and dst.get(key) not in (None, "") and dst[key] != src[key]:
                    overridden[key] = src[key]
            if overridden:
                dst["props"].setdefault("alt", {})[src.get("source", "?")] = overridden
            _merge_props(dst["props"], src["props"], dst_wins=True)
            if not dst.get("summary") and src.get("summary"):
                dst["summary"] = src["summary"]
            return
        # 같은 등급: 먼저 온 것이 이기되 빈 칸은 채운다
        for key in ("summary", "sourceRef", "lastVerifiedAt"):
            if not dst.get(key) and src.get(key):
                dst[key] = src[key]
        if src.get("status") == "retired":
            dst["status"] = "retired"
        _merge_props(dst["props"], src["props"], dst_wins=True)

    def edge(self, rec: Record) -> None:
        rec.setdefault("props", {})
        key = (rec["from"], rec["type"], rec["to"])
        existing = self.edges.get(key)
        if existing is None:
            self.edges[key] = rec
            return
        pd, ps = precedence(existing.get("source", "")), precedence(rec.get("source", ""))
        if ps > pd:
            for k in ("source", "confidence", "status", "lastVerifiedAt", "sourceRef"):
                if rec.get(k) not in (None, ""):
                    existing[k] = rec[k]
            _merge_props(existing["props"], rec["props"], dst_wins=False)
        else:
            _merge_props(existing["props"], rec["props"], dst_wins=True)
            if not existing.get("sourceRef") and rec.get("sourceRef"):
                existing["sourceRef"] = rec["sourceRef"]


def node_rec(uid: str, label: str, name: str, source: str, *, summary: str | None = None,
             props: dict[str, Any] | None = None, confidence: str = "auto", status: str = "active",
             source_ref: str | None = None, last_verified_at: str | None = None) -> Record:
    return {
        "uid": uid, "label": label, "name": name, "summary": summary, "props": props or {},
        "source": source, "confidence": confidence, "status": status, "sourceRef": source_ref,
        "firstSeenAt": None, "lastSeenAt": None, "lastVerifiedAt": last_verified_at,
    }


def edge_rec(from_uid: str, etype: str, to_uid: str, source: str, *, props: dict[str, Any] | None = None,
             confidence: str = "auto", status: str = "active", source_ref: str | None = None,
             last_verified_at: str | None = None) -> Record:
    return {
        "from": from_uid, "type": etype, "to": to_uid, "props": props or {},
        "source": source, "confidence": confidence, "status": status, "sourceRef": source_ref,
        "firstSeenAt": None, "lastSeenAt": None, "lastVerifiedAt": last_verified_at,
    }
