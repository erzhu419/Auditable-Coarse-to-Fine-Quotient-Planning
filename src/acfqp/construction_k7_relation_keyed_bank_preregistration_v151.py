"""Outcome-free V151 preregistration for relation-keyed template selection."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v151 as domains
from acfqp.generic_relation_keyed_workflow_adapter_v151 import (
    FAMILY,
    relation_keyed_workflow_config_v151,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


IMPLEMENTATION_COMMITS = ("e470c33b584d36c20b5856fd54e286ea3560fa48",)
PREREGISTRATION_ID = "78628783f9f922fc4ad866eb341463f68d367e4196e4c82c849e1a45902b148b"
EXPECTED_CANONICAL_BYTE_COUNT = 3_635
EXPECTED_CANONICAL_SHA256 = "86237f02e95663ca69358133237dd0cfe3f6262d57b4f0c8444f1aa1b4a5c486"
V150_CAMPAIGN_ID = "d76a443f781cd6e6f0c19cf7af12de2627cbccb0a719c41f804f41c416b966c9"
V150_CAMPAIGN_BYTE_COUNT = 61_088_428
V150_CAMPAIGN_SHA256 = "00c5bad86cb05825ecc5cc0d7b0fc5dd00119b95c38a8f44eb3b67f6896c66e9"
V150_VERIFICATION_ID = "b7fafe92cc2ae58b7c912f3eaaa400f407ea8908340b8075a4cbbe4e45776f72"
V150_VERIFICATION_BYTE_COUNT = 15_293
V150_VERIFICATION_SHA256 = "c42d69ad3ac086d8c433f1546400dd2e47d94d51e28ffa377d7ce19fefc97f32"
TARGET_OCCURRENCES = tuple((FAMILY, seed) for seed in range(1_047_371, 1_047_377))
TARGET_EPISODE_INDICES = (601, 602, 603, 604)
TARGET_WORKER_COUNT = 2
REQUIRED_TARGET_OCCURRENCE_COUNT = 6
MAXIMUM_ACQUISITION_LABELS = 1_536
SOURCE_ROOT = Path(__file__).resolve().parents[2]
FROZEN_SOURCE_FACTS = (
    ("src/acfqp/construction_k7_domain_registry_extension_v151.py", 1_440, "64d40fa15df0a8fbb863d09c38006cf0a5d7cbb25238818ed64e70d1230b73f5"),
    ("src/acfqp/domains/stochastic_relation_keyed_workflow.py", 6_001, "a475b445824850f4dabac7a144c6d7d707c6a62278aa79dbaa9211e02893284c"),
    ("src/acfqp/generic_relation_keyed_workflow_adapter_v151.py", 4_277, "9e58bc91635300d86c76bc3b0e51b20f6e020b6c5798a0891c290538a998b1bb"),
    ("src/acfqp/relation_keyed_relational_bank_campaign_core_v151.py", 4_740, "3ffb4fe1e0d7cf3afd8a4e5a46f2282aa3956c9f7555bdbf0d54b216b9ea9470"),
    ("src/acfqp/certified_planner_abstention_sequence_v150.py", 3_595, "51b83c5e91b47761211487b74ae2d901527a07519c6796cccbd961c7b7d4a01b"),
    ("src/acfqp/cross_domain_relational_factor_bank_campaign_core_v149.py", 15_468, "6759f91c3508857dafb00ee6a2b565f4a7f93d05c1790b2e0ffc1bf49875a9a4"),
)


class ConstructionK7RelationKeyedBankPreregistrationV151Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7RelationKeyedBankPreregistrationV151Error(message)


def campaign_config_v151() -> dict[str, Any]:
    config = relation_keyed_workflow_config_v151()
    config["families"][FAMILY]["maximum_acquisition_labels"] = MAXIMUM_ACQUISITION_LABELS
    config.update(
        target_occurrences=[{"family": family, "seed": seed} for family, seed in TARGET_OCCURRENCES],
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


def _verified_predecessor_facts(campaign_raw: bytes, verification_raw: bytes) -> dict[str, Any]:
    campaign = loads_canonical_json(campaign_raw)
    verification = loads_canonical_json(verification_raw)
    if (
        canonical_json_bytes(campaign) != campaign_raw
        or len(campaign_raw) != V150_CAMPAIGN_BYTE_COUNT
        or hashlib.sha256(campaign_raw).hexdigest() != V150_CAMPAIGN_SHA256
        or campaign.get("campaign_id") != V150_CAMPAIGN_ID
        or campaign.get("registered_gate", {}).get("passed") is not True
        or campaign.get("official_execution_allowed") is not False
        or campaign.get("official_scalar_cost") is not None
        or campaign.get("WORKLOAD_ECONOMICS_GATE") != "NOT_RUN"
        or canonical_json_bytes(verification) != verification_raw
        or len(verification_raw) != V150_VERIFICATION_BYTE_COUNT
        or hashlib.sha256(verification_raw).hexdigest() != V150_VERIFICATION_SHA256
        or verification.get("verification_id") != V150_VERIFICATION_ID
        or verification.get("campaign_id") != V150_CAMPAIGN_ID
        or verification.get(
            "registered_cross_domain_sample_efficiency_improvement_independently_verified"
        )
        is not True
        or verification.get("producer_free_abstract_plan_support_reconstruction")
        is not True
    ):
        _fail("V151 frozen V150 campaign or verification changed")
    return {
        "v150_campaign_id": V150_CAMPAIGN_ID,
        "v150_campaign_byte_count": V150_CAMPAIGN_BYTE_COUNT,
        "v150_campaign_sha256": V150_CAMPAIGN_SHA256,
        "v150_verification_id": V150_VERIFICATION_ID,
        "v150_verification_byte_count": V150_VERIFICATION_BYTE_COUNT,
        "v150_verification_sha256": V150_VERIFICATION_SHA256,
    }


def _document(campaign_raw: bytes, verification_raw: bytes) -> dict[str, Any]:
    source_facts = _source_facts()
    expected = [
        {"relative_path": path, "byte_count": count, "sha256": digest}
        for path, count, digest in FROZEN_SOURCE_FACTS
    ]
    if source_facts != expected:
        _fail("V151 frozen implementation source changed")
    config = campaign_config_v151()
    payload = {
        "schema": "acfqp.relation_keyed_bank_preregistration.v151",
        "implementation_commits": list(IMPLEMENTATION_COMMITS),
        "frozen_implementation_source_facts": source_facts,
        "frozen_v150_predecessor": _verified_predecessor_facts(campaign_raw, verification_raw),
        "target_occurrences": config["target_occurrences"],
        "target_episode_indices": list(config["target_episode_indices"]),
        "target_worker_count": config["target_worker_count"],
        "required_target_occurrence_count": config["required_target_occurrence_count"],
        "maximum_acquisition_labels": MAXIMUM_ACQUISITION_LABELS,
        "registered_gate": {
            "fresh_relation_keyed_target_occurrence_identities": True,
            "source_unseen_stochastic_family_required": True,
            "relation_binding_must_be_derived_from_raw_transition_deltas": True,
            "direct_numeric_increment_descriptor_forbidden": True,
            "same_raw_transition_stream_both_arms": True,
            "same_synthesizer_and_stop_rule_both_arms": True,
            "only_arm_switch_is_frozen_relational_factor_bank_codelength": True,
            "relational_artifact_must_be_selected_in_every_prior_arm": True,
            "same_relational_expression_must_exist_in_strict_pool": True,
            "aggregate_positive_label_reduction_required": True,
            "all_receding_episodes_required": True,
            "certificate_failure_only_local_recovery_required": True,
            "strict_incompatible_schema_no_transfer_required": True,
            "producer_free_verification_required": True,
            "frozen_two_worker_resource_schedule": True,
        },
        "claim_boundary": {
            "target_outcomes_accessed": False,
            "registered_v151_target_outcome_observed": False,
            "relational_template_selection_claimed": False,
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
        "preregistration_id": domains.extension_content_id_v151(
            domains.CONSTRUCTION_K7_PREREGISTRATION_V151_DOMAIN, payload
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class RelationKeyedBankPreregistrationV151:
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
            or domains.extension_content_id_v151(
                domains.CONSTRUCTION_K7_PREREGISTRATION_V151_DOMAIN, payload
            )
            != self.preregistration_id
        ):
            _fail("V151 preregistration bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


def freeze_relation_keyed_bank_preregistration_v151(
    campaign_raw: bytes, verification_raw: bytes
) -> RelationKeyedBankPreregistrationV151:
    document = _document(campaign_raw, verification_raw)
    raw = canonical_json_bytes(document)
    identity = document["preregistration_id"]
    if PREREGISTRATION_ID != "0" * 64 and (
        identity != PREREGISTRATION_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("V151 frozen preregistration changed")
    return RelationKeyedBankPreregistrationV151(_ISSUER, raw, identity)


__all__ = (
    "PREREGISTRATION_ID",
    "campaign_config_v151",
    "freeze_relation_keyed_bank_preregistration_v151",
)
