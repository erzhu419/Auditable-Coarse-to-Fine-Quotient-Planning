from __future__ import annotations

from dataclasses import replace
import hashlib
from pathlib import Path

import pytest

from acfqp.accounting_v1 import (
    CounterRecordV1,
    official_comparison_profile_v1,
    official_counter_registry_v1,
)
from acfqp.frozen_phase3c import load_frozen_phase3c_world
from acfqp.phase3e_fallback_v1 import (
    GroundFallbackCapProfileV1,
    GroundFallbackCardinalityBoundV1,
    GroundFallbackOutcome,
    build_ground_fallback_cardinality_evidence_v1,
    derive_safe_chain_fallback_cardinality_bound_v1,
    derive_safe_chain_fallback_cardinality_source_v1,
    execute_authorized_ground_fallback_v1,
    safe_chain_fallback_context_identity_v1,
)
from acfqp.route_upper_formula_v1 import (
    CapMode,
    RouteUpperFormulaV1Error,
    derive_route_upper_v1,
    official_route_upper_formula_v1,
)
from acfqp.routing_v1 import (
    DecisionPointV1,
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
    verify_ground_fallback_semantics_v1,
    verify_marginal_route_decision_semantics_v1,
    verify_route_upper_semantics_v1,
    verify_safe_chain_fallback_cardinality_semantics_v1,
)


ROOT = Path(__file__).resolve().parents[1]


def _id(label: str) -> str:
    return hashlib.sha256(
        b"acfqp:phase3e-fallback-cap-min-test:v1\x00" + label.encode("utf-8")
    ).hexdigest()


def _record(role: SemanticRole) -> CounterRecordV1:
    registry = official_counter_registry_v1()
    return CounterRecordV1.observe(
        registry,
        semantic_verifier_spec_v1(role).verification_counter_path,
        1,
        recorder_id=f"fallback-cap-min-{role.value.lower()}-v1",
    )


def _small_cap() -> GroundFallbackCapProfileV1:
    # Both coupled candidate/backup caps are one, making their per-leaf upper
    # exact at the first denied composition while leaving the other caps large.
    return GroundFallbackCapProfileV1(
        max_states_expanded=20,
        max_actions_evaluated=48,
        max_ground_steps=48,
        max_outcome_rows=192,
        max_bellman_backups=1,
        max_composed_candidates=1,
        max_cap_checks=5_812,
        max_positive_outcomes_per_step=4,
    )


def _authority_chain():
    world = load_frozen_phase3c_world(ROOT / "artifacts" / "phase3c")
    registry = official_counter_registry_v1()
    profile = official_comparison_profile_v1(registry)
    identities = safe_chain_fallback_context_identity_v1(world)
    context = RouteDecisionContextV1(
        _id("preregistration"),
        _id("protocol"),
        profile.comparison_profile_id,
        registry.registry_id,
        identities["structural_id"],
        identities["query_id"],
        _id("selected-plan"),
        _id("threshold"),
        identities["build_epoch_id"],
        _id("occurrence"),
        _id("attempt"),
    )
    not_applicable = TypedNotApplicable(
        "direct fallback has no local transaction"
    )
    point = DecisionPointV1(
        context.route_decision_context_id,
        not_applicable,
        TypedNotApplicable("direct fallback has no local frontier"),
        TypedNotApplicable("direct fallback has no causal evidence"),
        _id("common-prefix-work"),
    )
    binding = AttestationContextV1(
        context,
        point.decision_point_id,
        not_applicable,
        20,
    )
    cap = _small_cap()
    source = derive_safe_chain_fallback_cardinality_source_v1(
        world=world,
        context=context,
        decision_point=point,
        cap_profile=cap,
        frozen_at_protocol_step=1,
    )
    bound = derive_safe_chain_fallback_cardinality_bound_v1(
        source=source,
        cap_profile=cap,
    )
    cardinality = build_ground_fallback_cardinality_evidence_v1(
        context=context,
        decision_point=point,
        cap_profile=cap,
        bound=bound,
    )
    cardinality_result = verify_safe_chain_fallback_cardinality_semantics_v1(
        cardinality,
        source=source,
        bound=bound,
        frozen_world=world,
        context=context,
        decision_point=point,
        cap_profile=cap,
        binding=binding,
        verification_work_record=_record(SemanticRole.CARDINALITY_EVIDENCE),
        registry=registry,
    )
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
        verification_work_record=_record(SemanticRole.ROUTE_UPPER),
        registry=registry,
    )
    decision = derive_guarded_marginal_route_decision_v1(
        context=context,
        decision_point=point,
        fallback_upper_result=upper_result,
        local_upper_result=None,
        causal_result=None,
        binding=binding,
    )
    decision_result = verify_marginal_route_decision_semantics_v1(
        decision,
        context=context,
        decision_point=point,
        fallback_upper_result=upper_result,
        local_upper_result=None,
        causal_result=None,
        binding=binding,
        verification_work_record=_record(SemanticRole.ROUTE_DECISION),
        registry=registry,
    )
    return {
        "world": world,
        "registry": registry,
        "profile": profile,
        "context": context,
        "point": point,
        "binding": binding,
        "cap": cap,
        "source": source,
        "bound": bound,
        "cardinality": cardinality,
        "cardinality_result": cardinality_result,
        "formula": formula,
        "upper": upper,
        "proof": proof,
        "upper_result": upper_result,
        "decision_result": decision_result,
    }


def test_authorized_small_cap_fallback_closes_cap_exhausted_not_infeasible() -> None:
    chain = _authority_chain()
    exact = dict(chain["bound"].bounds)
    clipped = dict(
        chain["bound"].operational_upper_values(
            chain["cap"], chain["registry"]
        )
    )
    proof_upper = dict(chain["proof"].leaf_upper_bounds)

    # The source theorem stays exact; only the route upper is cap-clipped.
    assert exact["fallback.bellman_backups"] == 5_696
    assert exact["fallback.composed_candidates"] == 5_696
    assert dict(chain["cardinality"].counts)["fallback.bellman_backups"] == 5_696
    assert clipped["fallback.bellman_backups"] == 1
    assert proof_upper == clipped
    assert chain["decision_result"].outcome == RouteSelection.FALLBACK.value

    execution = execute_authorized_ground_fallback_v1(
        chain["world"].kernel,
        chain["world"].queries[1].query,
        context=chain["context"],
        decision_point=chain["point"],
        fallback_upper=chain["upper"],
        cardinality=chain["cardinality"],
        cardinality_bound=chain["bound"],
        cap_profile=chain["cap"],
        route_decision_result=chain["decision_result"],
        fallback_upper_result=chain["upper_result"],
        cardinality_result=chain["cardinality_result"],
        registry=chain["registry"],
    )
    assert execution.result.outcome is GroundFallbackOutcome.CAP_EXHAUSTED
    assert execution.result.search_complete is False
    assert execution.result.cap_exhausted_name == "max_composed_candidates"
    assert execution.result.frontier == ()
    assert execution.selected_policy is None
    assert execution.result.selected_failure_probability is None
    assert execution.result.outcome is not GroundFallbackOutcome.INFEASIBLE_CERTIFIED
    assert all(
        execution.work_vector.value(path) <= proof_upper[path]
        for path in proof_upper
    )

    verified = verify_ground_fallback_semantics_v1(
        execution,
        cap_profile=chain["cap"],
        binding=chain["binding"],
        verification_work_record=_record(SemanticRole.GROUND_FALLBACK),
        registry=chain["registry"],
    )
    assert verified.outcome == GroundFallbackOutcome.CAP_EXHAUSTED.value


def test_small_cap_cannot_relabel_exact_cardinality_as_clipped_source() -> None:
    chain = _authority_chain()
    values = dict(chain["bound"].bounds)
    values["fallback.bellman_backups"] = 1
    values["fallback.composed_candidates"] = 1
    attacked_bound = GroundFallbackCardinalityBoundV1(
        chain["context"].route_decision_context_id,
        chain["point"].decision_point_id,
        chain["cap"].ground_fallback_cap_profile_id,
        tuple((name, values[name]) for name, _ in chain["bound"].bounds),
        chain["bound"].source_artifact_ids,
    )
    attacked_cardinality = build_ground_fallback_cardinality_evidence_v1(
        context=chain["context"],
        decision_point=chain["point"],
        cap_profile=chain["cap"],
        bound=attacked_bound,
    )
    with pytest.raises(SemanticVerificationV1Error, match="registered formula"):
        verify_safe_chain_fallback_cardinality_semantics_v1(
            attacked_cardinality,
            source=chain["source"],
            bound=attacked_bound,
            frozen_world=chain["world"],
            context=chain["context"],
            decision_point=chain["point"],
            cap_profile=chain["cap"],
            binding=chain["binding"],
            verification_work_record=_record(
                SemanticRole.CARDINALITY_EVIDENCE
            ),
            registry=chain["registry"],
        )


def test_fallback_formula_cannot_remove_or_retarget_hard_cap_min() -> None:
    chain = _authority_chain()
    formula = chain["formula"]
    backup_term = next(
        term
        for term in formula.terms
        if term.target_leaf == "fallback.bellman_backups"
    )
    assert backup_term.cap_mode is CapMode.MIN_HARD_CAP
    assert backup_term.cap_name == "max_bellman_backups"

    for attacked_term in (
        replace(backup_term, cap_mode=CapMode.NONE, cap_name=None),
        replace(backup_term, cap_name="max_states_expanded"),
    ):
        attacked_formula = replace(
            formula,
            terms=tuple(
                attacked_term if term is backup_term else term
                for term in formula.terms
            ),
        )
        with pytest.raises(RouteUpperFormulaV1Error, match="official"):
            derive_route_upper_v1(
                context=chain["context"],
                decision_point=chain["point"],
                cardinality=chain["cardinality"],
                cap_profile=chain["cap"],
                registry=chain["registry"],
                profile=chain["profile"],
                formula=attacked_formula,
            )
