"""Outcome-free preregistration for changed-cardinality relational transfer."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v152 as domains
from acfqp.generic_ternary_relation_workflow_adapter_v152 import FAMILY, ternary_relation_workflow_config_v152
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


IMPLEMENTATION_COMMITS = ("124360f64d2fc7ceb58b35df272fb93272e19ac6",)
PREREGISTRATION_ID = "f5a86041bd92099f03bd87618238e4e1a5345c950e4c0ea221d8f7977a4f60ad"
EXPECTED_CANONICAL_BYTE_COUNT = 3_479
EXPECTED_CANONICAL_SHA256 = "1910e0c4da868166c7fac2d63717ffc537d9c19ada61d9a5c3e2343ef703c5a2"
V151_CAMPAIGN_ID = "da305e55c00ff69b3aa240f2536a511eec6d6c3ee07f1418f80281f9ffa64cb0"
V151_CAMPAIGN_BYTE_COUNT = 25_536_677
V151_CAMPAIGN_SHA256 = "df3c508a7aa9fb8b0fecebb07530b21288818ebf993cf2e1f8b4407e79568a68"
V151_VERIFICATION_ID = "a57a8075fa7edd59bbefa9555a9457403374ca9c69600f6f305efab6442efd35"
V151_VERIFICATION_BYTE_COUNT = 12_585
V151_VERIFICATION_SHA256 = "6d1597be009be60ab50381146267367cd35c57811845d10a1c9270cdf395c813"
TARGET_OCCURRENCES = tuple((FAMILY, seed) for seed in range(1_047_391, 1_047_397))
TARGET_EPISODE_INDICES = (621, 622, 623, 624)
TARGET_WORKER_COUNT = 2
REQUIRED_TARGET_OCCURRENCE_COUNT = 6
MAXIMUM_ACQUISITION_LABELS = 1_536
SOURCE_ROOT = Path(__file__).resolve().parents[2]
FROZEN_SOURCE_FACTS = (
    ("src/acfqp/construction_k7_domain_registry_extension_v152.py", 1_450, "8e77ca70ef471589110ed187a4667fae624d2f52e486b074acf68d590e3bf913"),
    ("src/acfqp/domains/stochastic_ternary_relation_workflow_v152.py", 3_078, "6b5df6861bbc136a14071244e782712ad3583a9b3689711757b089729fb216ff"),
    ("src/acfqp/generic_ternary_relation_workflow_adapter_v152.py", 4_250, "63c9be44a74569f665048393bc720231880787d7bae580ad29dcca25bb3e1030"),
    ("src/acfqp/ternary_relational_transfer_campaign_core_v152.py", 4_648, "4bf8522f03f7e1240d7d8f8b537b25afb85b0b8e99842bbb1de46e9f4b90eadc"),
    ("src/acfqp/certified_planner_abstention_sequence_v150.py", 3_595, "51b83c5e91b47761211487b74ae2d901527a07519c6796cccbd961c7b7d4a01b"),
    ("src/acfqp/cross_domain_relational_factor_bank_campaign_core_v149.py", 15_468, "6759f91c3508857dafb00ee6a2b565f4a7f93d05c1790b2e0ffc1bf49875a9a4"),
)


class ConstructionK7TernaryRelationalTransferPreregistrationV152Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7TernaryRelationalTransferPreregistrationV152Error(message)


def campaign_config_v152() -> dict[str, Any]:
    config = ternary_relation_workflow_config_v152()
    config["families"][FAMILY]["maximum_acquisition_labels"] = MAXIMUM_ACQUISITION_LABELS
    config.update(
        target_occurrences=[{"family": family, "seed": seed} for family, seed in TARGET_OCCURRENCES],
        target_episode_indices=TARGET_EPISODE_INDICES,
        target_worker_count=TARGET_WORKER_COUNT,
        required_target_occurrence_count=REQUIRED_TARGET_OCCURRENCE_COUNT,
    )
    return config


def _source_facts():
    return [
        {"relative_path": path, "byte_count": len(raw := (SOURCE_ROOT / path).read_bytes()), "sha256": hashlib.sha256(raw).hexdigest()}
        for path, _count, _digest in FROZEN_SOURCE_FACTS
    ]


def _predecessor_facts(campaign_raw: bytes, verification_raw: bytes):
    campaign = loads_canonical_json(campaign_raw)
    verification = loads_canonical_json(verification_raw)
    if (
        canonical_json_bytes(campaign) != campaign_raw
        or len(campaign_raw) != V151_CAMPAIGN_BYTE_COUNT
        or hashlib.sha256(campaign_raw).hexdigest() != V151_CAMPAIGN_SHA256
        or campaign.get("campaign_id") != V151_CAMPAIGN_ID
        or campaign.get("registered_gate", {}).get("passed") is not True
        or campaign.get("relational_template_selection_itself_claimed_cross_domain") is not True
        or canonical_json_bytes(verification) != verification_raw
        or len(verification_raw) != V151_VERIFICATION_BYTE_COUNT
        or hashlib.sha256(verification_raw).hexdigest() != V151_VERIFICATION_SHA256
        or verification.get("verification_id") != V151_VERIFICATION_ID
        or verification.get("registered_relation_keyed_sample_efficiency_improvement_independently_verified") is not True
        or verification.get("official_scalar_cost") is not None
    ):
        _fail("V152 frozen V151 predecessor changed")
    return {
        "v151_campaign_id": V151_CAMPAIGN_ID,
        "v151_campaign_byte_count": V151_CAMPAIGN_BYTE_COUNT,
        "v151_campaign_sha256": V151_CAMPAIGN_SHA256,
        "v151_verification_id": V151_VERIFICATION_ID,
        "v151_verification_byte_count": V151_VERIFICATION_BYTE_COUNT,
        "v151_verification_sha256": V151_VERIFICATION_SHA256,
    }


def _document(campaign_raw: bytes, verification_raw: bytes):
    source_facts = _source_facts()
    if source_facts != [
        {"relative_path": path, "byte_count": count, "sha256": digest}
        for path, count, digest in FROZEN_SOURCE_FACTS
    ]:
        _fail("V152 frozen implementation source changed")
    config = campaign_config_v152()
    payload = {
        "schema": "acfqp.ternary_relational_transfer_preregistration.v152",
        "implementation_commits": list(IMPLEMENTATION_COMMITS),
        "frozen_implementation_source_facts": source_facts,
        "frozen_v151_predecessor": _predecessor_facts(campaign_raw, verification_raw),
        "target_occurrences": config["target_occurrences"],
        "target_episode_indices": list(config["target_episode_indices"]),
        "target_worker_count": TARGET_WORKER_COUNT,
        "required_target_occurrence_count": REQUIRED_TARGET_OCCURRENCE_COUNT,
        "maximum_acquisition_labels": MAXIMUM_ACQUISITION_LABELS,
        "registered_gate": {
            "fresh_ternary_relation_target_identities": True,
            "two_key_source_to_three_key_target_required": True,
            "target_relation_binding_must_be_observation_derived": True,
            "relation_cardinality_must_not_be_supplied_by_prior": True,
            "same_raw_stream_synthesizer_and_stop_rule_both_arms": True,
            "only_arm_switch_is_relational_factor_bank_codelength": True,
            "relational_artifact_selected_in_every_prior_arm": True,
            "aggregate_positive_label_reduction_required": True,
            "both_arm_receding_planning_and_certificate_recovery_required": True,
            "strict_incompatible_schema_no_transfer_required": True,
            "producer_free_verification_required": True,
            "frozen_two_worker_resource_schedule": True,
        },
        "claim_boundary": {
            "target_outcomes_accessed": False,
            "changed_cardinality_transfer_observed": False,
            "complete_world_model_claimed": False,
            "arbitrary_relation_cardinality_claimed": False,
            "arbitrary_unseen_domain_transfer_claimed": False,
            "official_execution_allowed": False,
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
            "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        },
    }
    return {**payload, "preregistration_id": domains.extension_content_id_v152(domains.CONSTRUCTION_K7_PREREGISTRATION_V152_DOMAIN, payload)}


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class TernaryRelationalTransferPreregistrationV152:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str

    def __post_init__(self):
        document = loads_canonical_json(self.canonical_bytes)
        payload = {key: value for key, value in document.items() if key != "preregistration_id"}
        if self._issuer is not _ISSUER or canonical_json_bytes(document) != self.canonical_bytes or document.get("preregistration_id") != self.preregistration_id or domains.extension_content_id_v152(domains.CONSTRUCTION_K7_PREREGISTRATION_V152_DOMAIN, payload) != self.preregistration_id:
            _fail("V152 preregistration bytes or issuer changed")

    def to_document(self):
        return loads_canonical_json(self.canonical_bytes)


def freeze_ternary_relational_transfer_preregistration_v152(campaign_raw: bytes, verification_raw: bytes):
    document = _document(campaign_raw, verification_raw)
    raw = canonical_json_bytes(document)
    identity = document["preregistration_id"]
    if PREREGISTRATION_ID != "0" * 64 and (identity != PREREGISTRATION_ID or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256):
        _fail("V152 frozen preregistration changed")
    return TernaryRelationalTransferPreregistrationV152(_ISSUER, raw, identity)


__all__ = ("PREREGISTRATION_ID", "campaign_config_v152", "freeze_ternary_relational_transfer_preregistration_v152")
