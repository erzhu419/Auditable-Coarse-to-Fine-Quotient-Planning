"""Freeze the retrospective development-only V62 residual-factor library.

The three source identities were inspected while V18 was developed, so this is
not a preregistered scientific outcome.  It is a content-addressed offline
proposal prior for a later fresh held-out campaign.  Raw source transitions and
all offline acquisition costs are retained so a producer-free verifier can
reconstruct the partial library exactly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v62 as domains
from acfqp import construction_k7_true_bit_symmetric_preregistration_v59 as pre
from acfqp import true_bit_symmetric_three_domain_campaign_core_v59 as campaign
from acfqp.generic_certificate_guided_partial_planner_v16 import (
    run_certificate_guided_partial_episode_v16,
)
from acfqp.generic_overlay_residual_factor_compiler_v18 import (
    compile_overlay_residual_factor_library_v18,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


LIBRARY_ARTIFACT_ID = "0" * 64
EXPECTED_CANONICAL_BYTE_COUNT = 0
EXPECTED_CANONICAL_SHA256 = "0" * 64
DEVELOPMENT_OCCURRENCES = (
    ("O0", "BALANCED_BATCH_REFINEMENT", 590_541),
    ("O1", "COUPLED_EXCHANGE", 590_542),
    ("O2", "MAINTENANCE_CASCADE", 590_543),
)
SOURCE_ROOT = Path(__file__).resolve().parents[2]
BOUND_SOURCE_PATHS = (
    "src/acfqp/construction_k7_domain_registry_extension_v62.py",
    "src/acfqp/generic_overlay_residual_factor_compiler_v18.py",
    "src/acfqp/generic_certificate_guided_partial_planner_v16.py",
    "src/acfqp/true_bit_symmetric_three_domain_campaign_core_v59.py",
)


class ConstructionK7ResidualFactorLibraryV62Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7ResidualFactorLibraryV62Error(message)


def _source_facts() -> list[dict[str, Any]]:
    result = []
    for relative in BOUND_SOURCE_PATHS:
        raw = (SOURCE_ROOT / relative).read_bytes()
        result.append(
            {
                "relative_path": relative,
                "byte_count": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
    return result


def _legacy_config() -> dict[str, Any]:
    return pre.campaign_config_v59()


def _identifier(domain: str, payload: dict[str, Any], key: str) -> dict[str, Any]:
    return {**payload, key: domains.extension_content_id_v62(domain, payload)}


def _build_source_occurrence(
    label: str, family: str, seed: int, config: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    factor_library = pre.previous.previous.FACTOR_LIBRARY
    adapter = campaign.predecessor.predecessor.prior_ground._adapter(
        family, seed, config
    )
    acquired = campaign.acquire_matched_true_bit_models_v59(
        adapter, factor_library, config
    )["ANONYMOUS_FACTOR_PRIOR_ON"]
    episode = run_certificate_guided_partial_episode_v16(
        adapter,
        acquired["candidate"],
        acquired["rows"],
        episode_index=0,
        maximum_abstract_depth=12,
        maximum_execution_steps=96,
    )
    candidate = acquired["candidate"].public_document
    acquisition_batches = [
        [row.to_document() for row in batch] for batch in acquired["batches"]
    ]
    payload = {
        "schema": "acfqp.residual_factor_development_source.v62",
        "opaque_occurrence": label,
        "family_for_source_accounting_only": family,
        "seed": seed,
        "partial_candidate_id": candidate["candidate_id"],
        "layout": candidate["layout"],
        "unknown_residual_target_columns": candidate[
            "unknown_residual_target_columns"
        ],
        "raw_acquisition_batches": acquisition_batches,
        "raw_local_transition_rows": episode["raw_local_transition_rows"],
        "acquisition_ground_support_labels": len(acquisition_batches),
        "local_ground_support_labels": episode["local_ground_support_labels"],
        "execution_steps": episode["execution_steps"],
        "planning_compute_events": episode["abstract_planning_compute_events"],
        "all_local_queries_followed_failed_certificates": episode[
            "all_ground_queries_followed_failed_certificates"
        ],
        "retrospective_development_identity": True,
        "preregistered_scientific_outcome": False,
    }
    source = _identifier(
        domains.CONSTRUCTION_K7_RESIDUAL_FACTOR_SOURCE_V62_DOMAIN,
        payload,
        "source_id",
    )
    compiler_input = {
        "layout": candidate["layout"],
        "unknown_residual_target_columns": candidate[
            "unknown_residual_target_columns"
        ],
        "raw_transition_rows": episode["raw_local_transition_rows"],
    }
    return source, compiler_input


def _document() -> dict[str, Any]:
    config = _legacy_config()
    sources = []
    occurrences = {}
    for label, family, seed in DEVELOPMENT_OCCURRENCES:
        source, compiler_input = _build_source_occurrence(
            label, family, seed, config
        )
        sources.append(source)
        occurrences[label] = compiler_input
    library = compile_overlay_residual_factor_library_v18(occurrences)
    offline_acquisition = sum(
        source["acquisition_ground_support_labels"] for source in sources
    )
    offline_local = sum(source["local_ground_support_labels"] for source in sources)
    payload = {
        "schema": "acfqp.residual_factor_library_artifact.v62",
        "source_closure": {
            "source_facts": _source_facts(),
            "v62_domains": dict(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V62),
        },
        "development_sources": sources,
        "compiled_library": library,
        "accounting": {
            "offline_acquisition_labels": offline_acquisition,
            "offline_certificate_local_labels": offline_local,
            "offline_total_labels": offline_acquisition + offline_local,
            "offline_execution_steps": sum(
                source["execution_steps"] for source in sources
            ),
            "offline_planning_compute_events": sum(
                source["planning_compute_events"] for source in sources
            ),
            "compiler_candidate_binding_evaluations": library[
                "candidate_binding_evaluation_count"
            ],
            "all_axes_separate": True,
        },
        "evidence_boundary": {
            "raw_source_rows_embedded": True,
            "exact_library_reconstruction_required": True,
            "retrospective_development_only": True,
            "fresh_held_out_sample_tax_claim_present": False,
            "ground_fact_transfer_present": False,
            "proposal_only_not_safety_authority": True,
        },
        "complete_residual_world_model_synthesized": False,
        "global_exact_dynamics_claimed": False,
        "arbitrary_domain_transfer_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    return _identifier(
        domains.CONSTRUCTION_K7_RESIDUAL_FACTOR_LIBRARY_V62_DOMAIN,
        payload,
        "library_artifact_id",
    )


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class ResidualFactorLibraryArtifactV62:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    library_artifact_id: str

    def __post_init__(self) -> None:
        document = loads_canonical_json(self.canonical_bytes)
        payload = {
            key: value for key, value in document.items() if key != "library_artifact_id"
        }
        if (
            self._issuer is not _ISSUER
            or type(document) is not dict
            or canonical_json_bytes(document) != self.canonical_bytes
            or document.get("library_artifact_id") != self.library_artifact_id
            or domains.extension_content_id_v62(
                domains.CONSTRUCTION_K7_RESIDUAL_FACTOR_LIBRARY_V62_DOMAIN,
                payload,
            )
            != self.library_artifact_id
        ):
            _fail("V62 residual-factor library bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


_CACHE: ResidualFactorLibraryArtifactV62 | None = None


def freeze_residual_factor_library_v62() -> ResidualFactorLibraryArtifactV62:
    global _CACHE
    if _CACHE is None:
        document = _document()
        raw = canonical_json_bytes(document)
        identity = document["library_artifact_id"]
        if LIBRARY_ARTIFACT_ID != "0" * 64 and (
            identity != LIBRARY_ARTIFACT_ID
            or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
            or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
        ):
            _fail("frozen V62 residual-factor library changed")
        _CACHE = ResidualFactorLibraryArtifactV62(_ISSUER, raw, identity)
    return _CACHE


def verify_residual_factor_library_v62(
    value: Any,
) -> ResidualFactorLibraryArtifactV62:
    if type(value) is not ResidualFactorLibraryArtifactV62:
        _fail("V62 residual-factor library rejects foreign values")
    value.__post_init__()
    expected = freeze_residual_factor_library_v62()
    if value is not expected or value.canonical_bytes != expected.canonical_bytes:
        _fail("V62 residual-factor library differs from frozen bytes")
    return value


__all__ = (
    "BOUND_SOURCE_PATHS",
    "DEVELOPMENT_OCCURRENCES",
    "EXPECTED_CANONICAL_BYTE_COUNT",
    "EXPECTED_CANONICAL_SHA256",
    "LIBRARY_ARTIFACT_ID",
    "freeze_residual_factor_library_v62",
    "verify_residual_factor_library_v62",
)
