"""Memoize compiled-program plans by exact projected state and legal set."""

from __future__ import annotations

import copy
import hashlib
import heapq
from math import ceil
from types import FunctionType
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v115 as domains
from acfqp import generic_incremental_abstract_successor_sequence_v113 as previous
from acfqp import generic_incremental_abstract_successor_v113 as successor
from acfqp.generic_abstract_partial_agreement_shield_v99 import (
    shield_abstract_action_order_v99,
)
from acfqp.generic_incremental_abstract_successor_v113 import (
    IncrementalAbstractSuccessorStateV113,
)
from acfqp.generic_partial_factor_proposal_v15 import PartialFactorCandidateV15
from acfqp.generic_partial_factor_proposal_v15 import (
    partial_factor_successor_projections_v15,
)
from acfqp.generic_quotient_plan_dependency_receipt_v109 import (
    build_quotient_plan_dependency_receipt_v109,
)
from acfqp.phase3e_ids import canonical_json_bytes


class GenericProjectedProgramMemoSequenceV115Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise GenericProjectedProgramMemoSequenceV115Error(message)


def _memoized_program_plan(
    *,
    source_plan: Mapping[str, Any],
    source_successor_state_id: str,
    current_successor_state_id: str,
    quotient_graph_id: str,
    terminal_rule_sha256: str,
    legal: tuple[int, ...],
    legality_support_source: str,
    legality_failure_index: int | None,
) -> dict[str, Any]:
    action = source_plan["initial_action_key"]
    shield = shield_abstract_action_order_v99(
        abstract_proposal=(action,),
        partial_proposal=(action,),
        legal_action_keys=legal,
    )
    payload = {
        "schema": "acfqp.generic_projected_program_memo_plan.v115",
        "quotient_graph_id": quotient_graph_id,
        "source_successor_state_id": source_successor_state_id,
        "current_successor_state_id": current_successor_state_id,
        "partial_candidate_id": source_plan["partial_candidate_id"],
        "planning_source": "COMPILED_FACTOR_PROGRAM_MEMOIZED",
        "initial_action_key": action,
        "projected_action_path": copy.deepcopy(
            source_plan["projected_action_path"]
        ),
        "abstract_support_branch_evaluations": 0,
        "source_compiled_factor_program_plan": copy.deepcopy(source_plan),
        "source_compiled_factor_program_plan_id": source_plan[
            "legality_conditioned_quotient_plan_id"
        ],
        "terminal_projection_rule_sha256": terminal_rule_sha256,
        "exact_legal_action_keys_at_initial_state": list(legal),
        "legality_support_source": legality_support_source,
        "legality_failure_index": legality_failure_index,
        "agreement_shield_receipt": shield,
        "projected_state_and_exact_legal_set_cache_keyed": True,
        "cache_reused_only_under_identical_compiled_successor_state": True,
        "initial_illegal_actions_forbidden_in_reused_order": True,
        "ground_legality_used_only_after_existing_support_or_failed_certificate": True,
        "cached_program_ordering_used_as_safety_authority": False,
        "ground_transition_accessed_during_program_memo_reuse": False,
        "query_local_exact_overlay_remains_only_safety_authority": True,
        "complete_ground_world_model_claimed": False,
    }
    return {
        **payload,
        "legality_conditioned_quotient_plan_id": domains.extension_content_id_v115(
            domains.CONSTRUCTION_K7_PROJECTED_PROGRAM_MEMO_PLAN_V115_DOMAIN,
            payload,
        ),
    }


def _program_plan_with_branch_cache(
    candidate: PartialFactorCandidateV15,
    catalogue: tuple[Any, ...],
    rules: tuple[Mapping[str, Any], ...],
    initial: tuple[int, ...],
    legal: frozenset[int],
    branch_cache: dict[tuple[tuple[int, ...], int], tuple[tuple[int, ...], ...]],
    *,
    maximum_depth: int,
) -> dict[str, Any]:
    actions = successor._canonical_actions(candidate, catalogue)  # noqa: SLF001
    action_values = {
        field: tuple(action.fields[field] for action in actions)
        for field in range(len(actions[0].fields))
    }
    bound_cache: dict[tuple[int, ...], int | None] = {}

    def lower_bound(state: tuple[int, ...]) -> int | None:
        if state in bound_cache:
            return bound_cache[state]
        bounds = []
        for offset, (assignment, rule) in enumerate(
            zip(candidate.assignments, rules, strict=True)
        ):
            current = state[offset]
            kind = rule["kind"]
            if kind == "UNCONSTRAINED":
                bounds.append(0)
                continue
            if kind == "EQUAL":
                if current != rule["value"]:
                    bound_cache[state] = None
                    return None
                bounds.append(0)
                continue
            expression = assignment["expression"]
            if expression[0] != "E07":
                bounds.append(0)
                continue
            increments = action_values[expression[2][2][1]]
            if kind == "AT_LEAST":
                distance = max(0, rule["value"] - current)
                maximum = max(increments)
            elif kind == "AT_MOST":
                distance = max(0, current - rule["value"])
                maximum = max(-value for value in increments)
            else:
                distance = min(abs(current - value) for value in rule["values"])
                maximum = max(abs(value) for value in increments)
            bounds.append(
                0
                if distance == 0
                else ceil(distance / maximum)
                if maximum > 0
                else maximum_depth + 1
            )
        result = max(bounds, default=0)
        bound_cache[state] = result
        return result

    initial_bound = lower_bound(initial)
    if initial_bound is None or initial_bound > maximum_depth:
        _fail("V115 compiled factor program found no support-feasible continuation")
    frontier = [(initial_bound, 0, initial)]
    best_depth = {initial: 0}
    predecessor: dict[tuple[int, ...], tuple[tuple[int, ...], int] | None] = {
        initial: None
    }
    terminal = None
    new_evaluations = reused_evaluations = 0
    while frontier:
        _priority, depth, state = heapq.heappop(frontier)
        if depth != best_depth[state]:
            continue
        if successor._terminal_match(state, rules):  # noqa: SLF001
            terminal = state
            break
        if depth == maximum_depth:
            continue
        for action in actions:
            if state == initial and action.key not in legal:
                continue
            key = (state, action.key)
            successors = branch_cache.get(key)
            if successors is None:
                successors = partial_factor_successor_projections_v15(
                    candidate, state, action
                )
                branch_cache[key] = successors
                new_evaluations += len(successors)
            else:
                reused_evaluations += len(successors)
            for next_state in successors:
                if next_state == state:
                    continue
                bound = lower_bound(next_state)
                next_depth = depth + 1
                if (
                    bound is None
                    or next_depth + bound > maximum_depth
                    or next_depth
                    >= best_depth.get(next_state, maximum_depth + 1)
                ):
                    continue
                best_depth[next_state] = next_depth
                predecessor[next_state] = (state, action.key)
                heapq.heappush(
                    frontier,
                    (next_depth + bound, next_depth, next_state),
                )
    if terminal is None:
        _fail("V115 compiled factor program found no support-feasible continuation")
    actions_out = []
    cursor = terminal
    while predecessor[cursor] is not None:
        parent, key = predecessor[cursor]
        actions_out.append(key)
        cursor = parent
    actions_out.reverse()
    return {
        "schema": "acfqp.generic_partial_factor_receding_plan.v15",
        "candidate_id": candidate.public_document["candidate_id"],
        "known_factor_target_columns": [
            row["target_column"] for row in candidate.assignments
        ],
        "unknown_residual_target_columns": candidate.public_document[
            "unknown_residual_target_columns"
        ],
        "terminal_projection_rule": [dict(row) for row in rules],
        "rejected_accepting_projection_count": 0,
        "selected_support_feasible_depth": len(actions_out),
        "action_keys": actions_out,
        "projected_planning_compute_events": new_evaluations,
        "matched_uncached_projected_planning_compute_events": (
            new_evaluations + reused_evaluations
        ),
        "projected_branch_cache_hit_count": reused_evaluations,
        "projected_branch_cache_entry_count": len(branch_cache),
        "stochastic_support_branch_receding_semantics": True,
        "robust_all_branches_completion_claimed": False,
        "finite_worst_case_completion_claimed": False,
        "ground_transition_accessed_during_abstract_search": False,
        "complete_world_model_claimed": False,
    }


def _plan_with_branch_cache(
    state: IncrementalAbstractSuccessorStateV113,
    candidate: PartialFactorCandidateV15,
    catalogue: tuple[Any, ...],
    initial_raw_state: tuple[int, ...],
    exact_legal_action_keys: tuple[int, ...],
    branch_cache: dict[tuple[tuple[int, ...], int], tuple[tuple[int, ...], ...]],
    *,
    legality_support_source: str,
    legality_failure_index: int | None,
    maximum_depth: int,
) -> dict[str, Any]:
    model, rules = successor._verify_state(state, candidate, catalogue)  # noqa: SLF001
    catalogue_keys = {action.key for action in catalogue}
    if (
        type(initial_raw_state) is not tuple
        or type(exact_legal_action_keys) is not tuple
        or not exact_legal_action_keys
        or len(set(exact_legal_action_keys)) != len(exact_legal_action_keys)
        or any(
            type(key) is not int or key not in catalogue_keys
            for key in exact_legal_action_keys
        )
        or legality_support_source
        not in (
            "PRELOADED_EXACT_LEGALITY_SUPPORT",
            "CERTIFICATE_LOCAL_LEGALITY_AFTER_FAILURE",
            "CERTIFICATE_LOCAL_LEGALITY_FROM_TRANSITION_AFTER_FAILURE",
        )
        or (
            legality_support_source == "PRELOADED_EXACT_LEGALITY_SUPPORT"
            and legality_failure_index is not None
        )
        or (
            legality_support_source != "PRELOADED_EXACT_LEGALITY_SUPPORT"
            and (
                type(legality_failure_index) is not int
                or legality_failure_index < 0
            )
        )
        or maximum_depth <= 0
    ):
        _fail("V115 compiled planner inventory changed")
    initial = successor._initial_projected_state(  # noqa: SLF001
        candidate, initial_raw_state
    )
    legal = frozenset(exact_legal_action_keys)
    try:
        plan = successor._observation_graph_plan(  # noqa: SLF001
            model, rules, initial, legal, candidate
        )
        source = "OBSERVATION_QUOTIENT_GRAPH"
    except successor.GenericIncrementalAbstractSuccessorV113Error:
        plan = _program_plan_with_branch_cache(
            candidate,
            catalogue,
            rules,
            initial,
            legal,
            branch_cache,
            maximum_depth=maximum_depth,
        )
        source = "COMPILED_FACTOR_PROGRAM_FALLBACK"
    actions = plan.get("action_keys")
    if type(actions) is not list or not actions or actions[0] not in legal:
        _fail("V115 compiled planner action path changed")
    shield = shield_abstract_action_order_v99(
        abstract_proposal=(actions[0],),
        partial_proposal=(actions[0],),
        legal_action_keys=exact_legal_action_keys,
    )
    payload = {
        "schema": "acfqp.generic_legality_conditioned_quotient_plan.v106",
        "quotient_graph_id": model["quotient_graph_id"],
        "partial_candidate_id": candidate.public_document["candidate_id"],
        "planning_source": source,
        "initial_action_key": actions[0],
        "projected_action_path": list(actions),
        "abstract_support_branch_evaluations": plan[
            "projected_planning_compute_events"
        ],
        "embedded_projected_plan": copy.deepcopy(plan),
        "exact_legal_action_keys_at_initial_state": list(
            exact_legal_action_keys
        ),
        "legality_support_source": legality_support_source,
        "legality_failure_index": legality_failure_index,
        "agreement_shield_receipt": shield,
        "initial_illegal_actions_forbidden_in_abstract_search": True,
        "ground_legality_used_only_after_existing_support_or_failed_certificate": True,
        "ground_transition_accessed_during_abstract_search": False,
        "query_local_exact_overlay_remains_only_safety_authority": True,
        "complete_ground_world_model_claimed": False,
    }
    return {
        **payload,
        "legality_conditioned_quotient_plan_id": hashlib.sha256(
            successor._V106_PLAN_DOMAIN + canonical_json_bytes(payload)  # noqa: SLF001
        ).hexdigest(),
    }


def _projected_program_memo_orderer(
    adapter: Any,
    candidate: PartialFactorCandidateV15,
    state: IncrementalAbstractSuccessorStateV113,
    cache: dict[tuple[Any, ...], list[dict[str, Any]]],
    entries: dict[str, dict[str, Any]],
    reverse_index: dict[tuple[int, ...], set[str]],
    stats: dict[str, Any],
    *,
    maximum_abstract_depth: int,
):
    v109 = previous.v110.previous
    model = state.model
    rules = state.terminal_rules
    rule_sha = hashlib.sha256(canonical_json_bytes(list(rules))).hexdigest()
    program_cache = stats.setdefault("_program_cache", {})
    branch_cache = stats.setdefault("_program_branch_cache", {})
    prior_state_id = stats.get("_program_cache_successor_state_id")
    if prior_state_id is not None and prior_state_id != state.state_id:
        program_cache.clear()
        branch_cache.clear()
    stats["_program_cache_successor_state_id"] = state.state_id

    def order(
        raw: tuple[int, ...],
        legal: tuple[int, ...],
        legality_support_source: str,
        legality_failure_index: int | None,
    ) -> Mapping[str, Any] | None:
        stats["calls"] += 1
        key = v109._stable_key(candidate, raw, legal)  # noqa: SLF001
        cached = cache.get(key, [])
        if cached:
            entry = cached[0]
            if entry["authorized_quotient_graph_id"] != model["quotient_graph_id"]:
                _fail("V115 graph cache entry lacks current model authorization")
            stats["hits"] += 1
            chain = copy.deepcopy(entry["epoch_authorization_chain"])
            validation = {
                "dependency_receipt_id": entry["dependency"]["dependency_receipt_id"],
                "source_quotient_graph_id": entry["dependency"][
                    "source_quotient_graph_id"
                ],
                "current_quotient_graph_id": model["quotient_graph_id"],
                "dependency_validation_check_count": 0,
                "source_action_path_remains_valid_under_current_dependency_slice": True,
                "full_current_quotient_graph_identity_required": False,
                "epoch_transition_receipt_id": chain[-1][
                    "epoch_transition_receipt_id"
                ],
                "epoch_authorization_chain": chain,
                "per_hit_dependency_rescan_performed": False,
            }
            return v109._revalidated_plan(  # noqa: SLF001
                source_plan=entry["source_plan"],
                dependency_receipt=entry["dependency"],
                validation=validation,
                current_model=model,
                legal=legal,
                legality_support_source=legality_support_source,
                legality_failure_index=legality_failure_index,
            )
        program_entry = program_cache.get(key)
        if program_entry is not None:
            if (
                program_entry["successor_state_id"] != state.state_id
                or program_entry["terminal_rule_sha256"] != rule_sha
            ):
                _fail("V115 program memo lacks exact compiled-state authorization")
            stats["hits"] += 1
            return _memoized_program_plan(
                source_plan=program_entry["source_plan"],
                source_successor_state_id=program_entry["successor_state_id"],
                current_successor_state_id=state.state_id,
                quotient_graph_id=model["quotient_graph_id"],
                terminal_rule_sha256=rule_sha,
                legal=legal,
                legality_support_source=legality_support_source,
                legality_failure_index=legality_failure_index,
            )
        stats["misses"] += 1
        try:
            plan = _plan_with_branch_cache(
                state,
                candidate,
                adapter.catalogue,
                raw,
                legal,
                branch_cache,
                legality_support_source=legality_support_source,
                legality_failure_index=legality_failure_index,
                maximum_depth=maximum_abstract_depth,
            )
        except Exception as error:
            if not error.__class__.__module__.startswith("acfqp.generic_"):
                raise
            return None
        stats["actual_new_compute_events"] += plan[
            "abstract_support_branch_evaluations"
        ]
        if plan["planning_source"] == "OBSERVATION_QUOTIENT_GRAPH":
            dependency = build_quotient_plan_dependency_receipt_v109(
                source_model=model,
                source_plan=plan,
                initial_projected_state=v109._projected_state(candidate, raw),  # noqa: SLF001
            )
            identity = dependency["dependency_receipt_id"]
            entry = {
                "source_plan": copy.deepcopy(plan),
                "dependency": dependency,
                "authorized_quotient_graph_id": model["quotient_graph_id"],
                "epoch_authorization_chain": [],
            }
            cache.setdefault(key, []).append(entry)
            entries[identity] = entry
            for row in dependency["ordered_bfs_dependency_rows"]:
                reverse_index[tuple(row["projected_state"])].add(identity)
        elif plan["planning_source"] == "COMPILED_FACTOR_PROGRAM_FALLBACK":
            program_cache[key] = {
                "source_plan": copy.deepcopy(plan),
                "successor_state_id": state.state_id,
                "terminal_rule_sha256": rule_sha,
            }
        return copy.deepcopy(plan)

    return order


def _run_program_memoized_base_sequence(
    adapter: Any,
    candidate: PartialFactorCandidateV15,
    observed_rows: tuple[Any, ...],
    acquisition_ground_support_labels: int,
    *,
    episode_indices: tuple[int, ...],
    maximum_abstract_depth: int,
    maximum_execution_steps: int,
    maximum_incremental_certificate_ground_support_labels: int,
) -> dict[str, Any]:
    namespace = dict(previous.__dict__)
    namespace["_incremental_indexed_orderer"] = _projected_program_memo_orderer
    function = previous.run_incremental_abstract_successor_sequence_v113
    cloned = FunctionType(
        function.__code__,
        namespace,
        name=function.__name__,
        argdefs=function.__defaults__,
        closure=function.__closure__,
    )
    cloned.__kwdefaults__ = function.__kwdefaults__
    return cloned(
        adapter,
        candidate,
        observed_rows,
        acquisition_ground_support_labels,
        episode_indices=episode_indices,
        maximum_abstract_depth=maximum_abstract_depth,
        maximum_execution_steps=maximum_execution_steps,
        maximum_incremental_certificate_ground_support_labels=(
            maximum_incremental_certificate_ground_support_labels
        ),
    )


def run_projected_program_memo_sequence_v115(
    adapter: Any,
    candidate: PartialFactorCandidateV15,
    observed_rows: tuple[Any, ...],
    acquisition_ground_support_labels: int,
    *,
    episode_indices: tuple[int, ...],
    maximum_abstract_depth: int,
    maximum_execution_steps: int,
    maximum_incremental_certificate_ground_support_labels: int,
) -> dict[str, Any]:
    base = _run_program_memoized_base_sequence(
        adapter,
        candidate,
        observed_rows,
        acquisition_ground_support_labels,
        episode_indices=episode_indices,
        maximum_abstract_depth=maximum_abstract_depth,
        maximum_execution_steps=maximum_execution_steps,
        maximum_incremental_certificate_ground_support_labels=(
            maximum_incremental_certificate_ground_support_labels
        ),
    )
    plans = [
        row["abstract_plan"]
        for episode in base["episodes"]
        for row in episode["abstract_plan_receipts"]
    ]
    memo_hits = sum(
        row["planning_source"] == "COMPILED_FACTOR_PROGRAM_MEMOIZED"
        for row in plans
    )
    fallback_sources = sum(
        row["planning_source"] == "COMPILED_FACTOR_PROGRAM_FALLBACK"
        for row in plans
    )
    branch_hits = sum(
        row.get("embedded_projected_plan", {}).get(
            "projected_branch_cache_hit_count", 0
        )
        for row in plans
    )
    uncached_compute = sum(
        row.get("embedded_projected_plan", {}).get(
            "matched_uncached_projected_planning_compute_events",
            row["abstract_support_branch_evaluations"],
        )
        for row in plans
    )
    payload = {
        "schema": "acfqp.generic_projected_program_memo_sequence.v115",
        "family": adapter.family,
        "seed": adapter.seed,
        "episode_indices": list(episode_indices),
        "partial_candidate_id": candidate.public_document["candidate_id"],
        "program_memoized_base_sequence": base,
        "program_memoized_base_sequence_id": base["sequence_id"],
        "program_fallback_source_plan_count": fallback_sources,
        "projected_program_memo_hit_count": memo_hits,
        "projected_program_branch_cache_hit_count": branch_hits,
        "actual_new_abstract_planning_compute_events": base[
            "actual_new_abstract_planning_compute_events"
        ],
        "matched_uncached_abstract_planning_compute_events": uncached_compute,
        "planning_compute_events_avoided_by_program_memo": uncached_compute
        - base["actual_new_abstract_planning_compute_events"],
        "lifetime_target_ground_support_labels": base[
            "lifetime_target_ground_support_labels"
        ],
        "execution_step_count": base["execution_step_count"],
        "projected_state_and_exact_legal_set_cache_keyed": True,
        "program_memo_invalidated_on_compiled_successor_state_change": True,
        "ground_transition_accessed_during_program_memo_reuse": False,
        "query_local_exact_overlay_exclusively_discharges_safety": True,
        "compiled_program_memo_used_as_safety_authority": False,
        "complete_ground_world_model_synthesized": False,
        "official_execution_allowed": False,
    }
    return {
        **payload,
        "sequence_id": domains.extension_content_id_v115(
            domains.CONSTRUCTION_K7_PROJECTED_PROGRAM_MEMO_SEQUENCE_V115_DOMAIN,
            payload,
        ),
    }


__all__ = ("run_projected_program_memo_sequence_v115",)
