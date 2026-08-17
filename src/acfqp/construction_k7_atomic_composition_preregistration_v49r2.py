"""Fresh V49r2 registration with relation-transport certification."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_atomic_composition_failure_v49r1 as v49r1_failure
from acfqp import construction_k7_atomic_composition_preregistration_v49r1 as v49r1
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_ATOMIC_COMPOSITION_ADAPTIVE_ACQUISITION_V49R2_DOMAIN,
    CONSTRUCTION_K7_ATOMIC_COMPOSITION_CAMPAIGN_V49R2_DOMAIN,
    CONSTRUCTION_K7_ATOMIC_COMPOSITION_DEPENDENCY_SUPPORT_V49R2_DOMAIN,
    CONSTRUCTION_K7_ATOMIC_COMPOSITION_FAILED_CERTIFICATE_V49R2_DOMAIN,
    CONSTRUCTION_K7_ATOMIC_COMPOSITION_LOCAL_DISTINCTION_V49R2_DOMAIN,
    CONSTRUCTION_K7_ATOMIC_COMPOSITION_OOD_REJECTION_V49R2_DOMAIN,
    CONSTRUCTION_K7_ATOMIC_COMPOSITION_PARTIAL_DYNAMICS_V49R2_DOMAIN,
    CONSTRUCTION_K7_ATOMIC_COMPOSITION_PREREGISTRATION_V49R2_DOMAIN,
    CONSTRUCTION_K7_ATOMIC_COMPOSITION_PROGRAM_V49R2_DOMAIN,
    CONSTRUCTION_K7_ATOMIC_COMPOSITION_RAW_OBSERVATION_V49R2_DOMAIN,
    CONSTRUCTION_K7_ATOMIC_COMPOSITION_RECEDING_EPISODE_V49R2_DOMAIN,
    CONSTRUCTION_K7_ATOMIC_COMPOSITION_SAMPLE_TAX_V49R2_DOMAIN,
    CONSTRUCTION_K7_ATOMIC_COMPOSITION_VERIFICATION_V49R2_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
)


SCHEMA_VERSION = "49.2.0"
PROPOSED_CONTRACT_VERSION = "2.0.217"
PROFILE_KEY = "construction_k7_generic_atomic_composition_v49r2"
PREREGISTRATION_ID = "e2f041540e3ab3b6120020a844a46404ae45af6f613aff1a51eeb26c666a3ac6"
EXPECTED_CANONICAL_BYTE_COUNT = 8_645
EXPECTED_CANONICAL_SHA256 = "b91fbd3f3d246deafc3682afa25cf43651bf70deea34b8c2b1cd2a33e97056e6"

V49_PREREGISTRATION_ID = v49r1.V49_PREREGISTRATION_ID
V49_FAILURE_ID = v49r1.V49_FAILURE_ID
V49R1_PREREGISTRATION_ID = v49r1.PREREGISTRATION_ID
V49R1_FAILURE_ID = v49r1_failure.FAILURE_ID
SOURCE_ROOT = v49r1.SOURCE_ROOT
BOUND_SOURCE_PATHS = v49r1.BOUND_SOURCE_PATHS
SOURCE_SPEC = v49r1.SOURCE_SPEC
SOURCE_SEEDS = (493101, 493102, 493103)
TARGET_SPEC = v49r1.TARGET_SPEC
TARGET_SEEDS = tuple(range(493301, 493313))
SHARED_MODE_TOKENS = v49r1.SHARED_MODE_TOKENS
SHARED_CLASS_TOKENS = v49r1.SHARED_CLASS_TOKENS
SHARED_TERMINAL_TOKENS = v49r1.SHARED_TERMINAL_TOKENS
STATE_LAYOUT_ORDER = v49r1.STATE_LAYOUT_ORDER
ACTION_FIELD_ORDER = v49r1.ACTION_FIELD_ORDER
MAX_SOURCE_LABELS_PER_OCCURRENCE = v49r1.MAX_SOURCE_LABELS_PER_OCCURRENCE
RECEDING_HORIZON = v49r1.RECEDING_HORIZON
ARMS = v49r1.ARMS

FUTURE_DOMAINS = {
    "preregistration": CONSTRUCTION_K7_ATOMIC_COMPOSITION_PREREGISTRATION_V49R2_DOMAIN,
    "observation": CONSTRUCTION_K7_ATOMIC_COMPOSITION_RAW_OBSERVATION_V49R2_DOMAIN,
    "program": CONSTRUCTION_K7_ATOMIC_COMPOSITION_PROGRAM_V49R2_DOMAIN,
    "support": CONSTRUCTION_K7_ATOMIC_COMPOSITION_DEPENDENCY_SUPPORT_V49R2_DOMAIN,
    "failed_certificate": CONSTRUCTION_K7_ATOMIC_COMPOSITION_FAILED_CERTIFICATE_V49R2_DOMAIN,
    "distinction": CONSTRUCTION_K7_ATOMIC_COMPOSITION_LOCAL_DISTINCTION_V49R2_DOMAIN,
    "episode": CONSTRUCTION_K7_ATOMIC_COMPOSITION_RECEDING_EPISODE_V49R2_DOMAIN,
    "partial": CONSTRUCTION_K7_ATOMIC_COMPOSITION_PARTIAL_DYNAMICS_V49R2_DOMAIN,
    "acquisition": CONSTRUCTION_K7_ATOMIC_COMPOSITION_ADAPTIVE_ACQUISITION_V49R2_DOMAIN,
    "sample_tax": CONSTRUCTION_K7_ATOMIC_COMPOSITION_SAMPLE_TAX_V49R2_DOMAIN,
    "ood": CONSTRUCTION_K7_ATOMIC_COMPOSITION_OOD_REJECTION_V49R2_DOMAIN,
    "campaign": CONSTRUCTION_K7_ATOMIC_COMPOSITION_CAMPAIGN_V49R2_DOMAIN,
    "verification": CONSTRUCTION_K7_ATOMIC_COMPOSITION_VERIFICATION_V49R2_DOMAIN,
}


class ConstructionK7AtomicCompositionPreregistrationV49R2Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7AtomicCompositionPreregistrationV49R2Error(message)


def _document() -> dict[str, Any]:
    base = v49r1.freeze_atomic_composition_preregistration_v49r1().to_document()
    base.pop("atomic_composition_preregistration_id")
    base["schema"] = "acfqp.atomic_composition_preregistration.v49r2"
    base["schema_version"] = SCHEMA_VERSION
    base["proposed_contract_version"] = PROPOSED_CONTRACT_VERSION
    base["profile_key"] = PROFILE_KEY
    base["frozen_predecessor"] = {
        "v49_preregistration_id": V49_PREREGISTRATION_ID,
        "v49_failure_id": V49_FAILURE_ID,
        "v49r1_preregistration_id": V49R1_PREREGISTRATION_ID,
        "v49r1_failure_id": V49R1_FAILURE_ID,
        "both_failed_predecessors_preserved_without_correction": True,
        "v49r1_campaign_artifact_issued": False,
    }
    closure = base["source_closure"]
    closure["frozen_before_any_v49r1_source_or_target_outcome"] = False
    closure["frozen_before_any_v49r2_source_or_target_outcome"] = True
    workload = base["fresh_workload"]
    workload["source_seeds"] = list(SOURCE_SEEDS)
    workload["target_seeds"] = list(TARGET_SEEDS)
    workload["all_source_and_target_seed_identities_fresh_after_v49_failure"] = False
    workload["all_source_and_target_seed_identities_fresh_after_v49r1_failure"] = True
    base["protocol"].update(
        {
            "changed_occurrence_constant_invalidates_relation_transport_certificate": True,
            "one_failed_certificate_before_target_relation_exemplar_queries": True,
            "one_witness_blind_support_exemplar_per_anonymous_relation_input": True,
            "relation_exemplar_queries_must_precede_target_planning": True,
            "target_relation_overlay_immutable_after_certificate_recovery": True,
            "maximum_target_relation_exemplar_labels": len(SHARED_MODE_TOKENS),
        }
    )
    base["recovery_correction"] = {
        "correction": "INVALIDATE_RELATION_TRANSPORT_WHEN_DEPENDENT_OCCURRENCE_CONSTANT_CHANGES",
        "local_recovery": "ONE_RAW_SUPPORT_EXEMPLAR_PER_ANONYMOUS_RELATION_INPUT",
        "correction_frozen_before_v49r2_outcomes": True,
        "no_change_to_generic_composer_or_environment_kernel": True,
        "same_identity_rerun_forbidden": True,
    }
    base["required_positive_conditions"].extend(
        [
            "CHANGED_RELATION_VALUES_DETECTED_BY_TRANSPORT_CERTIFICATE",
            "TARGET_RELATION_TABLE_RECOVERED_WITH_AT_MOST_FOUR_LOCAL_SUPPORT_LABELS",
        ]
    )
    base["claim_boundary"]["v49r1_failure_preserved"] = True
    base["fresh_v49r1_outcome_execution_performed"] = False
    base["fresh_v49r2_outcome_execution_performed"] = False
    base["future_content_domains"] = FUTURE_DOMAINS
    return {
        **base,
        "atomic_composition_preregistration_id": content_id(
            FUTURE_DOMAINS["preregistration"], base
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class AtomicCompositionPreregistrationV49R2:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("V49r2 preregistration is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict or canonical_json_bytes(document) != self.canonical_bytes:
            _fail("V49r2 preregistration bytes changed")
        payload = {key: value for key, value in document.items() if key != "atomic_composition_preregistration_id"}
        if document.get("atomic_composition_preregistration_id") != self.preregistration_id or content_id(
            FUTURE_DOMAINS["preregistration"], payload
        ) != self.preregistration_id:
            _fail("V49r2 preregistration identity changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


def freeze_atomic_composition_preregistration_v49r2() -> AtomicCompositionPreregistrationV49R2:
    document = _document()
    raw = canonical_json_bytes(document)
    identity = document["atomic_composition_preregistration_id"]
    if PREREGISTRATION_ID != "0" * 64 and (
        identity != PREREGISTRATION_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V49r2 preregistration changed")
    return AtomicCompositionPreregistrationV49R2(_ISSUER, raw, identity)


def verify_atomic_composition_preregistration_v49r2(
    value: AtomicCompositionPreregistrationV49R2,
) -> AtomicCompositionPreregistrationV49R2:
    if type(value) is not AtomicCompositionPreregistrationV49R2:
        _fail("V49r2 preregistration rejects foreign values")
    value.__post_init__()
    if value.canonical_bytes != canonical_json_bytes(_document()):
        _fail("V49r2 preregistration semantics changed")
    return value


__all__ = (
    "ACTION_FIELD_ORDER",
    "ARMS",
    "AtomicCompositionPreregistrationV49R2",
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
    "freeze_atomic_composition_preregistration_v49r2",
    "verify_atomic_composition_preregistration_v49r2",
)
