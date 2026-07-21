from __future__ import annotations

import copy
from dataclasses import fields, replace
from fractions import Fraction
import hashlib
from pathlib import Path

import pytest

from acfqp.accounting_v1 import (
    CounterRecordV1,
    LaneEnum,
    RouteKindEnum,
    explicit_records_v1,
    official_counter_registry_v1,
)
from acfqp.phase3e_model_only_v1 import (
    Phase3EModelOnlyResultV1,
    run_phase3e_model_only_v1,
)
from acfqp.phase3e_rapm_consumer_v1 import (
    ABSTRACT_QUERY_KEY,
    LOCAL_QUERY_KEY,
    load_phase3c_model_source_v1,
)
from acfqp.routing_v1 import (
    TerminalArtifactV1,
    TerminalClass,
    TerminalCode,
    TypedNotApplicable,
)
from acfqp.semantic_verification_v1 import (
    AttestationContextV1,
    SemanticRole,
    SemanticVerificationV1Error,
    semantic_verifier_spec_v1,
    verify_abstract_plan_audit_semantics_v1,
    verify_terminal_classification_semantics_v1,
    verify_work_vector_semantics_v1,
)


ROOT = Path(__file__).resolve().parents[1]
PHASE3C = ROOT / "artifacts" / "phase3c"


def _id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _binding(
    result: Phase3EModelOnlyResultV1,
    *,
    lane: LaneEnum = LaneEnum.OPERATIONAL,
    context: object | None = None,
) -> AttestationContextV1:
    return AttestationContextV1(
        result.route_context if context is None else context,  # type: ignore[arg-type]
        TypedNotApplicable("model-only audit precedes route decision"),
        TypedNotApplicable("model-only audit precedes local transaction"),
        4,
        lane,
    )


def _record(
    role: SemanticRole,
    *,
    lane: LaneEnum = LaneEnum.OPERATIONAL,
) -> CounterRecordV1:
    registry = official_counter_registry_v1()
    spec = semantic_verifier_spec_v1(role)
    return CounterRecordV1.observe(
        registry,
        spec.counter_path_for_lane(lane),
        1,
        recorder_id=f"abstract-audit-{role.value.lower()}-test-v1",
    )


def _abstract_work(result: Phase3EModelOnlyResultV1):
    registry = official_counter_registry_v1()
    values = {path: 0 for path in registry.required_paths}
    return registry.materialize(
        subject_id=result.route_context.route_attempt_id,
        route_kind=RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE,
        records=explicit_records_v1(
            registry,
            values,
            recorder_id="abstract-audit-work-test-v1",
        ),
    )


def _unsafe_result_replace(
    result: Phase3EModelOnlyResultV1,
    **changes: object,
) -> Phase3EModelOnlyResultV1:
    """Build hostile transport while deliberately bypassing dataclass guards."""

    forged = object.__new__(Phase3EModelOnlyResultV1)
    for field in fields(Phase3EModelOnlyResultV1):
        object.__setattr__(
            forged,
            field.name,
            changes.get(field.name, getattr(result, field.name)),
        )
    return forged


def test_abstract_audit_semantics_replays_h1_pass_without_replanning(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = load_phase3c_model_source_v1(PHASE3C, query_key=ABSTRACT_QUERY_KEY)
    model_only = run_phase3e_model_only_v1(
        PHASE3C, query_key=ABSTRACT_QUERY_KEY
    )

    import acfqp.phase3e_model_only_v1 as model_only_module
    import acfqp.phase3e_rapm_consumer_v1 as consumer_module

    def forbidden(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("ABSTRACT_AUDIT semantic replay invoked a planner")

    monkeypatch.setattr(consumer_module, "solve_portable_pareto", forbidden)
    monkeypatch.setattr(
        model_only_module.Phase3EModelOnlyResultV1,
        "from_dict",
        classmethod(forbidden),
    )
    binding = _binding(model_only)
    verified = verify_abstract_plan_audit_semantics_v1(
        model_only.audit,
        source=source,
        model_only_result=model_only,
        binding=binding,
        verification_work_record=_record(SemanticRole.ABSTRACT_AUDIT),
    )

    assert semantic_verifier_spec_v1(SemanticRole.ABSTRACT_AUDIT).implemented
    assert verified.outcome == "PASS"
    assert verified.artifact == model_only.audit
    assert verified.attestation.artifact_id == model_only.audit.audit_id
    assert set(verified.recomputed_evidence_ids) == {
        source.lease.source_lease_id,
        model_only.selected_plan.selected_contingent_plan_id,
        model_only.sound_proof.proof_id,
        model_only.result_id,
        model_only.identities.identities_id,
        model_only.rebuild_policy.rebuild_policy_id,
        model_only.logical_occurrence.logical_occurrence_id,
        model_only.route_attempt.route_attempt_id,
        model_only.route_context.route_decision_context_id,
    }


def test_abstract_audit_rejects_source_copy_without_live_loader_authority() -> None:
    source = load_phase3c_model_source_v1(
        PHASE3C, query_key=ABSTRACT_QUERY_KEY
    )
    model_only = run_phase3e_model_only_v1(
        PHASE3C, query_key=ABSTRACT_QUERY_KEY
    )
    with pytest.raises(
        SemanticVerificationV1Error,
        match="live loader authority",
    ):
        verify_abstract_plan_audit_semantics_v1(
            model_only.audit,
            source=copy.copy(source),
            model_only_result=model_only,
            binding=_binding(model_only),
            verification_work_record=_record(SemanticRole.ABSTRACT_AUDIT),
        )


def test_h1_abstract_audit_closes_abstract_certified_terminal() -> None:
    source = load_phase3c_model_source_v1(PHASE3C, query_key=ABSTRACT_QUERY_KEY)
    model_only = run_phase3e_model_only_v1(
        PHASE3C, query_key=ABSTRACT_QUERY_KEY
    )
    binding = _binding(model_only, lane=LaneEnum.EVALUATION)
    audit_result = verify_abstract_plan_audit_semantics_v1(
        model_only.audit,
        source=source,
        model_only_result=model_only,
        binding=binding,
        verification_work_record=_record(
            SemanticRole.ABSTRACT_AUDIT, lane=LaneEnum.EVALUATION
        ),
    )
    work_result = verify_work_vector_semantics_v1(
        _abstract_work(model_only),
        binding=binding,
        verification_work_record=_record(
            SemanticRole.WORK_VECTOR, lane=LaneEnum.EVALUATION
        ),
    )
    evidence_ids = tuple(
        sorted(
            (
                audit_result.attestation.verification_attestation_id,
                work_result.attestation.verification_attestation_id,
            )
        )
    )
    terminal = TerminalArtifactV1(
        "ROUTE_ATTEMPT",
        TerminalClass.PLAN_CERTIFICATE,
        TerminalCode.ABSTRACT_CERTIFIED,
        model_only.route_context.route_decision_context_id,
        model_only.route_context.logical_occurrence_id,
        model_only.route_context.route_attempt_id,
        binding.decision_point_id,
        binding.transaction_id,
        work_result.attestation.artifact_id,
        evidence_ids,
    )
    verified_terminal = verify_terminal_classification_semantics_v1(
        terminal,
        evidence_results=(work_result, audit_result),
        binding=binding,
        verification_work_record=_record(
            SemanticRole.TERMINAL_CLASSIFICATION,
            lane=LaneEnum.EVALUATION,
        ),
    )
    assert verified_terminal.outcome == TerminalClass.PLAN_CERTIFICATE.value
    assert verified_terminal.artifact.terminal_code is TerminalCode.ABSTRACT_CERTIFIED


def test_h2_fail_is_authoritative_but_cannot_masquerade_as_abstract_certificate() -> None:
    source = load_phase3c_model_source_v1(PHASE3C, query_key=LOCAL_QUERY_KEY)
    model_only = run_phase3e_model_only_v1(PHASE3C, query_key=LOCAL_QUERY_KEY)
    binding = _binding(model_only, lane=LaneEnum.EVALUATION)
    audit_result = verify_abstract_plan_audit_semantics_v1(
        model_only.audit,
        source=source,
        model_only_result=model_only,
        binding=binding,
        verification_work_record=_record(
            SemanticRole.ABSTRACT_AUDIT, lane=LaneEnum.EVALUATION
        ),
    )
    assert audit_result.outcome == "FAIL"
    assert audit_result.artifact.policy_failure_upper == Fraction(5099, 10000)
    work_result = verify_work_vector_semantics_v1(
        _abstract_work(model_only),
        binding=binding,
        verification_work_record=_record(
            SemanticRole.WORK_VECTOR, lane=LaneEnum.EVALUATION
        ),
    )
    terminal = TerminalArtifactV1(
        "ROUTE_ATTEMPT",
        TerminalClass.PLAN_CERTIFICATE,
        TerminalCode.ABSTRACT_CERTIFIED,
        model_only.route_context.route_decision_context_id,
        model_only.route_context.logical_occurrence_id,
        model_only.route_context.route_attempt_id,
        binding.decision_point_id,
        binding.transaction_id,
        work_result.attestation.artifact_id,
        tuple(
            sorted(
                (
                    work_result.attestation.verification_attestation_id,
                    audit_result.attestation.verification_attestation_id,
                )
            )
        ),
    )
    with pytest.raises(
        SemanticVerificationV1Error,
        match="ABSTRACT_AUDIT=PASS",
    ):
        verify_terminal_classification_semantics_v1(
            terminal,
            evidence_results=(work_result, audit_result),
            binding=binding,
            verification_work_record=_record(
                SemanticRole.TERMINAL_CLASSIFICATION,
                lane=LaneEnum.EVALUATION,
            ),
        )


def test_resigned_audit_proof_plan_context_and_work_attacks_fail_closed() -> None:
    source = load_phase3c_model_source_v1(PHASE3C, query_key=ABSTRACT_QUERY_KEY)
    model_only = run_phase3e_model_only_v1(
        PHASE3C, query_key=ABSTRACT_QUERY_KEY
    )
    binding = _binding(model_only)

    forged_audit = replace(
        model_only.audit,
        reachable_cell_horizon_pairs=(
            model_only.audit.reachable_cell_horizon_pairs + 1
        ),
    )
    with pytest.raises(SemanticVerificationV1Error, match="claimed abstract audit"):
        verify_abstract_plan_audit_semantics_v1(
            forged_audit,
            source=source,
            model_only_result=model_only,
            binding=binding,
            verification_work_record=_record(SemanticRole.ABSTRACT_AUDIT),
        )

    forged_row = replace(
        model_only.sound_proof.unrestricted_rows[0],
        reward_upper=(
            model_only.sound_proof.unrestricted_rows[0].reward_upper
            + Fraction(1, 1000)
        ),
    )
    forged_proof = replace(
        model_only.sound_proof,
        unrestricted_rows=tuple(
            sorted((forged_row, *model_only.sound_proof.unrestricted_rows[1:]))
        ),
    )
    forged_proof_audit = replace(model_only.audit, proof_id=forged_proof.proof_id)
    forged_proof_result = _unsafe_result_replace(
        model_only,
        sound_proof=forged_proof,
        audit=forged_proof_audit,
    )
    with pytest.raises(SemanticVerificationV1Error, match="false, incomplete"):
        verify_abstract_plan_audit_semantics_v1(
            forged_proof_audit,
            source=source,
            model_only_result=forged_proof_result,
            binding=binding,
            verification_work_record=_record(SemanticRole.ABSTRACT_AUDIT),
        )

    forged_plan = replace(
        model_only.selected_plan,
        proposal_source="attacker_re_signed_selector_claim",
    )
    forged_plan_result = _unsafe_result_replace(
        model_only,
        selected_plan=forged_plan,
    )
    with pytest.raises(SemanticVerificationV1Error, match="selected plan"):
        verify_abstract_plan_audit_semantics_v1(
            model_only.audit,
            source=source,
            model_only_result=forged_plan_result,
            binding=binding,
            verification_work_record=_record(SemanticRole.ABSTRACT_AUDIT),
        )

    forged_context = replace(
        model_only.route_context,
        threshold_profile_id=_id("forged-threshold-profile"),
    )
    with pytest.raises(SemanticVerificationV1Error, match="attestation context"):
        verify_abstract_plan_audit_semantics_v1(
            model_only.audit,
            source=source,
            model_only_result=model_only,
            binding=_binding(model_only, context=forged_context),
            verification_work_record=_record(SemanticRole.ABSTRACT_AUDIT),
        )

    with pytest.raises(SemanticVerificationV1Error, match="must use"):
        verify_abstract_plan_audit_semantics_v1(
            model_only.audit,
            source=source,
            model_only_result=model_only,
            binding=binding,
            verification_work_record=_record(SemanticRole.WORK_VECTOR),
        )
