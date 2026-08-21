"""Producer-free verification of the V132 opaque source-archive dictionary."""

from __future__ import annotations

from collections import defaultdict
import hashlib
from typing import Any, Iterable, NoReturn

from acfqp import construction_k7_domain_registry_extension_v59 as domains59
from acfqp import construction_k7_domain_registry_extension_v132 as domains
from acfqp.generic_artifact_subprogram_instantiator_v121 import _symbols
from acfqp.generic_bit_codelength_universal_synthesizer_v14 import (
    _ast_bits,
    _unsigned_gamma_bits,
    _utf8_bits,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


FROZEN_DICTIONARY_ID = "10094aa8ced24dadc18cef22bd21587e54d44215e86fd3d6633b28c9e6d32836"
FROZEN_DICTIONARY_BYTE_COUNT = 6_774
FROZEN_DICTIONARY_SHA256 = "5daa55fef0366594bb566874578bf90c8a6033394be39d07d2f47056d42e5ed9"

VERIFICATION_ID = "6243d44117a941566aad18439c9c6f167d8d3688090c911f752269ee455abaf3"
EXPECTED_CANONICAL_BYTE_COUNT = 2_193
EXPECTED_CANONICAL_SHA256 = "437719c2698d31d2caf5608b44362a33b79e62db6d79a7ad9ec7762ea8a69eb0"


class OpaqueSourceArchiveIndependentVerifierV132Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise OpaqueSourceArchiveIndependentVerifierV132Error(message)


def _candidates(document: Any) -> list[dict[str, Any]]:
    found: dict[str, dict[str, Any]] = {}

    def visit(value: Any) -> None:
        if type(value) is dict:
            if value.get("schema") == "acfqp.generic_partial_factor_candidate.v15":
                identity = value.get("candidate_id")
                payload = {key: item for key, item in value.items() if key != "candidate_id"}
                if (
                    type(identity) is not str
                    or identity
                    != domains59.extension_content_id_v59(
                        domains59.CONSTRUCTION_K7_TRUE_BIT_SYMMETRIC_ACQUISITION_V59_DOMAIN,
                        payload,
                    )
                ):
                    _fail("V132 source candidate identity changed")
                prior = found.setdefault(identity, value)
                if prior != value:
                    _fail("V132 repeated candidate bytes changed")
            for item in value.values():
                visit(item)
        elif type(value) is list:
            for item in value:
                visit(item)

    visit(document)
    return [found[key] for key in sorted(found)]


def _normalize(expression: Any, target: int) -> Any:
    action_fields: dict[int, int] = {}
    state_columns: dict[int, int] = {}

    def visit(value: Any) -> Any:
        if type(value) is not list or not value:
            return value
        if value[0] == "E00":
            if value[1] == target:
                return ["S", "SELF"]
            state_columns.setdefault(value[1], len(state_columns))
            return ["S", state_columns[value[1]]]
        if value[0] == "E01":
            action_fields.setdefault(value[1], len(action_fields))
            return ["A", action_fields[value[1]]]
        return [value[0], *(visit(item) for item in value[1:])]

    return visit(expression)


def _binding_bits(expression: Any) -> int:
    symbols = _symbols(expression)
    return _unsigned_gamma_bits(len(symbols)) + sum(
        1 + _unsigned_gamma_bits(index) for _kind, index in symbols
    )


def _derive_opaque_source_archive_dictionary_independent_v132(
    source_artifact_bytes: Iterable[bytes],
    *,
    minimum_distinct_artifact_support: int = 3,
    minimum_distinct_schema_pair_support: int = 2,
) -> dict[str, Any]:
    raw_rows = tuple(source_artifact_bytes)
    if (
        len(raw_rows) < minimum_distinct_artifact_support + 1
        or minimum_distinct_artifact_support < 2
        or minimum_distinct_schema_pair_support < 2
        or any(type(raw) is not bytes for raw in raw_rows)
    ):
        _fail("V132 opaque source archive contract changed")
    artifacts = []
    seen_campaign_ids = set()
    seen_hashes = set()
    for raw in raw_rows:
        document = loads_canonical_json(raw)
        digest = hashlib.sha256(raw).hexdigest()
        campaign_id = document.get("campaign_id")
        candidates = _candidates(document)
        if (
            canonical_json_bytes(document) != raw
            or type(campaign_id) is not str
            or len(campaign_id) != 64
            or document.get("registered_gate", {}).get("passed") is not True
            or not candidates
            or campaign_id in seen_campaign_ids
            or digest in seen_hashes
        ):
            _fail("V132 opaque source artifact changed")
        seen_campaign_ids.add(campaign_id)
        seen_hashes.add(digest)
        artifacts.append(
            {
                "artifact_sha256": digest,
                "byte_count": len(raw),
                "campaign_id": campaign_id,
                "document": document,
                "candidates": candidates,
            }
        )
    artifacts.sort(key=lambda row: row["artifact_sha256"])
    normalized: dict[str, tuple[str, Any]] = {}
    origins: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for artifact in artifacts:
        for candidate in artifact["candidates"]:
            width = candidate.get("state_width")
            action_width = candidate.get("action_field_width")
            assignments = candidate.get("compiled_factor_assignments")
            if (
                type(width) is not int
                or type(action_width) is not int
                or type(assignments) is not list
                or not assignments
            ):
                _fail("V132 source candidate shape changed")
            for assignment in assignments:
                target = assignment.get("target_column")
                result_type = assignment.get("result_type")
                expression = assignment.get("expression")
                if (
                    type(target) is not int
                    or result_type not in {"INT", "FINITE_INT_SUPPORT"}
                    or type(expression) is not list
                ):
                    _fail("V132 source assignment changed")
                expression = _normalize(expression, target)
                signature_payload = {
                    "result_type": result_type,
                    "normalized_expression": expression,
                }
                signature = hashlib.sha256(
                    canonical_json_bytes(signature_payload)
                ).hexdigest()
                prior = normalized.setdefault(signature, (result_type, expression))
                if prior != (result_type, expression):
                    _fail("V132 normalized signature collision")
                origins[signature].append(
                    {
                        "source_artifact_sha256": artifact["artifact_sha256"],
                        "source_campaign_id": artifact["campaign_id"],
                        "source_candidate_id": candidate["candidate_id"],
                        "source_schema_pair": [width, action_width],
                        "source_target_column": target,
                    }
                )
    selected = []
    support_rows = []
    for signature in sorted(origins):
        result_type, expression = normalized[signature]
        rows = sorted(origins[signature], key=canonical_json_bytes)
        artifact_ids = sorted({row["source_artifact_sha256"] for row in rows})
        schema_pairs = sorted({tuple(row["source_schema_pair"]) for row in rows})
        holdouts = []
        for holdout in artifact_ids:
            retained = [row for row in rows if row["source_artifact_sha256"] != holdout]
            retained_artifacts = {row["source_artifact_sha256"] for row in retained}
            retained_pairs = {tuple(row["source_schema_pair"]) for row in retained}
            generic_bits = len(retained) * (1 + _ast_bits(expression))
            dictionary_bits = (
                _unsigned_gamma_bits(1)
                + _utf8_bits(result_type)
                + _ast_bits(expression)
                + len(retained) * (2 + _binding_bits(expression))
            )
            holdouts.append(
                {
                    "held_out_source_artifact_sha256": holdout,
                    "retained_artifact_count": len(retained_artifacts),
                    "retained_schema_pair_count": len(retained_pairs),
                    "singleton_dictionary_prefix_gain_bits": generic_bits
                    - dictionary_bits,
                    "eligible": (
                        len(retained_artifacts) >= minimum_distinct_artifact_support
                        and len(retained_pairs) >= minimum_distinct_schema_pair_support
                        and generic_bits > dictionary_bits
                    ),
                }
            )
        eligible = (
            len(artifact_ids) >= minimum_distinct_artifact_support + 1
            and len(schema_pairs) >= minimum_distinct_schema_pair_support
            and all(row["eligible"] for row in holdouts)
        )
        if eligible:
            selected.append(
                {
                    "signature_sha256": signature,
                    "result_type": result_type,
                    "normalized_expression": expression,
                    "source_schema_pairs": [list(pair) for pair in schema_pairs],
                }
            )
        support_rows.append(
            {
                "signature_sha256": signature,
                "distinct_source_artifact_count": len(artifact_ids),
                "distinct_schema_pair_count": len(schema_pairs),
                "origin_count": len(rows),
                "leave_one_artifact_reconstructions": holdouts,
                "selected": eligible,
            }
        )
    if not selected:
        _fail("V132 opaque archive selected no reusable factor")
    payload = {
        "schema": "acfqp.opaque_source_archive_factor_dictionary.v132",
        "source_archive": [
            {
                "artifact_sha256": row["artifact_sha256"],
                "byte_count": row["byte_count"],
                "campaign_id": row["campaign_id"],
                "unique_partial_candidate_count": len(row["candidates"]),
            }
            for row in artifacts
        ],
        "source_archive_cardinality": len(artifacts),
        "minimum_distinct_artifact_support": minimum_distinct_artifact_support,
        "minimum_distinct_schema_pair_support": minimum_distinct_schema_pair_support,
        "selected_template_count": len(selected),
        "selected_subprograms": selected,
        "support_and_leave_one_artifact_evidence": support_rows,
        "source_aliases_or_version_names_consumed": False,
        "fixed_source_archive_cardinality_required_by_synthesizer": False,
        "fixed_source_campaign_inventory_embedded_in_synthesizer": False,
        "selection_rule": (
            "OPAQUE_CONTENT_ADDRESSED_SUPPORT_PLUS_EVERY_LEAVE_ONE_ARTIFACT_"
            "POSITIVE_SINGLETON_PREFIX_GAIN"
        ),
        "target_occurrences_accessed": False,
        "target_outcomes_accessed": False,
        "semantic_family_names_used_for_selection": False,
        "complete_world_model_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    dictionary_id = domains.extension_content_id_v132(
        domains.CONSTRUCTION_K7_OPAQUE_SOURCE_ARCHIVE_DICTIONARY_V132_DOMAIN,
        payload,
    )
    return {
        **payload,
        "dictionary_id": dictionary_id,
        "v15_partial_synthesizer_projection": {
            "schema": "acfqp.cross_schema_factor_template_projection.v15",
            "source_factor_library_id": dictionary_id,
            "cross_schema_subprograms": selected,
            "target_slot_inventory_supplied": False,
            "semantic_names_supplied": False,
        },
    }


def freeze_opaque_source_archive_verification_v132(
    dictionary_raw: bytes,
    source_artifact_bytes: Iterable[bytes],
) -> bytes:
    if type(dictionary_raw) is not bytes:
        _fail("V132 dictionary bytes changed")
    dictionary = loads_canonical_json(dictionary_raw)
    reconstructed = _derive_opaque_source_archive_dictionary_independent_v132(
        source_artifact_bytes
    )
    if (
        canonical_json_bytes(dictionary) != dictionary_raw
        or dictionary != reconstructed
        or dictionary.get("dictionary_id") != FROZEN_DICTIONARY_ID
        or len(dictionary_raw) != FROZEN_DICTIONARY_BYTE_COUNT
        or hashlib.sha256(dictionary_raw).hexdigest() != FROZEN_DICTIONARY_SHA256
    ):
        _fail("V132 frozen dictionary did not reproduce independently")
    selected = reconstructed["selected_subprograms"]
    support = reconstructed["support_and_leave_one_artifact_evidence"]
    if (
        len(selected) != 3
        or reconstructed["source_archive_cardinality"] != 4
        or not all(
            holdout["eligible"]
            for row in support
            if row["selected"]
            for holdout in row["leave_one_artifact_reconstructions"]
        )
    ):
        _fail("V132 registered reconstruction gate changed")
    payload = {
        "schema": "acfqp.opaque_source_archive_factor_dictionary_verification.v132",
        "dictionary_id": FROZEN_DICTIONARY_ID,
        "dictionary_byte_count": FROZEN_DICTIONARY_BYTE_COUNT,
        "dictionary_sha256": FROZEN_DICTIONARY_SHA256,
        "source_archive": reconstructed["source_archive"],
        "source_archive_cardinality": reconstructed["source_archive_cardinality"],
        "selected_template_count": len(selected),
        "selected_template_signatures": [
            row["signature_sha256"] for row in selected
        ],
        "producer_free_dictionary_reconstruction": True,
        "opaque_content_addressed_archive_reconstruction": True,
        "variable_source_archive_cardinality_supported_by_synthesizer": True,
        "fixed_source_campaign_inventory_embedded_in_verifier": False,
        "source_aliases_or_version_names_consumed": False,
        "every_selected_template_leave_one_artifact_positive_gain_verified": True,
        "target_occurrences_accessed": False,
        "target_outcomes_accessed": False,
        "complete_world_model_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    verification_id = domains.extension_content_id_v132(
        domains.CONSTRUCTION_K7_OPAQUE_SOURCE_ARCHIVE_VERIFICATION_V132_DOMAIN,
        payload,
    )
    raw = canonical_json_bytes({**payload, "verification_id": verification_id})
    if VERIFICATION_ID != "0" * 64 and (
        verification_id != VERIFICATION_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("V132 frozen independent verification changed")
    return raw


__all__ = (
    "EXPECTED_CANONICAL_BYTE_COUNT",
    "EXPECTED_CANONICAL_SHA256",
    "VERIFICATION_ID",
    "freeze_opaque_source_archive_verification_v132",
)
