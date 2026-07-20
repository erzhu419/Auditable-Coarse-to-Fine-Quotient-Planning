from __future__ import annotations

from dataclasses import replace
import hashlib

import pytest

from acfqp.accounting_v1 import (
    CounterRecordV1,
    official_comparison_profile_v1,
    official_counter_registry_v1,
)
from acfqp.domains.g2048 import G2048SafeChainKernel
from acfqp.frozen_phase3c import load_frozen_phase3c_world
from acfqp.phase3e_ids import (
    CARDINALITY_EVIDENCE_DOMAIN,
    CARDINALITY_SOURCE_DOMAIN,
    GROUND_FALLBACK_CARDINALITY_BOUND_DOMAIN,
    GROUND_FALLBACK_CARDINALITY_SOURCE_DOMAIN,
    GROUND_FALLBACK_EXTRACTION_PROFILE_DOMAIN,
    GROUND_FALLBACK_PARENT_BINDING_DOMAIN,
    content_id,
)
from acfqp.phase3e_fallback_v1 import (
    GroundFallbackCapProfileV1,
    SafeChainFallbackCardinalitySourceV1,
    build_ground_fallback_cardinality_evidence_v1,
    derive_safe_chain_fallback_cardinality_bound_v1,
    derive_safe_chain_fallback_cardinality_source_v1,
    safe_chain_fallback_context_identity_v1,
)
from acfqp.route_upper_formula_v1 import (
    derive_route_upper_v1,
    official_route_upper_formula_v1,
)
from acfqp.routing_v1 import (
    DecisionPointV1,
    MarginalRouteDecisionV1,
    RouteComparison,
    RouteDecisionContextV1,
    RouteKind,
    RouteSelection,
    TypedNotApplicable,
)
from acfqp.semantic_verification_v1 import (
    AttestationContextV1,
    SemanticRole,
    SemanticVerificationV1Error,
    derive_guarded_marginal_route_decision_v1,
    semantic_verifier_spec_v1,
    verify_route_upper_semantics_v1,
    verify_safe_chain_fallback_cardinality_semantics_v1,
    verify_marginal_route_decision_semantics_v1,
)


def _id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _cap(**overrides: int) -> GroundFallbackCapProfileV1:
    values = {
        "max_states_expanded": 1_000,
        "max_actions_evaluated": 2_000,
        "max_ground_steps": 1_000,
        "max_outcome_rows": 6_000,
        "max_bellman_backups": 200_000,
        "max_composed_candidates": 200_000,
        "max_cap_checks": 300_000,
        "max_positive_outcomes_per_step": 6,
    }
    values.update(overrides)
    return GroundFallbackCapProfileV1(**values)


def _verification_record(role: SemanticRole) -> CounterRecordV1:
    registry = official_counter_registry_v1()
    return CounterRecordV1.observe(
        registry,
        semantic_verifier_spec_v1(role).verification_counter_path,
        1,
        recorder_id=f"{role.value.lower()}-safe-chain-parent-replay-v1",
    )


def _chain(*, cap: GroundFallbackCapProfileV1 | None = None):
    world = load_frozen_phase3c_world("artifacts/phase3c")
    identities = safe_chain_fallback_context_identity_v1(world)
    registry = official_counter_registry_v1()
    profile = official_comparison_profile_v1(registry)
    context = RouteDecisionContextV1(
        _id("fallback-authority-preregistration"),
        _id("fallback-authority-protocol"),
        profile.comparison_profile_id,
        registry.registry_id,
        identities["structural_id"],
        identities["query_id"],
        _id("fallback-authority-selected-plan"),
        _id("fallback-authority-threshold"),
        identities["build_epoch_id"],
        _id("fallback-authority-occurrence"),
        _id("fallback-authority-attempt"),
    )
    point = DecisionPointV1(
        context.route_decision_context_id,
        TypedNotApplicable("fallback-only profile has no local transaction"),
        TypedNotApplicable("fallback-only profile has no local frontier"),
        TypedNotApplicable("fallback-only profile has no causal search"),
        _id("fallback-authority-common-prefix"),
    )
    selected_cap = cap or _cap()
    source = derive_safe_chain_fallback_cardinality_source_v1(
        world=world,
        context=context,
        decision_point=point,
        cap_profile=selected_cap,
        frozen_at_protocol_step=1,
    )
    bound = derive_safe_chain_fallback_cardinality_bound_v1(
        source=source,
        cap_profile=selected_cap,
    )
    cardinality = build_ground_fallback_cardinality_evidence_v1(
        context=context,
        decision_point=point,
        cap_profile=selected_cap,
        bound=bound,
    )
    binding = AttestationContextV1(
        context,
        point.decision_point_id,
        TypedNotApplicable("direct fallback has no local transaction"),
        2,
    )
    return (
        world,
        registry,
        profile,
        context,
        point,
        selected_cap,
        source,
        bound,
        cardinality,
        binding,
    )


def _verify_chain(chain):
    (
        world,
        registry,
        _profile,
        context,
        point,
        cap,
        source,
        bound,
        cardinality,
        binding,
    ) = chain
    return verify_safe_chain_fallback_cardinality_semantics_v1(
        cardinality,
        source=source,
        bound=bound,
        frozen_world=world,
        context=context,
        decision_point=point,
        cap_profile=cap,
        binding=binding,
        verification_work_record=_verification_record(
            SemanticRole.CARDINALITY_EVIDENCE
        ),
        registry=registry,
    )


def test_fallback_source_parent_profile_and_bound_domains_are_not_interchangeable() -> None:
    payload = {"schema": "identical-attack-payload", "value": 1}
    identifiers = {
        content_id(domain, payload)
        for domain in (
            GROUND_FALLBACK_CARDINALITY_SOURCE_DOMAIN,
            GROUND_FALLBACK_PARENT_BINDING_DOMAIN,
            GROUND_FALLBACK_EXTRACTION_PROFILE_DOMAIN,
            GROUND_FALLBACK_CARDINALITY_BOUND_DOMAIN,
        )
    }
    assert len(identifiers) == 4
    assert content_id(CARDINALITY_EVIDENCE_DOMAIN, payload) != content_id(
        CARDINALITY_SOURCE_DOMAIN, payload
    )


def test_safe_chain_fallback_cardinality_replays_frozen_parent_without_step(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    chain = _chain()

    def forbidden_step(*_args, **_kwargs):
        raise AssertionError("kernel.step is forbidden during cardinality replay")

    monkeypatch.setattr(G2048SafeChainKernel, "step", forbidden_step)
    result = _verify_chain(chain)
    source = chain[6]
    bound = chain[7]
    cardinality = chain[8]
    assert result.outcome == "VALID"
    assert result.artifact == cardinality
    assert result.attestation.artifact_id == cardinality.cardinality_evidence_id
    assert SafeChainFallbackCardinalitySourceV1.from_dict(source.to_dict()) == source
    assert dict(bound.bounds)["common.protocol_checks"] == 5
    assert dict(cardinality.counts)["common.protocol_checks"] == 5
    assert dict(cardinality.counts)["common.hash_invocations"] == 0
    assert chain[0].binding_counters["kernel_step_calls"] == 0
    assert chain[0].binding_counters["transition_closure_calls"] == 0


def test_deletion_and_rehash_of_frozen_action_members_is_rejected() -> None:
    chain = _chain()
    source = chain[6]
    deleted = replace(
        source,
        ground_action_member_ids=source.ground_action_member_ids[:-1],
    )
    assert deleted.source_artifact_id != source.source_artifact_id
    assert SafeChainFallbackCardinalitySourceV1.from_dict(deleted.to_dict()) == deleted
    attacked = (*chain[:6], deleted, *chain[7:])
    with pytest.raises(SemanticVerificationV1Error, match="source differs"):
        _verify_chain(attacked)


def test_fallback_cardinality_context_mismatch_is_rejected() -> None:
    chain = _chain()
    source = replace(chain[6], route_decision_context_id=_id("foreign-context"))
    attacked = (*chain[:6], source, *chain[7:])
    with pytest.raises(SemanticVerificationV1Error, match="context mismatch"):
        _verify_chain(attacked)


def test_fallback_cardinality_cap_mismatch_is_rejected() -> None:
    chain = _chain()
    other_cap = _cap(max_states_expanded=1_001)
    attacked = (*chain[:5], other_cap, *chain[6:])
    with pytest.raises(SemanticVerificationV1Error, match="cap mismatch"):
        _verify_chain(attacked)


def test_authoritative_fallback_cardinality_feeds_upper_replay() -> None:
    chain = _chain()
    (
        _world,
        registry,
        profile,
        context,
        point,
        cap,
        _source,
        _bound,
        cardinality,
        binding,
    ) = chain
    cardinality_result = _verify_chain(chain)
    formula = official_route_upper_formula_v1(
        RouteKind.DIRECT_FALLBACK,
        registry=registry,
        profile=profile,
        cap_profile=cap,
    )
    upper, proof = derive_route_upper_v1(
        context=context,
        decision_point=point,
        cardinality=cardinality,
        cap_profile=cap,
        registry=registry,
        profile=profile,
        formula=formula,
    )
    upper_result = verify_route_upper_semantics_v1(
        upper,
        derivation_proof=proof,
        cardinality_result=cardinality_result,
        context=context,
        decision_point=point,
        cap_profile=cap,
        formula=formula,
        transaction=None,
        causal=None,
        binding=binding,
        verification_work_record=_verification_record(SemanticRole.ROUTE_UPPER),
        registry=registry,
    )
    assert upper_result.outcome == "VALID"
    assert dict(proof.leaf_upper_bounds)["common.protocol_checks"] == 5
    assert dict(proof.leaf_upper_bounds)["common.hash_invocations"] == 0


def test_authoritative_fallback_upper_closes_a_fallback_route_decision() -> None:
    chain = _chain()
    (
        _world,
        registry,
        profile,
        context,
        point,
        cap,
        _source,
        _bound,
        cardinality,
        binding,
    ) = chain
    cardinality_result = _verify_chain(chain)
    formula = official_route_upper_formula_v1(
        RouteKind.DIRECT_FALLBACK,
        registry=registry,
        profile=profile,
        cap_profile=cap,
    )
    upper, proof = derive_route_upper_v1(
        context=context,
        decision_point=point,
        cardinality=cardinality,
        cap_profile=cap,
        registry=registry,
        profile=profile,
        formula=formula,
    )
    upper_result = verify_route_upper_semantics_v1(
        upper,
        derivation_proof=proof,
        cardinality_result=cardinality_result,
        context=context,
        decision_point=point,
        cap_profile=cap,
        formula=formula,
        transaction=None,
        causal=None,
        binding=binding,
        verification_work_record=_verification_record(SemanticRole.ROUTE_UPPER),
        registry=registry,
    )
    claimed = derive_guarded_marginal_route_decision_v1(
        context=context,
        decision_point=point,
        fallback_upper_result=upper_result,
        local_upper_result=None,
        causal_result=None,
        binding=binding,
    )
    decision_result = verify_marginal_route_decision_semantics_v1(
        claimed,
        context=context,
        decision_point=point,
        fallback_upper_result=upper_result,
        local_upper_result=None,
        causal_result=None,
        binding=binding,
        verification_work_record=_verification_record(
            SemanticRole.ROUTE_DECISION
        ),
        registry=registry,
    )
    assert isinstance(decision_result.artifact, MarginalRouteDecisionV1)
    assert decision_result.outcome == RouteSelection.FALLBACK.value
    assert decision_result.artifact.comparison is RouteComparison.LOCAL_FORBIDDEN
