"""Producer-free replay of the failed V108 identity-bound memoization campaign.

The verifier does not trust V108 producer summaries.  It reconstructs every
successful quotient plan from the frozen catalogue and observation rows, then
replays the cache key in episode order.  V108 happened to contain no planner
abstentions, so the persisted successful-plan wrappers are the complete orderer
call inventory and make the successful-plan branch-evaluation metric exact.
"""

from __future__ import annotations

import copy
import hashlib
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v108 as domains
from acfqp import construction_k7_catalogue_closed_legality_quotient_independent_verifier_v107 as v107
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "fa9ce366738517878f37f171b553bde78a3522535063c82f9d17fa572bb95371"
CAMPAIGN_BYTE_COUNT = 6_947_135
CAMPAIGN_SHA256 = "f4cb08b6cfa7c5857dc6466e4ed1a0524cdc4e35322391025a2f203d6df127f5"
PREREGISTRATION_ID = "5a423ffdf36b592f12abfc5767e19ecc2af9e3db8e7aeb6e0179b8a634c09ad1"
V107_CAMPAIGN_ID = "5876fc38db769e0ffd518d1580577b7779e7276372b59ba2173b05b4d94e1293"
V107_VERIFICATION_ID = "18fb36d9897dfc750d399b310b55ca423f30dcf5f34f32368fd16c3dc47c25ea"
TARGETS = (
    ("BALANCED_BATCH_REFINEMENT", 1_020_101),
    ("BALANCED_BATCH_REFINEMENT", 1_020_102),
    ("MAINTENANCE_CASCADE", 1_020_103),
    ("MAINTENANCE_CASCADE", 1_020_104),
)
EPISODES = (171, 172, 173)
VERIFICATION_ID = "e7aba583086784cdf3b94f303b362c2094707a35cfb23670f78374d63784b4e2"
EXPECTED_CANONICAL_BYTE_COUNT = 3_982
EXPECTED_CANONICAL_SHA256 = "3ce0de37fe3e9bfe4029f599d7bcf02298f439a0e2b31738f4b245fe3039889d"

_MEMO_EPISODE_EXTRAS = {
    "memoized_orderer_call_count",
    "memoized_plan_cache_hit_count",
    "memoized_plan_cache_miss_count",
    "actual_new_abstract_planning_compute_events",
    "nominal_embedded_plan_compute_events",
    "planning_compute_events_avoided_by_identity_bound_cache",
    "memoized_plan_cache_entry_count_after_episode",
}


class ConstructionK7MemoizedCatalogueQuotientIndependentVerifierV108Error(
    ValueError
):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7MemoizedCatalogueQuotientIndependentVerifierV108Error(
        message
    )


def _content(document: Any, key: str, domain: str) -> None:
    if type(document) is not dict:
        _fail(f"V108 {key} document type changed")
    payload = {name: value for name, value in document.items() if name != key}
    if document.get(key) != domains.extension_content_id_v108(domain, payload):
        _fail(f"V108 {key} changed")


def _memo_key(
    candidate: Mapping[str, Any],
    model: Mapping[str, Any],
    wrapper: Mapping[str, Any],
) -> tuple[Any, ...]:
    raw = wrapper["raw_state"]
    plan = wrapper["abstract_plan"]
    canonical = [raw[index] for index in candidate["layout"]["state_canonical_to_raw"]]
    projected = tuple(
        canonical[row["target_column"]]
        for row in candidate["compiled_factor_assignments"]
    )
    return (
        model["quotient_graph_id"],
        projected,
        tuple(plan["exact_legal_action_keys_at_initial_state"]),
        plan["legality_support_source"],
        plan["legality_failure_index"],
    )


def _verify_full_plans(
    episode: Mapping[str, Any],
    model: Mapping[str, Any],
    candidate: Mapping[str, Any],
    rows: list[dict[str, Any]],
    catalogue: Mapping[int, tuple[int, ...]],
) -> None:
    for wrapper in episode["abstract_plan_receipts"]:
        raw = wrapper["raw_state"]
        plan = wrapper["abstract_plan"]
        exact_legal = tuple(plan["exact_legal_action_keys_at_initial_state"])
        expected = v107.v106._expected_plan(  # noqa: SLF001
            model,
            candidate,
            rows,
            catalogue,
            raw,
            exact_legal,
            plan["planning_source"],
            plan["legality_support_source"],
            plan["legality_failure_index"],
        )
        shield = v107.v106.v103._shield(  # noqa: SLF001
            plan["agreement_shield_receipt"]
        )
        expected["agreement_shield_receipt"] = shield
        expected = {
            **expected,
            "legality_conditioned_quotient_plan_id": v107.v106._hash(  # noqa: SLF001
                v107.v106._PLAN_DOMAIN, expected  # noqa: SLF001
            ),
        }
        if plan != expected:
            _fail("V108 complete catalogue did not reconstruct a quotient plan")


def _normalized_memo_episode(episode: Mapping[str, Any]) -> dict[str, Any]:
    v107.v106.v103._content_id(  # noqa: SLF001
        episode,
        "episode_id",
        v107.v106._EPISODE_DOMAIN,  # noqa: SLF001
        v107.v106._EPISODE_EXTRAS | _MEMO_EPISODE_EXTRAS,  # noqa: SLF001
    )
    normalized = copy.deepcopy(episode)
    for key in _MEMO_EPISODE_EXTRAS:
        normalized.pop(key)
    normalized["arm"] = "LEGALITY_CONDITIONED_OBSERVATION_QUOTIENT_ORDERING"
    payload = {
        key: value
        for key, value in normalized.items()
        if key not in {"episode_id", *v107.v106._EPISODE_EXTRAS}  # noqa: SLF001
    }
    normalized["episode_id"] = v107.v106._hash(  # noqa: SLF001
        v107.v106._EPISODE_DOMAIN, payload  # noqa: SLF001
    )
    return normalized


def _sequence(
    document: Any,
    acquisition: Mapping[str, Any],
    catalogue: Mapping[int, tuple[int, ...]],
    family: str,
    seed: int,
    *,
    memoized: bool,
) -> dict[str, Any]:
    if type(document) is not dict:
        _fail("V108 quotient sequence type changed")
    if memoized:
        _content(
            document,
            "sequence_id",
            domains.CONSTRUCTION_K7_MEMOIZED_CATALOGUE_QUOTIENT_SEQUENCE_V108_DOMAIN,
        )
    else:
        v107.v106._content(  # noqa: SLF001
            document, "sequence_id", v107.v106._SEQUENCE_DOMAIN  # noqa: SLF001
        )
    episodes = document.get("episodes")
    final_rows_document = document.get("persistent_exact_overlay_rows")
    models = document.get("quotient_models_before_each_episode")
    expected_schema = (
        "acfqp.generic_persistent_memoized_catalogue_quotient_sequence.v108"
        if memoized
        else "acfqp.generic_persistent_legality_conditioned_quotient_sequence.v106"
    )
    if (
        document.get("schema") != expected_schema
        or document.get("family") != family
        or document.get("seed") != seed
        or document.get("episode_indices") != list(EPISODES)
        or document.get("partial_candidate_id")
        != acquisition["candidate"]["candidate_id"]
        or type(episodes) is not list
        or len(episodes) != len(EPISODES)
        or type(models) is not list
        or len(models) != len(EPISODES)
        or type(final_rows_document) is not list
        or document.get("certified_legality_reused_as_abstract_boundary_not_recharged")
        is not True
        or document.get("actual_engine_action_order_receipts_not_posthoc_policy_matches")
        is not True
        or document.get("query_local_exact_overlay_exclusively_discharges_safety")
        is not True
        or document.get("global_lumpability_claimed") is not False
        or document.get("complete_ground_world_model_synthesized") is not False
        or document.get("official_execution_allowed") is not False
    ):
        _fail("V108 quotient sequence boundary changed")
    final_rows = [v107.v106.v105._row(row) for row in final_rows_document]  # noqa: SLF001
    all_incremental = [
        v107.v106.v105._row(row)  # noqa: SLF001
        for episode in episodes
        for row in episode.get("raw_incremental_transition_rows", [])
    ]
    incremental_keys = {
        v107.v106.v105._row_key(row) for row in all_incremental  # noqa: SLF001
    }
    initial = [
        row
        for row in final_rows
        if v107.v106.v105._row_key(row) not in incremental_keys  # noqa: SLF001
    ]
    if len(initial) + len(incremental_keys) != len(final_rows):
        _fail("V108 initial/overlay partition changed")
    candidate = v107.v106.v105._verify_acquisition(  # noqa: SLF001
        acquisition, initial, family, seed
    )
    rows = v107.v106.v105._deduplicate(initial)  # noqa: SLF001
    paid = 0
    all_actual: list[dict[str, Any]] = []
    all_failures: list[dict[str, Any]] = []
    all_distinctions: list[dict[str, Any]] = []
    seen: dict[tuple[Any, ...], dict[str, Any]] = {}
    calls = hits = misses = actual_compute = nominal_compute = 0
    plan_count = fallback_count = actual_fallback_count = 0
    for expected_index, episode, model in zip(
        EPISODES, episodes, models, strict=True
    ):
        expected_model = v107.v106.v105._expected_model(candidate, rows)  # noqa: SLF001
        if (
            model != expected_model
            or episode.get("quotient_graph_before_episode") != expected_model
        ):
            _fail("V108 quotient graph differs from observation replay")
        before_rows = rows
        checked_episode = (
            _normalized_memo_episode(episode) if memoized else episode
        )
        (
            actual,
            rows,
            incremental,
            episode_fallback,
            episode_actual_fallback,
        ) = v107.v106._episode(  # noqa: SLF001
            checked_episode,
            expected_model,
            candidate,
            before_rows,
            catalogue,
            family,
            seed,
            expected_index,
            paid,
        )
        _verify_full_plans(
            episode, expected_model, candidate, before_rows, catalogue
        )
        wrappers = episode["abstract_plan_receipts"]
        plan_count += len(wrappers)
        fallback_count += episode_fallback
        actual_fallback_count += episode_actual_fallback
        if memoized:
            if (
                episode["arm"]
                != "MEMOIZED_CATALOGUE_CLOSED_LEGALITY_QUOTIENT_ORDERING"
                or episode["abstract_plan_attempt_count"] != len(wrappers)
                or episode["abstract_plan_success_count"] != len(wrappers)
                or episode["abstract_plan_abstention_count"] != 0
            ):
                _fail("V108 memo call inventory is not fully receipted")
            episode_hits = episode_misses = episode_actual = 0
            for wrapper in wrappers:
                key = _memo_key(candidate, expected_model, wrapper)
                plan = wrapper["abstract_plan"]
                if key in seen:
                    episode_hits += 1
                    if seen[key] != plan:
                        _fail("V108 cache key reused a different plan")
                else:
                    episode_misses += 1
                    episode_actual += plan["abstract_support_branch_evaluations"]
                    seen[key] = plan
            episode_nominal = sum(
                wrapper["abstract_plan"]["abstract_support_branch_evaluations"]
                for wrapper in wrappers
            )
            episode_calls = len(wrappers)
            if (
                episode.get("memoized_orderer_call_count") != episode_calls
                or episode.get("memoized_plan_cache_hit_count") != episode_hits
                or episode.get("memoized_plan_cache_miss_count") != episode_misses
                or episode.get("actual_new_abstract_planning_compute_events")
                != episode_actual
                or episode.get("nominal_embedded_plan_compute_events")
                != episode_nominal
                or episode.get(
                    "planning_compute_events_avoided_by_identity_bound_cache"
                )
                != episode_nominal - episode_actual
                or episode.get("memoized_plan_cache_entry_count_after_episode")
                != len(seen)
            ):
                _fail("V108 episode cache accounting differs from receipt replay")
            calls += episode_calls
            hits += episode_hits
            misses += episode_misses
            actual_compute += episode_actual
            nominal_compute += episode_nominal
        else:
            nominal_compute += episode["abstract_planning_compute_events"]
        paid += incremental
        all_actual.extend(actual)
        all_failures.extend(episode["failed_certificates"])
        all_distinctions.extend(episode["local_distinctions"])
    if rows != final_rows:
        _fail("V108 final persistent overlay changed")
    steps = len(all_actual)
    admitted = sum(
        row["quotient_proposal_admitted_to_real_action_order"]
        for row in all_actual
    )
    matches = sum(
        row["chosen_action_matches_admitted_quotient_proposal"]
        for row in all_actual
    )
    local_legality = sum(
        row["legality_support_source"] in v107.v106._LOCAL_LEGALITY_SOURCES  # noqa: SLF001
        for row in all_actual
    )
    if (
        document.get("all_actual_legality_conditioned_execution_receipts")
        != all_actual
        or document.get("actual_legality_conditioned_execution_receipt_count")
        != steps
        or document.get("execution_step_count") != steps
        or document.get("quotient_proposal_admitted_execution_count") != admitted
        or document.get("chosen_action_matches_admitted_quotient_proposal_count")
        != matches
        or document.get("certificate_local_legality_plan_count") != local_legality
        or document.get("quotient_proposal_admitted_strict_majority")
        != (2 * admitted > steps)
        or document.get("chosen_action_matches_admitted_quotient_proposal_strict_majority")
        != (2 * matches > steps)
        or document.get("initial_acquisition_ground_support_labels_paid_once")
        != acquisition["ground_support_labels"]
        or document.get("certificate_ground_support_labels_paid_once") != paid
        or document.get("lifetime_target_ground_support_labels")
        != acquisition["ground_support_labels"] + paid
        or document.get("persistent_exact_overlay_sha256")
        != hashlib.sha256(canonical_json_bytes(final_rows)).hexdigest()
        or document.get("persistent_exact_support_group_count")
        != v107.v106.v105._group_count(final_rows)  # noqa: SLF001
        or document.get("all_failed_certificates") != all_failures
        or document.get("all_local_distinctions") != all_distinctions
        or document.get("every_new_ground_query_followed_a_failed_certificate")
        is not True
        or document.get("quotient_graph_updates_only_from_certificate_local_overlay")
        is not True
    ):
        _fail("V108 sequence aggregate reconstruction changed")
    if memoized and (
        document.get("memoized_orderer_call_count") != calls
        or document.get("memoized_plan_cache_hit_count") != hits
        or document.get("memoized_plan_cache_miss_count") != misses
        or document.get("memoized_plan_cache_entry_count") != len(seen)
        or document.get("nominal_embedded_plan_compute_events") != nominal_compute
        or document.get("actual_new_abstract_planning_compute_events")
        != actual_compute
        or document.get("planning_compute_events_avoided_by_identity_bound_cache")
        != nominal_compute - actual_compute
        or document.get(
            "identity_bound_cache_key_includes_model_projection_legality_and_provenance"
        )
        is not True
        or document.get("cache_hit_reuses_identical_content_addressed_plan")
        is not True
    ):
        _fail("V108 sequence cache aggregate reconstruction changed")
    return {
        "actions": [episode["action_keys"] for episode in episodes],
        "actual_receipts": all_actual,
        "execution_steps": steps,
        "admitted": admitted,
        "matches": matches,
        "local_legality": local_legality,
        "initial_labels": acquisition["ground_support_labels"],
        "certificate_labels": paid,
        "lifetime_labels": acquisition["ground_support_labels"] + paid,
        "planning_compute": actual_compute if memoized else nominal_compute,
        "nominal_compute": nominal_compute,
        "cache_hits": hits,
        "cache_misses": misses,
        "plan_count": plan_count,
        "fallback_plan_count": fallback_count,
        "actual_fallback_count": actual_fallback_count,
        "later_zero_label_reuse": any(
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
        _fail("V108 direct sequence changed")
    episodes = document.get("episodes")
    if type(episodes) is not list or len(episodes) != len(EPISODES):
        _fail("V108 direct episode inventory changed")
    labels = 0
    for expected_index, episode in zip(EPISODES, episodes, strict=True):
        v107.v106.v103._content_id(  # noqa: SLF001
            episode,
            "episode_id",
            v107.v106.v103._DIRECT_EPISODE_DOMAIN,  # noqa: SLF001
        )
        failures = episode.get("failed_certificates")
        distinctions = episode.get("local_distinctions")
        if (
            episode.get("schema")
            != "acfqp.generic_preloaded_certificate_receding_episode.v74"
            or episode.get("family") != family
            or episode.get("seed") != seed
            or episode.get("episode_index") != expected_index
            or episode.get("arm") != "STRICT_COLD_DIRECT_GROUND"
            or episode.get("target_candidate_id") != candidate_id
            or episode.get("success") is not True
            or episode.get("preloaded_acquisition_ground_support_labels") != 0
            or episode.get("abstract_model_used_only_for_action_ordering") is not False
            or episode.get("abstract_plan_attempt_count") != 0
            or episode.get("abstract_plan_receipts") != []
            or episode.get("abstract_planning_compute_events") != 0
            or episode.get("query_local_exact_overlay_exclusively_used_for_safety")
            is not True
            or type(failures) is not list
            or type(distinctions) is not list
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
            _fail("V108 direct episode semantics changed")
        incremental = sum(row["ground_support_labels"] for row in distinctions)
        if (
            episode.get("incremental_certificate_local_ground_support_labels")
            != incremental
            or episode.get("total_target_ground_support_labels") != incremental
        ):
            _fail("V108 direct label accounting changed")
        labels += incremental
    if document.get("lifetime_target_ground_support_labels") != labels:
        _fail("V108 direct lifetime labels changed")
    return labels


def _occurrence(document: Any, family: str, seed: int) -> dict[str, Any]:
    if type(document) is not dict:
        _fail("V108 occurrence type changed")
    _content(
        document,
        "occurrence_id",
        domains.CONSTRUCTION_K7_MEMOIZED_CATALOGUE_QUOTIENT_OCCURRENCE_V108_DOMAIN,
    )
    if (
        document.get("schema") != "acfqp.memoized_catalogue_quotient_occurrence.v108"
        or document.get("target_family") != family
        or document.get("seed") != seed
        or document.get("episode_indices") != list(EPISODES)
    ):
        _fail("V108 occurrence identity changed")
    catalogue = v107._catalogue(  # noqa: SLF001
        document.get("complete_anonymous_action_catalogue_receipt"), family, seed
    )
    acquisition = document.get("partial_acquisition")
    memo_document = document.get("persistent_memoized_catalogue_quotient_sequence")
    no_cache_document = document.get("matched_no_cache_legality_quotient_sequence")
    memo = _sequence(
        memo_document, acquisition, catalogue, family, seed, memoized=True
    )
    no_cache = _sequence(
        no_cache_document,
        acquisition,
        catalogue,
        family,
        seed,
        memoized=False,
    )
    direct_labels = _direct(
        document.get("strict_cold_direct_sequence"),
        family,
        seed,
        acquisition["candidate"]["candidate_id"],
    )
    utilization = v107.v106._utilization(memo_document)  # noqa: SLF001
    same_actions = memo["actions"] == no_cache["actions"]
    same_receipts = memo["actual_receipts"] == no_cache["actual_receipts"]
    same_labels = memo["lifetime_labels"] == no_cache["lifetime_labels"]
    gate = {
        "memoized_and_no_cache_action_sequences_exactly_match": same_actions,
        "memoized_and_no_cache_per_action_receipts_exactly_match": same_receipts,
        "memoized_and_no_cache_target_labels_exactly_match": same_labels,
        "memoized_actual_planning_compute_strictly_below_no_cache": memo[
            "planning_compute"
        ]
        < no_cache["planning_compute"],
        "memoized_cache_hit_observed": memo["cache_hits"] > 0,
        "quotient_model_orders_at_least_three_quarters": utilization[
            "quotient_actually_orders_at_least_three_quarters_of_execution"
        ],
        "chosen_action_matches_quotient_strict_majority": utilization[
            "chosen_action_matches_quotient_strict_majority"
        ],
        "certificate_failure_only_query_discipline_clean": memo_document[
            "every_new_ground_query_followed_a_failed_certificate"
        ],
        "later_zero_label_quotient_reuse_observed": memo[
            "later_zero_label_reuse"
        ],
        "quotient_lifetime_labels_strictly_below_cold_direct": memo[
            "lifetime_labels"
        ]
        < direct_labels,
    }
    gate["passed"] = all(gate.values())
    accounting = {
        "initial_acquisition_labels": memo["initial_labels"],
        "certificate_local_labels": memo["certificate_labels"],
        "memoized_quotient_lifetime_target_labels": memo["lifetime_labels"],
        "matched_no_cache_quotient_lifetime_target_labels": no_cache[
            "lifetime_labels"
        ],
        "cold_direct_lifetime_target_labels": direct_labels,
        "target_label_reduction_against_cold_direct": direct_labels
        - memo["lifetime_labels"],
        "execution_steps": memo["execution_steps"],
        "memoized_actual_new_planning_compute_events": memo["planning_compute"],
        "matched_no_cache_planning_compute_events": no_cache["planning_compute"],
        "planning_compute_events_avoided": no_cache["planning_compute"]
        - memo["planning_compute"],
        "sample_labels_execution_steps_and_planning_compute_separate": True,
        "scalar_cost_aggregation_performed": False,
    }
    if (
        document.get("legality_conditioned_quotient_utilization") != utilization
        or document.get("accounting") != accounting
        or document.get("registered_gate") != gate
        or document.get("identity_bound_memoization_preserves_actions_and_labels")
        != gate["passed"]
        or document.get("local_ground_distinctions_only_after_certificate_failure_verified")
        != gate["passed"]
        or document.get("global_lumpability_claimed") is not False
        or document.get("complete_ground_world_model_synthesized") is not False
        or document.get("official_execution_allowed") is not False
        or document.get("official_scalar_cost") is not None
        or document.get("official_N_break_even") is not None
        or document.get("WORKLOAD_ECONOMICS_GATE") != "NOT_RUN"
        or document.get("COUNTER_COMPLETENESS_GATE") != "NOT_RUN"
    ):
        _fail("V108 occurrence Gate or claim boundary changed")
    return {
        "target_family": family,
        "seed": seed,
        "gate_passed": gate["passed"],
        "execution_steps": memo["execution_steps"],
        "initial_acquisition_labels": memo["initial_labels"],
        "certificate_local_labels": memo["certificate_labels"],
        "memoized_quotient_lifetime_target_labels": memo["lifetime_labels"],
        "matched_no_cache_quotient_lifetime_target_labels": no_cache[
            "lifetime_labels"
        ],
        "cold_direct_lifetime_target_labels": direct_labels,
        "target_label_reduction_against_cold_direct": direct_labels
        - memo["lifetime_labels"],
        "memoized_actual_new_planning_compute_events": memo["planning_compute"],
        "matched_no_cache_planning_compute_events": no_cache["planning_compute"],
        "planning_compute_events_avoided": no_cache["planning_compute"]
        - memo["planning_compute"],
        "cache_hits": memo["cache_hits"],
        "cache_misses": memo["cache_misses"],
        "all_orderer_calls_successfully_receipted": True,
    }


def verify_memoized_catalogue_quotient_campaign_bytes_v108(
    raw: bytes,
) -> dict[str, Any]:
    if (
        type(raw) is not bytes
        or len(raw) != CAMPAIGN_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != CAMPAIGN_SHA256
    ):
        _fail("V108 campaign bytes changed")
    document = loads_canonical_json(raw)
    if canonical_json_bytes(document) != raw:
        _fail("V108 campaign is noncanonical")
    _content(
        document,
        "campaign_id",
        domains.CONSTRUCTION_K7_MEMOIZED_CATALOGUE_QUOTIENT_CAMPAIGN_V108_DOMAIN,
    )
    rows = document.get("target_occurrences")
    if (
        document.get("campaign_id") != CAMPAIGN_ID
        or document.get("schema") != "acfqp.memoized_catalogue_quotient_campaign.v108"
        or document.get("preregistration_id") != PREREGISTRATION_ID
        or document.get("v107_campaign_id") != V107_CAMPAIGN_ID
        or document.get("v107_verification_id") != V107_VERIFICATION_ID
        or type(rows) is not list
        or len(rows) != len(TARGETS)
    ):
        _fail("V108 campaign inventory changed")
    replay = [
        _occurrence(row, family, seed)
        for row, (family, seed) in zip(rows, TARGETS, strict=True)
    ]
    total_keys = (
        "initial_acquisition_labels",
        "certificate_local_labels",
        "memoized_quotient_lifetime_target_labels",
        "matched_no_cache_quotient_lifetime_target_labels",
        "cold_direct_lifetime_target_labels",
        "target_label_reduction_against_cold_direct",
        "execution_steps",
        "memoized_actual_new_planning_compute_events",
        "matched_no_cache_planning_compute_events",
        "planning_compute_events_avoided",
    )
    totals = {key: sum(row[key] for row in replay) for key in total_keys}
    expected_accounting = {
        **totals,
        "offline_source_labels_not_recharged": True,
        "sample_labels_execution_steps_and_planning_compute_separate": True,
        "scalar_cost_aggregation_performed": False,
    }
    ood = v107.v106.v105._ood(  # noqa: SLF001
        document.get("incompatible_schema_no_transfer_control")
    )
    passed = (
        all(row["gate_passed"] for row in replay)
        and totals["memoized_actual_new_planning_compute_events"]
        < totals["matched_no_cache_planning_compute_events"]
        and totals["memoized_quotient_lifetime_target_labels"]
        < totals["cold_direct_lifetime_target_labels"]
        and ood["strict_ood_no_transfer"] is True
    )
    gate = {
        "required_target_occurrence_count": 4,
        "passed_target_occurrence_count": sum(
            row["gate_passed"] for row in replay
        ),
        "every_occurrence_action_and_receipt_equivalent_to_no_cache": all(
            row["memoized_quotient_lifetime_target_labels"]
            == row["matched_no_cache_quotient_lifetime_target_labels"]
            for row in replay
        ),
        "every_occurrence_planning_compute_strictly_reduced": all(
            row["memoized_actual_new_planning_compute_events"]
            < row["matched_no_cache_planning_compute_events"]
            for row in replay
        ),
        "aggregate_sample_labels_unchanged_by_memoization": totals[
            "memoized_quotient_lifetime_target_labels"
        ]
        == totals["matched_no_cache_quotient_lifetime_target_labels"],
        "aggregate_quotient_labels_strictly_below_cold_direct": totals[
            "memoized_quotient_lifetime_target_labels"
        ]
        < totals["cold_direct_lifetime_target_labels"],
        "strict_incompatible_schema_no_transfer_verified": ood[
            "strict_ood_no_transfer"
        ],
        "passed": passed,
    }
    if (
        document.get("accounting") != expected_accounting
        or document.get("registered_gate") != gate
        or document.get("registered_identity_bound_quotient_memoization_verified")
        != passed
        or document.get("ground_distinctions_acquired_only_after_certificate_failure_verified")
        != passed
        or document.get("global_lumpability_claimed") is not False
        or document.get("complete_ground_world_model_synthesized") is not False
        or document.get("arbitrary_domain_transfer_claimed") is not False
        or document.get("official_execution_allowed") is not False
        or document.get("official_scalar_cost") is not None
        or document.get("official_N_break_even") is not None
        or document.get("WORKLOAD_ECONOMICS_GATE") != "NOT_RUN"
        or document.get("COUNTER_COMPLETENESS_GATE") != "NOT_RUN"
    ):
        _fail("V108 campaign Gate or claim boundary changed")
    return {
        "schema": "acfqp.memoized_catalogue_quotient_verification.v108",
        "campaign_id": CAMPAIGN_ID,
        "preregistration_id": PREREGISTRATION_ID,
        "verification_status": "REGISTERED_V108_MEMOIZATION_GATE_FAILED",
        "producer_free_complete_catalogue_and_plan_replay": True,
        "producer_free_identity_bound_cache_key_replay": True,
        "all_orderer_calls_successfully_receipted": all(
            row["all_orderer_calls_successfully_receipted"] for row in replay
        ),
        "producer_summary_cache_counts_not_used": True,
        "verified_occurrences": replay,
        "verified_accounting": expected_accounting,
        "verified_cache_hit_count": sum(row["cache_hits"] for row in replay),
        "verified_cache_miss_count": sum(row["cache_misses"] for row in replay),
        "registered_gate_independently_verified": passed,
        "registered_failure_reason": "TWO_BALANCED_OCCURRENCES_HAD_NO_CROSS_EPISODE_IDENTITY_BOUND_CACHE_HIT",
        "fresh_successor_required": True,
        "global_lumpability_claimed": False,
        "complete_ground_world_model_synthesized": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }


def freeze_memoized_catalogue_quotient_verification_v108(raw: bytes) -> bytes:
    payload = verify_memoized_catalogue_quotient_campaign_bytes_v108(raw)
    document = {
        **payload,
        "verification_id": domains.extension_content_id_v108(
            domains.CONSTRUCTION_K7_MEMOIZED_CATALOGUE_QUOTIENT_VERIFICATION_V108_DOMAIN,
            payload,
        ),
    }
    result = canonical_json_bytes(document)
    if VERIFICATION_ID != "0" * 64 and (
        document["verification_id"] != VERIFICATION_ID
        or len(result) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(result).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("V108 verification changed")
    return result


__all__ = (
    "VERIFICATION_ID",
    "freeze_memoized_catalogue_quotient_verification_v108",
    "verify_memoized_catalogue_quotient_campaign_bytes_v108",
)
