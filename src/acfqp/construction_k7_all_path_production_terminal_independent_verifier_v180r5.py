"""Producer-free replay for the source-pinned V180r5 V34 terminal."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, Mapping, NoReturn, Sequence

from acfqp import construction_accounting_registry_v9 as registry_v9
from acfqp import construction_k7_all_path_production_execution_protocol_v180r3 as protocol
from acfqp import construction_k7_all_path_v34_execution_authorization_v180r5 as authorization
from acfqp import construction_k7_domain_registry_extension_v180r3 as domains_r3
from acfqp import construction_k7_domain_registry_extension_v180r5 as domains
from acfqp import construction_k7_standard_2048_expression_full_accounting_preregistration_v34 as v34_pre
from acfqp.accounting_v1 import (
    LaneEnum,
    NativeZeroAttestationV1,
    ReducerEnum,
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

_V34_CAMPAIGN_ID = "f5e83e7cb6eaee01d35b325e83e6b50676843a32af40c21aae237144b5784f05"
_V34_CAMPAIGN_BYTE_COUNT = 322_463
_V34_CAMPAIGN_SHA256 = "1ec5ae427da041205f4b4ccae23d4bd3dd62cdd5146105a3f4373e62bb9d6630"
_V34_VERIFICATION_ID = "40baaf3c66d42ebc53e686f9dc91ae96ee92ebda442a176ac4db32c75cbc421a"
_V34_VERIFICATION_BYTE_COUNT = 3_275
_V34_VERIFICATION_SHA256 = "7445912f2d641337e0fd959fd951e73c667c8df05fe97fb18b28779cb001ddcb"

_TOP_LEVEL_FIELDS = {
    "COUNTER_COMPLETENESS_GATE",
    "WORKLOAD_ECONOMICS_GATE",
    "development_fixture_only",
    "finalizer_output_bytes",
    "fixed_point_iteration",
    "formalization_contract_id",
    "fresh_v180r3_observed_occurrence_present",
    "historical_summary_translation_used",
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
}


class ConstructionK7AllPathProductionTerminalIndependentVerifierV180r5Error(
    RuntimeError
):
    """The retained V34 tree or V180 terminal reconstruction changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7AllPathProductionTerminalIndependentVerifierV180r5Error(
        message
    )


def _object(raw: bytes, label: str) -> dict[str, Any]:
    document = loads_canonical_json(raw)
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail(f"{label} is not one canonical object")
    return document


def _source_authorization() -> tuple[dict[str, Any], dict[str, Any]]:
    frozen = authorization.freeze_v34_execution_authorization_v180r5()
    document = frozen.to_document()
    source_root = Path(__file__).resolve().parent
    for fact in document["source_facts"]:
        raw = (source_root / fact["filename"]).read_bytes()
        if fact != {
            "filename": fact["filename"],
            "byte_count": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
        }:
            _fail("V180r5 authorized source bytes changed")
    matches = [
        row
        for row in protocol.freeze_all_path_production_execution_protocol_v180r3()
        .to_document()["production_execution_slots"]
        if row["terminal_code"] == "ABSTRACT_CERTIFIED"
    ]
    if len(matches) != 1 or document["production_execution_slot"] != matches[0]:
        _fail("V180r5 authorization crossed its execution slot")
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
    if len(vectors) != 45 or len({row.work_vector_id for row in vectors}) != 45:
        _fail("retained V34 operational vector denominator changed")
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
        _fail("embedded V34 source document changed")


def verify_v34_production_terminal_independently_v180r5(
    terminal_bytes: bytes,
    output_root: Path,
) -> dict[str, Any]:
    if not isinstance(output_root, Path) or not output_root.is_dir():
        _fail("retained V34 output root is absent")
    authorization_document, slot = _source_authorization()
    document = _object(terminal_bytes, "V180r5 V34 terminal bundle")
    if set(document) != _TOP_LEVEL_FIELDS:
        _fail("V180r5 terminal bundle field set changed")
    payload = dict(document)
    bundle_id = payload.pop("production_terminal_bundle_id", None)
    if not (
        document["schema"] == "acfqp.all_path_production_terminal_bundle.v180r3"
        and document["production_execution_protocol_id"]
        == protocol.EXPECTED_PROTOCOL_ID
        and document["production_execution_slot"] == slot
        and document["terminal_code"] == "ABSTRACT_CERTIFIED"
        and bundle_id
        == domains_r3.extension_content_id_v180r3(
            domains_r3.CONSTRUCTION_K7_PRODUCTION_TERMINAL_BUNDLE_V180R3_DOMAIN,
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
        _fail("V180r5 terminal bundle identity changed")
    receipt = document["production_occurrence_receipt"]
    if type(receipt) is not dict or set(receipt) != _RECEIPT_FIELDS:
        _fail("V180r5 production receipt field set changed")
    receipt_payload = dict(receipt)
    receipt_id = receipt_payload.pop("production_occurrence_receipt_id", None)
    if not (
        receipt_id
        == domains_r3.extension_content_id_v180r3(
            domains_r3.CONSTRUCTION_K7_PRODUCTION_OCCURRENCE_RECEIPT_V180R3_DOMAIN,
            receipt_payload,
        )
        and receipt["production_execution_protocol_id"]
        == protocol.EXPECTED_PROTOCOL_ID
        and receipt["production_execution_slot_id"]
        == slot["production_execution_slot_id"]
        and receipt["predecessor_occurrence_slot_id"]
        == slot["predecessor_occurrence_slot_id"]
        and receipt["execution_nonce"] == slot["execution_nonce"]
        and receipt["terminal_code"] == "ABSTRACT_CERTIFIED"
        and receipt["source_campaign_id"] == _V34_CAMPAIGN_ID
        and receipt["source_campaign_byte_count"] == _V34_CAMPAIGN_BYTE_COUNT
        and receipt["source_campaign_sha256"] == _V34_CAMPAIGN_SHA256
        and receipt["source_verification_id"] == _V34_VERIFICATION_ID
        and receipt["source_verification_byte_count"]
        == _V34_VERIFICATION_BYTE_COUNT
        and receipt["source_verification_sha256"] == _V34_VERIFICATION_SHA256
        and receipt["source_operational_work_vector_count"] == 45
        and receipt["source_counter_record_count"] == 45 * 269
        and receipt["production_execution_started_by_this_call"] is True
        and receipt["preexisting_retained_output_used"] is False
        and receipt["native_v9_counter_records_used"] is True
        and receipt["historical_summary_translation_used"] is False
        and receipt["source_output_inventory"] == _inventory(output_root)
    ):
        _fail("V180r5 production receipt semantics changed")
    _verify_source_document(
        document["source_campaign"],
        id_key="expression_full_accounted_campaign_id",
        expected_id=_V34_CAMPAIGN_ID,
        expected_bytes=_V34_CAMPAIGN_BYTE_COUNT,
        expected_sha256=_V34_CAMPAIGN_SHA256,
        domain=v34_pre.FUTURE_DOMAINS["campaign"],
    )
    _verify_source_document(
        document["source_independent_verification"],
        id_key="expression_full_accounting_verification_id",
        expected_id=_V34_VERIFICATION_ID,
        expected_bytes=_V34_VERIFICATION_BYTE_COUNT,
        expected_sha256=_V34_VERIFICATION_SHA256,
        domain=v34_pre.FUTURE_DOMAINS["verification"],
    )
    retained_vectors = _operational_vectors(output_root)
    embedded = document["source_operational_work_vectors"]
    registry = registry_v9.official_counter_registry_v9()
    if type(embedded) is not list:
        _fail("embedded V34 vector inventory changed")
    embedded_vectors = tuple(
        WorkVectorV1.from_dict(row, registry) for row in embedded
    )
    if (
        embedded_vectors != retained_vectors
        or receipt["source_operational_work_vector_ids"]
        != [row.work_vector_id for row in retained_vectors]
    ):
        _fail("embedded and retained V34 vectors differ")
    aggregate = _aggregate(retained_vectors)
    terminal_vector = WorkVectorV1.from_dict(document["terminal_work_vector"], registry)
    expected_values = dict(aggregate)
    expected_values["io.output_bytes"] = (
        aggregate["io.output_bytes"] + len(terminal_bytes)
    )
    if terminal_vector.values != expected_values:
        _fail("V180r5 terminal WorkVector differs from direct source records")
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
        work_scope=ActualWorkScope.ABSTRACT_SELECTED_ROUTE_EXECUTION,
    )
    zero = NativeZeroAttestationV1.derive(terminal_vector, registry)
    if not (
        document["terminal_comparison_vector"] == comparison.to_dict()
        and document["terminal_actual_projection_proof"] == proof.to_dict()
        and document["terminal_native_zero_attestation"] == zero.to_dict()
        and document["source_output_bytes"] == aggregate["io.output_bytes"]
        and document["finalizer_output_bytes"] == len(terminal_bytes)
        and document["output_bytes_fixed_point"] == expected_values["io.output_bytes"]
        and document["fresh_v180r3_observed_occurrence_present"] is True
        and document["historical_summary_translation_used"] is False
        and document["development_fixture_only"] is False
        and document["partial_campaign_cannot_unlock_any_gate"] is True
        and document["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
        and document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
        and document["official_scalar_cost"] is None
        and document["official_N_break_even"] is None
        and document["official_execution_allowed"] is False
    ):
        _fail("V180r5 terminal projection, fixed point, or claim lock changed")
    verification_payload = {
        "schema": "acfqp.v34_production_execution_verification.v180r5",
        "v34_execution_authorization_id": authorization_document[
            "v34_execution_authorization_id"
        ],
        "production_terminal_bundle_id": bundle_id,
        "production_terminal_bytes_sha256": hashlib.sha256(
            terminal_bytes
        ).hexdigest(),
        "source_campaign_id": _V34_CAMPAIGN_ID,
        "source_verification_id": _V34_VERIFICATION_ID,
        "retained_output_file_count": len(receipt["source_output_inventory"]),
        "operational_work_vector_count": len(retained_vectors),
        "counter_record_count": sum(len(row.records) for row in retained_vectors),
        "terminal_counter_record_count": len(terminal_vector.records),
        "source_records_replayed_without_producer_import": True,
        "terminal_work_vector_reconstructed": True,
        "terminal_comparison_vector_rederived": True,
        "terminal_output_fixed_point_replayed": True,
        "fresh_single_path_verified": True,
        "all_ten_paths_verified": False,
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "official_execution_allowed": False,
    }
    return {
        **verification_payload,
        "verification_id": domains.extension_content_id_v180r5(
            domains.CONSTRUCTION_K7_V34_EXECUTION_TERMINAL_V180R5_DOMAIN,
            verification_payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V34ProductionVerificationV180r5:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    verification_id: str

    def to_document(self) -> dict[str, Any]:
        return _object(self.canonical_bytes, "V180r5 V34 verification")


def freeze_v34_production_verification_v180r5(
    terminal_bytes: bytes,
    output_root: Path,
) -> V34ProductionVerificationV180r5:
    document = verify_v34_production_terminal_independently_v180r5(
        terminal_bytes,
        output_root,
    )
    raw = canonical_json_bytes(document)
    if EXPECTED_VERIFICATION_ID != "0" * 64 and not (
        document["verification_id"] == EXPECTED_VERIFICATION_ID
        and len(raw) == EXPECTED_VERIFICATION_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_VERIFICATION_SHA256
    ):
        _fail("V180r5 frozen V34 verification changed")
    return V34ProductionVerificationV180r5(
        _ISSUER,
        raw,
        document["verification_id"],
    )


__all__ = (
    "EXPECTED_TERMINAL_BUNDLE_ID",
    "EXPECTED_VERIFICATION_ID",
    "freeze_v34_production_verification_v180r5",
    "verify_v34_production_terminal_independently_v180r5",
)
