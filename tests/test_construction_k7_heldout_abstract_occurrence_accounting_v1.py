from __future__ import annotations

from pathlib import Path

import pytest

from acfqp.accounting_v1 import RouteKindEnum
from acfqp import construction_k7_heldout_abstract_occurrence_accounting_v1 as subject
from acfqp import construction_shared_resource_receipts_v1 as shared_v1
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS
from tests.test_construction_k7_heldout_abstract_stage_accounting_v1 import (
    accounted_result,
)


@pytest.fixture(scope="module")
def accounted_occurrence(accounted_result, tmp_path_factory):
    output = tmp_path_factory.mktemp("heldout-abstract-occurrence") / "output"
    bundle = subject.run_heldout_abstract_occurrence_accounting_v1(
        accounted_result[1], output_directory=output
    )
    return bundle, output


def test_domains_and_surface_are_additive() -> None:
    assert subject.LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS
    assert len(subject.LOCAL_DOMAINS) == 7
    assert set(subject.__all__) == {
        "ConstructionK7HeldoutAbstractOccurrenceAccountingV1Error",
        "LOCAL_DOMAINS",
        "HeldoutAbstractOccurrenceAccountingBundleV1",
        "HeldoutAbstractOutputCommitV1",
        "HeldoutAbstractOutputRoleCommitV1",
        "HeldoutAbstractPathAggregationV1",
        "HeldoutAbstractSharedMeasurementV1",
        "HeldoutAbstractSharedReceiptSetV1",
        "HeldoutAbstractSharedReceiptV1",
        "run_heldout_abstract_occurrence_accounting_v1",
        "verify_heldout_abstract_occurrence_accounting_v1",
    }


def test_nine_shared_receipts_close_one_formal_abstract_chain(
    accounted_occurrence,
) -> None:
    bundle, output = accounted_occurrence
    verified = subject.verify_heldout_abstract_occurrence_accounting_v1(bundle)
    document = verified.to_document()
    assert tuple(row.path for row in bundle.receipt_set.receipts) == (
        shared_v1.SHARED_RESOURCE_PATHS
    )
    assert len(bundle.path_aggregations) == 202
    assert len(bundle.work_vector.records) == 202
    assert bundle.work_vector.route_kind is RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE
    assert bundle.actual_projection_proof.projection_term_count == 182
    assert document["complete_202_counter_record_chain_present"] is True
    assert document["all_182_operational_leaves_projected_exactly_once"] is True
    assert document["terminal_code"] == "ABSTRACT_CERTIFIED"
    assert document["logical_occurrence_campaign_closed"] is False
    assert len(tuple(output.glob("*.json"))) == 8


def test_shared_measurement_and_route_exclusivity_are_exact(
    accounted_occurrence,
) -> None:
    bundle, _output = accounted_occurrence
    values = bundle.work_vector.values
    receipt_values = {row.path: row.value for row in bundle.receipt_set.receipts}
    assert receipt_values["common.hash_invocations"] > 0
    assert receipt_values["common.integrity_checks"] == 6
    assert receipt_values["common.protocol_checks"] == 6
    assert receipt_values["io.read_bytes"] > 0
    assert receipt_values["io.staged_bytes"] == 0
    assert receipt_values["process.launches"] == 0
    assert all(
        value == 0
        for path, value in values.items()
        if path.startswith(("local.", "fallback.", "rebuild."))
    )
    assert values["acquisition.incremental_engine_ground_draws"] == 0
    assert values["common.abstract_audit_obligations"] == 1
    assert values["common.abstract_bellman_backups"] > 0
    assert values["route.attempts"] == 1
    assert values["route.successes"] == 1
    assert values["route.failures"] == 0


def test_output_fixed_point_matches_eight_committed_roles(
    accounted_occurrence,
) -> None:
    bundle, output = accounted_occurrence
    physical = sum(path.stat().st_size for path in output.glob("*.json"))
    assert physical == bundle.fixed_point.output_bytes
    assert physical == bundle.output_commit.output_bytes
    assert bundle.work_vector.values["io.output_bytes"] == physical
    assert bundle.work_vector.values["io.mounted_bytes_peak"] == (
        bundle.measurement.pre_output_mounted_bytes + physical
    )
    assert bundle.work_vector.values["memory.working_bytes_peak"] >= (
        bundle.work_vector.values["io.mounted_bytes_peak"]
    )


def test_portable_replay_is_not_charged_as_operational_ground_work(
    accounted_occurrence,
) -> None:
    bundle, _output = accounted_occurrence
    assert bundle.reuse_result.to_document()[
        "fresh_occurrence_evaluation_exact_kernel_calls"
    ] == 0
    assert bundle.measurement.to_document()[
        "independent_portable_replay_in_operational_window"
    ] is False
    assert bundle.comparison_vector.value("kernel_transition_calls") == 0
    assert bundle.work_vector.values["fallback.ground_steps"] == 0


def test_crossed_path_aggregation_is_rejected(accounted_occurrence) -> None:
    bundle, _output = accounted_occurrence
    row = bundle.path_aggregations[0]
    original = row.value
    try:
        object.__setattr__(row, "value", original + 1)
        with pytest.raises(
            subject.ConstructionK7HeldoutAbstractOccurrenceAccountingV1Error
        ):
            subject.verify_heldout_abstract_occurrence_accounting_v1(bundle)
    finally:
        object.__setattr__(row, "value", original)


def test_existing_output_directory_is_rejected(
    accounted_result, tmp_path: Path
) -> None:
    with pytest.raises(
        subject.ConstructionK7HeldoutAbstractOccurrenceAccountingV1Error
    ):
        subject.run_heldout_abstract_occurrence_accounting_v1(
            accounted_result[1], output_directory=tmp_path
        )
