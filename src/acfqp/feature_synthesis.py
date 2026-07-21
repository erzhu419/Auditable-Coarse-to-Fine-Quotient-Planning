"""Query-free synthesis of an exact, feature-realized reusable LMB RAPM.

The construction in this module deliberately has a narrow information
boundary.  It receives an authoritative LMB kernel and an already-frozen
suite coverage certificate.  It may inspect exact one-step transitions and
the registered, current-state feature grammar, but it accepts no QuerySpec,
reward scalarization, value/Q table, policy, J0 result, or held-out data.

V1 uses the exact behavioural quotient over the training coverage as a typed
realization obligation.  It exhaustively enumerates subsets of the registered
feature grammar, compiles adjacent-value midpoints into atomic ``<=`` splits,
and selects the first exact realization under a frozen deterministic rule.
The selected predicate partition is then independently materialized through
the ordinary quotient and portable-RAPM builders.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
from fractions import Fraction
import hashlib
import inspect
from itertools import combinations
from typing import Any, Iterable, Mapping

from acfqp.abstraction.behavioral import (
    BehavioralActionAssignment,
    BehavioralActionSignature,
    BehavioralCellId,
    BehavioralRefinementStep,
    BehavioralSemanticAdapter,
    ExactBehavioralQuotient,
    build_exact_behavioral_quotient,
)
from acfqp.abstraction.partition import Partition
from acfqp.abstraction.quotient import (
    EnvelopeEntry,
    ExactRealizationEnvelope,
    GroundRealization,
    NominalActionModel,
    NominalEntry,
    NominalQuotient,
    QuotientModels,
    build_quotient_models,
)
from acfqp.artifacts import object_id
from acfqp.build_coverage import SuiteBuildCoverage
from acfqp.domains.matching_buffer import LMBAction, LMBKernel, LMBState, LMBStatus
from acfqp.domains.semantic import LMBSemanticAdapter
from acfqp.phase3e_ids import canonical_json_bytes
from acfqp.portable import (
    PortableBuildResult,
    PortableRAPM,
    PortableRegistry,
    build_portable_rapm,
    fraction_to_json,
)


FEATURE_REGISTRY_SCHEMA = "acfqp.feature_registry@v1"
SYNTHESIS_SPEC_SCHEMA = "acfqp.feature_rapm_synthesis_spec@v1"
PREDICATE_TREE_SCHEMA = "acfqp.canonical_predicate_tree@v1"
CANDIDATE_TRACE_SCHEMA = "acfqp.feature_synthesis_candidate_trace@v1"
REALIZATION_CERTIFICATE_SCHEMA = "acfqp.feature_realization_certificate@v1"

FEATURE_REGISTRY_DOMAIN = "acfqp:feature-registry:v1"
SYNTHESIS_SPEC_DOMAIN = "acfqp:feature-rapm-synthesis-spec:v1"
PREDICATE_ATOM_DOMAIN = "acfqp:feature-predicate-atom:v1"
PREDICATE_CELL_DOMAIN = "acfqp:feature-predicate-cell:v1"
PREDICATE_TREE_DOMAIN = "acfqp:canonical-predicate-tree:v1"
CANDIDATE_DOMAIN = "acfqp:feature-synthesis-candidate:v1"
WITNESS_DOMAIN = "acfqp:feature-realization-witness:v1"
CANDIDATE_TRACE_DOMAIN = "acfqp:feature-synthesis-candidate-trace:v1"
REALIZATION_CERTIFICATE_DOMAIN = "acfqp:feature-realization-certificate:v1"
STRUCTURAL_DOMAIN = "acfqp:lmb-structural-identity:v1"
COVERAGE_DOMAIN = "acfqp:training-coverage-identity:v1"
PARTITION_DOMAIN = "acfqp:partition-signature:v1"

LMB_ADAPTER_SEMANTICS_ID = "lmb_semantic_adapter.current_state_features.v1"
LMB_FEATURE_IMPLEMENTATION_SHA256_V1 = (
    "823b48f9eb22975b3f1e97bc64e3074cc74ae7b48772c021d80b24d98064de98"
)
THRESHOLD_GENERATOR_V1 = "adjacent_distinct_value_midpoints_v1"
TARGET_EQUIVALENCE_V1 = "exact_controlled_behavioral_equivalence_v1"
CANDIDATE_ORDER_V1 = "feature_count_then_lexicographic_feature_names_v1"
SELECTION_RULE_V1 = (
    "minimum_feature_count_then_minimum_split_count_then_lexicographic_"
    "feature_names_then_partition_id_v1"
)
CANONICAL_PRODUCTION_PROFILE_V1 = "canonical_production_full_grammar_v1"
RESTRICTED_NEGATIVE_CONTROL_PROFILE_V1 = (
    "restricted_grammar_negative_control_v1"
)
ALLOWED_INFORMATION_CHANNELS_V1 = (
    "exact_one_step_transition_kernel",
    "frozen_structural_kernel",
    "frozen_training_coverage",
    "registered_current_state_features",
)
FORBIDDEN_INFORMATION_CHANNELS_V1 = (
    "J0",
    "Q_values",
    "QuerySpec",
    "heldout_data",
    "policy",
    "value_function",
)
FEATURE_REALIZATION_CLAIM_SCOPE_V1 = (
    "training-coverage exact controlled-behaviour realization by registered "
    "current-state predicates; no query/value/policy/heldout claim"
)
WORKLOAD_ECONOMICS_GATE_LOCKED = "WORKLOAD_ECONOMICS_GATE_NOT_RUN"
COUNTER_COMPLETENESS_GATE_LOCKED = "COUNTER_COMPLETENESS_GATE_NOT_RUN"


class FeatureSynthesisInvariantViolation(ValueError):
    """Raised when a synthesis artifact or its information boundary is invalid."""


class FeatureRAPMSynthesisStatus(str, Enum):
    EXACT_FEATURE_REALIZATION = "EXACT_FEATURE_REALIZATION"
    NO_EXACT_FEATURE_REALIZATION = "NO_EXACT_FEATURE_REALIZATION"


def _content_id(domain_tag: str, payload: Mapping[str, Any]) -> str:
    """Return a full domain-separated SHA-256 without extending Phase 3E's registry."""

    return hashlib.sha256(
        domain_tag.encode("utf-8") + b"\x00" + canonical_json_bytes(dict(payload))
    ).hexdigest()


def _require_exact_keys(
    document: Any,
    required: set[str],
    label: str,
) -> dict[str, Any]:
    if type(document) is not dict or set(document) != required:
        raise FeatureSynthesisInvariantViolation(
            f"{label} must contain exactly {tuple(sorted(required))!r}"
        )
    return document


def _require_text(value: Any, label: str) -> str:
    if type(value) is not str or not value:
        raise FeatureSynthesisInvariantViolation(f"{label} must be a nonempty string")
    return value


def _require_bool(value: Any, label: str) -> bool:
    if type(value) is not bool:
        raise FeatureSynthesisInvariantViolation(f"{label} must be boolean")
    return value


def _require_int(value: Any, label: str, *, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise FeatureSynthesisInvariantViolation(
            f"{label} must be an integer >= {minimum}"
        )
    return value


def _require_list(value: Any, label: str) -> list[Any]:
    if type(value) is not list:
        raise FeatureSynthesisInvariantViolation(f"{label} must be a JSON list")
    return value


def _json_exact_equal(left: Any, right: Any) -> bool:
    """Compare parsed JSON without Python's bool/int or tuple/list coercions."""

    if type(left) is not type(right):
        return False
    if type(left) is dict:
        return set(left) == set(right) and all(
            _json_exact_equal(left[key], right[key]) for key in left
        )
    if type(left) is list:
        return len(left) == len(right) and all(
            _json_exact_equal(lvalue, rvalue)
            for lvalue, rvalue in zip(left, right)
        )
    return left == right


def _require_canonical_document(
    received: dict[str, Any],
    canonical: dict[str, Any],
    label: str,
) -> None:
    if not _json_exact_equal(received, canonical):
        raise FeatureSynthesisInvariantViolation(
            f"{label} is not the exact canonical JSON representation"
        )


def _fraction_document(value: Fraction) -> dict[str, int]:
    reduced = Fraction(value)
    return {"numerator": reduced.numerator, "denominator": reduced.denominator}


def _parse_fraction(value: Any, label: str) -> Fraction:
    record = _require_exact_keys(value, {"numerator", "denominator"}, label)
    numerator = record["numerator"]
    if type(numerator) is not int:
        raise FeatureSynthesisInvariantViolation(
            f"{label}.numerator must be an integer"
        )
    denominator = _require_int(record["denominator"], f"{label}.denominator", minimum=1)
    result = Fraction(numerator, denominator)
    if _fraction_document(result) != record:
        raise FeatureSynthesisInvariantViolation(f"{label} must be reduced")
    return result


def _ordered_states(states: Iterable[LMBState]) -> tuple[LMBState, ...]:
    return tuple(sorted(states, key=repr))


def _partition_payload(partition: Partition) -> dict[str, Any]:
    return {
        "blocks": [
            sorted(object_id(state, "state") for state in partition.members(cell))
            for cell in partition.cell_ids
        ]
    }


def _partition_id(partition: Partition) -> str:
    payload = _partition_payload(partition)
    payload["blocks"].sort()
    return _content_id(PARTITION_DOMAIN, payload)


def _structural_payload(kernel: LMBKernel) -> dict[str, Any]:
    return {
        "domain": "layered_matching_buffer",
        "tile_types": list(kernel.tile_types),
        "blockers": [sorted(blockers) for blockers in kernel.blockers],
        "type_count": kernel.type_count,
        "capacity": kernel.capacity,
        "max_layers": kernel.max_layers,
        "reward_features": list(kernel.registered_reward_features),
        "goals": list(kernel.registered_goals),
    }


def _structural_id(kernel: LMBKernel) -> str:
    return _content_id(STRUCTURAL_DOMAIN, _structural_payload(kernel))


def _coverage_payload(coverage: SuiteBuildCoverage[LMBState]) -> dict[str, Any]:
    return {
        "mode": coverage.mode,
        "declared_support_set_sha256": coverage.declared_support_set_sha256,
        "declared_support_state_ids": list(coverage.declared_support_state_ids),
        "covered_state_ids": list(coverage.covered_state_ids),
        "exact_state_cap": coverage.exact_state_cap,
        "admissible_query_support_rule": coverage.admissible_query_support_rule,
        "reuse_outside_coverage_forbidden": coverage.reuse_outside_coverage_forbidden,
    }


def _coverage_id(coverage: SuiteBuildCoverage[LMBState]) -> str:
    return _content_id(COVERAGE_DOMAIN, _coverage_payload(coverage))


@dataclass(frozen=True, order=True, slots=True)
class FeatureDefinitionV1:
    feature_name: str
    value_kind: str
    semantics_id: str
    semantics: str
    implementation_sha256: str
    threshold_generator: str = THRESHOLD_GENERATOR_V1

    def __post_init__(self) -> None:
        _require_text(self.feature_name, "feature_name")
        if self.value_kind != "exact_rational":
            raise FeatureSynthesisInvariantViolation("only exact-rational features are allowed")
        _require_text(self.semantics_id, "semantics_id")
        _require_text(self.semantics, "semantics")
        if (
            type(self.implementation_sha256) is not str
            or len(self.implementation_sha256) != 64
            or any(
                character not in "0123456789abcdef"
                for character in self.implementation_sha256
            )
        ):
            raise FeatureSynthesisInvariantViolation(
                "feature implementation digest must be a full lowercase SHA-256"
            )
        if self.threshold_generator != THRESHOLD_GENERATOR_V1:
            raise FeatureSynthesisInvariantViolation("unsupported threshold generator")

    def to_document(self) -> dict[str, Any]:
        return {
            "feature_name": self.feature_name,
            "value_kind": self.value_kind,
            "semantics_id": self.semantics_id,
            "semantics": self.semantics,
            "implementation_sha256": self.implementation_sha256,
            "threshold_generator": self.threshold_generator,
        }

    @classmethod
    def from_document(cls, document: Any) -> "FeatureDefinitionV1":
        record = _require_exact_keys(
            document,
            {
                "feature_name",
                "value_kind",
                "semantics_id",
                "semantics",
                "implementation_sha256",
                "threshold_generator",
            },
            "feature definition",
        )
        result = cls(
            feature_name=_require_text(record["feature_name"], "feature_name"),
            value_kind=_require_text(record["value_kind"], "value_kind"),
            semantics_id=_require_text(record["semantics_id"], "semantics_id"),
            semantics=_require_text(record["semantics"], "semantics"),
            implementation_sha256=_require_text(
                record["implementation_sha256"], "implementation_sha256"
            ),
            threshold_generator=_require_text(
                record["threshold_generator"], "threshold_generator"
            ),
        )
        _require_canonical_document(record, result.to_document(), "feature definition")
        return result


_LMB_FEATURE_SEMANTICS = {
    "action_count": "number of currently legal primitive tile selections",
    "branching_count": "number of currently legal primitive tile selections",
    "buffer_occupancy": "sum of current per-type buffer counts",
    "capacity_slack": "remaining buffer capacity divided by total capacity",
    "capacity_slack_count": "remaining buffer capacity as an integer count",
    "immediate_release_liquidity": (
        "twice the number of legal selections completing a triple divided by "
        "capacity times legal-action count, or zero when undefined"
    ),
    "match_debt_mean": "mean fractional tiles needed to complete each type triple",
    "match_debt_min": "minimum fractional tiles needed to complete a type triple",
    "match_debt_nonzero_types": "number of types with nonzero match debt",
    "max_match_debt": "maximum fractional tiles needed to complete a type triple",
    "remaining_object_count": "number of tiles not yet removed",
}


def _lmb_feature_implementation_sha256() -> str:
    source = inspect.getsource(LMBSemanticAdapter.features).encode("utf-8")
    return hashlib.sha256(source).hexdigest()


def _require_frozen_lmb_feature_implementation_v1() -> str:
    observed = _lmb_feature_implementation_sha256()
    if observed != LMB_FEATURE_IMPLEMENTATION_SHA256_V1:
        raise FeatureSynthesisInvariantViolation(
            "LMBSemanticAdapter.features differs from the frozen V1 code authority"
        )
    return LMB_FEATURE_IMPLEMENTATION_SHA256_V1


@dataclass(frozen=True, slots=True)
class FeatureRegistryV1:
    adapter_semantics_id: str
    definitions: tuple[FeatureDefinitionV1, ...]
    schema: str = FEATURE_REGISTRY_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != FEATURE_REGISTRY_SCHEMA:
            raise FeatureSynthesisInvariantViolation("unsupported feature registry schema")
        if self.adapter_semantics_id != LMB_ADAPTER_SEMANTICS_ID:
            raise FeatureSynthesisInvariantViolation(
                "feature registry adapter semantics is not the frozen V1 authority"
            )
        if type(self.definitions) is not tuple or not self.definitions:
            raise FeatureSynthesisInvariantViolation("feature registry must be nonempty")
        if any(type(item) is not FeatureDefinitionV1 for item in self.definitions):
            raise FeatureSynthesisInvariantViolation(
                "feature definitions must be exact FeatureDefinitionV1 objects"
            )
        ordered = tuple(sorted(self.definitions, key=lambda item: item.feature_name))
        if ordered != self.definitions:
            raise FeatureSynthesisInvariantViolation(
                "feature definitions must be in canonical feature-name order"
            )
        names = tuple(definition.feature_name for definition in ordered)
        if len(set(names)) != len(names):
            raise FeatureSynthesisInvariantViolation("feature names must be unique")
        implementation_sha = _require_frozen_lmb_feature_implementation_v1()
        for definition in self.definitions:
            name = definition.feature_name
            if name not in _LMB_FEATURE_SEMANTICS:
                raise FeatureSynthesisInvariantViolation(
                    "feature registry contains an unregistered LMB feature"
                )
            expected = FeatureDefinitionV1(
                feature_name=name,
                value_kind="exact_rational",
                semantics_id=f"lmb.current_state_feature.{name}.v1",
                semantics=_LMB_FEATURE_SEMANTICS[name],
                implementation_sha256=implementation_sha,
            )
            if definition != expected:
                raise FeatureSynthesisInvariantViolation(
                    f"feature definition {name!r} is not the canonical V1 authority"
                )

    @property
    def feature_names(self) -> tuple[str, ...]:
        return tuple(definition.feature_name for definition in self.definitions)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "adapter_semantics_id": self.adapter_semantics_id,
            "definitions": [definition.to_document() for definition in self.definitions],
        }

    @property
    def feature_registry_id(self) -> str:
        return _content_id(FEATURE_REGISTRY_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "feature_registry_id": self.feature_registry_id}

    @classmethod
    def from_document(cls, document: Any) -> "FeatureRegistryV1":
        record = _require_exact_keys(
            document,
            {"schema", "adapter_semantics_id", "definitions", "feature_registry_id"},
            "feature registry",
        )
        if type(record["definitions"]) is not list:
            raise FeatureSynthesisInvariantViolation("feature definitions must be a list")
        result = cls(
            adapter_semantics_id=_require_text(
                record["adapter_semantics_id"], "adapter_semantics_id"
            ),
            definitions=tuple(
                FeatureDefinitionV1.from_document(item)
                for item in record["definitions"]
            ),
            schema=_require_text(record["schema"], "schema"),
        )
        if record["feature_registry_id"] != result.feature_registry_id:
            raise FeatureSynthesisInvariantViolation("feature registry ID mismatch")
        _require_canonical_document(record, result.to_document(), "feature registry")
        return result


def lmb_feature_registry_v1(
    feature_names: Iterable[str] | None = None,
) -> FeatureRegistryV1:
    """Return the frozen current-state LMB grammar, optionally restricted."""

    available = tuple(sorted(_LMB_FEATURE_SEMANTICS))
    selected = available if feature_names is None else tuple(sorted(set(feature_names)))
    if not selected or any(name not in _LMB_FEATURE_SEMANTICS for name in selected):
        raise FeatureSynthesisInvariantViolation("unknown or empty LMB feature grammar")
    implementation_sha = _require_frozen_lmb_feature_implementation_v1()
    definitions = tuple(
        FeatureDefinitionV1(
            feature_name=name,
            value_kind="exact_rational",
            semantics_id=f"lmb.current_state_feature.{name}.v1",
            semantics=_LMB_FEATURE_SEMANTICS[name],
            implementation_sha256=implementation_sha,
        )
        for name in selected
    )
    return FeatureRegistryV1(
        adapter_semantics_id=LMB_ADAPTER_SEMANTICS_ID,
        definitions=definitions,
    )


@dataclass(frozen=True, slots=True)
class SynthesisSpecV1:
    structural_id: str
    training_coverage_id: str
    feature_registry_id: str
    candidate_cap: int
    profile_kind: str = CANONICAL_PRODUCTION_PROFILE_V1
    allowed_information_channels: tuple[str, ...] = ALLOWED_INFORMATION_CHANNELS_V1
    forbidden_information_channels: tuple[str, ...] = FORBIDDEN_INFORMATION_CHANNELS_V1
    target_equivalence: str = TARGET_EQUIVALENCE_V1
    threshold_generator: str = THRESHOLD_GENERATOR_V1
    candidate_order: str = CANDIDATE_ORDER_V1
    selection_rule: str = SELECTION_RULE_V1
    schema: str = SYNTHESIS_SPEC_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != SYNTHESIS_SPEC_SCHEMA:
            raise FeatureSynthesisInvariantViolation("unsupported synthesis spec schema")
        for label, value in (
            ("structural_id", self.structural_id),
            ("training_coverage_id", self.training_coverage_id),
            ("feature_registry_id", self.feature_registry_id),
        ):
            if len(_require_text(value, label)) != 64:
                raise FeatureSynthesisInvariantViolation(f"{label} must be full SHA-256")
        _require_int(self.candidate_cap, "candidate_cap", minimum=1)
        if self.profile_kind not in {
            CANONICAL_PRODUCTION_PROFILE_V1,
            RESTRICTED_NEGATIVE_CONTROL_PROFILE_V1,
        }:
            raise FeatureSynthesisInvariantViolation(
                "synthesis profile kind is not registered"
            )
        if type(self.allowed_information_channels) is not tuple or any(
            type(item) is not str for item in self.allowed_information_channels
        ):
            raise FeatureSynthesisInvariantViolation(
                "allowed information channels must be a tuple of strings"
            )
        if type(self.forbidden_information_channels) is not tuple or any(
            type(item) is not str for item in self.forbidden_information_channels
        ):
            raise FeatureSynthesisInvariantViolation(
                "forbidden information channels must be a tuple of strings"
            )
        if self.allowed_information_channels != ALLOWED_INFORMATION_CHANNELS_V1:
            raise FeatureSynthesisInvariantViolation(
                "allowed information channels differ from the frozen V1 contract"
            )
        if self.forbidden_information_channels != FORBIDDEN_INFORMATION_CHANNELS_V1:
            raise FeatureSynthesisInvariantViolation(
                "forbidden information channels differ from the frozen V1 contract"
            )
        if self.target_equivalence != TARGET_EQUIVALENCE_V1:
            raise FeatureSynthesisInvariantViolation(
                "target equivalence differs from the frozen V1 contract"
            )
        if self.threshold_generator != THRESHOLD_GENERATOR_V1:
            raise FeatureSynthesisInvariantViolation(
                "threshold generator differs from the frozen V1 contract"
            )
        if self.candidate_order != CANDIDATE_ORDER_V1:
            raise FeatureSynthesisInvariantViolation(
                "candidate order differs from the frozen V1 contract"
            )
        if self.selection_rule != SELECTION_RULE_V1:
            raise FeatureSynthesisInvariantViolation(
                "selection rule differs from the frozen V1 contract"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "structural_id": self.structural_id,
            "training_coverage_id": self.training_coverage_id,
            "feature_registry_id": self.feature_registry_id,
            "candidate_cap": self.candidate_cap,
            "profile_kind": self.profile_kind,
            "allowed_information_channels": list(self.allowed_information_channels),
            "forbidden_information_channels": list(self.forbidden_information_channels),
            "target_equivalence": self.target_equivalence,
            "threshold_generator": self.threshold_generator,
            "candidate_order": self.candidate_order,
            "selection_rule": self.selection_rule,
        }

    @property
    def synthesis_spec_id(self) -> str:
        return _content_id(SYNTHESIS_SPEC_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "synthesis_spec_id": self.synthesis_spec_id}

    @classmethod
    def from_document(cls, document: Any) -> "SynthesisSpecV1":
        required = {
            "schema",
            "structural_id",
            "training_coverage_id",
            "feature_registry_id",
            "candidate_cap",
            "profile_kind",
            "allowed_information_channels",
            "forbidden_information_channels",
            "target_equivalence",
            "threshold_generator",
            "candidate_order",
            "selection_rule",
            "synthesis_spec_id",
        }
        record = _require_exact_keys(document, required, "synthesis spec")
        kwargs = {key: record[key] for key in required - {"synthesis_spec_id"}}
        for key in ("allowed_information_channels", "forbidden_information_channels"):
            if type(kwargs[key]) is not list:
                raise FeatureSynthesisInvariantViolation(f"{key} must be a list")
            kwargs[key] = tuple(kwargs[key])
        result = cls(**kwargs)
        if record["synthesis_spec_id"] != result.synthesis_spec_id:
            raise FeatureSynthesisInvariantViolation("synthesis spec ID mismatch")
        _require_canonical_document(record, result.to_document(), "synthesis spec")
        return result


def lmb_synthesis_spec_v1(
    kernel: LMBKernel,
    coverage: SuiteBuildCoverage[LMBState],
    registry: FeatureRegistryV1,
    *,
    candidate_cap: int = 4096,
    profile_kind: str = CANONICAL_PRODUCTION_PROFILE_V1,
) -> SynthesisSpecV1:
    return SynthesisSpecV1(
        structural_id=_structural_id(kernel),
        training_coverage_id=_coverage_id(coverage),
        feature_registry_id=registry.feature_registry_id,
        candidate_cap=candidate_cap,
        profile_kind=profile_kind,
    )


@dataclass(frozen=True, order=True, slots=True)
class PredicateAtomV1:
    feature_name: str
    operator: str
    threshold: Fraction

    def __post_init__(self) -> None:
        _require_text(self.feature_name, "predicate feature_name")
        if self.operator != "<=":
            raise FeatureSynthesisInvariantViolation("V1 predicates must use <=")
        object.__setattr__(self, "threshold", Fraction(self.threshold))

    def _payload(self) -> dict[str, Any]:
        return {
            "feature_name": self.feature_name,
            "operator": self.operator,
            "threshold": _fraction_document(self.threshold),
        }

    @property
    def predicate_id(self) -> str:
        return _content_id(PREDICATE_ATOM_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "predicate_id": self.predicate_id}

    @classmethod
    def from_document(cls, document: Any) -> "PredicateAtomV1":
        record = _require_exact_keys(
            document,
            {"feature_name", "operator", "threshold", "predicate_id"},
            "predicate atom",
        )
        result = cls(
            _require_text(record["feature_name"], "predicate feature_name"),
            _require_text(record["operator"], "predicate operator"),
            _parse_fraction(record["threshold"], "predicate threshold"),
        )
        if record["predicate_id"] != result.predicate_id:
            raise FeatureSynthesisInvariantViolation("predicate atom ID mismatch")
        _require_canonical_document(record, result.to_document(), "predicate atom")
        return result


@dataclass(frozen=True, slots=True)
class PredicateSplitNodeV1:
    sequence: int
    parent_cell_id: str
    predicate: PredicateAtomV1
    true_child_cell_id: str
    false_child_cell_id: str
    parent_member_count: int
    true_member_count: int
    false_member_count: int

    def __post_init__(self) -> None:
        _require_int(self.sequence, "split sequence", minimum=1)
        for field_name in (
            "parent_cell_id",
            "true_child_cell_id",
            "false_child_cell_id",
        ):
            _require_text(getattr(self, field_name), field_name)
        if type(self.predicate) is not PredicateAtomV1:
            raise FeatureSynthesisInvariantViolation(
                "split predicate must be an exact PredicateAtomV1"
            )
        for field_name, minimum in (
            ("parent_member_count", 2),
            ("true_member_count", 1),
            ("false_member_count", 1),
        ):
            _require_int(getattr(self, field_name), field_name, minimum=minimum)
        if self.true_child_cell_id == self.false_child_cell_id:
            raise FeatureSynthesisInvariantViolation(
                "predicate split children must be distinct"
            )
        if self.true_member_count + self.false_member_count != self.parent_member_count:
            raise FeatureSynthesisInvariantViolation(
                "predicate split child counts must exactly cover the parent"
            )

    def to_document(self) -> dict[str, Any]:
        return {
            "sequence": self.sequence,
            "parent_cell_id": self.parent_cell_id,
            "predicate": self.predicate.to_document(),
            "true_child_cell_id": self.true_child_cell_id,
            "false_child_cell_id": self.false_child_cell_id,
            "parent_member_count": self.parent_member_count,
            "true_member_count": self.true_member_count,
            "false_member_count": self.false_member_count,
        }

    @classmethod
    def from_document(cls, document: Any) -> "PredicateSplitNodeV1":
        required = {
            "sequence",
            "parent_cell_id",
            "predicate",
            "true_child_cell_id",
            "false_child_cell_id",
            "parent_member_count",
            "true_member_count",
            "false_member_count",
        }
        record = _require_exact_keys(document, required, "predicate split node")
        result = cls(
            sequence=_require_int(record["sequence"], "split sequence", minimum=1),
            parent_cell_id=_require_text(record["parent_cell_id"], "parent cell ID"),
            predicate=PredicateAtomV1.from_document(record["predicate"]),
            true_child_cell_id=_require_text(
                record["true_child_cell_id"], "true child cell ID"
            ),
            false_child_cell_id=_require_text(
                record["false_child_cell_id"], "false child cell ID"
            ),
            parent_member_count=_require_int(
                record["parent_member_count"], "parent member count", minimum=2
            ),
            true_member_count=_require_int(
                record["true_member_count"], "true member count", minimum=1
            ),
            false_member_count=_require_int(
                record["false_member_count"], "false member count", minimum=1
            ),
        )
        if result.true_member_count + result.false_member_count != result.parent_member_count:
            raise FeatureSynthesisInvariantViolation(
                "predicate split child counts must exactly cover the parent"
            )
        _require_canonical_document(record, result.to_document(), "predicate split node")
        return result


@dataclass(frozen=True, slots=True)
class CanonicalPredicateTreeV1:
    selected_features: tuple[str, ...]
    generated_atoms: tuple[PredicateAtomV1, ...]
    split_nodes: tuple[PredicateSplitNodeV1, ...]
    base_partition_id: str
    final_partition_id: str
    final_cell_count: int
    active_cell_count: int
    schema: str = PREDICATE_TREE_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != PREDICATE_TREE_SCHEMA:
            raise FeatureSynthesisInvariantViolation("unsupported predicate tree schema")
        if tuple(sorted(self.selected_features)) != self.selected_features:
            raise FeatureSynthesisInvariantViolation("selected features must be sorted")
        if any(type(name) is not str or not name for name in self.selected_features):
            raise FeatureSynthesisInvariantViolation(
                "selected features must be nonempty strings"
            )
        if len(set(self.selected_features)) != len(self.selected_features):
            raise FeatureSynthesisInvariantViolation("selected features must be unique")
        if type(self.generated_atoms) is not tuple or any(
            type(atom) is not PredicateAtomV1 for atom in self.generated_atoms
        ):
            raise FeatureSynthesisInvariantViolation(
                "generated atoms must be exact PredicateAtomV1 objects"
            )
        if type(self.split_nodes) is not tuple or any(
            type(node) is not PredicateSplitNodeV1 for node in self.split_nodes
        ):
            raise FeatureSynthesisInvariantViolation(
                "split nodes must be exact PredicateSplitNodeV1 objects"
            )
        if tuple(node.sequence for node in self.split_nodes) != tuple(
            range(1, len(self.split_nodes) + 1)
        ):
            raise FeatureSynthesisInvariantViolation("split sequence must be contiguous")
        if len({atom.predicate_id for atom in self.generated_atoms}) != len(
            self.generated_atoms
        ):
            raise FeatureSynthesisInvariantViolation("generated atoms must be unique")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "selected_features": list(self.selected_features),
            "generated_atoms": [atom.to_document() for atom in self.generated_atoms],
            "split_nodes": [node.to_document() for node in self.split_nodes],
            "base_partition_id": self.base_partition_id,
            "final_partition_id": self.final_partition_id,
            "final_cell_count": self.final_cell_count,
            "active_cell_count": self.active_cell_count,
        }

    @property
    def predicate_tree_id(self) -> str:
        return _content_id(PREDICATE_TREE_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "predicate_tree_id": self.predicate_tree_id}

    @classmethod
    def from_document(cls, document: Any) -> "CanonicalPredicateTreeV1":
        required = {
            "schema",
            "selected_features",
            "generated_atoms",
            "split_nodes",
            "base_partition_id",
            "final_partition_id",
            "final_cell_count",
            "active_cell_count",
            "predicate_tree_id",
        }
        record = _require_exact_keys(document, required, "predicate tree")
        selected_features = _require_list(
            record["selected_features"], "predicate tree selected_features"
        )
        generated_atoms = _require_list(
            record["generated_atoms"], "predicate tree generated_atoms"
        )
        split_nodes = _require_list(
            record["split_nodes"], "predicate tree split_nodes"
        )
        result = cls(
            selected_features=tuple(
                _require_text(item, "predicate tree selected feature")
                for item in selected_features
            ),
            generated_atoms=tuple(
                PredicateAtomV1.from_document(item) for item in generated_atoms
            ),
            split_nodes=tuple(
                PredicateSplitNodeV1.from_document(item) for item in split_nodes
            ),
            base_partition_id=_require_text(record["base_partition_id"], "base partition ID"),
            final_partition_id=_require_text(
                record["final_partition_id"], "final partition ID"
            ),
            final_cell_count=_require_int(
                record["final_cell_count"], "final cell count", minimum=1
            ),
            active_cell_count=_require_int(
                record["active_cell_count"], "active cell count", minimum=1
            ),
            schema=_require_text(record["schema"], "predicate tree schema"),
        )
        if record["predicate_tree_id"] != result.predicate_tree_id:
            raise FeatureSynthesisInvariantViolation("predicate tree ID mismatch")
        _require_canonical_document(record, result.to_document(), "predicate tree")
        return result


@dataclass(frozen=True, slots=True)
class FeatureRealizationWitnessV1:
    witness_kind: str
    left_state_id: str
    right_state_id: str
    left_target_cell_id: str
    right_target_cell_id: str
    left_candidate_cell_id: str
    right_candidate_cell_id: str

    def __post_init__(self) -> None:
        for field_name in (
            "witness_kind",
            "left_state_id",
            "right_state_id",
            "left_target_cell_id",
            "right_target_cell_id",
            "left_candidate_cell_id",
            "right_candidate_cell_id",
        ):
            _require_text(getattr(self, field_name), f"feature witness {field_name}")
        if self.left_state_id == self.right_state_id:
            raise FeatureSynthesisInvariantViolation(
                "feature witness states must be distinct"
            )

    def __post_init__(self) -> None:
        if self.witness_kind not in {
            "TARGET_SEPARATED_FEATURE_ALIASED",
            "TARGET_MERGED_FEATURE_SEPARATED",
        }:
            raise FeatureSynthesisInvariantViolation("unsupported feature witness kind")
        target_same = self.left_target_cell_id == self.right_target_cell_id
        candidate_same = (
            self.left_candidate_cell_id == self.right_candidate_cell_id
        )
        if self.witness_kind == "TARGET_SEPARATED_FEATURE_ALIASED" and (
            target_same or not candidate_same
        ):
            raise FeatureSynthesisInvariantViolation(
                "feature-alias witness has inconsistent cell relationships"
            )
        if self.witness_kind == "TARGET_MERGED_FEATURE_SEPARATED" and (
            not target_same or candidate_same
        ):
            raise FeatureSynthesisInvariantViolation(
                "feature-separation witness has inconsistent cell relationships"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "witness_kind": self.witness_kind,
            "left_state_id": self.left_state_id,
            "right_state_id": self.right_state_id,
            "left_target_cell_id": self.left_target_cell_id,
            "right_target_cell_id": self.right_target_cell_id,
            "left_candidate_cell_id": self.left_candidate_cell_id,
            "right_candidate_cell_id": self.right_candidate_cell_id,
        }

    @property
    def witness_id(self) -> str:
        return _content_id(WITNESS_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "witness_id": self.witness_id}

    @classmethod
    def from_document(cls, document: Any) -> "FeatureRealizationWitnessV1":
        required = {
            "witness_kind",
            "left_state_id",
            "right_state_id",
            "left_target_cell_id",
            "right_target_cell_id",
            "left_candidate_cell_id",
            "right_candidate_cell_id",
            "witness_id",
        }
        record = _require_exact_keys(document, required, "feature witness")
        result = cls(
            **{
                key: _require_text(record[key], f"feature witness {key}")
                for key in required - {"witness_id"}
            }
        )
        if record["witness_id"] != result.witness_id:
            raise FeatureSynthesisInvariantViolation("feature witness ID mismatch")
        _require_canonical_document(record, result.to_document(), "feature witness")
        return result


@dataclass(frozen=True, slots=True)
class FeatureSynthesisCandidateV1:
    selected_features: tuple[str, ...]
    predicate_tree_id: str
    final_partition_id: str
    final_cell_count: int
    active_cell_count: int
    applied_split_count: int
    exact_target_match: bool
    unresolved_witness_id: str | None

    def __post_init__(self) -> None:
        if type(self.selected_features) is not tuple:
            raise FeatureSynthesisInvariantViolation(
                "candidate selected features must be a tuple"
            )
        if tuple(sorted(self.selected_features)) != self.selected_features:
            raise FeatureSynthesisInvariantViolation(
                "candidate selected features must be sorted"
            )
        if len(set(self.selected_features)) != len(self.selected_features):
            raise FeatureSynthesisInvariantViolation(
                "candidate selected features must be unique"
            )
        if any(type(name) is not str or not name for name in self.selected_features):
            raise FeatureSynthesisInvariantViolation(
                "candidate selected features must be nonempty strings"
            )
        for field_name in ("predicate_tree_id", "final_partition_id"):
            _require_text(getattr(self, field_name), f"candidate {field_name}")
        if self.unresolved_witness_id is not None:
            _require_text(
                self.unresolved_witness_id,
                "candidate unresolved_witness_id",
            )
        for label, value, minimum in (
            ("final cell count", self.final_cell_count, 1),
            ("active cell count", self.active_cell_count, 1),
            ("applied split count", self.applied_split_count, 0),
        ):
            _require_int(value, label, minimum=minimum)
        if self.active_cell_count > self.final_cell_count:
            raise FeatureSynthesisInvariantViolation(
                "candidate active cells cannot exceed all cells"
            )
        _require_bool(self.exact_target_match, "candidate exact target match")
        if self.exact_target_match != (self.unresolved_witness_id is None):
            raise FeatureSynthesisInvariantViolation(
                "exact candidates have no witness and failed candidates require one"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "selected_features": list(self.selected_features),
            "predicate_tree_id": self.predicate_tree_id,
            "final_partition_id": self.final_partition_id,
            "final_cell_count": self.final_cell_count,
            "active_cell_count": self.active_cell_count,
            "applied_split_count": self.applied_split_count,
            "exact_target_match": self.exact_target_match,
            "unresolved_witness_id": self.unresolved_witness_id,
        }

    @property
    def candidate_id(self) -> str:
        return _content_id(CANDIDATE_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "candidate_id": self.candidate_id}

    @classmethod
    def from_document(cls, document: Any) -> "FeatureSynthesisCandidateV1":
        required = {
            "selected_features",
            "predicate_tree_id",
            "final_partition_id",
            "final_cell_count",
            "active_cell_count",
            "applied_split_count",
            "exact_target_match",
            "unresolved_witness_id",
            "candidate_id",
        }
        record = _require_exact_keys(document, required, "feature candidate")
        selected_features = _require_list(
            record["selected_features"], "candidate selected_features"
        )
        unresolved_witness_id = record["unresolved_witness_id"]
        if unresolved_witness_id is not None:
            unresolved_witness_id = _require_text(
                unresolved_witness_id, "candidate unresolved_witness_id"
            )
        result = cls(
            selected_features=tuple(
                _require_text(item, "candidate selected feature")
                for item in selected_features
            ),
            predicate_tree_id=_require_text(record["predicate_tree_id"], "tree ID"),
            final_partition_id=_require_text(record["final_partition_id"], "partition ID"),
            final_cell_count=_require_int(record["final_cell_count"], "cell count", minimum=1),
            active_cell_count=_require_int(
                record["active_cell_count"], "active cell count", minimum=1
            ),
            applied_split_count=_require_int(
                record["applied_split_count"], "split count", minimum=0
            ),
            exact_target_match=_require_bool(
                record["exact_target_match"], "exact target match"
            ),
            unresolved_witness_id=unresolved_witness_id,
        )
        if record["candidate_id"] != result.candidate_id:
            raise FeatureSynthesisInvariantViolation("feature candidate ID mismatch")
        _require_canonical_document(record, result.to_document(), "feature candidate")
        return result


@dataclass(frozen=True, slots=True)
class SynthesisCandidateTraceV1:
    synthesis_spec_id: str
    feature_registry_id: str
    training_coverage_id: str
    target_partition_id: str
    candidates: tuple[FeatureSynthesisCandidateV1, ...]
    witnesses: tuple[FeatureRealizationWitnessV1, ...]
    selected_candidate_id: str | None
    best_failed_candidate_id: str | None
    status: FeatureRAPMSynthesisStatus
    schema: str = CANDIDATE_TRACE_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != CANDIDATE_TRACE_SCHEMA:
            raise FeatureSynthesisInvariantViolation("unsupported candidate trace schema")
        for field_name in (
            "synthesis_spec_id",
            "feature_registry_id",
            "training_coverage_id",
            "target_partition_id",
        ):
            _require_text(getattr(self, field_name), f"candidate trace {field_name}")
        if type(self.candidates) is not tuple or any(
            type(candidate) is not FeatureSynthesisCandidateV1
            for candidate in self.candidates
        ):
            raise FeatureSynthesisInvariantViolation(
                "candidate trace candidates must be exact candidate objects"
            )
        if type(self.witnesses) is not tuple or any(
            type(witness) is not FeatureRealizationWitnessV1
            for witness in self.witnesses
        ):
            raise FeatureSynthesisInvariantViolation(
                "candidate trace witnesses must be exact witness objects"
            )
        candidate_ids = tuple(candidate.candidate_id for candidate in self.candidates)
        if len(set(candidate_ids)) != len(candidate_ids):
            raise FeatureSynthesisInvariantViolation("candidate IDs must be unique")
        witness_ids = tuple(witness.witness_id for witness in self.witnesses)
        if len(set(witness_ids)) != len(witness_ids):
            raise FeatureSynthesisInvariantViolation("witness IDs must be unique")
        referenced_witness_ids = {
            candidate.unresolved_witness_id
            for candidate in self.candidates
            if candidate.unresolved_witness_id is not None
        }
        if not referenced_witness_ids <= set(witness_ids):
            raise FeatureSynthesisInvariantViolation(
                "candidate trace omits a referenced unresolved witness"
            )
        if self.status is FeatureRAPMSynthesisStatus.EXACT_FEATURE_REALIZATION:
            if self.selected_candidate_id not in set(candidate_ids):
                raise FeatureSynthesisInvariantViolation("selected candidate is absent")
            selected = next(
                candidate
                for candidate in self.candidates
                if candidate.candidate_id == self.selected_candidate_id
            )
            if not selected.exact_target_match:
                raise FeatureSynthesisInvariantViolation(
                    "selected candidate must exactly match the target"
                )
            if self.best_failed_candidate_id is not None:
                raise FeatureSynthesisInvariantViolation("success cannot bind a failed candidate")
        else:
            if self.selected_candidate_id is not None:
                raise FeatureSynthesisInvariantViolation("negative trace cannot select a candidate")
            if self.best_failed_candidate_id not in set(candidate_ids) or not self.witnesses:
                raise FeatureSynthesisInvariantViolation(
                    "negative trace requires a failed candidate and witness"
                )
            best = next(
                candidate
                for candidate in self.candidates
                if candidate.candidate_id == self.best_failed_candidate_id
            )
            if best.exact_target_match:
                raise FeatureSynthesisInvariantViolation(
                    "negative trace cannot bind an exact candidate"
                )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "synthesis_spec_id": self.synthesis_spec_id,
            "feature_registry_id": self.feature_registry_id,
            "training_coverage_id": self.training_coverage_id,
            "target_partition_id": self.target_partition_id,
            "candidates": [candidate.to_document() for candidate in self.candidates],
            "witnesses": [witness.to_document() for witness in self.witnesses],
            "selected_candidate_id": self.selected_candidate_id,
            "best_failed_candidate_id": self.best_failed_candidate_id,
            "status": self.status.value,
        }

    @property
    def candidate_trace_id(self) -> str:
        return _content_id(CANDIDATE_TRACE_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "candidate_trace_id": self.candidate_trace_id}

    @classmethod
    def from_document(cls, document: Any) -> "SynthesisCandidateTraceV1":
        required = {
            "schema",
            "synthesis_spec_id",
            "feature_registry_id",
            "training_coverage_id",
            "target_partition_id",
            "candidates",
            "witnesses",
            "selected_candidate_id",
            "best_failed_candidate_id",
            "status",
            "candidate_trace_id",
        }
        record = _require_exact_keys(document, required, "candidate trace")
        candidates = _require_list(record["candidates"], "candidate trace candidates")
        witnesses = _require_list(record["witnesses"], "candidate trace witnesses")
        selected_candidate_id = record["selected_candidate_id"]
        if selected_candidate_id is not None:
            selected_candidate_id = _require_text(
                selected_candidate_id, "selected_candidate_id"
            )
        best_failed_candidate_id = record["best_failed_candidate_id"]
        if best_failed_candidate_id is not None:
            best_failed_candidate_id = _require_text(
                best_failed_candidate_id, "best_failed_candidate_id"
            )
        result = cls(
            synthesis_spec_id=_require_text(
                record["synthesis_spec_id"], "candidate trace synthesis_spec_id"
            ),
            feature_registry_id=_require_text(
                record["feature_registry_id"], "candidate trace feature_registry_id"
            ),
            training_coverage_id=_require_text(
                record["training_coverage_id"], "candidate trace training_coverage_id"
            ),
            target_partition_id=_require_text(
                record["target_partition_id"], "candidate trace target_partition_id"
            ),
            candidates=tuple(
                FeatureSynthesisCandidateV1.from_document(item)
                for item in candidates
            ),
            witnesses=tuple(
                FeatureRealizationWitnessV1.from_document(item)
                for item in witnesses
            ),
            selected_candidate_id=selected_candidate_id,
            best_failed_candidate_id=best_failed_candidate_id,
            status=FeatureRAPMSynthesisStatus(
                _require_text(record["status"], "candidate trace status")
            ),
            schema=_require_text(record["schema"], "candidate trace schema"),
        )
        if record["candidate_trace_id"] != result.candidate_trace_id:
            raise FeatureSynthesisInvariantViolation("candidate trace ID mismatch")
        _require_canonical_document(record, result.to_document(), "candidate trace")
        return result


@dataclass(frozen=True, slots=True)
class FeatureRealizationCertificateV1:
    structural_id: str
    training_coverage_id: str
    feature_registry_id: str
    synthesis_spec_id: str
    candidate_trace_id: str
    selected_candidate_id: str
    predicate_tree_id: str
    target_partition_id: str
    realized_partition_id: str
    portable_model_id: str
    selected_features: tuple[str, ...]
    selected_thresholds: tuple[Fraction, ...]
    ground_state_count: int
    active_ground_state_count: int
    quotient_cell_count: int
    active_quotient_cell_count: int
    envelope_is_singleton: bool
    claim_scope: str = FEATURE_REALIZATION_CLAIM_SCOPE_V1
    official_execution_allowed: bool = False
    official_scalar_cost: None = None
    official_N_break_even: None = None
    workload_economics_gate: str = WORKLOAD_ECONOMICS_GATE_LOCKED
    counter_completeness_gate: str = COUNTER_COMPLETENESS_GATE_LOCKED
    schema: str = REALIZATION_CERTIFICATE_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != REALIZATION_CERTIFICATE_SCHEMA:
            raise FeatureSynthesisInvariantViolation("unsupported certificate schema")
        if self.official_execution_allowed is not False:
            raise FeatureSynthesisInvariantViolation("official execution must remain locked")
        if self.official_scalar_cost is not None or self.official_N_break_even is not None:
            raise FeatureSynthesisInvariantViolation("official scalar fields must remain null")
        if self.workload_economics_gate != WORKLOAD_ECONOMICS_GATE_LOCKED:
            raise FeatureSynthesisInvariantViolation(
                "workload economics Gate must remain NOT_RUN"
            )
        if self.counter_completeness_gate != COUNTER_COMPLETENESS_GATE_LOCKED:
            raise FeatureSynthesisInvariantViolation(
                "counter completeness Gate must remain NOT_RUN"
            )
        if self.claim_scope != FEATURE_REALIZATION_CLAIM_SCOPE_V1:
            raise FeatureSynthesisInvariantViolation(
                "feature realization claim scope differs from the frozen V1 contract"
            )
        if type(self.envelope_is_singleton) is not bool or not self.envelope_is_singleton:
            raise FeatureSynthesisInvariantViolation("exact realization requires singleton envelope")
        if type(self.selected_features) is not tuple or any(
            type(name) is not str or not name for name in self.selected_features
        ):
            raise FeatureSynthesisInvariantViolation(
                "certificate features must be a tuple of nonempty strings"
            )
        if type(self.selected_thresholds) is not tuple:
            raise FeatureSynthesisInvariantViolation(
                "certificate thresholds must be a tuple"
            )
        if tuple(sorted(self.selected_features)) != self.selected_features:
            raise FeatureSynthesisInvariantViolation("certificate features must be sorted")
        if len(set(self.selected_features)) != len(self.selected_features):
            raise FeatureSynthesisInvariantViolation(
                "certificate selected features must be unique"
            )
        if any(type(value) is not Fraction for value in self.selected_thresholds):
            raise FeatureSynthesisInvariantViolation(
                "certificate thresholds must be exact rationals"
            )
        if self.target_partition_id != self.realized_partition_id:
            raise FeatureSynthesisInvariantViolation("certificate partition IDs must match")
        full_sha_fields = (
            "structural_id",
            "training_coverage_id",
            "feature_registry_id",
            "synthesis_spec_id",
            "candidate_trace_id",
            "selected_candidate_id",
            "predicate_tree_id",
            "target_partition_id",
            "realized_partition_id",
        )
        for field_name in full_sha_fields:
            value = getattr(self, field_name)
            if (
                type(value) is not str
                or len(value) != 64
                or any(character not in "0123456789abcdef" for character in value)
            ):
                raise FeatureSynthesisInvariantViolation(
                    f"certificate {field_name} must be a full lowercase SHA-256"
                )
        if (
            type(self.portable_model_id) is not str
            or not self.portable_model_id.startswith("rapm:")
            or len(self.portable_model_id) != len("rapm:") + 64
        ):
            raise FeatureSynthesisInvariantViolation(
                "certificate portable model ID must be a full RAPM logical ID"
            )
        for label, value in (
            ("ground state count", self.ground_state_count),
            ("active ground state count", self.active_ground_state_count),
            ("quotient cell count", self.quotient_cell_count),
            ("active quotient cell count", self.active_quotient_cell_count),
        ):
            _require_int(value, label, minimum=1)
        if self.active_ground_state_count > self.ground_state_count:
            raise FeatureSynthesisInvariantViolation(
                "active ground count cannot exceed ground count"
            )
        if self.quotient_cell_count > self.ground_state_count:
            raise FeatureSynthesisInvariantViolation(
                "quotient cell count cannot exceed ground count"
            )
        if self.active_quotient_cell_count > min(
            self.active_ground_state_count, self.quotient_cell_count
        ):
            raise FeatureSynthesisInvariantViolation(
                "active quotient count exceeds a parent count"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "structural_id": self.structural_id,
            "training_coverage_id": self.training_coverage_id,
            "feature_registry_id": self.feature_registry_id,
            "synthesis_spec_id": self.synthesis_spec_id,
            "candidate_trace_id": self.candidate_trace_id,
            "selected_candidate_id": self.selected_candidate_id,
            "predicate_tree_id": self.predicate_tree_id,
            "target_partition_id": self.target_partition_id,
            "realized_partition_id": self.realized_partition_id,
            "portable_model_id": self.portable_model_id,
            "selected_features": list(self.selected_features),
            "selected_thresholds": [
                _fraction_document(value) for value in self.selected_thresholds
            ],
            "ground_state_count": self.ground_state_count,
            "active_ground_state_count": self.active_ground_state_count,
            "quotient_cell_count": self.quotient_cell_count,
            "active_quotient_cell_count": self.active_quotient_cell_count,
            "envelope_is_singleton": self.envelope_is_singleton,
            "claim_scope": self.claim_scope,
            "official_execution_allowed": self.official_execution_allowed,
            "official_scalar_cost": self.official_scalar_cost,
            "official_N_break_even": self.official_N_break_even,
            "workload_economics_gate": self.workload_economics_gate,
            "counter_completeness_gate": self.counter_completeness_gate,
        }

    @property
    def feature_realization_certificate_id(self) -> str:
        return _content_id(REALIZATION_CERTIFICATE_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "feature_realization_certificate_id": self.feature_realization_certificate_id,
        }

    @classmethod
    def from_document(cls, document: Any) -> "FeatureRealizationCertificateV1":
        identifier = "feature_realization_certificate_id"
        required = set(cls.__dataclass_fields__) | {identifier}
        record = _require_exact_keys(document, required, "feature realization certificate")
        kwargs = {key: record[key] for key in cls.__dataclass_fields__}
        selected_features = _require_list(
            kwargs["selected_features"], "certificate selected_features"
        )
        selected_thresholds = _require_list(
            kwargs["selected_thresholds"], "certificate selected_thresholds"
        )
        kwargs["selected_features"] = tuple(
            _require_text(item, "certificate selected feature")
            for item in selected_features
        )
        kwargs["selected_thresholds"] = tuple(
            _parse_fraction(value, "selected threshold")
            for value in selected_thresholds
        )
        result = cls(**kwargs)
        if record[identifier] != result.feature_realization_certificate_id:
            raise FeatureSynthesisInvariantViolation("feature certificate ID mismatch")
        _require_canonical_document(
            record,
            result.to_document(),
            "feature realization certificate",
        )
        return result


@dataclass(frozen=True, slots=True)
class FeatureRAPMSynthesisResultV1:
    status: FeatureRAPMSynthesisStatus
    feature_registry: FeatureRegistryV1
    synthesis_spec: SynthesisSpecV1
    behavioral_target: ExactBehavioralQuotient
    candidate_trace: SynthesisCandidateTraceV1
    predicate_tree: CanonicalPredicateTreeV1 | None
    realized_partition: Partition | None
    quotient_models: QuotientModels | None
    portable_build: PortableBuildResult | None
    certificate: FeatureRealizationCertificateV1 | None
    unresolved_witnesses: tuple[FeatureRealizationWitnessV1, ...]

    def __post_init__(self) -> None:
        _require_exact_synthesis_result_types_v1(self)
        if self.status is FeatureRAPMSynthesisStatus.EXACT_FEATURE_REALIZATION:
            if any(
                value is None
                for value in (
                    self.predicate_tree,
                    self.realized_partition,
                    self.quotient_models,
                    self.portable_build,
                    self.certificate,
                )
            ):
                raise FeatureSynthesisInvariantViolation("successful result is incomplete")
            if self.unresolved_witnesses:
                raise FeatureSynthesisInvariantViolation("successful result has witnesses")
        else:
            if any(
                value is not None
                for value in (
                    self.predicate_tree,
                    self.realized_partition,
                    self.quotient_models,
                    self.portable_build,
                    self.certificate,
                )
            ):
                raise FeatureSynthesisInvariantViolation(
                    "negative result must not publish a model or certificate"
                )
            if not self.unresolved_witnesses:
                raise FeatureSynthesisInvariantViolation("negative result requires witnesses")


def _require_exact_partition_v1(partition: object, label: str) -> Partition:
    if type(partition) is not Partition:
        raise FeatureSynthesisInvariantViolation(
            f"{label} must be an exact Partition"
        )
    if type(partition.assignments) is not tuple or any(
        type(row) is not tuple
        or len(row) != 2
        or type(row[0]) is not LMBState
        or type(row[1]) not in {str, BehavioralCellId}
        for row in partition.assignments
    ):
        raise FeatureSynthesisInvariantViolation(
            f"{label} assignments must be exact two-item tuples"
        )
    return partition


def _require_exact_behavioral_signature_v1(
    signature: object,
    label: str,
) -> BehavioralActionSignature:
    if type(signature) is not BehavioralActionSignature:
        raise FeatureSynthesisInvariantViolation(
            f"{label} must be an exact BehavioralActionSignature"
        )
    if type(signature.reward_features) is not tuple or any(
        type(row) is not tuple
        or len(row) != 2
        or type(row[0]) is not str
        or type(row[1]) is not Fraction
        for row in signature.reward_features
    ):
        raise FeatureSynthesisInvariantViolation(
            f"{label}.reward_features have substituted runtime types"
        )
    if type(signature.successor_probabilities) is not tuple or any(
        type(row) is not tuple
        or len(row) != 2
        or type(row[0]) is not BehavioralCellId
        or type(row[1]) is not Fraction
        for row in signature.successor_probabilities
    ):
        raise FeatureSynthesisInvariantViolation(
            f"{label}.successor_probabilities have substituted runtime types"
        )
    if (
        type(signature.failure_probability) is not Fraction
        or type(signature.termination_probability) is not Fraction
    ):
        raise FeatureSynthesisInvariantViolation(
            f"{label} probabilities must be exact Fractions"
        )
    return signature


def _require_exact_model_vector_v1(
    reward_features: object,
    successor_probabilities: object,
    failure_probability: object,
    termination_probability: object,
    label: str,
) -> None:
    if type(reward_features) is not tuple or any(
        type(row) is not tuple
        or len(row) != 2
        or type(row[0]) is not str
        or type(row[1]) is not Fraction
        for row in reward_features
    ):
        raise FeatureSynthesisInvariantViolation(
            f"{label}.reward_features have substituted runtime types"
        )
    if type(successor_probabilities) is not tuple or any(
        type(row) is not tuple
        or len(row) != 2
        or type(row[0]) not in {str, BehavioralCellId}
        or type(row[1]) is not Fraction
        for row in successor_probabilities
    ):
        raise FeatureSynthesisInvariantViolation(
            f"{label}.successor_probabilities have substituted runtime types"
        )
    if (
        type(failure_probability) is not Fraction
        or type(termination_probability) is not Fraction
    ):
        raise FeatureSynthesisInvariantViolation(
            f"{label} probabilities must be exact Fractions"
        )


def _require_exact_quotient_models_v1(
    models: object,
    label: str,
) -> QuotientModels:
    if type(models) is not QuotientModels:
        raise FeatureSynthesisInvariantViolation(
            f"{label} must be exact QuotientModels"
        )
    if type(models.nominal) is not NominalQuotient:
        raise FeatureSynthesisInvariantViolation(
            f"{label}.nominal must be exact NominalQuotient"
        )
    if type(models.envelope) is not ExactRealizationEnvelope:
        raise FeatureSynthesisInvariantViolation(
            f"{label}.envelope must be exact ExactRealizationEnvelope"
        )
    _require_exact_partition_v1(models.nominal.partition, f"{label}.nominal.partition")
    _require_exact_partition_v1(
        models.envelope.partition,
        f"{label}.envelope.partition",
    )
    if type(models.nominal.entries) is not tuple or any(
        type(entry) is not NominalEntry
        or type(entry.model) is not NominalActionModel
        or type(entry.cell) not in {str, BehavioralCellId}
        or type(entry.action) is not BehavioralActionSignature
        for entry in models.nominal.entries
    ):
        raise FeatureSynthesisInvariantViolation(
            f"{label}.nominal entries have substituted runtime types"
        )
    if type(models.envelope.entries) is not tuple or any(
        type(entry) is not EnvelopeEntry
        or type(entry.cell) not in {str, BehavioralCellId}
        or type(entry.action) is not BehavioralActionSignature
        or type(entry.realizations) is not tuple
        or any(
            type(realization) is not GroundRealization
            or type(realization.state) is not LMBState
            for realization in entry.realizations
        )
        for entry in models.envelope.entries
    ):
        raise FeatureSynthesisInvariantViolation(
            f"{label}.envelope entries have substituted runtime types"
        )
    for index, entry in enumerate(models.nominal.entries):
        _require_exact_behavioral_signature_v1(
            entry.action,
            f"{label}.nominal.entries[{index}].action",
        )
        _require_exact_model_vector_v1(
            entry.model.reward_features,
            entry.model.successor_probabilities,
            entry.model.failure_probability,
            entry.model.termination_probability,
            f"{label}.nominal.entries[{index}].model",
        )
        if type(entry.model.realization_count) is not int:
            raise FeatureSynthesisInvariantViolation(
                f"{label}.nominal realization_count must be an exact integer"
            )
    for index, entry in enumerate(models.envelope.entries):
        _require_exact_behavioral_signature_v1(
            entry.action,
            f"{label}.envelope.entries[{index}].action",
        )
        for realization_index, realization in enumerate(entry.realizations):
            _require_exact_model_vector_v1(
                realization.reward_features,
                realization.successor_probabilities,
                realization.failure_probability,
                realization.termination_probability,
                (
                    f"{label}.envelope.entries[{index}]"
                    f".realizations[{realization_index}]"
                ),
            )
    return models


def _require_exact_portable_build_v1(build: object) -> PortableBuildResult:
    if type(build) is not PortableBuildResult:
        raise FeatureSynthesisInvariantViolation(
            "portable_build has a substituted runtime type"
        )
    if type(build.model) is not PortableRAPM:
        raise FeatureSynthesisInvariantViolation(
            "portable_build.model has a substituted runtime type"
        )
    if type(build.model._canonical_document) is not str:
        raise FeatureSynthesisInvariantViolation(
            "portable_build.model payload has a substituted runtime type"
        )
    try:
        replayed_model = PortableRAPM.from_dict(build.model.to_dict())
    except (TypeError, ValueError, json.JSONDecodeError) as error:
        raise FeatureSynthesisInvariantViolation(
            "portable_build.model does not replay canonically"
        ) from error
    if replayed_model.to_dict() != build.model.to_dict():
        raise FeatureSynthesisInvariantViolation(
            "portable_build.model differs from its canonical replay"
        )
    if type(build.registry) is not PortableRegistry:
        raise FeatureSynthesisInvariantViolation(
            "portable_build.registry has a substituted runtime type"
        )
    registry_shapes = (
        (build.registry.state_records, 2, (LMBState, str)),
        (
            build.registry.cell_records,
            2,
            ((str, BehavioralCellId), str),
        ),
        (
            build.registry.semantic_action_records,
            3,
            ((str, BehavioralCellId), BehavioralActionSignature, str),
        ),
        (build.registry.ground_action_records, 3, (LMBState, LMBAction, str)),
    )
    for records, width, expected_types in registry_shapes:
        if type(records) is not tuple:
            raise FeatureSynthesisInvariantViolation(
                "portable registry records must be exact tuples"
            )
        for row in records:
            if type(row) is not tuple or len(row) != width:
                raise FeatureSynthesisInvariantViolation(
                    "portable registry row shape is not exact"
                )
            for value, expected_type in zip(row, expected_types):
                allowed = (
                    expected_type
                    if type(expected_type) is tuple
                    else (expected_type,)
                )
                if type(value) not in set(allowed):
                    raise FeatureSynthesisInvariantViolation(
                        "portable registry row has a substituted runtime type"
                    )
    return build


def _require_exact_behavioral_target_v1(
    target: object,
) -> ExactBehavioralQuotient:
    if type(target) is not ExactBehavioralQuotient:
        raise FeatureSynthesisInvariantViolation(
            "behavioral_target must be an exact ExactBehavioralQuotient"
        )
    _require_exact_partition_v1(target.partition, "behavioral_target.partition")
    if type(target.semantic_adapter) is not BehavioralSemanticAdapter:
        raise FeatureSynthesisInvariantViolation(
            "behavioral_target.semantic_adapter has a substituted runtime type"
        )
    if type(target.semantic_adapter.assignments) is not tuple or any(
        type(row) is not BehavioralActionAssignment
        or type(row.state) is not LMBState
        or type(row.ground_action) is not LMBAction
        or type(row.semantic_action) is not BehavioralActionSignature
        for row in target.semantic_adapter.assignments
    ):
        raise FeatureSynthesisInvariantViolation(
            "behavioral_target assignments have substituted runtime types"
        )
    for index, row in enumerate(target.semantic_adapter.assignments):
        _require_exact_behavioral_signature_v1(
            row.semantic_action,
            f"behavioral_target.assignments[{index}].semantic_action",
        )
    if type(target.refinement_trace) is not tuple or any(
        type(row) is not BehavioralRefinementStep for row in target.refinement_trace
    ):
        raise FeatureSynthesisInvariantViolation(
            "behavioral_target refinement trace has substituted runtime types"
        )
    if type(target.failure_targets) is not tuple or any(
        type(state) is not LMBState for state in target.failure_targets
    ):
        raise FeatureSynthesisInvariantViolation(
            "behavioral_target failure targets have substituted runtime types"
        )
    _require_exact_quotient_models_v1(
        target.quotient_models,
        "behavioral_target.quotient_models",
    )
    return target


def _require_exact_synthesis_result_types_v1(
    result: object,
) -> FeatureRAPMSynthesisResultV1:
    if type(result) is not FeatureRAPMSynthesisResultV1:
        raise FeatureSynthesisInvariantViolation(
            "synthesis result must be an exact FeatureRAPMSynthesisResultV1"
        )
    if type(result.status) is not FeatureRAPMSynthesisStatus:
        raise FeatureSynthesisInvariantViolation(
            "synthesis result status has a substituted runtime type"
        )
    if type(result.feature_registry) is not FeatureRegistryV1:
        raise FeatureSynthesisInvariantViolation(
            "feature_registry has a substituted runtime type"
        )
    result.feature_registry.__post_init__()
    if type(result.synthesis_spec) is not SynthesisSpecV1:
        raise FeatureSynthesisInvariantViolation(
            "synthesis_spec has a substituted runtime type"
        )
    result.synthesis_spec.__post_init__()
    _require_exact_behavioral_target_v1(result.behavioral_target)
    if type(result.candidate_trace) is not SynthesisCandidateTraceV1:
        raise FeatureSynthesisInvariantViolation(
            "candidate_trace has a substituted runtime type"
        )
    result.candidate_trace.__post_init__()
    for candidate in result.candidate_trace.candidates:
        candidate.__post_init__()
    for witness in result.candidate_trace.witnesses:
        witness.__post_init__()
    if result.predicate_tree is not None and type(result.predicate_tree) is not CanonicalPredicateTreeV1:
        raise FeatureSynthesisInvariantViolation(
            "predicate_tree has a substituted runtime type"
        )
    if result.predicate_tree is not None:
        result.predicate_tree.__post_init__()
        for atom in result.predicate_tree.generated_atoms:
            atom.__post_init__()
        for node in result.predicate_tree.split_nodes:
            node.__post_init__()
    if result.realized_partition is not None:
        _require_exact_partition_v1(result.realized_partition, "realized_partition")
    if result.quotient_models is not None:
        _require_exact_quotient_models_v1(result.quotient_models, "quotient_models")
    if result.portable_build is not None:
        _require_exact_portable_build_v1(result.portable_build)
    if result.certificate is not None and type(result.certificate) is not FeatureRealizationCertificateV1:
        raise FeatureSynthesisInvariantViolation(
            "certificate has a substituted runtime type"
        )
    if result.certificate is not None:
        result.certificate.__post_init__()
    if type(result.unresolved_witnesses) is not tuple or any(
        type(witness) is not FeatureRealizationWitnessV1
        for witness in result.unresolved_witnesses
    ):
        raise FeatureSynthesisInvariantViolation(
            "unresolved_witnesses have substituted runtime types"
        )
    for witness in result.unresolved_witnesses:
        witness.__post_init__()
    return result


def _base_partition(states: tuple[LMBState, ...]) -> Partition:
    mapping: dict[LMBState, str] = {}
    for state in states:
        if state.status is LMBStatus.ACTIVE:
            kind = "active"
        elif state.status is LMBStatus.FAILURE:
            kind = "failure"
        else:
            kind = "success"
        mapping[state] = _content_id(
            PREDICATE_CELL_DOMAIN,
            {"kind": "base_terminal_kind", "terminal_kind": kind},
        )
    return Partition.from_mapping(mapping)


def _feature_rows(
    kernel: LMBKernel,
    states: tuple[LMBState, ...],
    registry: FeatureRegistryV1,
) -> dict[LMBState, dict[str, Fraction]]:
    adapter = LMBSemanticAdapter()
    result: dict[LMBState, dict[str, Fraction]] = {}
    expected = set(registry.feature_names)
    for state in states:
        if state.status is not LMBStatus.ACTIVE:
            continue
        raw = {name: Fraction(value) for name, value in adapter.features(kernel, state)}
        if not expected <= set(raw):
            raise FeatureSynthesisInvariantViolation(
                "feature registry is not implemented by LMBSemanticAdapter"
            )
        result[state] = {name: raw[name] for name in registry.feature_names}
    if not result:
        raise FeatureSynthesisInvariantViolation("training coverage has no active states")
    return result


def _feature_atoms(
    feature_rows: Mapping[LMBState, Mapping[str, Fraction]],
    selected_features: tuple[str, ...],
) -> tuple[PredicateAtomV1, ...]:
    atoms: list[PredicateAtomV1] = []
    for name in selected_features:
        values = sorted({row[name] for row in feature_rows.values()})
        atoms.extend(
            PredicateAtomV1(name, "<=", (left + right) / 2)
            for left, right in zip(values, values[1:])
        )
    return tuple(atoms)


def _compile_predicate_tree(
    states: tuple[LMBState, ...],
    feature_rows: Mapping[LMBState, Mapping[str, Fraction]],
    selected_features: tuple[str, ...],
) -> tuple[CanonicalPredicateTreeV1, Partition]:
    partition = _base_partition(states)
    base_id = _partition_id(partition)
    atoms = _feature_atoms(feature_rows, selected_features)
    nodes: list[PredicateSplitNodeV1] = []
    for atom in atoms:
        active_cells = tuple(
            cell
            for cell in partition.cell_ids
            if all(state.status is LMBStatus.ACTIVE for state in partition.members(cell))
        )
        for cell in active_cells:
            members = partition.members(cell)
            true_states = tuple(
                state
                for state in members
                if feature_rows[state][atom.feature_name] <= atom.threshold
            )
            false_states = tuple(state for state in members if state not in set(true_states))
            if not true_states or not false_states:
                continue
            sequence = len(nodes) + 1
            true_id = _content_id(
                PREDICATE_CELL_DOMAIN,
                {
                    "parent_cell_id": str(cell),
                    "predicate_id": atom.predicate_id,
                    "branch": "true",
                },
            )
            false_id = _content_id(
                PREDICATE_CELL_DOMAIN,
                {
                    "parent_cell_id": str(cell),
                    "predicate_id": atom.predicate_id,
                    "branch": "false",
                },
            )
            partition = partition.replace_cell(
                cell,
                false_states,
                true_states,
                false_id,
                true_id,
            )
            nodes.append(
                PredicateSplitNodeV1(
                    sequence,
                    str(cell),
                    atom,
                    true_id,
                    false_id,
                    len(members),
                    len(true_states),
                    len(false_states),
                )
            )
    active_cells = sum(
        all(state.status is LMBStatus.ACTIVE for state in partition.members(cell))
        for cell in partition.cell_ids
    )
    tree = CanonicalPredicateTreeV1(
        selected_features=selected_features,
        generated_atoms=atoms,
        split_nodes=tuple(nodes),
        base_partition_id=base_id,
        final_partition_id=_partition_id(partition),
        final_cell_count=len(partition.cell_ids),
        active_cell_count=active_cells,
    )
    return tree, partition


def _cell_content_id(partition: Partition, state: LMBState) -> str:
    members = partition.members(partition.cell_of(state))
    return _content_id(
        PREDICATE_CELL_DOMAIN,
        {"member_state_ids": sorted(object_id(member, "state") for member in members)},
    )


def _partition_mismatch_witness(
    candidate: Partition,
    target: Partition,
) -> FeatureRealizationWitnessV1 | None:
    states = _ordered_states(candidate.states)
    # Prefer an oversplit witness when a candidate is incomparable with the
    # target.  This makes the two directions of partition mismatch observable
    # instead of always reporting the coarsening half of an incomparable pair.
    for index, left in enumerate(states):
        for right in states[index + 1 :]:
            if (
                candidate.cell_of(left) != candidate.cell_of(right)
                and target.cell_of(left) == target.cell_of(right)
            ):
                return FeatureRealizationWitnessV1(
                    witness_kind="TARGET_MERGED_FEATURE_SEPARATED",
                    left_state_id=object_id(left, "state"),
                    right_state_id=object_id(right, "state"),
                    left_target_cell_id=_cell_content_id(target, left),
                    right_target_cell_id=_cell_content_id(target, right),
                    left_candidate_cell_id=_cell_content_id(candidate, left),
                    right_candidate_cell_id=_cell_content_id(candidate, right),
                )
    for index, left in enumerate(states):
        for right in states[index + 1 :]:
            if (
                candidate.cell_of(left) == candidate.cell_of(right)
                and target.cell_of(left) != target.cell_of(right)
            ):
                return FeatureRealizationWitnessV1(
                    witness_kind="TARGET_SEPARATED_FEATURE_ALIASED",
                    left_state_id=object_id(left, "state"),
                    right_state_id=object_id(right, "state"),
                    left_target_cell_id=_cell_content_id(target, left),
                    right_target_cell_id=_cell_content_id(target, right),
                    left_candidate_cell_id=_cell_content_id(candidate, left),
                    right_candidate_cell_id=_cell_content_id(candidate, right),
                )
    return None


def _enumerate_subsets(names: tuple[str, ...]) -> tuple[tuple[str, ...], ...]:
    return tuple(
        subset
        for count in range(len(names) + 1)
        for subset in combinations(names, count)
    )


def _lmb_normalizer_rules(kernel: LMBKernel) -> tuple[dict[str, Any], ...]:
    match_cap = {
        "name": "match",
        "per_step_cap": fraction_to_json(Fraction(1)),
        "total_cap": fraction_to_json(Fraction(kernel.tile_count // 3)),
    }
    terminal_clear_cap = {
        "name": "terminal_clear",
        "per_step_cap": fraction_to_json(Fraction(kernel.clear_bonus)),
        "total_cap": fraction_to_json(Fraction(kernel.clear_bonus)),
    }
    return (
        {
            "proof_id": "lmb.canonical.matches_plus_clear_le_2n_over_3.v1",
            "kind": "nonnegative_feature_caps_v1",
            "reward_basis": (
                {"name": "match", "value": fraction_to_json(Fraction(1))},
                {"name": "terminal_clear", "value": fraction_to_json(Fraction(1))},
            ),
            "feature_caps": (match_cap, terminal_clear_cap),
        },
        {
            "proof_id": "lmb.match_only.matches_le_n_over_3.v1",
            "kind": "nonnegative_feature_caps_v1",
            "reward_basis": (
                {"name": "match", "value": fraction_to_json(Fraction(1))},
                {"name": "terminal_clear", "value": fraction_to_json(Fraction(0))},
            ),
            "feature_caps": (match_cap,),
        },
        {
            "proof_id": "lmb.terminal_clear_only.clear_bonus.v1",
            "kind": "nonnegative_feature_caps_v1",
            "reward_basis": (
                {"name": "match", "value": fraction_to_json(Fraction(0))},
                {"name": "terminal_clear", "value": fraction_to_json(Fraction(1))},
            ),
            "feature_caps": (terminal_clear_cap,),
        },
    )


def _portable_build(
    kernel: LMBKernel,
    coverage: SuiteBuildCoverage[LMBState],
    models: QuotientModels,
    failure_targets: tuple[LMBState, ...],
) -> PortableBuildResult:
    failures = set(failure_targets)
    return build_portable_rapm(
        models,
        state_ids=lambda state: object_id(state, "state"),
        semantic_action_ids=lambda action: object_id(action, "semantic-source"),
        ground_action_ids=lambda action: object_id(action, "ground-action-source"),
        normalizer_rules=_lmb_normalizer_rules(kernel),
        state_kinds=lambda state: (
            "failure"
            if state in failures
            else "terminal"
            if kernel.is_terminal(state)
            else "active"
        ),
        goal_ids=tuple(kernel.registered_goals),
        coverage=_coverage_payload(coverage),
    )


def _singleton_envelope(models: QuotientModels) -> bool:
    return all(
        len(
            {
                (
                    realization.reward_features,
                    realization.failure_probability,
                    realization.termination_probability,
                    realization.successor_probabilities,
                )
                for realization in entry.realizations
            }
        )
        == 1
        for entry in models.envelope.entries
    )


def _require_synthesis_inputs_v1(
    kernel: object,
    coverage: object,
) -> tuple[LMBKernel, SuiteBuildCoverage[LMBState]]:
    if type(kernel) is not LMBKernel:
        raise FeatureSynthesisInvariantViolation("V1 requires the canonical LMBKernel")
    if type(coverage) is not SuiteBuildCoverage:
        raise FeatureSynthesisInvariantViolation(
            "V1 requires a frozen SuiteBuildCoverage, not a query or state sample"
        )
    if any(type(state) is not LMBState for state in coverage.covered_states):
        raise FeatureSynthesisInvariantViolation("coverage contains non-LMB states")
    return kernel, coverage


def _synthesize_lmb_feature_rapm_profile_v1(
    kernel: LMBKernel,
    coverage: SuiteBuildCoverage[LMBState],
    *,
    registry: FeatureRegistryV1,
    spec: SynthesisSpecV1,
) -> FeatureRAPMSynthesisResultV1:
    """Shared exact engine behind the production and negative-control profiles."""

    _require_synthesis_inputs_v1(kernel, coverage)
    if type(registry) is not FeatureRegistryV1:
        raise FeatureSynthesisInvariantViolation(
            "feature registry must be an exact FeatureRegistryV1"
        )
    if type(spec) is not SynthesisSpecV1:
        raise FeatureSynthesisInvariantViolation(
            "synthesis spec must be an exact SynthesisSpecV1"
        )
    selected_registry = registry
    canonical_registry = lmb_feature_registry_v1(selected_registry.feature_names)
    if selected_registry.to_document() != canonical_registry.to_document():
        raise FeatureSynthesisInvariantViolation(
            "caller-supplied feature registry is not the canonical LMB V1 registry"
        )
    selected_spec = spec
    if selected_spec.structural_id != _structural_id(kernel):
        raise FeatureSynthesisInvariantViolation("synthesis spec structural binding mismatch")
    if selected_spec.training_coverage_id != _coverage_id(coverage):
        raise FeatureSynthesisInvariantViolation("synthesis spec coverage binding mismatch")
    if selected_spec.feature_registry_id != selected_registry.feature_registry_id:
        raise FeatureSynthesisInvariantViolation("synthesis spec registry binding mismatch")
    canonical_full_registry_id = lmb_feature_registry_v1().feature_registry_id
    if (
        selected_spec.profile_kind == CANONICAL_PRODUCTION_PROFILE_V1
        and selected_registry.feature_registry_id != canonical_full_registry_id
    ):
        raise FeatureSynthesisInvariantViolation(
            "production synthesis profile requires the complete canonical grammar"
        )
    if (
        selected_spec.profile_kind == RESTRICTED_NEGATIVE_CONTROL_PROFILE_V1
        and selected_registry.feature_registry_id == canonical_full_registry_id
    ):
        raise FeatureSynthesisInvariantViolation(
            "negative-control synthesis profile requires a restricted grammar"
        )

    states = _ordered_states(coverage.covered_states)
    target = build_exact_behavioral_quotient(kernel, states)
    target_partition_id = _partition_id(target.partition)
    feature_rows = _feature_rows(kernel, states, selected_registry)
    subsets = _enumerate_subsets(selected_registry.feature_names)
    if len(subsets) > selected_spec.candidate_cap:
        raise FeatureSynthesisInvariantViolation("feature candidate cap is insufficient")

    candidates: list[FeatureSynthesisCandidateV1] = []
    witnesses_by_id: dict[str, FeatureRealizationWitnessV1] = {}
    trees_by_candidate: dict[str, tuple[CanonicalPredicateTreeV1, Partition]] = {}
    exact_candidates: list[FeatureSynthesisCandidateV1] = []
    for subset in subsets:
        tree, partition = _compile_predicate_tree(states, feature_rows, subset)
        exact = partition.signature() == target.partition.signature()
        witness = None if exact else _partition_mismatch_witness(
            partition, target.partition
        )
        if not exact and witness is None:
            raise FeatureSynthesisInvariantViolation(
                "nonexact feature partition lacks a bidirectional mismatch witness"
            )
        if witness is not None:
            witnesses_by_id[witness.witness_id] = witness
        candidate = FeatureSynthesisCandidateV1(
            selected_features=subset,
            predicate_tree_id=tree.predicate_tree_id,
            final_partition_id=tree.final_partition_id,
            final_cell_count=tree.final_cell_count,
            active_cell_count=tree.active_cell_count,
            applied_split_count=len(tree.split_nodes),
            exact_target_match=exact,
            unresolved_witness_id=None if witness is None else witness.witness_id,
        )
        candidates.append(candidate)
        trees_by_candidate[candidate.candidate_id] = (tree, partition)
        if exact:
            exact_candidates.append(candidate)

    if not exact_candidates:
        best = min(
            candidates,
            key=lambda candidate: (
                -candidate.final_cell_count,
                len(candidate.selected_features),
                candidate.applied_split_count,
                candidate.selected_features,
                candidate.final_partition_id,
            ),
        )
        witness = witnesses_by_id[best.unresolved_witness_id]
        trace = SynthesisCandidateTraceV1(
            synthesis_spec_id=selected_spec.synthesis_spec_id,
            feature_registry_id=selected_registry.feature_registry_id,
            training_coverage_id=selected_spec.training_coverage_id,
            target_partition_id=target_partition_id,
            candidates=tuple(candidates),
            witnesses=tuple(
                sorted(witnesses_by_id.values(), key=lambda item: item.witness_id)
            ),
            selected_candidate_id=None,
            best_failed_candidate_id=best.candidate_id,
            status=FeatureRAPMSynthesisStatus.NO_EXACT_FEATURE_REALIZATION,
        )
        return FeatureRAPMSynthesisResultV1(
            FeatureRAPMSynthesisStatus.NO_EXACT_FEATURE_REALIZATION,
            selected_registry,
            selected_spec,
            target,
            trace,
            None,
            None,
            None,
            None,
            None,
            (witness,),
        )

    selected = min(
        exact_candidates,
        key=lambda candidate: (
            len(candidate.selected_features),
            candidate.applied_split_count,
            candidate.selected_features,
            candidate.final_partition_id,
        ),
    )
    tree, partition = trees_by_candidate[selected.candidate_id]
    trace = SynthesisCandidateTraceV1(
        synthesis_spec_id=selected_spec.synthesis_spec_id,
        feature_registry_id=selected_registry.feature_registry_id,
        training_coverage_id=selected_spec.training_coverage_id,
        target_partition_id=target_partition_id,
        candidates=tuple(candidates),
        witnesses=tuple(
            sorted(witnesses_by_id.values(), key=lambda item: item.witness_id)
        ),
        selected_candidate_id=selected.candidate_id,
        best_failed_candidate_id=None,
        status=FeatureRAPMSynthesisStatus.EXACT_FEATURE_REALIZATION,
    )
    models = build_quotient_models(
        kernel,
        states,
        partition,
        semantic_adapter=target.semantic_adapter,
    )
    singleton = _singleton_envelope(models)
    if not singleton:
        raise FeatureSynthesisInvariantViolation(
            "exact feature realization produced a non-singleton sound envelope"
        )
    portable = _portable_build(kernel, coverage, models, target.failure_targets)
    active_ground = sum(state.status is LMBStatus.ACTIVE for state in states)
    certificate = FeatureRealizationCertificateV1(
        structural_id=selected_spec.structural_id,
        training_coverage_id=selected_spec.training_coverage_id,
        feature_registry_id=selected_registry.feature_registry_id,
        synthesis_spec_id=selected_spec.synthesis_spec_id,
        candidate_trace_id=trace.candidate_trace_id,
        selected_candidate_id=selected.candidate_id,
        predicate_tree_id=tree.predicate_tree_id,
        target_partition_id=target_partition_id,
        realized_partition_id=_partition_id(partition),
        portable_model_id=portable.model.model_id,
        selected_features=selected.selected_features,
        selected_thresholds=tuple(atom.threshold for atom in tree.generated_atoms),
        ground_state_count=len(states),
        active_ground_state_count=active_ground,
        quotient_cell_count=len(partition.cell_ids),
        active_quotient_cell_count=tree.active_cell_count,
        envelope_is_singleton=singleton,
    )
    return FeatureRAPMSynthesisResultV1(
        FeatureRAPMSynthesisStatus.EXACT_FEATURE_REALIZATION,
        selected_registry,
        selected_spec,
        target,
        trace,
        tree,
        partition,
        models,
        portable,
        certificate,
        (),
    )


def synthesize_lmb_feature_rapm_v1(
    kernel: LMBKernel,
    coverage: SuiteBuildCoverage[LMBState],
) -> FeatureRAPMSynthesisResultV1:
    """Run the canonical production profile over the complete V1 grammar.

    The registry and spec are constructed internally so a caller cannot encode
    query, value, policy, J0, or held-out bits by selecting a grammar subset.
    """

    _require_synthesis_inputs_v1(kernel, coverage)
    registry = lmb_feature_registry_v1()
    spec = lmb_synthesis_spec_v1(kernel, coverage, registry)
    return _synthesize_lmb_feature_rapm_profile_v1(
        kernel,
        coverage,
        registry=registry,
        spec=spec,
    )


def synthesize_lmb_feature_rapm_negative_control_v1(
    kernel: LMBKernel,
    coverage: SuiteBuildCoverage[LMBState],
    *,
    registry: FeatureRegistryV1,
    spec: SynthesisSpecV1 | None = None,
) -> FeatureRAPMSynthesisResultV1:
    """Run an explicitly non-production restricted-grammar control."""

    _require_synthesis_inputs_v1(kernel, coverage)
    if type(registry) is not FeatureRegistryV1:
        raise FeatureSynthesisInvariantViolation(
            "negative-control registry must be an exact FeatureRegistryV1"
        )
    canonical_full = lmb_feature_registry_v1()
    if registry.feature_registry_id == canonical_full.feature_registry_id:
        raise FeatureSynthesisInvariantViolation(
            "the complete canonical grammar belongs to the production profile"
        )
    selected_spec = (
        lmb_synthesis_spec_v1(
            kernel,
            coverage,
            registry,
            profile_kind=RESTRICTED_NEGATIVE_CONTROL_PROFILE_V1,
        )
        if spec is None
        else spec
    )
    if selected_spec.profile_kind != RESTRICTED_NEGATIVE_CONTROL_PROFILE_V1:
        raise FeatureSynthesisInvariantViolation(
            "negative-control API requires negative-control spec provenance"
        )
    result = _synthesize_lmb_feature_rapm_profile_v1(
        kernel,
        coverage,
        registry=registry,
        spec=selected_spec,
    )
    if result.status is FeatureRAPMSynthesisStatus.EXACT_FEATURE_REALIZATION:
        raise FeatureSynthesisInvariantViolation(
            "negative-control profile cannot publish an exact realization or certificate"
        )
    return result


def _compare_synthesis_result_to_rebuild_v1(
    result: FeatureRAPMSynthesisResultV1,
    expected: FeatureRAPMSynthesisResultV1,
) -> tuple[str, ...]:
    failures: list[str] = []
    if result.status is not expected.status:
        failures.append("STATUS_MISMATCH")
    if result.feature_registry.to_document() != expected.feature_registry.to_document():
        failures.append("FEATURE_REGISTRY_MISMATCH")
    if result.synthesis_spec.to_document() != expected.synthesis_spec.to_document():
        failures.append("SYNTHESIS_SPEC_MISMATCH")
    if result.behavioral_target.partition.signature() != (
        expected.behavioral_target.partition.signature()
    ):
        failures.append("BEHAVIORAL_TARGET_PARTITION_MISMATCH")
    if result.behavioral_target.refinement_trace != (
        expected.behavioral_target.refinement_trace
    ):
        failures.append("BEHAVIORAL_TARGET_TRACE_MISMATCH")
    if result.behavioral_target.semantic_adapter != (
        expected.behavioral_target.semantic_adapter
    ):
        failures.append("BEHAVIORAL_TARGET_ADAPTER_MISMATCH")
    if result.behavioral_target.failure_targets != (
        expected.behavioral_target.failure_targets
    ):
        failures.append("BEHAVIORAL_TARGET_FAILURE_TARGET_MISMATCH")
    if result.behavioral_target.quotient_models != (
        expected.behavioral_target.quotient_models
    ):
        failures.append("BEHAVIORAL_TARGET_MODEL_MISMATCH")
    if result.candidate_trace.to_document() != expected.candidate_trace.to_document():
        failures.append("CANDIDATE_TRACE_MISMATCH")
    if (result.predicate_tree is None) != (expected.predicate_tree is None) or (
        result.predicate_tree is not None
        and result.predicate_tree.to_document() != expected.predicate_tree.to_document()
    ):
        failures.append("PREDICATE_TREE_MISMATCH")
    if (result.certificate is None) != (expected.certificate is None) or (
        result.certificate is not None
        and result.certificate.to_document() != expected.certificate.to_document()
    ):
        failures.append("CERTIFICATE_MISMATCH")
    if result.realized_partition != expected.realized_partition:
        failures.append("REALIZED_PARTITION_MISMATCH")
    if result.quotient_models != expected.quotient_models:
        failures.append("QUOTIENT_MODELS_MISMATCH")
    if (result.portable_build is None) != (expected.portable_build is None) or (
        result.portable_build is not None
        and result.portable_build.model.to_dict()
        != expected.portable_build.model.to_dict()
    ):
        failures.append("PORTABLE_MODEL_MISMATCH")
    if (result.portable_build is None) != (expected.portable_build is None) or (
        result.portable_build is not None
        and result.portable_build.registry != expected.portable_build.registry
    ):
        failures.append("PORTABLE_REGISTRY_MISMATCH")
    if tuple(witness.to_document() for witness in result.unresolved_witnesses) != tuple(
        witness.to_document() for witness in expected.unresolved_witnesses
    ):
        failures.append("UNRESOLVED_WITNESS_MISMATCH")
    return tuple(failures)


def verify_lmb_feature_rapm_synthesis_v1(
    kernel: LMBKernel,
    coverage: SuiteBuildCoverage[LMBState],
    result: FeatureRAPMSynthesisResultV1,
) -> tuple[str, ...]:
    """Rebuild the canonical production profile and reject runtime substitutes."""

    try:
        _require_exact_synthesis_result_types_v1(result)
    except FeatureSynthesisInvariantViolation:
        return ("RUNTIME_TYPE_MISMATCH",)
    expected = synthesize_lmb_feature_rapm_v1(kernel, coverage)
    return _compare_synthesis_result_to_rebuild_v1(result, expected)


def verify_lmb_feature_rapm_negative_control_v1(
    kernel: LMBKernel,
    coverage: SuiteBuildCoverage[LMBState],
    result: FeatureRAPMSynthesisResultV1,
) -> tuple[str, ...]:
    """Rebuild one explicitly restricted, non-production grammar control."""

    try:
        _require_exact_synthesis_result_types_v1(result)
        canonical_full = lmb_feature_registry_v1()
        if result.feature_registry.feature_registry_id == canonical_full.feature_registry_id:
            return ("NEGATIVE_CONTROL_PROFILE_MISMATCH",)
        if result.synthesis_spec.profile_kind != RESTRICTED_NEGATIVE_CONTROL_PROFILE_V1:
            return ("NEGATIVE_CONTROL_PROFILE_MISMATCH",)
        if (
            result.status is not FeatureRAPMSynthesisStatus.NO_EXACT_FEATURE_REALIZATION
            or result.certificate is not None
            or result.predicate_tree is not None
            or result.portable_build is not None
        ):
            return ("NEGATIVE_CONTROL_PROFILE_MISMATCH",)
        expected = _synthesize_lmb_feature_rapm_profile_v1(
            kernel,
            coverage,
            registry=result.feature_registry,
            spec=result.synthesis_spec,
        )
    except FeatureSynthesisInvariantViolation:
        return ("RUNTIME_TYPE_MISMATCH",)
    return _compare_synthesis_result_to_rebuild_v1(result, expected)


def replace_candidate_trace_for_attack(
    result: FeatureRAPMSynthesisResultV1,
    trace: SynthesisCandidateTraceV1,
) -> FeatureRAPMSynthesisResultV1:
    """Test helper: create a coherently re-hashed but semantically forged trace."""

    return replace(result, candidate_trace=trace)


__all__ = [
    "CANONICAL_PRODUCTION_PROFILE_V1",
    "CanonicalPredicateTreeV1",
    "FeatureDefinitionV1",
    "FeatureRAPMSynthesisResultV1",
    "FeatureRAPMSynthesisStatus",
    "FeatureRealizationCertificateV1",
    "FeatureRealizationWitnessV1",
    "FeatureRegistryV1",
    "FeatureSynthesisCandidateV1",
    "FeatureSynthesisInvariantViolation",
    "LMB_FEATURE_IMPLEMENTATION_SHA256_V1",
    "PredicateAtomV1",
    "PredicateSplitNodeV1",
    "RESTRICTED_NEGATIVE_CONTROL_PROFILE_V1",
    "SynthesisCandidateTraceV1",
    "SynthesisSpecV1",
    "lmb_feature_registry_v1",
    "lmb_synthesis_spec_v1",
    "replace_candidate_trace_for_attack",
    "synthesize_lmb_feature_rapm_negative_control_v1",
    "synthesize_lmb_feature_rapm_v1",
    "verify_lmb_feature_rapm_negative_control_v1",
    "verify_lmb_feature_rapm_synthesis_v1",
]
