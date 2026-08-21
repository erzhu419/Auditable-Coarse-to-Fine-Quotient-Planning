"""Producer-free V110 replay of epoch deltas, reverse index, plans, and actions."""

from __future__ import annotations

from collections import defaultdict
import copy
import hashlib
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v110 as domains
from acfqp import construction_k7_dependency_revalidated_quotient_independent_verifier_v109 as v109
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "9efd58cd7d285b4f29b86ba8d750bac1569eea3d58027293c4699f48845b7ca7"
CAMPAIGN_BYTE_COUNT = 12_215_135
CAMPAIGN_SHA256 = "b3b57e0d3ea0db565ab254cf4898828d0409bc86537bd05ea01f2e3f6acf3b80"
PREREGISTRATION_ID = "ce41eb77cb6f1270fde8f6121ade5a73a937bbdb4dd912d95a0313891b04b2be"
V109_CAMPAIGN_ID = "32de00511536f8cfd82bfa1b966290e36d589d1d7e910d4b20657a69937fa6d0"
V109_VERIFICATION_ID = "5b40c9a49f89b83985fcfc7a98bdbd539ce6d0d1128ee033739fba23b9aeb89f"
TARGETS = (
    ("BALANCED_BATCH_REFINEMENT", 1_022_101),
    ("BALANCED_BATCH_REFINEMENT", 1_022_102),
    ("MAINTENANCE_CASCADE", 1_022_103),
    ("MAINTENANCE_CASCADE", 1_022_104),
)
EPISODES = (191, 192, 193)
VERIFICATION_ID = "f40981fb930d3662d6a66ff8794b2899bf7153dd21474b2bac82be882c842209"
EXPECTED_CANONICAL_BYTE_COUNT = 6_332
EXPECTED_CANONICAL_SHA256 = "a45776ad360f7eff37538a904b188da6a778a1ff1235b47a64e2e6890b87e756"

v106 = v109.v106

_V110_EPISODE_EXTRAS = {
    "quotient_graph_before_episode",
    "epoch_transition_receipt",
    "actual_legality_conditioned_execution_receipts",
    "actual_legality_conditioned_execution_receipt_count",
    "quotient_proposal_admitted_execution_count",
    "chosen_action_matches_admitted_quotient_proposal_count",
    "certificate_local_legality_plan_count",
    "epoch_indexed_orderer_call_count",
    "epoch_authorized_cache_hit_count",
    "epoch_cache_miss_count",
    "actual_new_abstract_planning_compute_events",
    "per_hit_dependency_validation_checks",
    "dependency_cache_entry_count_after_episode",
    "new_certificate_labels_charged_this_episode",
    "paid_certificate_labels_cumulative",
    "persistent_exact_support_group_count_after_episode",
}

_ENGINE_FIELDS = (
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
)


class ConstructionK7EpochIndexedQuotientIndependentVerifierV110Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7EpochIndexedQuotientIndependentVerifierV110Error(message)


def _content(document: Any, key: str, domain: str) -> None:
    if type(document) is not dict:
        _fail(f"V110 {key} document type changed")
    payload = {name: value for name, value in document.items() if name != key}
    if document.get(key) != domains.extension_content_id_v110(domain, payload):
        _fail(f"V110 {key} changed")


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
            _fail("V110 no-cache model replay changed")
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
            v109._v106_plan(  # noqa: SLF001
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
        _fail("V110 no-cache overlay replay changed")
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


def _per_hit(
    document: Mapping[str, Any],
    no_cache_document: Mapping[str, Any],
    acquisition: Mapping[str, Any],
    catalogue: Mapping[int, tuple[int, ...]],
    family: str,
    seed: int,
    baseline: Mapping[str, Any],
) -> dict[str, Any]:
    v109._content(  # noqa: SLF001
        document,
        "sequence_id",
        v109.domains.CONSTRUCTION_K7_DEPENDENCY_REVALIDATED_QUOTIENT_SEQUENCE_V109_DOMAIN,
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
        _fail("V110 per-hit sequence boundary changed")
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
            v109._V109_EPISODE_EXTRAS,  # noqa: SLF001
        )
        for key in _ENGINE_FIELDS:
            if episode.get(key) != no_cache_episode.get(key):
                _fail(f"V110 per-hit/no-cache engine field changed: {key}")
        if (
            episode.get("arm")
            != "DEPENDENCY_REVALIDATED_CATALOGUE_QUOTIENT_ORDERING"
            or episode.get("abstract_plan_abstention_count") != 0
            or episode.get("abstract_plan_attempt_count")
            != len(episode["abstract_plan_receipts"])
            or episode.get("abstract_plan_success_count")
            != len(episode["abstract_plan_receipts"])
        ):
            _fail("V110 per-hit plan-call inventory changed")
        rules = v106.v105._terminal_rules(candidate, rows, catalogue)  # noqa: SLF001
        wrappers = {}
        ep_hits = ep_misses = ep_compute = ep_checks = 0
        for wrapper in episode["abstract_plan_receipts"]:
            raw = wrapper["raw_state"]
            plan = wrapper["abstract_plan"]
            projected = v109._projected(candidate, raw)  # noqa: SLF001
            legal = tuple(plan["exact_legal_action_keys_at_initial_state"])
            stable = (candidate["candidate_id"], projected, legal)
            valid_entry = None
            valid_result = None
            for entry in cache[stable]:
                ep_checks += entry["dependency"]["dependency_validation_check_count"]
                result = v109._validate_dependency(  # noqa: SLF001
                    entry["dependency"], model, rules
                )
                if result is not None:
                    valid_entry = entry
                    valid_result = result
                    break
            if (
                plan["schema"]
                == "acfqp.generic_dependency_revalidated_quotient_heuristic_plan.v109"
            ):
                if valid_entry is None:
                    _fail("V110 per-hit claimed invalid cache hit")
                expected = v109._hit_plan(  # noqa: SLF001
                    source_plan=valid_entry["source_plan"],
                    dependency=valid_entry["dependency"],
                    validation=valid_result,
                    model=model,
                    legal=legal,
                    legality_source=plan["legality_support_source"],
                    failure_index=plan["legality_failure_index"],
                )
                if plan != expected:
                    _fail("V110 per-hit plan differs from replay")
                ep_hits += 1
            else:
                if valid_entry is not None:
                    _fail("V110 per-hit recomputed despite valid dependency")
                expected = v109._v106_plan(  # noqa: SLF001
                    plan, model, candidate, rows, catalogue, raw
                )
                ep_misses += 1
                ep_compute += plan["abstract_support_branch_evaluations"]
                if plan["planning_source"] == "OBSERVATION_QUOTIENT_GRAPH":
                    dependency = v109._dependency(model, plan, projected)  # noqa: SLF001
                    cache[stable].append(
                        {"source_plan": expected, "dependency": dependency}
                    )
            wrappers[tuple(raw)] = wrapper
        actual = [
            v109._receipt(  # noqa: SLF001
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
            or episode.get("actual_new_abstract_planning_compute_events") != ep_compute
            or episode.get("abstract_planning_compute_events") != ep_compute
            or episode.get("dependency_validation_checks") != ep_checks
            or episode.get("dependency_cache_entry_count_after_episode")
            != sum(len(value) for value in cache.values())
        ):
            _fail("V110 per-hit episode accounting changed")
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
    ):
        _fail("V110 per-hit aggregate changed")
    return {
        "actions": [episode["action_keys"] for episode in episodes],
        "base_receipts": [
            episode["abstract_execution_receipts"] for episode in episodes
        ],
        "lifetime_labels": document["lifetime_target_ground_support_labels"],
        "steps": document["execution_step_count"],
        "compute": compute,
        "checks": checks,
        "hits": hits,
        "misses": misses,
    }


def _adjacency(
    model: Mapping[str, Any],
) -> dict[tuple[int, ...], tuple[tuple[int, tuple[int, ...]], ...]]:
    staged: dict[tuple[int, ...], set[tuple[int, tuple[int, ...]]]] = defaultdict(set)
    for row in model["projected_edge_rows"]:
        staged[tuple(row["projected_pre"])].add(
            (row["action_key"], tuple(row["projected_post"]))
        )
    return {state: tuple(sorted(edges)) for state, edges in staged.items()}


def _transition(
    document: Any,
    *,
    previous_model: Mapping[str, Any],
    current_model: Mapping[str, Any],
    previous_rules: list[dict[str, Any]],
    current_rules: list[dict[str, Any]],
    cache: dict[tuple[Any, ...], list[dict[str, Any]]],
    entries: dict[str, dict[str, Any]],
    reverse_index: dict[tuple[int, ...], set[str]],
) -> dict[str, int]:
    before = _adjacency(previous_model)
    after = _adjacency(current_model)
    states = tuple(sorted(set(before) | set(after)))
    changed = tuple(
        state for state in states if before.get(state, ()) != after.get(state, ())
    )
    rules_changed = previous_rules != current_rules
    checks = sum(
        1 + len(before.get(state, ())) + len(after.get(state, ()))
        for state in states
    ) + len(previous_rules) + len(current_rules)
    all_ids = set(entries)
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
        "schema": "acfqp.generic_quotient_model_epoch_transition.v110",
        "previous_quotient_graph_id": previous_model["quotient_graph_id"],
        "current_quotient_graph_id": current_model["quotient_graph_id"],
        "previous_terminal_projection_rule": copy.deepcopy(previous_rules),
        "current_terminal_projection_rule": copy.deepcopy(current_rules),
        "terminal_projection_rule_changed": rules_changed,
        "changed_projected_state_rows": changed_rows,
        "changed_projected_state_count": len(changed_rows),
        "cache_entry_ids_before_transition": sorted(all_ids),
        "invalidated_dependency_receipt_ids": sorted(invalidated),
        "retained_dependency_receipt_ids": sorted(retained),
        "model_epoch_diff_checks": checks,
        "reverse_dependency_index_lookups": lookups,
        "invalidation_uses_exact_outgoing_edge_and_terminal_rule_delta": True,
        "unaffected_dependency_receipts_retained_without_per_hit_rescan": True,
        "epoch_transition_is_ordering_evidence_not_safety_authority": True,
    }
    expected = {
        **payload,
        "epoch_transition_receipt_id": domains.extension_content_id_v110(
            domains.CONSTRUCTION_K7_EPOCH_INDEXED_QUOTIENT_TRANSITION_V110_DOMAIN,
            payload,
        ),
    }
    if document != expected:
        _fail("V110 epoch transition differs from independent delta replay")
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
        entry["epoch_authorization_chain"].append(copy.deepcopy(expected))
    return {"checks": checks, "lookups": lookups, "invalidations": len(invalidated)}


def _indexed(
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
        domains.CONSTRUCTION_K7_EPOCH_INDEXED_QUOTIENT_SEQUENCE_V110_DOMAIN,
    )
    episodes = document["episodes"]
    if (
        document.get("schema") != "acfqp.generic_epoch_indexed_quotient_sequence.v110"
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
        or document.get("per_hit_dependency_validation_checks") != 0
    ):
        _fail("V110 indexed sequence boundary changed")
    candidate = baseline["candidate"]
    cache: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    entries: dict[str, dict[str, Any]] = {}
    reverse_index: dict[tuple[int, ...], set[str]] = defaultdict(set)
    all_actual = []
    transitions = []
    calls = hits = misses = compute = checks = lookups = invalidations = 0
    previous_model = None
    previous_rules = None
    for position, (episode, no_cache_episode, model, rows) in enumerate(
        zip(
            episodes,
            baseline["episodes"],
            baseline["models"],
            baseline["rows_before"],
            strict=True,
        )
    ):
        rules = v106.v105._terminal_rules(candidate, rows, catalogue)  # noqa: SLF001
        transition = episode["epoch_transition_receipt"]
        if position == 0:
            if transition is not None:
                _fail("V110 first episode unexpectedly has epoch transition")
        else:
            delta = _transition(
                transition,
                previous_model=previous_model,
                current_model=model,
                previous_rules=previous_rules,
                current_rules=rules,
                cache=cache,
                entries=entries,
                reverse_index=reverse_index,
            )
            transitions.append(copy.deepcopy(transition))
            checks += delta["checks"]
            lookups += delta["lookups"]
            invalidations += delta["invalidations"]
        v106.v103._content_id(  # noqa: SLF001
            episode,
            "episode_id",
            v106._EPISODE_DOMAIN,  # noqa: SLF001
            _V110_EPISODE_EXTRAS,
        )
        for key in _ENGINE_FIELDS:
            if episode.get(key) != no_cache_episode.get(key):
                _fail(f"V110 indexed/no-cache engine field changed: {key}")
        if (
            episode.get("arm")
            != "EPOCH_INDEXED_DEPENDENCY_REVALIDATED_QUOTIENT_ORDERING"
            or episode.get("abstract_plan_abstention_count") != 0
            or episode.get("abstract_plan_attempt_count")
            != len(episode["abstract_plan_receipts"])
            or episode.get("abstract_plan_success_count")
            != len(episode["abstract_plan_receipts"])
        ):
            _fail("V110 indexed plan-call inventory changed")
        wrappers = {}
        ep_hits = ep_misses = ep_compute = 0
        for wrapper in episode["abstract_plan_receipts"]:
            raw = wrapper["raw_state"]
            plan = wrapper["abstract_plan"]
            projected = v109._projected(candidate, raw)  # noqa: SLF001
            legal = tuple(plan["exact_legal_action_keys_at_initial_state"])
            stable = (candidate["candidate_id"], projected, legal)
            candidates = cache.get(stable, [])
            if candidates:
                entry = candidates[0]
                if entry["authorized_quotient_graph_id"] != model["quotient_graph_id"]:
                    _fail("V110 hit lacks current epoch authorization")
                chain = copy.deepcopy(entry["epoch_authorization_chain"])
                if not chain:
                    _fail("V110 cross-epoch hit lacks transition chain")
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
                expected = v109._hit_plan(  # noqa: SLF001
                    source_plan=entry["source_plan"],
                    dependency=entry["dependency"],
                    validation=validation,
                    model=model,
                    legal=legal,
                    legality_source=plan["legality_support_source"],
                    failure_index=plan["legality_failure_index"],
                )
                if plan != expected:
                    _fail("V110 epoch-authorized hit plan differs from replay")
                ep_hits += 1
            else:
                expected = v109._v106_plan(  # noqa: SLF001
                    plan, model, candidate, rows, catalogue, raw
                )
                ep_misses += 1
                ep_compute += plan["abstract_support_branch_evaluations"]
                if plan["planning_source"] == "OBSERVATION_QUOTIENT_GRAPH":
                    dependency = v109._dependency(model, plan, projected)  # noqa: SLF001
                    identity = dependency["dependency_receipt_id"]
                    entry = {
                        "source_plan": expected,
                        "dependency": dependency,
                        "authorized_quotient_graph_id": model["quotient_graph_id"],
                        "epoch_authorization_chain": [],
                    }
                    cache[stable].append(entry)
                    entries[identity] = entry
                    for row in dependency["ordered_bfs_dependency_rows"]:
                        reverse_index[tuple(row["projected_state"])].add(identity)
            wrappers[tuple(raw)] = wrapper
        actual = [
            v109._receipt(  # noqa: SLF001
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
            episode.get("epoch_indexed_orderer_call_count") != ep_calls
            or episode.get("epoch_authorized_cache_hit_count") != ep_hits
            or episode.get("epoch_cache_miss_count") != ep_misses
            or episode.get("actual_new_abstract_planning_compute_events") != ep_compute
            or episode.get("abstract_planning_compute_events") != ep_compute
            or episode.get("per_hit_dependency_validation_checks") != 0
            or episode.get("dependency_cache_entry_count_after_episode") != len(entries)
        ):
            _fail("V110 indexed episode accounting changed")
        calls += ep_calls
        hits += ep_hits
        misses += ep_misses
        compute += ep_compute
        all_actual.extend(actual)
        previous_model = model
        previous_rules = rules
    if (
        document.get("model_epoch_transition_receipts") != transitions
        or document.get("all_actual_legality_conditioned_execution_receipts")
        != all_actual
        or document.get("actual_legality_conditioned_execution_receipt_count")
        != len(all_actual)
        or document.get("execution_step_count") != baseline["steps"]
        or document.get("epoch_indexed_orderer_call_count") != calls
        or document.get("epoch_authorized_cache_hit_count") != hits
        or document.get("epoch_cache_miss_count") != misses
        or document.get("dependency_cache_entry_count") != len(entries)
        or document.get("actual_new_abstract_planning_compute_events") != compute
        or document.get("model_epoch_diff_checks") != checks
        or document.get("reverse_dependency_index_lookups") != lookups
        or document.get("dependency_cache_entry_invalidations") != invalidations
        or document.get("per_hit_dependency_validation_checks") != 0
        or document.get(
            "model_epoch_maintenance_and_planning_compute_reported_separately"
        )
        is not True
    ):
        _fail("V110 indexed sequence aggregate changed")
    return {
        "actions": [episode["action_keys"] for episode in episodes],
        "base_receipts": [
            episode["abstract_execution_receipts"] for episode in episodes
        ],
        "lifetime_labels": document["lifetime_target_ground_support_labels"],
        "initial_labels": document[
            "initial_acquisition_ground_support_labels_paid_once"
        ],
        "certificate_labels": document["certificate_ground_support_labels_paid_once"],
        "steps": document["execution_step_count"],
        "compute": compute,
        "checks": checks,
        "lookups": lookups,
        "invalidations": invalidations,
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
        _fail("V110 direct sequence changed")
    labels = 0
    for index, episode in zip(EPISODES, document["episodes"], strict=True):
        v106.v103._content_id(  # noqa: SLF001
            episode,
            "episode_id",
            v106.v103._DIRECT_EPISODE_DOMAIN,  # noqa: SLF001
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
            _fail("V110 direct episode changed")
        charged = sum(row["ground_support_labels"] for row in distinctions)
        if episode["incremental_certificate_local_ground_support_labels"] != charged:
            _fail("V110 direct labels changed")
        labels += charged
    if document["lifetime_target_ground_support_labels"] != labels:
        _fail("V110 direct lifetime labels changed")
    return labels


def _occurrence(document: Any, family: str, seed: int) -> dict[str, Any]:
    _content(
        document,
        "occurrence_id",
        domains.CONSTRUCTION_K7_EPOCH_INDEXED_QUOTIENT_OCCURRENCE_V110_DOMAIN,
    )
    if (
        document.get("schema") != "acfqp.epoch_indexed_quotient_occurrence.v110"
        or document.get("target_family") != family
        or document.get("seed") != seed
        or document.get("episode_indices") != list(EPISODES)
    ):
        _fail("V110 occurrence identity changed")
    catalogue = v109.v108.v107._catalogue(  # noqa: SLF001
        document["complete_anonymous_action_catalogue_receipt"], family, seed
    )
    acquisition = document["partial_acquisition"]
    no_cache_document = document["matched_no_cache_legality_quotient_sequence"]
    baseline = _no_cache(no_cache_document, acquisition, catalogue, family, seed)
    per_hit = _per_hit(
        document["matched_per_hit_dependency_revalidated_sequence"],
        no_cache_document,
        acquisition,
        catalogue,
        family,
        seed,
        baseline,
    )
    indexed_document = document["persistent_epoch_indexed_quotient_sequence"]
    indexed = _indexed(
        indexed_document,
        no_cache_document,
        acquisition,
        catalogue,
        family,
        seed,
        baseline,
    )
    direct = _direct(
        document["strict_cold_direct_sequence"],
        family,
        seed,
        acquisition["candidate"]["candidate_id"],
    )
    utilization = v109._utilization(indexed_document)  # noqa: SLF001
    exact = (
        indexed["actions"] == per_hit["actions"] == baseline["actions"]
        and indexed["base_receipts"]
        == per_hit["base_receipts"]
        == baseline["base_receipts"]
        and indexed["lifetime_labels"]
        == per_hit["lifetime_labels"]
        == baseline["lifetime_labels"]
        and indexed["steps"] == per_hit["steps"] == baseline["steps"]
    )
    maintenance = indexed["checks"] + indexed["lookups"]
    gate = {
        "indexed_per_hit_and_no_cache_actions_base_receipts_labels_and_steps_equal": exact,
        "indexed_and_per_hit_new_planning_compute_equal": indexed["compute"]
        == per_hit["compute"],
        "indexed_new_planning_compute_strictly_below_no_cache": indexed["compute"]
        < baseline["planning_compute"],
        "epoch_indexed_dependency_maintenance_strictly_below_per_hit_validation": maintenance
        < per_hit["checks"],
        "epoch_authorized_cache_hit_observed": indexed["hits"] > 0,
        "per_hit_dependency_rescan_count_is_zero": True,
        "quotient_model_orders_at_least_three_quarters": utilization[
            "quotient_actually_orders_at_least_three_quarters_of_execution"
        ],
        "chosen_action_matches_quotient_strict_majority": utilization[
            "chosen_action_matches_quotient_strict_majority"
        ],
        "certificate_failure_only_query_discipline_clean": indexed_document[
            "every_new_ground_query_followed_a_failed_certificate"
        ],
        "later_zero_label_quotient_reuse_observed": indexed["later_zero"],
        "quotient_lifetime_labels_strictly_below_cold_direct": indexed[
            "lifetime_labels"
        ]
        < direct,
    }
    gate["passed"] = all(gate.values())
    accounting = {
        "initial_acquisition_labels": indexed["initial_labels"],
        "certificate_local_labels": indexed["certificate_labels"],
        "epoch_indexed_quotient_lifetime_target_labels": indexed["lifetime_labels"],
        "per_hit_quotient_lifetime_target_labels": per_hit["lifetime_labels"],
        "no_cache_quotient_lifetime_target_labels": baseline["lifetime_labels"],
        "cold_direct_lifetime_target_labels": direct,
        "target_label_reduction_against_cold_direct": direct
        - indexed["lifetime_labels"],
        "execution_steps": indexed["steps"],
        "epoch_indexed_new_planning_compute_events": indexed["compute"],
        "per_hit_new_planning_compute_events": per_hit["compute"],
        "no_cache_planning_compute_events": baseline["planning_compute"],
        "planning_compute_events_avoided_against_no_cache": baseline[
            "planning_compute"
        ]
        - indexed["compute"],
        "model_epoch_diff_checks": indexed["checks"],
        "reverse_dependency_index_lookups": indexed["lookups"],
        "epoch_indexed_dependency_maintenance_events": maintenance,
        "per_hit_dependency_validation_checks": per_hit["checks"],
        "dependency_maintenance_events_avoided": per_hit["checks"] - maintenance,
        "sample_labels_execution_steps_planning_and_both_validation_axes_separate": True,
        "scalar_cost_aggregation_performed": False,
    }
    if (
        document["legality_conditioned_quotient_utilization"] != utilization
        or document["accounting"] != accounting
        or document["registered_gate"] != gate
        or document["epoch_indexed_invalidation_preserves_actions_labels_and_steps"]
        != gate["passed"]
        or document[
            "local_ground_distinctions_only_after_certificate_failure_verified"
        ]
        != gate["passed"]
        or document["cached_heuristic_used_as_safety_authority"] is not False
        or document["complete_ground_world_model_synthesized"] is not False
        or document["official_scalar_cost"] is not None
        or document["WORKLOAD_ECONOMICS_GATE"] != "NOT_RUN"
    ):
        _fail("V110 occurrence Gate or claim boundary changed")
    return {
        "target_family": family,
        "seed": seed,
        "gate_passed": gate["passed"],
        **accounting,
        "epoch_authorized_cache_hits": indexed["hits"],
        "epoch_cache_misses": indexed["misses"],
        "dependency_cache_entry_invalidations": indexed["invalidations"],
    }


def verify_epoch_indexed_quotient_campaign_bytes_v110(raw: bytes) -> dict[str, Any]:
    if (
        type(raw) is not bytes
        or len(raw) != CAMPAIGN_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != CAMPAIGN_SHA256
    ):
        _fail("V110 campaign bytes changed")
    document = loads_canonical_json(raw)
    if canonical_json_bytes(document) != raw:
        _fail("V110 campaign is noncanonical")
    _content(
        document,
        "campaign_id",
        domains.CONSTRUCTION_K7_EPOCH_INDEXED_QUOTIENT_CAMPAIGN_V110_DOMAIN,
    )
    rows = document.get("target_occurrences")
    if (
        document.get("campaign_id") != CAMPAIGN_ID
        or document.get("schema") != "acfqp.epoch_indexed_quotient_campaign.v110"
        or document.get("preregistration_id") != PREREGISTRATION_ID
        or document.get("v109_campaign_id") != V109_CAMPAIGN_ID
        or document.get("v109_verification_id") != V109_VERIFICATION_ID
        or type(rows) is not list
        or len(rows) != len(TARGETS)
    ):
        _fail("V110 campaign inventory changed")
    replay = [
        _occurrence(row, family, seed)
        for row, (family, seed) in zip(rows, TARGETS, strict=True)
    ]
    keys = (
        "initial_acquisition_labels",
        "certificate_local_labels",
        "epoch_indexed_quotient_lifetime_target_labels",
        "per_hit_quotient_lifetime_target_labels",
        "no_cache_quotient_lifetime_target_labels",
        "cold_direct_lifetime_target_labels",
        "target_label_reduction_against_cold_direct",
        "execution_steps",
        "epoch_indexed_new_planning_compute_events",
        "per_hit_new_planning_compute_events",
        "no_cache_planning_compute_events",
        "planning_compute_events_avoided_against_no_cache",
        "model_epoch_diff_checks",
        "reverse_dependency_index_lookups",
        "epoch_indexed_dependency_maintenance_events",
        "per_hit_dependency_validation_checks",
        "dependency_maintenance_events_avoided",
    )
    totals = {key: sum(row[key] for row in replay) for key in keys}
    accounting = {
        **totals,
        "offline_source_labels_not_recharged": True,
        "sample_labels_execution_steps_planning_and_both_validation_axes_separate": True,
        "scalar_cost_aggregation_performed": False,
    }
    ood = v106.v105._ood(  # noqa: SLF001
        document["incompatible_schema_no_transfer_control"]
    )
    passed = (
        all(row["gate_passed"] for row in replay)
        and totals["epoch_indexed_dependency_maintenance_events"]
        < totals["per_hit_dependency_validation_checks"]
        and totals["epoch_indexed_quotient_lifetime_target_labels"]
        < totals["cold_direct_lifetime_target_labels"]
        and ood["strict_ood_no_transfer"] is True
    )
    gate = {
        "required_target_occurrence_count": 4,
        "passed_target_occurrence_count": sum(row["gate_passed"] for row in replay),
        "every_occurrence_exactly_matches_per_hit_and_no_cache_execution": all(
            row["epoch_indexed_quotient_lifetime_target_labels"]
            == row["per_hit_quotient_lifetime_target_labels"]
            == row["no_cache_quotient_lifetime_target_labels"]
            for row in replay
        ),
        "every_occurrence_dependency_maintenance_strictly_reduced": all(
            row["epoch_indexed_dependency_maintenance_events"]
            < row["per_hit_dependency_validation_checks"]
            for row in replay
        ),
        "aggregate_quotient_labels_strictly_below_cold_direct": totals[
            "epoch_indexed_quotient_lifetime_target_labels"
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
        or document["registered_epoch_indexed_dependency_invalidation_verified"]
        != passed
        or document[
            "ground_distinctions_acquired_only_after_certificate_failure_verified"
        ]
        != passed
        or document["cached_heuristic_used_as_safety_authority"] is not False
        or document["global_lumpability_claimed"] is not False
        or document["complete_ground_world_model_synthesized"] is not False
        or document["arbitrary_domain_transfer_claimed"] is not False
        or document["official_execution_allowed"] is not False
        or document["official_scalar_cost"] is not None
        or document["official_N_break_even"] is not None
        or document["WORKLOAD_ECONOMICS_GATE"] != "NOT_RUN"
        or document["COUNTER_COMPLETENESS_GATE"] != "NOT_RUN"
    ):
        _fail("V110 campaign Gate or claim boundary changed")
    failed = [
        (row["target_family"], row["seed"], row["dependency_maintenance_events_avoided"])
        for row in replay
        if not row["gate_passed"]
    ]
    if failed != [("MAINTENANCE_CASCADE", 1_022_103, -2)]:
        _fail("V110 failed occurrence identity changed")
    return {
        "schema": "acfqp.epoch_indexed_quotient_verification.v110",
        "campaign_id": CAMPAIGN_ID,
        "preregistration_id": PREREGISTRATION_ID,
        "verification_status": "REGISTERED_V110_EPOCH_MAINTENANCE_GATE_FAILED",
        "producer_free_complete_catalogue_and_plan_replay": True,
        "producer_free_minimal_bfs_dependency_reconstruction": True,
        "producer_free_epoch_delta_and_reverse_index_reconstruction": True,
        "producer_free_cache_order_hit_miss_and_invalidation_reconstruction": True,
        "producer_free_per_action_receipt_reconstruction": True,
        "producer_summary_counts_not_used": True,
        "verified_occurrences": replay,
        "verified_accounting": accounting,
        "verified_epoch_authorized_cache_hit_count": sum(
            row["epoch_authorized_cache_hits"] for row in replay
        ),
        "verified_epoch_cache_miss_count": sum(
            row["epoch_cache_misses"] for row in replay
        ),
        "verified_dependency_cache_entry_invalidations": sum(
            row["dependency_cache_entry_invalidations"] for row in replay
        ),
        "registered_gate_independently_verified": passed,
        "registered_failure_reason": "ONE_SMALL_MAINTENANCE_OCCURRENCE_EPOCH_MAINTENANCE_EXCEEDED_PER_HIT_VALIDATION_BY_TWO_EVENTS",
        "fresh_successor_required": True,
        "cached_heuristic_used_as_safety_authority": False,
        "global_lumpability_claimed": False,
        "complete_ground_world_model_synthesized": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }


def freeze_epoch_indexed_quotient_verification_v110(raw: bytes) -> bytes:
    payload = verify_epoch_indexed_quotient_campaign_bytes_v110(raw)
    document = {
        **payload,
        "verification_id": domains.extension_content_id_v110(
            domains.CONSTRUCTION_K7_EPOCH_INDEXED_QUOTIENT_VERIFICATION_V110_DOMAIN,
            payload,
        ),
    }
    result = canonical_json_bytes(document)
    if VERIFICATION_ID != "0" * 64 and (
        document["verification_id"] != VERIFICATION_ID
        or len(result) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(result).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("V110 verification changed")
    return result


__all__ = (
    "VERIFICATION_ID",
    "freeze_epoch_indexed_quotient_verification_v110",
    "verify_epoch_indexed_quotient_campaign_bytes_v110",
)
