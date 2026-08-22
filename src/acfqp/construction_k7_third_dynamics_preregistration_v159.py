"""Outcome-free preregistration for the V159 third-dynamics campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v159 as domains
from acfqp.construction_k7_joint_factor_query_classifier_receipt_freeze_v159 import (
    CLASSIFIER_RECEIPT_ID,
    EXPECTED_CANONICAL_BYTE_COUNT as CLASSIFIER_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256 as CLASSIFIER_SHA256,
    verify_frozen_joint_factor_query_classifier_receipt_v159,
)
from acfqp.generic_modular_routing_adapter_v128 import FAMILY
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp.third_dynamics_joint_factor_query_campaign_core_v159 import (
    third_dynamics_campaign_config_v159,
)


IMPLEMENTATION_COMMITS = (
    "9f6f528",
    "cb45e0b",
    "25ce491",
)
TARGET_SEEDS = (1_048_121, 1_048_122, 1_048_123, 1_048_124)
TARGET_EPISODE_INDICES = (821, 822, 823, 824)
TARGET_WORKER_COUNT = 2
REQUIRED_TARGET_OCCURRENCE_COUNT = 4
MAXIMUM_ACQUISITION_LABELS = 2_048
MAXIMUM_TARGET_FACTORIZATION_AUDIT_LABELS_PER_OCCURRENCE = 1
PREREGISTRATION_ID = "c4d0d30374737df6ee38cfcd7e3ee9ba2f642007f753a9a43d8440154a36d413"
EXPECTED_CANONICAL_BYTE_COUNT = 13_314
EXPECTED_CANONICAL_SHA256 = "d1b705eab085c549a616d9811f6cd3d61d958f6390cc1feff9cc2eb64cd776bb"
SOURCE_ROOT = Path(__file__).resolve().parents[2]
FROZEN_SOURCE_FACTS = (
    (
        "src/acfqp/joint_factor_query_acquisition_operator_v159.py",
        4_512,
        "ed9e6c1f65d04581209208a2364c7b3bf0491c6a5b2718a39114eec5b7a1e715",
    ),
    (
        "src/acfqp/third_dynamics_joint_factor_query_campaign_core_v159.py",
        18_073,
        "97de63e20456f7512dce3fc33fc54b136487e6dca5ff20bf53a14b9226c48920",
    ),
    (
        "src/acfqp/construction_k7_joint_factor_query_classifier_receipt_freeze_v159.py",
        2_743,
        "cee5661e251800284578ce5e64e12bfbece0a6fd4c465ecf9a48c4126f46a1e6",
    ),
    (
        "src/acfqp/joint_factor_query_classifier_core_v159.py",
        7_626,
        "55e76289310caadb5e04ad40cc7a046dc36c8cc4cede01338384300b3b46487b",
    ),
)


class ConstructionK7ThirdDynamicsPreregistrationV159Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7ThirdDynamicsPreregistrationV159Error(message)


def campaign_config_v159():
    config = third_dynamics_campaign_config_v159()
    config["families"][FAMILY][
        "maximum_acquisition_labels"
    ] = MAXIMUM_ACQUISITION_LABELS
    config.update(
        target_occurrences=[{"family": FAMILY, "seed": seed} for seed in TARGET_SEEDS],
        target_episode_indices=TARGET_EPISODE_INDICES,
        target_worker_count=TARGET_WORKER_COUNT,
        required_target_occurrence_count=REQUIRED_TARGET_OCCURRENCE_COUNT,
    )
    return config


def _document(classifier_receipt_raw: bytes):
    classifier = verify_frozen_joint_factor_query_classifier_receipt_v159(
        classifier_receipt_raw
    )
    if not (
        len(classifier_receipt_raw) == CLASSIFIER_BYTE_COUNT
        and hashlib.sha256(classifier_receipt_raw).hexdigest() == CLASSIFIER_SHA256
        and classifier["classifier_receipt_id"] == CLASSIFIER_RECEIPT_ID
    ):
        _fail("V159 frozen classifier receipt changed")
    source_facts = []
    for path, byte_count, digest in FROZEN_SOURCE_FACTS:
        raw = (SOURCE_ROOT / path).read_bytes()
        if len(raw) != byte_count or hashlib.sha256(raw).hexdigest() != digest:
            _fail("V159 target implementation changed before outcomes")
        source_facts.append(
            {"relative_path": path, "byte_count": byte_count, "sha256": digest}
        )
    payload = {
        "schema": "acfqp.third_dynamics_preregistration.v159",
        "implementation_commits": list(IMPLEMENTATION_COMMITS),
        "frozen_implementation_source_facts": source_facts,
        "frozen_classifier_receipt": classifier,
        "target_occurrences": [
            {"family": FAMILY, "seed": seed} for seed in TARGET_SEEDS
        ],
        "target_episode_indices": list(TARGET_EPISODE_INDICES),
        "target_worker_count": TARGET_WORKER_COUNT,
        "required_target_occurrence_count": REQUIRED_TARGET_OCCURRENCE_COUNT,
        "maximum_acquisition_labels": MAXIMUM_ACQUISITION_LABELS,
        "maximum_target_factorization_audit_labels_per_occurrence": MAXIMUM_TARGET_FACTORIZATION_AUDIT_LABELS_PER_OCCURRENCE,
        "registered_gate": {
            "fresh_target_identities_fixed_before_target_outcomes": True,
            "third_genuinely_distinct_partial_stochastic_dynamics_required": True,
            "v158_metadata_classifier_false_positive_repair_required": True,
            "joint_factorization_labelled_query_policy_required": True,
            "paid_rows_plus_at_most_one_audit_label_must_corroborate_fallback": True,
            "query_policy_zero_acquisition_sample_regression_required": True,
            "factor_prior_noninferior_everywhere_and_positive_in_aggregate": True,
            "both_arm_receding_planning_and_certificate_failure_local_recovery_required": True,
            "direct_generic_plan_and_v109_execution_receipts_required": True,
            "strict_ood_no_transfer_required": True,
            "producer_free_verification_required": True,
            "frozen_two_worker_resource_schedule": True,
        },
        "claim_boundary": {
            "target_outcomes_accessed": False,
            "third_dynamics_transfer_observed": False,
            "query_policy_classifier_is_model_planning_or_certificate_authority": False,
            "complete_world_model_claimed": False,
            "arbitrary_unseen_domain_transfer_claimed": False,
            "official_execution_allowed": False,
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
            "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        },
    }
    return {
        **payload,
        "preregistration_id": domains.extension_content_id_v159(
            domains.CONSTRUCTION_K7_TARGET_PREREGISTRATION_V159_DOMAIN, payload
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class ThirdDynamicsPreregistrationV159:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


def freeze_third_dynamics_preregistration_v159(classifier_receipt_raw: bytes):
    document = _document(classifier_receipt_raw)
    raw = canonical_json_bytes(document)
    if PREREGISTRATION_ID != "0" * 64 and not (
        document["preregistration_id"] == PREREGISTRATION_ID
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    ):
        _fail("V159 frozen target preregistration changed")
    return ThirdDynamicsPreregistrationV159(
        _ISSUER, raw, document["preregistration_id"]
    )


__all__ = (
    "PREREGISTRATION_ID",
    "campaign_config_v159",
    "freeze_third_dynamics_preregistration_v159",
)
