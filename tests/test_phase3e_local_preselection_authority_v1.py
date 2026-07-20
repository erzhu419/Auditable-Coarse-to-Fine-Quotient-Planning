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
import acfqp.phase3d as phase3d_module
from acfqp.phase3d import prepare_safe_chain_estimate_context
from acfqp.phase3e_fallback_v1 import (
    GroundFallbackCapProfileV1,
    build_ground_fallback_cardinality_evidence_v1,
    derive_safe_chain_fallback_cardinality_bound_v1,
    derive_safe_chain_fallback_cardinality_source_v1,
)
from acfqp.phase3e_ids import (
    LOCAL_CARDINALITY_BOUND_DOMAIN,
    LOCAL_PRESELECTION_EXTRACTION_PROFILE_DOMAIN,
    LOCAL_PRESELECTION_PARENT_BINDING_DOMAIN,
    LOCAL_PRESELECTION_SOURCE_DOMAIN,
    LOCAL_PROOF_OBLIGATION_DOMAIN,
    content_id,
)
from acfqp.phase3e_local_preselection_v1 import (
    LOCAL_PRESELECTION_EXTRACTION_PROFILE_ID,
    SafeChainLocalCardinalityBoundV1,
    SafeChainLocalPreselectionSourceV1,
    build_safe_chain_local_cardinality_evidence_v1,
    derive_safe_chain_local_cardinality_bound_v1,
    derive_safe_chain_local_frontier_and_causal_v1,
    derive_safe_chain_local_preselection_source_v1,
    safe_chain_local_context_identity_v1,
    safe_chain_local_selected_plan_id_v1,
    safe_chain_local_threshold_profile_id_v1,
)
from acfqp.phase3e_local_semantics_v1 import FrozenThresholdProfileV1
from acfqp.route_upper_formula_v1 import (
    derive_route_upper_v1,
    official_route_upper_formula_v1,
)
from acfqp.routing_v1 import (
    CausalEvidenceV1,
    CausalOutcome,
    DecisionPointV1,
    MarginalRouteDecisionV1,
    RouteCapProfileV1,
    RouteComparison,
    RouteDecisionContextV1,
    RouteKind,
    RouteSelection,
    TransactionV1,
    TypedNotApplicable,
)
from acfqp.semantic_verification_v1 import (
    AttestationContextV1,
    SemanticRole,
    SemanticVerificationV1Error,
    derive_guarded_marginal_route_decision_v1,
    semantic_verifier_spec_v1,
    verify_marginal_route_decision_semantics_v1,
    verify_route_upper_semantics_v1,
    verify_safe_chain_fallback_cardinality_semantics_v1,
    verify_safe_chain_local_cardinality_semantics_v1,
    verify_safe_chain_local_causal_semantics_v1,
)


def _id(label: str) -> str:
    return hashlib.sha256(
        b"acfqp:phase3e-local-preselection-test:v1\x00" + label.encode("utf-8")
    ).hexdigest()


def _verification_record(role: SemanticRole) -> CounterRecordV1:
    registry = official_counter_registry_v1()
    spec = semantic_verifier_spec_v1(role)
    return CounterRecordV1.observe(
        registry,
        spec.verification_counter_path,
        1,
        recorder_id=f"phase3e-local-preselection-{role.value.lower()}-v1",
    )


def _fallback_cap() -> GroundFallbackCapProfileV1:
    return GroundFallbackCapProfileV1(
        max_states_expanded=20,
        max_actions_evaluated=48,
        max_ground_steps=48,
        max_outcome_rows=192,
        max_bellman_backups=5_696,
        max_composed_candidates=5_696,
        max_cap_checks=5_812,
        max_positive_outcomes_per_step=4,
    )


def _chain():
    world = load_frozen_phase3c_world("artifacts/phase3c")
    prepared = prepare_safe_chain_estimate_context(world)
    identities = safe_chain_local_context_identity_v1(world)
    registry = official_counter_registry_v1()
    profile = official_comparison_profile_v1(registry)
    context = RouteDecisionContextV1(
        _id("preregistration"),
        _id("protocol"),
        profile.comparison_profile_id,
        registry.registry_id,
        identities["structural_id"],
        identities["query_id"],
        safe_chain_local_selected_plan_id_v1(prepared),
        safe_chain_local_threshold_profile_id_v1(prepared),
        identities["build_epoch_id"],
        _id("logical-occurrence"),
        _id("route-attempt"),
    )
    cap = RouteCapProfileV1()
    frontier, causal = derive_safe_chain_local_frontier_and_causal_v1(
        prepared=prepared,
        context=context,
        cap_profile=cap,
        frontier_stage=1,
    )
    point = DecisionPointV1(
        context.route_decision_context_id,
        1,
        frontier.frontier_snapshot_id,
        causal.causal_evidence_id,
        _id("common-prefix-work"),
    )
    transaction = TransactionV1(
        context.logical_occurrence_id,
        context.route_attempt_id,
        point.decision_point_id,
        1,
        frontier.frontier_snapshot_id,
        cap.route_cap_profile_id,
    )
    source = derive_safe_chain_local_preselection_source_v1(
        prepared=prepared,
        context=context,
        frontier=frontier,
        causal=causal,
        decision_point=point,
        transaction=transaction,
        cap_profile=cap,
        frozen_at_protocol_step=1,
    )
    bound = derive_safe_chain_local_cardinality_bound_v1(
        source=source,
        cap_profile=cap,
        registry=registry,
    )
    cardinality = build_safe_chain_local_cardinality_evidence_v1(
        context=context,
        decision_point=point,
        transaction=transaction,
        cap_profile=cap,
        bound=bound,
    )
    binding = AttestationContextV1(
        context, point.decision_point_id, transaction.transaction_id, 10
    )
    return {
        "world": world,
        "prepared": prepared,
        "registry": registry,
        "profile": profile,
        "context": context,
        "cap": cap,
        "frontier": frontier,
        "causal": causal,
        "point": point,
        "transaction": transaction,
        "source": source,
        "bound": bound,
        "cardinality": cardinality,
        "binding": binding,
    }


def _verify_causal(chain):
    return verify_safe_chain_local_causal_semantics_v1(
        chain["causal"],
        source=chain["source"],
        frozen_world=chain["world"],
        context=chain["context"],
        frontier=chain["frontier"],
        decision_point=chain["point"],
        transaction=chain["transaction"],
        cap_profile=chain["cap"],
        binding=chain["binding"],
        verification_work_record=_verification_record(SemanticRole.CAUSAL_SEARCH),
        registry=chain["registry"],
    )


def _verify_cardinality(chain, causal_result):
    return verify_safe_chain_local_cardinality_semantics_v1(
        chain["cardinality"],
        source=chain["source"],
        bound=chain["bound"],
        causal_result=causal_result,
        frozen_world=chain["world"],
        context=chain["context"],
        frontier=chain["frontier"],
        decision_point=chain["point"],
        transaction=chain["transaction"],
        cap_profile=chain["cap"],
        binding=chain["binding"],
        verification_work_record=_verification_record(
            SemanticRole.CARDINALITY_EVIDENCE
        ),
        registry=chain["registry"],
    )


def _verify_local_upper(chain, cardinality_result):
    formula = official_route_upper_formula_v1(
        RouteKind.LOCAL_ATTEMPT,
        registry=chain["registry"],
        profile=chain["profile"],
        cap_profile=chain["cap"],
    )
    upper, proof = derive_route_upper_v1(
        context=chain["context"],
        decision_point=chain["point"],
        cardinality=chain["cardinality"],
        cap_profile=chain["cap"],
        registry=chain["registry"],
        profile=chain["profile"],
        formula=formula,
        transaction=chain["transaction"],
        causal=chain["causal"],
    )
    result = verify_route_upper_semantics_v1(
        upper,
        derivation_proof=proof,
        cardinality_result=cardinality_result,
        context=chain["context"],
        decision_point=chain["point"],
        cap_profile=chain["cap"],
        formula=formula,
        transaction=chain["transaction"],
        causal=chain["causal"],
        binding=chain["binding"],
        verification_work_record=_verification_record(SemanticRole.ROUTE_UPPER),
        registry=chain["registry"],
    )
    return upper, result


def _verify_fallback_upper(chain):
    cap = _fallback_cap()
    source = derive_safe_chain_fallback_cardinality_source_v1(
        world=chain["world"],
        context=chain["context"],
        decision_point=chain["point"],
        cap_profile=cap,
        frozen_at_protocol_step=1,
    )
    bound = derive_safe_chain_fallback_cardinality_bound_v1(
        source=source, cap_profile=cap
    )
    cardinality = build_ground_fallback_cardinality_evidence_v1(
        context=chain["context"],
        decision_point=chain["point"],
        cap_profile=cap,
        bound=bound,
    )
    fallback_binding = AttestationContextV1(
        chain["context"],
        chain["point"].decision_point_id,
        TypedNotApplicable("direct fallback has no local transaction"),
        10,
    )
    cardinality_result = verify_safe_chain_fallback_cardinality_semantics_v1(
        cardinality,
        source=source,
        bound=bound,
        frozen_world=chain["world"],
        context=chain["context"],
        decision_point=chain["point"],
        cap_profile=cap,
        binding=fallback_binding,
        verification_work_record=_verification_record(
            SemanticRole.CARDINALITY_EVIDENCE
        ),
        registry=chain["registry"],
    )
    formula = official_route_upper_formula_v1(
        RouteKind.DIRECT_FALLBACK,
        registry=chain["registry"],
        profile=chain["profile"],
        cap_profile=cap,
    )
    upper, proof = derive_route_upper_v1(
        context=chain["context"],
        decision_point=chain["point"],
        cardinality=cardinality,
        cap_profile=cap,
        registry=chain["registry"],
        profile=chain["profile"],
        formula=formula,
    )
    upper_result = verify_route_upper_semantics_v1(
        upper,
        derivation_proof=proof,
        cardinality_result=cardinality_result,
        context=chain["context"],
        decision_point=chain["point"],
        cap_profile=cap,
        formula=formula,
        transaction=None,
        causal=None,
        binding=fallback_binding,
        verification_work_record=_verification_record(SemanticRole.ROUTE_UPPER),
        registry=chain["registry"],
    )
    return upper, upper_result


def test_local_source_domains_and_strict_roundtrip_are_distinct() -> None:
    payload = {"schema": "same-payload", "value": 1}
    assert len(
        {
            content_id(domain, payload)
            for domain in (
                LOCAL_PRESELECTION_SOURCE_DOMAIN,
                LOCAL_CARDINALITY_BOUND_DOMAIN,
                LOCAL_PRESELECTION_PARENT_BINDING_DOMAIN,
                LOCAL_PRESELECTION_EXTRACTION_PROFILE_DOMAIN,
                LOCAL_PROOF_OBLIGATION_DOMAIN,
            )
        }
    ) == 5
    chain = _chain()
    assert SafeChainLocalPreselectionSourceV1.from_dict(
        chain["source"].to_dict()
    ) == chain["source"]
    assert SafeChainLocalCardinalityBoundV1.from_dict(
        chain["bound"].to_dict()
    ) == chain["bound"]
    assert chain["source"].extraction_profile_id == (
        LOCAL_PRESELECTION_EXTRACTION_PROFILE_ID
    )
    expected_threshold = FrozenThresholdProfileV1(
        chain["context"].query_id,
        chain["prepared"].pre_audit.regret_tolerance,
        chain["prepared"].pre_audit.risk_tolerance,
    )
    assert chain["context"].threshold_profile_id == (
        expected_threshold.threshold_profile_id
    )


def test_authorities_replay_frozen_parent_without_execution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    chain = _chain()

    def forbidden(*_args, **_kwargs):
        raise AssertionError("route execution occurred before decision freeze")

    monkeypatch.setattr(G2048SafeChainKernel, "step", forbidden)
    monkeypatch.setattr(phase3d_module, "materialize_authorized_slice", forbidden)
    monkeypatch.setattr(phase3d_module, "compile_sparse_recovery_inputs", forbidden)
    monkeypatch.setattr(phase3d_module, "solve_general_local_recovery", forbidden)
    causal_result = _verify_causal(chain)
    cardinality_result = _verify_cardinality(chain, causal_result)
    assert causal_result.outcome == "FOUND"
    assert cardinality_result.outcome == "VALID"
    assert cardinality_result.artifact == chain["cardinality"]
    assert chain["world"].binding_counters["kernel_step_calls"] == 0


def test_local_cardinality_covers_every_operational_leaf_and_guard() -> None:
    chain = _chain()
    registry = chain["registry"]
    values = dict(chain["bound"].bounds)
    expected = {leaf.path for leaf in registry.operational_leaves} | {
        "structural.cell_policy_assignments",
        "structural.form_subset_evaluations",
        "structural.rational_bits",
        "structural.slice_actions",
        "structural.slice_cells",
        "structural.slice_members",
    }
    assert set(values) == expected
    assert len(chain["bound"].operational_count_values(registry)) == 34
    assert dict(chain["bound"].operational_upper_values(chain["cap"]))[
        "local.materialization_ground_steps"
    ] == 16
    assert values["local.materialization_outcome_rows"] == 64
    assert values["local.postaudit_ground_steps"] == 8
    assert values["local.postaudit_outcome_rows"] == 32
    assert values["local.solver_policy_assignments"] == 257
    assert values["control.cap_rejections"] == 0
    assert values["process.launches"] == 1
    assert values["io.read_bytes"] > 0
    assert values["memory.working_bytes_peak"] > 0
    assert all(values[path] == 0 for path in values if path.startswith("fallback."))
    assert all(values[path] == 0 for path in values if path.startswith("rebuild."))


def test_deleted_or_reordered_source_members_cannot_self_authorize() -> None:
    chain = _chain()
    deleted = replace(
        chain["source"],
        frontier_action_member_ids=chain["source"].frontier_action_member_ids[:-1],
    )
    assert deleted.source_artifact_id != chain["source"].source_artifact_id
    attacked = {**chain, "source": deleted}
    with pytest.raises(SemanticVerificationV1Error, match="source differs"):
        _verify_causal(attacked)

    document = chain["source"].to_dict()
    document["frontier_action_member_ids"] = list(
        reversed(document["frontier_action_member_ids"])
    )
    document["source_artifact_id"] = content_id(
        LOCAL_PRESELECTION_SOURCE_DOMAIN,
        {
            key: value
            for key, value in document.items()
            if key != "source_artifact_id"
        },
    )
    with pytest.raises(ValueError, match="unique and sorted"):
        SafeChainLocalPreselectionSourceV1.from_dict(document)


def test_changed_bound_or_cardinality_count_is_rejected_after_rehash() -> None:
    chain = _chain()
    causal_result = _verify_causal(chain)
    changed_bounds = dict(chain["bound"].bounds)
    changed_bounds["local.solver_policy_assignments"] -= 1
    changed_bound = replace(chain["bound"], bounds=tuple(sorted(changed_bounds.items())))
    attacked = {**chain, "bound": changed_bound}
    with pytest.raises(SemanticVerificationV1Error, match="bound differs"):
        _verify_cardinality(attacked, causal_result)

    changed_counts = dict(chain["cardinality"].counts)
    changed_counts["local.solver_policy_assignments"] -= 1
    changed_cardinality = replace(
        chain["cardinality"], counts=tuple(sorted(changed_counts.items()))
    )
    attacked = {**chain, "cardinality": changed_cardinality}
    with pytest.raises(SemanticVerificationV1Error, match="authoritative local"):
        _verify_cardinality(attacked, causal_result)


def test_stale_transaction_and_negative_causal_claim_fail_closed() -> None:
    chain = _chain()
    foreign_transaction = replace(
        chain["transaction"], route_attempt_id=_id("foreign-attempt")
    )
    attacked = {**chain, "transaction": foreign_transaction}
    with pytest.raises(SemanticVerificationV1Error, match="another decision point or transaction"):
        _verify_causal(attacked)

    negative = CausalEvidenceV1(
        chain["frontier"].frontier_snapshot_id,
        CausalOutcome.NO_SOUND_COVER,
        False,
        "NO_SOUND_COVER",
        4,
        chain["cap"].route_cap_profile_id,
        chain["frontier"].failed_obligation_ids,
    )
    attacked = {**chain, "causal": negative}
    with pytest.raises(SemanticVerificationV1Error, match="stale"):
        _verify_causal(attacked)


def test_authoritative_local_cardinality_feeds_local_upper() -> None:
    chain = _chain()
    causal_result = _verify_causal(chain)
    cardinality_result = _verify_cardinality(chain, causal_result)
    upper, upper_result = _verify_local_upper(chain, cardinality_result)
    assert upper_result.outcome == "VALID"
    assert dict(upper.upper_bounds) == {
        "kernel_transition_calls": 24,
        "nonkernel_compute_events": 1_890,
        "output_bytes": 1_048_576,
        "peak_mounted_bytes": 2_097_152,
        "peak_working_bytes": 268_435_456,
        "process_launches": 1,
        "read_bytes": 1_048_576,
        "staged_bytes": 1_048_576,
    }


def test_real_authority_chain_selects_local_against_isolated_fallback() -> None:
    chain = _chain()
    causal_result = _verify_causal(chain)
    cardinality_result = _verify_cardinality(chain, causal_result)
    local_upper, local_upper_result = _verify_local_upper(
        chain, cardinality_result
    )
    fallback_upper, fallback_upper_result = _verify_fallback_upper(chain)
    assert dict(local_upper.upper_bounds)["kernel_transition_calls"] < dict(
        fallback_upper.upper_bounds
    )["kernel_transition_calls"]
    assert dict(local_upper.upper_bounds)["process_launches"] == dict(
        fallback_upper.upper_bounds
    )["process_launches"]
    assert all(
        dict(local_upper.upper_bounds)[axis]
        <= dict(fallback_upper.upper_bounds)[axis]
        for axis in dict(local_upper.upper_bounds)
    )

    decision = derive_guarded_marginal_route_decision_v1(
        context=chain["context"],
        decision_point=chain["point"],
        fallback_upper_result=fallback_upper_result,
        local_upper_result=local_upper_result,
        causal_result=causal_result,
        binding=chain["binding"],
    )
    assert decision.selected_route is RouteSelection.LOCAL
    assert decision.comparison is RouteComparison.LOCAL_STRICTLY_DOMINATES
    decision_result = verify_marginal_route_decision_semantics_v1(
        decision,
        context=chain["context"],
        decision_point=chain["point"],
        fallback_upper_result=fallback_upper_result,
        causal_result=causal_result,
        local_upper_result=local_upper_result,
        binding=chain["binding"],
        verification_work_record=_verification_record(SemanticRole.ROUTE_DECISION),
        registry=chain["registry"],
    )
    assert decision_result.outcome == "LOCAL"


def test_missing_causal_authority_never_reopens_local() -> None:
    chain = _chain()
    causal_result = _verify_causal(chain)
    cardinality_result = _verify_cardinality(chain, causal_result)
    _local_upper, local_upper_result = _verify_local_upper(chain, cardinality_result)
    _fallback_upper, fallback_upper_result = _verify_fallback_upper(chain)
    decision = derive_guarded_marginal_route_decision_v1(
        context=chain["context"],
        decision_point=chain["point"],
        fallback_upper_result=fallback_upper_result,
        local_upper_result=local_upper_result,
        causal_result=None,
        binding=chain["binding"],
    )
    assert decision.selected_route is RouteSelection.FALLBACK
    assert decision.comparison is RouteComparison.LOCAL_FORBIDDEN


def test_transport_selector_chooses_local_only_under_strict_dominance() -> None:
    """Exercise the pure selector rule without pretending transport is authority."""

    chain = _chain()
    causal_result = _verify_causal(chain)
    cardinality_result = _verify_cardinality(chain, causal_result)
    local_upper, _result = _verify_local_upper(chain, cardinality_result)
    fallback_upper, _fallback_result = _verify_fallback_upper(chain)
    local_values = dict(local_upper.upper_bounds)
    dominating_target = replace(
        fallback_upper,
        upper_bounds=tuple(
            (axis, local_values[axis] + 1) for axis, _ in fallback_upper.upper_bounds
        ),
    )
    decision = MarginalRouteDecisionV1.select(
        chain["point"],
        dominating_target,
        causal=chain["causal"],
        local_upper=local_upper,
    )
    assert decision.selected_route is RouteSelection.LOCAL
    assert decision.comparison is RouteComparison.LOCAL_STRICTLY_DOMINATES
