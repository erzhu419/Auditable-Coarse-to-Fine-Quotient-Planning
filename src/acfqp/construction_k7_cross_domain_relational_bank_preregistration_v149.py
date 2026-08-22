"""Outcome-free V149 preregistration for cross-domain bank reuse."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v149 as domains
from acfqp.anonymous_relational_template_instantiator_v147 import BANK_ID, VERIFICATION_ID
from acfqp.generic_dual_budget_adapter_v119 import FAMILY as DUAL
from acfqp.generic_inventory_assembly_adapter_v118 import FAMILY as INVENTORY
from acfqp.generic_modular_routing_adapter_v128 import FAMILY as MODULAR
from acfqp.generic_packet_batching_adapter_v134 import (
    FAMILY as PACKET,
    packet_batching_config_v134,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


IMPLEMENTATION_COMMITS = ("affb62106608c37d1ed6f6f4d732c4fdb9197399",)
PREREGISTRATION_ID = "0ab10d76752bf5a6aeea1341386015627debe3e1009c2780fa0dbbbc2d164cb3"
EXPECTED_CANONICAL_BYTE_COUNT = 8_807
EXPECTED_CANONICAL_SHA256 = "3f938c6d42ed0508502534047ed52eee76f5b67267b6bb9700b4dfb282f612ae"
V146_BANK_BYTE_COUNT = 4_033
V146_BANK_SHA256 = "eb733aad5d7b5aed20933366ba4b6f8c9d24338b20a4437ef11ffbf4f0a99fe6"
V146_VERIFICATION_BYTE_COUNT = 1_028
V146_VERIFICATION_SHA256 = "891b48ce7d035ea8e56f68a3e3dc6a8838cbd62dfabf7af6a86a5d81f14a7e80"
V148_CAMPAIGN_ID = "d555b567fafef5053dbfdcd6fae725b4913e989a7888e70c0021248e370e5a57"
V148_CAMPAIGN_BYTE_COUNT = 18_492_453
V148_CAMPAIGN_SHA256 = "edd853eba70e28bb8efc94015fde5f81b3146db7d57cfe5688bb64e632581979"
V148_VERIFICATION_ID = "442393a952009697d0881e5b8d934f1ca570c838c483f757740024f77a685280"
V148_VERIFICATION_BYTE_COUNT = 12_340
V148_VERIFICATION_SHA256 = "edc41ed8f339f216938cdb547e0217344913b58d4141a6236a588e32a60b6388"
TARGET_OCCURRENCES = (
    (INVENTORY, 1_047_341),
    (INVENTORY, 1_047_342),
    (DUAL, 1_047_343),
    (DUAL, 1_047_344),
    (MODULAR, 1_047_345),
    (MODULAR, 1_047_346),
    (PACKET, 1_047_347),
    (PACKET, 1_047_348),
)
TARGET_EPISODE_INDICES = (551, 552, 553, 554)
TARGET_WORKER_COUNT = 2
REQUIRED_TARGET_OCCURRENCE_COUNT = 8
MAXIMUM_ACQUISITION_LABELS = 1_536
SOURCE_ROOT = Path(__file__).resolve().parents[2]
FROZEN_SOURCE_FACTS = (
    (
        "src/acfqp/construction_k7_domain_registry_extension_v149.py",
        1_502,
        "6f7b9076f842d6e20d8b3bde76aca67636d37532fae7773952e37e07c7fea38d",
    ),
    (
        "src/acfqp/cross_domain_relational_factor_bank_campaign_core_v149.py",
        15_468,
        "6759f91c3508857dafb00ee6a2b565f4a7f93d05c1790b2e0ffc1bf49875a9a4",
    ),
    (
        "src/acfqp/anonymous_relational_template_instantiator_v147.py",
        9_218,
        "cdbb4c0f47707e9c490aaac95895079ff3878f716bc3015c4243eea226a520f5",
    ),
    (
        "src/acfqp/anonymous_relational_factor_bank_acquisition_v148.py",
        26_160,
        "3094d26ef86aa2fde1c4932cb8872a666e4cbdeec0c8c24a23a973a6e1b12a84",
    ),
    (
        "src/acfqp/certificate_local_relational_overlay_sequence_v144r1.py",
        21_798,
        "aa8241ca383854b8e75b1c251746f8828d5a848e0b95486e5fd65bebe3056dab",
    ),
)


class ConstructionK7CrossDomainRelationalBankPreregistrationV149Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7CrossDomainRelationalBankPreregistrationV149Error(message)


def campaign_config_v149() -> dict[str, Any]:
    config = packet_batching_config_v134()
    for family in (INVENTORY, DUAL, MODULAR, PACKET):
        config["families"][family]["maximum_acquisition_labels"] = (
            MAXIMUM_ACQUISITION_LABELS
        )
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
    bank_raw: bytes,
    bank_verification_raw: bytes,
    v148_campaign_raw: bytes,
    v148_verification_raw: bytes,
) -> dict[str, Any]:
    bank = loads_canonical_json(bank_raw)
    bank_verification = loads_canonical_json(bank_verification_raw)
    v148_campaign = loads_canonical_json(v148_campaign_raw)
    v148_verification = loads_canonical_json(v148_verification_raw)
    if (
        canonical_json_bytes(bank) != bank_raw
        or len(bank_raw) != V146_BANK_BYTE_COUNT
        or hashlib.sha256(bank_raw).hexdigest() != V146_BANK_SHA256
        or bank.get("bank_id") != BANK_ID
        or bank.get("selected_relational_template_count", 0) <= 0
        or canonical_json_bytes(bank_verification) != bank_verification_raw
        or len(bank_verification_raw) != V146_VERIFICATION_BYTE_COUNT
        or hashlib.sha256(bank_verification_raw).hexdigest()
        != V146_VERIFICATION_SHA256
        or bank_verification.get("verification_id") != VERIFICATION_ID
        or bank_verification.get("bank_id") != BANK_ID
        or canonical_json_bytes(v148_campaign) != v148_campaign_raw
        or len(v148_campaign_raw) != V148_CAMPAIGN_BYTE_COUNT
        or hashlib.sha256(v148_campaign_raw).hexdigest() != V148_CAMPAIGN_SHA256
        or v148_campaign.get("campaign_id") != V148_CAMPAIGN_ID
        or v148_campaign.get("registered_gate", {}).get("passed") is not True
        or canonical_json_bytes(v148_verification) != v148_verification_raw
        or len(v148_verification_raw) != V148_VERIFICATION_BYTE_COUNT
        or hashlib.sha256(v148_verification_raw).hexdigest()
        != V148_VERIFICATION_SHA256
        or v148_verification.get("verification_id") != V148_VERIFICATION_ID
        or v148_verification.get("campaign_id") != V148_CAMPAIGN_ID
        or v148_verification.get(
            "registered_workload_sample_efficiency_improvement_independently_verified"
        )
        is not True
    ):
        _fail("V149 frozen V146/V148 predecessor changed")
    source_facts = _source_facts()
    expected = [
        {"relative_path": path, "byte_count": count, "sha256": digest}
        for path, count, digest in FROZEN_SOURCE_FACTS
    ]
    if source_facts != expected:
        _fail("V149 frozen implementation source changed")
    config = campaign_config_v149()
    payload = {
        "schema": "acfqp.cross_domain_relational_bank_preregistration.v149",
        "implementation_commits": list(IMPLEMENTATION_COMMITS),
        "frozen_implementation_source_facts": source_facts,
        "frozen_v146_factor_bank": bank,
        "frozen_v146_independent_verification": bank_verification,
        "frozen_v148_source_identity": {
            "campaign_id": V148_CAMPAIGN_ID,
            "campaign_byte_count": V148_CAMPAIGN_BYTE_COUNT,
            "campaign_sha256": V148_CAMPAIGN_SHA256,
            "verification_id": V148_VERIFICATION_ID,
            "verification_byte_count": V148_VERIFICATION_BYTE_COUNT,
            "verification_sha256": V148_VERIFICATION_SHA256,
        },
        "target_occurrences": config["target_occurrences"],
        "target_episode_indices": list(config["target_episode_indices"]),
        "target_worker_count": config["target_worker_count"],
        "required_target_occurrence_count": config[
            "required_target_occurrence_count"
        ],
        "maximum_acquisition_labels": MAXIMUM_ACQUISITION_LABELS,
        "registered_gate": {
            "fresh_target_occurrence_identities": True,
            "v146_source_family_absent_from_all_target_families": True,
            "four_source_unseen_structural_families_required": True,
            "same_witness_blind_raw_transition_stream_both_arms": True,
            "same_anonymous_binding_and_atomic_hypothesis_pool_both_arms": True,
            "same_candidate_carrier_replay_and_stop_rule_both_arms": True,
            "only_arm_switch_is_anonymous_factor_bank_codelength": True,
            "relational_instantiation_must_be_present_both_arms": True,
            "relational_template_selection_itself_is_not_primary_gate": True,
            "aggregate_and_each_family_positive_reduction_required": True,
            "zero_and_negative_occurrences_must_be_preserved": True,
            "all_four_receding_episodes_required": True,
            "certificate_failure_local_recovery_must_be_exercised": True,
            "program_compatible_refinement_or_exact_overlay_is_admissible": True,
            "strict_incompatible_schema_no_transfer_required": True,
            "producer_free_verification_required": True,
            "frozen_two_worker_resource_schedule": True,
        },
        "claim_boundary": {
            "target_outcomes_accessed": False,
            "registered_v149_target_outcome_observed": False,
            "cross_domain_relational_template_selection_claimed": False,
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
        "preregistration_id": domains.extension_content_id_v149(
            domains.CONSTRUCTION_K7_CROSS_DOMAIN_RELATIONAL_BANK_PREREGISTRATION_V149_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class CrossDomainRelationalBankPreregistrationV149:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str

    def __post_init__(self) -> None:
        document = loads_canonical_json(self.canonical_bytes)
        payload = {
            key: value for key, value in document.items() if key != "preregistration_id"
        }
        if (
            self._issuer is not _ISSUER
            or canonical_json_bytes(document) != self.canonical_bytes
            or document.get("preregistration_id") != self.preregistration_id
            or domains.extension_content_id_v149(
                domains.CONSTRUCTION_K7_CROSS_DOMAIN_RELATIONAL_BANK_PREREGISTRATION_V149_DOMAIN,
                payload,
            )
            != self.preregistration_id
        ):
            _fail("V149 preregistration bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


def freeze_cross_domain_relational_bank_preregistration_v149(
    bank_raw: bytes,
    bank_verification_raw: bytes,
    v148_campaign_raw: bytes,
    v148_verification_raw: bytes,
) -> CrossDomainRelationalBankPreregistrationV149:
    document = _document(
        bank_raw,
        bank_verification_raw,
        v148_campaign_raw,
        v148_verification_raw,
    )
    raw = canonical_json_bytes(document)
    identity = document["preregistration_id"]
    if PREREGISTRATION_ID != "0" * 64 and (
        identity != PREREGISTRATION_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("V149 frozen preregistration changed")
    return CrossDomainRelationalBankPreregistrationV149(_ISSUER, raw, identity)


__all__ = (
    "PREREGISTRATION_ID",
    "campaign_config_v149",
    "freeze_cross_domain_relational_bank_preregistration_v149",
)
