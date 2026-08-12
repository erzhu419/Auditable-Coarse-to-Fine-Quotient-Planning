from __future__ import annotations

import pytest

from acfqp import construction_k7_basis_heldout_world_model_synthesis_v1 as subject
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS


@pytest.fixture(scope="module")
def campaign():
    return subject.run_basis_heldout_world_model_synthesis_v1()


def test_query_is_preregistered_isomorphic_and_basis_authorized(campaign) -> None:
    assert subject.LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS
    query = campaign.query.to_document()
    assert query["query_frozen_before_basis_derivation_and_authorized_constructor"] is True
    assert query["construction_topology_absent_from_basis_validation_rows"] is True
    assert query["source_topology"]["topology_id"] != query["heldout_topology"]["topology_id"]
    assert query["environment_semantics"] == "VERTEX_RELABEL_TRANSPORT_OF_SOURCE_W5_V1"
    transport = campaign.transport.to_document()
    assert transport["constructor_selection_authority"] == (
        "OBSERVATION_DERIVED_PRIMITIVE_BASIS_AND_PROGRAM_V1"
    )


def test_certificate_failure_triggers_only_local_distinctions(campaign) -> None:
    transport = campaign.transport.to_document()
    assert transport["base_abstract_certificate_status"] == "FAILED_PROOF_FRONTIER"
    assert transport["local_ground_recovery_triggered_after_failure"] is True
    assert transport["changed_ground_distinction_count"] == 2
    assert transport["incremental_local_ground_draw_count"] == 4096
    assert transport["final_abstract_certificate_status"] == "CERTIFIED"


def test_second_heldout_occurrence_plans_abstractly_with_zero_ground(campaign) -> None:
    plan = campaign.plan.to_document()
    assert plan["horizon"] == 2
    assert plan["multi_step_plan_completed_in_abstract_model"] is True
    assert plan["fresh_occurrence_abstract_planner_invocations"] == 1
    assert plan["fresh_occurrence_model_construction_invocations"] == 0
    assert plan["fresh_occurrence_observer_call_count"] == 0
    assert plan["fresh_occurrence_ground_draw_count"] == 0
    assert plan["plan_certificate_kind"] == (
        "ISOMORPHISM_TRANSPORTED_CONDITIONAL_STATISTICAL"
    )


def test_campaign_main_objective_and_boundaries(campaign) -> None:
    subject.verify_basis_heldout_world_model_synthesis_v1(campaign)
    document = campaign.to_document()
    assert document["reusable_abstract_world_model_synthesized"] is True
    assert document["multi_step_planning_mainly_completed_in_abstract_model"] is True
    assert document["local_ground_triggered_only_after_certificate_failure"] is True
    assert document["world_model_construction_count"] == 1
    assert document["abstract_h2_plan_count"] == 2
    assert document["fresh_reuse_ground_draw_count"] == 0
    assert document["unseen_structure_constructor_invocation_count"] == 0
    assert document["cross_domain_constructor_invocation_count"] == 0
    assert document["broad_graph_or_cross_domain_generalization_claimed"] is False
    assert document["open_ended_operator_invention_claimed"] is False
    assert document["official_execution_allowed"] is False


def test_transport_tamper_is_rejected(campaign) -> None:
    original = campaign.transport.certified_audit_id
    object.__setattr__(campaign.transport, "certified_audit_id", "f" * 64)
    with pytest.raises(subject.ConstructionK7BasisHeldoutWorldModelSynthesisV1Error):
        subject.verify_basis_heldout_world_model_synthesis_v1(campaign)
    object.__setattr__(campaign.transport, "certified_audit_id", original)
    subject.verify_basis_heldout_world_model_synthesis_v1(campaign)
