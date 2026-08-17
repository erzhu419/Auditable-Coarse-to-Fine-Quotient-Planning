"""V55 adaptive layout/program/factor/residual campaign construction core."""

from __future__ import annotations

from collections import deque
from concurrent.futures import ProcessPoolExecutor
from functools import lru_cache
import hashlib
import heapq
import random
from typing import Any, Iterator, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v55 as domains_v55
from acfqp.domains.stochastic_balanced_batch_refinement import (
    generate_stochastic_balanced_batch_refinement,
)
from acfqp.domains.stochastic_batch_refinement import (
    BatchRefinementAction,
    BatchRefinementState,
    BatchRefinementStatus,
    select_seeded_batch_refinement_outcome_v1,
)
from acfqp.generic_adaptive_joint_factor_residual_synthesizer_v10 import (
    AdaptiveJointCandidateV10,
    adaptive_stop_update_v10,
    exact_candidate_replay_v10,
    synthesize_adaptive_joint_candidate_v10,
)
from acfqp.generic_atomic_expression_world_model_v4 import (
    FlatRawActionV4,
    FlatRawTransitionV4,
    GenericAtomicExpressionWorldModelV4Error,
    execute_generic_atomic_support_v4,
    missing_relation_values_v4,
    plan_generic_atomic_program_v4,
)
from acfqp.generic_joint_factor_residual_world_model_v9 import (
    synthesize_joint_factor_residual_world_model_v9,
)
from acfqp.generic_layout_factorized_world_model_v5 import (
    align_generic_occurrence_v5,
)
from acfqp.phase3e_ids import canonical_json_bytes


class AdaptiveJointFactorResidualCampaignCoreV55Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise AdaptiveJointFactorResidualCampaignCoreV55Error(message)


def _interface(seed: int, kernel: Any, tokens: Mapping[str, int]):
    state_order = list(range(6))
    action_order = list(range(5))
    random.Random(seed ^ 0x55A17).shuffle(state_order)
    random.Random(seed ^ 0x55B29).shuffle(action_order)
    catalogue = tuple(
        FlatRawActionV4(
            key,
            tuple(
                (
                    rule.source_stage,
                    rule.anonymous_advance_class,
                    rule.unit_increment,
                    rule.risk_increment,
                    1,
                )[index]
                for index in action_order
            ),
        )
        for key, rule in enumerate(kernel.rules)
    )

    def encode(state: BatchRefinementState) -> tuple[int, ...]:
        status = tokens[
            "A"
            if state.status is BatchRefinementStatus.ACTIVE
            else "S"
            if state.status is BatchRefinementStatus.SUCCESS
            else "F"
        ]
        semantic = (
            state.stage,
            state.units,
            state.risk,
            status,
            kernel.risk_capacity,
            kernel.goal_stage,
        )
        return tuple(semantic[index] for index in state_order)

    return catalogue, encode


def _transition_batch(
    kernel: Any,
    catalogue: tuple[FlatRawActionV4, ...],
    encode: Any,
    state: BatchRefinementState,
    action: BatchRefinementAction,
    index: int,
) -> tuple[FlatRawTransitionV4, ...]:
    legal = tuple(kernel.actions(state))
    if action not in legal:
        _fail("V55 attempted a ground query for an illegal action")
    rows = []
    for offset, outcome in enumerate(kernel.step(state, action)):
        successor = outcome.next_state
        legal_after = tuple(kernel.actions(successor))
        rows.append(
            FlatRawTransitionV4(
                0,
                index + offset,
                encode(state),
                tuple(row.rule for row in legal),
                catalogue[action.rule],
                encode(successor),
                tuple(row.rule for row in legal_after),
                None
                if legal_after
                else successor.status is BatchRefinementStatus.SUCCESS,
            )
        )
    return tuple(rows)


def _witness_blind_depth_frontier(
    kernel: Any,
    catalogue: tuple[FlatRawActionV4, ...],
    encode: Any,
) -> Iterator[tuple[FlatRawTransitionV4, ...]]:
    initial = kernel.initial_distribution()[0][1]
    frontier: list[tuple[int, int, BatchRefinementState]] = [(0, 0, initial)]
    seen = {initial}
    insertion = 1
    pending: deque[
        tuple[BatchRefinementState, tuple[BatchRefinementAction, ...], BatchRefinementAction, int]
    ] = deque()
    transition_index = 0
    while frontier or pending:
        if not pending:
            negative_depth, _ordinal, state = heapq.heappop(frontier)
            depth = -negative_depth
            legal = tuple(kernel.actions(state))
            pending.extend((state, legal, action, depth) for action in legal)
        state, _legal, action, depth = pending.popleft()
        batch = _transition_batch(
            kernel, catalogue, encode, state, action, transition_index
        )
        transition_index += len(batch)
        for row, outcome in zip(batch, kernel.step(state, action), strict=True):
            successor = outcome.next_state
            if (
                row.terminal_acceptance_after is None
                and successor not in seen
            ):
                seen.add(successor)
                heapq.heappush(frontier, (-(depth + 1), insertion, successor))
                insertion += 1
        yield batch


def _raw_sha(rows: tuple[FlatRawTransitionV4, ...]) -> str:
    return hashlib.sha256(
        canonical_json_bytes([row.to_document() for row in rows])
    ).hexdigest()


def _candidate(
    rows: tuple[FlatRawTransitionV4, ...],
    catalogue: tuple[FlatRawActionV4, ...],
    factor_library: Mapping[str, Any],
    labels: int,
    config: Mapping[str, Any],
) -> AdaptiveJointCandidateV10:
    return synthesize_adaptive_joint_candidate_v10(
        rows,
        catalogue,
        factor_library,
        support_label_count=labels,
        generic_domains=config["generic_domains"],
        candidate_domain=config["domains"]["candidate"],
        candidate_content_id=domains_v55.extension_content_id_v55,
        minimum_reusable_factor_count=config["minimum_reusable_factor_count"],
    )


def _acquire(
    *,
    seed: int,
    factor_prior_enabled: bool,
    kernel: Any,
    catalogue: tuple[FlatRawActionV4, ...],
    encode: Any,
    factor_library: Mapping[str, Any],
    config: Mapping[str, Any],
) -> dict[str, Any]:
    rows: list[FlatRawTransitionV4] = []
    batches: list[tuple[FlatRawTransitionV4, ...]] = []
    candidate = None
    candidate_issued_at = None
    resets = 0
    history = []
    generator = _witness_blind_depth_frontier(kernel, catalogue, encode)
    for labels in range(1, config["maximum_acquisition_labels"] + 1):
        try:
            batch = next(generator)
        except StopIteration:
            _fail("V55 witness-blind frontier exhausted before stopping")
        rows.extend(batch)
        batches.append(batch)
        if labels < config["minimum_candidate_labels"]:
            continue
        reason = "EXISTING_CANDIDATE_EXACT_REPLAY"
        replay = None
        if candidate is None:
            try:
                candidate = _candidate(
                    tuple(rows), catalogue, factor_library, labels, config
                )
            except Exception:
                continue
            candidate_issued_at = labels
            reason = "FIRST_JOINT_CANDIDATE_SYNTHESIZED"
        else:
            replay = exact_candidate_replay_v10(
                candidate, tuple(rows), catalogue
            )
            if replay["exact"] is not True:
                candidate = _candidate(
                    tuple(rows), catalogue, factor_library, labels, config
                )
                candidate_issued_at = labels
                resets += 1
                reason = "COUNTEREVIDENCE_TRIGGERED_FULL_JOINT_RESYNTHESIS"
        if candidate_issued_at is None:  # pragma: no cover
            raise AssertionError
        stop = adaptive_stop_update_v10(
            candidate,
            factor_prior_enabled=factor_prior_enabled,
            confirming_support_labels=labels - candidate_issued_at,
            confirmation_block_size=config["confirmation_block_size"],
            factor_prior_weight=config["factor_prior_weight"],
            exact_likelihood_block_weight=config[
                "exact_likelihood_block_weight"
            ],
            stopping_weight=config["stopping_weight"],
            minimum_reusable_factor_count=config[
                "minimum_reusable_factor_count"
            ],
        )
        history.append(
            {
                "support_label_count": labels,
                "raw_transition_sha256": _raw_sha(tuple(rows)),
                "candidate_id": candidate.public_document["candidate_id"],
                "update_reason": reason,
                "exact_replay": replay,
                "stop_update": stop,
            }
        )
        if stop["stopped"] is not True:
            continue
        arm = (
            "ANONYMOUS_FACTOR_PRIOR_ON"
            if factor_prior_enabled
            else "STRICT_NO_PRIOR"
        )
        payload = {
            "schema": "acfqp.adaptive_joint_acquisition.v55",
            "seed": seed,
            "arm": arm,
            "factor_prior_enabled": factor_prior_enabled,
            "ground_support_labels": labels,
            "raw_transition_count": len(rows),
            "raw_transition_sha256": _raw_sha(tuple(rows)),
            "candidate": dict(candidate.public_document),
            "candidate_issued_at_support_label": candidate_issued_at,
            "candidate_reset_count": resets,
            "stopping_history": history,
            "witness_blind_depth_first_frontier_policy": True,
            "generation_witness_accessed": False,
            "full_frontier_calibration_consumed": False,
            "same_synthesizer_query_order_exact_likelihood_and_stop_formula": True,
            "only_switched_variable": "ANONYMOUS_FACTOR_SIGNATURE_INITIAL_WEIGHT",
        }
        document = {
            **payload,
            "acquisition_id": domains_v55.extension_content_id_v55(
                config["domains"]["acquisition"], payload
            ),
        }
        return {
            "document": document,
            "candidate": candidate,
            "rows": tuple(rows),
            "batches": tuple(batches),
        }
    _fail("V55 acquisition crossed its registered label cap")


def _relations(program: Mapping[str, Any]) -> dict[str, list[list[int]]]:
    encoded = canonical_json_bytes(
        [row["expression"] for row in program["compiled_assignments"]]
    ).decode("utf-8")
    return {
        name: values
        for name, values in program["occurrence_bindings"][0]["relations"].items()
        if f'"{name}"' in encoded
    }


def _relation_fields(program: Mapping[str, Any]) -> dict[str, int]:
    result: dict[str, int] = {}

    def visit(expression: Any) -> None:
        if type(expression) is not list:
            return
        if (
            len(expression) >= 3
            and expression[0] == "E04"
            and type(expression[2]) is list
            and expression[2][:1] == ["E01"]
        ):
            result[expression[1]] = expression[2][1]
        for item in expression:
            visit(item)

    for assignment in program["compiled_assignments"]:
        visit(assignment["expression"])
    return result


def _candidate_cap(state: tuple[int, ...], name: str, maximum: int) -> int:
    suffix = name.rsplit("_", 1)[-1]
    if suffix.isascii() and suffix.isdigit():
        column = int(suffix)
        if 0 <= column < len(state) and state[column] > 0:
            return min(maximum, state[column] - 1)
    return maximum


def _recover_relation(
    program: Mapping[str, Any],
    binding: Mapping[str, Any],
    state: tuple[int, ...],
    action: FlatRawActionV4,
    actual: set[tuple[int, ...]],
    name: str,
    relation_input: int,
    overlay: Mapping[str, Mapping[int, int]],
    maximum: int,
) -> int:
    matches = []
    for value in range(_candidate_cap(state, name, maximum) + 1):
        trial = {key: dict(rows) for key, rows in overlay.items()}
        trial.setdefault(name, {})[relation_input] = value
        try:
            predicted = set(
                execute_generic_atomic_support_v4(
                    program,
                    state,
                    action,
                    binding,
                    relation_overlay=trial,
                )
            )
        except (GenericAtomicExpressionWorldModelV4Error, ZeroDivisionError):
            continue
        if predicted == actual:
            matches.append(value)
    if len(matches) != 1:
        _fail("V55 local relation recovery was not unique")
    return matches[0]


def _certificate(
    *,
    seed: int,
    arm: str,
    episode_index: int,
    decision_index: int,
    program_id: str,
    kind: str,
    detail: Mapping[str, Any],
    config: Mapping[str, Any],
) -> dict[str, Any]:
    payload = {
        "schema": "acfqp.adaptive_joint_failed_certificate.v55",
        "seed": seed,
        "arm": arm,
        "episode_index": episode_index,
        "decision_index": decision_index,
        "program_id": program_id,
        "failure_kind": kind,
        "failure_detail": dict(detail),
        "ground_query_performed_before_failure": False,
    }
    return {
        **payload,
        "failed_certificate_id": domains_v55.extension_content_id_v55(
            config["domains"]["failed_certificate"], payload
        ),
    }


def _distinction(
    failure: Mapping[str, Any],
    kind: str,
    detail: Mapping[str, Any],
    labels: int,
    config: Mapping[str, Any],
) -> dict[str, Any]:
    payload = {
        "schema": "acfqp.adaptive_joint_local_distinction.v55",
        "failed_certificate_id": failure["failed_certificate_id"],
        "distinction_kind": kind,
        "distinction_detail": dict(detail),
        "query_after_failed_certificate": True,
        "ground_support_labels": labels,
    }
    return {
        **payload,
        "local_distinction_id": domains_v55.extension_content_id_v55(
            config["domains"]["distinction"], payload
        ),
    }


def _episode(
    *,
    seed: int,
    arm: str,
    episode_index: int,
    acquisition: Mapping[str, Any],
    kernel: Any,
    catalogue: tuple[FlatRawActionV4, ...],
    encode: Any,
    factor_library: Mapping[str, Any],
    config: Mapping[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    candidate = acquisition["candidate"]
    evidence_rows = list(acquisition["rows"])
    covered = {(row.pre, row.action.key) for row in evidence_rows}
    failures = []
    distinctions = []
    overlay: dict[str, dict[int, int]] = {}
    actions = []
    tapes = []
    planning_compute = 0
    peak_cache = 0
    local_labels = 0
    resynthesis_count = 0
    state = kernel.initial_distribution()[0][1]
    decision = 0
    recovery_attempts = 0
    initial_candidate_id = candidate.public_document["candidate_id"]
    while state.status is BatchRefinementStatus.ACTIVE:
        program = candidate.program
        layout = candidate.layout
        _aligned_rows, aligned_catalogue = align_generic_occurrence_v5(
            tuple(evidence_rows), catalogue, layout, canonical_occurrence=0
        )
        binding = program["occurrence_bindings"][0]
        raw_state = encode(state)
        canonical_state = tuple(
            raw_state[index] for index in layout.state_canonical_to_raw
        )
        relation_fields = _relation_fields(program)
        missing = sorted(
            {
                item
                for action in aligned_catalogue
                for item in missing_relation_values_v4(
                    program,
                    action,
                    binding,
                    relation_overlay=overlay,
                )
            }
        )
        for name, relation_input in missing:
            failure = _certificate(
                seed=seed,
                arm=arm,
                episode_index=episode_index,
                decision_index=decision,
                program_id=program["program_id"],
                kind="MISSING_COMPILED_RELATION_SUPPORT",
                detail={"relation_name": name, "relation_input": relation_input},
                config=config,
            )
            failures.append(failure)
            field = relation_fields[name]
            aligned_action = next(
                row
                for row in aligned_catalogue
                if row.fields[field] == relation_input
            )
            rule = kernel.rules[aligned_action.key]
            probe = BatchRefinementState(
                rule.source_stage, 0, 0, 0, BatchRefinementStatus.ACTIVE
            )
            raw_probe = encode(probe)
            canonical_probe = tuple(
                raw_probe[index] for index in layout.state_canonical_to_raw
            )
            actual = {
                tuple(
                    encode(outcome.next_state)[index]
                    for index in layout.state_canonical_to_raw
                )
                for outcome in kernel.step(
                    probe, BatchRefinementAction(aligned_action.key)
                )
            }
            value = _recover_relation(
                program,
                binding,
                canonical_probe,
                aligned_action,
                actual,
                name,
                relation_input,
                overlay,
                config["maximum_relation_output_candidate"],
            )
            overlay.setdefault(name, {})[relation_input] = value
            distinctions.append(
                _distinction(
                    failure,
                    "RELATION_OUTPUT_RECOVERED",
                    {
                        "relation_name": name,
                        "relation_input": relation_input,
                        "relation_output": value,
                    },
                    1,
                    config,
                )
            )
            local_labels += 1
        try:
            plan, evaluations, cache_size = plan_generic_atomic_program_v4(
                program,
                canonical_state,
                aligned_catalogue,
                binding,
                relation_overlay=overlay,
            )
        except Exception as error:
            _fail(
                f"V55 abstract planner failed at seed {seed} arm {arm}: "
                f"{type(error).__name__}: {error}"
            )
        key = plan[0]
        planning_compute += evaluations
        peak_cache = max(peak_cache, cache_size)
        pair = (raw_state, key)
        if pair not in covered:
            failure = _certificate(
                seed=seed,
                arm=arm,
                episode_index=episode_index,
                decision_index=decision,
                program_id=program["program_id"],
                kind="MISSING_QUERY_LOCAL_STATE_ACTION_SUPPORT",
                detail={"raw_state": list(raw_state), "action_key": key},
                config=config,
            )
            failures.append(failure)
            batch = _transition_batch(
                kernel,
                catalogue,
                encode,
                state,
                BatchRefinementAction(key),
                len(evidence_rows),
            )
            local_labels += 1
            aligned_batch, _ = align_generic_occurrence_v5(
                batch, catalogue, layout, canonical_occurrence=0
            )
            actual = {row.post for row in aligned_batch}
            aligned_action = next(row for row in aligned_catalogue if row.key == key)
            try:
                predicted = set(
                    execute_generic_atomic_support_v4(
                        program,
                        canonical_state,
                        aligned_action,
                        binding,
                        relation_overlay=overlay,
                    )
                )
            except Exception:
                predicted = set()
            evidence_rows.extend(batch)
            covered.add(pair)
            if predicted != actual:
                recovery_attempts += 1
                if recovery_attempts > config["maximum_local_resyntheses"]:
                    _fail("V55 crossed its local resynthesis cap")
                candidate = _candidate(
                    tuple(evidence_rows),
                    catalogue,
                    factor_library,
                    acquisition["document"]["ground_support_labels"]
                    + local_labels,
                    config,
                )
                overlay = {}
                resynthesis_count += 1
                distinctions.append(
                    _distinction(
                        failure,
                        "QUERY_LOCAL_COUNTEREXAMPLE_RESYNTHESIZED_PROGRAM",
                        {
                            "predicted_support": [list(row) for row in sorted(predicted)],
                            "actual_support": [list(row) for row in sorted(actual)],
                            "successor_candidate_id": candidate.public_document[
                                "candidate_id"
                            ],
                        },
                        1,
                        config,
                    )
                )
                continue
            distinctions.append(
                _distinction(
                    failure,
                    "QUERY_LOCAL_SUPPORT_CONFIRMED_WITHOUT_PROGRAM_CHANGE",
                    {"action_key": key, "support_cardinality": len(actual)},
                    1,
                    config,
                )
            )
        outcome, tape = select_seeded_batch_refinement_outcome_v1(
            kernel.step(state, BatchRefinementAction(key)),
            seed=seed,
            episode_index=episode_index,
            decision_index=decision,
        )
        state = outcome.next_state
        actions.append(key)
        tapes.append(tape)
        decision += 1
    payload = {
        "schema": "acfqp.adaptive_joint_receding_episode.v55",
        "seed": seed,
        "arm": arm,
        "initial_candidate_id": initial_candidate_id,
        "final_candidate_id": candidate.public_document["candidate_id"],
        "action_keys": actions,
        "outcome_tape_sha256": tapes,
        "execution_steps": len(actions),
        "planning_compute_events": planning_compute,
        "peak_planning_cache_entries": peak_cache,
        "local_ground_support_labels": local_labels,
        "failed_certificate_count": len(failures),
        "local_program_resynthesis_count": resynthesis_count,
        "all_ground_queries_followed_failed_certificates": (
            local_labels == sum(row["ground_support_labels"] for row in distinctions)
            and len(failures) == len(distinctions)
        ),
        "success": state.status is BatchRefinementStatus.SUCCESS,
    }
    return (
        {
            **payload,
            "episode_id": domains_v55.extension_content_id_v55(
                config["domains"]["episode"], payload
            ),
        },
        failures,
        distinctions,
    )


def _strict_choice(kernel: Any, state: BatchRefinementState, cache: dict) -> tuple[int, int, int]:
    choices = {}
    labels = 0

    @lru_cache(maxsize=None)
    def solve(current: BatchRefinementState) -> bool:
        nonlocal labels
        if current.status is BatchRefinementStatus.SUCCESS:
            return True
        if current.status is BatchRefinementStatus.FAILURE:
            return False
        for action in kernel.actions(current):
            key = (current, action.rule)
            if key not in cache:
                cache[key] = tuple(row.next_state for row in kernel.step(current, action))
                labels += 1
            if all(solve(successor) for successor in cache[key]):
                choices[current] = action.rule
                return True
        return False

    if not solve(state) or state not in choices:
        _fail("V55 strict planner found no robust continuation")
    return choices[state], solve.cache_info().currsize, labels


def _strict_episode(seed: int, episode_index: int, kernel: Any, config: Mapping[str, Any]) -> dict[str, Any]:
    state = kernel.initial_distribution()[0][1]
    cache = {}
    actions = []
    tapes = []
    planning = 0
    peak = 0
    labels = 0
    decision = 0
    while state.status is BatchRefinementStatus.ACTIVE:
        key, compute, new_labels = _strict_choice(kernel, state, cache)
        outcome, tape = select_seeded_batch_refinement_outcome_v1(
            kernel.step(state, BatchRefinementAction(key)),
            seed=seed,
            episode_index=episode_index,
            decision_index=decision,
        )
        state = outcome.next_state
        actions.append(key)
        tapes.append(tape)
        planning += compute
        peak = max(peak, compute)
        labels += new_labels
        decision += 1
    payload = {
        "schema": "acfqp.adaptive_joint_receding_episode.v55",
        "seed": seed,
        "arm": "STRICT_EXACT_CONTEXT",
        "initial_candidate_id": None,
        "final_candidate_id": None,
        "action_keys": actions,
        "outcome_tape_sha256": tapes,
        "execution_steps": len(actions),
        "planning_compute_events": planning,
        "peak_planning_cache_entries": peak,
        "local_ground_support_labels": labels,
        "failed_certificate_count": 0,
        "local_program_resynthesis_count": 0,
        "all_ground_queries_followed_failed_certificates": True,
        "success": state.status is BatchRefinementStatus.SUCCESS,
    }
    return {
        **payload,
        "episode_id": domains_v55.extension_content_id_v55(
            config["domains"]["episode"], payload
        ),
    }


def _isolated_validation(
    seed: int,
    acquisitions: Mapping[str, Any],
    kernel: Any,
    catalogue: tuple[FlatRawActionV4, ...],
    encode: Any,
    config: Mapping[str, Any],
) -> dict[str, Any]:
    batches = tuple(_witness_blind_depth_frontier(kernel, catalogue, encode))
    rows = tuple(row for batch in batches for row in batch)
    arms = {}
    for arm, acquisition in sorted(acquisitions.items()):
        replay = exact_candidate_replay_v10(
            acquisition["candidate"], rows, catalogue
        )
        arms[arm] = {
            **replay,
            "candidate_id": acquisition["candidate"].public_document[
                "candidate_id"
            ],
        }
    payload = {
        "schema": "acfqp.adaptive_joint_isolated_validation.v55",
        "seed": seed,
        "full_frontier_ground_support_labels": len(batches),
        "full_frontier_raw_transition_count": len(rows),
        "full_frontier_raw_transition_sha256": _raw_sha(rows),
        "arm_replay": arms,
        "validation_rows_consumed_for_acquisition": False,
        "validation_rows_consumed_for_binding": False,
        "validation_rows_consumed_for_planning": False,
        "honest_partial_dynamics_reported": True,
    }
    return {
        **payload,
        "isolated_validation_id": domains_v55.extension_content_id_v55(
            config["domains"]["validation"], payload
        ),
    }


def _run_occurrence(args: tuple[int, int, Mapping[str, Any], Mapping[str, Any]]) -> dict[str, Any]:
    episode_index, seed, factor_library, config = args
    kernel, _witness = generate_stochastic_balanced_batch_refinement(
        stage_count=config["target_stage_count"],
        unit_base=config["target_unit_base"],
        seed=seed,
    )
    catalogue, encode = _interface(seed, kernel, config["terminal_tokens"])
    prior = _acquire(
        seed=seed,
        factor_prior_enabled=True,
        kernel=kernel,
        catalogue=catalogue,
        encode=encode,
        factor_library=factor_library,
        config=config,
    )
    no_prior = _acquire(
        seed=seed,
        factor_prior_enabled=False,
        kernel=kernel,
        catalogue=catalogue,
        encode=encode,
        factor_library=factor_library,
        config=config,
    )
    prior_rows = prior["rows"]
    no_prior_prefix = tuple(
        row
        for batch in no_prior["batches"][: len(prior["batches"])]
        for row in batch
    )
    if prior_rows != no_prior_prefix:
        _fail("V55 matched arms changed their common raw-observation prefix")
    result = {
        "seed": seed,
        "acquisitions": {
            "ANONYMOUS_FACTOR_PRIOR_ON": prior["document"],
            "STRICT_NO_PRIOR": no_prior["document"],
        },
        "common_prefix_sha256": _raw_sha(prior_rows),
        "episodes": {},
        "failures": [],
        "distinctions": [],
        "isolated_validation": None,
    }
    if episode_index < config["planning_validation_seed_count"]:
        for arm, acquisition in (
            ("ANONYMOUS_FACTOR_PRIOR_ON", prior),
            ("STRICT_NO_PRIOR", no_prior),
        ):
            episode, failures, distinctions = _episode(
                seed=seed,
                arm=arm,
                episode_index=episode_index,
                acquisition=acquisition,
                kernel=kernel,
                catalogue=catalogue,
                encode=encode,
                factor_library=factor_library,
                config=config,
            )
            result["episodes"][arm] = episode
            result["failures"].extend(failures)
            result["distinctions"].extend(distinctions)
        result["episodes"]["STRICT_EXACT_CONTEXT"] = _strict_episode(
            seed, episode_index, kernel, config
        )
        action_rows = [row["action_keys"] for row in result["episodes"].values()]
        if any(row != action_rows[0] for row in action_rows[1:]):
            _fail(f"V55 matched held-out plans changed at seed {seed}")
        if not all(row["success"] for row in result["episodes"].values()):
            _fail(f"V55 held-out planning failed at seed {seed}")
        result["isolated_validation"] = _isolated_validation(
            seed,
            {
                "ANONYMOUS_FACTOR_PRIOR_ON": prior,
                "STRICT_NO_PRIOR": no_prior,
            },
            kernel,
            catalogue,
            encode,
            config,
        )
    return result


def _ood_rows() -> tuple[tuple[FlatRawTransitionV4, ...], tuple[FlatRawActionV4, ...]]:
    catalogue = tuple(
        FlatRawActionV4(index, (bit, 1))
        for index, bit in enumerate((1, 2, 4))
    )
    tokens = {"A": 9_001, "F": 9_007, "S": 9_011}
    rows = []
    for mask in (0, 1, 2):
        for key, bit in enumerate((1, 2, 4)):
            successor = mask | bit
            status = "F" if successor & 4 else "S" if successor == 3 else "A"
            rows.append(
                FlatRawTransitionV4(
                    0,
                    len(rows),
                    (mask, tokens["A"], 3, 4, 1),
                    (0, 1, 2),
                    catalogue[key],
                    (successor, tokens[status], 3, 4, 1),
                    () if status != "A" else (0, 1, 2),
                    None if status == "A" else status == "S",
                )
            )
    return tuple(rows), catalogue


def build_adaptive_joint_factor_residual_campaign_document_v55(
    config: Mapping[str, Any],
    preregistration_id: str,
    factor_library: Mapping[str, Any],
) -> dict[str, Any]:
    if factor_library.get("factor_library_id") != config["factor_library_id"]:
        _fail("V55 anonymous factor-library identity changed")
    arguments = [
        (index, seed, factor_library, config)
        for index, seed in enumerate(config["target_seeds"])
    ]
    if config["worker_count"] == 1:
        occurrences = [_run_occurrence(row) for row in arguments]
    else:
        with ProcessPoolExecutor(max_workers=config["worker_count"]) as executor:
            occurrences = list(executor.map(_run_occurrence, arguments))
    acquisitions = {
        arm: [row["acquisitions"][arm] for row in occurrences]
        for arm in ("ANONYMOUS_FACTOR_PRIOR_ON", "STRICT_NO_PRIOR")
    }
    episodes = {
        arm: [
            row["episodes"][arm]
            for row in occurrences
            if arm in row["episodes"]
        ]
        for arm in (
            "ANONYMOUS_FACTOR_PRIOR_ON",
            "STRICT_NO_PRIOR",
            "STRICT_EXACT_CONTEXT",
        )
    }
    failures = [item for row in occurrences for item in row["failures"]]
    distinctions = [item for row in occurrences for item in row["distinctions"]]
    validations = [
        row["isolated_validation"]
        for row in occurrences
        if row["isolated_validation"] is not None
    ]
    prior_labels = sum(
        row["ground_support_labels"]
        for row in acquisitions["ANONYMOUS_FACTOR_PRIOR_ON"]
    )
    no_prior_labels = sum(
        row["ground_support_labels"]
        for row in acquisitions["STRICT_NO_PRIOR"]
    )
    prior_local = sum(
        row["local_ground_support_labels"]
        for row in episodes["ANONYMOUS_FACTOR_PRIOR_ON"]
    )
    no_prior_local = sum(
        row["local_ground_support_labels"]
        for row in episodes["STRICT_NO_PRIOR"]
    )
    prefix_curve = []
    prior_running = config["factor_library_labels"]
    no_prior_running = 0
    break_even = None
    for index, (prior, no_prior) in enumerate(
        zip(
            acquisitions["ANONYMOUS_FACTOR_PRIOR_ON"],
            acquisitions["STRICT_NO_PRIOR"],
            strict=True,
        ),
        start=1,
    ):
        prior_running += prior["ground_support_labels"]
        no_prior_running += no_prior["ground_support_labels"]
        reduction = no_prior_running - prior_running
        prefix_curve.append(
            {
                "occurrence_count": index,
                "factor_prior_on_lifetime_labels": prior_running,
                "strict_no_prior_lifetime_labels": no_prior_running,
                "net_label_reduction": reduction,
            }
        )
        if break_even is None and reduction > 0:
            break_even = index
    incremental = no_prior_labels - prior_labels
    online = (no_prior_labels + no_prior_local) - (prior_labels + prior_local)
    lifetime = online - config["factor_library_labels"]
    if incremental <= 0 or online <= 0 or lifetime <= 0 or break_even is None:
        _fail("V55 factor prior did not reduce the registered sample tax")
    sample_payload = {
        "schema": "acfqp.adaptive_joint_sample_tax.v55",
        "factor_library_labels_prior_on_only": config["factor_library_labels"],
        "factor_prior_on_acquisition_labels": prior_labels,
        "strict_no_prior_acquisition_labels": no_prior_labels,
        "incremental_acquisition_label_reduction": incremental,
        "factor_prior_on_local_recovery_labels": prior_local,
        "strict_no_prior_local_recovery_labels": no_prior_local,
        "online_label_reduction_including_local_recovery": online,
        "lifetime_label_reduction_after_factor_library_tax": lifetime,
        "diagnostic_break_even_occurrence_count": break_even,
        "prefix_curve": prefix_curve,
        "same_synthesizer_and_stopping_formula": True,
        "only_factor_prior_initial_weight_switched": True,
        "isolated_validation_labels_excluded_from_online_acquisition_and_reported_separately": True,
        "official_break_even_claimed": False,
    }
    sample_tax = {
        **sample_payload,
        "sample_tax_id": domains_v55.extension_content_id_v55(
            config["domains"]["sample_tax"], sample_payload
        ),
    }
    ood_rows, ood_catalogue = _ood_rows()
    ood_model = synthesize_joint_factor_residual_world_model_v9(
        {0: ood_rows},
        {0: ood_catalogue},
        factor_library,
        layout_domain=config["generic_domains"]["layout"],
        program_domain=config["generic_domains"]["program"],
        support_domain=config["generic_domains"]["support"],
        factor_domain=config["generic_domains"]["model"],
        result_domain=config["generic_domains"]["model"],
        minimum_reusable_factor_count=config["minimum_reusable_factor_count"],
    )
    if ood_model["transfer_admitted"] is not False:
        _fail("V55 incompatible OOD domain was admitted")
    ood_payload = {
        "schema": "acfqp.adaptive_joint_ood_rejection.v55",
        "joint_model_id": ood_model["joint_model_id"],
        "factorable_reusable_count": ood_model["factorable_reusable_count"],
        "minimum_reusable_factor_count": config["minimum_reusable_factor_count"],
        "complete_ood_program_synthesized_from_raw_observations": True,
        "prior_transfer_attempted": False,
        "ood_outcome_execution_performed": False,
        "outcome": "STRICT_SIGNATURE_THRESHOLD_OOD_NO_TRANSFER",
    }
    ood = {
        **ood_payload,
        "ood_rejection_id": domains_v55.extension_content_id_v55(
            config["domains"]["ood"], ood_payload
        ),
    }
    payload = {
        "schema": "acfqp.adaptive_joint_factor_residual_campaign.v55",
        "preregistration_id": preregistration_id,
        "frozen_v54r1_campaign_id": config["v54r1_campaign_id"],
        "frozen_v54r1_verification_id": config["v54r1_verification_id"],
        "factor_library_id": factor_library["factor_library_id"],
        "factor_library_signature_inventory": [
            row["signature_sha256"]
            for row in factor_library["cross_schema_subprograms"]
        ],
        "acquisitions": acquisitions,
        "common_prefix_sha256": [row["common_prefix_sha256"] for row in occurrences],
        "episodes": episodes,
        "failed_certificates": failures,
        "local_distinctions": distinctions,
        "isolated_full_frontier_validations": validations,
        "sample_tax": sample_tax,
        "ood_rejection": ood,
        "accounting": {
            "factor_library_labels": config["factor_library_labels"],
            "target_acquisition_labels": {
                "ANONYMOUS_FACTOR_PRIOR_ON": prior_labels,
                "STRICT_NO_PRIOR": no_prior_labels,
            },
            "local_recovery_labels": {
                "ANONYMOUS_FACTOR_PRIOR_ON": prior_local,
                "STRICT_NO_PRIOR": no_prior_local,
            },
            "isolated_validation_labels": sum(
                row["full_frontier_ground_support_labels"] for row in validations
            ),
            "execution_steps": {
                arm: sum(row["execution_steps"] for row in values)
                for arm, values in episodes.items()
            },
            "planning_compute_events": {
                arm: sum(row["planning_compute_events"] for row in values)
                for arm, values in episodes.items()
            },
            "certificate_compute_events": len(failures),
            "derivation_compute_events": sum(
                len(row["stopping_history"])
                for values in acquisitions.values()
                for row in values
            ),
            "all_axes_separate": True,
        },
        "full_frontier_target_layout_calibration_consumed": False,
        "shared_residual_scaffold_consumed": False,
        "predeclared_reusable_factor_slots_consumed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    return {
        **payload,
        "campaign_id": domains_v55.extension_content_id_v55(
            config["domains"]["campaign"], payload
        ),
    }


__all__ = (
    "AdaptiveJointFactorResidualCampaignCoreV55Error",
    "build_adaptive_joint_factor_residual_campaign_document_v55",
)
