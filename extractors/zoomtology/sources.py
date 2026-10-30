"""입력 위치. 빌드는 Ken 의 메인 Mac 에서, 워크스페이스 `Service/` 의 형제 저장소를 읽는다."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

ZOOMTOLOGY = Path(__file__).resolve().parents[2]
SERVICE = ZOOMTOLOGY.parent                      # …/Zoomzoomtour/Service
HUB = SERVICE / "zoomzoom-services"
AGENT_PRISM = SERVICE.parent / "AgentPrism"
INPUTS = ZOOMTOLOGY / "build" / "inputs"
DIST = ZOOMTOLOGY / "build" / "dist"
LATEST = ZOOMTOLOGY / "build" / "latest"
STATE = ZOOMTOLOGY / "state"

HUB_REPO_NAME = "zoomzoom-services"


@dataclass(frozen=True)
class RepoRef:
    name: str
    path: Path

    def sha(self) -> str | None:
        return git_sha(self.path)


def git_sha(path: Path, short: bool = False) -> str | None:
    try:
        out = subprocess.run(
            ["git", "-C", str(path), "rev-parse", "--short" if short else "HEAD"] if short else ["git", "-C", str(path), "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        return out or None
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def git_dirty(path: Path) -> bool:
    try:
        out = subprocess.run(["git", "-C", str(path), "status", "--porcelain"], capture_output=True, text=True, check=True).stdout
        return bool(out.strip())
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def git_branch(path: Path) -> str | None:
    """현재 브랜치 이름. HEAD 가 분리됐거나 저장소가 아니면 None."""
    try:
        out = subprocess.run(["git", "-C", str(path), "branch", "--show-current"], capture_output=True, text=True, check=True).stdout.strip()
        return out or None
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def default_branches() -> dict[str, str]:
    """repos.tsv 의 저장소별 메인 브랜치. AgentPrism 처럼 표에 없는 저장소는 호출하는 쪽이 main 으로 본다."""
    path = HUB / "tools" / "repos.tsv"
    if not path.exists():
        return {}
    result: dict[str, str] = {}
    header: list[str] | None = None
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("#name"):
            header = line[1:].split("\t")
        elif line.strip() and not line.startswith("#") and header:
            rec = dict(zip(header, line.split("\t")))
            if rec.get("branch"):
                result[rec["name"]] = rec["branch"]
    return result


def latest_hub_dump() -> Path | None:
    dumps = sorted((HUB / "reference" / "schema").glob("*.sql"))
    return dumps[-1] if dumps else None


def latest_local_dump() -> Path | None:
    dumps = sorted(INPUTS.glob("local_zzt-*.sql"))
    return dumps[-1] if dumps else None
