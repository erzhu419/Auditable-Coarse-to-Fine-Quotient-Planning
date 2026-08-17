"""Fresh outcome-free successor to the preserved failed V49 campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_atomic_composition_failure_v49 as v49_failure
from acfqp import construction_k7_atomic_composition_preregistration_v49 as v49
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_ATOMIC_COMPOSITION_ADAPTIVE_ACQUISITION_V49R1_DOMAIN,
    CONSTRUCTION_K7_ATOMIC_COMPOSITION_CAMPAIGN_V49R1_DOMAIN,
    CONSTRUCTION_K7_ATOMIC_COMPOSITION_DEPENDENCY_SUPPORT_V49R1_DOMAIN,
    CONSTRUCTION_K7_ATOMIC_COMPOSITION_FAILED_CERTIFICATE_V49R1_DOMAIN,
    CONSTRUCTION_K7_ATOMIC_COMPOSITION_LOCAL_DISTINCTION_V49R1_DOMAIN,
    CONSTRUCTION_K7_ATOMIC_COMPOSITION_OOD_REJECTION_V49R1_DOMAIN,
    CONSTRUCTION_K7_ATOMIC_COMPOSITION_PARTIAL_DYNAMICS_V49R1_DOMAIN,
    CONSTRUCTION_K7_ATOMIC_COMPOSITION_PREREGISTRATION_V49R1_DOMAIN,
    CONSTRUCTION_K7_ATOMIC_COMPOSITION_PROGRAM_V49R1_DOMAIN,
    CONSTRUCTION_K7_ATOMIC_COMPOSITION_RAW_OBSERVATION_V49R1_DOMAIN,
    CONSTRUCTION_K7_ATOMIC_COMPOSITION_RECEDING_EPISODE_V49R1_DOMAIN,
    CONSTRUCTION_K7_ATOMIC_COMPOSITION_SAMPLE_TAX_V49R1_DOMAIN,
    CONSTRUCTION_K7_ATOMIC_COMPOSITION_VERIFICATION_V49R1_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
)


SCHEMA_VERSION = "49.1.0"
PROPOSED_CONTRACT_VERSION = "2.0.216"
PROFILE_KEY = "construction_k7_generic_atomic_composition_v49r1"
PREREGISTRATION_ID = "84d43e3b67e102cd3a3aa7545c5917d5252866e04846b1e8551f45acb1a233fc"
EXPECTED_CANONICAL_BYTE_COUNT = 7_676
EXPECTED_CANONICAL_SHA256 = "a56cdb49f5ef1bcc98ef6ed4462678e873e434a751f9647f8788389bdfb5759e"

V49_PREREGISTRATION_ID = v49.PREREGISTRATION_ID
V49_FAILURE_ID = v49_failure.FAILURE_ID
SOURCE_ROOT = v49.SOURCE_ROOT
BOUND_SOURCE_PATHS = v49.BOUND_SOURCE_PATHS
SOURCE_SPEC = v49.SOURCE_SPEC
SOURCE_SEEDS = (492101, 492102, 492103)
TARGET_SPEC = v49.TARGET_SPEC
TARGET_SEEDS = tuple(range(492301, 492313))
SHARED_MODE_TOKENS = v49.SHARED_MODE_TOKENS
SHARED_CLASS_TOKENS = v49.SHARED_CLASS_TOKENS
SHARED_TERMINAL_TOKENS = v49.SHARED_TERMINAL_TOKENS
STATE_LAYOUT_ORDER = v49.STATE_LAYOUT_ORDER
ACTION_FIELD_ORDER = v49.ACTION_FIELD_ORDER
MAX_SOURCE_LABELS_PER_OCCURRENCE = v49.MAX_SOURCE_LABELS_PER_OCCURRENCE
RECEDING_HORIZON = v49.RECEDING_HORIZON
ARMS = v49.ARMS

FUTURE_DOMAINS = {
    "preregistration": CONSTRUCTION_K7_ATOMIC_COMPOSITION_PREREGISTRATION_V49R1_DOMAIN,
    "observation": CONSTRUCTION_K7_ATOMIC_COMPOSITION_RAW_OBSERVATION_V49R1_DOMAIN,
    "program": CONSTRUCTION_K7_ATOMIC_COMPOSITION_PROGRAM_V49R1_DOMAIN,
    "support": CONSTRUCTION_K7_ATOMIC_COMPOSITION_DEPENDENCY_SUPPORT_V49R1_DOMAIN,
    "failed_certificate": CONSTRUCTION_K7_ATOMIC_COMPOSITION_FAILED_CERTIFICATE_V49R1_DOMAIN,
    "distinction": CONSTRUCTION_K7_ATOMIC_COMPOSITION_LOCAL_DISTINCTION_V49R1_DOMAIN,
    "episode": CONSTRUCTION_K7_ATOMIC_COMPOSITION_RECEDING_EPISODE_V49R1_DOMAIN,
    "partial": CONSTRUCTION_K7_ATOMIC_COMPOSITION_PARTIAL_DYNAMICS_V49R1_DOMAIN,
    "acquisition": CONSTRUCTION_K7_ATOMIC_COMPOSITION_ADAPTIVE_ACQUISITION_V49R1_DOMAIN,
    "sample_tax": CONSTRUCTION_K7_ATOMIC_COMPOSITION_SAMPLE_TAX_V49R1_DOMAIN,
    "ood": CONSTRUCTION_K7_ATOMIC_COMPOSITION_OOD_REJECTION_V49R1_DOMAIN,
    "campaign": CONSTRUCTION_K7_ATOMIC_COMPOSITION_CAMPAIGN_V49R1_DOMAIN,
    "verification": CONSTRUCTION_K7_ATOMIC_COMPOSITION_VERIFICATION_V49R1_DOMAIN,
}


class ConstructionK7AtomicCompositionPreregistrationV49R1Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7AtomicCompositionPreregistrationV49R1Error(message)


def _document() -> dict[str, Any]:
    base = v49.freeze_atomic_composition_preregistration_v49().to_document()
    base.pop("atomic_composition_preregistration_id")
    base["schema"] = "acfqp.atomic_composition_preregistration.v49r1"
    base["schema_version"] = SCHEMA_VERSION
    base["proposed_contract_version"] = PROPOSED_CONTRACT_VERSION
    base["profile_key"] = PROFILE_KEY
    base["frozen_predecessor"] = {
        "v49_preregistration_id": V49_PREREGISTRATION_ID,
        "v49_failure_id": V49_FAILURE_ID,
        "failed_predecessor_preserved_without_correction": True,
        "v49_first_target_local_query_count": 1,
        "v49_campaign_artifact_issued": False,
    }
    base["source_closure"]["frozen_before_any_v49_source_or_target_outcome"] = False
    base["source_closure"]["frozen_before_any_v49r1_source_or_target_outcome"] = True
    workload = base["fresh_workload"]
    workload["source_seeds"] = list(SOURCE_SEEDS)
    workload["target_seeds"] = list(TARGET_SEEDS)
    workload["all_source_and_target_seed_identities_fresh_after_v48"] = False
    workload["all_source_and_target_seed_identities_fresh_after_v49_failure"] = True
    base["recovery_correction"] = {
        "correction": "ACCEPT_E00_OR_E03_ANONYMOUS_MODULUS_OPERAND_IN_COMPILED_AST",
        "correction_frozen_before_v49r1_outcomes": True,
        "no_change_to_generic_composer_or_environment_kernel": True,
        "same_identity_rerun_forbidden": True,
    }
    base["claim_boundary"]["v49_failure_preserved"] = True
    base["fresh_v49_outcome_execution_performed"] = False
    base["fresh_v49r1_outcome_execution_performed"] = False
    base["future_content_domains"] = FUTURE_DOMAINS
    return {
        **base,
        "atomic_composition_preregistration_id": content_id(
            FUTURE_DOMAINS["preregistration"], base
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class AtomicCompositionPreregistrationV49R1:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("V49r1 preregistration is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict or canonical_json_bytes(document) != self.canonical_bytes:
            _fail("V49r1 preregistration bytes changed")
        payload = {
            key: value
            for key, value in document.items()
            if key != "atomic_composition_preregistration_id"
        }
        if (
            document.get("atomic_composition_preregistration_id") != self.preregistration_id
            or content_id(FUTURE_DOMAINS["preregistration"], payload) != self.preregistration_id
        ):
            _fail("V49r1 preregistration identity changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


def freeze_atomic_composition_preregistration_v49r1() -> AtomicCompositionPreregistrationV49R1:
    document = _document()
    raw = canonical_json_bytes(document)
    identity = document["atomic_composition_preregistration_id"]
    if PREREGISTRATION_ID != "0" * 64 and (
        identity != PREREGISTRATION_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V49r1 preregistration changed")
    return AtomicCompositionPreregistrationV49R1(_ISSUER, raw, identity)


def verify_atomic_composition_preregistration_v49r1(
    value: AtomicCompositionPreregistrationV49R1,
) -> AtomicCompositionPreregistrationV49R1:
    if type(value) is not AtomicCompositionPreregistrationV49R1:
        _fail("V49r1 preregistration rejects foreign values")
    value.__post_init__()
    if value.canonical_bytes != canonical_json_bytes(_document()):
        _fail("V49r1 preregistration semantics changed")
    return value


__all__ = (
    "ACTION_FIELD_ORDER",
    "ARMS",
    "AtomicCompositionPreregistrationV49R1",
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
    "freeze_atomic_composition_preregistration_v49r1",
    "verify_atomic_composition_preregistration_v49r1",
)
