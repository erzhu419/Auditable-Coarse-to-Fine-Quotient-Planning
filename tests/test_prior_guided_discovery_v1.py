from __future__ import annotations

import ast
from dataclasses import replace
from fractions import Fraction
import inspect
import json

import pytest

import acfqp.prior_guided_discovery_v1 as prior_module
from acfqp.build_coverage import SuiteBuildCoverage
from acfqp.core import QuerySpec
from acfqp.domains.matching_buffer import LMBState, LMBStatus, generate_solvable_lmb
from acfqp.prior_guided_discovery_v1 import (
    ExactTargetCandidateAuditV1,
    FeatureSubsetHypothesisV1,
    HeldOutTargetProposalV1,
    PriorGuidedDiscoveryInvariantViolation,
    PriorGuidedDiscoveryStatus,
    PriorGuidedExactCertificateV1,
    SourceCandidateEvidenceV1,
    StructuralHypothesisPriorV1,
    build_external_control_structural_prior_v1,
    build_source_candidate_evidence_v1,
    build_structural_hypothesis_prior_v1,
    feature_subset_hypothesis_v1,
    run_prior_guided_lmb_control_v1,
    run_prior_guided_lmb_discovery_v1,
    verify_prior_guided_lmb_control_v1,
    verify_prior_guided_lmb_discovery_v1,
)


def _coverage(kernel, mask: int, buffer: tuple[int, int]) -> SuiteBuildCoverage:
    query = QuerySpec(
        ((Fraction(1), LMBState(mask, buffer, LMBStatus.ACTIVE)),),
        horizon=3,
        reward_weights=(
            ("match", Fraction(1)),
            ("terminal_clear", Fraction(1)),
        ),
        goal="default",
        delta=Fraction(1, 20),
        normalizer=Fraction(4),
        normalizer_proof_id="lmb.canonical.matches_plus_clear_le_2n_over_3.v1",
    )
    result = SuiteBuildCoverage.from_queries(kernel, (query,))
    assert len(result.covered_states) == 7
    return result


@pytest.fixture(scope="module")
def prior_guided_contract():
    kernel, _ = generate_solvable_lmb(
        tile_count=6,
        type_count=2,
        capacity=3,
        max_layers=2,
        seed=0,
    )
    source_coverages = (
        ("lmb-source-mask-11-v0", _coverage(kernel, 11, (1, 2))),
        ("lmb-source-mask-13-v0", _coverage(kernel, 13, (2, 1))),
    )
    target_task_id = "lmb-heldout-mask-7-v0"
    target_coverage = _coverage(kernel, 7, (2, 1))
    hypothesis = feature_subset_hypothesis_v1(
        ("action_count",), ("completes_match",)
    )
    source_evidences = tuple(
        build_source_candidate_evidence_v1(
            kernel,
            coverage,
            source_task_id=task_id,
            hypothesis=hypothesis,
        )
        for task_id, coverage in source_coverages
    )
    prior = build_structural_hypothesis_prior_v1(source_evidences)
    result = run_prior_guided_lmb_discovery_v1(
        kernel,
        target_coverage,
        target_task_id=target_task_id,
        source_evidences=source_evidences,
        prior=prior,
    )
    return (
        kernel,
        source_coverages,
        target_task_id,
        target_coverage,
        hypothesis,
        source_evidences,
        prior,
        result,
    )


def test_source_unanimous_candidate_is_accepted_only_by_exact_heldout_audit(
    prior_guided_contract,
) -> None:
    (
        kernel,
        source_coverages,
        target_task_id,
        target_coverage,
        hypothesis,
        source_evidences,
        prior,
        result,
    ) = prior_guided_contract

    assert result.status is PriorGuidedDiscoveryStatus.EXACT_HELDOUT_HOMOMORPHISM
    assert result.proposal.proposal_is_acceptance_authority is False
    assert result.target_audit.acceptance_authority == (
        "exact_target_ground_homomorphism_audit_v1"
    )
    assert result.target_audit.candidate.exact_homomorphism is True
    assert result.target_audit.hypothesis == hypothesis
    assert result.certificate.exact_homomorphism_verified is True
    assert result.certificate.global_minimality_verified is False
    assert result.certificate.feature_invention_claim is False
    assert result.certificate.sampled_dynamics_claim is False
    assert result.certificate.sample_efficiency_claim is False
    assert result.certificate.official_gate_claim is False
    assert result.portable_build is not None
    assert result.fallback_required is False
    assert result.infeasibility_claim is False

    assert prior.profile == "source_unanimous_exact_v1"
    assert prior.catalogue_size == 4096
    assert prior.broad_support_metadata_only is True
    assert prior.executed_candidate_schedule is False
    assert prior.wide_tail_base_mass > 0
    assert prior.tail_hypothesis_mass > 0
    assert prior.preferred_total_mass > prior.tail_hypothesis_mass
    assert target_task_id not in prior.source_task_ids
    assert tuple(item.source_task_id for item in source_evidences) == prior.source_task_ids
    assert all(item.candidate.exact_homomorphism for item in source_evidences)

    accounting = result.accounting
    assert accounting.acquisition_kind == "EXACT_KERNEL_QUERY"
    assert accounting.interaction_samples == 0
    assert accounting.outcomes_counted_as_interaction_samples is False
    assert accounting.candidate_hypothesis_evaluations == 1
    assert accounting.source_task_count == 2
    assert accounting.source_offline_interaction_samples == 0
    assert accounting.source_offline_candidate_hypothesis_evaluations == 2
    assert accounting.exact_ground_kernel_calls == 21
    assert accounting.unique_ground_state_action_rows == 7
    assert accounting.eligible_ground_state_action_rows == 7
    assert accounting.source_offline_exact_ground_kernel_calls == 14
    assert accounting.source_offline_unique_ground_state_action_rows == 14
    assert accounting.source_offline_eligible_ground_state_action_rows == 14
    for evidence in source_evidences:
        assert evidence.accounting.interaction_samples == 0
        assert (
            evidence.accounting.exact_ground_kernel_calls
            == evidence.accounting.unique_ground_state_action_rows
            == evidence.accounting.eligible_ground_state_action_rows
            == 7
        )

    assert verify_prior_guided_lmb_discovery_v1(
        kernel,
        target_coverage,
        target_task_id=target_task_id,
        source_coverages=source_coverages,
        result=result,
    ) == ()


def test_content_addressed_transport_and_tamper_rejection(
    prior_guided_contract,
) -> None:
    (
        kernel,
        source_coverages,
        target_task_id,
        target_coverage,
        _,
        source_evidences,
        prior,
        result,
    ) = prior_guided_contract
    transport = lambda document: json.loads(json.dumps(document, sort_keys=True))

    assert FeatureSubsetHypothesisV1.from_document(
        transport(result.proposal.hypothesis.to_document())
    ) == result.proposal.hypothesis
    assert SourceCandidateEvidenceV1.from_document(
        transport(source_evidences[0].to_document())
    ) == source_evidences[0]
    assert StructuralHypothesisPriorV1.from_document(
        transport(prior.to_document())
    ) == prior
    assert HeldOutTargetProposalV1.from_document(
        transport(result.proposal.to_document())
    ) == result.proposal
    assert ExactTargetCandidateAuditV1.from_document(
        transport(result.target_audit.to_document())
    ) == result.target_audit
    assert PriorGuidedExactCertificateV1.from_document(
        transport(result.certificate.to_document())
    ) == result.certificate
    assert len(result.result_id) == 64

    tampered_document = transport(result.target_audit.to_document())
    tampered_document["exact_ground_kernel_calls"] += 1
    with pytest.raises(PriorGuidedDiscoveryInvariantViolation, match="ID/document"):
        ExactTargetCandidateAuditV1.from_document(tampered_document)

    tampered_accounting = replace(
        result.accounting,
        exact_ground_kernel_calls=result.accounting.exact_ground_kernel_calls + 1,
    )
    with pytest.raises(PriorGuidedDiscoveryInvariantViolation, match="accounting authority"):
        replace(result, accounting=tampered_accounting)
    resigned_certificate = replace(
        result.certificate, target_task_id="coherently-resigned-inside-certificate"
    )
    with pytest.raises(PriorGuidedDiscoveryInvariantViolation, match="certificate chain"):
        replace(result, certificate=resigned_certificate)
    with pytest.raises(PriorGuidedDiscoveryInvariantViolation, match="duck results"):
        verify_prior_guided_lmb_discovery_v1(
            kernel,
            target_coverage,
            target_task_id=target_task_id,
            source_coverages=source_coverages,
            result={"result_id": result.result_id},  # type: ignore[arg-type]
        )


def test_target_query_value_policy_and_j0_channels_are_absent(
    prior_guided_contract,
) -> None:
    kernel, _, _, target_coverage, _, source_evidences, prior, _ = prior_guided_contract
    signature = inspect.signature(run_prior_guided_lmb_discovery_v1)
    assert tuple(signature.parameters) == (
        "kernel",
        "target_coverage",
        "target_task_id",
        "source_evidences",
        "prior",
    )
    with pytest.raises(PriorGuidedDiscoveryInvariantViolation, match="held-out"):
        run_prior_guided_lmb_discovery_v1(
            kernel,
            target_coverage,
            target_task_id=source_evidences[0].source_task_id,
            source_evidences=source_evidences,
            prior=prior,
        )

    imports = {
        node.module
        for node in ast.walk(ast.parse(inspect.getsource(prior_module)))
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    assert "acfqp.core" not in imports
    assert not any(module.startswith("acfqp.planning") for module in imports)
    assert "query" not in result_field_names()
    assert "value" not in result_field_names()
    assert "policy" not in result_field_names()
    assert "j0" not in result_field_names()


def result_field_names() -> str:
    return " ".join(
        name.lower()
        for name in prior_module.PriorGuidedDiscoveryResultV1.__dataclass_fields__
    )


def test_production_prior_is_source_unanimous_and_not_caller_selected(
    prior_guided_contract,
) -> None:
    kernel, source_coverages, _, _, hypothesis, source_evidences, prior, _ = (
        prior_guided_contract
    )
    signature = inspect.signature(build_structural_hypothesis_prior_v1)
    assert "preferred_hypothesis" not in signature.parameters
    assert prior.preferred_hypothesis == hypothesis
    with pytest.raises(TypeError):
        build_structural_hypothesis_prior_v1(
            source_evidences, preferred_hypothesis=feature_subset_hypothesis_v1((), ())
        )

    rejected = build_source_candidate_evidence_v1(
        kernel,
        source_coverages[0][1],
        source_task_id="nonexact-source-control",
        hypothesis=feature_subset_hypothesis_v1((), ()),
    )
    assert rejected.candidate.exact_homomorphism is False
    with pytest.raises(PriorGuidedDiscoveryInvariantViolation, match="unanimous exact"):
        build_structural_hypothesis_prior_v1((rejected,))

    alternative = build_source_candidate_evidence_v1(
        kernel,
        source_coverages[1][1],
        source_task_id=source_coverages[1][0],
        hypothesis=feature_subset_hypothesis_v1(
            ("branching_count",), ("completes_match",)
        ),
    )
    assert alternative.candidate.exact_homomorphism is True
    with pytest.raises(PriorGuidedDiscoveryInvariantViolation, match="unanimous exact"):
        build_structural_hypothesis_prior_v1((source_evidences[0], alternative))


def test_renamed_target_coverage_identity_is_rejected(
    prior_guided_contract,
) -> None:
    kernel, source_coverages, _, _, _, source_evidences, prior, _ = (
        prior_guided_contract
    )
    with pytest.raises(PriorGuidedDiscoveryInvariantViolation, match="coverage identity"):
        run_prior_guided_lmb_discovery_v1(
            kernel,
            source_coverages[0][1],
            target_task_id="fresh-name-for-a-source-coverage",
            source_evidences=source_evidences,
            prior=prior,
        )


def test_coherently_resigned_different_target_fails_original_context_verifier(
    prior_guided_contract,
) -> None:
    (
        kernel,
        source_coverages,
        target_task_id,
        target_coverage,
        _,
        source_evidences,
        prior,
        result,
    ) = prior_guided_contract
    other_coverage = _coverage(kernel, 19, (1, 2))
    other = run_prior_guided_lmb_discovery_v1(
        kernel,
        other_coverage,
        target_task_id="coherently-resigned-other-target",
        source_evidences=source_evidences,
        prior=prior,
    )
    assert other.status is PriorGuidedDiscoveryStatus.EXACT_HELDOUT_HOMOMORPHISM
    assert other.result_id != result.result_id
    failures = verify_prior_guided_lmb_discovery_v1(
        kernel,
        target_coverage,
        target_task_id=target_task_id,
        source_coverages=source_coverages,
        result=other,
    )
    assert "RESULT_DOCUMENT_MISMATCH" in failures
    assert "PROPOSAL_MISMATCH" in failures
    assert "TARGET_AUDIT_MISMATCH" in failures
    assert "CERTIFICATE_MISMATCH" in failures


def test_wrong_structural_prior_fails_closed_and_requires_fallback(
    prior_guided_contract,
) -> None:
    (
        kernel,
        source_coverages,
        target_task_id,
        target_coverage,
        _,
        source_evidences,
        _,
        _,
    ) = prior_guided_contract
    empty = feature_subset_hypothesis_v1((), ())
    bad_prior = build_external_control_structural_prior_v1(
        source_evidences,
        preferred_hypothesis=empty,
        wide_tail_base_mass=Fraction(1, 10),
    )
    with pytest.raises(PriorGuidedDiscoveryInvariantViolation, match="incompatible prior profile"):
        run_prior_guided_lmb_discovery_v1(
            kernel,
            target_coverage,
            target_task_id=target_task_id,
            source_evidences=source_evidences,
            prior=bad_prior,
        )
    negative = run_prior_guided_lmb_control_v1(
        kernel,
        target_coverage,
        target_task_id=target_task_id,
        source_evidences=source_evidences,
        prior=bad_prior,
    )
    assert negative.status is PriorGuidedDiscoveryStatus.PRIOR_MISMATCH_FALLBACK_REQUIRED
    assert negative.target_audit.candidate.exact_homomorphism is False
    assert negative.target_audit.witness is not None
    assert negative.fallback_required is True
    assert negative.fallback_code == "GROUND_DISCOVERY_OR_DIRECT_OPTIMIZATION_REQUIRED"
    assert negative.infeasibility_claim is False
    assert negative.portable_build is None
    assert negative.quotient_models is None
    assert negative.certificate is None
    assert negative.accounting.interaction_samples == 0
    assert negative.accounting.candidate_hypothesis_evaluations == 1
    assert negative.accounting.exact_ground_kernel_calls == 3
    assert negative.accounting.unique_ground_state_action_rows == 3
    assert negative.accounting.eligible_ground_state_action_rows == 7
    assert verify_prior_guided_lmb_control_v1(
        kernel,
        target_coverage,
        target_task_id=target_task_id,
        source_coverages=source_coverages,
        result=negative,
    ) == ()
    with pytest.raises(PriorGuidedDiscoveryInvariantViolation, match="incompatible prior profile"):
        verify_prior_guided_lmb_discovery_v1(
            kernel,
            target_coverage,
            target_task_id=target_task_id,
            source_coverages=source_coverages,
            result=negative,
        )


def test_one_heldout_portable_model_serves_two_in_coverage_queries(
    prior_guided_contract,
) -> None:
    _, _, _, target_coverage, _, _, _, result = prior_guided_contract
    first_state = target_coverage.declared_support_states[0]
    second_state = next(
        state
        for state in target_coverage.covered_states
        if state.status is LMBStatus.ACTIVE and state != first_state
    )
    first = QuerySpec(
        ((Fraction(1), first_state),),
        horizon=3,
        reward_weights=(("match", Fraction(1)), ("terminal_clear", Fraction(1))),
        goal="default",
        delta=Fraction(1, 20),
        normalizer=Fraction(4),
        normalizer_proof_id="lmb.canonical.matches_plus_clear_le_2n_over_3.v1",
    )
    second = QuerySpec(
        ((Fraction(1), second_state),),
        horizon=2,
        reward_weights=(("match", Fraction(1)), ("terminal_clear", Fraction(0))),
        goal="default",
        delta=Fraction(1, 10),
        normalizer=Fraction(2),
        normalizer_proof_id="lmb.match_only.matches_le_n_over_3.v1",
    )
    portable_first = result.portable_build.query_from_spec(first)
    portable_second = result.portable_build.query_from_spec(second)
    assert portable_first.query_id != portable_second.query_id
    assert result.portable_build.model.model_id == result.certificate.portable_model_id
