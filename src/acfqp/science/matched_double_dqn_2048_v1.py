"""Matched Double-DQN runtime for latent-resource 2048 campaigns.

Torch, NumPy, and SciPy are experiment-environment dependencies and are
imported only by the runtime.  The repository's formal/accounting modules stay
dependency free.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
import random
import time
from typing import Any, Callable, Mapping, NoReturn

from acfqp.domains.standard_2048 import ACTION_ORDER, GOAL_RANK, Swipe2048Status
from acfqp.science.latent_resource_2048_v1 import (
    STATE_ONLY_RESOURCE_FEATURE_NAMES_V1,
    encode_standard_2048_state_only_state_v1,
)
from acfqp.science.latent_resource_protocol_v1 import (
    ARMS,
    PILOT_ARMS,
    build_pilot_protocol_v1,
    validate_ratified_confirmatory_protocol_v1,
    zero_mask_coordinate_indices_v1,
)
from acfqp.science.matched_2048_env_v1 import (
    initial_state_v1,
    legal_action_mask_v1,
    transition_v1,
)
from acfqp.science.sample_ledger_v1 import (
    EvidenceClass,
    EvidenceLane,
    SampleLedgerV1,
)


NETWORK_PARAMETER_COUNT_V1 = 71_172
PILOT_RESULT_SCHEMA_V1 = "acfqp.science.matched_double_dqn_2048_pilot_result.v1"
CONFIRMATORY_RESULT_SCHEMA_V1 = (
    "acfqp.science.matched_double_dqn_2048_confirmatory_seed_arm_result.v1"
)


class MatchedDoubleDQN2048V1Error(RuntimeError):
    """A pilot configuration, dependency, state, or result is invalid."""


def _fail(message: str) -> NoReturn:
    raise MatchedDoubleDQN2048V1Error(message)


def reward_from_merge_score_v1(merge_score: int) -> float:
    if type(merge_score) is not int or merge_score < 0:
        _fail("merge score must be a nonnegative integer")
    return 0.0 if merge_score == 0 else math.log2(merge_score) / GOAL_RANK


def epsilon_at_interaction_v1(
    interaction: int, *, decay_steps: int, end: float = 0.05
) -> float:
    if (
        type(interaction) is not int
        or interaction < 0
        or type(decay_steps) is not int
        or decay_steps <= 0
        or not 0.0 <= end <= 1.0
    ):
        _fail("epsilon schedule input changed")
    progress = min(interaction, decay_steps) / decay_steps
    return 1.0 + progress * (end - 1.0)


def observation_vector_v1(state, arm: str) -> tuple[float, ...]:
    """Build one registered 16-D observation from the current board only."""

    if arm not in ARMS:
        _fail("arm is not registered")
    if arm == "RAW_BOARD":
        vector = tuple(min(rank, GOAL_RANK) / GOAL_RANK for rank in state.board)
    else:
        encoded = encode_standard_2048_state_only_state_v1(state)
        values = [float(value) for value in encoded.resource_vector]
        for index in zero_mask_coordinate_indices_v1(arm):
            values[index] = 0.0
        vector = tuple(values)
    if len(vector) != 16 or any(not math.isfinite(value) for value in vector):
        _fail("network observation changed")
    return vector


def _timed_observation_v1(state, arm: str) -> tuple[tuple[float, ...], int]:
    started = time.perf_counter_ns()
    observation = observation_vector_v1(state, arm)
    return observation, time.perf_counter_ns() - started


def _sync_device_for_timing(torch, device) -> None:
    if device.type == "cuda":
        torch.cuda.synchronize(device)


@dataclass(slots=True)
class _ReplayBufferV1:
    observations: Any
    actions: Any
    rewards: Any
    next_observations: Any
    dones: Any
    next_masks: Any
    capacity: int
    position: int = 0
    size: int = 0

    @classmethod
    def create(cls, np, capacity: int) -> "_ReplayBufferV1":
        return cls(
            observations=np.empty((capacity, 16), dtype=np.float32),
            actions=np.empty(capacity, dtype=np.int64),
            rewards=np.empty(capacity, dtype=np.float32),
            next_observations=np.empty((capacity, 16), dtype=np.float32),
            dones=np.empty(capacity, dtype=np.float32),
            next_masks=np.empty((capacity, len(ACTION_ORDER)), dtype=np.bool_),
            capacity=capacity,
        )

    def append(
        self,
        observation,
        action: int,
        reward: float,
        next_observation,
        done: bool,
        next_mask,
    ) -> None:
        index = self.position
        self.observations[index] = observation
        self.actions[index] = action
        self.rewards[index] = reward
        self.next_observations[index] = next_observation
        self.dones[index] = float(done)
        self.next_masks[index] = next_mask
        self.position = (index + 1) % self.capacity
        self.size = min(self.size + 1, self.capacity)

    def sample(self, np, rng, batch_size: int) -> tuple[Any, ...]:
        if self.size < batch_size:
            _fail("replay sample requested before warmup")
        indices = rng.integers(0, self.size, size=batch_size)
        return (
            self.observations[indices],
            self.actions[indices],
            self.rewards[indices],
            self.next_observations[indices],
            self.dones[indices],
            self.next_masks[indices],
        )


def _network_factory(torch) -> Callable[[], Any]:
    def build():
        return torch.nn.Sequential(
            torch.nn.Linear(16, 256),
            torch.nn.ReLU(),
            torch.nn.Linear(256, 256),
            torch.nn.ReLU(),
            torch.nn.Linear(256, len(ACTION_ORDER)),
        )

    return build


def _parameter_count(model) -> int:
    return sum(parameter.numel() for parameter in model.parameters())


def _choose_action(
    *,
    torch,
    model,
    device,
    observation: tuple[float, ...],
    legal_mask: tuple[bool, bool, bool, bool],
    epsilon: float,
    epsilon_rng: random.Random,
    action_choice_rng: random.Random,
    ledger: SampleLedgerV1,
    measure_forward_latency: bool,
) -> tuple[int, int, bool]:
    legal_indices = tuple(index for index, allowed in enumerate(legal_mask) if allowed)
    if not legal_indices:
        _fail("active 2048 state has no legal action")
    if epsilon > 0.0 and epsilon_rng.random() < epsilon:
        return (
            legal_indices[action_choice_rng.randrange(len(legal_indices))],
            0,
            False,
        )
    if measure_forward_latency:
        _sync_device_for_timing(torch, device)
    forward_started = time.perf_counter_ns()
    with torch.no_grad():
        values = model(
            torch.tensor(observation, dtype=torch.float32, device=device).unsqueeze(0)
        )[0]
        mask = torch.tensor(legal_mask, dtype=torch.bool, device=device)
        values = values.masked_fill(~mask, float("-inf"))
        action = int(torch.argmax(values).item())
    if measure_forward_latency:
        _sync_device_for_timing(torch, device)
        forward_ns = time.perf_counter_ns() - forward_started
    else:
        forward_ns = 0
    ledger.increment_diagnostic("policy_forward_passes")
    return action, forward_ns, True


def _evaluate_policy_v1(
    *,
    torch,
    model,
    device,
    arm: str,
    tape_root: str,
    checkpoint: int,
    episode_count: int,
    ledger: SampleLedgerV1,
) -> tuple[dict[str, Any], list[tuple[int, ...]], list[tuple[int, ...]]]:
    evaluation_started = time.perf_counter_ns()
    episode_rows: list[dict[str, Any]] = []
    raw_signatures: list[tuple[int, ...]] = []
    resource_signatures: list[tuple[int, ...]] = []
    encoding_calls = 0
    encoding_total_ns = 0
    policy_forward_calls = 0
    policy_forward_total_ns = 0
    decision_total_ns = 0
    epsilon_rng = random.Random(0)
    action_choice_rng = random.Random(1)
    # All checkpoints, seeds, and arms in one protocol face the same held-out tapes.
    for episode_index in range(episode_count):
        state = initial_state_v1(seed=tape_root, episode_index=episode_index)
        total_score = 0
        decisions = 0
        maximum_rank = max(state.board)
        while state.status is Swipe2048Status.ACTIVE:
            if decisions >= 20_000:
                _fail("evaluation episode exceeded the registered decision cap")
            decision_started = time.perf_counter_ns()
            observation, encoding_ns = _timed_observation_v1(state, arm)
            encoding_calls += 1
            encoding_total_ns += encoding_ns
            if arm == "RAW_BOARD":
                raw_signatures.append(state.board)
            else:
                resource_signatures.append(
                    tuple(round(value * 255) for value in observation)
                )
            mask = legal_action_mask_v1(state)
            ledger.charge(
                EvidenceClass.EXACT_KERNEL_QUERY,
                EvidenceLane.STANDALONE_EVALUATION,
            )
            action, forward_ns, forward_executed = _choose_action(
                torch=torch,
                model=model,
                device=device,
                observation=observation,
                legal_mask=mask,
                epsilon=0.0,
                epsilon_rng=epsilon_rng,
                action_choice_rng=action_choice_rng,
                ledger=ledger,
                measure_forward_latency=True,
            )
            if not forward_executed:  # epsilon is zero in held-out evaluation
                raise AssertionError("held-out evaluation skipped a policy forward")
            policy_forward_calls += 1
            policy_forward_total_ns += forward_ns
            decision_total_ns += time.perf_counter_ns() - decision_started
            step = transition_v1(
                state,
                action,
                seed=tape_root,
                episode_index=episode_index,
                decision_index=decisions,
            )
            ledger.charge(
                EvidenceClass.ENVIRONMENT_INTERACTION,
                EvidenceLane.STANDALONE_EVALUATION,
            )
            ledger.increment_diagnostic("simulator_transition_calls")
            total_score += step.merge_score
            decisions += 1
            state = step.next_state
            maximum_rank = max(maximum_rank, max(state.board))
        ledger.increment_diagnostic("evaluation_episodes")
        episode_rows.append(
            {
                "episode_index": episode_index,
                "total_merge_score": total_score,
                "maximum_tile_rank": maximum_rank,
                "decision_count": decisions,
                "won": state.status is Swipe2048Status.WON,
            }
        )
    scores = [row["total_merge_score"] for row in episode_rows]
    evaluation_wall_ns = time.perf_counter_ns() - evaluation_started
    return (
        {
            "checkpoint_environment_interactions": checkpoint,
            "episode_count": episode_count,
            "mean_total_merge_score": sum(scores) / len(scores),
            "tile_2048_win_fraction": sum(row["won"] for row in episode_rows)
            / episode_count,
            "mean_maximum_tile_rank": sum(
                row["maximum_tile_rank"] for row in episode_rows
            )
            / episode_count,
            "mean_episode_decisions": sum(row["decision_count"] for row in episode_rows)
            / episode_count,
            "episodes": episode_rows,
            "compute_telemetry": {
                "wall_time_ns": evaluation_wall_ns,
                "decision_encoding_calls": encoding_calls,
                "decision_encoding_total_ns": encoding_total_ns,
                "decision_encoding_mean_ns": encoding_total_ns / encoding_calls,
                "policy_forward_calls": policy_forward_calls,
                "policy_forward_total_ns": policy_forward_total_ns,
                "policy_forward_mean_ns": policy_forward_total_ns
                / policy_forward_calls,
                "decision_total_ns": decision_total_ns,
                "decision_mean_ns": decision_total_ns / encoding_calls,
            },
        },
        raw_signatures,
        resource_signatures,
    )


def _ratio_v1(value: Mapping[str, Any], *, name: str) -> float:
    if (
        type(value) is not dict
        or type(value.get("numerator")) is not int
        or type(value.get("denominator")) is not int
        or value["denominator"] <= 0
    ):
        _fail(f"{name} ratio changed")
    ratio = value["numerator"] / value["denominator"]
    if not math.isfinite(ratio):
        _fail(f"{name} ratio is not finite")
    return ratio


def _run_seed_arm_v1(
    *,
    protocol: Mapping[str, Any],
    arm: str,
    seed: int,
    device_name: str,
    result_schema: str,
    training_tape_prefix: str,
    result_gate_fields: Mapping[str, Any],
) -> tuple[dict[str, Any], Any]:
    """Run one already-validated protocol seed-arm plus its standalone evaluations."""

    if type(protocol) is not dict:
        _fail("runtime protocol must be a plain object")
    if arm not in protocol["arms"] or seed not in protocol["training_seeds"]:
        _fail("seed-arm is not registered by the runtime protocol")
    if (
        type(result_schema) is not str
        or not result_schema
        or type(training_tape_prefix) is not str
        or not training_tape_prefix
        or type(protocol.get("evaluation_tape_prefix")) is not str
        or not protocol["evaluation_tape_prefix"]
        or type(result_gate_fields) is not dict
    ):
        _fail("runtime protocol execution binding changed")
    try:
        import numpy as np
        import torch
    except ImportError as error:  # pragma: no cover - dependency environment only
        raise MatchedDoubleDQN2048V1Error(
            "NumPy and Torch are required for the Double-DQN runtime"
        ) from error
    if device_name.startswith("cuda") and not torch.cuda.is_available():
        _fail("registered CUDA device is unavailable")
    device = torch.device(device_name)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    epsilon_rng = random.Random(seed)
    action_choice_rng = random.Random(seed + 2_000_000)
    replay_rng = np.random.default_rng(seed + 1_000_000)
    network = _network_factory(torch)
    online = network().to(device)
    target = network().to(device)
    target.load_state_dict(online.state_dict())
    target.eval()
    if _parameter_count(online) != NETWORK_PARAMETER_COUNT_V1:
        _fail("matched network parameter count changed")
    training = protocol["training"]
    learning_rate = _ratio_v1(training["adam_learning_rate"], name="learning rate")
    discount = _ratio_v1(training["discount"], name="discount")
    epsilon_end = _ratio_v1(
        training["epsilon_schedule"]["end"], name="epsilon end"
    )
    huber_delta = training["huber_delta"]
    updates_per_event = training["gradient_updates_per_train_event"]
    if (
        not 0.0 <= discount <= 1.0
        or learning_rate <= 0.0
        or not 0.0 <= epsilon_end <= 1.0
        or type(huber_delta) not in (int, float)
        or not math.isfinite(float(huber_delta))
        or huber_delta <= 0
        or type(updates_per_event) is not int
        or updates_per_event <= 0
    ):
        _fail("runtime optimizer or update contract changed")
    optimizer = torch.optim.Adam(online.parameters(), lr=learning_rate)
    replay = _ReplayBufferV1.create(np, training["replay_capacity"])
    ledger = SampleLedgerV1()
    environment_steps = training["environment_steps_per_seed_arm"]
    warmup = training["replay_warmup_environment_steps"]
    batch_size = training["batch_size"]
    train_every = training["train_every_environment_steps"]
    target_sync = training["target_network_sync_environment_steps"]
    decay_steps = training["epsilon_schedule"]["decay_steps"]
    checkpoints = set(training["evaluation_checkpoints"])
    training_tape_root = f"{training_tape_prefix}:{seed}"
    episode_index = 0
    decision_index = 0
    state = initial_state_v1(seed=training_tape_root, episode_index=episode_index)
    completed_training_episodes: list[dict[str, Any]] = []
    episode_score = 0
    episode_decisions = 0
    evaluation_rows: list[dict[str, Any]] = []
    raw_signature_set: set[tuple[int, ...]] = set()
    resource_signature_set: set[tuple[int, ...]] = set()
    training_decision_encoding_calls = 0
    training_decision_encoding_total_ns = 0
    replay_next_encoding_calls = 0
    replay_next_encoding_total_ns = 0
    training_policy_forward_calls = 0
    optimizer_update_calls = 0
    optimizer_update_total_ns = 0
    standalone_evaluation_wall_ns = 0
    if device.type == "cuda":
        torch.cuda.reset_peak_memory_stats(device)
    wall_started = time.perf_counter_ns()
    for interaction in range(1, environment_steps + 1):
        observation, encoding_ns = _timed_observation_v1(state, arm)
        training_decision_encoding_calls += 1
        training_decision_encoding_total_ns += encoding_ns
        if arm == "RAW_BOARD":
            raw_signature_set.add(state.board)
        else:
            resource_signature_set.add(
                tuple(round(value * 255) for value in observation)
            )
        legal_mask = legal_action_mask_v1(state)
        ledger.charge(
            EvidenceClass.EXACT_KERNEL_QUERY, EvidenceLane.ONLINE_TARGET
        )
        action, _, forward_executed = _choose_action(
            torch=torch,
            model=online,
            device=device,
            observation=observation,
            legal_mask=legal_mask,
            epsilon=epsilon_at_interaction_v1(
                interaction - 1, decay_steps=decay_steps, end=epsilon_end
            ),
            epsilon_rng=epsilon_rng,
            action_choice_rng=action_choice_rng,
            ledger=ledger,
            measure_forward_latency=False,
        )
        training_policy_forward_calls += int(forward_executed)
        step = transition_v1(
            state,
            action,
            seed=training_tape_root,
            episode_index=episode_index,
            decision_index=decision_index,
        )
        ledger.charge(
            EvidenceClass.ENVIRONMENT_INTERACTION, EvidenceLane.ONLINE_TARGET
        )
        ledger.increment_diagnostic("simulator_transition_calls")
        next_state = step.next_state
        next_observation, next_encoding_ns = _timed_observation_v1(next_state, arm)
        replay_next_encoding_calls += 1
        replay_next_encoding_total_ns += next_encoding_ns
        done = step.done
        next_mask = legal_action_mask_v1(next_state)
        ledger.charge(
            EvidenceClass.EXACT_KERNEL_QUERY, EvidenceLane.ONLINE_TARGET
        )
        replay.append(
            observation,
            action,
            reward_from_merge_score_v1(step.merge_score),
            next_observation,
            done,
            next_mask,
        )
        episode_score += step.merge_score
        episode_decisions += 1
        decision_index += 1
        state = next_state
        if interaction >= warmup and interaction % train_every == 0:
            for _ in range(updates_per_event):
                _sync_device_for_timing(torch, device)
                update_started = time.perf_counter_ns()
                batch = replay.sample(np, replay_rng, batch_size)
                observations = torch.as_tensor(batch[0], device=device)
                actions = torch.as_tensor(batch[1], device=device)
                rewards = torch.as_tensor(batch[2], device=device)
                next_observations = torch.as_tensor(batch[3], device=device)
                dones = torch.as_tensor(batch[4], device=device)
                next_masks = torch.as_tensor(batch[5], device=device)
                q_values = online(observations).gather(
                    1, actions.unsqueeze(1)
                ).squeeze(1)
                with torch.no_grad():
                    online_next = online(next_observations).masked_fill(
                        ~next_masks, float("-inf")
                    )
                    no_next = ~next_masks.any(dim=1)
                    next_actions = online_next.argmax(dim=1)
                    target_next = target(next_observations).gather(
                        1, next_actions.unsqueeze(1)
                    ).squeeze(1)
                    target_next = target_next.masked_fill(no_next, 0.0)
                    targets = rewards + discount * (1.0 - dones) * target_next
                loss = torch.nn.functional.smooth_l1_loss(
                    q_values, targets, beta=float(huber_delta)
                )
                optimizer.zero_grad(set_to_none=True)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(online.parameters(), 10.0)
                optimizer.step()
                _sync_device_for_timing(torch, device)
                optimizer_update_total_ns += time.perf_counter_ns() - update_started
                optimizer_update_calls += 1
                ledger.increment_diagnostic("gradient_updates")
                ledger.increment_diagnostic("replay_buffer_draws", batch_size)
        if interaction % target_sync == 0:
            target.load_state_dict(online.state_dict())
            ledger.increment_diagnostic("target_network_syncs")
        if done:
            completed_training_episodes.append(
                {
                    "episode_index": episode_index,
                    "total_merge_score": episode_score,
                    "decision_count": episode_decisions,
                    "terminal_status": state.status.value,
                    "maximum_tile_rank": max(state.board),
                }
            )
            ledger.increment_diagnostic("training_episodes")
            episode_index += 1
            decision_index = 0
            episode_score = 0
            episode_decisions = 0
            state = initial_state_v1(
                seed=training_tape_root, episode_index=episode_index
            )
        if interaction in checkpoints:
            evaluation, raw_rows, resource_rows = _evaluate_policy_v1(
                torch=torch,
                model=online,
                device=device,
                arm=arm,
                tape_root=protocol["evaluation_tape_prefix"],
                checkpoint=interaction,
                episode_count=training["evaluation_episodes_per_checkpoint"],
                ledger=ledger,
            )
            evaluation_rows.append(evaluation)
            standalone_evaluation_wall_ns += evaluation["compute_telemetry"][
                "wall_time_ns"
            ]
            raw_signature_set.update(raw_rows)
            resource_signature_set.update(resource_rows)
    if device.type == "cuda":
        torch.cuda.synchronize(device)
    total_wall_ns = time.perf_counter_ns() - wall_started
    training_wall_ns = total_wall_ns - standalone_evaluation_wall_ns
    if training_wall_ns < 0:
        raise AssertionError("evaluation wall time exceeded total run wall time")
    peak_device_memory_bytes = (
        int(torch.cuda.max_memory_allocated(device)) if device.type == "cuda" else 0
    )
    evaluation_decision_calls = sum(
        row["compute_telemetry"]["decision_encoding_calls"]
        for row in evaluation_rows
    )
    evaluation_decision_total_ns = sum(
        row["compute_telemetry"]["decision_total_ns"] for row in evaluation_rows
    )
    zero_mask_indices = zero_mask_coordinate_indices_v1(arm)
    representation_telemetry = {
        "active_representation": arm,
        "executed_arm": arm,
        "input_dimension": 16,
        "raw_observation_bytes": 64,
        "arm_observation_bytes": 64,
        "lossless_raw_board_signature_count": len(raw_signature_set),
        "quantized_state_only_resource_signature_count": len(
            resource_signature_set
        ),
        "resource_quantization_bins_per_coordinate": 256,
        "equal_dimension_is_not_counted_as_compression": True,
        "compression_claimed": False,
    }
    if result_schema == CONFIRMATORY_RESULT_SCHEMA_V1:
        representation_telemetry.update(
            {
                "zero_mask_coordinate_indices": list(zero_mask_indices),
                "zero_mask_coordinate_names": [
                    STATE_ONLY_RESOURCE_FEATURE_NAMES_V1[index]
                    for index in zero_mask_indices
                ],
                "zero_mask_applied_after_full_state_only_encoding": arm
                not in PILOT_ARMS,
            }
        )
    result = {
        "schema": result_schema,
        "protocol_id": protocol["protocol_id"],
        "campaign_kind": protocol["campaign_kind"],
        "arm": arm,
        "seed": seed,
        "device": str(device),
        "network_parameter_count": _parameter_count(online),
        "training_environment_interactions": environment_steps,
        "completed_training_episode_count": len(completed_training_episodes),
        "completed_training_episodes": completed_training_episodes,
        "unfinished_training_episode": {
            "episode_index": episode_index,
            "score_so_far": episode_score,
            "decisions_so_far": episode_decisions,
        },
        "evaluations": evaluation_rows,
        "representation_telemetry": representation_telemetry,
        "sample_ledger": ledger.to_document(),
        "decision_latency_telemetry": {
            "lane": EvidenceLane.STANDALONE_EVALUATION.value,
            "decision_count": evaluation_decision_calls,
            "total_decision_latency_ns": evaluation_decision_total_ns,
            "mean_decision_latency_ns": evaluation_decision_total_ns
            / evaluation_decision_calls,
            "includes_state_only_encoding_action_mask_and_policy_forward": True,
        },
        "compute_telemetry": {
            "wall_time_ns": total_wall_ns,
            "total_wall_time_ns": total_wall_ns,
            "training_wall_time_excluding_standalone_evaluation_ns": training_wall_ns,
            "standalone_evaluation_wall_time_ns": standalone_evaluation_wall_ns,
            "training_decision_encoding_calls": training_decision_encoding_calls,
            "training_decision_encoding_total_ns": training_decision_encoding_total_ns,
            "training_decision_encoding_mean_ns": training_decision_encoding_total_ns
            / training_decision_encoding_calls,
            "replay_next_encoding_calls": replay_next_encoding_calls,
            "replay_next_encoding_total_ns": replay_next_encoding_total_ns,
            "replay_next_encoding_mean_ns": replay_next_encoding_total_ns
            / replay_next_encoding_calls,
            "training_policy_forward_calls": training_policy_forward_calls,
            "optimizer_update_calls": optimizer_update_calls,
            "gradient_updates": optimizer_update_calls,
            "replay_buffer_draws": optimizer_update_calls * batch_size,
            "optimizer_network_forward_passes": optimizer_update_calls * 3,
            "optimizer_update_total_ns": optimizer_update_total_ns,
            "optimizer_update_mean_ns": optimizer_update_total_ns
            / optimizer_update_calls,
            "peak_device_memory_bytes": peak_device_memory_bytes,
            "device_latency_measured_with_synchronization": device.type == "cuda",
        },
    }
    result.update(result_gate_fields)
    return result, online


def run_pilot_seed_arm_v1(
    *, arm: str, seed: int, device_name: str = "cuda:0"
) -> tuple[dict[str, Any], Any]:
    """Run one preregistered pilot seed-arm with its unchanged result contract."""

    protocol = build_pilot_protocol_v1()
    return _run_seed_arm_v1(
        protocol=protocol,
        arm=arm,
        seed=seed,
        device_name=device_name,
        result_schema=PILOT_RESULT_SCHEMA_V1,
        training_tape_prefix="pilot-train",
        result_gate_fields={
            "pilot_scientific_gate": "NOT_RUN",
            "scientific_success_claimed": False,
        },
    )


def run_confirmatory_seed_arm_v1(
    *,
    protocol: Mapping[str, Any],
    arm: str,
    seed: int,
    device_name: str = "cuda:0",
) -> tuple[dict[str, Any], Any]:
    """Run one seed-arm from an exactly ratified confirmatory protocol."""

    validated = validate_ratified_confirmatory_protocol_v1(protocol)
    return _run_seed_arm_v1(
        protocol=validated,
        arm=arm,
        seed=seed,
        device_name=device_name,
        result_schema=CONFIRMATORY_RESULT_SCHEMA_V1,
        training_tape_prefix=validated["training_tape_prefix"],
        result_gate_fields={
            "confirmatory_joint_gate": "NOT_RUN_REQUIRES_COMPLETE_40_ARTIFACT_MATRIX",
            "scientific_success_claimed": False,
        },
    )


__all__ = (
    "CONFIRMATORY_RESULT_SCHEMA_V1",
    "MatchedDoubleDQN2048V1Error",
    "NETWORK_PARAMETER_COUNT_V1",
    "PILOT_ARMS",
    "PILOT_RESULT_SCHEMA_V1",
    "epsilon_at_interaction_v1",
    "observation_vector_v1",
    "reward_from_merge_score_v1",
    "run_confirmatory_seed_arm_v1",
    "run_pilot_seed_arm_v1",
)
