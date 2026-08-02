"""Exact, fail-closed reconciliation for the eight derived K7 leaves.

The V6 registry has eight required ``derived_only`` leaves.  This module
freezes their equations, derives values only from independently replayed
semantic dependencies, and reports typed blockers for every missing family.
It emits no CounterRecord, WorkVector, ComparisonVector, or formal claim.

The current production child bundle is intentionally *not* a route-terminal
dependency: its public replay does not independently replay every partial
native chain node, and a typed status/hash is not a semantic outcome proof.
Route reconciliation remains blocked until one stronger authority binds the
full owner transcript to the production runtime's actual ``BUSINESS_RESULT``
bytes, SHA-256, and public-replay ID.  Solver-zero reconciliation requires an
exact replayed root-cap stage transcript.  Process exits are classified from
the already verified process-launch source and its direct PIDfd-reap journal.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from enum import Enum
from functools import lru_cache
import os
import signal
from typing import Any, Mapping, NoReturn

from acfqp import construction_accounting_partial_native_v1 as partial_v1
from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp import construction_shared_resource_semantic_replay_v2 as replay_v2
from acfqp import construction_shared_resource_verified_envelope_v1 as verified_v1
from acfqp import construction_shared_resource_working_process_evidence_v2 as working_v2
from acfqp.accounting_v1 import LaneEnum, ReducerEnum
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_RECONCILIATION_ARITHMETIC_REPLAY_V1_DOMAIN,
    CONSTRUCTION_K7_RECONCILIATION_BLOCKER_V1_DOMAIN,
    CONSTRUCTION_K7_RECONCILIATION_FORMULA_AUTHORITY_V1_DOMAIN,
    CONSTRUCTION_K7_RECONCILIATION_PATH_PROOF_V1_DOMAIN,
    CONSTRUCTION_K7_RECONCILIATION_READINESS_V1_DOMAIN,
    CONSTRUCTION_K7_RECONCILIATION_SEMANTIC_DEPENDENCY_V1_DOMAIN,
    content_id,
    loads_canonical_json,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.24"
PROFILE_KEY = "construction_k7_derived_reconciliation_v1"

FORMULA_AUTHORITY_V1_DOMAIN = (
    CONSTRUCTION_K7_RECONCILIATION_FORMULA_AUTHORITY_V1_DOMAIN
)
ARITHMETIC_REPLAY_V1_DOMAIN = (
    CONSTRUCTION_K7_RECONCILIATION_ARITHMETIC_REPLAY_V1_DOMAIN
)
SEMANTIC_DEPENDENCY_V1_DOMAIN = (
    CONSTRUCTION_K7_RECONCILIATION_SEMANTIC_DEPENDENCY_V1_DOMAIN
)
PATH_PROOF_V1_DOMAIN = CONSTRUCTION_K7_RECONCILIATION_PATH_PROOF_V1_DOMAIN
BLOCKER_V1_DOMAIN = CONSTRUCTION_K7_RECONCILIATION_BLOCKER_V1_DOMAIN
READINESS_V1_DOMAIN = CONSTRUCTION_K7_RECONCILIATION_READINESS_V1_DOMAIN
REQUESTED_PHASE3E_DOMAIN_TAGS = (
    FORMULA_AUTHORITY_V1_DOMAIN,
    ARITHMETIC_REPLAY_V1_DOMAIN,
    SEMANTIC_DEPENDENCY_V1_DOMAIN,
    PATH_PROOF_V1_DOMAIN,
    BLOCKER_V1_DOMAIN,
    READINESS_V1_DOMAIN,
)

DERIVED_PATHS = (
    "process.exit_failures",
    "process.exit_successes",
    "route.attempts",
    "route.failures",
    "route.successes",
    "solver.attempts",
    "solver.failures",
    "solver.successes",
)

_FORMULA_ISSUER = object()
_ARITHMETIC_ISSUER = object()
_DEPENDENCY_ISSUER = object()
_PROOF_ISSUER = object()
_BLOCKER_ISSUER = object()
_READINESS_ISSUER = object()


class ConstructionK7DerivedReconciliationV1Error(ValueError):
    """A formula, dependency, or K7 occurrence identity is invalid."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7DerivedReconciliationV1Error(message)


def _local_content_id(domain: str, payload: Mapping[str, Any]) -> str:
    if domain not in REQUESTED_PHASE3E_DOMAIN_TAGS:
        _fail("reconciliation used an unknown local domain")
    return content_id(domain, dict(payload))


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7DerivedReconciliationV1Error(
            f"{label} must be one exact content ID"
        ) from error


def _nonnegative(value: Any, label: str) -> int:
    if type(value) is not int or value < 0:
        _fail(f"{label} must be one nonnegative exact integer")
    return value


def _exact_values(values: Any, label: str) -> tuple[tuple[str, int], ...]:
    if (
        type(values) is not tuple
        or tuple(sorted(values)) != values
        or len({key for key, _value in values}) != len(values)
        or any(type(key) is not str or not key for key, _value in values)
        or any(type(value) is not int or value < 0 for _key, value in values)
    ):
        _fail(f"{label} must be one sorted unique exact-value tuple")
    return values


class FormulaOperationV1(str, Enum):
    EXTERNAL_VALUE = "EXTERNAL_VALUE"
    SUM_DERIVED_PATHS = "SUM_DERIVED_PATHS"


@dataclass(frozen=True, slots=True)
class K7ReconciliationFormulaAuthorityV1:
    """One immutable equation from the official eight-path DAG."""

    _issuer: InitVar[object]
    path: str
    semantics_id: str
    operation: FormulaOperationV1
    external_key: str | None
    derived_dependencies: tuple[str, ...]
    _formula_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        try:
            operation = FormulaOperationV1(self.operation)
        except (TypeError, ValueError) as error:
            raise ConstructionK7DerivedReconciliationV1Error(
                "formula operation is invalid"
            ) from error
        object.__setattr__(self, "operation", operation)
        registry = registry_v6.official_counter_registry_v6()
        leaf = registry.by_path.get(self.path)
        if (
            _issuer is not _FORMULA_ISSUER
            or self.path not in DERIVED_PATHS
            or leaf is None
            or leaf.lane is not LaneEnum.DERIVED_ONLY
            or leaf.reducer is not ReducerEnum.SUM
            or leaf.semantics_id != self.semantics_id
            or tuple(sorted(self.derived_dependencies))
            != self.derived_dependencies
            or len(set(self.derived_dependencies))
            != len(self.derived_dependencies)
            or self.path in self.derived_dependencies
            or any(path not in DERIVED_PATHS for path in self.derived_dependencies)
        ):
            _fail("formula differs from the exact V6 derived leaf")
        if operation is FormulaOperationV1.EXTERNAL_VALUE:
            if (
                type(self.external_key) is not str
                or not self.external_key
                or self.derived_dependencies
            ):
                _fail("external formula requires exactly one external key")
        elif self.external_key is not None or not self.derived_dependencies:
            _fail("SUM formula requires derived dependencies only")
        expected = _FORMULA_BLUEPRINTS.get(self.path)
        if expected != (
            operation,
            self.external_key,
            self.derived_dependencies,
        ):
            _fail("formula differs from the frozen official equation")
        object.__setattr__(
            self,
            "_formula_id",
            _local_content_id(FORMULA_AUTHORITY_V1_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_reconciliation_formula_authority.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "path": self.path,
            "semantics_id": self.semantics_id,
            "reducer": ReducerEnum.SUM.value,
            "operation": self.operation.value,
            "external_key": self.external_key,
            "derived_dependencies": list(self.derived_dependencies),
            "closure_dependency_paths": list(self.closure_dependency_paths),
            "caller_formula_allowed": False,
        }

    @property
    def closure_dependency_paths(self) -> tuple[str, ...]:
        """Required-path DAG edge set for the later evidence-closure bridge."""

        paths = _CLOSURE_DEPENDENCY_BLUEPRINT[self.path]
        registry = registry_v6.official_counter_registry_v6()
        if (
            not paths
            or tuple(sorted(paths)) != paths
            or self.path in paths
            or any(path not in registry.by_path for path in paths)
        ):
            _fail("formula closure dependencies differ from the V6 path DAG")
        return paths

    @property
    def formula_id(self) -> str:
        current = _local_content_id(FORMULA_AUTHORITY_V1_DOMAIN, self._payload())
        if current != self._formula_id:
            _fail("reconciliation formula changed after issuance")
        return self._formula_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "reconciliation_formula_id": self.formula_id}


_FORMULA_BLUEPRINTS = {
    "process.exit_failures": (
        FormulaOperationV1.EXTERNAL_VALUE,
        "process_reaps.exit_failures",
        (),
    ),
    "process.exit_successes": (
        FormulaOperationV1.EXTERNAL_VALUE,
        "process_reaps.exit_successes",
        (),
    ),
    "route.attempts": (
        FormulaOperationV1.SUM_DERIVED_PATHS,
        None,
        ("route.failures", "route.successes"),
    ),
    "route.failures": (
        FormulaOperationV1.EXTERNAL_VALUE,
        "root_terminal.route_failures",
        (),
    ),
    "route.successes": (
        FormulaOperationV1.EXTERNAL_VALUE,
        "root_terminal.route_successes",
        (),
    ),
    "solver.attempts": (
        FormulaOperationV1.SUM_DERIVED_PATHS,
        None,
        ("solver.failures", "solver.successes"),
    ),
    "solver.failures": (
        FormulaOperationV1.EXTERNAL_VALUE,
        "root_stage_profile.solver_failures",
        (),
    ),
    "solver.successes": (
        FormulaOperationV1.EXTERNAL_VALUE,
        "root_stage_profile.solver_successes",
        (),
    ),
}

_CLOSURE_DEPENDENCY_BLUEPRINT = {
    "process.exit_failures": ("process.launches",),
    "process.exit_successes": ("process.launches",),
    "route.attempts": ("route.failures", "route.successes"),
    "route.failures": ("process.exit_failures", "process.exit_successes"),
    "route.successes": ("process.exit_failures", "process.exit_successes"),
    "solver.attempts": ("solver.failures", "solver.successes"),
    "solver.failures": ("route.attempts",),
    "solver.successes": ("route.attempts",),
}


@lru_cache(maxsize=1)
def official_k7_reconciliation_formulas_v1(
) -> tuple[K7ReconciliationFormulaAuthorityV1, ...]:
    registry = registry_v6.official_counter_registry_v6()
    formulas = tuple(
        K7ReconciliationFormulaAuthorityV1(
            _FORMULA_ISSUER,
            path,
            registry.by_path[path].semantics_id,
            _FORMULA_BLUEPRINTS[path][0],
            _FORMULA_BLUEPRINTS[path][1],
            _FORMULA_BLUEPRINTS[path][2],
        )
        for path in DERIVED_PATHS
    )
    _topological_formula_order(formulas)
    _topological_closure_order(formulas)
    return formulas


def _topological_formula_order(
    formulas: tuple[K7ReconciliationFormulaAuthorityV1, ...],
) -> tuple[str, ...]:
    by_path = {row.path: row for row in formulas}
    if set(by_path) != set(DERIVED_PATHS) or len(by_path) != len(formulas):
        _fail("formula set is missing, duplicated, or forged")
    visiting: set[str] = set()
    visited: set[str] = set()
    order: list[str] = []

    def visit(path: str) -> None:
        if path in visited:
            return
        if path in visiting:
            _fail("reconciliation formula dependencies are circular")
        visiting.add(path)
        for dependency in by_path[path].derived_dependencies:
            if dependency not in by_path:
                _fail("reconciliation formula dependency is missing")
            visit(dependency)
        visiting.remove(path)
        visited.add(path)
        order.append(path)

    for path in DERIVED_PATHS:
        visit(path)
    return tuple(order)


def _topological_closure_order(
    formulas: tuple[K7ReconciliationFormulaAuthorityV1, ...],
) -> tuple[str, ...]:
    """Validate the proof/application DAG, including non-derived V6 roots."""

    by_path = {row.path: row for row in formulas}
    if set(by_path) != set(DERIVED_PATHS) or len(by_path) != len(formulas):
        _fail("closure formula set is missing, duplicated, or forged")
    registry = registry_v6.official_counter_registry_v6()
    visiting: set[str] = set()
    visited: set[str] = set()
    order: list[str] = []

    def visit(path: str) -> None:
        if path in visited:
            return
        if path in visiting:
            _fail("reconciliation closure dependencies are circular")
        visiting.add(path)
        formula = by_path[path]
        for dependency in formula.closure_dependency_paths:
            if dependency not in registry.by_path:
                _fail("reconciliation closure dependency is not a V6 path")
            if dependency in by_path:
                visit(dependency)
        visiting.remove(path)
        visited.add(path)
        order.append(path)

    for path in DERIVED_PATHS:
        visit(path)
    return tuple(order)


@dataclass(frozen=True, slots=True)
class K7ReconciliationArithmeticReplayV1:
    """Arithmetic-only replay; caller inputs never become semantic evidence."""

    _issuer: InitVar[object]
    formula_ids: tuple[str, ...]
    external_values: tuple[tuple[str, int], ...]
    derived_values: tuple[tuple[str, int], ...]
    _replay_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        formulas = official_k7_reconciliation_formulas_v1()
        if (
            _issuer is not _ARITHMETIC_ISSUER
            or self.formula_ids != tuple(row.formula_id for row in formulas)
            or _exact_values(self.external_values, "arithmetic external values")
            != self.external_values
            or _exact_values(self.derived_values, "arithmetic derived values")
            != self.derived_values
            or tuple(path for path, _value in self.derived_values) != DERIVED_PATHS
        ):
            _fail("arithmetic replay is caller-minted or incomplete")
        object.__setattr__(
            self,
            "_replay_id",
            _local_content_id(ARITHMETIC_REPLAY_V1_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_reconciliation_arithmetic_replay.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "formula_ids": list(self.formula_ids),
            "external_values": [
                {"key": key, "value": value}
                for key, value in self.external_values
            ],
            "derived_values": [
                {"path": path, "value": value}
                for path, value in self.derived_values
            ],
            "arithmetic_only": True,
            "external_values_semantically_verified": False,
            "counter_record_materialization_eligible": False,
            "counter_records_issued": False,
        }

    @property
    def replay_id(self) -> str:
        current = _local_content_id(ARITHMETIC_REPLAY_V1_DOMAIN, self._payload())
        if current != self._replay_id:
            _fail("arithmetic replay changed after issuance")
        return self._replay_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "arithmetic_replay_id": self.replay_id}


def evaluate_official_k7_reconciliation_arithmetic_v1(
    external_values: Mapping[str, int],
) -> K7ReconciliationArithmeticReplayV1:
    """Evaluate the official DAG without treating caller values as evidence."""

    if type(external_values) is not dict:
        _fail("arithmetic replay requires one exact external-value dict")
    formulas = official_k7_reconciliation_formulas_v1()
    expected_keys = {
        row.external_key
        for row in formulas
        if row.external_key is not None
    }
    if set(external_values) != expected_keys or any(
        type(value) is not int or value < 0 for value in external_values.values()
    ):
        _fail("arithmetic replay external keys or values are missing or forged")
    by_path = {row.path: row for row in formulas}
    values: dict[str, int] = {}
    for path in _topological_formula_order(formulas):
        formula = by_path[path]
        if formula.operation is FormulaOperationV1.EXTERNAL_VALUE:
            assert formula.external_key is not None
            values[path] = external_values[formula.external_key]
        else:
            values[path] = sum(values[item] for item in formula.derived_dependencies)
    return K7ReconciliationArithmeticReplayV1(
        _ARITHMETIC_ISSUER,
        tuple(row.formula_id for row in formulas),
        tuple(sorted(external_values.items())),
        tuple((path, values[path]) for path in DERIVED_PATHS),
    )


class SemanticDependencyKindV1(str, Enum):
    PROCESS_DIRECT_PIDFD_REAPS = "PROCESS_DIRECT_PIDFD_REAPS"
    ROOT_CAP_STAGE_EXCLUSION = "ROOT_CAP_STAGE_EXCLUSION"
    ROOT_CAP_TERMINAL_OUTCOME = "ROOT_CAP_TERMINAL_OUTCOME"


@dataclass(frozen=True, slots=True)
class K7ExactReconciliationSemanticDependencyV1:
    """Issuer-owned exact semantic inputs for one formula family."""

    _issuer: InitVar[object]
    kind: SemanticDependencyKindV1
    counter_registry_id: str
    stage_profile_id: str
    occurrence_id: str
    source_ids: tuple[str, ...]
    exact_values: tuple[tuple[str, int], ...]
    semantic_checks: tuple[str, ...]
    _dependency_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        try:
            kind = SemanticDependencyKindV1(self.kind)
        except (TypeError, ValueError) as error:
            raise ConstructionK7DerivedReconciliationV1Error(
                "semantic dependency kind is invalid"
            ) from error
        object.__setattr__(self, "kind", kind)
        for value, label in (
            (self.counter_registry_id, "dependency counter registry"),
            (self.stage_profile_id, "dependency stage profile"),
            (self.occurrence_id, "dependency occurrence"),
            *((value, "dependency source") for value in self.source_ids),
        ):
            _cid(value, label)
        if (
            _issuer is not _DEPENDENCY_ISSUER
            or not self.source_ids
            or len(set(self.source_ids)) != len(self.source_ids)
            or _exact_values(self.exact_values, "semantic dependency values")
            != self.exact_values
            or type(self.semantic_checks) is not tuple
            or not self.semantic_checks
            or tuple(sorted(self.semantic_checks)) != self.semantic_checks
            or len(set(self.semantic_checks)) != len(self.semantic_checks)
        ):
            _fail("semantic dependency is caller-minted or incomplete")
        expected_keys = {
            SemanticDependencyKindV1.PROCESS_DIRECT_PIDFD_REAPS: {
                "process_reaps.exit_failures",
                "process_reaps.exit_successes",
            },
            SemanticDependencyKindV1.ROOT_CAP_STAGE_EXCLUSION: {
                "root_stage_profile.solver_failures",
                "root_stage_profile.solver_successes",
            },
            SemanticDependencyKindV1.ROOT_CAP_TERMINAL_OUTCOME: {
                "root_terminal.route_failures",
                "root_terminal.route_successes",
            },
        }[kind]
        if {key for key, _value in self.exact_values} != expected_keys:
            _fail("semantic dependency values differ from its fixed family")
        object.__setattr__(
            self,
            "_dependency_id",
            _local_content_id(SEMANTIC_DEPENDENCY_V1_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_reconciliation_semantic_dependency.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "dependency_kind": self.kind.value,
            "counter_registry_id": self.counter_registry_id,
            "stage_profile_id": self.stage_profile_id,
            "occurrence_id": self.occurrence_id,
            "source_ids": list(self.source_ids),
            "exact_values": [
                {"key": key, "value": value}
                for key, value in self.exact_values
            ],
            "semantic_checks": list(self.semantic_checks),
            "independent_semantic_replay_complete": True,
            "counter_records_issued": False,
        }

    @property
    def dependency_id(self) -> str:
        current = _local_content_id(
            SEMANTIC_DEPENDENCY_V1_DOMAIN, self._payload()
        )
        if current != self._dependency_id:
            _fail("semantic dependency changed after issuance")
        return self._dependency_id

    @property
    def by_key(self) -> dict[str, int]:
        return dict(self.exact_values)

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "semantic_dependency_id": self.dependency_id}


def _verified_context(
    verified: verified_v1.K7VerifiedNineSharedResourceEnvelopeV1,
) -> tuple[str, str, str]:
    if type(verified) is not verified_v1.K7VerifiedNineSharedResourceEnvelopeV1:
        _fail("reconciliation requires one exact verified-nine envelope")
    verified._assert_current()  # noqa: SLF001 - exact predecessor replay
    source = verified.source_envelope
    return source.counter_registry_id, source.stage_profile_id, source.occurrence_id


def derive_process_reap_dependency_v1(
    verified: verified_v1.K7VerifiedNineSharedResourceEnvelopeV1,
) -> K7ExactReconciliationSemanticDependencyV1:
    registry_id, stage_id, occurrence_id = _verified_context(verified)
    authorization = verified.by_path.get("process.launches")
    if authorization is None:
        _fail("verified-nine envelope lacks process.launches")
    source = authorization.bound_source.source
    replayed = replay_v2.verify_process_launches_exact_v2(source)
    if (
        replayed.exact_value != authorization.exact_value
        or replayed.semantic_verifier_id != authorization.semantic_verifier_id
        or replayed.exact_value <= 0
    ):
        _fail("process launch authorization differs from fresh semantic replay")
    component = next(
        (
            item
            for item in source.components
            if item.component_key == "process_lifecycle_journal"
        ),
        None,
    )
    if component is None:
        _fail("process source lacks its lifecycle journal")
    document = loads_canonical_json(component.raw_bytes)
    if type(document) is not dict or type(document.get("events")) is not list:
        _fail("process lifecycle journal is not canonical")
    reaps = tuple(
        row
        for row in document["events"]
        if type(row) is dict
        and row.get("kind")
        == working_v2.LifecycleEventKindV2.DIRECT_PIDFD_REAP.value
    )
    roles = tuple(row.get("role") for row in reaps)
    allowed_codes = {
        value
        for name in ("CLD_EXITED", "CLD_KILLED", "CLD_DUMPED")
        if type(value := getattr(os, name, None)) is int
    }
    if (
        roles != working_v2.EXPECTED_ROLES
        or len(reaps) != replayed.exact_value
        or not allowed_codes
        or any(
            type(row.get("wait_si_code")) is not int
            or row["wait_si_code"] not in allowed_codes
            or type(row.get("wait_si_status")) is not int
            or row["wait_si_status"] < 0
            or row.get("wait_si_signo") != signal.SIGCHLD
            or row.get("direct_child_reaped") is not True
            for row in reaps
        )
    ):
        _fail("process direct-reap outcomes are missing, forged, or unclassifiable")
    success = sum(
        row["wait_si_code"] == os.CLD_EXITED and row["wait_si_status"] == 0
        for row in reaps
    )
    failure = len(reaps) - success
    if success + failure != replayed.exact_value:
        _fail("process exits do not conserve exact process launches")
    return K7ExactReconciliationSemanticDependencyV1(
        _DEPENDENCY_ISSUER,
        SemanticDependencyKindV1.PROCESS_DIRECT_PIDFD_REAPS,
        registry_id,
        stage_id,
        occurrence_id,
        (
            verified.verified_envelope_id,
            authorization.authorization_id,
            component.source_artifact_id,
        ),
        tuple(
            sorted(
                (
                    ("process_reaps.exit_failures", failure),
                    ("process_reaps.exit_successes", success),
                )
            )
        ),
        tuple(
            sorted(
                (
                    "direct_pidfd_reap_roles_complete",
                    "exit_classification_from_waitid",
                    "fresh_process_semantic_replay",
                    "launch_exit_conservation",
                )
            )
        ),
    )


def derive_solver_stage_exclusion_dependency_v1(
    *,
    verified: verified_v1.K7VerifiedNineSharedResourceEnvelopeV1,
    transcript: partial_v1.PartialNativeOccurrenceTranscriptV1,
) -> K7ExactReconciliationSemanticDependencyV1:
    registry_id, stage_id, occurrence_id = _verified_context(verified)
    if type(transcript) is not partial_v1.PartialNativeOccurrenceTranscriptV1:
        _fail("solver exclusion requires one exact partial-native transcript")
    partial_v1.verify_partial_native_occurrence_transcript_v1(transcript)
    terminal = transcript.nodes[-1]
    registry = registry_v6.official_counter_registry_v6()
    stage = registry_v6.official_stage_profile_v6(registry)
    solver_paths = {
        "solver.attempts",
        "solver.failures",
        "solver.successes",
    }
    solver_stages = {
        rule.stage_kind.value
        for rule in stage.rules
        if solver_paths & set(rule.allowed_nonzero_paths)
    }
    if (
        transcript.start.counter_registry_id != registry_id
        or transcript.start.stage_profile_id != stage_id
        or transcript.start.occurrence_id != occurrence_id
        or registry.registry_id != registry_id
        or stage.stage_profile_id != stage_id
        or transcript.start.stage_plan != partial_v1.ROOT_CAP_FIVE_STAGE_PLAN_V1
        or transcript.terminal_kind is not partial_v1.PartialNativeTerminalKindV1.COMPLETED
        or type(terminal) is not partial_v1.PartialNativeOccurrenceCompletionV1
        or solver_stages != {"DIRECT_FALLBACK", "LOCAL_ATTEMPT"}
        or solver_stages & {item.value for item in transcript.start.stage_plan}
    ):
        _fail("root-cap stage closure cannot prove solver exclusion")
    return K7ExactReconciliationSemanticDependencyV1(
        _DEPENDENCY_ISSUER,
        SemanticDependencyKindV1.ROOT_CAP_STAGE_EXCLUSION,
        registry_id,
        stage_id,
        occurrence_id,
        (verified.verified_envelope_id, transcript.transcript_id, terminal.chain_id),
        (
            ("root_stage_profile.solver_failures", 0),
            ("root_stage_profile.solver_successes", 0),
        ),
        tuple(
            sorted(
                (
                    "exact_five_stage_chain_replayed",
                    "local_and_fallback_stages_absent",
                    "solver_nonzero_stage_set_replayed",
                )
            )
        ),
    )


@dataclass(frozen=True, slots=True)
class K7ExactDerivedPathProofV1:
    """One exact formula result; still not a CounterRecord."""

    _issuer: InitVar[object]
    path: str
    value: int
    formula: K7ReconciliationFormulaAuthorityV1 = field(repr=False)
    semantic_dependency_ids: tuple[str, ...]
    derived_dependency_proof_ids: tuple[str, ...]
    verified_nine_envelope_id: str
    production_runtime_envelope_id: str
    occurrence_id: str
    route_attempt_id: str
    decision_point_id: str
    measurement_window_id: str
    production_runtime_replay_id: str
    terminal_closure_observation_id: str
    _proof_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        for value, label in (
            (self.verified_nine_envelope_id, "verified-nine envelope"),
            (self.production_runtime_envelope_id, "production runtime envelope"),
            (self.occurrence_id, "occurrence"),
            (self.route_attempt_id, "route attempt"),
            (self.decision_point_id, "decision point"),
            (self.measurement_window_id, "measurement window"),
            (self.production_runtime_replay_id, "production runtime replay"),
            (
                self.terminal_closure_observation_id,
                "terminal closure observation",
            ),
            *((value, "semantic dependency") for value in self.semantic_dependency_ids),
            *((value, "derived dependency proof") for value in self.derived_dependency_proof_ids),
        ):
            _cid(value, label)
        _nonnegative(self.value, "derived path value")
        official_formula = {
            row.path: row for row in official_k7_reconciliation_formulas_v1()
        }.get(self.path)
        if (
            _issuer is not _PROOF_ISSUER
            or type(self.formula) is not K7ReconciliationFormulaAuthorityV1
            or self.path != self.formula.path
            or self.path not in DERIVED_PATHS
            or official_formula is None
            or self.formula.formula_id != official_formula.formula_id
            or len(set(self.semantic_dependency_ids))
            != len(self.semantic_dependency_ids)
            or len(set(self.derived_dependency_proof_ids))
            != len(self.derived_dependency_proof_ids)
            or bool(self.semantic_dependency_ids)
            == bool(self.derived_dependency_proof_ids)
        ):
            _fail("derived path proof is caller-minted or has ambiguous dependencies")
        if self.formula.operation is FormulaOperationV1.EXTERNAL_VALUE:
            if len(self.semantic_dependency_ids) != 1 or self.derived_dependency_proof_ids:
                _fail("external path proof lacks its one exact semantic dependency")
        elif (
            self.semantic_dependency_ids
            or len(self.derived_dependency_proof_ids)
            != len(self.formula.derived_dependencies)
        ):
            _fail("sum path proof lacks its exact derived dependencies")
        object.__setattr__(
            self,
            "_proof_id",
            _local_content_id(PATH_PROOF_V1_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_exact_derived_path_proof.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "path": self.path,
            "value": self.value,
            "reducer": ReducerEnum.SUM.value,
            "formula_id": self.formula.formula_id,
            "semantic_dependency_ids": list(self.semantic_dependency_ids),
            "derived_dependency_proof_ids": list(
                self.derived_dependency_proof_ids
            ),
            "verified_nine_envelope_id": self.verified_nine_envelope_id,
            "production_runtime_envelope_id": self.production_runtime_envelope_id,
            "occurrence_id": self.occurrence_id,
            "route_attempt_id": self.route_attempt_id,
            "decision_point_id": self.decision_point_id,
            "measurement_window_id": self.measurement_window_id,
            "production_runtime_replay_id": self.production_runtime_replay_id,
            "terminal_closure_observation_id": (
                self.terminal_closure_observation_id
            ),
            "exact_semantic_dependencies_replayed": True,
            "path_resolution_materialization_eligible": True,
            "counter_record_issued": False,
            "work_vector_issued": False,
            "comparison_vector_issued": False,
            "formal_vector_authorized": False,
        }

    @property
    def proof_id(self) -> str:
        current = _local_content_id(PATH_PROOF_V1_DOMAIN, self._payload())
        if current != self._proof_id:
            _fail("derived path proof changed after issuance")
        return self._proof_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "exact_derived_path_proof_id": self.proof_id}


def _proof(
    *,
    verified: verified_v1.K7VerifiedNineSharedResourceEnvelopeV1,
    formula: K7ReconciliationFormulaAuthorityV1,
    value: int,
    semantic_dependency_ids: tuple[str, ...] = (),
    derived_dependency_proof_ids: tuple[str, ...] = (),
) -> K7ExactDerivedPathProofV1:
    source = verified.source_envelope
    return K7ExactDerivedPathProofV1(
        _PROOF_ISSUER,
        formula.path,
        value,
        formula,
        semantic_dependency_ids,
        derived_dependency_proof_ids,
        verified.verified_envelope_id,
        source.production_runtime_envelope_id,
        source.occurrence_id,
        source.route_attempt_id,
        source.decision_point_id,
        source.measurement_window_id,
        source.production_runtime_replay_id,
        source.terminal_closure_observation_id,
    )


class ReconciliationBlockerCodeV1(str, Enum):
    PROCESS_REAP_AUTHORITY_NOT_AVAILABLE = (
        "PROCESS_REAP_AUTHORITY_NOT_AVAILABLE"
    )
    ROOT_CAP_OWNER_STAGE_CLOSURE_NOT_AVAILABLE = (
        "ROOT_CAP_OWNER_STAGE_CLOSURE_NOT_AVAILABLE"
    )
    ROUTE_TERMINAL_SEMANTIC_AUTHORITY_UNAVAILABLE = (
        "ROUTE_TERMINAL_SEMANTIC_AUTHORITY_UNAVAILABLE"
    )
    VERIFIED_NINE_CONTEXT_NOT_AVAILABLE = "VERIFIED_NINE_CONTEXT_NOT_AVAILABLE"


_BLOCKER_DETAILS = {
    ReconciliationBlockerCodeV1.PROCESS_REAP_AUTHORITY_NOT_AVAILABLE: (
        ("process.exit_failures", "process.exit_successes"),
        "exact verified process-launch/reap evidence is unavailable",
    ),
    ReconciliationBlockerCodeV1.ROOT_CAP_OWNER_STAGE_CLOSURE_NOT_AVAILABLE: (
        ("solver.attempts", "solver.failures", "solver.successes"),
        "an independently replayed typed root-cap stage closure is unavailable",
    ),
    ReconciliationBlockerCodeV1.ROUTE_TERMINAL_SEMANTIC_AUTHORITY_UNAVAILABLE: (
        ("route.attempts", "route.failures", "route.successes"),
        (
            "no authority binds full owner transcript replay to the production "
            "runtime's actual BUSINESS_RESULT bytes, SHA-256, and public-replay ID"
        ),
    ),
    ReconciliationBlockerCodeV1.VERIFIED_NINE_CONTEXT_NOT_AVAILABLE: (
        DERIVED_PATHS,
        "the verified-nine outer attempt context is unavailable",
    ),
}


@dataclass(frozen=True, slots=True)
class K7DerivedReconciliationBlockerV1:
    _issuer: InitVar[object]
    code: ReconciliationBlockerCodeV1
    affected_paths: tuple[str, ...]
    reason: str
    _blocker_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        try:
            code = ReconciliationBlockerCodeV1(self.code)
        except (TypeError, ValueError) as error:
            raise ConstructionK7DerivedReconciliationV1Error(
                "reconciliation blocker code is invalid"
            ) from error
        object.__setattr__(self, "code", code)
        paths, reason = _BLOCKER_DETAILS[code]
        if (
            _issuer is not _BLOCKER_ISSUER
            or self.affected_paths != paths
            or self.reason != reason
        ):
            _fail("reconciliation blocker is caller-minted or noncanonical")
        object.__setattr__(
            self,
            "_blocker_id",
            _local_content_id(BLOCKER_V1_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_derived_reconciliation_blocker.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "code": self.code.value,
            "affected_paths": list(self.affected_paths),
            "reason": self.reason,
            "kind": "NOT_AVAILABLE",
        }

    @property
    def blocker_id(self) -> str:
        current = _local_content_id(BLOCKER_V1_DOMAIN, self._payload())
        if current != self._blocker_id:
            _fail("reconciliation blocker changed after issuance")
        return self._blocker_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "reconciliation_blocker_id": self.blocker_id}


def _blocker(code: ReconciliationBlockerCodeV1) -> K7DerivedReconciliationBlockerV1:
    paths, reason = _BLOCKER_DETAILS[code]
    return K7DerivedReconciliationBlockerV1(
        _BLOCKER_ISSUER, code, paths, reason
    )


class ReconciliationReadinessStatusV1(str, Enum):
    COMPLETE_EXACT = "COMPLETE_EXACT"
    INCOMPLETE_TYPED = "INCOMPLETE_TYPED"


@dataclass(frozen=True, slots=True)
class K7DerivedReconciliationReadinessV1:
    """Exact proof subset plus canonical blockers for the remaining paths."""

    _issuer: InitVar[object]
    status: ReconciliationReadinessStatusV1
    formula_ids: tuple[str, ...]
    verified_nine_envelope_id: str | None
    proofs: tuple[K7ExactDerivedPathProofV1, ...] = field(repr=False)
    blockers: tuple[K7DerivedReconciliationBlockerV1, ...] = field(repr=False)
    _readiness_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        try:
            status = ReconciliationReadinessStatusV1(self.status)
        except (TypeError, ValueError) as error:
            raise ConstructionK7DerivedReconciliationV1Error(
                "reconciliation readiness status is invalid"
            ) from error
        object.__setattr__(self, "status", status)
        formulas = official_k7_reconciliation_formulas_v1()
        if self.verified_nine_envelope_id is not None:
            _cid(self.verified_nine_envelope_id, "verified-nine envelope")
        if (
            _issuer is not _READINESS_ISSUER
            or self.formula_ids != tuple(row.formula_id for row in formulas)
            or type(self.proofs) is not tuple
            or any(type(row) is not K7ExactDerivedPathProofV1 for row in self.proofs)
            or tuple(row.path for row in self.proofs)
            != tuple(path for path in DERIVED_PATHS if path in {row.path for row in self.proofs})
            or len({row.path for row in self.proofs}) != len(self.proofs)
            or type(self.blockers) is not tuple
            or any(
                type(row) is not K7DerivedReconciliationBlockerV1
                for row in self.blockers
            )
            or tuple(sorted(self.blockers, key=lambda row: row.code.value))
            != self.blockers
            or len({row.code for row in self.blockers}) != len(self.blockers)
        ):
            _fail("reconciliation readiness is caller-minted or noncanonical")
        resolved = {row.path for row in self.proofs}
        blocked = {path for row in self.blockers for path in row.affected_paths}
        verified_context_matches = all(
            row.verified_nine_envelope_id == self.verified_nine_envelope_id
            for row in self.proofs
        )
        proof_and_blocker_ids_current = all(
            row.proof_id for row in self.proofs
        ) and all(row.blocker_id for row in self.blockers)
        if (
            resolved & blocked
            or resolved | blocked != set(DERIVED_PATHS)
            or not verified_context_matches
            or not proof_and_blocker_ids_current
            or (status is ReconciliationReadinessStatusV1.COMPLETE_EXACT)
            != (len(resolved) == len(DERIVED_PATHS) and not self.blockers)
            or (
                status is ReconciliationReadinessStatusV1.COMPLETE_EXACT
                and self.verified_nine_envelope_id is None
            )
            or (
                self.verified_nine_envelope_id is None
                and (
                    self.proofs
                    or tuple(row.code for row in self.blockers)
                    != (
                        ReconciliationBlockerCodeV1
                        .VERIFIED_NINE_CONTEXT_NOT_AVAILABLE,
                    )
                )
            )
        ):
            _fail("reconciliation readiness coverage or status is inconsistent")
        object.__setattr__(
            self,
            "_readiness_id",
            _local_content_id(READINESS_V1_DOMAIN, self._payload()),
        )

    @property
    def resolved_paths(self) -> tuple[str, ...]:
        return tuple(row.path for row in self.proofs)

    @property
    def unresolved_paths(self) -> tuple[str, ...]:
        resolved = set(self.resolved_paths)
        return tuple(path for path in DERIVED_PATHS if path not in resolved)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_derived_reconciliation_readiness.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "status": self.status.value,
            "formula_ids": list(self.formula_ids),
            "verified_nine_envelope_id": self.verified_nine_envelope_id,
            "proof_ids": [row.proof_id for row in self.proofs],
            "resolved_paths": list(self.resolved_paths),
            "blocker_ids": [row.blocker_id for row in self.blockers],
            "blocker_codes": [row.code.value for row in self.blockers],
            "unresolved_paths": list(self.unresolved_paths),
            "all_eight_exact": not self.unresolved_paths,
            "counter_record_materialization_eligible": not self.unresolved_paths,
            "counter_records_issued": False,
            "work_vector_issued": False,
            "comparison_vector_issued": False,
            "formal_vector_authorized": False,
        }

    @property
    def readiness_id(self) -> str:
        current = _local_content_id(READINESS_V1_DOMAIN, self._payload())
        if current != self._readiness_id:
            _fail("reconciliation readiness changed after issuance")
        return self._readiness_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "derived_reconciliation_readiness_id": self.readiness_id}


def _family_proofs(
    *,
    verified: verified_v1.K7VerifiedNineSharedResourceEnvelopeV1,
    dependency: K7ExactReconciliationSemanticDependencyV1,
    family: str,
) -> tuple[K7ExactDerivedPathProofV1, ...]:
    formulas = {row.path: row for row in official_k7_reconciliation_formulas_v1()}
    values = dependency.by_key
    if family == "process":
        base_paths = ("process.exit_failures", "process.exit_successes")
        total_path = None
    elif family == "route":
        base_paths = ("route.failures", "route.successes")
        total_path = "route.attempts"
    elif family == "solver":
        base_paths = ("solver.failures", "solver.successes")
        total_path = "solver.attempts"
    else:
        _fail("unknown reconciliation proof family")
    base = tuple(
        _proof(
            verified=verified,
            formula=formulas[path],
            value=values[formulas[path].external_key],  # type: ignore[index]
            semantic_dependency_ids=(dependency.dependency_id,),
        )
        for path in base_paths
    )
    if total_path is None:
        return base
    total = _proof(
        verified=verified,
        formula=formulas[total_path],
        value=sum(row.value for row in base),
        derived_dependency_proof_ids=tuple(row.proof_id for row in base),
    )
    return (total, *base)


def derive_k7_eight_path_reconciliation_v1(
    *,
    verified_nine: verified_v1.K7VerifiedNineSharedResourceEnvelopeV1 | None,
    owner_transcript: partial_v1.PartialNativeOccurrenceTranscriptV1 | None = None,
    route_terminal_semantic_authority: object | None = None,
) -> K7DerivedReconciliationReadinessV1:
    """Derive every available exact family and retain canonical blockers."""

    formulas = official_k7_reconciliation_formulas_v1()
    if verified_nine is None:
        if owner_transcript is not None or route_terminal_semantic_authority is not None:
            _fail("owner/terminal evidence cannot float without outer attempt context")
        return K7DerivedReconciliationReadinessV1(
            _READINESS_ISSUER,
            ReconciliationReadinessStatusV1.INCOMPLETE_TYPED,
            tuple(row.formula_id for row in formulas),
            None,
            (),
            (_blocker(ReconciliationBlockerCodeV1.VERIFIED_NINE_CONTEXT_NOT_AVAILABLE),),
        )
    _verified_context(verified_nine)
    if owner_transcript is not None and type(owner_transcript) is not (
        partial_v1.PartialNativeOccurrenceTranscriptV1
    ):
        _fail("owner transcript evidence is forged")
    if route_terminal_semantic_authority is not None:
        _fail(
            "no route-terminal semantic authority is registered in this profile; "
            "owned result/status or bundle hashes are not admissible substitutes"
        )

    proofs: list[K7ExactDerivedPathProofV1] = []
    blockers: list[K7DerivedReconciliationBlockerV1] = []
    try:
        process_dependency = derive_process_reap_dependency_v1(verified_nine)
    except Exception as error:
        if isinstance(error, ConstructionK7DerivedReconciliationV1Error):
            raise
        raise ConstructionK7DerivedReconciliationV1Error(
            "process dependency replay failed"
        ) from error
    proofs.extend(
        _family_proofs(
            verified=verified_nine,
            dependency=process_dependency,
            family="process",
        )
    )

    if owner_transcript is None:
        blockers.append(
            _blocker(
                ReconciliationBlockerCodeV1
                .ROOT_CAP_OWNER_STAGE_CLOSURE_NOT_AVAILABLE
            )
        )
    else:
        solver_dependency = derive_solver_stage_exclusion_dependency_v1(
            verified=verified_nine,
            transcript=owner_transcript,
        )
        proofs.extend(
            _family_proofs(
                verified=verified_nine,
                dependency=solver_dependency,
                family="solver",
            )
        )

    blockers.append(
        _blocker(
            ReconciliationBlockerCodeV1
            .ROUTE_TERMINAL_SEMANTIC_AUTHORITY_UNAVAILABLE
        )
    )

    ordered_proofs = tuple(
        next(row for row in proofs if row.path == path)
        for path in DERIVED_PATHS
        if any(row.path == path for row in proofs)
    )
    ordered_blockers = tuple(sorted(blockers, key=lambda row: row.code.value))
    status = (
        ReconciliationReadinessStatusV1.COMPLETE_EXACT
        if len(ordered_proofs) == len(DERIVED_PATHS)
        else ReconciliationReadinessStatusV1.INCOMPLETE_TYPED
    )
    return K7DerivedReconciliationReadinessV1(
        _READINESS_ISSUER,
        status,
        tuple(row.formula_id for row in formulas),
        verified_nine.verified_envelope_id,
        ordered_proofs,
        ordered_blockers,
    )


__all__ = (
    "ARITHMETIC_REPLAY_V1_DOMAIN",
    "BLOCKER_V1_DOMAIN",
    "ConstructionK7DerivedReconciliationV1Error",
    "DERIVED_PATHS",
    "FORMULA_AUTHORITY_V1_DOMAIN",
    "FormulaOperationV1",
    "K7DerivedReconciliationBlockerV1",
    "K7DerivedReconciliationReadinessV1",
    "K7ExactDerivedPathProofV1",
    "K7ExactReconciliationSemanticDependencyV1",
    "K7ReconciliationArithmeticReplayV1",
    "K7ReconciliationFormulaAuthorityV1",
    "PATH_PROOF_V1_DOMAIN",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "READINESS_V1_DOMAIN",
    "REQUESTED_PHASE3E_DOMAIN_TAGS",
    "ReconciliationBlockerCodeV1",
    "ReconciliationReadinessStatusV1",
    "SCHEMA_VERSION",
    "SEMANTIC_DEPENDENCY_V1_DOMAIN",
    "SemanticDependencyKindV1",
    "derive_k7_eight_path_reconciliation_v1",
    "derive_process_reap_dependency_v1",
    "derive_solver_stage_exclusion_dependency_v1",
    "evaluate_official_k7_reconciliation_arithmetic_v1",
    "official_k7_reconciliation_formulas_v1",
)
