from __future__ import annotations

import copy
from dataclasses import replace
from fractions import Fraction
from pathlib import Path

import pytest

import acfqp.phase3d as phase3d
import acfqp.phase3e_ground_handoff_v1 as ground_handoff
from acfqp.accounting_v1 import (
    CounterRecordV1,
    LaneEnum,
    official_counter_registry_v1,
)
from acfqp.domains.g2048 import G2048SafeChainKernel
from acfqp.phase3e_ground_handoff_v1 import (
    open_ground_binding_after_failed_audit_v1,
)
from acfqp.phase3e_local_preselection_v1 import (
    Phase3ELocalPreselectionV1Error,
    derive_safe_chain_local_frontier_and_causal_v1,
    safe_chain_local_selected_plan_id_v1,
    safe_chain_local_threshold_profile_id_v1,
)
from acfqp.phase3e_model_only_v1 import (
    Phase3EModelOnlyResultV1,
    run_phase3e_model_only_from_source_v1,
)
from acfqp.phase3e_rapm_consumer_v1 import (
    ABSTRACT_QUERY_KEY,
    LOCAL_QUERY_KEY,
    ModelOnlyRAPMSourceV1,
    load_phase3c_model_source_v1,
)
from acfqp.routing_v1 import RouteCapProfileV1, TypedNotApplicable
from acfqp.semantic_verification_v1 import (
    AttestationContextV1,
    SemanticRole,
    SemanticVerificationResultV1,
    semantic_verifier_spec_v1,
    verify_abstract_plan_audit_semantics_v1,
)


ROOT = Path(__file__).resolve().parents[1]
PHASE3C = ROOT / "artifacts" / "phase3c"


def _model_only_case(
    *,
    query_key: str,
    regret_tolerance: Fraction = Fraction(1, 20),
) -> tuple[
    ModelOnlyRAPMSourceV1,
    Phase3EModelOnlyResultV1,
    SemanticVerificationResultV1,
]:
    source = load_phase3c_model_source_v1(PHASE3C, query_key=query_key)
    result = run_phase3e_model_only_from_source_v1(
        source, regret_tolerance=regret_tolerance
    )
    binding = AttestationContextV1(
        result.route_context,
        TypedNotApplicable("abstract audit precedes route decision"),
        TypedNotApplicable("abstract audit precedes local transaction"),
        3,
        LaneEnum.OPERATIONAL,
    )
    registry = official_counter_registry_v1()
    spec = semantic_verifier_spec_v1(SemanticRole.ABSTRACT_AUDIT)
    work = CounterRecordV1.observe(
        registry,
        spec.counter_path_for_lane(LaneEnum.OPERATIONAL),
        1,
        recorder_id="verified-audit-to-estimate-test-v1",
    )
    authority = verify_abstract_plan_audit_semantics_v1(
        result.audit,
        source=source,
        model_only_result=result,
        binding=binding,
        verification_work_record=work,
    )
    return source, result, authority


def _failed_case() -> tuple[
    Phase3EModelOnlyResultV1,
    SemanticVerificationResultV1,
    object,
]:
    _source, result, authority = _model_only_case(query_key=LOCAL_QUERY_KEY)
    binding = open_ground_binding_after_failed_audit_v1(
        PHASE3C,
        model_only_result=result,
        abstract_audit_authority=authority,
    )
    return result, authority, binding


def test_verified_failed_audit_reaches_estimate_without_replanning_or_ground_access(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result, authority, binding = _failed_case()

    def forbidden(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("forbidden work occurred in the estimate bridge")

    monkeypatch.setattr(phase3d, "solve_portable_pareto", forbidden)
    monkeypatch.setattr(phase3d, "audit_abstract_policy", forbidden)
    monkeypatch.setattr(G2048SafeChainKernel, "actions", forbidden)
    monkeypatch.setattr(G2048SafeChainKernel, "step", forbidden)
    monkeypatch.setattr(phase3d, "materialize_authorized_slice", forbidden)
    monkeypatch.setattr(phase3d, "compile_sparse_recovery_inputs", forbidden)

    prepared = phase3d.prepare_safe_chain_estimate_from_verified_model_failure_v1(
        binding,
        model_only_result=result,
        abstract_audit_authority=authority,
    )

    assert prepared.portable_result.to_dict() == result.selected_plan.planner_result
    assert prepared.proposal == result.selected_plan.proposal
    assert prepared.proposal_source == result.selected_plan.proposal_source
    assert prepared.pre_audit.unrestricted_reward_upper == Fraction(3, 64)
    assert prepared.pre_audit.lifted_reward_lower == Fraction(3, 64)
    assert prepared.pre_audit.lifted_failure_upper == Fraction(5099, 10000)
    assert prepared.pre_audit.regret_upper == 0
    assert prepared.pre_audit.certified is False
    assert len(prepared.pre_audit.reachable_bounds) == 4
    registry = prepared.world.portable.registry
    assert {
        (
            bound.remaining,
            registry.cell_id(bound.cell),
            bound.reward_lower,
            bound.failure_upper,
        )
        for bound in prepared.pre_audit.reachable_bounds
    } == {
        (
            row.remaining,
            row.cell_id,
            row.reward_lower,
            row.failure_upper,
        )
        for row in result.sound_proof.policy_rows
    }
    assert len(prepared.authorization.frontier_state_actions) == 16
    assert len(prepared.authorization.reverse_dependency_state_actions) == 8
    assert len(prepared.authorization.allowed_state_actions) == 24
    assert not hasattr(prepared, "v1_slice")
    assert not hasattr(prepared, "capability")
    assert prepared.verified_model_binding is not None
    assert safe_chain_local_selected_plan_id_v1(prepared) == (
        result.route_context.selected_plan_id
    )
    assert safe_chain_local_threshold_profile_id_v1(prepared) == (
        result.route_context.threshold_profile_id
    )
    frontier, causal = derive_safe_chain_local_frontier_and_causal_v1(
        prepared=prepared,
        context=result.route_context,
        cap_profile=RouteCapProfileV1(),
        frontier_stage=1,
    )
    assert frontier.route_decision_context_id == (
        result.route_context.route_decision_context_id
    )
    assert causal.frontier_snapshot_id == frontier.frontier_snapshot_id
    assert causal.local_allowed is True


def test_pass_result_is_rejected_before_ground_capability_access() -> None:
    _source, result, authority = _model_only_case(query_key=ABSTRACT_QUERY_KEY)
    with pytest.raises(
        phase3d.Phase3DInvariantViolation,
        match="forbidden for a PASS result",
    ):
        phase3d.prepare_safe_chain_estimate_from_verified_model_failure_v1(
            object(),
            model_only_result=result,
            abstract_audit_authority=authority,
        )


@pytest.mark.parametrize("raw", ["audit", "hash", "attestation"])
def test_raw_or_hash_only_audit_cannot_authorize_estimation(raw: str) -> None:
    result, authority, binding = _failed_case()
    substitute: object = {
        "audit": result.audit,
        "hash": result.audit.audit_id,
        "attestation": authority.attestation,
    }[raw]
    with pytest.raises(
        phase3d.Phase3DInvariantViolation,
        match="retained ABSTRACT_AUDIT authority",
    ):
        phase3d.prepare_safe_chain_estimate_from_verified_model_failure_v1(
            binding,
            model_only_result=result,
            abstract_audit_authority=substitute,
        )


def test_foreign_authority_and_foreign_result_are_rejected() -> None:
    result, authority, binding = _failed_case()
    _source, foreign_result, foreign_authority = _model_only_case(
        query_key=LOCAL_QUERY_KEY,
        regret_tolerance=Fraction(1, 10),
    )

    with pytest.raises(
        phase3d.Phase3DInvariantViolation,
        match="foreign to the ground handoff",
    ):
        phase3d.prepare_safe_chain_estimate_from_verified_model_failure_v1(
            binding,
            model_only_result=result,
            abstract_audit_authority=foreign_authority,
        )

    with pytest.raises(
        phase3d.Phase3DInvariantViolation,
        match="ground handoff/model-only mismatch",
    ):
        phase3d.prepare_safe_chain_estimate_from_verified_model_failure_v1(
            binding,
            model_only_result=foreign_result,
            abstract_audit_authority=authority,
        )


@pytest.mark.parametrize(
    "field_name",
    (
        "verification_work_record_id",
        "bound_ground_action_catalogue_id",
        "locality_metadata_id",
    ),
)
def test_estimate_bridge_checks_every_previously_omitted_binding_identity(
    field_name: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result, authority, binding = _failed_case()
    object.__setattr__(binding, field_name, binding.model_only_result_id)

    # Simulate a hostile internal caller bypassing the public capability
    # validator.  The Phase-3D bridge must still compare all three identities
    # against their independent semantic/world sources.
    monkeypatch.setattr(
        ground_handoff,
        "require_ground_binding_after_failed_audit_v1",
        lambda candidate: candidate,
    )
    with pytest.raises(
        phase3d.Phase3DInvariantViolation,
        match=rf"ground handoff/model-only mismatch for {field_name}",
    ):
        phase3d.prepare_safe_chain_estimate_from_verified_model_failure_v1(
            binding,
            model_only_result=result,
            abstract_audit_authority=authority,
        )


def test_verified_model_estimate_binding_rejects_public_id_replace() -> None:
    result, authority, ground_binding = _failed_case()
    prepared = phase3d.prepare_safe_chain_estimate_from_verified_model_failure_v1(
        ground_binding,
        model_only_result=result,
        abstract_audit_authority=authority,
    )
    assert prepared.verified_model_binding is not None

    with pytest.raises(
        phase3d.Phase3DInvariantViolation,
        match="binding mismatch for selected_plan_id",
    ):
        replace(
            prepared.verified_model_binding,
            selected_plan_id=result.result_id,
        )


def test_prepared_estimate_is_one_owner_and_binds_every_consumed_field() -> None:
    result, authority, ground_binding = _failed_case()
    prepared = phase3d.prepare_safe_chain_estimate_from_verified_model_failure_v1(
        ground_binding,
        model_only_result=result,
        abstract_audit_authority=authority,
    )
    authorization = prepared.authorization
    frontier_pairs = authorization.frontier_state_actions
    ancestor_pairs = authorization.reverse_dependency_state_actions
    alternate_authorization = replace(
        authorization,
        frontier_state_actions=(ancestor_pairs[0],) + frontier_pairs[1:],
        reverse_dependency_state_actions=(frontier_pairs[0],) + ancestor_pairs[1:],
    )
    assert len(alternate_authorization.frontier_state_actions) == 16
    assert len(alternate_authorization.reverse_dependency_state_actions) == 8
    assert len(alternate_authorization.allowed_state_actions) == 24

    first_bound = prepared.pre_audit.reachable_bounds[0]
    alternate_audit = replace(
        prepared.pre_audit,
        reachable_bounds=(
            replace(first_bound, reward_lower=first_bound.reward_lower + 1),
        )
        + prepared.pre_audit.reachable_bounds[1:],
    )
    alternate_circuit = type(prepared.causal_circuit)(
        prepared.causal_circuit.nodes,
        prepared.causal_circuit.roots,
    )
    attacks = {
        "world": replace(
            prepared.world,
            binding_counters={
                **prepared.world.binding_counters,
                "kernel_step_calls": 999,
            },
        ),
        "query": replace(prepared.query, horizon=1),
        "ground_query_id": prepared.ground_query_id + "-splice",
        "portable_query": replace(
            prepared.portable_query,
            _canonical_document=(
                prepared.portable_query._canonical_document + " "
            ),
        ),
        "portable_result": replace(
            prepared.portable_result,
            composed_candidate_count=(
                prepared.portable_result.composed_candidate_count + 1
            ),
        ),
        "proposal": replace(
            prepared.proposal,
            expected_reward=prepared.proposal.expected_reward + 1,
        ),
        "proposal_source": prepared.proposal_source + "-splice",
        "policy": replace(
            prepared.policy, decisions=prepared.policy.decisions[:-1]
        ),
        "pre_audit": alternate_audit,
        "proof_graph": replace(
            prepared.proof_graph,
            graph_id=prepared.proof_graph.graph_id + "-splice",
        ),
        "causal_circuit": alternate_circuit,
        "causal_search": replace(
            prepared.causal_search,
            evaluation_count=prepared.causal_search.evaluation_count + 1,
        ),
        "frontier": replace(
            prepared.frontier,
            frontier_id=prepared.frontier.frontier_id + "-splice",
        ),
        "authorization": alternate_authorization,
        "source_boundary": {**prepared.source_boundary, "splice": True},
        "source_phase3c_locality": {
            **prepared.source_phase3c_locality,
            "splice": True,
        },
        "source_phase3c_authorization": {
            **prepared.source_phase3c_authorization,
            "splice": True,
        },
        "unrestricted_reward_upper": (
            prepared.unrestricted_reward_upper + 1
        ),
    }
    assert set(attacks) == set(phase3d._PREPARED_ESTIMATE_BOUND_FIELDS) - {
        "verified_model_binding"
    }

    # A dataclass copy cannot become a second live capability, even when every
    # field still points at the exact same objects.
    with pytest.raises(
        phase3d.Phase3DInvariantViolation,
        match="continuation binding differs from its mint",
    ):
        replace(prepared)
    with pytest.raises(
        phase3d.Phase3DInvariantViolation,
        match="one-owner capability and cannot be copied",
    ):
        copy.copy(prepared)
    with pytest.raises(
        phase3d.Phase3DInvariantViolation,
        match="one-owner capability and cannot be deep-copied",
    ):
        copy.deepcopy(prepared)

    # Simulate a hostile internal caller bypassing the frozen dataclass.  Each
    # field consumed by preselection/execution remains independently bound to
    # the mint, rather than merely satisfying its old 16/8/24 cardinalities.
    for field_name, alternate in attacks.items():
        original = getattr(prepared, field_name)
        object.__setattr__(prepared, field_name, alternate)
        try:
            with pytest.raises(
                phase3d.Phase3DInvariantViolation,
                match=rf"object binding mismatch for {field_name}",
            ):
                phase3d.require_verified_model_estimate_binding_v1(prepared)
        finally:
            object.__setattr__(prepared, field_name, original)
        phase3d.require_verified_model_estimate_binding_v1(prepared)


def test_verified_binding_rejects_every_changed_retained_authority_member() -> None:
    result, authority, ground_binding = _failed_case()
    prepared = phase3d.prepare_safe_chain_estimate_from_verified_model_failure_v1(
        ground_binding,
        model_only_result=result,
        abstract_audit_authority=authority,
    )
    binding = prepared.verified_model_binding
    assert binding is not None

    _source, foreign_result, foreign_authority = _model_only_case(
        query_key=LOCAL_QUERY_KEY,
        regret_tolerance=Fraction(1, 10),
    )
    foreign_ground = open_ground_binding_after_failed_audit_v1(
        PHASE3C,
        model_only_result=foreign_result,
        abstract_audit_authority=foreign_authority,
    )
    foreign_prepared = (
        phase3d.prepare_safe_chain_estimate_from_verified_model_failure_v1(
            foreign_ground,
            model_only_result=foreign_result,
            abstract_audit_authority=foreign_authority,
        )
    )
    foreign_binding = foreign_prepared.verified_model_binding
    assert foreign_binding is not None

    for field_name, replacement in (
        ("_model_only_result", foreign_binding._model_only_result),
        (
            "_abstract_audit_authority",
            foreign_binding._abstract_audit_authority,
        ),
        ("_ground_binding", foreign_binding._ground_binding),
    ):
        with pytest.raises(
            phase3d.Phase3DInvariantViolation,
            match="retains a foreign or nonfailed chain",
        ):
            replace(binding, **{field_name: replacement})

    with pytest.raises(
        phase3d.Phase3DInvariantViolation,
        match="lacks its retained authority triple",
    ):
        replace(binding, _authority=object())

    # A token-only shallow copy still replays the exact same sealed triple, but
    # it cannot be substituted into the one-owner prepared context.
    copied_binding = copy.copy(binding)
    phase3d._validate_verified_model_estimate_binding_core_v1(copied_binding)
    with pytest.raises(
        phase3d.Phase3DInvariantViolation,
        match="continuation binding differs from its mint",
    ):
        replace(prepared, verified_model_binding=copied_binding)


@pytest.mark.parametrize(
    "field_name",
    (
        "source_boundary",
        "source_phase3c_locality",
        "source_phase3c_authorization",
    ),
)
def test_prepared_estimate_crypto_snapshot_rejects_in_place_document_mutation(
    field_name: str,
) -> None:
    result, authority, ground_binding = _failed_case()
    prepared = phase3d.prepare_safe_chain_estimate_from_verified_model_failure_v1(
        ground_binding,
        model_only_result=result,
        abstract_audit_authority=authority,
    )
    document = getattr(prepared, field_name)
    document["__splice_attack__"] = {"preserve_public_identity": True}
    try:
        with pytest.raises(
            phase3d.Phase3DInvariantViolation,
            match="payload differs from its cryptographic mint",
        ):
            phase3d.require_verified_model_estimate_binding_v1(prepared)
    finally:
        del document["__splice_attack__"]
    phase3d.require_verified_model_estimate_binding_v1(prepared)


def test_prepared_estimate_crypto_snapshot_covers_mutable_graph_and_world_state() -> None:
    result, authority, ground_binding = _failed_case()
    prepared = phase3d.prepare_safe_chain_estimate_from_verified_model_failure_v1(
        ground_binding,
        model_only_result=result,
        abstract_audit_authority=authority,
    )

    circuit = prepared.causal_circuit
    original_nodes = circuit.nodes
    circuit.nodes = tuple(reversed(original_nodes))
    try:
        with pytest.raises(
            phase3d.Phase3DInvariantViolation,
            match="payload differs from its cryptographic mint",
        ):
            phase3d.require_verified_model_estimate_binding_v1(prepared)
    finally:
        circuit.nodes = original_nodes
    phase3d.require_verified_model_estimate_binding_v1(prepared)

    authorization = prepared.authorization
    original_frontier = authorization.frontier_state_actions
    original_ancestors = authorization.reverse_dependency_state_actions
    object.__setattr__(
        authorization,
        "frontier_state_actions",
        (original_ancestors[0],) + original_frontier[1:],
    )
    object.__setattr__(
        authorization,
        "reverse_dependency_state_actions",
        (original_frontier[0],) + original_ancestors[1:],
    )
    assert len(authorization.frontier_state_actions) == 16
    assert len(authorization.reverse_dependency_state_actions) == 8
    assert len(authorization.allowed_state_actions) == 24
    try:
        with pytest.raises(
            phase3d.Phase3DInvariantViolation,
            match="payload differs from its cryptographic mint",
        ):
            phase3d.require_verified_model_estimate_binding_v1(prepared)
    finally:
        object.__setattr__(
            authorization, "frontier_state_actions", original_frontier
        )
        object.__setattr__(
            authorization,
            "reverse_dependency_state_actions",
            original_ancestors,
        )
    phase3d.require_verified_model_estimate_binding_v1(prepared)

    world_document = prepared.world.local_pre_recovery_document
    world_document["__splice_attack__"] = True
    try:
        with pytest.raises(
            phase3d.Phase3DInvariantViolation,
            match="payload differs from its cryptographic mint",
        ):
            phase3d.require_verified_model_estimate_binding_v1(prepared)
    finally:
        del world_document["__splice_attack__"]
    phase3d.require_verified_model_estimate_binding_v1(prepared)


def test_access_logged_executable_world_requires_distinct_derivative_mint() -> None:
    result, authority, ground_binding = _failed_case()
    prepared = phase3d.prepare_safe_chain_estimate_from_verified_model_failure_v1(
        ground_binding,
        model_only_result=result,
        abstract_audit_authority=authority,
    )

    class LoggedKernel:
        def __init__(self, kernel: object) -> None:
            self._kernel = kernel

    logged = LoggedKernel(prepared.world.kernel)
    with pytest.raises(
        phase3d.Phase3DInvariantViolation,
        match="lacks post-freeze authority",
    ):
        phase3d._derive_safe_chain_access_logged_estimate_v1(
            prepared,
            access_logged_kernel=logged,
            authority=object(),
        )

    derived = phase3d._derive_safe_chain_access_logged_estimate_v1(
        prepared,
        access_logged_kernel=logged,
        authority=(
            phase3d._EXECUTABLE_PREPARED_ESTIMATE_DERIVATION_AUTHORITY
        ),
    )
    phase3d._validate_safe_chain_prepared_estimate_context_v1(derived)
    assert derived is not prepared
    assert derived.world.kernel is logged
    assert derived._mint.derivation_kind == "ACCESS_LOGGED_KERNEL_DERIVATIVE"
    assert derived._mint.parent_payload_sha256 == prepared._mint.payload_sha256
    assert all(
        getattr(derived, name) is getattr(prepared, name)
        for name in phase3d._PREPARED_ESTIMATE_BOUND_FIELDS
        if name != "world"
    )


def test_local_preselection_rejects_foreign_binding_and_context_splice() -> None:
    result, authority, ground_binding = _failed_case()
    prepared = phase3d.prepare_safe_chain_estimate_from_verified_model_failure_v1(
        ground_binding,
        model_only_result=result,
        abstract_audit_authority=authority,
    )
    _source, foreign_result, foreign_authority = _model_only_case(
        query_key=LOCAL_QUERY_KEY,
        regret_tolerance=Fraction(1, 10),
    )
    foreign_ground_binding = open_ground_binding_after_failed_audit_v1(
        PHASE3C,
        model_only_result=foreign_result,
        abstract_audit_authority=foreign_authority,
    )
    foreign_prepared = (
        phase3d.prepare_safe_chain_estimate_from_verified_model_failure_v1(
            foreign_ground_binding,
            model_only_result=foreign_result,
            abstract_audit_authority=foreign_authority,
        )
    )
    cap = RouteCapProfileV1()
    spliced_context = replace(
        result.route_context,
        selected_plan_id=result.result_id,
    )
    with pytest.raises(
        Phase3ELocalPreselectionV1Error,
        match="selected_plan_id does not bind the failed portable plan",
    ):
        derive_safe_chain_local_frontier_and_causal_v1(
            prepared=prepared,
            context=spliced_context,
            cap_profile=cap,
            frontier_stage=1,
        )

    with pytest.raises(
        phase3d.Phase3DInvariantViolation,
        match="continuation binding differs from its mint",
    ):
        replace(
            prepared,
            verified_model_binding=foreign_prepared.verified_model_binding,
        )

    # Even an internal caller that bypasses the frozen dataclass guard cannot
    # feed the foreign authority through local preselection.
    object.__setattr__(
        prepared,
        "verified_model_binding",
        foreign_prepared.verified_model_binding,
    )
    with pytest.raises(
        Phase3ELocalPreselectionV1Error,
        match="continuation binding differs from its mint",
    ):
        derive_safe_chain_local_frontier_and_causal_v1(
            prepared=prepared,
            context=result.route_context,
            cap_profile=cap,
            frontier_stage=1,
        )
