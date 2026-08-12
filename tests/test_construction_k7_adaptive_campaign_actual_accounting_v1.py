from __future__ import annotations

import ast
from dataclasses import replace
from pathlib import Path
import shutil

import pytest

from acfqp.accounting_v1 import RouteKindEnum, SHARED_AXES
from acfqp import construction_accounting_registry_v7 as registry_v7
from acfqp import construction_k7_adaptive_campaign_actual_accounting_v1 as subject
from acfqp import construction_k7_adaptive_campaign_independent_verifier_v1 as independent


@pytest.fixture(scope="module")
def campaign(tmp_path_factory):
    root = tmp_path_factory.mktemp("adaptive-actual") / "outputs"
    return subject.run_adaptive_campaign_actual_accounting_v1(output_root=root)


@pytest.fixture(scope="module")
def independent_campaign(campaign):
    root = __import__("pathlib").Path(
        campaign.occurrences[0].output_commit.output_directory
    ).parent
    return root, independent.verify_adaptive_campaign_directory_independently_v1(root)


def test_three_adaptive_path_classes_have_formal_v7_vectors(campaign):
    assert [row.work_vector.route_kind for row in campaign.occurrences] == [
        RouteKindEnum.LOCAL_ATTEMPT,
        RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE,
        RouteKindEnum.LOCAL_ATTEMPT,
        RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE,
        RouteKindEnum.ABSTRACT_FAILED_PREFIX,
    ]
    assert all(
        len(row.work_vector.records) == registry_v7.EXPECTED_V7_REQUIRED_LEAF_COUNT
        and len(row.projection_proof.to_dict()) > 0
        and tuple(axis for axis, _value in row.comparison_vector.values)
        == SHARED_AXES
        for row in campaign.occurrences
    )


def test_all_nine_shared_paths_have_exactly_one_receipt(campaign):
    for occurrence in campaign.occurrences:
        assert tuple(row.path for row in occurrence.receipt_set.receipts) == subject.SHARED_PATHS
        assert len({row.receipt_id for row in occurrence.receipt_set.receipts}) == 9
        values = occurrence.work_vector.values
        assert values["io.read_bytes"] == len(
            occurrence.native_occurrence.route_input_bytes
        )
        assert values["io.output_bytes"] == occurrence.fixed_point.output_bytes
        assert values["io.mounted_bytes_peak"] == (
            values["io.read_bytes"]
            + values["io.staged_bytes"]
            + values["io.output_bytes"]
        )
        assert values["memory.working_bytes_peak"] >= values["io.mounted_bytes_peak"]
        assert values["process.launches"] == values["process.exit_successes"]


def test_construct_reuse_and_unsupported_preserve_ground_boundaries(campaign):
    constructed = (campaign.occurrences[0], campaign.occurrences[2])
    reuse = (campaign.occurrences[1], campaign.occurrences[3])
    unsupported = campaign.occurrences[4]
    assert all(
        row.work_vector.values["process.launches"] > 0
        and row.work_vector.values["io.staged_bytes"] > 0
        and row.work_vector.values["local.model_acquisition_ground_draws"] > 0
        for row in constructed
    )
    assert all(
        row.work_vector.values["process.launches"] == 0
        and row.work_vector.values["io.staged_bytes"] == 0
        and row.work_vector.values["local.model_acquisition_ground_draws"] == 0
        for row in reuse
    )
    assert unsupported.work_vector.values["process.launches"] == 0
    assert unsupported.work_vector.values["local.model_acquisition_ground_draws"] == 0
    assert unsupported.work_vector.values["route.failures"] == 1


def test_fixed_point_roles_are_committed_once_and_replay(campaign):
    for occurrence in campaign.occurrences:
        assert occurrence.output_commit.role_rows == tuple(
            (
                role,
                len(occurrence.fixed_point.artifact_bytes_by_role[role]),
                __import__("hashlib").sha256(
                    occurrence.fixed_point.artifact_bytes_by_role[role]
                ).hexdigest(),
            )
            for role in occurrence.fixed_point.artifact_bytes_by_role
        )
        assert subject.verify_adaptive_occurrence_actual_accounting_v1(
            occurrence
        ) is occurrence


def test_tampered_shared_receipt_or_vector_fails_closed(campaign):
    occurrence = campaign.occurrences[0]
    receipt = occurrence.receipt_set.receipts[0]
    forged_receipt = replace(receipt, value=receipt.value + 1)
    forged_set = replace(
        occurrence.receipt_set,
        receipts=(forged_receipt, *occurrence.receipt_set.receipts[1:]),
    )
    forged_bundle = replace(occurrence, receipt_set=forged_set)
    with pytest.raises(subject.ConstructionK7AdaptiveCampaignActualAccountingV1Error):
        subject.verify_adaptive_occurrence_actual_accounting_v1(forged_bundle)


def test_campaign_keeps_gates_and_scalar_locked(campaign):
    document = campaign.to_document()
    assert document["all_nine_shared_receipt_sets_present"] is True
    assert document["formal_work_vectors_issued"] is True
    assert document["formal_comparison_vectors_issued"] is True
    assert document["independent_complete_bundle_verifier_present"] is False
    assert document["counter_completeness_gate_status"] == "COUNTER_COMPLETENESS_GATE_NOT_RUN"
    assert document["workload_economics_gate_status"] == "WORKLOAD_ECONOMICS_GATE_NOT_RUN"
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["official_execution_allowed"] is False


def test_independent_bytes_replay_covers_all_occurrences(independent_campaign):
    _root, verification = independent_campaign
    document = verification.to_document()
    assert document["logical_occurrence_count"] == 5
    assert document["construct_count"] == 2
    assert document["abstract_reuse_count"] == 2
    assert document["unsupported_noncertificate_count"] == 1
    assert document["all_occurrence_native_event_graphs_replayed"] is True
    assert document["all_occurrence_formal_vectors_replayed"] is True
    assert document["counter_completeness_gate_status"] == "COUNTER_COMPLETENESS_GATE_NOT_RUN"


def test_independent_verifier_has_no_adaptive_producer_imports():
    source_path = Path(independent.__file__)
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module is not None:
                imported.add(node.module)
            imported.update(alias.name for alias in node.names)
    forbidden = {
        "acfqp.construction_k7_adaptive_campaign_actual_accounting_v1",
        "acfqp.construction_k7_adaptive_campaign_native_accounting_v1",
        "acfqp.construction_k7_adaptive_model_campaign_v1",
        "acfqp.observation_support_coordinate_refinement_v1",
    }
    assert imported.isdisjoint(forbidden)


def test_independent_replay_rejects_resigned_receipt_value(
    independent_campaign, tmp_path
):
    root, _verification = independent_campaign
    attacked = tmp_path / "attacked"
    shutil.copytree(root, attacked)
    target = attacked / "0001-W5_CONSTRUCT" / "COUNTER_RECORD_SET.json"
    raw = target.read_bytes()
    document = __import__("json").loads(raw)
    document["shared_resource_receipts"][0]["value"] += 1
    receipt = document["shared_resource_receipts"][0]
    payload = {
        key: value
        for key, value in receipt.items()
        if key != "shared_resource_receipt_id"
    }
    from acfqp.phase3e_ids import (
        CONSTRUCTION_K7_ADAPTIVE_SHARED_RECEIPT_V1_DOMAIN,
        canonical_json_bytes,
        content_id,
    )

    receipt["shared_resource_receipt_id"] = content_id(
        CONSTRUCTION_K7_ADAPTIVE_SHARED_RECEIPT_V1_DOMAIN,
        payload,
    )
    target.chmod(0o600)
    target.write_bytes(canonical_json_bytes(document))
    target.chmod(0o400)
    with pytest.raises(
        independent.ConstructionK7AdaptiveCampaignIndependentVerifierV1Error
    ):
        independent.verify_adaptive_campaign_directory_independently_v1(attacked)
