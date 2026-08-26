from __future__ import annotations

import ast
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile

import pytest

from acfqp import construction_k7_campaign_measurement_failure_freeze_v180r12r3r2 as frozen


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT
    / "src/acfqp/"
    "construction_k7_campaign_measurement_failure_freeze_v180r12r3r2.py"
)
BASE = ROOT / ".tmp/exact-freeze"


@pytest.fixture
def native_tmp_path() -> Path:
    with tempfile.TemporaryDirectory(
        prefix="acfqp-v180r12r3r2-failure-freeze-", dir="/tmp"
    ) as directory:
        yield Path(directory)


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def _resign_plain(document: dict[str, object], identity_field: str) -> None:
    payload = dict(document)
    del payload[identity_field]
    document[identity_field] = hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _resign_domain(
    document: dict[str, object], identity_field: str, domain: str
) -> None:
    payload = dict(document)
    del payload[identity_field]
    document[identity_field] = hashlib.sha256(
        domain.encode("utf-8") + b"\x00" + _canonical_bytes(payload)
    ).hexdigest()


def _copy_failure_boundary(destination: Path) -> None:
    destination.mkdir(mode=0o700)
    prelaunch = destination / "v180r12r3r2_campaign_measurement_prelaunch"
    output = destination / "v180r12r3r2_campaign_measurement"
    events = output / "EVENTS"
    prelaunch.mkdir(mode=0o700)
    output.mkdir(mode=0o700)
    events.mkdir(mode=0o700)
    for relative, _size, _digest in frozen._RETAINED_FILE_FACTS:
        target = destination / relative
        shutil.copyfile(BASE / relative, target)
        target.chmod(0o400)
    prelaunch.chmod(0o700)
    output.chmod(0o700)
    events.chmod(0o700)


def _require_documents(
    value: frozen.FrozenCampaignMeasurementFailureV180r12r3r2,
    *,
    launch_failure_raw: bytes | None = None,
    measurement_failure_raw: bytes | None = None,
    event_raws: tuple[bytes, bytes] | None = None,
) -> dict[str, object]:
    return frozen._require_failure_documents(
        value.external_root_bytes,
        value.materialization_terminal_bytes,
        value.launch_manifest_bytes,
        value.launch_attempt_bytes,
        launch_failure_raw or value.launch_failure_bytes,
        value.scientific_attempt_bytes,
        measurement_failure_raw or value.measurement_failure_bytes,
        event_raws or value.event_bytes,
    )


def _construct_frozen_object(
    value: frozen.FrozenCampaignMeasurementFailureV180r12r3r2,
    **overrides: object,
) -> frozen.FrozenCampaignMeasurementFailureV180r12r3r2:
    fields: dict[str, object] = {
        "_issuer": frozen._ISSUER,
        "external_root_bytes": value.external_root_bytes,
        "materialization_terminal_bytes": value.materialization_terminal_bytes,
        "launch_manifest_bytes": value.launch_manifest_bytes,
        "launch_attempt_bytes": value.launch_attempt_bytes,
        "launch_failure_bytes": value.launch_failure_bytes,
        "scientific_attempt_bytes": value.scientific_attempt_bytes,
        "measurement_failure_bytes": value.measurement_failure_bytes,
        "event_bytes": value.event_bytes,
        "launch_attempt_id": value.launch_attempt_id,
        "launch_failure_id": value.launch_failure_id,
        "campaign_attempt_id": value.campaign_attempt_id,
        "campaign_attempt_record_id": value.campaign_attempt_record_id,
        "failure_state_id": value.failure_state_id,
        "event_ids": value.event_ids,
    }
    fields.update(overrides)
    return frozen.FrozenCampaignMeasurementFailureV180r12r3r2(**fields)


def test_actual_scientific_internal_failure_is_frozen() -> None:
    value = frozen.load_frozen_campaign_measurement_failure_v180r12r3r2()
    launch_attempt = value.launch_attempt_document()
    launch_failure = value.launch_failure_document()
    scientific_attempt = value.scientific_attempt_document()
    measurement_failure = value.measurement_failure_document()
    event_zero, event_one = value.event_documents()

    assert value.launch_attempt_id == frozen.EXPECTED_LAUNCH_ATTEMPT_ID
    assert value.launch_failure_id == frozen.EXPECTED_LAUNCH_FAILURE_ID
    assert value.campaign_attempt_id == frozen.EXPECTED_CAMPAIGN_ATTEMPT_ID
    assert (
        value.campaign_attempt_record_id
        == frozen.EXPECTED_CAMPAIGN_ATTEMPT_RECORD_ID
    )
    assert value.failure_state_id == frozen.EXPECTED_FAILURE_STATE_ID
    assert value.event_ids == frozen.EXPECTED_EVENT_IDS
    assert len(frozen._RETAINED_FILE_FACTS) == 11
    assert len(frozen._PRELAUNCH_EXACT_ENTRIES) == 5
    assert frozen._OUTPUT_EXACT_ENTRIES == {"EVENTS"}
    assert frozen._EVENTS_EXACT_ENTRIES == {"000000.json", "000001.json"}
    assert len(frozen._REQUIRED_ABSENT_PATHS) == 16
    assert frozen.EXPECTED_RETAINED_FAILURE_TOTAL_BYTE_COUNT == sum(
        size for _relative, size, _digest in frozen._RETAINED_FILE_FACTS
    )

    assert launch_attempt["scientific_occurrence_started"] is False
    assert launch_attempt["campaign_actual_measurement"] is False
    assert launch_attempt["authorized_child_measurement_execution_attempted"] is True
    assert launch_failure["authorized_child_measurement_execution_completed"] is False
    assert launch_failure["producer_free_verification_attempted"] is False
    assert scientific_attempt["one_shot_attempt_opened"] is True
    assert scientific_attempt["attempt_id"] == value.campaign_attempt_id
    assert measurement_failure["failure_code"] == "SUPERVISOR_BIRTH_FAILURE"
    assert measurement_failure["message"] == "PermissionError: (13, 'Permission denied')"
    assert measurement_failure["completed_event_count"] == 2
    assert measurement_failure["completed_event_count"] < frozen.EXPECTED_SUCCESS_EVENT_COUNT
    assert measurement_failure["counter_records_issued"] is False
    assert measurement_failure["successful_ledger_claimed"] is False
    assert event_zero["event_kind"] == "ATTEMPT_OPEN"
    assert event_one["event_kind"] == "PROCESS_BIRTH_INTENT"
    assert event_one["previous_event_id"] == event_zero["event_id"]
    assert event_zero["monotonic_ns"] < event_one["monotonic_ns"]
    assert measurement_failure["last_event_id"] == event_one["event_id"]
    assert frozen.FAILURE_CLAIM_BOUNDARY == (
        "PERMISSION_DENIED_DURING_SUPERVISOR_BIRTH_OR_CLONE_PATH;"
        "EXACT_FAILING_SYSCALL_UNPROVEN"
    )


def test_loader_rechecks_the_complete_storage_boundary_before_return(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inventory_calls: list[str] = []
    retained_read_calls: list[str] = []
    absence_calls: list[str] = []
    cgroup_calls = 0
    original_inventory = frozen._require_inventory
    original_read = frozen._stable_read
    original_absent = frozen._require_absent
    original_cgroup = frozen._require_attempt_cgroup_absent

    def counted_inventory(
        base_fd: int,
        relative_path: str,
        expected_entries: frozenset[str],
        *,
        expected_mode: int,
        expected_nlink: int,
    ) -> None:
        inventory_calls.append(relative_path)
        original_inventory(
            base_fd,
            relative_path,
            expected_entries,
            expected_mode=expected_mode,
            expected_nlink=expected_nlink,
        )

    def counted_read(
        base_fd: int,
        relative_path: str,
        expected_size: int,
        expected_sha256: str,
        *,
        expected_mode: int,
    ) -> bytes:
        raw = original_read(
            base_fd,
            relative_path,
            expected_size,
            expected_sha256,
            expected_mode=expected_mode,
        )
        if relative_path in frozen._RETAINED_FILE_FACT_BY_PATH:
            retained_read_calls.append(relative_path)
        return raw

    def counted_absent(base_fd: int, relative_path: str) -> None:
        absence_calls.append(relative_path)
        original_absent(base_fd, relative_path)

    def counted_cgroup() -> None:
        nonlocal cgroup_calls
        cgroup_calls += 1
        original_cgroup()

    monkeypatch.setattr(frozen, "_require_inventory", counted_inventory)
    monkeypatch.setattr(frozen, "_stable_read", counted_read)
    monkeypatch.setattr(frozen, "_require_absent", counted_absent)
    monkeypatch.setattr(frozen, "_require_attempt_cgroup_absent", counted_cgroup)
    frozen.load_frozen_campaign_measurement_failure_v180r12r3r2()

    assert inventory_calls == [
        frozen._PRELAUNCH,
        frozen._OUTPUT,
        frozen._EVENTS,
    ] * 2
    assert retained_read_calls == [
        relative for relative, _size, _digest in frozen._RETAINED_FILE_FACTS
    ] * 2
    assert absence_calls == list(frozen._REQUIRED_ABSENT_PATHS) * 2
    assert cgroup_calls == 2


def test_post_first_read_extra_event_is_caught_by_return_recheck(
    native_tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    base = native_tmp_path / "exact-freeze"
    _copy_failure_boundary(base)
    original = frozen._stable_read
    retained_read_count = 0

    def insert_after_first_snapshot(
        base_fd: int,
        relative_path: str,
        expected_size: int,
        expected_sha256: str,
        *,
        expected_mode: int,
    ) -> bytes:
        nonlocal retained_read_count
        raw = original(
            base_fd,
            relative_path,
            expected_size,
            expected_sha256,
            expected_mode=expected_mode,
        )
        if relative_path in frozen._RETAINED_FILE_FACT_BY_PATH:
            retained_read_count += 1
            if retained_read_count == len(frozen._RETAINED_FILE_FACTS):
                extra = base / frozen._EVENTS / "000002.json"
                extra.write_bytes(b"{}")
                extra.chmod(0o400)
        return raw

    monkeypatch.setattr(frozen, "_stable_read", insert_after_first_snapshot)
    with pytest.raises(
        frozen.FrozenCampaignMeasurementFailureV180r12r3r2Error,
        match="inventory exceeded its cap",
    ):
        frozen.load_frozen_campaign_measurement_failure_v180r12r3r2(base)


def test_post_absence_success_artifact_is_caught_by_return_recheck(
    native_tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    base = native_tmp_path / "exact-freeze"
    _copy_failure_boundary(base)
    original = frozen._require_absent
    absence_count = 0

    def insert_after_first_absence_pass(base_fd: int, relative_path: str) -> None:
        nonlocal absence_count
        original(base_fd, relative_path)
        absence_count += 1
        if absence_count == len(frozen._REQUIRED_ABSENT_PATHS):
            success = base / "v180r12r3r2_campaign_measurement_verification.json"
            success.write_bytes(b"{}")
            success.chmod(0o400)

    monkeypatch.setattr(frozen, "_require_absent", insert_after_first_absence_pass)
    with pytest.raises(
        frozen.FrozenCampaignMeasurementFailureV180r12r3r2Error,
        match="forbidden V180r12r3r2 artifact exists",
    ):
        frozen.load_frozen_campaign_measurement_failure_v180r12r3r2(base)


def test_post_read_file_replacement_is_caught_by_return_recheck(
    native_tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    base = native_tmp_path / "exact-freeze"
    _copy_failure_boundary(base)
    original = frozen._stable_read
    replaced = False

    def replace_after_read(
        base_fd: int,
        relative_path: str,
        expected_size: int,
        expected_sha256: str,
        *,
        expected_mode: int,
    ) -> bytes:
        nonlocal replaced
        raw = original(
            base_fd,
            relative_path,
            expected_size,
            expected_sha256,
            expected_mode=expected_mode,
        )
        if relative_path == frozen._ATTEMPT_RELATIVE_PATH and not replaced:
            target = base / relative_path
            replacement = target.with_name(".replacement")
            replacement.write_bytes(raw[:-1] + b"[")
            replacement.chmod(0o400)
            os.replace(replacement, target)
            replaced = True
        return raw

    monkeypatch.setattr(frozen, "_stable_read", replace_after_read)
    with pytest.raises(
        frozen.FrozenCampaignMeasurementFailureV180r12r3r2Error,
        match="retained file bytes changed",
    ):
        frozen.load_frozen_campaign_measurement_failure_v180r12r3r2(base)


def test_pinned_runner_orders_cgroup_topology_before_birth_intent() -> None:
    raw = (ROOT / frozen._MEASUREMENT_RUNNER_RELATIVE_PATH).read_bytes()
    frozen._require_runner_causal_source(raw)
    source = raw.decode("utf-8")
    assert source.count("SUCCESS_EVENT_COUNT = 625") == 1
    create = source.index("cgroup, topology_receipt = adapter.create_cgroup(attempt_id)")
    register = source.index("campaign.register_evidence_document(topology_receipt)")
    intent = source.index(
        "birth_plan = campaign.success_event_plan[campaign.event_count]"
    )
    launch = source.index("child, supervisor_birth_receipt = adapter.launch_supervisor(")
    assert create < register < intent < launch
    assert "CGROUP_MKDIR_FAILURE" not in frozen.FAILURE_CLAIM_BOUNDARY
    assert "EXACT_FAILING_SYSCALL_UNPROVEN" in frozen.FAILURE_CLAIM_BOUNDARY


def test_same_size_resigned_retained_file_is_rejected(native_tmp_path: Path) -> None:
    base = native_tmp_path / "exact-freeze"
    _copy_failure_boundary(base)
    path = (
        base
        / "v180r12r3r2_campaign_measurement_prelaunch_measurement_launch_failure.json"
    )
    document = json.loads(path.read_bytes())
    document["child_stderr"]["sha256"] = "0" * 64
    _resign_plain(document, "launch_failure_id")
    raw = _canonical_bytes(document)
    assert len(raw) == frozen.EXPECTED_LAUNCH_FAILURE_BYTE_COUNT
    path.chmod(0o600)
    path.write_bytes(raw)
    path.chmod(0o400)
    with pytest.raises(
        frozen.FrozenCampaignMeasurementFailureV180r12r3r2Error,
        match="retained file bytes changed",
    ):
        frozen.load_frozen_campaign_measurement_failure_v180r12r3r2(base)


def test_resigned_root_cause_traceback_mutation_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    value = frozen.load_frozen_campaign_measurement_failure_v180r12r3r2()
    failure = value.launch_failure_document()
    stderr_raw = bytes.fromhex(failure["child_stderr"]["retained_prefix_hex"])
    original = b"PermissionError"
    replacement = b"ConnectionError"
    assert len(original) == len(replacement)
    assert stderr_raw.count(original) == 1
    mutated_stderr = stderr_raw.replace(original, replacement)
    mutated_stderr_sha256 = hashlib.sha256(mutated_stderr).hexdigest()
    failure["child_stderr"]["retained_prefix_hex"] = mutated_stderr.hex()
    failure["child_stderr"]["sha256"] = mutated_stderr_sha256
    _resign_plain(failure, "launch_failure_id")
    monkeypatch.setattr(frozen, "EXPECTED_CHILD_STDERR_SHA256", mutated_stderr_sha256)
    monkeypatch.setattr(
        frozen, "EXPECTED_LAUNCH_FAILURE_ID", failure["launch_failure_id"]
    )
    with pytest.raises(
        frozen.FrozenCampaignMeasurementFailureV180r12r3r2Error,
        match="supervisor-birth root-cause traceback changed",
    ):
        _require_documents(value, launch_failure_raw=_canonical_bytes(failure))


def test_resigned_outer_progress_mutation_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    value = frozen.load_frozen_campaign_measurement_failure_v180r12r3r2()
    failure = value.launch_failure_document()
    failure["progress_observations"]["terminal"] = {"presence": "PRESENT"}
    _resign_plain(failure, "launch_failure_id")
    monkeypatch.setattr(
        frozen, "EXPECTED_LAUNCH_FAILURE_ID", failure["launch_failure_id"]
    )
    with pytest.raises(
        frozen.FrozenCampaignMeasurementFailureV180r12r3r2Error,
        match="outer launch progress observations changed",
    ):
        _require_documents(value, launch_failure_raw=_canonical_bytes(failure))


def test_resigned_event_semantic_mutation_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    value = frozen.load_frozen_campaign_measurement_failure_v180r12r3r2()
    event_zero, event_one = value.event_documents()
    event_one["event_kind"] = "CGROUP_MKDIR_FAILURE"
    _resign_domain(event_one, "event_id", frozen._EVENT_DOMAIN)
    monkeypatch.setattr(
        frozen,
        "EXPECTED_EVENT_IDS",
        (event_zero["event_id"], event_one["event_id"]),
    )
    with pytest.raises(
        frozen.FrozenCampaignMeasurementFailureV180r12r3r2Error,
        match="two-event causal prefix changed",
    ):
        _require_documents(
            value,
            event_raws=(value.event_bytes[0], _canonical_bytes(event_one)),
        )


def test_resigned_typed_failure_semantic_mutation_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    value = frozen.load_frozen_campaign_measurement_failure_v180r12r3r2()
    failure = value.measurement_failure_document()
    failure["failure_code"] = "CGROUP_MKDIR_FAILURE"
    _resign_domain(failure, "failure_state_id", frozen._FAILURE_STATE_DOMAIN)
    monkeypatch.setattr(
        frozen, "EXPECTED_FAILURE_STATE_ID", failure["failure_state_id"]
    )
    with pytest.raises(
        frozen.FrozenCampaignMeasurementFailureV180r12r3r2Error,
        match="typed scientific failure boundary changed",
    ):
        _require_documents(value, measurement_failure_raw=_canonical_bytes(failure))


def test_extra_event_is_bounded_and_rejected(native_tmp_path: Path) -> None:
    base = native_tmp_path / "exact-freeze"
    _copy_failure_boundary(base)
    extra = base / "v180r12r3r2_campaign_measurement/EVENTS/000002.json"
    extra.write_bytes(b"{}")
    extra.chmod(0o400)
    with pytest.raises(
        frozen.FrozenCampaignMeasurementFailureV180r12r3r2Error,
        match="inventory exceeded its cap",
    ):
        frozen.load_frozen_campaign_measurement_failure_v180r12r3r2(base)


@pytest.mark.parametrize(
    "relative_path,is_directory",
    (
        ("v180r12r3r2_campaign_measurement/TERMINAL.json", False),
        ("v180r12r3r2_campaign_measurement_cas", True),
        ("v180r12r3r2_campaign_measurement_verification.json", False),
    ),
)
def test_success_cas_or_verification_coexistence_is_rejected(
    native_tmp_path: Path, relative_path: str, is_directory: bool
) -> None:
    base = native_tmp_path / "exact-freeze"
    _copy_failure_boundary(base)
    path = base / relative_path
    if is_directory:
        path.mkdir(mode=0o700)
    else:
        path.write_bytes(b"{}")
        path.chmod(0o400)
    with pytest.raises(
        frozen.FrozenCampaignMeasurementFailureV180r12r3r2Error,
        match="inventory exceeded its cap|forbidden V180r12r3r2 artifact exists",
    ):
        frozen.load_frozen_campaign_measurement_failure_v180r12r3r2(base)


def test_wrong_output_directory_mode_is_rejected(native_tmp_path: Path) -> None:
    base = native_tmp_path / "exact-freeze"
    _copy_failure_boundary(base)
    (base / "v180r12r3r2_campaign_measurement").chmod(0o755)
    with pytest.raises(
        frozen.FrozenCampaignMeasurementFailureV180r12r3r2Error,
        match="directory inventory changed",
    ):
        frozen.load_frozen_campaign_measurement_failure_v180r12r3r2(base)


def test_foreign_frozen_failure_object_is_rejected() -> None:
    value = frozen.load_frozen_campaign_measurement_failure_v180r12r3r2()
    with pytest.raises(
        frozen.FrozenCampaignMeasurementFailureV180r12r3r2Error,
        match="foreign",
    ):
        frozen.FrozenCampaignMeasurementFailureV180r12r3r2(
            _issuer=object(),
            external_root_bytes=value.external_root_bytes,
            materialization_terminal_bytes=value.materialization_terminal_bytes,
            launch_manifest_bytes=value.launch_manifest_bytes,
            launch_attempt_bytes=value.launch_attempt_bytes,
            launch_failure_bytes=value.launch_failure_bytes,
            scientific_attempt_bytes=value.scientific_attempt_bytes,
            measurement_failure_bytes=value.measurement_failure_bytes,
            event_bytes=value.event_bytes,
            launch_attempt_id=value.launch_attempt_id,
            launch_failure_id=value.launch_failure_id,
            campaign_attempt_id=value.campaign_attempt_id,
            campaign_attempt_record_id=value.campaign_attempt_record_id,
            failure_state_id=value.failure_state_id,
            event_ids=value.event_ids,
        )


def test_bytearray_is_rejected_before_document_parsing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    value = frozen.load_frozen_campaign_measurement_failure_v180r12r3r2()

    def parsing_must_not_start(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("document parsing started")

    monkeypatch.setattr(frozen, "_require_failure_documents", parsing_must_not_start)
    with pytest.raises(
        frozen.FrozenCampaignMeasurementFailureV180r12r3r2Error,
        match="raw bytes are foreign",
    ):
        _construct_frozen_object(
            value,
            _issuer=frozen._ISSUER,
            launch_attempt_bytes=bytearray(value.launch_attempt_bytes),
        )


def test_evil_str_id_is_rejected_before_document_parsing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    value = frozen.load_frozen_campaign_measurement_failure_v180r12r3r2()

    class EvilStr(str):
        def __eq__(self, _other: object) -> bool:
            raise AssertionError("evil string equality ran")

        def __iter__(self):
            raise AssertionError("evil string iteration ran")

        def encode(self, *_args: object, **_kwargs: object) -> bytes:
            raise AssertionError("evil string encoding ran")

    def parsing_must_not_start(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("document parsing started")

    monkeypatch.setattr(frozen, "_require_failure_documents", parsing_must_not_start)
    with pytest.raises(
        frozen.FrozenCampaignMeasurementFailureV180r12r3r2Error,
        match="scalar IDs are foreign",
    ):
        _construct_frozen_object(
            value,
            _issuer=frozen._ISSUER,
            launch_attempt_id=EvilStr(value.launch_attempt_id),
        )


@pytest.mark.parametrize("field_name", ("event_bytes", "event_ids"))
def test_evil_tuple_is_rejected_before_document_parsing(
    field_name: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    value = frozen.load_frozen_campaign_measurement_failure_v180r12r3r2()

    class EvilTuple(tuple):
        def __len__(self) -> int:
            raise AssertionError("evil tuple length ran")

        def __iter__(self):
            raise AssertionError("evil tuple iteration ran")

        def __getitem__(self, _key: object) -> object:
            raise AssertionError("evil tuple indexing ran")

        def __eq__(self, _other: object) -> bool:
            raise AssertionError("evil tuple equality ran")

    def parsing_must_not_start(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("document parsing started")

    monkeypatch.setattr(frozen, "_require_failure_documents", parsing_must_not_start)
    source = value.event_bytes if field_name == "event_bytes" else value.event_ids
    evil = tuple.__new__(EvilTuple, source)
    with pytest.raises(
        frozen.FrozenCampaignMeasurementFailureV180r12r3r2Error,
        match="tuple is foreign",
    ):
        _construct_frozen_object(
            value,
            _issuer=frozen._ISSUER,
            **{field_name: evil},
        )


def test_oversized_builtin_bytes_are_rejected_before_document_parsing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    value = frozen.load_frozen_campaign_measurement_failure_v180r12r3r2()

    def parsing_must_not_start(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("document parsing started")

    monkeypatch.setattr(frozen, "_require_failure_documents", parsing_must_not_start)
    with pytest.raises(
        frozen.FrozenCampaignMeasurementFailureV180r12r3r2Error,
        match="raw bytes changed: launch attempt",
    ):
        _construct_frozen_object(
            value,
            _issuer=frozen._ISSUER,
            launch_attempt_bytes=value.launch_attempt_bytes + b" ",
        )


def test_failure_evidence_base_has_public_path_caps() -> None:
    assert frozen.FAILURE_EVIDENCE_BASE_COMPONENT_COUNT_CAP == 64
    assert frozen.FAILURE_EVIDENCE_BASE_TOTAL_BYTE_CAP == 4_096
    assert "FAILURE_EVIDENCE_BASE_COMPONENT_COUNT_CAP" in frozen.__all__
    assert "FAILURE_EVIDENCE_BASE_TOTAL_BYTE_CAP" in frozen.__all__
    too_many_components = Path("/").joinpath(
        *("x" for _ in range(frozen.FAILURE_EVIDENCE_BASE_COMPONENT_COUNT_CAP + 1))
    )
    too_many_bytes = Path("/") / (
        "x" * frozen.FAILURE_EVIDENCE_BASE_TOTAL_BYTE_CAP
    )
    for invalid in (too_many_components, too_many_bytes):
        with pytest.raises(
            frozen.FrozenCampaignMeasurementFailureV180r12r3r2Error,
            match="bounded path caps",
        ):
            frozen._open_absolute_directory_no_symlink(invalid)


def test_failure_freeze_has_only_standard_library_imports() -> None:
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module != "__future__":
            imported.add((node.module or "").split(".", 1)[0])
    assert imported == {
        "dataclasses",
        "hashlib",
        "json",
        "os",
        "pathlib",
        "stat",
        "typing",
    }
