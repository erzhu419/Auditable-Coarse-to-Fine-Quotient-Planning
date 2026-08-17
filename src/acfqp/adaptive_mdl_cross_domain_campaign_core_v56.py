"""V56 two-domain adaptive MDL world-model campaign construction core."""

from __future__ import annotations

from collections import deque
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from functools import lru_cache
import hashlib
import heapq
import random
from typing import Any, Iterator, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v56 as domains_v56
from acfqp.domains.stochastic_balanced_batch_refinement import (
    generate_stochastic_balanced_batch_refinement,
)
from acfqp.domains.stochastic_batch_refinement import (
    BatchRefinementAction,
    BatchRefinementState,
    BatchRefinementStatus,
    select_seeded_batch_refinement_outcome_v1,
)
from acfqp.domains.stochastic_coupled_exchange import (
    CoupledExchangeAction,
    CoupledExchangeState,
    CoupledExchangeStatus,
    generate_stochastic_coupled_exchange,
    select_seeded_coupled_exchange_outcome_v1,
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
from acfqp.generic_mdl_adaptive_joint_synthesizer_v11 import (
    MDLAdaptiveJointCandidateV11,
    exact_candidate_replay_v11,
    mdl_confidence_stop_update_v11,
    synthesize_mdl_adaptive_joint_candidate_v11,
)
from acfqp.phase3e_ids import canonical_json_bytes


class AdaptiveMDLCrossDomainCampaignCoreV56Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise AdaptiveMDLCrossDomainCampaignCoreV56Error(message)


@dataclass(frozen=True, slots=True)
class _GroundAdapterV56:
    family: str
    seed: int
    kernel: Any
    catalogue: tuple[FlatRawActionV4, ...]
    encode: Any

    def initial(self) -> Any:
        return self.kernel.initial_distribution()[0][1]

    def actions(self, state: Any) -> tuple[Any, ...]:
        return tuple(self.kernel.actions(state))

    def action_key(self, action: Any) -> int:
        if self.family == "BALANCED_BATCH_REFINEMENT":
            return action.rule
        if self.family == "COUPLED_EXCHANGE":
            return action.exchange
        _fail("V56 ground family changed")

    def action(self, key: int) -> Any:
        if self.family == "BALANCED_BATCH_REFINEMENT":
            return BatchRefinementAction(key)
        if self.family == "COUPLED_EXCHANGE":
            return CoupledExchangeAction(key)
        _fail("V56 ground family changed")

    def active(self, state: Any) -> bool:
        if self.family == "BALANCED_BATCH_REFINEMENT":
            return state.status is BatchRefinementStatus.ACTIVE
        if self.family == "COUPLED_EXCHANGE":
            return state.status is CoupledExchangeStatus.ACTIVE
        _fail("V56 ground family changed")

    def success(self, state: Any) -> bool:
        if self.family == "BALANCED_BATCH_REFINEMENT":
            return state.status is BatchRefinementStatus.SUCCESS
        if self.family == "COUPLED_EXCHANGE":
            return state.status is CoupledExchangeStatus.SUCCESS
        _fail("V56 ground family changed")

    def probe_state(self, key: int) -> Any:
        rule = self.kernel.rules[key]
        if self.family == "BALANCED_BATCH_REFINEMENT":
            return BatchRefinementState(
                rule.source_stage, 0, 0, 0, BatchRefinementStatus.ACTIVE
            )
        if self.family == "COUPLED_EXCHANGE":
            return CoupledExchangeState(
                rule.source_stage,
                0,
                0,
                0,
                0,
                rule.source_stage,
                CoupledExchangeStatus.ACTIVE,
            )
        _fail("V56 ground family changed")

    def select_outcome(
        self, state: Any, key: int, episode_index: int, decision_index: int
    ) -> tuple[Any, str]:
        outcomes = self.kernel.step(state, self.action(key))
        if self.family == "BALANCED_BATCH_REFINEMENT":
            return select_seeded_batch_refinement_outcome_v1(
                outcomes,
                seed=self.seed,
                episode_index=episode_index,
                decision_index=decision_index,
            )
        if self.family == "COUPLED_EXCHANGE":
            return select_seeded_coupled_exchange_outcome_v1(
                outcomes,
                seed=self.seed,
                episode_index=episode_index,
                decision_index=decision_index,
            )
        _fail("V56 ground family changed")


def _balanced_interface(seed: int, kernel: Any, tokens: Mapping[str, int]):
    state_order = list(range(6))
    action_order = list(range(5))
    random.Random(seed ^ 0x56A17).shuffle(state_order)
    random.Random(seed ^ 0x56B29).shuffle(action_order)
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


def _coupled_interface(seed: int, kernel: Any, tokens: Mapping[str, int]):
    state_order = list(range(10))
    action_order = list(range(6))
    random.Random(seed ^ 0x56C37).shuffle(state_order)
    random.Random(seed ^ 0x56D49).shuffle(action_order)
    catalogue = tuple(
        FlatRawActionV4(
            key,
            tuple(
                (
                    seed * 100 + rule.source_stage,
                    seed * 100 + rule.destination_stage,
                    rule.primary_increment,
                    rule.secondary_increment,
                    rule.risk_increment,
                    seed * 10_000 + key,
                )[index]
                for index in action_order
            ),
        )
        for key, rule in enumerate(kernel.rules)
    )

    def encode(state: CoupledExchangeState) -> tuple[int, ...]:
        status = tokens[
            "A"
            if state.status is CoupledExchangeStatus.ACTIVE
            else "S"
            if state.status is CoupledExchangeStatus.SUCCESS
            else "F"
        ]
        semantic = (
            seed * 100 + state.stage,
            state.primary,
            state.secondary,
            state.bonus,
            state.risk,
            state.steps,
            status,
            kernel.risk_capacity,
            kernel.target_primary,
            seed * 100 + kernel.goal_stage,
        )
        return tuple(semantic[index] for index in state_order)

    return catalogue, encode


def _adapter(
    family: str, seed: int, config: Mapping[str, Any]
) -> _GroundAdapterV56:
    spec = config["families"][family]
    if family == "BALANCED_BATCH_REFINEMENT":
        kernel, _witness = generate_stochastic_balanced_batch_refinement(
            stage_count=spec["stage_count"],
            unit_base=spec["unit_base"],
            seed=seed,
        )
        catalogue, encode = _balanced_interface(
            seed, kernel, config["terminal_tokens"]
        )
    elif family == "COUPLED_EXCHANGE":
        kernel, _witness = generate_stochastic_coupled_exchange(
            stage_count=spec["stage_count"],
            primary_base=spec["primary_base"],
            seed=seed,
        )
        catalogue, encode = _coupled_interface(
            seed, kernel, config["terminal_tokens"]
        )
    else:
        _fail("V56 family registry changed")
    del _witness
    return _GroundAdapterV56(family, seed, kernel, catalogue, encode)


def _transition_batch(
    adapter: _GroundAdapterV56, state: Any, key: int, index: int
) -> tuple[FlatRawTransitionV4, ...]:
    legal = adapter.actions(state)
    action = adapter.action(key)
    if action not in legal:
        _fail("V56 attempted a ground query for an illegal action")
    rows = []
    for offset, outcome in enumerate(adapter.kernel.step(state, action)):
        successor = outcome.next_state
        legal_after = adapter.actions(successor)
        rows.append(
            FlatRawTransitionV4(
                0,
                index + offset,
                adapter.encode(state),
                tuple(adapter.action_key(row) for row in legal),
                adapter.catalogue[key],
                adapter.encode(successor),
                tuple(adapter.action_key(row) for row in legal_after),
                None if legal_after else adapter.success(successor),
            )
        )
    return tuple(rows)


def _witness_blind_depth_frontier(
    adapter: _GroundAdapterV56,
) -> Iterator[tuple[FlatRawTransitionV4, ...]]:
    initial = adapter.initial()
    frontier = [(0, 0, initial)]
    seen = {initial}
    insertion = 1
    pending: deque[tuple[Any, Any, int]] = deque()
    transition_index = 0
    while frontier or pending:
        if not pending:
            negative_depth, _ordinal, state = heapq.heappop(frontier)
            depth = -negative_depth
            pending.extend((state, action, depth) for action in adapter.actions(state))
        state, action, depth = pending.popleft()
        key = adapter.action_key(action)
        batch = _transition_batch(adapter, state, key, transition_index)
        transition_index += len(batch)
        for outcome in adapter.kernel.step(state, action):
            successor = outcome.next_state
            if adapter.active(successor) and successor not in seen:
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
) -> MDLAdaptiveJointCandidateV11:
    return synthesize_mdl_adaptive_joint_candidate_v11(
        rows,
        catalogue,
        factor_library,
        support_label_count=labels,
        generic_domains=config["generic_domains"],
        candidate_domain=config["domains"]["candidate"],
        candidate_content_id=domains_v56.extension_content_id_v56,
        minimum_reusable_factor_count=config["minimum_reusable_factor_count"],
    )


def _acquisition_document(
    *,
    adapter: _GroundAdapterV56,
    arm: str,
    factor_prior_enabled: bool,
    labels: int,
    rows: tuple[FlatRawTransitionV4, ...],
    candidate: MDLAdaptiveJointCandidateV11,
    issued_at: int,
    invalidated: int,
    program_disagreements: int,
    history: list[dict[str, Any]],
    config: Mapping[str, Any],
) -> dict[str, Any]:
    payload = {
        "schema": "acfqp.mdl_adaptive_acquisition.v56",
        "family": adapter.family,
        "seed": adapter.seed,
        "arm": arm,
        "factor_prior_enabled": factor_prior_enabled,
        "ground_support_labels": labels,
        "raw_transition_count": len(rows),
        "raw_transition_sha256": _raw_sha(rows),
        "candidate": dict(candidate.public_document),
        "candidate_issued_at_support_label": issued_at,
        "invalidated_candidate_count": invalidated,
        "candidate_program_disagreement_count": program_disagreements,
        "stopping_history": history,
        "candidate_synthesis_attempted_after_every_support_query": True,
        "minimum_candidate_label_floor_consumed": False,
        "confirmation_block_consumed": False,
        "witness_blind_depth_frontier_policy": True,
        "generation_witness_accessed": False,
        "full_frontier_calibration_consumed": False,
        "same_synthesizer_query_order_mdl_and_confidence_formula": True,
        "only_switched_variable": "REGISTERED_FACTOR_CODE_CREDIT_UNITS",
    }
    return {
        **payload,
        "acquisition_id": domains_v56.extension_content_id_v56(
            config["domains"]["acquisition"], payload
        ),
    }


def _acquire_matched(
    adapter: _GroundAdapterV56,
    factor_library: Mapping[str, Any],
    config: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    rows: list[FlatRawTransitionV4] = []
    batches: list[tuple[FlatRawTransitionV4, ...]] = []
    candidate: MDLAdaptiveJointCandidateV11 | None = None
    issued_at = 0
    invalidated = 0
    program_disagreements = 0
    previous_fingerprint = None
    pending = {
        "ANONYMOUS_FACTOR_PRIOR_ON": True,
        "STRICT_NO_PRIOR": False,
    }
    histories = {arm: [] for arm in pending}
    results: dict[str, dict[str, Any]] = {}
    maximum = config["families"][adapter.family]["maximum_acquisition_labels"]
    generator = _witness_blind_depth_frontier(adapter)
    for labels in range(1, maximum + 1):
        try:
            batch = next(generator)
        except StopIteration:
            _fail(
                "V56 witness-blind frontier exhausted before both arms stopped "
                f"for {adapter.family} seed {adapter.seed}; "
                f"pending arms={sorted(pending)}"
            )
        rows.extend(batch)
        batches.append(batch)
        reason = "NO_COMPLETE_CANDIDATE_YET"
        replay = None
        if candidate is not None:
            replay = exact_candidate_replay_v11(
                candidate, tuple(rows), adapter.catalogue
            )
            if replay["exact"] is not True:
                invalidated += 1
                previous_fingerprint = candidate.public_document[
                    "program_fingerprint_sha256"
                ]
                candidate = None
                reason = "COUNTEREVIDENCE_INVALIDATED_COMPLETE_CANDIDATE"
        if candidate is None:
            try:
                candidate = _candidate(
                    tuple(rows), adapter.catalogue, factor_library, labels, config
                )
            except Exception:
                for arm in tuple(pending):
                    histories[arm].append(
                        {
                            "support_label_count": labels,
                            "raw_transition_sha256": _raw_sha(tuple(rows)),
                            "update_reason": reason,
                            "candidate_available": False,
                        }
                    )
                continue
            issued_at = labels
            fingerprint = candidate.public_document[
                "program_fingerprint_sha256"
            ]
            if previous_fingerprint is not None and fingerprint != previous_fingerprint:
                program_disagreements += 1
            reason = (
                "FIRST_COMPLETE_CANDIDATE_SYNTHESIZED"
                if invalidated == 0
                else "COUNTEREVIDENCE_TRIGGERED_COMPLETE_RESYNTHESIS"
            )
        for arm, enabled in tuple(pending.items()):
            stop = mdl_confidence_stop_update_v11(
                candidate,
                tuple(rows),
                adapter.catalogue,
                factor_prior_enabled=enabled,
                invalidated_candidate_count=invalidated,
                candidate_program_disagreement_count=program_disagreements,
                factor_signature_credit_units=config[
                    "factor_signature_credit_units"
                ],
                confidence_reserve_units=config["confidence_reserve_units"],
                invalidated_candidate_penalty_units=config[
                    "invalidated_candidate_penalty_units"
                ],
                minimum_reusable_factor_count=config[
                    "minimum_reusable_factor_count"
                ],
            )
            histories[arm].append(
                {
                    "support_label_count": labels,
                    "raw_transition_sha256": _raw_sha(tuple(rows)),
                    "update_reason": reason,
                    "candidate_available": True,
                    "candidate_id": candidate.public_document["candidate_id"],
                    "exact_replay": replay,
                    "stop_update": stop,
                }
            )
            if stop["stopped"] is not True:
                continue
            document = _acquisition_document(
                adapter=adapter,
                arm=arm,
                factor_prior_enabled=enabled,
                labels=labels,
                rows=tuple(rows),
                candidate=candidate,
                issued_at=issued_at,
                invalidated=invalidated,
                program_disagreements=program_disagreements,
                history=list(histories[arm]),
                config=config,
            )
            results[arm] = {
                "document": document,
                "candidate": candidate,
                "rows": tuple(rows),
                "batches": tuple(batches),
            }
            del pending[arm]
        if not pending:
            prior = results["ANONYMOUS_FACTOR_PRIOR_ON"]
            no_prior = results["STRICT_NO_PRIOR"]
            common = tuple(
                row
                for batch in no_prior["batches"][: len(prior["batches"])]
                for row in batch
            )
            if prior["rows"] != common:
                _fail("V56 matched acquisition prefix changed")
            return results
    _fail(
        "V56 adaptive acquisition crossed its development label cap for "
        f"{adapter.family} seed {adapter.seed}; pending arms={sorted(pending)}"
    )


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
        _fail("V56 local relation recovery was not unique")
    return matches[0]


def _certificate(
    adapter: _GroundAdapterV56,
    arm: str,
    episode_index: int,
    decision_index: int,
    program_id: str,
    kind: str,
    detail: Mapping[str, Any],
    config: Mapping[str, Any],
) -> dict[str, Any]:
    payload = {
        "schema": "acfqp.mdl_adaptive_failed_certificate.v56",
        "family": adapter.family,
        "seed": adapter.seed,
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
        "failed_certificate_id": domains_v56.extension_content_id_v56(
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
        "schema": "acfqp.mdl_adaptive_local_distinction.v56",
        "failed_certificate_id": failure["failed_certificate_id"],
        "distinction_kind": kind,
        "distinction_detail": dict(detail),
        "query_after_failed_certificate": True,
        "ground_support_labels": labels,
    }
    return {
        **payload,
        "local_distinction_id": domains_v56.extension_content_id_v56(
            config["domains"]["distinction"], payload
        ),
    }


def _episode(
    *,
    adapter: _GroundAdapterV56,
    arm: str,
    episode_index: int,
    acquisition: Mapping[str, Any],
    factor_library: Mapping[str, Any],
    config: Mapping[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    candidate = acquisition["candidate"]
    evidence_rows = list(acquisition["rows"])
    covered = {(row.pre, row.action.key) for row in evidence_rows}
    failures: list[dict[str, Any]] = []
    distinctions: list[dict[str, Any]] = []
    overlay: dict[str, dict[int, int]] = {}
    actions: list[int] = []
    tapes: list[str] = []
    planning_compute = 0
    peak_cache = 0
    local_labels = 0
    resynthesis_count = 0
    recovery_attempts = 0
    state = adapter.initial()
    decision = 0
    initial_candidate_id = candidate.public_document["candidate_id"]
    while adapter.active(state):
        program = candidate.program
        layout = candidate.layout
        _aligned_rows, aligned_catalogue = align_generic_occurrence_v5(
            tuple(evidence_rows),
            adapter.catalogue,
            layout,
            canonical_occurrence=0,
        )
        binding = program["occurrence_bindings"][0]
        raw_state = adapter.encode(state)
        canonical_state = tuple(
            raw_state[index] for index in layout.state_canonical_to_raw
        )
        fields = _relation_fields(program)
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
                adapter,
                arm,
                episode_index,
                decision,
                program["program_id"],
                "MISSING_COMPILED_RELATION_SUPPORT",
                {"relation_name": name, "relation_input": relation_input},
                config,
            )
            failures.append(failure)
            field = fields[name]
            aligned_action = next(
                row for row in aligned_catalogue if row.fields[field] == relation_input
            )
            probe = adapter.probe_state(aligned_action.key)
            raw_probe = adapter.encode(probe)
            canonical_probe = tuple(
                raw_probe[index] for index in layout.state_canonical_to_raw
            )
            actual = {
                tuple(
                    adapter.encode(outcome.next_state)[index]
                    for index in layout.state_canonical_to_raw
                )
                for outcome in adapter.kernel.step(
                    probe, adapter.action(aligned_action.key)
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
                f"V56 abstract planner failed for {adapter.family} seed "
                f"{adapter.seed}: {type(error).__name__}: {error}"
            )
        key = plan[0]
        planning_compute += evaluations
        peak_cache = max(peak_cache, cache_size)
        pair = (raw_state, key)
        if pair not in covered:
            failure = _certificate(
                adapter,
                arm,
                episode_index,
                decision,
                program["program_id"],
                "MISSING_QUERY_LOCAL_STATE_ACTION_SUPPORT",
                {"raw_state": list(raw_state), "action_key": key},
                config,
            )
            failures.append(failure)
            batch = _transition_batch(
                adapter, state, key, len(evidence_rows)
            )
            local_labels += 1
            aligned_batch, _ = align_generic_occurrence_v5(
                batch,
                adapter.catalogue,
                layout,
                canonical_occurrence=0,
            )
            actual = {row.post for row in aligned_batch}
            aligned_action = next(
                row for row in aligned_catalogue if row.key == key
            )
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
                    _fail("V56 crossed its local resynthesis cap")
                candidate = _candidate(
                    tuple(evidence_rows),
                    adapter.catalogue,
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
                            "predicted_support": [
                                list(row) for row in sorted(predicted)
                            ],
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
        outcome, tape = adapter.select_outcome(
            state, key, episode_index, decision
        )
        state = outcome.next_state
        actions.append(key)
        tapes.append(tape)
        decision += 1
    payload = {
        "schema": "acfqp.mdl_adaptive_receding_episode.v56",
        "family": adapter.family,
        "seed": adapter.seed,
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
            local_labels
            == sum(row["ground_support_labels"] for row in distinctions)
            and len(failures) == len(distinctions)
        ),
        "success": adapter.success(state),
    }
    return (
        {
            **payload,
            "episode_id": domains_v56.extension_content_id_v56(
                config["domains"]["episode"], payload
            ),
        },
        failures,
        distinctions,
    )


def _strict_choice(
    adapter: _GroundAdapterV56, state: Any, cache: dict[Any, Any]
) -> tuple[int, int, int]:
    choices: dict[Any, int] = {}
    labels = 0

    @lru_cache(maxsize=None)
    def solve(current: Any) -> bool:
        nonlocal labels
        if adapter.success(current):
            return True
        if not adapter.active(current):
            return False
        for action in adapter.actions(current):
            key = adapter.action_key(action)
            pair = (current, key)
            if pair not in cache:
                cache[pair] = tuple(
                    row.next_state for row in adapter.kernel.step(current, action)
                )
                labels += 1
            if all(solve(successor) for successor in cache[pair]):
                choices[current] = key
                return True
        return False

    if not solve(state) or state not in choices:
        _fail("V56 strict planner found no robust continuation")
    return choices[state], solve.cache_info().currsize, labels


def _strict_episode(
    adapter: _GroundAdapterV56,
    episode_index: int,
    config: Mapping[str, Any],
) -> dict[str, Any]:
    state = adapter.initial()
    cache: dict[Any, Any] = {}
    actions: list[int] = []
    tapes: list[str] = []
    planning = 0
    peak = 0
    labels = 0
    decision = 0
    while adapter.active(state):
        key, compute, new_labels = _strict_choice(adapter, state, cache)
        outcome, tape = adapter.select_outcome(
            state, key, episode_index, decision
        )
        state = outcome.next_state
        actions.append(key)
        tapes.append(tape)
        planning += compute
        peak = max(peak, compute)
        labels += new_labels
        decision += 1
    payload = {
        "schema": "acfqp.mdl_adaptive_receding_episode.v56",
        "family": adapter.family,
        "seed": adapter.seed,
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
        "success": adapter.success(state),
    }
    return {
        **payload,
        "episode_id": domains_v56.extension_content_id_v56(
            config["domains"]["episode"], payload
        ),
    }


def _isolated_validation(
    adapter: _GroundAdapterV56,
    acquisitions: Mapping[str, Any],
    config: Mapping[str, Any],
) -> dict[str, Any]:
    batches = tuple(_witness_blind_depth_frontier(adapter))
    rows = tuple(row for batch in batches for row in batch)
    arms = {}
    for arm, acquisition in sorted(acquisitions.items()):
        replay = exact_candidate_replay_v11(
            acquisition["candidate"], rows, adapter.catalogue
        )
        arms[arm] = {
            **replay,
            "candidate_id": acquisition["candidate"].public_document[
                "candidate_id"
            ],
        }
    payload = {
        "schema": "acfqp.mdl_adaptive_isolated_validation.v56",
        "family": adapter.family,
        "seed": adapter.seed,
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
        "isolated_validation_id": domains_v56.extension_content_id_v56(
            config["domains"]["validation"], payload
        ),
    }


def _run_occurrence(
    args: tuple[str, int, int, Mapping[str, Any], Mapping[str, Any]]
) -> dict[str, Any]:
    family, episode_index, seed, factor_library, config = args
    adapter = _adapter(family, seed, config)
    acquisitions = _acquire_matched(adapter, factor_library, config)
    result = {
        "family": family,
        "seed": seed,
        "acquisitions": {
            arm: row["document"] for arm, row in acquisitions.items()
        },
        "common_prefix_sha256": _raw_sha(
            acquisitions["ANONYMOUS_FACTOR_PRIOR_ON"]["rows"]
        ),
        "episodes": {},
        "failures": [],
        "distinctions": [],
        "isolated_validation": None,
    }
    if episode_index < config["families"][family]["planning_seed_count"]:
        for arm, acquisition in acquisitions.items():
            episode, failures, distinctions = _episode(
                adapter=adapter,
                arm=arm,
                episode_index=episode_index,
                acquisition=acquisition,
                factor_library=factor_library,
                config=config,
            )
            result["episodes"][arm] = episode
            result["failures"].extend(failures)
            result["distinctions"].extend(distinctions)
        result["episodes"]["STRICT_EXACT_CONTEXT"] = _strict_episode(
            adapter, episode_index, config
        )
        action_rows = [row["action_keys"] for row in result["episodes"].values()]
        if any(row != action_rows[0] for row in action_rows[1:]):
            _fail(f"V56 matched plans changed for {family} seed {seed}")
        if not all(row["success"] for row in result["episodes"].values()):
            _fail(f"V56 held-out planning failed for {family} seed {seed}")
        result["isolated_validation"] = _isolated_validation(
            adapter, acquisitions, config
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


def build_adaptive_mdl_cross_domain_campaign_document_v56(
    config: Mapping[str, Any],
    preregistration_id: str,
    factor_library: Mapping[str, Any],
) -> dict[str, Any]:
    if factor_library.get("factor_library_id") != config["factor_library_id"]:
        _fail("V56 factor-library identity changed")
    arguments = [
        (family, index, seed, factor_library, config)
        for family, spec in config["families"].items()
        for index, seed in enumerate(spec["target_seeds"])
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
    prior_labels = sum(row["ground_support_labels"] for row in acquisitions[
        "ANONYMOUS_FACTOR_PRIOR_ON"
    ])
    no_prior_labels = sum(row["ground_support_labels"] for row in acquisitions[
        "STRICT_NO_PRIOR"
    ])
    prior_local = sum(row["local_ground_support_labels"] for row in episodes[
        "ANONYMOUS_FACTOR_PRIOR_ON"
    ])
    no_prior_local = sum(row["local_ground_support_labels"] for row in episodes[
        "STRICT_NO_PRIOR"
    ])
    family_rows = {}
    for family in config["families"]:
        prior_family = [
            row for row in acquisitions["ANONYMOUS_FACTOR_PRIOR_ON"]
            if row["family"] == family
        ]
        no_prior_family = [
            row for row in acquisitions["STRICT_NO_PRIOR"]
            if row["family"] == family
        ]
        family_rows[family] = {
            "occurrence_count": len(prior_family),
            "factor_prior_on_acquisition_labels": sum(
                row["ground_support_labels"] for row in prior_family
            ),
            "strict_no_prior_acquisition_labels": sum(
                row["ground_support_labels"] for row in no_prior_family
            ),
        }
        family_rows[family]["incremental_label_reduction"] = (
            family_rows[family]["strict_no_prior_acquisition_labels"]
            - family_rows[family]["factor_prior_on_acquisition_labels"]
        )
        if family_rows[family]["incremental_label_reduction"] <= 0:
            _fail(f"V56 factor prior did not reduce sample tax in {family}")
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
                "family": prior["family"],
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
        _fail("V56 registered cross-domain sample tax was not reduced")
    sample_payload = {
        "schema": "acfqp.mdl_adaptive_sample_tax.v56",
        "factor_library_labels_prior_on_only": config["factor_library_labels"],
        "factor_prior_on_acquisition_labels": prior_labels,
        "strict_no_prior_acquisition_labels": no_prior_labels,
        "incremental_acquisition_label_reduction": incremental,
        "factor_prior_on_local_recovery_labels": prior_local,
        "strict_no_prior_local_recovery_labels": no_prior_local,
        "online_label_reduction_including_local_recovery": online,
        "lifetime_label_reduction_after_factor_library_tax": lifetime,
        "diagnostic_break_even_occurrence_count": break_even,
        "family_projections": family_rows,
        "prefix_curve": prefix_curve,
        "same_synthesizer_query_order_mdl_and_confidence_formula": True,
        "only_registered_factor_code_credit_switched": True,
        "fixed_minimum_label_floor_consumed": False,
        "fixed_confirmation_block_consumed": False,
        "official_break_even_claimed": False,
    }
    sample_tax = {
        **sample_payload,
        "sample_tax_id": domains_v56.extension_content_id_v56(
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
        _fail("V56 incompatible OOD domain was admitted")
    ood_payload = {
        "schema": "acfqp.mdl_adaptive_ood_rejection.v56",
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
        "ood_rejection_id": domains_v56.extension_content_id_v56(
            config["domains"]["ood"], ood_payload
        ),
    }
    payload = {
        "schema": "acfqp.mdl_adaptive_cross_domain_campaign.v56",
        "preregistration_id": preregistration_id,
        "frozen_v55_campaign_id": config["v55_campaign_id"],
        "frozen_v55_verification_id": config["v55_verification_id"],
        "factor_library_id": config["factor_library_id"],
        "families": list(config["families"]),
        "acquisitions": acquisitions,
        "episodes": episodes,
        "failed_certificates": failures,
        "local_distinctions": distinctions,
        "isolated_full_frontier_validations": validations,
        "sample_tax": sample_tax,
        "ood_rejection": ood,
        "accounting": {
            "offline_factor_library_labels": config["factor_library_labels"],
            "factor_prior_on_target_acquisition_labels": prior_labels,
            "strict_no_prior_target_acquisition_labels": no_prior_labels,
            "factor_prior_on_local_recovery_labels": prior_local,
            "strict_no_prior_local_recovery_labels": no_prior_local,
            "isolated_validation_labels": sum(
                row["full_frontier_ground_support_labels"] for row in validations
            ),
            "factor_prior_on_execution_steps": sum(
                row["execution_steps"] for row in episodes[
                    "ANONYMOUS_FACTOR_PRIOR_ON"
                ]
            ),
            "strict_no_prior_execution_steps": sum(
                row["execution_steps"] for row in episodes["STRICT_NO_PRIOR"]
            ),
            "direct_execution_steps": sum(
                row["execution_steps"] for row in episodes["STRICT_EXACT_CONTEXT"]
            ),
            "factor_prior_on_planning_compute_events": sum(
                row["planning_compute_events"] for row in episodes[
                    "ANONYMOUS_FACTOR_PRIOR_ON"
                ]
            ),
            "strict_no_prior_planning_compute_events": sum(
                row["planning_compute_events"] for row in episodes[
                    "STRICT_NO_PRIOR"
                ]
            ),
            "direct_planning_compute_events": sum(
                row["planning_compute_events"] for row in episodes[
                    "STRICT_EXACT_CONTEXT"
                ]
            ),
            "certificate_compute_events": len(failures),
            "all_axes_separate": True,
        },
        "minimum_candidate_label_floor_consumed": False,
        "confirmation_block_consumed": False,
        "full_frontier_target_layout_calibration_consumed": False,
        "same_synthesizer_used_in_both_families": True,
        "arbitrary_domain_transfer_claimed": False,
        "global_exact_dynamics_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    return {
        **payload,
        "campaign_id": domains_v56.extension_content_id_v56(
            config["domains"]["campaign"], payload
        ),
    }


__all__ = (
    "AdaptiveMDLCrossDomainCampaignCoreV56Error",
    "build_adaptive_mdl_cross_domain_campaign_document_v56",
)
