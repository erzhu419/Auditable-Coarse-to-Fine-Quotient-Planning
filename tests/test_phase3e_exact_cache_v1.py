from __future__ import annotations

import copy
import dataclasses
from dataclasses import dataclass
from fractions import Fraction
import hashlib
from pathlib import Path

import pytest

from acfqp.accounting_v1 import (
    CounterRecordV1,
    LaneEnum,
    RouteKindEnum,
    explicit_records_v1,
    official_comparison_profile_v1,
    official_counter_registry_v1,
)
from acfqp.core import Outcome, QuerySpec
from acfqp.phase3e_exact_cache_v1 import (
    EXACT_CACHED_INFEASIBILITY_PROOF_DOMAIN,
    EXACT_CACHE_PREFLIGHT_ENTRY_DOMAIN,
    EXACT_CACHE_PREFLIGHT_REQUEST_DOMAIN,
    EXACT_CACHE_PREFLIGHT_RESULT_DOMAIN,
    EXACT_INFEASIBILITY_PROOF_PROFILE_ID,
    EXACT_INFEASIBILITY_PROOF_PROFILE_DOMAIN,
    MISSING_DURABLE_PROOF_BLOCKER,
    NON_OFFICIAL_PREFLIGHT_BLOCKERS,
    PLAN_FROZEN_EXACT_CACHE_BINDING_DOMAIN,
    VERIFIED_EXACT_INFEASIBILITY_SOURCE_DOMAIN,
    ExactCacheOutcome,
    ExactCachePreflightEntryV1,
    ExactCachePreflightRequestV1,
    ExactCachePreflightResultV1,
    ExactCachedInfeasibilityProofV1,
    ExactInfeasibilitySourceArtifactV1,
    Phase3EExactCacheV1Error,
    PlanFrozenExactCacheBindingV1,
    VerifiedExactInfeasibilitySourceV1,
    _content_id,
    build_exact_cached_infeasibility_proof_v1,
    build_exact_cache_preflight_entry_v1,
    build_exact_cache_preflight_request_v1,
    derive_exact_kernel_identity_v1,
    derive_exact_kernel_identity_from_model_source_v1,
    verify_exact_cached_infeasibility_v1,
    verify_exact_cache_preflight_v1,
    verify_exact_infeasibility_source_v1,
)
from acfqp.phase3e_ids import EXACT_KERNEL_CONTEXT_IDENTITY_DOMAIN
from acfqp.phase3e_fallback_v1 import (
    GroundFallbackCapProfileV1,
    _seal_trusted_ground_fallback_execution_v1,
    run_ground_fallback_search_v1,
)
from acfqp.phase3e_rapm_consumer_v1 import (
    LOCAL_QUERY_KEY,
    load_phase3c_model_source_v1,
)
from acfqp.routing_v1 import (
    RouteDecisionContextV1,
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
    verify_exact_cached_infeasibility_semantics_v1,
    verify_ground_fallback_semantics_v1,
    verify_terminal_classification_semantics_v1,
    verify_work_vector_semantics_v1,
)


ROOT = Path(__file__).resolve().parents[1]
PHASE3C = ROOT / "artifacts" / "phase3c"


def _id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class _State:
    label: str


class _OneStepKernel:
    horizon = 1
    registered_reward_features = ("reward",)
    registered_goals = ("default",)

    def __init__(self, *, fails: bool) -> None:
        self.start = _State("start")
        self.end = _State("failure" if fails else "terminal")
        self.action = "advance"
        self.fails = fails

    def reward_upper_bound(self, horizon, raw_weights, goal):
        return Fraction(horizon * raw_weights.get("reward", 0))

    def initial_distribution(self):
        return ((Fraction(1), self.start),)

    def actions(self, state):
        return (self.action,) if state == self.start else ()

    def step(self, state, action):
        assert state == self.start and action == self.action
        return (
            Outcome(
                Fraction(1),
                self.end,
                (("reward", Fraction(1)),),
                failure=self.fails,
                terminal=True,
            ),
        )

    def is_terminal(self, state):
        return state == self.end


def _cap(*, max_cap_checks: int = 100) -> GroundFallbackCapProfileV1:
    return GroundFallbackCapProfileV1(
        max_states_expanded=10,
        max_actions_evaluated=10,
        max_ground_steps=10,
        max_outcome_rows=10,
        max_bellman_backups=10,
        max_composed_candidates=10,
        max_cap_checks=max_cap_checks,
        max_positive_outcomes_per_step=1,
    )


def _context(label: str) -> RouteDecisionContextV1:
    registry = official_counter_registry_v1()
    profile = official_comparison_profile_v1(registry)
    return RouteDecisionContextV1(
        _id(f"{label}:pre"),
        _id(f"{label}:protocol"),
        profile.comparison_profile_id,
        registry.registry_id,
        _id(f"{label}:structural"),
        _id(f"{label}:query"),
        _id(f"{label}:plan"),
        _id(f"{label}:threshold"),
        _id(f"{label}:epoch"),
        _id(f"{label}:occurrence"),
        _id(f"{label}:attempt"),
    )


def _verification_record(
    role: SemanticRole = SemanticRole.GROUND_FALLBACK,
    *,
    lane: LaneEnum = LaneEnum.OPERATIONAL,
) -> CounterRecordV1:
    registry = official_counter_registry_v1()
    spec = semantic_verifier_spec_v1(role)
    return CounterRecordV1.observe(
        registry,
        spec.counter_path_for_lane(lane),
        1,
        recorder_id=f"phase3e-{role.value.lower()}-test-v1",
    )


def _abstract_work(context: RouteDecisionContextV1):
    registry = official_counter_registry_v1()
    values = {path: 0 for path in registry.required_paths}
    return registry.materialize(
        subject_id=context.route_attempt_id,
        route_kind=RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE,
        records=explicit_records_v1(
            registry,
            values,
            recorder_id="phase3e-exact-cache-abstract-work-test-v1",
        ),
    )


def _ground_semantic_result(
    *, fails: bool, cap: GroundFallbackCapProfileV1 | None = None
):
    selected_cap = cap or _cap()
    model_source = load_phase3c_model_source_v1(
        PHASE3C, query_key=LOCAL_QUERY_KEY
    )
    preflight = build_exact_cache_preflight_request_v1(
        model_source,
        complete_search_profile=selected_cap,
    )
    context = dataclasses.replace(
        _context("fails" if fails else "feasible"),
        structural_id=preflight.exact_identity.structural_id,
        query_id=preflight.exact_identity.query_id,
        threshold_profile_id=preflight.exact_identity.threshold_profile_id,
        build_epoch_id=preflight.exact_identity.build_epoch_id,
    )
    point_id = _id(f"{context.route_decision_context_id}:point")
    kernel = _OneStepKernel(fails=fails)
    query = QuerySpec.from_state(
        kernel.start,
        horizon=1,
        reward_weights=(("reward", Fraction(1)),),
        delta=Fraction(1, 20),
    )
    raw = run_ground_fallback_search_v1(
        kernel,
        query,
        route_decision_context_id=context.route_decision_context_id,
        decision_point_id=point_id,
        route_decision_id=_id(f"{point_id}:decision"),
        selected_upper_id=_id(f"{point_id}:upper"),
        route_attempt_id=context.route_attempt_id,
        query_id=context.query_id,
        cap_profile=selected_cap,
    )
    sealed = _seal_trusted_ground_fallback_execution_v1(
        raw, constraint_delta=Fraction(1, 20)
    )
    binding = AttestationContextV1(
        context,
        point_id,
        TypedNotApplicable("direct fallback has no local transaction"),
        20,
    )
    verified = verify_ground_fallback_semantics_v1(
        sealed,
        cap_profile=selected_cap,
        binding=binding,
        verification_work_record=_verification_record(),
    )
    return verified, context, model_source, selected_cap


def _source():
    verified, context, model_source, cap = _ground_semantic_result(fails=True)
    return (
        verify_exact_infeasibility_source_v1(
            verified,
            model_source=model_source,
            complete_search_profile=cap,
        ),
        context,
    )


def test_exact_source_and_lookup_round_trip_with_plan_frozen_context() -> None:
    source, context = _source()
    proof = build_exact_cached_infeasibility_proof_v1(
        source,
        current_context=context,
    )

    assert ExactInfeasibilitySourceArtifactV1.from_dict(
        source.artifact.to_dict()
    ) == source.artifact
    assert PlanFrozenExactCacheBindingV1.from_dict(
        proof.current_binding.to_dict()
    ) == proof.current_binding
    assert ExactCachedInfeasibilityProofV1.from_dict(proof.to_dict()) == proof
    assert proof.current_binding.selected_plan_id == context.selected_plan_id
    assert proof.current_binding.kernel_id == (
        derive_exact_kernel_identity_from_model_source_v1(source.model_source)
    )
    assert (
        verify_exact_cached_infeasibility_v1(
            proof.to_dict(),
            source=source,
            current_context=context,
        )
        is ExactCacheOutcome.IDENTICAL_MATCH
    )


def test_semantic_handler_recomputes_match_and_binds_complete_source_chain() -> None:
    source, context = _source()
    proof = build_exact_cached_infeasibility_proof_v1(
        source,
        current_context=context,
    )
    binding = AttestationContextV1(
        context,
        TypedNotApplicable("cache lookup precedes route decision"),
        TypedNotApplicable("cache lookup has no local transaction"),
        21,
    )

    verified = verify_exact_cached_infeasibility_semantics_v1(
        proof.to_dict(),
        source=source,
        binding=binding,
        verification_work_record=_verification_record(
            SemanticRole.EXACT_CACHED_INFEASIBILITY
        ),
    )

    assert semantic_verifier_spec_v1(
        SemanticRole.EXACT_CACHED_INFEASIBILITY
    ).implemented
    assert verified.role is SemanticRole.EXACT_CACHED_INFEASIBILITY
    assert verified.outcome == "IDENTICAL_MATCH"
    assert verified.artifact == proof
    assert (
        verified.attestation.artifact_id
        == proof.exact_cached_infeasibility_proof_id
    )
    expected_source_evidence = {
        source.artifact.verified_exact_infeasibility_source_id,
        source.artifact.source_ground_fallback_result_id,
        source.artifact.source_ground_fallback_attestation_id,
        source.artifact.source_ground_fallback_work_vector_id,
        source.artifact.source_verification_work_counter_record_id,
        source.artifact.complete_search_profile_id,
    }
    assert set(verified.recomputed_evidence_ids) == expected_source_evidence


def test_semantic_handler_authorizes_cached_exact_infeasibility_terminal() -> None:
    source, context = _source()
    proof = build_exact_cached_infeasibility_proof_v1(
        source,
        current_context=context,
    )
    binding = AttestationContextV1(
        context,
        TypedNotApplicable("cached result has no route decision"),
        TypedNotApplicable("cached result has no local transaction"),
        25,
        LaneEnum.EVALUATION,
    )
    cache_result = verify_exact_cached_infeasibility_semantics_v1(
        proof,
        source=source,
        binding=binding,
        verification_work_record=_verification_record(
            SemanticRole.EXACT_CACHED_INFEASIBILITY,
            lane=LaneEnum.EVALUATION,
        ),
    )
    work = _abstract_work(context)
    work_result = verify_work_vector_semantics_v1(
        work,
        binding=binding,
        verification_work_record=_verification_record(
            SemanticRole.WORK_VECTOR, lane=LaneEnum.EVALUATION
        ),
    )
    evidence_ids = tuple(
        sorted(
            (
                cache_result.attestation.verification_attestation_id,
                work_result.attestation.verification_attestation_id,
            )
        )
    )
    terminal = TerminalArtifactV1(
        "ROUTE_ATTEMPT",
        TerminalClass.INFEASIBILITY_CERTIFICATE,
        TerminalCode.CACHED_EXACT_INFEASIBLE,
        context.route_decision_context_id,
        context.logical_occurrence_id,
        context.route_attempt_id,
        binding.decision_point_id,
        binding.transaction_id,
        work.work_vector_id,
        evidence_ids,
    )

    terminal_result = verify_terminal_classification_semantics_v1(
        terminal,
        evidence_results=(work_result, cache_result),
        binding=binding,
        verification_work_record=_verification_record(
            SemanticRole.TERMINAL_CLASSIFICATION,
            lane=LaneEnum.EVALUATION,
        ),
    )

    assert terminal_result.outcome == TerminalClass.INFEASIBILITY_CERTIFICATE.value
    assert terminal_result.artifact == terminal


def test_semantic_handler_emits_no_match_but_no_cache_certificate() -> None:
    source, context = _source()
    other_context = dataclasses.replace(
        context, threshold_profile_id=_id("another-threshold")
    )
    proof = build_exact_cached_infeasibility_proof_v1(
        source,
        current_context=other_context,
    )
    binding = AttestationContextV1(
        other_context,
        TypedNotApplicable("no decision"),
        TypedNotApplicable("no transaction"),
        22,
    )
    verified = verify_exact_cached_infeasibility_semantics_v1(
        proof,
        source=source,
        binding=binding,
        verification_work_record=_verification_record(
            SemanticRole.EXACT_CACHED_INFEASIBILITY
        ),
    )
    assert verified.outcome == "NO_MATCH"


def test_semantic_handler_rejects_stale_context_splice_and_wrong_work_role() -> None:
    source, context = _source()
    proof = build_exact_cached_infeasibility_proof_v1(
        source,
        current_context=context,
    )
    binding = AttestationContextV1(
        context,
        TypedNotApplicable("no decision"),
        TypedNotApplicable("no transaction"),
        23,
    )
    stale_binding = dataclasses.replace(
        binding,
        route_context=dataclasses.replace(
            context, selected_plan_id=_id("stale-plan")
        ),
    )
    with pytest.raises(SemanticVerificationV1Error, match="semantic replay failed"):
        verify_exact_cached_infeasibility_semantics_v1(
            proof,
            source=source,
            binding=stale_binding,
            verification_work_record=_verification_record(
                SemanticRole.EXACT_CACHED_INFEASIBILITY
            ),
        )

    spliced = dataclasses.replace(
        proof, complete_search_profile_id=_id("foreign-search-profile")
    )
    with pytest.raises(SemanticVerificationV1Error, match="semantic replay failed"):
        verify_exact_cached_infeasibility_semantics_v1(
            spliced,
            source=source,
            binding=binding,
            verification_work_record=_verification_record(
                SemanticRole.EXACT_CACHED_INFEASIBILITY
            ),
        )

    with pytest.raises(Phase3EExactCacheV1Error, match="copied or modified"):
        dataclasses.replace(
            source,
            artifact=dataclasses.replace(
                source.artifact,
                source_ground_fallback_work_vector_id=_id(
                    "authority-lost-work"
                ),
            ),
        )

    with pytest.raises(SemanticVerificationV1Error, match="must use"):
        verify_exact_cached_infeasibility_semantics_v1(
            proof,
            source=source,
            binding=binding,
            verification_work_record=_verification_record(
                SemanticRole.WORK_VECTOR
            ),
        )


def test_exact_cache_domains_are_role_separated_for_identical_payload() -> None:
    payload = {"same": "bytes"}
    identifiers = {
        _content_id(domain, payload)
        for domain in (
            PLAN_FROZEN_EXACT_CACHE_BINDING_DOMAIN,
            VERIFIED_EXACT_INFEASIBILITY_SOURCE_DOMAIN,
            EXACT_CACHED_INFEASIBILITY_PROOF_DOMAIN,
            EXACT_KERNEL_CONTEXT_IDENTITY_DOMAIN,
            EXACT_INFEASIBILITY_PROOF_PROFILE_DOMAIN,
            EXACT_CACHE_PREFLIGHT_REQUEST_DOMAIN,
            EXACT_CACHE_PREFLIGHT_ENTRY_DOMAIN,
            EXACT_CACHE_PREFLIGHT_RESULT_DOMAIN,
        )
    }
    assert len(identifiers) == 8
    with pytest.raises(Phase3EExactCacheV1Error, match="unregistered"):
        _content_id("acfqp:not-an-exact-cache-role:v1", payload)


@pytest.mark.parametrize(
    "coordinate",
    ("threshold_profile_id",),
)
def test_every_exact_identity_mismatch_is_an_ordinary_no_match(
    coordinate: str,
) -> None:
    source, context = _source()
    current_context = context
    current_context = dataclasses.replace(
        context, **{coordinate: _id(f"different-{coordinate}")}
    )
    proof = build_exact_cached_infeasibility_proof_v1(
        source,
        current_context=current_context,
    )
    assert proof.claimed_outcome is ExactCacheOutcome.NO_MATCH
    assert (
        verify_exact_cached_infeasibility_v1(
            proof,
            source=source,
            current_context=current_context,
        )
        is ExactCacheOutcome.NO_MATCH
    )


@pytest.mark.parametrize("coordinate", ("structural_id", "query_id", "build_epoch_id"))
def test_plan_frozen_lookup_rejects_context_detached_from_model_source(
    coordinate: str,
) -> None:
    source, context = _source()
    detached = dataclasses.replace(
        context, **{coordinate: _id(f"detached-{coordinate}")}
    )
    with pytest.raises(Phase3EExactCacheV1Error, match="model-source mismatch"):
        build_exact_cached_infeasibility_proof_v1(
            source,
            current_context=detached,
        )


def test_kernel_coordinate_cannot_be_supplied_or_overridden_by_caller() -> None:
    verified, context, model_source, cap = _ground_semantic_result(fails=True)
    source = verify_exact_infeasibility_source_v1(
        verified,
        model_source=model_source,
        complete_search_profile=cap,
    )
    proof = build_exact_cached_infeasibility_proof_v1(
        source, current_context=context
    )
    attacker_kernel = _id("attacker-free-kernel-coordinate")

    with pytest.raises(TypeError, match="kernel_id"):
        verify_exact_infeasibility_source_v1(  # type: ignore[call-arg]
            verified,
            model_source=model_source,
            complete_search_profile=cap,
            kernel_id=attacker_kernel,
        )
    with pytest.raises(TypeError, match="current_kernel_id"):
        build_exact_cached_infeasibility_proof_v1(  # type: ignore[call-arg]
            source,
            current_context=context,
            current_kernel_id=attacker_kernel,
        )
    with pytest.raises(TypeError, match="current_kernel_id"):
        verify_exact_cached_infeasibility_v1(  # type: ignore[call-arg]
            proof,
            source=source,
            current_context=context,
            current_kernel_id=attacker_kernel,
        )

    changed_authority_context = dataclasses.replace(
        context, protocol_id=_id("changed-kernel-authority-protocol")
    )
    assert derive_exact_kernel_identity_v1(changed_authority_context) != (
        source.artifact.exact_identity.kernel_id
    )

def test_current_plan_is_real_and_bound_but_not_a_reusable_claim_coordinate() -> None:
    source, context = _source()
    another_plan_context = dataclasses.replace(
        context, selected_plan_id=_id("another-real-selected-plan")
    )
    proof = build_exact_cached_infeasibility_proof_v1(
        source,
        current_context=another_plan_context,
    )

    assert proof.current_binding.selected_plan_id == another_plan_context.selected_plan_id
    assert proof.claimed_outcome is ExactCacheOutcome.IDENTICAL_MATCH
    assert (
        verify_exact_cached_infeasibility_v1(
            proof,
            source=source,
            current_context=another_plan_context,
        )
        is ExactCacheOutcome.IDENTICAL_MATCH
    )
    with pytest.raises(Phase3EExactCacheV1Error, match="stale|another"):
        verify_exact_cached_infeasibility_v1(
            proof,
            source=source,
            current_context=context,
        )


def test_resigned_source_reference_splice_is_rejected() -> None:
    source, context = _source()
    proof = build_exact_cached_infeasibility_proof_v1(
        source,
        current_context=context,
    )
    spliced = dataclasses.replace(
        proof,
        source_ground_fallback_attestation_id=_id("foreign-attestation"),
    )
    # dataclasses.replace recomputes a valid outer content ID; replay still
    # rejects the internal reference splice against retained authority.
    ExactCachedInfeasibilityProofV1.from_dict(spliced.to_dict())
    with pytest.raises(Phase3EExactCacheV1Error, match="splices|misbinds"):
        verify_exact_cached_infeasibility_v1(
            spliced,
            source=source,
            current_context=context,
        )


def test_replaced_source_artifact_cannot_reuse_opaque_authority() -> None:
    source, context = _source()
    replaced_artifact = dataclasses.replace(
        source.artifact,
        source_ground_fallback_work_vector_id=_id("foreign-work"),
    )
    with pytest.raises(Phase3EExactCacheV1Error, match="copied or modified"):
        dataclasses.replace(
            source,
            artifact=replaced_artifact,
        )


def test_exact_source_copy_and_identity_replace_are_inert() -> None:
    source, context = _source()
    copied = copy.copy(source)
    with pytest.raises(Phase3EExactCacheV1Error, match="exact retained"):
        build_exact_cached_infeasibility_proof_v1(
            copied,
            current_context=context,
        )
    with pytest.raises(Phase3EExactCacheV1Error, match="copied or modified"):
        dataclasses.replace(source)


def test_raw_feasible_and_cap_exhausted_sources_are_rejected() -> None:
    infeasible_verified, _, infeasible_source, infeasible_cap = (
        _ground_semantic_result(fails=True)
    )
    with pytest.raises(Phase3EExactCacheV1Error, match="retained typed"):
        verify_exact_infeasibility_source_v1(
            infeasible_verified.artifact.to_dict(),
            model_source=infeasible_source,
            complete_search_profile=infeasible_cap,
        )

    feasible_verified, _, feasible_source, feasible_cap = (
        _ground_semantic_result(fails=False)
    )
    with pytest.raises(
        Phase3EExactCacheV1Error,
        match="GROUND_FALLBACK/INFEASIBLE_CERTIFIED",
    ):
        verify_exact_infeasibility_source_v1(
            feasible_verified,
            model_source=feasible_source,
            complete_search_profile=feasible_cap,
        )

    cap_verified, _, cap_source, cap_profile = _ground_semantic_result(
        fails=False, cap=_cap(max_cap_checks=1)
    )
    assert cap_verified.outcome == "CAP_EXHAUSTED"
    with pytest.raises(
        Phase3EExactCacheV1Error,
        match="GROUND_FALLBACK/INFEASIBLE_CERTIFIED",
    ):
        verify_exact_infeasibility_source_v1(
            cap_verified,
            model_source=cap_source,
            complete_search_profile=cap_profile,
        )


def test_malformed_proof_and_untrusted_source_handle_fail_closed() -> None:
    source, context = _source()
    proof = build_exact_cached_infeasibility_proof_v1(
        source,
        current_context=context,
    )
    malformed = proof.to_dict()
    malformed["claimed_outcome"] = "IDENTICAL_MATCH"
    malformed["cached_identity"]["query_id"] = _id("tampered-query")
    with pytest.raises(Phase3EExactCacheV1Error, match="malformed|content ID"):
        verify_exact_cached_infeasibility_v1(
            malformed,
            source=source,
            current_context=context,
        )

    with pytest.raises(Phase3EExactCacheV1Error, match="not minted"):
        VerifiedExactInfeasibilitySourceV1(
            source.artifact,
            source.semantic_result,
            source.model_source,
            source.complete_search_profile,
            object(),
        )


def _preflight_fixture():
    source, _ = _source()
    request = build_exact_cache_preflight_request_v1(
        source.model_source,
        complete_search_profile=source.complete_search_profile,
    )
    entry = build_exact_cache_preflight_entry_v1(source)
    return source, request, entry


def test_planner_free_preflight_round_trip_is_honestly_blocked_and_nonofficial(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source, request, entry = _preflight_fixture()

    import acfqp.phase3e_fallback_v1 as fallback
    import acfqp.phase3e_rapm_consumer_v1 as consumer
    import acfqp.planning.ground as ground
    import acfqp.portable_planner as portable_planner
    import acfqp.portable_sound_audit_v1 as sound_audit

    def forbidden(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("planner/auditor/J0/ground solver entered preflight")

    monkeypatch.setattr(consumer, "select_contingent_plan_v1", forbidden)
    monkeypatch.setattr(portable_planner, "solve_portable_pareto", forbidden)
    monkeypatch.setattr(sound_audit, "build_portable_sound_audit_v1", forbidden)
    monkeypatch.setattr(sound_audit, "verify_portable_sound_audit_v1", forbidden)
    monkeypatch.setattr(ground, "solve_ground_pareto", forbidden)
    monkeypatch.setattr(fallback, "run_ground_fallback_search_v1", forbidden)

    rebuilt_request = build_exact_cache_preflight_request_v1(
        source.model_source,
        complete_search_profile=source.complete_search_profile,
    )
    result = verify_exact_cache_preflight_v1(
        rebuilt_request.to_dict(),
        entry.to_dict(),
        current_model_source=source.model_source,
    )

    assert rebuilt_request == request
    assert ExactCachePreflightRequestV1.from_dict(request.to_dict()) == request
    assert ExactCachePreflightEntryV1.from_dict(entry.to_dict()) == entry
    assert ExactCachePreflightResultV1.from_dict(result.to_dict()) == result
    assert request.to_dict()["selected_plan_id"] is None
    assert result.outcome is ExactCacheOutcome.IDENTICAL_MATCH
    assert result.durable_proof_replay_status == MISSING_DURABLE_PROOF_BLOCKER
    assert result.blockers == NON_OFFICIAL_PREFLIGHT_BLOCKERS
    assert result.authorizes_infeasibility is False
    assert result.official is False
    assert not any(
        (
            result.portable_planner_called,
            result.abstract_auditor_called,
            result.j0_called,
            result.ground_solver_called,
        )
    )
    with pytest.raises(TypeError, match="kernel_id"):
        build_exact_cache_preflight_request_v1(  # type: ignore[call-arg]
            source.model_source,
            complete_search_profile=source.complete_search_profile,
            kernel_id=_id("caller-kernel-label"),
        )


@pytest.mark.parametrize(
    "coordinate",
    (
        "structural_id",
        "query_id",
        "build_epoch_id",
        "kernel_id",
        "manifest_id",
        "threshold_profile_id",
        "complete_search_profile_id",
    ),
)
def test_preflight_rejects_every_changed_identity_coordinate_as_no_match(
    coordinate: str,
) -> None:
    source, request, entry = _preflight_fixture()
    replacement = _id(f"preflight-changed-{coordinate}")
    changed_identity = dataclasses.replace(
        entry.exact_identity,
        **{coordinate: replacement},
    )
    artifact_updates: dict[str, object] = {"exact_identity": changed_identity}
    if coordinate == "complete_search_profile_id":
        artifact_updates["complete_search_profile_id"] = replacement
    changed_artifact = dataclasses.replace(
        entry.source_artifact,
        **artifact_updates,
    )
    changed_entry = ExactCachePreflightEntryV1(changed_artifact)

    result = verify_exact_cache_preflight_v1(
        request,
        changed_entry,
        current_model_source=source.model_source,
    )

    assert result.outcome is ExactCacheOutcome.NO_MATCH
    assert result.mismatched_coordinates == (coordinate,)
    assert result.authorizes_infeasibility is False
    assert result.blockers == ()


def test_changed_proof_profile_and_forged_cache_entry_are_invalid() -> None:
    source, request, entry = _preflight_fixture()
    changed_proof = entry.to_dict()
    changed_proof["source_artifact"]["exact_identity"]["proof_profile_id"] = _id(
        "changed-proof-profile"
    )
    changed_result = verify_exact_cache_preflight_v1(
        request,
        changed_proof,
        current_model_source=source.model_source,
    )
    assert changed_result.outcome is ExactCacheOutcome.INVALID
    assert changed_result.authorizes_infeasibility is False

    forged = entry.to_dict()
    forged["source_artifact"]["source_ground_fallback_result_id"] = _id(
        "forged-ground-result"
    )
    forged_result = verify_exact_cache_preflight_v1(
        request,
        forged,
        current_model_source=source.model_source,
    )
    assert forged_result.outcome is ExactCacheOutcome.INVALID
    assert forged_result.blockers == ("CACHE_ENTRY_SCHEMA_OR_CONTENT_ID_INVALID",)
    assert forged_result.authorizes_infeasibility is False


def test_no_match_or_identical_index_match_cannot_emit_infeasibility() -> None:
    source, request, entry = _preflight_fixture()
    no_match = verify_exact_cache_preflight_v1(
        request,
        None,
        current_model_source=source.model_source,
    )
    identical_but_blocked = verify_exact_cache_preflight_v1(
        request,
        entry,
        current_model_source=source.model_source,
    )

    assert no_match.outcome is ExactCacheOutcome.NO_MATCH
    assert no_match.authorizes_infeasibility is False
    assert identical_but_blocked.outcome is ExactCacheOutcome.IDENTICAL_MATCH
    assert identical_but_blocked.authorizes_infeasibility is False
    with pytest.raises(Phase3EExactCacheV1Error, match="cannot claim"):
        dataclasses.replace(no_match, authorizes_infeasibility=True)
    with pytest.raises(Phase3EExactCacheV1Error, match="cannot claim"):
        dataclasses.replace(identical_but_blocked, authorizes_infeasibility=True)
