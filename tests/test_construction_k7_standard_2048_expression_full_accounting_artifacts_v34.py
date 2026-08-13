from __future__ import annotations

from pathlib import Path

from acfqp import construction_k7_standard_2048_expression_full_accounting_artifacts_v34 as artifacts
from acfqp import construction_k7_standard_2048_expression_full_accounting_runtime_v34 as runtime
from acfqp.accounting_v1 import RouteKindEnum
from acfqp.actual_accounting_v1 import ActualWorkScope


def test_operational_bundle_reaches_output_byte_fixed_point(tmp_path: Path) -> None:
    values = runtime.NativeCounterSetV34()
    values.add("common.protocol_checks", 1)
    result = artifacts.materialize_operational_bundle_v34(
        subject_id="1" * 64,
        window_role="TEST_OPERATIONAL_WINDOW",
        route_kind=RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE,
        work_scope=ActualWorkScope.ABSTRACT_SELECTED_ROUTE_EXECUTION,
        base_values=values.freeze(),
        evidence_document={"kind": "TEST"},
        output_path=tmp_path / "operational.json",
    )
    document = result.to_document()
    assert document["output_bytes_fixed_point"] == len(result.canonical_bytes)
    assert result.output_path.read_bytes() == result.canonical_bytes
    assert document["work_vector"]["records"]
    assert document["comparison_vector"] is not None
    assert document["actual_projection_proof"] is not None


def test_evaluation_bundle_is_excluded_from_operational_projection(
    tmp_path: Path,
) -> None:
    values = runtime.NativeCounterSetV34()
    values.add("evaluation.semantic_protocol_checks", 1)
    result = artifacts.materialize_evaluation_bundle_v34(
        subject_id="2" * 64,
        window_role="TEST_EVALUATION_WINDOW",
        base_values=values.freeze(),
        evidence_document={"kind": "TEST"},
        output_path=tmp_path / "evaluation.json",
    )
    document = result.to_document()
    assert document["output_bytes_fixed_point"] == len(result.canonical_bytes)
    assert document["comparison_vector"] is None
    assert document["actual_projection_proof"] is None
    assert document["evaluation_lane_excluded_from_operational_comparison"] is True
