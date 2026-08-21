"""Select an anonymous factor dictionary from frozen candidate artifacts.

The selector receives no target occurrence and no named slot inventory.  It
enumerates every subset of the artifact-derived template pool and minimizes a
two-part prefix code for the frozen source candidate occurrences.  A template
is eligible only when it survives every leave-one-source-campaign reconstruction.
"""

from __future__ import annotations

from itertools import combinations
from math import ceil, log2
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v131 as domains
from acfqp.generic_artifact_derived_factor_projection_v120 import (
    SOURCE_CAMPAIGN_SPECS,
    verify_artifact_factor_projection_v120,
)
from acfqp.generic_artifact_subprogram_instantiator_v121 import _symbols
from acfqp.generic_bit_codelength_universal_synthesizer_v14 import (
    _ast_bits,
    _unsigned_gamma_bits,
    _utf8_bits,
)
from acfqp.phase3e_ids import canonical_json_bytes


class AutomaticMinimalFactorDictionaryV131Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise AutomaticMinimalFactorDictionaryV131Error(message)


def _symbol_binding_bits(expression: Any) -> int:
    symbols = _symbols(expression)
    return _unsigned_gamma_bits(len(symbols)) + sum(
        1 + _unsigned_gamma_bits(index) for _kind, index in symbols
    )


def _score_subset(
    signatures: tuple[str, ...],
    templates: Mapping[str, Mapping[str, Any]],
    origins: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    selected = frozenset(signatures)
    index_bits = max(1, ceil(log2(max(2, len(selected))))) if selected else 0
    dictionary_bits = _unsigned_gamma_bits(len(selected)) + sum(
        _utf8_bits(templates[signature]["result_type"])
        + _ast_bits(templates[signature]["normalized_expression"])
        for signature in signatures
    )
    source_bits = 0
    rows = []
    for signature in sorted(templates):
        template = templates[signature]
        count = origins[signature]["origin_count"]
        generic_bits = 1 + _ast_bits(template["normalized_expression"])
        reference_bits = (
            1 + index_bits + _symbol_binding_bits(template["normalized_expression"])
        )
        encoded_bits = (
            min(generic_bits, reference_bits)
            if signature in selected
            else generic_bits
        )
        source_bits += count * encoded_bits
        rows.append(
            {
                "signature_sha256": signature,
                "source_origin_count": count,
                "generic_ast_branch_bits_per_origin": generic_bits,
                "dictionary_reference_branch_bits_per_origin": (
                    reference_bits if signature in selected else None
                ),
                "selected": signature in selected,
            }
        )
    return {
        "selected_signatures": list(signatures),
        "dictionary_index_prefix_bits": index_bits,
        "dictionary_description_bits": dictionary_bits,
        "source_occurrence_encoding_bits": source_bits,
        "total_two_part_prefix_bits": dictionary_bits + source_bits,
        "per_template_code_rows": rows,
    }


def derive_automatic_minimal_factor_dictionary_v131(
    artifact_library: Mapping[str, Any],
    source_campaign_bytes: Mapping[str, bytes],
) -> dict[str, Any]:
    """Derive the minimum source code and independently test each holdout."""

    verified = verify_artifact_factor_projection_v120(
        artifact_library, dict(source_campaign_bytes)
    )
    templates = {
        row["signature_sha256"]: row
        for row in artifact_library.get("derived_subprograms", ())
    }
    origins = {
        row["signature_sha256"]: row
        for row in artifact_library.get("derivation_origins", ())
    }
    aliases = tuple(sorted(SOURCE_CAMPAIGN_SPECS))
    if (
        verified["derived_subprogram_count"] != len(templates)
        or not templates
        or set(templates) != set(origins)
        or tuple(sorted(source_campaign_bytes)) != aliases
    ):
        _fail("V131 source candidate template pool changed")
    eligible = []
    holdout_rows = []
    for signature in sorted(templates):
        row = origins[signature]
        supporting_aliases = {
            item["source_campaign_alias"] for item in row["origins"]
        }
        reconstructions = []
        for holdout in aliases:
            retained = [
                item
                for item in row["origins"]
                if item["source_campaign_alias"] != holdout
            ]
            retained_aliases = sorted(
                {item["source_campaign_alias"] for item in retained}
            )
            retained_schema_pairs = sorted(
                {tuple(item["source_schema_pair"]) for item in retained}
            )
            reconstructions.append(
                {
                    "held_out_source_campaign_alias": holdout,
                    "retained_supporting_source_campaign_aliases": retained_aliases,
                    "retained_distinct_schema_pairs": [
                        list(pair) for pair in retained_schema_pairs
                    ],
                    "eligible_without_held_out_source": (
                        len(retained_aliases) >= 2
                        and len(retained_schema_pairs) >= 2
                    ),
                }
            )
        survives = (
            supporting_aliases == set(aliases)
            and all(item["eligible_without_held_out_source"] for item in reconstructions)
        )
        if survives:
            eligible.append(signature)
        holdout_rows.append(
            {
                "signature_sha256": signature,
                "all_source_campaign_support": sorted(supporting_aliases),
                "leave_one_source_reconstructions": reconstructions,
                "eligible_for_dictionary_search": survives,
            }
        )
    if not eligible:
        _fail("V131 no factor survived leave-one-source reconstruction")
    scored = []
    for cardinality in range(len(eligible) + 1):
        for subset in combinations(eligible, cardinality):
            scored.append(_score_subset(subset, templates, origins))
    selected_score = min(
        scored,
        key=lambda row: (
            row["total_two_part_prefix_bits"],
            len(row["selected_signatures"]),
            canonical_json_bytes(row["selected_signatures"]),
        ),
    )
    selected = [templates[key] for key in selected_score["selected_signatures"]]
    if not selected:
        _fail("V131 minimum code selected an empty dictionary")
    payload = {
        "schema": "acfqp.automatic_minimal_factor_dictionary.v131",
        "source_artifact_factor_library_id": artifact_library["factor_library_id"],
        "source_candidate_document_count": artifact_library["candidate_document_count"],
        "source_template_pool_count": len(templates),
        "eligible_template_count": len(eligible),
        "selected_template_count": len(selected),
        "selected_subprograms": selected,
        "leave_one_source_campaign_reconstruction": holdout_rows,
        "subset_search": {
            "candidate_subset_count": len(scored),
            "exhaustive_finite_subset_enumeration": True,
            "selection_objective": (
                "MIN_TOTAL_TWO_PART_PREFIX_BITS_THEN_CARDINALITY_THEN_BYTES"
            ),
            "selected_score": selected_score,
        },
        "target_occurrences_accessed": False,
        "target_outcomes_accessed": False,
        "fixed_template_cardinality_supplied": False,
        "fixed_template_slot_inventory_supplied": False,
        "semantic_family_names_used_for_selection": False,
        "complete_world_model_claimed": False,
    }
    dictionary_id = domains.extension_content_id_v131(
        domains.CONSTRUCTION_K7_AUTOMATIC_FACTOR_DICTIONARY_V131_DOMAIN,
        payload,
    )
    projection = {
        "schema": "acfqp.cross_schema_factor_template_projection.v15",
        "source_factor_library_id": dictionary_id,
        "cross_schema_subprograms": selected,
        "target_slot_inventory_supplied": False,
        "semantic_names_supplied": False,
    }
    return {
        **payload,
        "dictionary_id": dictionary_id,
        "v15_partial_synthesizer_projection": projection,
    }


def verify_automatic_minimal_factor_dictionary_v131(
    document: Mapping[str, Any],
    artifact_library: Mapping[str, Any],
    source_campaign_bytes: Mapping[str, bytes],
) -> dict[str, Any]:
    expected = derive_automatic_minimal_factor_dictionary_v131(
        artifact_library, source_campaign_bytes
    )
    if type(document) is not dict or document != expected:
        _fail("V131 automatic factor dictionary changed")
    return {
        "dictionary_id": document["dictionary_id"],
        "selected_template_count": document["selected_template_count"],
        "leave_one_source_campaign_reconstruction_verified": True,
        "minimum_two_part_prefix_code_verified": True,
        "target_outcomes_accessed": False,
    }


__all__ = (
    "derive_automatic_minimal_factor_dictionary_v131",
    "verify_automatic_minimal_factor_dictionary_v131",
)
