"""Outcome-free preregistration for the V144 source-unseen fifth family."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v144 as domains
from acfqp.construction_k7_occurrence_factor_bank_update_independent_verifier_v141 import (
    EXPECTED_CANONICAL_BYTE_COUNT as V141_VERIFICATION_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256 as V141_VERIFICATION_SHA256,
    VERIFICATION_ID as V141_VERIFICATION_ID,
)
from acfqp.construction_k7_occurrence_factor_bank_update_planning_campaign_v143r1 import (
    CAMPAIGN_ID as V143R1_CAMPAIGN_ID,
    EXPECTED_CANONICAL_BYTE_COUNT as V143R1_CAMPAIGN_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256 as V143R1_CAMPAIGN_SHA256,
)
from acfqp.construction_k7_occurrence_factor_bank_update_planning_independent_verifier_v143r1 import (
    EXPECTED_CANONICAL_BYTE_COUNT as V143R1_VERIFICATION_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256 as V143R1_VERIFICATION_SHA256,
    VERIFICATION_ID as V143R1_VERIFICATION_ID,
)
from acfqp.generic_maintenance_cascade_adapter_v144 import (
    FAMILY,
    maintenance_cascade_config_v144,
)
from acfqp.occurrence_factor_bank_update_v141 import (
    BANK_ID as V141_BANK_ID,
    EXPECTED_CANONICAL_BYTE_COUNT as V141_BANK_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256 as V141_BANK_SHA256,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


IMPLEMENTATION_COMMITS = ("d5e45392c6a1c00d48449245f9fd45066edbb94a",)
PREREGISTRATION_ID = "f2e114e4c00b6a98475cd7548e1d4f3301c76204864453183cdf0df8903f9f38"
EXPECTED_CANONICAL_BYTE_COUNT = 18_504
EXPECTED_CANONICAL_SHA256 = (
    "3647773075dd04d18f24d3416d80ff5740cd713422693a9150a616ed57088a59"
)
TARGET_OCCURRENCES = tuple((FAMILY, seed) for seed in range(1_047_251, 1_047_257))
TARGET_EPISODE_INDICES = (453, 454)
TARGET_WORKER_COUNT = 2
REQUIRED_TARGET_OCCURRENCE_COUNT = 6
MAXIMUM_ACQUISITION_LABELS = 1_024
SOURCE_ROOT = Path(__file__).resolve().parents[2]
FROZEN_SOURCE_FACTS = (
    (
        "src/acfqp/construction_k7_domain_registry_extension_v144.py",
        2_110,
        "a9a8fde715009c2e1ea609495dfd8c0847d4e177df96aa2c51f8f83695e5ab45",
    ),
    (
        "src/acfqp/generic_maintenance_cascade_adapter_v144.py",
        4_425,
        "fe895b058ffc038fb2f529dd41f5a8e10eb57d3e49ecf40d3be7ecd12dcb7b41",
    ),
    (
        "src/acfqp/generic_relational_factor_execution_projection_v144.py",
        10_025,
        "f108b10b3b74a07e30c3f32b8d153a7cca2e761ce6f8878d7159254864388720",
    ),
    (
        "src/acfqp/fifth_family_factor_bank_transfer_acquisition_v144.py",
        14_223,
        "5b5f5eec815107da17ffcffefcc3d1ef89c14a253fb8a1738e703dd9593da9c2",
    ),
    (
        "src/acfqp/fifth_family_factor_bank_transfer_campaign_core_v144.py",
        15_455,
        "6b6cf49a33c9934f63a5b2a3aa3b2ba5a399a3defa71901a285045f205f1f833",
    ),
)


class ConstructionK7FifthFamilyFactorBankTransferPreregistrationV144Error(
    ValueError
):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7FifthFamilyFactorBankTransferPreregistrationV144Error(
        message
    )


def campaign_config_v144() -> dict[str, Any]:
    config = maintenance_cascade_config_v144()
    config["families"][FAMILY]["maximum_acquisition_labels"] = (
        MAXIMUM_ACQUISITION_LABELS
    )
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


def _source_facts() -> list[dict[str, Any]]:
    return [
        {
            "relative_path": path,
            "byte_count": len(raw := (SOURCE_ROOT / path).read_bytes()),
            "sha256": hashlib.sha256(raw).hexdigest(),
        }
        for path, _count, _digest in FROZEN_SOURCE_FACTS
    ]


def _document(dictionary_raw: bytes, verification_raw: bytes) -> dict[str, Any]:
    dictionary = loads_canonical_json(dictionary_raw)
    verification = loads_canonical_json(verification_raw)
    if (
        canonical_json_bytes(dictionary) != dictionary_raw
        or len(dictionary_raw) != V141_BANK_BYTE_COUNT
        or hashlib.sha256(dictionary_raw).hexdigest() != V141_BANK_SHA256
        or dictionary.get("bank_id") != V141_BANK_ID
        or dictionary.get("source_occurrence_archive_cardinality") != 16
        or dictionary.get("selected_minimum_distinct_occurrence_support") != 9
        or dictionary.get("selected_template_count") != 5
        or dictionary.get("robust_candidate_schema_decoded") is not True
        or dictionary.get("new_target_outcomes_accessed") is not False
        or canonical_json_bytes(verification) != verification_raw
        or len(verification_raw) != V141_VERIFICATION_BYTE_COUNT
        or hashlib.sha256(verification_raw).hexdigest() != V141_VERIFICATION_SHA256
        or verification.get("verification_id") != V141_VERIFICATION_ID
        or verification.get("bank_id") != V141_BANK_ID
        or verification.get(
            "producer_free_campaign_occurrence_candidate_reconstruction"
        )
        is not True
        or verification.get(
            "producer_free_support_threshold_and_factor_bank_reconstruction"
        )
        is not True
    ):
        _fail("V144 frozen V141 factor-bank receipt changed")
    source_facts = _source_facts()
    expected = [
        {"relative_path": path, "byte_count": count, "sha256": digest}
        for path, count, digest in FROZEN_SOURCE_FACTS
    ]
    if source_facts != expected:
        _fail("V144 frozen implementation source changed")
    config = campaign_config_v144()
    payload = {
        "schema": "acfqp.fifth_family_factor_bank_transfer_preregistration.v144",
        "implementation_commits": list(IMPLEMENTATION_COMMITS),
        "frozen_implementation_source_facts": source_facts,
        "frozen_v141_factor_bank": dictionary,
        "frozen_v141_independent_verification": verification,
        "preserved_v143r1_campaign_identity": {
            "campaign_id": V143R1_CAMPAIGN_ID,
            "byte_count": V143R1_CAMPAIGN_BYTE_COUNT,
            "sha256": V143R1_CAMPAIGN_SHA256,
        },
        "preserved_v143r1_verification_identity": {
            "verification_id": V143R1_VERIFICATION_ID,
            "byte_count": V143R1_VERIFICATION_BYTE_COUNT,
            "sha256": V143R1_VERIFICATION_SHA256,
        },
        "target_occurrences": config["target_occurrences"],
        "target_episode_indices": list(config["target_episode_indices"]),
        "target_worker_count": config["target_worker_count"],
        "required_target_occurrence_count": config[
            "required_target_occurrence_count"
        ],
        "maximum_acquisition_labels": MAXIMUM_ACQUISITION_LABELS,
        "registered_gate": {
            "v141_factor_bank_and_verification_precede_target_outcomes": True,
            "v143r1_campaign_and_verification_identities_preserved": True,
            "target_family_absent_from_v141_source_occurrence_archive": True,
            "source_unseen_relative_to_v141_not_globally_novel": True,
            "fresh_target_occurrence_identities": True,
            "same_synthesizer_and_stop_rule_both_arms": True,
            "only_arm_switch_is_normalized_factor_prior": True,
            "finite_relations_lowered_before_planning": True,
            "historical_v121_v122_modules_unchanged": True,
            "aggregate_positive_reduction_is_primary_gate": True,
            "strict_positive_reduction_required_each_occurrence": False,
            "zero_and_negative_occurrences_must_be_preserved": True,
            "both_arm_receding_episodes_required": True,
            "certificate_failure_only_ground_recovery_required": True,
            "compiled_world_model_only_planning_required": True,
            "strict_incompatible_schema_no_transfer_required": True,
            "producer_free_verification_required": True,
        },
        "claim_boundary": {
            "target_outcomes_accessed": False,
            "registered_v144_target_outcome_observed": False,
            "source_unseen_relative_to_v141": True,
            "globally_unseen_kernel_claimed": False,
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
        "preregistration_id": domains.extension_content_id_v144(
            domains.CONSTRUCTION_K7_FIFTH_FAMILY_FACTOR_BANK_TRANSFER_PREREGISTRATION_V144_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class FifthFamilyFactorBankTransferPreregistrationV144:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str

    def __post_init__(self) -> None:
        document = loads_canonical_json(self.canonical_bytes)
        payload = {
            key: value
            for key, value in document.items()
            if key != "preregistration_id"
        }
        if (
            self._issuer is not _ISSUER
            or canonical_json_bytes(document) != self.canonical_bytes
            or document.get("preregistration_id") != self.preregistration_id
            or domains.extension_content_id_v144(
                domains.CONSTRUCTION_K7_FIFTH_FAMILY_FACTOR_BANK_TRANSFER_PREREGISTRATION_V144_DOMAIN,
                payload,
            )
            != self.preregistration_id
        ):
            _fail("V144 preregistration bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


def freeze_fifth_family_factor_bank_transfer_preregistration_v144(
    dictionary_raw: bytes,
    verification_raw: bytes,
) -> FifthFamilyFactorBankTransferPreregistrationV144:
    document = _document(dictionary_raw, verification_raw)
    raw = canonical_json_bytes(document)
    identity = document["preregistration_id"]
    if PREREGISTRATION_ID != "0" * 64 and (
        identity != PREREGISTRATION_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("V144 frozen preregistration changed")
    return FifthFamilyFactorBankTransferPreregistrationV144(
        _ISSUER, raw, identity
    )


__all__ = (
    "PREREGISTRATION_ID",
    "campaign_config_v144",
    "freeze_fifth_family_factor_bank_transfer_preregistration_v144",
)
