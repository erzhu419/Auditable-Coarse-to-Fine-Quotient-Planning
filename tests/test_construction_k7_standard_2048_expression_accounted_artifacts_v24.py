from __future__ import annotations

from acfqp import construction_k7_standard_2048_expression_accounted_artifacts_v24 as artifacts
from acfqp import construction_k7_standard_2048_expression_accounted_runtime_v24 as runtime
from acfqp.accounting_v1 import RouteKindEnum
from acfqp.actual_accounting_v1 import ActualWorkScope


def test_operational_bundle_closes_output_fixed_point_and_nine_receipts(tmp_path) -> None:
    counters = runtime.NativeCounterSetV24()
    counters.add("model.target_probability_labels_acquired", 4)
    counters.add("common.hash_invocations")
    bundle = artifacts.materialize_operational_bundle_v24(
        subject_id="1" * 64,
        window_role="MODEL_ACQUISITION_AND_SELECTION",
        route_kind=RouteKindEnum.ABSTRACT_FAILED_PREFIX,
        work_scope=ActualWorkScope.COMMON_PREFIX,
        base_values=counters.freeze(),
        evidence_document={"stage": "acquisition", "label_count": 4},
        output_path=tmp_path / "operational.json",
    )
    document = bundle.to_document()
    assert document["output_bytes_fixed_point"] == len(bundle.canonical_bytes)
    assert bundle.output_path.read_bytes() == bundle.canonical_bytes
    assert len(document["measurement"]["measured_values"]) == 9
    assert document["work_vector"]["work_vector_id"] == bundle.chain.work_vector.work_vector_id
    assert document["comparison_vector"]["comparison_vector_id"] == bundle.chain.comparison_vector.comparison_vector_id


def test_evaluation_bundle_is_native_zero_operational_and_has_no_comparison(tmp_path) -> None:
    counters = runtime.NativeCounterSetV24()
    counters.add("evaluation.target_probability_labels_acquired", 4)
    counters.add("evaluation.exact_program_proof_rows_evaluated", 17)
    bundle = artifacts.materialize_evaluation_bundle_v24(
        subject_id="2" * 64,
        window_role="MODEL_SYNTHESIS_STANDALONE_REPLAY",
        base_values=counters.freeze(),
        evidence_document={"stage": "evaluation", "proof_rows": 17},
        output_path=tmp_path / "evaluation.json",
    )
    document = bundle.to_document()
    assert document["output_bytes_fixed_point"] == len(bundle.canonical_bytes)
    assert document["comparison_vector"] is None
    assert document["actual_projection_proof"] is None
    assert bundle.work_vector.value("model.target_probability_labels_acquired") == 0
    assert bundle.work_vector.value("evaluation.target_probability_labels_acquired") == 4
