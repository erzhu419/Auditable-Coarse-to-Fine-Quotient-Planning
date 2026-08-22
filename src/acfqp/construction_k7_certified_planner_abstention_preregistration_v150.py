"""Outcome-free V150 preregistration after the preserved V149 failure."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v150 as domains
from acfqp.generic_dual_budget_adapter_v119 import FAMILY as DUAL
from acfqp.generic_inventory_assembly_adapter_v118 import FAMILY as INVENTORY
from acfqp.generic_modular_routing_adapter_v128 import FAMILY as MODULAR
from acfqp.generic_packet_batching_adapter_v134 import (
    FAMILY as PACKET,
    packet_batching_config_v134,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


IMPLEMENTATION_COMMITS = ("ea69638c196c5b18c90903fadc92a21ce878d3f5",)
PREREGISTRATION_ID = "947179ea88496be6188b04e80fe7b9f3184f16864e1448d19e240fb6fba83d7c"
EXPECTED_CANONICAL_BYTE_COUNT = 14_290
EXPECTED_CANONICAL_SHA256 = "f0bee6ac66112e033211d00e14b676f4e546a506268acc5ff631f6e651d3554f"
V149_PREREGISTRATION_ID = "0ab10d76752bf5a6aeea1341386015627debe3e1009c2780fa0dbbbc2d164cb3"
V149_PREREGISTRATION_BYTE_COUNT = 8_807
V149_PREREGISTRATION_SHA256 = "3f938c6d42ed0508502534047ed52eee76f5b67267b6bb9700b4dfb282f612ae"
V149_FAILURE_BYTE_COUNT = 1_708
V149_FAILURE_SHA256 = "0ad197ecd213fa53467ff7252b61e5d750dbc27d675fdf0d5fd8c242ab22458d"
TARGET_OCCURRENCES = (
    (INVENTORY, 1_047_351),
    (INVENTORY, 1_047_352),
    (DUAL, 1_047_353),
    (DUAL, 1_047_354),
    (MODULAR, 1_047_355),
    (MODULAR, 1_047_356),
    (PACKET, 1_047_357),
    (PACKET, 1_047_358),
)
TARGET_EPISODE_INDICES = (571, 572, 573, 574)
TARGET_WORKER_COUNT = 2
REQUIRED_TARGET_OCCURRENCE_COUNT = 8
MAXIMUM_ACQUISITION_LABELS = 1_536
SOURCE_ROOT = Path(__file__).resolve().parents[2]
FROZEN_SOURCE_FACTS = (
    (
        "src/acfqp/construction_k7_domain_registry_extension_v150.py",
        1_545,
        "8ab61023769efde8ce673d6771b151449af48c490de15ba9dda60aa0df6d567b",
    ),
    (
        "src/acfqp/certified_planner_abstention_sequence_v150.py",
        3_595,
        "51b83c5e91b47761211487b74ae2d901527a07519c6796cccbd961c7b7d4a01b",
    ),
    (
        "src/acfqp/cross_domain_relational_factor_bank_campaign_core_v150.py",
        3_946,
        "cc1b363615f4af68d17a028369020bd888988ebfaa30030be351e622c129f129",
    ),
    (
        "src/acfqp/cross_domain_relational_factor_bank_campaign_core_v149.py",
        15_468,
        "6759f91c3508857dafb00ee6a2b565f4a7f93d05c1790b2e0ffc1bf49875a9a4",
    ),
    (
        "src/acfqp/certificate_local_relational_overlay_sequence_v144r1.py",
        21_798,
        "aa8241ca383854b8e75b1c251746f8828d5a848e0b95486e5fd65bebe3056dab",
    ),
    (
        "src/acfqp/standalone_generic_owned_sequence_v126.py",
        27_341,
        "66bdb98e9b4ce4994a2a2198bbadbe268aca59e5f5219e24e71ab3e77cc09a4a",
    ),
)


class ConstructionK7CertifiedPlannerAbstentionPreregistrationV150Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7CertifiedPlannerAbstentionPreregistrationV150Error(message)


def campaign_config_v150() -> dict[str, Any]:
    config = packet_batching_config_v134()
    for family in (INVENTORY, DUAL, MODULAR, PACKET):
        config["families"][family]["maximum_acquisition_labels"] = (
            MAXIMUM_ACQUISITION_LABELS
        )
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


def _document(v149_preregistration_raw: bytes, v149_failure_raw: bytes) -> dict[str, Any]:
    predecessor = loads_canonical_json(v149_preregistration_raw)
    failure = loads_canonical_json(v149_failure_raw)
    if (
        canonical_json_bytes(predecessor) != v149_preregistration_raw
        or len(v149_preregistration_raw) != V149_PREREGISTRATION_BYTE_COUNT
        or hashlib.sha256(v149_preregistration_raw).hexdigest()
        != V149_PREREGISTRATION_SHA256
        or predecessor.get("preregistration_id") != V149_PREREGISTRATION_ID
        or predecessor.get("claim_boundary", {}).get("target_outcomes_accessed")
        is not False
        or canonical_json_bytes(failure) != v149_failure_raw
        or len(v149_failure_raw) != V149_FAILURE_BYTE_COUNT
        or hashlib.sha256(v149_failure_raw).hexdigest() != V149_FAILURE_SHA256
        or failure.get("preregistration_id") != V149_PREREGISTRATION_ID
        or failure.get("outcome_kind")
        != "PREREGISTERED_PLANNER_ACTION_PATH_FAILURE"
        or failure.get("error_type")
        != "CertificateLocalRelationalOverlaySequenceV144R1Error"
        or failure.get("error_message") != "V126 planner action path changed"
        or failure.get("same_identity_rerun_forbidden") is not True
        or failure.get("partial_campaign_artifact_present") is not False
    ):
        _fail("V150 frozen V149 preregistration or failure changed")
    source_facts = _source_facts()
    expected = [
        {"relative_path": path, "byte_count": count, "sha256": digest}
        for path, count, digest in FROZEN_SOURCE_FACTS
    ]
    if source_facts != expected:
        _fail("V150 frozen implementation source changed")
    config = campaign_config_v150()
    payload = {
        "schema": "acfqp.certified_planner_abstention_preregistration.v150",
        "implementation_commits": list(IMPLEMENTATION_COMMITS),
        "frozen_implementation_source_facts": source_facts,
        "frozen_v149_preregistration": predecessor,
        "frozen_v149_failure": failure,
        "correction": {
            "failure_boundary": "INCOMPLETE_ABSTRACT_ACTION_PATH",
            "old_behavior": "LOCAL_EXCEPTION_ESCAPED_ABSTENTION_BOUNDARY",
            "new_behavior": "ABSTRACT_ORDERER_ABSTAINS_AND_CERTIFICATE_LAYER_DECIDES",
            "incomplete_abstract_path_used_as_execution_authority": False,
            "v149_identity_rerun": False,
        },
        "target_occurrences": config["target_occurrences"],
        "target_episode_indices": list(config["target_episode_indices"]),
        "target_worker_count": config["target_worker_count"],
        "required_target_occurrence_count": config[
            "required_target_occurrence_count"
        ],
        "maximum_acquisition_labels": MAXIMUM_ACQUISITION_LABELS,
        "registered_gate": {
            "v149_preregistration_and_failure_preserved": True,
            "v149_identity_not_rerun": True,
            "fresh_target_occurrence_identities": True,
            "four_source_unseen_structural_families_required": True,
            "same_witness_blind_raw_transition_stream_both_arms": True,
            "same_anonymous_binding_and_atomic_hypothesis_pool_both_arms": True,
            "same_candidate_carrier_replay_and_stop_rule_both_arms": True,
            "only_arm_switch_is_anonymous_factor_bank_codelength": True,
            "incomplete_abstract_path_must_abstain_not_fail_or_execute": True,
            "relational_instantiation_must_be_present_both_arms": True,
            "relational_template_selection_itself_is_not_primary_gate": True,
            "aggregate_and_each_family_positive_reduction_required": True,
            "zero_and_negative_occurrences_must_be_preserved": True,
            "all_four_receding_episodes_required": True,
            "certificate_failure_local_recovery_must_be_exercised": True,
            "strict_incompatible_schema_no_transfer_required": True,
            "producer_free_verification_required": True,
            "frozen_two_worker_resource_schedule": True,
        },
        "claim_boundary": {
            "target_outcomes_accessed": False,
            "registered_v150_target_outcome_observed": False,
            "cross_domain_relational_template_selection_claimed": False,
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
        "preregistration_id": domains.extension_content_id_v150(
            domains.CONSTRUCTION_K7_PREREGISTRATION_V150_DOMAIN, payload
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class CertifiedPlannerAbstentionPreregistrationV150:
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
            or domains.extension_content_id_v150(
                domains.CONSTRUCTION_K7_PREREGISTRATION_V150_DOMAIN, payload
            )
            != self.preregistration_id
        ):
            _fail("V150 preregistration bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


def freeze_certified_planner_abstention_preregistration_v150(
    v149_preregistration_raw: bytes,
    v149_failure_raw: bytes,
) -> CertifiedPlannerAbstentionPreregistrationV150:
    document = _document(v149_preregistration_raw, v149_failure_raw)
    raw = canonical_json_bytes(document)
    identity = document["preregistration_id"]
    if PREREGISTRATION_ID != "0" * 64 and (
        identity != PREREGISTRATION_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("V150 frozen preregistration changed")
    return CertifiedPlannerAbstentionPreregistrationV150(_ISSUER, raw, identity)


__all__ = (
    "PREREGISTRATION_ID",
    "campaign_config_v150",
    "freeze_certified_planner_abstention_preregistration_v150",
)
