from __future__ import annotations

from dataclasses import replace
from fractions import Fraction
import hashlib
import json

import pytest

from acfqp.phase3e_ids import canonical_json_bytes
from acfqp import v075_batch_native_statistical_backend_v1 as native
from acfqp import v075_batched_observer_authority_v1 as batch
from acfqp import v075_private_observer_boundary_v1 as observer
from acfqp import v075_public_campaign_authority_v1 as authority
from acfqp import v075_public_graph_semantics_v1 as graph
from acfqp import v075_registered_occurrence_worker_v1 as worker

try:
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import padding, rsa
except ImportError:  # pragma: no cover - slow stdlib-only CI fallback
    hashes = padding = rsa = None
    from tests.test_v075_private_observer_boundary_v1 import (
        _ConstructionSigner,
        _fixture,
        _namespace,
        _salt,
        _synthetic_environment,
    )


_MARKER = "batch-native-real-private-replay"


def _id(label: str) -> str:
    return hashlib.sha256(
        b"acfqp:v075-batch-native-test:v2"
        + b"\x00"
        + label.encode("utf-8")
    ).hexdigest()


if rsa is not None:
    _CAMPAIGN_TEST_KEY = rsa.generate_private_key(
        public_exponent=65_537,
        key_size=2_048,
    )
    _OBSERVER_TEST_KEY = rsa.generate_private_key(
        public_exponent=65_537,
        key_size=2_048,
    )

    def _public_key(role, private_key):
        return authority.V075RSAPublicVerificationKeyV1(
            role,
            private_key.public_key().public_numbers().n,
        )

    def _sign(private_key, message):
        return private_key.sign(
            message,
            padding.PKCS1v15(),
            hashes.SHA256(),
        ).hex()

    def _synthetic_environment():
        return (
            ((1, Fraction(2, 3)), (2, Fraction(1, 3))),
            ((1, Fraction(3, 4)), (2, Fraction(1, 4))),
            ((1, Fraction(4, 5)), (2, Fraction(1, 5))),
        )

    def _salt(marker):
        return hashlib.sha512(
            ("v075-batch-native-real-salt-" + marker).encode()
        ).digest()

    def _namespace(marker):
        family = authority.freeze_v075_public_family_generation_v1()
        commitment = authority.seal_opaque_environment_commitment_v1(
            family=family,
            secret_salt=_salt(marker),
            secret_laws=_synthetic_environment(),
        )
        registry = authority.V075TrustedSignerRegistryV1(
            _public_key("CAMPAIGN_AUTHORITY", _CAMPAIGN_TEST_KEY),
            _public_key("OBSERVER_EVIDENCE", _OBSERVER_TEST_KEY),
        )
        claims = []
        for role in authority.V075ExternalAuthorityRoleV1:
            external_id = _id("external-" + marker + "-" + role.value)
            message = authority.external_authority_claim_signing_bytes_v1(
                signer_registry=registry,
                role=role,
                external_id=external_id,
            )
            claims.append(
                authority.V075SignedExternalAuthorityClaimV1(
                    registry,
                    role,
                    external_id,
                    _sign(_CAMPAIGN_TEST_KEY, message),
                )
            )
        return authority.derive_public_target_tape_namespace_v1(
            family=family,
            environment_commitment=commitment,
            signer_registry=registry,
            claimed_final_preregistration_registry_id=registry.registry_id,
            remote_main_anchor=claims[0],
            final_preregistration=claims[1],
            observer_profile=claims[2],
        )

    class _ConstructionSigner:
        def public_verification_key_v1(self):
            return _public_key("OBSERVER_EVIDENCE", _OBSERVER_TEST_KEY)

        def sign_observer_evidence_v1(self, message):
            return _sign(_OBSERVER_TEST_KEY, message)

    def _fixture(namespace, marker):
        return observer.V075ConstructionOnlyObserverOpenAuthorityFixtureV1(
            namespace,
            _id("construction-authority-" + marker),
        )


def _bootstrap_stream(namespace, row, arm):
    root_epoch = graph.derive_shared_support_epoch_v1(
        namespace=namespace,
        row_binding=row,
        epoch_index=0,
        evidence=(),
    )
    root_chain = graph.freeze_shared_support_chain_v1(
        namespace=namespace,
        row_binding=row,
        epochs=(root_epoch,),
    )
    pairing = graph.freeze_five_arm_pairing_authority_v1(
        namespace=namespace,
        row_binding=row,
        support_chain=root_chain,
    )
    return (
        root_epoch,
        graph.derive_transition_stream_identity_v1(
            pairing_authority=pairing,
            arm=arm.value,
        ),
    )


def _observed_support_outcome(discovery, *, needs_child):
    candidates = tuple(
        item
        for item in discovery.outcomes
        if (
            not needs_child
            or (
                not item.failure
                and not item.terminal
                and graph.legal_action_triples_v1(
                    discovery.request.stream_identity.row_binding.context,
                    item.next_ranks,
                    False,
                )
            )
        )
    )
    if not candidates:
        raise AssertionError("registered real DISCOVERY tape found no support")
    return min(candidates, key=lambda item: item.outcome_id)


def _observe_row(
    *,
    namespace,
    wrapped,
    private_authority,
    private_fixture,
    catalogue,
    action,
    arm,
    promotion_batches=0,
):
    row = graph.observation_row_binding_v1(
        catalogue.context,
        catalogue,
        action,
    )
    root_epoch, discovery_stream = _bootstrap_stream(
        namespace,
        row,
        arm,
    )
    discovery_request = wrapped.issue_request_v1(
        stream_identity=discovery_stream,
        accepted_draw_start=1,
        accepted_draw_count=64,
        accepted_draw_cap=64,
    )
    discovery = wrapped.execute_request_v1(discovery_request)
    selected = _observed_support_outcome(
        discovery,
        needs_child=catalogue.remaining_horizon == 2,
    )
    evidence = batch.freeze_v075_batch_aggregate_support_evidence_v1(
        batched_session=wrapped,
        discovery_batch=discovery,
        selected_outcome_ids=(selected.outcome_id,),
    )
    assert all(
        type(item) is graph.V075BatchAggregateSupportEvidenceV1
        for item in evidence
    )
    validation_epoch = graph.derive_shared_support_epoch_v1(
        namespace=namespace,
        row_binding=row,
        epoch_index=1,
        evidence=evidence,
        parent=root_epoch,
    )
    validation_chain = graph.freeze_shared_support_chain_v1(
        namespace=namespace,
        row_binding=row,
        epochs=(root_epoch, validation_epoch),
    )
    validation_pairing = graph.freeze_five_arm_pairing_authority_v1(
        namespace=namespace,
        row_binding=row,
        support_chain=validation_chain,
    )
    validation_stream = graph.derive_transition_stream_identity_v1(
        pairing_authority=validation_pairing,
        arm=arm.value,
    )
    caps = worker.V075WorkerCapProfileV1()
    if arm is worker.V075WorkerArmV1.MATCHED_DIRECT_GROUND:
        validation_count = caps.direct_validation_checkpoints[0]
        validation_cap = validation_count
    elif catalogue.remaining_horizon == 2:
        validation_count = caps.initial_validation_draws_per_row
        validation_cap = (
            validation_count
            + caps.maximum_adaptive_rounds
            * caps.promotion_validation_draws_per_round
        )
    else:
        validation_count = caps.new_child_validation_draws_per_row
        validation_cap = (
            validation_count
            + caps.maximum_adaptive_rounds
            * caps.promotion_validation_draws_per_round
        )
    validation_request = wrapped.issue_request_v1(
        stream_identity=validation_stream,
        accepted_draw_start=1,
        accepted_draw_count=validation_count,
        accepted_draw_cap=validation_cap,
    )
    validations = [wrapped.execute_request_v1(validation_request)]
    for promotion_index in range(promotion_batches):
        promotion_request = wrapped.issue_request_v1(
            stream_identity=validation_stream,
            accepted_draw_start=(
                validation_count
                + promotion_index
                * caps.promotion_validation_draws_per_round
                + 1
            ),
            accepted_draw_count=caps.promotion_validation_draws_per_round,
            accepted_draw_cap=validation_cap,
        )
        validations.append(wrapped.execute_request_v1(promotion_request))
    replay = tuple(
        batch.verify_v075_construction_batched_observation_private_replay_v1(
            claimed=item,
            authority=private_authority,
            private_environment=private_fixture,
        )
        for item in (discovery, *validations)
    )
    child = (
        graph.V075SymbolicGraphStateV1(
            catalogue.context,
            selected.next_ranks,
            selected.failure,
        )
        if catalogue.remaining_horizon == 2
        else None
    )
    return (discovery, *validations), replay, child


def _complete_real_private_replay_batches(arm):
    namespace = _namespace(_MARKER)
    private_authority = _fixture(
        namespace,
        _MARKER + "-" + arm.value,
    )
    private_environment = _synthetic_environment()
    session = observer.open_construction_private_observer_fixture_v1(
        authority=private_authority,
        private_salt=_salt(_MARKER),
        private_environment=private_environment,
        observer_signer=_ConstructionSigner(),
        session_external_id=_id("session-" + arm.value),
    )
    wrapped = batch.wrap_v075_construction_batched_observer_session_v1(
        session
    )
    private_fixture = (
        batch.issue_v075_construction_batch_replay_environment_fixture_v1(
            namespace=namespace,
            private_salt=_salt(_MARKER),
            private_environment=private_environment,
        )
    )
    context = namespace.family.replicate_contexts[0]
    root = graph.root_catalogue_v1(context)
    batches = []
    replays = []
    children = {}
    for action_index, action in enumerate(root.actions):
        observed, replayed, child = _observe_row(
            namespace=namespace,
            wrapped=wrapped,
            private_authority=private_authority,
            private_fixture=private_fixture,
            catalogue=root,
            action=action,
            arm=arm,
            promotion_batches=(
                2
                if (
                    action_index == 0
                    and arm
                    is not worker.V075WorkerArmV1.MATCHED_DIRECT_GROUND
                )
                else 0
            ),
        )
        batches.extend(observed)
        replays.extend(replayed)
        assert child is not None
        children[child.state_id] = child
    first_child_action = True
    for child in (children[key] for key in sorted(children)):
        catalogue = graph.V075LegalActionCatalogueV1(
            context,
            child,
            1,
            graph.legal_action_triples_v1(
                context,
                child.ranks,
                child.failure,
            ),
        )
        for action in catalogue.actions:
            observed, replayed, terminal = _observe_row(
                namespace=namespace,
                wrapped=wrapped,
                private_authority=private_authority,
                private_fixture=private_fixture,
                catalogue=catalogue,
                action=action,
                arm=arm,
                promotion_batches=(
                    1
                    if (
                        first_child_action
                        and arm
                        is not worker.V075WorkerArmV1.MATCHED_DIRECT_GROUND
                    )
                    else 0
                ),
            )
            first_child_action = False
            batches.extend(observed)
            replays.extend(replayed)
            assert terminal is None
    return tuple(batches), tuple(replays)


@pytest.fixture(scope="module")
def adaptive_request():
    batches, replays = _complete_real_private_replay_batches(
        worker.V075WorkerArmV1.NO_PRIOR
    )
    request = native.freeze_v075_batch_native_backend_request_v1(
        arm=worker.V075WorkerArmV1.NO_PRIOR,
        occurrence_ordinal=1,
        batches=batches,
    )
    return request, replays


@pytest.fixture(scope="module")
def direct_request():
    batches, replays = _complete_real_private_replay_batches(
        worker.V075WorkerArmV1.MATCHED_DIRECT_GROUND
    )
    request = native.freeze_v075_batch_native_backend_request_v1(
        arm=worker.V075WorkerArmV1.MATCHED_DIRECT_GROUND,
        occurrence_ordinal=4,
        batches=batches,
    )
    return request, replays


def _request(value):
    return value[0]


def test_occurrence_identity_freezes_before_observation_without_target_access(
) -> None:
    namespace = _namespace("pre-sampling-occurrence-identity")
    context = namespace.family.replicate_contexts[1]
    thresholds = worker.V075WorkerThresholdProfileV1()
    caps = worker.V075WorkerCapProfileV1()
    first = native.freeze_v075_batch_native_occurrence_identity_v1(
        namespace=namespace,
        context=context,
        arm=worker.V075WorkerArmV1.NO_PRIOR,
        occurrence_ordinal=7,
        threshold_profile=thresholds,
        cap_profile=caps,
        source_prior_transport=None,
    )
    second = native.freeze_v075_batch_native_occurrence_identity_v1(
        namespace=namespace,
        context=context,
        arm=worker.V075WorkerArmV1.NO_PRIOR,
        occurrence_ordinal=7,
        threshold_profile=thresholds,
        cap_profile=caps,
        source_prior_transport=None,
    )
    document = first.to_document()
    assert first == second
    assert first.occurrence_id == second.occurrence_id
    assert document["occurrence_id"] == first.occurrence_id
    assert document["batch_count_at_freeze"] == 0
    assert document["observer_calls"] == 0
    assert document["kernel_calls"] == 0
    assert document["target_accessed"] is False
    assert "batches" not in document
    assert "outcomes" not in document


def test_backend_request_requires_the_exact_pre_sampling_occurrence_identity(
    adaptive_request,
) -> None:
    prior = _request(adaptive_request)
    identity = native.freeze_v075_batch_native_occurrence_identity_v1(
        namespace=prior.namespace,
        context=prior.context,
        arm=prior.arm,
        occurrence_ordinal=prior.occurrence_ordinal,
        threshold_profile=prior.threshold_profile,
        cap_profile=prior.cap_profile,
        source_prior_transport=prior.source_prior_transport,
    )
    rebound = native.freeze_v075_batch_native_backend_request_v1(
        arm=prior.arm,
        occurrence_ordinal=prior.occurrence_ordinal,
        batches=prior.batches,
        source_prior_transport=prior.source_prior_transport,
        occurrence_identity=identity,
    )
    assert rebound.occurrence_identity is identity
    assert rebound.occurrence_id == identity.occurrence_id
    assert (
        rebound.to_document()["occurrence_identity_id"]
        == identity.occurrence_id
    )

    with pytest.raises(
        native.V075BatchNativeBackendInvariantViolation,
        match="duck-typed occurrence identity",
    ):
        native.freeze_v075_batch_native_backend_request_v1(
            arm=prior.arm,
            occurrence_ordinal=prior.occurrence_ordinal,
            batches=prior.batches,
            occurrence_identity=object(),  # type: ignore[arg-type]
        )

    wrong_ordinal = native.freeze_v075_batch_native_occurrence_identity_v1(
        namespace=prior.namespace,
        context=prior.context,
        arm=prior.arm,
        occurrence_ordinal=prior.occurrence_ordinal + 1,
        threshold_profile=prior.threshold_profile,
        cap_profile=prior.cap_profile,
        source_prior_transport=prior.source_prior_transport,
    )
    with pytest.raises(
        native.V075BatchNativeBackendInvariantViolation,
        match="pre-sampling occurrence identity",
    ):
        native.freeze_v075_batch_native_backend_request_v1(
            arm=prior.arm,
            occurrence_ordinal=prior.occurrence_ordinal,
            batches=prior.batches,
            occurrence_identity=wrong_ordinal,
        )

    wrong_context = native.freeze_v075_batch_native_occurrence_identity_v1(
        namespace=prior.namespace,
        context=prior.namespace.family.replicate_contexts[1],
        arm=prior.arm,
        occurrence_ordinal=prior.occurrence_ordinal,
        threshold_profile=prior.threshold_profile,
        cap_profile=prior.cap_profile,
        source_prior_transport=prior.source_prior_transport,
    )
    with pytest.raises(
        native.V075BatchNativeBackendInvariantViolation,
        match="pre-sampling occurrence identity",
    ):
        native.freeze_v075_batch_native_backend_request_v1(
            arm=prior.arm,
            occurrence_ordinal=prior.occurrence_ordinal,
            batches=prior.batches,
            occurrence_identity=wrong_context,
        )

    with pytest.raises(
        native.V075BatchNativeBackendInvariantViolation,
        match="pre-sampling occurrence identity",
    ):
        native.V075BatchNativeOccurrenceIdentityV1(
            object(),
            identity.target_tape_namespace_id,
            identity.context_id,
            identity.arm,
            identity.occurrence_ordinal,
            identity.threshold_profile_id,
            identity.cap_profile_id,
            identity.source_transport_id,
        )


def test_real_private_replay_batch_graph_compiles_without_draw_expansion(
    adaptive_request,
) -> None:
    request, replays = adaptive_request
    result = native.compile_v075_batch_native_statistical_backend_v1(
        request
    )
    row_count = len(result.route_native_result.model.rows)
    assert row_count >= 4
    assert len(result.selected_batch_ids) == len(request.batches)
    assert len(replays) == len(request.batches)
    assert all(
        item.replayed_draw_count in {64, 2_048, 8_192}
        for item in replays
    )
    values = {item.path: item.value for item in result.work.counters}
    assert values["common.accepted_draws_consumed"] == sum(
        item.request.accepted_draw_count for item in request.batches
    )
    assert values["common.discovery_draws_consumed"] == row_count * 64
    assert values["common.validation_draws_consumed"] == sum(
        item.request.accepted_draw_count
        for item in request.batches
        if item.request.stream_identity.lane
        is graph.V075ObservationLaneV1.VALIDATION
    )
    assert (
        0
        < values["common.adaptive_cap_charged_incremental_draws"]
        < values["common.accepted_draws_consumed"]
    )
    assert values["common.aggregate_support_evidence_verified"] == row_count
    assert values["common.per_draw_capabilities_materialized"] == 0
    assert values["adaptive.route_attempts"] == 1
    assert result.to_document()["per_draw_capability_expansion"] is False
    assert len(result.aggregate_support_evidence_ids) == row_count


def test_aggregate_evidence_binds_actual_discovery_outcome_and_no_draw_index(
    adaptive_request,
) -> None:
    request = _request(adaptive_request)
    validation_batches = tuple(
        item
        for item in request.batches
        if item.request.stream_identity.lane
        is graph.V075ObservationLaneV1.VALIDATION
    )
    assert validation_batches
    for validation in validation_batches:
        evidence = (
            validation.request.stream_identity.pairing_authority
            .support_chain.leaf.evidence
        )
        assert len(evidence) == 1
        item = evidence[0]
        assert type(item) is graph.V075BatchAggregateSupportEvidenceV1
        discovery = next(
            batch_item
            for batch_item in request.batches
            if batch_item.batch_id == item.discovery_batch_id
        )
        outcome = next(
            outcome
            for outcome in discovery.outcomes
            if outcome.outcome_id == item.discovery_outcome_id
        )
        assert item.discovery_request_id == discovery.request.request_id
        assert item.discovery_outcome_count == outcome.count
        assert item.observed_state.ranks == outcome.next_ranks
        document = item.to_document()
        assert document["accepted_draw_index_serialized"] is False
        assert "accepted_draw_index" not in document


def test_support_other_and_exact_confidence_are_from_validation_aggregate(
    adaptive_request,
) -> None:
    request = _request(adaptive_request)
    result = native.compile_v075_batch_native_statistical_backend_v1(
        request
    )
    for row in result.route_native_result.model.rows:
        assert len(row.support) == 1
        assert row.validation_epoch_index == 1
        assert row.intervals[-1].event_key == "OTHER"
        draw_count = row.intervals[0].draw_count
        assert draw_count in {2_048, 6_144, 8_192, 10_240}
        assert sum(item.success_count for item in row.intervals) == draw_count
        assert all(item.draw_count == draw_count for item in row.intervals)
        assert all(
            item.lower_probability
            <= item.empirical_probability
            <= item.upper_probability
            for item in row.intervals
        )


def test_batch_native_output_feeds_support_and_abstract_planner(
    adaptive_request,
) -> None:
    request = _request(adaptive_request)
    result = native.compile_v075_batch_native_statistical_backend_v1(
        request
    )
    support = native.compile_v075_batch_native_support_graph_v1(result)
    planned = native.plan_v075_batch_native_route_v1(result)
    assert support.backend_result == result.route_native_result
    assert planned.route.value == "ADAPTIVE_QUOTIENT"
    assert planned.quotient is not None
    assert planned.to_document()["law_or_exact_atom_access"] is False


def test_matched_direct_route_stays_outside_quotient(direct_request) -> None:
    request, replays = direct_request
    result = native.compile_v075_batch_native_statistical_backend_v1(
        request
    )
    planned = native.plan_v075_batch_native_route_v1(result)
    assert replays
    assert planned.route.value == "MATCHED_DIRECT_GROUND"
    assert planned.quotient is None
    values = {item.path: item.value for item in result.work.counters}
    assert values["adaptive.route_attempts"] == 0
    assert values["direct.route_attempts"] == 1


def test_request_rejects_arm_transplant_and_missing_sequence(
    adaptive_request,
) -> None:
    request = _request(adaptive_request)
    with pytest.raises(
        native.V075BatchNativeBackendInvariantViolation,
        match="mixes namespace/context/arm/session",
    ):
        replace(
            request,
            arm=worker.V075WorkerArmV1.WRONG_CONSENSUS_PRIOR,
        )
    with pytest.raises(
        native.V075BatchNativeBackendInvariantViolation,
        match="sequence-verification registry",
    ):
        replace(
            request,
            sequence_verifications=request.sequence_verifications[1:],
        )


def test_partial_root_only_model_passes_but_partial_child_actions_fail(
    adaptive_request,
) -> None:
    request = _request(adaptive_request)
    root_id = graph.root_catalogue_v1(request.context).state.state_id
    root_batches = tuple(
        item
        for item in request.batches
        if item.request.stream_identity.row_binding.state_id == root_id
    )
    partial = native.freeze_v075_batch_native_backend_request_v1(
        arm=worker.V075WorkerArmV1.NO_PRIOR,
        occurrence_ordinal=2,
        batches=root_batches,
    )
    partial_result = (
        native.compile_v075_batch_native_statistical_backend_v1(partial)
    )
    partial_graph = native.compile_v075_batch_native_support_graph_v1(
        partial_result
    )
    assert partial_graph.active_child_state_ids == ()
    assert partial_graph.complete_modeled_h2_closure is False
    assert partial_graph.unmaterialized_root_support_descriptor_ids
    partial_plan = native.plan_v075_batch_native_route_v1(partial_result)
    assert partial_plan.status.value == "NO_RISK_FEASIBLE_POLICY"
    assert partial_plan.policy is not None
    assert partial_plan.ready_for_exact_total_lift is False

    child_batches = tuple(
        item
        for item in request.batches
        if item.request.stream_identity.row_binding.state_id != root_id
    )
    first_child = min(
        item.request.stream_identity.row_binding.state_id
        for item in child_batches
    )
    first_action = min(
        item.request.stream_identity.action
        for item in child_batches
        if item.request.stream_identity.row_binding.state_id == first_child
    )
    one_child_action = tuple(
        item
        for item in child_batches
        if (
            item.request.stream_identity.row_binding.state_id == first_child
            and item.request.stream_identity.action == first_action
        )
    )
    incomplete = native.freeze_v075_batch_native_backend_request_v1(
        arm=worker.V075WorkerArmV1.NO_PRIOR,
        occurrence_ordinal=3,
        batches=tuple((*root_batches, *one_child_action)),
    )
    with pytest.raises(
        native.V075BatchNativeBackendInvariantViolation,
        match="child action catalogue",
    ):
        native.compile_v075_batch_native_statistical_backend_v1(incomplete)


def test_result_identity_replay_and_tamper_fail(adaptive_request) -> None:
    request = _request(adaptive_request)
    result = native.compile_v075_batch_native_statistical_backend_v1(
        request
    )
    assert (
        native.verify_v075_batch_native_backend_result_v1(
            request=request,
            claimed_bytes=result.canonical_bytes,
        )
        == result
    )
    document = json.loads(result.canonical_bytes)
    document["production_integration_ready"] = True
    with pytest.raises(
        native.V075BatchNativeBackendInvariantViolation,
        match="recomputation",
    ):
        native.verify_v075_batch_native_backend_result_v1(
            request=request,
            claimed_bytes=canonical_json_bytes(document),
        )


def test_public_artifacts_expose_no_private_or_per_draw_material(
    adaptive_request,
) -> None:
    document = native.compile_v075_batch_native_statistical_backend_v1(
        _request(adaptive_request)
    ).to_document()
    keys = set()

    def walk(value):
        if isinstance(value, dict):
            keys.update(value)
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(document)
    assert keys.isdisjoint(
        {
            "law",
            "secret_laws",
            "environment_reveal",
            "salt",
            "private_signer",
            "random_words",
            "seed",
            "kernel",
            "exact_atoms",
            "accepted_draw_index",
        }
    )
    assert document["private_material_serialized"] is False
