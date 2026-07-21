from __future__ import annotations

import ast
from dataclasses import replace
from fractions import Fraction
import hashlib
import inspect

import pytest

import acfqp.observation_partial_rapm_v1 as partial_module
from acfqp.domains.matching_buffer import (
    LMBKernel,
    LMBState,
    LMBStatus,
)
from acfqp.observation_partial_rapm_v1 import (
    AmbiguityRowStatus,
    CanonicalGroundActionV1,
    CanonicalStateObservationV1,
    CoordinateAncestryRefV1,
    CoordinateContext,
    CoordinateOperation,
    DeterministicObservationProfileV1,
    DeterministicTransitionObservationV1,
    EvidenceClass,
    EvidenceLane,
    EvidenceLedgerV1,
    FrozenCoordinateExpressionV1,
    FrozenCoordinateProposalV1,
    ObservationAuthorityEventBindingV1,
    ObservationCoverageV1,
    ObservationLogManifestV1,
    ObservationPartialRAPMInvariantViolation,
    ObservedSuccessorRefV1,
    PartialGroundRowV1,
    PlanningKind,
    PreregisteredAcquisitionManifestV1,
    PreregisteredObservationAuthorityV1,
    RewardFeatureCapV1,
    SuccessorKind,
    TrustedCompleteActionCatalogueV1,
    build_observation_partial_rapm_v1,
    verify_observation_partial_rapm_v1,
)


def _hash(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _planning_kind(status: LMBStatus) -> PlanningKind:
    return {
        LMBStatus.ACTIVE: PlanningKind.ACTIVE,
        LMBStatus.SUCCESS: PlanningKind.SUCCESS,
        LMBStatus.FAILURE: PlanningKind.FAILURE,
    }[status]


def _state_observation(state: LMBState) -> CanonicalStateObservationV1:
    return CanonicalStateObservationV1(
        state_key=(
            f"removed={state.removed_mask};buffer={state.buffer};"
            f"status={state.status.value}"
        ),
        removed_mask=state.removed_mask,
        buffer_counts=state.buffer,
        status=state.status.value,
        planning_kind=_planning_kind(state.status),
    )


def _authority_for(
    log: ObservationLogManifestV1,
    acquisition: PreregisteredAcquisitionManifestV1,
    profile: DeterministicObservationProfileV1,
) -> PreregisteredObservationAuthorityV1:
    bindings = tuple(
        sorted(
            (
                ObservationAuthorityEventBindingV1(
                    item.event_receipt_id,
                    item.observation_id,
                    item.ground_row_id,
                    item.evidence_class,
                    item.evidence_lane,
                )
                for item in log.observations
            ),
            key=lambda item: item.binding_id,
        )
    )
    return PreregisteredObservationAuthorityV1(
        acquisition,
        log.structural_id,
        log.environment_instance_id,
        log.semantics_profile_id,
        profile.trusted_observer_id,
        log.log_id,
        log.evidence_ledger.ledger_id,
        tuple(item.state_id for item in log.states),
        tuple(sorted(item.catalogue_id for item in log.action_catalogues)),
        bindings,
    )


def _resigned_input_graph(
    contract,
    *,
    action_catalogues=None,
    observations=None,
    evidence_ledger=None,
):
    catalogues = action_catalogues or contract["log"].action_catalogues
    events = observations or contract["log"].observations
    ledger = evidence_ledger or contract["log"].evidence_ledger
    acquisition = PreregisteredAcquisitionManifestV1(
        contract["log"].structural_id,
        contract["log"].environment_instance_id,
        contract["profile"].profile_id,
        contract["profile"].trusted_observer_id,
        contract["acquisition"].acquisition_protocol_id,
        tuple(item.state_id for item in contract["log"].states),
        tuple(
            sorted(
                action.ground_row_id
                for catalogue in catalogues
                for action in catalogue.actions
            )
        ),
        tuple(sorted(item.ground_row_id for item in events)),
        tuple(sorted(item.event_receipt_id for item in events)),
    )
    log = ObservationLogManifestV1(
        contract["log"].structural_id,
        contract["log"].environment_instance_id,
        contract["profile"].profile_id,
        acquisition.manifest_id,
        contract["log"].states,
        catalogues,
        events,
        ledger,
    )
    return acquisition, log, _authority_for(log, acquisition, contract["profile"])


@pytest.fixture(scope="module")
def observation_contract():
    # Frozen literal structural-exploration acquisition data. Selection does
    # not start from a QuerySpec/initial-state closure and never calls step.
    initial = LMBState(7, (2, 1), LMBStatus.ACTIVE)
    failure_15 = LMBState(15, (2, 2), LMBStatus.FAILURE)
    failure_23 = LMBState(23, (2, 2), LMBStatus.FAILURE)
    active_39 = LMBState(39, (0, 1), LMBStatus.ACTIVE)
    active_47 = LMBState(47, (0, 2), LMBStatus.ACTIVE)
    active_55 = LMBState(55, (0, 2), LMBStatus.ACTIVE)
    success_63 = LMBState(63, (0, 0), LMBStatus.SUCCESS)
    target_states = tuple(
        sorted(
            (
                initial,
                failure_15,
                failure_23,
                active_39,
                active_47,
                active_55,
                success_63,
            )
        )
    )
    extra = LMBState(3, (1, 1), LMBStatus.ACTIVE)
    fixed_action_tiles = {
        initial: (3, 4, 5),
        active_39: (3, 4),
        active_47: (4,),
        active_55: (3,),
        extra: (2, 3, 4, 5),
    }
    tile_types = (0, 1, 0, 1, 1, 0)
    fixed_transitions = (
        (initial, 3, failure_15, (), True, True),
        (initial, 4, failure_23, (), True, True),
        (initial, 5, active_39, (("match", Fraction(1)),), False, False),
        (active_39, 3, active_47, (), False, False),
        (active_39, 4, active_55, (), False, False),
        (
            active_47, 4, success_63,
            (("match", Fraction(1)), ("terminal_clear", Fraction(2))),
            False, True,
        ),
        (
            active_55, 3, success_63,
            (("match", Fraction(1)), ("terminal_clear", Fraction(2))),
            False, True,
        ),
    )

    structural_id = _hash("lmb-seed0-six-tile-structural-v1")
    observer_id = _hash("trusted-lmb-observer-v1")
    environment_id = _hash("lmb-seed0-observation-environment-v1")
    profile = DeterministicObservationProfileV1(
        structural_id,
        observer_id,
        (
            RewardFeatureCapV1("match", Fraction(0), Fraction(1)),
            RewardFeatureCapV1("terminal_clear", Fraction(0), Fraction(2)),
        ),
        horizon_cap=6,
    )
    proposal = FrozenCoordinateProposalV1(
        (
            FrozenCoordinateExpressionV1(
                CoordinateContext.STATE,
                CoordinateOperation.LEGAL_ACTION_COUNT,
            ),
        ),
        (
            FrozenCoordinateExpressionV1(
                CoordinateContext.STATE_ACTION,
                CoordinateOperation.COMPLETES_MATCH,
            ),
        ),
    )

    ground_states = tuple(sorted((*target_states, extra)))
    observed_by_ground = {state: _state_observation(state) for state in ground_states}
    states = tuple(sorted(observed_by_ground.values(), key=lambda item: item.state_id))
    catalogues: list[TrustedCompleteActionCatalogueV1] = []
    actions_by_ground: dict[LMBState, tuple[CanonicalGroundActionV1, ...]] = {}
    for ground_state in ground_states:
        state = observed_by_ground[ground_state]
        action_tiles = fixed_action_tiles.get(ground_state, ())
        actions = tuple(
            sorted(
                (
                    CanonicalGroundActionV1(
                        state.state_id,
                        f"tile={tile}",
                        tile_types[tile],
                    )
                    for tile in action_tiles
                ),
                key=lambda item: item.action_id,
            )
        )
        actions_by_ground[ground_state] = actions
        catalogues.append(
            TrustedCompleteActionCatalogueV1(
                state.state_id,
                actions,
                observer_id,
            )
        )
    catalogues_tuple = tuple(sorted(catalogues, key=lambda item: item.state_id))

    transition_inputs: list[
        tuple[
            str,
            str,
            ObservedSuccessorRefV1,
            tuple[tuple[str, Fraction], ...],
            bool,
            bool,
        ]
    ] = []
    for source, tile, successor_state, rewards, failure, terminal in fixed_transitions:
        action_observation = next(
            item
            for item in actions_by_ground[source]
            if item.action_key == f"tile={tile}"
        )
        transition_inputs.append(
            (
                observed_by_ground[source].state_id,
                action_observation.action_id,
                ObservedSuccessorRefV1(
                    SuccessorKind.REGISTERED_STATE,
                    observed_by_ground[successor_state].state_id,
                ),
                rewards,
                failure,
                terminal,
            )
        )
    transition_inputs.sort(key=lambda item: (item[0], item[1]))
    observations = tuple(
        DeterministicTransitionObservationV1(
            sequence,
            state_id,
            action_id,
            successor,
            rewards,
            failure,
            terminal,
            _hash(f"v0-042-preregistered-offline-receipt-{sequence}"),
            EvidenceClass.OFFLINE_LOGGED_OBSERVATION,
            EvidenceLane.OFFLINE_SOURCE,
            observer_id,
        )
        for sequence, (
            state_id,
            action_id,
            successor,
            rewards,
            failure,
            terminal,
        ) in enumerate(transition_inputs, start=1)
    )
    assert len(observations) == 7
    ledger = EvidenceLedgerV1.complete(
        {
            (
                EvidenceLane.OFFLINE_SOURCE,
                EvidenceClass.OFFLINE_LOGGED_OBSERVATION,
            ): len(observations)
        }
    )
    registered_row_ids = tuple(
        sorted(
            action.ground_row_id
            for catalogue in catalogues_tuple
            for action in catalogue.actions
        )
    )
    acquisition = PreregisteredAcquisitionManifestV1(
        structural_id,
        environment_id,
        profile.profile_id,
        observer_id,
        _hash("v0-042-preregistered-offline-acquisition-protocol-v1"),
        tuple(item.state_id for item in states),
        registered_row_ids,
        tuple(sorted(item.ground_row_id for item in observations)),
        tuple(sorted(item.event_receipt_id for item in observations)),
    )
    log = ObservationLogManifestV1(
        structural_id,
        environment_id,
        profile.profile_id,
        acquisition.manifest_id,
        states,
        catalogues_tuple,
        observations,
        ledger,
    )
    authority = _authority_for(log, acquisition, profile)
    result = build_observation_partial_rapm_v1(log, proposal, profile, authority)
    return {
        "initial": initial,
        "target_states": target_states,
        "extra": extra,
        "observed_by_ground": observed_by_ground,
        "profile": profile,
        "proposal": proposal,
        "acquisition": acquisition,
        "authority": authority,
        "log": log,
        "result": result,
    }


def test_seed0_log_builds_genuinely_partial_query_neutral_rapm(
    observation_contract,
) -> None:
    contract = observation_contract
    result = contract["result"]
    model = result.model

    assert result.observed_ground_row_count == 7
    assert result.missing_ground_row_count == 4
    assert len(model.coverage.registered_ground_row_ids) == 11
    assert model.coverage.transition_closure_claimed is False
    assert model.query_neutral is True
    assert model.exact_quotient_claimed is False
    assert model.plan_certificate_claimed is False
    assert model.infeasibility_claimed is False
    assert result.exact_kernel_queries_during_construction == 0
    assert result.generative_oracle_samples_during_construction == 0
    assert result.synthetic_model_rollouts_used_as_evidence == 0
    assert result.construction_query_inputs_used == 0
    assert result.acquisition_query_inputs_used == 0
    assert contract["acquisition"].acquisition_query_inputs_used == 0
    assert contract["acquisition"].allowlist_registered_before_query is True
    assert model.observation_authority_id == contract["authority"].authority_id
    assert model.acquisition_manifest_id == contract["acquisition"].manifest_id

    observed = tuple(
        row
        for row in model.ground_rows
        if row.status is AmbiguityRowStatus.OBSERVED_SINGLETON
    )
    missing = tuple(
        row
        for row in model.ground_rows
        if row.status is AmbiguityRowStatus.MISSING_VACUOUS
    )
    assert len(observed) == 7
    assert len(missing) == 4
    assert all(row.ambiguity.is_singleton for row in observed)
    assert all(row.ambiguity.unknown_mass == 0 for row in observed)
    for row in missing:
        assert row.ambiguity.unknown_mass == 1
        assert model.external_boundary_id in (
            row.ambiguity.unknown_successor_destination_ids
        )
        assert row.ambiguity.failure_interval == partial_module.ExactIntervalV1(
            Fraction(0), Fraction(1)
        )
        assert row.ambiguity.terminal_interval == partial_module.ExactIntervalV1(
            Fraction(0), Fraction(1)
        )
        assert all(
            interval.interval == partial_module.ExactIntervalV1(
                Fraction(0), Fraction(1)
            )
            for interval in row.ambiguity.successor_intervals
        )

    ledger = contract["log"].evidence_ledger
    assert len(ledger.counters) == 20
    assert ledger.count(
        EvidenceLane.OFFLINE_SOURCE,
        EvidenceClass.OFFLINE_LOGGED_OBSERVATION,
    ) == 7
    assert ledger.count(
        EvidenceLane.OFFLINE_SOURCE,
        EvidenceClass.ENVIRONMENT_INTERACTION,
    ) == 0
    assert ledger.count(
        EvidenceLane.OFFLINE_SOURCE,
        EvidenceClass.GENERATIVE_ORACLE_SAMPLE,
    ) == 0
    assert ledger.count(
        EvidenceLane.OFFLINE_SOURCE,
        EvidenceClass.EXACT_KERNEL_QUERY,
    ) == 0
    assert ledger.count(
        EvidenceLane.OFFLINE_SOURCE,
        EvidenceClass.SYNTHETIC_MODEL_ROLLOUT,
    ) == 0

    first = contract["observed_by_ground"][contract["initial"]].state_id
    second_ground = next(
        state
        for state in contract["target_states"]
        if state.status is LMBStatus.ACTIVE and state != contract["initial"]
    )
    second = contract["observed_by_ground"][second_ground].state_id
    model.validate_registered_support((first,))
    model.validate_registered_support((second,))
    assert build_observation_partial_rapm_v1(
        contract["log"], contract["proposal"], contract["profile"], contract["authority"]
    ).model.model_id == model.model_id
    assert verify_observation_partial_rapm_v1(
        contract["log"],
        contract["proposal"],
        contract["profile"],
        contract["authority"],
        result,
    ) == ()


def test_constructor_and_verifier_are_kernel_blind_even_if_step_is_broken(
    observation_contract, monkeypatch
) -> None:
    contract = observation_contract

    def forbidden_step(*_args, **_kwargs):
        raise AssertionError("LMB kernel transition API must not be called")

    monkeypatch.setattr(LMBKernel, "step", forbidden_step)
    monkeypatch.setattr(LMBKernel, "actions", forbidden_step)
    rebuilt = build_observation_partial_rapm_v1(
        contract["log"], contract["proposal"], contract["profile"], contract["authority"]
    )
    assert rebuilt.model.model_id == contract["result"].model.model_id
    assert verify_observation_partial_rapm_v1(
        contract["log"],
        contract["proposal"],
        contract["profile"],
        contract["authority"],
        rebuilt,
    ) == ()

    imports = {
        node.module
        for node in ast.walk(ast.parse(inspect.getsource(partial_module)))
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    assert not any(module.startswith("acfqp.domains") for module in imports)
    assert "acfqp.core" not in imports
    assert "acfqp.build_coverage" not in imports
    assert not any(module.startswith("acfqp.planning") for module in imports)


def test_construction_api_has_no_query_or_exact_kernel_channel(
    observation_contract,
) -> None:
    signature = inspect.signature(build_observation_partial_rapm_v1)
    assert tuple(signature.parameters) == (
        "observation_log",
        "coordinate_proposal",
        "semantics_profile",
        "observation_authority",
    )
    verifier_signature = inspect.signature(verify_observation_partial_rapm_v1)
    assert tuple(verifier_signature.parameters) == (
        "observation_log",
        "coordinate_proposal",
        "semantics_profile",
        "observation_authority",
        "claimed_result",
    )
    with pytest.raises(TypeError):
        build_observation_partial_rapm_v1(
            observation_contract["log"],
            observation_contract["proposal"],
            observation_contract["profile"],
            observation_contract["authority"],
            query={"reward": "leak"},  # type: ignore[call-arg]
        )
    # A target exact certificate can be given a benign role name.  V0-042
    # does not infer authority from that string; it accepts no ancestry.
    renamed_target_exact = CoordinateAncestryRefV1(
        "generated_coordinate_certificate_v1",
        _hash("target-exact-certificate"),
    )
    with pytest.raises(
        ObservationPartialRAPMInvariantViolation,
        match="must be ancestry-free",
    ):
        FrozenCoordinateProposalV1(
            observation_contract["proposal"].state_expressions,
            observation_contract["proposal"].action_expressions,
            (renamed_target_exact,),
        )


def test_conflicting_deterministic_duplicate_is_rejected(
    observation_contract,
) -> None:
    contract = observation_contract
    first = contract["log"].observations[0]
    changed_rewards = (
        ()
        if first.reward_features
        else (("match", Fraction(1)),)
    )
    conflict = replace(
        first,
        sequence_number=len(contract["log"].observations) + 1,
        reward_features=changed_rewards,
        event_receipt_id=_hash("conflicting-offline-event-receipt"),
    )
    ledger = EvidenceLedgerV1.complete(
        {
            (
                EvidenceLane.OFFLINE_SOURCE,
                EvidenceClass.OFFLINE_LOGGED_OBSERVATION,
            ): 8
        }
    )
    with pytest.raises(
        ObservationPartialRAPMInvariantViolation,
        match="deterministic duplicate observations conflict",
    ):
        ObservationLogManifestV1(
            contract["log"].structural_id,
            contract["log"].environment_instance_id,
            contract["log"].semantics_profile_id,
            contract["log"].acquisition_manifest_id,
            contract["log"].states,
            contract["log"].action_catalogues,
            (*contract["log"].observations, conflict),
            ledger,
        )


def test_synthetic_or_exact_kernel_event_cannot_become_observed_row(
    observation_contract,
) -> None:
    first = observation_contract["log"].observations[0]
    with pytest.raises(
        ObservationPartialRAPMInvariantViolation,
        match="synthetic model rollout",
    ):
        replace(first, evidence_class=EvidenceClass.SYNTHETIC_MODEL_ROLLOUT)
    with pytest.raises(
        ObservationPartialRAPMInvariantViolation,
        match="exact-kernel evidence is forbidden",
    ):
        replace(first, evidence_class=EvidenceClass.EXACT_KERNEL_QUERY)


def test_deleted_observation_and_ledger_attack_fail_independent_rebuild(
    observation_contract,
) -> None:
    contract = observation_contract
    shortened = contract["log"].observations[:-1]
    ledger = EvidenceLedgerV1.complete(
        {
            (
                EvidenceLane.OFFLINE_SOURCE,
                EvidenceClass.OFFLINE_LOGGED_OBSERVATION,
            ): 6
        }
    )
    shortened_log = ObservationLogManifestV1(
        contract["log"].structural_id,
        contract["log"].environment_instance_id,
        contract["log"].semantics_profile_id,
        contract["log"].acquisition_manifest_id,
        contract["log"].states,
        contract["log"].action_catalogues,
        shortened,
        ledger,
    )
    with pytest.raises(
        ObservationPartialRAPMInvariantViolation,
        match="differs from its preregistered authority binding",
    ):
        verify_observation_partial_rapm_v1(
            shortened_log,
            contract["proposal"],
            contract["profile"],
            contract["authority"],
            contract["result"],
        )

    with pytest.raises(
        ObservationPartialRAPMInvariantViolation,
        match="evidence ledger does not exactly reconcile",
    ):
        ObservationLogManifestV1(
            contract["log"].structural_id,
            contract["log"].environment_instance_id,
            contract["log"].semantics_profile_id,
            contract["log"].acquisition_manifest_id,
            contract["log"].states,
            contract["log"].action_catalogues,
            shortened,
            contract["log"].evidence_ledger,
        )


def test_coherently_resigned_unknown_mass_shrink_is_rejected(
    observation_contract,
) -> None:
    contract = observation_contract
    model = contract["result"].model
    missing = next(
        row
        for row in model.ground_rows
        if row.status is AmbiguityRowStatus.MISSING_VACUOUS
    )
    observed = next(
        row
        for row in model.ground_rows
        if row.status is AmbiguityRowStatus.OBSERVED_SINGLETON
    )
    # The attacker fabricates a singleton outcome, updates coverage and lets all
    # content IDs re-sign themselves.  It is locally typed, but it has no event
    # in the authoritative input log.
    fabricated = PartialGroundRowV1(
        missing.ground_row_id,
        missing.state_id,
        missing.ground_action_id,
        AmbiguityRowStatus.OBSERVED_SINGLETON,
        (_hash("fabricated-observation"),),
        observed.ambiguity,
    )
    ground_rows = tuple(
        sorted(
            (
                fabricated if row.ground_row_id == missing.ground_row_id else row
                for row in model.ground_rows
            ),
            key=lambda item: item.ground_row_id,
        )
    )
    observed_ids = tuple(
        row.ground_row_id
        for row in ground_rows
        if row.status is AmbiguityRowStatus.OBSERVED_SINGLETON
    )
    missing_ids = tuple(
        row.ground_row_id
        for row in ground_rows
        if row.status is AmbiguityRowStatus.MISSING_VACUOUS
    )
    coverage = ObservationCoverageV1(
        model.coverage.registered_state_ids,
        model.coverage.registered_ground_row_ids,
        observed_ids,
        missing_ids,
        model.external_boundary_id,
    )
    with pytest.raises(
        ObservationPartialRAPMInvariantViolation,
        match="semantic realization evidence partition differs",
    ):
        replace(model, coverage=coverage, ground_rows=ground_rows)


def test_semantic_realization_only_forgery_fails_model_boundary(
    observation_contract,
) -> None:
    model = observation_contract["result"].model
    victim = next(
        item for item in model.semantic_realizations
        if item.missing_ground_row_ids
    )
    point_ambiguity = next(
        row.ambiguity for row in model.ground_rows
        if row.status is AmbiguityRowStatus.OBSERVED_SINGLETON
    )
    forged = replace(
        victim,
        observed_ground_row_ids=victim.support_ground_row_ids,
        missing_ground_row_ids=(),
        ambiguity=point_ambiguity,
    )
    forged_realizations = tuple(
        sorted(
            (
                forged if item is victim else item
                for item in model.semantic_realizations
            ),
            key=lambda item: (item.state_id, item.semantic_action_id),
        )
    )
    with pytest.raises(
        ObservationPartialRAPMInvariantViolation,
        match="semantic realization evidence partition differs",
    ):
        replace(model, semantic_realizations=forged_realizations)


def test_nonuniform_concretizer_is_rejected(observation_contract) -> None:
    concretizer = next(
        item for item in observation_contract["result"].model.concretizer_rows
        if len(item.support) > 1
    )
    denominator = sum(range(1, len(concretizer.support) + 1))
    nonuniform = tuple(
        (action_id, Fraction(index, denominator))
        for index, (action_id, _) in enumerate(concretizer.support, start=1)
    )
    with pytest.raises(
        ObservationPartialRAPMInvariantViolation,
        match="concretizer must be uniform over distinct ground actions",
    ):
        replace(concretizer, support=nonuniform)


def test_duplicate_semantic_names_are_rejected(observation_contract) -> None:
    contract = observation_contract
    profile = contract["profile"]
    model = contract["result"].model
    cap = profile.reward_feature_caps[0]
    duplicate_cap = replace(cap, upper=cap.upper + 1)
    duplicate_caps = tuple(sorted((*profile.reward_feature_caps, duplicate_cap)))
    with pytest.raises(
        ObservationPartialRAPMInvariantViolation,
        match="reward feature cap names must be unique",
    ):
        replace(profile, reward_feature_caps=duplicate_caps)
    with pytest.raises(
        ObservationPartialRAPMInvariantViolation,
        match="partial RAPM reward feature cap names must be unique",
    ):
        replace(model, reward_feature_caps=duplicate_caps)

    reward_ambiguity = next(
        row.ambiguity for row in model.ground_rows
        if row.ambiguity.known_reward_features
    )
    reward_name, reward_value = reward_ambiguity.known_reward_features[0]
    duplicate_rewards = tuple(
        sorted(
            (*reward_ambiguity.known_reward_features, (reward_name, reward_value + 1))
        )
    )
    with pytest.raises(
        ObservationPartialRAPMInvariantViolation,
        match="known reward feature names must be unique",
    ):
        replace(reward_ambiguity, known_reward_features=duplicate_rewards)

    successor_ambiguity = next(
        row.ambiguity for row in model.ground_rows
        if row.ambiguity.known_successor_masses
    )
    destination, mass = successor_ambiguity.known_successor_masses[0]
    alternate_mass = Fraction(1, 2) if mass != Fraction(1, 2) else Fraction(1, 3)
    duplicate_successors = tuple(
        sorted((*successor_ambiguity.known_successor_masses, (destination, alternate_mass)))
    )
    with pytest.raises(
        ObservationPartialRAPMInvariantViolation,
        match="known successor destination names must be unique",
    ):
        replace(successor_ambiguity, known_successor_masses=duplicate_successors)

    reward_interval = reward_ambiguity.reward_intervals[0]
    duplicate_reward_interval = partial_module.NamedIntervalV1(
        reward_interval.name,
        partial_module.ExactIntervalV1(
            reward_interval.interval.lower,
            reward_interval.interval.upper + 1,
        ),
    )
    with pytest.raises(
        ObservationPartialRAPMInvariantViolation,
        match="reward interval names must be unique",
    ):
        replace(
            reward_ambiguity,
            reward_intervals=tuple(
                sorted((*reward_ambiguity.reward_intervals, duplicate_reward_interval))
            ),
        )

    successor_interval = successor_ambiguity.successor_intervals[0]
    alternate_interval = partial_module.ExactIntervalV1(Fraction(0), Fraction(1))
    if alternate_interval == successor_interval.interval:
        alternate_interval = partial_module.ExactIntervalV1(Fraction(0), Fraction(1, 2))
    duplicate_successor_interval = partial_module.DestinationIntervalV1(
        successor_interval.destination_id,
        alternate_interval,
    )
    with pytest.raises(
        ObservationPartialRAPMInvariantViolation,
        match="successor interval destination names must be unique",
    ):
        replace(
            successor_ambiguity,
            successor_intervals=tuple(
                sorted((*successor_ambiguity.successor_intervals, duplicate_successor_interval))
            ),
        )


def test_duck_types_and_untrusted_complete_catalogue_are_rejected(
    observation_contract,
) -> None:
    contract = observation_contract
    with pytest.raises(
        ObservationPartialRAPMInvariantViolation,
        match="verifier rejects duck build results",
    ):
        verify_observation_partial_rapm_v1(
            contract["log"],
            contract["proposal"],
            contract["profile"],
            contract["authority"],
            {"result_id": contract["result"].result_id},  # type: ignore[arg-type]
        )
    catalogue = next(
        item for item in contract["log"].action_catalogues if item.actions
    )
    with pytest.raises(
        ObservationPartialRAPMInvariantViolation,
        match="frozen complete-catalogue authority",
    ):
        replace(catalogue, complete=False)


def test_partial_model_rejects_out_of_catalogue_support(
    observation_contract,
) -> None:
    with pytest.raises(
        ObservationPartialRAPMInvariantViolation,
        match="rebuild or fallback required",
    ):
        observation_contract["result"].model.validate_registered_support(
            (_hash("unknown-query-state"),)
        )


def test_nested_ducks_are_rejected_before_hash_property_or_iteration_side_effects(
    observation_contract,
) -> None:
    contract = observation_contract
    touched: list[str] = []

    class MaliciousNestedDuck:
        def __hash__(self):
            touched.append("hash")
            return 1

        @property
        def expression_id(self):
            touched.append("expression_id")
            return _hash("duck-expression")

        @property
        def context(self):
            touched.append("context")
            return CoordinateContext.STATE

        def __iter__(self):
            touched.append("iter")
            return iter(("match", Fraction(0)))

        def to_document(self):
            touched.append("to_document")
            return {}

    duck = MaliciousNestedDuck()
    with pytest.raises(
        ObservationPartialRAPMInvariantViolation,
        match="duck state expressions before canonical access",
    ):
        FrozenCoordinateProposalV1(
            (duck,),  # type: ignore[arg-type]
            contract["proposal"].action_expressions,
        )
    assert touched == []

    with pytest.raises(
        ObservationPartialRAPMInvariantViolation,
        match="duck reward caps before canonical access",
    ):
        replace(contract["profile"], reward_feature_caps=(duck,))  # type: ignore[arg-type]
    assert touched == []

    with pytest.raises(
        ObservationPartialRAPMInvariantViolation,
        match="duck counters before canonical access",
    ):
        EvidenceLedgerV1((duck,))  # type: ignore[arg-type]
    assert touched == []

    with pytest.raises(
        ObservationPartialRAPMInvariantViolation,
        match="nested duck IDs before hashing",
    ):
        replace(contract["acquisition"], registered_state_ids=(duck,))  # type: ignore[arg-type]
    assert touched == []

    with pytest.raises(
        ObservationPartialRAPMInvariantViolation,
        match="duck event bindings before canonical access",
    ):
        replace(contract["authority"], event_bindings=(duck,))  # type: ignore[arg-type]
    assert touched == []

    ambiguity = contract["result"].model.ground_rows[0].ambiguity
    with pytest.raises(
        ObservationPartialRAPMInvariantViolation,
        match="known reward features reject nested duck pairs",
    ):
        replace(ambiguity, known_reward_features=(duck,))  # type: ignore[arg-type]
    assert touched == []

    concretizer = contract["result"].model.concretizer_rows[0]
    with pytest.raises(
        ObservationPartialRAPMInvariantViolation,
        match="concretizer support rejects nested duck pairs",
    ):
        replace(concretizer, support=(duck,))  # type: ignore[arg-type]
    assert touched == []

    with pytest.raises(
        ObservationPartialRAPMInvariantViolation,
        match="partial RAPM rejects duck reward caps before canonical access",
    ):
        replace(contract["result"].model, reward_feature_caps=(duck,))  # type: ignore[arg-type]
    assert touched == []


def test_literal_acquisition_has_no_initial_closure_or_transition_call() -> None:
    source = inspect.getsource(observation_contract.__wrapped__)
    assert "_closure" not in source
    assert "kernel.step" not in source
    assert "kernel.actions" not in source


def test_coherent_catalogue_deletion_cannot_register_a_new_authority(
    observation_contract,
) -> None:
    contract = observation_contract
    extra_state_id = contract["observed_by_ground"][contract["extra"]].state_id
    target = next(
        item for item in contract["log"].action_catalogues
        if item.state_id == extra_state_id
    )
    deleted = replace(target, actions=target.actions[1:])
    catalogues = tuple(
        sorted(
            (deleted if item.state_id == target.state_id else item
             for item in contract["log"].action_catalogues),
            key=lambda item: item.state_id,
        )
    )
    _, resigned_log, resigned_authority = _resigned_input_graph(
        contract, action_catalogues=catalogues
    )
    assert resigned_authority.authority_id != contract["authority"].authority_id
    with pytest.raises(
        ObservationPartialRAPMInvariantViolation,
        match="absent from the frozen preregistered allowlist",
    ):
        build_observation_partial_rapm_v1(
            resigned_log,
            contract["proposal"],
            contract["profile"],
            resigned_authority,
        )
    with pytest.raises(
        ObservationPartialRAPMInvariantViolation,
        match="differs from its preregistered authority binding",
    ):
        build_observation_partial_rapm_v1(
            resigned_log,
            contract["proposal"],
            contract["profile"],
            contract["authority"],
        )


def test_fabricated_observation_and_resigned_inputs_remain_unregistered(
    observation_contract,
) -> None:
    contract = observation_contract
    extra_state_id = contract["observed_by_ground"][contract["extra"]].state_id
    catalogue = next(
        item for item in contract["log"].action_catalogues
        if item.state_id == extra_state_id
    )
    fabricated = DeterministicTransitionObservationV1(
        8,
        extra_state_id,
        catalogue.actions[0].action_id,
        ObservedSuccessorRefV1(
            SuccessorKind.EXTERNAL_STATE,
            _hash("fabricated-unregistered-active-successor"),
        ),
        (),
        False,
        False,
        _hash("fabricated-offline-event-receipt"),
        EvidenceClass.OFFLINE_LOGGED_OBSERVATION,
        EvidenceLane.OFFLINE_SOURCE,
        contract["profile"].trusted_observer_id,
    )
    observations = (*contract["log"].observations, fabricated)
    ledger = EvidenceLedgerV1.complete(
        {
            (
                EvidenceLane.OFFLINE_SOURCE,
                EvidenceClass.OFFLINE_LOGGED_OBSERVATION,
            ): 8
        }
    )
    _, resigned_log, resigned_authority = _resigned_input_graph(
        contract,
        observations=observations,
        evidence_ledger=ledger,
    )
    with pytest.raises(
        ObservationPartialRAPMInvariantViolation,
        match="absent from the frozen preregistered allowlist",
    ):
        build_observation_partial_rapm_v1(
            resigned_log,
            contract["proposal"],
            contract["profile"],
            resigned_authority,
        )


def test_external_successor_semantics_and_event_replay_relabel_fail_closed(
    observation_contract,
) -> None:
    contract = observation_contract
    first = contract["log"].observations[0]
    registered_alias = replace(
        first,
        successor=ObservedSuccessorRefV1(
            SuccessorKind.EXTERNAL_STATE,
            contract["log"].states[0].state_id,
        ),
        failure=False,
        terminal=False,
    )
    with pytest.raises(
        ObservationPartialRAPMInvariantViolation,
        match="external successor reference aliases a registered state",
    ):
        replace(
            contract["log"],
            observations=(registered_alias, *contract["log"].observations[1:]),
        )

    terminal_external = replace(
        first,
        successor=ObservedSuccessorRefV1(
            SuccessorKind.EXTERNAL_STATE,
            _hash("external-terminal-attack"),
        ),
        failure=True,
        terminal=True,
    )
    with pytest.raises(
        ObservationPartialRAPMInvariantViolation,
        match="external successor is active, nonterminal and nonfailure",
    ):
        replace(
            contract["log"],
            observations=(terminal_external, *contract["log"].observations[1:]),
        )

    replay = replace(
        first,
        sequence_number=8,
        event_receipt_id=_hash("replayed-ground-row-new-receipt"),
    )
    replay_ledger = EvidenceLedgerV1.complete(
        {
            (
                EvidenceLane.OFFLINE_SOURCE,
                EvidenceClass.OFFLINE_LOGGED_OBSERVATION,
            ): 8
        }
    )
    with pytest.raises(
        ObservationPartialRAPMInvariantViolation,
        match="replay of one ground row is forbidden",
    ):
        replace(
            contract["log"],
            observations=(*contract["log"].observations, replay),
            evidence_ledger=replay_ledger,
        )
    with pytest.raises(
        ObservationPartialRAPMInvariantViolation,
        match="only preregistered offline-source logged observations",
    ):
        replace(first, evidence_lane=EvidenceLane.ONLINE_TARGET)


def test_joint_simplex_is_machine_visible_coupled_and_horizon_bounded(
    observation_contract,
) -> None:
    model = observation_contract["result"].model
    assert model.semantics_horizon_cap == 6
    with pytest.raises(ObservationPartialRAPMInvariantViolation, match="semantics_horizon_cap"):
        replace(model, semantics_horizon_cap=0)

    missing = next(
        row.ambiguity for row in model.ground_rows
        if row.status is AmbiguityRowStatus.MISSING_VACUOUS
    )
    constraint = missing.joint_simplex_constraint
    assert constraint.known_continuation_mass == 0
    assert constraint.known_terminal_mass == 0
    assert constraint.unknown_atom_mass_sum == 1
    assert constraint.total_probability_mass == 1
    assert constraint.failure_implies_terminal is True
    assert constraint.independent_marginal_box_forbidden is True
    assert constraint.atom_ids == tuple(item.atom_id for item in missing.joint_outcome_atoms)
    continuation_destinations = tuple(
        sorted(
            item.destination_id for item in missing.joint_outcome_atoms
            if item.kind is partial_module.JointOutcomeKind.CONTINUATION
        )
    )
    assert continuation_destinations == missing.unknown_successor_destination_ids
    assert all(not item.failure or item.terminal for item in missing.joint_outcome_atoms)
    with pytest.raises(
        ObservationPartialRAPMInvariantViolation,
        match="joint simplex coupling constraints were relaxed",
    ):
        replace(constraint, independent_marginal_box_forbidden=False)

    observed_continuation = next(
        row.ambiguity for row in model.ground_rows
        if row.ambiguity.known_successor_masses
    )
    with pytest.raises(
        ObservationPartialRAPMInvariantViolation,
        match="known successor lies outside",
    ):
        replace(
            observed_continuation,
            known_successor_masses=((_hash("out-of-scope-successor"), Fraction(1)),),
        )
