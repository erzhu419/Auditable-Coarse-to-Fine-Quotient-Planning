"""V0-056 preregistered durable H2 multi-query workload.

This registered construction composes, without changing, the V0-055 source
recovery with a new query-facet proof layer:

* the three threshold/risk queries and ten logical occurrences are frozen
  before the V0-055 source producer runs;
* the source performs its already-audited failed-proof-to-one-row recovery;
* every target occurrence runs in a fresh model-only process against the
  durable final C2 model;
* query-facet nodes use key-before-builder lookup, so a cache hit does not
  execute the value builder;
* a C2-base-reset arm and a source-blind conditional-ground arm are executed
  for the same logical occurrences.

The counters in this module are deliberately profile-specific operation
traces.  They are not Phase 3E CounterRegistry/WorkVector evidence, exact
kernel calls are not relabelled as statistical samples, and no scalar or
total-work conclusion is emitted.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import inspect
from pathlib import Path
import tempfile
from typing import Any, Mapping

import acfqp.h2_conditional_direct_ground_v1 as direct
import acfqp.h2_durable_action_local_recovery_v1 as recovery
import acfqp.h2_query_family_model_v1 as query_family
from acfqp.h2_durable_multiquery_workload_pins_v1 import (
    EXPECTED_CANONICAL_IDS,
    EXPECTED_CONDITIONAL_DIRECT_MODULE_SHA256,
    EXPECTED_DIRECT_LAUNCH_SOURCE_SHA256,
    EXPECTED_ORCHESTRATOR_MODULE_SHA256,
    EXPECTED_QUERY_FAMILY_MODULE_SHA256,
    EXPECTED_QUERY_INITIALIZE_SOURCE_SHA256,
    EXPECTED_QUERY_LAUNCH_SOURCE_SHA256,
    EXPECTED_SOURCE_RUN_SOURCE_SHA256,
    EXPECTED_V0055_RECOVERY_MODULE_SHA256,
)
from acfqp._runtime_authority_v1 import (
    RuntimeAuthorityMintV1,
    bind_runtime_authority_v1,
    require_runtime_authority_v1,
)
from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id


SCHEMA_VERSION = "1.0.0"
CONTRACT_VERSION = "1.20.0"
PROFILE_KEY = "lmb_h2_preregistered_durable_multiquery_workload_v0"
SUCCESS_STATUS = (
    "CERTIFIED_REGISTERED_H2_PREREGISTERED_"
    "DURABLE_MULTIQUERY_WORKLOAD_CONTROL"
)

DOMAIN_TAGS = {
    "offline_equivalence": (
        "acfqp:h2-durable-multiquery-offline-base-equivalence:v1"
    ),
    "matched": "acfqp:h2-durable-multiquery-matched-occurrence:v1",
    "trace": "acfqp:h2-durable-multiquery-scoped-trace:v1",
    "prefix": "acfqp:h2-durable-multiquery-prefix:v1",
    "telemetry": "acfqp:h2-durable-multiquery-telemetry:v1",
    "snapshot": "acfqp:h2-durable-multiquery-directory-snapshot:v1",
    "result": "acfqp:h2-durable-multiquery-workload-result:v1",
    "verification": "acfqp:h2-durable-multiquery-workload-verification:v1",
}
if len(DOMAIN_TAGS) != len(set(DOMAIN_TAGS.values())):  # pragma: no cover
    raise RuntimeError("V0-056 content domains must be unique")


class DurableMultiQueryWorkloadInvariantViolation(ValueError):
    """The registered protocol, workload, trace, or result is invalid."""


def _content_id(role: str, payload: Mapping[str, Any]) -> str:
    try:
        domain = DOMAIN_TAGS[role]
        encoded = canonical_json_bytes(dict(payload))
    except (KeyError, TypeError, ValueError) as error:
        raise DurableMultiQueryWorkloadInvariantViolation(str(error)) from error
    return hashlib.sha256(domain.encode("utf-8") + b"\x00" + encoded).hexdigest()


def _cid(value: Any, name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise DurableMultiQueryWorkloadInvariantViolation(
            f"{name} must be a full content ID"
        ) from error


def _integer(value: Any, name: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise DurableMultiQueryWorkloadInvariantViolation(
            f"{name} must be an integer >= {minimum}"
        )
    return value


def _file_sha256(path: Path) -> str:
    if (
        not isinstance(path, Path)
        or path.suffix != ".py"
        or not path.is_file()
        or path.is_symlink()
    ):
        raise DurableMultiQueryWorkloadInvariantViolation(
            "registered source path changed"
        )
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _module_sha256(module: Any) -> str:
    return _file_sha256(Path(getattr(module, "__file__", "")).resolve())


def _callable_sha256(function: Any) -> str:
    try:
        return hashlib.sha256(
            inspect.getsource(function).encode("utf-8")
        ).hexdigest()
    except (OSError, TypeError) as error:
        raise DurableMultiQueryWorkloadInvariantViolation(
            "registered callable source cannot be inspected"
        ) from error


def _snapshot_id(root: Path, role: str) -> str:
    if (
        not isinstance(root, Path)
        or not root.is_dir()
        or root.is_symlink()
        or type(role) is not str
        or not role
    ):
        raise DurableMultiQueryWorkloadInvariantViolation(
            f"{role} snapshot root is invalid"
        )
    rows: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            raise DurableMultiQueryWorkloadInvariantViolation(
                f"{role} snapshot contains a symlink"
            )
        if path.is_dir():
            continue
        stat = path.stat()
        if not path.is_file() or stat.st_nlink != 1:
            raise DurableMultiQueryWorkloadInvariantViolation(
                f"{role} snapshot contains a non-unique regular file"
            )
        payload = path.read_bytes()
        after = path.stat()
        if (stat.st_ino, stat.st_size, stat.st_mtime_ns) != (
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
        ):
            raise DurableMultiQueryWorkloadInvariantViolation(
                f"{role} snapshot changed while being read"
            )
        rows.append(
            {
                "path": relative,
                "size_bytes": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
            }
        )
    if not rows:
        raise DurableMultiQueryWorkloadInvariantViolation(
            f"{role} snapshot cannot be empty"
        )
    return _content_id(
        "snapshot",
        {
            "schema": "acfqp.h2_durable_multiquery_directory_snapshot.v1",
            "schema_version": SCHEMA_VERSION,
            "role": role,
            "files": rows,
        },
    )


def _write_preregistration_v1(
    root: Path,
    protocol: query_family.H2QueryFamilyProtocolV1,
    preregistration: query_family.H2QueryFamilyPreregistrationV1,
) -> None:
    """Persist the source-blind workload contract before source construction."""

    if root.exists() or root.is_symlink():
        raise DurableMultiQueryWorkloadInvariantViolation(
            "preregistration target must not exist"
        )
    root.mkdir()
    documents = (
        ("protocol", protocol.protocol_id, protocol.to_document()),
        (
            "preregistration",
            preregistration.preregistration_id,
            preregistration.to_document(),
        ),
    )
    for role, identity, document in documents:
        target = root / f"{role}-{identity}.json"
        payload = canonical_json_bytes(document)
        try:
            with target.open("xb") as stream:
                stream.write(payload)
                stream.flush()
        except (FileExistsError, OSError) as error:
            raise DurableMultiQueryWorkloadInvariantViolation(
                "failed to freeze preregistration bytes"
            ) from error


@dataclass(frozen=True, slots=True)
class V0056ScopedOperationalTraceV1:
    """Only operation families instrumented at their V0-056 execution sites."""

    lane: str
    occurrence_id: str | None
    query_facet_value_builder_calls: int
    query_facet_identity_hits: int
    fresh_query_root_builder_calls: int
    exact_ground_transition_calls: int
    exact_action_catalogue_calls: int
    direct_policy_evaluations: int
    direct_optimizer_calls: int
    process_launches: int
    observed_query_store_read_bytes: int
    observed_query_store_output_bytes: int
    source_checkpoint_unique_bytes: int = 0
    query_store_io_complete: bool = False
    full_counter_registry_complete: bool = False

    def __post_init__(self) -> None:
        if self.lane not in {
            "SOURCE_OPERATIONAL",
            "QUERY_FACET_PROMOTION_OPERATIONAL",
            "WARM_TARGET_OPERATIONAL",
            "C2_BASE_RESET_CONTROL",
            "CONDITIONAL_DIRECT_OPERATIONAL",
        }:
            raise DurableMultiQueryWorkloadInvariantViolation(
                "V0-056 trace lane changed"
            )
        if self.occurrence_id is not None:
            _cid(self.occurrence_id, "trace occurrence")
        for name in (
            "query_facet_value_builder_calls",
            "query_facet_identity_hits",
            "fresh_query_root_builder_calls",
            "exact_ground_transition_calls",
            "exact_action_catalogue_calls",
            "direct_policy_evaluations",
            "direct_optimizer_calls",
            "process_launches",
            "observed_query_store_read_bytes",
            "observed_query_store_output_bytes",
            "source_checkpoint_unique_bytes",
        ):
            _integer(getattr(self, name), f"trace {name}")
        if (
            self.query_store_io_complete is not False
            or self.full_counter_registry_complete is not False
        ):
            raise DurableMultiQueryWorkloadInvariantViolation(
                "V0-056 scoped accounting classification changed"
            )
        occurrence_lanes = {
            "WARM_TARGET_OPERATIONAL",
            "C2_BASE_RESET_CONTROL",
            "CONDITIONAL_DIRECT_OPERATIONAL",
        }
        if (self.lane in occurrence_lanes) != (self.occurrence_id is not None):
            raise DurableMultiQueryWorkloadInvariantViolation(
                "V0-056 trace occurrence scope changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h2_durable_multiquery_scoped_trace.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "lane": self.lane,
            "occurrence_id": (
                self.occurrence_id
                if self.occurrence_id is not None
                else {
                    "kind": "NOT_APPLICABLE",
                    "reason": "CAMPAIGN_PREFIX",
                }
            ),
            "query_facet_value_builder_calls": (
                self.query_facet_value_builder_calls
            ),
            "query_facet_identity_hits": self.query_facet_identity_hits,
            "fresh_query_root_builder_calls": (
                self.fresh_query_root_builder_calls
            ),
            "exact_ground_transition_calls": (
                self.exact_ground_transition_calls
            ),
            "exact_action_catalogue_calls": self.exact_action_catalogue_calls,
            "direct_policy_evaluations": self.direct_policy_evaluations,
            "direct_optimizer_calls": self.direct_optimizer_calls,
            "process_launches": self.process_launches,
            "observed_query_store_read_bytes": (
                self.observed_query_store_read_bytes
            ),
            "observed_query_store_output_bytes": (
                self.observed_query_store_output_bytes
            ),
            "source_checkpoint_unique_bytes": (
                self.source_checkpoint_unique_bytes
            ),
            "query_store_io_complete": self.query_store_io_complete,
            "full_counter_registry_complete": (
                self.full_counter_registry_complete
            ),
        }

    @property
    def trace_id(self) -> str:
        return _content_id("trace", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "trace_id": self.trace_id}


@dataclass(frozen=True, slots=True)
class ConditionalOfflineBaseEquivalenceV1:
    source_first_model_id: str
    source_fixture_id: str
    direct_offline_base_id: str
    ordered_source_ground_row_ids: tuple[str, ...]
    ordered_direct_ground_row_ids: tuple[str, ...]
    exact_row_projection_match: bool
    direct_base_ground_calls_charged_per_occurrence: bool

    def __post_init__(self) -> None:
        for value in (
            self.source_first_model_id,
            self.source_fixture_id,
            self.direct_offline_base_id,
            *self.ordered_source_ground_row_ids,
            *self.ordered_direct_ground_row_ids,
        ):
            _cid(value, "offline equivalence identity")
        if (
            type(self.ordered_source_ground_row_ids) is not tuple
            or type(self.ordered_direct_ground_row_ids) is not tuple
            or len(self.ordered_source_ground_row_ids) != 4
            or self.ordered_source_ground_row_ids
            != self.ordered_direct_ground_row_ids
            or self.exact_row_projection_match is not True
            or self.direct_base_ground_calls_charged_per_occurrence is not False
        ):
            raise DurableMultiQueryWorkloadInvariantViolation(
                "conditional-direct offline-base equivalence changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.h2_durable_multiquery_offline_base_equivalence.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "source_first_model_id": self.source_first_model_id,
            "source_fixture_id": self.source_fixture_id,
            "direct_offline_base_id": self.direct_offline_base_id,
            "ordered_source_ground_row_ids": list(
                self.ordered_source_ground_row_ids
            ),
            "ordered_direct_ground_row_ids": list(
                self.ordered_direct_ground_row_ids
            ),
            "exact_row_projection_match": self.exact_row_projection_match,
            "direct_base_ground_calls_charged_per_occurrence": (
                self.direct_base_ground_calls_charged_per_occurrence
            ),
        }

    @property
    def proof_id(self) -> str:
        return _content_id("offline_equivalence", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "proof_id": self.proof_id}


@dataclass(frozen=True, slots=True)
class MatchedDurableMultiQueryOccurrenceV1:
    occurrence: query_family.H2QueryFamilyOccurrenceV1
    query: query_family.H2QueryFamilyQueryV1
    warm: query_family.H2QueryFamilyOccurrenceResultV1
    base_reset_initialization: query_family.H2QueryFamilyInitializationV1
    base_reset: query_family.H2QueryFamilyOccurrenceResultV1
    direct_result: direct.ConditionalDirectGroundResultV1
    warm_trace: V0056ScopedOperationalTraceV1
    base_reset_trace: V0056ScopedOperationalTraceV1
    direct_trace: V0056ScopedOperationalTraceV1
    exact_warm_reset_certificate_match: bool = True
    exact_selected_action_match: bool = True
    exact_reward_match: bool = True
    exact_failure_match: bool = True
    exact_regret_match: bool = True
    exact_certificate_status_match: bool = True

    def __post_init__(self) -> None:
        if (
            type(self.occurrence)
            is not query_family.H2QueryFamilyOccurrenceV1
            or type(self.query) is not query_family.H2QueryFamilyQueryV1
            or type(self.warm)
            is not query_family.H2QueryFamilyOccurrenceResultV1
            or type(self.base_reset_initialization)
            is not query_family.H2QueryFamilyInitializationV1
            or type(self.base_reset)
            is not query_family.H2QueryFamilyOccurrenceResultV1
            or type(self.direct_result)
            is not direct.ConditionalDirectGroundResultV1
            or type(self.warm_trace) is not V0056ScopedOperationalTraceV1
            or type(self.base_reset_trace) is not V0056ScopedOperationalTraceV1
            or type(self.direct_trace) is not V0056ScopedOperationalTraceV1
        ):
            raise DurableMultiQueryWorkloadInvariantViolation(
                "matched occurrence rejects substituted artifacts"
            )
        self.occurrence.__post_init__()
        self.query.__post_init__()
        self.warm.__post_init__()
        self.base_reset_initialization.__post_init__()
        self.base_reset_initialization.commit.__post_init__()
        self.base_reset.__post_init__()
        direct.require_conditional_direct_ground_result_v1(
            self.direct_result
        )
        self.warm_trace.__post_init__()
        self.base_reset_trace.__post_init__()
        self.direct_trace.__post_init__()
        for value in (
            self.exact_warm_reset_certificate_match,
            self.exact_selected_action_match,
            self.exact_reward_match,
            self.exact_failure_match,
            self.exact_regret_match,
            self.exact_certificate_status_match,
        ):
            if value is not True:
                raise DurableMultiQueryWorkloadInvariantViolation(
                    "matched occurrence semantic equality changed"
                )
        if (
            self.occurrence.query_id != self.query.query_id
            or self.warm.occurrence_id != self.occurrence.occurrence_id
            or self.base_reset.occurrence_id != self.occurrence.occurrence_id
            or self.base_reset_initialization.commit.commit_id
            != self.base_reset.before_commit_id
            or self.direct_result.occurrence_id
            != self.occurrence.occurrence_id
            or self.warm.query_id != self.query.query_id
            or self.base_reset.query_id != self.query.query_id
            or self.direct_result.query_id != self.query.query_id
            or self.warm.certificate.to_document()
            != self.base_reset.certificate.to_document()
            or self.warm.certificate.selected_action
            != self.direct_result.selected_action
            or self.warm.certificate.reward_lower
            != self.direct_result.reward
            or self.warm.certificate.failure_upper
            != self.direct_result.failure_probability
            or self.warm.certificate.normalized_regret
            != self.direct_result.normalized_regret
            or self.warm.certificate.certified
            is not self.direct_result.certified
            or self.warm_trace.occurrence_id
            != self.occurrence.occurrence_id
            or self.base_reset_trace.occurrence_id
            != self.occurrence.occurrence_id
            or self.direct_trace.occurrence_id
            != self.occurrence.occurrence_id
        ):
            raise DurableMultiQueryWorkloadInvariantViolation(
                "warm/reset/direct occurrence binding differs"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h2_durable_multiquery_matched_occurrence.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "occurrence": self.occurrence.to_document(),
            "query": self.query.to_document(),
            "warm": self.warm.to_document(),
            "base_reset_initialization": (
                self.base_reset_initialization.to_document()
            ),
            "base_reset": self.base_reset.to_document(),
            "direct_result": self.direct_result.to_document(),
            "warm_trace": self.warm_trace.to_document(),
            "base_reset_trace": self.base_reset_trace.to_document(),
            "direct_trace": self.direct_trace.to_document(),
            "exact_warm_reset_certificate_match": (
                self.exact_warm_reset_certificate_match
            ),
            "exact_selected_action_match": self.exact_selected_action_match,
            "exact_reward_match": self.exact_reward_match,
            "exact_failure_match": self.exact_failure_match,
            "exact_regret_match": self.exact_regret_match,
            "exact_certificate_status_match": (
                self.exact_certificate_status_match
            ),
        }

    @property
    def matched_id(self) -> str:
        return _content_id("matched", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "matched_id": self.matched_id}


@dataclass(frozen=True, slots=True)
class DurableMultiQueryPrefixV1:
    prefix_length: int
    occurrence_ids: tuple[str, ...]
    warm_source_inclusive_ground_calls: int
    warm_source_inclusive_process_launches: int
    warm_query_facet_builder_calls: int
    warm_query_facet_identity_hits: int
    reset_source_inclusive_ground_calls: int
    reset_source_inclusive_process_launches: int
    reset_query_facet_builder_calls: int
    reset_query_facet_identity_hits: int
    direct_ground_calls: int
    direct_process_launches: int
    direct_policy_evaluations: int
    official_scalar_cost: None = None
    official_N_break_even: None = None
    scalar_gate_status: str = "NOT_RUN"

    def __post_init__(self) -> None:
        _integer(self.prefix_length, "prefix length", 1)
        if (
            type(self.occurrence_ids) is not tuple
            or len(self.occurrence_ids) != self.prefix_length
            or len(set(self.occurrence_ids)) != self.prefix_length
        ):
            raise DurableMultiQueryWorkloadInvariantViolation(
                "prefix occurrence IDs changed"
            )
        for value in self.occurrence_ids:
            _cid(value, "prefix occurrence")
        for name in (
            "warm_source_inclusive_ground_calls",
            "warm_source_inclusive_process_launches",
            "warm_query_facet_builder_calls",
            "warm_query_facet_identity_hits",
            "reset_source_inclusive_ground_calls",
            "reset_source_inclusive_process_launches",
            "reset_query_facet_builder_calls",
            "reset_query_facet_identity_hits",
            "direct_ground_calls",
            "direct_process_launches",
            "direct_policy_evaluations",
        ):
            _integer(getattr(self, name), f"prefix {name}")
        if (
            self.warm_source_inclusive_ground_calls != 1
            or self.reset_source_inclusive_ground_calls != 1
            or self.warm_source_inclusive_process_launches
            != 3 + self.prefix_length
            or self.reset_source_inclusive_process_launches
            != 3 + self.prefix_length
            or self.direct_ground_calls != self.prefix_length
            or self.direct_process_launches != self.prefix_length
            or self.direct_policy_evaluations != 4 * self.prefix_length
            or self.official_scalar_cost is not None
            or self.official_N_break_even is not None
            or self.scalar_gate_status != "NOT_RUN"
        ):
            raise DurableMultiQueryWorkloadInvariantViolation(
                "prefix source/direct accounting or scalar locks changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h2_durable_multiquery_prefix.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "prefix_length": self.prefix_length,
            "occurrence_ids": list(self.occurrence_ids),
            "warm_source_inclusive_ground_calls": (
                self.warm_source_inclusive_ground_calls
            ),
            "warm_source_inclusive_process_launches": (
                self.warm_source_inclusive_process_launches
            ),
            "warm_query_facet_builder_calls": (
                self.warm_query_facet_builder_calls
            ),
            "warm_query_facet_identity_hits": (
                self.warm_query_facet_identity_hits
            ),
            "reset_source_inclusive_ground_calls": (
                self.reset_source_inclusive_ground_calls
            ),
            "reset_source_inclusive_process_launches": (
                self.reset_source_inclusive_process_launches
            ),
            "reset_query_facet_builder_calls": (
                self.reset_query_facet_builder_calls
            ),
            "reset_query_facet_identity_hits": (
                self.reset_query_facet_identity_hits
            ),
            "direct_ground_calls": self.direct_ground_calls,
            "direct_process_launches": self.direct_process_launches,
            "direct_policy_evaluations": self.direct_policy_evaluations,
            "official_scalar_cost": self.official_scalar_cost,
            "official_N_break_even": self.official_N_break_even,
            "scalar_gate_status": self.scalar_gate_status,
        }

    @property
    def prefix_id(self) -> str:
        return _content_id("prefix", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "prefix_id": self.prefix_id}


@dataclass(frozen=True, slots=True)
class DurableMultiQueryTelemetryV1:
    registered_query_count: int
    logical_occurrence_count: int
    repeated_occurrence_count: int
    source_ground_calls: int
    source_process_launches: int
    warm_target_ground_calls: int
    warm_target_process_launches: int
    warm_query_facet_builder_calls: int
    warm_query_facet_identity_hits: int
    warm_fresh_query_roots: int
    reset_target_ground_calls: int
    reset_target_process_launches: int
    reset_query_facet_builder_calls: int
    reset_query_facet_identity_hits: int
    reset_fresh_query_roots: int
    direct_ground_calls: int
    direct_catalogue_calls: int
    direct_policy_evaluations: int
    direct_optimizer_calls: int
    direct_process_launches: int
    w0_logical_lower_count: int
    w1_logical_lower_count: int
    w2_logical_lower_count: int
    final_persisted_query_facet_count: int
    persisted_query_root_count: int

    def __post_init__(self) -> None:
        for name in self.__dataclass_fields__:
            _integer(getattr(self, name), f"telemetry {name}")
        expected = {
            "registered_query_count": 3,
            "logical_occurrence_count": 10,
            "repeated_occurrence_count": 7,
            "source_ground_calls": 1,
            "source_process_launches": 3,
            "warm_target_ground_calls": 0,
            "warm_target_process_launches": 10,
            "warm_query_facet_builder_calls": 6,
            "warm_query_facet_identity_hits": 174,
            "warm_fresh_query_roots": 30,
            "reset_target_ground_calls": 0,
            "reset_target_process_launches": 10,
            "reset_query_facet_builder_calls": 18,
            "reset_query_facet_identity_hits": 162,
            "reset_fresh_query_roots": 30,
            "direct_ground_calls": 10,
            "direct_catalogue_calls": 10,
            "direct_policy_evaluations": 40,
            "direct_optimizer_calls": 10,
            "direct_process_launches": 10,
            "w0_logical_lower_count": 18,
            "w1_logical_lower_count": 21,
            "w2_logical_lower_count": 24,
            "final_persisted_query_facet_count": 6,
            "persisted_query_root_count": 0,
        }
        if any(getattr(self, name) != value for name, value in expected.items()):
            raise DurableMultiQueryWorkloadInvariantViolation(
                "registered V0-056 telemetry changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h2_durable_multiquery_telemetry.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            **{
                name: getattr(self, name)
                for name in self.__dataclass_fields__
            },
        }

    @property
    def telemetry_id(self) -> str:
        return _content_id("telemetry", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "telemetry_id": self.telemetry_id}


@dataclass(frozen=True, slots=True)
class DurableMultiQueryClaimLocksV1:
    registered_finite_h2_multiquery_workload_claimed: bool = True
    preregistered_before_source_claimed: bool = True
    failed_proof_only_source_ground_claimed: bool = True
    model_only_target_occurrences_claimed: bool = True
    lazy_query_facet_lookup_claimed: bool = True
    matched_conditional_ground_control_claimed: bool = True
    operation_family_trace_claimed: bool = True
    generic_cross_query_reuse_claimed: bool = False
    reward_basis_reuse_claimed: bool = False
    query_dependent_policy_switch_claimed: bool = False
    generic_durable_persistence_claimed: bool = False
    generic_h_gt_1_claimed: bool = False
    horizon_greater_than_two_claimed: bool = False
    automatic_coordinate_invention_claimed: bool = False
    partial_dynamics_claimed: bool = False
    learned_dynamics_claimed: bool = False
    sample_efficiency_claimed: bool = False
    ground_transition_calls_are_samples: bool = False
    byte_savings_claimed: bool = False
    cpu_savings_claimed: bool = False
    wall_clock_savings_claimed: bool = False
    total_work_savings_claimed: bool = False
    native_compute_event_completeness_claimed: bool = False
    counter_registry_v1_complete_claimed: bool = False
    statistical_generalization_claimed: bool = False
    independent_algorithm_verifier_claimed: bool = False
    hostile_worker_security_claimed: bool = False
    official_execution_allowed: bool = False
    official_scalar_cost: None = None
    official_N_break_even: None = None
    workload_economics_gate: str = "WORKLOAD_ECONOMICS_GATE_NOT_RUN"
    counter_completeness_gate: str = "COUNTER_COMPLETENESS_GATE_NOT_RUN"
    sample_efficiency_gate: str = "SAMPLE_EFFICIENCY_GATE_NOT_RUN"

    def __post_init__(self) -> None:
        positives = (
            self.registered_finite_h2_multiquery_workload_claimed,
            self.preregistered_before_source_claimed,
            self.failed_proof_only_source_ground_claimed,
            self.model_only_target_occurrences_claimed,
            self.lazy_query_facet_lookup_claimed,
            self.matched_conditional_ground_control_claimed,
            self.operation_family_trace_claimed,
        )
        negatives = tuple(
            getattr(self, name)
            for name in (
                "generic_cross_query_reuse_claimed",
                "reward_basis_reuse_claimed",
                "query_dependent_policy_switch_claimed",
                "generic_durable_persistence_claimed",
                "generic_h_gt_1_claimed",
                "horizon_greater_than_two_claimed",
                "automatic_coordinate_invention_claimed",
                "partial_dynamics_claimed",
                "learned_dynamics_claimed",
                "sample_efficiency_claimed",
                "ground_transition_calls_are_samples",
                "byte_savings_claimed",
                "cpu_savings_claimed",
                "wall_clock_savings_claimed",
                "total_work_savings_claimed",
                "native_compute_event_completeness_claimed",
                "counter_registry_v1_complete_claimed",
                "statistical_generalization_claimed",
                "independent_algorithm_verifier_claimed",
                "hostile_worker_security_claimed",
                "official_execution_allowed",
            )
        )
        if (
            any(value is not True for value in positives)
            or any(value is not False for value in negatives)
            or self.official_scalar_cost is not None
            or self.official_N_break_even is not None
            or self.workload_economics_gate
            != "WORKLOAD_ECONOMICS_GATE_NOT_RUN"
            or self.counter_completeness_gate
            != "COUNTER_COMPLETENESS_GATE_NOT_RUN"
            or self.sample_efficiency_gate
            != "SAMPLE_EFFICIENCY_GATE_NOT_RUN"
        ):
            raise DurableMultiQueryWorkloadInvariantViolation(
                "V0-056 claim locks changed"
            )

    def to_document(self) -> dict[str, Any]:
        return {
            name: getattr(self, name)
            for name in self.__dataclass_fields__
        }


EXPECTED_CAMPAIGN_EVENTS = (
    "WORKLOAD_PROTOCOL_FROZEN_BEFORE_SOURCE",
    "V0055_SOURCE_STARTED_WITHOUT_WORKLOAD_INPUT",
    "V0055_FAILED_PROOF_VERIFIED_BEFORE_GROUND",
    "V0055_ONE_OWNER_BOUND_M_ROW_ACQUIRED",
    "V0055_C2_CERTIFICATE_FROZEN",
    "QUERY_FACET_W0_PROMOTED_ROOT_FREE",
    "TEN_FRESH_WARM_TARGETS_COMPLETED_ZERO_GROUND",
    "TEN_FRESH_C2_BASE_RESET_CONTROLS_COMPLETED_ZERO_GROUND",
    "TEN_FRESH_SOURCE_BLIND_DIRECT_CONTROLS_COMPLETED",
    "ALL_MATCHED_OCCURRENCES_AND_PREFIXES_FROZEN",
)


@dataclass(frozen=True, slots=True)
class DurableMultiQueryWorkloadResultV1:
    protocol: query_family.H2QueryFamilyProtocolV1
    preregistration: query_family.H2QueryFamilyPreregistrationV1
    source_result_id: str
    source_c1_commit_id: str
    source_c2_commit_id: str
    source_failed_verification_id: str
    source_ground_authorization_id: str
    offline_base_equivalence: ConditionalOfflineBaseEquivalenceV1
    w0_commit_id: str
    w1_commit_id: str
    w2_commit_id: str
    warm_final_commit_id: str
    source_trace: V0056ScopedOperationalTraceV1
    promotion_trace: V0056ScopedOperationalTraceV1
    warm_occurrences: tuple[query_family.H2QueryFamilyOccurrenceResultV1, ...]
    base_reset_initializations: tuple[
        query_family.H2QueryFamilyInitializationV1, ...
    ]
    base_reset_occurrences: tuple[
        query_family.H2QueryFamilyOccurrenceResultV1, ...
    ]
    direct_occurrences: tuple[direct.ConditionalDirectGroundResultV1, ...]
    matched_occurrences: tuple[MatchedDurableMultiQueryOccurrenceV1, ...]
    prefixes: tuple[DurableMultiQueryPrefixV1, ...]
    telemetry: DurableMultiQueryTelemetryV1
    campaign_snapshot_id: str
    events: tuple[str, ...]
    claim_locks: DurableMultiQueryClaimLocksV1
    status: str = SUCCESS_STATUS
    _source_result: Any = field(default=None, repr=False, compare=False)
    _instance_mint: RuntimeAuthorityMintV1 | None = field(
        default=None,
        repr=False,
        compare=False,
    )

    def __post_init__(self) -> None:
        if (
            type(self.protocol) is not query_family.H2QueryFamilyProtocolV1
            or type(self.preregistration)
            is not query_family.H2QueryFamilyPreregistrationV1
            or type(self.source_trace) is not V0056ScopedOperationalTraceV1
            or type(self.promotion_trace) is not V0056ScopedOperationalTraceV1
            or type(self.offline_base_equivalence)
            is not ConditionalOfflineBaseEquivalenceV1
            or type(self.telemetry) is not DurableMultiQueryTelemetryV1
            or type(self.claim_locks) is not DurableMultiQueryClaimLocksV1
            or type(self._source_result)
            is not recovery.DurableActionLocalRecoveryResultV1
        ):
            raise DurableMultiQueryWorkloadInvariantViolation(
                "V0-056 result rejects substituted source artifacts"
            )
        recovery.require_durable_action_local_recovery_result_v1(
            self._source_result
        )
        query_family.require_registered_h2_query_family_protocol_v1(
            self.protocol
        )
        self.preregistration.__post_init__()
        tuple_specs = (
            (
                self.warm_occurrences,
                query_family.H2QueryFamilyOccurrenceResultV1,
            ),
            (
                self.base_reset_initializations,
                query_family.H2QueryFamilyInitializationV1,
            ),
            (
                self.base_reset_occurrences,
                query_family.H2QueryFamilyOccurrenceResultV1,
            ),
            (
                self.direct_occurrences,
                direct.ConditionalDirectGroundResultV1,
            ),
            (
                self.matched_occurrences,
                MatchedDurableMultiQueryOccurrenceV1,
            ),
            (self.prefixes, DurableMultiQueryPrefixV1),
        )
        if any(
            type(values) is not tuple
            or len(values) != 10
            or any(type(item) is not expected for item in values)
            for values, expected in tuple_specs
        ):
            raise DurableMultiQueryWorkloadInvariantViolation(
                "V0-056 result occurrence cardinality/type changed"
            )
        for item in (*self.warm_occurrences, *self.base_reset_occurrences):
            item.__post_init__()
        for item in self.base_reset_initializations:
            item.__post_init__()
            item.commit.__post_init__()
        for item in self.direct_occurrences:
            direct.require_conditional_direct_ground_result_v1(item)
        for item in self.prefixes:
            item.__post_init__()
        for value in (
            self.source_result_id,
            self.source_c1_commit_id,
            self.source_c2_commit_id,
            self.source_failed_verification_id,
            self.source_ground_authorization_id,
            self.w0_commit_id,
            self.w1_commit_id,
            self.w2_commit_id,
            self.warm_final_commit_id,
            self.campaign_snapshot_id,
        ):
            _cid(value, "V0-056 result identity")
        protocol_occurrences = self.preregistration.occurrences
        expected_warm_chain = (
            (self.w0_commit_id, self.w0_commit_id, 18, 0),
            (self.w0_commit_id, self.w1_commit_id, 21, 3),
            (self.w1_commit_id, self.w2_commit_id, 24, 3),
            *((self.w2_commit_id, self.w2_commit_id, 24, 0),) * 7,
        )
        if tuple(
            (
                item.before_commit_id,
                item.after_commit_id,
                item.logical_lower_count,
                item.value_builder_calls,
            )
            for item in self.warm_occurrences
        ) != expected_warm_chain:
            raise DurableMultiQueryWorkloadInvariantViolation(
                "warm W0/W1/W2 commit chain changed"
            )
        if any(
            item.before_commit_id != self.w0_commit_id
            or item.value_builder_calls
            != (0 if item.query_index == 1 else 3)
            for item in self.base_reset_occurrences
        ):
            raise DurableMultiQueryWorkloadInvariantViolation(
                "C2-base-reset arm did not restart from W0"
            )
        if any(
            item.commit.commit_id != self.w0_commit_id
            or item.source_lease_id
            != self.base_reset_initializations[0].source_lease_id
            or item.read_bytes
            != self.base_reset_initializations[0].read_bytes
            or item.output_bytes
            != self.base_reset_initializations[0].output_bytes
            for item in self.base_reset_initializations
        ):
            raise DurableMultiQueryWorkloadInvariantViolation(
                "C2-base-reset initialization identity/accounting changed"
            )
        for index, matched in enumerate(self.matched_occurrences):
            matched.__post_init__()
            if (
                matched.warm.to_document()
                != self.warm_occurrences[index].to_document()
                or matched.base_reset_initialization.to_document()
                != self.base_reset_initializations[index].to_document()
                or matched.base_reset.to_document()
                != self.base_reset_occurrences[index].to_document()
                or matched.direct_result.to_document()
                != self.direct_occurrences[index].to_document()
                or matched.warm_trace.to_document()
                != _model_trace(
                    "WARM_TARGET_OPERATIONAL",
                    protocol_occurrences[index],
                    self.warm_occurrences[index],
                ).to_document()
                or matched.base_reset_trace.to_document()
                != _model_trace(
                    "C2_BASE_RESET_CONTROL",
                    protocol_occurrences[index],
                    self.base_reset_occurrences[index],
                    self.base_reset_initializations[index],
                ).to_document()
                or matched.direct_trace.to_document()
                != _direct_trace(
                    protocol_occurrences[index],
                    self.direct_occurrences[index],
                ).to_document()
            ):
                raise DurableMultiQueryWorkloadInvariantViolation(
                    "matched occurrence differs from top-level arm artifacts"
                )
        if (
            self.status != SUCCESS_STATUS
            or self.events != EXPECTED_CAMPAIGN_EVENTS
            or self.preregistration.to_document()
            != query_family.registered_h2_query_family_preregistration_v1().to_document()
            or self.preregistration.protocol.to_document()
            != self.protocol.to_document()
            or self.source_result_id != self._source_result.result_id
            or self.source_c1_commit_id != self._source_result.c1_commit_id
            or self.source_c2_commit_id != self._source_result.c2_commit_id
            or self.source_failed_verification_id
            != self._source_result.failed_verification.verification_id
            or self.source_ground_authorization_id
            != self._source_result.ground_authorization.authorization_id
            or self.offline_base_equivalence.to_document()
            != _offline_base_equivalence(
                self._source_result
            ).to_document()
            or self.source_c2_commit_id
            != query_family.SOURCE_C2_COMMIT_ID
            or self.warm_final_commit_id != self.w2_commit_id
            or tuple(item.occurrence_id for item in self.warm_occurrences)
            != tuple(item.occurrence_id for item in protocol_occurrences)
            or tuple(
                item.occurrence_id for item in self.base_reset_occurrences
            )
            != tuple(item.occurrence_id for item in protocol_occurrences)
            or tuple(item.occurrence_id for item in self.direct_occurrences)
            != tuple(item.occurrence_id for item in protocol_occurrences)
            or tuple(
                item.occurrence.occurrence_id
                for item in self.matched_occurrences
            )
            != tuple(item.occurrence_id for item in protocol_occurrences)
            or tuple(item.prefix_length for item in self.prefixes)
            != tuple(range(1, 11))
            or tuple(item.to_document() for item in self.prefixes)
            != tuple(
                item.to_document()
                for item in _prefixes(self.matched_occurrences)
            )
            or self.telemetry.to_document()
            != _telemetry(self.matched_occurrences).to_document()
            or self.source_trace.lane != "SOURCE_OPERATIONAL"
            or self.source_trace.exact_ground_transition_calls != 1
            or self.source_trace.process_launches != 3
            or self.source_trace.source_checkpoint_unique_bytes <= 0
            or self.source_trace.observed_query_store_read_bytes != 0
            or self.source_trace.observed_query_store_output_bytes != 0
            or self.promotion_trace.lane
            != "QUERY_FACET_PROMOTION_OPERATIONAL"
            or self.promotion_trace.query_facet_value_builder_calls != 0
            or self.promotion_trace.query_facet_identity_hits != 0
            or self.promotion_trace.fresh_query_root_builder_calls != 0
            or self.promotion_trace.exact_ground_transition_calls != 0
            or self.promotion_trace.process_launches != 0
            or self.promotion_trace.observed_query_store_read_bytes <= 0
            or self.promotion_trace.observed_query_store_output_bytes <= 0
            or self.promotion_trace.observed_query_store_read_bytes
            != self.base_reset_initializations[0].read_bytes
            or self.promotion_trace.observed_query_store_output_bytes
            != self.base_reset_initializations[0].output_bytes
        ):
            raise DurableMultiQueryWorkloadInvariantViolation(
                "V0-056 result source/order/commit chain changed"
            )
        self.telemetry.__post_init__()
        self.offline_base_equivalence.__post_init__()
        self.claim_locks.__post_init__()

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h2_durable_multiquery_workload_result.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "status": self.status,
            "protocol": self.protocol.to_document(),
            "preregistration": self.preregistration.to_document(),
            "source_result_id": self.source_result_id,
            "source_c1_commit_id": self.source_c1_commit_id,
            "source_c2_commit_id": self.source_c2_commit_id,
            "source_failed_verification_id": (
                self.source_failed_verification_id
            ),
            "source_ground_authorization_id": (
                self.source_ground_authorization_id
            ),
            "offline_base_equivalence": (
                self.offline_base_equivalence.to_document()
            ),
            "w0_commit_id": self.w0_commit_id,
            "w1_commit_id": self.w1_commit_id,
            "w2_commit_id": self.w2_commit_id,
            "warm_final_commit_id": self.warm_final_commit_id,
            "source_trace": self.source_trace.to_document(),
            "promotion_trace": self.promotion_trace.to_document(),
            "warm_occurrences": [
                item.to_document() for item in self.warm_occurrences
            ],
            "base_reset_initializations": [
                item.to_document()
                for item in self.base_reset_initializations
            ],
            "base_reset_occurrences": [
                item.to_document() for item in self.base_reset_occurrences
            ],
            "direct_occurrences": [
                item.to_document() for item in self.direct_occurrences
            ],
            "matched_occurrences": [
                item.to_document() for item in self.matched_occurrences
            ],
            "prefixes": [item.to_document() for item in self.prefixes],
            "telemetry": self.telemetry.to_document(),
            "campaign_snapshot_id": self.campaign_snapshot_id,
            "events": list(self.events),
            "claim_locks": self.claim_locks.to_document(),
        }

    @property
    def result_id(self) -> str:
        _CANONICAL_RESULT_REQUIRE(self)
        return _content_id("result", self._payload())

    def to_document(self) -> dict[str, Any]:
        _CANONICAL_RESULT_REQUIRE(self)
        return {**self._payload(), "result_id": self.result_id}


_RESULT_ISSUER = object()
_VERIFICATION_ISSUER = object()
_CANONICAL_BIND_RUNTIME_AUTHORITY = bind_runtime_authority_v1
_CANONICAL_REQUIRE_RUNTIME_AUTHORITY = require_runtime_authority_v1


def require_durable_multiquery_workload_result_v1(
    result: DurableMultiQueryWorkloadResultV1,
) -> DurableMultiQueryWorkloadResultV1:
    if type(result) is not DurableMultiQueryWorkloadResultV1:
        raise DurableMultiQueryWorkloadInvariantViolation(
            "V0-056 result rejects substituted types"
        )
    try:
        _CANONICAL_REQUIRE_RUNTIME_AUTHORITY(result, issuer=_RESULT_ISSUER)
    except ValueError as error:
        raise DurableMultiQueryWorkloadInvariantViolation(
            "V0-056 result lacks live producer authority"
        ) from error
    result.__post_init__()
    return result


_CANONICAL_RESULT_REQUIRE = require_durable_multiquery_workload_result_v1


def _query_for_occurrence(
    protocol: query_family.H2QueryFamilyProtocolV1,
    occurrence: query_family.H2QueryFamilyOccurrenceV1,
) -> query_family.H2QueryFamilyQueryV1:
    try:
        query = protocol.queries[occurrence.query_index - 1]
    except (IndexError, TypeError) as error:
        raise DurableMultiQueryWorkloadInvariantViolation(
            "occurrence query index is outside the preregistered family"
        ) from error
    if query.query_id != occurrence.query_id:
        raise DurableMultiQueryWorkloadInvariantViolation(
            "occurrence query ID differs from preregistration"
        )
    return query


def _model_trace(
    lane: str,
    occurrence: query_family.H2QueryFamilyOccurrenceV1,
    result: query_family.H2QueryFamilyOccurrenceResultV1,
    reset_initialization: (
        query_family.H2QueryFamilyInitializationV1 | None
    ) = None,
) -> V0056ScopedOperationalTraceV1:
    if lane == "C2_BASE_RESET_CONTROL":
        if (
            type(reset_initialization)
            is not query_family.H2QueryFamilyInitializationV1
            or reset_initialization.commit.commit_id
            != result.before_commit_id
        ):
            raise DurableMultiQueryWorkloadInvariantViolation(
                "reset trace lacks its bound W0 initialization"
            )
        reset_initialization.__post_init__()
        initialization_read_bytes = reset_initialization.read_bytes
        initialization_output_bytes = reset_initialization.output_bytes
    else:
        if reset_initialization is not None:
            raise DurableMultiQueryWorkloadInvariantViolation(
                "non-reset trace cannot charge reset initialization"
            )
        initialization_read_bytes = 0
        initialization_output_bytes = 0
    return V0056ScopedOperationalTraceV1(
        lane,
        occurrence.occurrence_id,
        result.value_builder_calls,
        result.identity_hits,
        result.fresh_root_builder_calls,
        result.ground_transition_calls,
        0,
        0,
        0,
        result.process_launches,
        initialization_read_bytes + result.store_read_bytes,
        initialization_output_bytes + result.store_output_bytes,
    )


def _direct_trace(
    occurrence: query_family.H2QueryFamilyOccurrenceV1,
    result: direct.ConditionalDirectGroundResultV1,
) -> V0056ScopedOperationalTraceV1:
    return V0056ScopedOperationalTraceV1(
        "CONDITIONAL_DIRECT_OPERATIONAL",
        occurrence.occurrence_id,
        0,
        0,
        0,
        result.exact_ground_transition_calls,
        result.exact_action_catalogue_calls,
        result.policy_evaluations,
        result.optimizer_calls,
        result.process_launches,
        0,
        0,
    )


def _match_occurrence(
    protocol: query_family.H2QueryFamilyProtocolV1,
    occurrence: query_family.H2QueryFamilyOccurrenceV1,
    warm: query_family.H2QueryFamilyOccurrenceResultV1,
    base_reset_initialization: query_family.H2QueryFamilyInitializationV1,
    base_reset: query_family.H2QueryFamilyOccurrenceResultV1,
    direct_result: direct.ConditionalDirectGroundResultV1,
) -> MatchedDurableMultiQueryOccurrenceV1:
    query = _query_for_occurrence(protocol, occurrence)
    warm_trace = _model_trace(
        "WARM_TARGET_OPERATIONAL", occurrence, warm
    )
    reset_trace = _model_trace(
        "C2_BASE_RESET_CONTROL",
        occurrence,
        base_reset,
        base_reset_initialization,
    )
    direct_trace = _direct_trace(occurrence, direct_result)
    return MatchedDurableMultiQueryOccurrenceV1(
        occurrence,
        query,
        warm,
        base_reset_initialization,
        base_reset,
        direct_result,
        warm_trace,
        reset_trace,
        direct_trace,
    )


def _prefixes(
    matched: tuple[MatchedDurableMultiQueryOccurrenceV1, ...],
) -> tuple[DurableMultiQueryPrefixV1, ...]:
    if (
        type(matched) is not tuple
        or len(matched) != 10
        or any(
            type(item) is not MatchedDurableMultiQueryOccurrenceV1
            for item in matched
        )
    ):
        raise DurableMultiQueryWorkloadInvariantViolation(
            "prefix builder requires ten matched occurrences"
        )
    result: list[DurableMultiQueryPrefixV1] = []
    for length in range(1, 11):
        prefix = matched[:length]
        result.append(
            DurableMultiQueryPrefixV1(
                length,
                tuple(item.occurrence.occurrence_id for item in prefix),
                1,
                3 + length,
                sum(
                    item.warm_trace.query_facet_value_builder_calls
                    for item in prefix
                ),
                sum(
                    item.warm_trace.query_facet_identity_hits
                    for item in prefix
                ),
                1,
                3 + length,
                sum(
                    item.base_reset_trace.query_facet_value_builder_calls
                    for item in prefix
                ),
                sum(
                    item.base_reset_trace.query_facet_identity_hits
                    for item in prefix
                ),
                sum(
                    item.direct_trace.exact_ground_transition_calls
                    for item in prefix
                ),
                sum(item.direct_trace.process_launches for item in prefix),
                sum(
                    item.direct_trace.direct_policy_evaluations
                    for item in prefix
                ),
            )
        )
    return tuple(result)


def _telemetry(
    matched: tuple[MatchedDurableMultiQueryOccurrenceV1, ...],
) -> DurableMultiQueryTelemetryV1:
    return DurableMultiQueryTelemetryV1(
        3,
        10,
        7,
        1,
        3,
        sum(
            item.warm_trace.exact_ground_transition_calls for item in matched
        ),
        sum(item.warm_trace.process_launches for item in matched),
        sum(
            item.warm_trace.query_facet_value_builder_calls
            for item in matched
        ),
        sum(item.warm_trace.query_facet_identity_hits for item in matched),
        sum(
            item.warm_trace.fresh_query_root_builder_calls
            for item in matched
        ),
        sum(
            item.base_reset_trace.exact_ground_transition_calls
            for item in matched
        ),
        sum(item.base_reset_trace.process_launches for item in matched),
        sum(
            item.base_reset_trace.query_facet_value_builder_calls
            for item in matched
        ),
        sum(
            item.base_reset_trace.query_facet_identity_hits
            for item in matched
        ),
        sum(
            item.base_reset_trace.fresh_query_root_builder_calls
            for item in matched
        ),
        sum(
            item.direct_trace.exact_ground_transition_calls
            for item in matched
        ),
        sum(
            item.direct_trace.exact_action_catalogue_calls
            for item in matched
        ),
        sum(
            item.direct_trace.direct_policy_evaluations for item in matched
        ),
        sum(item.direct_trace.direct_optimizer_calls for item in matched),
        sum(item.direct_trace.process_launches for item in matched),
        18,
        21,
        24,
        6,
        0,
    )


def _tree_unique_bytes(root: Path) -> int:
    """Provenance footprint only; never returned as read/output traffic."""

    if not root.is_dir() or root.is_symlink():
        raise DurableMultiQueryWorkloadInvariantViolation(
            "source footprint root is invalid"
        )
    total = 0
    for path in root.rglob("*"):
        if path.is_symlink():
            raise DurableMultiQueryWorkloadInvariantViolation(
                "source footprint contains a symlink"
            )
        if path.is_dir():
            continue
        stat = path.stat()
        if not path.is_file() or stat.st_nlink != 1:
            raise DurableMultiQueryWorkloadInvariantViolation(
                "source footprint contains a non-unique regular file"
            )
        total += stat.st_size
    return total


def _offline_base_equivalence(
    source: recovery.DurableActionLocalRecoveryResultV1,
) -> ConditionalOfflineBaseEquivalenceV1:
    recovery.require_durable_action_local_recovery_result_v1(source)
    live = source._source_result
    direct_document = direct.conditional_direct_offline_base_document_v1()
    rows = direct_document["rows"]
    if type(rows) is not list or len(rows) != 4:
        raise DurableMultiQueryWorkloadInvariantViolation(
            "conditional-direct offline base is not four rows"
        )
    source_rows: list[dict[str, Any]] = []
    for evidence in live.first_model.observed_rows:
        action = live.fixture.action(evidence.name)
        tile_text = action.action_key.split("=", 1)
        if len(tile_text) != 2 or tile_text[0] != "tile":
            raise DurableMultiQueryWorkloadInvariantViolation(
                "source C1 action key is not canonical"
            )
        source_rows.append(
            {
                "name": evidence.name.value,
                "state_key": (
                    "x0"
                    if evidence.state_id == live.fixture.initial_state.state_id
                    else "x1"
                ),
                "state_id": evidence.state_id,
                "tile": int(tile_text[1]),
                "action_key": action.action_key,
                "action_id": evidence.action_id,
                "ground_row_id": evidence.ground_row_id,
                "reward": {
                    "numerator": evidence.reward.numerator,
                    "denominator": evidence.reward.denominator,
                },
                "failure": evidence.failure,
                "terminal": evidence.terminal,
                "lane": evidence.lane.value,
            }
        )
    if source_rows != rows:
        raise DurableMultiQueryWorkloadInvariantViolation(
            "conditional-direct offline base differs from source C1"
        )
    source_ids = tuple(item["ground_row_id"] for item in source_rows)
    direct_ids = tuple(item["ground_row_id"] for item in rows)
    return ConditionalOfflineBaseEquivalenceV1(
        live.first_model.model_id,
        live.fixture.fixture_id,
        direct_document["offline_base_id"],
        source_ids,
        direct_ids,
        True,
        direct_document["offline_ground_work_charged_per_occurrence"],
    )


@dataclass(frozen=True, slots=True)
class DurableMultiQueryWorkloadVerificationV1:
    claimed_result_id: str
    replayed_result_id: str
    exact_document_match: bool
    original_store_unchanged: bool
    protocol_reconstructed_before_replay_source: bool
    evaluation_lane_only: bool
    included_in_operational_work: bool
    same_implementation_replay: bool
    independent_algorithm: bool
    evaluation_ground_transition_calls: int
    evaluation_process_launches: int
    _instance_mint: RuntimeAuthorityMintV1 | None = field(
        default=None,
        repr=False,
        compare=False,
    )

    def __post_init__(self) -> None:
        _cid(self.claimed_result_id, "verification claimed result")
        _cid(self.replayed_result_id, "verification replayed result")
        if (
            self.claimed_result_id != self.replayed_result_id
            or self.exact_document_match is not True
            or self.original_store_unchanged is not True
            or self.protocol_reconstructed_before_replay_source is not True
            or self.evaluation_lane_only is not True
            or self.included_in_operational_work is not False
            or self.same_implementation_replay is not True
            or self.independent_algorithm is not False
            or self.evaluation_ground_transition_calls != 11
            or self.evaluation_process_launches != 33
        ):
            raise DurableMultiQueryWorkloadInvariantViolation(
                "V0-056 verification classification changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h2_durable_multiquery_workload_verification.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "claimed_result_id": self.claimed_result_id,
            "replayed_result_id": self.replayed_result_id,
            "exact_document_match": self.exact_document_match,
            "original_store_unchanged": self.original_store_unchanged,
            "protocol_reconstructed_before_replay_source": (
                self.protocol_reconstructed_before_replay_source
            ),
            "evaluation_lane_only": self.evaluation_lane_only,
            "included_in_operational_work": (
                self.included_in_operational_work
            ),
            "same_implementation_replay": self.same_implementation_replay,
            "independent_algorithm": self.independent_algorithm,
            "evaluation_ground_transition_calls": (
                self.evaluation_ground_transition_calls
            ),
            "evaluation_process_launches": self.evaluation_process_launches,
        }

    @property
    def report_id(self) -> str:
        _CANONICAL_VERIFICATION_REQUIRE(self)
        return _content_id("verification", self._payload())

    def to_document(self) -> dict[str, Any]:
        _CANONICAL_VERIFICATION_REQUIRE(self)
        return {**self._payload(), "report_id": self.report_id}


def require_durable_multiquery_workload_verification_v1(
    report: DurableMultiQueryWorkloadVerificationV1,
) -> DurableMultiQueryWorkloadVerificationV1:
    if type(report) is not DurableMultiQueryWorkloadVerificationV1:
        raise DurableMultiQueryWorkloadInvariantViolation(
            "V0-056 verifier rejects substituted types"
        )
    try:
        _CANONICAL_REQUIRE_RUNTIME_AUTHORITY(
            report,
            issuer=_VERIFICATION_ISSUER,
        )
    except ValueError as error:
        raise DurableMultiQueryWorkloadInvariantViolation(
            "V0-056 verification lacks live verifier authority"
        ) from error
    report.__post_init__()
    return report


_CANONICAL_VERIFICATION_REQUIRE = (
    require_durable_multiquery_workload_verification_v1
)


_CANONICAL_RECOVERY_RUN = (
    recovery.run_registered_h2_durable_action_local_recovery_v1
)
_CANONICAL_RECOVERY_REQUIRE = (
    recovery.require_durable_action_local_recovery_result_v1
)
_CANONICAL_QUERY_PROTOCOL = (
    query_family.registered_h2_query_family_protocol_v1
)
_CANONICAL_QUERY_PREREGISTRATION = (
    query_family.registered_h2_query_family_preregistration_v1
)
_CANONICAL_QUERY_INITIALIZE_W0 = (
    query_family.initialize_h2_query_family_w0_v1
)
_CANONICAL_QUERY_LAUNCH = (
    query_family.launch_h2_query_family_occurrence_fresh_worker_v1
)
_CANONICAL_QUERY_LOAD_STORE = (
    query_family.load_verified_h2_query_family_store_v1
)
_CANONICAL_DIRECT_LAUNCH = (
    direct.run_h2_conditional_direct_ground_fresh_worker_v1
)
_CANONICAL_DIRECT_REQUIRE_LAUNCH = direct.require_conditional_direct_launch_v1


def _id_vector_pin(role: str, values: tuple[str, ...]) -> str:
    for value in values:
        _cid(value, f"{role} vector item")
    return _content_id(
        "snapshot",
        {
            "schema": "acfqp.h2_durable_multiquery_id_vector.v1",
            "schema_version": SCHEMA_VERSION,
            "role": role,
            "ids": list(values),
        },
    )


def _visible_canonical_result_ids(
    result: DurableMultiQueryWorkloadResultV1,
) -> dict[str, str]:
    return {
        "protocol": result.protocol.protocol_id,
        "proof_semantics": result.protocol.proof_semantics_id,
        "preregistration": result.preregistration.preregistration_id,
        **{
            f"query_{index}": query.query_id
            for index, query in enumerate(result.protocol.queries, 1)
        },
        "occurrences": _id_vector_pin(
            "REGISTERED_OCCURRENCES",
            tuple(
                item.occurrence_id
                for item in result.preregistration.occurrences
            ),
        ),
        "source_result": result.source_result_id,
        "source_c1_commit": result.source_c1_commit_id,
        "source_c2_commit": result.source_c2_commit_id,
        "source_failed_verification": result.source_failed_verification_id,
        "source_ground_authorization": (
            result.source_ground_authorization_id
        ),
        "offline_base_equivalence": (
            result.offline_base_equivalence.proof_id
        ),
        "direct_structural": direct.conditional_direct_structural_id_v1(),
        "direct_offline_base": direct.conditional_direct_offline_base_id_v1(),
        "w0_commit": result.w0_commit_id,
        "w1_commit": result.w1_commit_id,
        "w2_commit": result.w2_commit_id,
        "source_trace": result.source_trace.trace_id,
        "promotion_trace": result.promotion_trace.trace_id,
        "warm_occurrences": _id_vector_pin(
            "WARM_OCCURRENCE_RESULTS",
            tuple(item.result_id for item in result.warm_occurrences),
        ),
        "reset_occurrences": _id_vector_pin(
            "RESET_OCCURRENCE_RESULTS",
            tuple(item.result_id for item in result.base_reset_occurrences),
        ),
        "reset_initializations": _id_vector_pin(
            "RESET_INITIALIZATIONS",
            tuple(
                item.initialization_id
                for item in result.base_reset_initializations
            ),
        ),
        "direct_occurrences": _id_vector_pin(
            "DIRECT_OCCURRENCE_RESULTS",
            tuple(item.result_id for item in result.direct_occurrences),
        ),
        "matched_occurrences": _id_vector_pin(
            "MATCHED_OCCURRENCES",
            tuple(item.matched_id for item in result.matched_occurrences),
        ),
        "prefixes": _id_vector_pin(
            "PREFIXES",
            tuple(item.prefix_id for item in result.prefixes),
        ),
        "telemetry": result.telemetry.telemetry_id,
        "campaign_snapshot": result.campaign_snapshot_id,
        "campaign_result": result.result_id,
    }


def _assert_source_pins() -> None:
    authority_rows = (
        (
            query_family,
            "initialize_h2_query_family_w0_v1",
            _CANONICAL_QUERY_INITIALIZE_W0,
            EXPECTED_QUERY_INITIALIZE_SOURCE_SHA256,
        ),
        (
            query_family,
            "launch_h2_query_family_occurrence_fresh_worker_v1",
            _CANONICAL_QUERY_LAUNCH,
            EXPECTED_QUERY_LAUNCH_SOURCE_SHA256,
        ),
        (
            direct,
            "run_h2_conditional_direct_ground_fresh_worker_v1",
            _CANONICAL_DIRECT_LAUNCH,
            EXPECTED_DIRECT_LAUNCH_SOURCE_SHA256,
        ),
        (
            recovery,
            "run_registered_h2_durable_action_local_recovery_v1",
            _CANONICAL_RECOVERY_RUN,
            EXPECTED_SOURCE_RUN_SOURCE_SHA256,
        ),
    )
    changed_authority = any(
        getattr(module, name, None) is not authority
        or _callable_sha256(authority) != expected_source
        for module, name, authority, expected_source in authority_rows
    )
    protocol = _CANONICAL_QUERY_PROTOCOL()
    preregistration = _CANONICAL_QUERY_PREREGISTRATION()
    if (
        _module_sha256(query_family)
        != EXPECTED_QUERY_FAMILY_MODULE_SHA256
        or _module_sha256(direct)
        != EXPECTED_CONDITIONAL_DIRECT_MODULE_SHA256
        or _module_sha256(recovery)
        != EXPECTED_V0055_RECOVERY_MODULE_SHA256
        or (
            EXPECTED_ORCHESTRATOR_MODULE_SHA256
            and _file_sha256(Path(__file__).resolve())
            != EXPECTED_ORCHESTRATOR_MODULE_SHA256
        )
        or changed_authority
        or query_family.registered_h2_query_family_protocol_v1
        is not _CANONICAL_QUERY_PROTOCOL
        or query_family.registered_h2_query_family_preregistration_v1
        is not _CANONICAL_QUERY_PREREGISTRATION
        or query_family.load_verified_h2_query_family_store_v1
        is not _CANONICAL_QUERY_LOAD_STORE
        or direct.require_conditional_direct_launch_v1
        is not _CANONICAL_DIRECT_REQUIRE_LAUNCH
        or recovery.require_durable_action_local_recovery_result_v1
        is not _CANONICAL_RECOVERY_REQUIRE
        or protocol.protocol_id
        != EXPECTED_CANONICAL_IDS.get(
            "protocol", protocol.protocol_id
        )
        or protocol.proof_semantics_id
        != EXPECTED_CANONICAL_IDS.get(
            "proof_semantics", protocol.proof_semantics_id
        )
        or preregistration.preregistration_id
        != EXPECTED_CANONICAL_IDS.get(
            "preregistration", preregistration.preregistration_id
        )
    ):
        raise DurableMultiQueryWorkloadInvariantViolation(
            "registered V0-056 source or callable identity changed"
        )


_CANONICAL_SOURCE_PIN_ASSERT = _assert_source_pins


def _assert_canonical_result_ids(
    result: DurableMultiQueryWorkloadResultV1,
) -> None:
    expected = {
        name: value
        for name, value in EXPECTED_CANONICAL_IDS.items()
        if name != "evaluation_replay_report"
    }
    if (
        expected
        and _visible_canonical_result_ids(result) != expected
    ):
        raise DurableMultiQueryWorkloadInvariantViolation(
            "registered V0-056 canonical artifact identities changed"
        )


def _prepare_campaign_root(store_root: Path) -> None:
    if not isinstance(store_root, Path):
        raise DurableMultiQueryWorkloadInvariantViolation(
            "V0-056 store root must be a Path"
        )
    if store_root.exists():
        if (
            store_root.is_symlink()
            or not store_root.is_dir()
            or any(store_root.iterdir())
        ):
            raise DurableMultiQueryWorkloadInvariantViolation(
                "V0-056 requires a fresh empty store root"
            )
    else:
        store_root.mkdir(parents=True)


def _run_registered_h2_durable_multiquery_workload_v1(
    store_root: Path,
) -> DurableMultiQueryWorkloadResultV1:
    """Produce the registered source, warm, reset and direct campaign."""

    _CANONICAL_SOURCE_PIN_ASSERT()
    _prepare_campaign_root(store_root)

    # This content is constructed and durably frozen before the source
    # producer is called.  Neither object contains a source artifact ID.
    protocol = _CANONICAL_QUERY_PROTOCOL()
    preregistration = _CANONICAL_QUERY_PREREGISTRATION()
    if (
        preregistration.protocol.to_document() != protocol.to_document()
        or preregistration.source_artifact_ids_absent is not True
    ):
        raise DurableMultiQueryWorkloadInvariantViolation(
            "source-blind preregistration changed"
        )
    _write_preregistration_v1(
        store_root / "preregistration",
        protocol,
        preregistration,
    )

    source_root = store_root / "source"
    source = _CANONICAL_RECOVERY_RUN(source_root)
    _CANONICAL_RECOVERY_REQUIRE(source)
    if (
        source.trace.preground_transition_calls != 0
        or source.trace.operational_ground_transition_calls != 1
        or source.trace.model_only_worker_ground_transition_calls != 0
        or source.trace.process_launches != 3
        or source.p2_continuation.first_action != "N"
        or source.p2_continuation.final_action != "M"
        or source.p2_continuation.final_certified is not True
    ):
        raise DurableMultiQueryWorkloadInvariantViolation(
            "V0-055 source no longer supplies the registered one-row recovery"
        )
    equivalence = _offline_base_equivalence(source)

    warm_root = store_root / "warm-query-facets"
    initialization = _CANONICAL_QUERY_INITIALIZE_W0(
        source_root / "c2",
        source.c2_commit_id,
        warm_root,
    )
    w0_commit_id = initialization.commit.commit_id
    current_commit_id = w0_commit_id
    w1_commit_id: str | None = None
    w2_commit_id: str | None = None
    warm_results: list[query_family.H2QueryFamilyOccurrenceResultV1] = []
    reset_initializations: list[
        query_family.H2QueryFamilyInitializationV1
    ] = []
    reset_results: list[query_family.H2QueryFamilyOccurrenceResultV1] = []
    direct_results: list[direct.ConditionalDirectGroundResultV1] = []

    reset_parent = store_root / "c2-base-reset-controls"
    reset_parent.mkdir()
    for occurrence in preregistration.occurrences:
        query = _query_for_occurrence(protocol, occurrence)

        warm = _CANONICAL_QUERY_LAUNCH(
            warm_root,
            current_commit_id,
            occurrence,
        )
        query_family.require_h2_query_family_occurrence_result_v1(
            warm, occurrence
        )
        current_commit_id = warm.after_commit_id
        if warm.logical_lower_count == 21 and w1_commit_id is None:
            w1_commit_id = current_commit_id
        if warm.logical_lower_count == 24 and w2_commit_id is None:
            w2_commit_id = current_commit_id
        warm_results.append(warm)

        reset_root = reset_parent / (
            f"occurrence-{occurrence.occurrence_index:02d}"
        )
        reset_initialization = _CANONICAL_QUERY_INITIALIZE_W0(
            source_root / "c2",
            source.c2_commit_id,
            reset_root,
        )
        if (
            reset_initialization.commit.commit_id != w0_commit_id
            or reset_initialization.source_lease_id
            != initialization.source_lease_id
        ):
            raise DurableMultiQueryWorkloadInvariantViolation(
                "C2-base-reset W0 identity changed"
            )
        reset_initializations.append(reset_initialization)
        reset = _CANONICAL_QUERY_LAUNCH(
            reset_root,
            reset_initialization.commit.commit_id,
            occurrence,
        )
        query_family.require_h2_query_family_occurrence_result_v1(
            reset, occurrence
        )
        reset_results.append(reset)

        launch = _CANONICAL_DIRECT_LAUNCH(query, occurrence)
        _CANONICAL_DIRECT_REQUIRE_LAUNCH(launch)
        direct_results.append(launch.result)

    if w1_commit_id is None or w2_commit_id is None:
        raise DurableMultiQueryWorkloadInvariantViolation(
            "warm workload did not construct both changed-query generations"
        )
    warm_lease = _CANONICAL_QUERY_LOAD_STORE(warm_root, current_commit_id)
    if (
        current_commit_id != w2_commit_id
        or warm_lease.commit.generation != 2
        or warm_lease.commit.logical_lower_count != 24
        or warm_lease.commit.persisted_facet_count != 6
        or warm_lease.commit.persisted_root_count != 0
    ):
        raise DurableMultiQueryWorkloadInvariantViolation(
            "final warm durable model changed"
        )

    warm_tuple = tuple(warm_results)
    reset_initialization_tuple = tuple(reset_initializations)
    reset_tuple = tuple(reset_results)
    direct_tuple = tuple(direct_results)
    matched = tuple(
        _match_occurrence(
            protocol,
            occurrence,
            warm,
            reset_initialization,
            reset,
            direct_result,
        )
        for occurrence, warm, reset_initialization, reset, direct_result in zip(
            preregistration.occurrences,
            warm_tuple,
            reset_initialization_tuple,
            reset_tuple,
            direct_tuple,
            strict=True,
        )
    )
    prefixes = _prefixes(matched)
    telemetry = _telemetry(matched)
    source_trace = V0056ScopedOperationalTraceV1(
        "SOURCE_OPERATIONAL",
        None,
        0,
        0,
        0,
        source.trace.operational_ground_transition_calls,
        0,
        0,
        0,
        source.trace.process_launches,
        0,
        0,
        _tree_unique_bytes(source_root),
    )
    promotion_trace = V0056ScopedOperationalTraceV1(
        "QUERY_FACET_PROMOTION_OPERATIONAL",
        None,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        initialization.read_bytes,
        initialization.output_bytes,
    )
    campaign_snapshot_id = _snapshot_id(store_root, "CAMPAIGN")
    result = DurableMultiQueryWorkloadResultV1(
        protocol,
        preregistration,
        source.result_id,
        source.c1_commit_id,
        source.c2_commit_id,
        source.failed_verification.verification_id,
        source.ground_authorization.authorization_id,
        equivalence,
        w0_commit_id,
        w1_commit_id,
        w2_commit_id,
        current_commit_id,
        source_trace,
        promotion_trace,
        warm_tuple,
        reset_initialization_tuple,
        reset_tuple,
        direct_tuple,
        matched,
        prefixes,
        telemetry,
        campaign_snapshot_id,
        EXPECTED_CAMPAIGN_EVENTS,
        DurableMultiQueryClaimLocksV1(),
        _source_result=source,
    )
    bound = _CANONICAL_BIND_RUNTIME_AUTHORITY(
        result,
        issuer=_RESULT_ISSUER,
    )
    require_durable_multiquery_workload_result_v1(bound)
    _assert_canonical_result_ids(bound)
    if _snapshot_id(store_root, "CAMPAIGN") != campaign_snapshot_id:
        raise DurableMultiQueryWorkloadInvariantViolation(
            "campaign bytes changed while result was frozen"
        )
    return bound


_CANONICAL_ORCHESTRATOR_PRODUCER = (
    _run_registered_h2_durable_multiquery_workload_v1
)


def run_registered_h2_durable_multiquery_workload_v1(
    store_root: Path,
) -> DurableMultiQueryWorkloadResultV1:
    """Run the registered V0-056 matched ten-occurrence campaign."""

    _CANONICAL_SOURCE_PIN_ASSERT()
    return _CANONICAL_ORCHESTRATOR_PRODUCER(store_root)


def verify_registered_h2_durable_multiquery_workload_v1(
    store_root: Path,
    claimed: DurableMultiQueryWorkloadResultV1,
) -> DurableMultiQueryWorkloadVerificationV1:
    """Same-implementation replay in the evaluation lane only."""

    _CANONICAL_SOURCE_PIN_ASSERT()
    require_durable_multiquery_workload_result_v1(claimed)
    _assert_canonical_result_ids(claimed)
    before = _snapshot_id(store_root, "CAMPAIGN")
    if before != claimed.campaign_snapshot_id:
        raise DurableMultiQueryWorkloadInvariantViolation(
            "claimed campaign store differs from its frozen snapshot"
        )
    # Reconstruct the source-blind contract before starting the replay source.
    replay_preregistration = _CANONICAL_QUERY_PREREGISTRATION()
    if (
        replay_preregistration.to_document()
        != claimed.preregistration.to_document()
    ):
        raise DurableMultiQueryWorkloadInvariantViolation(
            "reconstructed preregistration differs from claim"
        )
    with tempfile.TemporaryDirectory(
        prefix="acfqp-v0056-verifier-"
    ) as directory:
        replayed = _CANONICAL_ORCHESTRATOR_PRODUCER(
            Path(directory) / "campaign"
        )
        exact_match = replayed.to_document() == claimed.to_document()
    after = _snapshot_id(store_root, "CAMPAIGN")
    if not exact_match or before != after:
        raise DurableMultiQueryWorkloadInvariantViolation(
            "V0-056 replay or original-store immutability check failed"
        )
    report = DurableMultiQueryWorkloadVerificationV1(
        claimed.result_id,
        replayed.result_id,
        True,
        True,
        True,
        True,
        False,
        True,
        False,
        11,
        33,
    )
    bound = _CANONICAL_BIND_RUNTIME_AUTHORITY(
        report,
        issuer=_VERIFICATION_ISSUER,
    )
    required = require_durable_multiquery_workload_verification_v1(bound)
    expected_report_id = EXPECTED_CANONICAL_IDS.get(
        "evaluation_replay_report",
        required.report_id,
    )
    if required.report_id != expected_report_id:
        raise DurableMultiQueryWorkloadInvariantViolation(
            "registered V0-056 verifier identity changed"
        )
    return required


__all__ = [
    "CONTRACT_VERSION",
    "ConditionalOfflineBaseEquivalenceV1",
    "DurableMultiQueryClaimLocksV1",
    "DurableMultiQueryPrefixV1",
    "DurableMultiQueryTelemetryV1",
    "DurableMultiQueryWorkloadInvariantViolation",
    "DurableMultiQueryWorkloadResultV1",
    "DurableMultiQueryWorkloadVerificationV1",
    "EXPECTED_CAMPAIGN_EVENTS",
    "MatchedDurableMultiQueryOccurrenceV1",
    "PROFILE_KEY",
    "SCHEMA_VERSION",
    "SUCCESS_STATUS",
    "V0056ScopedOperationalTraceV1",
    "require_durable_multiquery_workload_result_v1",
    "require_durable_multiquery_workload_verification_v1",
    "run_registered_h2_durable_multiquery_workload_v1",
    "verify_registered_h2_durable_multiquery_workload_v1",
]
