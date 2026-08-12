from __future__ import annotations

import inspect

import pytest

from acfqp import construction_k7_observed_program_heldout_campaign_v1 as subject
from acfqp import transition_tuple_observer_v1 as observer
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS


@pytest.fixture(scope="module")
def campaign():
    return subject.run_observed_program_heldout_campaign_v1()


def test_preregistration_precedes_source_program_synthesis(campaign) -> None:
    document = campaign.preregistration.to_document()
    assert subject.LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS
    assert document["heldout_case_count"] == 5
    assert document["source_program_ids_absent_at_preregistration"] is True
    assert document["heldout_observations_frozen_before_source_program_synthesis"] is True
    assert "source_program_proposal_id" not in str(document)


def test_isomorphic_relabelling_transfers_only_the_w5_program(campaign) -> None:
    case = campaign.preregistration.cases[0]
    evaluation = campaign.evaluations[0]
    assert case.observation.relation_kind == "VERTEX_RELABEL_OF_SOURCE_W5"
    assert case.observation.topology is not None
    assert case.observation.source_topology is not None
    assert (
        case.observation.topology.topology_id
        != case.observation.source_topology.topology_id
    )
    assert evaluation.outcome == subject.PROGRAM_MATCH
    assert evaluation.selected_constructor_key == "W5_CHECKPOINT_OVERLAY_V1"
    assert len(evaluation.matched_proposal_ids) == 1


def test_all_heldout_graph_topology_ids_are_outside_the_source_corpus(campaign) -> None:
    source_topologies = {
        observer.public_context_by_key_v1(key).topology.topology_id
        for key in (
            "opaque_graph_w5_v0",
            "opaque_graph_k6_v0",
            "opaque_graph_k6_minus_edge_v0",
        )
    }
    heldout_topologies = {
        case.observation.topology.topology_id
        for case in campaign.preregistration.cases
        if case.observation.topology is not None
    }
    assert source_topologies.isdisjoint(heldout_topologies)


def test_unseen_graphs_fail_closed_without_constructor_or_ground(campaign) -> None:
    for case, evaluation in zip(
        campaign.preregistration.cases[1:4], campaign.evaluations[1:4]
    ):
        assert case.observation.domain_schema == subject.GRAPH_SCHEMA
        assert evaluation.outcome == subject.NO_SOUND_PROGRAM
        assert evaluation.selected_constructor_key is None
        document = evaluation.to_document()
        assert document["constructor_invocation_count"] == 0
        assert document["model_transfer_attempt_count"] == 0
        assert document["ground_access_count"] == 0


def test_second_domain_is_typed_no_transfer(campaign) -> None:
    case = campaign.preregistration.cases[-1]
    evaluation = campaign.evaluations[-1]
    assert case.observation.domain_schema == subject.LMB_SCHEMA
    assert evaluation.outcome == subject.SCHEMA_NO_TRANSFER
    assert evaluation.matched_proposal_ids == ()
    assert evaluation.selected_constructor_key is None


def test_evaluator_does_not_read_case_key_or_expected_label(campaign) -> None:
    source = inspect.getsource(subject._matches) + inspect.getsource(  # noqa: SLF001
        subject._evaluate  # noqa: SLF001
    )
    assert "case_key" not in source
    assert "expected_outcome" not in source
    assert tuple(inspect.signature(subject._evaluate).parameters) == (  # noqa: SLF001
        "preregistration_id",
        "observation",
        "proposals",
    )
    assert all(
        row.to_document()["context_key_or_expected_label_read_by_evaluator"] is False
        for row in campaign.evaluations
    )


def test_campaign_claim_boundary_and_counts(campaign) -> None:
    subject.verify_observed_program_heldout_campaign_v1(campaign)
    document = campaign.to_document()
    assert document["isomorphic_positive_program_transfer_count"] == 1
    assert document["same_domain_no_transfer_count"] == 3
    assert document["cross_vertex_count_no_transfer_count"] == 1
    assert document["cross_domain_typed_no_transfer_count"] == 1
    assert document["constructor_invocation_count"] == 0
    assert document["model_transfer_attempt_count"] == 0
    assert document["ground_access_count"] == 0
    assert document["human_registered_primitive_and_operator_vocabulary"] is True
    assert document["automatic_primitive_or_operator_invention_claimed"] is False
    assert document["constructor_or_model_transfer_authority_present"] is False
    assert document["broad_graph_or_cross_domain_generalization_claimed"] is False
    assert document["official_execution_allowed"] is False


def test_evaluation_or_claim_tampering_is_rejected(campaign) -> None:
    evaluation = campaign.evaluations[0]
    object.__setattr__(evaluation, "outcome", subject.NO_SOUND_PROGRAM)
    with pytest.raises(subject.ConstructionK7ObservedProgramHeldoutCampaignV1Error):
        subject.verify_observed_program_heldout_campaign_v1(campaign)
    object.__setattr__(evaluation, "outcome", subject.PROGRAM_MATCH)
    subject.verify_observed_program_heldout_campaign_v1(campaign)
