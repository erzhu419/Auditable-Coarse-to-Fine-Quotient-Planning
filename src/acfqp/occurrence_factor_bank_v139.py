"""Derive a reusable factor bank from independently seeded occurrences."""

from __future__ import annotations

from collections import defaultdict
import hashlib
from typing import Any, Iterable, NoReturn

from acfqp import construction_k7_domain_registry_extension_v139 as domains
from acfqp.generic_artifact_subprogram_instantiator_v121 import _symbols
from acfqp.generic_bit_codelength_universal_synthesizer_v14 import (
    _ast_bits,
    _unsigned_gamma_bits,
    _utf8_bits,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


BANK_ID = "9805a056c51adb2432e79992133ae1a27a7d17ce871893d0897f9f3cb65a8d12"
EXPECTED_CANONICAL_BYTE_COUNT = 10_555
EXPECTED_CANONICAL_SHA256 = (
    "5bf20a04e3321584fd2b2aa454305f1ec7ea85c8dce09e40674db613c0e30c21"
)

_CAMPAIGN_DOMAINS = {
    "acfqp.packet_batching_source_unseen_transfer_campaign.v134": (
        "acfqp:construction-k7-packet-batching-transfer-campaign:v134"
    ),
    "acfqp.auto_calibrated_archive_planning_campaign.v136": (
        "acfqp:construction-k7-auto-calibrated-archive-campaign:v136"
    ),
    "acfqp.heterogeneous_cohort_planning_campaign.v138": (
        "acfqp:construction-k7-heterogeneous-cohort-campaign:v138"
    ),
}
_OCCURRENCE_DOMAINS = {
    "acfqp.packet_batching_source_unseen_transfer_occurrence.v134": (
        "acfqp:construction-k7-packet-batching-transfer-occurrence:v134"
    ),
    "acfqp.auto_calibrated_archive_planning_occurrence.v136": (
        "acfqp:construction-k7-auto-calibrated-archive-occurrence:v136"
    ),
    "acfqp.heterogeneous_cohort_planning_occurrence.v138": (
        "acfqp:construction-k7-heterogeneous-cohort-occurrence:v138"
    ),
}
_ROBUST_CANDIDATE_DOMAIN = (
    "acfqp:construction-k7-robust-dictionary-factor-prior-candidate:v131r2"
)


class OccurrenceFactorBankV139Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise OccurrenceFactorBankV139Error(message)


def _content_id(domain: str, payload: Any) -> str:
    return hashlib.sha256(
        domain.encode() + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


def _verify_id(document: dict[str, Any], key: str, domain: str) -> None:
    payload = {name: value for name, value in document.items() if name != key}
    if document.get(key) != _content_id(domain, payload):
        _fail(f"V139 {key} changed")


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


def _occurrences(campaign_bytes: Iterable[bytes]) -> list[dict[str, Any]]:
    units = []
    seen_campaigns = set()
    seen_occurrences = set()
    for raw in campaign_bytes:
        if type(raw) is not bytes:
            _fail("V139 campaign bytes changed")
        campaign = loads_canonical_json(raw)
        schema = campaign.get("schema")
        domain = _CAMPAIGN_DOMAINS.get(schema)
        if (
            canonical_json_bytes(campaign) != raw
            or domain is None
            or campaign.get("registered_gate", {}).get("passed") is not True
        ):
            _fail("V139 source campaign changed")
        _verify_id(campaign, "campaign_id", domain)
        campaign_id = campaign["campaign_id"]
        if campaign_id in seen_campaigns:
            _fail("V139 duplicate source campaign")
        seen_campaigns.add(campaign_id)
        for occurrence in campaign.get("target_occurrences", ()):
            occurrence_domain = _OCCURRENCE_DOMAINS.get(occurrence.get("schema"))
            if (
                occurrence_domain is None
                or occurrence.get("registered_gate", {}).get("passed") is not True
            ):
                _fail("V139 source occurrence changed")
            _verify_id(occurrence, "occurrence_id", occurrence_domain)
            occurrence_id = occurrence["occurrence_id"]
            if occurrence_id in seen_occurrences:
                _fail("V139 duplicate source occurrence")
            seen_occurrences.add(occurrence_id)
            acquisition = occurrence.get("strict_no_prior_acquisition")
            candidate = acquisition.get("candidate") if type(acquisition) is dict else None
            if (
                type(candidate) is not dict
                or candidate.get("schema")
                != "acfqp.robust_dictionary_generic_partial_factor_candidate.v131r2"
            ):
                _fail("V139 robust candidate missing")
            _verify_id(candidate, "candidate_id", _ROBUST_CANDIDATE_DOMAIN)
            units.append(
                {
                    "source_campaign_id": campaign_id,
                    "source_campaign_sha256": hashlib.sha256(raw).hexdigest(),
                    "source_occurrence_id": occurrence_id,
                    "source_seed": occurrence["seed"],
                    "state_width": candidate["state_width"],
                    "action_field_width": candidate["action_field_width"],
                    "candidate": candidate,
                }
            )
    units.sort(key=lambda row: row["source_occurrence_id"])
    if len(units) < 8:
        _fail("V139 occurrence archive is too small")
    return units


def derive_occurrence_factor_bank_v139(
    campaign_bytes: Iterable[bytes],
) -> dict[str, Any]:
    units = _occurrences(campaign_bytes)
    normalized: dict[str, tuple[str, Any]] = {}
    origins: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for unit in units:
        candidate = unit["candidate"]
        for assignment in candidate["compiled_factor_assignments"]:
            target = assignment["target_column"]
            result_type = assignment["result_type"]
            expression = _normalize(assignment["expression"], target)
            signature_payload = {
                "result_type": result_type,
                "normalized_expression": expression,
            }
            signature = hashlib.sha256(
                canonical_json_bytes(signature_payload)
            ).hexdigest()
            prior = normalized.setdefault(signature, (result_type, expression))
            if prior != (result_type, expression):
                _fail("V139 normalized signature collision")
            origins[signature].append(
                {
                    "source_occurrence_id": unit["source_occurrence_id"],
                    "source_campaign_id": unit["source_campaign_id"],
                    "source_schema_pair": [
                        unit["state_width"],
                        unit["action_field_width"],
                    ],
                    "source_target_column": target,
                }
            )
    search_rows = []
    candidates = []
    for minimum_support in range(3, len(units)):
        selected = []
        gains = []
        for signature in sorted(origins):
            result_type, expression = normalized[signature]
            rows = sorted(origins[signature], key=canonical_json_bytes)
            occurrence_ids = sorted({row["source_occurrence_id"] for row in rows})
            schema_pairs = sorted({tuple(row["source_schema_pair"]) for row in rows})
            holdout_gains = []
            for holdout in occurrence_ids:
                retained = [
                    row for row in rows if row["source_occurrence_id"] != holdout
                ]
                generic_bits = len(retained) * (1 + _ast_bits(expression))
                dictionary_bits = (
                    _unsigned_gamma_bits(1)
                    + _utf8_bits(result_type)
                    + _ast_bits(expression)
                    + len(retained) * (2 + _binding_bits(expression))
                )
                holdout_gains.append(generic_bits - dictionary_bits)
            if (
                len(occurrence_ids) >= minimum_support + 1
                and holdout_gains
                and min(holdout_gains) > 0
            ):
                selected.append(
                    {
                        "signature_sha256": signature,
                        "result_type": result_type,
                        "normalized_expression": expression,
                        "source_schema_pairs": [list(pair) for pair in schema_pairs],
                        "transfer_scope": (
                            "CROSS_SCHEMA"
                            if len(schema_pairs) >= 2
                            else "STRUCTURAL_SCHEMA_PAIR"
                        ),
                    }
                )
                gains.append(min(holdout_gains))
        score = sum(gains)
        row = {
            "minimum_distinct_occurrence_support": minimum_support,
            "selected_template_count": len(selected),
            "selected_cross_schema_template_count": sum(
                item["transfer_scope"] == "CROSS_SCHEMA" for item in selected
            ),
            "selected_structural_schema_pair_template_count": sum(
                item["transfer_scope"] == "STRUCTURAL_SCHEMA_PAIR"
                for item in selected
            ),
            "summed_weakest_leave_one_occurrence_prefix_gain_bits": score,
        }
        search_rows.append(row)
        if selected:
            candidates.append((row, selected))
    if not candidates:
        _fail("V139 occurrence archive selected no reusable factor")
    selected_row, selected = min(
        candidates,
        key=lambda item: (
            -item[0]["summed_weakest_leave_one_occurrence_prefix_gain_bits"],
            -item[0]["minimum_distinct_occurrence_support"],
            canonical_json_bytes(item[1]),
        ),
    )
    archive = [
        {
            key: value
            for key, value in unit.items()
            if key != "candidate"
        }
        | {"candidate_id": unit["candidate"]["candidate_id"]}
        for unit in units
    ]
    payload = {
        "schema": "acfqp.occurrence_granular_factor_bank.v139",
        "source_occurrence_archive": archive,
        "source_occurrence_archive_cardinality": len(archive),
        "support_threshold_search_rows": search_rows,
        "selected_minimum_distinct_occurrence_support": selected_row[
            "minimum_distinct_occurrence_support"
        ],
        "selected_template_count": len(selected),
        "selected_cross_schema_template_count": selected_row[
            "selected_cross_schema_template_count"
        ],
        "selected_structural_schema_pair_template_count": selected_row[
            "selected_structural_schema_pair_template_count"
        ],
        "selected_summed_weakest_leave_one_occurrence_prefix_gain_bits": selected_row[
            "summed_weakest_leave_one_occurrence_prefix_gain_bits"
        ],
        "selected_subprograms": selected,
        "robust_candidate_schema_decoded": True,
        "occurrence_support_not_campaign_container_support": True,
        "semantic_family_names_used_for_selection": False,
        "new_target_occurrences_accessed": False,
        "new_target_outcomes_accessed": False,
        "complete_world_model_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    bank_id = domains.extension_content_id_v139(
        domains.CONSTRUCTION_K7_OCCURRENCE_FACTOR_BANK_V139_DOMAIN,
        payload,
    )
    return {
        **payload,
        "bank_id": bank_id,
        "v15_partial_synthesizer_projection": {
            "schema": "acfqp.cross_schema_factor_template_projection.v15",
            "source_factor_library_id": bank_id,
            "cross_schema_subprograms": selected,
            "target_slot_inventory_supplied": False,
            "semantic_names_supplied": False,
        },
    }


def freeze_occurrence_factor_bank_v139(campaign_bytes: Iterable[bytes]) -> bytes:
    document = derive_occurrence_factor_bank_v139(campaign_bytes)
    raw = canonical_json_bytes(document)
    if BANK_ID != "0" * 64 and (
        document["bank_id"] != BANK_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("V139 frozen occurrence factor bank changed")
    return raw


__all__ = (
    "BANK_ID",
    "derive_occurrence_factor_bank_v139",
    "freeze_occurrence_factor_bank_v139",
)
