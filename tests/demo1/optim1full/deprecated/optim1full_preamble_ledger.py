"""DEPRECATED — off OPTIM1FULL lane (fidelity ``python_src`` hot path).

OPTIM1FULL preamble is ``run_dem_atariiii_optim(entry_stop=11)`` + ledger replay
(``OPTIM1.md`` § **11**). Do not use this MATLAB inline port for sign-off runs.
Moved here 2026-06-25 after erroneous fidelity ``spm_MDP_generate`` use.
"""

raise ImportError(
    "optim1full_preamble_ledger is deprecated — use run_optim1full_ledger_preamble "
    "(run_dem_atariiii_optim + vb_call1 segment reuse) per OPTIM1.md § 11"
)
