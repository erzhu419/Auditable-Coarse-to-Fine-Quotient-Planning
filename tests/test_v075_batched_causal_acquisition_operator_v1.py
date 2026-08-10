from __future__ import annotations

from dataclasses import replace
from fractions import Fraction

import pytest

from acfqp import v075_adaptive_acquisition_round_bundle_authority_v1 as v1
from acfqp import v075_batched_causal_acquisition_operator_v1 as operator
from acfqp import v075_integrated_occurrence_pipeline_v1 as pipeline
from tests.test_v075_production_occurrence_authority_v1 import _open


@pytest.fixture(scope="module")
def deterministic_first_frontier():
    laws = tuple(((1, Fraction(1, 1)),) for _ in range(3))
    values = _open(
        "batched-causal-operator",
        scientific_ordinal=0,
        private_laws=laws,
    )
    entry = values[2]
    result = pipeline.run_v075_integrated_adaptive_occurrence_pipeline_v1(
        controller=values[5],
        namespace=values[0],
        context=values[0].family.replicate_contexts[entry.context_ordinal],
        arm=entry.arm,
        occurrence_ordinal=entry.occurrence_identity.occurrence_ordinal,
        source_prior_transport=values[1].source_prior_transport,
    )
    assert len(result.rounds) == 2
    return result.rounds[0].frontier, result.rounds[0].authorization, values[5]


def test_profile_is_additive_and_retains_the_v1_no_operator_control() -> None:
    profile = operator.freeze_v075_batched_causal_acquisition_profile_v1()
    document = profile.to_document()
    assert profile.no_operator_control_profile == v1.PROFILE_KEY
    assert document["selection_rule"] == (
        "RANKED_GREEDY_MINIMAL_CAUSAL_CONE_UNION_UNDER_FROZEN_CAPS"
    )
    assert document["complete_child_catalogue_required"] is True
    assert document["duplicate_child_rows_charged_once"] is True
    assert document["duplicate_source_promotions_charged_once"] is True
    assert document["missing_child_optional_source_promotions_suppressed"] is True
    assert document["prior_changes_statistical_model"] is False
    assert document["prior_changes_certificate"] is False
    assert operator.PRODUCTION_INTEGRATION_READY is False


def test_batched_operator_eliminates_the_observed_single_catalogue_round_tax(
    deterministic_first_frontier,
) -> None:
    frontier, baseline, controller = deterministic_first_frontier
    before_batches = tuple(item.batch_id for item in controller.batches)
    before_events = tuple(item.event_id for item in controller.events)
    authorization = operator.authorize_v075_batched_causal_acquisition_v1(
        frontier
    )
    assert baseline.status is v1.V075BundleAuthorizationStatusV1.AUTHORIZED
    assert baseline.selected_candidate_id is not None
    assert len({item.candidate_id for item in baseline.intents}) == 1
    assert authorization.outcome is (
        operator.V075BatchedCausalAuthorizationOutcomeV1.AUTHORIZED
    )
    assert len(frontier.candidates) >= 5
    assert len(authorization.selected_candidate_ids) > 1
    assert len(authorization.selected_child_row_ids) == (
        2 * len(authorization.selected_candidate_ids)
    )
    # Missing-child repair uses the minimal causal cone: complete child
    # catalogues only, without an unrelated root-prefix promotion.
    assert authorization.selected_promotion_row_ids == ()
    assert authorization.incremental_draw_count == (
        len(authorization.selected_child_row_ids) * v1.CHILD_ROW_INITIAL_DRAWS
    )
    selected_by_id = {
        item.candidate_id: item for item in frontier.candidates
    }
    assert authorization.incremental_draw_count < sum(
        selected_by_id[item].incremental_draw_count
        for item in authorization.selected_candidate_ids
    )
    assert authorization.incremental_draw_count <= 160_960
    assert len(authorization.selected_child_row_ids) <= 19
    assert tuple(item.batch_id for item in controller.batches) == before_batches
    assert tuple(item.event_id for item in controller.events) == before_events


def test_union_intents_are_complete_deduplicated_and_phase_ordered(
    deterministic_first_frontier,
) -> None:
    frontier = deterministic_first_frontier[0]
    authorization = operator.authorize_v075_batched_causal_acquisition_v1(
        frontier
    )
    discoveries = tuple(
        item
        for item in authorization.intents
        if item.kind
        is operator.V075BatchedCausalIntentKindV1.NEW_CHILD_ROW_DISCOVERY
    )
    extensions = tuple(
        item
        for item in authorization.intents
        if item.kind
        is operator.V075BatchedCausalIntentKindV1
        .EXISTING_VALIDATION_PREFIX_EXTENSION
    )
    validations = tuple(
        item
        for item in authorization.intents
        if item.kind
        is operator.V075BatchedCausalIntentKindV1.NEW_CHILD_ROW_VALIDATION
    )
    assert authorization.intents == (*discoveries, *extensions, *validations)
    assert tuple(item.row_binding.row_binding_id for item in discoveries) == (
        authorization.selected_child_row_ids
    )
    assert tuple(item.row_binding.row_binding_id for item in validations) == (
        authorization.selected_child_row_ids
    )
    assert tuple(item.dependency_intent_id for item in validations) == tuple(
        item.intent_id for item in discoveries
    )
    assert tuple(item.row_binding.row_binding_id for item in extensions) == (
        authorization.selected_promotion_row_ids
    )
    assert len({item.intent_id for item in authorization.intents}) == len(
        authorization.intents
    )
    assert sum(item.accepted_draw_count for item in authorization.intents) == (
        authorization.incremental_draw_count
    )


def test_union_and_cap_fields_cannot_be_resigned_by_replace(
    deterministic_first_frontier,
) -> None:
    authorization = operator.authorize_v075_batched_causal_acquisition_v1(
        deterministic_first_frontier[0]
    )
    with pytest.raises(
        operator.V075BatchedCausalAcquisitionInvariantViolation,
        match="exact union replay",
    ):
        replace(
            authorization,
            selected_candidate_ids=authorization.selected_candidate_ids[:-1],
        )
    with pytest.raises(
        operator.V075BatchedCausalAcquisitionInvariantViolation,
        match="exact union replay",
    ):
        replace(
            authorization,
            incremental_draw_count=authorization.incremental_draw_count + 1,
        )


def test_operator_output_remains_pretarget_and_noncertificate(
    deterministic_first_frontier,
) -> None:
    authorization = operator.authorize_v075_batched_causal_acquisition_v1(
        deterministic_first_frontier[0]
    )
    document = authorization.to_document()
    assert document["frozen_before_target_access"] is True
    assert document["observer_calls"] == 0
    assert document["kernel_calls"] == 0
    assert document["world_model_rows_written"] == 0
    assert document["scientific_certificate_issued"] is False
    assert document["v1_single_candidate_control_retained"] is True
