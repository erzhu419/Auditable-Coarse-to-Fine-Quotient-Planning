from __future__ import annotations

from dataclasses import replace
from fractions import Fraction
import hashlib
import os

import pytest

from acfqp import v075_batch_native_statistical_backend_v1 as backend
from acfqp import v075_batch_native_total_lift_authority_v1 as total_lift
from acfqp import v075_batched_observer_authority_v1 as batched
from acfqp import v075_multistage_observer_lifecycle_v1 as lifecycle
from acfqp import v075_private_observer_boundary_v1 as observer
from acfqp import v075_public_campaign_authority_v1 as campaign
from acfqp import v075_public_graph_semantics_v1 as graph
from acfqp import v075_registered_occurrence_worker_v1 as worker
from tests.v075_signature_test_support import (
    make_public_key,
    sign_test_message,
)


pytestmark = pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_V075_BATCH_LIFT_E2E") != "1",
    reason=(
        "full signed batch-native construction E2E is opt-in; set "
        "ACFQP_RUN_V075_BATCH_LIFT_E2E=1"
    ),
)

_ARM = worker.V075WorkerArmV1.NO_PRIOR
_OCCURRENCE_ORDINAL = 75
_MARKER = "v075-batch-native-total-lift-e2e-rank1"


def _id(label: str) -> str:
    return hashlib.sha256(
        b"acfqp:v075-batch-native-total-lift-e2e-test:v1"
        + b"\x00"
        + label.encode("utf-8")
    ).hexdigest()


def _salt() -> bytes:
    return hashlib.sha512(
        ("acfqp-private-" + _MARKER).encode("utf-8")
    ).digest()


def _construction_environment(
) -> tuple[tuple[tuple[int, Fraction], ...], ...]:
    # Rank-1 is retained for the unused construction contexts.  On the only
    # topology whose complete child closure fits the immutable 19-row cap
    # (ordinal 1), rank-1 is exactly ground-infeasible.  Deterministic rank-3
    # is the registered finite-law control that is both feasible and cap-safe.
    return (
        ((1, Fraction(1)),),
        ((3, Fraction(1)),),
        ((1, Fraction(1)),),
    )


class _ConstructionSigner:
    def public_verification_key_v1(
        self,
    ) -> campaign.V075RSAPublicVerificationKeyV1:
        return make_public_key("OBSERVER_EVIDENCE")

    def sign_observer_evidence_v1(self, message: bytes) -> str:
        return sign_test_message(
            message,
            key_role="OBSERVER_EVIDENCE",
        )


def _namespace() -> campaign.V075PublicTargetTapeNamespaceV1:
    family = campaign.freeze_v075_public_family_generation_v1()
    registry = campaign.V075TrustedSignerRegistryV1(
        make_public_key("CAMPAIGN_AUTHORITY"),
        make_public_key("OBSERVER_EVIDENCE"),
    )
    commitment = campaign.seal_opaque_environment_commitment_v1(
        family=family,
        secret_salt=_salt(),
        secret_laws=_construction_environment(),
    )

    def claim(
        role: campaign.V075ExternalAuthorityRoleV1,
    ) -> campaign.V075SignedExternalAuthorityClaimV1:
        external_id = _id("claim-" + role.value)
        message = campaign.external_authority_claim_signing_bytes_v1(
            signer_registry=registry,
            role=role,
            external_id=external_id,
        )
        return campaign.V075SignedExternalAuthorityClaimV1(
            registry,
            role,
            external_id,
            sign_test_message(message),
        )

    role = campaign.V075ExternalAuthorityRoleV1
    return campaign.derive_public_target_tape_namespace_v1(
        family=family,
        environment_commitment=commitment,
        signer_registry=registry,
        claimed_final_preregistration_registry_id=registry.registry_id,
        remote_main_anchor=claim(role.REMOTE_MAIN_ANCHOR),
        final_preregistration=claim(role.FINAL_PREREGISTRATION),
        observer_profile=claim(role.OBSERVER_PROFILE),
    )


def _occurrence_identity(
    *,
    namespace: campaign.V075PublicTargetTapeNamespaceV1,
    context: campaign.V075PublicReplicateContextV1,
    caps: worker.V075WorkerCapProfileV1,
    thresholds: worker.V075WorkerThresholdProfileV1,
) -> backend.V075BatchNativeOccurrenceIdentityV1:
    return backend.freeze_v075_batch_native_occurrence_identity_v1(
        namespace=namespace,
        context=context,
        arm=_ARM,
        occurrence_ordinal=_OCCURRENCE_ORDINAL,
        threshold_profile=thresholds,
        cap_profile=caps,
        source_prior_transport=None,
    )


def _discovery_stream(
    *,
    namespace: campaign.V075PublicTargetTapeNamespaceV1,
    catalogue: graph.V075LegalActionCatalogueV1,
    action: tuple[int, int, int],
) -> graph.V075TransitionStreamIdentityV1:
    row = graph.observation_row_binding_v1(
        catalogue.context,
        catalogue,
        action,
    )
    epoch = graph.derive_shared_support_epoch_v1(
        namespace=namespace,
        row_binding=row,
        epoch_index=0,
        evidence=(),
    )
    chain = graph.freeze_shared_support_chain_v1(
        namespace=namespace,
        row_binding=row,
        epochs=(epoch,),
    )
    pairing = graph.freeze_five_arm_pairing_authority_v1(
        namespace=namespace,
        row_binding=row,
        support_chain=chain,
    )
    return graph.derive_transition_stream_identity_v1(
        pairing_authority=pairing,
        arm=_ARM.value,
    )


def _distinct_projected_outcome_ids(
    discovery: batched.V075SignedBatchedObservationV1,
) -> tuple[str, ...]:
    context = discovery.request.stream_identity.row_binding.context
    representative_by_state_id: dict[str, str] = {}
    for outcome in discovery.outcomes:
        state = graph.V075SymbolicGraphStateV1(
            context,
            outcome.next_ranks,
            outcome.failure,
        )
        current = representative_by_state_id.get(state.state_id)
        if current is None or outcome.outcome_id < current:
            representative_by_state_id[state.state_id] = outcome.outcome_id
    return tuple(sorted(representative_by_state_id.values()))


def _validation_stream(
    *,
    namespace: campaign.V075PublicTargetTapeNamespaceV1,
    discovery_stream: graph.V075TransitionStreamIdentityV1,
    evidence: tuple[graph.V075BatchAggregateSupportEvidenceV1, ...],
) -> graph.V075TransitionStreamIdentityV1:
    row = discovery_stream.row_binding
    discovery_epoch = (
        discovery_stream.pairing_authority.support_chain.leaf
    )
    validation_epoch = graph.derive_shared_support_epoch_v1(
        namespace=namespace,
        row_binding=row,
        epoch_index=1,
        evidence=evidence,
        parent=discovery_epoch,
    )
    chain = graph.freeze_shared_support_chain_v1(
        namespace=namespace,
        row_binding=row,
        epochs=(discovery_epoch, validation_epoch),
    )
    pairing = graph.freeze_five_arm_pairing_authority_v1(
        namespace=namespace,
        row_binding=row,
        support_chain=chain,
    )
    return graph.derive_transition_stream_identity_v1(
        pairing_authority=pairing,
        arm=_ARM.value,
    )


def _discover_all_rows(
    *,
    controller: lifecycle.V075ParentOwnedMultistageObserverLifecycleV1,
    namespace: campaign.V075PublicTargetTapeNamespaceV1,
    catalogues: tuple[graph.V075LegalActionCatalogueV1, ...],
) -> tuple[
    tuple[
        graph.V075TransitionStreamIdentityV1,
        batched.V075SignedBatchedObservationV1,
    ],
    ...,
]:
    records = []
    for catalogue in catalogues:
        for action in catalogue.actions:
            stream = _discovery_stream(
                namespace=namespace,
                catalogue=catalogue,
                action=action,
            )
            observed = controller.execute_batch_v1(
                stream_identity=stream,
                accepted_draw_start=1,
                accepted_draw_count=64,
                accepted_draw_cap=64,
            )
            records.append((stream, observed))
    return tuple(records)


def _freeze_all_row_supports(
    *,
    controller: lifecycle.V075ParentOwnedMultistageObserverLifecycleV1,
    namespace: campaign.V075PublicTargetTapeNamespaceV1,
    discoveries: tuple[
        tuple[
            graph.V075TransitionStreamIdentityV1,
            batched.V075SignedBatchedObservationV1,
        ],
        ...,
    ],
) -> tuple[
    tuple[
        graph.V075TransitionStreamIdentityV1,
        tuple[graph.V075BatchAggregateSupportEvidenceV1, ...],
    ],
    ...,
]:
    values = []
    for discovery_stream, discovery in discoveries:
        evidence = controller.freeze_aggregate_support_evidence_v1(
            discovery_batch=discovery,
            selected_outcome_ids=(
                _distinct_projected_outcome_ids(discovery)
            ),
        )
        stream = _validation_stream(
            namespace=namespace,
            discovery_stream=discovery_stream,
            evidence=evidence,
        )
        controller.register_validation_support_epoch_v1(
            stream_identity=stream,
        )
        values.append((stream, evidence))
    return tuple(values)


def _validate_all_rows(
    *,
    controller: lifecycle.V075ParentOwnedMultistageObserverLifecycleV1,
    validations: tuple[
        tuple[
            graph.V075TransitionStreamIdentityV1,
            tuple[graph.V075BatchAggregateSupportEvidenceV1, ...],
        ],
        ...,
    ],
    caps: worker.V075WorkerCapProfileV1,
) -> None:
    for stream, _evidence in validations:
        if stream.row_binding.remaining_horizon == 2:
            count = caps.initial_validation_draws_per_row
            accepted_cap = (
                count
                + caps.maximum_adaptive_rounds
                * caps.promotion_validation_draws_per_round
            )
        else:
            # The canonical adaptive backend requires 8,192, not 2,048, for
            # newly acquired H=1 rows.  The E2E does not weaken that cap.
            count = caps.new_child_validation_draws_per_row
            accepted_cap = (
                count
                + caps.maximum_adaptive_rounds
                * caps.promotion_validation_draws_per_round
            )
        controller.execute_batch_v1(
            stream_identity=stream,
            accepted_draw_start=1,
            accepted_draw_count=count,
            accepted_draw_cap=accepted_cap,
        )


def _child_catalogues(
    *,
    context: campaign.V075PublicReplicateContextV1,
    root_supports: tuple[
        tuple[
            graph.V075TransitionStreamIdentityV1,
            tuple[graph.V075BatchAggregateSupportEvidenceV1, ...],
        ],
        ...,
    ],
) -> tuple[graph.V075LegalActionCatalogueV1, ...]:
    children = {
        item.observed_state.state_id: item.observed_state
        for _stream, evidence in root_supports
        for item in evidence
        if not item.observed_state.failure
    }
    return tuple(
        graph.V075LegalActionCatalogueV1(
            context,
            children[state_id],
            1,
            graph.legal_action_triples_v1(
                context,
                children[state_id].ranks,
                children[state_id].failure,
            ),
        )
        for state_id in sorted(children)
    )


@pytest.fixture(scope="module")
def completed_batch_native_total_lift_e2e():
    namespace = _namespace()
    # The preregistered ordinal-1 topology has ten complete H=1 action rows;
    # ordinals 0/2 each have twenty and intentionally exceed the frozen
    # maximum_new_child_action_rows=19 acquisition cap.
    context = namespace.family.replicate_contexts[1]
    authority = observer.V075ConstructionOnlyObserverOpenAuthorityFixtureV1(
        namespace,
        _id("construction-open-authority"),
    )
    private_environment = _construction_environment()
    session = observer.open_construction_private_observer_fixture_v1(
        authority=authority,
        private_salt=_salt(),
        private_environment=private_environment,
        observer_signer=_ConstructionSigner(),
        session_external_id=_id("observer-session"),
    )
    wrapped = (
        batched.wrap_v075_construction_batched_observer_session_v1(
            session
        )
    )
    replay_environment = (
        batched.issue_v075_construction_batch_replay_environment_fixture_v1(
            namespace=namespace,
            private_salt=_salt(),
            private_environment=private_environment,
        )
    )
    caps = worker.V075WorkerCapProfileV1()
    thresholds = worker.V075WorkerThresholdProfileV1()
    occurrence_identity = _occurrence_identity(
        namespace=namespace,
        context=context,
        caps=caps,
        thresholds=thresholds,
    )
    occurrence_id = occurrence_identity.occurrence_id
    controller = (
        lifecycle.open_v075_parent_owned_multistage_lifecycle_v1(
            batched_session=wrapped,
            occurrence_id=occurrence_id,
            context_id=context.context_id,
            arm=_ARM,
            route_cap_profile=caps,
        )
    )

    # Round 0 is parent-owned and phase-separated across every root row:
    # all DISCOVERY -> all support freezes -> all VALIDATION.
    root_discoveries = _discover_all_rows(
        controller=controller,
        namespace=namespace,
        catalogues=(graph.root_catalogue_v1(context),),
    )
    root_supports = _freeze_all_row_supports(
        controller=controller,
        namespace=namespace,
        discoveries=root_discoveries,
    )
    _validate_all_rows(
        controller=controller,
        validations=root_supports,
        caps=caps,
    )

    # Round 1 is generated only from observed, nonfailure root children and
    # materializes the complete legal action catalogue for each such child.
    child_catalogues = _child_catalogues(
        context=context,
        root_supports=root_supports,
    )
    child_action_row_count = sum(
        len(item.actions) for item in child_catalogues
    )
    assert 0 < child_action_row_count <= caps.maximum_new_child_action_rows
    controller.start_adaptive_round_v1(1)
    child_discoveries = _discover_all_rows(
        controller=controller,
        namespace=namespace,
        catalogues=child_catalogues,
    )
    child_supports = _freeze_all_row_supports(
        controller=controller,
        namespace=namespace,
        discoveries=child_discoveries,
    )
    _validate_all_rows(
        controller=controller,
        validations=child_supports,
        caps=caps,
    )

    sealed = controller.close_construction_v1(
        authority=authority,
        private_environment=replay_environment,
        process_launches=0,
        child_intent_count=len(child_catalogues),
        terminal_code=(
            lifecycle.V075LifecycleTerminalCodeV1
            .COMPLETE_REGISTERED_CHECKPOINT_CLOSED
        ),
    )
    request = backend.freeze_v075_batch_native_backend_request_v1(
        arm=_ARM,
        occurrence_ordinal=_OCCURRENCE_ORDINAL,
        batches=sealed.batches,
        occurrence_identity=occurrence_identity,
    )
    assert request.occurrence_id == occurrence_id
    native_result = (
        backend.compile_v075_batch_native_statistical_backend_v1(request)
    )
    planned = backend.plan_v075_batch_native_route_v1(native_result)
    if not planned.ready_for_exact_total_lift:
        envelope = (
            None
            if planned.envelope is None
            else planned.envelope.to_document()
        )
        pytest.fail(
            "canonical planner was not ready without weakening statistics: "
            f"status={planned.status.value}; envelope={envelope}"
        )
    lineage = total_lift.freeze_v075_batch_native_total_lift_lineage_v1(
        backend_result=native_result,
        planner_result=planned,
        sealed_lifecycle=sealed,
    )
    exact_replay = (
        total_lift.mint_v075_batch_native_construction_exact_replay_v1(
            lineage=lineage,
            authority=authority,
            private_environment=replay_environment,
        )
    )
    verification = (
        total_lift.evaluate_v075_batch_native_construction_total_lift_v1(
            lineage=lineage,
            exact_replay=exact_replay,
        )
    )
    independently_verified = (
        total_lift
        .verify_v075_batch_native_construction_total_lift_candidate_v1(
            lineage=lineage,
            exact_replay=exact_replay,
            claimed=verification.candidate,
        )
    )
    return {
        "caps": caps,
        "sealed": sealed,
        "request": request,
        "native_result": native_result,
        "planned": planned,
        "lineage": lineage,
        "exact_replay": exact_replay,
        "verification": verification,
        "independently_verified": independently_verified,
        "root_row_count": len(root_discoveries),
        "child_row_count": len(child_discoveries),
    }


def test_real_multistage_batch_native_total_lift_end_to_end(
    completed_batch_native_total_lift_e2e,
) -> None:
    result = completed_batch_native_total_lift_e2e
    sealed = result["sealed"]
    native_result = result["native_result"]
    verification = result["verification"]
    independently_verified = result["independently_verified"]

    assert sealed.underlying_closure.entries == ()
    assert sealed.closure.accepted_draw_count == sum(
        item.request.accepted_draw_count for item in sealed.batches
    )
    assert result["root_row_count"] == len(
        graph.root_catalogue_v1(
            result["request"].context
        ).actions
    )
    assert 0 < result["child_row_count"] <= (
        result["caps"].maximum_new_child_action_rows
    )
    assert native_result.request.batches == result["request"].batches
    assert (
        native_result.work.to_document()["native_zeros_complete"]
        is True
    )
    assert (
        verification.verification_id
        == independently_verified.verification_id
    )
    assert (
        independently_verified.candidate.candidate_id
        == verification.candidate.candidate_id
    )
    assert verification.candidate.partitions
    assert all(
        item.to_document()["disjoint_exhaustive_partition"]
        for item in verification.candidate.partitions
    )
    assert (
        total_lift.PRODUCTION_TOTAL_LIFT_EXECUTION_ALLOWED
        is False
    )


def test_production_candidate_domains_reject_cross_scope_and_tampering(
    completed_batch_native_total_lift_e2e,
) -> None:
    result = completed_batch_native_total_lift_e2e
    lineage = result["lineage"]
    construction_replay = result["exact_replay"]
    construction_candidate = result["verification"].candidate
    sealed = result["sealed"]

    with pytest.raises(
        total_lift.V075BatchNativeTotalLiftInvariantViolation,
        match="production lineage and replay types",
    ):
        total_lift.evaluate_v075_batch_native_production_total_lift_v1(
            lineage=lineage,
            exact_replay=construction_replay,
        )

    production_replay = (
        total_lift.V075BatchNativeProductionExactReplayV1(
            total_lift._PRODUCTION_EXACT_REPLAY_ISSUER,
            lineage.lineage_id,
            construction_replay.rows,
            construction_replay.private_replay_verification_ids,
            _id("production-open-authorization"),
            sealed.closure.closure_id,
            sealed.underlying_closure_verification.verification_id,
        )
    )
    with pytest.raises(
        total_lift.V075BatchNativeTotalLiftInvariantViolation,
        match="transplanted across authorization|production replay",
    ):
        total_lift.evaluate_v075_batch_native_production_total_lift_v1(
            lineage=lineage,
            exact_replay=production_replay,
        )
    transplanted = replace(
        production_replay,
        lineage_id=_id("foreign-lineage"),
    )
    with pytest.raises(
        total_lift.V075BatchNativeTotalLiftInvariantViolation,
        match="production lineage and replay types",
    ):
        total_lift.evaluate_v075_batch_native_production_total_lift_v1(
            lineage=lineage,
            exact_replay=transplanted,
        )

    production_candidate = (
        total_lift.V075BatchNativeProductionTotalLiftCandidateV1(
            total_lift._PRODUCTION_CANDIDATE_ISSUER,
            construction_candidate.lineage_id,
            production_replay.replay_id,
            production_replay.observer_open_authorization_id,
            production_replay.multistage_closure_id,
            production_replay.underlying_closure_verification_id,
            (
                total_lift.V075BatchTotalLiftProductionStatusV1
                .EXACT_POSITIVE_PRODUCTION_CANDIDATE
            ),
            construction_candidate.selected_expected_reward,
            construction_candidate.environment_failure_probability,
            construction_candidate.policy_abort_failure_probability,
            construction_candidate.selected_failure_probability,
            construction_candidate.optimal_expected_reward,
            construction_candidate.optimal_failure_probability,
            construction_candidate.exact_normalized_regret,
            construction_candidate.optimal_policy_signature,
            construction_candidate.envelope_miss_axes,
            construction_candidate.partitions,
        )
    )
    with pytest.raises(
        total_lift.V075BatchNativeTotalLiftInvariantViolation,
        match="duck-typed candidates",
    ):
        (
            total_lift
            .verify_v075_batch_native_construction_total_lift_candidate_v1(
                lineage=lineage,
                exact_replay=construction_replay,
                claimed=production_candidate,
            )
        )
    with pytest.raises(
        total_lift.V075BatchNativeTotalLiftInvariantViolation,
        match="production lineage and replay types|transplanted",
    ):
        total_lift.verify_v075_batch_native_production_total_lift_candidate_v1(
            lineage=lineage,
            exact_replay=production_replay,
            claimed=production_candidate,
        )

    tampered = replace(
        production_candidate,
        selected_expected_reward=(
            production_candidate.selected_expected_reward + Fraction(1, 64)
        ),
    )
    assert tampered.candidate_id != production_candidate.candidate_id
    with pytest.raises(
        total_lift.V075BatchNativeTotalLiftInvariantViolation,
        match="differs from recomputation",
    ):
        total_lift._verify_exact_production_candidate_match(
            claimed=tampered,
            expected=production_candidate,
        )
    verified = total_lift._verify_exact_production_candidate_match(
        claimed=production_candidate,
        expected=production_candidate,
    )
    assert (
        verified.independently_recomputed_candidate_id
        == production_candidate.candidate_id
    )
    assert verified.to_document()["official_execution_allowed"] is False


def test_multistage_registry_transplant_is_rejected(
    completed_batch_native_total_lift_e2e,
) -> None:
    sealed = completed_batch_native_total_lift_e2e["sealed"]
    transplanted = (
        sealed.batches[1:] + sealed.batches[:1]
    )
    with pytest.raises(
        lifecycle.V075MultistageObserverLifecycleInvariantViolation
    ):
        lifecycle.verify_v075_multistage_occurrence_closure_v1(
            closure=sealed.closure,
            batches=transplanted,
            public_verifications=sealed.public_verifications,
            sequence_verifications=sealed.sequence_verifications,
            private_replay_verifications=(
                sealed.private_replay_verifications
            ),
            aggregate_support_evidence=(
                sealed.aggregate_support_evidence
            ),
            underlying_closure=sealed.underlying_closure,
            underlying_closure_verification=(
                sealed.underlying_closure_verification
            ),
            observer_open_binding=(
                sealed.underlying_closure.authority_binding
            ),
        )

    forged_count = replace(
        sealed.closure,
        accepted_draw_count=sealed.closure.accepted_draw_count + 1,
    )
    with pytest.raises(
        lifecycle.V075MultistageObserverLifecycleInvariantViolation
    ):
        lifecycle.verify_v075_multistage_occurrence_closure_v1(
            closure=forged_count,
            batches=sealed.batches,
            public_verifications=sealed.public_verifications,
            sequence_verifications=sealed.sequence_verifications,
            private_replay_verifications=(
                sealed.private_replay_verifications
            ),
            aggregate_support_evidence=(
                sealed.aggregate_support_evidence
            ),
            underlying_closure=sealed.underlying_closure,
            underlying_closure_verification=(
                sealed.underlying_closure_verification
            ),
            observer_open_binding=(
                sealed.underlying_closure.authority_binding
            ),
        )
