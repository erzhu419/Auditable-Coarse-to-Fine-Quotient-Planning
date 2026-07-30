from __future__ import annotations

from dataclasses import replace
from fractions import Fraction
import hashlib
import inspect

import pytest

from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp import v075_batch_native_statistical_backend_v1 as identity_backend
from acfqp import v075_batch_occurrence_lifecycle_authority_v2 as lifecycle
from acfqp import v075_batched_observer_authority_v2 as batched
from acfqp import v075_private_observer_boundary_v2 as observer
from acfqp import v075_public_graph_semantics_v1 as graph
from acfqp import v075_registered_occurrence_worker_v1 as worker
from tests import test_v075_private_observer_boundary_v2 as observer_fixture


def _id(label: str) -> str:
    return hashlib.sha256(
        b"acfqp:v075-batch-lifecycle-v2-test:v1"
        + b"\x00"
        + label.encode("utf-8")
    ).hexdigest()


def _domain_hash(domain: str, payload) -> str:
    return hashlib.sha256(
        domain.encode("utf-8")
        + b"\x00"
        + canonical_json_bytes(payload)
    ).hexdigest()


def _flip_signature(value: str) -> str:
    return ("0" if value[0] != "0" else "1") + value[1:]


def _discovery_stream(namespace, catalogue, action):
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
        arm=worker.V075WorkerArmV1.NO_PRIOR.value,
    )


def _support_evidence(namespace, signer, stream, batch):
    representatives = {}
    for outcome in batch.outcomes:
        state = graph.V075SymbolicGraphStateV1(
            stream.row_binding.context,
            outcome.next_ranks,
            outcome.failure,
        )
        current = representatives.get(state.state_id)
        if current is None or outcome.outcome_id < current.outcome_id:
            representatives[state.state_id] = outcome
    result = []
    for state_id in sorted(representatives):
        outcome = representatives[state_id]
        state = graph.V075SymbolicGraphStateV1(
            stream.row_binding.context,
            outcome.next_ranks,
            outcome.failure,
        )
        message = graph.batch_aggregate_support_evidence_signing_bytes_v1(
            namespace=namespace,
            row_binding=stream.row_binding,
            observed_state=state,
            source_observer_epoch_index=0,
            discovery_request_id=batch.request.request_id,
            discovery_batch_id=batch.batch_id,
            discovery_outcome_id=outcome.outcome_id,
            discovery_outcome_count=outcome.count,
        )
        result.append(
            graph.bind_batch_aggregate_support_evidence_v1(
                namespace=namespace,
                row_binding=stream.row_binding,
                observed_state=state,
                source_observer_epoch_index=0,
                discovery_request_id=batch.request.request_id,
                discovery_batch_id=batch.batch_id,
                discovery_outcome_id=outcome.outcome_id,
                discovery_outcome_count=outcome.count,
                observer_signature_hex=(
                    signer.sign_observer_evidence_v1(message)
                ),
            )
        )
    return tuple(result)


def _validation_stream(namespace, discovery, evidence):
    row = discovery.row_binding
    bootstrap = discovery.pairing_authority.support_chain.leaf
    promoted = graph.derive_shared_support_epoch_v1(
        namespace=namespace,
        row_binding=row,
        epoch_index=1,
        evidence=evidence,
        parent=bootstrap,
    )
    chain = graph.freeze_shared_support_chain_v1(
        namespace=namespace,
        row_binding=row,
        epochs=(bootstrap, promoted),
    )
    pairing = graph.freeze_five_arm_pairing_authority_v1(
        namespace=namespace,
        row_binding=row,
        support_chain=chain,
    )
    return graph.derive_transition_stream_identity_v1(
        pairing_authority=pairing,
        arm=worker.V075WorkerArmV1.NO_PRIOR.value,
    )


def _fully_rehash_forged_production_graph(lineage_raw, closure_raw):
    closure = loads_canonical_json(closure_raw)
    first_batch = closure["entries"][0]["batch"]
    first_batch["observer_signature_hex"] = _flip_signature(
        first_batch["observer_signature_hex"]
    )
    batch_payload = {
        key: value
        for key, value in first_batch.items()
        if key
        not in {
            "request",
            "outcomes",
            "observer_signature_hex",
            "observer_signature_verified",
            "batch_id",
        }
    }
    first_batch["batch_id"] = _domain_hash(
        observer.DOMAIN_TAGS["batch_artifact"],
        {
            **batch_payload,
            "observer_signature_hex": first_batch["observer_signature_hex"],
            "observer_signature_verified": True,
        },
    )
    entry_ids = []
    batch_ids = []
    previous = None
    for entry in closure["entries"]:
        entry["previous_entry_id"] = previous
        entry["batch_id"] = entry["batch"]["batch_id"]
        entry_payload = {
            key: value
            for key, value in entry.items()
            if key not in {"batch", "entry_id"}
        }
        entry["entry_id"] = _domain_hash(
            observer.DOMAIN_TAGS["batch_journal_entry"],
            entry_payload,
        )
        previous = entry["entry_id"]
        entry_ids.append(previous)
        batch_ids.append(entry["batch_id"])
    closure["entry_ids"] = entry_ids
    closure["batch_ids"] = batch_ids
    closure["tail_entry_id"] = entry_ids[-1]
    closure_payload = {
        key: value
        for key, value in closure.items()
        if key
        not in {
            "observer_open_binding",
            "entries",
            "observer_signature_hex",
            "observer_signature_verified",
            "closure_id",
        }
    }
    closure["closure_id"] = _domain_hash(
        observer.DOMAIN_TAGS["batch_journal_closure_artifact"],
        {
            **closure_payload,
            "observer_signature_hex": closure["observer_signature_hex"],
            "observer_signature_verified": True,
        },
    )
    forged_closure_raw = canonical_json_bytes(closure)

    lineage_document = loads_canonical_json(lineage_raw)
    lineage_document["scope"] = "PRODUCTION_BYTE_REPLAY"
    lineage_document["production_authority_bytes_replayed"] = True
    lineage_document["closure_id"] = closure["closure_id"]
    lineage_document["closure_bytes_sha256"] = hashlib.sha256(
        forged_closure_raw
    ).hexdigest()
    lineage_document["journal_entry_ids"] = entry_ids
    lineage_document["batch_ids"] = batch_ids
    lineage_payload = dict(lineage_document)
    lineage_payload.pop("lineage_id")
    lineage_document["lineage_id"] = _domain_hash(
        batched.DOMAIN_TAGS["occurrence_lineage"],
        lineage_payload,
    )
    return canonical_json_bytes(lineage_document), forged_closure_raw


def _identity_for_graph(values, *, ordinal: int):
    namespace = values["namespace"]
    context = namespace.family.replicate_contexts[0]
    return (
        identity_backend
        .freeze_v075_batch_native_occurrence_identity_from_namespace_v2(
            namespace=namespace,
            context=context,
            arm=worker.V075WorkerArmV1.NO_PRIOR,
            occurrence_ordinal=ordinal,
            threshold_profile=namespace.workload.threshold_profile,
            cap_profile=namespace.workload.cap_profile,
            source_prior_transport=None,
        )
    )


def _adapter_for_graph(values, identity, marker):
    binding = observer._require_exact_v2_binding(  # noqa: SLF001
        authority=values["authorization"],
        namespace=values["namespace"],
    )
    session = observer._open_private_observer_from_verified_gate_v2(  # noqa: SLF001
        authority=values["authorization"],
        namespace=values["namespace"],
        binding=binding,
        private_salt=values["salt"],
        private_environment=(
            values["generated"].secret_laws_for_commitment()
        ),
        observer_signer=values["signer"],
        session_external_id=_id(marker),
    )
    return batched.bind_v075_construction_occurrence_batched_observer_v2(
        session=session,
        occurrence_identity=identity,
    )


@pytest.fixture(scope="module")
def lifecycle_graph():
    generated, salt, namespace, authorization, signer = (
        observer_fixture._fixture("batch-lifecycle-v2")
    )
    context = namespace.family.replicate_contexts[0]
    identity = (
        identity_backend
        .freeze_v075_batch_native_occurrence_identity_from_namespace_v2(
            namespace=namespace,
            context=context,
            arm=worker.V075WorkerArmV1.NO_PRIOR,
            occurrence_ordinal=0,
            threshold_profile=namespace.workload.threshold_profile,
            cap_profile=namespace.workload.cap_profile,
            source_prior_transport=None,
        )
    )
    binding = observer._require_exact_v2_binding(  # noqa: SLF001
        authority=authorization,
        namespace=namespace,
    )
    session = observer._open_private_observer_from_verified_gate_v2(  # noqa: SLF001
        authority=authorization,
        namespace=namespace,
        binding=binding,
        private_salt=salt,
        private_environment=generated.secret_laws_for_commitment(),
        observer_signer=signer,
        session_external_id=_id("session"),
    )
    adapter = batched.bind_v075_construction_occurrence_batched_observer_v2(
        session=session,
        occurrence_identity=identity,
    )
    catalogue = graph.root_catalogue_v1(context)
    action = catalogue.actions[0]
    discovery = _discovery_stream(
        namespace,
        catalogue,
        action,
    )
    discovery_batch = adapter.observe_batch_v2(
        stream_identity=discovery,
        accepted_draw_start=1,
        accepted_draw_count=64,
        accepted_draw_cap=64,
    )
    old_model_evidence = _support_evidence(
        namespace,
        signer,
        discovery,
        discovery_batch,
    )
    validation = _validation_stream(
        namespace,
        discovery,
        old_model_evidence,
    )
    validation_batch = adapter.observe_batch_v2(
        stream_identity=validation,
        accepted_draw_start=1,
        accepted_draw_count=64,
        accepted_draw_cap=64,
    )
    batch_closure = adapter.close_v2()
    lineage_value = batched.freeze_v075_construction_batch_occurrence_lineage_v2(
        occurrence_identity=identity,
        closure=batch_closure,
        authority=authorization,
        namespace=namespace,
        known_stream_identities=(discovery, validation),
        private_salt=salt,
        private_environment=generated.secret_laws_for_commitment(),
    )
    lifecycle_value = (
        lifecycle.freeze_v075_construction_batch_occurrence_lifecycle_v2(
            lineage=lineage_value,
            lineage_bytes=lineage_value.canonical_bytes,
            batch_closure_bytes=batch_closure.canonical_bytes,
        )
    )
    return {
        "generated": generated,
        "salt": salt,
        "namespace": namespace,
        "authorization": authorization,
        "signer": signer,
        "identity": identity,
        "discovery": discovery,
        "validation": validation,
        "discovery_batch": discovery_batch,
        "validation_batch": validation_batch,
        "batch_closure": batch_closure,
        "lineage": lineage_value,
        "lifecycle": lifecycle_value,
    }


def test_deterministic_v2_support_freeze_and_bytes_only_replay(
    lifecycle_graph,
) -> None:
    value = lifecycle_graph["lifecycle"]
    lineage_value = lifecycle_graph["lineage"]
    batch_closure = lifecycle_graph["batch_closure"]
    replayed, verification = (
        lifecycle.verify_v075_batch_occurrence_lifecycle_bytes_v2(
            lifecycle_bytes=value.canonical_bytes,
            lineage_bytes=lineage_value.canonical_bytes,
            batch_closure_bytes=batch_closure.canonical_bytes,
            known_stream_identities=(
                lifecycle_graph["discovery"],
                lifecycle_graph["validation"],
            ),
        )
    )

    assert replayed == value
    assert verification.lifecycle_closure_id == value.closure_id
    assert len(value.support_freezes) == 1
    assert value.support_freezes[0].validation_epoch_index == 1
    assert value.support_freezes[0].source_discovery_batch_ids == (
        lifecycle_graph["discovery_batch"].batch_id,
    )
    assert len(value.support_evidence) == len(
        lifecycle_graph["discovery_batch"].outcomes
    )
    assert tuple(event.kind.value for event in value.events) == (
        "DISCOVERY_BATCH",
        "SUPPORT_FREEZE",
        "VALIDATION_BATCH",
    )
    assert value.to_document()["per_draw_record_count"] == 0
    assert value.terminal_code is (
        lifecycle.V075BatchLifecycleTerminalCodeV2
        .COMPLETE_OBSERVED_REQUIRED_ROWS_CONSTRUCTION_CONTROL
    )
    assert (
        value.to_document()[
            "complete_observed_row_round_schedule_covered"
        ]
        is True
    )
    assert (
        value.to_document()["preregistered_schedule_authority_integrated"]
        is False
    )
    assert value.to_document()["plan_certificate"] is False
    assert value.to_document()["infeasibility_certificate"] is False


def test_validation_before_same_row_freeze_fails_closed() -> None:
    generated, salt, namespace, authorization, signer = (
        observer_fixture._fixture("validation-before-freeze")
    )
    context = namespace.family.replicate_contexts[0]
    identity = (
        identity_backend
        .freeze_v075_batch_native_occurrence_identity_from_namespace_v2(
            namespace=namespace,
            context=context,
            arm=worker.V075WorkerArmV1.NO_PRIOR,
            occurrence_ordinal=1,
            threshold_profile=namespace.workload.threshold_profile,
            cap_profile=namespace.workload.cap_profile,
            source_prior_transport=None,
        )
    )
    binding = observer._require_exact_v2_binding(  # noqa: SLF001
        authority=authorization,
        namespace=namespace,
    )
    # A separate construction session produces a syntactically valid public
    # support model.  It is deliberately absent from the tested occurrence.
    source_session = observer._open_private_observer_from_verified_gate_v2(  # noqa: SLF001
        authority=authorization,
        namespace=namespace,
        binding=binding,
        private_salt=salt,
        private_environment=generated.secret_laws_for_commitment(),
        observer_signer=signer,
        session_external_id=_id("foreign-source-session"),
    )
    source_adapter = (
        batched.bind_v075_construction_occurrence_batched_observer_v2(
            session=source_session,
            occurrence_identity=identity,
        )
    )
    catalogue = graph.root_catalogue_v1(context)
    discovery = _discovery_stream(
        namespace,
        catalogue,
        catalogue.actions[0],
    )
    source_batch = source_adapter.observe_batch_v2(
        stream_identity=discovery,
        accepted_draw_start=1,
        accepted_draw_count=8,
        accepted_draw_cap=8,
    )
    evidence = _support_evidence(
        namespace,
        signer,
        discovery,
        source_batch,
    )
    validation = _validation_stream(
        namespace,
        discovery,
        evidence,
    )

    tested_session = observer._open_private_observer_from_verified_gate_v2(  # noqa: SLF001
        authority=authorization,
        namespace=namespace,
        binding=binding,
        private_salt=salt,
        private_environment=generated.secret_laws_for_commitment(),
        observer_signer=signer,
        session_external_id=_id("tested-validation-session"),
    )
    adapter = batched.bind_v075_construction_occurrence_batched_observer_v2(
        session=tested_session,
        occurrence_identity=identity,
    )
    adapter.observe_batch_v2(
        stream_identity=validation,
        accepted_draw_start=1,
        accepted_draw_count=8,
        accepted_draw_cap=8,
    )
    closure = adapter.close_v2()
    lineage_value = batched.freeze_v075_construction_batch_occurrence_lineage_v2(
        occurrence_identity=identity,
        closure=closure,
        authority=authorization,
        namespace=namespace,
        known_stream_identities=(validation,),
        private_salt=salt,
        private_environment=generated.secret_laws_for_commitment(),
    )
    with pytest.raises(
        lifecycle.V075BatchOccurrenceLifecycleV2InvariantViolation,
        match="before any same-row DISCOVERY",
    ):
        lifecycle.freeze_v075_construction_batch_occurrence_lifecycle_v2(
            lineage=lineage_value,
            lineage_bytes=lineage_value.canonical_bytes,
            batch_closure_bytes=closure.canonical_bytes,
        )


def test_local_discovery_with_foreign_typed_support_is_rejected(
    lifecycle_graph,
) -> None:
    identity = _identity_for_graph(lifecycle_graph, ordinal=2)
    namespace = lifecycle_graph["namespace"]
    context = namespace.family.replicate_contexts[0]
    catalogue = graph.root_catalogue_v1(context)
    discovery = _discovery_stream(
        namespace,
        catalogue,
        catalogue.actions[0],
    )

    foreign_adapter = _adapter_for_graph(
        lifecycle_graph,
        identity,
        "foreign-support-source",
    )
    foreign_batch = foreign_adapter.observe_batch_v2(
        stream_identity=discovery,
        accepted_draw_start=1,
        accepted_draw_count=16,
        accepted_draw_cap=16,
    )
    foreign_evidence = _support_evidence(
        namespace,
        lifecycle_graph["signer"],
        discovery,
        foreign_batch,
    )
    validation = _validation_stream(
        namespace,
        discovery,
        foreign_evidence,
    )

    adapter = _adapter_for_graph(
        lifecycle_graph,
        identity,
        "local-with-foreign-support",
    )
    adapter.observe_batch_v2(
        stream_identity=discovery,
        accepted_draw_start=1,
        accepted_draw_count=16,
        accepted_draw_cap=16,
    )
    adapter.observe_batch_v2(
        stream_identity=validation,
        accepted_draw_start=1,
        accepted_draw_count=16,
        accepted_draw_cap=16,
    )
    closure = adapter.close_v2()
    lineage_value = batched.freeze_v075_construction_batch_occurrence_lineage_v2(
        occurrence_identity=identity,
        closure=closure,
        authority=lifecycle_graph["authorization"],
        namespace=namespace,
        known_stream_identities=(discovery, validation),
        private_salt=lifecycle_graph["salt"],
        private_environment=(
            lifecycle_graph["generated"].secret_laws_for_commitment()
        ),
    )
    with pytest.raises(
        lifecycle.V075BatchOccurrenceLifecycleV2InvariantViolation,
        match="foreign, incomplete",
    ):
        lifecycle.freeze_v075_construction_batch_occurrence_lifecycle_v2(
            lineage=lineage_value,
            lineage_bytes=lineage_value.canonical_bytes,
            batch_closure_bytes=closure.canonical_bytes,
        )


def test_complete_rejects_two_discovery_rows_with_one_validation(
    lifecycle_graph,
) -> None:
    identity = _identity_for_graph(lifecycle_graph, ordinal=3)
    namespace = lifecycle_graph["namespace"]
    context = namespace.family.replicate_contexts[0]
    catalogue = graph.root_catalogue_v1(context)
    assert len(catalogue.actions) >= 2
    adapter = _adapter_for_graph(
        lifecycle_graph,
        identity,
        "incomplete-required-rows",
    )
    discoveries = tuple(
        _discovery_stream(
            namespace,
            catalogue,
            action,
        )
        for action in catalogue.actions[:2]
    )
    batches = tuple(
        adapter.observe_batch_v2(
            stream_identity=stream,
            accepted_draw_start=1,
            accepted_draw_count=16,
            accepted_draw_cap=16,
        )
        for stream in discoveries
    )
    evidence = _support_evidence(
        namespace,
        lifecycle_graph["signer"],
        discoveries[0],
        batches[0],
    )
    validation = _validation_stream(
        namespace,
        discoveries[0],
        evidence,
    )
    adapter.observe_batch_v2(
        stream_identity=validation,
        accepted_draw_start=1,
        accepted_draw_count=16,
        accepted_draw_cap=16,
    )
    closure = adapter.close_v2()
    lineage_value = batched.freeze_v075_construction_batch_occurrence_lineage_v2(
        occurrence_identity=identity,
        closure=closure,
        authority=lifecycle_graph["authorization"],
        namespace=namespace,
        known_stream_identities=(*discoveries, validation),
        private_salt=lifecycle_graph["salt"],
        private_environment=(
            lifecycle_graph["generated"].secret_laws_for_commitment()
        ),
    )
    with pytest.raises(
        lifecycle.V075BatchOccurrenceLifecycleV2InvariantViolation,
        match="every required discovery row",
    ):
        lifecycle.freeze_v075_construction_batch_occurrence_lifecycle_v2(
            lineage=lineage_value,
            lineage_bytes=lineage_value.canonical_bytes,
            batch_closure_bytes=closure.canonical_bytes,
        )


def test_gap_overlap_and_cross_round_support_transplant_attacks_fail(
    lifecycle_graph,
) -> None:
    value = lifecycle_graph["lifecycle"]
    lineage_raw = lifecycle_graph["lineage"].canonical_bytes
    closure_raw = lifecycle_graph["batch_closure"].canonical_bytes

    gap_document = loads_canonical_json(closure_raw)
    gap_document["entries"][1]["batch"]["request"][
        "accepted_draw_start"
    ] = 2
    gap_raw = canonical_json_bytes(gap_document)
    with pytest.raises(
        lifecycle.V075BatchOccurrenceLifecycleV2InvariantViolation
    ):
        lifecycle.verify_v075_batch_occurrence_lifecycle_bytes_v2(
            lifecycle_bytes=value.canonical_bytes,
            lineage_bytes=lineage_raw,
            batch_closure_bytes=gap_raw,
            known_stream_identities=(
                lifecycle_graph["discovery"],
                lifecycle_graph["validation"],
            ),
        )

    transplant_document = loads_canonical_json(closure_raw)
    transplant_document["entries"][1]["batch"]["request"][
        "observer_epoch_index"
    ] = 2
    transplant_document["entries"][1]["batch"][
        "observer_epoch_index"
    ] = 2
    transplant_raw = canonical_json_bytes(transplant_document)
    with pytest.raises(
        lifecycle.V075BatchOccurrenceLifecycleV2InvariantViolation
    ):
        lifecycle.verify_v075_batch_occurrence_lifecycle_bytes_v2(
            lifecycle_bytes=value.canonical_bytes,
            lineage_bytes=lineage_raw,
            batch_closure_bytes=transplant_raw,
            known_stream_identities=(
                lifecycle_graph["discovery"],
                lifecycle_graph["validation"],
            ),
        )


def test_caller_minted_closure_object_is_not_a_verifier_input(
    lifecycle_graph,
) -> None:
    original = lifecycle_graph["lifecycle"]
    forged = object.__new__(
        lifecycle.V075BatchOccurrenceLifecycleClosureV2
    )
    object.__setattr__(forged, "_closure_id", original.closure_id)
    replayed, _verification = (
        lifecycle.verify_v075_batch_occurrence_lifecycle_bytes_v2(
            lifecycle_bytes=original.canonical_bytes,
            lineage_bytes=lifecycle_graph["lineage"].canonical_bytes,
            batch_closure_bytes=(
                lifecycle_graph["batch_closure"].canonical_bytes
            ),
            known_stream_identities=(
                lifecycle_graph["discovery"],
                lifecycle_graph["validation"],
            ),
        )
    )
    assert replayed is not forged
    assert replayed == original


def test_signature_replacement_with_full_rehash_cannot_claim_production(
    lifecycle_graph,
    monkeypatch,
) -> None:
    forged_lineage, forged_closure = _fully_rehash_forged_production_graph(
        lifecycle_graph["lineage"].canonical_bytes,
        lifecycle_graph["batch_closure"].canonical_bytes,
    )
    with pytest.raises(
        lifecycle.V075BatchOccurrenceLifecycleV2InvariantViolation,
        match="construction derivation rejects production",
    ):
        lifecycle.verify_v075_batch_occurrence_lifecycle_bytes_v2(
            lifecycle_bytes=lifecycle_graph["lifecycle"].canonical_bytes,
            lineage_bytes=forged_lineage,
            batch_closure_bytes=forged_closure,
            known_stream_identities=(
                lifecycle_graph["discovery"],
                lifecycle_graph["validation"],
            ),
        )

    def reject_unexpected_upstream_call(**_kwargs):
        raise AssertionError("locked production verifier called upstream")

    monkeypatch.setattr(
        batched,
        "freeze_v075_production_batch_occurrence_lineage_v2",
        reject_unexpected_upstream_call,
    )
    with pytest.raises(
        lifecycle.V075ProductionPositiveLifecycleV2NotReady,
        match="preregistered acquisition",
    ):
        lifecycle.verify_v075_production_batch_occurrence_lifecycle_v2(
            lifecycle_bytes=lifecycle_graph["lifecycle"].canonical_bytes,
            lineage_bytes=forged_lineage,
            batch_closure_bytes=forged_closure,
            repository_root=".",
            occurrence_identity=lifecycle_graph["identity"],
            private_reveal_attestation_bytes=b"x",
            claimed_authorization_bytes=b"x",
            namespace_bytes=b"x",
            known_stream_identities=(
                lifecycle_graph["discovery"],
                lifecycle_graph["validation"],
            ),
            private_salt=b"x",
            private_environment=(),
        )


def test_omitted_preregistered_stream_cannot_claim_production_complete(
    lifecycle_graph,
    monkeypatch,
) -> None:
    def reject_unexpected_upstream_call(**_kwargs):
        raise AssertionError("locked production verifier called upstream")

    monkeypatch.setattr(
        batched,
        "freeze_v075_production_batch_occurrence_lineage_v2",
        reject_unexpected_upstream_call,
    )
    with pytest.raises(
        lifecycle.V075ProductionPositiveLifecycleV2NotReady,
        match="preregistered acquisition",
    ):
        lifecycle.verify_v075_production_batch_occurrence_lifecycle_v2(
            lifecycle_bytes=lifecycle_graph["lifecycle"].canonical_bytes,
            lineage_bytes=lifecycle_graph["lineage"].canonical_bytes,
            batch_closure_bytes=(
                lifecycle_graph["batch_closure"].canonical_bytes
            ),
            repository_root=".",
            occurrence_identity=lifecycle_graph["identity"],
            private_reveal_attestation_bytes=b"x",
            claimed_authorization_bytes=b"x",
            namespace_bytes=b"x",
            # The validation stream is deliberately omitted.  Observed
            # discovery alone cannot stand in for a preregistered schedule.
            known_stream_identities=(lifecycle_graph["discovery"],),
            private_salt=b"x",
            private_environment=(),
        )


@pytest.mark.parametrize(
    ("code", "kwargs"),
    (
        (
            lifecycle.V075BatchFailureTerminalCodeV2.CAP_EXHAUSTED,
            {"cap_profile_id": _id("cap")},
        ),
        (
            lifecycle.V075BatchFailureTerminalCodeV2.PROTOCOL_FAILURE,
            {"violation_id": _id("protocol")},
        ),
        (
            lifecycle.V075BatchFailureTerminalCodeV2.INTEGRITY_FAILURE,
            {"violation_id": _id("integrity")},
        ),
        (
            lifecycle.V075BatchFailureTerminalCodeV2
            .POLICY_ABORT_NONCERTIFICATE,
            {
                "policy_abort_failure_probability": Fraction(1, 64),
                "use_lifecycle": True,
            },
        ),
    ),
)
def test_four_failure_codes_are_exclusive_and_never_certificates(
    lifecycle_graph,
    code,
    kwargs,
) -> None:
    options = dict(kwargs)
    use_lifecycle = options.pop("use_lifecycle", False)
    lifecycle_raw = (
        lifecycle_graph["lifecycle"].canonical_bytes
        if use_lifecycle
        else None
    )
    value = lifecycle.freeze_v075_batch_occurrence_failure_closure_v2(
        lineage_bytes=lifecycle_graph["lineage"].canonical_bytes,
        batch_closure_bytes=(
            lifecycle_graph["batch_closure"].canonical_bytes
        ),
        terminal_code=code,
        abort_stage="TOTAL_LIFT" if use_lifecycle else "ACQUISITION",
        observed_batch_count=2,
        source_artifact_ids=(_id("source"),),
        work_artifact_ids=(_id("work"),),
        known_stream_identities=(
            lifecycle_graph["discovery"],
            lifecycle_graph["validation"],
        ),
        lifecycle_bytes=lifecycle_raw,
        **options,
    )
    replayed, verification = (
        lifecycle.verify_v075_batch_occurrence_failure_bytes_v2(
            failure_bytes=value.canonical_bytes,
            lineage_bytes=lifecycle_graph["lineage"].canonical_bytes,
            batch_closure_bytes=(
                lifecycle_graph["batch_closure"].canonical_bytes
            ),
            known_stream_identities=(
                lifecycle_graph["discovery"],
                lifecycle_graph["validation"],
            ),
            lifecycle_bytes=lifecycle_raw,
        )
    )
    assert replayed == value
    assert verification.terminal_code is code
    document = value.to_document()
    assert document["terminal_class"] == "ATTEMPT_CLOSURE_NONCERTIFICATE"
    assert document["plan_certificate"] is False
    assert document["infeasibility_certificate"] is False
    populated = {
        name
        for name in (
            "cap_profile_id",
            "violation_id",
            "lifecycle_closure_id",
            "policy_abort_failure_probability",
        )
        if document[name] is not None
    }
    expected = {
        lifecycle.V075BatchFailureTerminalCodeV2.CAP_EXHAUSTED: {
            "cap_profile_id"
        },
        lifecycle.V075BatchFailureTerminalCodeV2.PROTOCOL_FAILURE: {
            "violation_id"
        },
        lifecycle.V075BatchFailureTerminalCodeV2.INTEGRITY_FAILURE: {
            "violation_id"
        },
        lifecycle.V075BatchFailureTerminalCodeV2
        .POLICY_ABORT_NONCERTIFICATE: {
            "lifecycle_closure_id",
            "policy_abort_failure_probability",
        },
    }[code]
    assert populated == expected


def test_failure_code_field_mixing_is_rejected(lifecycle_graph) -> None:
    with pytest.raises(
        lifecycle.V075BatchOccurrenceLifecycleV2InvariantViolation,
        match="code-specific",
    ):
        lifecycle.freeze_v075_batch_occurrence_failure_closure_v2(
            lineage_bytes=lifecycle_graph["lineage"].canonical_bytes,
            batch_closure_bytes=(
                lifecycle_graph["batch_closure"].canonical_bytes
            ),
            terminal_code=(
                lifecycle.V075BatchFailureTerminalCodeV2.CAP_EXHAUSTED
            ),
            abort_stage="ACQUISITION",
            observed_batch_count=1,
            source_artifact_ids=(_id("mixed-source"),),
            work_artifact_ids=(_id("mixed-work"),),
            known_stream_identities=(
                lifecycle_graph["discovery"],
                lifecycle_graph["validation"],
            ),
            cap_profile_id=_id("mixed-cap"),
            violation_id=_id("mixed-violation"),
        )


def test_construction_parsers_reject_unknown_and_private_fields(
    lifecycle_graph,
) -> None:
    lineage_document = loads_canonical_json(
        lifecycle_graph["lineage"].canonical_bytes
    )
    lineage_document["private_law"] = {"forbidden": True}
    with pytest.raises(
        lifecycle.V075BatchOccurrenceLifecycleV2InvariantViolation,
        match="unknown, or private",
    ):
        lifecycle.verify_v075_batch_occurrence_lifecycle_bytes_v2(
            lifecycle_bytes=lifecycle_graph["lifecycle"].canonical_bytes,
            lineage_bytes=canonical_json_bytes(lineage_document),
            batch_closure_bytes=(
                lifecycle_graph["batch_closure"].canonical_bytes
            ),
            known_stream_identities=(
                lifecycle_graph["discovery"],
                lifecycle_graph["validation"],
            ),
        )

    closure_document = loads_canonical_json(
        lifecycle_graph["batch_closure"].canonical_bytes
    )
    closure_document["entries"][0]["batch"]["outcomes"][0][
        "individual_random_words"
    ] = [1]
    with pytest.raises(
        lifecycle.V075BatchOccurrenceLifecycleV2InvariantViolation,
        match="unknown, or private",
    ):
        lifecycle.verify_v075_batch_occurrence_lifecycle_bytes_v2(
            lifecycle_bytes=lifecycle_graph["lifecycle"].canonical_bytes,
            lineage_bytes=lifecycle_graph["lineage"].canonical_bytes,
            batch_closure_bytes=canonical_json_bytes(closure_document),
            known_stream_identities=(
                lifecycle_graph["discovery"],
                lifecycle_graph["validation"],
            ),
        )


def test_production_failure_is_explicitly_locked_and_construction_is_dev_only(
    lifecycle_graph,
) -> None:
    assert lifecycle.PRODUCTION_FAILURE_AUTHORITY_READY is False
    with pytest.raises(
        lifecycle.V075ProductionFailureAuthorityV2NotReady,
        match="cap, violation, work",
    ):
        lifecycle.verify_v075_production_batch_occurrence_failure_v2(
            failure_bytes=b"claim",
            lineage_bytes=b"claim",
            batch_closure_bytes=b"claim",
            lifecycle_bytes=None,
            repository_root=".",
            occurrence_identity=lifecycle_graph["identity"],
            private_reveal_attestation_bytes=b"claim",
            claimed_authorization_bytes=b"claim",
            namespace_bytes=b"claim",
            known_stream_identities=(),
            private_salt=b"claim",
            private_environment=(),
        )

    value = lifecycle.freeze_v075_batch_occurrence_failure_closure_v2(
        lineage_bytes=lifecycle_graph["lineage"].canonical_bytes,
        batch_closure_bytes=(
            lifecycle_graph["batch_closure"].canonical_bytes
        ),
        terminal_code=(
            lifecycle.V075BatchFailureTerminalCodeV2.PROTOCOL_FAILURE
        ),
        abort_stage="DEVELOPMENT_CONTROL",
        observed_batch_count=1,
        source_artifact_ids=(_id("dev-source"),),
        work_artifact_ids=(_id("dev-work"),),
        known_stream_identities=(
            lifecycle_graph["discovery"],
            lifecycle_graph["validation"],
        ),
        violation_id=_id("dev-violation"),
    )
    document = value.to_document()
    assert document["scope"] == "CONSTRUCTION_ONLY"
    assert document["development_scope_only"] is True
    assert document["production_verified"] is False


def test_construction_and_production_content_domains_are_disjoint() -> None:
    assert (
        lifecycle.DOMAIN_TAGS["construction_lifecycle"]
        != lifecycle.DOMAIN_TAGS["production_lifecycle"]
    )
    assert (
        lifecycle.DOMAIN_TAGS["construction_failure"]
        != lifecycle.DOMAIN_TAGS["production_failure"]
    )
    assert lifecycle.PRODUCTION_POSITIVE_PATH_READY is False


def test_leaf_has_no_legacy_observer_projection_or_target_access() -> None:
    source = inspect.getsource(lifecycle)
    assert "v075_private_observer_boundary_v1" not in source
    assert "v075_batched_observer_authority_v1" not in source
    assert "v075_public_target_tape_namespace_v1" not in source
    assert ".observe_v2(" not in source
    assert "open_private_observer" not in source
    assert lifecycle.PER_DRAW_EXPANSION_ALLOWED is False
    assert lifecycle.TARGET_ACCESS_ALLOWED is False
    assert lifecycle.OFFICIAL_EXECUTION_ALLOWED is False
    assert lifecycle.SCIENTIFIC_ENDPOINT_CREDIT_ALLOWED is False
