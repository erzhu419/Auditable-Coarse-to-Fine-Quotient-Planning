from __future__ import annotations

import ast
from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import pickle
import shutil
import tempfile
import threading
from types import FunctionType, MappingProxyType

import pytest

from acfqp import construction_k7_h1_anchored_lifecycle_dispatch_v1 as dispatch_v1
from acfqp import construction_k7_h1_attempt_execution_phase_owner_v1 as phase_v1
from acfqp import construction_k7_h1_attempt_rejection_gate_v1 as rejection_v1
from acfqp import construction_k7_h1_lifecycle_complete_cleanup_v1 as cleanup_v1
from acfqp import construction_k7_h1_lifecycle_output_leaf_join_v1 as output_join_v1
from acfqp import construction_k7_h1_phase_aware_normal_prefix_v1 as normal_v1
from acfqp import construction_k7_h1_shared_cap_owner_v3 as owner_v3
from acfqp import construction_k7_h1_shared_cap_owner_v4_wal as owner_v4


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
EXPECTED_ANCHOR_ID = (
    "4a4b0d1888f0ac18123e4163e1a26b0583a64946d2eb219e02d4b77dc0a3e327"
)


def _id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


@pytest.fixture(scope="module")
def bundle():
    return dispatch_v1.freeze_h1_anchored_lifecycle_dispatch_bundle_v1(
        REPOSITORY_ROOT,
        expected_anchor_id=EXPECTED_ANCHOR_ID,
    )


@pytest.fixture(scope="module")
def analysis(bundle):
    output_join = output_join_v1.build_h1_lifecycle_output_leaf_join_v1(bundle)
    return cleanup_v1.derive_h1_lifecycle_complete_branch_analysis_v1(
        bundle, output_join
    )


@pytest.fixture
def fast_root():
    base = "/dev/shm" if Path("/dev/shm").is_dir() else "/tmp"
    path = Path(tempfile.mkdtemp(prefix="acfqp-h1-normal-prefix-", dir=base))
    try:
        yield path
    finally:
        shutil.rmtree(path)


@dataclass(frozen=True)
class _Case:
    gate: rejection_v1.H1AttemptRejectionGateHandleV1
    owner: owner_v4.H1SharedCapOwnerV4WalHandle
    dispatch_profile: dispatch_v1.H1LifecycleDispatchProfileV1
    phase: phase_v1.H1AttemptExecutionPhaseOwnerV1Handle
    normal: normal_v1.H1NormalPrefixHandleV1


def _build_case(root: Path, bundle, analysis, *, suffix: str, caps=None) -> _Case:
    hard_caps = {path: 100_000 for path in owner_v3.SHARED_RESOURCE_PATHS}
    if caps:
        hard_caps.update(caps)
    profile = owner_v3.freeze_h1_shared_cap_profile_core_v3(
        logical_occurrence_id=_id(f"occurrence-{suffix}"),
        route_attempt_id=_id(f"attempt-{suffix}"),
        decision_point_id=_id(f"decision-{suffix}"),
        transaction_id=_id(f"transaction-{suffix}"),
        caller_pinned_lifecycle_provenance_id=bundle.program.provenance_id,
        lifecycle_program_snapshot_id=bundle.program.snapshot_id,
        lifecycle_program_id=bundle.program.program_id,
        lifecycle_branch_analysis_id=bundle.program.branch_analysis_id,
        hard_caps=hard_caps,
    )
    source = owner_v3.freeze_h1_shared_cap_owner_v3_source_manifest(
        caller_pinned_lifecycle_provenance_id=(
            profile.caller_pinned_lifecycle_provenance_id
        ),
        lifecycle_program_snapshot_id=profile.lifecycle_program_snapshot_id,
        lifecycle_program_id=profile.lifecycle_program_id,
        lifecycle_branch_analysis_id=profile.lifecycle_branch_analysis_id,
    )
    gate_spec = rejection_v1.freeze_h1_attempt_rejection_gate_spec_v1(
        base_directory=root,
        logical_occurrence_id=profile.logical_occurrence_id,
        route_attempt_id=profile.route_attempt_id,
        caller_pinned_lifecycle_provenance_id=(
            profile.caller_pinned_lifecycle_provenance_id
        ),
    )
    gate = rejection_v1.initialize_h1_attempt_rejection_gate_v1(root, gate_spec)
    historical_owner = owner_v3.initialize_h1_shared_cap_owner_v3(
        root,
        profile=profile,
        source_manifest=source,
        rejection_gate=gate,
    )
    operands = {
        row["site_key"]: (
            1
            if row["handler_mode"]
            == dispatch_v1.H1LifecycleHandlerModeV1.IMMEDIATE_UNIT.value
            else 10
        )
        for row in bundle.registry.handlers
        if row["reservation_edge"] is True
    }
    dispatch_profile = dispatch_v1.bind_h1_lifecycle_dispatch_profile_v1(
        bundle,
        historical_owner,
        site_reservation_uppers=operands,
    )
    upgraded = owner_v3._enable_h1_shared_cap_owner_v4_pending_payload_wal(
        historical_owner
    )
    owner = owner_v4.open_h1_shared_cap_owner_v4_wal(
        upgraded.owner_directory,
        expected_runtime_id=upgraded.runtime_id,
        gate_directory=upgraded.gate_directory,
    )
    phase_spec = phase_v1.freeze_h1_attempt_execution_phase_spec_v1(
        root,
        logical_occurrence_id=profile.logical_occurrence_id,
        route_attempt_id=profile.route_attempt_id,
        caller_pinned_lifecycle_provenance_id=(
            profile.caller_pinned_lifecycle_provenance_id
        ),
        rejection_gate=gate,
        anchored_program_id=bundle.program.anchored_program_id,
        handler_registry_id=bundle.registry.registry_id,
        cleanup_analysis=analysis,
    )
    phase = phase_v1.initialize_h1_attempt_execution_phase_owner_v1(
        phase_spec,
        rejection_gate=gate,
    )
    normal_spec = normal_v1.freeze_h1_normal_prefix_spec_v1(
        root,
        phase_handle=phase,
        rejection_gate=gate,
        owner=owner,
        bundle=bundle,
        dispatch_profile=dispatch_profile,
    )
    normal = normal_v1.initialize_h1_normal_prefix_journal_v1(normal_spec)
    return _Case(gate, owner, dispatch_profile, phase, normal)


def _callback_for(row):
    if row["ordinal"] in {1, 5}:
        return None
    if row["operation"] in {
        "COMMON_HASH",
        "COMMON_INTEGRITY",
        "COMMON_PROTOCOL",
        "LAUNCH_CHILD",
    }:
        return lambda: None
    return lambda: 1


def _execute(case: _Case, bundle, *, callback=None, crash_point=None):
    with normal_v1.hold_h1_phase_aware_normal_prefix_lease_v1(
        case.normal,
        phase_handle=case.phase,
        rejection_gate=case.gate,
        owner=case.owner,
        bundle=bundle,
        dispatch_profile=case.dispatch_profile,
    ) as lease:
        kwargs = {"callback": callback}
        if crash_point is not None:
            kwargs["crash_point"] = crash_point
        return normal_v1.execute_next_h1_phase_aware_normal_site_v1(
            lease, **kwargs
        )


def _assert_pretransition_phase(case: _Case):
    replay = phase_v1.replay_h1_attempt_execution_phase_owner_v1(
        case.phase, rejection_gate=case.gate
    )
    assert replay["state"] == "NORMAL"
    assert replay["h1_attempt_cleanup_transition_id"] == {
        "kind": "NOT_APPLICABLE",
        "reason": "NO_CLEANUP_TRANSITION",
    }
    assert replay["cleanup_only_allowed_by_phase"] is False


def test_all_40_normal_sites_cover_nine_paths_and_stop_before_cleanup(
    fast_root, bundle, analysis
):
    case = _build_case(fast_root, bundle, analysis, suffix="happy")
    events = []
    for row in bundle.program.transitions[:40]:
        event = _execute(case, bundle, callback=_callback_for(row))
        assert type(event) is normal_v1.H1NormalSiteEventCommitV1
        assert event.ordinal == row["ordinal"]
        assert event.outcome == "SUCCESS"
        events.append(event.document)
    snapshot = normal_v1.replay_h1_normal_prefix_journal_v1(case.normal)
    assert snapshot.status is (
        normal_v1.H1NormalPrefixStatusV1.NORMAL_PREFIX_COMPLETE_AWAITING_POST_CHILD_CLEANUP
    )
    assert snapshot.document["next_ordinal"] == 41
    assert snapshot.document["attempt_closure_issued"] is False
    assert {row["resource_path"] for row in events} == set(
        owner_v3.SHARED_RESOURCE_PATHS
    )
    assert [len(row["owner_appended_records"]) for row in events] == [
        1 if ordinal in {1, 5} else 7 for ordinal in range(1, 41)
    ]
    replay = owner_v4.replay_h1_shared_cap_owner_v4_wal(case.owner)
    assert replay["journal_sequence"] == 275
    _assert_pretransition_phase(case)
    with normal_v1.hold_h1_phase_aware_normal_prefix_lease_v1(
        case.normal,
        phase_handle=case.phase,
        rejection_gate=case.gate,
        owner=case.owner,
        bundle=bundle,
        dispatch_profile=case.dispatch_profile,
    ) as lease:
        result = normal_v1.execute_next_h1_phase_aware_normal_site_v1(lease)
        assert type(result) is normal_v1.H1NormalPrefixSnapshotV1


def test_intent_and_reservation_recovery_are_safe_prestart(
    fast_root, bundle, analysis
):
    case = _build_case(fast_root, bundle, analysis, suffix="prestart")
    with pytest.raises(normal_v1.H1NormalPrefixInjectedCrashV1):
        _execute(
            case,
            bundle,
            callback=None,
            crash_point=normal_v1.H1NormalPrefixCrashPointV1.AFTER_INTENT_FSYNC,
        )
    recovered = _execute(case, bundle, callback=None)
    assert recovered.outcome == "SUCCESS"
    with pytest.raises(normal_v1.H1NormalPrefixInjectedCrashV1):
        _execute(
            case,
            bundle,
            callback=lambda: None,
            crash_point=normal_v1.H1NormalPrefixCrashPointV1.AFTER_RESERVATION_FSYNC,
        )
    with normal_v1.hold_h1_phase_aware_normal_prefix_lease_v1(
        case.normal,
        phase_handle=case.phase,
        rejection_gate=case.gate,
        owner=case.owner,
        bundle=bundle,
        dispatch_profile=case.dispatch_profile,
    ) as lease:
        snapshot = normal_v1.recover_pending_h1_phase_aware_normal_site_v1(lease)
    assert snapshot.status is (
        normal_v1.H1NormalPrefixStatusV1.CALLBACK_REQUIRED_TO_RESUME_SAFE_PRESTART
    )
    calls = []
    event = _execute(case, bundle, callback=lambda: calls.append(1))
    assert event.outcome == "SUCCESS"
    assert calls == [1]


def test_native_cell_without_callback_result_never_reexecutes_callback(
    fast_root, bundle, analysis
):
    case = _build_case(fast_root, bundle, analysis, suffix="native-cell")
    _execute(case, bundle, callback=None)
    calls = []
    with pytest.raises(normal_v1.H1NormalPrefixInjectedCrashV1):
        _execute(
            case,
            bundle,
            callback=lambda: calls.append("first"),
            crash_point=normal_v1.H1NormalPrefixCrashPointV1.AFTER_NATIVE_CELL_FSYNC,
        )
    assert calls == []
    event = _execute(case, bundle, callback=lambda: calls.append("forbidden"))
    assert calls == []
    assert event.outcome == "CALLBACK_FAILED_AFTER_ADMISSION"
    assert event.document["callback_invocation_may_have_occurred"] is True
    assert event.document["value_basis"] == "CONSERVATIVE_RESERVATION_UPPER"
    _assert_pretransition_phase(case)


def test_durable_callback_result_completes_without_callback_replay(
    fast_root, bundle, analysis
):
    case = _build_case(fast_root, bundle, analysis, suffix="callback-result")
    _execute(case, bundle, callback=None)
    calls = []
    with pytest.raises(normal_v1.H1NormalPrefixInjectedCrashV1):
        _execute(
            case,
            bundle,
            callback=lambda: calls.append(1),
            crash_point=normal_v1.H1NormalPrefixCrashPointV1.AFTER_CALLBACK_RESULT_FSYNC,
        )
    assert calls == [1]
    with normal_v1.hold_h1_phase_aware_normal_prefix_lease_v1(
        case.normal,
        phase_handle=case.phase,
        rejection_gate=case.gate,
        owner=case.owner,
        bundle=bundle,
        dispatch_profile=case.dispatch_profile,
    ) as lease:
        event = normal_v1.recover_pending_h1_phase_aware_normal_site_v1(lease)
    assert event.outcome == "SUCCESS"
    assert calls == [1]


def test_cap_rejection_is_recovered_inside_retained_gate_and_skips_callback(
    fast_root, bundle, analysis
):
    case = _build_case(
        fast_root,
        bundle,
        analysis,
        suffix="cap",
        caps={"io.staged_bytes": 10},
    )
    for row in bundle.program.transitions[:7]:
        _execute(case, bundle, callback=_callback_for(row))
    calls = []
    event = _execute(case, bundle, callback=lambda: calls.append(1) or 1)
    assert event.outcome == "CAP_REJECTED_BEFORE_SIDE_EFFECT"
    assert event.document["callback_invocation_count"] == 0
    assert calls == []
    gate = rejection_v1.h1_attempt_rejection_gate_snapshot_v1(case.gate)
    assert gate["state"] == "ACKNOWLEDGED"
    snapshot = normal_v1.replay_h1_normal_prefix_journal_v1(case.normal)
    assert snapshot.status is (
        normal_v1.H1NormalPrefixStatusV1.FAILURE_POISONED_AWAITING_PHASE_TRANSITION
    )
    _assert_pretransition_phase(case)


def test_handles_and_lease_are_not_pickleable(fast_root, bundle, analysis):
    case = _build_case(fast_root, bundle, analysis, suffix="pickle")
    with pytest.raises(normal_v1.ConstructionK7H1PhaseAwareNormalPrefixV1Error):
        pickle.dumps(case.normal)
    with normal_v1.hold_h1_phase_aware_normal_prefix_lease_v1(
        case.normal,
        phase_handle=case.phase,
        rejection_gate=case.gate,
        owner=case.owner,
        bundle=bundle,
        dispatch_profile=case.dispatch_profile,
    ) as lease:
        with pytest.raises(normal_v1.ConstructionK7H1PhaseAwareNormalPrefixV1Error):
            pickle.dumps(lease)


def test_artifact_documents_are_defensive_copies(fast_root, bundle, analysis):
    case = _build_case(fast_root, bundle, analysis, suffix="immutable-artifact")
    event = _execute(case, bundle, callback=None)
    event_bytes = event.canonical_bytes
    event_copy = event.document
    event_copy["outcome"] = "MUTATED"
    event_copy["owner_appended_records"].append({"attack": True})
    assert event.outcome == "SUCCESS"
    assert event.canonical_bytes == event_bytes

    snapshot = normal_v1.replay_h1_normal_prefix_journal_v1(case.normal)
    snapshot_bytes = snapshot.canonical_bytes
    snapshot_copy = snapshot.document
    snapshot_copy["status"] = "MUTATED"
    assert snapshot.status is normal_v1.H1NormalPrefixStatusV1.READY
    assert snapshot.canonical_bytes == snapshot_bytes


def test_dependency_registry_is_ast_complete_and_detects_monkeypatch(monkeypatch):
    tree = ast.parse(Path(normal_v1.__file__).read_text(encoding="utf-8"))
    used = {name: set() for name in normal_v1._DEPENDENCY_SYMBOL_NAMES}
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id in used
        ):
            used[node.value.id].add(node.attr)
    assert {
        name: frozenset(symbols) for name, symbols in used.items()
    } == dict(normal_v1._DEPENDENCY_SYMBOL_NAMES)

    baseline = normal_v1.inspect_h1_normal_prefix_semantic_closure_candidate_v1()
    monkeypatch.setattr(dispatch_v1, "_resource_path", lambda _row: "io.output_bytes")
    with pytest.raises(normal_v1.ConstructionK7H1PhaseAwareNormalPrefixV1Error):
        normal_v1.inspect_h1_normal_prefix_semantic_closure_candidate_v1()
    monkeypatch.undo()
    assert (
        normal_v1.inspect_h1_normal_prefix_semantic_closure_candidate_v1()
        == baseline
    )


def test_dependency_registry_detects_in_place_constant_drift():
    original = owner_v3._EXTRA_FIELDS
    key = next(iter(original))
    previous = original[key]
    try:
        original[key] = frozenset({*previous, "injected_field"})
        with pytest.raises(normal_v1.ConstructionK7H1PhaseAwareNormalPrefixV1Error):
            normal_v1.inspect_h1_normal_prefix_semantic_closure_candidate_v1()
    finally:
        original[key] = previous
    normal_v1.inspect_h1_normal_prefix_semantic_closure_candidate_v1()


def test_transitive_dependency_and_class_behavior_drift_fail_closed(monkeypatch):
    baseline = normal_v1.inspect_h1_normal_prefix_semantic_closure_candidate_v1()
    monkeypatch.setattr(dispatch_v1, "_is_typed_null", lambda _value: True)
    with pytest.raises(normal_v1.ConstructionK7H1PhaseAwareNormalPrefixV1Error):
        normal_v1.inspect_h1_normal_prefix_semantic_closure_candidate_v1()
    monkeypatch.undo()

    monkeypatch.setattr(
        rejection_v1.H1AttemptRejectionAckV1,
        "__post_init__",
        lambda self, _issuer: None,
    )
    with pytest.raises(normal_v1.ConstructionK7H1PhaseAwareNormalPrefixV1Error):
        normal_v1.inspect_h1_normal_prefix_semantic_closure_candidate_v1()
    monkeypatch.undo()
    assert normal_v1.inspect_h1_normal_prefix_semantic_closure_candidate_v1() == baseline


def test_transitive_enum_dataclass_and_exception_table_drift_fail_closed():
    enum_type = owner_v3.H1SharedValueBasisV3
    enum_map = enum_type._value2member_map_
    enum_map["ATTACK_VALUE"] = next(iter(enum_type))
    try:
        with pytest.raises(normal_v1.ConstructionK7H1PhaseAwareNormalPrefixV1Error):
            normal_v1.inspect_h1_normal_prefix_semantic_closure_candidate_v1()
    finally:
        enum_map.pop("ATTACK_VALUE")

    fields = owner_v3.H1SharedCapOwnerV3Handle.__dataclass_fields__
    original_fields = dict(fields)
    fields.pop(next(iter(fields)))
    try:
        with pytest.raises(normal_v1.ConstructionK7H1PhaseAwareNormalPrefixV1Error):
            normal_v1.inspect_h1_normal_prefix_semantic_closure_candidate_v1()
    finally:
        fields.clear()
        fields.update(original_fields)

    function = rejection_v1._read_file
    original_code = function.__code__
    replacement = (
        original_code.replace(co_exceptiontable=b"")
        if hasattr(original_code, "co_exceptiontable")
        else original_code.replace(
            co_consts=original_code.co_consts + ("dependency-code-drift",)
        )
    )
    function.__code__ = replacement
    try:
        with pytest.raises(normal_v1.ConstructionK7H1PhaseAwareNormalPrefixV1Error):
            normal_v1.inspect_h1_normal_prefix_semantic_closure_candidate_v1()
    finally:
        function.__code__ = original_code
    normal_v1.inspect_h1_normal_prefix_semantic_closure_candidate_v1()


def test_high_water_rejects_joint_record_seal_and_cursor_rollback(
    fast_root, bundle, analysis
):
    case = _build_case(fast_root, bundle, analysis, suffix="joint-rollback")
    _execute(case, bundle, callback=None)
    journal = Path(case.normal.journal_directory)
    root = Path(case.normal.root_directory)
    for path in journal.iterdir():
        if normal_v1._RECORD_PATTERN.fullmatch(path.name):
            path.unlink()
    seal_prefix = f"record-seal-{case.normal.route_attempt_id}-"
    for path in root.iterdir():
        if path.name.startswith(seal_prefix):
            path.unlink()
    cursor = journal / normal_v1._CURSOR_FILE
    genesis = cursor.read_bytes().splitlines(keepends=True)[0]
    with cursor.open("r+b") as stream:
        stream.truncate(0)
        stream.write(genesis)
        stream.flush()
        os.fsync(stream.fileno())
    with pytest.raises(normal_v1.H1NormalPrefixProtocolFailureV1):
        normal_v1.replay_h1_normal_prefix_journal_v1(case.normal)


def _install_previous_high_water_link(case: _Case):
    root = Path(case.normal.root_directory)
    cursor = Path(case.normal.journal_directory) / normal_v1._CURSOR_FILE
    lines = cursor.read_bytes().splitlines(keepends=True)
    assert len(lines) >= 2
    previous = normal_v1.loads_canonical_json(lines[-2].rstrip(b"\n"))
    current = normal_v1.loads_canonical_json(lines[-1].rstrip(b"\n"))
    previous_state = root / normal_v1._high_water_state_name(
        case.normal.route_attempt_id,
        previous["sequence"],
        previous["h1_normal_prefix_cursor_record_id"],
    )
    token = root / normal_v1._high_water_token_name(case.normal.route_attempt_id)
    os.link(token, previous_state)
    root_fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(root_fd)
    finally:
        os.close(root_fd)
    return cursor, lines, previous, current, previous_state


def test_high_water_recovers_successor_link_before_cursor(
    fast_root, bundle, analysis
):
    case = _build_case(fast_root, bundle, analysis, suffix="pre-cursor-window")
    event = _execute(case, bundle, callback=None)
    cursor, lines, _previous, current, previous_state = (
        _install_previous_high_water_link(case)
    )
    with cursor.open("r+b") as stream:
        stream.truncate(0)
        stream.write(b"".join(lines[:-1]))
        stream.flush()
        os.fsync(stream.fileno())

    snapshot = normal_v1.replay_h1_normal_prefix_journal_v1(case.normal)
    assert snapshot.document["last_event_id"] == event.event_id
    assert cursor.read_bytes() == b"".join(lines)
    assert not previous_state.exists()
    assert (
        Path(case.normal.root_directory)
        / normal_v1._high_water_state_name(
            case.normal.route_attempt_id,
            current["sequence"],
            current["h1_normal_prefix_cursor_record_id"],
        )
    ).exists()


def test_high_water_recovers_strict_torn_cursor_suffix(
    fast_root, bundle, analysis
):
    case = _build_case(fast_root, bundle, analysis, suffix="torn-cursor-window")
    event = _execute(case, bundle, callback=None)
    cursor, lines, _previous, _current, previous_state = (
        _install_previous_high_water_link(case)
    )
    torn = lines[-1][: max(1, len(lines[-1]) // 2)]
    assert not torn.endswith(b"\n")
    with cursor.open("r+b") as stream:
        stream.truncate(0)
        stream.write(b"".join(lines[:-1]) + torn)
        stream.flush()
        os.fsync(stream.fileno())

    snapshot = normal_v1.replay_h1_normal_prefix_journal_v1(case.normal)
    assert snapshot.document["last_event_id"] == event.event_id
    assert cursor.read_bytes() == b"".join(lines)
    assert not previous_state.exists()


def test_high_water_finishes_postcursor_predecessor_unlink(
    fast_root, bundle, analysis
):
    case = _build_case(fast_root, bundle, analysis, suffix="post-cursor-window")
    event = _execute(case, bundle, callback=None)
    cursor, lines, _previous, _current, previous_state = (
        _install_previous_high_water_link(case)
    )

    snapshot = normal_v1.replay_h1_normal_prefix_journal_v1(case.normal)
    assert snapshot.document["last_event_id"] == event.event_id
    assert cursor.read_bytes() == b"".join(lines)
    assert not previous_state.exists()


def test_high_water_rejects_nonprefix_torn_cursor_tail(
    fast_root, bundle, analysis
):
    case = _build_case(fast_root, bundle, analysis, suffix="bad-torn-cursor")
    _execute(case, bundle, callback=None)
    cursor = Path(case.normal.journal_directory) / normal_v1._CURSOR_FILE
    with cursor.open("ab") as stream:
        stream.write(b"not-a-prefix-of-the-next-cursor-row")
        stream.flush()
        os.fsync(stream.fileno())
    with pytest.raises(normal_v1.H1NormalPrefixProtocolFailureV1):
        normal_v1.replay_h1_normal_prefix_journal_v1(case.normal)


def test_high_water_rejects_foreign_link_and_sequence_gap(
    fast_root, bundle, analysis
):
    foreign_case = _build_case(
        fast_root, bundle, analysis, suffix="foreign-high-water-link"
    )
    foreign_root = Path(foreign_case.normal.root_directory)
    foreign_token = foreign_root / normal_v1._high_water_token_name(
        foreign_case.normal.route_attempt_id
    )
    foreign_link = foreign_root / "unregistered-token-hardlink"
    os.link(foreign_token, foreign_link)
    with pytest.raises(normal_v1.H1NormalPrefixProtocolFailureV1):
        normal_v1.replay_h1_normal_prefix_journal_v1(foreign_case.normal)
    foreign_link.unlink()

    gap_case = _build_case(fast_root, bundle, analysis, suffix="high-water-gap")
    gap_root = Path(gap_case.normal.root_directory)
    gap_token = gap_root / normal_v1._high_water_token_name(
        gap_case.normal.route_attempt_id
    )
    gap_state = gap_root / normal_v1._high_water_state_name(
        gap_case.normal.route_attempt_id, 2, _id("nonlocal-high-water")
    )
    os.link(gap_token, gap_state)
    with pytest.raises(normal_v1.H1NormalPrefixProtocolFailureV1):
        normal_v1.replay_h1_normal_prefix_journal_v1(gap_case.normal)


def test_high_water_bootstrap_recovers_only_before_allocation(
    fast_root, bundle, analysis
):
    case = _build_case(fast_root, bundle, analysis, suffix="partial-bootstrap")
    root = Path(case.normal.root_directory)
    allocation = root / normal_v1._allocation_name(case.normal.route_attempt_id)
    state_prefix = f"{normal_v1._HIGH_WATER_STATE_PREFIX}{case.normal.route_attempt_id}-"
    allocation.unlink()
    states = [path for path in root.iterdir() if path.name.startswith(state_prefix)]
    assert len(states) == 1
    states[0].unlink()

    recovered = normal_v1.initialize_h1_normal_prefix_journal_v1(case.normal.spec)
    assert recovered.allocation_id == case.normal.allocation_id
    assert normal_v1.replay_h1_normal_prefix_journal_v1(recovered).status is (
        normal_v1.H1NormalPrefixStatusV1.READY
    )

    states = [path for path in root.iterdir() if path.name.startswith(state_prefix)]
    assert len(states) == 1
    states[0].unlink()
    with pytest.raises(normal_v1.ConstructionK7H1PhaseAwareNormalPrefixV1Error):
        normal_v1.initialize_h1_normal_prefix_journal_v1(case.normal.spec)


def test_high_water_bootstrap_accepts_existing_exact_genesis_state(
    fast_root, bundle, analysis
):
    case = _build_case(fast_root, bundle, analysis, suffix="existing-genesis-state")
    root = Path(case.normal.root_directory)
    allocation = root / normal_v1._allocation_name(case.normal.route_attempt_id)
    state_prefix = f"{normal_v1._HIGH_WATER_STATE_PREFIX}{case.normal.route_attempt_id}-"
    states = [path for path in root.iterdir() if path.name.startswith(state_prefix)]
    assert len(states) == 1
    allocation.unlink()

    recovered = normal_v1.initialize_h1_normal_prefix_journal_v1(case.normal.spec)
    assert recovered.allocation_id == case.normal.allocation_id
    assert states[0].exists()


def test_missing_allocation_after_progress_is_not_recreated(
    fast_root, bundle, analysis
):
    case = _build_case(fast_root, bundle, analysis, suffix="allocation-progress")
    _execute(case, bundle, callback=None)
    allocation = (
        Path(case.normal.root_directory)
        / normal_v1._allocation_name(case.normal.route_attempt_id)
    )
    allocation.unlink()
    with pytest.raises(normal_v1.ConstructionK7H1PhaseAwareNormalPrefixV1Error):
        normal_v1.initialize_h1_normal_prefix_journal_v1(case.normal.spec)


def test_dangling_intent_rejects_out_of_band_owner_append(
    fast_root, bundle, analysis
):
    case = _build_case(fast_root, bundle, analysis, suffix="owner-suffix-crossing")
    with pytest.raises(normal_v1.H1NormalPrefixInjectedCrashV1):
        _execute(
            case,
            bundle,
            callback=None,
            crash_point=normal_v1.H1NormalPrefixCrashPointV1.AFTER_INTENT_FSYNC,
        )
    owner_v4.reserve_h1_shared_cap_owner_v4_wal(
        case.owner,
        operation_id=_id("unrelated-owner-operation"),
        site_key="unrelated:owner:site",
        path="io.read_bytes",
        reservation_upper=1,
    )
    with pytest.raises(normal_v1.H1NormalPrefixProtocolFailureV1):
        _execute(case, bundle, callback=None)


def test_open_replays_existing_prefix_without_new_authority(
    fast_root, bundle, analysis
):
    case = _build_case(fast_root, bundle, analysis, suffix="positive-open")
    event = _execute(case, bundle, callback=None)
    opened = normal_v1.open_h1_normal_prefix_journal_v1(case.normal.spec)
    snapshot = normal_v1.replay_h1_normal_prefix_journal_v1(opened)
    assert snapshot.document["completed_event_count"] == 1
    assert snapshot.document["last_event_id"] == event.event_id


def test_high_water_rejects_same_name_different_inode(fast_root, bundle, analysis):
    case = _build_case(fast_root, bundle, analysis, suffix="state-inode")
    root = Path(case.normal.root_directory)
    state_prefix = f"{normal_v1._HIGH_WATER_STATE_PREFIX}{case.normal.route_attempt_id}-"
    state = next(path for path in root.iterdir() if path.name.startswith(state_prefix))
    state_name = state.name
    state.unlink()
    replacement = root / state_name
    replacement.write_bytes(b"not-the-token-inode")
    replacement.chmod(0o600)
    with pytest.raises(normal_v1.H1NormalPrefixProtocolFailureV1):
        normal_v1.replay_h1_normal_prefix_journal_v1(case.normal)


def test_open_rejects_rehashed_allocation_semantic_attack(
    fast_root, bundle, analysis
):
    case = _build_case(fast_root, bundle, analysis, suffix="allocation-attack")
    allocation_path = (
        Path(case.normal.root_directory)
        / normal_v1._allocation_name(case.normal.route_attempt_id)
    )
    document = normal_v1.loads_canonical_json(allocation_path.read_bytes())
    document["single_attempt_allocation"] = False
    payload = dict(document)
    payload.pop("h1_normal_prefix_allocation_id")
    document["h1_normal_prefix_allocation_id"] = normal_v1._content_id(
        normal_v1.ALLOCATION_DOMAIN, payload
    )
    allocation_path.chmod(0o600)
    allocation_path.write_bytes(normal_v1.canonical_json_bytes(document))
    allocation_path.chmod(0o400)
    with pytest.raises(normal_v1.H1NormalPrefixProtocolFailureV1):
        normal_v1.open_h1_normal_prefix_journal_v1(case.normal.spec)


def test_open_rejects_allocation_numeric_type_and_physical_inode_attacks(
    fast_root, bundle, analysis
):
    numeric_case = _build_case(
        fast_root, bundle, analysis, suffix="allocation-numeric-type"
    )
    allocation_path = (
        Path(numeric_case.normal.root_directory)
        / normal_v1._allocation_name(numeric_case.normal.route_attempt_id)
    )
    document = normal_v1.loads_canonical_json(allocation_path.read_bytes())
    document["normal_prefix_root_inode"] = True
    payload = dict(document)
    payload.pop("h1_normal_prefix_allocation_id")
    document["h1_normal_prefix_allocation_id"] = normal_v1._content_id(
        normal_v1.ALLOCATION_DOMAIN, payload
    )
    allocation_path.chmod(0o600)
    allocation_path.write_bytes(normal_v1.canonical_json_bytes(document))
    allocation_path.chmod(0o400)
    with pytest.raises(normal_v1.ConstructionK7H1PhaseAwareNormalPrefixV1Error):
        normal_v1.open_h1_normal_prefix_journal_v1(numeric_case.normal.spec)

    inode_case = _build_case(fast_root, bundle, analysis, suffix="physical-inode")
    lock_path = Path(inode_case.normal.journal_directory) / normal_v1._LOCK_FILE
    lock_path.unlink()
    lock_path.write_bytes(b"")
    lock_path.chmod(0o600)
    with pytest.raises(normal_v1.ConstructionK7H1PhaseAwareNormalPrefixV1Error):
        normal_v1.open_h1_normal_prefix_journal_v1(inode_case.normal.spec)


@pytest.mark.parametrize("child_raises", [False, True])
def test_fork_child_cannot_publish_parent_callback_authority(
    fast_root, bundle, analysis, child_raises
):
    if not hasattr(os, "fork"):
        pytest.skip("requires fork")
    case = _build_case(
        fast_root, bundle, analysis, suffix=f"callback-fork-{child_raises}"
    )
    for row in bundle.program.transitions[:5]:
        _execute(case, bundle, callback=_callback_for(row))

    parent_pid = os.getpid()
    read_fd, write_fd = os.pipe()

    def callback():
        child = os.fork()
        if child == 0:
            os.close(read_fd)
            if child_raises:
                raise RuntimeError("child callback branch")
            return 2
        os.waitpid(child, 0)
        return 1

    try:
        try:
            event = _execute(case, bundle, callback=callback)
        except normal_v1.H1NormalPrefixForkedCallbackContinuationV1:
            if os.getpid() != parent_pid:
                os.write(write_fd, b"child-aborted")
                os.close(write_fd)
                os._exit(0)
            raise
        os.close(write_fd)
        assert os.read(read_fd, 64) == b"child-aborted"
    finally:
        for descriptor in (read_fd, write_fd):
            try:
                os.close(descriptor)
            except OSError:
                pass
    assert event.outcome == "SUCCESS"
    assert event.document["native_observed_value"] == 1
    assert event.document["callback_invocation_count"] == 1
    assert len(event.document["owner_appended_records"]) == 7


def test_foreign_thread_cannot_consume_or_reuse_site_lease(
    fast_root, bundle, analysis
):
    case = _build_case(fast_root, bundle, analysis, suffix="thread-crossing")
    with normal_v1.hold_h1_phase_aware_normal_prefix_lease_v1(
        case.normal,
        phase_handle=case.phase,
        rejection_gate=case.gate,
        owner=case.owner,
        bundle=bundle,
        dispatch_profile=case.dispatch_profile,
    ) as lease:
        errors = []

        def cross_thread():
            try:
                normal_v1.execute_next_h1_phase_aware_normal_site_v1(lease)
            except BaseException as error:
                errors.append(error)

        worker = threading.Thread(target=cross_thread)
        worker.start()
        worker.join()
        assert len(errors) == 1
        assert isinstance(
            errors[0], normal_v1.ConstructionK7H1PhaseAwareNormalPrefixV1Error
        )
        event = normal_v1.execute_next_h1_phase_aware_normal_site_v1(lease)
        assert event.outcome == "SUCCESS"
        with pytest.raises(normal_v1.ConstructionK7H1PhaseAwareNormalPrefixV1Error):
            normal_v1.execute_next_h1_phase_aware_normal_site_v1(lease)


@pytest.mark.parametrize(
    "attack",
    [
        "replace_helper",
        "replace_code",
        "mutate_kwdefaults",
        "add_type_method",
        "replace_dependency_view",
        "replace_imported_callable",
        "replace_module_alias",
        "replace_frozen_view_values",
        "mutate_nested_function_code",
    ],
)
def test_callback_cannot_mutate_local_authority_before_publication(
    fast_root, bundle, analysis, attack
):
    case = _build_case(fast_root, bundle, analysis, suffix=f"local-{attack}")
    _execute(case, bundle, callback=None)

    settlement_function = normal_v1._settlement_semantics_from_callback
    settlement_code = settlement_function.__code__
    callback_kwdefaults = normal_v1._callback_document.__kwdefaults__
    assert callback_kwdefaults is not None
    callback_kwdefaults_before = dict(callback_kwdefaults)
    dependency_view = normal_v1.owner_v3
    canonicalizer = normal_v1.canonical_json_bytes
    os_alias = normal_v1.os
    frozen_values = object.__getattribute__(dependency_view, "_values")
    nested_functions = [
        cell.cell_contents
        for cell in (
            normal_v1.hold_h1_phase_aware_normal_prefix_lease_v1.__closure__ or ()
        )
        if type(cell.cell_contents) is FunctionType
    ]
    assert len(nested_functions) == 1
    nested_function = nested_functions[0]
    nested_code = nested_function.__code__

    def callback():
        if attack == "replace_helper":
            normal_v1._settlement_semantics_from_callback = (
                lambda _intent, _result: (
                    owner_v3.H1SharedValueBasisV3.EXACT_NATIVE,
                    0,
                    "SUCCESS",
                    owner_v3.H1SharedValueBasisV3.EXACT_NATIVE.value,
                )
            )
        elif attack == "replace_code":
            settlement_function.__code__ = (
                lambda _intent, _result: (
                    owner_v3.H1SharedValueBasisV3.EXACT_NATIVE,
                    0,
                    "SUCCESS",
                    owner_v3.H1SharedValueBasisV3.EXACT_NATIVE.value,
                )
            ).__code__
        elif attack == "mutate_kwdefaults":
            callback_kwdefaults["callback_invocation_count"] = 0
        elif attack == "add_type_method":
            normal_v1.H1NormalSiteCallbackResultV1.__getattribute__ = (
                lambda self, name: object.__getattribute__(self, name)
            )
        elif attack == "replace_dependency_view":
            normal_v1.owner_v3 = object()
        elif attack == "replace_imported_callable":
            normal_v1.canonical_json_bytes = lambda _value: b"{}"
        elif attack == "replace_module_alias":
            normal_v1.os = object()
        elif attack == "replace_frozen_view_values":
            replacement = dict(frozen_values)
            replacement["_limit"] = lambda _profile, _path: None
            object.__setattr__(
                dependency_view, "_values", MappingProxyType(replacement)
            )
        else:
            nested_function.__code__ = nested_code.replace(
                co_consts=nested_code.co_consts + ("nested-code-drift",)
            )
        return 5

    try:
        with pytest.raises((RuntimeError, normal_v1.ConstructionK7H1PhaseAwareNormalPrefixV1Error)):
            _execute(case, bundle, callback=callback)
    finally:
        normal_v1._settlement_semantics_from_callback = settlement_function
        settlement_function.__code__ = settlement_code
        callback_kwdefaults.clear()
        callback_kwdefaults.update(callback_kwdefaults_before)
        normal_v1.owner_v3 = dependency_view
        normal_v1.canonical_json_bytes = canonicalizer
        normal_v1.os = os_alias
        object.__setattr__(dependency_view, "_values", frozen_values)
        nested_function.__code__ = nested_code
        if "__getattribute__" in vars(normal_v1.H1NormalSiteCallbackResultV1):
            delattr(normal_v1.H1NormalSiteCallbackResultV1, "__getattribute__")

    calls = []
    event = _execute(case, bundle, callback=lambda: calls.append(1) or 1)
    assert calls == []
    assert event.outcome == "CALLBACK_FAILED_AFTER_ADMISSION"
    assert event.document["callback_invocation_may_have_occurred"] is True


def test_callback_cannot_reopen_consumed_lease_authority(
    fast_root, bundle, analysis
):
    case = _build_case(fast_root, bundle, analysis, suffix="lease-consumed-reset")
    _execute(case, bundle, callback=None)
    with normal_v1.hold_h1_phase_aware_normal_prefix_lease_v1(
        case.normal,
        phase_handle=case.phase,
        rejection_gate=case.gate,
        owner=case.owner,
        bundle=bundle,
        dispatch_profile=case.dispatch_profile,
    ) as lease:
        def callback():
            object.__setattr__(lease, "_site_consumed", False)
            return 1

        with pytest.raises(normal_v1.ConstructionK7H1PhaseAwareNormalPrefixV1Error):
            normal_v1.execute_next_h1_phase_aware_normal_site_v1(
                lease, callback=callback
            )
        assert lease._site_consumed is True
        assert lease._active is False
        with pytest.raises(normal_v1.ConstructionK7H1PhaseAwareNormalPrefixV1Error):
            normal_v1.execute_next_h1_phase_aware_normal_site_v1(lease)


def test_detected_callback_code_drift_is_restored_before_later_recovery(
    fast_root, bundle, analysis
):
    case = _build_case(fast_root, bundle, analysis, suffix="code-drift-restored")
    _execute(case, bundle, callback=None)
    function = normal_v1._settlement_semantics_from_callback
    original_code = function.__code__

    def callback():
        function.__code__ = (
            lambda _intent, _result: (
                owner_v3.H1SharedValueBasisV3.EXACT_SOURCE_EVENT,
                1,
                "SUCCESS",
                owner_v3.H1SharedValueBasisV3.EXACT_SOURCE_EVENT.value,
            )
        ).__code__
        return 1

    with pytest.raises(RuntimeError):
        _execute(case, bundle, callback=callback)
    assert function.__code__ is original_code
    assert normal_v1._LOCAL_AUTHORITY_POISONED is False

    event = _execute(case, bundle, callback=None)
    assert event.outcome == "CALLBACK_FAILED_AFTER_ADMISSION"
    assert event.document["native_observed_value"] == {
        "kind": "NOT_APPLICABLE",
        "reason": "NO_EXACT_NATIVE_VALUE",
    }
    assert event.document["callback_invocation_may_have_occurred"] is True


def test_callback_cannot_weaken_import_authority_state_for_later_sites(
    fast_root, bundle, analysis
):
    case = _build_case(fast_root, bundle, analysis, suffix="state-binding-weaken")
    _execute(case, bundle, callback=None)
    original_state = normal_v1._IMPORT_LOCAL_AUTHORITY_STATE

    def callback():
        normal_v1._IMPORT_LOCAL_AUTHORITY_STATE = (original_state[0],)
        return 1

    with pytest.raises(normal_v1.ConstructionK7H1PhaseAwareNormalPrefixV1Error):
        _execute(case, bundle, callback=callback)
    assert normal_v1._IMPORT_LOCAL_AUTHORITY_STATE is original_state

    event = _execute(case, bundle, callback=None)
    assert event.outcome == "CALLBACK_FAILED_AFTER_ADMISSION"
    assert event.document["callback_invocation_may_have_occurred"] is True


def test_callback_cannot_change_durable_intent_input(fast_root, bundle, analysis):
    case = _build_case(fast_root, bundle, analysis, suffix="intent-input-mutation")
    _execute(case, bundle, callback=None)

    def callback():
        frame = normal_v1.inspect.currentframe()
        assert frame is not None and frame.f_back is not None
        callback_frame = frame.f_back
        intent = callback_frame.f_locals["intent"]
        intent["native_evidence_source_id"] = _id("mutated-evidence-source")
        return 1

    with pytest.raises(normal_v1.ConstructionK7H1PhaseAwareNormalPrefixV1Error):
        _execute(case, bundle, callback=callback)


def test_claim_boundary_remains_locked():
    assert normal_v1.AUTHORITY_STAGE == "PRETRANSITION_ONLY"
    assert normal_v1.PHASE_AWARE_NORMAL_PREFIX_PRETRANSITION_1_40_PRESENT is True
    assert normal_v1.NORMAL_PREFIX_1_40_DURABLE_HAPPY_PATH_PRESENT is True
    assert normal_v1.NORMAL_PREFIX_1_40_PRETRANSITION_EVENT_RECOVERY_PRESENT is False
    assert (
        normal_v1.PHASE_AWARE_CAP_REJECTION_PAIR_ACK_EVENT_PRETRANSITION_RECOVERY_PRESENT
        is False
    )
    assert normal_v1.PHASE_AWARE_NORMAL_PREFIX_1_40_PRESENT is False
    assert normal_v1.NORMAL_PREFIX_1_40_NO_EVENT_RECOVERY_COMPLETE is False
    assert normal_v1.PHASE_AWARE_CAP_REJECTION_RECOVERY_PRESENT is False
    assert normal_v1.PHASE_AWARE_FAILURE_TO_CLEANUP_TRANSITION_PRESENT is False
    assert normal_v1.NO_EVENT_RECOVERY_COMPLETE is False
    assert normal_v1.CLEANUP_EXECUTION_AUTHORITY_PRESENT is False
    assert normal_v1.PRODUCTION_OUTPUT_LEAF_AUTHORITY_PRESENT is False
    assert normal_v1.FORMAL_COUNTER_RECORDS_ISSUED is False
    assert normal_v1.FORMAL_WORK_VECTOR_ISSUED is False
    assert normal_v1.FORMAL_COMPARISON_VECTOR_ISSUED is False
    assert normal_v1.FORMAL_V7_ROUTE_AUTHORITY_PRESENT is False
    assert normal_v1.OFFICIAL_EXECUTION_ALLOWED is False
