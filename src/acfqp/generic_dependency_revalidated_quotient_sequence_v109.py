"""Persistent quotient ordering with minimal dependency revalidation V109."""

from __future__ import annotations

import copy
import hashlib
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v109 as domains
from acfqp.generic_abstract_partial_agreement_shield_v99 import (
    shield_abstract_action_order_v99,
)
from acfqp.generic_dependency_revalidated_execution_receipt_v109 import (
    build_dependency_revalidated_execution_receipt_v109,
    verify_dependency_revalidated_execution_receipt_v109,
)
from acfqp.generic_atomic_expression_world_model_v4 import (
    FlatRawActionV4,
    FlatRawTransitionV4,
)
from acfqp.generic_layout_factorized_world_model_v5 import (
    align_generic_occurrence_v5,
)
from acfqp.generic_legality_conditioned_certificate_engine_v106 import (
    run_legality_conditioned_certificate_episode_v106,
)
from acfqp.generic_legality_conditioned_quotient_planner_v106 import (
    plan_legality_conditioned_quotient_v106,
)
from acfqp.generic_observation_quotient_graph_v105 import (
    compile_observation_quotient_graph_v105,
)
from acfqp.generic_partial_factor_proposal_v15 import PartialFactorCandidateV15
from acfqp.generic_quotient_plan_dependency_receipt_v109 import (
    build_quotient_plan_dependency_receipt_v109,
    revalidate_quotient_plan_dependency_v109,
)
from acfqp.phase3e_ids import canonical_json_bytes


class GenericDependencyRevalidatedQuotientSequenceV109Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise GenericDependencyRevalidatedQuotientSequenceV109Error(message)


def _row(document: Mapping[str, Any]) -> FlatRawTransitionV4:
    selected = document.get("selected_action")
    if type(selected) is not dict:
        _fail("V109 persisted transition action changed")
    return FlatRawTransitionV4(
        document["occurrence"],
        document["transition_index"],
        tuple(document["pre_vector"]),
        tuple(document["legal_action_keys_before"]),
        FlatRawActionV4(
            selected["action_key"], tuple(selected["anonymous_fields"])
        ),
        tuple(document["post_vector"]),
        tuple(document["legal_action_keys_after"]),
        document["terminal_acceptance_after"],
        document.get("outcome_tape_sha256"),
    )


def _deduplicate(
    rows: tuple[FlatRawTransitionV4, ...],
) -> tuple[FlatRawTransitionV4, ...]:
    unique = {(row.pre, row.action.key, row.post): row for row in rows}
    return tuple(unique[key] for key in sorted(unique))


def _group_count(rows: tuple[FlatRawTransitionV4, ...]) -> int:
    return len({(row.pre, row.action.key) for row in rows})


def _actual_receipts(episode: Mapping[str, Any]) -> list[dict[str, Any]]:
    plans = {}
    for wrapper in episode["abstract_plan_receipts"]:
        raw = wrapper.get("raw_state") if type(wrapper) is dict else None
        if type(raw) is not list or tuple(raw) in plans:
            _fail("V109 quotient plan receipt inventory changed")
        plans[tuple(raw)] = wrapper
    return [
        verify_dependency_revalidated_execution_receipt_v109(
            build_dependency_revalidated_execution_receipt_v109(
                episode_index=episode["episode_index"],
                base_execution_receipt=base,
                quotient_plan_receipt=plans.get(tuple(base["raw_state"])),
            )
        )
        for base in episode["abstract_execution_receipts"]
    ]


def _projected_state(
    candidate: PartialFactorCandidateV15, raw: tuple[int, ...]
) -> tuple[int, ...]:
    canonical = tuple(
        raw[index] for index in candidate.layout.state_canonical_to_raw
    )
    return tuple(
        canonical[row["target_column"]] for row in candidate.assignments
    )


def _terminal_rules(
    candidate: PartialFactorCandidateV15,
    rows: tuple[FlatRawTransitionV4, ...],
    catalogue: tuple[FlatRawActionV4, ...],
) -> tuple[dict[str, Any], ...]:
    aligned, _ = align_generic_occurrence_v5(
        rows, catalogue, candidate.layout, canonical_occurrence=0
    )
    accepting = tuple(row for row in aligned if row.terminal_acceptance_after is True)
    if not accepting:
        _fail("V109 partial observations exposed no accepting projection")
    actions = tuple(
        FlatRawActionV4(
            action.key,
            tuple(
                action.fields[index]
                for index in candidate.layout.action_canonical_to_raw
            ),
        )
        for action in catalogue
    )
    rules = []
    for assignment in candidate.assignments:
        target = assignment["target_column"]
        values = tuple(sorted({row.post[target] for row in accepting}))
        expression = assignment["expression"]
        if expression[0] == "E00" and len(values) == 1:
            rule = {"kind": "EQUAL", "value": values[0]}
        elif expression[0] == "E07":
            field = expression[2][2][1]
            increments = tuple(action.fields[field] for action in actions)
            if all(value >= 0 for value in increments):
                rule = {"kind": "AT_LEAST", "value": min(values)}
            elif all(value <= 0 for value in increments):
                rule = {"kind": "AT_MOST", "value": max(values)}
            else:
                rule = {"kind": "OBSERVED_SET", "values": list(values)}
        else:
            rule = {"kind": "UNCONSTRAINED"}
        rules.append({"target_column": target, **rule})
    return tuple(rules)


def _stable_key(
    candidate: PartialFactorCandidateV15,
    raw: tuple[int, ...],
    legal: tuple[int, ...],
) -> tuple[Any, ...]:
    return (
        candidate.public_document["candidate_id"],
        _projected_state(candidate, raw),
        legal,
    )


def _revalidated_plan(
    *,
    source_plan: Mapping[str, Any],
    dependency_receipt: Mapping[str, Any],
    validation: Mapping[str, Any],
    current_model: Mapping[str, Any],
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
        "schema": "acfqp.generic_dependency_revalidated_quotient_heuristic_plan.v109",
        "quotient_graph_id": current_model["quotient_graph_id"],
        "source_quotient_graph_id": source_plan["quotient_graph_id"],
        "partial_candidate_id": source_plan["partial_candidate_id"],
        "planning_source": "DEPENDENCY_REVALIDATED_PRIOR_QUOTIENT_ORDER",
        "initial_action_key": action,
        "projected_action_path": copy.deepcopy(
            source_plan["projected_action_path"]
        ),
        "abstract_support_branch_evaluations": 0,
        "dependency_validation_check_count": validation[
            "dependency_validation_check_count"
        ],
        "source_legality_conditioned_quotient_plan": copy.deepcopy(source_plan),
        "source_legality_conditioned_quotient_plan_id": source_plan[
            "legality_conditioned_quotient_plan_id"
        ],
        "quotient_plan_dependency_receipt": copy.deepcopy(dependency_receipt),
        "quotient_plan_dependency_receipt_id": dependency_receipt[
            "dependency_receipt_id"
        ],
        "dependency_revalidation": copy.deepcopy(validation),
        "exact_legal_action_keys_at_initial_state": list(legal),
        "legality_support_source": legality_support_source,
        "legality_failure_index": legality_failure_index,
        "agreement_shield_receipt": shield,
        "initial_illegal_actions_forbidden_in_reused_order": True,
        "ground_legality_used_only_after_existing_support_or_failed_certificate": True,
        "cached_ordering_used_as_safety_authority": False,
        "ground_transition_accessed_during_dependency_revalidation": False,
        "query_local_exact_overlay_remains_only_safety_authority": True,
        "complete_ground_world_model_claimed": False,
    }
    return {
        **payload,
        "legality_conditioned_quotient_plan_id": domains.extension_content_id_v109(
            domains.CONSTRUCTION_K7_DEPENDENCY_REVALIDATED_QUOTIENT_PLAN_V109_DOMAIN,
            payload,
        ),
    }


def _dependency_orderer(
    adapter: Any,
    candidate: PartialFactorCandidateV15,
    rows: tuple[FlatRawTransitionV4, ...],
    model: Mapping[str, Any],
    cache: dict[tuple[Any, ...], list[dict[str, Any]]],
    stats: dict[str, int],
    *,
    maximum_abstract_depth: int,
):
    rules = _terminal_rules(candidate, rows, adapter.catalogue)

    def order(
        raw: tuple[int, ...],
        legal: tuple[int, ...],
        legality_support_source: str,
        legality_failure_index: int | None,
    ) -> Mapping[str, Any] | None:
        stats["calls"] += 1
        key = _stable_key(candidate, raw, legal)
        for entry in cache.get(key, []):
            stats["dependency_validation_checks"] += entry[
                "dependency"
            ]["dependency_validation_check_count"]
            validation = revalidate_quotient_plan_dependency_v109(
                entry["dependency"],
                current_model=model,
                current_terminal_projection_rule=rules,
            )
            if validation is not None:
                stats["hits"] += 1
                return _revalidated_plan(
                    source_plan=entry["source_plan"],
                    dependency_receipt=entry["dependency"],
                    validation=validation,
                    current_model=model,
                    legal=legal,
                    legality_support_source=legality_support_source,
                    legality_failure_index=legality_failure_index,
                )
        stats["misses"] += 1
        try:
            plan = plan_legality_conditioned_quotient_v106(
                model,
                candidate,
                rows,
                adapter.catalogue,
                raw,
                legal,
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
                initial_projected_state=_projected_state(candidate, raw),
            )
            cache.setdefault(key, []).append(
                {
                    "source_plan": copy.deepcopy(plan),
                    "dependency": dependency,
                }
            )
        return copy.deepcopy(plan)

    return order


def run_dependency_revalidated_quotient_sequence_v109(
    adapter: Any,
    candidate: PartialFactorCandidateV15,
    observed_rows: tuple[FlatRawTransitionV4, ...],
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
        or _group_count(observed_rows) != acquisition_ground_support_labels
        or type(episode_indices) is not tuple
        or len(episode_indices) < 2
        or len(set(episode_indices)) != len(episode_indices)
        or maximum_abstract_depth <= 0
        or maximum_execution_steps <= 0
        or maximum_incremental_certificate_ground_support_labels <= 0
    ):
        _fail("V109 persistent sequence inventory changed")
    persistent_rows = _deduplicate(observed_rows)
    paid_certificate_labels = 0
    episodes = []
    models = []
    receipts = []
    previous_model_id = None
    previous_incremental = None
    cache: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
    stats = {
        "calls": 0,
        "hits": 0,
        "misses": 0,
        "actual_new_compute_events": 0,
        "dependency_validation_checks": 0,
    }
    for episode_index in episode_indices:
        model = compile_observation_quotient_graph_v105(
            candidate, persistent_rows, adapter.catalogue
        )
        if (
            previous_model_id is not None
            and model["quotient_graph_id"] != previous_model_id
            and not previous_incremental
        ):
            _fail("V109 quotient graph changed without certificate-local overlay")
        before = dict(stats)
        episode = run_legality_conditioned_certificate_episode_v106(
            adapter,
            candidate,
            persistent_rows,
            preloaded_acquisition_ground_support_labels=_group_count(
                persistent_rows
            ),
            arm="DEPENDENCY_REVALIDATED_CATALOGUE_QUOTIENT_ORDERING",
            abstract_orderer=_dependency_orderer(
                adapter,
                candidate,
                persistent_rows,
                model,
                cache,
                stats,
                maximum_abstract_depth=maximum_abstract_depth,
            ),
            episode_index=episode_index,
            maximum_execution_steps=maximum_execution_steps,
            maximum_incremental_certificate_ground_support_labels=(
                maximum_incremental_certificate_ground_support_labels
            ),
        )
        actual = _actual_receipts(episode)
        incremental = episode[
            "incremental_certificate_local_ground_support_labels"
        ]
        paid_certificate_labels += incremental
        new_rows = tuple(
            _row(document) for document in episode["raw_incremental_transition_rows"]
        )
        persistent_rows = _deduplicate((*persistent_rows, *new_rows))
        calls = stats["calls"] - before["calls"]
        hits = stats["hits"] - before["hits"]
        misses = stats["misses"] - before["misses"]
        actual_new = stats["actual_new_compute_events"] - before[
            "actual_new_compute_events"
        ]
        validation_checks = stats["dependency_validation_checks"] - before[
            "dependency_validation_checks"
        ]
        if (
            calls != hits + misses
            or actual_new != episode["abstract_planning_compute_events"]
        ):
            _fail("V109 dependency memo accounting changed")
        episodes.append(
            {
                **copy.deepcopy(episode),
                "quotient_graph_before_episode": copy.deepcopy(model),
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
                "dependency_cache_orderer_call_count": calls,
                "dependency_revalidated_cache_hit_count": hits,
                "dependency_cache_miss_count": misses,
                "actual_new_abstract_planning_compute_events": actual_new,
                "dependency_validation_checks": validation_checks,
                "dependency_cache_entry_count_after_episode": sum(
                    len(entries) for entries in cache.values()
                ),
                "new_certificate_labels_charged_this_episode": incremental,
                "paid_certificate_labels_cumulative": paid_certificate_labels,
                "persistent_exact_support_group_count_after_episode": _group_count(
                    persistent_rows
                ),
            }
        )
        models.append(copy.deepcopy(model))
        receipts.extend(actual)
        previous_model_id = model["quotient_graph_id"]
        previous_incremental = incremental
    steps = sum(row["execution_steps"] for row in episodes)
    admitted = sum(
        row["quotient_proposal_admitted_to_real_action_order"] for row in receipts
    )
    matches = sum(
        row["chosen_action_matches_admitted_quotient_proposal"] for row in receipts
    )
    local_legality = sum(
        row["legality_support_source"]
        in (
            "CERTIFICATE_LOCAL_LEGALITY_AFTER_FAILURE",
            "CERTIFICATE_LOCAL_LEGALITY_FROM_TRANSITION_AFTER_FAILURE",
        )
        for row in receipts
    )
    failures = [item for episode in episodes for item in episode["failed_certificates"]]
    distinctions = [
        item for episode in episodes for item in episode["local_distinctions"]
    ]
    overlay = [row.to_document() for row in persistent_rows]
    payload = {
        "schema": "acfqp.generic_dependency_revalidated_quotient_sequence.v109",
        "family": adapter.family,
        "seed": adapter.seed,
        "episode_indices": list(episode_indices),
        "partial_candidate_id": candidate.public_document["candidate_id"],
        "initial_acquisition_ground_support_labels_paid_once": acquisition_ground_support_labels,
        "quotient_models_before_each_episode": models,
        "episodes": episodes,
        "all_actual_legality_conditioned_execution_receipts": receipts,
        "actual_legality_conditioned_execution_receipt_count": len(receipts),
        "execution_step_count": steps,
        "quotient_proposal_admitted_execution_count": admitted,
        "chosen_action_matches_admitted_quotient_proposal_count": matches,
        "certificate_local_legality_plan_count": local_legality,
        "quotient_proposal_admitted_strict_majority": 2 * admitted > steps,
        "chosen_action_matches_admitted_quotient_proposal_strict_majority": 2
        * matches
        > steps,
        "dependency_cache_orderer_call_count": stats["calls"],
        "dependency_revalidated_cache_hit_count": stats["hits"],
        "dependency_cache_miss_count": stats["misses"],
        "dependency_cache_entry_count": sum(len(entries) for entries in cache.values()),
        "actual_new_abstract_planning_compute_events": stats[
            "actual_new_compute_events"
        ],
        "dependency_validation_checks": stats["dependency_validation_checks"],
        "dependency_key_excludes_unrelated_full_graph_identity": True,
        "reuse_requires_exact_minimal_bfs_dependency_slice_match": True,
        "dependency_validation_and_planning_compute_reported_separately": True,
        "certificate_ground_support_labels_paid_once": paid_certificate_labels,
        "lifetime_target_ground_support_labels": acquisition_ground_support_labels
        + paid_certificate_labels,
        "persistent_exact_overlay_rows": overlay,
        "persistent_exact_overlay_sha256": hashlib.sha256(
            canonical_json_bytes(overlay)
        ).hexdigest(),
        "persistent_exact_support_group_count": _group_count(persistent_rows),
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
        "sequence_id": domains.extension_content_id_v109(
            domains.CONSTRUCTION_K7_DEPENDENCY_REVALIDATED_QUOTIENT_SEQUENCE_V109_DOMAIN,
            payload,
        ),
    }


__all__ = ("run_dependency_revalidated_quotient_sequence_v109",)
