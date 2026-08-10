from __future__ import annotations

from copy import deepcopy
import hashlib

import pytest

from acfqp import construction_k7_campaign_closure_v1 as campaign_v1
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS, canonical_json_bytes
from tests import (
    test_construction_k7_production_accounting_pipeline_v1 as pipeline_test,
)
from tests import (
    test_construction_k7_production_complete_bundle_independent_verifier_v1
    as complete_test,
)


def _id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


@pytest.fixture(scope="module")
def campaign_case():
    case, pipeline = pipeline_test.assembled_case.__wrapped__()
    workload_spec_id = _id("k7-campaign-workload")
    logical_occurrence_id = (
        pipeline.logical_occurrence_closure.occurrence_closure
        .logical_occurrence_id
    )
    registration = campaign_v1.preregister_k7_campaign_v1(
        workload_spec_id=workload_spec_id,
        logical_occurrence_ids=(logical_occurrence_id,),
    )
    summary = campaign_v1.issue_k7_campaign_closure_from_pipeline_results_v1(
        registration=registration,
        pipeline_results=(pipeline,),
    )
    replay_input = campaign_v1.K7CampaignOccurrenceReplayInputV1.from_pipeline_result(
        pipeline,
    )
    patcher = pytest.MonkeyPatch()
    try:
        complete_test.synthetic_replay.__wrapped__(patcher, case)
        verification = campaign_v1.verify_k7_campaign_closure_summary_bytes_v1(
            raw=summary.canonical_bytes,
            campaign_registration_raw=registration.canonical_bytes,
            occurrence_replay_inputs=(replay_input,),
        )
        replayed = campaign_v1.verify_k7_campaign_closure_verification_bytes_v1(
            raw=verification.canonical_bytes,
            campaign_summary_raw=summary.canonical_bytes,
            campaign_registration_raw=registration.canonical_bytes,
            occurrence_replay_inputs=(replay_input,),
        )
    finally:
        patcher.undo()
    return (
        case,
        pipeline,
        workload_spec_id,
        registration,
        summary,
        replay_input,
        verification,
        replayed,
    )


def test_registered_domains_are_unique_and_central() -> None:
    assert len(campaign_v1.LOCAL_DOMAINS) == 4
    assert campaign_v1.LOCAL_DOMAINS.issubset(PHASE3E_DOMAIN_TAGS)


def test_campaign_closes_exact_logical_occurrence_denominators(campaign_case) -> None:
    (
        _case,
        pipeline,
        workload_spec_id,
        registration,
        summary,
        _input,
        verification,
        replayed,
    ) = campaign_case
    document = summary.to_document()
    row = document["rows"][0]

    assert document["workload_spec_id"] == workload_spec_id
    assert document["campaign_registration_id"] == registration.registration_id
    assert document["logical_occurrence_count"] == 1
    assert document["closure_denominator"] == 1
    assert document["certification_coverage_denominator"] == 1
    assert document["economics_cost_denominator"] == 1
    assert document["total_route_attempt_count"] == 1
    assert document["plan_certificate_count"] == 0
    assert document["infeasibility_certificate_count"] == 0
    assert document["noncertificate_count"] == 1
    assert document["certificate_coverage_gate"] == "FAIL"
    assert row["counter_record_count"] == 202
    assert row["work_vector_id"] == (
        pipeline.formal_materialization.work_vector.work_vector_id
    )
    assert row["comparison_vector_id"] == (
        pipeline.formal_materialization.comparison_vector.comparison_vector_id
    )
    assert row["terminal_class"] == "ATTEMPT_CLOSURE_NONCERTIFICATE"
    assert row["terminal_code"] == "ATTEMPT_BUDGET_EXHAUSTED"
    assert row["specific_cause"] == "CHILD_ACTION_ROW_CAP_EXCEEDED"
    assert verification.to_document() == replayed.to_document()


def test_campaign_keeps_all_official_and_economics_gates_locked(
    campaign_case,
) -> None:
    (
        _case,
        _pipeline,
        _workload,
        _registration,
        summary,
        _input,
        verification,
        _replayed,
    ) = campaign_case
    for document in (summary.to_document(), verification.to_document()):
        assert document["official_execution_allowed"] is False
        assert document["counter_completeness_gate_status"] == (
            "COUNTER_COMPLETENESS_GATE_NOT_RUN"
        )
        assert document["workload_economics_gate_status"] == (
            "WORKLOAD_ECONOMICS_GATE_NOT_RUN"
        )
        assert document["official_scalar_cost"] is None
        assert document["official_N_break_even"] is None


def test_empty_or_duplicate_occurrence_campaign_is_rejected(campaign_case) -> None:
    (
        _case,
        pipeline,
        _workload_spec_id,
        registration,
        _summary,
        _input,
        _verification,
        _replayed,
    ) = campaign_case
    with pytest.raises(campaign_v1.ConstructionK7CampaignClosureV1Error):
        campaign_v1.issue_k7_campaign_closure_summary_v1(
            registration=registration,
            occurrence_verifications=(),
        )
    with pytest.raises(
        campaign_v1.ConstructionK7CampaignClosureV1Error,
        match="caller-minted, empty, or noncanonical",
    ):
        campaign_v1.issue_k7_campaign_closure_summary_v1(
            registration=registration,
            occurrence_verifications=(
                pipeline.logical_occurrence_verification,
                pipeline.logical_occurrence_verification,
            ),
        )


def test_registration_prevents_posthoc_occurrence_deletion(campaign_case) -> None:
    (
        _case,
        pipeline,
        workload_spec_id,
        registration,
        _summary,
        _input,
        _verification,
        _replayed,
    ) = campaign_case
    extended = campaign_v1.preregister_k7_campaign_v1(
        workload_spec_id=workload_spec_id,
        logical_occurrence_ids=(
            registration.logical_occurrence_ids[0],
            _id("registered-but-omitted-occurrence"),
        ),
    )
    with pytest.raises(
        campaign_v1.ConstructionK7CampaignClosureV1Error,
        match="caller-minted, empty, or noncanonical",
    ):
        campaign_v1.issue_k7_campaign_closure_summary_v1(
            registration=extended,
            occurrence_verifications=(
                pipeline.logical_occurrence_verification,
            ),
        )


def test_tampered_campaign_denominator_is_rejected(campaign_case) -> None:
    (
        case,
        _pipeline,
        _workload_spec_id,
        registration,
        summary,
        replay_input,
        _verified,
        _replayed,
    ) = campaign_case
    document = deepcopy(summary.to_document())
    document["closure_denominator"] = 0
    patcher = pytest.MonkeyPatch()
    try:
        complete_test.synthetic_replay.__wrapped__(patcher, case)
        with pytest.raises(
            campaign_v1.ConstructionK7CampaignClosureV1Error,
            match="differs from replayed occurrences",
        ):
            campaign_v1.verify_k7_campaign_closure_summary_bytes_v1(
                raw=canonical_json_bytes(document),
                campaign_registration_raw=registration.canonical_bytes,
                occurrence_replay_inputs=(replay_input,),
            )
    finally:
        patcher.undo()


def test_partial_occurrence_replay_cannot_enter_campaign(campaign_case) -> None:
    (
        case,
        _pipeline,
        _workload_spec_id,
        registration,
        summary,
        replay_input,
        _verified,
        _replayed,
    ) = campaign_case
    incomplete = campaign_v1.K7CampaignOccurrenceReplayInputV1(
        replay_input.logical_occurrence_closure_raw,
        replay_input.complete_bundle_verification_raw,
        replay_input.semantic_closure_raw,
        replay_input.formal_materialization_raw,
        canonical_json_bytes({"terminal": "missing"}),
        replay_input.closure_replay_inputs,
    )
    patcher = pytest.MonkeyPatch()
    try:
        complete_test.synthetic_replay.__wrapped__(patcher, case)
        with pytest.raises(
            campaign_v1.ConstructionK7CampaignClosureV1Error,
            match="failed complete independent replay",
        ):
            campaign_v1.verify_k7_campaign_closure_summary_bytes_v1(
                raw=summary.canonical_bytes,
                campaign_registration_raw=registration.canonical_bytes,
                occurrence_replay_inputs=(incomplete,),
            )
    finally:
        patcher.undo()


def test_campaign_types_cannot_be_caller_minted() -> None:
    with pytest.raises(campaign_v1.ConstructionK7CampaignClosureV1Error):
        campaign_v1.K7CampaignRegistrationV1(
            object(),
            _id("workload"),
            (_id("occurrence"),),
        )
    with pytest.raises(campaign_v1.ConstructionK7CampaignClosureV1Error):
        campaign_v1.K7CampaignOccurrenceRowV1(
            object(),
            1,
            *(_id(f"row-{index}") for index in range(8)),
            202,
        )
    with pytest.raises(campaign_v1.ConstructionK7CampaignClosureV1Error):
        campaign_v1.K7CampaignClosureSummaryV1(
            object(),
            _id("workload"),
            (),
        )


def test_production_campaign_result_cannot_be_caller_minted(
    campaign_case,
) -> None:
    (
        _case,
        pipeline,
        _workload,
        registration,
        summary,
        _replay_input,
        verification,
        _replayed,
    ) = campaign_case
    with pytest.raises(
        campaign_v1.ConstructionK7CampaignClosureV1Error,
        match="caller-minted",
    ):
        campaign_v1.K7ProductionAccountingCampaignResultV1(
            object(),
            registration,
            (pipeline,),
            summary,
            verification,
        )


def test_campaign_verification_rejects_another_workload_identity(
    campaign_case,
) -> None:
    (
        case,
        _pipeline,
        _workload,
        _registration,
        summary,
        replay_input,
        _verified,
        _replayed,
    ) = campaign_case
    patcher = pytest.MonkeyPatch()
    try:
        complete_test.synthetic_replay.__wrapped__(patcher, case)
        with pytest.raises(
            campaign_v1.ConstructionK7CampaignClosureV1Error,
            match="differs from replayed occurrences",
        ):
            campaign_v1.verify_k7_campaign_closure_summary_bytes_v1(
                raw=summary.canonical_bytes,
                campaign_registration_raw=(
                    campaign_v1.preregister_k7_campaign_v1(
                        workload_spec_id=_id("another-workload"),
                        logical_occurrence_ids=(
                            summary.rows[0].logical_occurrence_id,
                        ),
                    ).canonical_bytes
                ),
                occurrence_replay_inputs=(replay_input,),
            )
    finally:
        patcher.undo()


def test_production_campaign_runs_only_after_exact_registration(
    campaign_case,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (
        _case,
        pipeline,
        _workload,
        registration,
        summary,
        _replay_input,
        verification,
        _replayed,
    ) = campaign_case
    calls: list[str] = []

    def run_pipeline(**_kwargs):
        calls.append("pipeline")
        return pipeline

    def verify_campaign(**_kwargs):
        calls.append("campaign_verify")
        return verification

    monkeypatch.setattr(
        campaign_v1.pipeline_v1,
        "run_k7_production_accounting_pipeline_v1",
        run_pipeline,
    )
    monkeypatch.setattr(
        campaign_v1,
        "verify_k7_campaign_closure_summary_bytes_v1",
        verify_campaign,
    )
    occurrence_input = (
        campaign_v1.K7ProductionAccountingCampaignOccurrenceInputV1(
            {"registered-root": object()},
            b"source-archive",
        )
    )
    result = campaign_v1.run_k7_production_accounting_campaign_v1(
        registration=registration,
        occurrence_inputs=(occurrence_input,),
    )

    assert calls == ["pipeline", "campaign_verify"]
    assert result.campaign_summary.to_document() == summary.to_document()
    assert result.to_document()["all_registered_occurrences_executed"] is True
    assert result.to_document()["campaign_denominator_closed"] is True


def test_production_campaign_rejects_missing_input_before_execution(
    campaign_case,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (
        _case,
        _pipeline,
        _workload,
        registration,
        _summary,
        _replay_input,
        _verification,
        _replayed,
    ) = campaign_case

    def forbidden(**_kwargs):
        raise AssertionError("pipeline must not run")

    monkeypatch.setattr(
        campaign_v1.pipeline_v1,
        "run_k7_production_accounting_pipeline_v1",
        forbidden,
    )
    with pytest.raises(
        campaign_v1.ConstructionK7CampaignClosureV1Error,
        match="registered denominator",
    ):
        campaign_v1.run_k7_production_accounting_campaign_v1(
            registration=registration,
            occurrence_inputs=(),
        )


def test_production_campaign_rejects_executed_identity_transplant(
    campaign_case,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (
        _case,
        pipeline,
        workload_spec_id,
        _registration,
        _summary,
        _replay_input,
        _verification,
        _replayed,
    ) = campaign_case
    another_registration = campaign_v1.preregister_k7_campaign_v1(
        workload_spec_id=workload_spec_id,
        logical_occurrence_ids=(_id("another-occurrence"),),
    )
    monkeypatch.setattr(
        campaign_v1.pipeline_v1,
        "run_k7_production_accounting_pipeline_v1",
        lambda **_kwargs: pipeline,
    )
    with pytest.raises(
        campaign_v1.ConstructionK7CampaignClosureV1Error,
        match="differ from registration",
    ):
        campaign_v1.run_k7_production_accounting_campaign_v1(
            registration=another_registration,
            occurrence_inputs=(
                campaign_v1.K7ProductionAccountingCampaignOccurrenceInputV1(
                    {"registered-root": object()},
                    b"source-archive",
                ),
            ),
        )
