"""V0-051 identity-bound incremental fixed-plan proof DAG.

V0-050 reused only a complete, byte-identical audit root.  This module keeps
the authoritative V0-043 arithmetic and V0-049 held-out V5 model, but factors
one audit into threshold-neutral proof obligations.  An affected node and all
of its affected descendants are recomputed when the registered initial
support, regret tolerance, or risk tolerance changes.

The production runner never calls the monolithic fixed-plan auditor.  It uses
the unchanged private arithmetic functions from :mod:`partial_sound_audit_v1`
and materializes the exact legacy V1 rows only at the role-bound ``R`` root.
The monolithic auditor is used solely by the evaluation-only matched control.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from fractions import Fraction
import hashlib
from itertools import product
from pathlib import Path
from typing import Any, Callable, Mapping

import acfqp.heldout_family_amortization_v1 as family_module
import acfqp.partial_sound_audit_v1 as audit_module
from acfqp._runtime_authority_v1 import (
    RuntimeAuthorityMintV1,
    bind_runtime_authority_v1,
    require_runtime_authority_v1,
    runtime_authority_fingerprint_v1,
)
from acfqp.cross_query_promotion_v1 import (
    HeldOutPlanAuditV1,
    HeldOutPlanProposalV1,
)
from acfqp.heldout_family_amortization_v1 import (
    FAMILY_TARGET_STATES,
    HeldOutFamilyAmortizationResultV1,
    HeldOutFamilyPromotionBuildV1,
    HeldOutFamilyProtocolV1,
    verify_lmb_heldout_family_amortization_v1,
)
from acfqp.observation_partial_rapm_v1 import (
    DeterministicObservationProfileV1,
    ObservationLogManifestV1,
    PreregisteredObservationAuthorityV1,
)
from acfqp.observed_typed_coordinate_synthesis_v1 import (
    ObservedTypedPartialRAPMResultV1,
)
from acfqp.partial_model_planner_v1 import (
    TypedPartialModelPlanProposalResultV2,
    _candidate_summary,
    _planner_context,
    _selected_summary,
    _stage_assignments,
)
from acfqp.partial_sound_audit_v1 import (
    ContingentPlanStageV1,
    FailedProofReason,
    FrozenContingentAbstractPlanV1,
    FrozenPartialAuditThresholdsV1,
    InitialStateMassV1,
    InitialSupportPointRegretRowV1,
    PartialAuditOutcome,
    PartialFailedProofFrontierV1,
    PartialFixedPlanCertificateV1,
    PartialFixedPlanRobustBoundsV1,
    PartialPolicyBoundRowV1,
    PartialSoundAuditResultV1,
    StateActionTimeObligationV1,
    TypedPartialSoundAuditResultV2,
    UnrestrictedGroundUpperRowV1,
    canonical_lmb_n6_return_bound_proof_v1,
)
from acfqp.multistep_query_refinement_v1 import MultiStepQueryRefinementResultV1
from acfqp.domains.matching_buffer import LMBKernel
from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id


SCHEMA_VERSION = "1.0.0"
CONTRACT_VERSION = "1.14.0"
PROFILE_KEY = "lmb_identity_bound_incremental_proof_dag_v0"
SUCCESS_STATUS = "CERTIFIED_IDENTITY_BOUND_INCREMENTAL_PROOF_DAG_CONTROL"

EXPECTED_PARTIAL_AUDIT_SOURCE_SHA256 = (
    "661aee3732afda05c860f5dadae2b3545ecbbed7cee86f27517d1ea5dfcb7934"
)
EXPECTED_FAMILY_PLANNER_SOURCE_SHA256 = (
    "30020f7fd0e060970063a35d1365a52a1a28549119b12217c397f8252f35e84d"
)

CONTEXT_SEQUENCE = (
    (1, Fraction(0), Fraction(0)),
    (2, Fraction(0), Fraction(0)),
    (2, Fraction(1, 20), Fraction(0)),
    (2, Fraction(1, 20), Fraction(1, 20)),
    (3, Fraction(1, 20), Fraction(1, 20)),
    (3, Fraction(0), Fraction(1, 20)),
    (3, Fraction(0), Fraction(1, 10)),
)

EXPECTED_GLOBAL_COMPUTES = {
    "U": 1,
    "P": 2,
    "C": 6,
    "D": 6,
    "E": 10,
    "F": 10,
    "G": 6,
    "R": 21,
}
EXPECTED_GLOBAL_REUSES = {
    "U": 20,
    "P": 19,
    "C": 15,
    "D": 15,
    "E": 11,
    "F": 11,
    "G": 15,
    "R": 0,
}

DOMAIN_TAGS = {
    "semantics": "acfqp:incremental-proof-dag-semantics:v1",
    "context": "acfqp:incremental-proof-context:v1",
    "protocol": "acfqp:incremental-proof-dag-protocol:v1",
    "binding": "acfqp:incremental-proof-threshold-binding:v1",
    "node_key": "acfqp:incremental-proof-node-key:v1",
    "node_result": "acfqp:incremental-proof-neutral-result:v1",
    "node_entry": "acfqp:incremental-proof-node-entry:v1",
    "resolution": "acfqp:incremental-proof-node-resolution:v1",
    "request": "acfqp:incremental-proof-request-receipt:v1",
    "cache_state": "acfqp:incremental-proof-cache-state:v1",
    "cache": "acfqp:incremental-proof-cache:v1",
    "work": "acfqp:incremental-proof-dag-work:v1",
    "closure": "acfqp:incremental-proof-change-closure:v1",
    "prefix": "acfqp:incremental-proof-prefix:v1",
    "context_execution": "acfqp:incremental-proof-context-execution:v1",
    "execution": "acfqp:incremental-proof-dag-family-execution:v1",
    "legacy_match": "acfqp:incremental-proof-legacy-audit-match:v1",
    "result": "acfqp:incremental-proof-dag-control-result:v1",
}

if len(DOMAIN_TAGS) != len(set(DOMAIN_TAGS.values())):  # pragma: no cover
    raise RuntimeError("V0-051 content-ID domains must be unique")


class IncrementalProofDAGInvariantViolation(ValueError):
    """The proof graph, identity closure, replay, or claim lock is invalid."""


class ProofNodeKind(str, Enum):
    U = "U"
    P = "P"
    C = "C"
    D = "D"
    E = "E"
    F = "F"
    G = "G"
    R = "R"


class ProofCacheScope(str, Enum):
    REQUEST_RESET = "REQUEST_RESET"
    OCCURRENCE_RESET = "OCCURRENCE_RESET"
    GLOBAL = "GLOBAL"


class ProofResolutionOutcome(str, Enum):
    COMPUTED = "COMPUTED"
    REUSED = "REUSED"


class ProofRootRole(str, Enum):
    CANDIDATE_RANKING_AUDIT = "CANDIDATE_RANKING_AUDIT"
    INDEPENDENT_SELECTED_PLAN_CERTIFICATE = (
        "INDEPENDENT_SELECTED_PLAN_CERTIFICATE"
    )


def _content_id(role: str, payload: Mapping[str, Any]) -> str:
    try:
        encoded = canonical_json_bytes(dict(payload))
        domain = DOMAIN_TAGS[role]
    except (KeyError, TypeError, ValueError) as error:
        raise IncrementalProofDAGInvariantViolation(str(error)) from error
    return hashlib.sha256(domain.encode("utf-8") + b"\x00" + encoded).hexdigest()


def _cid(value: Any, field_name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise IncrementalProofDAGInvariantViolation(
            f"{field_name} must be a full content ID"
        ) from error


def _integer(value: Any, field_name: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise IncrementalProofDAGInvariantViolation(
            f"{field_name} must be an integer >= {minimum}"
        )
    return value


def _fraction(value: Any, field_name: str) -> Fraction:
    try:
        result = Fraction(value)
    except (TypeError, ValueError, ZeroDivisionError) as error:
        raise IncrementalProofDAGInvariantViolation(
            f"{field_name} must be rational"
        ) from error
    return result


def _fdoc(value: Fraction) -> dict[str, int]:
    return {"numerator": value.numerator, "denominator": value.denominator}


def _runtime_source_sha256(module: Any) -> str:
    path = Path(module.__file__)
    if path.suffix != ".py" or not path.is_file():
        raise IncrementalProofDAGInvariantViolation(
            "proof DAG semantics require registered Python source files"
        )
    return hashlib.sha256(path.read_bytes()).hexdigest()


@dataclass(frozen=True, slots=True)
class IncrementalProofDAGSemanticsV1:
    partial_audit_schema_version: str
    partial_audit_profile_key: str
    partial_audit_source_sha256: str
    family_planner_source_sha256: str
    robust_bellman_formula_id: str
    unrestricted_upper_formula_id: str
    arithmetic_kind: str = "EXACT_FRACTIONS_FRACTION"
    threshold_bound_v1_rows_only_at_root: bool = True
    monolithic_auditor_production_calls: int = 0
    lower_nodes_shared_across_roles: bool = True
    root_role_and_selected_result_bound: bool = True

    def __post_init__(self) -> None:
        _cid(self.partial_audit_source_sha256, "partial audit source SHA")
        _cid(self.family_planner_source_sha256, "family planner source SHA")
        if (
            self.partial_audit_schema_version != audit_module.SCHEMA_VERSION
            or self.partial_audit_profile_key != audit_module.PROFILE_KEY
            or self.partial_audit_source_sha256
            != EXPECTED_PARTIAL_AUDIT_SOURCE_SHA256
            or self.family_planner_source_sha256
            != EXPECTED_FAMILY_PLANNER_SOURCE_SHA256
            or self.robust_bellman_formula_id
            != audit_module.ROBUST_BELLMAN_FORMULA_ID
            or self.unrestricted_upper_formula_id
            != audit_module.UNRESTRICTED_UPPER_FORMULA_ID
            or self.arithmetic_kind != "EXACT_FRACTIONS_FRACTION"
            or self.threshold_bound_v1_rows_only_at_root is not True
            or self.monolithic_auditor_production_calls != 0
            or self.lower_nodes_shared_across_roles is not True
            or self.root_role_and_selected_result_bound is not True
        ):
            raise IncrementalProofDAGInvariantViolation(
                "incremental proof DAG semantics differ from the frozen profile"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.incremental_proof_dag_semantics.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            **{
                name: getattr(self, name)
                for name in self.__dataclass_fields__
            },
        }

    @property
    def semantics_id(self) -> str:
        return _content_id("semantics", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "semantics_id": self.semantics_id}


def incremental_proof_dag_semantics_v1() -> IncrementalProofDAGSemanticsV1:
    return IncrementalProofDAGSemanticsV1(
        audit_module.SCHEMA_VERSION,
        audit_module.PROFILE_KEY,
        _runtime_source_sha256(audit_module),
        _runtime_source_sha256(family_module),
        audit_module.ROBUST_BELLMAN_FORMULA_ID,
        audit_module.UNRESTRICTED_UPPER_FORMULA_ID,
    )


@dataclass(frozen=True, slots=True)
class IncrementalProofContextV1:
    context_index: int
    base_query_id: str
    query_index: int
    initial_state_id: str
    normalized_regret_tolerance: Fraction
    risk_tolerance: Fraction
    registration_phase: str = "BEFORE_INCREMENTAL_PROOF_EXECUTION"

    def __post_init__(self) -> None:
        _integer(self.context_index, "context index", 1)
        _integer(self.query_index, "context query index", 1)
        _cid(self.base_query_id, "context base query")
        _cid(self.initial_state_id, "context initial state")
        object.__setattr__(
            self,
            "normalized_regret_tolerance",
            _fraction(self.normalized_regret_tolerance, "context regret tolerance"),
        )
        object.__setattr__(
            self,
            "risk_tolerance",
            _fraction(self.risk_tolerance, "context risk tolerance"),
        )
        if (
            self.context_index > len(CONTEXT_SEQUENCE)
            or CONTEXT_SEQUENCE[self.context_index - 1]
            != (
                self.query_index,
                self.normalized_regret_tolerance,
                self.risk_tolerance,
            )
            or self.registration_phase != "BEFORE_INCREMENTAL_PROOF_EXECUTION"
        ):
            raise IncrementalProofDAGInvariantViolation(
                "context order or registered identity change was modified"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.incremental_proof_context.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "context_index": self.context_index,
            "base_query_id": self.base_query_id,
            "query_index": self.query_index,
            "initial_state_id": self.initial_state_id,
            "normalized_regret_tolerance": _fdoc(
                self.normalized_regret_tolerance
            ),
            "risk_tolerance": _fdoc(self.risk_tolerance),
            "registration_phase": self.registration_phase,
        }

    @property
    def context_id(self) -> str:
        return _content_id("context", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "context_id": self.context_id}


@dataclass(frozen=True, slots=True)
class IncrementalProofDAGProtocolV1:
    family_protocol_id: str
    ordered_contexts: tuple[IncrementalProofContextV1, ...]
    adjacent_change_kinds: tuple[str, ...] = (
        "INITIAL_DISTRIBUTION",
        "NORMALIZED_REGRET_TOLERANCE",
        "RISK_TOLERANCE",
        "INITIAL_DISTRIBUTION",
        "NORMALIZED_REGRET_TOLERANCE",
        "RISK_TOLERANCE",
    )
    horizon: int = 1
    candidate_requests_per_context: int = 2
    selected_requests_per_context: int = 1
    proof_requests_per_context: int = 3
    single_field_adjacency_required: bool = True
    registration_phase: str = "BEFORE_INCREMENTAL_PROOF_EXECUTION"

    def __post_init__(self) -> None:
        _cid(self.family_protocol_id, "incremental DAG family protocol")
        if (
            type(self.ordered_contexts) is not tuple
            or len(self.ordered_contexts) != 7
            or any(
                type(item) is not IncrementalProofContextV1
                for item in self.ordered_contexts
            )
            or tuple(item.context_index for item in self.ordered_contexts)
            != tuple(range(1, 8))
            or tuple(
                (
                    item.query_index,
                    item.normalized_regret_tolerance,
                    item.risk_tolerance,
                )
                for item in self.ordered_contexts
            )
            != CONTEXT_SEQUENCE
            or len({item.context_id for item in self.ordered_contexts}) != 7
            or self.adjacent_change_kinds
            != (
                "INITIAL_DISTRIBUTION",
                "NORMALIZED_REGRET_TOLERANCE",
                "RISK_TOLERANCE",
                "INITIAL_DISTRIBUTION",
                "NORMALIZED_REGRET_TOLERANCE",
                "RISK_TOLERANCE",
            )
            or self.horizon != 1
            or self.candidate_requests_per_context != 2
            or self.selected_requests_per_context != 1
            or self.proof_requests_per_context != 3
            or self.single_field_adjacency_required is not True
            or self.registration_phase
            != "BEFORE_INCREMENTAL_PROOF_EXECUTION"
        ):
            raise IncrementalProofDAGInvariantViolation(
                "incremental proof protocol order, H1 workload, or preregistration changed"
            )
        for previous, current, change_kind in zip(
            self.ordered_contexts,
            self.ordered_contexts[1:],
            self.adjacent_change_kinds,
        ):
            changed = tuple(
                name
                for name, left, right in (
                    (
                        "INITIAL_DISTRIBUTION",
                        (previous.base_query_id, previous.initial_state_id),
                        (current.base_query_id, current.initial_state_id),
                    ),
                    (
                        "NORMALIZED_REGRET_TOLERANCE",
                        previous.normalized_regret_tolerance,
                        current.normalized_regret_tolerance,
                    ),
                    (
                        "RISK_TOLERANCE",
                        previous.risk_tolerance,
                        current.risk_tolerance,
                    ),
                )
                if left != right
            )
            if changed != (change_kind,):
                raise IncrementalProofDAGInvariantViolation(
                    "adjacent contexts must change exactly one registered facet"
                )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.incremental_proof_dag_protocol.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "family_protocol_id": self.family_protocol_id,
            "ordered_contexts": [
                item.to_document() for item in self.ordered_contexts
            ],
            "adjacent_change_kinds": list(self.adjacent_change_kinds),
            "horizon": self.horizon,
            "candidate_requests_per_context": (
                self.candidate_requests_per_context
            ),
            "selected_requests_per_context": (
                self.selected_requests_per_context
            ),
            "proof_requests_per_context": self.proof_requests_per_context,
            "single_field_adjacency_required": (
                self.single_field_adjacency_required
            ),
            "registration_phase": self.registration_phase,
        }

    @property
    def protocol_id(self) -> str:
        return _content_id("protocol", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "protocol_id": self.protocol_id}


@dataclass(frozen=True, slots=True)
class IncrementalThresholdBindingV1:
    family_promotion_result_id: str
    family_protocol_id: str
    context: IncrementalProofContextV1
    promoted_model_id: str
    thresholds: FrozenPartialAuditThresholdsV1

    def __post_init__(self) -> None:
        for name in (
            "family_promotion_result_id",
            "family_protocol_id",
            "promoted_model_id",
        ):
            _cid(getattr(self, name), f"incremental binding {name}")
        if (
            type(self.context) is not IncrementalProofContextV1
            or type(self.thresholds) is not FrozenPartialAuditThresholdsV1
            or self.thresholds.partial_model_id != self.promoted_model_id
            or self.thresholds.horizon != 1
            or self.thresholds.initial_state_distribution
            != (InitialStateMassV1(self.context.initial_state_id, Fraction(1)),)
            or self.thresholds.normalized_regret_tolerance
            != self.context.normalized_regret_tolerance
            or self.thresholds.risk_tolerance != self.context.risk_tolerance
        ):
            raise IncrementalProofDAGInvariantViolation(
                "incremental context and threshold binding disagree"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.incremental_proof_threshold_binding.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "family_promotion_result_id": self.family_promotion_result_id,
            "family_protocol_id": self.family_protocol_id,
            "context": self.context.to_document(),
            "promoted_model_id": self.promoted_model_id,
            "thresholds": self.thresholds.to_document(),
        }

    @property
    def binding_id(self) -> str:
        return _content_id("binding", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "binding_id": self.binding_id}


_FORBIDDEN_LOWER_IDENTITY_TOKENS = (
    "threshold",
    "tolerance",
    "binding",
    "context",
    "audit_role",
    "planner_result",
)


@dataclass(frozen=True, slots=True)
class IncrementalProofNodeKeyV1:
    kind: ProofNodeKind
    semantics_id: str
    identity_terms: tuple[tuple[str, str], ...]
    dependency_node_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if type(self.kind) is not ProofNodeKind:
            raise IncrementalProofDAGInvariantViolation(
                "proof-node key requires the exact kind enum"
            )
        _cid(self.semantics_id, "proof-node semantics")
        if (
            type(self.identity_terms) is not tuple
            or not self.identity_terms
            or any(
                type(item) is not tuple
                or len(item) != 2
                or any(type(part) is not str or not part for part in item)
                for item in self.identity_terms
            )
            or tuple(name for name, _ in self.identity_terms)
            != tuple(sorted(set(name for name, _ in self.identity_terms)))
        ):
            raise IncrementalProofDAGInvariantViolation(
                "proof-node identity terms must be unique and name-sorted"
            )
        if (
            type(self.dependency_node_ids) is not tuple
            or self.dependency_node_ids
            != tuple(sorted(set(self.dependency_node_ids)))
        ):
            raise IncrementalProofDAGInvariantViolation(
                "proof-node dependencies must be unique and sorted"
            )
        for value in self.dependency_node_ids:
            _cid(value, "proof-node dependency")
        names = tuple(name.lower() for name, _ in self.identity_terms)
        if self.kind in {
            ProofNodeKind.U,
            ProofNodeKind.P,
            ProofNodeKind.C,
            ProofNodeKind.D,
            ProofNodeKind.G,
        } and any(token in name for name in names for token in _FORBIDDEN_LOWER_IDENTITY_TOKENS):
            raise IncrementalProofDAGInvariantViolation(
                "threshold-bound or role-bound identity leaked into a neutral node"
            )
        if self.kind is ProofNodeKind.E and names.count(
            "normalized_regret_tolerance"
        ) != 1:
            raise IncrementalProofDAGInvariantViolation(
                "E must bind exactly the normalized-regret tolerance"
            )
        if self.kind is ProofNodeKind.F and names.count("risk_tolerance") != 1:
            raise IncrementalProofDAGInvariantViolation(
                "F must bind exactly the risk tolerance"
            )
        if self.kind is ProofNodeKind.R and not {
            "thresholds_id",
            "context_id",
            "audit_role",
            "contingent_plan_id",
            "proof_request_id",
        }.issubset(set(names)):
            raise IncrementalProofDAGInvariantViolation(
                "R must bind context, thresholds, plan, and proof role"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.incremental_proof_node_key.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "kind": self.kind.value,
            "semantics_id": self.semantics_id,
            "identity_terms": [
                {"name": name, "value": value}
                for name, value in self.identity_terms
            ],
            "dependency_node_ids": list(self.dependency_node_ids),
        }

    @property
    def node_key_id(self) -> str:
        return _content_id("node_key", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "node_key_id": self.node_key_id}


@dataclass(frozen=True, slots=True)
class IncrementalProofNodeEntryV1:
    key: IncrementalProofNodeKeyV1
    result_digest: str
    result_semantics: str
    threshold_bound_v1_row_count: int = 0

    def __post_init__(self) -> None:
        if type(self.key) is not IncrementalProofNodeKeyV1:
            raise IncrementalProofDAGInvariantViolation(
                "proof-node entry rejects substituted keys"
            )
        _cid(self.result_digest, "proof-node result digest")
        _integer(
            self.threshold_bound_v1_row_count,
            "proof-node threshold-bound row count",
        )
        if not self.result_semantics:
            raise IncrementalProofDAGInvariantViolation(
                "proof-node result semantics are required"
            )
        if (
            self.key.kind is not ProofNodeKind.R
            and self.threshold_bound_v1_row_count != 0
        ):
            raise IncrementalProofDAGInvariantViolation(
                "legacy threshold-bound V1 rows are forbidden below R"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.incremental_proof_node_entry.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "key": self.key.to_document(),
            "result_digest": self.result_digest,
            "result_semantics": self.result_semantics,
            "threshold_bound_v1_row_count": self.threshold_bound_v1_row_count,
        }

    @property
    def entry_id(self) -> str:
        return _content_id("node_entry", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "entry_id": self.entry_id}


@dataclass(frozen=True, slots=True)
class IncrementalProofNodeResolutionV1:
    request_id: str
    ordinal_in_request: int
    kind: ProofNodeKind
    node_key_id: str
    entry_id: str
    pre_cache_state_id: str
    post_cache_state_id: str
    outcome: ProofResolutionOutcome

    def __post_init__(self) -> None:
        _cid(self.request_id, "node resolution request")
        _integer(self.ordinal_in_request, "node resolution ordinal", 1)
        if type(self.kind) is not ProofNodeKind or type(
            self.outcome
        ) is not ProofResolutionOutcome:
            raise IncrementalProofDAGInvariantViolation(
                "node resolution enum was substituted"
            )
        _cid(self.node_key_id, "node resolution key")
        _cid(self.entry_id, "node resolution entry")

        _cid(self.pre_cache_state_id, "node resolution pre-cache state")
        _cid(self.post_cache_state_id, "node resolution post-cache state")
    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.incremental_proof_node_resolution.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "request_id": self.request_id,
            "ordinal_in_request": self.ordinal_in_request,
            "kind": self.kind.value,
            "node_key_id": self.node_key_id,
            "entry_id": self.entry_id,
            "pre_cache_state_id": self.pre_cache_state_id,
            "post_cache_state_id": self.post_cache_state_id,
            "outcome": self.outcome.value,
        }

    @property
    def resolution_id(self) -> str:
        return _content_id("resolution", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "resolution_id": self.resolution_id}


@dataclass(frozen=True, slots=True)
class IncrementalProofRequestReceiptV1:
    request_sequence: int
    context_id: str
    audit_role: ProofRootRole
    contingent_plan_id: str
    planner_result_id: str | None
    resolutions: tuple[IncrementalProofNodeResolutionV1, ...]
    audit_result_id: str

    def __post_init__(self) -> None:
        _integer(self.request_sequence, "proof request sequence", 1)
        for name in ("context_id", "contingent_plan_id", "audit_result_id"):
            _cid(getattr(self, name), f"proof request {name}")
        if type(self.audit_role) is not ProofRootRole:
            raise IncrementalProofDAGInvariantViolation(
                "proof request requires the exact role enum"
            )
        if self.planner_result_id is not None:
            _cid(self.planner_result_id, "proof request planner result")
        if (
            self.audit_role is ProofRootRole.CANDIDATE_RANKING_AUDIT
            and self.planner_result_id is not None
        ) or (
            self.audit_role
            is ProofRootRole.INDEPENDENT_SELECTED_PLAN_CERTIFICATE
            and self.planner_result_id is None
        ):
            raise IncrementalProofDAGInvariantViolation(
                "root role and selected planner-result binding disagree"
            )
        if (
            type(self.resolutions) is not tuple
            or tuple(item.kind for item in self.resolutions)
            != tuple(ProofNodeKind)
            or any(
                type(item) is not IncrementalProofNodeResolutionV1
                for item in self.resolutions
            )
        ):
            raise IncrementalProofDAGInvariantViolation(
                "every request must resolve U,P,C,D,E,F,G,R exactly once"
            )

    def _payload_without_id(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.incremental_proof_request_receipt.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "request_sequence": self.request_sequence,
            "context_id": self.context_id,
            "audit_role": self.audit_role.value,
            "contingent_plan_id": self.contingent_plan_id,
            "planner_result_id": self.planner_result_id,
            "resolutions": [item.to_document() for item in self.resolutions],
            "audit_result_id": self.audit_result_id,
        }

    @property
    def request_id(self) -> str:
        # Resolution objects already bind the preregistered pre-resolution ID;
        # use the same deterministic header here to avoid a recursive hash.
        return _request_id(
            self.request_sequence,
            self.context_id,
            self.audit_role,
            self.contingent_plan_id,
            self.planner_result_id,
        )

    @property
    def receipt_id(self) -> str:
        return _content_id("request", self._payload_without_id())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload_without_id(),
            "request_id": self.request_id,
            "receipt_id": self.receipt_id,
        }


def _request_id(
    sequence: int,
    context_id: str,
    role: ProofRootRole,
    plan_id: str,
    planner_result_id: str | None,
) -> str:
    return _content_id(
        "request",
        {
            "schema": "acfqp.incremental_proof_request_header.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "request_sequence": sequence,
            "context_id": context_id,
            "audit_role": role.value,
            "contingent_plan_id": plan_id,
            "planner_result_id": planner_result_id,
        },
    )


@dataclass(frozen=True, slots=True)
class IncrementalProofCacheV1:
    scope: ProofCacheScope
    entries: tuple[IncrementalProofNodeEntryV1, ...]

    def __post_init__(self) -> None:
        if type(self.scope) is not ProofCacheScope or type(self.entries) is not tuple:
            raise IncrementalProofDAGInvariantViolation(
                "incremental proof cache type or scope was substituted"
            )
        if any(type(item) is not IncrementalProofNodeEntryV1 for item in self.entries):
            raise IncrementalProofDAGInvariantViolation(
                "incremental proof cache rejects duck entries"
            )
        keys = tuple(item.key.node_key_id for item in self.entries)
        if keys != tuple(sorted(set(keys))):
            raise IncrementalProofDAGInvariantViolation(
                "incremental proof cache keys must be unique and sorted"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.incremental_proof_cache.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "scope": self.scope.value,
            "entries": [item.to_document() for item in self.entries],
        }

    @property
    def cache_id(self) -> str:
        return _content_id("cache", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "cache_id": self.cache_id}




def _cache_state_id(
    entries: Mapping[str, IncrementalProofNodeEntryV1],
) -> str:
    return _content_id(
        "cache_state",
        {
            "schema": "acfqp.incremental_proof_cache_state.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "entries": [
                {"node_key_id": key_id, "entry_id": entries[key_id].entry_id}
                for key_id in sorted(entries)
            ],
        },
    )
@dataclass(frozen=True, order=True, slots=True)
class ProofKindCountV1:
    kind: ProofNodeKind
    computed_count: int
    reused_count: int

    def __post_init__(self) -> None:
        if type(self.kind) is not ProofNodeKind:
            raise IncrementalProofDAGInvariantViolation(
                "proof-kind work requires the exact kind enum"
            )
        _integer(self.computed_count, "proof-kind computed count")
        _integer(self.reused_count, "proof-kind reused count")

    def to_document(self) -> dict[str, Any]:
        return {
            "kind": self.kind.value,
            "computed_count": self.computed_count,
            "reused_count": self.reused_count,
        }


@dataclass(frozen=True, slots=True)
class ProofDAGWorkV1:
    cache_scope: ProofCacheScope
    context_count: int
    proof_request_count: int
    obligation_resolution_count: int
    kind_counts: tuple[ProofKindCountV1, ...]
    target_transition_calls: int = 0
    target_catalogue_calls: int = 0
    direct_ground_optimizer_calls: int = 0
    production_monolithic_auditor_calls: int = 0

    def __post_init__(self) -> None:
        if type(self.cache_scope) is not ProofCacheScope:
            raise IncrementalProofDAGInvariantViolation(
                "proof work cache scope was substituted"
            )
        for name in (
            "context_count",
            "proof_request_count",
            "obligation_resolution_count",
            "target_transition_calls",
            "target_catalogue_calls",
            "direct_ground_optimizer_calls",
            "production_monolithic_auditor_calls",
        ):
            _integer(getattr(self, name), f"proof work {name}")
        if (
            type(self.kind_counts) is not tuple
            or tuple(item.kind for item in self.kind_counts) != tuple(ProofNodeKind)
            or any(type(item) is not ProofKindCountV1 for item in self.kind_counts)
        ):
            raise IncrementalProofDAGInvariantViolation(
                "proof work must report every node kind in DAG order"
            )
        computed = sum(item.computed_count for item in self.kind_counts)
        reused = sum(item.reused_count for item in self.kind_counts)
        expected_by_scope = {
            ProofCacheScope.REQUEST_RESET: (168, 0),
            ProofCacheScope.OCCURRENCE_RESET: (112, 56),
            ProofCacheScope.GLOBAL: (62, 106),
        }
        if (
            self.context_count != 7
            or self.proof_request_count != 21
            or self.obligation_resolution_count != 168
            or (computed, reused) != expected_by_scope[self.cache_scope]
            or computed + reused != self.obligation_resolution_count
            or self.target_transition_calls != 0
            or self.target_catalogue_calls != 0
            or self.direct_ground_optimizer_calls != 0
            or self.production_monolithic_auditor_calls != 0
        ):
            raise IncrementalProofDAGInvariantViolation(
                "proof work counts or no-ground/no-monolithic boundary changed"
            )
        if self.cache_scope is ProofCacheScope.GLOBAL and (
            {item.kind.value: item.computed_count for item in self.kind_counts}
            != EXPECTED_GLOBAL_COMPUTES
            or {item.kind.value: item.reused_count for item in self.kind_counts}
            != EXPECTED_GLOBAL_REUSES
        ):
            raise IncrementalProofDAGInvariantViolation(
                "global proof work per-kind counts changed"
            )

    @property
    def computed_count(self) -> int:
        return sum(item.computed_count for item in self.kind_counts)

    @property
    def reused_count(self) -> int:
        return sum(item.reused_count for item in self.kind_counts)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.incremental_proof_dag_work.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "cache_scope": self.cache_scope.value,
            "context_count": self.context_count,
            "proof_request_count": self.proof_request_count,
            "obligation_resolution_count": self.obligation_resolution_count,
            "kind_counts": [item.to_document() for item in self.kind_counts],
            "computed_count": self.computed_count,
            "reused_count": self.reused_count,
            "target_transition_calls": self.target_transition_calls,
            "target_catalogue_calls": self.target_catalogue_calls,
            "direct_ground_optimizer_calls": self.direct_ground_optimizer_calls,
            "production_monolithic_auditor_calls": (
                self.production_monolithic_auditor_calls
            ),
        }

    @property
    def work_id(self) -> str:
        return _content_id("work", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "work_id": self.work_id}


@dataclass(frozen=True, slots=True)
class ContextChangeClosureV1:
    context_index: int
    previous_context_id: str | None
    context_id: str
    directly_changed_facets: tuple[str, ...]
    expected_new_nodes_by_kind: tuple[ProofKindCountV1, ...]
    actual_new_nodes_by_kind: tuple[ProofKindCountV1, ...]

    def __post_init__(self) -> None:
        _integer(self.context_index, "change closure context index", 1)
        if self.previous_context_id is not None:
            _cid(self.previous_context_id, "change closure previous context")
        _cid(self.context_id, "change closure context")
        expected_facets = (
            ("INITIAL_CONTEXT",)
            if self.context_index == 1
            else (
                ("INITIAL_DISTRIBUTION",)
                if self.context_index in (2, 5)
                else (
                    ("NORMALIZED_REGRET_TOLERANCE",)
                    if self.context_index in (3, 6)
                    else ("RISK_TOLERANCE",)
                )
            )
        )
        if self.directly_changed_facets != expected_facets:
            raise IncrementalProofDAGInvariantViolation(
                "change closure direct facet differs from the registered sequence"
            )
        for counts in (
            self.expected_new_nodes_by_kind,
            self.actual_new_nodes_by_kind,
        ):
            if (
                type(counts) is not tuple
                or tuple(item.kind for item in counts) != tuple(ProofNodeKind)
                or any(type(item) is not ProofKindCountV1 for item in counts)
                or any(item.reused_count != 0 for item in counts)
            ):
                raise IncrementalProofDAGInvariantViolation(
                    "change closure must report ordered computed-only counts"
                )
        if self.expected_new_nodes_by_kind != self.actual_new_nodes_by_kind:
            raise IncrementalProofDAGInvariantViolation(
                "actual recomputation differs from the dependency closure"
            )

    @property
    def recomputed_kinds(self) -> tuple[ProofNodeKind, ...]:
        return tuple(
            item.kind
            for item in self.actual_new_nodes_by_kind
            if item.computed_count
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.incremental_proof_change_closure.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "context_index": self.context_index,
            "previous_context_id": self.previous_context_id,
            "context_id": self.context_id,
            "directly_changed_facets": list(self.directly_changed_facets),
            "expected_new_nodes_by_kind": [
                item.to_document() for item in self.expected_new_nodes_by_kind
            ],
            "actual_new_nodes_by_kind": [
                item.to_document() for item in self.actual_new_nodes_by_kind
            ],
            "recomputed_kinds": [item.value for item in self.recomputed_kinds],
        }

    @property
    def closure_id(self) -> str:
        return _content_id("closure", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "closure_id": self.closure_id}


@dataclass(frozen=True, slots=True)
class ProofDAGPrefixV1:
    cache_scope: ProofCacheScope
    prefix_length: int
    context_ids: tuple[str, ...]
    cumulative_computed_count: int
    cumulative_reused_count: int
    cumulative_resolution_count: int

    def __post_init__(self) -> None:
        if type(self.cache_scope) is not ProofCacheScope:
            raise IncrementalProofDAGInvariantViolation(
                "prefix cache scope was substituted"
            )
        _integer(self.prefix_length, "proof prefix length", 1)
        for name in (
            "cumulative_computed_count",
            "cumulative_reused_count",
            "cumulative_resolution_count",
        ):
            _integer(getattr(self, name), f"proof prefix {name}")
        if len(self.context_ids) != self.prefix_length:
            raise IncrementalProofDAGInvariantViolation(
                "proof prefix context cardinality changed"
            )
        for value in self.context_ids:
            _cid(value, "proof prefix context")
        expected_computed = {
            ProofCacheScope.REQUEST_RESET: (24, 48, 72, 96, 120, 144, 168),
            ProofCacheScope.OCCURRENCE_RESET: (16, 32, 48, 64, 80, 96, 112),
            ProofCacheScope.GLOBAL: (16, 29, 34, 39, 52, 57, 62),
        }[self.cache_scope][self.prefix_length - 1]
        expected_total = 24 * self.prefix_length
        if (
            self.cumulative_computed_count != expected_computed
            or self.cumulative_resolution_count != expected_total
            or self.cumulative_reused_count != expected_total - expected_computed
        ):
            raise IncrementalProofDAGInvariantViolation(
                "proof prefix does not match the registered reuse curve"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.incremental_proof_prefix.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "cache_scope": self.cache_scope.value,
            "prefix_length": self.prefix_length,
            "context_ids": list(self.context_ids),
            "cumulative_computed_count": self.cumulative_computed_count,
            "cumulative_reused_count": self.cumulative_reused_count,
            "cumulative_resolution_count": self.cumulative_resolution_count,
        }

    @property
    def prefix_id(self) -> str:
        return _content_id("prefix", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "prefix_id": self.prefix_id}


@dataclass(frozen=True, slots=True)
class IncrementalProofContextExecutionV1:
    context: IncrementalProofContextV1
    threshold_binding: IncrementalThresholdBindingV1
    plan_proposal: HeldOutPlanProposalV1
    candidate_audit_results: tuple[PartialSoundAuditResultV1, ...]
    selected_plan_audit: HeldOutPlanAuditV1
    request_receipt_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if (
            type(self.context) is not IncrementalProofContextV1
            or type(self.threshold_binding) is not IncrementalThresholdBindingV1
            or type(self.plan_proposal) is not HeldOutPlanProposalV1
            or type(self.selected_plan_audit) is not HeldOutPlanAuditV1
            or type(self.candidate_audit_results) is not tuple
            or len(self.candidate_audit_results) != 2
            or any(
                type(item) is not PartialSoundAuditResultV1
                for item in self.candidate_audit_results
            )
            or len(self.request_receipt_ids) != 3
        ):
            raise IncrementalProofDAGInvariantViolation(
                "context execution rejects substituted planning/proof artifacts"
            )
        for value in self.request_receipt_ids:
            _cid(value, "context execution request receipt")
        if (
            self.threshold_binding.context.context_id != self.context.context_id
            or self.plan_proposal.target_query_id != self.context.context_id
            or self.plan_proposal.threshold_binding_id
            != self.threshold_binding.binding_id
            or self.selected_plan_audit.target_query_id != self.context.context_id
            or self.selected_plan_audit.threshold_binding_id
            != self.threshold_binding.binding_id
            or self.selected_plan_audit.planner_result_id
            != self.plan_proposal.result_id
            or tuple(
                item.result_id
                for item in sorted(
                    self.candidate_audit_results,
                    key=lambda audit: audit.contingent_plan_id,
                )
            )
            != tuple(
                item.audit_result_id
                for item in self.plan_proposal.candidate_summaries
            )
        ):
            raise IncrementalProofDAGInvariantViolation(
                "context execution identity chain is inconsistent"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.incremental_proof_context_execution.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "context": self.context.to_document(),
            "threshold_binding": self.threshold_binding.to_document(),
            "plan_proposal": self.plan_proposal.to_document(),
            "candidate_audit_results": [
                item.to_document() for item in self.candidate_audit_results
            ],
            "selected_plan_audit": self.selected_plan_audit.to_document(),
            "request_receipt_ids": list(self.request_receipt_ids),
        }

    @property
    def result_id(self) -> str:
        return _content_id("context_execution", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "result_id": self.result_id}


_INCREMENTAL_EXECUTION_AUTHORITY = object()


@dataclass(frozen=True, slots=True)
class IncrementalProofDAGFamilyExecutionV1:
    semantics: IncrementalProofDAGSemanticsV1
    cache_scope: ProofCacheScope
    family_promotion_result_id: str
    family_protocol_id: str
    protocol: IncrementalProofDAGProtocolV1
    contexts: tuple[IncrementalProofContextExecutionV1, ...]
    use_receipts: tuple[IncrementalProofRequestReceiptV1, ...]
    entry_catalogue: tuple[IncrementalProofNodeEntryV1, ...]
    final_cache: IncrementalProofCacheV1
    aggregate_work: ProofDAGWorkV1
    prefixes: tuple[ProofDAGPrefixV1, ...]
    change_closures: tuple[ContextChangeClosureV1, ...]
    initial_store_empty: bool
    _authority: object = field(repr=False, compare=False)
    _instance_mint: RuntimeAuthorityMintV1 | None = field(
        default=None, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        if self._authority is not _INCREMENTAL_EXECUTION_AUTHORITY:
            raise IncrementalProofDAGInvariantViolation(
                "incremental proof execution was not minted by its trusted runner"
            )
        if self._instance_mint is not None:
            try:
                self._instance_mint.validate_construction(
                    self,
                    issuer=_INCREMENTAL_EXECUTION_AUTHORITY,
                    fingerprint=runtime_authority_fingerprint_v1(self),
                )
            except ValueError as error:
                raise IncrementalProofDAGInvariantViolation(
                    "incremental execution is copied, replaced, or modified"
                ) from error
        if (
            type(self.semantics) is not IncrementalProofDAGSemanticsV1
            or type(self.cache_scope) is not ProofCacheScope
            or type(self.protocol) is not IncrementalProofDAGProtocolV1
            or type(self.final_cache) is not IncrementalProofCacheV1
            or type(self.aggregate_work) is not ProofDAGWorkV1
            or self.final_cache.scope is not self.cache_scope
            or self.aggregate_work.cache_scope is not self.cache_scope
            or type(self.contexts) is not tuple
            or len(self.contexts) != 7
            or any(
                type(item) is not IncrementalProofContextExecutionV1
                for item in self.contexts
            )
            or self.protocol.family_protocol_id != self.family_protocol_id
            or tuple(
                item.context.to_document() for item in self.contexts
            ) != tuple(
                item.to_document() for item in self.protocol.ordered_contexts
            )
            or len({
                item.threshold_binding.thresholds.thresholds_id
                for item in self.contexts
            }) != 7
            or len({
                item.threshold_binding.binding_id for item in self.contexts
            }) != 7
            or type(self.use_receipts) is not tuple
            or len(self.use_receipts) != 21
            or any(
                type(item) is not IncrementalProofRequestReceiptV1
                for item in self.use_receipts
            )
            or type(self.entry_catalogue) is not tuple
            or any(
                type(item) is not IncrementalProofNodeEntryV1
                for item in self.entry_catalogue
            )
            or type(self.prefixes) is not tuple
            or len(self.prefixes) != 7
            or type(self.change_closures) is not tuple
            or len(self.change_closures) != 7
            or self.initial_store_empty is not True
        ):
            raise IncrementalProofDAGInvariantViolation(
                "incremental execution cardinality or typed artifact changed"
            )
        _cid(self.family_promotion_result_id, "execution family promotion")
        _cid(self.family_protocol_id, "execution family protocol")
        _validate_execution_trace(self)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.incremental_proof_dag_family_execution.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "semantics": self.semantics.to_document(),
            "cache_scope": self.cache_scope.value,
            "family_promotion_result_id": self.family_promotion_result_id,
            "family_protocol_id": self.family_protocol_id,
            "protocol": self.protocol.to_document(),
            "contexts": [item.to_document() for item in self.contexts],
            "use_receipts": [item.to_document() for item in self.use_receipts],
            "entry_catalogue": [item.to_document() for item in self.entry_catalogue],
            "final_cache": self.final_cache.to_document(),
            "aggregate_work": self.aggregate_work.to_document(),
            "prefixes": [item.to_document() for item in self.prefixes],
            "change_closures": [item.to_document() for item in self.change_closures],
            "initial_store_empty": self.initial_store_empty,
        }

    @property
    def execution_id(self) -> str:
        return _content_id("execution", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "execution_id": self.execution_id}


def require_incremental_proof_dag_family_execution_v1(
    execution: IncrementalProofDAGFamilyExecutionV1,
) -> IncrementalProofDAGFamilyExecutionV1:
    if type(execution) is not IncrementalProofDAGFamilyExecutionV1:
        raise IncrementalProofDAGInvariantViolation(
            "incremental proof execution requires its exact authority type"
        )
    try:
        require_runtime_authority_v1(
            execution,
            issuer=_INCREMENTAL_EXECUTION_AUTHORITY,
        )
    except ValueError as error:
        raise IncrementalProofDAGInvariantViolation(
            "incremental proof execution lacks owner-bound authority"
        ) from error
    _validate_execution_trace(execution)
    return execution



@dataclass(frozen=True, slots=True)
class _URow:
    time_index: int
    remaining_horizon: int
    state_id: str
    cell_id: str
    ground_row_id: str
    ground_action_id: str
    reward_upper: Fraction


@dataclass(frozen=True, slots=True)
class _NeutralU:
    initial_state_upper: Mapping[str, Fraction]
    rows: tuple[_URow, ...]


@dataclass(frozen=True, slots=True)
class _PRow:
    time_index: int
    remaining_horizon: int
    cell_id: str
    action_id: str
    representative_state_ids: tuple[str, ...]
    missing_ground_row_ids: tuple[str, ...]
    reward_lower: Fraction
    reward_upper: Fraction
    failure_lower: Fraction
    failure_upper: Fraction
    max_shared_unknown_mass: Fraction
    external_boundary_possible: bool
    representative_disagreement: bool


@dataclass(frozen=True, slots=True)
class _NeutralP:
    table: Mapping[tuple[int, str], Any]
    rows: tuple[_PRow, ...]


@dataclass(frozen=True, slots=True)
class _CRow:
    time_index: int
    remaining_horizon: int
    state_id: str
    cell_id: str
    action_id: str
    support_ground_row_ids: tuple[str, ...]
    observed_ground_row_ids: tuple[str, ...]
    missing_ground_row_ids: tuple[str, ...]
    reachable_cell_mass_upper: Fraction
    shared_unknown_mass: Fraction
    known_external_successor_mass: Fraction
    reachable_unknown_mass_upper: Fraction
    reachable_external_continuation_mass_upper: Fraction
    representative_disagreement: bool
    realization_singleton: bool


@dataclass(frozen=True, slots=True)
class _NeutralC:
    rows: tuple[_CRow, ...]
    reachable_pairs: tuple[tuple[int, str], ...]


@dataclass(frozen=True, slots=True)
class _NeutralD:
    initial_bounds: Mapping[str, Any]
    unrestricted_upper: Fraction
    root_reward_lower: Fraction
    root_reward_upper: Fraction
    root_failure_lower: Fraction
    root_failure_upper: Fraction
    raw_distribution_regret: Fraction
    normalized_distribution_regret: Fraction
    support_metrics: tuple[
        tuple[str, str, Fraction, Fraction, Fraction, Fraction, Fraction], ...
    ]


@dataclass(frozen=True, slots=True)
class _NeutralE:
    support_certified: tuple[bool, ...]
    reward_certified: bool


@dataclass(frozen=True, slots=True)
class _NeutralF:
    risk_certified: bool


@dataclass(frozen=True, slots=True)
class _NeutralG:
    external_row_indices: tuple[int, ...]
    coverage_certified: bool


def _fraction_text(value: Fraction) -> str:
    return f"{value.numerator}/{value.denominator}"


def _terms(**values: str) -> tuple[tuple[str, str], ...]:
    return tuple(sorted(values.items()))


def _neutral_digest(kind: ProofNodeKind, document: Mapping[str, Any]) -> str:
    return _content_id(
        "node_result",
        {
            "schema": "acfqp.incremental_proof_neutral_result.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "kind": kind.value,
            "document": dict(document),
        },
    )


def _u_document(value: _NeutralU) -> dict[str, Any]:
    return {
        "initial_state_upper": [
            {"state_id": state_id, "reward_upper": _fdoc(upper)}
            for state_id, upper in sorted(value.initial_state_upper.items())
        ],
        "rows": [
            {
                "time_index": row.time_index,
                "remaining_horizon": row.remaining_horizon,
                "state_id": row.state_id,
                "cell_id": row.cell_id,
                "ground_row_id": row.ground_row_id,
                "ground_action_id": row.ground_action_id,
                "reward_upper": _fdoc(row.reward_upper),
            }
            for row in value.rows
        ],
    }


def _p_document(value: _NeutralP) -> dict[str, Any]:
    return {
        "rows": [
            {
                "time_index": row.time_index,
                "remaining_horizon": row.remaining_horizon,
                "cell_id": row.cell_id,
                "action_id": row.action_id,
                "representative_state_ids": list(row.representative_state_ids),
                "missing_ground_row_ids": list(row.missing_ground_row_ids),
                "reward_lower": _fdoc(row.reward_lower),
                "reward_upper": _fdoc(row.reward_upper),
                "failure_lower": _fdoc(row.failure_lower),
                "failure_upper": _fdoc(row.failure_upper),
                "max_shared_unknown_mass": _fdoc(row.max_shared_unknown_mass),
                "external_boundary_possible": row.external_boundary_possible,
                "representative_disagreement": row.representative_disagreement,
            }
            for row in value.rows
        ]
    }


def _c_document(value: _NeutralC) -> dict[str, Any]:
    return {
        "rows": [
            {
                "time_index": row.time_index,
                "remaining_horizon": row.remaining_horizon,
                "state_id": row.state_id,
                "cell_id": row.cell_id,
                "action_id": row.action_id,
                "support_ground_row_ids": list(row.support_ground_row_ids),
                "observed_ground_row_ids": list(row.observed_ground_row_ids),
                "missing_ground_row_ids": list(row.missing_ground_row_ids),
                "reachable_cell_mass_upper": _fdoc(row.reachable_cell_mass_upper),
                "shared_unknown_mass": _fdoc(row.shared_unknown_mass),
                "known_external_successor_mass": _fdoc(
                    row.known_external_successor_mass
                ),
                "reachable_unknown_mass_upper": _fdoc(
                    row.reachable_unknown_mass_upper
                ),
                "reachable_external_continuation_mass_upper": _fdoc(
                    row.reachable_external_continuation_mass_upper
                ),
                "representative_disagreement": row.representative_disagreement,
                "realization_singleton": row.realization_singleton,
            }
            for row in value.rows
        ],
        "reachable_pairs": [
            {"time_index": time_index, "cell_id": cell_id}
            for time_index, cell_id in value.reachable_pairs
        ],
    }


def _d_document(value: _NeutralD) -> dict[str, Any]:
    return {
        "unrestricted_upper": _fdoc(value.unrestricted_upper),
        "root_reward_lower": _fdoc(value.root_reward_lower),
        "root_reward_upper": _fdoc(value.root_reward_upper),
        "root_failure_lower": _fdoc(value.root_failure_lower),
        "root_failure_upper": _fdoc(value.root_failure_upper),
        "raw_distribution_regret": _fdoc(value.raw_distribution_regret),
        "normalized_distribution_regret": _fdoc(
            value.normalized_distribution_regret
        ),
        "support_metrics": [
            {
                "state_id": state_id,
                "cell_id": cell_id,
                "probability": _fdoc(probability),
                "unrestricted_upper": _fdoc(unrestricted_upper),
                "policy_lower": _fdoc(policy_lower),
                "raw_regret": _fdoc(raw_regret),
                "normalized_regret": _fdoc(normalized_regret),
            }
            for (
                state_id,
                cell_id,
                probability,
                unrestricted_upper,
                policy_lower,
                raw_regret,
                normalized_regret,
            ) in value.support_metrics
        ],
    }


def _compute_u(
    partial_model: Any,
    thresholds: FrozenPartialAuditThresholdsV1,
    active_cells: Mapping[str, Any],
) -> _NeutralU:
    weights = {item.name: item.weight for item in thresholds.reward_weights}
    per_step_lower, per_step_upper = audit_module._cap_interval(
        partial_model, weights
    )
    return_upper = thresholds.return_bound_proof.return_upper
    active_ids = tuple(sorted(active_cells))
    state_to_cell = {
        state_id: cell_id
        for cell_id, cell in active_cells.items()
        for state_id in cell.member_state_ids
    }
    rows_by_state: dict[str, list[Any]] = {
        state_id: [] for state_id in state_to_cell
    }
    for ground_row in partial_model.ground_rows:
        if ground_row.state_id in rows_by_state:
            rows_by_state[ground_row.state_id].append(ground_row)
    if any(not rows for rows in rows_by_state.values()):
        raise IncrementalProofDAGInvariantViolation(
            "neutral U lacks a complete active-state action catalogue"
        )
    cell_upper: dict[tuple[int, str], Fraction] = {}
    rows: list[_URow] = []
    initial_state_upper: dict[str, Fraction] = {}
    for time_index in reversed(range(thresholds.horizon)):
        remaining = thresholds.horizon - time_index
        next_upper = {
            cell_id: (
                Fraction(0)
                if remaining == 1
                else cell_upper[(time_index + 1, cell_id)]
            )
            for cell_id in active_ids
        }
        outside = audit_module._outside_bound(
            remaining - 1,
            per_step_lower,
            per_step_upper,
            return_upper,
        )
        state_upper: dict[str, Fraction] = {}
        for state_id in sorted(rows_by_state):
            action_values: list[Fraction] = []
            cell_id = state_to_cell[state_id]
            for ground_row in sorted(
                rows_by_state[state_id], key=lambda item: item.ground_row_id
            ):
                ambiguity = ground_row.ambiguity
                _, value_upper = audit_module._reward_interval(ambiguity, weights)
                for destination, mass in ambiguity.known_successor_masses:
                    value_upper += mass * (
                        outside.reward_upper
                        if destination == partial_model.external_boundary_id
                        else next_upper[destination]
                    )
                shared_unknown = audit_module._validate_joint_simplex(ambiguity)
                if shared_unknown:
                    value_upper += shared_unknown * max(
                        Fraction(0),
                        outside.reward_upper,
                        *(next_upper[destination] for destination in active_ids),
                    )
                value_upper = min(return_upper, value_upper)
                action_values.append(value_upper)
                rows.append(
                    _URow(
                        time_index,
                        remaining,
                        state_id,
                        cell_id,
                        ground_row.ground_row_id,
                        ground_row.ground_action_id,
                        value_upper,
                    )
                )
            state_upper[state_id] = max(action_values)
        if time_index == 0:
            initial_state_upper = dict(state_upper)
        for cell_id, cell in active_cells.items():
            cell_upper[(time_index, cell_id)] = max(
                state_upper[state_id] for state_id in cell.member_state_ids
            )
    return _NeutralU(
        initial_state_upper,
        tuple(
            sorted(
                rows,
                key=lambda item: (
                    item.time_index,
                    item.state_id,
                    item.ground_row_id,
                ),
            )
        ),
    )


def _compute_p(
    partial_model: Any,
    thresholds: FrozenPartialAuditThresholdsV1,
    contingent_plan: FrozenContingentAbstractPlanV1,
    active_cells: Mapping[str, Any],
    realizations: Mapping[tuple[str, str], tuple[Any, ...]],
    stage_maps: Mapping[int, Mapping[str, str]],
) -> _NeutralP:
    weights = {item.name: item.weight for item in thresholds.reward_weights}
    per_step_lower, per_step_upper = audit_module._cap_interval(
        partial_model, weights
    )
    return_upper = thresholds.return_bound_proof.return_upper
    active_ids = tuple(sorted(active_cells))
    table: dict[tuple[int, str], Any] = {}
    rows: list[_PRow] = []
    zero_next = {
        cell_id: audit_module._Bound(
            Fraction(0), Fraction(0), Fraction(0), Fraction(0)
        )
        for cell_id in active_ids
    }
    for time_index in reversed(range(thresholds.horizon)):
        remaining = thresholds.horizon - time_index
        next_by_cell = (
            zero_next
            if remaining == 1
            else {
                cell_id: table[(time_index + 1, cell_id)]
                for cell_id in active_ids
            }
        )
        outside = audit_module._outside_bound(
            remaining - 1,
            per_step_lower,
            per_step_upper,
            return_upper,
        )
        for cell_id in active_ids:
            action_id = stage_maps[time_index][cell_id]
            state_rows = realizations[(cell_id, action_id)]
            state_bounds = tuple(
                audit_module._realization_bound(
                    item.ambiguity,
                    next_by_cell,
                    active_ids,
                    partial_model.external_boundary_id,
                    outside,
                    weights,
                    return_upper,
                )
                for item in state_rows
            )
            bound = audit_module._Bound(
                min(item.reward_lower for item in state_bounds),
                max(item.reward_upper for item in state_bounds),
                min(item.failure_lower for item in state_bounds),
                max(item.failure_upper for item in state_bounds),
            )
            table[(time_index, cell_id)] = bound
            documents = tuple(item.ambiguity.to_document() for item in state_rows)
            rows.append(
                _PRow(
                    time_index,
                    remaining,
                    cell_id,
                    action_id,
                    tuple(item.state_id for item in state_rows),
                    tuple(
                        sorted(
                            {
                                row_id
                                for item in state_rows
                                for row_id in item.missing_ground_row_ids
                            }
                        )
                    ),
                    bound.reward_lower,
                    bound.reward_upper,
                    bound.failure_lower,
                    bound.failure_upper,
                    max(
                        item.ambiguity.joint_simplex_constraint.unknown_atom_mass_sum
                        for item in state_rows
                    ),
                    any(
                        item.ambiguity.joint_simplex_constraint.unknown_atom_mass_sum
                        > 0
                        or dict(item.ambiguity.known_successor_masses).get(
                            partial_model.external_boundary_id, Fraction(0)
                        )
                        > 0
                        for item in state_rows
                    ),
                    any(document != documents[0] for document in documents[1:]),
                )
            )
    return _NeutralP(
        table,
        tuple(sorted(rows, key=lambda item: (item.time_index, item.cell_id))),
    )


def _compute_c(
    partial_model: Any,
    thresholds: FrozenPartialAuditThresholdsV1,
    realizations: Mapping[tuple[str, str], tuple[Any, ...]],
    stage_maps: Mapping[int, Mapping[str, str]],
    state_to_cell: Mapping[str, str],
) -> _NeutralC:
    active_ids = tuple(
        sorted(
            item.cell_id
            for item in partial_model.cells
            if item.planning_kind.value == "ACTIVE"
        )
    )
    reach_upper: dict[str, Fraction] = {}
    for item in thresholds.initial_state_distribution:
        cell_id = state_to_cell[item.state_id]
        reach_upper[cell_id] = reach_upper.get(cell_id, Fraction(0)) + item.probability
    rows: list[_CRow] = []
    reachable_pairs: list[tuple[int, str]] = []
    for time_index in range(thresholds.horizon):
        remaining = thresholds.horizon - time_index
        next_reach: dict[str, Fraction] = {}
        for cell_id in sorted(reach_upper):
            cell_mass = reach_upper[cell_id]
            if not cell_mass:
                continue
            reachable_pairs.append((time_index, cell_id))
            action_id = stage_maps[time_index][cell_id]
            state_rows = realizations[(cell_id, action_id)]
            documents = tuple(item.ambiguity.to_document() for item in state_rows)
            disagreement = any(
                document != documents[0] for document in documents[1:]
            )
            for item in state_rows:
                unknown = audit_module._validate_joint_simplex(item.ambiguity)
                known_external = dict(
                    item.ambiguity.known_successor_masses
                ).get(partial_model.external_boundary_id, Fraction(0))
                rows.append(
                    _CRow(
                        time_index,
                        remaining,
                        item.state_id,
                        cell_id,
                        action_id,
                        item.support_ground_row_ids,
                        item.observed_ground_row_ids,
                        item.missing_ground_row_ids,
                        cell_mass,
                        unknown,
                        known_external,
                        cell_mass * unknown,
                        (
                            cell_mass * known_external
                            if remaining > 1
                            else Fraction(0)
                        ),
                        disagreement,
                        item.ambiguity.is_singleton,
                    )
                )
            if remaining == 1:
                continue
            for destination in active_ids:
                destination_upper = max(
                    dict(item.ambiguity.known_successor_masses).get(
                        destination, Fraction(0)
                    )
                    + audit_module._validate_joint_simplex(item.ambiguity)
                    for item in state_rows
                )
                if destination_upper:
                    next_reach[destination] = min(
                        Fraction(1),
                        next_reach.get(destination, Fraction(0))
                        + cell_mass * destination_upper,
                    )
        reach_upper = next_reach
        if not reach_upper:
            break
    return _NeutralC(
        tuple(
            sorted(
                rows,
                key=lambda item: (
                    item.time_index,
                    item.cell_id,
                    item.state_id,
                    item.action_id,
                ),
            )
        ),
        tuple(sorted(set(reachable_pairs))),
    )


def _compute_d(
    partial_model: Any,
    thresholds: FrozenPartialAuditThresholdsV1,
    active_cells: Mapping[str, Any],
    realizations: Mapping[tuple[str, str], tuple[Any, ...]],
    stage_maps: Mapping[int, Mapping[str, str]],
    state_to_cell: Mapping[str, str],
    u_value: _NeutralU,
    p_value: _NeutralP,
) -> _NeutralD:
    initial_bounds = audit_module._build_initial_support_bounds(
        partial_model,
        thresholds,
        active_cells,
        realizations,
        stage_maps,
        state_to_cell,
        p_value.table,
    )
    return_upper = thresholds.return_bound_proof.return_upper
    unrestricted_upper = sum(
        (
            support.probability * u_value.initial_state_upper[support.state_id]
            for support in thresholds.initial_state_distribution
        ),
        Fraction(0),
    )
    root_reward_lower = sum(
        (
            support.probability
            * initial_bounds[support.state_id].reward_lower
            for support in thresholds.initial_state_distribution
        ),
        Fraction(0),
    )
    root_reward_upper = min(
        return_upper,
        sum(
            (
                support.probability
                * initial_bounds[support.state_id].reward_upper
                for support in thresholds.initial_state_distribution
            ),
            Fraction(0),
        ),
    )
    root_failure_lower = sum(
        (
            support.probability
            * initial_bounds[support.state_id].failure_lower
            for support in thresholds.initial_state_distribution
        ),
        Fraction(0),
    )
    root_failure_upper = sum(
        (
            support.probability
            * initial_bounds[support.state_id].failure_upper
            for support in thresholds.initial_state_distribution
        ),
        Fraction(0),
    )
    support_metrics = tuple(
        (
            support.state_id,
            state_to_cell[support.state_id],
            support.probability,
            u_value.initial_state_upper[support.state_id],
            initial_bounds[support.state_id].reward_lower,
            u_value.initial_state_upper[support.state_id]
            - initial_bounds[support.state_id].reward_lower,
            (
                u_value.initial_state_upper[support.state_id]
                - initial_bounds[support.state_id].reward_lower
            )
            / return_upper,
        )
        for support in thresholds.initial_state_distribution
    )
    raw_regret = unrestricted_upper - root_reward_lower
    return _NeutralD(
        initial_bounds,
        unrestricted_upper,
        root_reward_lower,
        root_reward_upper,
        root_failure_lower,
        root_failure_upper,
        raw_regret,
        raw_regret / return_upper,
        support_metrics,
    )


def _materialize_root(
    partial_model: Any,
    thresholds: FrozenPartialAuditThresholdsV1,
    plan: FrozenContingentAbstractPlanV1,
    u_value: _NeutralU,
    p_value: _NeutralP,
    c_value: _NeutralC,
    d_value: _NeutralD,
    e_value: _NeutralE,
    f_value: _NeutralF,
    g_value: _NeutralG,
) -> PartialSoundAuditResultV1:
    rows = tuple(
        PartialPolicyBoundRowV1(
            partial_model.model_id,
            thresholds.thresholds_id,
            plan.plan_id,
            row.time_index,
            row.remaining_horizon,
            row.cell_id,
            row.action_id,
            row.representative_state_ids,
            row.missing_ground_row_ids,
            row.reward_lower,
            row.reward_upper,
            row.failure_lower,
            row.failure_upper,
            row.max_shared_unknown_mass,
            row.external_boundary_possible,
            row.representative_disagreement,
        )
        for row in p_value.rows
    )
    unrestricted_rows = tuple(
        UnrestrictedGroundUpperRowV1(
            partial_model.model_id,
            thresholds.thresholds_id,
            row.time_index,
            row.remaining_horizon,
            row.state_id,
            row.cell_id,
            row.ground_row_id,
            row.ground_action_id,
            row.reward_upper,
        )
        for row in u_value.rows
    )
    obligations = tuple(
        StateActionTimeObligationV1(
            partial_model.model_id,
            thresholds.thresholds_id,
            plan.plan_id,
            row.time_index,
            row.remaining_horizon,
            row.state_id,
            row.cell_id,
            row.action_id,
            row.support_ground_row_ids,
            row.observed_ground_row_ids,
            row.missing_ground_row_ids,
            row.reachable_cell_mass_upper,
            row.shared_unknown_mass,
            row.known_external_successor_mass,
            row.reachable_unknown_mass_upper,
            row.reachable_external_continuation_mass_upper,
            row.representative_disagreement,
            row.realization_singleton,
        )
        for row in c_value.rows
    )
    support_rows = tuple(
        InitialSupportPointRegretRowV1(
            partial_model.model_id,
            thresholds.thresholds_id,
            plan.plan_id,
            thresholds.return_bound_proof.proof_id,
            state_id,
            cell_id,
            probability,
            unrestricted_upper,
            policy_lower,
            raw_regret,
            thresholds.return_bound_proof.return_upper,
            normalized_regret,
            thresholds.normalized_regret_tolerance,
            certified,
        )
        for (
            (
                state_id,
                cell_id,
                probability,
                unrestricted_upper,
                policy_lower,
                raw_regret,
                normalized_regret,
            ),
            certified,
        ) in zip(d_value.support_metrics, e_value.support_certified)
    )
    external_ids = tuple(
        sorted(obligations[index].obligation_id for index in g_value.external_row_indices)
    )
    return_upper = thresholds.return_bound_proof.return_upper
    bounds = PartialFixedPlanRobustBoundsV1(
        partial_model.model_id,
        thresholds.thresholds_id,
        plan.plan_id,
        thresholds.return_bound_proof.proof_id,
        rows,
        unrestricted_rows,
        support_rows,
        d_value.unrestricted_upper,
        d_value.root_reward_lower,
        d_value.root_reward_upper,
        d_value.root_failure_lower,
        d_value.root_failure_upper,
        d_value.raw_distribution_regret,
        d_value.normalized_distribution_regret,
        return_upper,
        thresholds.normalized_regret_tolerance,
        thresholds.risk_tolerance,
        e_value.reward_certified,
        f_value.risk_certified,
        g_value.coverage_certified,
        external_ids,
        len(c_value.reachable_pairs),
    )
    if bounds.certified:
        reachable_set = set(c_value.reachable_pairs)
        certificate = PartialFixedPlanCertificateV1(
            partial_model.model_id,
            thresholds.thresholds_id,
            plan.plan_id,
            bounds.bounds_id,
            bounds.return_bound_proof_id,
            tuple(sorted(item.obligation_id for item in obligations)),
            tuple(
                sorted(
                    item.bound_row_id
                    for item in rows
                    if (item.time_index, item.cell_id) in reachable_set
                )
            ),
            tuple(
                sorted(item.support_point_regret_row_id for item in support_rows)
            ),
            bounds.maximum_support_point_normalized_regret,
            bounds.normalized_regret_tolerance,
            bounds.policy_failure_upper,
            bounds.risk_tolerance,
            bounds.external_coverage_certified,
        )
        return PartialSoundAuditResultV1(
            partial_model.model_id,
            thresholds.thresholds_id,
            plan.plan_id,
            bounds,
            obligations,
            PartialAuditOutcome.CERTIFIED_FIXED_PLAN,
            certificate,
            None,
        )
    external_escape = tuple(
        item for item in obligations if item.obligation_id in set(external_ids)
    )
    unresolved = tuple(
        item
        for item in obligations
        if item.unresolved_mass_upper > 0 or item.representative_disagreement
    )
    if external_escape:
        earliest = min(item.time_index for item in external_escape)
        frontier_rows = tuple(
            item for item in external_escape if item.time_index == earliest
        )
        reason = FailedProofReason.EXTERNAL_COVERAGE_ESCAPE
    elif unresolved:
        earliest = min(item.time_index for item in unresolved)
        frontier_rows = tuple(
            item for item in unresolved if item.time_index == earliest
        )
        reason = FailedProofReason.UNRESOLVED_POLICY_PATH_DISTINCTION
    else:
        earliest = min(item.time_index for item in obligations)
        frontier_rows = tuple(
            item for item in obligations if item.time_index == earliest
        )
        reason = FailedProofReason.KNOWN_FIXED_PLAN_THRESHOLD_FAILURE
    frontier = PartialFailedProofFrontierV1(
        partial_model.model_id,
        thresholds.thresholds_id,
        plan.plan_id,
        bounds.bounds_id,
        earliest,
        thresholds.horizon - earliest,
        frontier_rows,
        sum((item.unresolved_mass_upper for item in frontier_rows), Fraction(0)),
        not bounds.reward_obligation_certified,
        not bounds.risk_obligation_certified,
        not bounds.external_coverage_certified,
        reason,
    )
    return PartialSoundAuditResultV1(
        partial_model.model_id,
        thresholds.thresholds_id,
        plan.plan_id,
        bounds,
        obligations,
        PartialAuditOutcome.FAILED_PROOF_FRONTIER,
        None,
        frontier,
    )



class _ProofRuntime:
    def __init__(
        self,
        observation_log: ObservationLogManifestV1,
        semantics_profile: DeterministicObservationProfileV1,
        observation_authority: PreregisteredObservationAuthorityV1,
        promotion: HeldOutFamilyPromotionBuildV1,
        semantics: IncrementalProofDAGSemanticsV1,
        scope: ProofCacheScope,
    ) -> None:
        self.observation_log = observation_log
        self.semantics_profile = semantics_profile
        self.observation_authority = observation_authority
        self.promotion = promotion
        self.semantics = semantics
        self.scope = scope
        self.entries: dict[str, IncrementalProofNodeEntryV1] = {}
        self.values: dict[str, Any] = {}
        self.catalogue: dict[str, IncrementalProofNodeEntryV1] = {}
        self.receipts: list[IncrementalProofRequestReceiptV1] = []

    def begin_context(self) -> None:
        if self.scope is ProofCacheScope.OCCURRENCE_RESET:
            self.entries.clear()
            self.values.clear()

    def _resolve(
        self,
        request_id: str,
        ordinal: int,
        key: IncrementalProofNodeKeyV1,
        builder: Callable[[], tuple[Any, Mapping[str, Any], int, str]],
    ) -> tuple[Any, IncrementalProofNodeResolutionV1]:
        key_id = key.node_key_id
        pre_cache_state_id = _cache_state_id(self.entries)
        entry = self.entries.get(key_id)
        if entry is None:
            value, result_document, row_count, result_semantics = builder()
            entry = IncrementalProofNodeEntryV1(
                key,
                _neutral_digest(key.kind, result_document),
                result_semantics,
                row_count,
            )
            self.entries[key_id] = entry
            self.values[key_id] = value
            self.catalogue[entry.entry_id] = entry
            outcome = ProofResolutionOutcome.COMPUTED
        else:
            value = self.values[key_id]
            outcome = ProofResolutionOutcome.REUSED
        post_cache_state_id = _cache_state_id(self.entries)
        resolution = IncrementalProofNodeResolutionV1(
            request_id,
            ordinal,
            key.kind,
            key_id,
            entry.entry_id,
            pre_cache_state_id,
            post_cache_state_id,
            outcome,
        )
        return value, resolution

    def resolve_request(
        self,
        context: IncrementalProofContextV1,
        thresholds: FrozenPartialAuditThresholdsV1,
        plan: FrozenContingentAbstractPlanV1,
        role: ProofRootRole,
        planner_result_id: str | None,
    ) -> tuple[PartialSoundAuditResultV1, IncrementalProofRequestReceiptV1]:
        if self.scope is ProofCacheScope.REQUEST_RESET:
            self.entries.clear()
            self.values.clear()
        sequence = len(self.receipts) + 1
        request_id = _request_id(
            sequence,
            context.context_id,
            role,
            plan.plan_id,
            planner_result_id,
        )
        partial_model = self.promotion.model
        (
            active_cells,
            realizations,
            stage_maps,
            state_to_cell,
        ) = audit_module._validate_inputs(partial_model, thresholds, plan)
        audit_module._validate_return_bound_authority(
            self.observation_log,
            self.semantics_profile,
            self.observation_authority,
            partial_model,
            thresholds,
        )
        reward_basis_id = _neutral_digest(
            ProofNodeKind.U,
            {
                "reward_weights": [
                    item.to_document() for item in thresholds.reward_weights
                ],
                "return_bound_proof_id": thresholds.return_bound_proof.proof_id,
                "horizon": thresholds.horizon,
            },
        )
        u_key = IncrementalProofNodeKeyV1(
            ProofNodeKind.U,
            self.semantics.semantics_id,
            _terms(
                arithmetic_kind=self.semantics.arithmetic_kind,
                horizon=str(thresholds.horizon),
                partial_model_id=partial_model.model_id,
                reward_basis_id=reward_basis_id,
                unrestricted_formula_id=self.semantics.unrestricted_upper_formula_id,
            ),
            (),
        )
        u_value, u_resolution = self._resolve(
            request_id,
            1,
            u_key,
            lambda: (
                (value := _compute_u(partial_model, thresholds, active_cells)),
                _u_document(value),
                0,
                "THRESHOLD_NEUTRAL_UNRESTRICTED_BELLMAN",
            ),
        )
        p_key = IncrementalProofNodeKeyV1(
            ProofNodeKind.P,
            self.semantics.semantics_id,
            _terms(
                contingent_plan_id=plan.plan_id,
                horizon=str(thresholds.horizon),
                partial_model_id=partial_model.model_id,
                robust_bellman_formula_id=self.semantics.robust_bellman_formula_id,
                reward_basis_id=reward_basis_id,
            ),
            (),
        )
        p_value, p_resolution = self._resolve(
            request_id,
            2,
            p_key,
            lambda: (
                (
                    value := _compute_p(
                        partial_model,
                        thresholds,
                        plan,
                        active_cells,
                        realizations,
                        stage_maps,
                    )
                ),
                _p_document(value),
                0,
                "THRESHOLD_NEUTRAL_FIXED_POLICY_BELLMAN",
            ),
        )
        c_key = IncrementalProofNodeKeyV1(
            ProofNodeKind.C,
            self.semantics.semantics_id,
            _terms(
                contingent_plan_id=plan.plan_id,
                horizon=str(thresholds.horizon),
                initial_state_id=context.initial_state_id,
                partial_model_id=partial_model.model_id,
                reachability_formula_id="partial-reachability-upper-v1",
            ),
            (),
        )
        c_value, c_resolution = self._resolve(
            request_id,
            3,
            c_key,
            lambda: (
                (
                    value := _compute_c(
                        partial_model,
                        thresholds,
                        realizations,
                        stage_maps,
                        state_to_cell,
                    )
                ),
                _c_document(value),
                0,
                "THRESHOLD_NEUTRAL_REACHABILITY_OBLIGATIONS",
            ),
        )
        d_key = IncrementalProofNodeKeyV1(
            ProofNodeKind.D,
            self.semantics.semantics_id,
            _terms(
                contingent_plan_id=plan.plan_id,
                initial_state_id=context.initial_state_id,
                partial_model_id=partial_model.model_id,
                return_bound_proof_id=thresholds.return_bound_proof.proof_id,
                root_metrics_formula_id="partial-support-root-metrics-v1",
            ),
            tuple(sorted((u_key.node_key_id, p_key.node_key_id, c_key.node_key_id))),
        )
        d_value, d_resolution = self._resolve(
            request_id,
            4,
            d_key,
            lambda: (
                (
                    value := _compute_d(
                        partial_model,
                        thresholds,
                        active_cells,
                        realizations,
                        stage_maps,
                        state_to_cell,
                        u_value,
                        p_value,
                    )
                ),
                _d_document(value),
                0,
                "THRESHOLD_NEUTRAL_SUPPORT_AND_ROOT_METRICS",
            ),
        )
        e_key = IncrementalProofNodeKeyV1(
            ProofNodeKind.E,
            self.semantics.semantics_id,
            _terms(
                normalized_regret_tolerance=_fraction_text(
                    thresholds.normalized_regret_tolerance
                )
            ),
            (d_key.node_key_id,),
        )
        e_value, e_resolution = self._resolve(
            request_id,
            5,
            e_key,
            lambda: (
                (
                    value := _NeutralE(
                        tuple(
                            item[-1] <= thresholds.normalized_regret_tolerance
                            for item in d_value.support_metrics
                        ),
                        all(
                            item[-1] <= thresholds.normalized_regret_tolerance
                            for item in d_value.support_metrics
                        ),
                    )
                ),
                {
                    "support_certified": list(value.support_certified),
                    "reward_certified": value.reward_certified,
                    "normalized_regret_tolerance": _fdoc(
                        thresholds.normalized_regret_tolerance
                    ),
                },
                0,
                "REGRET_THRESHOLD_VERDICT",
            ),
        )
        f_key = IncrementalProofNodeKeyV1(
            ProofNodeKind.F,
            self.semantics.semantics_id,
            _terms(risk_tolerance=_fraction_text(thresholds.risk_tolerance)),
            (d_key.node_key_id,),
        )
        f_value, f_resolution = self._resolve(
            request_id,
            6,
            f_key,
            lambda: (
                (
                    value := _NeutralF(
                        d_value.root_failure_upper <= thresholds.risk_tolerance
                    )
                ),
                {
                    "risk_certified": value.risk_certified,
                    "risk_tolerance": _fdoc(thresholds.risk_tolerance),
                },
                0,
                "RISK_THRESHOLD_VERDICT",
            ),
        )
        g_key = IncrementalProofNodeKeyV1(
            ProofNodeKind.G,
            self.semantics.semantics_id,
            _terms(coverage_formula_id="partial-external-coverage-v1"),
            (c_key.node_key_id,),
        )
        g_value, g_resolution = self._resolve(
            request_id,
            7,
            g_key,
            lambda: (
                (
                    value := _NeutralG(
                        tuple(
                            index
                            for index, row in enumerate(c_value.rows)
                            if row.remaining_horizon > 1
                            and (
                                row.reachable_external_continuation_mass_upper > 0
                                or row.reachable_unknown_mass_upper > 0
                            )
                        ),
                        not any(
                            row.remaining_horizon > 1
                            and (
                                row.reachable_external_continuation_mass_upper > 0
                                or row.reachable_unknown_mass_upper > 0
                            )
                            for row in c_value.rows
                        ),
                    )
                ),
                {
                    "external_row_indices": list(value.external_row_indices),
                    "coverage_certified": value.coverage_certified,
                },
                0,
                "EXTERNAL_COVERAGE_VERDICT",
            ),
        )
        r_key = IncrementalProofNodeKeyV1(
            ProofNodeKind.R,
            self.semantics.semantics_id,
            _terms(
                audit_role=role.value,
                context_id=context.context_id,
                contingent_plan_id=plan.plan_id,
                planner_result_id=planner_result_id or "NOT_APPLICABLE",
                proof_request_id=request_id,
                thresholds_id=thresholds.thresholds_id,
            ),
            tuple(
                sorted(
                    (
                        u_key.node_key_id,
                        p_key.node_key_id,
                        c_key.node_key_id,
                        d_key.node_key_id,
                        e_key.node_key_id,
                        f_key.node_key_id,
                        g_key.node_key_id,
                    )
                )
            ),
        )

        def build_root() -> tuple[
            PartialSoundAuditResultV1, Mapping[str, Any], int, str
        ]:
            result = _materialize_root(
                partial_model,
                thresholds,
                plan,
                u_value,
                p_value,
                c_value,
                d_value,
                e_value,
                f_value,
                g_value,
            )
            row_count = (
                len(result.robust_bounds.rows)
                + len(result.robust_bounds.unrestricted_rows)
                + len(result.robust_bounds.support_point_regret_rows)
                + len(result.proof_obligations)
            )
            return (
                result,
                {"legacy_v1_audit": result.to_document()},
                row_count,
                f"LEGACY_V1_AUDIT:{result.result_id}",
            )

        audit_result, r_resolution = self._resolve(
            request_id, 8, r_key, build_root
        )
        receipt = IncrementalProofRequestReceiptV1(
            sequence,
            context.context_id,
            role,
            plan.plan_id,
            planner_result_id,
            (
                u_resolution,
                p_resolution,
                c_resolution,
                d_resolution,
                e_resolution,
                f_resolution,
                g_resolution,
                r_resolution,
            ),
            audit_result.result_id,
        )
        self.receipts.append(receipt)
        return audit_result, receipt


def _registered_contexts(
    promotion: HeldOutFamilyPromotionBuildV1,
) -> tuple[IncrementalProofContextV1, ...]:
    query_by_index = {
        item.query_index: item for item in promotion.protocol.target_queries
    }
    contexts = tuple(
        IncrementalProofContextV1(
            context_index,
            query_by_index[query_index].query_id,
            query_index,
            query_by_index[query_index].initial_state.state_id,
            regret,
            risk,
        )
        for context_index, (query_index, regret, risk) in enumerate(
            CONTEXT_SEQUENCE, start=1
        )
    )
    expected_state_ids = tuple(
        query_by_index[index].initial_state.state_id for index in (1, 2, 3)
    )
    if expected_state_ids != tuple(
        family_module._state_observation(state).state_id
        for state in FAMILY_TARGET_STATES
    ):
        raise IncrementalProofDAGInvariantViolation(
            "incremental contexts differ from the registered family targets"
        )
    return contexts



def _registered_protocol(
    promotion: HeldOutFamilyPromotionBuildV1,
) -> IncrementalProofDAGProtocolV1:
    return IncrementalProofDAGProtocolV1(
        promotion.protocol.protocol_id,
        _registered_contexts(promotion),
    )

def _threshold_binding(
    promotion: HeldOutFamilyPromotionBuildV1,
    context: IncrementalProofContextV1,
) -> IncrementalThresholdBindingV1:
    base_query = promotion.protocol.target_queries[context.query_index - 1]
    proof = canonical_lmb_n6_return_bound_proof_v1()
    thresholds = FrozenPartialAuditThresholdsV1(
        promotion.model.model_id,
        1,
        (InitialStateMassV1(context.initial_state_id, Fraction(1)),),
        base_query.reward_weights,
        context.normalized_regret_tolerance,
        context.risk_tolerance,
        proof,
    )
    return IncrementalThresholdBindingV1(
        promotion.result_id,
        promotion.protocol.protocol_id,
        context,
        promotion.model.model_id,
        thresholds,
    )


def _run_context(
    runtime: _ProofRuntime,
    context: IncrementalProofContextV1,
) -> IncrementalProofContextExecutionV1:
    runtime.begin_context()
    promotion = runtime.promotion
    binding = _threshold_binding(promotion, context)
    thresholds = binding.thresholds
    _, domains = _planner_context(
        runtime.observation_log,
        runtime.semantics_profile,
        runtime.observation_authority,
        promotion.model,
        thresholds,
    )
    stage_count = 1
    for domain in domains:
        stage_count *= len(domain.semantic_action_ids)
    schedules = _stage_assignments(domains)
    plans: dict[str, FrozenContingentAbstractPlanV1] = {}
    audits: dict[str, PartialSoundAuditResultV1] = {}
    receipts: list[IncrementalProofRequestReceiptV1] = []
    summaries = []
    for schedule in product(schedules, repeat=thresholds.horizon):
        plan = FrozenContingentAbstractPlanV1(
            promotion.model.model_id,
            thresholds.horizon,
            tuple(
                ContingentPlanStageV1(time_index, assignments)
                for time_index, assignments in enumerate(schedule)
            ),
        )
        audit_result, receipt = runtime.resolve_request(
            context,
            thresholds,
            plan,
            ProofRootRole.CANDIDATE_RANKING_AUDIT,
            None,
        )
        plans[plan.plan_id] = plan
        audits[plan.plan_id] = audit_result
        summaries.append(_candidate_summary(thresholds, plan, audit_result))
        receipts.append(receipt)
    if len(plans) != 2:
        raise IncrementalProofDAGInvariantViolation(
            "incremental proof profile requires exactly two H1 candidates"
        )
    summaries_tuple = tuple(
        sorted(summaries, key=lambda item: item.contingent_plan_id)
    )
    mode, provisional = _selected_summary(summaries_tuple)
    numeric_key = family_module._selection_numeric_key(mode, provisional)
    tied = tuple(
        item
        for item in summaries_tuple
        if family_module._selection_numeric_key(mode, item) == numeric_key
    )
    selected = min(
        tied,
        key=lambda item: (
            family_module._semantic_plan_key(
                promotion.model, plans[item.contingent_plan_id]
            ),
            item.contingent_plan_id,
        ),
    )
    selected_plan = plans[selected.contingent_plan_id]
    proposal = HeldOutPlanProposalV1(
        promotion.result_id,
        promotion.protocol.protocol_id,
        context.context_id,
        promotion.model.model_id,
        binding.binding_id,
        thresholds.thresholds_id,
        domains,
        stage_count,
        stage_count,
        summaries_tuple,
        mode,
        selected_plan,
        family_module._semantic_plan_key(promotion.model, selected_plan),
        len(summaries_tuple),
    )
    selected_result, selected_receipt = runtime.resolve_request(
        context,
        thresholds,
        selected_plan,
        ProofRootRole.INDEPENDENT_SELECTED_PLAN_CERTIFICATE,
        proposal.result_id,
    )
    receipts.append(selected_receipt)
    selected_audit = HeldOutPlanAuditV1(
        promotion.result_id,
        promotion.protocol.protocol_id,
        context.context_id,
        promotion.model.model_id,
        binding.binding_id,
        proposal.result_id,
        selected_plan.plan_id,
        selected_result,
    )
    return IncrementalProofContextExecutionV1(
        context,
        binding,
        proposal,
        tuple(audits[item.contingent_plan_id] for item in summaries_tuple),
        selected_audit,
        tuple(item.receipt_id for item in receipts),
    )


def _work_from_receipts(
    scope: ProofCacheScope,
    receipts: tuple[IncrementalProofRequestReceiptV1, ...],
) -> ProofDAGWorkV1:
    return ProofDAGWorkV1(
        scope,
        7,
        len(receipts),
        sum(len(item.resolutions) for item in receipts),
        tuple(
            ProofKindCountV1(
                kind,
                sum(
                    resolution.kind is kind
                    and resolution.outcome is ProofResolutionOutcome.COMPUTED
                    for receipt in receipts
                    for resolution in receipt.resolutions
                ),
                sum(
                    resolution.kind is kind
                    and resolution.outcome is ProofResolutionOutcome.REUSED
                    for receipt in receipts
                    for resolution in receipt.resolutions
                ),
            )
            for kind in ProofNodeKind
        ),
    )


def _prefixes(
    scope: ProofCacheScope,
    contexts: tuple[IncrementalProofContextExecutionV1, ...],
    receipts: tuple[IncrementalProofRequestReceiptV1, ...],
) -> tuple[ProofDAGPrefixV1, ...]:
    result = []
    for length in range(1, len(contexts) + 1):
        selected = receipts[: 3 * length]
        computed = sum(
            resolution.outcome is ProofResolutionOutcome.COMPUTED
            for receipt in selected
            for resolution in receipt.resolutions
        )
        reused = sum(
            resolution.outcome is ProofResolutionOutcome.REUSED
            for receipt in selected
            for resolution in receipt.resolutions
        )
        result.append(
            ProofDAGPrefixV1(
                scope,
                length,
                tuple(item.context.context_id for item in contexts[:length]),
                computed,
                reused,
                computed + reused,
            )
        )
    return tuple(result)


def _expected_global_new_counts(index: int) -> dict[ProofNodeKind, int]:
    if index == 1:
        values = (1, 2, 2, 2, 2, 2, 2, 3)
    elif index in (2, 5):
        values = (0, 0, 2, 2, 2, 2, 2, 3)
    elif index in (3, 6):
        values = (0, 0, 0, 0, 2, 0, 0, 3)
    else:
        values = (0, 0, 0, 0, 0, 2, 0, 3)
    return dict(zip(ProofNodeKind, values))


def _change_closures(
    scope: ProofCacheScope,
    contexts: tuple[IncrementalProofContextExecutionV1, ...],
    receipts: tuple[IncrementalProofRequestReceiptV1, ...],
) -> tuple[ContextChangeClosureV1, ...]:
    result = []
    for index, context_execution in enumerate(contexts, start=1):
        group = receipts[3 * (index - 1) : 3 * index]
        actual = {
            kind: sum(
                resolution.kind is kind
                and resolution.outcome is ProofResolutionOutcome.COMPUTED
                for receipt in group
                for resolution in receipt.resolutions
            )
            for kind in ProofNodeKind
        }
        expected = (
            _expected_global_new_counts(index)
            if scope is ProofCacheScope.GLOBAL
            else actual
        )
        counts_expected = tuple(
            ProofKindCountV1(kind, expected[kind], 0) for kind in ProofNodeKind
        )
        counts_actual = tuple(
            ProofKindCountV1(kind, actual[kind], 0) for kind in ProofNodeKind
        )
        facets = (
            ("INITIAL_CONTEXT",)
            if index == 1
            else (
                ("INITIAL_DISTRIBUTION",)
                if index in (2, 5)
                else (
                    ("NORMALIZED_REGRET_TOLERANCE",)
                    if index in (3, 6)
                    else ("RISK_TOLERANCE",)
                )
            )
        )
        result.append(
            ContextChangeClosureV1(
                index,
                contexts[index - 2].context.context_id if index > 1 else None,
                context_execution.context.context_id,
                facets,
                counts_expected,
                counts_actual,
            )
        )
    return tuple(result)


def _validate_execution_trace(
    execution: IncrementalProofDAGFamilyExecutionV1,
) -> None:
    if tuple(item.context.context_index for item in execution.contexts) != tuple(
        range(1, 8)
    ):
        raise IncrementalProofDAGInvariantViolation(
            "incremental execution context order changed"
        )
    if tuple(item.request_sequence for item in execution.use_receipts) != tuple(
        range(1, 22)
    ):
        raise IncrementalProofDAGInvariantViolation(
            "incremental execution request sequence is not contiguous"
        )
    catalogue = {item.entry_id: item for item in execution.entry_catalogue}
    if (
        len(catalogue) != 62
        or len({item.key.node_key_id for item in catalogue.values()}) != 62
        or tuple(item.entry_id for item in execution.entry_catalogue)
        != tuple(sorted(catalogue))
    ):
        raise IncrementalProofDAGInvariantViolation(
            "incremental execution entry catalogue is incomplete or unsorted"
        )
    expected_final_size = {
        ProofCacheScope.REQUEST_RESET: 8,
        ProofCacheScope.OCCURRENCE_RESET: 16,
        ProofCacheScope.GLOBAL: 62,
    }[execution.cache_scope]
    if len(execution.final_cache.entries) != expected_final_size:
        raise IncrementalProofDAGInvariantViolation(
            "incremental final cache size differs from its reset scope"
        )
    context_by_id = {
        item.context.context_id: item for item in execution.contexts
    }
    for context_index, context_execution in enumerate(execution.contexts):
        group = execution.use_receipts[3 * context_index : 3 * context_index + 3]
        if context_execution.request_receipt_ids != tuple(
            item.receipt_id for item in group
        ):
            raise IncrementalProofDAGInvariantViolation(
                "context execution does not bind its three proof requests"
            )

    replay_state: dict[str, IncrementalProofNodeEntryV1] = {}
    previous_context_id: str | None = None
    for receipt in execution.use_receipts:
        if execution.cache_scope is ProofCacheScope.REQUEST_RESET:
            replay_state.clear()
        elif (
            execution.cache_scope is ProofCacheScope.OCCURRENCE_RESET
            and receipt.context_id != previous_context_id
        ):
            replay_state.clear()
        previous_context_id = receipt.context_id
        context_execution = context_by_id.get(receipt.context_id)
        if context_execution is None:
            raise IncrementalProofDAGInvariantViolation(
                "proof request names an unregistered context"
            )
        thresholds = context_execution.threshold_binding.thresholds
        if (
            tuple(item.ordinal_in_request for item in receipt.resolutions)
            != tuple(range(1, 9))
            or any(
                resolution.request_id != receipt.request_id
                for resolution in receipt.resolutions
            )
            or receipt.resolutions[0].pre_cache_state_id
            != _cache_state_id(replay_state)
        ):
            raise IncrementalProofDAGInvariantViolation(
                "proof request ordering, identity, or reset state is invalid"
            )

        resolved_keys: dict[ProofNodeKind, str] = {}
        resolved_entries: dict[ProofNodeKind, IncrementalProofNodeEntryV1] = {}
        for resolution in receipt.resolutions:
            entry = catalogue.get(resolution.entry_id)
            if (
                entry is None
                or entry.key.node_key_id != resolution.node_key_id
                or entry.key.kind is not resolution.kind
                or resolution.pre_cache_state_id != _cache_state_id(replay_state)
            ):
                raise IncrementalProofDAGInvariantViolation(
                    "node resolution key, entry, or pre-cache state is invalid"
                )
            if resolution.outcome is ProofResolutionOutcome.COMPUTED:
                if resolution.node_key_id in replay_state:
                    raise IncrementalProofDAGInvariantViolation(
                        "computed node overwrites an append-only cache entry"
                    )
                replay_state[resolution.node_key_id] = entry
            else:
                existing = replay_state.get(resolution.node_key_id)
                if existing is None or existing.entry_id != resolution.entry_id:
                    raise IncrementalProofDAGInvariantViolation(
                        "reused node is absent from the exact pre-cache state"
                    )
            if resolution.post_cache_state_id != _cache_state_id(replay_state):
                raise IncrementalProofDAGInvariantViolation(
                    "proof resolution post-cache state breaks the append-only chain"
                )
            resolved_keys[resolution.kind] = resolution.node_key_id
            resolved_entries[resolution.kind] = entry

        expected_parents = {
            ProofNodeKind.U: (),
            ProofNodeKind.P: (),
            ProofNodeKind.C: (),
            ProofNodeKind.D: tuple(
                sorted(
                    (
                        resolved_keys[ProofNodeKind.U],
                        resolved_keys[ProofNodeKind.P],
                        resolved_keys[ProofNodeKind.C],
                    )
                )
            ),
            ProofNodeKind.E: (resolved_keys[ProofNodeKind.D],),
            ProofNodeKind.F: (resolved_keys[ProofNodeKind.D],),
            ProofNodeKind.G: (resolved_keys[ProofNodeKind.C],),
            ProofNodeKind.R: tuple(
                sorted(
                    resolved_keys[kind]
                    for kind in ProofNodeKind
                    if kind is not ProofNodeKind.R
                )
            ),
        }
        if any(
            resolved_entries[kind].key.dependency_node_ids
            != expected_parents[kind]
            for kind in ProofNodeKind
        ):
            raise IncrementalProofDAGInvariantViolation(
                "proof request has a missing, extra, stale, or cyclic DAG edge"
            )
        reward_basis_id = _neutral_digest(
            ProofNodeKind.U,
            {
                "reward_weights": [
                    item.to_document() for item in thresholds.reward_weights
                ],
                "return_bound_proof_id": thresholds.return_bound_proof.proof_id,
                "horizon": thresholds.horizon,
            },
        )
        expected_identity_by_kind = {
            ProofNodeKind.U: dict(
                _terms(
                    arithmetic_kind=execution.semantics.arithmetic_kind,
                    horizon=str(thresholds.horizon),
                    partial_model_id=(
                        context_execution.threshold_binding.promoted_model_id
                    ),
                    reward_basis_id=reward_basis_id,
                    unrestricted_formula_id=(
                        execution.semantics.unrestricted_upper_formula_id
                    ),
                )
            ),
            ProofNodeKind.P: dict(
                _terms(
                    contingent_plan_id=receipt.contingent_plan_id,
                    horizon=str(thresholds.horizon),
                    partial_model_id=(
                        context_execution.threshold_binding.promoted_model_id
                    ),
                    robust_bellman_formula_id=(
                        execution.semantics.robust_bellman_formula_id
                    ),
                    reward_basis_id=reward_basis_id,
                )
            ),
            ProofNodeKind.C: dict(
                _terms(
                    contingent_plan_id=receipt.contingent_plan_id,
                    horizon=str(thresholds.horizon),
                    initial_state_id=context_execution.context.initial_state_id,
                    partial_model_id=(
                        context_execution.threshold_binding.promoted_model_id
                    ),
                    reachability_formula_id="partial-reachability-upper-v1",
                )
            ),
            ProofNodeKind.D: dict(
                _terms(
                    contingent_plan_id=receipt.contingent_plan_id,
                    initial_state_id=context_execution.context.initial_state_id,
                    partial_model_id=(
                        context_execution.threshold_binding.promoted_model_id
                    ),
                    return_bound_proof_id=(
                        thresholds.return_bound_proof.proof_id
                    ),
                    root_metrics_formula_id="partial-support-root-metrics-v1",
                )
            ),
            ProofNodeKind.E: dict(
                _terms(
                    normalized_regret_tolerance=_fraction_text(
                        thresholds.normalized_regret_tolerance
                    )
                )
            ),
            ProofNodeKind.F: dict(
                _terms(
                    risk_tolerance=_fraction_text(thresholds.risk_tolerance)
                )
            ),
            ProofNodeKind.G: dict(
                _terms(coverage_formula_id="partial-external-coverage-v1")
            ),
            ProofNodeKind.R: dict(
                _terms(
                    audit_role=receipt.audit_role.value,
                    context_id=receipt.context_id,
                    contingent_plan_id=receipt.contingent_plan_id,
                    planner_result_id=receipt.planner_result_id
                    or "NOT_APPLICABLE",
                    proof_request_id=receipt.request_id,
                    thresholds_id=thresholds.thresholds_id,
                )
            ),
        }
        identity_by_kind = {
            kind: dict(resolved_entries[kind].key.identity_terms)
            for kind in ProofNodeKind
        }
        if (
            any(
                resolved_entries[kind].key.semantics_id
                != execution.semantics.semantics_id
                for kind in ProofNodeKind
            )
            or identity_by_kind != expected_identity_by_kind
        ):
            raise IncrementalProofDAGInvariantViolation(
                "proof-node facet identity is stale or transplanted"
            )
        expected_result_semantics = {
            ProofNodeKind.U: "THRESHOLD_NEUTRAL_UNRESTRICTED_BELLMAN",
            ProofNodeKind.P: "THRESHOLD_NEUTRAL_FIXED_POLICY_BELLMAN",
            ProofNodeKind.C: "THRESHOLD_NEUTRAL_REACHABILITY_OBLIGATIONS",
            ProofNodeKind.D: "THRESHOLD_NEUTRAL_SUPPORT_AND_ROOT_METRICS",
            ProofNodeKind.E: "REGRET_THRESHOLD_VERDICT",
            ProofNodeKind.F: "RISK_THRESHOLD_VERDICT",
            ProofNodeKind.G: "EXTERNAL_COVERAGE_VERDICT",
        }
        if any(
            resolved_entries[kind].result_semantics
            != expected_result_semantics[kind]
            for kind in expected_result_semantics
        ):
            raise IncrementalProofDAGInvariantViolation(
                "neutral node result semantics are stale or cross-kind"
            )
        root_entry = resolved_entries[ProofNodeKind.R]
        if (
            root_entry.result_semantics
            != f"LEGACY_V1_AUDIT:{receipt.audit_result_id}"
            or root_entry.threshold_bound_v1_row_count <= 0
            or any(
                resolved_entries[kind].threshold_bound_v1_row_count != 0
                for kind in ProofNodeKind
                if kind is not ProofNodeKind.R
            )
        ):
            raise IncrementalProofDAGInvariantViolation(
                "legacy V1 rows leaked below R or root result binding changed"
            )

    replayed_final_cache = IncrementalProofCacheV1(
        execution.cache_scope,
        tuple(sorted(replay_state.values(), key=lambda item: item.key.node_key_id)),
    )
    if replayed_final_cache.to_document() != execution.final_cache.to_document():
        raise IncrementalProofDAGInvariantViolation(
            "final proof cache differs from the replayed append-only state"
        )
    recomputed_work = _work_from_receipts(
        execution.cache_scope, execution.use_receipts
    )
    if recomputed_work.to_document() != execution.aggregate_work.to_document():
        raise IncrementalProofDAGInvariantViolation(
            "incremental execution work is not replayable from receipts"
        )
    expected_prefixes = _prefixes(
        execution.cache_scope, execution.contexts, execution.use_receipts
    )
    if tuple(item.to_document() for item in expected_prefixes) != tuple(
        item.to_document() for item in execution.prefixes
    ):
        raise IncrementalProofDAGInvariantViolation(
            "incremental execution prefix curve is invalid"
        )
    expected_closures = _change_closures(
        execution.cache_scope, execution.contexts, execution.use_receipts
    )
    if tuple(item.to_document() for item in expected_closures) != tuple(
        item.to_document() for item in execution.change_closures
    ):
        raise IncrementalProofDAGInvariantViolation(
            "incremental execution change-set closure is invalid"
        )

def _run_incremental_arm(
    observation_log: ObservationLogManifestV1,
    semantics_profile: DeterministicObservationProfileV1,
    observation_authority: PreregisteredObservationAuthorityV1,
    promotion: HeldOutFamilyPromotionBuildV1,
    scope: ProofCacheScope,
) -> IncrementalProofDAGFamilyExecutionV1:
    if type(promotion) is not HeldOutFamilyPromotionBuildV1:
        raise IncrementalProofDAGInvariantViolation(
            "incremental proof runner rejects substituted V5 promotions"
        )
    semantics = incremental_proof_dag_semantics_v1()
    runtime = _ProofRuntime(
        observation_log,
        semantics_profile,
        observation_authority,
        promotion,
        semantics,
        scope,
    )
    protocol = _registered_protocol(promotion)
    contexts = tuple(
        _run_context(runtime, context)
        for context in protocol.ordered_contexts
    )
    receipts = tuple(runtime.receipts)
    catalogue = tuple(sorted(runtime.catalogue.values(), key=lambda x: x.entry_id))
    final_cache = IncrementalProofCacheV1(
        scope,
        tuple(sorted(runtime.entries.values(), key=lambda x: x.key.node_key_id)),
    )
    work = _work_from_receipts(scope, receipts)
    raw = IncrementalProofDAGFamilyExecutionV1(
        semantics,
        scope,
        promotion.result_id,
        promotion.protocol.protocol_id,
        protocol,
        contexts,
        receipts,
        catalogue,
        final_cache,
        work,
        _prefixes(scope, contexts, receipts),
        _change_closures(scope, contexts, receipts),
        True,
        _INCREMENTAL_EXECUTION_AUTHORITY,
    )
    return bind_runtime_authority_v1(
        raw,
        issuer=_INCREMENTAL_EXECUTION_AUTHORITY,
    )


def run_identity_bound_incremental_proof_dag_family_v1(
    observation_log: ObservationLogManifestV1,
    semantics_profile: DeterministicObservationProfileV1,
    observation_authority: PreregisteredObservationAuthorityV1,
    promotion: HeldOutFamilyPromotionBuildV1,
) -> IncrementalProofDAGFamilyExecutionV1:
    """Run the production global-cache incremental proof DAG.

    This target-blind consumer has exactly the four frozen arguments.  It has no
    kernel, direct optimizer, source refinement, or control-arm input.
    """

    return _run_incremental_arm(
        observation_log,
        semantics_profile,
        observation_authority,
        promotion,
        ProofCacheScope.GLOBAL,
    )



@dataclass(frozen=True, slots=True)
class LegacyAuditMatchV1:
    request_receipt_id: str
    context_id: str
    audit_role: ProofRootRole
    contingent_plan_id: str
    incremental_audit_result_id: str
    legacy_audit_result_id: str
    exact_document_match: bool = True
    evaluation_lane_only: bool = True
    monolithic_auditor_call_count: int = 1

    def __post_init__(self) -> None:
        for name in (
            "request_receipt_id",
            "context_id",
            "contingent_plan_id",
            "incremental_audit_result_id",
            "legacy_audit_result_id",
        ):
            _cid(getattr(self, name), f"legacy audit match {name}")
        if (
            type(self.audit_role) is not ProofRootRole
            or self.incremental_audit_result_id != self.legacy_audit_result_id
            or self.exact_document_match is not True
            or self.evaluation_lane_only is not True
            or self.monolithic_auditor_call_count != 1
        ):
            raise IncrementalProofDAGInvariantViolation(
                "legacy audit match is not exact or leaked into production"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.incremental_proof_legacy_audit_match.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "request_receipt_id": self.request_receipt_id,
            "context_id": self.context_id,
            "audit_role": self.audit_role.value,
            "contingent_plan_id": self.contingent_plan_id,
            "incremental_audit_result_id": self.incremental_audit_result_id,
            "legacy_audit_result_id": self.legacy_audit_result_id,
            "exact_document_match": self.exact_document_match,
            "evaluation_lane_only": self.evaluation_lane_only,
            "monolithic_auditor_call_count": self.monolithic_auditor_call_count,
        }

    @property
    def match_id(self) -> str:
        return _content_id("legacy_match", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "match_id": self.match_id}


@dataclass(frozen=True, slots=True)
class IncrementalProofDAGControlResultV1:
    family_promotion_result_id: str
    request_reset_execution: IncrementalProofDAGFamilyExecutionV1
    occurrence_reset_execution: IncrementalProofDAGFamilyExecutionV1
    global_execution: IncrementalProofDAGFamilyExecutionV1
    legacy_audit_matches: tuple[LegacyAuditMatchV1, ...]
    evaluation_monolithic_auditor_call_count: int
    status: str = SUCCESS_STATUS
    identity_bound_incremental_proof_claimed: bool = False
    registered_h1_changed_query_incremental_proof_claimed: bool = True
    cross_identity_unaffected_obligation_reuse_claimed: bool = False
    general_cross_identity_incremental_proof_claimed: bool = False
    higher_horizon_incremental_bellman_claimed: bool = False
    reward_or_model_epoch_incremental_claimed: bool = False
    persistent_cache_claimed: bool = False
    sample_tax_operator_claimed: bool = False
    total_work_or_wallclock_reduction_claimed: bool = False
    sample_efficiency_claimed: bool = False
    learned_or_partial_dynamics_claimed: bool = False
    cross_domain_generalization_claimed: bool = False
    official_execution_allowed: bool = False
    official_scalar_cost: None = None
    official_N_break_even: None = None
    workload_economics_gate: str = "WORKLOAD_ECONOMICS_GATE_NOT_RUN"
    counter_completeness_gate: str = "COUNTER_COMPLETENESS_GATE_NOT_RUN"
    sample_efficiency_gate: str = "SAMPLE_EFFICIENCY_GATE_NOT_RUN"

    def __post_init__(self) -> None:
        _cid(self.family_promotion_result_id, "control family promotion")
        for execution, scope in (
            (self.request_reset_execution, ProofCacheScope.REQUEST_RESET),
            (self.occurrence_reset_execution, ProofCacheScope.OCCURRENCE_RESET),
            (self.global_execution, ProofCacheScope.GLOBAL),
        ):
            require_incremental_proof_dag_family_execution_v1(execution)
            if (
                execution.cache_scope is not scope
                or execution.family_promotion_result_id
                != self.family_promotion_result_id
            ):
                raise IncrementalProofDAGInvariantViolation(
                    "control arm scope or promotion identity changed"
                )
        if (
            type(self.legacy_audit_matches) is not tuple
            or len(self.legacy_audit_matches) != 21
            or any(
                type(item) is not LegacyAuditMatchV1
                for item in self.legacy_audit_matches
            )
        ):
            raise IncrementalProofDAGInvariantViolation(
                "control requires 21 typed legacy audit matches"
            )
        _integer(
            self.evaluation_monolithic_auditor_call_count,
            "evaluation monolithic audit count",
        )
        if (
            self.evaluation_monolithic_auditor_call_count != 21
            or self.status != SUCCESS_STATUS
            or self.identity_bound_incremental_proof_claimed is not False
            or self.registered_h1_changed_query_incremental_proof_claimed
            is not True
            or self.cross_identity_unaffected_obligation_reuse_claimed is not False
            or self.general_cross_identity_incremental_proof_claimed is not False
            or self.higher_horizon_incremental_bellman_claimed is not False
            or self.reward_or_model_epoch_incremental_claimed is not False
            or self.persistent_cache_claimed is not False
            or self.sample_tax_operator_claimed is not False
            or self.total_work_or_wallclock_reduction_claimed is not False
            or self.sample_efficiency_claimed is not False
            or self.learned_or_partial_dynamics_claimed is not False
            or self.cross_domain_generalization_claimed is not False
            or self.official_execution_allowed is not False
            or self.official_scalar_cost is not None
            or self.official_N_break_even is not None
            or self.workload_economics_gate != "WORKLOAD_ECONOMICS_GATE_NOT_RUN"
            or self.counter_completeness_gate != "COUNTER_COMPLETENESS_GATE_NOT_RUN"
            or self.sample_efficiency_gate != "SAMPLE_EFFICIENCY_GATE_NOT_RUN"
        ):
            raise IncrementalProofDAGInvariantViolation(
                "incremental proof claim boundary or locked Gate fields changed"
            )
        _validate_control_equivalence(self)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.incremental_proof_dag_control_result.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "family_promotion_result_id": self.family_promotion_result_id,
            "request_reset_execution": self.request_reset_execution.to_document(),
            "occurrence_reset_execution": (
                self.occurrence_reset_execution.to_document()
            ),
            "global_execution": self.global_execution.to_document(),
            "legacy_audit_matches": [
                item.to_document() for item in self.legacy_audit_matches
            ],
            "evaluation_monolithic_auditor_call_count": (
                self.evaluation_monolithic_auditor_call_count
            ),
            "status": self.status,
            "identity_bound_incremental_proof_claimed": (
                self.identity_bound_incremental_proof_claimed
            ),
            "registered_h1_changed_query_incremental_proof_claimed": (
                self.registered_h1_changed_query_incremental_proof_claimed
            ),
            "cross_identity_unaffected_obligation_reuse_claimed": (
                self.cross_identity_unaffected_obligation_reuse_claimed
            ),
            "general_cross_identity_incremental_proof_claimed": (
                self.general_cross_identity_incremental_proof_claimed
            ),
            "higher_horizon_incremental_bellman_claimed": (
                self.higher_horizon_incremental_bellman_claimed
            ),
            "reward_or_model_epoch_incremental_claimed": (
                self.reward_or_model_epoch_incremental_claimed
            ),
            "persistent_cache_claimed": self.persistent_cache_claimed,
            "sample_tax_operator_claimed": self.sample_tax_operator_claimed,
            "total_work_or_wallclock_reduction_claimed": (
                self.total_work_or_wallclock_reduction_claimed
            ),
            "sample_efficiency_claimed": self.sample_efficiency_claimed,
            "learned_or_partial_dynamics_claimed": (
                self.learned_or_partial_dynamics_claimed
            ),
            "cross_domain_generalization_claimed": (
                self.cross_domain_generalization_claimed
            ),
            "official_execution_allowed": self.official_execution_allowed,
            "official_scalar_cost": self.official_scalar_cost,
            "official_N_break_even": self.official_N_break_even,
            "workload_economics_gate": self.workload_economics_gate,
            "counter_completeness_gate": self.counter_completeness_gate,
            "sample_efficiency_gate": self.sample_efficiency_gate,
        }

    @property
    def result_id(self) -> str:
        return _content_id("result", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "result_id": self.result_id}

def _context_semantic_document(
    context: IncrementalProofContextExecutionV1,
) -> dict[str, Any]:
    return {
        "context": context.context.to_document(),
        "threshold_binding": context.threshold_binding.to_document(),
        "plan_proposal": context.plan_proposal.to_document(),
        "candidate_audit_results": [
            item.to_document() for item in context.candidate_audit_results
        ],
        "selected_plan_audit": context.selected_plan_audit.to_document(),
    }


def _validate_control_equivalence(
    result: IncrementalProofDAGControlResultV1,
) -> None:
    arms = (
        result.request_reset_execution,
        result.occurrence_reset_execution,
        result.global_execution,
    )
    reference = tuple(
        _context_semantic_document(item) for item in arms[0].contexts
    )
    if any(
        tuple(_context_semantic_document(item) for item in arm.contexts)
        != reference
        for arm in arms[1:]
    ):
        raise IncrementalProofDAGInvariantViolation(
            "cache scope changed planner selection or exact audit artifacts"
        )
    global_receipts = {
        item.receipt_id: item for item in result.global_execution.use_receipts
    }
    if tuple(item.request_receipt_id for item in result.legacy_audit_matches) != tuple(
        item.receipt_id for item in result.global_execution.use_receipts
    ):
        raise IncrementalProofDAGInvariantViolation(
            "legacy matches are not ordered by the global proof requests"
        )
    if any(
        global_receipts[item.request_receipt_id].audit_result_id
        != item.incremental_audit_result_id
        for item in result.legacy_audit_matches
    ):
        raise IncrementalProofDAGInvariantViolation(
            "legacy match was transplanted to another incremental root"
        )


def _plans_for_context(
    observation_log: ObservationLogManifestV1,
    semantics_profile: DeterministicObservationProfileV1,
    observation_authority: PreregisteredObservationAuthorityV1,
    promotion: HeldOutFamilyPromotionBuildV1,
    context_execution: IncrementalProofContextExecutionV1,
) -> Mapping[str, FrozenContingentAbstractPlanV1]:
    thresholds = context_execution.threshold_binding.thresholds
    _, domains = _planner_context(
        observation_log,
        semantics_profile,
        observation_authority,
        promotion.model,
        thresholds,
    )
    schedules = _stage_assignments(domains)
    return {
        plan.plan_id: plan
        for schedule in product(schedules, repeat=thresholds.horizon)
        for plan in (
            FrozenContingentAbstractPlanV1(
                promotion.model.model_id,
                thresholds.horizon,
                tuple(
                    ContingentPlanStageV1(time_index, assignments)
                    for time_index, assignments in enumerate(schedule)
                ),
            ),
        )
    }


def _legacy_matches(
    observation_log: ObservationLogManifestV1,
    semantics_profile: DeterministicObservationProfileV1,
    observation_authority: PreregisteredObservationAuthorityV1,
    promotion: HeldOutFamilyPromotionBuildV1,
    execution: IncrementalProofDAGFamilyExecutionV1,
) -> tuple[LegacyAuditMatchV1, ...]:
    matches: list[LegacyAuditMatchV1] = []
    for index, context_execution in enumerate(execution.contexts):
        thresholds = context_execution.threshold_binding.thresholds
        plans = _plans_for_context(
            observation_log,
            semantics_profile,
            observation_authority,
            promotion,
            context_execution,
        )
        group = execution.use_receipts[3 * index : 3 * index + 3]
        incremental_by_request = {
            receipt.receipt_id: next(
                (
                    item
                    for item in context_execution.candidate_audit_results
                    if item.contingent_plan_id == receipt.contingent_plan_id
                ),
                context_execution.selected_plan_audit.audit_result,
            )
            if receipt.audit_role is ProofRootRole.CANDIDATE_RANKING_AUDIT
            else context_execution.selected_plan_audit.audit_result
            for receipt in group
        }
        for receipt in group:
            incremental = incremental_by_request[receipt.receipt_id]
            legacy = audit_module._audit_verified_partial_model_v1(
                promotion.model,
                observation_log,
                semantics_profile,
                observation_authority,
                thresholds,
                plans[receipt.contingent_plan_id],
            )
            if legacy.to_document() != incremental.to_document():
                raise IncrementalProofDAGInvariantViolation(
                    "R rematerialization differs from the unchanged legacy auditor"
                )
            matches.append(
                LegacyAuditMatchV1(
                    receipt.receipt_id,
                    context_execution.context.context_id,
                    receipt.audit_role,
                    receipt.contingent_plan_id,
                    incremental.result_id,
                    legacy.result_id,
                )
            )
    return tuple(matches)


def run_lmb_incremental_proof_dag_control_v1(
    observation_log: ObservationLogManifestV1,
    semantics_profile: DeterministicObservationProfileV1,
    observation_authority: PreregisteredObservationAuthorityV1,
    promotion: HeldOutFamilyPromotionBuildV1,
) -> IncrementalProofDAGControlResultV1:
    """Run all three reset arms and the evaluation-only 21-audit legacy match."""

    request_reset = _run_incremental_arm(
        observation_log,
        semantics_profile,
        observation_authority,
        promotion,
        ProofCacheScope.REQUEST_RESET,
    )
    occurrence_reset = _run_incremental_arm(
        observation_log,
        semantics_profile,
        observation_authority,
        promotion,
        ProofCacheScope.OCCURRENCE_RESET,
    )
    global_execution = run_identity_bound_incremental_proof_dag_family_v1(
        observation_log,
        semantics_profile,
        observation_authority,
        promotion,
    )
    matches = _legacy_matches(
        observation_log,
        semantics_profile,
        observation_authority,
        promotion,
        global_execution,
    )
    return IncrementalProofDAGControlResultV1(
        promotion.result_id,
        request_reset,
        occurrence_reset,
        global_execution,
        matches,
        len(matches),
    )


def verify_lmb_incremental_proof_dag_control_v1(
    observation_log: ObservationLogManifestV1,
    semantics_profile: DeterministicObservationProfileV1,
    observation_authority: PreregisteredObservationAuthorityV1,
    observed_synthesis_result: ObservedTypedPartialRAPMResultV1,
    source_thresholds: FrozenPartialAuditThresholdsV1,
    source_base_plan_proposal: TypedPartialModelPlanProposalResultV2,
    source_failed_audit: TypedPartialSoundAuditResultV2,
    protocol: HeldOutFamilyProtocolV1,
    source_result: MultiStepQueryRefinementResultV1,
    kernel: LMBKernel,
    parent_family_result: HeldOutFamilyAmortizationResultV1,
    claimed_result: IncrementalProofDAGControlResultV1,
) -> IncrementalProofDAGControlResultV1:
    """Rebuild V0-049 authority, then independently replay V0-051 in full."""

    if type(claimed_result) is not IncrementalProofDAGControlResultV1:
        raise IncrementalProofDAGInvariantViolation(
            "incremental verifier rejects substituted claimed results"
        )
    verified_parent = verify_lmb_heldout_family_amortization_v1(
        observation_log,
        semantics_profile,
        observation_authority,
        observed_synthesis_result,
        source_thresholds,
        source_base_plan_proposal,
        source_failed_audit,
        protocol,
        source_result,
        kernel,
        parent_family_result,
    )
    if (
        verified_parent.promotion_build.result_id
        != claimed_result.family_promotion_result_id
    ):
        raise IncrementalProofDAGInvariantViolation(
            "claimed proof DAG does not descend from the rebuilt V0-049 promotion"
        )
    replayed = run_lmb_incremental_proof_dag_control_v1(
        observation_log,
        semantics_profile,
        observation_authority,
        verified_parent.promotion_build,
    )
    if replayed.to_document() != claimed_result.to_document():
        raise IncrementalProofDAGInvariantViolation(
            "independent incremental proof DAG replay differs from the claim"
        )
    return replayed


__all__ = [
    "CONTEXT_SEQUENCE",
    "CONTRACT_VERSION",
    "ContextChangeClosureV1",
    "EXPECTED_FAMILY_PLANNER_SOURCE_SHA256",
    "EXPECTED_GLOBAL_COMPUTES",
    "EXPECTED_GLOBAL_REUSES",
    "EXPECTED_PARTIAL_AUDIT_SOURCE_SHA256",
    "IncrementalProofCacheV1",
    "IncrementalProofContextExecutionV1",
    "IncrementalProofContextV1",
    "IncrementalProofDAGControlResultV1",
    "IncrementalProofDAGFamilyExecutionV1",
    "IncrementalProofDAGInvariantViolation",
    "IncrementalProofDAGProtocolV1",
    "IncrementalProofDAGSemanticsV1",
    "IncrementalProofNodeEntryV1",
    "IncrementalProofNodeKeyV1",
    "IncrementalProofNodeResolutionV1",
    "IncrementalProofRequestReceiptV1",
    "IncrementalThresholdBindingV1",
    "LegacyAuditMatchV1",
    "PROFILE_KEY",
    "ProofCacheScope",
    "ProofDAGPrefixV1",
    "ProofDAGWorkV1",
    "ProofKindCountV1",
    "ProofNodeKind",
    "ProofResolutionOutcome",
    "ProofRootRole",
    "SCHEMA_VERSION",
    "SUCCESS_STATUS",
    "incremental_proof_dag_semantics_v1",
    "require_incremental_proof_dag_family_execution_v1",
    "run_identity_bound_incremental_proof_dag_family_v1",
    "run_lmb_incremental_proof_dag_control_v1",
    "verify_lmb_incremental_proof_dag_control_v1",
]
