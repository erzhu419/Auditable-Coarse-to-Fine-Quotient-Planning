"""Producer-free V107 replay using the receipted complete action catalogue."""

from __future__ import annotations

import hashlib
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v107 as domains
from acfqp import construction_k7_legality_conditioned_quotient_independent_verifier_v106 as v106
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "5876fc38db769e0ffd518d1580577b7779e7276372b59ba2173b05b4d94e1293"
CAMPAIGN_BYTE_COUNT = 3_822_627
CAMPAIGN_SHA256 = "10c35c92792032ae91c2e421d758e4ff5e4fb0244910d37acd25018dd96ef244"
PREREGISTRATION_ID = "38b7e1adc4392decd5d07e47f4384173a3709c9c14e0f0d8fdec903820126fb8"
V106_CAMPAIGN_ID = "ba998dae81c2e83c2e8dc388aebe878a5336a3dd6826d5f7d65e455545b7e5b7"
V106_VERIFICATION_ID = "cc6f26563e94e4a6b76311ba0cc51a34ef92cd27f154fdbd2dcd7eea9a98f94e"
TARGETS = (
    ("BALANCED_BATCH_REFINEMENT", 1_019_101),
    ("BALANCED_BATCH_REFINEMENT", 1_019_102),
    ("MAINTENANCE_CASCADE", 1_019_103),
    ("MAINTENANCE_CASCADE", 1_019_104),
)
EPISODES = (161, 162, 163)
VERIFICATION_ID = "18fb36d9897dfc750d399b310b55ca423f30dcf5f34f32368fd16c3dc47c25ea"
EXPECTED_CANONICAL_BYTE_COUNT = 3_977
EXPECTED_CANONICAL_SHA256 = "88742bb8e5473f06487ba677afdee62561e8cc6315f8a1d84994b6ca67f6bfe6"


class ConstructionK7CatalogueClosedLegalityQuotientIndependentVerifierV107Error(
    ValueError
):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7CatalogueClosedLegalityQuotientIndependentVerifierV107Error(
        message
    )


def _catalogue(
    document: Any, family: str, seed: int
) -> dict[int, tuple[int, ...]]:
    if type(document) is not dict:
        _fail("V107 catalogue receipt type changed")
    rows = document.get("action_descriptor_rows")
    if type(rows) is not list or not rows:
        _fail("V107 catalogue descriptor inventory changed")
    keys = []
    widths = set()
    catalogue: dict[int, tuple[int, ...]] = {}
    for row in rows:
        if type(row) is not dict or set(row) != {
            "action_key",
            "anonymous_fields",
        }:
            _fail("V107 catalogue row schema changed")
        key = row["action_key"]
        fields = row["anonymous_fields"]
        if (
            type(key) is not int
            or key in catalogue
            or type(fields) is not list
            or not fields
            or any(type(value) is not int for value in fields)
        ):
            _fail("V107 catalogue row value changed")
        keys.append(key)
        widths.add(len(fields))
        catalogue[key] = tuple(fields)
    payload = {
        "schema": "acfqp.complete_anonymous_action_catalogue_receipt.v107",
        "family": family,
        "seed": seed,
        "action_descriptor_rows": rows,
        "action_key_count": len(rows),
        "action_field_width": next(iter(widths)) if len(widths) == 1 else None,
        "catalogue_order_is_exact_planner_iteration_order": True,
        "catalogue_complete_at_target_adapter_boundary": True,
        "catalogue_enumerated_before_target_episode_outcomes": True,
        "catalogue_contains_transition_outcomes": False,
        "semantic_action_names_present": False,
        "catalogue_is_planning_input_not_safety_authority": True,
        "complete_ground_world_model_claimed": False,
    }
    expected = {
        **payload,
        "catalogue_receipt_id": domains.extension_content_id_v107(
            domains.CONSTRUCTION_K7_COMPLETE_ANONYMOUS_ACTION_CATALOGUE_RECEIPT_V107_DOMAIN,
            payload,
        ),
    }
    if (
        document != expected
        or len(widths) != 1
        or keys != sorted(keys)
    ):
        _fail("V107 complete catalogue receipt semantics changed")
    return catalogue


def _full_plan_replay(
    sequence: Mapping[str, Any],
    acquisition: Mapping[str, Any],
    catalogue: Mapping[int, tuple[int, ...]],
    family: str,
    seed: int,
) -> dict[str, int]:
    episodes = sequence["episodes"]
    final_rows = [
        v106.v105._row(row) for row in sequence["persistent_exact_overlay_rows"]
    ]
    all_incremental = [
        v106.v105._row(row)
        for episode in episodes
        for row in episode["raw_incremental_transition_rows"]
    ]
    incremental_keys = {v106.v105._row_key(row) for row in all_incremental}
    initial = [
        row
        for row in final_rows
        if v106.v105._row_key(row) not in incremental_keys
    ]
    candidate = v106.v105._verify_acquisition(
        acquisition, initial, family, seed
    )
    rows = v106.v105._deduplicate(initial)
    plan_count = 0
    fallback_count = 0
    actual_fallback_count = 0
    for expected_index, episode in zip(EPISODES, episodes, strict=True):
        if episode["episode_index"] != expected_index:
            _fail("V107 episode identity changed during full plan replay")
        model = v106.v105._expected_model(candidate, rows)
        by_raw = {}
        for wrapper in episode["abstract_plan_receipts"]:
            raw = wrapper["raw_state"]
            plan = wrapper["abstract_plan"]
            exact_legal = tuple(plan["exact_legal_action_keys_at_initial_state"])
            expected = v106._expected_plan(
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
            shield = v106.v103._shield(plan["agreement_shield_receipt"])
            expected["agreement_shield_receipt"] = shield
            expected = {
                **expected,
                "legality_conditioned_quotient_plan_id": v106._hash(
                    v106._PLAN_DOMAIN, expected
                ),
            }
            if plan != expected:
                _fail("V107 complete catalogue did not reconstruct abstract plan")
            if any(key not in catalogue for key in plan["projected_action_path"]):
                _fail("V107 abstract plan escaped the complete catalogue")
            by_raw[tuple(raw)] = plan["planning_source"]
            plan_count += 1
            fallback_count += (
                plan["planning_source"] == "COMPILED_FACTOR_PROGRAM_FALLBACK"
            )
        for receipt in episode[
            "actual_legality_conditioned_execution_receipts"
        ]:
            wrapper = receipt["quotient_plan_receipt"]
            if wrapper is not None:
                source = by_raw.get(tuple(receipt["raw_state"]))
                if source != wrapper["abstract_plan"]["planning_source"]:
                    _fail("V107 actual receipt/plan source join changed")
                actual_fallback_count += (
                    source == "COMPILED_FACTOR_PROGRAM_FALLBACK"
                )
        rows = v106.v105._deduplicate(
            [
                *rows,
                *[
                    v106.v105._row(row)
                    for row in episode["raw_incremental_transition_rows"]
                ],
            ]
        )
    if rows != final_rows:
        _fail("V107 full catalogue replay ended on a different overlay")
    return {
        "abstract_plan_receipt_count": plan_count,
        "fallback_plan_receipt_count": fallback_count,
        "actual_execution_receipt_count_using_fallback": actual_fallback_count,
    }


def _sequence(
    document: Any,
    acquisition: Mapping[str, Any],
    family: str,
    seed: int,
) -> dict[str, Any]:
    if type(document) is not dict:
        _fail("V107 embedded quotient sequence type changed")
    v106._content(document, "sequence_id", v106._SEQUENCE_DOMAIN)
    episodes = document.get("episodes")
    final_rows = document.get("persistent_exact_overlay_rows")
    models = document.get("quotient_models_before_each_episode")
    if (
        document.get("schema")
        != "acfqp.generic_persistent_legality_conditioned_quotient_sequence.v106"
        or document.get("family") != family
        or document.get("seed") != seed
        or document.get("episode_indices") != list(EPISODES)
        or document.get("partial_candidate_id")
        != acquisition["candidate"]["candidate_id"]
        or type(episodes) is not list
        or len(episodes) != len(EPISODES)
        or type(models) is not list
        or len(models) != len(EPISODES)
        or type(final_rows) is not list
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
        _fail("V107 embedded quotient sequence boundary changed")
    final_rows = [v106.v105._row(row) for row in final_rows]
    all_incremental = [
        v106.v105._row(row)
        for episode in episodes
        for row in episode.get("raw_incremental_transition_rows", [])
    ]
    incremental_keys = {v106.v105._row_key(row) for row in all_incremental}
    initial = [
        row
        for row in final_rows
        if v106.v105._row_key(row) not in incremental_keys
    ]
    if len(initial) + len(incremental_keys) != len(final_rows):
        _fail("V107 initial/overlay row partition changed")
    candidate = v106.v105._verify_acquisition(
        acquisition, initial, family, seed
    )
    catalogue = v106.v105._catalogue(final_rows)
    rows = v106.v105._deduplicate(initial)
    all_actual = []
    all_failures = []
    all_distinctions = []
    paid = 0
    fallback_plans = 0
    actual_fallback_receipts = 0
    for expected_index, episode, model in zip(
        EPISODES, episodes, models, strict=True
    ):
        expected_model = v106.v105._expected_model(candidate, rows)
        if (
            model != expected_model
            or episode.get("quotient_graph_before_episode") != expected_model
        ):
            _fail("V107 quotient graph differs from observation replay")
        (
            actual,
            rows,
            incremental,
            episode_fallback_plans,
            episode_actual_fallback_receipts,
        ) = v106._episode(
            episode,
            expected_model,
            candidate,
            rows,
            catalogue,
            family,
            seed,
            expected_index,
            paid,
        )
        paid += incremental
        fallback_plans += episode_fallback_plans
        actual_fallback_receipts += episode_actual_fallback_receipts
        all_actual.extend(actual)
        all_failures.extend(episode["failed_certificates"])
        all_distinctions.extend(episode["local_distinctions"])
    if rows != final_rows:
        _fail("V107 final persistent overlay changed")
    steps = len(all_actual)
    admitted = sum(
        row["quotient_proposal_admitted_to_real_action_order"] for row in all_actual
    )
    matches = sum(
        row["chosen_action_matches_admitted_quotient_proposal"] for row in all_actual
    )
    local_legality = sum(
        row["legality_support_source"] in v106._LOCAL_LEGALITY_SOURCES
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
        != v106.v105._group_count(final_rows)
        or document.get("all_failed_certificates") != all_failures
        or document.get("all_local_distinctions") != all_distinctions
        or document.get("every_new_ground_query_followed_a_failed_certificate")
        is not True
        or document.get("quotient_graph_updates_only_from_certificate_local_overlay")
        is not True
    ):
        _fail("V107 sequence aggregate reconstruction changed")
    return {
        "execution_steps": steps,
        "admitted": admitted,
        "matches": matches,
        "local_legality": local_legality,
        "certificate_labels": paid,
        "initial_labels": acquisition["ground_support_labels"],
        "lifetime_labels": acquisition["ground_support_labels"] + paid,
        "planning_compute": sum(
            row["abstract_planning_compute_events"] for row in episodes
        ),
        "fallback_plan_receipt_count_without_complete_catalogue_closure": fallback_plans,
        "actual_execution_receipt_count_using_unreconstructable_fallback": actual_fallback_receipts,
        "later_zero_label_reuse": any(
            row["episode_index"] != EPISODES[0]
            and row["new_certificate_labels_charged_this_episode"] == 0
            and row["quotient_proposal_admitted_execution_count"] > 0
            for row in episodes
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
        _fail("V107 direct sequence changed")
    episodes = document.get("episodes")
    if type(episodes) is not list or len(episodes) != len(EPISODES):
        _fail("V107 direct episode inventory changed")
    labels = 0
    for expected_index, episode in zip(EPISODES, episodes, strict=True):
        v106.v103._content_id(
            episode, "episode_id", v106.v103._DIRECT_EPISODE_DOMAIN
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
            _fail("V107 direct episode semantics changed")
        incremental = sum(row["ground_support_labels"] for row in distinctions)
        if (
            episode.get("incremental_certificate_local_ground_support_labels")
            != incremental
            or episode.get("total_target_ground_support_labels") != incremental
        ):
            _fail("V107 direct label accounting changed")
        labels += incremental
    if document.get("lifetime_target_ground_support_labels") != labels:
        _fail("V107 direct lifetime labels changed")
    return labels


def _occurrence(document: Any, family: str, seed: int) -> dict[str, Any]:
    if type(document) is not dict:
        _fail("V107 occurrence type changed")
    payload = {key: value for key, value in document.items() if key != "occurrence_id"}
    if (
        document.get("occurrence_id")
        != domains.extension_content_id_v107(
            domains.CONSTRUCTION_K7_CATALOGUE_CLOSED_LEGALITY_QUOTIENT_OCCURRENCE_V107_DOMAIN,
            payload,
        )
        or document.get("schema")
        != "acfqp.catalogue_closed_legality_quotient_occurrence.v107"
        or document.get("target_family") != family
        or document.get("seed") != seed
        or document.get("episode_indices") != list(EPISODES)
    ):
        _fail("V107 occurrence identity changed")
    catalogue = _catalogue(
        document.get("complete_anonymous_action_catalogue_receipt"), family, seed
    )
    acquisition = document.get("partial_acquisition")
    sequence_document = document.get(
        "persistent_legality_conditioned_quotient_sequence"
    )
    sequence = _sequence(sequence_document, acquisition, family, seed)
    full = _full_plan_replay(
        sequence_document, acquisition, catalogue, family, seed
    )
    direct_labels = _direct(
        document.get("strict_cold_direct_sequence"),
        family,
        seed,
        acquisition["candidate"]["candidate_id"],
    )
    utilization = v106._utilization(sequence_document)
    accounting = {
        "initial_acquisition_labels": sequence["initial_labels"],
        "certificate_local_labels": sequence["certificate_labels"],
        "quotient_lifetime_target_labels": sequence["lifetime_labels"],
        "cold_direct_lifetime_target_labels": direct_labels,
        "target_label_reduction": direct_labels - sequence["lifetime_labels"],
        "execution_steps": sequence["execution_steps"],
        "abstract_planning_compute_events": sequence["planning_compute"],
        "sample_labels_execution_steps_and_planning_compute_separate": True,
        "scalar_cost_aggregation_performed": False,
    }
    all_plan_actions = {
        key
        for episode in sequence_document["episodes"]
        for wrapper in episode["abstract_plan_receipts"]
        for key in wrapper["abstract_plan"]["projected_action_path"]
    }
    gate = {
        "complete_anonymous_action_catalogue_receipted_before_outcomes": True,
        "every_abstract_plan_action_bound_to_catalogue_descriptor": all_plan_actions
        <= set(catalogue),
        "every_action_independently_receipted": utilization[
            "every_action_independently_receipted"
        ],
        "quotient_model_actually_orders_at_least_three_quarters": utilization[
            "quotient_actually_orders_at_least_three_quarters_of_execution"
        ],
        "chosen_action_matches_quotient_strict_majority": utilization[
            "chosen_action_matches_quotient_strict_majority"
        ],
        "certificate_local_legality_not_forced_when_preloaded_support_suffices": True,
        "certificate_failure_only_query_discipline_clean": sequence_document[
            "every_new_ground_query_followed_a_failed_certificate"
        ],
        "later_zero_label_quotient_reuse_observed": sequence[
            "later_zero_label_reuse"
        ],
        "quotient_lifetime_labels_strictly_below_cold_direct": sequence[
            "lifetime_labels"
        ]
        < direct_labels,
    }
    gate["passed"] = all(gate.values())
    if (
        document.get("legality_conditioned_quotient_utilization") != utilization
        or document.get("accounting") != accounting
        or document.get("registered_gate") != gate
        or document.get("catalogue_closed_fallback_planning_replayable")
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
        _fail("V107 occurrence Gate or claim boundary changed")
    return {
        "target_family": family,
        "seed": seed,
        "execution_steps": sequence["execution_steps"],
        "quotient_proposal_admitted_execution_count": sequence["admitted"],
        "chosen_action_matches_admitted_quotient_proposal_count": sequence[
            "matches"
        ],
        "certificate_local_legality_plan_count": sequence["local_legality"],
        "initial_acquisition_labels": sequence["initial_labels"],
        "certificate_local_labels": sequence["certificate_labels"],
        "quotient_lifetime_target_labels": sequence["lifetime_labels"],
        "cold_direct_lifetime_target_labels": direct_labels,
        "target_label_reduction": direct_labels - sequence["lifetime_labels"],
        "abstract_planning_compute_events": sequence["planning_compute"],
        "abstract_plan_receipt_count": full["abstract_plan_receipt_count"],
        "fallback_plan_receipt_count": full["fallback_plan_receipt_count"],
        "actual_execution_receipt_count_using_fallback": full[
            "actual_execution_receipt_count_using_fallback"
        ],
        "gate_passed": gate["passed"],
    }


def verify_catalogue_closed_legality_quotient_campaign_bytes_v107(
    raw: bytes,
) -> dict[str, Any]:
    if (
        type(raw) is not bytes
        or len(raw) != CAMPAIGN_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != CAMPAIGN_SHA256
    ):
        _fail("V107 campaign bytes changed")
    document = loads_canonical_json(raw)
    if canonical_json_bytes(document) != raw:
        _fail("V107 campaign is noncanonical")
    payload = {key: value for key, value in document.items() if key != "campaign_id"}
    rows = document.get("target_occurrences")
    if (
        document.get("campaign_id") != CAMPAIGN_ID
        or document.get("campaign_id")
        != domains.extension_content_id_v107(
            domains.CONSTRUCTION_K7_CATALOGUE_CLOSED_LEGALITY_QUOTIENT_CAMPAIGN_V107_DOMAIN,
            payload,
        )
        or document.get("schema")
        != "acfqp.catalogue_closed_legality_quotient_campaign.v107"
        or document.get("preregistration_id") != PREREGISTRATION_ID
        or document.get("v106_failed_campaign_id") != V106_CAMPAIGN_ID
        or document.get("v106_failed_verification_id") != V106_VERIFICATION_ID
        or type(rows) is not list
        or len(rows) != len(TARGETS)
    ):
        _fail("V107 campaign inventory changed")
    replay = [
        _occurrence(row, family, seed)
        for row, (family, seed) in zip(rows, TARGETS, strict=True)
    ]
    totals = {
        key: sum(row[key] for row in replay)
        for key in (
            "initial_acquisition_labels",
            "certificate_local_labels",
            "quotient_lifetime_target_labels",
            "cold_direct_lifetime_target_labels",
            "target_label_reduction",
            "execution_steps",
            "abstract_planning_compute_events",
            "quotient_proposal_admitted_execution_count",
            "chosen_action_matches_admitted_quotient_proposal_count",
            "certificate_local_legality_plan_count",
        )
    }
    expected_accounting = {
        **totals,
        "offline_source_labels_not_recharged": True,
        "sample_labels_execution_steps_and_planning_compute_separate": True,
        "scalar_cost_aggregation_performed": False,
    }
    ood = v106.v105._ood(document.get("incompatible_schema_no_transfer_control"))
    passed = (
        all(row["gate_passed"] for row in replay)
        and totals["certificate_local_legality_plan_count"] > 0
        and totals["quotient_lifetime_target_labels"]
        < totals["cold_direct_lifetime_target_labels"]
        and ood["strict_ood_no_transfer"] is True
    )
    gate = {
        "required_target_occurrence_count": 4,
        "passed_target_occurrence_count": sum(
            row["gate_passed"] for row in replay
        ),
        "every_occurrence_catalogue_closed": True,
        "every_occurrence_quotient_orders_at_least_three_quarters": all(
            4 * row["quotient_proposal_admitted_execution_count"]
            >= 3 * row["execution_steps"]
            for row in replay
        ),
        "every_occurrence_chosen_action_match_strict_majority": all(
            2 * row["chosen_action_matches_admitted_quotient_proposal_count"]
            > row["execution_steps"]
            for row in replay
        ),
        "aggregate_certificate_local_legality_path_observed": totals[
            "certificate_local_legality_plan_count"
        ]
        > 0,
        "no_occurrence_forced_to_manufacture_local_legality_failure": True,
        "aggregate_quotient_labels_strictly_below_cold_direct": totals[
            "quotient_lifetime_target_labels"
        ]
        < totals["cold_direct_lifetime_target_labels"],
        "strict_incompatible_schema_no_transfer_verified": True,
        "passed": passed,
    }
    if (
        document.get("accounting") != expected_accounting
        or document.get("registered_gate") != gate
        or document.get("registered_catalogue_closed_legality_conditioned_quotient_verified")
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
        _fail("V107 campaign Gate or claim boundary changed")
    return {
        "schema": "acfqp.catalogue_closed_legality_quotient_verification.v107",
        "campaign_id": CAMPAIGN_ID,
        "preregistration_id": PREREGISTRATION_ID,
        "verification_status": "REGISTERED_V107_CATALOGUE_CLOSED_QUOTIENT_VERIFIED",
        "producer_free_complete_catalogue_replay": True,
        "producer_free_observation_and_fallback_plan_reconstruction": True,
        "producer_free_per_action_receipt_replay": True,
        "producer_summary_counts_not_used": True,
        "verified_occurrences": replay,
        "verified_accounting": expected_accounting,
        "verified_abstract_plan_receipt_count": sum(
            row["abstract_plan_receipt_count"] for row in replay
        ),
        "verified_fallback_plan_receipt_count": sum(
            row["fallback_plan_receipt_count"] for row in replay
        ),
        "verified_actual_execution_receipt_count_using_fallback": sum(
            row["actual_execution_receipt_count_using_fallback"] for row in replay
        ),
        "registered_gate_independently_verified": passed,
        "ground_query_discipline_independently_verified": True,
        "global_lumpability_claimed": False,
        "complete_ground_world_model_synthesized": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }


def freeze_catalogue_closed_legality_quotient_verification_v107(raw: bytes) -> bytes:
    payload = verify_catalogue_closed_legality_quotient_campaign_bytes_v107(raw)
    document = {
        **payload,
        "verification_id": domains.extension_content_id_v107(
            domains.CONSTRUCTION_K7_CATALOGUE_CLOSED_LEGALITY_QUOTIENT_VERIFICATION_V107_DOMAIN,
            payload,
        ),
    }
    result = canonical_json_bytes(document)
    if VERIFICATION_ID != "0" * 64 and (
        document["verification_id"] != VERIFICATION_ID
        or len(result) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(result).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("V107 verification changed")
    return result


__all__ = (
    "VERIFICATION_ID",
    "freeze_catalogue_closed_legality_quotient_verification_v107",
    "verify_catalogue_closed_legality_quotient_campaign_bytes_v107",
)
