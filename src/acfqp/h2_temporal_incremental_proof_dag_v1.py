"""V0-052 registered H2 stage-local Bellman proof-dependency DAG.

This module factors the unchanged V0-043 fixed-plan audit over the final,
exact-type V0-047 query-local ``QueryScopedPartialRAPMV3`` into two temporal
Bellman stages.  The production entry point accepts only the observation
authority and the already-built V0-047 result.  It neither accepts nor opens a
kernel, a caller supplied cache/protocol, an expected-reuse oracle, a control
arm, or a monolithic-audit result.

The deliberately narrow positive control is H=2.  It proves that Bellman and
reachability obligations whose identities are local to a stage can be reused
across four Gray-ordered contingent plans.  Full query, threshold, proposal,
plan and role identities first meet at the fresh ``R`` root, where the legacy
threshold-bound V0-043 rows are rematerialized.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from fractions import Fraction
import hashlib
from pathlib import Path
from typing import Any, Mapping

import acfqp.multistep_query_refinement_v1 as multistep_module
import acfqp.partial_model_planner_v1 as planner_module
import acfqp.partial_sound_audit_v1 as audit_module
from acfqp._runtime_authority_v1 import (
    RuntimeAuthorityMintV1,
    bind_runtime_authority_v1,
    require_runtime_authority_v1,
    runtime_authority_fingerprint_v1,
)
from acfqp.domains.matching_buffer import LMBKernel
from acfqp.multistep_query_refinement_v1 import (
    MultiStepQueryRefinementResultV1,
    verify_lmb_h2_multistep_query_refinement_v1,
)
from acfqp.observation_partial_rapm_v1 import (
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
    PartialPlannerCandidateSummaryV1,
    PartialModelPlannerSelectionMode,
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
)
from acfqp.partial_model_planner_v1 import TypedPartialModelPlanProposalResultV2
from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id


SCHEMA_VERSION = "1.0.0"
CONTRACT_VERSION = "1.15.0"
PROFILE_KEY = "lmb_h2_stage_local_bellman_proof_dag_v0"
SUCCESS_STATUS = "CERTIFIED_REGISTERED_H2_STAGE_LOCAL_BELLMAN_RECURRENCE_CONTROL"

EXPECTED_PARTIAL_AUDIT_SOURCE_SHA256 = (
    "661aee3732afda05c860f5dadae2b3545ecbbed7cee86f27517d1ea5dfcb7934"
)
EXPECTED_PARTIAL_MODEL_PLANNER_SOURCE_SHA256 = (
    "b676c4f91d18ea9406ef1101d7072baccb519a05176496ccf6a867cedb6d4f7d"
)
EXPECTED_MULTISTEP_SOURCE_SHA256 = (
    "d335b509311f6d87a6e2106d1090580f3c7c4cca8cd4eaa4209fff4038e54845"
)
EXPECTED_V0051_SOURCE_SHA256 = (
    "f67a5d7fd47eddccca6124c859bf636230f76b228d37dcc399d8e3ce7dbfec6b"
)
EXPECTED_SOURCE_RESULT_ID = (
    "9a3691831b8103d1523333f50b302a5f099dee9d1b8790a893e5998810866d42"
)
EXPECTED_FINAL_MODEL_ID = (
    "a18a29a1c1bd3433ef7ace6d99c67a594a0d587b6b0c2889f71022eaa7437315"
)
EXPECTED_GRAY_PLAN_IDS = (
    "0a90dfe57c48c76e917b80b546242975f43219b310ccff238bea00bae19ad1eb",
    "125090d288cddb9a5bf42bcfc77ca406b8474d4f3091c0643fb4c3b8de9b21af",
    "88d24a71393c598fba0de332ee8662a23c6532f34c856763d54fcb88ca296841",
    "81e44a708a6b80c43ba4c9cef4254144165cc84f235a649054e7f1158d5b9a73",
)
GRAY_SCHEDULE_CODES = ("A0A0", "A0A1", "A1A1", "A1A0")

EXPECTED_COMPUTES = {
    "REQUEST_RESET": 55,
    "EXACT_PLAN_PARTITIONED": 45,
    "GLOBAL_STAGE_DAG": 35,
}
EXPECTED_REUSES = {
    "REQUEST_RESET": 0,
    "EXACT_PLAN_PARTITIONED": 10,
    "GLOBAL_STAGE_DAG": 20,
}
EXPECTED_PREFIX_COMPUTES = {
    "REQUEST_RESET": (11, 22, 33, 44, 55),
    "EXACT_PLAN_PARTITIONED": (11, 22, 33, 44, 45),
    "GLOBAL_STAGE_DAG": (11, 19, 27, 34, 35),
}
EXPECTED_GLOBAL_GROUPED = {
    "U": (2, 8),
    "P": (6, 4),
    "C": (6, 4),
    "D": (4, 1),
    "E": (4, 1),
    "F": (4, 1),
    "G": (4, 1),
    "R": (5, 0),
}

DOMAIN_TAGS = {
    "semantics": "acfqp:h2-temporal-proof-semantics:v1",
    "stage": "acfqp:h2-temporal-stage-assignment:v1",
    "gray_plan": "acfqp:h2-temporal-gray-plan:v1",
    "selection": "acfqp:h2-temporal-plan-selection:v1",
    "protocol": "acfqp:h2-temporal-proof-protocol:v1",
    "manifest": "acfqp:h2-temporal-expected-reuse-manifest:v1",
    "request": "acfqp:h2-temporal-proof-request:v1",
    "node_key": "acfqp:h2-temporal-proof-node-key:v1",
    "node_result": "acfqp:h2-temporal-proof-node-result:v1",
    "node_entry": "acfqp:h2-temporal-proof-node-entry:v1",
    "resolution": "acfqp:h2-temporal-proof-resolution:v1",
    "receipt": "acfqp:h2-temporal-proof-request-receipt:v1",
    "cache_state": "acfqp:h2-temporal-proof-cache-state:v1",
    "cache": "acfqp:h2-temporal-proof-cache:v1",
    "work": "acfqp:h2-temporal-proof-work:v1",
    "prefix": "acfqp:h2-temporal-proof-prefix:v1",
    "closure": "acfqp:h2-temporal-plan-change-closure:v1",
    "arm": "acfqp:h2-temporal-proof-arm:v1",
    "execution": "acfqp:h2-temporal-proof-execution:v1",
    "legacy": "acfqp:h2-temporal-legacy-match:v1",
    "result": "acfqp:h2-temporal-proof-control-result:v1",
}
if len(DOMAIN_TAGS) != len(set(DOMAIN_TAGS.values())):  # pragma: no cover
    raise RuntimeError("V0-052 content domains must be unique")


class H2TemporalProofDAGInvariantViolation(ValueError):
    """The registered H2 temporal proof graph or authority is invalid."""


class H2TemporalProofSlot(str, Enum):
    U1 = "U1"
    U0 = "U0"
    P1 = "P1"
    P0 = "P0"
    C0 = "C0"
    C1 = "C1"
    D = "D"
    E = "E"
    F = "F"
    G = "G"
    R = "R"


SLOT_ORDER = tuple(H2TemporalProofSlot)
LOWER_SLOT_ORDER = SLOT_ORDER[:-1]


class H2TemporalCacheScope(str, Enum):
    REQUEST_RESET = "REQUEST_RESET"
    EXACT_PLAN_PARTITIONED = "EXACT_PLAN_PARTITIONED"
    GLOBAL_STAGE_DAG = "GLOBAL_STAGE_DAG"


class H2TemporalProofRole(str, Enum):
    CANDIDATE_RANKING_AUDIT = "CANDIDATE_RANKING_AUDIT"
    INDEPENDENT_SELECTED_PLAN_CERTIFICATE = (
        "INDEPENDENT_SELECTED_PLAN_CERTIFICATE"
    )


class H2TemporalResolutionOutcome(str, Enum):
    COMPUTED = "COMPUTED"
    REUSED = "REUSED"


def _content_id(role: str, payload: Mapping[str, Any]) -> str:
    try:
        domain = DOMAIN_TAGS[role]
        encoded = canonical_json_bytes(dict(payload))
    except (KeyError, TypeError, ValueError) as error:
        raise H2TemporalProofDAGInvariantViolation(str(error)) from error
    return hashlib.sha256(domain.encode() + b"\x00" + encoded).hexdigest()


def _cid(value: Any, name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise H2TemporalProofDAGInvariantViolation(
            f"{name} must be a full content ID"
        ) from error


def _integer(value: Any, name: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise H2TemporalProofDAGInvariantViolation(
            f"{name} must be an integer >= {minimum}"
        )
    return value


def _fdoc(value: Fraction) -> dict[str, int]:
    return {"numerator": value.numerator, "denominator": value.denominator}


def _source_sha(module: Any) -> str:
    path = Path(module.__file__)
    if path.suffix != ".py" or not path.is_file():
        raise H2TemporalProofDAGInvariantViolation("registered source is unavailable")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _slot_family(slot: H2TemporalProofSlot) -> str:
    return slot.value[0]


@dataclass(frozen=True, slots=True)
class H2TemporalProofDAGSemanticsV1:
    partial_audit_source_sha256: str
    partial_model_planner_source_sha256: str
    multistep_source_sha256: str
    predecessor_incremental_source_sha256: str
    temporal_topology: tuple[tuple[str, tuple[str, ...]], ...]
    horizon: int = 2
    arithmetic_kind: str = "EXACT_FRACTIONS_FRACTION"
    stage_local_policy_and_reachability_keys: bool = True
    whole_horizon_v0051_helpers_allowed: bool = False

    def __post_init__(self) -> None:
        expected_topology = (
            ("U1", ()), ("U0", ("U1",)),
            ("P1", ()), ("P0", ("P1",)),
            ("C0", ()), ("C1", ("C0",)),
            ("D", ("U0", "P0", "C0", "C1")),
            ("E", ("D",)), ("F", ("D",)),
            ("G", ("C0", "C1")),
            ("R", tuple(slot.value for slot in LOWER_SLOT_ORDER)),
        )
        if (
            self.partial_audit_source_sha256 != EXPECTED_PARTIAL_AUDIT_SOURCE_SHA256
            or self.partial_model_planner_source_sha256
            != EXPECTED_PARTIAL_MODEL_PLANNER_SOURCE_SHA256
            or self.multistep_source_sha256 != EXPECTED_MULTISTEP_SOURCE_SHA256
            or self.predecessor_incremental_source_sha256
            != EXPECTED_V0051_SOURCE_SHA256
            or self.temporal_topology != expected_topology
            or self.horizon != 2
            or self.arithmetic_kind != "EXACT_FRACTIONS_FRACTION"
            or self.stage_local_policy_and_reachability_keys is not True
            or self.whole_horizon_v0051_helpers_allowed is not False
        ):
            raise H2TemporalProofDAGInvariantViolation(
                "H2 temporal proof semantics or source pin changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h2_temporal_proof_semantics.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "partial_audit_source_sha256": self.partial_audit_source_sha256,
            "partial_model_planner_source_sha256": (
                self.partial_model_planner_source_sha256
            ),
            "multistep_source_sha256": self.multistep_source_sha256,
            "predecessor_incremental_source_sha256": self.predecessor_incremental_source_sha256,
            "temporal_topology": [
                {"slot": slot, "ordered_parents": list(parents)}
                for slot, parents in self.temporal_topology
            ],
            "horizon": self.horizon,
            "arithmetic_kind": self.arithmetic_kind,
            "stage_local_policy_and_reachability_keys": self.stage_local_policy_and_reachability_keys,
            "whole_horizon_v0051_helpers_allowed": self.whole_horizon_v0051_helpers_allowed,
        }

    @property
    def semantics_id(self) -> str:
        return _content_id("semantics", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "semantics_id": self.semantics_id}


def h2_temporal_proof_dag_semantics_v1() -> H2TemporalProofDAGSemanticsV1:
    return H2TemporalProofDAGSemanticsV1(
        _source_sha(audit_module),
        _source_sha(planner_module),
        _source_sha(multistep_module),
        hashlib.sha256(
            Path(__file__).with_name("incremental_proof_dag_v1.py").read_bytes()
        ).hexdigest(),
        (
            ("U1", ()), ("U0", ("U1",)),
            ("P1", ()), ("P0", ("P1",)),
            ("C0", ()), ("C1", ("C0",)),
            ("D", ("U0", "P0", "C0", "C1")),
            ("E", ("D",)), ("F", ("D",)),
            ("G", ("C0", "C1")),
            ("R", tuple(slot.value for slot in LOWER_SLOT_ORDER)),
        ),
    )


@dataclass(frozen=True, slots=True)
class H2TemporalStageAssignmentV1:
    assignment_index: int
    ordered_cell_action_labels: tuple[tuple[str, str, tuple[int, ...]], ...]

    def __post_init__(self) -> None:
        if self.assignment_index not in (0, 1):
            raise H2TemporalProofDAGInvariantViolation(
                "H2 profile has exactly two canonical stage assignments"
            )
        if (
            type(self.ordered_cell_action_labels) is not tuple
            or not self.ordered_cell_action_labels
            or len({row[0] for row in self.ordered_cell_action_labels})
            != len(self.ordered_cell_action_labels)
            or any(
                type(row) is not tuple
                or len(row) != 3
                or type(row[0]) is not str
                or type(row[1]) is not str
                or type(row[2]) is not tuple
                or any(bit not in (0, 1) for bit in row[2])
                for row in self.ordered_cell_action_labels
            )
        ):
            raise H2TemporalProofDAGInvariantViolation(
                "stage assignment is not a canonical semantic assignment"
            )
        for cell_id, action_id, _ in self.ordered_cell_action_labels:
            _cid(cell_id, "stage cell")
            _cid(action_id, "stage semantic action")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h2_temporal_stage_assignment.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "assignment_index": self.assignment_index,
            "ordered_cell_action_labels": [
                {
                    "cell_id": cell_id,
                    "semantic_action_id": action_id,
                    "label_values": list(labels),
                }
                for cell_id, action_id, labels in self.ordered_cell_action_labels
            ],
        }

    @property
    def stage_assignment_id(self) -> str:
        return _content_id("stage", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "stage_assignment_id": self.stage_assignment_id}


@dataclass(frozen=True, slots=True)
class H2TemporalGrayPlanV1:
    gray_index: int
    schedule_code: str
    stage_assignment_ids: tuple[str, str]
    contingent_plan: FrozenContingentAbstractPlanV1
    semantic_schedule_key: tuple[int, ...]

    def __post_init__(self) -> None:
        _integer(self.gray_index, "Gray plan index")
        if (
            self.gray_index >= 4
            or self.schedule_code != GRAY_SCHEDULE_CODES[self.gray_index]
            or type(self.stage_assignment_ids) is not tuple
            or len(self.stage_assignment_ids) != 2
            or type(self.contingent_plan) is not FrozenContingentAbstractPlanV1
            or self.contingent_plan.horizon != 2
            or self.contingent_plan.plan_id != EXPECTED_GRAY_PLAN_IDS[self.gray_index]
            or type(self.semantic_schedule_key) is not tuple
            or any(value not in (0, 1) for value in self.semantic_schedule_key)
        ):
            raise H2TemporalProofDAGInvariantViolation(
                "Gray plan proposal is not the frozen canonical schedule"
            )
        for value in self.stage_assignment_ids:
            _cid(value, "proposal stage assignment")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h2_temporal_gray_plan.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "gray_index": self.gray_index,
            "schedule_code": self.schedule_code,
            "stage_assignment_ids": list(self.stage_assignment_ids),
            "contingent_plan": self.contingent_plan.to_document(),
            "semantic_schedule_key": list(self.semantic_schedule_key),
        }

    @property
    def gray_plan_id(self) -> str:
        return _content_id("gray_plan", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "gray_plan_id": self.gray_plan_id}


@dataclass(frozen=True, slots=True)
class H2TemporalProofDAGProtocolV1:
    semantics_id: str
    source_result_id: str
    source_final_model_id: str
    source_thresholds_id: str
    stage_assignments: tuple[H2TemporalStageAssignmentV1, ...]
    gray_plans: tuple[H2TemporalGrayPlanV1, ...]
    selection_rule: str = "V0047_NUMERIC_GATE_THEN_SEMANTIC_LABEL_LEXICOGRAPHIC_V1"
    candidate_request_count: int = 4
    selected_request_count: int = 1
    horizon: int = 2

    def __post_init__(self) -> None:
        for value, name in (
            (self.semantics_id, "protocol semantics"),
            (self.source_result_id, "protocol source result"),
            (self.source_final_model_id, "protocol source model"),
            (self.source_thresholds_id, "protocol thresholds"),
        ):
            _cid(value, name)
        if (
            self.source_result_id != EXPECTED_SOURCE_RESULT_ID
            or self.source_final_model_id != EXPECTED_FINAL_MODEL_ID
            or type(self.stage_assignments) is not tuple
            or len(self.stage_assignments) != 2
            or tuple(item.assignment_index for item in self.stage_assignments) != (0, 1)
            or len({item.stage_assignment_id for item in self.stage_assignments}) != 2
            or type(self.gray_plans) is not tuple
            or len(self.gray_plans) != 4
            or tuple(item.gray_index for item in self.gray_plans) != (0, 1, 2, 3)
            or tuple(item.schedule_code for item in self.gray_plans)
            != GRAY_SCHEDULE_CODES
            or tuple(item.contingent_plan.plan_id for item in self.gray_plans)
            != EXPECTED_GRAY_PLAN_IDS
            or self.selection_rule
            != "V0047_NUMERIC_GATE_THEN_SEMANTIC_LABEL_LEXICOGRAPHIC_V1"
            or self.candidate_request_count != 4
            or self.selected_request_count != 1
            or self.horizon != 2
        ):
            raise H2TemporalProofDAGInvariantViolation(
                "H2 temporal protocol, Gray order, or source identity changed"
            )
        stage_by_id = {
            item.stage_assignment_id: item for item in self.stage_assignments
        }
        for gray in self.gray_plans:
            bits = (int(gray.schedule_code[1]), int(gray.schedule_code[3]))
            expected_ids = tuple(
                self.stage_assignments[bit].stage_assignment_id for bit in bits
            )
            if gray.stage_assignment_ids != expected_ids:
                raise H2TemporalProofDAGInvariantViolation(
                    "Gray code and stage-assignment IDs disagree"
                )
            for time_index, stage in enumerate(gray.contingent_plan.stages):
                artifact = stage_by_id[gray.stage_assignment_ids[time_index]]
                if {
                    item.cell_id: item.semantic_action_id for item in stage.assignments
                } != {
                    cell_id: action_id
                    for cell_id, action_id, _ in artifact.ordered_cell_action_labels
                }:
                    raise H2TemporalProofDAGInvariantViolation(
                        "Gray plan stages differ from their stage artifacts"
                    )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h2_temporal_proof_dag_protocol.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "semantics_id": self.semantics_id,
            "source_result_id": self.source_result_id,
            "source_final_model_id": self.source_final_model_id,
            "source_thresholds_id": self.source_thresholds_id,
            "stage_assignments": [item.to_document() for item in self.stage_assignments],
            "gray_plans": [item.to_document() for item in self.gray_plans],
            "selection_rule": self.selection_rule,
            "candidate_request_count": self.candidate_request_count,
            "selected_request_count": self.selected_request_count,
            "horizon": self.horizon,
        }

    @property
    def protocol_id(self) -> str:
        return _content_id("protocol", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "protocol_id": self.protocol_id}


def _manifest_outcomes() -> Mapping[H2TemporalCacheScope, tuple[tuple[str, ...], ...]]:
    computed = H2TemporalResolutionOutcome.COMPUTED.value
    reused = H2TemporalResolutionOutcome.REUSED.value
    all_c = tuple(computed for _ in SLOT_ORDER)
    return {
        H2TemporalCacheScope.REQUEST_RESET: (all_c,) * 5,
        H2TemporalCacheScope.EXACT_PLAN_PARTITIONED: (
            all_c, all_c, all_c, all_c,
            tuple(reused for _ in LOWER_SLOT_ORDER) + (computed,),
        ),
        H2TemporalCacheScope.GLOBAL_STAGE_DAG: (
            all_c,
            tuple(
                computed if slot in {
                    H2TemporalProofSlot.P1, H2TemporalProofSlot.P0,
                    H2TemporalProofSlot.C1, H2TemporalProofSlot.D,
                    H2TemporalProofSlot.E, H2TemporalProofSlot.F,
                    H2TemporalProofSlot.G, H2TemporalProofSlot.R,
                } else reused
                for slot in SLOT_ORDER
            ),
            tuple(
                computed if slot in {
                    H2TemporalProofSlot.P0, H2TemporalProofSlot.C0,
                    H2TemporalProofSlot.C1, H2TemporalProofSlot.D,
                    H2TemporalProofSlot.E, H2TemporalProofSlot.F,
                    H2TemporalProofSlot.G, H2TemporalProofSlot.R,
                } else reused
                for slot in SLOT_ORDER
            ),
            tuple(
                computed if slot in {
                    H2TemporalProofSlot.P0, H2TemporalProofSlot.C1,
                    H2TemporalProofSlot.D, H2TemporalProofSlot.E,
                    H2TemporalProofSlot.F, H2TemporalProofSlot.G,
                    H2TemporalProofSlot.R,
                } else reused
                for slot in SLOT_ORDER
            ),
            tuple(computed if slot is H2TemporalProofSlot.R else reused for slot in SLOT_ORDER),
        ),
    }


@dataclass(frozen=True, slots=True)
class H2TemporalExpectedReuseManifestV1:
    protocol_id: str
    schedule_codes: tuple[str, ...]
    selected_request_binding: str
    expected_outcomes: tuple[tuple[str, tuple[tuple[str, ...], ...]], ...]
    expected_prefix_computes: tuple[tuple[str, tuple[int, ...]], ...]
    frozen_before_arithmetic: bool = True
    post_run_actuals_observed: bool = False

    def __post_init__(self) -> None:
        _cid(self.protocol_id, "reuse manifest protocol")
        expected = _manifest_outcomes()
        if (
            self.schedule_codes != GRAY_SCHEDULE_CODES
            or self.selected_request_binding != "WINNER_OF_FROZEN_V0047_NUMERIC_SEMANTIC_RULE"
            or self.expected_outcomes
            != tuple((scope.value, expected[scope]) for scope in H2TemporalCacheScope)
            or self.expected_prefix_computes
            != tuple(
                (scope.value, EXPECTED_PREFIX_COMPUTES[scope.value])
                for scope in H2TemporalCacheScope
            )
            or self.frozen_before_arithmetic is not True
            or self.post_run_actuals_observed is not False
        ):
            raise H2TemporalProofDAGInvariantViolation(
                "expected reuse manifest was changed or learned from actual arithmetic"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h2_temporal_expected_reuse_manifest.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "protocol_id": self.protocol_id,
            "schedule_codes": list(self.schedule_codes),
            "selected_request_binding": self.selected_request_binding,
            "expected_outcomes": [
                {"scope": scope, "requests": [list(row) for row in rows]}
                for scope, rows in self.expected_outcomes
            ],
            "expected_prefix_computes": [
                {"scope": scope, "prefix_computes": list(values)}
                for scope, values in self.expected_prefix_computes
            ],
            "frozen_before_arithmetic": self.frozen_before_arithmetic,
            "post_run_actuals_observed": self.post_run_actuals_observed,
        }

    @property
    def manifest_id(self) -> str:
        return _content_id("manifest", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "manifest_id": self.manifest_id}


@dataclass(frozen=True, slots=True)
class H2TemporalProofRequestV1:
    request_index: int
    role: H2TemporalProofRole
    protocol_id: str
    gray_plan_id: str
    planner_result_id: str | None
    contingent_plan_id: str
    source_result_id: str
    partial_model_id: str
    thresholds_id: str

    def __post_init__(self) -> None:
        _integer(self.request_index, "proof request index", 1)
        if self.request_index > 5 or type(self.role) is not H2TemporalProofRole:
            raise H2TemporalProofDAGInvariantViolation("proof request index/role invalid")
        for name in (
            "protocol_id", "gray_plan_id", "contingent_plan_id", "source_result_id",
            "partial_model_id", "thresholds_id",
        ):
            _cid(getattr(self, name), f"proof request {name}")
        if (
            (self.request_index <= 4)
            != (self.role is H2TemporalProofRole.CANDIDATE_RANKING_AUDIT)
            or self.source_result_id != EXPECTED_SOURCE_RESULT_ID
            or self.partial_model_id != EXPECTED_FINAL_MODEL_ID
            or (self.request_index <= 4) != (self.planner_result_id is None)
        ):
            raise H2TemporalProofDAGInvariantViolation("proof request role/source changed")
        if self.planner_result_id is not None:
            _cid(self.planner_result_id, "selected proof request planner result")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h2_temporal_proof_request.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "request_index": self.request_index,
            "role": self.role.value,
            "protocol_id": self.protocol_id,
            "gray_plan_id": self.gray_plan_id,
            "planner_result_id": (
                {"kind": "NOT_APPLICABLE", "reason": "CANDIDATE_PRECEDES_SELECTION"}
                if self.planner_result_id is None else self.planner_result_id
            ),
            "contingent_plan_id": self.contingent_plan_id,
            "source_result_id": self.source_result_id,
            "partial_model_id": self.partial_model_id,
            "thresholds_id": self.thresholds_id,
        }

    @property
    def request_id(self) -> str:
        return _content_id("request", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "request_id": self.request_id}


@dataclass(frozen=True, slots=True)
class H2TemporalProofNodeKeyV1:
    slot: H2TemporalProofSlot
    semantics_id: str
    partial_model_id: str
    time_index: int | None
    stage_assignment_id: str | None
    ordered_parent_entry_ids: tuple[str, ...]
    identity_terms: tuple[tuple[str, str], ...]

    def __post_init__(self) -> None:
        if type(self.slot) is not H2TemporalProofSlot:
            raise H2TemporalProofDAGInvariantViolation("node slot is substituted")
        _cid(self.semantics_id, "node semantics")
        _cid(self.partial_model_id, "node model")
        if self.time_index is not None and self.time_index not in (0, 1):
            raise H2TemporalProofDAGInvariantViolation("node time is outside H2")
        if self.stage_assignment_id is not None:
            _cid(self.stage_assignment_id, "node stage assignment")
        if type(self.ordered_parent_entry_ids) is not tuple:
            raise H2TemporalProofDAGInvariantViolation("node parents are not ordered")
        for value in self.ordered_parent_entry_ids:
            _cid(value, "node parent entry")
        if (
            type(self.identity_terms) is not tuple
            or self.identity_terms != tuple(sorted(self.identity_terms))
            or len({name for name, _ in self.identity_terms}) != len(self.identity_terms)
        ):
            raise H2TemporalProofDAGInvariantViolation("node identity terms are not canonical")
        parent_count = {
            H2TemporalProofSlot.U1: 0, H2TemporalProofSlot.U0: 1,
            H2TemporalProofSlot.P1: 0, H2TemporalProofSlot.P0: 1,
            H2TemporalProofSlot.C0: 0, H2TemporalProofSlot.C1: 1,
            H2TemporalProofSlot.D: 4, H2TemporalProofSlot.E: 1,
            H2TemporalProofSlot.F: 1, H2TemporalProofSlot.G: 2,
            H2TemporalProofSlot.R: 10,
        }[self.slot]
        if len(self.ordered_parent_entry_ids) != parent_count:
            raise H2TemporalProofDAGInvariantViolation("node parent topology changed")
        exact_term_names = {
            H2TemporalProofSlot.U1: ("formula_id", "return_bound_proof_id", "reward_weights_digest"),
            H2TemporalProofSlot.U0: ("formula_id", "return_bound_proof_id", "reward_weights_digest"),
            H2TemporalProofSlot.P1: ("formula_id", "return_bound_proof_id", "reward_weights_digest"),
            H2TemporalProofSlot.P0: ("formula_id", "return_bound_proof_id", "reward_weights_digest"),
            H2TemporalProofSlot.C0: ("formula_id", "initial_distribution_digest"),
            H2TemporalProofSlot.C1: ("formula_id",),
            H2TemporalProofSlot.D: (
                "formula_id", "initial_distribution_digest",
                "return_bound_proof_id", "reward_weights_digest",
            ),
            H2TemporalProofSlot.E: ("formula_id", "normalized_regret_tolerance"),
            H2TemporalProofSlot.F: ("formula_id", "risk_tolerance"),
            H2TemporalProofSlot.G: ("formula_id",),
            H2TemporalProofSlot.R: (
                "formula_id", "gray_plan_id", "plan_id", "planner_result_id",
                "request_id", "role", "source_result_id", "thresholds_id",
            ),
        }[self.slot]
        if tuple(name for name, _ in self.identity_terms) != exact_term_names:
            raise H2TemporalProofDAGInvariantViolation(
                "node identity term allowlist has missing, extra, or reordered fields"
            )
        expected_time = {
            H2TemporalProofSlot.U1: 1, H2TemporalProofSlot.U0: 0,
            H2TemporalProofSlot.P1: 1, H2TemporalProofSlot.P0: 0,
            H2TemporalProofSlot.C0: 0, H2TemporalProofSlot.C1: 1,
            H2TemporalProofSlot.D: None, H2TemporalProofSlot.E: None,
            H2TemporalProofSlot.F: None, H2TemporalProofSlot.G: None,
            H2TemporalProofSlot.R: None,
        }[self.slot]
        stage_required = self.slot in {
            H2TemporalProofSlot.P1, H2TemporalProofSlot.P0,
            H2TemporalProofSlot.C0, H2TemporalProofSlot.C1,
        }
        if self.time_index != expected_time or stage_required != (self.stage_assignment_id is not None):
            raise H2TemporalProofDAGInvariantViolation(
                "slot time/stage identity does not match the frozen H2 topology"
            )
        if self.slot in {
            H2TemporalProofSlot.P0, H2TemporalProofSlot.P1,
            H2TemporalProofSlot.C0, H2TemporalProofSlot.C1,
        }:
            forbidden = {"plan_id", "query_id", "thresholds_id", "role", "request_id", "proposal_id"}
            if (
                self.time_index not in (0, 1)
                or self.stage_assignment_id is None
                or forbidden & {name for name, _ in self.identity_terms}
            ):
                raise H2TemporalProofDAGInvariantViolation(
                    "P/C cache identity escaped its local stage/time/parent scope"
                )
        if self.slot is H2TemporalProofSlot.R:
            required = {
                "source_result_id", "thresholds_id", "gray_plan_id",
                "planner_result_id", "plan_id", "role", "request_id",
            }
            if not required <= {name for name, _ in self.identity_terms}:
                raise H2TemporalProofDAGInvariantViolation("R does not bind full identities")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h2_temporal_proof_node_key.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "slot": self.slot.value,
            "semantics_id": self.semantics_id,
            "partial_model_id": self.partial_model_id,
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
class H2TemporalProofNodeEntryV1:
    key: H2TemporalProofNodeKeyV1
    result_digest: str
    result_semantics: str
    threshold_bound_v1_row_count: int

    def __post_init__(self) -> None:
        if type(self.key) is not H2TemporalProofNodeKeyV1:
            raise H2TemporalProofDAGInvariantViolation("node entry key is substituted")
        _cid(self.result_digest, "node result digest")
        _integer(self.threshold_bound_v1_row_count, "threshold-bound row count")
        if type(self.result_semantics) is not str or not self.result_semantics:
            raise H2TemporalProofDAGInvariantViolation("node result semantics missing")
        if (
            (self.key.slot is H2TemporalProofSlot.R)
            != (self.threshold_bound_v1_row_count > 0)
        ):
            raise H2TemporalProofDAGInvariantViolation(
                "legacy threshold/plan-bound V1 rows may exist only at R"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h2_temporal_proof_node_entry.v1",
            "schema_version": SCHEMA_VERSION,
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
class H2TemporalProofResolutionV1:
    sequence_number: int
    request_id: str
    logical_slot: H2TemporalProofSlot
    partition_id: str
    node_key_id: str
    entry_id: str
    outcome: H2TemporalResolutionOutcome
    pre_cache_state_id: str
    post_cache_state_id: str

    def __post_init__(self) -> None:
        _integer(self.sequence_number, "resolution sequence", 1)
        if type(self.logical_slot) is not H2TemporalProofSlot or type(self.outcome) is not H2TemporalResolutionOutcome:
            raise H2TemporalProofDAGInvariantViolation("resolution enum is substituted")
        for name in (
            "request_id", "partition_id", "node_key_id", "entry_id",
            "pre_cache_state_id", "post_cache_state_id",
        ):
            _cid(getattr(self, name), f"resolution {name}")
        if self.outcome is H2TemporalResolutionOutcome.REUSED and self.pre_cache_state_id != self.post_cache_state_id:
            raise H2TemporalProofDAGInvariantViolation("reuse mutated the append-only cache")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h2_temporal_proof_resolution.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "sequence_number": self.sequence_number,
            "request_id": self.request_id,
            "logical_slot": self.logical_slot.value,
            "partition_id": self.partition_id,
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
class H2TemporalProofRequestReceiptV1:
    request: H2TemporalProofRequestV1
    gray_plan: H2TemporalGrayPlanV1
    resolution_ids: tuple[str, ...]
    root_entry_id: str
    audit_result: PartialSoundAuditResultV1

    def __post_init__(self) -> None:
        if (
            type(self.request) is not H2TemporalProofRequestV1
            or type(self.gray_plan) is not H2TemporalGrayPlanV1
            or type(self.audit_result) is not PartialSoundAuditResultV1
            or type(self.resolution_ids) is not tuple
            or len(self.resolution_ids) != 11
        ):
            raise H2TemporalProofDAGInvariantViolation("request receipt artifacts changed")
        for value in (*self.resolution_ids, self.root_entry_id):
            _cid(value, "request receipt dependency")
        if (
            self.request.gray_plan_id != self.gray_plan.gray_plan_id
            or self.request.contingent_plan_id != self.gray_plan.contingent_plan.plan_id
            or self.audit_result.contingent_plan_id != self.request.contingent_plan_id
            or self.audit_result.partial_model_id != self.request.partial_model_id
            or self.audit_result.thresholds_id != self.request.thresholds_id
        ):
            raise H2TemporalProofDAGInvariantViolation("receipt root identity chain changed")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h2_temporal_proof_request_receipt.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "request": self.request.to_document(),
            "gray_plan": self.gray_plan.to_document(),
            "resolution_ids": list(self.resolution_ids),
            "root_entry_id": self.root_entry_id,
            "audit_result": self.audit_result.to_document(),
        }

    @property
    def receipt_id(self) -> str:
        return _content_id("receipt", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "receipt_id": self.receipt_id}


def _cache_state_id(
    scope: H2TemporalCacheScope,
    partitions: Mapping[str, Mapping[str, str]],
) -> str:
    return _content_id(
        "cache_state",
        {
            "schema": "acfqp.h2_temporal_proof_cache_state.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "scope": scope.value,
            "partitions": [
                {
                    "partition_id": partition_id,
                    "entries": [
                        {"node_key_id": key, "entry_id": entry}
                        for key, entry in sorted(entries.items())
                    ],
                }
                for partition_id, entries in sorted(partitions.items())
            ],
        },
    )


@dataclass(frozen=True, slots=True)
class H2TemporalProofCacheV1:
    scope: H2TemporalCacheScope
    partitions: tuple[tuple[str, tuple[tuple[str, str], ...]], ...]

    def __post_init__(self) -> None:
        if type(self.scope) is not H2TemporalCacheScope or type(self.partitions) is not tuple:
            raise H2TemporalProofDAGInvariantViolation("cache scope/partitions invalid")
        if self.partitions != tuple(sorted(self.partitions)):
            raise H2TemporalProofDAGInvariantViolation("cache partitions are not canonical")
        seen: set[str] = set()
        for partition_id, rows in self.partitions:
            _cid(partition_id, "cache partition")
            if partition_id in seen or rows != tuple(sorted(rows)):
                raise H2TemporalProofDAGInvariantViolation("cache partition duplicate/order invalid")
            seen.add(partition_id)
            if len({key for key, _ in rows}) != len(rows):
                raise H2TemporalProofDAGInvariantViolation("cache partition contains duplicate keys")
            for key, entry in rows:
                _cid(key, "cache key")
                _cid(entry, "cache entry")

    @classmethod
    def from_mapping(
        cls,
        scope: H2TemporalCacheScope,
        partitions: Mapping[str, Mapping[str, str]],
    ) -> "H2TemporalProofCacheV1":
        return cls(
            scope,
            tuple(
                (partition_id, tuple(sorted(entries.items())))
                for partition_id, entries in sorted(partitions.items())
            ),
        )

    def _mapping(self) -> dict[str, dict[str, str]]:
        return {
            partition_id: dict(rows) for partition_id, rows in self.partitions
        }

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h2_temporal_proof_cache.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "scope": self.scope.value,
            "partitions": [
                {
                    "partition_id": partition_id,
                    "entries": [
                        {"node_key_id": key, "entry_id": entry}
                        for key, entry in rows
                    ],
                }
                for partition_id, rows in self.partitions
            ],
        }

    @property
    def cache_id(self) -> str:
        return _content_id("cache", self._payload())

    @property
    def state_id(self) -> str:
        return _cache_state_id(self.scope, self._mapping())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "cache_id": self.cache_id, "state_id": self.state_id}


@dataclass(frozen=True, slots=True)
class H2TemporalProofKindCountV1:
    family: str
    computed: int
    reused: int

    def __post_init__(self) -> None:
        if self.family not in tuple("UPCDEFGR"):
            raise H2TemporalProofDAGInvariantViolation("unknown temporal proof family")
        _integer(self.computed, "family computed")
        _integer(self.reused, "family reused")

    def to_document(self) -> dict[str, Any]:
        return {"family": self.family, "computed": self.computed, "reused": self.reused}


@dataclass(frozen=True, slots=True)
class H2TemporalProofWorkV1:
    scope: H2TemporalCacheScope
    computed: int
    reused: int
    grouped_counts: tuple[H2TemporalProofKindCountV1, ...]

    def __post_init__(self) -> None:
        if type(self.scope) is not H2TemporalCacheScope:
            raise H2TemporalProofDAGInvariantViolation("work scope substituted")
        _integer(self.computed, "work computed")
        _integer(self.reused, "work reused")
        if (
            type(self.grouped_counts) is not tuple
            or tuple(item.family for item in self.grouped_counts) != tuple("UPCDEFGR")
            or any(type(item) is not H2TemporalProofKindCountV1 for item in self.grouped_counts)
            or sum(item.computed for item in self.grouped_counts) != self.computed
            or sum(item.reused for item in self.grouped_counts) != self.reused
            or self.computed != EXPECTED_COMPUTES[self.scope.value]
            or self.reused != EXPECTED_REUSES[self.scope.value]
        ):
            raise H2TemporalProofDAGInvariantViolation("work vector/count golden changed")
        if self.scope is H2TemporalCacheScope.GLOBAL_STAGE_DAG and {
            item.family: (item.computed, item.reused) for item in self.grouped_counts
        } != EXPECTED_GLOBAL_GROUPED:
            raise H2TemporalProofDAGInvariantViolation("global grouped counts changed")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h2_temporal_proof_work.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "scope": self.scope.value,
            "computed": self.computed,
            "reused": self.reused,
            "grouped_counts": [item.to_document() for item in self.grouped_counts],
        }

    @property
    def work_id(self) -> str:
        return _content_id("work", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "work_id": self.work_id}


@dataclass(frozen=True, slots=True)
class H2TemporalProofPrefixV1:
    scope: H2TemporalCacheScope
    request_index: int
    computed: int
    reused: int

    def __post_init__(self) -> None:
        if type(self.scope) is not H2TemporalCacheScope:
            raise H2TemporalProofDAGInvariantViolation("prefix scope substituted")
        _integer(self.request_index, "prefix request", 1)
        _integer(self.computed, "prefix computed")
        _integer(self.reused, "prefix reused")
        if (
            self.request_index > 5
            or self.computed != EXPECTED_PREFIX_COMPUTES[self.scope.value][self.request_index - 1]
            or self.computed + self.reused != 11 * self.request_index
        ):
            raise H2TemporalProofDAGInvariantViolation("prefix golden changed")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h2_temporal_proof_prefix.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "scope": self.scope.value,
            "request_index": self.request_index,
            "computed": self.computed,
            "reused": self.reused,
        }

    @property
    def prefix_id(self) -> str:
        return _content_id("prefix", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "prefix_id": self.prefix_id}


@dataclass(frozen=True, slots=True)
class H2TemporalPlanChangeClosureV1:
    transition_index: int
    previous_schedule_code: str | None
    current_schedule_code: str
    changed_time_indices: tuple[int, ...]
    affected_slots: tuple[H2TemporalProofSlot, ...]

    def __post_init__(self) -> None:
        _integer(self.transition_index, "closure transition", 1)
        if self.transition_index > 5 or type(self.affected_slots) is not tuple:
            raise H2TemporalProofDAGInvariantViolation("closure transition invalid")
        expected = (
            (None, "A0A0", (0, 1), SLOT_ORDER),
            ("A0A0", "A0A1", (1,), (
                H2TemporalProofSlot.P1, H2TemporalProofSlot.P0,
                H2TemporalProofSlot.C1, H2TemporalProofSlot.D,
                H2TemporalProofSlot.E, H2TemporalProofSlot.F,
                H2TemporalProofSlot.G, H2TemporalProofSlot.R,
            )),
            ("A0A1", "A1A1", (0,), (
                H2TemporalProofSlot.P0, H2TemporalProofSlot.C0,
                H2TemporalProofSlot.C1, H2TemporalProofSlot.D,
                H2TemporalProofSlot.E, H2TemporalProofSlot.F,
                H2TemporalProofSlot.G, H2TemporalProofSlot.R,
            )),
            ("A1A1", "A1A0", (1,), (
                H2TemporalProofSlot.P1, H2TemporalProofSlot.P0,
                H2TemporalProofSlot.C1, H2TemporalProofSlot.D,
                H2TemporalProofSlot.E, H2TemporalProofSlot.F,
                H2TemporalProofSlot.G, H2TemporalProofSlot.R,
            )),
            ("A1A0", "A0A0", (0,), (
                H2TemporalProofSlot.P0, H2TemporalProofSlot.C0,
                H2TemporalProofSlot.C1, H2TemporalProofSlot.D,
                H2TemporalProofSlot.E, H2TemporalProofSlot.F,
                H2TemporalProofSlot.G, H2TemporalProofSlot.R,
            )),
        )[self.transition_index - 1]
        if (
            self.previous_schedule_code,
            self.current_schedule_code,
            self.changed_time_indices,
            self.affected_slots,
        ) != expected:
            raise H2TemporalProofDAGInvariantViolation("plan-change descendant closure changed")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h2_temporal_plan_change_closure.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "transition_index": self.transition_index,
            "previous_schedule_code": self.previous_schedule_code,
            "current_schedule_code": self.current_schedule_code,
            "changed_time_indices": list(self.changed_time_indices),
            "affected_slots": [item.value for item in self.affected_slots],
        }

    @property
    def closure_id(self) -> str:
        return _content_id("closure", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "closure_id": self.closure_id}


# Threshold-neutral live values.  They are deliberately not public cache
# artifacts; the content-addressed entries retain only exact digests and typed
# result semantics.  A retained runner owner is required to reuse a value.
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
class _UStage:
    time_index: int
    cell_upper: Mapping[str, Fraction]
    state_upper: Mapping[str, Fraction]
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
class _PStage:
    time_index: int
    table: Mapping[str, Any]
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
class _CStage:
    time_index: int
    next_reach: Mapping[str, Fraction]
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
    reachable_state_time_cell_count: int
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


def _u_stage_document(value: _UStage) -> dict[str, Any]:
    return {
        "time_index": value.time_index,
        "cell_upper": [
            {"cell_id": key, "reward_upper": _fdoc(item)}
            for key, item in sorted(value.cell_upper.items())
        ],
        "state_upper": [
            {"state_id": key, "reward_upper": _fdoc(item)}
            for key, item in sorted(value.state_upper.items())
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


def _p_stage_document(value: _PStage) -> dict[str, Any]:
    return {
        "time_index": value.time_index,
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
        ],
    }


def _c_stage_document(value: _CStage) -> dict[str, Any]:
    return {
        "time_index": value.time_index,
        "next_reach": [
            {"cell_id": key, "mass_upper": _fdoc(item)}
            for key, item in sorted(value.next_reach.items())
        ],
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
                "known_external_successor_mass": _fdoc(row.known_external_successor_mass),
                "reachable_unknown_mass_upper": _fdoc(row.reachable_unknown_mass_upper),
                "reachable_external_continuation_mass_upper": _fdoc(row.reachable_external_continuation_mass_upper),
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
        "normalized_distribution_regret": _fdoc(value.normalized_distribution_regret),
        "reachable_state_time_cell_count": value.reachable_state_time_cell_count,
        "support_metrics": [
            {
                "state_id": state_id,
                "cell_id": cell_id,
                "probability": _fdoc(probability),
                "unrestricted_upper": _fdoc(unrestricted),
                "policy_lower": _fdoc(policy_lower),
                "raw_regret": _fdoc(raw_regret),
                "normalized_regret": _fdoc(normalized),
            }
            for state_id, cell_id, probability, unrestricted, policy_lower, raw_regret, normalized
            in value.support_metrics
        ],
    }


def _value_document(slot: H2TemporalProofSlot, value: Any) -> dict[str, Any]:
    if slot in (H2TemporalProofSlot.U1, H2TemporalProofSlot.U0):
        return _u_stage_document(value)
    if slot in (H2TemporalProofSlot.P1, H2TemporalProofSlot.P0):
        return _p_stage_document(value)
    if slot in (H2TemporalProofSlot.C0, H2TemporalProofSlot.C1):
        return _c_stage_document(value)
    if slot is H2TemporalProofSlot.D:
        return _d_document(value)
    if slot is H2TemporalProofSlot.E:
        return {
            "support_certified": list(value.support_certified),
            "reward_certified": value.reward_certified,
        }
    if slot is H2TemporalProofSlot.F:
        return {"risk_certified": value.risk_certified}
    if slot is H2TemporalProofSlot.G:
        return {
            "external_row_indices": list(value.external_row_indices),
            "coverage_certified": value.coverage_certified,
        }
    if slot is H2TemporalProofSlot.R:
        return value.to_document()
    raise AssertionError(slot)


def _value_digest(slot: H2TemporalProofSlot, value: Any) -> str:
    return _content_id(
        "node_result",
        {
            "schema": "acfqp.h2_temporal_proof_node_result.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "slot": slot.value,
            "document": _value_document(slot, value),
        },
    )


def _compute_u_stage(
    model: QueryScopedPartialRAPMV3,
    thresholds: FrozenPartialAuditThresholdsV1,
    active_cells: Mapping[str, Any],
    time_index: int,
    parent: _UStage | None,
) -> _UStage:
    if (time_index == 1) != (parent is None):
        raise H2TemporalProofDAGInvariantViolation("U temporal parent order changed")
    weights = {item.name: item.weight for item in thresholds.reward_weights}
    per_step_lower, per_step_upper = audit_module._cap_interval(model, weights)
    return_upper = thresholds.return_bound_proof.return_upper
    active_ids = tuple(sorted(active_cells))
    state_to_cell = {
        state_id: cell_id
        for cell_id, cell in active_cells.items()
        for state_id in cell.member_state_ids
    }
    rows_by_state: dict[str, list[Any]] = {state_id: [] for state_id in state_to_cell}
    for row in model.ground_rows:
        if row.state_id in rows_by_state:
            rows_by_state[row.state_id].append(row)
    if any(not rows for rows in rows_by_state.values()):
        raise H2TemporalProofDAGInvariantViolation("U lacks complete action catalogues")
    remaining = 2 - time_index
    next_upper = {
        cell_id: Fraction(0) if parent is None else parent.cell_upper[cell_id]
        for cell_id in active_ids
    }
    outside = audit_module._outside_bound(
        remaining - 1, per_step_lower, per_step_upper, return_upper
    )
    state_upper: dict[str, Fraction] = {}
    proof_rows: list[_URow] = []
    for state_id in sorted(rows_by_state):
        action_values: list[Fraction] = []
        cell_id = state_to_cell[state_id]
        for row in sorted(rows_by_state[state_id], key=lambda item: item.ground_row_id):
            ambiguity = row.ambiguity
            _, upper = audit_module._reward_interval(ambiguity, weights)
            for destination, mass in ambiguity.known_successor_masses:
                upper += mass * (
                    outside.reward_upper
                    if destination == model.external_boundary_id
                    else next_upper[destination]
                )
            unknown = audit_module._validate_joint_simplex(ambiguity)
            if unknown:
                upper += unknown * max(
                    Fraction(0), outside.reward_upper,
                    *(next_upper[destination] for destination in active_ids),
                )
            upper = min(return_upper, upper)
            action_values.append(upper)
            proof_rows.append(
                _URow(time_index, remaining, state_id, cell_id, row.ground_row_id, row.ground_action_id, upper)
            )
        state_upper[state_id] = max(action_values)
    cell_upper = {
        cell_id: max(state_upper[state_id] for state_id in cell.member_state_ids)
        for cell_id, cell in active_cells.items()
    }
    return _UStage(
        time_index,
        cell_upper,
        state_upper,
        tuple(sorted(proof_rows, key=lambda row: (row.time_index, row.state_id, row.ground_row_id))),
    )


def _compute_p_stage(
    model: QueryScopedPartialRAPMV3,
    thresholds: FrozenPartialAuditThresholdsV1,
    active_cells: Mapping[str, Any],
    realizations: Mapping[tuple[str, str], tuple[Any, ...]],
    assignment: Mapping[str, str],
    time_index: int,
    parent: _PStage | None,
) -> _PStage:
    if (time_index == 1) != (parent is None):
        raise H2TemporalProofDAGInvariantViolation("P temporal parent order changed")
    weights = {item.name: item.weight for item in thresholds.reward_weights}
    per_step_lower, per_step_upper = audit_module._cap_interval(model, weights)
    return_upper = thresholds.return_bound_proof.return_upper
    active_ids = tuple(sorted(active_cells))
    remaining = 2 - time_index
    next_by_cell = {
        cell_id: (
            audit_module._Bound(Fraction(0), Fraction(0), Fraction(0), Fraction(0))
            if parent is None else parent.table[cell_id]
        )
        for cell_id in active_ids
    }
    outside = audit_module._outside_bound(
        remaining - 1, per_step_lower, per_step_upper, return_upper
    )
    table: dict[str, Any] = {}
    rows: list[_PRow] = []
    for cell_id in active_ids:
        action_id = assignment[cell_id]
        state_rows = realizations[(cell_id, action_id)]
        state_bounds = tuple(
            audit_module._realization_bound(
                item.ambiguity, next_by_cell, active_ids,
                model.external_boundary_id, outside, weights, return_upper,
            )
            for item in state_rows
        )
        bound = audit_module._Bound(
            min(item.reward_lower for item in state_bounds),
            max(item.reward_upper for item in state_bounds),
            min(item.failure_lower for item in state_bounds),
            max(item.failure_upper for item in state_bounds),
        )
        table[cell_id] = bound
        documents = tuple(item.ambiguity.to_document() for item in state_rows)
        rows.append(
            _PRow(
                time_index, remaining, cell_id, action_id,
                tuple(item.state_id for item in state_rows),
                tuple(sorted({row_id for item in state_rows for row_id in item.missing_ground_row_ids})),
                bound.reward_lower, bound.reward_upper, bound.failure_lower, bound.failure_upper,
                max(item.ambiguity.joint_simplex_constraint.unknown_atom_mass_sum for item in state_rows),
                any(
                    item.ambiguity.joint_simplex_constraint.unknown_atom_mass_sum > 0
                    or dict(item.ambiguity.known_successor_masses).get(model.external_boundary_id, Fraction(0)) > 0
                    for item in state_rows
                ),
                any(document != documents[0] for document in documents[1:]),
            )
        )
    return _PStage(time_index, table, tuple(sorted(rows, key=lambda row: (row.time_index, row.cell_id))))


def _compute_c_stage(
    model: QueryScopedPartialRAPMV3,
    thresholds: FrozenPartialAuditThresholdsV1,
    active_cells: Mapping[str, Any],
    realizations: Mapping[tuple[str, str], tuple[Any, ...]],
    state_to_cell: Mapping[str, str],
    assignment: Mapping[str, str],
    time_index: int,
    parent: _CStage | None,
) -> _CStage:
    if (time_index == 0) != (parent is None):
        raise H2TemporalProofDAGInvariantViolation("C temporal parent order changed")
    active_ids = tuple(sorted(active_cells))
    if parent is None:
        reach: dict[str, Fraction] = {}
        for item in thresholds.initial_state_distribution:
            cell_id = state_to_cell[item.state_id]
            reach[cell_id] = reach.get(cell_id, Fraction(0)) + item.probability
    else:
        reach = dict(parent.next_reach)
    remaining = 2 - time_index
    next_reach: dict[str, Fraction] = {}
    rows: list[_CRow] = []
    pairs: list[tuple[int, str]] = []
    for cell_id in sorted(reach):
        cell_mass = reach[cell_id]
        if not cell_mass:
            continue
        pairs.append((time_index, cell_id))
        action_id = assignment[cell_id]
        state_rows = realizations[(cell_id, action_id)]
        documents = tuple(item.ambiguity.to_document() for item in state_rows)
        disagreement = any(document != documents[0] for document in documents[1:])
        for item in state_rows:
            unknown = audit_module._validate_joint_simplex(item.ambiguity)
            known_external = dict(item.ambiguity.known_successor_masses).get(
                model.external_boundary_id, Fraction(0)
            )
            rows.append(
                _CRow(
                    time_index, remaining, item.state_id, cell_id, action_id,
                    item.support_ground_row_ids, item.observed_ground_row_ids,
                    item.missing_ground_row_ids, cell_mass, unknown, known_external,
                    cell_mass * unknown,
                    cell_mass * known_external if remaining > 1 else Fraction(0),
                    disagreement, item.ambiguity.is_singleton,
                )
            )
        if remaining > 1:
            for destination in active_ids:
                upper = max(
                    dict(item.ambiguity.known_successor_masses).get(destination, Fraction(0))
                    + audit_module._validate_joint_simplex(item.ambiguity)
                    for item in state_rows
                )
                if upper:
                    next_reach[destination] = min(
                        Fraction(1), next_reach.get(destination, Fraction(0)) + cell_mass * upper
                    )
    return _CStage(
        time_index, next_reach,
        tuple(sorted(rows, key=lambda row: (row.time_index, row.cell_id, row.state_id, row.action_id))),
        tuple(sorted(set(pairs))),
    )


def _compute_d(
    model: QueryScopedPartialRAPMV3,
    thresholds: FrozenPartialAuditThresholdsV1,
    active_cells: Mapping[str, Any],
    realizations: Mapping[tuple[str, str], tuple[Any, ...]],
    stage_maps: Mapping[int, Mapping[str, str]],
    state_to_cell: Mapping[str, str],
    u0: _UStage,
    p1: _PStage,
    p0: _PStage,
    c0: _CStage,
    c1: _CStage,
) -> _NeutralD:
    table = {
        (1, cell_id): bound for cell_id, bound in p1.table.items()
    } | {
        (0, cell_id): bound for cell_id, bound in p0.table.items()
    }
    initial_bounds = audit_module._build_initial_support_bounds(
        model, thresholds, active_cells, realizations, stage_maps, state_to_cell, table
    )
    return_upper = thresholds.return_bound_proof.return_upper
    unrestricted_upper = sum(
        (
            support.probability * u0.state_upper[support.state_id]
            for support in thresholds.initial_state_distribution
        ),
        Fraction(0),
    )
    root_reward_lower = sum(
        (
            support.probability * initial_bounds[support.state_id].reward_lower
            for support in thresholds.initial_state_distribution
        ),
        Fraction(0),
    )
    root_reward_upper = min(
        return_upper,
        sum(
            (
                support.probability * initial_bounds[support.state_id].reward_upper
                for support in thresholds.initial_state_distribution
            ),
            Fraction(0),
        ),
    )
    root_failure_lower = sum(
        (
            support.probability * initial_bounds[support.state_id].failure_lower
            for support in thresholds.initial_state_distribution
        ),
        Fraction(0),
    )
    root_failure_upper = sum(
        (
            support.probability * initial_bounds[support.state_id].failure_upper
            for support in thresholds.initial_state_distribution
        ),
        Fraction(0),
    )
    metrics = tuple(
        (
            support.state_id,
            state_to_cell[support.state_id],
            support.probability,
            u0.state_upper[support.state_id],
            initial_bounds[support.state_id].reward_lower,
            u0.state_upper[support.state_id] - initial_bounds[support.state_id].reward_lower,
            (
                u0.state_upper[support.state_id]
                - initial_bounds[support.state_id].reward_lower
            ) / return_upper,
        )
        for support in thresholds.initial_state_distribution
    )
    raw = unrestricted_upper - root_reward_lower
    reachable_count = len(set((*c0.reachable_pairs, *c1.reachable_pairs)))
    return _NeutralD(
        initial_bounds,
        unrestricted_upper,
        root_reward_lower,
        root_reward_upper,
        root_failure_lower,
        root_failure_upper,
        raw,
        raw / return_upper,
        reachable_count,
        metrics,
    )


def _materialize_root(
    model: QueryScopedPartialRAPMV3,
    thresholds: FrozenPartialAuditThresholdsV1,
    plan: FrozenContingentAbstractPlanV1,
    u1: _UStage,
    u0: _UStage,
    p1: _PStage,
    p0: _PStage,
    c0: _CStage,
    c1: _CStage,
    d: _NeutralD,
    e: _NeutralE,
    f: _NeutralF,
    g: _NeutralG,
) -> PartialSoundAuditResultV1:
    p_rows = tuple(sorted((*p0.rows, *p1.rows), key=lambda row: (row.time_index, row.cell_id)))
    u_rows = tuple(
        sorted((*u0.rows, *u1.rows), key=lambda row: (row.time_index, row.state_id, row.ground_row_id))
    )
    c_rows = tuple(
        sorted((*c0.rows, *c1.rows), key=lambda row: (row.time_index, row.cell_id, row.state_id, row.action_id))
    )
    policy_rows = tuple(
        PartialPolicyBoundRowV1(
            model.model_id, thresholds.thresholds_id, plan.plan_id,
            row.time_index, row.remaining_horizon, row.cell_id, row.action_id,
            row.representative_state_ids, row.missing_ground_row_ids,
            row.reward_lower, row.reward_upper, row.failure_lower, row.failure_upper,
            row.max_shared_unknown_mass, row.external_boundary_possible,
            row.representative_disagreement,
        )
        for row in p_rows
    )
    unrestricted_rows = tuple(
        UnrestrictedGroundUpperRowV1(
            model.model_id, thresholds.thresholds_id,
            row.time_index, row.remaining_horizon, row.state_id, row.cell_id,
            row.ground_row_id, row.ground_action_id, row.reward_upper,
        )
        for row in u_rows
    )
    obligations = tuple(
        StateActionTimeObligationV1(
            model.model_id, thresholds.thresholds_id, plan.plan_id,
            row.time_index, row.remaining_horizon, row.state_id, row.cell_id,
            row.action_id, row.support_ground_row_ids, row.observed_ground_row_ids,
            row.missing_ground_row_ids, row.reachable_cell_mass_upper,
            row.shared_unknown_mass, row.known_external_successor_mass,
            row.reachable_unknown_mass_upper,
            row.reachable_external_continuation_mass_upper,
            row.representative_disagreement, row.realization_singleton,
        )
        for row in c_rows
    )
    support_rows = tuple(
        InitialSupportPointRegretRowV1(
            model.model_id, thresholds.thresholds_id, plan.plan_id,
            thresholds.return_bound_proof.proof_id,
            state_id, cell_id, probability, unrestricted, policy_lower, raw_regret,
            thresholds.return_bound_proof.return_upper, normalized,
            thresholds.normalized_regret_tolerance, certified,
        )
        for (
            (state_id, cell_id, probability, unrestricted, policy_lower, raw_regret, normalized),
            certified,
        ) in zip(d.support_metrics, e.support_certified)
    )
    external_ids = tuple(
        sorted(obligations[index].obligation_id for index in g.external_row_indices)
    )
    reachable_pairs = tuple(sorted(set((*c0.reachable_pairs, *c1.reachable_pairs))))
    bounds = PartialFixedPlanRobustBoundsV1(
        model.model_id, thresholds.thresholds_id, plan.plan_id,
        thresholds.return_bound_proof.proof_id,
        policy_rows, unrestricted_rows, support_rows,
        d.unrestricted_upper, d.root_reward_lower, d.root_reward_upper,
        d.root_failure_lower, d.root_failure_upper,
        d.raw_distribution_regret, d.normalized_distribution_regret,
        thresholds.return_bound_proof.return_upper,
        thresholds.normalized_regret_tolerance, thresholds.risk_tolerance,
        e.reward_certified, f.risk_certified, g.coverage_certified,
        external_ids, d.reachable_state_time_cell_count,
    )
    if d.reachable_state_time_cell_count != len(reachable_pairs):
        raise H2TemporalProofDAGInvariantViolation("D/C reachable-pair dependency changed")
    if bounds.certified:
        reachable_set = set(reachable_pairs)
        certificate = PartialFixedPlanCertificateV1(
            model.model_id, thresholds.thresholds_id, plan.plan_id,
            bounds.bounds_id, bounds.return_bound_proof_id,
            tuple(sorted(item.obligation_id for item in obligations)),
            tuple(sorted(
                item.bound_row_id for item in policy_rows
                if (item.time_index, item.cell_id) in reachable_set
            )),
            tuple(sorted(item.support_point_regret_row_id for item in support_rows)),
            bounds.maximum_support_point_normalized_regret,
            bounds.normalized_regret_tolerance,
            bounds.policy_failure_upper, bounds.risk_tolerance,
            bounds.external_coverage_certified,
        )
        return PartialSoundAuditResultV1(
            model.model_id, thresholds.thresholds_id, plan.plan_id,
            bounds, obligations, PartialAuditOutcome.CERTIFIED_FIXED_PLAN,
            certificate, None,
        )
    external = tuple(item for item in obligations if item.obligation_id in set(external_ids))
    unresolved = tuple(
        item for item in obligations
        if item.unresolved_mass_upper > 0 or item.representative_disagreement
    )
    if external:
        earliest = min(item.time_index for item in external)
        frontier_rows = tuple(item for item in external if item.time_index == earliest)
        reason = FailedProofReason.EXTERNAL_COVERAGE_ESCAPE
    elif unresolved:
        earliest = min(item.time_index for item in unresolved)
        frontier_rows = tuple(item for item in unresolved if item.time_index == earliest)
        reason = FailedProofReason.UNRESOLVED_POLICY_PATH_DISTINCTION
    else:
        earliest = min(item.time_index for item in obligations)
        frontier_rows = tuple(item for item in obligations if item.time_index == earliest)
        reason = FailedProofReason.KNOWN_FIXED_PLAN_THRESHOLD_FAILURE
    frontier = PartialFailedProofFrontierV1(
        model.model_id, thresholds.thresholds_id, plan.plan_id, bounds.bounds_id,
        earliest, thresholds.horizon - earliest, frontier_rows,
        sum((item.unresolved_mass_upper for item in frontier_rows), Fraction(0)),
        not bounds.reward_obligation_certified,
        not bounds.risk_obligation_certified,
        not bounds.external_coverage_certified,
        reason,
    )
    return PartialSoundAuditResultV1(
        model.model_id, thresholds.thresholds_id, plan.plan_id,
        bounds, obligations, PartialAuditOutcome.FAILED_PROOF_FRONTIER,
        None, frontier,
    )


def _threshold_bound_row_count(result: PartialSoundAuditResultV1) -> int:
    bounds = result.robust_bounds
    # Every listed row directly binds thresholds_id and/or contingent_plan_id.
    return (
        len(bounds.rows)
        + len(bounds.unrestricted_rows)
        + len(bounds.support_point_regret_rows)
        + len(result.proof_obligations)
    )


@dataclass(frozen=True, slots=True)
class H2TemporalPlanProposalV1:
    protocol_id: str
    source_result_id: str
    partial_model_id: str
    thresholds_id: str
    candidate_receipt_ids: tuple[str, ...]
    candidate_summaries: tuple[PartialPlannerCandidateSummaryV1, ...]
    selection_mode: PartialModelPlannerSelectionMode
    selected_gray_plan_id: str
    selected_plan: FrozenContingentAbstractPlanV1
    selected_semantic_schedule_key: tuple[int, ...]
    selection_rule: str = "V0047_NUMERIC_GATE_THEN_SEMANTIC_LABEL_LEXICOGRAPHIC_V1"

    def __post_init__(self) -> None:
        for name in (
            "protocol_id", "source_result_id", "partial_model_id", "thresholds_id",
            "selected_gray_plan_id",
        ):
            _cid(getattr(self, name), f"plan proposal {name}")
        if type(self.candidate_receipt_ids) is not tuple or len(self.candidate_receipt_ids) != 4:
            raise H2TemporalProofDAGInvariantViolation("selection requires four candidate roots")
        for value in self.candidate_receipt_ids:
            _cid(value, "candidate root receipt")
        if (
            type(self.candidate_summaries) is not tuple
            or len(self.candidate_summaries) != 4
            or any(type(item) is not PartialPlannerCandidateSummaryV1 for item in self.candidate_summaries)
            or tuple(item.contingent_plan_id for item in self.candidate_summaries)
            != tuple(sorted({item.contingent_plan_id for item in self.candidate_summaries}))
            or any(
                item.partial_model_id != self.partial_model_id
                or item.thresholds_id != self.thresholds_id
                for item in self.candidate_summaries
            )
            or type(self.selection_mode) is not PartialModelPlannerSelectionMode
            or type(self.selected_plan) is not FrozenContingentAbstractPlanV1
            or self.selected_plan.plan_id != EXPECTED_GRAY_PLAN_IDS[0]
            or self.selected_plan.partial_model_id != self.partial_model_id
            or not self.selected_semantic_schedule_key
            or self.selection_rule
            != "V0047_NUMERIC_GATE_THEN_SEMANTIC_LABEL_LEXICOGRAPHIC_V1"
        ):
            raise H2TemporalProofDAGInvariantViolation("numeric/semantic H2 selection changed")
        mode, numeric_selected = _selected_summary(self.candidate_summaries)
        selected_summary = next(
            (
                item for item in self.candidate_summaries
                if item.contingent_plan_id == self.selected_plan.plan_id
            ),
            None,
        )
        if (
            mode is not self.selection_mode
            or selected_summary is None
            or multistep_module._selection_numeric_key(mode, selected_summary)
            != multistep_module._selection_numeric_key(mode, numeric_selected)
        ):
            raise H2TemporalProofDAGInvariantViolation(
                "plan proposal does not satisfy the unchanged numeric gate"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h2_temporal_plan_selection_proposal.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "protocol_id": self.protocol_id,
            "source_result_id": self.source_result_id,
            "partial_model_id": self.partial_model_id,
            "thresholds_id": self.thresholds_id,
            "candidate_receipt_ids": list(self.candidate_receipt_ids),
            "candidate_summaries": [item.to_document() for item in self.candidate_summaries],
            "selection_mode": self.selection_mode.value,
            "selected_gray_plan_id": self.selected_gray_plan_id,
            "selected_plan": self.selected_plan.to_document(),
            "selected_semantic_schedule_key": list(self.selected_semantic_schedule_key),
            "selection_rule": self.selection_rule,
        }

    @property
    def result_id(self) -> str:
        return _content_id("selection", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "result_id": self.result_id}


def _fraction_text(value: Fraction) -> str:
    return f"{value.numerator}/{value.denominator}"


def _facet_digest(name: str, document: Any) -> str:
    return _content_id(
        "node_result",
        {
            "schema": "acfqp.h2_temporal_consumed_facet.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "facet": name,
            "document": document,
        },
    )


def _identity_facets(thresholds: FrozenPartialAuditThresholdsV1) -> dict[str, str]:
    return {
        "reward_weights_digest": _facet_digest(
            "reward_weights", [item.to_document() for item in thresholds.reward_weights]
        ),
        "initial_distribution_digest": _facet_digest(
            "initial_distribution",
            [item.to_document() for item in thresholds.initial_state_distribution],
        ),
        "return_bound_proof_id": thresholds.return_bound_proof.proof_id,
    }


def _result_semantics(slot: H2TemporalProofSlot) -> str:
    return {
        H2TemporalProofSlot.U1: "STAGE_LOCAL_UNRESTRICTED_BELLMAN_T1",
        H2TemporalProofSlot.U0: "STAGE_LOCAL_UNRESTRICTED_BELLMAN_T0",
        H2TemporalProofSlot.P1: "STAGE_LOCAL_FIXED_POLICY_BELLMAN_T1",
        H2TemporalProofSlot.P0: "STAGE_LOCAL_FIXED_POLICY_BELLMAN_T0",
        H2TemporalProofSlot.C0: "STAGE_LOCAL_FORWARD_REACHABILITY_T0",
        H2TemporalProofSlot.C1: "STAGE_LOCAL_FORWARD_REACHABILITY_T1",
        H2TemporalProofSlot.D: "ROOT_SUPPORT_VALUE_RISK_METRICS",
        H2TemporalProofSlot.E: "REGRET_THRESHOLD_VERDICT",
        H2TemporalProofSlot.F: "RISK_THRESHOLD_VERDICT",
        H2TemporalProofSlot.G: "EXTERNAL_COVERAGE_VERDICT",
        H2TemporalProofSlot.R: "FULL_IDENTITY_LEGACY_V1_AUDIT_ROOT",
    }[slot]


def _partition_id(
    scope: H2TemporalCacheScope,
    protocol_id: str,
    request: H2TemporalProofRequestV1,
) -> str:
    if scope is H2TemporalCacheScope.REQUEST_RESET:
        discriminator = request.request_id
    elif scope is H2TemporalCacheScope.EXACT_PLAN_PARTITIONED:
        discriminator = request.contingent_plan_id
    else:
        discriminator = protocol_id
    return _content_id(
        "cache_state",
        {
            "schema": "acfqp.h2_temporal_cache_partition.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "scope": scope.value,
            "discriminator": discriminator,
        },
    )


class _ArmRuntime:
    def __init__(
        self,
        scope: H2TemporalCacheScope,
        semantics: H2TemporalProofDAGSemanticsV1,
        protocol: H2TemporalProofDAGProtocolV1,
        model: QueryScopedPartialRAPMV3,
        thresholds: FrozenPartialAuditThresholdsV1,
    ) -> None:
        self.scope = scope
        self.semantics = semantics
        self.protocol = protocol
        self.model = model
        self.thresholds = thresholds
        self.partitions: dict[str, dict[str, str]] = {}
        self.live_values: dict[tuple[str, str], Any] = {}
        self.entries: dict[str, H2TemporalProofNodeEntryV1] = {}
        self.resolutions: list[H2TemporalProofResolutionV1] = []
        self.receipts: list[H2TemporalProofRequestReceiptV1] = []

    def resolve(
        self,
        request: H2TemporalProofRequestV1,
        slot: H2TemporalProofSlot,
        key: H2TemporalProofNodeKeyV1,
        factory: Any,
    ) -> tuple[H2TemporalProofNodeEntryV1, Any]:
        partition_id = _partition_id(self.scope, self.protocol.protocol_id, request)
        pre = _cache_state_id(self.scope, self.partitions)
        partition = self.partitions.get(partition_id)
        if partition is None:
            partition = {}
        existing = partition.get(key.node_key_id)
        if existing is None:
            value = factory()
            row_count = _threshold_bound_row_count(value) if slot is H2TemporalProofSlot.R else 0
            entry = H2TemporalProofNodeEntryV1(
                key, _value_digest(slot, value), _result_semantics(slot), row_count
            )
            if partition_id not in self.partitions:
                self.partitions[partition_id] = partition
            partition[key.node_key_id] = entry.entry_id
            self.live_values[(partition_id, key.node_key_id)] = value
            self.entries[entry.entry_id] = entry
            outcome = H2TemporalResolutionOutcome.COMPUTED
        else:
            entry = self.entries[existing]
            value = self.live_values[(partition_id, key.node_key_id)]
            outcome = H2TemporalResolutionOutcome.REUSED
        post = _cache_state_id(self.scope, self.partitions)
        resolution = H2TemporalProofResolutionV1(
            len(self.resolutions) + 1,
            request.request_id,
            slot,
            partition_id,
            key.node_key_id,
            entry.entry_id,
            outcome,
            pre,
            post,
        )
        self.resolutions.append(resolution)
        return entry, value


def _terms(**values: str) -> tuple[tuple[str, str], ...]:
    return tuple(sorted(values.items()))


def _node_key(
    runtime: _ArmRuntime,
    request: H2TemporalProofRequestV1,
    slot: H2TemporalProofSlot,
    stage_id: str | None,
    parent_entries: tuple[H2TemporalProofNodeEntryV1, ...],
    facets: Mapping[str, str],
) -> H2TemporalProofNodeKeyV1:
    if slot in (H2TemporalProofSlot.U1, H2TemporalProofSlot.U0):
        terms = _terms(
            formula_id="STAGE_LOCAL_UNRESTRICTED_BELLMAN_V1",
            return_bound_proof_id=facets["return_bound_proof_id"],
            reward_weights_digest=facets["reward_weights_digest"],
        )
    elif slot in (H2TemporalProofSlot.P1, H2TemporalProofSlot.P0):
        terms = _terms(
            formula_id="STAGE_LOCAL_FIXED_POLICY_BELLMAN_V1",
            return_bound_proof_id=facets["return_bound_proof_id"],
            reward_weights_digest=facets["reward_weights_digest"],
        )
    elif slot is H2TemporalProofSlot.C0:
        terms = _terms(
            formula_id="STAGE_LOCAL_FORWARD_REACHABILITY_V1",
            initial_distribution_digest=facets["initial_distribution_digest"],
        )
    elif slot is H2TemporalProofSlot.C1:
        terms = _terms(formula_id="STAGE_LOCAL_FORWARD_REACHABILITY_V1")
    elif slot is H2TemporalProofSlot.D:
        terms = _terms(
            formula_id="ROOT_SUPPORT_VALUE_RISK_METRICS_V1",
            initial_distribution_digest=facets["initial_distribution_digest"],
            return_bound_proof_id=facets["return_bound_proof_id"],
            reward_weights_digest=facets["reward_weights_digest"],
        )
    elif slot is H2TemporalProofSlot.E:
        terms = _terms(
            formula_id="REGRET_THRESHOLD_VERDICT_V1",
            normalized_regret_tolerance=_fraction_text(runtime.thresholds.normalized_regret_tolerance),
        )
    elif slot is H2TemporalProofSlot.F:
        terms = _terms(
            formula_id="RISK_THRESHOLD_VERDICT_V1",
            risk_tolerance=_fraction_text(runtime.thresholds.risk_tolerance),
        )
    elif slot is H2TemporalProofSlot.G:
        terms = _terms(formula_id="EXTERNAL_COVERAGE_VERDICT_V1")
    else:
        terms = _terms(
            formula_id="FULL_IDENTITY_LEGACY_V1_ROOT_V1",
            gray_plan_id=request.gray_plan_id,
            plan_id=request.contingent_plan_id,
            planner_result_id=(
                request.planner_result_id
                if request.planner_result_id is not None
                else "NOT_APPLICABLE:CANDIDATE_PRECEDES_SELECTION"
            ),
            request_id=request.request_id,
            role=request.role.value,
            source_result_id=request.source_result_id,
            thresholds_id=request.thresholds_id,
        )
    time_index = {
        H2TemporalProofSlot.U1: 1, H2TemporalProofSlot.P1: 1,
        H2TemporalProofSlot.C1: 1,
        H2TemporalProofSlot.U0: 0, H2TemporalProofSlot.P0: 0,
        H2TemporalProofSlot.C0: 0,
    }.get(slot)
    return H2TemporalProofNodeKeyV1(
        slot,
        runtime.semantics.semantics_id,
        runtime.model.model_id,
        time_index,
        stage_id,
        tuple(item.entry_id for item in parent_entries),
        terms,
    )


def _run_request(
    runtime: _ArmRuntime,
    request: H2TemporalProofRequestV1,
    gray_plan: H2TemporalGrayPlanV1,
) -> H2TemporalProofRequestReceiptV1:
    plan = gray_plan.contingent_plan
    active_cells, realizations, stage_maps, state_to_cell = audit_module._validate_inputs(
        runtime.model, runtime.thresholds, plan
    )
    facets = _identity_facets(runtime.thresholds)
    start = len(runtime.resolutions)
    entries: dict[H2TemporalProofSlot, H2TemporalProofNodeEntryV1] = {}
    values: dict[H2TemporalProofSlot, Any] = {}

    def resolve(
        slot: H2TemporalProofSlot,
        stage_id: str | None,
        parents: tuple[H2TemporalProofSlot, ...],
        factory: Any,
    ) -> None:
        parent_entries = tuple(entries[item] for item in parents)
        key = _node_key(runtime, request, slot, stage_id, parent_entries, facets)
        entries[slot], values[slot] = runtime.resolve(request, slot, key, factory)

    resolve(
        H2TemporalProofSlot.U1, None, (),
        lambda: _compute_u_stage(runtime.model, runtime.thresholds, active_cells, 1, None),
    )
    resolve(
        H2TemporalProofSlot.U0, None, (H2TemporalProofSlot.U1,),
        lambda: _compute_u_stage(
            runtime.model, runtime.thresholds, active_cells, 0,
            values[H2TemporalProofSlot.U1],
        ),
    )
    resolve(
        H2TemporalProofSlot.P1, gray_plan.stage_assignment_ids[1], (),
        lambda: _compute_p_stage(
            runtime.model, runtime.thresholds, active_cells, realizations,
            stage_maps[1], 1, None,
        ),
    )
    resolve(
        H2TemporalProofSlot.P0, gray_plan.stage_assignment_ids[0],
        (H2TemporalProofSlot.P1,),
        lambda: _compute_p_stage(
            runtime.model, runtime.thresholds, active_cells, realizations,
            stage_maps[0], 0, values[H2TemporalProofSlot.P1],
        ),
    )
    resolve(
        H2TemporalProofSlot.C0, gray_plan.stage_assignment_ids[0], (),
        lambda: _compute_c_stage(
            runtime.model, runtime.thresholds, active_cells, realizations,
            state_to_cell, stage_maps[0], 0, None,
        ),
    )
    resolve(
        H2TemporalProofSlot.C1, gray_plan.stage_assignment_ids[1],
        (H2TemporalProofSlot.C0,),
        lambda: _compute_c_stage(
            runtime.model, runtime.thresholds, active_cells, realizations,
            state_to_cell, stage_maps[1], 1, values[H2TemporalProofSlot.C0],
        ),
    )
    resolve(
        H2TemporalProofSlot.D, None,
        (
            H2TemporalProofSlot.U0, H2TemporalProofSlot.P0,
            H2TemporalProofSlot.C0, H2TemporalProofSlot.C1,
        ),
        lambda: _compute_d(
            runtime.model, runtime.thresholds, active_cells, realizations,
            stage_maps, state_to_cell,
            values[H2TemporalProofSlot.U0],
            values[H2TemporalProofSlot.P1],
            values[H2TemporalProofSlot.P0],
            values[H2TemporalProofSlot.C0],
            values[H2TemporalProofSlot.C1],
        ),
    )
    resolve(
        H2TemporalProofSlot.E, None, (H2TemporalProofSlot.D,),
        lambda: _NeutralE(
            tuple(
                item[-1] <= runtime.thresholds.normalized_regret_tolerance
                for item in values[H2TemporalProofSlot.D].support_metrics
            ),
            all(
                item[-1] <= runtime.thresholds.normalized_regret_tolerance
                for item in values[H2TemporalProofSlot.D].support_metrics
            ),
        ),
    )
    resolve(
        H2TemporalProofSlot.F, None, (H2TemporalProofSlot.D,),
        lambda: _NeutralF(
            values[H2TemporalProofSlot.D].root_failure_upper
            <= runtime.thresholds.risk_tolerance
        ),
    )

    def compute_g() -> _NeutralG:
        rows = tuple(sorted(
            (*values[H2TemporalProofSlot.C0].rows, *values[H2TemporalProofSlot.C1].rows),
            key=lambda row: (row.time_index, row.cell_id, row.state_id, row.action_id),
        ))
        indices = tuple(
            index for index, row in enumerate(rows)
            if row.remaining_horizon > 1
            and (
                row.reachable_external_continuation_mass_upper > 0
                or row.reachable_unknown_mass_upper > 0
            )
        )
        return _NeutralG(indices, not indices)

    resolve(
        H2TemporalProofSlot.G, None,
        (H2TemporalProofSlot.C0, H2TemporalProofSlot.C1), compute_g,
    )
    resolve(
        H2TemporalProofSlot.R, None, LOWER_SLOT_ORDER,
        lambda: _materialize_root(
            runtime.model, runtime.thresholds, plan,
            values[H2TemporalProofSlot.U1], values[H2TemporalProofSlot.U0],
            values[H2TemporalProofSlot.P1], values[H2TemporalProofSlot.P0],
            values[H2TemporalProofSlot.C0], values[H2TemporalProofSlot.C1],
            values[H2TemporalProofSlot.D], values[H2TemporalProofSlot.E],
            values[H2TemporalProofSlot.F], values[H2TemporalProofSlot.G],
        ),
    )
    current = tuple(runtime.resolutions[start:])
    if tuple(item.logical_slot for item in current) != SLOT_ORDER:
        raise H2TemporalProofDAGInvariantViolation("runtime did not execute the 11-slot topology")
    receipt = H2TemporalProofRequestReceiptV1(
        request,
        gray_plan,
        tuple(item.resolution_id for item in current),
        entries[H2TemporalProofSlot.R].entry_id,
        values[H2TemporalProofSlot.R],
    )
    runtime.receipts.append(receipt)
    return receipt


def _build_selection(
    protocol: H2TemporalProofDAGProtocolV1,
    candidate_receipts: tuple[H2TemporalProofRequestReceiptV1, ...],
    thresholds: FrozenPartialAuditThresholdsV1,
) -> H2TemporalPlanProposalV1:
    if len(candidate_receipts) != 4:
        raise H2TemporalProofDAGInvariantViolation("selection requires exactly four candidate roots")
    summary_by_plan = {
        receipt.gray_plan.contingent_plan.plan_id: _candidate_summary(
            thresholds, receipt.gray_plan.contingent_plan, receipt.audit_result
        )
        for receipt in candidate_receipts
    }
    summaries = tuple(sorted(summary_by_plan.values(), key=lambda item: item.contingent_plan_id))
    mode, provisional = _selected_summary(summaries)
    numeric = multistep_module._selection_numeric_key(mode, provisional)
    gray_by_plan = {
        item.contingent_plan.plan_id: item for item in protocol.gray_plans
    }
    tied = tuple(
        item for item in summaries
        if multistep_module._selection_numeric_key(mode, item) == numeric
    )
    selected_summary = min(
        tied,
        key=lambda item: (
            gray_by_plan[item.contingent_plan_id].semantic_schedule_key,
            item.contingent_plan_id,
        ),
    )
    selected_gray = gray_by_plan[selected_summary.contingent_plan_id]
    if selected_gray.contingent_plan.plan_id != EXPECTED_GRAY_PLAN_IDS[0]:
        raise H2TemporalProofDAGInvariantViolation("registered V0-047 tie rule selected another plan")
    return H2TemporalPlanProposalV1(
        protocol.protocol_id,
        protocol.source_result_id,
        protocol.source_final_model_id,
        protocol.source_thresholds_id,
        tuple(item.receipt_id for item in candidate_receipts),
        summaries,
        mode,
        selected_gray.gray_plan_id,
        selected_gray.contingent_plan,
        selected_gray.semantic_schedule_key,
    )


def _make_request(
    protocol: H2TemporalProofDAGProtocolV1,
    gray: H2TemporalGrayPlanV1,
    index: int,
    planner_result_id: str | None,
) -> H2TemporalProofRequestV1:
    return H2TemporalProofRequestV1(
        index,
        (
            H2TemporalProofRole.CANDIDATE_RANKING_AUDIT
            if index <= 4
            else H2TemporalProofRole.INDEPENDENT_SELECTED_PLAN_CERTIFICATE
        ),
        protocol.protocol_id,
        gray.gray_plan_id,
        planner_result_id,
        gray.contingent_plan.plan_id,
        protocol.source_result_id,
        protocol.source_final_model_id,
        protocol.source_thresholds_id,
    )


def _derive_work(
    scope: H2TemporalCacheScope,
    resolutions: tuple[H2TemporalProofResolutionV1, ...],
) -> H2TemporalProofWorkV1:
    rows: list[H2TemporalProofKindCountV1] = []
    for family in tuple("UPCDEFGR"):
        matching = tuple(item for item in resolutions if _slot_family(item.logical_slot) == family)
        rows.append(
            H2TemporalProofKindCountV1(
                family,
                sum(item.outcome is H2TemporalResolutionOutcome.COMPUTED for item in matching),
                sum(item.outcome is H2TemporalResolutionOutcome.REUSED for item in matching),
            )
        )
    return H2TemporalProofWorkV1(
        scope,
        sum(item.outcome is H2TemporalResolutionOutcome.COMPUTED for item in resolutions),
        sum(item.outcome is H2TemporalResolutionOutcome.REUSED for item in resolutions),
        tuple(rows),
    )


def _derive_prefixes(
    scope: H2TemporalCacheScope,
    resolutions: tuple[H2TemporalProofResolutionV1, ...],
) -> tuple[H2TemporalProofPrefixV1, ...]:
    result: list[H2TemporalProofPrefixV1] = []
    for request_index in range(1, 6):
        prefix = resolutions[: 11 * request_index]
        result.append(
            H2TemporalProofPrefixV1(
                scope,
                request_index,
                sum(item.outcome is H2TemporalResolutionOutcome.COMPUTED for item in prefix),
                sum(item.outcome is H2TemporalResolutionOutcome.REUSED for item in prefix),
            )
        )
    return tuple(result)


@dataclass(frozen=True, slots=True)
class H2TemporalProofDAGArmV1:
    scope: H2TemporalCacheScope
    semantics_id: str
    protocol_id: str
    expected_reuse_manifest_id: str
    request_receipts: tuple[H2TemporalProofRequestReceiptV1, ...]
    resolutions: tuple[H2TemporalProofResolutionV1, ...]
    entry_catalogue: tuple[H2TemporalProofNodeEntryV1, ...]
    final_cache: H2TemporalProofCacheV1
    aggregate_work: H2TemporalProofWorkV1
    prefixes: tuple[H2TemporalProofPrefixV1, ...]
    initial_cache_empty: bool = True

    def __post_init__(self) -> None:
        if type(self.scope) is not H2TemporalCacheScope:
            raise H2TemporalProofDAGInvariantViolation("arm scope substituted")
        for value, name in (
            (self.semantics_id, "arm semantics"),
            (self.protocol_id, "arm protocol"),
            (self.expected_reuse_manifest_id, "arm reuse manifest"),
        ):
            _cid(value, name)
        if (
            type(self.request_receipts) is not tuple
            or len(self.request_receipts) != 5
            or any(type(item) is not H2TemporalProofRequestReceiptV1 for item in self.request_receipts)
            or type(self.resolutions) is not tuple
            or len(self.resolutions) != 55
            or any(type(item) is not H2TemporalProofResolutionV1 for item in self.resolutions)
            or type(self.entry_catalogue) is not tuple
            or any(type(item) is not H2TemporalProofNodeEntryV1 for item in self.entry_catalogue)
            or type(self.final_cache) is not H2TemporalProofCacheV1
            or self.final_cache.scope is not self.scope
            or type(self.aggregate_work) is not H2TemporalProofWorkV1
            or self.aggregate_work.scope is not self.scope
            or type(self.prefixes) is not tuple
            or len(self.prefixes) != 5
            or self.initial_cache_empty is not True
        ):
            raise H2TemporalProofDAGInvariantViolation("arm typed cardinality changed")
        _validate_arm_trace(self)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h2_temporal_proof_dag_arm.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "scope": self.scope.value,
            "semantics_id": self.semantics_id,
            "protocol_id": self.protocol_id,
            "expected_reuse_manifest_id": self.expected_reuse_manifest_id,
            "request_receipts": [item.to_document() for item in self.request_receipts],
            "resolutions": [item.to_document() for item in self.resolutions],
            "entry_catalogue": [item.to_document() for item in self.entry_catalogue],
            "final_cache": self.final_cache.to_document(),
            "aggregate_work": self.aggregate_work.to_document(),
            "prefixes": [item.to_document() for item in self.prefixes],
            "initial_cache_empty": self.initial_cache_empty,
        }

    @property
    def arm_id(self) -> str:
        return _content_id("arm", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "arm_id": self.arm_id}


def _validate_arm_trace(arm: H2TemporalProofDAGArmV1) -> None:
    if tuple(item.sequence_number for item in arm.resolutions) != tuple(range(1, 56)):
        raise H2TemporalProofDAGInvariantViolation("resolution sequence is not contiguous")
    entry_by_id = {item.entry_id: item for item in arm.entry_catalogue}
    if len(entry_by_id) != len(arm.entry_catalogue):
        raise H2TemporalProofDAGInvariantViolation("entry catalogue contains duplicate IDs")
    partitions: dict[str, dict[str, str]] = {}
    expected_parents = {
        H2TemporalProofSlot.U1: (),
        H2TemporalProofSlot.U0: (H2TemporalProofSlot.U1,),
        H2TemporalProofSlot.P1: (),
        H2TemporalProofSlot.P0: (H2TemporalProofSlot.P1,),
        H2TemporalProofSlot.C0: (),
        H2TemporalProofSlot.C1: (H2TemporalProofSlot.C0,),
        H2TemporalProofSlot.D: (
            H2TemporalProofSlot.U0, H2TemporalProofSlot.P0,
            H2TemporalProofSlot.C0, H2TemporalProofSlot.C1,
        ),
        H2TemporalProofSlot.E: (H2TemporalProofSlot.D,),
        H2TemporalProofSlot.F: (H2TemporalProofSlot.D,),
        H2TemporalProofSlot.G: (H2TemporalProofSlot.C0, H2TemporalProofSlot.C1),
        H2TemporalProofSlot.R: LOWER_SLOT_ORDER,
    }
    for request_offset, receipt in enumerate(arm.request_receipts):
        group = arm.resolutions[11 * request_offset : 11 * (request_offset + 1)]
        if (
            tuple(item.logical_slot for item in group) != SLOT_ORDER
            or tuple(item.resolution_id for item in group) != receipt.resolution_ids
            or any(item.request_id != receipt.request.request_id for item in group)
        ):
            raise H2TemporalProofDAGInvariantViolation("receipt/resolution topology changed")
        group_entries: dict[H2TemporalProofSlot, H2TemporalProofNodeEntryV1] = {}
        for resolution in group:
            pre = _cache_state_id(arm.scope, partitions)
            if resolution.pre_cache_state_id != pre:
                raise H2TemporalProofDAGInvariantViolation("pre-cache state replay mismatch")
            partition = partitions.get(resolution.partition_id)
            if partition is None:
                partition = {}
            entry = entry_by_id.get(resolution.entry_id)
            if (
                entry is None
                or entry.key.node_key_id != resolution.node_key_id
                or entry.key.slot is not resolution.logical_slot
                or entry.result_semantics != _result_semantics(resolution.logical_slot)
            ):
                raise H2TemporalProofDAGInvariantViolation("resolution entry/key/slot mismatch")
            expected_parent_ids = tuple(
                group_entries[parent].entry_id
                for parent in expected_parents[resolution.logical_slot]
            )
            if entry.key.ordered_parent_entry_ids != expected_parent_ids:
                raise H2TemporalProofDAGInvariantViolation("ordered parent topology mismatch")
            existing = partition.get(resolution.node_key_id)
            if resolution.outcome is H2TemporalResolutionOutcome.COMPUTED:
                if existing is not None:
                    raise H2TemporalProofDAGInvariantViolation("computed node already existed")
                if resolution.partition_id not in partitions:
                    partitions[resolution.partition_id] = partition
                partition[resolution.node_key_id] = resolution.entry_id
            elif existing != resolution.entry_id:
                raise H2TemporalProofDAGInvariantViolation("reuse lacks exact prior entry")
            post = _cache_state_id(arm.scope, partitions)
            if resolution.post_cache_state_id != post:
                raise H2TemporalProofDAGInvariantViolation("post-cache state replay mismatch")
            group_entries[resolution.logical_slot] = entry
        root = group_entries[H2TemporalProofSlot.R]
        if (
            receipt.root_entry_id != root.entry_id
            or root.result_digest != _value_digest(H2TemporalProofSlot.R, receipt.audit_result)
            or root.threshold_bound_v1_row_count != _threshold_bound_row_count(receipt.audit_result)
            or any(
                group_entries[slot].threshold_bound_v1_row_count != 0
                for slot in LOWER_SLOT_ORDER
            )
        ):
            raise H2TemporalProofDAGInvariantViolation("R row materialization/count mismatch")
    expected_cache = H2TemporalProofCacheV1.from_mapping(arm.scope, partitions)
    if expected_cache.to_document() != arm.final_cache.to_document():
        raise H2TemporalProofDAGInvariantViolation("final cache replay mismatch")
    if _derive_work(arm.scope, arm.resolutions).to_document() != arm.aggregate_work.to_document():
        raise H2TemporalProofDAGInvariantViolation("work replay mismatch")
    if tuple(item.to_document() for item in _derive_prefixes(arm.scope, arm.resolutions)) != tuple(
        item.to_document() for item in arm.prefixes
    ):
        raise H2TemporalProofDAGInvariantViolation("prefix replay mismatch")
    used = {item.entry_id for item in arm.resolutions}
    if used != set(entry_by_id):
        raise H2TemporalProofDAGInvariantViolation("entry catalogue contains unused/missing entries")


def _freeze_arm(runtime: _ArmRuntime, manifest_id: str) -> H2TemporalProofDAGArmV1:
    resolutions = tuple(runtime.resolutions)
    return H2TemporalProofDAGArmV1(
        runtime.scope,
        runtime.semantics.semantics_id,
        runtime.protocol.protocol_id,
        manifest_id,
        tuple(runtime.receipts),
        resolutions,
        tuple(sorted(runtime.entries.values(), key=lambda item: item.entry_id)),
        H2TemporalProofCacheV1.from_mapping(runtime.scope, runtime.partitions),
        _derive_work(runtime.scope, resolutions),
        _derive_prefixes(runtime.scope, resolutions),
    )


def _validate_manifest_arm(
    manifest: H2TemporalExpectedReuseManifestV1,
    arm: H2TemporalProofDAGArmV1,
) -> None:
    expected = dict(manifest.expected_outcomes)[arm.scope.value]
    actual = tuple(
        tuple(
            item.outcome.value
            for item in arm.resolutions[index * 11 : (index + 1) * 11]
        )
        for index in range(5)
    )
    if actual != expected:
        raise H2TemporalProofDAGInvariantViolation(
            "actual cache outcomes differ from the preregistered reuse manifest"
        )


_H2_TEMPORAL_EXECUTION_AUTHORITY = object()


@dataclass(frozen=True, slots=True)
class H2TemporalProofDAGExecutionV1:
    source_result_id: str
    cache_scope: H2TemporalCacheScope
    semantics: H2TemporalProofDAGSemanticsV1
    protocol: H2TemporalProofDAGProtocolV1
    expected_reuse_manifest: H2TemporalExpectedReuseManifestV1
    plan_proposal: H2TemporalPlanProposalV1
    arm: H2TemporalProofDAGArmV1
    plan_change_closures: tuple[H2TemporalPlanChangeClosureV1, ...]
    initial_cache_empty: bool
    _authority: object = field(repr=False, compare=False)
    _instance_mint: RuntimeAuthorityMintV1 | None = field(
        default=None, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        if self._authority is not _H2_TEMPORAL_EXECUTION_AUTHORITY:
            raise H2TemporalProofDAGInvariantViolation(
                "H2 temporal execution was not minted by its trusted runner"
            )
        if self._instance_mint is not None:
            try:
                self._instance_mint.validate_construction(
                    self,
                    issuer=_H2_TEMPORAL_EXECUTION_AUTHORITY,
                    fingerprint=runtime_authority_fingerprint_v1(self),
                )
            except ValueError as error:
                raise H2TemporalProofDAGInvariantViolation(
                    "H2 temporal execution was copied, replaced, or modified"
                ) from error
        _cid(self.source_result_id, "execution source result")
        if (
            self.source_result_id != EXPECTED_SOURCE_RESULT_ID
            or type(self.cache_scope) is not H2TemporalCacheScope
            or type(self.semantics) is not H2TemporalProofDAGSemanticsV1
            or type(self.protocol) is not H2TemporalProofDAGProtocolV1
            or type(self.expected_reuse_manifest) is not H2TemporalExpectedReuseManifestV1
            or type(self.plan_proposal) is not H2TemporalPlanProposalV1
            or self.protocol.semantics_id != self.semantics.semantics_id
            or self.expected_reuse_manifest.protocol_id != self.protocol.protocol_id
            or self.plan_proposal.protocol_id != self.protocol.protocol_id
            or self.plan_proposal.source_result_id != self.source_result_id
            or type(self.arm) is not H2TemporalProofDAGArmV1
            or self.arm.scope is not self.cache_scope
            or self.arm.protocol_id != self.protocol.protocol_id
            or self.arm.semantics_id != self.semantics.semantics_id
            or self.arm.expected_reuse_manifest_id != self.expected_reuse_manifest.manifest_id
            or type(self.plan_change_closures) is not tuple
            or len(self.plan_change_closures) != 5
            or any(type(item) is not H2TemporalPlanChangeClosureV1 for item in self.plan_change_closures)
            or self.initial_cache_empty is not True
        ):
            raise H2TemporalProofDAGInvariantViolation("execution identity/cardinality changed")
        _validate_arm_trace(self.arm)
        _validate_manifest_arm(self.expected_reuse_manifest, self.arm)
        receipts = self.arm.request_receipts
        selected_gray = next(
            (
                item for item in self.protocol.gray_plans
                if item.gray_plan_id == self.plan_proposal.selected_gray_plan_id
            ),
            None,
        )
        expected_summaries = tuple(
            sorted(
                (
                    PartialPlannerCandidateSummaryV1(
                        receipt.audit_result.robust_bounds.partial_model_id,
                        receipt.audit_result.robust_bounds.thresholds_id,
                        receipt.audit_result.robust_bounds.return_bound_proof_id,
                        receipt.request.contingent_plan_id,
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
                    )
                    for receipt in receipts[:4]
                ),
                key=lambda item: item.contingent_plan_id,
            )
        )
        if (
            self.plan_proposal.candidate_receipt_ids
            != tuple(item.receipt_id for item in receipts[:4])
            or tuple(item.to_document() for item in self.plan_proposal.candidate_summaries)
            != tuple(item.to_document() for item in expected_summaries)
            or any(item.request.planner_result_id is not None for item in receipts[:4])
            or receipts[4].request.planner_result_id != self.plan_proposal.result_id
            or receipts[4].request.contingent_plan_id
            != self.plan_proposal.selected_plan.plan_id
            or receipts[4].audit_result.to_document()
            != receipts[0].audit_result.to_document()
            or selected_gray is None
            or selected_gray.contingent_plan.to_document()
            != self.plan_proposal.selected_plan.to_document()
            or selected_gray.semantic_schedule_key
            != self.plan_proposal.selected_semantic_schedule_key
        ):
            raise H2TemporalProofDAGInvariantViolation(
                "selection/root role or exact cross-plan attribution changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h2_temporal_proof_dag_execution.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "source_result_id": self.source_result_id,
            "cache_scope": self.cache_scope.value,
            "semantics": self.semantics.to_document(),
            "protocol": self.protocol.to_document(),
            "expected_reuse_manifest": self.expected_reuse_manifest.to_document(),
            "plan_proposal": self.plan_proposal.to_document(),
            "arm": self.arm.to_document(),
            "plan_change_closures": [item.to_document() for item in self.plan_change_closures],
            "initial_cache_empty": self.initial_cache_empty,
        }

    @property
    def execution_id(self) -> str:
        return _content_id("execution", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "execution_id": self.execution_id}

    @property
    def request_receipts(self) -> tuple[H2TemporalProofRequestReceiptV1, ...]:
        return self.arm.request_receipts

    @property
    def resolutions(self) -> tuple[H2TemporalProofResolutionV1, ...]:
        return self.arm.resolutions

    @property
    def entry_catalogue(self) -> tuple[H2TemporalProofNodeEntryV1, ...]:
        return self.arm.entry_catalogue

    @property
    def final_cache(self) -> H2TemporalProofCacheV1:
        return self.arm.final_cache

    @property
    def aggregate_work(self) -> H2TemporalProofWorkV1:
        return self.arm.aggregate_work

    @property
    def prefixes(self) -> tuple[H2TemporalProofPrefixV1, ...]:
        return self.arm.prefixes


def require_h2_temporal_proof_dag_execution_v1(
    execution: H2TemporalProofDAGExecutionV1,
) -> H2TemporalProofDAGExecutionV1:
    if type(execution) is not H2TemporalProofDAGExecutionV1:
        raise H2TemporalProofDAGInvariantViolation("execution exact type is required")
    try:
        require_runtime_authority_v1(
            execution, issuer=_H2_TEMPORAL_EXECUTION_AUTHORITY
        )
    except ValueError as error:
        raise H2TemporalProofDAGInvariantViolation(
            "execution lacks retained owner-bound authority"
        ) from error
    execution.__post_init__()
    return execution


def _registered_protocol(
    observation_log: ObservationLogManifestV1,
    semantics_profile: DeterministicObservationProfileV1,
    observation_authority: PreregisteredObservationAuthorityV1,
    source_result: MultiStepQueryRefinementResultV1,
) -> tuple[
    H2TemporalProofDAGSemanticsV1,
    H2TemporalProofDAGProtocolV1,
    H2TemporalExpectedReuseManifestV1,
    QueryScopedPartialRAPMV3,
    FrozenPartialAuditThresholdsV1,
]:
    if (
        type(observation_log) is not ObservationLogManifestV1
        or type(semantics_profile) is not DeterministicObservationProfileV1
        or type(observation_authority) is not PreregisteredObservationAuthorityV1
        or type(source_result) is not MultiStepQueryRefinementResultV1
    ):
        raise H2TemporalProofDAGInvariantViolation("production rejects duck source/authority inputs")
    if source_result.result_id != EXPECTED_SOURCE_RESULT_ID:
        raise H2TemporalProofDAGInvariantViolation("production requires the canonical V0-047 source")
    model = source_result.final_overlay_build.model
    thresholds = source_result.final_threshold_rebase.rebased_thresholds
    if (
        type(model) is not QueryScopedPartialRAPMV3
        or model.model_id != EXPECTED_FINAL_MODEL_ID
        or type(thresholds) is not FrozenPartialAuditThresholdsV1
        or thresholds.horizon != 2
        or thresholds.partial_model_id != model.model_id
        or model.observation_log_id != observation_log.log_id
        or model.semantics_profile_id != semantics_profile.profile_id
        or model.observation_authority_id != observation_authority.authority_id
    ):
        raise H2TemporalProofDAGInvariantViolation("canonical H2 model/query authority changed")
    semantics = h2_temporal_proof_dag_semantics_v1()
    # This is an authority/facet check, not a whole-horizon audit.
    audit_module._validate_return_bound_authority(
        observation_log, semantics_profile, observation_authority, model, thresholds
    )
    _, domains = _planner_context(
        observation_log, semantics_profile, observation_authority, model, thresholds
    )
    raw_assignments = _stage_assignments(domains)
    action_by_id = {item.semantic_action_id: item for item in model.semantic_actions}
    cell_by_id = {item.cell_id: item for item in model.cells}
    ordered_cells = tuple(
        item.cell_id for item in sorted(
            (item for item in model.cells if item.planning_kind is PlanningKind.ACTIVE),
            key=lambda item: (item.coordinate_values, item.member_state_ids),
        )
    )

    def semantic_key(assignments: tuple[Any, ...]) -> tuple[int, ...]:
        mapping = {item.cell_id: item.semantic_action_id for item in assignments}
        return tuple(
            int(value)
            for cell_id in ordered_cells
            for value in action_by_id[mapping[cell_id]].label_values
        )

    ordered_assignments = tuple(sorted(raw_assignments, key=lambda item: (semantic_key(item), tuple(row.semantic_action_id for row in item))))
    if len(ordered_assignments) != 2:
        raise H2TemporalProofDAGInvariantViolation("canonical H2 model must expose two stage assignments")
    stage_artifacts = tuple(
        H2TemporalStageAssignmentV1(
            index,
            tuple(
                (
                    row.cell_id,
                    row.semantic_action_id,
                    tuple(int(value) for value in action_by_id[row.semantic_action_id].label_values),
                )
                for row in assignments
            ),
        )
        for index, assignments in enumerate(ordered_assignments)
    )
    gray_bits = ((0, 0), (0, 1), (1, 1), (1, 0))
    gray_plans: list[H2TemporalGrayPlanV1] = []
    for index, bits in enumerate(gray_bits):
        plan = FrozenContingentAbstractPlanV1(
            model.model_id,
            2,
            tuple(
                ContingentPlanStageV1(time_index, ordered_assignments[bit])
                for time_index, bit in enumerate(bits)
            ),
        )
        gray_plans.append(
            H2TemporalGrayPlanV1(
                index,
                GRAY_SCHEDULE_CODES[index],
                tuple(stage_artifacts[bit].stage_assignment_id for bit in bits),
                plan,
                multistep_module._semantic_plan_key(model, plan),
            )
        )
    protocol = H2TemporalProofDAGProtocolV1(
        semantics.semantics_id,
        source_result.result_id,
        model.model_id,
        thresholds.thresholds_id,
        stage_artifacts,
        tuple(gray_plans),
    )
    for gray in protocol.gray_plans:
        if gray.semantic_schedule_key != multistep_module._semantic_plan_key(model, gray.contingent_plan):
            raise H2TemporalProofDAGInvariantViolation("Gray semantic key differs from V0-047")
    manifest = H2TemporalExpectedReuseManifestV1(
        protocol.protocol_id,
        GRAY_SCHEDULE_CODES,
        "WINNER_OF_FROZEN_V0047_NUMERIC_SEMANTIC_RULE",
        tuple((scope.value, _manifest_outcomes()[scope]) for scope in H2TemporalCacheScope),
        tuple(
            (scope.value, EXPECTED_PREFIX_COMPUTES[scope.value])
            for scope in H2TemporalCacheScope
        ),
    )
    return semantics, protocol, manifest, model, thresholds


def _closures() -> tuple[H2TemporalPlanChangeClosureV1, ...]:
    return (
        H2TemporalPlanChangeClosureV1(1, None, "A0A0", (0, 1), SLOT_ORDER),
        H2TemporalPlanChangeClosureV1(
            2, "A0A0", "A0A1", (1,),
            (
                H2TemporalProofSlot.P1, H2TemporalProofSlot.P0,
                H2TemporalProofSlot.C1, H2TemporalProofSlot.D,
                H2TemporalProofSlot.E, H2TemporalProofSlot.F,
                H2TemporalProofSlot.G, H2TemporalProofSlot.R,
            ),
        ),
        H2TemporalPlanChangeClosureV1(
            3, "A0A1", "A1A1", (0,),
            (
                H2TemporalProofSlot.P0, H2TemporalProofSlot.C0,
                H2TemporalProofSlot.C1, H2TemporalProofSlot.D,
                H2TemporalProofSlot.E, H2TemporalProofSlot.F,
                H2TemporalProofSlot.G, H2TemporalProofSlot.R,
            ),
        ),
        H2TemporalPlanChangeClosureV1(
            4, "A1A1", "A1A0", (1,),
            (
                H2TemporalProofSlot.P1, H2TemporalProofSlot.P0,
                H2TemporalProofSlot.C1, H2TemporalProofSlot.D,
                H2TemporalProofSlot.E, H2TemporalProofSlot.F,
                H2TemporalProofSlot.G, H2TemporalProofSlot.R,
            ),
        ),
        H2TemporalPlanChangeClosureV1(
            5, "A1A0", "A0A0", (0,),
            (
                H2TemporalProofSlot.P0, H2TemporalProofSlot.C0,
                H2TemporalProofSlot.C1, H2TemporalProofSlot.D,
                H2TemporalProofSlot.E, H2TemporalProofSlot.F,
                H2TemporalProofSlot.G, H2TemporalProofSlot.R,
            ),
        ),
    )


def _execute_scope(
    source_result: MultiStepQueryRefinementResultV1,
    semantics: H2TemporalProofDAGSemanticsV1,
    protocol: H2TemporalProofDAGProtocolV1,
    manifest: H2TemporalExpectedReuseManifestV1,
    model: QueryScopedPartialRAPMV3,
    thresholds: FrozenPartialAuditThresholdsV1,
    scope: H2TemporalCacheScope,
) -> H2TemporalProofDAGExecutionV1:
    runtime = _ArmRuntime(scope, semantics, protocol, model, thresholds)
    for index, gray in enumerate(protocol.gray_plans, start=1):
        request = _make_request(protocol, gray, index, None)
        _run_request(runtime, request, gray)
    proposal = _build_selection(
        protocol, tuple(runtime.receipts[:4]), thresholds
    )
    selected_gray = next(
        item for item in protocol.gray_plans
        if item.gray_plan_id == proposal.selected_gray_plan_id
    )
    selected_request = _make_request(
        protocol, selected_gray, 5, proposal.result_id
    )
    _run_request(runtime, selected_request, selected_gray)
    arm = _freeze_arm(runtime, manifest.manifest_id)
    execution = H2TemporalProofDAGExecutionV1(
        source_result.result_id,
        scope,
        semantics,
        protocol,
        manifest,
        proposal,
        arm,
        _closures(),
        True,
        _H2_TEMPORAL_EXECUTION_AUTHORITY,
    )
    return bind_runtime_authority_v1(
        execution, issuer=_H2_TEMPORAL_EXECUTION_AUTHORITY
    )


def run_h2_temporal_incremental_proof_dag_v1(
    observation_log: ObservationLogManifestV1,
    semantics_profile: DeterministicObservationProfileV1,
    observation_authority: PreregisteredObservationAuthorityV1,
    source_result: MultiStepQueryRefinementResultV1,
) -> H2TemporalProofDAGExecutionV1:
    """Run only the production ``GLOBAL_STAGE_DAG`` arm."""

    semantics, protocol, manifest, model, thresholds = _registered_protocol(
        observation_log, semantics_profile, observation_authority, source_result
    )
    return _execute_scope(
        source_result, semantics, protocol, manifest, model, thresholds,
        H2TemporalCacheScope.GLOBAL_STAGE_DAG,
    )


@dataclass(frozen=True, slots=True)
class H2TemporalLegacyAuditMatchV1:
    request_receipt_id: str
    role: H2TemporalProofRole
    contingent_plan_id: str
    incremental_audit_result_id: str
    legacy_audit_result_id: str
    exact_document_match: bool = True
    evaluation_lane_only: bool = True
    monolithic_auditor_call_count: int = 1

    def __post_init__(self) -> None:
        for name in (
            "request_receipt_id", "contingent_plan_id",
            "incremental_audit_result_id", "legacy_audit_result_id",
        ):
            _cid(getattr(self, name), f"legacy match {name}")
        if (
            type(self.role) is not H2TemporalProofRole
            or self.incremental_audit_result_id != self.legacy_audit_result_id
            or self.exact_document_match is not True
            or self.evaluation_lane_only is not True
            or self.monolithic_auditor_call_count != 1
        ):
            raise H2TemporalProofDAGInvariantViolation("legacy match is not exact/evaluation-only")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h2_temporal_legacy_audit_match.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "request_receipt_id": self.request_receipt_id,
            "role": self.role.value,
            "contingent_plan_id": self.contingent_plan_id,
            "incremental_audit_result_id": self.incremental_audit_result_id,
            "legacy_audit_result_id": self.legacy_audit_result_id,
            "exact_document_match": self.exact_document_match,
            "evaluation_lane_only": self.evaluation_lane_only,
            "monolithic_auditor_call_count": self.monolithic_auditor_call_count,
        }

    @property
    def match_id(self) -> str:
        return _content_id("legacy", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "match_id": self.match_id}


@dataclass(frozen=True, slots=True)
class H2TemporalProofDAGControlResultV1:
    source_result_id: str
    request_reset_execution: H2TemporalProofDAGExecutionV1
    exact_plan_partitioned_execution: H2TemporalProofDAGExecutionV1
    global_stage_dag_execution: H2TemporalProofDAGExecutionV1
    legacy_audit_matches: tuple[H2TemporalLegacyAuditMatchV1, ...]
    evaluation_monolithic_auditor_call_count: int
    cross_plan_avoided_node_constructions: int
    status: str = SUCCESS_STATUS
    registered_h2_stage_local_bellman_recurrence_claimed: bool = True
    general_horizon_incremental_recurrence_claimed: bool = False
    generic_h_gt_1_recurrence_claimed: bool = False
    horizon_greater_than_two_claimed: bool = False
    cross_query_h2_persistence_claimed: bool = False
    changed_threshold_or_rho_incremental_claimed: bool = False
    changed_model_incremental_claimed: bool = False
    changed_reward_incremental_claimed: bool = False
    closed_loop_local_overlay_invalidation_claimed: bool = False
    general_cross_query_incremental_proof_claimed: bool = False
    reward_or_model_epoch_incremental_claimed: bool = False
    persistent_cache_claimed: bool = False
    sample_tax_operator_claimed: bool = False
    sample_reduction_claimed: bool = False
    workload_economics_claimed: bool = False
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
        _cid(self.source_result_id, "control source result")
        executions = (
            (self.request_reset_execution, H2TemporalCacheScope.REQUEST_RESET),
            (self.exact_plan_partitioned_execution, H2TemporalCacheScope.EXACT_PLAN_PARTITIONED),
            (self.global_stage_dag_execution, H2TemporalCacheScope.GLOBAL_STAGE_DAG),
        )
        for execution, scope in executions:
            require_h2_temporal_proof_dag_execution_v1(execution)
            if execution.cache_scope is not scope or execution.source_result_id != self.source_result_id:
                raise H2TemporalProofDAGInvariantViolation("control execution scope/source changed")
        if (
            type(self.legacy_audit_matches) is not tuple
            or len(self.legacy_audit_matches) != 5
            or any(type(item) is not H2TemporalLegacyAuditMatchV1 for item in self.legacy_audit_matches)
            or self.evaluation_monolithic_auditor_call_count != 5
            or self.cross_plan_avoided_node_constructions != 10
            or self.exact_plan_partitioned_execution.aggregate_work.computed
            - self.global_stage_dag_execution.aggregate_work.computed
            != self.cross_plan_avoided_node_constructions
            or self.status != SUCCESS_STATUS
            or self.registered_h2_stage_local_bellman_recurrence_claimed is not True
            or self.general_horizon_incremental_recurrence_claimed is not False
            or self.generic_h_gt_1_recurrence_claimed is not False
            or self.horizon_greater_than_two_claimed is not False
            or self.cross_query_h2_persistence_claimed is not False
            or self.changed_threshold_or_rho_incremental_claimed is not False
            or self.changed_model_incremental_claimed is not False
            or self.changed_reward_incremental_claimed is not False
            or self.closed_loop_local_overlay_invalidation_claimed is not False
            or self.general_cross_query_incremental_proof_claimed is not False
            or self.reward_or_model_epoch_incremental_claimed is not False
            or self.persistent_cache_claimed is not False
            or self.sample_tax_operator_claimed is not False
            or self.sample_reduction_claimed is not False
            or self.workload_economics_claimed is not False
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
            raise H2TemporalProofDAGInvariantViolation("control claim/Gate lock changed")
        reference = tuple(
            item.audit_result.to_document()
            for item in self.request_reset_execution.request_receipts
        )
        if any(
            tuple(item.audit_result.to_document() for item in execution.request_receipts)
            != reference
            for execution, _ in executions[1:]
        ):
            raise H2TemporalProofDAGInvariantViolation("control scope changed root semantics")
        if len({execution.plan_proposal.result_id for execution, _ in executions}) != 3:
            raise H2TemporalProofDAGInvariantViolation("each scope must derive its own selection proposal")
        receipts = self.global_stage_dag_execution.request_receipts
        if (
            tuple(item.request_receipt_id for item in self.legacy_audit_matches)
            != tuple(item.receipt_id for item in receipts)
            or any(
                match.incremental_audit_result_id != receipt.audit_result.result_id
                for match, receipt in zip(self.legacy_audit_matches, receipts)
            )
        ):
            raise H2TemporalProofDAGInvariantViolation("legacy matches were transplanted")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h2_temporal_proof_dag_control_result.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "source_result_id": self.source_result_id,
            "request_reset_execution": self.request_reset_execution.to_document(),
            "exact_plan_partitioned_execution": self.exact_plan_partitioned_execution.to_document(),
            "global_stage_dag_execution": self.global_stage_dag_execution.to_document(),
            "legacy_audit_matches": [item.to_document() for item in self.legacy_audit_matches],
            "evaluation_monolithic_auditor_call_count": self.evaluation_monolithic_auditor_call_count,
            "cross_plan_avoided_node_constructions": self.cross_plan_avoided_node_constructions,
            "status": self.status,
            "registered_h2_stage_local_bellman_recurrence_claimed": self.registered_h2_stage_local_bellman_recurrence_claimed,
            "general_horizon_incremental_recurrence_claimed": self.general_horizon_incremental_recurrence_claimed,
            "generic_h_gt_1_recurrence_claimed": self.generic_h_gt_1_recurrence_claimed,
            "horizon_greater_than_two_claimed": self.horizon_greater_than_two_claimed,
            "cross_query_h2_persistence_claimed": self.cross_query_h2_persistence_claimed,
            "changed_threshold_or_rho_incremental_claimed": self.changed_threshold_or_rho_incremental_claimed,
            "changed_model_incremental_claimed": self.changed_model_incremental_claimed,
            "changed_reward_incremental_claimed": self.changed_reward_incremental_claimed,
            "closed_loop_local_overlay_invalidation_claimed": self.closed_loop_local_overlay_invalidation_claimed,
            "general_cross_query_incremental_proof_claimed": self.general_cross_query_incremental_proof_claimed,
            "reward_or_model_epoch_incremental_claimed": self.reward_or_model_epoch_incremental_claimed,
            "persistent_cache_claimed": self.persistent_cache_claimed,
            "sample_tax_operator_claimed": self.sample_tax_operator_claimed,
            "sample_reduction_claimed": self.sample_reduction_claimed,
            "workload_economics_claimed": self.workload_economics_claimed,
            "total_work_or_wallclock_reduction_claimed": self.total_work_or_wallclock_reduction_claimed,
            "sample_efficiency_claimed": self.sample_efficiency_claimed,
            "learned_or_partial_dynamics_claimed": self.learned_or_partial_dynamics_claimed,
            "cross_domain_generalization_claimed": self.cross_domain_generalization_claimed,
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


def _legacy_matches(
    observation_log: ObservationLogManifestV1,
    semantics_profile: DeterministicObservationProfileV1,
    observation_authority: PreregisteredObservationAuthorityV1,
    source_result: MultiStepQueryRefinementResultV1,
    execution: H2TemporalProofDAGExecutionV1,
) -> tuple[H2TemporalLegacyAuditMatchV1, ...]:
    model = source_result.final_overlay_build.model
    thresholds = source_result.final_threshold_rebase.rebased_thresholds
    matches: list[H2TemporalLegacyAuditMatchV1] = []
    for receipt in execution.request_receipts:
        legacy = audit_module._audit_verified_partial_model_v1(
            model,
            observation_log,
            semantics_profile,
            observation_authority,
            thresholds,
            receipt.gray_plan.contingent_plan,
        )
        if legacy.to_document() != receipt.audit_result.to_document():
            raise H2TemporalProofDAGInvariantViolation(
                "stage-local R differs from the unchanged monolithic V0-043 audit"
            )
        matches.append(
            H2TemporalLegacyAuditMatchV1(
                receipt.receipt_id,
                receipt.request.role,
                receipt.request.contingent_plan_id,
                receipt.audit_result.result_id,
                legacy.result_id,
            )
        )
    return tuple(matches)


def run_lmb_h2_temporal_incremental_proof_dag_control_v1(
    observation_log: ObservationLogManifestV1,
    semantics_profile: DeterministicObservationProfileV1,
    observation_authority: PreregisteredObservationAuthorityV1,
    source_result: MultiStepQueryRefinementResultV1,
) -> H2TemporalProofDAGControlResultV1:
    """Run two reset controls, production global DAG, and five legacy audits."""

    semantics, protocol, manifest, model, thresholds = _registered_protocol(
        observation_log, semantics_profile, observation_authority, source_result
    )
    request_reset = _execute_scope(
        source_result, semantics, protocol, manifest, model, thresholds,
        H2TemporalCacheScope.REQUEST_RESET,
    )
    exact_plan_partitioned = _execute_scope(
        source_result, semantics, protocol, manifest, model, thresholds,
        H2TemporalCacheScope.EXACT_PLAN_PARTITIONED,
    )
    # Call the public production boundary for the operational arm.  It neither
    # constructs nor observes either reset control.
    global_stage_dag = run_h2_temporal_incremental_proof_dag_v1(
        observation_log, semantics_profile, observation_authority, source_result
    )
    matches = _legacy_matches(
        observation_log, semantics_profile, observation_authority,
        source_result, global_stage_dag,
    )
    return H2TemporalProofDAGControlResultV1(
        source_result.result_id,
        request_reset,
        exact_plan_partitioned,
        global_stage_dag,
        matches,
        len(matches),
        exact_plan_partitioned.aggregate_work.computed
        - global_stage_dag.aggregate_work.computed,
    )


def verify_lmb_h2_temporal_incremental_proof_dag_control_v1(
    observation_log: ObservationLogManifestV1,
    semantics_profile: DeterministicObservationProfileV1,
    observation_authority: PreregisteredObservationAuthorityV1,
    observed_synthesis_result: ObservedTypedPartialRAPMResultV1,
    source_thresholds: FrozenPartialAuditThresholdsV1,
    source_base_plan_proposal: TypedPartialModelPlanProposalResultV2,
    source_failed_audit: TypedPartialSoundAuditResultV2,
    kernel: LMBKernel,
    source_result: MultiStepQueryRefinementResultV1,
    claimed_result: H2TemporalProofDAGControlResultV1,
) -> H2TemporalProofDAGControlResultV1:
    """Rebuild V0-047 first, then independently replay the complete control."""

    if type(claimed_result) is not H2TemporalProofDAGControlResultV1:
        raise H2TemporalProofDAGInvariantViolation(
            "independent verifier rejects substituted control results"
        )
    verified_source = verify_lmb_h2_multistep_query_refinement_v1(
        observation_log,
        semantics_profile,
        observation_authority,
        observed_synthesis_result,
        source_thresholds,
        source_base_plan_proposal,
        source_failed_audit,
        kernel,
        source_result,
    )
    replayed = run_lmb_h2_temporal_incremental_proof_dag_control_v1(
        observation_log, semantics_profile, observation_authority, verified_source
    )
    if replayed.to_document() != claimed_result.to_document():
        raise H2TemporalProofDAGInvariantViolation(
            "independent H2 temporal replay differs from the claimed control"
        )
    return replayed


__all__ = [
    "CONTRACT_VERSION",
    "EXPECTED_FINAL_MODEL_ID",
    "EXPECTED_GLOBAL_GROUPED",
    "EXPECTED_GRAY_PLAN_IDS",
    "EXPECTED_MULTISTEP_SOURCE_SHA256",
    "EXPECTED_PARTIAL_AUDIT_SOURCE_SHA256",
    "EXPECTED_PARTIAL_MODEL_PLANNER_SOURCE_SHA256",
    "EXPECTED_PREFIX_COMPUTES",
    "EXPECTED_SOURCE_RESULT_ID",
    "GRAY_SCHEDULE_CODES",
    "H2TemporalCacheScope",
    "H2TemporalExpectedReuseManifestV1",
    "H2TemporalGrayPlanV1",
    "H2TemporalLegacyAuditMatchV1",
    "H2TemporalPlanChangeClosureV1",
    "H2TemporalPlanProposalV1",
    "H2TemporalProofCacheV1",
    "H2TemporalProofDAGArmV1",
    "H2TemporalProofDAGControlResultV1",
    "H2TemporalProofDAGExecutionV1",
    "H2TemporalProofDAGInvariantViolation",
    "H2TemporalProofDAGProtocolV1",
    "H2TemporalProofDAGSemanticsV1",
    "H2TemporalProofKindCountV1",
    "H2TemporalProofNodeEntryV1",
    "H2TemporalProofNodeKeyV1",
    "H2TemporalProofPrefixV1",
    "H2TemporalProofRequestReceiptV1",
    "H2TemporalProofRequestV1",
    "H2TemporalProofResolutionV1",
    "H2TemporalProofRole",
    "H2TemporalProofSlot",
    "H2TemporalProofWorkV1",
    "H2TemporalResolutionOutcome",
    "PROFILE_KEY",
    "SCHEMA_VERSION",
    "SUCCESS_STATUS",
    "h2_temporal_proof_dag_semantics_v1",
    "require_h2_temporal_proof_dag_execution_v1",
    "run_h2_temporal_incremental_proof_dag_v1",
    "run_lmb_h2_temporal_incremental_proof_dag_control_v1",
    "verify_lmb_h2_temporal_incremental_proof_dag_control_v1",
]
