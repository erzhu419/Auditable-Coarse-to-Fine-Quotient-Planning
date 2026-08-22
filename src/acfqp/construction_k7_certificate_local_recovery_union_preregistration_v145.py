"""Outcome-free V145 preregistration for the sound local-recovery union gate."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v145 as domains
from acfqp import construction_k7_fifth_family_factor_bank_transfer_preregistration_v144r2 as v144r2
from acfqp.generic_maintenance_cascade_adapter_v144 import FAMILY
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


IMPLEMENTATION_COMMITS = ("2789462f4433befb559ed3c946f8939dd69aeaa1",)
PREREGISTRATION_ID = "c254e8a09b46c8efb5849697887595f3e7462f2a2d797c5e58bd8a7011ec564e"
EXPECTED_CANONICAL_BYTE_COUNT = 34_809
EXPECTED_CANONICAL_SHA256 = "dd8a0b07244327bb46fed537bb59586ee09062948f8f3d1d62240d02d6a12549"
V144R2_PREREGISTRATION_ID = "505c219aab3d82ecac7e1b65953e7c56045a56010c6304f35344c4f70249a03f"
V144R2_PREREGISTRATION_BYTE_COUNT = 28_502
V144R2_PREREGISTRATION_SHA256 = "8127eab8bfdcbf9780b4d39ff88da8dc854c31a7e383c536af5957e3a9e86f70"
V144R2_CAMPAIGN_ID = "5008bebdbac2bd80674873dde52ffec8b220a4dcb395a10e80c50b701619567e"
V144R2_CAMPAIGN_BYTE_COUNT = 41_468_476
V144R2_CAMPAIGN_SHA256 = "fe5baa36098041a57cb865e7882d27eb8666c3606d120d2c1a99becd0db282db"
V144R2_FAILURE_BYTE_COUNT = 3_181
V144R2_FAILURE_SHA256 = "420242cda458596a23302aa73763752ec8fc91943a099e5113bb3b25c9ca2162"
TARGET_OCCURRENCES = tuple((FAMILY, seed) for seed in range(1_047_291, 1_047_297))
TARGET_EPISODE_INDICES = (501, 502, 503, 504)
TARGET_WORKER_COUNT = 2
REQUIRED_TARGET_OCCURRENCE_COUNT = 6
MAXIMUM_ACQUISITION_LABELS = 1_024
SOURCE_ROOT = Path(__file__).resolve().parents[2]
FROZEN_SOURCE_FACTS = (
    (
        "src/acfqp/construction_k7_domain_registry_extension_v145.py",
        1_791,
        "7dfc2ed512b078b1af20e9bf99804c8853583b09ab7f70bfa832f0ac32041ea9",
    ),
    (
        "src/acfqp/certificate_local_recovery_union_campaign_core_v145.py",
        4_712,
        "5ecb65e52c9d5017eeb9d4fb3776f1dbf2b59d78a83c75ad5e0b3c4bea33c1de",
    ),
)


class ConstructionK7CertificateLocalRecoveryUnionPreregistrationV145Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7CertificateLocalRecoveryUnionPreregistrationV145Error(message)


def campaign_config_v145() -> dict[str, Any]:
    config = v144r2.campaign_config_v144r2()
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
    v144r2_preregistration_raw: bytes,
    v144r2_campaign_raw: bytes,
    v144r2_failure_raw: bytes,
) -> dict[str, Any]:
    registration = loads_canonical_json(v144r2_preregistration_raw)
    campaign = loads_canonical_json(v144r2_campaign_raw)
    failure = loads_canonical_json(v144r2_failure_raw)
    if (
        canonical_json_bytes(registration) != v144r2_preregistration_raw
        or len(v144r2_preregistration_raw) != V144R2_PREREGISTRATION_BYTE_COUNT
        or hashlib.sha256(v144r2_preregistration_raw).hexdigest()
        != V144R2_PREREGISTRATION_SHA256
        or registration.get("preregistration_id") != V144R2_PREREGISTRATION_ID
        or canonical_json_bytes(campaign) != v144r2_campaign_raw
        or len(v144r2_campaign_raw) != V144R2_CAMPAIGN_BYTE_COUNT
        or hashlib.sha256(v144r2_campaign_raw).hexdigest() != V144R2_CAMPAIGN_SHA256
        or campaign.get("campaign_id") != V144R2_CAMPAIGN_ID
        or campaign.get("registered_gate", {}).get("passed") is not False
        or campaign.get("accounting", {}).get(
            "occurrence_factor_bank_update_prior_certificate_local_labels"
        )
        + campaign.get("accounting", {}).get(
            "strict_no_prior_certificate_local_labels"
        )
        != 79
        or canonical_json_bytes(failure) != v144r2_failure_raw
        or len(v144r2_failure_raw) != V144R2_FAILURE_BYTE_COUNT
        or hashlib.sha256(v144r2_failure_raw).hexdigest() != V144R2_FAILURE_SHA256
        or failure.get("campaign_id") != V144R2_CAMPAIGN_ID
        or failure.get("same_identity_rerun_forbidden") is not True
    ):
        _fail("V145 frozen V144R2 predecessor or failure changed")
    source_facts = _source_facts()
    expected = [
        {"relative_path": path, "byte_count": count, "sha256": digest}
        for path, count, digest in FROZEN_SOURCE_FACTS
    ]
    if source_facts != expected:
        _fail("V145 frozen implementation source changed")
    config = campaign_config_v145()
    payload = {
        "schema": "acfqp.certificate_local_recovery_union_preregistration.v145",
        "implementation_commits": list(IMPLEMENTATION_COMMITS),
        "frozen_implementation_source_facts": source_facts,
        "frozen_v144r2_preregistration": registration,
        "preserved_v144r2_failed_campaign_identity": {
            "campaign_id": V144R2_CAMPAIGN_ID,
            "byte_count": V144R2_CAMPAIGN_BYTE_COUNT,
            "sha256": V144R2_CAMPAIGN_SHA256,
        },
        "frozen_v144r2_failure": failure,
        "gate_correction_rationale": {
            "v144r2_certificate_failure_local_ground_labels": 79,
            "v144r2_query_local_exact_overlay_edges": 0,
            "program_compatible_incremental_refinement_is_sound_local_recovery": True,
            "exact_overlay_is_reserved_for_program_incompatible_rows": True,
            "requiring_both_branches_was_stricter_than_the_main_claim": True,
        },
        "target_occurrences": config["target_occurrences"],
        "target_episode_indices": list(config["target_episode_indices"]),
        "target_worker_count": config["target_worker_count"],
        "required_target_occurrence_count": config["required_target_occurrence_count"],
        "maximum_acquisition_labels": MAXIMUM_ACQUISITION_LABELS,
        "registered_gate": {
            "v144r2_failure_and_complete_campaign_preserved": True,
            "v144r2_identity_not_rerun": True,
            "fresh_target_occurrence_identities": True,
            "same_v144r1_algorithm_without_outcome_adaptive_change": True,
            "certificate_failure_local_recovery_must_be_exercised": True,
            "either_program_compatible_refinement_or_exact_overlay_is_admissible": True,
            "exact_overlay_branch_exercise_required": False,
            "source_partial_program_remains_immutable": True,
            "overlay_not_promoted_to_global_dynamics": True,
            "overlay_not_used_as_safety_authority": True,
            "same_synthesizer_and_stop_rule_both_arms": True,
            "only_arm_switch_is_normalized_factor_prior": True,
            "aggregate_positive_reduction_is_primary_gate": True,
            "zero_and_negative_occurrences_must_be_preserved": True,
            "all_four_receding_episodes_required": True,
            "strict_incompatible_schema_no_transfer_required": True,
            "producer_free_verification_required": True,
        },
        "claim_boundary": {
            "target_outcomes_accessed": False,
            "registered_v145_target_outcome_observed": False,
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
        "preregistration_id": domains.extension_content_id_v145(
            domains.CONSTRUCTION_K7_CERTIFICATE_LOCAL_RECOVERY_UNION_PREREGISTRATION_V145_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class CertificateLocalRecoveryUnionPreregistrationV145:
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
            or domains.extension_content_id_v145(
                domains.CONSTRUCTION_K7_CERTIFICATE_LOCAL_RECOVERY_UNION_PREREGISTRATION_V145_DOMAIN,
                payload,
            )
            != self.preregistration_id
        ):
            _fail("V145 preregistration bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


def freeze_certificate_local_recovery_union_preregistration_v145(
    v144r2_preregistration_raw: bytes,
    v144r2_campaign_raw: bytes,
    v144r2_failure_raw: bytes,
) -> CertificateLocalRecoveryUnionPreregistrationV145:
    document = _document(
        v144r2_preregistration_raw, v144r2_campaign_raw, v144r2_failure_raw
    )
    raw = canonical_json_bytes(document)
    identity = document["preregistration_id"]
    if PREREGISTRATION_ID != "0" * 64 and (
        identity != PREREGISTRATION_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("V145 frozen preregistration changed")
    return CertificateLocalRecoveryUnionPreregistrationV145(_ISSUER, raw, identity)


__all__ = (
    "PREREGISTRATION_ID",
    "campaign_config_v145",
    "freeze_certificate_local_recovery_union_preregistration_v145",
)
