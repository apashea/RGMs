#!/usr/bin/env python3
"""Focused C4l PolicyExecutionContext contracts (no MATLAB Engine)."""
from __future__ import annotations

from python_src.optimized.toolbox.DEM.vb_forwards_optim import (
    POLICY_CTX_BUNDLE_KEY,
    PolicyExecutionContext,
    policy_ctx_attach,
    policy_ctx_clear,
    policy_ctx_get,
)


def test_policy_ctx_attach_reuse_and_clear():
    bundle: dict = {}
    ctx = policy_ctx_attach(bundle)
    assert isinstance(ctx, PolicyExecutionContext)
    assert bundle[POLICY_CTX_BUNDLE_KEY] is ctx
    assert policy_ctx_get(bundle) is ctx
    # Re-attach without new ctx reuses the same object.
    assert policy_ctx_attach(bundle) is ctx
    policy_ctx_clear(bundle)
    assert POLICY_CTX_BUNDLE_KEY not in bundle
    assert policy_ctx_get(bundle) is None


def test_policy_ctx_dirty_gens_invalidate_built_markers():
    ctx = PolicyExecutionContext()
    ctx.likelihood_built_gen[0] = ctx.likelihood_gen
    ctx.propagator_built_gen[0] = ctx.propagator_gen
    ctx.mark_propagator_dirty()
    assert ctx.propagator_built_gen[0] != ctx.propagator_gen
    assert ctx.likelihood_built_gen[0] == ctx.likelihood_gen
    ctx.mark_likelihood_dirty()
    assert ctx.likelihood_built_gen[0] != ctx.likelihood_gen
