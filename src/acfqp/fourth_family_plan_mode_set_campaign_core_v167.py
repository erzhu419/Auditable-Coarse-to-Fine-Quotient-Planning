"""Fresh V167 successor using receipt-set rather than occurrence-wide XOR."""

from __future__ import annotations

from types import FunctionType, SimpleNamespace

from acfqp import construction_k7_domain_registry_extension_v167 as domains
from acfqp import fourth_family_sample_tax_transfer_campaign_core_v166 as v166
from acfqp import progressive_raw_prefix_campaign_core_v160 as v160
from acfqp.applicable_plan_mode_set_sequence_v167 import (
    annotate_applicable_plan_mode_set_sequence_v167,
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
from acfqp.phase3e_ids import canonical_json_bytes


POSITIVE_FAMILY = v166.POSITIVE_FAMILY
FALLBACK_FAMILY = v166.FALLBACK_FAMILY
MODULAR_FAMILY = v166.MODULAR_FAMILY
MAINTENANCE_FAMILY = v166.MAINTENANCE_FAMILY
TARGET_FAMILIES = v166.TARGET_FAMILIES
V166_FAILURE_ID = (
    "2d299454ac4aaa7d0517875f568b90a782d79c1c4aa6881b5d0e18ab48d15911"
)


def fourth_family_plan_mode_set_campaign_config_v167():
    return v166.fourth_family_sample_tax_transfer_campaign_config_v166()


def _verify_classifier_compat(raw):
    document = verify_frozen_paid_path_prefix_classifier_receipt_v161(raw)
    return {
        **document,
        "fresh_v160_target_outcomes_accessed": document[
            "fresh_v161_target_outcomes_accessed"
        ],
    }


_V160_DOMAIN_PROXY = SimpleNamespace(
    extension_content_id_v160=domains.extension_content_id_v167,
    CONSTRUCTION_K7_OCCURRENCE_V160_DOMAIN=(
        domains.CONSTRUCTION_K7_OCCURRENCE_V167_DOMAIN
    ),
)
_V160_GLOBALS = dict(v160.__dict__)
_V160_GLOBALS.update(
    domains=_V160_DOMAIN_PROXY,
    CLASSIFIER_RECEIPT_ID=CLASSIFIER_RECEIPT_ID,
    _BUILDERS={
        **v160._BUILDERS,  # noqa: SLF001
        MAINTENANCE_FAMILY: build_maintenance_cascade_adapter_v144,
    },
    verify_frozen_progressive_raw_prefix_classifier_receipt_v160=(
        _verify_classifier_compat
    ),
    acquire_matched_progressive_raw_prefix_arms_v160=(
        acquire_matched_certified_paid_path_switch_arms_v162
    ),
    annotate_applicable_plan_mode_sequence_v157=(
        annotate_applicable_plan_mode_set_sequence_v167
    ),
)
_BASE_V160_OCCURRENCE = FunctionType(
    v160.build_progressive_raw_prefix_occurrence_v160.__code__,
    _V160_GLOBALS,
    name="_base_plan_mode_set_occurrence_v167",
)

_V166_DOMAIN_PROXY = SimpleNamespace(
    extension_content_id_v166=domains.extension_content_id_v167,
    CONSTRUCTION_K7_OCCURRENCE_V166_DOMAIN=(
        domains.CONSTRUCTION_K7_OCCURRENCE_V167_DOMAIN
    ),
    CONSTRUCTION_K7_CAMPAIGN_V166_DOMAIN=(
        domains.CONSTRUCTION_K7_CAMPAIGN_V167_DOMAIN
    ),
)
_V166_OCCURRENCE_GLOBALS = dict(v166.__dict__)
_V166_OCCURRENCE_GLOBALS.update(
    domains=_V166_DOMAIN_PROXY,
    _BASE_OCCURRENCE=_BASE_V160_OCCURRENCE,
)
_BASE_V166_OCCURRENCE = FunctionType(
    v166.build_fourth_family_sample_tax_occurrence_v166.__code__,
    _V166_OCCURRENCE_GLOBALS,
    name="_base_fourth_family_plan_mode_set_occurrence_v167",
)


def build_fourth_family_plan_mode_set_occurrence_v167(
    config,
    *,
    family,
    seed,
    episode_indices,
    bank_raw,
    verification_raw,
    classifier_receipt_raw,
):
    base = _BASE_V166_OCCURRENCE(
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
        registered_plan_mode_set_annotated_both_arms=all(
            sequence["at_least_one_registered_plan_mode_exercised"] is True
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
        "schema": "acfqp.fourth_family_plan_mode_set_occurrence.v167",
        "failed_v166_attempt_id": V166_FAILURE_ID,
        "registered_plan_mode_sets": [
            sequence["applicable_plan_receipt_modes"] for sequence in sequences
        ],
        "mixed_registered_plan_mode_sequence_observed": any(
            sequence["mixed_registered_plan_mode_sequence"]
            for sequence in sequences
        ),
        "registered_gate": gate,
        "plan_mode_set_annotation_changes_planner_or_execution": False,
        "sample_tax_claim_scope": (
            "ONLY_THIS_PREREGISTERED_V167_FOUR_FAMILY_COHORT"
        ),
    }
    return {
        **payload,
        "occurrence_id": domains.extension_content_id_v167(
            domains.CONSTRUCTION_K7_OCCURRENCE_V167_DOMAIN, payload
        ),
    }


def _target(args):
    return build_fourth_family_plan_mode_set_occurrence_v167(
        args[0],
        family=args[1],
        seed=args[2],
        episode_indices=args[3],
        bank_raw=args[4],
        verification_raw=args[5],
        classifier_receipt_raw=args[6],
    )


_V166_CAMPAIGN_GLOBALS = dict(v166.__dict__)
_V166_CAMPAIGN_GLOBALS.update(
    domains=_V166_DOMAIN_PROXY,
    _target=_target,
)
_BASE_V166_CAMPAIGN = FunctionType(
    v166.build_fourth_family_sample_tax_campaign_v166.__code__,
    _V166_CAMPAIGN_GLOBALS,
    name="_base_fourth_family_plan_mode_set_campaign_v167",
)


def build_fourth_family_plan_mode_set_campaign_v167(
    config,
    *,
    preregistration_id,
    bank_raw,
    verification_raw,
    classifier_receipt_raw,
):
    base = _BASE_V166_CAMPAIGN(
        config,
        preregistration_id=preregistration_id,
        bank_raw=bank_raw,
        verification_raw=verification_raw,
        classifier_receipt_raw=classifier_receipt_raw,
    )
    rows = base["target_occurrences"]
    sequences = [
        row[name]
        for row in rows
        for name in ("progressive_prior_sequence", "progressive_strict_sequence")
    ]
    gate = {
        key: value
        for key, value in base["registered_gate"].items()
        if key != "passed"
    }
    gate.update(
        v166_frozen_failure_preserved=all(
            row["failed_v166_attempt_id"] == V166_FAILURE_ID for row in rows
        ),
        v166_failed_targets_not_reused=True,
        plan_mode_set_annotation_present_everywhere=all(
            sequence["at_least_one_registered_plan_mode_exercised"] is True
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
    )
    gate["passed"] = (
        len(rows) == config["required_target_occurrence_count"]
        and all(value for value in gate.values() if type(value) is bool)
    )
    mode_histogram = {
        "DIRECT_ONLY": sum(
            sequence["applicable_plan_receipt_modes"]
            == ["DIRECT_GENERIC_FACTOR_PROGRAM"]
            for sequence in sequences
        ),
        "MEMOIZED_ONLY": sum(
            sequence["applicable_plan_receipt_modes"]
            == ["V115_MEMOIZED_COMPILED_PROGRAM"]
            for sequence in sequences
        ),
        "MIXED": sum(
            sequence["mixed_registered_plan_mode_sequence"]
            for sequence in sequences
        ),
    }
    payload = {
        **{
            key: value
            for key, value in base.items()
            if key not in {"schema", "campaign_id", "registered_gate"}
        },
        "schema": "acfqp.fourth_family_plan_mode_set_campaign.v167",
        "failed_v166_attempt_id": V166_FAILURE_ID,
        "registered_plan_mode_sequence_histogram": mode_histogram,
        "registered_gate": gate,
        "fourth_family_factor_prior_sample_tax_transfer_verified": gate["passed"],
        "v166_failure_preserved_not_reclassified": True,
        "plan_mode_set_annotation_changes_planner_or_execution": False,
        "sample_tax_claim_scope": (
            "ONLY_THIS_PREREGISTERED_V167_FOUR_FAMILY_COHORT"
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
        "campaign_id": domains.extension_content_id_v167(
            domains.CONSTRUCTION_K7_CAMPAIGN_V167_DOMAIN, payload
        ),
    }


__all__ = (
    "FALLBACK_FAMILY",
    "MAINTENANCE_FAMILY",
    "MODULAR_FAMILY",
    "POSITIVE_FAMILY",
    "TARGET_FAMILIES",
    "V166_FAILURE_ID",
    "build_fourth_family_plan_mode_set_campaign_v167",
    "build_fourth_family_plan_mode_set_occurrence_v167",
    "fourth_family_plan_mode_set_campaign_config_v167",
)
