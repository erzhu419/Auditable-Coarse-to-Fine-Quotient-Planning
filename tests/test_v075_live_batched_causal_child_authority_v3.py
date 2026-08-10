from __future__ import annotations

from dataclasses import dataclass, replace

import pytest

from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp import v075_live_batched_causal_child_authority_v3 as batched
from acfqp import v075_live_dynamic_acquisition_authority_v2 as dynamic
from tests.test_v075_observer_signed_multiround_occurrence_runner_v2 import (
    capped_closed_result,
)


@dataclass(frozen=True)
class _StableFingerprintProbe:
    label: str
    count: int


def test_owned_authorization_fingerprint_does_not_hash_temporary_container_id(
) -> None:
    authorization = _StableFingerprintProbe("authorization", 1)
    verification = _StableFingerprintProbe("verification", 2)
    first = batched._owned_authorization_fingerprint(  # noqa: SLF001
        authorization,
        verification,
    )
    second = batched._owned_authorization_fingerprint(  # noqa: SLF001
        authorization,
        verification,
    )
    assert first == second
    assert first != batched._owned_authorization_fingerprint(  # noqa: SLF001
        authorization,
        _StableFingerprintProbe("verification", 3),
    )


@pytest.fixture(scope="module")
def batched_authorization(capped_closed_result):
    values = capped_closed_result
    authorization = batched.authorize_v075_live_batched_causal_children_v3(
        source_epoch=values["roots"]["root_model_epoch"],
        namespace=values["namespace"],
    )
    return values, authorization


def test_v2_all_or_none_control_is_retained_but_causal_union_fits(
    batched_authorization,
) -> None:
    values, authorization = batched_authorization
    control = authorization.source_closure
    assert control.closure_id == values["roots"]["child_closure"].closure_id
    assert control.status is (
        dynamic.V075LiveDynamicChildClosureStatusV2
        .CHILD_ACTION_ROW_CAP_EXCEEDED
    )
    assert control.unresolved_child_action_row_count == 28
    assert authorization.outcome is (
        batched.V075LiveBatchedCausalChildOutcomeV3.AUTHORIZED
    )
    assert len(authorization.candidates) == 6
    assert len(authorization.selected_candidate_ids) == 6
    assert len(authorization.selected_child_state_ids) == 6
    assert len(authorization.selected_row_binding_ids) == 16
    assert authorization.incremental_draw_count == 132_096
    assert len(authorization.selected_row_binding_ids) <= 19
    assert authorization.incremental_draw_count <= 160_960


def test_only_exact_failed_frontier_successors_are_selected(
    batched_authorization,
) -> None:
    _values, authorization = batched_authorization
    frontier = authorization.source_closure.source_epoch.proof.failed_frontier
    assert frontier is not None
    expected_states = tuple(
        sorted(
            {
                state_id
                for obligation in frontier.obligations
                for state_id in obligation.unmaterialized_successor_ids
            }
        )
    )
    assert authorization.selected_child_state_ids == expected_states
    assert tuple(
        item.child.state.state_id for item in authorization.candidates
    ) == expected_states
    noncausal = {
        item.state.state_id
        for item in authorization.source_closure.child_states
    } - set(expected_states)
    assert len(noncausal) == 6
    assert not noncausal & set(authorization.selected_child_state_ids)
    obligation_rows = {item.row_id for item in frontier.obligations}
    for candidate in authorization.candidates:
        assert set(candidate.source_obligation_row_ids) <= obligation_rows
        assert set(candidate.source_obligation_row_ids) <= {
            edge.parent_numerical_row_id
            for edge in candidate.child.causal_edges
        }
        assert candidate.child.modeled_row_binding_ids == ()
        assert candidate.row_binding_ids == tuple(
            item.row_binding_id for item in candidate.child.row_bindings
        )


def test_authorized_intents_preserve_the_support_phase_barrier(
    batched_authorization,
) -> None:
    values, authorization = batched_authorization
    discoveries = authorization.discovery_intents
    validations = authorization.validation_templates
    assert len(discoveries) == len(validations) == 16
    assert tuple(item.ordinal for item in discoveries) == tuple(range(16))
    assert tuple(item.ordinal for item in validations) == tuple(range(16))
    assert tuple(
        item.discovery_intent.intent_id for item in validations
    ) == tuple(item.intent_id for item in discoveries)
    assert tuple(
        item.row_binding.row_binding_id for item in discoveries
    ) == authorization.selected_row_binding_ids
    assert all(
        item.stream_identity.target_tape_namespace_id
        == values["namespace"].target_tape_namespace_id
        and item.stream_identity.observer_epoch_index == 0
        and item.stream_identity.lane.value == "DISCOVERY"
        for item in discoveries
    )
    assert all(
        item.to_document()["observer_execution_ready"] is False
        and item.to_document()[
            "observer_signed_complete_support_required"
        ]
        is True
        for item in validations
    )


def test_selected_intents_are_exact_v2_control_schema_projections(
    batched_authorization,
) -> None:
    _values, authorization = batched_authorization
    discovery = authorization.discovery_intents[0]
    expected_discovery = dynamic.V075LiveDynamicChildDiscoveryIntentV2(
        dynamic._CHILD_DISCOVERY_ISSUER,  # noqa: SLF001
        discovery.source_model_epoch_id,
        discovery.source_numerical_model_id,
        discovery.source_proof_id,
        discovery.source_frontier_id,
        discovery.source_head_id,
        discovery.occurrence_id,
        discovery.context_id,
        discovery.arm,
        discovery.child_binding_id,
        discovery.child_state_id,
        discovery.catalogue_id,
        discovery.row_binding,
        discovery.stream_identity,
        discovery.ordinal,
    )
    expected_template = (
        dynamic.V075LiveDynamicChildValidationIntentTemplateV2(
            dynamic._CHILD_VALIDATION_TEMPLATE_ISSUER,  # noqa: SLF001
            expected_discovery,
        )
    )
    assert discovery.intent_id == expected_discovery.intent_id
    assert discovery.to_document() == expected_discovery.to_document()
    assert authorization.validation_templates[0].template_id == (
        expected_template.template_id
    )
    assert authorization.validation_templates[0].to_document() == (
        expected_template.to_document()
    )


def test_authorization_is_pretarget_and_not_a_certificate(
    batched_authorization,
) -> None:
    _values, authorization = batched_authorization
    document = authorization.to_document()
    assert document["selection_rule"] == batched.SELECTION_RULE
    assert document["no_operator_control_retained"] is True
    assert document["only_failed_frontier_successors_selected"] is True
    assert document["complete_selected_child_catalogues"] is True
    assert document["frozen_before_target_access"] is True
    assert document["observer_calls"] == 0
    assert document["kernel_calls"] == 0
    assert document["world_model_rows_written"] == 0
    assert document["production_integration_ready"] is False
    assert document["plan_certificate"] is False
    assert document["infeasibility_certificate"] is False
    assert authorization.profile.no_operator_control_profile == dynamic.PROFILE_KEY
    assert batched.PRODUCTION_INTEGRATION_READY is False


def test_exact_replay_rejects_selection_or_cap_drift(
    batched_authorization,
) -> None:
    _values, authorization = batched_authorization
    with pytest.raises(
        batched.V075LiveBatchedCausalChildV3InvariantViolation,
        match="differs from exact replay",
    ):
        replace(
            authorization,
            selected_candidate_ids=authorization.selected_candidate_ids[:-1],
        )
    with pytest.raises(
        batched.V075LiveBatchedCausalChildV3InvariantViolation,
        match="differs from exact replay",
    ):
        replace(
            authorization,
            incremental_draw_count=authorization.incremental_draw_count + 1,
        )
    with pytest.raises(
        batched.V075LiveBatchedCausalChildV3InvariantViolation,
        match="profile changed",
    ):
        replace(
            authorization.profile,
            maximum_new_child_action_rows=18,
        )


def test_canonical_byte_verifier_reconstructs_the_exact_union(
    batched_authorization,
) -> None:
    values, authorization = batched_authorization
    replayed, verification = (
        batched.verify_v075_live_batched_causal_child_authorization_bytes_v3(
            source_epoch=values["roots"]["root_model_epoch"],
            namespace=values["namespace"],
            claimed_bytes=authorization.canonical_bytes,
        )
    )
    assert replayed.authorization_id == authorization.authorization_id
    assert verification.authorization_id == authorization.authorization_id
    assert verification.selected_candidate_ids == (
        authorization.selected_candidate_ids
    )
    assert verification.selected_row_binding_ids == (
        authorization.selected_row_binding_ids
    )
    assert verification.incremental_draw_count == 132_096
    document = loads_canonical_json(authorization.canonical_bytes)
    assert isinstance(document, dict)
    document["selected_new_action_row_count"] = 15
    with pytest.raises(
        batched.V075LiveBatchedCausalChildV3InvariantViolation,
        match="differs from exact replay",
    ):
        batched.verify_v075_live_batched_causal_child_authorization_bytes_v3(
            source_epoch=values["roots"]["root_model_epoch"],
            namespace=values["namespace"],
            claimed_bytes=canonical_json_bytes(document),
        )
