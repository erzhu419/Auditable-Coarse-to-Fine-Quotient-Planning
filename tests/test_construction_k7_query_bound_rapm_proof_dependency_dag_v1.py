from __future__ import annotations

import pytest

from acfqp import construction_k7_query_bound_rapm_proof_dependency_dag_v1 as subject
from acfqp.phase3e_ids import (
    PHASE3E_DOMAIN_TAGS,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
)
from tests.test_construction_k7_query_bound_final_local_replanning_v1 import (
    real_final_local_replanning,
)
from tests.test_construction_k7_query_bound_ground_transaction_v1 import (
    real_query_bound_ground_transaction,
)
from tests.test_construction_k7_query_bound_overlay_replanning_v1 import (
    real_overlay_replanning,
)
from tests.test_construction_k7_query_bound_second_ground_transaction_v1 import (
    real_second_ground_transaction,
)
from tests.test_construction_k7_query_bound_second_recovery_request_v1 import (
    real_second_request,
)


def test_domains_and_public_surface_are_additive() -> None:
    assert subject.LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS
    assert len(subject.LOCAL_DOMAINS) == 5
    assert set(subject.__all__) == {
        "ConstructionK7QueryBoundRAPMProofDependencyDAGV1Error",
        "LOCAL_DOMAINS",
        "ProofDependencyNodeKindV1",
        "ProofDependencyResolutionV1",
        "QueryBoundRAPMProofDependencyTransitionV1",
        "freeze_query_bound_rapm_proof_dependency_transition_v1",
        "replay_query_bound_rapm_proof_dependency_transition_bytes_v1",
    }


@pytest.fixture(scope="module")
def real_proof_dependency_transition(real_final_local_replanning):
    _transaction, final_local = real_final_local_replanning
    transition = subject.freeze_query_bound_rapm_proof_dependency_transition_v1(
        final_local
    )
    return final_local, transition


def test_real_h2_proof_dependency_dag_invalidates_exact_ancestor_cone(
    real_proof_dependency_transition,
) -> None:
    final_local, transition = real_proof_dependency_transition
    document = transition.to_document()
    replayed = subject.replay_query_bound_rapm_proof_dependency_transition_bytes_v1(
        canonical_json_bytes(document)
    )
    assert replayed.transition_id == transition.transition_id
    assert document["source_graph"]["numerical_model_id"] == (
        final_local.source_model.model_id
    )
    assert document["target_graph"]["numerical_model_id"] == (
        final_local.successor_model.model_id
    )
    assert document["source_graph"]["numerical_proof_id"] == (
        final_local.source_proof.proof_id
    )
    assert document["target_graph"]["numerical_proof_id"] == (
        final_local.successor_proof.proof_id
    )
    assert document["source_graph"]["node_count"] == 41
    assert document["target_graph"]["node_count"] == 41
    assert document["proof_node_count"] == 41
    assert document["reused_proof_node_count"] == 22
    assert document["recomputed_proof_node_count"] == 19
    assert len(document["changed_semantic_row_binding_ids"]) == 6
    assert len(document["preserved_semantic_row_binding_ids"]) == 12
    assert document["recomputed_proof_node_count"] == len(
        document["changed_ancestor_role_keys"]
    )
    assert (
        document["reused_proof_node_count"]
        + document["recomputed_proof_node_count"]
        == 41
    )
    resolutions = {item["role_key"]: item for item in document["resolutions"]}
    for binding in document["changed_semantic_row_binding_ids"]:
        assert resolutions[f"ROW:{binding}"]["outcome"] == "RECOMPUTED"
        assert resolutions[f"ROW:{binding}"]["reason"] == (
            "SIGNED_SEMANTIC_ROW_DELTA"
        )
    for binding in document["preserved_semantic_row_binding_ids"]:
        assert resolutions[f"ROW:{binding}"]["outcome"] == "REUSED"
        assert resolutions[f"ROW:{binding}"]["reason"] == (
            "IDENTICAL_DEPENDENCY_CLOSURE"
        )
    assert document["proof_dependency_dag_materialized"] is True
    assert document["changed_ancestor_invalidation_exact"] is True
    assert document["unaffected_nonancestor_recomputation_count"] == 0
    assert document["persistent_cross_query_cache_materialized"] is False
    assert document["fresh_query_cache_consumer_present"] is False
    assert document["plan_certificate_issued"] is False
    assert document["official_execution_allowed"] is False


def test_transition_replay_rejects_resigned_resolution_change(
    real_proof_dependency_transition,
) -> None:
    _final_local, transition = real_proof_dependency_transition
    document = loads_canonical_json(
        canonical_json_bytes(transition.to_document())
    )
    reused = next(
        item for item in document["resolutions"] if item["outcome"] == "REUSED"
    )
    reused["reason"] = "CHANGED_ANCESTOR"
    payload = dict(document)
    payload.pop("source_graph")
    payload.pop("target_graph")
    payload.pop("query_bound_rapm_proof_dependency_transition_id")
    document["query_bound_rapm_proof_dependency_transition_id"] = content_id(
        subject.TRANSITION_DOMAIN,
        payload,
    )
    with pytest.raises(
        subject.ConstructionK7QueryBoundRAPMProofDependencyDAGV1Error
    ):
        subject.replay_query_bound_rapm_proof_dependency_transition_bytes_v1(
            canonical_json_bytes(document)
        )


def test_transition_is_not_caller_mintable() -> None:
    with pytest.raises(
        subject.ConstructionK7QueryBoundRAPMProofDependencyDAGV1Error
    ):
        subject.QueryBoundRAPMProofDependencyTransitionV1(
            object(),
            "0" * 64,
            object(),
            object(),
            (),
            (),
            (),
            (),
        )
