"""Content-identity short circuit over V110 epoch dependency invalidation."""

from __future__ import annotations

import copy
from collections import defaultdict
import hashlib
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v111 as domains
from acfqp import generic_epoch_indexed_quotient_sequence_v110 as previous
from acfqp.generic_legality_conditioned_certificate_engine_v106 import (
    run_legality_conditioned_certificate_episode_v106,
)
from acfqp.generic_observation_quotient_graph_v105 import (
    compile_observation_quotient_graph_v105,
)
from acfqp.generic_partial_factor_proposal_v15 import PartialFactorCandidateV15
from acfqp.phase3e_ids import canonical_json_bytes


class GenericIdentityShortCircuitedEpochSequenceV111Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise GenericIdentityShortCircuitedEpochSequenceV111Error(message)


def _identity_short_circuited_transition(
    *,
    previous_model: Mapping[str, Any],
    current_model: Mapping[str, Any],
    previous_rules: tuple[Mapping[str, Any], ...],
    current_rules: tuple[Mapping[str, Any], ...],
    cache: dict[tuple[Any, ...], list[dict[str, Any]]],
    entries: dict[str, dict[str, Any]],
    reverse_index: dict[tuple[int, ...], set[str]],
) -> dict[str, Any]:
    same_identity = (
        previous_model["quotient_graph_id"] == current_model["quotient_graph_id"]
    )
    identity_checks = 1
    all_ids = set(entries)
    if same_identity:
        changed: tuple[tuple[int, ...], ...] = ()
        changed_rows: list[dict[str, Any]] = []
        rules_changed = False
        diff_checks = 0
        lookups = 0
        invalidated: set[str] = set()
        retained = set(all_ids)
    else:
        before = previous._adjacency(previous_model)  # noqa: SLF001
        after = previous._adjacency(current_model)  # noqa: SLF001
        states = tuple(sorted(set(before) | set(after)))
        changed = tuple(
            state
            for state in states
            if before.get(state, ()) != after.get(state, ())
        )
        rules_changed = list(previous_rules) != list(current_rules)
        diff_checks = sum(
            1 + len(before.get(state, ())) + len(after.get(state, ()))
            for state in states
        ) + len(previous_rules) + len(current_rules)
        if rules_changed:
            invalidated = set(all_ids)
            lookups = 0
        else:
            invalidated = set()
            for state in changed:
                invalidated.update(reverse_index.get(state, set()))
            lookups = len(changed)
        retained = all_ids - invalidated
        changed_rows = [
            {
                "projected_state": list(state),
                "previous_outgoing_edges": [
                    {"action_key": key, "projected_post": list(post)}
                    for key, post in before.get(state, ())
                ],
                "current_outgoing_edges": [
                    {"action_key": key, "projected_post": list(post)}
                    for key, post in after.get(state, ())
                ],
            }
            for state in changed
        ]
    payload = {
        "schema": "acfqp.identity_short_circuited_quotient_model_epoch_transition.v111",
        "previous_quotient_graph_id": previous_model["quotient_graph_id"],
        "current_quotient_graph_id": current_model["quotient_graph_id"],
        "quotient_graph_identity_equal": same_identity,
        "identity_short_circuit_applied": same_identity,
        "previous_terminal_projection_rule": [dict(row) for row in previous_rules],
        "current_terminal_projection_rule": [dict(row) for row in current_rules],
        "terminal_projection_rule_changed": rules_changed,
        "changed_projected_state_rows": changed_rows,
        "changed_projected_state_count": len(changed_rows),
        "cache_entry_ids_before_transition": sorted(all_ids),
        "invalidated_dependency_receipt_ids": sorted(invalidated),
        "retained_dependency_receipt_ids": sorted(retained),
        "model_epoch_identity_checks": identity_checks,
        "full_model_epoch_diff_checks": diff_checks,
        "reverse_dependency_index_lookups": lookups,
        "same_content_address_skips_full_graph_and_dependency_scan": same_identity,
        "changed_content_address_uses_exact_outgoing_edge_and_terminal_rule_delta": not same_identity,
        "unaffected_dependency_receipts_retained_without_per_hit_rescan": True,
        "epoch_transition_is_ordering_evidence_not_safety_authority": True,
    }
    receipt = {
        **payload,
        "epoch_transition_receipt_id": domains.extension_content_id_v111(
            domains.CONSTRUCTION_K7_IDENTITY_SHORT_CIRCUITED_EPOCH_TRANSITION_V111_DOMAIN,
            payload,
        ),
    }
    for key in tuple(cache):
        cache[key] = [
            entry
            for entry in cache[key]
            if entry["dependency"]["dependency_receipt_id"] not in invalidated
        ]
        if not cache[key]:
            del cache[key]
    for identity in invalidated:
        entry = entries.pop(identity)
        for row in entry["dependency"]["ordered_bfs_dependency_rows"]:
            state = tuple(row["projected_state"])
            reverse_index[state].discard(identity)
            if not reverse_index[state]:
                del reverse_index[state]
    for identity in retained:
        entry = entries[identity]
        entry["authorized_quotient_graph_id"] = current_model["quotient_graph_id"]
        entry["epoch_authorization_chain"].append(copy.deepcopy(receipt))
    return receipt


def run_identity_short_circuited_epoch_sequence_v111(
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
    v109 = previous.previous
    if (
        type(candidate) is not PartialFactorCandidateV15
        or type(observed_rows) is not tuple
        or not observed_rows
        or v109._group_count(observed_rows) != acquisition_ground_support_labels  # noqa: SLF001
        or type(episode_indices) is not tuple
        or len(episode_indices) < 2
    ):
        _fail("V111 sequence inventory changed")
    persistent_rows = v109._deduplicate(observed_rows)  # noqa: SLF001
    cache: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
    entries: dict[str, dict[str, Any]] = {}
    reverse_index: dict[tuple[int, ...], set[str]] = defaultdict(set)
    stats = {"calls": 0, "hits": 0, "misses": 0, "actual_new_compute_events": 0}
    episodes = []
    models = []
    receipts = []
    transitions = []
    paid = 0
    previous_model = None
    previous_rules = None
    previous_incremental = None
    identity_checks = diff_checks = index_lookups = invalidations = short_circuits = 0
    for episode_index in episode_indices:
        model = compile_observation_quotient_graph_v105(
            candidate, persistent_rows, adapter.catalogue
        )
        rules = v109._terminal_rules(  # noqa: SLF001
            candidate, persistent_rows, adapter.catalogue
        )
        transition = None
        if previous_model is not None:
            if (
                model["quotient_graph_id"] != previous_model["quotient_graph_id"]
                and not previous_incremental
            ):
                _fail("V111 quotient graph changed without local overlay")
            transition = _identity_short_circuited_transition(
                previous_model=previous_model,
                current_model=model,
                previous_rules=previous_rules,
                current_rules=rules,
                cache=cache,
                entries=entries,
                reverse_index=reverse_index,
            )
            transitions.append(copy.deepcopy(transition))
            identity_checks += transition["model_epoch_identity_checks"]
            diff_checks += transition["full_model_epoch_diff_checks"]
            index_lookups += transition["reverse_dependency_index_lookups"]
            invalidations += len(transition["invalidated_dependency_receipt_ids"])
            short_circuits += transition["identity_short_circuit_applied"]
        before = dict(stats)
        episode = run_legality_conditioned_certificate_episode_v106(
            adapter,
            candidate,
            persistent_rows,
            preloaded_acquisition_ground_support_labels=v109._group_count(  # noqa: SLF001
                persistent_rows
            ),
            arm="IDENTITY_SHORT_CIRCUITED_EPOCH_INDEXED_QUOTIENT_ORDERING",
            abstract_orderer=previous._indexed_orderer(  # noqa: SLF001
                adapter,
                candidate,
                persistent_rows,
                model,
                cache,
                entries,
                reverse_index,
                stats,
                maximum_abstract_depth=maximum_abstract_depth,
            ),
            episode_index=episode_index,
            maximum_execution_steps=maximum_execution_steps,
            maximum_incremental_certificate_ground_support_labels=(
                maximum_incremental_certificate_ground_support_labels
            ),
        )
        actual = v109._actual_receipts(episode)  # noqa: SLF001
        incremental = episode["incremental_certificate_local_ground_support_labels"]
        paid += incremental
        new_rows = tuple(
            v109._row(document)  # noqa: SLF001
            for document in episode["raw_incremental_transition_rows"]
        )
        persistent_rows = v109._deduplicate((*persistent_rows, *new_rows))  # noqa: SLF001
        calls = stats["calls"] - before["calls"]
        hits = stats["hits"] - before["hits"]
        misses = stats["misses"] - before["misses"]
        actual_new = stats["actual_new_compute_events"] - before[
            "actual_new_compute_events"
        ]
        if calls != hits + misses or actual_new != episode["abstract_planning_compute_events"]:
            _fail("V111 episode memo accounting changed")
        episodes.append(
            {
                **copy.deepcopy(episode),
                "quotient_graph_before_episode": copy.deepcopy(model),
                "epoch_transition_receipt": copy.deepcopy(transition),
                "actual_legality_conditioned_execution_receipts": actual,
                "actual_legality_conditioned_execution_receipt_count": len(actual),
                "quotient_proposal_admitted_execution_count": sum(
                    row["quotient_proposal_admitted_to_real_action_order"]
                    for row in actual
                ),
                "chosen_action_matches_admitted_quotient_proposal_count": sum(
                    row["chosen_action_matches_admitted_quotient_proposal"]
                    for row in actual
                ),
                "certificate_local_legality_plan_count": sum(
                    row["legality_support_source"]
                    in (
                        "CERTIFICATE_LOCAL_LEGALITY_AFTER_FAILURE",
                        "CERTIFICATE_LOCAL_LEGALITY_FROM_TRANSITION_AFTER_FAILURE",
                    )
                    for row in actual
                ),
                "epoch_indexed_orderer_call_count": calls,
                "epoch_authorized_cache_hit_count": hits,
                "epoch_cache_miss_count": misses,
                "actual_new_abstract_planning_compute_events": actual_new,
                "per_hit_dependency_validation_checks": 0,
                "dependency_cache_entry_count_after_episode": len(entries),
                "new_certificate_labels_charged_this_episode": incremental,
                "paid_certificate_labels_cumulative": paid,
                "persistent_exact_support_group_count_after_episode": v109._group_count(  # noqa: SLF001
                    persistent_rows
                ),
            }
        )
        models.append(copy.deepcopy(model))
        receipts.extend(actual)
        previous_model = model
        previous_rules = rules
        previous_incremental = incremental
    steps = sum(row["execution_steps"] for row in episodes)
    failures = [item for episode in episodes for item in episode["failed_certificates"]]
    distinctions = [item for episode in episodes for item in episode["local_distinctions"]]
    overlay = [row.to_document() for row in persistent_rows]
    payload = {
        "schema": "acfqp.generic_identity_short_circuited_epoch_sequence.v111",
        "family": adapter.family,
        "seed": adapter.seed,
        "episode_indices": list(episode_indices),
        "partial_candidate_id": candidate.public_document["candidate_id"],
        "initial_acquisition_ground_support_labels_paid_once": acquisition_ground_support_labels,
        "quotient_models_before_each_episode": models,
        "model_epoch_transition_receipts": transitions,
        "episodes": episodes,
        "all_actual_legality_conditioned_execution_receipts": receipts,
        "actual_legality_conditioned_execution_receipt_count": len(receipts),
        "execution_step_count": steps,
        "quotient_proposal_admitted_execution_count": sum(
            row["quotient_proposal_admitted_to_real_action_order"] for row in receipts
        ),
        "chosen_action_matches_admitted_quotient_proposal_count": sum(
            row["chosen_action_matches_admitted_quotient_proposal"] for row in receipts
        ),
        "certificate_local_legality_plan_count": sum(
            row["legality_support_source"]
            in (
                "CERTIFICATE_LOCAL_LEGALITY_AFTER_FAILURE",
                "CERTIFICATE_LOCAL_LEGALITY_FROM_TRANSITION_AFTER_FAILURE",
            )
            for row in receipts
        ),
        "epoch_indexed_orderer_call_count": stats["calls"],
        "epoch_authorized_cache_hit_count": stats["hits"],
        "epoch_cache_miss_count": stats["misses"],
        "dependency_cache_entry_count": len(entries),
        "actual_new_abstract_planning_compute_events": stats[
            "actual_new_compute_events"
        ],
        "model_epoch_identity_checks": identity_checks,
        "full_model_epoch_diff_checks": diff_checks,
        "reverse_dependency_index_lookups": index_lookups,
        "dependency_cache_entry_invalidations": invalidations,
        "identity_short_circuit_count": short_circuits,
        "per_hit_dependency_validation_checks": 0,
        "all_dependency_maintenance_axes_and_planning_compute_reported_separately": True,
        "certificate_ground_support_labels_paid_once": paid,
        "lifetime_target_ground_support_labels": acquisition_ground_support_labels + paid,
        "persistent_exact_overlay_rows": overlay,
        "persistent_exact_overlay_sha256": hashlib.sha256(
            canonical_json_bytes(overlay)
        ).hexdigest(),
        "persistent_exact_support_group_count": v109._group_count(  # noqa: SLF001
            persistent_rows
        ),
        "all_failed_certificates": failures,
        "all_local_distinctions": distinctions,
        "every_new_ground_query_followed_a_failed_certificate": all(
            row.get("ground_query_performed_before_failure") is False
            for row in failures
        )
        and all(
            row.get("query_after_failed_certificate") is True
            for row in distinctions
        ),
        "certified_legality_reused_as_abstract_boundary_not_recharged": True,
        "quotient_graph_updates_only_from_certificate_local_overlay": True,
        "actual_engine_action_order_receipts_not_posthoc_policy_matches": True,
        "query_local_exact_overlay_exclusively_discharges_safety": True,
        "cached_heuristic_used_as_safety_authority": False,
        "global_lumpability_claimed": False,
        "complete_ground_world_model_synthesized": False,
        "official_execution_allowed": False,
    }
    return {
        **payload,
        "sequence_id": domains.extension_content_id_v111(
            domains.CONSTRUCTION_K7_IDENTITY_SHORT_CIRCUITED_EPOCH_SEQUENCE_V111_DOMAIN,
            payload,
        ),
    }


__all__ = ("run_identity_short_circuited_epoch_sequence_v111",)
