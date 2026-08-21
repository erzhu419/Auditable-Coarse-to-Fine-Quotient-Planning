"""Producer-free verification of heterogeneous archive cohort selection."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
import hashlib
from itertools import combinations
from typing import Any, Iterable, NoReturn

from acfqp import construction_k7_domain_registry_extension_v137 as domains
from acfqp.construction_k7_auto_calibrated_archive_independent_verifier_v135 import (
    AutoCalibratedArchiveIndependentVerifierV135Error,
    _derive_auto_calibrated_archive_dictionary_independent_v135,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


FROZEN_DICTIONARY_ID = (
    "e1a97462b7a3d16a7f1d071fd14f0d22a0bf4e94209cabb67107598f3479e6f6"
)
FROZEN_DICTIONARY_BYTE_COUNT = 6_146
FROZEN_DICTIONARY_SHA256 = (
    "b52020a585bf3e9fd21aafe56e03f62361a331eb43894b10111baa06f17ca661"
)

VERIFICATION_ID = "a16c8a16a06e58e7fe2fad2fe1b54d1d92e62badf05b7cb47076e0f653ccfe43"
EXPECTED_CANONICAL_BYTE_COUNT = 2_138
EXPECTED_CANONICAL_SHA256 = (
    "b0a73f25e0f8d9df06362833ab1e81b72459b19e55be09cd5ba6b6c65b7d3330"
)


class HeterogeneousArchiveIndependentVerifierV137Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise HeterogeneousArchiveIndependentVerifierV137Error(message)


def _attempt(args: tuple[tuple[bytes, ...], tuple[int, ...]]) -> dict[str, Any]:
    sources, indices = args
    selected = tuple(sources[index] for index in indices)
    digests = [hashlib.sha256(raw).hexdigest() for raw in selected]
    try:
        dictionary = _derive_auto_calibrated_archive_dictionary_independent_v135(
            selected
        )
    except AutoCalibratedArchiveIndependentVerifierV135Error as error:
        del error
        return {
            "source_artifact_sha256s": digests,
            "source_archive_cardinality": len(indices),
            "calibration_succeeded": False,
            "failure_type": "AutoCalibratedArchiveDictionaryV135Error",
        }
    return {
        "source_artifact_sha256s": digests,
        "source_archive_cardinality": len(indices),
        "calibration_succeeded": True,
        "selected_template_count": dictionary["selected_template_count"],
        "selected_summed_weakest_leave_one_prefix_gain_bits": dictionary[
            "selected_summed_weakest_leave_one_prefix_gain_bits"
        ],
        "dictionary": dictionary,
    }


def _derive_heterogeneous_archive_cohort_dictionary_independent_v137(
    source_artifact_bytes: Iterable[bytes],
    *,
    worker_count: int = 2,
) -> dict[str, Any]:
    sources = tuple(source_artifact_bytes)
    if (
        len(sources) < 5
        or any(type(raw) is not bytes for raw in sources)
        or len({hashlib.sha256(raw).digest() for raw in sources}) != len(sources)
        or type(worker_count) is not int
        or worker_count not in {1, 2}
    ):
        _fail("V137 heterogeneous archive contract changed")
    full = _attempt((sources, tuple(range(len(sources)))))
    attempts = [full]
    if full["calibration_succeeded"] is not True:
        frontier = [
            tuple(indices)
            for indices in combinations(range(len(sources)), len(sources) - 1)
        ]
        args = [(sources, indices) for indices in frontier]
        if worker_count == 1:
            attempts.extend(_attempt(arg) for arg in args)
        else:
            with ProcessPoolExecutor(max_workers=worker_count) as executor:
                attempts.extend(executor.map(_attempt, args))
    successful = [row for row in attempts if row["calibration_succeeded"] is True]
    if not successful:
        _fail("V137 no coherent maximal source cohort found")
    selected = min(
        successful,
        key=lambda row: (
            -row["source_archive_cardinality"],
            -row["selected_summed_weakest_leave_one_prefix_gain_bits"],
            canonical_json_bytes(row["source_artifact_sha256s"]),
        ),
    )
    selected_hashes = frozenset(selected["source_artifact_sha256s"])
    all_rows = sorted(
        (
            {
                "artifact_sha256": hashlib.sha256(raw).hexdigest(),
                "byte_count": len(raw),
                "selected_in_coherent_cohort": hashlib.sha256(raw).hexdigest()
                in selected_hashes,
            }
            for raw in sources
        ),
        key=lambda row: row["artifact_sha256"],
    )
    source_dictionary = selected["dictionary"]
    attempt_documents = [
        {key: value for key, value in row.items() if key != "dictionary"}
        for row in attempts
    ]
    payload = {
        "schema": "acfqp.heterogeneous_archive_cohort_dictionary.v137",
        "complete_source_archive": all_rows,
        "complete_source_archive_cardinality": len(sources),
        "cohort_search_attempts": attempt_documents,
        "selected_cohort_artifact_sha256s": sorted(selected_hashes),
        "selected_cohort_cardinality": selected["source_archive_cardinality"],
        "excluded_archive_artifact_sha256s": sorted(
            row["artifact_sha256"]
            for row in all_rows
            if row["selected_in_coherent_cohort"] is False
        ),
        "selected_minimum_distinct_artifact_support": source_dictionary[
            "selected_minimum_distinct_artifact_support"
        ],
        "selected_minimum_distinct_schema_pair_support": source_dictionary[
            "selected_minimum_distinct_schema_pair_support"
        ],
        "selected_template_count": source_dictionary["selected_template_count"],
        "selected_subprograms": source_dictionary["selected_subprograms"],
        "maximal_cardinality_then_source_only_gain_selection": True,
        "incompatible_sources_recorded_not_silently_dropped": True,
        "source_aliases_or_family_names_used_for_cohort_selection": False,
        "target_occurrences_accessed": False,
        "target_outcomes_accessed": False,
        "complete_world_model_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    dictionary_id = domains.extension_content_id_v137(
        domains.CONSTRUCTION_K7_HETEROGENEOUS_ARCHIVE_DICTIONARY_V137_DOMAIN,
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


def freeze_heterogeneous_archive_verification_v137(
    dictionary_raw: bytes,
    source_artifact_bytes: Iterable[bytes],
) -> bytes:
    if type(dictionary_raw) is not bytes:
        _fail("V137 dictionary bytes changed")
    dictionary = loads_canonical_json(dictionary_raw)
    reconstructed = _derive_heterogeneous_archive_cohort_dictionary_independent_v137(
        source_artifact_bytes
    )
    if (
        canonical_json_bytes(dictionary) != dictionary_raw
        or dictionary != reconstructed
        or dictionary.get("dictionary_id") != FROZEN_DICTIONARY_ID
        or len(dictionary_raw) != FROZEN_DICTIONARY_BYTE_COUNT
        or hashlib.sha256(dictionary_raw).hexdigest() != FROZEN_DICTIONARY_SHA256
    ):
        _fail("V137 frozen heterogeneous dictionary did not reproduce")
    if (
        reconstructed["complete_source_archive_cardinality"] != 5
        or reconstructed["selected_cohort_cardinality"] != 4
        or len(reconstructed["excluded_archive_artifact_sha256s"]) != 1
        or reconstructed["selected_template_count"] != 3
        or reconstructed["target_outcomes_accessed"] is not False
    ):
        _fail("V137 registered heterogeneous archive gate changed")
    payload = {
        "schema": "acfqp.heterogeneous_archive_cohort_verification.v137",
        "dictionary_id": FROZEN_DICTIONARY_ID,
        "dictionary_byte_count": FROZEN_DICTIONARY_BYTE_COUNT,
        "dictionary_sha256": FROZEN_DICTIONARY_SHA256,
        "complete_source_archive": reconstructed["complete_source_archive"],
        "complete_source_archive_cardinality": 5,
        "cohort_search_attempt_count": len(
            reconstructed["cohort_search_attempts"]
        ),
        "selected_cohort_artifact_sha256s": reconstructed[
            "selected_cohort_artifact_sha256s"
        ],
        "selected_cohort_cardinality": 4,
        "excluded_archive_artifact_sha256s": reconstructed[
            "excluded_archive_artifact_sha256s"
        ],
        "selected_template_count": 3,
        "producer_free_full_and_leave_one_cohort_search": True,
        "producer_free_auto_calibration_reconstruction": True,
        "incompatible_sources_recorded_not_silently_dropped": True,
        "source_aliases_or_family_names_used_for_cohort_selection": False,
        "target_occurrences_accessed": False,
        "target_outcomes_accessed": False,
        "complete_world_model_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    verification_id = domains.extension_content_id_v137(
        domains.CONSTRUCTION_K7_HETEROGENEOUS_ARCHIVE_VERIFICATION_V137_DOMAIN,
        payload,
    )
    raw = canonical_json_bytes({**payload, "verification_id": verification_id})
    if VERIFICATION_ID != "0" * 64 and (
        verification_id != VERIFICATION_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("V137 frozen independent verification changed")
    return raw


__all__ = (
    "EXPECTED_CANONICAL_BYTE_COUNT",
    "EXPECTED_CANONICAL_SHA256",
    "VERIFICATION_ID",
    "freeze_heterogeneous_archive_verification_v137",
)
