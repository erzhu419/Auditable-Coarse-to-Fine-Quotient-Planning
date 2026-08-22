"""Freeze the V165 source-only paid-prefix identifiability audit."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Mapping, NoReturn

from acfqp.paid_prefix_profitability_identifiability_core_v165 import (
    build_paid_prefix_profitability_identifiability_audit_v165,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


V163_CAMPAIGN_ID = "193323db43d5524e5bebe3a1713e946ab7dbb77cf79307c957a13cded0d9c219"
V163_CAMPAIGN_BYTE_COUNT = 31_528_790
V163_CAMPAIGN_SHA256 = "9dab876ef04bd5b48698fdb9295aaf6efe1f6e3a51bd945fe84e449367aaa433"
V163_VERIFICATION_ID = (
    "5e856f8cab34726906f3e93924ea099d2027ee39aca0708efc5ebabec437975b"
)
V163_VERIFICATION_BYTE_COUNT = 28_544
V163_VERIFICATION_SHA256 = (
    "bd98840ef1a21d3897195e86093b0ed727acbb606dc544cd10df343d7dda002f"
)
V164_CAMPAIGN_ID = "108bc4cf4f61123c6da7812ae76a48c21027a3b5e32e80005952a93b2ab8da1c"
V164_CAMPAIGN_BYTE_COUNT = 33_323_896
V164_CAMPAIGN_SHA256 = "d964f250d8d6e0587cb80a1df50515ae9b74c319b0a4f5f24aee3cae262aa9f5"
V164_VERIFICATION_ID = (
    "1095eec978a045ac3fec2ef0848927ecf7ce3d290d68415656b28fe34b3f298f"
)
V164_VERIFICATION_BYTE_COUNT = 41_990
V164_VERIFICATION_SHA256 = (
    "91c6939851c37de8094be13bf113a17aef51abfc8379853af1f509559ea03be8"
)
AUDIT_ID = "8de483f4f827caddf96dd367b470aba6b8fef409f3cc060c4f3308fd592cbdeb"
EXPECTED_CANONICAL_BYTE_COUNT = 126_086
EXPECTED_CANONICAL_SHA256 = (
    "ebc57797a7b516d10d8a7a2d641b84a6d17621d47554c958235a1ec5981b8200"
)
SOURCE_ROOT = Path(__file__).resolve().parents[2]
SOURCE_PATHS = (
    "src/acfqp/construction_k7_domain_registry_extension_v165.py",
    "src/acfqp/paid_prefix_profitability_identifiability_core_v165.py",
)


class ConstructionK7PaidPrefixProfitabilityIdentifiabilityAuditV165Error(
    ValueError
):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7PaidPrefixProfitabilityIdentifiabilityAuditV165Error(message)


def _frozen(
    raw: bytes,
    *,
    count: int,
    digest: str,
    key: str,
    identity: str,
    label: str,
) -> Mapping[str, Any]:
    document = loads_canonical_json(raw)
    if not (
        canonical_json_bytes(document) == raw
        and len(raw) == count
        and hashlib.sha256(raw).hexdigest() == digest
        and document.get(key) == identity
    ):
        _fail(f"V165 frozen {label} changed")
    return document


def _source_facts() -> list[dict[str, Any]]:
    facts = []
    for relative_path in SOURCE_PATHS:
        raw = (SOURCE_ROOT / relative_path).read_bytes()
        facts.append(
            {
                "relative_path": relative_path,
                "byte_count": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
    return facts


def freeze_paid_prefix_profitability_identifiability_audit_v165(
    v163_campaign_raw: bytes,
    v163_verification_raw: bytes,
    v164_campaign_raw: bytes,
    v164_verification_raw: bytes,
) -> bytes:
    v163_campaign = _frozen(
        v163_campaign_raw,
        count=V163_CAMPAIGN_BYTE_COUNT,
        digest=V163_CAMPAIGN_SHA256,
        key="campaign_id",
        identity=V163_CAMPAIGN_ID,
        label="V163 campaign",
    )
    v163_verification = _frozen(
        v163_verification_raw,
        count=V163_VERIFICATION_BYTE_COUNT,
        digest=V163_VERIFICATION_SHA256,
        key="verification_id",
        identity=V163_VERIFICATION_ID,
        label="V163 verification",
    )
    v164_campaign = _frozen(
        v164_campaign_raw,
        count=V164_CAMPAIGN_BYTE_COUNT,
        digest=V164_CAMPAIGN_SHA256,
        key="campaign_id",
        identity=V164_CAMPAIGN_ID,
        label="V164 campaign",
    )
    v164_verification = _frozen(
        v164_verification_raw,
        count=V164_VERIFICATION_BYTE_COUNT,
        digest=V164_VERIFICATION_SHA256,
        key="verification_id",
        identity=V164_VERIFICATION_ID,
        label="V164 verification",
    )
    if not (
        v163_campaign["registered_gate"]["passed"] is True
        and v164_campaign["registered_gate"]["passed"] is True
        and v163_verification[
            "safe_query_and_factor_prior_sample_tax_evidence_independently_verified"
        ]
        is True
        and v164_verification[
            "query_and_factor_prior_sample_tax_replication_independently_verified"
        ]
        is True
    ):
        _fail("V165 source campaign semantics changed")
    audit = build_paid_prefix_profitability_identifiability_audit_v165(
        (v163_campaign, v164_campaign),
        source_campaign_ids=(V163_CAMPAIGN_ID, V164_CAMPAIGN_ID),
        source_verification_ids=(V163_VERIFICATION_ID, V164_VERIFICATION_ID),
        frozen_implementation_source_facts=_source_facts(),
    )
    if not (
        audit["source_occurrence_count"] == 20
        and audit["strictly_profitable_occurrence_count"] == 3
        and audit["zero_reduction_occurrence_count"] == 17
        and audit["mixed_profitability_signature_count"] >= 1
        and audit[
            "perfect_deterministic_classifier_exists_in_registered_signature_space"
        ]
        is False
        and audit["profitability_classifier_issued"] is False
        and audit["new_target_outcomes_accessed"] is False
    ):
        _fail("V165 registered identifiability conclusion changed")
    raw = canonical_json_bytes(audit)
    if AUDIT_ID != "0" * 64 and not (
        audit["audit_id"] == AUDIT_ID
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    ):
        _fail("V165 frozen audit changed")
    return raw


__all__ = (
    "AUDIT_ID",
    "freeze_paid_prefix_profitability_identifiability_audit_v165",
)
