from __future__ import annotations

import math
from pathlib import Path

import pytest

from acfqp.domains import standard_2048
from acfqp.science import learned_resource_forecast_2048_v1 as subject
from acfqp.science.early_strategic_signature_2048_pilot_v1 import (
    collect_full_game_v1,
    collect_prefix_v1,
)
from acfqp.science.latent_resource_2048_v1 import (
    encode_standard_2048_state_only_state_v1,
)
from acfqp.science.latent_resource_hybrid_confirmatory_protocol_v2 import (
    HYBRID_CONFIRMATORY_ARMS_V2,
    RAW_STANDARD_ARM_V2,
)
from acfqp.science.matched_2048_env_v1 import (
    initial_state_v1,
    legal_action_mask_v1,
)
from acfqp.science.matched_double_dqn_2048_v1 import _network_factory


def _first_legal(_state, mask: tuple[bool, bool, bool, bool]) -> int:
    return next(index for index, allowed in enumerate(mask) if allowed)


@pytest.fixture(scope="module")
def complete_traces():
    return (
        collect_full_game_v1(
            _first_legal,
            tape_root="learned-resource-trajectory-player-a",
            episode_index=0,
        ),
        collect_full_game_v1(
            _first_legal,
            tape_root="learned-resource-trajectory-player-b",
            episode_index=0,
        ),
    )


def test_prefix_tokens_and_raw_layout_are_exact_and_observable_only() -> None:
    prefix = collect_prefix_v1(
        _first_legal,
        tape_root="learned-resource-probe-prefix",
        episode_index=4,
    )
    tokens = subject.prefix_tokens_v1(prefix)
    raw = subject.raw_prefix_v1(prefix)

    assert len(tokens) == subject.PREFIX_ACTION_COUNT_V1 == 8
    assert {len(row) for row in tokens} == {subject.PREFIX_TOKEN_WIDTH_V1}
    assert len(raw) == subject.RAW_PREFIX_DIMENSION_V1 == 184
    for decision, row in enumerate(tokens):
        assert row[:16] == tuple(
            rank / standard_2048.GOAL_RANK
            for rank in prefix.states[decision].board
        )
        assert row[16:20] == tuple(
            float(index == prefix.action_indices[decision]) for index in range(4)
        )
        assert row[20] == pytest.approx(
            math.log2(prefix.merge_scores[decision] + 1)
            / standard_2048.GOAL_RANK
        )
    assert raw[: 9 * 16] == tuple(
        rank / standard_2048.GOAL_RANK
        for state in prefix.states
        for rank in state.board
    )
    assert raw[9 * 16 : 9 * 16 + 32] == tuple(
        float(index == action)
        for action in prefix.action_indices
        for index in range(4)
    )
    assert raw[-8:] == tuple(row[-1] for row in tokens)


def test_complete_trajectory_windows_span_episode_and_targets_clamp(
    complete_traces,
) -> None:
    assert subject.deterministic_window_starts_v1(8) == (0,)
    assert subject.deterministic_window_starts_v1(9) == (0, 1)
    assert subject.deterministic_window_starts_v1(39) == tuple(range(32))
    forty_starts = subject.deterministic_window_starts_v1(40)
    assert len(forty_starts) == 32
    assert forty_starts[0] == 0 and forty_starts[-1] == 32
    trace = complete_traces[0]
    starts = subject.deterministic_window_starts_v1(len(trace.action_indices))
    assert len(starts) == subject.MAX_WINDOWS_PER_COMPLETE_TRAJECTORY_V1 == 32
    assert starts[0] == 0
    assert starts[-1] == len(trace.action_indices) - 8
    assert all(left < right for left, right in zip(starts[:-1], starts[1:]))
    assert starts == subject.deterministic_window_starts_v1(
        len(trace.action_indices)
    )

    examples = subject.aligned_forecast_examples_v1(trace, player_id="player-a")
    assert len(examples) == 32
    assert tuple(example.key.window_start for example in examples) == starts
    assert all(example.key == example.target_source_key for example in examples)

    first = examples[0]
    endpoint = 8
    expected_blocks = []
    for horizon in subject.FORECAST_HORIZONS_V1:
        state_index = min(endpoint + horizon, len(trace.action_indices))
        expected_blocks.extend(
            float(value)
            for value in encode_standard_2048_state_only_state_v1(
                trace.states[state_index]
            ).resource_vector
        )
        future_score = sum(trace.merge_scores[endpoint:state_index])
        expected_blocks.append(
            math.log2(future_score + 1) / standard_2048.GOAL_RANK
        )
        expected_blocks.append(
            float(endpoint + horizon >= len(trace.action_indices))
        )
    assert first.target == pytest.approx(expected_blocks)

    final = examples[-1].target
    final_resource = tuple(
        float(value)
        for value in encode_standard_2048_state_only_state_v1(
            trace.states[-1]
        ).resource_vector
    )
    for offset in range(0, subject.FORECAST_TARGET_DIMENSION_V1, 18):
        assert final[offset : offset + 16] == final_resource
        assert final[offset + 16] == 0.0
        assert final[offset + 17] == 1.0


def test_player_shuffle_is_a_same_player_derangement_and_preserves_inputs(
    complete_traces,
) -> None:
    aligned = (
        *subject.aligned_forecast_examples_v1(
            complete_traces[0], player_id="player-a"
        ),
        *subject.aligned_forecast_examples_v1(
            complete_traces[1], player_id="player-b"
        ),
    )
    shuffled = subject.player_shuffled_targets_v1(aligned)
    reversed_shuffled = subject.player_shuffled_targets_v1(tuple(reversed(aligned)))
    assert {
        row.key: row.target_source_key for row in shuffled
    } == {
        row.key: row.target_source_key for row in reversed_shuffled
    }
    assert len(shuffled) == len(aligned) == 64
    for original, control in zip(aligned, shuffled, strict=True):
        assert control.key == original.key
        assert control.tokens == original.tokens
        assert control.target_source_key.player_id == original.key.player_id
        assert control.target_source_key != original.key
    for player in ("player-a", "player-b"):
        original_sources = sorted(
            row.target_source_key for row in aligned if row.key.player_id == player
        )
        shuffled_sources = sorted(
            row.target_source_key
            for row in shuffled
            if row.key.player_id == player
        )
        assert original_sources == shuffled_sources

    roots = tuple(trace.tape_root for trace in complete_traces)
    assert subject.validate_forecast_training_examples_v1(
        aligned,
        eligible_player_ids=("player-a", "player-b"),
        trajectory_tape_roots=roots,
        ineligible_player_ids=("heldout-player",),
        forbidden_tape_roots=("label-root", "probe-root"),
        target_mode=subject.ALIGNED_TARGET_MODE_V1,
    ) == aligned
    assert subject.validate_forecast_training_examples_v1(
        shuffled,
        eligible_player_ids=("player-a", "player-b"),
        trajectory_tape_roots=roots,
        ineligible_player_ids=("heldout-player",),
        forbidden_tape_roots=("label-root", "probe-root"),
        target_mode=subject.PLAYER_SHUFFLED_TARGET_MODE_V1,
    ) == shuffled


def test_strict_lane_and_leakage_validation_rejects_overlap_and_foreign_rows(
    complete_traces,
) -> None:
    subject.validate_disjoint_lane_roots_v1(
        trajectory_tape_roots=("trajectory-root",),
        skill_label_tape_roots=("label-root",),
        probe_tape_roots=("probe-root",),
    )
    with pytest.raises(
        subject.LearnedResourceForecast2048V1Error, match="must be disjoint"
    ):
        subject.validate_disjoint_lane_roots_v1(
            trajectory_tape_roots=("shared-root",),
            skill_label_tape_roots=("shared-root",),
            probe_tape_roots=("probe-root",),
        )

    aligned = subject.aligned_forecast_examples_v1(
        complete_traces[0], player_id="player-a"
    )
    with pytest.raises(
        subject.LearnedResourceForecast2048V1Error, match="exactly cover"
    ):
        subject.validate_forecast_training_examples_v1(
            aligned,
            eligible_player_ids=("player-a", "heldout-player"),
            trajectory_tape_roots=(complete_traces[0].tape_root,),
            target_mode=subject.ALIGNED_TARGET_MODE_V1,
        )
    with pytest.raises(
        subject.LearnedResourceForecast2048V1Error, match="non-trajectory tape"
    ):
        subject.validate_forecast_training_examples_v1(
            aligned,
            eligible_player_ids=("player-a",),
            trajectory_tape_roots=("some-other-root",),
            target_mode=subject.ALIGNED_TARGET_MODE_V1,
        )

    row = aligned[0]
    with pytest.raises(
        subject.LearnedResourceForecast2048V1Error, match="finiteness"
    ):
        subject.ForecastExampleV1(
            key=row.key,
            tokens=row.tokens,
            target=(*row.target[:-1], float("nan")),
            target_source_key=row.target_source_key,
        )


def test_gru_factory_fixed_training_and_frozen_embedding(complete_traces) -> None:
    torch = pytest.importorskip("torch")
    build = subject.forecast_model_factory_v1(torch)
    torch.manual_seed(17)
    left = build()
    torch.manual_seed(17)
    right = build()
    assert all(
        torch.equal(left.state_dict()[key], right.state_dict()[key])
        for key in left.state_dict()
    )
    assert left.encoder.input_size == 21
    assert left.encoder.hidden_size == 64
    assert left.forecast_head.in_features == 64
    assert left.forecast_head.out_features == 54
    assert sum(parameter.numel() for parameter in left.encoder.parameters()) == 16_704
    assert sum(parameter.numel() for parameter in left.parameters()) == 20_214
    assert tuple(left(torch.zeros(2, 8, 21)).shape) == (2, 54)
    with pytest.raises(subject.LearnedResourceForecast2048V1Error):
        left(torch.zeros(2, 9, 21))

    rows = subject.aligned_forecast_examples_v1(
        complete_traces[0], player_id="player-a"
    )[:2]
    global_flags_before = (
        torch.are_deterministic_algorithms_enabled(),
        torch.is_deterministic_algorithms_warn_only_enabled(),
        torch.backends.cudnn.benchmark,
        torch.backends.cudnn.deterministic,
    )
    encoder, receipt = subject.train_forecast_encoder_v1(
        rows,
        eligible_player_ids=("player-a",),
        trajectory_tape_roots=(complete_traces[0].tape_root,),
        ineligible_player_ids=("heldout-player",),
        forbidden_tape_roots=("label-root", "probe-root"),
        target_mode=subject.ALIGNED_TARGET_MODE_V1,
        initialization_seed=29,
        device_name="cpu",
    )
    assert (
        torch.are_deterministic_algorithms_enabled(),
        torch.is_deterministic_algorithms_warn_only_enabled(),
        torch.backends.cudnn.benchmark,
        torch.backends.cudnn.deterministic,
    ) == global_flags_before
    assert encoder.training is False
    assert all(not parameter.requires_grad for parameter in encoder.parameters())
    assert len(receipt.training_loss_by_epoch) == 50
    assert receipt.document()["skill_labels_opened_during_training"] is False
    embeddings = subject.frozen_embeddings_v1(
        encoder, tuple(row.tokens for row in rows)
    )
    assert len(embeddings) == 2
    assert all(len(row) == 64 for row in embeddings)
    assert all(math.isfinite(value) for row in embeddings for value in row)


def test_forecast_training_restores_global_torch_flags_after_failure(
    complete_traces, monkeypatch: pytest.MonkeyPatch
) -> None:
    torch = pytest.importorskip("torch")
    rows = subject.aligned_forecast_examples_v1(
        complete_traces[0], player_id="player-a"
    )[:2]
    global_flags_before = (
        torch.are_deterministic_algorithms_enabled(),
        torch.is_deterministic_algorithms_warn_only_enabled(),
        torch.backends.cudnn.benchmark,
        torch.backends.cudnn.deterministic,
    )

    def fail_loss(*_args, **_kwargs):
        raise RuntimeError("intentional forecast loss failure")

    monkeypatch.setattr(torch.nn.functional, "mse_loss", fail_loss)
    with pytest.raises(RuntimeError, match="intentional forecast loss failure"):
        subject.train_forecast_encoder_v1(
            rows,
            eligible_player_ids=("player-a",),
            trajectory_tape_roots=(complete_traces[0].tape_root,),
            target_mode=subject.ALIGNED_TARGET_MODE_V1,
            initialization_seed=31,
            device_name="cpu",
        )
    assert (
        torch.are_deterministic_algorithms_enabled(),
        torch.is_deterministic_algorithms_warn_only_enabled(),
        torch.backends.cudnn.benchmark,
        torch.backends.cudnn.deterministic,
    ) == global_flags_before


def test_generic_snapshot_loader_and_greedy_selector_support_all_three_arms(
    tmp_path: Path,
) -> None:
    torch = pytest.importorskip("torch")
    raw_path = tmp_path / "raw-16.pt"
    hybrid_path = tmp_path / "hybrid-32.pt"
    raw_model = _network_factory(torch, 16)()
    hybrid_model = _network_factory(torch, 32)()
    for model in (raw_model, hybrid_model):
        for parameter in model.parameters():
            parameter.data.zero_()
    torch.save(raw_model.state_dict(), raw_path)
    torch.save(hybrid_model.state_dict(), hybrid_path)

    state = initial_state_v1(seed="snapshot-selector-test", episode_index=0)
    legal = legal_action_mask_v1(state)
    for arm in HYBRID_CONFIRMATORY_ARMS_V2:
        path = raw_path if arm == RAW_STANDARD_ARM_V2 else hybrid_path
        model = subject.load_generator_policy_snapshot_v1(
            path, arm=arm, device_name="cpu"
        )
        selector = subject.greedy_policy_selector_v1(model, arm=arm)
        action = selector(state, legal)
        assert legal[action]
        assert action == next(index for index, allowed in enumerate(legal) if allowed)

    with pytest.raises(subject.LearnedResourceForecast2048V1Error):
        subject.load_generator_policy_snapshot_v1(
            raw_path,
            arm=HYBRID_CONFIRMATORY_ARMS_V2[1],
            device_name="cpu",
        )
