from __future__ import annotations

from dataclasses import replace
import hashlib
from pathlib import Path

import pytest

from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp import construction_k7_canonical_infeasible_fallback_acquisition_v1 as acquisition_v1
from acfqp.access_protocol_v1 import (
    AccessEventLogV1,
    AccessEventV1,
    AccessOperation,
    AccessRouteScope,
    ProtocolSequenceProfileV1,
)
from acfqp.construction_k7_direct_fallback_route_upper_v6 import (
    COUNTER_COMPLETENESS_GATE_STATUS,
    CapEnforcementStatusV6,
    ConstructionK7DirectFallbackRouteUpperV6Error,
    DirectFallbackSharedResourceCapSourceV6,
    EXPECTED_OPERATIONAL_PATH_COUNT,
    EXPECTED_OWNER_EXACT_COUNT,
    EXPECTED_SHARED_RESOURCE_CAP_COUNT,
    EXPECTED_STAGE_FORBIDDEN_ZERO_COUNT,
    LeafUpperSourceV6,
    OFFICIAL_EXECUTION_ALLOWED,
    OWNER_EXACT_UPPERS,
    UPPER_KIND,
    WORKLOAD_ECONOMICS_GATE_STATUS,
    freeze_construction_k7_direct_fallback_route_upper_v6,
    freeze_direct_fallback_shared_resource_cap_source_v6,
    prepare_construction_k7_direct_fallback_route_upper_v6,
    verify_construction_k7_direct_fallback_route_upper_v6,
)
from acfqp.phase3e_exact_infeasibility_durable_proof_v1 import (
    DurableExactInfeasibilityIdentityV1,
    issue_phase3e_exact_infeasibility_durable_proof_v1,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


ROOT = Path(__file__).resolve().parents[1]
CANONICAL_BUNDLE = ROOT / "artifacts" / "phase05" / "g2048"


def _id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


@pytest.fixture(scope="module")
def authority_evidence():
    proof_bytes = issue_phase3e_exact_infeasibility_durable_proof_v1(CANONICAL_BUNDLE)
    identity = DurableExactInfeasibilityIdentityV1.from_dict(
        loads_canonical_json(proof_bytes)["identity"]
    )
    current = acquisition_v1.build_current_canonical_fallback_identity_v1(
        CANONICAL_BUNDLE,
        build_epoch_id=identity.build_epoch_id,
        threshold_profile_id=identity.threshold_profile_id,
        reward_profile_id=identity.reward_profile_id,
        policy_class_id=identity.policy_class_id,
        complete_search_profile_id=identity.complete_search_profile_id,
    )
    acquired = acquisition_v1.acquire_canonical_infeasible_direct_fallback_v1(
        proof_bytes,
        current_identity=current,
    )
    return proof_bytes, current, acquired.preexecution


@pytest.fixture(scope="module")
def source_preexecution(authority_evidence):
    return authority_evidence[2]


def _prepare(source_preexecution, authority_evidence):
    proof_bytes, current_identity, _source = authority_evidence
    return prepare_construction_k7_direct_fallback_route_upper_v6(
        source_preexecution,
        durable_proof_bytes=proof_bytes,
        current_identity=current_identity,
    )


def _allowed_log(preparation) -> AccessEventLogV1:
    profile = ProtocolSequenceProfileV1()
    attempt = preparation.route_context.route_attempt_id
    point = preparation.decision_point.decision_point_id
    artifacts = (
        preparation.source_preexecution_candidate_id,
        preparation.current_identity_attestation_id,
        preparation.source_cardinality_evidence_id,
    )
    operations = (
        AccessOperation.READ_FAILED_CERTIFICATE,
        AccessOperation.READ_PREREGISTERED_CARDINALITIES,
        AccessOperation.READ_CAP_REGISTRY,
    )
    return AccessEventLogV1(
        attempt,
        point,
        profile.protocol_sequence_profile_id,
        tuple(
            AccessEventV1(
                index,
                attempt,
                point,
                operation,
                AccessRouteScope.COMMON,
                artifact,
            )
            for index, (operation, artifact) in enumerate(
                zip(operations, artifacts), start=1
            )
        ),
    )


@pytest.fixture(scope="module")
def frozen(source_preexecution, authority_evidence):
    preparation = _prepare(source_preexecution, authority_evidence)
    return freeze_construction_k7_direct_fallback_route_upper_v6(
        preparation=preparation,
        source_preexecution=source_preexecution,
        preselection_access_log=_allowed_log(preparation),
        shared_resource_cap_source=(
            freeze_direct_fallback_shared_resource_cap_source_v6()
        ),
    )


def test_typed_h1_source_and_replayed_log_freeze_honest_candidate(frozen) -> None:
    registry = registry_v6.official_counter_registry_v6()
    counts = frozen.formula.disposition_counts
    leaf = dict(frozen.upper.leaf_upper_bounds)

    assert len(leaf) == EXPECTED_OPERATIONAL_PATH_COUNT
    assert tuple(leaf) == tuple(row.path for row in registry.operational_leaves)
    assert counts[LeafUpperSourceV6.STAGE_FORBIDDEN_ZERO] == (
        EXPECTED_STAGE_FORBIDDEN_ZERO_COUNT
    )
    assert counts[LeafUpperSourceV6.EXACT_TYPED_H1_CARDINALITY] == (
        EXPECTED_OWNER_EXACT_COUNT
    )
    assert counts[LeafUpperSourceV6.UNENFORCED_SHARED_ADMISSION_CAP] == (
        EXPECTED_SHARED_RESOURCE_CAP_COUNT
    )
    assert {path: leaf[path] for path, _value in OWNER_EXACT_UPPERS} == dict(
        OWNER_EXACT_UPPERS
    )
    assert frozen.preparation.source_preexecution_candidate_id == (
        frozen.preparation.source_preexecution.candidate_id
    )
    assert frozen.preparation.current_identity_attestation_id == (
        frozen.preparation.source_preexecution.current_identity.attestation_id
    )
    assert frozen.barrier.access_event_log_id == frozen.access_log.access_event_log_id
    assert frozen.barrier.access_event_count == len(frozen.access_log.events) == 3
    assert frozen.barrier.to_document()["kernel_step_before_freeze"] is False
    assert frozen.barrier.to_document()["caller_supplied_zero_snapshot_used"] is False
    assert frozen.decision.to_document()["selected_route_candidate"] == "FALLBACK"
    assert frozen.decision.to_document()["execution_permitted"] is False
    assert frozen.upper.to_document()["upper_kind"] == UPPER_KIND
    assert UPPER_KIND == "FINITE_ADMISSION_CAP_CANDIDATE"
    assert frozen.upper.to_document()["formal_actual_compliance_eligible"] is False
    assert frozen.to_document()["formal_route_decision_issued"] is False
    assert OFFICIAL_EXECUTION_ALLOWED is False
    assert COUNTER_COMPLETENESS_GATE_STATUS == "COUNTER_COMPLETENESS_GATE_NOT_RUN"
    assert WORKLOAD_ECONOMICS_GATE_STATUS == "WORKLOAD_ECONOMICS_GATE_NOT_RUN"


def test_shared_caps_are_typed_live_source_but_explicitly_unenforced(frozen) -> None:
    source = frozen.cap_source
    assert len(source.rows) == 9
    assert source.current_runner_module.endswith(
        "construction_k7_canonical_infeasible_fallback_owned_runner_v2"
    )
    assert all(len(digest) == 64 for _module, digest in source.source_module_sha256)
    assert all(
        row.enforcement_status is not CapEnforcementStatusV6.CURRENT_RUNNER_ENFORCED
        for row in source.rows
    )
    document = source.to_document()
    assert document["all_nine_paths_enforced_by_current_runner"] is False
    assert document["formal_actual_compliance_eligible"] is False
    assert "LACKS_COMPLETE_SHARED_CAP_ENFORCEMENT" in document[
        "production_join_blocker"
    ]


def test_independent_replay_rejects_stale_document_and_v1_raw(
    frozen, source_preexecution, authority_evidence
) -> None:
    proof_bytes, current_identity, _source = authority_evidence
    verified = verify_construction_k7_direct_fallback_route_upper_v6(
        frozen.canonical_bytes,
        expected_source_preexecution=source_preexecution,
        expected_durable_proof_bytes=proof_bytes,
        expected_current_identity=current_identity,
        expected_preselection_access_log=frozen.access_log,
    )
    assert verified.bundle_id == frozen.bundle_id

    document = loads_canonical_json(frozen.canonical_bytes)
    document["fallback_upper_candidate"]["comparison_upper_bounds"].pop()
    with pytest.raises(
        ConstructionK7DirectFallbackRouteUpperV6Error,
        match="differs from independent V6 replay",
    ):
        verify_construction_k7_direct_fallback_route_upper_v6(
            canonical_json_bytes(document),
            expected_source_preexecution=source_preexecution,
            expected_durable_proof_bytes=proof_bytes,
            expected_current_identity=current_identity,
            expected_preselection_access_log=frozen.access_log,
        )
    v1_raw = canonical_json_bytes(source_preexecution.upper.to_dict())
    with pytest.raises(
        ConstructionK7DirectFallbackRouteUpperV6Error,
        match="differs from independent V6 replay",
    ):
        verify_construction_k7_direct_fallback_route_upper_v6(
            v1_raw,
            expected_source_preexecution=source_preexecution,
            expected_durable_proof_bytes=proof_bytes,
            expected_current_identity=current_identity,
            expected_preselection_access_log=frozen.access_log,
        )


def test_kernel_step_in_real_typed_log_cannot_be_hidden_by_zero_claim(
    source_preexecution,
    authority_evidence,
) -> None:
    preparation = _prepare(source_preexecution, authority_evidence)
    allowed = _allowed_log(preparation)
    events = (*allowed.events, AccessEventV1(
        4,
        allowed.route_attempt_id,
        allowed.decision_point_id,
        AccessOperation.KERNEL_STEP,
        AccessRouteScope.FALLBACK,
        None,
    ))
    violating = AccessEventLogV1(
        allowed.route_attempt_id,
        allowed.decision_point_id,
        allowed.protocol_sequence_profile_id,
        events,
    )
    with pytest.raises(
        ConstructionK7DirectFallbackRouteUpperV6Error,
        match="access protocol replay rejected",
    ):
        freeze_construction_k7_direct_fallback_route_upper_v6(
            preparation=preparation,
            source_preexecution=source_preexecution,
            preselection_access_log=violating,
            shared_resource_cap_source=(
                freeze_direct_fallback_shared_resource_cap_source_v6()
            ),
        )


def test_random_identity_source_hashes_and_raw_v1_object_are_rejected(
    source_preexecution, authority_evidence,
) -> None:
    proof_bytes, current_identity, _source = authority_evidence
    with pytest.raises(
        ConstructionK7DirectFallbackRouteUpperV6Error,
        match="issuer-owned typed preexecution authority",
    ):
        prepare_construction_k7_direct_fallback_route_upper_v6(
            _id("random"),
            durable_proof_bytes=proof_bytes,
            current_identity=current_identity,
        )

    preparation = _prepare(source_preexecution, authority_evidence)
    stale = replace(
        preparation,
        source_preexecution_candidate_id=_id("random-source"),
    )
    with pytest.raises(
        ConstructionK7DirectFallbackRouteUpperV6Error,
        match="preparation differs",
    ):
        freeze_construction_k7_direct_fallback_route_upper_v6(
            preparation=stale,
            source_preexecution=source_preexecution,
            preselection_access_log=_allowed_log(preparation),
            shared_resource_cap_source=(
                freeze_direct_fallback_shared_resource_cap_source_v6()
            ),
        )

    with pytest.raises(
        ConstructionK7DirectFallbackRouteUpperV6Error,
        match="issuer-owned typed preexecution authority",
    ):
        freeze_construction_k7_direct_fallback_route_upper_v6(
            preparation=preparation,
            source_preexecution=source_preexecution.upper,
            preselection_access_log=_allowed_log(preparation),
            shared_resource_cap_source=(
                freeze_direct_fallback_shared_resource_cap_source_v6()
            ),
        )


def test_recomputed_candidate_id_cannot_replace_durable_authority(
    source_preexecution, authority_evidence
) -> None:
    proof_bytes, current_identity, _source = authority_evidence
    forged = object.__new__(type(source_preexecution))
    for name in type(source_preexecution).__slots__:
        object.__setattr__(forged, name, getattr(source_preexecution, name))
    object.__setattr__(
        forged,
        "route_context",
        replace(source_preexecution.route_context, structural_id=_id("other-structure")),
    )
    object.__setattr__(
        forged,
        "_candidate_id",
        acquisition_v1._local_id(
            acquisition_v1._PREEXECUTION_DOMAIN,
            forged._payload(),
        ),
    )
    assert forged.candidate_id != source_preexecution.candidate_id

    with pytest.raises(
        ConstructionK7DirectFallbackRouteUpperV6Error,
        match="differs from durable independent replay",
    ):
        prepare_construction_k7_direct_fallback_route_upper_v6(
            forged,
            durable_proof_bytes=proof_bytes,
            current_identity=current_identity,
        )


def test_route_upper_requires_all_eight_official_comparison_axes(frozen) -> None:
    assert len(frozen.upper.comparison_upper_bounds) == 8
    with pytest.raises(
        ConstructionK7DirectFallbackRouteUpperV6Error,
        match="exactly the eight official comparison axes",
    ):
        replace(
            frozen.upper,
            comparison_upper_bounds=frozen.upper.comparison_upper_bounds[:-1],
        )


def test_fake_cap_source_and_actual_hints_fail_closed(
    source_preexecution, authority_evidence
) -> None:
    preparation = _prepare(source_preexecution, authority_evidence)
    real = freeze_direct_fallback_shared_resource_cap_source_v6()
    fake = object.__new__(DirectFallbackSharedResourceCapSourceV6)
    for name in (
        "current_runner_module",
        "current_runner_source_sha256",
        "source_module_sha256",
        "rows",
        "_source_id",
    ):
        object.__setattr__(fake, name, getattr(real, name))
    fake_rows = list(real.rows)
    fake_rows[0] = replace(fake_rows[0], value=fake_rows[0].value + 1)
    object.__setattr__(fake, "rows", tuple(fake_rows))
    with pytest.raises(
        ConstructionK7DirectFallbackRouteUpperV6Error,
        match="cap source became stale",
    ):
        freeze_construction_k7_direct_fallback_route_upper_v6(
            preparation=preparation,
            source_preexecution=source_preexecution,
            preselection_access_log=_allowed_log(preparation),
            shared_resource_cap_source=fake,
        )

    with pytest.raises(
        ConstructionK7DirectFallbackRouteUpperV6Error,
        match="actual hints cannot enter",
    ):
        freeze_construction_k7_direct_fallback_route_upper_v6(
            preparation=preparation,
            source_preexecution=source_preexecution,
            preselection_access_log=_allowed_log(preparation),
            shared_resource_cap_source=real,
            actual_hints={"fallback.ground_steps": 16},
        )
