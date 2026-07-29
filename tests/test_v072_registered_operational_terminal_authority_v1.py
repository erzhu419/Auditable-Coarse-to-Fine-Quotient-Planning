from __future__ import annotations

from dataclasses import replace
import hashlib
import inspect

import pytest

from acfqp import heldout_graph_transition_observer_v2 as observer
from acfqp import transfer_guided_acquisition_preregistration_v1 as prereg
from acfqp import v072_independent_exact_ground_evaluator_v1 as evaluator
from acfqp import v072_registered_campaign_consumer_v1 as consumer
from acfqp import (
    v072_registered_operational_terminal_authority_v1 as authority,
)


def _id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _occurrence(
    route: authority.RegistrationDisjointTerminalRouteV1,
) -> authority.RegistrationDisjointTerminalOccurrenceV1:
    return authority.RegistrationDisjointTerminalOccurrenceV1(
        f"SYNTHETIC_DISJOINT_OCCURRENCE_{route.value}",
        route,
    )


def _verified_runtime(
    occurrence: authority.RegistrationDisjointTerminalOccurrenceV1,
    *,
    root_action: tuple[int, int, int] = (0, 1, 0),
) -> authority.RegistrationDisjointVerifiedRuntimeResultV1:
    decisions = tuple(
        sorted(
            (
                authority.RegistrationDisjointTerminalChildDecisionV1(
                    occurrence.occurrence_id,
                    _id("synthetic-terminal-state-a"),
                    (1, 2, 0),
                ),
                authority.RegistrationDisjointTerminalChildDecisionV1(
                    occurrence.occurrence_id,
                    _id("synthetic-terminal-state-b"),
                    (2, 3, 1),
                ),
            ),
            key=lambda item: item.state_id,
        )
    )
    return authority.RegistrationDisjointVerifiedRuntimeResultV1(
        occurrence.occurrence_id,
        occurrence.route,
        root_action,
        decisions,
    )


def test_production_authority_accepts_no_terminal_status_or_policy() -> None:
    signature = inspect.signature(
        authority.derive_registered_operational_terminal_authority_v1
    )
    assert tuple(signature.parameters) == (
        "authority_chain",
        "anchor",
        "occurrence_plan",
        "context",
        "verified_runtime_result",
    )
    assert all(
        item.kind is inspect.Parameter.KEYWORD_ONLY
        for item in signature.parameters.values()
    )
    assert {
        "terminal",
        "terminal_code",
        "status",
        "policy",
        "root_action",
        "child_decisions",
        "value",
        "risk",
        "callback",
    }.isdisjoint(signature.parameters)
    core_signature = inspect.signature(
        authority
        .derive_registration_disjoint_operational_terminal_commitment_v1
    )
    assert tuple(core_signature.parameters) == (
        "occurrence_identity",
        "verified_runtime_result",
    )


def test_adapter_protocol_is_exact_and_fail_closed() -> None:
    protocol = (
        authority.inspect_registered_runtime_result_adapter_protocol_v1()
    )
    assert protocol.blockers == ()
    assert authority.ADAPTIVE_RUNTIME_ADAPTER_BLOCKER is None
    assert authority.DIRECT_RUNTIME_ADAPTER_BLOCKER is None
    assert protocol.adaptive_runtime_module.endswith(
        "v072_registered_adaptive_quotient_runtime_v1"
    )
    assert protocol.direct_runtime_module.endswith(
        "v072_registered_matched_direct_runtime_v1"
    )
    assert protocol.evaluator_factory_entrypoint.endswith(
        "mint_registered_occurrence_operational_terminal_policy_v1"
    )
    assert protocol.production_adapters_available is True
    document = protocol.to_document()
    assert (
        document["terminal_status_or_policy_caller_injection_allowed"]
        is False
    )
    assert document["value_or_risk_caller_injection_allowed"] is False


def test_evaluator_factory_is_connected_only_to_private_authority() -> None:
    signature = inspect.signature(
        evaluator.mint_registered_occurrence_operational_terminal_policy_v1
    )
    assert tuple(signature.parameters) == ("mint_authority",)
    assert signature.parameters["mint_authority"].kind is (
        inspect.Parameter.KEYWORD_ONLY
    )
    assert evaluator.REGISTERED_OPERATIONAL_TERMINAL_AUTHORITY_ENABLED is True
    assert evaluator.REGISTERED_EVALUATION_ALLOWED is True
    with pytest.raises(
        evaluator.RegisteredIndependentExactGroundEvaluationLocked,
        match=evaluator.REGISTERED_OPERATIONAL_TERMINAL_BLOCKER,
    ):
        evaluator.mint_registered_occurrence_operational_terminal_policy_v1(
            mint_authority=object(),  # type: ignore[arg-type]
        )


def test_invalid_production_inputs_fail_before_target_access(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def forbidden(*_args: object, **_kwargs: object) -> None:
        calls.append("TARGET_ACCESS")
        raise AssertionError("terminal authority touched registered target")

    for module, name in (
        (observer, "_environment_law"),
        (observer, "open_heldout_target_transition_stream_v2"),
        (observer, "evaluation_only_exact_atoms_v2"),
        (observer.AnchorGatedHeldoutTransitionStreamV2, "draw"),
    ):
        monkeypatch.setattr(module, name, forbidden)
    with pytest.raises(
        authority.RegisteredOperationalTerminalAuthorityLockedV1
    ) as captured:
        authority.derive_registered_operational_terminal_authority_v1(
            authority_chain=object(),  # type: ignore[arg-type]
            anchor=object(),  # type: ignore[arg-type]
            occurrence_plan=object(),  # type: ignore[arg-type]
            context=object(),  # type: ignore[arg-type]
            verified_runtime_result=object(),  # type: ignore[arg-type]
        )
    assert captured.value.access_audit == authority.ZERO_ACCESS_AUDIT
    assert captured.value.access_audit.target_access_started is False
    assert calls == []


@pytest.mark.parametrize(
    ("route", "terminal_code"),
    (
        (
            authority.RegistrationDisjointTerminalRouteV1
            .ADAPTIVE_QUOTIENT,
            "CONDITIONAL_PLAN_CERTIFICATE",
        ),
        (
            authority.RegistrationDisjointTerminalRouteV1
            .MATCHED_DIRECT_GROUND,
            "CONDITIONAL_PLAN_CERTIFICATE",
        ),
    ),
)
def test_registration_disjoint_verified_runtime_derives_terminal_policy(
    route: authority.RegistrationDisjointTerminalRouteV1,
    terminal_code: str,
) -> None:
    occurrence = _occurrence(route)
    runtime_result = _verified_runtime(occurrence)
    result = (
        authority
        .derive_registration_disjoint_operational_terminal_commitment_v1(
            occurrence_identity=occurrence,
            verified_runtime_result=runtime_result,
        )
    )
    assert result.terminal_code == terminal_code
    assert result.occurrence_id == occurrence.occurrence_id
    assert result.runtime_result_id == runtime_result.runtime_result_id
    assert result.independent_verification_id == (
        runtime_result.independent_verification_id
    )
    assert len(result.selected_policy_id) == 64
    assert len(result.operational_terminal_id) == 64
    document = result.to_document()
    assert document["terminal_status_or_policy_caller_supplied"] is False
    assert document["production_authority_minted"] is False
    assert document["registered_target_accesses"] == 0


def test_commitment_is_deterministic_and_runtime_bound() -> None:
    occurrence = _occurrence(
        authority.RegistrationDisjointTerminalRouteV1.ADAPTIVE_QUOTIENT
    )
    first_runtime = _verified_runtime(occurrence)
    first = (
        authority
        .derive_registration_disjoint_operational_terminal_commitment_v1(
            occurrence_identity=occurrence,
            verified_runtime_result=first_runtime,
        )
    )
    replay = (
        authority
        .derive_registration_disjoint_operational_terminal_commitment_v1(
            occurrence_identity=occurrence,
            verified_runtime_result=first_runtime,
        )
    )
    changed_runtime = _verified_runtime(
        occurrence,
        root_action=(0, 2, 1),
    )
    changed = (
        authority
        .derive_registration_disjoint_operational_terminal_commitment_v1(
            occurrence_identity=occurrence,
            verified_runtime_result=changed_runtime,
        )
    )
    assert first == replay
    assert first.commitment_id == replay.commitment_id
    assert first.selected_policy_id != changed.selected_policy_id
    assert first.operational_terminal_id != changed.operational_terminal_id
    assert first.commitment_id != changed.commitment_id


def test_transplanted_occurrence_and_route_are_rejected() -> None:
    adaptive = _occurrence(
        authority.RegistrationDisjointTerminalRouteV1.ADAPTIVE_QUOTIENT
    )
    direct = _occurrence(
        authority.RegistrationDisjointTerminalRouteV1.MATCHED_DIRECT_GROUND
    )
    adaptive_runtime = _verified_runtime(adaptive)
    with pytest.raises(
        authority.V072RegisteredOperationalTerminalAuthorityViolation,
        match="transplanted",
    ):
        authority.derive_registration_disjoint_operational_terminal_commitment_v1(
            occurrence_identity=direct,
            verified_runtime_result=adaptive_runtime,
        )
    route_rebound = replace(adaptive_runtime, route=direct.route)
    with pytest.raises(
        authority.V072RegisteredOperationalTerminalAuthorityViolation,
        match="transplanted",
    ):
        authority.derive_registration_disjoint_operational_terminal_commitment_v1(
            occurrence_identity=adaptive,
            verified_runtime_result=route_rebound,
        )


def test_duplicate_child_decision_scope_is_rejected() -> None:
    occurrence = _occurrence(
        authority.RegistrationDisjointTerminalRouteV1.ADAPTIVE_QUOTIENT
    )
    runtime_result = _verified_runtime(occurrence)
    duplicate = (
        runtime_result.child_decisions[0],
        runtime_result.child_decisions[0],
    )
    with pytest.raises(
        authority.V072RegisteredOperationalTerminalAuthorityViolation,
        match="malformed",
    ):
        authority.RegistrationDisjointVerifiedRuntimeResultV1(
            occurrence.occurrence_id,
            occurrence.route,
            runtime_result.root_action,
            duplicate,
        )


def test_registration_disjoint_result_has_no_status_or_terminal_input() -> None:
    fields = (
        authority.RegistrationDisjointVerifiedRuntimeResultV1
        .__dataclass_fields__
    )
    assert {
        "status",
        "terminal",
        "terminal_code",
        "selected_policy_id",
        "value",
        "risk",
    }.isdisjoint(fields)


def test_both_production_adapters_replay_before_policy_extraction() -> None:
    adaptive_source = inspect.getsource(
        authority
        .derive_registered_adaptive_operational_terminal_authority_v1
    )
    direct_source = inspect.getsource(
        authority
        .derive_registered_matched_direct_operational_terminal_authority_v1
    )
    assert adaptive_source.index(
        "verify_registered_adaptive_quotient_occurrence_result_v1"
    ) < adaptive_source.index("_kappa_spec_from_adaptive_decision")
    assert direct_source.index(
        "verify_registered_matched_direct_occurrence_result_v1"
    ) < direct_source.index("_kappa_spec_from_direct_decision")
    assert "claimed=verified_runtime_result.execution" in adaptive_source
    assert "verified_runtime_result.selected_policy" in direct_source


def test_fixed_kappa_spec_rejects_duplicate_or_nonuniform_support() -> None:
    base = dict(
        ground_state_id=_id("ground-state"),
        public_state_id=_id("public-state"),
        state_ranks=(1, 1, 0, 0, 0, 0, 0),
        remaining_horizon=2,
        semantic_action_id=_id("semantic-selector"),
        ground_action_ids=(_id("action-a"), _id("action-b")),
        ground_semantic_action_ids=(
            _id("semantic-action-a"),
            _id("semantic-action-b"),
        ),
        ground_actions=((0, 1, 0), (0, 1, 1)),
        source_action_realization_artifact_id=_id("concretizer"),
    )
    with pytest.raises(
        authority.RegisteredOperationalTerminalAuthorityLockedV1,
        match="fixed-kappa",
    ):
        authority.RegisteredVerifiedKappaDecisionSpecV1(
            authority._VERIFIED_KAPPA_SPEC_SENTINEL,
            **base,
            uniform_weights=(evaluator.Fraction(3, 4), evaluator.Fraction(1, 4)),
        )
    duplicate = {
        **base,
        "ground_actions": ((0, 1, 0), (0, 1, 0)),
    }
    with pytest.raises(
        authority.RegisteredOperationalTerminalAuthorityLockedV1,
        match="fixed-kappa",
    ):
        authority.RegisteredVerifiedKappaDecisionSpecV1(
            authority._VERIFIED_KAPPA_SPEC_SENTINEL,
            **duplicate,
            uniform_weights=(evaluator.Fraction(1, 2),) * 2,
        )


def test_terminal_code_is_never_exact_feasible_fallback() -> None:
    source = inspect.getsource(authority)
    assert '"EXACT_FEASIBLE_FALLBACK"' not in source
    assert authority.PRODUCTION_ADAPTERS_AVAILABLE is True


def test_cross_route_disguise_and_direct_nonsingleton_are_rejected() -> None:
    context = prereg.registered_heldout_public_contexts_v2()[0]
    adaptive_occurrence = evaluator.RegisteredOccurrenceIdentityV1(
        _id("adapter-anchor"),
        context.context_id,
        context.context_key,
        prereg.ARM_ORDER[0],
        0,
        0,
        0,
    )
    spec = authority.RegisteredVerifiedKappaDecisionSpecV1(
        authority._VERIFIED_KAPPA_SPEC_SENTINEL,
        _id("adapter-ground-state"),
        _id("adapter-public-state"),
        (1, 1, 0, 0, 0, 0, 0),
        2,
        _id("adapter-semantic-action"),
        (_id("adapter-action-a"), _id("adapter-action-b")),
        (
            _id("adapter-semantic-action-a"),
            _id("adapter-semantic-action-b"),
        ),
        ((0, 1, 0), (0, 1, 1)),
        (evaluator.Fraction(1, 2), evaluator.Fraction(1, 2)),
        _id("adapter-concretizer"),
    )
    with pytest.raises(
        authority.RegisteredOperationalTerminalAuthorityLockedV1
    ):
        authority.RegisteredVerifiedOccurrenceRuntimeAdapterV1(
            authority._VERIFIED_RUNTIME_ADAPTER_SENTINEL,
            consumer.RegisteredRouteKindV1.MATCHED_DIRECT_GROUND,
            adaptive_occurrence,
            _id("adapter-runtime"),
            _id("adapter-verification"),
            spec,
            (),
        )
    direct_arm_ordinal = prereg.ARM_ORDER.index("MATCHED_DIRECT_GROUND")
    direct_occurrence = evaluator.RegisteredOccurrenceIdentityV1(
        _id("adapter-anchor"),
        context.context_id,
        context.context_key,
        "MATCHED_DIRECT_GROUND",
        0,
        direct_arm_ordinal,
        direct_arm_ordinal,
    )
    with pytest.raises(
        authority.RegisteredOperationalTerminalAuthorityLockedV1
    ):
        authority.RegisteredVerifiedOccurrenceRuntimeAdapterV1(
            authority._VERIFIED_RUNTIME_ADAPTER_SENTINEL,
            consumer.RegisteredRouteKindV1.MATCHED_DIRECT_GROUND,
            direct_occurrence,
            _id("adapter-runtime"),
            _id("adapter-verification"),
            spec,
            (),
        )


def test_noncertificate_paths_are_checked_before_terminal_mint() -> None:
    adaptive_source = inspect.getsource(
        authority
        .derive_registered_adaptive_operational_terminal_authority_v1
    )
    direct_source = inspect.getsource(
        authority
        .derive_registered_matched_direct_operational_terminal_authority_v1
    )
    assert "RegisteredAdaptiveOccurrenceStatusV1.CERTIFIED" in adaptive_source
    assert "RegisteredMatchedDirectTerminalClassV1.PLAN_CERTIFICATE" in (
        direct_source
    )
    assert "selected is None" in direct_source


def test_private_mint_retains_full_kappa_without_representative_selection(
) -> None:
    context = prereg.registered_heldout_public_contexts_v2()[0]
    state = observer.HeldoutSymbolicGraphStateV2(context.root_ranks)
    catalogue = observer.legal_action_catalogue_v2(context, state, 2)
    assert len(catalogue.actions) >= 2
    aligned = tuple(
        sorted(
            (
                (_id(f"private-ground-action-{index}"), action)
                for index, action in enumerate(catalogue.actions[:2])
            )
        )
    )
    ground_ids = tuple(item[0] for item in aligned)
    actions = tuple(item[1] for item in aligned)
    semantic_ids = tuple(
        observer.observation_row_binding_v2(
            context, catalogue, action
        ).row_binding_id
        for action in actions
    )
    spec = authority.RegisteredVerifiedKappaDecisionSpecV1(
        authority._VERIFIED_KAPPA_SPEC_SENTINEL,
        _id("private-ground-state"),
        state.state_id,
        state.ranks,
        2,
        _id("private-abstract-semantic-action"),
        ground_ids,
        semantic_ids,
        actions,
        (evaluator.Fraction(1, 2), evaluator.Fraction(1, 2)),
        _id("private-concretizer"),
    )
    occurrence = evaluator.RegisteredOccurrenceIdentityV1(
        _id("private-mint-anchor"),
        context.context_id,
        context.context_key,
        prereg.ARM_ORDER[0],
        0,
        0,
        0,
    )
    adapter = authority.RegisteredVerifiedOccurrenceRuntimeAdapterV1(
        authority._VERIFIED_RUNTIME_ADAPTER_SENTINEL,
        consumer.RegisteredRouteKindV1.ADAPTIVE_QUOTIENT,
        occurrence,
        _id("private-runtime-result"),
        _id("private-runtime-verification"),
        spec,
        (),
    )
    mint = authority.RegisteredEvaluatorTerminalMintAuthorityV1(
        authority._EVALUATOR_MINT_AUTHORITY_SENTINEL,
        adapter,
    )
    bundle = (
        evaluator.mint_registered_occurrence_operational_terminal_policy_v1(
            mint_authority=mint
        )
    )
    assert bundle.operational_terminal.terminal_code == (
        "CONDITIONAL_PLAN_CERTIFICATE"
    )
    assert bundle.selected_policy.root_decision.ground_actions == actions
    assert bundle.selected_policy.root_decision.uniform_weights == (
        evaluator.Fraction(1, 2),
        evaluator.Fraction(1, 2),
    )
    assert not hasattr(bundle.selected_policy, "root_action")
