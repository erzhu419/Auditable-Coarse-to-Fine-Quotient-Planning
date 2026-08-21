"""Producer-free V111 replay of identity short circuits and matched epochs."""

from __future__ import annotations

from collections import defaultdict
import copy
import hashlib
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v111 as domains
from acfqp import construction_k7_epoch_indexed_quotient_independent_verifier_v110 as v110
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "378f333008191bdb338182c787547aeb80f4fa27b612f499043b20163a6327f5"
CAMPAIGN_BYTE_COUNT = 19_377_728
CAMPAIGN_SHA256 = "9aa43e94e150c085c155db2115ce01cc1447b7547f72b29c128392b972072efc"
PREREGISTRATION_ID = "22642fa7df8eb182748bdb821f8a8d8281f274379565ddf63acc191b175465f7"
V110_CAMPAIGN_ID = "9efd58cd7d285b4f29b86ba8d750bac1569eea3d58027293c4699f48845b7ca7"
V110_VERIFICATION_ID = "f40981fb930d3662d6a66ff8794b2899bf7153dd21474b2bac82be882c842209"
TARGETS = (
    ("BALANCED_BATCH_REFINEMENT", 1_023_101),
    ("BALANCED_BATCH_REFINEMENT", 1_023_102),
    ("MAINTENANCE_CASCADE", 1_023_103),
    ("MAINTENANCE_CASCADE", 1_023_104),
)
EPISODES = (201, 202, 203)
VERIFICATION_ID = "e648b69d758ba92816777d5a7f1ea9eee1663c6a6bed1a2585f7e0d8f5814184"
EXPECTED_CANONICAL_BYTE_COUNT = 7_347
EXPECTED_CANONICAL_SHA256 = "a9e46fa203572cf800b1789a8979abd202c97f870cbf70bce1721abed1cf10b8"

v109 = v110.v109
v106 = v110.v106


class ConstructionK7IdentityShortCircuitedEpochIndependentVerifierV111Error(
    ValueError
):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7IdentityShortCircuitedEpochIndependentVerifierV111Error(
        message
    )


def _content(document: Any, key: str, domain: str) -> None:
    if type(document) is not dict:
        _fail(f"V111 {key} document type changed")
    payload = {name: value for name, value in document.items() if name != key}
    if document.get(key) != domains.extension_content_id_v111(domain, payload):
        _fail(f"V111 {key} changed")


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
            _fail("V111 no-cache model replay changed")
        rows_before.append(rows)
        models.append(model)
        _actual, rows, charged, _fallback, _actual_fallback = v106._episode(  # noqa: SLF001
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
    if rows != final_rows:
        _fail("V111 no-cache overlay replay changed")
    return {
        "candidate": candidate,
        "rows_before": rows_before,
        "models": models,
        "episodes": episodes,
        "actions": [episode["action_keys"] for episode in episodes],
        "base_receipts": [
            episode["abstract_execution_receipts"] for episode in episodes
        ],
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
        or document.get("quotient_models_before_each_episode")
        != no_cache_document["quotient_models_before_each_episode"]
        or document.get("persistent_exact_overlay_rows")
        != no_cache_document["persistent_exact_overlay_rows"]
    ):
        _fail("V111 per-hit sequence boundary changed")
    candidate = baseline["candidate"]
    cache: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
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
        for key in v110._ENGINE_FIELDS:  # noqa: SLF001
            if episode.get(key) != no_cache_episode.get(key):
                _fail(f"V111 per-hit/no-cache engine field changed: {key}")
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
                    _fail("V111 per-hit claimed invalid cache hit")
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
                    _fail("V111 per-hit plan replay changed")
                ep_hits += 1
            else:
                if valid_entry is not None:
                    _fail("V111 per-hit recomputed despite valid dependency")
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
            or episode.get("actual_legality_conditioned_execution_receipts")
            != actual
        ):
            _fail("V111 per-hit episode accounting changed")
        calls += ep_calls
        hits += ep_hits
        misses += ep_misses
        compute += ep_compute
        checks += ep_checks
    if (
        document.get("dependency_cache_orderer_call_count") != calls
        or document.get("dependency_revalidated_cache_hit_count") != hits
        or document.get("dependency_cache_miss_count") != misses
        or document.get("actual_new_abstract_planning_compute_events") != compute
        or document.get("dependency_validation_checks") != checks
    ):
        _fail("V111 per-hit aggregate changed")
    return {
        "actions": [episode["action_keys"] for episode in episodes],
        "base_receipts": [
            episode["abstract_execution_receipts"] for episode in episodes
        ],
        "lifetime_labels": document["lifetime_target_ground_support_labels"],
        "steps": document["execution_step_count"],
        "compute": compute,
        "checks": checks,
    }


def _identity_transition(
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
    same = previous_model["quotient_graph_id"] == current_model["quotient_graph_id"]
    all_ids = set(entries)
    if same:
        changed: tuple[tuple[int, ...], ...] = ()
        changed_rows: list[dict[str, Any]] = []
        rules_changed = False
        diff_checks = lookups = 0
        invalidated: set[str] = set()
        retained = set(all_ids)
    else:
        before = v110._adjacency(previous_model)  # noqa: SLF001
        after = v110._adjacency(current_model)  # noqa: SLF001
        states = tuple(sorted(set(before) | set(after)))
        changed = tuple(
            state
            for state in states
            if before.get(state, ()) != after.get(state, ())
        )
        rules_changed = previous_rules != current_rules
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
        "quotient_graph_identity_equal": same,
        "identity_short_circuit_applied": same,
        "previous_terminal_projection_rule": copy.deepcopy(previous_rules),
        "current_terminal_projection_rule": copy.deepcopy(current_rules),
        "terminal_projection_rule_changed": rules_changed,
        "changed_projected_state_rows": changed_rows,
        "changed_projected_state_count": len(changed_rows),
        "cache_entry_ids_before_transition": sorted(all_ids),
        "invalidated_dependency_receipt_ids": sorted(invalidated),
        "retained_dependency_receipt_ids": sorted(retained),
        "model_epoch_identity_checks": 1,
        "full_model_epoch_diff_checks": diff_checks,
        "reverse_dependency_index_lookups": lookups,
        "same_content_address_skips_full_graph_and_dependency_scan": same,
        "changed_content_address_uses_exact_outgoing_edge_and_terminal_rule_delta": not same,
        "unaffected_dependency_receipts_retained_without_per_hit_rescan": True,
        "epoch_transition_is_ordering_evidence_not_safety_authority": True,
    }
    expected = {
        **payload,
        "epoch_transition_receipt_id": domains.extension_content_id_v111(
            domains.CONSTRUCTION_K7_IDENTITY_SHORT_CIRCUITED_EPOCH_TRANSITION_V111_DOMAIN,
            payload,
        ),
    }
    if document != expected:
        _fail("V111 identity transition replay changed")
    _update_cache(
        expected, cache=cache, entries=entries, reverse_index=reverse_index
    )
    return {
        "identity": 1,
        "diff": diff_checks,
        "lookups": lookups,
        "invalidations": len(invalidated),
        "short": int(same),
    }


def _update_cache(
    receipt: Mapping[str, Any],
    *,
    cache: dict[tuple[Any, ...], list[dict[str, Any]]],
    entries: dict[str, dict[str, Any]],
    reverse_index: dict[tuple[int, ...], set[str]],
) -> None:
    invalidated = set(receipt["invalidated_dependency_receipt_ids"])
    retained = set(receipt["retained_dependency_receipt_ids"])
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
        entry["authorized_quotient_graph_id"] = receipt[
            "current_quotient_graph_id"
        ]
        entry["epoch_authorization_chain"].append(copy.deepcopy(receipt))


def _epoch_sequence(
    document: Mapping[str, Any],
    no_cache_document: Mapping[str, Any],
    acquisition: Mapping[str, Any],
    catalogue: Mapping[int, tuple[int, ...]],
    family: str,
    seed: int,
    baseline: Mapping[str, Any],
    *,
    identity_short: bool,
) -> dict[str, Any]:
    if identity_short:
        _content(
            document,
            "sequence_id",
            domains.CONSTRUCTION_K7_IDENTITY_SHORT_CIRCUITED_EPOCH_SEQUENCE_V111_DOMAIN,
        )
        schema = "acfqp.generic_identity_short_circuited_epoch_sequence.v111"
        arm = "IDENTITY_SHORT_CIRCUITED_EPOCH_INDEXED_QUOTIENT_ORDERING"
    else:
        v110._content(  # noqa: SLF001
            document,
            "sequence_id",
            v110.domains.CONSTRUCTION_K7_EPOCH_INDEXED_QUOTIENT_SEQUENCE_V110_DOMAIN,
        )
        schema = "acfqp.generic_epoch_indexed_quotient_sequence.v110"
        arm = "EPOCH_INDEXED_DEPENDENCY_REVALIDATED_QUOTIENT_ORDERING"
    episodes = document["episodes"]
    if (
        document.get("schema") != schema
        or document.get("family") != family
        or document.get("seed") != seed
        or document.get("episode_indices") != list(EPISODES)
        or document.get("partial_candidate_id")
        != acquisition["candidate"]["candidate_id"]
        or document.get("quotient_models_before_each_episode")
        != no_cache_document["quotient_models_before_each_episode"]
        or document.get("persistent_exact_overlay_rows")
        != no_cache_document["persistent_exact_overlay_rows"]
    ):
        _fail("V111 epoch sequence boundary changed")
    candidate = baseline["candidate"]
    cache: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    entries: dict[str, dict[str, Any]] = {}
    reverse_index: dict[tuple[int, ...], set[str]] = defaultdict(set)
    transitions = []
    calls = hits = misses = compute = identity = diff = lookups = invalidations = short = 0
    previous_model = previous_rules = None
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
                _fail("V111 first epoch transition must be null")
        else:
            if identity_short:
                delta = _identity_transition(
                    transition,
                    previous_model=previous_model,
                    current_model=model,
                    previous_rules=previous_rules,
                    current_rules=rules,
                    cache=cache,
                    entries=entries,
                    reverse_index=reverse_index,
                )
                identity += delta["identity"]
                diff += delta["diff"]
                short += delta["short"]
            else:
                delta = v110._transition(  # noqa: SLF001
                    transition,
                    previous_model=previous_model,
                    current_model=model,
                    previous_rules=previous_rules,
                    current_rules=rules,
                    cache=cache,
                    entries=entries,
                    reverse_index=reverse_index,
                )
                diff += delta["checks"]
            lookups += delta["lookups"]
            invalidations += delta["invalidations"]
            transitions.append(copy.deepcopy(transition))
        v106.v103._content_id(  # noqa: SLF001
            episode,
            "episode_id",
            v106._EPISODE_DOMAIN,  # noqa: SLF001
            v110._V110_EPISODE_EXTRAS,  # noqa: SLF001
        )
        for key in v110._ENGINE_FIELDS:  # noqa: SLF001
            if episode.get(key) != no_cache_episode.get(key):
                _fail(f"V111 epoch/no-cache engine field changed: {key}")
        if episode.get("arm") != arm:
            _fail("V111 epoch arm changed")
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
                    _fail("V111 epoch-authorized plan replay changed")
                ep_hits += 1
            else:
                expected = v109._v106_plan(  # noqa: SLF001
                    plan, model, candidate, rows, catalogue, raw
                )
                ep_misses += 1
                ep_compute += plan["abstract_support_branch_evaluations"]
                if plan["planning_source"] == "OBSERVATION_QUOTIENT_GRAPH":
                    dependency = v109._dependency(model, plan, projected)  # noqa: SLF001
                    identity_key = dependency["dependency_receipt_id"]
                    entry = {
                        "source_plan": expected,
                        "dependency": dependency,
                        "authorized_quotient_graph_id": model["quotient_graph_id"],
                        "epoch_authorization_chain": [],
                    }
                    cache[stable].append(entry)
                    entries[identity_key] = entry
                    for row in dependency["ordered_bfs_dependency_rows"]:
                        reverse_index[tuple(row["projected_state"])].add(identity_key)
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
            or episode.get("actual_legality_conditioned_execution_receipts")
            != actual
        ):
            _fail("V111 epoch episode accounting changed")
        calls += ep_calls
        hits += ep_hits
        misses += ep_misses
        compute += ep_compute
        previous_model = model
        previous_rules = rules
    if (
        document.get("model_epoch_transition_receipts") != transitions
        or document.get("epoch_indexed_orderer_call_count") != calls
        or document.get("epoch_authorized_cache_hit_count") != hits
        or document.get("epoch_cache_miss_count") != misses
        or document.get("actual_new_abstract_planning_compute_events") != compute
        or document.get("reverse_dependency_index_lookups") != lookups
        or document.get("dependency_cache_entry_invalidations") != invalidations
        or document.get("per_hit_dependency_validation_checks") != 0
    ):
        _fail("V111 epoch aggregate changed")
    if identity_short:
        if (
            document.get("model_epoch_identity_checks") != identity
            or document.get("full_model_epoch_diff_checks") != diff
            or document.get("identity_short_circuit_count") != short
        ):
            _fail("V111 identity short-circuit accounting changed")
    elif document.get("model_epoch_diff_checks") != diff:
        _fail("V111 full-diff accounting changed")
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
        "identity": identity,
        "diff": diff,
        "lookups": lookups,
        "invalidations": invalidations,
        "short": short,
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
        or document.get("family") != family
        or document.get("seed") != seed
        or document.get("episode_indices") != list(EPISODES)
    ):
        _fail("V111 direct sequence changed")
    labels = 0
    for index, episode in zip(EPISODES, document["episodes"], strict=True):
        v106.v103._content_id(  # noqa: SLF001
            episode,
            "episode_id",
            v106.v103._DIRECT_EPISODE_DOMAIN,  # noqa: SLF001
        )
        if (
            episode.get("episode_index") != index
            or episode.get("target_candidate_id") != candidate_id
            or episode.get("success") is not True
        ):
            _fail("V111 direct episode changed")
        labels += sum(
            row["ground_support_labels"] for row in episode["local_distinctions"]
        )
    if document["lifetime_target_ground_support_labels"] != labels:
        _fail("V111 direct labels changed")
    return labels


def _occurrence(document: Any, family: str, seed: int) -> dict[str, Any]:
    _content(
        document,
        "occurrence_id",
        domains.CONSTRUCTION_K7_IDENTITY_SHORT_CIRCUITED_EPOCH_OCCURRENCE_V111_DOMAIN,
    )
    if (
        document.get("schema")
        != "acfqp.identity_short_circuited_epoch_occurrence.v111"
        or document.get("target_family") != family
        or document.get("seed") != seed
        or document.get("episode_indices") != list(EPISODES)
    ):
        _fail("V111 occurrence identity changed")
    catalogue = v109.v108.v107._catalogue(  # noqa: SLF001
        document["complete_anonymous_action_catalogue_receipt"], family, seed
    )
    acquisition = document["partial_acquisition"]
    no_cache_doc = document["matched_no_cache_legality_quotient_sequence"]
    baseline = _no_cache(no_cache_doc, acquisition, catalogue, family, seed)
    per_hit = _per_hit(
        document["matched_per_hit_dependency_revalidated_sequence"],
        no_cache_doc,
        acquisition,
        catalogue,
        family,
        seed,
        baseline,
    )
    full_diff = _epoch_sequence(
        document["matched_full_diff_epoch_sequence"],
        no_cache_doc,
        acquisition,
        catalogue,
        family,
        seed,
        baseline,
        identity_short=False,
    )
    short_document = document["persistent_identity_short_circuited_epoch_sequence"]
    short = _epoch_sequence(
        short_document,
        no_cache_doc,
        acquisition,
        catalogue,
        family,
        seed,
        baseline,
        identity_short=True,
    )
    direct = _direct(
        document["strict_cold_direct_sequence"],
        family,
        seed,
        acquisition["candidate"]["candidate_id"],
    )
    utilization = v109._utilization(short_document)  # noqa: SLF001
    exact = (
        short["actions"] == full_diff["actions"] == per_hit["actions"] == baseline["actions"]
        and short["base_receipts"]
        == full_diff["base_receipts"]
        == per_hit["base_receipts"]
        == baseline["base_receipts"]
        and short["lifetime_labels"]
        == full_diff["lifetime_labels"]
        == per_hit["lifetime_labels"]
        == baseline["lifetime_labels"]
        and short["steps"] == full_diff["steps"] == per_hit["steps"] == baseline["steps"]
    )
    short_maintenance = short["identity"] + short["diff"] + short["lookups"]
    full_maintenance = full_diff["diff"] + full_diff["lookups"]
    gate = {
        "identity_short_full_diff_per_hit_and_no_cache_execution_equal": exact,
        "all_reuse_arms_new_planning_compute_equal": short["compute"]
        == full_diff["compute"]
        == per_hit["compute"],
        "identity_short_new_planning_compute_strictly_below_no_cache": short[
            "compute"
        ]
        < baseline["planning_compute"],
        "identity_short_dependency_maintenance_strictly_below_per_hit_validation": short_maintenance
        < per_hit["checks"],
        "identity_short_dependency_maintenance_not_above_full_diff": short_maintenance
        <= full_maintenance,
        "epoch_authorized_cache_hit_observed": short["hits"] > 0,
        "per_hit_dependency_rescan_count_is_zero": True,
        "quotient_model_orders_at_least_three_quarters": utilization[
            "quotient_actually_orders_at_least_three_quarters_of_execution"
        ],
        "chosen_action_matches_quotient_strict_majority": utilization[
            "chosen_action_matches_quotient_strict_majority"
        ],
        "certificate_failure_only_query_discipline_clean": short_document[
            "every_new_ground_query_followed_a_failed_certificate"
        ],
        "later_zero_label_quotient_reuse_observed": short["later_zero"],
        "quotient_lifetime_labels_strictly_below_cold_direct": short[
            "lifetime_labels"
        ]
        < direct,
    }
    gate["passed"] = all(gate.values())
    accounting = {
        "initial_acquisition_labels": short["initial_labels"],
        "certificate_local_labels": short["certificate_labels"],
        "identity_short_quotient_lifetime_target_labels": short["lifetime_labels"],
        "full_diff_quotient_lifetime_target_labels": full_diff["lifetime_labels"],
        "per_hit_quotient_lifetime_target_labels": per_hit["lifetime_labels"],
        "no_cache_quotient_lifetime_target_labels": baseline["lifetime_labels"],
        "cold_direct_lifetime_target_labels": direct,
        "target_label_reduction_against_cold_direct": direct - short["lifetime_labels"],
        "execution_steps": short["steps"],
        "identity_short_new_planning_compute_events": short["compute"],
        "full_diff_new_planning_compute_events": full_diff["compute"],
        "per_hit_new_planning_compute_events": per_hit["compute"],
        "no_cache_planning_compute_events": baseline["planning_compute"],
        "planning_compute_events_avoided_against_no_cache": baseline[
            "planning_compute"
        ]
        - short["compute"],
        "model_epoch_identity_checks": short["identity"],
        "full_model_epoch_diff_checks": short["diff"],
        "reverse_dependency_index_lookups": short["lookups"],
        "identity_short_dependency_maintenance_events": short_maintenance,
        "full_diff_dependency_maintenance_events": full_maintenance,
        "per_hit_dependency_validation_checks": per_hit["checks"],
        "maintenance_events_avoided_against_full_diff": full_maintenance
        - short_maintenance,
        "maintenance_events_avoided_against_per_hit": per_hit["checks"]
        - short_maintenance,
        "identity_short_circuit_count": short["short"],
        "sample_labels_execution_steps_planning_and_all_maintenance_axes_separate": True,
        "scalar_cost_aggregation_performed": False,
    }
    if (
        document["legality_conditioned_quotient_utilization"] != utilization
        or document["registered_gate"] != gate
        or document["accounting"] != accounting
        or document["identity_short_circuit_preserves_actions_labels_and_steps"]
        != gate["passed"]
        or document["cached_heuristic_used_as_safety_authority"] is not False
        or document["official_scalar_cost"] is not None
    ):
        _fail("V111 occurrence Gate changed")
    return {
        "target_family": family,
        "seed": seed,
        "gate_passed": gate["passed"],
        **accounting,
        "cache_hits": short["hits"],
        "cache_misses": short["misses"],
        "invalidations": short["invalidations"],
    }


def verify_identity_short_circuited_epoch_campaign_bytes_v111(
    raw: bytes,
) -> dict[str, Any]:
    if (
        type(raw) is not bytes
        or len(raw) != CAMPAIGN_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != CAMPAIGN_SHA256
    ):
        _fail("V111 campaign bytes changed")
    document = loads_canonical_json(raw)
    if canonical_json_bytes(document) != raw:
        _fail("V111 campaign is noncanonical")
    _content(
        document,
        "campaign_id",
        domains.CONSTRUCTION_K7_IDENTITY_SHORT_CIRCUITED_EPOCH_CAMPAIGN_V111_DOMAIN,
    )
    rows = document.get("target_occurrences")
    if (
        document.get("campaign_id") != CAMPAIGN_ID
        or document.get("schema")
        != "acfqp.identity_short_circuited_epoch_campaign.v111"
        or document.get("preregistration_id") != PREREGISTRATION_ID
        or document.get("v110_failed_campaign_id") != V110_CAMPAIGN_ID
        or document.get("v110_failed_verification_id") != V110_VERIFICATION_ID
        or type(rows) is not list
        or len(rows) != len(TARGETS)
    ):
        _fail("V111 campaign inventory changed")
    replay = [
        _occurrence(row, family, seed)
        for row, (family, seed) in zip(rows, TARGETS, strict=True)
    ]
    keys = (
        "initial_acquisition_labels",
        "certificate_local_labels",
        "identity_short_quotient_lifetime_target_labels",
        "full_diff_quotient_lifetime_target_labels",
        "per_hit_quotient_lifetime_target_labels",
        "no_cache_quotient_lifetime_target_labels",
        "cold_direct_lifetime_target_labels",
        "target_label_reduction_against_cold_direct",
        "execution_steps",
        "identity_short_new_planning_compute_events",
        "full_diff_new_planning_compute_events",
        "per_hit_new_planning_compute_events",
        "no_cache_planning_compute_events",
        "planning_compute_events_avoided_against_no_cache",
        "model_epoch_identity_checks",
        "full_model_epoch_diff_checks",
        "reverse_dependency_index_lookups",
        "identity_short_dependency_maintenance_events",
        "full_diff_dependency_maintenance_events",
        "per_hit_dependency_validation_checks",
        "maintenance_events_avoided_against_full_diff",
        "maintenance_events_avoided_against_per_hit",
        "identity_short_circuit_count",
    )
    totals = {key: sum(row[key] for row in replay) for key in keys}
    accounting = {
        **totals,
        "offline_source_labels_not_recharged": True,
        "sample_labels_execution_steps_planning_and_all_maintenance_axes_separate": True,
        "scalar_cost_aggregation_performed": False,
    }
    ood = v106.v105._ood(document["incompatible_schema_no_transfer_control"])  # noqa: SLF001
    passed = (
        all(row["gate_passed"] for row in replay)
        and totals["identity_short_dependency_maintenance_events"]
        < totals["full_diff_dependency_maintenance_events"]
        and totals["identity_short_dependency_maintenance_events"]
        < totals["per_hit_dependency_validation_checks"]
        and totals["identity_short_circuit_count"] > 0
        and totals["identity_short_quotient_lifetime_target_labels"]
        < totals["cold_direct_lifetime_target_labels"]
        and ood["strict_ood_no_transfer"] is True
    )
    gate = {
        "required_target_occurrence_count": 4,
        "passed_target_occurrence_count": sum(row["gate_passed"] for row in replay),
        "every_occurrence_exactly_matches_all_baselines": all(
            row["identity_short_quotient_lifetime_target_labels"]
            == row["full_diff_quotient_lifetime_target_labels"]
            == row["per_hit_quotient_lifetime_target_labels"]
            == row["no_cache_quotient_lifetime_target_labels"]
            for row in replay
        ),
        "every_occurrence_maintenance_below_per_hit_validation": all(
            row["identity_short_dependency_maintenance_events"]
            < row["per_hit_dependency_validation_checks"]
            for row in replay
        ),
        "aggregate_maintenance_strictly_below_full_diff": totals[
            "identity_short_dependency_maintenance_events"
        ]
        < totals["full_diff_dependency_maintenance_events"],
        "identity_short_circuit_observed": totals["identity_short_circuit_count"]
        > 0,
        "aggregate_quotient_labels_strictly_below_cold_direct": totals[
            "identity_short_quotient_lifetime_target_labels"
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
        or document[
            "registered_identity_short_circuited_epoch_invalidation_verified"
        ]
        != passed
        or document["cached_heuristic_used_as_safety_authority"] is not False
        or document["complete_ground_world_model_synthesized"] is not False
        or document["official_scalar_cost"] is not None
        or document["WORKLOAD_ECONOMICS_GATE"] != "NOT_RUN"
    ):
        _fail("V111 campaign Gate changed")
    failed = [
        (row["target_family"], row["seed"], row["maintenance_events_avoided_against_full_diff"])
        for row in replay
        if not row["gate_passed"]
    ]
    if failed != [
        ("BALANCED_BATCH_REFINEMENT", 1_023_101, -2),
        ("BALANCED_BATCH_REFINEMENT", 1_023_102, -2),
    ]:
        _fail("V111 failed occurrence identities changed")
    return {
        "schema": "acfqp.identity_short_circuited_epoch_verification.v111",
        "campaign_id": CAMPAIGN_ID,
        "preregistration_id": PREREGISTRATION_ID,
        "verification_status": "REGISTERED_V111_ASYMMETRIC_BASELINE_ACCOUNTING_GATE_FAILED",
        "producer_free_plan_and_per_action_receipt_reconstruction": True,
        "producer_free_full_diff_epoch_reconstruction": True,
        "producer_free_identity_short_circuit_reconstruction": True,
        "producer_free_cache_hit_miss_and_invalidation_reconstruction": True,
        "producer_summary_counts_not_used": True,
        "verified_occurrences": replay,
        "verified_accounting": accounting,
        "registered_gate_independently_verified": passed,
        "registered_failure_reason": "TWO_CHANGED_GRAPH_OCCURRENCES_PAID_TWO_IDENTITY_CHECKS_ABSENT_FROM_THE_OLD_FULL_DIFF_BASELINE_ACCOUNTING",
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


def freeze_identity_short_circuited_epoch_verification_v111(raw: bytes) -> bytes:
    payload = verify_identity_short_circuited_epoch_campaign_bytes_v111(raw)
    document = {
        **payload,
        "verification_id": domains.extension_content_id_v111(
            domains.CONSTRUCTION_K7_IDENTITY_SHORT_CIRCUITED_EPOCH_VERIFICATION_V111_DOMAIN,
            payload,
        ),
    }
    result = canonical_json_bytes(document)
    if VERIFICATION_ID != "0" * 64 and (
        document["verification_id"] != VERIFICATION_ID
        or len(result) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(result).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("V111 verification changed")
    return result


__all__ = (
    "VERIFICATION_ID",
    "freeze_identity_short_circuited_epoch_verification_v111",
    "verify_identity_short_circuited_epoch_campaign_bytes_v111",
)
