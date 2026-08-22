"""Derive occurrence-portable E03/E04 templates from verified V145 candidates."""

from __future__ import annotations

from collections import defaultdict
import hashlib
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v146 as domains
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "24a50acc5cf553f4fc457e17aa4ffff0fc6b6b9ebe08fa0d54076d998c3eeaa9"
CAMPAIGN_BYTE_COUNT = 17_516_246
CAMPAIGN_SHA256 = "5584aa76043f76d69b72ec189bc67a3952e758bbaaad33025b73dc859851f33c"
VERIFICATION_ID = "0924f57684bdeae9b9da339d949f9ab2f00949b5684817621eae26497adc3d7c"
VERIFICATION_BYTE_COUNT = 12_863
VERIFICATION_SHA256 = "f363feba0e5e5c6a12c0f6f709f9c0f4fe55b0e3113b907005e4eb8f77bbcb13"
BANK_ID = "78bb4dae4682ed0cedb7a7781caca4af04986f0db86d7086a0786166d07020b5"
EXPECTED_CANONICAL_BYTE_COUNT = 4_033
EXPECTED_CANONICAL_SHA256 = "eb733aad5d7b5aed20933366ba4b6f8c9d24338b20a4437ef11ffbf4f0a99fe6"
_CAMPAIGN_DOMAIN = "acfqp:construction-k7-certificate-local-recovery-union-campaign:v145"
_OCCURRENCE_DOMAIN = "acfqp:construction-k7-certificate-local-recovery-union-occurrence:v145"
_CANDIDATE_DOMAIN = "acfqp:construction-k7-robust-dictionary-factor-prior-candidate:v131r2"


class AnonymousRelationalFactorBankV146Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise AnonymousRelationalFactorBankV146Error(message)


def _content_id(domain: str, payload: Any) -> str:
    return hashlib.sha256(domain.encode() + b"\x00" + canonical_json_bytes(payload)).hexdigest()


def _verify_id(document: Mapping[str, Any], key: str, domain: str) -> None:
    payload = {name: value for name, value in document.items() if name != key}
    if document.get(key) != _content_id(domain, payload):
        _fail(f"V146 {key} changed")


def _normalize_relational_expression(expression: Any, target: int) -> tuple[Any, list[dict[str, Any]]]:
    state: dict[int, int] = {}
    action: dict[int, int] = {}
    constants: dict[str, int] = {}
    relations: dict[str, int] = {}

    def visit(value: Any) -> Any:
        if type(value) is not list or not value:
            return value
        opcode = value[0]
        if opcode == "E00":
            if value[1] == target:
                return ["S", "SELF"]
            state.setdefault(value[1], len(state))
            return ["S", state[value[1]]]
        if opcode == "E01":
            action.setdefault(value[1], len(action))
            return ["A", action[value[1]]]
        if opcode == "E03":
            constants.setdefault(value[1], len(constants))
            return ["K", constants[value[1]]]
        if opcode == "E04":
            relations.setdefault(value[1], len(relations))
            return ["E04", ["R", relations[value[1]]], visit(value[2])]
        return [opcode, *(visit(item) for item in value[1:])]

    normalized = visit(expression)
    bindings = [
        {"symbol_kind": "STATE", "normalized_index": normalized_index, "source_token": raw}
        for raw, normalized_index in sorted(state.items(), key=lambda item: item[1])
    ] + [
        {"symbol_kind": "ACTION", "normalized_index": normalized_index, "source_token": raw}
        for raw, normalized_index in sorted(action.items(), key=lambda item: item[1])
    ] + [
        {"symbol_kind": "CONSTANT", "normalized_index": normalized_index, "source_token": raw}
        for raw, normalized_index in sorted(constants.items(), key=lambda item: item[1])
    ] + [
        {"symbol_kind": "RELATION", "normalized_index": normalized_index, "source_token": raw}
        for raw, normalized_index in sorted(relations.items(), key=lambda item: item[1])
    ]
    return normalized, bindings


def _node_count(value: Any) -> int:
    if type(value) is not list:
        return 1
    return 1 + sum(_node_count(item) for item in value[1:])


def derive_anonymous_relational_factor_bank_v146(
    campaign_raw: bytes,
    verification_raw: bytes,
) -> dict[str, Any]:
    campaign = loads_canonical_json(campaign_raw)
    verification = loads_canonical_json(verification_raw)
    if (
        canonical_json_bytes(campaign) != campaign_raw
        or len(campaign_raw) != CAMPAIGN_BYTE_COUNT
        or hashlib.sha256(campaign_raw).hexdigest() != CAMPAIGN_SHA256
        or campaign.get("campaign_id") != CAMPAIGN_ID
        or campaign.get("registered_gate", {}).get("passed") is not True
        or canonical_json_bytes(verification) != verification_raw
        or len(verification_raw) != VERIFICATION_BYTE_COUNT
        or hashlib.sha256(verification_raw).hexdigest() != VERIFICATION_SHA256
        or verification.get("verification_id") != VERIFICATION_ID
        or verification.get("campaign_id") != CAMPAIGN_ID
        or verification.get("producer_free_relational_expression_lowering_reconstruction") is not True
        or verification.get("producer_free_model_epoch_and_local_recovery_receipt_reconstruction") is not True
    ):
        _fail("V146 frozen V145 source or verification changed")
    _verify_id(campaign, "campaign_id", _CAMPAIGN_DOMAIN)
    normalized: dict[str, tuple[str, Any]] = {}
    origins: dict[str, list[dict[str, Any]]] = defaultdict(list)
    source_occurrence_ids = []
    for occurrence in campaign["target_occurrences"]:
        _verify_id(occurrence, "occurrence_id", _OCCURRENCE_DOMAIN)
        source_occurrence_ids.append(occurrence["occurrence_id"])
        candidate = occurrence["strict_no_prior_acquisition"]["candidate"]
        _verify_id(candidate, "candidate_id", _CANDIDATE_DOMAIN)
        for assignment in candidate["compiled_factor_assignments"]:
            expression, binding = _normalize_relational_expression(
                assignment["expression"], assignment["target_column"]
            )
            signature_payload = {
                "result_type": assignment["result_type"],
                "normalized_expression": expression,
            }
            signature = hashlib.sha256(canonical_json_bytes(signature_payload)).hexdigest()
            prior = normalized.setdefault(
                signature, (assignment["result_type"], expression)
            )
            if prior != (assignment["result_type"], expression):
                _fail("V146 normalized signature collision")
            origins[signature].append(
                {
                    "source_occurrence_id": occurrence["occurrence_id"],
                    "source_seed": occurrence["seed"],
                    "source_candidate_id": candidate["candidate_id"],
                    "source_target_column": assignment["target_column"],
                    "source_schema_pair": [
                        candidate["state_width"],
                        candidate["action_field_width"],
                    ],
                    "anonymous_symbol_binding": binding,
                }
            )
    search = []
    candidates = []
    for minimum_support in range(3, len(source_occurrence_ids)):
        selected = []
        total_gain = 0
        for signature in sorted(origins):
            result_type, expression = normalized[signature]
            rows = sorted(origins[signature], key=canonical_json_bytes)
            occurrence_ids = sorted({row["source_occurrence_id"] for row in rows})
            leave_one_gains = []
            for holdout in occurrence_ids:
                retained = [row for row in rows if row["source_occurrence_id"] != holdout]
                generic_bits = len(retained) * (8 + 8 * _node_count(expression))
                dictionary_bits = 16 + 8 * _node_count(expression) + 8 * len(retained)
                leave_one_gains.append(generic_bits - dictionary_bits)
            eligible = (
                len(occurrence_ids) >= minimum_support + 1
                and leave_one_gains
                and min(leave_one_gains) > 0
            )
            if eligible:
                selected.append(
                    {
                        "signature_sha256": signature,
                        "result_type": result_type,
                        "normalized_expression": expression,
                        "distinct_occurrence_support": len(occurrence_ids),
                        "minimum_leave_one_occurrence_syntactic_mdl_gain_bits": min(leave_one_gains),
                        "constant_symbol_count": sum(
                            row[0] == "K" for row in _walk_atoms(expression)
                        ),
                        "relation_symbol_count": sum(
                            row[0] == "R" for row in _walk_atoms(expression)
                        ),
                    }
                )
                total_gain += min(leave_one_gains)
        row = {
            "minimum_distinct_occurrence_support": minimum_support,
            "selected_template_count": len(selected),
            "selected_relational_template_count": sum(
                item["relation_symbol_count"] > 0 for item in selected
            ),
            "summed_weakest_leave_one_occurrence_syntactic_mdl_gain_bits": total_gain,
        }
        search.append(row)
        if selected:
            candidates.append((row, selected))
    if not candidates:
        _fail("V146 selected no reusable anonymous relation")
    selected_row, selected = min(
        candidates,
        key=lambda item: (
            -item[0]["summed_weakest_leave_one_occurrence_syntactic_mdl_gain_bits"],
            -item[0]["selected_relational_template_count"],
            -item[0]["minimum_distinct_occurrence_support"],
            canonical_json_bytes(item[1]),
        ),
    )
    if not any(item["relation_symbol_count"] > 0 for item in selected):
        _fail("V146 selected bank contains no anonymous finite-relation template")
    payload = {
        "schema": "acfqp.anonymous_relational_factor_bank.v146",
        "source_v145_campaign_id": CAMPAIGN_ID,
        "source_v145_verification_id": VERIFICATION_ID,
        "source_occurrence_ids": sorted(source_occurrence_ids),
        "source_occurrence_count": len(source_occurrence_ids),
        "support_threshold_search_rows": search,
        "selected_minimum_distinct_occurrence_support": selected_row[
            "minimum_distinct_occurrence_support"
        ],
        "selected_template_count": len(selected),
        "selected_relational_template_count": selected_row[
            "selected_relational_template_count"
        ],
        "selected_summed_weakest_leave_one_occurrence_syntactic_mdl_gain_bits": selected_row[
            "summed_weakest_leave_one_occurrence_syntactic_mdl_gain_bits"
        ],
        "selected_subprograms": selected,
        "constant_and_relation_names_alpha_normalized": True,
        "state_and_action_coordinates_alpha_normalized": True,
        "selection_uses_occurrence_support_not_campaign_container_support": True,
        "source_outcomes_precede_bank_construction": True,
        "new_target_occurrences_accessed": False,
        "new_target_outcomes_accessed": False,
        "historical_v121_instantiator_claimed_to_consume_relational_symbols": False,
        "new_relational_instantiator_required_before_target_use": True,
        "complete_world_model_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    return {
        **payload,
        "bank_id": domains.extension_content_id_v146(
            domains.CONSTRUCTION_K7_ANONYMOUS_RELATIONAL_FACTOR_BANK_V146_DOMAIN,
            payload,
        ),
    }


def _walk_atoms(expression: Any) -> list[Any]:
    if type(expression) is not list or not expression:
        return []
    return [expression, *(atom for item in expression[1:] for atom in _walk_atoms(item))]


def freeze_anonymous_relational_factor_bank_v146(
    campaign_raw: bytes,
    verification_raw: bytes,
) -> bytes:
    document = derive_anonymous_relational_factor_bank_v146(
        campaign_raw, verification_raw
    )
    raw = canonical_json_bytes(document)
    if BANK_ID != "0" * 64 and (
        document["bank_id"] != BANK_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("V146 frozen anonymous relational bank changed")
    return raw


__all__ = (
    "BANK_ID",
    "derive_anonymous_relational_factor_bank_v146",
    "freeze_anonymous_relational_factor_bank_v146",
)
