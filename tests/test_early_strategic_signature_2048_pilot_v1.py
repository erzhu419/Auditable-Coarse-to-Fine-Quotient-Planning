from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from acfqp.domains import standard_2048
from acfqp.science import early_strategic_signature_2048_pilot_v1 as subject
from acfqp.science.latent_resource_2048_v1 import (
    encode_standard_2048_state_only_board_v1,
    encode_standard_2048_state_only_state_v1,
)
from acfqp.science.latent_resource_hybrid_confirmatory_protocol_v2 import (
    HYBRID_INPUT_DIMENSION_V2,
    HYBRID_PARAMETER_COUNT_V2,
)
from acfqp.science.matched_2048_env_v1 import legal_action_mask_v1
from acfqp.science.matched_double_dqn_2048_v1 import (
    _network_factory,
    _parameter_count,
)


def _first_legal(_state, mask: tuple[bool, bool, bool, bool]) -> int:
    return next(index for index, allowed in enumerate(mask) if allowed)


def _zero_candidate_model():
    torch = pytest.importorskip("torch")
    model = _network_factory(torch, HYBRID_INPUT_DIMENSION_V2)()
    for parameter in model.parameters():
        parameter.data.zero_()
    return model.eval()


def test_strict_bare_candidate_state_dict_loader(tmp_path: Path) -> None:
    torch = pytest.importorskip("torch")
    model = _zero_candidate_model()
    path = tmp_path / "candidate.pt"
    torch.save(model.state_dict(), path)

    loaded = subject.load_candidate_policy_v1(path, "cpu")
    assert loaded.training is False
    assert _parameter_count(loaded) == HYBRID_PARAMETER_COUNT_V2
    observation = torch.arange(
        HYBRID_INPUT_DIMENSION_V2, dtype=torch.float32
    ).unsqueeze(0)
    assert torch.equal(model(observation), loaded(observation))

    wrapped = tmp_path / "wrapped.pt"
    torch.save({"state_dict": model.state_dict()}, wrapped)
    with pytest.raises(
        subject.EarlyStrategicSignature2048PilotV1Error,
        match="bare candidate state_dict",
    ):
        subject.load_candidate_policy_v1(wrapped, "cpu")

    wrong_dimension = tmp_path / "raw-16d.pt"
    torch.save(_network_factory(torch, 16)().state_dict(), wrong_dimension)
    with pytest.raises(subject.EarlyStrategicSignature2048PilotV1Error):
        subject.load_candidate_policy_v1(wrong_dimension, "cpu")


def test_full_game_and_prefix_are_deterministic_and_tape_independent() -> None:
    first = subject.collect_full_game_v1(
        _first_legal,
        tape_root="label-independent-v1",
        episode_index=3,
    )
    second = subject.collect_full_game_v1(
        _first_legal,
        tape_root="label-independent-v1",
        episode_index=3,
    )
    assert first == second
    assert first.completed_game is True
    assert first.states[-1].status is not standard_2048.Swipe2048Status.ACTIVE
    assert first.label_document()["total_merge_score"] == sum(first.merge_scores)

    label, prefix = subject.collect_independent_policy_tapes_v1(
        _first_legal,
        label_tape_root="label-independent-v1",
        prefix_tape_root="prefix-independent-v1",
        episode_index=3,
    )
    assert label == first
    assert len(prefix.action_indices) == 8
    assert len(prefix.states) == 9
    for state, action_index in zip(
        prefix.states[:-1], prefix.action_indices, strict=True
    ):
        assert legal_action_mask_v1(state)[action_index]

    with pytest.raises(
        subject.EarlyStrategicSignature2048PilotV1Error,
        match="independent",
    ):
        subject.collect_independent_policy_tapes_v1(
            _first_legal,
            label_tape_root="same-root",
            prefix_tape_root="same-root",
            episode_index=0,
        )


def test_prefix_feature_layout_is_exact_and_not_canonicalized(monkeypatch) -> None:
    prefix = subject.collect_prefix_v1(
        _first_legal,
        tape_root="feature-prefix-v1",
        episode_index=5,
    )
    original_step = standard_2048.step_v1

    def forbidden_spawn_successor(*_args, **_kwargs):
        raise AssertionError("strategic features consulted a post-spawn successor")

    monkeypatch.setattr(standard_2048, "step_v1", forbidden_spawn_successor)
    features = subject.prefix_feature_vectors_v1(prefix)
    monkeypatch.setattr(standard_2048, "step_v1", original_step)

    raw = features[subject.RAW_PREFIX_ARM_V1]
    rotated = features[subject.ROTATED_PREFIX_ARM_V1]
    strategic = features[subject.STRATEGIC_PREFIX_ARM_V1]
    assert len(raw) == subject.RAW_PREFIX_DIMENSION_V1 == 184
    assert len(rotated) == len(strategic) == subject.AUGMENTED_PREFIX_DIMENSION_V1
    assert tuple(raw[:16]) == tuple(
        rank / standard_2048.GOAL_RANK for rank in prefix.states[0].board
    )

    action_offset = 9 * 16
    for decision, action_index in enumerate(prefix.action_indices):
        one_hot = raw[action_offset + 4 * decision : action_offset + 4 * decision + 4]
        assert one_hot == tuple(float(index == action_index) for index in range(4))
    assert raw[-8:] == tuple(
        math.log2(score + 1) / standard_2048.GOAL_RANK
        for score in prefix.merge_scores
    )

    expected_rotated = tuple(
        rank / standard_2048.GOAL_RANK
        for state_index in (0, 2, 5, 8)
        for rank in reversed(prefix.states[state_index].board)
    )
    assert rotated[:184] == raw
    assert rotated[184:] == expected_rotated
    assert strategic[:184] == raw

    append = strategic[184:]
    final_resource = encode_standard_2048_state_only_state_v1(
        prefix.states[-1]
    ).resource_vector
    assert append[:16] == tuple(float(value) for value in final_resource)
    assert len(append) == subject.STRATEGIC_APPEND_DIMENSION_V1 == 64
    assert all(value >= 0 for value in append[32:48])
    assert len(subject.TRAJECTORY_SUMMARY_NAMES_V1) == len(append[48:]) == 16

    expected_harmful = [0.0] * 8
    expected_beneficial = [0.0] * 8
    for state, action_index in zip(
        prefix.states[:-1], prefix.action_indices, strict=True
    ):
        before = encode_standard_2048_state_only_state_v1(state).resource_vector
        action = standard_2048.ACTION_ORDER[action_index]
        after_board, _score, changed = standard_2048.swipe_board_v1(
            state.board, action
        )
        assert changed
        after = encode_standard_2048_state_only_board_v1(after_board).resource_vector
        for index in range(8):
            beneficial_delta = float(
                before[index] - after[index]
                if index == 7
                else after[index] - before[index]
            )
            expected_beneficial[index] += max(0.0, beneficial_delta)
            expected_harmful[index] += max(0.0, -beneficial_delta)
    assert append[32:40] == pytest.approx(expected_harmful)
    assert append[40:48] == pytest.approx(expected_beneficial)


def test_illegal_policy_action_is_never_silently_accepted() -> None:
    def illegal(_state, _mask: tuple[bool, bool, bool, bool]) -> int:
        return 99

    with pytest.raises(
        subject.EarlyStrategicSignature2048PilotV1Error,
        match="not legal and accepted",
    ):
        subject.collect_prefix_v1(
            illegal,
            tape_root="illegal-policy-v1",
            episode_index=0,
        )


def test_high_level_policy_evidence_is_json_serializable_and_matrix_exact() -> None:
    model = _zero_candidate_model()
    evidence = subject.collect_policy_evidence_v1(
        model,
        label_tape_root="u005-label-tapes-v1",
        prefix_tape_root="u005-prefix-tapes-v1",
        episode_indices=(0, 1),
    )
    json.dumps(evidence, allow_nan=False, sort_keys=True)
    assert evidence["independent_tape_roots"] is True
    assert evidence["state_canonicalization_applied"] is False
    assert len(evidence["label_rows"]) == 2
    assert all(row["decision_count"] > 8 for row in evidence["label_rows"])
    assert evidence["prefix_feature_dimensions"] == {
        subject.RAW_PREFIX_ARM_V1: 184,
        subject.ROTATED_PREFIX_ARM_V1: 248,
        subject.STRATEGIC_PREFIX_ARM_V1: 248,
    }
    assert {
        arm: (len(matrix), len(matrix[0]))
        for arm, matrix in evidence["prefix_matrices"].items()
    } == {
        subject.RAW_PREFIX_ARM_V1: (2, 184),
        subject.ROTATED_PREFIX_ARM_V1: (2, 248),
        subject.STRATEGIC_PREFIX_ARM_V1: (2, 248),
    }
