from __future__ import annotations

import threading
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from dress_agent.cli import run


@dataclass
class RunState:
    id: str | None = None
    status: str = "idle"
    started_at: str | None = None
    finished_at: str | None = None
    markdown_report: str | None = None
    json_report: str | None = None
    error: str | None = None
    selected_sites: list[str] | None = None


class AgentRunner:
    def __init__(self, config_path: str | Path = "config.yaml") -> None:
        self.config_path = config_path
        self._state = RunState()
        self._lock = threading.Lock()

    def state(self) -> dict:
        with self._lock:
            return asdict(self._state)

    def start(self, selected_sites: list[str]) -> dict:
        with self._lock:
            if self._state.status == "running":
                return asdict(self._state)
            self._state = RunState(
                id=uuid.uuid4().hex,
                status="running",
                started_at=_now(),
                selected_sites=selected_sites,
            )
            state = asdict(self._state)
        threading.Thread(
            target=self._execute, args=(set(selected_sites),), daemon=True
        ).start()
        return state

    def _execute(self, selected_sites: set[str]) -> None:
        try:
            markdown_path, json_path = run(self.config_path, selected_sites)
        except Exception as error:
            with self._lock:
                self._state.status = "failed"
                self._state.finished_at = _now()
                self._state.error = str(error)
            return
        with self._lock:
            self._state.status = "completed"
            self._state.finished_at = _now()
            self._state.markdown_report = str(markdown_path)
            self._state.json_report = str(json_path)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
