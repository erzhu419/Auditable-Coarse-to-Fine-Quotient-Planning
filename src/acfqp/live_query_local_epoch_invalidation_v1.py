"""V0-053 live H2 query-local model-epoch invalidation control.

The production runner interleaves the authentic V0-047 two-round evidence
protocol with the V0-052 eleven-node temporal proof DAG.  In particular, the
first epoch's independently selected failed root is frozen before the second
evidence request is derived or executed.  Lower proof keys use extensional
model slices; only the unchanged C0 slice may survive the registered epoch
transition.  This module deliberately makes no persistent-cache, policy-change,
sample-efficiency, total-work, or general changed-model claim.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from fractions import Fraction
import hashlib
from pathlib import Path
from typing import Any, Mapping

import acfqp.h2_temporal_incremental_proof_dag_v1 as temporal
import acfqp.multistep_query_refinement_v1 as multistep
import acfqp.observation_partial_rapm_v1 as observation_model
import acfqp.partial_model_planner_v1 as planner
import acfqp.partial_sound_audit_v1 as audit
from acfqp._runtime_authority_v1 import (
    RuntimeAuthorityMintV1,
    bind_runtime_authority_v1,
    require_runtime_authority_v1,
    runtime_authority_fingerprint_v1,
)
from acfqp.domains.matching_buffer import LMBKernel
from acfqp.multistep_query_refinement_v1 import (
    MultiStepPlanAuditV1,
    MultiStepPlanProposalV1,
    MultiStepQueryRefinementResultV1,
    MultiStepRefinementTelemetryV1,
)
from acfqp.observation_partial_rapm_v1 import (
    AmbiguityRowStatus,
    DeterministicObservationProfileV1,
    ObservationLogManifestV1,
    PlanningKind,
    PreregisteredObservationAuthorityV1,
    QueryScopedPartialRAPMV3,
)
from acfqp.observed_typed_coordinate_synthesis_v1 import (
    ObservedTypedPartialRAPMResultV1,
)
from acfqp.partial_model_planner_v1 import (
    TypedPartialModelPlanProposalResultV2,
)
from acfqp.partial_sound_audit_v1 import (
    ContingentPlanStageV1,
    FrozenContingentAbstractPlanV1,
    FrozenPartialAuditThresholdsV1,
    PartialAuditOutcome,
    PartialSoundAuditResultV1,
    TypedPartialSoundAuditResultV2,
)
from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id


SCHEMA_VERSION = "1.0.0"
CONTRACT_VERSION = "1.16.0"
PROFILE_KEY = "lmb_h2_live_query_local_epoch_invalidation_v0"
SUCCESS_STATUS = (
    "CERTIFIED_REGISTERED_H2_LIVE_QUERY_LOCAL_EPOCH_INVALIDATION_CONTROL"
)

EXPECTED_AUDIT_SOURCE_SHA256 = (
    "661aee3732afda05c860f5dadae2b3545ecbbed7cee86f27517d1ea5dfcb7934"
)
EXPECTED_PLANNER_SOURCE_SHA256 = (
    "b676c4f91d18ea9406ef1101d7072baccb519a05176496ccf6a867cedb6d4f7d"
)
EXPECTED_MULTISTEP_SOURCE_SHA256 = (
    "d335b509311f6d87a6e2106d1090580f3c7c4cca8cd4eaa4209fff4038e54845"
)
EXPECTED_TEMPORAL_SOURCE_SHA256 = (
    "8ff988035ba360671dfb6c1c874fcceb3f4ea94e45930f0f0bdfae0c1050fbe7"
)
EXPECTED_OBSERVATION_MODEL_SOURCE_SHA256 = (
    "f43203595d4281b58cb53b0fefbc2d24eddd132b9e37c43ee5cff8031425d1bc"
)

EXPECTED_FIRST_MODEL_ID = (
    "e3d550b7d46b516bd443881e14ade00b8a1cc673f141039d09dc585fa2b28fba"
)
EXPECTED_FINAL_MODEL_ID = (
    "a18a29a1c1bd3433ef7ace6d99c67a594a0d587b6b0c2889f71022eaa7437315"
)
EXPECTED_FIRST_PROPOSAL_ID = (
    "b5db44c042eaa656980f942430c2fee6eda6fcf6ec8c0a1af1142b723ec006e4"
)
EXPECTED_ROUND_TWO_REQUEST_ID = (
    "dc79dda993650f03b335217fbdf98cc10449bb79f7374d0440258996b84b1ccf"
)
EXPECTED_FINAL_AUDIT_ID = (
    "81f379b9485d1da2aaf56fd20ff75d5c45c8ac4b870cc6e52b795ef6896e9529"
)
EXPECTED_MULTISTEP_RESULT_ID = (
    "9a3691831b8103d1523333f50b302a5f099dee9d1b8790a893e5998810866d42"
)
EXPECTED_SEMANTICS_ID = (
    "17a7fb36b05d6dcf9ed319cae706a5a5b0fd496359b66348cc444ea16955f264"
)
EXPECTED_ORDERING_PROTOCOL_ID = (
    "e7e0a08ecf6cf5ef04fd990f73065955e6d4412aec5fb474aff1e4660f391da2"
)
EXPECTED_EPOCH_DELTA_ID = (
    "40e6447cfff4526e4b17f4e381bf8067f6dec946a1d3e655a3380c780de053fa"
)
EXPECTED_INVALIDATION_MANIFEST_ID = (
    "a9657e12ebd46cee061263205d103ff4b82dfd557b3923a843ef00c1b841668c"
)
EXPECTED_REQUEST_RESET_ARM_ID = (
    "e91726ac2b17bf42b2890bf456118de04ec9c09bfd07d29830e2239e558340d6"
)
EXPECTED_EPOCH_RESET_ARM_ID = (
    "a51f8e3682aac5d932bb68cfd54193be7bd19f1b302865a2f8ca467438cc69d9"
)
EXPECTED_CROSS_EPOCH_ARM_ID = (
    "5e8c2d23cfcf96c9d810fac1af3069b83eea2caa1a191c6b02e546a29bf21b56"
)
EXPECTED_FIRST_LIVE_EXECUTION_ID = (
    "4818bcaa0a2217bb720b02879869062e58efb4dd0e05a5555c57c0e22ff81572"
)
EXPECTED_FINAL_LIVE_EXECUTION_ID = (
    "3cbe43d106be12824e8d15a27a8fc0e82d37cf37a8c772a191eacd2b5fb77279"
)
EXPECTED_FINAL_CROSS_CACHE_STATE_ID = (
    "270b5b126953dfbe9ab1e33e3f99505f5e0b95f8a5929b1f581b78165706185f"
)
EXPECTED_LIVE_RESULT_ID = (
    "5e46f0eda3f6d9c96e955315034829913dc248d09ed1a73ca8384d4cbcd65d44"
)

GRAY_CODES = ("A0A0", "A0A1", "A1A1", "A1A0")
GRAY_BITS = ((0, 0), (0, 1), (1, 1), (1, 0))
SLOT_ORDER = temporal.SLOT_ORDER
LOWER_SLOT_ORDER = temporal.LOWER_SLOT_ORDER
EXPECTED_TOTALS = {
    "REQUEST_RESET": (110, 0),
    "EPOCH_RESET_GLOBAL_DAG": (70, 40),
    "GLOBAL_CROSS_EPOCH_FACET_DAG": (68, 42),
}
EXPECTED_CROSS_PREFIX_COMPUTES = (11, 19, 27, 34, 35, 45, 53, 60, 67, 68)
EXPECTED_CROSS_PREFIX_HITS = (0, 3, 6, 10, 20, 21, 24, 28, 32, 42)
EXPECTED_CROSS_KIND_COUNTS = {
    "U1": (2, 8), "U0": (2, 8),
    "P1": (4, 6), "P0": (8, 2),
    "C0": (2, 8), "C1": (8, 2),
    "D": (8, 2), "E": (8, 2), "F": (8, 2), "G": (8, 2),
    "R": (10, 0),
}

DOMAIN_TAGS = {
    "semantics": "acfqp:live-epoch-proof-semantics:v1",
    "slice_content": "acfqp:live-epoch-model-slice-content:v1",
    "slice_binding": "acfqp:live-epoch-model-slice-binding:v1",
    "canonical_input": "acfqp:live-epoch-canonical-input:v1",
    "request": "acfqp:live-epoch-proof-request:v1",
    "node_key": "acfqp:live-epoch-proof-node-key:v1",
    "node_result": "acfqp:live-epoch-proof-node-result:v1",
    "entry": "acfqp:live-epoch-proof-entry:v1",
    "resolution": "acfqp:live-epoch-proof-resolution:v1",
    "receipt": "acfqp:live-epoch-proof-receipt:v1",
    "cache_state": "acfqp:live-epoch-proof-cache-state:v1",
    "work": "acfqp:live-epoch-proof-work:v1",
    "epoch": "acfqp:live-epoch-proof-execution:v1",
    "arm": "acfqp:live-epoch-proof-arm:v1",
    "delta": "acfqp:live-epoch-model-delta:v1",
    "invalidation": "acfqp:live-epoch-invalidation-manifest:v1",
    "event": "acfqp:live-epoch-ordering-event:v1",
    "ordering": "acfqp:live-epoch-ordering-protocol:v1",
    "result": "acfqp:live-epoch-invalidation-result:v1",
    "verification": "acfqp:live-epoch-verification-report:v1",
}
if len(DOMAIN_TAGS) != len(set(DOMAIN_TAGS.values())):  # pragma: no cover
    raise RuntimeError("V0-053 content domains must be unique")


class LiveEpochInvariantViolation(ValueError):
    """The registered live ordering, facet, cache, or claim is invalid."""


class LiveEpochName(str, Enum):
    FIRST = "FIRST_OVERLAY_V3"
    FINAL = "FINAL_OVERLAY_V3"


class LiveEpochCacheScope(str, Enum):
    REQUEST_RESET = "REQUEST_RESET"
    EPOCH_RESET_GLOBAL_DAG = "EPOCH_RESET_GLOBAL_DAG"
    GLOBAL_CROSS_EPOCH_FACET_DAG = "GLOBAL_CROSS_EPOCH_FACET_DAG"


class LiveEpochResolutionOutcome(str, Enum):
    COMPUTED = "COMPUTED"
    REUSED = "REUSED"


def _content_id(role: str, payload: Mapping[str, Any]) -> str:
    try:
        encoded = canonical_json_bytes(dict(payload))
        domain = DOMAIN_TAGS[role]
    except (KeyError, TypeError, ValueError) as error:
        raise LiveEpochInvariantViolation(str(error)) from error
    return hashlib.sha256(domain.encode() + b"\x00" + encoded).hexdigest()


def _cid(value: Any, name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise LiveEpochInvariantViolation(f"{name} must be a full content ID") from error


def _source_sha(module: Any) -> str:
    path = Path(module.__file__)
    if path.suffix != ".py" or not path.is_file():
        raise LiveEpochInvariantViolation("registered source is unavailable")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _ftext(value: Fraction) -> str:
    return f"{value.numerator}/{value.denominator}"


@dataclass(frozen=True, slots=True)
class LiveEpochProofSemanticsV1:
    audit_source_sha256: str
    planner_source_sha256: str
    multistep_source_sha256: str
    temporal_source_sha256: str
    observation_model_source_sha256: str
    topology: tuple[tuple[str, tuple[str, ...]], ...]
    horizon: int = 2
    exact_fraction_arithmetic: bool = True

    def __post_init__(self) -> None:
        expected = (
            ("U1", ()), ("U0", ("U1",)),
            ("P1", ()), ("P0", ("P1",)),
            ("C0", ()), ("C1", ("C0",)),
            ("D", ("U0", "P0", "C0", "C1")),
            ("E", ("D",)), ("F", ("D",)),
            ("G", ("C0", "C1")),
            ("R", tuple(item.value for item in LOWER_SLOT_ORDER)),
        )
        if (
            self.audit_source_sha256 != EXPECTED_AUDIT_SOURCE_SHA256
            or self.planner_source_sha256 != EXPECTED_PLANNER_SOURCE_SHA256
            or self.multistep_source_sha256 != EXPECTED_MULTISTEP_SOURCE_SHA256
            or self.temporal_source_sha256 != EXPECTED_TEMPORAL_SOURCE_SHA256
            or self.observation_model_source_sha256
            != EXPECTED_OBSERVATION_MODEL_SOURCE_SHA256
            or self.topology != expected
            or self.horizon != 2
            or self.exact_fraction_arithmetic is not True
        ):
            raise LiveEpochInvariantViolation("registered semantics/source topology changed")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.live_epoch_proof_semantics.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "audit_source_sha256": self.audit_source_sha256,
            "planner_source_sha256": self.planner_source_sha256,
            "multistep_source_sha256": self.multistep_source_sha256,
            "temporal_source_sha256": self.temporal_source_sha256,
            "observation_model_source_sha256": self.observation_model_source_sha256,
            "topology": [
                {"slot": slot, "parents": list(parents)}
                for slot, parents in self.topology
            ],
            "horizon": self.horizon,
            "exact_fraction_arithmetic": self.exact_fraction_arithmetic,
        }

    @property
    def semantics_id(self) -> str:
        return _content_id("semantics", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "semantics_id": self.semantics_id}


def live_epoch_proof_semantics_v1() -> LiveEpochProofSemanticsV1:
    topology = (
        ("U1", ()), ("U0", ("U1",)),
        ("P1", ()), ("P0", ("P1",)),
        ("C0", ()), ("C1", ("C0",)),
        ("D", ("U0", "P0", "C0", "C1")),
        ("E", ("D",)), ("F", ("D",)),
        ("G", ("C0", "C1")),
        ("R", tuple(item.value for item in LOWER_SLOT_ORDER)),
    )
    return LiveEpochProofSemanticsV1(
        _source_sha(audit), _source_sha(planner), _source_sha(multistep),
        _source_sha(temporal), _source_sha(observation_model), topology,
    )


@dataclass(frozen=True, slots=True)
class ModelSliceContentV1:
    slot: temporal.H2TemporalProofSlot
    time_index: int | None
    stage_assignment_id: str | None
    input_ground_row_ids: tuple[str, ...]
    canonical_input_digest: str
    facet_kind: str

    def __post_init__(self) -> None:
        if type(self.slot) is not temporal.H2TemporalProofSlot:
            raise LiveEpochInvariantViolation("model slice slot type changed")
        if self.time_index is not None and self.time_index not in (0, 1):
            raise LiveEpochInvariantViolation("model slice time lies outside H2")
        if self.stage_assignment_id is not None:
            _cid(self.stage_assignment_id, "model slice stage assignment")
        if (
            type(self.input_ground_row_ids) is not tuple
            or self.input_ground_row_ids
            != tuple(sorted(set(self.input_ground_row_ids)))
        ):
            raise LiveEpochInvariantViolation("model slice row IDs are not canonical")
        for value in (*self.input_ground_row_ids, self.canonical_input_digest):
            _cid(value, "model slice content dependency")
        if not self.facet_kind or type(self.facet_kind) is not str:
            raise LiveEpochInvariantViolation("model slice facet kind is empty")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.model_slice_content.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "slot": self.slot.value,
            "time_index": self.time_index,
            "stage_assignment_id": self.stage_assignment_id,
            "input_ground_row_ids": list(self.input_ground_row_ids),
            "canonical_input_digest": self.canonical_input_digest,
            "facet_kind": self.facet_kind,
        }

    @property
    def content_id(self) -> str:
        return _content_id("slice_content", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "content_id": self.content_id}


@dataclass(frozen=True, slots=True)
class ModelSliceBindingV1:
    epoch: LiveEpochName
    model_id: str
    overlay_build_result_id: str
    evidence_request_id: str
    evidence_bundle_id: str
    content: ModelSliceContentV1

    def __post_init__(self) -> None:
        if type(self.epoch) is not LiveEpochName or type(self.content) is not ModelSliceContentV1:
            raise LiveEpochInvariantViolation("model slice binding type changed")
        for name in (
            "model_id", "overlay_build_result_id", "evidence_request_id",
            "evidence_bundle_id",
        ):
            _cid(getattr(self, name), f"model slice binding {name}")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.model_slice_binding.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "epoch": self.epoch.value,
            "model_id": self.model_id,
            "overlay_build_result_id": self.overlay_build_result_id,
            "evidence_request_id": self.evidence_request_id,
            "evidence_bundle_id": self.evidence_bundle_id,
            "content": self.content.to_document(),
        }

    @property
    def binding_id(self) -> str:
        return _content_id("slice_binding", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "binding_id": self.binding_id}


@dataclass(frozen=True, slots=True)
class LiveEpochProofRequestV1:
    epoch: LiveEpochName
    request_index: int
    role: temporal.H2TemporalProofRole
    schedule_code: str
    model_id: str
    thresholds_id: str
    contingent_plan: FrozenContingentAbstractPlanV1
    stage_assignment_ids: tuple[str, str]
    planner_result_id: str | None

    def __post_init__(self) -> None:
        if (
            type(self.epoch) is not LiveEpochName
            or type(self.request_index) is not int
            or self.request_index not in range(1, 6)
            or type(self.role) is not temporal.H2TemporalProofRole
            or self.schedule_code not in GRAY_CODES
            or type(self.contingent_plan) is not FrozenContingentAbstractPlanV1
            or type(self.stage_assignment_ids) is not tuple
            or len(self.stage_assignment_ids) != 2
        ):
            raise LiveEpochInvariantViolation("live proof request shape changed")
        for value in (self.model_id, self.thresholds_id, *self.stage_assignment_ids):
            _cid(value, "live proof request identity")
        selected = self.request_index == 5
        if (
            selected != (self.role is temporal.H2TemporalProofRole.INDEPENDENT_SELECTED_PLAN_CERTIFICATE)
            or selected != (self.planner_result_id is not None)
            or self.contingent_plan.partial_model_id != self.model_id
        ):
            raise LiveEpochInvariantViolation("live proof request role/model changed")
        if self.planner_result_id is not None:
            _cid(self.planner_result_id, "live proof planner result")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.live_epoch_proof_request.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "epoch": self.epoch.value,
            "request_index": self.request_index,
            "role": self.role.value,
            "schedule_code": self.schedule_code,
            "model_id": self.model_id,
            "thresholds_id": self.thresholds_id,
            "contingent_plan": self.contingent_plan.to_document(),
            "stage_assignment_ids": list(self.stage_assignment_ids),
            "planner_result_id": (
                self.planner_result_id if self.planner_result_id is not None
                else {"kind": "NOT_APPLICABLE", "reason": "CANDIDATE_PRECEDES_SELECTION"}
            ),
        }

    @property
    def request_id(self) -> str:
        return _content_id("request", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "request_id": self.request_id}


_PARENT_COUNTS = {
    temporal.H2TemporalProofSlot.U1: 0,
    temporal.H2TemporalProofSlot.U0: 1,
    temporal.H2TemporalProofSlot.P1: 0,
    temporal.H2TemporalProofSlot.P0: 1,
    temporal.H2TemporalProofSlot.C0: 0,
    temporal.H2TemporalProofSlot.C1: 1,
    temporal.H2TemporalProofSlot.D: 4,
    temporal.H2TemporalProofSlot.E: 1,
    temporal.H2TemporalProofSlot.F: 1,
    temporal.H2TemporalProofSlot.G: 2,
    temporal.H2TemporalProofSlot.R: 10,
}


@dataclass(frozen=True, slots=True)
class LiveEpochProofNodeKeyV1:
    slot: temporal.H2TemporalProofSlot
    semantics_id: str
    model_slice_content_id: str
    time_index: int | None
    stage_assignment_id: str | None
    ordered_parent_entry_ids: tuple[str, ...]
    identity_terms: tuple[tuple[str, str], ...]

    def __post_init__(self) -> None:
        if type(self.slot) is not temporal.H2TemporalProofSlot:
            raise LiveEpochInvariantViolation("proof node slot type changed")
        for value in (self.semantics_id, self.model_slice_content_id):
            _cid(value, "proof node identity")
        if self.time_index is not None and self.time_index not in (0, 1):
            raise LiveEpochInvariantViolation("proof node time lies outside H2")
        if self.stage_assignment_id is not None:
            _cid(self.stage_assignment_id, "proof node stage assignment")
        if (
            type(self.ordered_parent_entry_ids) is not tuple
            or len(self.ordered_parent_entry_ids) != _PARENT_COUNTS[self.slot]
        ):
            raise LiveEpochInvariantViolation("proof node parent topology changed")
        for value in self.ordered_parent_entry_ids:
            _cid(value, "proof node parent entry")
        if (
            type(self.identity_terms) is not tuple
            or self.identity_terms != tuple(sorted(self.identity_terms))
            or len({name for name, _ in self.identity_terms})
            != len(self.identity_terms)
        ):
            raise LiveEpochInvariantViolation("proof node identity terms are not canonical")
        lower_names = {name for name, _ in self.identity_terms}
        expected_term_names = {
            temporal.H2TemporalProofSlot.U1: {
                "formula_id", "return_bound_proof_id", "reward_weights_digest"
            },
            temporal.H2TemporalProofSlot.U0: {
                "formula_id", "return_bound_proof_id", "reward_weights_digest"
            },
            temporal.H2TemporalProofSlot.P1: {
                "formula_id", "return_bound_proof_id", "reward_weights_digest"
            },
            temporal.H2TemporalProofSlot.P0: {
                "formula_id", "return_bound_proof_id", "reward_weights_digest"
            },
            temporal.H2TemporalProofSlot.C0: {
                "formula_id", "initial_distribution_digest"
            },
            temporal.H2TemporalProofSlot.C1: {"formula_id"},
            temporal.H2TemporalProofSlot.D: {
                "formula_id", "initial_distribution_digest",
                "return_bound_proof_id", "reward_weights_digest",
            },
            temporal.H2TemporalProofSlot.E: {
                "formula_id", "normalized_regret_tolerance"
            },
            temporal.H2TemporalProofSlot.F: {"formula_id", "risk_tolerance"},
            temporal.H2TemporalProofSlot.G: {"formula_id"},
            temporal.H2TemporalProofSlot.R: {
                "formula_id", "model_id", "thresholds_id", "plan_id",
                "planner_result_id", "request_id", "role",
            },
        }[self.slot]
        expected_time = {
            temporal.H2TemporalProofSlot.U1: 1,
            temporal.H2TemporalProofSlot.U0: 0,
            temporal.H2TemporalProofSlot.P1: 1,
            temporal.H2TemporalProofSlot.P0: 0,
            temporal.H2TemporalProofSlot.C0: 0,
            temporal.H2TemporalProofSlot.C1: 1,
            temporal.H2TemporalProofSlot.D: None,
            temporal.H2TemporalProofSlot.E: None,
            temporal.H2TemporalProofSlot.F: None,
            temporal.H2TemporalProofSlot.G: None,
            temporal.H2TemporalProofSlot.R: None,
        }[self.slot]
        stage_required = self.slot in {
            temporal.H2TemporalProofSlot.P1,
            temporal.H2TemporalProofSlot.P0,
            temporal.H2TemporalProofSlot.C0,
            temporal.H2TemporalProofSlot.C1,
            temporal.H2TemporalProofSlot.D,
        }
        if (
            lower_names != expected_term_names
            or self.time_index != expected_time
            or stage_required != (self.stage_assignment_id is not None)
        ):
            raise LiveEpochInvariantViolation("proof node slot/time/stage/term allowlist changed")
        if self.slot is temporal.H2TemporalProofSlot.R:
            required = {
                "model_id", "thresholds_id", "plan_id", "planner_result_id",
                "request_id", "role",
            }
            if not required <= lower_names:
                raise LiveEpochInvariantViolation("R does not bind complete epoch identities")
        elif {"model_id", "epoch", "plan_id", "request_id", "role"} & lower_names:
            raise LiveEpochInvariantViolation("lower proof key leaked whole-epoch identity")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.live_epoch_proof_node_key.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "slot": self.slot.value,
            "semantics_id": self.semantics_id,
            "model_slice_content_id": self.model_slice_content_id,
            "time_index": self.time_index,
            "stage_assignment_id": self.stage_assignment_id,
            "ordered_parent_entry_ids": list(self.ordered_parent_entry_ids),
            "identity_terms": [
                {"name": name, "value": value} for name, value in self.identity_terms
            ],
        }

    @property
    def node_key_id(self) -> str:
        return _content_id("node_key", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "node_key_id": self.node_key_id}


@dataclass(frozen=True, slots=True)
class LiveEpochProofNodeEntryV1:
    key: LiveEpochProofNodeKeyV1
    result_digest: str
    result_semantics: str

    def __post_init__(self) -> None:
        if type(self.key) is not LiveEpochProofNodeKeyV1:
            raise LiveEpochInvariantViolation("proof entry key type changed")
        _cid(self.result_digest, "proof entry result digest")
        if not self.result_semantics:
            raise LiveEpochInvariantViolation("proof entry result semantics is empty")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.live_epoch_proof_entry.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "key": self.key.to_document(),
            "result_digest": self.result_digest,
            "result_semantics": self.result_semantics,
        }

    @property
    def entry_id(self) -> str:
        return _content_id("entry", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "entry_id": self.entry_id}


@dataclass(frozen=True, slots=True)
class LiveEpochProofResolutionV1:
    sequence_number: int
    epoch: LiveEpochName
    request_id: str
    slot: temporal.H2TemporalProofSlot
    slice_binding_id: str
    node_key_id: str
    entry_id: str
    outcome: LiveEpochResolutionOutcome
    pre_cache_state_id: str
    post_cache_state_id: str

    def __post_init__(self) -> None:
        if (
            type(self.sequence_number) is not int or self.sequence_number < 1
            or type(self.epoch) is not LiveEpochName
            or type(self.slot) is not temporal.H2TemporalProofSlot
            or type(self.outcome) is not LiveEpochResolutionOutcome
        ):
            raise LiveEpochInvariantViolation("proof resolution type/index changed")
        for name in (
            "request_id", "slice_binding_id", "node_key_id", "entry_id",
            "pre_cache_state_id", "post_cache_state_id",
        ):
            _cid(getattr(self, name), f"proof resolution {name}")
        if (
            self.outcome is LiveEpochResolutionOutcome.REUSED
            and self.pre_cache_state_id != self.post_cache_state_id
        ):
            raise LiveEpochInvariantViolation("cache hit changed append-only state")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.live_epoch_proof_resolution.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "sequence_number": self.sequence_number,
            "epoch": self.epoch.value,
            "request_id": self.request_id,
            "slot": self.slot.value,
            "slice_binding_id": self.slice_binding_id,
            "node_key_id": self.node_key_id,
            "entry_id": self.entry_id,
            "outcome": self.outcome.value,
            "pre_cache_state_id": self.pre_cache_state_id,
            "post_cache_state_id": self.post_cache_state_id,
        }

    @property
    def resolution_id(self) -> str:
        return _content_id("resolution", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "resolution_id": self.resolution_id}


@dataclass(frozen=True, slots=True)
class LiveEpochProofReceiptV1:
    request: LiveEpochProofRequestV1
    resolution_ids: tuple[str, ...]
    root_entry_id: str
    audit_result: PartialSoundAuditResultV1

    def __post_init__(self) -> None:
        if (
            type(self.request) is not LiveEpochProofRequestV1
            or type(self.resolution_ids) is not tuple
            or len(self.resolution_ids) != 11
            or type(self.audit_result) is not PartialSoundAuditResultV1
        ):
            raise LiveEpochInvariantViolation("proof receipt nested type/cardinality changed")
        for value in (*self.resolution_ids, self.root_entry_id):
            _cid(value, "proof receipt dependency")
        if (
            self.audit_result.partial_model_id != self.request.model_id
            or self.audit_result.thresholds_id != self.request.thresholds_id
            or self.audit_result.contingent_plan_id
            != self.request.contingent_plan.plan_id
        ):
            raise LiveEpochInvariantViolation("proof receipt root binding changed")
        self.request.__post_init__()
        self.audit_result.__post_init__()

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.live_epoch_proof_receipt.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "request": self.request.to_document(),
            "resolution_ids": list(self.resolution_ids),
            "root_entry_id": self.root_entry_id,
            "audit_result": self.audit_result.to_document(),
        }

    @property
    def receipt_id(self) -> str:
        return _content_id("receipt", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "receipt_id": self.receipt_id}


@dataclass(frozen=True, slots=True)
class LiveEpochProofWorkV1:
    computed: int
    reused: int
    slot_counts: tuple[tuple[str, int, int], ...]

    def __post_init__(self) -> None:
        if (
            type(self.computed) is not int or type(self.reused) is not int
            or self.computed < 0 or self.reused < 0
            or type(self.slot_counts) is not tuple
            or tuple(name for name, _, _ in self.slot_counts)
            != tuple(item.value for item in SLOT_ORDER)
            or any(type(c) is not int or type(r) is not int or c < 0 or r < 0
                   for _, c, r in self.slot_counts)
            or sum(c for _, c, _ in self.slot_counts) != self.computed
            or sum(r for _, _, r in self.slot_counts) != self.reused
        ):
            raise LiveEpochInvariantViolation("proof work counters are inconsistent")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.live_epoch_proof_work.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "computed": self.computed,
            "reused": self.reused,
            "slot_counts": [
                {"slot": name, "computed": computed, "reused": reused}
                for name, computed, reused in self.slot_counts
            ],
        }

    @property
    def work_id(self) -> str:
        return _content_id("work", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "work_id": self.work_id}


def _derive_work(resolutions: tuple[LiveEpochProofResolutionV1, ...]) -> LiveEpochProofWorkV1:
    rows = []
    for slot in SLOT_ORDER:
        matching = tuple(item for item in resolutions if item.slot is slot)
        rows.append((
            slot.value,
            sum(item.outcome is LiveEpochResolutionOutcome.COMPUTED for item in matching),
            sum(item.outcome is LiveEpochResolutionOutcome.REUSED for item in matching),
        ))
    return LiveEpochProofWorkV1(
        sum(item.outcome is LiveEpochResolutionOutcome.COMPUTED for item in resolutions),
        sum(item.outcome is LiveEpochResolutionOutcome.REUSED for item in resolutions),
        tuple(rows),
    )


def _cache_state_id(scope: LiveEpochCacheScope, cache: Mapping[str, str]) -> str:
    return _content_id(
        "cache_state",
        {
            "schema": "acfqp.live_epoch_proof_cache_state.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "scope": scope.value,
            "entries": [
                {"node_key_id": key, "entry_id": value}
                for key, value in sorted(cache.items())
            ],
        },
    )


def _canonical_input_digest(document: Mapping[str, Any]) -> str:
    return _content_id(
        "canonical_input",
        {
            "schema": "acfqp.live_epoch_canonical_input.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "document": dict(document),
        },
    )


def _slice_content(
    slot: temporal.H2TemporalProofSlot,
    model: QueryScopedPartialRAPMV3,
    thresholds: FrozenPartialAuditThresholdsV1,
    active_cells: Mapping[str, Any],
    realizations: Mapping[tuple[str, str], tuple[Any, ...]],
    state_to_cell: Mapping[str, str],
    stage_map: Mapping[str, str] | None,
    stage_assignment_id: str | None,
    parent_value: Any | None,
) -> ModelSliceContentV1:
    time_index = {
        temporal.H2TemporalProofSlot.U1: 1,
        temporal.H2TemporalProofSlot.U0: 0,
        temporal.H2TemporalProofSlot.P1: 1,
        temporal.H2TemporalProofSlot.P0: 0,
        temporal.H2TemporalProofSlot.C0: 0,
        temporal.H2TemporalProofSlot.C1: 1,
    }.get(slot)
    row_ids: tuple[str, ...] = ()
    if slot in (temporal.H2TemporalProofSlot.U1, temporal.H2TemporalProofSlot.U0):
        active_states = {
            state_id for cell in active_cells.values() for state_id in cell.member_state_ids
        }
        rows = tuple(
            sorted(
                (item for item in model.ground_rows if item.state_id in active_states),
                key=lambda item: item.ground_row_id,
            )
        )
        row_ids = tuple(item.ground_row_id for item in rows)
        document = {
            "facet_kind": "ALL_ACTIVE_GROUND_ROWS_REWARD_CAPS_EXTERNAL_V1",
            "active_cells": [active_cells[key].to_document() for key in sorted(active_cells)],
            "ground_rows": [item.to_document() for item in rows],
            "reward_feature_caps": [item.to_document() for item in model.reward_feature_caps],
            "external_boundary_id": model.external_boundary_id,
        }
        kind = "ALL_ACTIVE_GROUND_ROWS_REWARD_CAPS_EXTERNAL_V1"
    elif slot in (temporal.H2TemporalProofSlot.P1, temporal.H2TemporalProofSlot.P0):
        if stage_map is None:
            raise LiveEpochInvariantViolation("P slice lacks a stage assignment")
        selected = tuple(
            item
            for cell_id in sorted(active_cells)
            for item in realizations[(cell_id, stage_map[cell_id])]
        )
        row_ids = tuple(sorted({row for item in selected for row in item.support_ground_row_ids}))
        document = {
            "facet_kind": "ALL_ACTIVE_SELECTED_REALIZATIONS_REWARD_CAPS_EXTERNAL_V1",
            "active_cells": [active_cells[key].to_document() for key in sorted(active_cells)],
            "selected_realizations": [item.to_document() for item in selected],
            "reward_feature_caps": [item.to_document() for item in model.reward_feature_caps],
            "external_boundary_id": model.external_boundary_id,
        }
        kind = "ALL_ACTIVE_SELECTED_REALIZATIONS_REWARD_CAPS_EXTERNAL_V1"
    elif slot in (temporal.H2TemporalProofSlot.C0, temporal.H2TemporalProofSlot.C1):
        if stage_map is None:
            raise LiveEpochInvariantViolation("C slice lacks a stage assignment")
        if slot is temporal.H2TemporalProofSlot.C0:
            reach: dict[str, Fraction] = {}
            for item in thresholds.initial_state_distribution:
                cell_id = state_to_cell[item.state_id]
                reach[cell_id] = reach.get(cell_id, Fraction(0)) + item.probability
        else:
            if type(parent_value) is not temporal._CStage:
                raise LiveEpochInvariantViolation("C1 slice lacks its exact C0 value")
            reach = dict(parent_value.next_reach)
        reached_cells = tuple(sorted(cell_id for cell_id, mass in reach.items() if mass > 0))
        selected = tuple(
            item
            for cell_id in reached_cells
            for item in realizations[(cell_id, stage_map[cell_id])]
        )
        row_ids = tuple(sorted({row for item in selected for row in item.support_ground_row_ids}))
        document = {
            "facet_kind": "POSITIVE_REACH_SELECTED_REALIZATIONS_EXTERNAL_V1",
            "reach": [
                {"cell_id": cell_id, "mass": _ftext(reach[cell_id])}
                for cell_id in reached_cells
            ],
            "active_destination_cell_ids": sorted(active_cells),
            "selected_realizations": [item.to_document() for item in selected],
            "external_boundary_id": model.external_boundary_id,
        }
        kind = "POSITIVE_REACH_SELECTED_REALIZATIONS_EXTERNAL_V1"
    elif slot is temporal.H2TemporalProofSlot.D:
        if stage_map is None:
            raise LiveEpochInvariantViolation("D slice lacks its stage-zero assignment")
        selected = tuple(
            next(
                item
                for item in realizations[(state_to_cell[support.state_id], stage_map[state_to_cell[support.state_id]])]
                if item.state_id == support.state_id
            )
            for support in thresholds.initial_state_distribution
        )
        row_ids = tuple(sorted({row for item in selected for row in item.support_ground_row_ids}))
        document = {
            "facet_kind": "INITIAL_SUPPORT_DIRECT_REALIZATION_V1",
            "active_destination_cell_ids": sorted(active_cells),
            "selected_initial_support_realizations": [item.to_document() for item in selected],
            "reward_feature_caps": [item.to_document() for item in model.reward_feature_caps],
            "external_boundary_id": model.external_boundary_id,
        }
        kind = "INITIAL_SUPPORT_DIRECT_REALIZATION_V1"
    elif slot is temporal.H2TemporalProofSlot.R:
        row_ids = tuple(sorted(item.ground_row_id for item in model.ground_rows))
        document = {
            "facet_kind": "FULL_EPOCH_MODEL_ROOT_V1",
            "model": model.to_document(),
        }
        kind = "FULL_EPOCH_MODEL_ROOT_V1"
    else:
        document = {
            "facet_kind": "PARENT_DERIVED_NO_DIRECT_MODEL_READ_V1",
            "slot": slot.value,
        }
        kind = "PARENT_DERIVED_NO_DIRECT_MODEL_READ_V1"
    return ModelSliceContentV1(
        slot,
        time_index,
        stage_assignment_id,
        row_ids,
        _canonical_input_digest(document),
        kind,
    )


def _identity_terms(
    slot: temporal.H2TemporalProofSlot,
    thresholds: FrozenPartialAuditThresholdsV1,
    request: LiveEpochProofRequestV1,
) -> tuple[tuple[str, str], ...]:
    weights_digest = _canonical_input_digest({
        "reward_weights": [item.to_document() for item in thresholds.reward_weights]
    })
    initial_digest = _canonical_input_digest({
        "initial_distribution": [item.to_document() for item in thresholds.initial_state_distribution]
    })
    return_bound = thresholds.return_bound_proof.proof_id
    if slot in (temporal.H2TemporalProofSlot.U1, temporal.H2TemporalProofSlot.U0):
        terms = {
            "formula_id": "STAGE_LOCAL_UNRESTRICTED_BELLMAN_V1",
            "return_bound_proof_id": return_bound,
            "reward_weights_digest": weights_digest,
        }
    elif slot in (temporal.H2TemporalProofSlot.P1, temporal.H2TemporalProofSlot.P0):
        terms = {
            "formula_id": "STAGE_LOCAL_FIXED_POLICY_BELLMAN_V1",
            "return_bound_proof_id": return_bound,
            "reward_weights_digest": weights_digest,
        }
    elif slot is temporal.H2TemporalProofSlot.C0:
        terms = {
            "formula_id": "STAGE_LOCAL_FORWARD_REACHABILITY_V1",
            "initial_distribution_digest": initial_digest,
        }
    elif slot is temporal.H2TemporalProofSlot.C1:
        terms = {"formula_id": "STAGE_LOCAL_FORWARD_REACHABILITY_V1"}
    elif slot is temporal.H2TemporalProofSlot.D:
        terms = {
            "formula_id": "ROOT_SUPPORT_VALUE_RISK_METRICS_V1",
            "initial_distribution_digest": initial_digest,
            "return_bound_proof_id": return_bound,
            "reward_weights_digest": weights_digest,
        }
    elif slot is temporal.H2TemporalProofSlot.E:
        terms = {
            "formula_id": "REGRET_THRESHOLD_VERDICT_V1",
            "normalized_regret_tolerance": _ftext(thresholds.normalized_regret_tolerance),
        }
    elif slot is temporal.H2TemporalProofSlot.F:
        terms = {
            "formula_id": "RISK_THRESHOLD_VERDICT_V1",
            "risk_tolerance": _ftext(thresholds.risk_tolerance),
        }
    elif slot is temporal.H2TemporalProofSlot.G:
        terms = {"formula_id": "EXTERNAL_COVERAGE_VERDICT_V1"}
    else:
        terms = {
            "formula_id": "FULL_IDENTITY_LEGACY_V1_ROOT_V1",
            "model_id": request.model_id,
            "thresholds_id": request.thresholds_id,
            "plan_id": request.contingent_plan.plan_id,
            "planner_result_id": request.planner_result_id or "NOT_APPLICABLE",
            "request_id": request.request_id,
            "role": request.role.value,
        }
    return tuple(sorted(terms.items()))


def _node_result_digest(slot: temporal.H2TemporalProofSlot, value: Any) -> str:
    return _content_id(
        "node_result",
        {
            "schema": "acfqp.live_epoch_proof_node_result.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "slot": slot.value,
            "document": temporal._value_document(slot, value),
        },
    )


def _result_semantics(slot: temporal.H2TemporalProofSlot) -> str:
    return {
        temporal.H2TemporalProofSlot.U1: "UNRESTRICTED_BELLMAN_T1",
        temporal.H2TemporalProofSlot.U0: "UNRESTRICTED_BELLMAN_T0",
        temporal.H2TemporalProofSlot.P1: "FIXED_POLICY_BELLMAN_T1",
        temporal.H2TemporalProofSlot.P0: "FIXED_POLICY_BELLMAN_T0",
        temporal.H2TemporalProofSlot.C0: "FORWARD_REACHABILITY_T0",
        temporal.H2TemporalProofSlot.C1: "FORWARD_REACHABILITY_T1",
        temporal.H2TemporalProofSlot.D: "ROOT_VALUE_RISK_METRICS",
        temporal.H2TemporalProofSlot.E: "REGRET_VERDICT",
        temporal.H2TemporalProofSlot.F: "RISK_VERDICT",
        temporal.H2TemporalProofSlot.G: "EXTERNAL_COVERAGE_VERDICT",
        temporal.H2TemporalProofSlot.R: "FULL_LEGACY_AUDIT_ROOT",
    }[slot]


class _Runtime:
    def __init__(
        self,
        scope: LiveEpochCacheScope,
        semantics: LiveEpochProofSemanticsV1,
    ) -> None:
        self.scope = scope
        self.semantics = semantics
        self.cache: dict[str, str] = {}
        self.live_values: dict[str, Any] = {}
        self.entries: dict[str, LiveEpochProofNodeEntryV1] = {}
        self.bindings: dict[str, ModelSliceBindingV1] = {}
        self.resolutions: list[LiveEpochProofResolutionV1] = []

    def reset(self) -> None:
        self.cache.clear()
        self.live_values.clear()

    def resolve(
        self,
        epoch: LiveEpochName,
        request: LiveEpochProofRequestV1,
        binding: ModelSliceBindingV1,
        parent_entries: tuple[LiveEpochProofNodeEntryV1, ...],
        thresholds: FrozenPartialAuditThresholdsV1,
        factory: Any,
    ) -> tuple[LiveEpochProofNodeEntryV1, Any]:
        content = binding.content
        key = LiveEpochProofNodeKeyV1(
            content.slot,
            self.semantics.semantics_id,
            content.content_id,
            content.time_index,
            content.stage_assignment_id,
            tuple(item.entry_id for item in parent_entries),
            _identity_terms(content.slot, thresholds, request),
        )
        pre = _cache_state_id(self.scope, self.cache)
        existing = self.cache.get(key.node_key_id)
        if existing is None:
            value = factory()
            entry = LiveEpochProofNodeEntryV1(
                key, _node_result_digest(content.slot, value),
                _result_semantics(content.slot),
            )
            self.cache[key.node_key_id] = entry.entry_id
            self.live_values[key.node_key_id] = value
            self.entries[entry.entry_id] = entry
            outcome = LiveEpochResolutionOutcome.COMPUTED
        else:
            entry = self.entries[existing]
            value = self.live_values[key.node_key_id]
            if entry.result_digest != _node_result_digest(content.slot, value):
                raise LiveEpochInvariantViolation("retained cache value digest changed")
            outcome = LiveEpochResolutionOutcome.REUSED
        self.bindings[binding.binding_id] = binding
        post = _cache_state_id(self.scope, self.cache)
        resolution = LiveEpochProofResolutionV1(
            len(self.resolutions) + 1, epoch, request.request_id, content.slot,
            binding.binding_id, key.node_key_id, entry.entry_id, outcome, pre, post,
        )
        self.resolutions.append(resolution)
        return entry, value


@dataclass(frozen=True, slots=True)
class LiveEpochProofExecutionV1:
    epoch: LiveEpochName
    model_id: str
    thresholds_id: str
    request_receipts: tuple[LiveEpochProofReceiptV1, ...]
    plan_proposal: MultiStepPlanProposalV1
    selected_plan_audit: MultiStepPlanAuditV1
    resolution_ids: tuple[str, ...]
    work: LiveEpochProofWorkV1
    pre_cache_state_id: str
    post_cache_state_id: str

    def __post_init__(self) -> None:
        if (
            type(self.epoch) is not LiveEpochName
            or type(self.request_receipts) is not tuple
            or len(self.request_receipts) != 5
            or any(type(item) is not LiveEpochProofReceiptV1 for item in self.request_receipts)
            or type(self.plan_proposal) is not MultiStepPlanProposalV1
            or type(self.selected_plan_audit) is not MultiStepPlanAuditV1
            or type(self.resolution_ids) is not tuple
            or len(self.resolution_ids) != 55
            or type(self.work) is not LiveEpochProofWorkV1
        ):
            raise LiveEpochInvariantViolation("epoch execution nested artifacts changed")
        for value in (
            self.model_id, self.thresholds_id, self.pre_cache_state_id,
            self.post_cache_state_id, *self.resolution_ids,
        ):
            _cid(value, "epoch execution identity")
        if (
            self.plan_proposal.query_scoped_model_id != self.model_id
            or self.plan_proposal.thresholds_id != self.thresholds_id
            or self.selected_plan_audit.query_scoped_model_id != self.model_id
            or self.selected_plan_audit.planner_result_id
            != self.plan_proposal.result_id
            or self.selected_plan_audit.audit_result.to_document()
            != self.request_receipts[-1].audit_result.to_document()
            or self.work.computed + self.work.reused != 55
            or tuple(item.request.request_index for item in self.request_receipts)
            != (1, 2, 3, 4, 5)
            or tuple(item.request.schedule_code for item in self.request_receipts[:4])
            != GRAY_CODES
        ):
            raise LiveEpochInvariantViolation("epoch proposal/selected/root chain changed")
        if any(
            receipt.request.epoch is not self.epoch
            or receipt.request.model_id != self.model_id
            or receipt.request.thresholds_id != self.thresholds_id
            for receipt in self.request_receipts
        ):
            raise LiveEpochInvariantViolation("epoch receipt escaped model/threshold ownership")
        if (
            any(
                receipt.request.role
                is not temporal.H2TemporalProofRole.CANDIDATE_RANKING_AUDIT
                or receipt.request.planner_result_id is not None
                for receipt in self.request_receipts[:4]
            )
            or self.request_receipts[-1].request.role
            is not temporal.H2TemporalProofRole.INDEPENDENT_SELECTED_PLAN_CERTIFICATE
            or self.request_receipts[-1].request.planner_result_id
            != self.plan_proposal.result_id
            or self.request_receipts[-1].request.contingent_plan.to_document()
            != self.plan_proposal.selected_plan.to_document()
            or self.selected_plan_audit.selected_plan_id
            != self.plan_proposal.selected_plan.plan_id
        ):
            raise LiveEpochInvariantViolation("candidate/selected proof roles were conflated")
        # Candidate summaries are reconstructed without trusting selection fields.
        expected_summary_documents = tuple(sorted(
            (
                planner.PartialPlannerCandidateSummaryV1(
                    receipt.audit_result.robust_bounds.partial_model_id,
                    receipt.audit_result.robust_bounds.thresholds_id,
                    receipt.audit_result.robust_bounds.return_bound_proof_id,
                    receipt.request.contingent_plan.plan_id,
                    receipt.audit_result.result_id,
                    receipt.audit_result.outcome,
                    receipt.audit_result.robust_bounds.policy_reward_lower,
                    receipt.audit_result.robust_bounds.policy_reward_upper,
                    receipt.audit_result.robust_bounds.policy_failure_lower,
                    receipt.audit_result.robust_bounds.policy_failure_upper,
                    receipt.audit_result.robust_bounds.raw_distribution_regret,
                    receipt.audit_result.robust_bounds.normalized_distribution_regret,
                    receipt.audit_result.robust_bounds.maximum_support_point_normalized_regret,
                    receipt.audit_result.robust_bounds.risk_tolerance,
                    receipt.audit_result.robust_bounds.policy_failure_upper
                    <= receipt.audit_result.robust_bounds.risk_tolerance,
                    receipt.audit_result.robust_bounds.external_coverage_certified,
                ).to_document()
                for receipt in self.request_receipts[:4]
            ),
            key=lambda item: item["contingent_plan_id"],
        ))
        if tuple(item.to_document() for item in self.plan_proposal.candidate_summaries) != expected_summary_documents:
            raise LiveEpochInvariantViolation("proposal summaries were not derived from candidate roots")
        selected_candidates = tuple(
            receipt for receipt in self.request_receipts[:4]
            if receipt.request.contingent_plan.plan_id
            == self.plan_proposal.selected_plan.plan_id
        )
        if len(selected_candidates) != 1:
            raise LiveEpochInvariantViolation("selected plan is absent or duplicated among candidates")
        selected_candidate = selected_candidates[0]
        if selected_candidate.audit_result.to_document() != self.request_receipts[-1].audit_result.to_document():
            raise LiveEpochInvariantViolation("selected root differs from its independent candidate semantics")
        for item in self.request_receipts:
            item.__post_init__()
        self.plan_proposal.__post_init__()
        self.selected_plan_audit.__post_init__()
        self.work.__post_init__()

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.live_epoch_proof_execution.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "epoch": self.epoch.value,
            "model_id": self.model_id,
            "thresholds_id": self.thresholds_id,
            "request_receipts": [item.to_document() for item in self.request_receipts],
            "plan_proposal": self.plan_proposal.to_document(),
            "selected_plan_audit": self.selected_plan_audit.to_document(),
            "resolution_ids": list(self.resolution_ids),
            "work": self.work.to_document(),
            "pre_cache_state_id": self.pre_cache_state_id,
            "post_cache_state_id": self.post_cache_state_id,
        }

    @property
    def execution_id(self) -> str:
        return _content_id("epoch", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "execution_id": self.execution_id}


@dataclass(frozen=True, slots=True)
class LiveEpochProofArmV1:
    scope: LiveEpochCacheScope
    first_epoch: LiveEpochProofExecutionV1
    final_epoch: LiveEpochProofExecutionV1
    resolutions: tuple[LiveEpochProofResolutionV1, ...]
    slice_bindings: tuple[ModelSliceBindingV1, ...]
    entry_catalogue: tuple[LiveEpochProofNodeEntryV1, ...]
    aggregate_work: LiveEpochProofWorkV1
    prefix_computes: tuple[int, ...]
    prefix_reuses: tuple[int, ...]
    initial_cache_empty: bool = True

    def __post_init__(self) -> None:
        if (
            type(self.scope) is not LiveEpochCacheScope
            or type(self.first_epoch) is not LiveEpochProofExecutionV1
            or type(self.final_epoch) is not LiveEpochProofExecutionV1
            or self.first_epoch.epoch is not LiveEpochName.FIRST
            or self.final_epoch.epoch is not LiveEpochName.FINAL
            or type(self.resolutions) is not tuple
            or len(self.resolutions) != 110
            or any(type(item) is not LiveEpochProofResolutionV1 for item in self.resolutions)
            or type(self.slice_bindings) is not tuple
            or type(self.entry_catalogue) is not tuple
            or type(self.aggregate_work) is not LiveEpochProofWorkV1
            or self.prefix_computes != tuple(
                sum(item.outcome is LiveEpochResolutionOutcome.COMPUTED
                    for item in self.resolutions[:11 * index])
                for index in range(1, 11)
            )
            or self.prefix_reuses != tuple(
                sum(item.outcome is LiveEpochResolutionOutcome.REUSED
                    for item in self.resolutions[:11 * index])
                for index in range(1, 11)
            )
            or self.initial_cache_empty is not True
        ):
            raise LiveEpochInvariantViolation("proof arm trace/prefix changed")
        expected = EXPECTED_TOTALS[self.scope.value]
        if (
            self.aggregate_work.to_document() != _derive_work(self.resolutions).to_document()
            or (self.aggregate_work.computed, self.aggregate_work.reused) != expected
        ):
            raise LiveEpochInvariantViolation("proof arm totals differ from frozen control")
        if self.scope is LiveEpochCacheScope.GLOBAL_CROSS_EPOCH_FACET_DAG:
            if (
                self.prefix_computes != EXPECTED_CROSS_PREFIX_COMPUTES
                or self.prefix_reuses != EXPECTED_CROSS_PREFIX_HITS
                or dict((name, (computed, reused)) for name, computed, reused
                        in self.aggregate_work.slot_counts)
                != EXPECTED_CROSS_KIND_COUNTS
            ):
                raise LiveEpochInvariantViolation("cross-epoch prefix/kind counts changed")
        if tuple(item.sequence_number for item in self.resolutions) != tuple(range(1, 111)):
            raise LiveEpochInvariantViolation("proof arm resolution sequence is not continuous")
        entry_by_id = {item.entry_id: item for item in self.entry_catalogue}
        binding_by_id = {item.binding_id: item for item in self.slice_bindings}
        if (
            len(entry_by_id) != len(self.entry_catalogue)
            or len(binding_by_id) != len(self.slice_bindings)
            or set(entry_by_id) != {item.entry_id for item in self.resolutions}
            or set(binding_by_id) != {item.slice_binding_id for item in self.resolutions}
        ):
            raise LiveEpochInvariantViolation("proof arm catalogues are duplicate, missing, or extra")
        expected_request_ids = tuple(
            receipt.request.request_id
            for execution in (self.first_epoch, self.final_epoch)
            for receipt in execution.request_receipts
            for _ in SLOT_ORDER
        )
        if tuple(item.request_id for item in self.resolutions) != expected_request_ids:
            raise LiveEpochInvariantViolation("proof arm resolutions escaped request ownership")
        if (
            self.first_epoch.resolution_ids
            != tuple(item.resolution_id for item in self.resolutions[:55])
            or self.final_epoch.resolution_ids
            != tuple(item.resolution_id for item in self.resolutions[55:])
        ):
            raise LiveEpochInvariantViolation("epoch resolution IDs differ from arm trace")
        if (
            self.first_epoch.pre_cache_state_id != self.resolutions[0].pre_cache_state_id
            or self.first_epoch.post_cache_state_id != self.resolutions[54].post_cache_state_id
            or self.final_epoch.pre_cache_state_id != self.resolutions[55].pre_cache_state_id
            or self.final_epoch.post_cache_state_id != self.resolutions[109].post_cache_state_id
        ):
            raise LiveEpochInvariantViolation("epoch cache endpoints differ from arm trace")
        expected_facet_kind = {
            temporal.H2TemporalProofSlot.U1: "ALL_ACTIVE_GROUND_ROWS_REWARD_CAPS_EXTERNAL_V1",
            temporal.H2TemporalProofSlot.U0: "ALL_ACTIVE_GROUND_ROWS_REWARD_CAPS_EXTERNAL_V1",
            temporal.H2TemporalProofSlot.P1: "ALL_ACTIVE_SELECTED_REALIZATIONS_REWARD_CAPS_EXTERNAL_V1",
            temporal.H2TemporalProofSlot.P0: "ALL_ACTIVE_SELECTED_REALIZATIONS_REWARD_CAPS_EXTERNAL_V1",
            temporal.H2TemporalProofSlot.C0: "POSITIVE_REACH_SELECTED_REALIZATIONS_EXTERNAL_V1",
            temporal.H2TemporalProofSlot.C1: "POSITIVE_REACH_SELECTED_REALIZATIONS_EXTERNAL_V1",
            temporal.H2TemporalProofSlot.D: "INITIAL_SUPPORT_DIRECT_REALIZATION_V1",
            temporal.H2TemporalProofSlot.E: "PARENT_DERIVED_NO_DIRECT_MODEL_READ_V1",
            temporal.H2TemporalProofSlot.F: "PARENT_DERIVED_NO_DIRECT_MODEL_READ_V1",
            temporal.H2TemporalProofSlot.G: "PARENT_DERIVED_NO_DIRECT_MODEL_READ_V1",
            temporal.H2TemporalProofSlot.R: "FULL_EPOCH_MODEL_ROOT_V1",
        }
        for resolution in self.resolutions:
            entry = entry_by_id.get(resolution.entry_id)
            binding = binding_by_id.get(resolution.slice_binding_id)
            if (
                entry is None or binding is None
                or entry.key.node_key_id != resolution.node_key_id
                or entry.key.slot is not resolution.slot
                or entry.result_semantics != _result_semantics(resolution.slot)
                or entry.key.model_slice_content_id != binding.content.content_id
                or binding.content.slot is not resolution.slot
                or binding.content.facet_kind != expected_facet_kind[resolution.slot]
                or binding.content.time_index != entry.key.time_index
                or binding.content.stage_assignment_id != entry.key.stage_assignment_id
                or binding.epoch is not resolution.epoch
                or binding.model_id
                != (
                    self.first_epoch.model_id
                    if resolution.epoch is LiveEpochName.FIRST
                    else self.final_epoch.model_id
                )
            ):
                raise LiveEpochInvariantViolation("resolution entry/slice binding is unresolved")
        parent_slots = {
            temporal.H2TemporalProofSlot.U1: (),
            temporal.H2TemporalProofSlot.U0: (temporal.H2TemporalProofSlot.U1,),
            temporal.H2TemporalProofSlot.P1: (),
            temporal.H2TemporalProofSlot.P0: (temporal.H2TemporalProofSlot.P1,),
            temporal.H2TemporalProofSlot.C0: (),
            temporal.H2TemporalProofSlot.C1: (temporal.H2TemporalProofSlot.C0,),
            temporal.H2TemporalProofSlot.D: (
                temporal.H2TemporalProofSlot.U0,
                temporal.H2TemporalProofSlot.P0,
                temporal.H2TemporalProofSlot.C0,
                temporal.H2TemporalProofSlot.C1,
            ),
            temporal.H2TemporalProofSlot.E: (temporal.H2TemporalProofSlot.D,),
            temporal.H2TemporalProofSlot.F: (temporal.H2TemporalProofSlot.D,),
            temporal.H2TemporalProofSlot.G: (
                temporal.H2TemporalProofSlot.C0,
                temporal.H2TemporalProofSlot.C1,
            ),
            temporal.H2TemporalProofSlot.R: LOWER_SLOT_ORDER,
        }
        receipts = self.first_epoch.request_receipts + self.final_epoch.request_receipts
        for request_index, receipt in enumerate(receipts):
            block = self.resolutions[11 * request_index:11 * (request_index + 1)]
            if (
                tuple(item.slot for item in block) != SLOT_ORDER
                or any(item.epoch is not receipt.request.epoch for item in block)
                or receipt.resolution_ids != tuple(item.resolution_id for item in block)
                or receipt.root_entry_id != block[-1].entry_id
                or entry_by_id[block[-1].entry_id].result_digest
                != _node_result_digest(temporal.H2TemporalProofSlot.R, receipt.audit_result)
            ):
                raise LiveEpochInvariantViolation("receipt does not bind its canonical eleven-node block")
            block_entries = {item.slot: entry_by_id[item.entry_id] for item in block}
            for item in block:
                if entry_by_id[item.entry_id].key.ordered_parent_entry_ids != tuple(
                    block_entries[parent].entry_id for parent in parent_slots[item.slot]
                ):
                    raise LiveEpochInvariantViolation("proof node parent slots/order changed")
        reset_indices = (
            set(range(0, 110, 11))
            if self.scope is LiveEpochCacheScope.REQUEST_RESET
            else ({0, 55} if self.scope is LiveEpochCacheScope.EPOCH_RESET_GLOBAL_DAG else {0})
        )
        cache: dict[str, str] = {}
        for index, resolution in enumerate(self.resolutions):
            if index in reset_indices:
                cache = {}
            if resolution.pre_cache_state_id != _cache_state_id(self.scope, cache):
                raise LiveEpochInvariantViolation("cache pre-state differs from exact replay")
            existing = cache.get(resolution.node_key_id)
            if resolution.outcome is LiveEpochResolutionOutcome.COMPUTED:
                if existing is not None:
                    raise LiveEpochInvariantViolation("computed outcome replaced an existing key")
                cache[resolution.node_key_id] = resolution.entry_id
            else:
                if existing != resolution.entry_id:
                    raise LiveEpochInvariantViolation("reuse outcome lacks its exact cached entry")
            if resolution.post_cache_state_id != _cache_state_id(self.scope, cache):
                raise LiveEpochInvariantViolation("cache post-state differs from exact replay")
        self.first_epoch.__post_init__()
        self.final_epoch.__post_init__()
        self.aggregate_work.__post_init__()
        for item in self.resolutions:
            item.__post_init__()
        for item in self.slice_bindings:
            item.__post_init__()
            item.content.__post_init__()
        for item in self.entry_catalogue:
            item.__post_init__()
            item.key.__post_init__()

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.live_epoch_proof_arm.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "scope": self.scope.value,
            "first_epoch": self.first_epoch.to_document(),
            "final_epoch": self.final_epoch.to_document(),
            "resolutions": [item.to_document() for item in self.resolutions],
            "slice_bindings": [item.to_document() for item in self.slice_bindings],
            "entry_catalogue": [item.to_document() for item in self.entry_catalogue],
            "aggregate_work": self.aggregate_work.to_document(),
            "prefix_computes": list(self.prefix_computes),
            "prefix_reuses": list(self.prefix_reuses),
            "initial_cache_empty": self.initial_cache_empty,
        }

    @property
    def arm_id(self) -> str:
        return _content_id("arm", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "arm_id": self.arm_id}


def _binding(
    epoch: LiveEpochName,
    build: Any,
    evidence_request: Any,
    evidence_bundle: Any,
    content: ModelSliceContentV1,
) -> ModelSliceBindingV1:
    return ModelSliceBindingV1(
        epoch, build.model.model_id, build.result_id, evidence_request.request_id,
        evidence_bundle.bundle_id, content,
    )


def _run_request(
    runtime: _Runtime,
    epoch: LiveEpochName,
    request: LiveEpochProofRequestV1,
    build: Any,
    rebase: Any,
    evidence_request: Any,
    evidence_bundle: Any,
    stage_maps_by_id: Mapping[str, Mapping[str, str]],
) -> LiveEpochProofReceiptV1:
    model = build.model
    thresholds = rebase.rebased_thresholds
    plan = request.contingent_plan
    active_cells, realizations, stage_maps, state_to_cell = audit._validate_inputs(
        model, thresholds, plan
    )
    if tuple(stage_maps[index] for index in (0, 1)) != tuple(
        stage_maps_by_id[item] for item in request.stage_assignment_ids
    ):
        raise LiveEpochInvariantViolation("request stage assignment mapping changed")
    start = len(runtime.resolutions)
    entries: dict[temporal.H2TemporalProofSlot, LiveEpochProofNodeEntryV1] = {}
    values: dict[temporal.H2TemporalProofSlot, Any] = {}

    def resolve(
        slot: temporal.H2TemporalProofSlot,
        parents: tuple[temporal.H2TemporalProofSlot, ...],
        factory: Any,
        stage_id: str | None = None,
        stage_map: Mapping[str, str] | None = None,
        parent_value: Any | None = None,
    ) -> None:
        content = _slice_content(
            slot, model, thresholds, active_cells, realizations, state_to_cell,
            stage_map, stage_id, parent_value,
        )
        entries[slot], values[slot] = runtime.resolve(
            epoch, request,
            _binding(epoch, build, evidence_request, evidence_bundle, content),
            tuple(entries[item] for item in parents), thresholds, factory,
        )

    resolve(
        temporal.H2TemporalProofSlot.U1, (),
        lambda: temporal._compute_u_stage(model, thresholds, active_cells, 1, None),
    )
    resolve(
        temporal.H2TemporalProofSlot.U0, (temporal.H2TemporalProofSlot.U1,),
        lambda: temporal._compute_u_stage(
            model, thresholds, active_cells, 0, values[temporal.H2TemporalProofSlot.U1]
        ),
    )
    resolve(
        temporal.H2TemporalProofSlot.P1, (),
        lambda: temporal._compute_p_stage(
            model, thresholds, active_cells, realizations, stage_maps[1], 1, None
        ),
        request.stage_assignment_ids[1], stage_maps[1],
    )
    resolve(
        temporal.H2TemporalProofSlot.P0, (temporal.H2TemporalProofSlot.P1,),
        lambda: temporal._compute_p_stage(
            model, thresholds, active_cells, realizations, stage_maps[0], 0,
            values[temporal.H2TemporalProofSlot.P1],
        ),
        request.stage_assignment_ids[0], stage_maps[0],
    )
    resolve(
        temporal.H2TemporalProofSlot.C0, (),
        lambda: temporal._compute_c_stage(
            model, thresholds, active_cells, realizations, state_to_cell,
            stage_maps[0], 0, None,
        ),
        request.stage_assignment_ids[0], stage_maps[0],
    )
    resolve(
        temporal.H2TemporalProofSlot.C1, (temporal.H2TemporalProofSlot.C0,),
        lambda: temporal._compute_c_stage(
            model, thresholds, active_cells, realizations, state_to_cell,
            stage_maps[1], 1, values[temporal.H2TemporalProofSlot.C0],
        ),
        request.stage_assignment_ids[1], stage_maps[1],
        values[temporal.H2TemporalProofSlot.C0],
    )
    resolve(
        temporal.H2TemporalProofSlot.D,
        (
            temporal.H2TemporalProofSlot.U0,
            temporal.H2TemporalProofSlot.P0,
            temporal.H2TemporalProofSlot.C0,
            temporal.H2TemporalProofSlot.C1,
        ),
        lambda: temporal._compute_d(
            model, thresholds, active_cells, realizations, stage_maps, state_to_cell,
            values[temporal.H2TemporalProofSlot.U0],
            values[temporal.H2TemporalProofSlot.P1],
            values[temporal.H2TemporalProofSlot.P0],
            values[temporal.H2TemporalProofSlot.C0],
            values[temporal.H2TemporalProofSlot.C1],
        ),
        request.stage_assignment_ids[0], stage_maps[0],
    )
    resolve(
        temporal.H2TemporalProofSlot.E, (temporal.H2TemporalProofSlot.D,),
        lambda: temporal._NeutralE(
            tuple(
                item[-1] <= thresholds.normalized_regret_tolerance
                for item in values[temporal.H2TemporalProofSlot.D].support_metrics
            ),
            all(
                item[-1] <= thresholds.normalized_regret_tolerance
                for item in values[temporal.H2TemporalProofSlot.D].support_metrics
            ),
        ),
    )
    resolve(
        temporal.H2TemporalProofSlot.F, (temporal.H2TemporalProofSlot.D,),
        lambda: temporal._NeutralF(
            values[temporal.H2TemporalProofSlot.D].root_failure_upper
            <= thresholds.risk_tolerance
        ),
    )

    def compute_g() -> Any:
        rows = tuple(sorted(
            (*values[temporal.H2TemporalProofSlot.C0].rows,
             *values[temporal.H2TemporalProofSlot.C1].rows),
            key=lambda row: (row.time_index, row.cell_id, row.state_id, row.action_id),
        ))
        indices = tuple(
            index for index, row in enumerate(rows)
            if row.remaining_horizon > 1 and (
                row.reachable_external_continuation_mass_upper > 0
                or row.reachable_unknown_mass_upper > 0
            )
        )
        return temporal._NeutralG(indices, not indices)

    resolve(
        temporal.H2TemporalProofSlot.G,
        (temporal.H2TemporalProofSlot.C0, temporal.H2TemporalProofSlot.C1),
        compute_g,
    )
    resolve(
        temporal.H2TemporalProofSlot.R, LOWER_SLOT_ORDER,
        lambda: temporal._materialize_root(
            model, thresholds, plan,
            values[temporal.H2TemporalProofSlot.U1],
            values[temporal.H2TemporalProofSlot.U0],
            values[temporal.H2TemporalProofSlot.P1],
            values[temporal.H2TemporalProofSlot.P0],
            values[temporal.H2TemporalProofSlot.C0],
            values[temporal.H2TemporalProofSlot.C1],
            values[temporal.H2TemporalProofSlot.D],
            values[temporal.H2TemporalProofSlot.E],
            values[temporal.H2TemporalProofSlot.F],
            values[temporal.H2TemporalProofSlot.G],
        ),
    )
    current = tuple(runtime.resolutions[start:])
    if tuple(item.slot for item in current) != SLOT_ORDER:
        raise LiveEpochInvariantViolation("runtime did not resolve the eleven-slot graph")
    return LiveEpochProofReceiptV1(
        request, tuple(item.resolution_id for item in current),
        entries[temporal.H2TemporalProofSlot.R].entry_id,
        values[temporal.H2TemporalProofSlot.R],
    )


def _semantic_stage_key(
    model: QueryScopedPartialRAPMV3,
    assignments: tuple[Any, ...],
) -> tuple[int, ...]:
    actions = {item.semantic_action_id: item for item in model.semantic_actions}
    cells = tuple(
        item.cell_id for item in sorted(
            (item for item in model.cells if item.planning_kind is PlanningKind.ACTIVE),
            key=lambda item: (item.coordinate_values, item.member_state_ids),
        )
    )
    mapping = {item.cell_id: item.semantic_action_id for item in assignments}
    return tuple(int(value) for cell_id in cells for value in actions[mapping[cell_id]].label_values)


def _run_epoch(
    runtime: _Runtime,
    epoch: LiveEpochName,
    observation_log: ObservationLogManifestV1,
    semantics_profile: DeterministicObservationProfileV1,
    observation_authority: PreregisteredObservationAuthorityV1,
    build: Any,
    rebase: Any,
    evidence_request: Any,
    evidence_bundle: Any,
) -> LiveEpochProofExecutionV1:
    model = build.model
    thresholds = rebase.rebased_thresholds
    _, domains = planner._planner_context(
        observation_log, semantics_profile, observation_authority, model, thresholds
    )
    assignments = tuple(sorted(
        planner._stage_assignments(domains),
        key=lambda item: (_semantic_stage_key(model, item), tuple(row.semantic_action_id for row in item)),
    ))
    if len(assignments) != 2:
        raise LiveEpochInvariantViolation("registered epoch must expose two stage assignments")
    stage_artifacts = tuple(
        temporal.H2TemporalStageAssignmentV1(
            index,
            tuple(
                (
                    row.cell_id,
                    row.semantic_action_id,
                    tuple(int(value) for value in next(
                        action.label_values for action in model.semantic_actions
                        if action.semantic_action_id == row.semantic_action_id
                    )),
                )
                for row in stage
            ),
        )
        for index, stage in enumerate(assignments)
    )
    stage_maps_by_id = {
        artifact.stage_assignment_id: {
            row.cell_id: row.semantic_action_id for row in stage
        }
        for artifact, stage in zip(stage_artifacts, assignments)
    }
    plans: list[tuple[str, tuple[str, str], FrozenContingentAbstractPlanV1]] = []
    for code, bits in zip(GRAY_CODES, GRAY_BITS):
        plan = FrozenContingentAbstractPlanV1(
            model.model_id,
            2,
            tuple(
                ContingentPlanStageV1(time_index, assignments[bit])
                for time_index, bit in enumerate(bits)
            ),
        )
        plans.append((
            code,
            tuple(stage_artifacts[bit].stage_assignment_id for bit in bits),
            plan,
        ))
    if runtime.scope is LiveEpochCacheScope.REQUEST_RESET:
        runtime.reset()
    start = len(runtime.resolutions)
    pre_cache = _cache_state_id(runtime.scope, runtime.cache)
    receipts: list[LiveEpochProofReceiptV1] = []
    for index, (code, stage_ids, plan) in enumerate(plans, start=1):
        if runtime.scope is LiveEpochCacheScope.REQUEST_RESET:
            runtime.reset()
        request = LiveEpochProofRequestV1(
            epoch, index, temporal.H2TemporalProofRole.CANDIDATE_RANKING_AUDIT,
            code, model.model_id, thresholds.thresholds_id, plan, stage_ids, None,
        )
        receipts.append(_run_request(
            runtime, epoch, request, build, rebase, evidence_request,
            evidence_bundle, stage_maps_by_id,
        ))
    plan_by_id = {plan.plan_id: plan for _, _, plan in plans}
    summaries = tuple(sorted(
        (
            planner._candidate_summary(
                thresholds, receipt.request.contingent_plan, receipt.audit_result
            )
            for receipt in receipts
        ),
        key=lambda item: item.contingent_plan_id,
    ))
    selection_mode, selected_summary, semantic_key = multistep._select_with_semantic_tie_break(
        model, summaries, plan_by_id
    )
    selected_plan = plan_by_id[selected_summary.contingent_plan_id]
    proposal = MultiStepPlanProposalV1(
        build.result_id, model.model_id, rebase.rebase_id, thresholds.thresholds_id,
        domains, 2, 4, summaries, selection_mode, selected_plan,
        "NUMERIC_GATE_THEN_SEMANTIC_LABEL_LEXICOGRAPHIC_V1", semantic_key, 4,
    )
    selected_code, selected_stage_ids, _ = next(
        item for item in plans if item[2].plan_id == selected_plan.plan_id
    )
    if runtime.scope is LiveEpochCacheScope.REQUEST_RESET:
        runtime.reset()
    selected_request = LiveEpochProofRequestV1(
        epoch, 5,
        temporal.H2TemporalProofRole.INDEPENDENT_SELECTED_PLAN_CERTIFICATE,
        selected_code, model.model_id, thresholds.thresholds_id, selected_plan,
        selected_stage_ids, proposal.result_id,
    )
    selected_receipt = _run_request(
        runtime, epoch, selected_request, build, rebase, evidence_request,
        evidence_bundle, stage_maps_by_id,
    )
    receipts.append(selected_receipt)
    selected_audit = MultiStepPlanAuditV1(
        build.result_id, model.model_id, evidence_request.request_id,
        evidence_bundle.bundle_id, rebase.rebase_id, proposal.result_id,
        selected_plan.plan_id, selected_receipt.audit_result,
    )
    current = tuple(runtime.resolutions[start:])
    execution = LiveEpochProofExecutionV1(
        epoch, model.model_id, thresholds.thresholds_id, tuple(receipts), proposal,
        selected_audit, tuple(item.resolution_id for item in current),
        _derive_work(current), pre_cache, _cache_state_id(runtime.scope, runtime.cache),
    )
    return execution


def _freeze_arm(
    runtime: _Runtime,
    first: LiveEpochProofExecutionV1,
    final: LiveEpochProofExecutionV1,
) -> LiveEpochProofArmV1:
    resolutions = tuple(runtime.resolutions)
    return LiveEpochProofArmV1(
        runtime.scope, first, final, resolutions,
        tuple(sorted(runtime.bindings.values(), key=lambda item: item.binding_id)),
        tuple(sorted(runtime.entries.values(), key=lambda item: item.entry_id)),
        _derive_work(resolutions),
        tuple(
            sum(item.outcome is LiveEpochResolutionOutcome.COMPUTED
                for item in resolutions[:11 * index])
            for index in range(1, 11)
        ),
        tuple(
            sum(item.outcome is LiveEpochResolutionOutcome.REUSED
                for item in resolutions[:11 * index])
            for index in range(1, 11)
        ),
    )


@dataclass(frozen=True, slots=True)
class LiveModelEpochDeltaV1:
    first_model_id: str
    final_model_id: str
    round_two_request_id: str
    round_two_bundle_id: str
    changed_ground_row_ids: tuple[str, ...]
    unchanged_ground_row_ids: tuple[str, ...]
    changed_realization_pairs: tuple[tuple[str, str], ...]
    direct_changed_slots: tuple[str, ...]
    affected_descendant_slots: tuple[str, ...]
    reusable_slots: tuple[str, ...]
    first_observed_count: int
    first_missing_count: int
    final_observed_count: int
    final_missing_count: int

    def __post_init__(self) -> None:
        for value in (
            self.first_model_id, self.final_model_id, self.round_two_request_id,
            self.round_two_bundle_id, *self.changed_ground_row_ids,
            *self.unchanged_ground_row_ids,
            *(value for pair in self.changed_realization_pairs for value in pair),
        ):
            _cid(value, "epoch delta identity")
        if (
            self.first_model_id != EXPECTED_FIRST_MODEL_ID
            or self.final_model_id != EXPECTED_FINAL_MODEL_ID
            or self.round_two_request_id != EXPECTED_ROUND_TWO_REQUEST_ID
            or type(self.changed_ground_row_ids) is not tuple
            or len(self.changed_ground_row_ids) != 9
            or len(self.unchanged_ground_row_ids) != 11
            or set(self.changed_ground_row_ids) & set(self.unchanged_ground_row_ids)
            or len(self.changed_realization_pairs) != 6
            or self.direct_changed_slots != ("U1", "U0", "P1", "P0", "C1")
            or self.affected_descendant_slots != ("D", "E", "F", "G", "R")
            or self.reusable_slots != ("C0",)
            or (self.first_observed_count, self.first_missing_count,
                self.final_observed_count, self.final_missing_count) != (11, 9, 20, 0)
        ):
            raise LiveEpochInvariantViolation("registered epoch delta/closure changed")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.live_model_epoch_delta.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "first_model_id": self.first_model_id,
            "final_model_id": self.final_model_id,
            "round_two_request_id": self.round_two_request_id,
            "round_two_bundle_id": self.round_two_bundle_id,
            "changed_ground_row_ids": list(self.changed_ground_row_ids),
            "unchanged_ground_row_ids": list(self.unchanged_ground_row_ids),
            "changed_realization_pairs": [
                {"state_id": state_id, "semantic_action_id": action_id}
                for state_id, action_id in self.changed_realization_pairs
            ],
            "direct_changed_slots": list(self.direct_changed_slots),
            "affected_descendant_slots": list(self.affected_descendant_slots),
            "reusable_slots": list(self.reusable_slots),
            "first_observed_count": self.first_observed_count,
            "first_missing_count": self.first_missing_count,
            "final_observed_count": self.final_observed_count,
            "final_missing_count": self.final_missing_count,
        }

    @property
    def delta_id(self) -> str:
        return _content_id("delta", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "delta_id": self.delta_id}


@dataclass(frozen=True, slots=True)
class LiveEpochInvalidationManifestV1:
    delta_id: str
    direct_changed_slots: tuple[str, ...]
    affected_descendant_slots: tuple[str, ...]
    reusable_slots: tuple[str, ...]
    matched_request_count: int = 5
    reusable_distinct_entry_count: int = 2
    output_equality_cannot_bypass_parent_change: bool = True

    def __post_init__(self) -> None:
        _cid(self.delta_id, "invalidation manifest delta")
        if (
            self.direct_changed_slots != ("U1", "U0", "P1", "P0", "C1")
            or self.affected_descendant_slots != ("D", "E", "F", "G", "R")
            or self.reusable_slots != ("C0",)
            or self.matched_request_count != 5
            or self.reusable_distinct_entry_count != 2
            or self.output_equality_cannot_bypass_parent_change is not True
        ):
            raise LiveEpochInvariantViolation("invalidation manifest closure changed")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.live_epoch_invalidation_manifest.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "delta_id": self.delta_id,
            "direct_changed_slots": list(self.direct_changed_slots),
            "affected_descendant_slots": list(self.affected_descendant_slots),
            "reusable_slots": list(self.reusable_slots),
            "matched_request_count": self.matched_request_count,
            "reusable_distinct_entry_count": self.reusable_distinct_entry_count,
            "output_equality_cannot_bypass_parent_change": self.output_equality_cannot_bypass_parent_change,
        }

    @property
    def manifest_id(self) -> str:
        return _content_id("invalidation", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "manifest_id": self.manifest_id}


def _derive_delta(source: MultiStepQueryRefinementResultV1) -> LiveModelEpochDeltaV1:
    first = source.first_overlay_build.model
    final = source.final_overlay_build.model
    first_rows = {item.ground_row_id: item for item in first.ground_rows}
    final_rows = {item.ground_row_id: item for item in final.ground_rows}
    if set(first_rows) != set(final_rows):
        raise LiveEpochInvariantViolation("epoch transition changed ground-row identities")
    changed = tuple(sorted(
        row_id for row_id in first_rows
        if first_rows[row_id].to_document() != final_rows[row_id].to_document()
    ))
    unchanged = tuple(sorted(set(first_rows) - set(changed)))
    first_real = {
        (item.state_id, item.semantic_action_id): item.to_document()
        for item in first.semantic_realizations
    }
    final_real = {
        (item.state_id, item.semantic_action_id): item.to_document()
        for item in final.semantic_realizations
    }
    if set(first_real) != set(final_real):
        raise LiveEpochInvariantViolation("epoch transition changed realization identities")
    changed_real = tuple(sorted(
        key for key in first_real if first_real[key] != final_real[key]
    ))
    structural_names = (
        "cells", "semantic_actions", "concretizer_rows", "reward_feature_caps",
        "external_boundary_id", "semantics_profile_id", "semantics_horizon_cap",
    )
    if any(getattr(first, name) != getattr(final, name) for name in structural_names):
        raise LiveEpochInvariantViolation("epoch transition changed a non-delta structural facet")
    if changed != tuple(sorted(source.round_two_request.requested_ground_row_ids)):
        raise LiveEpochInvariantViolation("derived row delta differs from authorized request")
    if any(
        first_rows[row_id].status is not AmbiguityRowStatus.MISSING_VACUOUS
        or final_rows[row_id].status is not AmbiguityRowStatus.OBSERVED_SINGLETON
        for row_id in changed
    ):
        raise LiveEpochInvariantViolation("row delta is not missing-to-observed")
    return LiveModelEpochDeltaV1(
        first.model_id, final.model_id, source.round_two_request.request_id,
        source.round_two_bundle.bundle_id, changed, unchanged, changed_real,
        ("U1", "U0", "P1", "P0", "C1"), ("D", "E", "F", "G", "R"),
        ("C0",), len(first.coverage.observed_ground_row_ids),
        len(first.coverage.missing_ground_row_ids),
        len(final.coverage.observed_ground_row_ids),
        len(final.coverage.missing_ground_row_ids),
    )


@dataclass(frozen=True, slots=True)
class LiveOrderingEventV1:
    sequence_number: int
    event_kind: str
    artifact_id: str
    cumulative_transition_calls: int
    cumulative_boundary_catalogue_calls: int

    def __post_init__(self) -> None:
        if (
            type(self.sequence_number) is not int or self.sequence_number < 1
            or not self.event_kind or type(self.event_kind) is not str
            or type(self.cumulative_transition_calls) is not int
            or self.cumulative_transition_calls < 0
            or type(self.cumulative_boundary_catalogue_calls) is not int
            or self.cumulative_boundary_catalogue_calls < 0
        ):
            raise LiveEpochInvariantViolation("ordering event shape changed")
        _cid(self.artifact_id, "ordering event artifact")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.live_epoch_ordering_event.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "sequence_number": self.sequence_number,
            "event_kind": self.event_kind,
            "artifact_id": self.artifact_id,
            "cumulative_transition_calls": self.cumulative_transition_calls,
            "cumulative_boundary_catalogue_calls": self.cumulative_boundary_catalogue_calls,
        }

    @property
    def event_id(self) -> str:
        return _content_id("event", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "event_id": self.event_id}


@dataclass(frozen=True, slots=True)
class LiveOrderingProtocolV1:
    events: tuple[LiveOrderingEventV1, ...]
    first_selected_root_precedes_round_two_request: bool = True
    round_two_request_precedes_round_two_evidence: bool = True
    final_epoch_follows_round_two_evidence: bool = True

    def __post_init__(self) -> None:
        expected_kinds = (
            "BASE_FAILURE_CHAIN_VERIFIED",
            "ROUND_ONE_REQUEST_FROZEN",
            "ROUND_ONE_EVIDENCE_AND_BOUNDARY_FROZEN",
            "FIRST_OVERLAY_EPOCH_FROZEN",
            "FIRST_CANDIDATE_DAG_AND_PROPOSAL_FROZEN",
            "FIRST_INDEPENDENT_SELECTED_FAILURE_FROZEN",
            "ROUND_TWO_REQUEST_DERIVED_FROM_FIRST_ROOT",
            "ROUND_TWO_NINE_ROWS_ACQUIRED",
            "FINAL_OVERLAY_EPOCH_FROZEN",
            "EXACT_MODEL_EPOCH_DELTA_FROZEN",
            "FINAL_CANDIDATE_DAG_AND_PROPOSAL_FROZEN",
            "FINAL_INDEPENDENT_SELECTED_CERTIFICATE_FROZEN",
        )
        if (
            type(self.events) is not tuple
            or len(self.events) != len(expected_kinds)
            or tuple(item.sequence_number for item in self.events)
            != tuple(range(1, len(expected_kinds) + 1))
            or tuple(item.event_kind for item in self.events) != expected_kinds
            or self.first_selected_root_precedes_round_two_request is not True
            or self.round_two_request_precedes_round_two_evidence is not True
            or self.final_epoch_follows_round_two_evidence is not True
            or tuple(item.cumulative_transition_calls for item in self.events)
            != (0, 0, 4, 4, 4, 4, 4, 13, 13, 13, 13, 13)
            or tuple(item.cumulative_boundary_catalogue_calls for item in self.events)
            != (0, 0, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3)
        ):
            raise LiveEpochInvariantViolation("live source-order protocol changed")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.live_epoch_ordering_protocol.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "events": [item.to_document() for item in self.events],
            "first_selected_root_precedes_round_two_request": self.first_selected_root_precedes_round_two_request,
            "round_two_request_precedes_round_two_evidence": self.round_two_request_precedes_round_two_evidence,
            "final_epoch_follows_round_two_evidence": self.final_epoch_follows_round_two_evidence,
        }

    @property
    def protocol_id(self) -> str:
        return _content_id("ordering", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "protocol_id": self.protocol_id}


_RESULT_AUTHORITY = object()


@dataclass(frozen=True, slots=True)
class LiveQueryLocalEpochInvalidationResultV1:
    semantics: LiveEpochProofSemanticsV1
    live_multistep_result: MultiStepQueryRefinementResultV1
    ordering_protocol: LiveOrderingProtocolV1
    epoch_delta: LiveModelEpochDeltaV1
    invalidation_manifest: LiveEpochInvalidationManifestV1
    request_reset_arm: LiveEpochProofArmV1
    epoch_reset_global_arm: LiveEpochProofArmV1
    global_cross_epoch_facet_arm: LiveEpochProofArmV1
    avoided_cross_epoch_constructions: int
    _authority: object = field(repr=False, compare=False)
    _instance_mint: RuntimeAuthorityMintV1 | None = field(
        default=None, repr=False, compare=False
    )
    status: str = SUCCESS_STATUS
    registered_h2_live_query_local_epoch_invalidation_claimed: bool = True
    live_closed_loop_claimed: bool = True
    semantic_policy_change_claimed: bool = False
    generic_changed_model_incremental_proof_claimed: bool = False
    generic_h_gt_1_recurrence_claimed: bool = False
    persistent_cache_claimed: bool = False
    cross_query_cache_claimed: bool = False
    sample_reduction_claimed: bool = False
    sample_efficiency_claimed: bool = False
    total_work_reduction_claimed: bool = False
    workload_economics_claimed: bool = False
    learned_dynamics_claimed: bool = False
    coordinate_invention_claimed: bool = False
    official_execution_allowed: bool = False
    official_scalar_cost: None = None
    official_N_break_even: None = None
    workload_economics_gate: str = "WORKLOAD_ECONOMICS_GATE_NOT_RUN"
    counter_completeness_gate: str = "COUNTER_COMPLETENESS_GATE_NOT_RUN"
    sample_efficiency_gate: str = "SAMPLE_EFFICIENCY_GATE_NOT_RUN"
    sample_efficiency_gate_blocks_mainline: bool = False

    def __post_init__(self) -> None:
        if self._authority is not _RESULT_AUTHORITY:
            raise LiveEpochInvariantViolation("result was not minted by the live runner")
        if self._instance_mint is not None:
            try:
                self._instance_mint.validate_construction(
                    self, issuer=_RESULT_AUTHORITY,
                    fingerprint=runtime_authority_fingerprint_v1(self),
                )
            except ValueError as error:
                raise LiveEpochInvariantViolation("result was copied or replaced") from error
        if (
            type(self.semantics) is not LiveEpochProofSemanticsV1
            or type(self.live_multistep_result) is not MultiStepQueryRefinementResultV1
            or type(self.ordering_protocol) is not LiveOrderingProtocolV1
            or type(self.epoch_delta) is not LiveModelEpochDeltaV1
            or type(self.invalidation_manifest) is not LiveEpochInvalidationManifestV1
            or self.invalidation_manifest.delta_id != self.epoch_delta.delta_id
            or type(self.request_reset_arm) is not LiveEpochProofArmV1
            or self.request_reset_arm.scope is not LiveEpochCacheScope.REQUEST_RESET
            or type(self.epoch_reset_global_arm) is not LiveEpochProofArmV1
            or self.epoch_reset_global_arm.scope is not LiveEpochCacheScope.EPOCH_RESET_GLOBAL_DAG
            or type(self.global_cross_epoch_facet_arm) is not LiveEpochProofArmV1
            or self.global_cross_epoch_facet_arm.scope
            is not LiveEpochCacheScope.GLOBAL_CROSS_EPOCH_FACET_DAG
            or self.live_multistep_result.result_id != EXPECTED_MULTISTEP_RESULT_ID
            or self.avoided_cross_epoch_constructions != 2
            or self.epoch_reset_global_arm.aggregate_work.computed
            - self.global_cross_epoch_facet_arm.aggregate_work.computed != 2
            or self.status != SUCCESS_STATUS
            or self.registered_h2_live_query_local_epoch_invalidation_claimed is not True
            or self.live_closed_loop_claimed is not True
            or any((
                self.semantic_policy_change_claimed,
                self.generic_changed_model_incremental_proof_claimed,
                self.generic_h_gt_1_recurrence_claimed,
                self.persistent_cache_claimed,
                self.cross_query_cache_claimed,
                self.sample_reduction_claimed,
                self.sample_efficiency_claimed,
                self.total_work_reduction_claimed,
                self.workload_economics_claimed,
                self.learned_dynamics_claimed,
                self.coordinate_invention_claimed,
                self.official_execution_allowed,
            ))
            or self.official_scalar_cost is not None
            or self.official_N_break_even is not None
            or self.workload_economics_gate != "WORKLOAD_ECONOMICS_GATE_NOT_RUN"
            or self.counter_completeness_gate != "COUNTER_COMPLETENESS_GATE_NOT_RUN"
            or self.sample_efficiency_gate != "SAMPLE_EFFICIENCY_GATE_NOT_RUN"
            or self.sample_efficiency_gate_blocks_mainline is not False
        ):
            raise LiveEpochInvariantViolation("result identity/claim/Gate locks changed")
        first = self.global_cross_epoch_facet_arm.first_epoch
        final = self.global_cross_epoch_facet_arm.final_epoch
        if (
            first.plan_proposal.result_id != EXPECTED_FIRST_PROPOSAL_ID
            or final.selected_plan_audit.result_id != EXPECTED_FINAL_AUDIT_ID
            or first.plan_proposal.selected_semantic_tie_break_key
            != final.plan_proposal.selected_semantic_tie_break_key
            or first.plan_proposal.selected_semantic_tie_break_key
            != (0, 1, 0, 1, 0, 1, 0, 1)
            or first.request_receipts[-1].audit_result.outcome
            is not PartialAuditOutcome.FAILED_PROOF_FRONTIER
            or final.request_receipts[-1].audit_result.outcome
            is not PartialAuditOutcome.CERTIFIED_FIXED_PLAN
        ):
            raise LiveEpochInvariantViolation("live first/final replan-recertify result changed")
        source = self.live_multistep_result
        if self.epoch_delta.to_document() != _derive_delta(source).to_document():
            raise LiveEpochInvariantViolation("epoch delta is not derivable from immutable models")
        arms = (
            self.request_reset_arm,
            self.epoch_reset_global_arm,
            self.global_cross_epoch_facet_arm,
        )
        for arm in arms:
            if (
                arm.first_epoch.plan_proposal.to_document()
                != source.first_plan_proposal.to_document()
                or arm.first_epoch.selected_plan_audit.to_document()
                != source.first_plan_audit.to_document()
                or arm.final_epoch.plan_proposal.to_document()
                != source.final_plan_proposal.to_document()
                or arm.final_epoch.selected_plan_audit.to_document()
                != source.final_plan_audit.to_document()
                or tuple(item.audit_result.to_document() for item in arm.first_epoch.request_receipts)
                != tuple(item.audit_result.to_document() for item in first.request_receipts)
                or tuple(item.audit_result.to_document() for item in arm.final_epoch.request_receipts)
                != tuple(item.audit_result.to_document() for item in final.request_receipts)
            ):
                raise LiveEpochInvariantViolation("matched control arms changed planning/audit semantics")
            expected_binding = {
                LiveEpochName.FIRST: (
                    source.first_overlay_build.model.model_id,
                    source.first_overlay_build.result_id,
                    source.round_one_request.request_id,
                    source.round_one_bundle.bundle_id,
                ),
                LiveEpochName.FINAL: (
                    source.final_overlay_build.model.model_id,
                    source.final_overlay_build.result_id,
                    source.round_two_request.request_id,
                    source.round_two_bundle.bundle_id,
                ),
            }
            for binding in arm.slice_bindings:
                if (
                    binding.model_id,
                    binding.overlay_build_result_id,
                    binding.evidence_request_id,
                    binding.evidence_bundle_id,
                ) != expected_binding[binding.epoch]:
                    raise LiveEpochInvariantViolation("slice provenance escaped its source epoch")
            entry_by_id = {item.entry_id: item for item in arm.entry_catalogue}
            for epoch_offset, execution, current_thresholds in (
                (0, arm.first_epoch, source.first_threshold_rebase.rebased_thresholds),
                (55, arm.final_epoch, source.final_threshold_rebase.rebased_thresholds),
            ):
                for request_offset, receipt in enumerate(execution.request_receipts):
                    block = arm.resolutions[
                        epoch_offset + 11 * request_offset:
                        epoch_offset + 11 * (request_offset + 1)
                    ]
                    for resolution in block:
                        key = entry_by_id[resolution.entry_id].key
                        if (
                            key.semantics_id != self.semantics.semantics_id
                            or key.identity_terms
                            != _identity_terms(resolution.slot, current_thresholds, receipt.request)
                        ):
                            raise LiveEpochInvariantViolation("node key escaped semantics/request facets")
        linked_ids = tuple(item.artifact_id for item in self.ordering_protocol.events[1:])
        if linked_ids != (
            source.round_one_request.request_id,
            source.boundary_expansion.expansion_id,
            source.first_overlay_build.model.model_id,
            first.plan_proposal.result_id,
            first.selected_plan_audit.result_id,
            source.round_two_request.request_id,
            source.round_two_bundle.bundle_id,
            source.final_overlay_build.model.model_id,
            self.epoch_delta.delta_id,
            final.plan_proposal.result_id,
            final.selected_plan_audit.result_id,
        ):
            raise LiveEpochInvariantViolation("ordering events do not bind the live artifacts")
        if self.ordering_protocol.events[0].artifact_id != source.round_one_request.frontier_id:
            raise LiveEpochInvariantViolation("base failure event does not bind the source frontier")
        first_entries = {
            (receipt.request.schedule_code, receipt.request.role.value, resolution.slot.value):
            resolution.entry_id
            for receipt in first.request_receipts
            for resolution in self.global_cross_epoch_facet_arm.resolutions[
                (receipt.request.request_index - 1) * 11:
                receipt.request.request_index * 11
            ]
        }
        final_offset = 55
        final_entries = {
            (receipt.request.schedule_code, receipt.request.role.value, resolution.slot.value):
            resolution.entry_id
            for receipt in final.request_receipts
            for resolution in self.global_cross_epoch_facet_arm.resolutions[
                final_offset + (receipt.request.request_index - 1) * 11:
                final_offset + receipt.request.request_index * 11
            ]
        }
        shared_slots = {
            key[2] for key in set(first_entries) & set(final_entries)
            if first_entries[key] == final_entries[key]
        }
        if shared_slots != {"C0"}:
            raise LiveEpochInvariantViolation("cross-epoch reuse escaped the exact C0 slice")
        self.semantics.__post_init__()
        self.live_multistep_result.__post_init__()
        self.ordering_protocol.__post_init__()
        for item in self.ordering_protocol.events:
            item.__post_init__()
        self.epoch_delta.__post_init__()
        self.invalidation_manifest.__post_init__()
        self.request_reset_arm.__post_init__()
        self.epoch_reset_global_arm.__post_init__()
        self.global_cross_epoch_facet_arm.__post_init__()
        if (
            self.semantics.semantics_id != EXPECTED_SEMANTICS_ID
            or self.ordering_protocol.protocol_id != EXPECTED_ORDERING_PROTOCOL_ID
            or self.epoch_delta.delta_id != EXPECTED_EPOCH_DELTA_ID
            or self.invalidation_manifest.manifest_id
            != EXPECTED_INVALIDATION_MANIFEST_ID
            or self.request_reset_arm.arm_id != EXPECTED_REQUEST_RESET_ARM_ID
            or self.epoch_reset_global_arm.arm_id != EXPECTED_EPOCH_RESET_ARM_ID
            or self.global_cross_epoch_facet_arm.arm_id != EXPECTED_CROSS_EPOCH_ARM_ID
            or first.execution_id != EXPECTED_FIRST_LIVE_EXECUTION_ID
            or final.execution_id != EXPECTED_FINAL_LIVE_EXECUTION_ID
            or final.post_cache_state_id != EXPECTED_FINAL_CROSS_CACHE_STATE_ID
            or self.result_id != EXPECTED_LIVE_RESULT_ID
        ):
            raise LiveEpochInvariantViolation("canonical V0-053 identities changed")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.live_query_local_epoch_invalidation_result.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "semantics": self.semantics.to_document(),
            "live_multistep_result": self.live_multistep_result.to_document(),
            "ordering_protocol": self.ordering_protocol.to_document(),
            "epoch_delta": self.epoch_delta.to_document(),
            "invalidation_manifest": self.invalidation_manifest.to_document(),
            "request_reset_arm": self.request_reset_arm.to_document(),
            "epoch_reset_global_arm": self.epoch_reset_global_arm.to_document(),
            "global_cross_epoch_facet_arm": self.global_cross_epoch_facet_arm.to_document(),
            "avoided_cross_epoch_constructions": self.avoided_cross_epoch_constructions,
            "status": self.status,
            "registered_h2_live_query_local_epoch_invalidation_claimed": self.registered_h2_live_query_local_epoch_invalidation_claimed,
            "live_closed_loop_claimed": self.live_closed_loop_claimed,
            "semantic_policy_change_claimed": self.semantic_policy_change_claimed,
            "generic_changed_model_incremental_proof_claimed": self.generic_changed_model_incremental_proof_claimed,
            "generic_h_gt_1_recurrence_claimed": self.generic_h_gt_1_recurrence_claimed,
            "persistent_cache_claimed": self.persistent_cache_claimed,
            "cross_query_cache_claimed": self.cross_query_cache_claimed,
            "sample_reduction_claimed": self.sample_reduction_claimed,
            "sample_efficiency_claimed": self.sample_efficiency_claimed,
            "total_work_reduction_claimed": self.total_work_reduction_claimed,
            "workload_economics_claimed": self.workload_economics_claimed,
            "learned_dynamics_claimed": self.learned_dynamics_claimed,
            "coordinate_invention_claimed": self.coordinate_invention_claimed,
            "official_execution_allowed": self.official_execution_allowed,
            "official_scalar_cost": self.official_scalar_cost,
            "official_N_break_even": self.official_N_break_even,
            "workload_economics_gate": self.workload_economics_gate,
            "counter_completeness_gate": self.counter_completeness_gate,
            "sample_efficiency_gate": self.sample_efficiency_gate,
            "sample_efficiency_gate_blocks_mainline": self.sample_efficiency_gate_blocks_mainline,
        }

    @property
    def result_id(self) -> str:
        return _content_id("result", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "result_id": self.result_id}


def require_live_query_local_epoch_invalidation_result_v1(
    result: LiveQueryLocalEpochInvalidationResultV1,
) -> LiveQueryLocalEpochInvalidationResultV1:
    if type(result) is not LiveQueryLocalEpochInvalidationResultV1:
        raise LiveEpochInvariantViolation("live result exact type is required")
    try:
        require_runtime_authority_v1(result, issuer=_RESULT_AUTHORITY)
    except ValueError as error:
        raise LiveEpochInvariantViolation("live result lacks owner-bound authority") from error
    result.__post_init__()
    return result


def _event(
    events: list[LiveOrderingEventV1],
    kind: str,
    artifact_id: str,
    transitions: int,
    catalogues: int,
) -> None:
    events.append(LiveOrderingEventV1(
        len(events) + 1, kind, artifact_id, transitions, catalogues
    ))


def _telemetry(
    base_model: Any,
    first_build: Any,
    final_build: Any,
    bundle_one: Any,
    bundle_two: Any,
    boundary: Any,
    proposal_one: MultiStepPlanProposalV1,
    proposal_two: MultiStepPlanProposalV1,
) -> MultiStepRefinementTelemetryV1:
    return MultiStepRefinementTelemetryV1(
        len(base_model.coverage.observed_ground_row_ids),
        len(base_model.coverage.missing_ground_row_ids),
        bundle_one.exact_kernel_query_count,
        boundary.action_catalogue_query_count,
        len(first_build.model.coverage.observed_ground_row_ids),
        len(first_build.model.coverage.missing_ground_row_ids),
        bundle_two.exact_kernel_query_count,
        len(final_build.model.coverage.observed_ground_row_ids),
        len(final_build.model.coverage.missing_ground_row_ids),
        bundle_one.exact_kernel_query_count + bundle_two.exact_kernel_query_count,
        len(boundary.registered_boundary_state_ids),
        len(boundary.registered_boundary_ground_row_ids),
        2,
        proposal_one.fixed_plan_audit_count + proposal_two.fixed_plan_audit_count,
        multistep._coordinate_reuse_count(base_model, final_build.model),
    )


def _run_control_arm(
    scope: LiveEpochCacheScope,
    semantics: LiveEpochProofSemanticsV1,
    observation_log: ObservationLogManifestV1,
    semantics_profile: DeterministicObservationProfileV1,
    observation_authority: PreregisteredObservationAuthorityV1,
    source: MultiStepQueryRefinementResultV1,
) -> LiveEpochProofArmV1:
    runtime = _Runtime(scope, semantics)
    first = _run_epoch(
        runtime, LiveEpochName.FIRST, observation_log, semantics_profile,
        observation_authority, source.first_overlay_build,
        source.first_threshold_rebase, source.round_one_request,
        source.round_one_bundle,
    )
    if scope is LiveEpochCacheScope.EPOCH_RESET_GLOBAL_DAG:
        runtime.reset()
    final = _run_epoch(
        runtime, LiveEpochName.FINAL, observation_log, semantics_profile,
        observation_authority, source.final_overlay_build,
        source.final_threshold_rebase, source.round_two_request,
        source.round_two_bundle,
    )
    return _freeze_arm(runtime, first, final)


def run_lmb_h2_live_query_local_epoch_invalidation_v1(
    observation_log: ObservationLogManifestV1,
    semantics_profile: DeterministicObservationProfileV1,
    observation_authority: PreregisteredObservationAuthorityV1,
    observed_synthesis_result: ObservedTypedPartialRAPMResultV1,
    thresholds: FrozenPartialAuditThresholdsV1,
    base_plan_proposal: TypedPartialModelPlanProposalResultV2,
    failed_audit: TypedPartialSoundAuditResultV2,
    kernel: LMBKernel,
) -> LiveQueryLocalEpochInvalidationResultV1:
    """Execute the authentic live first-failure -> nine-row -> final-certificate loop."""

    if (
        type(observation_log) is not ObservationLogManifestV1
        or type(semantics_profile) is not DeterministicObservationProfileV1
        or type(observation_authority) is not PreregisteredObservationAuthorityV1
        or type(observed_synthesis_result) is not ObservedTypedPartialRAPMResultV1
        or type(thresholds) is not FrozenPartialAuditThresholdsV1
        or type(base_plan_proposal) is not TypedPartialModelPlanProposalResultV2
        or type(failed_audit) is not TypedPartialSoundAuditResultV2
        or type(kernel) is not LMBKernel
    ):
        raise LiveEpochInvariantViolation("production rejects substituted upstream authorities")
    semantics = live_epoch_proof_semantics_v1()
    model, verified_plan, source_plan, verified_audit, frontier = (
        multistep._verified_h2_failure_chain(
            observation_log, semantics_profile, observation_authority,
            observed_synthesis_result, thresholds, base_plan_proposal, failed_audit,
        )
    )
    base_document = model.to_document()
    events: list[LiveOrderingEventV1] = []
    _event(events, "BASE_FAILURE_CHAIN_VERIFIED", frontier.frontier_id, 0, 0)
    request_one = multistep._round_one_request(
        model, thresholds, verified_plan, source_plan, verified_audit, frontier
    )
    _event(events, "ROUND_ONE_REQUEST_FROZEN", request_one.request_id, 0, 0)
    bundle_one = multistep._acquire(1, request_one, observation_log, None, kernel)
    boundary = multistep._expand_boundary(
        observation_log, observed_synthesis_result, request_one, bundle_one, kernel
    )
    _event(
        events, "ROUND_ONE_EVIDENCE_AND_BOUNDARY_FROZEN", boundary.expansion_id,
        4, 3,
    )
    model_one = multistep._assemble_overlay(
        observation_log, semantics_profile, observed_synthesis_result, thresholds,
        source_plan, verified_audit, request_one, bundle_one, (bundle_one,), boundary,
        model.model_id,
    )
    build_one = multistep._build_result(
        1, model_one, model.model_id, model.model_id, thresholds, source_plan,
        verified_audit, request_one, bundle_one, boundary,
    )
    rebase_one = multistep._rebase(build_one, thresholds)
    if model_one.model_id != EXPECTED_FIRST_MODEL_ID:
        raise LiveEpochInvariantViolation("first immutable epoch identity changed")
    _event(events, "FIRST_OVERLAY_EPOCH_FROZEN", model_one.model_id, 4, 3)

    live_runtime = _Runtime(
        LiveEpochCacheScope.GLOBAL_CROSS_EPOCH_FACET_DAG, semantics
    )
    first_execution = _run_epoch(
        live_runtime, LiveEpochName.FIRST, observation_log, semantics_profile,
        observation_authority, build_one, rebase_one, request_one, bundle_one,
    )
    if first_execution.plan_proposal.result_id != EXPECTED_FIRST_PROPOSAL_ID:
        raise LiveEpochInvariantViolation("first DAG-derived proposal changed")
    _event(
        events, "FIRST_CANDIDATE_DAG_AND_PROPOSAL_FROZEN",
        first_execution.plan_proposal.result_id, 4, 3,
    )
    first_selected = first_execution.selected_plan_audit.audit_result
    if (
        first_selected.outcome is not PartialAuditOutcome.FAILED_PROOF_FRONTIER
        or first_selected.failed_proof_frontier is None
        or first_selected.failed_proof_frontier.earliest_time_index != 1
        or first_selected.failed_proof_frontier.remaining_horizon != 1
    ):
        raise LiveEpochInvariantViolation("first independent DAG root did not freeze H2 failure")
    _event(
        events, "FIRST_INDEPENDENT_SELECTED_FAILURE_FROZEN",
        first_execution.selected_plan_audit.result_id, 4, 3,
    )
    request_two = multistep._round_two_request(
        build_one, rebase_one, first_execution.plan_proposal,
        first_execution.selected_plan_audit, boundary,
    )
    if request_two.request_id != EXPECTED_ROUND_TWO_REQUEST_ID:
        raise LiveEpochInvariantViolation("round-two request differs from first-root authority")
    _event(
        events, "ROUND_TWO_REQUEST_DERIVED_FROM_FIRST_ROOT", request_two.request_id,
        4, 3,
    )
    bundle_two = multistep._acquire(
        2, request_two, observation_log, boundary, kernel
    )
    if bundle_two.exact_kernel_query_count != 9:
        raise LiveEpochInvariantViolation("round-two evidence is not exactly nine rows")
    _event(events, "ROUND_TWO_NINE_ROWS_ACQUIRED", bundle_two.bundle_id, 13, 3)
    model_two = multistep._assemble_overlay(
        observation_log, semantics_profile, observed_synthesis_result, thresholds,
        source_plan, verified_audit, request_two, bundle_two,
        (bundle_one, bundle_two), boundary, model_one.model_id,
    )
    build_two = multistep._build_result(
        2, model_two, model.model_id, model_one.model_id, thresholds, source_plan,
        verified_audit, request_two, bundle_two, boundary,
    )
    rebase_two = multistep._rebase(build_two, thresholds)
    if model_two.model_id != EXPECTED_FINAL_MODEL_ID:
        raise LiveEpochInvariantViolation("final immutable epoch identity changed")
    _event(events, "FINAL_OVERLAY_EPOCH_FROZEN", model_two.model_id, 13, 3)

    # The final source object does not yet exist. Derive the delta directly from
    # the two immutable model documents and the authoritative request/bundle.
    class _DeltaSource:
        first_overlay_build = build_one
        final_overlay_build = build_two
        round_two_request = request_two
        round_two_bundle = bundle_two

    delta = _derive_delta(_DeltaSource())  # type: ignore[arg-type]
    invalidation = LiveEpochInvalidationManifestV1(
        delta.delta_id, delta.direct_changed_slots,
        delta.affected_descendant_slots, delta.reusable_slots,
    )
    _event(events, "EXACT_MODEL_EPOCH_DELTA_FROZEN", delta.delta_id, 13, 3)
    final_execution = _run_epoch(
        live_runtime, LiveEpochName.FINAL, observation_log, semantics_profile,
        observation_authority, build_two, rebase_two, request_two, bundle_two,
    )
    _event(
        events, "FINAL_CANDIDATE_DAG_AND_PROPOSAL_FROZEN",
        final_execution.plan_proposal.result_id, 13, 3,
    )
    if final_execution.selected_plan_audit.result_id != EXPECTED_FINAL_AUDIT_ID:
        raise LiveEpochInvariantViolation("final independent DAG audit identity changed")
    _event(
        events, "FINAL_INDEPENDENT_SELECTED_CERTIFICATE_FROZEN",
        final_execution.selected_plan_audit.result_id, 13, 3,
    )
    telemetry = _telemetry(
        model, build_one, build_two, bundle_one, bundle_two, boundary,
        first_execution.plan_proposal, final_execution.plan_proposal,
    )
    source = MultiStepQueryRefinementResultV1(
        observed_synthesis_result.result_id, thresholds.thresholds_id,
        verified_plan.result_id, source_plan.plan_id, verified_audit.result_id,
        request_one, bundle_one, boundary, build_one, rebase_one,
        first_execution.plan_proposal, first_execution.selected_plan_audit,
        request_two, bundle_two, build_two, rebase_two,
        final_execution.plan_proposal, final_execution.selected_plan_audit, telemetry,
    )
    if source.result_id != EXPECTED_MULTISTEP_RESULT_ID or model.to_document() != base_document:
        raise LiveEpochInvariantViolation("live DAG did not reconstruct canonical V0-047 chain")
    live_arm = _freeze_arm(live_runtime, first_execution, final_execution)
    request_reset = _run_control_arm(
        LiveEpochCacheScope.REQUEST_RESET, semantics, observation_log,
        semantics_profile, observation_authority, source,
    )
    epoch_reset = _run_control_arm(
        LiveEpochCacheScope.EPOCH_RESET_GLOBAL_DAG, semantics, observation_log,
        semantics_profile, observation_authority, source,
    )
    result = LiveQueryLocalEpochInvalidationResultV1(
        semantics, source, LiveOrderingProtocolV1(tuple(events)), delta, invalidation,
        request_reset, epoch_reset, live_arm, 2, _RESULT_AUTHORITY,
    )
    return bind_runtime_authority_v1(result, issuer=_RESULT_AUTHORITY)


@dataclass(frozen=True, slots=True)
class LiveEpochVerificationReportV1:
    claimed_result_id: str
    replayed_result_id: str
    legacy_multistep_result_id: str
    exact_document_match: bool
    legacy_exact_document_match: bool
    evaluation_transition_calls: int
    evaluation_boundary_catalogue_calls: int
    evaluation_lane_only: bool = True
    included_in_operational_work: bool = False

    def __post_init__(self) -> None:
        for value in (
            self.claimed_result_id, self.replayed_result_id,
            self.legacy_multistep_result_id,
        ):
            _cid(value, "verification report identity")
        if (
            self.claimed_result_id != self.replayed_result_id
            or self.legacy_multistep_result_id != EXPECTED_MULTISTEP_RESULT_ID
            or self.exact_document_match is not True
            or self.legacy_exact_document_match is not True
            or self.evaluation_transition_calls != 26
            or self.evaluation_boundary_catalogue_calls != 6
            or self.evaluation_lane_only is not True
            or self.included_in_operational_work is not False
        ):
            raise LiveEpochInvariantViolation("independent verification report changed")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.live_epoch_verification_report.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "claimed_result_id": self.claimed_result_id,
            "replayed_result_id": self.replayed_result_id,
            "legacy_multistep_result_id": self.legacy_multistep_result_id,
            "exact_document_match": self.exact_document_match,
            "legacy_exact_document_match": self.legacy_exact_document_match,
            "evaluation_transition_calls": self.evaluation_transition_calls,
            "evaluation_boundary_catalogue_calls": self.evaluation_boundary_catalogue_calls,
            "evaluation_lane_only": self.evaluation_lane_only,
            "included_in_operational_work": self.included_in_operational_work,
        }

    @property
    def report_id(self) -> str:
        return _content_id("verification", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "report_id": self.report_id}


def verify_lmb_h2_live_query_local_epoch_invalidation_v1(
    observation_log: ObservationLogManifestV1,
    semantics_profile: DeterministicObservationProfileV1,
    observation_authority: PreregisteredObservationAuthorityV1,
    observed_synthesis_result: ObservedTypedPartialRAPMResultV1,
    thresholds: FrozenPartialAuditThresholdsV1,
    base_plan_proposal: TypedPartialModelPlanProposalResultV2,
    failed_audit: TypedPartialSoundAuditResultV2,
    kernel: LMBKernel,
    claimed_result: LiveQueryLocalEpochInvalidationResultV1,
) -> LiveEpochVerificationReportV1:
    """Replay the live runner and the unchanged V0-047 whole-chain control."""

    require_live_query_local_epoch_invalidation_result_v1(claimed_result)
    replayed = run_lmb_h2_live_query_local_epoch_invalidation_v1(
        observation_log, semantics_profile, observation_authority,
        observed_synthesis_result, thresholds, base_plan_proposal, failed_audit,
        kernel,
    )
    exact = replayed.to_document() == claimed_result.to_document()
    legacy = multistep.run_lmb_h2_multistep_query_refinement_v1(
        observation_log, semantics_profile, observation_authority,
        observed_synthesis_result, thresholds, base_plan_proposal, failed_audit,
        kernel,
    )
    legacy_exact = legacy.to_document() == replayed.live_multistep_result.to_document()
    if not exact or not legacy_exact:
        raise LiveEpochInvariantViolation("independent replay differs from claimed live result")
    return LiveEpochVerificationReportV1(
        claimed_result.result_id, replayed.result_id, legacy.result_id,
        exact, legacy_exact,
        replayed.live_multistep_result.telemetry.cumulative_exact_kernel_queries
        + legacy.telemetry.cumulative_exact_kernel_queries,
        replayed.live_multistep_result.telemetry.boundary_action_catalogue_queries
        + legacy.telemetry.boundary_action_catalogue_queries,
    )
