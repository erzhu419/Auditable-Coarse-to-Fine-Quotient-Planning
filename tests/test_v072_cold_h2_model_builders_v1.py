from __future__ import annotations

from dataclasses import fields, replace
from fractions import Fraction
import hashlib
import inspect
from typing import Any

import pytest

from acfqp import partial_support_robust_planner_v1 as robust
from acfqp import exact_lazy_h2_robust_planner_v1 as exact_lazy
from acfqp import exact_lazy_h2_independent_verifier_v1 as lazy_independent
from acfqp import v072_cold_h2_closure_v1 as closure
from acfqp import v072_cold_h2_model_builders_v1 as models
from acfqp import v072_confidence_row_projection_v1 as row_projection
from acfqp import v072_heldout_public_graph_adapter_v1 as public_adapter
from acfqp import transfer_guided_acquisition_preregistration_v1 as prereg
from acfqp import (
    v072_cold_h2_model_builders_independent_verifier_v1 as independent,
)


def _id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


CONTEXT_ID = _id("v072-model-builder-independent-multirow-context")
CONTEXT_KEY = "v072_model_builder_independent_multirow_context_v1"
DEVELOPMENT_SCOPE_ID = _id("v072-model-builder-development-scope")
TOPOLOGY_ID = _id("v072-model-builder-k4-topology")
K4_EDGES = tuple(
    (first, second)
    for first in range(4)
    for second in range(first + 1, 4)
)
ROOT = "root"
CHILD_A = "child-a"
CHILD_B = "child-b"
NOVEL = "validation-novel-do-not-expand"
RANKS = {
    ROOT: (1, 1, 2, 3),
    CHILD_A: (2, 2, 1, 3),
    CHILD_B: (3, 1, 2, 2),
    NOVEL: (1, 2, 3, 4),
}
MERGE_EDGE = {
    ROOT: (0, 1),
    CHILD_A: (0, 1),
    CHILD_B: (2, 3),
}


def _state(label: str) -> closure.ColdPublicStateV1:
    return closure.ColdPublicStateV1(
        _id(f"model-state:{label}"),
        {
            "schema": "test.v072_model_public_state.v1",
            "context_id": CONTEXT_ID,
            "topology_id": TOPOLOGY_ID,
            "ranks": list(RANKS[label]),
            "failure": False,
            "opaque_public_payload": f"state-payload-{label}",
            "registered_target": False,
        },
    )


def _action(label: str, position: int) -> closure.ColdPublicActionV1:
    first, second = MERGE_EDGE[label]
    return closure.ColdPublicActionV1(
        _id(f"model-action:{label}:{position}"),
        {
            "schema": "test.v072_model_public_action.v1",
            "context_id": CONTEXT_ID,
            "topology_id": TOPOLOGY_ID,
            "action": [
                first,
                second,
                first if position == 0 else second,
            ],
            "opaque_public_payload": f"action-payload-{label}-{position}",
            "registered_target": False,
        },
    )


class _PublicGraph:
    context_id = CONTEXT_ID
    horizon = 2

    def root_state_v1(self) -> closure.ColdPublicStateV1:
        return _state(ROOT)

    def canonical_state_v1(
        self,
        state: closure.ColdPublicStateV1,
    ) -> closure.ColdPublicStateV1:
        return next(
            _state(label)
            for label in RANKS
            if state.semantic_state_id == _state(label).semantic_state_id
        )

    def legal_actions_v1(
        self,
        state: closure.ColdPublicStateV1,
        remaining_horizon: int,
    ) -> tuple[closure.ColdPublicActionV1, ...]:
        label = next(
            label
            for label in RANKS
            if state.semantic_state_id == _state(label).semantic_state_id
        )
        assert remaining_horizon == (2 if label == ROOT else 1)
        return (_action(label, 0), _action(label, 1))


def _descriptor(
    name: str,
    *,
    successor: str | None = None,
) -> closure.ColdOutcomeDescriptorV1:
    return closure.ColdOutcomeDescriptorV1(
        _id(f"model-descriptor:{name}:{successor}"),
        failure=False,
        terminal=successor is None,
        successor_state=None if successor is None else _state(successor),
        document={
            "schema": "test.v072_model_outcome.v1",
            "opaque_public_payload": name,
        },
    )


def _row(
    state_label: str,
    horizon: int,
    action_position: int,
    discovery: tuple[closure.ColdOutcomeDescriptorV1, ...],
    novel: tuple[closure.ColdOutcomeDescriptorV1, ...] = (),
) -> closure.ColdRowEvidenceV1:
    key = f"{state_label}:{horizon}:{action_position}"
    return closure.ColdRowEvidenceV1(
        CONTEXT_ID,
        _state(state_label),
        horizon,
        _action(state_label, action_position),
        tuple(sorted(discovery, key=lambda item: item.descriptor_record_id)),
        tuple(sorted(novel, key=lambda item: item.descriptor_record_id)),
        _id(f"model-support-epoch:{key}"),
        _id(f"model-confidence-snapshot:{key}"),
        _id(f"model-row-replay:{key}"),
        _id(f"model-physical-row:{key}"),
        closure.ColdRowNativeWorkV1(
            discovery_random_word_calls=64,
            validation_random_word_calls=2_048,
            discovery_rejections=0,
            validation_rejections=0,
        ),
    )


def _inventory() -> tuple[closure.ColdRowEvidenceV1, ...]:
    rows = (
        _row(
            ROOT,
            2,
            0,
            (_descriptor("root-to-a", successor=CHILD_A),),
            (_descriptor("novel-only", successor=NOVEL),),
        ),
        _row(
            ROOT,
            2,
            1,
            (_descriptor("root-to-b", successor=CHILD_B),),
        ),
        _row(
            CHILD_A,
            1,
            0,
            (_descriptor("terminal-a0"),),
        ),
        _row(
            CHILD_A,
            1,
            1,
            (_descriptor("terminal-a1"),),
        ),
        _row(
            CHILD_B,
            1,
            0,
            (_descriptor("terminal-b0"),),
        ),
        _row(
            CHILD_B,
            1,
            1,
            (_descriptor("terminal-b1"),),
        ),
    )
    return tuple(sorted(rows, key=lambda item: item.row_evidence_id))


@pytest.fixture(scope="module")
def cold_bundle() -> closure.V072ColdH2ClosureBundleV1:
    return closure.freeze_v072_cold_h2_closure_v1(
        public_graph=_PublicGraph(),
        row_evidence=_inventory(),
        logical_occurrence_id=_id("model-logical-occurrence"),
        arm="NO_PRIOR",
        cap_evidence=(
            closure.development_synthetic_cold_h2_cap_evidence_v1(
                context_id=CONTEXT_ID,
                context_key=CONTEXT_KEY,
                total_physical_row_cap=8,
                development_scope_id=DEVELOPMENT_SCOPE_ID,
            )
        ),
    )


@pytest.fixture(scope="module")
def relational_context() -> models.ColdH2PublicRelationalContextV1:
    return models.ColdH2PublicRelationalContextV1(
        CONTEXT_ID,
        TOPOLOGY_ID,
        4,
        K4_EDGES,
    )


def _projection(
    row: closure.ColdRowEvidenceV1,
    *,
    support_lower: Fraction = Fraction(7, 8),
    support_upper: Fraction = Fraction(15, 16),
    other_lower: Fraction = Fraction(1, 16),
    other_upper: Fraction = Fraction(1, 8),
) -> models.VerifiedColdH2ConfidenceRowProjectionV1:
    destinations = tuple(
        sorted(
            (
                *(
                    models.destination_for_descriptor_v1(row, descriptor)
                    for descriptor in row.discovery_support
                ),
                models.other_destination_for_row_v1(row),
            ),
            key=lambda item: item.destination_id,
        )
    )
    masses = tuple(
        sorted(
            (
                *(
                    robust.IntervalDestinationMassV1(
                        destination.destination_id,
                        support_lower,
                        support_upper,
                    )
                    for destination in destinations
                    if destination.category
                    is not robust.DestinationCategory.OTHER
                ),
                robust.IntervalDestinationMassV1(
                    models.row_bound_other_destination_id_v1(row),
                    other_lower,
                    other_upper,
                ),
            ),
            key=lambda item: item.destination_id,
        )
    )
    interval_row = robust.IntervalSimplexRowV1(
        models.ground_state_id_v1(
            row.context_id, row.state, row.remaining_horizon
        ),
        row.remaining_horizon,
        models.ground_action_id_v1(
            row.context_id,
            row.state,
            row.remaining_horizon,
            row.action,
        ),
        Fraction(1, 16),
        Fraction(1, 16),
        models.row_bound_other_destination_id_v1(row),
        masses,
    )
    return models.VerifiedColdH2ConfidenceRowProjectionV1(
        context_id=row.context_id,
        row_evidence_id=row.row_evidence_id,
        physical_evidence_id=row.physical_evidence_id,
        support_epoch_id=row.support_epoch_id,
        confidence_snapshot_id=row.confidence_snapshot_id,
        row_replay_verification_id=row.row_replay_verification_id,
        discovery_transcript_id=_id(
            f"discovery-transcript:{row.row_evidence_id}"
        ),
        validation_transcript_id=_id(
            f"validation-transcript:{row.row_evidence_id}:2048"
        ),
        validation_prefix_id=_id(
            f"validation-prefix:{row.row_evidence_id}:2048"
        ),
        selected_checkpoint_draw_count=2_048,
        source_projection_id=_id(
            f"source-projection:{row.row_evidence_id}"
        ),
        projection_verification_id=_id(
            f"projection-verification:{row.row_evidence_id}"
        ),
        state_semantic_id=row.state.semantic_state_id,
        remaining_horizon=row.remaining_horizon,
        action_semantic_id=row.action.semantic_action_id,
        discovery_support_descriptor_ids=tuple(
            sorted(
                member.descriptor_record_id
                for member in row.discovery_support
            )
        ),
        validation_novel_descriptor_ids=tuple(
            sorted(
                member.descriptor_record_id
                for member in row.validation_novel
            )
        ),
        interval_row=interval_row,
        destinations=destinations,
        rank_cap=4,
        rank_profile=models.DEVELOPMENT_RANK_PROFILE,
        evidence_class=(
            models.RowProjectionEvidenceClassV1
            .DEVELOPMENT_SYNTHETIC_NONCONFIRMATORY
        ),
        registered_target_evidence=False,
    )


@pytest.fixture(scope="module")
def projections(
    cold_bundle: closure.V072ColdH2ClosureBundleV1,
) -> tuple[models.VerifiedColdH2ConfidenceRowProjectionV1, ...]:
    return tuple(_projection(row) for row in cold_bundle.all_rows)


@pytest.fixture(scope="module")
def pair(
    cold_bundle: closure.V072ColdH2ClosureBundleV1,
    projections: tuple[
        models.VerifiedColdH2ConfidenceRowProjectionV1, ...
    ],
    relational_context: models.ColdH2PublicRelationalContextV1,
) -> models.V072ColdH2ModelPairV1:
    return models.build_v072_cold_h2_models_v1(
        closure_bundle=cold_bundle,
        verified_row_projections=projections,
        relational_context=relational_context,
    )


def _unsafe(value: Any, **changes: Any) -> Any:
    result = object.__new__(type(value))
    for member in fields(value):
        object.__setattr__(
            result,
            member.name,
            changes.get(member.name, getattr(value, member.name)),
        )
    return result


def _all_keys(value: Any) -> set[str]:
    if isinstance(value, dict):
        return {
            str(key).lower()
            for key in value
        } | {
            nested
            for member in value.values()
            for nested in _all_keys(member)
        }
    if isinstance(value, (tuple, list)):
        return {
            nested
            for member in value
            for nested in _all_keys(member)
        }
    return set()


def test_builds_shared_direct_and_nontrivial_relational_models(
    cold_bundle: closure.V072ColdH2ClosureBundleV1,
    pair: models.V072ColdH2ModelPairV1,
) -> None:
    assert pair.direct_model.rows is pair.quotient_model.rows
    assert pair.direct_model.destinations is pair.quotient_model.destinations
    assert len(pair.shared_physical_row_ids) == len(cold_bundle.all_rows) == 6
    assert pair.shared_interval_row_ids == tuple(
        row.row_id for row in pair.direct_model.rows
    )
    assert pair.direct_model.physical_evidence_ids == tuple(
        sorted(row.physical_evidence_id for row in cold_bundle.all_rows)
    )
    direct_states = {
        item.state_coordinate_key for item in pair.direct_model.catalogues
    }
    quotient_states = {
        item.state_coordinate_key for item in pair.quotient_model.catalogues
    }
    direct_actions = {
        action.action_coordinate_key
        for catalogue in pair.direct_model.catalogues
        for action in catalogue.actions
    }
    quotient_actions = {
        action.action_coordinate_key
        for catalogue in pair.quotient_model.catalogues
        for action in catalogue.actions
    }
    assert len(quotient_states) < len(direct_states)
    assert len(quotient_actions) < len(direct_actions)
    assert all(
        catalogue.state_coordinate_key == catalogue.state_id
        and all(
            action.action_coordinate_key == action.action_id
            for action in catalogue.actions
        )
        for catalogue in pair.direct_model.catalogues
    )


def test_coordinates_are_public_behavioral_and_identity_free(
    pair: models.V072ColdH2ModelPairV1,
) -> None:
    for coordinate in pair.relational_coordinates:
        assert not (
            _all_keys(dict(coordinate.signature))
            & models.FORBIDDEN_COORDINATE_KEYS
        )
        assert "opaque_public_payload" not in str(
            coordinate.to_document()
        )
        serialized = str(coordinate.to_document()).lower()
        assert "feature_rank" not in serialized
        assert "source_prior" not in serialized
    assert {
        coordinate.role for coordinate in pair.relational_coordinates
    } == {
        models.RelationalCoordinateRoleV1.STATE,
        models.RelationalCoordinateRoleV1.ACTION,
        models.RelationalCoordinateRoleV1.SUPPORT,
    }


def test_fixed_distinct_action_concretizer_is_exact_partition(
    pair: models.V072ColdH2ModelPairV1,
) -> None:
    catalogues = {
        item.state_id: item for item in pair.quotient_model.catalogues
    }
    entries_by_state: dict[
        str, list[robust.DistinctActionConcretizerEntryV1]
    ] = {}
    for entry in pair.quotient_model.concretizer_entries:
        entries_by_state.setdefault(entry.state_id, []).append(entry)
    for state_id, catalogue in catalogues.items():
        flattened = [
            action_id
            for entry in entries_by_state[state_id]
            for action_id in entry.ground_action_ids
        ]
        assert sorted(flattened) == [
            item.action_id for item in catalogue.actions
        ]
        assert len(flattened) == len(set(flattened))
        assert any(
            len(entry.ground_action_ids) == 2
            for entry in entries_by_state[state_id]
        )


def test_other_is_adversarial_and_bound_to_each_physical_row(
    pair: models.V072ColdH2ModelPairV1,
) -> None:
    destination_by_id = {
        item.destination_id: item
        for item in pair.direct_model.destinations
    }
    other_ids = {
        row.other_destination_id for row in pair.direct_model.rows
    }
    assert len(other_ids) == len(pair.direct_model.rows)
    assert all(
        destination_by_id[destination_id].category
        is robust.DestinationCategory.OTHER
        for destination_id in other_ids
    )
    assert all(
        sum(
            mass.destination_id == row.other_destination_id
            for mass in row.masses
        )
        == 1
        for row in pair.direct_model.rows
    )


def test_validation_novel_support_does_not_expand_model(
    cold_bundle: closure.V072ColdH2ClosureBundleV1,
    pair: models.V072ColdH2ModelPairV1,
) -> None:
    novel_ids = {
        member.descriptor_record_id
        for row in cold_bundle.all_rows
        for member in row.validation_novel
    }
    serialized = str(
        {
            "direct": pair.direct_model.to_document(),
            "quotient": pair.quotient_model.to_document(),
        }
    )
    assert novel_ids
    assert all(novel_id not in serialized for novel_id in novel_ids)
    assert _state(NOVEL).semantic_state_id not in {
        catalogue.state.semantic_state_id
        for catalogue in (
            (cold_bundle.root_catalogue,)
            + cold_bundle.child_catalogues
        )
    }


def test_independent_replay_certifies_exact_pair(
    pair: models.V072ColdH2ModelPairV1,
) -> None:
    result = (
        independent.verify_v072_cold_h2_model_pair_independently_v1(
            pair
        )
    )
    assert result.model_pair_id == pair.model_pair_id
    assert result.physical_row_count == 6
    assert result.strict_state_compression is True
    assert result.strict_action_compression is True
    assert result.registered_target_evidence_count == 0


def test_direct_only_checkpoint_exposes_standard_planner_model_and_replay(
    cold_bundle: closure.V072ColdH2ClosureBundleV1,
    projections: tuple[
        models.VerifiedColdH2ConfidenceRowProjectionV1, ...
    ],
) -> None:
    snapshot = models.build_v072_cold_h2_ground_direct_model_v1(
        closure_bundle=cold_bundle,
        verified_row_projections=projections,
    )
    assert type(snapshot.planner_model) is robust.PartialSupportIntervalModelV1
    assert snapshot.direct_model.concretizer_entries == ()
    assert snapshot.planner_model.concretizer_entries == ()
    assert snapshot.direct_model.relational_context_id is None
    assert snapshot.direct_model.source_skeleton_id is None
    assert snapshot.direct_model.coordinate_profile_id is None
    verification = (
        independent
        .verify_v072_cold_h2_ground_direct_snapshot_independently_v1(
            snapshot
        )
    )
    assert verification.snapshot_id == snapshot.snapshot_id
    assert verification.physical_row_count == 6
    assert verification.checkpoint_row_count == 6
    source = inspect.getsource(
        models.build_v072_cold_h2_ground_direct_model_v1
    )
    assert "build_v072_cold_h2_models_v1(" not in source
    assert "relational_context" not in source


def test_row_bound_other_collapse_is_behavior_preserving_and_exact_lazy_runs(
    pair: models.V072ColdH2ModelPairV1,
) -> None:
    for projection in (
        pair.direct_planner_projection,
        pair.quotient_planner_projection,
    ):
        planner = projection.planner_model
        assert (
            sum(
                destination.category
                is robust.DestinationCategory.OTHER
                for destination in planner.destinations
            )
            == 1
        )
        assert len(projection.collapse_proof.entries) == len(
            projection.source_model.rows
        )
        source_by_key = {
            row.row_key: row for row in projection.source_model.rows
        }
        for row in planner.rows:
            source = source_by_key[row.row_key]
            assert row.reward_lower == source.reward_lower
            assert row.reward_upper == source.reward_upper
            assert {
                mass.mass_id
                for mass in row.masses
                if mass.destination_id != row.other_destination_id
            } == {
                mass.mass_id
                for mass in source.masses
                if mass.destination_id != source.other_destination_id
            }
            assert (
                row.other_mass.lower,
                row.other_mass.upper,
            ) == (
                source.other_mass.lower,
                source.other_mass.upper,
            )
    direct_result = exact_lazy.solve_exact_lazy_ground_direct_h2_v1(
        pair.direct_planner_projection.planner_model,
        pair.threshold_profile,
    )
    quotient_result = exact_lazy.solve_exact_lazy_quotient_h2_v1(
        pair.quotient_planner_projection.planner_model,
        pair.threshold_profile,
    )
    assert direct_result.status is exact_lazy.ExactLazyH2SolveStatus.SOLVED
    assert quotient_result.status is exact_lazy.ExactLazyH2SolveStatus.SOLVED
    assert direct_result.audit is not None
    assert quotient_result.audit is not None
    assert (
        direct_result.audit.status
        is quotient_result.audit.status
        is robust.RobustAuditStatus.FAILED_PROOF_FRONTIER
    )
    assert (
        direct_result.audit.root_failure_upper
        == quotient_result.audit.root_failure_upper
        == Fraction(15, 64)
    )
    assert direct_result.trace is not None
    assert quotient_result.trace is not None
    assert direct_result.trace.original.branch_nodes == 4
    assert quotient_result.trace.original.branch_nodes == 2
    assert lazy_independent.verify_exact_lazy_h2_solve_result_v1(
        pair.direct_planner_projection.planner_model,
        pair.threshold_profile,
        direct_result,
    ).audit_id == direct_result.audit.audit_id
    assert lazy_independent.verify_exact_lazy_h2_solve_result_v1(
        pair.quotient_planner_projection.planner_model,
        pair.threshold_profile,
        quotient_result,
    ).audit_id == quotient_result.audit.audit_id


def test_coordinates_do_not_drift_when_confidence_endpoints_change(
    cold_bundle: closure.V072ColdH2ClosureBundleV1,
    pair: models.V072ColdH2ModelPairV1,
    relational_context: models.ColdH2PublicRelationalContextV1,
) -> None:
    changed = tuple(
        _projection(
            row,
            support_lower=Fraction(3, 4),
            support_upper=Fraction(7, 8),
            other_lower=Fraction(1, 8),
            other_upper=Fraction(1, 4),
        )
        for row in cold_bundle.all_rows
    )
    rebuilt = models.build_v072_cold_h2_models_v1(
        closure_bundle=cold_bundle,
        verified_row_projections=changed,
        relational_context=relational_context,
    )
    assert rebuilt.model_pair_id != pair.model_pair_id
    assert rebuilt.shared_interval_row_ids != pair.shared_interval_row_ids
    assert tuple(
        item.coordinate_id for item in rebuilt.relational_coordinates
    ) == tuple(
        item.coordinate_id for item in pair.relational_coordinates
    )
    assert tuple(
        (
            catalogue.state_coordinate_key,
            tuple(
                action.action_coordinate_key
                for action in catalogue.actions
            ),
        )
        for catalogue in rebuilt.quotient_model.catalogues
    ) == tuple(
        (
            catalogue.state_coordinate_key,
            tuple(
                action.action_coordinate_key
                for action in catalogue.actions
            ),
        )
        for catalogue in pair.quotient_model.catalogues
    )


def test_publicly_non_equivalent_survivor_geometry_is_not_merged() -> None:
    context_id = _id("non-equivalent-public-geometry-context")
    topology_id = _id("non-equivalent-public-geometry-topology")
    context = models.ColdH2PublicRelationalContextV1(
        context_id,
        topology_id,
        4,
        ((0, 1), (0, 2), (1, 2), (1, 3)),
    )
    state = closure.ColdPublicStateV1(
        _id("non-equivalent-public-state"),
        {
            "schema": "test.non_equivalent_public_state.v1",
            "context_id": context_id,
            "topology_id": topology_id,
            "ranks": [1, 1, 2, 3],
            "failure": False,
        },
    )
    actions = tuple(
        sorted(
            (
                closure.ColdPublicActionV1(
                    _id(f"non-equivalent-action:{survivor}"),
                    {
                        "schema": (
                            "test.non_equivalent_public_action.v1"
                        ),
                        "context_id": context_id,
                        "topology_id": topology_id,
                        "action": [0, 1, survivor],
                    },
                )
                for survivor in (0, 1)
            ),
            key=lambda item: item.action_record_id,
        )
    )
    catalogue = closure.ColdPublicCatalogueV1(
        context_id, state, 1, actions
    )
    state_value, action_values = (
        models.replay_v0066_base_coordinate_values_v1(
            context, catalogue
        )
    )
    assert state_value == 2
    assert sorted(value for _, value in action_values) == [2, 3]
    coordinates = {
        models.ObservationRelationalCoordinateV1(
            models.RelationalCoordinateRoleV1.ACTION,
            1,
            {
                "portable_base_program": (
                    "cardinality_resources("
                    "linked_filter(action_anchor,active_resources))"
                ),
                "portable_base_value": value,
                "bounded_refinement": {
                    "kind": "NOT_APPLICABLE",
                    "status": models.BOUNDED_REFINEMENT_STATUS,
                    "values": [],
                },
                "sample_independent": True,
            },
        ).coordinate_id
        for _, value in action_values
    }
    assert len(coordinates) == 2


def test_cap4_threshold_cannot_be_transplanted_with_cap6_reward_ceiling(
    pair: models.V072ColdH2ModelPairV1,
) -> None:
    production_like = robust.RobustThresholdProfileV1(
        pair.closure_bundle.context_id,
        Fraction(1, 20),
        Fraction(3, 64),
    )
    with pytest.raises(
        models.V072ColdH2ModelBuilderInvariantViolation,
        match="threshold",
    ):
        models.ColdH2PlannerProjectionV1(
            pair.direct_model,
            pair.direct_planner_projection.planner_model,
            pair.direct_planner_projection.collapse_proof,
            production_like,
        )
    attacked_projection = _unsafe(
        pair.direct_planner_projection,
        threshold_profile=production_like,
    )
    attacked_pair = _unsafe(
        pair,
        direct_planner_projection=attacked_projection,
        threshold_profile=production_like,
    )
    with pytest.raises(
        independent.V072ColdH2ModelIndependentVerificationFailure,
        match="threshold",
    ):
        independent.verify_v072_cold_h2_model_pair_independently_v1(
            attacked_pair
        )


def test_independent_direct_verifier_rejects_collapse_entry_attack(
    cold_bundle: closure.V072ColdH2ClosureBundleV1,
    projections: tuple[
        models.VerifiedColdH2ConfidenceRowProjectionV1, ...
    ],
) -> None:
    snapshot = models.build_v072_cold_h2_ground_direct_model_v1(
        closure_bundle=cold_bundle,
        verified_row_projections=projections,
    )
    proof = snapshot.collapse_proof
    first = proof.entries[0]
    forged_entry = _unsafe(
        first,
        planner_other_mass_id=_id("forged-planner-other-mass"),
    )
    forged_proof = _unsafe(
        proof,
        entries=(forged_entry, *proof.entries[1:]),
    )
    forged_projection = _unsafe(
        snapshot.planner_projection,
        collapse_proof=forged_proof,
    )
    with pytest.raises(
        independent.V072ColdH2ModelIndependentVerificationFailure,
        match="collapse entry",
    ):
        (
            independent
            .verify_v072_cold_h2_ground_direct_snapshot_independently_v1(
                _unsafe(
                    snapshot,
                    planner_projection=forged_projection,
                )
            )
        )


def test_projection_inventory_must_be_exactly_one_per_closure_row(
    cold_bundle: closure.V072ColdH2ClosureBundleV1,
    projections: tuple[
        models.VerifiedColdH2ConfidenceRowProjectionV1, ...
    ],
    relational_context: models.ColdH2PublicRelationalContextV1,
) -> None:
    for malformed in (projections[:-1], projections + (projections[0],)):
        with pytest.raises(
            models.V072ColdH2ModelBuilderInvariantViolation,
            match="one-to-one",
        ):
            models.build_v072_cold_h2_models_v1(
                closure_bundle=cold_bundle,
                verified_row_projections=malformed,
                relational_context=relational_context,
            )


def test_projection_transplant_is_rejected_before_model_construction(
    cold_bundle: closure.V072ColdH2ClosureBundleV1,
    projections: tuple[
        models.VerifiedColdH2ConfidenceRowProjectionV1, ...
    ],
    relational_context: models.ColdH2PublicRelationalContextV1,
) -> None:
    transplanted = _unsafe(
        projections[0],
        physical_evidence_id=projections[1].physical_evidence_id,
    )
    malformed = (transplanted,) + projections[1:]
    with pytest.raises(
        models.V072ColdH2ModelBuilderInvariantViolation,
        match="transplanted",
    ):
        models.build_v072_cold_h2_models_v1(
            closure_bundle=cold_bundle,
            verified_row_projections=malformed,
            relational_context=relational_context,
        )


def test_independent_replay_rejects_coordinate_and_concretizer_attacks(
    pair: models.V072ColdH2ModelPairV1,
) -> None:
    first_coordinate = pair.relational_coordinates[0]
    leaked = _unsafe(
        first_coordinate,
        _signature_object={
            **dict(first_coordinate.signature),
            "source_rank": 1,
        },
    )
    attacked_coordinates = (
        leaked,
        *pair.relational_coordinates[1:],
    )
    attacked_pair = _unsafe(
        pair,
        relational_coordinates=attacked_coordinates,
    )
    with pytest.raises(
        independent.V072ColdH2ModelIndependentVerificationFailure
    ):
        independent.verify_v072_cold_h2_model_pair_independently_v1(
            attacked_pair
        )

    quotient = pair.quotient_model
    attacked_quotient = _unsafe(
        quotient,
        concretizer_entries=quotient.concretizer_entries[:-1],
    )
    attacked_pair = _unsafe(pair, quotient_model=attacked_quotient)
    with pytest.raises(
        independent.V072ColdH2ModelIndependentVerificationFailure,
        match="concretizer",
    ):
        independent.verify_v072_cold_h2_model_pair_independently_v1(
            attacked_pair
        )


def test_independent_replay_rejects_false_merge_and_global_other_attack(
    pair: models.V072ColdH2ModelPairV1,
) -> None:
    quotient = pair.quotient_model
    root = next(
        item
        for item in quotient.catalogues
        if item.state_id == quotient.root_state_id
    )
    other_catalogue = next(
        item
        for item in quotient.catalogues
        if item.state_id != quotient.root_state_id
    )
    forged_action = _unsafe(
        root.actions[0],
        action_coordinate_key=other_catalogue.actions[
            0
        ].action_coordinate_key,
    )
    forged_root = _unsafe(
        root,
        actions=tuple(
            sorted(
                (forged_action, *root.actions[1:]),
                key=lambda item: item.action_id,
            )
        ),
    )
    forged_quotient = _unsafe(
        quotient,
        catalogues=tuple(
            sorted(
                (
                    forged_root,
                    *(
                        item
                        for item in quotient.catalogues
                        if item.state_id != root.state_id
                    ),
                ),
                key=lambda item: item.state_id,
            )
        ),
    )
    with pytest.raises(
        independent.V072ColdH2ModelIndependentVerificationFailure
    ):
        independent.verify_v072_cold_h2_model_pair_independently_v1(
            _unsafe(pair, quotient_model=forged_quotient)
        )

    rows = list(pair.direct_model.rows)
    rows[1] = _unsafe(
        rows[1], other_destination_id=rows[0].other_destination_id
    )
    forged_direct = _unsafe(
        pair.direct_model,
        rows=tuple(sorted(rows, key=lambda item: item.row_id)),
    )
    with pytest.raises(
        independent.V072ColdH2ModelIndependentVerificationFailure
    ):
        independent.verify_v072_cold_h2_model_pair_independently_v1(
            _unsafe(pair, direct_model=forged_direct)
        )


def test_independent_replay_rejects_physical_and_model_identity_attacks(
    pair: models.V072ColdH2ModelPairV1,
) -> None:
    direct = _unsafe(
        pair.direct_model,
        physical_evidence_ids=(
            _id("forged-physical-row"),
            *pair.direct_model.physical_evidence_ids[1:],
        ),
    )
    with pytest.raises(
        independent.V072ColdH2ModelIndependentVerificationFailure,
        match="binding",
    ):
        independent.verify_v072_cold_h2_model_pair_independently_v1(
            _unsafe(pair, direct_model=direct)
        )
    forged_pair = _unsafe(pair, _model_pair_id=_id("forged-model-pair"))
    with pytest.raises(
        independent.V072ColdH2ModelIndependentVerificationFailure,
        match="content ID",
    ):
        independent.verify_v072_cold_h2_model_pair_independently_v1(
            forged_pair
        )


def test_registered_target_rank_cap_six_requires_exact_authorities() -> None:
    assert (
        models.REGISTERED_TARGET_MODEL_BUILD_STATUS
        == "ENABLED_FOR_EXACT_REGISTERED_CONFIDENCE_PROJECTIONS"
    )
    contexts = prereg.registered_heldout_public_contexts_v2()
    registered = tuple(
        models.registered_cold_h2_relational_context_v1(context)
        for context in contexts
    )
    assert tuple(item.context_id for item in registered) == tuple(
        item.context_id for item in contexts
    )
    assert all(
        item.rank_cap == prereg.RANK_CAP
        and item.to_document()["registered_target_evidence"] is True
        for item in registered
    )
    with pytest.raises(
        models.RegisteredTargetColdH2ModelBuildLockedV1
    ):
        models.build_registered_target_cold_h2_models_v1(
            anchor=object(),  # type: ignore[arg-type]
            closure_bundle=object(),  # type: ignore[arg-type]
            row_projections=(),
            relational_context=object(),  # type: ignore[arg-type]
        )


def test_registered_projection_math_core_runs_on_disjoint_synthetic_rows(
    cold_bundle: closure.V072ColdH2ClosureBundleV1,
) -> None:
    row = cold_bundle.all_rows[0]
    events = tuple(
        row_projection.RegisteredConfidenceEventIntervalV1(
            _id(f"disjoint-core-support-{index}"),
            index,
            row_projection.RegisteredConfidenceEventKindV1.SUPPORT,
            descriptor.descriptor_record_id,
            Fraction(0),
            Fraction(1),
        )
        for index, descriptor in enumerate(row.discovery_support)
    ) + (
        row_projection.RegisteredConfidenceEventIntervalV1(
            _id("disjoint-core-other"),
            len(row.discovery_support),
            row_projection.RegisteredConfidenceEventKindV1.OTHER,
            None,
            Fraction(0),
            Fraction(1),
        ),
    )
    interval_row, destinations, reward = (
        row_projection.project_registered_interval_events_core_v1(
            row_evidence=row,
            event_intervals=events,
        )
    )
    assert interval_row.reward_lower == reward
    assert interval_row.reward_upper == reward
    assert len(destinations) == len(row.discovery_support) + 1
    assert {
        item.destination_id for item in interval_row.masses
    } == {item.destination_id for item in destinations}
    assert sum(
        item.category is robust.DestinationCategory.OTHER
        for item in destinations
    ) == 1


def test_registered_coordinate_core_replays_all_public_roots_without_draws(
) -> None:
    for context in prereg.registered_heldout_public_contexts_v2():
        adapter = public_adapter.HeldoutPublicGraphColdClosureAdapterV1(
            context
        )
        relational = (
            models.registered_cold_h2_relational_context_v1(context)
        )
        state_value, action_values = (
            models.replay_registered_base_coordinate_values_v1(
                relational,
                adapter.root_catalogue_v1(),
            )
        )
        assert state_value == len(adapter.root_actions)
        assert tuple(item[0] for item in action_values) == tuple(
            sorted(item.action_record_id for item in adapter.root_actions)
        )


def test_builder_and_verifier_are_kernel_free_and_verifier_rederives(
    monkeypatch: pytest.MonkeyPatch,
    cold_bundle: closure.V072ColdH2ClosureBundleV1,
    projections: tuple[
        models.VerifiedColdH2ConfidenceRowProjectionV1, ...
    ],
    relational_context: models.ColdH2PublicRelationalContextV1,
) -> None:
    def _forbidden(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("forbidden external authority was touched")

    monkeypatch.setattr(
        closure.prereg,
        "freeze_transfer_guided_acquisition_preregistration_v1",
        _forbidden,
        raising=True,
    )
    pair = models.build_v072_cold_h2_models_v1(
        closure_bundle=cold_bundle,
        verified_row_projections=projections,
        relational_context=relational_context,
    )
    independent.verify_v072_cold_h2_model_pair_independently_v1(pair)
    production_source = inspect.getsource(
        models.build_v072_cold_h2_models_v1
    )
    verifier_source = inspect.getsource(
        independent.verify_v072_cold_h2_model_pair_independently_v1
    )
    for forbidden in (
        "kernel.step",
        "hidden_law(",
        "source_prior(",
        "open_observer",
        "freeze_transfer_guided",
    ):
        assert forbidden not in production_source
        assert forbidden not in verifier_source
    for forbidden_call in (
        "build_v072_cold_h2_models_v1(",
        "ground_state_id_v1(",
        "ground_action_id_v1(",
        "destination_for_descriptor_v1(",
        "row_bound_other_destination_id_v1(",
        "_row_behavior_signature(",
        "_all_mapping_keys(",
    ):
        assert forbidden_call not in verifier_source


def test_registration_disjoint_rank_cap_six_replay_core_is_positive(
    cold_bundle: closure.V072ColdH2ClosureBundleV1,
) -> None:
    source, claimed = (
        independent
        .build_registration_disjoint_cold_h2_replay_fixture_v1(
            closure_bundle=cold_bundle,
            topology_id=TOPOLOGY_ID,
            vertex_count=4,
            edges=K4_EDGES,
        )
    )
    result = (
        independent
        .verify_registration_disjoint_cold_h2_replay_core_v1(
            source=source,
            claimed=claimed,
        )
    )
    assert result.model_pair_id == claimed.model_pair_id
    assert result.physical_row_count == len(cold_bundle.all_rows)
    assert result.production_attestation_minted is False
    assert result.registered_target_accesses == 0
    assert claimed.direct_model.rank_cap == 6
    assert claimed.quotient_model.rank_cap == 6
    assert claimed.direct_model.rows == claimed.quotient_model.rows
    assert (
        models.REGISTERED_TARGET_MODEL_INDEPENDENT_REPLAY_STATUS
        == "SEPARATE_IDENTITY_BOUND_ATTESTATION_REQUIRED"
    )


def test_registration_disjoint_replay_rejects_projection_and_pair_attacks(
    cold_bundle: closure.V072ColdH2ClosureBundleV1,
) -> None:
    source, claimed = (
        independent
        .build_registration_disjoint_cold_h2_replay_fixture_v1(
            closure_bundle=cold_bundle,
            topology_id=TOPOLOGY_ID,
            vertex_count=4,
            edges=K4_EDGES,
        )
    )
    first = source.row_projections[0]
    attacked_source = replace(
        source,
        row_projections=(
            replace(first, projection_id=_id("forged-registered-projection")),
            *source.row_projections[1:],
        ),
    )
    with pytest.raises(
        independent.V072ColdH2ModelIndependentVerificationFailure
    ):
        independent.verify_registration_disjoint_cold_h2_replay_core_v1(
            source=attacked_source,
            claimed=claimed,
        )
    attacked_claim = replace(
        claimed,
        direct_model=replace(
            claimed.direct_model,
            model_id=_id("forged-registered-direct-model"),
        ),
    )
    with pytest.raises(
        independent.V072ColdH2ModelIndependentVerificationFailure,
        match="differs",
    ):
        independent.verify_registration_disjoint_cold_h2_replay_core_v1(
            source=source,
            claimed=attacked_claim,
        )


def test_registered_production_wrapper_is_preanchor_fail_closed() -> None:
    class _ExplosiveTarget:
        touched = False

        @property
        def anchor_id(self) -> str:
            self.touched = True
            raise AssertionError("target artifact was touched before anchor")

    target = _ExplosiveTarget()
    with pytest.raises(
        independent.V072ColdH2ModelIndependentVerificationFailure,
        match="exact anchor",
    ):
        independent.verify_registered_cold_h2_model_pair_independently_v1(
            object(),
            object(),
            target,
        )
    assert target.touched is False


def test_registered_replay_attestation_is_private_mint_only() -> None:
    with pytest.raises(
        independent.V072ColdH2ModelIndependentVerificationFailure,
        match="privately minted",
    ):
        independent.RegisteredColdH2ModelIndependentReplayAttestationV1(
            object(),
            _id("chain"),
            _id("anchor"),
            _id("anchor-attestation"),
            _id("final"),
            _id("context"),
            _id("closure"),
            _id("pair"),
            1,
            1,
            independent.RegisteredColdH2ModelIndependentReplayWorkV1(),
        )
