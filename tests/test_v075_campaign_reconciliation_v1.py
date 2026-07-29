from __future__ import annotations

from dataclasses import replace
import hashlib
import inspect

import pytest

from acfqp.phase3e_ids import canonical_json_bytes
from acfqp import v075_campaign_reconciliation_v1 as reconciliation
from acfqp import v075_public_campaign_authority_v1 as public
from acfqp import v075_public_source_work_authority_v1 as public_source_work
from acfqp import v075_source_offline_work_materializer_v1 as source_work
from tests.test_v075_source_offline_work_materializer_v1 import (
    exact_source_replay,
)
from tests.test_verified_source_acquisition_archive_independent_verifier_v2 import (
    miniature_source_archive,
)


def _draw_for(entry: reconciliation.V075ScientificOccurrencePlanEntryV1) -> int:
    base = {
        "SOURCE_CONSENSUS_PRIOR": 10,
        "NO_PRIOR": 20,
        "WRONG_CONSENSUS_PRIOR": 30,
        "OOD_ABSTENTION": 40,
        "MATCHED_DIRECT_GROUND": 10,
    }[entry.arm]
    return base + entry.context_ordinal


def _test_id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _public_source_bundle(exact_source_replay):
    materialization = source_work.materialize_v075_source_offline_work_v1(
        exact_source_replay
    )
    verification = (
        source_work.verify_v075_source_offline_work_independently_v1(
            replay=exact_source_replay,
            claimed=materialization,
        )
    )
    status_payload = {
        "schema": "acfqp.v075_source_replay_materialization_status.v1",
        "schema_version": "1.0.0",
        "profile_key": (
            "v075_source_replay_materialization_controller_v1"
        ),
        "snapshot_preflight_id": _test_id("snapshot-preflight"),
        "controller_code_manifest_id": _test_id("controller-code"),
        "source_only_bypass_evidence_id": _test_id("source-bypass"),
        "source_only_readiness_id": _test_id("source-readiness"),
        "same_process_protocol_id": _test_id("same-process-protocol"),
        "source_graph_verification_id": _test_id("source-graph"),
        "blocker": None,
        "source_only_snapshot_eligible": True,
        "current_code_production_ready": True,
        "production_replay_status": "COMPLETED",
        "production_materialization_status": "COMPLETED",
        "source_replay_id": None,
        "source_replay_object_persisted": False,
        "source_replay_object_consumed_same_process": True,
        "source_work_materialization_id": materialization.materialization_id,
        "source_work_verification_id": verification.verification_id,
        "source_child_launched": False,
        "sample_draws_started": True,
        "materialization_artifact_written": True,
        "verification_artifact_written": True,
        "counter_document_accepted": False,
        "pickle_transport_accepted": False,
        "caller_supplied_expected_ids_accepted": False,
        "current_tree_recomputation_used_as_source_replay": False,
        "generic_recipe_freeze_helper_called": False,
        "confirmatory_manifest_imported": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "counter_completeness_gate_status": "NOT_RUN",
        "workload_economics_gate_status": "NOT_RUN",
        "target_access": False,
        "hidden_law_access": False,
    }
    status_id = hashlib.sha256(
        public_source_work.DOMAIN_TAGS["controller_status"].encode("utf-8")
        + b"\x00"
        + canonical_json_bytes(status_payload)
    ).hexdigest()
    return public_source_work.verify_v075_public_source_work_artifacts_v1(
        materialization_raw=materialization.canonical_bytes,
        verification_raw=canonical_json_bytes(verification.to_document()),
        controller_status_raw=canonical_json_bytes(
            {**status_payload, "status_id": status_id}
        ),
    )


def _fixture_inputs(
    *,
    kinds: dict[
        int, reconciliation.V075ConstructionTerminalEvidenceKindV1
    ]
    | None = None,
    draws: dict[int, int] | None = None,
):
    plan = reconciliation.freeze_v075_scientific_occurrence_plan_v1(
        public.V075PublicFamilyGenerationV1()
    )
    source = reconciliation.issue_v075_construction_source_work_fixture_v1(
        plan=plan,
        fixture_nonce="source-work-fixture",
        offline_draw_count=777,
    )
    verifications = []
    for entry in plan.entries:
        evidence = (
            reconciliation.issue_v075_construction_occurrence_fixture_v1(
                plan_entry=entry,
                fixture_nonce=f"occurrence-{entry.scientific_ordinal}",
                online_draw_count=(
                    draws.get(entry.scientific_ordinal, _draw_for(entry))
                    if draws is not None
                    else _draw_for(entry)
                ),
                terminal_evidence_kind=(
                    kinds.get(
                        entry.scientific_ordinal,
                        reconciliation
                        .V075ConstructionTerminalEvidenceKindV1
                        .EXACT_VALID_PLAN,
                    )
                    if kinds is not None
                    else reconciliation
                    .V075ConstructionTerminalEvidenceKindV1
                    .EXACT_VALID_PLAN
                ),
            )
        )
        verifications.append(
            reconciliation.verify_v075_construction_occurrence_fixture_v1(
                evidence
            )
        )
    return plan, source, tuple(verifications)


def _reconcile(
    *,
    kinds: dict[
        int, reconciliation.V075ConstructionTerminalEvidenceKindV1
    ]
    | None = None,
    draws: dict[int, int] | None = None,
    reverse: bool = False,
):
    plan, source, values = _fixture_inputs(kinds=kinds, draws=draws)
    if reverse:
        values = tuple(reversed(values))
    return reconciliation.reconcile_v075_construction_fixture_campaign_v1(
        plan=plan,
        source_offline_work=source,
        occurrence_verifications=values,
    )


def test_frozen_plan_is_exact_context_major_3_by_5() -> None:
    plan = reconciliation.freeze_v075_scientific_occurrence_plan_v1(
        public.V075PublicFamilyGenerationV1()
    )
    assert len(plan.entries) == 15
    assert tuple(item.scientific_ordinal for item in plan.entries) == tuple(
        range(15)
    )
    assert tuple(item.transport_ordinal for item in plan.entries) == tuple(
        range(1, 16)
    )
    assert tuple(
        (item.context_ordinal, item.arm)
        for item in plan.entries
    ) == tuple(
        (context_ordinal, arm)
        for context_ordinal in range(3)
        for arm in public.ARM_ORDER
    )
    assert len({item.occurrence_id for item in plan.entries}) == 15


def test_sequential_and_parallel_completion_order_have_one_identity() -> None:
    sequential = _reconcile()
    parallel_completion = _reconcile(reverse=True)
    assert sequential == parallel_completion
    assert sequential.reconciliation_id == parallel_completion.reconciliation_id
    assert sequential.canonical_bytes == parallel_completion.canonical_bytes


def test_source_offline_work_is_charged_once_and_online_work_stays_per_arm() -> None:
    result = _reconcile()
    document = result.to_document()
    assert document["source_offline_charge_count"] == 1
    assert document["source_offline_draw_count"] == 777
    assert document["source_offline_in_online_totals"] is False
    assert document["target_online_draw_count"] == sum(
        item.evidence.online_draw_count for item in result.occurrences
    )
    assert tuple(item.arm for item in result.arm_online_accounting) == (
        public.ARM_ORDER
    )
    assert all(
        len(item.to_document()["online_work_ids"]) == 3
        for item in result.arm_online_accounting
    )
    target_work_ids = {
        item.evidence.online_work_id for item in result.occurrences
    }
    assert len(target_work_ids) == 15
    assert result.source_offline_work.offline_work_id not in target_work_ids


def test_exact_source_materialization_is_reconciled_once_without_caller_total(
    exact_source_replay,
) -> None:
    source_bundle = _public_source_bundle(exact_source_replay)
    accounting = reconciliation.reconcile_v075_source_offline_work_once_v1(
        source_bundle=source_bundle,
    )
    document = accounting.to_document()
    assert document["source_offline_charge_count"] == 1
    assert document["source_offline_in_online_totals"] is False
    assert document["source_offline_draw_count"] == (
        exact_source_replay.source_campaign.counters
        .physical_unique_observer_draws
    )
    assert document["source_public_work_bundle_id"] == source_bundle.bundle_id
    assert (
        document["source_replay_controller_status_id"]
        == source_bundle.controller_status_id
    )
    assert document["counter_completeness_claimed"] is False
    assert document["official_scalar_cost"] is None


def test_observer_journal_transport_and_total_lift_refs_are_all_retained() -> None:
    result = _reconcile()
    for attribute in (
        "observer_record_id",
        "observer_journal_id",
        "transport_manifest_id",
        "total_lift_result_id",
    ):
        values = tuple(
            getattr(item.evidence, attribute) for item in result.occurrences
        )
        assert len(set(values)) == 15
    assert all(item.to_document()["retained"] for item in result.occurrences)
    assert result.to_document()["all_occurrences_retained"] is True


def test_independent_reconciliation_replay_is_exact() -> None:
    result = _reconcile()
    verification = (
        reconciliation.verify_v075_construction_campaign_reconciliation_v1(
            result
        )
    )
    assert verification.reconciliation_id == result.reconciliation_id
    assert verification.replayed_reconciliation_id == result.reconciliation_id
    assert verification.denominator == 15


@pytest.mark.parametrize("drop_index", [0, 7, 14])
def test_omitted_occurrence_is_rejected(drop_index: int) -> None:
    plan, source, values = _fixture_inputs()
    incomplete = values[:drop_index] + values[drop_index + 1 :]
    with pytest.raises(
        reconciliation.V075CampaignReconciliationInvariantViolation
    ):
        reconciliation.reconcile_v075_construction_fixture_campaign_v1(
            plan=plan,
            source_offline_work=source,
            occurrence_verifications=incomplete,
        )


def test_duplicate_and_byte_identical_occurrence_replay_is_rejected() -> None:
    plan, source, values = _fixture_inputs()
    replay_attack = values[:-1] + (values[0],)
    with pytest.raises(
        reconciliation.V075CampaignReconciliationInvariantViolation
    ):
        reconciliation.reconcile_v075_construction_fixture_campaign_v1(
            plan=plan,
            source_offline_work=source,
            occurrence_verifications=replay_attack,
        )


def test_reordered_serialized_reconciliation_and_denominator_deletion_fail() -> None:
    result = _reconcile()
    with pytest.raises(
        reconciliation.V075CampaignReconciliationInvariantViolation
    ):
        replace(result, occurrences=tuple(reversed(result.occurrences)))
    with pytest.raises(
        reconciliation.V075CampaignReconciliationInvariantViolation
    ):
        replace(result, occurrences=result.occurrences[:-1])


def test_cross_slot_transplant_is_rejected() -> None:
    result = _reconcile()
    transplanted = replace(
        result.occurrences[0],
        verification=result.occurrences[1].verification,
    )
    attacked = (transplanted,) + result.occurrences[1:]
    with pytest.raises(
        reconciliation.V075CampaignReconciliationInvariantViolation
    ):
        replace(result, occurrences=attacked)


def test_semantic_terminal_forgery_is_rejected() -> None:
    _plan, _source, values = _fixture_inputs(
        kinds={
            0: (
                reconciliation.V075ConstructionTerminalEvidenceKindV1
                .CAP_EXHAUSTED
            )
        }
    )
    with pytest.raises(
        reconciliation.V075CampaignReconciliationInvariantViolation
    ):
        replace(
            values[0],
            terminal_class=(
                reconciliation.V075OccurrenceTerminalClassV1
                .INFEASIBILITY_CERTIFICATE
            ),
            terminal_code=(
                reconciliation.V075OccurrenceTerminalCodeV1
                .EXACT_INFEASIBILITY_CERTIFICATE
            ),
        )


def test_cap_exhaustion_and_exact_infeasibility_are_not_confused() -> None:
    result = _reconcile(
        kinds={
            0: (
                reconciliation.V075ConstructionTerminalEvidenceKindV1
                .CAP_EXHAUSTED
            ),
            1: (
                reconciliation.V075ConstructionTerminalEvidenceKindV1
                .EXACT_INFEASIBLE
            ),
        }
    )
    assert result.plan_certificate_count == 13
    assert result.infeasibility_certificate_count == 1
    assert result.noncertificate_count == 1
    assert (
        result.occurrences[0].verification.terminal_class
        is reconciliation.V075OccurrenceTerminalClassV1
        .ATTEMPT_CLOSURE_NONCERTIFICATE
    )
    assert (
        result.occurrences[1].verification.terminal_class
        is reconciliation.V075OccurrenceTerminalClassV1
        .INFEASIBILITY_CERTIFICATE
    )


def test_locks_and_production_not_ready_are_explicit() -> None:
    result = _reconcile()
    document = result.to_document()
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["workload_economics_gate_status"] == "NOT_RUN"
    assert document["counter_completeness_gate_status"] == "NOT_RUN"
    status = reconciliation.v075_production_reconciliation_readiness_v1()
    assert (
        status.to_document()["production_occurrence_result_protocol_status"]
        == "NOT_READY"
    )
    with pytest.raises(reconciliation.V075ProductionReconciliationNotReady):
        reconciliation.reconcile_v075_campaign_v1()


def test_public_apis_accept_no_status_validity_or_expected_id_authority() -> None:
    for function in (
        reconciliation.reconcile_v075_source_offline_work_once_v1,
        reconciliation.reconcile_v075_construction_fixture_campaign_v1,
        reconciliation.verify_v075_construction_campaign_reconciliation_v1,
        reconciliation.verify_v075_construction_occurrence_fixture_v1,
    ):
        names = set(inspect.signature(function).parameters)
        assert not any(
            fragment in name
            for name in names
            for fragment in ("status", "valid", "expected")
        )
