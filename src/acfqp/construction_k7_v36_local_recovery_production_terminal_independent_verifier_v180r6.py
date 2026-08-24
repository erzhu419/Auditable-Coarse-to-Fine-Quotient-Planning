"""Producer-free replay for the source-pinned V180r6 V36 terminal."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, Mapping, NoReturn, Sequence

from acfqp import construction_accounting_registry_v9 as registry_v9
from acfqp import construction_k7_all_path_production_execution_protocol_v180r3 as protocol
from acfqp import construction_k7_all_path_v36_execution_authorization_v180r6 as authorization
from acfqp import construction_k7_domain_registry_extension_v180r6 as domains
from acfqp import construction_k7_standard_2048_adaptive_accounting_preregistration_v36 as v36_pre
from acfqp.accounting_v1 import (
    LaneEnum,
    NativeZeroAttestationV1,
    ReducerEnum,
    RouteKindEnum,
    WorkVectorV1,
)
from acfqp.actual_accounting_v1 import ActualWorkScope, derive_actual_projection_v1
from acfqp.phase3e_ids import canonical_json_bytes, content_id, loads_canonical_json


EXPECTED_TERMINAL_BUNDLE_ID = "0" * 64
EXPECTED_TERMINAL_BYTE_COUNT = 0
EXPECTED_TERMINAL_SHA256 = "0" * 64
EXPECTED_VERIFICATION_ID = "0" * 64
EXPECTED_VERIFICATION_BYTE_COUNT = 0
EXPECTED_VERIFICATION_SHA256 = "0" * 64

_V35_CAMPAIGN_ID = "c33002f8bac5415d94c5185876ce104ac859243e7b50ee5922c1be9b4a812d25"
_V35_CAMPAIGN_SHA256 = "a68782308b14b76d8261f233d8a576b7c148e5f2134b0097af482aed772db050"
_V35_VERIFICATION_ID = "0591b03140cb3e807b68ee4e90129c93863a45ef29ed44896df49c7d4caea348"
_V35_VERIFICATION_SHA256 = "6835ac89b3b01beb93a0c34ef7f543a85ae17316b11c82a229326dc0a307ca5d"
_V36_CAMPAIGN_ID = "758f01ac78789d25512b218ed16b8ca4bfaa95a08dc52e81fc15601b42662693"
_V36_CAMPAIGN_BYTE_COUNT = 250_414
_V36_CAMPAIGN_SHA256 = "da3432bf18e4aa94091456f9ab09b1809258fa60dae9cd89aec93daa5dee6030"
_V36_VERIFICATION_ID = "ed3354625ab6c3e8928bdf0b0807ee7e7c47a2c5c84a0e364916fc1ac2e94c14"
_V36_VERIFICATION_BYTE_COUNT = 2_457
_V36_VERIFICATION_SHA256 = "e3656a5ac5aa9572670b4fd382dd8b08fc32d1c1ba1eebbcf142e751ad68ef52"
_OPERATIONAL_VECTOR_COUNT = 15

_TOP_LEVEL_FIELDS = {
    "COUNTER_COMPLETENESS_GATE",
    "WORKLOAD_ECONOMICS_GATE",
    "certificate_failure_before_local_recovery_observed",
    "development_fixture_only",
    "finalizer_output_bytes",
    "fixed_point_iteration",
    "formalization_contract_id",
    "fresh_v180r6_observed_occurrence_present",
    "historical_summary_translation_used",
    "local_ground_distinction_only_after_certificate_failure",
    "official_N_break_even",
    "official_execution_allowed",
    "official_scalar_cost",
    "output_bytes_fixed_point",
    "partial_campaign_cannot_unlock_any_gate",
    "production_execution_protocol_id",
    "production_execution_slot",
    "production_occurrence_receipt",
    "production_terminal_bundle_id",
    "schema",
    "source_campaign",
    "source_independent_verification",
    "source_operational_work_vectors",
    "source_output_bytes",
    "terminal_actual_projection_proof",
    "terminal_code",
    "terminal_comparison_vector",
    "terminal_native_zero_attestation",
    "terminal_work_vector",
}
_RECEIPT_FIELDS = {
    "execution_nonce",
    "historical_summary_translation_used",
    "native_v9_counter_records_used",
    "predecessor_occurrence_slot_id",
    "preexisting_retained_output_used",
    "production_execution_protocol_id",
    "production_execution_slot_id",
    "production_execution_started_by_this_call",
    "production_occurrence_receipt_id",
    "schema",
    "source_campaign_byte_count",
    "source_campaign_id",
    "source_campaign_sha256",
    "source_counter_record_count",
    "source_operational_work_vector_count",
    "source_operational_work_vector_ids",
    "source_output_inventory",
    "source_verification_byte_count",
    "source_verification_id",
    "source_verification_sha256",
    "terminal_code",
    "v35_source_campaign_id",
    "v35_source_campaign_sha256",
    "v35_source_verification_id",
    "v35_source_verification_sha256",
}


class ConstructionK7V36ProductionTerminalIndependentVerifierV180r6Error(
    RuntimeError
):
    """The retained V36 tree or terminal reconstruction changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7V36ProductionTerminalIndependentVerifierV180r6Error(
        message
    )


def _object(raw: bytes, label: str) -> dict[str, Any]:
    if type(raw) is not bytes:
        _fail(f"{label} is not exact bytes")
    document = loads_canonical_json(raw)
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail(f"{label} is not one canonical object")
    return document


def _source_authorization() -> tuple[dict[str, Any], dict[str, Any]]:
    frozen = authorization.freeze_v36_execution_authorization_v180r6()
    document = frozen.to_document()
    source_root = Path(__file__).resolve().parent
    for fact in document["source_facts"]:
        raw = (source_root / fact["filename"]).read_bytes()
        if fact != {
            "filename": fact["filename"],
            "byte_count": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
        }:
            _fail("V180r6 authorized source bytes changed")
    matches = [
        row
        for row in protocol.freeze_all_path_production_execution_protocol_v180r3()
        .to_document()["production_execution_slots"]
        if row["terminal_code"] == "LOCAL_GROUND_RECOVERY"
    ]
    if len(matches) != 1 or document["production_execution_slot"] != matches[0]:
        _fail("V180r6 authorization crossed its execution slot")
    return document, matches[0]


def _inventory(root: Path) -> list[dict[str, Any]]:
    return [
        {
            "relative_path": path.relative_to(root).as_posix(),
            "canonical_byte_count": len(raw),
            "canonical_sha256": hashlib.sha256(raw).hexdigest(),
        }
        for path in sorted(item for item in root.rglob("*") if item.is_file())
        for raw in (path.read_bytes(),)
    ]


def _operational_vectors(root: Path) -> tuple[WorkVectorV1, ...]:
    registry = registry_v9.official_counter_registry_v9()
    vectors = []
    for path in sorted(item for item in root.rglob("*.json") if item.is_file()):
        document = _object(path.read_bytes(), path.name)
        measurement = document.get("measurement")
        vector_document = document.get("work_vector")
        if not isinstance(measurement, Mapping) or not isinstance(
            vector_document, Mapping
        ):
            continue
        if measurement.get("lane") == LaneEnum.OPERATIONAL.value:
            vectors.append(WorkVectorV1.from_dict(vector_document, registry))
    if (
        len(vectors) != _OPERATIONAL_VECTOR_COUNT
        or len({row.work_vector_id for row in vectors}) != len(vectors)
    ):
        _fail("retained V36 operational vector denominator changed")
    return tuple(vectors)


def _aggregate(vectors: Sequence[WorkVectorV1]) -> dict[str, int]:
    registry = registry_v9.official_counter_registry_v9()
    values = {path: 0 for path in registry.by_path}
    for vector in vectors:
        registry.validate_vector(vector)
        for path, value in vector.values.items():
            if registry.by_path[path].reducer is ReducerEnum.MAX:
                values[path] = max(values[path], value)
            else:
                values[path] += value
    return values


def _verify_source_document(
    document: Mapping[str, Any],
    *,
    id_key: str,
    expected_id: str,
    expected_bytes: int,
    expected_sha256: str,
    domain: str,
) -> None:
    raw = canonical_json_bytes(dict(document))
    payload = dict(document)
    observed_id = payload.pop(id_key, None)
    if not (
        observed_id == expected_id
        and len(raw) == expected_bytes
        and hashlib.sha256(raw).hexdigest() == expected_sha256
        and content_id(domain, payload) == expected_id
    ):
        _fail("embedded V36 source document changed")


def verify_v36_production_terminal_independently_v180r6(
    terminal_bytes: bytes, output_root: Path
) -> dict[str, Any]:
    if not isinstance(output_root, Path) or not output_root.is_dir():
        _fail("retained V36 output root is absent")
    authorization_document, slot = _source_authorization()
    document = _object(terminal_bytes, "V180r6 V36 terminal bundle")
    if set(document) != _TOP_LEVEL_FIELDS:
        _fail("V180r6 terminal bundle field set changed")
    payload = dict(document)
    bundle_id = payload.pop("production_terminal_bundle_id", None)
    if not (
        document["schema"]
        == "acfqp.v36_local_recovery_production_terminal_bundle.v180r6"
        and document["production_execution_protocol_id"]
        == protocol.EXPECTED_PROTOCOL_ID
        and document["production_execution_slot"] == slot
        and document["terminal_code"] == "LOCAL_GROUND_RECOVERY"
        and bundle_id
        == domains.extension_content_id_v180r6(
            domains.CONSTRUCTION_K7_V36_EXECUTION_TERMINAL_V180R6_DOMAIN,
            payload,
        )
        and (
            EXPECTED_TERMINAL_BUNDLE_ID == "0" * 64
            or (
                bundle_id == EXPECTED_TERMINAL_BUNDLE_ID
                and len(terminal_bytes) == EXPECTED_TERMINAL_BYTE_COUNT
                and hashlib.sha256(terminal_bytes).hexdigest()
                == EXPECTED_TERMINAL_SHA256
            )
        )
    ):
        _fail("V180r6 terminal bundle identity changed")
    receipt = document["production_occurrence_receipt"]
    if type(receipt) is not dict or set(receipt) != _RECEIPT_FIELDS:
        _fail("V180r6 production receipt field set changed")
    receipt_payload = dict(receipt)
    receipt_id = receipt_payload.pop("production_occurrence_receipt_id", None)
    if not (
        receipt_id
        == domains.extension_content_id_v180r6(
            domains.CONSTRUCTION_K7_V36_OCCURRENCE_RECEIPT_V180R6_DOMAIN,
            receipt_payload,
        )
        and receipt["production_execution_protocol_id"]
        == protocol.EXPECTED_PROTOCOL_ID
        and receipt["production_execution_slot_id"]
        == slot["production_execution_slot_id"]
        and receipt["predecessor_occurrence_slot_id"]
        == slot["predecessor_occurrence_slot_id"]
        and receipt["execution_nonce"] == slot["execution_nonce"]
        and receipt["terminal_code"] == "LOCAL_GROUND_RECOVERY"
        and receipt["v35_source_campaign_id"] == _V35_CAMPAIGN_ID
        and receipt["v35_source_campaign_sha256"] == _V35_CAMPAIGN_SHA256
        and receipt["v35_source_verification_id"] == _V35_VERIFICATION_ID
        and receipt["v35_source_verification_sha256"]
        == _V35_VERIFICATION_SHA256
        and receipt["source_campaign_id"] == _V36_CAMPAIGN_ID
        and receipt["source_campaign_byte_count"] == _V36_CAMPAIGN_BYTE_COUNT
        and receipt["source_campaign_sha256"] == _V36_CAMPAIGN_SHA256
        and receipt["source_verification_id"] == _V36_VERIFICATION_ID
        and receipt["source_verification_byte_count"]
        == _V36_VERIFICATION_BYTE_COUNT
        and receipt["source_verification_sha256"] == _V36_VERIFICATION_SHA256
        and receipt["source_operational_work_vector_count"]
        == _OPERATIONAL_VECTOR_COUNT
        and receipt["source_counter_record_count"]
        == _OPERATIONAL_VECTOR_COUNT * 269
        and receipt["production_execution_started_by_this_call"] is True
        and receipt["preexisting_retained_output_used"] is False
        and receipt["native_v9_counter_records_used"] is True
        and receipt["historical_summary_translation_used"] is False
        and receipt["source_output_inventory"] == _inventory(output_root)
    ):
        _fail("V180r6 production receipt semantics changed")
    _verify_source_document(
        document["source_campaign"],
        id_key="adaptive_accounted_campaign_id",
        expected_id=_V36_CAMPAIGN_ID,
        expected_bytes=_V36_CAMPAIGN_BYTE_COUNT,
        expected_sha256=_V36_CAMPAIGN_SHA256,
        domain=v36_pre.FUTURE_DOMAINS["campaign"],
    )
    _verify_source_document(
        document["source_independent_verification"],
        id_key="adaptive_accounting_verification_id",
        expected_id=_V36_VERIFICATION_ID,
        expected_bytes=_V36_VERIFICATION_BYTE_COUNT,
        expected_sha256=_V36_VERIFICATION_SHA256,
        domain=v36_pre.FUTURE_DOMAINS["verification"],
    )
    retained_vectors = _operational_vectors(output_root)
    embedded = document["source_operational_work_vectors"]
    registry = registry_v9.official_counter_registry_v9()
    if type(embedded) is not list:
        _fail("embedded V36 vector inventory changed")
    embedded_vectors = tuple(WorkVectorV1.from_dict(row, registry) for row in embedded)
    if (
        embedded_vectors != retained_vectors
        or receipt["source_operational_work_vector_ids"]
        != [row.work_vector_id for row in retained_vectors]
    ):
        _fail("embedded and retained V36 vectors differ")
    aggregate = _aggregate(retained_vectors)
    terminal_vector = WorkVectorV1.from_dict(document["terminal_work_vector"], registry)
    expected_values = dict(aggregate)
    expected_values["io.output_bytes"] = aggregate["io.output_bytes"] + len(
        terminal_bytes
    )
    if not (
        terminal_vector.values == expected_values
        and terminal_vector.subject_id == receipt_id
        and terminal_vector.route_kind is RouteKindEnum.LOCAL_ATTEMPT
    ):
        _fail("V180r6 terminal WorkVector differs from direct source records")
    comparison_profile = registry_v9.official_comparison_profile_v9(registry)
    actual_profile = registry_v9.official_actual_projection_profile_v9(
        registry, comparison_profile
    )
    comparison, proof = derive_actual_projection_v1(
        terminal_vector,
        registry,
        comparison_profile,
        actual_profile,
        source_lane=LaneEnum.OPERATIONAL,
        work_scope=ActualWorkScope.MARGINAL_ROUTE_EXECUTION,
    )
    zero = NativeZeroAttestationV1.derive(terminal_vector, registry)
    if not (
        document["terminal_comparison_vector"] == comparison.to_dict()
        and document["terminal_actual_projection_proof"] == proof.to_dict()
        and document["terminal_native_zero_attestation"] == zero.to_dict()
        and document["source_output_bytes"] == aggregate["io.output_bytes"]
        and document["finalizer_output_bytes"] == len(terminal_bytes)
        and document["output_bytes_fixed_point"] == expected_values["io.output_bytes"]
        and document["fresh_v180r6_observed_occurrence_present"] is True
        and document["certificate_failure_before_local_recovery_observed"] is True
        and document["local_ground_distinction_only_after_certificate_failure"]
        is True
        and document["historical_summary_translation_used"] is False
        and document["development_fixture_only"] is False
        and document["partial_campaign_cannot_unlock_any_gate"] is True
        and document["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
        and document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
        and document["official_scalar_cost"] is None
        and document["official_N_break_even"] is None
        and document["official_execution_allowed"] is False
    ):
        _fail("V180r6 terminal projection, fixed point, or claim lock changed")
    verification_payload = {
        "schema": "acfqp.v36_production_execution_verification.v180r6",
        "v36_execution_authorization_id": authorization_document[
            "v36_execution_authorization_id"
        ],
        "production_terminal_bundle_id": bundle_id,
        "production_terminal_bytes_sha256": hashlib.sha256(
            terminal_bytes
        ).hexdigest(),
        "source_campaign_id": _V36_CAMPAIGN_ID,
        "source_verification_id": _V36_VERIFICATION_ID,
        "retained_output_file_count": len(receipt["source_output_inventory"]),
        "operational_work_vector_count": len(retained_vectors),
        "counter_record_count": sum(len(row.records) for row in retained_vectors),
        "terminal_counter_record_count": len(terminal_vector.records),
        "source_records_replayed_without_producer_import": True,
        "terminal_work_vector_reconstructed": True,
        "terminal_comparison_vector_rederived": True,
        "terminal_output_fixed_point_replayed": True,
        "certificate_failure_then_local_recovery_verified": True,
        "fresh_single_path_verified": True,
        "all_ten_paths_verified": False,
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "official_execution_allowed": False,
    }
    return {
        **verification_payload,
        "verification_id": domains.extension_content_id_v180r6(
            domains.CONSTRUCTION_K7_V36_EXECUTION_VERIFICATION_V180R6_DOMAIN,
            verification_payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V36ProductionVerificationV180r6:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    verification_id: str

    def to_document(self) -> dict[str, Any]:
        return _object(self.canonical_bytes, "V180r6 V36 verification")


def freeze_v36_production_verification_v180r6(
    terminal_bytes: bytes, output_root: Path
) -> V36ProductionVerificationV180r6:
    document = verify_v36_production_terminal_independently_v180r6(
        terminal_bytes, output_root
    )
    raw = canonical_json_bytes(document)
    if EXPECTED_VERIFICATION_ID != "0" * 64 and not (
        document["verification_id"] == EXPECTED_VERIFICATION_ID
        and len(raw) == EXPECTED_VERIFICATION_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_VERIFICATION_SHA256
    ):
        _fail("V180r6 frozen V36 verification changed")
    return V36ProductionVerificationV180r6(
        _ISSUER,
        raw,
        document["verification_id"],
    )


__all__ = (
    "EXPECTED_TERMINAL_BUNDLE_ID",
    "EXPECTED_VERIFICATION_ID",
    "freeze_v36_production_verification_v180r6",
    "verify_v36_production_terminal_independently_v180r6",
)
