from __future__ import annotations

import copy

import pytest

from acfqp import construction_k7_observation_derived_primitive_basis_v1 as subject
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS


@pytest.fixture(scope="module")
def campaign():
    return subject.run_observation_derived_primitive_campaign_v1()


def test_basis_is_compiled_from_raw_relational_meta_grammar(campaign) -> None:
    assert subject.LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS
    basis = campaign.basis
    assert tuple(row.compatibility_name for row in basis.selected_candidates) == subject.COMPATIBILITY_PRIMITIVES
    assert all(row.selected for row in basis.candidates)
    document = basis.to_document()
    assert document["final_feature_names_used_as_candidate_inputs"] is False
    assert document["primitive_values_compiled_from_raw_relations"] is True
    assert document["heldout_observations_frozen_before_basis_derivation"] is True
    assert document["human_registered_relational_meta_grammar"] is True
    assert document["open_ended_operator_invention_claimed"] is False


def test_source_columns_are_unique_and_observation_derived(campaign) -> None:
    columns = [row.source_observation_column for row in campaign.basis.candidates]
    assert len(set(columns)) == len(columns) == 5
    assert columns[0] == ((5,), (6,), (6,))
    assert columns[1] == (8, 15, 14)
    assert columns[2] == ((3, 3, 3, 3, 4), (5, 5, 5, 5, 5, 5), (4, 4, 5, 5, 5, 5))
    assert columns[3] == (4, 20, 16)
    assert columns[4] == (5, 6, 6)


def test_all_graph_heldout_rows_replay_from_topology(campaign) -> None:
    assert [row.outcome for row in campaign.evaluations] == [
        "BASIS_REPLAY_MATCH",
        "BASIS_REPLAY_MATCH",
        "BASIS_REPLAY_MATCH",
        "BASIS_REPLAY_MATCH",
        "TYPED_SCHEMA_NO_EVALUATION",
    ]
    for row in campaign.evaluations[:4]:
        assert row.derived_feature_rows == row.expected_feature_rows
    assert campaign.evaluations[-1].derived_feature_rows == ()


def test_campaign_is_ready_for_constructor_but_executes_none(campaign) -> None:
    subject.verify_observation_derived_primitive_campaign_v1(campaign)
    document = campaign.to_document()
    assert document["basis_ready_for_constructor_authority"] is True
    assert document["constructor_invocation_count"] == 0
    assert document["ground_access_count"] == 0
    assert document["official_execution_allowed"] is False


def test_candidate_mutation_is_rejected(campaign) -> None:
    candidate = campaign.basis.candidates[0]
    original = candidate.source_observation_column
    object.__setattr__(candidate, "source_observation_column", ((99,), (6,), (6,)))
    with pytest.raises(subject.ConstructionK7ObservationDerivedPrimitiveBasisV1Error):
        subject.verify_observation_derived_primitive_campaign_v1(campaign)
    object.__setattr__(candidate, "source_observation_column", original)
    subject.verify_observation_derived_primitive_campaign_v1(campaign)

