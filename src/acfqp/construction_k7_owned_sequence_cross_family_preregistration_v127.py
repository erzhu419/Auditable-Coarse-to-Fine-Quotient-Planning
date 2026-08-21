"""Outcome-free preregistration for V127 cross-family owned-sequence reuse."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v127 as domains
from acfqp import construction_k7_standalone_generic_owned_preregistration_v126 as previous
from acfqp.construction_k7_standalone_generic_owned_campaign_v126 import (
    CAMPAIGN_ID as V126_CAMPAIGN_ID,
    EXPECTED_CANONICAL_BYTE_COUNT as V126_CAMPAIGN_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256 as V126_CAMPAIGN_SHA256,
)
from acfqp.construction_k7_standalone_generic_owned_independent_verifier_v126 import (
    EXPECTED_CANONICAL_BYTE_COUNT as V126_VERIFICATION_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256 as V126_VERIFICATION_SHA256,
    VERIFICATION_ID as V126_VERIFICATION_ID,
)
from acfqp.generic_artifact_derived_factor_projection_v120 import derive_artifact_factor_projection_v120
from acfqp.generic_dual_budget_adapter_v119 import FAMILY, dual_budget_config_v119
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


IMPLEMENTATION_COMMITS = ("352fbf6af12c1d9e565e86bdba607f49984fe29c",)
V126_VERIFICATION_COMMIT = "dcf68b9"
PREREGISTRATION_ID = "0008da1c71911896c437dd35dda3879f46a33ffab81e25126dea3589a91efdbd"
EXPECTED_CANONICAL_BYTE_COUNT = 50_765
EXPECTED_CANONICAL_SHA256 = "31e9438b4527c7c706b73c9cbdf31a07ce38664b745d50480a5d0f3e1f0e61c5"
TARGET_OCCURRENCES = ((FAMILY, 1_042_101), (FAMILY, 1_042_102))
TARGET_EPISODE_INDICES = (311, 312, 313)
TARGET_WORKER_COUNT = 2
REQUIRED_TARGET_OCCURRENCE_COUNT = 2
MAXIMUM_ACQUISITION_LABELS = 2_048
SOURCE_ROOT = Path(__file__).resolve().parents[2]
FROZEN_SOURCE_FACTS = (
    ("src/acfqp/construction_k7_domain_registry_extension_v127.py", 1_567, "95294a890d13126cbd877ffe95d9db099b51f1647a2713764a4ef68f7842593a"),
    ("src/acfqp/owned_sequence_cross_family_campaign_core_v127.py", 10_529, "6eeeebf020e6fbf246a65f770ed5ebb7d1725f9739e15ab23b279662686cfa5f"),
    ("src/acfqp/construction_k7_standalone_generic_owned_campaign_v126.py", 3_728, "228123d29effdf80b8631a66a907860d1ba38282634d1763377f5d0030b4e386"),
    ("src/acfqp/construction_k7_standalone_generic_owned_independent_verifier_v126.py", 20_725, "60d378ccd359f19b79d7747977d543dc25ec897321f1cd73aaf4cc8534a73933"),
    *previous.FROZEN_SOURCE_FACTS,
)


class ConstructionK7OwnedSequenceCrossFamilyPreregistrationV127Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7OwnedSequenceCrossFamilyPreregistrationV127Error(message)


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


def campaign_config_v127() -> dict[str, Any]:
    config = copy.deepcopy(dual_budget_config_v119())
    config["families"][FAMILY]["maximum_acquisition_labels"] = MAXIMUM_ACQUISITION_LABELS
    config.update(
        target_occurrences=[{"family": family, "seed": seed} for family, seed in TARGET_OCCURRENCES],
        target_episode_indices=TARGET_EPISODE_INDICES,
        target_worker_count=TARGET_WORKER_COUNT,
        required_target_occurrence_count=REQUIRED_TARGET_OCCURRENCE_COUNT,
    )
    return config


def _document(source_campaign_bytes: Mapping[str, bytes], v126_campaign_raw: bytes, v126_verification_raw: bytes):
    campaign = loads_canonical_json(v126_campaign_raw)
    verification = loads_canonical_json(v126_verification_raw)
    if (
        len(v126_campaign_raw) != V126_CAMPAIGN_BYTE_COUNT
        or hashlib.sha256(v126_campaign_raw).hexdigest() != V126_CAMPAIGN_SHA256
        or campaign.get("campaign_id") != V126_CAMPAIGN_ID
        or campaign.get("registered_gate", {}).get("passed") is not True
        or len(v126_verification_raw) != V126_VERIFICATION_BYTE_COUNT
        or hashlib.sha256(v126_verification_raw).hexdigest() != V126_VERIFICATION_SHA256
        or verification.get("verification_id") != V126_VERIFICATION_ID
        or verification.get("registered_gate_independently_verified") is not True
    ):
        _fail("V127 frozen V126 predecessor changed")
    library = derive_artifact_factor_projection_v120(dict(source_campaign_bytes))
    payload = {
        "schema": "acfqp.owned_sequence_cross_family_preregistration.v127",
        "implementation_commits": list(IMPLEMENTATION_COMMITS),
        "frozen_success_predecessor": {
            "v126_campaign_id": V126_CAMPAIGN_ID,
            "v126_campaign_byte_count": V126_CAMPAIGN_BYTE_COUNT,
            "v126_campaign_sha256": V126_CAMPAIGN_SHA256,
            "v126_verification_id": V126_VERIFICATION_ID,
            "v126_verification_byte_count": V126_VERIFICATION_BYTE_COUNT,
            "v126_verification_sha256": V126_VERIFICATION_SHA256,
            "v126_verification_commit": V126_VERIFICATION_COMMIT,
        },
        "artifact_factor_library": library,
        "artifact_factor_library_id": library["factor_library_id"],
        "source_closure": {
            "source_facts": _frozen_source_facts(),
            "v127_domains": dict(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V127),
            "frozen_before_any_registered_v127_target_outcome": True,
        },
        "identity_contract": {
            "target_family": FAMILY,
            "target_occurrences": campaign_config_v127()["target_occurrences"],
            "target_seeds_unique": True,
            "target_seeds_not_previously_exposed": True,
            "target_episode_indices": list(TARGET_EPISODE_INDICES),
            "development_seed": 1_030_005,
            "development_episode_indices": [308, 309, 310],
            "development_identity_excluded_from_registered_gate": True,
        },
        "construction_contract": {
            "unchanged_v126_owned_sequence_required": True,
            "target_family_differs_from_v126_inventory_family": True,
            "family_dispatch_inside_owned_sequence_forbidden": True,
            "retained_v113_sequence_orchestration_present": False,
            "retained_v119_sequence_orchestration_present": False,
            "local_ground_distinction_only_after_certificate_failure": True,
            "strict_incompatible_schema_no_transfer_required": True,
        },
        "development_evidence_retained_before_registration": {
            "target_family": FAMILY,
            "development_seed": 1_030_005,
            "all_three_episodes_succeeded": True,
            "partial_prior_acquisition_labels": 21,
            "certificate_local_labels": 30,
            "lifetime_target_labels": 51,
            "execution_steps": 18,
            "direct_generic_factor_program_plans": 20,
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
            "registered_v127_target_outcome_observed": False,
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
        "preregistration_id": domains.extension_content_id_v127(
            domains.CONSTRUCTION_K7_OWNED_SEQUENCE_CROSS_FAMILY_PREREGISTRATION_V127_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class OwnedSequenceCrossFamilyPreregistrationV127:
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
            or domains.extension_content_id_v127(
                domains.CONSTRUCTION_K7_OWNED_SEQUENCE_CROSS_FAMILY_PREREGISTRATION_V127_DOMAIN,
                payload,
            )
            != self.preregistration_id
        ):
            _fail("V127 preregistration bytes or issuer changed")

    def to_document(self):
        return loads_canonical_json(self.canonical_bytes)


_CACHE = None


def freeze_owned_sequence_cross_family_preregistration_v127(
    source_campaign_bytes: Mapping[str, bytes],
    v126_campaign_raw: bytes,
    v126_verification_raw: bytes,
):
    global _CACHE
    if _CACHE is None:
        if _source_facts() != _frozen_source_facts():
            _fail("V127 preregistered source closure changed")
        document = _document(source_campaign_bytes, v126_campaign_raw, v126_verification_raw)
        raw = canonical_json_bytes(document)
        identity = document["preregistration_id"]
        if PREREGISTRATION_ID != "0" * 64 and (
            identity != PREREGISTRATION_ID
            or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
            or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
        ):
            _fail("V127 frozen preregistration changed")
        _CACHE = OwnedSequenceCrossFamilyPreregistrationV127(_ISSUER, raw, identity)
    return _CACHE


__all__ = ("PREREGISTRATION_ID", "campaign_config_v127", "freeze_owned_sequence_cross_family_preregistration_v127")
