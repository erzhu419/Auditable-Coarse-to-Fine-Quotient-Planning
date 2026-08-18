import ast
import copy

import pytest

from acfqp.construction_k7_residual_factor_independent_verifier_v62 import (
    verify_residual_factor_library_bytes_v62,
)
from acfqp.construction_k7_residual_factor_library_v62 import (
    freeze_residual_factor_library_v62,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


pytestmark = pytest.mark.skipif(
    __import__("os").environ.get("ACFQP_RUN_REAL_RESIDUAL_LIBRARY") != "1",
    reason="explicit retrospective library bytes",
)


def test_v62_independent_verifier_reconstructs_partial_library():
    artifact = freeze_residual_factor_library_v62()
    result = loads_canonical_json(
        verify_residual_factor_library_bytes_v62(artifact.canonical_bytes)
    )
    assert result["status"] == "PRODUCER_FREE_RETROSPECTIVE_PARTIAL_LIBRARY_VERIFIED"
    assert result["covered_residual_target_count"] == 3
    assert result["uncovered_residual_target_count"] == 3
    assert result["scientific_fresh_outcome_verified"] is False


def test_v62_independent_verifier_rejects_resigned_semantic_attack():
    document = freeze_residual_factor_library_v62().to_document()
    forged = copy.deepcopy(document)
    forged["compiled_library"]["complete_world_model_claimed"] = True
    payload = {key: value for key, value in forged.items() if key != "library_artifact_id"}
    from acfqp import construction_k7_domain_registry_extension_v62 as domains

    forged["library_artifact_id"] = domains.extension_content_id_v62(
        domains.CONSTRUCTION_K7_RESIDUAL_FACTOR_LIBRARY_V62_DOMAIN, payload
    )
    with pytest.raises(Exception):
        verify_residual_factor_library_bytes_v62(canonical_json_bytes(forged))


def test_v62_independent_verifier_has_no_producer_or_compiler_import():
    path = __import__(
        "acfqp.construction_k7_residual_factor_independent_verifier_v62",
        fromlist=["x"],
    ).__file__
    tree = ast.parse(open(path, encoding="utf-8").read())
    imported = {
        node.module or ""
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }
    assert all("residual_factor_library_v62" not in name for name in imported)
    assert all("generic_overlay_residual_factor_compiler" not in name for name in imported)
