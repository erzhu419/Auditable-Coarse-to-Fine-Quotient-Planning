from __future__ import annotations

from dataclasses import replace
import hashlib

import pytest

from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS
from acfqp import construction_accounting_completion_readiness_v1 as readiness
from acfqp import construction_accounting_evidence_closure_v1 as evidence
from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp import v075_k7_root_cap_execution_identity_overlay_v1 as execution
from acfqp import v075_k7_root_cap_operation_boundary_manifest_v3 as boundary


def _id(label: str) -> str:
    return hashlib.sha256(
        b"acfqp:construction-accounting-completion-readiness-test:v1\x00"
        + label.encode("utf-8")
    ).hexdigest()


def _unresolved_closure() -> evidence.EvidenceClosureV1:
    registry = registry_v6.official_counter_registry_v6()
    stage = registry_v6.official_stage_profile_v6(registry)
    manifest = boundary.official_k7_root_cap_operation_boundary_manifest_v3()
    execution_profile = (
        execution.official_v075_k7_root_cap_execution_identity_profile_v1()
    )
    context = evidence.EvidenceClosureContextV1(
        registry.registry_id,
        stage.stage_profile_id,
        manifest.manifest_id,
        execution_profile.profile_id,
        _id("transcript"),
        _id("terminal"),
    )
    return evidence.initialize_evidence_closure_v1(context)


def test_readiness_domains_are_centrally_registered() -> None:
    assert readiness.LOCAL_DOMAIN_TAGS <= PHASE3E_DOMAIN_TAGS


def test_exact_partition_is_disjoint_and_covers_all_required_paths() -> None:
    partition = readiness.official_required_path_partition_v1()
    groups = (
        partition.shared_resource_paths,
        partition.derived_reconciliation_paths,
        partition.profile_static_zero_paths,
        partition.emittable_owner_paths,
    )
    flattened = tuple(path for group in groups for path in group)
    assert tuple(map(len, groups)) == (9, 8, 114, 71)
    assert len(flattened) == len(set(flattened)) == 202
    assert set(flattened) == set(
        registry_v6.official_counter_registry_v6().required_paths
    )


def test_current_same_process_path_is_deterministically_not_ready() -> None:
    closure = _unresolved_closure()
    result = readiness.evaluate_current_same_process_completion_readiness_v1(
        closure
    )
    replayed = readiness.verify_current_same_process_completion_readiness_v1(
        result, closure=closure
    )
    assert replayed is result
    assert result.status is (
        readiness.CompletionReadinessStatusV1.NOT_READY_PARTIAL_EVIDENCE
    )
    assert len(result.unresolved_paths) == 202
    assert tuple(item.code.value for item in result.blockers) == tuple(
        sorted(item.code.value for item in result.blockers)
    )
    assert len(result.blockers) == 8
    document = result.to_document()
    assert document["shared_resource_live_closed"] is False
    assert document["counter_records_allowed"] is False
    assert document["work_vector_allowed"] is False
    assert document["comparison_vector_allowed"] is False


def test_partition_and_readiness_are_not_caller_mintable() -> None:
    partition = readiness.official_required_path_partition_v1()
    with pytest.raises(
        readiness.ConstructionAccountingCompletionReadinessV1Error,
        match="caller-minted|differs",
    ):
        replace(
            partition,
            _issuer=object(),
            shared_resource_paths=partition.shared_resource_paths[1:],
        )


def test_resolving_one_shared_path_cannot_promote_same_process_readiness() -> None:
    closure = _unresolved_closure()
    changed = evidence.resolve_shared_resource_receipt_v1(
        closure,
        path="process.launches",
        resolved_value=0,
        receipt_id=_id("caller-receipt"),
    )
    with pytest.raises(
        readiness.ConstructionAccountingCompletionReadinessV1Error,
        match="all nine shared paths",
    ):
        readiness.evaluate_current_same_process_completion_readiness_v1(changed)
