from __future__ import annotations

import ast
from dataclasses import replace
from fractions import Fraction
import hashlib
import inspect
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

import pytest

from acfqp.phase3e_ids import canonical_json_bytes
from acfqp import v075_frozen_source_proposal_archive_v1 as source_archive
from acfqp import v075_private_observer_boundary_v1 as observer
from acfqp import v075_public_campaign_authority_v1 as authority
from acfqp import v075_public_graph_semantics_v1 as public_graph
from acfqp import v075_registered_occurrence_worker_v1 as worker
from acfqp import v075_source_prior_adapter_v1 as source_prior
from tests.v075_signature_test_support import (
    make_public_key,
    sign_test_message,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def _id(label: str) -> str:
    return hashlib.sha256(
        b"acfqp:v075-registered-worker-test:v1"
        + b"\x00"
        + label.encode("utf-8")
    ).hexdigest()


def _laws() -> tuple[tuple[tuple[int, Fraction], ...], ...]:
    # Construction-only data.  These are not production laws.
    return (
        ((1, Fraction(2, 3)), (2, Fraction(1, 3))),
        ((1, Fraction(3, 4)), (2, Fraction(1, 4))),
        ((1, Fraction(4, 5)), (2, Fraction(1, 5))),
    )


def _salt() -> bytes:
    return hashlib.sha512(b"v075-registered-worker-construction-salt").digest()


def _namespace() -> authority.V075PublicTargetTapeNamespaceV1:
    family = authority.freeze_v075_public_family_generation_v1()
    registry = authority.V075TrustedSignerRegistryV1(
        make_public_key("CAMPAIGN_AUTHORITY"),
        make_public_key("OBSERVER_EVIDENCE"),
    )
    commitment = authority.seal_opaque_environment_commitment_v1(
        family=family,
        secret_salt=_salt(),
        secret_laws=_laws(),
    )

    def claim(
        role: authority.V075ExternalAuthorityRoleV1,
        label: str,
    ) -> authority.V075SignedExternalAuthorityClaimV1:
        subject = _id(label)
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

    role = authority.V075ExternalAuthorityRoleV1
    return authority.derive_public_target_tape_namespace_v1(
        family=family,
        environment_commitment=commitment,
        signer_registry=registry,
        claimed_final_preregistration_registry_id=registry.registry_id,
        remote_main_anchor=claim(role.REMOTE_MAIN_ANCHOR, "anchor"),
        final_preregistration=claim(
            role.FINAL_PREREGISTRATION,
            "preregistration",
        ),
        observer_profile=claim(role.OBSERVER_PROFILE, "observer-profile"),
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


@pytest.fixture(scope="module")
def capability_refs() -> dict[
    worker.V075WorkerArmV1,
    worker.V075WorkerObservationCapabilityRefV1,
]:
    namespace = _namespace()
    context = namespace.family.replicate_contexts[0]
    catalogue = public_graph.root_catalogue_v1(context)
    row = public_graph.observation_row_binding_v1(
        context,
        catalogue,
        catalogue.actions[0],
    )
    epoch = public_graph.derive_shared_support_epoch_v1(
        namespace=namespace,
        row_binding=row,
        epoch_index=0,
        evidence=(),
    )
    chain = public_graph.freeze_shared_support_chain_v1(
        namespace=namespace,
        row_binding=row,
        epochs=(epoch,),
    )
    pairing = public_graph.freeze_five_arm_pairing_authority_v1(
        namespace=namespace,
        row_binding=row,
        support_chain=chain,
    )
    streams = public_graph.freeze_five_arm_stream_set_v1(pairing)
    fixture = observer.V075ConstructionOnlyObserverOpenAuthorityFixtureV1(
        namespace,
        _id("observer-open-fixture"),
    )
    session = observer.open_construction_private_observer_fixture_v1(
        authority=fixture,
        private_salt=_salt(),
        private_environment=_laws(),
        observer_signer=_ConstructionSigner(),
        session_external_id=_id("observer-session"),
    )
    result: dict[
        worker.V075WorkerArmV1,
        worker.V075WorkerObservationCapabilityRefV1,
    ] = {}
    for stream in streams.streams:
        capability = session.observe_v1(stream)
        capability_bytes = canonical_json_bytes(capability.to_document())
        key = namespace.signer_registry.observer_evidence_key
        message = worker.capability_attestation_signing_bytes_v1(
            signer_registry_id=namespace.signer_registry.registry_id,
            observer_signer_key_id=key.key_id,
            capability_bytes=capability_bytes,
        )
        ref = worker.V075WorkerObservationCapabilityRefV1(
            capability_bytes,
            namespace.signer_registry,
            sign_test_message(
                message,
                key_role="OBSERVER_EVIDENCE",
            ),
        )
        result[worker.V075WorkerArmV1(stream.arm)] = ref
    return result


@pytest.fixture(scope="module")
def source_transport() -> worker.V075SourcePriorTransportV1:
    archive = source_archive.compile_v075_frozen_source_proposal_archive_v1(
        REPOSITORY_ROOT
    )
    archive_verification = (
        source_archive
        .verify_v075_frozen_source_proposal_archive_independently_v1(
            repository_root=REPOSITORY_ROOT,
            claimed=archive,
        )
    )
    catalogue = source_prior.compile_v075_source_prior_catalogue_v1(
        archive,
        archive_verification,
    )
    # Explicitly construction-only: production source work replay remains
    # NOT_RUN.  The worker transport still exercises the exact adapter and
    # independent-verification schemas and never treats this as production.
    adapter = source_prior.V075SourcePriorAdapterV1(
        source_prior._ISSUER,
        catalogue,
        _id("construction-source-work"),
        _id("construction-source-work-verification"),
        _id("construction-source-counters"),
    )
    verification = source_prior.V075SourcePriorAdapterVerificationV1(
        adapter.adapter_id,
        adapter.adapter_id,
        catalogue.catalogue_id,
        catalogue.source_archive_id,
        catalogue.source_archive_verification_id,
        adapter.source_offline_work_materialization_id,
        adapter.source_offline_work_verification_id,
        hashlib.sha256(adapter.canonical_bytes).hexdigest(),
    )
    return worker.bind_verified_source_prior_transport_v1(
        adapter=adapter,
        verification=verification,
    )


def _request(
    arm: worker.V075WorkerArmV1,
    capability_refs,
    source_transport,
) -> worker.V075RegisteredOccurrenceWorkerRequestV1:
    capability = capability_refs[arm]
    return worker.V075RegisteredOccurrenceWorkerRequestV1(
        worker.freeze_v075_worker_registry_draft_v1(),
        arm,
        list(worker.V075WorkerArmV1).index(arm),
        capability.target_tape_namespace_id,
        capability.context_id,
        (capability,),
        worker.V075WorkerThresholdProfileV1(),
        worker.V075WorkerCapProfileV1(),
        worker.construction_total_lift_authority_ref_v1("TEST"),
        (
            source_transport
            if arm is worker.V075WorkerArmV1.SOURCE_CONSENSUS_PRIOR
            else None
        ),
    )


def _all_keys(value: Any) -> tuple[str, ...]:
    if type(value) is dict:
        return tuple(value) + tuple(
            key for child in value.values() for key in _all_keys(child)
        )
    if type(value) is list:
        return tuple(
            key for child in value for key in _all_keys(child)
        )
    return ()


def test_complete_five_arm_registry_is_distinct_and_not_ready() -> None:
    registry = worker.freeze_v075_worker_registry_draft_v1()
    assert tuple(item.arm.value for item in registry.registrations) == (
        authority.ARM_ORDER
    )
    assert len({item.registration_id for item in registry.registrations}) == 5
    assert tuple(item.route.value for item in registry.registrations) == (
        "ADAPTIVE_QUOTIENT",
        "ADAPTIVE_QUOTIENT",
        "ADAPTIVE_QUOTIENT",
        "ADAPTIVE_QUOTIENT",
        "MATCHED_DIRECT_GROUND",
    )
    assert tuple(
        item.proposal_semantics.value for item in registry.registrations
    ) == (
        "SOURCE_ARCHIVE_FORWARD_MIDRANK",
        "NO_PRIOR",
        "REGISTERED_WRONG_REVERSED_MIDRANK_NO_SOURCE_PAYLOAD",
        "OOD_TYPED_SCHEMA_ABSTENTION_NEUTRAL",
        "MATCHED_DIRECT_NO_SELECTOR",
    )
    assert tuple(
        item.source_prior_required for item in registry.registrations
    ) == (True, False, False, False, False)
    assert all(
        item.backend_status is worker.V075WorkerBackendStatusV1.NOT_READY
        for item in registry.registrations
    )
    assert registry.to_document()["final_spec_frozen"] is False


def test_worker_import_and_entrypoint_surface_has_no_executable_authority() -> None:
    tree = ast.parse(inspect.getsource(worker))
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(item.name for item in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module or "")
    assert not any(
        fragment in name
        for name in imports
        for fragment in (
            "v072_registered",
            "private_observer",
            "transition_engine",
            "matched_direct",
        )
    )
    assert tuple(
        inspect.signature(
            worker.execute_production_occurrence_worker_v1
        ).parameters
    ) == ("request_bytes",)


@pytest.mark.parametrize("arm", tuple(worker.V075WorkerArmV1))
def test_all_arms_canonical_reconstruct_and_preserve_route_native_work(
    arm,
    capability_refs,
    source_transport,
) -> None:
    request = _request(arm, capability_refs, source_transport)
    loaded = worker.load_v075_registered_occurrence_worker_request_v1(
        request.canonical_bytes
    )
    result_bytes = (
        worker.execute_construction_fixture_occurrence_worker_v1(
            request.canonical_bytes
        )
    )
    result = worker.verify_construction_fixture_occurrence_result_v1(
        request_bytes=request.canonical_bytes,
        result_bytes=result_bytes,
    )
    assert loaded["request_id"] == request.request_id
    assert result.request_id == request.request_id
    assert result.occurrence_id == request.occurrence_id
    assert result.to_document()["scientific_result"] is False
    assert result.to_document()["target_accessed"] is False
    counters = {
        item.path: item.value for item in result.work.counters
    }
    adaptive = arm is not worker.V075WorkerArmV1.MATCHED_DIRECT_GROUND
    assert counters["adaptive.route_dispatches"] == int(adaptive)
    assert counters["direct.route_dispatches"] == int(not adaptive)
    assert counters["adaptive.observation_capabilities"] == int(adaptive)
    assert counters["direct.observation_capabilities"] == int(not adaptive)
    assert counters["source_prior.adapter_reads"] == int(
        arm is worker.V075WorkerArmV1.SOURCE_CONSENSUS_PRIOR
    )
    semantic_paths = (
        "adaptive.source_proposal_dispatches",
        "adaptive.no_prior_dispatches",
        "adaptive.wrong_prior_dispatches",
        "adaptive.ood_abstention_dispatches",
    )
    assert tuple(counters[path] for path in semantic_paths) == tuple(
        int(arm is candidate)
        for candidate in tuple(worker.V075WorkerArmV1)[:4]
    )
    assert tuple(item.path for item in result.work.counters) == (
        worker.REGISTERED_COUNTER_PATHS
    )
    assert all(item.observed for item in result.work.counters)


def test_source_prior_is_required_only_by_source_arm(
    capability_refs,
    source_transport,
) -> None:
    source_request = _request(
        worker.V075WorkerArmV1.SOURCE_CONSENSUS_PRIOR,
        capability_refs,
        source_transport,
    )
    assert source_request.source_prior_transport is source_transport

    with pytest.raises(
        worker.V075RegisteredOccurrenceWorkerInvariantViolation,
        match="missing",
    ):
        replace(source_request, source_prior_transport=None)

    no_prior = _request(
        worker.V075WorkerArmV1.NO_PRIOR,
        capability_refs,
        source_transport,
    )
    with pytest.raises(
        worker.V075RegisteredOccurrenceWorkerInvariantViolation,
        match="escaped",
    ):
        replace(no_prior, source_prior_transport=source_transport)


def test_capability_tamper_and_resign_with_wrong_key_fail_closed(
    capability_refs,
) -> None:
    ref = capability_refs[worker.V075WorkerArmV1.NO_PRIOR]
    document = json.loads(ref.capability_bytes)
    document["failure"] = not document["failure"]
    forged_bytes = canonical_json_bytes(document)
    with pytest.raises(
        worker.V075RegisteredOccurrenceWorkerInvariantViolation,
        match="identity changed",
    ):
        worker.V075WorkerObservationCapabilityRefV1(
            forged_bytes,
            ref.signer_registry,
            ref.capability_attestation_signature_hex,
        )

    with pytest.raises(
        worker.V075RegisteredOccurrenceWorkerInvariantViolation,
        match="signature is invalid",
    ):
        worker.V075WorkerObservationCapabilityRefV1(
            ref.capability_bytes,
            ref.signer_registry,
            "00" * 256,
        )


def test_request_tamper_noncanonical_and_cross_arm_capability_fail_closed(
    capability_refs,
    source_transport,
) -> None:
    request = _request(
        worker.V075WorkerArmV1.NO_PRIOR,
        capability_refs,
        source_transport,
    )
    document = json.loads(request.canonical_bytes)
    document["cap_profile"]["maximum_adaptive_rounds"] = 3
    with pytest.raises(worker.V075RegisteredOccurrenceWorkerInvariantViolation):
        worker.load_v075_registered_occurrence_worker_request_v1(
            canonical_json_bytes(document)
        )
    with pytest.raises(worker.V075RegisteredOccurrenceWorkerInvariantViolation):
        worker.load_v075_registered_occurrence_worker_request_v1(
            request.canonical_bytes + b"\n"
        )

    with pytest.raises(
        worker.V075RegisteredOccurrenceWorkerInvariantViolation,
        match="transplanted",
    ):
        replace(
            request,
            capability_refs=(
                capability_refs[
                    worker.V075WorkerArmV1.OOD_ABSTENTION
                ],
            ),
        )


def test_source_transport_tamper_and_result_forgery_fail_closed(
    capability_refs,
    source_transport,
) -> None:
    request = _request(
        worker.V075WorkerArmV1.SOURCE_CONSENSUS_PRIOR,
        capability_refs,
        source_transport,
    )
    document = json.loads(request.canonical_bytes)
    adapter_bytes = bytearray.fromhex(
        document["source_prior_transport"]["adapter_bytes_hex"]
    )
    adapter_bytes[-1] ^= 1
    document["source_prior_transport"]["adapter_bytes_hex"] = (
        bytes(adapter_bytes).hex()
    )
    with pytest.raises(worker.V075RegisteredOccurrenceWorkerInvariantViolation):
        worker.load_v075_registered_occurrence_worker_request_v1(
            canonical_json_bytes(document)
        )

    result_bytes = worker.execute_construction_fixture_occurrence_worker_v1(
        request.canonical_bytes
    )
    result_document = json.loads(result_bytes)
    result_document["scientific_result"] = True
    with pytest.raises(
        worker.V075RegisteredOccurrenceWorkerInvariantViolation,
        match="deterministic reconstruction",
    ):
        worker.verify_construction_fixture_occurrence_result_v1(
            request_bytes=request.canonical_bytes,
            result_bytes=canonical_json_bytes(result_document),
        )


def test_worker_artifacts_contain_no_private_or_executable_inputs(
    capability_refs,
    source_transport,
) -> None:
    request = _request(
        worker.V075WorkerArmV1.SOURCE_CONSENSUS_PRIOR,
        capability_refs,
        source_transport,
    )
    result = json.loads(
        worker.execute_construction_fixture_occurrence_worker_v1(
            request.canonical_bytes
        )
    )
    request_document = json.loads(request.canonical_bytes)
    keys = set(_all_keys(request_document)) | set(_all_keys(result))
    forbidden_exact_keys = {
        "kernel",
        "transition_kernel",
        "law",
        "secret_laws",
        "environment_reveal",
        "reveal",
        "salt",
        "secret_salt",
        "private_signer",
        "observer_session",
        "observer_session_public_id",
        "callback",
        "cache",
        "resume",
        "random_words",
        "seed",
    }
    assert keys.isdisjoint(forbidden_exact_keys)
    assert request_document["no_target_persistence"] is True
    assert (
        request_document["source_prior_transport"]["target_fields_present"]
        is False
    )


def test_production_entrypoint_stays_locked_without_backend(
    capability_refs,
    source_transport,
) -> None:
    request = _request(
        worker.V075WorkerArmV1.MATCHED_DIRECT_GROUND,
        capability_refs,
        source_transport,
    )
    with pytest.raises(
        worker.V075RegisteredOccurrenceWorkerNotReady,
        match="NOT_READY",
    ):
        worker.execute_production_occurrence_worker_v1(
            request.canonical_bytes
        )


def test_fresh_process_receives_only_canonical_request_bytes(
    capability_refs,
    source_transport,
) -> None:
    request = _request(
        worker.V075WorkerArmV1.NO_PRIOR,
        capability_refs,
        source_transport,
    )
    script = (
        "import sys;"
        "from acfqp.v075_registered_occurrence_worker_v1 "
        "import execute_construction_fixture_occurrence_worker_v1 as run;"
        "sys.stdout.buffer.write(run(sys.stdin.buffer.read()))"
    )
    process = subprocess.run(
        (sys.executable, "-c", script),
        input=request.canonical_bytes,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=30,
        cwd=REPOSITORY_ROOT,
    )
    assert process.returncode == 0, process.stderr.decode()
    assert process.stdout == (
        worker.execute_construction_fixture_occurrence_worker_v1(
            request.canonical_bytes
        )
    )
