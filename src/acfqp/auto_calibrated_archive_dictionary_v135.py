"""Select opaque-archive support thresholds from source-only jackknife gains."""

from __future__ import annotations

import hashlib
from typing import Any, Iterable, NoReturn

from acfqp import construction_k7_domain_registry_extension_v135 as domains
from acfqp.opaque_source_archive_dictionary_v132 import (
    OpaqueSourceArchiveDictionaryV132Error,
    derive_opaque_source_archive_dictionary_v132,
)
from acfqp.phase3e_ids import canonical_json_bytes


DICTIONARY_ID = "b7c1f1898090c168fdf39daf5b6aa10863680d066a3fadf0719826b3062bd5b3"
EXPECTED_CANONICAL_BYTE_COUNT = 8_466
EXPECTED_CANONICAL_SHA256 = "27c411000f048445d70a475ddb11d7ccba77ef097b80fa6c4f819164ce36ec3b"


class AutoCalibratedArchiveDictionaryV135Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise AutoCalibratedArchiveDictionaryV135Error(message)


def derive_auto_calibrated_archive_dictionary_v135(
    source_artifact_bytes: Iterable[bytes],
) -> dict[str, Any]:
    sources = tuple(source_artifact_bytes)
    if len(sources) < 4 or any(type(raw) is not bytes for raw in sources):
        _fail("V135 source archive contract changed")
    candidates = []
    for artifact_support in range(2, len(sources)):
        for schema_support in range(2, 1 + len(sources)):
            try:
                dictionary = derive_opaque_source_archive_dictionary_v132(
                    sources,
                    minimum_distinct_artifact_support=artifact_support,
                    minimum_distinct_schema_pair_support=schema_support,
                )
            except OpaqueSourceArchiveDictionaryV132Error:
                continue
            selected_rows = [
                row
                for row in dictionary["support_and_leave_one_artifact_evidence"]
                if row["selected"]
            ]
            weakest_gains = [
                min(
                    holdout["singleton_dictionary_prefix_gain_bits"]
                    for holdout in row["leave_one_artifact_reconstructions"]
                )
                for row in selected_rows
            ]
            score = sum(weakest_gains)
            candidates.append(
                {
                    "minimum_distinct_artifact_support": artifact_support,
                    "minimum_distinct_schema_pair_support": schema_support,
                    "selected_template_count": dictionary["selected_template_count"],
                    "selected_template_signatures": [
                        row["signature_sha256"]
                        for row in dictionary["selected_subprograms"]
                    ],
                    "per_template_weakest_leave_one_prefix_gain_bits": weakest_gains,
                    "summed_weakest_leave_one_prefix_gain_bits": score,
                    "dictionary": dictionary,
                }
            )
    if not candidates:
        _fail("V135 source-only threshold search returned no dictionary")
    selected = min(
        candidates,
        key=lambda row: (
            -row["summed_weakest_leave_one_prefix_gain_bits"],
            -row["minimum_distinct_artifact_support"],
            row["minimum_distinct_schema_pair_support"],
            canonical_json_bytes(row["selected_template_signatures"]),
        ),
    )
    source_dictionary = selected["dictionary"]
    search_rows = [
        {key: value for key, value in row.items() if key != "dictionary"}
        for row in sorted(
            candidates,
            key=lambda row: (
                row["minimum_distinct_artifact_support"],
                row["minimum_distinct_schema_pair_support"],
            ),
        )
    ]
    payload = {
        "schema": "acfqp.auto_calibrated_opaque_archive_dictionary.v135",
        "source_archive": source_dictionary["source_archive"],
        "source_archive_cardinality": len(sources),
        "support_threshold_search_rows": search_rows,
        "selected_minimum_distinct_artifact_support": selected[
            "minimum_distinct_artifact_support"
        ],
        "selected_minimum_distinct_schema_pair_support": selected[
            "minimum_distinct_schema_pair_support"
        ],
        "selected_summed_weakest_leave_one_prefix_gain_bits": selected[
            "summed_weakest_leave_one_prefix_gain_bits"
        ],
        "selected_template_count": source_dictionary["selected_template_count"],
        "selected_subprograms": source_dictionary["selected_subprograms"],
        "support_and_leave_one_artifact_evidence": source_dictionary[
            "support_and_leave_one_artifact_evidence"
        ],
        "support_thresholds_supplied_by_caller": False,
        "selection_objective": (
            "MAX_SUMMED_PER_TEMPLATE_WEAKEST_LEAVE_ONE_PREFIX_GAIN_THEN_"
            "MAX_ARTIFACT_SUPPORT_THEN_MIN_SCHEMA_SUPPORT_THEN_BYTES"
        ),
        "opaque_content_addressed_source_archive": True,
        "target_occurrences_accessed": False,
        "target_outcomes_accessed": False,
        "complete_world_model_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    dictionary_id = domains.extension_content_id_v135(
        domains.CONSTRUCTION_K7_AUTO_CALIBRATED_ARCHIVE_DICTIONARY_V135_DOMAIN,
        payload,
    )
    return {
        **payload,
        "dictionary_id": dictionary_id,
        "v15_partial_synthesizer_projection": {
            "schema": "acfqp.cross_schema_factor_template_projection.v15",
            "source_factor_library_id": dictionary_id,
            "cross_schema_subprograms": source_dictionary["selected_subprograms"],
            "target_slot_inventory_supplied": False,
            "semantic_names_supplied": False,
        },
    }


def freeze_auto_calibrated_archive_dictionary_v135(
    source_artifact_bytes: Iterable[bytes],
) -> bytes:
    document = derive_auto_calibrated_archive_dictionary_v135(source_artifact_bytes)
    raw = canonical_json_bytes(document)
    if DICTIONARY_ID != "0" * 64 and (
        document["dictionary_id"] != DICTIONARY_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("V135 frozen auto-calibrated dictionary changed")
    return raw


__all__ = (
    "DICTIONARY_ID",
    "derive_auto_calibrated_archive_dictionary_v135",
    "freeze_auto_calibrated_archive_dictionary_v135",
)
