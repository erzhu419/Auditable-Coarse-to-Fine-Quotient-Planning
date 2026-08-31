from __future__ import annotations

import json
import math

import pytest

from acfqp.domains import standard_2048
from acfqp.science import decision_point_signature_2048_pilot_v2 as subject
from acfqp.science import early_strategic_signature_2048_pilot_v1 as v1
from acfqp.science.matched_2048_env_v1 import legal_action_mask_v1


def _first_legal(_state, mask: tuple[bool, bool, bool, bool]) -> int:
    return next(index for index, allowed in enumerate(mask) if allowed)


def test_fixed_state_library_is_deterministic_eligible_and_round_trips() -> None:
    first = subject.build_decision_state_library_v2()
    second = subject.build_decision_state_library_v2()

    assert first is second
    assert len(first) == subject.DECISION_STATE_COUNT_V2 == 64
    assert tuple(row.state_index for row in first) == tuple(range(64))
    assert len({row.generator_episode_index for row in first}) == 64
    assert (first[0].generator_episode_index, first[0].generator_decision_index) == (
        5,
        44,
    )
    assert first[0].board == (
        0,
        0,
        0,
        0,
        2,
        0,
        1,
        0,
        3,
        3,
        0,
        0,
        6,
        3,
        2,
        0,
    )
    assert first[-1].generator_episode_index == 143

    for row in first:
        state = standard_2048.state_from_board_v1(row.board)
        assert subject.is_eligible_decision_state_v2(state)
        assert row.maximum_rank >= subject.MINIMUM_DECISION_MAXIMUM_RANK_V2
        assert row.empty_cell_count >= subject.MINIMUM_DECISION_EMPTY_CELL_COUNT_V2
        assert len(row.legal_action_indices) >= 2
        assert row.corner_preserving_action_indices
        assert row.corner_breaking_action_indices
        assert subject.FrozenDecisionStateV2.from_document(row.to_document()) == row

    tampered = first[0].to_document()
    tampered["maximum_rank"] += 1
    with pytest.raises(
        subject.DecisionPointSignature2048PilotV2Error,
        match="disagrees",
    ):
        subject.FrozenDecisionStateV2.from_document(tampered)

    initial = standard_2048.state_from_board_v1((1, 0, 0, 0) * 4)
    assert subject.is_eligible_decision_state_v2(initial) is False


def test_decision_prefix_and_feature_layout_are_exact_and_observation_only(
    monkeypatch,
) -> None:
    frozen = subject.build_decision_state_library_v2()[0]
    prefix = subject.collect_decision_prefix_v2(_first_legal, frozen)
    assert len(prefix.action_indices) == 8
    assert len(prefix.states) == 9
    assert prefix.states[0].board == frozen.board
    assert prefix.episode_index == frozen.state_index
    for state, action_index in zip(
        prefix.states[:-1], prefix.action_indices, strict=True
    ):
        assert legal_action_mask_v1(state)[action_index]

    def forbidden_future_spawn(*_args, **_kwargs):
        raise AssertionError("features consulted a post-spawn future")

    monkeypatch.setattr(standard_2048, "step_v1", forbidden_future_spawn)
    features = subject.decision_prefix_feature_vectors_v2(prefix)
    assert {arm: len(vector) for arm, vector in features.items()} == {
        subject.RAW_PREFIX_ARM_V2: 184,
        subject.ROTATED_PREFIX_ARM_V2: 248,
        subject.STRATEGIC_PREFIX_ARM_V2: 248,
    }

    raw = features[subject.RAW_PREFIX_ARM_V2]
    rotated = features[subject.ROTATED_PREFIX_ARM_V2]
    strategic = features[subject.STRATEGIC_PREFIX_ARM_V2]
    assert raw[:16] == tuple(
        rank / standard_2048.GOAL_RANK for rank in frozen.board
    )
    expected_rotated = tuple(
        rank / standard_2048.GOAL_RANK
        for state_index in (0, 2, 5, 8)
        for rank in reversed(prefix.states[state_index].board)
    )
    assert rotated[:184] == raw
    assert rotated[184:] == expected_rotated
    assert strategic[:184] == raw
    assert len(strategic[184:232]) == 48
    assert len(strategic[232:]) == len(subject.DECISION_SUMMARY_NAMES_V2) == 16
    assert all(math.isfinite(value) for value in strategic)


def test_opportunity_regret_is_span_normalized_and_decision_conditioned() -> None:
    frozen = subject.build_decision_state_library_v2()[0]

    def choose_worst_resource(
        state: standard_2048.Swipe2048State,
        mask: tuple[bool, bool, bool, bool],
    ) -> int:
        legal = tuple(index for index, allowed in enumerate(mask) if allowed)
        qualities = {
            index: v1._observable_quality_v1(
                v1._pre_spawn_resource_v1(state, index)
            )
            for index in legal
        }
        return min(legal, key=lambda index: (qualities[index], index))

    prefix = subject.collect_decision_prefix_v2(choose_worst_resource, frozen)
    regrets = subject.opportunity_normalized_resource_regrets_v2(prefix)
    assert len(regrets) == 8
    assert regrets[0] == pytest.approx(1.0)
    assert all(0.0 <= value <= 1.0 for value in regrets)

    summaries = dict(
        zip(
            subject.DECISION_SUMMARY_NAMES_V2,
            subject.decision_summaries_v2(prefix),
            strict=True,
        )
    )
    assert 0.0 < summaries["corner_opportunity_fraction"] <= 1.0
    assert (
        summaries["chosen_corner_preservation_fraction"]
        + summaries["corner_break_fraction"]
    ) == pytest.approx(1.0)
    assert 0.0 <= summaries[
        "mean_opportunity_normalized_resource_regret"
    ] <= summaries["maximum_opportunity_normalized_resource_regret"] <= 1.0
    assert 0.0 <= summaries[
        "resource_optimal_action_match_fraction"
    ] <= 1.0


def test_policy_collector_emits_exact_unlabelled_64_row_schema(monkeypatch) -> None:
    library = subject.build_decision_state_library_v2()
    monkeypatch.setattr(subject, "model_action_selector_v2", lambda _model: _first_legal)
    evidence = subject.collect_policy_decision_evidence_v2(
        object(), state_library=library
    )
    json.dumps(evidence, allow_nan=False, sort_keys=True)

    assert set(evidence) == {
        "schema",
        "state_library_tape_root",
        "prefix_tape_root",
        "state_count",
        "state_indices",
        "prefix_accepted_legal_action_count",
        "state_canonicalization_applied",
        "label_lane_present",
        "decision_state_rows",
        "prefix_rows",
        "prefix_feature_dimensions",
        "prefix_matrices",
        "strategic_features_use_only_observed_prefix_and_pre_spawn_swipes",
        "independent_state_generation_and_policy_execution",
    }
    assert evidence["schema"] == (
        "acfqp.science.decision_point_signature_2048_pilot_evidence.v2"
    )
    assert evidence["state_count"] == 64
    assert evidence["state_indices"] == list(range(64))
    assert evidence["label_lane_present"] is False
    assert evidence["state_canonicalization_applied"] is False
    assert evidence[
        "strategic_features_use_only_observed_prefix_and_pre_spawn_swipes"
    ] is True
    assert len(evidence["decision_state_rows"]) == 64
    assert len(evidence["prefix_rows"]) == 64
    assert all(len(row["action_indices"]) == 8 for row in evidence["prefix_rows"])
    assert evidence["prefix_feature_dimensions"] == {
        subject.RAW_PREFIX_ARM_V2: 184,
        subject.ROTATED_PREFIX_ARM_V2: 248,
        subject.STRATEGIC_PREFIX_ARM_V2: 248,
    }
    assert {
        arm: (len(matrix), len(matrix[0]))
        for arm, matrix in evidence["prefix_matrices"].items()
    } == {
        subject.RAW_PREFIX_ARM_V2: (64, 184),
        subject.ROTATED_PREFIX_ARM_V2: (64, 248),
        subject.STRATEGIC_PREFIX_ARM_V2: (64, 248),
    }


def test_library_validator_rejects_a_reordered_frozen_registry() -> None:
    library = list(subject.build_decision_state_library_v2())
    library[0], library[1] = library[1], library[0]
    with pytest.raises(
        subject.DecisionPointSignature2048PilotV2Error,
        match="differs",
    ):
        subject.validate_decision_state_library_v2(library)
