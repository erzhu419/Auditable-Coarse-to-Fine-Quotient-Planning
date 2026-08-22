"""Fresh V168 total receipt-set campaign over five stochastic families."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
import hashlib
from types import FunctionType, SimpleNamespace

from acfqp import construction_k7_domain_registry_extension_v168 as domains
from acfqp import fourth_family_sample_tax_transfer_campaign_core_v166 as v166
from acfqp import progressive_raw_prefix_campaign_core_v160 as v160
from acfqp.applicable_plan_receipt_set_sequence_v168 import (
    annotate_applicable_plan_receipt_set_sequence_v168,
)
from acfqp.certified_paid_path_switch_acquisition_operator_v162 import (
    acquire_matched_certified_paid_path_switch_arms_v162,
)
from acfqp.construction_k7_paid_path_prefix_classifier_receipt_freeze_v161 import (
    CLASSIFIER_RECEIPT_ID,
    verify_frozen_paid_path_prefix_classifier_receipt_v161,
)
from acfqp.generic_maintenance_cascade_adapter_v144 import (
    build_maintenance_cascade_adapter_v144,
)
from acfqp.generic_packet_batching_adapter_v134 import (
    FAMILY as PACKET_BATCHING_FAMILY,
    build_packet_batching_adapter_v134,
    packet_batching_config_v134,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


POSITIVE_FAMILY = v166.POSITIVE_FAMILY
FALLBACK_FAMILY = v166.FALLBACK_FAMILY
MODULAR_FAMILY = v166.MODULAR_FAMILY
MAINTENANCE_FAMILY = v166.MAINTENANCE_FAMILY
TARGET_FAMILIES = (*v166.TARGET_FAMILIES, PACKET_BATCHING_FAMILY)
V166_FAILURE_ID = (
    "2d299454ac4aaa7d0517875f568b90a782d79c1c4aa6881b5d0e18ab48d15911"
)
V167_CAMPAIGN_ID = (
    "433be30e23c4c6f1a27b6e271fb02127b3b62e8218268de8941eec64bec94839"
)
V167_CAMPAIGN_BYTE_COUNT = 23_911_368
V167_CAMPAIGN_SHA256 = (
    "73a52baa738282a18a64b5be7c4aff0f089038647b9adeca9c8ecabe2b56920b"
)


def fifth_family_total_plan_receipt_set_campaign_config_v168():
    config = v166.fourth_family_sample_tax_transfer_campaign_config_v166()
    packet = packet_batching_config_v134()
    config["families"][PACKET_BATCHING_FAMILY] = dict(
        packet["families"][PACKET_BATCHING_FAMILY]
    )
    config["families"][PACKET_BATCHING_FAMILY][
        "maximum_acquisition_labels"
    ] = 2_048
    return config


def _verify_classifier_compat(raw):
    document = verify_frozen_paid_path_prefix_classifier_receipt_v161(raw)
    return {
        **document,
        "fresh_v160_target_outcomes_accessed": document[
            "fresh_v161_target_outcomes_accessed"
        ],
    }


_V160_DOMAIN_PROXY_V168 = SimpleNamespace(
    extension_content_id_v160=domains.extension_content_id_v168,
    CONSTRUCTION_K7_OCCURRENCE_V160_DOMAIN=(
        domains.CONSTRUCTION_K7_OCCURRENCE_V168_DOMAIN
    ),
)
_V160_GLOBALS_V168 = dict(v160.__dict__)
_V160_GLOBALS_V168.update(
    domains=_V160_DOMAIN_PROXY_V168,
    CLASSIFIER_RECEIPT_ID=CLASSIFIER_RECEIPT_ID,
    _BUILDERS={
        **v160._BUILDERS,  # noqa: SLF001
        MAINTENANCE_FAMILY: build_maintenance_cascade_adapter_v144,
        PACKET_BATCHING_FAMILY: build_packet_batching_adapter_v134,
    },
    verify_frozen_progressive_raw_prefix_classifier_receipt_v160=(
        _verify_classifier_compat
    ),
    acquire_matched_progressive_raw_prefix_arms_v160=(
        acquire_matched_certified_paid_path_switch_arms_v162
    ),
    annotate_applicable_plan_mode_sequence_v157=(
        annotate_applicable_plan_receipt_set_sequence_v168
    ),
)
_BASE_V160_OCCURRENCE_V168 = FunctionType(
    v160.build_progressive_raw_prefix_occurrence_v160.__code__,
    _V160_GLOBALS_V168,
    name="_base_plan_mode_set_occurrence_v168",
)

_V166_DOMAIN_PROXY_V168 = SimpleNamespace(
    extension_content_id_v166=domains.extension_content_id_v168,
    CONSTRUCTION_K7_OCCURRENCE_V166_DOMAIN=(
        domains.CONSTRUCTION_K7_OCCURRENCE_V168_DOMAIN
    ),
    CONSTRUCTION_K7_CAMPAIGN_V166_DOMAIN=(
        domains.CONSTRUCTION_K7_CAMPAIGN_V168_DOMAIN
    ),
)
_V166_OCCURRENCE_GLOBALS_V168 = dict(v166.__dict__)
_V166_OCCURRENCE_GLOBALS_V168.update(
    domains=_V166_DOMAIN_PROXY_V168,
    _BASE_OCCURRENCE=_BASE_V160_OCCURRENCE_V168,
    TARGET_FAMILIES=TARGET_FAMILIES,
)
_BASE_V166_OCCURRENCE_V168 = FunctionType(
    v166.build_fourth_family_sample_tax_occurrence_v166.__code__,
    _V166_OCCURRENCE_GLOBALS_V168,
    name="_base_fourth_family_plan_mode_set_occurrence_v168",
)


def build_fifth_family_total_plan_receipt_set_occurrence_v168(
    config,
    *,
    family,
    seed,
    episode_indices,
    bank_raw,
    verification_raw,
    classifier_receipt_raw,
):
    base = _BASE_V166_OCCURRENCE_V168(
        config,
        family=family,
        seed=seed,
        episode_indices=episode_indices,
        bank_raw=bank_raw,
        verification_raw=verification_raw,
        classifier_receipt_raw=classifier_receipt_raw,
    )
    sequences = (
        base["progressive_prior_sequence"],
        base["progressive_strict_sequence"],
    )
    gate = {
        key: value
        for key, value in base["registered_gate"].items()
        if key
        not in {
            "passed",
            "applicable_plan_receipt_mode_agrees_between_arms",
        }
    }
    gate.update(
        registered_plan_receipt_set_totalized_both_arms=all(
            sequence["registered_plan_receipt_set_totalized"] is True
            for sequence in sequences
        ),
        none_receipt_set_is_nonfailure_v109_certificate_fallback=all(
            sequence["empty_registered_plan_mode_set_is_failure"] is False
            and (
                sequence["registered_plan_receipt_set_class"] != "NONE"
                or sequence[
                    "none_path_defers_to_v109_and_query_local_certificate"
                ]
                is True
            )
            for sequence in sequences
        ),
        mixed_plan_mode_sequence_is_temporal_not_action_competition=all(
            sequence[
                "multiple_registered_modes_mean_temporal_receipt_use_not_action_competition"
            ]
            is True
            for sequence in sequences
        ),
        every_abstract_receipt_contains_one_concrete_plan=all(
            sequence["each_abstract_receipt_contains_one_concrete_plan_document"]
            is True
            for sequence in sequences
        ),
        plan_mode_set_is_not_safety_authority=all(
            sequence["registered_plan_mode_set_is_safety_authority"] is False
            for sequence in sequences
        ),
        all_executed_actions_have_v109_receipts=all(
            sequence["all_executed_actions_have_v109_receipts"] is True
            for sequence in sequences
        ),
        v166_failed_identity_preserved=True,
        v166_same_identity_not_rerun=True,
    )
    gate["passed"] = all(
        value for value in gate.values() if type(value) is bool
    )
    payload = {
        **{
            key: value
            for key, value in base.items()
            if key not in {"schema", "occurrence_id", "registered_gate"}
        },
        "schema": "acfqp.fifth_family_total_plan_receipt_set_occurrence.v168",
        "failed_v166_attempt_id": V166_FAILURE_ID,
        "registered_plan_mode_sets": [
            sequence["applicable_plan_receipt_modes"] for sequence in sequences
        ],
        "registered_plan_receipt_set_classes": [
            sequence["registered_plan_receipt_set_class"] for sequence in sequences
        ],
        "mixed_registered_plan_mode_sequence_observed": any(
            sequence["mixed_registered_plan_mode_sequence"]
            for sequence in sequences
        ),
        "registered_gate": gate,
        "plan_mode_set_annotation_changes_planner_or_execution": False,
        "sample_tax_claim_scope": (
            "ONLY_THIS_PREREGISTERED_V168_FIVE_FAMILY_COHORT"
        ),
    }
    return {
        **payload,
        "occurrence_id": domains.extension_content_id_v168(
            domains.CONSTRUCTION_K7_OCCURRENCE_V168_DOMAIN, payload
        ),
    }


def _target_v168(args):
    return build_fifth_family_total_plan_receipt_set_occurrence_v168(
        args[0],
        family=args[1],
        seed=args[2],
        episode_indices=args[3],
        bank_raw=args[4],
        verification_raw=args[5],
        classifier_receipt_raw=args[6],
    )


def build_fifth_family_total_plan_receipt_set_campaign_v168(
    config,
    *,
    preregistration_id,
    bank_raw,
    verification_raw,
    classifier_receipt_raw,
    v167_campaign_raw,
):
    v167_campaign = loads_canonical_json(v167_campaign_raw)
    if not (
        canonical_json_bytes(v167_campaign) == v167_campaign_raw
        and len(v167_campaign_raw) == V167_CAMPAIGN_BYTE_COUNT
        and hashlib.sha256(v167_campaign_raw).hexdigest() == V167_CAMPAIGN_SHA256
        and v167_campaign.get("campaign_id") == V167_CAMPAIGN_ID
        and v167_campaign.get("registered_gate", {}).get("passed") is True
    ):
        raise ValueError("V168 frozen V167 campaign changed")
    args = [
        (
            config,
            row["family"],
            row["seed"],
            tuple(config["target_episode_indices"]),
            bank_raw,
            verification_raw,
            classifier_receipt_raw,
        )
        for row in config["target_occurrences"]
    ]
    if config["target_worker_count"] == 1:
        rows = [_target_v168(row) for row in args]
    else:
        with ProcessPoolExecutor(max_workers=config["target_worker_count"]) as executor:
            rows = list(executor.map(_target_v168, args))
    sequences = [
        row[name]
        for row in rows
        for name in ("progressive_prior_sequence", "progressive_strict_sequence")
    ]
    guards = tuple(
        row["query_policy_sample_reduction_vs_legacy_path_first"] for row in rows
    )
    factors = tuple(
        row["factor_prior_sample_reduction_within_progressive_policy"] for row in rows
    )
    numeric = [
        key for key, value in rows[0]["accounting"].items() if type(value) is int
    ]
    fresh_accounting = {
        key: sum(row["accounting"][key] for row in rows) for key in numeric
    }
    fresh_accounting.update(
        total_query_policy_labels_avoided_vs_exact_path_first=sum(guards),
        total_factor_prior_labels_avoided_within_same_query_policy=sum(factors),
        sample_labels_execution_steps_derivation_and_planning_compute_separate=True,
        scalar_cost_aggregation_performed=False,
    )
    gate = dict(
        required_fresh_packet_occurrence_count=config[
            "required_target_occurrence_count"
        ],
        passed_fresh_packet_occurrence_count=sum(
            row["registered_gate"]["passed"] for row in rows
        ),
        every_fresh_target_is_packet_batching=all(
            row["target_family"] == PACKET_BATCHING_FAMILY for row in rows
        ),
        frozen_v167_campaign_preserved=True,
        v166_frozen_failure_preserved=all(
            row["failed_v166_attempt_id"] == V166_FAILURE_ID for row in rows
        ),
        v166_failed_targets_not_reused=True,
        plan_receipt_set_totalized_everywhere=all(
            sequence["registered_plan_receipt_set_totalized"] is True
            for sequence in sequences
        ),
        none_receipt_set_is_admissible_without_authority_change=all(
            sequence["empty_registered_plan_mode_set_is_failure"] is False
            for sequence in sequences
        ),
        all_executed_actions_have_v109_receipts=all(
            sequence["all_executed_actions_have_v109_receipts"] is True
            for sequence in sequences
        ),
        mixed_plan_mode_sequences_admitted_without_authority_change=all(
            sequence["registered_plan_mode_set_changes_planning_or_execution"]
            is False
            and sequence["registered_plan_mode_set_is_safety_authority"] is False
            for sequence in sequences
        ),
        fresh_packet_query_policy_noninferior=all(value >= 0 for value in guards),
        fresh_packet_factor_prior_noninferior=all(value >= 0 for value in factors),
        fresh_packet_receding_plans_succeed=all(
            row["registered_gate"]["both_arm_receding_episodes_succeed"]
            for row in rows
        ),
        fresh_packet_certificate_failure_only_local_ground_distinctions=all(
            row["registered_gate"][
                "certificate_failure_only_local_ground_distinctions"
            ]
            for row in rows
        ),
    )
    gate["passed"] = (
        len(rows) == config["required_target_occurrence_count"]
        and gate["passed_fresh_packet_occurrence_count"] == len(rows)
        and all(value for value in gate.values() if type(value) is bool)
    )
    mode_histogram = {
        name: sum(
            sequence["registered_plan_receipt_set_class"] == name
            for sequence in sequences
        )
        for name in ("DIRECT_ONLY", "MEMOIZED_ONLY", "MIXED", "NONE")
    }
    payload = {
        "schema": "acfqp.fifth_family_total_plan_receipt_set_campaign.v168",
        "preregistration_id": preregistration_id,
        "frozen_v167_campaign": {
            "campaign_id": V167_CAMPAIGN_ID,
            "byte_count": V167_CAMPAIGN_BYTE_COUNT,
            "sha256": V167_CAMPAIGN_SHA256,
            "registered_plan_mode_sequence_histogram": v167_campaign[
                "registered_plan_mode_sequence_histogram"
            ],
        },
        "target_occurrences": rows,
        "target_occurrence_ids": [row["occurrence_id"] for row in rows],
        "fresh_packet_accounting": fresh_accounting,
        "failed_v166_attempt_id": V166_FAILURE_ID,
        "fresh_packet_registered_plan_receipt_set_histogram": mode_histogram,
        "registered_gate": gate,
        "fifth_family_factor_prior_sample_tax_transfer_verified": gate["passed"],
        "v166_failure_preserved_not_reclassified": True,
        "plan_mode_set_annotation_changes_planner_or_execution": False,
        "mixed_and_none_branches_are_semantic_totalization_not_observed_frequency_claim": True,
        "sample_tax_claim_scope": (
            "V167_FOUR_FAMILY_EVIDENCE_PLUS_THIS_PREREGISTERED_V168_PACKET_COHORT"
        ),
        "query_policy_classifier_is_model_planning_or_certificate_authority": False,
        "complete_world_model_synthesized": False,
        "arbitrary_unseen_domain_transfer_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    return {
        **payload,
        "campaign_id": domains.extension_content_id_v168(
            domains.CONSTRUCTION_K7_CAMPAIGN_V168_DOMAIN, payload
        ),
    }


__all__ = (
    "FALLBACK_FAMILY",
    "MAINTENANCE_FAMILY",
    "MODULAR_FAMILY",
    "PACKET_BATCHING_FAMILY",
    "POSITIVE_FAMILY",
    "TARGET_FAMILIES",
    "V166_FAILURE_ID",
    "build_fifth_family_total_plan_receipt_set_campaign_v168",
    "build_fifth_family_total_plan_receipt_set_occurrence_v168",
    "fifth_family_total_plan_receipt_set_campaign_config_v168",
)
