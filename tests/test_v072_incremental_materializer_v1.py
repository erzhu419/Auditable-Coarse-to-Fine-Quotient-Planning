from __future__ import annotations

import ast
import copy
from dataclasses import replace
import hashlib
import inspect
from pathlib import Path

import pytest

from acfqp import target_preauthorization_selector_v2 as selector
from acfqp import transfer_guided_acquisition_preregistration_v1 as prereg
from acfqp import v072_incremental_materializer_v1 as materializer
from acfqp import (
    v072_incremental_materializer_independent_verifier_v1 as verifier,
)
from acfqp import v072_incremental_postbuild_bridge_v1 as postbuild


@pytest.fixture(scope="module")
def control_a() -> materializer.DevelopmentAcquisitionControlRunV1:
    return materializer.run_development_incremental_materializer_control_v1(
        materializer.DevelopmentLawKeyV1.HASH_BUCKET_LAW_A
    )


@pytest.fixture(scope="module")
def control_b() -> materializer.DevelopmentAcquisitionControlRunV1:
    return materializer.run_development_incremental_materializer_control_v1(
        materializer.DevelopmentLawKeyV1.HASH_BUCKET_LAW_B
    )


@pytest.fixture(scope="module")
def explicit_occurrence_control() -> (
    materializer.DevelopmentAcquisitionControlRunV1
):
    return materializer.run_development_incremental_materializer_control_v1(
        materializer.DevelopmentLawKeyV1.HASH_BUCKET_LAW_A,
        logical_occurrence_id=_id("protocol-derived-occurrence"),
    )


def _id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


@pytest.fixture(scope="module")
def failed_postbuild_b(
    control_b: materializer.DevelopmentAcquisitionControlRunV1,
) -> postbuild.IncrementalPostbuildResultV1:
    result = postbuild.run_incremental_postbuild_bridge_v1(
        handoff=control_b.handoff
    )
    assert result.audit_status.value == "FAILED_PROOF_FRONTIER"
    return result


@pytest.fixture(scope="module")
def round_two_preparation_b(
    control_b: materializer.DevelopmentAcquisitionControlRunV1,
    failed_postbuild_b: postbuild.IncrementalPostbuildResultV1,
) -> postbuild.DevelopmentRoundTwoPreparationV1:
    return materializer.consume_verified_postbuild_failure_for_round_two_v1(
        first_handoff=control_b.handoff,
        failed_postbuild=failed_postbuild_b,
    )


def test_real_multirow_acquisition_stops_at_honest_pending_handoff(
    control_a: materializer.DevelopmentAcquisitionControlRunV1,
) -> None:
    handoff = control_a.handoff
    assert handoff.status == materializer.PENDING_STATUS
    assert len(handoff.child_rows) == 4
    assert handoff.counters.random_word_calls == 2_048 + 4 * 8_256
    assert handoff.counters.parent_discovery_draws == 0
    assert handoff.counters.parent_validation_draws == 2_048
    assert handoff.counters.child_discovery_draws == 4 * 64
    assert handoff.counters.child_validation_draws == 4 * 8_192
    assert handoff.model_id is None
    assert handoff.selected_policy_id is None
    assert handoff.audit_id is None
    assert handoff.frontier_id is None


def test_all_observer_and_materializer_counters_are_native_zero_before_freeze(
    control_a: materializer.DevelopmentAcquisitionControlRunV1,
) -> None:
    request = control_a.handoff.request
    access = request.preauthorization_access
    assert tuple(item.path for item in access.native_zero_counters) == (
        selector.REQUIRED_NATIVE_ZERO_PATHS
    )
    assert all(
        item.value == 0 and item.observed
        for item in access.native_zero_counters
    )
    assert request.authorization.authorization_sequence == 1
    assert request.authorization.target_access_sequence_minimum == 2
    assert request.authorization.frozen_before_target_access


def test_parent_uses_fresh_validation_only_and_children_use_fresh_64_8192(
    control_a: materializer.DevelopmentAcquisitionControlRunV1,
) -> None:
    handoff = control_a.handoff
    assert handoff.parent_validation_stream.lane is (
        materializer.AcquisitionLaneV1.PARENT_FRESH_VALIDATION
    )
    assert handoff.parent_validation_stream.draw_count == 2_048
    assert handoff.parent_validation_stream.parent_stream_id is None
    for child in handoff.child_rows:
        assert child.discovery_stream.draw_count == 64
        assert child.validation_stream.draw_count == 8_192
        assert (
            child.validation_stream.parent_stream_id
            == child.discovery_stream.stream_id
        )


def test_development_context_is_content_disjoint_from_registered_targets(
    control_a: materializer.DevelopmentAcquisitionControlRunV1,
) -> None:
    context_id = control_a.handoff.request.parent_epoch.context_id
    assert context_id == materializer.development_public_context_v1().context_id
    assert context_id not in {
        item.context_id
        for item in prereg.registered_heldout_public_contexts_v2()
    }
    assert materializer.REGISTERED_EXECUTION_ALLOWED is False


def test_explicit_protocol_occurrence_is_bound_and_independently_replayed(
    explicit_occurrence_control: (
        materializer.DevelopmentAcquisitionControlRunV1
    ),
) -> None:
    occurrence_id = _id("protocol-derived-occurrence")
    assert (
        explicit_occurrence_control.handoff.request.parent_epoch
        .logical_occurrence_id
        == occurrence_id
    )
    attestation = verifier.verify_development_incremental_materializer_control_v1(
        explicit_occurrence_control
    )
    assert attestation.logical_occurrence_id == occurrence_id


def test_occurrence_transplant_or_non_cid_fails_closed(
    explicit_occurrence_control: (
        materializer.DevelopmentAcquisitionControlRunV1
    ),
) -> None:
    attacked = copy.deepcopy(explicit_occurrence_control)
    object.__setattr__(
        attacked.handoff.request.parent_epoch,
        "logical_occurrence_id",
        _id("transplanted-protocol-occurrence"),
    )
    with pytest.raises(
        verifier.IndependentIncrementalMaterializerVerificationFailure
    ):
        verifier.verify_development_incremental_materializer_control_v1(
            attacked
        )
    with pytest.raises(
        materializer.V072IncrementalMaterializerInvariantViolation
    ):
        materializer.run_development_incremental_materializer_control_v1(
            materializer.DevelopmentLawKeyV1.HASH_BUCKET_LAW_A,
            logical_occurrence_id="not-a-content-id",
        )


def test_law_keys_are_outcome_blind_and_have_disjoint_streams(
    control_a: materializer.DevelopmentAcquisitionControlRunV1,
    control_b: materializer.DevelopmentAcquisitionControlRunV1,
) -> None:
    assert all(
        token not in law.value
        for law in materializer.DevelopmentLawKeyV1
        for token in ("CERTIFY", "FAILED", "ROUND_ONE", "ROUND_TWO")
    )
    assert control_a.handoff.status == control_b.handoff.status
    assert (
        control_a.handoff.parent_validation_stream.stream_id
        != control_b.handoff.parent_validation_stream.stream_id
    )
    assert control_a.run_id != control_b.run_id


def test_evidence_first_cardinality_is_complete_and_preselection(
    control_a: materializer.DevelopmentAcquisitionControlRunV1,
) -> None:
    authority = control_a.handoff.request.cardinality_authority
    evidence = authority.evidence
    assert len(evidence.induced_rows) == 4
    assert evidence.already_present_rows == ()
    assert len(evidence.rows_to_acquire) == 4
    assert evidence.exact_round_draw_upper == 35_072
    assert evidence.cumulative_draw_upper == 35_072
    assert authority.selector_gain.cardinality_evidence_id == evidence.evidence_id
    assert authority.selector_gain.exact_draw_upper == 35_072


def test_round_two_cardinality_mechanics_are_nonresetting_and_distinct(
    control_b: materializer.DevelopmentAcquisitionControlRunV1,
    round_two_preparation_b: postbuild.DevelopmentRoundTwoPreparationV1,
) -> None:
    second = (
        round_two_preparation_b.request.cardinality_authority.evidence
    )
    assert second.round_index == 2
    assert len(second.rows_to_acquire) == 2
    assert len(second.cumulative_rows) == 6
    assert second.exact_round_draw_upper == 2_048 + 2 * 8_256
    assert second.cumulative_draw_upper == 2 * 2_048 + 6 * 8_256
    assert second.cumulative_draw_upper == 53_632
    first_ids = {
        item.physical_row_id
        for item in (
            control_b.handoff.request.cardinality_authority.evidence
            .cumulative_rows
        )
    }
    assert first_ids.isdisjoint(
        {item.physical_row_id for item in second.rows_to_acquire}
    )


def test_round_two_executes_only_from_actual_failed_postbuild_authority(
    control_b: materializer.DevelopmentAcquisitionControlRunV1,
    round_two_preparation_b: postbuild.DevelopmentRoundTwoPreparationV1,
) -> None:
    second = (
        round_two_preparation_b.request.cardinality_authority.evidence
    )
    assert second.cumulative_draw_upper <= 160_960
    handoff = materializer.materialize_authorized_incremental_round_v1(
        law_key=control_b.law_key,
        request=round_two_preparation_b.request,
    )
    assert handoff.request.parent_epoch.round_index == 2
    assert len(handoff.child_rows) == 2
    assert handoff.counters.random_word_calls == 18_560
    assert handoff.request.previous_handoff_id == control_b.handoff.handoff_id


def test_independent_verifier_replays_raw_counts_lineage_and_ids(
    control_a: materializer.DevelopmentAcquisitionControlRunV1,
    control_b: materializer.DevelopmentAcquisitionControlRunV1,
) -> None:
    for claimed in (control_a, control_b):
        attestation = (
            verifier.verify_development_incremental_materializer_control_v1(
                claimed
            )
        )
        assert attestation.run_id == claimed.run_id
        assert attestation.handoff_id == claimed.handoff.handoff_id
        assert attestation.acquired_child_row_count == 4
        assert attestation.exact_draw_count == 35_072
        assert attestation.status == materializer.PENDING_STATUS


def test_independent_verifier_does_not_call_production_execution_helpers(
    control_a: materializer.DevelopmentAcquisitionControlRunV1,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden(*_args, **_kwargs):
        raise AssertionError("production execution helper was called")

    for name in (
        "_acquire_stream",
        "_raw_summary",
        "derive_development_cardinality_evidence_v1",
        "materialize_authorized_incremental_round_v1",
        "run_development_incremental_materializer_control_v1",
    ):
        monkeypatch.setattr(materializer, name, forbidden)
    attestation = (
        verifier.verify_development_incremental_materializer_control_v1(
            control_a
        )
    )
    assert attestation.exact_draw_count == 35_072


def test_raw_digest_tamper_is_rejected(
    control_a: materializer.DevelopmentAcquisitionControlRunV1,
) -> None:
    attacked = copy.deepcopy(control_a)
    object.__setattr__(
        attacked.handoff.child_rows[0].validation_stream,
        "raw_word_digest",
        "0" * 64,
    )
    with pytest.raises(
        verifier.IndependentIncrementalMaterializerVerificationFailure,
        match="raw word tape",
    ):
        verifier.verify_development_incremental_materializer_control_v1(
            attacked
        )


def test_counter_and_row_union_tampering_are_rejected(
    control_a: materializer.DevelopmentAcquisitionControlRunV1,
) -> None:
    attacked_counter = copy.deepcopy(control_a)
    object.__setattr__(
        attacked_counter.handoff.counters,
        "accepted_draws",
        attacked_counter.handoff.counters.accepted_draws + 1,
    )
    with pytest.raises(
        verifier.IndependentIncrementalMaterializerVerificationFailure
    ):
        verifier.verify_development_incremental_materializer_control_v1(
            attacked_counter
        )

    attacked_union = copy.deepcopy(control_a)
    object.__setattr__(
        attacked_union.handoff,
        "resulting_physical_row_ids",
        attacked_union.handoff.resulting_physical_row_ids[:-1],
    )
    with pytest.raises(
        verifier.IndependentIncrementalMaterializerVerificationFailure,
        match="row union",
    ):
        verifier.verify_development_incremental_materializer_control_v1(
            attacked_union
        )


def test_authorization_transplant_is_rejected(
    control_a: materializer.DevelopmentAcquisitionControlRunV1,
) -> None:
    attacked = copy.deepcopy(control_a)
    object.__setattr__(
        attacked.handoff.request.authorization,
        "model_id",
        _id("foreign-model"),
    )
    with pytest.raises(
        verifier.IndependentIncrementalMaterializerVerificationFailure,
        match="authorization",
    ):
        verifier.verify_development_incremental_materializer_control_v1(
            attacked
        )


def test_handoff_cannot_claim_a_model_policy_or_audit(
    control_a: materializer.DevelopmentAcquisitionControlRunV1,
) -> None:
    for field in ("model_id", "selected_policy_id", "audit_id", "frontier_id"):
        attacked = copy.deepcopy(control_a)
        object.__setattr__(attacked.handoff, field, _id(f"forged-{field}"))
        with pytest.raises(
            verifier.IndependentIncrementalMaterializerVerificationFailure,
            match="invents model",
        ):
            verifier.verify_development_incremental_materializer_control_v1(
                attacked
            )


def test_registered_entrypoint_remains_fail_closed() -> None:
    with pytest.raises(materializer.RegisteredV072IncrementalMaterializerLocked):
        materializer.run_registered_v072_incremental_materializer_v1()


def test_public_api_has_no_caller_supplied_result_or_audit_status_parameter() -> None:
    parameters = inspect.signature(
        materializer.materialize_authorized_incremental_round_v1
    ).parameters
    assert tuple(parameters) == ("law_key", "request")
    forbidden = {
        "result",
        "status",
        "audit_result",
        "audit_required_row_ids",
        "certificate",
        "model",
        "policy",
        "frontier",
    }
    assert forbidden.isdisjoint(parameters)


def test_ast_has_no_draft_freezer_hidden_law_or_result_profile() -> None:
    source_path = Path(materializer.__file__)
    source = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    called_names = {
        (
            node.func.attr
            if isinstance(node.func, ast.Attribute)
            else node.func.id
        )
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, (ast.Attribute, ast.Name))
    }
    assert "freeze_transfer_guided_acquisition_preregistration_v1" not in (
        called_names
    )
    assert "frozen_heldout_environment_manifest_v1" not in called_names
    assert "hidden_spawn_law" not in called_names
    assert "audit_required_row_ids" not in source
    assert "CERTIFY_AFTER_ROUND" not in source

    registered_calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "registered_heldout_public_contexts_v2"
    ]
    assert len(registered_calls) == 1


def test_contract_and_cap_constants_are_frozen() -> None:
    assert materializer.PROPOSED_CONTRACT_VERSION == "1.36.0"
    assert materializer.MAX_ROUNDS == 2
    assert materializer.MAX_CUMULATIVE_CHILD_ROWS == 19
    assert materializer.MAX_CUMULATIVE_DRAWS == 160_960
    assert materializer.cumulative_draw_upper_v1(2, 19) == 160_960
    with pytest.raises(materializer.V072IncrementalMaterializerInvariantViolation):
        materializer.cumulative_draw_upper_v1(2, 20)
