"""Outcome-free preregistration for source-unseen packet-batching V134."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v134 as domains
from acfqp.construction_k7_opaque_archive_planning_campaign_v133 import (
    CAMPAIGN_ID as V133_CAMPAIGN_ID,
    EXPECTED_CANONICAL_BYTE_COUNT as V133_CAMPAIGN_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256 as V133_CAMPAIGN_SHA256,
)
from acfqp.construction_k7_opaque_archive_planning_independent_verifier_v133 import (
    EXPECTED_CANONICAL_BYTE_COUNT as V133_VERIFICATION_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256 as V133_VERIFICATION_SHA256,
    VERIFICATION_ID as V133_VERIFICATION_ID,
)
from acfqp.construction_k7_opaque_source_archive_independent_verifier_v132 import (
    EXPECTED_CANONICAL_BYTE_COUNT as V132_VERIFICATION_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256 as V132_VERIFICATION_SHA256,
    VERIFICATION_ID as V132_VERIFICATION_ID,
)
from acfqp.generic_packet_batching_adapter_v134 import (
    FAMILY,
    packet_batching_config_v134,
)
from acfqp.opaque_source_archive_dictionary_v132 import (
    DICTIONARY_ID as V132_DICTIONARY_ID,
    EXPECTED_CANONICAL_BYTE_COUNT as V132_DICTIONARY_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256 as V132_DICTIONARY_SHA256,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


IMPLEMENTATION_COMMITS = ("0aca8e8d5a5f653b498bcbc416a6dc14af57b686",)
V132_FINAL_COMMIT = "296f84c"
PREREGISTRATION_ID = "0" * 64
EXPECTED_CANONICAL_BYTE_COUNT = 0
EXPECTED_CANONICAL_SHA256 = "0" * 64
TARGET_SEEDS = (1_047_141, 1_047_142, 1_047_143, 1_047_144)
TARGET_EPISODE_INDICES = (374, 375, 376)
TARGET_WORKER_COUNT = 2
REQUIRED_TARGET_OCCURRENCE_COUNT = 4
MAXIMUM_ACQUISITION_LABELS = 384
SOURCE_ROOT = Path(__file__).resolve().parents[2]
FROZEN_SOURCE_FACTS = (
    (
        "src/acfqp/construction_k7_domain_registry_extension_v134.py",
        1_709,
        "355f17ddc5a0d063f04af47d0051ffdf80ae560b4cbd51a306b9a3afab5b4a8c",
    ),
    (
        "src/acfqp/domains/stochastic_packet_batching.py",
        9_735,
        "08097fe843771f188cafd593065a27c2553e2a7819bb5c567b7f9ebde6a7e979",
    ),
    (
        "src/acfqp/generic_packet_batching_adapter_v134.py",
        4_279,
        "10fba1e8f4aee4e86fe3de184cd455601b48f1cb115a7c5dd79c166770e2d817",
    ),
    (
        "src/acfqp/packet_batching_transfer_campaign_core_v134.py",
        10_419,
        "0337336eeab63369c87d436f82c45d8bdf4608e2522f25b74736985e1ba616d0",
    ),
)


class ConstructionK7PacketBatchingTransferPreregistrationV134Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7PacketBatchingTransferPreregistrationV134Error(message)


def campaign_config_v134() -> dict[str, Any]:
    config = packet_batching_config_v134()
    config["families"][FAMILY]["maximum_acquisition_labels"] = (
        MAXIMUM_ACQUISITION_LABELS
    )
    config.update(
        target_occurrences=[{"family": FAMILY, "seed": seed} for seed in TARGET_SEEDS],
        target_episode_indices=TARGET_EPISODE_INDICES,
        target_worker_count=TARGET_WORKER_COUNT,
        required_target_occurrence_count=REQUIRED_TARGET_OCCURRENCE_COUNT,
    )
    return config


def _source_facts() -> list[dict[str, Any]]:
    result = []
    for path, _count, _digest in FROZEN_SOURCE_FACTS:
        raw = (SOURCE_ROOT / path).read_bytes()
        result.append(
            {
                "relative_path": path,
                "byte_count": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
    return result


def _document(
    dictionary_raw: bytes,
    dictionary_verification_raw: bytes,
    v133_campaign_raw: bytes,
    v133_verification_raw: bytes,
) -> dict[str, Any]:
    dictionary = loads_canonical_json(dictionary_raw)
    dictionary_verification = loads_canonical_json(dictionary_verification_raw)
    v133_campaign = loads_canonical_json(v133_campaign_raw)
    v133_verification = loads_canonical_json(v133_verification_raw)
    if (
        canonical_json_bytes(dictionary) != dictionary_raw
        or len(dictionary_raw) != V132_DICTIONARY_BYTE_COUNT
        or hashlib.sha256(dictionary_raw).hexdigest() != V132_DICTIONARY_SHA256
        or dictionary.get("dictionary_id") != V132_DICTIONARY_ID
        or canonical_json_bytes(dictionary_verification)
        != dictionary_verification_raw
        or len(dictionary_verification_raw) != V132_VERIFICATION_BYTE_COUNT
        or hashlib.sha256(dictionary_verification_raw).hexdigest()
        != V132_VERIFICATION_SHA256
        or dictionary_verification.get("verification_id") != V132_VERIFICATION_ID
        or canonical_json_bytes(v133_campaign) != v133_campaign_raw
        or len(v133_campaign_raw) != V133_CAMPAIGN_BYTE_COUNT
        or hashlib.sha256(v133_campaign_raw).hexdigest() != V133_CAMPAIGN_SHA256
        or v133_campaign.get("campaign_id") != V133_CAMPAIGN_ID
        or v133_campaign.get("registered_gate", {}).get("passed") is not True
        or canonical_json_bytes(v133_verification) != v133_verification_raw
        or len(v133_verification_raw) != V133_VERIFICATION_BYTE_COUNT
        or hashlib.sha256(v133_verification_raw).hexdigest()
        != V133_VERIFICATION_SHA256
        or v133_verification.get("verification_id") != V133_VERIFICATION_ID
        or v133_verification.get(
            "registered_workload_sample_efficiency_improvement_independently_verified"
        )
        is not True
    ):
        _fail("V134 frozen V132/V133 predecessor changed")
    expected_source_facts = [
        {"relative_path": path, "byte_count": count, "sha256": digest}
        for path, count, digest in FROZEN_SOURCE_FACTS
    ]
    if _source_facts() != expected_source_facts:
        _fail("V134 frozen implementation source changed")
    config = campaign_config_v134()
    payload = {
        "schema": "acfqp.packet_batching_source_unseen_transfer_preregistration.v134",
        "implementation_commits": list(IMPLEMENTATION_COMMITS),
        "v132_final_commit_precedes_v134_implementation": V132_FINAL_COMMIT,
        "frozen_implementation_source_facts": expected_source_facts,
        "frozen_v132_dictionary": dictionary,
        "frozen_v132_independent_verification": dictionary_verification,
        "frozen_v133_success_predecessor": {
            "campaign_id": V133_CAMPAIGN_ID,
            "campaign_byte_count": V133_CAMPAIGN_BYTE_COUNT,
            "campaign_sha256": V133_CAMPAIGN_SHA256,
            "verification_id": V133_VERIFICATION_ID,
            "verification_byte_count": V133_VERIFICATION_BYTE_COUNT,
            "verification_sha256": V133_VERIFICATION_SHA256,
        },
        "target_occurrences": config["target_occurrences"],
        "target_episode_indices": list(config["target_episode_indices"]),
        "target_worker_count": config["target_worker_count"],
        "required_target_occurrence_count": config[
            "required_target_occurrence_count"
        ],
        "maximum_acquisition_labels": MAXIMUM_ACQUISITION_LABELS,
        "registered_gate": {
            "v132_dictionary_predates_target_domain_implementation": True,
            "fresh_source_unseen_target_identities": True,
            "same_synthesizer_and_stop_rule_both_arms": True,
            "only_arm_switch_is_factor_prior": True,
            "strict_positive_reduction_required_each_occurrence": True,
            "both_arm_receding_episodes_required": True,
            "certificate_failure_only_ground_recovery_required": True,
            "compiled_world_model_only_planning_required": True,
        },
        "claim_boundary": {
            "target_outcomes_accessed": False,
            "registered_v134_target_outcome_observed": False,
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
        "preregistration_id": domains.extension_content_id_v134(
            domains.CONSTRUCTION_K7_PACKET_BATCHING_TRANSFER_PREREGISTRATION_V134_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class PacketBatchingTransferPreregistrationV134:
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
            or domains.extension_content_id_v134(
                domains.CONSTRUCTION_K7_PACKET_BATCHING_TRANSFER_PREREGISTRATION_V134_DOMAIN,
                payload,
            )
            != self.preregistration_id
        ):
            _fail("V134 preregistration bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


def freeze_packet_batching_transfer_preregistration_v134(
    dictionary_raw: bytes,
    dictionary_verification_raw: bytes,
    v133_campaign_raw: bytes,
    v133_verification_raw: bytes,
) -> PacketBatchingTransferPreregistrationV134:
    document = _document(
        dictionary_raw,
        dictionary_verification_raw,
        v133_campaign_raw,
        v133_verification_raw,
    )
    raw = canonical_json_bytes(document)
    identity = document["preregistration_id"]
    if PREREGISTRATION_ID != "0" * 64 and (
        identity != PREREGISTRATION_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("V134 frozen preregistration changed")
    return PacketBatchingTransferPreregistrationV134(_ISSUER, raw, identity)


__all__ = (
    "PREREGISTRATION_ID",
    "campaign_config_v134",
    "freeze_packet_batching_transfer_preregistration_v134",
)
