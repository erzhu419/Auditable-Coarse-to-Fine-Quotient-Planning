from __future__ import annotations

from pathlib import Path

import pytest

from acfqp import construction_k7_standard_2048_adaptive_accounting_artifacts_v36 as artifacts
from acfqp import construction_k7_standard_2048_adaptive_accounting_preregistration_v36 as pre
from acfqp import construction_k7_standard_2048_adaptive_accounting_runtime_v36 as runtime
from acfqp.accounting_v1 import RouteKindEnum
from acfqp.actual_accounting_v1 import ActualWorkScope
from acfqp.phase3e_ids import content_id


def _subject(label: str) -> str:
    return content_id(pre.FUTURE_DOMAINS["measurement"], {"label": label})


def _model_counts() -> dict[str, int]:
    return {
        "model.structural_context_rows_frozen": 2400,
        "model.structural_expression_value_evaluations": 100_000,
        "model.expression_candidates_materialized": 19,
        "model.candidate_label_consistency_checks": 31,
        "model.active_query_partition_evaluations": 76_000,
        "model.target_probability_labels_acquired": 6,
        "model.exact_program_proof_rows_evaluated": 4,
        "model.world_model_freezes": 1,
    }


def test_operational_bundle_reaches_output_byte_fixed_point(tmp_path: Path) -> None:
    values = dict(
        runtime.model_stage_counter_values_v36(
            _model_counts(), stage="ACQUISITION"
        )
    )
    values["io.read_bytes"] = 123
    values["io.staged_bytes"] = 17
    values["io.mounted_bytes_peak"] = 4096
    values["memory.working_bytes_peak"] = 8192
    path = tmp_path / "operational.json"
    bundle = artifacts.materialize_operational_bundle_v36(
        subject_id=_subject("acquisition"),
        window_role="ADAPTIVE_LABEL_ACQUISITION_AND_CANDIDATE_ELIMINATION",
        route_kind=RouteKindEnum.ABSTRACT_FAILED_PREFIX,
        work_scope=ActualWorkScope.COMMON_PREFIX,
        base_values=values,
        evidence_document={"stage": "ACQUISITION", "label_count": 6},
        output_path=path,
        external_output_bytes=11,
    )
    document = bundle.to_document()
    assert path.read_bytes() == bundle.canonical_bytes
    assert document["output_bytes_fixed_point"] == (
        len(bundle.canonical_bytes) + 11
    )
    assert document["measurement"][
        "native_measurement_not_legacy_summary_translation"
    ] is True
    assert document["comparison_vector"] is not None
    assert document["evaluation_work_in_operational_vector"] is False


def test_evaluation_bundle_has_no_comparison_vector(tmp_path: Path) -> None:
    values = dict(runtime.no_prior_control_counter_values_v36(2400))
    values["evaluation.io_read_bytes"] = 51
    values["evaluation.io_staged_bytes"] = 7
    values["evaluation.io_mounted_bytes_peak"] = 2048
    values["evaluation.memory_working_bytes_peak"] = 4096
    path = tmp_path / "evaluation.json"
    bundle = artifacts.materialize_evaluation_bundle_v36(
        subject_id=_subject("control"),
        window_role="MATCHED_FIRST_FRONTIER_NO_PRIOR_CONTROL",
        base_values=values,
        evidence_document={"lane": "EVALUATION", "label_count": 2400},
        output_path=path,
    )
    document = bundle.to_document()
    assert document["comparison_vector"] is None
    assert document["actual_projection_proof"] is None
    assert document[
        "evaluation_lane_excluded_from_operational_comparison"
    ] is True
    assert bundle.work_vector.value(
        "evaluation.target_probability_labels_acquired"
    ) == 2400


def test_existing_output_path_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "occupied.json"
    path.write_text("occupied", encoding="utf-8")
    with pytest.raises(
        artifacts.ConstructionK7Standard2048AdaptiveAccountingArtifactsV36Error
    ):
        artifacts.materialize_evaluation_bundle_v36(
            subject_id=_subject("occupied"),
            window_role="CONTROL",
            base_values=runtime.no_prior_control_counter_values_v36(1),
            evidence_document={"lane": "EVALUATION"},
            output_path=path,
        )
