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


def latest_hub_dump() -> Path | None:
    dumps = sorted((HUB / "reference" / "schema").glob("*.sql"))
    return dumps[-1] if dumps else None


def latest_local_dump() -> Path | None:
    dumps = sorted(INPUTS.glob("local_zzt-*.sql"))
    return dumps[-1] if dumps else None
