from __future__ import annotations

import hashlib
import os
from pathlib import Path
import shutil
import stat
import tempfile
import threading

import pytest

from acfqp import construction_k7_h1_anchored_lifecycle_dispatch_v1 as dispatch_v1
from acfqp import construction_k7_h1_attempt_execution_phase_owner_v1 as phase_v1
from acfqp import construction_k7_h1_failed_prefix_cleanup_budget_admission_v1 as admission_v1
from acfqp import construction_k7_h1_lifecycle_complete_cleanup_v1 as cleanup_v1
from acfqp import construction_k7_h1_lifecycle_output_leaf_join_v1 as output_join_v1
from acfqp import construction_k7_h1_native_resource_receipt_journal_v1 as receipts_v1
from acfqp import construction_k7_h1_phase_aware_normal_prefix_v1 as normal_v1
from acfqp import construction_k7_h1_preadmitted_cleanup_transition_v2 as cleanup_v2
from acfqp import construction_k7_h1_shared_cap_owner_v3 as owner_v3
from acfqp import construction_k7_h1_shared_cap_owner_v4_wal as owner_v4

from test_construction_k7_h1_phase_aware_normal_prefix_v1 import (
    _build_case,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
EXPECTED_ANCHOR_ID = (
    "4a4b0d1888f0ac18123e4163e1a26b0583a64946d2eb219e02d4b77dc0a3e327"
)
EXACT_BUDGET = {
    "RESOLVE": 1,
    "REAP": 2,
    "MOUNT_CLOSE": 10,
    "MEMORY_RELEASE": 1,
    "OUTPUT_RELEASE": 1,
}


@pytest.fixture(scope="module")
def bundle():
    return dispatch_v1.freeze_h1_anchored_lifecycle_dispatch_bundle_v1(
        REPOSITORY_ROOT, expected_anchor_id=EXPECTED_ANCHOR_ID
    )


@pytest.fixture(scope="module")
def analysis(bundle):
    return cleanup_v1.derive_h1_lifecycle_complete_branch_analysis_v1(
        bundle, output_join_v1.build_h1_lifecycle_output_leaf_join_v1(bundle)
    )


@pytest.fixture
def fast_root():
    base = "/dev/shm" if Path("/dev/shm").is_dir() else "/tmp"
    path = Path(tempfile.mkdtemp(prefix="acfqp-h1-cleanup-budget-", dir=base))
    try:
        yield path
    finally:
        shutil.rmtree(path)


def _lease(case, bundle):
    return normal_v1.hold_h1_phase_aware_normal_prefix_lease_v1(
        case.normal,
        phase_handle=case.phase,
        rejection_gate=case.gate,
        owner=case.owner,
        bundle=bundle,
        dispatch_profile=case.dispatch_profile,
    )


def _prerequisites(root, case, bundle, analysis):
    with _lease(case, bundle) as lease:
        envelope = cleanup_v2.preadmit_h1_normal_prefix_cleanup_envelope_v2(
            lease, cleanup_analysis=analysis
        )
    spec = receipts_v1.freeze_h1_native_receipt_journal_spec_v1(
        root, normal_handle=case.normal
    )
    handle = receipts_v1.initialize_h1_native_receipt_journal_v1(
        spec, normal_handle=case.normal
    )
    return envelope, spec, handle


def _admit(case, bundle, analysis, envelope, spec, handle, budget=EXACT_BUDGET):
    with _lease(case, bundle) as lease:
        return admission_v1.admit_h1_failed_prefix_cleanup_budget_v1(
            lease,
            envelope=envelope,
            cleanup_analysis=analysis,
            native_receipt_spec=spec,
            native_receipt_handle=handle,
            available_cleanup_budget=budget,
        )


def _attempt_directory(root, case):
    return (
        root
        / admission_v1._ROOT_NAME
        / case.phase.spec.payload["route_attempt_id"]
    )


def test_exact_112_111_branchwise_maxima_and_real_v6_binding_are_admitted_once(
    fast_root, bundle, analysis
):
    case = _build_case(fast_root, bundle, analysis, suffix="exact")
    envelope, spec, handle = _prerequisites(
        fast_root, case, bundle, analysis
    )
    admission = _admit(case, bundle, analysis, envelope, spec, handle)
    repeated = _admit(case, bundle, analysis, envelope, spec, handle)
    payload = admission.payload
    assert repeated.admission_id == admission.admission_id
    assert payload["registered_failure_branch_count"] == 112
    assert payload["dispatcher_reachable_failure_branch_count"] == 111
    assert payload["unreachable_negative_control_branch_count"] == 1
    assert payload["branchwise_cleanup_maxima"] == EXACT_BUDGET
    assert payload["branchwise_cleanup_maximum_total"] == 15
    assert payload["available_cleanup_budget_total"] == 15
    assert len(payload["branch_budget_rows"]) == 112
    assert {
        row["h1_lifecycle_cleanup_pass_id"]
        for row in payload["branch_budget_rows"]
    } == {
        row["h1_lifecycle_cleanup_pass_id"]
        for row in envelope.payload["failure_branch_action_whitelist"]
    }
    assert payload["h1_native_receipt_journal_spec_id"] == spec.spec_id
    assert payload["h1_native_receipt_allocation_id"] == handle.allocation_id
    assert payload["native_receipt_record_count_at_admission"] == 0
    attempt = _attempt_directory(fast_root, case)
    primary = attempt / admission_v1._ADMISSION_FILE
    seal = (
        fast_root
        / f"{admission_v1._SEAL_PREFIX}{case.phase.spec.payload['route_attempt_id']}"
    )
    assert primary.stat().st_ino == seal.stat().st_ino
    assert primary.stat().st_nlink == 2
    assert primary.read_bytes() == admission.canonical_bytes


def test_v5_binding_is_explicitly_prospective_and_all_authority_nonclaims_hold(
    fast_root, bundle, analysis
):
    case = _build_case(fast_root, bundle, analysis, suffix="prospective")
    envelope, spec, handle = _prerequisites(
        fast_root, case, bundle, analysis
    )
    admission = _admit(case, bundle, analysis, envelope, spec, handle)
    payload = admission.payload
    baseline = payload["prospective_owner_cleanup_sidecar_baseline"]
    assert baseline["actual_h1_owner_cleanup_sidecar_spec_id"] == {
        "kind": "NOT_APPLICABLE",
        "reason": "V5_SPEC_CAN_ONLY_BIND_THE_SELECTED_POST_FAILURE_ACTION",
    }
    assert baseline["actual_h1_owner_cleanup_sidecar_allocation_id"] == {
        "kind": "NOT_APPLICABLE",
        "reason": "V5_ALLOCATION_DOES_NOT_EXIST_BEFORE_NORMAL_ORDINAL_1",
    }
    assert baseline["prospective_baseline_is_not_a_v5_spec_or_allocation"] is True
    assert baseline["future_v5_spec_must_bind_exact_selected_transition_pass_action"] is True
    assert baseline["future_v5_spec_must_bind_stable_failure_time_owner_cutoff"] is True
    assert payload["actual_v5_sidecar_spec_allocation_present"] is False
    assert payload["v5_binding_is_prospective_only"] is True
    assert payload["later_native_cutoff_receipt_join_present"] is False
    assert payload["fq11_cleanup_counter_leaf_ratified"] is False
    assert payload["cleanup_budget_units_are_construction_admission_tokens_only"] is True
    assert payload["cleanup_action_execution_authority_present"] is False
    assert payload["native_cleanup_effect_authority_present"] is False
    assert payload["current_access_authority_present"] is False
    assert payload["formal_counter_records_issued"] is False
    assert payload["formal_work_vector_issued"] is False
    assert payload["formal_comparison_vector_issued"] is False
    assert payload["formal_v7_route_authority_present"] is False
    assert payload["official_execution_allowed"] is False


@pytest.mark.parametrize(
    "budget",
    [
        {**EXACT_BUDGET, "MOUNT_CLOSE": 9},
        {key: value for key, value in EXACT_BUDGET.items() if key != "REAP"},
        {**EXACT_BUDGET, "UNKNOWN": 1},
        {**EXACT_BUDGET, "RESOLVE": True},
    ],
)
def test_insufficient_or_malformed_budget_rejects_before_admission_mutation(
    fast_root, bundle, analysis, budget
):
    suffix = f"budget-{len(list(fast_root.iterdir()))}"
    case = _build_case(fast_root, bundle, analysis, suffix=suffix)
    envelope, spec, handle = _prerequisites(
        fast_root, case, bundle, analysis
    )
    attempt = _attempt_directory(fast_root, case)
    with pytest.raises(
        admission_v1.ConstructionK7H1FailedPrefixCleanupBudgetAdmissionV1Error
    ):
        _admit(case, bundle, analysis, envelope, spec, handle, budget)
    assert not attempt.exists()


def test_late_normal_prefix_rejects_without_creating_an_admission(
    fast_root, bundle, analysis
):
    case = _build_case(fast_root, bundle, analysis, suffix="late")
    envelope, spec, handle = _prerequisites(
        fast_root, case, bundle, analysis
    )
    with _lease(case, bundle) as lease:
        event = normal_v1.execute_next_h1_phase_aware_normal_site_v1(lease)
    assert event.outcome == "SUCCESS"
    with pytest.raises(
        admission_v1.ConstructionK7H1FailedPrefixCleanupBudgetAdmissionV1Error,
        match="late|stale",
    ):
        _admit(case, bundle, analysis, envelope, spec, handle)
    assert not _attempt_directory(fast_root, case).exists()
    assert receipts_v1.replay_h1_native_receipt_journal_v1(handle)[
        "record_count"
    ] == 0


def test_cross_attempt_receipt_or_envelope_rejects_before_admission_mutation(
    fast_root, bundle, analysis
):
    left = _build_case(fast_root, bundle, analysis, suffix="cross-left")
    right = _build_case(fast_root, bundle, analysis, suffix="cross-right")
    left_envelope, left_spec, left_handle = _prerequisites(
        fast_root, left, bundle, analysis
    )
    right_envelope, right_spec, right_handle = _prerequisites(
        fast_root, right, bundle, analysis
    )
    with pytest.raises(
        admission_v1.ConstructionK7H1FailedPrefixCleanupBudgetAdmissionV1Error
    ):
        _admit(right, bundle, analysis, right_envelope, left_spec, left_handle)
    assert not _attempt_directory(fast_root, right).exists()
    with pytest.raises(
        admission_v1.ConstructionK7H1FailedPrefixCleanupBudgetAdmissionV1Error
    ):
        _admit(right, bundle, analysis, left_envelope, right_spec, right_handle)
    assert not _attempt_directory(fast_root, right).exists()


def test_live_owner_tail_drift_rejects_before_admission_mutation(
    fast_root, bundle, analysis
):
    case = _build_case(fast_root, bundle, analysis, suffix="owner-tail-drift")
    envelope, spec, handle = _prerequisites(
        fast_root, case, bundle, analysis
    )
    reservation = owner_v4.reserve_h1_shared_cap_owner_v4_wal(
        case.owner,
        operation_id=hashlib.sha256(b"cleanup-admission-owner-drift").hexdigest(),
        site_key="cleanup-admission:owner-drift",
        path="io.read_bytes",
        reservation_upper=1,
    )
    with owner_v4.hold_h1_shared_cap_owner_v4_wal_side_effect(
        case.owner, reservation
    ):
        pass
    owner_v4.settle_h1_shared_cap_owner_v4_wal(
        case.owner,
        reservation,
        value_basis=owner_v3.H1SharedValueBasisV3.EXACT_NATIVE,
        native_observed_value=0,
        evidence_source_id=hashlib.sha256(
            b"cleanup-admission-owner-drift-evidence"
        ).hexdigest(),
    )
    with pytest.raises(
        admission_v1.ConstructionK7H1FailedPrefixCleanupBudgetAdmissionV1Error,
        match="Owner/gate cutoff",
    ):
        _admit(case, bundle, analysis, envelope, spec, handle)
    assert not _attempt_directory(fast_root, case).exists()
    assert not (
        fast_root
        / f"{admission_v1._SEAL_PREFIX}{case.phase.spec.payload['route_attempt_id']}"
    ).exists()


def test_inactive_normal_lease_rejects_before_admission_mutation(
    fast_root, bundle, analysis
):
    case = _build_case(fast_root, bundle, analysis, suffix="nested")
    envelope, spec, handle = _prerequisites(
        fast_root, case, bundle, analysis
    )
    with _lease(case, bundle) as lease:
        stale_lease = lease
    with pytest.raises(
        normal_v1.ConstructionK7H1PhaseAwareNormalPrefixV1Error,
        match="stale|crossed",
    ):
        admission_v1.admit_h1_failed_prefix_cleanup_budget_v1(
            stale_lease,
            envelope=envelope,
            cleanup_analysis=analysis,
            native_receipt_spec=spec,
            native_receipt_handle=handle,
            available_cleanup_budget=EXACT_BUDGET,
        )
    assert not _attempt_directory(fast_root, case).exists()


def test_ordinal_one_contender_cannot_cross_the_composite_lock_publication_window(
    fast_root, bundle, analysis, monkeypatch
):
    case = _build_case(fast_root, bundle, analysis, suffix="concurrent")
    envelope, spec, handle = _prerequisites(
        fast_root, case, bundle, analysis
    )
    publication_entered = threading.Event()
    allow_publication = threading.Event()
    contender_started = threading.Event()
    contender_done = threading.Event()
    ordering = []
    admission_results = []
    errors = []
    original_publish = admission_v1._reconcile_or_publish

    def blocked_publish(base, base_fd, admission):
        publication_entered.set()
        if not allow_publication.wait(timeout=10):
            raise AssertionError("test did not release cleanup admission publication")
        result = original_publish(base, base_fd, admission)
        ordering.append("ADMISSION_PUBLISHED")
        return result

    monkeypatch.setattr(admission_v1, "_reconcile_or_publish", blocked_publish)

    def run_admission():
        try:
            admission_results.append(
                _admit(case, bundle, analysis, envelope, spec, handle)
            )
        except BaseException as error:  # pragma: no cover - reported below
            errors.append(error)

    def run_ordinal_one():
        contender_started.set()
        try:
            with _lease(case, bundle) as lease:
                event = normal_v1.execute_next_h1_phase_aware_normal_site_v1(
                    lease
                )
            assert event.outcome == "SUCCESS"
            ordering.append("ORDINAL_ONE_COMPLETED")
        except BaseException as error:  # pragma: no cover - reported below
            errors.append(error)
        finally:
            contender_done.set()

    admission_thread = threading.Thread(
        target=run_admission, name="cleanup-admission"
    )
    admission_thread.start()
    assert publication_entered.wait(timeout=60), errors
    contender_thread = threading.Thread(
        target=run_ordinal_one, name="ordinal-one-contender"
    )
    contender_thread.start()
    assert contender_started.wait(timeout=10)
    assert contender_done.wait(timeout=0.25) is False
    allow_publication.set()
    admission_thread.join(timeout=60)
    contender_thread.join(timeout=60)
    assert not admission_thread.is_alive()
    assert not contender_thread.is_alive()
    assert errors == []
    assert len(admission_results) == 1
    assert ordering == ["ADMISSION_PUBLISHED", "ORDINAL_ONE_COMPLETED"]


def test_phase_base_substitution_cannot_redirect_admission_publication(
    fast_root, bundle, analysis, monkeypatch
):
    case = _build_case(fast_root, bundle, analysis, suffix="phase-base-swap")
    envelope, spec, handle = _prerequisites(
        fast_root, case, bundle, analysis
    )
    moved = fast_root.with_name(fast_root.name + "-original")
    original_publish = admission_v1._reconcile_or_publish
    swapped = False

    def swap_path_then_publish(base, base_fd, admission):
        nonlocal swapped
        fast_root.rename(moved)
        fast_root.mkdir(mode=0o700)
        swapped = True
        return original_publish(base, base_fd, admission)

    monkeypatch.setattr(
        admission_v1, "_reconcile_or_publish", swap_path_then_publish
    )
    try:
        with pytest.raises(
            admission_v1.ConstructionK7H1FailedPrefixCleanupBudgetAdmissionV1Error,
            match="phase-base pathname changed",
        ):
            _admit(case, bundle, analysis, envelope, spec, handle)
        assert swapped is True
        assert not _attempt_directory(moved, case).exists()
        assert not _attempt_directory(fast_root, case).exists()
        assert not (
            moved
            / f"{admission_v1._SEAL_PREFIX}{case.phase.spec.payload['route_attempt_id']}"
        ).exists()
        assert not (moved / admission_v1._ROOT_LOCK_FILE).exists()
    finally:
        if fast_root.exists():
            shutil.rmtree(fast_root)
        if moved.exists():
            moved.rename(fast_root)


def test_native_cursor_open_failure_releases_all_admission_descriptors(
    fast_root, bundle, analysis, monkeypatch
):
    case = _build_case(fast_root, bundle, analysis, suffix="cursor-open-failure")
    envelope, spec, handle = _prerequisites(
        fast_root, case, bundle, analysis
    )
    target = handle.attempt_directory / receipts_v1._CURSOR_FILE
    original_open = os.open

    def fail_exact_native_cursor(path, *args, **kwargs):
        if isinstance(path, (str, os.PathLike)) and Path(path) == target:
            raise OSError("injected native receipt cursor open failure")
        return original_open(path, *args, **kwargs)

    with _lease(case, bundle) as lease:
        normal_state = normal_v1._replay_journal_locked(
            lease.handle,
            lease._journal_root_fd,
            lease._journal_directory_fd,
            lease._journal_cursor_fd,
            repair=False,
        )
        normal_evidence = receipts_v1._normal_evidence_from_state(normal_state)
        before_native = len(os.listdir("/proc/self/fd"))
        monkeypatch.setattr(receipts_v1.os, "open", fail_exact_native_cursor)
        try:
            with pytest.raises(OSError, match="injected native receipt cursor"):
                receipts_v1._with_locked(
                    handle, normal_evidence=normal_evidence, repair=False
                )
            assert len(os.listdir("/proc/self/fd")) == before_native
        finally:
            monkeypatch.setattr(receipts_v1.os, "open", original_open)

        def fail_native_preflight(*args, **kwargs):
            raise OSError("injected native preflight failure")

        before_admission = len(os.listdir("/proc/self/fd"))
        monkeypatch.setattr(receipts_v1, "_with_locked", fail_native_preflight)
        with pytest.raises(OSError, match="injected native preflight"):
            admission_v1.admit_h1_failed_prefix_cleanup_budget_v1(
                lease,
                envelope=envelope,
                cleanup_analysis=analysis,
                native_receipt_spec=spec,
                native_receipt_handle=handle,
                available_cleanup_budget=EXACT_BUDGET,
            )
        assert len(os.listdir("/proc/self/fd")) == before_admission
    assert not _attempt_directory(fast_root, case).exists()


def test_nonreconcilable_native_cursor_is_rejected_without_admission_mutation(
    fast_root, bundle, analysis
):
    case = _build_case(fast_root, bundle, analysis, suffix="native-cursor-torn")
    envelope, spec, handle = _prerequisites(
        fast_root, case, bundle, analysis
    )
    cursor = handle.attempt_directory / receipts_v1._CURSOR_FILE
    complete = cursor.read_bytes()
    cursor.write_bytes(complete[:-1])
    torn = cursor.read_bytes()
    with pytest.raises(
        receipts_v1.ConstructionK7H1NativeReceiptJournalV1Error,
        match="immutable high-water cannot reconcile",
    ):
        _admit(case, bundle, analysis, envelope, spec, handle)
    assert cursor.read_bytes() == torn
    assert not _attempt_directory(fast_root, case).exists()


def test_repairable_normal_temp_is_rejected_read_only_inside_live_lease(
    fast_root, bundle, analysis
):
    case = _build_case(fast_root, bundle, analysis, suffix="normal-temp-readonly")
    envelope, spec, handle = _prerequisites(
        fast_root, case, bundle, analysis
    )
    with _lease(case, bundle) as lease:
        temp = (
            Path(case.normal.root_directory)
            / case.normal.route_attempt_id
            / f"{normal_v1._TEMP_PREFIX}admission-readonly-probe"
        )
        temp.write_bytes(b"unchanged-repairable-temp")
        temp.chmod(0o600)
        before = (temp.read_bytes(), temp.stat().st_ino, temp.stat().st_mode)
        with pytest.raises(
            normal_v1.H1NormalPrefixProtocolFailureV1,
            match="read-only replay refuses",
        ):
            admission_v1.admit_h1_failed_prefix_cleanup_budget_v1(
                lease,
                envelope=envelope,
                cleanup_analysis=analysis,
                native_receipt_spec=spec,
                native_receipt_handle=handle,
                available_cleanup_budget=EXACT_BUDGET,
            )
        assert (temp.read_bytes(), temp.stat().st_ino, temp.stat().st_mode) == before
    assert not _attempt_directory(fast_root, case).exists()


def test_preexisting_hardlinked_root_lock_is_rejected_without_mutation(
    fast_root, bundle, analysis
):
    case = _build_case(fast_root, bundle, analysis, suffix="hardlinked-root-lock")
    envelope, spec, handle = _prerequisites(
        fast_root, case, bundle, analysis
    )
    foreign = fast_root / "foreign-root-lock-target"
    foreign.write_bytes(b"do-not-mutate")
    foreign.chmod(0o644)
    lock = fast_root / admission_v1._ROOT_LOCK_FILE
    os.link(foreign, lock)
    before = foreign.stat()
    before_bytes = foreign.read_bytes()
    with pytest.raises(
        admission_v1.ConstructionK7H1FailedPrefixCleanupBudgetAdmissionV1Error,
        match="root coordination lock changed",
    ):
        _admit(case, bundle, analysis, envelope, spec, handle)
    after = foreign.stat()
    assert foreign.read_bytes() == before_bytes
    assert stat.S_IMODE(after.st_mode) == stat.S_IMODE(before.st_mode) == 0o644
    assert after.st_nlink == before.st_nlink == 2
    assert not _attempt_directory(fast_root, case).exists()


def test_lone_primary_or_seal_with_foreign_hardlink_is_rejected_before_repair(
    fast_root, bundle, analysis
):
    case = _build_case(fast_root, bundle, analysis, suffix="foreign-admission-link")
    envelope, spec, handle = _prerequisites(
        fast_root, case, bundle, analysis
    )
    admitted = _admit(case, bundle, analysis, envelope, spec, handle)
    primary = _attempt_directory(fast_root, case) / admission_v1._ADMISSION_FILE
    seal = (
        fast_root
        / f"{admission_v1._SEAL_PREFIX}{case.phase.spec.payload['route_attempt_id']}"
    )

    primary.unlink()
    foreign_seal = fast_root / "foreign-seal-hardlink"
    os.link(seal, foreign_seal)
    before_seal = seal.stat()
    with pytest.raises(
        admission_v1.ConstructionK7H1FailedPrefixCleanupBudgetAdmissionV1Error,
        match="lone cleanup admission seal has a foreign hard link",
    ):
        _admit(case, bundle, analysis, envelope, spec, handle)
    after_seal = seal.stat()
    assert not primary.exists()
    assert seal.read_bytes() == foreign_seal.read_bytes() == admitted.canonical_bytes
    assert (after_seal.st_ino, after_seal.st_nlink, after_seal.st_mode) == (
        before_seal.st_ino,
        before_seal.st_nlink,
        before_seal.st_mode,
    )

    foreign_seal.unlink()
    recovered = _admit(case, bundle, analysis, envelope, spec, handle)
    assert recovered.admission_id == admitted.admission_id
    seal.unlink()
    foreign_primary = fast_root / "foreign-primary-hardlink"
    os.link(primary, foreign_primary)
    before_primary = primary.stat()
    with pytest.raises(
        admission_v1.ConstructionK7H1FailedPrefixCleanupBudgetAdmissionV1Error,
        match="lone cleanup admission primary has a foreign hard link",
    ):
        _admit(case, bundle, analysis, envelope, spec, handle)
    after_primary = primary.stat()
    assert not seal.exists()
    assert primary.read_bytes() == foreign_primary.read_bytes() == admitted.canonical_bytes
    assert (after_primary.st_ino, after_primary.st_nlink, after_primary.st_mode) == (
        before_primary.st_ino,
        before_primary.st_nlink,
        before_primary.st_mode,
    )


def test_temp_and_primary_before_seal_crash_frontiers_converge_exactly(
    fast_root, bundle, analysis, monkeypatch
):
    temp_case = _build_case(fast_root, bundle, analysis, suffix="stale-temp")
    temp_envelope, temp_spec, temp_handle = _prerequisites(
        fast_root, temp_case, bundle, analysis
    )
    temp_attempt = _attempt_directory(fast_root, temp_case)
    temp_attempt.parent.mkdir(mode=0o700)
    temp_attempt.mkdir(mode=0o700)
    stale_temp = temp_attempt / f"{phase_v1._TEMP_PREFIX}crashed-writer"
    stale_temp.write_bytes(b"partial")
    admitted = _admit(
        temp_case,
        bundle,
        analysis,
        temp_envelope,
        temp_spec,
        temp_handle,
    )
    assert admitted.admission_id
    assert not stale_temp.exists()

    seal_case = _build_case(fast_root, bundle, analysis, suffix="primary-no-seal")
    seal_envelope, seal_spec, seal_handle = _prerequisites(
        fast_root, seal_case, bundle, analysis
    )
    original_link = os.link
    original_publish_locked = admission_v1._reconcile_or_publish_locked
    failed_once = False

    def fail_first_admission_seal(source, destination, *args, **kwargs):
        nonlocal failed_once
        if (
            not failed_once
            and isinstance(destination, str)
            and destination.startswith(admission_v1._SEAL_PREFIX)
        ):
            failed_once = True
            raise OSError("injected crash before admission seal")
        return original_link(source, destination, *args, **kwargs)

    def crash_inside_publication(base_fd, admission):
        monkeypatch.setattr(
            admission_v1.os, "link", fail_first_admission_seal
        )
        try:
            return original_publish_locked(base_fd, admission)
        finally:
            monkeypatch.setattr(admission_v1.os, "link", original_link)

    monkeypatch.setattr(
        admission_v1,
        "_reconcile_or_publish_locked",
        crash_inside_publication,
    )
    with pytest.raises(OSError, match="injected crash before admission seal"):
        _admit(
            seal_case,
            bundle,
            analysis,
            seal_envelope,
            seal_spec,
            seal_handle,
        )
    primary = _attempt_directory(fast_root, seal_case) / admission_v1._ADMISSION_FILE
    seal = (
        fast_root
        / f"{admission_v1._SEAL_PREFIX}{seal_case.phase.spec.payload['route_attempt_id']}"
    )
    assert primary.exists()
    assert not seal.exists()
    monkeypatch.setattr(
        admission_v1,
        "_reconcile_or_publish_locked",
        original_publish_locked,
    )
    recovered = _admit(
        seal_case,
        bundle,
        analysis,
        seal_envelope,
        seal_spec,
        seal_handle,
    )
    assert recovered.canonical_bytes == primary.read_bytes() == seal.read_bytes()
    assert primary.stat().st_ino == seal.stat().st_ino


def test_registry_domains_are_disjoint_and_admission_objects_are_not_caller_mintable():
    from acfqp import construction_k7_h1_domain_registry_extension_v4 as v4
    from acfqp import construction_k7_h1_domain_registry_extension_v5 as v5
    from acfqp import construction_k7_h1_domain_registry_extension_v6 as v6
    from acfqp import construction_k7_h1_domain_registry_extension_v7 as v7

    assert v7.K7_H1_DOMAIN_TAG_EXTENSION_V7.isdisjoint(
        v4.K7_H1_DOMAIN_TAG_EXTENSION_V4
        | v5.K7_H1_DOMAIN_TAG_EXTENSION_V5
        | v6.K7_H1_DOMAIN_TAG_EXTENSION_V6
    )
    with pytest.raises(
        admission_v1.ConstructionK7H1FailedPrefixCleanupBudgetAdmissionV1Error
    ):
        admission_v1.H1FailedPrefixCleanupBudgetAdmissionV1(
            object(), b"{}"
        )
