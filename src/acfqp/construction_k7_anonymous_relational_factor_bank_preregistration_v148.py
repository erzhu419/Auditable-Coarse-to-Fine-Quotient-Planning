"""Outcome-free V148 preregistration for the relational-prior ablation."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v148 as domains
from acfqp import construction_k7_certificate_local_recovery_union_preregistration_v145 as v145
from acfqp.anonymous_relational_template_instantiator_v147 import BANK_ID, VERIFICATION_ID
from acfqp.generic_maintenance_cascade_adapter_v144 import FAMILY
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


IMPLEMENTATION_COMMITS = ("6d85636b7c465cf92c7679f4998927f5e1e13f99",)
PREREGISTRATION_ID = "b8e2e47d301a77134e90e27beecd263be211ce383c90fa959d3eae26261c7900"
EXPECTED_CANONICAL_BYTE_COUNT = 8_523
EXPECTED_CANONICAL_SHA256 = "bed3f6a36aea6601f495602db0ec712e5431012f89f1370574367aaf3c4fee21"
V145_CAMPAIGN_ID = "24a50acc5cf553f4fc457e17aa4ffff0fc6b6b9ebe08fa0d54076d998c3eeaa9"
V145_CAMPAIGN_BYTE_COUNT = 17_516_246
V145_CAMPAIGN_SHA256 = "5584aa76043f76d69b72ec189bc67a3952e758bbaaad33025b73dc859851f33c"
V145_VERIFICATION_ID = "0924f57684bdeae9b9da339d949f9ab2f00949b5684817621eae26497adc3d7c"
V145_VERIFICATION_BYTE_COUNT = 12_863
V145_VERIFICATION_SHA256 = "f363feba0e5e5c6a12c0f6f709f9c0f4fe55b0e3113b907005e4eb8f77bbcb13"
V146_BANK_BYTE_COUNT = 4_033
V146_BANK_SHA256 = "eb733aad5d7b5aed20933366ba4b6f8c9d24338b20a4437ef11ffbf4f0a99fe6"
V146_VERIFICATION_BYTE_COUNT = 1_028
V146_VERIFICATION_SHA256 = "891b48ce7d035ea8e56f68a3e3dc6a8838cbd62dfabf7af6a86a5d81f14a7e80"
TARGET_OCCURRENCES = tuple((FAMILY, seed) for seed in range(1_047_311, 1_047_317))
TARGET_EPISODE_INDICES = (521, 522, 523, 524)
TARGET_WORKER_COUNT = 2
REQUIRED_TARGET_OCCURRENCE_COUNT = 6
MAXIMUM_ACQUISITION_LABELS = 1_024
SOURCE_ROOT = Path(__file__).resolve().parents[2]
FROZEN_SOURCE_FACTS = (
    (
        "src/acfqp/construction_k7_domain_registry_extension_v148.py",
        1_735,
        "d52fe4f30dbcda02e0f8bc194480246f58cd43f999020920ae34cf17f2fde4c1",
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
        "src/acfqp/anonymous_relational_factor_bank_planning_campaign_core_v148.py",
        16_432,
        "7976ba1a720b4330a6f5d68683ea49484e70e9124e9977c3b8db7a9370bc30fe",
    ),
)


class ConstructionK7AnonymousRelationalFactorBankPreregistrationV148Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7AnonymousRelationalFactorBankPreregistrationV148Error(message)


def campaign_config_v148() -> dict[str, Any]:
    config = v145.campaign_config_v145()
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
    v145_campaign_raw: bytes,
    v145_verification_raw: bytes,
    v146_bank_raw: bytes,
    v146_verification_raw: bytes,
) -> dict[str, Any]:
    campaign = loads_canonical_json(v145_campaign_raw)
    source_verification = loads_canonical_json(v145_verification_raw)
    bank = loads_canonical_json(v146_bank_raw)
    bank_verification = loads_canonical_json(v146_verification_raw)
    if (
        canonical_json_bytes(campaign) != v145_campaign_raw
        or len(v145_campaign_raw) != V145_CAMPAIGN_BYTE_COUNT
        or hashlib.sha256(v145_campaign_raw).hexdigest() != V145_CAMPAIGN_SHA256
        or campaign.get("campaign_id") != V145_CAMPAIGN_ID
        or campaign.get("registered_gate", {}).get("passed") is not True
        or canonical_json_bytes(source_verification) != v145_verification_raw
        or len(v145_verification_raw) != V145_VERIFICATION_BYTE_COUNT
        or hashlib.sha256(v145_verification_raw).hexdigest()
        != V145_VERIFICATION_SHA256
        or source_verification.get("verification_id") != V145_VERIFICATION_ID
        or source_verification.get("campaign_id") != V145_CAMPAIGN_ID
        or canonical_json_bytes(bank) != v146_bank_raw
        or len(v146_bank_raw) != V146_BANK_BYTE_COUNT
        or hashlib.sha256(v146_bank_raw).hexdigest() != V146_BANK_SHA256
        or bank.get("bank_id") != BANK_ID
        or bank.get("source_v145_campaign_id") != V145_CAMPAIGN_ID
        or bank.get("source_v145_verification_id") != V145_VERIFICATION_ID
        or bank.get("selected_relational_template_count", 0) <= 0
        or bank.get("constant_and_relation_names_alpha_normalized") is not True
        or canonical_json_bytes(bank_verification) != v146_verification_raw
        or len(v146_verification_raw) != V146_VERIFICATION_BYTE_COUNT
        or hashlib.sha256(v146_verification_raw).hexdigest()
        != V146_VERIFICATION_SHA256
        or bank_verification.get("verification_id") != VERIFICATION_ID
        or bank_verification.get("bank_id") != BANK_ID
        or bank_verification.get(
            "producer_free_constant_relation_and_coordinate_alpha_normalization"
        )
        is not True
    ):
        _fail("V148 frozen V145/V146 predecessor changed")
    source_facts = _source_facts()
    expected = [
        {"relative_path": path, "byte_count": count, "sha256": digest}
        for path, count, digest in FROZEN_SOURCE_FACTS
    ]
    if source_facts != expected:
        _fail("V148 frozen implementation source changed")
    config = campaign_config_v148()
    payload = {
        "schema": "acfqp.anonymous_relational_factor_bank_preregistration.v148",
        "implementation_commits": list(IMPLEMENTATION_COMMITS),
        "frozen_implementation_source_facts": source_facts,
        "frozen_v145_source_identity": {
            "campaign_id": V145_CAMPAIGN_ID,
            "campaign_byte_count": V145_CAMPAIGN_BYTE_COUNT,
            "campaign_sha256": V145_CAMPAIGN_SHA256,
            "verification_id": V145_VERIFICATION_ID,
            "verification_byte_count": V145_VERIFICATION_BYTE_COUNT,
            "verification_sha256": V145_VERIFICATION_SHA256,
        },
        "frozen_v146_factor_bank": bank,
        "frozen_v146_independent_verification": bank_verification,
        "target_occurrences": config["target_occurrences"],
        "target_episode_indices": list(config["target_episode_indices"]),
        "target_worker_count": config["target_worker_count"],
        "required_target_occurrence_count": config["required_target_occurrence_count"],
        "maximum_acquisition_labels": MAXIMUM_ACQUISITION_LABELS,
        "registered_gate": {
            "fresh_target_occurrence_identities": True,
            "source_bank_and_verification_frozen_before_target_outcomes": True,
            "same_witness_blind_raw_transition_stream_both_arms": True,
            "same_observation_derived_relation_binding_both_arms": True,
            "same_generic_atomic_hypothesis_pool_both_arms": True,
            "same_candidate_carrier_replay_and_stop_rule_both_arms": True,
            "only_arm_switch_is_anonymous_relational_prior_codelength": True,
            "anonymous_relational_template_must_be_selected_in_prior_arm": True,
            "aggregate_positive_reduction_is_primary_gate": True,
            "zero_and_negative_occurrences_must_be_preserved": True,
            "all_four_receding_episodes_required": True,
            "certificate_failure_local_recovery_must_be_exercised": True,
            "program_compatible_refinement_or_exact_overlay_is_admissible": True,
            "exact_overlay_branch_exercise_required": False,
            "strict_incompatible_schema_no_transfer_required": True,
            "producer_free_verification_required": True,
            "frozen_two_worker_resource_schedule": True,
        },
        "claim_boundary": {
            "target_outcomes_accessed": False,
            "registered_v148_target_outcome_observed": False,
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
        "preregistration_id": domains.extension_content_id_v148(
            domains.CONSTRUCTION_K7_ANONYMOUS_RELATIONAL_PRIOR_PREREGISTRATION_V148_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class AnonymousRelationalFactorBankPreregistrationV148:
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
            or domains.extension_content_id_v148(
                domains.CONSTRUCTION_K7_ANONYMOUS_RELATIONAL_PRIOR_PREREGISTRATION_V148_DOMAIN,
                payload,
            )
            != self.preregistration_id
        ):
            _fail("V148 preregistration bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


def freeze_anonymous_relational_factor_bank_preregistration_v148(
    v145_campaign_raw: bytes,
    v145_verification_raw: bytes,
    v146_bank_raw: bytes,
    v146_verification_raw: bytes,
) -> AnonymousRelationalFactorBankPreregistrationV148:
    document = _document(
        v145_campaign_raw,
        v145_verification_raw,
        v146_bank_raw,
        v146_verification_raw,
    )
    raw = canonical_json_bytes(document)
    identity = document["preregistration_id"]
    if PREREGISTRATION_ID != "0" * 64 and (
        identity != PREREGISTRATION_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("V148 frozen preregistration changed")
    return AnonymousRelationalFactorBankPreregistrationV148(_ISSUER, raw, identity)


__all__ = (
    "PREREGISTRATION_ID",
    "campaign_config_v148",
    "freeze_anonymous_relational_factor_bank_preregistration_v148",
)
