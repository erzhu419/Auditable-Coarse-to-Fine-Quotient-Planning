"""Outcome-free V144R1 preregistration after the preserved V144 failure."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v144r1 as domains
from acfqp.generic_maintenance_cascade_adapter_v144 import (
    FAMILY,
    maintenance_cascade_config_v144,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


IMPLEMENTATION_COMMITS = ("30bd6707929f48b14ec07a9c978fdc3cdf37e5cc",)
PREREGISTRATION_ID = "34beef0555332e3f95666007a587d9bfef465a82d1f5fed39eccc6d2511584c2"
EXPECTED_CANONICAL_BYTE_COUNT = 22_554
EXPECTED_CANONICAL_SHA256 = "07a97f2d09bcc80b8ec536af73a76d25cef8490662de54f1690b2aa35d5b69ca"
V144_PREREGISTRATION_ID = "f2e114e4c00b6a98475cd7548e1d4f3301c76204864453183cdf0df8903f9f38"
V144_PREREGISTRATION_BYTE_COUNT = 18_504
V144_PREREGISTRATION_SHA256 = "3647773075dd04d18f24d3416d80ff5740cd713422693a9150a616ed57088a59"
V144_FAILURE_BYTE_COUNT = 1_260
V144_FAILURE_SHA256 = "24a77206af172b7b51c9f4836b7e40ee28fbb63ef9e9c1de622dae91eb9e6418"
TARGET_OCCURRENCES = tuple((FAMILY, seed) for seed in range(1_047_261, 1_047_267))
TARGET_EPISODE_INDICES = (471, 472)
TARGET_WORKER_COUNT = 2
REQUIRED_TARGET_OCCURRENCE_COUNT = 6
MAXIMUM_ACQUISITION_LABELS = 1_024
SOURCE_ROOT = Path(__file__).resolve().parents[2]
FROZEN_SOURCE_FACTS = (
    (
        "src/acfqp/construction_k7_domain_registry_extension_v144r1.py",
        2_440,
        "c09a909d9ff6d07495b12e29c17d1d5d1cf455b71e1a07920825044cdff190cf",
    ),
    (
        "src/acfqp/certificate_local_relational_overlay_sequence_v144r1.py",
        21_798,
        "aa8241ca383854b8e75b1c251746f8828d5a848e0b95486e5fd65bebe3056dab",
    ),
    (
        "src/acfqp/fifth_family_factor_bank_transfer_campaign_core_v144r1.py",
        17_567,
        "aa848fed30a36f68d3bc1f966df22d19b9946f9d097fb23323bcfc58df60af41",
    ),
)


class ConstructionK7FifthFamilyFactorBankTransferPreregistrationV144R1Error(
    ValueError
):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7FifthFamilyFactorBankTransferPreregistrationV144R1Error(
        message
    )


def campaign_config_v144r1() -> dict[str, Any]:
    config = maintenance_cascade_config_v144()
    config["families"][FAMILY]["maximum_acquisition_labels"] = MAXIMUM_ACQUISITION_LABELS
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


def _document(v144_preregistration_raw: bytes, v144_failure_raw: bytes) -> dict[str, Any]:
    predecessor = loads_canonical_json(v144_preregistration_raw)
    failure = loads_canonical_json(v144_failure_raw)
    if (
        canonical_json_bytes(predecessor) != v144_preregistration_raw
        or len(v144_preregistration_raw) != V144_PREREGISTRATION_BYTE_COUNT
        or hashlib.sha256(v144_preregistration_raw).hexdigest()
        != V144_PREREGISTRATION_SHA256
        or predecessor.get("preregistration_id") != V144_PREREGISTRATION_ID
        or predecessor.get("claim_boundary", {}).get("target_outcomes_accessed")
        is not False
        or canonical_json_bytes(failure) != v144_failure_raw
        or len(v144_failure_raw) != V144_FAILURE_BYTE_COUNT
        or hashlib.sha256(v144_failure_raw).hexdigest() != V144_FAILURE_SHA256
        or failure.get("preregistration_id") != V144_PREREGISTRATION_ID
        or failure.get("outcome_kind")
        != "PREREGISTERED_INCREMENTAL_RELATIONAL_PROJECTION_FAILURE"
        or failure.get("error_type") != "GenericCompiledQuotientModelV123Error"
        or failure.get("same_identity_rerun_forbidden") is not True
        or failure.get("fresh_successor_identity_required_for_any_correction")
        is not True
    ):
        _fail("V144R1 predecessor identity or failure changed")
    source_facts = _source_facts()
    expected = [
        {"relative_path": path, "byte_count": count, "sha256": digest}
        for path, count, digest in FROZEN_SOURCE_FACTS
    ]
    if source_facts != expected:
        _fail("V144R1 frozen overlay implementation changed")
    config = campaign_config_v144r1()
    payload = {
        "schema": "acfqp.fifth_family_factor_bank_transfer_preregistration.v144r1",
        "implementation_commits": list(IMPLEMENTATION_COMMITS),
        "frozen_overlay_implementation_source_facts": source_facts,
        "frozen_v144_preregistration": predecessor,
        "frozen_v144_failed_predecessor": failure,
        "target_occurrences": config["target_occurrences"],
        "target_episode_indices": list(config["target_episode_indices"]),
        "target_worker_count": config["target_worker_count"],
        "required_target_occurrence_count": config[
            "required_target_occurrence_count"
        ],
        "maximum_acquisition_labels": MAXIMUM_ACQUISITION_LABELS,
        "registered_gate": {
            "v144_preregistered_failure_preserved_before_successor_execution": True,
            "v144_identity_not_rerun": True,
            "fresh_target_occurrence_identities": True,
            "query_local_exact_overlay_only_after_certificate_failure": True,
            "source_partial_program_remains_immutable": True,
            "overlay_not_promoted_to_global_dynamics": True,
            "overlay_not_used_as_safety_authority": True,
            "merged_overlay_graph_consumed_by_later_abstract_planning": True,
            "same_synthesizer_and_stop_rule_both_arms": True,
            "only_arm_switch_is_normalized_factor_prior": True,
            "aggregate_positive_reduction_is_primary_gate": True,
            "strict_positive_reduction_required_each_occurrence": False,
            "zero_and_negative_occurrences_must_be_preserved": True,
            "overlay_pipeline_must_be_exercised_at_least_once": True,
            "both_arm_receding_episodes_required": True,
            "strict_incompatible_schema_no_transfer_required": True,
            "producer_free_verification_required": True,
        },
        "claim_boundary": {
            "target_outcomes_accessed": False,
            "registered_v144r1_target_outcome_observed": False,
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
        "preregistration_id": domains.extension_content_id_v144r1(
            domains.CONSTRUCTION_K7_FIFTH_FAMILY_FACTOR_BANK_TRANSFER_PREREGISTRATION_V144R1_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class FifthFamilyFactorBankTransferPreregistrationV144R1:
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
            or domains.extension_content_id_v144r1(
                domains.CONSTRUCTION_K7_FIFTH_FAMILY_FACTOR_BANK_TRANSFER_PREREGISTRATION_V144R1_DOMAIN,
                payload,
            )
            != self.preregistration_id
        ):
            _fail("V144R1 preregistration bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


def freeze_fifth_family_factor_bank_transfer_preregistration_v144r1(
    v144_preregistration_raw: bytes,
    v144_failure_raw: bytes,
) -> FifthFamilyFactorBankTransferPreregistrationV144R1:
    document = _document(v144_preregistration_raw, v144_failure_raw)
    raw = canonical_json_bytes(document)
    identity = document["preregistration_id"]
    if PREREGISTRATION_ID != "0" * 64 and (
        identity != PREREGISTRATION_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("V144R1 frozen preregistration changed")
    return FifthFamilyFactorBankTransferPreregistrationV144R1(
        _ISSUER, raw, identity
    )


__all__ = (
    "PREREGISTRATION_ID",
    "campaign_config_v144r1",
    "freeze_fifth_family_factor_bank_transfer_preregistration_v144r1",
)
