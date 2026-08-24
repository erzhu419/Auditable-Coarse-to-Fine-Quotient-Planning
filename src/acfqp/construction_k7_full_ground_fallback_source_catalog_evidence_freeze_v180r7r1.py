"""Freeze the exact outcome-free V180r7r1 source-catalog manifest."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
from typing import Any

from acfqp import construction_k7_full_ground_fallback_source_inventory_preregistration_v180r7r1 as preregistration
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


EXPECTED_MANIFEST_ID = (
    "92e4f36212d957d3701591ee689a23e4446d942c4c3e3b562049290c19ad50d0"
)
EXPECTED_CANONICAL_BYTE_COUNT = 911_647
EXPECTED_CANONICAL_SHA256 = (
    "16dc6c70a266224b3fb59d0850c432d6996c72e1a5868340e3878c9fdffde66e"
)
EXPECTED_PREREGISTRATION_ID = (
    "30a0aa732e44389f9b246a3664bacf13f5465233c7a1e3a1782baac80dbf38b8"
)
EXPECTED_PREREGISTRATION_CANONICAL_SHA256 = (
    "dc9852248e583060b6bce18b0c1cf3ec16d41d7fd0e6e8e1b6850948137cedaa"
)
EXPECTED_SOURCE_BOUNDARY_COMMIT = (
    "0d9d32dcb2aa3652696ccc0b5010dfc39455e8af"
)
EXPECTED_SOURCE_BOUNDARY_TREE_ID = (
    "bcce9bdccbe041aa67f390fb7494892b8a704ac6"
)
EXPECTED_CATALOG_MODULE_COUNT = 1_955
EXPECTED_CATALOG_SOURCE_BYTE_COUNT = 49_484_313
EXPECTED_CATALOG_FACTS_SHA256 = (
    "b355f9ffeebca568568b222a8b7a7a664c415b92b670aee8e72d9620c1d046c0"
)
EXPECTED_REPAIR_ID = (
    "feb8f6034ef1da9050242fe4e112edb285b77bd63a87642196f8fbc7995544c8"
)
EXPECTED_ROOT_MODULE_COUNT = 151
EXPECTED_REACHABLE_MODULE_COUNT = 307
EXPECTED_REACHABLE_SOURCE_BYTE_COUNT = 15_129_926
EXPECTED_REACHABLE_FACTS_SHA256 = (
    "a087ecfac3bcd6132a2242a670b9c38273de3e7bd823b5687e8223a73069772d"
)
EXPECTED_SOURCE_CLOSURE_ID = (
    "ac3f10ef4eea5c0ecc740d9cecc1991e851a65af198e6696f32bde1965feeb4b"
)
EXPECTED_PRODUCER_RELATIVE_PATH = (
    "scripts/preregister_v180r7r1_source_catalog_manifest.py"
)
EXPECTED_PRODUCER_BYTE_COUNT = 11_775
EXPECTED_PRODUCER_SHA256 = (
    "ec8743212aff87e33861d070274f59285f21f246caf04086ae989c98cc8bb86b"
)

_MANIFEST_DOMAIN = (
    "acfqp:construction-k7-full-ground-fallback-source-catalog-manifest:"
    "v180r7r1"
)
_REPAIR_DOMAIN = (
    "acfqp:construction-k7-full-ground-fallback-source-closure-repair:"
    "v180r7r1"
)
_CLOSURE_DOMAIN = "acfqp:v075-construction-source-closure:v2"

_MANIFEST_FIELDS = {
    "COUNTER_COMPLETENESS_GATE",
    "WORKLOAD_ECONOMICS_GATE",
    "construction_only",
    "directory_fsync_required",
    "file_fsync_required",
    "fresh_execution_authorization_issued",
    "fresh_fallback_execution_started",
    "manifest_identity_hardcoded_in_catalogued_source",
    "manifest_output_relative_path",
    "manifest_producer_source_fact",
    "official_N_break_even",
    "official_execution_allowed",
    "official_scalar_cost",
    "producer_free_verification_present",
    "production_outcome_accessed",
    "same_manifest_identity_rerun_after_progress_forbidden",
    "schema",
    "scientific_occurrence_executed",
    "source_boundary_commit",
    "source_boundary_tree_id",
    "source_catalog_facts",
    "source_catalog_facts_sha256",
    "source_catalog_manifest_domain",
    "source_catalog_manifest_id",
    "source_catalog_module_count",
    "source_catalog_source_byte_count",
    "source_closure_repair",
    "source_closure_repair_id",
    "source_inventory_preregistration_canonical_sha256",
    "source_inventory_preregistration_id",
    "source_root_relative_path",
    "success_claimed",
    "write_once_o_excl_required",
}


class FullGroundFallbackSourceCatalogEvidenceFreezeV180r7r1Error(ValueError):
    """The retained manifest or one of its exact identities changed."""


def _content_id(domain: str, payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        domain.encode() + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


def _exact_embedded_id(
    document: dict[str, Any], *, identity_field: str, domain: str
) -> str:
    payload = dict(document)
    identity = payload.pop(identity_field, None)
    if type(identity) is not str or identity != _content_id(domain, payload):
        raise FullGroundFallbackSourceCatalogEvidenceFreezeV180r7r1Error(
            f"retained {identity_field} changed"
        )
    return identity


@dataclass(frozen=True, slots=True)
class FrozenFullGroundFallbackSourceCatalogV180r7r1:
    canonical_bytes: bytes
    manifest_id: str
    repair_id: str

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:
            raise FullGroundFallbackSourceCatalogEvidenceFreezeV180r7r1Error(
                "retained source-catalog manifest is not one document"
            )
        return document


def load_frozen_full_ground_fallback_source_catalog_manifest_v180r7r1(
) -> FrozenFullGroundFallbackSourceCatalogV180r7r1:
    root = Path(__file__).resolve().parents[2]
    path = root / ".tmp" / "exact-freeze" / "v180r7r1_source_catalog_manifest.json"
    raw = path.read_bytes()
    document = loads_canonical_json(raw)
    if type(document) is not dict:
        raise FullGroundFallbackSourceCatalogEvidenceFreezeV180r7r1Error(
            "retained source-catalog manifest is not one document"
        )
    if not (
        canonical_json_bytes(document) == raw
        and set(document) == _MANIFEST_FIELDS
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
        and document["source_catalog_manifest_id"] == EXPECTED_MANIFEST_ID
        and _exact_embedded_id(
            document,
            identity_field="source_catalog_manifest_id",
            domain=_MANIFEST_DOMAIN,
        )
        == EXPECTED_MANIFEST_ID
        and document["source_catalog_manifest_domain"] == _MANIFEST_DOMAIN
        and document["source_boundary_commit"]
        == EXPECTED_SOURCE_BOUNDARY_COMMIT
        and document["source_boundary_tree_id"] == EXPECTED_SOURCE_BOUNDARY_TREE_ID
        and document["source_inventory_preregistration_id"]
        == EXPECTED_PREREGISTRATION_ID
        and document["source_inventory_preregistration_canonical_sha256"]
        == EXPECTED_PREREGISTRATION_CANONICAL_SHA256
        and document["source_catalog_module_count"]
        == EXPECTED_CATALOG_MODULE_COUNT
        and document["source_catalog_source_byte_count"]
        == EXPECTED_CATALOG_SOURCE_BYTE_COUNT
        and document["source_catalog_facts_sha256"]
        == EXPECTED_CATALOG_FACTS_SHA256
    ):
        raise FullGroundFallbackSourceCatalogEvidenceFreezeV180r7r1Error(
            "retained source-catalog manifest identity changed"
        )

    facts = document["source_catalog_facts"]
    if not (
        type(facts) is list
        and len(facts) == EXPECTED_CATALOG_MODULE_COUNT
        and all(
            type(row) is dict
            and set(row)
            == {
                "module_name",
                "relative_path",
                "source_byte_count",
                "source_sha256",
            }
            and type(row["module_name"]) is str
            and type(row["relative_path"]) is str
            and type(row["source_byte_count"]) is int
            and row["source_byte_count"] > 0
            and type(row["source_sha256"]) is str
            and len(row["source_sha256"]) == 64
            for row in facts
        )
        and [row["module_name"] for row in facts]
        == sorted({row["module_name"] for row in facts})
        and sum(row["source_byte_count"] for row in facts)
        == EXPECTED_CATALOG_SOURCE_BYTE_COUNT
        and hashlib.sha256(canonical_json_bytes(facts)).hexdigest()
        == EXPECTED_CATALOG_FACTS_SHA256
    ):
        raise FullGroundFallbackSourceCatalogEvidenceFreezeV180r7r1Error(
            "retained source-catalog facts changed"
        )

    repair = document["source_closure_repair"]
    if type(repair) is not dict:
        raise FullGroundFallbackSourceCatalogEvidenceFreezeV180r7r1Error(
            "retained source-closure repair is not one document"
        )
    repair_id = _exact_embedded_id(
        repair,
        identity_field="source_closure_repair_id",
        domain=_REPAIR_DOMAIN,
    )
    candidate = repair["candidate_catalog"]
    reachable = repair["reachable_runtime"]
    closure = repair["source_closure"]
    if not (
        document["source_closure_repair_id"] == EXPECTED_REPAIR_ID
        and repair_id == EXPECTED_REPAIR_ID
        and type(candidate) is dict
        and candidate["module_count"] == EXPECTED_CATALOG_MODULE_COUNT
        and candidate["source_byte_count"] == EXPECTED_CATALOG_SOURCE_BYTE_COUNT
        and candidate["source_facts_sha256"] == EXPECTED_CATALOG_FACTS_SHA256
        and type(repair["root_modules"]) is list
        and len(repair["root_modules"]) == EXPECTED_ROOT_MODULE_COUNT
        and type(reachable) is dict
        and reachable["module_count"] == EXPECTED_REACHABLE_MODULE_COUNT
        and reachable["source_byte_count"]
        == EXPECTED_REACHABLE_SOURCE_BYTE_COUNT
        and reachable["source_facts_sha256"]
        == EXPECTED_REACHABLE_FACTS_SHA256
        and type(closure) is dict
        and closure["closure_id"] == EXPECTED_SOURCE_CLOSURE_ID
        and closure["module_count"] == EXPECTED_REACHABLE_MODULE_COUNT
        and _exact_embedded_id(
            closure,
            identity_field="closure_id",
            domain=_CLOSURE_DOMAIN,
        )
        == EXPECTED_SOURCE_CLOSURE_ID
        and repair["scientific_occurrence_executed"] is False
        and repair["target_outcomes_accessed"] is False
        and repair["official_execution_allowed"] is False
    ):
        raise FullGroundFallbackSourceCatalogEvidenceFreezeV180r7r1Error(
            "retained source-closure repair facts changed"
        )

    producer = document["manifest_producer_source_fact"]
    producer_path = root / EXPECTED_PRODUCER_RELATIVE_PATH
    producer_raw = producer_path.read_bytes()
    if not (
        producer
        == {
            "relative_path": EXPECTED_PRODUCER_RELATIVE_PATH,
            "byte_count": EXPECTED_PRODUCER_BYTE_COUNT,
            "sha256": EXPECTED_PRODUCER_SHA256,
            "excluded_from_frozen_worker_source_catalog": True,
        }
        and len(producer_raw) == EXPECTED_PRODUCER_BYTE_COUNT
        and hashlib.sha256(producer_raw).hexdigest() == EXPECTED_PRODUCER_SHA256
    ):
        raise FullGroundFallbackSourceCatalogEvidenceFreezeV180r7r1Error(
            "retained manifest producer source changed"
        )

    frozen_preregistration = (
        preregistration.freeze_full_ground_fallback_source_inventory_preregistration_v180r7r1()
    )
    if not (
        frozen_preregistration.preregistration_id == EXPECTED_PREREGISTRATION_ID
        and hashlib.sha256(frozen_preregistration.canonical_bytes).hexdigest()
        == EXPECTED_PREREGISTRATION_CANONICAL_SHA256
        and document["schema"]
        == "acfqp.full_ground_fallback_source_catalog_manifest.v180r7r1"
        and document["source_root_relative_path"] == "src/acfqp"
        and document["manifest_output_relative_path"]
        == ".tmp/exact-freeze/v180r7r1_source_catalog_manifest.json"
        and document["manifest_identity_hardcoded_in_catalogued_source"] is False
        and document["write_once_o_excl_required"] is True
        and document["file_fsync_required"] is True
        and document["directory_fsync_required"] is True
        and document["same_manifest_identity_rerun_after_progress_forbidden"]
        is True
        and document["fresh_execution_authorization_issued"] is False
        and document["fresh_fallback_execution_started"] is False
        and document["scientific_occurrence_executed"] is False
        and document["production_outcome_accessed"] is False
        and document["producer_free_verification_present"] is False
        and document["success_claimed"] is False
        and document["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
        and document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
        and document["official_scalar_cost"] is None
        and document["official_N_break_even"] is None
        and document["official_execution_allowed"] is False
        and document["construction_only"] is True
    ):
        raise FullGroundFallbackSourceCatalogEvidenceFreezeV180r7r1Error(
            "retained source-catalog claim locks changed"
        )
    return FrozenFullGroundFallbackSourceCatalogV180r7r1(
        raw,
        EXPECTED_MANIFEST_ID,
        EXPECTED_REPAIR_ID,
    )


__all__ = (
    "EXPECTED_CANONICAL_BYTE_COUNT",
    "EXPECTED_CANONICAL_SHA256",
    "EXPECTED_CATALOG_FACTS_SHA256",
    "EXPECTED_MANIFEST_ID",
    "EXPECTED_REPAIR_ID",
    "FrozenFullGroundFallbackSourceCatalogV180r7r1",
    "FullGroundFallbackSourceCatalogEvidenceFreezeV180r7r1Error",
    "load_frozen_full_ground_fallback_source_catalog_manifest_v180r7r1",
)
