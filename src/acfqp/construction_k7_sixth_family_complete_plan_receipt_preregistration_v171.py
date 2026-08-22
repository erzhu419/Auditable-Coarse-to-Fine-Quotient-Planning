"""Outcome-free preregistration for the V171 sixth-family campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v171 as domains
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp.sixth_family_complete_plan_receipt_campaign_core_v171 import (
    RESERVOIR_DISPATCH_FAMILY,
    sixth_family_complete_plan_receipt_campaign_config_v171,
)


IMPLEMENTATION_COMMITS = ("8318ac9", "4089929")
TARGET_OCCURRENCES = (
    (RESERVOIR_DISPATCH_FAMILY, 1_059_851),
    (RESERVOIR_DISPATCH_FAMILY, 1_059_852),
)
TARGET_EPISODE_INDICES = (963, 964, 965, 966)
TARGET_WORKER_COUNT = 2
REQUIRED_TARGET_OCCURRENCE_COUNT = 2
ROOT = Path(__file__).resolve().parents[2]
FROZEN_SOURCE_FACTS = (
    (
        "src/acfqp/domains/stochastic_reservoir_dispatch.py",
        10_289,
        "c9ce8849213f5f198959c15c8808aa30912d58bd9ef1a3019bfada767a5011bf",
    ),
    (
        "src/acfqp/generic_reservoir_dispatch_adapter_v171.py",
        4_332,
        "d3df34f07529022157ebccbbea63754ce3d0d850d1ba79fdf6b9d82a74ee7865",
    ),
    (
        "src/acfqp/construction_k7_domain_registry_extension_v171.py",
        1_783,
        "9111929c6d0b14712b1aca0926b249a187faa963760887c6923501a4cefb498e",
    ),
    (
        "src/acfqp/complete_plan_receipt_taxonomy_sequence_v171.py",
        11_662,
        "f0dfabdc884fe71c14f6af276ce2fc2db81570422b5b064ab275316b37e39657",
    ),
    (
        "src/acfqp/sixth_family_complete_plan_receipt_campaign_core_v171.py",
        16_086,
        "b4d0c6d605169c5d5611fcd0b249ec81b7730036fd36660dc7b7dbbbe51f35ec",
    ),
)
FROZEN_PREDECESSORS = (
    (
        "v168_fifth_family_total_plan_receipt_set_campaign.json",
        25_586_483,
        "e0cd4d36fb72bf79519878e1a368aeecf128cd91c4571bf0071d68af2760dfa5",
        "campaign_id",
        "447f04fb450a9b76083993593a66ef717431f0b814212927ff2adfa1e27e4dce",
    ),
    (
        "v168_fifth_family_total_plan_receipt_set_verification.json",
        10_215,
        "ecf1c0d10fc9cedc508353425cbf2c93533a52cbd2b07af2076eb5b9161cbc09",
        "verification_id",
        "11378538ea1d8340647b9e172f34c7e6f427a1d177a045074e596329c2cb8908",
    ),
    (
        "v170_complete_abstract_plan_receipt_taxonomy_contract.json",
        2_820,
        "f527daa87f4389bfedd501ccb1eba21066413457bef1904abbaa5a7fec751575",
        "contract_id",
        "bb751f90d592f289cfcf1c00041a6b1f0579dc95c93a01b76a0598f0c2a0ae66",
    ),
    (
        "v170_complete_abstract_plan_receipt_taxonomy_audit.json",
        1_193_174,
        "24e90f4af2da248de54c233931f7d6aefcc89eeb3b1c3b6a8ac3fe5cd81599a2",
        "audit_id",
        "0372043e8d6a3277070488777e3f0dc5f33702abb2b72a8fcabc12a60dd35944",
    ),
    (
        "v170_complete_abstract_plan_receipt_taxonomy_verification.json",
        1_537,
        "a4bcb3aff4f465a66c6dabd06c6427871d6418e027258d6fe9bde0da2a0541c3",
        "verification_id",
        "f9b7570d565cb160d80aafadd9d4bcf49abdcb7879d782c597fd9f955cfa4217",
    ),
)
PREREGISTRATION_ID = "4c1047ed0b55077150f2bb7433f644525a380ba65650c78ab3ec11228fa0bc73"
EXPECTED_CANONICAL_BYTE_COUNT = 4_279
EXPECTED_CANONICAL_SHA256 = (
    "508da1b214c972f798da66754bf72990810ff469f6daa56951b4ca6abd97abd0"
)


class ConstructionK7SixthFamilyCompletePlanReceiptPreregistrationV171Error(
    ValueError
):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7SixthFamilyCompletePlanReceiptPreregistrationV171Error(
        message
    )


def campaign_config_v171():
    config = sixth_family_complete_plan_receipt_campaign_config_v171()
    config.update(
        target_occurrences=[
            {"family": family, "seed": seed} for family, seed in TARGET_OCCURRENCES
        ],
        target_episode_indices=TARGET_EPISODE_INDICES,
        target_worker_count=TARGET_WORKER_COUNT,
        required_target_occurrence_count=REQUIRED_TARGET_OCCURRENCE_COUNT,
    )
    return config


def _frozen_predecessor(row):
    name, count, digest, identity_key, identity = row
    raw = (ROOT / ".tmp/exact-freeze" / name).read_bytes()
    document = loads_canonical_json(raw)
    if not (
        canonical_json_bytes(document) == raw
        and len(raw) == count
        and hashlib.sha256(raw).hexdigest() == digest
        and document.get(identity_key) == identity
    ):
        _fail(f"V171 frozen predecessor changed: {name}")
    return document


def build_sixth_family_complete_plan_receipt_preregistration_v171():
    source_facts = []
    for path, count, digest in FROZEN_SOURCE_FACTS:
        raw = (ROOT / path).read_bytes()
        if len(raw) != count or hashlib.sha256(raw).hexdigest() != digest:
            _fail(f"V171 implementation changed before target outcomes: {path}")
        source_facts.append(
            {"relative_path": path, "byte_count": count, "sha256": digest}
        )
    predecessors = [
        _frozen_predecessor(row) for row in FROZEN_PREDECESSORS
    ]
    if not (
        predecessors[0]["registered_gate"]["passed"] is True
        and predecessors[1][
            "fifth_family_factor_prior_sample_tax_transfer_independently_verified"
        ]
        is True
        and predecessors[3]["registered_gate"]["passed"] is True
        and predecessors[4]["producer_free_every_plan_instance_reconstructed"]
        is True
        and predecessors[4]["producer_free_every_execution_join_reconstructed"]
        is True
    ):
        _fail("V171 predecessor gate changed")
    config = campaign_config_v171()
    payload = {
        "schema": "acfqp.sixth_family_complete_plan_receipt_preregistration.v171",
        "implementation_commits": list(IMPLEMENTATION_COMMITS),
        "frozen_implementation_source_facts": source_facts,
        "frozen_predecessors": [
            {
                "name": row[0],
                "byte_count": row[1],
                "sha256": row[2],
                row[3]: row[4],
            }
            for row in FROZEN_PREDECESSORS
        ],
        "target_occurrences": [
            {"family": family, "seed": seed} for family, seed in TARGET_OCCURRENCES
        ],
        "target_episode_indices": list(TARGET_EPISODE_INDICES),
        "target_worker_count": TARGET_WORKER_COUNT,
        "required_target_occurrence_count": REQUIRED_TARGET_OCCURRENCE_COUNT,
        "maximum_acquisition_labels": config["families"][
            RESERVOIR_DISPATCH_FAMILY
        ]["maximum_acquisition_labels"],
        "typed_receipt_taxonomy": {
            "source_v170_contract_id": predecessors[2]["contract_id"],
            "source_v170_audit_id": predecessors[3]["audit_id"],
            "source_v170_verification_id": predecessors[4]["verification_id"],
            "every_abstract_plan_instance_must_be_typed": True,
            "every_executed_action_must_have_unique_typed_plan_join": True,
            "unknown_plan_source_is_failure": True,
            "taxonomy_changes_planning_or_execution": False,
            "taxonomy_is_model_or_safety_authority": False,
        },
        "registered_gate": {
            "fresh_target_identities_fixed_before_target_outcomes": True,
            "exactly_two_fresh_reservoir_occurrences_required": True,
            "same_synthesizer_and_stop_rule_both_arms_required": True,
            "factor_prior_strict_acquisition_label_reduction_each_occurrence_required": True,
            "query_policy_noninferiority_each_occurrence_required": True,
            "both_arm_receding_planning_success_required": True,
            "certificate_failure_only_local_ground_distinctions_required": True,
            "complete_typed_plan_receipt_taxonomy_required": True,
            "producer_free_reconstruction_required": True,
            "sample_execution_derivation_and_planning_axes_separate": True,
            "frozen_two_worker_resource_schedule": True,
        },
        "claim_boundary": {
            "target_outcomes_accessed": False,
            "v171_sixth_family_transfer_observed": False,
            "v171_sample_tax_reduction_observed": False,
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
        "preregistration_id": domains.extension_content_id_v171(
            domains.CONSTRUCTION_K7_TARGET_PREREGISTRATION_V171_DOMAIN, payload
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class SixthFamilyCompletePlanReceiptPreregistrationV171:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


def freeze_sixth_family_complete_plan_receipt_preregistration_v171():
    document = build_sixth_family_complete_plan_receipt_preregistration_v171()
    raw = canonical_json_bytes(document)
    if PREREGISTRATION_ID != "0" * 64 and not (
        document["preregistration_id"] == PREREGISTRATION_ID
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    ):
        _fail("V171 frozen target preregistration changed")
    return SixthFamilyCompletePlanReceiptPreregistrationV171(
        _ISSUER, raw, document["preregistration_id"]
    )


__all__ = (
    "PREREGISTRATION_ID",
    "TARGET_OCCURRENCES",
    "campaign_config_v171",
    "freeze_sixth_family_complete_plan_receipt_preregistration_v171",
)
