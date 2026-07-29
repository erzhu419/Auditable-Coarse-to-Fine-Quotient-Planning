from __future__ import annotations

from dataclasses import replace
from fractions import Fraction
import ast
import hashlib
import inspect
import json

import pytest

from acfqp.phase3e_ids import canonical_json_bytes
from acfqp import v075_learned_support_quotient_planners_v1 as planners
from acfqp import v075_public_campaign_authority_v1 as authority
from acfqp import v075_public_graph_semantics_v1 as graph
from acfqp import v075_registered_occurrence_worker_v1 as worker
from acfqp import v075_route_native_backend_core_v1 as backend


def _id(label: str) -> str:
    return hashlib.sha256(
        b"acfqp:v075-support-planner-test:v1"
        + b"\x00"
        + label.encode("utf-8")
    ).hexdigest()


def _reward(context, state, action) -> Fraction:
    rank = state.ranks[action[0]]
    return (
        Fraction(2 ** (rank + 1), 2 ** (context.rank_cap + 1))
        / context.horizon
    )


def _descriptor(context, state, action, remaining_horizon):
    first, second, survivor = action
    board = list(state.ranks)
    rank = board[first]
    board[first] = 0
    board[second] = 0
    board[survivor] = min(rank + 1, context.rank_cap)
    empty = tuple(index for index, value in enumerate(board) if value == 0)
    candidates = []
    for cell in empty:
        for spawn_rank in range(1, context.rank_cap + 1):
            successor = list(board)
            successor[cell] = spawn_rank
            ranks = tuple(successor)
            failure = not graph.legal_action_triples_v1(
                context,
                ranks,
                False,
            )
            candidates.append((failure, cell, ranks))
    # Prefer a nonfailure realization so the construction policy has a
    # genuine H=2 continuation.
    failure, _cell, ranks = sorted(candidates)[0]
    state_out = graph.V075SymbolicGraphStateV1(
        context,
        ranks,
        failure,
    )
    return backend.V075OutcomeDescriptorV1(
        context.context_id,
        state_out.state_id,
        state_out.ranks,
        failure,
        failure or remaining_horizon == 1,
        _reward(context, state, action),
    )


def _intervals(
    descriptor,
    *,
    other_probability: Fraction = Fraction(0),
):
    draw_count = other_probability.denominator
    other_count = other_probability.numerator
    support_count = draw_count - other_count
    support_probability = Fraction(support_count, draw_count)
    return (
        backend.V075EventIntervalV1(
            descriptor.descriptor_id,
            descriptor,
            draw_count,
            support_count,
            support_probability,
            support_probability,
            support_probability,
            0,
            0,
        ),
        backend.V075EventIntervalV1(
            "OTHER",
            None,
            draw_count,
            other_count,
            other_probability,
            other_probability,
            other_probability,
            0,
            0,
        ),
    )


def _row(
    context,
    catalogue,
    action,
    *,
    label,
    other_probability: Fraction = Fraction(0),
):
    binding = graph.observation_row_binding_v1(
        context,
        catalogue,
        action,
    )
    descriptor = _descriptor(
        context,
        catalogue.state,
        action,
        catalogue.remaining_horizon,
    )
    return backend.V075StatisticalRowV1(
        context.context_id,
        binding.row_binding_id,
        catalogue.state.state_id,
        catalogue.remaining_horizon,
        action,
        (_id(label + "-discovery"),),
        (_id(label + "-validation"),),
        (descriptor,),
        _intervals(
            descriptor,
            other_probability=other_probability,
        ),
        1,
        "TYPED_SUPPORT_GRAPH_REPLAY_NOT_AVAILABLE",
    )


def _work(request_id, arm):
    adaptive = arm is not worker.V075WorkerArmV1.MATCHED_DIRECT_GROUND
    values = {path: 0 for path in backend.COUNTER_PATHS}
    values["common.request_reconstructions"] = 1
    values["adaptive.route_attempts"] = int(adaptive)
    values["direct.route_attempts"] = int(not adaptive)
    values[
        {
            worker.V075WorkerArmV1.SOURCE_CONSENSUS_PRIOR:
            "adaptive.source_proposal_attempts",
            worker.V075WorkerArmV1.NO_PRIOR: "adaptive.no_prior_attempts",
            worker.V075WorkerArmV1.WRONG_CONSENSUS_PRIOR:
            "adaptive.wrong_prior_attempts",
            worker.V075WorkerArmV1.OOD_ABSTENTION:
            "adaptive.ood_abstention_attempts",
            worker.V075WorkerArmV1.MATCHED_DIRECT_GROUND:
            "direct.route_attempts",
        }[arm]
    ] = 1
    return backend.V075BackendWorkV1(
        request_id,
        arm,
        tuple(
            backend.V075BackendCounterV1(path, values[path])
            for path in backend.COUNTER_PATHS
        ),
    )


def _complete_backend_result(
    arm=worker.V075WorkerArmV1.NO_PRIOR,
    *,
    child_other_probability: Fraction = Fraction(0),
):
    context = (
        authority.freeze_v075_public_family_generation_v1()
        .replicate_contexts[0]
    )
    root = graph.root_catalogue_v1(context)
    root_rows = tuple(
        _row(
            context,
            root,
            action,
            label=f"root-{index}",
        )
        for index, action in enumerate(root.actions)
    )
    child_states = {
        descriptor.next_state_id:
        graph.V075SymbolicGraphStateV1(
            context,
            descriptor.next_ranks,
            descriptor.failure,
        )
        for row in root_rows
        for descriptor in row.support
        if not descriptor.failure and not descriptor.terminal
    }
    child_rows = []
    for state_index, state in enumerate(
        child_states[state_id] for state_id in sorted(child_states)
    ):
        catalogue = graph.V075LegalActionCatalogueV1(
            context,
            state,
            1,
            graph.legal_action_triples_v1(
                context,
                state.ranks,
                state.failure,
            ),
        )
        child_rows.extend(
            _row(
                context,
                catalogue,
                action,
                label=f"child-{state_index}-{action_index}",
                other_probability=child_other_probability,
            )
            for action_index, action in enumerate(catalogue.actions)
        )
    rows = tuple(
        sorted((*root_rows, *child_rows), key=lambda item: item.row_id)
    )
    request_id = _id("request-" + arm.value)
    occurrence_id = _id("occurrence-" + arm.value)
    route = (
        worker.V075WorkerRouteV1.MATCHED_DIRECT_GROUND
        if arm is worker.V075WorkerArmV1.MATCHED_DIRECT_GROUND
        else worker.V075WorkerRouteV1.ADAPTIVE_QUOTIENT
    )
    caps = worker.V075WorkerCapProfileV1()
    schedule = backend.V075RouteScheduleV1(
        request_id,
        arm,
        route,
        ((_id("discovery-stream-" + arm.value), 64),),
        ((_id("validation-stream-" + arm.value), 2_048),),
        backend.V075BackendScheduleStatusV1.COMPLETE_REGISTERED_CHECKPOINT,
        caps.cap_profile_id,
    )
    registration = (
        worker.freeze_v075_worker_registry_draft_v1().require_arm(arm)
    )
    proposal = backend.V075ProposalBasisV1(
        request_id,
        arm,
        registration.proposal_semantics,
        (
            backend.SOURCE_FORWARD_MIDRANK
            if arm is worker.V075WorkerArmV1.SOURCE_CONSENSUS_PRIOR
            else (
                backend.REGISTERED_WRONG_REVERSED_MIDRANK
                if arm is worker.V075WorkerArmV1.WRONG_CONSENSUS_PRIOR
                else ()
            )
        ),
        (
            _id("source-transport")
            if arm is worker.V075WorkerArmV1.SOURCE_CONSENSUS_PRIOR
            else None
        ),
    )
    model = backend.V075StatisticalModelV1(
        request_id,
        occurrence_id,
        arm,
        proposal.proposal_id,
        schedule.schedule_id,
        rows,
        True,
        True,
        (),
    )
    status = (
        backend.V075BackendCandidateStatusV1
        .NOT_READY_TYPED_SUPPORT_GRAPH_BINDER
    )
    policy = backend.V075PolicyCandidateV1(
        model.model_id,
        arm,
        status,
        tuple(
            sorted(
                row.row_id
                for row in root_rows
            )
        ),
    )
    envelope = backend.V075EnvelopeCandidateV1(
        model.model_id,
        policy.policy_candidate_id,
        status,
    )
    capability_ids = tuple(
        sorted(
            {
                item
                for row in rows
                for item in (
                    *row.discovery_capability_ids,
                    *row.validation_capability_ids,
                )
            }
        )
    )
    total_lift = backend.V075TotalLiftCandidateInputV1(
        occurrence_id,
        model.model_id,
        policy.policy_candidate_id,
        envelope.envelope_candidate_id,
        status,
        tuple(row.row_id for row in rows),
        capability_ids,
    )
    return backend.V075RouteNativeBackendResultV1(
        request_id,
        occurrence_id,
        arm,
        schedule,
        proposal,
        model,
        policy,
        envelope,
        total_lift,
        _work(request_id, arm),
    )


def _graph(
    arm=worker.V075WorkerArmV1.NO_PRIOR,
    *,
    child_other_probability: Fraction = Fraction(0),
):
    return planners.compile_v075_learned_support_graph_v1(
        _complete_backend_result(
            arm,
            child_other_probability=child_other_probability,
        )
    )


def _replace_backend_rows(result, rows):
    canonical_rows = tuple(sorted(rows, key=lambda item: item.row_id))
    model = replace(result.model, rows=canonical_rows)
    policy = replace(result.policy, model_id=model.model_id)
    envelope = replace(
        result.envelope,
        model_id=model.model_id,
        policy_candidate_id=policy.policy_candidate_id,
    )
    capability_ids = tuple(
        sorted(
            {
                item
                for row in canonical_rows
                for item in (
                    *row.discovery_capability_ids,
                    *row.validation_capability_ids,
                )
            }
        )
    )
    total_lift = replace(
        result.total_lift_input,
        model_id=model.model_id,
        policy_candidate_id=policy.policy_candidate_id,
        envelope_candidate_id=envelope.envelope_candidate_id,
        observed_row_ids=tuple(item.row_id for item in canonical_rows),
        capability_ref_ids=capability_ids,
    )
    return replace(
        result,
        model=model,
        policy=policy,
        envelope=envelope,
        total_lift_input=total_lift,
    )


def test_complete_typed_support_graph_and_observation_lineage() -> None:
    support = _graph()
    assert len(support.nodes) == 3
    assert sum(len(item.rows) for item in support.nodes) == 6
    assert support.root.remaining_horizon == 2
    assert support.familywise_confidence_error_upper == Fraction(
        6,
        300_000,
    )
    assert support.observation_artifact_ref_ids == tuple(
        sorted(
            support.backend_result.total_lift_input.capability_ref_ids
        )
    )
    document = support.to_document()
    assert document["complete_modeled_h2_closure"] is True
    assert document["support_is_observation_driven"] is True
    assert document["law_or_exact_atom_access"] is False
    assert document["other_behavior"] == planners.POLICY_ABORT_RULE


def test_partial_world_model_maps_unmaterialized_positive_child_to_abort() -> None:
    full = _complete_backend_result()
    root_rows = tuple(
        row for row in full.model.rows if row.remaining_horizon == 2
    )
    child_state_ids = sorted(
        {
            descriptor.next_state_id
            for row in root_rows
            for descriptor in row.support
            if not descriptor.failure and not descriptor.terminal
        }
    )
    omitted = child_state_ids[-1]
    partial = _replace_backend_rows(
        full,
        tuple(
            row
            for row in full.model.rows
            if row.source_state_id != omitted
        ),
    )
    support = planners.compile_v075_learned_support_graph_v1(partial)
    assert support.complete_modeled_h2_closure is False
    assert omitted not in support.active_child_state_ids
    omitted_descriptors = {
        descriptor.descriptor_id
        for row in root_rows
        for descriptor in row.support
        if descriptor.next_state_id == omitted
    }
    assert omitted_descriptors <= set(
        support.unmaterialized_root_support_descriptor_ids
    )
    assert all(
        omitted_descriptors.isdisjoint(active_ids)
        for row_id, active_ids in support.row_active_support_descriptor_ids
        if row_id in {row.row_id for row in root_rows}
    )
    quotient = planners.compile_v075_observation_driven_quotient_v1(
        support
    )
    root_behaviors = tuple(
        behavior
        for behavior in quotient.row_behaviors
        if behavior.row_id in {row.row_id for row in root_rows}
    )
    assert any(
        term.destination_kind
        is planners.V075RobustDestinationKindV1.POLICY_ABORT_OTHER
        and term.upper_probability > 0
        for behavior in root_behaviors
        for term in behavior.terms
    )
    planned = planners.plan_v075_exact_h2_abstract_v1(support)
    assert planned.policy is not None
    assert planned.to_document()["scientific_plan_certificate"] is False


def test_partial_child_action_catalogue_and_orphan_child_are_rejected() -> None:
    full = _complete_backend_result()
    child_rows = tuple(
        row for row in full.model.rows if row.remaining_horizon == 1
    )
    target = child_rows[0].source_state_id
    same_state = tuple(
        row for row in child_rows if row.source_state_id == target
    )
    assert len(same_state) > 1
    incomplete = _replace_backend_rows(
        full,
        tuple(row for row in full.model.rows if row != same_state[0]),
    )
    with pytest.raises(
        planners.V075LearnedSupportPlannerInvariantViolation,
        match="complete materialized reconstructed catalogue",
    ):
        planners.compile_v075_learned_support_graph_v1(incomplete)

    orphan_row = replace(
        same_state[0],
        source_state_id=_id("transplanted-orphan-child"),
    )
    orphan = _replace_backend_rows(
        full,
        tuple(
            orphan_row if row == same_state[0] else row
            for row in full.model.rows
        ),
    )
    with pytest.raises(
        planners.V075LearnedSupportPlannerInvariantViolation,
        match="unobserved",
    ):
        planners.compile_v075_learned_support_graph_v1(orphan)


def test_observation_driven_quotient_compresses_states_and_actions() -> None:
    support = _graph()
    quotient = planners.compile_v075_observation_driven_quotient_v1(
        support
    )
    assert len(quotient.cells) == 2
    child_cell = next(
        item for item in quotient.cells if item.remaining_horizon == 1
    )
    assert len(child_cell.state_ids) == 2
    assert len(quotient.semantic_actions) == 2
    assert all(
        len(item.concretizers) == len(item.cell.state_ids)
        for item in quotient.semantic_actions
    )
    assert all(
        all(
            weight == Fraction(1, len(concretizer.ground_actions))
            for weight in concretizer.uniform_weights
        )
        for item in quotient.semantic_actions
        for concretizer in item.concretizers
    )
    document = quotient.to_document()
    assert document["known_automorphism_used"] is False
    assert document["initial_human_or_group_partition_used"] is False


def test_exact_abstract_and_matched_direct_planners_preserve_value() -> None:
    abstract = planners.plan_v075_exact_h2_abstract_v1(_graph())
    direct = planners.plan_v075_exact_h2_matched_direct_ground_v1(
        _graph(worker.V075WorkerArmV1.MATCHED_DIRECT_GROUND)
    )
    assert abstract.status is (
        planners.V075PlannerStatusV1
        .CANDIDATE_CERTIFIED_FOR_EXACT_TOTAL_LIFT
    )
    assert direct.status is abstract.status
    assert abstract.envelope is not None
    assert direct.envelope is not None
    for result in (abstract, direct):
        assert result.envelope.selected_reward_lower == Fraction(3, 64)
        assert result.envelope.selected_reward_upper == Fraction(3, 64)
        assert result.envelope.unrestricted_reward_upper == Fraction(3, 64)
        assert result.envelope.selected_failure_upper == 0
        assert result.envelope.normalized_regret_upper == 0
        assert result.ready_for_exact_total_lift is True
        assert result.to_document()["scientific_plan_certificate"] is False
    assert abstract.policy is not None
    assert direct.policy is not None
    assert len(abstract.policy.decisions[0].state_choices[0].ground_actions) == 2
    assert len(direct.policy.decisions[0].state_choices[0].ground_actions) == 1


def test_other_is_policy_abort_not_conditional_renormalization() -> None:
    result = planners.plan_v075_exact_h2_abstract_v1(
        _graph(child_other_probability=Fraction(1, 100))
    )
    assert result.envelope is not None
    assert result.envelope.selected_failure_upper == Fraction(1, 100)
    # The H=1 merge reward is earned before the post-spawn policy abort;
    # only continuation reward is zero.
    assert result.envelope.selected_reward_lower == Fraction(3, 64)
    assert result.to_document()["envelope"]["other_behavior"] == (
        planners.POLICY_ABORT_RULE
    )


def test_no_risk_feasible_retains_replayable_min_risk_diagnostic_frontier(
) -> None:
    support = _graph(child_other_probability=Fraction(1, 10))
    first = planners.plan_v075_exact_h2_abstract_v1(support)
    second = planners.plan_v075_exact_h2_abstract_v1(support)
    assert first == second
    assert first.canonical_bytes == second.canonical_bytes
    assert first.status is (
        planners.V075PlannerStatusV1.NO_RISK_FEASIBLE_POLICY
    )
    assert first.ready_for_exact_total_lift is False
    assert first.policy is not None
    assert first.envelope is not None
    assert first.envelope.selected_failure_upper == Fraction(1, 10)
    assert first.diagnostic_failed_frontier_row_ids
    root_rows = tuple(
        sorted(
            row_id
            for decision in first.policy.decisions
            if decision.remaining_horizon == 2
            for choice in decision.state_choices
            for row_id in choice.row_ids
        )
    )
    assert first.diagnostic_failed_frontier_row_ids[: len(root_rows)] == (
        root_rows
    )
    document = first.to_document()
    assert document["diagnostic_selection_rule"] == (
        "MIN_FAILURE_UPPER_THEN_MAX_REWARD_LOWER_THEN_"
        "LEXICOGRAPHIC_POLICY_V1"
    )
    assert document["scientific_plan_certificate"] is False
    assert document["ready_for_exact_total_lift"] is False
    values = {item.path: item.value for item in first.work.counters}
    assert values["common.total_lift_candidate_emissions"] == 0


def test_route_separation_is_strict() -> None:
    with pytest.raises(
        planners.V075LearnedSupportPlannerInvariantViolation,
        match="direct arm",
    ):
        planners.compile_v075_observation_driven_quotient_v1(
            _graph(worker.V075WorkerArmV1.MATCHED_DIRECT_GROUND)
        )
    with pytest.raises(
        planners.V075LearnedSupportPlannerInvariantViolation,
        match="direct arm",
    ):
        planners.plan_v075_exact_h2_matched_direct_ground_v1(_graph())


def test_structurally_impossible_outcome_is_rejected() -> None:
    result = _complete_backend_result()
    root_row = next(
        item for item in result.model.rows if item.remaining_horizon == 2
    )
    descriptor = root_row.support[0]
    ranks = list(descriptor.next_ranks)
    zero_cells = [index for index, rank in enumerate(ranks) if rank == 0]
    ranks[zero_cells[0]] = 1
    impossible = replace(
        descriptor,
        next_ranks=tuple(ranks),
        next_state_id=_id("impossible-next-state"),
    )
    bad_row = replace(
        root_row,
        support=(impossible,),
        intervals=_intervals(impossible),
    )
    rows = tuple(
        sorted(
            (
                bad_row if item.row_id == root_row.row_id else item
                for item in result.model.rows
            ),
            key=lambda item: item.row_id,
        )
    )
    model = replace(result.model, rows=rows)
    policy = replace(result.policy, model_id=model.model_id)
    envelope = replace(
        result.envelope,
        model_id=model.model_id,
        policy_candidate_id=policy.policy_candidate_id,
    )
    total_lift = replace(
        result.total_lift_input,
        model_id=model.model_id,
        policy_candidate_id=policy.policy_candidate_id,
        envelope_candidate_id=envelope.envelope_candidate_id,
        observed_row_ids=tuple(item.row_id for item in rows),
    )
    bad = replace(
        result,
        model=model,
        policy=policy,
        envelope=envelope,
        total_lift_input=total_lift,
    )
    with pytest.raises(
        planners.V075LearnedSupportPlannerInvariantViolation,
        match="structurally possible",
    ):
        planners.compile_v075_learned_support_graph_v1(bad)


def test_interval_simplex_attack_and_lineage_omission_fail() -> None:
    result = _complete_backend_result()
    row = result.model.rows[0]
    support, other = row.intervals
    bad_row = replace(
        row,
        intervals=(
            support,
            replace(
                other,
                success_count=other.draw_count,
                empirical_probability=Fraction(1),
                lower_probability=Fraction(1),
                upper_probability=Fraction(1),
            ),
        ),
    )
    # Backend row construction permits caller-supplied marginal intervals;
    # the learned graph must reject their empty joint simplex.
    with pytest.raises(
        planners.V075LearnedSupportPlannerInvariantViolation,
        match="partition",
    ):
        planners.V075LearnedStateNodeV1(
            next(
                node.catalogue
                for node in _graph().nodes
                if node.state_id == row.source_state_id
            ),
            tuple(
                bad_row if item.row_id == row.row_id else item
                for item in next(
                    node.rows
                    for node in _graph().nodes
                    if node.state_id == row.source_state_id
                )
            ),
        )
    support_graph = _graph()
    with pytest.raises(
        planners.V075LearnedSupportPlannerInvariantViolation,
        match="lineage",
    ):
        replace(
            support_graph,
            observation_artifact_ref_ids=(
                support_graph.observation_artifact_ref_ids[1:]
            ),
        )


def test_identity_replay_tamper_and_native_zero_accounting() -> None:
    abstract = planners.plan_v075_exact_h2_abstract_v1(_graph())
    verified = planners.verify_v075_abstract_planner_result_v1(
        graph=abstract.graph,
        claimed_bytes=abstract.canonical_bytes,
    )
    assert verified == abstract
    document = json.loads(abstract.canonical_bytes)
    document["production_integration_ready"] = True
    with pytest.raises(
        planners.V075LearnedSupportPlannerInvariantViolation,
        match="recomputation",
    ):
        planners.verify_v075_abstract_planner_result_v1(
            graph=abstract.graph,
            claimed_bytes=canonical_json_bytes(document),
        )
    direct = planners.plan_v075_exact_h2_matched_direct_ground_v1(
        _graph(worker.V075WorkerArmV1.MATCHED_DIRECT_GROUND)
    )
    adaptive_values = {
        item.path: item.value for item in abstract.work.counters
    }
    direct_values = {item.path: item.value for item in direct.work.counters}
    assert adaptive_values["direct.ground_states_considered"] == 0
    assert adaptive_values["direct.ground_actions_considered"] == 0
    assert direct_values["adaptive.quotient_compiler_calls"] == 0
    assert direct_values["adaptive.cells_compiled"] == 0
    assert tuple(item.path for item in abstract.work.counters) == (
        planners.PLANNER_COUNTER_PATHS
    )
    assert all(item.observed for item in abstract.work.counters)


def test_exact_search_cap_exhaustion_is_noncertificate(monkeypatch) -> None:
    monkeypatch.setattr(planners, "MAX_EXACT_POLICY_ASSIGNMENTS", 0)
    result = planners.plan_v075_exact_h2_abstract_v1(_graph())
    assert result.status is planners.V075PlannerStatusV1.SEARCH_CAP_EXHAUSTED
    assert result.policy is None
    assert result.envelope is None
    assert result.ready_for_exact_total_lift is False


def test_module_has_no_private_or_exact_transition_authority_import() -> None:
    tree = ast.parse(inspect.getsource(planners))
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(item.name for item in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module or "")
    forbidden = (
        "private_observer",
        "private_environment",
        "transition_engine",
        "h2_graph",
        "v072",
    )
    assert not any(
        fragment in item
        for item in imports
        for fragment in forbidden
    )
    keys = set()

    def walk(value):
        if isinstance(value, dict):
            keys.update(value)
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(planners.plan_v075_exact_h2_abstract_v1(_graph()).to_document())
    assert keys.isdisjoint(
        {
            "law",
            "secret_laws",
            "environment_reveal",
            "salt",
            "private_signer",
            "observer_session",
            "random_words",
            "seed",
            "exact_atoms",
            "kernel",
        }
    )
