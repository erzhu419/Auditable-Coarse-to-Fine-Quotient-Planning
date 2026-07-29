"""Model-only minimal-pair causal support recovery for K6.

V0-070 starts from the immutable V0-069 negative singleton result.  It
reconstructs the transaction-1 selected-policy candidate registry, evaluates
cardinality one and two by complete fixed-policy H1->H2 replay, and opens
fresh observer streams only after one budget-admissible pair authorization
has been frozen.

The Gate is intentionally bounded to the current selected policy and
``k <= 2``.  A fixed-policy joint cover is sufficient, but the Gate does not
claim global subset minimality or search for a policy-changing pair.
"""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, replace
from enum import Enum
from fractions import Fraction
import hashlib
import itertools
from multiprocessing import get_context
from typing import Any, Iterable, Mapping, Sequence

import acfqp.observation_support_exact_evaluation_v1 as exact_evaluation
import acfqp.observation_support_graph_acquisition_v1 as acquisition
import acfqp.observation_support_graph_model_v1 as graph_model
import acfqp.observation_support_h2_closure_v1 as h2_closure
import acfqp.observation_support_promoted_h2_consumer_v1 as first_consumer
import acfqp.observation_support_relational_adapter_v1 as relational
import acfqp.observation_support_second_transaction_v1 as second
import acfqp.partial_support_expansion_authority_v1 as expansion
import acfqp.partial_support_robust_planner_v1 as robust
import acfqp.transition_tuple_observer_v1 as observer
from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id


SCHEMA_VERSION = "1.0.0"
CONTRACT_VERSION = "1.34.0"
PROFILE_KEY = "k6_model_only_minimal_pair_support_recovery_v0"

REGISTERED_CONTEXT_KEY = "opaque_graph_k6_v0"
REGISTERED_BASE_CHECKPOINT = 8_192
REGISTERED_PROMOTION_CHECKPOINT = 2_048
REGISTERED_NEW_CHILD_CHECKPOINT = 8_192
MAX_ELIGIBLE_ROWS = 64
MAX_SINGLETON_OVERLAY_EVALUATIONS = 64
MAX_PAIR_OVERLAY_EVALUATIONS = 2_016
MAX_SUBSET_CARDINALITY = 2
MAX_SELECTED_PAIR_COUNT = 1
MAX_OPERATIONAL_FULL_JOINT_REPLANS = 1
MAX_PAIR_PROMOTIONS = 2
MAX_NEW_CHILD_CATALOGUES = 19
MAX_NEW_CHILD_ACTION_ROWS = 19
MAX_INCREMENTAL_OBSERVER_DRAWS = 160_960
ALTERNATIVE_GLOBAL_16384_SUFFIX_DRAWS = 163_840
MATCHED_DIRECT_8192_DRAWS = 165_120
TRANSACTION1_PREFIX_DRAWS = 414_848
MATCHED_DIRECT_HEADROOM = -249_728
MAX_PROCESS_WORKERS = h2_closure.MAX_PROCESS_WORKERS
STATISTICAL_CLAIM_SCOPE = observer.STATISTICAL_CLAIM_SCOPE

MINIMALITY_SCOPE = (
    "MIN_CARDINALITY_WITHIN_TX1_SELECTED_POLICY_FRONTIER_UP_TO_K2"
)


class ObservationSupportJointPairInvariantViolation(ValueError):
    """A joint-pair identity, cap, replay, or no-reuse rule is invalid."""


class JointPairOutcome(str, Enum):
    CERTIFIED_AT_8192_AFTER_JOINT_PAIR = (
        "CERTIFIED_AT_8192_AFTER_JOINT_PAIR"
    )
    FAILED_NEW_FRONTIER_AFTER_JOINT_PAIR = (
        "FAILED_NEW_FRONTIER_AFTER_JOINT_PAIR"
    )
    NO_SOUND_FIXED_PLAN_PAIR_COVER = "NO_SOUND_FIXED_PLAN_PAIR_COVER"
    PAIR_COUNTERFACTUAL_CAP_EXHAUSTED = (
        "PAIR_COUNTERFACTUAL_CAP_EXHAUSTED"
    )
    PAIR_COVER_SAMPLE_BUDGET_DOMINATED = (
        "PAIR_COVER_SAMPLE_BUDGET_DOMINATED"
    )
    MATERIALIZATION_CAP_EXHAUSTED = "MATERIALIZATION_CAP_EXHAUSTED"
    PROTOCOL_FAILURE = "PROTOCOL_FAILURE"


class ModelOnlySubsetStatus(str, Enum):
    FIXED_PLAN_CERTIFIED = "FIXED_PLAN_CERTIFIED"
    STILL_FAILED = "STILL_FAILED"
    INFEASIBLE_SIMPLEX = "INFEASIBLE_SIMPLEX"


DOMAIN_TAGS = {
    "caps": "acfqp:joint-pair-support-caps:v1",
    "context": "acfqp:joint-pair-support-context:v1",
    "candidate": "acfqp:joint-pair-candidate-row:v1",
    "registry": "acfqp:joint-pair-candidate-registry:v1",
    "evidence": "acfqp:model-only-fixed-plan-subset-evidence:v1",
    "cardinality": "acfqp:joint-pair-materialization-cardinality:v1",
    "authorization": "acfqp:joint-pair-support-authorization:v1",
    "replacement": "acfqp:joint-pair-promoted-row-replacement:v1",
    "counters": "acfqp:joint-pair-support-counters:v1",
    "closure": "acfqp:joint-pair-promoted-h2-closure:v1",
    "run": "acfqp:joint-pair-support-run:v1",
    "probe": "acfqp:k6-joint-pair-support-probe:v1",
    "verification": "acfqp:joint-pair-support-verification:v1",
}

if len(DOMAIN_TAGS) != len(set(DOMAIN_TAGS.values())):  # pragma: no cover
    raise RuntimeError("joint-pair content domains must be unique")


def _content_id(role: str, payload: Mapping[str, Any]) -> str:
    try:
        domain = DOMAIN_TAGS[role].encode("utf-8")
        body = canonical_json_bytes(dict(payload))
    except (KeyError, TypeError, ValueError) as error:
        raise ObservationSupportJointPairInvariantViolation(str(error)) from error
    return hashlib.sha256(domain + b"\x00" + body).hexdigest()


def _cid(value: Any, field: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise ObservationSupportJointPairInvariantViolation(
            f"{field} must be a full content ID"
        ) from error


def _ids(values: Any, field: str) -> tuple[str, ...]:
    if (
        type(values) is not tuple
        or values != tuple(sorted(set(values)))
    ):
        raise ObservationSupportJointPairInvariantViolation(
            f"{field} must be a sorted distinct tuple"
        )
    for value in values:
        _cid(value, field)
    return values


def _fdoc(value: Fraction) -> dict[str, int]:
    if type(value) is not Fraction:
        raise ObservationSupportJointPairInvariantViolation(
            "counterfactual values must be exact Fractions"
        )
    return {"numerator": value.numerator, "denominator": value.denominator}


def _workers(value: Any) -> int:
    if (
        type(value) is not int
        or isinstance(value, bool)
        or not 1 <= value <= MAX_PROCESS_WORKERS
    ):
        raise ObservationSupportJointPairInvariantViolation(
            "max_workers is outside the registered finite range"
        )
    return value


def _registered_k6(
    context: observer.PublicGraphContextV1,
) -> observer.PublicGraphContextV1:
    expected = observer.public_context_by_key_v1(REGISTERED_CONTEXT_KEY)
    if (
        type(context) is not observer.PublicGraphContextV1
        or context != expected
        or context.horizon != 2
    ):
        raise ObservationSupportJointPairInvariantViolation(
            "joint-pair Gate is restricted to registered K6 H=2"
        )
    return expected


@dataclass(frozen=True, slots=True)
class JointPairSupportCapsV1:
    max_eligible_rows: int = MAX_ELIGIBLE_ROWS
    max_singleton_overlay_evaluations: int = (
        MAX_SINGLETON_OVERLAY_EVALUATIONS
    )
    max_pair_overlay_evaluations: int = MAX_PAIR_OVERLAY_EVALUATIONS
    max_subset_cardinality: int = MAX_SUBSET_CARDINALITY
    max_selected_pair_count: int = MAX_SELECTED_PAIR_COUNT
    max_operational_full_joint_replans: int = (
        MAX_OPERATIONAL_FULL_JOINT_REPLANS
    )
    max_pair_promotions: int = MAX_PAIR_PROMOTIONS
    promoted_validation_checkpoint: int = REGISTERED_PROMOTION_CHECKPOINT
    new_child_validation_checkpoint: int = (
        REGISTERED_NEW_CHILD_CHECKPOINT
    )
    max_new_child_catalogues: int = MAX_NEW_CHILD_CATALOGUES
    max_new_child_action_rows: int = MAX_NEW_CHILD_ACTION_ROWS
    max_incremental_observer_draws: int = (
        MAX_INCREMENTAL_OBSERVER_DRAWS
    )
    max_global_checkpoint: int = REGISTERED_BASE_CHECKPOINT
    global_16384_checkpoint_forbidden: bool = True

    def __post_init__(self) -> None:
        expected = (
            MAX_ELIGIBLE_ROWS,
            MAX_SINGLETON_OVERLAY_EVALUATIONS,
            MAX_PAIR_OVERLAY_EVALUATIONS,
            MAX_SUBSET_CARDINALITY,
            MAX_SELECTED_PAIR_COUNT,
            MAX_OPERATIONAL_FULL_JOINT_REPLANS,
            MAX_PAIR_PROMOTIONS,
            REGISTERED_PROMOTION_CHECKPOINT,
            REGISTERED_NEW_CHILD_CHECKPOINT,
            MAX_NEW_CHILD_CATALOGUES,
            MAX_NEW_CHILD_ACTION_ROWS,
            MAX_INCREMENTAL_OBSERVER_DRAWS,
            REGISTERED_BASE_CHECKPOINT,
            True,
        )
        actual = tuple(
            getattr(self, field) for field in self.__dataclass_fields__
        )
        if actual != expected:
            raise ObservationSupportJointPairInvariantViolation(
                "joint-pair caps are not the registered finite profile"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.joint_pair_support_caps.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            **{
                field: getattr(self, field)
                for field in self.__dataclass_fields__
            },
            "alternative_global_16384_suffix_draws": (
                ALTERNATIVE_GLOBAL_16384_SUFFIX_DRAWS
            ),
        }

    @property
    def cap_profile_id(self) -> str:
        return _content_id("caps", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "cap_profile_id": self.cap_profile_id}


def registered_joint_pair_caps_v1() -> JointPairSupportCapsV1:
    return JointPairSupportCapsV1()


@dataclass(frozen=True, slots=True)
class JointPairCandidateRowV1:
    planner_row_id: str
    partial_row_id: str
    binding_id: str
    physical_evidence_id: str
    support_epoch_id: str
    confidence_authority_id: str
    remaining_horizon: int
    novel_outcome_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        for value, field in (
            (self.planner_row_id, "candidate planner row"),
            (self.partial_row_id, "candidate partial row"),
            (self.binding_id, "candidate binding"),
            (self.physical_evidence_id, "candidate physical evidence"),
            (self.support_epoch_id, "candidate support epoch"),
            (self.confidence_authority_id, "candidate confidence authority"),
        ):
            _cid(value, field)
        _ids(self.novel_outcome_ids, "candidate novel outcomes")
        if (
            self.remaining_horizon not in (1, 2)
            or not self.novel_outcome_ids
        ):
            raise ObservationSupportJointPairInvariantViolation(
                "joint-pair candidate row is malformed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.joint_pair_candidate_row.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "planner_row_id": self.planner_row_id,
            "partial_row_id": self.partial_row_id,
            "binding_id": self.binding_id,
            "physical_evidence_id": self.physical_evidence_id,
            "support_epoch_id": self.support_epoch_id,
            "confidence_authority_id": self.confidence_authority_id,
            "remaining_horizon": self.remaining_horizon,
            "novel_outcome_ids": list(self.novel_outcome_ids),
            "support_epoch_index": 1,
        }

    @property
    def candidate_id(self) -> str:
        return _content_id("candidate", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "candidate_id": self.candidate_id}


@dataclass(frozen=True, slots=True)
class JointPairCandidateRegistryV1:
    parent_model_id: str
    parent_audit_id: str
    parent_frontier_id: str
    threshold_profile_id: str
    selected_assignment_ids: tuple[str, ...]
    source_partial_row_ids: tuple[str, ...]
    quarantined_v0069_evidence_ids: tuple[str, ...]
    excluded_binding_ids: tuple[str, ...]
    excluded_physical_evidence_ids: tuple[str, ...]
    candidates: tuple[JointPairCandidateRowV1, ...]

    def __post_init__(self) -> None:
        for value, field in (
            (self.parent_model_id, "registry parent model"),
            (self.parent_audit_id, "registry parent audit"),
            (self.parent_frontier_id, "registry parent frontier"),
            (self.threshold_profile_id, "registry threshold"),
        ):
            _cid(value, field)
        for values, field in (
            (self.selected_assignment_ids, "registry assignments"),
            (self.source_partial_row_ids, "registry source rows"),
            (
                self.quarantined_v0069_evidence_ids,
                "quarantined V0-069 evidence",
            ),
            (self.excluded_binding_ids, "registry excluded bindings"),
            (
                self.excluded_physical_evidence_ids,
                "registry excluded evidence",
            ),
        ):
            _ids(values, field)
        candidate_ids = tuple(item.candidate_id for item in self.candidates)
        if (
            not self.candidates
            or any(
                type(item) is not JointPairCandidateRowV1
                for item in self.candidates
            )
            or candidate_ids != tuple(sorted(set(candidate_ids)))
            or len({item.planner_row_id for item in self.candidates})
            != len(self.candidates)
            or len({item.partial_row_id for item in self.candidates})
            != len(self.candidates)
            or any(
                item.binding_id in self.excluded_binding_ids
                or item.physical_evidence_id
                in self.excluded_physical_evidence_ids
                or item.partial_row_id not in self.source_partial_row_ids
                for item in self.candidates
            )
        ):
            raise ObservationSupportJointPairInvariantViolation(
                "fresh joint-pair candidate registry is malformed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.joint_pair_candidate_registry.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "parent_model_id": self.parent_model_id,
            "parent_audit_id": self.parent_audit_id,
            "parent_frontier_id": self.parent_frontier_id,
            "threshold_profile_id": self.threshold_profile_id,
            "selected_assignment_ids": list(self.selected_assignment_ids),
            "source_partial_row_ids": list(self.source_partial_row_ids),
            "quarantined_v0069_evidence_ids": list(
                self.quarantined_v0069_evidence_ids
            ),
            "excluded_binding_ids": list(self.excluded_binding_ids),
            "excluded_physical_evidence_ids": list(
                self.excluded_physical_evidence_ids
            ),
            "candidate_ids": [
                item.candidate_id for item in self.candidates
            ],
            "candidate_registry_recomputed_from_parent_frontier": True,
            "v0069_counterfactual_authority_reused": False,
        }

    @property
    def registry_id(self) -> str:
        return _content_id("registry", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "candidates": [item.to_document() for item in self.candidates],
            "registry_id": self.registry_id,
        }


@dataclass(frozen=True, slots=True)
class ModelOnlySubsetEvidenceV1:
    registry_id: str
    parent_model_id: str
    parent_audit_id: str
    threshold_profile_id: str
    selected_assignment_ids: tuple[str, ...]
    candidate_ids: tuple[str, ...]
    planner_row_ids: tuple[str, ...]
    partial_row_ids: tuple[str, ...]
    zero_other_model_id: str | None
    root_reward_lower: Fraction | None
    root_failure_upper: Fraction | None
    normalized_regret_upper: Fraction | None
    minimum_certificate_slack: Fraction | None
    status: ModelOnlySubsetStatus
    subset_cardinality: int
    h1_then_h2_recomputed: bool = True
    full_policy_replan_count: int = 0
    observer_draws: int = 0
    kernel_calls: int = 0
    exact_calls: int = 0

    def __post_init__(self) -> None:
        for value, field in (
            (self.registry_id, "subset registry"),
            (self.parent_model_id, "subset parent model"),
            (self.parent_audit_id, "subset parent audit"),
            (self.threshold_profile_id, "subset threshold"),
        ):
            _cid(value, field)
        for values, field in (
            (self.selected_assignment_ids, "subset assignments"),
            (self.candidate_ids, "subset candidates"),
            (self.planner_row_ids, "subset planner rows"),
            (self.partial_row_ids, "subset partial rows"),
        ):
            _ids(values, field)
        if self.zero_other_model_id is not None:
            _cid(self.zero_other_model_id, "subset zero-OTHER model")
        cardinality = self.subset_cardinality
        metrics = (
            self.root_reward_lower,
            self.root_failure_upper,
            self.normalized_regret_upper,
            self.minimum_certificate_slack,
        )
        infeasible = (
            self.status is ModelOnlySubsetStatus.INFEASIBLE_SIMPLEX
        )
        if (
            type(self.status) is not ModelOnlySubsetStatus
            or cardinality not in (1, 2)
            or len(self.candidate_ids) != cardinality
            or len(self.planner_row_ids) != cardinality
            or len(self.partial_row_ids) != cardinality
            or not self.selected_assignment_ids
            or self.h1_then_h2_recomputed is not True
            or self.full_policy_replan_count != 0
            or self.observer_draws != 0
            or self.kernel_calls != 0
            or self.exact_calls != 0
            or (
                infeasible
                and (
                    self.zero_other_model_id is not None
                    or any(item is not None for item in metrics)
                )
            )
            or (
                not infeasible
                and (
                    self.zero_other_model_id is None
                    or any(type(item) is not Fraction for item in metrics)
                )
            )
            or (
                self.status is ModelOnlySubsetStatus.FIXED_PLAN_CERTIFIED
                and (
                    self.minimum_certificate_slack is None
                    or self.minimum_certificate_slack < 0
                )
            )
            or (
                self.status is ModelOnlySubsetStatus.STILL_FAILED
                and (
                    self.minimum_certificate_slack is None
                    or self.minimum_certificate_slack >= 0
                )
            )
        ):
            raise ObservationSupportJointPairInvariantViolation(
                "model-only subset evidence is inconsistent"
            )

    @property
    def fixed_plan_certified(self) -> bool:
        return self.status is ModelOnlySubsetStatus.FIXED_PLAN_CERTIFIED

    def _payload(self) -> dict[str, Any]:
        def maybe(value: Fraction | None) -> dict[str, int] | None:
            return None if value is None else _fdoc(value)

        return {
            "schema": "acfqp.model_only_fixed_plan_subset_evidence.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "registry_id": self.registry_id,
            "parent_model_id": self.parent_model_id,
            "parent_audit_id": self.parent_audit_id,
            "threshold_profile_id": self.threshold_profile_id,
            "selected_assignment_ids": list(self.selected_assignment_ids),
            "candidate_ids": list(self.candidate_ids),
            "planner_row_ids": list(self.planner_row_ids),
            "partial_row_ids": list(self.partial_row_ids),
            "zero_other_model_id": self.zero_other_model_id,
            "root_reward_lower": maybe(self.root_reward_lower),
            "root_failure_upper": maybe(self.root_failure_upper),
            "normalized_regret_upper": maybe(
                self.normalized_regret_upper
            ),
            "minimum_certificate_slack": maybe(
                self.minimum_certificate_slack
            ),
            "status": self.status.value,
            "subset_cardinality": self.subset_cardinality,
            "h1_then_h2_recomputed": True,
            "parent_unrestricted_reward_upper_retained": True,
            "full_policy_replan_count": 0,
            "observer_draws": 0,
            "kernel_calls": 0,
            "exact_calls": 0,
        }

    @property
    def evidence_id(self) -> str:
        return _content_id("evidence", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "evidence_id": self.evidence_id}


@dataclass(frozen=True, slots=True)
class JointPairMaterializationCardinalityV1:
    registry_id: str
    pair_evidence_id: str
    planner_row_ids: tuple[str, str]
    new_child_catalogue_ids: tuple[str, ...]
    new_child_binding_keys: tuple[
        tuple[str, tuple[int, int, int]], ...
    ]
    pair_promotion_draws: int
    new_child_action_row_count: int
    incremental_draw_upper: int
    within_registered_caps: bool
    avoids_further_global_checkpoint_tax: bool

    def __post_init__(self) -> None:
        for value, field in (
            (self.registry_id, "cardinality registry"),
            (self.pair_evidence_id, "cardinality pair evidence"),
        ):
            _cid(value, field)
        _ids(self.planner_row_ids, "cardinality planner rows")
        _ids(
            self.new_child_catalogue_ids,
            "cardinality child catalogues",
        )
        binding_keys = tuple(
            sorted(set(self.new_child_binding_keys))
        )
        if (
            len(self.planner_row_ids) != 2
            or self.new_child_binding_keys != binding_keys
            or any(
                type(catalogue_id) is not str
                or type(action) is not tuple
                or len(action) != 3
                or any(type(item) is not int for item in action)
                for catalogue_id, action in self.new_child_binding_keys
            )
            or any(
                _cid(catalogue_id, "cardinality binding catalogue")
                != catalogue_id
                for catalogue_id, _ in self.new_child_binding_keys
            )
            or self.pair_promotion_draws
            != 2 * REGISTERED_PROMOTION_CHECKPOINT
            or self.new_child_action_row_count
            != len(self.new_child_binding_keys)
            or self.incremental_draw_upper
            != self.pair_promotion_draws
            + self.new_child_action_row_count
            * (
                acquisition.DISCOVERY_DRAW_COUNT
                + REGISTERED_NEW_CHILD_CHECKPOINT
            )
            or self.within_registered_caps
            is not (
                len(self.new_child_catalogue_ids)
                <= MAX_NEW_CHILD_CATALOGUES
                and self.new_child_action_row_count
                <= MAX_NEW_CHILD_ACTION_ROWS
                and self.incremental_draw_upper
                <= MAX_INCREMENTAL_OBSERVER_DRAWS
            )
            or self.avoids_further_global_checkpoint_tax
            is not (
                self.incremental_draw_upper
                < ALTERNATIVE_GLOBAL_16384_SUFFIX_DRAWS
            )
        ):
            raise ObservationSupportJointPairInvariantViolation(
                "joint-pair materialization cardinality is inconsistent"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.joint_pair_materialization_cardinality.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "registry_id": self.registry_id,
            "pair_evidence_id": self.pair_evidence_id,
            "planner_row_ids": list(self.planner_row_ids),
            "new_child_catalogue_ids": list(
                self.new_child_catalogue_ids
            ),
            "new_child_binding_keys": [
                {
                    "catalogue_id": catalogue_id,
                    "action": list(action),
                }
                for catalogue_id, action in self.new_child_binding_keys
            ],
            "pair_promotion_draws": self.pair_promotion_draws,
            "new_child_action_row_count": (
                self.new_child_action_row_count
            ),
            "incremental_draw_upper": self.incremental_draw_upper,
            "within_registered_caps": self.within_registered_caps,
            "avoids_further_global_checkpoint_tax": (
                self.avoids_further_global_checkpoint_tax
            ),
            "cardinality_frozen_before_observer_access": True,
        }

    @property
    def cardinality_id(self) -> str:
        return _content_id("cardinality", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "cardinality_id": self.cardinality_id,
        }


@dataclass(frozen=True, slots=True)
class JointPairSupportAuthorizationV1:
    context_id: str
    registry_id: str
    parent_model_id: str
    parent_audit_id: str
    parent_frontier_id: str
    threshold_profile_id: str
    selected_assignment_ids: tuple[str, ...]
    pair_evidence_id: str
    cardinality_id: str
    selected_candidate_ids: tuple[str, str]
    selected_planner_row_ids: tuple[str, str]
    selected_partial_row_ids: tuple[str, str]
    selected_binding_ids: tuple[str, str]
    selected_physical_evidence_ids: tuple[str, str]
    selected_support_epoch_ids: tuple[str, str]
    selected_confidence_authority_ids: tuple[str, str]
    selected_novel_outcome_ids: tuple[str, ...]
    cap_profile_id: str
    authorization_sequence: int = 1
    fresh_stream_open_sequence_minimum: int = 2
    authorization_scope: str = (
        "ONE_JOINT_PAIR_FROM_TX1_SELECTED_POLICY_FRONTIER"
    )

    def __post_init__(self) -> None:
        for value, field in (
            (self.context_id, "authorization context"),
            (self.registry_id, "authorization registry"),
            (self.parent_model_id, "authorization parent model"),
            (self.parent_audit_id, "authorization parent audit"),
            (self.parent_frontier_id, "authorization parent frontier"),
            (self.threshold_profile_id, "authorization threshold"),
            (self.pair_evidence_id, "authorization pair evidence"),
            (self.cardinality_id, "authorization cardinality"),
            (self.cap_profile_id, "authorization cap profile"),
        ):
            _cid(value, field)
        for values, field in (
            (self.selected_assignment_ids, "authorization assignments"),
            (self.selected_candidate_ids, "authorization candidates"),
            (self.selected_planner_row_ids, "authorization planner rows"),
            (self.selected_partial_row_ids, "authorization partial rows"),
            (self.selected_binding_ids, "authorization bindings"),
            (
                self.selected_physical_evidence_ids,
                "authorization physical evidence",
            ),
            (
                self.selected_support_epoch_ids,
                "authorization support epochs",
            ),
            (
                self.selected_confidence_authority_ids,
                "authorization confidence authorities",
            ),
            (
                self.selected_novel_outcome_ids,
                "authorization novel outcomes",
            ),
        ):
            _ids(values, field)
        pair_fields = (
            self.selected_candidate_ids,
            self.selected_planner_row_ids,
            self.selected_partial_row_ids,
            self.selected_binding_ids,
            self.selected_physical_evidence_ids,
            self.selected_support_epoch_ids,
            self.selected_confidence_authority_ids,
        )
        if (
            any(len(values) != 2 for values in pair_fields)
            or not self.selected_assignment_ids
            or not self.selected_novel_outcome_ids
            or self.authorization_sequence != 1
            or self.fresh_stream_open_sequence_minimum != 2
            or self.authorization_scope
            != "ONE_JOINT_PAIR_FROM_TX1_SELECTED_POLICY_FRONTIER"
        ):
            raise ObservationSupportJointPairInvariantViolation(
                "joint-pair authorization is malformed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.joint_pair_support_authorization.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "context_id": self.context_id,
            "registry_id": self.registry_id,
            "parent_model_id": self.parent_model_id,
            "parent_audit_id": self.parent_audit_id,
            "parent_frontier_id": self.parent_frontier_id,
            "threshold_profile_id": self.threshold_profile_id,
            "selected_assignment_ids": list(
                self.selected_assignment_ids
            ),
            "pair_evidence_id": self.pair_evidence_id,
            "cardinality_id": self.cardinality_id,
            "selected_candidate_ids": list(self.selected_candidate_ids),
            "selected_planner_row_ids": list(
                self.selected_planner_row_ids
            ),
            "selected_partial_row_ids": list(
                self.selected_partial_row_ids
            ),
            "selected_binding_ids": list(self.selected_binding_ids),
            "selected_physical_evidence_ids": list(
                self.selected_physical_evidence_ids
            ),
            "selected_support_epoch_ids": list(
                self.selected_support_epoch_ids
            ),
            "selected_confidence_authority_ids": list(
                self.selected_confidence_authority_ids
            ),
            "selected_novel_outcome_ids": list(
                self.selected_novel_outcome_ids
            ),
            "cap_profile_id": self.cap_profile_id,
            "authorization_sequence": self.authorization_sequence,
            "fresh_stream_open_sequence_minimum": (
                self.fresh_stream_open_sequence_minimum
            ),
            "authorization_scope": self.authorization_scope,
            "authorization_frozen_before_both_fresh_streams": True,
            "v0069_counterfactual_authority_reused": False,
        }

    @property
    def authorization_id(self) -> str:
        return _content_id("authorization", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "authorization_id": self.authorization_id,
        }


@dataclass(frozen=True, slots=True)
class JointPairPromotedRowReplacementV1:
    authorization_id: str
    parent_row: acquisition.GraphPartialSupportRowV1
    promoted_row: acquisition.GraphPartialSupportRowV1
    quarantined_parent_observation_ids: tuple[str, ...]
    fresh_validation_observation_ids: tuple[str, ...]
    fresh_stream_open_sequence: int

    def __post_init__(self) -> None:
        _cid(self.authorization_id, "replacement authorization")
        if (
            type(self.parent_row)
            is not acquisition.GraphPartialSupportRowV1
            or type(self.promoted_row)
            is not acquisition.GraphPartialSupportRowV1
        ):
            raise ObservationSupportJointPairInvariantViolation(
                "joint replacement rows are untyped"
            )
        quarantined = _ids(
            self.quarantined_parent_observation_ids,
            "replacement quarantined observations",
        )
        fresh = _ids(
            self.fresh_validation_observation_ids,
            "replacement fresh observations",
        )
        expected_quarantined = tuple(
            sorted(
                {
                    *self.parent_row.initial_discovery_observation_ids,
                    *self.parent_row.prior_validation_observation_ids,
                    *self.parent_row.current_validation_observation_ids,
                }
            )
        )
        if (
            self.parent_row.support_epoch_index != 1
            or self.promoted_row.parent_row != self.parent_row
            or self.promoted_row.binding != self.parent_row.binding
            or self.promoted_row.support_epoch_index != 2
            or quarantined != expected_quarantined
            or fresh
            != tuple(
                sorted(
                    self.promoted_row.current_validation_observation_ids
                )
            )
            or set(quarantined) & set(fresh)
            or len(fresh) != REGISTERED_PROMOTION_CHECKPOINT
            or self.fresh_stream_open_sequence not in (2, 3)
        ):
            raise ObservationSupportJointPairInvariantViolation(
                "joint replacement reused samples or opened before authorization"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.joint_pair_promoted_row_replacement.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "authorization_id": self.authorization_id,
            "parent_partial_row_id": self.parent_row.partial_row_id,
            "promoted_partial_row_id": self.promoted_row.partial_row_id,
            "binding_id": self.parent_row.binding.row_id,
            "quarantined_parent_observation_ids": list(
                self.quarantined_parent_observation_ids
            ),
            "fresh_validation_observation_ids": list(
                self.fresh_validation_observation_ids
            ),
            "fresh_stream_open_sequence": (
                self.fresh_stream_open_sequence
            ),
        }

    @property
    def replacement_id(self) -> str:
        return _content_id("replacement", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "replacement_id": self.replacement_id,
        }


@dataclass(frozen=True, slots=True)
class JointPairSupportCountersV1:
    eligible_row_count: int
    singleton_overlay_evaluations: int
    pair_overlay_evaluations: int
    fixed_plan_pair_cover_count: int
    cardinality_evaluations: int
    selected_pair_count: int
    promoted_row_count: int
    promoted_validation_draws: int
    promoted_validation_random_word_calls: int
    promoted_validation_rejections: int
    new_child_catalogue_count: int
    new_child_action_row_count: int
    new_child_discovery_draws: int
    new_child_validation_draws: int
    new_child_observer_draws: int
    new_child_random_word_calls: int
    new_child_rejections: int
    incremental_observer_draws: int
    incremental_random_word_calls: int
    incremental_rejections: int
    operational_full_joint_replans: int
    cap_checks: int
    cap_rejections: int
    model_only_observer_draws: int = 0
    model_only_kernel_calls: int = 0
    model_only_exact_calls: int = 0
    global_16384_checkpoint_accesses: int = 0

    def __post_init__(self) -> None:
        values = tuple(
            getattr(self, field) for field in self.__dataclass_fields__
        )
        if (
            any(type(item) is not int or item < 0 for item in values)
            or self.singleton_overlay_evaluations
            > MAX_SINGLETON_OVERLAY_EVALUATIONS
            or self.pair_overlay_evaluations
            > MAX_PAIR_OVERLAY_EVALUATIONS
            or self.selected_pair_count > 1
            or self.promoted_row_count not in (0, 2)
            or self.operational_full_joint_replans not in (0, 1)
            or self.promoted_validation_random_word_calls
            != self.promoted_validation_draws
            + self.promoted_validation_rejections
            or self.new_child_observer_draws
            != self.new_child_discovery_draws
            + self.new_child_validation_draws
            or self.incremental_observer_draws
            != self.promoted_validation_draws
            + self.new_child_observer_draws
            or self.incremental_random_word_calls
            != self.promoted_validation_random_word_calls
            + self.new_child_random_word_calls
            or self.incremental_rejections
            != self.promoted_validation_rejections
            + self.new_child_rejections
            or self.incremental_random_word_calls
            != self.incremental_observer_draws
            + self.incremental_rejections
            or self.incremental_observer_draws
            > MAX_INCREMENTAL_OBSERVER_DRAWS
            or self.cap_checks < 6
            or self.model_only_observer_draws != 0
            or self.model_only_kernel_calls != 0
            or self.model_only_exact_calls != 0
            or self.global_16384_checkpoint_accesses != 0
        ):
            raise ObservationSupportJointPairInvariantViolation(
                "joint-pair counters do not reconcile"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.joint_pair_support_counters.v1",
            "schema_version": SCHEMA_VERSION,
            **{
                field: getattr(self, field)
                for field in self.__dataclass_fields__
            },
        }

    @property
    def counters_id(self) -> str:
        return _content_id("counters", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "counters_id": self.counters_id}


def _sorted_rows(
    rows: Iterable[acquisition.GraphPartialSupportRowV1],
) -> tuple[acquisition.GraphPartialSupportRowV1, ...]:
    result = tuple(sorted(rows, key=lambda item: item.binding.row_id))
    if (
        any(
            type(item) is not acquisition.GraphPartialSupportRowV1
            for item in result
        )
        or len({item.binding.row_id for item in result}) != len(result)
        or len({item.partial_row_id for item in result}) != len(result)
    ):
        raise ObservationSupportJointPairInvariantViolation(
            "joint closure rows are not unique typed rows"
        )
    return result


def _sorted_catalogues(
    catalogues: Iterable[observer.LegalActionCatalogueV1],
) -> tuple[observer.LegalActionCatalogueV1, ...]:
    result = tuple(sorted(catalogues, key=lambda item: item.catalogue_id))
    if (
        any(
            type(item) is not observer.LegalActionCatalogueV1
            for item in result
        )
        or len({item.catalogue_id for item in result}) != len(result)
    ):
        raise ObservationSupportJointPairInvariantViolation(
            "joint closure catalogues are not unique"
        )
    return result


def _active_root_states(
    root_rows: Iterable[acquisition.GraphPartialSupportRowV1],
) -> tuple[observer.SymbolicGraphStateV1, ...]:
    by_id: dict[str, observer.SymbolicGraphStateV1] = {}
    for row in root_rows:
        for descriptor in row.support_descriptors:
            if descriptor.failure or descriptor.terminal:
                continue
            state = descriptor.next_state
            prior = by_id.setdefault(state.state_id, state)
            if prior != state:
                raise ObservationSupportJointPairInvariantViolation(
                    "one successor ID has conflicting symbolic states"
                )
    return tuple(by_id[key] for key in sorted(by_id))


@dataclass(frozen=True, slots=True)
class JointPairPromotedH2ClosureV1:
    context_id: str
    parent_consumer_id: str
    authorization: JointPairSupportAuthorizationV1
    replacements: tuple[
        JointPairPromotedRowReplacementV1,
        JointPairPromotedRowReplacementV1,
    ]
    context: observer.PublicGraphContextV1
    root_catalogue: observer.LegalActionCatalogueV1
    child_catalogues: tuple[observer.LegalActionCatalogueV1, ...]
    root_rows: tuple[acquisition.GraphPartialSupportRowV1, ...]
    child_rows: tuple[acquisition.GraphPartialSupportRowV1, ...]
    epoch2_binding_ids: tuple[str, str, str]
    newly_admitted_child_catalogue_ids: tuple[str, ...]
    newly_acquired_child_partial_row_ids: tuple[str, ...]
    counters: JointPairSupportCountersV1
    support_transaction_count: int = 2
    subset_cardinality: int = 2
    third_transaction_allowed: bool = False
    exact_iid_implementation_claimed: bool = False
    formal_exact_iid_plan_certificate: bool = False
    statistical_claim_scope: str = STATISTICAL_CLAIM_SCOPE

    def __post_init__(self) -> None:
        _cid(self.context_id, "closure Gate context")
        _cid(self.parent_consumer_id, "closure parent consumer")
        if (
            type(self.authorization)
            is not JointPairSupportAuthorizationV1
            or len(self.replacements) != 2
            or any(
                type(item) is not JointPairPromotedRowReplacementV1
                for item in self.replacements
            )
            or _registered_k6(self.context) != self.context
            or type(self.root_catalogue)
            is not observer.LegalActionCatalogueV1
            or type(self.counters) is not JointPairSupportCountersV1
            or self.support_transaction_count != 2
            or self.subset_cardinality != 2
            or self.third_transaction_allowed is not False
            or self.exact_iid_implementation_claimed is not False
            or self.formal_exact_iid_plan_certificate is not False
            or self.statistical_claim_scope != STATISTICAL_CLAIM_SCOPE
        ):
            raise ObservationSupportJointPairInvariantViolation(
                "joint promoted closure schema is invalid"
            )
        if (
            tuple(
                sorted(item.replacement_id for item in self.replacements)
            )
            != tuple(item.replacement_id for item in self.replacements)
            or any(
                item.authorization_id
                != self.authorization.authorization_id
                for item in self.replacements
            )
        ):
            raise ObservationSupportJointPairInvariantViolation(
                "joint replacements are not canonical and authorization-bound"
            )
        rows = (*self.root_rows, *self.child_rows)
        epoch2 = _ids(self.epoch2_binding_ids, "epoch-2 bindings")
        new_catalogues = _ids(
            self.newly_admitted_child_catalogue_ids,
            "new child catalogue IDs",
        )
        new_rows = _ids(
            self.newly_acquired_child_partial_row_ids,
            "new child partial rows",
        )
        actual_epoch2 = tuple(
            sorted(
                row.binding.row_id
                for row in rows
                if row.support_epoch_index == 2
            )
        )
        fresh_sets = tuple(
            set(item.fresh_validation_observation_ids)
            for item in self.replacements
        )
        selected_bindings = set(
            self.authorization.selected_binding_ids
        )
        all_parent_ids = set().union(
            *(
                {
                    *row.initial_discovery_observation_ids,
                    *row.prior_validation_observation_ids,
                    *row.current_validation_observation_ids,
                }
                for row in rows
                if row.binding.row_id not in selected_bindings
            ),
            *(
                set(item.quarantined_parent_observation_ids)
                for item in self.replacements
            ),
        )
        if (
            _sorted_rows(self.root_rows) != self.root_rows
            or _sorted_rows(self.child_rows) != self.child_rows
            or _sorted_catalogues(self.child_catalogues)
            != self.child_catalogues
            or len(epoch2) != 3
            or actual_epoch2 != epoch2
            or set(self.authorization.selected_binding_ids)
            != {
                item.parent_row.binding.row_id
                for item in self.replacements
            }
            or self.authorization.authorization_sequence != 1
            or {
                item.fresh_stream_open_sequence
                for item in self.replacements
            }
            != {2, 3}
            or fresh_sets[0] & fresh_sets[1]
            or any(values & all_parent_ids for values in fresh_sets)
            or len(rows) != len({row.binding.row_id for row in rows})
            or any(row.support_epoch_index not in (1, 2) for row in rows)
        ):
            raise ObservationSupportJointPairInvariantViolation(
                "closure lacks exactly three disjoint epoch-2 bindings"
            )
        expected_catalogues = _sorted_catalogues(
            observer.legal_action_catalogue_v1(self.context, state, 1)
            for state in _active_root_states(self.root_rows)
        )
        if tuple(
            item.to_document() for item in expected_catalogues
        ) != tuple(item.to_document() for item in self.child_catalogues):
            raise ObservationSupportJointPairInvariantViolation(
                "joint closure omits a reachable child catalogue"
            )
        expected_root = {
            (self.root_catalogue.catalogue_id, action)
            for action in self.root_catalogue.actions
        }
        expected_child = {
            (catalogue.catalogue_id, action)
            for catalogue in self.child_catalogues
            for action in catalogue.actions
        }
        actual_root = {
            (row.binding.catalogue_id, row.binding.action)
            for row in self.root_rows
        }
        actual_child = {
            (row.binding.catalogue_id, row.binding.action)
            for row in self.child_rows
        }
        if (
            actual_root != expected_root
            or actual_child != expected_child
            or len(new_catalogues)
            != self.counters.new_child_catalogue_count
            or len(new_rows) != self.counters.new_child_action_row_count
        ):
            raise ObservationSupportJointPairInvariantViolation(
                "joint closure action coverage or counters are incomplete"
            )

    @property
    def all_rows(
        self,
    ) -> tuple[acquisition.GraphPartialSupportRowV1, ...]:
        return (*self.root_rows, *self.child_rows)

    @property
    def public_catalogues(
        self,
    ) -> tuple[observer.LegalActionCatalogueV1, ...]:
        return (self.root_catalogue, *self.child_catalogues)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.joint_pair_promoted_h2_closure.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "context_id": self.context_id,
            "parent_consumer_id": self.parent_consumer_id,
            "authorization_id": self.authorization.authorization_id,
            "replacement_ids": [
                item.replacement_id for item in self.replacements
            ],
            "public_context_id": self.context.context_id,
            "root_catalogue_id": self.root_catalogue.catalogue_id,
            "child_catalogue_ids": [
                item.catalogue_id for item in self.child_catalogues
            ],
            "root_partial_row_ids": [
                item.partial_row_id for item in self.root_rows
            ],
            "child_partial_row_ids": [
                item.partial_row_id for item in self.child_rows
            ],
            "epoch2_binding_ids": list(self.epoch2_binding_ids),
            "newly_admitted_child_catalogue_ids": list(
                self.newly_admitted_child_catalogue_ids
            ),
            "newly_acquired_child_partial_row_ids": list(
                self.newly_acquired_child_partial_row_ids
            ),
            "counters_id": self.counters.counters_id,
            "support_transaction_count": 2,
            "subset_cardinality": 2,
            "third_transaction_allowed": False,
            "global_16384_checkpoint_accesses": 0,
            "exact_iid_implementation_claimed": False,
            "formal_exact_iid_plan_certificate": False,
            "statistical_claim_scope": self.statistical_claim_scope,
        }

    @property
    def closure_id(self) -> str:
        return _content_id("closure", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "authorization": self.authorization.to_document(),
            "replacements": [
                item.to_document() for item in self.replacements
            ],
            "counters": self.counters.to_document(),
            "closure_id": self.closure_id,
        }


@dataclass(frozen=True, slots=True)
class JointPairSupportContextV1:
    public_context_id: str
    base_closure_id: str
    transaction1_consumer_id: str
    v0069_negative_run_id: str
    parent_closure_id: str
    parent_bridge_id: str
    parent_model_id: str
    parent_audit_id: str
    parent_frontier_id: str
    threshold_profile_id: str
    selected_assignment_ids: tuple[str, ...]
    quarantined_v0069_evidence_ids: tuple[str, ...]
    registry_id: str
    cap_profile_id: str
    base_checkpoint: int = REGISTERED_BASE_CHECKPOINT
    maximum_subset_cardinality: int = 2
    third_transaction_allowed: bool = False
    global_16384_checkpoint_accesses: int = 0

    def __post_init__(self) -> None:
        for value, field in (
            (self.public_context_id, "Gate public context"),
            (self.base_closure_id, "Gate base closure"),
            (self.transaction1_consumer_id, "Gate transaction-1 consumer"),
            (self.v0069_negative_run_id, "Gate V0-069 run"),
            (self.parent_closure_id, "Gate parent closure"),
            (self.parent_bridge_id, "Gate parent bridge"),
            (self.parent_model_id, "Gate parent model"),
            (self.parent_audit_id, "Gate parent audit"),
            (self.parent_frontier_id, "Gate parent frontier"),
            (self.threshold_profile_id, "Gate threshold"),
            (self.registry_id, "Gate registry"),
            (self.cap_profile_id, "Gate cap profile"),
        ):
            _cid(value, field)
        _ids(self.selected_assignment_ids, "Gate selected assignments")
        _ids(
            self.quarantined_v0069_evidence_ids,
            "Gate quarantined V0-069 evidence",
        )
        if (
            not self.selected_assignment_ids
            or self.base_checkpoint != REGISTERED_BASE_CHECKPOINT
            or self.maximum_subset_cardinality != 2
            or self.third_transaction_allowed is not False
            or self.global_16384_checkpoint_accesses != 0
        ):
            raise ObservationSupportJointPairInvariantViolation(
                "joint-pair Gate context is malformed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.joint_pair_support_context.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            **{
                field: (
                    list(getattr(self, field))
                    if field in (
                        "selected_assignment_ids",
                        "quarantined_v0069_evidence_ids",
                    )
                    else getattr(self, field)
                )
                for field in self.__dataclass_fields__
            },
            "minimality_scope": MINIMALITY_SCOPE,
            "matched_direct_sample_advantage_eligible": False,
            "sample_efficiency_claimed": False,
        }

    @property
    def context_id(self) -> str:
        return _content_id("context", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "context_id": self.context_id}


@dataclass(frozen=True, slots=True)
class JointPairSupportRunV1:
    context: JointPairSupportContextV1
    registry: JointPairCandidateRegistryV1
    outcome: JointPairOutcome
    singleton_evidence: tuple[ModelOnlySubsetEvidenceV1, ...]
    pair_evidence: tuple[ModelOnlySubsetEvidenceV1, ...]
    cardinality_evidence: tuple[
        JointPairMaterializationCardinalityV1, ...
    ]
    selected_pair_evidence_id: str | None
    selected_cardinality_id: str | None
    authorization: JointPairSupportAuthorizationV1 | None
    replacements: tuple[JointPairPromotedRowReplacementV1, ...]
    closure: JointPairPromotedH2ClosureV1 | None
    bridge: graph_model.ObservationSupportGraphModelBridgeV1 | None
    audit: robust.RobustPlanAuditV1 | None
    counters: JointPairSupportCountersV1
    maximum_subset_cardinality: int = 2
    third_transaction_allowed: bool = False
    global_16384_checkpoint_accesses: int = 0
    matched_direct_sample_advantage_eligible: bool = False
    sample_efficiency_claimed: bool = False

    def __post_init__(self) -> None:
        if (
            type(self.context) is not JointPairSupportContextV1
            or type(self.registry) is not JointPairCandidateRegistryV1
            or self.context.registry_id != self.registry.registry_id
            or self.context.parent_model_id
            != self.registry.parent_model_id
            or self.context.parent_audit_id
            != self.registry.parent_audit_id
            or self.context.parent_frontier_id
            != self.registry.parent_frontier_id
            or self.context.threshold_profile_id
            != self.registry.threshold_profile_id
            or self.context.selected_assignment_ids
            != self.registry.selected_assignment_ids
            or self.context.quarantined_v0069_evidence_ids
            != self.registry.quarantined_v0069_evidence_ids
            or type(self.outcome) is not JointPairOutcome
            or type(self.counters) is not JointPairSupportCountersV1
            or self.maximum_subset_cardinality != 2
            or self.third_transaction_allowed is not False
            or self.global_16384_checkpoint_accesses != 0
            or self.matched_direct_sample_advantage_eligible is not False
            or self.sample_efficiency_claimed is not False
        ):
            raise ObservationSupportJointPairInvariantViolation(
                "joint-pair run schema is invalid"
            )
        for values, cardinality, field in (
            (self.singleton_evidence, 1, "singleton evidence"),
            (self.pair_evidence, 2, "pair evidence"),
        ):
            if (
                any(
                    type(item) is not ModelOnlySubsetEvidenceV1
                    or item.registry_id != self.registry.registry_id
                    or item.subset_cardinality != cardinality
                    for item in values
                )
                or tuple(item.evidence_id for item in values)
                != tuple(sorted({item.evidence_id for item in values}))
            ):
                raise ObservationSupportJointPairInvariantViolation(
                    f"joint-pair {field} is noncanonical"
                )
        for item in (*self.singleton_evidence, *self.pair_evidence):
            if (
                item.parent_model_id != self.registry.parent_model_id
                or item.parent_audit_id != self.registry.parent_audit_id
                or item.threshold_profile_id
                != self.registry.threshold_profile_id
                or item.selected_assignment_ids
                != self.registry.selected_assignment_ids
            ):
                raise ObservationSupportJointPairInvariantViolation(
                    "subset evidence was transplanted across authorities"
                )
        candidate_ids = tuple(
            item.candidate_id for item in self.registry.candidates
        )
        expected_singletons = {(item,) for item in candidate_ids}
        actual_singletons = {
            item.candidate_ids for item in self.singleton_evidence
        }
        expected_pairs = {
            tuple(sorted(pair))
            for pair in itertools.combinations(candidate_ids, 2)
        }
        actual_pairs = {item.candidate_ids for item in self.pair_evidence}
        pre_singleton_cap = (
            len(candidate_ids) > MAX_ELIGIBLE_ROWS
            and self.outcome
            is JointPairOutcome.PAIR_COUNTERFACTUAL_CAP_EXHAUSTED
        )
        singleton_protocol_failure = (
            self.outcome is JointPairOutcome.PROTOCOL_FAILURE
        )
        pair_phase_outcomes = {
            JointPairOutcome.CERTIFIED_AT_8192_AFTER_JOINT_PAIR,
            JointPairOutcome.FAILED_NEW_FRONTIER_AFTER_JOINT_PAIR,
            JointPairOutcome.NO_SOUND_FIXED_PLAN_PAIR_COVER,
            JointPairOutcome.PAIR_COVER_SAMPLE_BUDGET_DOMINATED,
            JointPairOutcome.MATERIALIZATION_CAP_EXHAUSTED,
        }
        if (
            (
                pre_singleton_cap
                and (actual_singletons or actual_pairs)
            )
            or (
                not pre_singleton_cap
                and (
                    actual_singletons != expected_singletons
                    or len(self.singleton_evidence)
                    != len(expected_singletons)
                )
            )
            or (
                singleton_protocol_failure
                and actual_pairs
            )
            or (
                self.outcome in pair_phase_outcomes
                and (
                    actual_pairs != expected_pairs
                    or len(self.pair_evidence) != len(expected_pairs)
                )
            )
            or (
                self.outcome
                is JointPairOutcome.PAIR_COUNTERFACTUAL_CAP_EXHAUSTED
                and not pre_singleton_cap
                and actual_pairs
            )
        ):
            raise ObservationSupportJointPairInvariantViolation(
                "singleton/pair evidence topology is incomplete or forged"
            )
        if (
            any(
                type(item) is not JointPairMaterializationCardinalityV1
                or item.registry_id != self.registry.registry_id
                for item in self.cardinality_evidence
            )
            or tuple(
                item.cardinality_id for item in self.cardinality_evidence
            )
            != tuple(
                sorted(
                    {
                        item.cardinality_id
                        for item in self.cardinality_evidence
                    }
                )
            )
        ):
            raise ObservationSupportJointPairInvariantViolation(
                "joint-pair cardinality evidence is noncanonical"
            )
        if (
            any(
                item.fixed_plan_certified
                for item in self.singleton_evidence
            )
            and self.outcome is not JointPairOutcome.PROTOCOL_FAILURE
        ):
            raise ObservationSupportJointPairInvariantViolation(
                "pair enumeration is illegal after a singleton cover"
            )
        cover_ids = {
            item.evidence_id
            for item in self.pair_evidence
            if item.fixed_plan_certified
        }
        cardinality_pair_ids = {
            item.pair_evidence_id for item in self.cardinality_evidence
        }
        materialized = self.outcome in (
            JointPairOutcome.CERTIFIED_AT_8192_AFTER_JOINT_PAIR,
            JointPairOutcome.FAILED_NEW_FRONTIER_AFTER_JOINT_PAIR,
        )
        if materialized:
            if (
                self.selected_pair_evidence_id is None
                or self.selected_cardinality_id is None
                or type(self.authorization)
                is not JointPairSupportAuthorizationV1
                or len(self.replacements) != 2
                or type(self.closure) is not JointPairPromotedH2ClosureV1
                or type(self.bridge)
                is not graph_model.ObservationSupportGraphModelBridgeV1
                or type(self.audit) is not robust.RobustPlanAuditV1
                or self.authorization.pair_evidence_id
                != self.selected_pair_evidence_id
                or self.authorization.cardinality_id
                != self.selected_cardinality_id
                or self.closure.context_id != self.context.context_id
                or self.bridge.source_partial_row_ids
                != tuple(
                    sorted(
                        row.partial_row_id for row in self.closure.all_rows
                    )
                )
                or self.audit.model_id
                != self.bridge.quotient_model.model_id
                or (
                    self.outcome
                    is JointPairOutcome.CERTIFIED_AT_8192_AFTER_JOINT_PAIR
                )
                is not self.audit.certified
                or (
                    self.outcome
                    is JointPairOutcome.FAILED_NEW_FRONTIER_AFTER_JOINT_PAIR
                )
                is not (
                    self.audit.status
                    is robust.RobustAuditStatus.FAILED_PROOF_FRONTIER
                )
                or self.counters.operational_full_joint_replans != 1
                or cardinality_pair_ids != cover_ids
                or len(self.cardinality_evidence) != len(cover_ids)
            ):
                raise ObservationSupportJointPairInvariantViolation(
                    "materialized joint-pair result has stale authorities"
                )
        elif (
            self.selected_pair_evidence_id is not None
            or self.selected_cardinality_id is not None
            or self.authorization is not None
            or self.replacements
            or self.closure is not None
            or self.bridge is not None
            or self.audit is not None
            or self.counters.incremental_observer_draws != 0
            or self.counters.operational_full_joint_replans != 0
        ):
            raise ObservationSupportJointPairInvariantViolation(
                "nonmaterialized joint-pair outcome carries route artifacts"
            )
        if self.outcome is JointPairOutcome.NO_SOUND_FIXED_PLAN_PAIR_COVER:
            if cover_ids or self.cardinality_evidence:
                raise ObservationSupportJointPairInvariantViolation(
                    "NO_SOUND outcome hides a model-only pair cover"
                )
        if (
            self.outcome
            is JointPairOutcome.PAIR_COVER_SAMPLE_BUDGET_DOMINATED
        ):
            if (
                not cover_ids
                or cardinality_pair_ids != cover_ids
                or len(self.cardinality_evidence) != len(cover_ids)
                or any(
                    item.within_registered_caps
                    and item.avoids_further_global_checkpoint_tax
                    for item in self.cardinality_evidence
                )
            ):
                raise ObservationSupportJointPairInvariantViolation(
                    "budget-dominated result is not supported"
                )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.joint_pair_support_run.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "context_id": self.context.context_id,
            "registry_id": self.registry.registry_id,
            "outcome": self.outcome.value,
            "singleton_evidence_ids": [
                item.evidence_id for item in self.singleton_evidence
            ],
            "pair_evidence_ids": [
                item.evidence_id for item in self.pair_evidence
            ],
            "cardinality_evidence_ids": [
                item.cardinality_id
                for item in self.cardinality_evidence
            ],
            "selected_pair_evidence_id": self.selected_pair_evidence_id,
            "selected_cardinality_id": self.selected_cardinality_id,
            "authorization_id": (
                None
                if self.authorization is None
                else self.authorization.authorization_id
            ),
            "replacement_ids": [
                item.replacement_id for item in self.replacements
            ],
            "closure_id": (
                None if self.closure is None else self.closure.closure_id
            ),
            "bridge_id": (
                None if self.bridge is None else self.bridge.bridge_id
            ),
            "audit_id": None if self.audit is None else self.audit.audit_id,
            "counters_id": self.counters.counters_id,
            "minimality_scope": MINIMALITY_SCOPE,
            "maximum_subset_cardinality": 2,
            "third_transaction_allowed": False,
            "global_16384_checkpoint_accesses": 0,
            "matched_direct_sample_advantage_eligible": False,
            "sample_efficiency_claimed": False,
            "formal_exact_iid_plan_certificate": False,
            "statistical_claim_scope": STATISTICAL_CLAIM_SCOPE,
        }

    @property
    def run_id(self) -> str:
        return _content_id("run", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "context": self.context.to_document(),
            "registry": self.registry.to_document(),
            "singleton_evidence": [
                item.to_document() for item in self.singleton_evidence
            ],
            "pair_evidence": [
                item.to_document() for item in self.pair_evidence
            ],
            "cardinality_evidence": [
                item.to_document() for item in self.cardinality_evidence
            ],
            "authorization": (
                None
                if self.authorization is None
                else self.authorization.to_document()
            ),
            "replacements": [
                item.to_document() for item in self.replacements
            ],
            "closure": (
                None if self.closure is None else self.closure.to_document()
            ),
            "bridge": (
                None if self.bridge is None else self.bridge.to_document()
            ),
            "audit": (
                None if self.audit is None else self.audit.to_document()
            ),
            "counters": self.counters.to_document(),
            "run_id": self.run_id,
        }


@dataclass(frozen=True, slots=True)
class K6JointPairSupportProbeV0:
    public_context_id: str
    base_closure_id: str
    transaction1_consumer_id: str
    v0069_negative_run_id: str
    run: JointPairSupportRunV1
    exact_lift: (
        exact_evaluation.ObservationSupportExactLiftEvaluationV1 | None
    )
    base_checkpoint: int = REGISTERED_BASE_CHECKPOINT
    max_global_checkpoint: int = REGISTERED_BASE_CHECKPOINT
    global_16384_checkpoint_accesses: int = 0
    third_transaction_allowed: bool = False
    matched_direct_8192_draws: int = MATCHED_DIRECT_8192_DRAWS
    transaction1_prefix_draws: int = TRANSACTION1_PREFIX_DRAWS
    matched_direct_headroom: int = MATCHED_DIRECT_HEADROOM
    matched_direct_sample_advantage_eligible: bool = False
    sample_efficiency_claimed: bool = False

    def __post_init__(self) -> None:
        for value, field in (
            (self.public_context_id, "probe context"),
            (self.base_closure_id, "probe base closure"),
            (self.transaction1_consumer_id, "probe transaction-1 consumer"),
            (self.v0069_negative_run_id, "probe V0-069 run"),
        ):
            _cid(value, field)
        if (
            type(self.run) is not JointPairSupportRunV1
            or self.run.context.public_context_id != self.public_context_id
            or self.run.context.base_closure_id != self.base_closure_id
            or self.run.context.transaction1_consumer_id
            != self.transaction1_consumer_id
            or self.run.context.v0069_negative_run_id
            != self.v0069_negative_run_id
            or self.base_checkpoint != REGISTERED_BASE_CHECKPOINT
            or self.max_global_checkpoint != REGISTERED_BASE_CHECKPOINT
            or self.global_16384_checkpoint_accesses != 0
            or self.third_transaction_allowed is not False
            or self.matched_direct_8192_draws != MATCHED_DIRECT_8192_DRAWS
            or self.transaction1_prefix_draws != TRANSACTION1_PREFIX_DRAWS
            or self.matched_direct_headroom != MATCHED_DIRECT_HEADROOM
            or self.matched_direct_headroom
            != self.matched_direct_8192_draws
            - self.transaction1_prefix_draws
            or self.matched_direct_sample_advantage_eligible is not False
            or self.sample_efficiency_claimed is not False
        ):
            raise ObservationSupportJointPairInvariantViolation(
                "bounded K6 joint-pair probe identity or sample boundary changed"
            )
        certified = (
            self.run.outcome
            is JointPairOutcome.CERTIFIED_AT_8192_AFTER_JOINT_PAIR
        )
        if certified:
            if (
                type(self.exact_lift)
                is not exact_evaluation.ObservationSupportExactLiftEvaluationV1
                or self.run.bridge is None
                or self.run.audit is None
                or self.exact_lift.bridge_id != self.run.bridge.bridge_id
                or self.exact_lift.audit_id != self.run.audit.audit_id
                or self.exact_lift.prerequisite_operational_freeze_id
                != self.run.run_id
            ):
                raise ObservationSupportJointPairInvariantViolation(
                    "certified pair probe lacks evaluation-only exact lift"
                )
        elif self.exact_lift is not None:
            raise ObservationSupportJointPairInvariantViolation(
                "uncertified pair probe cannot invoke exact lift"
            )

    @property
    def exact_failure_probability(self) -> Fraction | None:
        return (
            None
            if self.exact_lift is None
            else self.exact_lift.exact_failure_probability
        )

    @property
    def exact_normalized_regret(self) -> Fraction | None:
        return (
            None
            if self.exact_lift is None
            else self.exact_lift.exact_normalized_regret
        )

    def _payload(self) -> dict[str, Any]:
        def maybe(value: Fraction | None) -> dict[str, int] | None:
            return None if value is None else _fdoc(value)

        return {
            "schema": "acfqp.k6_joint_pair_support_probe.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "public_context_id": self.public_context_id,
            "base_closure_id": self.base_closure_id,
            "transaction1_consumer_id": self.transaction1_consumer_id,
            "v0069_negative_run_id": self.v0069_negative_run_id,
            "run_id": self.run.run_id,
            "outcome": self.run.outcome.value,
            "exact_lift_evaluation_id": (
                None
                if self.exact_lift is None
                else self.exact_lift.evaluation_id
            ),
            "exact_failure_probability": maybe(
                self.exact_failure_probability
            ),
            "exact_normalized_regret": maybe(
                self.exact_normalized_regret
            ),
            "base_checkpoint": REGISTERED_BASE_CHECKPOINT,
            "max_global_checkpoint": REGISTERED_BASE_CHECKPOINT,
            "global_16384_checkpoint_accesses": 0,
            "third_transaction_allowed": False,
            "matched_direct_8192_draws": MATCHED_DIRECT_8192_DRAWS,
            "transaction1_prefix_draws": TRANSACTION1_PREFIX_DRAWS,
            "matched_direct_headroom": MATCHED_DIRECT_HEADROOM,
            "matched_direct_sample_advantage_eligible": False,
            "sample_efficiency_claimed": False,
            "exact_evaluation_lane_only": True,
        }

    @property
    def probe_id(self) -> str:
        return _content_id("probe", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "run": self.run.to_document(),
            "exact_lift": (
                None
                if self.exact_lift is None
                else self.exact_lift.to_document()
            ),
            "probe_id": self.probe_id,
        }


def _validate_parent_chain(
    *,
    context: observer.PublicGraphContextV1,
    base_closure: h2_closure.ObservationSupportH2ClosureV1,
    base_bridge: graph_model.ObservationSupportGraphModelBridgeV1,
    base_audit: robust.RobustPlanAuditV1,
    threshold: robust.RobustThresholdProfileV1,
    transaction1: first_consumer.ObservationSupportPromotedH2ConsumerV1,
    v0069_negative_run: second.SecondSupportTransactionRunV1,
) -> None:
    registered = _registered_k6(context)
    parent_audit = transaction1.audit
    if (
        type(base_closure)
        is not h2_closure.ObservationSupportH2ClosureV1
        or base_closure.context != registered
        or base_closure.validation_checkpoint != REGISTERED_BASE_CHECKPOINT
        or type(base_bridge)
        is not graph_model.ObservationSupportGraphModelBridgeV1
        or base_bridge.context_id != registered.context_id
        or type(base_audit) is not robust.RobustPlanAuditV1
        or type(threshold) is not robust.RobustThresholdProfileV1
        or type(transaction1)
        is not first_consumer.ObservationSupportPromotedH2ConsumerV1
        or type(v0069_negative_run)
        is not second.SecondSupportTransactionRunV1
        or transaction1.promoted_closure.parent_closure.closure_id
        != base_closure.closure_id
        or transaction1.parent_bridge_id != base_bridge.bridge_id
        or transaction1.threshold_profile_id
        != threshold.threshold_profile_id
        or parent_audit.solver_kind
        is not robust.RobustSolverKind.QUOTIENT
        or parent_audit.status
        is not robust.RobustAuditStatus.FAILED_PROOF_FRONTIER
        or parent_audit.failed_frontier is None
        or parent_audit.model_id
        != transaction1.bridge.quotient_model.model_id
        or v0069_negative_run.outcome
        is not second.SecondTransactionOutcome.NO_SOUND_DIFFERENT_ROW_COVER
        or v0069_negative_run.context.context_id != registered.context_id
        or v0069_negative_run.context.base_closure_id
        != base_closure.closure_id
        or v0069_negative_run.context.base_bridge_id
        != base_bridge.bridge_id
        or v0069_negative_run.context.base_audit_id != base_audit.audit_id
        or v0069_negative_run.context.threshold_profile_id
        != threshold.threshold_profile_id
        or v0069_negative_run.context.transaction1_consumer_id
        != transaction1.consumer_id
        or v0069_negative_run.context.transaction1_model_id
        != parent_audit.model_id
        or v0069_negative_run.context.transaction1_audit_id
        != parent_audit.audit_id
        or v0069_negative_run.context.transaction1_frontier_id
        != parent_audit.failed_frontier.frontier_id
        or v0069_negative_run.authorization is not None
        or v0069_negative_run.replacement is not None
        or v0069_negative_run.closure is not None
        or v0069_negative_run.bridge is not None
        or v0069_negative_run.audit is not None
        or v0069_negative_run.counters.incremental_observer_draws != 0
        or any(
            item.status is not expansion.RowCounterfactualStatus.STILL_FAILED
            for item in v0069_negative_run.candidate_evidence
        )
    ):
        raise ObservationSupportJointPairInvariantViolation(
            "V0-069 negative parent chain is stale or not authoritative"
        )


def _reconstruct_candidate_registry(
    *,
    transaction1: first_consumer.ObservationSupportPromotedH2ConsumerV1,
    v0069_negative_run: second.SecondSupportTransactionRunV1,
    threshold: robust.RobustThresholdProfileV1,
) -> tuple[
    JointPairCandidateRegistryV1,
    dict[str, acquisition.GraphPartialSupportRowV1],
    dict[str, graph_model.GraphRowModelProjectionV1],
]:
    bridge = transaction1.bridge
    audit = transaction1.audit
    assert audit.failed_frontier is not None
    rows = transaction1.promoted_closure.all_rows
    by_partial = {row.partial_row_id: row for row in rows}
    by_planner = {
        projection.planner_row.row_id: projection
        for projection in bridge.row_projections
    }
    first_replacement = transaction1.promoted_closure.replacement
    excluded_binding_ids = (
        first_replacement.parent_row.binding.row_id,
    )
    excluded_physical_ids = tuple(
        sorted(
            (
                first_replacement.parent_row.physical_evidence_id,
                first_replacement.promoted_row.physical_evidence_id,
            )
        )
    )
    candidates: list[JointPairCandidateRowV1] = []
    for planner_row_id in audit.failed_frontier.other_positive_row_ids:
        projection = by_planner.get(planner_row_id)
        if projection is None:
            raise ObservationSupportJointPairInvariantViolation(
                "parent frontier references an unknown planner row"
            )
        row = by_partial.get(projection.partial_row_id)
        if row is None:
            raise ObservationSupportJointPairInvariantViolation(
                "parent projection references an unknown physical row"
            )
        if (
            row.binding.row_id in excluded_binding_ids
            or row.physical_evidence_id in excluded_physical_ids
            or row.support_epoch_index != 1
            or not row.novel_descriptors
        ):
            continue
        candidates.append(
            JointPairCandidateRowV1(
                planner_row_id,
                row.partial_row_id,
                row.binding.row_id,
                row.physical_evidence_id,
                row.support_epoch.support_epoch_id,
                row.confidence_authority.authority_id,
                row.binding.remaining_horizon,
                tuple(
                    sorted(
                        item.outcome_id
                        for item in row.novel_descriptors
                    )
                ),
            )
        )
    candidates_tuple = tuple(
        sorted(candidates, key=lambda item: item.candidate_id)
    )
    reconstructed_pairs = {
        (item.planner_row_id, item.partial_row_id)
        for item in candidates_tuple
    }
    quarantined_pairs = {
        (item.planner_row_id, item.partial_row_id)
        for item in v0069_negative_run.candidate_evidence
    }
    if reconstructed_pairs != quarantined_pairs:
        raise ObservationSupportJointPairInvariantViolation(
            "fresh registry differs from the frozen selected-policy frontier"
        )
    registry = JointPairCandidateRegistryV1(
        audit.model_id,
        audit.audit_id,
        audit.failed_frontier.frontier_id,
        threshold.threshold_profile_id,
        tuple(sorted(item.assignment_id for item in audit.assignments)),
        bridge.source_partial_row_ids,
        tuple(
            sorted(
                item.evidence_id
                for item in v0069_negative_run.candidate_evidence
            )
        ),
        tuple(sorted(excluded_binding_ids)),
        excluded_physical_ids,
        candidates_tuple,
    )
    return registry, by_partial, by_planner


def _build_gate_context(
    *,
    context: observer.PublicGraphContextV1,
    base_closure: h2_closure.ObservationSupportH2ClosureV1,
    transaction1: first_consumer.ObservationSupportPromotedH2ConsumerV1,
    v0069_negative_run: second.SecondSupportTransactionRunV1,
    threshold: robust.RobustThresholdProfileV1,
    registry: JointPairCandidateRegistryV1,
    caps: JointPairSupportCapsV1,
) -> JointPairSupportContextV1:
    audit = transaction1.audit
    assert audit.failed_frontier is not None
    return JointPairSupportContextV1(
        context.context_id,
        base_closure.closure_id,
        transaction1.consumer_id,
        v0069_negative_run.run_id,
        transaction1.promoted_closure.closure_id,
        transaction1.bridge.bridge_id,
        transaction1.bridge.quotient_model.model_id,
        audit.audit_id,
        audit.failed_frontier.frontier_id,
        threshold.threshold_profile_id,
        registry.selected_assignment_ids,
        registry.quarantined_v0069_evidence_ids,
        registry.registry_id,
        caps.cap_profile_id,
    )


def _joint_zero_other_model(
    model: robust.PartialSupportIntervalModelV1,
    planner_row_ids: tuple[str, ...],
) -> robust.PartialSupportIntervalModelV1:
    row_ids = _ids(planner_row_ids, "zero-OTHER planner rows")
    if len(row_ids) not in (1, 2):
        raise ObservationSupportJointPairInvariantViolation(
            "only singleton or pair zero-OTHER overlays are registered"
        )
    present = {item.row_id for item in model.rows}
    if not set(row_ids).issubset(present):
        raise ObservationSupportJointPairInvariantViolation(
            "zero-OTHER overlay references an absent planner row"
        )
    replacements: dict[str, robust.IntervalSimplexRowV1] = {}
    for row in model.rows:
        if row.row_id not in row_ids:
            continue
        replacements[row.row_id] = replace(
            row,
            masses=tuple(
                (
                    robust.IntervalDestinationMassV1(
                        item.destination_id,
                        Fraction(0),
                        Fraction(0),
                    )
                    if item.destination_id == row.other_destination_id
                    else item
                )
                for item in row.masses
            ),
        )
    return robust.build_partial_support_model_v1(
        context_id=model.context_id,
        root_state_id=model.root_state_id,
        catalogues=model.catalogues,
        destinations=model.destinations,
        rows=(
            replacements.get(item.row_id, item) for item in model.rows
        ),
        concretizer_entries=model.concretizer_entries,
    )


def _fixed_policy_metrics_operational(
    model: robust.PartialSupportIntervalModelV1,
    audit: robust.RobustPlanAuditV1,
    threshold: robust.RobustThresholdProfileV1,
) -> tuple[Fraction, Fraction, Fraction, Fraction]:
    """Evaluate exactly one frozen quotient policy, H1 before H2."""

    if (
        audit.solver_kind is not robust.RobustSolverKind.QUOTIENT
        or any(
            item.scope is not robust.PolicyScope.QUOTIENT_CELL
            for item in audit.assignments
        )
    ):
        raise ObservationSupportJointPairInvariantViolation(
            "fixed-policy Gate requires quotient-cell assignments"
        )
    assignment = {
        (item.scope_key, item.remaining_horizon): item.selected_action_key
        for item in audit.assignments
    }
    if len(assignment) != len(audit.assignments):
        raise ObservationSupportJointPairInvariantViolation(
            "frozen policy has duplicate assignment scopes"
        )
    catalogue_by_state, _, _ = robust._registries(model)
    child_states = robust._reachable_child_states(model)
    child_values: dict[str, robust._StateActionEvaluation] = {}
    expected_keys: set[tuple[str, int]] = set()
    for state_id in child_states:
        cell = catalogue_by_state[state_id].state_coordinate_key
        key = (cell, 1)
        expected_keys.add(key)
        action = assignment.get(key)
        if action is None:
            raise ObservationSupportJointPairInvariantViolation(
                "frozen policy omits a reachable H1 quotient cell"
            )
        child_values[state_id] = robust._evaluate_concretized_state_action(
            model,
            threshold,
            state_id=state_id,
            remaining_horizon=1,
            abstract_action_key=action,
            child_values={},
            category=(
                robust.SelectedRowCategory
                .CONTINUATION_CONCRETIZER_COMPONENT
            ),
        )
    root_cell = catalogue_by_state[
        model.root_state_id
    ].state_coordinate_key
    root_key = (root_cell, 2)
    expected_keys.add(root_key)
    root_action = assignment.get(root_key)
    if root_action is None or set(assignment) != expected_keys:
        raise ObservationSupportJointPairInvariantViolation(
            "frozen policy assignment domain changed under overlay"
        )
    root = robust._evaluate_concretized_state_action(
        model,
        threshold,
        state_id=model.root_state_id,
        remaining_horizon=2,
        abstract_action_key=root_action,
        child_values=child_values,
        category=robust.SelectedRowCategory.ROOT_CONCRETIZER_COMPONENT,
    )
    regret = max(
        Fraction(0),
        audit.unrestricted_reward_upper - root.reward_lower,
    ) / threshold.reward_ceiling
    slack = min(
        threshold.risk_tolerance - root.failure_upper,
        threshold.normalized_regret_tolerance - regret,
    )
    return root.reward_lower, root.failure_upper, regret, slack


@dataclass(frozen=True, slots=True)
class _SubsetBatchTaskV1:
    model: robust.PartialSupportIntervalModelV1
    audit: robust.RobustPlanAuditV1
    threshold: robust.RobustThresholdProfileV1
    registry: JointPairCandidateRegistryV1
    subsets: tuple[tuple[JointPairCandidateRowV1, ...], ...]


def _evaluate_subset_operational(
    *,
    model: robust.PartialSupportIntervalModelV1,
    audit: robust.RobustPlanAuditV1,
    threshold: robust.RobustThresholdProfileV1,
    registry: JointPairCandidateRegistryV1,
    candidates: tuple[JointPairCandidateRowV1, ...],
) -> ModelOnlySubsetEvidenceV1:
    planner_ids = tuple(
        sorted(item.planner_row_id for item in candidates)
    )
    candidate_ids = tuple(sorted(item.candidate_id for item in candidates))
    partial_ids = tuple(sorted(item.partial_row_id for item in candidates))
    try:
        zero_model = _joint_zero_other_model(model, planner_ids)
    except robust.PartialSupportRobustPlannerInvariantViolation:
        return ModelOnlySubsetEvidenceV1(
            registry.registry_id,
            model.model_id,
            audit.audit_id,
            threshold.threshold_profile_id,
            registry.selected_assignment_ids,
            candidate_ids,
            planner_ids,
            partial_ids,
            None,
            None,
            None,
            None,
            None,
            ModelOnlySubsetStatus.INFEASIBLE_SIMPLEX,
            len(candidates),
        )
    reward, failure, regret, slack = _fixed_policy_metrics_operational(
        zero_model,
        audit,
        threshold,
    )
    return ModelOnlySubsetEvidenceV1(
        registry.registry_id,
        model.model_id,
        audit.audit_id,
        threshold.threshold_profile_id,
        registry.selected_assignment_ids,
        candidate_ids,
        planner_ids,
        partial_ids,
        zero_model.model_id,
        reward,
        failure,
        regret,
        slack,
        (
            ModelOnlySubsetStatus.FIXED_PLAN_CERTIFIED
            if slack >= 0
            else ModelOnlySubsetStatus.STILL_FAILED
        ),
        len(candidates),
    )


def _evaluate_subset_batch_v1(
    task: _SubsetBatchTaskV1,
) -> tuple[ModelOnlySubsetEvidenceV1, ...]:
    return tuple(
        _evaluate_subset_operational(
            model=task.model,
            audit=task.audit,
            threshold=task.threshold,
            registry=task.registry,
            candidates=subset,
        )
        for subset in task.subsets
    )


def _model_only_evidence(
    *,
    model: robust.PartialSupportIntervalModelV1,
    audit: robust.RobustPlanAuditV1,
    threshold: robust.RobustThresholdProfileV1,
    registry: JointPairCandidateRegistryV1,
    subsets: tuple[tuple[JointPairCandidateRowV1, ...], ...],
    max_workers: int,
) -> tuple[ModelOnlySubsetEvidenceV1, ...]:
    if not subsets:
        return ()
    if max_workers == 1 or len(subsets) == 1:
        raw = _evaluate_subset_batch_v1(
            _SubsetBatchTaskV1(
                model,
                audit,
                threshold,
                registry,
                subsets,
            )
        )
    else:
        batch_count = min(max_workers, len(subsets))
        width = (len(subsets) + batch_count - 1) // batch_count
        tasks = tuple(
            _SubsetBatchTaskV1(
                model,
                audit,
                threshold,
                registry,
                subsets[index : index + width],
            )
            for index in range(0, len(subsets), width)
        )
        with ProcessPoolExecutor(
            max_workers=min(max_workers, len(tasks)),
            mp_context=get_context("spawn"),
        ) as executor:
            chunks = tuple(executor.map(_evaluate_subset_batch_v1, tasks))
        raw = tuple(item for chunk in chunks for item in chunk)
    return tuple(sorted(raw, key=lambda item: item.evidence_id))


def _materialization_cardinality(
    *,
    context: observer.PublicGraphContextV1,
    transaction1: first_consumer.ObservationSupportPromotedH2ConsumerV1,
    registry: JointPairCandidateRegistryV1,
    evidence: ModelOnlySubsetEvidenceV1,
    by_partial: Mapping[str, acquisition.GraphPartialSupportRowV1],
) -> JointPairMaterializationCardinalityV1:
    if (
        evidence.subset_cardinality != 2
        or not evidence.fixed_plan_certified
    ):
        raise ObservationSupportJointPairInvariantViolation(
            "cardinality may be computed only for one fixed-plan pair cover"
        )
    selected_rows = tuple(by_partial[item] for item in evidence.partial_row_ids)
    existing_catalogue_ids = {
        item.catalogue_id
        for item in transaction1.promoted_closure.child_catalogues
    }
    new_by_id: dict[str, observer.LegalActionCatalogueV1] = {}
    for row in selected_rows:
        if row.binding.remaining_horizon != 2:
            continue
        for descriptor in row.novel_descriptors:
            if descriptor.failure or descriptor.terminal:
                continue
            catalogue = observer.legal_action_catalogue_v1(
                context,
                descriptor.next_state,
                1,
            )
            if catalogue.catalogue_id in existing_catalogue_ids:
                continue
            prior = new_by_id.setdefault(catalogue.catalogue_id, catalogue)
            if prior != catalogue:
                raise ObservationSupportJointPairInvariantViolation(
                    "one predicted catalogue ID has conflicting content"
                )
    new_catalogues = tuple(new_by_id[key] for key in sorted(new_by_id))
    binding_keys = tuple(
        sorted(
            (
                catalogue.catalogue_id,
                action,
            )
            for catalogue in new_catalogues
            for action in catalogue.actions
        )
    )
    draws = 2 * REGISTERED_PROMOTION_CHECKPOINT + len(binding_keys) * (
        acquisition.DISCOVERY_DRAW_COUNT
        + REGISTERED_NEW_CHILD_CHECKPOINT
    )
    within = (
        len(new_catalogues) <= MAX_NEW_CHILD_CATALOGUES
        and len(binding_keys) <= MAX_NEW_CHILD_ACTION_ROWS
        and draws <= MAX_INCREMENTAL_OBSERVER_DRAWS
    )
    return JointPairMaterializationCardinalityV1(
        registry.registry_id,
        evidence.evidence_id,
        evidence.planner_row_ids,  # type: ignore[arg-type]
        tuple(item.catalogue_id for item in new_catalogues),
        binding_keys,
        2 * REGISTERED_PROMOTION_CHECKPOINT,
        len(binding_keys),
        draws,
        within,
        draws < ALTERNATIVE_GLOBAL_16384_SUFFIX_DRAWS,
    )


def _select_pair(
    *,
    pair_evidence: tuple[ModelOnlySubsetEvidenceV1, ...],
    cardinality: tuple[JointPairMaterializationCardinalityV1, ...],
) -> tuple[
    ModelOnlySubsetEvidenceV1,
    JointPairMaterializationCardinalityV1,
] | None:
    evidence_by_id = {item.evidence_id: item for item in pair_evidence}
    admissible = tuple(
        (
            evidence_by_id[item.pair_evidence_id],
            item,
        )
        for item in cardinality
        if (
            item.within_registered_caps
            and item.avoids_further_global_checkpoint_tax
        )
    )
    if not admissible:
        return None
    return min(
        admissible,
        key=lambda pair: (
            pair[1].incremental_draw_upper,
            -pair[0].minimum_certificate_slack,  # type: ignore[operator]
            pair[0].planner_row_ids,
        ),
    )


def _authorize_pair(
    *,
    gate_context: JointPairSupportContextV1,
    registry: JointPairCandidateRegistryV1,
    evidence: ModelOnlySubsetEvidenceV1,
    cardinality: JointPairMaterializationCardinalityV1,
) -> JointPairSupportAuthorizationV1:
    by_candidate = {
        item.candidate_id: item for item in registry.candidates
    }
    selected = tuple(by_candidate[item] for item in evidence.candidate_ids)
    if (
        cardinality.pair_evidence_id != evidence.evidence_id
        or cardinality.registry_id != registry.registry_id
        or not cardinality.within_registered_caps
        or not cardinality.avoids_further_global_checkpoint_tax
    ):
        raise ObservationSupportJointPairInvariantViolation(
            "selected pair lacks a budget-admissible cardinality proof"
        )
    return JointPairSupportAuthorizationV1(
        gate_context.context_id,
        registry.registry_id,
        registry.parent_model_id,
        registry.parent_audit_id,
        registry.parent_frontier_id,
        registry.threshold_profile_id,
        registry.selected_assignment_ids,
        evidence.evidence_id,
        cardinality.cardinality_id,
        evidence.candidate_ids,  # type: ignore[arg-type]
        evidence.planner_row_ids,  # type: ignore[arg-type]
        evidence.partial_row_ids,  # type: ignore[arg-type]
        tuple(sorted(item.binding_id for item in selected)),
        tuple(
            sorted(item.physical_evidence_id for item in selected)
        ),
        tuple(sorted(item.support_epoch_id for item in selected)),
        tuple(
            sorted(item.confidence_authority_id for item in selected)
        ),
        tuple(
            sorted(
                {
                    outcome_id
                    for item in selected
                    for outcome_id in item.novel_outcome_ids
                }
            )
        ),
        gate_context.cap_profile_id,
    )


def _catalogue_for_row(
    closure: first_consumer.ObservationSupportPromotedH2ClosureV1,
    row: acquisition.GraphPartialSupportRowV1,
) -> observer.LegalActionCatalogueV1:
    matches = tuple(
        item
        for item in closure.public_catalogues
        if item.catalogue_id == row.binding.catalogue_id
    )
    if len(matches) != 1 or row.binding.action not in matches[0].actions:
        raise ObservationSupportJointPairInvariantViolation(
            "selected row has no exact public action catalogue"
        )
    return matches[0]


def _promote_pair(
    *,
    context: observer.PublicGraphContextV1,
    transaction1: first_consumer.ObservationSupportPromotedH2ConsumerV1,
    authorization: JointPairSupportAuthorizationV1,
) -> tuple[
    JointPairPromotedRowReplacementV1,
    JointPairPromotedRowReplacementV1,
]:
    by_partial = {
        row.partial_row_id: row
        for row in transaction1.promoted_closure.all_rows
    }
    raw: list[JointPairPromotedRowReplacementV1] = []
    for sequence, partial_row_id in enumerate(
        authorization.selected_partial_row_ids,
        start=2,
    ):
        parent = by_partial[partial_row_id]
        catalogue = _catalogue_for_row(
            transaction1.promoted_closure,
            parent,
        )
        promoted = acquisition.promote_graph_partial_support_row_v1(
            parent,
            context,
            catalogue,
            parent.binding.action,
            REGISTERED_PROMOTION_CHECKPOINT,
        )
        raw.append(
            JointPairPromotedRowReplacementV1(
                authorization.authorization_id,
                parent,
                promoted,
                tuple(
                    sorted(
                        {
                            *parent.initial_discovery_observation_ids,
                            *parent.prior_validation_observation_ids,
                            *parent.current_validation_observation_ids,
                        }
                    )
                ),
                tuple(
                    sorted(
                        promoted.current_validation_observation_ids
                    )
                ),
                sequence,
            )
        )
    return tuple(  # type: ignore[return-value]
        sorted(raw, key=lambda item: item.replacement_id)
    )


def _replace_pair_rows(
    rows: tuple[acquisition.GraphPartialSupportRowV1, ...],
    replacements: tuple[
        JointPairPromotedRowReplacementV1,
        JointPairPromotedRowReplacementV1,
    ],
) -> tuple[acquisition.GraphPartialSupportRowV1, ...]:
    by_parent = {
        item.parent_row.partial_row_id: item.promoted_row
        for item in replacements
    }
    return _sorted_rows(
        by_parent.get(row.partial_row_id, row) for row in rows
    )


@dataclass(frozen=True, slots=True)
class _AcquireChildTaskV1:
    context: observer.PublicGraphContextV1
    catalogue: observer.LegalActionCatalogueV1
    action: tuple[int, int, int]


def _acquire_child_task_v1(
    task: _AcquireChildTaskV1,
) -> acquisition.GraphPartialSupportRowV1:
    return acquisition.acquire_graph_partial_support_row_v1(
        task.context,
        task.catalogue,
        task.action,
        REGISTERED_NEW_CHILD_CHECKPOINT,
    )


def _materialized_counters(
    *,
    eligible_count: int,
    singleton_count: int,
    pair_count: int,
    cover_count: int,
    cardinality_count: int,
    replacements: tuple[
        JointPairPromotedRowReplacementV1,
        JointPairPromotedRowReplacementV1,
    ],
    new_catalogue_count: int,
    new_rows: tuple[acquisition.GraphPartialSupportRowV1, ...],
) -> JointPairSupportCountersV1:
    promotion_draws = sum(
        item.promoted_row.counters.current_validation_draws
        for item in replacements
    )
    promotion_words = sum(
        item.promoted_row.counters.current_validation_random_word_calls
        for item in replacements
    )
    promotion_rejections = sum(
        item.promoted_row.counters.current_validation_rejections
        for item in replacements
    )
    child_discovery = sum(
        item.counters.discovery_draws for item in new_rows
    )
    child_validation = sum(
        item.counters.current_validation_draws for item in new_rows
    )
    child_words = sum(
        item.counters.total_random_word_calls for item in new_rows
    )
    child_rejections = sum(
        item.counters.total_rejections for item in new_rows
    )
    child_draws = child_discovery + child_validation
    return JointPairSupportCountersV1(
        eligible_count,
        singleton_count,
        pair_count,
        cover_count,
        cardinality_count,
        1,
        2,
        promotion_draws,
        promotion_words,
        promotion_rejections,
        new_catalogue_count,
        len(new_rows),
        child_discovery,
        child_validation,
        child_draws,
        child_words,
        child_rejections,
        promotion_draws + child_draws,
        promotion_words + child_words,
        promotion_rejections + child_rejections,
        1,
        6,
        0,
    )


def _nonmaterialized_counters(
    *,
    eligible_count: int,
    singleton_count: int,
    pair_count: int,
    cover_count: int,
    cardinality_count: int,
    cap_rejections: int,
) -> JointPairSupportCountersV1:
    return JointPairSupportCountersV1(
        eligible_count,
        singleton_count,
        pair_count,
        cover_count,
        cardinality_count,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        6,
        cap_rejections,
    )


def run_joint_pair_support_recovery_v1(
    *,
    context: observer.PublicGraphContextV1,
    base_closure: h2_closure.ObservationSupportH2ClosureV1,
    base_bridge: graph_model.ObservationSupportGraphModelBridgeV1,
    base_audit: robust.RobustPlanAuditV1,
    threshold: robust.RobustThresholdProfileV1,
    transaction1: first_consumer.ObservationSupportPromotedH2ConsumerV1,
    v0069_negative_run: second.SecondSupportTransactionRunV1,
    max_workers: int = 1,
) -> JointPairSupportRunV1:
    """Run the bounded K6 fixed-policy ``k <= 2`` causal-cover Gate."""

    registered = _registered_k6(context)
    workers = _workers(max_workers)
    caps = registered_joint_pair_caps_v1()
    _validate_parent_chain(
        context=registered,
        base_closure=base_closure,
        base_bridge=base_bridge,
        base_audit=base_audit,
        threshold=threshold,
        transaction1=transaction1,
        v0069_negative_run=v0069_negative_run,
    )
    registry, by_partial, _ = _reconstruct_candidate_registry(
        transaction1=transaction1,
        v0069_negative_run=v0069_negative_run,
        threshold=threshold,
    )
    gate_context = _build_gate_context(
        context=registered,
        base_closure=base_closure,
        transaction1=transaction1,
        v0069_negative_run=v0069_negative_run,
        threshold=threshold,
        registry=registry,
        caps=caps,
    )
    eligible_count = len(registry.candidates)
    if eligible_count > caps.max_eligible_rows:
        counters = _nonmaterialized_counters(
            eligible_count=eligible_count,
            singleton_count=0,
            pair_count=0,
            cover_count=0,
            cardinality_count=0,
            cap_rejections=1,
        )
        return JointPairSupportRunV1(
            gate_context,
            registry,
            JointPairOutcome.PAIR_COUNTERFACTUAL_CAP_EXHAUSTED,
            (),
            (),
            (),
            None,
            None,
            None,
            (),
            None,
            None,
            None,
            counters,
        )
    model = transaction1.bridge.quotient_model
    audit = transaction1.audit
    singleton_subsets = tuple((item,) for item in registry.candidates)
    singleton_evidence = _model_only_evidence(
        model=model,
        audit=audit,
        threshold=threshold,
        registry=registry,
        subsets=singleton_subsets,
        max_workers=workers,
    )
    if any(item.fixed_plan_certified for item in singleton_evidence):
        counters = _nonmaterialized_counters(
            eligible_count=eligible_count,
            singleton_count=len(singleton_evidence),
            pair_count=0,
            cover_count=0,
            cardinality_count=0,
            cap_rejections=1,
        )
        return JointPairSupportRunV1(
            gate_context,
            registry,
            JointPairOutcome.PROTOCOL_FAILURE,
            singleton_evidence,
            (),
            (),
            None,
            None,
            None,
            (),
            None,
            None,
            None,
            counters,
        )
    pair_subsets = tuple(
        tuple(pair)
        for pair in itertools.combinations(registry.candidates, 2)
    )
    if len(pair_subsets) > caps.max_pair_overlay_evaluations:
        counters = _nonmaterialized_counters(
            eligible_count=eligible_count,
            singleton_count=len(singleton_evidence),
            pair_count=0,
            cover_count=0,
            cardinality_count=0,
            cap_rejections=1,
        )
        return JointPairSupportRunV1(
            gate_context,
            registry,
            JointPairOutcome.PAIR_COUNTERFACTUAL_CAP_EXHAUSTED,
            singleton_evidence,
            (),
            (),
            None,
            None,
            None,
            (),
            None,
            None,
            None,
            counters,
        )
    pair_evidence = _model_only_evidence(
        model=model,
        audit=audit,
        threshold=threshold,
        registry=registry,
        subsets=pair_subsets,
        max_workers=workers,
    )
    covers = tuple(
        item for item in pair_evidence if item.fixed_plan_certified
    )
    if not covers:
        counters = _nonmaterialized_counters(
            eligible_count=eligible_count,
            singleton_count=len(singleton_evidence),
            pair_count=len(pair_evidence),
            cover_count=0,
            cardinality_count=0,
            cap_rejections=0,
        )
        return JointPairSupportRunV1(
            gate_context,
            registry,
            JointPairOutcome.NO_SOUND_FIXED_PLAN_PAIR_COVER,
            singleton_evidence,
            pair_evidence,
            (),
            None,
            None,
            None,
            (),
            None,
            None,
            None,
            counters,
        )
    cardinality = tuple(
        sorted(
            (
                _materialization_cardinality(
                    context=registered,
                    transaction1=transaction1,
                    registry=registry,
                    evidence=item,
                    by_partial=by_partial,
                )
                for item in covers
            ),
            key=lambda item: item.cardinality_id,
        )
    )
    selected = _select_pair(
        pair_evidence=pair_evidence,
        cardinality=cardinality,
    )
    if selected is None:
        counters = _nonmaterialized_counters(
            eligible_count=eligible_count,
            singleton_count=len(singleton_evidence),
            pair_count=len(pair_evidence),
            cover_count=len(covers),
            cardinality_count=len(cardinality),
            cap_rejections=len(cardinality),
        )
        return JointPairSupportRunV1(
            gate_context,
            registry,
            JointPairOutcome.PAIR_COVER_SAMPLE_BUDGET_DOMINATED,
            singleton_evidence,
            pair_evidence,
            cardinality,
            None,
            None,
            None,
            (),
            None,
            None,
            None,
            counters,
        )
    selected_evidence, selected_cardinality = selected
    authorization = _authorize_pair(
        gate_context=gate_context,
        registry=registry,
        evidence=selected_evidence,
        cardinality=selected_cardinality,
    )

    # The authorization identity is frozen above before either stream opens.
    _ = authorization.authorization_id
    replacements = _promote_pair(
        context=registered,
        transaction1=transaction1,
        authorization=authorization,
    )
    parent_closure = transaction1.promoted_closure
    parent_rows = parent_closure.all_rows
    selected_parent_ids = {
        item.parent_row.partial_row_id for item in replacements
    }
    if sum(
        row.partial_row_id in selected_parent_ids for row in parent_rows
    ) != 2:
        raise ObservationSupportJointPairInvariantViolation(
            "joint authorization does not replace exactly two parent rows"
        )
    root_rows = _replace_pair_rows(parent_closure.root_rows, replacements)
    child_rows = _replace_pair_rows(parent_closure.child_rows, replacements)
    child_catalogues = _sorted_catalogues(
        observer.legal_action_catalogue_v1(registered, state, 1)
        for state in _active_root_states(root_rows)
    )
    prior_catalogue_ids = {
        item.catalogue_id for item in parent_closure.child_catalogues
    }
    new_catalogues = tuple(
        item
        for item in child_catalogues
        if item.catalogue_id not in prior_catalogue_ids
    )
    tasks = tuple(
        _AcquireChildTaskV1(registered, catalogue, action)
        for catalogue in new_catalogues
        for action in catalogue.actions
    )
    actual_binding_keys = tuple(
        sorted(
            (task.catalogue.catalogue_id, task.action)
            for task in tasks
        )
    )
    predicted_catalogues = (
        selected_cardinality.new_child_catalogue_ids
    )
    if (
        tuple(item.catalogue_id for item in new_catalogues)
        != predicted_catalogues
        or actual_binding_keys
        != selected_cardinality.new_child_binding_keys
        or len(new_catalogues) > caps.max_new_child_catalogues
        or len(tasks) > caps.max_new_child_action_rows
    ):
        raise ObservationSupportJointPairInvariantViolation(
            "post-authorization materialization differs from frozen cardinality"
        )
    if workers == 1 or len(tasks) <= 1:
        new_rows = tuple(_acquire_child_task_v1(task) for task in tasks)
    else:
        with ProcessPoolExecutor(
            max_workers=min(workers, len(tasks)),
            mp_context=get_context("spawn"),
        ) as executor:
            new_rows = tuple(executor.map(_acquire_child_task_v1, tasks))
    new_rows = _sorted_rows(new_rows) if new_rows else ()
    child_rows = _sorted_rows((*child_rows, *new_rows))
    profile = relational.base_coordinate_profile_v1()
    if transaction1.coordinate_profile_id != profile.profile_id:
        raise ObservationSupportJointPairInvariantViolation(
            "joint recovery cannot change the coordinate profile"
        )
    bridge = graph_model.build_observation_support_graph_models_v1(
        context=registered,
        root_catalogue=parent_closure.root_catalogue,
        catalogues=(parent_closure.root_catalogue, *child_catalogues),
        partial_rows=(*root_rows, *child_rows),
        coordinate_profile=profile,
    )
    # Exactly one operational full policy search is permitted, after sampling.
    final_audit = robust.solve_quotient_robust_h2_v1(
        bridge.quotient_model,
        threshold,
    )
    counters = _materialized_counters(
        eligible_count=eligible_count,
        singleton_count=len(singleton_evidence),
        pair_count=len(pair_evidence),
        cover_count=len(covers),
        cardinality_count=len(cardinality),
        replacements=replacements,
        new_catalogue_count=len(new_catalogues),
        new_rows=new_rows,
    )
    if (
        counters.incremental_observer_draws
        != selected_cardinality.incremental_draw_upper
    ):
        raise ObservationSupportJointPairInvariantViolation(
            "actual observer draws differ from the frozen upper"
        )
    closure = JointPairPromotedH2ClosureV1(
        gate_context.context_id,
        transaction1.consumer_id,
        authorization,
        replacements,
        registered,
        parent_closure.root_catalogue,
        child_catalogues,
        root_rows,
        child_rows,
        tuple(
            sorted(
                row.binding.row_id
                for row in (*root_rows, *child_rows)
                if row.support_epoch_index == 2
            )
        ),
        tuple(item.catalogue_id for item in new_catalogues),
        tuple(sorted(item.partial_row_id for item in new_rows)),
        counters,
    )
    outcome = (
        JointPairOutcome.CERTIFIED_AT_8192_AFTER_JOINT_PAIR
        if final_audit.certified
        else JointPairOutcome.FAILED_NEW_FRONTIER_AFTER_JOINT_PAIR
    )
    return JointPairSupportRunV1(
        gate_context,
        registry,
        outcome,
        singleton_evidence,
        pair_evidence,
        cardinality,
        selected_evidence.evidence_id,
        selected_cardinality.cardinality_id,
        authorization,
        replacements,
        closure,
        bridge,
        final_audit,
        counters,
    )


def freeze_k6_joint_pair_support_probe_v0(
    *,
    context: observer.PublicGraphContextV1,
    base_closure: h2_closure.ObservationSupportH2ClosureV1,
    transaction1: first_consumer.ObservationSupportPromotedH2ConsumerV1,
    v0069_negative_run: second.SecondSupportTransactionRunV1,
    run: JointPairSupportRunV1,
) -> K6JointPairSupportProbeV0:
    registered = _registered_k6(context)
    if (
        type(base_closure)
        is not h2_closure.ObservationSupportH2ClosureV1
        or base_closure.context != registered
        or base_closure.validation_checkpoint != REGISTERED_BASE_CHECKPOINT
        or type(transaction1)
        is not first_consumer.ObservationSupportPromotedH2ConsumerV1
        or type(v0069_negative_run)
        is not second.SecondSupportTransactionRunV1
        or type(run) is not JointPairSupportRunV1
        or run.context.public_context_id != registered.context_id
        or run.context.base_closure_id != base_closure.closure_id
        or run.context.transaction1_consumer_id
        != transaction1.consumer_id
        or run.context.v0069_negative_run_id
        != v0069_negative_run.run_id
    ):
        raise ObservationSupportJointPairInvariantViolation(
            "joint-pair probe freeze inputs are stale"
        )
    exact = None
    if (
        run.outcome
        is JointPairOutcome.CERTIFIED_AT_8192_AFTER_JOINT_PAIR
    ):
        assert run.bridge is not None and run.audit is not None
        _ = run.run_id
        exact = exact_evaluation.evaluate_observation_support_exact_lift_v1(
            registered,
            run.bridge,
            run.audit,
            prerequisite_operational_freeze_id=run.run_id,
        )
        exact_evaluation.verify_observation_support_exact_lift_v1(
            registered,
            run.bridge,
            run.audit,
            exact,
        )
    return K6JointPairSupportProbeV0(
        registered.context_id,
        base_closure.closure_id,
        transaction1.consumer_id,
        v0069_negative_run.run_id,
        run,
        exact,
    )


def run_k6_joint_pair_support_probe_v0(
    *,
    max_workers: int = 1,
) -> K6JointPairSupportProbeV0:
    """Build K6@8192, V0-068/V0-069, then execute V0-070."""

    workers = _workers(max_workers)
    context = observer.public_context_by_key_v1(REGISTERED_CONTEXT_KEY)
    base_closure = h2_closure.acquire_observation_support_h2_closure_v1(
        context,
        REGISTERED_BASE_CHECKPOINT,
        max_workers=workers,
    )
    base_bridge = graph_model.build_observation_support_graph_models_v1(
        context=context,
        root_catalogue=base_closure.root_catalogue,
        catalogues=(
            base_closure.root_catalogue,
            *base_closure.child_catalogues,
        ),
        partial_rows=base_closure.all_rows,
    )
    threshold = robust.RobustThresholdProfileV1(
        context.context_id,
        context.risk_tolerance,
        base_bridge.reward_ceiling,
    )
    base_audit = robust.solve_quotient_robust_h2_v1(
        base_bridge.quotient_model,
        threshold,
    )
    authorization1 = expansion.authorize_partial_support_expansion_v1(
        bridge=base_bridge,
        audit=base_audit,
        threshold=threshold,
        partial_rows=base_closure.all_rows,
        checkpoint_draw_count=REGISTERED_PROMOTION_CHECKPOINT,
    )
    replacement1 = expansion.promote_authorized_partial_support_row_v1(
        bridge=base_bridge,
        audit=base_audit,
        threshold=threshold,
        partial_rows=base_closure.all_rows,
        authorization=authorization1,
    )
    transaction1 = (
        first_consumer.consume_partial_support_promoted_row_replacement_v1(
            context=context,
            parent_closure=base_closure,
            parent_bridge=base_bridge,
            parent_audit=base_audit,
            threshold=threshold,
            replacement=replacement1,
            new_child_validation_checkpoint=(
                REGISTERED_NEW_CHILD_CHECKPOINT
            ),
            max_workers=workers,
        )
    )
    v0069 = second.run_second_support_transaction_v1(
        context=context,
        base_closure=base_closure,
        base_bridge=base_bridge,
        base_audit=base_audit,
        threshold=threshold,
        transaction1=transaction1,
        max_workers=workers,
    )
    run = run_joint_pair_support_recovery_v1(
        context=context,
        base_closure=base_closure,
        base_bridge=base_bridge,
        base_audit=base_audit,
        threshold=threshold,
        transaction1=transaction1,
        v0069_negative_run=v0069,
        max_workers=workers,
    )
    return freeze_k6_joint_pair_support_probe_v0(
        context=context,
        base_closure=base_closure,
        transaction1=transaction1,
        v0069_negative_run=v0069,
        run=run,
    )


def _independent_extreme_expectation(
    masses: Sequence[robust.IntervalDestinationMassV1],
    values: Mapping[str, Fraction],
    *,
    maximize: bool,
) -> Fraction:
    if {item.destination_id for item in masses} != set(values):
        raise ObservationSupportJointPairInvariantViolation(
            "independent expectation registry differs from row masses"
        )
    allocations = {
        item.destination_id: item.lower for item in masses
    }
    residual = Fraction(1) - sum(allocations.values(), Fraction(0))
    ordered = sorted(
        masses,
        key=lambda item: (
            -values[item.destination_id]
            if maximize
            else values[item.destination_id],
            item.destination_id,
        ),
    )
    for item in ordered:
        if residual == 0:
            break
        increment = min(residual, item.upper - item.lower)
        allocations[item.destination_id] += increment
        residual -= increment
    if residual != 0:
        raise ObservationSupportJointPairInvariantViolation(
            "independent interval simplex is infeasible"
        )
    return sum(
        allocations[item.destination_id] * values[item.destination_id]
        for item in masses
    )


def _independent_fixed_policy_metrics(
    model: robust.PartialSupportIntervalModelV1,
    audit: robust.RobustPlanAuditV1,
    threshold: robust.RobustThresholdProfileV1,
) -> tuple[Fraction, Fraction, Fraction, Fraction]:
    """Independent implementation of the fixed-policy H1->H2 recurrence."""

    catalogue_by_state = {item.state_id: item for item in model.catalogues}
    destination_by_id = {
        item.destination_id: item for item in model.destinations
    }
    row_by_key = {item.row_key: item for item in model.rows}
    concretizer = {
        (
            item.state_coordinate_key,
            item.state_id,
            item.abstract_action_key,
        ): item
        for item in model.concretizer_entries
    }
    assignment = {
        (item.scope_key, item.remaining_horizon): item.selected_action_key
        for item in audit.assignments
    }
    if (
        len(assignment) != len(audit.assignments)
        or any(
            item.scope is not robust.PolicyScope.QUOTIENT_CELL
            for item in audit.assignments
        )
    ):
        raise ObservationSupportJointPairInvariantViolation(
            "independent replay received a non-quotient frozen policy"
        )

    child_states: set[str] = set()
    root_catalogue = catalogue_by_state[model.root_state_id]
    for action in root_catalogue.actions:
        row = row_by_key[(model.root_state_id, 2, action.action_id)]
        for mass in row.masses:
            destination = destination_by_id[mass.destination_id]
            if (
                mass.upper > 0
                and destination.category
                is robust.DestinationCategory.ACTIVE_STATE
            ):
                assert destination.state_id is not None
                child_states.add(destination.state_id)

    def ground_row(
        row: robust.IntervalSimplexRowV1,
        child_values: Mapping[str, tuple[Fraction, Fraction]],
    ) -> tuple[Fraction, Fraction]:
        reward_values: dict[str, Fraction] = {}
        risk_values: dict[str, Fraction] = {}
        for mass in row.masses:
            destination = destination_by_id[mass.destination_id]
            active = (
                destination.category
                is robust.DestinationCategory.ACTIVE_STATE
                and row.remaining_horizon > 1
            )
            if active:
                assert destination.state_id is not None
                child_reward, child_risk = child_values[
                    destination.state_id
                ]
                reward_values[mass.destination_id] = child_reward
                risk_values[mass.destination_id] = child_risk
            else:
                reward_values[mass.destination_id] = Fraction(0)
                risk_values[mass.destination_id] = (
                    Fraction(1)
                    if destination.category
                    in (
                        robust.DestinationCategory.FAILURE,
                        robust.DestinationCategory.OTHER,
                    )
                    else Fraction(0)
                )
        reward = row.reward_lower + _independent_extreme_expectation(
            row.masses,
            reward_values,
            maximize=False,
        )
        failure = _independent_extreme_expectation(
            row.masses,
            risk_values,
            maximize=True,
        )
        return reward, failure

    def abstract_action(
        *,
        state_id: str,
        horizon: int,
        action_key: str,
        child_values: Mapping[str, tuple[Fraction, Fraction]],
    ) -> tuple[Fraction, Fraction]:
        cell = catalogue_by_state[state_id].state_coordinate_key
        entry = concretizer.get((cell, state_id, action_key))
        if entry is None or not entry.ground_action_ids:
            raise ObservationSupportJointPairInvariantViolation(
                "independent replay lacks concretizer support"
            )
        values = tuple(
            ground_row(
                row_by_key[(state_id, horizon, action_id)],
                child_values,
            )
            for action_id in entry.ground_action_ids
        )
        denominator = len(values)
        return (
            sum((item[0] for item in values), Fraction(0))
            / denominator,
            sum((item[1] for item in values), Fraction(0))
            / denominator,
        )

    child_values: dict[str, tuple[Fraction, Fraction]] = {}
    expected_keys: set[tuple[str, int]] = set()
    for state_id in sorted(child_states):
        cell = catalogue_by_state[state_id].state_coordinate_key
        key = (cell, 1)
        expected_keys.add(key)
        action_key = assignment.get(key)
        if action_key is None:
            raise ObservationSupportJointPairInvariantViolation(
                "independent replay lacks a child assignment"
            )
        child_values[state_id] = abstract_action(
            state_id=state_id,
            horizon=1,
            action_key=action_key,
            child_values={},
        )
    root_cell = root_catalogue.state_coordinate_key
    root_key = (root_cell, 2)
    expected_keys.add(root_key)
    root_action = assignment.get(root_key)
    if root_action is None or set(assignment) != expected_keys:
        raise ObservationSupportJointPairInvariantViolation(
            "independent replay assignment domain changed"
        )
    reward, failure = abstract_action(
        state_id=model.root_state_id,
        horizon=2,
        action_key=root_action,
        child_values=child_values,
    )
    regret = max(
        Fraction(0),
        audit.unrestricted_reward_upper - reward,
    ) / threshold.reward_ceiling
    slack = min(
        threshold.risk_tolerance - failure,
        threshold.normalized_regret_tolerance - regret,
    )
    return reward, failure, regret, slack


def _independent_subset_evidence(
    *,
    model: robust.PartialSupportIntervalModelV1,
    audit: robust.RobustPlanAuditV1,
    threshold: robust.RobustThresholdProfileV1,
    registry: JointPairCandidateRegistryV1,
    candidates: tuple[JointPairCandidateRowV1, ...],
) -> ModelOnlySubsetEvidenceV1:
    planner_ids = tuple(
        sorted(item.planner_row_id for item in candidates)
    )
    candidate_ids = tuple(sorted(item.candidate_id for item in candidates))
    partial_ids = tuple(sorted(item.partial_row_id for item in candidates))
    try:
        zero_model = _joint_zero_other_model(model, planner_ids)
    except robust.PartialSupportRobustPlannerInvariantViolation:
        return ModelOnlySubsetEvidenceV1(
            registry.registry_id,
            model.model_id,
            audit.audit_id,
            threshold.threshold_profile_id,
            registry.selected_assignment_ids,
            candidate_ids,
            planner_ids,
            partial_ids,
            None,
            None,
            None,
            None,
            None,
            ModelOnlySubsetStatus.INFEASIBLE_SIMPLEX,
            len(candidates),
        )
    reward, failure, regret, slack = _independent_fixed_policy_metrics(
        zero_model,
        audit,
        threshold,
    )
    return ModelOnlySubsetEvidenceV1(
        registry.registry_id,
        model.model_id,
        audit.audit_id,
        threshold.threshold_profile_id,
        registry.selected_assignment_ids,
        candidate_ids,
        planner_ids,
        partial_ids,
        zero_model.model_id,
        reward,
        failure,
        regret,
        slack,
        (
            ModelOnlySubsetStatus.FIXED_PLAN_CERTIFIED
            if slack >= 0
            else ModelOnlySubsetStatus.STILL_FAILED
        ),
        len(candidates),
    )


@dataclass(frozen=True, slots=True)
class JointPairSupportVerificationV1:
    claimed_run_id: str
    replayed_run_id: str
    outcome: JointPairOutcome
    independently_replayed_subset_count: int
    independent_fixed_policy_recurrence: bool = True
    independent_full_planner_implementation: bool = False
    evaluation_lane_only: bool = True
    valid: bool = True

    def __post_init__(self) -> None:
        _cid(self.claimed_run_id, "claimed joint-pair run")
        _cid(self.replayed_run_id, "replayed joint-pair run")
        if (
            self.claimed_run_id != self.replayed_run_id
            or type(self.outcome) is not JointPairOutcome
            or type(self.independently_replayed_subset_count) is not int
            or self.independently_replayed_subset_count < 0
            or self.independent_fixed_policy_recurrence is not True
            or self.independent_full_planner_implementation is not False
            or self.evaluation_lane_only is not True
            or self.valid is not True
        ):
            raise ObservationSupportJointPairInvariantViolation(
                "joint-pair standalone verification failed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.joint_pair_support_verification.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "claimed_run_id": self.claimed_run_id,
            "replayed_run_id": self.replayed_run_id,
            "outcome": self.outcome.value,
            "independently_replayed_subset_count": (
                self.independently_replayed_subset_count
            ),
            "independent_fixed_policy_recurrence": True,
            "independent_full_planner_implementation": False,
            "evaluation_lane_only": True,
            "valid": True,
        }

    @property
    def verification_id(self) -> str:
        return _content_id("verification", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "verification_id": self.verification_id,
        }


def verify_joint_pair_support_recovery_v1(
    *,
    context: observer.PublicGraphContextV1,
    base_closure: h2_closure.ObservationSupportH2ClosureV1,
    base_bridge: graph_model.ObservationSupportGraphModelBridgeV1,
    base_audit: robust.RobustPlanAuditV1,
    threshold: robust.RobustThresholdProfileV1,
    transaction1: first_consumer.ObservationSupportPromotedH2ConsumerV1,
    v0069_negative_run: second.SecondSupportTransactionRunV1,
    claimed: JointPairSupportRunV1,
) -> JointPairSupportVerificationV1:
    """Standalone replay with an independent fixed-policy recurrence.

    The final full planner audit, if present, is deliberately verified with
    the existing same-implementation semantic replay and is not represented
    as an independent planner implementation.
    """

    if type(claimed) is not JointPairSupportRunV1:
        raise ObservationSupportJointPairInvariantViolation(
            "claimed joint-pair run has the wrong type"
        )
    registered = _registered_k6(context)
    _validate_parent_chain(
        context=registered,
        base_closure=base_closure,
        base_bridge=base_bridge,
        base_audit=base_audit,
        threshold=threshold,
        transaction1=transaction1,
        v0069_negative_run=v0069_negative_run,
    )
    registry, by_partial, _ = _reconstruct_candidate_registry(
        transaction1=transaction1,
        v0069_negative_run=v0069_negative_run,
        threshold=threshold,
    )
    caps = registered_joint_pair_caps_v1()
    gate_context = _build_gate_context(
        context=registered,
        base_closure=base_closure,
        transaction1=transaction1,
        v0069_negative_run=v0069_negative_run,
        threshold=threshold,
        registry=registry,
        caps=caps,
    )
    if (
        canonical_json_bytes(registry.to_document())
        != canonical_json_bytes(claimed.registry.to_document())
        or canonical_json_bytes(gate_context.to_document())
        != canonical_json_bytes(claimed.context.to_document())
    ):
        raise ObservationSupportJointPairInvariantViolation(
            "claimed registry/context differs from independent reconstruction"
        )
    eligible_count = len(registry.candidates)
    model = transaction1.bridge.quotient_model
    audit = transaction1.audit
    if eligible_count > caps.max_eligible_rows:
        singletons: tuple[ModelOnlySubsetEvidenceV1, ...] = ()
        pairs: tuple[ModelOnlySubsetEvidenceV1, ...] = ()
        cardinality: tuple[
            JointPairMaterializationCardinalityV1, ...
        ] = ()
        outcome = JointPairOutcome.PAIR_COUNTERFACTUAL_CAP_EXHAUSTED
        counters = _nonmaterialized_counters(
            eligible_count=eligible_count,
            singleton_count=0,
            pair_count=0,
            cover_count=0,
            cardinality_count=0,
            cap_rejections=1,
        )
    else:
        singletons = tuple(
            sorted(
                (
                    _independent_subset_evidence(
                        model=model,
                        audit=audit,
                        threshold=threshold,
                        registry=registry,
                        candidates=(item,),
                    )
                    for item in registry.candidates
                ),
                key=lambda item: item.evidence_id,
            )
        )
        if any(item.fixed_plan_certified for item in singletons):
            pairs = ()
            cardinality = ()
            outcome = JointPairOutcome.PROTOCOL_FAILURE
            counters = _nonmaterialized_counters(
                eligible_count=eligible_count,
                singleton_count=len(singletons),
                pair_count=0,
                cover_count=0,
                cardinality_count=0,
                cap_rejections=1,
            )
        else:
            pair_subsets = tuple(
                tuple(item)
                for item in itertools.combinations(
                    registry.candidates,
                    2,
                )
            )
            if len(pair_subsets) > caps.max_pair_overlay_evaluations:
                pairs = ()
                cardinality = ()
                outcome = (
                    JointPairOutcome.PAIR_COUNTERFACTUAL_CAP_EXHAUSTED
                )
                counters = _nonmaterialized_counters(
                    eligible_count=eligible_count,
                    singleton_count=len(singletons),
                    pair_count=0,
                    cover_count=0,
                    cardinality_count=0,
                    cap_rejections=1,
                )
            else:
                pairs = tuple(
                    sorted(
                        (
                            _independent_subset_evidence(
                                model=model,
                                audit=audit,
                                threshold=threshold,
                                registry=registry,
                                candidates=pair,
                            )
                            for pair in pair_subsets
                        ),
                        key=lambda item: item.evidence_id,
                    )
                )
                covers = tuple(
                    item for item in pairs if item.fixed_plan_certified
                )
                if not covers:
                    cardinality = ()
                    outcome = (
                        JointPairOutcome
                        .NO_SOUND_FIXED_PLAN_PAIR_COVER
                    )
                    counters = _nonmaterialized_counters(
                        eligible_count=eligible_count,
                        singleton_count=len(singletons),
                        pair_count=len(pairs),
                        cover_count=0,
                        cardinality_count=0,
                        cap_rejections=0,
                    )
                else:
                    cardinality = tuple(
                        sorted(
                            (
                                _materialization_cardinality(
                                    context=registered,
                                    transaction1=transaction1,
                                    registry=registry,
                                    evidence=item,
                                    by_partial=by_partial,
                                )
                                for item in covers
                            ),
                            key=lambda item: item.cardinality_id,
                        )
                    )
                    selected = _select_pair(
                        pair_evidence=pairs,
                        cardinality=cardinality,
                    )
                    if selected is None:
                        outcome = (
                            JointPairOutcome
                            .PAIR_COVER_SAMPLE_BUDGET_DOMINATED
                        )
                        counters = _nonmaterialized_counters(
                            eligible_count=eligible_count,
                            singleton_count=len(singletons),
                            pair_count=len(pairs),
                            cover_count=len(covers),
                            cardinality_count=len(cardinality),
                            cap_rejections=len(cardinality),
                        )
                    else:
                        selected_evidence, selected_cardinality = selected
                        expected_authorization = _authorize_pair(
                            gate_context=gate_context,
                            registry=registry,
                            evidence=selected_evidence,
                            cardinality=selected_cardinality,
                        )
                        if (
                            claimed.selected_pair_evidence_id
                            != selected_evidence.evidence_id
                            or claimed.selected_cardinality_id
                            != selected_cardinality.cardinality_id
                            or claimed.authorization
                            != expected_authorization
                            or len(claimed.replacements) != 2
                            or claimed.closure is None
                            or claimed.bridge is None
                            or claimed.audit is None
                        ):
                            raise ObservationSupportJointPairInvariantViolation(
                                "claimed selected pair/materialization is forged"
                            )
                        expected_replacements: list[
                            JointPairPromotedRowReplacementV1
                        ] = []
                        for replacement in claimed.replacements:
                            parent = by_partial.get(
                                replacement.parent_row.partial_row_id
                            )
                            if (
                                parent is None
                                or parent != replacement.parent_row
                                or parent.partial_row_id
                                not in expected_authorization
                                .selected_partial_row_ids
                            ):
                                raise ObservationSupportJointPairInvariantViolation(
                                    "replacement parent is not selected"
                                )
                            catalogue = _catalogue_for_row(
                                transaction1.promoted_closure,
                                parent,
                            )
                            acquisition.verify_graph_partial_support_row_v1(
                                registered,
                                catalogue,
                                parent.binding.action,
                                replacement.promoted_row,
                            )
                            expected_replacements.append(
                                JointPairPromotedRowReplacementV1(
                                    expected_authorization.authorization_id,
                                    parent,
                                    replacement.promoted_row,
                                    tuple(
                                        sorted(
                                            {
                                                *parent.initial_discovery_observation_ids,
                                                *parent.prior_validation_observation_ids,
                                                *parent.current_validation_observation_ids,
                                            }
                                        )
                                    ),
                                    tuple(
                                        sorted(
                                            replacement.promoted_row
                                            .current_validation_observation_ids
                                        )
                                    ),
                                    replacement.fresh_stream_open_sequence,
                                )
                            )
                        replacements = tuple(  # type: ignore[assignment]
                            sorted(
                                expected_replacements,
                                key=lambda item: item.replacement_id,
                            )
                        )
                        if replacements != claimed.replacements:
                            raise ObservationSupportJointPairInvariantViolation(
                                "replacement replay differs from claim"
                            )
                        closure = claimed.closure
                        catalogue_by_id = {
                            item.catalogue_id: item
                            for item in closure.public_catalogues
                        }
                        new_ids = set(
                            closure.newly_acquired_child_partial_row_ids
                        )
                        new_rows = tuple(
                            row
                            for row in closure.child_rows
                            if row.partial_row_id in new_ids
                        )
                        for row in new_rows:
                            catalogue = catalogue_by_id.get(
                                row.binding.catalogue_id
                            )
                            if catalogue is None:
                                raise ObservationSupportJointPairInvariantViolation(
                                    "new child row lacks its catalogue"
                                )
                            acquisition.verify_graph_partial_support_row_v1(
                                registered,
                                catalogue,
                                row.binding.action,
                                row,
                            )
                        graph_model.verify_observation_support_graph_models_v1(
                            context=registered,
                            root_catalogue=closure.root_catalogue,
                            catalogues=closure.public_catalogues,
                            partial_rows=closure.all_rows,
                            bridge=claimed.bridge,
                            coordinate_profile=(
                                relational.base_coordinate_profile_v1()
                            ),
                        )
                        robust.verify_robust_plan_audit_v1(
                            claimed.bridge.quotient_model,
                            threshold,
                            claimed.audit,
                        )
                        counters = _materialized_counters(
                            eligible_count=eligible_count,
                            singleton_count=len(singletons),
                            pair_count=len(pairs),
                            cover_count=len(covers),
                            cardinality_count=len(cardinality),
                            replacements=replacements,
                            new_catalogue_count=len(
                                closure
                                .newly_admitted_child_catalogue_ids
                            ),
                            new_rows=new_rows,
                        )
                        expected_closure = JointPairPromotedH2ClosureV1(
                            gate_context.context_id,
                            transaction1.consumer_id,
                            expected_authorization,
                            replacements,
                            registered,
                            closure.root_catalogue,
                            closure.child_catalogues,
                            closure.root_rows,
                            closure.child_rows,
                            closure.epoch2_binding_ids,
                            closure.newly_admitted_child_catalogue_ids,
                            closure.newly_acquired_child_partial_row_ids,
                            counters,
                        )
                        if (
                            expected_closure.closure_id
                            != closure.closure_id
                            or expected_closure.to_document()
                            != closure.to_document()
                        ):
                            raise ObservationSupportJointPairInvariantViolation(
                                "independent closure reconstruction differs"
                            )
                        outcome = (
                            JointPairOutcome
                            .CERTIFIED_AT_8192_AFTER_JOINT_PAIR
                            if claimed.audit.certified
                            else JointPairOutcome
                            .FAILED_NEW_FRONTIER_AFTER_JOINT_PAIR
                        )

    if outcome in (
        JointPairOutcome.CERTIFIED_AT_8192_AFTER_JOINT_PAIR,
        JointPairOutcome.FAILED_NEW_FRONTIER_AFTER_JOINT_PAIR,
    ):
        replay = JointPairSupportRunV1(
            gate_context,
            registry,
            outcome,
            singletons,
            pairs,
            cardinality,
            claimed.selected_pair_evidence_id,
            claimed.selected_cardinality_id,
            claimed.authorization,
            claimed.replacements,
            claimed.closure,
            claimed.bridge,
            claimed.audit,
            counters,
        )
    else:
        replay = JointPairSupportRunV1(
            gate_context,
            registry,
            outcome,
            singletons,
            pairs,
            cardinality,
            None,
            None,
            None,
            (),
            None,
            None,
            None,
            counters,
        )
    if (
        replay.run_id != claimed.run_id
        or canonical_json_bytes(replay.to_document())
        != canonical_json_bytes(claimed.to_document())
    ):
        raise ObservationSupportJointPairInvariantViolation(
            "independent joint-pair replay differs from claim"
        )
    return JointPairSupportVerificationV1(
        claimed.run_id,
        replay.run_id,
        replay.outcome,
        len(singletons) + len(pairs),
    )


__all__ = [
    "ALTERNATIVE_GLOBAL_16384_SUFFIX_DRAWS",
    "CONTRACT_VERSION",
    "JointPairCandidateRegistryV1",
    "JointPairCandidateRowV1",
    "JointPairMaterializationCardinalityV1",
    "JointPairOutcome",
    "JointPairPromotedH2ClosureV1",
    "JointPairPromotedRowReplacementV1",
    "JointPairSupportAuthorizationV1",
    "JointPairSupportCapsV1",
    "JointPairSupportContextV1",
    "JointPairSupportCountersV1",
    "JointPairSupportRunV1",
    "JointPairSupportVerificationV1",
    "K6JointPairSupportProbeV0",
    "MATCHED_DIRECT_8192_DRAWS",
    "MATCHED_DIRECT_HEADROOM",
    "MAX_ELIGIBLE_ROWS",
    "MAX_INCREMENTAL_OBSERVER_DRAWS",
    "MAX_NEW_CHILD_ACTION_ROWS",
    "MAX_PAIR_OVERLAY_EVALUATIONS",
    "MAX_SINGLETON_OVERLAY_EVALUATIONS",
    "MINIMALITY_SCOPE",
    "ModelOnlySubsetEvidenceV1",
    "ModelOnlySubsetStatus",
    "ObservationSupportJointPairInvariantViolation",
    "PROFILE_KEY",
    "REGISTERED_BASE_CHECKPOINT",
    "TRANSACTION1_PREFIX_DRAWS",
    "freeze_k6_joint_pair_support_probe_v0",
    "registered_joint_pair_caps_v1",
    "run_joint_pair_support_recovery_v1",
    "run_k6_joint_pair_support_probe_v0",
    "verify_joint_pair_support_recovery_v1",
]
