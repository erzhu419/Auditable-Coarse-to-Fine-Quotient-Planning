"""Fresh durable-cache occurrence and V9 terminal finalization for V180r8.

The source proof is produced before the online measurement window from the
already frozen Phase-0.5 bundle.  The measured occurrence then reads those
immutable bytes, runs the registered independent durable-proof verifier, and
binds the retained verifier handle to one preregistered plan.  It never calls
the durable-proof producer, a planner, or a ground solver in the online
window.

All V9 paths are emitted as native ``CounterRecordV1`` rows.  The nine shared
resource paths have an explicit, source-closed receipt set.  Accounting hashes
performed after the operational cutoff are excluded from the business hash
meter, which makes the output-byte fixed point finite and replayable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
import resource
import stat
import threading
from typing import Any, Mapping, NoReturn

from acfqp import construction_accounting_registry_v9 as registry_v9
from acfqp import construction_k7_all_path_formalization_contract_v180 as contract
from acfqp import construction_k7_all_path_production_execution_protocol_v180r3 as protocol
from acfqp import construction_k7_domain_registry_extension_v180r8 as domains
from acfqp import phase3e_exact_infeasibility_durable_proof_v1 as durable
from acfqp.accounting_v1 import (
    CounterRecordV1,
    LaneEnum,
    NativeZeroAttestationV1,
    ReducerEnum,
    RouteKindEnum,
    WorkVectorV1,
)
from acfqp.actual_accounting_v1 import ActualWorkScope, derive_actual_projection_v1
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp.routing_v1 import TerminalCode


MAXIMUM_FIXED_POINT_ITERATIONS = 32
EXPECTED_DURABLE_PROOF_BYTE_COUNT = 37_591
EXPECTED_DURABLE_PROOF_SHA256 = (
    "d795e6cdca04070632912c0f9cfe0a2e49f14710020fb2481c5a43aa892ed1ca"
)
EXPECTED_DURABLE_PROOF_ID = (
    "9f682a2c1b6e9ce1e697b9910e01b41180353eae24a9d5f720e071b802b6a6c8"
)
LOGICAL_OCCURRENCE_ID = hashlib.sha256(
    b"acfqp:v180r8:fresh-cached-exact-infeasibility-occurrence\x00ordinal-8"
).hexdigest()
SELECTED_PLAN_ID = hashlib.sha256(
    b"acfqp:v180r8:durable-exact-cache-plan\x00identity-match"
).hexdigest()
WORKING_BYTES_HARD_CAP = 2 * 1024 * 1024 * 1024

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
_SUM_PATHS = frozenset(
    {
        "common.hash_invocations",
        "common.integrity_checks",
        "common.protocol_checks",
        "io.output_bytes",
        "io.read_bytes",
        "io.staged_bytes",
        "process.launches",
    }
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
_BUSINESS_HASH_LOCK = threading.Lock()


class ConstructionK7CachedExactInfeasibilityFinalizerV180r8Error(RuntimeError):
    """The proof, measured occurrence, or terminal fixed point changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7CachedExactInfeasibilityFinalizerV180r8Error(message)


def _slot() -> dict[str, Any]:
    rows = protocol.freeze_all_path_production_execution_protocol_v180r3().to_document()[
        "production_execution_slots"
    ]
    matches = [
        row
        for row in rows
        if row["terminal_code"] == TerminalCode.CACHED_EXACT_INFEASIBLE.value
    ]
    if len(matches) != 1:
        _fail("V180r3 protocol lost the cached-exact slot")
    return matches[0]


def _canonical_object(raw: bytes, label: str) -> dict[str, Any]:
    try:
        document = loads_canonical_json(raw)
    except Exception as error:
        raise ConstructionK7CachedExactInfeasibilityFinalizerV180r8Error(
            f"{label} is not canonical JSON"
        ) from error
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail(f"{label} is not one canonical object")
    return document


def _source_receipt(
    proof_bytes: bytes,
    proof_document: Mapping[str, Any],
    *,
    proof_sha256: str,
) -> dict[str, Any]:
    payload = {
        "schema": "acfqp.cached_exact_infeasibility_source_receipt.v180r8",
        "logical_occurrence_id": LOGICAL_OCCURRENCE_ID,
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


def _business_replay(proof_bytes: bytes) -> tuple[dict[str, Any], dict[str, Any], int]:
    """Run the online proof verifier while counting only its business hashes."""

    with _BUSINESS_HASH_LOCK:
        original_id = durable._id  # noqa: SLF001 - registered measurement boundary
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
            if (
                verified.result.outcome
                is not durable.DurableProofVerificationOutcomeV1.IDENTICAL_MATCH
                or verified.result.durable_proof_id != EXPECTED_DURABLE_PROOF_ID
                or verified.result.submitted_bytes_sha256
                != EXPECTED_DURABLE_PROOF_SHA256
            ):
                _fail("durable proof did not independently replay as an exact match")
            verification_document = verified.result.to_dict()
            consumption = durable.bind_verified_durable_exact_infeasibility_to_plan_v1(
                verified,
                selected_plan_id=SELECTED_PLAN_ID,
            )
            consumption_document = consumption.to_dict()
        finally:
            durable._id = original_id  # type: ignore[assignment]  # noqa: SLF001
            durable._sha256_bytes = original_sha  # type: ignore[assignment]  # noqa: SLF001
    if count <= 0:
        _fail("durable proof replay emitted no business hash observation")
    return verification_document, consumption_document, count


def _evidence_id(role: str, payload: Mapping[str, Any]) -> str:
    return domains.extension_content_id_v180r8(
        domains.CONSTRUCTION_K7_CACHED_SOURCE_RECEIPT_V180R8_DOMAIN,
        {"role": role, "payload": dict(payload)},
    )


def _receipt_set(
    *,
    slot: Mapping[str, Any],
    source_receipt: Mapping[str, Any],
    values: Mapping[str, int],
) -> dict[str, Any]:
    registry = registry_v9.official_counter_registry_v9()
    rows = []
    source_kind = {
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
    for path in SHARED_RESOURCE_PATHS:
        leaf = registry.by_path[path]
        row_payload = {
            "schema": "acfqp.cached_exact_shared_resource_receipt.v180r8",
            "logical_occurrence_id": LOGICAL_OCCURRENCE_ID,
            "production_execution_slot_id": slot["production_execution_slot_id"],
            "path": path,
            "reducer": leaf.reducer.value,
            "value": values[path],
            "source_kind": source_kind[path],
            "source_receipt_id": source_receipt["cached_source_receipt_id"],
            "window_start_sequence": 1,
            "window_cutoff_sequence": 9,
            "complete_through_terminal_cutoff": True,
            "native_zero_observed": values[path] == 0,
            "accounting_provenance_hashes_excluded": True,
        }
        rows.append(
            {
                **row_payload,
                "receipt_id": _evidence_id(f"SHARED_RESOURCE:{path}", row_payload),
            }
        )
    payload = {
        "schema": "acfqp.cached_exact_shared_resource_receipt_set.v180r8",
        "logical_occurrence_id": LOGICAL_OCCURRENCE_ID,
        "production_execution_slot_id": slot["production_execution_slot_id"],
        "selected_plan_id": SELECTED_PLAN_ID,
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
    *,
    values: Mapping[str, int],
    receipt_set_id: str,
) -> tuple[WorkVectorV1, Any, Any, NativeZeroAttestationV1]:
    registry = registry_v9.official_counter_registry_v9()
    if set(values) != set(registry.by_path):
        _fail("cached path did not explicitly observe every V9 leaf")
    records = tuple(
        CounterRecordV1.observe(
            registry,
            path,
            values[path],
            recorder_id=receipt_set_id,
        )
        for path in sorted(registry.by_path)
    )
    vector = WorkVectorV1(
        registry.registry_id,
        LOGICAL_OCCURRENCE_ID,
        RouteKindEnum.ABSTRACT_FAILED_PREFIX,
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


def _materialize_terminal(
    *,
    slot: Mapping[str, Any],
    source_receipt: Mapping[str, Any],
    proof_bytes: bytes,
    proof_document: Mapping[str, Any],
    verification_document: Mapping[str, Any],
    consumption_document: Mapping[str, Any],
    base_values: Mapping[str, int],
    observed_peak_working_bytes_diagnostic: int,
) -> bytes:
    guess = 0
    for iteration in range(MAXIMUM_FIXED_POINT_ITERATIONS):
        values = dict(base_values)
        values["io.output_bytes"] = guess
        receipt_set = _receipt_set(
            slot=slot,
            source_receipt=source_receipt,
            values=values,
        )
        vector, comparison, projection, zero = _work_chain(
            values=values,
            receipt_set_id=receipt_set["shared_resource_receipt_set_id"],
        )
        terminal_evidence_payload = {
            "schema": "acfqp.cached_exact_terminal_classification.v180r8",
            "logical_occurrence_id": LOGICAL_OCCURRENCE_ID,
            "terminal_class": "INFEASIBILITY_CERTIFICATE",
            "terminal_code": TerminalCode.CACHED_EXACT_INFEASIBLE.value,
            "durable_exact_infeasibility_proof_id": proof_document[
                "durable_exact_infeasibility_proof_id"
            ],
            "durable_verification_id": verification_document["verification_id"],
            "cache_consumption_id": consumption_document["cache_consumption_id"],
            "work_vector_id": vector.work_vector_id,
            "actual_projection_proof_id": projection.actual_projection_proof_id,
            "shared_resource_receipt_set_id": receipt_set[
                "shared_resource_receipt_set_id"
            ],
            "outcome": "IDENTICAL_MATCH",
        }
        terminal_evidence = {
            **terminal_evidence_payload,
            "terminal_classification_id": _evidence_id(
                "TERMINAL_CLASSIFICATION", terminal_evidence_payload
            ),
        }
        payload = {
            "schema": "acfqp.cached_exact_infeasibility_production_terminal.v180r8",
            "formalization_contract_id": contract.EXPECTED_CONTRACT_ID,
            "production_execution_protocol_id": protocol.EXPECTED_PROTOCOL_ID,
            "production_execution_slot": dict(slot),
            "logical_occurrence_id": LOGICAL_OCCURRENCE_ID,
            "selected_plan_id": SELECTED_PLAN_ID,
            "terminal_code": TerminalCode.CACHED_EXACT_INFEASIBLE.value,
            "terminal_class": "INFEASIBILITY_CERTIFICATE",
            "source_receipt": dict(source_receipt),
            "durable_proof_bytes_hex": proof_bytes.hex(),
            "durable_proof_document": dict(proof_document),
            "durable_independent_verification": dict(verification_document),
            "durable_cache_consumption": dict(consumption_document),
            "terminal_classification": terminal_evidence,
            "shared_resource_receipt_set": receipt_set,
            "terminal_work_vector": vector.to_dict(),
            "terminal_comparison_vector": comparison.to_dict(),
            "terminal_actual_projection_proof": projection.to_dict(),
            "terminal_native_zero_attestation": zero.to_dict(),
            "integrity_obligations": list(_INTEGRITY_OBLIGATIONS),
            "protocol_obligations": list(_PROTOCOL_OBLIGATIONS),
            "working_bytes_hard_cap": WORKING_BYTES_HARD_CAP,
            "observed_peak_working_bytes_diagnostic": (
                observed_peak_working_bytes_diagnostic
            ),
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
    _fail("V180r8 output-byte fixed point did not converge")


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class CachedExactProductionTerminalV180r8:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    production_terminal_bundle_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("V180r8 terminal is not issuer-created")

    def to_document(self) -> dict[str, Any]:
        return _canonical_object(self.canonical_bytes, "V180r8 cached terminal")


def run_cached_exact_infeasibility_production_occurrence_v180r8(
    proof_path: Path,
) -> CachedExactProductionTerminalV180r8:
    """Execute one fresh, source-pinned durable cache lookup exactly once."""

    if not isinstance(proof_path, Path) or proof_path.is_symlink() or not proof_path.is_file():
        _fail("V180r8 proof path must be one exact regular Path")
    mode = proof_path.stat(follow_symlinks=False).st_mode
    if not stat.S_ISREG(mode):
        _fail("V180r8 proof source is not a regular file")
    slot = _slot()
    old_soft, old_hard = resource.getrlimit(resource.RLIMIT_AS)
    if old_hard != resource.RLIM_INFINITY and old_hard < WORKING_BYTES_HARD_CAP:
        _fail("current address-space hard limit is below the preregistered cap")
    resource.setrlimit(
        resource.RLIMIT_AS,
        (WORKING_BYTES_HARD_CAP, WORKING_BYTES_HARD_CAP),
    )
    proof_bytes = proof_path.read_bytes()
    proof_document = _canonical_object(proof_bytes, "durable proof source")
    proof_sha256 = hashlib.sha256(proof_bytes).hexdigest()
    if not (
        len(proof_bytes) == EXPECTED_DURABLE_PROOF_BYTE_COUNT
        and proof_sha256 == EXPECTED_DURABLE_PROOF_SHA256
        and proof_document.get("durable_exact_infeasibility_proof_id")
        == EXPECTED_DURABLE_PROOF_ID
    ):
        _fail("V180r8 durable proof source changed")
    source_receipt = _source_receipt(
        proof_bytes,
        proof_document,
        proof_sha256=proof_sha256,
    )
    verification, consumption, replay_hash_count = _business_replay(proof_bytes)
    hash_count = 1 + replay_hash_count
    if not (
        consumption["selected_plan_id"] == SELECTED_PLAN_ID
        and consumption["durable_proof_id"] == EXPECTED_DURABLE_PROOF_ID
        and consumption["verification_id"] == verification["verification_id"]
        and consumption["outcome"] == "IDENTICAL_MATCH"
    ):
        _fail("V180r8 plan-frozen cache consumption changed")
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
    if type(peak) is not int or peak <= 0 or peak > WORKING_BYTES_HARD_CAP:
        _fail("V180r8 diagnostic working peak crossed the hard cap")
    registry = registry_v9.official_counter_registry_v9()
    values = {path: 0 for path in registry.by_path}
    values.update(
        {
            "common.abstract_subproof_cache_lookups": 1,
            "common.hash_invocations": hash_count,
            "common.integrity_checks": len(_INTEGRITY_OBLIGATIONS),
            "common.protocol_checks": len(_PROTOCOL_OBLIGATIONS),
            "io.mounted_bytes_peak": len(proof_bytes),
            "io.read_bytes": len(proof_bytes),
            "io.staged_bytes": 0,
            "memory.working_bytes_peak": WORKING_BYTES_HARD_CAP,
            "process.launches": 0,
            "route.attempts": 1,
            "route.successes": 1,
            "route.failures": 0,
        }
    )
    raw = _materialize_terminal(
        slot=slot,
        source_receipt=source_receipt,
        proof_bytes=proof_bytes,
        proof_document=proof_document,
        verification_document=verification,
        consumption_document=consumption,
        base_values=values,
        observed_peak_working_bytes_diagnostic=peak,
    )
    document = _canonical_object(raw, "V180r8 cached terminal")
    return CachedExactProductionTerminalV180r8(
        _ISSUER,
        raw,
        document["production_terminal_bundle_id"],
    )


__all__ = (
    "CachedExactProductionTerminalV180r8",
    "ConstructionK7CachedExactInfeasibilityFinalizerV180r8Error",
    "EXPECTED_DURABLE_PROOF_BYTE_COUNT",
    "EXPECTED_DURABLE_PROOF_ID",
    "EXPECTED_DURABLE_PROOF_SHA256",
    "LOGICAL_OCCURRENCE_ID",
    "SELECTED_PLAN_ID",
    "WORKING_BYTES_HARD_CAP",
    "run_cached_exact_infeasibility_production_occurrence_v180r8",
)
