"""Reconstruct the exact V34 campaign bytes from retained V180r5 bundles."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import hashlib
from pathlib import Path
from typing import Any, Mapping, NoReturn, Sequence

from acfqp import construction_accounting_registry_v9 as registry_v9
from acfqp import construction_k7_all_path_v34_failure_freeze_v180r5 as failure
from acfqp import construction_k7_standard_2048_expression_checkpoint_preregistration_v26 as v26
from acfqp import construction_k7_standard_2048_expression_checkpoint_preregistration_v27 as v27
from acfqp import construction_k7_standard_2048_expression_checkpoint_preregistration_v28 as v28
from acfqp import construction_k7_standard_2048_expression_checkpoint_preregistration_v29 as v29
from acfqp import construction_k7_standard_2048_expression_checkpoint_preregistration_v30 as v30
from acfqp import construction_k7_standard_2048_expression_checkpoint_preregistration_v31 as v31
from acfqp import construction_k7_standard_2048_expression_checkpoint_preregistration_v32 as v32
from acfqp import construction_k7_standard_2048_expression_checkpoint_preregistration_v33 as v33
from acfqp import construction_k7_standard_2048_expression_full_accounted_campaign_v34 as campaign
from acfqp import construction_k7_standard_2048_expression_full_accounted_independent_verifier_v34 as verifier
from acfqp import construction_k7_standard_2048_expression_full_accounting_preregistration_v34 as preregistration
from acfqp.accounting_v1 import ReducerEnum, SHARED_AXES, WorkVectorV1
from acfqp.phase3e_ids import canonical_json_bytes, content_id, loads_canonical_json


class ConstructionK7V34RetainedCampaignReconstructorV180r11Error(RuntimeError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7V34RetainedCampaignReconstructorV180r11Error(message)


def _object(raw: bytes, label: str) -> dict[str, Any]:
    document = loads_canonical_json(raw)
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail(f"{label} is not one canonical object")
    return document


def _load(output_root: Path, relative_path: str) -> tuple[bytes, dict[str, Any]]:
    raw = (output_root / relative_path).read_bytes()
    return raw, _object(raw, relative_path)


def _summary(output_root: Path, relative_path: str) -> dict[str, Any]:
    raw, document = _load(output_root, relative_path)
    comparison = document["comparison_vector"]
    proof = document["actual_projection_proof"]
    return {
        "counter_bundle_id": document[
            "expression_full_accounting_counter_bundle_id"
        ],
        "window_role": document["window_role"],
        "work_vector_id": document["work_vector"]["work_vector_id"],
        "comparison_vector_id": (
            None
            if comparison is None
            else comparison["comparison_vector_id"]
        ),
        "actual_projection_proof_id": (
            None if proof is None else proof["actual_projection_proof_id"]
        ),
        "native_zero_attestation_id": document["native_zero_attestation"][
            "native_zero_attestation_id"
        ],
        "output_key": relative_path,
        "canonical_byte_count": len(raw),
        "canonical_sha256": hashlib.sha256(raw).hexdigest(),
        "charged_output_bytes": document["output_bytes_fixed_point"],
    }


_PROFILES = (
    "V24_INITIAL_32",
    "V26",
    "V27",
    "V28",
    "V29",
    "V30",
    "V31",
    "V32",
    "V33",
)
_CHECKPOINT_MODULES = (None, v26, v27, v28, v29, v30, v31, v32, v33)
_OUTPUT_EPISODE_IDS = (
    None,
    v27.CHECKPOINT_EPISODE_IDS,
    v28.CHECKPOINT_EPISODE_IDS,
    v29.CHECKPOINT_EPISODE_IDS,
    v30.CHECKPOINT_EPISODE_IDS,
    v31.CHECKPOINT_EPISODE_IDS,
    v32.CHECKPOINT_EPISODE_IDS,
    v33.CHECKPOINT_EPISODE_IDS,
    campaign.FINAL_EPISODE_IDS,
)


def _terminal_rows(ordinal: int) -> list[dict[str, Any]]:
    if ordinal == 0:
        return []
    module = _CHECKPOINT_MODULES[ordinal]
    output_ids = _OUTPUT_EPISODE_IDS[ordinal]
    if module is None or output_ids is None:
        raise AssertionError("V180r11 checkpoint table changed")
    statuses = tuple(getattr(module, "CHECKPOINT_STATUSES", ("ACTIVE",) * 4))
    source_counts = tuple(
        module.SOURCE_DECISION_COUNTS
        if hasattr(module, "SOURCE_DECISION_COUNTS")
        else (module.GLOBAL_DECISION_START,) * 4
    )
    return [
        {
            "episode_index": index,
            "source_episode_id": module.CHECKPOINT_EPISODE_IDS[index],
            "output_episode_id": output_ids[index],
            "source_status": status,
            "source_board_ranks": list(module.CHECKPOINT_BOARDS[index]),
            "cumulative_decision_count": source_counts[index],
            "decision_count": 0,
            "route_work_vector_id": None,
            "zero_decision_work": True,
            "retained_in_campaign_denominator": True,
        }
        for index, status in enumerate(statuses)
        if status != "ACTIVE"
    ]


def _reconstruct_segments(
    output_root: Path,
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    operational = [
        _summary(output_root, "model/operational-acquisition.json"),
        _summary(output_root, "model/operational-proof.json"),
    ]
    evaluation = [_summary(output_root, "model/evaluation-replay.json")]
    segments = []
    for ordinal, profile in enumerate(_PROFILES):
        relative_directory = f"segment-{ordinal:02d}-{profile.lower()}"
        directory = output_root / relative_directory
        episode_rows = []
        segment_decisions = 0
        segment_cold = 0
        for path in sorted(directory.glob("episode-*-operational.json")):
            relative_path = path.relative_to(output_root).as_posix()
            raw = path.read_bytes()
            document = _object(raw, relative_path)
            reply = document["evidence"]["worker_reply"]
            episode = reply["episode"]
            episode_index = reply["episode_index"]
            decision_count = len(episode["decisions"])
            segment_decisions += decision_count
            segment_cold += reply["cold_evaluation_checkpoint_count"]
            operational_summary = _summary(output_root, relative_path)
            operational.append(operational_summary)
            evaluation_path = (
                f"{relative_directory}/episode-{episode_index:04d}-evaluation.json"
            )
            evaluation_summary = (
                _summary(output_root, evaluation_path)
                if (output_root / evaluation_path).is_file()
                else None
            )
            if evaluation_summary is not None:
                evaluation.append(evaluation_summary)
            episode_rows.append(
                {
                    "episode_index": episode_index,
                    "episode_id": episode.get("expression_accounted_episode_id")
                    or episode.get("expression_checkpoint_episode_id"),
                    "source_episode_id": reply.get("task_id"),
                    "decision_count": decision_count,
                    "closure_reason": episode["closure_reason"],
                    "final_state": episode["final_state"],
                    "tile_2048_reached": episode["tile_2048_reached"],
                    "operational_bundle": operational_summary,
                    "evaluation_bundle": evaluation_summary,
                }
            )
        terminal_rows = _terminal_rows(ordinal)
        process_path = f"{relative_directory}/process-supervision.json"
        process_summary = _summary(output_root, process_path)
        operational.append(process_summary)
        segments.append(
            {
                "segment_ordinal": ordinal,
                "profile": profile,
                "active_worker_count": len(episode_rows),
                "terminal_carry_forward_count": len(terminal_rows),
                "terminal_carry_forward": terminal_rows,
                "decision_count": segment_decisions,
                "cold_evaluation_checkpoint_count": segment_cold,
                "process_bundle": process_summary,
                "episodes": sorted(
                    episode_rows,
                    key=lambda row: row["episode_index"],
                ),
            }
        )
    operational.append(_summary(output_root, "campaign.json"))
    return segments, operational, evaluation


def _prefix_and_totals(
    output_root: Path,
    summaries: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    profile = registry_v9.official_comparison_profile_v9()
    reducers = {row.name: row.reducer for row in profile.axes}
    totals = {axis: 0 for axis in SHARED_AXES}
    prefix = []
    for sequence_index, summary in enumerate(summaries):
        _, document = _load(output_root, summary["output_key"])
        for row in document["comparison_vector"]["values"]:
            axis = row["axis"]
            value = row["value"]
            if reducers[axis] is ReducerEnum.SUM:
                totals[axis] += value
            else:
                totals[axis] = max(totals[axis], value)
        prefix.append(
            {
                "sequence_index": sequence_index,
                "work_vector_id": summary["work_vector_id"],
                "comparison_vector_id": summary["comparison_vector_id"],
                "subject_id": document["work_vector"]["subject_id"],
                "route_kind": document["work_vector"]["route_kind"],
                "cumulative_axis_values": [
                    {"axis": axis, "value": totals[axis]}
                    for axis in SHARED_AXES
                ],
            }
        )
    return prefix, totals


def _evaluation_totals(
    output_root: Path,
    summaries: Sequence[Mapping[str, Any]],
) -> dict[str, int]:
    registry = registry_v9.official_counter_registry_v9()
    vectors = [
        WorkVectorV1.from_dict(
            _load(output_root, summary["output_key"])[1]["work_vector"],
            registry,
        )
        for summary in summaries
    ]
    return {
        path: sum(vector.value(path) for vector in vectors)
        for path in registry.by_path
        if path.startswith("evaluation.")
    }


@dataclass(frozen=True, slots=True)
class ReconstructedV34CampaignV180r11:
    canonical_bytes: bytes
    campaign_id: str
    verification_bytes: bytes
    verification_id: str

    def to_document(self) -> dict[str, Any]:
        return _object(self.canonical_bytes, "reconstructed V34 campaign")


def reconstruct_retained_v34_campaign_v180r11(
    output_root: Path,
) -> ReconstructedV34CampaignV180r11:
    if not isinstance(output_root, Path) or not output_root.is_dir():
        _fail("V180r11 retained V34 output root is absent")
    frozen_failure = failure.load_frozen_v34_failure_v180r5()
    expected_root = (
        Path(__file__).resolve().parents[2]
        / ".tmp"
        / "exact-freeze"
        / "v180r5_v34_production_output"
    )
    if output_root.resolve() != expected_root.resolve() or not frozen_failure.partial_inventory:
        _fail("V180r11 recovery crossed the frozen V180r5 output tree")
    segments, operational, evaluation = _reconstruct_segments(output_root)
    prefix, totals = _prefix_and_totals(output_root, operational)
    complete_decision_count = sum(row["decision_count"] for row in segments)
    payload = {
        "schema": "acfqp.standard_2048_expression_full_accounted_campaign.v34",
        "schema_version": preregistration.SCHEMA_VERSION,
        "profile_key": preregistration.PROFILE_KEY,
        "expression_full_accounting_preregistration": preregistration.freeze_standard_2048_expression_full_accounting_preregistration_v34().to_document(),
        "model_operational_bundles": operational[:2],
        "model_evaluation_bundle": evaluation[0],
        "segments": segments,
        "segment_count": len(segments),
        "logical_occurrence_count": 4,
        "complete_decision_count": complete_decision_count,
        "model_certificate_count": complete_decision_count,
        "won_occurrence_count": 2,
        "lost_occurrence_count": 2,
        "terminal_occurrence_count": 4,
        "operational_work_vector_count": len(operational),
        "evaluation_work_vector_count": len(evaluation),
        "campaign_bundle": operational[-1],
        "vector_prefix_totals": prefix,
        "final_operational_comparison_totals": [
            {"axis": axis, "value": totals[axis]} for axis in SHARED_AXES
        ],
        "evaluation_lane_totals": _evaluation_totals(output_root, evaluation),
        "operational_target_probability_label_query_count": 4,
        "unique_operational_target_probability_label_count": 4,
        "additional_operational_target_probability_label_count": 0,
        "strict_no_prior_target_probability_label_count": 8,
        "target_probability_label_fraction_of_no_prior": Fraction(1, 2),
        "certified_decisions_per_acquired_target_label": Fraction(3187, 4),
        "all_3187_decisions_rerun_under_native_counter_windows": True,
        "all_required_counter_leaves_have_explicit_native_records": True,
        "all_nine_shared_resource_paths_have_measurement_receipts": True,
        "evaluation_replay_excluded_from_operational_comparison": True,
        "terminal_occurrences_retained_in_denominator": True,
        "summary_to_counter_translation_used": False,
        "registered_profile_counter_completeness_candidate": True,
        "full_standard_2048_campaign_terminalized": True,
        "tile_2048_reached": True,
        "sample_tax_reduced_on_registered_label_axis": True,
        "broad_iid_sample_efficiency_claimed": False,
        "total_operational_work_saving_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "counter_completeness_gate_status": "NOT_RUN",
        "workload_economics_gate_status": "NOT_RUN",
    }
    document = {
        **payload,
        "expression_full_accounted_campaign_id": content_id(
            preregistration.FUTURE_DOMAINS["campaign"],
            payload,
        ),
    }
    raw = canonical_json_bytes(document)
    if not (
        document["expression_full_accounted_campaign_id"]
        == campaign.EXPECTED_CAMPAIGN_ID
        and len(raw) == campaign.EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == campaign.EXPECTED_CANONICAL_SHA256
    ):
        _fail("V180r11 retained V34 campaign reconstruction changed")
    verified = verifier.verify_standard_2048_expression_full_accounting_bytes_independently_v34(
        raw,
        output_root,
    )
    return ReconstructedV34CampaignV180r11(
        raw,
        document["expression_full_accounted_campaign_id"],
        verified.canonical_bytes,
        verified.verification_id,
    )


__all__ = (
    "ConstructionK7V34RetainedCampaignReconstructorV180r11Error",
    "ReconstructedV34CampaignV180r11",
    "reconstruct_retained_v34_campaign_v180r11",
)
