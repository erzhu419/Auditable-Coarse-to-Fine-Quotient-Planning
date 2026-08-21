"""Producer-free V109 replay of plans, dependencies, cache, and execution."""

from __future__ import annotations

from collections import defaultdict, deque
import copy
import hashlib
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v109 as domains
from acfqp import construction_k7_memoized_catalogue_quotient_independent_verifier_v108 as v108
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "32de00511536f8cfd82bfa1b966290e36d589d1d7e910d4b20657a69937fa6d0"
CAMPAIGN_BYTE_COUNT = 7_213_563
CAMPAIGN_SHA256 = "46e00a6bf70ff12b010296ffdc01b341e8ce64abaf7f969747679533c7fdf4e1"
PREREGISTRATION_ID = "c1a213ba65426761648c31c6a2f51356509d49d88e0a14244c7428cf42e44df8"
V108_CAMPAIGN_ID = "fa9ce366738517878f37f171b553bde78a3522535063c82f9d17fa572bb95371"
V108_VERIFICATION_ID = "e7aba583086784cdf3b94f303b362c2094707a35cfb23670f78374d63784b4e2"
TARGETS = (
    ("BALANCED_BATCH_REFINEMENT", 1_021_101),
    ("BALANCED_BATCH_REFINEMENT", 1_021_102),
    ("MAINTENANCE_CASCADE", 1_021_103),
    ("MAINTENANCE_CASCADE", 1_021_104),
)
EPISODES = (181, 182, 183)
VERIFICATION_ID = "5b40c9a49f89b83985fcfc7a98bdbd539ce6d0d1128ee033739fba23b9aeb89f"
EXPECTED_CANONICAL_BYTE_COUNT = 4_700
EXPECTED_CANONICAL_SHA256 = "8ac806cea45b2eddda641a40cdda9aa978478ee5fb6f95437d979fd2f066adfc"

v106 = v108.v107.v106

_V109_EPISODE_EXTRAS = {
    "quotient_graph_before_episode",
    "actual_legality_conditioned_execution_receipts",
    "actual_legality_conditioned_execution_receipt_count",
    "quotient_proposal_admitted_execution_count",
    "chosen_action_matches_admitted_quotient_proposal_count",
    "certificate_local_legality_plan_count",
    "dependency_cache_orderer_call_count",
    "dependency_revalidated_cache_hit_count",
    "dependency_cache_miss_count",
    "actual_new_abstract_planning_compute_events",
    "dependency_validation_checks",
    "dependency_cache_entry_count_after_episode",
    "new_certificate_labels_charged_this_episode",
    "paid_certificate_labels_cumulative",
    "persistent_exact_support_group_count_after_episode",
}


class ConstructionK7DependencyRevalidatedQuotientIndependentVerifierV109Error(
    ValueError
):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7DependencyRevalidatedQuotientIndependentVerifierV109Error(
        message
    )


def _content(document: Any, key: str, domain: str) -> None:
    if type(document) is not dict:
        _fail(f"V109 {key} document type changed")
    payload = {name: value for name, value in document.items() if name != key}
    if document.get(key) != domains.extension_content_id_v109(domain, payload):
        _fail(f"V109 {key} changed")


def _adjacency(model: Mapping[str, Any]) -> dict[tuple[int, ...], tuple[tuple[int, tuple[int, ...]], ...]]:
    staged: dict[tuple[int, ...], set[tuple[int, tuple[int, ...]]]] = defaultdict(set)
    for row in model["projected_edge_rows"]:
        staged[tuple(row["projected_pre"])].add(
            (row["action_key"], tuple(row["projected_post"]))
        )
    return {state: tuple(sorted(edges)) for state, edges in staged.items()}


def _terminal_match(state: tuple[int, ...], rules: list[dict[str, Any]]) -> bool:
    return v106.v105._terminal_match(state, rules)  # noqa: SLF001


def _dependency(
    model: Mapping[str, Any],
    source_plan: Mapping[str, Any],
    initial: tuple[int, ...],
) -> dict[str, Any]:
    legal = tuple(source_plan["exact_legal_action_keys_at_initial_state"])
    rules = source_plan["embedded_projected_plan"]["terminal_projection_rule"]
    adjacency = _adjacency(model)
    queue = deque((initial,))
    predecessor: dict[tuple[int, ...], tuple[tuple[int, ...], int] | None] = {
        initial: None
    }
    popped = []
    goal = None
    evaluations = 0
    while queue:
        state = queue.popleft()
        terminal = _terminal_match(state, rules)
        edges = adjacency.get(state, ())
        popped.append(
            {
                "projected_state": list(state),
                "terminal_match": terminal,
                "outgoing_edges": [
                    {"action_key": key, "projected_post": list(post)}
                    for key, post in edges
                ],
            }
        )
        if terminal:
            goal = state
            break
        for key, successor in edges:
            evaluations += 1
            if state == initial and key not in legal:
                continue
            if successor not in predecessor:
                predecessor[successor] = (state, key)
                queue.append(successor)
    if goal is None:
        _fail("V109 independent dependency trace found no goal")
    actions = []
    cursor = goal
    while predecessor[cursor] is not None:
        parent, key = predecessor[cursor]
        actions.append(key)
        cursor = parent
    actions.reverse()
    if (
        actions != source_plan["projected_action_path"]
        or evaluations != source_plan["abstract_support_branch_evaluations"]
    ):
        _fail("V109 independent dependency trace differs from source plan")
    payload = {
        "schema": "acfqp.generic_quotient_plan_dependency_receipt.v109",
        "source_quotient_plan_id": source_plan[
            "legality_conditioned_quotient_plan_id"
        ],
        "source_quotient_graph_id": model["quotient_graph_id"],
        "partial_candidate_id": source_plan["partial_candidate_id"],
        "initial_projected_state": list(initial),
        "exact_legal_action_keys": list(legal),
        "terminal_projection_rule": copy.deepcopy(rules),
        "ordered_bfs_dependency_rows": popped,
        "source_projected_action_path": actions,
        "source_initial_action_key": actions[0],
        "source_branch_evaluations": evaluations,
        "dependency_row_count": len(popped),
        "dependency_validation_check_count": sum(
            1 + len(row["outgoing_edges"]) for row in popped
        ),
        "only_dequeued_pre_goal_states_and_the_first_goal_retained": True,
        "unrelated_quotient_edges_deliberately_excluded": True,
        "receipt_is_ordering_dependency_not_safety_authority": True,
        "query_local_exact_certificate_remains_only_safety_authority": True,
    }
    return {
        **payload,
        "dependency_receipt_id": domains.extension_content_id_v109(
            domains.CONSTRUCTION_K7_DEPENDENCY_REVALIDATED_QUOTIENT_DEPENDENCY_V109_DOMAIN,
            payload,
        ),
    }


def _validate_dependency(
    receipt: Mapping[str, Any],
    model: Mapping[str, Any],
    rules: list[dict[str, Any]],
) -> dict[str, Any] | None:
    adjacency = _adjacency(model)
    if receipt["terminal_projection_rule"] != rules:
        return None
    checks = 0
    for row in receipt["ordered_bfs_dependency_rows"]:
        state = tuple(row["projected_state"])
        checks += 1
        if _terminal_match(state, rules) is not row["terminal_match"]:
            return None
        edges = [
            {"action_key": key, "projected_post": list(post)}
            for key, post in adjacency.get(state, ())
        ]
        checks += len(edges)
        if edges != row["outgoing_edges"]:
            return None
    if checks != receipt["dependency_validation_check_count"]:
        _fail("V109 dependency check accounting changed")
    return {
        "dependency_receipt_id": receipt["dependency_receipt_id"],
        "source_quotient_graph_id": receipt["source_quotient_graph_id"],
        "current_quotient_graph_id": model["quotient_graph_id"],
        "dependency_validation_check_count": checks,
        "source_action_path_remains_valid_under_current_dependency_slice": True,
        "full_current_quotient_graph_identity_required": False,
    }


def _projected(candidate: Mapping[str, Any], raw: list[int]) -> tuple[int, ...]:
    canonical = [raw[index] for index in candidate["layout"]["state_canonical_to_raw"]]
    return tuple(
        canonical[row["target_column"]]
        for row in candidate["compiled_factor_assignments"]
    )


def _v106_plan(
    plan: Mapping[str, Any],
    model: Mapping[str, Any],
    candidate: Mapping[str, Any],
    rows: list[dict[str, Any]],
    catalogue: Mapping[int, tuple[int, ...]],
    raw: list[int],
) -> dict[str, Any]:
    expected = v106._expected_plan(  # noqa: SLF001
        model,
        candidate,
        rows,
        catalogue,
        raw,
        tuple(plan["exact_legal_action_keys_at_initial_state"]),
        plan["planning_source"],
        plan["legality_support_source"],
        plan["legality_failure_index"],
    )
    expected["agreement_shield_receipt"] = v106.v103._shield(  # noqa: SLF001
        plan["agreement_shield_receipt"]
    )
    expected = {
        **expected,
        "legality_conditioned_quotient_plan_id": v106._hash(  # noqa: SLF001
            v106._PLAN_DOMAIN, expected  # noqa: SLF001
        ),
    }
    if plan != expected:
        _fail("V109 fresh quotient plan differs from independent replay")
    return expected


def _hit_plan(
    *,
    source_plan: Mapping[str, Any],
    dependency: Mapping[str, Any],
    validation: Mapping[str, Any],
    model: Mapping[str, Any],
    legal: tuple[int, ...],
    legality_source: str,
    failure_index: int | None,
) -> dict[str, Any]:
    action = source_plan["initial_action_key"]
    shield_payload = {
        "schema": "acfqp.abstract_partial_agreement_shield.v99",
        "abstract_proposal": [action],
        "partial_proposal": [action],
        "legal_action_keys": list(legal),
        "abstract_legal_proposal": action,
        "partial_legal_proposal": action,
        "abstract_partial_agreement": True,
        "abstract_proposal_admitted_to_action_order": True,
        "abstract_disagreement_abstained": False,
        "shielded_action_order": [
            action,
            *[key for key in legal if key != action],
        ],
        "abstract_proposal_can_precede_partial_without_agreement": False,
        "same_shield_applied_to_prior_and_no_prior_arms": True,
        "query_local_exact_overlay_remains_only_safety_authority": True,
    }
    shield = {
        **shield_payload,
        "shield_receipt_id": v106.v103._hash(  # noqa: SLF001
            v106.v103._SHIELD_DOMAIN, shield_payload  # noqa: SLF001
        ),
    }
    payload = {
        "schema": "acfqp.generic_dependency_revalidated_quotient_heuristic_plan.v109",
        "quotient_graph_id": model["quotient_graph_id"],
        "source_quotient_graph_id": source_plan["quotient_graph_id"],
        "partial_candidate_id": source_plan["partial_candidate_id"],
        "planning_source": "DEPENDENCY_REVALIDATED_PRIOR_QUOTIENT_ORDER",
        "initial_action_key": action,
        "projected_action_path": source_plan["projected_action_path"],
        "abstract_support_branch_evaluations": 0,
        "dependency_validation_check_count": validation[
            "dependency_validation_check_count"
        ],
        "source_legality_conditioned_quotient_plan": source_plan,
        "source_legality_conditioned_quotient_plan_id": source_plan[
            "legality_conditioned_quotient_plan_id"
        ],
        "quotient_plan_dependency_receipt": dependency,
        "quotient_plan_dependency_receipt_id": dependency["dependency_receipt_id"],
        "dependency_revalidation": validation,
        "exact_legal_action_keys_at_initial_state": list(legal),
        "legality_support_source": legality_source,
        "legality_failure_index": failure_index,
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


def _receipt(
    document: Any,
    episode_index: int,
    base_document: Mapping[str, Any],
    wrapper: Mapping[str, Any] | None,
) -> dict[str, Any]:
    base = v106.v103._receipt(base_document)  # noqa: SLF001
    plan = None if wrapper is None else wrapper["abstract_plan"]
    proposed = None if plan is None else plan["initial_action_key"]
    admitted = proposed in base["legal_action_keys"] if proposed is not None else False
    chosen = base["chosen_action_key"]
    match = admitted and chosen == proposed
    source = (
        "ACTUAL_DEPENDENCY_REVALIDATED_QUOTIENT_ORDER"
        if match
        else "EXACT_CERTIFICATE_FALLBACK_AFTER_DEPENDENCY_REVALIDATED_ORDER"
        if admitted
        else "EXACT_CERTIFICATE_ONLY_NO_QUOTIENT_ORDER"
    )
    payload = {
        "schema": "acfqp.generic_dependency_revalidated_execution_receipt.v109",
        "episode_index": episode_index,
        "decision_index": base["decision_index"],
        "raw_state": base["raw_state"],
        "chosen_action_key": chosen,
        "legal_action_keys": base["legal_action_keys"],
        "base_execution_receipt": base,
        "base_execution_receipt_id": base["execution_receipt_id"],
        "quotient_plan_receipt": wrapper,
        "quotient_graph_id": None if plan is None else plan["quotient_graph_id"],
        "quotient_plan_id": None
        if plan is None
        else plan["legality_conditioned_quotient_plan_id"],
        "quotient_proposed_action_key": proposed,
        "quotient_proposal_admitted_to_real_action_order": admitted,
        "chosen_action_matches_admitted_quotient_proposal": match,
        "actual_action_ordering_source": source,
        "legality_support_source": None
        if plan is None
        else plan["legality_support_source"],
        "legality_failure_index": None
        if plan is None
        else plan["legality_failure_index"],
        "exact_certificate_may_override_fallible_quotient_order": True,
        "receipt_is_observation_not_safety_authority": True,
        "query_local_exact_overlay_remains_only_safety_authority": True,
        "complete_ground_world_model_claimed": False,
    }
    expected = {
        **payload,
        "actual_dependency_revalidated_execution_receipt_id": domains.extension_content_id_v109(
            domains.CONSTRUCTION_K7_DEPENDENCY_REVALIDATED_QUOTIENT_EXECUTION_RECEIPT_V109_DOMAIN,
            payload,
        ),
    }
    if document != expected:
        _fail("V109 actual execution receipt changed")
    return expected


def _no_cache(
    document: Mapping[str, Any],
    acquisition: Mapping[str, Any],
    catalogue: Mapping[int, tuple[int, ...]],
    family: str,
    seed: int,
) -> dict[str, Any]:
    v106._content(document, "sequence_id", v106._SEQUENCE_DOMAIN)  # noqa: SLF001
    episodes = document["episodes"]
    final_rows = [
        v106.v105._row(row) for row in document["persistent_exact_overlay_rows"]  # noqa: SLF001
    ]
    incremental = [
        v106.v105._row(row)  # noqa: SLF001
        for episode in episodes
        for row in episode["raw_incremental_transition_rows"]
    ]
    incremental_keys = {v106.v105._row_key(row) for row in incremental}  # noqa: SLF001
    initial = [
        row
        for row in final_rows
        if v106.v105._row_key(row) not in incremental_keys  # noqa: SLF001
    ]
    candidate = v106.v105._verify_acquisition(  # noqa: SLF001
        acquisition, initial, family, seed
    )
    rows = v106.v105._deduplicate(initial)  # noqa: SLF001
    all_actual = []
    paid = 0
    models = []
    rows_before = []
    for index, episode, model in zip(
        EPISODES,
        episodes,
        document["quotient_models_before_each_episode"],
        strict=True,
    ):
        expected_model = v106.v105._expected_model(candidate, rows)  # noqa: SLF001
        if model != expected_model or episode["quotient_graph_before_episode"] != model:
            _fail("V109 no-cache model replay changed")
        rows_before.append(rows)
        models.append(model)
        actual, rows, charged, _fallback, _actual_fallback = v106._episode(  # noqa: SLF001
            episode,
            model,
            candidate,
            rows,
            catalogue,
            family,
            seed,
            index,
            paid,
        )
        for wrapper in episode["abstract_plan_receipts"]:
            _v106_plan(
                wrapper["abstract_plan"],
                model,
                candidate,
                rows_before[-1],
                catalogue,
                wrapper["raw_state"],
            )
        paid += charged
        all_actual.extend(actual)
    if rows != final_rows:
        _fail("V109 no-cache overlay replay changed")
    return {
        "candidate": candidate,
        "initial_rows": initial,
        "rows_before": rows_before,
        "models": models,
        "episodes": episodes,
        "actions": [episode["action_keys"] for episode in episodes],
        "base_receipts": [
            episode["abstract_execution_receipts"] for episode in episodes
        ],
        "actual_receipts": all_actual,
        "lifetime_labels": acquisition["ground_support_labels"] + paid,
        "initial_labels": acquisition["ground_support_labels"],
        "certificate_labels": paid,
        "planning_compute": sum(
            episode["abstract_planning_compute_events"] for episode in episodes
        ),
        "steps": sum(episode["execution_steps"] for episode in episodes),
    }


def _reuse(
    document: Mapping[str, Any],
    no_cache_document: Mapping[str, Any],
    acquisition: Mapping[str, Any],
    catalogue: Mapping[int, tuple[int, ...]],
    family: str,
    seed: int,
    baseline: Mapping[str, Any],
) -> dict[str, Any]:
    _content(
        document,
        "sequence_id",
        domains.CONSTRUCTION_K7_DEPENDENCY_REVALIDATED_QUOTIENT_SEQUENCE_V109_DOMAIN,
    )
    episodes = document["episodes"]
    if (
        document.get("schema")
        != "acfqp.generic_dependency_revalidated_quotient_sequence.v109"
        or document.get("family") != family
        or document.get("seed") != seed
        or document.get("episode_indices") != list(EPISODES)
        or document.get("partial_candidate_id")
        != acquisition["candidate"]["candidate_id"]
        or len(episodes) != len(EPISODES)
        or document.get("quotient_models_before_each_episode")
        != no_cache_document["quotient_models_before_each_episode"]
        or document.get("persistent_exact_overlay_rows")
        != no_cache_document["persistent_exact_overlay_rows"]
        or document.get("all_failed_certificates")
        != no_cache_document["all_failed_certificates"]
        or document.get("all_local_distinctions")
        != no_cache_document["all_local_distinctions"]
        or document.get("cached_heuristic_used_as_safety_authority") is not False
        or document.get("reuse_requires_exact_minimal_bfs_dependency_slice_match")
        is not True
    ):
        _fail("V109 reuse sequence boundary changed")
    candidate = baseline["candidate"]
    cache: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    all_actual = []
    calls = hits = misses = compute = checks = 0
    for episode, no_cache_episode, model, rows in zip(
        episodes,
        baseline["episodes"],
        baseline["models"],
        baseline["rows_before"],
        strict=True,
    ):
        v106.v103._content_id(  # noqa: SLF001
            episode,
            "episode_id",
            v106._EPISODE_DOMAIN,  # noqa: SLF001
            _V109_EPISODE_EXTRAS,
        )
        for key in (
            "family",
            "seed",
            "episode_index",
            "target_candidate_id",
            "action_keys",
            "outcome_tape_sha256",
            "execution_steps",
            "preloaded_acquisition_ground_support_labels",
            "incremental_certificate_local_ground_support_labels",
            "total_target_ground_support_labels",
            "preloaded_transition_support_hit_count",
            "queried_state_action_count",
            "abstract_execution_receipts",
            "execution_action_matches_abstract_proposal",
            "execution_action_matches_abstract_proposal_count",
            "failed_certificates",
            "local_distinctions",
            "raw_incremental_transition_rows",
            "all_incremental_ground_queries_followed_failed_certificates",
            "preloaded_exact_rows_reused_without_reacquisition",
            "query_local_exact_overlay_exclusively_used_for_safety",
            "abstract_model_used_only_for_action_ordering",
            "certified_legality_exposed_only_as_abstract_initial_action_constraint",
            "ground_transition_accessed_during_abstract_search",
            "model_or_alignment_used_as_safety_authority",
            "target_episode_outcomes_used_to_refit_model_or_alignment",
            "same_exact_engine_implementation_for_transfer_and_strict_arms",
            "complete_world_model_synthesized",
            "success",
        ):
            if episode.get(key) != no_cache_episode.get(key):
                _fail(f"V109 reuse/no-cache engine field changed: {key}")
        if (
            episode.get("arm")
            != "DEPENDENCY_REVALIDATED_CATALOGUE_QUOTIENT_ORDERING"
            or episode.get("abstract_plan_abstention_count") != 0
            or episode.get("abstract_plan_attempt_count")
            != len(episode["abstract_plan_receipts"])
            or episode.get("abstract_plan_success_count")
            != len(episode["abstract_plan_receipts"])
        ):
            _fail("V109 reuse plan-call inventory changed")
        rules = v106.v105._terminal_rules(candidate, rows, catalogue)  # noqa: SLF001
        wrappers = {}
        ep_hits = ep_misses = ep_compute = ep_checks = 0
        for wrapper in episode["abstract_plan_receipts"]:
            raw = wrapper["raw_state"]
            plan = wrapper["abstract_plan"]
            projected = _projected(candidate, raw)
            legal = tuple(plan["exact_legal_action_keys_at_initial_state"])
            stable = (candidate["candidate_id"], projected, legal)
            valid_entry = None
            valid_result = None
            for entry in cache[stable]:
                ep_checks += entry["dependency"][
                    "dependency_validation_check_count"
                ]
                result = _validate_dependency(entry["dependency"], model, rules)
                if result is not None:
                    valid_entry = entry
                    valid_result = result
                    break
            if plan["schema"] == "acfqp.generic_dependency_revalidated_quotient_heuristic_plan.v109":
                if valid_entry is None:
                    _fail("V109 claimed a dependency hit without a valid cached slice")
                expected = _hit_plan(
                    source_plan=valid_entry["source_plan"],
                    dependency=valid_entry["dependency"],
                    validation=valid_result,
                    model=model,
                    legal=legal,
                    legality_source=plan["legality_support_source"],
                    failure_index=plan["legality_failure_index"],
                )
                if plan != expected:
                    _fail("V109 revalidated hit plan differs from independent replay")
                ep_hits += 1
            else:
                if valid_entry is not None:
                    _fail("V109 recomputed a plan despite a valid dependency entry")
                expected = _v106_plan(
                    plan, model, candidate, rows, catalogue, raw
                )
                ep_misses += 1
                ep_compute += plan["abstract_support_branch_evaluations"]
                if plan["planning_source"] == "OBSERVATION_QUOTIENT_GRAPH":
                    dependency = _dependency(model, plan, projected)
                    cache[stable].append(
                        {"source_plan": expected, "dependency": dependency}
                    )
            wrappers[tuple(raw)] = wrapper
        actual = [
            _receipt(
                row,
                episode["episode_index"],
                base,
                wrappers.get(tuple(base["raw_state"])),
            )
            for row, base in zip(
                episode["actual_legality_conditioned_execution_receipts"],
                episode["abstract_execution_receipts"],
                strict=True,
            )
        ]
        ep_calls = len(episode["abstract_plan_receipts"])
        if (
            episode.get("dependency_cache_orderer_call_count") != ep_calls
            or episode.get("dependency_revalidated_cache_hit_count") != ep_hits
            or episode.get("dependency_cache_miss_count") != ep_misses
            or episode.get("actual_new_abstract_planning_compute_events")
            != ep_compute
            or episode.get("abstract_planning_compute_events") != ep_compute
            or episode.get("dependency_validation_checks") != ep_checks
            or episode.get("dependency_cache_entry_count_after_episode")
            != sum(len(value) for value in cache.values())
        ):
            _fail("V109 episode dependency accounting changed")
        calls += ep_calls
        hits += ep_hits
        misses += ep_misses
        compute += ep_compute
        checks += ep_checks
        all_actual.extend(actual)
    if (
        document.get("all_actual_legality_conditioned_execution_receipts")
        != all_actual
        or document.get("actual_legality_conditioned_execution_receipt_count")
        != len(all_actual)
        or document.get("execution_step_count") != baseline["steps"]
        or document.get("dependency_cache_orderer_call_count") != calls
        or document.get("dependency_revalidated_cache_hit_count") != hits
        or document.get("dependency_cache_miss_count") != misses
        or document.get("dependency_cache_entry_count")
        != sum(len(value) for value in cache.values())
        or document.get("actual_new_abstract_planning_compute_events") != compute
        or document.get("dependency_validation_checks") != checks
        or document.get("dependency_key_excludes_unrelated_full_graph_identity")
        is not True
        or document.get(
            "dependency_validation_and_planning_compute_reported_separately"
        )
        is not True
    ):
        _fail("V109 sequence dependency aggregate changed")
    return {
        "actions": [episode["action_keys"] for episode in episodes],
        "base_receipts": [
            episode["abstract_execution_receipts"] for episode in episodes
        ],
        "actual_receipts": all_actual,
        "lifetime_labels": document["lifetime_target_ground_support_labels"],
        "initial_labels": document[
            "initial_acquisition_ground_support_labels_paid_once"
        ],
        "certificate_labels": document[
            "certificate_ground_support_labels_paid_once"
        ],
        "steps": document["execution_step_count"],
        "compute": compute,
        "checks": checks,
        "hits": hits,
        "misses": misses,
        "later_zero": any(
            episode["episode_index"] != EPISODES[0]
            and episode["new_certificate_labels_charged_this_episode"] == 0
            and episode["quotient_proposal_admitted_execution_count"] > 0
            for episode in episodes
        ),
    }


def _direct(document: Any, family: str, seed: int, candidate_id: str) -> int:
    if (
        type(document) is not dict
        or document.get("schema") != "acfqp.generic_strict_cold_direct_sequence.v96"
        or document.get("family") != family
        or document.get("seed") != seed
        or document.get("episode_indices") != list(EPISODES)
        or document.get("free_target_rows_received") is not False
        or document.get("abstract_planning_compute_events") != 0
    ):
        _fail("V109 direct sequence changed")
    labels = 0
    for index, episode in zip(EPISODES, document["episodes"], strict=True):
        v106.v103._content_id(  # noqa: SLF001
            episode, "episode_id", v106.v103._DIRECT_EPISODE_DOMAIN  # noqa: SLF001
        )
        failures = episode["failed_certificates"]
        distinctions = episode["local_distinctions"]
        if (
            episode.get("family") != family
            or episode.get("seed") != seed
            or episode.get("episode_index") != index
            or episode.get("arm") != "STRICT_COLD_DIRECT_GROUND"
            or episode.get("target_candidate_id") != candidate_id
            or episode.get("success") is not True
            or len(failures) != len(distinctions)
            or any(
                row.get("ground_query_performed_before_failure") is not False
                for row in failures
            )
            or any(
                row.get("query_after_failed_certificate") is not True
                for row in distinctions
            )
        ):
            _fail("V109 direct episode changed")
        charged = sum(row["ground_support_labels"] for row in distinctions)
        if episode["incremental_certificate_local_ground_support_labels"] != charged:
            _fail("V109 direct labels changed")
        labels += charged
    if document["lifetime_target_ground_support_labels"] != labels:
        _fail("V109 direct lifetime labels changed")
    return labels


def _utilization(sequence: Mapping[str, Any]) -> dict[str, Any]:
    receipts = sequence["all_actual_legality_conditioned_execution_receipts"]
    steps = len(receipts)
    admitted = sum(
        row["quotient_proposal_admitted_to_real_action_order"] for row in receipts
    )
    matches = sum(
        row["chosen_action_matches_admitted_quotient_proposal"] for row in receipts
    )
    local = sum(
        row["legality_support_source"] in v106._LOCAL_LEGALITY_SOURCES  # noqa: SLF001
        for row in receipts
    )
    return {
        "schema": "acfqp.dependency_revalidated_quotient_utilization.v109",
        "execution_receipt_count": steps,
        "execution_step_count": steps,
        "quotient_proposal_admitted_execution_count": admitted,
        "chosen_action_matches_admitted_quotient_proposal_count": matches,
        "certificate_local_legality_plan_count": local,
        "quotient_proposal_admitted_fraction_numerator": admitted,
        "quotient_proposal_admitted_fraction_denominator": steps,
        "chosen_action_match_fraction_numerator": matches,
        "chosen_action_match_fraction_denominator": steps,
        "quotient_actually_orders_strict_majority_of_execution": 2 * admitted > steps,
        "quotient_actually_orders_at_least_three_quarters_of_execution": 4
        * admitted
        >= 3 * steps,
        "chosen_action_matches_quotient_strict_majority": 2 * matches > steps,
        "every_action_independently_receipted": True,
        "receipt_replay_uses_no_producer_summary_count": True,
        "ordering_is_engine_input_not_posthoc_policy_match": True,
        "certified_legality_is_boundary_condition_not_transition_model": True,
        "query_local_exact_overlay_remains_only_safety_authority": True,
    }


def _occurrence(document: Any, family: str, seed: int) -> dict[str, Any]:
    _content(
        document,
        "occurrence_id",
        domains.CONSTRUCTION_K7_DEPENDENCY_REVALIDATED_QUOTIENT_OCCURRENCE_V109_DOMAIN,
    )
    if (
        document.get("schema")
        != "acfqp.dependency_revalidated_quotient_occurrence.v109"
        or document.get("target_family") != family
        or document.get("seed") != seed
        or document.get("episode_indices") != list(EPISODES)
    ):
        _fail("V109 occurrence identity changed")
    catalogue = v108.v107._catalogue(  # noqa: SLF001
        document["complete_anonymous_action_catalogue_receipt"], family, seed
    )
    acquisition = document["partial_acquisition"]
    no_cache_doc = document["matched_no_cache_legality_quotient_sequence"]
    baseline = _no_cache(no_cache_doc, acquisition, catalogue, family, seed)
    reuse_doc = document["persistent_dependency_revalidated_quotient_sequence"]
    reuse = _reuse(
        reuse_doc, no_cache_doc, acquisition, catalogue, family, seed, baseline
    )
    direct = _direct(
        document["strict_cold_direct_sequence"],
        family,
        seed,
        acquisition["candidate"]["candidate_id"],
    )
    utilization = _utilization(reuse_doc)
    gate = {
        "revalidated_and_no_cache_action_sequences_exactly_match": reuse[
            "actions"
        ]
        == baseline["actions"],
        "revalidated_and_no_cache_base_execution_receipts_exactly_match": reuse[
            "base_receipts"
        ]
        == baseline["base_receipts"],
        "revalidated_and_no_cache_target_labels_exactly_match": reuse[
            "lifetime_labels"
        ]
        == baseline["lifetime_labels"],
        "revalidated_and_no_cache_execution_steps_exactly_match": reuse["steps"]
        == baseline["steps"],
        "actual_new_planning_compute_strictly_below_no_cache": reuse["compute"]
        < baseline["planning_compute"],
        "dependency_revalidated_hit_observed": reuse["hits"] > 0,
        "quotient_model_orders_at_least_three_quarters": utilization[
            "quotient_actually_orders_at_least_three_quarters_of_execution"
        ],
        "chosen_action_matches_quotient_strict_majority": utilization[
            "chosen_action_matches_quotient_strict_majority"
        ],
        "certificate_failure_only_query_discipline_clean": reuse_doc[
            "every_new_ground_query_followed_a_failed_certificate"
        ],
        "later_zero_label_quotient_reuse_observed": reuse["later_zero"],
        "quotient_lifetime_labels_strictly_below_cold_direct": reuse[
            "lifetime_labels"
        ]
        < direct,
    }
    gate["passed"] = all(gate.values())
    accounting = {
        "initial_acquisition_labels": reuse["initial_labels"],
        "certificate_local_labels": reuse["certificate_labels"],
        "dependency_revalidated_quotient_lifetime_target_labels": reuse[
            "lifetime_labels"
        ],
        "matched_no_cache_quotient_lifetime_target_labels": baseline[
            "lifetime_labels"
        ],
        "cold_direct_lifetime_target_labels": direct,
        "target_label_reduction_against_cold_direct": direct
        - reuse["lifetime_labels"],
        "execution_steps": reuse["steps"],
        "actual_new_abstract_planning_compute_events": reuse["compute"],
        "matched_no_cache_planning_compute_events": baseline["planning_compute"],
        "planning_compute_events_avoided": baseline["planning_compute"]
        - reuse["compute"],
        "dependency_validation_checks": reuse["checks"],
        "sample_labels_execution_steps_planning_and_validation_compute_separate": True,
        "scalar_cost_aggregation_performed": False,
    }
    if (
        document["legality_conditioned_quotient_utilization"] != utilization
        or document["accounting"] != accounting
        or document["registered_gate"] != gate
        or document["dependency_revalidated_ordering_preserves_actions_labels_and_steps"]
        != gate["passed"]
        or document["local_ground_distinctions_only_after_certificate_failure_verified"]
        != gate["passed"]
        or document["cached_heuristic_used_as_safety_authority"] is not False
        or document["complete_ground_world_model_synthesized"] is not False
        or document["official_scalar_cost"] is not None
        or document["WORKLOAD_ECONOMICS_GATE"] != "NOT_RUN"
    ):
        _fail("V109 occurrence Gate or claim boundary changed")
    return {
        "target_family": family,
        "seed": seed,
        "gate_passed": gate["passed"],
        **accounting,
        "dependency_revalidated_cache_hits": reuse["hits"],
        "dependency_cache_misses": reuse["misses"],
    }


def verify_dependency_revalidated_quotient_campaign_bytes_v109(
    raw: bytes,
) -> dict[str, Any]:
    if (
        type(raw) is not bytes
        or len(raw) != CAMPAIGN_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != CAMPAIGN_SHA256
    ):
        _fail("V109 campaign bytes changed")
    document = loads_canonical_json(raw)
    if canonical_json_bytes(document) != raw:
        _fail("V109 campaign is noncanonical")
    _content(
        document,
        "campaign_id",
        domains.CONSTRUCTION_K7_DEPENDENCY_REVALIDATED_QUOTIENT_CAMPAIGN_V109_DOMAIN,
    )
    rows = document.get("target_occurrences")
    if (
        document.get("campaign_id") != CAMPAIGN_ID
        or document.get("schema") != "acfqp.dependency_revalidated_quotient_campaign.v109"
        or document.get("preregistration_id") != PREREGISTRATION_ID
        or document.get("v108_failed_campaign_id") != V108_CAMPAIGN_ID
        or document.get("v108_failed_verification_id") != V108_VERIFICATION_ID
        or type(rows) is not list
        or len(rows) != len(TARGETS)
    ):
        _fail("V109 campaign inventory changed")
    replay = [
        _occurrence(row, family, seed)
        for row, (family, seed) in zip(rows, TARGETS, strict=True)
    ]
    keys = (
        "initial_acquisition_labels",
        "certificate_local_labels",
        "dependency_revalidated_quotient_lifetime_target_labels",
        "matched_no_cache_quotient_lifetime_target_labels",
        "cold_direct_lifetime_target_labels",
        "target_label_reduction_against_cold_direct",
        "execution_steps",
        "actual_new_abstract_planning_compute_events",
        "matched_no_cache_planning_compute_events",
        "planning_compute_events_avoided",
        "dependency_validation_checks",
    )
    totals = {key: sum(row[key] for row in replay) for key in keys}
    accounting = {
        **totals,
        "offline_source_labels_not_recharged": True,
        "sample_labels_execution_steps_planning_and_validation_compute_separate": True,
        "scalar_cost_aggregation_performed": False,
    }
    ood = v106.v105._ood(document["incompatible_schema_no_transfer_control"])  # noqa: SLF001
    passed = (
        all(row["gate_passed"] for row in replay)
        and totals["actual_new_abstract_planning_compute_events"]
        < totals["matched_no_cache_planning_compute_events"]
        and totals["dependency_revalidated_quotient_lifetime_target_labels"]
        < totals["cold_direct_lifetime_target_labels"]
        and ood["strict_ood_no_transfer"] is True
    )
    gate = {
        "required_target_occurrence_count": 4,
        "passed_target_occurrence_count": sum(row["gate_passed"] for row in replay),
        "every_occurrence_actions_base_receipts_labels_and_steps_equal_no_cache": all(
            row["gate_passed"] for row in replay
        ),
        "every_occurrence_planning_compute_strictly_reduced": all(
            row["actual_new_abstract_planning_compute_events"]
            < row["matched_no_cache_planning_compute_events"]
            for row in replay
        ),
        "aggregate_sample_labels_unchanged_by_reuse": totals[
            "dependency_revalidated_quotient_lifetime_target_labels"
        ]
        == totals["matched_no_cache_quotient_lifetime_target_labels"],
        "aggregate_quotient_labels_strictly_below_cold_direct": totals[
            "dependency_revalidated_quotient_lifetime_target_labels"
        ]
        < totals["cold_direct_lifetime_target_labels"],
        "strict_incompatible_schema_no_transfer_verified": ood[
            "strict_ood_no_transfer"
        ],
        "passed": passed,
    }
    if (
        document["accounting"] != accounting
        or document["registered_gate"] != gate
        or document["registered_dependency_revalidated_quotient_reuse_verified"]
        != passed
        or document["ground_distinctions_acquired_only_after_certificate_failure_verified"]
        != passed
        or document["cached_heuristic_used_as_safety_authority"] is not False
        or document["complete_ground_world_model_synthesized"] is not False
        or document["official_scalar_cost"] is not None
        or document["WORKLOAD_ECONOMICS_GATE"] != "NOT_RUN"
    ):
        _fail("V109 campaign Gate or claim boundary changed")
    return {
        "schema": "acfqp.dependency_revalidated_quotient_verification.v109",
        "campaign_id": CAMPAIGN_ID,
        "preregistration_id": PREREGISTRATION_ID,
        "verification_status": "REGISTERED_V109_DEPENDENCY_REVALIDATED_REUSE_VERIFIED",
        "producer_free_complete_catalogue_and_fresh_plan_replay": True,
        "producer_free_minimal_bfs_dependency_reconstruction": True,
        "producer_free_cache_order_and_hit_miss_reconstruction": True,
        "producer_free_per_action_receipt_reconstruction": True,
        "producer_summary_counts_not_used": True,
        "verified_occurrences": replay,
        "verified_accounting": accounting,
        "verified_dependency_revalidated_cache_hit_count": sum(
            row["dependency_revalidated_cache_hits"] for row in replay
        ),
        "verified_dependency_cache_miss_count": sum(
            row["dependency_cache_misses"] for row in replay
        ),
        "registered_gate_independently_verified": passed,
        "cached_heuristic_used_as_safety_authority": False,
        "global_lumpability_claimed": False,
        "complete_ground_world_model_synthesized": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }


def freeze_dependency_revalidated_quotient_verification_v109(raw: bytes) -> bytes:
    payload = verify_dependency_revalidated_quotient_campaign_bytes_v109(raw)
    document = {
        **payload,
        "verification_id": domains.extension_content_id_v109(
            domains.CONSTRUCTION_K7_DEPENDENCY_REVALIDATED_QUOTIENT_VERIFICATION_V109_DOMAIN,
            payload,
        ),
    }
    result = canonical_json_bytes(document)
    if VERIFICATION_ID != "0" * 64 and (
        document["verification_id"] != VERIFICATION_ID
        or len(result) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(result).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("V109 verification changed")
    return result


__all__ = (
    "VERIFICATION_ID",
    "freeze_dependency_revalidated_quotient_verification_v109",
    "verify_dependency_revalidated_quotient_campaign_bytes_v109",
)
