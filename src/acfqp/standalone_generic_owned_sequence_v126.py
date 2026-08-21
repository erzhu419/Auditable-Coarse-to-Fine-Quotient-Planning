"""Own the generic-model episode loop without V113/V119 sequence orchestration."""

from __future__ import annotations

from collections import defaultdict
import copy
import hashlib
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v126 as domains
from acfqp import generic_dependency_revalidated_quotient_sequence_v109 as v109
from acfqp import generic_identity_short_circuited_epoch_sequence_v111 as v111
from acfqp import generic_projected_program_memo_sequence_v115 as v115
from acfqp import generic_dependency_derived_program_branch_sequence_v117 as v117
from acfqp.generic_abstract_partial_agreement_shield_v99 import shield_abstract_action_order_v99
from acfqp.generic_atomic_expression_world_model_v4 import FlatRawActionV4
from acfqp.generic_compiled_factor_planner_v122 import (
    derive_generic_terminal_rules_v122,
    plan_generic_factor_program_v122,
)
from acfqp.generic_incremental_abstract_successor_v113 import (
    GenericIncrementalAbstractSuccessorV113Error,
    _V106_PLAN_DOMAIN,
    _initial_projected_state,
    _observation_graph_plan,
)
from acfqp.generic_legality_conditioned_certificate_engine_v106 import run_legality_conditioned_certificate_episode_v106
from acfqp.generic_partial_factor_proposal_v15 import PartialFactorCandidateV15
from acfqp.generic_quotient_plan_dependency_receipt_v109 import build_quotient_plan_dependency_receipt_v109
from acfqp.phase3e_ids import canonical_json_bytes
from acfqp.standalone_generic_model_epoch_v125 import (
    StandaloneGenericModelEpochStateV125,
    advance_standalone_generic_model_v125,
    initialize_standalone_generic_model_v125,
    verify_standalone_generic_model_full_rebuild_v125,
    verify_standalone_generic_model_state_v125,
)


class StandaloneGenericOwnedSequenceV126Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise StandaloneGenericOwnedSequenceV126Error(message)


def _plan_with_branch_cache_v126(
    state: StandaloneGenericModelEpochStateV125,
    candidate: PartialFactorCandidateV15,
    catalogue: tuple[FlatRawActionV4, ...],
    initial_raw_state: tuple[int, ...],
    exact_legal_action_keys: tuple[int, ...],
    branch_cache: dict[tuple[tuple[int, ...], int], tuple[tuple[int, ...], ...]],
    *,
    legality_support_source: str,
    legality_failure_index: int | None,
    maximum_depth: int,
) -> dict[str, Any]:
    model, matched_rules = verify_standalone_generic_model_state_v125(state, candidate, catalogue)
    generic_rules = derive_generic_terminal_rules_v122(
        candidate, model["projected_edge_rows"], model["projected_terminal_rows"]
    )
    if generic_rules != matched_rules:
        _fail("V126 generic terminal rule differs from the standalone model state")
    keys = {action.key for action in catalogue}
    if (
        type(initial_raw_state) is not tuple
        or type(exact_legal_action_keys) is not tuple
        or not exact_legal_action_keys
        or len(set(exact_legal_action_keys)) != len(exact_legal_action_keys)
        or any(type(key) is not int or key not in keys for key in exact_legal_action_keys)
        or legality_support_source not in (
            "PRELOADED_EXACT_LEGALITY_SUPPORT",
            "CERTIFICATE_LOCAL_LEGALITY_AFTER_FAILURE",
            "CERTIFICATE_LOCAL_LEGALITY_FROM_TRANSITION_AFTER_FAILURE",
        )
        or (legality_support_source == "PRELOADED_EXACT_LEGALITY_SUPPORT" and legality_failure_index is not None)
        or (legality_support_source != "PRELOADED_EXACT_LEGALITY_SUPPORT" and (type(legality_failure_index) is not int or legality_failure_index < 0))
        or maximum_depth <= 0
    ):
        _fail("V126 legality-conditioned planner inventory changed")
    initial = _initial_projected_state(candidate, initial_raw_state)
    legal = frozenset(exact_legal_action_keys)
    try:
        plan = _observation_graph_plan(model, generic_rules, initial, legal, candidate)
        source = "OBSERVATION_QUOTIENT_GRAPH"
    except GenericIncrementalAbstractSuccessorV113Error:
        plan = plan_generic_factor_program_v122(
            candidate,
            catalogue,
            generic_rules,
            initial,
            legal,
            branch_cache,
            maximum_depth=maximum_depth,
        )
        source = "COMPILED_FACTOR_PROGRAM_FALLBACK"
    actions = plan.get("action_keys")
    if type(actions) is not list or not actions or actions[0] not in legal:
        _fail("V126 planner action path changed")
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
        "abstract_support_branch_evaluations": plan["projected_planning_compute_events"],
        "embedded_projected_plan": copy.deepcopy(plan),
        "exact_legal_action_keys_at_initial_state": list(exact_legal_action_keys),
        "legality_support_source": legality_support_source,
        "legality_failure_index": legality_failure_index,
        "agreement_shield_receipt": shield,
        "generic_terminal_rules_equal_retained_matched_compiler": True,
        "generic_factor_program_execution_adapter_used": source == "COMPILED_FACTOR_PROGRAM_FALLBACK",
        "legacy_shape_specific_planner_execution_adapter_called": False,
        "initial_illegal_actions_forbidden_in_abstract_search": True,
        "ground_legality_used_only_after_existing_support_or_failed_certificate": True,
        "ground_transition_accessed_during_abstract_search": False,
        "query_local_exact_overlay_remains_only_safety_authority": True,
        "complete_ground_world_model_claimed": False,
    }
    return {
        **payload,
        "legality_conditioned_quotient_plan_id": hashlib.sha256(
            _V106_PLAN_DOMAIN + canonical_json_bytes(payload)
        ).hexdigest(),
    }


def _owned_orderer(
    adapter: Any,
    candidate: PartialFactorCandidateV15,
    state: StandaloneGenericModelEpochStateV125,
    cache: dict[tuple[Any, ...], list[dict[str, Any]]],
    entries: dict[str, dict[str, Any]],
    reverse_index: dict[tuple[int, ...], set[str]],
    stats: dict[str, Any],
    *,
    maximum_abstract_depth: int,
):
    model = state.model
    rules = state.terminal_rules
    rule_sha = hashlib.sha256(canonical_json_bytes(list(rules))).hexdigest()
    program_cache = stats.setdefault("_program_cache", {})
    branch_cache = stats.setdefault("_program_branch_cache", {})
    prior_state_id = stats.get("_program_cache_successor_state_id")
    if prior_state_id is not None and prior_state_id != state.state_id:
        program_cache.clear()
        stats["_cross_epoch_retained_branch_entry_count"] = stats.get("_cross_epoch_retained_branch_entry_count", 0) + len(branch_cache)
    stats["_program_cache_successor_state_id"] = state.state_id
    current_receipt = v117.derive_program_branch_dependency_receipt_v117(candidate, adapter.catalogue)
    prior_receipt = stats.get("_program_branch_dependency_receipt")
    decision = v117.program_branch_cache_retention_decision_v117(prior_receipt, current_receipt)
    if decision["invalidate_program_branch_cache"]:
        branch_cache.clear()
    stats["_program_branch_dependency_receipt"] = copy.deepcopy(current_receipt)

    def order(raw, legal, legality_support_source, legality_failure_index):
        stats["calls"] += 1
        key = v109._stable_key(candidate, raw, legal)  # noqa: SLF001
        cached = cache.get(key, [])
        if cached:
            entry = cached[0]
            if entry["authorized_quotient_graph_id"] != model["quotient_graph_id"]:
                _fail("V126 graph cache entry lacks current authorization")
            stats["hits"] += 1
            chain = copy.deepcopy(entry["epoch_authorization_chain"])
            if not chain:
                if entry["dependency"]["source_quotient_graph_id"] != model["quotient_graph_id"] or entry["source_successor_state_id"] != state.state_id:
                    _fail("V126 zero-transition cache hit lacks genesis identity")
                stats["_same_epoch_genesis_authorized_hit_count"] = stats.get("_same_epoch_genesis_authorized_hit_count", 0) + 1
                return v115._memoized_program_plan(  # noqa: SLF001
                    source_plan=entry["source_plan"],
                    source_successor_state_id=entry["source_successor_state_id"],
                    current_successor_state_id=state.state_id,
                    quotient_graph_id=model["quotient_graph_id"],
                    terminal_rule_sha256=rule_sha,
                    legal=legal,
                    legality_support_source=legality_support_source,
                    legality_failure_index=legality_failure_index,
                )
            validation = {
                "dependency_receipt_id": entry["dependency"]["dependency_receipt_id"],
                "source_quotient_graph_id": entry["dependency"]["source_quotient_graph_id"],
                "current_quotient_graph_id": model["quotient_graph_id"],
                "dependency_validation_check_count": 0,
                "source_action_path_remains_valid_under_current_dependency_slice": True,
                "full_current_quotient_graph_identity_required": False,
                "epoch_transition_receipt_id": chain[-1]["epoch_transition_receipt_id"],
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
            if program_entry["successor_state_id"] != state.state_id or program_entry["terminal_rule_sha256"] != rule_sha:
                _fail("V126 program memo lacks exact compiled-state authorization")
            stats["hits"] += 1
            return v115._memoized_program_plan(  # noqa: SLF001
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
            plan = _plan_with_branch_cache_v126(
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
            if not error.__class__.__module__.startswith("acfqp.generic_") and not isinstance(error, StandaloneGenericOwnedSequenceV126Error):
                raise
            return None
        stats["actual_new_compute_events"] += plan["abstract_support_branch_evaluations"]
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
                "source_successor_state_id": state.state_id,
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


def run_standalone_generic_owned_sequence_v126(
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
    if (
        type(candidate) is not PartialFactorCandidateV15
        or type(observed_rows) is not tuple
        or not observed_rows
        or v109._group_count(observed_rows) != acquisition_ground_support_labels  # noqa: SLF001
        or type(episode_indices) is not tuple
        or len(episode_indices) < 2
        or len(set(episode_indices)) != len(episode_indices)
        or maximum_abstract_depth <= 0
        or maximum_execution_steps <= 0
        or maximum_incremental_certificate_ground_support_labels <= 0
    ):
        _fail("V126 owned sequence inventory changed")
    dependency_receipt = v117.derive_program_branch_dependency_receipt_v117(candidate, adapter.catalogue)
    persistent_rows = v109._deduplicate(observed_rows)  # noqa: SLF001
    state, bootstrap = initialize_standalone_generic_model_v125(candidate, persistent_rows, adapter.catalogue)
    bootstrap_match = verify_standalone_generic_model_full_rebuild_v125(
        state, candidate, persistent_rows, adapter.catalogue, update_receipt=None
    )
    cache: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
    entries: dict[str, dict[str, Any]] = {}
    reverse_index: dict[tuple[int, ...], set[str]] = defaultdict(set)
    stats: dict[str, Any] = {"calls": 0, "hits": 0, "misses": 0, "actual_new_compute_events": 0}
    episodes = []
    models_before = []
    models_after = []
    actual_receipts = []
    update_receipts = []
    match_receipts = []
    epoch_receipts = []
    paid = 0
    identity_checks = diff_checks = index_lookups = invalidations = short_circuits = 0
    incremental_update_events = full_rebuild_update_events = 0
    for offset, episode_index in enumerate(episode_indices):
        model = state.model
        rules = state.terminal_rules
        before_stats = dict(stats)
        episode = run_legality_conditioned_certificate_episode_v106(
            adapter,
            candidate,
            persistent_rows,
            preloaded_acquisition_ground_support_labels=v109._group_count(persistent_rows),  # noqa: SLF001
            arm="V126_OWNED_STANDALONE_GENERIC_MODEL_ORDERING",
            abstract_orderer=_owned_orderer(
                adapter,
                candidate,
                state,
                cache,
                entries,
                reverse_index,
                stats,
                maximum_abstract_depth=maximum_abstract_depth,
            ),
            episode_index=episode_index,
            maximum_execution_steps=maximum_execution_steps,
            maximum_incremental_certificate_ground_support_labels=maximum_incremental_certificate_ground_support_labels,
        )
        actual = v109._actual_receipts(episode)  # noqa: SLF001
        incremental_labels = episode["incremental_certificate_local_ground_support_labels"]
        paid += incremental_labels
        new_rows = tuple(v109._row(document) for document in episode["raw_incremental_transition_rows"])  # noqa: SLF001
        persistent_rows = v109._deduplicate((*persistent_rows, *new_rows))  # noqa: SLF001
        next_state, update = advance_standalone_generic_model_v125(state, candidate, new_rows, adapter.catalogue)
        match = verify_standalone_generic_model_full_rebuild_v125(
            next_state, candidate, persistent_rows, adapter.catalogue, update_receipt=update
        )
        transition = None
        if offset + 1 < len(episode_indices):
            if model["quotient_graph_id"] != next_state.model["quotient_graph_id"] and not incremental_labels:
                _fail("V126 graph changed without certificate-local overlay")
            transition = v111._identity_short_circuited_transition(  # noqa: SLF001
                previous_model=model,
                current_model=next_state.model,
                previous_rules=rules,
                current_rules=next_state.terminal_rules,
                cache=cache,
                entries=entries,
                reverse_index=reverse_index,
            )
            epoch_receipts.append(copy.deepcopy(transition))
            identity_checks += transition["model_epoch_identity_checks"]
            diff_checks += transition["full_model_epoch_diff_checks"]
            index_lookups += transition["reverse_dependency_index_lookups"]
            invalidations += len(transition["invalidated_dependency_receipt_ids"])
            short_circuits += transition["identity_short_circuit_applied"]
        calls = stats["calls"] - before_stats["calls"]
        hits = stats["hits"] - before_stats["hits"]
        misses = stats["misses"] - before_stats["misses"]
        new_compute = stats["actual_new_compute_events"] - before_stats["actual_new_compute_events"]
        if calls != hits + misses or new_compute != episode["abstract_planning_compute_events"]:
            _fail("V126 planner memo accounting changed")
        incremental_update_events += update["incremental_compilation_events"]
        full_rebuild_update_events += match["matched_full_rebuild_compilation_events"]
        episodes.append(
            {
                **copy.deepcopy(episode),
                "quotient_graph_before_episode": copy.deepcopy(model),
                "standalone_model_state_id_before_episode": state.state_id,
                "standalone_model_update_after_episode": copy.deepcopy(update),
                "standalone_full_rebuild_match_after_episode": copy.deepcopy(match),
                "quotient_graph_after_episode": copy.deepcopy(next_state.model),
                "standalone_model_state_id_after_episode": next_state.state_id,
                "epoch_transition_after_episode": copy.deepcopy(transition),
                "actual_legality_conditioned_execution_receipts": actual,
                "actual_legality_conditioned_execution_receipt_count": len(actual),
                "quotient_proposal_admitted_execution_count": sum(row["quotient_proposal_admitted_to_real_action_order"] for row in actual),
                "chosen_action_matches_admitted_quotient_proposal_count": sum(row["chosen_action_matches_admitted_quotient_proposal"] for row in actual),
                "certificate_local_legality_plan_count": sum(row["legality_support_source"] in ("CERTIFICATE_LOCAL_LEGALITY_AFTER_FAILURE", "CERTIFICATE_LOCAL_LEGALITY_FROM_TRANSITION_AFTER_FAILURE") for row in actual),
                "epoch_indexed_orderer_call_count": calls,
                "epoch_authorized_cache_hit_count": hits,
                "epoch_cache_miss_count": misses,
                "actual_new_abstract_planning_compute_events": new_compute,
                "dependency_cache_entry_count_after_episode": len(entries),
                "new_certificate_labels_charged_this_episode": incremental_labels,
                "paid_certificate_labels_cumulative": paid,
                "persistent_exact_support_group_count_after_episode": v109._group_count(persistent_rows),  # noqa: SLF001
                "planner_raw_transition_argument_present": False,
            }
        )
        models_before.append(copy.deepcopy(model))
        models_after.append(copy.deepcopy(next_state.model))
        actual_receipts.extend(actual)
        update_receipts.append(copy.deepcopy(update))
        match_receipts.append(copy.deepcopy(match))
        state = next_state
    failures = [item for row in episodes for item in row["failed_certificates"]]
    distinctions = [item for row in episodes for item in row["local_distinctions"]]
    overlay = [row.to_document() for row in persistent_rows]
    dependency_maintenance = identity_checks + diff_checks + index_lookups
    plans = [row["abstract_plan"] for episode in episodes for row in episode["abstract_plan_receipts"]]
    uncached_compute = sum(row.get("embedded_projected_plan", {}).get("matched_uncached_projected_planning_compute_events", row["abstract_support_branch_evaluations"]) for row in plans)
    branch_hits = sum(row.get("embedded_projected_plan", {}).get("projected_branch_cache_hit_count", 0) for row in plans)
    genesis_hits = sum(row["planning_source"] == "COMPILED_FACTOR_PROGRAM_MEMOIZED" and row.get("source_successor_state_id") == row.get("current_successor_state_id") for row in plans)
    dependency_compute = len(episode_indices) * (len(dependency_receipt["compiled_factor_assignments"]) + len(dependency_receipt["canonical_action_catalogue"]))
    direct = sum(row["planning_source"] == "COMPILED_FACTOR_PROGRAM_FALLBACK" for row in plans)
    payload = {
        "schema": "acfqp.standalone_generic_owned_sequence.v126",
        "family": adapter.family,
        "seed": adapter.seed,
        "episode_indices": list(episode_indices),
        "partial_candidate_id": candidate.public_document["candidate_id"],
        "program_branch_dependency_receipt": dependency_receipt,
        "program_branch_dependency_receipt_id": dependency_receipt["dependency_receipt_id"],
        "dependency_receipt_rederivation_count": len(episode_indices),
        "dependency_derivation_compute_events": dependency_compute,
        "same_epoch_genesis_authorized_cache_hit_count": genesis_hits,
        "program_branch_cache_hit_count": branch_hits,
        "initial_acquisition_ground_support_labels_paid_once": acquisition_ground_support_labels,
        "bootstrap_receipt": bootstrap,
        "bootstrap_full_rebuild_match": bootstrap_match,
        "quotient_models_before_each_episode": models_before,
        "quotient_models_after_each_episode": models_after,
        "standalone_model_update_receipts": update_receipts,
        "standalone_full_rebuild_match_receipts": match_receipts,
        "model_epoch_transition_receipts": epoch_receipts,
        "episodes": episodes,
        "all_actual_legality_conditioned_execution_receipts": actual_receipts,
        "actual_legality_conditioned_execution_receipt_count": len(actual_receipts),
        "execution_step_count": sum(row["execution_steps"] for row in episodes),
        "quotient_proposal_admitted_execution_count": sum(row["quotient_proposal_admitted_to_real_action_order"] for row in actual_receipts),
        "chosen_action_matches_admitted_quotient_proposal_count": sum(row["chosen_action_matches_admitted_quotient_proposal"] for row in actual_receipts),
        "certificate_local_legality_plan_count": sum(row["legality_support_source"] in ("CERTIFICATE_LOCAL_LEGALITY_AFTER_FAILURE", "CERTIFICATE_LOCAL_LEGALITY_FROM_TRANSITION_AFTER_FAILURE") for row in actual_receipts),
        "epoch_indexed_orderer_call_count": stats["calls"],
        "epoch_authorized_cache_hit_count": stats["hits"],
        "epoch_cache_miss_count": stats["misses"],
        "actual_new_abstract_planning_compute_events": stats["actual_new_compute_events"],
        "matched_uncached_abstract_planning_compute_events": uncached_compute,
        "planning_compute_events_avoided_against_uncached": uncached_compute - stats["actual_new_compute_events"],
        "model_epoch_identity_checks": identity_checks,
        "full_model_epoch_diff_checks": diff_checks,
        "reverse_dependency_index_lookups": index_lookups,
        "dependency_cache_entry_invalidations": invalidations,
        "identity_short_circuit_count": short_circuits,
        "dependency_maintenance_events": dependency_maintenance,
        "incremental_model_update_compilation_events": incremental_update_events,
        "matched_full_rebuild_update_compilation_events": full_rebuild_update_events,
        "model_compilation_events_avoided_against_full_rebuild": full_rebuild_update_events - incremental_update_events,
        "bootstrap_compilation_events_separate": bootstrap["bootstrap_compilation_events"],
        "matched_control_compilation_not_charged_to_incremental_arm": True,
        "all_model_successors_exactly_equal_full_generic_rebuild": all(row["model_bytes_exactly_equal_full_generic_rebuild"] and row["terminal_projection_rule_exactly_equal_full_rebuild"] for row in match_receipts),
        "direct_generic_factor_program_plan_count": direct,
        "planner_consumed_compiled_successor_without_raw_transition_argument": all(row["planner_raw_transition_argument_present"] is False for row in episodes),
        "certificate_ground_support_labels_paid_once": paid,
        "lifetime_target_ground_support_labels": acquisition_ground_support_labels + paid,
        "persistent_exact_overlay_rows": overlay,
        "persistent_exact_overlay_sha256": hashlib.sha256(canonical_json_bytes(overlay)).hexdigest(),
        "persistent_exact_support_group_count": v109._group_count(persistent_rows),  # noqa: SLF001
        "all_failed_certificates": failures,
        "all_local_distinctions": distinctions,
        "every_new_ground_query_followed_a_failed_certificate": all(row.get("ground_query_performed_before_failure") is False for row in failures) and all(row.get("query_after_failed_certificate") is True for row in distinctions),
        "owned_episode_loop_implementation_present": True,
        "standalone_v125_state_carrier_verified": True,
        "retained_v113_state_carrier_present": False,
        "retained_v113_sequence_orchestration_present": False,
        "retained_v119_sequence_orchestration_present": False,
        "retained_v119_ordering_primitives_present": True,
        "query_local_exact_overlay_exclusively_discharges_safety": True,
        "compiled_abstract_model_used_only_to_order_actions": True,
        "compiled_model_cache_or_receipt_used_as_safety_authority": False,
        "global_lumpability_claimed": False,
        "complete_ground_world_model_synthesized": False,
        "official_execution_allowed": False,
    }
    return {
        **payload,
        "sequence_id": domains.extension_content_id_v126(
            domains.CONSTRUCTION_K7_STANDALONE_GENERIC_OWNED_SEQUENCE_V126_DOMAIN,
            payload,
        ),
    }


__all__ = ("run_standalone_generic_owned_sequence_v126",)
