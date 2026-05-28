"""Stub for ``spm_figure.m`` — window title + clear; not full SPM graphics stack."""

from __future__ import annotations

from typing import Any, Dict, Optional

import matplotlib.pyplot as plt


_FIGURES: Dict[str, Any] = {}


def spm_figure(*args: Any, **kwargs: Any) -> Any:
    """Mirror ``spm_figure('GetWin', title)`` enough for DEM plotting."""
    title: Optional[str] = None
    if len(args) >= 2 and str(args[0]).lower() in ("getwin", "get win"):
        title = str(args[1])
    elif len(args) >= 1:
        title = str(args[0])
    if title is None:
        title = "SPM"
    fig = _FIGURES.get(title)
    if fig is None or not plt.fignum_exists(fig.number):
        fig = plt.figure(title)
        _FIGURES[title] = fig
    else:
        plt.figure(fig.number)
    return fig


def spm_figure_clf(title: Optional[str] = None) -> None:
    """``clf`` on the active or named figure."""
    if title is not None:
        spm_figure("GetWin", title)
    plt.clf()
