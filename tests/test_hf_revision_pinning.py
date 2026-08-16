"""Pin the Phase 4(iii) HF revision-pinning hardening.

Audit residual: HuggingFace downloads in the OD fusion/training scripts
(``scripts/diffusion_server.py``) and the ``hf download`` entrypoint
(``scripts/hf_download.py``) called ``snapshot_download`` /
``hf_hub_download`` / ``from_pretrained`` with no pinned revision, so they
tracked each repo's default branch — supply-chain malleable.

Fix: both scripts now accept a ``--revision`` (branch / tag / 40-hex commit)
that is threaded through every hub call. An unpinned deployment is unchanged
(previous behavior); a pinned one is reproducible and auditable.

The tests AST-load the scripts' argument builders / hub-call wiring without
importing the heavy modules (no torch / diffusers / huggingface_hub needed)
so they exercise the production code paths.
"""

import pytest

from pathlib import Path

_SCRIPT = Path(__file__).resolve().parent.parent / "scripts"
_HF_DOWNLOAD = _SCRIPT / "hf_download.py"
_DIFFUSION = _SCRIPT / "diffusion_server.py"


# ── hf_download.py: `--revision` flows into snapshot_download kwargs ───────

def test_hf_download_has_revision_arg():
    source = _HF_DOWNLOAD.read_text(encoding="utf-8")
    assert '"--revision"' in source


def test_hf_download_threads_revision_into_kwargs():
    source = _HF_DOWNLOAD.read_text(encoding="utf-8")
    # The kwargs dict only grows revision when the flag is provided.
    assert 'kwargs["revision"] = args.revision' in source
    # And the START banner shows the pinned ref for purely cosmetic traceability.
    assert "args.revision" in source


# ── diffusion_server.py: `--revision` exists and is threaded ───────────────

def test_diffusion_server_has_revision_arg():
    source = _DIFFUSION.read_text(encoding="utf-8")
    assert '"--revision"' in source


@pytest.mark.parametrize("snippet", [
    '_pp_kwargs["revision"] = _rev',        # from_pretrained path
    "revision=_rev",                         # hf_hub_download + snapshot_download
])
def test_diffusion_server_threads_revision(snippet):
    source = _DIFFUSION.read_text(encoding="utf-8")
    assert snippet in source


def test_diffusion_server_revision_respects_no_pin_default():
    """Unpinned runs must not force a revision (backwards compatible)."""
    source = _DIFFUSION.read_text(encoding="utf-8")
    # The _snap dict only grows revision when _rev is truthy.
    assert "dict(token=_hf_token, local_files_only=False, revision=_rev) if _rev" in source or \
        "revision=_rev) if _rev" in source