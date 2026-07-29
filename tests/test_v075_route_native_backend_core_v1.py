from __future__ import annotations

import ast
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
from acfqp import v075_private_observer_boundary_v1 as observer
from acfqp import v075_public_graph_semantics_v1 as public_graph
from acfqp import v075_registered_occurrence_worker_v1 as worker
from acfqp import v075_route_native_backend_core_v1 as backend
from tests import test_v075_registered_occurrence_worker_v1 as worker_test
from tests.v075_signature_test_support import sign_test_message


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def _id(label: str) -> str:
    return hashlib.sha256(
        b"acfqp:v075-route-native-backend-test:v1"
        + b"\x00"
        + label.encode("utf-8")
    ).hexdigest()


def _capability_ref(
    namespace,
    capability,
) -> worker.V075WorkerObservationCapabilityRefV1:
    capability_bytes = canonical_json_bytes(capability.to_document())
    key = namespace.signer_registry.observer_evidence_key
    message = worker.capability_attestation_signing_bytes_v1(
        signer_registry_id=namespace.signer_registry.registry_id,
        observer_signer_key_id=key.key_id,
        capability_bytes=capability_bytes,
    )
    return worker.V075WorkerObservationCapabilityRefV1(
        capability_bytes,
        namespace.signer_registry,
        sign_test_message(
            message,
            key_role="OBSERVER_EVIDENCE",
        ),
    )


def _no_prior_discovery_validation_request(
) -> worker.V075RegisteredOccurrenceWorkerRequestV1:
    namespace = worker_test._namespace()
    context = namespace.family.replicate_contexts[0]
    catalogue = public_graph.root_catalogue_v1(context)
    row = public_graph.observation_row_binding_v1(
        context,
        catalogue,
        catalogue.actions[0],
    )
    root_epoch = public_graph.derive_shared_support_epoch_v1(
        namespace=namespace,
        row_binding=row,
        epoch_index=0,
        evidence=(),
    )
    root_chain = public_graph.freeze_shared_support_chain_v1(
        namespace=namespace,
        row_binding=row,
        epochs=(root_epoch,),
    )
    root_pairing = public_graph.freeze_five_arm_pairing_authority_v1(
        namespace=namespace,
        row_binding=row,
        support_chain=root_chain,
    )
    discovery_stream = public_graph.derive_transition_stream_identity_v1(
        pairing_authority=root_pairing,
        arm=worker.V075WorkerArmV1.NO_PRIOR.value,
    )
    fixture = observer.V075ConstructionOnlyObserverOpenAuthorityFixtureV1(
        namespace,
        _id("observer-open-fixture"),
    )
    session = observer.open_construction_private_observer_fixture_v1(
        authority=fixture,
        private_salt=worker_test._salt(),
        private_environment=worker_test._laws(),
        observer_signer=worker_test._ConstructionSigner(),
        session_external_id=_id("observer-session"),
    )
    discovery = tuple(session.observe_v1(discovery_stream) for _ in range(2))
    sampled_state = discovery[0].record.sample.next_state
    observed_state = public_graph.V075SymbolicGraphStateV1(
        context,
        sampled_state.ranks,
        sampled_state.failure,
    )
    evidence_message = public_graph.support_evidence_signing_bytes_v1(
        namespace=namespace,
        row_binding=row,
        observed_state=observed_state,
        source_observer_epoch_index=0,
        accepted_draw_index=1,
    )
    evidence = public_graph.bind_support_evidence_v1(
        namespace=namespace,
        row_binding=row,
        observed_state=observed_state,
        source_observer_epoch_index=0,
        accepted_draw_index=1,
        observer_signature_hex=sign_test_message(
            evidence_message,
            key_role="OBSERVER_EVIDENCE",
        ),
    )
    validation_epoch = public_graph.derive_shared_support_epoch_v1(
        namespace=namespace,
        row_binding=row,
        epoch_index=1,
        evidence=(evidence,),
        parent=root_epoch,
    )
    validation_chain = public_graph.freeze_shared_support_chain_v1(
        namespace=namespace,
        row_binding=row,
        epochs=(root_epoch, validation_epoch),
    )
    validation_pairing = public_graph.freeze_five_arm_pairing_authority_v1(
        namespace=namespace,
        row_binding=row,
        support_chain=validation_chain,
    )
    validation_stream = public_graph.derive_transition_stream_identity_v1(
        pairing_authority=validation_pairing,
        arm=worker.V075WorkerArmV1.NO_PRIOR.value,
    )
    validation = tuple(
        session.observe_v1(validation_stream) for _ in range(3)
    )
    refs = tuple(
        _capability_ref(namespace, item)
        for item in (*discovery, *validation)
    )
    return worker.V075RegisteredOccurrenceWorkerRequestV1(
        worker.freeze_v075_worker_registry_draft_v1(),
        worker.V075WorkerArmV1.NO_PRIOR,
        1,
        namespace.target_tape_namespace_id,
        context.context_id,
        refs,
        worker.V075WorkerThresholdProfileV1(),
        worker.V075WorkerCapProfileV1(),
        worker.construction_total_lift_authority_ref_v1(
            "BACKEND_VALIDATION_TEST"
        ),
        None,
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


@pytest.fixture(scope="module")
def construction_inputs():
    return (
        worker_test.capability_refs.__wrapped__(),
        worker_test.source_transport.__wrapped__(),
    )


def test_worker_and_backend_import_graph_excludes_source_runtime_and_v072() -> None:
    forbidden = (
        "v075_source_prior_adapter",
        "v075_frozen_source_proposal_archive",
        "v075_source_offline_work_materializer",
        "v072",
        "private_observer",
    )
    for module in (worker, backend):
        tree = ast.parse(inspect.getsource(module))
        imports: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(item.name for item in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
        assert not any(
            fragment in imported
            for imported in imports
            for fragment in forbidden
        )

    script = r"""
import importlib.abc
import sys

blocked = (
    "acfqp.v075_source_prior_adapter_v1",
    "acfqp.v075_frozen_source_proposal_archive_v1",
    "acfqp.v075_source_offline_work_materializer_v1",
    "acfqp.v072",
)

class BlockForbidden(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if any(fullname == item or fullname.startswith(item) for item in blocked):
            raise RuntimeError("forbidden production dependency: " + fullname)
        return None

sys.meta_path.insert(0, BlockForbidden())
import acfqp.v075_registered_occurrence_worker_v1
import acfqp.v075_route_native_backend_core_v1
bad = [name for name in sys.modules if any(
    name == item or name.startswith(item) for item in blocked
)]
if bad:
    raise RuntimeError("forbidden modules loaded: " + repr(bad))
"""
    process = subprocess.run(
        (sys.executable, "-c", script),
        cwd=REPOSITORY_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=30,
    )
    assert process.returncode == 0, process.stderr.decode()


@pytest.mark.parametrize("arm", tuple(worker.V075WorkerArmV1))
def test_all_five_route_native_arms_execute_deterministically_without_claim(
    arm,
    construction_inputs,
) -> None:
    refs, transport = construction_inputs
    request = worker_test._request(arm, refs, transport)
    result = backend.execute_v075_route_native_backend_core_v1(
        request.canonical_bytes
    )
    verified = backend.verify_v075_route_native_backend_result_v1(
        request_bytes=request.canonical_bytes,
        claimed_bytes=result.canonical_bytes,
    )
    assert verified == result
    document = result.to_document()
    assert document["target_accessed"] is False
    assert document["scientific_result"] is False
    assert document["production_backend_ready"] is False
    assert document["terminal_class"] == (
        "ATTEMPT_CLOSURE_NONCERTIFICATE"
    )
    assert result.policy.status is (
        backend.V075BackendCandidateStatusV1.NOT_READY_NO_VALIDATION
    )
    assert result.total_lift_input.to_document()[
        "ready_for_total_lift_evaluation"
    ] is False

    values = {item.path: item.value for item in result.work.counters}
    adaptive = arm is not worker.V075WorkerArmV1.MATCHED_DIRECT_GROUND
    assert values["adaptive.route_attempts"] == int(adaptive)
    assert values["direct.route_attempts"] == int(not adaptive)
    assert values["adaptive.model_rows"] == (1 if adaptive else 0)
    assert values["direct.model_rows"] == (0 if adaptive else 1)
    assert tuple(item.path for item in result.work.counters) == (
        backend.COUNTER_PATHS
    )
    assert all(item.observed for item in result.work.counters)

    if arm is worker.V075WorkerArmV1.SOURCE_CONSENSUS_PRIOR:
        assert result.proposal.exact_midrank_vector == (
            backend.SOURCE_FORWARD_MIDRANK
        )
        assert result.proposal.source_transport_id is not None
    elif arm is worker.V075WorkerArmV1.WRONG_CONSENSUS_PRIOR:
        assert result.proposal.exact_midrank_vector == (
            backend.REGISTERED_WRONG_REVERSED_MIDRANK
        )
        assert result.proposal.source_transport_id is None
    else:
        assert result.proposal.exact_midrank_vector == ()
        assert result.proposal.source_transport_id is None


def test_neutral_ood_and_no_prior_share_schedule_semantics_only(
    construction_inputs,
) -> None:
    refs, transport = construction_inputs
    no_prior = backend.execute_v075_route_native_backend_core_v1(
        worker_test._request(
            worker.V075WorkerArmV1.NO_PRIOR,
            refs,
            transport,
        ).canonical_bytes
    )
    ood = backend.execute_v075_route_native_backend_core_v1(
        worker_test._request(
            worker.V075WorkerArmV1.OOD_ABSTENTION,
            refs,
            transport,
        ).canonical_bytes
    )
    assert (
        no_prior.schedule.schedule_semantics_id
        == ood.schedule.schedule_semantics_id
    )
    assert no_prior.schedule.schedule_id != ood.schedule.schedule_id
    assert no_prior.proposal.proposal_id != ood.proposal.proposal_id
    assert ood.proposal.to_document()[
        "ood_abstains_exactly_to_no_prior"
    ] is True


def test_discovery_support_and_validation_statistics_are_lane_separated() -> None:
    request = _no_prior_discovery_validation_request()
    result = backend.execute_v075_route_native_backend_core_v1(
        request.canonical_bytes
    )
    row = result.model.rows[0]
    assert len(row.discovery_capability_ids) == 2
    assert len(row.validation_capability_ids) == 3
    assert row.validation_epoch_index == 1
    assert row.support
    assert tuple(item.event_key for item in row.intervals) == tuple(
        item.descriptor_id for item in row.support
    ) + ("OTHER",)
    assert all(item.draw_count == 3 for item in row.intervals)
    assert sum(item.success_count for item in row.intervals) == 3
    assert all(
        item.empirical_probability
        == Fraction(item.success_count, item.draw_count)
        for item in row.intervals
    )
    assert all(
        0
        <= item.lower_probability
        <= item.empirical_probability
        <= item.upper_probability
        <= 1
        for item in row.intervals
    )
    assert row.blocker == "TYPED_SUPPORT_GRAPH_REPLAY_NOT_AVAILABLE"
    assert result.policy.status is (
        backend.V075BackendCandidateStatusV1
        .NOT_READY_INCOMPLETE_ACTION_CATALOGUE
    )
    values = {item.path: item.value for item in result.work.counters}
    assert values["common.discovery_capabilities_consumed"] == 2
    assert values["common.validation_capabilities_consumed"] == 3
    assert values["common.confidence_event_evaluations"] == len(
        row.intervals
    )
    assert values["common.exact_likelihood_comparisons"] > 0
    assert result.schedule.status is (
        backend.V075BackendScheduleStatusV1
        .PREFIX_BEFORE_REGISTERED_CHECKPOINT
    )


def test_result_tamper_and_noncanonical_bytes_fail_recomputation(
    construction_inputs,
) -> None:
    refs, transport = construction_inputs
    request = worker_test._request(
        worker.V075WorkerArmV1.MATCHED_DIRECT_GROUND,
        refs,
        transport,
    )
    result = backend.execute_v075_route_native_backend_core_v1(
        request.canonical_bytes
    )
    document = json.loads(result.canonical_bytes)
    document["scientific_result"] = True
    with pytest.raises(
        backend.V075RouteNativeBackendInvariantViolation,
        match="recomputation",
    ):
        backend.verify_v075_route_native_backend_result_v1(
            request_bytes=request.canonical_bytes,
            claimed_bytes=canonical_json_bytes(document),
        )
    with pytest.raises(
        backend.V075RouteNativeBackendInvariantViolation,
        match="recomputation",
    ):
        backend.verify_v075_route_native_backend_result_v1(
            request_bytes=request.canonical_bytes,
            claimed_bytes=result.canonical_bytes + b"\n",
        )


def test_backend_artifacts_exclude_private_and_executable_surfaces(
    construction_inputs,
) -> None:
    refs, transport = construction_inputs
    request = worker_test._request(
        worker.V075WorkerArmV1.SOURCE_CONSENSUS_PRIOR,
        refs,
        transport,
    )
    document = backend.execute_v075_route_native_backend_core_v1(
        request.canonical_bytes
    ).to_document()
    keys = set(_all_keys(document))
    assert keys.isdisjoint(
        {
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
            "callback",
            "cache",
            "resume",
            "random_words",
            "seed",
            "exact_atoms",
        }
    )
    assert all(
        value.startswith("acfqp:v075-")
        for value in backend.DOMAIN_TAGS.values()
    )
