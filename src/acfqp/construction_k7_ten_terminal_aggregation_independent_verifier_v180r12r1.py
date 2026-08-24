"""Producer-free reconstruction of the V180r12r1 ten-terminal aggregate."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Mapping, NoReturn, Sequence

from acfqp import construction_accounting_registry_v9 as registry_v9
from acfqp import construction_k7_cached_exact_infeasibility_production_terminal_independent_verifier_v180r8 as r8_verifier
from acfqp import construction_k7_domain_registry_extension_v180r12r1 as domains
from acfqp import construction_k7_domain_registry_extension_v180r12r1e as subdomains
from acfqp import construction_k7_full_ground_fallback_production_terminal_independent_verifier_v180r7 as r7_verifier
from acfqp import construction_k7_remaining_terminal_execution_authorization_v180r9 as r9_authorization
from acfqp import construction_k7_remaining_terminal_independent_verifier_v180r9 as r9_verifier
from acfqp import construction_k7_ten_terminal_aggregation_execution_authorization_v180r12r1 as authorization
from acfqp import construction_k7_ten_terminal_aggregation_protocol_v180r12r1 as protocol
from acfqp import construction_k7_v34_retained_recovery_authorization_v180r11 as r11_authorization
from acfqp import construction_k7_v34_retained_recovery_independent_verifier_v180r11 as r11_verifier
from acfqp import construction_k7_v36_local_recovery_resource_successor_independent_verifier_v180r10 as r10_verifier
from acfqp.accounting_v1 import (
    ComparisonVectorV1,
    CounterRecordV1,
    LaneEnum,
    NativeZeroAttestationV1,
    RouteKindEnum,
    WorkVectorV1,
)
from acfqp.actual_accounting_v1 import (
    ActualProjectionProofV1,
    ActualWorkScope,
    derive_actual_projection_v1,
    verify_actual_projection_v1,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp.routing_v1 import TerminalCode


MAXIMUM_FIXED_POINT_ITERATIONS = 32
WORKING_BYTES_HARD_CAP = 4 * 1024 * 1024 * 1024
SHARED_RESOURCE_PATHS = (
    "common.hash_invocations",
    "common.integrity_checks",
    "common.protocol_checks",
    "io.mounted_bytes_peak",
    "io.output_bytes",
    "io.read_bytes",
    "io.staged_bytes",
    "memory.working_bytes_peak",
    "process.launches",
)
_PATH_FAMILY = {
    TerminalCode.ABSTRACT_CERTIFIED: "SUCCESS",
    TerminalCode.CACHED_EXACT_INFEASIBLE: "SUCCESS",
    TerminalCode.LOCAL_GROUND_RECOVERY: "FALLBACK",
    TerminalCode.FULL_GROUND_FALLBACK: "FALLBACK",
    TerminalCode.FULL_GROUND_EXACT_INFEASIBLE: "FALLBACK",
    TerminalCode.FALLBACK_CAP_EXHAUSTED: "FALLBACK",
    TerminalCode.REBUILD_REQUIRED: "OOD",
    TerminalCode.INTEGRITY_FAILURE: "FAILURE",
    TerminalCode.PROTOCOL_FAILURE: "FAILURE",
    TerminalCode.ATTEMPT_BUDGET_EXHAUSTED: "FAILURE",
}


class ConstructionK7TenTerminalAggregationIndependentVerifierV180R12R1Error(
    RuntimeError
):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7TenTerminalAggregationIndependentVerifierV180R12R1Error(
        message
    )


def _object(raw: bytes, label: str) -> dict[str, Any]:
    if type(raw) is not bytes:
        _fail(f"{label} is not exact bytes")
    document = loads_canonical_json(raw)
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail(f"{label} is not one canonical object")
    return document


def _read(root: Path, relative_path: str, label: str) -> tuple[bytes, dict[str, Any]]:
    try:
        raw = (root / relative_path).read_bytes()
    except OSError as error:
        raise ConstructionK7TenTerminalAggregationIndependentVerifierV180R12R1Error(
            f"{label} is absent"
        ) from error
    return raw, _object(raw, label)


def _group(
    *,
    source_kind: str,
    terminal_path: str,
    terminal_bytes: bytes,
    terminal: Mapping[str, Any],
    verification_path: str,
    verification_bytes: bytes,
    verification: Mapping[str, Any],
    terminal_id_key: str,
) -> dict[str, Any]:
    return {
        "source_kind": source_kind,
        "terminal_path": terminal_path,
        "terminal_bytes": terminal_bytes,
        "terminal": dict(terminal),
        "verification_path": verification_path,
        "verification_bytes": verification_bytes,
        "verification": dict(verification),
        "terminal_id": terminal[terminal_id_key],
        "verification_id": verification["verification_id"],
    }


def _verified_groups(root: Path) -> tuple[dict[str, Any], ...]:
    result: list[dict[str, Any]] = []
    terminal_path = ".tmp/exact-freeze/v180r11_v34_retained_terminal.json"
    verification_path = ".tmp/exact-freeze/v180r11_v34_retained_verification.json"
    terminal_bytes, terminal = _read(root, terminal_path, "V180r11 terminal")
    verification_bytes, verification = _read(root, verification_path, "V180r11 verification")
    replay = r11_verifier.verify_v34_retained_recovery_bytes_independently_v180r11(
        terminal_bytes,
        root / ".tmp/exact-freeze/v180r5_v34_production_output",
        recovery_authorization_id=r11_authorization.EXPECTED_AUTHORIZATION_ID,
    )
    if canonical_json_bytes(replay) != verification_bytes:
        _fail("V180r11 verification replay changed")
    result.append(
        _group(
            source_kind="V180R11_RETAINED_V34_FINISH_FORWARD",
            terminal_path=terminal_path,
            terminal_bytes=terminal_bytes,
            terminal=terminal,
            verification_path=verification_path,
            verification_bytes=verification_bytes,
            verification=verification,
            terminal_id_key="v34_retained_terminal_id",
        )
    )

    terminal_path = ".tmp/exact-freeze/v180r10_v36_resource_successor_terminal.json"
    verification_path = ".tmp/exact-freeze/v180r10_v36_resource_successor_verification.json"
    terminal_bytes, terminal = _read(root, terminal_path, "V180r10 terminal")
    verification_bytes, verification = _read(root, verification_path, "V180r10 verification")
    replay = r10_verifier.verify_v36_resource_successor_independently_v180r10(
        terminal_bytes,
        root / ".tmp/exact-freeze/v180r10_v36_resource_successor_output",
    )
    if canonical_json_bytes(replay) != verification_bytes:
        _fail("V180r10 verification replay changed")
    result.append(
        _group(
            source_kind="V180R10_FRESH_V36_RESOURCE_SUCCESSOR",
            terminal_path=terminal_path,
            terminal_bytes=terminal_bytes,
            terminal=terminal,
            verification_path=verification_path,
            verification_bytes=verification_bytes,
            verification=verification,
            terminal_id_key="production_terminal_bundle_id",
        )
    )

    terminal_path = ".tmp/exact-freeze/v180r7_full_ground_fallback_terminal_bundle.json"
    verification_path = ".tmp/exact-freeze/v180r7_full_ground_fallback_verification.json"
    terminal_bytes, terminal = _read(root, terminal_path, "V180r7 terminal")
    verification_bytes, verification = _read(root, verification_path, "V180r7 verification")
    replay = r7_verifier.verify_full_ground_fallback_terminal_independently_v180r7(
        terminal_bytes,
        root / ".tmp/exact-freeze/v180r7_full_ground_fallback_output",
    )
    if canonical_json_bytes(replay) != verification_bytes:
        _fail("V180r7 verification replay changed")
    result.append(
        _group(
            source_kind="V180R7_FRESH_FULL_GROUND_FALLBACK",
            terminal_path=terminal_path,
            terminal_bytes=terminal_bytes,
            terminal=terminal,
            verification_path=verification_path,
            verification_bytes=verification_bytes,
            verification=verification,
            terminal_id_key="production_terminal_bundle_id",
        )
    )

    terminal_path = ".tmp/v180r8-cached-exact-production/TERMINAL.json"
    verification_path = ".tmp/v180r8-cached-exact-verification/VERIFICATION.json"
    terminal_bytes, terminal = _read(root, terminal_path, "V180r8 terminal")
    verification_bytes, verification = _read(root, verification_path, "V180r8 verification")
    replay = r8_verifier.verify_cached_exact_terminal_independently_v180r8(
        terminal_bytes
    )
    if canonical_json_bytes(replay) != verification_bytes:
        _fail("V180r8 verification replay changed")
    result.append(
        _group(
            source_kind="V180R8_FRESH_CACHED_EXACT",
            terminal_path=terminal_path,
            terminal_bytes=terminal_bytes,
            terminal=terminal,
            verification_path=verification_path,
            verification_bytes=verification_bytes,
            verification=verification,
            terminal_id_key="production_terminal_bundle_id",
        )
    )

    terminal_path = ".tmp/exact-freeze/v180r9_remaining_terminal_production/TERMINAL.json"
    verification_path = ".tmp/exact-freeze/v180r9_remaining_terminal_production/VERIFICATION.json"
    terminal_bytes, terminal = _read(root, terminal_path, "V180r9 terminal")
    verification_bytes, verification = _read(root, verification_path, "V180r9 verification")
    replay = r9_verifier.verify_remaining_terminal_campaign_independently_v180r9(
        terminal_bytes,
        execution_authorization_id=r9_authorization.EXPECTED_AUTHORIZATION_ID,
        event_manifests=r9_authorization.event_manifests_v180r9(),
    )
    if canonical_json_bytes(replay) != verification_bytes:
        _fail("V180r9 verification replay changed")
    result.append(
        _group(
            source_kind="V180R9_FRESH_SIX_TERMINAL_CAMPAIGN",
            terminal_path=terminal_path,
            terminal_bytes=terminal_bytes,
            terminal=terminal,
            verification_path=verification_path,
            verification_bytes=verification_bytes,
            verification=verification,
            terminal_id_key="production_campaign_bundle_id",
        )
    )
    return tuple(result)


def _source_receipt(group: Mapping[str, Any]) -> dict[str, Any]:
    payload = {
        "schema": "acfqp.ten_terminal_source_verification_receipt.v180r12r1",
        "aggregation_protocol_id": protocol.EXPECTED_PROTOCOL_ID,
        "source_kind": group["source_kind"],
        "terminal_relative_path": group["terminal_path"],
        "terminal_content_id": group["terminal_id"],
        "terminal_byte_count": len(group["terminal_bytes"]),
        "terminal_sha256": hashlib.sha256(group["terminal_bytes"]).hexdigest(),
        "verification_relative_path": group["verification_path"],
        "verification_id": group["verification_id"],
        "verification_byte_count": len(group["verification_bytes"]),
        "verification_sha256": hashlib.sha256(
            group["verification_bytes"]
        ).hexdigest(),
        "independent_verifier_replayed_before_aggregation": True,
        "verification_bytes_equal_replay": True,
    }
    return {
        **payload,
        "source_receipt_id": subdomains.extension_content_id_v180r12r1e(
            subdomains.CONSTRUCTION_K7_SOURCE_RECEIPT_V180R12R1E_DOMAIN,
            payload,
        ),
    }


def _chain(
    vector_document: Mapping[str, Any],
    comparison_document: Mapping[str, Any],
    proof_document: Mapping[str, Any],
    zero_document: Mapping[str, Any],
) -> WorkVectorV1:
    registry = registry_v9.official_counter_registry_v9()
    comparison_profile = registry_v9.official_comparison_profile_v9(registry)
    actual_profile = registry_v9.official_actual_projection_profile_v9(
        registry, comparison_profile
    )
    try:
        vector = WorkVectorV1.from_dict(vector_document, registry)
        comparison = ComparisonVectorV1.from_dict(comparison_document)
        proof = ActualProjectionProofV1.from_dict(proof_document)
        zero = NativeZeroAttestationV1.from_dict(zero_document)
        recomputed = verify_actual_projection_v1(
            proof,
            vector,
            comparison,
            registry,
            comparison_profile,
            actual_profile,
        )
    except Exception as error:
        raise ConstructionK7TenTerminalAggregationIndependentVerifierV180R12R1Error(
            "terminal chain replay failed"
        ) from error
    if not (
        len(vector.records) == 269
        and recomputed == comparison
        and zero == NativeZeroAttestationV1.derive(vector, registry)
    ):
        _fail("terminal chain identity changed")
    return vector


def _terminal_receipt(
    *,
    code: TerminalCode,
    source_receipt_id: str,
    group: Mapping[str, Any],
    terminal_bytes: bytes,
    terminal_id: str,
    vector_document: Mapping[str, Any],
    comparison_document: Mapping[str, Any],
    proof_document: Mapping[str, Any],
    zero_document: Mapping[str, Any],
    supporting_ids: Sequence[str],
    shared_count: int,
) -> dict[str, Any]:
    vector = _chain(
        vector_document,
        comparison_document,
        proof_document,
        zero_document,
    )
    if shared_count != 9:
        _fail("terminal shared-resource denominator changed")
    payload = {
        "schema": "acfqp.ten_terminal_chain_receipt.v180r12r1",
        "aggregation_protocol_id": protocol.EXPECTED_PROTOCOL_ID,
        "terminal_code": code.value,
        "path_family": _PATH_FAMILY[code],
        "source_receipt_id": source_receipt_id,
        "source_verification_id": group["verification_id"],
        "source_terminal_bundle_id": terminal_id,
        "source_terminal_byte_count": len(terminal_bytes),
        "source_terminal_sha256": hashlib.sha256(terminal_bytes).hexdigest(),
        "work_vector_id": vector.work_vector_id,
        "comparison_vector_id": comparison_document["comparison_vector_id"],
        "actual_projection_proof_id": proof_document["actual_projection_proof_id"],
        "native_zero_attestation_id": zero_document["native_zero_attestation_id"],
        "counter_record_count": len(vector.records),
        "supporting_work_vector_ids": list(supporting_ids),
        "shared_resource_receipt_count": shared_count,
        "counter_record_to_work_vector_to_comparison_vector_replayed": True,
        "source_output_fixed_point_replayed": True,
        "historical_summary_translation_used": False,
        "fresh_v180_observed_occurrence_present": True,
    }
    return {
        **payload,
        "terminal_chain_receipt_id": subdomains.extension_content_id_v180r12r1e(
            subdomains.CONSTRUCTION_K7_TERMINAL_RECEIPT_V180R12R1E_DOMAIN,
            payload,
        ),
    }


def _receipts(
    groups: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    source_receipts: list[dict[str, Any]] = []
    terminals: dict[str, dict[str, Any]] = {}
    for group in groups:
        source = _source_receipt(group)
        source_receipts.append(source)
        document = group["terminal"]
        if group["source_kind"] == "V180R9_FRESH_SIX_TERMINAL_CAMPAIGN":
            for row in document["terminal_rows"]:
                code = TerminalCode(row["terminal_code"])
                bundle = row["bundle"]
                raw = canonical_json_bytes(bundle)
                terminals[code.value] = _terminal_receipt(
                    code=code,
                    source_receipt_id=source["source_receipt_id"],
                    group=group,
                    terminal_bytes=raw,
                    terminal_id=row["production_terminal_bundle_id"],
                    vector_document=bundle["terminal_work_vector"],
                    comparison_document=bundle["terminal_comparison_vector"],
                    proof_document=bundle["terminal_actual_projection_proof"],
                    zero_document=bundle["terminal_native_zero_attestation"],
                    supporting_ids=[bundle["terminal_work_vector"]["work_vector_id"]],
                    shared_count=bundle["shared_resource_receipt_set"]["receipt_count"],
                )
            continue
        code = TerminalCode(document["terminal_code"])
        if code is TerminalCode.FULL_GROUND_FALLBACK:
            components = document["v9_lifted_route_components"]
            direct = next(
                row
                for row in components
                if row["v9_work_vector"]["route_kind"] == "DIRECT_FALLBACK"
            )
            vector_document = direct["v9_work_vector"]
            comparison_document = direct["v9_comparison_vector"]
            proof_document = direct["v9_actual_projection_proof"]
            zero_document = direct["v9_native_zero_attestation"]
            supporting = [row["v9_work_vector"]["work_vector_id"] for row in components]
            shared_count = document["source_occurrence_accounting_bundle"][
                "shared_resource_path_count"
            ]
        else:
            vector_document = document["terminal_work_vector"]
            comparison_document = document["terminal_comparison_vector"]
            proof_document = document["terminal_actual_projection_proof"]
            zero_document = document["terminal_native_zero_attestation"]
            supporting = [vector_document["work_vector_id"]]
            if code is TerminalCode.CACHED_EXACT_INFEASIBLE:
                shared_count = document["shared_resource_receipt_set"]["receipt_count"]
            else:
                if document["source_independent_verification"].get(
                    "all_nine_shared_resource_receipts_replayed"
                ) is not True:
                    _fail("source shared-resource verification changed")
                shared_count = 9
        terminals[code.value] = _terminal_receipt(
            code=code,
            source_receipt_id=source["source_receipt_id"],
            group=group,
            terminal_bytes=group["terminal_bytes"],
            terminal_id=group["terminal_id"],
            vector_document=vector_document,
            comparison_document=comparison_document,
            proof_document=proof_document,
            zero_document=zero_document,
            supporting_ids=supporting,
            shared_count=shared_count,
        )
    if len(terminals) != len(TerminalCode):
        _fail("terminal receipt denominator changed")
    return source_receipts, [terminals[code.value] for code in TerminalCode]


def _shared_receipt_set(
    subject_id: str,
    source_ids: Sequence[str],
    values: Mapping[str, int],
) -> dict[str, Any]:
    registry = registry_v9.official_counter_registry_v9()
    receipts = []
    for path in SHARED_RESOURCE_PATHS:
        source_kind = (
            "OUTPUT_FIXED_POINT"
            if path == "io.output_bytes"
            else "OS_ENFORCED_FROZEN_HARD_CAP"
            if path == "memory.working_bytes_peak"
            else "COMPLETE_WINDOW_NATIVE_ZERO"
            if values[path] == 0
            else "EXACT_SOURCE_REPLAY_LEDGER"
        )
        payload = {
            "schema": "acfqp.ten_terminal_shared_resource_receipt.v180r12r1",
            "aggregation_protocol_id": protocol.EXPECTED_PROTOCOL_ID,
            "execution_authorization_id": authorization.EXPECTED_AUTHORIZATION_ID,
            "subject_id": subject_id,
            "source_receipt_ids": list(source_ids),
            "path": path,
            "reducer": registry.by_path[path].reducer.value,
            "value": values[path],
            "source_kind": source_kind,
            "window_start_sequence": 1,
            "window_cutoff_sequence": 9,
            "complete_through_aggregation_cutoff": True,
            "native_zero_observed": values[path] == 0,
            "accounting_provenance_hashes_excluded": True,
        }
        receipts.append(
            {
                **payload,
                "receipt_id": subdomains.extension_content_id_v180r12r1e(
                    subdomains.CONSTRUCTION_K7_SHARED_RECEIPT_V180R12R1E_DOMAIN,
                    payload,
                ),
            }
        )
    payload = {
        "schema": "acfqp.ten_terminal_shared_resource_receipt_set.v180r12r1",
        "aggregation_protocol_id": protocol.EXPECTED_PROTOCOL_ID,
        "execution_authorization_id": authorization.EXPECTED_AUTHORIZATION_ID,
        "subject_id": subject_id,
        "source_receipt_ids": list(source_ids),
        "ordered_paths": list(SHARED_RESOURCE_PATHS),
        "receipts": receipts,
        "receipt_count": len(receipts),
        "all_nine_paths_complete_through_aggregation_cutoff": True,
        "missing_path_inferred_zero": False,
    }
    return {
        **payload,
        "shared_resource_receipt_set_id": subdomains.extension_content_id_v180r12r1e(
            subdomains.CONSTRUCTION_K7_RECEIPT_SET_V180R12R1E_DOMAIN,
            payload,
        ),
    }


def _orchestration_chain(
    subject_id: str,
    values: Mapping[str, int],
    recorder_id: str,
) -> tuple[Any, Any, Any, NativeZeroAttestationV1]:
    registry = registry_v9.official_counter_registry_v9()
    records = tuple(
        CounterRecordV1.observe(
            registry, path, values[path], recorder_id=recorder_id
        )
        for path in sorted(values)
    )
    vector = WorkVectorV1(
        registry.registry_id,
        subject_id,
        RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE,
        records,
    )
    comparison_profile = registry_v9.official_comparison_profile_v9(registry)
    actual_profile = registry_v9.official_actual_projection_profile_v9(
        registry, comparison_profile
    )
    comparison, proof = derive_actual_projection_v1(
        vector,
        registry,
        comparison_profile,
        actual_profile,
        source_lane=LaneEnum.OPERATIONAL,
        work_scope=ActualWorkScope.COMMON_PREFIX,
    )
    return vector, comparison, proof, NativeZeroAttestationV1.derive(vector, registry)


def _reconstruct(root: Path) -> bytes:
    groups = _verified_groups(root)
    source_receipts, terminal_receipts = _receipts(groups)
    source_ids = [row["source_receipt_id"] for row in source_receipts]
    subject_id = hashlib.sha256(
        b"acfqp:v180r12r1:ten-terminal-aggregation\x00"
        + authorization.EXPECTED_AUTHORIZATION_ID.encode("ascii")
        + b"\x00"
        + canonical_json_bytes(
            [row["terminal_chain_receipt_id"] for row in terminal_receipts]
        )
    ).hexdigest()
    base_values = {
        path: 0 for path in registry_v9.official_counter_registry_v9().by_path
    }
    base_values.update(
        {
            "common.hash_invocations": 15,
            "common.integrity_checks": 10,
            "common.protocol_checks": 10,
            "io.mounted_bytes_peak": 0,
            "io.read_bytes": sum(
                len(group["terminal_bytes"]) + len(group["verification_bytes"])
                for group in groups
            ),
            "io.staged_bytes": 0,
            "memory.working_bytes_peak": WORKING_BYTES_HARD_CAP,
            "process.launches": 0,
            "route.attempts": 1,
            "route.successes": 1,
        }
    )
    guess = 0
    for iteration in range(MAXIMUM_FIXED_POINT_ITERATIONS):
        values = dict(base_values)
        values["io.output_bytes"] = guess
        receipt_set = _shared_receipt_set(subject_id, source_ids, values)
        vector, comparison, proof, zero = _orchestration_chain(
            subject_id,
            values,
            receipt_set["shared_resource_receipt_set_id"],
        )
        payload = {
            "schema": "acfqp.ten_terminal_production_aggregation.v180r12r1",
            "aggregation_protocol_id": protocol.EXPECTED_PROTOCOL_ID,
            "execution_authorization_id": authorization.EXPECTED_AUTHORIZATION_ID,
            "ordered_terminal_codes": [code.value for code in TerminalCode],
            "terminal_code_count": len(TerminalCode),
            "source_group_count": len(source_receipts),
            "source_verification_receipts": source_receipts,
            "terminal_chain_receipts": terminal_receipts,
            "terminal_counter_record_count": sum(
                row["counter_record_count"] for row in terminal_receipts
            ),
            "terminal_shared_resource_receipt_count": sum(
                row["shared_resource_receipt_count"] for row in terminal_receipts
            ),
            "campaign_orchestration_shared_resource_receipt_set": receipt_set,
            "campaign_orchestration_work_vector": vector.to_dict(),
            "campaign_orchestration_comparison_vector": comparison.to_dict(),
            "campaign_orchestration_actual_projection_proof": proof.to_dict(),
            "campaign_orchestration_native_zero_attestation": zero.to_dict(),
            "output_bytes_fixed_point": guess,
            "fixed_point_iteration": iteration,
            "fresh_v180_observed_occurrence_count": len(TerminalCode),
            "success_fallback_ood_failure_coverage_complete": True,
            "all_source_independent_verifiers_replayed": True,
            "all_ten_counter_record_work_vector_comparison_vector_chains_present": True,
            "all_ten_nine_path_receipt_sets_present": True,
            "campaign_orchestration_v9_chain_present": True,
            "historical_summary_translation_used": False,
            "development_fixture_only": False,
            "all_ten_paths_verified_by_producer": True,
            "all_ten_paths_independently_verified": False,
            "COUNTER_COMPLETENESS_GATE": "PENDING_INDEPENDENT_REPLAY",
            "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "official_execution_allowed": False,
        }
        document = {
            **payload,
            "production_aggregation_bundle_id": domains.extension_content_id_v180r12r1(
                domains.CONSTRUCTION_K7_TERMINAL_BUNDLE_V180R12R1_DOMAIN,
                payload,
            ),
        }
        raw = canonical_json_bytes(document)
        if len(raw) == guess:
            return raw
        guess = len(raw)
    _fail("producer-free aggregate fixed point did not converge")


def verify_ten_terminal_aggregation_independently_v180r12r1(
    aggregation_bytes: bytes,
    repository_root: Path,
) -> dict[str, Any]:
    if not isinstance(repository_root, Path) or not repository_root.is_dir():
        _fail("repository root is absent")
    authorization_document = (
        authorization.freeze_ten_terminal_aggregation_execution_authorization_v180r12r1().to_document()
    )
    root = Path(__file__).resolve().parents[2]
    for fact in authorization_document["source_facts"]:
        raw = (root / fact["relative_path"]).read_bytes()
        if fact != {
            "relative_path": fact["relative_path"],
            "byte_count": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
        }:
            _fail("authorized aggregation source changed")
    expected = _reconstruct(repository_root)
    if expected != aggregation_bytes:
        _fail("ten-terminal aggregate did not reproduce without producer import")
    document = _object(aggregation_bytes, "V180r12r1 aggregation")
    if not (
        document["terminal_code_count"] == 10
        and document["source_group_count"] == 5
        and document["terminal_counter_record_count"] == 2_690
        and document["terminal_shared_resource_receipt_count"] == 90
        and document["output_bytes_fixed_point"] == len(aggregation_bytes)
        and document["fresh_v180_observed_occurrence_count"] == 10
        and document["success_fallback_ood_failure_coverage_complete"] is True
        and document["all_source_independent_verifiers_replayed"] is True
        and document[
            "all_ten_counter_record_work_vector_comparison_vector_chains_present"
        ]
        is True
        and document["all_ten_nine_path_receipt_sets_present"] is True
        and document["campaign_orchestration_v9_chain_present"] is True
        and document["historical_summary_translation_used"] is False
        and document["development_fixture_only"] is False
        and document["all_ten_paths_verified_by_producer"] is True
        and document["all_ten_paths_independently_verified"] is False
        and document["COUNTER_COMPLETENESS_GATE"] == "PENDING_INDEPENDENT_REPLAY"
        and document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
        and document["official_execution_allowed"] is False
    ):
        _fail("aggregate coverage or claim lock changed")
    payload = {
        "schema": "acfqp.ten_terminal_aggregation_verification.v180r12r1",
        "aggregation_protocol_id": protocol.EXPECTED_PROTOCOL_ID,
        "execution_authorization_id": authorization.EXPECTED_AUTHORIZATION_ID,
        "production_aggregation_bundle_id": document[
            "production_aggregation_bundle_id"
        ],
        "aggregation_byte_count": len(aggregation_bytes),
        "aggregation_sha256": hashlib.sha256(aggregation_bytes).hexdigest(),
        "source_group_count": 5,
        "terminal_code_count": 10,
        "terminal_counter_record_count": 2_690,
        "terminal_shared_resource_receipt_count": 90,
        "all_source_independent_verifiers_replayed": True,
        "all_terminal_counter_records_replayed": True,
        "all_terminal_work_vectors_replayed": True,
        "all_terminal_comparison_vectors_rederived": True,
        "all_terminal_actual_projection_proofs_replayed": True,
        "all_terminal_output_fixed_points_replayed": True,
        "campaign_orchestration_work_vector_replayed": True,
        "producer_module_imported": False,
        "historical_summary_translation_used": False,
        "all_ten_paths_verified": True,
        "COUNTER_COMPLETENESS_GATE": "PASS",
        "WORKLOAD_ECONOMICS_GATE": "READY_NOT_RUN",
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "official_execution_allowed": False,
    }
    return {
        **payload,
        "verification_id": domains.extension_content_id_v180r12r1(
            domains.CONSTRUCTION_K7_VERIFICATION_V180R12R1_DOMAIN,
            payload,
        ),
    }


__all__ = (
    "ConstructionK7TenTerminalAggregationIndependentVerifierV180R12R1Error",
    "verify_ten_terminal_aggregation_independently_v180r12r1",
)
