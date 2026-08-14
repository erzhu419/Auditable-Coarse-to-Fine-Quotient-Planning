"""Producer-free reconstruction of the V43 witness-blind LMB campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
import hashlib
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_lmb_witness_blind_preregistration_v43 as pre
from acfqp.domains.matching_buffer import (
    LMBAction,
    LMBKernel,
    LMBState,
    LMBStatus,
    generate_solvable_lmb,
)
from acfqp.phase3e_ids import canonical_json_bytes, content_id, loads_canonical_json


SCHEMA_VERSION = pre.SCHEMA_VERSION
PROFILE_KEY = "construction_k7_lmb_witness_blind_independent_verification_v43"
EXPECTED_CAMPAIGN_ID = "d435246de035efd4081922b8d6995f1dceb36216bf08cb5766a76ed5dfdbe00d"
EXPECTED_CAMPAIGN_BYTE_COUNT = 459_730
EXPECTED_CAMPAIGN_SHA256 = "918718cef97e62fb4445e346f3e0a30431dcbc945e6eaeb20cc9a7ae7231a443"
EXPECTED_VERIFICATION_ID = "d3e7426521c663ccef51a4da6bb30112c37fc7d37f743050d27942b578a76a51"
EXPECTED_CANONICAL_BYTE_COUNT = 1_930
EXPECTED_CANONICAL_SHA256 = "52572144513eba3befe078738dae99f19c2d1eb405879f311cf6e6d1ff4d114d"
SOURCE_ROOT = Path(__file__).resolve().parents[2]
BOUND_SOURCE_PATHS = (
    "src/acfqp/construction_k7_lmb_witness_blind_preregistration_v43.py",
    "src/acfqp/domains/matching_buffer.py",
)


class ConstructionK7LMBWitnessBlindIndependentVerifierV43Error(ValueError):
    """The V43 bytes fail independent exploration, plan, or identity replay."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7LMBWitnessBlindIndependentVerifierV43Error(message)


def _state(state: LMBState) -> dict[str, Any]:
    return {
        "removed_mask": state.removed_mask,
        "buffer_counts": list(state.buffer),
        "status": state.status.value,
    }


def _action(action: LMBAction) -> dict[str, int]:
    return {"tile": action.tile}


def _model_step(kernel: LMBKernel, state: LMBState, action: LMBAction) -> LMBState:
    removed = state.removed_mask | (1 << action.tile)
    selected = kernel.tile_types[action.tile]
    counts = list(state.buffer)
    counts[selected] += 1
    if counts[selected] == 3:
        counts[selected] = 0
    load = sum(counts)
    empty = removed == (1 << kernel.tile_count) - 1
    status = (
        LMBStatus.FAILURE
        if load > kernel.capacity
        else LMBStatus.SUCCESS
        if empty
        else LMBStatus.ACTIVE
    )
    return LMBState(removed, tuple(counts), status)


def _candidate_step(
    kernel: LMBKernel,
    state: LMBState,
    action: LMBAction,
    candidate: tuple[int, int],
) -> LMBState | None:
    removed = state.removed_mask | (1 << action.tile)
    selected = kernel.tile_types[action.tile]
    counts = list(state.buffer)
    counts[selected] = 0 if counts[selected] == candidate[0] else counts[selected] + 1
    if counts[selected] >= 3:
        return None
    load = sum(counts)
    empty = removed == (1 << kernel.tile_count) - 1
    status = (
        LMBStatus.FAILURE
        if load > kernel.capacity + candidate[1]
        else LMBStatus.SUCCESS
        if empty
        else LMBStatus.ACTIVE
    )
    return LMBState(removed, tuple(counts), status)


def _support(kernel: LMBKernel, state: LMBState, action: LMBAction) -> tuple[int, int, bool]:
    return (
        state.buffer[kernel.tile_types[action.tile]],
        sum(state.buffer),
        sum(state.buffer) == kernel.capacity,
    )


def _context(state: LMBState, action: LMBAction) -> str:
    return content_id(
        pre.FUTURE_DOMAINS["distinction"],
        {"role": "EXACT_CONTEXT", "state": _state(state), "action": _action(action)},
    )


def _prediction_key(value: LMBState | None) -> str:
    return repr(None if value is None else _state(value))


def _expected_proposal() -> tuple[dict[str, Any], set[tuple[int, int, bool]]]:
    surviving = list(pre.CANDIDATES)
    supports: set[tuple[int, int, bool]] = set()
    rows = []
    closures = []
    for seed in pre.SOURCE_SEEDS:
        if len(surviving) == 1:
            break
        kernel, witness = generate_solvable_lmb(seed=seed, **pre.SOURCE_SPEC)
        del witness
        state = kernel.initial_distribution()[0][1]
        start_count = len(surviving)
        labels = 0
        while state.status is LMBStatus.ACTIVE and len(surviving) > 1:
            ranked = []
            for action in kernel.actions(state):
                groups: dict[str, int] = {}
                for candidate in surviving:
                    key = _prediction_key(_candidate_step(kernel, state, action, candidate))
                    groups[key] = groups.get(key, 0) + 1
                score = (
                    len(groups),
                    -max(groups.values()),
                    sum(state.buffer),
                    state.buffer[kernel.tile_types[action.tile]],
                    -action.tile,
                )
                ranked.append((score, action))
            score, action = max(ranked)
            before = len(surviving)
            outcome = kernel.step(state, action)[0]
            surviving = [
                candidate
                for candidate in surviving
                if _candidate_step(kernel, state, action, candidate) == outcome.next_state
            ]
            key = _support(kernel, state, action)
            supports.add(key)
            rows.append(
                {
                    "source_seed": seed,
                    "source_decision_index": labels,
                    "source_state": _state(state),
                    "legal_action_tiles": [candidate.tile for candidate in kernel.actions(state)],
                    "selected_action": _action(action),
                    "exploration_score": list(score),
                    "candidate_count_before": before,
                    "candidate_count_after": len(surviving),
                    "observed_successor": _state(outcome.next_state),
                    "observed_failure": outcome.failure,
                    "observed_terminal": outcome.terminal,
                    "support_key": list(key),
                    "source_generation_witness_accessed": False,
                }
            )
            labels += 1
            state = outcome.next_state
        closures.append(
            {
                "source_seed": seed,
                "candidate_count_at_start": start_count,
                "transition_label_count": labels,
                "terminal_status": state.status.value,
                "candidate_count_at_close": len(surviving),
            }
        )
    if surviving != [(2, 0)]:
        _fail("independent witness-blind policy selected a different program")
    payload = {
        "schema": "acfqp.lmb_witness_blind_proposal.v43",
        "schema_version": SCHEMA_VERSION,
        "preregistration_id": pre.PREREGISTRATION_ID,
        "source_instance_specification": pre.SOURCE_SPEC,
        "initial_candidate_programs": [list(row) for row in pre.CANDIDATES],
        "exploration_score_lexicographic": list(pre.EXPLORATION_SCORE),
        "source_observation_rows": rows,
        "source_episode_closures": closures,
        "source_support_keys": [list(row) for row in sorted(supports)],
        "selected_candidate": [2, 0],
        "compiled_shared_primitives": [
            ["resource_load", ["SUM_VECTOR", "RESOURCE_COUNT_VECTOR"]],
            ["capacity_slack", ["SUBTRACT", "CAPACITY_LIMIT", "resource_load"]],
            ["selected_class_count", ["SELECT_CLASS_COUNT", "RESOURCE_COUNT_VECTOR", "OPERATION_CLASS"]],
            ["rewrite_on_next", ["EQUALS", "selected_class_count", 2]],
            ["post_operation_load", ["REWRITE_OR_INCREMENT", "resource_load", "rewrite_on_next"]],
            ["future_repair_supply", ["COUNT_AVAILABLE_BY_CLASS", "AVAILABLE_OPERATION_SET", "OPERATION_CLASS"]],
        ],
        "offline_source_transition_label_count": len(rows),
        "source_generation_witness_access_count": 0,
        "target_generation_witness_access_count": 0,
        "query_value_reward_or_policy_input_present": False,
        "status": "UNIQUE_WITNESS_BLIND_OBSERVATION_CONSISTENT_PROGRAM",
    }
    return {**payload, "proposal_id": content_id(pre.FUTURE_DOMAINS["proposal"], payload)}, supports


def _plan(kernel: LMBKernel, state: LMBState) -> tuple[tuple[LMBAction, ...], int, int]:
    memo: dict[LMBState, tuple[LMBAction, ...] | None] = {}
    evaluations = 0
    peak = 0

    def solve(current: LMBState) -> tuple[LMBAction, ...] | None:
        nonlocal evaluations, peak
        if current.status is LMBStatus.SUCCESS:
            return ()
        if current.status is LMBStatus.FAILURE:
            return None
        if current in memo:
            return memo[current]
        candidates = []
        for action in kernel.actions(current):
            successor = _model_step(kernel, current, action)
            evaluations += 1
            rewrite = sum(successor.buffer) < sum(current.buffer)
            available = sum(
                1
                for tile in range(kernel.tile_count)
                if not successor.removed_mask & (1 << tile)
                and all(
                    successor.removed_mask & (1 << blocker)
                    for blocker in kernel.blockers[tile]
                )
            )
            candidates.append(
                ((-int(rewrite), sum(successor.buffer), -available, action.tile), action, successor)
            )
        for _rank, action, successor in sorted(candidates):
            suffix = solve(successor)
            if suffix is not None:
                memo[current] = (action, *suffix)
                peak = max(peak, len(memo))
                return memo[current]
        memo[current] = None
        peak = max(peak, len(memo))
        return None

    result = solve(state)
    if result is None:
        _fail("independent abstract planner found no continuation")
    return result, evaluations, peak


def _certificate(
    proposal_id: str,
    arm: str,
    seed: int,
    index: int,
    state: LMBState,
    action: LMBAction,
    support_key: list[Any],
    status: str,
    failed_id: str | None,
) -> dict[str, Any]:
    payload = {
        "schema": "acfqp.lmb_witness_blind_certificate.v43",
        "schema_version": SCHEMA_VERSION,
        "preregistration_id": pre.PREREGISTRATION_ID,
        "proposal_id": proposal_id,
        "arm": arm,
        "episode_seed": seed,
        "decision_index": index,
        "state": _state(state),
        "action": _action(action),
        "support_key": support_key,
        "status": status,
        "failed_certificate_id": failed_id,
        "kernel_step_during_planning": False,
    }
    return {**payload, "certificate_id": content_id(pre.FUTURE_DOMAINS["distinction"], payload)}


def _expected_episode(
    seed: int,
    arm: str,
    proposal_id: str,
    source_supports: set[tuple[int, int, bool]],
) -> dict[str, Any]:
    kernel, witness = generate_solvable_lmb(seed=seed, **pre.TARGET_SPEC)
    del witness
    state = kernel.initial_distribution()[0][1]
    generic_overlay: set[tuple[int, int, bool]] = set()
    context_overlay: set[str] = set()
    decisions = []
    labels = 0
    abstract_compute = 0
    certificate_compute = 0
    peak = 0
    while state.status is LMBStatus.ACTIVE:
        index = len(decisions)
        plan, count, plan_peak = _plan(kernel, state)
        abstract_compute += count
        peak = max(peak, plan_peak)
        action = plan[0]
        predicted = _model_step(kernel, state, action)
        generic_key = _support(kernel, state, action)
        context_key = _context(state, action)
        support_key = list(generic_key) if arm == pre.ARMS[0] else [context_key]
        supported = (
            generic_key in source_supports or generic_key in generic_overlay
            if arm == pre.ARMS[0]
            else context_key in context_overlay
        )
        initial = _certificate(
            proposal_id,
            arm,
            seed,
            index,
            state,
            action,
            support_key,
            "CERTIFIED_MODEL_SUPPORT" if supported else "FAILED_MISSING_SUPPORT",
            None,
        )
        certificate_compute += 1
        distinction = None
        exact = None
        final = initial
        replanned = False
        if not supported:
            exact = kernel.step(state, action)[0]
            labels += 1
            distinction_payload = {
                "schema": "acfqp.lmb_witness_blind_local_distinction.v43",
                "schema_version": SCHEMA_VERSION,
                "preregistration_id": pre.PREREGISTRATION_ID,
                "proposal_id": proposal_id,
                "failed_certificate_id": initial["certificate_id"],
                "arm": arm,
                "episode_seed": seed,
                "decision_index": index,
                "state": _state(state),
                "action": _action(action),
                "support_key": support_key,
                "observed_successor": _state(exact.next_state),
                "observed_failure": exact.failure,
                "observed_terminal": exact.terminal,
                "acquired_after_failed_certificate": True,
            }
            distinction = {
                **distinction_payload,
                "distinction_id": content_id(pre.FUTURE_DOMAINS["distinction"], distinction_payload),
            }
            if arm == pre.ARMS[0]:
                generic_overlay.add(generic_key)
            else:
                context_overlay.add(context_key)
            repeated, count, repeated_peak = _plan(kernel, state)
            abstract_compute += count
            peak = max(peak, repeated_peak)
            if repeated[0] != action:
                _fail("independent post-distinction plan changed")
            replanned = True
            final = _certificate(
                proposal_id,
                arm,
                seed,
                index,
                state,
                action,
                support_key,
                "CERTIFIED_AFTER_LOCAL_DISTINCTION",
                initial["certificate_id"],
            )
            certificate_compute += 1
        outcome = exact or kernel.step(state, action)[0]
        if outcome.next_state != predicted:
            _fail("independent held-out transition differs from world model")
        decisions.append(
            {
                "decision_index": index,
                "source_state": _state(state),
                "plan_prefix": [_action(row) for row in plan[: pre.RECEDING_HORIZON]],
                "selected_action": _action(action),
                "predicted_successor": _state(predicted),
                "initial_certificate": initial,
                "local_distinction": distinction,
                "replanned_after_local_distinction": replanned,
                "final_certificate": final,
                "executed_successor": _state(outcome.next_state),
                "model_matches_execution": True,
            }
        )
        state = outcome.next_state
    payload = {
        "schema": "acfqp.lmb_cross_cardinality_episode.v43",
        "schema_version": SCHEMA_VERSION,
        "preregistration_id": pre.PREREGISTRATION_ID,
        "proposal_id": proposal_id,
        "arm": arm,
        "episode_seed": seed,
        "instance_specification": pre.TARGET_SPEC,
        "decisions": decisions,
        "terminal_state": _state(state),
        "full_board_cleared": True,
        "source_generation_witness_access_count": 0,
        "target_generation_witness_access_count": 0,
        "target_local_distinction_label_count": labels,
        "execution_environment_step_count": len(decisions),
        "abstract_transition_evaluation_count": abstract_compute,
        "certificate_evaluation_count": certificate_compute,
        "peak_dynamic_program_cache_entries": peak,
        "labels_steps_and_compute_separate": True,
    }
    return {**payload, "episode_id": content_id(pre.FUTURE_DOMAINS["episode"], payload)}


def _verify_source_binding(value: Any) -> None:
    expected_facts = []
    for relative in BOUND_SOURCE_PATHS:
        raw = (SOURCE_ROOT / relative).read_bytes()
        expected_facts.append(
            {"relative_path": relative, "byte_count": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
        )
    expected = {
        "schema": "acfqp.lmb_witness_blind_source_binding.v43",
        "preregistration_id": pre.PREREGISTRATION_ID,
        "v42_campaign_id": pre.V42_CAMPAIGN_ID,
        "v42_verification_id": pre.V42_VERIFICATION_ID,
        "source_facts": expected_facts,
        "full_producer_source_closure_claimed": False,
        "producer_free_verification_required": True,
    }
    if value != expected:
        _fail("V43 source binding changed")


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class LMBWitnessBlindIndependentVerificationV43:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    verification_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("V43 verification is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict or canonical_json_bytes(document) != self.canonical_bytes:
            _fail("V43 verification bytes changed")
        payload = {key: value for key, value in document.items() if key != "verification_id"}
        if (
            document.get("verification_id") != self.verification_id
            or content_id(pre.FUTURE_DOMAINS["verification"], payload) != self.verification_id
        ):
            _fail("V43 verification identity changed")

    def to_document(self) -> dict[str, Any]:
        value = loads_canonical_json(self.canonical_bytes)
        if type(value) is not dict:  # pragma: no cover
            raise AssertionError("V43 verification is not an object")
        return value


def independently_verify_lmb_witness_blind_campaign_v43(
    campaign_bytes: bytes,
    output_path: str | Path | None = None,
) -> LMBWitnessBlindIndependentVerificationV43:
    if type(campaign_bytes) is not bytes:
        _fail("V43 campaign input must be exact bytes")
    campaign = loads_canonical_json(campaign_bytes)
    if type(campaign) is not dict or canonical_json_bytes(campaign) != campaign_bytes:
        _fail("V43 campaign is not canonical")
    payload = {key: value for key, value in campaign.items() if key != "campaign_id"}
    campaign_id = content_id(pre.FUTURE_DOMAINS["campaign"], payload)
    if (
        set(campaign)
        != {
            "schema",
            "schema_version",
            "profile_key",
            "preregistration_id",
            "v41_campaign_id",
            "v41_verification_id",
            "v42_campaign_id",
            "v42_verification_id",
            "source_binding",
            "proposal",
            "episodes",
            "summary",
            "verified_scope_candidate",
            "open_ended_operator_invention_claimed",
            "broad_iid_or_cross_domain_sample_efficiency_claimed",
            "total_operational_work_saving_claimed",
            "official_execution_allowed",
            "official_scalar_cost",
            "official_N_break_even",
            "counter_completeness_gate_status",
            "workload_economics_gate_status",
            "campaign_id",
        }
        or campaign["schema"] != "acfqp.lmb_witness_blind_campaign.v43"
        or campaign["schema_version"] != SCHEMA_VERSION
        or campaign["profile_key"] != "construction_k7_lmb_witness_blind_campaign_v43"
        or campaign["preregistration_id"] != pre.PREREGISTRATION_ID
        or campaign["v41_campaign_id"] != pre.V41_CAMPAIGN_ID
        or campaign["v41_verification_id"] != pre.V41_VERIFICATION_ID
        or campaign["v42_campaign_id"] != pre.V42_CAMPAIGN_ID
        or campaign["v42_verification_id"] != pre.V42_VERIFICATION_ID
        or campaign["campaign_id"] != campaign_id
        or campaign["open_ended_operator_invention_claimed"] is not False
        or campaign["broad_iid_or_cross_domain_sample_efficiency_claimed"] is not False
        or campaign["total_operational_work_saving_claimed"] is not False
        or campaign["official_execution_allowed"] is not False
        or campaign["official_scalar_cost"] is not None
        or campaign["official_N_break_even"] is not None
        or campaign["counter_completeness_gate_status"] != "NOT_RUN"
        or campaign["workload_economics_gate_status"] != "NOT_RUN"
    ):
        _fail("V43 campaign schema, identity, or claims changed")
    if EXPECTED_CAMPAIGN_ID != "0" * 64 and (
        campaign_id != EXPECTED_CAMPAIGN_ID
        or len(campaign_bytes) != EXPECTED_CAMPAIGN_BYTE_COUNT
        or hashlib.sha256(campaign_bytes).hexdigest() != EXPECTED_CAMPAIGN_SHA256
    ):
        _fail("V43 campaign differs from frozen evidence")
    _verify_source_binding(campaign["source_binding"])
    proposal, supports = _expected_proposal()
    if campaign["proposal"] != proposal:
        _fail("V43 witness-blind proposal replay changed")
    expected_episodes = [
        _expected_episode(seed, arm, proposal["proposal_id"], supports)
        for arm in pre.ARMS
        for seed in pre.HELDOUT_SEEDS
    ]
    if campaign["episodes"] != expected_episodes:
        _fail("V43 cross-cardinality episode replay changed")
    structural = expected_episodes[: len(pre.HELDOUT_SEEDS)]
    control = expected_episodes[len(pre.HELDOUT_SEEDS) :]
    structural_labels = sum(row["target_local_distinction_label_count"] for row in structural)
    control_labels = sum(row["target_local_distinction_label_count"] for row in control)
    ratio = Fraction(structural_labels, control_labels)
    expected_summary = {
        "offline_source_transition_label_count": proposal["offline_source_transition_label_count"],
        "structural_meta_prior_target_label_count": structural_labels,
        "strict_no_prior_target_label_count": control_labels,
        "target_label_fraction": ratio,
        "heldout_episode_count_per_arm": len(pre.HELDOUT_SEEDS),
        "execution_environment_step_count_per_arm": sum(
            row["execution_environment_step_count"] for row in structural
        ),
        "structural_abstract_compute_events": sum(
            row["abstract_transition_evaluation_count"] + row["certificate_evaluation_count"]
            for row in structural
        ),
        "control_abstract_compute_events": sum(
            row["abstract_transition_evaluation_count"] + row["certificate_evaluation_count"]
            for row in control
        ),
        "all_episodes_completed": True,
        "all_local_labels_follow_failed_certificates": True,
        "source_generation_witness_access_count": 0,
        "target_generation_witness_access_count": 0,
        "planning_kernel_step_count": 0,
        "labels_steps_and_compute_separate": True,
    }
    if campaign["summary"] != expected_summary:
        _fail("V43 matched summary changed")
    verification_payload = {
        "schema": "acfqp.lmb_witness_blind_verification.v43",
        "schema_version": SCHEMA_VERSION,
        "profile_key": PROFILE_KEY,
        "preregistration_id": pre.PREREGISTRATION_ID,
        "campaign_id": campaign_id,
        "campaign_byte_count": len(campaign_bytes),
        "campaign_sha256": hashlib.sha256(campaign_bytes).hexdigest(),
        "proposal_id": proposal["proposal_id"],
        "selected_candidate": proposal["selected_candidate"],
        "offline_source_transition_label_count": proposal[
            "offline_source_transition_label_count"
        ],
        "source_generation_witness_access_count": 0,
        "target_generation_witness_access_count": 0,
        "heldout_episode_count_per_arm": len(pre.HELDOUT_SEEDS),
        "source_tile_count": pre.SOURCE_SPEC["tile_count"],
        "target_tile_count": pre.TARGET_SPEC["tile_count"],
        "source_max_layers": pre.SOURCE_SPEC["max_layers"],
        "target_max_layers": pre.TARGET_SPEC["max_layers"],
        "structural_meta_prior_target_label_count": structural_labels,
        "strict_no_prior_target_label_count": control_labels,
        "target_label_fraction": ratio,
        "execution_environment_step_count_per_arm": expected_summary[
            "execution_environment_step_count_per_arm"
        ],
        "structural_abstract_compute_events": expected_summary[
            "structural_abstract_compute_events"
        ],
        "control_abstract_compute_events": expected_summary[
            "control_abstract_compute_events"
        ],
        "replayed_certificate_count": sum(
            len(episode["decisions"])
            + sum(decision["local_distinction"] is not None for decision in episode["decisions"])
            for episode in expected_episodes
        ),
        "replayed_execution_transition_count": sum(
            len(episode["decisions"]) for episode in expected_episodes
        ),
        "all_episodes_cold_replayed_to_success": True,
        "all_local_labels_follow_failed_certificates": True,
        "planning_kernel_step_count": 0,
        "labels_steps_and_compute_separate": True,
        "verification_imports_campaign_producer": False,
        "verified_claim_scope": "REGISTERED_WITNESS_BLIND_LMB_CROSS_CARDINALITY_WORKLOAD_V43",
        "open_ended_operator_invention_claimed": False,
        "broad_iid_or_cross_domain_sample_efficiency_claimed": False,
        "total_operational_work_saving_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "counter_completeness_gate_status": "NOT_RUN",
        "workload_economics_gate_status": "NOT_RUN",
        "status": "PRODUCER_FREE_WITNESS_BLIND_CROSS_CARDINALITY_VERIFIED",
    }
    verification = {
        **verification_payload,
        "verification_id": content_id(pre.FUTURE_DOMAINS["verification"], verification_payload),
    }
    raw = canonical_json_bytes(verification)
    identity = verification["verification_id"]
    if EXPECTED_VERIFICATION_ID != "0" * 64 and (
        identity != EXPECTED_VERIFICATION_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V43 independent verification changed")
    if output_path is not None:
        Path(output_path).write_bytes(raw)
    return LMBWitnessBlindIndependentVerificationV43(_ISSUER, raw, identity)


__all__ = (
    "EXPECTED_CAMPAIGN_BYTE_COUNT",
    "EXPECTED_CAMPAIGN_ID",
    "EXPECTED_CAMPAIGN_SHA256",
    "EXPECTED_CANONICAL_BYTE_COUNT",
    "EXPECTED_CANONICAL_SHA256",
    "EXPECTED_VERIFICATION_ID",
    "LMBWitnessBlindIndependentVerificationV43",
    "independently_verify_lmb_witness_blind_campaign_v43",
)
