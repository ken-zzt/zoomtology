"""노드·관계 자료형과 uid 생성기. uid 규칙은 ontology/uid.md 가 원본이다."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

Props = dict[str, Any]


@dataclass
class Node:
    uid: str
    label: str
    name: str
    source: str
    summary: str | None = None
    props: Props = field(default_factory=dict)
    confidence: str = "auto"
    status: str = "active"
    sourceRef: str | None = None
    firstSeenAt: date | None = None
    lastSeenAt: date | None = None
    lastVerifiedAt: date | None = None

    def to_record(self) -> dict[str, Any]:
        rec: dict[str, Any] = {
            "uid": self.uid,
            "label": self.label,
            "name": self.name,
            "summary": self.summary,
            "props": self.props,
            "source": self.source,
            "confidence": self.confidence,
            "status": self.status,
            "sourceRef": self.sourceRef,
            "firstSeenAt": _d(self.firstSeenAt),
            "lastSeenAt": _d(self.lastSeenAt),
            "lastVerifiedAt": _d(self.lastVerifiedAt),
        }
        return rec


@dataclass
class Edge:
    from_uid: str
    type: str
    to_uid: str
    source: str
    props: Props = field(default_factory=dict)
    confidence: str = "auto"
    status: str = "active"
    sourceRef: str | None = None
    firstSeenAt: date | None = None
    lastSeenAt: date | None = None
    lastVerifiedAt: date | None = None

    @property
    def key(self) -> tuple[str, str, str]:
        return (self.from_uid, self.type, self.to_uid)

    def to_record(self) -> dict[str, Any]:
        return {
            "from": self.from_uid,
            "type": self.type,
            "to": self.to_uid,
            "props": self.props,
            "source": self.source,
            "confidence": self.confidence,
            "status": self.status,
            "sourceRef": self.sourceRef,
            "firstSeenAt": _d(self.firstSeenAt),
            "lastSeenAt": _d(self.lastSeenAt),
            "lastVerifiedAt": _d(self.lastVerifiedAt),
        }


def _d(value: date | None) -> str | None:
    return value.isoformat() if value else None


# --- uid 생성기 (ontology/uid.md) ---------------------------------------------

def repo_uid(name: str) -> str:
    return f"repo:{name}"


def service_uid(repo: str, instance: str) -> str:
    return f"svc:{repo}/{instance}"


def file_uid(repo: str, path: str) -> str:
    return f"file:{repo}/{path.lstrip('/')}"


def code_uid(repo: str, path: str, symbol: str, method: str | None = None) -> str:
    tail = f"{symbol}::{method}" if method else symbol
    return f"code:{repo}/{path.lstrip('/')}#{tail}"


def route_uid(repo: str, method: str, path: str) -> str:
    """HTTP 라우트. method 는 대문자, path 는 선행 `/` 포함."""
    return f"route:{repo} {method.upper()} {path}"


def opencart_route_uid(repo: str, route: str) -> str:
    """OpenCart 라우트 `폴더/파일/메서드` (index 는 `폴더/파일` 로도 등록한다)."""
    return f"route:{repo} route={route}"


def queue_uid(role: str) -> str:
    return f"queue:{role}"


def msg_uid(role: str, key: str) -> str:
    return f"msg:{role}/{key}"


def cron_uid(host: str, target: str) -> str:
    return f"cron:{host}/{target}"


def db_uid(handle: str) -> str:
    return f"db:{handle}"


def table_uid(name: str, db: str | None = None) -> str:
    return f"table:{db}/{name}" if db else f"table:{name}"


def col_uid(table: str, column: str) -> str:
    return f"col:{table}.{column}"


def enum_uid(table: str, column: str, value: str | int) -> str:
    return f"enum:{table}.{column}={value}"


def rule_uid(slug: str) -> str:
    return f"rule:{slug}"


def domain_uid(slug: str) -> str:
    return f"domain:{slug}"


def ext_uid(slug: str) -> str:
    return f"ext:{slug}"


def doc_uid(repo: str, path: str, section: str | None = None) -> str:
    base = f"doc:{repo}/{path.lstrip('/')}"
    return f"{base}#{section}" if section else base
