"""Non-circular H1 predecision current-access authority boundary.

Contract 2.0.57 separates observed current access from every later route
decision object.  A context binds the already-issued Contract-2.0.52 current
source and claimant proof to one occurrence/attempt/epoch/nonce.  An
append-only recorder then commits the exact predecision access sequence.  A
production authority can be issued only from retained fresh-exec evidence
whose independent verifier reports
``OBSERVED_RUNTIME_PLUS_EXHAUSTIVE_CAPABILITY_CLOSURE``.

Construction fixtures have separate issuers, domains and status values.  They
can exercise schemas and cutoff attacks, but can never mint the production
authority.  In particular, no test-only or caller-selected ``observed=True``
escape hatch exists.

The production authority intentionally contains no decision point, selected
plan/route, common-prefix work, route upper/decision, or route-freeze fields.
Those belong to a future downstream join.  This module does not perform that
join and does not unlock official execution or any Gate.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from enum import Enum
import hashlib
import hmac
import threading
from typing import Any, NoReturn

from acfqp.construction_k7_h1_production_current_identity_v1 import (
    H1CurrentSourceFixtureV1,
    H1DurableProofMatchAttestationV1,
    H1ProductionCurrentIdentityCandidateV1,
    H1ProductionCurrentIdentityCandidateVerificationV1,
)
from acfqp.construction_k7_h1_direct_fallback_two_role_recipe_v1 import (
    H1DirectFallbackTwoRoleRecipeV1,
)
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_H1_CURRENT_ACCESS_AUTHORITY_BLOCKER_V1_DOMAIN,
    CONSTRUCTION_K7_H1_CURRENT_ACCESS_CHILD_RESULT_V1_DOMAIN,
    CONSTRUCTION_K7_H1_CURRENT_ACCESS_CONSTRUCTION_FIXTURE_V1_DOMAIN,
    CONSTRUCTION_K7_H1_CURRENT_ACCESS_EXECUTION_PROFILE_V1_DOMAIN,
    CONSTRUCTION_K7_H1_CURRENT_ACCESS_OBSERVED_EVIDENCE_V1_DOMAIN,
    CONSTRUCTION_K7_H1_CURRENT_ACCESS_PREDECISION_CONTEXT_V1_DOMAIN,
    CONSTRUCTION_K7_H1_CURRENT_ACCESS_PREDECISION_INPUT_SET_V1_DOMAIN,
    CONSTRUCTION_K7_H1_PREDECISION_ACCESS_EVENT_V1_DOMAIN,
    CONSTRUCTION_K7_H1_PREDECISION_ACCESS_LOG_V1_DOMAIN,
    CONSTRUCTION_K7_H1_PREDECISION_CURRENT_ACCESS_CUTOFF_V1_DOMAIN,
    CONSTRUCTION_K7_H1_PRODUCTION_CURRENT_ACCESS_AUTHORITY_V1_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    canonical_json_bytes,
    content_id,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.57"
PROFILE_KEY = "construction_k7_h1_current_access_authority_v1"

CONSTRUCTION_ONLY = False
FRESH_EXEC_RUNTIME_EVIDENCE_INTEGRATED = True
PRODUCTION_CURRENT_ACCESS_AUTHORITY_PRESENT = True
FUTURE_FORMAL_V7_JOIN_PRESENT = False
OFFICIAL_EXECUTION_ALLOWED = False
OFFICIAL_SCALAR_COST = None
OFFICIAL_N_BREAK_EVEN = None
COUNTER_COMPLETENESS_GATE_STATUS = "COUNTER_COMPLETENESS_GATE_NOT_RUN"
WORKLOAD_ECONOMICS_GATE_STATUS = "WORKLOAD_ECONOMICS_GATE_NOT_RUN"
SAMPLE_EFFICIENCY_GATE_STATUS = "SAMPLE_EFFICIENCY_GATE_NOT_RUN"

PROFILE_DOMAIN = CONSTRUCTION_K7_H1_CURRENT_ACCESS_EXECUTION_PROFILE_V1_DOMAIN
CONTEXT_DOMAIN = CONSTRUCTION_K7_H1_CURRENT_ACCESS_PREDECISION_CONTEXT_V1_DOMAIN
INPUT_SET_DOMAIN = CONSTRUCTION_K7_H1_CURRENT_ACCESS_PREDECISION_INPUT_SET_V1_DOMAIN
EVENT_DOMAIN = CONSTRUCTION_K7_H1_PREDECISION_ACCESS_EVENT_V1_DOMAIN
LOG_DOMAIN = CONSTRUCTION_K7_H1_PREDECISION_ACCESS_LOG_V1_DOMAIN
CHILD_RESULT_DOMAIN = CONSTRUCTION_K7_H1_CURRENT_ACCESS_CHILD_RESULT_V1_DOMAIN
EVIDENCE_DOMAIN = CONSTRUCTION_K7_H1_CURRENT_ACCESS_OBSERVED_EVIDENCE_V1_DOMAIN
CUTOFF_DOMAIN = CONSTRUCTION_K7_H1_PREDECISION_CURRENT_ACCESS_CUTOFF_V1_DOMAIN
AUTHORITY_DOMAIN = CONSTRUCTION_K7_H1_PRODUCTION_CURRENT_ACCESS_AUTHORITY_V1_DOMAIN
FIXTURE_DOMAIN = CONSTRUCTION_K7_H1_CURRENT_ACCESS_CONSTRUCTION_FIXTURE_V1_DOMAIN
BLOCKER_DOMAIN = CONSTRUCTION_K7_H1_CURRENT_ACCESS_AUTHORITY_BLOCKER_V1_DOMAIN

REQUESTED_PHASE3E_DOMAIN_TAGS = (
    PROFILE_DOMAIN,
    CONTEXT_DOMAIN,
    INPUT_SET_DOMAIN,
    EVENT_DOMAIN,
    LOG_DOMAIN,
    CHILD_RESULT_DOMAIN,
    EVIDENCE_DOMAIN,
    CUTOFF_DOMAIN,
    AUTHORITY_DOMAIN,
    FIXTURE_DOMAIN,
    BLOCKER_DOMAIN,
)
if (
    len(set(REQUESTED_PHASE3E_DOMAIN_TAGS)) != len(REQUESTED_PHASE3E_DOMAIN_TAGS)
    or not set(REQUESTED_PHASE3E_DOMAIN_TAGS) <= PHASE3E_DOMAIN_TAGS
):  # pragma: no cover - import-time registry invariant
    raise RuntimeError("H1 current-access authority domains are not registered")


class ConstructionK7H1CurrentAccessAuthorityV1Error(ValueError):
    """A current-access context, log, evidence, or authority failed closed."""


class H1CurrentAccessAuthorityBlockedV1(
    ConstructionK7H1CurrentAccessAuthorityV1Error
):
    """Observed fresh-exec evidence is absent; this is not a certificate."""

    terminal_scope = "ROUTE_ATTEMPT"
    terminal_class = "ATTEMPT_CLOSURE_NONCERTIFICATE"
    terminal_code = "PROTOCOL_FAILURE"
    certificate_issued = False


class H1CurrentAccessEvidenceStatusV1(str, Enum):
    CONSTRUCTION_FIXTURE_ONLY = "CONSTRUCTION_FIXTURE_ONLY"
    OBSERVED_RUNTIME_PLUS_EXHAUSTIVE_CAPABILITY_CLOSURE = (
        "OBSERVED_RUNTIME_PLUS_EXHAUSTIVE_CAPABILITY_CLOSURE"
    )


REQUIRED_RUNTIME_VERIFICATION_STATUS = (
    H1CurrentAccessEvidenceStatusV1.
    OBSERVED_RUNTIME_PLUS_EXHAUSTIVE_CAPABILITY_CLOSURE.value
)


class H1PredecisionAccessOperationV1(str, Enum):
    CURRENT_SOURCE_FIXTURE_REPLAYED = "CURRENT_SOURCE_FIXTURE_REPLAYED"
    PROOF_MATCH_ATTESTATION_REPLAYED = "PROOF_MATCH_ATTESTATION_REPLAYED"
    FRESH_EXEC_RUNTIME_VERIFICATION_ACCEPTED = (
        "FRESH_EXEC_RUNTIME_VERIFICATION_ACCEPTED"
    )
    EXHAUSTIVE_CAPABILITY_CLOSURE_VERIFIED = (
        "EXHAUSTIVE_CAPABILITY_CLOSURE_VERIFIED"
    )
    FORMAL_V7_DECISION_VERIFIED = "FORMAL_V7_DECISION_VERIFIED"
    ROUTE_DECISION_FROZEN = "ROUTE_DECISION_FROZEN"


EXPECTED_OPERATION_SEQUENCE = tuple(
    item.value for item in tuple(H1PredecisionAccessOperationV1)[:4]
)
REGISTERED_POSTCUTOFF_OPERATION_SEQUENCE = tuple(
    item.value for item in tuple(H1PredecisionAccessOperationV1)[4:]
)
REGISTERED_OPERATION_SEQUENCE = (
    *EXPECTED_OPERATION_SEQUENCE,
    *REGISTERED_POSTCUTOFF_OPERATION_SEQUENCE,
)
FORBIDDEN_PREDECISION_OPERATIONS = (
    "CAPABILITY_COMPILER",
    "DURABLE_PROOF_PRODUCER",
    "FALLBACK_SOLVER",
    "GROUND_OUTCOME_ENUMERATION",
    "J0_OR_OTHER_PLANNER",
    "KERNEL_STEP",
    "LOCAL_MATERIALIZATION",
    "LOCAL_POSTAUDIT",
    "LOCAL_SOLVER",
    "POSTRUN_RESULT_READ",
)


_PROFILE_ISSUER = object()
_CONTEXT_ISSUER = object()
_INPUT_SET_ISSUER = object()
_EVENT_ISSUER = object()
_LOG_ISSUER = object()
_CUTOFF_ISSUER = object()
_CHILD_RUNTIME_ISSUER = object()
_CHILD_FIXTURE_ISSUER = object()
_EVIDENCE_RUNTIME_ISSUER = object()
_EVIDENCE_FIXTURE_ISSUER = object()
_AUTHORITY_ISSUER = object()
_BLOCKER_ISSUER = object()

_LIVE_PROFILES: dict[int, tuple[object, bytes]] = {}
_LIVE_CONTEXTS: dict[int, tuple[object, bytes]] = {}
_LIVE_INPUT_SETS: dict[int, tuple[object, bytes]] = {}
_LIVE_EVENTS: dict[int, tuple[object, bytes]] = {}
_LIVE_LOGS: dict[int, tuple[object, bytes]] = {}
_LIVE_CUTOFFS: dict[int, tuple[object, bytes]] = {}
_LIVE_CHILD_RESULTS: dict[int, tuple[object, bytes, str]] = {}
_LIVE_EVIDENCE: dict[int, tuple[Any, ...]] = {}
_LIVE_AUTHORITIES: dict[int, list[Any]] = {}
_AUTHORITY_ISSUED_EVIDENCE_IDS: set[int] = set()
_LIVE_BLOCKERS: dict[int, tuple[object, bytes]] = {}
_RETENTION_LOCK = threading.RLock()


def _fail(message: str) -> NoReturn:
    raise ConstructionK7H1CurrentAccessAuthorityV1Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7H1CurrentAccessAuthorityV1Error(
            f"{label} must be one exact lowercase content ID"
        ) from error


def _positive(value: Any, label: str) -> int:
    if type(value) is not int or value <= 0:
        _fail(f"{label} must be one positive exact integer")
    return value


def _nonce(value: Any) -> str:
    return _cid(value, "session nonce")


def _sha256(raw: bytes) -> str:
    if type(raw) is not bytes or not raw:
        _fail("sealed input canonical bytes are missing")
    return hashlib.sha256(raw).hexdigest()


def _retain(
    registry: dict[int, Any],
    value: object,
    raw: bytes,
    *extra: Any,
) -> None:
    with _RETENTION_LOCK:
        if id(value) in registry:
            _fail("current-access object was retained twice")
        registry[id(value)] = (value, raw, *extra)


def _require_live(
    registry: dict[int, Any],
    value: Any,
    expected_type: type,
    label: str,
) -> tuple[Any, ...]:
    if type(value) is not expected_type:
        _fail(f"{label} has a foreign type")
    with _RETENTION_LOCK:
        retained = registry.get(id(value))
    if retained is None or retained[0] is not value:
        _fail(f"{label} is not one retained issuer object")
    try:
        current = canonical_json_bytes(value.to_document())
    except Exception as error:
        raise ConstructionK7H1CurrentAccessAuthorityV1Error(
            f"{label} failed canonical replay"
        ) from error
    if not hmac.compare_digest(current, retained[1]):
        _fail(f"{label} changed after issuance")
    return retained


def _official_runtime_prelaunch_objects() -> tuple[Any, Any, Any]:
    """Load and validate the complementary deterministic prelaunch manifests."""

    try:
        from acfqp import construction_k7_h1_current_access_fresh_exec_runtime_v1 as runtime_v1
    except ImportError as error:
        raise H1CurrentAccessAuthorityBlockedV1(
            "fresh-exec current-access runtime profile is unavailable"
        ) from error
    names = (
        "fresh_exec_runtime_profile",
        "fresh_exec_source_manifest",
        "fresh_exec_runtime_manifest",
    )
    values: list[Any] = []
    for name in names:
        factory = getattr(runtime_v1, f"official_h1_current_access_{name}_v1", None)
        require = getattr(runtime_v1, f"require_h1_current_access_{name}_v1", None)
        if not callable(factory) or not callable(require):
            raise H1CurrentAccessAuthorityBlockedV1(
                f"fresh-exec {name} API is unavailable"
            )
        value = factory()
        if require(value) is not value:
            raise H1CurrentAccessAuthorityBlockedV1(
                f"fresh-exec {name} is not one retained object"
            )
        values.append(value)
    return values[0], values[1], values[2]


@dataclass(frozen=True, slots=True)
class H1CurrentAccessExecutionProfileV1:
    _issuer: InitVar[object]
    fresh_exec_runtime_profile_id: str
    fresh_exec_source_manifest_id: str
    fresh_exec_runtime_manifest_id: str
    _profile_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _PROFILE_ISSUER:
            _fail("H1 current-access execution profile is caller-minted")
        for value, label in (
            (self.fresh_exec_runtime_profile_id, "fresh-exec runtime profile"),
            (self.fresh_exec_source_manifest_id, "fresh-exec source manifest"),
            (self.fresh_exec_runtime_manifest_id, "fresh-exec runtime manifest"),
        ):
            _cid(value, label)
        object.__setattr__(self, "_profile_id", content_id(PROFILE_DOMAIN, self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h1_current_access_execution_profile.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "stage_scope": "PREDECISION_CURRENT_ACCESS",
            "h1_current_access_fresh_exec_runtime_profile_id": (
                self.fresh_exec_runtime_profile_id
            ),
            "h1_current_access_fresh_exec_source_manifest_id": (
                self.fresh_exec_source_manifest_id
            ),
            "h1_current_access_fresh_exec_runtime_manifest_id": (
                self.fresh_exec_runtime_manifest_id
            ),
            "expected_operation_sequence": list(EXPECTED_OPERATION_SEQUENCE),
            "registered_postcutoff_operation_sequence": list(
                REGISTERED_POSTCUTOFF_OPERATION_SEQUENCE
            ),
            "forbidden_predecision_operations": list(FORBIDDEN_PREDECISION_OPERATIONS),
            "required_runtime_verification_status": REQUIRED_RUNTIME_VERIFICATION_STATUS,
            "append_only_access_log_required": True,
            "cutoff_must_equal_current_log_head": True,
            "downstream_route_authority_join_present": False,
            "construction_only": False,
            "official_execution_allowed": False,
        }

    @property
    def profile_id(self) -> str:
        _require_live(_LIVE_PROFILES, self, H1CurrentAccessExecutionProfileV1, "execution profile")
        return self._profile_id

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "h1_current_access_execution_profile_id": self._profile_id}


def official_h1_current_access_execution_profile_v1() -> H1CurrentAccessExecutionProfileV1:
    runtime_profile, source_manifest, runtime_manifest = (
        _official_runtime_prelaunch_objects()
    )
    value = H1CurrentAccessExecutionProfileV1(
        _PROFILE_ISSUER,
        runtime_profile.h1_current_access_fresh_exec_runtime_profile_id,
        source_manifest.h1_current_access_fresh_exec_source_manifest_id,
        runtime_manifest.h1_current_access_fresh_exec_runtime_manifest_id,
    )
    _retain(_LIVE_PROFILES, value, canonical_json_bytes(value.to_document()))
    return value


SEALED_INPUT_ROLES = (
    "PREDECISION_CONTEXT",
    "CURRENT_SOURCE_FIXTURE",
    "PROOF_MATCH_ATTESTATION",
    "H1_TWO_ROLE_RECIPE",
    "CURRENT_IDENTITY_CANDIDATE",
    "CANDIDATE_VERIFICATION",
)


@dataclass(frozen=True, slots=True)
class H1PredecisionSealedInputRowV1:
    role: str
    artifact_id: str
    sha256: str
    byte_count: int

    def __post_init__(self) -> None:
        if self.role not in SEALED_INPUT_ROLES:
            _fail("H1 sealed input role is not registered")
        _cid(self.artifact_id, f"{self.role} artifact")
        if (
            type(self.sha256) is not str
            or len(self.sha256) != 64
            or any(character not in "0123456789abcdef" for character in self.sha256)
        ):
            _fail(f"{self.role} SHA-256 is invalid")
        _positive(self.byte_count, f"{self.role} byte count")

    def to_document(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "artifact_id": self.artifact_id,
            "sha256": self.sha256,
            "byte_count": self.byte_count,
        }


def _sealed_input_row(
    role: str,
    artifact_id: str,
    raw: bytes,
) -> H1PredecisionSealedInputRowV1:
    return H1PredecisionSealedInputRowV1(
        role,
        _cid(artifact_id, f"{role} artifact"),
        _sha256(raw),
        len(raw),
    )


@dataclass(frozen=True, slots=True)
class H1CurrentAccessPredecisionContextV1:
    _issuer: InitVar[object]
    execution_profile_id: str
    current_source_fixture_id: str
    proof_match_attestation_id: str
    recipe_id: str
    current_identity_candidate_id: str
    candidate_verification_id: str
    fresh_exec_runtime_profile_id: str
    fresh_exec_source_manifest_id: str
    fresh_exec_runtime_manifest_id: str
    precontext_sealed_inputs: tuple[H1PredecisionSealedInputRowV1, ...]
    exact_infeasibility_identity_id: str
    structural_id: str
    query_id: str
    build_epoch_id: str
    kernel_id: str
    threshold_profile_id: str
    reward_profile_id: str
    policy_class_id: str
    complete_search_profile_id: str
    logical_occurrence_id: str
    route_attempt_id: str
    session_nonce: str
    _context_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _CONTEXT_ISSUER:
            _fail("H1 current-access predecision context is caller-minted")
        for value, label in (
            (self.execution_profile_id, "execution profile"),
            (self.current_source_fixture_id, "current-source fixture"),
            (self.proof_match_attestation_id, "proof-match attestation"),
            (self.recipe_id, "H1 two-role recipe"),
            (self.current_identity_candidate_id, "current-identity candidate"),
            (self.candidate_verification_id, "candidate verification"),
            (self.fresh_exec_runtime_profile_id, "fresh-exec runtime profile"),
            (self.fresh_exec_source_manifest_id, "fresh-exec source manifest"),
            (self.fresh_exec_runtime_manifest_id, "fresh-exec runtime manifest"),
            (self.exact_infeasibility_identity_id, "exact infeasibility identity"),
            (self.structural_id, "structural identity"),
            (self.query_id, "query identity"),
            (self.build_epoch_id, "BuildEpoch identity"),
            (self.kernel_id, "kernel identity"),
            (self.threshold_profile_id, "threshold identity"),
            (self.reward_profile_id, "reward identity"),
            (self.policy_class_id, "policy-class identity"),
            (self.complete_search_profile_id, "complete-search identity"),
            (self.logical_occurrence_id, "logical occurrence"),
            (self.route_attempt_id, "route attempt"),
            (self.session_nonce, "session nonce"),
        ):
            _cid(value, label)
        if (
            type(self.precontext_sealed_inputs) is not tuple
            or tuple(row.role for row in self.precontext_sealed_inputs)
            != SEALED_INPUT_ROLES[1:]
            or any(type(row) is not H1PredecisionSealedInputRowV1 for row in self.precontext_sealed_inputs)
        ):
            _fail("H1 precontext sealed inputs are not the exact five-row prefix")
        object.__setattr__(self, "_context_id", content_id(CONTEXT_DOMAIN, self._payload()))

    @property
    def identity_document(self) -> dict[str, str]:
        return {
            "structural_id": self.structural_id,
            "query_id": self.query_id,
            "BuildEpoch_id": self.build_epoch_id,
            "kernel_id": self.kernel_id,
            "threshold_profile_id": self.threshold_profile_id,
            "reward_profile_id": self.reward_profile_id,
            "policy_class_id": self.policy_class_id,
            "complete_search_profile_id": self.complete_search_profile_id,
        }

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h1_current_access_predecision_context.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "h1_current_access_execution_profile_id": self.execution_profile_id,
            "h1_current_source_fixture_id": self.current_source_fixture_id,
            "h1_durable_proof_match_attestation_id": self.proof_match_attestation_id,
            "h1_direct_fallback_two_role_recipe_id": self.recipe_id,
            "h1_production_current_identity_candidate_id": (
                self.current_identity_candidate_id
            ),
            "h1_production_current_identity_candidate_verification_id": (
                self.candidate_verification_id
            ),
            "h1_current_access_fresh_exec_runtime_profile_id": (
                self.fresh_exec_runtime_profile_id
            ),
            "h1_current_access_fresh_exec_source_manifest_id": (
                self.fresh_exec_source_manifest_id
            ),
            "h1_current_access_fresh_exec_runtime_manifest_id": (
                self.fresh_exec_runtime_manifest_id
            ),
            "precontext_sealed_inputs": [
                row.to_document() for row in self.precontext_sealed_inputs
            ],
            "exact_infeasibility_identity_id": self.exact_infeasibility_identity_id,
            **self.identity_document,
            "logical_occurrence_id": self.logical_occurrence_id,
            "route_attempt_id": self.route_attempt_id,
            "session_nonce": self.session_nonce,
            "stage_scope": "PREDECISION_CURRENT_ACCESS",
            "downstream_route_authority_join_present": False,
        }

    @property
    def context_id(self) -> str:
        _require_live(_LIVE_CONTEXTS, self, H1CurrentAccessPredecisionContextV1, "predecision context")
        return self._context_id

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "h1_current_access_predecision_context_id": self._context_id}


def freeze_h1_current_access_predecision_context_v1(
    *,
    execution_profile: H1CurrentAccessExecutionProfileV1,
    current_source: H1CurrentSourceFixtureV1,
    proof_match_attestation: H1DurableProofMatchAttestationV1,
    recipe: H1DirectFallbackTwoRoleRecipeV1,
    current_identity_candidate: H1ProductionCurrentIdentityCandidateV1,
    candidate_verification: H1ProductionCurrentIdentityCandidateVerificationV1,
    logical_occurrence_id: str,
    route_attempt_id: str,
    session_nonce: str,
) -> H1CurrentAccessPredecisionContextV1:
    _require_live(_LIVE_PROFILES, execution_profile, H1CurrentAccessExecutionProfileV1, "execution profile")
    if type(current_source) is not H1CurrentSourceFixtureV1:
        _fail("current source must be the exact Contract-2.0.52 type")
    if type(proof_match_attestation) is not H1DurableProofMatchAttestationV1:
        _fail("proof match must be the exact Contract-2.0.52 type")
    if type(recipe) is not H1DirectFallbackTwoRoleRecipeV1:
        _fail("H1 recipe must be the exact Contract-2.0.50 type")
    if type(current_identity_candidate) is not H1ProductionCurrentIdentityCandidateV1:
        _fail("current identity must be the exact Contract-2.0.52 candidate type")
    if type(candidate_verification) is not H1ProductionCurrentIdentityCandidateVerificationV1:
        _fail("current-identity verification must be the exact Contract-2.0.52 type")
    source_id = current_source.fixture_id
    proof_id = proof_match_attestation.attestation_id
    recipe_id = recipe.recipe_id
    current_candidate_id = current_identity_candidate.candidate_id
    candidate_verification_id = candidate_verification.verification_id
    identity = current_source.identity
    if (
        proof_match_attestation.current_source_fixture_id != source_id
        or proof_match_attestation.exact_identity_id
        != identity.exact_infeasibility_identity_id
        or proof_match_attestation.recipe_id != recipe_id
        or current_identity_candidate.current_source is not current_source
        or current_identity_candidate.proof_match is not proof_match_attestation
        or current_identity_candidate.recipe is not recipe
        or candidate_verification.candidate_id != current_candidate_id
        or candidate_verification.current_source_fixture_id != source_id
        or candidate_verification.proof_match_attestation_id != proof_id
        or candidate_verification.recipe_id != recipe_id
        or proof_match_attestation.recipe_chain.get("logical_occurrence_id")
        != _cid(logical_occurrence_id, "logical occurrence")
        or proof_match_attestation.recipe_chain.get("route_attempt_id")
        != _cid(route_attempt_id, "route attempt")
    ):
        _fail("Contract-2.0.52 current source/proof/attempt identities differ")
    source_raw = current_source.canonical_bytes
    proof_raw = canonical_json_bytes(proof_match_attestation.to_document())
    recipe_raw = recipe.canonical_bytes
    candidate_raw = current_identity_candidate.canonical_bytes
    verification_raw = canonical_json_bytes(candidate_verification.to_document())
    precontext_rows = tuple(
        _sealed_input_row(role, artifact_id, raw)
        for role, artifact_id, raw in (
            ("CURRENT_SOURCE_FIXTURE", source_id, source_raw),
            ("PROOF_MATCH_ATTESTATION", proof_id, proof_raw),
            ("H1_TWO_ROLE_RECIPE", recipe_id, recipe_raw),
            ("CURRENT_IDENTITY_CANDIDATE", current_candidate_id, candidate_raw),
            ("CANDIDATE_VERIFICATION", candidate_verification_id, verification_raw),
        )
    )
    value = H1CurrentAccessPredecisionContextV1(
        _CONTEXT_ISSUER,
        execution_profile.profile_id,
        source_id,
        proof_id,
        recipe_id,
        current_candidate_id,
        candidate_verification_id,
        execution_profile.fresh_exec_runtime_profile_id,
        execution_profile.fresh_exec_source_manifest_id,
        execution_profile.fresh_exec_runtime_manifest_id,
        precontext_rows,
        identity.exact_infeasibility_identity_id,
        identity.structural_id,
        identity.query_id,
        identity.build_epoch_id,
        identity.kernel_id,
        identity.threshold_profile_id,
        identity.reward_profile_id,
        identity.policy_class_id,
        identity.complete_search_profile_id,
        logical_occurrence_id,
        route_attempt_id,
        _nonce(session_nonce),
    )
    _retain(_LIVE_CONTEXTS, value, canonical_json_bytes(value.to_document()))
    return value


@dataclass(frozen=True, slots=True)
class H1CurrentAccessPredecisionInputSetV1:
    """Launch context that adds the semantic-context bytes without self-reference."""

    _issuer: InitVar[object]
    execution_profile_id: str
    context_id: str
    fresh_exec_runtime_profile_id: str
    fresh_exec_source_manifest_id: str
    fresh_exec_runtime_manifest_id: str
    sealed_inputs: tuple[H1PredecisionSealedInputRowV1, ...]
    _input_set_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _INPUT_SET_ISSUER:
            _fail("H1 current-access predecision input set is caller-minted")
        for value, label in (
            (self.execution_profile_id, "execution profile"),
            (self.context_id, "predecision context"),
            (self.fresh_exec_runtime_profile_id, "fresh-exec runtime profile"),
            (self.fresh_exec_source_manifest_id, "fresh-exec source manifest"),
            (self.fresh_exec_runtime_manifest_id, "fresh-exec runtime manifest"),
        ):
            _cid(value, label)
        if (
            type(self.sealed_inputs) is not tuple
            or tuple(row.role for row in self.sealed_inputs) != SEALED_INPUT_ROLES
            or any(type(row) is not H1PredecisionSealedInputRowV1 for row in self.sealed_inputs)
            or self.sealed_inputs[0].artifact_id != self.context_id
        ):
            _fail("H1 predecision input set is not the exact six-row launch set")
        object.__setattr__(
            self,
            "_input_set_id",
            content_id(INPUT_SET_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h1_current_access_predecision_input_set.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "h1_current_access_predecision_context_id": self.context_id,
            "h1_current_access_execution_profile_id": self.execution_profile_id,
            "h1_current_access_fresh_exec_runtime_profile_id": (
                self.fresh_exec_runtime_profile_id
            ),
            "h1_current_access_fresh_exec_source_manifest_id": (
                self.fresh_exec_source_manifest_id
            ),
            "h1_current_access_fresh_exec_runtime_manifest_id": (
                self.fresh_exec_runtime_manifest_id
            ),
            "sealed_inputs": [row.to_document() for row in self.sealed_inputs],
            "semantic_context_contains_input_set_backreference": False,
            "launch_input_set_frozen_before_fresh_exec": True,
        }

    @property
    def input_set_id(self) -> str:
        _require_live(
            _LIVE_INPUT_SETS,
            self,
            H1CurrentAccessPredecisionInputSetV1,
            "predecision input set",
        )
        return self._input_set_id

    @property
    def h1_current_access_predecision_input_set_id(self) -> str:
        return self.input_set_id

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "h1_current_access_predecision_input_set_id": self._input_set_id,
        }


def freeze_h1_current_access_predecision_input_set_v1(
    *,
    execution_profile: H1CurrentAccessExecutionProfileV1,
    context: H1CurrentAccessPredecisionContextV1,
) -> H1CurrentAccessPredecisionInputSetV1:
    _require_live(
        _LIVE_PROFILES,
        execution_profile,
        H1CurrentAccessExecutionProfileV1,
        "execution profile",
    )
    _require_live(
        _LIVE_CONTEXTS,
        context,
        H1CurrentAccessPredecisionContextV1,
        "predecision context",
    )
    if (
        context.execution_profile_id != execution_profile.profile_id
        or context.fresh_exec_runtime_profile_id
        != execution_profile.fresh_exec_runtime_profile_id
        or context.fresh_exec_source_manifest_id
        != execution_profile.fresh_exec_source_manifest_id
        or context.fresh_exec_runtime_manifest_id
        != execution_profile.fresh_exec_runtime_manifest_id
    ):
        _fail("H1 predecision input set crossed its profile/context manifests")
    context_row = _sealed_input_row(
        "PREDECISION_CONTEXT",
        context.context_id,
        context.canonical_bytes,
    )
    value = H1CurrentAccessPredecisionInputSetV1(
        _INPUT_SET_ISSUER,
        execution_profile.profile_id,
        context.context_id,
        execution_profile.fresh_exec_runtime_profile_id,
        execution_profile.fresh_exec_source_manifest_id,
        execution_profile.fresh_exec_runtime_manifest_id,
        (context_row, *context.precontext_sealed_inputs),
    )
    _retain(_LIVE_INPUT_SETS, value, canonical_json_bytes(value.to_document()))
    return value


def require_h1_current_access_predecision_input_set_v1(
    value: Any,
) -> H1CurrentAccessPredecisionInputSetV1:
    _require_live(
        _LIVE_INPUT_SETS,
        value,
        H1CurrentAccessPredecisionInputSetV1,
        "predecision input set",
    )
    return value


@dataclass(frozen=True, slots=True)
class H1PredecisionAccessEventV1:
    _issuer: InitVar[object]
    execution_profile_id: str
    context_id: str
    logical_occurrence_id: str
    route_attempt_id: str
    build_epoch_id: str
    session_nonce: str
    sequence: int
    operation: str
    resource_id: str
    predecessor_event_id: str | None
    _event_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _EVENT_ISSUER:
            _fail("H1 predecision access event is caller-minted")
        for value, label in (
            (self.execution_profile_id, "execution profile"),
            (self.context_id, "predecision context"),
            (self.logical_occurrence_id, "logical occurrence"),
            (self.route_attempt_id, "route attempt"),
            (self.build_epoch_id, "BuildEpoch"),
            (self.session_nonce, "session nonce"),
            (self.resource_id, "access resource"),
        ):
            _cid(value, label)
        _positive(self.sequence, "access sequence")
        if self.operation not in REGISTERED_OPERATION_SEQUENCE:
            _fail("H1 predecision access operation is outside the exact profile")
        if self.predecessor_event_id is not None:
            _cid(self.predecessor_event_id, "predecessor event")
        object.__setattr__(self, "_event_id", content_id(EVENT_DOMAIN, self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h1_predecision_access_event.v1",
            "schema_version": SCHEMA_VERSION,
            "h1_current_access_execution_profile_id": self.execution_profile_id,
            "h1_current_access_predecision_context_id": self.context_id,
            "logical_occurrence_id": self.logical_occurrence_id,
            "route_attempt_id": self.route_attempt_id,
            "BuildEpoch_id": self.build_epoch_id,
            "session_nonce": self.session_nonce,
            "sequence": self.sequence,
            "operation": self.operation,
            "resource_id": self.resource_id,
            "predecessor_event_id": self.predecessor_event_id,
        }

    @property
    def event_id(self) -> str:
        _require_live(_LIVE_EVENTS, self, H1PredecisionAccessEventV1, "access event")
        return self._event_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "h1_predecision_access_event_id": self._event_id}


@dataclass(frozen=True, slots=True)
class H1PredecisionAccessLogV1:
    _issuer: InitVar[object]
    execution_profile_id: str
    context_id: str
    logical_occurrence_id: str
    route_attempt_id: str
    build_epoch_id: str
    session_nonce: str
    events: tuple[H1PredecisionAccessEventV1, ...]
    _log_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _LOG_ISSUER:
            _fail("H1 predecision access log is caller-minted")
        if type(self.events) is not tuple:
            _fail("H1 access log events must be one exact tuple")
        predecessor = None
        for index, event in enumerate(self.events, 1):
            _require_live(_LIVE_EVENTS, event, H1PredecisionAccessEventV1, "access event")
            if (
                event.execution_profile_id != self.execution_profile_id
                or event.context_id != self.context_id
                or event.logical_occurrence_id != self.logical_occurrence_id
                or event.route_attempt_id != self.route_attempt_id
                or event.build_epoch_id != self.build_epoch_id
                or event.session_nonce != self.session_nonce
                or event.sequence != index
                or event.predecessor_event_id != predecessor
            ):
                _fail("H1 access log crossed context or predecessor identity")
            predecessor = event.event_id
        object.__setattr__(self, "_log_id", content_id(LOG_DOMAIN, self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h1_predecision_access_log.v1",
            "schema_version": SCHEMA_VERSION,
            "h1_current_access_execution_profile_id": self.execution_profile_id,
            "h1_current_access_predecision_context_id": self.context_id,
            "logical_occurrence_id": self.logical_occurrence_id,
            "route_attempt_id": self.route_attempt_id,
            "BuildEpoch_id": self.build_epoch_id,
            "session_nonce": self.session_nonce,
            "event_count": len(self.events),
            "event_ids": [event.event_id for event in self.events],
            "last_event_id": None if not self.events else self.events[-1].event_id,
            "append_only_prefix_committed": True,
        }

    @property
    def log_id(self) -> str:
        _require_live(_LIVE_LOGS, self, H1PredecisionAccessLogV1, "access log")
        return self._log_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "h1_predecision_access_log_id": self._log_id}


class H1PredecisionAccessLogRecorderV1:
    """Process-local append authority for one exact predecision context."""

    __slots__ = ("_context", "_events", "_lock", "_profile")

    def __init__(
        self,
        *,
        execution_profile: H1CurrentAccessExecutionProfileV1,
        context: H1CurrentAccessPredecisionContextV1,
    ) -> None:
        _require_live(_LIVE_PROFILES, execution_profile, H1CurrentAccessExecutionProfileV1, "execution profile")
        _require_live(_LIVE_CONTEXTS, context, H1CurrentAccessPredecisionContextV1, "predecision context")
        if context.execution_profile_id != execution_profile.profile_id:
            _fail("H1 access recorder crossed execution profiles")
        self._profile = execution_profile
        self._context = context
        self._events: list[H1PredecisionAccessEventV1] = []
        self._lock = threading.RLock()

    @property
    def context(self) -> H1CurrentAccessPredecisionContextV1:
        return self._context

    @property
    def execution_profile(self) -> H1CurrentAccessExecutionProfileV1:
        return self._profile

    def append(self, operation: H1PredecisionAccessOperationV1 | str, *, resource_id: str) -> H1PredecisionAccessEventV1:
        try:
            normalized = H1PredecisionAccessOperationV1(operation).value
        except (TypeError, ValueError) as error:
            raise ConstructionK7H1CurrentAccessAuthorityV1Error(
                "H1 predecision recorder rejected a forbidden/unknown operation"
            ) from error
        with self._lock:
            sequence = len(self._events) + 1
            if sequence > len(REGISTERED_OPERATION_SEQUENCE):
                _fail("H1 predecision access log exceeded its registered phase events")
            if sequence <= len(EXPECTED_OPERATION_SEQUENCE) and (
                normalized != EXPECTED_OPERATION_SEQUENCE[sequence - 1]
            ):
                _fail("H1 predecision access sequence differs from the exact profile")
            if sequence > len(EXPECTED_OPERATION_SEQUENCE) and (
                normalized
                != REGISTERED_POSTCUTOFF_OPERATION_SEQUENCE[
                    sequence - len(EXPECTED_OPERATION_SEQUENCE) - 1
                ]
            ):
                _fail("H1 post-cutoff access sequence differs from its registered phases")
            predecessor = None if not self._events else self._events[-1].event_id
            context = self._context
            event = H1PredecisionAccessEventV1(
                _EVENT_ISSUER,
                self._profile.profile_id,
                context.context_id,
                context.logical_occurrence_id,
                context.route_attempt_id,
                context.build_epoch_id,
                context.session_nonce,
                sequence,
                normalized,
                _cid(resource_id, "access resource"),
                predecessor,
            )
            _retain(_LIVE_EVENTS, event, canonical_json_bytes(event.to_document()))
            self._events.append(event)
            return event

    def snapshot(self) -> H1PredecisionAccessLogV1:
        with self._lock:
            context = self._context
            value = H1PredecisionAccessLogV1(
                _LOG_ISSUER,
                self._profile.profile_id,
                context.context_id,
                context.logical_occurrence_id,
                context.route_attempt_id,
                context.build_epoch_id,
                context.session_nonce,
                tuple(self._events),
            )
            _retain(_LIVE_LOGS, value, canonical_json_bytes(value.to_document()))
            return value


def record_h1_predecision_identity_inputs_v1(
    recorder: H1PredecisionAccessLogRecorderV1,
) -> tuple[H1PredecisionAccessEventV1, H1PredecisionAccessEventV1]:
    if type(recorder) is not H1PredecisionAccessLogRecorderV1:
        _fail("H1 identity input recorder has a foreign type")
    context = recorder.context
    first = recorder.append(
        H1PredecisionAccessOperationV1.CURRENT_SOURCE_FIXTURE_REPLAYED,
        resource_id=context.current_source_fixture_id,
    )
    second = recorder.append(
        H1PredecisionAccessOperationV1.PROOF_MATCH_ATTESTATION_REPLAYED,
        resource_id=context.proof_match_attestation_id,
    )
    return first, second


@dataclass(frozen=True, slots=True)
class H1PredecisionCurrentAccessCutoffV1:
    _issuer: InitVar[object]
    execution_profile_id: str
    context_id: str
    logical_occurrence_id: str
    route_attempt_id: str
    build_epoch_id: str
    session_nonce: str
    access_log_id: str
    event_count: int
    last_event_id: str
    _cutoff_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _CUTOFF_ISSUER:
            _fail("H1 current-access cutoff is caller-minted")
        for value, label in (
            (self.execution_profile_id, "execution profile"),
            (self.context_id, "predecision context"),
            (self.logical_occurrence_id, "logical occurrence"),
            (self.route_attempt_id, "route attempt"),
            (self.build_epoch_id, "BuildEpoch"),
            (self.session_nonce, "session nonce"),
            (self.access_log_id, "access log"),
            (self.last_event_id, "last access event"),
        ):
            _cid(value, label)
        if self.event_count != len(EXPECTED_OPERATION_SEQUENCE):
            _fail("H1 current-access cutoff does not close the exact access sequence")
        object.__setattr__(self, "_cutoff_id", content_id(CUTOFF_DOMAIN, self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h1_predecision_current_access_cutoff.v1",
            "schema_version": SCHEMA_VERSION,
            "h1_current_access_execution_profile_id": self.execution_profile_id,
            "h1_current_access_predecision_context_id": self.context_id,
            "logical_occurrence_id": self.logical_occurrence_id,
            "route_attempt_id": self.route_attempt_id,
            "BuildEpoch_id": self.build_epoch_id,
            "session_nonce": self.session_nonce,
            "h1_predecision_access_log_id": self.access_log_id,
            "event_count": self.event_count,
            "last_event_id": self.last_event_id,
            "cutoff_semantics": "CURRENT_APPEND_ONLY_LOG_HEAD",
        }

    @property
    def cutoff_id(self) -> str:
        _require_live(_LIVE_CUTOFFS, self, H1PredecisionCurrentAccessCutoffV1, "current-access cutoff")
        return self._cutoff_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "h1_predecision_current_access_cutoff_id": self._cutoff_id}


def freeze_h1_predecision_current_access_cutoff_v1(
    recorder: H1PredecisionAccessLogRecorderV1,
) -> H1PredecisionCurrentAccessCutoffV1:
    if type(recorder) is not H1PredecisionAccessLogRecorderV1:
        _fail("H1 current-access cutoff recorder has a foreign type")
    log = recorder.snapshot()
    if len(log.events) != len(EXPECTED_OPERATION_SEQUENCE):
        _fail("H1 current-access cutoff requires the complete exact access sequence")
    context = recorder.context
    value = H1PredecisionCurrentAccessCutoffV1(
        _CUTOFF_ISSUER,
        recorder.execution_profile.profile_id,
        context.context_id,
        context.logical_occurrence_id,
        context.route_attempt_id,
        context.build_epoch_id,
        context.session_nonce,
        log.log_id,
        len(log.events),
        log.events[-1].event_id,
    )
    _retain(_LIVE_CUTOFFS, value, canonical_json_bytes(value.to_document()))
    return value


def require_h1_predecision_current_access_cutoff_v1(
    *,
    recorder: H1PredecisionAccessLogRecorderV1,
    cutoff: H1PredecisionCurrentAccessCutoffV1,
) -> H1PredecisionAccessLogV1:
    _require_live(_LIVE_CUTOFFS, cutoff, H1PredecisionCurrentAccessCutoffV1, "current-access cutoff")
    if type(recorder) is not H1PredecisionAccessLogRecorderV1:
        _fail("H1 current-access cutoff recorder has a foreign type")
    current = recorder.snapshot()
    context = recorder.context
    if (
        cutoff.execution_profile_id != recorder.execution_profile.profile_id
        or cutoff.context_id != context.context_id
        or cutoff.logical_occurrence_id != context.logical_occurrence_id
        or cutoff.route_attempt_id != context.route_attempt_id
        or cutoff.build_epoch_id != context.build_epoch_id
        or cutoff.session_nonce != context.session_nonce
        or cutoff.access_log_id != current.log_id
        or cutoff.event_count != len(current.events)
        or cutoff.last_event_id != current.events[-1].event_id
    ):
        _fail("H1 current-access cutoff is stale or crossed context identity")
    return current


@dataclass(frozen=True, slots=True)
class H1CurrentAccessChildResultV1:
    _issuer: InitVar[object]
    execution_profile_id: str
    context_id: str
    input_set_id: str
    logical_occurrence_id: str
    route_attempt_id: str
    build_epoch_id: str
    session_nonce: str
    runtime_facts_id: str
    runtime_verification_id: str
    source_manifest_id: str
    runtime_manifest_id: str
    verification_status: str
    construction_fixture: bool
    _result_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        expected_issuer = _CHILD_FIXTURE_ISSUER if self.construction_fixture else _CHILD_RUNTIME_ISSUER
        if _issuer is not expected_issuer:
            _fail("H1 current-access child result crossed its issuer lane")
        for value, label in (
            (self.execution_profile_id, "execution profile"),
            (self.context_id, "predecision context"),
            (self.input_set_id, "predecision input set"),
            (self.logical_occurrence_id, "logical occurrence"),
            (self.route_attempt_id, "route attempt"),
            (self.build_epoch_id, "BuildEpoch"),
            (self.session_nonce, "session nonce"),
            (self.runtime_facts_id, "runtime facts"),
            (self.runtime_verification_id, "runtime verification"),
            (self.source_manifest_id, "source manifest"),
            (self.runtime_manifest_id, "runtime manifest"),
        ):
            _cid(value, label)
        if self.construction_fixture:
            if self.verification_status != H1CurrentAccessEvidenceStatusV1.CONSTRUCTION_FIXTURE_ONLY.value:
                _fail("construction child result claimed observed runtime authority")
        elif self.verification_status != REQUIRED_RUNTIME_VERIFICATION_STATUS:
            _fail("runtime child result lacks exhaustive observed verification")
        object.__setattr__(self, "_result_id", content_id(CHILD_RESULT_DOMAIN, self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h1_current_access_child_result.v1",
            "schema_version": SCHEMA_VERSION,
            "h1_current_access_execution_profile_id": self.execution_profile_id,
            "h1_current_access_predecision_context_id": self.context_id,
            "h1_current_access_predecision_input_set_id": self.input_set_id,
            "logical_occurrence_id": self.logical_occurrence_id,
            "route_attempt_id": self.route_attempt_id,
            "BuildEpoch_id": self.build_epoch_id,
            "session_nonce": self.session_nonce,
            "h1_current_access_observed_runtime_facts_id": self.runtime_facts_id,
            "h1_current_access_observed_runtime_facts_verification_id": self.runtime_verification_id,
            "h1_current_access_fresh_exec_source_manifest_id": self.source_manifest_id,
            "h1_current_access_fresh_exec_runtime_manifest_id": self.runtime_manifest_id,
            "verification_status": self.verification_status,
            "construction_fixture": self.construction_fixture,
            "production_evidence_eligible": not self.construction_fixture,
        }

    @property
    def child_result_id(self) -> str:
        _require_live(_LIVE_CHILD_RESULTS, self, H1CurrentAccessChildResultV1, "child result")
        return self._result_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "h1_current_access_child_result_id": self._result_id}


def _runtime_verification_document(value: Any) -> dict[str, Any]:
    """Require the complementary fresh-exec verifier without a circular import."""

    try:
        from acfqp import construction_k7_h1_current_access_fresh_exec_runtime_v1 as runtime_v1
    except ImportError as error:
        raise H1CurrentAccessAuthorityBlockedV1(
            "fresh-exec current-access runtime verifier is unavailable"
        ) from error
    expected_type = getattr(runtime_v1, "H1CurrentAccessObservedRuntimeFactsVerificationV1", None)
    require = getattr(runtime_v1, "require_h1_current_access_observed_runtime_facts_verification_v1", None)
    if expected_type is None or type(value) is not expected_type or not callable(require):
        raise H1CurrentAccessAuthorityBlockedV1(
            "current-access evidence is not the exact retained runtime-verifier type"
        )
    try:
        verified = require(value)
    except Exception as error:
        raise H1CurrentAccessAuthorityBlockedV1(
            "current-access runtime verification is not retained"
        ) from error
    if verified is not value:
        raise H1CurrentAccessAuthorityBlockedV1(
            "runtime verifier did not retain the supplied evidence object"
        )
    document = value.to_document()
    if type(document) is not dict:
        raise H1CurrentAccessAuthorityBlockedV1(
            "runtime verification document is malformed"
        )
    return document


def _require_live_child_result(
    value: Any,
) -> tuple[Any, ...]:
    retained = _require_live(
        _LIVE_CHILD_RESULTS,
        value,
        H1CurrentAccessChildResultV1,
        "child result",
    )
    if value.construction_fixture:
        if retained[2] != H1CurrentAccessEvidenceStatusV1.CONSTRUCTION_FIXTURE_ONLY.value:
            _fail("construction child-result retained status changed")
        return retained
    if retained[2] != REQUIRED_RUNTIME_VERIFICATION_STATUS or retained[3] is None:
        _fail("observed child result lost its runtime-verifier handle")
    document = _runtime_verification_document(retained[3])
    expected = {
        "h1_current_access_execution_profile_id": value.execution_profile_id,
        "h1_current_access_predecision_context_id": value.context_id,
        "h1_current_access_predecision_input_set_id": value.input_set_id,
        "h1_current_access_observed_runtime_facts_id": value.runtime_facts_id,
        "h1_current_access_observed_runtime_facts_verification_id": (
            value.runtime_verification_id
        ),
        "h1_current_access_fresh_exec_source_manifest_id": value.source_manifest_id,
        "h1_current_access_fresh_exec_runtime_manifest_id": value.runtime_manifest_id,
        "logical_occurrence_id": value.logical_occurrence_id,
        "route_attempt_id": value.route_attempt_id,
        "BuildEpoch_id": value.build_epoch_id,
        "session_nonce": value.session_nonce,
        "verification_status": REQUIRED_RUNTIME_VERIFICATION_STATUS,
    }
    if any(document.get(key) != expected_value for key, expected_value in expected.items()):
        _fail("observed child result runtime-verifier binding changed")
    return retained


def issue_h1_current_access_child_result_v1(
    *,
    execution_profile: H1CurrentAccessExecutionProfileV1,
    context: H1CurrentAccessPredecisionContextV1,
    input_set: H1CurrentAccessPredecisionInputSetV1,
    runtime_verification: Any,
) -> H1CurrentAccessChildResultV1:
    _require_live(_LIVE_PROFILES, execution_profile, H1CurrentAccessExecutionProfileV1, "execution profile")
    _require_live(_LIVE_CONTEXTS, context, H1CurrentAccessPredecisionContextV1, "predecision context")
    require_h1_current_access_predecision_input_set_v1(input_set)
    if (
        input_set.context_id != context.context_id
        or input_set.execution_profile_id != execution_profile.profile_id
    ):
        _fail("H1 runtime child input set crossed context/profile")
    document = _runtime_verification_document(runtime_verification)
    expected = {
        "h1_current_access_execution_profile_id": execution_profile.profile_id,
        "h1_current_access_predecision_context_id": context.context_id,
        "h1_current_access_predecision_input_set_id": input_set.input_set_id,
        "h1_current_access_fresh_exec_runtime_profile_id": (
            execution_profile.fresh_exec_runtime_profile_id
        ),
        "h1_current_access_fresh_exec_source_manifest_id": (
            execution_profile.fresh_exec_source_manifest_id
        ),
        "h1_current_access_fresh_exec_runtime_manifest_id": (
            execution_profile.fresh_exec_runtime_manifest_id
        ),
        "h1_current_source_fixture_id": context.current_source_fixture_id,
        "h1_durable_proof_match_attestation_id": context.proof_match_attestation_id,
        "exact_infeasibility_identity_id": context.exact_infeasibility_identity_id,
        **context.identity_document,
        "logical_occurrence_id": context.logical_occurrence_id,
        "route_attempt_id": context.route_attempt_id,
        "BuildEpoch_id": context.build_epoch_id,
        "session_nonce": context.session_nonce,
        "verification_status": REQUIRED_RUNTIME_VERIFICATION_STATUS,
    }
    for key, expected_value in expected.items():
        if document.get(key) != expected_value:
            raise H1CurrentAccessAuthorityBlockedV1(
                f"runtime verification crossed {key}"
            )
    fields = (
        "h1_current_access_observed_runtime_facts_id",
        "h1_current_access_observed_runtime_facts_verification_id",
        "h1_current_access_fresh_exec_source_manifest_id",
        "h1_current_access_fresh_exec_runtime_manifest_id",
    )
    for key in fields:
        _cid(document.get(key), key)
    value = H1CurrentAccessChildResultV1(
        _CHILD_RUNTIME_ISSUER,
        execution_profile.profile_id,
        context.context_id,
        input_set.input_set_id,
        context.logical_occurrence_id,
        context.route_attempt_id,
        context.build_epoch_id,
        context.session_nonce,
        document[fields[0]],
        document[fields[1]],
        document[fields[2]],
        document[fields[3]],
        REQUIRED_RUNTIME_VERIFICATION_STATUS,
        False,
    )
    _retain(
        _LIVE_CHILD_RESULTS,
        value,
        canonical_json_bytes(value.to_document()),
        REQUIRED_RUNTIME_VERIFICATION_STATUS,
        runtime_verification,
    )
    return value


def build_h1_current_access_child_result_fixture_v1(
    *,
    execution_profile: H1CurrentAccessExecutionProfileV1,
    context: H1CurrentAccessPredecisionContextV1,
    input_set: H1CurrentAccessPredecisionInputSetV1,
) -> H1CurrentAccessChildResultV1:
    """Build a separately typed/statused schema fixture, never runtime proof."""

    _require_live(_LIVE_PROFILES, execution_profile, H1CurrentAccessExecutionProfileV1, "execution profile")
    _require_live(_LIVE_CONTEXTS, context, H1CurrentAccessPredecisionContextV1, "predecision context")
    require_h1_current_access_predecision_input_set_v1(input_set)
    if (
        input_set.context_id != context.context_id
        or input_set.execution_profile_id != execution_profile.profile_id
    ):
        _fail("H1 fixture child input set crossed context/profile")
    fixture_ids = tuple(
        content_id(
            FIXTURE_DOMAIN,
            {
                "schema": "acfqp.h1_current_access_construction_fixture_member.v1",
                "role": role,
                "h1_current_access_predecision_context_id": context.context_id,
            },
        )
        for role in ("RUNTIME_FACTS", "RUNTIME_VERIFICATION", "SOURCE_MANIFEST", "RUNTIME_MANIFEST")
    )
    value = H1CurrentAccessChildResultV1(
        _CHILD_FIXTURE_ISSUER,
        execution_profile.profile_id,
        context.context_id,
        input_set.input_set_id,
        context.logical_occurrence_id,
        context.route_attempt_id,
        context.build_epoch_id,
        context.session_nonce,
        *fixture_ids,
        H1CurrentAccessEvidenceStatusV1.CONSTRUCTION_FIXTURE_ONLY.value,
        True,
    )
    _retain(
        _LIVE_CHILD_RESULTS,
        value,
        canonical_json_bytes(value.to_document()),
        H1CurrentAccessEvidenceStatusV1.CONSTRUCTION_FIXTURE_ONLY.value,
        None,
    )
    return value


def record_h1_current_access_child_result_v1(
    *,
    recorder: H1PredecisionAccessLogRecorderV1,
    child_result: H1CurrentAccessChildResultV1,
) -> tuple[H1PredecisionAccessEventV1, H1PredecisionAccessEventV1]:
    retained = _require_live_child_result(child_result)
    context = recorder.context
    if (
        child_result.execution_profile_id != recorder.execution_profile.profile_id
        or child_result.context_id != context.context_id
        or child_result.logical_occurrence_id != context.logical_occurrence_id
        or child_result.route_attempt_id != context.route_attempt_id
        or child_result.build_epoch_id != context.build_epoch_id
        or child_result.session_nonce != context.session_nonce
    ):
        _fail("H1 child result crossed recorder context/attempt/epoch/nonce")
    third = recorder.append(
        H1PredecisionAccessOperationV1.FRESH_EXEC_RUNTIME_VERIFICATION_ACCEPTED,
        resource_id=child_result.runtime_verification_id,
    )
    fourth = recorder.append(
        H1PredecisionAccessOperationV1.EXHAUSTIVE_CAPABILITY_CLOSURE_VERIFIED,
        resource_id=child_result.runtime_facts_id,
    )
    if retained[2] != child_result.verification_status:
        _fail("H1 child-result retained status changed")
    return third, fourth


@dataclass(frozen=True, slots=True)
class H1CurrentAccessObservedEvidenceV1:
    _issuer: InitVar[object]
    execution_profile_id: str
    context_id: str
    input_set_id: str
    logical_occurrence_id: str
    route_attempt_id: str
    build_epoch_id: str
    session_nonce: str
    child_result_id: str
    runtime_facts_id: str
    runtime_verification_id: str
    access_log_id: str
    cutoff_id: str
    verification_status: str
    construction_fixture: bool
    _evidence_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        expected = _EVIDENCE_FIXTURE_ISSUER if self.construction_fixture else _EVIDENCE_RUNTIME_ISSUER
        if _issuer is not expected:
            _fail("H1 observed evidence crossed its issuer lane")
        for value, label in (
            (self.execution_profile_id, "execution profile"),
            (self.context_id, "predecision context"),
            (self.input_set_id, "predecision input set"),
            (self.logical_occurrence_id, "logical occurrence"),
            (self.route_attempt_id, "route attempt"),
            (self.build_epoch_id, "BuildEpoch"),
            (self.session_nonce, "session nonce"),
            (self.child_result_id, "child result"),
            (self.runtime_facts_id, "runtime facts"),
            (self.runtime_verification_id, "runtime verification"),
            (self.access_log_id, "access log"),
            (self.cutoff_id, "access cutoff"),
        ):
            _cid(value, label)
        expected_status = (
            H1CurrentAccessEvidenceStatusV1.CONSTRUCTION_FIXTURE_ONLY.value
            if self.construction_fixture
            else REQUIRED_RUNTIME_VERIFICATION_STATUS
        )
        if self.verification_status != expected_status:
            _fail("H1 observed-evidence status differs from its issuer lane")
        object.__setattr__(self, "_evidence_id", content_id(EVIDENCE_DOMAIN, self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h1_current_access_observed_evidence.v1",
            "schema_version": SCHEMA_VERSION,
            "h1_current_access_execution_profile_id": self.execution_profile_id,
            "h1_current_access_predecision_context_id": self.context_id,
            "h1_current_access_predecision_input_set_id": self.input_set_id,
            "logical_occurrence_id": self.logical_occurrence_id,
            "route_attempt_id": self.route_attempt_id,
            "BuildEpoch_id": self.build_epoch_id,
            "session_nonce": self.session_nonce,
            "h1_current_access_child_result_id": self.child_result_id,
            "h1_current_access_observed_runtime_facts_id": self.runtime_facts_id,
            "h1_current_access_observed_runtime_facts_verification_id": self.runtime_verification_id,
            "h1_predecision_access_log_id": self.access_log_id,
            "h1_predecision_current_access_cutoff_id": self.cutoff_id,
            "verification_status": self.verification_status,
            "construction_fixture": self.construction_fixture,
            "production_authority_eligible": not self.construction_fixture,
            "downstream_route_authority_join_present": False,
        }

    @property
    def evidence_id(self) -> str:
        _require_live(_LIVE_EVIDENCE, self, H1CurrentAccessObservedEvidenceV1, "observed evidence")
        return self._evidence_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "h1_current_access_observed_evidence_id": self._evidence_id}


def freeze_h1_current_access_observed_evidence_v1(
    *,
    recorder: H1PredecisionAccessLogRecorderV1,
    cutoff: H1PredecisionCurrentAccessCutoffV1,
    child_result: H1CurrentAccessChildResultV1,
    input_set: H1CurrentAccessPredecisionInputSetV1,
) -> H1CurrentAccessObservedEvidenceV1:
    log = require_h1_predecision_current_access_cutoff_v1(recorder=recorder, cutoff=cutoff)
    child_retained = _require_live_child_result(child_result)
    require_h1_current_access_predecision_input_set_v1(input_set)
    context = recorder.context
    if tuple(event.operation for event in log.events) != EXPECTED_OPERATION_SEQUENCE:
        _fail("H1 observed evidence contains missing, reordered, or extra events")
    if (
        child_result.execution_profile_id != recorder.execution_profile.profile_id
        or child_result.context_id != context.context_id
        or child_result.input_set_id != input_set.input_set_id
        or input_set.context_id != context.context_id
        or input_set.execution_profile_id != recorder.execution_profile.profile_id
        or child_result.logical_occurrence_id != context.logical_occurrence_id
        or child_result.route_attempt_id != context.route_attempt_id
        or child_result.build_epoch_id != context.build_epoch_id
        or child_result.session_nonce != context.session_nonce
        or log.events[2].resource_id != child_result.runtime_verification_id
        or log.events[3].resource_id != child_result.runtime_facts_id
    ):
        _fail("H1 observed evidence crossed child/log context identity")
    construction_fixture = child_result.construction_fixture
    issuer = _EVIDENCE_FIXTURE_ISSUER if construction_fixture else _EVIDENCE_RUNTIME_ISSUER
    value = H1CurrentAccessObservedEvidenceV1(
        issuer,
        recorder.execution_profile.profile_id,
        context.context_id,
        input_set.input_set_id,
        context.logical_occurrence_id,
        context.route_attempt_id,
        context.build_epoch_id,
        context.session_nonce,
        child_result.child_result_id,
        child_result.runtime_facts_id,
        child_result.runtime_verification_id,
        log.log_id,
        cutoff.cutoff_id,
        child_result.verification_status,
        construction_fixture,
    )
    _retain(
        _LIVE_EVIDENCE,
        value,
        canonical_json_bytes(value.to_document()),
        child_retained[2],
        recorder,
        cutoff,
        child_result,
    )
    return value


_AUTHORITY_FORBIDDEN_FIELD_FRAGMENTS = (
    "common_prefix",
    "decision_point",
    "formal_v7_route_decision",
    "formal_v7_route_upper",
    "route_decision",
    "route_freeze",
    "selected_plan",
    "selected_route",
)


@dataclass(frozen=True, slots=True)
class H1ProductionCurrentAccessAuthorityV1:
    _issuer: InitVar[object]
    execution_profile_id: str
    context_id: str
    input_set_id: str
    current_source_fixture_id: str
    proof_match_attestation_id: str
    exact_infeasibility_identity_id: str
    structural_id: str
    query_id: str
    build_epoch_id: str
    kernel_id: str
    threshold_profile_id: str
    reward_profile_id: str
    policy_class_id: str
    complete_search_profile_id: str
    logical_occurrence_id: str
    route_attempt_id: str
    session_nonce: str
    observed_evidence_id: str
    child_result_id: str
    runtime_facts_id: str
    runtime_verification_id: str
    access_log_id: str
    cutoff_id: str
    _authority_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _AUTHORITY_ISSUER:
            _fail("H1 production current-access authority is caller-minted")
        for value in self._payload().values():
            if type(value) is str and len(value) == 64:
                _cid(value, "authority identity")
        object.__setattr__(self, "_authority_id", content_id(AUTHORITY_DOMAIN, self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h1_production_current_access_authority.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "h1_current_access_execution_profile_id": self.execution_profile_id,
            "h1_current_access_predecision_context_id": self.context_id,
            "h1_current_access_predecision_input_set_id": self.input_set_id,
            "h1_current_source_fixture_id": self.current_source_fixture_id,
            "h1_durable_proof_match_attestation_id": self.proof_match_attestation_id,
            "exact_infeasibility_identity_id": self.exact_infeasibility_identity_id,
            "structural_id": self.structural_id,
            "query_id": self.query_id,
            "BuildEpoch_id": self.build_epoch_id,
            "kernel_id": self.kernel_id,
            "threshold_profile_id": self.threshold_profile_id,
            "reward_profile_id": self.reward_profile_id,
            "policy_class_id": self.policy_class_id,
            "complete_search_profile_id": self.complete_search_profile_id,
            "logical_occurrence_id": self.logical_occurrence_id,
            "route_attempt_id": self.route_attempt_id,
            "session_nonce": self.session_nonce,
            "h1_current_access_observed_evidence_id": self.observed_evidence_id,
            "h1_current_access_child_result_id": self.child_result_id,
            "h1_current_access_observed_runtime_facts_id": self.runtime_facts_id,
            "h1_current_access_observed_runtime_facts_verification_id": self.runtime_verification_id,
            "h1_predecision_access_log_id": self.access_log_id,
            "h1_predecision_current_access_cutoff_id": self.cutoff_id,
            "verification_status": REQUIRED_RUNTIME_VERIFICATION_STATUS,
            "downstream_route_authority_join_present": False,
            "one_shot_consumption_required": True,
            "production_current_access_authority": True,
            "official_execution_allowed": False,
        }

    @property
    def authority_id(self) -> str:
        _require_live_authority(self, allow_consumed=False)
        return self._authority_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "h1_production_current_access_authority_id": self._authority_id}


def _require_live_authority(
    value: Any,
    *,
    allow_consumed: bool,
) -> list[Any]:
    if type(value) is not H1ProductionCurrentAccessAuthorityV1:
        _fail("H1 production current-access authority has a foreign type")
    with _RETENTION_LOCK:
        retained = _LIVE_AUTHORITIES.get(id(value))
        if retained is None or retained[0] is not value:
            _fail("H1 production current-access authority is not retained")
        if retained[2] and not allow_consumed:
            _fail("H1 production current-access authority was already consumed")
        evidence = retained[3]
        evidence_retained = _require_live(
            _LIVE_EVIDENCE,
            evidence,
            H1CurrentAccessObservedEvidenceV1,
            "observed evidence",
        )
        if (
            evidence.evidence_id != value.observed_evidence_id
            or evidence_retained[2] != REQUIRED_RUNTIME_VERIFICATION_STATUS
        ):
            _fail("H1 current-access authority lost its observed evidence")
        child_retained = _require_live_child_result(evidence_retained[5])
        if (
            evidence_retained[5].child_result_id != value.child_result_id
            or child_retained[2] != REQUIRED_RUNTIME_VERIFICATION_STATUS
        ):
            _fail("H1 current-access authority lost its observed child result")
        require_h1_predecision_current_access_cutoff_v1(
            recorder=evidence_retained[3],
            cutoff=evidence_retained[4],
        )
        current = canonical_json_bytes(value.to_document())
        if not hmac.compare_digest(current, retained[1]):
            _fail("H1 production current-access authority changed")
        return retained


def issue_h1_production_current_access_authority_v1(
    *,
    execution_profile: H1CurrentAccessExecutionProfileV1,
    context: H1CurrentAccessPredecisionContextV1,
    observed_evidence: H1CurrentAccessObservedEvidenceV1,
) -> H1ProductionCurrentAccessAuthorityV1:
    if (
        not FRESH_EXEC_RUNTIME_EVIDENCE_INTEGRATED
        or not PRODUCTION_CURRENT_ACCESS_AUTHORITY_PRESENT
    ):
        raise H1CurrentAccessAuthorityBlockedV1(
            "production current-access issuance remains locked pending runtime review"
        )
    _require_live(_LIVE_PROFILES, execution_profile, H1CurrentAccessExecutionProfileV1, "execution profile")
    _require_live(_LIVE_CONTEXTS, context, H1CurrentAccessPredecisionContextV1, "predecision context")
    retained = _require_live(_LIVE_EVIDENCE, observed_evidence, H1CurrentAccessObservedEvidenceV1, "observed evidence")
    child_retained = _require_live_child_result(retained[5])
    if (
        observed_evidence.construction_fixture
        or retained[2] != REQUIRED_RUNTIME_VERIFICATION_STATUS
        or child_retained[2] != REQUIRED_RUNTIME_VERIFICATION_STATUS
        or observed_evidence.verification_status != REQUIRED_RUNTIME_VERIFICATION_STATUS
    ):
        raise H1CurrentAccessAuthorityBlockedV1(
            "construction or fake evidence cannot mint production current access"
        )
    if (
        observed_evidence.execution_profile_id != execution_profile.profile_id
        or observed_evidence.context_id != context.context_id
        or observed_evidence.logical_occurrence_id != context.logical_occurrence_id
        or observed_evidence.route_attempt_id != context.route_attempt_id
        or observed_evidence.build_epoch_id != context.build_epoch_id
        or observed_evidence.session_nonce != context.session_nonce
    ):
        _fail("H1 current-access evidence crossed context/attempt/epoch/nonce")
    require_h1_predecision_current_access_cutoff_v1(
        recorder=retained[3],
        cutoff=retained[4],
    )
    value = H1ProductionCurrentAccessAuthorityV1(
        _AUTHORITY_ISSUER,
        execution_profile.profile_id,
        context.context_id,
        observed_evidence.input_set_id,
        context.current_source_fixture_id,
        context.proof_match_attestation_id,
        context.exact_infeasibility_identity_id,
        context.structural_id,
        context.query_id,
        context.build_epoch_id,
        context.kernel_id,
        context.threshold_profile_id,
        context.reward_profile_id,
        context.policy_class_id,
        context.complete_search_profile_id,
        context.logical_occurrence_id,
        context.route_attempt_id,
        context.session_nonce,
        observed_evidence.evidence_id,
        observed_evidence.child_result_id,
        observed_evidence.runtime_facts_id,
        observed_evidence.runtime_verification_id,
        observed_evidence.access_log_id,
        observed_evidence.cutoff_id,
    )
    document = value.to_document()
    flattened_keys = "\n".join(document)
    if any(fragment in flattened_keys for fragment in _AUTHORITY_FORBIDDEN_FIELD_FRAGMENTS):
        _fail("H1 current-access authority leaked a downstream route field")
    raw = canonical_json_bytes(document)
    with _RETENTION_LOCK:
        if id(observed_evidence) in _AUTHORITY_ISSUED_EVIDENCE_IDS:
            _fail("H1 observed current-access evidence already issued an authority")
        _AUTHORITY_ISSUED_EVIDENCE_IDS.add(id(observed_evidence))
        _LIVE_AUTHORITIES[id(value)] = [value, raw, False, observed_evidence]
    return value


def require_h1_production_current_access_authority_v1(
    value: Any,
) -> H1ProductionCurrentAccessAuthorityV1:
    _require_live_authority(value, allow_consumed=False)
    return value


def consume_h1_production_current_access_authority_v1(value: Any) -> bytes:
    """Consume the retained authority exactly once and return its frozen bytes."""

    with _RETENTION_LOCK:
        retained = _require_live_authority(value, allow_consumed=False)
        retained[2] = True
        return bytes(retained[1])


@dataclass(frozen=True, slots=True)
class H1ProductionCurrentAccessAuthorityBlockerV1:
    _issuer: InitVar[object]
    execution_profile_id: str
    context_id: str
    logical_occurrence_id: str
    route_attempt_id: str
    build_epoch_id: str
    session_nonce: str
    blocker_code: str
    _blocker_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _BLOCKER_ISSUER:
            _fail("H1 current-access blocker is caller-minted")
        if self.blocker_code != "FRESH_EXEC_RUNTIME_EVIDENCE_UNAVAILABLE":
            _fail("H1 current-access blocker code is not registered")
        object.__setattr__(self, "_blocker_id", content_id(BLOCKER_DOMAIN, self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h1_production_current_access_authority_blocker.v1",
            "schema_version": SCHEMA_VERSION,
            "h1_current_access_execution_profile_id": self.execution_profile_id,
            "h1_current_access_predecision_context_id": self.context_id,
            "logical_occurrence_id": self.logical_occurrence_id,
            "route_attempt_id": self.route_attempt_id,
            "BuildEpoch_id": self.build_epoch_id,
            "session_nonce": self.session_nonce,
            "blocker_code": self.blocker_code,
            "terminal_scope": "ROUTE_ATTEMPT",
            "terminal_class": "ATTEMPT_CLOSURE_NONCERTIFICATE",
            "terminal_code": "PROTOCOL_FAILURE",
            "production_current_access_authority": False,
            "official_execution_allowed": False,
        }

    @property
    def blocker_id(self) -> str:
        _require_live(_LIVE_BLOCKERS, self, H1ProductionCurrentAccessAuthorityBlockerV1, "current-access blocker")
        return self._blocker_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "h1_production_current_access_authority_blocker_id": self._blocker_id}


def build_h1_production_current_access_authority_blocker_v1(
    *,
    execution_profile: H1CurrentAccessExecutionProfileV1,
    context: H1CurrentAccessPredecisionContextV1,
) -> H1ProductionCurrentAccessAuthorityBlockerV1:
    _require_live(_LIVE_PROFILES, execution_profile, H1CurrentAccessExecutionProfileV1, "execution profile")
    _require_live(_LIVE_CONTEXTS, context, H1CurrentAccessPredecisionContextV1, "predecision context")
    value = H1ProductionCurrentAccessAuthorityBlockerV1(
        _BLOCKER_ISSUER,
        execution_profile.profile_id,
        context.context_id,
        context.logical_occurrence_id,
        context.route_attempt_id,
        context.build_epoch_id,
        context.session_nonce,
        "FRESH_EXEC_RUNTIME_EVIDENCE_UNAVAILABLE",
    )
    _retain(_LIVE_BLOCKERS, value, canonical_json_bytes(value.to_document()))
    return value


def production_current_access_authority_field_fragments_v1() -> tuple[str, ...]:
    return _AUTHORITY_FORBIDDEN_FIELD_FRAGMENTS


__all__ = (
    "CONSTRUCTION_ONLY",
    "COUNTER_COMPLETENESS_GATE_STATUS",
    "ConstructionK7H1CurrentAccessAuthorityV1Error",
    "EXPECTED_OPERATION_SEQUENCE",
    "FORBIDDEN_PREDECISION_OPERATIONS",
    "FRESH_EXEC_RUNTIME_EVIDENCE_INTEGRATED",
    "FUTURE_FORMAL_V7_JOIN_PRESENT",
    "H1CurrentAccessAuthorityBlockedV1",
    "H1CurrentAccessChildResultV1",
    "H1CurrentAccessEvidenceStatusV1",
    "H1CurrentAccessExecutionProfileV1",
    "H1CurrentAccessObservedEvidenceV1",
    "H1CurrentAccessPredecisionContextV1",
    "H1CurrentAccessPredecisionInputSetV1",
    "H1PredecisionAccessEventV1",
    "H1PredecisionAccessLogRecorderV1",
    "H1PredecisionAccessLogV1",
    "H1PredecisionAccessOperationV1",
    "H1PredecisionCurrentAccessCutoffV1",
    "H1PredecisionSealedInputRowV1",
    "H1ProductionCurrentAccessAuthorityBlockerV1",
    "H1ProductionCurrentAccessAuthorityV1",
    "OFFICIAL_EXECUTION_ALLOWED",
    "OFFICIAL_N_BREAK_EVEN",
    "OFFICIAL_SCALAR_COST",
    "PRODUCTION_CURRENT_ACCESS_AUTHORITY_PRESENT",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "REQUESTED_PHASE3E_DOMAIN_TAGS",
    "REGISTERED_OPERATION_SEQUENCE",
    "REGISTERED_POSTCUTOFF_OPERATION_SEQUENCE",
    "REQUIRED_RUNTIME_VERIFICATION_STATUS",
    "SAMPLE_EFFICIENCY_GATE_STATUS",
    "SCHEMA_VERSION",
    "SEALED_INPUT_ROLES",
    "WORKLOAD_ECONOMICS_GATE_STATUS",
    "build_h1_current_access_child_result_fixture_v1",
    "build_h1_production_current_access_authority_blocker_v1",
    "consume_h1_production_current_access_authority_v1",
    "freeze_h1_current_access_observed_evidence_v1",
    "freeze_h1_current_access_predecision_context_v1",
    "freeze_h1_current_access_predecision_input_set_v1",
    "freeze_h1_predecision_current_access_cutoff_v1",
    "issue_h1_current_access_child_result_v1",
    "issue_h1_production_current_access_authority_v1",
    "official_h1_current_access_execution_profile_v1",
    "production_current_access_authority_field_fragments_v1",
    "record_h1_current_access_child_result_v1",
    "record_h1_predecision_identity_inputs_v1",
    "require_h1_predecision_current_access_cutoff_v1",
    "require_h1_current_access_predecision_input_set_v1",
    "require_h1_production_current_access_authority_v1",
)
