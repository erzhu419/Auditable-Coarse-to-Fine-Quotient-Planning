from __future__ import annotations

import ast
import copy
from pathlib import Path

import pytest

from acfqp import construction_k7_basis_heldout_world_model_synthesis_v1 as producer
from acfqp import construction_k7_basis_heldout_world_model_independent_verifier_v1 as subject
from acfqp.phase3e_ids import canonical_json_bytes, content_id


@pytest.fixture(scope="module")
def campaign_bytes() -> bytes:
    return canonical_json_bytes(
        producer.run_basis_heldout_world_model_synthesis_v1().to_document()
    )


def test_independent_replay_closes_basis_constructor_model_and_plan(campaign_bytes) -> None:
    verification = subject.verify_basis_heldout_world_model_synthesis_bytes_independently_v1(
        campaign_bytes
    )
    document = verification.to_document()
    assert document["query_isomorphism_replayed"] is True
    assert document["primitive_basis_replayed"] is True
    assert document["source_failure_recovery_and_model_replayed"] is True
    assert document["heldout_h2_abstract_audit_replayed"] is True
    assert document["no_transfer_controls_replayed"] is True
    assert document["process_execution_or_timing_independently_verified"] is False


def test_independent_verifier_imports_no_basis_heldout_producer() -> None:
    tree = ast.parse(Path(subject.__file__).read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported.add(node.module)
            imported.update(alias.name for alias in node.names)
    assert "acfqp.construction_k7_basis_heldout_world_model_synthesis_v1" not in imported


def test_fully_resigned_permutation_attack_is_rejected(campaign_bytes) -> None:
    attacked = copy.deepcopy(__import__("json").loads(campaign_bytes))
    query = attacked["heldout_query"]
    query["vertex_permutation_source_to_heldout"] = [0, 1, 2, 3, 4]
    payload = {key: value for key, value in query.items() if key != "basis_heldout_query_id"}
    query["basis_heldout_query_id"] = content_id(producer.QUERY_DOMAIN, payload)
    with pytest.raises(subject.ConstructionK7BasisHeldoutWorldModelIndependentVerifierV1Error):
        subject.verify_basis_heldout_world_model_synthesis_bytes_independently_v1(
            canonical_json_bytes(attacked)
        )

def test_fully_resigned_zero_ground_claim_attack_is_rejected(campaign_bytes) -> None:
    attacked = copy.deepcopy(__import__("json").loads(campaign_bytes))
    plan = attacked["heldout_plan"]
    plan["fresh_occurrence_ground_draw_count"] = 1
    payload = {
        key: value
        for key, value in plan.items()
        if key not in {"source_replayed_audit", "basis_heldout_abstract_plan_id"}
    }
    plan["basis_heldout_abstract_plan_id"] = content_id(producer.PLAN_DOMAIN, payload)
    with pytest.raises(subject.ConstructionK7BasisHeldoutWorldModelIndependentVerifierV1Error):
        subject.verify_basis_heldout_world_model_synthesis_bytes_independently_v1(
            canonical_json_bytes(attacked)
        )
