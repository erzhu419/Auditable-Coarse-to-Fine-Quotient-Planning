"""Outcome-free preregistration for V128 third-family owned-sequence reuse."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v128 as domains
from acfqp import construction_k7_owned_sequence_cross_family_preregistration_v127 as previous
from acfqp.construction_k7_owned_sequence_cross_family_campaign_v127 import (
    CAMPAIGN_ID as V127_CAMPAIGN_ID,
    EXPECTED_CANONICAL_BYTE_COUNT as V127_CAMPAIGN_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256 as V127_CAMPAIGN_SHA256,
)
from acfqp.construction_k7_owned_sequence_cross_family_independent_verifier_v127 import (
    EXPECTED_CANONICAL_BYTE_COUNT as V127_VERIFICATION_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256 as V127_VERIFICATION_SHA256,
    VERIFICATION_ID as V127_VERIFICATION_ID,
)
from acfqp.generic_artifact_derived_factor_projection_v120 import derive_artifact_factor_projection_v120
from acfqp.generic_modular_routing_adapter_v128 import FAMILY, modular_routing_config_v128
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


IMPLEMENTATION_COMMITS = ("dbca3ab7fb247d6e2344e140b5fad1cf2de2554b",)
V127_CAMPAIGN_COMMIT = "d0fd18c"
V127_VERIFICATION_COMMIT = "2620483"
PREREGISTRATION_ID = "4bc5ad827e039781a5c94e25ade64c2afad3d032018a95199d70a4c64f1082e8"
EXPECTED_CANONICAL_BYTE_COUNT = 51_706
EXPECTED_CANONICAL_SHA256 = "ca00c27a3e1c43e4c01284c917cfc3d45ddb7ba314168db326a5dbce2b997659"
TARGET_OCCURRENCES = ((FAMILY, 1_043_101), (FAMILY, 1_043_102))
TARGET_EPISODE_INDICES = (317, 318, 319)
TARGET_WORKER_COUNT = 2
REQUIRED_TARGET_OCCURRENCE_COUNT = 2
MAXIMUM_ACQUISITION_LABELS = 2_048
SOURCE_ROOT = Path(__file__).resolve().parents[2]
FROZEN_SOURCE_FACTS = (
    ("src/acfqp/construction_k7_domain_registry_extension_v128.py", 1_567, "85e08ee3163f4f9590c0b582f4507b14a09f6509f5d03a6d99ec26d9366da2e0"),
    ("src/acfqp/generic_modular_routing_adapter_v128.py", 4_512, "98586ebaecdf73239321d77189a836dd5430c866cb42707d030b72c5852edc0b"),
    ("src/acfqp/third_family_owned_sequence_campaign_core_v128.py", 10_558, "f29c6adfe1dcf0afc7eab17bd348007f33a6b7c879a37fb84b72ced9896a1f4a"),
    ("src/acfqp/construction_k7_owned_sequence_cross_family_campaign_v127.py", 3_758, "2bc2c64f7cff363263f3f77931a16f06ad27053b6ff8701064a5e012db8f40ba"),
    ("src/acfqp/construction_k7_owned_sequence_cross_family_independent_verifier_v127.py", 21_263, "40aada0b529550da59a3ebd8dc10be60f9ea5f013f6b4dc7c9f6b92162a1ef60"),
    *previous.FROZEN_SOURCE_FACTS,
)


class ConstructionK7ThirdFamilyOwnedSequencePreregistrationV128Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7ThirdFamilyOwnedSequencePreregistrationV128Error(message)


def _frozen_source_facts():
    return [{"relative_path": path, "byte_count": count, "sha256": digest} for path, count, digest in FROZEN_SOURCE_FACTS]


def _source_facts():
    return [
        {
            "relative_path": path,
            "byte_count": len((SOURCE_ROOT / path).read_bytes()),
            "sha256": hashlib.sha256((SOURCE_ROOT / path).read_bytes()).hexdigest(),
        }
        for path, _count, _digest in FROZEN_SOURCE_FACTS
    ]


def campaign_config_v128() -> dict[str, Any]:
    config = copy.deepcopy(modular_routing_config_v128())
    config["families"][FAMILY]["maximum_acquisition_labels"] = MAXIMUM_ACQUISITION_LABELS
    config.update(
        target_occurrences=[{"family": family, "seed": seed} for family, seed in TARGET_OCCURRENCES],
        target_episode_indices=TARGET_EPISODE_INDICES,
        target_worker_count=TARGET_WORKER_COUNT,
        required_target_occurrence_count=REQUIRED_TARGET_OCCURRENCE_COUNT,
    )
    return config


def _document(source_campaign_bytes: Mapping[str, bytes], v127_campaign_raw: bytes, v127_verification_raw: bytes):
    campaign = loads_canonical_json(v127_campaign_raw)
    verification = loads_canonical_json(v127_verification_raw)
    if (
        len(v127_campaign_raw) != V127_CAMPAIGN_BYTE_COUNT
        or hashlib.sha256(v127_campaign_raw).hexdigest() != V127_CAMPAIGN_SHA256
        or campaign.get("campaign_id") != V127_CAMPAIGN_ID
        or campaign.get("registered_gate", {}).get("passed") is not True
        or len(v127_verification_raw) != V127_VERIFICATION_BYTE_COUNT
        or hashlib.sha256(v127_verification_raw).hexdigest() != V127_VERIFICATION_SHA256
        or verification.get("verification_id") != V127_VERIFICATION_ID
        or verification.get("registered_gate_independently_verified") is not True
    ):
        _fail("V128 frozen V127 predecessor changed")
    source = dict(source_campaign_bytes)
    if FAMILY.encode("ascii") in b"".join(source.values()):
        _fail("V128 target family leaked into the frozen factor-artifact sources")
    library = derive_artifact_factor_projection_v120(source)
    payload = {
        "schema": "acfqp.third_family_owned_sequence_preregistration.v128",
        "implementation_commits": list(IMPLEMENTATION_COMMITS),
        "frozen_success_predecessor": {
            "v127_campaign_id": V127_CAMPAIGN_ID,
            "v127_campaign_byte_count": V127_CAMPAIGN_BYTE_COUNT,
            "v127_campaign_sha256": V127_CAMPAIGN_SHA256,
            "v127_campaign_commit": V127_CAMPAIGN_COMMIT,
            "v127_verification_id": V127_VERIFICATION_ID,
            "v127_verification_byte_count": V127_VERIFICATION_BYTE_COUNT,
            "v127_verification_sha256": V127_VERIFICATION_SHA256,
            "v127_verification_commit": V127_VERIFICATION_COMMIT,
        },
        "artifact_factor_library": library,
        "artifact_factor_library_id": library["factor_library_id"],
        "source_closure": {
            "source_facts": _frozen_source_facts(),
            "v128_domains": dict(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V128),
            "frozen_before_any_registered_v128_target_outcome": True,
        },
        "identity_contract": {
            "target_family": FAMILY,
            "target_family_absent_from_frozen_factor_artifact_sources": True,
            "target_occurrences": campaign_config_v128()["target_occurrences"],
            "target_seeds_unique": True,
            "target_seeds_not_previously_exposed": True,
            "target_episode_indices": list(TARGET_EPISODE_INDICES),
            "development_seed": 1_030_006,
            "development_episode_indices": [314, 315, 316],
            "development_identity_excluded_from_registered_gate": True,
        },
        "construction_contract": {
            "unchanged_v126_owned_sequence_required": True,
            "family_dispatch_inside_owned_sequence_forbidden": True,
            "retained_v113_sequence_orchestration_present": False,
            "retained_v119_sequence_orchestration_present": False,
            "local_ground_distinction_only_after_certificate_failure": True,
            "strict_incompatible_schema_no_transfer_required": True,
        },
        "development_evidence_retained_before_registration": {
            "target_family": FAMILY,
            "development_seed": 1_030_006,
            "all_three_episodes_succeeded": True,
            "partial_prior_acquisition_labels": 20,
            "certificate_local_labels": 27,
            "lifetime_target_labels": 47,
            "execution_steps": 18,
            "direct_generic_factor_program_plans": 17,
        },
        "registered_gate": {
            "required_target_occurrence_count": REQUIRED_TARGET_OCCURRENCE_COUNT,
            "unchanged_v126_owned_sequence_reused_in_every_occurrence": True,
            "retained_v113_sequence_orchestration_absent_in_every_occurrence": True,
            "retained_v119_sequence_orchestration_absent_in_every_occurrence": True,
            "all_receding_episodes_succeed": True,
            "strict_incompatible_schema_no_transfer_required": True,
            "all_unfavourable_results_retained": True,
        },
        "resource_schedule": {
            "target_worker_count": TARGET_WORKER_COUNT,
            "maximum_simultaneous_worker_count": TARGET_WORKER_COUNT,
            "maximum_acquisition_labels": MAXIMUM_ACQUISITION_LABELS,
            "target_occurrence_count": REQUIRED_TARGET_OCCURRENCE_COUNT,
            "query_episode_count": len(TARGET_EPISODE_INDICES),
            "maximum_incremental_certificate_labels_per_episode": 100_000,
        },
        "accounting_contract": {
            "sample_labels_execution_steps_derivation_planning_and_model_checks_separate": True,
            "unused_resource_headroom_not_counted_as_sample_labels": True,
            "no_scalar_cost_aggregation": True,
        },
        "claim_boundary": {
            "registered_v128_target_outcome_observed": False,
            "producer_free_verification_present": False,
            "arbitrary_unseen_domain_transfer_claimed": False,
            "sample_efficiency_improvement_claimed": False,
            "complete_ground_world_model_synthesized": False,
            "official_execution_allowed": False,
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
            "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        },
    }
    return {
        **payload,
        "preregistration_id": domains.extension_content_id_v128(
            domains.CONSTRUCTION_K7_THIRD_FAMILY_OWNED_SEQUENCE_PREREGISTRATION_V128_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class ThirdFamilyOwnedSequencePreregistrationV128:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str

    def __post_init__(self):
        document = loads_canonical_json(self.canonical_bytes)
        payload = {key: value for key, value in document.items() if key != "preregistration_id"}
        if (
            self._issuer is not _ISSUER
            or canonical_json_bytes(document) != self.canonical_bytes
            or document.get("preregistration_id") != self.preregistration_id
            or domains.extension_content_id_v128(
                domains.CONSTRUCTION_K7_THIRD_FAMILY_OWNED_SEQUENCE_PREREGISTRATION_V128_DOMAIN,
                payload,
            ) != self.preregistration_id
        ):
            _fail("V128 preregistration bytes or issuer changed")

    def to_document(self):
        return loads_canonical_json(self.canonical_bytes)


_CACHE = None


def freeze_third_family_owned_sequence_preregistration_v128(
    source_campaign_bytes: Mapping[str, bytes],
    v127_campaign_raw: bytes,
    v127_verification_raw: bytes,
) -> ThirdFamilyOwnedSequencePreregistrationV128:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if _source_facts() != _frozen_source_facts():
        _fail("V128 source closure changed before registration")
    document = _document(source_campaign_bytes, v127_campaign_raw, v127_verification_raw)
    raw = canonical_json_bytes(document)
    identity = document["preregistration_id"]
    if PREREGISTRATION_ID != "0" * 64 and (
        identity != PREREGISTRATION_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("V128 preregistration changed")
    _CACHE = ThirdFamilyOwnedSequencePreregistrationV128(_ISSUER, raw, identity)
    return _CACHE


__all__ = (
    "FROZEN_SOURCE_FACTS",
    "PREREGISTRATION_ID",
    "TARGET_EPISODE_INDICES",
    "TARGET_OCCURRENCES",
    "V127_CAMPAIGN_ID",
    "V127_VERIFICATION_ID",
    "campaign_config_v128",
    "freeze_third_family_owned_sequence_preregistration_v128",
)
