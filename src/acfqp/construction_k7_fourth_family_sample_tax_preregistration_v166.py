"""Outcome-free preregistration for the V166 fourth-family transfer."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v166 as domains
from acfqp.fourth_family_sample_tax_transfer_campaign_core_v166 import (
    FALLBACK_FAMILY,
    MAINTENANCE_FAMILY,
    MODULAR_FAMILY,
    POSITIVE_FAMILY,
    TARGET_FAMILIES,
    fourth_family_sample_tax_transfer_campaign_config_v166,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


IMPLEMENTATION_COMMITS = ("0643ce3", "9fee213", "3afb60b")
TARGET_OCCURRENCES = (
    (POSITIVE_FAMILY, 1_048_711),
    (POSITIVE_FAMILY, 1_048_712),
    (FALLBACK_FAMILY, 1_048_721),
    (FALLBACK_FAMILY, 1_048_722),
    (MODULAR_FAMILY, 1_048_731),
    (MODULAR_FAMILY, 1_048_732),
    (MAINTENANCE_FAMILY, 1_048_741),
    (MAINTENANCE_FAMILY, 1_048_742),
)
TARGET_EPISODE_INDICES = (941, 942, 943, 944)
TARGET_WORKER_COUNT = 2
REQUIRED_TARGET_OCCURRENCE_COUNT = 8
V164_CAMPAIGN_ID = "108bc4cf4f61123c6da7812ae76a48c21027a3b5e32e80005952a93b2ab8da1c"
V164_CAMPAIGN_BYTE_COUNT = 33_323_896
V164_CAMPAIGN_SHA256 = "d964f250d8d6e0587cb80a1df50515ae9b74c319b0a4f5f24aee3cae262aa9f5"
V164_VERIFICATION_ID = (
    "1095eec978a045ac3fec2ef0848927ecf7ce3d290d68415656b28fe34b3f298f"
)
V164_VERIFICATION_BYTE_COUNT = 41_990
V164_VERIFICATION_SHA256 = (
    "91c6939851c37de8094be13bf113a17aef51abfc8379853af1f509559ea03be8"
)
V165_AUDIT_ID = "8de483f4f827caddf96dd367b470aba6b8fef409f3cc060c4f3308fd592cbdeb"
V165_AUDIT_BYTE_COUNT = 126_086
V165_AUDIT_SHA256 = "ebc57797a7b516d10d8a7a2d641b84a6d17621d47554c958235a1ec5981b8200"
V165_VERIFICATION_ID = (
    "d9aab6590d650f534edf19b7f87fd51045cd0d07cdf9d528f9873de3421e6390"
)
V165_VERIFICATION_BYTE_COUNT = 1_204
V165_VERIFICATION_SHA256 = (
    "f1c2a75cd081550b9751b4d30e9b78eb07938741f69fd48df06f8a30268fffcd"
)
PREREGISTRATION_ID = (
    "043a502c5f6f7da983ce1859edace7a74aca28645b688362bcdb2760620337c8"
)
EXPECTED_CANONICAL_BYTE_COUNT = 4_681
EXPECTED_CANONICAL_SHA256 = (
    "7ef9a7141c6b181d5cbc14a6174a5d273b04f8260a586d3c9e63f35728d3da6e"
)
SOURCE_ROOT = Path(__file__).resolve().parents[2]
FROZEN_SOURCE_FACTS = (
    (
        "src/acfqp/fourth_family_sample_tax_transfer_campaign_core_v166.py",
        14_682,
        "888ff2b6b0594b044c06b46f58d6357f23e0646dc1a3431cf92e2228c713c411",
    ),
    (
        "src/acfqp/construction_k7_domain_registry_extension_v166.py",
        1_495,
        "7ebc7926ba8adcdef497bff8578f7d02800f1fdea01a8027901049b7c728eb0d",
    ),
    (
        "src/acfqp/certified_paid_path_switch_acquisition_operator_v162.py",
        12_523,
        "da2fb40bd62af0952b87e2e8256b5e3e92c3d7f486751143f6d6fbe7d216e06a",
    ),
    (
        "src/acfqp/generic_maintenance_cascade_adapter_v144.py",
        4_425,
        "fe895b058ffc038fb2f529dd41f5a8e10eb57d3e49ecf40d3be7ecd12dcb7b41",
    ),
    (
        "src/acfqp/domains/stochastic_maintenance_cascade.py",
        9_036,
        "70f82715c16a4dd0daabefcca56ea7e50285166115bd3d6f4b9f27e9f917bf2a",
    ),
)


class ConstructionK7FourthFamilySampleTaxPreregistrationV166Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7FourthFamilySampleTaxPreregistrationV166Error(message)


def campaign_config_v166():
    config = fourth_family_sample_tax_transfer_campaign_config_v166()
    config.update(
        target_occurrences=[
            {"family": family, "seed": seed}
            for family, seed in TARGET_OCCURRENCES
        ],
        target_episode_indices=TARGET_EPISODE_INDICES,
        target_worker_count=TARGET_WORKER_COUNT,
        required_target_occurrence_count=REQUIRED_TARGET_OCCURRENCE_COUNT,
    )
    return config


def _frozen_predecessor(name, *, count, digest, key, identity):
    raw = (SOURCE_ROOT / ".tmp/exact-freeze" / name).read_bytes()
    document = loads_canonical_json(raw)
    if not (
        canonical_json_bytes(document) == raw
        and len(raw) == count
        and hashlib.sha256(raw).hexdigest() == digest
        and document[key] == identity
    ):
        _fail("V166 frozen predecessor changed")
    return document


def _document():
    source_facts = []
    for path, byte_count, digest in FROZEN_SOURCE_FACTS:
        raw = (SOURCE_ROOT / path).read_bytes()
        if len(raw) != byte_count or hashlib.sha256(raw).hexdigest() != digest:
            _fail("V166 implementation changed before target outcomes")
        source_facts.append(
            {"relative_path": path, "byte_count": byte_count, "sha256": digest}
        )
    v164_campaign = _frozen_predecessor(
        "v164_sample_tax_replication_campaign.json",
        count=V164_CAMPAIGN_BYTE_COUNT,
        digest=V164_CAMPAIGN_SHA256,
        key="campaign_id",
        identity=V164_CAMPAIGN_ID,
    )
    v164_verification = _frozen_predecessor(
        "v164_sample_tax_replication_verification.json",
        count=V164_VERIFICATION_BYTE_COUNT,
        digest=V164_VERIFICATION_SHA256,
        key="verification_id",
        identity=V164_VERIFICATION_ID,
    )
    v165_audit = _frozen_predecessor(
        "v165_paid_prefix_profitability_identifiability_audit.json",
        count=V165_AUDIT_BYTE_COUNT,
        digest=V165_AUDIT_SHA256,
        key="audit_id",
        identity=V165_AUDIT_ID,
    )
    v165_verification = _frozen_predecessor(
        "v165_paid_prefix_profitability_identifiability_verification.json",
        count=V165_VERIFICATION_BYTE_COUNT,
        digest=V165_VERIFICATION_SHA256,
        key="verification_id",
        identity=V165_VERIFICATION_ID,
    )
    if not (
        v164_campaign["registered_gate"]["passed"] is True
        and v164_verification[
            "query_and_factor_prior_sample_tax_replication_independently_verified"
        ]
        is True
        and v165_audit["registered_paid_prefix_profitability_is_identifiable"]
        is False
        and v165_audit["profitability_classifier_issued"] is False
        and v165_verification[
            "registered_paid_prefix_nonidentifiability_independently_verified"
        ]
        is True
    ):
        _fail("V166 predecessor semantics changed")
    config = campaign_config_v166()
    payload = {
        "schema": "acfqp.fourth_family_sample_tax_preregistration.v166",
        "implementation_commits": list(IMPLEMENTATION_COMMITS),
        "frozen_implementation_source_facts": source_facts,
        "frozen_v164_campaign": {
            "campaign_id": V164_CAMPAIGN_ID,
            "byte_count": V164_CAMPAIGN_BYTE_COUNT,
            "sha256": V164_CAMPAIGN_SHA256,
            "query_policy_labels_avoided": 88,
            "factor_prior_labels_avoided": 68,
        },
        "frozen_v164_independent_verification": {
            "verification_id": V164_VERIFICATION_ID,
            "byte_count": V164_VERIFICATION_BYTE_COUNT,
            "sha256": V164_VERIFICATION_SHA256,
            "producer_free_verified": True,
        },
        "frozen_v165_identifiability_audit": {
            "audit_id": V165_AUDIT_ID,
            "byte_count": V165_AUDIT_BYTE_COUNT,
            "sha256": V165_AUDIT_SHA256,
            "mixed_profitability_signature_count": 1,
            "profitability_classifier_issued": False,
        },
        "frozen_v165_independent_verification": {
            "verification_id": V165_VERIFICATION_ID,
            "byte_count": V165_VERIFICATION_BYTE_COUNT,
            "sha256": V165_VERIFICATION_SHA256,
            "producer_free_verified": True,
        },
        "target_occurrences": [
            {"family": family, "seed": seed}
            for family, seed in TARGET_OCCURRENCES
        ],
        "target_episode_indices": list(TARGET_EPISODE_INDICES),
        "target_worker_count": TARGET_WORKER_COUNT,
        "required_target_occurrence_count": REQUIRED_TARGET_OCCURRENCE_COUNT,
        "maximum_acquisition_labels_by_family": {
            family: config["families"][family]["maximum_acquisition_labels"]
            for family in TARGET_FAMILIES
        },
        "registered_gate": {
            "fresh_target_identities_fixed_before_target_outcomes": True,
            "exactly_two_occurrences_from_each_of_four_families_required": True,
            "maintenance_family_is_new_to_v163_v164_cohorts": True,
            "v164_replication_and_v165_nonidentifiability_boundary_frozen": True,
            "profitability_classifier_must_not_be_issued": True,
            "query_policy_noninferior_everywhere_required": True,
            "strict_query_policy_reduction_not_required": True,
            "every_exact_fallback_zero_regression_required": True,
            "factor_prior_noninferior_everywhere_required": True,
            "factor_prior_strict_aggregate_reduction_required": True,
            "factor_prior_strict_new_family_reduction_required": True,
            "sample_historical_annotation_execution_derivation_planning_axes_separate": True,
            "both_arm_receding_planning_and_certificate_failure_local_recovery_required": True,
            "all_executed_actions_require_v109_receipts": True,
            "strict_ood_no_transfer_required": True,
            "producer_free_verification_required": True,
            "frozen_two_worker_resource_schedule": True,
        },
        "claim_boundary": {
            "target_outcomes_accessed": False,
            "fourth_family_sample_tax_transfer_observed": False,
            "profitability_classifier_issued": False,
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
        "preregistration_id": domains.extension_content_id_v166(
            domains.CONSTRUCTION_K7_TARGET_PREREGISTRATION_V166_DOMAIN, payload
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class FourthFamilySampleTaxPreregistrationV166:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


def freeze_fourth_family_sample_tax_preregistration_v166():
    document = _document()
    raw = canonical_json_bytes(document)
    if PREREGISTRATION_ID != "0" * 64 and not (
        document["preregistration_id"] == PREREGISTRATION_ID
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    ):
        _fail("V166 frozen target preregistration changed")
    return FourthFamilySampleTaxPreregistrationV166(
        _ISSUER, raw, document["preregistration_id"]
    )


__all__ = (
    "PREREGISTRATION_ID",
    "campaign_config_v166",
    "freeze_fourth_family_sample_tax_preregistration_v166",
)
