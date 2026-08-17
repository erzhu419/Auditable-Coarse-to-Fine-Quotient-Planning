"""Fresh V49r3 registration with AST-complete transport dependencies."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_atomic_composition_failure_v49r2 as v49r2_failure
from acfqp import construction_k7_atomic_composition_preregistration_v49r2 as v49r2
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_ATOMIC_COMPOSITION_ADAPTIVE_ACQUISITION_V49R3_DOMAIN,
    CONSTRUCTION_K7_ATOMIC_COMPOSITION_CAMPAIGN_V49R3_DOMAIN,
    CONSTRUCTION_K7_ATOMIC_COMPOSITION_DEPENDENCY_SUPPORT_V49R3_DOMAIN,
    CONSTRUCTION_K7_ATOMIC_COMPOSITION_FAILED_CERTIFICATE_V49R3_DOMAIN,
    CONSTRUCTION_K7_ATOMIC_COMPOSITION_LOCAL_DISTINCTION_V49R3_DOMAIN,
    CONSTRUCTION_K7_ATOMIC_COMPOSITION_OOD_REJECTION_V49R3_DOMAIN,
    CONSTRUCTION_K7_ATOMIC_COMPOSITION_PARTIAL_DYNAMICS_V49R3_DOMAIN,
    CONSTRUCTION_K7_ATOMIC_COMPOSITION_PREREGISTRATION_V49R3_DOMAIN,
    CONSTRUCTION_K7_ATOMIC_COMPOSITION_PROGRAM_V49R3_DOMAIN,
    CONSTRUCTION_K7_ATOMIC_COMPOSITION_RAW_OBSERVATION_V49R3_DOMAIN,
    CONSTRUCTION_K7_ATOMIC_COMPOSITION_RECEDING_EPISODE_V49R3_DOMAIN,
    CONSTRUCTION_K7_ATOMIC_COMPOSITION_SAMPLE_TAX_V49R3_DOMAIN,
    CONSTRUCTION_K7_ATOMIC_COMPOSITION_VERIFICATION_V49R3_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
)


SCHEMA_VERSION = "49.3.0"
PROPOSED_CONTRACT_VERSION = "2.0.218"
PROFILE_KEY = "construction_k7_generic_atomic_composition_v49r3"
PREREGISTRATION_ID = "90198055b383f88f46d44887951601628473c5b32e68b30f5386237b540b92d3"
EXPECTED_CANONICAL_BYTE_COUNT = 9_548
EXPECTED_CANONICAL_SHA256 = "fd787c5f178bfda30692beec500b866990df4ba9fc3172f6a9a4ce954081fc15"

V49_PREREGISTRATION_ID = v49r2.V49_PREREGISTRATION_ID
V49_FAILURE_ID = v49r2.V49_FAILURE_ID
V49R1_PREREGISTRATION_ID = v49r2.V49R1_PREREGISTRATION_ID
V49R1_FAILURE_ID = v49r2.V49R1_FAILURE_ID
V49R2_PREREGISTRATION_ID = v49r2.PREREGISTRATION_ID
V49R2_FAILURE_ID = v49r2_failure.FAILURE_ID
SOURCE_ROOT = v49r2.SOURCE_ROOT
BOUND_SOURCE_PATHS = v49r2.BOUND_SOURCE_PATHS
SOURCE_SPEC = v49r2.SOURCE_SPEC
SOURCE_SEEDS = (494101, 494102, 494103)
TARGET_SPEC = v49r2.TARGET_SPEC
TARGET_SEEDS = tuple(range(494301, 494313))
SHARED_MODE_TOKENS = v49r2.SHARED_MODE_TOKENS
SHARED_CLASS_TOKENS = v49r2.SHARED_CLASS_TOKENS
SHARED_TERMINAL_TOKENS = v49r2.SHARED_TERMINAL_TOKENS
STATE_LAYOUT_ORDER = v49r2.STATE_LAYOUT_ORDER
ACTION_FIELD_ORDER = v49r2.ACTION_FIELD_ORDER
MAX_SOURCE_LABELS_PER_OCCURRENCE = v49r2.MAX_SOURCE_LABELS_PER_OCCURRENCE
RECEDING_HORIZON = v49r2.RECEDING_HORIZON
ARMS = v49r2.ARMS

FUTURE_DOMAINS = {
    "preregistration": CONSTRUCTION_K7_ATOMIC_COMPOSITION_PREREGISTRATION_V49R3_DOMAIN,
    "observation": CONSTRUCTION_K7_ATOMIC_COMPOSITION_RAW_OBSERVATION_V49R3_DOMAIN,
    "program": CONSTRUCTION_K7_ATOMIC_COMPOSITION_PROGRAM_V49R3_DOMAIN,
    "support": CONSTRUCTION_K7_ATOMIC_COMPOSITION_DEPENDENCY_SUPPORT_V49R3_DOMAIN,
    "failed_certificate": CONSTRUCTION_K7_ATOMIC_COMPOSITION_FAILED_CERTIFICATE_V49R3_DOMAIN,
    "distinction": CONSTRUCTION_K7_ATOMIC_COMPOSITION_LOCAL_DISTINCTION_V49R3_DOMAIN,
    "episode": CONSTRUCTION_K7_ATOMIC_COMPOSITION_RECEDING_EPISODE_V49R3_DOMAIN,
    "partial": CONSTRUCTION_K7_ATOMIC_COMPOSITION_PARTIAL_DYNAMICS_V49R3_DOMAIN,
    "acquisition": CONSTRUCTION_K7_ATOMIC_COMPOSITION_ADAPTIVE_ACQUISITION_V49R3_DOMAIN,
    "sample_tax": CONSTRUCTION_K7_ATOMIC_COMPOSITION_SAMPLE_TAX_V49R3_DOMAIN,
    "ood": CONSTRUCTION_K7_ATOMIC_COMPOSITION_OOD_REJECTION_V49R3_DOMAIN,
    "campaign": CONSTRUCTION_K7_ATOMIC_COMPOSITION_CAMPAIGN_V49R3_DOMAIN,
    "verification": CONSTRUCTION_K7_ATOMIC_COMPOSITION_VERIFICATION_V49R3_DOMAIN,
}


class ConstructionK7AtomicCompositionPreregistrationV49R3Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7AtomicCompositionPreregistrationV49R3Error(message)


def _document() -> dict[str, Any]:
    base = v49r2.freeze_atomic_composition_preregistration_v49r2().to_document()
    base.pop("atomic_composition_preregistration_id")
    base["schema"] = "acfqp.atomic_composition_preregistration.v49r3"
    base["schema_version"] = SCHEMA_VERSION
    base["proposed_contract_version"] = PROPOSED_CONTRACT_VERSION
    base["profile_key"] = PROFILE_KEY
    base["frozen_predecessor"] = {
        "v49_preregistration_id": V49_PREREGISTRATION_ID,
        "v49_failure_id": V49_FAILURE_ID,
        "v49r1_preregistration_id": V49R1_PREREGISTRATION_ID,
        "v49r1_failure_id": V49R1_FAILURE_ID,
        "v49r2_preregistration_id": V49R2_PREREGISTRATION_ID,
        "v49r2_failure_id": V49R2_FAILURE_ID,
        "all_three_failed_predecessors_preserved_without_correction": True,
    }
    closure = base["source_closure"]
    closure["frozen_before_any_v49r2_source_or_target_outcome"] = False
    closure["frozen_before_any_v49r3_source_or_target_outcome"] = True
    workload = base["fresh_workload"]
    workload["source_seeds"] = list(SOURCE_SEEDS)
    workload["target_seeds"] = list(TARGET_SEEDS)
    workload["all_source_and_target_seed_identities_fresh_after_v49r1_failure"] = False
    workload["all_source_and_target_seed_identities_fresh_after_v49r2_failure"] = True
    base["protocol"].update(
        {
            "relation_transport_dependency_extraction": "ALL_E00_AND_E03_LEAVES_ON_E06_PATH_CONTAINING_E04_RELATION",
            "source_target_comparison_for_E00": "FIRST_RAW_SOURCE_PRE_VECTOR_VERSUS_TARGET_INITIAL_VECTOR",
            "source_target_comparison_for_E03": "SOURCE_OCCURRENCE_BINDING_VERSUS_TARGET_BINDING",
            "certificate_must_fail_if_any_dependent_leaf_changes": True,
        }
    )
    base["recovery_correction"] = {
        "correction": "EXTRACT_RELATION_DEPENDENT_E00_AND_E03_LEAVES_DIRECTLY_FROM_COMPILED_AST",
        "local_recovery": "ONE_RAW_SUPPORT_EXEMPLAR_PER_ANONYMOUS_RELATION_INPUT",
        "development_validation": "FULL_UNREGISTERED_THREE_SOURCE_TWELVE_TARGET_DRY_RUN_PASSED",
        "development_registered_outcomes_used": False,
        "correction_frozen_before_v49r3_outcomes": True,
        "no_change_to_generic_composer_or_environment_kernel": True,
        "same_identity_rerun_forbidden": True,
    }
    base["required_positive_conditions"].append(
        "RELATION_TRANSPORT_CERTIFICATE_REPLAYS_AST_COMPLETE_E00_E03_DEPENDENCIES"
    )
    base["claim_boundary"]["v49r2_failure_preserved"] = True
    base["fresh_v49r2_outcome_execution_performed"] = False
    base["fresh_v49r3_outcome_execution_performed"] = False
    base["future_content_domains"] = FUTURE_DOMAINS
    return {
        **base,
        "atomic_composition_preregistration_id": content_id(
            FUTURE_DOMAINS["preregistration"], base
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class AtomicCompositionPreregistrationV49R3:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("V49r3 preregistration is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict or canonical_json_bytes(document) != self.canonical_bytes:
            _fail("V49r3 preregistration bytes changed")
        payload = {key: value for key, value in document.items() if key != "atomic_composition_preregistration_id"}
        if document.get("atomic_composition_preregistration_id") != self.preregistration_id or content_id(
            FUTURE_DOMAINS["preregistration"], payload
        ) != self.preregistration_id:
            _fail("V49r3 preregistration identity changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


def freeze_atomic_composition_preregistration_v49r3() -> AtomicCompositionPreregistrationV49R3:
    document = _document()
    raw = canonical_json_bytes(document)
    identity = document["atomic_composition_preregistration_id"]
    if PREREGISTRATION_ID != "0" * 64 and (
        identity != PREREGISTRATION_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V49r3 preregistration changed")
    return AtomicCompositionPreregistrationV49R3(_ISSUER, raw, identity)


def verify_atomic_composition_preregistration_v49r3(
    value: AtomicCompositionPreregistrationV49R3,
) -> AtomicCompositionPreregistrationV49R3:
    if type(value) is not AtomicCompositionPreregistrationV49R3:
        _fail("V49r3 preregistration rejects foreign values")
    value.__post_init__()
    if value.canonical_bytes != canonical_json_bytes(_document()):
        _fail("V49r3 preregistration semantics changed")
    return value


__all__ = (
    "ACTION_FIELD_ORDER",
    "ARMS",
    "AtomicCompositionPreregistrationV49R3",
    "BOUND_SOURCE_PATHS",
    "EXPECTED_CANONICAL_BYTE_COUNT",
    "EXPECTED_CANONICAL_SHA256",
    "FUTURE_DOMAINS",
    "MAX_SOURCE_LABELS_PER_OCCURRENCE",
    "PREREGISTRATION_ID",
    "RECEDING_HORIZON",
    "SHARED_CLASS_TOKENS",
    "SHARED_MODE_TOKENS",
    "SHARED_TERMINAL_TOKENS",
    "SOURCE_ROOT",
    "SOURCE_SEEDS",
    "SOURCE_SPEC",
    "STATE_LAYOUT_ORDER",
    "TARGET_SEEDS",
    "TARGET_SPEC",
    "V49_FAILURE_ID",
    "V49R1_FAILURE_ID",
    "V49R2_FAILURE_ID",
    "freeze_atomic_composition_preregistration_v49r3",
    "verify_atomic_composition_preregistration_v49r3",
)
