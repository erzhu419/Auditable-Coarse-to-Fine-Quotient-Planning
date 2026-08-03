from __future__ import annotations

import copy
import gc
import hashlib

import pytest

import acfqp.production_shared_cap_engine_v2 as subject
from acfqp.production_shared_cap_engine_v2 import (
    ActivationStatusV2,
    OWNER_SITE_SPECS,
    ProductionEngineStateV2,
    ProductionRouteActivationInterfaceV2,
    ProductionSharedCapEngineV2,
    ProductionSharedCapProtocolFailureV2,
    ProductionSharedCapV2Error,
    SHARED_RESOURCE_PATHS,
    V7AuthorityPendingV2,
    freeze_production_shared_cap_profile_v2,
    freeze_v7_pending_activation_interface_v2,
    prepare_production_shared_cap_engine_v2,
    production_shared_cap_engine_document_v2,
    production_shared_cap_engine_id_v2,
    production_shared_cap_engine_owner_sentinel_v2,
    production_shared_cap_engine_state_v2,
)


def _id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _caps(default: int = 1_000) -> dict[str, int]:
    return {path: default for path in SHARED_RESOURCE_PATHS}


@pytest.fixture
def pending_activation():
    return freeze_v7_pending_activation_interface_v2(
        route_decision_context_id=_id("context"),
        decision_point_id=_id("decision"),
        route_attempt_id=_id("attempt"),
        v7_authority_request_id=_id("request"),
    )


@pytest.fixture
def profile(pending_activation):
    return freeze_production_shared_cap_profile_v2(
        activation=pending_activation,
        caps=_caps(),
        max_control_cap_checks=100,
    )


@pytest.fixture
def pending_engine(pending_activation, profile):
    return prepare_production_shared_cap_engine_v2(
        activation=pending_activation,
        profile=profile,
    )


def test_pending_interface_profile_and_engine_are_explicitly_non_authoritative(
    pending_activation, profile, pending_engine
) -> None:
    activation_doc = pending_activation.to_document()
    profile_doc = profile.to_document()
    engine_doc = production_shared_cap_engine_document_v2(pending_engine)
    assert pending_activation.status is ActivationStatusV2.V7_AUTHORITY_PENDING
    assert (
        production_shared_cap_engine_state_v2(pending_engine)
        is ProductionEngineStateV2.V7_AUTHORITY_PENDING
    )
    for document in (activation_doc, profile_doc, engine_doc):
        assert document["formal_v7_route_decision_authority_present"] is False
        assert document["production_execution_authorized"] is False
        assert document["production_owner_sites_wired"] is False
        assert document["source_site_manifest_semantically_verified"] is False
        assert document["formal_actual_compliance_eligible"] is False
        assert document["blocker"] == "V7_AUTHORITY_PENDING"
    assert activation_doc["construction_prerequisite_accepted"] is False
    assert engine_doc["preproduction_kernel_receipts_accepted"] is False
    assert engine_doc["official_execution_allowed"] is False


def test_nine_sites_are_exact_embedded_and_not_caller_selectable(pending_engine) -> None:
    assert len(OWNER_SITE_SPECS) == 9
    assert tuple(row.path for row in OWNER_SITE_SPECS) == SHARED_RESOURCE_PATHS
    assert len({row.site_key for row in OWNER_SITE_SPECS}) == 9
    assert all(not hasattr(pending_engine, row.owner_method) for row in OWNER_SITE_SPECS)
    assert all(
        production_shared_cap_engine_owner_sentinel_v2(
            pending_engine, row.owner_method
        )
        == "V7_AUTHORITY_PENDING"
        for row in OWNER_SITE_SPECS
    )
    assert not hasattr(pending_engine, "admit_path")
    assert not hasattr(pending_engine, "record_shared_resource")
    document = production_shared_cap_engine_document_v2(pending_engine)
    assert document["caller_selectable_path"] is False
    assert document["owner_site_count"] == 9
    assert document["callable_owner_surface_present"] is False
    assert document["exact_tuple_capability_required"] is True
    assert document["tuple_subclasses_authoritative"] is False
    assert document["caller_created_exact_tuple_authoritative"] is False
    assert document["reachable_mutable_backing_present"] is False
    assert [row["path"] for row in document["owner_sites"]] == list(
        SHARED_RESOURCE_PATHS
    )


def test_declarative_owner_contract_freezes_atomic_failure_semantics() -> None:
    by_path = {row.path: row for row in OWNER_SITE_SPECS}
    for path in (
        "common.hash_invocations",
        "common.integrity_checks",
        "common.protocol_checks",
        "io.output_bytes",
        "io.read_bytes",
        "io.staged_bytes",
    ):
        assert (
            "CALLBACK_OR_JOURNAL_EXCEPTION_FULL_CHARGE_PROTOCOL_FAILURE"
            in by_path[path].required_semantics
        )
    for path in (
        "common.hash_invocations",
        "common.integrity_checks",
        "common.protocol_checks",
    ):
        assert "ATOMIC_RECEIPT_EVENT_PAIR" in by_path[path].required_semantics
    assert "GENERIC_IPC_EXCLUDED" in by_path["io.staged_bytes"].required_semantics
    assert (
        "AMBIGUOUS_OR_EXCEPTION_FULL_CHARGE_PROTOCOL_FAILURE"
        in by_path["process.launches"].required_semantics
    )


def test_declarative_output_mount_launch_and_same_ofd_lifecycles() -> None:
    by_path = {row.path: row.required_semantics for row in OWNER_SITE_SPECS}
    assert "WHOLE_ROUTE_FIXED_POINT_RESERVE_BEFORE_FIRST_LAUNCH" in by_path[
        "io.output_bytes"
    ]
    assert "OUTSTANDING_RESERVATION_BLOCKS_CLOSE" in by_path["io.output_bytes"]
    assert "OPEN_BEFORE_CHILD_VISIBILITY" in by_path["io.mounted_bytes_peak"]
    assert "CLOSE_ONLY_AFTER_TRUSTED_DESCENDANT_REAP" in by_path[
        "io.mounted_bytes_peak"
    ]
    assert "CLEANUP_REMAINS_AVAILABLE_AFTER_PROTOCOL_FAILURE" in by_path[
        "io.mounted_bytes_peak"
    ]
    assert "POSITIVE_EDGE_REQUIRES_MATCHING_PIDFD" in by_path["process.launches"]
    assert "REFUND_ONLY_TRUSTED_NO_CHILD" in by_path["process.launches"]
    assert "TRUSTED_DESCENDANT_REAP" in by_path["memory.working_bytes_peak"]
    assert "RETAINED_SAME_OFD_MEMORY_PEAK" in by_path[
        "memory.working_bytes_peak"
    ]
    assert "MEMORY_LIMIT_IS_NOT_ACTUAL_PEAK" in by_path[
        "memory.working_bytes_peak"
    ]


def test_every_owner_name_is_a_noncallable_pending_sentinel(
    pending_engine,
) -> None:
    calls: list[str] = []

    def callback():
        calls.append("called")
        return b"payload"

    for site in OWNER_SITE_SPECS:
        sentinel = production_shared_cap_engine_owner_sentinel_v2(
            pending_engine, site.owner_method
        )
        assert sentinel == "V7_AUTHORITY_PENDING"
        assert not callable(sentinel)
        with pytest.raises(TypeError):
            sentinel(callback)
    assert calls == []
    assert (
        production_shared_cap_engine_state_v2(pending_engine)
        is ProductionEngineStateV2.V7_AUTHORITY_PENDING
    )


def test_pending_profile_cannot_issue_private_or_preproduction_live_kernel(
    profile,
) -> None:
    calls: list[bool] = []
    with pytest.raises(V7AuthorityPendingV2, match="V7_AUTHORITY_PENDING"):
        subject._issue_preproduction_atomic_kernel_v2(
            profile, journal_sink=lambda _pair: calls.append(True)
        )
    assert calls == []
    assert "_issue_preproduction_atomic_kernel_v2" not in subject.__all__


def test_exact_tuple_type_is_immutable_and_subclasses_are_not_authority(
    pending_engine,
) -> None:
    with pytest.raises(TypeError):
        ProductionSharedCapEngineV2.record_hash_invocation = (  # type: ignore[attr-defined]
            lambda self, callback: callback()
        )
    with pytest.raises(TypeError):
        type.__setattr__(
            ProductionSharedCapEngineV2,
            "record_hash_invocation",
            lambda self, callback: callback(),
        )

    class HostileProductionEngine(ProductionSharedCapEngineV2):
        pass

    hostile = HostileProductionEngine(pending_engine)
    with pytest.raises(ProductionSharedCapProtocolFailureV2, match="exact tuple"):
        production_shared_cap_engine_state_v2(hostile)

    with pytest.raises(TypeError):
        pending_engine[2] = ProductionEngineStateV2.CLOSED.value
    with pytest.raises(AttributeError):
        pending_engine.record_hash_invocation = lambda callback: callback()  # type: ignore[attr-defined]


def test_object_new_and_caller_tuple_cannot_mint_live_engine() -> None:
    with pytest.raises(TypeError):
        object.__new__(ProductionSharedCapEngineV2)
    forged = ProductionSharedCapEngineV2(
        (
            "acfqp.production_shared_cap_engine_runtime.v2",
            _id("forged"),
            "V7_AUTHORITY_PENDING",
            (("record_hash_invocation", "V7_AUTHORITY_PENDING"),),
        )
    )
    calls: list[bool] = []
    with pytest.raises(ProductionSharedCapProtocolFailureV2, match="live issuer"):
        production_shared_cap_engine_state_v2(forged)
    assert calls == []


def test_gc_referents_expose_no_mutable_backing_or_callable_sentinel(
    pending_engine,
) -> None:
    seen: set[int] = set()
    frontier = [pending_engine]
    while frontier:
        value = frontier.pop()
        if id(value) in seen:
            continue
        seen.add(id(value))
        referents = gc.get_referents(value)
        assert all(
            type(item) not in {dict, list, set, bytearray}
            for item in referents
        )
        frontier.extend(
            item for item in referents if type(item) is tuple
        )

    owner_rows = pending_engine[3]
    assert type(owner_rows) is tuple
    assert all(type(row) is tuple and not callable(row[1]) for row in owner_rows)
    with pytest.raises(TypeError):
        owner_rows[0] = ("record_hash_invocation", lambda callback: callback())
    assert (
        production_shared_cap_engine_owner_sentinel_v2(
            pending_engine, "record_hash_invocation"
        )
        == "V7_AUTHORITY_PENDING"
    )


def test_construction_or_caller_minted_objects_cannot_activate(profile) -> None:
    with pytest.raises(ProductionSharedCapV2Error, match="exact V2 activation"):
        prepare_production_shared_cap_engine_v2(
            activation=object(),  # type: ignore[arg-type]
            profile=profile,
        )
    with pytest.raises(ProductionSharedCapV2Error, match="issuer-owned"):
        ProductionRouteActivationInterfaceV2(
            object(),
            _id("c"),
            _id("d"),
            _id("a"),
            _id("r"),
            ActivationStatusV2.V7_AUTHORITY_PENDING,
        )


def test_copied_mutated_and_object_new_capabilities_fail_closed(
    pending_activation, pending_engine
) -> None:
    copied = copy.copy(pending_activation)
    with pytest.raises(ProductionSharedCapV2Error, match="foreign|caller-minted"):
        freeze_production_shared_cap_profile_v2(
            activation=copied, caps=_caps(), max_control_cap_checks=10
        )

    with pytest.raises(TypeError):
        pending_engine[2] = ProductionEngineStateV2.CLOSED.value
    with pytest.raises((AttributeError, TypeError)):
        object.__setattr__(pending_engine, "state", ProductionEngineStateV2.CLOSED)
    assert (
        production_shared_cap_engine_state_v2(pending_engine)
        is ProductionEngineStateV2.V7_AUTHORITY_PENDING
    )
    assert production_shared_cap_engine_id_v2(pending_engine) == pending_engine[1]


def test_activation_and_profile_mutation_cannot_be_resealed(
    pending_activation,
) -> None:
    object.__setattr__(pending_activation, "status", "V7_AUTHORIZED")
    with pytest.raises(ProductionSharedCapV2Error, match="identity replay"):
        pending_activation.to_document()
    with pytest.raises(ProductionSharedCapV2Error, match="identity replay"):
        freeze_production_shared_cap_profile_v2(
            activation=pending_activation,
            caps=_caps(),
            max_control_cap_checks=10,
        )


def test_local_domains_are_unregistered_candidates_not_central_claims() -> None:
    assert len(subject.REQUESTED_PHASE3E_DOMAIN_TAGS) == 6
    assert len(set(subject.REQUESTED_PHASE3E_DOMAIN_TAGS)) == 6
    assert all(
        "production-shared-cap" in tag or "preproduction-shared-cap" in tag
        for tag in subject.REQUESTED_PHASE3E_DOMAIN_TAGS
    )
    assert subject.PROPOSED_CONTRACT_VERSION == "2.0.49"


def test_pending_identity_helper_is_not_a_receipt_event_or_pair_mint_oracle() -> None:
    for domain in (
        subject.RECEIPT_DOMAIN_CANDIDATE,
        subject.SEMANTIC_EVENT_DOMAIN_CANDIDATE,
        subject.ATOMIC_PAIR_DOMAIN_CANDIDATE,
    ):
        with pytest.raises(ProductionSharedCapV2Error, match="not mintable"):
            subject._candidate_content_id(domain, {"attacker": "payload"})
    assert len(
        subject._candidate_content_id(
            subject.ACTIVATION_INTERFACE_DOMAIN_CANDIDATE,
            {"pending_identity_probe": True},
        )
    ) == 64


def test_malicious_string_subclass_cannot_bypass_domain_allowlist() -> None:
    calls: list[str] = []

    class HostileDomain(str):
        def __hash__(self) -> int:
            calls.append("hash")
            return hash(subject.ACTIVATION_INTERFACE_DOMAIN_CANDIDATE)

        def __eq__(self, other):
            calls.append("eq")
            return True

        def encode(self, *args, **kwargs):
            calls.append("encode")
            return subject.ACTIVATION_INTERFACE_DOMAIN_CANDIDATE.encode(*args, **kwargs)

    hostile = HostileDomain(subject.RECEIPT_DOMAIN_CANDIDATE)
    with pytest.raises(ProductionSharedCapV2Error, match="exact string"):
        subject._candidate_content_id(hostile, {"attacker": "payload"})
    assert calls == []
