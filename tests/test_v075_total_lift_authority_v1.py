from __future__ import annotations

from dataclasses import dataclass, replace
from fractions import Fraction
import hashlib
import inspect
from typing import Callable

import pytest

from acfqp.h2_graph_transition_engine_v1 import (
    H2GraphActionV1,
    H2GraphKernelV1,
    H2GraphStateV1,
)
from acfqp import v075_private_observer_boundary_v1 as observer
from acfqp import v075_public_campaign_authority_v1 as authority
from acfqp import v075_public_graph_semantics_v1 as public
from acfqp import v075_total_lift_authority_v1 as lift
from tests.v075_signature_test_support import (
    make_public_key,
    sign_test_message,
)


def _id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _salt(marker: str) -> bytes:
    return hashlib.sha512(
        ("v075-total-lift-test-salt-" + marker).encode("utf-8")
    ).digest()


def _environment(
    selected_context_index: int,
    selected_law: tuple[tuple[int, Fraction], ...],
) -> tuple[tuple[tuple[int, Fraction], ...], ...]:
    laws = [
        ((1, Fraction(1)),),
        ((1, Fraction(1)),),
        ((1, Fraction(1)),),
    ]
    laws[selected_context_index] = selected_law
    return tuple(laws)


def _namespace(
    *,
    marker: str,
    environment: tuple[tuple[tuple[int, Fraction], ...], ...],
) -> authority.V075PublicTargetTapeNamespaceV1:
    family = authority.freeze_v075_public_family_generation_v1()
    commitment = authority.seal_opaque_environment_commitment_v1(
        family=family,
        secret_salt=_salt(marker),
        secret_laws=environment,
    )
    registry = authority.V075TrustedSignerRegistryV1(
        make_public_key("CAMPAIGN_AUTHORITY"),
        make_public_key("OBSERVER_EVIDENCE"),
    )

    def claim(
        role: authority.V075ExternalAuthorityRoleV1,
        subject: str,
    ) -> authority.V075SignedExternalAuthorityClaimV1:
        message = authority.external_authority_claim_signing_bytes_v1(
            signer_registry=registry,
            role=role,
            external_id=subject,
        )
        return authority.V075SignedExternalAuthorityClaimV1(
            registry,
            role,
            subject,
            sign_test_message(message),
        )

    roles = authority.V075ExternalAuthorityRoleV1
    return authority.derive_public_target_tape_namespace_v1(
        family=family,
        environment_commitment=commitment,
        signer_registry=registry,
        claimed_final_preregistration_registry_id=registry.registry_id,
        remote_main_anchor=claim(
            roles.REMOTE_MAIN_ANCHOR,
            _id("total-lift-anchor-" + marker),
        ),
        final_preregistration=claim(
            roles.FINAL_PREREGISTRATION,
            _id("total-lift-prereg-" + marker),
        ),
        observer_profile=claim(
            roles.OBSERVER_PROFILE,
            _id("total-lift-observer-" + marker),
        ),
    )


class _ConstructionSigner:
    def public_verification_key_v1(
        self,
    ) -> authority.V075RSAPublicVerificationKeyV1:
        return make_public_key("OBSERVER_EVIDENCE")

    def sign_observer_evidence_v1(self, message: bytes) -> str:
        return sign_test_message(
            message,
            key_role="OBSERVER_EVIDENCE",
        )


def _open_observer(
    *,
    namespace: authority.V075PublicTargetTapeNamespaceV1,
    environment: tuple[tuple[tuple[int, Fraction], ...], ...],
    marker: str,
) -> observer.V075PrivateObserverSessionV1:
    fixture = _construction_authority(namespace=namespace, marker=marker)
    return observer.open_construction_private_observer_fixture_v1(
        authority=fixture,
        private_salt=_salt(marker),
        private_environment=environment,
        observer_signer=_ConstructionSigner(),
        session_external_id=_id("total-lift-session-" + marker),
    )


def _construction_authority(
    *,
    namespace: authority.V075PublicTargetTapeNamespaceV1,
    marker: str,
) -> observer.V075ConstructionOnlyObserverOpenAuthorityFixtureV1:
    return observer.V075ConstructionOnlyObserverOpenAuthorityFixtureV1(
        namespace,
        _id("total-lift-observer-fixture-" + marker),
    )


def _row_binding(
    catalogue: public.V075LegalActionCatalogueV1,
    action: tuple[int, int, int],
) -> public.V075ObservationRowBindingV1:
    return public.observation_row_binding_v1(
        catalogue.context,
        catalogue,
        action,
    )


def _exact_rows(
    context: authority.V075PublicReplicateContextV1,
    law: tuple[tuple[int, Fraction], ...],
) -> tuple[lift.V075ExactReplayRowV1, ...]:
    kernel = H2GraphKernelV1(
        context.topology,
        context.rank_cap,
        context.horizon,
        law,
    )
    root = public.root_catalogue_v1(context)
    rows: list[lift.V075ExactReplayRowV1] = []
    active_states: dict[str, public.V075SymbolicGraphStateV1] = {}

    def add_row(
        catalogue: public.V075LegalActionCatalogueV1,
        action: tuple[int, int, int],
    ) -> None:
        binding = _row_binding(catalogue, action)
        atoms = tuple(
            lift.V075ExactReplayAtomV1(binding, atom)
            for atom in kernel.exact_atoms(
                catalogue.state.to_kernel_state(),
                H2GraphActionV1(*action),
                remaining_horizon=catalogue.remaining_horizon,
            )
        )
        row = lift.V075ExactReplayRowV1(
            binding,
            tuple(sorted(atoms, key=lambda item: item.atom_id)),
        )
        rows.append(row)
        if catalogue.remaining_horizon == context.horizon:
            for exact_atom in row.atoms:
                if not exact_atom.atom.failure:
                    active_states[exact_atom.next_state_id] = (
                        exact_atom.next_state
                    )

    for action in root.actions:
        add_row(root, action)
    for state_id in sorted(active_states):
        state = active_states[state_id]
        catalogue = public.V075LegalActionCatalogueV1(
            context,
            state,
            1,
            public.legal_action_triples_v1(
                context,
                state.ranks,
                state.failure,
            ),
        )
        for action in catalogue.actions:
            add_row(catalogue, action)
    return tuple(sorted(rows, key=lambda item: item.row_id))


def _stream_for_row(
    *,
    namespace: authority.V075PublicTargetTapeNamespaceV1,
    row_binding: public.V075ObservationRowBindingV1,
    arm: str,
) -> public.V075TransitionStreamIdentityV1:
    epoch = public.derive_shared_support_epoch_v1(
        namespace=namespace,
        row_binding=row_binding,
        epoch_index=0,
        evidence=(),
    )
    chain = public.freeze_shared_support_chain_v1(
        namespace=namespace,
        row_binding=row_binding,
        epochs=(epoch,),
    )
    pairing = public.freeze_five_arm_pairing_authority_v1(
        namespace=namespace,
        row_binding=row_binding,
        support_chain=chain,
    )
    return public.derive_transition_stream_identity_v1(
        pairing_authority=pairing,
        arm=arm,
    )


def _observed_row(
    *,
    occurrence: lift.V075LawFreePlannerOccurrenceV1,
    session: observer.V075PrivateObserverSessionV1,
    catalogue: public.V075LegalActionCatalogueV1,
    action: tuple[int, int, int],
) -> lift.V075ObservedRowBindingV1:
    binding = _row_binding(catalogue, action)
    capability = session.observe_v1(
        _stream_for_row(
            namespace=occurrence.namespace,
            row_binding=binding,
            arm=occurrence.arm,
        )
    )
    return lift.V075ObservedRowBindingV1(
        occurrence,
        binding,
        (capability,),
    )


def _boundary(
    *,
    namespace: authority.V075PublicTargetTapeNamespaceV1,
    context_index: int,
    law: tuple[tuple[int, Fraction], ...],
    marker: str,
) -> tuple[
    lift.V075LawFreePlannerOccurrenceV1,
    lift.V075IndependentExactReplayBoundaryV1,
]:
    context = namespace.family.replicate_contexts[context_index]
    occurrence = lift.V075LawFreePlannerOccurrenceV1(
        namespace,
        context,
        "SOURCE_CONSENSUS_PRIOR",
        0,
    )
    boundary = lift.mint_construction_exact_replay_boundary_v1(
        occurrence=occurrence,
        rows=_exact_rows(context, law),
        construction_fixture_registration_id=_id(
            "total-lift-exact-replay-" + marker
        ),
    )
    return occurrence, boundary


def _rows_by_key(
    boundary: lift.V075IndependentExactReplayBoundaryV1,
) -> dict[
    tuple[str, int, tuple[int, int, int]],
    lift.V075ExactReplayRowV1,
]:
    return {
        (
            row.row_binding.state_id,
            row.row_binding.remaining_horizon,
            row.row_binding.action,
        ): row
        for row in boundary.rows
    }


def _active_catalogues(
    row: lift.V075ExactReplayRowV1,
) -> tuple[public.V075LegalActionCatalogueV1, ...]:
    states = {
        atom.next_state_id: atom.next_state
        for atom in row.atoms
        if not atom.atom.failure
    }
    return tuple(
        public.V075LegalActionCatalogueV1(
            state.context,
            state,
            1,
            public.legal_action_triples_v1(
                state.context,
                state.ranks,
                state.failure,
            ),
        )
        for _state_id, state in sorted(states.items())
    )


def _rank_two_merge_actions(
    catalogue: public.V075LegalActionCatalogueV1,
) -> tuple[tuple[int, int, int], ...]:
    state = catalogue.state
    actions = tuple(
        action
        for action in catalogue.actions
        if state.ranks[action[0]] == 2
        and state.ranks[action[1]] == 2
    )
    assert actions
    return actions


def _resigned_closure(
    *,
    template: observer.V075ObserverJournalClosureV1,
    records: tuple[observer.V075SignedObservationRecordV1, ...],
) -> observer.V075ObserverJournalClosureV1:
    entries: list[observer.V075ObserverJournalEntryV1] = []
    previous: str | None = None
    for index, record in enumerate(records, start=1):
        entry = observer.V075ObserverJournalEntryV1(
            index,
            previous,
            record,
        )
        entries.append(entry)
        previous = entry.entry_id
    frozen = tuple(entries)
    message = observer.observer_journal_closure_signing_bytes_v1(
        session_public_id=template.session_public_id,
        authority_binding=template.authority_binding,
        entries=frozen,
    )
    return observer.V075ObserverJournalClosureV1(
        template.session_public_id,
        template.authority_binding,
        frozen,
        sign_test_message(
            message,
            key_role="OBSERVER_EVIDENCE",
        ),
    )


def _build_binding(
    *,
    occurrence: lift.V075LawFreePlannerOccurrenceV1,
    boundary: lift.V075IndependentExactReplayBoundaryV1,
    session: observer.V075PrivateObserverSessionV1,
    root_actions: tuple[tuple[int, int, int], ...],
    modeled_child_selector: Callable[
        [tuple[int, int, int], tuple[public.V075LegalActionCatalogueV1, ...]],
        tuple[public.V075LegalActionCatalogueV1, ...],
    ],
    child_action_selector: Callable[
        [public.V075LegalActionCatalogueV1],
        tuple[tuple[int, int, int], ...],
    ],
) -> tuple[
    lift.V075LawFreePartialModelBindingV1,
    lift.V075SelectedPolicyBindingV1,
    lift.V075OperationalEnvelopeV1,
]:
    rows = _rows_by_key(boundary)
    root_catalogue = public.root_catalogue_v1(occurrence.context)
    observed_root_rows = tuple(
        _observed_row(
            occurrence=occurrence,
            session=session,
            catalogue=root_catalogue,
            action=action,
        )
        for action in root_actions
    )
    root_semantic = lift.V075ObservedSemanticActionV1(
        occurrence,
        root_catalogue,
        "selected-root-semantic",
        tuple(
            sorted(observed_root_rows, key=lambda item: item.action)
        ),
    )
    root_decision = lift.V075FixedConcretizerDecisionV1(
        root_semantic,
        root_semantic.ground_actions,
        tuple(
            Fraction(1, len(root_semantic.ground_actions))
            for _action in root_semantic.ground_actions
        ),
    )
    supports: list[lift.V075SelectedRootSupportV1] = []
    global_catalogues: dict[
        str,
        public.V075LegalActionCatalogueV1,
    ] = {}
    child_semantics: list[lift.V075ObservedSemanticActionV1] = []
    child_decisions: list[lift.V075FixedConcretizerDecisionV1] = []
    for observed_root in observed_root_rows:
        exact_root = rows[
            (
                root_catalogue.state.state_id,
                root_catalogue.remaining_horizon,
                observed_root.action,
            )
        ]
        selected_children = modeled_child_selector(
            observed_root.action,
            _active_catalogues(exact_root),
        )
        selected_children = tuple(
            sorted(
                selected_children,
                key=lambda item: item.state.state_id,
            )
        )
        supports.append(
            lift.V075SelectedRootSupportV1(
                observed_root,
                selected_children,
            )
        )
        for catalogue in selected_children:
            prior = global_catalogues.setdefault(
                catalogue.state.state_id,
                catalogue,
            )
            assert prior == catalogue
    for state_id in sorted(global_catalogues):
        catalogue = global_catalogues[state_id]
        actions = child_action_selector(catalogue)
        action_rows = tuple(
            _observed_row(
                occurrence=occurrence,
                session=session,
                catalogue=catalogue,
                action=action,
            )
            for action in actions
        )
        semantic = lift.V075ObservedSemanticActionV1(
            occurrence,
            catalogue,
            "selected-child-" + state_id,
            tuple(sorted(action_rows, key=lambda item: item.action)),
        )
        child_semantics.append(semantic)
        child_decisions.append(
            lift.V075FixedConcretizerDecisionV1(
                semantic,
                semantic.ground_actions,
                tuple(
                    Fraction(1, len(semantic.ground_actions))
                    for _action in semantic.ground_actions
                ),
            )
        )
    semantics = tuple(
        sorted(
            (root_semantic, *child_semantics),
            key=lambda item: item.semantic_action_id,
        )
    )
    model = lift.V075LawFreePartialModelBindingV1(
        occurrence,
        root_catalogue,
        semantics,
        tuple(sorted(supports, key=lambda item: item.root_action)),
        tuple(
            global_catalogues[state_id]
            for state_id in sorted(global_catalogues)
        ),
    )
    policy = lift.V075SelectedPolicyBindingV1(
        model,
        lift.V075RouteKindV1.ADAPTIVE_QUOTIENT,
        root_decision,
        tuple(
            sorted(
                child_decisions,
                key=lambda item: item.catalogue.state.state_id,
            )
        ),
    )
    envelope = lift.V075OperationalEnvelopeV1(
        policy,
        Fraction(0),
        Fraction(1),
        Fraction(1),
        Fraction(10),
    )
    return model, policy, envelope


@dataclass(frozen=True)
class _PositiveFixture:
    namespace: authority.V075PublicTargetTapeNamespaceV1
    environment: tuple[tuple[tuple[int, Fraction], ...], ...]
    boundary: lift.V075IndependentExactReplayBoundaryV1
    envelope: lift.V075OperationalEnvelopeV1
    observer_authority: (
        observer.V075ConstructionOnlyObserverOpenAuthorityFixtureV1
    )
    closure: observer.V075ObserverJournalClosureV1


@pytest.fixture(scope="module")
def positive_fixture() -> _PositiveFixture:
    marker = "positive"
    law = ((1, Fraction(1)),)
    environment = _environment(0, law)
    namespace = _namespace(marker=marker, environment=environment)
    occurrence, boundary = _boundary(
        namespace=namespace,
        context_index=0,
        law=law,
        marker=marker,
    )
    session = _open_observer(
        namespace=namespace,
        environment=environment,
        marker=marker,
    )
    root_action = public.root_catalogue_v1(
        occurrence.context
    ).actions[0]
    _model, _policy, envelope = _build_binding(
        occurrence=occurrence,
        boundary=boundary,
        session=session,
        root_actions=(root_action,),
        modeled_child_selector=lambda _action, children: children,
        child_action_selector=_rank_two_merge_actions,
    )
    closure = session.close_v1()
    return _PositiveFixture(
        namespace,
        environment,
        boundary,
        envelope,
        _construction_authority(
            namespace=namespace,
            marker=marker,
        ),
        closure,
    )


def test_exact_positive_endpoint_integrates_complete_fixed_concretizer(
    positive_fixture: _PositiveFixture,
) -> None:
    boundary = positive_fixture.boundary
    envelope = positive_fixture.envelope
    outcome = lift.evaluate_total_lift_v1(
        envelope=envelope,
        exact_replay=boundary,
    )
    assert type(outcome) is lift.V075TotalLiftEndpointV1
    assert (
        outcome.status
        is lift.V075TotalLiftEndpointStatusV1.EXACT_POSITIVE_ENDPOINT
    )
    candidate = outcome.candidate
    assert candidate.selected_expected_reward == Fraction(3, 64)
    assert candidate.optimal_expected_reward == Fraction(3, 64)
    assert candidate.exact_regret == Fraction(0)
    assert candidate.exact_normalized_regret == Fraction(0)
    assert candidate.environment_failure_probability == Fraction(0)
    assert candidate.policy_abort_failure_probability == Fraction(0)
    assert candidate.selected_failure_probability == Fraction(0)
    assert all(
        type(value) is Fraction
        for value in (
            candidate.selected_expected_reward,
            candidate.selected_failure_probability,
            candidate.exact_regret,
            candidate.exact_normalized_regret,
        )
    )
    document = outcome.to_document()
    assert document["operational_envelope_containment"] is True
    assert document["exact_fraction_arithmetic"] is True


def test_omitted_and_duplicate_branch_witnesses_are_protocol_failures(
    positive_fixture: _PositiveFixture,
) -> None:
    boundary = positive_fixture.boundary
    envelope = positive_fixture.envelope
    correct = lift.evaluate_total_lift_v1(
        envelope=envelope,
        exact_replay=boundary,
    )
    assert type(correct) is lift.V075TotalLiftEndpointV1
    candidate = correct.candidate
    assert len(candidate.branch_partitions) == 1
    for attacked in (
        replace(candidate, branch_partitions=()),
        replace(
            candidate,
            branch_partitions=(
                candidate.branch_partitions[0],
                candidate.branch_partitions[0],
            ),
        ),
    ):
        result = lift.verify_total_lift_candidate_v1(
            envelope=envelope,
            exact_replay=boundary,
            candidate=attacked,
        )
        assert type(result) is lift.V075TotalLiftProtocolFailureV1
        assert (
            result.code
            is (
                lift.V075TotalLiftProtocolCodeV1
                .EXACT_BRANCH_PARTITION_INVALID
            )
        )
        assert (
            result.to_document()["terminal_code"]
            == "PROTOCOL_FAILURE"
        )


def test_modeled_selected_child_without_decision_is_protocol_failure(
    positive_fixture: _PositiveFixture,
) -> None:
    boundary = positive_fixture.boundary
    envelope = positive_fixture.envelope
    policy = envelope.policy
    attacked_policy = lift.V075SelectedPolicyBindingV1(
        policy.model,
        policy.route_kind,
        policy.root_decision,
        policy.child_decisions[1:],
    )
    attacked_envelope = lift.V075OperationalEnvelopeV1(
        attacked_policy,
        envelope.selected_reward_lower,
        envelope.unrestricted_reward_upper,
        envelope.selected_failure_upper,
        envelope.normalized_regret_upper,
    )
    result = lift.evaluate_total_lift_v1(
        envelope=attacked_envelope,
        exact_replay=boundary,
    )
    assert type(result) is lift.V075TotalLiftProtocolFailureV1
    assert (
        result.code
        is lift.V075TotalLiftProtocolCodeV1.MODELED_CHILD_DECISION_MISSING
    )


def test_incomplete_or_nonuniform_concretizer_is_rejected_before_lift(
    positive_fixture: _PositiveFixture,
) -> None:
    envelope = positive_fixture.envelope
    semantic = envelope.policy.child_decisions[0].semantic_action
    assert len(semantic.ground_actions) == 2
    with pytest.raises(
        lift.V075TotalLiftProtocolViolation,
        match="complete distinct",
    ) as omitted:
        lift.V075FixedConcretizerDecisionV1(
            semantic,
            semantic.ground_actions[:1],
            (Fraction(1),),
        )
    assert (
        omitted.value.code
        is (
            lift.V075TotalLiftProtocolCodeV1
            .INCOMPLETE_FIXED_CONCRETIZER
        )
    )
    with pytest.raises(
        lift.V075TotalLiftProtocolViolation,
        match="uniformly",
    ):
        lift.V075FixedConcretizerDecisionV1(
            semantic,
            semantic.ground_actions,
            (Fraction(3, 4), Fraction(1, 4)),
        )


def test_environment_and_policy_abort_failure_are_separate_exact_mass() -> None:
    marker = "mixed-accounting"
    law = ((1, Fraction(1, 2)), (2, Fraction(1, 2)))
    environment = _environment(1, law)
    namespace = _namespace(marker=marker, environment=environment)
    occurrence, boundary = _boundary(
        namespace=namespace,
        context_index=1,
        law=law,
        marker=marker,
    )
    session = _open_observer(
        namespace=namespace,
        environment=environment,
        marker=marker,
    )
    root_action = (0, 1, 0)
    rows = _rows_by_key(boundary)
    root = public.root_catalogue_v1(occurrence.context)
    exact_root = rows[
        (root.state.state_id, root.remaining_horizon, root_action)
    ]
    active_children = _active_catalogues(exact_root)
    _model, _policy, envelope = _build_binding(
        occurrence=occurrence,
        boundary=boundary,
        session=session,
        root_actions=(root_action,),
        modeled_child_selector=lambda _action, children: children[:1],
        child_action_selector=lambda catalogue: (
            catalogue.actions[0],
        ),
    )
    outcome = lift.evaluate_total_lift_v1(
        envelope=envelope,
        exact_replay=boundary,
    )
    assert type(outcome) is lift.V075TotalLiftEndpointV1
    candidate = outcome.candidate
    assert candidate.environment_failure_probability >= Fraction(3, 5)
    assert candidate.policy_abort_failure_probability == Fraction(3, 10)
    assert (
        candidate.selected_failure_probability
        == candidate.environment_failure_probability
        + candidate.policy_abort_failure_probability
    )
    assert candidate.policy_abort_branches
    assert all(
        branch.continuation_reward == Fraction(0)
        and branch.to_document()["behavior"]
        == "ABSORBING_POLICY_ABORT_FAILURE"
        and branch.to_document()["failure"]
        == {"numerator": 1, "denominator": 1}
        for branch in candidate.policy_abort_branches
    )
    partition = candidate.branch_partitions[0]
    assert (
        set(partition.environment_failure_atom_ids)
        | set(partition.modeled_recurse_atom_ids)
        | set(partition.policy_abort_atom_ids)
        == set(partition.exact_atom_ids)
    )
    assert not (
        set(partition.environment_failure_atom_ids)
        & set(partition.policy_abort_atom_ids)
    )


def test_forged_binding_is_protocol_failure_but_honest_bad_bound_is_miss(
    positive_fixture: _PositiveFixture,
) -> None:
    boundary = positive_fixture.boundary
    broad = positive_fixture.envelope
    positive = lift.evaluate_total_lift_v1(
        envelope=broad,
        exact_replay=boundary,
    )
    assert type(positive) is lift.V075TotalLiftEndpointV1
    honest_bad = lift.V075OperationalEnvelopeV1(
        broad.policy,
        Fraction(1, 8),
        Fraction(1),
        Fraction(1),
        Fraction(10),
    )
    miss = lift.evaluate_total_lift_v1(
        envelope=honest_bad,
        exact_replay=boundary,
    )
    assert type(miss) is lift.V075TotalLiftStatisticalEnvelopeMissV1
    assert miss.miss_axes == ("SELECTED_REWARD_LOWER",)
    assert miss.to_document()["protocol_failure"] is False

    forged = lift.verify_total_lift_candidate_v1(
        envelope=honest_bad,
        exact_replay=boundary,
        candidate=positive.candidate,
    )
    assert type(forged) is lift.V075TotalLiftProtocolFailureV1
    assert (
        forged.code
        is (
            lift.V075TotalLiftProtocolCodeV1
            .CANDIDATE_RECOMPUTATION_MISMATCH
        )
    )


def test_verified_construction_journal_mints_same_exact_production_shape(
    positive_fixture: _PositiveFixture,
) -> None:
    minted = (
        lift.verify_and_mint_construction_exact_replay_from_journal_v1(
            authority=positive_fixture.observer_authority,
            namespace=positive_fixture.namespace,
            envelope=positive_fixture.envelope,
            observer_journal_closure=positive_fixture.closure,
            private_salt=_salt("positive"),
            private_environment=positive_fixture.environment,
        )
    )
    assert type(minted) is lift.V075VerifiedExactReplayMintV1
    assert (
        minted.verification.scope
        is lift.V075ExactReplayScopeV1.CONSTRUCTION_ONLY
    )
    assert (
        tuple(row.row_id for row in minted.boundary.rows)
        == tuple(row.row_id for row in positive_fixture.boundary.rows)
    )
    assert minted.verification.exact_atom_count == sum(
        len(row.atoms) for row in minted.boundary.rows
    )
    endpoint = lift.evaluate_total_lift_v1(
        envelope=positive_fixture.envelope,
        exact_replay=minted.boundary,
    )
    assert type(endpoint) is lift.V075TotalLiftEndpointV1
    assert (
        endpoint.status
        is lift.V075TotalLiftEndpointStatusV1.EXACT_POSITIVE_ENDPOINT
    )
    document = minted.to_document()
    flattened = repr(document).lower()
    assert "private_environment" in flattened
    assert "transition_law_serialized': false" in flattened
    assert "private_salt_serialized': false" in flattened
    assert "random_tape_serialized': false" in flattened
    assert "random_words" not in flattened
    assert "spawn_law" not in flattened
    assert _salt("positive").hex() not in flattened

    honest_bad = lift.V075OperationalEnvelopeV1(
        positive_fixture.envelope.policy,
        Fraction(1, 8),
        Fraction(1),
        Fraction(1),
        Fraction(10),
    )
    transplanted = lift.evaluate_total_lift_v1(
        envelope=honest_bad,
        exact_replay=minted.boundary,
    )
    assert type(transplanted) is lift.V075TotalLiftProtocolFailureV1
    assert (
        transplanted.code
        is lift.V075TotalLiftProtocolCodeV1.BINDING_MISMATCH
    )
    missed_mint = (
        lift.verify_and_mint_construction_exact_replay_from_journal_v1(
            authority=positive_fixture.observer_authority,
            namespace=positive_fixture.namespace,
            envelope=honest_bad,
            observer_journal_closure=positive_fixture.closure,
            private_salt=_salt("positive"),
            private_environment=positive_fixture.environment,
        )
    )
    miss = lift.evaluate_total_lift_v1(
        envelope=honest_bad,
        exact_replay=missed_mint.boundary,
    )
    assert type(miss) is lift.V075TotalLiftStatisticalEnvelopeMissV1
    assert miss.to_document()["scientific_endpoint_credit_allowed"] is False


def test_production_mint_rejects_construction_authority_without_target_access(
    positive_fixture: _PositiveFixture,
) -> None:
    with pytest.raises(
        lift.V075ExactReplayMintViolation,
        match="production-open authority",
    ) as failure:
        lift.verify_and_mint_production_exact_replay_boundary_v1(
            authority=positive_fixture.observer_authority,
            namespace=positive_fixture.namespace,
            envelope=positive_fixture.envelope,
            observer_journal_closure=positive_fixture.closure,
            private_salt=_salt("positive"),
            private_environment=positive_fixture.environment,
        )
    assert (
        failure.value.failure_class
        is lift.V075ExactReplayMintFailureClassV1.PROTOCOL_FAILURE
    )
    assert (
        failure.value.code
        is (
            lift.V075ExactReplayMintFailureCodeV1
            .PRODUCTION_AUTHORITY_TYPE_MISMATCH
        )
    )


def test_reveal_mismatch_and_observer_transplant_are_integrity_failures(
    positive_fixture: _PositiveFixture,
) -> None:
    with pytest.raises(lift.V075ExactReplayMintViolation) as mismatch:
        lift.verify_and_mint_construction_exact_replay_from_journal_v1(
            authority=positive_fixture.observer_authority,
            namespace=positive_fixture.namespace,
            envelope=positive_fixture.envelope,
            observer_journal_closure=positive_fixture.closure,
            private_salt=_salt("wrong"),
            private_environment=positive_fixture.environment,
        )
    assert (
        mismatch.value.failure_class
        is lift.V075ExactReplayMintFailureClassV1.INTEGRITY_FAILURE
    )
    assert (
        mismatch.value.code
        is lift.V075ExactReplayMintFailureCodeV1.PRIVATE_REVEAL_MISMATCH
    )

    other_namespace = _namespace(
        marker="transplant",
        environment=positive_fixture.environment,
    )
    other_authority = _construction_authority(
        namespace=other_namespace,
        marker="transplant",
    )
    with pytest.raises(lift.V075ExactReplayMintViolation) as transplant:
        lift.verify_and_mint_construction_exact_replay_from_journal_v1(
            authority=other_authority,
            namespace=positive_fixture.namespace,
            envelope=positive_fixture.envelope,
            observer_journal_closure=positive_fixture.closure,
            private_salt=_salt("positive"),
            private_environment=positive_fixture.environment,
        )
    assert (
        transplant.value.failure_class
        is lift.V075ExactReplayMintFailureClassV1.INTEGRITY_FAILURE
    )
    assert (
        transplant.value.code
        is lift.V075ExactReplayMintFailureCodeV1.OBSERVER_CLOSURE_INVALID
    )


def test_missing_or_duplicate_observation_lineage_fails_closed(
    positive_fixture: _PositiveFixture,
) -> None:
    records = tuple(
        entry.record for entry in positive_fixture.closure.entries
    )
    assert len(records) > 1
    missing = _resigned_closure(
        template=positive_fixture.closure,
        records=records[:-1],
    )
    with pytest.raises(lift.V075ExactReplayMintViolation) as omitted:
        lift.verify_and_mint_construction_exact_replay_from_journal_v1(
            authority=positive_fixture.observer_authority,
            namespace=positive_fixture.namespace,
            envelope=positive_fixture.envelope,
            observer_journal_closure=missing,
            private_salt=_salt("positive"),
            private_environment=positive_fixture.environment,
        )
    assert (
        omitted.value.code
        is lift.V075ExactReplayMintFailureCodeV1.CAPABILITY_LINEAGE_INVALID
    )

    duplicate = _resigned_closure(
        template=positive_fixture.closure,
        records=(*records, records[-1]),
    )
    with pytest.raises(lift.V075ExactReplayMintViolation) as repeated:
        lift.verify_and_mint_construction_exact_replay_from_journal_v1(
            authority=positive_fixture.observer_authority,
            namespace=positive_fixture.namespace,
            envelope=positive_fixture.envelope,
            observer_journal_closure=duplicate,
            private_salt=_salt("positive"),
            private_environment=positive_fixture.environment,
        )
    assert (
        repeated.value.code
        is lift.V075ExactReplayMintFailureCodeV1.OBSERVER_CLOSURE_INVALID
    )


def test_incomplete_caller_supplied_exact_support_cannot_mint_boundary(
    positive_fixture: _PositiveFixture,
) -> None:
    with pytest.raises(
        lift.V075TotalLiftProtocolViolation,
    ) as failure:
        lift.mint_construction_exact_replay_boundary_v1(
            occurrence=(
                positive_fixture.envelope.policy.model.occurrence
            ),
            rows=positive_fixture.boundary.rows[:-1],
            construction_fixture_registration_id=_id(
                "incomplete-exact-support"
            ),
        )
    assert (
        failure.value.code
        is lift.V075TotalLiftProtocolCodeV1.EXACT_REPLAY_INCOMPLETE
    )


def test_planner_types_are_law_free_and_exact_atoms_are_replay_only() -> None:
    source = inspect.getsource(lift)
    assert "spawn_law" not in source
    operational_types = (
        lift.V075LawFreePlannerOccurrenceV1,
        lift.V075ObservedRowBindingV1,
        lift.V075ObservedSemanticActionV1,
        lift.V075FixedConcretizerDecisionV1,
        lift.V075SelectedRootSupportV1,
        lift.V075LawFreePartialModelBindingV1,
        lift.V075SelectedPolicyBindingV1,
        lift.V075OperationalEnvelopeV1,
    )
    assert all(
        "H2GraphTransitionAtomV1" not in repr(cls.__annotations__)
        and "V075ExactReplay" not in repr(cls.__annotations__)
        for cls in operational_types
    )
    assert "H2GraphKernelV1" not in repr(
        {
            cls.__name__: cls.__annotations__
            for cls in operational_types
        }
    )
    assert lift.PRODUCTION_EXACT_REPLAY_MINT_IMPLEMENTED is True
    assert lift.PRODUCTION_TOTAL_LIFT_EXECUTION_ALLOWED is False

    signature = inspect.signature(lift.evaluate_total_lift_v1)
    assert tuple(signature.parameters) == ("envelope", "exact_replay")
    production_signature = inspect.signature(
        lift.verify_and_mint_production_exact_replay_boundary_v1
    )
    for checked in (signature, production_signature):
        assert all(
            "valid" not in name
            and "expected" not in name
            and "status" not in name
            for name in checked.parameters
        )
    duck = object()
    outcome = lift.evaluate_total_lift_v1(
        envelope=duck,  # type: ignore[arg-type]
        exact_replay=duck,  # type: ignore[arg-type]
    )
    assert type(outcome) is lift.V075TotalLiftProtocolFailureV1
    assert (
        outcome.code
        is lift.V075TotalLiftProtocolCodeV1.INPUT_TYPE_MISMATCH
    )
