from __future__ import annotations

import hashlib

import pytest

from acfqp.construction_k7_h1_shared_cap_owner_v2 import (
    EXACT_CHILD_LAUNCH_ORDER,
    EXACT_CONTROL_CAP_REJECTIONS_UPPER,
    H1SharedCapExecutionLockedV2,
    H1SharedCapExhaustedV2,
    H1SharedCapProtocolFailureV2,
    H1SharedIngressKindV2,
    H1SharedOwnerModeV2,
    OWNER_SITE_SPECS,
    REQUESTED_PHASE3E_DOMAIN_TAGS,
    SHARED_RESOURCE_PATHS,
    freeze_h1_shared_cap_profile_v2,
    freeze_h1_shared_cap_source_manifest_v2,
    h1_shared_cap_owner_snapshot_v2,
    prepare_h1_shared_cap_owner_construction_exercise_v2,
    prepare_h1_shared_cap_owner_v2,
    verify_h1_shared_cap_failure_cause_chain_v2,
)
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS


def _id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _caps(default: int = 1_000) -> dict[str, int]:
    result = {path: default for path in SHARED_RESOURCE_PATHS}
    result["process.launches"] = 2
    result["memory.working_bytes_peak"] = 400
    result["io.output_bytes"] = 120
    result["io.mounted_bytes_peak"] = 100
    return result


def _profile(
    *,
    caps: dict[str, int] | None = None,
    checks: int = 100,
    identity_suffix: str = "",
):
    return freeze_h1_shared_cap_profile_v2(
        predecision_context_id=_id(f"context{identity_suffix}"),
        current_access_authority_id=_id(f"current-access{identity_suffix}"),
        route_attempt_id=_id(f"attempt{identity_suffix}"),
        execution_topology_profile_id=_id(f"topology{identity_suffix}"),
        source_archive_id=_id(f"source{identity_suffix}"),
        hard_caps=_caps() if caps is None else caps,
        max_control_cap_checks=checks,
        outer_hierarchy_cap=350,
        broker_parent_cap=100,
        worker_role_cap=120,
        business_role_cap=150,
        retained_memory_peak_ofd_plan_id=_id("memory-ofd-plan"),
    )


def _manifest(*, identity_suffix: str = ""):
    return freeze_h1_shared_cap_source_manifest_v2(
        source_archive_id=_id(f"source{identity_suffix}"),
        execution_topology_profile_id=_id(f"topology{identity_suffix}"),
    )


def _exercise(*, caps: dict[str, int] | None = None, checks: int = 100):
    return prepare_h1_shared_cap_owner_construction_exercise_v2(
        profile=_profile(caps=caps, checks=checks),
        source_manifest=_manifest(),
    )


def test_domains_are_central_and_structural_manifest_declares_nine_owner_methods() -> None:
    assert len(REQUESTED_PHASE3E_DOMAIN_TAGS) == 8
    assert set(REQUESTED_PHASE3E_DOMAIN_TAGS) <= PHASE3E_DOMAIN_TAGS
    assert tuple(row.path for row in OWNER_SITE_SPECS) == SHARED_RESOURCE_PATHS
    assert len({row.owner_method for row in OWNER_SITE_SPECS}) == 9
    manifest = _manifest().to_document()
    assert manifest["site_count"] == 9
    assert manifest["issuer_retained_owner_kernel_required"] is True
    assert manifest["reserve_before_side_effect_required"] is True
    assert manifest["sentinel_owner_allowed"] is False
    assert manifest["manifest_role"] == "STRUCTURAL_OWNER_SITE_MANIFEST"
    assert manifest["source_bytes_bound"] is False
    assert manifest["normalized_ast_bound"] is False
    assert manifest["loaded_symbol_semantics_verified"] is False
    assert manifest["symbol_rows_are_structural_declarations"] is True
    assert manifest["production_source_authority_present"] is False
    for error_type in (
        H1SharedCapExecutionLockedV2,
        H1SharedCapProtocolFailureV2,
        H1SharedCapExhaustedV2,
    ):
        assert error_type.terminal_classification_issued is False
        assert not hasattr(error_type, "terminal_scope")
        assert not hasattr(error_type, "terminal_class")
        assert not hasattr(error_type, "terminal_code")


def test_profile_is_predecision_non_circular_and_memory_covers_all_roles() -> None:
    profile = _profile()
    document = profile.to_document()
    forbidden = {
        "decision_point_id",
        "DecisionPoint_id",
        "route_upper_id",
        "route_upper_bound_envelope_id",
        "route_decision_id",
        "marginal_route_decision_id",
        "selected_route",
        "route_decision_freeze_id",
        "route_decision_freeze_sequence",
    }
    assert not forbidden & set(document)
    assert document["profile_frozen_predecision"] is True
    assert document["formal_operand_authority_join_present"] is False
    assert document["formal_route_authority_join_present"] is False
    assert document["production_execution_authorized"] is False
    memory = document["memory_topology"]
    assert memory["roles_covered"] == ["BROKER", "WORKER", "BUSINESS"]
    assert memory["formula"] == (
        "MIN(HARD_CAP,OUTER,BROKER_PARENT+WORKER+BUSINESS)"
    )
    assert profile.memory_formula_upper == min(400, 350, 100 + 120 + 150) == 350
    assert document["child_launch_order"] == ["WORKER", "BUSINESS"]
    assert document["process_launches_upper"] == 2
    assert document["control_cap_rejections_upper"] == 1


def test_process_cap_and_exact_nine_profile_are_fail_closed() -> None:
    caps = _caps()
    caps["process.launches"] = 3
    with pytest.raises(ValueError, match=r"WORKER\+BUSINESS=2"):
        _profile(caps=caps)
    caps = _caps()
    caps.pop("io.read_bytes")
    with pytest.raises(ValueError, match="exactly the nine"):
        _profile(caps=caps)


def test_production_owner_is_real_handle_but_locked_before_both_joins() -> None:
    owner = prepare_h1_shared_cap_owner_v2(
        profile=_profile(), source_manifest=_manifest()
    )
    assert callable(owner.record_hash_invocation)
    before = h1_shared_cap_owner_snapshot_v2(owner)
    assert before["mode"] == "AWAITING_OPERAND_FORMAL_JOIN"
    assert before["formal_operand_authority_join_present"] is False
    assert before["formal_route_authority_join_present"] is False
    assert before["production_execution_authorized"] is False
    calls: list[str] = []
    with pytest.raises(H1SharedCapExecutionLockedV2, match="operand and formal"):
        owner.record_hash_invocation(lambda: calls.append("side-effect"))
    assert calls == []
    assert h1_shared_cap_owner_snapshot_v2(owner)["sequence"] == 0


def test_production_runtime_identity_cannot_be_prepared_twice() -> None:
    profile = _profile(identity_suffix="-one-shot")
    manifest = _manifest(identity_suffix="-one-shot")
    prepare_h1_shared_cap_owner_v2(profile=profile, source_manifest=manifest)
    with pytest.raises(ValueError, match="only once"):
        prepare_h1_shared_cap_owner_v2(
            profile=profile,
            source_manifest=manifest,
        )


def test_memory_binding_must_be_first_and_is_admitted_before_callback() -> None:
    owner = _exercise()
    with pytest.raises(H1SharedCapProtocolFailureV2, match="hierarchy must bind"):
        owner.record_integrity_check(lambda: None)

    owner = _exercise()
    seen: list[dict] = []

    def bind_callback(_binding) -> None:
        seen.append(h1_shared_cap_owner_snapshot_v2(owner))

    binding = owner.bind_working_hierarchy(bind_callback)
    assert seen[0]["outstanding"]["memory.working_bytes_peak"] == 350
    assert seen[0]["sequence"] == 0
    after = h1_shared_cap_owner_snapshot_v2(owner)
    assert binding.formula_upper == 350
    assert after["memory_bound"] is True
    assert after["actual"]["memory.working_bytes_peak"] == 0
    assert after["outstanding"]["memory.working_bytes_peak"] == 350
    assert after["control"]["cap_checks"] == 1
    assert after["sequence"] == 1


def test_memory_peak_settles_the_single_prelaunch_admission() -> None:
    owner = _exercise()
    owner.bind_working_hierarchy(lambda _binding: None)
    output = owner.begin_route_output()
    owner.launch_registered_role("WORKER", lambda: None)
    owner.launch_registered_role("BUSINESS", lambda: None)
    owner.mark_trusted_descendants_reaped(
        worker_pidfd_observation_id=_id("worker-reap"),
        business_pidfd_observation_id=_id("business-reap"),
        retained_memory_peak_ofd_plan_id=_id("memory-ofd-plan"),
    )
    before = h1_shared_cap_owner_snapshot_v2(owner)
    assert before["control"]["cap_checks"] == 4
    assert owner.read_working_bytes_peak(lambda: 275) == 275
    after = h1_shared_cap_owner_snapshot_v2(owner)
    assert after["control"]["cap_checks"] == 4
    assert after["outstanding"]["memory.working_bytes_peak"] == 0
    assert after["actual"]["memory.working_bytes_peak"] == 275
    owner.finalize_route_output(output, 0, lambda: None)
    owner.close()


def test_sum_paths_reserve_before_side_effect_and_settle_exact_actuals() -> None:
    owner = _exercise()
    owner.bind_working_hierarchy(lambda _binding: None)
    observations: list[tuple[str, int]] = []

    def unit(path: str):
        observations.append(
            (path, h1_shared_cap_owner_snapshot_v2(owner)["outstanding"][path])
        )
        return path

    assert owner.record_hash_invocation(
        lambda: unit("common.hash_invocations")
    ) == "common.hash_invocations"
    assert owner.record_integrity_check(
        lambda: unit("common.integrity_checks")
    ) == "common.integrity_checks"
    assert owner.record_protocol_check(
        lambda: unit("common.protocol_checks")
    ) == "common.protocol_checks"

    def reader() -> bytes:
        observations.append(
            (
                "io.read_bytes",
                h1_shared_cap_owner_snapshot_v2(owner)["outstanding"][
                    "io.read_bytes"
                ],
            )
        )
        return b"abcdef"

    assert owner.read_registered_payload(10, reader) == b"abcdef"

    def stage() -> int:
        observations.append(
            (
                "io.staged_bytes",
                h1_shared_cap_owner_snapshot_v2(owner)["outstanding"][
                    "io.staged_bytes"
                ],
            )
        )
        return 7

    assert owner.stage_registered_payload(
        12, H1SharedIngressKindV2.COPY_INTO_EXECUTION_SANDBOX, stage
    ) == 7
    assert observations == [
        ("common.hash_invocations", 1),
        ("common.integrity_checks", 1),
        ("common.protocol_checks", 1),
        ("io.read_bytes", 10),
        ("io.staged_bytes", 12),
    ]
    snapshot = h1_shared_cap_owner_snapshot_v2(owner)
    assert snapshot["actual"]["common.hash_invocations"] == 1
    assert snapshot["actual"]["common.integrity_checks"] == 1
    assert snapshot["actual"]["common.protocol_checks"] == 1
    assert snapshot["actual"]["io.read_bytes"] == 6
    assert snapshot["actual"]["io.staged_bytes"] == 7


def test_mount_max_deduplicates_identity_and_close_waits_for_both_reaps() -> None:
    owner = _exercise()
    owner.bind_working_hierarchy(lambda _binding: None)
    output = owner.begin_route_output()
    payload = _id("shared-payload")
    first = owner.open_mounted_payload(payload, 40, lambda: None)
    second = owner.open_mounted_payload(payload, 40, lambda: None)
    third = owner.open_mounted_payload(_id("other-payload"), 30, lambda: None)
    snapshot = h1_shared_cap_owner_snapshot_v2(owner)
    assert snapshot["actual"]["io.mounted_bytes_peak"] == 70
    assert snapshot["mounted_current"] == 70
    assert snapshot["active_mount_count"] == 3
    with pytest.raises(H1SharedCapProtocolFailureV2, match="descendant reap"):
        owner.close_mounted_payload(first, lambda: None)

    # A protocol-failed owner is intentionally not recoverable.  Rebuild the
    # positive lifecycle rather than hiding the failed prefix.
    owner = _exercise()
    owner.bind_working_hierarchy(lambda _binding: None)
    output = owner.begin_route_output()
    first = owner.open_mounted_payload(payload, 40, lambda: None)
    second = owner.open_mounted_payload(payload, 40, lambda: None)
    third = owner.open_mounted_payload(_id("other-payload"), 30, lambda: None)
    owner.launch_registered_role("WORKER", lambda: _id("worker-edge"))
    owner.launch_registered_role("BUSINESS", lambda: _id("business-edge"))
    owner.mark_trusted_descendants_reaped(
        worker_pidfd_observation_id=_id("worker-reap"),
        business_pidfd_observation_id=_id("business-reap"),
        retained_memory_peak_ofd_plan_id=_id("memory-ofd-plan"),
    )
    owner.close_mounted_payload(first, lambda: None)
    assert h1_shared_cap_owner_snapshot_v2(owner)["mounted_current"] == 70
    owner.close_mounted_payload(second, lambda: None)
    assert h1_shared_cap_owner_snapshot_v2(owner)["mounted_current"] == 30
    owner.close_mounted_payload(third, lambda: None)
    assert h1_shared_cap_owner_snapshot_v2(owner)["mounted_current"] == 0
    owner.read_working_bytes_peak(lambda: 275)
    owner.finalize_route_output(output, 80, lambda: None)
    owner.close()
    assert h1_shared_cap_owner_snapshot_v2(owner)["mode"] == "CLOSED"


def test_mount_callback_cannot_reenter_and_hide_a_larger_peak() -> None:
    caps = _caps()
    caps["io.mounted_bytes_peak"] = 100
    owner = _exercise(caps=caps)
    owner.bind_working_hierarchy(lambda _binding: None)
    nested_calls: list[str] = []

    def nested_open() -> None:
        owner.open_mounted_payload(
            _id("nested-physical-payload"),
            60,
            lambda: nested_calls.append("nested-side-effect"),
        )

    with pytest.raises(H1SharedCapProtocolFailureV2, match="after admission"):
        owner.open_mounted_payload(_id("outer-physical-payload"), 60, nested_open)
    snapshot = h1_shared_cap_owner_snapshot_v2(owner)
    assert nested_calls == []
    assert snapshot["mode"] == "PROTOCOL_FAILURE"
    assert snapshot["mounted_current"] == 0
    assert snapshot["actual"]["io.mounted_bytes_peak"] == 60
    assert snapshot["operation_in_flight"] is False


def test_callback_cannot_conceal_a_nested_mutation_failure() -> None:
    owner = _exercise()
    owner.bind_working_hierarchy(lambda _binding: None)

    def conceal_nested_failure() -> None:
        try:
            owner.record_integrity_check(lambda: None)
        except H1SharedCapProtocolFailureV2:
            pass

    with pytest.raises(
        H1SharedCapProtocolFailureV2,
        match="after admission",
    ):
        owner.record_hash_invocation(conceal_nested_failure)
    snapshot = h1_shared_cap_owner_snapshot_v2(owner)
    assert snapshot["mode"] == "PROTOCOL_FAILURE"
    assert snapshot["actual"]["common.integrity_checks"] == 0


def test_mount_tokens_are_unique_sealed_and_cannot_redirect_cleanup() -> None:
    owner = _exercise()
    owner.bind_working_hierarchy(lambda _binding: None)
    owner.begin_route_output()
    payload = _id("same-physical-payload")
    first = owner.open_mounted_payload(payload, 20, lambda: None)
    second = owner.open_mounted_payload(payload, 20, lambda: None)
    assert first.token_id != second.token_id
    object.__setattr__(first, "payload_identity_id", _id("redirected-payload"))
    owner.launch_registered_role("WORKER", lambda: None)
    owner.launch_registered_role("BUSINESS", lambda: None)
    owner.mark_trusted_descendants_reaped(
        worker_pidfd_observation_id=_id("worker-reap"),
        business_pidfd_observation_id=_id("business-reap"),
        retained_memory_peak_ofd_plan_id=_id("memory-ofd-plan"),
    )
    with pytest.raises(ValueError, match="foreign or belongs|stale, foreign"):
        owner.close_mounted_payload(first, lambda: None)


def test_snapshot_is_a_deep_copy_of_the_atomic_journal() -> None:
    owner = _exercise()
    owner.bind_working_hierarchy(lambda _binding: None)
    owner.record_hash_invocation(lambda: None)
    exposed = h1_shared_cap_owner_snapshot_v2(owner)
    exposed["receipts"][0]["detail"]["forged"] = True
    exposed["semantic_events"][0]["detail"]["forged"] = True
    replay = h1_shared_cap_owner_snapshot_v2(owner)
    assert "forged" not in replay["receipts"][0]["detail"]
    assert "forged" not in replay["semantic_events"][0]["detail"]


def test_launch_topology_is_exactly_worker_then_business_and_two() -> None:
    owner = _exercise()
    owner.bind_working_hierarchy(lambda _binding: None)
    owner.begin_route_output()
    with pytest.raises(H1SharedCapProtocolFailureV2, match="requires WORKER"):
        owner.launch_registered_role("BUSINESS", lambda: None)

    owner = _exercise()
    owner.bind_working_hierarchy(lambda _binding: None)
    owner.begin_route_output()
    observed: list[tuple[str, int]] = []
    for role in EXACT_CHILD_LAUNCH_ORDER:
        owner.launch_registered_role(
            role,
            lambda role=role: observed.append(
                (
                    role,
                    h1_shared_cap_owner_snapshot_v2(owner)["outstanding"][
                        "process.launches"
                    ],
                )
            ),
        )
    assert observed == [("WORKER", 1), ("BUSINESS", 1)]
    snapshot = h1_shared_cap_owner_snapshot_v2(owner)
    assert snapshot["launch_order"] == ["WORKER", "BUSINESS"]
    assert snapshot["process_launches_exact"] == 2


def test_cap_rejection_occurs_before_callback_and_is_reserved_at_one() -> None:
    caps = _caps()
    caps["io.read_bytes"] = 3
    owner = _exercise(caps=caps)
    owner.bind_working_hierarchy(lambda _binding: None)
    calls: list[str] = []
    with pytest.raises(H1SharedCapExhaustedV2, match="io.read_bytes"):
        owner.read_registered_payload(4, lambda: calls.append("read") or b"1234")
    assert calls == []
    snapshot = h1_shared_cap_owner_snapshot_v2(owner)
    assert snapshot["mode"] == "CAP_EXHAUSTED"
    assert snapshot["control"] == {
        "cap_checks": 2,
        "cap_rejections": 1,
        "cap_rejections_upper": EXACT_CONTROL_CAP_REJECTIONS_UPPER,
    }
    assert snapshot["actual"]["io.read_bytes"] == 0
    assert snapshot["receipts"][-1]["settlement"] == (
        "CAP_REJECTED_BEFORE_SIDE_EFFECT"
    )
    assert snapshot["receipts"][-1]["detail"]["side_effect_started"] is False
    assert snapshot["receipts"][-1]["control_cap_rejections_after_event"] == 1


def test_prebinding_protocol_failure_needs_no_phantom_cleanup() -> None:
    owner = _exercise()
    with pytest.raises(H1SharedCapProtocolFailureV2, match="hierarchy must bind"):
        owner.record_hash_invocation(lambda: None)
    owner.close_failed_cleanup()
    snapshot = h1_shared_cap_owner_snapshot_v2(owner)
    assert snapshot["cleanup_closed"] is True
    assert snapshot["ambiguous_memory_binding"] is False
    assert snapshot["descendants_reaped"] is False
    assert snapshot["memory_observed"] is False


def test_failed_known_one_child_prefix_requires_only_worker_reap() -> None:
    owner = _exercise(checks=3)
    owner.bind_working_hierarchy(lambda _binding: None)
    output = owner.begin_route_output()
    owner.launch_registered_role("WORKER", lambda: None)
    with pytest.raises(H1SharedCapExhaustedV2, match="control.cap_checks"):
        owner.launch_registered_role("BUSINESS", lambda: None)
    owner.mark_trusted_descendants_reaped(
        worker_pidfd_observation_id=_id("worker-only-reap"),
        business_pidfd_observation_id=None,
        retained_memory_peak_ofd_plan_id=_id("memory-ofd-plan"),
    )
    owner.read_working_bytes_peak(lambda: 200)
    owner.finalize_route_output(output, 80, lambda: None)
    owner.close_failed_cleanup()
    snapshot = h1_shared_cap_owner_snapshot_v2(owner)
    assert snapshot["launch_order"] == ["WORKER"]
    assert snapshot["cleanup_closed"] is True


def test_reap_observation_for_unlaunched_role_is_rejected() -> None:
    owner = _exercise(checks=3)
    owner.bind_working_hierarchy(lambda _binding: None)
    owner.begin_route_output()
    owner.launch_registered_role("WORKER", lambda: None)
    with pytest.raises(H1SharedCapExhaustedV2):
        owner.launch_registered_role("BUSINESS", lambda: None)
    with pytest.raises(H1SharedCapProtocolFailureV2, match="not launched"):
        owner.mark_trusted_descendants_reaped(
            worker_pidfd_observation_id=_id("worker-only-reap"),
            business_pidfd_observation_id=_id("fabricated-business-reap"),
            retained_memory_peak_ofd_plan_id=_id("memory-ofd-plan"),
        )


def test_descendant_reap_is_exact_once_and_retains_both_pidfd_observations() -> None:
    owner = _exercise()
    owner.bind_working_hierarchy(lambda _binding: None)
    owner.begin_route_output()
    owner.launch_registered_role("WORKER", lambda: None)
    owner.launch_registered_role("BUSINESS", lambda: None)
    worker_observation = _id("retained-worker-reap")
    business_observation = _id("retained-business-reap")
    owner.mark_trusted_descendants_reaped(
        worker_pidfd_observation_id=worker_observation,
        business_pidfd_observation_id=business_observation,
        retained_memory_peak_ofd_plan_id=_id("memory-ofd-plan"),
    )
    snapshot = h1_shared_cap_owner_snapshot_v2(owner)
    assert snapshot["reap_exact_once"] is True
    assert snapshot["reap_transition_count"] == 1
    assert snapshot["reap_observations_native_verified"] is False
    assert snapshot["reap_observations_role_bound"] is False
    assert snapshot["reap_pidfd_observation_ids"] == {
        "WORKER": worker_observation,
        "BUSINESS": business_observation,
    }
    with pytest.raises(H1SharedCapProtocolFailureV2, match="exactly once"):
        owner.mark_trusted_descendants_reaped(
            worker_pidfd_observation_id=worker_observation,
            business_pidfd_observation_id=business_observation,
            retained_memory_peak_ofd_plan_id=_id("memory-ofd-plan"),
        )
    failed = h1_shared_cap_owner_snapshot_v2(owner)
    assert failed["mode"] == "PROTOCOL_FAILURE"
    assert failed["reap_pidfd_observation_ids"] == snapshot[
        "reap_pidfd_observation_ids"
    ]
    assert verify_h1_shared_cap_failure_cause_chain_v2(owner) is True


def test_cleanup_failure_is_secondary_and_preserves_cap_exhausted_primary() -> None:
    owner = _exercise(checks=3)
    owner.bind_working_hierarchy(lambda _binding: None)
    owner.begin_route_output()
    owner.launch_registered_role("WORKER", lambda: None)
    with pytest.raises(H1SharedCapExhaustedV2):
        owner.launch_registered_role("BUSINESS", lambda: None)

    with pytest.raises(H1SharedCapProtocolFailureV2, match="not launched"):
        owner.mark_trusted_descendants_reaped(
            worker_pidfd_observation_id=_id("worker-only-reap"),
            business_pidfd_observation_id=_id("fabricated-business-reap"),
            retained_memory_peak_ofd_plan_id=_id("memory-ofd-plan"),
        )

    snapshot = h1_shared_cap_owner_snapshot_v2(owner)
    assert snapshot["mode"] == "CAP_EXHAUSTED"
    assert snapshot["primary_failure"]["kind"] == "PRIMARY"
    assert snapshot["primary_failure"]["observed_mode"] == "CAP_EXHAUSTED"
    assert snapshot["secondary_failures"][-1]["kind"] == "SECONDARY"
    assert snapshot["secondary_failures"][-1]["cleanup_phase"] is True
    assert snapshot["secondary_failures"][-1]["observed_mode"] == (
        "PROTOCOL_FAILURE"
    )
    assert snapshot["secondary_failures"][-1][
        "preserved_primary_mode"
    ] == "CAP_EXHAUSTED"
    assert snapshot["primary_failure_mode_preserved"] is True
    assert snapshot["failure_cause_chain_verified"] is True
    assert verify_h1_shared_cap_failure_cause_chain_v2(owner) is True

    owner.mark_trusted_descendants_reaped(
        worker_pidfd_observation_id=_id("worker-only-reap"),
        business_pidfd_observation_id=None,
        retained_memory_peak_ofd_plan_id=_id("memory-ofd-plan"),
    )
    assert h1_shared_cap_owner_snapshot_v2(owner)["mode"] == "CAP_EXHAUSTED"


def test_secondary_cleanup_observation_does_not_inherit_cap_mode() -> None:
    caps = _caps()
    caps["io.read_bytes"] = 0
    owner = _exercise(caps=caps)
    owner.bind_working_hierarchy(lambda _binding: None)
    owner.begin_route_output()
    owner.launch_registered_role("WORKER", lambda: None)
    owner.launch_registered_role("BUSINESS", lambda: None)
    with pytest.raises(H1SharedCapExhaustedV2):
        owner.read_registered_payload(1, lambda: b"x")

    with pytest.raises(ValueError, match="worker pidfd reap observation"):
        owner.mark_trusted_descendants_reaped(
            worker_pidfd_observation_id="not-a-content-id",
            business_pidfd_observation_id=_id("business-reap"),
            retained_memory_peak_ofd_plan_id=_id("memory-ofd-plan"),
        )

    secondary = h1_shared_cap_owner_snapshot_v2(owner)["secondary_failures"][-1]
    assert secondary["kind"] == "SECONDARY"
    assert secondary["cleanup_phase"] is True
    assert secondary["observed_mode"] == "PROTOCOL_FAILURE"
    assert secondary["preserved_primary_mode"] == "CAP_EXHAUSTED"


def test_late_cap_rejection_retains_cleanup_only_lifecycle() -> None:
    caps = _caps()
    caps["io.read_bytes"] = 0
    owner = _exercise(caps=caps)
    owner.bind_working_hierarchy(lambda _binding: None)
    output = owner.begin_route_output()
    mount = owner.open_mounted_payload(_id("cleanup-payload"), 20, lambda: None)
    owner.launch_registered_role("WORKER", lambda: None)
    owner.launch_registered_role("BUSINESS", lambda: None)
    with pytest.raises(H1SharedCapExhaustedV2):
        owner.read_registered_payload(1, lambda: b"x")
    owner.mark_trusted_descendants_reaped(
        worker_pidfd_observation_id=_id("worker-reap"),
        business_pidfd_observation_id=_id("business-reap"),
        retained_memory_peak_ofd_plan_id=_id("memory-ofd-plan"),
    )
    owner.read_working_bytes_peak(lambda: 250)
    owner.close_mounted_payload(mount, lambda: None)
    owner.finalize_route_output(output, 80, lambda: None)
    owner.close_failed_cleanup()
    snapshot = h1_shared_cap_owner_snapshot_v2(owner)
    assert snapshot["mode"] == "CAP_EXHAUSTED"
    assert snapshot["cleanup_closed"] is True
    assert snapshot["active_mount_count"] == 0
    assert not any(snapshot["outstanding"].values())
    with pytest.raises(H1SharedCapProtocolFailureV2, match="already closed"):
        owner.close_failed_cleanup()


def test_callback_failure_full_charges_and_atomically_pairs_receipt_event() -> None:
    owner = _exercise()
    owner.bind_working_hierarchy(lambda _binding: None)

    def explode() -> bytes:
        snapshot = h1_shared_cap_owner_snapshot_v2(owner)
        assert snapshot["outstanding"]["io.read_bytes"] == 9
        raise RuntimeError("boom")

    with pytest.raises(H1SharedCapProtocolFailureV2, match="after admission"):
        owner.read_registered_payload(9, explode)
    snapshot = h1_shared_cap_owner_snapshot_v2(owner)
    assert snapshot["mode"] == H1SharedOwnerModeV2.PROTOCOL_FAILURE.value
    assert snapshot["actual"]["io.read_bytes"] == 9
    assert len(snapshot["receipts"]) == len(snapshot["semantic_events"]) == 2
    for receipt, event in zip(snapshot["receipts"], snapshot["semantic_events"]):
        assert receipt["atomic_pair_sequence"] == event["atomic_pair_sequence"]
        assert receipt["path"] == event["path"]
        assert receipt["actual"] == event["actual"]
    assert snapshot["receipts"][-1]["settlement"] == (
        "FULL_RESERVATION_ON_CALLBACK_FAILURE"
    )


def test_failed_mount_open_retains_native_existence_ambiguity() -> None:
    owner = _exercise()
    owner.bind_working_hierarchy(lambda _binding: None)
    owner.begin_route_output()
    payload_id = _id("ambiguous-native-mount")
    visible: list[str] = []

    def fail_after_visibility() -> None:
        visible.append("native-mounted")
        raise RuntimeError("mount syscall wrapper lost acknowledgement")

    with pytest.raises(H1SharedCapProtocolFailureV2, match="mount callback"):
        owner.open_mounted_payload(payload_id, 20, fail_after_visibility)
    assert visible == ["native-mounted"]
    snapshot = h1_shared_cap_owner_snapshot_v2(owner)
    assert snapshot["active_mount_count"] == 0
    assert snapshot["ambiguous_mount_opens"] == {payload_id: 20}
    with pytest.raises(H1SharedCapProtocolFailureV2, match="unresolved resources"):
        owner.close_failed_cleanup()


@pytest.mark.parametrize(
    ("kind", "expected_actual"),
    (("read", 2), ("stage", 2)),
)
def test_observed_sum_overrun_preserves_the_true_actual(
    kind: str, expected_actual: int
) -> None:
    owner = _exercise()
    owner.bind_working_hierarchy(lambda _binding: None)
    with pytest.raises(H1SharedCapProtocolFailureV2, match="observed actual"):
        if kind == "read":
            owner.read_registered_payload(1, lambda: b"12")
        else:
            owner.stage_registered_payload(
                1,
                H1SharedIngressKindV2.COPY_INTO_EXECUTION_SANDBOX,
                lambda: 2,
            )
    path = "io.read_bytes" if kind == "read" else "io.staged_bytes"
    snapshot = h1_shared_cap_owner_snapshot_v2(owner)
    assert snapshot["actual"][path] == expected_actual
    assert snapshot["receipts"][-1]["actual"] == expected_actual
    assert snapshot["receipts"][-1]["settlement"] == (
        "OBSERVED_UPPER_BOUND_VIOLATION"
    )


def test_observed_memory_overrun_preserves_the_true_peak() -> None:
    owner = _exercise()
    owner.bind_working_hierarchy(lambda _binding: None)
    output = owner.begin_route_output()
    owner.launch_registered_role("WORKER", lambda: None)
    owner.launch_registered_role("BUSINESS", lambda: None)
    owner.mark_trusted_descendants_reaped(
        worker_pidfd_observation_id=_id("worker-reap"),
        business_pidfd_observation_id=_id("business-reap"),
        retained_memory_peak_ofd_plan_id=_id("memory-ofd-plan"),
    )
    with pytest.raises(H1SharedCapProtocolFailureV2, match="observed actual"):
        owner.read_working_bytes_peak(lambda: 351)
    snapshot = h1_shared_cap_owner_snapshot_v2(owner)
    assert snapshot["actual"]["memory.working_bytes_peak"] == 351
    assert snapshot["receipts"][-1]["actual"] == 351
    assert snapshot["memory_peak_terminal"] == "OBSERVED_UPPER_BOUND_VIOLATION"
    assert snapshot["memory_peak_terminal_settled"] is True
    retry_reads: list[str] = []
    with pytest.raises(H1SharedCapProtocolFailureV2, match="pending post-reap"):
        owner.read_working_bytes_peak(
            lambda: retry_reads.append("duplicate-read") or 1
        )
    assert retry_reads == []
    owner.finalize_route_output(output, 80, lambda: None)
    owner.close_failed_cleanup()


def test_observed_output_overrun_preserves_the_true_extent() -> None:
    owner = _exercise()
    owner.bind_working_hierarchy(lambda _binding: None)
    output = owner.begin_route_output()
    owner.launch_registered_role("WORKER", lambda: None)
    owner.launch_registered_role("BUSINESS", lambda: None)
    owner.mark_trusted_descendants_reaped(
        worker_pidfd_observation_id=_id("worker-reap"),
        business_pidfd_observation_id=_id("business-reap"),
        retained_memory_peak_ofd_plan_id=_id("memory-ofd-plan"),
    )
    owner.read_working_bytes_peak(lambda: 1)
    with pytest.raises(H1SharedCapProtocolFailureV2, match="observed actual"):
        owner.finalize_route_output(output, 121, lambda: None)
    snapshot = h1_shared_cap_owner_snapshot_v2(owner)
    assert snapshot["actual"]["io.output_bytes"] == 121
    assert snapshot["receipts"][-1]["actual"] == 121


def test_output_callback_failure_does_not_clip_known_overrun() -> None:
    owner = _exercise()
    owner.bind_working_hierarchy(lambda _binding: None)
    output = owner.begin_route_output()
    owner.launch_registered_role("WORKER", lambda: None)
    owner.launch_registered_role("BUSINESS", lambda: None)
    owner.mark_trusted_descendants_reaped(
        worker_pidfd_observation_id=_id("worker-reap"),
        business_pidfd_observation_id=_id("business-reap"),
        retained_memory_peak_ofd_plan_id=_id("memory-ofd-plan"),
    )
    owner.read_working_bytes_peak(lambda: 1)
    with pytest.raises(H1SharedCapProtocolFailureV2, match="observed actual"):
        owner.finalize_route_output(
            output,
            121,
            lambda: (_ for _ in ()).throw(RuntimeError("write failed")),
        )
    snapshot = h1_shared_cap_owner_snapshot_v2(owner)
    assert snapshot["actual"]["io.output_bytes"] == 121
    assert snapshot["receipts"][-1]["actual"] == 121
    assert snapshot["receipts"][-1]["settlement"] == (
        "OBSERVED_UPPER_BOUND_VIOLATION"
    )
    assert snapshot["receipts"][-1]["detail"][
        "finalization_callback_failed"
    ] is True


def test_output_callback_failure_is_terminal_and_retry_cannot_write() -> None:
    owner = _exercise()
    owner.bind_working_hierarchy(lambda _binding: None)
    output = owner.begin_route_output()
    owner.launch_registered_role("WORKER", lambda: None)
    owner.launch_registered_role("BUSINESS", lambda: None)
    owner.mark_trusted_descendants_reaped(
        worker_pidfd_observation_id=_id("worker-reap"),
        business_pidfd_observation_id=_id("business-reap"),
        retained_memory_peak_ofd_plan_id=_id("memory-ofd-plan"),
    )
    owner.read_working_bytes_peak(lambda: 1)

    with pytest.raises(H1SharedCapProtocolFailureV2, match="finalization failed"):
        owner.finalize_route_output(
            output,
            80,
            lambda: (_ for _ in ()).throw(RuntimeError("write failed")),
        )
    failed = h1_shared_cap_owner_snapshot_v2(owner)
    assert failed["output_terminal"] == "FAILED_UPPER_ONLY"
    assert failed["output_terminal_settled"] is True
    assert failed["output_finalized"] is False
    assert failed["outstanding"]["io.output_bytes"] == 0

    retry_side_effects: list[str] = []
    with pytest.raises(H1SharedCapProtocolFailureV2, match="terminal output"):
        owner.finalize_route_output(
            output,
            80,
            lambda: retry_side_effects.append("duplicate-write"),
        )
    assert retry_side_effects == []
    owner.close_failed_cleanup()
    assert h1_shared_cap_owner_snapshot_v2(owner)["cleanup_closed"] is True


def test_output_overrun_is_terminal_and_retry_cannot_write() -> None:
    owner = _exercise()
    owner.bind_working_hierarchy(lambda _binding: None)
    output = owner.begin_route_output()
    owner.launch_registered_role("WORKER", lambda: None)
    owner.launch_registered_role("BUSINESS", lambda: None)
    owner.mark_trusted_descendants_reaped(
        worker_pidfd_observation_id=_id("worker-reap"),
        business_pidfd_observation_id=_id("business-reap"),
        retained_memory_peak_ofd_plan_id=_id("memory-ofd-plan"),
    )
    owner.read_working_bytes_peak(lambda: 1)
    with pytest.raises(H1SharedCapProtocolFailureV2, match="observed actual"):
        owner.finalize_route_output(output, 121, lambda: None)

    snapshot = h1_shared_cap_owner_snapshot_v2(owner)
    assert snapshot["output_terminal"] == "OBSERVED_UPPER_BOUND_VIOLATION"
    retry_side_effects: list[str] = []
    with pytest.raises(H1SharedCapProtocolFailureV2, match="terminal output"):
        owner.finalize_route_output(
            output,
            121,
            lambda: retry_side_effects.append("duplicate-write"),
        )
    assert retry_side_effects == []
    owner.close_failed_cleanup()


def test_memory_peak_callback_failure_is_upper_only_and_cleanup_can_close() -> None:
    owner = _exercise()
    owner.bind_working_hierarchy(lambda _binding: None)
    output = owner.begin_route_output()
    owner.launch_registered_role("WORKER", lambda: None)
    owner.launch_registered_role("BUSINESS", lambda: None)
    owner.mark_trusted_descendants_reaped(
        worker_pidfd_observation_id=_id("worker-reap"),
        business_pidfd_observation_id=_id("business-reap"),
        retained_memory_peak_ofd_plan_id=_id("memory-ofd-plan"),
    )
    with pytest.raises(H1SharedCapProtocolFailureV2, match="peak read failed"):
        owner.read_working_bytes_peak(
            lambda: (_ for _ in ()).throw(RuntimeError("read failed"))
        )

    failed = h1_shared_cap_owner_snapshot_v2(owner)
    assert failed["memory_peak_terminal"] == "FAILED_UPPER_ONLY"
    assert failed["memory_peak_terminal_settled"] is True
    assert failed["memory_observed"] is False
    assert failed["outstanding"]["memory.working_bytes_peak"] == 0

    retry_reads: list[str] = []
    with pytest.raises(H1SharedCapProtocolFailureV2, match="pending post-reap"):
        owner.read_working_bytes_peak(
            lambda: retry_reads.append("duplicate-read") or 1
        )
    assert retry_reads == []
    owner.finalize_route_output(output, 80, lambda: None)
    owner.close_failed_cleanup()
    assert h1_shared_cap_owner_snapshot_v2(owner)["cleanup_closed"] is True


def test_output_cannot_finalize_before_children_and_peak_lifecycle() -> None:
    owner = _exercise()
    owner.bind_working_hierarchy(lambda _binding: None)
    output = owner.begin_route_output()
    calls: list[str] = []
    with pytest.raises(H1SharedCapProtocolFailureV2, match="known launch prefix"):
        owner.finalize_route_output(
            output, 80, lambda: calls.append("premature-write")
        )
    assert calls == []
    snapshot = h1_shared_cap_owner_snapshot_v2(owner)
    assert snapshot["output_finalized"] is False
    assert snapshot["actual"]["io.output_bytes"] == 0
    assert snapshot["mode"] == "PROTOCOL_FAILURE"


@pytest.mark.parametrize(
    "operation",
    ("hash", "integrity", "protocol", "read", "stage"),
)
def test_no_shared_resource_mutation_after_final_output(operation: str) -> None:
    owner = _exercise()
    owner.bind_working_hierarchy(lambda _binding: None)
    output = owner.begin_route_output()
    owner.launch_registered_role("WORKER", lambda: None)
    owner.launch_registered_role("BUSINESS", lambda: None)
    owner.mark_trusted_descendants_reaped(
        worker_pidfd_observation_id=_id("worker-reap"),
        business_pidfd_observation_id=_id("business-reap"),
        retained_memory_peak_ofd_plan_id=_id("memory-ofd-plan"),
    )
    owner.read_working_bytes_peak(lambda: 1)
    owner.finalize_route_output(output, 80, lambda: None)
    called: list[str] = []
    with pytest.raises(H1SharedCapProtocolFailureV2, match="terminal output"):
        if operation == "hash":
            owner.record_hash_invocation(lambda: called.append(operation))
        elif operation == "integrity":
            owner.record_integrity_check(lambda: called.append(operation))
        elif operation == "protocol":
            owner.record_protocol_check(lambda: called.append(operation))
        elif operation == "read":
            owner.read_registered_payload(
                1, lambda: called.append(operation) or b"x"
            )
        else:
            owner.stage_registered_payload(
                1,
                H1SharedIngressKindV2.COPY_INTO_EXECUTION_SANDBOX,
                lambda: called.append(operation) or 1,
            )
    assert called == []
    owner.close_failed_cleanup()
    assert h1_shared_cap_owner_snapshot_v2(owner)["cleanup_closed"] is True


def test_complete_construction_lifecycle_covers_all_nine_paths() -> None:
    owner = _exercise()
    owner.bind_working_hierarchy(lambda _binding: None)
    output = owner.begin_route_output()
    mount = owner.open_mounted_payload(_id("payload"), 20, lambda: None)
    owner.record_hash_invocation(lambda: None)
    owner.record_integrity_check(lambda: None)
    owner.record_protocol_check(lambda: None)
    owner.read_registered_payload(8, lambda: b"12345")
    owner.stage_registered_payload(
        8, H1SharedIngressKindV2.BIND_INTO_EXECUTION_SANDBOX, lambda: 8
    )
    owner.launch_registered_role("WORKER", lambda: None)
    owner.launch_registered_role("BUSINESS", lambda: None)
    owner.mark_trusted_descendants_reaped(
        worker_pidfd_observation_id=_id("worker-reap"),
        business_pidfd_observation_id=_id("business-reap"),
        retained_memory_peak_ofd_plan_id=_id("memory-ofd-plan"),
    )
    owner.read_working_bytes_peak(lambda: 300)
    owner.close_mounted_payload(mount, lambda: None)
    owner.finalize_route_output(output, 90, lambda: None)
    owner.close()
    snapshot = h1_shared_cap_owner_snapshot_v2(owner)
    assert snapshot["mode"] == "CLOSED"
    assert set(row["path"] for row in snapshot["receipts"]) == set(
        SHARED_RESOURCE_PATHS
    )
    assert snapshot["actual"] == {
        "common.hash_invocations": 1,
        "common.integrity_checks": 1,
        "common.protocol_checks": 1,
        "io.mounted_bytes_peak": 20,
        "io.output_bytes": 90,
        "io.read_bytes": 5,
        "io.staged_bytes": 8,
        "memory.working_bytes_peak": 300,
        "process.launches": 2,
    }
    assert snapshot["formal_actual_compliance_eligible"] is False
    assert snapshot["official_execution_allowed"] is False
