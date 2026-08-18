import copy

import pytest

from acfqp.construction_k7_residual_factor_library_v62 import (
    ResidualFactorLibraryArtifactV62,
    freeze_residual_factor_library_v62,
    verify_residual_factor_library_v62,
)


@pytest.mark.skipif(
    __import__("os").environ.get("ACFQP_RUN_REAL_RESIDUAL_LIBRARY") != "1",
    reason="explicit retrospective three-source library construction",
)
def test_v62_freezes_honest_partial_development_library():
    artifact = verify_residual_factor_library_v62(
        freeze_residual_factor_library_v62()
    )
    document = artifact.to_document()
    assert document["evidence_boundary"]["retrospective_development_only"] is True
    assert document["evidence_boundary"]["fresh_held_out_sample_tax_claim_present"] is False
    assert document["compiled_library"]["all_observed_residual_targets_covered"] is False
    assert len(document["compiled_library"]["covered_residual_targets"]) == 3
    assert len(document["compiled_library"]["uncovered_residual_targets"]) == 3
    assert document["official_execution_allowed"] is False
    assert document["official_N_break_even"] is None


def test_v62_rejects_foreign_and_copy_values():
    with pytest.raises(Exception):
        verify_residual_factor_library_v62(object())
    if __import__("os").environ.get("ACFQP_RUN_REAL_RESIDUAL_LIBRARY") == "1":
        artifact = freeze_residual_factor_library_v62()
        with pytest.raises(Exception):
            ResidualFactorLibraryArtifactV62(
                object(), artifact.canonical_bytes, artifact.library_artifact_id
            )
        assert copy.deepcopy(artifact.to_document()) == artifact.to_document()
