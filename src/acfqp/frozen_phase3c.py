"""Load and bind a frozen Phase-3C RAPM without rebuilding it.

The consumption path validates a completed Phase-3C artifact bundle and binds
its portable state/action catalogues to the registered safe-chain domain.  It
never evaluates a ground transition and never calls a partition, quotient, or
portable-RAPM builder.  The serialized partition, nominal model, realization
envelope, and concretizer remain the planning authority.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
import hashlib
from itertools import product
import json
from pathlib import Path
from typing import Any, Iterable

from acfqp.abstraction import (
    ExactRealizationEnvelope,
    GroundRealization,
    NominalActionModel,
    NominalQuotient,
    Partition,
    QuotientModels,
)
from acfqp.abstraction.quotient import EnvelopeEntry, NominalEntry
from acfqp.artifacts import (
    PHASE3C_DOCUMENT_CONTRACTS,
    PHASE3C_REQUIRED_PATHS,
    canonical_sha256,
    object_id,
    serialized_json_bytes,
    sha256_file,
    verify_artifact_bundle,
)
from acfqp.build_coverage import SuiteBuildCoverage
from acfqp.core import QuerySpec
from acfqp.domains import G2048ActionFrameGeometryAdapter, safe_chain_fixture
from acfqp.domains.g2048 import G2048State, G2048Status
from acfqp.phase3c import (
    ABSTRACT_QUERY_KEY,
    CONTRACT_VERSION,
    ECONOMICS_NOT_RUN,
    EXECUTION_PROFILE,
    FULL_PHASE3_NOT_RUN,
    LOCAL_HYBRID_PASS,
    LOCAL_QUERY_KEY,
    PROFILE_KEY,
    SLICE_PASS,
    Phase3CWorld,
    RegisteredQuery,
)
from acfqp.portable import (
    PortableBuildResult,
    PortableRAPM,
    PortableRegistry,
    fraction_from_json,
)


class FrozenPhase3CLoadError(ValueError):
    """The source is not an admissible immutable Phase-3C model bundle."""


@dataclass(frozen=True, slots=True)
class FrozenPhase3CWorld(Phase3CWorld):
    """A Phase3CWorld bound entirely from an earlier build artifact."""

    source_bundle: Path
    portable_rapm_source_bytes: bytes = field(repr=False)
    build_epoch_source_bytes: bytes = field(repr=False)
    source_manifest_sha256: str
    source_run_document: dict[str, Any] = field(repr=False)
    source_manifest_document: dict[str, Any] = field(repr=False)
    local_pre_recovery_document: dict[str, Any] = field(repr=False)
    source_locality_document: dict[str, Any] = field(repr=False)
    source_authorization_document: dict[str, Any] = field(repr=False)
    bound_ground_action_records: tuple[tuple[G2048State, Any], ...] = field(
        repr=False
    )
    unrestricted_reward_upper: Fraction
    binding_counters: dict[str, int]

    @property
    def portable_rapm_source_sha256(self) -> str:
        return hashlib.sha256(self.portable_rapm_source_bytes).hexdigest()

    @property
    def build_epoch_source_sha256(self) -> str:
        return hashlib.sha256(self.build_epoch_source_bytes).hexdigest()


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise FrozenPhase3CLoadError(f"cannot load JSON artifact {path}: {error}") from error


def _load_exact_document(path: Path) -> tuple[dict[str, Any], bytes]:
    try:
        source_bytes = path.read_bytes()
        document = json.loads(source_bytes.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise FrozenPhase3CLoadError(f"cannot load JSON artifact {path}: {error}") from error
    if not isinstance(document, dict):
        raise FrozenPhase3CLoadError(f"JSON artifact must be an object: {path}")
    if source_bytes != serialized_json_bytes(document):
        raise FrozenPhase3CLoadError(
            f"artifact is not in canonical serialized-byte form: {path}"
        )
    return document, source_bytes


def _load_stable_documents(bundle: Path) -> dict[str, Any]:
    stable: dict[str, Any] = {}
    for relative in PHASE3C_REQUIRED_PATHS:
        if relative == "run.json":
            continue
        path = bundle / relative
        if relative.endswith(".jsonl"):
            try:
                stable[relative] = [
                    json.loads(line)
                    for line in path.read_text(encoding="utf-8").splitlines()
                    if line
                ]
            except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
                raise FrozenPhase3CLoadError(
                    f"cannot load JSONL artifact {path}: {error}"
                ) from error
        else:
            stable[relative] = _load_json(path)
    return stable


def _validate_bundle_contract(
    bundle: Path,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    failures = verify_artifact_bundle(bundle)
    if failures:
        raise FrozenPhase3CLoadError(
            "Phase3C artifact integrity failed: " + "; ".join(failures)
        )
    manifest = _load_json(bundle / "manifest.json")
    if not isinstance(manifest, dict):
        raise FrozenPhase3CLoadError("manifest.json must contain an object")
    if manifest.get("required_paths") != sorted(PHASE3C_REQUIRED_PATHS):
        raise FrozenPhase3CLoadError("source bundle is not the exact Phase3C topology")
    records = manifest.get("files")
    if not isinstance(records, list):
        raise FrozenPhase3CLoadError("manifest files must be a list")
    by_path = {
        record.get("path"): record for record in records if isinstance(record, dict)
    }
    if set(by_path) != set(PHASE3C_REQUIRED_PATHS) or len(records) != len(by_path):
        raise FrozenPhase3CLoadError("source bundle has a non-Phase3C file catalogue")
    for relative, (role, schema) in PHASE3C_DOCUMENT_CONTRACTS.items():
        record = by_path[relative]
        if (
            record.get("role") != role
            or record.get("schema") != schema
            or record.get("required") is not True
        ):
            raise FrozenPhase3CLoadError(
                f"Phase3C artifact contract mismatch: {relative}"
            )

    run = _load_json(bundle / "run.json")
    if not isinstance(run, dict):
        raise FrozenPhase3CLoadError("run.json must contain an object")
    expected_status = {
        "schema_version": "phase3c.v1",
        "contract_version": CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "execution_profile": EXECUTION_PROFILE,
        "status": SLICE_PASS,
        "local_hybrid_gate_status": LOCAL_HYBRID_PASS,
        "full_phase3_gate_status": FULL_PHASE3_NOT_RUN,
        "workload_economics_gate_status": ECONOMICS_NOT_RUN,
    }
    for name, expected in expected_status.items():
        if run.get(name) != expected:
            raise FrozenPhase3CLoadError(
                f"source Phase3C run status mismatch for {name}: {run.get(name)!r}"
            )
    stable = _load_stable_documents(bundle)
    if run.get("semantic_hash") != canonical_sha256(stable):
        raise FrozenPhase3CLoadError("source Phase3C semantic hash mismatch")
    run_payload = {
        key: value
        for key, value in run.items()
        if key not in {"run_id", "started_at", "finished_at"}
    }
    if run.get("run_id") != object_id(run_payload, "run"):
        raise FrozenPhase3CLoadError("source Phase3C run_id mismatch")
    return manifest, run, stable


def _registered_queries(
    canonical: QuerySpec[Any],
) -> tuple[RegisteredQuery, RegisteredQuery]:
    abstract = QuerySpec(
        canonical.initial_distribution,
        1,
        canonical.reward_weights,
        canonical.goal,
        Fraction(0),
        Fraction(1),
        canonical.normalizer_proof_id,
    )
    return (
        RegisteredQuery(ABSTRACT_QUERY_KEY, abstract, "ABSTRACT_CERTIFIED"),
        RegisteredQuery(LOCAL_QUERY_KEY, canonical, "LOCAL_GROUND_RECOVERY"),
    )


def _ordered_states(states: Iterable[G2048State]) -> tuple[G2048State, ...]:
    return tuple(sorted(states, key=lambda state: (type(state).__qualname__, repr(state))))


def _bind_coverage_without_transitions(
    model_document: dict[str, Any],
    queries: tuple[RegisteredQuery, RegisteredQuery],
    *,
    rank_cap: int,
    cell_count: int,
) -> tuple[SuiteBuildCoverage[G2048State], dict[str, G2048State], dict[str, int]]:
    """Bind portable state IDs by finite structural scan; never call ``step``."""

    coverage_document = model_document["coverage"]
    target_ids = set(coverage_document["covered_state_ids"])
    state_by_id: dict[str, G2048State] = {}
    candidate_count = 0
    for status in G2048Status:
        for board in product(range(rank_cap + 1), repeat=cell_count):
            candidate_count += 1
            state = G2048State(tuple(board), status)
            state_id = object_id(state, "state")
            if state_id not in target_ids:
                continue
            incumbent = state_by_id.get(state_id)
            if incumbent is not None and incumbent != state:
                raise FrozenPhase3CLoadError("ground state stable-ID collision")
            state_by_id[state_id] = state
    if set(state_by_id) != target_ids:
        missing = sorted(target_ids - set(state_by_id))
        raise FrozenPhase3CLoadError(
            f"portable states are outside the registered finite structure: {missing!r}"
        )

    declared = _ordered_states(
        {
            state
            for registered in queries
            for probability, state in registered.query.initial_distribution
            if Fraction(probability) > 0
        }
    )
    covered = _ordered_states(state_by_id.values())
    coverage = SuiteBuildCoverage(
        declared_support_set_sha256=coverage_document[
            "declared_support_set_sha256"
        ],
        declared_support_states=declared,
        declared_support_state_ids=tuple(
            coverage_document["declared_support_state_ids"]
        ),
        covered_states=covered,
        covered_state_ids=tuple(coverage_document["covered_state_ids"]),
        exact_state_cap=int(coverage_document["exact_state_cap"]),
        mode=coverage_document["mode"],
        admissible_query_support_rule=coverage_document[
            "admissible_query_support_rule"
        ],
        reuse_outside_coverage_forbidden=coverage_document[
            "reuse_outside_coverage_forbidden"
        ],
    )
    return coverage, state_by_id, {
        "structural_candidate_states_scanned": candidate_count,
        "portable_states_bound": len(state_by_id),
        "kernel_step_calls": 0,
        "transition_closure_calls": 0,
    }


def _fraction_items(
    rows: Iterable[dict[str, Any]],
    *,
    id_field: str,
    value_field: str,
    location: str,
) -> tuple[tuple[str, Fraction], ...]:
    return tuple(
        (
            str(row[id_field]),
            fraction_from_json(row[value_field], field=f"{location}.{value_field}"),
        )
        for row in rows
    )


def _bind_registry(
    model: PortableRAPM,
    *,
    kernel: Any,
    adapter: G2048ActionFrameGeometryAdapter,
    coverage: SuiteBuildCoverage[G2048State],
    state_by_id: dict[str, G2048State],
    counters: dict[str, int],
) -> tuple[
    Partition,
    PortableRegistry,
    tuple[tuple[G2048State, Any], ...],
]:
    document = model.to_dict()
    catalog_state_ids = {row["state_id"] for row in document["state_catalog"]}
    if set(state_by_id) != catalog_state_ids:
        raise FrozenPhase3CLoadError(
            "portable state catalogue does not equal bound safe-chain coverage"
        )
    if document["coverage"]["covered_state_ids"] != sorted(state_by_id):
        raise FrozenPhase3CLoadError("portable coverage/state catalogue mismatch")
    for row in document["state_catalog"]:
        state = state_by_id[row["state_id"]]
        expected_kind = (
            "failure"
            if state.status is G2048Status.FAILURE
            else "terminal"
            if kernel.is_terminal(state)
            else "active"
        )
        if row["planning_kind"] != expected_kind:
            raise FrozenPhase3CLoadError(
                f"planning kind is inconsistent with ground state {row['state_id']}"
            )

    assignments: dict[G2048State, str] = {}
    for row in document["partition"]:
        cell_id = row["cell_id"]
        for state_id in row["member_state_ids"]:
            state = state_by_id[state_id]
            if state in assignments:
                raise FrozenPhase3CLoadError("portable partition assigns a state twice")
            assignments[state] = cell_id
    if set(assignments) != set(coverage.covered_states):
        raise FrozenPhase3CLoadError("portable partition is not total on ground coverage")
    partition = Partition.from_mapping(assignments)

    semantic_by_source: dict[str, Any] = {}
    label_candidates = 0
    labels_by_state: dict[G2048State, tuple[Any, ...]] = {}
    for state in coverage.covered_states:
        labels = tuple(adapter.labels(kernel, state))
        labels_by_state[state] = labels
        label_candidates += len(labels)
        for action in labels:
            source_id = object_id(action, "semantic-source")
            incumbent = semantic_by_source.get(source_id)
            if incumbent is not None and incumbent != action:
                raise FrozenPhase3CLoadError("semantic source ID collision")
            semantic_by_source[source_id] = action
    semantic_records: list[tuple[str, Any, str]] = []
    semantic_by_action_id: dict[str, Any] = {}
    for row in document["semantic_action_catalog"]:
        try:
            action = semantic_by_source[row["source_action_id"]]
        except KeyError as error:
            raise FrozenPhase3CLoadError(
                f"unknown G2048 semantic source ID {row['source_action_id']}"
            ) from error
        cell_id = row["cell_id"]
        for state in partition.members(cell_id):
            if not kernel.is_terminal(state) and action not in labels_by_state[state]:
                raise FrozenPhase3CLoadError(
                    "serialized semantic action is unavailable for a cell member"
                )
        semantic_records.append((cell_id, action, row["action_id"]))
        semantic_by_action_id[row["action_id"]] = action

    ground_records: list[tuple[G2048State, Any, str]] = []
    ground_by_id: dict[str, Any] = {}
    action_candidates = 0
    action_maps: dict[G2048State, dict[str, Any]] = {}
    for state in coverage.covered_states:
        actions = tuple(kernel.actions(state))
        action_candidates += len(actions)
        action_maps[state] = {
            object_id(action, "ground-action-source"): action for action in actions
        }
    complete_ground_action_records = tuple(
        (state, action)
        for state in coverage.covered_states
        for action in action_maps[state].values()
    )
    for row in document["ground_action_catalog"]:
        state = state_by_id[row["state_id"]]
        try:
            action = action_maps[state][row["source_action_id"]]
        except KeyError as error:
            raise FrozenPhase3CLoadError(
                f"unknown G2048 ground source ID {row['source_action_id']}"
            ) from error
        ground_records.append((state, action, row["ground_action_id"]))
        ground_by_id[row["ground_action_id"]] = action

    registry = PortableRegistry(
        tuple((state, state_id) for state_id, state in sorted(state_by_id.items())),
        tuple((cell_id, cell_id) for cell_id in model.cells),
        tuple(semantic_records),
        tuple(ground_records),
    )
    serialized = PortableBuildResult(model, registry).serialized_adapter()
    for row in document["concretizer_registry"]:
        state = state_by_id[row["state_id"]]
        action = semantic_by_action_id[row["action_id"]]
        expected = tuple(adapter.concretize(kernel, state, action))
        actual = tuple(serialized.concretize(kernel, state, action))
        if actual != expected:
            raise FrozenPhase3CLoadError(
                "serialized concretizer differs from the registered G2048 adapter"
            )
        actual_ids = {
            registry.ground_action_id(state, ground_action): probability
            for probability, ground_action in actual
        }
        recorded_ids = {
            support["ground_action_id"]: fraction_from_json(
                support["probability"], field="concretizer probability"
            )
            for support in row["support"]
        }
        if actual_ids != recorded_ids or not set(recorded_ids).issubset(ground_by_id):
            raise FrozenPhase3CLoadError("concretizer/ground catalogue binding mismatch")
    counters.update(
        {
            "semantic_label_candidates_scanned": label_candidates,
            "ground_action_candidates_scanned": action_candidates,
            "serialized_cells_bound": len(model.cells),
            "serialized_semantic_actions_bound": len(semantic_records),
            "serialized_ground_actions_bound": len(ground_records),
            "serialized_concretizer_rows_bound": len(
                document["concretizer_registry"]
            ),
            "partition_builder_calls": 0,
            "quotient_builder_calls": 0,
            "portable_rapm_builder_calls": 0,
        }
    )
    return partition, registry, complete_ground_action_records


def _bind_models(
    model: PortableRAPM,
    partition: Partition,
    registry: PortableRegistry,
    *,
    kernel: Any,
) -> QuotientModels:
    document = model.to_dict()
    action_by_id = {
        action_id: action
        for _cell, action, action_id in registry.semantic_action_records
    }
    state_by_id = {state_id: state for state, state_id in registry.state_records}
    nominal_entries: list[NominalEntry] = []
    for row in document["nominal"]:
        transition = row["model"]
        nominal_entries.append(
            NominalEntry(
                row["cell_id"],
                action_by_id[row["action_id"]],
                NominalActionModel(
                    _fraction_items(
                        transition["reward_features"],
                        id_field="name",
                        value_field="value",
                        location="nominal.reward_features",
                    ),
                    _fraction_items(
                        transition["successor_probabilities"],
                        id_field="cell_id",
                        value_field="probability",
                        location="nominal.successor_probabilities",
                    ),
                    fraction_from_json(
                        transition["failure_probability"],
                        field="nominal.failure_probability",
                    ),
                    fraction_from_json(
                        transition["termination_probability"],
                        field="nominal.termination_probability",
                    ),
                    int(transition["realization_count"]),
                ),
            )
        )
    nominal = NominalQuotient(partition, model.horizon, tuple(nominal_entries))

    serialized_adapter = PortableBuildResult(model, registry).serialized_adapter()
    envelope_entries: list[EnvelopeEntry] = []
    for row in document["envelope"]:
        realizations: list[GroundRealization] = []
        for realization in row["realizations"]:
            realizations.append(
                GroundRealization(
                    state_by_id[realization["state_id"]],
                    _fraction_items(
                        realization["reward_features"],
                        id_field="name",
                        value_field="value",
                        location="envelope.reward_features",
                    ),
                    _fraction_items(
                        realization["successor_probabilities"],
                        id_field="cell_id",
                        value_field="probability",
                        location="envelope.successor_probabilities",
                    ),
                    fraction_from_json(
                        realization["failure_probability"],
                        field="envelope.failure_probability",
                    ),
                    fraction_from_json(
                        realization["termination_probability"],
                        field="envelope.termination_probability",
                    ),
                )
            )
        envelope_entries.append(
            EnvelopeEntry(
                row["cell_id"],
                action_by_id[row["action_id"]],
                tuple(realizations),
            )
        )
    envelope = ExactRealizationEnvelope(
        partition,
        model.horizon,
        tuple(envelope_entries),
        None,
        lambda state: serialized_adapter.labels(kernel, state),
        lambda state, action: serialized_adapter.concretize(kernel, state, action),
    )
    return QuotientModels(nominal, envelope)


def _validate_cross_ids(
    *,
    model: PortableRAPM,
    model_document: dict[str, Any],
    epoch: dict[str, Any],
    stable: dict[str, Any],
    kernel: Any,
    coverage: SuiteBuildCoverage[G2048State],
    structural_id: str,
    model_sha256: str,
    epoch_sha256: str,
) -> None:
    epoch_payload = dict(epoch)
    build_epoch_id = epoch_payload.pop("build_epoch_id", None)
    if build_epoch_id != object_id(epoch_payload, "build-epoch"):
        raise FrozenPhase3CLoadError("BuildEpoch content ID mismatch")
    expected = {
        "structural_id": structural_id,
        "kernel_sha256": canonical_sha256(kernel.structural_key()),
        "coverage_id": model.coverage_id,
        "coverage": coverage.descriptor(),
        "portable_rapm_id": model.model_id,
        "partition_id": object_id(model_document["partition"], "partition"),
        "nominal_model_id": object_id(model_document["nominal"], "nominal"),
        "sound_envelope_id": object_id(model_document["envelope"], "envelope"),
        "concretizer_id": object_id(
            model_document["concretizer_registry"], "concretizer"
        ),
        "covered_ground_states": len(coverage.covered_states),
        "ground_state_action_pairs": sum(
            len(kernel.actions(state))
            for state in coverage.covered_states
            if not kernel.is_terminal(state)
        ),
        "abstract_cells": len(model.cells),
        "abstract_state_action_pairs": len(model_document["nominal"]),
    }
    for name, value in expected.items():
        if epoch.get(name) != value:
            raise FrozenPhase3CLoadError(f"BuildEpoch cross-ID mismatch: {name}")
    if epoch.get("consumption_is_query_neutral") is not True:
        raise FrozenPhase3CLoadError("BuildEpoch is not query-neutral")
    if epoch.get("query_results_used_for_phase3c_build") is not False:
        raise FrozenPhase3CLoadError("BuildEpoch records query-result construction leakage")

    workload = stable["workload/spec.json"]
    for name, expected_value in (
        ("build_epoch_id", build_epoch_id),
        ("portable_rapm_id", model.model_id),
        ("coverage_id", model.coverage_id),
    ):
        if workload.get(name) != expected_value:
            raise FrozenPhase3CLoadError(f"workload/model/epoch cross-ID mismatch: {name}")
    locality = stable["evaluation/locality.json"]
    byte_links = {
        "base_model_sha256_before": model_sha256,
        "base_model_sha256_after": model_sha256,
        "base_build_epoch_sha256_before": epoch_sha256,
        "base_build_epoch_sha256_after": epoch_sha256,
    }
    for name, expected_value in byte_links.items():
        if locality.get(name) != expected_value:
            raise FrozenPhase3CLoadError(f"source byte-invariance link mismatch: {name}")
    if locality.get("base_rapm_immutable") is not True:
        raise FrozenPhase3CLoadError("source bundle does not certify an immutable base RAPM")
    expected_locality_counts = {
        "frontier_state_action_pairs": 32,
        "frontier_positive_probability_outcomes": 128,
        "reverse_selected_dependency_state_action_pairs": 8,
        "reverse_selected_dependency_positive_probability_outcomes": 32,
        "authorized_state_action_pairs": 40,
        "authorized_positive_probability_outcomes": 160,
        "coverage_ground_state_action_pairs": 144,
        "coverage_positive_probability_outcomes": 576,
    }
    for name, expected_value in expected_locality_counts.items():
        if locality.get(name) != expected_value:
            raise FrozenPhase3CLoadError(
                f"source Phase3C locality count mismatch: {name}"
            )
    if locality.get("full_same_query_all_action_graph") != {
        "decision_state_time_pairs": 20,
        "state_action_pairs": 48,
        "positive_probability_outcomes": 192,
    }:
        raise FrozenPhase3CLoadError(
            "source Phase3C same-query locality count mismatch"
        )


def _local_pre_recovery(
    stable: dict[str, Any],
    model_id: str,
    ground_query_id: str,
) -> dict[str, Any]:
    rows = stable["audit/pre_recovery.jsonl"]
    selected = [row for row in rows if row.get("query_key") == LOCAL_QUERY_KEY]
    if len(selected) != 1:
        raise FrozenPhase3CLoadError("source must contain exactly one local pre-audit row")
    row = selected[0]
    if row.get("stage") != "pre_recovery" or row.get("portable_model_id") != model_id:
        raise FrozenPhase3CLoadError("local pre-audit is not bound to the frozen RAPM")
    if row.get("ground_query_id") != ground_query_id:
        raise FrozenPhase3CLoadError(
            "local pre-audit is not bound to the registered ground query"
        )
    payload = dict(row)
    audit_id = payload.pop("audit_id", None)
    if audit_id != object_id(payload, "audit"):
        raise FrozenPhase3CLoadError("local pre-audit content ID mismatch")
    fraction_from_json(
        row.get("unrestricted_reward_upper"),
        field="local pre-audit unrestricted_reward_upper",
    )
    return row


def _source_authorization(
    stable: dict[str, Any],
    complete_ground_action_records: tuple[tuple[G2048State, Any], ...],
    model_id: str,
    ground_query_id: str,
) -> dict[str, Any]:
    document = stable["recovery/authorization.json"]
    if document.get("schema") != "acfqp.local_recovery_authorization.v1":
        raise FrozenPhase3CLoadError("source authorization schema mismatch")
    if (
        document.get("portable_model_id") != model_id
        or document.get("ground_query_id") != ground_query_id
    ):
        raise FrozenPhase3CLoadError(
            "source authorization is not bound to the frozen model/query"
        )
    catalog = {
        (object_id(state, "state"), object_id(action, "ground-action"))
        for state, action in complete_ground_action_records
    }

    def pairs(field: str) -> set[tuple[str, str]]:
        rows = document.get(field)
        if not isinstance(rows, list):
            raise FrozenPhase3CLoadError(
                f"source authorization field is not a list: {field}"
            )
        result = {
            (str(row.get("state_id")), str(row.get("action_id")))
            for row in rows
            if isinstance(row, dict)
            and set(row) == {"state_id", "action_id"}
        }
        if len(result) != len(rows) or not result.issubset(catalog):
            raise FrozenPhase3CLoadError(
                f"source authorization contains invalid pairs: {field}"
            )
        return result

    frontier = pairs("frontier_state_actions")
    reverse = pairs("reverse_selected_dependency_state_actions")
    if frontier & reverse:
        raise FrozenPhase3CLoadError("source authorization scopes overlap")
    expected_counts = {
        "frontier_state_action_count": len(frontier),
        "reverse_dependency_state_action_count": len(reverse),
        "authorized_state_action_count": len(frontier | reverse),
    }
    if expected_counts != {
        name: document.get(name) for name in expected_counts
    } or expected_counts != {
        "frontier_state_action_count": 32,
        "reverse_dependency_state_action_count": 8,
        "authorized_state_action_count": 40,
    }:
        raise FrozenPhase3CLoadError("source authorization count mismatch")
    if (
        document.get("coverage_extension_allowed") is not False
        or document.get("full_ground_model_or_j0_allowed") is not False
        or document.get("reverse_dependency_rule")
        != "strict_ancestor_selected_concretizer_support_only"
    ):
        raise FrozenPhase3CLoadError("source authorization authority flags mismatch")
    return document


def load_frozen_phase3c_world(source_bundle: str | Path) -> FrozenPhase3CWorld:
    """Load a verified Phase-3C model using zero ground transition calls."""

    bundle = Path(source_bundle).resolve()
    manifest, run, stable = _validate_bundle_contract(bundle)
    model_document, model_bytes = _load_exact_document(
        bundle / "build/portable_rapm.json"
    )
    epoch, epoch_bytes = _load_exact_document(bundle / "build/epoch.json")
    try:
        model = PortableRAPM.from_dict(model_document)
    except (TypeError, ValueError) as error:
        raise FrozenPhase3CLoadError(f"portable RAPM validation failed: {error}") from error

    kernel, canonical_query = safe_chain_fixture()
    queries = _registered_queries(canonical_query)
    coverage, state_by_id, counters = _bind_coverage_without_transitions(
        model_document,
        queries,
        rank_cap=kernel.rank_cap,
        cell_count=kernel.cell_count,
    )
    if len(coverage.covered_states) != 192:
        raise FrozenPhase3CLoadError("safe-chain bound coverage is not the Phase3C set")
    adapter = G2048ActionFrameGeometryAdapter()
    partition, registry, complete_ground_action_records = _bind_registry(
        model,
        kernel=kernel,
        adapter=adapter,
        coverage=coverage,
        state_by_id=state_by_id,
        counters=counters,
    )
    models = _bind_models(model, partition, registry, kernel=kernel)
    portable = PortableBuildResult(model, registry)
    structural_id = object_id(kernel.structural_key(), "structural")
    model_sha256 = hashlib.sha256(model_bytes).hexdigest()
    epoch_sha256 = hashlib.sha256(epoch_bytes).hexdigest()
    _validate_cross_ids(
        model=model,
        model_document=model_document,
        epoch=epoch,
        stable=stable,
        kernel=kernel,
        coverage=coverage,
        structural_id=structural_id,
        model_sha256=model_sha256,
        epoch_sha256=epoch_sha256,
    )
    local_pre = _local_pre_recovery(
        stable,
        model.model_id,
        object_id(queries[1].query, "query"),
    )
    source_authorization = _source_authorization(
        stable,
        complete_ground_action_records,
        model.model_id,
        object_id(queries[1].query, "query"),
    )
    unrestricted_upper = fraction_from_json(
        local_pre["unrestricted_reward_upper"],
        field="local pre-audit unrestricted_reward_upper",
    )

    if (bundle / "build/portable_rapm.json").read_bytes() != model_bytes:
        raise FrozenPhase3CLoadError("portable RAPM bytes changed while loading")
    if (bundle / "build/epoch.json").read_bytes() != epoch_bytes:
        raise FrozenPhase3CLoadError("BuildEpoch bytes changed while loading")

    return FrozenPhase3CWorld(
        kernel,
        adapter,
        coverage,
        partition,
        models,
        portable,
        queries,
        structural_id,
        epoch,
        bundle,
        model_bytes,
        epoch_bytes,
        sha256_file(bundle / "manifest.json"),
        run,
        manifest,
        local_pre,
        stable["evaluation/locality.json"],
        source_authorization,
        complete_ground_action_records,
        unrestricted_upper,
        counters,
    )


__all__ = [
    "FrozenPhase3CLoadError",
    "FrozenPhase3CWorld",
    "load_frozen_phase3c_world",
]
