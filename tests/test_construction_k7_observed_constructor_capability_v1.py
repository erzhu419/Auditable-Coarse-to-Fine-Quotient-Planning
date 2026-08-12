from __future__ import annotations

import hashlib
import inspect

import pytest

from acfqp import construction_k7_heldout_reusable_model_catalogue_v1 as catalogue_v1
from acfqp import construction_k7_observation_driven_world_model_synthesis_v2 as synthesis_v2
from acfqp import construction_k7_observed_constructor_capability_v1 as subject
from acfqp import transition_tuple_observer_v1 as observer
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS, canonical_json_bytes


def _occurrence(label: str) -> str:
    return hashlib.sha256(f"observed-capability:{label}".encode()).hexdigest()


@pytest.fixture(scope="session")
def empty_catalogue():
    return catalogue_v1.build_heldout_reusable_model_catalogue_snapshot_v1(())


@pytest.fixture(scope="session")
def w5_v2(empty_catalogue):
    return synthesis_v2.run_observation_driven_world_model_synthesis_v2(
        empty_catalogue,
        observer.public_context_by_key_v1("opaque_graph_w5_v0"),
        logical_occurrence_id=_occurrence("w5-construct"),
        occurrence_ordinal=1,
        selected_reuse_result_bytes=None,
    )


def test_domains_and_public_surface_are_exact() -> None:
    assert subject.LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS
    assert synthesis_v2.LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS
    assert set(subject.__all__) == {
        "ConstructionK7ObservedConstructorCapabilityV1Error",
        "LOCAL_DOMAINS",
        "ObservedConstructorCapabilityCandidateV1",
        "ObservedConstructorCapabilityDecisionV1",
        "ObservedGraphConstructorSignatureV1",
        "REGISTERED_CAPABILITY_SPECS",
        "RegisteredConstructorCapabilitySpecV1",
        "observed_graph_constructor_signature_v1",
        "propose_observed_constructor_capability_v1",
        "verify_observed_constructor_capability_v1",
    }


def test_w5_and_k6_are_selected_from_graph_invariants_not_context_key() -> None:
    w5 = subject.propose_observed_constructor_capability_v1(
        observer.public_context_by_key_v1("opaque_graph_w5_v0")
    )
    k6 = subject.propose_observed_constructor_capability_v1(
        observer.public_context_by_key_v1("opaque_graph_k6_v0")
    )
    assert w5.signature.sorted_degree_sequence == (3, 3, 3, 3, 4)
    assert w5.signature.edge_count == 8
    assert w5.signature.triangle_count == 4
    assert w5.selected_constructor_key == "W5_CHECKPOINT_OVERLAY_V1"
    assert k6.signature.sorted_degree_sequence == (5, 5, 5, 5, 5, 5)
    assert k6.signature.edge_count == 15
    assert k6.signature.triangle_count == 20
    assert k6.selected_constructor_key == "K6_CHECKPOINT_OVERLAY_V1"
    assert "context_key" not in inspect.getsource(
        subject.observed_graph_constructor_signature_v1
    )
    assert "context_key" not in inspect.getsource(
        subject.propose_observed_constructor_capability_v1
    )


def test_nearby_k6_minus_edge_has_no_sound_capability() -> None:
    context = observer.public_context_by_key_v1("opaque_graph_k6_minus_edge_v0")
    decision = subject.propose_observed_constructor_capability_v1(context)
    subject.verify_observed_constructor_capability_v1(context, decision)
    assert decision.signature.edge_count == 14
    assert decision.signature.sorted_degree_sequence == (4, 4, 5, 5, 5, 5)
    assert decision.outcome == "NO_SOUND_CAPABILITY"
    assert decision.selected_constructor_key is None
    assert not any(row.matched for row in decision.candidates)
    document = decision.to_document()
    assert document["context_key_registry_authoritative"] is False
    assert document["nearby_capability_transfer_allowed"] is False
    assert document["ground_access_authorized_here"] is False


def test_v2_construction_is_bound_to_observed_capability(w5_v2) -> None:
    context = observer.public_context_by_key_v1("opaque_graph_w5_v0")
    result = synthesis_v2.verify_observation_driven_world_model_synthesis_v2(
        context, w5_v2
    )
    document = result.to_document()
    assert result.capability_decision.selected_constructor_key == (
        "W5_CHECKPOINT_OVERLAY_V1"
    )
    assert result.executor_result.promotion is not None
    assert document["constructor_selection_authority"] == (
        "OBSERVED_GRAPH_INVARIANT_CAPABILITY_DECISION_V1"
    )
    assert document["legacy_context_key_dispatch_authoritative"] is False
    assert document["legacy_executor_selection_exactly_cross_checked"] is True


def test_v2_exact_hit_bypasses_constructor(w5_v2, monkeypatch) -> None:
    reuse_document = w5_v2.executor_result.reuse_result_document
    assert reuse_document is not None
    reuse_bytes = canonical_json_bytes(reuse_document)
    entry = catalogue_v1.build_heldout_reusable_model_catalogue_entry_v1(
        "W5", reuse_bytes
    )
    catalogue = catalogue_v1.build_heldout_reusable_model_catalogue_snapshot_v1(
        (entry,)
    )

    def forbidden(*_args, **_kwargs):
        raise AssertionError("exact hit invoked constructor")

    monkeypatch.setattr(
        synthesis_v2.executor_v1.w5_source_v1,
        "run_heldout_checkpoint_recertification_v1",
        forbidden,
    )
    result = synthesis_v2.run_observation_driven_world_model_synthesis_v2(
        catalogue,
        observer.public_context_by_key_v1("opaque_graph_w5_v0"),
        logical_occurrence_id=_occurrence("w5-hit"),
        occurrence_ordinal=2,
        selected_reuse_result_bytes=reuse_bytes,
    )
    assert result.executor_result.dispatch.dispatch_outcome == "REUSE_EXACT_MODEL"
    assert result.to_document()["exact_catalogue_hit_bypasses_constructor"] is True


def test_v2_unsupported_branch_is_zero_access(empty_catalogue) -> None:
    context = observer.public_context_by_key_v1("opaque_graph_k6_minus_edge_v0")
    result = synthesis_v2.run_observation_driven_world_model_synthesis_v2(
        empty_catalogue,
        context,
        logical_occurrence_id=_occurrence("unsupported"),
        occurrence_ordinal=3,
        selected_reuse_result_bytes=None,
    )
    assert result.capability_decision.outcome == "NO_SOUND_CAPABILITY"
    assert result.executor_result.unsupported is not None
    unsupported = result.executor_result.unsupported.to_document()
    assert unsupported["ground_access_count"] == 0
    assert unsupported["observer_call_count"] == 0
    assert unsupported["nearby_model_transfer_attempted"] is False


def test_claim_boundary_is_capability_discovery_not_primitive_invention(
    w5_v2,
) -> None:
    capability = w5_v2.capability_decision.to_document()
    result = w5_v2.to_document()
    assert capability["fixed_human_capability_signature_registry"] is True
    assert capability["automatic_coordinate_primitive_invention_claimed"] is False
    assert capability["broad_graph_generalization_claimed"] is False
    assert result["fixed_human_capability_signature_registry"] is True
    assert result["automatic_coordinate_primitive_invention_claimed"] is False
    assert result["broad_graph_or_domain_generalization_claimed"] is False
    assert result["official_execution_allowed"] is False
