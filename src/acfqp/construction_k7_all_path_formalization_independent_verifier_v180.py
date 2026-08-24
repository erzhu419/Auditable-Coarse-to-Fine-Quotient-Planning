"""Producer-free verifier for the frozen V180 readiness audit."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any

from acfqp import construction_k7_domain_registry_extension_v180 as domains
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


EXPECTED_CONTRACT_ID = (
    "f392e9178e8c9c69150567ce210ad146ab96d61aa5925c34b133415fa86737fd"
)
EXPECTED_READINESS_AUDIT_ID = (
    "3abd33da19d79a8daf2c69fc757bcfed0ffba6a2a1515a5f9991e106b887a8af"
)
EXPECTED_VERIFICATION_ID = (
    "82b729f142d5764ebcb3a48048c68446895d778735780ab53f59119a0d08c2b6"
)
EXPECTED_TERMINALS = (
    "ABSTRACT_CERTIFIED",
    "LOCAL_GROUND_RECOVERY",
    "FULL_GROUND_FALLBACK",
    "CACHED_EXACT_INFEASIBLE",
    "FULL_GROUND_EXACT_INFEASIBLE",
    "INTEGRITY_FAILURE",
    "PROTOCOL_FAILURE",
    "REBUILD_REQUIRED",
    "FALLBACK_CAP_EXHAUSTED",
    "ATTEMPT_BUDGET_EXHAUSTED",
)
_ROW_KEYS = {
    "terminal_code",
    "accounting_registry_version",
    "implementation_state",
    "producer_source",
    "verifier_source",
    "complete_counter_record_work_vector_comparison_vector_chain_implemented",
    "terminal_specific_independent_verifier_implemented",
    "production_site_bound",
    "retained_portable_occurrence_bytes_in_v180",
    "fresh_v180_observed_occurrence_present",
    "v180_output_fixed_point_replayed",
    "blocker_code",
}
_SOURCE_KEYS = {"filename", "source_byte_count", "source_sha256"}


class ConstructionK7AllPathFormalizationIndependentVerifierV180Error(ValueError):
    pass


def _fail(message: str) -> None:
    raise ConstructionK7AllPathFormalizationIndependentVerifierV180Error(message)


def _document(raw: bytes, label: str) -> dict[str, Any]:
    if type(raw) is not bytes or not raw:
        _fail(f"{label} bytes are missing")
    try:
        document = loads_canonical_json(raw)
    except (TypeError, ValueError) as error:
        raise ConstructionK7AllPathFormalizationIndependentVerifierV180Error(
            f"{label} bytes are noncanonical"
        ) from error
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail(f"{label} bytes are noncanonical")
    return document


def _verify_source(row: Any, base: Path) -> None:
    if type(row) is not dict or set(row) != _SOURCE_KEYS:
        _fail("source fact schema changed")
    filename = row["filename"]
    if type(filename) is not str or Path(filename).name != filename:
        _fail("source filename is invalid")
    raw = (base / filename).read_bytes()
    if (
        row["source_byte_count"] != len(raw)
        or row["source_sha256"] != hashlib.sha256(raw).hexdigest()
    ):
        _fail("source bytes changed after readiness freeze")


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class AllPathFormalizationVerificationV180:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    verification_id: str

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


def verify_all_path_formalization_readiness_independently_v180(
    *, contract_bytes: bytes, readiness_bytes: bytes
) -> AllPathFormalizationVerificationV180:
    contract = _document(contract_bytes, "V180 contract")
    audit = _document(readiness_bytes, "V180 readiness audit")
    contract_payload = {
        key: value
        for key, value in contract.items()
        if key != "formalization_contract_id"
    }
    if (
        contract.get("schema") != "acfqp.all_path_formalization_contract.v180"
        or contract.get("formalization_contract_id") != EXPECTED_CONTRACT_ID
        or domains.extension_content_id_v180(
            domains.CONSTRUCTION_K7_FORMALIZATION_CONTRACT_V180_DOMAIN,
            contract_payload,
        )
        != EXPECTED_CONTRACT_ID
        or contract.get("claim_locks", {}).get("v180_terminal_outcomes_accessed")
        is not False
    ):
        _fail("V180 contract identity or outcome-free lock changed")
    audit_payload = {
        key: value
        for key, value in audit.items()
        if key != "formalization_readiness_audit_id"
    }
    audit_id = domains.extension_content_id_v180(
        domains.CONSTRUCTION_K7_READINESS_AUDIT_V180_DOMAIN,
        audit_payload,
    )
    rows = audit.get("terminal_rows")
    if (
        audit.get("schema") != "acfqp.all_path_formalization_readiness.v180"
        or audit.get("formalization_contract_id") != EXPECTED_CONTRACT_ID
        or audit.get("formalization_readiness_audit_id") != audit_id
        or audit_id != EXPECTED_READINESS_AUDIT_ID
        or type(rows) is not list
        or len(rows) != 10
        or tuple(row.get("terminal_code") for row in rows) != EXPECTED_TERMINALS
        or audit.get("audit_timing")
        != "AFTER_V180_CONTRACT_BEFORE_ANY_V180_OUTCOME"
    ):
        _fail("V180 readiness root or terminal inventory changed")
    base = Path(__file__).resolve().parent
    formal_count = 0
    v9_count = 0
    for row in rows:
        if type(row) is not dict or set(row) != _ROW_KEYS:
            _fail("V180 readiness terminal row schema changed")
        _verify_source(row["producer_source"], base)
        verifier_source = row["verifier_source"]
        if verifier_source is not None:
            _verify_source(verifier_source, base)
        formal = row[
            "complete_counter_record_work_vector_comparison_vector_chain_implemented"
        ]
        if type(formal) is not bool:
            _fail("formal-chain fact is not exact boolean")
        if row["terminal_specific_independent_verifier_implemented"] is not (
            verifier_source is not None
        ):
            _fail("terminal verifier fact changed")
        if any(
            row[key] is not False
            for key in (
                "retained_portable_occurrence_bytes_in_v180",
                "fresh_v180_observed_occurrence_present",
                "v180_output_fixed_point_replayed",
            )
        ):
            _fail("readiness audit contains post-contract V180 outcomes")
        formal_count += int(formal)
        v9_count += int(formal and row["accounting_registry_version"] == "9.0.0")
    locks = audit.get("claim_locks")
    if (
        formal_count != 6
        or v9_count != 2
        or audit.get("prior_profile_formal_chain_implementation_count") != 6
        or audit.get("current_v9_formal_chain_implementation_count") != 2
        or audit.get("fresh_v180_observed_occurrence_count") != 0
        or audit.get("fresh_v180_missing_occurrence_count") != 10
        or audit.get("retained_v180_portable_occurrence_count") != 0
        or audit.get("historical_summary_promoted_to_v180_evidence") is not False
        or locks
        != {
            "all_path_native_accounting_complete": False,
            "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
            "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "official_execution_allowed": False,
        }
    ):
        _fail("V180 readiness counts or claim locks changed")
    payload = {
        "schema": "acfqp.all_path_formalization_verification.v180",
        "formalization_contract_id": EXPECTED_CONTRACT_ID,
        "formalization_readiness_audit_id": audit_id,
        "terminal_code_count": 10,
        "source_bytes_rehashed": True,
        "readiness_rows_reconstructed_without_producer_import": True,
        "prior_profile_formal_chain_implementation_count": 6,
        "current_v9_formal_chain_implementation_count": 2,
        "fresh_v180_observed_occurrence_count": 0,
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "official_execution_allowed": False,
    }
    verification_id = domains.extension_content_id_v180(
        domains.CONSTRUCTION_K7_VERIFICATION_V180_DOMAIN,
        payload,
    )
    if verification_id != EXPECTED_VERIFICATION_ID:
        _fail("V180 verification identity changed")
    document = {
        **payload,
        "formalization_verification_id": verification_id,
    }
    return AllPathFormalizationVerificationV180(
        _ISSUER,
        canonical_json_bytes(document),
        verification_id,
    )


__all__ = (
    "ConstructionK7AllPathFormalizationIndependentVerifierV180Error",
    "verify_all_path_formalization_readiness_independently_v180",
)
