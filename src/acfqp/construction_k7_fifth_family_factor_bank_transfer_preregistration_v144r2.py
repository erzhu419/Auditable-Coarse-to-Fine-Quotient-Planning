"""Outcome-free V144R2 long-horizon overlay-exercise preregistration."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v144r2 as domains
from acfqp import construction_k7_fifth_family_factor_bank_transfer_preregistration_v144r1 as v144r1
from acfqp.generic_maintenance_cascade_adapter_v144 import FAMILY
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


IMPLEMENTATION_COMMITS = ("4620ec8e8f3cbc1110826b907c0c424b7c96b5df",)
PREREGISTRATION_ID = "505c219aab3d82ecac7e1b65953e7c56045a56010c6304f35344c4f70249a03f"
EXPECTED_CANONICAL_BYTE_COUNT = 28_502
EXPECTED_CANONICAL_SHA256 = "8127eab8bfdcbf9780b4d39ff88da8dc854c31a7e383c536af5957e3a9e86f70"
V144R1_PREREGISTRATION_ID = "34beef0555332e3f95666007a587d9bfef465a82d1f5fed39eccc6d2511584c2"
V144R1_PREREGISTRATION_BYTE_COUNT = 22_554
V144R1_PREREGISTRATION_SHA256 = "07a97f2d09bcc80b8ec536af73a76d25cef8490662de54f1690b2aa35d5b69ca"
V144R1_CAMPAIGN_ID = "bc59170e6cbd15c082d699620e800ebca78bda2a4a338db4e840b841e901d2d1"
V144R1_CAMPAIGN_BYTE_COUNT = 5_840_090
V144R1_CAMPAIGN_SHA256 = "e7665f51118ffd271ef508d9f63ae48583026f27b23cdcf2d5979022ca405194"
V144R1_FAILURE_BYTE_COUNT = 2_921
V144R1_FAILURE_SHA256 = "4ca167f46e3be61ff3acd74adf3f766f034c67a859da2cdf38245434db33ebe9"
TARGET_OCCURRENCES = tuple((FAMILY, seed) for seed in range(1_047_271, 1_047_279))
TARGET_EPISODE_INDICES = (481, 482, 483, 484, 485, 486)
TARGET_WORKER_COUNT = 2
REQUIRED_TARGET_OCCURRENCE_COUNT = 8
MAXIMUM_ACQUISITION_LABELS = 1_024
SOURCE_ROOT = Path(__file__).resolve().parents[2]
FROZEN_SOURCE_FACTS = (
    (
        "src/acfqp/construction_k7_domain_registry_extension_v144r2.py",
        1_935,
        "613db6aae245f1637007ab213d86ff172638824ad0a0b4fc7116c4a542a0f05e",
    ),
    (
        "src/acfqp/fifth_family_factor_bank_transfer_campaign_core_v144r2.py",
        3_202,
        "90ddbf91e5a806e02f12a2f423bb126a0c9e61c95a42e27a812d9d68968198b5",
    ),
)


class ConstructionK7FifthFamilyFactorBankTransferPreregistrationV144R2Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7FifthFamilyFactorBankTransferPreregistrationV144R2Error(message)


def campaign_config_v144r2() -> dict[str, Any]:
    config = v144r1.campaign_config_v144r1()
    config["families"][FAMILY]["maximum_acquisition_labels"] = MAXIMUM_ACQUISITION_LABELS
    config.update(
        target_occurrences=[
            {"family": family, "seed": seed} for family, seed in TARGET_OCCURRENCES
        ],
        target_episode_indices=TARGET_EPISODE_INDICES,
        target_worker_count=TARGET_WORKER_COUNT,
        required_target_occurrence_count=REQUIRED_TARGET_OCCURRENCE_COUNT,
    )
    return config


def _source_facts() -> list[dict[str, Any]]:
    return [
        {
            "relative_path": path,
            "byte_count": len(raw := (SOURCE_ROOT / path).read_bytes()),
            "sha256": hashlib.sha256(raw).hexdigest(),
        }
        for path, _count, _digest in FROZEN_SOURCE_FACTS
    ]


def _document(
    v144r1_preregistration_raw: bytes,
    v144r1_campaign_raw: bytes,
    v144r1_failure_raw: bytes,
) -> dict[str, Any]:
    registration = loads_canonical_json(v144r1_preregistration_raw)
    campaign = loads_canonical_json(v144r1_campaign_raw)
    failure = loads_canonical_json(v144r1_failure_raw)
    if (
        canonical_json_bytes(registration) != v144r1_preregistration_raw
        or len(v144r1_preregistration_raw) != V144R1_PREREGISTRATION_BYTE_COUNT
        or hashlib.sha256(v144r1_preregistration_raw).hexdigest()
        != V144R1_PREREGISTRATION_SHA256
        or registration.get("preregistration_id") != V144R1_PREREGISTRATION_ID
        or canonical_json_bytes(campaign) != v144r1_campaign_raw
        or len(v144r1_campaign_raw) != V144R1_CAMPAIGN_BYTE_COUNT
        or hashlib.sha256(v144r1_campaign_raw).hexdigest() != V144R1_CAMPAIGN_SHA256
        or campaign.get("campaign_id") != V144R1_CAMPAIGN_ID
        or campaign.get("registered_gate", {}).get("passed") is not False
        or campaign.get("registered_gate", {}).get(
            "query_local_relational_overlay_exercised_at_least_once"
        )
        is not False
        or canonical_json_bytes(failure) != v144r1_failure_raw
        or len(v144r1_failure_raw) != V144R1_FAILURE_BYTE_COUNT
        or hashlib.sha256(v144r1_failure_raw).hexdigest() != V144R1_FAILURE_SHA256
        or failure.get("campaign_id") != V144R1_CAMPAIGN_ID
        or failure.get("same_identity_rerun_forbidden") is not True
    ):
        _fail("V144R2 frozen V144R1 predecessor or failure changed")
    source_facts = _source_facts()
    expected = [
        {"relative_path": path, "byte_count": count, "sha256": digest}
        for path, count, digest in FROZEN_SOURCE_FACTS
    ]
    if source_facts != expected:
        _fail("V144R2 frozen implementation source changed")
    config = campaign_config_v144r2()
    payload = {
        "schema": "acfqp.fifth_family_factor_bank_transfer_preregistration.v144r2",
        "implementation_commits": list(IMPLEMENTATION_COMMITS),
        "frozen_implementation_source_facts": source_facts,
        "frozen_v144r1_preregistration": registration,
        "preserved_v144r1_failed_campaign_identity": {
            "campaign_id": V144R1_CAMPAIGN_ID,
            "byte_count": V144R1_CAMPAIGN_BYTE_COUNT,
            "sha256": V144R1_CAMPAIGN_SHA256,
        },
        "frozen_v144r1_failure": failure,
        "target_occurrences": config["target_occurrences"],
        "target_episode_indices": list(config["target_episode_indices"]),
        "target_worker_count": config["target_worker_count"],
        "required_target_occurrence_count": config[
            "required_target_occurrence_count"
        ],
        "maximum_acquisition_labels": MAXIMUM_ACQUISITION_LABELS,
        "registered_gate": {
            "v144r1_failure_and_complete_campaign_preserved": True,
            "v144r1_identity_not_rerun": True,
            "fresh_target_occurrence_identities": True,
            "longer_receding_episode_stress_than_v144r1": True,
            "v144r1_algorithm_reused_without_outcome_adaptive_change": True,
            "query_local_exact_overlay_only_after_certificate_failure": True,
            "source_partial_program_remains_immutable": True,
            "overlay_not_promoted_to_global_dynamics": True,
            "overlay_not_used_as_safety_authority": True,
            "merged_overlay_graph_consumed_by_later_abstract_planning": True,
            "same_synthesizer_and_stop_rule_both_arms": True,
            "only_arm_switch_is_normalized_factor_prior": True,
            "aggregate_positive_reduction_is_primary_gate": True,
            "zero_and_negative_occurrences_must_be_preserved": True,
            "overlay_pipeline_must_be_exercised_at_least_once": True,
            "all_six_receding_episodes_required": True,
            "strict_incompatible_schema_no_transfer_required": True,
            "producer_free_verification_required": True,
        },
        "claim_boundary": {
            "target_outcomes_accessed": False,
            "registered_v144r2_target_outcome_observed": False,
            "complete_world_model_claimed": False,
            "arbitrary_unseen_domain_transfer_claimed": False,
            "global_exact_dynamics_claimed": False,
            "official_execution_allowed": False,
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
            "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        },
    }
    return {
        **payload,
        "preregistration_id": domains.extension_content_id_v144r2(
            domains.CONSTRUCTION_K7_FIFTH_FAMILY_FACTOR_BANK_TRANSFER_PREREGISTRATION_V144R2_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class FifthFamilyFactorBankTransferPreregistrationV144R2:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str

    def __post_init__(self) -> None:
        document = loads_canonical_json(self.canonical_bytes)
        payload = {key: value for key, value in document.items() if key != "preregistration_id"}
        if (
            self._issuer is not _ISSUER
            or canonical_json_bytes(document) != self.canonical_bytes
            or document.get("preregistration_id") != self.preregistration_id
            or domains.extension_content_id_v144r2(
                domains.CONSTRUCTION_K7_FIFTH_FAMILY_FACTOR_BANK_TRANSFER_PREREGISTRATION_V144R2_DOMAIN,
                payload,
            )
            != self.preregistration_id
        ):
            _fail("V144R2 preregistration bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


def freeze_fifth_family_factor_bank_transfer_preregistration_v144r2(
    v144r1_preregistration_raw: bytes,
    v144r1_campaign_raw: bytes,
    v144r1_failure_raw: bytes,
) -> FifthFamilyFactorBankTransferPreregistrationV144R2:
    document = _document(
        v144r1_preregistration_raw, v144r1_campaign_raw, v144r1_failure_raw
    )
    raw = canonical_json_bytes(document)
    identity = document["preregistration_id"]
    if PREREGISTRATION_ID != "0" * 64 and (
        identity != PREREGISTRATION_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("V144R2 frozen preregistration changed")
    return FifthFamilyFactorBankTransferPreregistrationV144R2(_ISSUER, raw, identity)


__all__ = (
    "PREREGISTRATION_ID",
    "campaign_config_v144r2",
    "freeze_fifth_family_factor_bank_transfer_preregistration_v144r2",
)
