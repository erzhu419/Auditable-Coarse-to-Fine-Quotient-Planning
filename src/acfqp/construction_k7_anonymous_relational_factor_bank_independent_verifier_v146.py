"""Producer-free reconstruction of the V146 anonymous relational factor bank."""

from __future__ import annotations

from collections import defaultdict
import hashlib
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v146 as domains
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "24a50acc5cf553f4fc457e17aa4ffff0fc6b6b9ebe08fa0d54076d998c3eeaa9"
CAMPAIGN_BYTE_COUNT = 17_516_246
CAMPAIGN_SHA256 = "5584aa76043f76d69b72ec189bc67a3952e758bbaaad33025b73dc859851f33c"
SOURCE_VERIFICATION_ID = "0924f57684bdeae9b9da339d949f9ab2f00949b5684817621eae26497adc3d7c"
SOURCE_VERIFICATION_BYTE_COUNT = 12_863
SOURCE_VERIFICATION_SHA256 = "f363feba0e5e5c6a12c0f6f709f9c0f4fe55b0e3113b907005e4eb8f77bbcb13"
BANK_ID = "78bb4dae4682ed0cedb7a7781caca4af04986f0db86d7086a0786166d07020b5"
BANK_BYTE_COUNT = 4_033
BANK_SHA256 = "eb733aad5d7b5aed20933366ba4b6f8c9d24338b20a4437ef11ffbf4f0a99fe6"
VERIFICATION_ID = "0" * 64
EXPECTED_CANONICAL_BYTE_COUNT = 0
EXPECTED_CANONICAL_SHA256 = "0" * 64
_CAMPAIGN_DOMAIN = "acfqp:construction-k7-certificate-local-recovery-union-campaign:v145"
_OCCURRENCE_DOMAIN = "acfqp:construction-k7-certificate-local-recovery-union-occurrence:v145"
_CANDIDATE_DOMAIN = "acfqp:construction-k7-robust-dictionary-factor-prior-candidate:v131r2"


class ConstructionK7AnonymousRelationalFactorBankIndependentVerifierV146Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7AnonymousRelationalFactorBankIndependentVerifierV146Error(message)


def _require(condition: bool, message: str) -> None:
    if condition is not True:
        _fail(message)


def _content_id(domain: str, payload: Any) -> str:
    return hashlib.sha256(domain.encode() + b"\x00" + canonical_json_bytes(payload)).hexdigest()


def _verify_id(document: Mapping[str, Any], key: str, domain: str) -> None:
    _require(
        document.get(key)
        == _content_id(domain, {name: value for name, value in document.items() if name != key}),
        f"V146 independent {key} changed",
    )


def _alpha(expression: Any, target: int) -> tuple[Any, list[dict[str, Any]]]:
    inventories: dict[str, dict[Any, int]] = {
        "STATE": {},
        "ACTION": {},
        "CONSTANT": {},
        "RELATION": {},
    }

    def symbol(kind: str, token: Any) -> int:
        inventory = inventories[kind]
        inventory.setdefault(token, len(inventory))
        return inventory[token]

    def visit(value: Any) -> Any:
        if type(value) is not list or not value:
            return value
        head = value[0]
        if head == "E00":
            return ["S", "SELF"] if value[1] == target else ["S", symbol("STATE", value[1])]
        if head == "E01":
            return ["A", symbol("ACTION", value[1])]
        if head == "E03":
            return ["K", symbol("CONSTANT", value[1])]
        if head == "E04":
            return ["E04", ["R", symbol("RELATION", value[1])], visit(value[2])]
        return [head, *(visit(item) for item in value[1:])]

    normalized = visit(expression)
    binding = [
        {"symbol_kind": kind, "normalized_index": index, "source_token": token}
        for kind in ("STATE", "ACTION", "CONSTANT", "RELATION")
        for token, index in sorted(inventories[kind].items(), key=lambda item: item[1])
    ]
    return normalized, binding


def _nodes(value: Any) -> int:
    return 1 if type(value) is not list else 1 + sum(_nodes(item) for item in value[1:])


def _symbols(value: Any, kind: str) -> int:
    if type(value) is not list or not value:
        return 0
    return int(value[0] == kind) + sum(_symbols(item, kind) for item in value[1:])


def _reconstruct(campaign: Mapping[str, Any], source_verification: Mapping[str, Any]) -> dict[str, Any]:
    templates: dict[str, tuple[str, Any]] = {}
    origins: dict[str, list[dict[str, Any]]] = defaultdict(list)
    occurrence_ids = []
    for occurrence in campaign["target_occurrences"]:
        _verify_id(occurrence, "occurrence_id", _OCCURRENCE_DOMAIN)
        occurrence_ids.append(occurrence["occurrence_id"])
        candidate = occurrence["strict_no_prior_acquisition"]["candidate"]
        _verify_id(candidate, "candidate_id", _CANDIDATE_DOMAIN)
        for assignment in candidate["compiled_factor_assignments"]:
            normalized, binding = _alpha(assignment["expression"], assignment["target_column"])
            signature_payload = {
                "result_type": assignment["result_type"],
                "normalized_expression": normalized,
            }
            signature = hashlib.sha256(canonical_json_bytes(signature_payload)).hexdigest()
            _require(
                templates.setdefault(signature, (assignment["result_type"], normalized))
                == (assignment["result_type"], normalized),
                "V146 independent signature collision",
            )
            origins[signature].append(
                {
                    "source_occurrence_id": occurrence["occurrence_id"],
                    "source_seed": occurrence["seed"],
                    "source_candidate_id": candidate["candidate_id"],
                    "source_target_column": assignment["target_column"],
                    "source_schema_pair": [candidate["state_width"], candidate["action_field_width"]],
                    "anonymous_symbol_binding": binding,
                }
            )
    search = []
    alternatives = []
    for threshold in range(3, len(occurrence_ids)):
        selected = []
        total_gain = 0
        for signature in sorted(origins):
            result_type, expression = templates[signature]
            source_ids = sorted({row["source_occurrence_id"] for row in origins[signature]})
            gains = []
            for holdout in source_ids:
                retained = [row for row in origins[signature] if row["source_occurrence_id"] != holdout]
                gains.append(
                    len(retained) * (8 + 8 * _nodes(expression))
                    - (16 + 8 * _nodes(expression) + 8 * len(retained))
                )
            if len(source_ids) >= threshold + 1 and gains and min(gains) > 0:
                selected.append(
                    {
                        "signature_sha256": signature,
                        "result_type": result_type,
                        "normalized_expression": expression,
                        "distinct_occurrence_support": len(source_ids),
                        "minimum_leave_one_occurrence_syntactic_mdl_gain_bits": min(gains),
                        "constant_symbol_count": _symbols(expression, "K"),
                        "relation_symbol_count": _symbols(expression, "R"),
                    }
                )
                total_gain += min(gains)
        row = {
            "minimum_distinct_occurrence_support": threshold,
            "selected_template_count": len(selected),
            "selected_relational_template_count": sum(item["relation_symbol_count"] > 0 for item in selected),
            "summed_weakest_leave_one_occurrence_syntactic_mdl_gain_bits": total_gain,
        }
        search.append(row)
        if selected:
            alternatives.append((row, selected))
    _require(bool(alternatives), "V146 independent selection is empty")
    chosen, selected = min(
        alternatives,
        key=lambda item: (
            -item[0]["summed_weakest_leave_one_occurrence_syntactic_mdl_gain_bits"],
            -item[0]["selected_relational_template_count"],
            -item[0]["minimum_distinct_occurrence_support"],
            canonical_json_bytes(item[1]),
        ),
    )
    payload = {
        "schema": "acfqp.anonymous_relational_factor_bank.v146",
        "source_v145_campaign_id": CAMPAIGN_ID,
        "source_v145_verification_id": SOURCE_VERIFICATION_ID,
        "source_occurrence_ids": sorted(occurrence_ids),
        "source_occurrence_count": len(occurrence_ids),
        "support_threshold_search_rows": search,
        "selected_minimum_distinct_occurrence_support": chosen["minimum_distinct_occurrence_support"],
        "selected_template_count": len(selected),
        "selected_relational_template_count": chosen["selected_relational_template_count"],
        "selected_summed_weakest_leave_one_occurrence_syntactic_mdl_gain_bits": chosen["summed_weakest_leave_one_occurrence_syntactic_mdl_gain_bits"],
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


def freeze_anonymous_relational_factor_bank_verification_v146(
    bank_raw: bytes,
    campaign_raw: bytes,
    source_verification_raw: bytes,
) -> bytes:
    bank = loads_canonical_json(bank_raw)
    campaign = loads_canonical_json(campaign_raw)
    source_verification = loads_canonical_json(source_verification_raw)
    _require(
        canonical_json_bytes(bank) == bank_raw
        and len(bank_raw) == BANK_BYTE_COUNT
        and hashlib.sha256(bank_raw).hexdigest() == BANK_SHA256
        and bank.get("bank_id") == BANK_ID
        and canonical_json_bytes(campaign) == campaign_raw
        and len(campaign_raw) == CAMPAIGN_BYTE_COUNT
        and hashlib.sha256(campaign_raw).hexdigest() == CAMPAIGN_SHA256
        and campaign.get("campaign_id") == CAMPAIGN_ID
        and canonical_json_bytes(source_verification) == source_verification_raw
        and len(source_verification_raw) == SOURCE_VERIFICATION_BYTE_COUNT
        and hashlib.sha256(source_verification_raw).hexdigest() == SOURCE_VERIFICATION_SHA256
        and source_verification.get("verification_id") == SOURCE_VERIFICATION_ID,
        "V146 frozen inputs changed",
    )
    _verify_id(campaign, "campaign_id", _CAMPAIGN_DOMAIN)
    expected = _reconstruct(campaign, source_verification)
    _require(expected == bank, "V146 producer-free bank reconstruction changed")
    payload = {
        "schema": "acfqp.anonymous_relational_factor_bank_verification.v146",
        "bank_id": BANK_ID,
        "source_v145_campaign_id": CAMPAIGN_ID,
        "source_v145_verification_id": SOURCE_VERIFICATION_ID,
        "verified_source_occurrence_count": bank["source_occurrence_count"],
        "verified_selected_template_count": bank["selected_template_count"],
        "verified_selected_relational_template_count": bank["selected_relational_template_count"],
        "producer_free_candidate_and_occurrence_id_reconstruction": True,
        "producer_free_constant_relation_and_coordinate_alpha_normalization": True,
        "producer_free_support_threshold_and_mdl_selection": True,
        "new_target_outcomes_accessed": False,
        "relational_instantiator_execution_claimed": False,
        "complete_world_model_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    document = {
        **payload,
        "verification_id": domains.extension_content_id_v146(
            domains.CONSTRUCTION_K7_ANONYMOUS_RELATIONAL_FACTOR_BANK_VERIFICATION_V146_DOMAIN,
            payload,
        ),
    }
    raw = canonical_json_bytes(document)
    if VERIFICATION_ID != "0" * 64:
        _require(
            document["verification_id"] == VERIFICATION_ID
            and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
            and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256,
            "V146 frozen verification changed",
        )
    return raw


__all__ = (
    "VERIFICATION_ID",
    "freeze_anonymous_relational_factor_bank_verification_v146",
)
