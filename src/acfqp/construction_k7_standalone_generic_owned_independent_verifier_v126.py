"""Producer-free verification of the V126 owned generic-model episode loop."""

from __future__ import annotations

import hashlib
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_standalone_generic_model_independent_verifier_v125 as previous
from acfqp import construction_k7_generic_quotient_compiler_independent_verifier_v123r1 as generic
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "c10d9d46c448c2fc12661b24a47886c9b8b4c53f6849609e76f0620f8d21877f"
CAMPAIGN_BYTE_COUNT = 2_287_042
CAMPAIGN_SHA256 = "4f4277bc8b35297ddc5ff272fbaaa0e37734f1ee0d419b52d825285f8ec36085"
PREREGISTRATION_ID = "d069767abba581d17917da663428ae29839267fa6255116d89d7b8f4a011da51"
V125_CAMPAIGN_ID = previous.CAMPAIGN_ID
V125_VERIFICATION_ID = previous.VERIFICATION_ID
EXPECTED_FAMILY = "STOCHASTIC_INVENTORY_ASSEMBLY"
EXPECTED_SEEDS = (1_041_101, 1_041_102)
EXPECTED_EPISODES = (305, 306, 307)
VERIFICATION_ID = "67943949e90173d5daa9aaf50a0c38f132e3c7b4fb9682005ae3a9b414cee756"
EXPECTED_CANONICAL_BYTE_COUNT = 3_846
EXPECTED_CANONICAL_SHA256 = "78eda7db87601302a2298a56afe082966944f8dfd1abf585fdf3c55c4f8ab7f6"


_DOMAINS = {
    "campaign": "acfqp:construction-k7-standalone-generic-owned-campaign:v126",
    "occurrence": "acfqp:construction-k7-standalone-generic-owned-occurrence:v126",
    "sequence": "acfqp:construction-k7-standalone-generic-owned-sequence:v126",
    "verification": "acfqp:construction-k7-standalone-generic-owned-verification:v126",
    "acquisition": "acfqp:construction-k7-generic-artifact-subprogram-partial-acquisition:v121",
    "strict": "acfqp:construction-k7-generic-artifact-subprogram-strict-control:v121",
    "plan": "acfqp:generic-legality-conditioned-quotient-plan:v106",
    "ood": "acfqp:incompatible-schema-no-transfer-control:v99",
}


class ConstructionK7StandaloneGenericOwnedIndependentVerifierV126Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7StandaloneGenericOwnedIndependentVerifierV126Error(message)


def _require(condition: bool, message: str) -> None:
    if condition is not True:
        _fail(message)


def _content_id(domain: str, payload: Any) -> str:
    return hashlib.sha256(domain.encode() + b"\x00" + canonical_json_bytes(payload)).hexdigest()


def _verify_id(document: Mapping[str, Any], key: str, domain: str) -> None:
    payload = {name: value for name, value in document.items() if name != key}
    _require(document.get(key) == _content_id(domain, payload), f"V126 {key} changed")


def _verify_occurrence(row: Mapping[str, Any]) -> dict[str, Any]:
    _require(
        row.get("schema") == "acfqp.standalone_generic_owned_occurrence.v126"
        and row.get("target_family") == EXPECTED_FAMILY,
        "V126 occurrence family/schema changed",
    )
    _verify_id(row, "occurrence_id", _DOMAINS["occurrence"])
    acquisition = row["partial_prior_acquisition"]
    strict = row["strict_no_prior_complete_model_control"]
    _verify_id(acquisition, "acquisition_id", _DOMAINS["acquisition"])
    _verify_id(strict, "strict_control_id", _DOMAINS["strict"])
    candidate = acquisition["candidate"]
    _verify_id(candidate, "candidate_id", _DOMAINS["acquisition"])
    _require(
        acquisition["family"] == EXPECTED_FAMILY
        and acquisition["ground_support_labels"] == strict["ground_support_labels"]
        and acquisition["raw_transition_sha256"] == strict["raw_transition_sha256"]
        and bool(candidate["unknown_residual_target_columns"]),
        "V126 acquisition/control join changed",
    )
    sequence = row["standalone_generic_owned_sequence"]
    _verify_id(sequence, "sequence_id", _DOMAINS["sequence"])
    _require(
        row["standalone_generic_owned_sequence_id"] == sequence["sequence_id"]
        and sequence["partial_candidate_id"] == candidate["candidate_id"]
        and sequence["family"] == EXPECTED_FAMILY
        and sequence["seed"] == row["seed"]
        and tuple(sequence["episode_indices"]) == EXPECTED_EPISODES,
        "V126 owned sequence identity changed",
    )
    dependency = sequence["program_branch_dependency_receipt"]
    _require(
        sequence["program_branch_dependency_receipt_id"] == dependency["dependency_receipt_id"]
        and dependency["partial_candidate_id"] == candidate["candidate_id"]
        and dependency["compiled_factor_assignments"] == candidate["compiled_factor_assignments"],
        "V126 dependency receipt changed",
    )
    actions = {
        action["action_key"]: tuple(action["canonical_anonymous_fields"])
        for action in dependency["canonical_action_catalogue"]
    }
    persistent = sequence["persistent_exact_overlay_rows"]
    _require(
        hashlib.sha256(canonical_json_bytes(persistent)).hexdigest()
        == sequence["persistent_exact_overlay_sha256"],
        "V126 persistent raw evidence changed",
    )
    episode_keys = {
        previous._raw_key(raw)  # noqa: SLF001
        for episode in sequence["episodes"]
        for raw in episode["raw_incremental_transition_rows"]
    }
    current = {
        previous._raw_key(raw): raw  # noqa: SLF001
        for raw in persistent
        if previous._raw_key(raw) not in episode_keys  # noqa: SLF001
    }
    initial_rows = tuple(current.values())
    facts = previous._project(initial_rows, candidate, actions)  # noqa: SLF001
    _require(
        facts["model"] == sequence["quotient_models_before_each_episode"][0]
        and previous._bootstrap_receipt(initial_rows, facts) == sequence["bootstrap_receipt"]  # noqa: SLF001
        and previous._match_receipt(facts, initial_rows, None) == sequence["bootstrap_full_rebuild_match"],  # noqa: SLF001
        "V126 bootstrap reconstruction changed",
    )
    updates = sequence["standalone_model_update_receipts"]
    matches = sequence["standalone_full_rebuild_match_receipts"]
    _require(
        len(sequence["episodes"]) == len(updates) == len(matches) == len(EXPECTED_EPISODES),
        "V126 episode/receipt cardinality changed",
    )
    rebuilt = []
    path_checks = direct = reused = 0
    all_plans = []
    for index, episode in enumerate(sequence["episodes"]):
        before = previous._project(tuple(current.values()), candidate, actions)  # noqa: SLF001
        _require(
            before["model"] == sequence["quotient_models_before_each_episode"][index]
            and episode["quotient_graph_before_episode"] == before["model"]
            and episode["standalone_model_state_id_before_episode"] == before["state_id"]
            and updates[index]["previous_successor_state_id"] == before["state_id"],
            "V126 before-model/state reconstruction changed",
        )
        rebuilt.append(before["model"])
        for wrapper in episode["abstract_plan_receipts"]:
            plan = wrapper["abstract_plan"]
            all_plans.append(plan)
            source = plan["planning_source"]
            if source in {"OBSERVATION_QUOTIENT_GRAPH", "COMPILED_FACTOR_PROGRAM_FALLBACK"}:
                _verify_id(plan, "legality_conditioned_quotient_plan_id", _DOMAINS["plan"])
                _require(
                    tuple(plan["embedded_projected_plan"]["terminal_projection_rule"]) == before["rules"],
                    "V126 terminal rule changed",
                )
                path_checks += generic._verify_plan(  # noqa: SLF001
                    plan,
                    wrapper["raw_state"],
                    candidate,
                    actions,
                    before["model"],
                    before["rules"],
                )
                if source == "COMPILED_FACTOR_PROGRAM_FALLBACK":
                    direct += 1
                    _require(
                        plan["generic_factor_program_execution_adapter_used"] is True
                        and plan["legacy_shape_specific_planner_execution_adapter_called"] is False,
                        "V126 direct generic plan changed",
                    )
            elif source in {"COMPILED_FACTOR_PROGRAM_MEMOIZED", "DEPENDENCY_REVALIDATED_PRIOR_QUOTIENT_ORDER"}:
                reused += 1
                if source == "DEPENDENCY_REVALIDATED_PRIOR_QUOTIENT_ORDER":
                    _require(
                        plan["cached_ordering_used_as_safety_authority"] is False
                        and plan["dependency_revalidation"]["current_quotient_graph_id"] == before["model"]["quotient_graph_id"],
                        "V126 dependency reuse changed",
                    )
            else:
                _fail("V126 unknown planning source")
        delta_rows = tuple(episode["raw_incremental_transition_rows"])
        novel_rows = tuple(raw for raw in delta_rows if previous._raw_key(raw) not in current)  # noqa: SLF001
        novel = previous._project(novel_rows, candidate, actions) if novel_rows else {"raw_keys": frozenset(), "checks": 0}  # noqa: SLF001
        for raw in delta_rows:
            current[previous._raw_key(raw)] = raw  # noqa: SLF001
        after = previous._project(tuple(current.values()), candidate, actions)  # noqa: SLF001
        expected_update = previous._update_receipt(before, after, delta_rows, novel)  # noqa: SLF001
        expected_match = previous._match_receipt(after, tuple(current.values()), expected_update)  # noqa: SLF001
        _require(
            expected_update == updates[index]
            and expected_match == matches[index]
            and episode["standalone_model_update_after_episode"] == expected_update
            and episode["standalone_full_rebuild_match_after_episode"] == expected_match
            and episode["quotient_graph_after_episode"] == after["model"]
            and episode["standalone_model_state_id_after_episode"] == after["state_id"]
            and after["model"] == sequence["quotient_models_after_each_episode"][index],
            "V126 update/full-match/after-state reconstruction changed",
        )
        rebuilt.append(after["model"])
        _require(
            episode["success"] is True
            and episode["all_incremental_ground_queries_followed_failed_certificates"] is True
            and episode["planner_raw_transition_argument_present"] is False,
            "V126 episode certificate discipline changed",
        )
    _require(len(current) == len(persistent), "V126 persistent inventory changed")
    model_checks = sum(model["source_projected_edge_program_checks"] for model in rebuilt)
    uncached_compute = sum(
        plan.get("embedded_projected_plan", {}).get(
            "matched_uncached_projected_planning_compute_events",
            plan["abstract_support_branch_evaluations"],
        )
        for plan in all_plans
    )
    actual_compute = sum(episode["abstract_planning_compute_events"] for episode in sequence["episodes"])
    dependency_compute = len(EXPECTED_EPISODES) * (
        len(dependency["compiled_factor_assignments"])
        + len(dependency["canonical_action_catalogue"])
    )
    _require(
        sequence["dependency_receipt_rederivation_count"] == len(EXPECTED_EPISODES)
        and sequence["dependency_derivation_compute_events"] == dependency_compute
        and sequence["actual_new_abstract_planning_compute_events"] == actual_compute
        and sequence["matched_uncached_abstract_planning_compute_events"] == uncached_compute
        and sequence["planning_compute_events_avoided_against_uncached"] == uncached_compute - actual_compute
        and sequence["direct_generic_factor_program_plan_count"] == direct
        and sequence["owned_episode_loop_implementation_present"] is True
        and sequence["standalone_v125_state_carrier_verified"] is True
        and sequence["retained_v113_state_carrier_present"] is False
        and sequence["retained_v113_sequence_orchestration_present"] is False
        and sequence["retained_v119_sequence_orchestration_present"] is False
        and sequence["compiled_model_cache_or_receipt_used_as_safety_authority"] is False,
        "V126 owned-loop accounting/claim boundary changed",
    )
    accounting = {
        "partial_prior_acquisition_labels": acquisition["ground_support_labels"],
        "strict_control_matched_prefix_labels": strict["ground_support_labels"],
        "strict_complete_model_attempt_count": strict["attempt_count"],
        "certificate_local_labels": sequence["certificate_ground_support_labels_paid_once"],
        "lifetime_target_labels": sequence["lifetime_target_ground_support_labels"],
        "execution_steps": sequence["execution_step_count"],
        "abstract_planning_compute_events": sequence["actual_new_abstract_planning_compute_events"],
        "matched_uncached_planning_compute_events": sequence["matched_uncached_abstract_planning_compute_events"],
        "planning_compute_events_avoided_against_uncached": sequence["planning_compute_events_avoided_against_uncached"],
        "dependency_derivation_compute_events": dependency_compute,
        "standalone_model_epoch_reconstructions": len(rebuilt),
        "generic_model_program_support_checks": model_checks,
        "direct_generic_factor_program_plans": direct,
        "sample_labels_execution_steps_derivation_planning_and_model_checks_separate": True,
        "scalar_cost_aggregation_performed": False,
    }
    _require(
        row["accounting"] == accounting
        and row["registered_gate"]["passed"] is True
        and all(value is True for key, value in row["registered_gate"].items() if key != "passed")
        and row["registered_owned_generic_sequence_verified"] is True
        and row["retained_v113_state_carrier_present"] is False
        and row["retained_v113_sequence_orchestration_present"] is False
        and row["retained_v119_sequence_orchestration_present"] is False
        and row["compiled_model_or_receipt_used_as_safety_authority"] is False
        and row["complete_ground_world_model_synthesized"] is False
        and row["official_scalar_cost"] is None,
        "V126 occurrence Gate/accounting changed",
    )
    return {
        "occurrence_id": row["occurrence_id"],
        "seed": row["seed"],
        "episode_count": len(sequence["episodes"]),
        "independently_rebuilt_v125_model_epoch_count": len(rebuilt),
        "independently_rebuilt_v125_receipt_count": 2 + 2 * len(sequence["episodes"]),
        "independent_plan_path_support_checks": path_checks,
        "reused_plan_count": reused,
        "accounting": accounting,
    }


def freeze_standalone_generic_owned_verification_v126(
    campaign_raw: bytes,
    v125_campaign_raw: bytes,
    v125_verification_raw: bytes,
    v124_campaign_raw: bytes,
    v124_verification_raw: bytes,
    v123r1_campaign_raw: bytes,
    v123r1_verification_raw: bytes,
    v122_campaign_raw: bytes,
    v122_verification_raw: bytes,
    failed_v123_raw: bytes,
    v121r1_campaign_raw: bytes,
    v121_failed_campaign_raw: bytes,
    v121r1_verification_raw: bytes,
    source_campaign_bytes: Mapping[str, bytes],
) -> bytes:
    campaign = loads_canonical_json(campaign_raw)
    _require(
        canonical_json_bytes(campaign) == campaign_raw
        and len(campaign_raw) == CAMPAIGN_BYTE_COUNT
        and hashlib.sha256(campaign_raw).hexdigest() == CAMPAIGN_SHA256
        and campaign.get("campaign_id") == CAMPAIGN_ID,
        "V126 frozen campaign identity/bytes changed",
    )
    _verify_id(campaign, "campaign_id", _DOMAINS["campaign"])
    _require(
        previous.freeze_standalone_generic_model_verification_v125(
            v125_campaign_raw,
            v124_campaign_raw,
            v124_verification_raw,
            v123r1_campaign_raw,
            v123r1_verification_raw,
            v122_campaign_raw,
            v122_verification_raw,
            failed_v123_raw,
            v121r1_campaign_raw,
            v121_failed_campaign_raw,
            v121r1_verification_raw,
            dict(source_campaign_bytes),
        )
        == v125_verification_raw,
        "V126 V125 producer-free predecessor changed",
    )
    _require(
        campaign["preregistration_id"] == PREREGISTRATION_ID
        and campaign["v125_success_campaign_id"] == V125_CAMPAIGN_ID
        and campaign["v125_success_verification_id"] == V125_VERIFICATION_ID,
        "V126 predecessor joins changed",
    )
    rows = tuple(_verify_occurrence(row) for row in campaign["target_occurrences"])
    _require(
        tuple(row["seed"] for row in rows) == EXPECTED_SEEDS
        and all(row["episode_count"] == len(EXPECTED_EPISODES) for row in rows)
        and campaign["target_occurrence_ids"] == [row["occurrence_id"] for row in rows],
        "V126 occurrence identities changed",
    )
    ood = campaign["incompatible_schema_no_transfer_control"]
    ood_payload = {key: value for key, value in ood.items() if key != "control_id"}
    _require(
        ood["control_id"] == _content_id(_DOMAINS["ood"], ood_payload)
        and ood["strict_ood_no_transfer"] is True
        and ood["learned_structure_prior_delivered"] is False
        and ood["target_outcomes_accessed"] is False,
        "V126 strict OOD control changed",
    )
    numeric = [key for key, value in rows[0]["accounting"].items() if type(value) is int]
    accounting = {key: sum(row["accounting"][key] for row in rows) for key in numeric}
    accounting.update(
        sample_labels_execution_steps_derivation_planning_and_model_checks_separate=True,
        sample_efficiency_improvement_claimed=False,
        scalar_cost_aggregation_performed=False,
    )
    _require(
        campaign["accounting"] == accounting
        and campaign["registered_gate"] == {
            "required_target_occurrence_count": 2,
            "passed_target_occurrence_count": 2,
            "owned_v126_episode_loop_used_in_every_occurrence": True,
            "retained_v113_sequence_orchestration_absent_in_every_occurrence": True,
            "retained_v119_sequence_orchestration_absent_in_every_occurrence": True,
            "all_receding_episodes_succeed": True,
            "strict_incompatible_schema_no_transfer_verified": True,
            "passed": True,
        }
        and campaign["registered_owned_generic_sequence_verified"] is True
        and campaign["retained_v113_state_carrier_present"] is False
        and campaign["retained_v113_sequence_orchestration_present"] is False
        and campaign["retained_v119_sequence_orchestration_present"] is False
        and campaign["sample_efficiency_improvement_claimed"] is False
        and campaign["complete_ground_world_model_synthesized"] is False
        and campaign["official_execution_allowed"] is False
        and campaign["official_scalar_cost"] is None
        and campaign["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
        and campaign["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN",
        "V126 campaign Gate/accounting changed",
    )
    payload = {
        "schema": "acfqp.standalone_generic_owned_verification.v126",
        "campaign_id": CAMPAIGN_ID,
        "preregistration_id": PREREGISTRATION_ID,
        "v125_predecessor_verification_id": V125_VERIFICATION_ID,
        "verified_family": EXPECTED_FAMILY,
        "verified_occurrences": list(rows),
        "verified_accounting": accounting,
        "producer_free_owned_episode_loop_reconstruction": True,
        "producer_free_raw_transition_v125_model_epoch_reconstruction": True,
        "producer_free_v125_receipt_reconstruction": True,
        "producer_free_terminal_rule_and_plan_reconstruction": True,
        "registered_gate_independently_verified": True,
        "retained_v113_state_carrier_present": False,
        "retained_v113_sequence_orchestration_present": False,
        "retained_v119_sequence_orchestration_present": False,
        "retained_v119_ordering_primitives_present": True,
        "arbitrary_unseen_domain_transfer_claimed": False,
        "sample_efficiency_improvement_claimed": False,
        "complete_ground_world_model_synthesized": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    document = {**payload, "verification_id": _content_id(_DOMAINS["verification"], payload)}
    raw = canonical_json_bytes(document)
    if VERIFICATION_ID != "0" * 64:
        _require(
            document["verification_id"] == VERIFICATION_ID
            and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
            and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256,
            "V126 frozen verification changed",
        )
    return raw


__all__ = ("VERIFICATION_ID", "freeze_standalone_generic_owned_verification_v126")
