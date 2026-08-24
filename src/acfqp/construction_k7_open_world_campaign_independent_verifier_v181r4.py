"""Producer-free replay of the retained V181r4 rank-decreasing campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
from collections import Counter
import hashlib
from typing import Any, Sequence

from acfqp import construction_k7_domain_registry_extension_v181r4 as domains
from acfqp import construction_k7_open_world_execution_preregistration_v181r4 as prereg
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


EXPECTED_CAMPAIGN_ID = (
    "defda4e4b216105cbadae6ddc50c9cc9a2bf6b17d31a4a59f7395d401743a6d9"
)
EXPECTED_CAMPAIGN_BYTE_COUNT = 646_606
EXPECTED_CAMPAIGN_SHA256 = (
    "50816bdf0b7403db11ef638dbbb6f7f361d973e2a0abce9baa78368b98652baa"
)
EXPECTED_VERIFICATION_ID = (
    "6cda784e10eecb1e2a9879b8c341b4c7f2cf0b86446e00221f6590283e506789"
)
EXPECTED_VERIFICATION_BYTE_COUNT = 9_705
EXPECTED_VERIFICATION_SHA256 = (
    "4a28c53bfbc8c0d27d43bc0712ab5e6ca00a7e5ecea5746c26c47a07c4d181ad"
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
        raise ValueError("V181r4 progress denominator changed")
    previous = None
    sha256s = []
    stages: Counter[str] = Counter()
    for sequence, (raw, expected_id) in enumerate(zip(raws, expected_ids)):
        document = loads_canonical_json(raw)
        if (
            type(document) is not dict
            or set(document) != _CHECKPOINT_KEYS
            or canonical_json_bytes(document) != raw
            or document["schema"] != "acfqp.open_world_progress_checkpoint.v181r4"
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
            raise ValueError(f"V181r4 progress checkpoint {sequence} changed")
        payload = dict(document)
        checkpoint_id = payload.pop("progress_checkpoint_id")
        if checkpoint_id != domains.extension_content_id_v181r4(
            domains.CONSTRUCTION_K7_PROGRESS_CHECKPOINT_V181R4_DOMAIN,
            payload,
        ):
            raise ValueError(f"V181r4 progress checkpoint {sequence} ID changed")
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


def verify_open_world_campaign_bundle_v181r4(
    campaign_raw: bytes,
    checkpoint_raws: Sequence[bytes],
) -> dict[str, Any]:
    document = loads_canonical_json(campaign_raw)
    if (
        type(document) is not dict
        or canonical_json_bytes(document) != campaign_raw
        or len(campaign_raw) != EXPECTED_CAMPAIGN_BYTE_COUNT
        or hashlib.sha256(campaign_raw).hexdigest() != EXPECTED_CAMPAIGN_SHA256
        or document.get("schema") != "acfqp.open_world_campaign.v181r4"
        or document.get("campaign_id") != EXPECTED_CAMPAIGN_ID
        or document.get("execution_preregistration_id")
        != prereg.EXPECTED_EXECUTION_PREREGISTRATION_ID
    ):
        raise ValueError("V181r4 campaign bytes or identity changed")
    payload = dict(document)
    campaign_id = payload.pop("campaign_id")
    if campaign_id != domains.extension_content_id_v181r4(
        domains.CONSTRUCTION_K7_CAMPAIGN_V181R4_DOMAIN,
        payload,
    ):
        raise ValueError("V181r4 campaign content ID changed")
    checkpoint_ids = document.get("durable_progress_checkpoint_ids")
    if type(checkpoint_ids) is not list or len(checkpoint_ids) != 125:
        raise ValueError("V181r4 progress ID denominator changed")
    checkpoint_sha256, stages = _verify_progress(checkpoint_raws, checkpoint_ids)
    expected_stages = Counter(
        {
            "ACQUISITION_BLOCK_RETAINED_BEFORE_MINIMUM": 6,
            "ACQUISITION_BLOCK_COMPILED": 19,
            "ACQUISITION_BLOCK_COVERED_NO_RECOMPILE": 19,
            "ACQUISITION_ARM_COMPLETE": 6,
            "EPISODE_COMPLETE": 72,
            "DISTRIBUTION_COMPLETE": 3,
        }
    )
    if (
        stages != expected_stages
        or document["last_durable_progress_checkpoint_id"] != checkpoint_ids[-1]
    ):
        raise ValueError("V181r4 progress stage inventory changed")
    if set(document["work_vectors"]) != set(_ARMS) or any(
        document["work_vectors"][arm] != _recompute_work(document, arm)
        for arm in _ARMS
    ):
        raise ValueError("V181r4 work vectors changed")
    episodes = _episodes(document)
    if len(episodes) != 72:
        raise ValueError("V181r4 episode denominator changed")
    steps = [step for episode in episodes for step in episode["steps"]]
    local_rows = [step for step in steps if step["local_ground_distinction_acquired"]]
    mismatch_rows = [
        step for step in steps if not step["support_match"] or not step["terminal_match"]
    ]
    recompiled_rows = [step for step in steps if step["recompiled_model_id"] is not None]
    mismatch_only_recompilation = all(
        not step["support_match"] or not step["terminal_match"]
        for step in recompiled_rows
    ) and len(recompiled_rows) == len(mismatch_rows) == 0
    local_failure_only = all(
        step["certificate"]["certified"] is False
        or not step["support_match"]
        or not step["terminal_match"]
        for step in local_rows
    )
    rank_bindings_valid = True
    for episode in episodes:
        if (
            episode["execution_step_count"] != len(episode["steps"])
            or episode["certificate_event_count"] != len(episode["steps"])
            or episode["planning_compute_events"]
            != sum(step["certificate"]["planning_compute_events"] for step in episode["steps"])
            or episode["target_ground_label_count"]
            != sum(step["local_ground_distinction_acquired"] for step in episode["steps"])
            or episode["model_recompilation_count"]
            != sum(step["recompiled_model_id"] is not None for step in episode["steps"])
        ):
            rank_bindings_valid = False
        for index, step in enumerate(episode["steps"]):
            certificate = step["certificate"]
            certificate_payload = dict(certificate)
            certificate_id = certificate_payload.pop("certificate_id", None)
            observation = step["execution_observation"]
            expected_successor = (
                episode["steps"][index + 1]["state"]
                if index + 1 < len(episode["steps"])
                else episode["final_state"]
            )
            if not (
                certificate.get("schema") == "acfqp.open_world_rank_certificate.v181r4"
                and certificate_id
                == domains.extension_content_id_v181r4(
                    domains.CONSTRUCTION_K7_CERTIFICATE_V181R4_DOMAIN,
                    certificate_payload,
                )
                and certificate.get("compiled_model_id") == step["model_id_before"]
                and certificate.get("state") == step["state"]
                and certificate.get("horizon") == episode["horizon"]
                and certificate.get("certified") is True
                and certificate.get("selected_action") == step["action"]
                and type(certificate.get("terminal_distance_rank")) is int
                and type(certificate.get("selected_successor_rank_upper_bound")) is int
                and certificate["selected_successor_rank_upper_bound"]
                < certificate["terminal_distance_rank"]
                and certificate.get("strict_rank_decrease_proved") is True
                and certificate.get("certificate_failure_requires_local_ground_distinction")
                is False
                and step["plan_mode"] == "ABSTRACT_CERTIFIED"
                and step["certificate_failure_kinds"] == []
                and step["local_ground_distinction_acquired"] is False
                and step["support_match"] is True
                and step["terminal_match"] is True
                and observation["state"] == step["state"]
                and observation["action"] == step["action"]
                and observation["successor"] == expected_successor
            ):
                rank_bindings_valid = False
    terminal_count = sum(episode["terminal_reached"] for episode in episodes)
    if (
        len(local_rows) != 0
        or not mismatch_only_recompilation
        or not local_failure_only
        or not rank_bindings_valid
        or terminal_count != 72
        or document["covered_recompilation_skip_count"] != 19
        or document["registered_gate_passed"] is not True
        or not all(document["registered_gates"].values())
        or document["sample_tax_comparison"]["prior_labels_avoided"] != -32
        or document["sample_tax_comparison"][
            "bounded_three_distribution_sample_efficiency_observed"
        ]
        is not False
        or document["weight_agnostic_total_work_dominance_observed"] is not False
        or document["official_execution_allowed"] is not False
        or document["official_scalar_cost"] is not None
        or document["official_N_break_even"] is not None
        or document["WORKLOAD_ECONOMICS_GATE"] != "NOT_RUN"
        or document["COUNTER_COMPLETENESS_GATE"] != "NOT_RUN"
    ):
        raise ValueError("V181r4 retained scientific semantics changed")
    verification_payload = {
        "schema": "acfqp.open_world_campaign_verification.v181r4",
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
        "bounded_sample_tax_reduction_independently_verified": False,
        "negative_prior_transfer_independently_observed": True,
        "mismatch_only_recompilation_independently_verified": True,
        "rank_certificate_identity_and_execution_binding_independently_verified": True,
        "strict_rank_decrease_fields_independently_verified": True,
        "all_episode_terminalization_independently_verified": True,
        "registered_gate_projection_independently_verified": True,
        "weight_agnostic_total_work_dominance_independently_verified": False,
        "scientific_campaign_completed_without_runtime_error": True,
        "bounded_rank_decreasing_campaign_succeeded": True,
        "broad_open_world_success_claimed": False,
        "fresh_successor_required": True,
        "official_execution_allowed": False,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    return {
        **verification_payload,
        "verification_id": domains.extension_content_id_v181r4(
            domains.CONSTRUCTION_K7_VERIFICATION_V181R4_DOMAIN,
            verification_payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class OpenWorldCampaignVerificationV181R4:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    verification_id: str

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


def freeze_open_world_campaign_verification_v181r4(
    campaign_raw: bytes,
    checkpoint_raws: Sequence[bytes],
) -> OpenWorldCampaignVerificationV181R4:
    document = verify_open_world_campaign_bundle_v181r4(
        campaign_raw,
        checkpoint_raws,
    )
    raw = canonical_json_bytes(document)
    if EXPECTED_VERIFICATION_ID != "0" * 64 and not (
        document["verification_id"] == EXPECTED_VERIFICATION_ID
        and len(raw) == EXPECTED_VERIFICATION_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_VERIFICATION_SHA256
    ):
        raise ValueError("V181r4 frozen campaign verification changed")
    return OpenWorldCampaignVerificationV181R4(
        _ISSUER,
        raw,
        document["verification_id"],
    )


__all__ = (
    "EXPECTED_CAMPAIGN_ID",
    "EXPECTED_VERIFICATION_ID",
    "freeze_open_world_campaign_verification_v181r4",
    "verify_open_world_campaign_bundle_v181r4",
)
