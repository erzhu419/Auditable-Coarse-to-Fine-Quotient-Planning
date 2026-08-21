"""Leave-one-source robust automatic factor dictionary V131r2."""

from __future__ import annotations

from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v131r2 as domains
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


class RobustAutomaticFactorDictionaryV131R2Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise RobustAutomaticFactorDictionaryV131R2Error(message)


def _symbol_binding_bits(expression: Any) -> int:
    symbols = _symbols(expression)
    return _unsigned_gamma_bits(len(symbols)) + sum(
        1 + _unsigned_gamma_bits(index) for _kind, index in symbols
    )


def derive_robust_automatic_factor_dictionary_v131r2(
    artifact_library: Mapping[str, Any],
    source_campaign_bytes: Mapping[str, bytes],
) -> dict[str, Any]:
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
        _fail("V131r2 source candidate template pool changed")
    selected_signatures = []
    holdout_rows = []
    for signature in sorted(templates):
        template = templates[signature]
        generic_bits = 1 + _ast_bits(template["normalized_expression"])
        singleton_dictionary_description_bits = (
            _unsigned_gamma_bits(1)
            + _utf8_bits(template["result_type"])
            + _ast_bits(template["normalized_expression"])
        )
        reference_bits = (
            1 + 1 + _symbol_binding_bits(template["normalized_expression"])
        )
        reconstructions = []
        for holdout in aliases:
            retained = [
                row
                for row in origins[signature]["origins"]
                if row["source_campaign_alias"] != holdout
            ]
            retained_aliases = sorted(
                {row["source_campaign_alias"] for row in retained}
            )
            retained_pairs = sorted(
                {tuple(row["source_schema_pair"]) for row in retained}
            )
            generic_total = len(retained) * generic_bits
            dictionary_total = (
                singleton_dictionary_description_bits
                + len(retained) * reference_bits
            )
            gain = generic_total - dictionary_total
            reconstructions.append(
                {
                    "held_out_source_campaign_alias": holdout,
                    "retained_supporting_source_campaign_aliases": retained_aliases,
                    "retained_distinct_schema_pairs": [
                        list(pair) for pair in retained_pairs
                    ],
                    "retained_origin_count": len(retained),
                    "generic_ast_source_prefix_bits": generic_total,
                    "singleton_dictionary_source_prefix_bits": dictionary_total,
                    "singleton_dictionary_prefix_gain_bits": gain,
                    "eligible_without_held_out_source": (
                        len(retained_aliases) >= 2
                        and len(retained_pairs) >= 2
                        and gain > 0
                    ),
                }
            )
        eligible = all(
            row["eligible_without_held_out_source"] for row in reconstructions
        )
        if eligible:
            selected_signatures.append(signature)
        holdout_rows.append(
            {
                "signature_sha256": signature,
                "leave_one_source_reconstructions": reconstructions,
                "minimum_leave_one_source_prefix_gain_bits": min(
                    row["singleton_dictionary_prefix_gain_bits"]
                    for row in reconstructions
                ),
                "eligible_for_dictionary_search": eligible,
            }
        )
    if not selected_signatures:
        _fail("V131r2 no robust positive-gain source template exists")
    selected = [templates[signature] for signature in selected_signatures]
    payload = {
        "schema": "acfqp.robust_automatic_factor_dictionary.v131r2",
        "source_artifact_factor_library_id": artifact_library["factor_library_id"],
        "source_candidate_document_count": artifact_library["candidate_document_count"],
        "source_template_pool_count": len(templates),
        "selected_template_count": len(selected),
        "selected_subprograms": selected,
        "leave_one_source_campaign_reconstruction": holdout_rows,
        "selection_rule": (
            "SELECT_EXACTLY_EACH_TEMPLATE_WITH_POSITIVE_SINGLETON_PREFIX_GAIN_"
            "UNDER_EVERY_LEAVE_ONE_SOURCE_RECONSTRUCTION"
        ),
        "selection_rule_applied_independently_per_anonymous_template": True,
        "minimum_selected_template_leave_one_source_gain_bits": min(
            row["minimum_leave_one_source_prefix_gain_bits"]
            for row in holdout_rows
            if row["eligible_for_dictionary_search"]
        ),
        "target_occurrences_accessed": False,
        "target_outcomes_accessed": False,
        "failed_v131r1_target_outcome_used_for_selection": False,
        "fixed_template_cardinality_supplied": False,
        "fixed_template_slot_inventory_supplied": False,
        "semantic_family_names_used_for_selection": False,
        "complete_world_model_claimed": False,
    }
    dictionary_id = domains.extension_content_id_v131r2(
        domains.CONSTRUCTION_K7_ROBUST_FACTOR_DICTIONARY_V131R2_DOMAIN,
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


def verify_robust_automatic_factor_dictionary_v131r2(
    document: Mapping[str, Any],
    artifact_library: Mapping[str, Any],
    source_campaign_bytes: Mapping[str, bytes],
) -> dict[str, Any]:
    expected = derive_robust_automatic_factor_dictionary_v131r2(
        artifact_library, source_campaign_bytes
    )
    if type(document) is not dict or document != expected:
        _fail("V131r2 robust automatic dictionary changed")
    return {
        "dictionary_id": document["dictionary_id"],
        "selected_template_count": document["selected_template_count"],
        "leave_one_source_campaign_reconstruction_verified": True,
        "positive_singleton_prefix_gain_every_holdout_verified": True,
        "target_outcomes_accessed": False,
    }


__all__ = (
    "derive_robust_automatic_factor_dictionary_v131r2",
    "verify_robust_automatic_factor_dictionary_v131r2",
)
