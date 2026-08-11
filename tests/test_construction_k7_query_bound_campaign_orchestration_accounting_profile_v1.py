from __future__ import annotations

import ast
from pathlib import Path

import pytest

from acfqp import construction_k7_query_bound_campaign_orchestration_accounting_profile_independent_verifier_v1 as independent
from acfqp import construction_k7_query_bound_campaign_orchestration_accounting_profile_v1 as subject
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS, canonical_json_bytes, content_id


def test_profile_freezes_nine_paths_windows_and_gate_locks() -> None:
    profile = subject.freeze_query_bound_campaign_orchestration_accounting_profile_v1()
    document = profile.to_document()
    assert document["shared_resource_paths"] == list(subject.SHARED_RESOURCE_PATHS)
    assert len(document["shared_resource_paths"]) == 9
    assert [row["sequence"] for row in document["windows"]] == [1, 2, 3]
    assert document["windows"][1]["cardinality"] == "ONCE_PER_OCCURRENCE"
    assert document["occurrence_executor_and_finalizer_work_excluded_from_orchestration"] is True
    assert document["operational_bundle_acceptance_verification_included"] is True
    assert document["standalone_evaluation_verification_excluded"] is True
    assert document["legacy_work_vector_v1_route_kind_reused_for_campaign"] is False
    assert document["campaign_scope_work_vector_schema_required"] is True
    assert document["campaign_orchestration_measurement_present"] is False
    assert document["campaign_orchestration_work_vector_present"] is False
    assert document["counter_completeness_gate_status"] == "COUNTER_COMPLETENESS_GATE_NOT_RUN"
    assert document["workload_economics_gate_status"] == "WORKLOAD_ECONOMICS_GATE_NOT_RUN"
    assert document["official_execution_allowed"] is False


def test_producer_and_independent_bytes_replay_agree() -> None:
    profile = subject.freeze_query_bound_campaign_orchestration_accounting_profile_v1()
    assert subject.verify_query_bound_campaign_orchestration_accounting_profile_bytes_v1(
        profile.canonical_bytes
    ).profile_id == profile.profile_id
    verification = independent.verify_query_bound_campaign_orchestration_accounting_profile_bytes_independently_v1(
        profile.canonical_bytes
    )
    assert verification.producer_profile_id == profile.profile_id
    assert verification.profile_byte_count == len(profile.canonical_bytes)


def test_independent_verifier_does_not_import_profile_producer() -> None:
    tree = ast.parse(Path(independent.__file__).read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
            imported.update(f"{node.module}.{alias.name}" for alias in node.names)
    assert (
        "acfqp.construction_k7_query_bound_campaign_orchestration_accounting_profile_v1"
        not in imported
    )


@pytest.mark.parametrize(
    ("attack", "value"),
    (
        ("drop_path", None),
        ("include_occurrence_execution", None),
        ("reuse_legacy_route", True),
        ("claim_measurement", True),
        ("move_finalization_before_prefix", None),
    ),
)
def test_fully_resigned_profile_attacks_are_rejected(
    attack: str,
    value: bool | None,
) -> None:
    profile = subject.freeze_query_bound_campaign_orchestration_accounting_profile_v1()
    attacked = profile.to_document()
    if attack == "drop_path":
        attacked["shared_resource_paths"] = attacked["shared_resource_paths"][:-1]
    elif attack == "include_occurrence_execution":
        windows = [dict(row) for row in attacked["windows"]]
        included = list(windows[1]["included_operations"])
        included.append("scientific_occurrence_execution")
        windows[1]["included_operations"] = sorted(included)
        attacked["windows"] = windows
    elif attack == "reuse_legacy_route":
        attacked["legacy_work_vector_v1_route_kind_reused_for_campaign"] = value
    elif attack == "claim_measurement":
        attacked["campaign_orchestration_measurement_present"] = value
    elif attack == "move_finalization_before_prefix":
        windows = [dict(row) for row in attacked["windows"]]
        windows[2]["prefix_charge_point"] = "BEFORE_PREFIX_1"
        attacked["windows"] = windows
    payload = dict(attacked)
    payload.pop("campaign_orchestration_accounting_profile_id")
    attacked["campaign_orchestration_accounting_profile_id"] = content_id(
        subject.PROFILE_DOMAIN,
        payload,
    )
    with pytest.raises(
        independent.ConstructionK7QueryBoundCampaignOrchestrationAccountingProfileIndependentVerifierV1Error
    ):
        independent.verify_query_bound_campaign_orchestration_accounting_profile_bytes_independently_v1(
            canonical_json_bytes(attacked)
        )


def test_types_are_not_caller_mintable_and_domains_are_registered() -> None:
    with pytest.raises(
        subject.ConstructionK7QueryBoundCampaignOrchestrationAccountingProfileV1Error
    ):
        subject.QueryBoundCampaignOrchestrationAccountingProfileV1(
            object(),
            "1" * 64,
            "2" * 64,
            "3" * 64,
            subject.WINDOWS,
            subject.MEASUREMENT_METHODS,
        )
    with pytest.raises(
        independent.ConstructionK7QueryBoundCampaignOrchestrationAccountingProfileIndependentVerifierV1Error
    ):
        independent.QueryBoundCampaignOrchestrationAccountingProfileVerificationV1(
            object(),
            "1" * 64,
            "2" * 64,
            "3" * 64,
            1,
            "4" * 64,
            "5" * 64,
            "6" * 64,
        )
    assert {
        subject.PROFILE_DOMAIN,
        independent.VERIFICATION_PROFILE_DOMAIN,
        independent.VERIFICATION_DOMAIN,
    }.issubset(PHASE3E_DOMAIN_TAGS)

