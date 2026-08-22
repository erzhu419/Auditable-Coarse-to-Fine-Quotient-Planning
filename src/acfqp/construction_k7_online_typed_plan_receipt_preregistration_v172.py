"""Outcome-free preregistration for the V172 online receipt campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v172 as domains
from acfqp.online_typed_plan_receipt_campaign_core_v172 import (
    RESERVOIR_DISPATCH_FAMILY,
    online_typed_plan_receipt_campaign_config_v172,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


IMPLEMENTATION_COMMITS = ("cb6256b", "c9db58e", "2aeec9f")
TARGET_OCCURRENCES = (
    (RESERVOIR_DISPATCH_FAMILY, 1_069_851),
    (RESERVOIR_DISPATCH_FAMILY, 1_069_852),
)
TARGET_EPISODE_INDICES = (973, 974, 975, 976)
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
        "src/acfqp/construction_k7_domain_registry_extension_v172.py",
        1_730,
        "4609ea35f0155b02eda3df7f2f1706c0c5c1fa572c429e3c4d15cc03ae53e66b",
    ),
    (
        "src/acfqp/online_typed_plan_receipt_sequence_v172.py",
        12_135,
        "87fa0617ba7ff42a52d6cc6195b25c26f3ef7ae31d43e940fd5f9b5f7064931d",
    ),
    (
        "src/acfqp/online_typed_plan_receipt_campaign_core_v172.py",
        15_983,
        "4508937be410f283023751a4ac50e7d505d76eab3dd5efdc9b6983fddc8c3109",
    ),
)
FROZEN_PREDECESSORS = (
    (
        "v171_sixth_family_complete_plan_receipt_campaign.json",
        14_712_225,
        "95b2fb332a5813d83a50b4ba192cc5720e054c009e8af4b3e9ce8c93cf99f76a",
        "campaign_id",
        "ca284948d3d8886025fb13a84cffbab9bb535c242d292a2a68dd194bef4ed463",
    ),
    (
        "v171_sixth_family_complete_plan_receipt_verification.json",
        1_894,
        "a668ce94f507b62a22c85bdc8c569d39991394a29687069a531c8ac90138014c",
        "verification_id",
        "422770529178614103624e873a5a1aaf732df6b949fe0bfe50edad3ad2fb78d0",
    ),
)
PREREGISTRATION_ID = "4240c6d1d44e9c704e41d9a21cf54c43475af9f8938bc1a8eb2128341cdcb375"
EXPECTED_CANONICAL_BYTE_COUNT = 3_235
EXPECTED_CANONICAL_SHA256 = "71930a312698c615b50155ed2603fe6537f84d06a4874e9502278a1273248ac8"


class ConstructionK7OnlineTypedPlanReceiptPreregistrationV172Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7OnlineTypedPlanReceiptPreregistrationV172Error(message)


def campaign_config_v172():
    config = online_typed_plan_receipt_campaign_config_v172()
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
        _fail(f"V172 frozen predecessor changed: {name}")
    return document


def build_online_typed_plan_receipt_preregistration_v172():
    source_facts = []
    for path, count, digest in FROZEN_SOURCE_FACTS:
        raw = (ROOT / path).read_bytes()
        if len(raw) != count or hashlib.sha256(raw).hexdigest() != digest:
            _fail(f"V172 implementation changed before target outcomes: {path}")
        source_facts.append(
            {"relative_path": path, "byte_count": count, "sha256": digest}
        )
    predecessors = [_frozen_predecessor(row) for row in FROZEN_PREDECESSORS]
    if not (
        predecessors[0]["registered_gate"]["passed"] is True
        and predecessors[1]["producer_free_target_outcome_reexecution"]
        is True
        and predecessors[1][
            "factor_prior_strict_sample_tax_reduction_independently_verified"
        ]
        is True
    ):
        _fail("V172 predecessor gate changed")
    config = campaign_config_v172()
    payload = {
        "schema": "acfqp.online_typed_plan_receipt_preregistration.v172",
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
        "registered_gate": {
            "fresh_target_identities_fixed_before_target_outcomes": True,
            "each_abstract_plan_receipt_issued_before_orderer_return_required": True,
            "each_executed_action_joined_to_prior_online_receipt_required": True,
            "complete_four_source_online_taxonomy_required": True,
            "delegate_plan_byte_identity_required": True,
            "same_synthesizer_and_stop_rule_both_arms_required": True,
            "factor_prior_strict_acquisition_label_reduction_each_occurrence_required": True,
            "query_policy_noninferiority_each_occurrence_required": True,
            "both_arm_receding_planning_success_required": True,
            "certificate_failure_only_local_ground_distinctions_required": True,
            "producer_free_reconstruction_required": True,
            "sample_execution_derivation_planning_and_receipt_axes_separate": True,
            "frozen_two_worker_resource_schedule": True,
        },
        "claim_boundary": {
            "target_outcomes_accessed": False,
            "online_typed_receipt_taxonomy_observed": False,
            "factor_prior_sample_tax_reduction_observed": False,
            "online_receipt_is_model_or_safety_authority": False,
            "query_local_exact_overlay_remains_only_safety_authority": True,
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
        "preregistration_id": domains.extension_content_id_v172(
            domains.CONSTRUCTION_K7_TARGET_PREREGISTRATION_V172_DOMAIN, payload
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class OnlineTypedPlanReceiptPreregistrationV172:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


def freeze_online_typed_plan_receipt_preregistration_v172():
    document = build_online_typed_plan_receipt_preregistration_v172()
    raw = canonical_json_bytes(document)
    if PREREGISTRATION_ID != "0" * 64 and not (
        document["preregistration_id"] == PREREGISTRATION_ID
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    ):
        _fail("V172 frozen target preregistration changed")
    return OnlineTypedPlanReceiptPreregistrationV172(
        _ISSUER, raw, document["preregistration_id"]
    )


__all__ = (
    "PREREGISTRATION_ID",
    "TARGET_OCCURRENCES",
    "campaign_config_v172",
    "freeze_online_typed_plan_receipt_preregistration_v172",
)
