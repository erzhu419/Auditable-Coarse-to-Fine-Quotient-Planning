from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

from acfqp import (
    construction_k7_ten_terminal_aggregation_finalizer_v180r12r2
    as finalizer,
)
from acfqp.phase3e_ids import canonical_json_bytes


ROOT = Path(__file__).resolve().parents[1]


def _resign_bundle(document: dict[str, object]) -> bytes:
    for _ in range(32):
        payload = dict(document)
        payload.pop("production_aggregation_bundle_id", None)
        document["production_aggregation_bundle_id"] = (
            finalizer.domains.extension_content_id_v180r12r2(
                finalizer.domains.CONSTRUCTION_K7_TERMINAL_BUNDLE_V180R12R2_DOMAIN,
                payload,
            )
        )
        raw = canonical_json_bytes(document)
        if document["output_bytes_fixed_point"] == len(raw):
            return raw
        document["output_bytes_fixed_point"] = len(raw)
    raise AssertionError("test bundle failed to reach its byte fixed point")


def test_v180r12r2_finalizer_locks_the_corrected_denominators() -> None:
    assert finalizer.SOURCE_GROUP_COUNT == 5
    assert finalizer.TERMINAL_RECEIPT_COUNT == 10
    assert finalizer.ROUTE_COMPONENT_CHAIN_COUNT == 12
    assert finalizer.COUNTER_RECORDS_PER_V9_CHAIN == 269
    assert finalizer.TEN_TERMINAL_REPRESENTATIVE_COUNTER_RECORD_COUNT == 2_690
    assert finalizer.ROUTE_COMPONENT_COUNTER_RECORD_COUNT == 3_228
    assert finalizer.V180R7R1_ADDITIONAL_COUNTER_RECORD_COUNT == 538
    assert finalizer.OCCURRENCE_SHARED_RESOURCE_RECEIPT_COUNT == 90
    assert finalizer.CAMPAIGN_SCOPE_STRUCTURAL_OBLIGATION_COUNT == 9
    assert finalizer.CAMPAIGN_SCOPE_ACTUAL_COUNTER_RECORD_COUNT == 0
    assert finalizer.CAMPAIGN_SCOPE_ACTUAL_SHARED_RESOURCE_RECEIPT_COUNT == 0
    assert finalizer.CAMPAIGN_SCOPE_ACTUAL_WORK_VECTOR_COUNT == 0
    assert finalizer.CAMPAIGN_SCOPE_ACTUAL_COMPARISON_VECTOR_COUNT == 0
    assert finalizer.CAMPAIGN_SCOPE_ACTUAL_PROJECTION_PROOF_COUNT == 0
    assert finalizer.CAMPAIGN_SCOPE_ACTUAL_NATIVE_ZERO_ATTESTATION_COUNT == 0
    assert finalizer.CAMPAIGN_SCOPE_AUTHORITATIVE_RECEIPT_COUNT == 0
    assert finalizer.TOTAL_AUTHORITATIVE_SHARED_RESOURCE_RECEIPT_COUNT == 90
    assert finalizer.COUNTER_COMPLETENESS_BLOCKER == (
        "CAMPAIGN_SCOPE_ACTUAL_MEASUREMENT_LEDGER_ABSENT"
    )
    assert finalizer.ROUTE_COMPONENT_COUNTER_CLOSURE_STATUS == (
        "PENDING_INDEPENDENT_REPLAY"
    )
    assert len(finalizer.EXPECTED_ROUTE_COMPONENTS) == 12
    assert [
        row
        for row in finalizer.EXPECTED_ROUTE_COMPONENTS
        if row[0] == "FULL_GROUND_FALLBACK"
    ] == [
        ("FULL_GROUND_FALLBACK", "ABSTRACT_FAILED_PREFIX"),
        ("FULL_GROUND_FALLBACK", "LOCAL_ATTEMPT"),
        ("FULL_GROUND_FALLBACK", "DIRECT_FALLBACK"),
    ]


def test_v180r12r2_finalizer_uses_only_fresh_r10r1_and_r7r1_sources() -> None:
    roles = finalizer._INPUT_ROLES
    paths = tuple(path for row in roles for path in row[1:])
    assert any("v180r10r1_v36_retained_terminal.json" in path for path in paths)
    assert any(
        "v180r7r1_full_ground_fallback_terminal_bundle.json" in path
        for path in paths
    )
    assert not any("v180r10_v36_resource_successor_terminal.json" in path for path in paths)
    assert not any("v180r7_full_ground_fallback_terminal_bundle.json" in path for path in paths)


def _contract_fixture() -> tuple[
    dict[str, object],
    dict[str, object],
    tuple[finalizer._VerifiedGroup, ...],
]:
    groups = tuple(
        finalizer._VerifiedGroup(
            source_kind,
            terminal_path,
            len(f"terminal-{ordinal}".encode()),
            finalizer._sha256(f"terminal-{ordinal}".encode()),
            {},
            verification_path,
            len(f"verification-{ordinal}".encode()),
            finalizer._sha256(f"verification-{ordinal}".encode()),
            {},
            f"{ordinal + 1:064x}",
            f"{ordinal + 101:064x}",
        )
        for ordinal, (
            source_kind,
            terminal_path,
            verification_path,
        ) in enumerate(finalizer._INPUT_ROLES)
    )
    retained = [
        {
            "source_kind": group.source_kind,
            "terminal_fact": {
                "relative_path": group.terminal_path,
                "content_id": group.terminal_id,
                "byte_count": group.terminal_byte_count,
                "sha256": group.terminal_sha256,
            },
            "verification_fact": {
                "relative_path": group.verification_path,
                "verification_id": group.verification_id,
                "byte_count": group.verification_byte_count,
                "sha256": group.verification_sha256,
            },
        }
        for group in groups
    ]
    protocol = {
        "retained_source_groups": retained,
        "terminal_code_count": 10,
        "ordered_route_components": [
            {
                "component_ordinal": ordinal,
                "terminal_code": terminal_code,
                "route_kind": route_kind,
                "counter_record_count": 269,
            }
            for ordinal, (terminal_code, route_kind) in enumerate(
                finalizer.EXPECTED_ROUTE_COMPONENTS
            )
        ],
    }
    input_facts = [
        fact
        for group in groups
        for fact in (
            {
                "source_kind": group.source_kind,
                "role": "TERMINAL",
                "relative_path": group.terminal_path,
                "content_id": group.terminal_id,
                "byte_count": group.terminal_byte_count,
                "sha256": group.terminal_sha256,
            },
            {
                "source_kind": group.source_kind,
                "role": "INDEPENDENT_VERIFICATION",
                "relative_path": group.verification_path,
                "content_id": group.verification_id,
                "byte_count": group.verification_byte_count,
                "sha256": group.verification_sha256,
            },
        )
    ]
    authorization = {
        "retained_source_input_facts": input_facts,
        "retained_source_input_fact_count": len(input_facts),
        "retained_source_input_total_byte_count": sum(
            row["byte_count"] for row in input_facts
        ),
        "retained_source_input_facts_sha256": finalizer._sha256(
            canonical_json_bytes(input_facts)
        ),
        "source_group_count": 5,
        "terminal_code_count": 10,
    }
    return protocol, authorization, groups


def test_v180r12r2_input_contract_joins_every_exact_retained_byte_fact() -> None:
    protocol, authorization, groups = _contract_fixture()
    finalizer._assert_input_contract(protocol, authorization, groups)
    mutated = json.loads(canonical_json_bytes(authorization))
    mutated["retained_source_input_facts"][2]["sha256"] = "f" * 64
    with pytest.raises(
        finalizer.ConstructionK7TenTerminalAggregationFinalizerV180R12R2Error,
        match="input contract changed",
    ):
        finalizer._assert_input_contract(protocol, mutated, groups)


def test_v180r12r2_claim_locks_require_explicit_null_scalar_fields() -> None:
    locked = {
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "SCALAR_CALIBRATION_GATE": "NOT_RUN",
        "BREAK_EVEN_GATE": "NOT_RUN",
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "official_execution_allowed": False,
    }
    finalizer._claim_locks(locked, "fixture")
    for field in ("official_scalar_cost", "official_N_break_even"):
        incomplete = dict(locked)
        incomplete.pop(field)
        with pytest.raises(
            finalizer.ConstructionK7TenTerminalAggregationFinalizerV180R12R2Error,
            match="accounting or official gate changed",
        ):
            finalizer._claim_locks(incomplete, "fixture")


def test_v180r12r2_verification_claim_locks_follow_exact_retained_schemas() -> None:
    common = {
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "official_execution_allowed": False,
    }
    for source_kind in (
        finalizer._VERIFICATION_ABSENT_SCALAR_FIELDS_SOURCE_KINDS  # noqa: SLF001
    ):
        finalizer._verification_claim_locks(common, source_kind)  # noqa: SLF001
        with pytest.raises(
            finalizer.ConstructionK7TenTerminalAggregationFinalizerV180R12R2Error,
            match="accounting or official gate changed",
        ):
            finalizer._verification_claim_locks(  # noqa: SLF001
                {**common, "official_scalar_cost": None},
                source_kind,
            )

    v180r9 = {
        **common,
        "official_scalar_cost": None,
        "official_N_break_even": None,
    }
    finalizer._verification_claim_locks(  # noqa: SLF001
        v180r9,
        "V180R9_FRESH_SIX_TERMINAL_CAMPAIGN",
    )
    with pytest.raises(
        finalizer.ConstructionK7TenTerminalAggregationFinalizerV180R12R2Error,
        match="accounting or official gate changed",
    ):
        finalizer._verification_claim_locks(  # noqa: SLF001
            common,
            "V180R9_FRESH_SIX_TERMINAL_CAMPAIGN",
        )


def test_v180r12r2_full_producer_core_no_output_under_explicit_16gib_rlimit() -> None:
    code = r'''
import json
import os
from pathlib import Path
import resource
import sys

if not (
    len(sys.argv) == 2
    and sys.executable == "/usr/bin/python3"
    and sys.flags.isolated == 1
    and sys.flags.no_site == 1
    and sys.flags.ignore_environment == 1
    and sys.flags.dont_write_bytecode == 1
    and sys.dont_write_bytecode is True
    and sys.pycache_prefix == "/dev/null/v180r12r2"
):
    raise RuntimeError("producer preflight startup boundary is not isolated")
repository_root = Path(sys.argv[1]).resolve(strict=True)
bound_source = (repository_root / "src").resolve(strict=True)
if str(bound_source) in sys.path:
    raise RuntimeError("bound source existed before producer preflight insertion")
sys.path.insert(0, str(bound_source))
if sys.path[0] != str(bound_source):
    raise RuntimeError("producer preflight bound source insertion changed")

from acfqp import construction_k7_ten_terminal_aggregation_finalizer_v180r12r2 as f

Path(f.__file__).resolve(strict=True).relative_to(bound_source)

cap = 16 * 1024 * 1024 * 1024
resource.setrlimit(resource.RLIMIT_AS, (cap, cap))
artifact_relative_paths = {
    "runtime_cas_root": f.authorization.RUNTIME_CAS_ROOT_RELATIVE_PATH,
    "output_root": f.authorization.OUTPUT_ROOT_RELATIVE_PATH,
    "production_terminal": f.authorization.TERMINAL_RELATIVE_PATH,
    "production_failure": f.authorization.FAILURE_RELATIVE_PATH,
    "verification": f.authorization.VERIFICATION_RELATIVE_PATH,
    "verification_failure": f.authorization.VERIFICATION_FAILURE_RELATIVE_PATH,
    "retained_verification_replay": (
        f.authorization.RETAINED_VERIFICATION_REPLAY_RELATIVE_PATH
    ),
}
def artifact_snapshot():
    return {
        name: {
            "relative_path": relative_path,
            "lexists": os.path.lexists(repository_root / relative_path),
        }
        for name, relative_path in sorted(artifact_relative_paths.items())
    }
artifact_snapshot_before = artifact_snapshot()
if any(row["lexists"] for row in artifact_snapshot_before.values()):
    raise AssertionError("V180r12r2 artifact path existed before producer preflight")
protocol_id = "a" * 64
authorization_id = "b" * 64
protocol_document = (
    f.protocol.freeze_ten_terminal_aggregation_protocol_v180r12r2().to_document()
)
authorization_document = (
    f.authorization
    .freeze_ten_terminal_aggregation_execution_authorization_v180r12r2()
    .to_document()
)
raw = f.reconstruct_ten_terminal_aggregation_core_no_output_v180r12r2(
    repository_root,
    aggregation_protocol_id=protocol_id,
    execution_authorization_id=authorization_id,
    protocol_document=protocol_document,
    authorization_document=authorization_document,
)
document = f._object(raw, "dummy-ID no-output producer core")
artifact_snapshot_after = artifact_snapshot()
if any(row["lexists"] for row in artifact_snapshot_after.values()):
    raise AssertionError("V180r12r2 artifact path exists after producer preflight")
payload = {
    "preflight_kind": "PRE_PREREG_NONFROZEN_DEVELOPMENT_RESOURCE_PREFLIGHT",
    "evidence_class": "NONFROZEN_DEVELOPMENT_EVIDENCE",
    "lifecycle_scope": "DUMMY_ID_NO_OUTPUT_FULL_PRODUCER_CORE",
    "formal_production_runner_phase_schedule_replayed": False,
    "startup_python_executable": sys.executable,
    "startup_isolated": sys.flags.isolated,
    "startup_no_site": sys.flags.no_site,
    "startup_dont_write_bytecode": sys.flags.dont_write_bytecode,
    "startup_pycache_prefix": sys.pycache_prefix,
    "bound_source": str(bound_source),
    "production_artifact_written": False,
    "scientific_authority": False,
    "artifact_snapshot_before": artifact_snapshot_before,
    "artifact_snapshot_after": artifact_snapshot_after,
    "rlimit_as_bytes": cap,
    "byte_count": len(raw),
    "sha256": f._sha256(raw),
    "fixed_point": document["output_bytes_fixed_point"],
    "source_receipt_count": len(document["source_verification_receipts"]),
    "terminal_receipt_count": len(document["terminal_receipts"]),
    "route_component_receipt_count": len(
        document["route_component_chain_receipts"]
    ),
    "shared_receipt_set_count": len(
        document["terminal_shared_resource_receipt_sets"]
    ),
    "shared_receipt_count": sum(
        row["receipt_count"]
        for row in document["terminal_shared_resource_receipt_sets"]
    ),
    "route_component_counter_record_count": document[
        "route_component_counter_record_count"
    ],
    "actual_axes": {
        field: document[field]
        for field in (
            "campaign_scope_actual_counter_record_count",
            "campaign_scope_actual_shared_resource_receipt_count",
            "campaign_scope_actual_work_vector_count",
            "campaign_scope_actual_comparison_vector_count",
            "campaign_scope_actual_projection_proof_count",
            "campaign_scope_actual_native_zero_attestation_count",
            "campaign_scope_authoritative_receipt_count",
        )
    },
    "scalar_gate": document["SCALAR_CALIBRATION_GATE"],
    "break_even_gate": document["BREAK_EVEN_GATE"],
    "ru_maxrss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
    "ru_maxrss_interpretation": "PROCESS_MAXIMUM_RESIDENT_SET_SIZE_ONLY",
    "ru_maxrss_is_address_space_headroom": False,
}
print(f.canonical_json_bytes(payload).decode("utf-8"), flush=True)
'''
    completed = subprocess.run(
        [
            "/usr/bin/python3",
            "-I",
            "-S",
            "-B",
            "-X",
            "pycache_prefix=/dev/null/v180r12r2",
            "-c",
            code,
            str(ROOT),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=14_400,
    )
    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["preflight_kind"] == (
        "PRE_PREREG_NONFROZEN_DEVELOPMENT_RESOURCE_PREFLIGHT"
    )
    assert payload["evidence_class"] == "NONFROZEN_DEVELOPMENT_EVIDENCE"
    assert payload["lifecycle_scope"] == "DUMMY_ID_NO_OUTPUT_FULL_PRODUCER_CORE"
    assert payload["formal_production_runner_phase_schedule_replayed"] is False
    assert payload["startup_python_executable"] == "/usr/bin/python3"
    assert payload["startup_isolated"] == 1
    assert payload["startup_no_site"] == 1
    assert payload["startup_dont_write_bytecode"] == 1
    assert payload["startup_pycache_prefix"] == "/dev/null/v180r12r2"
    assert payload["bound_source"] == str((ROOT / "src").resolve())
    assert payload["production_artifact_written"] is False
    assert payload["scientific_authority"] is False
    assert payload["artifact_snapshot_before"] == payload["artifact_snapshot_after"]
    assert len(payload["artifact_snapshot_before"]) == 7
    assert all(
        row["lexists"] is False
        for row in payload["artifact_snapshot_before"].values()
    )
    assert payload["rlimit_as_bytes"] == 16 * 1024 * 1024 * 1024
    assert payload["byte_count"] == payload["fixed_point"]
    assert len(payload["sha256"]) == 64
    assert payload["source_receipt_count"] == 5
    assert payload["terminal_receipt_count"] == 10
    assert payload["route_component_receipt_count"] == 12
    assert payload["shared_receipt_set_count"] == 10
    assert payload["shared_receipt_count"] == 90
    assert payload["route_component_counter_record_count"] == 3_228
    assert set(payload["actual_axes"].values()) == {0}
    assert payload["scalar_gate"] == "NOT_RUN"
    assert payload["break_even_gate"] == "NOT_RUN"
    assert payload["ru_maxrss_interpretation"] == (
        "PROCESS_MAXIMUM_RESIDENT_SET_SIZE_ONLY"
    )
    assert payload["ru_maxrss_is_address_space_headroom"] is False
    assert payload["ru_maxrss_kib"] * 1024 <= 16 * 1024 * 1024 * 1024
    print(canonical_json_bytes(payload).decode("utf-8"), flush=True)


def test_v180r12r2_compact_projection_rejects_extra_or_missing_keys() -> None:
    terminal = json.loads(
        (
            ROOT
            / ".tmp/v180r8-cached-exact-production/TERMINAL.json"
        ).read_bytes()
    )
    projection = finalizer._compact_terminal_projection(  # noqa: SLF001
        "V180R8_FRESH_CACHED_EXACT",
        terminal,
    )
    assert set(projection) == finalizer._SINGLE_CHAIN_PROJECTION_FIELDS  # noqa: SLF001
    assert "durable_proof_bytes_hex" not in projection
    assert "production_execution_slot" not in projection
    assert projection["source_occurrence_shared_resource_receipt_ids"] == [
        row["receipt_id"]
        for row in terminal["shared_resource_receipt_set"]["receipts"]
    ]

    malformed = dict(terminal)
    malformed["shared_resource_receipt_set"] = {
        **terminal["shared_resource_receipt_set"],
        "receipts": terminal["shared_resource_receipt_set"]["receipts"][:-1],
    }
    with pytest.raises(
        finalizer.ConstructionK7TenTerminalAggregationFinalizerV180R12R2Error,
        match="receipt identities changed",
    ):
        finalizer._compact_terminal_projection(  # noqa: SLF001
            "V180R8_FRESH_CACHED_EXACT",
            malformed,
        )


def test_v180r12r2_runtime_rejects_duplicate_counter_record_ids() -> None:
    vectors = [
        SimpleNamespace(
            records=[
                SimpleNamespace(record_id=f"{ordinal:064x}")
                for ordinal in range(finalizer.ROUTE_COMPONENT_COUNTER_RECORD_COUNT)
            ]
        )
    ]
    finalizer._assert_global_counter_record_uniqueness(vectors)  # noqa: SLF001
    vectors[0].records[-1].record_id = vectors[0].records[0].record_id
    with pytest.raises(
        finalizer.ConstructionK7TenTerminalAggregationFinalizerV180R12R2Error,
        match="3228 unique CounterRecords",
    ):
        finalizer._assert_global_counter_record_uniqueness(vectors)  # noqa: SLF001


def test_v180r12r2_heap_release_is_fail_closed_and_structural(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert finalizer.TRANSIENT_HEAP_RELEASE_PHASE_COUNT == 7
    assert finalizer.TRANSIENT_HEAP_RELEASE_AUTHORITY_CLASS == (
        "PREAUTHORIZATION_MEMORY_LIFECYCLE_STRUCTURAL_OBLIGATION"
    )

    def absent(_name: object) -> object:
        raise OSError("fixture absent")

    monkeypatch.setattr(finalizer.ctypes, "CDLL", absent)
    with pytest.raises(
        finalizer.ConstructionK7TenTerminalAggregationFinalizerV180R12R2Error,
        match="malloc_trim lifecycle primitive is unavailable",
    ):
        finalizer._release_transient_verifier_heap()  # noqa: SLF001


def test_v180r12r2_heap_release_rejects_foreign_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _ForeignTrim:
        argtypes: object = None
        restype: object = None

        def __call__(self, _pad: int) -> int:
            return 2

    monkeypatch.setattr(
        finalizer.ctypes,
        "CDLL",
        lambda _name: SimpleNamespace(malloc_trim=_ForeignTrim()),
    )
    with pytest.raises(
        finalizer.ConstructionK7TenTerminalAggregationFinalizerV180R12R2Error,
        match="foreign status",
    ):
        finalizer._release_transient_verifier_heap()  # noqa: SLF001


def test_v180r12r2_replays_all_three_r7r1_route_component_chains() -> None:
    terminal = json.loads(
        (
            ROOT
            / ".tmp/exact-freeze/"
            "v180r7r1_full_ground_fallback_terminal_bundle.json"
        ).read_bytes()
    )
    vectors = []
    for component in terminal["v9_lifted_route_components"]:
        vectors.append(
            finalizer._verify_chain(
                vector_document=component["v9_work_vector"],
                comparison_document=component["v9_comparison_vector"],
                proof_document=component["v9_actual_projection_proof"],
                zero_document=component["v9_native_zero_attestation"],
                expected_route_kind=component["v9_work_vector"]["route_kind"],
            )
        )
    assert [row.route_kind.value for row in vectors] == [
        "ABSTRACT_FAILED_PREFIX",
        "LOCAL_ATTEMPT",
        "DIRECT_FALLBACK",
    ]
    assert sum(len(row.records) for row in vectors) == 807
    receipt_set = finalizer._terminal_shared_receipt_set(
        terminal_code=finalizer.TerminalCode.FULL_GROUND_FALLBACK,
        source_receipt_id="a" * 64,
        source_receipt_ids=terminal["source_occurrence_accounting_bundle"][
            "shared_resource_receipt_ids"
        ],
        vectors=vectors,
        aggregation_protocol_id="b" * 64,
        execution_authorization_id="c" * 64,
    )
    assert receipt_set["receipt_count"] == 9
    assert len(receipt_set["receipts"]) == 9
    assert all(
        len(row["source_route_component_values"]) == 3
        for row in receipt_set["receipts"]
    )
    assert all(
        row["source_occurrence_shared_resource_receipt_count"] == 9
        and row["source_occurrence_shared_resource_receipt_ids_embedded"] is True
        for row in receipt_set["receipts"]
    )


def test_v180r12r2_construction_axis_is_separate_and_nonroute() -> None:
    terminal_bytes = (
        ROOT
        / ".tmp/exact-freeze/"
        "v180r7r1_full_ground_fallback_terminal_bundle.json"
    ).read_bytes()
    verification_bytes = (
        ROOT
        / ".tmp/exact-freeze/"
        "v180r7r1_full_ground_fallback_verification.json"
    ).read_bytes()
    terminal = json.loads(terminal_bytes)
    verification = json.loads(verification_bytes)
    group = finalizer._verified_group(
        source_kind="V180R7R1_FRESH_FULL_GROUND_FALLBACK",
        terminal_path=finalizer._INPUT_ROLES[2][1],
        terminal_bytes=terminal_bytes,
        terminal=terminal,
        verification_path=finalizer._INPUT_ROLES[2][2],
        verification_bytes=verification_bytes,
        verification=verification,
        terminal_id_field="production_terminal_bundle_id",
    )
    receipt = finalizer._construction_axis_receipt(
        group=group,
        source_receipt_id="a" * 64,
        aggregation_protocol_id="b" * 64,
        execution_authorization_id="c" * 64,
    )
    assert receipt["one_time_construction_axis"] is True
    assert receipt["charged_to_any_route_component"] is False
    assert receipt["occurrence_route_counter_record_count"] == 0
    assert receipt["construction_axis_replayed_separately"] is True
    assert receipt["materialized_source_module_count"] == 307
    assert receipt["materialized_source_byte_count"] == 15_129_926


def test_v180r12r2_finalizer_uses_only_campaign_structural_obligations() -> None:
    source = Path(finalizer.__file__).read_text(encoding="utf-8")
    assert "record_campaign_scope_shared_resources_v180r12r2" in source
    assert "derive_campaign_scope_accounting_v180r12r2" in source
    assert "verify_campaign_scope_accounting_v180r12r2" in source
    assert "RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE" not in source
    assert finalizer._BUNDLE_FIELDS >= {
        "campaign_scope_structural_boundary",
        "campaign_scope_structural_obligation_count",
        "campaign_scope_actual_counter_record_count",
        "campaign_scope_actual_shared_resource_receipt_count",
        "campaign_scope_actual_work_vector_count",
        "campaign_scope_actual_comparison_vector_count",
        "campaign_scope_actual_projection_proof_count",
        "campaign_scope_actual_native_zero_attestation_count",
        "campaign_scope_authoritative_receipt_count",
        "total_authoritative_shared_resource_receipt_count",
        "route_component_counter_closure_status",
        "COUNTER_COMPLETENESS_BLOCKER",
        "v180r7r1_construction_axis_receipt",
        "route_component_chain_receipts",
        "terminal_shared_resource_receipt_sets",
        "COUNTER_COMPLETENESS_GATE",
        "WORKLOAD_ECONOMICS_GATE",
        "SCALAR_CALIBRATION_GATE",
        "BREAK_EVEN_GATE",
        "official_scalar_cost",
        "official_N_break_even",
        "official_execution_allowed",
    }
    assert "campaign_scope_accounting" not in finalizer._BUNDLE_FIELDS
    assert "campaign_scope_shared_resource_receipt_count" not in (
        finalizer._BUNDLE_FIELDS
    )
    assert "total_shared_resource_receipt_count" not in finalizer._BUNDLE_FIELDS


def test_v180r12r2_real_campaign_api_enters_exact_structural_guard() -> None:
    values = {
        "common.hash_invocations": 15,
        "common.integrity_checks": 10,
        "common.protocol_checks": 10,
        "io.mounted_bytes_peak": 0,
        "io.output_bytes": 1_234,
        "io.read_bytes": 5_678,
        "io.staged_bytes": 0,
        "memory.working_bytes_peak": finalizer.WORKING_BYTES_HARD_CAP,
        "process.launches": 0,
    }
    declarations = (
        finalizer.campaign_accounting.record_campaign_scope_shared_resources_v180r12r2(
            aggregation_protocol_id="a" * 64,
            execution_authorization_id="b" * 64,
            subject_id="c" * 64,
            source_receipt_ids=[f"{ordinal:064x}" for ordinal in range(1, 6)],
            values=values,
        )
    )
    boundary = (
        finalizer.campaign_accounting.derive_campaign_scope_accounting_v180r12r2(
            declarations
        )
    )
    replayed = (
        finalizer.campaign_accounting.verify_campaign_scope_accounting_v180r12r2(
            boundary.canonical_bytes
        )
    )
    document = replayed.to_document()
    finalizer._assert_campaign_scope_structural_boundary(document)

    assert set(document) == finalizer._CAMPAIGN_STRUCTURAL_BOUNDARY_FIELDS
    assert document["structural_declaration_count"] == 9
    assert document["actual_counter_record_count"] == 0
    assert document["campaign_scope_authoritative_receipt_count"] == 0
    assert document["authoritative_occurrence_receipt_count"] == 90
    assert document["authoritative_receipt_total"] == 90
    assert document["actual_work_vector_present"] is False
    assert document["actual_comparison_vector_present"] is False
    assert document["actual_projection_proof_present"] is False
    assert document["actual_native_zero_attestation_present"] is False
    assert document["native_zero_claim_count"] == 0
    assert document["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
    assert all(
        set(row) == finalizer._CAMPAIGN_STRUCTURAL_DECLARATION_FIELDS
        and row["actual_measurement_present"] is False
        and row["counter_gate_eligible"] is False
        and row["economics_gate_eligible"] is False
        and "observed" not in row
        and "native_zero_observed" not in row
        for row in document["structural_declarations"]
    )

    inflated = json.loads(canonical_json_bytes(document))
    inflated["actual_work_vector_present"] = True
    with pytest.raises(
        finalizer.ConstructionK7TenTerminalAggregationFinalizerV180R12R2Error,
        match="structural boundary replay changed",
    ):
        finalizer._assert_campaign_scope_structural_boundary(inflated)


def test_v180r12r2_materializer_uses_real_structural_accounting_api(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    protocol_id = "a" * 64
    authorization_id = "b" * 64
    locked = {
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "official_execution_allowed": False,
    }
    protocol_document = dict(locked)
    authorization_document = {
        **locked,
        "aggregation_protocol_id": protocol_id,
    }
    monkeypatch.setattr(finalizer.protocol, "EXPECTED_PROTOCOL_ID", protocol_id)
    monkeypatch.setattr(
        finalizer.authorization,
        "EXPECTED_AUTHORIZATION_ID",
        authorization_id,
    )
    monkeypatch.setattr(
        finalizer.protocol,
        "freeze_ten_terminal_aggregation_protocol_v180r12r2",
        lambda: SimpleNamespace(
            aggregation_protocol_id=protocol_id,
            to_document=lambda: protocol_document,
        ),
    )
    monkeypatch.setattr(
        finalizer.authorization,
        "freeze_ten_terminal_aggregation_execution_authorization_v180r12r2",
        lambda: SimpleNamespace(
            authorization_id=authorization_id,
            to_document=lambda: authorization_document,
        ),
    )
    groups = tuple(
        SimpleNamespace(terminal_byte_count=1, verification_byte_count=1)
        for _ in range(5)
    )
    source_receipts = [
        {"source_receipt_id": f"{ordinal:064x}"}
        for ordinal in range(1, 6)
    ]
    monkeypatch.setattr(finalizer, "_load_verified_groups", lambda root: groups)
    monkeypatch.setattr(
        finalizer,
        "_assert_input_contract",
        lambda protocol_doc, authorization_doc, loaded_groups: None,
    )
    monkeypatch.setattr(
        finalizer,
        "_all_receipts",
        lambda loaded_groups, **kwargs: (
            source_receipts,
            [{} for _ in range(10)],
            [{} for _ in range(12)],
            [{} for _ in range(10)],
            {},
        ),
    )
    monkeypatch.setattr(finalizer, "_subject_id", lambda **kwargs: "c" * 64)

    raw = finalizer.materialize_ten_terminal_aggregation_v180r12r2(tmp_path)
    no_output_raw = (
        finalizer.reconstruct_ten_terminal_aggregation_core_no_output_v180r12r2(
            tmp_path,
            aggregation_protocol_id=protocol_id,
            execution_authorization_id=authorization_id,
            protocol_document=protocol_document,
            authorization_document=authorization_document,
        )
    )
    assert no_output_raw == raw
    assert list(tmp_path.iterdir()) == []
    document = json.loads(raw)
    boundary = document["campaign_scope_structural_boundary"]
    finalizer._assert_campaign_scope_structural_boundary(boundary)
    assert boundary["authoritative_receipt_total"] == 90
    assert boundary["actual_counter_record_count"] == 0
    actual_axes = {
        "campaign_scope_actual_counter_record_count",
        "campaign_scope_actual_shared_resource_receipt_count",
        "campaign_scope_actual_work_vector_count",
        "campaign_scope_actual_comparison_vector_count",
        "campaign_scope_actual_projection_proof_count",
        "campaign_scope_actual_native_zero_attestation_count",
        "campaign_scope_authoritative_receipt_count",
    }
    assert {field: document[field] for field in actual_axes} == {
        field: 0 for field in actual_axes
    }
    assert document["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
    assert document["SCALAR_CALIBRATION_GATE"] == "NOT_RUN"
    assert document["BREAK_EVEN_GATE"] == "NOT_RUN"
    valid_bundle = finalizer.TenTerminalAggregationBundleV180R12R2(
        finalizer._ISSUER,  # noqa: SLF001
        raw,
        document["production_aggregation_bundle_id"],
    )
    assert valid_bundle.canonical_bytes == raw
    for field, foreign_value in (
        ("campaign_scope_actual_counter_record_count", 1),
        ("campaign_scope_actual_shared_resource_receipt_count", 1),
        ("campaign_scope_actual_work_vector_count", 1),
        ("campaign_scope_actual_comparison_vector_count", 1),
        ("campaign_scope_actual_projection_proof_count", 1),
        ("campaign_scope_actual_native_zero_attestation_count", 1),
        ("campaign_scope_authoritative_receipt_count", 1),
        ("SCALAR_CALIBRATION_GATE", "PASS"),
        ("BREAK_EVEN_GATE", "PASS"),
    ):
        mutated_document = json.loads(raw)
        mutated_document[field] = foreign_value
        mutated_raw = _resign_bundle(mutated_document)
        with pytest.raises(
            finalizer.ConstructionK7TenTerminalAggregationFinalizerV180R12R2Error,
            match="foreign or malformed",
        ):
            finalizer.TenTerminalAggregationBundleV180R12R2(
                finalizer._ISSUER,  # noqa: SLF001
                mutated_raw,
                mutated_document["production_aggregation_bundle_id"],
            )
