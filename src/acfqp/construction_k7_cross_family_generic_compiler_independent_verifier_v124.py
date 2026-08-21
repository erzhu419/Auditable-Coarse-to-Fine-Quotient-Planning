"""Producer-free verification of the V124 cross-family generic compiler."""

from __future__ import annotations

import hashlib
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_generic_quotient_compiler_independent_verifier_v123r1 as generic
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "d2da5c1f3271b362a584156fa7febe4d0cf2e715e14d9d4d453eeef471aa1d26"
CAMPAIGN_BYTE_COUNT = 1_830_635
CAMPAIGN_SHA256 = "b1a1f7e40747275077ce32e3147a48bef2235de23bc3b983e86b79d36a32eb49"
PREREGISTRATION_ID = "6c477fe146df4ba12cf0b0fcfd79c2dc7d865dac3a2781b1b586104ca1add7cc"
V123R1_CAMPAIGN_ID = generic.CAMPAIGN_ID
V123R1_VERIFICATION_ID = generic.VERIFICATION_ID
EXPECTED_FAMILY = "STOCHASTIC_INVENTORY_ASSEMBLY"
EXPECTED_SEEDS = (1_039_101, 1_039_102)
EXPECTED_EPISODES = (296, 297, 298)
VERIFICATION_ID = "f58ab2a74d21907b019da2461b26b33c6d988416eb4050cb7545370b5ff24ea1"
EXPECTED_CANONICAL_BYTE_COUNT = 3_636
EXPECTED_CANONICAL_SHA256 = "5dac5d7a7f147759e82c7384d13a3ee4148285ca852057077ba5ad8fddbf7f7b"


_DOMAINS = {
    "campaign": "acfqp:construction-k7-cross-family-generic-compiler-campaign:v124",
    "occurrence": "acfqp:construction-k7-cross-family-generic-compiler-occurrence:v124",
    "sequence": "acfqp:construction-k7-cross-family-generic-compiler-sequence:v124",
    "verification": "acfqp:construction-k7-cross-family-generic-compiler-verification:v124",
    "acquisition": "acfqp:construction-k7-generic-artifact-subprogram-partial-acquisition:v121",
    "strict": "acfqp:construction-k7-generic-artifact-subprogram-strict-control:v121",
    "v119_sequence": "acfqp:construction-k7-source-unseen-residual-genesis-authorized-branch-sequence:v119",
    "v113_sequence": "acfqp:construction-k7-incremental-abstract-successor-sequence:v113",
    "plan": "acfqp:generic-legality-conditioned-quotient-plan:v106",
}


class ConstructionK7CrossFamilyGenericCompilerIndependentVerifierV124Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7CrossFamilyGenericCompilerIndependentVerifierV124Error(message)


def _require(condition: bool, message: str) -> None:
    if condition is not True:
        _fail(message)


def _content_id(domain: str, payload: Any) -> str:
    return hashlib.sha256(domain.encode() + b"\x00" + canonical_json_bytes(payload)).hexdigest()


def _verify_id(document: Mapping[str, Any], key: str, domain: str) -> None:
    payload = {name: value for name, value in document.items() if name != key}
    _require(document.get(key) == _content_id(domain, payload), f"V124 {key} changed")


def _verify_occurrence(row: Mapping[str, Any]) -> dict[str, Any]:
    _require(
        row.get("schema") == "acfqp.cross_family_generic_compiler_occurrence.v124"
        and row.get("target_family") == EXPECTED_FAMILY,
        "V124 occurrence family/schema changed",
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
        "V124 acquisition/control join changed",
    )
    sequence = row["generic_compiler_sequence"]
    _verify_id(sequence, "sequence_id", _DOMAINS["sequence"])
    v119 = sequence["generic_compiler_base_sequence"]
    _verify_id(v119, "sequence_id", _DOMAINS["v119_sequence"])
    base = v119["genesis_authorized_base_sequence"]
    _verify_id(base, "sequence_id", _DOMAINS["v113_sequence"])
    _require(
        sequence["generic_compiler_base_sequence_id"] == v119["sequence_id"]
        and sequence["partial_candidate_id"] == candidate["candidate_id"]
        and v119["partial_candidate_id"] == candidate["candidate_id"]
        and base["partial_candidate_id"] == candidate["candidate_id"],
        "V124 sequence/candidate joins changed",
    )
    receipt = v119["program_branch_dependency_receipt"]
    _require(
        receipt["compiled_factor_assignments"] == candidate["compiled_factor_assignments"]
        and receipt["partial_candidate_id"] == candidate["candidate_id"],
        "V124 program dependency receipt changed",
    )
    actions = {
        action["action_key"]: tuple(action["canonical_anonymous_fields"])
        for action in receipt["canonical_action_catalogue"]
    }
    persistent = base["persistent_exact_overlay_rows"]
    _require(
        hashlib.sha256(canonical_json_bytes(persistent)).hexdigest()
        == base["persistent_exact_overlay_sha256"],
        "V124 persistent raw evidence changed",
    )
    new_keys = {
        generic._raw_key(raw)  # noqa: SLF001
        for episode in base["episodes"]
        for raw in episode["raw_incremental_transition_rows"]
    }
    current = {
        generic._raw_key(raw): raw  # noqa: SLF001
        for raw in persistent
        if generic._raw_key(raw) not in new_keys  # noqa: SLF001
    }
    rebuilt = []
    direct = memoized = path_checks = 0
    for index, episode in enumerate(base["episodes"]):
        before, rules = generic._compile_model(tuple(current.values()), candidate, actions)  # noqa: SLF001
        _require(before == base["quotient_models_before_each_episode"][index], "V124 before-model reconstruction changed")
        rebuilt.append(before)
        for plan_receipt in episode["abstract_plan_receipts"]:
            plan = plan_receipt["abstract_plan"]
            source = plan["planning_source"]
            if source in {"OBSERVATION_QUOTIENT_GRAPH", "COMPILED_FACTOR_PROGRAM_FALLBACK"}:
                _verify_id(plan, "legality_conditioned_quotient_plan_id", _DOMAINS["plan"])
                _require(tuple(plan["embedded_projected_plan"]["terminal_projection_rule"]) == rules, "V124 terminal rules changed")
                path_checks += generic._verify_plan(  # noqa: SLF001
                    plan,
                    plan_receipt["raw_state"],
                    candidate,
                    actions,
                    before,
                    rules,
                )
                if source == "COMPILED_FACTOR_PROGRAM_FALLBACK":
                    direct += 1
                    _require(plan["legacy_shape_specific_planner_execution_adapter_called"] is False, "V124 legacy planner path changed")
            elif source == "COMPILED_FACTOR_PROGRAM_MEMOIZED":
                memoized += 1
                _require(plan["source_compiled_factor_program_plan"]["legacy_shape_specific_planner_execution_adapter_called"] is False, "V124 memoized plan source changed")
        for raw in episode["raw_incremental_transition_rows"]:
            current[generic._raw_key(raw)] = raw  # noqa: SLF001
        after, _after_rules = generic._compile_model(tuple(current.values()), candidate, actions)  # noqa: SLF001
        _require(after == base["quotient_models_after_each_episode"][index], "V124 after-model reconstruction changed")
        rebuilt.append(after)
        _require(
            episode["success"] is True
            and episode["all_incremental_ground_queries_followed_failed_certificates"] is True
            and episode["planner_raw_transition_argument_present"] is False,
            "V124 episode/certificate discipline changed",
        )
    checks = sum(model["source_projected_edge_program_checks"] for model in rebuilt)
    reconstruction = {
        "generic_model_epoch_reconstruction_count": len(rebuilt),
        "generic_model_program_support_checks": checks,
        "every_model_epoch_reconstructed_only_by_generic_compiler": True,
        "legacy_shape_specific_model_builder_called": False,
        "legacy_matched_control_present": False,
    }
    _require(
        sequence["generic_model_epoch_reconstruction"] == reconstruction
        and sequence["direct_generic_factor_program_plan_count"] == direct
        and sequence["legacy_shape_specific_model_builder_called"] is False
        and sequence["legacy_matched_model_control_present"] is False
        and sequence["retained_v113_state_carrier_present"] is True,
        "V124 generic reconstruction/claim boundary changed",
    )
    accounting = {
        "partial_prior_acquisition_labels": acquisition["ground_support_labels"],
        "strict_control_matched_prefix_labels": strict["ground_support_labels"],
        "strict_complete_model_attempt_count": strict["attempt_count"],
        "certificate_local_labels": base["certificate_ground_support_labels_paid_once"],
        "lifetime_target_labels": base["lifetime_target_ground_support_labels"],
        "execution_steps": base["execution_step_count"],
        "abstract_planning_compute_events": v119["actual_new_abstract_planning_compute_events"],
        "matched_uncached_planning_compute_events": v119["matched_uncached_abstract_planning_compute_events"],
        "planning_compute_events_avoided_against_uncached": v119["planning_compute_events_avoided_against_uncached"],
        "dependency_derivation_compute_events": v119["dependency_derivation_compute_events"],
        "generic_model_epoch_reconstructions": len(rebuilt),
        "generic_model_program_support_checks": checks,
        "direct_generic_factor_program_plans": direct,
        "sample_labels_execution_steps_derivation_planning_and_model_checks_separate": True,
        "scalar_cost_aggregation_performed": False,
    }
    _require(
        row["accounting"] == accounting
        and row["registered_gate"]["passed"] is True
        and all(value is True for key, value in row["registered_gate"].items() if key != "passed")
        and row["legacy_shape_specific_model_builder_called"] is False
        and row["legacy_matched_model_control_present"] is False
        and row["retained_v113_state_carrier_present"] is True
        and row["complete_ground_world_model_synthesized"] is False
        and row["official_scalar_cost"] is None,
        "V124 occurrence accounting/Gate changed",
    )
    return {
        "occurrence_id": row["occurrence_id"],
        "seed": row["seed"],
        "episode_count": len(base["episodes"]),
        "independently_rebuilt_model_epoch_count": len(rebuilt),
        "independent_plan_path_support_checks": path_checks,
        "memoized_plan_count": memoized,
        "accounting": accounting,
    }


def freeze_cross_family_generic_compiler_verification_v124(
    campaign_raw: bytes,
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
        "V124 frozen campaign identity or bytes changed",
    )
    _verify_id(campaign, "campaign_id", _DOMAINS["campaign"])
    _require(
        generic.freeze_generic_quotient_compiler_verification_v123r1(
            v123r1_campaign_raw,
            v122_campaign_raw,
            v122_verification_raw,
            failed_v123_raw,
            v121r1_campaign_raw,
            v121_failed_campaign_raw,
            v121r1_verification_raw,
            dict(source_campaign_bytes),
        )
        == v123r1_verification_raw,
        "V124 V123r1 producer-free predecessor changed",
    )
    _require(
        campaign["preregistration_id"] == PREREGISTRATION_ID
        and campaign["v123r1_success_campaign_id"] == V123R1_CAMPAIGN_ID
        and campaign["v123r1_success_verification_id"] == V123R1_VERIFICATION_ID,
        "V124 predecessor joins changed",
    )
    rows = tuple(_verify_occurrence(row) for row in campaign["target_occurrences"])
    _require(
        tuple(row["seed"] for row in rows) == EXPECTED_SEEDS
        and all(row["episode_count"] == len(EXPECTED_EPISODES) for row in rows)
        and campaign["target_occurrence_ids"] == [row["occurrence_id"] for row in rows],
        "V124 occurrence identities changed",
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
        and campaign["registered_gate"]["passed"] is True
        and campaign["registered_gate"]["passed_target_occurrence_count"] == 2
        and campaign["legacy_shape_specific_model_builder_called"] is False
        and campaign["legacy_matched_model_control_present"] is False
        and campaign["retained_v113_state_carrier_present"] is True
        and campaign["sample_efficiency_improvement_claimed"] is False
        and campaign["complete_ground_world_model_synthesized"] is False
        and campaign["official_execution_allowed"] is False
        and campaign["official_scalar_cost"] is None
        and campaign["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN",
        "V124 campaign accounting/Gate changed",
    )
    payload = {
        "schema": "acfqp.cross_family_generic_compiler_verification.v124",
        "campaign_id": CAMPAIGN_ID,
        "preregistration_id": PREREGISTRATION_ID,
        "v123r1_predecessor_verification_id": V123R1_VERIFICATION_ID,
        "verified_family": EXPECTED_FAMILY,
        "verified_occurrences": list(rows),
        "verified_accounting": accounting,
        "producer_free_raw_transition_model_epoch_reconstruction": True,
        "producer_free_recursive_expression_successor_reconstruction": True,
        "producer_free_terminal_rule_and_plan_reconstruction": True,
        "registered_gate_independently_verified": True,
        "legacy_shape_specific_model_builder_called": False,
        "legacy_matched_model_control_present": False,
        "retained_v113_state_carrier_present": True,
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
        _require(document["verification_id"] == VERIFICATION_ID and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256, "V124 frozen verification changed")
    return raw


__all__ = ("VERIFICATION_ID", "freeze_cross_family_generic_compiler_verification_v124")
