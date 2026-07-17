"""Optional driver hooks for long DEM_AtariIII ledger loops (Entries 8–9)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class DemAtariLedgerHooks:
    """No-op defaults for FSL isolated runners; driver passes label/deadline hooks."""

    set_label: Callable[[str], None]
    deadline_check: Callable[[], None]

    @staticmethod
    def noop() -> DemAtariLedgerHooks:
        return DemAtariLedgerHooks(set_label=lambda _s: None, deadline_check=lambda: None)
