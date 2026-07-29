from __future__ import annotations

from dataclasses import dataclass, replace
from itertools import combinations

import pytest

import acfqp.observation_support_graph_model_v1 as graph_model
import acfqp.observation_support_h2_closure_v1 as h2_closure
import acfqp.observation_support_joint_pair_recovery_v1 as joint
import acfqp.observation_support_promoted_h2_consumer_v1 as first_consumer
import acfqp.observation_support_second_transaction_v1 as second
import acfqp.partial_support_expansion_authority_v1 as expansion
import acfqp.partial_support_robust_planner_v1 as robust
import acfqp.transition_tuple_observer_v1 as observer


@dataclass(frozen=True)
class _Built:
    context: observer.PublicGraphContextV1
    base_closure: h2_closure.ObservationSupportH2ClosureV1
    base_bridge: graph_model.ObservationSupportGraphModelBridgeV1
    base_audit: robust.RobustPlanAuditV1
    threshold: robust.RobustThresholdProfileV1
    transaction1: first_consumer.ObservationSupportPromotedH2ConsumerV1
    v0069: second.SecondSupportTransactionRunV1
    run: joint.JointPairSupportRunV1
    probe: joint.K6JointPairSupportProbeV0


@pytest.fixture(scope="module")
def built() -> _Built:
    context = observer.public_context_by_key_v1("opaque_graph_k6_v0")
    base_closure = h2_closure.acquire_observation_support_h2_closure_v1(
        context,
        8_192,
        max_workers=16,
    )
    base_bridge = graph_model.build_observation_support_graph_models_v1(
        context=context,
        root_catalogue=base_closure.root_catalogue,
        catalogues=(
            base_closure.root_catalogue,
            *base_closure.child_catalogues,
        ),
        partial_rows=base_closure.all_rows,
    )
    threshold = robust.RobustThresholdProfileV1(
        context.context_id,
        context.risk_tolerance,
        base_bridge.reward_ceiling,
    )
    base_audit = robust.solve_quotient_robust_h2_v1(
        base_bridge.quotient_model,
        threshold,
    )
    authorization1 = expansion.authorize_partial_support_expansion_v1(
        bridge=base_bridge,
        audit=base_audit,
        threshold=threshold,
        partial_rows=base_closure.all_rows,
        checkpoint_draw_count=2_048,
    )
    replacement1 = expansion.promote_authorized_partial_support_row_v1(
        bridge=base_bridge,
        audit=base_audit,
        threshold=threshold,
        partial_rows=base_closure.all_rows,
        authorization=authorization1,
    )
    transaction1 = (
        first_consumer.consume_partial_support_promoted_row_replacement_v1(
            context=context,
            parent_closure=base_closure,
            parent_bridge=base_bridge,
            parent_audit=base_audit,
            threshold=threshold,
            replacement=replacement1,
            new_child_validation_checkpoint=8_192,
            max_workers=16,
        )
    )
    v0069 = second.run_second_support_transaction_v1(
        context=context,
        base_closure=base_closure,
        base_bridge=base_bridge,
        base_audit=base_audit,
        threshold=threshold,
        transaction1=transaction1,
        max_workers=16,
    )
    run = joint.run_joint_pair_support_recovery_v1(
        context=context,
        base_closure=base_closure,
        base_bridge=base_bridge,
        base_audit=base_audit,
        threshold=threshold,
        transaction1=transaction1,
        v0069_negative_run=v0069,
        max_workers=16,
    )
    probe = joint.freeze_k6_joint_pair_support_probe_v0(
        context=context,
        base_closure=base_closure,
        transaction1=transaction1,
        v0069_negative_run=v0069,
        run=run,
    )
    return _Built(
        context,
        base_closure,
        base_bridge,
        base_audit,
        threshold,
        transaction1,
        v0069,
        run,
        probe,
    )


def test_real_k6_pair_gate_exhausts_the_complete_k2_ladder(
    built: _Built,
) -> None:
    run = built.run

    assert joint.CONTRACT_VERSION == "1.34.0"
    assert (
        run.outcome
        is joint.JointPairOutcome.NO_SOUND_FIXED_PLAN_PAIR_COVER
    )
    assert len(run.registry.candidates) == 49
    assert len(run.singleton_evidence) == 49
    assert len(run.pair_evidence) == 1_176
    assert not any(
        item.fixed_plan_certified for item in run.singleton_evidence
    )
    assert not any(item.fixed_plan_certified for item in run.pair_evidence)
    assert run.cardinality_evidence == ()


def test_pair_topology_is_complete_canonical_and_fresh(
    built: _Built,
) -> None:
    candidate_ids = tuple(
        item.candidate_id for item in built.run.registry.candidates
    )
    expected = {
        tuple(sorted(pair)) for pair in combinations(candidate_ids, 2)
    }

    assert {
        item.candidate_ids for item in built.run.pair_evidence
    } == expected
    assert (
        built.run.registry.quarantined_v0069_evidence_ids
        == tuple(
            sorted(
                item.evidence_id
                for item in built.v0069.candidate_evidence
            )
        )
    )
    assert not (
        set(built.run.registry.quarantined_v0069_evidence_ids)
        & {
            item.evidence_id
            for item in (
                *built.run.singleton_evidence,
                *built.run.pair_evidence,
            )
        }
    )


def test_no_pair_cover_opens_no_sampling_or_exact_lane(
    built: _Built,
) -> None:
    counters = built.run.counters

    assert counters.singleton_overlay_evaluations == 49
    assert counters.pair_overlay_evaluations == 1_176
    assert counters.model_only_observer_draws == 0
    assert counters.model_only_kernel_calls == 0
    assert counters.model_only_exact_calls == 0
    assert counters.incremental_observer_draws == 0
    assert counters.operational_full_joint_replans == 0
    assert counters.global_16384_checkpoint_accesses == 0
    assert built.run.authorization is None
    assert built.run.replacements == ()
    assert built.run.closure is None
    assert built.run.bridge is None
    assert built.run.audit is None
    assert built.probe.exact_lift is None
    assert built.probe.exact_failure_probability is None
    assert built.probe.exact_normalized_regret is None


def test_standalone_verifier_replays_every_subset_independently(
    built: _Built,
) -> None:
    verification = joint.verify_joint_pair_support_recovery_v1(
        context=built.context,
        base_closure=built.base_closure,
        base_bridge=built.base_bridge,
        base_audit=built.base_audit,
        threshold=built.threshold,
        transaction1=built.transaction1,
        v0069_negative_run=built.v0069,
        claimed=built.run,
    )

    assert verification.valid
    assert verification.claimed_run_id == built.run.run_id
    assert verification.replayed_run_id == built.run.run_id
    assert verification.independently_replayed_subset_count == 1_225
    assert verification.independent_fixed_policy_recurrence
    assert not verification.independent_full_planner_implementation


def test_model_only_schedule_is_identity_invariant_and_cannot_execute(
    built: _Built,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden(*_args, **_kwargs):
        raise AssertionError("no-cover model-only path crossed execution")

    monkeypatch.setattr(
        joint.acquisition,
        "promote_graph_partial_support_row_v1",
        forbidden,
    )
    monkeypatch.setattr(
        robust,
        "solve_quotient_robust_h2_v1",
        forbidden,
    )
    monkeypatch.setattr(
        observer,
        "legal_action_catalogue_v1",
        forbidden,
    )
    monkeypatch.setattr(
        joint.exact_evaluation,
        "evaluate_observation_support_exact_lift_v1",
        forbidden,
    )

    replay = joint.run_joint_pair_support_recovery_v1(
        context=built.context,
        base_closure=built.base_closure,
        base_bridge=built.base_bridge,
        base_audit=built.base_audit,
        threshold=built.threshold,
        transaction1=built.transaction1,
        v0069_negative_run=built.v0069,
        max_workers=1,
    )

    assert replay.run_id == built.run.run_id
    assert replay.to_document() == built.run.to_document()


def test_missing_pair_and_authority_transplant_attacks_fail_closed(
    built: _Built,
) -> None:
    error = joint.ObservationSupportJointPairInvariantViolation

    with pytest.raises(error, match="topology"):
        replace(
            built.run,
            pair_evidence=built.run.pair_evidence[:-1],
        )
    transplanted = replace(
        built.run.pair_evidence[0],
        parent_model_id="f" * 64,
    )
    forged = tuple(
        sorted(
            (transplanted, *built.run.pair_evidence[1:]),
            key=lambda item: item.evidence_id,
        )
    )
    with pytest.raises(error, match="transplanted"):
        replace(built.run, pair_evidence=forged)
    with pytest.raises(error, match="schema"):
        replace(built.run, maximum_subset_cardinality=3)
    with pytest.raises(error):
        replace(built.run, third_transaction_allowed=True)
    with pytest.raises(error):
        replace(built.run, global_16384_checkpoint_accesses=1)
    with pytest.raises(error, match="sample boundary"):
        replace(
            built.probe,
            matched_direct_sample_advantage_eligible=True,
        )
    forged_metric = replace(
        built.run.pair_evidence[0],
        root_reward_lower=(
            None
            if built.run.pair_evidence[0].root_reward_lower is None
            else built.run.pair_evidence[0].root_reward_lower + 1
        ),
    )
    attacked_evidence = tuple(
        sorted(
            (forged_metric, *built.run.pair_evidence[1:]),
            key=lambda item: item.evidence_id,
        )
    )
    with pytest.raises(error):
        attacked = replace(
            built.run,
            pair_evidence=attacked_evidence,
        )
        joint.verify_joint_pair_support_recovery_v1(
            context=built.context,
            base_closure=built.base_closure,
            base_bridge=built.base_bridge,
            base_audit=built.base_audit,
            threshold=built.threshold,
            transaction1=built.transaction1,
            v0069_negative_run=built.v0069,
            claimed=attacked,
        )


def _cardinality_fixture(
    row_count: int,
) -> joint.JointPairMaterializationCardinalityV1:
    catalogue_id = "a" * 64
    binding_keys = tuple(
        (catalogue_id, (index, 0, 0)) for index in range(row_count)
    )
    draws = 4_096 + row_count * (64 + 8_192)
    return joint.JointPairMaterializationCardinalityV1(
        "0" * 64,
        "1" * 64,
        ("2" * 64, "3" * 64),
        (catalogue_id,),
        binding_keys,
        4_096,
        row_count,
        draws,
        row_count <= 19,
        draws < 163_840,
    )


def test_nineteen_child_rows_are_the_exact_pre_sampling_boundary() -> None:
    within = _cardinality_fixture(19)
    dominated = _cardinality_fixture(20)

    assert within.incremental_draw_upper == 160_960
    assert within.within_registered_caps
    assert within.avoids_further_global_checkpoint_tax
    assert dominated.incremental_draw_upper == 169_216
    assert not dominated.within_registered_caps
    assert not dominated.avoids_further_global_checkpoint_tax
    with pytest.raises(
        joint.ObservationSupportJointPairInvariantViolation,
        match="registered finite profile",
    ):
        replace(
            joint.registered_joint_pair_caps_v1(),
            max_subset_cardinality=3,
        )


def test_claim_boundary_remains_locked(
    built: _Built,
) -> None:
    assert built.probe.matched_direct_8192_draws == 165_120
    assert built.probe.transaction1_prefix_draws == 414_848
    assert built.probe.matched_direct_headroom == -249_728
    assert not built.probe.matched_direct_sample_advantage_eligible
    assert not built.probe.sample_efficiency_claimed
    assert built.probe.max_global_checkpoint == 8_192
    assert built.probe.global_16384_checkpoint_accesses == 0
    assert not built.probe.third_transaction_allowed
