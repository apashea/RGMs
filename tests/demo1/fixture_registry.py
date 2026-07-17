"""DEMO1 parity fixture registry — shipped Python module (no tracked JSON).

Lists Phase A–D artifacts, producers, and dependencies for ``DEM_AtariIII_demo1_parity.py``.
Runtime ``entry12_signoff_manifest_*.json`` is generated under the fixture root and gitignored.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from tests.demo1.demo1_paths import demo1_fixtures_dir, demo1_repo_root, demo1_shipped_parity_png


@dataclass(frozen=True)
class FixtureArtifact:
    artifact_id: str
    relative_path: str
    phase: str
    producer: str
    skip_if_present: bool = True
    depends_on: tuple[str, ...] = ()

    def path(self, fixtures: Path | None = None) -> Path:
        if self.artifact_id == "D3_png":
            return demo1_shipped_parity_png()
        if self.artifact_id == "C4_compare":
            return demo1_repo_root() / "matlab_custom" / "XXX_12_compare_pdp_pkl_to_mat_output.txt"
        root = fixtures or demo1_fixtures_dir()
        rel = self.relative_path
        if rel.endswith("/"):
            return root / rel.rstrip("/")
        return root / rel


def _phase_a() -> tuple[FixtureArtifact, ...]:
    pre10 = "DEMAtariIII_fsl_backward_MDP_pre_entry10.mat"
    return (
        FixtureArtifact("A1_pre_entry10", pre10, "A", "matlab_custom/fsl_backward/dump_MDP_pre_entry10.m"),
        FixtureArtifact("A2_patch_entry1", pre10, "A", "matlab_custom/fsl_backward/patch_entry1_authority_to_pre_entry10_mat.m", depends_on=("A1_pre_entry10",)),
        FixtureArtifact("A3_patch_entry2", pre10, "A", "matlab_custom/fsl_backward/patch_entry2_authority_to_pre_entry10_mat.m", depends_on=("A1_pre_entry10",)),
        FixtureArtifact("A5_patch_entry5", pre10, "A", "matlab_custom/fsl_backward/patch_mdp_pre_entry5_to_pre_entry10_mat.m", depends_on=("A1_pre_entry10",)),
        FixtureArtifact("A4_patch_entry6", pre10, "A", "matlab_custom/fsl_backward/patch_entry6_authority_to_pre_entry10_mat.m", depends_on=("A1_pre_entry10",)),
        FixtureArtifact("A6_pre_entry11", "DEMAtariIII_fsl_backward_MDP_pre_entry11.mat", "A", "matlab_custom/fsl_backward/dump_MDP_pre_entry11.m"),
        FixtureArtifact("A7_rand_buf", "dem_atari_rand_buf_through_entry11.mat", "A", "matlab_custom/fsl_backward/capture_dem_atari_rand_buf_through_entry11.m"),
        FixtureArtifact("A8_plot_ctx", "DEMAtariIII_fsl_1_11_plot_ctx.mat", "A", "matlab_custom/dump_plot_ctx_DEM_AtariIII_FSL_1_11.m"),
        FixtureArtifact("A9_rdp", "DEMAtariIII_XXX_12_rdp.mat", "A", "matlab_custom/entry12/DEMAtariIII_entry12_dump_all_subentries.m (SKIP_CALL2=1)"),
        FixtureArtifact("A9_vb_k", "entry12_vb_rand_K.mat", "A", "tests/oracle/toolbox/DEM/entry12_preflight_vb_rand_k.py", depends_on=("A9_rdp",)),
        FixtureArtifact("A9_capture", "DEMAtariIII_entry12_rgms_canonical_12A.mat", "A", "matlab_custom/entry12/DEMAtariIII_entry12_dump_all_subentries.m", depends_on=("A9_vb_k",)),
        FixtureArtifact("A10_12plot", "DEMAtariIII_entry12_rgms_canonical_12PLOT.mat", "A", "matlab_custom/entry12/DEMAtariIII_entry12_12plot_capture.m", depends_on=("A9_capture",)),
    )


def _phase_b_entry(n: int) -> tuple[FixtureArtifact, ...]:
    return (
        FixtureArtifact(f"B{n}_pre_pkl", f"DEMAtariIII_fsl_backward_MDP_pre_entry{n}.pkl", "B", f"fsl_backward_materialize_mdp_pre_entry{n}_pkl.py"),
        FixtureArtifact(f"B{n}_post", f"DEMAtariIII_fsl_backward_entry{n}_post.pkl", "B", f"fsl_backward_run_entry{n}_isolated.py"),
        FixtureArtifact(f"B{n}_compare", f"DEMAtariIII_fsl_backward_entry{n}_post.pkl", "B", f"fsl_backward_compare_entry{n}_pkl_to_mat.py"),
    )


def _phase_b_entry89() -> tuple[FixtureArtifact, ...]:
    """Full-driver path: merge+basin combined loop (``run_entry9_from_boundary``)."""
    return (
        FixtureArtifact(
            "B89_pre_pkl",
            "DEMAtariIII_fsl_backward_MDP_pre_entry9.pkl",
            "B",
            "fsl_backward_materialize_mdp_pre_entry9_pkl.py",
        ),
        FixtureArtifact(
            "B89_post",
            "DEMAtariIII_fsl_backward_entry9_post.pkl",
            "B",
            "fsl_backward_run_entry9_isolated.py",
        ),
        FixtureArtifact(
            "B89_compare",
            "DEMAtariIII_fsl_backward_entry9_post.pkl",
            "B",
            "fsl_backward_compare_entry9_pkl_to_mat.py",
        ),
    )


def all_artifacts() -> tuple[FixtureArtifact, ...]:
    items: list[FixtureArtifact] = list(_phase_a())
    for n in range(1, 12):
        if n == 8:
            items.extend(_phase_b_entry89())
            continue
        if n == 9:
            continue
        items.extend(_phase_b_entry(n))
    # Entry 11 isolated runner writes ``entry11_rdp.pkl`` (RDP only), not ``entry11_post.pkl``.
    for i, art in enumerate(items):
        if art.artifact_id in ("B11_post", "B11_compare"):
            items[i] = FixtureArtifact(
                art.artifact_id,
                "DEMAtariIII_fsl_backward_entry11_rdp.pkl",
                art.phase,
                art.producer,
                art.skip_if_present,
                art.depends_on,
            )
    items.extend(
        (
            FixtureArtifact("B11_gate", "fsl_backward_entry11_entry12_vb/", "B", "fsl_backward_validate_entry11_through_entry12.py"),
            FixtureArtifact("C1a_k", "entry12_vb_rand_K.mat", "C", "entry12_preflight_vb_rand_k.py"),
            FixtureArtifact("C3_pdp", "DEMAtariIII_XXX_12_pdp.pkl", "C", "test_DEM_AtariIII_XXX_12.py"),
            FixtureArtifact("C4_compare", "matlab_custom/XXX_12_compare_pdp_pkl_to_mat_output.txt", "C", "XXX_12_compare_pdp_pkl_to_mat.py"),
            FixtureArtifact("D1_pytest", "DEMAtariIII_entry12_rgms_canonical_12PLOT.mat", "D", "test_spm_show_RGB_entry12plot.py"),
            FixtureArtifact("D3_png", demo1_shipped_parity_png().name, "D", "entry12_plot.run_entry12plot_phase_b_visual_review"),
        )
    )
    return tuple(items)


def artifact_by_id(artifact_id: str) -> FixtureArtifact:
    for art in all_artifacts():
        if art.artifact_id == artifact_id:
            return art
    raise KeyError(f"unknown DEMO1 artifact id: {artifact_id!r}")


def missing_artifacts(fixtures: Path | None = None) -> list[FixtureArtifact]:
    root = fixtures or demo1_fixtures_dir()
    out: list[FixtureArtifact] = []
    for art in all_artifacts():
        p = art.path(root)
        if art.relative_path.endswith("/"):
            if not p.is_dir():
                out.append(art)
        elif not p.is_file():
            out.append(art)
    return out
