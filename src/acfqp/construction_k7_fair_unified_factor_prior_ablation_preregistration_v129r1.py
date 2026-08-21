"""Outcome-free preregistration for the fair V129r1 sample-tax successor."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v129r1 as domains
from acfqp import construction_k7_unified_factor_prior_ablation_preregistration_v129 as failed_pre
from acfqp.construction_k7_third_family_owned_sequence_campaign_v128 import (
    CAMPAIGN_ID as V128_CAMPAIGN_ID,
    EXPECTED_CANONICAL_BYTE_COUNT as V128_CAMPAIGN_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256 as V128_CAMPAIGN_SHA256,
)
from acfqp.construction_k7_third_family_owned_sequence_independent_verifier_v128 import (
    EXPECTED_CANONICAL_BYTE_COUNT as V128_VERIFICATION_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256 as V128_VERIFICATION_SHA256,
    VERIFICATION_ID as V128_VERIFICATION_ID,
)
from acfqp.generic_artifact_derived_factor_projection_v120 import (
    derive_artifact_factor_projection_v120,
)
from acfqp.generic_dual_budget_adapter_v119 import FAMILY as DUAL
from acfqp.generic_inventory_assembly_adapter_v118 import FAMILY as INVENTORY
from acfqp.generic_modular_routing_adapter_v128 import (
    FAMILY as MODULAR,
    modular_routing_config_v128,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


IMPLEMENTATION_COMMITS = ("ff03f687e56bfbef0c0bc054a16e89a9cf7a0904",)
PREREGISTRATION_ID = "d1565e2058f8640d5d3645205fd789517155928d74531a489d9efd1a419b03ae"
EXPECTED_CANONICAL_BYTE_COUNT = 54_080
EXPECTED_CANONICAL_SHA256 = "d5c11cde6be4febb71412c199a9a5733e825c8909accc2aa54be26c0d0d9ae06"
FAILED_V129_PREREGISTRATION_ID = failed_pre.PREREGISTRATION_ID
FAILED_V129_BYTE_COUNT = 1_674
FAILED_V129_SHA256 = "a778be8fd64f5d77544e1dd8c97593c02f788ab074d62a79500d9336e431c94b"
TARGET_OCCURRENCES = (
    (INVENTORY, 1_045_101),
    (INVENTORY, 1_045_102),
    (DUAL, 1_045_103),
    (DUAL, 1_045_104),
    (MODULAR, 1_045_105),
    (MODULAR, 1_045_106),
)
TARGET_EPISODE_INDICES = (329, 330, 331)
TARGET_WORKER_COUNT = 2
REQUIRED_TARGET_OCCURRENCE_COUNT = 6
MAXIMUM_ACQUISITION_LABELS = 320
REGISTERED_FACTOR_PRIOR_MASS_MULTIPLIER = 8
SOURCE_ROOT = Path(__file__).resolve().parents[2]
FROZEN_SOURCE_FACTS = (
    (
        "src/acfqp/construction_k7_domain_registry_extension_v129r1.py",
        1_717,
        "94071e09f9a88150aa56e9b6e6713bfb61a3125637192451e5b40cfe94fa8999",
    ),
    (
        "src/acfqp/fair_unified_factor_prior_ablation_acquisition_v129r1.py",
        9_700,
        "42918debaaf2b35658a65a7d82b24b3364cab0689369d73cb24c9c5ca6dd39b6",
    ),
    (
        "src/acfqp/fair_unified_factor_prior_ablation_campaign_core_v129r1.py",
        12_601,
        "124e96b196f0cbb457e38599c3f3d31cf3f46c58c9be0de30f547e60eb0d1521",
    ),
    *failed_pre.FROZEN_SOURCE_FACTS,
)


class ConstructionK7FairUnifiedFactorPriorAblationPreregistrationV129R1Error(
    ValueError
):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7FairUnifiedFactorPriorAblationPreregistrationV129R1Error(
        message
    )


def _frozen_source_facts() -> list[dict[str, Any]]:
    return [
        {"relative_path": path, "byte_count": count, "sha256": digest}
        for path, count, digest in FROZEN_SOURCE_FACTS
    ]


def _source_facts() -> list[dict[str, Any]]:
    facts = []
    for path, _count, _digest in FROZEN_SOURCE_FACTS:
        raw = (SOURCE_ROOT / path).read_bytes()
        facts.append(
            {
                "relative_path": path,
                "byte_count": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
    return facts


def campaign_config_v129r1() -> dict[str, Any]:
    config = copy.deepcopy(modular_routing_config_v128())
    for family in (INVENTORY, DUAL, MODULAR):
        config["families"][family][
            "maximum_acquisition_labels"
        ] = MAXIMUM_ACQUISITION_LABELS
    config.update(
        target_occurrences=[
            {"family": family, "seed": seed} for family, seed in TARGET_OCCURRENCES
        ],
        target_episode_indices=TARGET_EPISODE_INDICES,
        target_worker_count=TARGET_WORKER_COUNT,
        required_target_occurrence_count=REQUIRED_TARGET_OCCURRENCE_COUNT,
    )
    return config


def _document(
    source_campaign_bytes: Mapping[str, bytes],
    v128_campaign_raw: bytes,
    v128_verification_raw: bytes,
    failed_v129_raw: bytes,
) -> dict[str, Any]:
    campaign = loads_canonical_json(v128_campaign_raw)
    verification = loads_canonical_json(v128_verification_raw)
    failure = json.loads(failed_v129_raw)
    if (
        len(v128_campaign_raw) != V128_CAMPAIGN_BYTE_COUNT
        or hashlib.sha256(v128_campaign_raw).hexdigest() != V128_CAMPAIGN_SHA256
        or campaign.get("campaign_id") != V128_CAMPAIGN_ID
        or campaign.get("registered_gate", {}).get("passed") is not True
        or len(v128_verification_raw) != V128_VERIFICATION_BYTE_COUNT
        or hashlib.sha256(v128_verification_raw).hexdigest()
        != V128_VERIFICATION_SHA256
        or verification.get("verification_id") != V128_VERIFICATION_ID
        or verification.get("registered_gate_independently_verified") is not True
    ):
        _fail("V129r1 frozen V128 predecessor changed")
    if (
        len(failed_v129_raw) != FAILED_V129_BYTE_COUNT
        or hashlib.sha256(failed_v129_raw).hexdigest() != FAILED_V129_SHA256
        or failure.get("preregistration_id") != FAILED_V129_PREREGISTRATION_ID
        or failure.get("outcome_kind") != "PREREGISTERED_RESOURCE_CAP_FAILURE"
        or failure.get("same_identity_rerun_forbidden") is not True
        or failure.get("complete_campaign_document_emitted") is not False
        or canonical_json_bytes(failure) != failed_v129_raw.rstrip(b"\n")
    ):
        _fail("V129r1 retained V129 failure changed")
    library = derive_artifact_factor_projection_v120(dict(source_campaign_bytes))
    if (
        len(library["derived_subprograms"]) != 3
        or 2 ** len(library["derived_subprograms"])
        != REGISTERED_FACTOR_PRIOR_MASS_MULTIPLIER
    ):
        _fail("V129r1 registered finite factor-prior mass changed")
    config = campaign_config_v129r1()
    payload = {
        "schema": "acfqp.fair_unified_factor_prior_ablation_preregistration.v129r1",
        "implementation_commits": list(IMPLEMENTATION_COMMITS),
        "frozen_success_predecessor": {
            "v128_campaign_id": V128_CAMPAIGN_ID,
            "v128_campaign_byte_count": V128_CAMPAIGN_BYTE_COUNT,
            "v128_campaign_sha256": V128_CAMPAIGN_SHA256,
            "v128_verification_id": V128_VERIFICATION_ID,
            "v128_verification_byte_count": V128_VERIFICATION_BYTE_COUNT,
            "v128_verification_sha256": V128_VERIFICATION_SHA256,
        },
        "retained_failed_predecessor": {
            "v129_preregistration_id": FAILED_V129_PREREGISTRATION_ID,
            "failure_byte_count": FAILED_V129_BYTE_COUNT,
            "failure_sha256": FAILED_V129_SHA256,
            "same_identity_rerun_forbidden": True,
            "failed_identity_reused_by_v129r1": False,
        },
        "artifact_factor_library": library,
        "artifact_factor_library_id": library["factor_library_id"],
        "source_closure": {
            "source_facts": _frozen_source_facts(),
            "v129r1_domains": dict(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V129R1),
            "frozen_before_any_registered_v129r1_target_outcome": True,
        },
        "identity_contract": {
            "target_occurrences": config["target_occurrences"],
            "target_families": [INVENTORY, DUAL, MODULAR],
            "two_fresh_occurrences_per_family": True,
            "target_seeds_unique": True,
            "target_seeds_not_previously_exposed": True,
            "target_episode_indices": list(TARGET_EPISODE_INDICES),
            "development_identities": [
                {"family": INVENTORY, "seed": 1_030_021},
                {"family": DUAL, "seed": 1_030_023},
                {"family": MODULAR, "seed": 1_030_022},
                {"family": MODULAR, "seed": 1_030_024},
            ],
            "discarded_development_identities_not_reused": [
                1_030_017,
                1_030_018,
                1_030_019,
                1_030_020,
            ],
            "development_identities_excluded_from_registered_gate": True,
        },
        "matched_ablation_contract": {
            "same_fair_witness_blind_path_first_backtracking_policy": True,
            "generation_witness_accessed": False,
            "reachable_frontier_exhaustion_used_as_stopping_input": False,
            "same_raw_transition_prefix_through_common_label": True,
            "same_generic_atomic_hypothesis_pool": True,
            "same_candidate_carrier_and_schema": True,
            "same_candidate_replay_function": True,
            "same_stopping_rule_function": True,
            "only_arm_switch_is_registered_factor_prior": True,
            "registered_factor_prior_mass_multiplier": REGISTERED_FACTOR_PRIOR_MASS_MULTIPLIER,
            "strictly_positive_acquisition_label_reduction_required_in_every_occurrence": True,
        },
        "registered_gate": {
            "required_target_occurrence_count": REQUIRED_TARGET_OCCURRENCE_COUNT,
            "every_occurrence_has_strictly_positive_label_reduction": True,
            "same_synthesizer_representation_and_stop_rule_in_every_occurrence": True,
            "both_arm_receding_episodes_succeed_everywhere": True,
            "strict_incompatible_schema_no_transfer_required": True,
            "all_unfavourable_results_retained": True,
        },
        "resource_schedule": {
            "target_worker_count": TARGET_WORKER_COUNT,
            "maximum_simultaneous_worker_count": TARGET_WORKER_COUNT,
            "maximum_acquisition_labels_per_arm": MAXIMUM_ACQUISITION_LABELS,
            "target_occurrence_count": REQUIRED_TARGET_OCCURRENCE_COUNT,
            "query_episode_count_per_arm": len(TARGET_EPISODE_INDICES),
            "maximum_incremental_certificate_labels_per_episode": 100_000,
        },
        "accounting_contract": {
            "sample_labels_execution_steps_derivation_and_planning_compute_separate": True,
            "unused_resource_headroom_not_counted_as_sample_labels": True,
            "no_scalar_cost_aggregation": True,
        },
        "claim_boundary": {
            "registered_v129r1_target_outcome_observed": False,
            "registered_workload_sample_efficiency_improvement_observed": False,
            "producer_free_verification_present": False,
            "arbitrary_unseen_domain_transfer_claimed": False,
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
        "preregistration_id": domains.extension_content_id_v129r1(
            domains.CONSTRUCTION_K7_FAIR_UNIFIED_FACTOR_PRIOR_ABLATION_PREREGISTRATION_V129R1_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class FairUnifiedFactorPriorAblationPreregistrationV129R1:
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
            or domains.extension_content_id_v129r1(
                domains.CONSTRUCTION_K7_FAIR_UNIFIED_FACTOR_PRIOR_ABLATION_PREREGISTRATION_V129R1_DOMAIN,
                payload,
            )
            != self.preregistration_id
        ):
            _fail("V129r1 preregistration bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


_CACHE: FairUnifiedFactorPriorAblationPreregistrationV129R1 | None = None


def freeze_fair_unified_factor_prior_ablation_preregistration_v129r1(
    source_campaign_bytes: Mapping[str, bytes],
    v128_campaign_raw: bytes,
    v128_verification_raw: bytes,
    failed_v129_raw: bytes,
) -> FairUnifiedFactorPriorAblationPreregistrationV129R1:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if _source_facts() != _frozen_source_facts():
        _fail("V129r1 source closure changed before registration")
    document = _document(
        source_campaign_bytes,
        v128_campaign_raw,
        v128_verification_raw,
        failed_v129_raw,
    )
    raw = canonical_json_bytes(document)
    identity = document["preregistration_id"]
    if PREREGISTRATION_ID != "0" * 64 and (
        identity != PREREGISTRATION_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("V129r1 preregistration changed")
    _CACHE = FairUnifiedFactorPriorAblationPreregistrationV129R1(
        _ISSUER, raw, identity
    )
    return _CACHE


__all__ = (
    "FAILED_V129_PREREGISTRATION_ID",
    "FAILED_V129_SHA256",
    "FROZEN_SOURCE_FACTS",
    "PREREGISTRATION_ID",
    "TARGET_EPISODE_INDICES",
    "TARGET_OCCURRENCES",
    "V128_CAMPAIGN_ID",
    "V128_VERIFICATION_ID",
    "campaign_config_v129r1",
    "freeze_fair_unified_factor_prior_ablation_preregistration_v129r1",
)
