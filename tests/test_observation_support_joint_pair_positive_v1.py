from __future__ import annotations

from itertools import combinations

import pytest

import acfqp.observation_support_joint_pair_recovery_v1 as joint
import acfqp.partial_support_robust_planner_v1 as robust
from tests.test_partial_support_expansion_authority_v1 import (
    _build_noncausal_fixture,
)


@pytest.fixture(scope="module")
def positive_pair_fixture():
    patcher = pytest.MonkeyPatch()
    try:
        fixture = _build_noncausal_fixture(patcher)
        direct = fixture.bridge.direct_model
        singleton_concretizer = tuple(
            robust.DistinctActionConcretizerEntryV1(
                catalogue.state_coordinate_key,
                catalogue.state_id,
                action.action_coordinate_key,
                (action.action_id,),
            )
            for catalogue in direct.catalogues
            for action in catalogue.actions
        )
        model = robust.build_partial_support_model_v1(
            context_id=direct.context_id,
            root_state_id=direct.root_state_id,
            catalogues=direct.catalogues,
            destinations=direct.destinations,
            rows=direct.rows,
            concretizer_entries=singleton_concretizer,
        )
        audit = robust.solve_quotient_robust_h2_v1(
            model,
            fixture.threshold,
        )
        assert (
            audit.status
            is robust.RobustAuditStatus.FAILED_PROOF_FRONTIER
        )
        assert audit.failed_frontier is not None
        projection_by_planner = {
            item.planner_row.row_id: item
            for item in fixture.bridge.row_projections
        }
        assignment = {
            (item.scope_key, item.remaining_horizon):
            item.selected_action_key
            for item in audit.assignments
        }
        planner_row_by_key = {
            (
                item.state_id,
                item.remaining_horizon,
                item.action_id,
            ): item
            for item in model.rows
        }
        selected_planner_rows: set[str] = set()
        for entry in model.concretizer_entries:
            horizon = (
                2
                if entry.state_id
                == model.root_state_id
                else 1
            )
            if (
                assignment.get((entry.state_coordinate_key, horizon))
                != entry.abstract_action_key
            ):
                continue
            selected_planner_rows.update(
                planner_row_by_key[
                    (entry.state_id, horizon, action_id)
                ].row_id
                for action_id in entry.ground_action_ids
            )
        row_by_partial = {
            item.partial_row_id: item for item in fixture.rows
        }
        candidates = []
        for planner_row_id in audit.failed_frontier.other_positive_row_ids:
            if planner_row_id not in selected_planner_rows:
                continue
            projection = projection_by_planner[planner_row_id]
            row = row_by_partial[projection.partial_row_id]
            candidates.append(
                joint.JointPairCandidateRowV1(
                    planner_row_id,
                    row.partial_row_id,
                    row.binding.row_id,
                    row.physical_evidence_id,
                    row.support_epoch.support_epoch_id,
                    row.confidence_authority.authority_id,
                    row.binding.remaining_horizon,
                    ("f" * 64,),
                )
            )
        candidates = tuple(
            sorted(candidates, key=lambda item: item.candidate_id)
        )
        registry = joint.JointPairCandidateRegistryV1(
            audit.model_id,
            audit.audit_id,
            audit.failed_frontier.frontier_id,
            fixture.threshold.threshold_profile_id,
            tuple(sorted(item.assignment_id for item in audit.assignments)),
            fixture.bridge.source_partial_row_ids,
            (),
            (),
            (),
            candidates,
        )
        singletons = joint._model_only_evidence(
            model=model,
            audit=audit,
            threshold=fixture.threshold,
            registry=registry,
            subsets=tuple((item,) for item in candidates),
            max_workers=1,
        )
        pairs = joint._model_only_evidence(
            model=model,
            audit=audit,
            threshold=fixture.threshold,
            registry=registry,
            subsets=tuple(
                tuple(pair) for pair in combinations(candidates, 2)
            ),
            max_workers=1,
        )
        yield fixture, model, audit, registry, singletons, pairs
    finally:
        patcher.undo()


def test_joint_recurrence_detects_interaction_missed_by_every_singleton(
    positive_pair_fixture,
) -> None:
    _, _, _, registry, singletons, pairs = positive_pair_fixture

    assert len(registry.candidates) == 5
    assert len(singletons) == 5
    assert len(pairs) == 10
    assert all(
        item.status is joint.ModelOnlySubsetStatus.STILL_FAILED
        for item in singletons
    )
    assert all(
        item.status is joint.ModelOnlySubsetStatus.FIXED_PLAN_CERTIFIED
        for item in pairs
    )


def test_independent_fixed_policy_recurrence_matches_positive_pair_screen(
    positive_pair_fixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture, model, audit, registry, singletons, pairs = (
        positive_pair_fixture
    )
    by_candidate = {
        item.candidate_id: item for item in registry.candidates
    }

    def forbidden(*_args, **_kwargs):
        raise AssertionError("independent replay called operational recurrence")

    monkeypatch.setattr(
        joint,
        "_fixed_policy_metrics_operational",
        forbidden,
    )
    independently_replayed = tuple(
        joint._independent_subset_evidence(
            model=model,
            audit=audit,
            threshold=fixture.threshold,
            registry=registry,
            candidates=tuple(
                by_candidate[candidate_id]
                for candidate_id in item.candidate_ids
            ),
        )
        for item in (*singletons, *pairs)
    )

    assert independently_replayed == (*singletons, *pairs)
