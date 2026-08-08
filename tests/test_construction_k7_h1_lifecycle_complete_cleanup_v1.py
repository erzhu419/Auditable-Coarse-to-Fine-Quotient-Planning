from __future__ import annotations

import copy
from pathlib import Path

import pytest

from acfqp import construction_k7_h1_anchored_lifecycle_dispatch_v1 as dispatch_v1
from acfqp import construction_k7_h1_lifecycle_complete_cleanup_v1 as cleanup_v1
from acfqp import construction_k7_h1_lifecycle_output_leaf_join_v1 as output_join_v1
from acfqp.phase3e_ids import canonical_json_bytes, content_id


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
EXPECTED_ANCHOR_ID = "4a4b0d1888f0ac18123e4163e1a26b0583a64946d2eb219e02d4b77dc0a3e327"


@pytest.fixture(scope="module")
def bundle():
    return dispatch_v1.freeze_h1_anchored_lifecycle_dispatch_bundle_v1(
        REPOSITORY_ROOT, expected_anchor_id=EXPECTED_ANCHOR_ID
    )


@pytest.fixture(scope="module")
def output_join(bundle):
    return output_join_v1.build_h1_lifecycle_output_leaf_join_v1(bundle)


@pytest.fixture(scope="module")
def analysis(bundle, output_join):
    return cleanup_v1.derive_h1_lifecycle_complete_branch_analysis_v1(
        bundle, output_join
    )


def _resign(domain: str, document: dict, id_field: str) -> bytes:
    value = copy.deepcopy(document)
    value.pop(id_field, None)
    value[id_field] = content_id(domain, value)
    return canonical_json_bytes(value)


def test_exact_declared_replay_supplemental_coverage_and_locks(
    bundle, output_join, analysis
) -> None:
    document = analysis.to_document()
    assert document["replayed_declared_lifecycle_branch_analysis_id"] == (
        bundle.program.branch_analysis_id
    )
    assert document["declared_transition_count"] == 62
    assert document["declared_failure_edge_count"] == 143
    assert document["declared_branch_count_including_success"] == 144
    assert document["supplemental_dispatch_protocol_abort_count"] == 10
    assert document["registered_analysis_branch_count_including_success"] == 154
    assert document["first_failure_outcome_counts"] == {
        "ANCHOR_GRAMMAR_VIOLATION_AFTER_ADMISSION": 10,
        "CALLBACK_FAILED_AFTER_ADMISSION": 36,
        "CAP_REJECTED_BEFORE_SIDE_EFFECT": 48,
        "CLEANUP_FAILED": 10,
        "NATIVE_EXISTENCE_AMBIGUOUS_AFTER_ADMISSION": 13,
        "OBSERVED_UPPER_BOUND_VIOLATION": 33,
        "PROTOCOL_FAILED": 3,
    }
    assert document["dispatcher_unreachable_declared_branch_count"] == 2
    assert set(document["dispatcher_unreachable_declared_branch_keys"]) == {
        (
            "FAIL:memory:bind-working-hierarchy:"
            "NATIVE_EXISTENCE_AMBIGUOUS_AFTER_ADMISSION"
        ),
        "FAIL:output:finalize-route-wide:PROTOCOL_FAILED",
    }
    assert (
        document["complete_registered_branch_resource_cleanup_plans_present"]
        is True
    )
    assert document["h1_lifecycle_output_leaf_join_id"] == output_join.join_id
    assert document["output_role_presence_join_bound"] is True
    assert document["cleanup_execution_authority_present"] is False
    assert document["cleanup_only_attempt_gate_capability_present"] is False
    assert document["output_terminal_context_join_complete"] is False
    assert document["production_output_leaf_authority_present"] is False
    assert document["all_interleaving_branch_completeness_claimed"] is False
    assert document["post_admission_no_event_recovery_complete"] is False
    assert (
        document["conditional_absent_output_role_skip_dispatch_semantics_present"]
        is False
    )
    assert document["production_execution_authority_present"] is False
    assert document["formal_v7_route_authority_present"] is False
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None


def test_cleanup_order_reap_memory_lifo_readback_finalize_close(analysis) -> None:
    branch = analysis.by_key[
        "FAIL:read:business-result:BROKER:CALLBACK_FAILED_AFTER_ADMISSION"
    ]
    actions = branch["cleanup_actions"]
    kinds = [row["action_kind"] for row in actions]
    business = next(
        index
        for index, row in enumerate(actions)
        if row["action_kind"] == "REAP_DESCENDANT" and row["target"] == "BUSINESS"
    )
    worker = next(
        index
        for index, row in enumerate(actions)
        if row["action_kind"] == "REAP_DESCENDANT" and row["target"] == "WORKER"
    )
    memory = kinds.index(
        "SETTLE_MEMORY_RESERVATION_CONSERVATIVELY_WITHOUT_NATIVE_READ"
    )
    mount_indices = [
        index for index, kind in enumerate(kinds) if kind == "CLOSE_MOUNT"
    ]
    output = kinds.index(
        "SETTLE_OUTPUT_RESERVATION_CONSERVATIVELY_WITHOUT_NATIVE_FINALIZE"
    )
    assert business < worker < memory < min(mount_indices)
    assert max(mount_indices) < output
    assert "READBACK_OUTPUT_ROLE" not in kinds
    assert "CLOSE_OUTPUT_OWNER" not in kinds
    mount_targets = [
        row["target"] for row in actions if row["action_kind"] == "CLOSE_MOUNT"
    ]
    assert mount_targets[0] == "mount-open:BUSINESS:fallback_cap_profile"
    assert mount_targets[-1] == "mount-open:WORKER:sealed_runtime_archive"
    assert all(row["primary_failure_preserved"] is True for row in actions)
    assert all(
        row["continue_with_later_safe_cleanup_after_secondary_failure"] is True
        for row in actions
    )


def test_ambiguity_is_never_silently_absent_and_supplemental_mount_is_known(
    analysis,
) -> None:
    ambiguous = analysis.by_key[
        (
            "FAIL:mount-open:WORKER:sealed_runtime_archive:"
            "NATIVE_EXISTENCE_AMBIGUOUS_AFTER_ADMISSION"
        )
    ]
    assert ambiguous["cleanup_frontier"]["ambiguous_mount_sites"] == [
        "mount-open:WORKER:sealed_runtime_archive"
    ]
    assert ambiguous["cleanup_actions"][0]["action_kind"] == (
        "RESOLVE_NATIVE_EXISTENCE_OR_CALLBACK_COMPLETION"
    )
    supplemental = analysis.by_key[
        (
            "SUPPLEMENTAL:mount-open:WORKER:sealed_runtime_archive:"
            "ANCHOR_GRAMMAR_VIOLATION_AFTER_ADMISSION"
        )
    ]
    assert supplemental["cleanup_frontier"]["ambiguous_mount_sites"] == []
    assert supplemental["cleanup_frontier"]["active_mount_open_sites"] == [
        "mount-open:WORKER:sealed_runtime_archive"
    ]
    assert supplemental["cleanup_actions"][0]["action_kind"] == (
        "SETTLE_MEMORY_RESERVATION_CONSERVATIVELY_WITHOUT_NATIVE_READ"
    )
    assert any(
        row["action_kind"] == "CLOSE_MOUNT"
        and row["target"] == "mount-open:WORKER:sealed_runtime_archive"
        for row in supplemental["cleanup_actions"]
    )
    success = analysis.by_key["SUCCESS:COMPLETE_LIFECYCLE"]
    assert success["cleanup_actions"] == []


def test_deferred_origins_do_not_fabricate_native_memory_or_output(analysis) -> None:
    branch = analysis.by_key[
        "FAIL:stage:WORKER:sealed_runtime_archive:CALLBACK_FAILED_AFTER_ADMISSION"
    ]
    frontier = branch["cleanup_frontier"]
    assert frontier["memory_reservation_state"] == "ACTIVE"
    assert frontier["memory_native_state"] == "NOT_STARTED_BY_CONSTRUCTION_DISPATCH"
    assert frontier["output_reservation_state"] == "ACTIVE"
    assert frontier["output_native_state"] == "NOT_STARTED_BY_CONSTRUCTION_DISPATCH"
    assert frontier["output_owner_state"] == "NOT_STARTED_BY_CONSTRUCTION_DISPATCH"
    kinds = [row["action_kind"] for row in branch["cleanup_actions"]]
    assert kinds == [
        "SETTLE_MEMORY_RESERVATION_CONSERVATIVELY_WITHOUT_NATIVE_READ",
        "SETTLE_OUTPUT_RESERVATION_CONSERVATIVELY_WITHOUT_NATIVE_FINALIZE",
    ]


def test_analysis_and_cleanup_pass_exact_replay_reject_resigned_tamper(
    bundle, output_join, analysis
) -> None:
    verified = cleanup_v1.verify_h1_lifecycle_complete_branch_analysis_bytes_v1(
        canonical_json_bytes(analysis.to_document()),
        bundle=bundle,
        output_join=output_join,
    )
    assert verified.analysis_id == analysis.analysis_id
    tampered = analysis.to_document()
    target = next(
        row
        for row in tampered["branches"]
        if row["branch_key"]
        == (
            "FAIL:memory:bind-working-hierarchy:"
            "NATIVE_EXISTENCE_AMBIGUOUS_AFTER_ADMISSION"
        )
    )
    target["cleanup_actions"] = []
    with pytest.raises(ValueError, match="exact reconstruction"):
        cleanup_v1.verify_h1_lifecycle_complete_branch_analysis_bytes_v1(
            _resign(
                cleanup_v1.COMPLETE_BRANCH_ANALYSIS_DOMAIN,
                tampered,
                "h1_lifecycle_complete_branch_analysis_id",
            ),
            bundle=bundle,
            output_join=output_join,
        )

    branch_key = (
        "FAIL:common:preflight-hash:CALLBACK_FAILED_AFTER_ADMISSION"
    )
    cleanup_pass = cleanup_v1.bind_h1_lifecycle_cleanup_pass_v1(
        analysis, branch_key=branch_key
    )
    replayed = cleanup_v1.verify_h1_lifecycle_cleanup_pass_bytes_v1(
        canonical_json_bytes(cleanup_pass.to_document()), analysis=analysis
    )
    assert replayed.pass_id == cleanup_pass.pass_id
    assert replayed.payload["execution_status"] == "NOT_RUN"
    assert replayed.payload["cleanup_plan_complete"] is False
    assert replayed.payload["registered_resource_cleanup_plan_complete"] is True
    assert replayed.payload["cleanup_pass_complete"] is False
    forged = cleanup_pass.to_document()
    forged["cleanup_pass_complete"] = True
    with pytest.raises(ValueError, match="exact reconstruction"):
        cleanup_v1.verify_h1_lifecycle_cleanup_pass_bytes_v1(
            _resign(
                cleanup_v1.CLEANUP_PASS_DOMAIN,
                forged,
                "h1_lifecycle_cleanup_pass_id",
            ),
            analysis=analysis,
        )
