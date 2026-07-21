"""Contract-0.9 general local-recovery Gate.

Phase 3D closes the three deliberately open limitations of the first local
hybrid slice without changing the immutable Phase 3C RAPM:

* failed proof localization is slack-aware and follows exact active Bellman
  derivations;
* the worker receives a compiled sparse affine capability instead of the
  selected-policy realization graph; and
* local actions are composed by one exact, cap-aware global deterministic
  value--risk search.

The safe-chain control reuses the existing portable model and proves the full
hybrid plan again.  A separate algebraic control contains the value/risk
trade-off that the Phase 3C independent minimum-risk choice cannot find.
Ground J0 is not an input to construction, localization, compilation, or
search in this profile.
"""

from __future__ import annotations

import argparse
import copy
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from fractions import Fraction
import hashlib
import itertools
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Any, Hashable, Mapping

from acfqp.artifacts import (
    PHASE3D_DOCUMENT_CONTRACTS,
    PHASE3D_REQUIRED_PATHS,
    canonical_sha256,
    object_id,
    serialized_json_sha256,
    sha256_file,
    to_jsonable,
    verify_artifact_bundle,
    write_artifact_bundle,
)
from acfqp.general_local_recovery import (
    FAILURE_UPPER,
    REWARD_LOWER,
    CertificateObligation,
    CausalSearchStatus,
    causal_circuit_from_failed_proof,
    evaluate_counterfactual_certificate,
    find_slack_aware_causal_family,
    root_channel_gain,
)
from acfqp.general_local_solver import (
    ALGORITHM_ID,
    CERTIFIED,
    POLICY_CLASS,
    REQUEST_SCHEMA,
    SEARCH_CAP_EXHAUSTED,
    SELECTION_RULE,
    SearchLimits,
    solve_general_local_recovery,
    validate_general_local_result,
)
from acfqp.frozen_phase3c import (
    FrozenPhase3CLoadError,
    FrozenPhase3CWorld,
    load_frozen_phase3c_world,
)
from acfqp.local_recovery import (
    FailedProofFrontier,
    GroundPatchDecision,
    HybridPolicyOverlay,
    LocalRecoveryAuthorization,
    PatchedAuditKernelView,
    audit_hybrid_policy,
    build_failed_proof_graph,
    build_redacted_boundary_view,
    materialize_authorized_slice,
    redact_authorized_slice_for_worker,
)
from acfqp.phase3c import (
    _audit_document,
    _select_recovery_proposal,
)
from acfqp.planning import (
    AbstractPolicyAudit,
    CellPolicyBound,
    FiniteHorizonPolicy,
    audit_abstract_policy,
)
from acfqp.portable import logical_id
from acfqp.portable_planner import PortablePlanResult, solve_portable_pareto
from acfqp.sparse_capability import (
    CAPABILITY_SCHEMA,
    SparseAffineForm,
    compile_sparse_recovery_inputs,
    parse_sparse_capability,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PHASE3C_BUNDLE = PROJECT_ROOT / "artifacts" / "phase3c"
PROFILE_KEY = "phase3d_general_local_recovery_v0"
EXECUTION_PROFILE = "phase3d_general_local_recovery"
CONTRACT_VERSION = "0.9.0"

PHASE3D_PASS = "PHASE3D_GENERAL_LOCAL_RECOVERY_PASS"
GENERAL_LOCAL_GATE_PASS = "GENERAL_LOCAL_RECOVERY_GATE_PASS"
FULL_PHASE3_NOT_RUN = "PHASE3_AGGREGATE_NOT_RUN"
ECONOMICS_NOT_RUN = "WORKLOAD_ECONOMICS_GATE_NOT_RUN"
INVARIANT_FAILURE = "PHASE3D_INVARIANT_VIOLATION"

CAUSAL_EVALUATION_CAP = 32
COMPILER_LIMITS = {
    "max_slice_cells": 64,
    "max_slice_members": 4096,
    "max_slice_actions": 65536,
    "max_slice_successor_rows": 262144,
    "max_cell_policy_assignments": 65536,
    "max_expanded_forms": 65536,
    "max_domain_assignments": 65536,
    "max_form_subset_evaluations": 65536,
}
SAFE_CHAIN_SEARCH_LIMITS = SearchLimits(
    max_subset_evaluations=16,
    max_policy_assignments=1024,
    max_root_frontier_points=128,
    max_dominance_comparisons=65536,
    max_affine_term_evaluations=65536,
    max_rational_bits=512,
)
SYNTHETIC_SEARCH_LIMITS = SearchLimits(
    max_subset_evaluations=16,
    max_policy_assignments=128,
    max_root_frontier_points=64,
    max_dominance_comparisons=4096,
    max_affine_term_evaluations=4096,
    max_rational_bits=256,
)

SUPPORTED_CLAIMS = (
    "slack-aware active-derivation search can remove reachable DirectBad residuals that cannot close the root certificate deficit",
    "a trusted selected-policy proof DAG can be compiled to an extensionally sufficient finite-domain-minimal sparse affine worker capability",
    "the isolated local worker jointly enumerates deterministic value-risk assignments across every authorized frontier cell and member under explicit caps",
    "the safe-chain hybrid preserves the immutable reusable RAPM while using a strictly smaller causal ground authorization than Phase 3C",
)

UNSUPPORTED_CLAIMS = (
    "automatic predicate invention or unknown quotient discovery",
    "one-shot recovery of causally dependent multi-horizon local cells",
    "information-theoretically minimum capability encoding",
    "uncapped polynomial-time local recovery",
    "workload break-even, full Phase 3/5, scale, learning, or cross-domain empirical generality",
)


class Phase3DInvariantViolation(RuntimeError):
    status = INVARIANT_FAILURE


_VERIFIED_MODEL_ESTIMATE_BINDING_AUTHORITY = object()
_PREPARED_ESTIMATE_MINT_AUTHORITY = object()
_EXECUTABLE_PREPARED_ESTIMATE_DERIVATION_AUTHORITY = object()

_PREPARED_ESTIMATE_BOUND_FIELDS = (
    "world",
    "query",
    "ground_query_id",
    "portable_query",
    "portable_result",
    "proposal",
    "proposal_source",
    "policy",
    "pre_audit",
    "proof_graph",
    "causal_circuit",
    "causal_search",
    "frontier",
    "authorization",
    "source_boundary",
    "source_phase3c_locality",
    "source_phase3c_authorization",
    "unrestricted_reward_upper",
    "verified_model_binding",
)


def _prepared_estimate_bound_value_v1(field_name: str, value: Any) -> Any:
    """Return a complete canonical view of one prepared-estimate field.

    Most bound objects are frozen dataclasses and are handled recursively by
    ``to_jsonable``.  ``CausalProofCircuit`` intentionally is not a dataclass,
    so spell out its complete public graph instead of falling back to an
    address-bearing ``repr``.  Portable planner objects provide their own
    canonical documents and are bound through those documents as well as live
    object identity in the opaque mint.
    """

    if field_name == "causal_circuit":
        return {
            "nodes": to_jsonable(value.nodes),
            "roots": to_jsonable(value.roots),
            "node_index": {
                node_id: to_jsonable(node)
                for node_id, node in sorted(value._by_id.items())
            },
        }
    if field_name in {"portable_result", "proposal"}:
        return value.to_dict()
    if field_name == "verified_model_binding":
        if value is None:
            return None
        return {
            name: getattr(value, name)
            for name in (
                "model_only_result_id",
                "selected_plan_id",
                "threshold_profile_id",
                "route_decision_context_id",
                "abstract_audit_attestation_id",
                "verification_work_record_id",
                "ground_binding_id",
            )
        }
    return to_jsonable(value)


def _prepared_estimate_payload_sha256_v1(
    fields: Mapping[str, Any],
) -> str:
    missing = set(_PREPARED_ESTIMATE_BOUND_FIELDS) - set(fields)
    extra = set(fields) - set(_PREPARED_ESTIMATE_BOUND_FIELDS)
    if missing or extra:
        raise Phase3DInvariantViolation(
            "prepared estimate binding field set is incomplete"
        )
    payload = {
        "schema": "acfqp.safe_chain_prepared_estimate_payload.v1",
        "fields": {
            name: _prepared_estimate_bound_value_v1(name, fields[name])
            for name in _PREPARED_ESTIMATE_BOUND_FIELDS
        },
    }
    return hashlib.sha256(
        b"acfqp:safe-chain-prepared-estimate-payload:v1\x00"
        + _canonical_bytes(payload)
    ).hexdigest()


@dataclass(frozen=True, slots=True)
class VerifiedModelEstimateBindingV1:
    """Process-local bridge from a verified model failure to local estimation.

    The public IDs are conveniences for downstream route construction.  Their
    authority comes from the retained model result, semantic audit result, and
    ground handoff; copying this object and replacing an ID cannot mint a new
    binding because every construction replays that retained triple.
    """

    model_only_result_id: str
    selected_plan_id: str
    threshold_profile_id: str
    route_decision_context_id: str
    abstract_audit_attestation_id: str
    verification_work_record_id: str
    ground_binding_id: str
    _model_only_result: object = field(repr=False, compare=False)
    _abstract_audit_authority: object = field(repr=False, compare=False)
    _ground_binding: object = field(repr=False, compare=False)
    _authority: object = field(repr=False, compare=False)

    def __post_init__(self) -> None:
        _validate_verified_model_estimate_binding_core_v1(self)


def _validate_verified_model_estimate_binding_core_v1(
    binding: VerifiedModelEstimateBindingV1,
) -> None:
    """Replay the retained authority triple behind one estimate binding."""

    from acfqp.phase3e_ground_handoff_v1 import (
        GroundBindingAfterFailedAuditV1,
        Phase3EGroundHandoffV1Error,
        require_ground_binding_after_failed_audit_v1,
    )
    from acfqp.phase3e_model_only_v1 import (
        ModelOnlyOutcome,
        Phase3EModelOnlyResultV1,
    )
    from acfqp.semantic_verification_v1 import (
        SemanticRole,
        SemanticVerificationResultV1,
        SemanticVerificationV1Error,
        require_semantic_verification_result_v1,
    )

    if (
        type(binding) is not VerifiedModelEstimateBindingV1
        or binding._authority is not _VERIFIED_MODEL_ESTIMATE_BINDING_AUTHORITY
        or type(binding._model_only_result) is not Phase3EModelOnlyResultV1
        or type(binding._abstract_audit_authority)
        is not SemanticVerificationResultV1
        or type(binding._ground_binding) is not GroundBindingAfterFailedAuditV1
    ):
        raise Phase3DInvariantViolation(
            "verified-model estimate binding lacks its retained authority triple"
        )
    result = binding._model_only_result
    try:
        ground = require_ground_binding_after_failed_audit_v1(
            binding._ground_binding
        )
        audit_authority = require_semantic_verification_result_v1(
            binding._abstract_audit_authority, SemanticRole.ABSTRACT_AUDIT
        )
    except (Phase3EGroundHandoffV1Error, SemanticVerificationV1Error) as error:
        raise Phase3DInvariantViolation(
            f"verified-model estimate binding replay failed: {error}"
        ) from error
    if (
        result.outcome is not ModelOnlyOutcome.FAIL
        or result.ground_binding_required is not True
        or audit_authority.outcome != "FAIL"
        or audit_authority is not ground.semantic_authority
        or audit_authority.binding.route_context != result.route_context
        or audit_authority.artifact != result.audit
        or ground.model_only_result_id != result.result_id
    ):
        raise Phase3DInvariantViolation(
            "verified-model estimate binding retains a foreign or nonfailed chain"
        )
    expected = {
        "model_only_result_id": result.result_id,
        "selected_plan_id": result.route_context.selected_plan_id,
        "threshold_profile_id": result.route_context.threshold_profile_id,
        "route_decision_context_id": (
            result.route_context.route_decision_context_id
        ),
        "abstract_audit_attestation_id": (
            audit_authority.attestation.verification_attestation_id
        ),
        "verification_work_record_id": (
            audit_authority.verification_work_record.record_id
        ),
        "ground_binding_id": ground.ground_binding_id,
    }
    for field_name, expected_value in expected.items():
        if getattr(binding, field_name) != expected_value:
            raise Phase3DInvariantViolation(
                f"verified-model estimate binding mismatch for {field_name}"
            )


@dataclass(frozen=True, slots=True)
class _SafeChainPreparedEstimateMintV1:
    """One-owner opaque seal over every prepared-estimate input.

    ``bound_objects`` prevents an equal-content object from being spliced into
    a live capability.  ``payload_sha256`` additionally detects mutation of a
    retained mapping or another nested object after minting.  ``owner`` makes
    a generic ``dataclasses.replace`` copy fail closed even when none of the
    public fields changed.
    """

    verified_model_binding: VerifiedModelEstimateBindingV1 | None = field(
        repr=False, compare=False
    )
    bound_objects: tuple[tuple[str, object], ...] = field(
        repr=False, compare=False
    )
    payload_sha256: str = field(repr=False, compare=False)
    derivation_kind: str
    parent_payload_sha256: str | None
    authority: object = field(repr=False, compare=False)
    owner: object | None = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        if (
            self.authority is not _PREPARED_ESTIMATE_MINT_AUTHORITY
            or tuple(name for name, _value in self.bound_objects)
            != _PREPARED_ESTIMATE_BOUND_FIELDS
            or len(self.payload_sha256) != 64
            or self.derivation_kind
            not in {"FROZEN_ESTIMATE", "ACCESS_LOGGED_KERNEL_DERIVATIVE"}
            or (
                self.derivation_kind == "FROZEN_ESTIMATE"
                and self.parent_payload_sha256 is not None
            )
            or (
                self.derivation_kind == "ACCESS_LOGGED_KERNEL_DERIVATIVE"
                and (
                    self.parent_payload_sha256 is None
                    or len(self.parent_payload_sha256) != 64
                )
            )
        ):
            raise Phase3DInvariantViolation(
                "prepared estimate mint has no trusted constructor"
            )


@dataclass(frozen=True, slots=True)
class SafeChainPreparedEstimateContext:
    """Safe-chain proof/frontier state before selected-route execution.

    This object contains no materialized ground slice, compiled capability,
    worker result, stitch, or post-audit.  Contract-1.0 consumers may use its
    frozen proof and action-catalogue cardinalities to construct marginal route
    uppers before a route decision is frozen.
    """

    world: Any
    query: Any
    ground_query_id: str
    portable_query: Any
    portable_result: Any
    proposal: Any
    proposal_source: str
    policy: FiniteHorizonPolicy[Any, Any]
    pre_audit: Any
    proof_graph: Any
    causal_circuit: Any
    causal_search: Any
    frontier: FailedProofFrontier
    authorization: LocalRecoveryAuthorization
    source_boundary: dict[str, Any]
    source_phase3c_locality: dict[str, Any]
    source_phase3c_authorization: dict[str, Any]
    unrestricted_reward_upper: Fraction
    _mint: _SafeChainPreparedEstimateMintV1 = field(repr=False, compare=False)
    verified_model_binding: VerifiedModelEstimateBindingV1 | None = field(
        default=None, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        _validate_safe_chain_prepared_estimate_context_v1(
            self, allow_unowned_mint=True
        )

    def __copy__(self) -> object:
        raise Phase3DInvariantViolation(
            "prepared estimate is a one-owner capability and cannot be copied"
        )

    def __deepcopy__(self, memo: dict[int, object]) -> object:
        raise Phase3DInvariantViolation(
            "prepared estimate is a one-owner capability and cannot be deep-copied"
        )

    def __reduce_ex__(self, protocol: int) -> object:
        raise Phase3DInvariantViolation(
            "prepared estimate is a live capability and cannot be serialized"
        )


def _prepared_estimate_context_fields_v1(
    prepared: SafeChainPreparedEstimateContext,
) -> dict[str, Any]:
    return {
        name: getattr(prepared, name)
        for name in _PREPARED_ESTIMATE_BOUND_FIELDS
    }


def _validate_safe_chain_prepared_estimate_context_v1(
    prepared: SafeChainPreparedEstimateContext,
    *,
    allow_unowned_mint: bool = False,
) -> None:
    """Verify live ownership, exact object binding, and the payload snapshot."""

    if type(prepared) is not SafeChainPreparedEstimateContext:
        raise Phase3DInvariantViolation(
            "prepared estimate requires the exact safe-chain context type"
        )
    mint = prepared._mint
    if (
        type(mint) is not _SafeChainPreparedEstimateMintV1
        or mint.authority is not _PREPARED_ESTIMATE_MINT_AUTHORITY
        or (
            mint.owner is not prepared
            and not (allow_unowned_mint and mint.owner is None)
        )
        or prepared.verified_model_binding is not mint.verified_model_binding
    ):
        raise Phase3DInvariantViolation(
            "prepared estimate continuation binding differs from its mint"
        )
    fields = _prepared_estimate_context_fields_v1(prepared)
    for field_name, expected_object in mint.bound_objects:
        if fields[field_name] is not expected_object:
            raise Phase3DInvariantViolation(
                f"prepared estimate object binding mismatch for {field_name}"
            )
    if _prepared_estimate_payload_sha256_v1(fields) != mint.payload_sha256:
        raise Phase3DInvariantViolation(
            "prepared estimate payload differs from its cryptographic mint"
        )


def _mint_safe_chain_prepared_estimate_context_v1(
    *,
    derivation_kind: str = "FROZEN_ESTIMATE",
    parent_payload_sha256: str | None = None,
    **fields: Any,
) -> SafeChainPreparedEstimateContext:
    """Mint the sole live owner for one complete prepared-estimate payload."""

    payload_sha256 = _prepared_estimate_payload_sha256_v1(fields)
    mint = _SafeChainPreparedEstimateMintV1(
        verified_model_binding=fields["verified_model_binding"],
        bound_objects=tuple(
            (name, fields[name]) for name in _PREPARED_ESTIMATE_BOUND_FIELDS
        ),
        payload_sha256=payload_sha256,
        derivation_kind=derivation_kind,
        parent_payload_sha256=parent_payload_sha256,
        authority=_PREPARED_ESTIMATE_MINT_AUTHORITY,
    )
    prepared = SafeChainPreparedEstimateContext(**fields, _mint=mint)
    object.__setattr__(mint, "owner", prepared)
    _validate_safe_chain_prepared_estimate_context_v1(prepared)
    return prepared


def require_safe_chain_prepared_estimate_context_v1(
    prepared: SafeChainPreparedEstimateContext,
) -> SafeChainPreparedEstimateContext:
    """Require the exact one-owner, cryptographically sealed context."""

    _validate_safe_chain_prepared_estimate_context_v1(prepared)
    return prepared


def _derive_safe_chain_access_logged_estimate_v1(
    prepared: SafeChainPreparedEstimateContext,
    *,
    access_logged_kernel: object,
    authority: object,
) -> SafeChainPreparedEstimateContext:
    """Mint the one authorized post-freeze executable-world derivative.

    The caller cannot supply a replacement world or any proof/authorization
    field.  This function derives the world itself and changes exactly its
    kernel to a wrapper over the source kernel.  All other prepared fields are
    copied from the validated parent and receive a fresh one-owner seal.
    """

    if authority is not _EXECUTABLE_PREPARED_ESTIMATE_DERIVATION_AUTHORITY:
        raise Phase3DInvariantViolation(
            "executable estimate derivative lacks post-freeze authority"
        )
    _validate_safe_chain_prepared_estimate_context_v1(prepared)
    if getattr(access_logged_kernel, "_kernel", None) is not prepared.world.kernel:
        raise Phase3DInvariantViolation(
            "executable estimate kernel does not wrap the frozen parent kernel"
        )
    executable_world = replace(prepared.world, kernel=access_logged_kernel)
    fields = _prepared_estimate_context_fields_v1(prepared)
    fields["world"] = executable_world
    return _mint_safe_chain_prepared_estimate_context_v1(
        **fields,
        derivation_kind="ACCESS_LOGGED_KERNEL_DERIVATIVE",
        parent_payload_sha256=prepared._mint.payload_sha256,
    )


def require_verified_model_estimate_binding_v1(
    prepared: SafeChainPreparedEstimateContext,
) -> VerifiedModelEstimateBindingV1:
    """Return the exact model-only route identity retained by ``prepared``."""

    _validate_safe_chain_prepared_estimate_context_v1(prepared)
    binding = prepared.verified_model_binding
    if type(binding) is not VerifiedModelEstimateBindingV1:
        raise Phase3DInvariantViolation(
            "prepared estimate has no verified-model continuation binding"
        )
    _validate_verified_model_estimate_binding_core_v1(binding)
    result = binding._model_only_result
    ground = binding._ground_binding
    portable_result_document = prepared.portable_result.to_dict()
    audit = result.audit
    if (
        prepared.world is not ground.world
        or prepared.ground_query_id != result.source_lease.legacy_ground_query_id
        or prepared.portable_query.query_id
        != result.source_lease.legacy_portable_query_id
        or portable_result_document != result.selected_plan.planner_result
        or prepared.proposal != result.selected_plan.proposal
        or prepared.proposal_source != result.selected_plan.proposal_source
        or prepared.pre_audit.unrestricted_reward_upper
        != audit.unrestricted_reward_upper
        or prepared.pre_audit.lifted_reward_lower != audit.policy_reward_lower
        or prepared.pre_audit.lifted_failure_upper != audit.policy_failure_upper
        or prepared.pre_audit.regret_upper != audit.regret_upper
        or prepared.pre_audit.regret_tolerance != audit.regret_tolerance
        or prepared.pre_audit.risk_tolerance != audit.risk_tolerance
    ):
        raise Phase3DInvariantViolation(
            "prepared estimate is spliced from a different verified-model chain"
        )
    return binding


def _mint_verified_model_estimate_binding_v1(
    *,
    model_only_result: object,
    abstract_audit_authority: object,
    ground_binding: object,
) -> VerifiedModelEstimateBindingV1:
    """Mint the process-local identity bridge after the FAIL handoff."""

    return VerifiedModelEstimateBindingV1(
        model_only_result_id=model_only_result.result_id,
        selected_plan_id=model_only_result.route_context.selected_plan_id,
        threshold_profile_id=model_only_result.route_context.threshold_profile_id,
        route_decision_context_id=(
            model_only_result.route_context.route_decision_context_id
        ),
        abstract_audit_attestation_id=(
            abstract_audit_authority.attestation.verification_attestation_id
        ),
        verification_work_record_id=(
            abstract_audit_authority.verification_work_record.record_id
        ),
        ground_binding_id=ground_binding.ground_binding_id,
        _model_only_result=model_only_result,
        _abstract_audit_authority=abstract_audit_authority,
        _ground_binding=ground_binding,
        _authority=_VERIFIED_MODEL_ESTIMATE_BINDING_AUTHORITY,
    )


@dataclass(frozen=True, slots=True)
class SafeChainContext:
    world: Any
    query: Any
    ground_query_id: str
    portable_query: Any
    portable_result: Any
    proposal: Any
    proposal_source: str
    policy: FiniteHorizonPolicy[Any, Any]
    pre_audit: Any
    proof_graph: Any
    causal_circuit: Any
    causal_search: Any
    frontier: FailedProofFrontier
    authorization: LocalRecoveryAuthorization
    v1_slice: dict[str, Any]
    sparse_slice: dict[str, Any]
    capability: dict[str, Any]
    capability_evidence: dict[str, Any]
    source_boundary: dict[str, Any]
    source_phase3c_locality: dict[str, Any]
    source_phase3c_authorization: dict[str, Any]
    materialization_counts: dict[str, int]
    unrestricted_reward_upper: Fraction


@dataclass(frozen=True, slots=True)
class _FrozenEstimateKernelView:
    """The only kernel-shaped authority admitted during route estimation.

    Terminal status is read from the serialized RAPM state catalogue.  Live
    action and transition methods are intentionally fail-closed; action
    cardinalities come from ``FrozenPhase3CWorld.bound_ground_action_records``.
    """

    horizon: int
    registered_reward_features: tuple[str, ...]
    registered_goals: tuple[str, ...]
    registry: Any
    planning_kind_by_state_id: Mapping[str, str]

    @classmethod
    def from_world(cls, world: Any) -> "_FrozenEstimateKernelView":
        model = world.portable.model
        document = model.to_dict()
        kinds = {
            row["state_id"]: row["planning_kind"]
            for row in document["state_catalog"]
        }
        if not kinds or any(
            kind not in {"active", "terminal", "failure"}
            for kind in kinds.values()
        ):
            raise Phase3DInvariantViolation(
                "frozen RAPM lacks a complete planning-kind catalogue"
            )
        return cls(
            int(model.horizon),
            tuple(model.reward_features),
            tuple(model.goal_ids),
            world.portable.registry,
            kinds,
        )

    def is_terminal(self, state: Hashable) -> bool:
        try:
            state_id = self.registry.state_id(state)
            return self.planning_kind_by_state_id[state_id] != "active"
        except KeyError as error:
            raise Phase3DInvariantViolation(
                "estimate state is absent from the frozen RAPM catalogue"
            ) from error

    def actions(self, _state: Hashable) -> tuple[Any, ...]:
        raise Phase3DInvariantViolation(
            "live kernel actions are forbidden during route estimation"
        )

    def step(self, _state: Hashable, _action: Hashable) -> tuple[Any, ...]:
        raise Phase3DInvariantViolation(
            "live kernel transitions are forbidden during route estimation"
        )


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            to_jsonable(value),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _input_sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _fraction_json(value: Fraction | int) -> dict[str, int]:
    value = Fraction(value)
    return {"numerator": value.numerator, "denominator": value.denominator}


def _fraction(value: Mapping[str, int]) -> Fraction:
    return Fraction(value["numerator"], value["denominator"])


def _system_mounts() -> tuple[str, ...]:
    mounts: list[str] = []
    for system_path in ("/usr", "/lib", "/lib64"):
        if Path(system_path).exists():
            mounts.extend(("--ro-bind", system_path, system_path))
    return tuple(mounts)


def _isolated_python() -> str:
    candidate = shutil.which("python3", path="/usr/bin:/bin")
    if candidate is None:
        raise Phase3DInvariantViolation(
            "Phase 3D isolation requires system python3 under /usr/bin or /bin"
        )
    return str(Path(candidate).resolve())


def _causal_frontier(graph: Any, node_ids: tuple[str, ...]) -> FailedProofFrontier:
    nodes = tuple(graph.node(node_id) for node_id in sorted(node_ids))
    payload = {"graph_id": graph.graph_id, "node_ids": tuple(node.node_id for node in nodes)}
    return FailedProofFrontier(
        graph.graph_id,
        nodes,
        object_id(payload, "failed-proof-frontier"),
    )


def _frozen_capability_cost(
    world: Any,
    proof_node: Any,
    estimate_kernel: _FrozenEstimateKernelView,
    *,
    allow_live_evaluation_catalogue: bool = False,
) -> int:
    """Count a proof cell's registered ground actions without kernel access."""

    count = sum(
        len(
            _frozen_ground_actions(
                world,
                state,
                allow_live_evaluation_catalogue=allow_live_evaluation_catalogue,
            )
        )
        for state in world.partition.members(proof_node.cell)
        if not estimate_kernel.is_terminal(state)
    )
    if count <= 0:
        raise Phase3DInvariantViolation(
            "frozen registry has no ground actions for an active proof cell"
        )
    return count


def _frozen_ground_actions(
    world: Any,
    state: Hashable,
    *,
    allow_live_evaluation_catalogue: bool = False,
) -> tuple[Hashable, ...]:
    """Return one state's complete binding-time ground-action catalogue.

    Operational frozen worlds carry all 144 records captured during their
    permitted namespace binding.  A plain authority world occurs only inside
    the standalone evaluation verifier and may query its rebuilt kernel.
    """

    records = getattr(world, "bound_ground_action_records", None)
    if records is not None:
        return tuple(action for candidate, action in records if candidate == state)
    if allow_live_evaluation_catalogue:
        return tuple(world.kernel.actions(state))
    raise Phase3DInvariantViolation(
        "Phase 3E route estimation requires a prebound frozen action catalogue"
    )


def _authority_accounting(context: SafeChainContext) -> dict[str, Any]:
    """Reconcile locality without opening any additional ground transition.

    Phase-3C/all-query/coverage baselines come from the verified frozen source
    locality artifact.  Phase-3D frontier outcome counts are captured while the
    already-authorized slice is materialized.  Reverse-dependency transitions
    are capability support only and are not re-stepped merely for accounting.
    """

    source = context.source_phase3c_locality
    source_authorization = context.source_phase3c_authorization
    authorization = context.authorization
    materialized = context.materialization_counts
    phase3c = {
        "frontier_state_actions": source["frontier_state_action_pairs"],
        "ancestor_state_actions": source[
            "reverse_selected_dependency_state_action_pairs"
        ],
        "authorized_state_actions": source["authorized_state_action_pairs"],
        "frontier_positive_outcomes": source[
            "frontier_positive_probability_outcomes"
        ],
        "ancestor_positive_outcomes": source[
            "reverse_selected_dependency_positive_probability_outcomes"
        ],
        "authorized_positive_outcomes": source[
            "authorized_positive_probability_outcomes"
        ],
    }
    phase3d = {
        "frontier_state_actions": len(authorization.frontier_state_actions),
        "ancestor_state_actions": len(
            authorization.reverse_dependency_state_actions
        ),
        "authorized_state_actions": len(authorization.allowed_state_actions),
        "frontier_positive_outcomes": materialized[
            "positive_probability_outcomes"
        ],
        "ancestor_positive_outcomes": source[
            "reverse_selected_dependency_positive_probability_outcomes"
        ],
    }
    phase3d["authorized_positive_outcomes"] = (
        phase3d["frontier_positive_outcomes"]
        + phase3d["ancestor_positive_outcomes"]
    )
    current_frontier_ids = {
        (object_id(state, "state"), object_id(action, "ground-action"))
        for state, action in authorization.frontier_state_actions
    }
    current_reverse_ids = {
        (object_id(state, "state"), object_id(action, "ground-action"))
        for state, action in authorization.reverse_dependency_state_actions
    }
    source_frontier_ids = {
        (row["state_id"], row["action_id"])
        for row in source_authorization["frontier_state_actions"]
    }
    source_reverse_ids = {
        (row["state_id"], row["action_id"])
        for row in source_authorization[
            "reverse_selected_dependency_state_actions"
        ]
    }
    if (
        not current_frontier_ids < source_frontier_ids
        or current_reverse_ids != source_reverse_ids
    ):
        raise Phase3DInvariantViolation(
            "Phase 3D authorization is not the registered causal subset of Phase 3C"
        )
    result = {
        "phase3c": phase3c,
        "phase3d": phase3d,
        "same_query_all_action": source["full_same_query_all_action_graph"],
        "coverage": {
            "state_actions": source["coverage_ground_state_action_pairs"],
            "positive_outcomes": source[
                "coverage_positive_probability_outcomes"
            ],
        },
    }
    expected = {
        "phase3c": {
            "frontier_state_actions": 32,
            "ancestor_state_actions": 8,
            "authorized_state_actions": 40,
            "frontier_positive_outcomes": 128,
            "ancestor_positive_outcomes": 32,
            "authorized_positive_outcomes": 160,
        },
        "phase3d": {
            "frontier_state_actions": 16,
            "ancestor_state_actions": 8,
            "authorized_state_actions": 24,
            "frontier_positive_outcomes": 64,
            "ancestor_positive_outcomes": 32,
            "authorized_positive_outcomes": 96,
        },
        "same_query_all_action": {
            "decision_state_time_pairs": 20,
            "state_action_pairs": 48,
            "positive_probability_outcomes": 192,
        },
        "coverage": {
            "state_actions": 144,
            "positive_outcomes": 576,
        },
    }
    if result != expected:
        raise Phase3DInvariantViolation(
            f"Phase 3D authority accounting golden changed: {result!r}"
        )
    if materialized != {
        "state_action_steps": result["phase3d"]["frontier_state_actions"],
        "positive_probability_outcomes": result["phase3d"][
            "frontier_positive_outcomes"
        ],
    }:
        raise Phase3DInvariantViolation(
            "Phase 3D materialized-slice accounting is inconsistent"
        )
    if result["coverage"]["state_actions"] != context.world.build_epoch.get(
        "ground_state_action_pairs"
    ):
        raise Phase3DInvariantViolation(
            "Phase 3D coverage accounting disagrees with the base BuildEpoch"
        )
    return result


def _prepare_safe_chain_estimate_from_frozen_plan(
    world: Any,
    *,
    query: Any,
    portable_query: Any,
    portable_result: Any,
    proposal: Any,
    proposal_source: str,
    policy: FiniteHorizonPolicy[Any, Any],
    pre_audit: AbstractPolicyAudit,
    source_phase3c_locality: Mapping[str, Any],
    source_phase3c_authorization: Mapping[str, Any],
    allow_live_evaluation_catalogue: bool = False,
    verified_model_binding: VerifiedModelEstimateBindingV1 | None = None,
) -> SafeChainPreparedEstimateContext:
    """Prepare proof/frontier/cardinalities from an already frozen plan/audit.

    This is the shared estimate-only tail.  It deliberately has no planner or
    abstract-auditor call: every realization comes from the reusable RAPM
    envelope and every ground-action cardinality comes from the binding-time
    catalogue.  Materialization and compilation are also absent.
    """

    if (
        getattr(world, "bound_ground_action_records", None) is None
        and not allow_live_evaluation_catalogue
    ):
        raise Phase3DInvariantViolation(
            "route estimation requires a prebound frozen ground-action catalogue"
        )
    estimate_kernel = _FrozenEstimateKernelView.from_world(world)
    if (
        pre_audit.certified
        or pre_audit.lifted_reward_lower != Fraction(3, 64)
        or pre_audit.lifted_failure_upper != Fraction(5099, 10000)
        or pre_audit.unrestricted_reward_upper != Fraction(3, 64)
    ):
        raise Phase3DInvariantViolation("safe-chain pre-certificate golden changed")

    graph = build_failed_proof_graph(
        estimate_kernel,
        query,
        world.models.envelope,
        policy,
        pre_audit,
    )
    circuit = causal_circuit_from_failed_proof(
        estimate_kernel,
        query,
        world.models.envelope,
        policy,
        graph,
        capability_cost_provider=lambda node: _frozen_capability_cost(
            world,
            node,
            estimate_kernel,
            allow_live_evaluation_catalogue=allow_live_evaluation_catalogue,
        ),
    )
    obligations = (
        CertificateObligation(
            REWARD_LOWER,
            pre_audit.unrestricted_reward_upper - pre_audit.regret_tolerance,
        ),
        CertificateObligation(FAILURE_UPPER, pre_audit.risk_tolerance),
    )
    causal = find_slack_aware_causal_family(
        circuit,
        obligations,
        max_evaluations=CAUSAL_EVALUATION_CAP,
    )
    if (
        causal.status is not CausalSearchStatus.CAUSAL_FAMILY_FOUND
        or not causal.search_complete
        or causal.selected_node_ids is None
        or len(causal.selected_node_ids) != 1
        or causal.minimal_cover_node_ids != (causal.selected_node_ids,)
        or causal.baseline.root_value(FAILURE_UPPER) != Fraction(5099, 10000)
    ):
        raise Phase3DInvariantViolation("slack-aware safe-chain causal golden changed")

    selected_counterfactual = evaluate_counterfactual_certificate(
        circuit,
        obligations,
        causal.selected_node_ids,
    )
    if selected_counterfactual.root_value(FAILURE_UPPER) != Fraction(397, 20000):
        raise Phase3DInvariantViolation("safe-chain causal counterfactual changed")
    frontier = _causal_frontier(graph, causal.selected_node_ids)
    authorization = LocalRecoveryAuthorization.for_frontier(
        estimate_kernel,
        world.models.envelope,
        frontier,
        graph,
        ground_action_provider=lambda state: _frozen_ground_actions(
            world,
            state,
            allow_live_evaluation_catalogue=allow_live_evaluation_catalogue,
        ),
    )
    if (
        len(authorization.frontier_state_actions) != 16
        or len(authorization.reverse_dependency_state_actions) != 8
        or len(authorization.allowed_state_actions) != 24
    ):
        raise Phase3DInvariantViolation("causal authorization golden changed")

    source_boundary = build_redacted_boundary_view(
        query,
        world.models.envelope,
        policy,
        graph,
        unrestricted_reward_upper=pre_audit.unrestricted_reward_upper,
        regret_tolerance=pre_audit.regret_tolerance,
    )
    source_phase3c_locality_document = dict(source_phase3c_locality)
    source_phase3c_authorization_document = dict(source_phase3c_authorization)
    return _mint_safe_chain_prepared_estimate_context_v1(
        world=world,
        query=query,
        ground_query_id=object_id(query, "query"),
        portable_query=portable_query,
        portable_result=portable_result,
        proposal=proposal,
        proposal_source=proposal_source,
        policy=policy,
        pre_audit=pre_audit,
        proof_graph=graph,
        causal_circuit=circuit,
        causal_search=causal,
        frontier=frontier,
        authorization=authorization,
        source_boundary=source_boundary,
        source_phase3c_locality=source_phase3c_locality_document,
        source_phase3c_authorization=source_phase3c_authorization_document,
        unrestricted_reward_upper=pre_audit.unrestricted_reward_upper,
        verified_model_binding=verified_model_binding,
    )


def _prepare_safe_chain_estimate_from_world(
    world: Any,
    *,
    unrestricted_reward_upper: Fraction,
    source_phase3c_locality: Mapping[str, Any],
    source_phase3c_authorization: Mapping[str, Any],
    allow_live_evaluation_catalogue: bool = False,
) -> SafeChainPreparedEstimateContext:
    """Historical planner/auditor front end for the shared estimate-only tail."""

    estimate_kernel = _FrozenEstimateKernelView.from_world(world)
    registered = world.queries[1]
    query = registered.query
    portable_query = world.portable.query_from_spec(query)
    portable_result = solve_portable_pareto(world.portable.model, portable_query)
    proposal, proposal_source = _select_recovery_proposal(portable_result)
    policy = FiniteHorizonPolicy.from_mapping(
        world.portable.decode_policy(proposal.policy)
    )
    pre_audit = audit_abstract_policy(
        estimate_kernel,
        query,
        world.models.envelope,
        policy,
        regret_tolerance=Fraction(1, 20),
        unrestricted_reward_upper=unrestricted_reward_upper,
    )
    return _prepare_safe_chain_estimate_from_frozen_plan(
        world,
        query=query,
        portable_query=portable_query,
        portable_result=portable_result,
        proposal=proposal,
        proposal_source=proposal_source,
        policy=policy,
        pre_audit=pre_audit,
        source_phase3c_locality=source_phase3c_locality,
        source_phase3c_authorization=source_phase3c_authorization,
        allow_live_evaluation_catalogue=allow_live_evaluation_catalogue,
    )


def _execute_safe_chain_local_preparation(
    prepared: SafeChainPreparedEstimateContext,
) -> SafeChainContext:
    """Materialize and compile only after a caller has frozen LOCAL selection."""

    _validate_safe_chain_prepared_estimate_context_v1(prepared)

    world = prepared.world
    query = prepared.query
    frontier = prepared.frontier
    authorization = prepared.authorization
    graph = prepared.proof_graph

    materialized = materialize_authorized_slice(
        world.kernel,
        query,
        world.models.envelope,
        frontier,
        authorization,
        graph=graph,
        state_payload=lambda state: {
            "board": state.board,
            "status": state.status.value,
        },
        action_payload=lambda action: {
            "first": action.first,
            "second": action.second,
            "survivor": action.survivor,
        },
    )
    materialization_counts = dict(materialized["materialization_counts"])
    if materialization_counts != {
        "state_action_steps": 16,
        "positive_probability_outcomes": 64,
    }:
        raise Phase3DInvariantViolation(
            "authorized frontier materialization accounting changed"
        )
    access_log = tuple(materialized["access_log"])
    materialized_step_ids = {
        (row["state_id"], row["action_id"])
        for row in access_log
        if row["operation"] == "step"
    }
    authorized_frontier_ids = {
        (object_id(state, "state"), object_id(action, "ground-action"))
        for state, action in authorization.frontier_state_actions
    }
    if (
        len(access_log) != 24
        or sum(row["operation"] == "actions" for row in access_log) != 8
        or sum(row["operation"] == "step" for row in access_log) != 16
        or materialized_step_ids != authorized_frontier_ids
    ):
        raise Phase3DInvariantViolation(
            "authorized materialization access log is not the exact frontier"
        )
    v1_slice = redact_authorized_slice_for_worker(materialized)
    compiled = compile_sparse_recovery_inputs(
        prepared.source_boundary,
        v1_slice,
        target_frontier_id=frontier.frontier_id,
        **COMPILER_LIMITS,
    )
    capability = compiled.compilation.capability.to_dict()
    sparse_slice = compiled.sparse_slice
    evidence = compiled.compilation.evidence
    parse_sparse_capability(capability)
    if (
        len(capability["input_ports"]) != 1
        or capability["exit_ports"] != []
        or len(capability["root_reward_forms"]) != 1
        or len(capability["root_failure_forms"]) != 1
        or len(sparse_slice["cells"]) != 1
        or len(sparse_slice["cells"][0]["members"]) != 8
        or evidence["source_node_count"] != 4
        or evidence["source_abstract_realization_row_count"] != 20
    ):
        raise Phase3DInvariantViolation("sparse capability golden changed")

    return SafeChainContext(
        world=world,
        query=query,
        ground_query_id=prepared.ground_query_id,
        portable_query=prepared.portable_query,
        portable_result=prepared.portable_result,
        proposal=prepared.proposal,
        proposal_source=prepared.proposal_source,
        policy=prepared.policy,
        pre_audit=prepared.pre_audit,
        proof_graph=graph,
        causal_circuit=prepared.causal_circuit,
        causal_search=prepared.causal_search,
        frontier=frontier,
        authorization=authorization,
        v1_slice=v1_slice,
        sparse_slice=sparse_slice,
        capability=capability,
        capability_evidence=evidence,
        source_boundary=prepared.source_boundary,
        source_phase3c_locality=prepared.source_phase3c_locality,
        source_phase3c_authorization=prepared.source_phase3c_authorization,
        materialization_counts=materialization_counts,
        unrestricted_reward_upper=prepared.unrestricted_reward_upper,
    )


def _construct_safe_chain_context_from_world(
    world: Any,
    *,
    unrestricted_reward_upper: Fraction,
    source_phase3c_locality: Mapping[str, Any],
    source_phase3c_authorization: Mapping[str, Any],
) -> SafeChainContext:
    """Historical one-call construction retained for 0.9 replay/verifiers."""

    prepared = _prepare_safe_chain_estimate_from_world(
        world,
        unrestricted_reward_upper=unrestricted_reward_upper,
        source_phase3c_locality=source_phase3c_locality,
        source_phase3c_authorization=source_phase3c_authorization,
        allow_live_evaluation_catalogue=(
            getattr(world, "bound_ground_action_records", None) is None
        ),
    )
    return _execute_safe_chain_local_preparation(prepared)


def prepare_safe_chain_estimate_context(
    frozen_world: FrozenPhase3CWorld | str | Path = DEFAULT_PHASE3C_BUNDLE,
) -> SafeChainPreparedEstimateContext:
    """Prepare one estimate from an already bound frozen Phase-3C world.

    Contract 1.0 keeps namespace/model binding outside the decision point.  A
    path is therefore rejected here instead of silently invoking the legacy
    binder, whose structural validation reads live ``actions``/``is_terminal``.
    Historical Phase 3D construction still performs that binding explicitly in
    :func:`construct_safe_chain_context`.
    """

    if not isinstance(frozen_world, FrozenPhase3CWorld):
        raise Phase3DInvariantViolation(
            "Phase 3E estimate preparation requires a prebound FrozenPhase3CWorld"
        )
    world = frozen_world
    return _prepare_safe_chain_estimate_from_world(
        world,
        unrestricted_reward_upper=world.unrestricted_reward_upper,
        source_phase3c_locality=world.source_locality_document,
        source_phase3c_authorization=world.source_authorization_document,
    )


def _audit_from_portable_sound_proof_v1(
    world: Any,
    model_only_result: Any,
    policy: FiniteHorizonPolicy[Any, Any],
) -> AbstractPolicyAudit:
    """Decode the frozen portable proof rows into Phase-3D audit bounds.

    This is a representation bridge, not a second audit.  The retained
    ``ABSTRACT_AUDIT=FAIL`` semantic authority has already replayed the
    portable sound proof.  Here we require an exact one-to-one correspondence
    between its policy rows and the decoded policy decisions, then translate
    portable cell IDs into the frozen world's construction-time cell objects.
    """

    portable_audit = model_only_result.audit
    proof = model_only_result.sound_proof
    if (
        portable_audit.outcome != "FAIL"
        or portable_audit.certified
        or not portable_audit.action_realization_complete
        or proof.proof_id != portable_audit.proof_id
    ):
        raise Phase3DInvariantViolation(
            "verified-model estimate requires a complete failed portable audit"
        )

    registry = world.portable.registry
    cells_by_id = {
        identifier: cell for cell, identifier in registry.cell_records
    }
    if len(cells_by_id) != len(registry.cell_records):
        raise Phase3DInvariantViolation("frozen cell registry has duplicate IDs")
    decisions = {
        (decision.remaining, decision.cell_id): decision.action_id
        for decision in model_only_result.selected_plan.proposal.policy.decisions
    }
    if len(decisions) != len(
        model_only_result.selected_plan.proposal.policy.decisions
    ):
        raise Phase3DInvariantViolation("portable policy decisions are duplicated")

    bounds: list[CellPolicyBound] = []
    seen: set[tuple[int, str]] = set()
    for row in proof.policy_rows:
        key = (row.remaining, row.cell_id)
        if key in seen or decisions.get(key) != row.action_id:
            raise Phase3DInvariantViolation(
                "portable proof rows do not exactly bind the selected policy"
            )
        seen.add(key)
        try:
            cell = cells_by_id[row.cell_id]
            decoded_action = policy.action(cell, row.remaining)
            decoded_action_id = registry.semantic_action_id(cell, decoded_action)
        except (KeyError, ValueError) as error:
            raise Phase3DInvariantViolation(
                "portable proof row cannot be decoded in the authorized world"
            ) from error
        if decoded_action_id != row.action_id:
            raise Phase3DInvariantViolation(
                "portable proof action differs from the decoded frozen policy"
            )
        bounds.append(
            CellPolicyBound(
                cell,
                row.remaining,
                row.reward_lower,
                row.failure_upper,
            )
        )
    if (
        seen != set(decisions)
        or len(bounds) != portable_audit.reachable_cell_horizon_pairs
    ):
        raise Phase3DInvariantViolation(
            "portable proof does not cover every reachable selected-policy pair"
        )

    bounds.sort(key=lambda item: (-item.remaining, repr(item.cell)))
    translated = AbstractPolicyAudit(
        unrestricted_reward_upper=portable_audit.unrestricted_reward_upper,
        lifted_reward_lower=portable_audit.policy_reward_lower,
        lifted_failure_upper=portable_audit.policy_failure_upper,
        regret_upper=portable_audit.regret_upper,
        regret_tolerance=portable_audit.regret_tolerance,
        risk_tolerance=portable_audit.risk_tolerance,
        certified=False,
        issues=(),
        reachable_bounds=tuple(bounds),
    )
    if (
        translated.regret_upper
        != translated.unrestricted_reward_upper - translated.lifted_reward_lower
        or len(translated.reachable_bounds)
        != portable_audit.reachable_cell_horizon_pairs
    ):
        raise Phase3DInvariantViolation(
            "translated portable proof has inconsistent root or reachability bounds"
        )
    return translated


def prepare_safe_chain_estimate_from_verified_model_failure_v1(
    ground_binding: object,
    *,
    model_only_result: object,
    abstract_audit_authority: object,
) -> SafeChainPreparedEstimateContext:
    """Continue a verified model-only ``FAIL`` into Phase-3D route estimation.

    No portable planner, abstract auditor, ground transition, materializer,
    compiler, or worker is invoked.  The opaque handoff is the sole source of
    the already-authorized ground namespace; the selected contingent plan and
    every Bellman bound are decoded from the frozen model-only result.
    """

    # Lazy imports preserve the historical Phase-3D dependency surface and
    # make the ground-handoff authority boundary explicit.
    from acfqp.phase3e_ground_handoff_v1 import (
        GroundBindingAfterFailedAuditV1,
        Phase3EGroundHandoffV1Error,
        require_ground_binding_after_failed_audit_v1,
    )
    from acfqp.phase3e_model_only_v1 import (
        ModelOnlyOutcome,
        Phase3EModelOnlyResultV1,
    )
    from acfqp.semantic_verification_v1 import (
        SemanticRole,
        SemanticVerificationResultV1,
        SemanticVerificationV1Error,
        require_semantic_verification_result_v1,
    )

    if type(model_only_result) is not Phase3EModelOnlyResultV1:
        raise Phase3DInvariantViolation(
            "verified-model estimate requires Phase3EModelOnlyResultV1"
        )
    if (
        model_only_result.outcome is not ModelOnlyOutcome.FAIL
        or model_only_result.audit.outcome != "FAIL"
        or model_only_result.ground_binding_required is not True
    ):
        raise Phase3DInvariantViolation(
            "verified-model estimate is forbidden for a PASS result"
        )
    if type(abstract_audit_authority) is not SemanticVerificationResultV1:
        raise Phase3DInvariantViolation(
            "verified-model estimate requires retained ABSTRACT_AUDIT authority"
        )
    try:
        binding = require_ground_binding_after_failed_audit_v1(ground_binding)
        verified_audit = require_semantic_verification_result_v1(
            abstract_audit_authority, SemanticRole.ABSTRACT_AUDIT
        )
    except (Phase3EGroundHandoffV1Error, SemanticVerificationV1Error) as error:
        raise Phase3DInvariantViolation(
            f"verified-model estimate authority is invalid: {error}"
        ) from error
    if type(binding) is not GroundBindingAfterFailedAuditV1:  # defensive
        raise Phase3DInvariantViolation("ground handoff has the wrong authority type")
    if verified_audit.outcome != "FAIL":
        raise Phase3DInvariantViolation(
            "verified-model estimate requires ABSTRACT_AUDIT=FAIL"
        )
    if verified_audit is not binding.semantic_authority:
        raise Phase3DInvariantViolation(
            "abstract-audit authority is foreign to the ground handoff"
        )

    # Re-derive the two ground-only identities from the retained world instead
    # of trusting the capability's public metadata.  This is a catalogue and
    # locality hash operation only; it performs no ground transition or route
    # execution.  Together with the verification-work identity below it keeps
    # the Phase-3D bridge from accepting a metadata-spliced handoff even if a
    # caller bypasses the public capability validator.
    from acfqp.phase3e_fallback_v1 import (
        safe_chain_fallback_context_identity_v1,
    )

    world = binding.world
    try:
        ground_identities = safe_chain_fallback_context_identity_v1(world)
    except (TypeError, ValueError) as error:
        raise Phase3DInvariantViolation(
            f"cannot re-derive ground handoff identities: {error}"
        ) from error

    expected_binding = {
        "model_only_result_id": model_only_result.result_id,
        "source_lease_id": model_only_result.source_lease.source_lease_id,
        "selected_plan_id": (
            model_only_result.selected_plan.selected_contingent_plan_id
        ),
        "sound_proof_id": model_only_result.sound_proof.proof_id,
        "abstract_audit_id": model_only_result.audit.audit_id,
        "abstract_audit_verification_attestation_id": (
            verified_audit.attestation.verification_attestation_id
        ),
        "verification_work_record_id": (
            verified_audit.verification_work_record.record_id
        ),
        "route_decision_context_id": (
            model_only_result.route_context.route_decision_context_id
        ),
        "structural_id": model_only_result.identities.structural_id,
        "query_id": model_only_result.identities.query_id,
        "build_epoch_id": model_only_result.identities.build_epoch_id,
        "manifest_id": model_only_result.identities.manifest_id,
        "portable_rapm_id": model_only_result.identities.portable_rapm_id,
        "bound_ground_action_catalogue_id": (
            ground_identities["bound_ground_action_catalogue_id"]
        ),
        "locality_metadata_id": ground_identities["locality_metadata_id"],
    }
    for field_name, expected in expected_binding.items():
        if getattr(binding, field_name) != expected:
            raise Phase3DInvariantViolation(
                f"ground handoff/model-only mismatch for {field_name}"
            )
    if (
        verified_audit.artifact != model_only_result.audit
        or verified_audit.binding.route_context != model_only_result.route_context
    ):
        raise Phase3DInvariantViolation(
            "retained abstract-audit authority does not own this model result"
        )

    registered = world.queries[1]
    query = registered.query
    if (
        registered.query_key != model_only_result.source_lease.query_key
        or object_id(query, "query")
        != model_only_result.source_lease.legacy_ground_query_id
        or world.portable.model.model_id
        != model_only_result.source_lease.legacy_portable_rapm_id
    ):
        raise Phase3DInvariantViolation(
            "authorized world does not contain the frozen failed query/model"
        )
    portable_query = world.portable.query_from_spec(query)
    if (
        portable_query.query_id
        != model_only_result.source_lease.legacy_portable_query_id
    ):
        raise Phase3DInvariantViolation(
            "authorized world reconstructed a different portable query"
        )
    try:
        portable_result = PortablePlanResult.from_dict(
            model_only_result.selected_plan.planner_result,
            model=world.portable.model,
            query=portable_query,
        )
        proposal = portable_result.frontier[
            model_only_result.selected_plan.selected_frontier_index
        ]
        if proposal != model_only_result.selected_plan.proposal:
            raise ValueError("selected proposal differs from the frozen plan")
        policy = FiniteHorizonPolicy.from_mapping(
            world.portable.decode_policy(proposal.policy)
        )
    except (IndexError, KeyError, TypeError, ValueError) as error:
        raise Phase3DInvariantViolation(
            f"cannot decode the frozen contingent plan: {error}"
        ) from error
    pre_audit = _audit_from_portable_sound_proof_v1(
        world, model_only_result, policy
    )
    verified_model_binding = _mint_verified_model_estimate_binding_v1(
        model_only_result=model_only_result,
        abstract_audit_authority=verified_audit,
        ground_binding=binding,
    )
    return _prepare_safe_chain_estimate_from_frozen_plan(
        world,
        query=query,
        portable_query=portable_query,
        portable_result=portable_result,
        proposal=proposal,
        proposal_source=model_only_result.selected_plan.proposal_source,
        policy=policy,
        pre_audit=pre_audit,
        source_phase3c_locality=world.source_locality_document,
        source_phase3c_authorization=world.source_authorization_document,
        verified_model_binding=verified_model_binding,
    )


def construct_safe_chain_context(
    source_bundle: str | Path = DEFAULT_PHASE3C_BUNDLE,
) -> SafeChainContext:
    """Historical 0.9 bind-and-execute entry point, retained unchanged."""

    try:
        world = load_frozen_phase3c_world(source_bundle)
    except FrozenPhase3CLoadError as error:
        raise Phase3DInvariantViolation(
            f"frozen Phase 3C source bundle is inadmissible: {error}"
        ) from error
    return _execute_safe_chain_local_preparation(
        _prepare_safe_chain_estimate_from_world(
            world,
            unrestricted_reward_upper=world.unrestricted_reward_upper,
            source_phase3c_locality=world.source_locality_document,
            source_phase3c_authorization=world.source_authorization_document,
        )
    )


def _general_request(
    *,
    occurrence_id: str,
    capability: Mapping[str, Any],
    ground_slice: Mapping[str, Any],
    limits: SearchLimits,
) -> dict[str, Any]:
    payload = {
        "schema": REQUEST_SCHEMA,
        "occurrence_id": occurrence_id,
        "frontier_id": capability["frontier_id"],
        "capability_id": capability["capability_id"],
        "slice_id": ground_slice["slice_id"],
        "capability_sha256": _input_sha256(capability),
        "slice_sha256": _input_sha256(ground_slice),
        "algorithm_id": ALGORITHM_ID,
        "selection_rule": SELECTION_RULE,
        "policy_class": POLICY_CLASS,
        "search_limits": limits.to_dict(),
    }
    return {**payload, "request_id": object_id(payload, "general-local-request")}


def _validate_general_worker_result(
    result: dict[str, Any],
    capability: dict[str, Any],
    ground_slice: dict[str, Any],
    request: dict[str, Any],
    *,
    operational_no_full_replay: bool,
) -> None:
    """Validate general-worker output, optionally replaying the full search."""

    try:
        validate_general_local_result(result)
    except (KeyError, TypeError, ValueError) as exc:
        raise Phase3DInvariantViolation(
            f"isolated general local result validation failed: {exc}"
        ) from exc

    expected_bindings = {
        "request_id": request.get("request_id"),
        "occurrence_id": request.get("occurrence_id"),
        "capability_id": capability.get("capability_id"),
        "slice_id": ground_slice.get("slice_id"),
        "frontier_id": capability.get("frontier_id"),
        "required_reward_floor": capability.get("reward_floor"),
        "allowed_failure_ceiling": capability.get("failure_ceiling"),
        "search_limits": request.get("search_limits"),
    }
    if any(result.get(field) != value for field, value in expected_bindings.items()):
        raise Phase3DInvariantViolation(
            "isolated general local result does not bind the frozen request capabilities"
        )
    if (
        ground_slice.get("frontier_id") != capability.get("frontier_id")
        or request.get("frontier_id") != capability.get("frontier_id")
        or request.get("capability_id") != capability.get("capability_id")
        or request.get("slice_id") != ground_slice.get("slice_id")
    ):
        raise Phase3DInvariantViolation(
            "general local worker inputs contain inconsistent capability bindings"
        )

    cells = {
        row.get("node_id"): row
        for row in ground_slice.get("cells", [])
        if isinstance(row, dict)
    }
    localized = set(result["localized_node_ids"])
    if not localized.issubset(cells):
        raise Phase3DInvariantViolation(
            "isolated general local result localizes outside the authorized slice"
        )
    expected_decisions = {
        (node_id, member.get("state_id"))
        for node_id in localized
        for member in cells[node_id].get("members", [])
        if isinstance(member, dict)
    }
    observed_decisions = {
        (row["node_id"], row["state_id"]) for row in result["decisions"]
    }
    if observed_decisions != expected_decisions:
        raise Phase3DInvariantViolation(
            "isolated general local result does not assign every localized member"
        )
    for decision in result["decisions"]:
        cell = cells[decision["node_id"]]
        member = next(
            (
                row
                for row in cell.get("members", [])
                if row.get("state_id") == decision["state_id"]
            ),
            None,
        )
        if (
            decision["cell"] != cell.get("cell")
            or decision["remaining"] != cell.get("remaining")
            or decision["input_port_id"] != cell.get("input_port_id")
            or member is None
            or decision["action_id"]
            not in {row.get("action_id") for row in member.get("actions", [])}
        ):
            raise Phase3DInvariantViolation(
                "isolated general local result contains an unauthorized decision"
            )

    if not operational_no_full_replay:
        replay = solve_general_local_recovery(
            capability, ground_slice, request
        ).to_dict()
        if result != replay:
            raise Phase3DInvariantViolation(
                "isolated general local result disagrees with exact replay"
            )


def _run_fresh_general_solver(
    capability: dict[str, Any],
    ground_slice: dict[str, Any],
    request: dict[str, Any],
    *,
    operational_no_full_replay: bool = False,
    runtime_source_root: Path | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Run the stdlib worker with exactly three mounted input files.

    Historical Phase 3D retains its deterministic host replay by default.
    Contract-1.0 operational consumers opt into strict validation without a
    second host-side solver search.
    """

    bubblewrap = shutil.which("bwrap")
    if bubblewrap is None:
        raise Phase3DInvariantViolation("Phase 3D general local worker requires bubblewrap")
    source_root = (
        PROJECT_ROOT / "src"
        if runtime_source_root is None
        else Path(runtime_source_root)
    )
    runtime_package = source_root / "acfqp"
    if runtime_package.is_symlink() or not runtime_package.is_dir():
        raise Phase3DInvariantViolation(
            "Phase 3D general local worker runtime source is invalid"
        )
    with tempfile.TemporaryDirectory(prefix="acfqp-phase3d-local-") as temporary:
        root = Path(temporary)
        runtime = root / "runtime"
        input_root = root / "input"
        output_root = root / "output"
        runtime.mkdir()
        input_root.mkdir()
        output_root.mkdir()
        for module_name in ("general_local_solver.py", "general_local_runtime.py"):
            source = runtime_package / module_name
            if source.is_symlink() or not source.is_file():
                raise Phase3DInvariantViolation(
                    "Phase 3D general local runtime snapshot is incomplete"
                )
            shutil.copy2(source, runtime)
        inputs = {
            "capability.json": capability,
            "slice.json": ground_slice,
            "request.json": request,
        }
        for name, document in inputs.items():
            (input_root / name).write_bytes(_canonical_bytes(document))
        result_path = output_root / "result.json"
        attestation_path = output_root / "attestation.json"
        process = subprocess.run(
            (
                bubblewrap,
                "--unshare-all",
                "--die-with-parent",
                "--new-session",
                "--clearenv",
                *_system_mounts(),
                "--proc",
                "/proc",
                "--dev",
                "/dev",
                "--tmpfs",
                "/tmp",
                "--ro-bind",
                str(runtime),
                "/runtime",
                "--ro-bind",
                str(input_root),
                "/input",
                "--dir",
                "/output",
                "--bind",
                str(output_root),
                "/output",
                "--chdir",
                "/output",
                "--setenv",
                "PATH",
                "/usr/bin:/bin",
                "--setenv",
                "LANG",
                "C.UTF-8",
                "--setenv",
                "PYTHONHASHSEED",
                "0",
                "--setenv",
                "ACFQP_FORBIDDEN_ROOTS",
                str(PROJECT_ROOT),
                _isolated_python(),
                "-B",
                "-S",
                "/runtime/general_local_runtime.py",
                "--capability",
                "/input/capability.json",
                "--slice",
                "/input/slice.json",
                "--request",
                "/input/request.json",
                "--output",
                "/output/result.json",
                "--attestation",
                "/output/attestation.json",
            ),
            cwd=output_root,
            env={"PATH": "/usr/bin:/bin"},
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=120,
            check=False,
        )
        if process.returncode != 0 or process.stdout or process.stderr:
            raise Phase3DInvariantViolation(
                "isolated general local worker failed: "
                f"rc={process.returncode}, stdout={process.stdout!r}, "
                f"stderr={process.stderr!r}"
            )
        result = json.loads(result_path.read_text(encoding="utf-8"))
        attestation = json.loads(attestation_path.read_text(encoding="utf-8"))
        _validate_general_worker_result(
            result,
            capability,
            ground_slice,
            request,
            operational_no_full_replay=operational_no_full_replay,
        )
        payload = dict(attestation)
        attestation_id = payload.pop("attestation_id", None)
        if (
            attestation_id
            != logical_id("general-local-runtime-attestation", payload)
            or payload.get("schema")
            != "acfqp.general_local_runtime_attestation.v1"
            or payload.get("request_id") != request["request_id"]
            or payload.get("capability_id") != capability["capability_id"]
            or payload.get("slice_id") != ground_slice["slice_id"]
            or payload.get("result_id") != result["result_id"]
            or payload.get("input_regular_files")
            != ["capability.json", "request.json", "slice.json"]
            or payload.get("output_regular_files_before") != []
            or payload.get("python_site_disabled") is not True
            or payload.get("project_checkout_visible") is not False
            or payload.get("network_namespace_unshared") is not True
            or payload.get("working_set_limit_bytes") != 256 * 1024 * 1024
            or payload.get("unexpected_module_origins") != []
            or payload.get("forbidden_loaded_before") != []
            or payload.get("forbidden_loaded_after") != []
        ):
            raise Phase3DInvariantViolation(
                "isolated general local runtime attestation failed"
            )
        return result, attestation


def _overlay_from_result(
    context: SafeChainContext,
    result: Mapping[str, Any],
) -> HybridPolicyOverlay:
    state_by_id = {
        object_id(state, "state"): state
        for state in context.world.coverage.covered_states
    }
    action_by_pair = {
        (object_id(state, "state"), object_id(action, "ground-action")): action
        for state, action in context.authorization.allowed_state_actions
    }
    node_by_id = {node.node_id: node for node in context.frontier.nodes}
    decisions: list[GroundPatchDecision] = []
    for row in result["decisions"]:
        try:
            node = node_by_id[row["node_id"]]
            state = state_by_id[row["state_id"]]
            action = action_by_pair[(row["state_id"], row["action_id"])]
        except KeyError as error:
            raise Phase3DInvariantViolation(
                "general local result escaped its causal authorization"
            ) from error
        decisions.append(
            GroundPatchDecision(row["remaining"], node.cell, state, action)
        )
    return HybridPolicyOverlay(
        context.policy,
        tuple(decisions),
        context.ground_query_id,
        context.frontier.frontier_id,
    )


def _causal_circuit_document(context: SafeChainContext) -> dict[str, Any]:
    circuit = context.causal_circuit
    payload = {
        "schema": "acfqp.causal_proof_circuit.v1",
        "failed_proof_graph_id": context.proof_graph.graph_id,
        "root_nodes": tuple(
            {"node_id": root.node_id, "probability": root.probability}
            for root in circuit.roots
        ),
        "nodes": tuple(
            {
                "node_id": node.node_id,
                "recoverable": node.recoverable,
                "capability_cost": node.capability_cost,
                "realizations": tuple(
                    {
                        "realization_id": realization.realization_id,
                        "immediate_reward": realization.immediate_reward,
                        "immediate_failure": realization.immediate_failure,
                        "successors": tuple(
                            {
                                "node_id": successor.node_id,
                                "probability": successor.probability,
                            }
                            for successor in realization.successors
                        ),
                    }
                    for realization in node.realizations
                ),
            }
            for node in circuit.nodes
        ),
        "candidate_scope": "earliest_DirectBad_antichain_only",
        "one_shot_multi_layer_recovery_claimed": False,
    }
    return {**payload, "circuit_id": object_id(payload, "causal-circuit")}


def _causal_search_document(
    context: SafeChainContext,
    circuit_document: Mapping[str, Any],
) -> dict[str, Any]:
    causal = context.causal_search
    obligations = (
        CertificateObligation(
            REWARD_LOWER,
            context.pre_audit.unrestricted_reward_upper
            - context.pre_audit.regret_tolerance,
        ),
        CertificateObligation(FAILURE_UPPER, context.pre_audit.risk_tolerance),
    )
    influence = []
    for node_id in causal.candidate_node_ids:
        certificate = evaluate_counterfactual_certificate(
            context.causal_circuit,
            obligations,
            (node_id,),
        )
        influence.append(
            {
                "node_id": node_id,
                "root_failure_upper": certificate.root_value(FAILURE_UPPER),
                "root_failure_gain": root_channel_gain(
                    causal.baseline, certificate, FAILURE_UPPER
                ),
                "counterfactual_certified": certificate.certified,
            }
        )

    def node_channel_values(certificate: Any) -> tuple[dict[str, Any], ...]:
        return tuple(
            {
                "node_id": value.node_id,
                "channel": value.channel,
                "pessimistic_value": value.pessimistic_value,
                "optimistic_value": value.optimistic_value,
                "selected_value": value.selected_value,
                "residual_width": value.residual_width,
                "active_realization_ids": value.active_realization_ids,
                "discharged": value.discharged,
            }
            for value in certificate.node_values
        )

    payload = {
        "schema": "acfqp.slack_aware_causal_family.v1",
        "circuit_id": circuit_document["circuit_id"],
        "status": causal.status.value,
        "evaluation_cap": causal.evaluation_cap,
        "evaluation_count": causal.evaluation_count,
        "search_complete": causal.search_complete,
        "obligations": tuple(
            {"channel": item.channel, "threshold": item.threshold}
            for item in obligations
        ),
        "baseline_root_values": causal.baseline.root_values,
        "baseline_deficits": causal.baseline.deficits,
        "baseline_active_node_ids": causal.baseline.active_node_ids,
        "baseline_node_channel_values": node_channel_values(causal.baseline),
        "candidate_node_ids": causal.candidate_node_ids,
        "minimal_cover_node_ids": causal.minimal_cover_node_ids,
        "selected_node_ids": causal.selected_node_ids,
        "selected_activation_trace": causal.selected_activation_trace,
        "excluded_candidate_node_ids": causal.excluded_candidate_node_ids,
        "singleton_root_influence": tuple(influence),
        "evaluations": tuple(
            {
                "discharged_node_ids": row.discharged_node_ids,
                "activation_trace": row.activation_trace,
                "capability_cost": row.capability_cost,
                "root_values": row.certificate.root_values,
                "deficits": row.certificate.deficits,
                "failed_channels": row.certificate.failed_channels,
                "active_node_ids": row.certificate.active_node_ids,
                "eligible_node_ids": row.certificate.eligible_node_ids,
                "node_channel_values": node_channel_values(row.certificate),
                "certified": row.certificate.certified,
            }
            for row in causal.evaluations
        ),
        "counterfactual_is_final_certificate": False,
        "post_recovery_full_audit_required": True,
    }
    return {**payload, "causal_search_id": object_id(payload, "causal-search")}


def _authorization_document(
    context: SafeChainContext,
    accounting: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    authorization = context.authorization
    accounting = _authority_accounting(context) if accounting is None else accounting
    phase3d_counts = accounting["phase3d"]

    def records(pairs: tuple[tuple[Hashable, Hashable], ...]) -> tuple[dict[str, str], ...]:
        return tuple(
            {
                "state_id": object_id(state, "state"),
                "action_id": object_id(action, "ground-action"),
            }
            for state, action in pairs
        )

    frontier = records(authorization.frontier_state_actions)
    ancestors = records(authorization.reverse_dependency_state_actions)
    return {
        "schema": "acfqp.local_recovery_authorization.phase3d.v1",
        "authorization_id": authorization.authorization_id,
        "frontier_id": authorization.frontier_id,
        "ground_query_id": context.ground_query_id,
        "frontier_state_actions": frontier,
        "strict_ancestor_selected_state_actions": ancestors,
        "frontier_state_action_count": phase3d_counts["frontier_state_actions"],
        "ancestor_state_action_count": phase3d_counts["ancestor_state_actions"],
        "authorized_state_action_count": phase3d_counts["authorized_state_actions"],
        "frontier_positive_outcome_count": phase3d_counts[
            "frontier_positive_outcomes"
        ],
        "ancestor_positive_outcome_count": phase3d_counts[
            "ancestor_positive_outcomes"
        ],
        "authorized_positive_outcome_count": phase3d_counts[
            "authorized_positive_outcomes"
        ],
        "candidate_scope": "slack_aware_subset_of_earliest_DirectBad_antichain",
        "full_ground_model_or_j0_allowed": False,
    }


def _overlay_document(
    context: SafeChainContext,
    overlay: HybridPolicyOverlay,
    result: Mapping[str, Any],
) -> dict[str, Any]:
    payload = {
        "schema": "acfqp.hybrid_policy_overlay.phase3d.v1",
        "overlay_id": overlay.overlay_id,
        "ground_query_id": context.ground_query_id,
        "frontier_id": context.frontier.frontier_id,
        "local_result_id": result["result_id"],
        "base_policy_signature": context.policy.signature(),
        "decisions": tuple(
            {
                "remaining": decision.remaining,
                "cell": repr(decision.cell),
                "state_id": object_id(decision.state, "state"),
                "action_id": object_id(decision.action, "ground-action"),
            }
            for decision in overlay.decisions
        ),
        "base_rapm_mutated": False,
        "query_owned": True,
    }
    return payload


def _synthetic_tradeoff_documents() -> dict[str, dict[str, Any]]:
    """Build the algebraic control that defeats independent min-risk choice."""

    frontier_id = object_id(
        {"profile": PROFILE_KEY, "control": "joint-pareto-tradeoff"},
        "synthetic-frontier",
    )
    node_ids = tuple(
        object_id({"synthetic_cell": name}, "proof-node") for name in ("left", "right")
    )
    state_ids = {
        node_id: tuple(
            object_id({"node_id": node_id, "member": index}, "state")
            for index in range(2)
        )
        for node_id in node_ids
    }

    def action(node_id: str, state_id: str, kind: str) -> dict[str, Any]:
        high = kind == "high"
        return {
            "action_id": object_id(
                {"node_id": node_id, "state_id": state_id, "kind": kind},
                "ground-action",
            ),
            "immediate_reward": _fraction_json(1 if high else 0),
            "failure_probability": _fraction_json(
                Fraction(1, 25) if high else 0
            ),
            "termination_probability": _fraction_json(1),
            "exits": [],
        }

    cells = []
    for node_id in sorted(node_ids):
        cells.append(
            {
                "node_id": node_id,
                "cell": f"synthetic:{node_id}",
                "remaining": 1,
                "input_port_id": node_id,
                "members": [
                    {
                        "state_id": state_id,
                        "actions": sorted(
                            (
                                action(node_id, state_id, "low"),
                                action(node_id, state_id, "high"),
                            ),
                            key=lambda row: row["action_id"],
                        ),
                    }
                    for state_id in sorted(state_ids[node_id])
                ],
            }
        )
    slice_payload = {
        "schema": "acfqp.sparse_frontier_ground_slice.v1",
        "authorization_id": object_id(
            {"frontier_id": frontier_id, "node_ids": node_ids},
            "synthetic-authorization",
        ),
        "frontier_id": frontier_id,
        "cells": cells,
    }
    ground_slice = {
        **slice_payload,
        "slice_id": object_id(slice_payload, "sparse-frontier-ground-slice"),
    }
    root_form = SparseAffineForm.create(
        Fraction(0),
        {node_id: Fraction(1, 2) for node_id in node_ids},
    )
    capability_payload = {
        "schema": CAPABILITY_SCHEMA,
        "frontier_id": frontier_id,
        "reward_floor": _fraction_json(Fraction(3, 4)),
        "failure_ceiling": _fraction_json(Fraction(1, 20)),
        "input_ports": [
            {
                "port_id": node_id,
                "default_reward_lower": _fraction_json(0),
                "default_failure_upper": _fraction_json(0),
            }
            for node_id in node_ids
        ],
        "exit_ports": [],
        "root_reward_forms": [root_form.to_dict()],
        "root_failure_forms": [root_form.to_dict()],
    }
    capability = {
        **capability_payload,
        "capability_id": logical_id(
            "sparse-robust-affine-capability", capability_payload
        ),
    }
    parse_sparse_capability(capability)
    occurrence_id = object_id(
        {"frontier_id": frontier_id, "control": "joint-pareto"},
        "occurrence",
    )
    request = _general_request(
        occurrence_id=occurrence_id,
        capability=capability,
        ground_slice=ground_slice,
        limits=SYNTHETIC_SEARCH_LIMITS,
    )
    result = solve_general_local_recovery(
        capability, ground_slice, request
    ).to_dict()
    if (
        result["status"] != CERTIFIED
        or result["localized_node_ids"] != list(node_ids)
        or len(result["decisions"]) != 4
        or result["root_reward_lower"] != _fraction_json(1)
        or result["root_failure_upper"] != _fraction_json(Fraction(1, 25))
        or result["theoretical_total_policy_space"] != 25
        or result["counters"]["policy_assignments"] != 25
    ):
        raise Phase3DInvariantViolation("joint Pareto synthetic golden changed")

    legacy_decisions = tuple(
        {
            "node_id": cell["node_id"],
            "state_id": member["state_id"],
            "action_id": next(
                action_row["action_id"]
                for action_row in member["actions"]
                if action_row["failure_probability"] == _fraction_json(0)
            ),
        }
        for cell in cells
        for member in cell["members"]
    )
    legacy = {
        "schema": "acfqp.legacy_greedy_counterexample.v1",
        "selection_rule": "independent_minimum_failure_then_maximum_reward",
        "decisions": legacy_decisions,
        "root_reward_lower": _fraction_json(0),
        "root_failure_upper": _fraction_json(0),
        "certified_safe": True,
        "certified_value": False,
        "misses_existing_joint_certificate": True,
    }
    problem = {
        "schema": "acfqp.joint_tradeoff_problem.v1",
        "profile_key": "synthetic.two_cell_two_member.tradeoff.v1",
        "frontier_id": frontier_id,
        "policy_class": POLICY_CLASS,
        "cell_count": 2,
        "members_per_cell": 2,
        "actions_per_member": 2,
        "low_action_pair": {
            "reward": _fraction_json(0),
            "failure": _fraction_json(0),
        },
        "high_action_pair": {
            "reward": _fraction_json(1),
            "failure": _fraction_json(Fraction(1, 25)),
        },
        "root_cell_masses": [_fraction_json(Fraction(1, 2))] * 2,
        "required_reward_floor": _fraction_json(Fraction(3, 4)),
        "allowed_failure_ceiling": _fraction_json(Fraction(1, 20)),
        "expected_minimum_localized_cells": 2,
        "expected_joint_policy": "all_four_high_actions",
    }

    capped_limits = copy.deepcopy(SYNTHETIC_SEARCH_LIMITS.to_dict())
    capped_limits["max_policy_assignments"] = 1
    capped_payload = dict(request)
    capped_payload.pop("request_id")
    capped_payload["search_limits"] = capped_limits
    capped_request = {
        **capped_payload,
        "request_id": object_id(capped_payload, "general-local-request"),
    }
    capped = solve_general_local_recovery(
        capability, ground_slice, capped_request
    ).to_dict()
    if (
        capped["status"] != SEARCH_CAP_EXHAUSTED
        or capped["cap_reason"] != "max_policy_assignments"
        or capped["search_complete"]
    ):
        raise Phase3DInvariantViolation("joint solver cap status changed")
    return {
        "problem": problem,
        "capability": capability,
        "ground_slice": ground_slice,
        "request": request,
        "result": result,
        "legacy": legacy,
        "capped_result": capped,
    }


def _safe_chain_attacks(
    context: SafeChainContext,
    request: Mapping[str, Any],
    result: Mapping[str, Any],
    synthetic: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    capability_extra_field_rejected = False
    forged_capability = copy.deepcopy(context.capability)
    forged_capability["graph_id"] = context.proof_graph.graph_id
    try:
        parse_sparse_capability(forged_capability)
    except ValueError:
        capability_extra_field_rejected = True

    result_derived_field_rejected = False
    forged_result = copy.deepcopy(result)
    forged_result["certified"] = False
    try:
        validate_general_local_result(forged_result)
    except ValueError:
        result_derived_field_rejected = True

    causal_cap = find_slack_aware_causal_family(
        context.causal_circuit,
        (
            CertificateObligation(
                REWARD_LOWER,
                context.pre_audit.unrestricted_reward_upper
                - context.pre_audit.regret_tolerance,
            ),
            CertificateObligation(
                FAILURE_UPPER, context.pre_audit.risk_tolerance
            ),
        ),
        max_evaluations=1,
    )
    payload = {
        "schema": "acfqp.general_local_attacks.phase3d.v1",
        "cases": (
            {
                "case": "reachable_but_slack_insufficient_rare_residual",
                "passed": len(context.causal_search.excluded_candidate_node_ids) == 1,
                "expected": "excluded_from_selected_causal_capability",
            },
            {
                "case": "causal_search_cap",
                "passed": (
                    causal_cap.status is CausalSearchStatus.SEARCH_CAP_REACHED
                    and not causal_cap.search_complete
                    and causal_cap.selected_node_ids is None
                ),
                "expected": "SEARCH_CAP_REACHED_without_provisional_frontier",
            },
            {
                "case": "worker_capability_extra_trusted_metadata",
                "passed": capability_extra_field_rejected,
                "expected": "exact_field_rejection",
            },
            {
                "case": "derived_result_field_forgery",
                "passed": result_derived_field_rejected,
                "expected": "content_or_semantic_validation_rejection",
            },
            {
                "case": "independent_minimum_risk_action_selection",
                "passed": synthetic["legacy"]["misses_existing_joint_certificate"],
                "expected": "joint_search_succeeds_while_legacy_value_fails",
            },
            {
                "case": "joint_search_policy_assignment_cap",
                "passed": (
                    synthetic["capped_result"]["status"]
                    == SEARCH_CAP_EXHAUSTED
                    and not synthetic["capped_result"]["search_complete"]
                ),
                "expected": "LOCAL_RECOVERY_SEARCH_CAP_EXHAUSTED_not_infeasible",
            },
        ),
        "request_id": request["request_id"],
        "all_passed": True,
    }
    payload["all_passed"] = all(row["passed"] for row in payload["cases"])
    if not payload["all_passed"]:
        raise Phase3DInvariantViolation("general local attack matrix failed")
    return {**payload, "attack_report_id": object_id(payload, "attack-report")}


def _pre_certificate_document(context: SafeChainContext) -> dict[str, Any]:
    policy_graph_id = object_id(
        {
            "portable_model_id": context.world.portable.model.model_id,
            "ground_query_id": context.ground_query_id,
            "policy_signature": context.policy.signature(),
        },
        "policy-graph",
    )
    document = _audit_document(
        audit=context.pre_audit,
        query_key=context.world.queries[1].query_key,
        query_id=context.ground_query_id,
        policy_graph_id=policy_graph_id,
        model_id=context.world.portable.model.model_id,
        stage="phase3d_pre_recovery",
    )
    return {
        "schema": "acfqp.pre_certificate.phase3d.v1",
        **document,
        "proposal_source": context.proposal_source,
        "ground_j0_used": False,
    }


def run_phase3d(
    output_dir: Path,
    phase3c_bundle: str | Path = DEFAULT_PHASE3C_BUNDLE,
) -> dict[str, Any]:
    """Execute, freeze, and integrity-check the contract-0.9 Gate."""

    started_at = _utc_now()
    context = construct_safe_chain_context(phase3c_bundle)
    if not isinstance(context.world, FrozenPhase3CWorld):
        raise Phase3DInvariantViolation(
            "operational Phase 3D must consume a frozen Phase 3C artifact bundle"
        )
    model_document = context.world.portable.model.to_dict()
    base_model_sha256 = context.world.portable_rapm_source_sha256
    base_epoch_sha256 = context.world.build_epoch_source_sha256
    if (
        serialized_json_sha256(model_document) != base_model_sha256
        or serialized_json_sha256(context.world.build_epoch) != base_epoch_sha256
    ):
        raise Phase3DInvariantViolation(
            "loaded Phase 3C source bytes differ from the bound model objects"
        )

    safe_occurrence_id = object_id(
        {
            "profile_key": PROFILE_KEY,
            "ground_query_id": context.ground_query_id,
            "frontier_id": context.frontier.frontier_id,
            "capability_id": context.capability["capability_id"],
        },
        "occurrence",
    )
    request = _general_request(
        occurrence_id=safe_occurrence_id,
        capability=context.capability,
        ground_slice=context.sparse_slice,
        limits=SAFE_CHAIN_SEARCH_LIMITS,
    )
    result, runtime_attestation = _run_fresh_general_solver(
        context.capability,
        context.sparse_slice,
        request,
    )
    if (
        result["status"] != CERTIFIED
        or result["localized_node_ids"]
        != list(context.causal_search.selected_node_ids or ())
        or len(result["decisions"]) != 8
        or result["root_reward_lower"] != _fraction_json(Fraction(3, 64))
        or result["root_failure_upper"] != _fraction_json(Fraction(397, 20000))
        or result["candidate_subset_count"] != 2
        or result["theoretical_total_policy_space"] != 257
        or result["counters"]["policy_assignments"] != 257
        or not result["search_complete"]
        or not result["minimality_proven"]
    ):
        raise Phase3DInvariantViolation("safe-chain joint solver golden changed")

    overlay = _overlay_from_result(context, result)
    post_audit_kernel = PatchedAuditKernelView(
        context.world.kernel,
        tuple((decision.state, decision.action) for decision in overlay.decisions),
    )
    post_audit = audit_hybrid_policy(
        post_audit_kernel,
        context.query,
        context.world.models.envelope,
        overlay,
        regret_tolerance=Fraction(1, 20),
        unrestricted_reward_upper=context.unrestricted_reward_upper,
    )
    if (
        not post_audit.certified
        or post_audit.lifted_reward_lower != Fraction(3, 64)
        or post_audit.lifted_failure_upper != Fraction(397, 20000)
        or post_audit.regret_upper != 0
    ):
        raise Phase3DInvariantViolation("safe-chain full post-audit golden changed")
    post_audit_access_log = post_audit_kernel.access_log
    post_audit_step_ids = {
        (record.state_id, record.action_id)
        for record in post_audit_access_log
        if record.operation == "step"
    }
    overlay_ids = {
        (object_id(decision.state, "state"), object_id(decision.action, "ground-action"))
        for decision in overlay.decisions
    }
    if (
        sum(record.operation == "actions" for record in post_audit_access_log) != 16
        or sum(record.operation == "step" for record in post_audit_access_log) != 8
        or post_audit_step_ids != overlay_ids
    ):
        raise Phase3DInvariantViolation(
            "post-audit ground access is not exactly the frozen overlay"
        )
    if (
        serialized_json_sha256(context.world.portable.model.to_dict())
        != base_model_sha256
        or serialized_json_sha256(context.world.build_epoch) != base_epoch_sha256
    ):
        raise Phase3DInvariantViolation("Phase 3D mutated the reusable base model")

    synthetic = _synthetic_tradeoff_documents()
    attacks = _safe_chain_attacks(context, request, result, synthetic)
    accounting = _authority_accounting(context)
    circuit_document = _causal_circuit_document(context)
    causal_document = _causal_search_document(context, circuit_document)
    authorization_document = _authorization_document(context, accounting)
    pre_document = _pre_certificate_document(context)
    overlay_document = _overlay_document(context, overlay, result)
    post_document = {
        "schema": "acfqp.post_certificate.phase3d.v1",
        "overlay_id": overlay.overlay_id,
        "local_result_id": result["result_id"],
        "unrestricted_reward_upper": post_audit.unrestricted_reward_upper,
        "lifted_reward_lower": post_audit.lifted_reward_lower,
        "lifted_failure_upper": post_audit.lifted_failure_upper,
        "regret_upper": post_audit.regret_upper,
        "regret_tolerance": post_audit.regret_tolerance,
        "risk_tolerance": post_audit.risk_tolerance,
        "exact_hybrid_evaluation_status": (
            "EVALUATION_ONLY_NOT_RUN_IN_OPERATIONAL_RUNNER"
        ),
        "exact_hybrid_reward": None,
        "exact_hybrid_failure": None,
        "patched_decision_count": len(overlay.decisions),
        "abstract_decision_count": None,
        "certified": post_audit.certified,
        "full_authority_replay": True,
        "ground_j0_used": False,
    }
    source_boundary_bytes = len(_canonical_bytes(context.source_boundary))
    capability_bytes = len(_canonical_bytes(context.capability))
    locality = {
        "schema": "acfqp.locality_audit.phase3d.v1",
        "phase3c_direct_frontier_state_actions": accounting["phase3c"][
            "frontier_state_actions"
        ],
        "phase3c_total_authorized_state_actions": accounting["phase3c"][
            "authorized_state_actions"
        ],
        "phase3c_total_authorized_outcomes": accounting["phase3c"][
            "authorized_positive_outcomes"
        ],
        "phase3d_causal_frontier_state_actions": accounting["phase3d"][
            "frontier_state_actions"
        ],
        "phase3d_total_authorized_state_actions": accounting["phase3d"][
            "authorized_state_actions"
        ],
        "phase3d_total_authorized_outcomes": accounting["phase3d"][
            "authorized_positive_outcomes"
        ],
        "state_action_authorization_reduction": Fraction(2, 5),
        "outcome_authorization_reduction": Fraction(2, 5),
        "same_query_all_action_state_actions": accounting[
            "same_query_all_action"
        ]["state_action_pairs"],
        "coverage_state_actions": accounting["coverage"]["state_actions"],
        "strict_query_locality": accounting["phase3d"]["authorized_state_actions"]
        < accounting["same_query_all_action"]["state_action_pairs"],
        "strict_build_locality": accounting["phase3d"]["authorized_state_actions"]
        < accounting["coverage"]["state_actions"],
        "source_boundary_nodes": 4,
        "source_boundary_realization_rows": 20,
        "worker_input_ports": len(context.capability["input_ports"]),
        "worker_exit_ports": len(context.capability["exit_ports"]),
        "worker_reward_forms": len(context.capability["root_reward_forms"]),
        "worker_failure_forms": len(context.capability["root_failure_forms"]),
        "source_boundary_canonical_bytes": source_boundary_bytes,
        "worker_capability_canonical_bytes": capability_bytes,
        "boundary_byte_reduction": Fraction(
            source_boundary_bytes - capability_bytes,
            source_boundary_bytes,
        ),
        "finite_domain_extensional_sufficiency": True,
        "finite_domain_representation_minimality": True,
        "information_theoretic_minimality_claimed": False,
        "base_rapm_immutable": True,
        "base_model_sha256_before": base_model_sha256,
        "base_model_sha256_after": serialized_json_sha256(
            context.world.portable.model.to_dict()
        ),
        "base_epoch_sha256_before": base_epoch_sha256,
        "base_epoch_sha256_after": serialized_json_sha256(
            context.world.build_epoch
        ),
        "operational_rapm_builder_invocations": 0,
        "operational_transition_closure_invocations": 0,
        "operational_ground_steps_before_local_authorization": 0,
        "operational_authorized_frontier_materialization_step_calls": (
            context.materialization_counts["state_action_steps"]
        ),
        "operational_authorized_frontier_materialization_positive_outcomes": (
            context.materialization_counts["positive_probability_outcomes"]
        ),
        "operational_patched_post_audit_step_calls": sum(
            record.operation == "step" for record in post_audit_access_log
        ),
        "operational_total_ground_step_calls": (
            context.materialization_counts["state_action_steps"]
            + sum(
                record.operation == "step" for record in post_audit_access_log
            )
        ),
        "operational_ground_steps_for_accounting": 0,
        "operational_ground_steps_outside_authorized_or_patched_cells": 0,
        "evaluation_only_exact_hybrid_ground_replay_invocations": 0,
    }

    base_identity = {
        "schema": "acfqp.base_identity.phase3d.v1",
        "portable_model_id": context.world.portable.model.model_id,
        "portable_model_sha256": base_model_sha256,
        "build_epoch_id": context.world.build_epoch["build_epoch_id"],
        "build_epoch_sha256": base_epoch_sha256,
        "coverage_id": context.world.portable.model.coverage_id,
        "source_profile": "phase3c_certificate_triggered_local_recovery_v0",
        "source_contract_version": "0.8.0",
        "source_run_id": context.world.source_run_document["run_id"],
        "source_semantic_hash": context.world.source_run_document["semantic_hash"],
        "source_manifest_sha256": context.world.source_manifest_sha256,
        "source_locality_sha256": serialized_json_sha256(
            context.world.source_locality_document
        ),
        "source_authorization_sha256": serialized_json_sha256(
            context.world.source_authorization_document
        ),
        "source_bundle_integrity_verified": True,
        "binding_mode": "finite_structural_id_scan_without_transitions",
        "binding_counters": context.world.binding_counters,
        "frozen_unrestricted_reward_upper": context.unrestricted_reward_upper,
        "rapm_builder_invocations": 0,
        "partition_builder_invocations": 0,
        "quotient_builder_invocations": 0,
        "transition_closure_invocations": 0,
        "kernel_step_invocations_during_binding": 0,
        "reused_without_mutation": True,
    }
    profile = {
        "schema": "acfqp.general_local_recovery_profile.phase3d.v1",
        "profile_key": PROFILE_KEY,
        "execution_profile": EXECUTION_PROFILE,
        "contract_version": CONTRACT_VERSION,
        "policy_class": POLICY_CLASS,
        "causal_candidate_scope": "earliest_DirectBad_antichain",
        "causal_search_evaluation_cap": CAUSAL_EVALUATION_CAP,
        "compiler_limits": COMPILER_LIMITS,
        "safe_chain_search_limits": SAFE_CHAIN_SEARCH_LIMITS.to_dict(),
        "synthetic_search_limits": SYNTHETIC_SEARCH_LIMITS.to_dict(),
        "worker_inputs": ["capability.json", "request.json", "slice.json"],
        "joint_search_completeness_scope": (
            "finite deterministic overlays over the authorized antichain; "
            "fixed abstract policy and scalar exits elsewhere; only when caps complete"
        ),
        "deeper_causal_recovery_rule": (
            "full post-audit then a new occurrence-bound transaction"
        ),
        "base_model_source": "verified_frozen_phase3c_artifact_bundle",
        "operational_rebuild_forbidden": True,
        "unrestricted_upper_source": "content_addressed_phase3c_pre_certificate",
        "ground_authority_accounting_source": (
            "verified_phase3c_locality_plus_authorized_slice_materialization"
        ),
        "independent_verifier_rebuild_is_evaluation_only": True,
        "operational_exact_hybrid_ground_replay_forbidden": True,
        "j0_authority": "not_mounted_or_invoked",
        "supported_claims": SUPPORTED_CLAIMS,
        "unsupported_claims": UNSUPPORTED_CLAIMS,
    }
    compiler_counts = context.capability_evidence["recovery_input_compilation"][
        "counts"
    ]
    work = {
        "schema": "acfqp.work_counters.phase3d.v1",
        "safe_chain": {
            "causal_evaluations": context.causal_search.evaluation_count,
            "authorized_state_action_pairs": accounting["phase3d"][
                "authorized_state_actions"
            ],
            "authorized_outcomes": accounting["phase3d"][
                "authorized_positive_outcomes"
            ],
            "frontier_worker_state_action_pairs": accounting["phase3d"][
                "frontier_state_actions"
            ],
            "frontier_worker_outcomes": accounting["phase3d"][
                "frontier_positive_outcomes"
            ],
            "trusted_frontier_materialization": {
                "step_calls": context.materialization_counts[
                    "state_action_steps"
                ],
                "positive_probability_outcomes": context.materialization_counts[
                    "positive_probability_outcomes"
                ],
                "extra_accounting_step_calls": 0,
            },
            "sound_post_audit": {
                "patched_action_checks": sum(
                    record.operation == "actions"
                    for record in post_audit_access_log
                ),
                "patched_step_calls": sum(
                    record.operation == "step" for record in post_audit_access_log
                ),
                "outside_patch_step_calls": 0,
            },
            "compiler": {
                **context.capability_evidence["enumeration"],
                "recovery_input_counts": compiler_counts,
            },
            "joint_solver": result["counters"],
            "joint_theoretical_policy_space": result[
                "theoretical_total_policy_space"
            ],
        },
        "synthetic": {
            "joint_solver": synthetic["result"]["counters"],
            "joint_theoretical_policy_space": synthetic["result"][
                "theoretical_total_policy_space"
            ],
        },
        "model_binding": context.world.binding_counters,
        "ground_j0_invocations": 0,
        "evaluation_only_exact_hybrid_ground_replay_invocations": 0,
        "ground_fallback_invocations": 0,
        "rapm_rebuilds": 0,
    }
    report_payload = {
        "schema": "acfqp.phase3d_report.v1",
        "profile_key": PROFILE_KEY,
        "status": PHASE3D_PASS,
        "general_local_recovery_gate_status": GENERAL_LOCAL_GATE_PASS,
        "full_phase3_gate_status": FULL_PHASE3_NOT_RUN,
        "workload_economics_gate_status": ECONOMICS_NOT_RUN,
        "resolved_risks": ("V0-RISK-004", "V0-RISK-005", "V0-RISK-006"),
        "safe_chain": {
            "baseline_failure_upper": Fraction(5099, 10000),
            "selected_causal_failure_upper": Fraction(397, 20000),
            "selected_causal_nodes": 1,
            "excluded_direct_bad_nodes": 1,
            "authorized_state_action_pairs": accounting["phase3d"][
                "authorized_state_actions"
            ],
            "authorized_outcomes": accounting["phase3d"][
                "authorized_positive_outcomes"
            ],
            "root_reward_lower": Fraction(3, 64),
            "root_failure_upper": Fraction(397, 20000),
            "exact_hybrid_evaluation_status": (
                "EVALUATION_ONLY_NOT_RUN_IN_OPERATIONAL_RUNNER"
            ),
            "exact_hybrid_failure": None,
            "patched_decisions": 8,
            "retained_abstract_decisions": None,
        },
        "synthetic_joint_tradeoff": {
            "legacy_certified_value": False,
            "joint_search_certified": True,
            "minimum_localized_cells": 2,
            "root_reward_lower": Fraction(1),
            "root_failure_upper": Fraction(1, 25),
        },
        "base_rapm_immutable": True,
        "fallback_count": 0,
        "rebuild_count": 0,
        "j0_invocations": 0,
        "supported_claims": SUPPORTED_CLAIMS,
        "unsupported_claims": UNSUPPORTED_CLAIMS,
    }
    report = {
        **report_payload,
        "report_id": object_id(report_payload, "phase3d-report"),
    }
    metrics = {
        "schema": "acfqp.metrics.phase3d.v1",
        "status": PHASE3D_PASS,
        "causal_candidate_nodes": len(context.causal_search.candidate_node_ids),
        "causal_selected_nodes": len(
            context.causal_search.selected_node_ids or ()
        ),
        "causal_excluded_nodes": len(
            context.causal_search.excluded_candidate_node_ids
        ),
        "authorization_pairs_before": accounting["phase3c"][
            "authorized_state_actions"
        ],
        "authorization_pairs_after": accounting["phase3d"][
            "authorized_state_actions"
        ],
        "boundary_rows_before": 20,
        "capability_input_ports_after": 1,
        "safe_chain_policy_assignments": result["counters"][
            "policy_assignments"
        ],
        "synthetic_policy_assignments": synthetic["result"]["counters"][
            "policy_assignments"
        ],
    }
    events = (
        {
            "sequence": 1,
            "event": "verified_frozen_phase3c_bundle_consumed_and_bound",
        },
        {"sequence": 2, "event": "abstract_plan_certificate_failed"},
        {"sequence": 3, "event": "exact_causal_circuit_frozen"},
        {"sequence": 4, "event": "slack_aware_causal_family_completed"},
        {"sequence": 5, "event": "strict_causal_authorization_frozen"},
        {"sequence": 6, "event": "sparse_worker_capability_compiled"},
        {"sequence": 7, "event": "isolated_joint_value_risk_search_completed"},
        {"sequence": 8, "event": "hybrid_overlay_frozen"},
        {"sequence": 9, "event": "full_authority_post_audit_passed"},
        {"sequence": 10, "event": "synthetic_joint_tradeoff_control_passed"},
        {"sequence": 11, "event": "general_local_recovery_gate_frozen"},
    )

    documents: dict[str, Any] = {
        "contract/profile.json": profile,
        "safe_chain/base_identity.json": base_identity,
        "safe_chain/base_portable_rapm.json": model_document,
        "safe_chain/base_build_epoch.json": context.world.build_epoch,
        "safe_chain/source_phase3c_run.json": context.world.source_run_document,
        "safe_chain/source_phase3c_manifest.json": (
            context.world.source_manifest_document
        ),
        "safe_chain/source_phase3c_local_pre_certificate.json": (
            context.world.local_pre_recovery_document
        ),
        "safe_chain/source_phase3c_locality.json": (
            context.world.source_locality_document
        ),
        "safe_chain/source_phase3c_authorization.json": (
            context.world.source_authorization_document
        ),
        "safe_chain/pre_certificate.json": pre_document,
        "safe_chain/causal_circuit.json": circuit_document,
        "safe_chain/causal_search.json": causal_document,
        "safe_chain/authorization.json": authorization_document,
        "safe_chain/ground_slice.json": context.sparse_slice,
        "safe_chain/source_boundary.json": context.source_boundary,
        "safe_chain/capability.json": context.capability,
        "safe_chain/capability_evidence.json": context.capability_evidence,
        "safe_chain/request.json": request,
        "safe_chain/runtime_attestation.json": runtime_attestation,
        "safe_chain/result.json": result,
        "safe_chain/overlay.json": overlay_document,
        "safe_chain/post_certificate.json": post_document,
        "safe_chain/locality.json": locality,
        "synthetic/tradeoff_problem.json": synthetic["problem"],
        "synthetic/capability.json": synthetic["capability"],
        "synthetic/ground_slice.json": synthetic["ground_slice"],
        "synthetic/request.json": synthetic["request"],
        "synthetic/result.json": synthetic["result"],
        "synthetic/legacy_greedy.json": synthetic["legacy"],
        "attacks/regressions.json": attacks,
        "accounting/work_counters.json": work,
        "result/phase3d_report.json": report,
        "metrics.json": metrics,
        "events.jsonl": events,
    }
    semantic_hash = canonical_sha256(documents)
    finished_at = _utc_now()
    run_payload = {
        "schema": "acfqp.run.phase3d.v1",
        "schema_version": "phase3d.v1",
        "profile_key": PROFILE_KEY,
        "execution_profile": EXECUTION_PROFILE,
        "contract_version": CONTRACT_VERSION,
        "status": PHASE3D_PASS,
        "general_local_recovery_gate_status": GENERAL_LOCAL_GATE_PASS,
        "full_phase3_gate_status": FULL_PHASE3_NOT_RUN,
        "workload_economics_gate_status": ECONOMICS_NOT_RUN,
        "semantic_hash": semantic_hash,
        "required_paths": PHASE3D_REQUIRED_PATHS,
        "started_at": started_at,
        "finished_at": finished_at,
    }
    run_id_payload = {
        key: value
        for key, value in run_payload.items()
        if key not in {"started_at", "finished_at"}
    }
    documents["run.json"] = {
        **run_payload,
        "run_id": object_id(run_id_payload, "run"),
    }
    write_artifact_bundle(
        output_dir,
        documents,
        required_paths=PHASE3D_REQUIRED_PATHS,
    )
    source_records = {
        row["path"]: row for row in context.world.source_manifest_document["files"]
    }
    if (
        (output_dir / "safe_chain/base_portable_rapm.json").read_bytes()
        != context.world.portable_rapm_source_bytes
        or (output_dir / "safe_chain/base_build_epoch.json").read_bytes()
        != context.world.build_epoch_source_bytes
        or sha256_file(output_dir / "safe_chain/source_phase3c_manifest.json")
        != context.world.source_manifest_sha256
        or sha256_file(output_dir / "safe_chain/source_phase3c_locality.json")
        != source_records["evaluation/locality.json"]["sha256"]
        or sha256_file(
            output_dir / "safe_chain/source_phase3c_authorization.json"
        )
        != source_records["recovery/authorization.json"]["sha256"]
    ):
        raise Phase3DInvariantViolation(
            "Phase 3D did not preserve the consumed Phase 3C source documents"
        )
    integrity = verify_artifact_bundle(output_dir)
    if integrity:
        raise Phase3DInvariantViolation(
            f"Phase 3D bundle failed integrity verification: {integrity!r}"
        )
    return {
        "status": PHASE3D_PASS,
        "general_local_recovery_gate_status": GENERAL_LOCAL_GATE_PASS,
        "full_phase3_gate_status": FULL_PHASE3_NOT_RUN,
        "workload_economics_gate_status": ECONOMICS_NOT_RUN,
        "run_id": documents["run.json"]["run_id"],
        "semantic_hash": semantic_hash,
        "manifest_sha256": sha256_file(output_dir / "manifest.json"),
        "output_dir": str(output_dir),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("artifacts/phase3d"))
    parser.add_argument(
        "--phase3c-bundle",
        type=Path,
        default=DEFAULT_PHASE3C_BUNDLE,
        help="verified Phase 3C artifact bundle to consume without rebuilding",
    )
    arguments = parser.parse_args(argv)
    try:
        summary = run_phase3d(arguments.output, arguments.phase3c_bundle)
    except Phase3DInvariantViolation as error:
        print(
            json.dumps(
                {"status": error.status, "detail": str(error)},
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 2
    print(json.dumps(to_jsonable(summary), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "CONTRACT_VERSION",
    "DEFAULT_PHASE3C_BUNDLE",
    "ECONOMICS_NOT_RUN",
    "EXECUTION_PROFILE",
    "FULL_PHASE3_NOT_RUN",
    "GENERAL_LOCAL_GATE_PASS",
    "PHASE3D_PASS",
    "PROFILE_KEY",
    "Phase3DInvariantViolation",
    "SafeChainContext",
    "SafeChainPreparedEstimateContext",
    "VerifiedModelEstimateBindingV1",
    "construct_safe_chain_context",
    "prepare_safe_chain_estimate_context",
    "prepare_safe_chain_estimate_from_verified_model_failure_v1",
    "require_safe_chain_prepared_estimate_context_v1",
    "require_verified_model_estimate_binding_v1",
    "run_phase3d",
]
