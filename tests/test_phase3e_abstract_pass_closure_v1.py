from __future__ import annotations

import copy
from dataclasses import replace
from pathlib import Path

import pytest

from acfqp.accounting_v1 import CounterRecordV1, LaneEnum, official_counter_registry_v1
from acfqp.phase3e_abstract_pass_closure_v1 import (
    AbstractOnlyOccurrenceWorkSumV1,
    MODEL_ONLY_PASS_ACCOUNTING_STATUS,
    Phase3EAbstractPassClosureV1Error,
    close_model_only_abstract_pass_v1,
    verify_model_only_operational_execution_v1,
)
from acfqp.phase3e_model_only_executor_v1 import (
    ModelOnlyQueryExecutionArtifactV1,
    ModelOnlyQueryExecutionV1,
    execute_model_only_query_v1,
)
from acfqp.phase3e_rapm_consumer_v1 import (
    ABSTRACT_QUERY_KEY,
    LOCAL_QUERY_KEY,
    load_phase3c_model_source_v1,
)
from acfqp.routing_v1 import TerminalClass, TerminalCode, TypedNotApplicable
from acfqp.semantic_verification_v1 import (
    AttestationContextV1,
    SemanticRole,
    semantic_verifier_spec_v1,
    verify_abstract_plan_audit_semantics_v1,
)


ROOT = Path(__file__).resolve().parents[1]
PHASE3C = ROOT / "artifacts" / "phase3c"


def _verification_record(role: SemanticRole) -> CounterRecordV1:
    registry = official_counter_registry_v1()
    spec = semantic_verifier_spec_v1(role)
    return CounterRecordV1.observe(
        registry,
        spec.counter_path_for_lane(LaneEnum.EVALUATION),
        1,
        recorder_id=f"model-only-pass-{role.value.lower()}-evaluation-v1",
    )


def _case(query_key: str):
    source = load_phase3c_model_source_v1(PHASE3C, query_key=query_key)
    execution = execute_model_only_query_v1(source)
    result = execution.model_only_result
    authority = verify_abstract_plan_audit_semantics_v1(
        result.audit,
        source=source,
        model_only_result=result,
        binding=AttestationContextV1(
            result.route_context,
            TypedNotApplicable("model-only audit precedes route decision"),
            TypedNotApplicable("model-only audit precedes local transaction"),
            4,
            LaneEnum.EVALUATION,
        ),
        verification_work_record=_verification_record(SemanticRole.ABSTRACT_AUDIT),
    )
    return source, execution, authority


def _close(execution: ModelOnlyQueryExecutionV1, authority):
    return close_model_only_abstract_pass_v1(
        execution,
        authority,
        work_verification_record=_verification_record(SemanticRole.WORK_VECTOR),
        terminal_verification_record=_verification_record(
            SemanticRole.TERMINAL_CLASSIFICATION
        ),
    )


def test_executor_owned_h1_pass_closes_terminal_and_campaign_with_locked_gates() -> None:
    _source, execution, authority = _case(ABSTRACT_QUERY_KEY)
    closure = _close(execution, authority)
    recorded = execution.recorded_work

    assert closure.terminal_artifact.terminal_class is TerminalClass.PLAN_CERTIFICATE
    assert closure.terminal_artifact.terminal_code is TerminalCode.ABSTRACT_CERTIFIED
    assert closure.terminal_artifact.actual_work_vector_id == (
        recorded.work_vector.work_vector_id
    )
    assert closure.campaign_closure.final_terminal_artifact_id == (
        closure.terminal_artifact.terminal_artifact_id
    )
    assert closure.accounting_status == MODEL_ONLY_PASS_ACCOUNTING_STATUS
    assert closure.official_execution_allowed is False
    assert closure.official_scalar_cost is None
    assert closure.official_N_break_even is None
    assert dict(closure.occurrence_work_sum.aggregate_values) == dict(
        recorded.comparison_vector.values
    )
    assert AbstractOnlyOccurrenceWorkSumV1.from_dict(
        closure.occurrence_work_sum.to_dict()
    ) == closure.occurrence_work_sum


def test_abstract_pass_rejects_copied_campaign_closure_authority() -> None:
    _source, execution, authority = _case(ABSTRACT_QUERY_KEY)
    closure = _close(execution, authority)
    with pytest.raises(
        Phase3EAbstractPassClosureV1Error,
        match="retained minted instance",
    ):
        replace(
            closure,
            campaign_closure=copy.copy(closure.campaign_closure),
        )


def test_closure_never_replans_or_opens_ground_namespace(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _source, execution, authority = _case(ABSTRACT_QUERY_KEY)
    import acfqp.phase3e_ground_handoff_v1 as ground_handoff
    import acfqp.phase3e_model_only_v1 as model_only
    import acfqp.phase3e_rapm_consumer_v1 as consumer

    def forbidden(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("abstract PASS closure crossed a forbidden boundary")

    monkeypatch.setattr(consumer, "solve_portable_pareto", forbidden)
    monkeypatch.setattr(model_only, "select_contingent_plan_v1", forbidden)
    monkeypatch.setattr(
        model_only, "verify_phase3e_model_only_result_without_replanning_v1", forbidden
    )
    monkeypatch.setattr(
        ground_handoff, "open_ground_binding_after_failed_audit_v1", forbidden
    )
    assert _close(execution, authority).terminal_artifact.terminal_code is (
        TerminalCode.ABSTRACT_CERTIFIED
    )


def test_h2_failed_prefix_authority_can_never_enter_pass_closure() -> None:
    _source, execution, authority = _case(LOCAL_QUERY_KEY)
    with pytest.raises(Phase3EAbstractPassClosureV1Error, match="failed-prefix"):
        _close(execution, authority)


def test_raw_work_transport_roundtrip_copy_and_constructor_are_not_authority() -> None:
    source, execution, authority = _case(ABSTRACT_QUERY_KEY)
    verification_args = {
        "work_verification_record": _verification_record(SemanticRole.WORK_VECTOR),
        "terminal_verification_record": _verification_record(
            SemanticRole.TERMINAL_CLASSIFICATION
        ),
    }
    transport = ModelOnlyQueryExecutionArtifactV1.from_dict(
        execution.to_dict(), source=source
    )
    for forged in (execution.recorded_work, transport):
        with pytest.raises(
            Phase3EAbstractPassClosureV1Error, match="executor-owned"
        ):
            close_model_only_abstract_pass_v1(
                forged, authority, **verification_args  # type: ignore[arg-type]
            )
    with pytest.raises(ValueError, match="not minted"):
        ModelOnlyQueryExecutionV1(transport, object())
    with pytest.raises(AttributeError, match="immutable"):
        copy.copy(execution)
    assert verify_model_only_operational_execution_v1(execution) is execution


def test_private_legacy_bare_work_seam_is_not_accepted_by_public_close() -> None:
    import acfqp.phase3e_abstract_pass_closure_v1 as closure_module

    _source, execution, authority = _case(ABSTRACT_QUERY_KEY)
    result = execution.model_only_result
    request = closure_module.ModelOnlyOperationalRequestV1.from_source_lease(
        result.source_lease,
        regret_tolerance=result.audit.regret_tolerance,
    )
    legacy = closure_module._seal_model_only_operational_execution_v1(
        request,
        result,
        execution.recorded_work,
    )
    with pytest.raises(Phase3EAbstractPassClosureV1Error, match="executor-owned"):
        _close(legacy, authority)  # type: ignore[arg-type]
    assert "ModelOnlyOperationalExecutionV1" not in closure_module.__all__
    assert "ModelOnlyOperationalRequestV1" not in closure_module.__all__


def test_raw_or_foreign_audit_claims_fail_closed() -> None:
    _source, execution, authority = _case(ABSTRACT_QUERY_KEY)
    _h2_source, _h2_execution, h2_authority = _case(LOCAL_QUERY_KEY)
    for raw in (
        execution.model_only_result.audit,
        execution.model_only_result.audit.audit_id,
        authority.attestation,
        h2_authority,
    ):
        with pytest.raises(
            Phase3EAbstractPassClosureV1Error,
            match="retained semantic authority|another result",
        ):
            _close(execution, raw)  # type: ignore[arg-type]


def test_ground_inputs_are_rejected_even_with_valid_pass_authority() -> None:
    _source, execution, authority = _case(ABSTRACT_QUERY_KEY)
    for keyword in ("ground_binding", "ground_executor"):
        kwargs = {
            "work_verification_record": _verification_record(SemanticRole.WORK_VECTOR),
            "terminal_verification_record": _verification_record(
                SemanticRole.TERMINAL_CLASSIFICATION
            ),
            keyword: object(),
        }
        with pytest.raises(Phase3EAbstractPassClosureV1Error, match="forbids ground"):
            close_model_only_abstract_pass_v1(execution, authority, **kwargs)


def test_resigned_transport_cannot_change_live_execution_or_work_binding() -> None:
    source, execution, authority = _case(ABSTRACT_QUERY_KEY)
    document = execution.to_dict()
    document["recorded_work"]["work_vector"]["route_kind"] = (
        "ABSTRACT_FAILED_PREFIX"
    )
    with pytest.raises(ValueError):
        ModelOnlyQueryExecutionArtifactV1.from_dict(document, source=source)
    assert _close(execution, authority).terminal_artifact.terminal_code is (
        TerminalCode.ABSTRACT_CERTIFIED
    )


def test_locked_aggregate_content_id_cannot_be_resigned() -> None:
    _source, execution, authority = _case(ABSTRACT_QUERY_KEY)
    closure = _close(execution, authority)
    for field, value, message in (
        ("official_execution_allowed", True, "unlock official execution"),
        ("official_scalar_cost", 0, "invent scalar economics"),
    ):
        document = closure.occurrence_work_sum.to_dict()
        document[field] = value
        with pytest.raises(Phase3EAbstractPassClosureV1Error, match=message):
            AbstractOnlyOccurrenceWorkSumV1.from_dict(document)

    document = closure.occurrence_work_sum.to_dict()
    document["aggregate_values"][0]["value"] += 1
    with pytest.raises(Phase3EAbstractPassClosureV1Error, match="content ID mismatch"):
        AbstractOnlyOccurrenceWorkSumV1.from_dict(document)
