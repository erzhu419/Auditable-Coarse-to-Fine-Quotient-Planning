from __future__ import annotations

import hashlib
import itertools

import pytest

from acfqp.accounting_v1 import (
    official_comparison_profile_v1,
    official_counter_registry_v1,
)
from acfqp.access_protocol_v1 import FailClosedAccessController
from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp.construction_shared_cap_authority_v1 import (
    CONTROL_CAP_CHECKS_PATH,
    READ_BYTES_PATH,
    SHARED_RESOURCE_PATHS,
    STAGED_BYTES_PATH,
    SHARED_CAP_MOUNT_TOKEN_V1_DOMAIN,
    SHARED_CAP_RECEIPT_V1_DOMAIN,
    SHARED_CAP_RESERVATION_V1_DOMAIN,
    SHARED_CAP_SNAPSHOT_V1_DOMAIN,
    ConstructionSharedCapAuthorityV1Error,
    DirectFallbackSharedCapSessionV1,
    SandboxIngressKindV1,
    SharedCapExhaustedV1,
    SharedCapProtocolFailureV1,
    SharedCapReceiptKindV1,
    SharedCapSessionSnapshotV1,
    SharedCapSessionStateV1,
    freeze_construction_fallback_decision_candidate_v1,
    freeze_construction_fallback_decision_prerequisite_v1,
    freeze_direct_fallback_shared_cap_profile_v1,
    issue_construction_shared_cap_session_v1,
)
from acfqp.phase3e_ids import content_id
from acfqp.routing_v1 import RouteDecisionContextV1


def _id(label: str) -> str:
    return hashlib.sha256(
        b"acfqp:construction-shared-cap-authority-test:v2\x00"
        + label.encode("utf-8")
    ).hexdigest()


def _context(
    *,
    registry_id: str | None = None,
    comparison_id: str | None = None,
    label: str = "v6",
) -> RouteDecisionContextV1:
    registry = registry_v6.official_counter_registry_v6()
    comparison = registry_v6.official_comparison_profile_v6(registry)
    return RouteDecisionContextV1(
        _id(f"{label}-preregistration"),
        _id(f"{label}-protocol"),
        comparison.comparison_profile_id if comparison_id is None else comparison_id,
        registry.registry_id if registry_id is None else registry_id,
        _id(f"{label}-structural"),
        _id(f"{label}-query"),
        _id(f"{label}-selected-plan"),
        _id(f"{label}-threshold"),
        _id(f"{label}-epoch"),
        _id(f"{label}-occurrence"),
        _id(f"{label}-attempt"),
    )


@pytest.fixture(scope="module")
def construction_chain():
    registry = registry_v6.official_counter_registry_v6()
    stage = registry_v6.official_stage_profile_v6(registry)
    comparison = registry_v6.official_comparison_profile_v6(registry)
    context = _context()
    point_id = _id("v6-decision-point")
    candidate = freeze_construction_fallback_decision_candidate_v1(
        route_context=context,
        decision_point_id=point_id,
        fallback_upper_candidate_id=_id("v7-upper-not-yet-formal"),
        preexecution_barrier_id=_id("clean-preexecution-barrier"),
    )
    controller = FailClosedAccessController(context.route_attempt_id, point_id)
    return {
        "registry": registry,
        "stage": stage,
        "comparison": comparison,
        "context": context,
        "point_id": point_id,
        "candidate": candidate,
        "protocol_profile": controller.profile,
        "prefreeze_log": controller.snapshot(),
    }


def _caps(**overrides: int) -> dict[str, int]:
    result = {path: 64 for path in SHARED_RESOURCE_PATHS}
    result.update(overrides)
    return result


def _sites(label: str = "base") -> dict[str, tuple[str, ...]]:
    return {path: (_id(f"{label}-site-{path}"),) for path in SHARED_RESOURCE_PATHS}


_PROFILE_CACHE: dict[tuple[object, ...], tuple[object, object, object]] = {}
_ACTIVE_PROFILE_SEQUENCE = itertools.count(1)


def _profile(
    construction_chain,
    *,
    caps: dict[str, int] | None = None,
    max_control_cap_checks: int = 128,
    site_label: str = "base",
):
    selected_caps = _caps() if caps is None else caps
    cache_key = (
        id(construction_chain),
        tuple((path, selected_caps[path]) for path in SHARED_RESOURCE_PATHS),
        max_control_cap_checks,
        site_label,
    )
    cached = _PROFILE_CACHE.get(cache_key)
    if cached is not None:
        return cached
    sites = _sites(site_label)
    profile = freeze_direct_fallback_shared_cap_profile_v1(
        route_context=construction_chain["context"],
        route_decision_candidate=construction_chain["candidate"],
        stage_profile_id=construction_chain["stage"].stage_profile_id,
        source_site_manifest_id=_id(f"{site_label}-source-site-manifest"),
        caps=selected_caps,
        source_site_ids=sites,
        max_control_cap_checks=max_control_cap_checks,
    )
    prerequisite = freeze_construction_fallback_decision_prerequisite_v1(
        profile=profile,
        route_decision_candidate=construction_chain["candidate"],
        protocol_profile=construction_chain["protocol_profile"],
        prefreeze_log=construction_chain["prefreeze_log"],
    )
    result = (profile, prerequisite, sites)
    _PROFILE_CACHE[cache_key] = result
    return result


def _active_session(construction_chain, **kwargs):
    label = kwargs.pop("site_label", "active")
    kwargs["site_label"] = f"{label}-{next(_ACTIVE_PROFILE_SEQUENCE)}"
    profile, prerequisite, sites = _profile(construction_chain, **kwargs)
    session = issue_construction_shared_cap_session_v1(profile)
    session.activate_construction(prerequisite)
    return session, profile, prerequisite, sites


def _value(session, path: str) -> int:
    return dict(session.snapshot().shared_values)[path]


def test_profile_is_exactly_official_v6_but_not_formal_or_executable(
    construction_chain,
) -> None:
    profile, prerequisite, sites = _profile(construction_chain)
    repeated, _, _ = _profile(construction_chain)
    document = profile.to_document()
    assert profile.profile_id == repeated.profile_id
    assert tuple(row.path for row in profile.limits) == SHARED_RESOURCE_PATHS
    assert profile.counter_registry_id == construction_chain["registry"].registry_id
    assert profile.stage_profile_id == construction_chain["stage"].stage_profile_id
    assert (
        profile.comparison_profile_id
        == construction_chain["comparison"].comparison_profile_id
    )
    assert document["formal_v6_route_decision_authority_present"] is False
    assert document["production_owner_sites_wired"] is False
    assert document["source_site_manifest_semantically_verified"] is False
    assert (
        document["source_site_registration_status"]
        == "PREREGISTERED_CONSTRUCTION_ONLY_UNVERIFIED"
    )
    assert document["formal_actual_compliance_eligible"] is False
    assert document["official_execution_allowed"] is False
    assert document["generic_ipc_is_staged_bytes"] is False
    assert all(profile.by_path[path].source_site_ids == sites[path] for path in sites)
    prerequisite_document = prerequisite.to_document()
    assert prerequisite_document["formal_v6_route_decision_authority_present"] is False
    assert prerequisite_document["authorizes_production_route_execution"] is False
    assert prerequisite_document["construction_cap_mechanics_only"] is True


def test_legacy_v1_registry_and_comparison_cannot_mint_candidate_or_profile(
    construction_chain,
) -> None:
    legacy_registry = official_counter_registry_v1()
    legacy_comparison = official_comparison_profile_v1(legacy_registry)
    legacy = _context(
        registry_id=legacy_registry.registry_id,
        comparison_id=legacy_comparison.comparison_profile_id,
        label="legacy-v1",
    )
    with pytest.raises(
        ConstructionSharedCapAuthorityV1Error, match="official V6"
    ):
        freeze_construction_fallback_decision_candidate_v1(
            route_context=legacy,
            decision_point_id=_id("legacy-point"),
            fallback_upper_candidate_id=_id("legacy-upper"),
            preexecution_barrier_id=_id("legacy-barrier"),
        )
    with pytest.raises(
        ConstructionSharedCapAuthorityV1Error, match="official V6"
    ):
        freeze_direct_fallback_shared_cap_profile_v1(
            route_context=legacy,
            route_decision_candidate=construction_chain["candidate"],
            stage_profile_id=construction_chain["stage"].stage_profile_id,
            source_site_manifest_id=_id("legacy-manifest"),
            caps=_caps(),
            source_site_ids=_sites("legacy"),
            max_control_cap_checks=128,
        )


def test_cross_registry_comparison_and_stage_identities_are_rejected(
    construction_chain,
) -> None:
    wrong_comparison_context = _context(
        comparison_id=_id("foreign-comparison"), label="wrong-comparison"
    )
    with pytest.raises(
        ConstructionSharedCapAuthorityV1Error, match="official V6"
    ):
        freeze_construction_fallback_decision_candidate_v1(
            route_context=wrong_comparison_context,
            decision_point_id=_id("wrong-comparison-point"),
            fallback_upper_candidate_id=_id("wrong-comparison-upper"),
            preexecution_barrier_id=_id("wrong-comparison-barrier"),
        )

    with pytest.raises(
        ConstructionSharedCapAuthorityV1Error, match="official V6 stage"
    ):
        freeze_direct_fallback_shared_cap_profile_v1(
            route_context=construction_chain["context"],
            route_decision_candidate=construction_chain["candidate"],
            stage_profile_id=_id("foreign-stage"),
            source_site_manifest_id=_id("foreign-stage-manifest"),
            caps=_caps(),
            source_site_ids=_sites("foreign-stage"),
            max_control_cap_checks=128,
        )


def test_session_is_inactive_until_construction_prerequisite(construction_chain) -> None:
    profile, prerequisite, sites = _profile(construction_chain)
    session = issue_construction_shared_cap_session_v1(profile)
    assert session.state is SharedCapSessionStateV1.PREPARED
    with pytest.raises(SharedCapProtocolFailureV1) as caught:
        session.reserve_sum(
            "common.hash_invocations",
            1,
            site_id=sites["common.hash_invocations"][0],
        )
    assert caught.value.terminal_code == "PROTOCOL_FAILURE"
    assert caught.value.infeasibility_certified is False
    assert session.state is SharedCapSessionStateV1.PROTOCOL_FAILED
    with pytest.raises(SharedCapProtocolFailureV1):
        session.activate_construction(prerequisite)


def test_session_issuance_is_one_shot_and_direct_construction_is_typed_failure(
    construction_chain,
) -> None:
    profile, _, sites = _profile(construction_chain, site_label="one-shot")
    reminted = freeze_direct_fallback_shared_cap_profile_v1(
        route_context=construction_chain["context"],
        route_decision_candidate=construction_chain["candidate"],
        stage_profile_id=construction_chain["stage"].stage_profile_id,
        source_site_manifest_id=_id("one-shot-source-site-manifest"),
        caps=_caps(),
        source_site_ids=sites,
        max_control_cap_checks=128,
    )
    assert reminted is not profile
    assert reminted.profile_id == profile.profile_id
    with pytest.raises(SharedCapProtocolFailureV1, match="one-shot factory"):
        DirectFallbackSharedCapSessionV1(profile)
    first = issue_construction_shared_cap_session_v1(profile)
    with pytest.raises(SharedCapProtocolFailureV1, match="already issued"):
        issue_construction_shared_cap_session_v1(reminted)
    assert first.state is SharedCapSessionStateV1.PREPARED


def test_legacy_or_untyped_decision_result_cannot_activate(construction_chain) -> None:
    profile, _, _ = _profile(construction_chain, site_label="untyped")
    session = issue_construction_shared_cap_session_v1(profile)
    with pytest.raises(SharedCapProtocolFailureV1, match="construction decision"):
        session.activate_construction(object())  # type: ignore[arg-type]
    assert session.state is SharedCapSessionStateV1.PROTOCOL_FAILED


@pytest.mark.parametrize(
    "path",
    tuple(
        path
        for path in SHARED_RESOURCE_PATHS
        if path
        not in {
            STAGED_BYTES_PATH,
            "io.mounted_bytes_peak",
            "memory.working_bytes_peak",
        }
    ),
)
def test_each_generic_sum_cap_accepts_exact_and_rejects_plus_one(
    construction_chain, path: str
) -> None:
    session, _, _, sites = _active_session(
        construction_chain, caps=_caps(**{path: 3})
    )
    reservation = session.reserve_sum(path, 3, site_id=sites[path][0])
    session.commit_sum(reservation)
    assert _value(session, path) == 3
    with pytest.raises(SharedCapExhaustedV1) as caught:
        session.reserve_sum(path, 1, site_id=sites[path][0])
    assert caught.value.path == path
    assert caught.value.terminal_code == "FALLBACK_CAP_EXHAUSTED"
    assert caught.value.infeasibility_certified is False
    assert session.receipts[-1].accepted is False


def test_bounded_read_commits_returned_bytes_and_refunds_unused(
    construction_chain,
) -> None:
    session, _, _, sites = _active_session(
        construction_chain, caps=_caps(**{READ_BYTES_PATH: 8})
    )
    requested = []

    def reader(limit: int) -> bytes:
        requested.append(limit)
        return b"abc"

    assert session.bounded_read(
        8, site_id=sites[READ_BYTES_PATH][0], reader=reader
    ) == b"abc"
    assert requested == [8]
    assert _value(session, READ_BYTES_PATH) == 3
    assert dict(session.snapshot().outstanding_reserved_values)[READ_BYTES_PATH] == 0
    settlement = session.receipts[-1]
    assert settlement.kind is SharedCapReceiptKindV1.SUM_COMMITTED
    assert settlement.committed == 3
    assert settlement.refunded == 5


def test_bounded_reader_overreturn_is_protocol_failure_and_charged(
    construction_chain,
) -> None:
    session, _, _, sites = _active_session(
        construction_chain, caps=_caps(**{READ_BYTES_PATH: 8})
    )
    with pytest.raises(SharedCapProtocolFailureV1):
        session.bounded_read(
            4,
            site_id=sites[READ_BYTES_PATH][0],
            reader=lambda _limit: b"12345",
        )
    assert session.state is SharedCapSessionStateV1.PROTOCOL_FAILED
    assert _value(session, READ_BYTES_PATH) == 5
    assert session.receipts[-1].kind is SharedCapReceiptKindV1.SUM_PROTOCOL_OVERRETURN


@pytest.mark.parametrize(
    ("path", "amount"),
    (("process.launches", 1), ("common.protocol_checks", 7)),
)
def test_failed_sum_callback_conservatively_commits_full_reservation(
    construction_chain, path: str, amount: int
) -> None:
    session, _, _, sites = _active_session(
        construction_chain,
        caps=_caps(**{path: amount}),
        site_label=f"callback-{path}",
    )

    def fail() -> None:
        raise RuntimeError("callback failed after unknown side-effect prefix")

    with pytest.raises(RuntimeError, match="unknown side-effect"):
        session.run_sum_operation(path, amount, site_id=sites[path][0], operation=fail)
    assert session.state is SharedCapSessionStateV1.PROTOCOL_FAILED
    assert _value(session, path) == amount
    assert dict(session.snapshot().outstanding_reserved_values)[path] == 0
    assert session.receipts[-1].kind is SharedCapReceiptKindV1.SUM_CALLBACK_FAILED
    assert session.receipts[-1].committed == amount


def test_failed_stage_and_read_callbacks_conservatively_preserve_full_prefix(
    construction_chain,
) -> None:
    staged, _, _, staged_sites = _active_session(
        construction_chain,
        caps=_caps(**{STAGED_BYTES_PATH: 8}),
        site_label="failed-stage",
    )
    with pytest.raises(RuntimeError, match="stage failed"):
        staged.stage_ingress(
            8,
            site_id=staged_sites[STAGED_BYTES_PATH][0],
            ingress_kind=SandboxIngressKindV1.COPY_INTO_EXECUTION_SANDBOX,
            operation=lambda: (_ for _ in ()).throw(RuntimeError("stage failed")),
        )
    assert _value(staged, STAGED_BYTES_PATH) == 8
    assert staged.state is SharedCapSessionStateV1.PROTOCOL_FAILED

    read_full, _, _, read_sites = _active_session(
        construction_chain,
        caps=_caps(**{READ_BYTES_PATH: 8}),
        site_label="failed-read-full",
    )
    with pytest.raises(OSError, match="read failed"):
        read_full.bounded_read(
            8,
            site_id=read_sites[READ_BYTES_PATH][0],
            reader=lambda _limit: (_ for _ in ()).throw(OSError("read failed")),
        )
    assert _value(read_full, READ_BYTES_PATH) == 8



def test_staging_is_named_ingress_repeated_additive_and_generic_ipc_rejected(
    construction_chain,
) -> None:
    session, _, _, sites = _active_session(
        construction_chain, caps=_caps(**{STAGED_BYTES_PATH: 8})
    )
    effects: list[str] = []
    for kind in SandboxIngressKindV1:
        session.stage_ingress(
            4,
            site_id=sites[STAGED_BYTES_PATH][0],
            ingress_kind=kind,
            operation=lambda kind=kind: effects.append(kind.value),
        )
    assert _value(session, STAGED_BYTES_PATH) == 8
    assert len(effects) == 2

    other, _, _, other_sites = _active_session(
        construction_chain, site_label="ipc"
    )
    with pytest.raises(SharedCapProtocolFailureV1):
        other.stage_ingress(
            1,
            site_id=other_sites[STAGED_BYTES_PATH][0],
            ingress_kind="GENERIC_IPC",  # type: ignore[arg-type]
            operation=lambda: None,
        )
    assert _value(other, STAGED_BYTES_PATH) == 0


def test_staging_plus_one_is_blocked_before_side_effect(construction_chain) -> None:
    session, _, _, sites = _active_session(
        construction_chain, caps=_caps(**{STAGED_BYTES_PATH: 4})
    )
    effects: list[str] = []
    session.stage_ingress(
        4,
        site_id=sites[STAGED_BYTES_PATH][0],
        ingress_kind=SandboxIngressKindV1.COPY_INTO_EXECUTION_SANDBOX,
        operation=lambda: effects.append("exact"),
    )
    with pytest.raises(SharedCapExhaustedV1):
        session.stage_ingress(
            1,
            site_id=sites[STAGED_BYTES_PATH][0],
            ingress_kind=SandboxIngressKindV1.BIND_INTO_EXECUTION_SANDBOX,
            operation=lambda: effects.append("forbidden"),
        )
    assert effects == ["exact"]


def test_working_max_accepts_exact_retains_peak_and_rejects_plus_one(
    construction_chain,
) -> None:
    path = "memory.working_bytes_peak"
    session, _, _, sites = _active_session(
        construction_chain, caps=_caps(**{path: 10})
    )
    session.admit_max(path, 10, site_id=sites[path][0])
    session.admit_max(path, 3, site_id=sites[path][0])
    assert _value(session, path) == 10
    with pytest.raises(SharedCapExhaustedV1):
        session.admit_max(path, 11, site_id=sites[path][0])
    assert _value(session, path) == 10


def test_mount_peak_uses_unique_payloads_duplicate_refs_and_retained_peak(
    construction_chain,
) -> None:
    path = "io.mounted_bytes_peak"
    session, _, _, sites = _active_session(
        construction_chain, caps=_caps(**{path: 10})
    )
    site = sites[path][0]
    payload_a = _id("payload-a")
    payload_b = _id("payload-b")
    first = session.open_mount_visibility(payload_a, 6, site_id=site)
    duplicate = session.open_mount_visibility(payload_a, 6, site_id=site)
    assert session.snapshot().mounted_current_bytes == 6
    second = session.open_mount_visibility(payload_b, 4, site_id=site)
    assert session.snapshot().mounted_current_bytes == 10
    assert _value(session, path) == 10
    session.close_mount_visibility(first)
    assert session.snapshot().mounted_current_bytes == 10
    session.close_mount_visibility(duplicate)
    assert session.snapshot().mounted_current_bytes == 4
    session.close_mount_visibility(second)
    assert session.snapshot().mounted_current_bytes == 0
    assert _value(session, path) == 10


def test_mount_distinct_plus_one_rejected_before_visibility(construction_chain) -> None:
    path = "io.mounted_bytes_peak"
    session, _, _, sites = _active_session(
        construction_chain, caps=_caps(**{path: 4})
    )
    site = sites[path][0]
    token = session.open_mount_visibility(_id("exact-payload"), 4, site_id=site)
    with pytest.raises(SharedCapExhaustedV1):
        session.open_mount_visibility(_id("plus-one-payload"), 1, site_id=site)
    assert session.snapshot().mounted_current_bytes == 4
    session.close_mount_visibility(token)
    assert _value(session, path) == 4


def test_each_admission_is_one_nonrecursive_control_cap_check(
    construction_chain,
) -> None:
    session, profile, _, sites = _active_session(
        construction_chain, max_control_cap_checks=2
    )
    first = session.reserve_sum(
        "common.hash_invocations",
        1,
        site_id=sites["common.hash_invocations"][0],
    )
    session.commit_sum(first)
    session.admit_max(
        "memory.working_bytes_peak",
        1,
        site_id=sites["memory.working_bytes_peak"][0],
    )
    assert session.control_cap_checks == 2
    assert sum(row.control_cap_checks_delta for row in session.receipts) == 2
    assert profile.to_document()["control_cap_check_recursive_event_count"] == 0
    with pytest.raises(SharedCapExhaustedV1) as caught:
        session.reserve_sum(
            "common.protocol_checks",
            1,
            site_id=sites["common.protocol_checks"][0],
        )
    assert caught.value.path == CONTROL_CAP_CHECKS_PATH
    assert session.control_cap_checks == 2


def test_unknown_site_and_direct_staged_bypass_fail_closed(
    construction_chain,
) -> None:
    session, _, _, _ = _active_session(construction_chain)
    with pytest.raises(SharedCapProtocolFailureV1):
        session.reserve_sum(
            "common.integrity_checks", 1, site_id=_id("unknown-site")
        )
    assert session.control_cap_checks == 0
    other, _, _, sites = _active_session(construction_chain, site_label="bypass")
    with pytest.raises(SharedCapProtocolFailureV1):
        other.reserve_sum(
            STAGED_BYTES_PATH, 1, site_id=sites[STAGED_BYTES_PATH][0]
        )
    assert _value(other, STAGED_BYTES_PATH) == 0


def test_foreign_prerequisite_stale_profile_and_object_new_fail_closed(
    construction_chain,
) -> None:
    first_profile, _, _ = _profile(construction_chain, site_label="first")
    _, foreign_prerequisite, _ = _profile(construction_chain, site_label="foreign")
    session = issue_construction_shared_cap_session_v1(first_profile)
    with pytest.raises(SharedCapProtocolFailureV1):
        session.activate_construction(foreign_prerequisite)

    profile, prerequisite, sites = _profile(construction_chain, site_label="stale")
    stale = issue_construction_shared_cap_session_v1(profile)
    stale.activate_construction(prerequisite)
    object.__setattr__(profile, "max_control_cap_checks", 999)
    with pytest.raises(SharedCapProtocolFailureV1):
        stale.reserve_sum(
            "common.hash_invocations",
            1,
            site_id=sites["common.hash_invocations"][0],
        )

    honest_profile, honest_prerequisite, _ = _profile(
        construction_chain, site_label="unforgeable"
    )
    fake_profile = object.__new__(type(honest_profile))
    with pytest.raises(Exception, match="live issuer authority"):
        issue_construction_shared_cap_session_v1(fake_profile)
    honest_session = issue_construction_shared_cap_session_v1(honest_profile)
    fake_prerequisite = object.__new__(type(honest_prerequisite))
    with pytest.raises(SharedCapProtocolFailureV1, match="live construction"):
        honest_session.activate_construction(fake_prerequisite)


def test_invalid_runtime_amount_is_protocol_failure(construction_chain) -> None:
    session, _, _, sites = _active_session(
        construction_chain, site_label="negative"
    )
    with pytest.raises(SharedCapProtocolFailureV1) as caught:
        session.reserve_sum(
            "common.hash_invocations",
            -1,
            site_id=sites["common.hash_invocations"][0],
        )
    assert caught.value.terminal_class == "ATTEMPT_CLOSURE_NONCERTIFICATE"
    assert session.state is SharedCapSessionStateV1.PROTOCOL_FAILED


def test_mutated_reservation_fails_typed_and_conservatively_settles_without_negative(
    construction_chain,
) -> None:
    path = "io.output_bytes"
    session, _, _, sites = _active_session(
        construction_chain, site_label="mutated-reservation"
    )
    reservation = session.reserve_sum(path, 5, site_id=sites[path][0])
    object.__setattr__(reservation, "amount", 500)
    object.__setattr__(
        reservation,
        "_reservation_id",
        content_id(SHARED_CAP_RESERVATION_V1_DOMAIN, reservation._payload()),
    )
    assert reservation.reservation_id
    with pytest.raises(SharedCapProtocolFailureV1, match="changed after issuance"):
        session.commit_sum(reservation)
    snapshot = session.snapshot()
    assert dict(snapshot.shared_values)[path] == 5
    assert dict(snapshot.outstanding_reserved_values)[path] == 0
    assert all(value >= 0 for _, value in snapshot.outstanding_reserved_values)
    assert (
        session.receipts[-1].kind
        is SharedCapReceiptKindV1.SUM_PROTOCOL_CAPABILITY_REJECTED
    )


def test_forged_foreign_and_stale_reservations_fail_without_cross_session_charge(
    construction_chain,
) -> None:
    path = "io.output_bytes"
    owner, _, _, owner_sites = _active_session(
        construction_chain, site_label="reservation-owner"
    )
    foreign, _, _, _ = _active_session(
        construction_chain, site_label="reservation-foreign"
    )
    reservation = owner.reserve_sum(path, 4, site_id=owner_sites[path][0])
    with pytest.raises(SharedCapProtocolFailureV1, match="foreign"):
        foreign.commit_sum(reservation)
    assert _value(foreign, path) == 0
    owner.commit_sum(reservation)
    assert _value(owner, path) == 4
    with pytest.raises(SharedCapProtocolFailureV1, match="stale"):
        owner.commit_sum(reservation)

    forged_owner, _, _, _ = _active_session(
        construction_chain, site_label="reservation-forged"
    )
    forged = object.__new__(type(reservation))
    with pytest.raises(SharedCapProtocolFailureV1, match="live issuer"):
        forged_owner.commit_sum(forged)
    assert all(
        value >= 0 for _, value in forged_owner.snapshot().outstanding_reserved_values
    )


def test_mutated_mount_token_fails_typed_and_closes_visibility_without_leak(
    construction_chain,
) -> None:
    path = "io.mounted_bytes_peak"
    session, _, _, sites = _active_session(
        construction_chain, site_label="mutated-mount"
    )
    token = session.open_mount_visibility(
        _id("mutated-mount-payload"), 6, site_id=sites[path][0]
    )
    object.__setattr__(token, "payload_bytes", 600)
    object.__setattr__(
        token,
        "_token_id",
        content_id(SHARED_CAP_MOUNT_TOKEN_V1_DOMAIN, token._payload()),
    )
    assert token.token_id
    with pytest.raises(SharedCapProtocolFailureV1, match="changed after issuance"):
        session.close_mount_visibility(token)
    snapshot = session.snapshot()
    assert snapshot.mounted_current_bytes == 0
    assert dict(snapshot.shared_values)[path] == 6
    assert (
        session.receipts[-1].kind
        is SharedCapReceiptKindV1.MOUNT_PROTOCOL_CAPABILITY_REJECTED
    )


def test_forged_and_foreign_mount_tokens_fail_without_leaking_local_mounts(
    construction_chain,
) -> None:
    path = "io.mounted_bytes_peak"
    owner, _, _, owner_sites = _active_session(
        construction_chain, site_label="mount-owner"
    )
    other, _, _, _ = _active_session(construction_chain, site_label="mount-other")
    token = owner.open_mount_visibility(
        _id("foreign-mount-payload"), 4, site_id=owner_sites[path][0]
    )
    with pytest.raises(SharedCapProtocolFailureV1, match="another cap session"):
        other.close_mount_visibility(token)
    assert other.snapshot().mounted_current_bytes == 0
    owner.close_mount_visibility(token)
    assert owner.snapshot().mounted_current_bytes == 0
    with pytest.raises(SharedCapProtocolFailureV1, match="stale"):
        owner.close_mount_visibility(token)

    forged_owner, _, _, _ = _active_session(
        construction_chain, site_label="mount-forged"
    )
    forged = object.__new__(type(token))
    with pytest.raises(SharedCapProtocolFailureV1, match="live issuer"):
        forged_owner.close_mount_visibility(forged)
    assert forged_owner.snapshot().mounted_current_bytes == 0


def test_receipt_mutation_is_detected_even_if_attacker_recomputes_content_id(
    construction_chain,
) -> None:
    path = "common.hash_invocations"
    session, _, _, sites = _active_session(
        construction_chain, site_label="mutated-receipt"
    )
    reservation = session.reserve_sum(path, 1, site_id=sites[path][0])
    session.commit_sum(reservation)
    receipt = session.receipts[0]
    object.__setattr__(receipt, "requested", 99)
    with pytest.raises(
        ConstructionSharedCapAuthorityV1Error, match="changed after issuance"
    ):
        _ = receipt.receipt_id
    object.__setattr__(
        receipt,
        "_receipt_id",
        content_id(SHARED_CAP_RECEIPT_V1_DOMAIN, receipt._payload()),
    )
    assert receipt.receipt_id
    effects: list[str] = []
    with pytest.raises(SharedCapProtocolFailureV1, match="changed after issuance"):
        session.run_sum_operation(
            path,
            1,
            site_id=sites[path][0],
            operation=lambda: effects.append("must-not-run"),
        )
    assert effects == []
    assert session.state is SharedCapSessionStateV1.PROTOCOL_FAILED


def test_close_requires_no_outstanding_capabilities_and_never_certifies(
    construction_chain,
) -> None:
    session, _, _, sites = _active_session(construction_chain, site_label="close")
    reservation = session.reserve_sum(
        "io.output_bytes", 2, site_id=sites["io.output_bytes"][0]
    )
    with pytest.raises(SharedCapProtocolFailureV1):
        session.close()
    snapshot = session.snapshot()
    assert snapshot.terminal_code == "PROTOCOL_FAILURE"
    assert snapshot.to_document()["certificate_issued"] is False
    assert snapshot.to_document()["infeasibility_certified"] is False
    assert snapshot.to_document()["formal_actual_compliance_eligible"] is False
    assert reservation.reservation_id


@pytest.mark.parametrize(
    ("field", "replacement"),
    (
        ("_session_id", _id("forged-session-id")),
        ("_profile_id", _id("forged-profile-id")),
        ("_state", SharedCapSessionStateV1.CLOSED),
        ("_control_cap_checks", 0),
    ),
)
def test_session_issuer_seal_rejects_fixed_identity_and_runtime_mutation(
    construction_chain, field: str, replacement: object
) -> None:
    session, _, _, sites = _active_session(
        construction_chain, site_label=f"session-seal-{field}"
    )
    if field == "_control_cap_checks":
        reservation = session.reserve_sum(
            "common.hash_invocations",
            1,
            site_id=sites["common.hash_invocations"][0],
        )
        session.commit_sum(reservation)
        assert session.control_cap_checks == 1
    object.__setattr__(session, field, replacement)
    effects: list[str] = []
    with pytest.raises(SharedCapProtocolFailureV1, match="issuer seal"):
        session.run_sum_operation(
            "common.hash_invocations",
            1,
            site_id=sites["common.hash_invocations"][0],
            operation=lambda: effects.append("must-not-run"),
        )
    assert effects == []
    assert session.state is SharedCapSessionStateV1.PROTOCOL_FAILED


@pytest.mark.parametrize(
    "public_name",
    (
        "session_id",
        "state",
        "receipts",
        "control_cap_checks",
        "activate_construction",
        "reserve_sum",
        "commit_sum",
        "refund_sum",
        "run_sum_operation",
        "bounded_read",
        "stage_ingress",
        "admit_max",
        "open_mount_visibility",
        "close_mount_visibility",
        "snapshot",
        "close",
    ),
)
def test_object_new_session_public_surface_is_typed_fail_closed(
    public_name: str,
) -> None:
    forged = object.__new__(DirectFallbackSharedCapSessionV1)
    with pytest.raises(SharedCapProtocolFailureV1, match="live issuer"):
        getattr(forged, public_name)


def test_object_new_session_unbound_public_entry_is_typed_fail_closed() -> None:
    forged = object.__new__(DirectFallbackSharedCapSessionV1)
    with pytest.raises(SharedCapProtocolFailureV1, match="live issuer"):
        DirectFallbackSharedCapSessionV1.snapshot(forged)
    session_id_property = DirectFallbackSharedCapSessionV1.__dict__["session_id"]
    with pytest.raises(SharedCapProtocolFailureV1, match="live issuer"):
        session_id_property.fget(forged)


def test_snapshot_is_live_canonical_and_rejects_recomputed_id_mutation(
    construction_chain,
) -> None:
    session, _, _, _ = _active_session(
        construction_chain, site_label="snapshot-live-seal"
    )
    snapshot = session.snapshot()
    assert snapshot.snapshot_id
    assert snapshot.to_document()["shared_cap_snapshot_id"] == snapshot.snapshot_id
    object.__setattr__(snapshot, "control_cap_checks", 99)
    object.__setattr__(
        snapshot,
        "_snapshot_id",
        content_id(SHARED_CAP_SNAPSHOT_V1_DOMAIN, snapshot._payload()),
    )
    with pytest.raises(SharedCapProtocolFailureV1):
        _ = snapshot.snapshot_id
    with pytest.raises(SharedCapProtocolFailureV1):
        snapshot.to_document()
    forged = object.__new__(SharedCapSessionSnapshotV1)
    with pytest.raises(SharedCapProtocolFailureV1, match="live issuer"):
        _ = forged.snapshot_id


@pytest.mark.parametrize("operation_kind", ("sum", "read", "stage"))
def test_callback_cannot_catch_protocol_failure_and_return_success(
    construction_chain, operation_kind: str
) -> None:
    path = {
        "sum": "common.hash_invocations",
        "read": READ_BYTES_PATH,
        "stage": STAGED_BYTES_PATH,
    }[operation_kind]
    amount = 7
    session, _, _, sites = _active_session(
        construction_chain,
        caps=_caps(**{path: amount}),
        site_label=f"caught-callback-{operation_kind}",
    )

    def caught_protocol_failure() -> None:
        try:
            session.reserve_sum(
                "common.protocol_checks",
                1,
                site_id=_id(f"foreign-site-{operation_kind}"),
            )
        except SharedCapProtocolFailureV1:
            pass

    with pytest.raises(SharedCapProtocolFailureV1, match="callback"):
        if operation_kind == "sum":
            session.run_sum_operation(
                path,
                amount,
                site_id=sites[path][0],
                operation=lambda: caught_protocol_failure(),
            )
        elif operation_kind == "read":
            session.bounded_read(
                amount,
                site_id=sites[path][0],
                reader=lambda _limit: (caught_protocol_failure(), b"ok")[1],
            )
        else:
            session.stage_ingress(
                amount,
                site_id=sites[path][0],
                ingress_kind=SandboxIngressKindV1.COPY_INTO_EXECUTION_SANDBOX,
                operation=lambda: caught_protocol_failure(),
            )
    snapshot = session.snapshot()
    assert session.state is SharedCapSessionStateV1.PROTOCOL_FAILED
    assert dict(snapshot.shared_values)[path] == amount
    assert dict(snapshot.outstanding_reserved_values)[path] == 0


@pytest.mark.parametrize("operation_kind", ("sum", "read", "stage"))
def test_callback_runtime_mutation_then_exception_restores_and_fully_charges(
    construction_chain, operation_kind: str
) -> None:
    path = {
        "sum": "common.hash_invocations",
        "read": READ_BYTES_PATH,
        "stage": STAGED_BYTES_PATH,
    }[operation_kind]
    amount = 9
    session, _, _, sites = _active_session(
        construction_chain,
        caps=_caps(**{path: amount}),
        site_label=f"mutating-exception-{operation_kind}",
    )

    def corrupt_runtime_then_fail() -> None:
        corrupted_reserved = dict(
            object.__getattribute__(session, "_sum_reserved")
        )
        corrupted_reserved[path] = 0
        object.__setattr__(session, "_sum_reserved", corrupted_reserved)
        object.__setattr__(session, "_active_reservations", {})
        raise RuntimeError(f"mutated-{operation_kind}-callback")

    with pytest.raises(
        SharedCapProtocolFailureV1, match="callback corrupted"
    ) as caught:
        if operation_kind == "sum":
            session.run_sum_operation(
                path,
                amount,
                site_id=sites[path][0],
                operation=corrupt_runtime_then_fail,
            )
        elif operation_kind == "read":
            session.bounded_read(
                amount,
                site_id=sites[path][0],
                reader=lambda _limit: (corrupt_runtime_then_fail(), b"")[1],
            )
        else:
            session.stage_ingress(
                amount,
                site_id=sites[path][0],
                ingress_kind=SandboxIngressKindV1.BIND_INTO_EXECUTION_SANDBOX,
                operation=corrupt_runtime_then_fail,
            )
    assert isinstance(caught.value.__cause__, RuntimeError)
    snapshot = session.snapshot()
    assert session.state is SharedCapSessionStateV1.PROTOCOL_FAILED
    assert dict(snapshot.shared_values)[path] == amount
    assert dict(snapshot.outstanding_reserved_values)[path] == 0


def test_callback_runtime_mutation_then_normal_return_is_also_fully_charged(
    construction_chain,
) -> None:
    path = "common.protocol_checks"
    amount = 5
    session, _, _, sites = _active_session(
        construction_chain,
        caps=_caps(**{path: amount}),
        site_label="mutating-normal-return",
    )

    def corrupt_runtime_then_return() -> str:
        object.__setattr__(session, "_active_reservations", {})
        return "must-not-be-accepted"

    with pytest.raises(SharedCapProtocolFailureV1):
        session.run_sum_operation(
            path,
            amount,
            site_id=sites[path][0],
            operation=corrupt_runtime_then_return,
        )
    snapshot = session.snapshot()
    assert dict(snapshot.shared_values)[path] == amount
    assert dict(snapshot.outstanding_reserved_values)[path] == 0


def test_callback_reservation_mutation_then_exception_preserves_callback_cause(
    construction_chain,
) -> None:
    path = "io.output_bytes"
    amount = 6
    session, _, _, sites = _active_session(
        construction_chain,
        caps=_caps(**{path: amount}),
        site_label="mutating-reservation-exception",
    )

    def corrupt_reservation_then_fail() -> None:
        active = object.__getattribute__(session, "_active_reservations")
        reservation = next(iter(active.values()))
        object.__setattr__(reservation, "amount", 600)
        raise RuntimeError("reservation-mutating-callback")

    with pytest.raises(
        SharedCapProtocolFailureV1, match="active reservation"
    ) as caught:
        session.run_sum_operation(
            path,
            amount,
            site_id=sites[path][0],
            operation=corrupt_reservation_then_fail,
        )
    assert isinstance(caught.value.__cause__, RuntimeError)
    assert str(caught.value.__cause__) == "reservation-mutating-callback"
    snapshot = session.snapshot()
    assert dict(snapshot.shared_values)[path] == amount
    assert dict(snapshot.outstanding_reserved_values)[path] == 0
    settlements = [
        receipt
        for receipt in session.receipts
        if receipt.kind
        is SharedCapReceiptKindV1.SUM_PROTOCOL_CAPABILITY_REJECTED
    ]
    assert len(settlements) == 1
    assert settlements[0].committed == amount


def test_protocol_transition_settles_all_outstanding_and_allows_mount_cleanup(
    construction_chain,
) -> None:
    mount_path = "io.mounted_bytes_peak"
    first_path = "common.hash_invocations"
    second_path = "io.output_bytes"
    session, _, _, sites = _active_session(
        construction_chain, site_label="terminal-cleanup"
    )
    token = session.open_mount_visibility(
        _id("terminal-cleanup-payload"), 6, site_id=sites[mount_path][0]
    )
    session.reserve_sum(first_path, 3, site_id=sites[first_path][0])
    session.reserve_sum(second_path, 4, site_id=sites[second_path][0])
    with pytest.raises(SharedCapProtocolFailureV1):
        session.admit_max(
            "memory.working_bytes_peak", 1, site_id=_id("foreign-working-site")
        )
    failed = session.snapshot()
    assert dict(failed.shared_values)[first_path] == 3
    assert dict(failed.shared_values)[second_path] == 4
    assert all(value == 0 for _, value in failed.outstanding_reserved_values)
    assert failed.mounted_current_bytes == 6
    peak = dict(failed.shared_values)[mount_path]

    receipt = session.close_mount_visibility(token)
    cleaned = session.snapshot()
    assert receipt.kind is SharedCapReceiptKindV1.MOUNT_CLOSED
    assert receipt.terminal_code == "PROTOCOL_FAILURE"
    assert session.state is SharedCapSessionStateV1.PROTOCOL_FAILED
    assert cleaned.mounted_current_bytes == 0
    assert dict(cleaned.shared_values)[mount_path] == peak == 6
    assert len(cleaned.receipt_ids) == len(failed.receipt_ids) + 1
