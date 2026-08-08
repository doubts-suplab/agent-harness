"""Cross-process kill switch backed by a shared signal file (spec §7.6).

`is_engaged` checks the filesystem on every call, so a trip in one process (or by an operator running
`touch`) propagates to every process that shares the path — the switch stops the whole deployment
without a code deploy. A file is the least-dependency shared signal; a DB/Redis adapter follows the
same `KillSwitchPort` contract.
"""

from __future__ import annotations

from pathlib import Path


class FileKillSwitch:
    """Engaged iff the signal file exists. Reads fresh each call, so trips propagate across processes."""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)

    def is_engaged(self) -> bool:
        return self._path.exists()

    def engage(self) -> None:
        """Trip the switch — creates the signal file (idempotent)."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.touch()

    def disengage(self) -> None:
        """Clear the switch — removes the signal file (idempotent)."""
        self._path.unlink(missing_ok=True)

    @property
    def path(self) -> Path:
        return self._path
