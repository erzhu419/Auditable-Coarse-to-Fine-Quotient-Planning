from __future__ import annotations

import hashlib

import pytest

from acfqp import construction_k7_observation_driven_world_model_synthesis_v1 as subject
from acfqp import construction_k7_heldout_reusable_model_catalogue_v1 as catalogue_v1
from acfqp import transition_tuple_observer_v1 as observer
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS, canonical_json_bytes


def _occurrence(label: str) -> str:
    return hashlib.sha256(f"world-model-synthesis:{label}".encode()).hexdigest()


@pytest.fixture(scope="session")
def empty_catalogue():
    return catalogue_v1.build_heldout_reusable_model_catalogue_snapshot_v1(())


@pytest.fixture(scope="session")
def w5_synthesis(empty_catalogue):
    return subject.run_observation_driven_world_model_synthesis_v1(
        empty_catalogue,
        observer.public_context_by_key_v1("opaque_graph_w5_v0"),
        logical_occurrence_id=_occurrence("w5-construction"),
        occurrence_ordinal=1,
        selected_reuse_result_bytes=None,
    )


@pytest.fixture(scope="session")
def k6_synthesis(empty_catalogue):
    return subject.run_observation_driven_world_model_synthesis_v1(
        empty_catalogue,
        observer.public_context_by_key_v1("opaque_graph_k6_v0"),
        logical_occurrence_id=_occurrence("k6-construction"),
        occurrence_ordinal=4,
        selected_reuse_result_bytes=None,
    )


def test_domains_and_public_surface_are_exact() -> None:
    assert subject.LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS
    assert len(subject.LOCAL_DOMAINS) == 4
    assert set(subject.__all__) == {
        "ConstructionK7ObservationDrivenWorldModelSynthesisV1Error",
        "LOCAL_DOMAINS",
        "ObservationDrivenModelPromotionV1",
        "ObservationDrivenSynthesisDispatchV1",
        "ObservationDrivenSynthesisUnsupportedV1",
        "ObservationDrivenWorldModelSynthesisResultV1",
        "run_observation_driven_world_model_synthesis_v1",
        "verify_observation_driven_world_model_synthesis_v1",
    }


def test_empty_catalogue_w5_is_synthesized_promoted_and_reused(
    w5_synthesis,
) -> None:
    result = subject.verify_observation_driven_world_model_synthesis_v1(
        w5_synthesis
    )
    document = result.to_document()
    assert result.initial_route.to_document()["routing_outcome"] == "CONSTRUCTION_REQUIRED"
    assert result.dispatch.constructor_key == "W5_CHECKPOINT_OVERLAY_V1"
    assert document["result_outcome"] == "MODEL_SYNTHESIZED_PROMOTED_AND_REUSED"
    assert document["model_construction_executed"] is True
    assert result.promotion is not None
    assert result.promotion.family_key == "W5"
    assert result.promotion.changed_row_count == 2
    assert result.promotion.preserved_row_count == 6
    assert result.promotion.incremental_ground_draw_count == 4_096
    assert tuple(item.family_key for item in result.final_catalogue.entries) == ("W5",)
    assert result.final_route is not None and result.final_route.plan is not None
    assert result.final_route.to_document()["routing_outcome"] == "ABSTRACT_PLAN_CERTIFIED"
    assert document["fresh_postconstruction_ground_draw_count"] == 0
    assert document["fresh_postconstruction_observer_call_count"] == 0
    assert document["fresh_postconstruction_abstract_planner_invocations"] == 1
    assert document["multi_step_plan_mainly_completed_in_abstract_model"] is True
    assert document["ground_distinctions_restored_only_after_certificate_failure"] is True


def test_k6_dispatch_uses_k6_constructor_and_promotes_one_row(
    k6_synthesis,
) -> None:
    result = k6_synthesis
    assert result.dispatch.constructor_key == "K6_CHECKPOINT_OVERLAY_V1"
    assert result.promotion is not None
    assert result.promotion.family_key == "K6"
    assert result.promotion.changed_row_count == 1
    assert result.promotion.preserved_row_count == 19
    assert result.promotion.incremental_ground_draw_count == 8_192
    assert result.final_route is not None and result.final_route.plan is not None
    assert tuple(item.family_key for item in result.final_catalogue.entries) == ("K6",)


def test_exact_catalogue_hit_never_invokes_constructor(
    w5_synthesis,
    monkeypatch,
) -> None:
    assert w5_synthesis.reuse_result_document is not None
    reuse_bytes = canonical_json_bytes(w5_synthesis.reuse_result_document)
    entry = catalogue_v1.build_heldout_reusable_model_catalogue_entry_v1(
        "W5", reuse_bytes
    )
    catalogue = catalogue_v1.build_heldout_reusable_model_catalogue_snapshot_v1(
        (entry,)
    )

    def forbidden(*_args, **_kwargs):
        raise AssertionError("exact hit invoked model construction")

    monkeypatch.setattr(
        subject.w5_source_v1, "run_heldout_checkpoint_recertification_v1", forbidden
    )
    result = subject.run_observation_driven_world_model_synthesis_v1(
        catalogue,
        observer.public_context_by_key_v1("opaque_graph_w5_v0"),
        logical_occurrence_id=_occurrence("w5-hit"),
        occurrence_ordinal=7,
        selected_reuse_result_bytes=reuse_bytes,
    )
    document = result.to_document()
    assert document["result_outcome"] == "EXISTING_MODEL_REUSED"
    assert document["model_construction_executed"] is False
    assert result.final_catalogue == catalogue
    assert result.final_route == result.initial_route
    assert result.initial_route.plan is not None


def test_negative_control_is_no_access_and_does_not_transfer_models(
    k6_synthesis,
    monkeypatch,
) -> None:
    assert k6_synthesis.reuse_result_document is not None
    reuse_bytes = canonical_json_bytes(k6_synthesis.reuse_result_document)
    entry = catalogue_v1.build_heldout_reusable_model_catalogue_entry_v1(
        "K6", reuse_bytes
    )
    catalogue = catalogue_v1.build_heldout_reusable_model_catalogue_snapshot_v1(
        (entry,)
    )

    def forbidden(*_args, **_kwargs):
        raise AssertionError("unsupported control invoked a positive constructor")

    monkeypatch.setattr(
        subject.w5_source_v1, "run_heldout_checkpoint_recertification_v1", forbidden
    )
    monkeypatch.setattr(
        subject.k6_source_v1,
        "run_heldout_k6_checkpoint_recertification_v1",
        forbidden,
    )
    result = subject.run_observation_driven_world_model_synthesis_v1(
        catalogue,
        observer.public_context_by_key_v1("opaque_graph_k6_minus_edge_v0"),
        logical_occurrence_id=_occurrence("negative-control"),
        occurrence_ordinal=8,
        selected_reuse_result_bytes=None,
    )
    document = result.to_document()
    assert document["result_outcome"] == "NO_CERTIFIABLE_CONSTRUCTOR"
    assert document["model_construction_executed"] is False
    assert result.final_catalogue == catalogue
    assert result.final_route is None
    assert result.unsupported is not None
    unsupported = result.unsupported.to_document()
    assert unsupported["terminal_class"] == "ATTEMPT_CLOSURE_NONCERTIFICATE"
    assert unsupported["terminal_code"] == "NO_CERTIFIABLE_CONSTRUCTOR_REGISTERED"
    assert unsupported["ground_access_count"] == 0
    assert unsupported["nearby_model_transfer_attempted"] is False
    assert unsupported["infeasibility_certified"] is False


def test_constructor_miss_rejects_prebuilt_bytes(
    empty_catalogue,
    w5_synthesis,
) -> None:
    assert w5_synthesis.reuse_result_document is not None
    with pytest.raises(
        (
            subject.ConstructionK7ObservationDrivenWorldModelSynthesisV1Error,
            ValueError,
        )
    ):
        subject.run_observation_driven_world_model_synthesis_v1(
            empty_catalogue,
            observer.public_context_by_key_v1("opaque_graph_w5_v0"),
            logical_occurrence_id=_occurrence("prebuilt-injection"),
            occurrence_ordinal=9,
            selected_reuse_result_bytes=canonical_json_bytes(
                w5_synthesis.reuse_result_document
            ),
        )


def test_claim_boundaries_remain_locked(w5_synthesis) -> None:
    document = w5_synthesis.to_document()
    dispatch = document["dispatch"]
    assert dispatch["fixed_human_constructor_registry"] is True
    assert dispatch["automatic_coordinate_primitive_invention_claimed"] is False
    assert document["automatic_coordinate_primitive_invention_claimed"] is False
    assert document["broad_cross_domain_generalization_claimed"] is False
    assert document["official_execution_allowed"] is False
