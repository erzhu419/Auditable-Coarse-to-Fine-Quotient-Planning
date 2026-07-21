"""Direct synthesis of an exact homomorphic LMB quotient from frozen grammars.

Unlike the V0-038 feature-realization control, this construction has no
behavioural-quotient target.  It enumerates state and action feature subsets
and accepts a candidate only after directly proving the exact homomorphism
obligations against the authoritative one-step kernel.  Query specifications,
scalar rewards, value/Q functions, policies, J0, and held-out data are not
inputs to this module.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
from fractions import Fraction
import hashlib
import inspect
from itertools import combinations
from typing import Any, Iterable, Mapping

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


STATE_REGISTRY_SCHEMA = "acfqp.direct_state_feature_registry@v1"
ACTION_REGISTRY_SCHEMA = "acfqp.direct_action_feature_registry@v1"
DIRECT_SPEC_SCHEMA = "acfqp.direct_homomorphism_synthesis_spec@v1"
DIRECT_TRACE_SCHEMA = "acfqp.direct_homomorphism_candidate_trace@v1"
DIRECT_CERTIFICATE_SCHEMA = "acfqp.direct_homomorphism_certificate@v1"

STATE_REGISTRY_DOMAIN = "acfqp:direct-state-feature-registry:v1"
ACTION_REGISTRY_DOMAIN = "acfqp:direct-action-feature-registry:v1"
DIRECT_SPEC_DOMAIN = "acfqp:direct-homomorphism-synthesis-spec:v1"
STRUCTURAL_DOMAIN = "acfqp:direct-lmb-structural:v1"
COVERAGE_DOMAIN = "acfqp:direct-training-coverage:v1"
PARTITION_DOMAIN = "acfqp:direct-feature-partition:v1"
CELL_DOMAIN = "acfqp:direct-feature-cell:v1"
ATOM_DOMAIN = "acfqp:direct-state-predicate-atom:v1"
TREE_DOMAIN = "acfqp:direct-state-predicate-tree:v1"
LABEL_DOMAIN = "acfqp:direct-semantic-action-label:v1"
SIGNATURE_DOMAIN = "acfqp:direct-one-step-signature:v1"
WITNESS_DOMAIN = "acfqp:direct-homomorphism-witness:v1"
CANDIDATE_DOMAIN = "acfqp:direct-homomorphism-candidate:v1"
TRACE_DOMAIN = "acfqp:direct-homomorphism-candidate-trace:v1"
CERTIFICATE_DOMAIN = "acfqp:direct-homomorphism-certificate:v1"

THRESHOLD_GENERATOR = "adjacent_distinct_value_midpoints_v1"
SELECTION_RULE = (
    "minimum_state_feature_count_then_action_feature_count_then_split_count_"
    "then_state_names_then_action_names_then_partition_id_v1"
)
ALLOWED_CHANNELS = (
    "exact_one_step_transition_kernel",
    "frozen_state_action_feature_registries",
    "frozen_structural_kernel",
    "frozen_training_coverage",
)
FORBIDDEN_CHANNELS = (
    "BehavioralActionSignature",
    "J0",
    "Q_values",
    "QuerySpec",
    "behavioral_quotient_target",
    "heldout_data",
    "policy",
    "value_function",
)
CLAIM_SCOPE = (
    "direct exact homomorphism verification from preregistered state and action "
    "grammars; no feature-invention, partial-model, scale, query, value, policy, "
    "or heldout claim"
)
WORKLOAD_GATE = "WORKLOAD_ECONOMICS_GATE_NOT_RUN"
COUNTER_GATE = "COUNTER_COMPLETENESS_GATE_NOT_RUN"


class DirectSynthesisInvariantViolation(ValueError):
    """A direct-synthesis contract or exact obligation was malformed."""


class DirectSynthesisStatus(str, Enum):
    EXACT_DIRECT_HOMOMORPHISM = "EXACT_DIRECT_HOMOMORPHISM"
    NO_EXACT_DIRECT_HOMOMORPHISM = "NO_EXACT_DIRECT_HOMOMORPHISM"
    CANDIDATE_CAP_EXHAUSTED = "CANDIDATE_CAP_EXHAUSTED"
    RESTRICTED_CONTROL_EXACT_FOUND = "RESTRICTED_CONTROL_EXACT_FOUND"


def _content_id(domain: str, payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        domain.encode("utf-8") + b"\x00" + canonical_json_bytes(dict(payload))
    ).hexdigest()


def _exact(document: Any, keys: set[str], label: str) -> dict[str, Any]:
    if type(document) is not dict or set(document) != keys:
        raise DirectSynthesisInvariantViolation(
            f"{label} must contain exactly {tuple(sorted(keys))!r}"
        )
    return document


def _text(value: Any, label: str) -> str:
    if type(value) is not str or not value:
        raise DirectSynthesisInvariantViolation(f"{label} must be nonempty text")
    return value


def _integer(value: Any, label: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise DirectSynthesisInvariantViolation(
            f"{label} must be an integer >= {minimum}"
        )
    return value


def _fraction_doc(value: Fraction) -> dict[str, int]:
    value = Fraction(value)
    return {"numerator": value.numerator, "denominator": value.denominator}


def _fraction(value: Any, label: str) -> Fraction:
    record = _exact(value, {"numerator", "denominator"}, label)
    if type(record["numerator"]) is not int:
        raise DirectSynthesisInvariantViolation(f"{label}.numerator must be integer")
    denominator = _integer(record["denominator"], f"{label}.denominator", 1)
    result = Fraction(record["numerator"], denominator)
    if _fraction_doc(result) != record:
        raise DirectSynthesisInvariantViolation(f"{label} must be reduced")
    return result


def _full_sha(value: Any, label: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise DirectSynthesisInvariantViolation(f"{label} must be full lowercase SHA-256")
    return value


def _states(states: Iterable[LMBState]) -> tuple[LMBState, ...]:
    return tuple(sorted(states, key=repr))


def _structural_payload(kernel: LMBKernel) -> dict[str, Any]:
    return {
        "tile_types": list(kernel.tile_types),
        "blockers": [sorted(value) for value in kernel.blockers],
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


STATE_FEATURE_SEMANTICS = {
    "action_count": "number of currently legal primitive tile selections",
    "branching_count": "number of currently legal primitive tile selections",
    "buffer_occupancy": "sum of current per-type buffer counts",
    "capacity_slack": "remaining buffer capacity divided by total capacity",
    "capacity_slack_count": "remaining buffer capacity as an integer count",
    "immediate_release_liquidity": (
        "twice immediately matching legal actions divided by capacity times action count"
    ),
    "match_debt_mean": "mean fractional tiles required to complete each type triple",
    "match_debt_min": "minimum fractional tiles required to complete a type triple",
    "match_debt_nonzero_types": "number of types with nonzero match debt",
    "max_match_debt": "maximum fractional tiles required to complete a type triple",
    "remaining_object_count": "number of tiles not yet removed",
}
ACTION_FEATURE_SEMANTICS = {
    "completes_match": (
        "one iff the selected tile's type currently has buffer count two"
    ),
}
STATE_FEATURE_IMPLEMENTATION_SHA256 = (
    "823b48f9eb22975b3f1e97bc64e3074cc74ae7b48772c021d80b24d98064de98"
)
ACTION_FEATURE_IMPLEMENTATION_SHA256 = (
    "9941d077f5d78e1581c7462b17f6319820e1d5cabda1a9bd715c06c42e91d994"
)
FEATURE_IMPLEMENTATION_EPOCH_ID = (
    "acfqp_lmb_direct_feature_implementation_epoch_2026_07_21_v1"
)


def _action_feature_values(
    kernel: LMBKernel,
    state: LMBState,
    action: LMBAction,
) -> dict[str, Fraction]:
    tile_type = kernel.tile_types[action.tile]
    return {
        "completes_match": Fraction(state.buffer[tile_type] == 2),
    }


def _validate_feature_implementation_authority() -> None:
    """Compare runtime implementations to independently frozen epoch digests."""

    state_digest = hashlib.sha256(
        inspect.getsource(LMBSemanticAdapter.features).encode("utf-8")
    ).hexdigest()
    action_digest = hashlib.sha256(
        inspect.getsource(_action_feature_values).encode("utf-8")
    ).hexdigest()
    if state_digest != STATE_FEATURE_IMPLEMENTATION_SHA256:
        raise DirectSynthesisInvariantViolation(
            "runtime state-feature implementation differs from frozen authority"
        )
    if action_digest != ACTION_FEATURE_IMPLEMENTATION_SHA256:
        raise DirectSynthesisInvariantViolation(
            "runtime action-feature implementation differs from frozen authority"
        )


@dataclass(frozen=True, order=True, slots=True)
class DirectFeatureDefinitionV1:
    feature_name: str
    scope: str
    value_kind: str
    semantics_id: str
    semantics: str
    implementation_sha256: str

    def __post_init__(self) -> None:
        for name in ("feature_name", "scope", "value_kind", "semantics_id", "semantics"):
            _text(getattr(self, name), name)
        _full_sha(self.implementation_sha256, "feature implementation digest")

    def to_document(self) -> dict[str, Any]:
        return {
            "feature_name": self.feature_name,
            "scope": self.scope,
            "value_kind": self.value_kind,
            "semantics_id": self.semantics_id,
            "semantics": self.semantics,
            "implementation_sha256": self.implementation_sha256,
        }

    @classmethod
    def from_document(cls, document: Any) -> "DirectFeatureDefinitionV1":
        keys = {
            "feature_name",
            "scope",
            "value_kind",
            "semantics_id",
            "semantics",
            "implementation_sha256",
        }
        return cls(**_exact(document, keys, "direct feature definition"))


def _expected_definition(name: str, scope: str) -> DirectFeatureDefinitionV1:
    semantics = STATE_FEATURE_SEMANTICS if scope == "state" else ACTION_FEATURE_SEMANTICS
    implementation = (
        STATE_FEATURE_IMPLEMENTATION_SHA256
        if scope == "state"
        else ACTION_FEATURE_IMPLEMENTATION_SHA256
    )
    if name not in semantics:
        raise DirectSynthesisInvariantViolation(f"unregistered {scope} feature {name!r}")
    return DirectFeatureDefinitionV1(
        name,
        scope,
        "exact_rational",
        f"lmb.direct_{scope}_feature.{name}.v1",
        semantics[name],
        implementation,
    )


@dataclass(frozen=True, slots=True)
class DirectStateFeatureRegistryV1:
    definitions: tuple[DirectFeatureDefinitionV1, ...]
    implementation_epoch_id: str = FEATURE_IMPLEMENTATION_EPOCH_ID
    schema: str = STATE_REGISTRY_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != STATE_REGISTRY_SCHEMA or not self.definitions:
            raise DirectSynthesisInvariantViolation("invalid direct state registry schema/content")
        if self.implementation_epoch_id != FEATURE_IMPLEMENTATION_EPOCH_ID:
            raise DirectSynthesisInvariantViolation("state implementation epoch substitution")
        if type(self.definitions) is not tuple or any(
            type(item) is not DirectFeatureDefinitionV1 for item in self.definitions
        ):
            raise DirectSynthesisInvariantViolation("state definitions require exact tuple/types")
        if tuple(sorted(self.definitions)) != self.definitions:
            raise DirectSynthesisInvariantViolation("state definitions must be canonical")
        if len({item.feature_name for item in self.definitions}) != len(self.definitions):
            raise DirectSynthesisInvariantViolation("state feature names must be unique")
        if any(item != _expected_definition(item.feature_name, "state") for item in self.definitions):
            raise DirectSynthesisInvariantViolation("state registry semantic substitution")

    @property
    def feature_names(self) -> tuple[str, ...]:
        return tuple(item.feature_name for item in self.definitions)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "implementation_epoch_id": self.implementation_epoch_id,
            "definitions": [item.to_document() for item in self.definitions],
        }

    @property
    def registry_id(self) -> str:
        return _content_id(STATE_REGISTRY_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "registry_id": self.registry_id}

    @classmethod
    def from_document(cls, document: Any) -> "DirectStateFeatureRegistryV1":
        record = _exact(
            document,
            {"schema", "implementation_epoch_id", "definitions", "registry_id"},
            "state registry",
        )
        if type(record["definitions"]) is not list:
            raise DirectSynthesisInvariantViolation("state registry definitions must be a list")
        result = cls(
            tuple(DirectFeatureDefinitionV1.from_document(item) for item in record["definitions"]),
            record["implementation_epoch_id"],
            record["schema"],
        )
        if record["registry_id"] != result.registry_id:
            raise DirectSynthesisInvariantViolation("state registry ID mismatch")
        if record != result.to_document():
            raise DirectSynthesisInvariantViolation("state registry document is noncanonical")
        return result


@dataclass(frozen=True, slots=True)
class DirectActionFeatureRegistryV1:
    definitions: tuple[DirectFeatureDefinitionV1, ...]
    implementation_epoch_id: str = FEATURE_IMPLEMENTATION_EPOCH_ID
    schema: str = ACTION_REGISTRY_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != ACTION_REGISTRY_SCHEMA or not self.definitions:
            raise DirectSynthesisInvariantViolation("invalid direct action registry schema/content")
        if self.implementation_epoch_id != FEATURE_IMPLEMENTATION_EPOCH_ID:
            raise DirectSynthesisInvariantViolation("action implementation epoch substitution")
        if type(self.definitions) is not tuple or any(
            type(item) is not DirectFeatureDefinitionV1 for item in self.definitions
        ):
            raise DirectSynthesisInvariantViolation("action definitions require exact tuple/types")
        if tuple(sorted(self.definitions)) != self.definitions:
            raise DirectSynthesisInvariantViolation("action definitions must be canonical")
        if len({item.feature_name for item in self.definitions}) != len(self.definitions):
            raise DirectSynthesisInvariantViolation("action feature names must be unique")
        if any(item != _expected_definition(item.feature_name, "action") for item in self.definitions):
            raise DirectSynthesisInvariantViolation("action registry semantic substitution")

    @property
    def feature_names(self) -> tuple[str, ...]:
        return tuple(item.feature_name for item in self.definitions)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "implementation_epoch_id": self.implementation_epoch_id,
            "definitions": [item.to_document() for item in self.definitions],
        }

    @property
    def registry_id(self) -> str:
        return _content_id(ACTION_REGISTRY_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "registry_id": self.registry_id}

    @classmethod
    def from_document(cls, document: Any) -> "DirectActionFeatureRegistryV1":
        record = _exact(
            document,
            {"schema", "implementation_epoch_id", "definitions", "registry_id"},
            "action registry",
        )
        if type(record["definitions"]) is not list:
            raise DirectSynthesisInvariantViolation("action registry definitions must be a list")
        result = cls(
            tuple(DirectFeatureDefinitionV1.from_document(item) for item in record["definitions"]),
            record["implementation_epoch_id"],
            record["schema"],
        )
        if record["registry_id"] != result.registry_id:
            raise DirectSynthesisInvariantViolation("action registry ID mismatch")
        if record != result.to_document():
            raise DirectSynthesisInvariantViolation("action registry document is noncanonical")
        return result


def direct_state_feature_registry_v1(
    feature_names: Iterable[str] | None = None,
) -> DirectStateFeatureRegistryV1:
    names = tuple(sorted(STATE_FEATURE_SEMANTICS if feature_names is None else set(feature_names)))
    if not names:
        raise DirectSynthesisInvariantViolation("state registry cannot be empty")
    return DirectStateFeatureRegistryV1(tuple(_expected_definition(name, "state") for name in names))


def direct_action_feature_registry_v1(
    feature_names: Iterable[str] | None = None,
) -> DirectActionFeatureRegistryV1:
    names = tuple(sorted(ACTION_FEATURE_SEMANTICS if feature_names is None else set(feature_names)))
    if not names:
        raise DirectSynthesisInvariantViolation("action registry cannot be empty")
    return DirectActionFeatureRegistryV1(tuple(_expected_definition(name, "action") for name in names))


@dataclass(frozen=True, slots=True)
class DirectHomomorphismSynthesisSpecV1:
    structural_id: str
    training_coverage_id: str
    state_registry_id: str
    action_registry_id: str
    candidate_cap: int = 4096
    execution_profile: str = "production_full_grammar_v1"
    allowed_information_channels: tuple[str, ...] = ALLOWED_CHANNELS
    forbidden_information_channels: tuple[str, ...] = FORBIDDEN_CHANNELS
    threshold_generator: str = THRESHOLD_GENERATOR
    selection_rule: str = SELECTION_RULE
    obligation_profile: str = "direct_exact_state_action_homomorphism_v1"
    schema: str = DIRECT_SPEC_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != DIRECT_SPEC_SCHEMA:
            raise DirectSynthesisInvariantViolation("invalid direct synthesis spec schema")
        for name in ("structural_id", "training_coverage_id", "state_registry_id", "action_registry_id"):
            _full_sha(getattr(self, name), name)
        _integer(self.candidate_cap, "candidate cap", 1)
        if type(self.allowed_information_channels) is not tuple or type(self.forbidden_information_channels) is not tuple:
            raise DirectSynthesisInvariantViolation("spec channels require exact tuple types")
        if self.allowed_information_channels != ALLOWED_CHANNELS:
            raise DirectSynthesisInvariantViolation("allowed-channel contract substitution")
        if self.forbidden_information_channels != FORBIDDEN_CHANNELS:
            raise DirectSynthesisInvariantViolation("forbidden-channel contract substitution")
        if self.threshold_generator != THRESHOLD_GENERATOR:
            raise DirectSynthesisInvariantViolation("threshold-generator substitution")
        if self.selection_rule != SELECTION_RULE:
            raise DirectSynthesisInvariantViolation("selection-rule substitution")
        if self.obligation_profile != "direct_exact_state_action_homomorphism_v1":
            raise DirectSynthesisInvariantViolation("obligation-profile substitution")
        if self.execution_profile not in {
            "production_full_grammar_v1",
            "restricted_negative_control_v1",
        }:
            raise DirectSynthesisInvariantViolation("execution-profile substitution")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "structural_id": self.structural_id,
            "training_coverage_id": self.training_coverage_id,
            "state_registry_id": self.state_registry_id,
            "action_registry_id": self.action_registry_id,
            "candidate_cap": self.candidate_cap,
            "execution_profile": self.execution_profile,
            "allowed_information_channels": list(self.allowed_information_channels),
            "forbidden_information_channels": list(self.forbidden_information_channels),
            "threshold_generator": self.threshold_generator,
            "selection_rule": self.selection_rule,
            "obligation_profile": self.obligation_profile,
        }

    @property
    def spec_id(self) -> str:
        return _content_id(DIRECT_SPEC_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "spec_id": self.spec_id}

    @classmethod
    def from_document(cls, document: Any) -> "DirectHomomorphismSynthesisSpecV1":
        keys = {
            "schema", "structural_id", "training_coverage_id", "state_registry_id",
            "action_registry_id", "candidate_cap", "execution_profile", "allowed_information_channels",
            "forbidden_information_channels", "threshold_generator", "selection_rule",
            "obligation_profile", "spec_id",
        }
        record = _exact(document, keys, "direct synthesis spec")
        if type(record["allowed_information_channels"]) is not list or type(record["forbidden_information_channels"]) is not list:
            raise DirectSynthesisInvariantViolation("spec channel fields must be lists")
        result = cls(
            structural_id=record["structural_id"],
            training_coverage_id=record["training_coverage_id"],
            state_registry_id=record["state_registry_id"],
            action_registry_id=record["action_registry_id"],
            candidate_cap=record["candidate_cap"],
            execution_profile=record["execution_profile"],
            allowed_information_channels=tuple(record["allowed_information_channels"]),
            forbidden_information_channels=tuple(record["forbidden_information_channels"]),
            threshold_generator=record["threshold_generator"],
            selection_rule=record["selection_rule"],
            obligation_profile=record["obligation_profile"],
            schema=record["schema"],
        )
        if record["spec_id"] != result.spec_id:
            raise DirectSynthesisInvariantViolation("direct synthesis spec ID mismatch")
        if record != result.to_document():
            raise DirectSynthesisInvariantViolation("direct synthesis spec document is noncanonical")
        return result


def direct_synthesis_spec_v1(
    kernel: LMBKernel,
    coverage: SuiteBuildCoverage[LMBState],
    state_registry: DirectStateFeatureRegistryV1,
    action_registry: DirectActionFeatureRegistryV1,
    *,
    candidate_cap: int = 4096,
) -> DirectHomomorphismSynthesisSpecV1:
    return DirectHomomorphismSynthesisSpecV1(
        _structural_id(kernel),
        _coverage_id(coverage),
        state_registry.registry_id,
        action_registry.registry_id,
        candidate_cap,
    )


def _negative_control_spec_v1(
    kernel: LMBKernel,
    coverage: SuiteBuildCoverage[LMBState],
    state_registry: DirectStateFeatureRegistryV1,
    action_registry: DirectActionFeatureRegistryV1,
    candidate_cap: int,
) -> DirectHomomorphismSynthesisSpecV1:
    return DirectHomomorphismSynthesisSpecV1(
        _structural_id(kernel),
        _coverage_id(coverage),
        state_registry.registry_id,
        action_registry.registry_id,
        candidate_cap,
        "restricted_negative_control_v1",
    )


@dataclass(frozen=True, order=True, slots=True)
class DirectPredicateAtomV1:
    feature_name: str
    threshold: Fraction

    def __post_init__(self) -> None:
        if self.feature_name not in STATE_FEATURE_SEMANTICS:
            raise DirectSynthesisInvariantViolation("predicate uses an unknown state feature")
        if type(self.threshold) is not Fraction:
            raise DirectSynthesisInvariantViolation("predicate threshold requires exact Fraction")

    def _payload(self) -> dict[str, Any]:
        return {
            "feature_name": self.feature_name,
            "operator": "<=",
            "threshold": _fraction_doc(self.threshold),
        }

    @property
    def atom_id(self) -> str:
        return _content_id(ATOM_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "atom_id": self.atom_id}

    @classmethod
    def from_document(cls, document: Any) -> "DirectPredicateAtomV1":
        record = _exact(document, {"feature_name", "operator", "threshold", "atom_id"}, "direct predicate atom")
        if record["operator"] != "<=":
            raise DirectSynthesisInvariantViolation("predicate operator substitution")
        result = cls(record["feature_name"], _fraction(record["threshold"], "predicate threshold"))
        if record["atom_id"] != result.atom_id or record != result.to_document():
            raise DirectSynthesisInvariantViolation("predicate atom ID/document mismatch")
        return result


@dataclass(frozen=True, slots=True)
class DirectPredicateSplitV1:
    sequence: int
    parent_cell_id: str
    atom: DirectPredicateAtomV1
    true_child_cell_id: str
    false_child_cell_id: str
    true_member_count: int
    false_member_count: int

    def __post_init__(self) -> None:
        if type(self.atom) is not DirectPredicateAtomV1:
            raise DirectSynthesisInvariantViolation("predicate split atom type substitution")
        _integer(self.sequence, "split sequence", 1)
        _integer(self.true_member_count, "true member count", 1)
        _integer(self.false_member_count, "false member count", 1)
        for name in ("parent_cell_id", "true_child_cell_id", "false_child_cell_id"):
            _full_sha(getattr(self, name), name)

    def to_document(self) -> dict[str, Any]:
        return {
            "sequence": self.sequence,
            "parent_cell_id": self.parent_cell_id,
            "atom": self.atom.to_document(),
            "true_child_cell_id": self.true_child_cell_id,
            "false_child_cell_id": self.false_child_cell_id,
            "true_member_count": self.true_member_count,
            "false_member_count": self.false_member_count,
        }

    @classmethod
    def from_document(cls, document: Any) -> "DirectPredicateSplitV1":
        keys = {
            "sequence", "parent_cell_id", "atom", "true_child_cell_id",
            "false_child_cell_id", "true_member_count", "false_member_count",
        }
        record = _exact(document, keys, "direct predicate split")
        result = cls(
            record["sequence"], record["parent_cell_id"],
            DirectPredicateAtomV1.from_document(record["atom"]),
            record["true_child_cell_id"], record["false_child_cell_id"],
            record["true_member_count"], record["false_member_count"],
        )
        if record != result.to_document():
            raise DirectSynthesisInvariantViolation("predicate split document is noncanonical")
        return result


@dataclass(frozen=True, slots=True)
class DirectPredicateTreeV1:
    selected_state_features: tuple[str, ...]
    generated_atoms: tuple[DirectPredicateAtomV1, ...]
    splits: tuple[DirectPredicateSplitV1, ...]
    partition_id: str
    cell_count: int
    active_cell_count: int

    def __post_init__(self) -> None:
        if type(self.selected_state_features) is not tuple or type(self.generated_atoms) is not tuple or type(self.splits) is not tuple:
            raise DirectSynthesisInvariantViolation("predicate tree nested fields require tuples")
        if any(type(item) is not DirectPredicateAtomV1 for item in self.generated_atoms) or any(type(item) is not DirectPredicateSplitV1 for item in self.splits):
            raise DirectSynthesisInvariantViolation("predicate tree nested type substitution")
        if tuple(sorted(self.selected_state_features)) != self.selected_state_features:
            raise DirectSynthesisInvariantViolation("state feature subset must be sorted")
        if any(type(name) is not str or name not in STATE_FEATURE_SEMANTICS for name in self.selected_state_features):
            raise DirectSynthesisInvariantViolation("predicate tree state feature substitution")
        _full_sha(self.partition_id, "predicate tree partition ID")
        _integer(self.cell_count, "predicate tree cell count", 1)
        _integer(self.active_cell_count, "predicate tree active cell count", 1)
        if tuple(item.sequence for item in self.splits) != tuple(range(1, len(self.splits) + 1)):
            raise DirectSynthesisInvariantViolation("predicate split sequence is not contiguous")

    def _payload(self) -> dict[str, Any]:
        return {
            "selected_state_features": list(self.selected_state_features),
            "generated_atoms": [item.to_document() for item in self.generated_atoms],
            "splits": [item.to_document() for item in self.splits],
            "partition_id": self.partition_id,
            "cell_count": self.cell_count,
            "active_cell_count": self.active_cell_count,
        }

    @property
    def tree_id(self) -> str:
        return _content_id(TREE_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "tree_id": self.tree_id}

    @classmethod
    def from_document(cls, document: Any) -> "DirectPredicateTreeV1":
        keys = {
            "selected_state_features", "generated_atoms", "splits", "partition_id",
            "cell_count", "active_cell_count", "tree_id",
        }
        record = _exact(document, keys, "direct predicate tree")
        if type(record["selected_state_features"]) is not list or type(record["generated_atoms"]) is not list or type(record["splits"]) is not list:
            raise DirectSynthesisInvariantViolation("predicate tree arrays must be lists")
        result = cls(
            tuple(record["selected_state_features"]),
            tuple(DirectPredicateAtomV1.from_document(item) for item in record["generated_atoms"]),
            tuple(DirectPredicateSplitV1.from_document(item) for item in record["splits"]),
            record["partition_id"], record["cell_count"], record["active_cell_count"],
        )
        if record["tree_id"] != result.tree_id or record != result.to_document():
            raise DirectSynthesisInvariantViolation("predicate tree ID/document mismatch")
        return result


@dataclass(frozen=True, order=True, slots=True)
class DirectSemanticActionLabelV1:
    features: tuple[tuple[str, Fraction], ...]

    def __post_init__(self) -> None:
        if type(self.features) is not tuple or any(
            type(item) is not tuple or len(item) != 2 or type(item[0]) is not str or type(item[1]) is not Fraction
            for item in self.features
        ):
            raise DirectSynthesisInvariantViolation("semantic label requires exact tuple/Fraction pairs")
        if tuple(sorted(self.features)) != self.features:
            raise DirectSynthesisInvariantViolation("semantic action features must be sorted")
        if len({name for name, _ in self.features}) != len(self.features):
            raise DirectSynthesisInvariantViolation("semantic action features must be unique")
        if any(name not in ACTION_FEATURE_SEMANTICS for name, _ in self.features):
            raise DirectSynthesisInvariantViolation("semantic action feature substitution")

    def _payload(self) -> dict[str, Any]:
        return {
            "features": [
                {"name": name, "value": _fraction_doc(value)}
                for name, value in self.features
            ]
        }

    @property
    def label_id(self) -> str:
        return _content_id(LABEL_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "label_id": self.label_id}

    @classmethod
    def from_document(cls, document: Any) -> "DirectSemanticActionLabelV1":
        record = _exact(document, {"features", "label_id"}, "direct semantic label")
        if type(record["features"]) is not list:
            raise DirectSynthesisInvariantViolation("semantic label features must be a list")
        values: list[tuple[str, Fraction]] = []
        for item in record["features"]:
            feature = _exact(item, {"name", "value"}, "semantic label feature")
            values.append((feature["name"], _fraction(feature["value"], "semantic label value")))
        result = cls(tuple(values))
        if record["label_id"] != result.label_id or record != result.to_document():
            raise DirectSynthesisInvariantViolation("semantic label ID/document mismatch")
        return result


@dataclass(frozen=True, slots=True)
class DirectActionSemanticAdapterV1:
    selected_action_features: tuple[str, ...]

    def __post_init__(self) -> None:
        if type(self.selected_action_features) is not tuple or any(type(name) is not str for name in self.selected_action_features):
            raise DirectSynthesisInvariantViolation("adapter feature names require exact tuple/text")
        if tuple(sorted(self.selected_action_features)) != self.selected_action_features:
            raise DirectSynthesisInvariantViolation("action feature subset must be sorted")
        if any(name not in ACTION_FEATURE_SEMANTICS for name in self.selected_action_features):
            raise DirectSynthesisInvariantViolation("semantic adapter uses unknown action feature")

    def label(
        self,
        kernel: LMBKernel,
        state: LMBState,
        action: LMBAction,
    ) -> DirectSemanticActionLabelV1:
        values = _action_feature_values(kernel, state, action)
        return DirectSemanticActionLabelV1(
            tuple((name, values[name]) for name in self.selected_action_features)
        )

    def labels(
        self,
        kernel: LMBKernel,
        state: LMBState,
    ) -> tuple[DirectSemanticActionLabelV1, ...]:
        return tuple(sorted({self.label(kernel, state, action) for action in kernel.actions(state)}))

    def concretize(
        self,
        kernel: LMBKernel,
        state: LMBState,
        label: DirectSemanticActionLabelV1,
    ) -> tuple[tuple[Fraction, LMBAction], ...]:
        actions = tuple(
            sorted(
                {
                    action
                    for action in kernel.actions(state)
                    if self.label(kernel, state, action) == label
                }
            )
        )
        if not actions:
            raise DirectSynthesisInvariantViolation("semantic label is unavailable")
        probability = Fraction(1, len(actions))
        return tuple((probability, action) for action in actions)


@dataclass(frozen=True, order=True, slots=True)
class DirectOneStepSignatureV1:
    reward_features: tuple[tuple[str, Fraction], ...]
    failure_probability: Fraction
    termination_probability: Fraction
    successor_probabilities: tuple[tuple[str, Fraction], ...]

    def __post_init__(self) -> None:
        if type(self.reward_features) is not tuple or type(self.successor_probabilities) is not tuple:
            raise DirectSynthesisInvariantViolation("one-step signature fields require tuples")
        if type(self.failure_probability) is not Fraction or type(self.termination_probability) is not Fraction:
            raise DirectSynthesisInvariantViolation("signature probabilities require exact Fractions")
        if any(type(item) is not tuple or len(item) != 2 or type(item[0]) is not str or type(item[1]) is not Fraction for item in self.reward_features + self.successor_probabilities):
            raise DirectSynthesisInvariantViolation("signature entries require exact text/Fraction pairs")

    def _payload(self) -> dict[str, Any]:
        return {
            "reward_features": [
                {"name": name, "value": _fraction_doc(value)}
                for name, value in self.reward_features
            ],
            "failure_probability": _fraction_doc(self.failure_probability),
            "termination_probability": _fraction_doc(self.termination_probability),
            "successor_probabilities": [
                {"cell_id": cell, "probability": _fraction_doc(value)}
                for cell, value in self.successor_probabilities
            ],
        }

    @property
    def signature_id(self) -> str:
        return _content_id(SIGNATURE_DOMAIN, self._payload())


@dataclass(frozen=True, slots=True)
class DirectHomomorphismWitnessV1:
    witness_kind: str
    partition_id: str
    selected_state_features: tuple[str, ...]
    selected_action_features: tuple[str, ...]
    state_ids: tuple[str, ...]
    action_ids: tuple[str, ...]
    semantic_label_ids: tuple[str, ...]
    signature_ids: tuple[str, ...]
    detail: str

    def __post_init__(self) -> None:
        allowed = {
            "LABEL_SET_MISMATCH",
            "WITHIN_STATE_ACTION_ALIAS",
            "CROSS_STATE_LABEL_DYNAMICS_MISMATCH",
            "CANDIDATE_CAP_INSUFFICIENT",
        }
        if self.witness_kind not in allowed:
            raise DirectSynthesisInvariantViolation("unknown direct witness kind")
        if tuple(sorted(self.selected_state_features)) != self.selected_state_features:
            raise DirectSynthesisInvariantViolation("witness state features are not sorted")
        if tuple(sorted(self.selected_action_features)) != self.selected_action_features:
            raise DirectSynthesisInvariantViolation("witness action features are not sorted")
        _full_sha(self.partition_id, "witness partition ID")
        _text(self.detail, "witness detail")
        for name in (
            "selected_state_features", "selected_action_features", "state_ids",
            "action_ids", "semantic_label_ids", "signature_ids",
        ):
            value = getattr(self, name)
            if type(value) is not tuple or any(type(item) is not str for item in value):
                raise DirectSynthesisInvariantViolation(f"witness {name} requires exact tuple/text")

    def _payload(self) -> dict[str, Any]:
        return {
            "witness_kind": self.witness_kind,
            "partition_id": self.partition_id,
            "selected_state_features": list(self.selected_state_features),
            "selected_action_features": list(self.selected_action_features),
            "state_ids": list(self.state_ids),
            "action_ids": list(self.action_ids),
            "semantic_label_ids": list(self.semantic_label_ids),
            "signature_ids": list(self.signature_ids),
            "detail": self.detail,
        }

    @property
    def witness_id(self) -> str:
        return _content_id(WITNESS_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "witness_id": self.witness_id}

    @classmethod
    def from_document(cls, document: Any) -> "DirectHomomorphismWitnessV1":
        keys = {
            "witness_kind", "partition_id", "selected_state_features",
            "selected_action_features", "state_ids", "action_ids",
            "semantic_label_ids", "signature_ids", "detail", "witness_id",
        }
        record = _exact(document, keys, "direct witness")
        for name in (
            "selected_state_features", "selected_action_features", "state_ids",
            "action_ids", "semantic_label_ids", "signature_ids",
        ):
            if type(record[name]) is not list:
                raise DirectSynthesisInvariantViolation(f"direct witness {name} must be a list")
        result = cls(
            record["witness_kind"], record["partition_id"],
            tuple(record["selected_state_features"]),
            tuple(record["selected_action_features"]), tuple(record["state_ids"]),
            tuple(record["action_ids"]), tuple(record["semantic_label_ids"]),
            tuple(record["signature_ids"]), record["detail"],
        )
        if record["witness_id"] != result.witness_id:
            raise DirectSynthesisInvariantViolation("direct witness ID mismatch")
        if record != result.to_document():
            raise DirectSynthesisInvariantViolation("direct witness document is noncanonical")
        return result


@dataclass(frozen=True, slots=True)
class DirectHomomorphismCandidateV1:
    selected_state_features: tuple[str, ...]
    selected_action_features: tuple[str, ...]
    predicate_tree_id: str
    partition_id: str
    cell_count: int
    active_cell_count: int
    split_count: int
    abstract_entry_count: int | None
    exact_homomorphism: bool
    witness_id: str | None

    def __post_init__(self) -> None:
        if type(self.selected_state_features) is not tuple or type(self.selected_action_features) is not tuple:
            raise DirectSynthesisInvariantViolation("candidate feature subsets require tuple types")
        if any(type(name) is not str for name in self.selected_state_features + self.selected_action_features):
            raise DirectSynthesisInvariantViolation("candidate feature names require text")
        for name in ("cell_count", "active_cell_count", "split_count"):
            _integer(getattr(self, name), name, 0 if name == "split_count" else 1)
        if self.abstract_entry_count is not None:
            _integer(self.abstract_entry_count, "abstract entry count", 1)
        if type(self.exact_homomorphism) is not bool:
            raise DirectSynthesisInvariantViolation("candidate exact flag must be boolean")
        _full_sha(self.predicate_tree_id, "candidate predicate tree ID")
        _full_sha(self.partition_id, "candidate partition ID")
        if self.witness_id is not None:
            _full_sha(self.witness_id, "candidate witness ID")
        if self.exact_homomorphism != (self.witness_id is None):
            raise DirectSynthesisInvariantViolation("candidate exact/witness relation is invalid")
        if self.exact_homomorphism != (self.abstract_entry_count is not None):
            raise DirectSynthesisInvariantViolation("candidate exact/entry relation is invalid")

    def _payload(self) -> dict[str, Any]:
        return {
            "selected_state_features": list(self.selected_state_features),
            "selected_action_features": list(self.selected_action_features),
            "predicate_tree_id": self.predicate_tree_id,
            "partition_id": self.partition_id,
            "cell_count": self.cell_count,
            "active_cell_count": self.active_cell_count,
            "split_count": self.split_count,
            "abstract_entry_count": self.abstract_entry_count,
            "exact_homomorphism": self.exact_homomorphism,
            "witness_id": self.witness_id,
        }

    @property
    def candidate_id(self) -> str:
        return _content_id(CANDIDATE_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "candidate_id": self.candidate_id}

    @classmethod
    def from_document(cls, document: Any) -> "DirectHomomorphismCandidateV1":
        keys = {
            "selected_state_features", "selected_action_features", "predicate_tree_id",
            "partition_id", "cell_count", "active_cell_count", "split_count",
            "abstract_entry_count", "exact_homomorphism", "witness_id", "candidate_id",
        }
        record = _exact(document, keys, "direct candidate")
        if type(record["selected_state_features"]) is not list or type(record["selected_action_features"]) is not list:
            raise DirectSynthesisInvariantViolation("candidate feature subsets must be lists")
        if type(record["exact_homomorphism"]) is not bool:
            raise DirectSynthesisInvariantViolation("candidate exact_homomorphism must be boolean")
        result = cls(
            tuple(record["selected_state_features"]),
            tuple(record["selected_action_features"]), record["predicate_tree_id"],
            record["partition_id"], record["cell_count"], record["active_cell_count"],
            record["split_count"], record["abstract_entry_count"],
            record["exact_homomorphism"], record["witness_id"],
        )
        if record["candidate_id"] != result.candidate_id:
            raise DirectSynthesisInvariantViolation("direct candidate ID mismatch")
        if record != result.to_document():
            raise DirectSynthesisInvariantViolation("direct candidate document is noncanonical")
        return result


@dataclass(frozen=True, slots=True)
class DirectHomomorphismCandidateTraceV1:
    spec_id: str
    state_registry_id: str
    action_registry_id: str
    required_candidate_count: int
    evaluated_candidate_count: int
    candidates: tuple[DirectHomomorphismCandidateV1, ...]
    witnesses: tuple[DirectHomomorphismWitnessV1, ...]
    selected_candidate_id: str | None
    status: DirectSynthesisStatus
    schema: str = DIRECT_TRACE_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != DIRECT_TRACE_SCHEMA:
            raise DirectSynthesisInvariantViolation("invalid direct trace schema")
        _full_sha(self.spec_id, "trace spec ID")
        _full_sha(self.state_registry_id, "trace state registry ID")
        _full_sha(self.action_registry_id, "trace action registry ID")
        _integer(self.required_candidate_count, "required candidate count", 1)
        _integer(self.evaluated_candidate_count, "evaluated candidate count", 0)
        if type(self.candidates) is not tuple or any(
            type(item) is not DirectHomomorphismCandidateV1 for item in self.candidates
        ):
            raise DirectSynthesisInvariantViolation("trace candidates require exact tuple/types")
        if type(self.witnesses) is not tuple or any(
            type(item) is not DirectHomomorphismWitnessV1 for item in self.witnesses
        ):
            raise DirectSynthesisInvariantViolation("trace witnesses require exact tuple/types")
        if self.evaluated_candidate_count != len(self.candidates):
            raise DirectSynthesisInvariantViolation("trace evaluated count mismatch")
        candidate_ids = {item.candidate_id for item in self.candidates}
        witness_ids = {item.witness_id for item in self.witnesses}
        if len(candidate_ids) != len(self.candidates) or len(witness_ids) != len(self.witnesses):
            raise DirectSynthesisInvariantViolation("trace contains duplicate IDs")
        if any(item.witness_id not in witness_ids for item in self.candidates if item.witness_id):
            raise DirectSynthesisInvariantViolation("trace omits a candidate witness")
        if self.status is DirectSynthesisStatus.EXACT_DIRECT_HOMOMORPHISM:
            if self.evaluated_candidate_count != self.required_candidate_count:
                raise DirectSynthesisInvariantViolation("successful trace is incomplete")
            selected = tuple(item for item in self.candidates if item.candidate_id == self.selected_candidate_id)
            if len(selected) != 1 or not selected[0].exact_homomorphism:
                raise DirectSynthesisInvariantViolation("successful trace selected invalid candidate")
        elif self.status is DirectSynthesisStatus.RESTRICTED_CONTROL_EXACT_FOUND:
            if self.evaluated_candidate_count != self.required_candidate_count:
                raise DirectSynthesisInvariantViolation("restricted-control trace is incomplete")
            selected = tuple(item for item in self.candidates if item.candidate_id == self.selected_candidate_id)
            if len(selected) != 1 or not selected[0].exact_homomorphism:
                raise DirectSynthesisInvariantViolation("restricted control did not bind its exact candidate")
        elif self.status is DirectSynthesisStatus.NO_EXACT_DIRECT_HOMOMORPHISM:
            if self.selected_candidate_id is not None or self.evaluated_candidate_count != self.required_candidate_count:
                raise DirectSynthesisInvariantViolation("negative trace is incomplete or selected")
            if any(item.exact_homomorphism for item in self.candidates):
                raise DirectSynthesisInvariantViolation("negative trace contains an exact candidate")
        else:
            if self.selected_candidate_id is not None or self.evaluated_candidate_count != 0:
                raise DirectSynthesisInvariantViolation("cap trace must stop before enumeration")
            if len(self.witnesses) != 1 or self.witnesses[0].witness_kind != "CANDIDATE_CAP_INSUFFICIENT":
                raise DirectSynthesisInvariantViolation("cap trace requires typed cap witness")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "spec_id": self.spec_id,
            "state_registry_id": self.state_registry_id,
            "action_registry_id": self.action_registry_id,
            "required_candidate_count": self.required_candidate_count,
            "evaluated_candidate_count": self.evaluated_candidate_count,
            "candidates": [item.to_document() for item in self.candidates],
            "witnesses": [item.to_document() for item in self.witnesses],
            "selected_candidate_id": self.selected_candidate_id,
            "status": self.status.value,
        }

    @property
    def trace_id(self) -> str:
        return _content_id(TRACE_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "trace_id": self.trace_id}

    @classmethod
    def from_document(cls, document: Any) -> "DirectHomomorphismCandidateTraceV1":
        keys = {
            "schema", "spec_id", "state_registry_id", "action_registry_id",
            "required_candidate_count", "evaluated_candidate_count", "candidates",
            "witnesses", "selected_candidate_id", "status", "trace_id",
        }
        record = _exact(document, keys, "direct candidate trace")
        if type(record["candidates"]) is not list or type(record["witnesses"]) is not list:
            raise DirectSynthesisInvariantViolation("trace candidates/witnesses must be lists")
        result = cls(
            record["spec_id"], record["state_registry_id"], record["action_registry_id"],
            record["required_candidate_count"], record["evaluated_candidate_count"],
            tuple(DirectHomomorphismCandidateV1.from_document(item) for item in record["candidates"]),
            tuple(DirectHomomorphismWitnessV1.from_document(item) for item in record["witnesses"]),
            record["selected_candidate_id"], DirectSynthesisStatus(record["status"]),
            record["schema"],
        )
        if record["trace_id"] != result.trace_id:
            raise DirectSynthesisInvariantViolation("direct trace ID mismatch")
        if record != result.to_document():
            raise DirectSynthesisInvariantViolation("direct trace document is noncanonical")
        return result


@dataclass(frozen=True, slots=True)
class DirectHomomorphismCertificateV1:
    structural_id: str
    training_coverage_id: str
    state_registry_id: str
    action_registry_id: str
    spec_id: str
    trace_id: str
    selected_candidate_id: str
    predicate_tree_id: str
    partition_id: str
    portable_model_id: str
    selected_state_features: tuple[str, ...]
    selected_action_features: tuple[str, ...]
    state_thresholds: tuple[Fraction, ...]
    ground_state_count: int
    active_ground_state_count: int
    quotient_cell_count: int
    active_quotient_cell_count: int
    abstract_entry_count: int
    envelope_is_singleton: bool
    action_alias_checked_before_mixture: bool = True
    execution_profile: str = "production_full_grammar_v1"
    claim_kind: str = "DIRECT_EXACT_HOMOMORPHISM_INSIDE_FIXED_GRAMMAR"
    claim_scope: str = CLAIM_SCOPE
    official_execution_allowed: bool = False
    official_scalar_cost: None = None
    official_N_break_even: None = None
    workload_economics_gate: str = WORKLOAD_GATE
    counter_completeness_gate: str = COUNTER_GATE
    schema: str = DIRECT_CERTIFICATE_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != DIRECT_CERTIFICATE_SCHEMA:
            raise DirectSynthesisInvariantViolation("invalid direct certificate schema")
        if self.claim_scope != CLAIM_SCOPE:
            raise DirectSynthesisInvariantViolation("direct certificate claim substitution")
        if self.execution_profile != "production_full_grammar_v1" or self.claim_kind != "DIRECT_EXACT_HOMOMORPHISM_INSIDE_FIXED_GRAMMAR":
            raise DirectSynthesisInvariantViolation("certificate profile/claim-kind substitution")
        if self.official_execution_allowed is not False or self.official_scalar_cost is not None or self.official_N_break_even is not None:
            raise DirectSynthesisInvariantViolation("official economics fields must remain locked")
        if self.workload_economics_gate != WORKLOAD_GATE or self.counter_completeness_gate != COUNTER_GATE:
            raise DirectSynthesisInvariantViolation("direct certificate Gate substitution")
        if self.envelope_is_singleton is not True or self.action_alias_checked_before_mixture is not True:
            raise DirectSynthesisInvariantViolation("direct exact obligations are not fully certified")
        if not self.selected_state_features or not self.selected_action_features:
            raise DirectSynthesisInvariantViolation("direct certificate requires state and action features")
        if type(self.selected_state_features) is not tuple or type(self.selected_action_features) is not tuple or type(self.state_thresholds) is not tuple:
            raise DirectSynthesisInvariantViolation("certificate feature fields require tuple types")
        if any(type(item) is not Fraction for item in self.state_thresholds):
            raise DirectSynthesisInvariantViolation("certificate thresholds require exact Fractions")
        if tuple(sorted(self.selected_state_features)) != self.selected_state_features or tuple(sorted(self.selected_action_features)) != self.selected_action_features:
            raise DirectSynthesisInvariantViolation("certificate feature names are not sorted")
        for name in (
            "structural_id", "training_coverage_id", "state_registry_id", "action_registry_id",
            "spec_id", "trace_id", "selected_candidate_id", "predicate_tree_id", "partition_id",
        ):
            _full_sha(getattr(self, name), name)
        if type(self.portable_model_id) is not str or not self.portable_model_id.startswith("rapm:") or len(self.portable_model_id) != 69:
            raise DirectSynthesisInvariantViolation("invalid portable model ID")
        for name in (
            "ground_state_count", "active_ground_state_count", "quotient_cell_count",
            "active_quotient_cell_count", "abstract_entry_count",
        ):
            _integer(getattr(self, name), name, 1)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": self.schema, "structural_id": self.structural_id,
            "training_coverage_id": self.training_coverage_id,
            "state_registry_id": self.state_registry_id,
            "action_registry_id": self.action_registry_id, "spec_id": self.spec_id,
            "trace_id": self.trace_id, "selected_candidate_id": self.selected_candidate_id,
            "predicate_tree_id": self.predicate_tree_id, "partition_id": self.partition_id,
            "portable_model_id": self.portable_model_id,
            "selected_state_features": list(self.selected_state_features),
            "selected_action_features": list(self.selected_action_features),
            "state_thresholds": [_fraction_doc(item) for item in self.state_thresholds],
            "ground_state_count": self.ground_state_count,
            "active_ground_state_count": self.active_ground_state_count,
            "quotient_cell_count": self.quotient_cell_count,
            "active_quotient_cell_count": self.active_quotient_cell_count,
            "abstract_entry_count": self.abstract_entry_count,
            "envelope_is_singleton": self.envelope_is_singleton,
            "action_alias_checked_before_mixture": self.action_alias_checked_before_mixture,
            "execution_profile": self.execution_profile,
            "claim_kind": self.claim_kind,
            "claim_scope": self.claim_scope,
            "official_execution_allowed": self.official_execution_allowed,
            "official_scalar_cost": self.official_scalar_cost,
            "official_N_break_even": self.official_N_break_even,
            "workload_economics_gate": self.workload_economics_gate,
            "counter_completeness_gate": self.counter_completeness_gate,
        }

    @property
    def certificate_id(self) -> str:
        return _content_id(CERTIFICATE_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "certificate_id": self.certificate_id}

    @classmethod
    def from_document(cls, document: Any) -> "DirectHomomorphismCertificateV1":
        keys = set(cls.__dataclass_fields__) | {"certificate_id"}
        record = _exact(document, keys, "direct certificate")
        if type(record["selected_state_features"]) is not list or type(record["selected_action_features"]) is not list or type(record["state_thresholds"]) is not list:
            raise DirectSynthesisInvariantViolation("certificate feature/threshold fields must be lists")
        kwargs = {name: record[name] for name in cls.__dataclass_fields__}
        kwargs["selected_state_features"] = tuple(kwargs["selected_state_features"])
        kwargs["selected_action_features"] = tuple(kwargs["selected_action_features"])
        kwargs["state_thresholds"] = tuple(_fraction(item, "state threshold") for item in kwargs["state_thresholds"])
        result = cls(**kwargs)
        if record["certificate_id"] != result.certificate_id:
            raise DirectSynthesisInvariantViolation("direct certificate ID mismatch")
        if record != result.to_document():
            raise DirectSynthesisInvariantViolation("direct certificate document is noncanonical")
        return result


@dataclass(frozen=True, slots=True)
class DirectHomomorphismSynthesisResultV1:
    status: DirectSynthesisStatus
    state_registry: DirectStateFeatureRegistryV1
    action_registry: DirectActionFeatureRegistryV1
    spec: DirectHomomorphismSynthesisSpecV1
    trace: DirectHomomorphismCandidateTraceV1
    predicate_tree: DirectPredicateTreeV1 | None
    partition: Partition | None
    semantic_adapter: DirectActionSemanticAdapterV1 | None
    quotient_models: QuotientModels | None
    portable_build: PortableBuildResult | None
    certificate: DirectHomomorphismCertificateV1 | None

    def __post_init__(self) -> None:
        exact_types = (
            (self.status, DirectSynthesisStatus, "status"),
            (self.state_registry, DirectStateFeatureRegistryV1, "state_registry"),
            (self.action_registry, DirectActionFeatureRegistryV1, "action_registry"),
            (self.spec, DirectHomomorphismSynthesisSpecV1, "spec"),
            (self.trace, DirectHomomorphismCandidateTraceV1, "trace"),
        )
        for value, expected, label in exact_types:
            if type(value) is not expected:
                raise DirectSynthesisInvariantViolation(
                    f"result {label} must have exact type {expected.__name__}"
                )
        optional_types = (
            (self.predicate_tree, DirectPredicateTreeV1, "predicate_tree"),
            (self.partition, Partition, "partition"),
            (self.semantic_adapter, DirectActionSemanticAdapterV1, "semantic_adapter"),
            (self.quotient_models, QuotientModels, "quotient_models"),
            (self.portable_build, PortableBuildResult, "portable_build"),
            (self.certificate, DirectHomomorphismCertificateV1, "certificate"),
        )
        for value, expected, label in optional_types:
            if value is not None and type(value) is not expected:
                raise DirectSynthesisInvariantViolation(
                    f"result {label} must have exact type {expected.__name__}"
                )
        published = (
            self.predicate_tree,
            self.partition,
            self.semantic_adapter,
            self.quotient_models,
            self.portable_build,
            self.certificate,
        )
        if self.status is DirectSynthesisStatus.EXACT_DIRECT_HOMOMORPHISM:
            if any(item is None for item in published):
                raise DirectSynthesisInvariantViolation("exact direct result is incomplete")
        elif any(item is not None for item in published):
            raise DirectSynthesisInvariantViolation("negative direct result published a model")
        _validate_result_graph(self)
        if (
            self.spec.state_registry_id != self.state_registry.registry_id
            or self.spec.action_registry_id != self.action_registry.registry_id
            or self.trace.spec_id != self.spec.spec_id
            or self.trace.state_registry_id != self.state_registry.registry_id
            or self.trace.action_registry_id != self.action_registry.registry_id
            or self.trace.status is not self.status
        ):
            raise DirectSynthesisInvariantViolation("result authority chain mismatch")
        if self.certificate is not None:
            certificate = self.certificate
            if (
                certificate.spec_id != self.spec.spec_id
                or certificate.trace_id != self.trace.trace_id
                or certificate.state_registry_id != self.state_registry.registry_id
                or certificate.action_registry_id != self.action_registry.registry_id
                or certificate.predicate_tree_id != self.predicate_tree.tree_id
                or certificate.partition_id != _partition_id(self.partition)
                or certificate.portable_model_id != self.portable_build.model.model_id
            ):
                raise DirectSynthesisInvariantViolation("certificate authority chain mismatch")


def _validate_partition_graph(partition: Partition) -> None:
    if type(partition) is not Partition or type(partition.assignments) is not tuple:
        raise DirectSynthesisInvariantViolation("partition requires exact type/assignment tuple")
    for assignment in partition.assignments:
        if type(assignment) is not tuple or len(assignment) != 2:
            raise DirectSynthesisInvariantViolation("partition assignment is not an exact pair")
        state, cell = assignment
        if type(state) is not LMBState or type(cell) is not str:
            raise DirectSynthesisInvariantViolation("partition assignment member types are invalid")


def _validate_quotient_graph(models: QuotientModels) -> None:
    if type(models) is not QuotientModels:
        raise DirectSynthesisInvariantViolation("quotient models require exact outer type")
    if type(models.nominal) is not NominalQuotient or type(models.envelope) is not ExactRealizationEnvelope:
        raise DirectSynthesisInvariantViolation("quotient nominal/envelope require exact types")
    if type(models.nominal.horizon) is not int or type(models.envelope.horizon) is not int:
        raise DirectSynthesisInvariantViolation("quotient horizons require exact integers")
    _validate_partition_graph(models.nominal.partition)
    _validate_partition_graph(models.envelope.partition)
    if type(models.nominal.entries) is not tuple or type(models.envelope.entries) is not tuple:
        raise DirectSynthesisInvariantViolation("quotient entries require tuple types")
    for entry in models.nominal.entries:
        if type(entry) is not NominalEntry or type(entry.model) is not NominalActionModel:
            raise DirectSynthesisInvariantViolation("nominal entry/model type substitution")
        if type(entry.action) is not DirectSemanticActionLabelV1 or type(entry.cell) is not str:
            raise DirectSynthesisInvariantViolation("nominal cell/action type substitution")
        entry.action.__post_init__()
        model = entry.model
        if type(model.reward_features) is not tuple or type(model.successor_probabilities) is not tuple:
            raise DirectSynthesisInvariantViolation("nominal model tuple substitution")
        if any(
            type(row) is not tuple
            or len(row) != 2
            or type(row[0]) is not str
            or type(row[1]) is not Fraction
            for row in model.reward_features
        ) or any(
            type(row) is not tuple
            or len(row) != 2
            or type(row[0]) is not str
            or type(row[1]) is not Fraction
            for row in model.successor_probabilities
        ):
            raise DirectSynthesisInvariantViolation("nominal model vector type substitution")
        if type(model.failure_probability) is not Fraction or type(model.termination_probability) is not Fraction or type(model.realization_count) is not int:
            raise DirectSynthesisInvariantViolation("nominal model scalar type substitution")
    for entry in models.envelope.entries:
        if type(entry) is not EnvelopeEntry or type(entry.action) is not DirectSemanticActionLabelV1 or type(entry.cell) is not str:
            raise DirectSynthesisInvariantViolation("envelope entry type substitution")
        if type(entry.realizations) is not tuple or any(
            type(item) is not GroundRealization for item in entry.realizations
        ):
            raise DirectSynthesisInvariantViolation("ground realization type substitution")
        entry.action.__post_init__()
        for realization in entry.realizations:
            if type(realization.state) is not LMBState or type(realization.reward_features) is not tuple or type(realization.successor_probabilities) is not tuple:
                raise DirectSynthesisInvariantViolation("ground realization member type substitution")
            if any(
                type(row) is not tuple
                or len(row) != 2
                or type(row[0]) is not str
                or type(row[1]) is not Fraction
                for row in realization.reward_features
            ) or any(
                type(row) is not tuple
                or len(row) != 2
                or type(row[0]) is not str
                or type(row[1]) is not Fraction
                for row in realization.successor_probabilities
            ):
                raise DirectSynthesisInvariantViolation("ground realization vector type substitution")
            if type(realization.failure_probability) is not Fraction or type(realization.termination_probability) is not Fraction:
                raise DirectSynthesisInvariantViolation("ground realization probability type substitution")


def _validate_portable_graph(portable: PortableBuildResult) -> None:
    if type(portable) is not PortableBuildResult or type(portable.model) is not PortableRAPM or type(portable.registry) is not PortableRegistry:
        raise DirectSynthesisInvariantViolation("portable build/model/registry type substitution")
    if type(portable.model._canonical_document) is not str:
        raise DirectSynthesisInvariantViolation("portable model transport is not canonical text")
    registry = portable.registry
    registry_shapes = (
        ("state_records", 2, (LMBState, str)),
        ("cell_records", 2, (str, str)),
        (
            "semantic_action_records",
            3,
            (str, DirectSemanticActionLabelV1, str),
        ),
        ("ground_action_records", 3, (LMBState, LMBAction, str)),
    )
    for name, width, expected_types in registry_shapes:
        records = getattr(registry, name)
        if type(records) is not tuple:
            raise DirectSynthesisInvariantViolation(f"portable registry {name} type substitution")
        for row in records:
            if type(row) is not tuple or len(row) != width:
                raise DirectSynthesisInvariantViolation(f"portable registry {name} row substitution")
            if any(type(value) is not expected for value, expected in zip(row, expected_types)):
                raise DirectSynthesisInvariantViolation(f"portable registry {name} value substitution")


def _validate_result_graph(result: DirectHomomorphismSynthesisResultV1) -> None:
    result.state_registry.__post_init__()
    result.action_registry.__post_init__()
    result.spec.__post_init__()
    result.trace.__post_init__()
    for candidate in result.trace.candidates:
        candidate.__post_init__()
    for witness in result.trace.witnesses:
        witness.__post_init__()
    if type(result.trace.candidates) is not tuple or type(result.trace.witnesses) is not tuple:
        raise DirectSynthesisInvariantViolation("result trace graph is not exact")
    if result.predicate_tree is not None:
        tree = result.predicate_tree
        if type(tree.generated_atoms) is not tuple or any(type(item) is not DirectPredicateAtomV1 for item in tree.generated_atoms):
            raise DirectSynthesisInvariantViolation("predicate atoms type substitution")
        if type(tree.splits) is not tuple or any(type(item) is not DirectPredicateSplitV1 or type(item.atom) is not DirectPredicateAtomV1 for item in tree.splits):
            raise DirectSynthesisInvariantViolation("predicate split type substitution")
        tree.__post_init__()
        for atom in tree.generated_atoms:
            atom.__post_init__()
        for split in tree.splits:
            split.__post_init__()
    if result.partition is not None:
        _validate_partition_graph(result.partition)
    if result.semantic_adapter is not None and type(result.semantic_adapter.selected_action_features) is not tuple:
        raise DirectSynthesisInvariantViolation("semantic adapter feature tuple substitution")
    if result.semantic_adapter is not None:
        result.semantic_adapter.__post_init__()
    if result.quotient_models is not None:
        _validate_quotient_graph(result.quotient_models)
    if result.portable_build is not None:
        _validate_portable_graph(result.portable_build)
    if result.certificate is not None:
        result.certificate.__post_init__()


def _partition_payload(partition: Partition) -> dict[str, Any]:
    blocks = [
        sorted(object_id(state, "state") for state in partition.members(cell))
        for cell in partition.cell_ids
    ]
    blocks.sort()
    return {"blocks": blocks}


def _partition_id(partition: Partition) -> str:
    return _content_id(PARTITION_DOMAIN, _partition_payload(partition))


def _base_partition(states: tuple[LMBState, ...]) -> Partition:
    mapping: dict[LMBState, str] = {}
    for state in states:
        kind = (
            "active"
            if state.status is LMBStatus.ACTIVE
            else "failure"
            if state.status is LMBStatus.FAILURE
            else "success"
        )
        mapping[state] = _content_id(CELL_DOMAIN, {"base_kind": kind})
    return Partition.from_mapping(mapping)


def _state_feature_rows(
    kernel: LMBKernel,
    states: tuple[LMBState, ...],
    registry: DirectStateFeatureRegistryV1,
) -> dict[LMBState, dict[str, Fraction]]:
    adapter = LMBSemanticAdapter()
    rows: dict[LMBState, dict[str, Fraction]] = {}
    for state in states:
        if state.status is not LMBStatus.ACTIVE:
            continue
        raw = {name: Fraction(value) for name, value in adapter.features(kernel, state)}
        if not set(registry.feature_names) <= set(raw):
            raise DirectSynthesisInvariantViolation("state feature implementation is incomplete")
        rows[state] = {name: raw[name] for name in registry.feature_names}
    return rows


def _compile_state_tree(
    states: tuple[LMBState, ...],
    rows: Mapping[LMBState, Mapping[str, Fraction]],
    selected: tuple[str, ...],
) -> tuple[DirectPredicateTreeV1, Partition]:
    partition = _base_partition(states)
    atoms: list[DirectPredicateAtomV1] = []
    for feature in selected:
        values = sorted({row[feature] for row in rows.values()})
        atoms.extend(
            DirectPredicateAtomV1(feature, (left + right) / 2)
            for left, right in zip(values, values[1:])
        )
    splits: list[DirectPredicateSplitV1] = []
    for atom in atoms:
        active_cells = tuple(
            cell
            for cell in partition.cell_ids
            if all(state.status is LMBStatus.ACTIVE for state in partition.members(cell))
        )
        for cell in active_cells:
            members = partition.members(cell)
            true_states = tuple(
                state for state in members if rows[state][atom.feature_name] <= atom.threshold
            )
            true_set = set(true_states)
            false_states = tuple(state for state in members if state not in true_set)
            if not true_states or not false_states:
                continue
            true_cell = _content_id(
                CELL_DOMAIN,
                {"parent": str(cell), "atom_id": atom.atom_id, "branch": "true"},
            )
            false_cell = _content_id(
                CELL_DOMAIN,
                {"parent": str(cell), "atom_id": atom.atom_id, "branch": "false"},
            )
            partition = partition.replace_cell(
                cell, false_states, true_states, false_cell, true_cell
            )
            splits.append(
                DirectPredicateSplitV1(
                    len(splits) + 1,
                    str(cell),
                    atom,
                    true_cell,
                    false_cell,
                    len(true_states),
                    len(false_states),
                )
            )
    active_cells = sum(
        all(state.status is LMBStatus.ACTIVE for state in partition.members(cell))
        for cell in partition.cell_ids
    )
    tree = DirectPredicateTreeV1(
        selected,
        tuple(atoms),
        tuple(splits),
        _partition_id(partition),
        len(partition.cell_ids),
        active_cells,
    )
    return tree, partition


def _outcomes(kernel: LMBKernel, state: LMBState, action: LMBAction) -> tuple[Any, ...]:
    raw = kernel.step(state, action)
    outcomes = (raw,) if hasattr(raw, "probability") else tuple(raw)
    if not outcomes or sum((Fraction(item.probability) for item in outcomes), Fraction(0)) != 1:
        raise DirectSynthesisInvariantViolation("kernel outcomes must have exact unit mass")
    return outcomes


def _ground_signature(
    kernel: LMBKernel,
    partition: Partition,
    state: LMBState,
    action: LMBAction,
) -> DirectOneStepSignatureV1:
    rewards: dict[str, Fraction] = {}
    successors: dict[str, Fraction] = {}
    failure = Fraction(0)
    termination = Fraction(0)
    for outcome in _outcomes(kernel, state, action):
        probability = Fraction(outcome.probability)
        raw_features = outcome.reward_features
        items = raw_features.items() if hasattr(raw_features, "items") else raw_features
        for name, value in items:
            rewards[str(name)] = rewards.get(str(name), Fraction(0)) + probability * Fraction(value)
        stopped = bool(outcome.failure or outcome.terminal or kernel.is_terminal(outcome.next_state))
        if outcome.failure:
            failure += probability
        if stopped:
            termination += probability
        else:
            cell = str(partition.cell_of(outcome.next_state))
            successors[cell] = successors.get(cell, Fraction(0)) + probability
    return DirectOneStepSignatureV1(
        tuple(sorted(rewards.items())),
        failure,
        termination,
        tuple(sorted(successors.items())),
    )


def _candidate_witness(
    kind: str,
    partition: Partition,
    state_features: tuple[str, ...],
    action_features: tuple[str, ...],
    states: Iterable[LMBState],
    actions: Iterable[LMBAction],
    labels: Iterable[DirectSemanticActionLabelV1],
    signatures: Iterable[DirectOneStepSignatureV1],
    detail: str,
) -> DirectHomomorphismWitnessV1:
    return DirectHomomorphismWitnessV1(
        kind,
        _partition_id(partition),
        state_features,
        action_features,
        tuple(object_id(state, "state") for state in states),
        tuple(object_id(action, "ground-action-source") for action in actions),
        tuple(label.label_id for label in labels),
        tuple(signature.signature_id for signature in signatures),
        detail,
    )


def _verify_candidate_obligations(
    kernel: LMBKernel,
    partition: Partition,
    state_features: tuple[str, ...],
    action_features: tuple[str, ...],
) -> tuple[int | None, DirectHomomorphismWitnessV1 | None]:
    adapter = DirectActionSemanticAdapterV1(action_features)
    entry_count = 0
    for cell in partition.cell_ids:
        active = tuple(
            state for state in partition.members(cell) if state.status is LMBStatus.ACTIVE
        )
        if not active:
            continue
        label_sets = {state: adapter.labels(kernel, state) for state in active}
        reference_state = active[0]
        for state in active[1:]:
            if label_sets[state] != label_sets[reference_state]:
                labels = tuple(sorted(set(label_sets[state]) ^ set(label_sets[reference_state])))
                return None, _candidate_witness(
                    "LABEL_SET_MISMATCH",
                    partition,
                    state_features,
                    action_features,
                    (reference_state, state),
                    (),
                    labels,
                    (),
                    "members of one state cell expose different semantic-label sets",
                )
        reference_signatures: dict[DirectSemanticActionLabelV1, DirectOneStepSignatureV1] = {}
        for state in active:
            for label in label_sets[state]:
                actions = tuple(action for action in kernel.actions(state) if adapter.label(kernel, state, action) == label)
                signatures = tuple(_ground_signature(kernel, partition, state, action) for action in actions)
                if len(set(signatures)) != 1:
                    left_index = next(
                        index
                        for index in range(1, len(signatures))
                        if signatures[index] != signatures[0]
                    )
                    return None, _candidate_witness(
                        "WITHIN_STATE_ACTION_ALIAS",
                        partition,
                        state_features,
                        action_features,
                        (state,),
                        (actions[0], actions[left_index]),
                        (label,),
                        (signatures[0], signatures[left_index]),
                        "ground actions were aliased before proving identical raw signatures",
                    )
                signature = signatures[0]
                if state is reference_state:
                    reference_signatures[label] = signature
                elif signature != reference_signatures[label]:
                    return None, _candidate_witness(
                        "CROSS_STATE_LABEL_DYNAMICS_MISMATCH",
                        partition,
                        state_features,
                        action_features,
                        (reference_state, state),
                        (),
                        (label,),
                        (reference_signatures[label], signature),
                        "same cell and semantic label have different one-step signatures",
                    )
        entry_count += len(label_sets[reference_state])
    return entry_count, None


def _subsets(names: tuple[str, ...]) -> tuple[tuple[str, ...], ...]:
    return tuple(
        subset
        for size in range(len(names) + 1)
        for subset in combinations(names, size)
    )


def _normalizer_rules(kernel: LMBKernel) -> tuple[dict[str, Any], ...]:
    match_cap = {
        "name": "match",
        "per_step_cap": fraction_to_json(Fraction(1)),
        "total_cap": fraction_to_json(Fraction(kernel.tile_count // 3)),
    }
    clear_cap = {
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
            "feature_caps": (match_cap, clear_cap),
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
            "feature_caps": (clear_cap,),
        },
    )


def _portable(
    kernel: LMBKernel,
    coverage: SuiteBuildCoverage[LMBState],
    models: QuotientModels,
) -> PortableBuildResult:
    return build_portable_rapm(
        models,
        state_ids=lambda state: object_id(state, "state"),
        semantic_action_ids=lambda action: object_id(action, "direct-semantic-action-source"),
        ground_action_ids=lambda action: object_id(action, "ground-action-source"),
        normalizer_rules=_normalizer_rules(kernel),
        state_kinds=lambda state: (
            "failure"
            if state.status is LMBStatus.FAILURE
            else "terminal"
            if state.status is not LMBStatus.ACTIVE
            else "active"
        ),
        goal_ids=tuple(kernel.registered_goals),
        coverage=_coverage_payload(coverage),
    )


def _singleton(models: QuotientModels) -> bool:
    return all(
        len(
            {
                (
                    item.reward_features,
                    item.failure_probability,
                    item.termination_probability,
                    item.successor_probabilities,
                )
                for item in entry.realizations
            }
        )
        == 1
        for entry in models.envelope.entries
    )


def _synthesize(
    kernel: LMBKernel,
    coverage: SuiteBuildCoverage[LMBState],
    state_registry: DirectStateFeatureRegistryV1,
    action_registry: DirectActionFeatureRegistryV1,
    spec: DirectHomomorphismSynthesisSpecV1,
) -> DirectHomomorphismSynthesisResultV1:
    _validate_feature_implementation_authority()
    if type(kernel) is not LMBKernel or type(coverage) is not SuiteBuildCoverage:
        raise DirectSynthesisInvariantViolation(
            "direct synthesis requires exact LMBKernel and SuiteBuildCoverage types"
        )
    if type(state_registry) is not DirectStateFeatureRegistryV1 or type(action_registry) is not DirectActionFeatureRegistryV1 or type(spec) is not DirectHomomorphismSynthesisSpecV1:
        raise DirectSynthesisInvariantViolation("direct construction authorities require exact types")
    canonical_state = direct_state_feature_registry_v1(state_registry.feature_names)
    canonical_action = direct_action_feature_registry_v1(action_registry.feature_names)
    if state_registry.to_document() != canonical_state.to_document() or action_registry.to_document() != canonical_action.to_document():
        raise DirectSynthesisInvariantViolation("direct feature registry is not canonical")
    if (
        spec.structural_id != _structural_id(kernel)
        or spec.training_coverage_id != _coverage_id(coverage)
        or spec.state_registry_id != state_registry.registry_id
        or spec.action_registry_id != action_registry.registry_id
    ):
        raise DirectSynthesisInvariantViolation("direct synthesis spec binding mismatch")
    if spec.execution_profile == "production_full_grammar_v1" and (
        state_registry.to_document() != direct_state_feature_registry_v1().to_document()
        or action_registry.to_document() != direct_action_feature_registry_v1().to_document()
    ):
        raise DirectSynthesisInvariantViolation(
            "production profile requires the complete canonical grammars"
        )
    states = _states(coverage.covered_states)
    if not states or any(type(state) is not LMBState for state in states):
        raise DirectSynthesisInvariantViolation("coverage has invalid LMB states")
    rows = _state_feature_rows(kernel, states, state_registry)
    state_subsets = _subsets(state_registry.feature_names)
    action_subsets = _subsets(action_registry.feature_names)
    required = len(state_subsets) * len(action_subsets)
    if required > spec.candidate_cap:
        not_evaluated = _content_id(PARTITION_DOMAIN, {"kind": "NOT_EVALUATED_CAP"})
        witness = DirectHomomorphismWitnessV1(
            "CANDIDATE_CAP_INSUFFICIENT",
            not_evaluated,
            (),
            (),
            (),
            (),
            (),
            (),
            f"required={required};cap={spec.candidate_cap}",
        )
        trace = DirectHomomorphismCandidateTraceV1(
            spec.spec_id,
            state_registry.registry_id,
            action_registry.registry_id,
            required,
            0,
            (),
            (witness,),
            None,
            DirectSynthesisStatus.CANDIDATE_CAP_EXHAUSTED,
        )
        return DirectHomomorphismSynthesisResultV1(
            DirectSynthesisStatus.CANDIDATE_CAP_EXHAUSTED,
            state_registry,
            action_registry,
            spec,
            trace,
            None,
            None,
            None,
            None,
            None,
            None,
        )

    candidates: list[DirectHomomorphismCandidateV1] = []
    witnesses: dict[str, DirectHomomorphismWitnessV1] = {}
    runtime: dict[str, tuple[DirectPredicateTreeV1, Partition, DirectActionSemanticAdapterV1]] = {}
    exact_candidates: list[DirectHomomorphismCandidateV1] = []
    for state_subset in state_subsets:
        tree, partition = _compile_state_tree(states, rows, state_subset)
        for action_subset in action_subsets:
            entry_count, witness = _verify_candidate_obligations(
                kernel, partition, state_subset, action_subset
            )
            if witness is not None:
                witnesses[witness.witness_id] = witness
            candidate = DirectHomomorphismCandidateV1(
                state_subset,
                action_subset,
                tree.tree_id,
                tree.partition_id,
                tree.cell_count,
                tree.active_cell_count,
                len(tree.splits),
                entry_count,
                witness is None,
                None if witness is None else witness.witness_id,
            )
            candidates.append(candidate)
            if witness is None:
                exact_candidates.append(candidate)
                runtime[candidate.candidate_id] = (
                    tree,
                    partition,
                    DirectActionSemanticAdapterV1(action_subset),
                )

    witness_tuple = tuple(sorted(witnesses.values(), key=lambda item: item.witness_id))
    if not exact_candidates:
        trace = DirectHomomorphismCandidateTraceV1(
            spec.spec_id,
            state_registry.registry_id,
            action_registry.registry_id,
            required,
            len(candidates),
            tuple(candidates),
            witness_tuple,
            None,
            DirectSynthesisStatus.NO_EXACT_DIRECT_HOMOMORPHISM,
        )
        return DirectHomomorphismSynthesisResultV1(
            DirectSynthesisStatus.NO_EXACT_DIRECT_HOMOMORPHISM,
            state_registry,
            action_registry,
            spec,
            trace,
            None,
            None,
            None,
            None,
            None,
            None,
        )

    selected = min(
        exact_candidates,
        key=lambda item: (
            len(item.selected_state_features),
            len(item.selected_action_features),
            item.split_count,
            item.selected_state_features,
            item.selected_action_features,
            item.partition_id,
        ),
    )
    tree, partition, adapter = runtime[selected.candidate_id]
    if spec.execution_profile == "restricted_negative_control_v1":
        trace = DirectHomomorphismCandidateTraceV1(
            spec.spec_id,
            state_registry.registry_id,
            action_registry.registry_id,
            required,
            len(candidates),
            tuple(candidates),
            witness_tuple,
            selected.candidate_id,
            DirectSynthesisStatus.RESTRICTED_CONTROL_EXACT_FOUND,
        )
        return DirectHomomorphismSynthesisResultV1(
            DirectSynthesisStatus.RESTRICTED_CONTROL_EXACT_FOUND,
            state_registry,
            action_registry,
            spec,
            trace,
            None,
            None,
            None,
            None,
            None,
            None,
        )
    trace = DirectHomomorphismCandidateTraceV1(
        spec.spec_id,
        state_registry.registry_id,
        action_registry.registry_id,
        required,
        len(candidates),
        tuple(candidates),
        witness_tuple,
        selected.candidate_id,
        DirectSynthesisStatus.EXACT_DIRECT_HOMOMORPHISM,
    )
    models = build_quotient_models(
        kernel,
        states,
        partition,
        semantic_adapter=adapter,
    )
    if not _singleton(models):
        raise DirectSynthesisInvariantViolation("verified direct homomorphism produced a non-singleton envelope")
    portable = _portable(kernel, coverage, models)
    certificate = DirectHomomorphismCertificateV1(
        spec.structural_id,
        spec.training_coverage_id,
        state_registry.registry_id,
        action_registry.registry_id,
        spec.spec_id,
        trace.trace_id,
        selected.candidate_id,
        tree.tree_id,
        tree.partition_id,
        portable.model.model_id,
        selected.selected_state_features,
        selected.selected_action_features,
        tuple(item.threshold for item in tree.generated_atoms),
        len(states),
        sum(state.status is LMBStatus.ACTIVE for state in states),
        len(partition.cell_ids),
        tree.active_cell_count,
        len(models.envelope.entries),
        True,
    )
    return DirectHomomorphismSynthesisResultV1(
        DirectSynthesisStatus.EXACT_DIRECT_HOMOMORPHISM,
        state_registry,
        action_registry,
        spec,
        trace,
        tree,
        partition,
        adapter,
        models,
        portable,
        certificate,
    )


def synthesize_direct_lmb_homomorphism_v1(
    kernel: LMBKernel,
    coverage: SuiteBuildCoverage[LMBState],
) -> DirectHomomorphismSynthesisResultV1:
    """Production V0-039 entry point with the complete frozen grammars."""

    if type(kernel) is not LMBKernel or type(coverage) is not SuiteBuildCoverage:
        raise DirectSynthesisInvariantViolation(
            "production API requires exact LMBKernel and SuiteBuildCoverage types"
        )
    state_registry = direct_state_feature_registry_v1()
    action_registry = direct_action_feature_registry_v1()
    return _synthesize(
        kernel,
        coverage,
        state_registry,
        action_registry,
        direct_synthesis_spec_v1(kernel, coverage, state_registry, action_registry),
    )


def run_direct_lmb_negative_control_v1(
    kernel: LMBKernel,
    coverage: SuiteBuildCoverage[LMBState],
    *,
    state_feature_names: tuple[str, ...],
    action_feature_names: tuple[str, ...],
    candidate_cap: int = 4096,
) -> DirectHomomorphismSynthesisResultV1:
    """Explicit non-production profile for restricted-grammar/cap controls."""

    if type(kernel) is not LMBKernel or type(coverage) is not SuiteBuildCoverage:
        raise DirectSynthesisInvariantViolation(
            "negative-control API requires exact LMBKernel and SuiteBuildCoverage types"
        )
    state_registry = direct_state_feature_registry_v1(state_feature_names)
    action_registry = direct_action_feature_registry_v1(action_feature_names)
    spec = _negative_control_spec_v1(
        kernel, coverage, state_registry, action_registry, candidate_cap
    )
    return _synthesize(kernel, coverage, state_registry, action_registry, spec)


def _verify_rebuild(
    kernel: LMBKernel,
    coverage: SuiteBuildCoverage[LMBState],
    result: DirectHomomorphismSynthesisResultV1,
    *,
    production: bool,
) -> tuple[str, ...]:
    if type(result) is not DirectHomomorphismSynthesisResultV1:
        raise DirectSynthesisInvariantViolation("verifier rejects nonexact result types")
    _validate_feature_implementation_authority()
    _validate_result_graph(result)
    expected = (
        synthesize_direct_lmb_homomorphism_v1(kernel, coverage)
        if production
        else _synthesize(kernel, coverage, result.state_registry, result.action_registry, result.spec)
    )
    failures: list[str] = []
    for code, left, right in (
        ("STATUS_MISMATCH", result.status, expected.status),
        ("STATE_REGISTRY_MISMATCH", result.state_registry.to_document(), expected.state_registry.to_document()),
        ("ACTION_REGISTRY_MISMATCH", result.action_registry.to_document(), expected.action_registry.to_document()),
        ("SPEC_MISMATCH", result.spec.to_document(), expected.spec.to_document()),
        ("TRACE_MISMATCH", result.trace.to_document(), expected.trace.to_document()),
        ("PREDICATE_TREE_MISMATCH", None if result.predicate_tree is None else result.predicate_tree.to_document(), None if expected.predicate_tree is None else expected.predicate_tree.to_document()),
        ("PARTITION_MISMATCH", result.partition, expected.partition),
        ("SEMANTIC_ADAPTER_MISMATCH", result.semantic_adapter, expected.semantic_adapter),
        ("QUOTIENT_MODELS_MISMATCH", result.quotient_models, expected.quotient_models),
        ("CERTIFICATE_MISMATCH", None if result.certificate is None else result.certificate.to_document(), None if expected.certificate is None else expected.certificate.to_document()),
        ("PORTABLE_MODEL_MISMATCH", None if result.portable_build is None else result.portable_build.model.to_dict(), None if expected.portable_build is None else expected.portable_build.model.to_dict()),
        ("PORTABLE_REGISTRY_MISMATCH", None if result.portable_build is None else result.portable_build.registry, None if expected.portable_build is None else expected.portable_build.registry),
    ):
        if left != right:
            failures.append(code)
    return tuple(failures)


def verify_direct_lmb_homomorphism_v1(
    kernel: LMBKernel,
    coverage: SuiteBuildCoverage[LMBState],
    result: DirectHomomorphismSynthesisResultV1,
) -> tuple[str, ...]:
    if type(result) is not DirectHomomorphismSynthesisResultV1:
        raise DirectSynthesisInvariantViolation("production verifier rejects duck results")
    if result.spec.execution_profile != "production_full_grammar_v1":
        raise DirectSynthesisInvariantViolation(
            "production verifier rejects restricted-control provenance"
        )
    if (
        result.state_registry.to_document() != direct_state_feature_registry_v1().to_document()
        or result.action_registry.to_document() != direct_action_feature_registry_v1().to_document()
    ):
        raise DirectSynthesisInvariantViolation(
            "production verifier requires complete canonical registries"
        )
    return _verify_rebuild(kernel, coverage, result, production=True)


def verify_direct_lmb_negative_control_v1(
    kernel: LMBKernel,
    coverage: SuiteBuildCoverage[LMBState],
    result: DirectHomomorphismSynthesisResultV1,
) -> tuple[str, ...]:
    if type(result) is not DirectHomomorphismSynthesisResultV1:
        raise DirectSynthesisInvariantViolation("negative-control verifier rejects duck results")
    if result.spec.execution_profile != "restricted_negative_control_v1":
        raise DirectSynthesisInvariantViolation(
            "negative-control verifier rejects production provenance"
        )
    return _verify_rebuild(kernel, coverage, result, production=False)


__all__ = [
    "DirectActionFeatureRegistryV1",
    "DirectActionSemanticAdapterV1",
    "DirectHomomorphismCandidateTraceV1",
    "DirectHomomorphismCertificateV1",
    "DirectHomomorphismSynthesisResultV1",
    "DirectHomomorphismSynthesisSpecV1",
    "DirectHomomorphismWitnessV1",
    "DirectSemanticActionLabelV1",
    "DirectStateFeatureRegistryV1",
    "DirectSynthesisInvariantViolation",
    "DirectSynthesisStatus",
    "direct_action_feature_registry_v1",
    "direct_state_feature_registry_v1",
    "run_direct_lmb_negative_control_v1",
    "synthesize_direct_lmb_homomorphism_v1",
    "verify_direct_lmb_homomorphism_v1",
    "verify_direct_lmb_negative_control_v1",
]
