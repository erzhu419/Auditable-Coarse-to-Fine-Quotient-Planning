"""V0-054B one-row action-local H2 semantic-switch control.

The registered control starts from a four-observed/one-missing model, plans
entirely against that partial model, and obtains a failed unrestricted-value
certificate.  A non-authorizing challenger frontier identifies the one
off-policy row that can close the failed proof.  Only after a row-necessity
proof and request are frozen may the authority call the registered LMB kernel.
The exact row is appended to a new immutable model epoch, the model-only
action-indexed proof DAG is incrementally recomputed, and the reachable H1
action switches strictly from reward-zero ``N`` to reward-one ``M``.

This is a finite construction control.  It does not claim general causal
minimality, automatic coordinate invention, learned dynamics, durable or
cross-query reuse, sample savings, or workload economics.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from fractions import Fraction
import hashlib
import inspect
from pathlib import Path
import threading
from typing import Any, Mapping

from acfqp.domains.matching_buffer import (
    LMBAction,
    LMBKernel,
    LMBState,
    LMBStatus,
)
from acfqp.h2_action_indexed_proof_dag_v1 import (
    ActionIndexedEpochExecutionV1,
    ActionIndexedH2ModelV1,
    ActionIndexedH2QueryV1,
    ActionIndexedInvalidationManifestV1,
    ActionIndexedModelDeltaV1,
    ActionIndexedPreExecutionInvalidationV1,
    ActionIndexedProofRuntimeV1,
    CandidateAction,
    GroundRowName,
    GroundRowStatus,
    ModelEpoch,
    ProofAddress,
    authorize_action_indexed_final_epoch_v1,
    derive_action_indexed_delta_and_invalidation_v1,
    derive_action_indexed_preexecution_invalidation_v1,
    execute_action_indexed_epoch_v1,
    registered_action_indexed_h2_query_v1,
    registered_final_action_indexed_h2_model_v1,
    registered_first_action_indexed_h2_model_v1,
)
from acfqp.observation_partial_rapm_v1 import (
    CanonicalGroundActionV1,
    CanonicalStateObservationV1,
    PlanningKind,
    TrustedCompleteActionCatalogueV1,
)
from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id


_CANONICAL_LMB_STEP = LMBKernel.step

CONTRACT_VERSION = "1.18.0"
SCHEMA_VERSION = "1.0.0"
PROFILE_KEY = "lmb_h2_action_local_semantic_switch_v0"
SUCCESS_STATUS = "CERTIFIED_REGISTERED_H2_ACTION_LOCAL_SEMANTIC_SWITCH_CONTROL"

EXPECTED_X0_STATE_ID = (
    "923ac69167104293200e5f71263951ec6207d04b576d759fa28f589ce5940c37"
)
EXPECTED_X1_STATE_ID = (
    "52acc4ceec0b25ef96c6c039e39adfdd5cbd728d9b974b7ebb029e4a7ec62226"
)
EXPECTED_GROUND_ROW_IDS = {
    GroundRowName.S: (
        "cf0ebe94dc11825e0f1aa820487a5439efd1615d5fd2b95b16346f61c9b8274b"
    ),
    GroundRowName.M: (
        "a5bf62ceb55ad0f6624a52b21a0d5f52739d5b2fbd3db8198536ccb250aa4ae0"
    ),
    GroundRowName.N1: (
        "a5a288985739f75fc7540a5d0df7b0d4a5e6d56b12989fb596b9dcdf4712b8d6"
    ),
    GroundRowName.N2: (
        "c4566f8e43470f739188052a430a58cf8e3b956025f9d548885bbd1b64c40aa3"
    ),
    GroundRowName.N3: (
        "db320fcc2bc7f7ad0fdbd4199f974574d581181e377f04c2c9465ffd3aab5503"
    ),
}
EXPECTED_GROUND_ACTION_IDS = {
    GroundRowName.S: (
        "ecdb44bfdbb033cb123af61b70f31e9d05af1dc4e44a9a3afa89665c71cc9d47"
    ),
    GroundRowName.M: (
        "67abfc4c846912ce3ed003eb6166940cab0544c3aca1b24ddddedfdb01db88b4"
    ),
    GroundRowName.N1: (
        "06e38f83f744b311078d3b79238bf87226e718b9eb765d3c90f11d5de4b1bc8e"
    ),
    GroundRowName.N2: (
        "7e669425c9fcd4a227741ed1bbf4f585a037cbdb2cb4256077174212eedf610f"
    ),
    GroundRowName.N3: (
        "a2458fcd6e21916217dd3651c1823709e4674a1a9268669fab4d32410abdde54"
    ),
}
EXPECTED_KERNEL_SOURCE_SHA256 = (
    "82bef64d20aa10bc6920fd67a9dc7db0c8c7e310170f93bf4e90c7995d5416da"
)
EXPECTED_KERNEL_STEP_SOURCE_SHA256 = (
    "5849a61d4424df3146499125dcee95623a769caa539655ca66d53af9157ee6af"
)
EXPECTED_GATE_EXECUTE_SOURCE_SHA256 = (
    "ecb91ec72c2397463986baca044693b9e79954632126b24a425f6b908f522084"
)
EXPECTED_CANONICAL_IDS = {
    "structural": "55a22b7617349c2d89bd7b9be940597cd851fc2e9e2a04ec6444e21bfbc83bc0",
    "fixture": "c62be2d328d5a5ffc86d9b844c920b251345031e2667507ca7cc728e3c51cd92",
    "query": "aa6f149330c798d2650fea28d7d5b489389cb5a80d24f6feb8fc06fdececc7f8",
    "first_model": "ba0da7534a75a20f3c77a1cd097c6864a60bb8778df0ef2de6b57089767e0f32",
    "first_dag_model": "b986f0b8f1864e2139eabc3979fb9448f2fc39554ee4a80a734ca664ef525dab",
    "first_execution": "cf36bf88a5cc41e3962e3b51bc87ba39eadb61827aabd909844934717eb51975",
    "support_frontier": "a2f64571975a5047772cd7a2ca41469ad5d46b67851cc47cb01ba778e4588907",
    "challenger_frontier": "ed6e64de6382eba3de37e64a4eec19aedca4461ab9f34c7870e7867aec4cfd37",
    "necessity": "0da69443e0be5a9f3c14dbcc854f72e11aaa561a756388e719763fe21840288f",
    "request": "2b48e517f78b32c0f63ed658b6b55e9cbdeeb896681d8ba48be95dc4d3c4630d",
    "receipt": "0dc2ac0508694145021721f73b7c068da371d879acf6e150fab764baa151cdad",
    "evidence_bundle": "76b4d028d9cda285ed6692d940d7d5a2062f9bf7859eb5f01fe01426a3f2f85c",
    "final_model": "764b2a8b754d22edc7356238f461b823db3bf4b206227cdb7c6a19751288dcff",
    "final_dag_model": "da7f9fba48cd455dd1a7c68db4daa5ddba36040aed64a27aa57f54f2a9f28d2d",
    "delta": "fbd6a5e89f363b45f0198c55d2b63342fb053cb83e1ae3302aa06189185b5c73",
    "pre_invalidation": "fb6112135f098fc4144b24cbe9dec7ec4c727eabb0484f9ed8e4dbcf218d11c0",
    "final_execution": "5d65fd780ca38a9e6c21314156eee9f94b9777566ec42737762e5ecec2cdd240",
    "invalidation": "f69fbdd143e68f19dc42d0f2a1c7ab76876433ebdca960770204fe689c0c1c17",
    "overlay": "0614d53923d44abae6ffbea765743bb11524ae33096dbe282eb9f4d2dc9824a2",
    "switch": "84848291d930d2390e5985839feb9f743be2ae6ccbe631f0e2db6cb56f5ec1c8",
    "trace": "5754c78ec80163abdfdbb5a7b8f85c1a772f77e91710a436b2442e210449d721",
    "result": "1389019bf1b5eddd088246ec591a100fef243069615294d1c686e1242b24ffa1",
    "verification": "6d94adcc5a3a0605e6e9e1599c9861e1a96fcea6aa2c0413ae260a513a1cb41f",
}

TILE_TYPES = (1, 0, 0, 0, 1, 1)
BLOCKERS = (
    frozenset({4, 5}),
    frozenset({4}),
    frozenset({4}),
    frozenset({4, 5}),
    frozenset(),
    frozenset(),
)
TYPE_COUNT = 2
CAPACITY = 3
MAX_LAYERS = 4

DOMAIN_TAGS = {
    "structural": "acfqp:h2-action-local-structural-authority:v1",
    "fixture": "acfqp:h2-action-local-registered-fixture:v1",
    "row_evidence": "acfqp:h2-action-local-ground-row-evidence:v1",
    "model_epoch": "acfqp:h2-action-local-model-epoch:v1",
    "support_frontier": "acfqp:h2-selected-support-frontier:v1",
    "challenger_frontier": "acfqp:h2-unrestricted-challenger-frontier:v1",
    "necessity": "acfqp:h2-action-local-row-necessity-proof:v1",
    "authority": "acfqp:h2-action-local-transition-authority:v1",
    "request": "acfqp:h2-action-local-evidence-request:v1",
    "receipt": "acfqp:h2-action-local-transition-receipt:v1",
    "bundle": "acfqp:h2-action-local-evidence-bundle:v1",
    "overlay": "acfqp:h2-action-local-overlay-build:v1",
    "switch": "acfqp:h2-action-local-policy-switch-witness:v1",
    "trace": "acfqp:h2-action-local-access-trace:v1",
    "result": "acfqp:h2-action-local-semantic-switch-result:v1",
    "verification": "acfqp:h2-action-local-semantic-switch-verification:v1",
}
if len(DOMAIN_TAGS) != len(set(DOMAIN_TAGS.values())):  # pragma: no cover
    raise RuntimeError("V0-054B content domains must be unique")


class ActionLocalSemanticSwitchInvariantViolation(ValueError):
    """The registered authority, evidence, epoch, or certificate chain is invalid."""


_KERNEL_GATE_LOCK = threading.Lock()


def _content_id(role: str, payload: Mapping[str, Any]) -> str:
    try:
        encoded = canonical_json_bytes(dict(payload))
        domain = DOMAIN_TAGS[role]
    except (KeyError, TypeError, ValueError) as error:
        raise ActionLocalSemanticSwitchInvariantViolation(str(error)) from error
    return hashlib.sha256(domain.encode("utf-8") + b"\x00" + encoded).hexdigest()


def _cid(value: Any, field: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise ActionLocalSemanticSwitchInvariantViolation(
            f"{field} must be a full content ID"
        ) from error


def _integer(value: Any, field: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise ActionLocalSemanticSwitchInvariantViolation(
            f"{field} must be an exact integer >= {minimum}"
        )
    return value


def _fraction(value: Any, field: str) -> Fraction:
    if isinstance(value, bool) or not isinstance(value, (int, Fraction)):
        raise ActionLocalSemanticSwitchInvariantViolation(f"{field} must be exact")
    return Fraction(value)


def _fdoc(value: Fraction) -> dict[str, int]:
    exact = Fraction(value)
    return {"numerator": exact.numerator, "denominator": exact.denominator}


def _planning_kind(status: LMBStatus) -> PlanningKind:
    return {
        LMBStatus.ACTIVE: PlanningKind.ACTIVE,
        LMBStatus.SUCCESS: PlanningKind.SUCCESS,
        LMBStatus.FAILURE: PlanningKind.FAILURE,
    }[status]


def _state_observation(state: LMBState) -> CanonicalStateObservationV1:
    return CanonicalStateObservationV1(
        (
            f"removed={state.removed_mask};buffer={state.buffer};"
            f"status={state.status.value}"
        ),
        state.removed_mask,
        state.buffer,
        state.status.value,
        _planning_kind(state.status),
    )


def _literal_kernel_v1() -> LMBKernel:
    return LMBKernel(
        TILE_TYPES,
        BLOCKERS,
        TYPE_COUNT,
        CAPACITY,
        MAX_LAYERS,
    )


def _kernel_source_sha256() -> str:
    source = inspect.getsourcefile(LMBKernel)
    if not source:
        raise ActionLocalSemanticSwitchInvariantViolation(
            "registered LMB kernel has no readable source file"
        )
    try:
        payload = Path(source).read_bytes()
    except OSError as error:
        raise ActionLocalSemanticSwitchInvariantViolation(
            "registered LMB kernel source cannot be read"
        ) from error
    return hashlib.sha256(payload).hexdigest()


def _assert_canonical_step_callable() -> None:
    try:
        step_source = inspect.getsource(_CANONICAL_LMB_STEP).encode("utf-8")
        step_file = Path(inspect.getsourcefile(_CANONICAL_LMB_STEP) or "").resolve()
        kernel_file = Path(inspect.getsourcefile(LMBKernel) or "").resolve()
    except (OSError, TypeError) as error:
        raise ActionLocalSemanticSwitchInvariantViolation(
            "canonical LMB step implementation cannot be inspected"
        ) from error
    if (
        getattr(_CANONICAL_LMB_STEP, "__module__", None)
        != "acfqp.domains.matching_buffer"
        or getattr(_CANONICAL_LMB_STEP, "__qualname__", None) != "LMBKernel.step"
        or step_file != kernel_file
        or hashlib.sha256(step_source).hexdigest()
        != EXPECTED_KERNEL_STEP_SOURCE_SHA256
    ):
        raise ActionLocalSemanticSwitchInvariantViolation(
            "canonical LMB step callable identity changed"
        )


def _assert_literal_kernel(kernel: LMBKernel) -> None:
    if type(kernel) is not LMBKernel or (
        kernel.tile_types,
        kernel.blockers,
        kernel.type_count,
        kernel.capacity,
        kernel.max_layers,
    ) != (TILE_TYPES, BLOCKERS, TYPE_COUNT, CAPACITY, MAX_LAYERS):
        raise ActionLocalSemanticSwitchInvariantViolation(
            "ground authority requires the exact registered literal kernel"
        )
    if _kernel_source_sha256() != EXPECTED_KERNEL_SOURCE_SHA256:
        raise ActionLocalSemanticSwitchInvariantViolation(
            "registered LMB kernel source identity changed"
        )
    _assert_canonical_step_callable()


def _structural_payload() -> dict[str, Any]:
    return {
        "schema": "acfqp.h2_action_local_structural_authority.v1",
        "schema_version": SCHEMA_VERSION,
        "profile_key": PROFILE_KEY,
        "kernel_class": "acfqp.domains.matching_buffer.LMBKernel",
        "tile_types": list(TILE_TYPES),
        "blockers": [sorted(item) for item in BLOCKERS],
        "type_count": TYPE_COUNT,
        "capacity": CAPACITY,
        "max_layers": MAX_LAYERS,
        "transition_semantics": "CANONICAL_LMB_DETERMINISTIC_STEP_V1",
        "kernel_source_sha256": _kernel_source_sha256(),
    }


def _structural_id() -> str:
    return _content_id("structural", _structural_payload())


@dataclass(frozen=True, slots=True)
class RegisteredActionLocalFixtureV1:
    structural_id: str
    initial_state: CanonicalStateObservationV1
    downstream_state: CanonicalStateObservationV1
    stage_zero_action: CanonicalGroundActionV1
    downstream_catalogue: TrustedCompleteActionCatalogueV1
    row_names: tuple[GroundRowName, ...]
    ground_row_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        _cid(self.structural_id, "fixture structural_id")
        if (
            type(self.initial_state) is not CanonicalStateObservationV1
            or type(self.downstream_state) is not CanonicalStateObservationV1
            or type(self.stage_zero_action) is not CanonicalGroundActionV1
            or type(self.downstream_catalogue)
            is not TrustedCompleteActionCatalogueV1
        ):
            raise ActionLocalSemanticSwitchInvariantViolation(
                "fixture rejects copied state/action/catalogue artifacts"
            )
        if (
            self.structural_id != _structural_id()
            or self.initial_state.state_id != EXPECTED_X0_STATE_ID
            or self.downstream_state.state_id != EXPECTED_X1_STATE_ID
            or self.stage_zero_action.state_id != self.initial_state.state_id
            or self.stage_zero_action.action_key != "tile=4"
            or self.stage_zero_action.action_id
            != EXPECTED_GROUND_ACTION_IDS[GroundRowName.S]
            or self.stage_zero_action.ground_row_id
            != EXPECTED_GROUND_ROW_IDS[GroundRowName.S]
            or self.downstream_catalogue.state_id != self.downstream_state.state_id
            or self.downstream_catalogue.trusted_observer_id != self.structural_id
            or self.downstream_catalogue.complete is not True
            or self.row_names != tuple(GroundRowName)
            or self.ground_row_ids
            != tuple(EXPECTED_GROUND_ROW_IDS[name] for name in GroundRowName)
        ):
            raise ActionLocalSemanticSwitchInvariantViolation(
                "registered fixture identity changed"
            )
        expected_keys = {"tile=0", "tile=1", "tile=2", "tile=3"}
        if {
            item.action_key for item in self.downstream_catalogue.actions
        } != expected_keys:
            raise ActionLocalSemanticSwitchInvariantViolation(
                "downstream complete action catalogue changed"
            )
        if {
            item.action_id for item in self.downstream_catalogue.actions
        } != {
            EXPECTED_GROUND_ACTION_IDS[name]
            for name in (
                GroundRowName.M,
                GroundRowName.N1,
                GroundRowName.N2,
                GroundRowName.N3,
            )
        }:
            raise ActionLocalSemanticSwitchInvariantViolation(
                "downstream action identities changed"
            )

    def action(self, name: GroundRowName) -> CanonicalGroundActionV1:
        if type(name) is not GroundRowName:
            raise ActionLocalSemanticSwitchInvariantViolation(
                "fixture action lookup requires the exact enum"
            )
        if name is GroundRowName.S:
            return self.stage_zero_action
        tile = {
            GroundRowName.M: 0,
            GroundRowName.N1: 1,
            GroundRowName.N2: 2,
            GroundRowName.N3: 3,
        }[name]
        return next(
            item
            for item in self.downstream_catalogue.actions
            if item.action_key == f"tile={tile}"
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h2_action_local_registered_fixture.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "structural_id": self.structural_id,
            "initial_state": self.initial_state.to_document(),
            "downstream_state": self.downstream_state.to_document(),
            "stage_zero_action": self.stage_zero_action.to_document(),
            "downstream_catalogue": self.downstream_catalogue.to_document(),
            "row_names": [item.value for item in self.row_names],
            "ground_row_ids": list(self.ground_row_ids),
        }

    @property
    def fixture_id(self) -> str:
        return _content_id("fixture", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "fixture_id": self.fixture_id}


def registered_action_local_fixture_v1() -> RegisteredActionLocalFixtureV1:
    """Build the registered fixture without invoking ``LMBKernel.step``."""

    x0 = _state_observation(LMBState(32, (0, 1), LMBStatus.ACTIVE))
    x1 = _state_observation(LMBState(48, (0, 2), LMBStatus.ACTIVE))
    s = CanonicalGroundActionV1(x0.state_id, "tile=4", TILE_TYPES[4])
    actions = tuple(
        sorted(
            (
                CanonicalGroundActionV1(
                    x1.state_id,
                    f"tile={tile}",
                    TILE_TYPES[tile],
                )
                for tile in (0, 1, 2, 3)
            ),
            key=lambda item: item.action_id,
        )
    )
    catalogue = TrustedCompleteActionCatalogueV1(
        x1.state_id,
        actions,
        _structural_id(),
    )
    return RegisteredActionLocalFixtureV1(
        _structural_id(),
        x0,
        x1,
        s,
        catalogue,
        tuple(GroundRowName),
        tuple(EXPECTED_GROUND_ROW_IDS[name] for name in GroundRowName),
    )


class EvidenceLane(str, Enum):
    OFFLINE_REGISTERED_BASE = "OFFLINE_REGISTERED_BASE"
    QUERY_LOCAL_AUTHORIZED = "QUERY_LOCAL_AUTHORIZED"


@dataclass(frozen=True, slots=True)
class ActionLocalGroundRowEvidenceV1:
    name: GroundRowName
    state_id: str
    action_id: str
    ground_row_id: str
    successor_state: CanonicalStateObservationV1
    reward: Fraction
    failure: bool
    terminal: bool
    lane: EvidenceLane

    def __post_init__(self) -> None:
        if type(self.name) is not GroundRowName or type(self.lane) is not EvidenceLane:
            raise ActionLocalSemanticSwitchInvariantViolation(
                "ground-row evidence enum changed"
            )
        for value in (self.state_id, self.action_id, self.ground_row_id):
            _cid(value, "ground-row evidence identity")
        if type(self.successor_state) is not CanonicalStateObservationV1:
            raise ActionLocalSemanticSwitchInvariantViolation(
                "ground-row evidence rejects copied successor"
            )
        object.__setattr__(self, "reward", _fraction(self.reward, "row reward"))
        if type(self.failure) is not bool or type(self.terminal) is not bool:
            raise ActionLocalSemanticSwitchInvariantViolation(
                "row failure/terminal flags must be exact booleans"
            )
        expected_reward = Fraction(1) if self.name is GroundRowName.M else Fraction(0)
        expected_lane = (
            EvidenceLane.QUERY_LOCAL_AUTHORIZED
            if self.name is GroundRowName.M
            else EvidenceLane.OFFLINE_REGISTERED_BASE
        )
        expected_state_id = (
            EXPECTED_X0_STATE_ID
            if self.name is GroundRowName.S
            else EXPECTED_X1_STATE_ID
        )
        expected_successor = {
            GroundRowName.S: _state_observation(
                LMBState(48, (0, 2), LMBStatus.ACTIVE)
            ),
            GroundRowName.N1: _state_observation(
                LMBState(50, (1, 2), LMBStatus.ACTIVE)
            ),
            GroundRowName.N2: _state_observation(
                LMBState(52, (1, 2), LMBStatus.ACTIVE)
            ),
            GroundRowName.N3: _state_observation(
                LMBState(56, (1, 2), LMBStatus.ACTIVE)
            ),
            GroundRowName.M: _state_observation(
                LMBState(49, (0, 0), LMBStatus.ACTIVE)
            ),
        }[self.name]
        if (
            self.state_id != expected_state_id
            or self.action_id != EXPECTED_GROUND_ACTION_IDS[self.name]
            or self.ground_row_id != EXPECTED_GROUND_ROW_IDS[self.name]
            or self.successor_state != expected_successor
            or self.reward != expected_reward
            or self.failure is not False
            or self.terminal is not False
            or self.lane is not expected_lane
        ):
            raise ActionLocalSemanticSwitchInvariantViolation(
                "registered row evidence semantics changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h2_action_local_ground_row_evidence.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "name": self.name.value,
            "state_id": self.state_id,
            "action_id": self.action_id,
            "ground_row_id": self.ground_row_id,
            "successor_state": self.successor_state.to_document(),
            "reward": _fdoc(self.reward),
            "failure": self.failure,
            "terminal": self.terminal,
            "lane": self.lane.value,
        }

    @property
    def evidence_id(self) -> str:
        return _content_id("row_evidence", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "evidence_id": self.evidence_id}


def _offline_registered_rows_v1(
    fixture: RegisteredActionLocalFixtureV1,
) -> tuple[ActionLocalGroundRowEvidenceV1, ...]:
    if type(fixture) is not RegisteredActionLocalFixtureV1:
        raise ActionLocalSemanticSwitchInvariantViolation(
            "offline rows require the exact registered fixture"
        )
    successor_by_name = {
        GroundRowName.S: fixture.downstream_state,
        GroundRowName.N1: _state_observation(
            LMBState(50, (1, 2), LMBStatus.ACTIVE)
        ),
        GroundRowName.N2: _state_observation(
            LMBState(52, (1, 2), LMBStatus.ACTIVE)
        ),
        GroundRowName.N3: _state_observation(
            LMBState(56, (1, 2), LMBStatus.ACTIVE)
        ),
    }
    result = []
    for name in (
        GroundRowName.S,
        GroundRowName.N1,
        GroundRowName.N2,
        GroundRowName.N3,
    ):
        action = fixture.action(name)
        state_id = (
            fixture.initial_state.state_id
            if name is GroundRowName.S
            else fixture.downstream_state.state_id
        )
        result.append(
            ActionLocalGroundRowEvidenceV1(
                name,
                state_id,
                action.action_id,
                action.ground_row_id,
                successor_by_name[name],
                Fraction(0),
                False,
                False,
                EvidenceLane.OFFLINE_REGISTERED_BASE,
            )
        )
    return tuple(result)


@dataclass(frozen=True, slots=True)
class ActionLocalModelEpochV1:
    epoch_index: int
    fixture_id: str
    query_id: str
    parent_model_id: str | None
    dag_model: ActionIndexedH2ModelV1
    observed_rows: tuple[ActionLocalGroundRowEvidenceV1, ...]
    missing_ground_row_ids: tuple[str, ...]
    immutable: bool = True
    query_local: bool = True
    promotable: bool = False

    def __post_init__(self) -> None:
        _integer(self.epoch_index, "model epoch index", 1)
        for value in (self.fixture_id, self.query_id):
            _cid(value, "model epoch identity")
        if self.parent_model_id is not None:
            _cid(self.parent_model_id, "model parent")
        if type(self.dag_model) is not ActionIndexedH2ModelV1 or (
            type(self.observed_rows) is not tuple
            or any(
                type(item) is not ActionLocalGroundRowEvidenceV1
                for item in self.observed_rows
            )
            or type(self.missing_ground_row_ids) is not tuple
        ):
            raise ActionLocalSemanticSwitchInvariantViolation(
                "model epoch nested artifact type changed"
            )
        for value in self.missing_ground_row_ids:
            _cid(value, "missing ground row")
        names = tuple(item.name for item in self.observed_rows)
        if self.epoch_index == 1:
            if (
                self.parent_model_id is not None
                or self.dag_model.to_document()
                != registered_first_action_indexed_h2_model_v1().to_document()
                or names
                != (
                    GroundRowName.S,
                    GroundRowName.N1,
                    GroundRowName.N2,
                    GroundRowName.N3,
                )
                or self.missing_ground_row_ids
                != (EXPECTED_GROUND_ROW_IDS[GroundRowName.M],)
            ):
                raise ActionLocalSemanticSwitchInvariantViolation(
                    "first model is not the registered immutable 4/1 epoch"
                )
        elif self.epoch_index == 2:
            if (
                self.parent_model_id is None
                or self.dag_model.to_document()
                != registered_final_action_indexed_h2_model_v1().to_document()
                or names != tuple(GroundRowName)
                or self.missing_ground_row_ids
            ):
                raise ActionLocalSemanticSwitchInvariantViolation(
                    "final model is not the registered immutable 5/0 epoch"
                )
        else:
            raise ActionLocalSemanticSwitchInvariantViolation(
                "registered control has exactly two model epochs"
            )
        if (
            self.immutable is not True
            or self.query_local is not True
            or self.promotable is not False
        ):
            raise ActionLocalSemanticSwitchInvariantViolation(
                "model epoch ownership/immutability changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h2_action_local_model_epoch.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "epoch_index": self.epoch_index,
            "fixture_id": self.fixture_id,
            "query_id": self.query_id,
            "parent_model_id": (
                self.parent_model_id
                if self.parent_model_id is not None
                else {
                    "kind": "NOT_APPLICABLE",
                    "reason": "FIRST_QUERY_LOCAL_EPOCH",
                }
            ),
            "dag_model": self.dag_model.to_document(),
            "observed_rows": [item.to_document() for item in self.observed_rows],
            "missing_ground_row_ids": list(self.missing_ground_row_ids),
            "immutable": self.immutable,
            "query_local": self.query_local,
            "promotable": self.promotable,
        }

    @property
    def model_id(self) -> str:
        return _content_id("model_epoch", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "model_id": self.model_id}


@dataclass(frozen=True, slots=True)
class SelectedPolicySupportFrontierV1:
    model_id: str
    execution_id: str
    selected_action: CandidateAction
    supported_ground_row_ids: tuple[str, ...]
    target_ground_row_id: str
    target_is_supported: bool
    authorizing: bool = False

    def __post_init__(self) -> None:
        for value in (
            self.model_id,
            self.execution_id,
            *self.supported_ground_row_ids,
            self.target_ground_row_id,
        ):
            _cid(value, "support frontier identity")
        if (
            type(self.selected_action) is not CandidateAction
            or self.selected_action is not CandidateAction.N
            or self.supported_ground_row_ids
            != tuple(
                EXPECTED_GROUND_ROW_IDS[name]
                for name in (
                    GroundRowName.S,
                    GroundRowName.N1,
                    GroundRowName.N2,
                    GroundRowName.N3,
                )
            )
            or self.target_ground_row_id
            != EXPECTED_GROUND_ROW_IDS[GroundRowName.M]
            or self.target_is_supported is not False
            or self.authorizing is not False
        ):
            raise ActionLocalSemanticSwitchInvariantViolation(
                "selected-policy support frontier changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h2_selected_policy_support_frontier.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "model_id": self.model_id,
            "execution_id": self.execution_id,
            "selected_action": self.selected_action.value,
            "supported_ground_row_ids": list(self.supported_ground_row_ids),
            "target_ground_row_id": self.target_ground_row_id,
            "target_is_supported": self.target_is_supported,
            "authorizing": self.authorizing,
        }

    @property
    def frontier_id(self) -> str:
        return _content_id("support_frontier", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "frontier_id": self.frontier_id}


EXPECTED_CHALLENGER_CIRCUIT = (
    ProofAddress.REGRET_N,
    ProofAddress.U0,
    ProofAddress.ROW_S,
    ProofAddress.U1,
    ProofAddress.Q_M,
    ProofAddress.ROW_M,
)


@dataclass(frozen=True, slots=True)
class UnrestrictedChallengerFrontierV1:
    model_id: str
    query_id: str
    failed_execution_id: str
    selected_audit_id: str
    complete_action_catalogue_id: str
    target_state_id: str
    target_action_id: str
    target_ground_row_id: str
    remaining_horizon: int
    circuit_addresses: tuple[ProofAddress, ...]
    circuit_node_ids: tuple[str, ...]
    unique_missing_maximizer: bool
    authorizing: bool = False

    def __post_init__(self) -> None:
        for value in (
            self.model_id,
            self.query_id,
            self.failed_execution_id,
            self.selected_audit_id,
            self.complete_action_catalogue_id,
            self.target_state_id,
            self.target_action_id,
            self.target_ground_row_id,
            *self.circuit_node_ids,
        ):
            _cid(value, "challenger frontier identity")
        _integer(self.remaining_horizon, "frontier remaining_horizon", 1)
        if (
            self.target_state_id != EXPECTED_X1_STATE_ID
            or self.target_action_id
            != EXPECTED_GROUND_ACTION_IDS[GroundRowName.M]
            or self.target_ground_row_id
            != EXPECTED_GROUND_ROW_IDS[GroundRowName.M]
            or self.remaining_horizon != 1
            or self.circuit_addresses != EXPECTED_CHALLENGER_CIRCUIT
            or len(self.circuit_node_ids) != len(self.circuit_addresses)
            or len(set(self.circuit_node_ids)) != len(self.circuit_node_ids)
            or self.unique_missing_maximizer is not True
            or self.authorizing is not False
        ):
            raise ActionLocalSemanticSwitchInvariantViolation(
                "unrestricted challenger frontier changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h2_unrestricted_challenger_frontier.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "model_id": self.model_id,
            "query_id": self.query_id,
            "failed_execution_id": self.failed_execution_id,
            "selected_audit_id": self.selected_audit_id,
            "complete_action_catalogue_id": self.complete_action_catalogue_id,
            "target_state_id": self.target_state_id,
            "target_action_id": self.target_action_id,
            "target_ground_row_id": self.target_ground_row_id,
            "remaining_horizon": self.remaining_horizon,
            "circuit_addresses": [item.value for item in self.circuit_addresses],
            "circuit_node_ids": list(self.circuit_node_ids),
            "unique_missing_maximizer": self.unique_missing_maximizer,
            "authorizing": self.authorizing,
        }

    @property
    def frontier_id(self) -> str:
        return _content_id("challenger_frontier", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "frontier_id": self.frontier_id}


@dataclass(frozen=True, slots=True)
class ActionLocalRowNecessityProofV1:
    frontier_id: str
    first_model_id: str
    query_id: str
    target_ground_row_id: str
    necessity_reason: str
    old_support_frontier_cannot_authorize: bool
    exact_one_row: bool

    def __post_init__(self) -> None:
        for value in (
            self.frontier_id,
            self.first_model_id,
            self.query_id,
            self.target_ground_row_id,
        ):
            _cid(value, "necessity proof identity")
        if (
            self.target_ground_row_id
            != EXPECTED_GROUND_ROW_IDS[GroundRowName.M]
            or self.necessity_reason
            != "UNIQUE_MISSING_UNRESTRICTED_H1_MAXIMIZER_ON_FAILED_REGRET_CONE"
            or self.old_support_frontier_cannot_authorize is not True
            or self.exact_one_row is not True
        ):
            raise ActionLocalSemanticSwitchInvariantViolation(
                "row-necessity proof changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h2_action_local_row_necessity_proof.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "frontier_id": self.frontier_id,
            "first_model_id": self.first_model_id,
            "query_id": self.query_id,
            "target_ground_row_id": self.target_ground_row_id,
            "necessity_reason": self.necessity_reason,
            "old_support_frontier_cannot_authorize": (
                self.old_support_frontier_cannot_authorize
            ),
            "exact_one_row": self.exact_one_row,
        }

    @property
    def proof_id(self) -> str:
        return _content_id("necessity", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "proof_id": self.proof_id}


@dataclass(frozen=True, slots=True)
class ActionLocalEvidenceRequestV1:
    proof_id: str
    authority_id: str
    first_model_id: str
    query_id: str
    state_id: str
    action_id: str
    ground_row_id: str
    max_ground_transition_calls: int = 1

    def __post_init__(self) -> None:
        for value in (
            self.proof_id,
            self.authority_id,
            self.first_model_id,
            self.query_id,
            self.state_id,
            self.action_id,
            self.ground_row_id,
        ):
            _cid(value, "evidence request identity")
        _integer(
            self.max_ground_transition_calls,
            "request max_ground_transition_calls",
            1,
        )
        if (
            self.state_id != EXPECTED_X1_STATE_ID
            or self.action_id != EXPECTED_GROUND_ACTION_IDS[GroundRowName.M]
            or self.ground_row_id != EXPECTED_GROUND_ROW_IDS[GroundRowName.M]
            or self.max_ground_transition_calls != 1
        ):
            raise ActionLocalSemanticSwitchInvariantViolation(
                "evidence request target/cap changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h2_action_local_evidence_request.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "proof_id": self.proof_id,
            "authority_id": self.authority_id,
            "first_model_id": self.first_model_id,
            "query_id": self.query_id,
            "state_id": self.state_id,
            "action_id": self.action_id,
            "ground_row_id": self.ground_row_id,
            "max_ground_transition_calls": self.max_ground_transition_calls,
        }

    @property
    def request_id(self) -> str:
        return _content_id("request", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "request_id": self.request_id}


@dataclass(frozen=True, slots=True)
class ActionLocalTransitionReceiptV1:
    request_id: str
    authority_id: str
    call_sequence: int
    state_id: str
    action_id: str
    ground_row_id: str
    successor_state: CanonicalStateObservationV1
    probability: Fraction
    reward: Fraction
    failure: bool
    terminal: bool
    _runtime_owner: Any = field(repr=False, compare=False)

    def __post_init__(self) -> None:
        for value in (
            self.request_id,
            self.authority_id,
            self.state_id,
            self.action_id,
            self.ground_row_id,
        ):
            _cid(value, "transition receipt identity")
        _integer(self.call_sequence, "receipt call_sequence", 1)
        if type(self.successor_state) is not CanonicalStateObservationV1:
            raise ActionLocalSemanticSwitchInvariantViolation(
                "receipt rejects copied successor"
            )
        if type(self._runtime_owner) is not _ActionLocalRuntimeOwnerV1:
            raise ActionLocalSemanticSwitchInvariantViolation(
                "transition receipt lacks its live runtime owner"
            )
        object.__setattr__(
            self, "probability", _fraction(self.probability, "receipt probability")
        )
        object.__setattr__(self, "reward", _fraction(self.reward, "receipt reward"))
        if (
            self.call_sequence != 1
            or self.state_id != EXPECTED_X1_STATE_ID
            or self.action_id != EXPECTED_GROUND_ACTION_IDS[GroundRowName.M]
            or self.ground_row_id != EXPECTED_GROUND_ROW_IDS[GroundRowName.M]
            or self.probability != 1
            or self.reward != 1
            or self.failure is not False
            or self.terminal is not False
            or self.successor_state
            != _state_observation(LMBState(49, (0, 0), LMBStatus.ACTIVE))
        ):
            raise ActionLocalSemanticSwitchInvariantViolation(
                "registered exact M transition changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h2_action_local_transition_receipt.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "request_id": self.request_id,
            "authority_id": self.authority_id,
            "call_sequence": self.call_sequence,
            "state_id": self.state_id,
            "action_id": self.action_id,
            "ground_row_id": self.ground_row_id,
            "successor_state": self.successor_state.to_document(),
            "probability": _fdoc(self.probability),
            "reward": _fdoc(self.reward),
            "failure": self.failure,
            "terminal": self.terminal,
        }

    @property
    def receipt_id(self) -> str:
        self._assert_owner_bound()
        return _content_id("receipt", self._payload())

    def to_document(self) -> dict[str, Any]:
        self._assert_owner_bound()
        return {**self._payload(), "receipt_id": self.receipt_id}

    def _assert_owner_bound(self) -> None:
        self._runtime_owner.assert_receipt(self)

    def __copy__(self) -> ActionLocalTransitionReceiptV1:
        raise ActionLocalSemanticSwitchInvariantViolation(
            "transition receipts are live owner-bound artifacts"
        )

    def __deepcopy__(self, _memo: Any) -> ActionLocalTransitionReceiptV1:
        raise ActionLocalSemanticSwitchInvariantViolation(
            "transition receipts are live owner-bound artifacts"
        )

    def __reduce__(self) -> Any:
        raise ActionLocalSemanticSwitchInvariantViolation(
            "transition receipts cannot be serialized as live authority"
        )


@dataclass(frozen=True, slots=True)
class ActionLocalEvidenceBundleV1:
    request_id: str
    receipt: ActionLocalTransitionReceiptV1
    row_evidence: ActionLocalGroundRowEvidenceV1
    exact_row_count: int = 1

    def __post_init__(self) -> None:
        _cid(self.request_id, "bundle request")
        _integer(self.exact_row_count, "bundle row count", 1)
        if type(self.receipt) is ActionLocalTransitionReceiptV1:
            self.receipt._assert_owner_bound()
        if (
            type(self.receipt) is not ActionLocalTransitionReceiptV1
            or type(self.row_evidence) is not ActionLocalGroundRowEvidenceV1
            or self.request_id != self.receipt.request_id
            or self.row_evidence.name is not GroundRowName.M
            or self.row_evidence.ground_row_id != self.receipt.ground_row_id
            or self.row_evidence.action_id != self.receipt.action_id
            or self.row_evidence.successor_state != self.receipt.successor_state
            or self.row_evidence.reward != self.receipt.reward
            or self.exact_row_count != 1
        ):
            raise ActionLocalSemanticSwitchInvariantViolation(
                "one-row exact evidence bundle changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h2_action_local_evidence_bundle.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "request_id": self.request_id,
            "receipt": self.receipt.to_document(),
            "row_evidence": self.row_evidence.to_document(),
            "exact_row_count": self.exact_row_count,
        }

    @property
    def bundle_id(self) -> str:
        return _content_id("bundle", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "bundle_id": self.bundle_id}


class _ActionLocalKernelStepGateV1:
    """Process-local guard: no LMB step is possible before request activation."""

    __slots__ = (
        "_original_step",
        "_guarded_step_function",
        "_installed",
        "_owns_global_lock",
        "_active_request_id",
        "_active_state_id",
        "_active_action_id",
        "_active_ground_row_id",
        "_ground_transition_calls",
    )

    def __init__(self) -> None:
        self._original_step: Any = None
        self._guarded_step_function: Any = None
        self._installed = False
        self._owns_global_lock = False
        self._active_request_id: str | None = None
        self._active_state_id: str | None = None
        self._active_action_id: str | None = None
        self._active_ground_row_id: str | None = None
        self._ground_transition_calls = 0

    def install(self) -> None:
        if self._installed:
            raise ActionLocalSemanticSwitchInvariantViolation(
                "kernel step gate is already installed"
            )
        if not _KERNEL_GATE_LOCK.acquire(blocking=False):
            raise ActionLocalSemanticSwitchInvariantViolation(
                "registered kernel step gate forbids concurrent/reentrant execution"
            )
        self._owns_global_lock = True
        try:
            _assert_canonical_step_callable()
            _assert_canonical_gate_execute_callable()
            if LMBKernel.step is not _CANONICAL_LMB_STEP:
                raise ActionLocalSemanticSwitchInvariantViolation(
                    "LMB step was replaced before the registered gate installed"
                )
            self._original_step = _CANONICAL_LMB_STEP
            canonical_step = _CANONICAL_LMB_STEP
        except BaseException:
            self._owns_global_lock = False
            _KERNEL_GATE_LOCK.release()
            raise

        def guarded_step(
            kernel: LMBKernel,
            state: LMBState,
            action: LMBAction,
        ) -> Any:
            if (
                self._active_request_id is None
                or self._ground_transition_calls != 0
                or state != LMBState(48, (0, 2), LMBStatus.ACTIVE)
                or action != LMBAction(0)
                or self._active_state_id != EXPECTED_X1_STATE_ID
                or self._active_action_id
                != EXPECTED_GROUND_ACTION_IDS[GroundRowName.M]
                or self._active_ground_row_id
                != EXPECTED_GROUND_ROW_IDS[GroundRowName.M]
            ):
                raise ActionLocalSemanticSwitchInvariantViolation(
                    "ground transition occurred outside the frozen one-row request"
                )
            self._ground_transition_calls += 1
            return canonical_step(kernel, state, action)

        try:
            self._guarded_step_function = guarded_step
            LMBKernel.step = guarded_step  # type: ignore[method-assign]
            self._installed = True
        except BaseException:
            self._owns_global_lock = False
            _KERNEL_GATE_LOCK.release()
            raise

    def close(self) -> None:
        substitution_detected = False
        if self._installed:
            substitution_detected = (
                LMBKernel.step is not self._guarded_step_function
            )
            LMBKernel.step = self._original_step  # type: ignore[method-assign]
            self._installed = False
            self._active_request_id = None
        if self._owns_global_lock:
            self._owns_global_lock = False
            _KERNEL_GATE_LOCK.release()
        if substitution_detected:
            raise ActionLocalSemanticSwitchInvariantViolation(
                "LMB step changed while the registered gate owned it"
            )

    def activate(self, request: ActionLocalEvidenceRequestV1) -> None:
        if (
            not self._installed
            or self._active_request_id is not None
            or self._ground_transition_calls != 0
            or LMBKernel.step is not self._guarded_step_function
            or type(request) is not ActionLocalEvidenceRequestV1
        ):
            raise ActionLocalSemanticSwitchInvariantViolation(
                "kernel step gate cannot activate this request"
            )
        self._active_request_id = request.request_id
        self._active_state_id = request.state_id
        self._active_action_id = request.action_id
        self._active_ground_row_id = request.ground_row_id

    def deactivate(self, request: ActionLocalEvidenceRequestV1) -> None:
        if (
            self._active_request_id != request.request_id
            or self._ground_transition_calls != 1
            or LMBKernel.step is not self._guarded_step_function
        ):
            raise ActionLocalSemanticSwitchInvariantViolation(
                "authorized request did not perform exactly one ground transition"
            )
        self._active_request_id = None
        self._active_state_id = None
        self._active_action_id = None
        self._active_ground_row_id = None

    @property
    def ground_transition_calls(self) -> int:
        return self._ground_transition_calls

    def execute(
        self,
        request: ActionLocalEvidenceRequestV1,
        kernel: LMBKernel,
        state: LMBState,
        action: LMBAction,
    ) -> Any:
        if (
            type(self) is not _ActionLocalKernelStepGateV1
            or self._original_step is not _CANONICAL_LMB_STEP
            or self._active_request_id != request.request_id
            or LMBKernel.step is not self._guarded_step_function
            or self._guarded_step_function is None
            or self._ground_transition_calls != 0
        ):
            raise ActionLocalSemanticSwitchInvariantViolation(
                "authorized transition lost the installed canonical guard"
            )
        guarded_step = self._guarded_step_function
        result = guarded_step(kernel, state, action)
        if (
            LMBKernel.step is not guarded_step
            or self._guarded_step_function is not guarded_step
            or self._original_step is not _CANONICAL_LMB_STEP
            or self._ground_transition_calls != 1
        ):
            raise ActionLocalSemanticSwitchInvariantViolation(
                "LMB step changed during the authorized transition"
            )
        return result


_CANONICAL_ACTION_LOCAL_GATE_EXECUTE = _ActionLocalKernelStepGateV1.execute


def _assert_canonical_gate_execute_callable() -> None:
    try:
        execute_source = inspect.getsource(
            _CANONICAL_ACTION_LOCAL_GATE_EXECUTE
        ).encode("utf-8")
        execute_file = Path(
            inspect.getsourcefile(_CANONICAL_ACTION_LOCAL_GATE_EXECUTE) or ""
        ).resolve()
        module_file = Path(__file__).resolve()
    except (OSError, TypeError) as error:
        raise ActionLocalSemanticSwitchInvariantViolation(
            "canonical action-local gate execution entry cannot be inspected"
        ) from error
    if (
        _ActionLocalKernelStepGateV1.execute
        is not _CANONICAL_ACTION_LOCAL_GATE_EXECUTE
        or getattr(_CANONICAL_ACTION_LOCAL_GATE_EXECUTE, "__module__", None)
        != __name__
        or getattr(_CANONICAL_ACTION_LOCAL_GATE_EXECUTE, "__qualname__", None)
        != "_ActionLocalKernelStepGateV1.execute"
        or execute_file != module_file
        or hashlib.sha256(execute_source).hexdigest()
        != EXPECTED_GATE_EXECUTE_SOURCE_SHA256
    ):
        raise ActionLocalSemanticSwitchInvariantViolation(
            "canonical action-local gate execution entry changed"
        )


class _ActionLocalRuntimeOwnerV1:
    """Live owner for the gate, authority, receipt, protocol trace, and result."""

    __slots__ = (
        "gate",
        "_authority",
        "_receipt",
        "_result",
        "_events",
        "_calls_at_request_freeze",
        "_requested_ground_row_id",
        "_acquired_ground_row_id",
    )

    def __init__(self) -> None:
        self.gate = _ActionLocalKernelStepGateV1()
        self._authority: ActionLocalGroundTransitionAuthorityV1 | None = None
        self._receipt: ActionLocalTransitionReceiptV1 | None = None
        self._result: ActionLocalSemanticSwitchResultV1 | None = None
        self._events: list[str] = []
        self._calls_at_request_freeze: int | None = None
        self._requested_ground_row_id: str | None = None
        self._acquired_ground_row_id: str | None = None

    def install(self) -> None:
        self.gate.install()

    def close(self) -> None:
        self.gate.close()

    def record(self, event: str) -> None:
        index = len(self._events)
        if (
            type(event) is not str
            or index >= len(EXPECTED_PROTOCOL_EVENTS)
            or event != EXPECTED_PROTOCOL_EVENTS[index]
        ):
            raise ActionLocalSemanticSwitchInvariantViolation(
                "protocol event is missing, duplicated, or out of order"
            )
        if event == "ONE_ROW_REQUEST_FROZEN":
            self._calls_at_request_freeze = self.gate.ground_transition_calls
        if event == "EXACT_GROUND_TRANSITION_EXECUTED":
            if self.gate.ground_transition_calls != 1:
                raise ActionLocalSemanticSwitchInvariantViolation(
                    "transition event lacks the monitored kernel call"
                )
        self._events.append(event)

    def record_request(self, request: ActionLocalEvidenceRequestV1) -> None:
        if type(request) is not ActionLocalEvidenceRequestV1:
            raise ActionLocalSemanticSwitchInvariantViolation(
                "protocol recorder rejects copied requests"
            )
        self._requested_ground_row_id = request.ground_row_id

    def record_receipt(self, receipt: ActionLocalTransitionReceiptV1) -> None:
        self.assert_receipt(receipt)
        self._acquired_ground_row_id = receipt.ground_row_id

    def mint_authority(
        self,
        fixture_id: str,
        query_id: str,
        necessity_proof_id: str,
        first_model_id: str,
        target_state_id: str,
        target_action_id: str,
        target_ground_row_id: str,
    ) -> ActionLocalGroundTransitionAuthorityV1:
        if self._authority is not None:
            raise ActionLocalSemanticSwitchInvariantViolation(
                "runtime owner already minted its transition authority"
            )
        authority = ActionLocalGroundTransitionAuthorityV1(
            fixture_id,
            query_id,
            necessity_proof_id,
            first_model_id,
            target_state_id,
            target_action_id,
            target_ground_row_id,
            _owner=self,
        )
        self._authority = authority
        return authority

    def assert_authority(
        self, authority: ActionLocalGroundTransitionAuthorityV1
    ) -> None:
        if self._authority is not authority:
            raise ActionLocalSemanticSwitchInvariantViolation(
                "transition authority is copied, foreign, or stale"
            )

    def mint_receipt(self, *args: Any) -> ActionLocalTransitionReceiptV1:
        if self._receipt is not None:
            raise ActionLocalSemanticSwitchInvariantViolation(
                "runtime owner already minted its transition receipt"
            )
        receipt = ActionLocalTransitionReceiptV1(*args, self)
        self._receipt = receipt
        return receipt

    def assert_receipt(self, receipt: ActionLocalTransitionReceiptV1) -> None:
        if self._receipt is not receipt:
            raise ActionLocalSemanticSwitchInvariantViolation(
                "transition receipt is copied, forged, or foreign"
            )

    def bind_result(self, result: ActionLocalSemanticSwitchResultV1) -> None:
        if self._result is not None:
            raise ActionLocalSemanticSwitchInvariantViolation(
                "runtime owner already bound a result"
            )
        self._result = result

    def assert_result(self, result: ActionLocalSemanticSwitchResultV1) -> None:
        if self._result is not result:
            raise ActionLocalSemanticSwitchInvariantViolation(
                "semantic-switch result is copied, forged, or foreign"
            )

    def freeze_trace(self) -> ActionLocalAccessTraceV1:
        if (
            tuple(self._events) != EXPECTED_PROTOCOL_EVENTS
            or self._calls_at_request_freeze is None
            or self._requested_ground_row_id is None
            or self._acquired_ground_row_id is None
        ):
            raise ActionLocalSemanticSwitchInvariantViolation(
                "protocol recorder is incomplete"
            )
        return ActionLocalAccessTraceV1(
            tuple(self._events),
            self._calls_at_request_freeze,
            self.gate.ground_transition_calls - self._calls_at_request_freeze,
            self.gate.ground_transition_calls,
            (self._requested_ground_row_id,),
            (self._acquired_ground_row_id,),
        )


class ActionLocalGroundTransitionAuthorityV1:
    """Single-use exact authority for the frozen ``(x1, M)`` request."""

    __slots__ = (
        "fixture_id",
        "query_id",
        "necessity_proof_id",
        "first_model_id",
        "target_state_id",
        "target_action_id",
        "target_ground_row_id",
        "_owner",
        "_consumed",
    )

    def __init__(
        self,
        fixture_id: str,
        query_id: str,
        necessity_proof_id: str,
        first_model_id: str,
        target_state_id: str,
        target_action_id: str,
        target_ground_row_id: str,
        *,
        _owner: _ActionLocalRuntimeOwnerV1,
    ) -> None:
        if type(_owner) is not _ActionLocalRuntimeOwnerV1:
            raise ActionLocalSemanticSwitchInvariantViolation(
                "transition authority cannot be externally minted"
            )
        for value in (
            fixture_id,
            query_id,
            necessity_proof_id,
            first_model_id,
            target_state_id,
            target_action_id,
            target_ground_row_id,
        ):
            _cid(value, "transition authority identity")
        if (
            target_state_id != EXPECTED_X1_STATE_ID
            or target_action_id != EXPECTED_GROUND_ACTION_IDS[GroundRowName.M]
            or target_ground_row_id != EXPECTED_GROUND_ROW_IDS[GroundRowName.M]
        ):
            raise ActionLocalSemanticSwitchInvariantViolation(
                "transition authority target changed"
            )
        self.fixture_id = fixture_id
        self.query_id = query_id
        self.necessity_proof_id = necessity_proof_id
        self.first_model_id = first_model_id
        self.target_state_id = target_state_id
        self.target_action_id = target_action_id
        self.target_ground_row_id = target_ground_row_id
        self._owner = _owner
        self._consumed = False

    @property
    def authority_id(self) -> str:
        self._owner.assert_authority(self)
        return _content_id(
            "authority",
            {
                "schema": "acfqp.h2_action_local_transition_authority.v1",
                "schema_version": SCHEMA_VERSION,
                "profile_key": PROFILE_KEY,
                "fixture_id": self.fixture_id,
                "query_id": self.query_id,
                "necessity_proof_id": self.necessity_proof_id,
                "first_model_id": self.first_model_id,
                "target_state_id": self.target_state_id,
                "target_action_id": self.target_action_id,
                "target_ground_row_id": self.target_ground_row_id,
                "single_use": True,
            },
        )

    def acquire(
        self,
        request: ActionLocalEvidenceRequestV1,
        kernel: LMBKernel,
    ) -> ActionLocalTransitionReceiptV1:
        self._owner.assert_authority(self)
        if (
            type(request) is not ActionLocalEvidenceRequestV1
            or type(kernel) is not LMBKernel
        ):
            raise ActionLocalSemanticSwitchInvariantViolation(
                "authority rejects copied request/kernel"
            )
        _assert_literal_kernel(kernel)
        if self._consumed:
            raise ActionLocalSemanticSwitchInvariantViolation(
                "single-use transition authority was already consumed"
            )
        if (
            request.authority_id != self.authority_id
            or request.query_id != self.query_id
            or request.proof_id != self.necessity_proof_id
            or request.first_model_id != self.first_model_id
            or request.state_id != self.target_state_id
            or request.action_id != self.target_action_id
            or request.ground_row_id != self.target_ground_row_id
            or request.max_ground_transition_calls != 1
        ):
            raise ActionLocalSemanticSwitchInvariantViolation(
                "request lies outside the frozen transition authority"
            )
        self._consumed = True
        state = LMBState(48, (0, 2), LMBStatus.ACTIVE)
        gate = self._owner.gate
        if type(gate) is not _ActionLocalKernelStepGateV1:
            raise ActionLocalSemanticSwitchInvariantViolation(
                "transition authority lost its canonical kernel gate"
            )
        _assert_canonical_gate_execute_callable()
        gate.activate(request)
        try:
            outcomes = _CANONICAL_ACTION_LOCAL_GATE_EXECUTE(
                gate,
                request,
                kernel,
                state,
                LMBAction(0),
            )
        finally:
            gate.deactivate(request)
        if len(outcomes) != 1:
            raise ActionLocalSemanticSwitchInvariantViolation(
                "registered transition is not deterministic"
            )
        outcome = outcomes[0]
        reward = sum(
            value
            for name, value in outcome.reward_features
            if name == "match"
        )
        return self._owner.mint_receipt(
            request.request_id,
            self.authority_id,
            1,
            request.state_id,
            request.action_id,
            request.ground_row_id,
            _state_observation(outcome.next_state),
            outcome.probability,
            reward,
            outcome.failure,
            outcome.terminal,
        )

    def __copy__(self) -> ActionLocalGroundTransitionAuthorityV1:
        raise ActionLocalSemanticSwitchInvariantViolation(
            "transition authority is a non-copyable live capability"
        )

    def __deepcopy__(self, _memo: Any) -> ActionLocalGroundTransitionAuthorityV1:
        raise ActionLocalSemanticSwitchInvariantViolation(
            "transition authority is a non-copyable live capability"
        )

    def __reduce__(self) -> Any:
        raise ActionLocalSemanticSwitchInvariantViolation(
            "transition authority cannot be serialized"
        )


@dataclass(frozen=True, slots=True)
class ActionLocalOverlayBuildV1:
    first_model_id: str
    final_model_id: str
    evidence_bundle_id: str
    added_ground_row_ids: tuple[str, ...]
    removed_ground_row_ids: tuple[str, ...]
    changed_ground_row_ids: tuple[str, ...]
    action_indexed_delta: ActionIndexedModelDeltaV1
    immutable_append_only: bool = True

    def __post_init__(self) -> None:
        for value in (
            self.first_model_id,
            self.final_model_id,
            self.evidence_bundle_id,
            *self.added_ground_row_ids,
            *self.removed_ground_row_ids,
            *self.changed_ground_row_ids,
        ):
            _cid(value, "overlay build identity")
        if (
            type(self.action_indexed_delta) is not ActionIndexedModelDeltaV1
            or self.added_ground_row_ids
            != (EXPECTED_GROUND_ROW_IDS[GroundRowName.M],)
            or self.removed_ground_row_ids
            or self.changed_ground_row_ids
            or self.action_indexed_delta.changed_row_names
            != (GroundRowName.M,)
            or self.immutable_append_only is not True
        ):
            raise ActionLocalSemanticSwitchInvariantViolation(
                "registered one-row immutable overlay changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h2_action_local_overlay_build.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "first_model_id": self.first_model_id,
            "final_model_id": self.final_model_id,
            "evidence_bundle_id": self.evidence_bundle_id,
            "added_ground_row_ids": list(self.added_ground_row_ids),
            "removed_ground_row_ids": list(self.removed_ground_row_ids),
            "changed_ground_row_ids": list(self.changed_ground_row_ids),
            "action_indexed_delta": self.action_indexed_delta.to_document(),
            "immutable_append_only": self.immutable_append_only,
        }

    @property
    def build_id(self) -> str:
        return _content_id("overlay", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "build_id": self.build_id}


@dataclass(frozen=True, slots=True)
class StrictPolicySwitchWitnessV1:
    first_execution_id: str
    final_execution_id: str
    first_action: CandidateAction
    final_action: CandidateAction
    first_schedule_code: str
    final_schedule_code: str
    first_reachable_value: Fraction
    final_reachable_value: Fraction
    value_improvement: Fraction
    first_normalized_regret: Fraction
    final_normalized_regret: Fraction
    first_certified: bool
    final_certified: bool
    tie_break_only: bool = False

    def __post_init__(self) -> None:
        for value in (self.first_execution_id, self.final_execution_id):
            _cid(value, "policy switch execution")
        if (
            type(self.first_action) is not CandidateAction
            or type(self.final_action) is not CandidateAction
        ):
            raise ActionLocalSemanticSwitchInvariantViolation(
                "policy switch action type changed"
            )
        for field in (
            "first_reachable_value",
            "final_reachable_value",
            "value_improvement",
            "first_normalized_regret",
            "final_normalized_regret",
        ):
            object.__setattr__(self, field, _fraction(getattr(self, field), field))
        if (
            self.first_action is not CandidateAction.N
            or self.final_action is not CandidateAction.M
            or self.first_schedule_code != "A0A0"
            or self.final_schedule_code != "A0A1"
            or self.first_reachable_value != 0
            or self.final_reachable_value != 1
            or self.value_improvement != 1
            or self.first_normalized_regret != Fraction(3, 4)
            or self.final_normalized_regret != 0
            or self.first_certified is not False
            or self.final_certified is not True
            or self.tie_break_only is not False
        ):
            raise ActionLocalSemanticSwitchInvariantViolation(
                "strict policy switch witness changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h2_action_local_policy_switch_witness.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "first_execution_id": self.first_execution_id,
            "final_execution_id": self.final_execution_id,
            "first_action": self.first_action.value,
            "final_action": self.final_action.value,
            "first_schedule_code": self.first_schedule_code,
            "final_schedule_code": self.final_schedule_code,
            "first_reachable_value": _fdoc(self.first_reachable_value),
            "final_reachable_value": _fdoc(self.final_reachable_value),
            "value_improvement": _fdoc(self.value_improvement),
            "first_normalized_regret": _fdoc(self.first_normalized_regret),
            "final_normalized_regret": _fdoc(self.final_normalized_regret),
            "first_certified": self.first_certified,
            "final_certified": self.final_certified,
            "tie_break_only": self.tie_break_only,
        }

    @property
    def witness_id(self) -> str:
        return _content_id("switch", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "witness_id": self.witness_id}


EXPECTED_PROTOCOL_EVENTS = (
    "REGISTERED_FIXTURE_FROZEN_WITHOUT_TRANSITION",
    "FIRST_4_1_MODEL_FROZEN",
    "FIRST_MODEL_ONLY_H2_AUDIT_FAILED",
    "SELECTED_SUPPORT_FRONTIER_FROZEN_NONAUTHORIZING",
    "UNRESTRICTED_CHALLENGER_FRONTIER_FROZEN_NONAUTHORIZING",
    "ONE_ROW_NECESSITY_PROOF_FROZEN",
    "ONE_ROW_REQUEST_FROZEN",
    "EXACT_GROUND_TRANSITION_EXECUTED",
    "ONE_ROW_EVIDENCE_BUNDLE_FROZEN",
    "FINAL_5_0_MODEL_EPOCH_FROZEN",
    "ACTION_INDEXED_INVALIDATION_DERIVED",
    "FINAL_MODEL_ONLY_H2_AUDIT_CERTIFIED",
)


@dataclass(frozen=True, slots=True)
class ActionLocalAccessTraceV1:
    events: tuple[str, ...]
    ground_calls_before_request_freeze: int
    ground_calls_after_request_freeze: int
    total_ground_transition_calls: int
    requested_ground_row_ids: tuple[str, ...]
    acquired_ground_row_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        for field in (
            "ground_calls_before_request_freeze",
            "ground_calls_after_request_freeze",
            "total_ground_transition_calls",
        ):
            _integer(getattr(self, field), field)
        for value in (*self.requested_ground_row_ids, *self.acquired_ground_row_ids):
            _cid(value, "access trace ground row")
        if (
            self.events != EXPECTED_PROTOCOL_EVENTS
            or self.ground_calls_before_request_freeze != 0
            or self.ground_calls_after_request_freeze != 1
            or self.total_ground_transition_calls != 1
            or self.requested_ground_row_ids
            != (EXPECTED_GROUND_ROW_IDS[GroundRowName.M],)
            or self.acquired_ground_row_ids != self.requested_ground_row_ids
        ):
            raise ActionLocalSemanticSwitchInvariantViolation(
                "access-order/ground-call trace changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h2_action_local_access_trace.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "events": list(self.events),
            "ground_calls_before_request_freeze": (
                self.ground_calls_before_request_freeze
            ),
            "ground_calls_after_request_freeze": (
                self.ground_calls_after_request_freeze
            ),
            "total_ground_transition_calls": self.total_ground_transition_calls,
            "requested_ground_row_ids": list(self.requested_ground_row_ids),
            "acquired_ground_row_ids": list(self.acquired_ground_row_ids),
        }

    @property
    def trace_id(self) -> str:
        return _content_id("trace", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "trace_id": self.trace_id}


@dataclass(frozen=True, slots=True)
class ActionLocalClaimLocksV1:
    registered_h2_action_local_switch_claimed: bool = True
    unrestricted_challenger_frontier_claimed: bool = True
    exact_one_row_overlay_claimed: bool = True
    action_indexed_invalidation_claimed: bool = True
    strict_policy_switch_claimed: bool = True
    generic_action_local_minimality_claimed: bool = False
    generic_h_gt_1_completeness_claimed: bool = False
    durable_persistence_claimed: bool = False
    cross_query_reuse_claimed: bool = False
    automatic_coordinate_invention_claimed: bool = False
    partial_dynamics_claimed: bool = False
    learned_dynamics_claimed: bool = False
    sample_efficiency_claimed: bool = False
    byte_savings_claimed: bool = False
    cpu_savings_claimed: bool = False
    wall_clock_savings_claimed: bool = False
    total_work_savings_claimed: bool = False
    official_execution_allowed: bool = False
    official_scalar_cost: None = None
    official_N_break_even: None = None
    workload_economics_gate: str = "WORKLOAD_ECONOMICS_GATE_NOT_RUN"
    counter_completeness_gate: str = "COUNTER_COMPLETENESS_GATE_NOT_RUN"

    def __post_init__(self) -> None:
        if (
            self.registered_h2_action_local_switch_claimed is not True
            or self.unrestricted_challenger_frontier_claimed is not True
            or self.exact_one_row_overlay_claimed is not True
            or self.action_indexed_invalidation_claimed is not True
            or self.strict_policy_switch_claimed is not True
            or any(
                value is not False
                for value in (
                    self.generic_action_local_minimality_claimed,
                    self.generic_h_gt_1_completeness_claimed,
                    self.durable_persistence_claimed,
                    self.cross_query_reuse_claimed,
                    self.automatic_coordinate_invention_claimed,
                    self.partial_dynamics_claimed,
                    self.learned_dynamics_claimed,
                    self.sample_efficiency_claimed,
                    self.byte_savings_claimed,
                    self.cpu_savings_claimed,
                    self.wall_clock_savings_claimed,
                    self.total_work_savings_claimed,
                    self.official_execution_allowed,
                )
            )
            or self.official_scalar_cost is not None
            or self.official_N_break_even is not None
            or self.workload_economics_gate != "WORKLOAD_ECONOMICS_GATE_NOT_RUN"
            or self.counter_completeness_gate
            != "COUNTER_COMPLETENESS_GATE_NOT_RUN"
        ):
            raise ActionLocalSemanticSwitchInvariantViolation(
                "V0-054B claim locks changed"
            )

    def to_document(self) -> dict[str, Any]:
        return {
            field: getattr(self, field)
            for field in self.__dataclass_fields__
        }


@dataclass(frozen=True, slots=True)
class ActionLocalSemanticSwitchResultV1:
    fixture: RegisteredActionLocalFixtureV1
    query: ActionIndexedH2QueryV1
    first_model: ActionLocalModelEpochV1
    first_execution: ActionIndexedEpochExecutionV1
    support_frontier: SelectedPolicySupportFrontierV1
    challenger_frontier: UnrestrictedChallengerFrontierV1
    necessity_proof: ActionLocalRowNecessityProofV1
    request: ActionLocalEvidenceRequestV1
    evidence_bundle: ActionLocalEvidenceBundleV1
    final_model: ActionLocalModelEpochV1
    overlay_build: ActionLocalOverlayBuildV1
    preexecution_invalidation: ActionIndexedPreExecutionInvalidationV1
    invalidation: ActionIndexedInvalidationManifestV1
    final_execution: ActionIndexedEpochExecutionV1
    policy_switch: StrictPolicySwitchWitnessV1
    access_trace: ActionLocalAccessTraceV1
    claim_locks: ActionLocalClaimLocksV1
    status: str = SUCCESS_STATUS
    _runtime_owner: Any = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        if type(self._runtime_owner) is not _ActionLocalRuntimeOwnerV1:
            raise ActionLocalSemanticSwitchInvariantViolation(
                "semantic-switch result lacks its live runtime owner"
            )
        exact_types = (
            (self.fixture, RegisteredActionLocalFixtureV1),
            (self.query, ActionIndexedH2QueryV1),
            (self.first_model, ActionLocalModelEpochV1),
            (self.first_execution, ActionIndexedEpochExecutionV1),
            (self.support_frontier, SelectedPolicySupportFrontierV1),
            (self.challenger_frontier, UnrestrictedChallengerFrontierV1),
            (self.necessity_proof, ActionLocalRowNecessityProofV1),
            (self.request, ActionLocalEvidenceRequestV1),
            (self.evidence_bundle, ActionLocalEvidenceBundleV1),
            (self.final_model, ActionLocalModelEpochV1),
            (self.overlay_build, ActionLocalOverlayBuildV1),
            (
                self.preexecution_invalidation,
                ActionIndexedPreExecutionInvalidationV1,
            ),
            (self.invalidation, ActionIndexedInvalidationManifestV1),
            (self.final_execution, ActionIndexedEpochExecutionV1),
            (self.policy_switch, StrictPolicySwitchWitnessV1),
            (self.access_trace, ActionLocalAccessTraceV1),
            (self.claim_locks, ActionLocalClaimLocksV1),
        )
        if any(type(value) is not expected for value, expected in exact_types):
            raise ActionLocalSemanticSwitchInvariantViolation(
                "result rejects copied nested artifacts"
            )
        if self.status != SUCCESS_STATUS:
            raise ActionLocalSemanticSwitchInvariantViolation(
                "registered result status changed"
            )
        first_audit = self.first_execution.candidate_audits[0]
        final_audit = self.final_execution.candidate_audits[1]
        if (
            self.first_model.fixture_id != self.fixture.fixture_id
            or self.final_model.fixture_id != self.fixture.fixture_id
            or self.first_model.query_id != self.query.query_id
            or self.final_model.query_id != self.query.query_id
            or self.first_model.dag_model.model_id != self.first_execution.model_id
            or self.final_model.dag_model.model_id != self.final_execution.model_id
            or self.final_model.parent_model_id != self.first_model.model_id
            or self.support_frontier.model_id != self.first_model.model_id
            or self.support_frontier.execution_id
            != self.first_execution.execution_id
            or self.challenger_frontier.model_id != self.first_model.model_id
            or self.challenger_frontier.failed_execution_id
            != self.first_execution.execution_id
            or self.challenger_frontier.selected_audit_id != first_audit.audit_id
            or self.necessity_proof.frontier_id
            != self.challenger_frontier.frontier_id
            or self.necessity_proof.first_model_id != self.first_model.model_id
            or self.request.proof_id != self.necessity_proof.proof_id
            or self.request.first_model_id != self.first_model.model_id
            or self.evidence_bundle.request_id != self.request.request_id
            or self.overlay_build.first_model_id != self.first_model.model_id
            or self.overlay_build.final_model_id != self.final_model.model_id
            or self.overlay_build.evidence_bundle_id
            != self.evidence_bundle.bundle_id
            or self.overlay_build.action_indexed_delta.delta_id
            != self.invalidation.delta_id
            or self.preexecution_invalidation.delta_id
            != self.overlay_build.action_indexed_delta.delta_id
            or self.preexecution_invalidation.first_execution_id
            != self.first_execution.execution_id
            or self.final_execution.preexecution_invalidation_id
            != self.preexecution_invalidation.plan_id
            or self.invalidation.preexecution_invalidation_id
            != self.preexecution_invalidation.plan_id
            or self.invalidation.first_execution_id
            != self.first_execution.execution_id
            or self.invalidation.final_execution_id
            != self.final_execution.execution_id
            or self.policy_switch.first_execution_id
            != self.first_execution.execution_id
            or self.policy_switch.final_execution_id
            != self.final_execution.execution_id
            or first_audit.certified is not False
            or final_audit.certified is not True
            or self.first_execution.proposal.selected_action is not CandidateAction.N
            or self.final_execution.proposal.selected_action is not CandidateAction.M
        ):
            raise ActionLocalSemanticSwitchInvariantViolation(
                "result identity/certificate chain changed"
            )
        if tuple(
            item.to_document() for item in self.final_model.observed_rows[:-1]
        ) != tuple(
            item.to_document() for item in self.first_model.observed_rows
        ):
            raise ActionLocalSemanticSwitchInvariantViolation(
                "final epoch mutated an existing base row"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h2_action_local_semantic_switch_result.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "status": self.status,
            "fixture": self.fixture.to_document(),
            "query": self.query.to_document(),
            "first_model": self.first_model.to_document(),
            "first_execution": self.first_execution.to_document(),
            "support_frontier": self.support_frontier.to_document(),
            "challenger_frontier": self.challenger_frontier.to_document(),
            "necessity_proof": self.necessity_proof.to_document(),
            "request": self.request.to_document(),
            "evidence_bundle": self.evidence_bundle.to_document(),
            "final_model": self.final_model.to_document(),
            "overlay_build": self.overlay_build.to_document(),
            "preexecution_invalidation": (
                self.preexecution_invalidation.to_document()
            ),
            "invalidation": self.invalidation.to_document(),
            "final_execution": self.final_execution.to_document(),
            "policy_switch": self.policy_switch.to_document(),
            "access_trace": self.access_trace.to_document(),
            "claim_locks": self.claim_locks.to_document(),
        }

    @property
    def result_id(self) -> str:
        self._assert_owner_bound()
        return _content_id("result", self._payload())

    def to_document(self) -> dict[str, Any]:
        self._assert_owner_bound()
        return {**self._payload(), "result_id": self.result_id}

    def _assert_owner_bound(self) -> None:
        self._runtime_owner.assert_result(self)
        self.evidence_bundle.receipt._assert_owner_bound()

    def __copy__(self) -> ActionLocalSemanticSwitchResultV1:
        raise ActionLocalSemanticSwitchInvariantViolation(
            "semantic-switch results are live owner-bound artifacts"
        )

    def __deepcopy__(self, _memo: Any) -> ActionLocalSemanticSwitchResultV1:
        raise ActionLocalSemanticSwitchInvariantViolation(
            "semantic-switch results are live owner-bound artifacts"
        )

    def __reduce__(self) -> Any:
        raise ActionLocalSemanticSwitchInvariantViolation(
            "semantic-switch live authority cannot be serialized"
        )


def _derive_frontiers_v1(
    fixture: RegisteredActionLocalFixtureV1,
    first_model: ActionLocalModelEpochV1,
    first_execution: ActionIndexedEpochExecutionV1,
) -> tuple[SelectedPolicySupportFrontierV1, UnrestrictedChallengerFrontierV1]:
    if (
        type(fixture) is not RegisteredActionLocalFixtureV1
        or type(first_model) is not ActionLocalModelEpochV1
        or type(first_execution) is not ActionIndexedEpochExecutionV1
    ):
        raise ActionLocalSemanticSwitchInvariantViolation(
            "frontier derivation requires exact registered artifacts"
        )
    first_execution.__post_init__()
    n_audit, m_audit = first_execution.candidate_audits
    nodes = {item.address: item for item in first_execution.nodes}
    if (
        first_execution.proposal.selected_action is not CandidateAction.N
        or n_audit.normalized_regret != Fraction(3, 4)
        or n_audit.certified is not False
        or m_audit.coverage_passed is not False
        or nodes[ProofAddress.Q_N].fraction("reward_upper") != 0
        or nodes[ProofAddress.Q_M].fraction("reward_upper") != 3
        or nodes[ProofAddress.U1].fraction("reward_upper") != 3
        or nodes[ProofAddress.U0].fraction("reward_upper") != 3
        or first_model.missing_ground_row_ids
        != (EXPECTED_GROUND_ROW_IDS[GroundRowName.M],)
    ):
        raise ActionLocalSemanticSwitchInvariantViolation(
            "registered failed unrestricted proof changed"
        )
    support = SelectedPolicySupportFrontierV1(
        first_model.model_id,
        first_execution.execution_id,
        CandidateAction.N,
        tuple(
            EXPECTED_GROUND_ROW_IDS[name]
            for name in (
                GroundRowName.S,
                GroundRowName.N1,
                GroundRowName.N2,
                GroundRowName.N3,
            )
        ),
        EXPECTED_GROUND_ROW_IDS[GroundRowName.M],
        False,
    )
    m_action = fixture.action(GroundRowName.M)
    challenger = UnrestrictedChallengerFrontierV1(
        first_model.model_id,
        first_execution.query_id,
        first_execution.execution_id,
        n_audit.audit_id,
        fixture.downstream_catalogue.catalogue_id,
        fixture.downstream_state.state_id,
        m_action.action_id,
        m_action.ground_row_id,
        1,
        EXPECTED_CHALLENGER_CIRCUIT,
        tuple(nodes[address].node_id for address in EXPECTED_CHALLENGER_CIRCUIT),
        True,
        False,
    )
    return support, challenger


def _canonical_result_ids(
    result: ActionLocalSemanticSwitchResultV1,
) -> dict[str, str]:
    if type(result) is not ActionLocalSemanticSwitchResultV1:
        raise ActionLocalSemanticSwitchInvariantViolation(
            "canonical ID audit requires the exact result"
        )
    return {
        "structural": result.fixture.structural_id,
        "fixture": result.fixture.fixture_id,
        "query": result.query.query_id,
        "first_model": result.first_model.model_id,
        "first_dag_model": result.first_model.dag_model.model_id,
        "first_execution": result.first_execution.execution_id,
        "support_frontier": result.support_frontier.frontier_id,
        "challenger_frontier": result.challenger_frontier.frontier_id,
        "necessity": result.necessity_proof.proof_id,
        "request": result.request.request_id,
        "receipt": result.evidence_bundle.receipt.receipt_id,
        "evidence_bundle": result.evidence_bundle.bundle_id,
        "final_model": result.final_model.model_id,
        "final_dag_model": result.final_model.dag_model.model_id,
        "delta": result.overlay_build.action_indexed_delta.delta_id,
        "pre_invalidation": result.preexecution_invalidation.plan_id,
        "final_execution": result.final_execution.execution_id,
        "invalidation": result.invalidation.manifest_id,
        "overlay": result.overlay_build.build_id,
        "switch": result.policy_switch.witness_id,
        "trace": result.access_trace.trace_id,
        "result": result.result_id,
    }


def _assert_canonical_result_ids(
    result: ActionLocalSemanticSwitchResultV1,
) -> None:
    actual = _canonical_result_ids(result)
    expected = {
        key: value
        for key, value in EXPECTED_CANONICAL_IDS.items()
        if key != "verification"
    }
    if actual != expected:
        raise ActionLocalSemanticSwitchInvariantViolation(
            "registered V0-054B canonical identities changed"
        )


def freeze_action_local_evidence_request_v1(
    proof: ActionLocalRowNecessityProofV1,
    authority: ActionLocalGroundTransitionAuthorityV1,
    frontier: UnrestrictedChallengerFrontierV1,
) -> ActionLocalEvidenceRequestV1:
    """Freeze the only request type that can authorize the registered call."""

    if (
        type(proof) is not ActionLocalRowNecessityProofV1
        or type(authority) is not ActionLocalGroundTransitionAuthorityV1
        or type(frontier) is not UnrestrictedChallengerFrontierV1
    ):
        raise ActionLocalSemanticSwitchInvariantViolation(
            "support/copy artifacts cannot authorize a transition request"
        )
    authority._owner.assert_authority(authority)
    if (
        proof.frontier_id != frontier.frontier_id
        or proof.target_ground_row_id != frontier.target_ground_row_id
        or authority.query_id != proof.query_id
        or authority.necessity_proof_id != proof.proof_id
        or authority.first_model_id != proof.first_model_id
        or authority.target_state_id != frontier.target_state_id
        or authority.target_action_id != frontier.target_action_id
        or authority.target_ground_row_id != frontier.target_ground_row_id
    ):
        raise ActionLocalSemanticSwitchInvariantViolation(
            "necessity/frontier/authority request binding changed"
        )
    return ActionLocalEvidenceRequestV1(
        proof.proof_id,
        authority.authority_id,
        proof.first_model_id,
        proof.query_id,
        frontier.target_state_id,
        frontier.target_action_id,
        frontier.target_ground_row_id,
    )


def _execute_registered_h2_action_local_semantic_switch_with_owner_v1(
    owner: _ActionLocalRuntimeOwnerV1,
) -> ActionLocalSemanticSwitchResultV1:
    if type(owner) is not _ActionLocalRuntimeOwnerV1:
        raise ActionLocalSemanticSwitchInvariantViolation(
            "registered execution requires its exact runtime owner"
        )
    fixture = registered_action_local_fixture_v1()
    owner.record("REGISTERED_FIXTURE_FROZEN_WITHOUT_TRANSITION")
    query = registered_action_indexed_h2_query_v1()
    offline_rows = _offline_registered_rows_v1(fixture)
    first_model = ActionLocalModelEpochV1(
        1,
        fixture.fixture_id,
        query.query_id,
        None,
        registered_first_action_indexed_h2_model_v1(),
        offline_rows,
        (fixture.action(GroundRowName.M).ground_row_id,),
    )
    owner.record("FIRST_4_1_MODEL_FROZEN")
    runtime = ActionIndexedProofRuntimeV1()
    first_execution = execute_action_indexed_epoch_v1(
        first_model.dag_model,
        query,
        runtime,
    )
    owner.record("FIRST_MODEL_ONLY_H2_AUDIT_FAILED")
    support_frontier, challenger_frontier = _derive_frontiers_v1(
        fixture,
        first_model,
        first_execution,
    )
    owner.record("SELECTED_SUPPORT_FRONTIER_FROZEN_NONAUTHORIZING")
    owner.record("UNRESTRICTED_CHALLENGER_FRONTIER_FROZEN_NONAUTHORIZING")
    necessity = ActionLocalRowNecessityProofV1(
        challenger_frontier.frontier_id,
        first_model.model_id,
        query.query_id,
        challenger_frontier.target_ground_row_id,
        "UNIQUE_MISSING_UNRESTRICTED_H1_MAXIMIZER_ON_FAILED_REGRET_CONE",
        support_frontier.target_is_supported is False
        and support_frontier.authorizing is False,
        True,
    )
    owner.record("ONE_ROW_NECESSITY_PROOF_FROZEN")
    authority = owner.mint_authority(
        fixture.fixture_id,
        query.query_id,
        necessity.proof_id,
        first_model.model_id,
        challenger_frontier.target_state_id,
        challenger_frontier.target_action_id,
        challenger_frontier.target_ground_row_id,
    )
    request = freeze_action_local_evidence_request_v1(
        necessity,
        authority,
        challenger_frontier,
    )
    owner.record_request(request)
    owner.record("ONE_ROW_REQUEST_FROZEN")
    receipt = authority.acquire(request, _literal_kernel_v1())
    owner.record_receipt(receipt)
    owner.record("EXACT_GROUND_TRANSITION_EXECUTED")
    row = ActionLocalGroundRowEvidenceV1(
        GroundRowName.M,
        receipt.state_id,
        receipt.action_id,
        receipt.ground_row_id,
        receipt.successor_state,
        receipt.reward,
        receipt.failure,
        receipt.terminal,
        EvidenceLane.QUERY_LOCAL_AUTHORIZED,
    )
    bundle = ActionLocalEvidenceBundleV1(request.request_id, receipt, row)
    owner.record("ONE_ROW_EVIDENCE_BUNDLE_FROZEN")
    final_model = ActionLocalModelEpochV1(
        2,
        fixture.fixture_id,
        query.query_id,
        first_model.model_id,
        registered_final_action_indexed_h2_model_v1(),
        (*first_model.observed_rows, row),
        (),
    )
    owner.record("FINAL_5_0_MODEL_EPOCH_FROZEN")
    delta, preexecution_invalidation = (
        derive_action_indexed_preexecution_invalidation_v1(
            first_model.dag_model,
            final_model.dag_model,
            first_execution,
        )
    )
    authorize_action_indexed_final_epoch_v1(
        runtime,
        preexecution_invalidation,
    )
    owner.record("ACTION_INDEXED_INVALIDATION_DERIVED")
    final_execution = execute_action_indexed_epoch_v1(
        final_model.dag_model,
        query,
        runtime,
    )
    owner.record("FINAL_MODEL_ONLY_H2_AUDIT_CERTIFIED")
    verified_delta, invalidation = derive_action_indexed_delta_and_invalidation_v1(
        first_model.dag_model,
        final_model.dag_model,
        first_execution,
        final_execution,
    )
    if verified_delta.to_document() != delta.to_document():
        raise ActionLocalSemanticSwitchInvariantViolation(
            "post-execution delta differs from frozen pre-execution delta"
        )
    overlay = ActionLocalOverlayBuildV1(
        first_model.model_id,
        final_model.model_id,
        bundle.bundle_id,
        (row.ground_row_id,),
        (),
        (),
        delta,
    )
    first_selected = first_execution.candidate_audits[0]
    final_selected = final_execution.candidate_audits[1]
    switch = StrictPolicySwitchWitnessV1(
        first_execution.execution_id,
        final_execution.execution_id,
        first_execution.proposal.selected_action,
        final_execution.proposal.selected_action,
        first_execution.proposal.selected_schedule_code,
        final_execution.proposal.selected_schedule_code,
        first_selected.policy_reward_lower,
        final_selected.policy_reward_lower,
        final_selected.policy_reward_lower - first_selected.policy_reward_lower,
        first_selected.normalized_regret,
        final_selected.normalized_regret,
        first_selected.certified,
        final_selected.certified,
    )
    trace = owner.freeze_trace()
    result = ActionLocalSemanticSwitchResultV1(
        fixture,
        query,
        first_model,
        first_execution,
        support_frontier,
        challenger_frontier,
        necessity,
        request,
        bundle,
        final_model,
        overlay,
        preexecution_invalidation,
        invalidation,
        final_execution,
        switch,
        trace,
        ActionLocalClaimLocksV1(),
        _runtime_owner=owner,
    )
    owner.bind_result(result)
    _assert_canonical_result_ids(result)
    return result


def _execute_registered_h2_action_local_semantic_switch_v1(
) -> ActionLocalSemanticSwitchResultV1:
    owner = _ActionLocalRuntimeOwnerV1()
    owner.install()
    try:
        return _execute_registered_h2_action_local_semantic_switch_with_owner_v1(
            owner
        )
    finally:
        owner.close()


def run_registered_h2_action_local_semantic_switch_v1(
) -> ActionLocalSemanticSwitchResultV1:
    """Run the registered V0-054B construction control."""

    return _execute_registered_h2_action_local_semantic_switch_v1()


@dataclass(frozen=True, slots=True)
class ActionLocalSemanticSwitchVerificationV1:
    claimed_result_id: str
    replayed_result_id: str
    exact_document_match: bool
    independent_algorithm: bool
    evaluation_lane_only: bool
    included_in_operational_work: bool

    def __post_init__(self) -> None:
        _cid(self.claimed_result_id, "verification claimed result")
        _cid(self.replayed_result_id, "verification replayed result")
        if (
            self.claimed_result_id != self.replayed_result_id
            or self.exact_document_match is not True
            or self.independent_algorithm is not False
            or self.evaluation_lane_only is not True
            or self.included_in_operational_work is not False
        ):
            raise ActionLocalSemanticSwitchInvariantViolation(
                "semantic-switch verification result changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h2_action_local_semantic_switch_verification.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "claimed_result_id": self.claimed_result_id,
            "replayed_result_id": self.replayed_result_id,
            "exact_document_match": self.exact_document_match,
            "independent_algorithm": self.independent_algorithm,
            "evaluation_lane_only": self.evaluation_lane_only,
            "included_in_operational_work": self.included_in_operational_work,
        }

    @property
    def report_id(self) -> str:
        return _content_id("verification", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "report_id": self.report_id}


def verify_registered_h2_action_local_semantic_switch_v1(
    claimed: ActionLocalSemanticSwitchResultV1,
) -> ActionLocalSemanticSwitchVerificationV1:
    """Fresh deterministic replay; deliberately not an independent algorithm."""

    if type(claimed) is not ActionLocalSemanticSwitchResultV1:
        raise ActionLocalSemanticSwitchInvariantViolation(
            "verifier rejects copied result types"
        )
    claimed._assert_owner_bound()
    claimed.__post_init__()
    replayed = _execute_registered_h2_action_local_semantic_switch_v1()
    exact = claimed.to_document() == replayed.to_document()
    if not exact:
        raise ActionLocalSemanticSwitchInvariantViolation(
            "claimed result differs from fresh registered replay"
        )
    report = ActionLocalSemanticSwitchVerificationV1(
        claimed.result_id,
        replayed.result_id,
        exact,
        False,
        True,
        False,
    )
    if report.report_id != EXPECTED_CANONICAL_IDS["verification"]:
        raise ActionLocalSemanticSwitchInvariantViolation(
            "registered V0-054B verification identity changed"
        )
    return report


__all__ = [
    "ActionLocalAccessTraceV1",
    "ActionLocalClaimLocksV1",
    "ActionLocalEvidenceBundleV1",
    "ActionLocalEvidenceRequestV1",
    "ActionLocalGroundRowEvidenceV1",
    "ActionLocalGroundTransitionAuthorityV1",
    "ActionLocalModelEpochV1",
    "ActionLocalOverlayBuildV1",
    "ActionLocalRowNecessityProofV1",
    "ActionLocalSemanticSwitchInvariantViolation",
    "ActionLocalSemanticSwitchResultV1",
    "ActionLocalSemanticSwitchVerificationV1",
    "ActionLocalTransitionReceiptV1",
    "EvidenceLane",
    "EXPECTED_CANONICAL_IDS",
    "EXPECTED_GROUND_ACTION_IDS",
    "EXPECTED_GROUND_ROW_IDS",
    "EXPECTED_X0_STATE_ID",
    "EXPECTED_X1_STATE_ID",
    "PROFILE_KEY",
    "RegisteredActionLocalFixtureV1",
    "SUCCESS_STATUS",
    "SelectedPolicySupportFrontierV1",
    "StrictPolicySwitchWitnessV1",
    "UnrestrictedChallengerFrontierV1",
    "freeze_action_local_evidence_request_v1",
    "registered_action_local_fixture_v1",
    "run_registered_h2_action_local_semantic_switch_v1",
    "verify_registered_h2_action_local_semantic_switch_v1",
]
