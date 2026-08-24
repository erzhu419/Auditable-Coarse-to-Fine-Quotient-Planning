"""Producer-free replay of the V180r8 cached exact-infeasibility terminal."""

from __future__ import annotations

import hashlib
from pathlib import Path
import threading
from typing import Any, Mapping, NoReturn

from acfqp import construction_accounting_registry_v9 as registry_v9
from acfqp import construction_k7_all_path_cached_execution_authorization_v180r8 as authorization
from acfqp import construction_k7_all_path_formalization_contract_v180 as contract
from acfqp import construction_k7_all_path_production_execution_protocol_v180r3 as protocol
from acfqp import construction_k7_domain_registry_extension_v180r8 as domains
from acfqp import phase3e_exact_infeasibility_durable_proof_v1 as durable
from acfqp.accounting_v1 import (
    CounterRecordV1,
    LaneEnum,
    NativeZeroAttestationV1,
    RouteKindEnum,
    WorkVectorV1,
)
from acfqp.actual_accounting_v1 import ActualWorkScope, derive_actual_projection_v1
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


EXPECTED_TERMINAL_BUNDLE_ID = (
    "4a90d809119b470ee6feefcd7d6332bb0c9144612bf32fad72f608e99a08dae6"
)
EXPECTED_TERMINAL_BYTE_COUNT = 335_305
EXPECTED_TERMINAL_SHA256 = (
    "3b39bec8f60c0f7115c35e898b06e82d87ef2efa386c2f39906b20124fee1052"
)
EXPECTED_VERIFICATION_ID = (
    "6d3aaefb90bc2c341c3a14a2d38bfc1345f7335d99fb94726df9821132a9f37f"
)
EXPECTED_VERIFICATION_BYTE_COUNT = 1_406
EXPECTED_VERIFICATION_SHA256 = (
    "35715f6f295459157ddd30ef3f48a809ba31e9470e39fd0a6bf12fa77b9da0b8"
)

MAXIMUM_FIXED_POINT_ITERATIONS = 32
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
_INTEGRITY_OBLIGATIONS = (
    "durable-proof-source-is-canonical-and-pinned",
    "durable-proof-independent-semantic-replay-succeeded",
    "durable-proof-identity-is-an-exact-match",
    "durable-proof-verification-content-id-replayed",
    "cache-consumption-content-id-replayed",
    "cache-consumption-binds-the-preregistered-plan",
    "v9-registry-and-projection-profiles-replayed",
    "nine-shared-resource-rows-cover-the-complete-window",
)
_PROTOCOL_OBLIGATIONS = (
    "registered-cached-terminal-slot-selected",
    "source-proof-produced-before-online-window",
    "online-window-does-not-call-proof-producer",
    "online-window-does-not-call-planner-or-ground-solver",
    "independent-match-precedes-plan-consumption",
    "single-cache-lookup-precedes-single-successful-terminal",
    "no-process-launch-or-staging-occurs-in-online-window",
    "output-byte-accounting-closes-at-one-exact-fixed-point",
)
_SOURCE_KIND = {
    "common.hash_invocations": "SOURCE_CLOSED_BUSINESS_HASH_METER",
    "common.integrity_checks": "NAMED_INTEGRITY_OBLIGATION_LEDGER",
    "common.protocol_checks": "NAMED_PROTOCOL_OBLIGATION_LEDGER",
    "io.mounted_bytes_peak": "SINGLE_FILE_MOUNT_MANIFEST",
    "io.output_bytes": "OUTPUT_FIXED_POINT",
    "io.read_bytes": "EXACT_PROOF_FILE_READ",
    "io.staged_bytes": "COMPLETE_WINDOW_NATIVE_ZERO",
    "memory.working_bytes_peak": "OS_ENFORCED_FROZEN_HARD_CAP",
    "process.launches": "COMPLETE_WINDOW_NATIVE_ZERO",
}
_BUSINESS_REPLAY_LOCK = threading.Lock()


class ConstructionK7CachedExactIndependentVerifierV180r8Error(RuntimeError):
    """The authorization, proof, accounting chain, or fixed point changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7CachedExactIndependentVerifierV180r8Error(message)


def _object(raw: bytes, label: str) -> dict[str, Any]:
    if type(raw) is not bytes:
        _fail(f"{label} is not exact bytes")
    try:
        document = loads_canonical_json(raw)
    except Exception as error:
        raise ConstructionK7CachedExactIndependentVerifierV180r8Error(
            f"{label} is not canonical JSON"
        ) from error
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail(f"{label} is not one canonical object")
    return document


def _authorization() -> tuple[dict[str, Any], dict[str, Any]]:
    frozen = authorization.freeze_cached_execution_authorization_v180r8()
    document = frozen.to_document()
    root = Path(__file__).resolve().parents[2]
    for key in ("source_facts", "proof_source_facts"):
        facts = document[key]
        if type(facts) is not list or not facts:
            _fail(f"V180r8 {key} is not a nonempty exact inventory")
        expected_paths = []
        for fact in facts:
            if type(fact) is not dict or set(fact) != {
                "relative_path",
                "byte_count",
                "sha256",
            }:
                _fail(f"V180r8 {key} row changed")
            raw = (root / fact["relative_path"]).read_bytes()
            expected = {
                "relative_path": fact["relative_path"],
                "byte_count": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
            if fact != expected:
                _fail(f"V180r8 {key} source bytes changed")
            expected_paths.append(fact["relative_path"])
        if expected_paths != sorted(expected_paths) and key == "proof_source_facts":
            _fail("V180r8 proof source inventory order changed")
        if len(expected_paths) != len(set(expected_paths)):
            _fail(f"V180r8 {key} contains duplicate paths")
    slots = [
        row
        for row in protocol.freeze_all_path_production_execution_protocol_v180r3()
        .to_document()["production_execution_slots"]
        if row["terminal_code"] == "CACHED_EXACT_INFEASIBLE"
    ]
    if not (
        len(slots) == 1
        and document["production_execution_slot"] == slots[0]
        and document["logical_occurrence_id"] == authorization.LOGICAL_OCCURRENCE_ID
        and document["selected_plan_id"] == authorization.SELECTED_PLAN_ID
        and document["query_ordinal"] == authorization.QUERY_ORDINAL
        and document["working_bytes_hard_cap"]
        == authorization.WORKING_BYTES_HARD_CAP
        and document["expected_durable_proof_byte_count"]
        == authorization.EXPECTED_DURABLE_PROOF_BYTE_COUNT
        and document["expected_durable_proof_sha256"]
        == authorization.EXPECTED_DURABLE_PROOF_SHA256
        and document["expected_durable_proof_id"]
        == authorization.EXPECTED_DURABLE_PROOF_ID
        and document["fresh_cached_execution_started"] is False
        and document["production_outcome_accessed"] is False
        and document["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
        and document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
        and document["official_scalar_cost"] is None
        and document["official_N_break_even"] is None
        and document["official_execution_allowed"] is False
    ):
        _fail("V180r8 authorization or slot semantics changed")
    return document, slots[0]


def _business_replay(proof_bytes: bytes) -> tuple[dict[str, Any], dict[str, Any], int]:
    with _BUSINESS_REPLAY_LOCK:
        original_id = durable._id  # noqa: SLF001 - independent meter replay
        original_sha = durable._sha256_bytes  # noqa: SLF001
        count = 0

        def counted_id(domain: str, payload: Any) -> str:
            nonlocal count
            count += 1
            return original_id(domain, payload)

        def counted_sha(payload: bytes) -> str:
            nonlocal count
            count += 1
            return original_sha(payload)

        durable._id = counted_id  # type: ignore[assignment]  # noqa: SLF001
        durable._sha256_bytes = counted_sha  # type: ignore[assignment]  # noqa: SLF001
        try:
            verified = durable.verify_phase3e_exact_infeasibility_durable_proof_bytes_v1(
                proof_bytes
            )
            verification = verified.result.to_dict()
            consumption = durable.bind_verified_durable_exact_infeasibility_to_plan_v1(
                verified,
                selected_plan_id=authorization.SELECTED_PLAN_ID,
            ).to_dict()
        finally:
            durable._id = original_id  # type: ignore[assignment]  # noqa: SLF001
            durable._sha256_bytes = original_sha  # type: ignore[assignment]  # noqa: SLF001
    if not (
        count > 0
        and verification["outcome"] == "IDENTICAL_MATCH"
        and verification["durable_proof_id"]
        == authorization.EXPECTED_DURABLE_PROOF_ID
        and verification["submitted_bytes_sha256"]
        == authorization.EXPECTED_DURABLE_PROOF_SHA256
        and consumption["outcome"] == "IDENTICAL_MATCH"
        and consumption["selected_plan_id"] == authorization.SELECTED_PLAN_ID
        and consumption["durable_proof_id"]
        == authorization.EXPECTED_DURABLE_PROOF_ID
        and consumption["verification_id"] == verification["verification_id"]
    ):
        _fail("V180r8 durable proof or fresh plan binding did not replay")
    return verification, consumption, count


def _id(role: str, payload: Mapping[str, Any]) -> str:
    return domains.extension_content_id_v180r8(
        domains.CONSTRUCTION_K7_CACHED_SOURCE_RECEIPT_V180R8_DOMAIN,
        {"role": role, "payload": dict(payload)},
    )


def _source_receipt(
    proof_bytes: bytes, proof_document: Mapping[str, Any], proof_sha256: str
) -> dict[str, Any]:
    payload = {
        "schema": "acfqp.cached_exact_infeasibility_source_receipt.v180r8",
        "logical_occurrence_id": authorization.LOGICAL_OCCURRENCE_ID,
        "source_role": "DURABLE_EXACT_PROOF_PAYLOAD",
        "durable_exact_infeasibility_proof_id": proof_document[
            "durable_exact_infeasibility_proof_id"
        ],
        "canonical_byte_count": len(proof_bytes),
        "canonical_sha256": proof_sha256,
        "proof_produced_before_online_measurement_window": True,
        "proof_source_is_the_frozen_phase05_g2048_bundle": True,
        "historical_summary_to_counter_translation_used": False,
    }
    return {
        **payload,
        "cached_source_receipt_id": domains.extension_content_id_v180r8(
            domains.CONSTRUCTION_K7_CACHED_SOURCE_RECEIPT_V180R8_DOMAIN,
            payload,
        ),
    }


def _receipt_set(
    slot: Mapping[str, Any], source_receipt: Mapping[str, Any], values: Mapping[str, int]
) -> dict[str, Any]:
    registry = registry_v9.official_counter_registry_v9()
    rows = []
    for path in SHARED_RESOURCE_PATHS:
        leaf = registry.by_path[path]
        row_payload = {
            "schema": "acfqp.cached_exact_shared_resource_receipt.v180r8",
            "logical_occurrence_id": authorization.LOGICAL_OCCURRENCE_ID,
            "production_execution_slot_id": slot["production_execution_slot_id"],
            "path": path,
            "reducer": leaf.reducer.value,
            "value": values[path],
            "source_kind": _SOURCE_KIND[path],
            "source_receipt_id": source_receipt["cached_source_receipt_id"],
            "window_start_sequence": 1,
            "window_cutoff_sequence": 9,
            "complete_through_terminal_cutoff": True,
            "native_zero_observed": values[path] == 0,
            "accounting_provenance_hashes_excluded": True,
        }
        rows.append(
            {**row_payload, "receipt_id": _id(f"SHARED_RESOURCE:{path}", row_payload)}
        )
    payload = {
        "schema": "acfqp.cached_exact_shared_resource_receipt_set.v180r8",
        "logical_occurrence_id": authorization.LOGICAL_OCCURRENCE_ID,
        "production_execution_slot_id": slot["production_execution_slot_id"],
        "selected_plan_id": authorization.SELECTED_PLAN_ID,
        "ordered_paths": list(SHARED_RESOURCE_PATHS),
        "receipts": rows,
        "receipt_count": len(rows),
        "all_nine_paths_complete_through_terminal_cutoff": True,
        "missing_path_inferred_zero": False,
    }
    return {
        **payload,
        "shared_resource_receipt_set_id": domains.extension_content_id_v180r8(
            domains.CONSTRUCTION_K7_CACHED_SHARED_RESOURCE_RECEIPT_SET_V180R8_DOMAIN,
            payload,
        ),
    }


def _work_chain(
    values: Mapping[str, int], receipt_set_id: str
) -> tuple[WorkVectorV1, Any, Any, NativeZeroAttestationV1]:
    registry = registry_v9.official_counter_registry_v9()
    if set(values) != set(registry.by_path):
        _fail("V180r8 independent replay did not cover every V9 leaf")
    vector = WorkVectorV1(
        registry.registry_id,
        authorization.LOGICAL_OCCURRENCE_ID,
        RouteKindEnum.ABSTRACT_FAILED_PREFIX,
        tuple(
            CounterRecordV1.observe(
                registry, path, values[path], recorder_id=receipt_set_id
            )
            for path in sorted(registry.by_path)
        ),
    )
    comparison_profile = registry_v9.official_comparison_profile_v9(registry)
    actual_profile = registry_v9.official_actual_projection_profile_v9(
        registry, comparison_profile
    )
    comparison, projection = derive_actual_projection_v1(
        vector,
        registry,
        comparison_profile,
        actual_profile,
        source_lane=LaneEnum.OPERATIONAL,
        work_scope=ActualWorkScope.COMMON_PREFIX,
    )
    return (
        vector,
        comparison,
        projection,
        NativeZeroAttestationV1.derive(vector, registry),
    )


def _replay_terminal(
    *,
    slot: Mapping[str, Any],
    proof_bytes: bytes,
    proof_document: Mapping[str, Any],
    verification: Mapping[str, Any],
    consumption: Mapping[str, Any],
    hash_count: int,
    observed_peak: int,
) -> bytes:
    proof_sha = hashlib.sha256(proof_bytes).hexdigest()
    source_receipt = _source_receipt(proof_bytes, proof_document, proof_sha)
    registry = registry_v9.official_counter_registry_v9()
    base_values = {path: 0 for path in registry.by_path}
    base_values.update(
        {
            "common.abstract_subproof_cache_lookups": 1,
            "common.hash_invocations": 1 + hash_count,
            "common.integrity_checks": len(_INTEGRITY_OBLIGATIONS),
            "common.protocol_checks": len(_PROTOCOL_OBLIGATIONS),
            "io.mounted_bytes_peak": len(proof_bytes),
            "io.read_bytes": len(proof_bytes),
            "io.staged_bytes": 0,
            "memory.working_bytes_peak": authorization.WORKING_BYTES_HARD_CAP,
            "process.launches": 0,
            "route.attempts": 1,
            "route.successes": 1,
            "route.failures": 0,
        }
    )
    guess = 0
    for iteration in range(MAXIMUM_FIXED_POINT_ITERATIONS):
        values = dict(base_values)
        values["io.output_bytes"] = guess
        receipts = _receipt_set(slot, source_receipt, values)
        vector, comparison, projection, zero = _work_chain(
            values, receipts["shared_resource_receipt_set_id"]
        )
        classification_payload = {
            "schema": "acfqp.cached_exact_terminal_classification.v180r8",
            "logical_occurrence_id": authorization.LOGICAL_OCCURRENCE_ID,
            "terminal_class": "INFEASIBILITY_CERTIFICATE",
            "terminal_code": "CACHED_EXACT_INFEASIBLE",
            "durable_exact_infeasibility_proof_id": proof_document[
                "durable_exact_infeasibility_proof_id"
            ],
            "durable_verification_id": verification["verification_id"],
            "cache_consumption_id": consumption["cache_consumption_id"],
            "work_vector_id": vector.work_vector_id,
            "actual_projection_proof_id": projection.actual_projection_proof_id,
            "shared_resource_receipt_set_id": receipts[
                "shared_resource_receipt_set_id"
            ],
            "outcome": "IDENTICAL_MATCH",
        }
        classification = {
            **classification_payload,
            "terminal_classification_id": _id(
                "TERMINAL_CLASSIFICATION", classification_payload
            ),
        }
        payload = {
            "schema": "acfqp.cached_exact_infeasibility_production_terminal.v180r8",
            "formalization_contract_id": contract.EXPECTED_CONTRACT_ID,
            "production_execution_protocol_id": protocol.EXPECTED_PROTOCOL_ID,
            "production_execution_slot": dict(slot),
            "logical_occurrence_id": authorization.LOGICAL_OCCURRENCE_ID,
            "selected_plan_id": authorization.SELECTED_PLAN_ID,
            "terminal_code": "CACHED_EXACT_INFEASIBLE",
            "terminal_class": "INFEASIBILITY_CERTIFICATE",
            "source_receipt": source_receipt,
            "durable_proof_bytes_hex": proof_bytes.hex(),
            "durable_proof_document": dict(proof_document),
            "durable_independent_verification": dict(verification),
            "durable_cache_consumption": dict(consumption),
            "terminal_classification": classification,
            "shared_resource_receipt_set": receipts,
            "terminal_work_vector": vector.to_dict(),
            "terminal_comparison_vector": comparison.to_dict(),
            "terminal_actual_projection_proof": projection.to_dict(),
            "terminal_native_zero_attestation": zero.to_dict(),
            "integrity_obligations": list(_INTEGRITY_OBLIGATIONS),
            "protocol_obligations": list(_PROTOCOL_OBLIGATIONS),
            "working_bytes_hard_cap": authorization.WORKING_BYTES_HARD_CAP,
            "observed_peak_working_bytes_diagnostic": observed_peak,
            "finalizer_output_bytes": guess,
            "output_bytes_fixed_point": guess,
            "fixed_point_iteration": iteration,
            "fresh_v180r8_observed_occurrence_present": True,
            "durable_exact_proof_payload_present": True,
            "exact_cached_infeasibility_identical_match_present": True,
            "ground_solver_called_in_online_window": False,
            "planner_called_in_online_window": False,
            "proof_producer_called_in_online_window": False,
            "historical_summary_translation_used": False,
            "development_fixture_only": False,
            "partial_campaign_cannot_unlock_any_gate": True,
            "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
            "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "official_execution_allowed": False,
        }
        document = {
            **payload,
            "production_terminal_bundle_id": domains.extension_content_id_v180r8(
                domains.CONSTRUCTION_K7_CACHED_EXECUTION_TERMINAL_V180R8_DOMAIN,
                payload,
            ),
        }
        raw = canonical_json_bytes(document)
        if len(raw) == guess:
            return raw
        guess = len(raw)
    _fail("V180r8 producer-free output fixed point did not converge")


def verify_cached_exact_terminal_independently_v180r8(
    terminal_bytes: bytes,
) -> dict[str, Any]:
    authorization_document, slot = _authorization()
    document = _object(terminal_bytes, "V180r8 cached terminal")
    proof_hex = document.get("durable_proof_bytes_hex")
    if type(proof_hex) is not str:
        _fail("V180r8 durable proof hex is absent")
    try:
        proof_bytes = bytes.fromhex(proof_hex)
    except ValueError as error:
        raise ConstructionK7CachedExactIndependentVerifierV180r8Error(
            "V180r8 durable proof hex is invalid"
        ) from error
    proof_sha = hashlib.sha256(proof_bytes).hexdigest()
    proof_document = _object(proof_bytes, "V180r8 embedded durable proof")
    if not (
        proof_bytes.hex() == proof_hex
        and len(proof_bytes) == authorization.EXPECTED_DURABLE_PROOF_BYTE_COUNT
        and proof_sha == authorization.EXPECTED_DURABLE_PROOF_SHA256
        and proof_document.get("durable_exact_infeasibility_proof_id")
        == authorization.EXPECTED_DURABLE_PROOF_ID
    ):
        _fail("V180r8 embedded durable proof identity changed")
    verification, consumption, hash_count = _business_replay(proof_bytes)
    peak = document.get("observed_peak_working_bytes_diagnostic")
    if type(peak) is not int or not 0 < peak <= authorization.WORKING_BYTES_HARD_CAP:
        _fail("V180r8 observed memory diagnostic crossed its hard cap")
    expected = _replay_terminal(
        slot=slot,
        proof_bytes=proof_bytes,
        proof_document=proof_document,
        verification=verification,
        consumption=consumption,
        hash_count=hash_count,
        observed_peak=peak,
    )
    if expected != terminal_bytes:
        _fail("V180r8 complete terminal did not reproduce without its producer")
    terminal_id = document["production_terminal_bundle_id"]
    if EXPECTED_TERMINAL_BUNDLE_ID != "0" * 64 and not (
        terminal_id == EXPECTED_TERMINAL_BUNDLE_ID
        and len(terminal_bytes) == EXPECTED_TERMINAL_BYTE_COUNT
        and hashlib.sha256(terminal_bytes).hexdigest() == EXPECTED_TERMINAL_SHA256
    ):
        _fail("V180r8 frozen production terminal identity changed")
    verification_payload = {
        "schema": "acfqp.cached_exact_infeasibility_execution_verification.v180r8",
        "cached_execution_authorization_id": authorization_document[
            "cached_execution_authorization_id"
        ],
        "production_terminal_bundle_id": terminal_id,
        "production_terminal_byte_count": len(terminal_bytes),
        "production_terminal_sha256": hashlib.sha256(terminal_bytes).hexdigest(),
        "durable_exact_infeasibility_proof_id": (
            authorization.EXPECTED_DURABLE_PROOF_ID
        ),
        "durable_verification_id": verification["verification_id"],
        "cache_consumption_id": consumption["cache_consumption_id"],
        "selected_plan_id": authorization.SELECTED_PLAN_ID,
        "v9_counter_record_count": 269,
        "shared_resource_receipt_count": 9,
        "source_proof_replayed_without_v180r8_producer_import": True,
        "fresh_plan_binding_replayed": True,
        "complete_v9_counter_record_set_reconstructed": True,
        "counter_to_work_to_comparison_chain_reconstructed": True,
        "nine_shared_resource_receipts_reconstructed": True,
        "output_fixed_point_reconstructed": True,
        "fresh_single_path_verified": True,
        "all_ten_paths_verified": False,
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "official_execution_allowed": False,
    }
    result = {
        **verification_payload,
        "verification_id": domains.extension_content_id_v180r8(
            domains.CONSTRUCTION_K7_CACHED_EXECUTION_VERIFICATION_V180R8_DOMAIN,
            verification_payload,
        ),
    }
    raw = canonical_json_bytes(result)
    if EXPECTED_VERIFICATION_ID != "0" * 64 and not (
        result["verification_id"] == EXPECTED_VERIFICATION_ID
        and len(raw) == EXPECTED_VERIFICATION_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_VERIFICATION_SHA256
    ):
        _fail("V180r8 frozen verification identity changed")
    return result


__all__ = (
    "EXPECTED_TERMINAL_BUNDLE_ID",
    "EXPECTED_TERMINAL_BYTE_COUNT",
    "EXPECTED_TERMINAL_SHA256",
    "EXPECTED_VERIFICATION_ID",
    "EXPECTED_VERIFICATION_BYTE_COUNT",
    "EXPECTED_VERIFICATION_SHA256",
    "verify_cached_exact_terminal_independently_v180r8",
)
