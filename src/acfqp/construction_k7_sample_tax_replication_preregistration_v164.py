"""Outcome-free preregistration for the V164 sample-tax replication."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v164 as domains
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp.sample_tax_replication_campaign_core_v164 import (
    FALLBACK_FAMILY,
    MODULAR_FAMILY,
    POSITIVE_FAMILY,
    sample_tax_replication_campaign_config_v164,
)


IMPLEMENTATION_COMMITS = ("de12241", "e5d3f52", "ef969eb")
TARGET_OCCURRENCES = (
    *((POSITIVE_FAMILY, seed) for seed in range(1_048_601, 1_048_609)),
    (FALLBACK_FAMILY, 1_048_611),
    (FALLBACK_FAMILY, 1_048_612),
    (MODULAR_FAMILY, 1_048_621),
    (MODULAR_FAMILY, 1_048_622),
)
TARGET_EPISODE_INDICES = (921, 922, 923, 924)
TARGET_WORKER_COUNT = 2
REQUIRED_TARGET_OCCURRENCE_COUNT = 12
V163_CAMPAIGN_ID = "193323db43d5524e5bebe3a1713e946ab7dbb77cf79307c957a13cded0d9c219"
V163_CAMPAIGN_BYTE_COUNT = 31_528_790
V163_CAMPAIGN_SHA256 = (
    "9dab876ef04bd5b48698fdb9295aaf6efe1f6e3a51bd945fe84e449367aaa433"
)
V163_VERIFICATION_ID = (
    "5e856f8cab34726906f3e93924ea099d2027ee39aca0708efc5ebabec437975b"
)
V163_VERIFICATION_BYTE_COUNT = 28_544
V163_VERIFICATION_SHA256 = (
    "bd98840ef1a21d3897195e86093b0ed727acbb606dc544cd10df343d7dda002f"
)
PREREGISTRATION_ID = (
    "c4b822f5b57280eb63cd0affd15f0f38b7c74d52342f0270e282de3cced94424"
)
EXPECTED_CANONICAL_BYTE_COUNT = 3_944
EXPECTED_CANONICAL_SHA256 = (
    "267e0ff7ba31d780f21915d2df29f19f55910c74cf0c3263ea3196e363ee7d95"
)
SOURCE_ROOT = Path(__file__).resolve().parents[2]
FROZEN_SOURCE_FACTS = (
    (
        "src/acfqp/certified_paid_path_switch_acquisition_operator_v162.py",
        12_523,
        "da2fb40bd62af0952b87e2e8256b5e3e92c3d7f486751143f6d6fbe7d216e06a",
    ),
    (
        "src/acfqp/sample_tax_replication_campaign_core_v164.py",
        8_452,
        "d218fd891353da1a5b3ac1fbfb353b6571fa1eeda3105e8c9bafbb422f73d0ef",
    ),
    (
        "src/acfqp/construction_k7_domain_registry_extension_v164.py",
        1_441,
        "747ef2f60377e6e2c2e1521a8224b6fecd341268ff0cfdbacb30d6bcad1cdb5f",
    ),
)


class ConstructionK7SampleTaxReplicationPreregistrationV164Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7SampleTaxReplicationPreregistrationV164Error(message)


def campaign_config_v164():
    config = sample_tax_replication_campaign_config_v164()
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
        _fail("V164 frozen V163 predecessor changed")
    return document


def _document():
    source_facts = []
    for path, byte_count, digest in FROZEN_SOURCE_FACTS:
        raw = (SOURCE_ROOT / path).read_bytes()
        if len(raw) != byte_count or hashlib.sha256(raw).hexdigest() != digest:
            _fail("V164 implementation changed before outcomes")
        source_facts.append(
            {"relative_path": path, "byte_count": byte_count, "sha256": digest}
        )
    campaign = _frozen_predecessor(
        "v163_safe_paid_path_sample_tax_campaign.json",
        count=V163_CAMPAIGN_BYTE_COUNT,
        digest=V163_CAMPAIGN_SHA256,
        key="campaign_id",
        identity=V163_CAMPAIGN_ID,
    )
    verification = _frozen_predecessor(
        "v163_safe_paid_path_sample_tax_verification.json",
        count=V163_VERIFICATION_BYTE_COUNT,
        digest=V163_VERIFICATION_SHA256,
        key="verification_id",
        identity=V163_VERIFICATION_ID,
    )
    if not (
        campaign["registered_gate"]["passed"] is True
        and verification[
            "safe_query_and_factor_prior_sample_tax_evidence_independently_verified"
        ]
        is True
        and verification["query_policy_labels_avoided_vs_exact_path_first"] == 49
        and verification["factor_prior_labels_avoided_within_same_query_policy"]
        == 43
    ):
        _fail("V164 V163 evidence semantics changed")
    config = campaign_config_v164()
    payload = {
        "schema": "acfqp.sample_tax_replication_preregistration.v164",
        "implementation_commits": list(IMPLEMENTATION_COMMITS),
        "frozen_implementation_source_facts": source_facts,
        "frozen_v163_campaign": {
            "campaign_id": V163_CAMPAIGN_ID,
            "byte_count": V163_CAMPAIGN_BYTE_COUNT,
            "sha256": V163_CAMPAIGN_SHA256,
            "query_policy_labels_avoided": 49,
            "factor_prior_labels_avoided": 43,
        },
        "frozen_v163_independent_verification": {
            "verification_id": V163_VERIFICATION_ID,
            "byte_count": V163_VERIFICATION_BYTE_COUNT,
            "sha256": V163_VERIFICATION_SHA256,
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
            for family in (POSITIVE_FAMILY, FALLBACK_FAMILY, MODULAR_FAMILY)
        },
        "registered_gate": {
            "fresh_target_identities_fixed_before_target_outcomes": True,
            "v163_campaign_and_independent_verification_frozen": True,
            "positive_fallback_and_modular_cohorts_required": True,
            "at_least_one_certified_switch_required": True,
            "query_policy_noninferior_everywhere_required": True,
            "query_policy_strict_aggregate_sample_reduction_required": True,
            "every_exact_fallback_zero_regression_required": True,
            "factor_prior_noninferior_everywhere_required": True,
            "factor_prior_strict_aggregate_sample_reduction_required": True,
            "sample_execution_derivation_planning_axes_separate": True,
            "both_arm_receding_planning_and_certificate_failure_local_recovery_required": True,
            "all_executed_actions_require_v109_receipts": True,
            "strict_ood_no_transfer_required": True,
            "producer_free_verification_required": True,
            "frozen_two_worker_resource_schedule": True,
        },
        "claim_boundary": {
            "target_outcomes_accessed": False,
            "sample_tax_replication_observed": False,
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
        "preregistration_id": domains.extension_content_id_v164(
            domains.CONSTRUCTION_K7_TARGET_PREREGISTRATION_V164_DOMAIN, payload
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class SampleTaxReplicationPreregistrationV164:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


def freeze_sample_tax_replication_preregistration_v164():
    document = _document()
    raw = canonical_json_bytes(document)
    if PREREGISTRATION_ID != "0" * 64 and not (
        document["preregistration_id"] == PREREGISTRATION_ID
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    ):
        _fail("V164 frozen target preregistration changed")
    return SampleTaxReplicationPreregistrationV164(
        _ISSUER, raw, document["preregistration_id"]
    )


__all__ = (
    "PREREGISTRATION_ID",
    "campaign_config_v164",
    "freeze_sample_tax_replication_preregistration_v164",
)
