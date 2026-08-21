"""Derive reusable anonymous factor templates from frozen campaign bytes."""

from __future__ import annotations

from collections import defaultdict
import hashlib
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v59 as domains59
from acfqp import construction_k7_domain_registry_extension_v120 as domains
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


SOURCE_CAMPAIGN_SPECS = {
    "V117": {
        "campaign_id": "5817b88896699206fcb08ed64111fc993691515fd0461e518c956a04de283b9d",
        "byte_count": 7_794_238,
        "sha256": "061a653cf1048fe01420a3159d4389b9b81eb573f97c5acfbd66fcf618d60039",
    },
    "V118": {
        "campaign_id": "0ab03c02a8b5b795860c5c96943204f8553fc6836e7dab92ef753c1fe6d86df1",
        "byte_count": 2_986_273,
        "sha256": "9afbade52f4b553ad5696e769ba6f8f1faced07fbb11b07b0f8a59991961e19d",
    },
    "V119": {
        "campaign_id": "611c995b93af4016bb85e070f5c1f263d6028ec424cc860e2b67da2bb9aeb3d4",
        "byte_count": 4_479_714,
        "sha256": "22565e57114973fbf1c2fc16d11785eb67c9aebcb5df2c61dc39cc0ba64e301e",
    },
}


class GenericArtifactDerivedFactorProjectionV120Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise GenericArtifactDerivedFactorProjectionV120Error(message)


def _campaign(alias: str, raw: bytes) -> dict[str, Any]:
    spec = SOURCE_CAMPAIGN_SPECS.get(alias)
    if (
        spec is None
        or type(raw) is not bytes
        or len(raw) != spec["byte_count"]
        or hashlib.sha256(raw).hexdigest() != spec["sha256"]
    ):
        _fail("V120 source campaign bytes changed")
    document = loads_canonical_json(raw)
    if (
        canonical_json_bytes(document) != raw
        or document.get("campaign_id") != spec["campaign_id"]
        or document.get("registered_gate", {}).get("passed") is not True
    ):
        _fail("V120 source campaign identity or Gate changed")
    return document


def _candidates(value: Any) -> list[dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}

    def visit(item: Any) -> None:
        if type(item) is dict:
            if item.get("schema") == "acfqp.generic_partial_factor_candidate.v15":
                identity = item.get("candidate_id")
                payload = {
                    key: value for key, value in item.items() if key != "candidate_id"
                }
                if (
                    type(identity) is not str
                    or identity
                    != domains59.extension_content_id_v59(
                        domains59.CONSTRUCTION_K7_TRUE_BIT_SYMMETRIC_ACQUISITION_V59_DOMAIN,
                        payload,
                    )
                ):
                    _fail("V120 source candidate identity changed")
                incumbent = result.setdefault(identity, item)
                if incumbent != item:
                    _fail("V120 repeated source candidate bytes changed")
            for nested in item.values():
                visit(nested)
        elif type(item) is list:
            for nested in item:
                visit(nested)

    visit(value)
    return [result[key] for key in sorted(result)]


def _normalize(expression: Any, target: int) -> Any:
    action_fields: dict[int, int] = {}
    state_columns: dict[int, int] = {}

    def visit(item: Any) -> Any:
        if type(item) is not list or not item:
            return item
        head = item[0]
        if head == "E00":
            if item[1] == target:
                return ["S", "SELF"]
            state_columns.setdefault(item[1], len(state_columns))
            return ["S", state_columns[item[1]]]
        if head == "E01":
            action_fields.setdefault(item[1], len(action_fields))
            return ["A", action_fields[item[1]]]
        return [head, *(visit(value) for value in item[1:])]

    return visit(expression)


def derive_artifact_factor_projection_v120(
    source_campaign_bytes: Mapping[str, bytes],
    *,
    minimum_distinct_schema_pair_support: int = 2,
) -> dict[str, Any]:
    if (
        type(source_campaign_bytes) is not dict
        or set(source_campaign_bytes) != set(SOURCE_CAMPAIGN_SPECS)
        or type(minimum_distinct_schema_pair_support) is not int
        or minimum_distinct_schema_pair_support < 2
    ):
        _fail("V120 source inventory or support rule changed")
    campaigns = {
        alias: _campaign(alias, source_campaign_bytes[alias])
        for alias in sorted(source_campaign_bytes)
    }
    candidates = {
        alias: _candidates(document) for alias, document in campaigns.items()
    }
    if any(not rows for rows in candidates.values()):
        _fail("V120 source campaign exposed no partial candidates")
    origins_by_signature: dict[str, list[dict[str, Any]]] = defaultdict(list)
    normalized_by_signature: dict[str, tuple[str, Any]] = {}
    for alias, rows in candidates.items():
        for candidate in rows:
            state_width = candidate.get("state_width")
            action_width = candidate.get("action_field_width")
            assignments = candidate.get("compiled_factor_assignments")
            if (
                type(state_width) is not int
                or type(action_width) is not int
                or type(assignments) is not list
                or not assignments
            ):
                _fail("V120 source candidate shape changed")
            for assignment in assignments:
                target = assignment.get("target_column")
                result_type = assignment.get("result_type")
                expression = assignment.get("expression")
                if (
                    type(target) is not int
                    or result_type not in {"INT", "FINITE_INT_SUPPORT"}
                    or type(expression) is not list
                ):
                    _fail("V120 source factor assignment changed")
                normalized = _normalize(expression, target)
                signature_payload = {
                    "result_type": result_type,
                    "normalized_expression": normalized,
                }
                signature = hashlib.sha256(
                    canonical_json_bytes(signature_payload)
                ).hexdigest()
                prior = normalized_by_signature.setdefault(
                    signature, (result_type, normalized)
                )
                if prior != (result_type, normalized):
                    _fail("V120 normalized factor signature collision")
                origins_by_signature[signature].append(
                    {
                        "source_campaign_alias": alias,
                        "source_campaign_id": campaigns[alias]["campaign_id"],
                        "source_candidate_id": candidate["candidate_id"],
                        "source_schema_pair": [state_width, action_width],
                        "source_target_column": target,
                    }
                )
    templates = []
    origin_rows = []
    for signature in sorted(origins_by_signature):
        result_type, normalized = normalized_by_signature[signature]
        origins = sorted(
            origins_by_signature[signature],
            key=canonical_json_bytes,
        )
        schema_pairs = sorted({tuple(row["source_schema_pair"]) for row in origins})
        if len(schema_pairs) < minimum_distinct_schema_pair_support:
            continue
        templates.append(
            {
                "signature_sha256": signature,
                "result_type": result_type,
                "normalized_expression": normalized,
                "source_schema_pairs": [list(row) for row in schema_pairs],
            }
        )
        origin_rows.append(
            {
                "signature_sha256": signature,
                "distinct_schema_pair_count": len(schema_pairs),
                "origin_count": len(origins),
                "origins": origins,
            }
        )
    if len(templates) < 3:
        _fail("V120 artifact evidence derived too few reusable factors")
    library_payload = {
        "schema": "acfqp.artifact_derived_factor_library.v120",
        "source_campaigns": [
            {
                "alias": alias,
                **SOURCE_CAMPAIGN_SPECS[alias],
                "unique_partial_candidate_count": len(candidates[alias]),
            }
            for alias in sorted(campaigns)
        ],
        "minimum_distinct_schema_pair_support": minimum_distinct_schema_pair_support,
        "derived_subprograms": templates,
        "derivation_origins": origin_rows,
        "candidate_document_count": sum(len(rows) for rows in candidates.values()),
        "normalization_rule": "ALPHA_RENAME_STATE_AND_ACTION_REFERENCES_WITH_TARGET_AS_SELF",
        "semantic_family_names_used_for_subprogram_selection": False,
        "target_slot_inventory_supplied": False,
        "ground_transition_prediction_authority_present": False,
        "complete_world_model_claimed": False,
    }
    factor_library_id = domains.extension_content_id_v120(
        domains.CONSTRUCTION_K7_ARTIFACT_DERIVED_FACTOR_LIBRARY_V120_DOMAIN,
        library_payload,
    )
    projection = {
        "schema": "acfqp.cross_schema_factor_template_projection.v15",
        "source_factor_library_id": factor_library_id,
        "cross_schema_subprograms": templates,
        "target_slot_inventory_supplied": False,
        "semantic_names_supplied": False,
    }
    return {
        **library_payload,
        "factor_library_id": factor_library_id,
        "v15_partial_synthesizer_projection": projection,
        "projection_derived_only_from_frozen_candidate_artifacts": True,
        "hand_written_factor_template_count": 0,
    }


def verify_artifact_factor_projection_v120(
    document: Mapping[str, Any], source_campaign_bytes: Mapping[str, bytes]
) -> dict[str, Any]:
    expected = derive_artifact_factor_projection_v120(
        source_campaign_bytes,
        minimum_distinct_schema_pair_support=document.get(
            "minimum_distinct_schema_pair_support"
        ),
    )
    if type(document) is not dict or document != expected:
        _fail("V120 artifact-derived factor projection changed")
    return {
        "factor_library_id": document["factor_library_id"],
        "derived_subprogram_count": len(document["derived_subprograms"]),
        "source_candidate_document_count": document["candidate_document_count"],
        "exact_artifact_reconstruction": True,
        "ground_transition_prediction_authority_present": False,
    }


__all__ = (
    "SOURCE_CAMPAIGN_SPECS",
    "derive_artifact_factor_projection_v120",
    "verify_artifact_factor_projection_v120",
)
