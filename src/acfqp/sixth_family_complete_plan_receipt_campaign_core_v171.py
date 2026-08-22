"""Fresh sixth-family campaign with complete typed plan receipts and joins."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
import copy
import hashlib
from types import FunctionType, SimpleNamespace

from acfqp import applicable_plan_receipt_set_sequence_v168 as sequence_v168
from acfqp import construction_k7_domain_registry_extension_v171 as domains
from acfqp import fifth_family_total_plan_receipt_set_campaign_core_v168 as v168
from acfqp import fourth_family_sample_tax_transfer_campaign_core_v166 as v166
from acfqp.complete_plan_receipt_taxonomy_sequence_v171 import (
    annotate_complete_plan_receipt_taxonomy_sequence_v171,
)
from acfqp.generic_reservoir_dispatch_adapter_v171 import (
    FAMILY as RESERVOIR_DISPATCH_FAMILY,
    build_reservoir_dispatch_adapter_v171,
    reservoir_dispatch_config_v171,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


TARGET_FAMILIES = (*v168.TARGET_FAMILIES, RESERVOIR_DISPATCH_FAMILY)
V168_CAMPAIGN_ID = "447f04fb450a9b76083993593a66ef717431f0b814212927ff2adfa1e27e4dce"
V168_CAMPAIGN_BYTE_COUNT = 25_586_483
V168_CAMPAIGN_SHA256 = "e0cd4d36fb72bf79519878e1a368aeecf128cd91c4571bf0071d68af2760dfa5"
V170_AUDIT_ID = "0372043e8d6a3277070488777e3f0dc5f33702abb2b72a8fcabc12a60dd35944"
V170_AUDIT_BYTE_COUNT = 1_193_174
V170_AUDIT_SHA256 = "24e90f4af2da248de54c233931f7d6aefcc89eeb3b1c3b6a8ac3fe5cd81599a2"
V170_VERIFICATION_ID = "f9b7570d565cb160d80aafadd9d4bcf49abdcb7879d782c597fd9f955cfa4217"
V170_VERIFICATION_BYTE_COUNT = 1_537
V170_VERIFICATION_SHA256 = "a4bcb3aff4f465a66c6dabd06c6427871d6418e027258d6fe9bde0da2a0541c3"


def sixth_family_complete_plan_receipt_campaign_config_v171():
    config = v168.fifth_family_total_plan_receipt_set_campaign_config_v168()
    reservoir = reservoir_dispatch_config_v171()
    config["families"][RESERVOIR_DISPATCH_FAMILY] = copy.deepcopy(
        reservoir["families"][RESERVOIR_DISPATCH_FAMILY]
    )
    config["families"][RESERVOIR_DISPATCH_FAMILY][
        "maximum_acquisition_labels"
    ] = 2_048
    return config


_DOMAIN_PROXY = SimpleNamespace(
    extension_content_id_v168=domains.extension_content_id_v171,
    CONSTRUCTION_K7_SEQUENCE_V168_DOMAIN=domains.CONSTRUCTION_K7_SEQUENCE_V171_DOMAIN,
)
_ANNOTATOR_GLOBALS = dict(sequence_v168.__dict__)
_ANNOTATOR_GLOBALS["domains"] = _DOMAIN_PROXY
_ANNOTATE_V168_SHAPE_V171 = FunctionType(
    sequence_v168.annotate_applicable_plan_receipt_set_sequence_v168.__code__,
    _ANNOTATOR_GLOBALS,
    name="_annotate_v168_shape_v171",
)

_V160_DOMAIN_PROXY = SimpleNamespace(
    extension_content_id_v160=domains.extension_content_id_v171,
    CONSTRUCTION_K7_OCCURRENCE_V160_DOMAIN=domains.CONSTRUCTION_K7_OCCURRENCE_V171_DOMAIN,
)
_V160_GLOBALS = dict(v168._BASE_V160_OCCURRENCE_V168.__globals__)  # noqa: SLF001
_V160_GLOBALS.update(
    domains=_V160_DOMAIN_PROXY,
    _BUILDERS={
        **_V160_GLOBALS["_BUILDERS"],
        RESERVOIR_DISPATCH_FAMILY: build_reservoir_dispatch_adapter_v171,
    },
    annotate_applicable_plan_mode_sequence_v157=_ANNOTATE_V168_SHAPE_V171,
)
_BASE_V160_OCCURRENCE = FunctionType(
    v168._BASE_V160_OCCURRENCE_V168.__code__,  # noqa: SLF001
    _V160_GLOBALS,
    name="_base_sixth_family_v160_occurrence_v171",
)

_V166_DOMAIN_PROXY = SimpleNamespace(
    extension_content_id_v166=domains.extension_content_id_v171,
    CONSTRUCTION_K7_OCCURRENCE_V166_DOMAIN=domains.CONSTRUCTION_K7_OCCURRENCE_V171_DOMAIN,
    CONSTRUCTION_K7_CAMPAIGN_V166_DOMAIN=domains.CONSTRUCTION_K7_CAMPAIGN_V171_DOMAIN,
)
_V166_GLOBALS = dict(v166.__dict__)
_V166_GLOBALS.update(
    domains=_V166_DOMAIN_PROXY,
    _BASE_OCCURRENCE=_BASE_V160_OCCURRENCE,
    TARGET_FAMILIES=TARGET_FAMILIES,
)
_BASE_V166_OCCURRENCE = FunctionType(
    v166.build_fourth_family_sample_tax_occurrence_v166.__code__,
    _V166_GLOBALS,
    name="_base_sixth_family_v166_occurrence_v171",
)

_V168_DOMAIN_PROXY = SimpleNamespace(
    extension_content_id_v168=domains.extension_content_id_v171,
    CONSTRUCTION_K7_OCCURRENCE_V168_DOMAIN=domains.CONSTRUCTION_K7_OCCURRENCE_V171_DOMAIN,
)
_V168_GLOBALS = dict(v168.__dict__)
_V168_GLOBALS.update(
    domains=_V168_DOMAIN_PROXY,
    _BASE_V166_OCCURRENCE_V168=_BASE_V166_OCCURRENCE,
    TARGET_FAMILIES=TARGET_FAMILIES,
)
_BASE_V168_OCCURRENCE = FunctionType(
    v168.build_fifth_family_total_plan_receipt_set_occurrence_v168.__code__,
    _V168_GLOBALS,
    name="_base_sixth_family_v168_occurrence_v171",
)


def build_sixth_family_complete_plan_receipt_occurrence_v171(
    config,
    *,
    family,
    seed,
    episode_indices,
    bank_raw,
    verification_raw,
    classifier_receipt_raw,
):
    if family != RESERVOIR_DISPATCH_FAMILY:
        raise ValueError("V171 target family is not the preregistered sixth family")
    base = _BASE_V168_OCCURRENCE(
        config,
        family=family,
        seed=seed,
        episode_indices=episode_indices,
        bank_raw=bank_raw,
        verification_raw=verification_raw,
        classifier_receipt_raw=classifier_receipt_raw,
    )
    prior = annotate_complete_plan_receipt_taxonomy_sequence_v171(
        base["progressive_prior_sequence"]
    )
    strict = annotate_complete_plan_receipt_taxonomy_sequence_v171(
        base["progressive_strict_sequence"]
    )
    sequences = (prior, strict)
    gate = {
        key: value
        for key, value in base["registered_gate"].items()
        if key != "passed"
    }
    gate.update(
        complete_v170_taxonomy_applied_both_arms=all(
            sequence["complete_four_source_taxonomy_applied"] is True
            for sequence in sequences
        ),
        every_abstract_plan_instance_typed=all(
            sequence["every_abstract_plan_instance_typed"] is True
            and sequence["untyped_abstract_plan_receipt_count"] == 0
            for sequence in sequences
        ),
        every_executed_action_exactly_joined=all(
            sequence["every_executed_action_exactly_joined"] is True
            and sequence["unjoined_executed_action_count"] == 0
            for sequence in sequences
        ),
        taxonomy_does_not_change_planning_or_execution=all(
            sequence["taxonomy_changes_planning_or_execution"] is False
            for sequence in sequences
        ),
        taxonomy_is_not_model_or_safety_authority=all(
            sequence["taxonomy_is_model_or_safety_authority"] is False
            for sequence in sequences
        ),
        factor_prior_strictly_reduces_sixth_family_acquisition_labels=(
            base["factor_prior_sample_reduction_within_progressive_policy"] > 0
        ),
        query_policy_has_zero_regression=(
            base["query_policy_sample_reduction_vs_legacy_path_first"] >= 0
        ),
    )
    gate["passed"] = all(value for value in gate.values() if type(value) is bool)
    payload = {
        **{
            key: value
            for key, value in base.items()
            if key
            not in {
                "schema",
                "occurrence_id",
                "progressive_prior_sequence",
                "progressive_strict_sequence",
                "registered_gate",
                "sample_tax_claim_scope",
            }
        },
        "schema": "acfqp.sixth_family_complete_plan_receipt_occurrence.v171",
        "progressive_prior_sequence": prior,
        "progressive_strict_sequence": strict,
        "typed_plan_source_histogram": {
            source: sum(
                sequence["typed_plan_source_histogram"][source]
                for sequence in sequences
            )
            for source in prior["typed_plan_source_histogram"]
        },
        "typed_plan_receipt_count": sum(
            sequence["typed_plan_receipt_count"] for sequence in sequences
        ),
        "execution_join_receipt_count": sum(
            sequence["execution_join_receipt_count"] for sequence in sequences
        ),
        "registered_gate": gate,
        "sample_tax_claim_scope": "ONLY_THIS_PREREGISTERED_V171_SIXTH_FAMILY_COHORT",
        "v170_taxonomy_annotation_changes_planning_or_execution": False,
    }
    return {
        **payload,
        "occurrence_id": domains.extension_content_id_v171(
            domains.CONSTRUCTION_K7_OCCURRENCE_V171_DOMAIN, payload
        ),
    }


def _target_v171(args):
    return build_sixth_family_complete_plan_receipt_occurrence_v171(
        args[0],
        family=args[1],
        seed=args[2],
        episode_indices=args[3],
        bank_raw=args[4],
        verification_raw=args[5],
        classifier_receipt_raw=args[6],
    )


def _frozen(raw, *, count, digest, identity_key, identity, name):
    document = loads_canonical_json(raw)
    if not (
        canonical_json_bytes(document) == raw
        and len(raw) == count
        and hashlib.sha256(raw).hexdigest() == digest
        and document.get(identity_key) == identity
    ):
        raise ValueError(f"V171 frozen predecessor changed: {name}")
    return document


def build_sixth_family_complete_plan_receipt_campaign_v171(
    config,
    *,
    preregistration_id,
    bank_raw,
    verification_raw,
    classifier_receipt_raw,
    v168_campaign_raw,
    v170_audit_raw,
    v170_verification_raw,
):
    v168_campaign = _frozen(
        v168_campaign_raw,
        count=V168_CAMPAIGN_BYTE_COUNT,
        digest=V168_CAMPAIGN_SHA256,
        identity_key="campaign_id",
        identity=V168_CAMPAIGN_ID,
        name="V168 campaign",
    )
    v170_audit = _frozen(
        v170_audit_raw,
        count=V170_AUDIT_BYTE_COUNT,
        digest=V170_AUDIT_SHA256,
        identity_key="audit_id",
        identity=V170_AUDIT_ID,
        name="V170 audit",
    )
    v170_verification = _frozen(
        v170_verification_raw,
        count=V170_VERIFICATION_BYTE_COUNT,
        digest=V170_VERIFICATION_SHA256,
        identity_key="verification_id",
        identity=V170_VERIFICATION_ID,
        name="V170 verification",
    )
    if not (
        v168_campaign["registered_gate"]["passed"] is True
        and v170_audit["registered_gate"]["passed"] is True
        and v170_verification["producer_free_every_plan_instance_reconstructed"]
        is True
        and v170_verification["producer_free_every_execution_join_reconstructed"]
        is True
    ):
        raise ValueError("V171 predecessor claim boundary changed")
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
        rows = [_target_v171(row) for row in args]
    else:
        with ProcessPoolExecutor(max_workers=config["target_worker_count"]) as executor:
            rows = list(executor.map(_target_v171, args))
    numeric = [
        key for key, value in rows[0]["accounting"].items() if type(value) is int
    ]
    accounting = {
        key: sum(row["accounting"][key] for row in rows) for key in numeric
    }
    accounting.update(
        total_query_policy_labels_avoided_vs_exact_path_first=sum(
            row["query_policy_sample_reduction_vs_legacy_path_first"] for row in rows
        ),
        total_factor_prior_labels_avoided_within_same_query_policy=sum(
            row["factor_prior_sample_reduction_within_progressive_policy"]
            for row in rows
        ),
        typed_plan_receipt_count=sum(
            row["typed_plan_receipt_count"] for row in rows
        ),
        execution_join_receipt_count=sum(
            row["execution_join_receipt_count"] for row in rows
        ),
        sample_labels_execution_steps_derivation_and_planning_compute_separate=True,
        scalar_cost_aggregation_performed=False,
    )
    histogram = {
        source: sum(row["typed_plan_source_histogram"][source] for row in rows)
        for source in rows[0]["typed_plan_source_histogram"]
    }
    gate = {
        "required_fresh_reservoir_occurrence_count": config[
            "required_target_occurrence_count"
        ],
        "passed_fresh_reservoir_occurrence_count": sum(
            row["registered_gate"]["passed"] for row in rows
        ),
        "every_target_is_fresh_reservoir_dispatch": all(
            row["target_family"] == RESERVOIR_DISPATCH_FAMILY for row in rows
        ),
        "v168_and_v170_frozen_predecessors_preserved": True,
        "every_abstract_plan_instance_typed": all(
            row["registered_gate"]["every_abstract_plan_instance_typed"]
            for row in rows
        ),
        "every_executed_action_exactly_joined": all(
            row["registered_gate"]["every_executed_action_exactly_joined"]
            for row in rows
        ),
        "zero_unknown_plan_sources": all(
            row["progressive_prior_sequence"]["untyped_abstract_plan_receipt_count"]
            == row["progressive_strict_sequence"][
                "untyped_abstract_plan_receipt_count"
            ]
            == 0
            for row in rows
        ),
        "sixth_family_factor_prior_strictly_reduces_labels": all(
            row["factor_prior_sample_reduction_within_progressive_policy"] > 0
            for row in rows
        ),
        "sixth_family_query_policy_noninferior": all(
            row["query_policy_sample_reduction_vs_legacy_path_first"] >= 0
            for row in rows
        ),
        "both_arm_receding_plans_succeed": all(
            row["registered_gate"]["both_arm_receding_episodes_succeed"]
            for row in rows
        ),
        "certificate_failure_only_local_ground_distinctions": all(
            row["registered_gate"][
                "certificate_failure_only_local_ground_distinctions"
            ]
            for row in rows
        ),
        "taxonomy_does_not_change_planning_or_execution": all(
            row["v170_taxonomy_annotation_changes_planning_or_execution"] is False
            for row in rows
        ),
    }
    gate["passed"] = (
        len(rows) == config["required_target_occurrence_count"]
        and gate["passed_fresh_reservoir_occurrence_count"] == len(rows)
        and all(value for value in gate.values() if type(value) is bool)
    )
    payload = {
        "schema": "acfqp.sixth_family_complete_plan_receipt_campaign.v171",
        "preregistration_id": preregistration_id,
        "frozen_v168_campaign_id": V168_CAMPAIGN_ID,
        "frozen_v170_taxonomy_audit_id": V170_AUDIT_ID,
        "frozen_v170_taxonomy_verification_id": V170_VERIFICATION_ID,
        "target_occurrences": rows,
        "target_occurrence_ids": [row["occurrence_id"] for row in rows],
        "fresh_reservoir_accounting": accounting,
        "typed_plan_source_histogram": histogram,
        "registered_gate": gate,
        "sixth_family_world_model_reuse_observed": gate["passed"],
        "sixth_family_factor_prior_sample_tax_reduction_observed": gate[
            "sixth_family_factor_prior_strictly_reduces_labels"
        ],
        "sample_tax_claim_scope": "ONLY_THIS_PREREGISTERED_V171_SIXTH_FAMILY_COHORT",
        "taxonomy_changes_planning_or_execution": False,
        "taxonomy_is_model_or_safety_authority": False,
        "query_local_exact_overlay_remains_only_safety_authority": True,
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
        "campaign_id": domains.extension_content_id_v171(
            domains.CONSTRUCTION_K7_CAMPAIGN_V171_DOMAIN, payload
        ),
    }


__all__ = (
    "RESERVOIR_DISPATCH_FAMILY",
    "build_sixth_family_complete_plan_receipt_campaign_v171",
    "build_sixth_family_complete_plan_receipt_occurrence_v171",
    "sixth_family_complete_plan_receipt_campaign_config_v171",
)
