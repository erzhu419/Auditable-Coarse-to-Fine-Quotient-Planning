"""Producer-free replay of the retained V181r3 mixed-result campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
from collections import Counter
import hashlib
from typing import Any, Sequence

from acfqp import construction_k7_domain_registry_extension_v181r3 as domains
from acfqp import construction_k7_open_world_execution_preregistration_v181r3 as prereg
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


EXPECTED_CAMPAIGN_ID = (
    "499d6046ab3b12325c044b03374c5f377e9047d0b0d0b828a2dd628a585d4ce8"
)
EXPECTED_CAMPAIGN_BYTE_COUNT = 3_349_302
EXPECTED_CAMPAIGN_SHA256 = (
    "3bec76566e78f6f8f5cc6b5820a80ae4ef40798dae98c22ee3882d0b419b5229"
)
EXPECTED_VERIFICATION_ID = (
    "6a14973234274670ca77e166b6b982bca904361b1b626e88436e65be3bcda188"
)
EXPECTED_VERIFICATION_BYTE_COUNT = 9_057
EXPECTED_VERIFICATION_SHA256 = (
    "75902c660ed8f0cf95a75b8820e012a6065bdd17314987d968fedb26d743cd82"
)


_ARMS = ("REUSED_SUBPROGRAM_PRIOR", "EMPTY_ARCHIVE_NO_PRIOR")
_AXES = (
    "OFFLINE_SOURCE_LABELS",
    "TARGET_GROUND_LABELS",
    "EXECUTION_STEPS",
    "PROGRAM_ENUMERATION_EVENTS",
    "PLANNING_EVENTS",
    "CERTIFICATE_EVENTS",
    "MODEL_RECOMPILATIONS",
    "OUTPUT_BYTES",
)
_CHECKPOINT_KEYS = {
    "COUNTER_COMPLETENESS_GATE",
    "WORKLOAD_ECONOMICS_GATE",
    "arm",
    "block_index",
    "compiled_model",
    "completed_row_ids",
    "decision_index",
    "event_document",
    "execution_preregistration_id",
    "failure_message",
    "failure_type",
    "manifest_index",
    "occurrence_index",
    "official_execution_allowed",
    "previous_checkpoint_id",
    "progress_checkpoint_id",
    "schema",
    "sequence",
    "source_label_count",
    "source_observations",
    "stage",
    "target_outcome_progress_not_success_claim",
}


def _verify_progress(
    raws: Sequence[bytes],
    expected_ids: Sequence[str],
) -> tuple[list[str], Counter[str]]:
    if type(raws) not in {tuple, list} or len(raws) != len(expected_ids):
        raise ValueError("V181r3 progress denominator changed")
    previous = None
    sha256s = []
    stages: Counter[str] = Counter()
    for sequence, (raw, expected_id) in enumerate(zip(raws, expected_ids)):
        document = loads_canonical_json(raw)
        if (
            type(document) is not dict
            or set(document) != _CHECKPOINT_KEYS
            or canonical_json_bytes(document) != raw
            or document["schema"] != "acfqp.open_world_progress_checkpoint.v181r3"
            or document["execution_preregistration_id"]
            != prereg.EXPECTED_EXECUTION_PREREGISTRATION_ID
            or document["sequence"] != sequence
            or document["previous_checkpoint_id"] != previous
            or document["progress_checkpoint_id"] != expected_id
            or document["failure_type"] is not None
            or document["failure_message"] is not None
            or document["target_outcome_progress_not_success_claim"] is not True
            or document["official_execution_allowed"] is not False
            or document["WORKLOAD_ECONOMICS_GATE"] != "NOT_RUN"
            or document["COUNTER_COMPLETENESS_GATE"] != "NOT_RUN"
        ):
            raise ValueError(f"V181r3 progress checkpoint {sequence} changed")
        payload = dict(document)
        checkpoint_id = payload.pop("progress_checkpoint_id")
        if checkpoint_id != domains.extension_content_id_v181r3(
            domains.CONSTRUCTION_K7_PROGRESS_CHECKPOINT_V181R3_DOMAIN,
            payload,
        ):
            raise ValueError(f"V181r3 progress checkpoint {sequence} ID changed")
        previous = checkpoint_id
        sha256s.append(hashlib.sha256(raw).hexdigest())
        stages[document["stage"]] += 1
    return sha256s, stages


def _episodes(document: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        episode
        for distribution in document["distribution_results"]
        for arm in _ARMS
        for episode in distribution["episodes"][arm]
    ]


def _recompute_work(document: dict[str, Any], arm: str) -> dict[str, int]:
    result = {axis: 0 for axis in _AXES}
    result["OUTPUT_BYTES"] = len(canonical_json_bytes(document))
    for distribution in document["distribution_results"]:
        acquisition = distribution["acquisitions"][arm]
        episodes = distribution["episodes"][arm]
        result["OFFLINE_SOURCE_LABELS"] += acquisition["source_label_count"]
        result["TARGET_GROUND_LABELS"] += sum(
            row["target_ground_label_count"] for row in episodes
        )
        result["EXECUTION_STEPS"] += sum(row["execution_step_count"] for row in episodes)
        result["PROGRAM_ENUMERATION_EVENTS"] += acquisition[
            "cumulative_enumeration_events"
        ] + sum(row["recompilation_enumeration_events"] for row in episodes)
        result["PLANNING_EVENTS"] += sum(row["planning_compute_events"] for row in episodes)
        result["CERTIFICATE_EVENTS"] += sum(row["certificate_event_count"] for row in episodes)
        result["MODEL_RECOMPILATIONS"] += acquisition["recompilation_count"] + sum(
            row["model_recompilation_count"] for row in episodes
        )
    return result


def verify_open_world_campaign_bundle_v181r3(
    campaign_raw: bytes,
    checkpoint_raws: Sequence[bytes],
) -> dict[str, Any]:
    document = loads_canonical_json(campaign_raw)
    if (
        type(document) is not dict
        or canonical_json_bytes(document) != campaign_raw
        or len(campaign_raw) != EXPECTED_CAMPAIGN_BYTE_COUNT
        or hashlib.sha256(campaign_raw).hexdigest() != EXPECTED_CAMPAIGN_SHA256
        or document.get("schema") != "acfqp.open_world_campaign.v181r3"
        or document.get("campaign_id") != EXPECTED_CAMPAIGN_ID
        or document.get("execution_preregistration_id")
        != prereg.EXPECTED_EXECUTION_PREREGISTRATION_ID
    ):
        raise ValueError("V181r3 campaign bytes or identity changed")
    payload = dict(document)
    campaign_id = payload.pop("campaign_id")
    if campaign_id != domains.extension_content_id_v181r3(
        domains.CONSTRUCTION_K7_CAMPAIGN_V181R3_DOMAIN,
        payload,
    ):
        raise ValueError("V181r3 campaign content ID changed")
    checkpoint_ids = document.get("durable_progress_checkpoint_ids")
    if type(checkpoint_ids) is not list or len(checkpoint_ids) != 118:
        raise ValueError("V181r3 progress ID denominator changed")
    checkpoint_sha256, stages = _verify_progress(checkpoint_raws, checkpoint_ids)
    expected_stages = Counter(
        {
            "ACQUISITION_BLOCK_RETAINED_BEFORE_MINIMUM": 6,
            "ACQUISITION_BLOCK_COMPILED": 10,
            "ACQUISITION_BLOCK_COVERED_NO_RECOMPILE": 14,
            "ACQUISITION_ARM_COMPLETE": 6,
            "EPISODE_MODEL_MISMATCH_RECOMPILED": 7,
            "EPISODE_COMPLETE": 72,
            "DISTRIBUTION_COMPLETE": 3,
        }
    )
    if (
        stages != expected_stages
        or document["last_durable_progress_checkpoint_id"] != checkpoint_ids[-1]
    ):
        raise ValueError("V181r3 progress stage inventory changed")
    if set(document["work_vectors"]) != set(_ARMS) or any(
        document["work_vectors"][arm] != _recompute_work(document, arm)
        for arm in _ARMS
    ):
        raise ValueError("V181r3 work vectors changed")
    episodes = _episodes(document)
    if len(episodes) != 72:
        raise ValueError("V181r3 episode denominator changed")
    steps = [step for episode in episodes for step in episode["steps"]]
    local_rows = [step for step in steps if step["local_ground_distinction_acquired"]]
    mismatch_rows = [
        step for step in steps if not step["support_match"] or not step["terminal_match"]
    ]
    recompiled_rows = [step for step in steps if step["recompiled_model_id"] is not None]
    overlap_rows = [
        step
        for step in recompiled_rows
        if step["plan_mode"] == "CERTIFICATE_FAILURE_LOCAL_GROUND_FALLBACK"
    ]
    mismatch_only_recompilation = all(
        not step["support_match"] or not step["terminal_match"]
        for step in recompiled_rows
    ) and len(recompiled_rows) == len(mismatch_rows) == 7
    local_failure_only = all(
        step["certificate"]["certified"] is False
        or not step["support_match"]
        or not step["terminal_match"]
        for step in local_rows
    )
    terminal_count = sum(episode["terminal_reached"] for episode in episodes)
    if (
        len(local_rows) != 32
        or len(overlap_rows) != 6
        or not mismatch_only_recompilation
        or not local_failure_only
        or terminal_count != 32
        or document["covered_recompilation_skip_count"] != 39
        or document["registered_gate_passed"] is not False
        or document["registered_gates"]["all_72_episodes_terminalized"] is not False
        or document["sample_tax_comparison"]["prior_labels_avoided"] != 8
        or document["sample_tax_comparison"][
            "bounded_three_distribution_sample_efficiency_observed"
        ]
        is not True
        or document["weight_agnostic_total_work_dominance_observed"] is not False
        or document["official_execution_allowed"] is not False
        or document["official_scalar_cost"] is not None
        or document["official_N_break_even"] is not None
        or document["WORKLOAD_ECONOMICS_GATE"] != "NOT_RUN"
        or document["COUNTER_COMPLETENESS_GATE"] != "NOT_RUN"
    ):
        raise ValueError("V181r3 retained scientific semantics changed")
    verification_payload = {
        "schema": "acfqp.open_world_campaign_verification.v181r3",
        "campaign_id": campaign_id,
        "campaign_bytes_sha256": EXPECTED_CAMPAIGN_SHA256,
        "checkpoint_count": len(checkpoint_ids),
        "checkpoint_bytes_sha256": checkpoint_sha256,
        "episode_denominator": len(episodes),
        "terminal_episode_count": terminal_count,
        "local_ground_label_count": len(local_rows),
        "model_mismatch_recompile_count": len(recompiled_rows),
        "covered_recompilation_skip_count": document[
            "covered_recompilation_skip_count"
        ],
        "prior_labels_avoided": document["sample_tax_comparison"][
            "prior_labels_avoided"
        ],
        "bounded_sample_tax_reduction_independently_verified": True,
        "mismatch_only_recompilation_independently_verified": True,
        "producer_nonexclusive_failure_kind_projection_false_negative_count": len(
            overlap_rows
        ),
        "all_episode_terminalization_independently_verified": False,
        "registered_gate_passed_independently_verified": False,
        "weight_agnostic_total_work_dominance_independently_verified": False,
        "scientific_campaign_completed_without_runtime_error": True,
        "scientific_success_claimed": False,
        "fresh_successor_required": True,
        "official_execution_allowed": False,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    return {
        **verification_payload,
        "verification_id": domains.extension_content_id_v181r3(
            domains.CONSTRUCTION_K7_VERIFICATION_V181R3_DOMAIN,
            verification_payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class OpenWorldCampaignVerificationV181R3:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    verification_id: str

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


def freeze_open_world_campaign_verification_v181r3(
    campaign_raw: bytes,
    checkpoint_raws: Sequence[bytes],
) -> OpenWorldCampaignVerificationV181R3:
    document = verify_open_world_campaign_bundle_v181r3(
        campaign_raw,
        checkpoint_raws,
    )
    raw = canonical_json_bytes(document)
    if EXPECTED_VERIFICATION_ID != "0" * 64 and not (
        document["verification_id"] == EXPECTED_VERIFICATION_ID
        and len(raw) == EXPECTED_VERIFICATION_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_VERIFICATION_SHA256
    ):
        raise ValueError("V181r3 frozen campaign verification changed")
    return OpenWorldCampaignVerificationV181R3(
        _ISSUER,
        raw,
        document["verification_id"],
    )


__all__ = (
    "EXPECTED_CAMPAIGN_ID",
    "EXPECTED_VERIFICATION_ID",
    "freeze_open_world_campaign_verification_v181r3",
    "verify_open_world_campaign_bundle_v181r3",
)
