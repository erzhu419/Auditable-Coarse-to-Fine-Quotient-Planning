"""Anchor-gated held-out graph transition observations for V0-072.

This is a new observer authority for the preregistered seven-vertex target
family.  It intentionally does not import or extend the V0-068 observer
registry, types, streams, or content domains.

The public side exposes only the already-preregistered graph contexts,
symbolic states, complete legal-action catalogues, support-epoch identities,
and opaque observed transition tuples.  Spawn laws remain in the separately
frozen environment manifest.  Exact atoms are available only through the
explicit evaluation-only API.

No registered target stream can currently be opened because the executable
remote-main authority is not yet mintable.  A
``TargetExecutionAnchorPlaceholderV1`` remains explicitly nonauthorizing.
The observer accepts only the exact internally minted
``V072RemoteMainAnchorV1`` type; a claim, independent nonauthorizing
attestation, draft/null preregistration, placeholder, or duck type cannot
substitute for that capability.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
import hashlib
import re
from typing import Any, Iterable, Mapping

from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id
from acfqp.relational_graph_core_v1 import GraphTopologyV1
import acfqp.transfer_guided_acquisition_preregistration_v1 as prereg
import acfqp.v072_final_preregistration_authority_v1 as final_authority


SCHEMA_VERSION = "2.0.0"
PROPOSED_CONTRACT_VERSION = "1.36.0"
PROFILE_KEY = "v072_anchor_gated_heldout_graph_transition_observer_v1"
SAMPLE_EFFICIENCY_GATE_STATUS = "NOT_RUN"
OFFICIAL_EXECUTION_ALLOWED = False
MAX_FROZEN_SUPPORT_MEMBERS_PER_ROW_V2 = 16
MAX_OBSERVER_STREAM_EPOCH_INDEX_V2 = 3

OBSERVER_SEMANTICS_ID = (
    "v072_arm_isolated_splitmix64_joint_transition_replay_v2"
)
RANDOMNESS_IMPLEMENTATION = (
    "DETERMINISTIC_SPLITMIX64_COUNTER_REPLAY_BENCHMARK"
)
EXACT_IID_IMPLEMENTATION_CLAIMED = False
STATISTICAL_CLAIM_SCOPE = (
    "CONDITIONAL_ON_IDEALIZED_TARGET_LOCAL_UINT64_IID_AUTHORITY_"
    "NOT_PROVEN_BY_DETERMINISTIC_REPLAY_IMPLEMENTATION"
)

_UINT64_MODULUS = 1 << 64
_UINT64_MASK = _UINT64_MODULUS - 1
_SPLITMIX_GAMMA = 0x9E3779B97F4A7C15
_COMMIT_SHA_RE = re.compile(r"^[0-9a-f]{40}(?:[0-9a-f]{24})?$")


class HeldoutGraphTransitionObserverV2InvariantViolation(ValueError):
    """A V0-072 observer identity, binding, tuple, or replay is invalid."""


DOMAIN_TAGS = {
    "anchor": "acfqp:v072-target-execution-anchor-placeholder:v1",
    "state": "acfqp:v072-heldout-symbolic-graph-state:v3",
    "catalogue": "acfqp:v072-heldout-legal-action-catalogue:v3",
    "row_binding": "acfqp:v072-heldout-observation-row-binding:v3",
    "support_set": "acfqp:v072-heldout-frozen-support-set:v3",
    "pairing_support_set": (
        "acfqp:v072-heldout-arm-free-pairing-support-set:v3"
    ),
    "pairing_lineage": (
        "acfqp:v072-heldout-arm-free-support-lineage:v3"
    ),
    "support_epoch": "acfqp:v072-heldout-support-epoch:v3",
    "support_epoch_chain": "acfqp:v072-heldout-support-epoch-chain:v3",
    "stream_pair": "acfqp:v072-arm-isolated-stream-pair:v3",
    "pairing_group": "acfqp:v072-arm-free-raw-word-pairing-group:v3",
    "stream": "acfqp:v072-arm-isolated-transition-stream:v3",
    "raw_digest": "acfqp:v072-heldout-raw-draw-digest:v3",
    "raw_commitment": "acfqp:v072-heldout-raw-draw-commitment:v3",
    "observation": "acfqp:v072-heldout-joint-transition-observation:v3",
    "work": "acfqp:v072-heldout-transition-stream-work:v3",
    "replay": "acfqp:v072-heldout-transition-replay:v3",
    "evaluation_atom": "acfqp:v072-evaluation-only-exact-atom:v3",
}

_STREAM_SEED_DOMAINS = {
    "DISCOVERY": "acfqp:v072-heldout-discovery-stream-seed:v3",
    "VALIDATION": "acfqp:v072-heldout-validation-stream-seed:v3",
}

if len(DOMAIN_TAGS) != len(set(DOMAIN_TAGS.values())):  # pragma: no cover
    raise RuntimeError("V0-072 observer content domains must be unique")
if len(_STREAM_SEED_DOMAINS) != len(set(_STREAM_SEED_DOMAINS.values())):
    raise RuntimeError("V0-072 observer seed domains must be unique")


def _content_id(
    role: str,
    payload: Mapping[str, Any],
    *,
    raw_suffix: bytes = b"",
) -> str:
    try:
        domain = DOMAIN_TAGS[role].encode("utf-8")
        encoded = canonical_json_bytes(dict(payload))
    except (KeyError, TypeError, ValueError) as error:
        raise HeldoutGraphTransitionObserverV2InvariantViolation(
            str(error)
        ) from error
    body = domain + b"\x00" + encoded
    if raw_suffix:
        body += b"\x00" + raw_suffix
    return hashlib.sha256(body).hexdigest()


def _cid(value: Any, field: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise HeldoutGraphTransitionObserverV2InvariantViolation(
            f"{field} must be a full content ID"
        ) from error


def _fdoc(value: Fraction) -> dict[str, int]:
    if type(value) is not Fraction:
        raise HeldoutGraphTransitionObserverV2InvariantViolation(
            "observer arithmetic must use exact Fraction"
        )
    return {
        "numerator": value.numerator,
        "denominator": value.denominator,
    }


def _action(value: Any, field: str = "action") -> tuple[int, int, int]:
    if (
        type(value) is not tuple
        or len(value) != 3
        or any(type(item) is not int for item in value)
    ):
        raise HeldoutGraphTransitionObserverV2InvariantViolation(
            f"{field} must be an exact integer triple"
        )
    return value


def _sorted_content_ids(
    values: Iterable[str],
    field: str,
) -> tuple[str, ...]:
    if type(values) not in (tuple, list):
        raise HeldoutGraphTransitionObserverV2InvariantViolation(
            f"{field} must be a concrete sequence"
        )
    output = tuple(values)
    for value in output:
        _cid(value, field)
    if output != tuple(sorted(set(output))):
        raise HeldoutGraphTransitionObserverV2InvariantViolation(
            f"{field} must be unique and content-ID sorted"
        )
    return output


def _registered_context(
    context: Any,
) -> prereg.HeldoutPublicGraphContextV2:
    if (
        type(context) is not prereg.HeldoutPublicGraphContextV2
        or context not in prereg.registered_heldout_public_contexts_v2()
        or type(context.topology) is not GraphTopologyV1
    ):
        raise HeldoutGraphTransitionObserverV2InvariantViolation(
            "operation requires an exact registered V0-072 public context"
        )
    return context


def _context_by_id(context_id: str) -> prereg.HeldoutPublicGraphContextV2:
    canonical = _cid(context_id, "context")
    for context in prereg.registered_heldout_public_contexts_v2():
        if context.context_id == canonical:
            return context
    raise HeldoutGraphTransitionObserverV2InvariantViolation(
        "context ID is outside the registered V0-072 family"
    )


def _arm(value: Any) -> str:
    if type(value) is not str or value not in prereg.ARM_ORDER:
        raise HeldoutGraphTransitionObserverV2InvariantViolation(
            "observation arm is outside the preregistered arm order"
        )
    return value


@dataclass(frozen=True, slots=True)
class TargetExecutionAnchorPlaceholderV1:
    """Nonauthorizing placeholder for first-remote-main verification.

    The containment attestation is intentionally opaque here.  A later
    independent authority must define a distinct verified execution-anchor
    type before any registered target tape can be opened.
    """

    preregistration_id: str
    environment_manifest_id: str
    remote_main_commit_sha: str
    remote_main_containment_attestation_id: str
    verification_profile: str = (
        "EXTERNAL_FIRST_REMOTE_MAIN_CONTAINMENT_ATTESTATION_PLACEHOLDER_V1"
    )
    immutable_anchor: bool = True
    sample_efficiency_gate_status: str = SAMPLE_EFFICIENCY_GATE_STATUS

    def __post_init__(self) -> None:
        frozen = (
            prereg.freeze_transfer_guided_acquisition_preregistration_v1()
        )
        manifest = prereg.frozen_heldout_environment_manifest_v1()
        if (
            _cid(self.preregistration_id, "anchor preregistration")
            != frozen.preregistration_id
            or _cid(
                self.environment_manifest_id,
                "anchor environment manifest",
            )
            != manifest.manifest_id
            or type(self.remote_main_commit_sha) is not str
            or _COMMIT_SHA_RE.fullmatch(self.remote_main_commit_sha) is None
            or _cid(
                self.remote_main_containment_attestation_id,
                "remote-main containment attestation",
            )
            != self.remote_main_containment_attestation_id
            or self.verification_profile
            != (
                "EXTERNAL_FIRST_REMOTE_MAIN_CONTAINMENT_"
                "ATTESTATION_PLACEHOLDER_V1"
            )
            or self.immutable_anchor is not True
            or self.sample_efficiency_gate_status
            != SAMPLE_EFFICIENCY_GATE_STATUS
        ):
            raise HeldoutGraphTransitionObserverV2InvariantViolation(
                "target-execution anchor placeholder is invalid"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_target_execution_anchor_placeholder.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "preregistration_id": self.preregistration_id,
            "environment_manifest_id": self.environment_manifest_id,
            "remote_main_commit_sha": self.remote_main_commit_sha,
            "remote_main_containment_attestation_id": (
                self.remote_main_containment_attestation_id
            ),
            "verification_profile": self.verification_profile,
            "immutable_anchor": True,
            "separate_from_null_preregistration_anchor": True,
            "authorizes_registered_target_execution": False,
            "future_verified_remote_main_anchor_required": True,
            "sample_efficiency_gate_status": "NOT_RUN",
            "official_execution_allowed": False,
        }

    @property
    def anchor_id(self) -> str:
        return _content_id("anchor", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "anchor_id": self.anchor_id}


def bind_target_execution_anchor_placeholder_v1(
    frozen_preregistration: (
        prereg.TransferGuidedAcquisitionPreregistrationV1
    ),
    *,
    remote_main_commit_sha: str,
    remote_main_containment_attestation_id: str,
) -> TargetExecutionAnchorPlaceholderV1:
    """Bind a separate anchor without mutating the pre-execution artifact."""

    expected = prereg.freeze_transfer_guided_acquisition_preregistration_v1()
    if (
        type(frozen_preregistration)
        is not prereg.TransferGuidedAcquisitionPreregistrationV1
        or frozen_preregistration.to_document() != expected.to_document()
        or frozen_preregistration.anchor_commit_id is not None
        or frozen_preregistration.target_execution_allowed is not False
    ):
        raise HeldoutGraphTransitionObserverV2InvariantViolation(
            "anchor binding requires the exact null-anchor preregistration"
        )
    return TargetExecutionAnchorPlaceholderV1(
        expected.preregistration_id,
        expected.environment_manifest_id,
        remote_main_commit_sha,
        remote_main_containment_attestation_id,
    )


def _require_execution_anchor(
    anchor: Any,
) -> final_authority.V072RemoteMainAnchorV1:
    if type(anchor) is TargetExecutionAnchorPlaceholderV1:
        raise HeldoutGraphTransitionObserverV2InvariantViolation(
            "target-execution anchor placeholder is nonauthorizing; the "
            "exact internally minted remote-main execution anchor is required"
        )
    if (
        type(anchor) is final_authority.V072RemoteMainAnchorV1
        and anchor.target_execution_allowed is True
        and type(anchor.claim)
        is final_authority.V072RemoteMainAnchorClaimV1
        and anchor.claim.verification_scope
        is (
            final_authority.RemoteMainAnchorVerificationScopeV1
            .REGISTERED_PRODUCTION_CANDIDATE
        )
    ):
        return anchor
    raise HeldoutGraphTransitionObserverV2InvariantViolation(
        "registered target tape requires the exact internally minted "
        "remote-main execution-anchor authority"
    )


def _anchor_preregistration_id(
    anchor: final_authority.V072RemoteMainAnchorV1,
) -> str:
    canonical = _require_execution_anchor(anchor)
    return _cid(
        canonical.claim.final_preregistration_id,
        "anchor final preregistration",
    )


def _anchor_environment_manifest_id(
    anchor: final_authority.V072RemoteMainAnchorV1,
) -> str:
    _require_execution_anchor(anchor)
    return prereg.frozen_heldout_environment_manifest_v1().manifest_id


@dataclass(frozen=True, slots=True)
class HeldoutSymbolicGraphStateV2:
    """A seven-vertex symbolic board with no transition-law fields."""

    ranks: tuple[int, ...]
    failure: bool = False

    def __post_init__(self) -> None:
        if (
            type(self.ranks) is not tuple
            or len(self.ranks) != 7
            or any(
                type(rank) is not int
                or not 0 <= rank <= prereg.RANK_CAP
                for rank in self.ranks
            )
            or type(self.failure) is not bool
        ):
            raise HeldoutGraphTransitionObserverV2InvariantViolation(
                "held-out symbolic graph state is invalid"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_heldout_symbolic_graph_state.v2",
            "schema_version": SCHEMA_VERSION,
            "ranks": list(self.ranks),
            "failure": self.failure,
        }

    @property
    def state_id(self) -> str:
        return _content_id("state", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "state_id": self.state_id}


def root_state_v2(
    context: prereg.HeldoutPublicGraphContextV2,
) -> HeldoutSymbolicGraphStateV2:
    registered = _registered_context(context)
    return HeldoutSymbolicGraphStateV2(registered.root_ranks)


def _validate_state(
    context: prereg.HeldoutPublicGraphContextV2,
    state: HeldoutSymbolicGraphStateV2,
) -> None:
    if (
        type(state) is not HeldoutSymbolicGraphStateV2
        or len(state.ranks) != context.topology.vertex_count
    ):
        raise HeldoutGraphTransitionObserverV2InvariantViolation(
            "symbolic state lies outside the seven-vertex context"
        )


def _legal_actions(
    context: prereg.HeldoutPublicGraphContextV2,
    state: HeldoutSymbolicGraphStateV2,
) -> tuple[tuple[int, int, int], ...]:
    _validate_state(context, state)
    if state.failure:
        return ()
    return tuple(
        sorted(
            (first, second, survivor)
            for first, second in context.topology.edges
            if state.ranks[first] > 0
            and state.ranks[first] == state.ranks[second]
            for survivor in (first, second)
        )
    )


@dataclass(frozen=True, slots=True)
class HeldoutLegalActionCatalogueV2:
    context_id: str
    state: HeldoutSymbolicGraphStateV2
    remaining_horizon: int
    actions: tuple[tuple[int, int, int], ...]

    def __post_init__(self) -> None:
        _cid(self.context_id, "catalogue context")
        if (
            type(self.state) is not HeldoutSymbolicGraphStateV2
            or type(self.remaining_horizon) is not int
            or self.remaining_horizon not in (1, prereg.HORIZON)
            or type(self.actions) is not tuple
            or any(_action(item) != item for item in self.actions)
            or self.actions != tuple(sorted(set(self.actions)))
            or (self.state.failure and self.actions)
        ):
            raise HeldoutGraphTransitionObserverV2InvariantViolation(
                "held-out legal-action catalogue is invalid"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_heldout_legal_action_catalogue.v2",
            "schema_version": SCHEMA_VERSION,
            "context_id": self.context_id,
            "state": self.state.to_document(),
            "remaining_horizon": self.remaining_horizon,
            "actions": [list(action) for action in self.actions],
            "complete_exact_legal_action_catalogue": True,
        }

    @property
    def catalogue_id(self) -> str:
        return _content_id("catalogue", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "catalogue_id": self.catalogue_id}


def legal_action_catalogue_v2(
    context: prereg.HeldoutPublicGraphContextV2,
    state: HeldoutSymbolicGraphStateV2,
    remaining_horizon: int,
) -> HeldoutLegalActionCatalogueV2:
    registered = _registered_context(context)
    _validate_state(registered, state)
    if (
        type(remaining_horizon) is not int
        or remaining_horizon not in (1, prereg.HORIZON)
    ):
        raise HeldoutGraphTransitionObserverV2InvariantViolation(
            "remaining horizon is outside the registered H=2 query"
        )
    actions = _legal_actions(registered, state)
    if state.failure != (not actions):
        raise HeldoutGraphTransitionObserverV2InvariantViolation(
            "state failure flag disagrees with complete legal actions"
        )
    return HeldoutLegalActionCatalogueV2(
        registered.context_id,
        state,
        remaining_horizon,
        actions,
    )


def _validated_catalogue(
    context: prereg.HeldoutPublicGraphContextV2,
    catalogue: Any,
) -> HeldoutLegalActionCatalogueV2:
    if (
        type(catalogue) is not HeldoutLegalActionCatalogueV2
        or catalogue.context_id != context.context_id
    ):
        raise HeldoutGraphTransitionObserverV2InvariantViolation(
            "catalogue/public-context identity mismatch"
        )
    expected = legal_action_catalogue_v2(
        context,
        catalogue.state,
        catalogue.remaining_horizon,
    )
    if catalogue.to_document() != expected.to_document():
        raise HeldoutGraphTransitionObserverV2InvariantViolation(
            "catalogue is not the canonical complete action catalogue"
        )
    return catalogue


@dataclass(frozen=True, slots=True)
class HeldoutObservationRowBindingV2:
    """Physical state-action-time row bound before a support epoch exists."""

    context_id: str
    catalogue_id: str
    state_id: str
    remaining_horizon: int
    action: tuple[int, int, int]

    def __post_init__(self) -> None:
        _context_by_id(self.context_id)
        _cid(self.catalogue_id, "row-binding catalogue")
        _cid(self.state_id, "row-binding state")
        _action(self.action)
        if (
            type(self.remaining_horizon) is not int
            or self.remaining_horizon not in (1, prereg.HORIZON)
        ):
            raise HeldoutGraphTransitionObserverV2InvariantViolation(
                "observation row has an invalid remaining horizon"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_heldout_observation_row_binding.v2",
            "schema_version": SCHEMA_VERSION,
            "context_id": self.context_id,
            "catalogue_id": self.catalogue_id,
            "state_id": self.state_id,
            "remaining_horizon": self.remaining_horizon,
            "action": list(self.action),
            "physical_row_binding": True,
        }

    @property
    def row_binding_id(self) -> str:
        return _content_id("row_binding", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "row_binding_id": self.row_binding_id,
        }


def observation_row_binding_v2(
    context: prereg.HeldoutPublicGraphContextV2,
    catalogue: HeldoutLegalActionCatalogueV2,
    action: tuple[int, int, int],
) -> HeldoutObservationRowBindingV2:
    registered = _registered_context(context)
    canonical_catalogue = _validated_catalogue(registered, catalogue)
    canonical_action = _action(action)
    if canonical_action not in canonical_catalogue.actions:
        raise HeldoutGraphTransitionObserverV2InvariantViolation(
            "row-binding action is outside the complete legal catalogue"
        )
    return HeldoutObservationRowBindingV2(
        registered.context_id,
        canonical_catalogue.catalogue_id,
        canonical_catalogue.state.state_id,
        canonical_catalogue.remaining_horizon,
        canonical_action,
    )


def _support_set_content_id(
    context_id: str,
    row_binding_id: str,
    arm: str,
    members: tuple[str, ...],
) -> str:
    return _content_id(
        "support_set",
        {
            "schema": "acfqp.v072_heldout_frozen_support_set.v2",
            "schema_version": SCHEMA_VERSION,
            "context_id": context_id,
            "row_binding_id": row_binding_id,
            "arm": arm,
            "member_ids": list(members),
        },
    )


def _pairing_support_set_content_id(
    context_id: str,
    row_binding_id: str,
    members: tuple[str, ...],
) -> str:
    return _content_id(
        "pairing_support_set",
        {
            "schema": (
                "acfqp.v072_heldout_arm_free_pairing_support_set.v2"
            ),
            "schema_version": SCHEMA_VERSION,
            "context_id": context_id,
            "row_binding_id": row_binding_id,
            "member_ids": list(members),
            "arm_serialized": False,
        },
    )


def _pairing_lineage_content_id(
    context_id: str,
    row_binding_id: str,
    epoch_index: int,
    pairing_support_set_id: str,
    parent_pairing_lineage_id: str | None,
) -> str:
    return _content_id(
        "pairing_lineage",
        {
            "schema": (
                "acfqp.v072_heldout_arm_free_support_lineage.v2"
            ),
            "schema_version": SCHEMA_VERSION,
            "context_id": context_id,
            "row_binding_id": row_binding_id,
            "epoch_index": epoch_index,
            "pairing_support_set_id": pairing_support_set_id,
            "parent_pairing_lineage": (
                {"kind": "ROOT"}
                if parent_pairing_lineage_id is None
                else {
                    "kind": "PREDECESSOR",
                    "pairing_lineage_id": parent_pairing_lineage_id,
                }
            ),
            "arm_serialized": False,
        },
    )


@dataclass(frozen=True, slots=True)
class HeldoutSupportEpochIdentityV2:
    context_id: str
    row_binding_id: str
    arm: str
    epoch_index: int
    frozen_support_member_ids: tuple[str, ...]
    frozen_support_set_id: str
    arm_free_pairing_support_set_id: str
    arm_free_pairing_lineage_id: str
    parent_epoch_id: str | None
    parent_arm_free_pairing_lineage_id: str | None

    def __post_init__(self) -> None:
        _context_by_id(self.context_id)
        _cid(self.row_binding_id, "support epoch row binding")
        canonical_arm = _arm(self.arm)
        members = _sorted_content_ids(
            self.frozen_support_member_ids,
            "support epoch frozen member IDs",
        )
        if (
            type(self.epoch_index) is not int
            or self.epoch_index
            not in range(MAX_OBSERVER_STREAM_EPOCH_INDEX_V2 + 1)
            or len(members) > MAX_FROZEN_SUPPORT_MEMBERS_PER_ROW_V2
        ):
            raise HeldoutGraphTransitionObserverV2InvariantViolation(
                "support epoch index or registered per-row cap is invalid"
            )
        if self.epoch_index == 0:
            if (
                members
                or self.parent_epoch_id is not None
                or self.parent_arm_free_pairing_lineage_id is not None
            ):
                raise HeldoutGraphTransitionObserverV2InvariantViolation(
                    "bootstrap discovery epoch requires empty support and "
                    "has no parent"
                )
        else:
            if not members:
                raise HeldoutGraphTransitionObserverV2InvariantViolation(
                    "validation epochs require frozen discovered support"
                )
            _cid(self.parent_epoch_id, "parent support epoch")
            _cid(
                self.parent_arm_free_pairing_lineage_id,
                "parent arm-free pairing lineage",
            )
        expected_support_set_id = _support_set_content_id(
            self.context_id,
            self.row_binding_id,
            canonical_arm,
            members,
        )
        expected_pairing_support_set_id = (
            _pairing_support_set_content_id(
                self.context_id,
                self.row_binding_id,
                members,
            )
        )
        expected_pairing_lineage_id = _pairing_lineage_content_id(
            self.context_id,
            self.row_binding_id,
            self.epoch_index,
            expected_pairing_support_set_id,
            self.parent_arm_free_pairing_lineage_id,
        )
        if (
            _cid(self.frozen_support_set_id, "frozen support set")
            != expected_support_set_id
            or _cid(
                self.arm_free_pairing_support_set_id,
                "arm-free pairing support set",
            )
            != expected_pairing_support_set_id
            or _cid(
                self.arm_free_pairing_lineage_id,
                "arm-free support pairing lineage",
            )
            != expected_pairing_lineage_id
        ):
            raise HeldoutGraphTransitionObserverV2InvariantViolation(
                "support epoch commitments do not recompute from members"
            )

    @property
    def frozen_support_member_count(self) -> int:
        return len(self.frozen_support_member_ids)

    @property
    def observer_stage(self) -> str:
        return (
            "BOOTSTRAP_DISCOVERY"
            if self.epoch_index == 0
            else (
                "INITIAL_VALIDATION"
                if self.epoch_index == 1
                else "PROMOTED_VALIDATION"
            )
        )

    @property
    def required_lane(self) -> "ObservationLaneV2":
        return (
            ObservationLaneV2.DISCOVERY
            if self.epoch_index == 0
            else ObservationLaneV2.VALIDATION
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_heldout_support_epoch.v2",
            "schema_version": SCHEMA_VERSION,
            "context_id": self.context_id,
            "row_binding_id": self.row_binding_id,
            "arm": self.arm,
            "epoch_index": self.epoch_index,
            "observer_stage": self.observer_stage,
            "required_lane": self.required_lane.value,
            "frozen_support_member_ids": list(
                self.frozen_support_member_ids
            ),
            "frozen_support_set_id": self.frozen_support_set_id,
            "arm_free_pairing_support_set_id": (
                self.arm_free_pairing_support_set_id
            ),
            "arm_free_pairing_lineage_id": (
                self.arm_free_pairing_lineage_id
            ),
            "frozen_support_member_count": (
                self.frozen_support_member_count
            ),
            "per_row_frozen_support_member_cap": (
                MAX_FROZEN_SUPPORT_MEMBERS_PER_ROW_V2
            ),
            "campaign_row_epoch_count_cap_applied_here": False,
            "parent_epoch": (
                {"kind": "ROOT"}
                if self.parent_epoch_id is None
                else {
                    "kind": "PREDECESSOR",
                    "epoch_id": self.parent_epoch_id,
                    "parent_arm_free_pairing_lineage_id": (
                        self.parent_arm_free_pairing_lineage_id
                    ),
                }
            ),
        }

    @property
    def epoch_id(self) -> str:
        return _content_id("support_epoch", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "epoch_id": self.epoch_id}


def support_epoch_identity_v2(
    context: prereg.HeldoutPublicGraphContextV2,
    row_binding: HeldoutObservationRowBindingV2,
    arm: str,
    epoch_index: int,
    frozen_support_member_ids: tuple[str, ...] = (),
    parent_epoch: HeldoutSupportEpochIdentityV2 | None = None,
) -> HeldoutSupportEpochIdentityV2:
    registered = _registered_context(context)
    if (
        type(row_binding) is not HeldoutObservationRowBindingV2
        or row_binding.context_id != registered.context_id
    ):
        raise HeldoutGraphTransitionObserverV2InvariantViolation(
            "support epoch requires an exact same-context row binding"
        )
    canonical_arm = _arm(arm)
    members = _sorted_content_ids(
        frozen_support_member_ids,
        "frozen support member IDs",
    )
    if len(members) > MAX_FROZEN_SUPPORT_MEMBERS_PER_ROW_V2:
        raise HeldoutGraphTransitionObserverV2InvariantViolation(
            "support set exceeds the registered per-row V2 support cap"
        )
    if (
        type(epoch_index) is not int
        or epoch_index
        not in range(MAX_OBSERVER_STREAM_EPOCH_INDEX_V2 + 1)
    ):
        raise HeldoutGraphTransitionObserverV2InvariantViolation(
            "support epoch is outside bootstrap plus three confidence epochs"
        )
    if epoch_index == 0:
        if parent_epoch is not None or members:
            raise HeldoutGraphTransitionObserverV2InvariantViolation(
                "bootstrap discovery requires empty support and no parent"
            )
        parent_id = None
        parent_pairing_lineage_id = None
    else:
        if (
            type(parent_epoch) is not HeldoutSupportEpochIdentityV2
            or parent_epoch.context_id != registered.context_id
            or parent_epoch.row_binding_id != row_binding.row_binding_id
            or parent_epoch.arm != canonical_arm
            or parent_epoch.epoch_index != epoch_index - 1
            or not members
        ):
            raise HeldoutGraphTransitionObserverV2InvariantViolation(
                "validation requires nonempty support and the immediate "
                "same-row/context/arm parent epoch"
            )
        parent_id = parent_epoch.epoch_id
        parent_pairing_lineage_id = (
            parent_epoch.arm_free_pairing_lineage_id
        )
    support_set_id = _support_set_content_id(
        registered.context_id,
        row_binding.row_binding_id,
        canonical_arm,
        members,
    )
    pairing_support_set_id = _pairing_support_set_content_id(
        registered.context_id,
        row_binding.row_binding_id,
        members,
    )
    pairing_lineage_id = _pairing_lineage_content_id(
        registered.context_id,
        row_binding.row_binding_id,
        epoch_index,
        pairing_support_set_id,
        parent_pairing_lineage_id,
    )
    return HeldoutSupportEpochIdentityV2(
        registered.context_id,
        row_binding.row_binding_id,
        canonical_arm,
        epoch_index,
        members,
        support_set_id,
        pairing_support_set_id,
        pairing_lineage_id,
        parent_id,
        parent_pairing_lineage_id,
    )


@dataclass(frozen=True, slots=True)
class HeldoutSupportEpochChainV2:
    context_id: str
    row_binding_id: str
    arm: str
    epochs: tuple[HeldoutSupportEpochIdentityV2, ...]

    def __post_init__(self) -> None:
        _context_by_id(self.context_id)
        _cid(self.row_binding_id, "support chain row binding")
        canonical_arm = _arm(self.arm)
        if (
            type(self.epochs) is not tuple
            or not 1
            <= len(self.epochs)
            <= MAX_OBSERVER_STREAM_EPOCH_INDEX_V2 + 1
            or any(
                type(epoch) is not HeldoutSupportEpochIdentityV2
                for epoch in self.epochs
            )
        ):
            raise HeldoutGraphTransitionObserverV2InvariantViolation(
                "support epoch chain must contain one to four epochs"
            )
        for index, epoch in enumerate(self.epochs):
            if (
                epoch.context_id != self.context_id
                or epoch.row_binding_id != self.row_binding_id
                or epoch.arm != canonical_arm
                or epoch.epoch_index != index
            ):
                raise HeldoutGraphTransitionObserverV2InvariantViolation(
                    "support epoch chain context/row/arm/index mismatch"
                )
            if index == 0:
                if (
                    epoch.parent_epoch_id is not None
                    or epoch.parent_arm_free_pairing_lineage_id is not None
                ):
                    raise HeldoutGraphTransitionObserverV2InvariantViolation(
                        "bootstrap support chain parent is invalid"
                    )
            else:
                parent = self.epochs[index - 1]
                if (
                    epoch.parent_epoch_id != parent.epoch_id
                    or epoch.parent_arm_free_pairing_lineage_id
                    != parent.arm_free_pairing_lineage_id
                ):
                    raise HeldoutGraphTransitionObserverV2InvariantViolation(
                        "support epoch chain has a forged or skipped parent"
                    )

    @property
    def leaf(self) -> HeldoutSupportEpochIdentityV2:
        return self.epochs[-1]

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_heldout_support_epoch_chain.v2",
            "schema_version": SCHEMA_VERSION,
            "context_id": self.context_id,
            "row_binding_id": self.row_binding_id,
            "arm": self.arm,
            "epoch_ids": [epoch.epoch_id for epoch in self.epochs],
            "leaf_epoch_id": self.leaf.epoch_id,
            "complete_bootstrap_to_leaf_chain": True,
        }

    @property
    def chain_id(self) -> str:
        return _content_id("support_epoch_chain", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "chain_id": self.chain_id}


def support_epoch_chain_v2(
    context: prereg.HeldoutPublicGraphContextV2,
    row_binding: HeldoutObservationRowBindingV2,
    arm: str,
    epochs: tuple[HeldoutSupportEpochIdentityV2, ...],
) -> HeldoutSupportEpochChainV2:
    registered = _registered_context(context)
    if (
        type(row_binding) is not HeldoutObservationRowBindingV2
        or row_binding.context_id != registered.context_id
    ):
        raise HeldoutGraphTransitionObserverV2InvariantViolation(
            "support chain requires the exact same-context row binding"
        )
    return HeldoutSupportEpochChainV2(
        registered.context_id,
        row_binding.row_binding_id,
        _arm(arm),
        epochs,
    )


def verify_heldout_support_epoch_chain_v2(
    context: prereg.HeldoutPublicGraphContextV2,
    row_binding: HeldoutObservationRowBindingV2,
    arm: str,
    chain: HeldoutSupportEpochChainV2,
) -> HeldoutSupportEpochChainV2:
    if type(chain) is not HeldoutSupportEpochChainV2:
        raise HeldoutGraphTransitionObserverV2InvariantViolation(
            "stream requires a canonical complete support epoch chain"
        )
    expected = support_epoch_chain_v2(
        context,
        row_binding,
        arm,
        chain.epochs,
    )
    if chain.to_document() != expected.to_document():
        raise HeldoutGraphTransitionObserverV2InvariantViolation(
            "support epoch chain is not canonical"
        )
    return chain


class ObservationLaneV2(str, Enum):
    DISCOVERY = "DISCOVERY"
    VALIDATION = "VALIDATION"


def _lane(value: Any) -> ObservationLaneV2:
    if type(value) is not ObservationLaneV2:
        raise HeldoutGraphTransitionObserverV2InvariantViolation(
            "stream lane must be DISCOVERY or VALIDATION"
        )
    return value


@dataclass(frozen=True, slots=True)
class ArmIsolatedTransitionStreamPairV2:
    anchor_id: str
    preregistration_id: str
    environment_manifest_id: str
    context_id: str
    row_binding_id: str
    catalogue_id: str
    support_epoch_id: str
    support_epoch_chain_id: str
    arm_free_pairing_lineage_id: str
    observer_epoch_index: int
    observer_stage: str
    required_lane: ObservationLaneV2
    arm: str
    action: tuple[int, int, int]

    def __post_init__(self) -> None:
        for value, field in (
            (self.anchor_id, "stream-pair anchor"),
            (self.preregistration_id, "stream-pair preregistration"),
            (self.environment_manifest_id, "stream-pair environment"),
            (self.context_id, "stream-pair context"),
            (self.row_binding_id, "stream-pair row binding"),
            (self.catalogue_id, "stream-pair catalogue"),
            (self.support_epoch_id, "stream-pair support epoch"),
            (
                self.support_epoch_chain_id,
                "stream-pair support epoch chain",
            ),
            (
                self.arm_free_pairing_lineage_id,
                "stream-pair arm-free support lineage",
            ),
        ):
            _cid(value, field)
        _arm(self.arm)
        _lane(self.required_lane)
        _action(self.action)
        expected_stage = (
            "BOOTSTRAP_DISCOVERY"
            if self.observer_epoch_index == 0
            else (
                "INITIAL_VALIDATION"
                if self.observer_epoch_index == 1
                else "PROMOTED_VALIDATION"
            )
        )
        expected_lane = (
            ObservationLaneV2.DISCOVERY
            if self.observer_epoch_index == 0
            else ObservationLaneV2.VALIDATION
        )
        if (
            type(self.observer_epoch_index) is not int
            or self.observer_epoch_index
            not in range(MAX_OBSERVER_STREAM_EPOCH_INDEX_V2 + 1)
            or self.observer_stage != expected_stage
            or self.required_lane is not expected_lane
        ):
            raise HeldoutGraphTransitionObserverV2InvariantViolation(
                "stream binding disagrees with observer epoch chronology"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_arm_isolated_stream_pair.v2",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "anchor_id": self.anchor_id,
            "preregistration_id": self.preregistration_id,
            "environment_manifest_id": self.environment_manifest_id,
            "context_id": self.context_id,
            "row_binding_id": self.row_binding_id,
            "catalogue_id": self.catalogue_id,
            "support_epoch_id": self.support_epoch_id,
            "support_epoch_chain_id": self.support_epoch_chain_id,
            "arm_free_pairing_lineage_id": (
                self.arm_free_pairing_lineage_id
            ),
            "observer_epoch_index": self.observer_epoch_index,
            "observer_stage": self.observer_stage,
            "required_lane": self.required_lane.value,
            "arm": self.arm,
            "action": list(self.action),
            "consumer_route_serialized": False,
            "common_random_number_pairing_across_arms": True,
            "cross_arm_independence_claimed": False,
            "discovery_validation_share_one_epoch_id": False,
            "bootstrap_not_counted_as_confidence_epoch": True,
        }

    @property
    def pair_id(self) -> str:
        return _content_id("stream_pair", self._payload())

    def stream_id(self, lane: ObservationLaneV2) -> str:
        canonical_lane = _lane(lane)
        if canonical_lane is not self.required_lane:
            raise HeldoutGraphTransitionObserverV2InvariantViolation(
                "observer epoch cannot open the requested lane"
            )
        return _content_id(
            "stream",
            {
                "schema": "acfqp.v072_arm_isolated_transition_stream.v2",
                "schema_version": SCHEMA_VERSION,
                "pair_id": self.pair_id,
                "arm": self.arm,
                "lane": canonical_lane.value,
                "consumer_route_serialized": False,
            },
        )

    def raw_word_pairing_group_id(
        self,
        lane: ObservationLaneV2,
    ) -> str:
        """Arm-free seed identity for matched common-random-number draws."""

        canonical_lane = _lane(lane)
        if canonical_lane is not self.required_lane:
            raise HeldoutGraphTransitionObserverV2InvariantViolation(
                "observer epoch cannot seed the requested lane"
            )
        return _content_id(
            "pairing_group",
            {
                "schema": (
                    "acfqp.v072_arm_free_raw_word_pairing_group.v2"
                ),
                "schema_version": SCHEMA_VERSION,
                "preregistration_id": self.preregistration_id,
                "environment_manifest_id": self.environment_manifest_id,
                "context_id": self.context_id,
                "row_binding_id": self.row_binding_id,
                "arm_free_pairing_lineage_id": (
                    self.arm_free_pairing_lineage_id
                ),
                "lane": canonical_lane.value,
                "arm_serialized": False,
                "common_random_number_pairing": True,
                "cross_arm_independence_claimed": False,
                "execution_anchor_entropy_used": False,
            },
        )

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "pair_id": self.pair_id,
            "stream_id": self.stream_id(self.required_lane),
            "raw_word_pairing_group_id": (
                self.raw_word_pairing_group_id(self.required_lane)
            ),
        }


def arm_isolated_stream_pair_identity_v2(
    anchor: final_authority.V072RemoteMainAnchorV1,
    context: prereg.HeldoutPublicGraphContextV2,
    catalogue: HeldoutLegalActionCatalogueV2,
    action: tuple[int, int, int],
    arm: str,
    support_epoch_chain: HeldoutSupportEpochChainV2,
) -> ArmIsolatedTransitionStreamPairV2:
    canonical_anchor = _require_execution_anchor(anchor)
    registered = _registered_context(context)
    canonical_catalogue = _validated_catalogue(registered, catalogue)
    canonical_action = _action(action)
    canonical_arm = _arm(arm)
    row_binding = observation_row_binding_v2(
        registered,
        canonical_catalogue,
        canonical_action,
    )
    if canonical_action not in canonical_catalogue.actions:
        raise HeldoutGraphTransitionObserverV2InvariantViolation(
            "stream action is outside the complete legal catalogue"
        )
    canonical_chain = verify_heldout_support_epoch_chain_v2(
        registered,
        row_binding,
        canonical_arm,
        support_epoch_chain,
    )
    support_epoch = canonical_chain.leaf
    return ArmIsolatedTransitionStreamPairV2(
        canonical_anchor.anchor_id,
        _anchor_preregistration_id(canonical_anchor),
        _anchor_environment_manifest_id(canonical_anchor),
        registered.context_id,
        row_binding.row_binding_id,
        canonical_catalogue.catalogue_id,
        support_epoch.epoch_id,
        canonical_chain.chain_id,
        support_epoch.arm_free_pairing_lineage_id,
        support_epoch.epoch_index,
        support_epoch.observer_stage,
        support_epoch.required_lane,
        canonical_arm,
        canonical_action,
    )


@dataclass(frozen=True, slots=True)
class HeldoutRawDrawCommitmentV2:
    pair_id: str
    stream_id: str
    raw_word_pairing_group_id: str
    arm: str
    lane: ObservationLaneV2
    accepted_draw_index: int
    random_word_start_index: int
    random_word_count: int
    rejection_count: int
    raw_digest: str

    def __post_init__(self) -> None:
        _cid(self.pair_id, "raw commitment pair")
        _cid(self.stream_id, "raw commitment stream")
        _cid(
            self.raw_word_pairing_group_id,
            "raw commitment pairing group",
        )
        _cid(self.raw_digest, "raw commitment digest")
        _arm(self.arm)
        _lane(self.lane)
        if (
            type(self.accepted_draw_index) is not int
            or self.accepted_draw_index <= 0
            or type(self.random_word_start_index) is not int
            or self.random_word_start_index <= 0
            or type(self.random_word_count) is not int
            or self.random_word_count <= 0
            or type(self.rejection_count) is not int
            or self.rejection_count < 0
            or self.random_word_count != self.rejection_count + 1
        ):
            raise HeldoutGraphTransitionObserverV2InvariantViolation(
                "raw-draw counters do not reconcile"
            )

    @property
    def random_word_end_index(self) -> int:
        return self.random_word_start_index + self.random_word_count - 1

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_heldout_raw_draw_commitment.v2",
            "schema_version": SCHEMA_VERSION,
            "pair_id": self.pair_id,
            "stream_id": self.stream_id,
            "raw_word_pairing_group_id": (
                self.raw_word_pairing_group_id
            ),
            "arm": self.arm,
            "lane": self.lane.value,
            "accepted_draw_index": self.accepted_draw_index,
            "random_word_start_index": self.random_word_start_index,
            "random_word_end_index": self.random_word_end_index,
            "random_word_count": self.random_word_count,
            "rejection_count": self.rejection_count,
            "raw_digest": self.raw_digest,
        }

    @property
    def commitment_id(self) -> str:
        return _content_id("raw_commitment", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "commitment_id": self.commitment_id}


@dataclass(frozen=True, slots=True)
class HeldoutObservedJointTransitionV2:
    anchor_id: str
    context_id: str
    row_binding_id: str
    catalogue_id: str
    support_epoch_id: str
    support_epoch_chain_id: str
    pair_id: str
    stream_id: str
    raw_word_pairing_group_id: str
    arm: str
    lane: ObservationLaneV2
    source_state: HeldoutSymbolicGraphStateV2
    action: tuple[int, int, int]
    remaining_horizon: int
    accepted_draw_index: int
    next_state: HeldoutSymbolicGraphStateV2
    realized_row_reward: Fraction
    failure: bool
    terminal: bool
    raw_commitment: HeldoutRawDrawCommitmentV2

    def __post_init__(self) -> None:
        for value, field in (
            (self.anchor_id, "observation anchor"),
            (self.context_id, "observation context"),
            (self.row_binding_id, "observation row binding"),
            (self.catalogue_id, "observation catalogue"),
            (self.support_epoch_id, "observation support epoch"),
            (
                self.support_epoch_chain_id,
                "observation support epoch chain",
            ),
            (self.pair_id, "observation pair"),
            (self.stream_id, "observation stream"),
            (
                self.raw_word_pairing_group_id,
                "observation raw-word pairing group",
            ),
        ):
            _cid(value, field)
        _arm(self.arm)
        _lane(self.lane)
        _action(self.action)
        if (
            type(self.source_state) is not HeldoutSymbolicGraphStateV2
            or type(self.next_state) is not HeldoutSymbolicGraphStateV2
            or type(self.remaining_horizon) is not int
            or self.remaining_horizon not in (1, prereg.HORIZON)
            or type(self.accepted_draw_index) is not int
            or self.accepted_draw_index <= 0
            or type(self.realized_row_reward) is not Fraction
            or not 0 <= self.realized_row_reward <= 1
            or type(self.failure) is not bool
            or self.failure != self.next_state.failure
            or type(self.terminal) is not bool
            or self.terminal
            != (self.failure or self.remaining_horizon == 1)
            or type(self.raw_commitment)
            is not HeldoutRawDrawCommitmentV2
            or self.raw_commitment.pair_id != self.pair_id
            or self.raw_commitment.stream_id != self.stream_id
            or self.raw_commitment.raw_word_pairing_group_id
            != self.raw_word_pairing_group_id
            or self.raw_commitment.arm != self.arm
            or self.raw_commitment.lane is not self.lane
            or self.raw_commitment.accepted_draw_index
            != self.accepted_draw_index
        ):
            raise HeldoutGraphTransitionObserverV2InvariantViolation(
                "held-out observed joint transition is inconsistent"
            )

    @property
    def joint_tuple(
        self,
    ) -> tuple[
        HeldoutSymbolicGraphStateV2,
        Fraction,
        bool,
        bool,
        HeldoutRawDrawCommitmentV2,
    ]:
        return (
            self.next_state,
            self.realized_row_reward,
            self.failure,
            self.terminal,
            self.raw_commitment,
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_heldout_joint_transition_observation.v2",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "anchor_id": self.anchor_id,
            "context_id": self.context_id,
            "row_binding_id": self.row_binding_id,
            "catalogue_id": self.catalogue_id,
            "support_epoch_id": self.support_epoch_id,
            "support_epoch_chain_id": self.support_epoch_chain_id,
            "pair_id": self.pair_id,
            "stream_id": self.stream_id,
            "raw_word_pairing_group_id": (
                self.raw_word_pairing_group_id
            ),
            "arm": self.arm,
            "lane": self.lane.value,
            "source_state": self.source_state.to_document(),
            "action": list(self.action),
            "remaining_horizon": self.remaining_horizon,
            "accepted_draw_index": self.accepted_draw_index,
            "next_state": self.next_state.to_document(),
            "realized_row_reward": _fdoc(self.realized_row_reward),
            "failure": self.failure,
            "terminal": self.terminal,
            "raw_commitment": self.raw_commitment.to_document(),
            "transition_probability_serialized": False,
            "support_descriptor_serialized": False,
        }

    @property
    def observation_id(self) -> str:
        return _content_id("observation", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "observation_id": self.observation_id}


@dataclass(frozen=True, slots=True)
class HeldoutTransitionStreamWorkV2:
    stream_id: str
    accepted_draws: int
    random_word_calls: int
    rejection_count: int

    def __post_init__(self) -> None:
        _cid(self.stream_id, "stream work")
        if (
            type(self.accepted_draws) is not int
            or self.accepted_draws < 0
            or type(self.random_word_calls) is not int
            or self.random_word_calls < 0
            or type(self.rejection_count) is not int
            or self.rejection_count < 0
            or self.random_word_calls
            != self.accepted_draws + self.rejection_count
        ):
            raise HeldoutGraphTransitionObserverV2InvariantViolation(
                "transition stream work does not reconcile"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_heldout_transition_stream_work.v2",
            "schema_version": SCHEMA_VERSION,
            "stream_id": self.stream_id,
            "accepted_draws": self.accepted_draws,
            "random_word_calls": self.random_word_calls,
            "rejection_count": self.rejection_count,
        }

    @property
    def work_id(self) -> str:
        return _content_id("work", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "work_id": self.work_id}


def _splitmix64(value: int) -> int:
    word = value & _UINT64_MASK
    word = (word ^ (word >> 30)) * 0xBF58476D1CE4E5B9
    word &= _UINT64_MASK
    word = (word ^ (word >> 27)) * 0x94D049BB133111EB
    word &= _UINT64_MASK
    return (word ^ (word >> 31)) & _UINT64_MASK


def _stream_seed(
    raw_word_pairing_group_id: str,
    lane: ObservationLaneV2,
) -> int:
    canonical_group = _cid(
        raw_word_pairing_group_id,
        "raw-word pairing-group seed",
    )
    canonical_lane = _lane(lane)
    digest = hashlib.sha256(
        _STREAM_SEED_DOMAINS[canonical_lane.value].encode("utf-8")
        + b"\x00"
        + canonical_group.encode("ascii")
    ).digest()
    return int.from_bytes(digest[:8], "big")


def _merge_row(
    context: prereg.HeldoutPublicGraphContextV2,
    state: HeldoutSymbolicGraphStateV2,
    action: tuple[int, int, int],
) -> tuple[tuple[int, ...], tuple[int, ...], Fraction]:
    canonical_action = _action(action)
    if canonical_action not in _legal_actions(context, state):
        raise HeldoutGraphTransitionObserverV2InvariantViolation(
            "transition action is not legal at its source state"
        )
    first, second, survivor = canonical_action
    rank = state.ranks[first]
    board = list(state.ranks)
    board[first] = 0
    board[second] = 0
    board[survivor] = min(rank + 1, prereg.RANK_CAP)
    empty = tuple(index for index, value in enumerate(board) if value == 0)
    if not empty:
        raise HeldoutGraphTransitionObserverV2InvariantViolation(
            "registered merge produced no spawn location"
        )
    reward = (
        Fraction(2 ** (rank + 1), 2 ** (prereg.RANK_CAP + 1))
        / prereg.HORIZON
    )
    return tuple(board), empty, reward


def _environment_law(
    anchor: final_authority.V072RemoteMainAnchorV1,
    context: prereg.HeldoutPublicGraphContextV2,
) -> tuple[tuple[int, Fraction], ...]:
    canonical_anchor = _require_execution_anchor(anchor)
    registered = _registered_context(context)
    manifest = prereg.frozen_heldout_environment_manifest_v1()
    if (
        _anchor_environment_manifest_id(canonical_anchor)
        != manifest.manifest_id
    ):
        raise HeldoutGraphTransitionObserverV2InvariantViolation(
            "anchor no longer binds the frozen environment manifest"
        )
    law = next(
        (
            item.rank_probabilities
            for item in manifest.laws
            if item.context_id == registered.context_id
        ),
        None,
    )
    if (
        law is None
        or sum((probability for _, probability in law), Fraction(0)) != 1
        or any(type(probability) is not Fraction for _, probability in law)
    ):
        raise HeldoutGraphTransitionObserverV2InvariantViolation(
            "frozen environment manifest has no exact law for the context"
        )
    return law


def _greatest_common_divisor(first: int, second: int) -> int:
    while second:
        first, second = second, first % second
    return first


def _integer_law(
    law: tuple[tuple[int, Fraction], ...],
) -> tuple[int, tuple[tuple[int, int], ...]]:
    denominator = 1
    for _, probability in law:
        denominator = (
            denominator
            * probability.denominator
            // _greatest_common_divisor(
                denominator,
                probability.denominator,
            )
        )
    integer = tuple(
        (
            rank,
            probability.numerator
            * (denominator // probability.denominator),
        )
        for rank, probability in law
    )
    if sum(weight for _, weight in integer) != denominator:
        raise RuntimeError("frozen exact spawn law does not normalize")
    return denominator, integer


def _rank_from_token(
    integer_law: tuple[tuple[int, int], ...],
    token: int,
) -> int:
    cursor = 0
    for rank, weight in integer_law:
        cursor += weight
        if token < cursor:
            return rank
    raise RuntimeError("accepted rank token lies outside the frozen law")


def _raw_draw_digest(
    *,
    pair_id: str,
    stream_id: str,
    raw_word_pairing_group_id: str,
    arm: str,
    lane: ObservationLaneV2,
    accepted_draw_index: int,
    random_word_start_index: int,
    next_state: HeldoutSymbolicGraphStateV2,
    reward: Fraction,
    failure: bool,
    terminal: bool,
    words: tuple[int, ...],
) -> str:
    payload = {
        "schema": "acfqp.v072_heldout_raw_draw_digest.v2",
        "schema_version": SCHEMA_VERSION,
        "pair_id": pair_id,
        "stream_id": stream_id,
        "raw_word_pairing_group_id": raw_word_pairing_group_id,
        "arm": arm,
        "lane": lane.value,
        "accepted_draw_index": accepted_draw_index,
        "random_word_start_index": random_word_start_index,
        "random_word_count": len(words),
        "next_state": next_state.to_document(),
        "realized_row_reward": _fdoc(reward),
        "failure": failure,
        "terminal": terminal,
    }
    raw = b"".join(word.to_bytes(8, "big") for word in words)
    return _content_id("raw_digest", payload, raw_suffix=raw)


class AnchorGatedHeldoutTransitionStreamV2:
    """Mutable target tape; immutable draw artifacts are its only output."""

    __slots__ = (
        "_anchor",
        "_context",
        "_catalogue",
        "_action",
        "_row_binding",
        "_arm",
        "_lane",
        "_support_epoch_chain",
        "_support_epoch",
        "_pair",
        "_stream_id",
        "_seed",
        "_merged_board",
        "_empty_cells",
        "_reward",
        "_law_denominator",
        "_integer_law",
        "_outcome_denominator",
        "_acceptance_limit",
        "_successor_cache",
        "_accepted_draws",
        "_random_word_calls",
        "_rejection_count",
    )

    def __init__(
        self,
        anchor: final_authority.V072RemoteMainAnchorV1,
        context: prereg.HeldoutPublicGraphContextV2,
        catalogue: HeldoutLegalActionCatalogueV2,
        action: tuple[int, int, int],
        arm: str,
        lane: ObservationLaneV2,
        support_epoch_chain: HeldoutSupportEpochChainV2,
    ) -> None:
        self._anchor = _require_execution_anchor(anchor)
        self._context = _registered_context(context)
        self._catalogue = _validated_catalogue(
            self._context,
            catalogue,
        )
        self._action = _action(action)
        self._row_binding = observation_row_binding_v2(
            self._context,
            self._catalogue,
            self._action,
        )
        self._arm = _arm(arm)
        self._lane = _lane(lane)
        self._support_epoch_chain = verify_heldout_support_epoch_chain_v2(
            self._context,
            self._row_binding,
            self._arm,
            support_epoch_chain,
        )
        self._support_epoch = self._support_epoch_chain.leaf
        self._pair = arm_isolated_stream_pair_identity_v2(
            self._anchor,
            self._context,
            self._catalogue,
            self._action,
            self._arm,
            self._support_epoch_chain,
        )
        self._stream_id = self._pair.stream_id(self._lane)
        self._seed = _stream_seed(
            self._pair.raw_word_pairing_group_id(self._lane),
            self._lane,
        )
        board, empty_cells, reward = _merge_row(
            self._context,
            self._catalogue.state,
            self._action,
        )
        law_denominator, integer_law = _integer_law(
            _environment_law(self._anchor, self._context)
        )
        outcome_denominator = len(empty_cells) * law_denominator
        self._merged_board = board
        self._empty_cells = empty_cells
        self._reward = reward
        self._law_denominator = law_denominator
        self._integer_law = integer_law
        self._outcome_denominator = outcome_denominator
        self._acceptance_limit = (
            _UINT64_MODULUS
            - (_UINT64_MODULUS % outcome_denominator)
        )
        self._successor_cache: dict[
            tuple[int, int],
            tuple[HeldoutSymbolicGraphStateV2, bool, bool],
        ] = {}
        self._accepted_draws = 0
        self._random_word_calls = 0
        self._rejection_count = 0

    @property
    def pair_id(self) -> str:
        return self._pair.pair_id

    @property
    def row_binding_id(self) -> str:
        return self._row_binding.row_binding_id

    @property
    def stream_id(self) -> str:
        return self._stream_id

    @property
    def raw_word_pairing_group_id(self) -> str:
        return self._pair.raw_word_pairing_group_id(self._lane)

    @property
    def accepted_draw_count(self) -> int:
        return self._accepted_draws

    def work_snapshot(self) -> HeldoutTransitionStreamWorkV2:
        return HeldoutTransitionStreamWorkV2(
            self._stream_id,
            self._accepted_draws,
            self._random_word_calls,
            self._rejection_count,
        )

    def draw(self) -> HeldoutObservedJointTransitionV2:
        start = self._random_word_calls + 1
        words: list[int] = []
        while True:
            word_index = self._random_word_calls + 1
            word = _splitmix64(
                self._seed + _SPLITMIX_GAMMA * word_index
            )
            self._random_word_calls += 1
            words.append(word)
            if word >= self._acceptance_limit:
                self._rejection_count += 1
                continue
            token = word % self._outcome_denominator
            empty_index = token // self._law_denominator
            rank_token = token % self._law_denominator
            spawn_rank = _rank_from_token(
                self._integer_law,
                rank_token,
            )
            break
        outcome_key = (empty_index, spawn_rank)
        outcome = self._successor_cache.get(outcome_key)
        if outcome is None:
            successor = list(self._merged_board)
            successor[self._empty_cells[empty_index]] = spawn_rank
            provisional = HeldoutSymbolicGraphStateV2(tuple(successor))
            failure = not _legal_actions(self._context, provisional)
            next_state = HeldoutSymbolicGraphStateV2(
                tuple(successor),
                failure,
            )
            terminal = (
                failure or self._catalogue.remaining_horizon == 1
            )
            outcome = (next_state, failure, terminal)
            self._successor_cache[outcome_key] = outcome
        else:
            next_state, failure, terminal = outcome
        self._accepted_draws += 1
        digest = _raw_draw_digest(
            pair_id=self._pair.pair_id,
            stream_id=self._stream_id,
            raw_word_pairing_group_id=(
                self._pair.raw_word_pairing_group_id(self._lane)
            ),
            arm=self._arm,
            lane=self._lane,
            accepted_draw_index=self._accepted_draws,
            random_word_start_index=start,
            next_state=next_state,
            reward=self._reward,
            failure=failure,
            terminal=terminal,
            words=tuple(words),
        )
        commitment = HeldoutRawDrawCommitmentV2(
            self._pair.pair_id,
            self._stream_id,
            self._pair.raw_word_pairing_group_id(self._lane),
            self._arm,
            self._lane,
            self._accepted_draws,
            start,
            len(words),
            len(words) - 1,
            digest,
        )
        return HeldoutObservedJointTransitionV2(
            self._anchor.anchor_id,
            self._context.context_id,
            self._row_binding.row_binding_id,
            self._catalogue.catalogue_id,
            self._support_epoch.epoch_id,
            self._support_epoch_chain.chain_id,
            self._pair.pair_id,
            self._stream_id,
            self._pair.raw_word_pairing_group_id(self._lane),
            self._arm,
            self._lane,
            self._catalogue.state,
            self._action,
            self._catalogue.remaining_horizon,
            self._accepted_draws,
            next_state,
            self._reward,
            failure,
            terminal,
            commitment,
        )


def open_heldout_target_transition_stream_v2(
    anchor: final_authority.V072RemoteMainAnchorV1,
    context: prereg.HeldoutPublicGraphContextV2,
    catalogue: HeldoutLegalActionCatalogueV2,
    action: tuple[int, int, int],
    arm: str,
    lane: ObservationLaneV2,
    support_epoch_chain: HeldoutSupportEpochChainV2,
) -> AnchorGatedHeldoutTransitionStreamV2:
    # Validate the external gate before a mutable target-tape object exists.
    _require_execution_anchor(anchor)
    return AnchorGatedHeldoutTransitionStreamV2(
        anchor,
        context,
        catalogue,
        action,
        arm,
        lane,
        support_epoch_chain,
    )


@dataclass(frozen=True, slots=True)
class HeldoutTransitionReplayVerificationV2:
    anchor_id: str
    observation_id: str
    stream_id: str
    replayed_accepted_draws: int
    replayed_random_word_calls: int
    replayed_rejections: int
    tuple_replay_passed: bool = True
    execution_lane: str = "TRUSTED_TARGET_OBSERVATION_REPLAY"

    def __post_init__(self) -> None:
        _cid(self.anchor_id, "replay anchor")
        _cid(self.observation_id, "replay observation")
        _cid(self.stream_id, "replay stream")
        if (
            type(self.replayed_accepted_draws) is not int
            or self.replayed_accepted_draws <= 0
            or type(self.replayed_random_word_calls) is not int
            or self.replayed_random_word_calls
            < self.replayed_accepted_draws
            or type(self.replayed_rejections) is not int
            or self.replayed_rejections < 0
            or self.replayed_random_word_calls
            != self.replayed_accepted_draws + self.replayed_rejections
            or self.tuple_replay_passed is not True
            or self.execution_lane
            != "TRUSTED_TARGET_OBSERVATION_REPLAY"
        ):
            raise HeldoutGraphTransitionObserverV2InvariantViolation(
                "held-out transition replay verification is invalid"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_heldout_transition_replay.v2",
            "schema_version": SCHEMA_VERSION,
            "anchor_id": self.anchor_id,
            "observation_id": self.observation_id,
            "stream_id": self.stream_id,
            "replayed_accepted_draws": self.replayed_accepted_draws,
            "replayed_random_word_calls": self.replayed_random_word_calls,
            "replayed_rejections": self.replayed_rejections,
            "tuple_replay_passed": True,
            "execution_lane": self.execution_lane,
        }

    @property
    def verification_id(self) -> str:
        return _content_id("replay", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "verification_id": self.verification_id}


def verify_heldout_observed_transition_v2(
    anchor: final_authority.V072RemoteMainAnchorV1,
    context: prereg.HeldoutPublicGraphContextV2,
    catalogue: HeldoutLegalActionCatalogueV2,
    action: tuple[int, int, int],
    arm: str,
    lane: ObservationLaneV2,
    support_epoch_chain: HeldoutSupportEpochChainV2,
    observation: HeldoutObservedJointTransitionV2,
) -> HeldoutTransitionReplayVerificationV2:
    canonical_anchor = _require_execution_anchor(anchor)
    if type(observation) is not HeldoutObservedJointTransitionV2:
        raise HeldoutGraphTransitionObserverV2InvariantViolation(
            "replay rejects a noncanonical held-out observation"
        )
    stream = open_heldout_target_transition_stream_v2(
        canonical_anchor,
        context,
        catalogue,
        action,
        arm,
        lane,
        support_epoch_chain,
    )
    if (
        observation.anchor_id != canonical_anchor.anchor_id
        or observation.context_id != context.context_id
        or observation.row_binding_id != stream.row_binding_id
        or observation.catalogue_id != catalogue.catalogue_id
        or observation.support_epoch_id
        != support_epoch_chain.leaf.epoch_id
        or observation.support_epoch_chain_id
        != support_epoch_chain.chain_id
        or observation.pair_id != stream.pair_id
        or observation.stream_id != stream.stream_id
        or observation.raw_word_pairing_group_id
        != stream.raw_word_pairing_group_id
        or observation.arm != arm
        or observation.lane is not lane
    ):
        raise HeldoutGraphTransitionObserverV2InvariantViolation(
            "observation identity does not match the replay authority"
        )
    replayed: HeldoutObservedJointTransitionV2 | None = None
    for _ in range(observation.accepted_draw_index):
        replayed = stream.draw()
    if (
        replayed is None
        or replayed.to_document() != observation.to_document()
    ):
        raise HeldoutGraphTransitionObserverV2InvariantViolation(
            "observed joint tuple differs from deterministic raw replay"
        )
    work = stream.work_snapshot()
    return HeldoutTransitionReplayVerificationV2(
        canonical_anchor.anchor_id,
        observation.observation_id,
        stream.stream_id,
        work.accepted_draws,
        work.random_word_calls,
        work.rejection_count,
    )


@dataclass(frozen=True, slots=True)
class EvaluationOnlyExactAtomV2:
    anchor_id: str
    environment_manifest_id: str
    context_id: str
    catalogue_id: str
    action: tuple[int, int, int]
    next_state: HeldoutSymbolicGraphStateV2
    probability: Fraction
    realized_row_reward: Fraction
    failure: bool
    terminal: bool
    execution_lane: str = "EVALUATION_ONLY"

    def __post_init__(self) -> None:
        for value, field in (
            (self.anchor_id, "evaluation anchor"),
            (self.environment_manifest_id, "evaluation environment"),
            (self.context_id, "evaluation context"),
            (self.catalogue_id, "evaluation catalogue"),
        ):
            _cid(value, field)
        _action(self.action)
        if (
            type(self.next_state) is not HeldoutSymbolicGraphStateV2
            or type(self.probability) is not Fraction
            or not 0 < self.probability <= 1
            or type(self.realized_row_reward) is not Fraction
            or not 0 <= self.realized_row_reward <= 1
            or type(self.failure) is not bool
            or self.failure != self.next_state.failure
            or type(self.terminal) is not bool
            or self.execution_lane != "EVALUATION_ONLY"
        ):
            raise HeldoutGraphTransitionObserverV2InvariantViolation(
                "evaluation-only exact atom is invalid"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_evaluation_only_exact_atom.v2",
            "schema_version": SCHEMA_VERSION,
            "anchor_id": self.anchor_id,
            "environment_manifest_id": self.environment_manifest_id,
            "context_id": self.context_id,
            "catalogue_id": self.catalogue_id,
            "action": list(self.action),
            "next_state": self.next_state.to_document(),
            "probability": _fdoc(self.probability),
            "realized_row_reward": _fdoc(self.realized_row_reward),
            "failure": self.failure,
            "terminal": self.terminal,
            "execution_lane": self.execution_lane,
        }

    @property
    def atom_id(self) -> str:
        return _content_id("evaluation_atom", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "atom_id": self.atom_id}


def evaluation_only_exact_atoms_v2(
    anchor: final_authority.V072RemoteMainAnchorV1,
    context: prereg.HeldoutPublicGraphContextV2,
    catalogue: HeldoutLegalActionCatalogueV2,
    action: tuple[int, int, int],
) -> tuple[EvaluationOnlyExactAtomV2, ...]:
    """Reveal one frozen-law row only in the evaluation lane."""

    canonical_anchor = _require_execution_anchor(anchor)
    registered = _registered_context(context)
    canonical_catalogue = _validated_catalogue(registered, catalogue)
    canonical_action = _action(action)
    if canonical_action not in canonical_catalogue.actions:
        raise HeldoutGraphTransitionObserverV2InvariantViolation(
            "evaluation action is outside the complete legal catalogue"
        )
    board, empty, reward = _merge_row(
        registered,
        canonical_catalogue.state,
        canonical_action,
    )
    law = _environment_law(canonical_anchor, registered)
    atoms: list[EvaluationOnlyExactAtomV2] = []
    for cell in empty:
        for rank, rank_probability in law:
            successor = list(board)
            successor[cell] = rank
            provisional = HeldoutSymbolicGraphStateV2(tuple(successor))
            failure = not _legal_actions(registered, provisional)
            next_state = HeldoutSymbolicGraphStateV2(
                tuple(successor),
                failure,
            )
            atoms.append(
                EvaluationOnlyExactAtomV2(
                    canonical_anchor.anchor_id,
                    _anchor_environment_manifest_id(canonical_anchor),
                    registered.context_id,
                    canonical_catalogue.catalogue_id,
                    canonical_action,
                    next_state,
                    Fraction(1, len(empty)) * rank_probability,
                    reward,
                    failure,
                    failure
                    or canonical_catalogue.remaining_horizon == 1,
                )
            )
    if sum((atom.probability for atom in atoms), Fraction(0)) != 1:
        raise RuntimeError("evaluation-only exact atom row is not normalized")
    return tuple(atoms)


__all__ = [
    "AnchorGatedHeldoutTransitionStreamV2",
    "ArmIsolatedTransitionStreamPairV2",
    "EvaluationOnlyExactAtomV2",
    "EXACT_IID_IMPLEMENTATION_CLAIMED",
    "HeldoutGraphTransitionObserverV2InvariantViolation",
    "HeldoutLegalActionCatalogueV2",
    "HeldoutObservationRowBindingV2",
    "HeldoutObservedJointTransitionV2",
    "HeldoutRawDrawCommitmentV2",
    "HeldoutSupportEpochChainV2",
    "HeldoutSupportEpochIdentityV2",
    "HeldoutSymbolicGraphStateV2",
    "HeldoutTransitionReplayVerificationV2",
    "HeldoutTransitionStreamWorkV2",
    "OBSERVER_SEMANTICS_ID",
    "OFFICIAL_EXECUTION_ALLOWED",
    "MAX_FROZEN_SUPPORT_MEMBERS_PER_ROW_V2",
    "MAX_OBSERVER_STREAM_EPOCH_INDEX_V2",
    "ObservationLaneV2",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "RANDOMNESS_IMPLEMENTATION",
    "SAMPLE_EFFICIENCY_GATE_STATUS",
    "SCHEMA_VERSION",
    "STATISTICAL_CLAIM_SCOPE",
    "TargetExecutionAnchorPlaceholderV1",
    "arm_isolated_stream_pair_identity_v2",
    "bind_target_execution_anchor_placeholder_v1",
    "evaluation_only_exact_atoms_v2",
    "legal_action_catalogue_v2",
    "open_heldout_target_transition_stream_v2",
    "observation_row_binding_v2",
    "root_state_v2",
    "support_epoch_identity_v2",
    "support_epoch_chain_v2",
    "verify_heldout_support_epoch_chain_v2",
    "verify_heldout_observed_transition_v2",
]
