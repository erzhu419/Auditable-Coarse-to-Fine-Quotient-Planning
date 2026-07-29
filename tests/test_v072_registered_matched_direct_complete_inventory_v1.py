from __future__ import annotations

from dataclasses import replace
from fractions import Fraction
import hashlib
import inspect

import pytest

from acfqp import heldout_graph_transition_observer_v2 as observer
from acfqp import v072_cold_h2_closure_v1 as cold
from acfqp import (
    v072_registered_matched_direct_complete_inventory_v1 as direct,
)


def _id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def test_production_factories_accept_no_rows_law_counts_or_outcomes() -> None:
    signatures = {
        "open": inspect.signature(
            direct
            .open_registered_matched_direct_complete_inventory_accumulator_v1
        ),
        "run": inspect.signature(
            direct.run_registered_matched_direct_complete_inventory_v1
        ),
        "checkpoint": inspect.signature(
            direct
            .acquire_registered_matched_direct_complete_inventory_checkpoint_v1
        ),
        "verify": inspect.signature(
            direct
            .verify_registered_matched_direct_complete_inventory_checkpoint_v1
        ),
    }
    assert tuple(signatures["open"].parameters) == (
        "authority_chain",
        "anchor",
        "occurrence_plan",
        "context",
    )
    assert tuple(signatures["run"].parameters) == (
        "authority_chain",
        "anchor",
        "occurrence_plan",
        "context",
    )
    assert tuple(signatures["checkpoint"].parameters) == (
        "accumulator",
        "checkpoint",
    )
    assert tuple(signatures["verify"].parameters) == (
        "checkpoint_artifact",
    )
    assert all(
        parameter.kind is inspect.Parameter.KEYWORD_ONLY
        for signature in signatures.values()
        for parameter in signature.parameters.values()
    )
    forbidden = {
        "rows",
        "row_count",
        "catalogues",
        "law",
        "probabilities",
        "outcomes",
        "observations",
        "counts",
        "intervals",
        "status",
        "terminal",
        "callback",
        "evaluation_only_exact_atoms",
    }
    assert all(
        forbidden.isdisjoint(signature.parameters)
        for signature in signatures.values()
    )


def test_invalid_or_rebound_chain_has_zero_observer_access(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def forbidden(*_args: object, **_kwargs: object) -> None:
        calls.append("OBSERVER")
        raise AssertionError("observer access preceded authority verification")

    for module, name in (
        (observer, "root_state_v2"),
        (observer, "legal_action_catalogue_v2"),
        (observer, "open_heldout_target_transition_stream_v2"),
        (observer, "evaluation_only_exact_atoms_v2"),
    ):
        monkeypatch.setattr(module, name, forbidden)
    with pytest.raises(
        direct.RegisteredMatchedDirectInventoryGateLockedV1
    ) as captured:
        direct.open_registered_matched_direct_complete_inventory_accumulator_v1(
            authority_chain=object(),  # type: ignore[arg-type]
            anchor=object(),  # type: ignore[arg-type]
            occurrence_plan=object(),  # type: ignore[arg-type]
            context=object(),  # type: ignore[arg-type]
        )
    assert captured.value.access_audit == direct.ZERO_TARGET_ACCESS_AUDIT
    assert (
        captured.value.access_audit.observer_or_target_access_started
        is False
    )
    assert calls == []


def test_registration_disjoint_core_uses_one_append_only_stream_prefix() -> None:
    result = direct.run_registration_disjoint_complete_inventory_schedule_v1()
    assert tuple(item.checkpoint for item in result.checkpoints) == (
        2_048,
        4_096,
        8_192,
        16_384,
    )
    assert len(result.checkpoints[0].stable_row_binding_ids) == 5
    assert all(
        item.stable_row_binding_ids
        == result.checkpoints[0].stable_row_binding_ids
        for item in result.checkpoints
    )
    expected_ranges = (
        (1, 2_048),
        (2_049, 4_096),
        (4_097, 8_192),
        (8_193, 16_384),
    )
    for checkpoint, expected_range in zip(
        result.checkpoints,
        expected_ranges,
        strict=True,
    ):
        assert {
            (
                item.appended_start_index,
                item.appended_end_index,
            )
            for item in checkpoint.prefixes
        } == {expected_range}
    for previous, current in zip(
        result.checkpoints[:-1],
        result.checkpoints[1:],
        strict=True,
    ):
        assert tuple(
            item.previous_prefix_id for item in current.prefixes
        ) == tuple(item.prefix_id for item in previous.prefixes)
        assert tuple(
            item.validation_stream_id for item in current.prefixes
        ) == tuple(
            item.validation_stream_id for item in previous.prefixes
        )


def test_direct_work_charges_final_prefix_not_sum_of_checkpoints() -> None:
    result = direct.run_registration_disjoint_complete_inventory_schedule_v1()
    row_count = 5
    expected = row_count * (64 + 16_384)
    assert result.final_acquisition_sample_total == expected
    assert (
        result.checkpoints[-1].work.deterministic_verifier_replay_total
        == expected
    )
    assert result.final_acquisition_sample_total < sum(
        item.work.acquisition_sample_total
        for item in result.checkpoints
    )
    assert result.sum_of_checkpoint_totals_charged is False
    assert result.crn_draw_discount == 0
    assert all(
        item.work.acquisition_sample_total
        == row_count * (64 + item.checkpoint)
        and item.work.deterministic_verifier_replay_total
        == row_count * (64 + item.checkpoint)
        and item.work.crn_draw_discount == 0
        for item in result.checkpoints
    )
    assert tuple(
        item.work.acquisition_discovery_draws_new
        for item in result.checkpoints
    ) == (row_count * 64, 0, 0, 0)
    assert tuple(
        item.work.replay_discovery_draws_new
        for item in result.checkpoints
    ) == (row_count * 64, 0, 0, 0)


def test_direct_work_rejects_checkpoint_sum_or_wrong_delta() -> None:
    valid = direct.RegisteredMatchedDirectCheckpointWorkV1(
        4_096,
        2_048,
        3,
        3 * 64,
        3 * 2_048,
        3 * 4_096,
        3 * (64 + 4_096),
        3 * 64,
        3 * 2_048,
        3 * 4_096,
        3 * (64 + 4_096),
        6,
        6,
    )
    with pytest.raises(
        direct.V072RegisteredMatchedDirectInventoryViolation,
        match="summed checkpoints|mixed replay",
    ):
        replace(
            valid,
            acquisition_sample_total=3
            * ((64 + 2_048) + (64 + 4_096)),
        )
    with pytest.raises(
        direct.V072RegisteredMatchedDirectInventoryViolation,
        match="summed checkpoints|mixed replay",
    ):
        replace(valid, acquisition_validation_draws_new=1)


def test_disjoint_prefix_replacement_and_redraw_are_rejected() -> None:
    result = direct.run_registration_disjoint_complete_inventory_schedule_v1()
    second = result.checkpoints[1].prefixes[0]
    with pytest.raises(
        direct.V072RegisteredMatchedDirectInventoryViolation,
        match="skipped|redrew",
    ):
        replace(second, appended_start_index=1)
    with pytest.raises(
        direct.V072RegisteredMatchedDirectInventoryViolation,
        match="skipped|redrew",
    ):
        replace(second, previous_prefix_id=None)


@pytest.mark.parametrize("checkpoint", (2_048, 4_096, 8_192, 16_384))
def test_direct_native_row_work_supports_every_registered_checkpoint(
    checkpoint: int,
) -> None:
    work = cold.ColdRowNativeWorkV1(
        acquisition_purpose=(
            cold.ColdRowAcquisitionPurposeV1.MATCHED_DIRECT_CHECKPOINT
        ),
        discovery_draws=64,
        validation_draws=checkpoint,
        discovery_random_word_calls=64,
        validation_random_word_calls=checkpoint,
    )
    assert work.total_draws == 64 + checkpoint
    assert work.acquisition_purpose is (
        cold.ColdRowAcquisitionPurposeV1.MATCHED_DIRECT_CHECKPOINT
    )


def test_direct_private_capabilities_cannot_be_faked() -> None:
    ids = tuple(_id(f"id-{index}") for index in range(12))
    with pytest.raises(
        direct.V072RegisteredMatchedDirectInventoryViolation,
        match="confidence replay attestation",
    ):
        direct.RegisteredMatchedDirectConfidenceReplayAttestationV1(
            object(),
            ids[0],
            ids[1],
            ids[2],
            ids[3],
            ids[4],
            ids[5],
            ids[6],
            ids[7],
            ids[8],
            (ids[9],),
            (ids[10],),
            (),
            (ids[11], _id("other-event")),
            (2_048, 0),
            ((Fraction(0), Fraction(1)),) * 2,
            2_048,
            2,
            2_112,
        )
