from __future__ import annotations

import ast
from copy import deepcopy
import os
from pathlib import Path
import subprocess
import shutil
import sys
from types import SimpleNamespace
from typing import Any, Sequence

import pytest

from acfqp import construction_k7_domain_registry_extension_v180r12r2 as domains
from acfqp import construction_k7_domain_registry_extension_v180r12r2e as subdomains
from acfqp import (
    construction_k7_ten_terminal_aggregation_independent_verifier_v180r12r2
    as verifier,
)
from acfqp import (
    construction_k7_ten_terminal_aggregation_campaign_accounting_v180r12r2
    as producer_campaign_accounting,
)
from acfqp.phase3e_ids import canonical_json_bytes


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_ID = "a" * 64
AUTHORIZATION_ID = "b" * 64


@pytest.fixture(scope="module")
def groups() -> tuple[verifier._VerifiedGroup, ...]:
    return verifier._capture_verified_groups(ROOT, replay_semantics=False)


@pytest.fixture(scope="module")
def aggregation_bytes(
    groups: Sequence[verifier._VerifiedGroup],
) -> bytes:
    return verifier._reconstruct_aggregation_bytes(
        groups,
        PROTOCOL_ID,
        AUTHORIZATION_ID,
    )


def _contract_documents(
    groups: Sequence[verifier._VerifiedGroup],
) -> tuple[dict[str, Any], dict[str, Any]]:
    source_rows = verifier._protocol_source_rows(groups)
    input_rows = verifier._authorization_input_rows(groups)
    gates = {
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "SCALAR_CALIBRATION_GATE": "NOT_RUN",
        "BREAK_EVEN_GATE": "NOT_RUN",
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "official_execution_allowed": False,
    }
    protocol_document = {
        "retained_source_groups": source_rows,
        "retained_source_total_byte_count": sum(
            group.terminal_byte_count + group.verification_byte_count
            for group in groups
        ),
        "source_group_count": 5,
        "terminal_code_count": 10,
        "route_component_chain_count": 12,
        "ordered_route_components": [
            {
                "terminal_code": terminal_code,
                "route_kind": route_kind,
                "component_ordinal": ordinal,
                "counter_record_count": 269,
            }
            for ordinal, (terminal_code, route_kind) in enumerate(
                verifier.EXPECTED_ROUTE_COMPONENTS
            )
        ],
        **gates,
    }
    authorization_document = {
        "retained_source_input_facts": input_rows,
        "retained_source_input_fact_count": 10,
        "retained_source_input_total_byte_count": sum(
            row["byte_count"] for row in input_rows
        ),
        "retained_source_input_facts_sha256": verifier._sha256(
            canonical_json_bytes(input_rows)
        ),
        "source_group_count": 5,
        "terminal_code_count": 10,
        "route_component_chain_count": 12,
        **gates,
    }
    return protocol_document, authorization_document


def _install_synthetic_contract(
    monkeypatch: pytest.MonkeyPatch,
    groups: Sequence[verifier._VerifiedGroup],
    *,
    capture_groups: bool = True,
) -> None:
    protocol_document, authorization_document = _contract_documents(groups)
    monkeypatch.setattr(
        verifier,
        "_frozen_contract",
        lambda: (
            PROTOCOL_ID,
            AUTHORIZATION_ID,
            protocol_document,
            authorization_document,
        ),
    )
    monkeypatch.setattr(
        verifier,
        "_replay_group_semantics",
        lambda group, _root: group.verification,
    )
    if capture_groups:
        monkeypatch.setattr(
            verifier,
            "_capture_verified_groups",
            lambda _root, replay_semantics=True: tuple(groups),
        )


def _resign_subdocument(
    document: dict[str, Any],
    identity_field: str,
    domain: str,
) -> str:
    payload = dict(document)
    payload.pop(identity_field, None)
    identity = subdomains.extension_content_id_v180r12r2e(domain, payload)
    document[identity_field] = identity
    return identity


def test_v180r12r2_compact_groups_have_exact_minimal_projection_keys(
    groups: Sequence[verifier._VerifiedGroup],
) -> None:
    assert [set(row.terminal) for row in groups] == [
        verifier._SINGLE_CHAIN_PROJECTION_FIELDS,
        verifier._SINGLE_CHAIN_PROJECTION_FIELDS,
        verifier._R7R1_PROJECTION_FIELDS,
        verifier._SINGLE_CHAIN_PROJECTION_FIELDS,
        verifier._R9_PROJECTION_FIELDS,
    ]
    assert all(
        set(row.verification) == verifier._VERIFICATION_PROJECTION_FIELDS
        for row in groups
    )
    assert sum(row.terminal_byte_count for row in groups) == 15_488_382
    assert sum(row.verification_byte_count for row in groups) == 7_657


def test_v180r12r2_independent_runtime_rejects_duplicate_counter_ids() -> None:
    vectors = [
        SimpleNamespace(
            records=[
                SimpleNamespace(record_id=f"{ordinal:064x}")
                for ordinal in range(verifier.ROUTE_COMPONENT_COUNTER_RECORD_COUNT)
            ]
        )
    ]
    verifier._assert_global_counter_record_uniqueness(vectors)
    vectors[0].records[-1].record_id = vectors[0].records[0].record_id
    with pytest.raises(
        verifier.ConstructionK7TenTerminalAggregationIndependentVerifierV180R12R2Error,
        match="3228 unique CounterRecords",
    ):
        verifier._assert_global_counter_record_uniqueness(vectors)


def test_v180r12r2_independent_heap_release_is_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert verifier.TRANSIENT_HEAP_RELEASE_PHASE_COUNT == 10
    assert verifier.TRANSIENT_HEAP_RELEASE_AUTHORITY_CLASS == (
        "PREAUTHORIZATION_MEMORY_LIFECYCLE_STRUCTURAL_OBLIGATION"
    )

    def absent(_name: object) -> object:
        raise OSError("fixture absent")

    monkeypatch.setattr(verifier.ctypes, "CDLL", absent)
    with pytest.raises(
        verifier.ConstructionK7TenTerminalAggregationIndependentVerifierV180R12R2Error,
        match="malloc_trim lifecycle primitive is unavailable",
    ):
        verifier._release_transient_verifier_heap()


def test_v180r12r2_independent_heap_release_rejects_foreign_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _ForeignTrim:
        argtypes: object = None
        restype: object = None

        def __call__(self, _pad: int) -> int:
            return 2

    monkeypatch.setattr(
        verifier.ctypes,
        "CDLL",
        lambda _name: SimpleNamespace(malloc_trim=_ForeignTrim()),
    )
    with pytest.raises(
        verifier.ConstructionK7TenTerminalAggregationIndependentVerifierV180R12R2Error,
        match="foreign status",
    ):
        verifier._release_transient_verifier_heap()


def test_v180r12r2_two_full_verify_lifecycles_fit_explicit_16gib_rlimit() -> None:
    code = r'''
import gc
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
    raise RuntimeError("verifier preflight startup boundary is not isolated")
repository_root = Path(sys.argv[1]).resolve(strict=True)
bound_source = (repository_root / "src").resolve(strict=True)
if str(bound_source) in sys.path:
    raise RuntimeError("bound source existed before verifier preflight insertion")
sys.path.insert(0, str(bound_source))
if sys.path[0] != str(bound_source):
    raise RuntimeError("verifier preflight bound source insertion changed")

from acfqp import construction_k7_ten_terminal_aggregation_independent_verifier_v180r12r2 as v
from acfqp import construction_k7_ten_terminal_aggregation_execution_authorization_v180r12r2 as a

Path(v.__file__).resolve(strict=True).relative_to(bound_source)
Path(a.__file__).resolve(strict=True).relative_to(bound_source)

cap = 16 * 1024 * 1024 * 1024
resource.setrlimit(resource.RLIMIT_AS, (cap, cap))
artifact_relative_paths = {
    "runtime_cas_root": a.RUNTIME_CAS_ROOT_RELATIVE_PATH,
    "output_root": a.OUTPUT_ROOT_RELATIVE_PATH,
    "production_terminal": a.TERMINAL_RELATIVE_PATH,
    "production_failure": a.FAILURE_RELATIVE_PATH,
    "verification": a.VERIFICATION_RELATIVE_PATH,
    "verification_failure": a.VERIFICATION_FAILURE_RELATIVE_PATH,
    "retained_verification_replay": a.RETAINED_VERIFICATION_REPLAY_RELATIVE_PATH,
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
    raise AssertionError("V180r12r2 artifact path existed before verifier preflight")
(
    _frozen_protocol_id,
    _frozen_authorization_id,
    protocol_document,
    authorization_document,
) = v._frozen_contract()
candidate_groups = v._capture_verified_groups(repository_root, replay_semantics=False)
candidate_bytes = v._reconstruct_aggregation_bytes(
    candidate_groups,
    "a" * 64,
    "b" * 64,
)
del candidate_groups
gc.collect()
v._release_transient_verifier_heap()
digests = []
for _ordinal in range(2):
    verification = v.verify_ten_terminal_aggregation_core_no_output_v180r12r2(
        candidate_bytes,
        repository_root,
        aggregation_protocol_id="a" * 64,
        execution_authorization_id="b" * 64,
        protocol_document=protocol_document,
        authorization_document=authorization_document,
    )
    digests.append({
        "sha256": verification["aggregation_sha256"],
        "byte_count": verification["aggregation_byte_count"],
        "source_count": verification["source_verification_receipt_count"],
        "terminal_count": verification["terminal_receipt_count"],
        "component_count": verification["route_component_chain_receipt_count"],
        "shared_count": verification[
            "occurrence_shared_resource_receipt_count"
        ],
        "counter_count": verification["route_component_counter_record_count"],
        "construction_axis": verification[
            "v180r7r1_construction_axis_replayed_separately"
        ],
        "verification_id": verification["verification_id"],
    })
    del verification
    gc.collect()
    v._release_transient_verifier_heap()
authorization_document = a.build_ten_terminal_aggregation_execution_authorization_v180r12r2()
bound_paths = {
    row["relative_path"] for row in authorization_document["source_facts"]
}
allowed_exclusions = set(authorization_document["source_fact_exclusions"])
loaded_paths = set()
source_root = (repository_root / "src" / "acfqp").resolve()
for module in tuple(sys.modules.values()):
    module_file = getattr(module, "__file__", None)
    if not isinstance(module_file, str):
        continue
    candidate = Path(module_file)
    try:
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(source_root)
    except (OSError, ValueError):
        continue
    if resolved.suffix == ".py":
        loaded_paths.add(resolved.relative_to(repository_root).as_posix())
unbound_paths = sorted(loaded_paths - bound_paths - allowed_exclusions)
artifact_snapshot_after = artifact_snapshot()
if any(row["lexists"] for row in artifact_snapshot_after.values()):
    raise AssertionError("V180r12r2 artifact path exists after verifier preflight")
payload = {
    "preflight_kind": "PRE_PREREG_NONFROZEN_DEVELOPMENT_RESOURCE_PREFLIGHT",
    "evidence_class": "NONFROZEN_DEVELOPMENT_EVIDENCE",
    "lifecycle_scope": (
        "TWO_SEQUENTIAL_FULL_VERIFY_CORES_WITH_CONSERVATIVE_CANDIDATE_SETUP"
    ),
    "candidate_construction_setup_class": (
        "CONSERVATIVE_IN_PROCESS_CANDIDATE_CONSTRUCTION"
    ),
    "candidate_construction_setup_is_formal_runner_phase": False,
    "formal_verification_runner_phase_schedule_replayed": False,
    "startup_python_executable": sys.executable,
    "startup_isolated": sys.flags.isolated,
    "startup_no_site": sys.flags.no_site,
    "startup_dont_write_bytecode": sys.flags.dont_write_bytecode,
    "startup_pycache_prefix": sys.pycache_prefix,
    "bound_source": str(bound_source),
    "dummy_aggregation_protocol_id": "a" * 64,
    "dummy_execution_authorization_id": "b" * 64,
    "production_artifact_written": False,
    "scientific_authority": False,
    "full_verify_lifecycle_count": 2,
    "artifact_snapshot_before": artifact_snapshot_before,
    "artifact_snapshot_after": artifact_snapshot_after,
    "rlimit_as_bytes": cap,
    "authorization_source_fact_count": len(bound_paths),
    "loaded_repo_local_acfqp_python_module_count": len(loaded_paths),
    "allowed_source_fact_exclusions": sorted(allowed_exclusions),
    "unbound_repo_local_acfqp_python_modules": unbound_paths,
    "digests": digests,
    "ru_maxrss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
    "ru_maxrss_interpretation": "PROCESS_MAXIMUM_RESIDENT_SET_SIZE_ONLY",
    "ru_maxrss_is_address_space_headroom": False,
}
print(v.canonical_json_bytes(payload).decode("utf-8"), flush=True)
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
        timeout=28_800,
    )
    assert completed.returncode == 0, completed.stderr
    payload = __import__("json").loads(completed.stdout)
    print(canonical_json_bytes(payload).decode("utf-8"), flush=True)
    first, second = payload["digests"]
    assert first == second
    assert payload["full_verify_lifecycle_count"] == 2
    assert first["source_count"] == 5
    assert first["terminal_count"] == 10
    assert first["component_count"] == 12
    assert first["shared_count"] == 90
    assert first["counter_count"] == 3_228
    assert first["construction_axis"] is True
    assert payload["preflight_kind"] == (
        "PRE_PREREG_NONFROZEN_DEVELOPMENT_RESOURCE_PREFLIGHT"
    )
    assert payload["evidence_class"] == "NONFROZEN_DEVELOPMENT_EVIDENCE"
    assert payload["lifecycle_scope"] == (
        "TWO_SEQUENTIAL_FULL_VERIFY_CORES_WITH_CONSERVATIVE_CANDIDATE_SETUP"
    )
    assert payload["candidate_construction_setup_class"] == (
        "CONSERVATIVE_IN_PROCESS_CANDIDATE_CONSTRUCTION"
    )
    assert payload["candidate_construction_setup_is_formal_runner_phase"] is False
    assert payload["formal_verification_runner_phase_schedule_replayed"] is False
    assert payload["startup_python_executable"] == "/usr/bin/python3"
    assert payload["startup_isolated"] == 1
    assert payload["startup_no_site"] == 1
    assert payload["startup_dont_write_bytecode"] == 1
    assert payload["startup_pycache_prefix"] == "/dev/null/v180r12r2"
    assert payload["bound_source"] == str((ROOT / "src").resolve())
    assert payload["dummy_aggregation_protocol_id"] == "a" * 64
    assert payload["dummy_execution_authorization_id"] == "b" * 64
    assert payload["production_artifact_written"] is False
    assert payload["scientific_authority"] is False
    assert payload["artifact_snapshot_before"] == payload["artifact_snapshot_after"]
    assert len(payload["artifact_snapshot_before"]) == 7
    assert all(
        row["lexists"] is False
        for row in payload["artifact_snapshot_before"].values()
    )
    assert payload["rlimit_as_bytes"] == 16 * 1024 * 1024 * 1024
    assert payload["authorization_source_fact_count"] > 0
    assert payload["loaded_repo_local_acfqp_python_module_count"] > 0
    assert payload["allowed_source_fact_exclusions"] == [
        "src/acfqp/construction_k7_ten_terminal_aggregation_"
        "execution_authorization_v180r12r2.py"
    ]
    assert payload["unbound_repo_local_acfqp_python_modules"] == []
    assert payload["ru_maxrss_interpretation"] == (
        "PROCESS_MAXIMUM_RESIDENT_SET_SIZE_ONLY"
    )
    assert payload["ru_maxrss_is_address_space_headroom"] is False
    assert payload["ru_maxrss_kib"] * 1024 <= 16 * 1024 * 1024 * 1024


def _resign_bundle(document: dict[str, Any]) -> bytes:
    for _ in range(32):
        payload = dict(document)
        payload.pop("production_aggregation_bundle_id", None)
        document["production_aggregation_bundle_id"] = (
            domains.extension_content_id_v180r12r2(
                domains.CONSTRUCTION_K7_TERMINAL_BUNDLE_V180R12R2_DOMAIN,
                payload,
            )
        )
        raw = canonical_json_bytes(document)
        if document["output_bytes_fixed_point"] == len(raw):
            return raw
        document["output_bytes_fixed_point"] = len(raw)
    raise AssertionError("test mutation failed to reach an output-size fixed point")


def _rejects_mutation(
    monkeypatch: pytest.MonkeyPatch,
    groups: Sequence[verifier._VerifiedGroup],
    baseline: bytes,
    mutated: bytes,
) -> None:
    _install_synthetic_contract(monkeypatch, groups)
    monkeypatch.setattr(
        verifier,
        "_reconstruct_aggregation_bytes",
        lambda *_args, **_kwargs: baseline,
    )
    with pytest.raises(
        verifier.ConstructionK7TenTerminalAggregationIndependentVerifierV180R12R2Error,
        match="did not reproduce without producer import",
    ):
        verifier.verify_ten_terminal_aggregation_independently_v180r12r2(
            mutated,
            ROOT,
        )


def test_v180r12r2_verifier_import_surface_is_producer_free() -> None:
    source = Path(verifier.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.append(node.module or "")
            imported.extend(alias.name for alias in node.names)
    assert not any("aggregation_finalizer_v180r12r2" in name for name in imported)
    assert not any(
        "aggregation_campaign_accounting_v180r12r2" in name for name in imported
    )
    assert "materialize_ten_terminal_aggregation_v180r12r2" not in source


def test_v180r12r2_verifier_ignores_monkeypatched_campaign_producer_helpers(
    monkeypatch: pytest.MonkeyPatch,
    groups: Sequence[verifier._VerifiedGroup],
    aggregation_bytes: bytes,
) -> None:
    def producer_helper_must_not_run(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("producer campaign helper entered independent verifier")

    for name in (
        "record_campaign_scope_shared_resources_v180r12r2",
        "derive_campaign_scope_accounting_v180r12r2",
        "verify_campaign_scope_accounting_v180r12r2",
    ):
        monkeypatch.setattr(
            producer_campaign_accounting,
            name,
            producer_helper_must_not_run,
        )
    _install_synthetic_contract(monkeypatch, groups)
    result = verifier.verify_ten_terminal_aggregation_independently_v180r12r2(
        aggregation_bytes,
        ROOT,
    )
    assert result["campaign_scope_structural_boundary_replayed"] is True
    assert result["producer_module_imported"] is False


def test_v180r12r2_verifier_rebuilds_exact_bytes_and_bounded_gates(
    monkeypatch: pytest.MonkeyPatch,
    groups: Sequence[verifier._VerifiedGroup],
    aggregation_bytes: bytes,
) -> None:
    _install_synthetic_contract(monkeypatch, groups)
    result = verifier.verify_ten_terminal_aggregation_independently_v180r12r2(
        aggregation_bytes,
        ROOT,
    )
    payload = dict(result)
    verification_id = payload.pop("verification_id")
    assert verification_id == domains.extension_content_id_v180r12r2(
        domains.CONSTRUCTION_K7_VERIFICATION_V180R12R2_DOMAIN,
        payload,
    )
    assert result["source_group_count"] == 5
    assert result["terminal_receipt_count"] == 10
    assert result["route_component_chain_receipt_count"] == 12
    assert result["ten_terminal_representative_counter_record_count"] == 2_690
    assert result["route_component_counter_record_count"] == 3_228
    assert result["v180r7r1_additional_counter_record_count"] == 538
    assert result["occurrence_shared_resource_receipt_count"] == 90
    assert result["campaign_scope_structural_obligation_count"] == 9
    actual_axes = {
        "campaign_scope_actual_counter_record_count",
        "campaign_scope_actual_shared_resource_receipt_count",
        "campaign_scope_actual_work_vector_count",
        "campaign_scope_actual_comparison_vector_count",
        "campaign_scope_actual_projection_proof_count",
        "campaign_scope_actual_native_zero_attestation_count",
        "campaign_scope_authoritative_receipt_count",
    }
    assert {field: result[field] for field in actual_axes} == {
        field: 0 for field in actual_axes
    }
    assert result["total_authoritative_shared_resource_receipt_count"] == 90
    assert result["v180r7r1_construction_axis_replayed_separately"] is True
    assert result["v180r7r1_construction_work_charged_to_route_components"] is False
    assert result["campaign_scope_has_no_route_kind"] is True
    assert result["producer_module_imported"] is False
    assert result["route_component_counter_closure_status"] == "PASS"
    assert result["COUNTER_COMPLETENESS_BLOCKER"] == (
        "CAMPAIGN_SCOPE_ACTUAL_MEASUREMENT_LEDGER_ABSENT"
    )
    assert result["campaign_scope_actual_measurement_ledger_present"] is False
    assert result["v180r12r3_actual_campaign_measurement_ledger_required"] is True
    assert result["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
    assert result["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
    assert result["SCALAR_CALIBRATION_GATE"] == "NOT_RUN"
    assert result["BREAK_EVEN_GATE"] == "NOT_RUN"
    assert result["official_scalar_cost"] is None
    assert result["official_N_break_even"] is None
    assert result["official_execution_allowed"] is False


@pytest.mark.parametrize(
    "field,foreign_value",
    (
        ("campaign_scope_actual_counter_record_count", 1),
        ("campaign_scope_actual_shared_resource_receipt_count", 1),
        ("campaign_scope_actual_work_vector_count", 1),
        ("campaign_scope_actual_comparison_vector_count", 1),
        ("campaign_scope_actual_projection_proof_count", 1),
        ("campaign_scope_actual_native_zero_attestation_count", 1),
        ("campaign_scope_authoritative_receipt_count", 1),
        ("SCALAR_CALIBRATION_GATE", "PASS"),
        ("BREAK_EVEN_GATE", "PASS"),
    ),
)
def test_v180r12r2_verifier_rejects_nonzero_actual_axes_or_unlocked_gates(
    monkeypatch: pytest.MonkeyPatch,
    groups: Sequence[verifier._VerifiedGroup],
    aggregation_bytes: bytes,
    field: str,
    foreign_value: object,
) -> None:
    document = deepcopy(verifier._object(aggregation_bytes, "baseline"))
    document[field] = foreign_value
    mutated = _resign_bundle(document)
    _install_synthetic_contract(monkeypatch, groups)
    monkeypatch.setattr(
        verifier,
        "_reconstruct_aggregation_bytes",
        lambda *_args, **_kwargs: mutated,
    )
    with pytest.raises(
        verifier.ConstructionK7TenTerminalAggregationIndependentVerifierV180R12R2Error,
        match="accounting denominator or claim lock changed",
    ):
        verifier.verify_ten_terminal_aggregation_independently_v180r12r2(
            mutated,
            ROOT,
        )


def test_v180r12r2_verifier_compares_expected_bytes_before_candidate_parse(
    monkeypatch: pytest.MonkeyPatch,
    groups: Sequence[verifier._VerifiedGroup],
) -> None:
    events: list[str] = []
    candidate_bytes = b"candidate"
    protocol_document, authorization_document = _contract_documents(groups)
    monkeypatch.setattr(
        verifier,
        "_capture_verified_groups",
        lambda *_args, **_kwargs: events.append("capture") or groups,
    )
    monkeypatch.setattr(
        verifier,
        "_assert_input_contract",
        lambda *_args, **_kwargs: events.append("input_contract"),
    )
    monkeypatch.setattr(
        verifier,
        "_reconstruct_aggregation_bytes",
        lambda *_args, **_kwargs: events.append("reconstruct") or candidate_bytes,
    )
    monkeypatch.setattr(
        verifier,
        "_object",
        lambda *_args, **_kwargs: events.append("parse_candidate")
        or {"production_aggregation_bundle_id": "c" * 64},
    )
    monkeypatch.setattr(
        verifier,
        "_assert_exact_aggregate_schema",
        lambda *_args, **_kwargs: events.append("full_schema"),
    )
    result = verifier.verify_ten_terminal_aggregation_core_no_output_v180r12r2(
        candidate_bytes,
        ROOT,
        aggregation_protocol_id=PROTOCOL_ID,
        execution_authorization_id=AUTHORIZATION_ID,
        protocol_document=protocol_document,
        authorization_document=authorization_document,
    )
    assert events == [
        "capture",
        "input_contract",
        "reconstruct",
        "parse_candidate",
        "full_schema",
    ]
    assert result["producer_aggregate_exact_bytes_reconstructed"] is True


@pytest.mark.parametrize(
    "source_index,stale_path",
    (
        (1, ".tmp/exact-freeze/v180r10_v36_retained_terminal.json"),
        (2, ".tmp/exact-freeze/v180r7_full_ground_fallback_terminal_bundle.json"),
    ),
)
def test_v180r12r2_verifier_rejects_stale_r10_or_r7_source_paths(
    monkeypatch: pytest.MonkeyPatch,
    groups: Sequence[verifier._VerifiedGroup],
    aggregation_bytes: bytes,
    source_index: int,
    stale_path: str,
) -> None:
    document = deepcopy(verifier._object(aggregation_bytes, "baseline"))
    source = document["source_verification_receipts"][source_index]
    source["terminal_relative_path"] = stale_path
    _resign_subdocument(
        source,
        "source_receipt_id",
        subdomains.CONSTRUCTION_K7_SOURCE_RECEIPT_V180R12R2E_DOMAIN,
    )
    _rejects_mutation(
        monkeypatch,
        groups,
        aggregation_bytes,
        _resign_bundle(document),
    )


@pytest.mark.parametrize("mutation", ("missing", "duplicated"))
def test_v180r12r2_verifier_rejects_missing_or_duplicated_r7_component(
    monkeypatch: pytest.MonkeyPatch,
    groups: Sequence[verifier._VerifiedGroup],
    aggregation_bytes: bytes,
    mutation: str,
) -> None:
    document = deepcopy(verifier._object(aggregation_bytes, "baseline"))
    rows = document["route_component_chain_receipts"]
    r7_rows = [
        index
        for index, row in enumerate(rows)
        if row["terminal_code"] == "FULL_GROUND_FALLBACK"
    ]
    assert len(r7_rows) == 3
    if mutation == "missing":
        rows.pop(r7_rows[0])
    else:
        rows.insert(r7_rows[-1] + 1, deepcopy(rows[r7_rows[-1]]))
    document["route_component_chain_receipt_count"] = len(rows)
    _rejects_mutation(
        monkeypatch,
        groups,
        aggregation_bytes,
        _resign_bundle(document),
    )


def test_v180r12r2_verifier_rejects_construction_work_charged_to_route(
    monkeypatch: pytest.MonkeyPatch,
    groups: Sequence[verifier._VerifiedGroup],
    aggregation_bytes: bytes,
) -> None:
    document = deepcopy(verifier._object(aggregation_bytes, "baseline"))
    construction = document["v180r7r1_construction_axis_receipt"]
    construction["charged_to_any_route_component"] = True
    construction["occurrence_route_counter_record_count"] = 538
    _resign_subdocument(
        construction,
        "v180r7r1_construction_axis_receipt_id",
        subdomains.CONSTRUCTION_K7_V180R7R1_CONSTRUCTION_AXIS_RECEIPT_V180R12R2E_DOMAIN,
    )
    document["v180r7r1_construction_work_charged_to_route_components"] = True
    _rejects_mutation(
        monkeypatch,
        groups,
        aggregation_bytes,
        _resign_bundle(document),
    )


def test_v180r12r2_verifier_rejects_terminal_receipt_denominator_change(
    monkeypatch: pytest.MonkeyPatch,
    groups: Sequence[verifier._VerifiedGroup],
    aggregation_bytes: bytes,
) -> None:
    document = deepcopy(verifier._object(aggregation_bytes, "baseline"))
    receipt_set = document["terminal_shared_resource_receipt_sets"][0]
    receipt_set["receipt_count"] = 8
    _resign_subdocument(
        receipt_set,
        "terminal_shared_resource_receipt_set_id",
        subdomains.CONSTRUCTION_K7_TERMINAL_RECEIPT_SET_V180R12R2E_DOMAIN,
    )
    document["occurrence_shared_resource_receipt_count"] = 89
    document["total_authoritative_shared_resource_receipt_count"] = 89
    _rejects_mutation(
        monkeypatch,
        groups,
        aggregation_bytes,
        _resign_bundle(document),
    )


def test_v180r12r2_verifier_rejects_campaign_structural_denominator_change(
    monkeypatch: pytest.MonkeyPatch,
    groups: Sequence[verifier._VerifiedGroup],
    aggregation_bytes: bytes,
) -> None:
    document = deepcopy(verifier._object(aggregation_bytes, "baseline"))
    boundary = document["campaign_scope_structural_boundary"]
    boundary["structural_declaration_count"] = 8
    _resign_subdocument(
        boundary,
        "campaign_scope_structural_boundary_id",
        subdomains.CONSTRUCTION_K7_CAMPAIGN_STRUCTURAL_BOUNDARY_V180R12R2E_DOMAIN,
    )
    document["campaign_scope_structural_obligation_count"] = 8
    _rejects_mutation(
        monkeypatch,
        groups,
        aggregation_bytes,
        _resign_bundle(document),
    )


@pytest.mark.parametrize(
    "mutation",
    (
        "observed",
        "counter_eligible",
        "economics_eligible",
        "native_zero",
        "cap_as_peak",
        "unique_bytes_as_actual_reads",
        "literal_zero_as_native_zero",
        "authoritative_total_99",
    ),
)
def test_v180r12r2_independent_structural_replay_rejects_authority_inflation(
    aggregation_bytes: bytes,
    mutation: str,
) -> None:
    aggregate = deepcopy(verifier._object(aggregation_bytes, "baseline"))
    boundary = aggregate["campaign_scope_structural_boundary"]
    rows = {row["path"]: row for row in boundary["structural_declarations"]}
    if mutation == "observed":
        rows["common.hash_invocations"]["actual_measurement_present"] = True
    elif mutation == "counter_eligible":
        rows["common.integrity_checks"]["counter_gate_eligible"] = True
    elif mutation == "economics_eligible":
        rows["common.protocol_checks"]["economics_gate_eligible"] = True
    elif mutation == "native_zero":
        rows["io.staged_bytes"]["quantity_semantics"] = "OBSERVED_NATIVE_ZERO"
        boundary["native_zero_claim_count"] = 1
    elif mutation == "cap_as_peak":
        rows["memory.working_bytes_peak"]["quantity_semantics"] = (
            "OBSERVED_WORKING_BYTES_PEAK"
        )
        rows["memory.working_bytes_peak"]["actual_measurement_present"] = True
        boundary["working_bytes_peak_measurement_present"] = True
    elif mutation == "unique_bytes_as_actual_reads":
        rows["io.read_bytes"]["quantity_semantics"] = "OBSERVED_UNIQUE_READ_BYTES"
        rows["io.read_bytes"]["authority_class"] = "MEASURED_IO_LEDGER"
        rows["io.read_bytes"]["actual_measurement_present"] = True
    elif mutation == "literal_zero_as_native_zero":
        rows["process.launches"]["quantity_semantics"] = "LITERAL_NATIVE_ZERO"
        boundary["native_zero_claim_count"] = 1
    else:
        boundary["campaign_scope_authoritative_receipt_count"] = 9
        boundary["authoritative_receipt_total"] = 99
    _resign_subdocument(
        boundary,
        "campaign_scope_structural_boundary_id",
        subdomains.CONSTRUCTION_K7_CAMPAIGN_STRUCTURAL_BOUNDARY_V180R12R2E_DOMAIN,
    )
    with pytest.raises(
        verifier.ConstructionK7TenTerminalAggregationIndependentVerifierV180R12R2Error,
        match="campaign structural boundary changed",
    ):
        verifier._independently_verify_campaign_scope_structural_boundary_document(
            boundary
        )


def test_v180r12r2_verifier_rejects_synchronized_unknown_field_and_id(
    monkeypatch: pytest.MonkeyPatch,
    groups: Sequence[verifier._VerifiedGroup],
    aggregation_bytes: bytes,
) -> None:
    document = deepcopy(verifier._object(aggregation_bytes, "baseline"))
    component = document["route_component_chain_receipts"][0]
    old_id = component["route_component_chain_receipt_id"]
    component["synchronized_unknown_field"] = True
    new_id = _resign_subdocument(
        component,
        "route_component_chain_receipt_id",
        subdomains.CONSTRUCTION_K7_ROUTE_COMPONENT_CHAIN_RECEIPT_V180R12R2E_DOMAIN,
    )
    terminal = next(
        row
        for row in document["terminal_receipts"]
        if old_id in row["route_component_chain_receipt_ids"]
    )
    terminal["route_component_chain_receipt_ids"] = [
        new_id if value == old_id else value
        for value in terminal["route_component_chain_receipt_ids"]
    ]
    if terminal["representative_route_component_chain_receipt_id"] == old_id:
        terminal["representative_route_component_chain_receipt_id"] = new_id
    _resign_subdocument(
        terminal,
        "terminal_chain_receipt_id",
        subdomains.CONSTRUCTION_K7_TERMINAL_RECEIPT_V180R12R2E_DOMAIN,
    )
    _rejects_mutation(
        monkeypatch,
        groups,
        aggregation_bytes,
        _resign_bundle(document),
    )


def test_v180r12r2_verifier_rejects_retained_source_bytes_mismatch(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    groups: Sequence[verifier._VerifiedGroup],
) -> None:
    for group in groups:
        for relative_path in (group.terminal_path, group.verification_path):
            source = ROOT / relative_path
            target = tmp_path / relative_path
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
    changed = tmp_path / groups[0].verification_path
    changed_document = verifier._object(changed.read_bytes(), "source mutation")
    changed_document["official_execution_allowed"] = True
    changed.write_bytes(canonical_json_bytes(changed_document))
    assert os.stat(changed).st_nlink == 1
    _install_synthetic_contract(monkeypatch, groups, capture_groups=False)
    with pytest.raises(
        verifier.ConstructionK7TenTerminalAggregationIndependentVerifierV180R12R2Error,
        match="retained source bytes or identity changed",
    ):
        verifier.verify_ten_terminal_aggregation_independently_v180r12r2(
            b"{}",
            tmp_path,
        )
