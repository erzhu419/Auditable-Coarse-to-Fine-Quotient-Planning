"""Portable, content-addressed reusable abstract planning models.

The in-memory quotient objects intentionally retain Python ground-state objects
and a callable concretizer.  Those are useful while a model is being built,
but neither can cross a process boundary.  This module freezes the complete
planning/certificate payload into a domain-independent JSON document:

* caller-supplied stable state and action keys form the object catalogue;
* quotient cells and scoped actions receive content IDs;
* exact rational nominal and envelope data are preserved; and
* every callable concretizer result is materialized as a finite registry.

The logical model ID is a SHA-256 digest of the canonical payload.  Loading a
document therefore both reconstructs the same logical model and rejects any
un-resigned modification.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import hashlib
import json
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Hashable, Iterable, Mapping

if TYPE_CHECKING:
    from acfqp.abstraction.quotient import QuotientModels


MODEL_SCHEMA = "acfqp.portable_rapm.v1"
QUERY_SCHEMA = "acfqp.portable_query.v1"

JsonObject = dict[str, Any]
IdSource = Mapping[Hashable, str] | Callable[[Hashable], str]
StateKindSource = Mapping[Hashable, str] | Callable[[Hashable], str]
STATE_KINDS = frozenset({"active", "terminal", "failure", "success"})


def canonical_json(value: Any) -> str:
    """Return the byte-stable JSON representation used by all logical IDs."""

    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def logical_id(prefix: str, payload: Any) -> str:
    digest = hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()
    return f"{prefix}:{digest}"


def fraction_to_json(value: Fraction | int | str) -> JsonObject:
    rational = value if isinstance(value, Fraction) else Fraction(value)
    return {
        "numerator": rational.numerator,
        "denominator": rational.denominator,
    }


def fraction_from_json(value: Any, *, field: str = "fraction") -> Fraction:
    if not isinstance(value, dict) or set(value) != {"numerator", "denominator"}:
        raise ValueError(f"{field} must be a rational object")
    numerator = value["numerator"]
    denominator = value["denominator"]
    if (
        isinstance(numerator, bool)
        or isinstance(denominator, bool)
        or not isinstance(numerator, int)
        or not isinstance(denominator, int)
        or denominator <= 0
    ):
        raise ValueError(f"{field} must contain integer numerator and positive denominator")
    rational = Fraction(numerator, denominator)
    if fraction_to_json(rational) != value:
        raise ValueError(f"{field} must be reduced with a positive denominator")
    return rational


def _require_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} must be a nonempty string")
    return value


def _require_exact_keys(document: Any, keys: set[str], field: str) -> JsonObject:
    if not isinstance(document, dict) or set(document) != keys:
        raise ValueError(f"{field} has an invalid field set")
    return document


def _fraction_items(
    items: Any,
    *,
    id_field: str,
    probability_field: str,
    known_ids: set[str] | None,
    field: str,
) -> tuple[tuple[str, Fraction], ...]:
    if not isinstance(items, list):
        raise ValueError(f"{field} must be a list")
    result: list[tuple[str, Fraction]] = []
    seen: set[str] = set()
    for index, item in enumerate(items):
        record = _require_exact_keys(
            item, {id_field, probability_field}, f"{field}[{index}]"
        )
        identifier = _require_string(record[id_field], f"{field}[{index}].{id_field}")
        if identifier in seen:
            raise ValueError(f"{field} contains a duplicate {id_field}")
        if known_ids is not None and identifier not in known_ids:
            raise ValueError(f"{field} references an unknown {id_field}")
        seen.add(identifier)
        probability = fraction_from_json(
            record[probability_field], field=f"{field}[{index}].{probability_field}"
        )
        if probability <= 0:
            raise ValueError(f"{field} probabilities must be positive")
        result.append((identifier, probability))
    return tuple(result)


def _validate_reward_features(items: Any, field: str) -> tuple[tuple[str, Fraction], ...]:
    if not isinstance(items, list):
        raise ValueError(f"{field} must be a list")
    result: list[tuple[str, Fraction]] = []
    seen: set[str] = set()
    for index, item in enumerate(items):
        record = _require_exact_keys(item, {"name", "value"}, f"{field}[{index}]")
        name = _require_string(record["name"], f"{field}[{index}].name")
        if name in seen:
            raise ValueError(f"{field} contains a duplicate feature")
        seen.add(name)
        result.append(
            (name, fraction_from_json(record["value"], field=f"{field}[{index}].value"))
        )
    if [name for name, _ in result] != sorted(seen):
        raise ValueError(f"{field} must be sorted by feature name")
    return tuple(result)


def _validate_normalizer_rules(
    items: Any,
    reward_features: set[str],
) -> dict[
    str,
    tuple[
        tuple[tuple[str, Fraction], ...],
        dict[str, tuple[Fraction | None, Fraction | None]],
    ],
]:
    if not isinstance(items, list) or not items:
        raise ValueError("normalizer_rules must be a nonempty list")
    proof_ids: list[str] = []
    result: dict[
        str,
        tuple[
            tuple[tuple[str, Fraction], ...],
            dict[str, tuple[Fraction | None, Fraction | None]],
        ],
    ] = {}
    for index, item in enumerate(items):
        record = _require_exact_keys(
            item,
            {"proof_id", "kind", "reward_basis", "feature_caps"},
            f"normalizer_rules[{index}]",
        )
        proof_id = _require_string(record["proof_id"], "normalizer rule proof_id")
        if record["kind"] != "nonnegative_feature_caps_v1":
            raise ValueError("normalizer rule kind is unsupported")
        reward_basis = _validate_reward_features(
            record["reward_basis"],
            f"normalizer_rules[{index}].reward_basis",
        )
        if not reward_basis:
            raise ValueError("normalizer rule reward_basis must be nonempty")
        if {name for name, _ in reward_basis} != reward_features:
            raise ValueError(
                "normalizer rule reward_basis must cover the complete reward registry"
            )
        if any(weight < 0 for _, weight in reward_basis):
            raise ValueError("normalizer rule reward basis must be nonnegative")
        caps = record["feature_caps"]
        if not isinstance(caps, list) or not caps:
            raise ValueError("normalizer rule feature_caps must be nonempty")
        cap_names: list[str] = []
        parsed: dict[str, tuple[Fraction | None, Fraction | None]] = {}
        for cap_index, cap in enumerate(caps):
            cap_record = _require_exact_keys(
                cap,
                {"name", "per_step_cap", "total_cap"},
                f"normalizer_rules[{index}].feature_caps[{cap_index}]",
            )
            name = _require_string(cap_record["name"], "normalizer cap feature")
            if name not in reward_features:
                raise ValueError("normalizer rule references an unknown reward feature")
            per_step = (
                None
                if cap_record["per_step_cap"] is None
                else fraction_from_json(
                    cap_record["per_step_cap"], field="normalizer per-step cap"
                )
            )
            total = (
                None
                if cap_record["total_cap"] is None
                else fraction_from_json(
                    cap_record["total_cap"], field="normalizer total cap"
                )
            )
            if per_step is None and total is None:
                raise ValueError("normalizer feature cap must provide at least one bound")
            if (per_step is not None and per_step < 0) or (
                total is not None and total < 0
            ):
                raise ValueError("normalizer feature caps must be nonnegative")
            cap_names.append(name)
            parsed[name] = (per_step, total)
        if cap_names != sorted(set(cap_names)):
            raise ValueError("normalizer feature caps must be unique and sorted")
        missing_positive_caps = {
            name for name, weight in reward_basis if weight > 0 and name not in parsed
        }
        if missing_positive_caps:
            raise ValueError(
                "normalizer rule does not cap every positive reward-basis feature"
            )
        proof_ids.append(proof_id)
        result[proof_id] = (reward_basis, parsed)
    if proof_ids != sorted(set(proof_ids)):
        raise ValueError("normalizer proof IDs must be unique and sorted")
    return result


def _validate_transition_payload(
    document: Any,
    *,
    cell_ids: set[str],
    field: str,
    require_realization_count: bool,
) -> None:
    keys = {
        "reward_features",
        "successor_probabilities",
        "failure_probability",
        "termination_probability",
    }
    if require_realization_count:
        keys.add("realization_count")
    record = _require_exact_keys(document, keys, field)
    _validate_reward_features(record["reward_features"], f"{field}.reward_features")
    successors = _fraction_items(
        record["successor_probabilities"],
        id_field="cell_id",
        probability_field="probability",
        known_ids=cell_ids,
        field=f"{field}.successor_probabilities",
    )
    if [identifier for identifier, _ in successors] != sorted(
        identifier for identifier, _ in successors
    ):
        raise ValueError(f"{field}.successor_probabilities must be sorted")
    failure = fraction_from_json(
        record["failure_probability"], field=f"{field}.failure_probability"
    )
    termination = fraction_from_json(
        record["termination_probability"], field=f"{field}.termination_probability"
    )
    if failure < 0 or termination < 0 or failure > termination or termination > 1:
        raise ValueError(f"{field} has invalid failure/termination probabilities")
    if sum((probability for _, probability in successors), termination) != 1:
        raise ValueError(f"{field} continuation and termination mass must equal one")
    if require_realization_count:
        count = record["realization_count"]
        if isinstance(count, bool) or not isinstance(count, int) or count <= 0:
            raise ValueError(f"{field}.realization_count must be a positive integer")


def _validate_model_payload(payload: Any) -> None:
    expected = {
        "schema",
        "horizon",
        "coverage_id",
        "coverage",
        "state_catalog",
        "partition",
        "reward_features",
        "normalizer_rules",
        "goal_ids",
        "semantic_action_catalog",
        "ground_action_catalog",
        "nominal",
        "envelope",
        "concretizer_registry",
    }
    document = _require_exact_keys(payload, expected, "portable RAPM payload")
    if document["schema"] != MODEL_SCHEMA:
        raise ValueError("unsupported portable RAPM schema")
    horizon = document["horizon"]
    if isinstance(horizon, bool) or not isinstance(horizon, int) or horizon < 0:
        raise ValueError("portable RAPM horizon must be a nonnegative integer")
    coverage_id = _require_string(document["coverage_id"], "coverage_id")
    coverage = document["coverage"]
    if not isinstance(coverage, dict):
        raise ValueError("portable RAPM coverage has an invalid field set")
    mode = _require_string(coverage.get("mode"), "coverage.mode")
    if mode == "explicit_state_catalog":
        _require_exact_keys(
            coverage,
            {
                "mode",
                "covered_state_ids",
                "reuse_outside_coverage_forbidden",
            },
            "portable explicit coverage",
        )
    elif mode == "suite_support_union_transition_closure":
        _require_exact_keys(
            coverage,
            {
                "mode",
                "declared_support_set_sha256",
                "declared_support_state_ids",
                "covered_state_ids",
                "exact_state_cap",
                "admissible_query_support_rule",
                "reuse_outside_coverage_forbidden",
            },
            "portable suite coverage",
        )
        support_hash = coverage["declared_support_set_sha256"]
        if (
            not isinstance(support_hash, str)
            or len(support_hash) != 64
            or any(character not in "0123456789abcdef" for character in support_hash)
        ):
            raise ValueError("portable suite support digest must be lowercase SHA-256")
        support_ids = coverage["declared_support_state_ids"]
        if (
            not isinstance(support_ids, list)
            or support_ids != sorted(set(support_ids))
            or any(not isinstance(identifier, str) or not identifier for identifier in support_ids)
        ):
            raise ValueError("portable suite support state IDs must be unique and sorted")
        state_cap = coverage["exact_state_cap"]
        if isinstance(state_cap, bool) or not isinstance(state_cap, int) or state_cap <= 0:
            raise ValueError("portable suite exact state cap must be positive")
        if (
            coverage["admissible_query_support_rule"]
            != "positive_support_subset_of_covered_states"
        ):
            raise ValueError("portable suite coverage has an unsupported query rule")
    else:
        raise ValueError("portable RAPM coverage mode is unsupported")
    covered_ids = coverage["covered_state_ids"]
    if (
        not isinstance(covered_ids, list)
        or covered_ids != sorted(set(covered_ids))
        or any(not isinstance(identifier, str) or not identifier for identifier in covered_ids)
    ):
        raise ValueError("portable covered state IDs must be unique and sorted")
    if coverage["reuse_outside_coverage_forbidden"] is not True:
        raise ValueError("portable RAPM must forbid reuse outside recorded coverage")
    if mode == "suite_support_union_transition_closure":
        if not set(coverage["declared_support_state_ids"]).issubset(covered_ids):
            raise ValueError("portable declared support must lie inside coverage")
        if coverage["exact_state_cap"] < len(covered_ids):
            raise ValueError("portable coverage exceeds its exact state cap")
    if coverage_id != logical_id("coverage", coverage):
        raise ValueError("portable RAPM coverage content ID mismatch")

    if not isinstance(document["state_catalog"], list) or not document["state_catalog"]:
        raise ValueError("state_catalog must be a nonempty list")
    state_ids: list[str] = []
    state_kinds: dict[str, str] = {}
    for index, item in enumerate(document["state_catalog"]):
        record = _require_exact_keys(
            item, {"state_id", "planning_kind"}, f"state_catalog[{index}]"
        )
        state_id = _require_string(record["state_id"], "state_catalog.state_id")
        planning_kind = _require_string(
            record["planning_kind"], "state_catalog.planning_kind"
        )
        if planning_kind not in STATE_KINDS:
            raise ValueError("state_catalog contains an unsupported planning kind")
        state_ids.append(state_id)
        state_kinds[state_id] = planning_kind
    if state_ids != sorted(set(state_ids)):
        raise ValueError("state_catalog IDs must be unique and sorted")
    state_set = set(state_ids)
    if coverage["covered_state_ids"] != state_ids:
        raise ValueError("portable coverage must exactly match the state catalog")

    if not isinstance(document["partition"], list) or not document["partition"]:
        raise ValueError("partition must be a nonempty list")
    cell_ids: list[str] = []
    assigned_states: list[str] = []
    state_cells: dict[str, str] = {}
    active_cells: set[str] = set()
    for index, item in enumerate(document["partition"]):
        record = _require_exact_keys(
            item, {"cell_id", "member_state_ids"}, f"partition[{index}]"
        )
        cell_id = _require_string(record["cell_id"], "partition.cell_id")
        members = record["member_state_ids"]
        if not isinstance(members, list) or not members:
            raise ValueError("partition cells must contain at least one state")
        if members != sorted(set(members)) or any(member not in state_set for member in members):
            raise ValueError("partition member IDs must be known, unique, and sorted")
        if cell_id != logical_id("cell", {"member_state_ids": members}):
            raise ValueError("partition cell content ID mismatch")
        cell_ids.append(cell_id)
        assigned_states.extend(members)
        state_cells.update((member, cell_id) for member in members)
        member_kinds = {state_kinds[member] for member in members}
        if len(member_kinds) != 1:
            raise ValueError("a portable cell cannot mix planning kinds")
        if member_kinds == {"active"}:
            active_cells.add(cell_id)
    if cell_ids != sorted(set(cell_ids)):
        raise ValueError("partition cell IDs must be unique and sorted")
    if sorted(assigned_states) != state_ids:
        raise ValueError("partition must assign every catalogued state exactly once")
    cell_set = set(cell_ids)

    features = document["reward_features"]
    if (
        not isinstance(features, list)
        or any(not isinstance(name, str) or not name for name in features)
        or features != sorted(set(features))
    ):
        raise ValueError("reward_features must be unique nonempty sorted strings")
    _validate_normalizer_rules(document["normalizer_rules"], set(features))

    goal_ids = document["goal_ids"]
    if (
        not isinstance(goal_ids, list)
        or any(not isinstance(goal_id, str) or not goal_id for goal_id in goal_ids)
        or goal_ids != sorted(set(goal_ids))
    ):
        raise ValueError("goal_ids must be unique nonempty sorted strings")
    if goal_ids != ["default"]:
        raise ValueError(
            "portable RAPM v1 supports exactly the default structural stopping goal"
        )

    action_records = document["semantic_action_catalog"]
    if not isinstance(action_records, list):
        raise ValueError("semantic_action_catalog must be a list")
    action_ids: list[str] = []
    action_cells: dict[str, str] = {}
    action_source_keys: set[tuple[str, str]] = set()
    for index, item in enumerate(action_records):
        record = _require_exact_keys(
            item,
            {"action_id", "cell_id", "source_action_id"},
            f"semantic_action_catalog[{index}]",
        )
        action_id = _require_string(record["action_id"], "semantic action ID")
        cell_id = _require_string(record["cell_id"], "semantic action cell ID")
        source_id = _require_string(record["source_action_id"], "source action ID")
        if cell_id not in cell_set:
            raise ValueError("semantic action references an unknown cell")
        if action_id != logical_id(
            "semantic-action", {"cell_id": cell_id, "source_action_id": source_id}
        ):
            raise ValueError("semantic action content ID mismatch")
        source_key = (cell_id, source_id)
        if source_key in action_source_keys:
            raise ValueError("duplicate scoped semantic source action ID")
        action_source_keys.add(source_key)
        action_ids.append(action_id)
        action_cells[action_id] = cell_id
    if action_ids != sorted(set(action_ids)):
        raise ValueError("semantic action IDs must be unique and sorted")
    action_set = set(action_ids)

    ground_records = document["ground_action_catalog"]
    if not isinstance(ground_records, list):
        raise ValueError("ground_action_catalog must be a list")
    ground_ids: list[str] = []
    ground_states: dict[str, str] = {}
    ground_source_keys: set[tuple[str, str]] = set()
    for index, item in enumerate(ground_records):
        record = _require_exact_keys(
            item,
            {"ground_action_id", "state_id", "source_action_id"},
            f"ground_action_catalog[{index}]",
        )
        ground_id = _require_string(record["ground_action_id"], "ground action ID")
        state_id = _require_string(record["state_id"], "ground action state ID")
        source_id = _require_string(record["source_action_id"], "ground source action ID")
        if state_id not in state_set:
            raise ValueError("ground action references an unknown state")
        if ground_id != logical_id(
            "ground-action", {"state_id": state_id, "source_action_id": source_id}
        ):
            raise ValueError("ground action content ID mismatch")
        source_key = (state_id, source_id)
        if source_key in ground_source_keys:
            raise ValueError("duplicate scoped ground source action ID")
        ground_source_keys.add(source_key)
        ground_ids.append(ground_id)
        ground_states[ground_id] = state_id
    if ground_ids != sorted(set(ground_ids)):
        raise ValueError("ground action IDs must be unique and sorted")
    ground_set = set(ground_ids)

    nominal_records = document["nominal"]
    if not isinstance(nominal_records, list):
        raise ValueError("nominal must be a list")
    nominal_keys: list[tuple[str, str]] = []
    nominal_counts: dict[tuple[str, str], int] = {}
    nominal_models: dict[tuple[str, str], JsonObject] = {}
    transition_feature_names: set[str] = set()
    for index, item in enumerate(nominal_records):
        record = _require_exact_keys(
            item, {"cell_id", "action_id", "model"}, f"nominal[{index}]"
        )
        cell_id = _require_string(record["cell_id"], "nominal.cell_id")
        action_id = _require_string(record["action_id"], "nominal.action_id")
        if cell_id not in cell_set or action_id not in action_set:
            raise ValueError("nominal entry references an unknown cell/action")
        if action_cells[action_id] != cell_id:
            raise ValueError("nominal action is scoped to a different cell")
        _validate_transition_payload(
            record["model"],
            cell_ids=cell_set,
            field=f"nominal[{index}].model",
            require_realization_count=True,
        )
        transition_feature_names.update(
            feature["name"] for feature in record["model"]["reward_features"]
        )
        nominal_keys.append((cell_id, action_id))
        nominal_counts[(cell_id, action_id)] = record["model"]["realization_count"]
        nominal_models[(cell_id, action_id)] = record["model"]
    if nominal_keys != sorted(set(nominal_keys)):
        raise ValueError("nominal entries must have unique sorted keys")
    catalog_keys = sorted(
        (action_cells[action_id], action_id) for action_id in action_ids
    )
    if nominal_keys != catalog_keys:
        raise ValueError("semantic action catalog must exactly match nominal entries")
    cells_with_actions = {cell_id for cell_id, _ in nominal_keys}
    if cells_with_actions != active_cells:
        missing = sorted(active_cells - cells_with_actions)
        terminal_actions = sorted(cells_with_actions - active_cells)
        raise ValueError(
            "portable active/action cell mismatch; "
            f"active_without_common_action={missing!r}, "
            f"terminal_with_action={terminal_actions!r}"
        )

    envelope_records = document["envelope"]
    if not isinstance(envelope_records, list):
        raise ValueError("envelope must be a list")
    envelope_keys: list[tuple[str, str]] = []
    realization_keys: set[tuple[str, str]] = set()
    for index, item in enumerate(envelope_records):
        record = _require_exact_keys(
            item, {"cell_id", "action_id", "realizations"}, f"envelope[{index}]"
        )
        cell_id = _require_string(record["cell_id"], "envelope.cell_id")
        action_id = _require_string(record["action_id"], "envelope.action_id")
        if (cell_id, action_id) not in nominal_keys:
            raise ValueError("envelope entry has no matching nominal entry")
        realizations = record["realizations"]
        if not isinstance(realizations, list) or not realizations:
            raise ValueError("envelope entries must contain realizations")
        realization_state_ids: list[str] = []
        for realization_index, realization in enumerate(realizations):
            realized = _require_exact_keys(
                realization,
                {
                    "state_id",
                    "reward_features",
                    "successor_probabilities",
                    "failure_probability",
                    "termination_probability",
                },
                f"envelope[{index}].realizations[{realization_index}]",
            )
            state_id = _require_string(realized["state_id"], "realization.state_id")
            if state_id not in state_set:
                raise ValueError("envelope realization references an unknown state")
            if state_cells[state_id] != cell_id:
                raise ValueError("envelope realization belongs to a different partition cell")
            _validate_transition_payload(
                {key: value for key, value in realized.items() if key != "state_id"},
                cell_ids=cell_set,
                field=f"envelope[{index}].realizations[{realization_index}]",
                require_realization_count=False,
            )
            transition_feature_names.update(
                feature["name"] for feature in realized["reward_features"]
            )
            realization_state_ids.append(state_id)
            realization_keys.add((state_id, action_id))
        if realization_state_ids != sorted(set(realization_state_ids)):
            raise ValueError("envelope realization state IDs must be unique and sorted")
        expected_realization_states = sorted(
            state_id
            for state_id, assigned_cell in state_cells.items()
            if assigned_cell == cell_id and state_kinds[state_id] == "active"
        )
        if realization_state_ids != expected_realization_states:
            raise ValueError(
                "each portable semantic action must realize every active member of its cell"
            )
        if len(realization_state_ids) != nominal_counts[(cell_id, action_id)]:
            raise ValueError("nominal realization_count differs from exact envelope")
        count = len(realizations)
        reward_names = sorted(
            {
                feature["name"]
                for realization in realizations
                for feature in realization["reward_features"]
            }
        )
        successor_ids = sorted(
            {
                successor["cell_id"]
                for realization in realizations
                for successor in realization["successor_probabilities"]
            }
        )
        expected_rewards = []
        for name in reward_names:
            total = sum(
                (
                    {
                        feature["name"]: fraction_from_json(
                            feature["value"], field="envelope reward feature"
                        )
                        for feature in realization["reward_features"]
                    }.get(name, Fraction(0))
                    for realization in realizations
                ),
                Fraction(0),
            )
            expected_rewards.append(
                {"name": name, "value": fraction_to_json(total / count)}
            )
        expected_successors = []
        for successor_id in successor_ids:
            total = sum(
                (
                    {
                        successor["cell_id"]: fraction_from_json(
                            successor["probability"],
                            field="envelope successor probability",
                        )
                        for successor in realization["successor_probabilities"]
                    }.get(successor_id, Fraction(0))
                    for realization in realizations
                ),
                Fraction(0),
            )
            probability = total / count
            if probability > 0:
                expected_successors.append(
                    {
                        "cell_id": successor_id,
                        "probability": fraction_to_json(probability),
                    }
                )
        expected_nominal = {
            "reward_features": expected_rewards,
            "successor_probabilities": expected_successors,
            "failure_probability": fraction_to_json(
                sum(
                    (
                        fraction_from_json(
                            realization["failure_probability"],
                            field="envelope failure probability",
                        )
                        for realization in realizations
                    ),
                    Fraction(0),
                )
                / count
            ),
            "termination_probability": fraction_to_json(
                sum(
                    (
                        fraction_from_json(
                            realization["termination_probability"],
                            field="envelope termination probability",
                        )
                        for realization in realizations
                    ),
                    Fraction(0),
                )
                / count
            ),
            "realization_count": count,
        }
        if nominal_models[(cell_id, action_id)] != expected_nominal:
            raise ValueError("portable nominal entry is not the exact envelope average")
        envelope_keys.append((cell_id, action_id))
    if envelope_keys != nominal_keys:
        raise ValueError("nominal and envelope entry keys must match in sorted order")
    if transition_feature_names != set(features):
        raise ValueError("reward feature catalog differs from transition payloads")

    registry = document["concretizer_registry"]
    if not isinstance(registry, list):
        raise ValueError("concretizer_registry must be a list")
    registry_keys: list[tuple[str, str]] = []
    referenced_ground_ids: set[str] = set()
    semantic_owner_by_ground_id: dict[str, str] = {}
    for index, item in enumerate(registry):
        record = _require_exact_keys(
            item,
            {"state_id", "cell_id", "action_id", "support"},
            f"concretizer_registry[{index}]",
        )
        state_id = _require_string(record["state_id"], "concretizer state ID")
        cell_id = _require_string(record["cell_id"], "concretizer cell ID")
        action_id = _require_string(record["action_id"], "concretizer action ID")
        if (state_id, action_id) not in realization_keys:
            raise ValueError("concretizer entry has no matching envelope realization")
        if action_cells.get(action_id) != cell_id:
            raise ValueError("concretizer action/cell scope mismatch")
        if state_cells[state_id] != cell_id:
            raise ValueError("concretizer state/cell scope mismatch")
        support = _fraction_items(
            record["support"],
            id_field="ground_action_id",
            probability_field="probability",
            known_ids=ground_set,
            field=f"concretizer_registry[{index}].support",
        )
        if not support or sum((probability for _, probability in support), Fraction(0)) != 1:
            raise ValueError("concretizer support must be nonempty and sum to one")
        if [identifier for identifier, _ in support] != sorted(
            identifier for identifier, _ in support
        ):
            raise ValueError("concretizer support must be sorted")
        if any(ground_states[identifier] != state_id for identifier, _ in support):
            raise ValueError("concretizer ground action belongs to a different state")
        for identifier, _ in support:
            incumbent = semantic_owner_by_ground_id.get(identifier)
            if incumbent is not None and incumbent != action_id:
                raise ValueError(
                    "a ground action cannot support multiple semantic actions in one state"
                )
            semantic_owner_by_ground_id[identifier] = action_id
        referenced_ground_ids.update(identifier for identifier, _ in support)
        registry_keys.append((state_id, action_id))
    if registry_keys != sorted(realization_keys):
        raise ValueError("concretizer registry must exactly cover envelope realizations")
    if referenced_ground_ids != ground_set:
        raise ValueError("ground action catalog contains an unreferenced action")


@dataclass(frozen=True, slots=True)
class PortableRAPM:
    """Immutable canonical JSON representation of one reusable model."""

    _canonical_document: str

    @classmethod
    def from_payload(cls, payload: JsonObject) -> "PortableRAPM":
        # Round-trip first to reject non-JSON objects and detach caller-owned
        # mutable containers.
        clean = json.loads(canonical_json(payload))
        _validate_model_payload(clean)
        document = dict(clean)
        document["model_id"] = logical_id("rapm", clean)
        return cls(canonical_json(document))

    @classmethod
    def from_dict(cls, document: JsonObject) -> "PortableRAPM":
        clean = json.loads(canonical_json(document))
        if not isinstance(clean, dict) or "model_id" not in clean:
            raise ValueError("portable RAPM document is missing model_id")
        model_id = clean.pop("model_id")
        expected = logical_id("rapm", clean)
        if model_id != expected:
            raise ValueError("portable RAPM model_id mismatch")
        _validate_model_payload(clean)
        clean["model_id"] = model_id
        return cls(canonical_json(clean))

    def to_dict(self) -> JsonObject:
        return json.loads(self._canonical_document)

    @property
    def model_id(self) -> str:
        return self.to_dict()["model_id"]

    @property
    def horizon(self) -> int:
        return self.to_dict()["horizon"]

    @property
    def coverage_id(self) -> str:
        return self.to_dict()["coverage_id"]

    @property
    def cells(self) -> tuple[str, ...]:
        return tuple(record["cell_id"] for record in self.to_dict()["partition"])

    @property
    def reward_features(self) -> tuple[str, ...]:
        return tuple(self.to_dict()["reward_features"])

    @property
    def goal_ids(self) -> tuple[str, ...]:
        return tuple(self.to_dict()["goal_ids"])

    def recompute_model_id(self) -> str:
        document = self.to_dict()
        document.pop("model_id")
        return logical_id("rapm", document)


def _validate_query_payload(payload: Any, model: PortableRAPM | None = None) -> None:
    document = _require_exact_keys(
        payload,
        {
            "schema",
            "model_id",
            "initial_distribution",
            "horizon",
            "reward_weights",
            "normalizer",
            "normalizer_proof_id",
            "normalized_reward_weights",
            "goal_id",
            "delta",
        },
        "portable query payload",
    )
    if document["schema"] != QUERY_SCHEMA:
        raise ValueError("unsupported portable query schema")
    _require_string(document["model_id"], "query.model_id")
    horizon = document["horizon"]
    if isinstance(horizon, bool) or not isinstance(horizon, int) or horizon < 0:
        raise ValueError("portable query horizon must be a nonnegative integer")
    known_cells = set(model.cells) if model is not None else None
    distribution = _fraction_items(
        document["initial_distribution"],
        id_field="cell_id",
        probability_field="probability",
        known_ids=known_cells,
        field="query.initial_distribution",
    )
    if not distribution or sum((probability for _, probability in distribution), Fraction(0)) != 1:
        raise ValueError("portable query initial distribution must have mass one")
    if [cell_id for cell_id, _ in distribution] != sorted(cell_id for cell_id, _ in distribution):
        raise ValueError("portable query initial distribution must be sorted")
    raw_weights = _validate_reward_features(document["reward_weights"], "query.reward_weights")
    if any(value < 0 for _, value in raw_weights):
        raise ValueError("portable query reward weights must be nonnegative")
    normalizer = fraction_from_json(document["normalizer"], field="query.normalizer")
    if normalizer <= 0:
        raise ValueError("portable query normalizer must be positive")
    proof_id = _require_string(
        document["normalizer_proof_id"], "query.normalizer_proof_id"
    )
    weights = _validate_reward_features(
        document["normalized_reward_weights"], "query.normalized_reward_weights"
    )
    expected_weights = tuple((name, value / normalizer) for name, value in raw_weights)
    if weights != expected_weights:
        raise ValueError(
            "portable query normalized reward weights do not match raw weights/normalizer"
        )
    goal_id = _require_string(document["goal_id"], "query.goal_id")
    delta = fraction_from_json(document["delta"], field="query.delta")
    if delta not in {Fraction(0), Fraction(1, 20), Fraction(1, 10)}:
        raise ValueError("portable query delta must be one of 0, 0.05, or 0.10")
    if model is not None:
        if document["model_id"] != model.model_id:
            raise ValueError("portable query/model mismatch")
        if horizon > model.horizon:
            raise ValueError("portable query horizon exceeds model horizon")
        unknown_features = {name for name, _ in weights} - set(model.reward_features)
        if unknown_features:
            raise ValueError(f"portable query uses unknown reward features: {unknown_features!r}")
        normalizer_rules = _validate_normalizer_rules(
            model.to_dict()["normalizer_rules"], set(model.reward_features)
        )
        try:
            registered_basis, caps = normalizer_rules[proof_id]
        except KeyError as error:
            raise ValueError(
                f"portable query uses an unregistered normalizer proof: {proof_id!r}"
            ) from error
        if raw_weights != registered_basis:
            raise ValueError(
                "portable query reward weights do not match its registered "
                "normalizer proof basis"
            )
        proved_bound = Fraction(0)
        for name, weight in raw_weights:
            if weight == 0:
                continue
            try:
                per_step_cap, total_cap = caps[name]
            except KeyError as error:
                raise ValueError(
                    f"normalizer proof does not bound reward feature {name!r}"
                ) from error
            candidates = []
            if per_step_cap is not None:
                candidates.append(per_step_cap * horizon)
            if total_cap is not None:
                candidates.append(total_cap)
            proved_bound += weight * min(candidates)
        if normalizer < proved_bound:
            raise ValueError(
                "portable query normalizer is below its registered deterministic bound"
            )
        if goal_id not in set(model.goal_ids):
            raise ValueError(f"portable query uses unknown goal: {goal_id!r}")
        model_document = model.to_dict()
        kind_by_state = {
            record["state_id"]: record["planning_kind"]
            for record in model_document["state_catalog"]
        }
        failure_cells = {
            cell["cell_id"]
            for cell in model_document["partition"]
            if all(
                kind_by_state[state_id] == "failure"
                for state_id in cell["member_state_ids"]
            )
        }
        if any(cell_id in failure_cells for cell_id, _ in distribution):
            raise ValueError(
                "portable queries cannot place initial mass on an already-failed cell"
            )


@dataclass(frozen=True, slots=True)
class PortableQuery:
    """A model-bound query containing only cell-level planning inputs."""

    _canonical_document: str

    @classmethod
    def from_cells(
        cls,
        model: PortableRAPM,
        initial_distribution: Iterable[tuple[Fraction | int | str, str]],
        horizon: int,
        reward_weights: Mapping[str, Fraction | int | str]
        | Iterable[tuple[str, Fraction | int | str]],
        normalizer: Fraction | int | str,
        normalizer_proof_id: str,
        goal_id: str,
        delta: Fraction | int | str,
    ) -> "PortableQuery":
        masses: dict[str, Fraction] = {}
        for probability, cell_id in initial_distribution:
            probability_value = (
                probability if isinstance(probability, Fraction) else Fraction(probability)
            )
            masses[cell_id] = masses.get(cell_id, Fraction(0)) + probability_value
        raw_weights = (
            reward_weights.items()
            if isinstance(reward_weights, Mapping)
            else reward_weights
        )
        weights: dict[str, Fraction] = {}
        for name, value in raw_weights:
            if name in weights:
                raise ValueError("reward weights contain a duplicate feature")
            weights[name] = value if isinstance(value, Fraction) else Fraction(value)
        normalizer_value = (
            normalizer if isinstance(normalizer, Fraction) else Fraction(normalizer)
        )
        if normalizer_value <= 0:
            raise ValueError("portable query normalizer must be positive")
        payload = {
            "schema": QUERY_SCHEMA,
            "model_id": model.model_id,
            "initial_distribution": [
                {"cell_id": cell_id, "probability": fraction_to_json(probability)}
                for cell_id, probability in sorted(masses.items())
                if probability != 0
            ],
            "horizon": horizon,
            "reward_weights": [
                {"name": name, "value": fraction_to_json(value)}
                for name, value in sorted(weights.items())
            ],
            "normalizer": fraction_to_json(normalizer_value),
            "normalizer_proof_id": normalizer_proof_id,
            "normalized_reward_weights": [
                {"name": name, "value": fraction_to_json(value / normalizer_value)}
                for name, value in sorted(weights.items())
            ],
            "goal_id": goal_id,
            "delta": fraction_to_json(delta),
        }
        _validate_query_payload(payload, model)
        document = dict(payload)
        document["query_id"] = logical_id("query", payload)
        return cls(canonical_json(document))

    @classmethod
    def from_dict(
        cls, document: JsonObject, model: PortableRAPM | None = None
    ) -> "PortableQuery":
        clean = json.loads(canonical_json(document))
        if not isinstance(clean, dict) or "query_id" not in clean:
            raise ValueError("portable query document is missing query_id")
        query_id = clean.pop("query_id")
        expected = logical_id("query", clean)
        if query_id != expected:
            raise ValueError("portable query query_id mismatch")
        _validate_query_payload(clean, model)
        clean["query_id"] = query_id
        return cls(canonical_json(clean))

    def to_dict(self) -> JsonObject:
        return json.loads(self._canonical_document)

    @property
    def query_id(self) -> str:
        return self.to_dict()["query_id"]

    @property
    def model_id(self) -> str:
        return self.to_dict()["model_id"]

    @property
    def horizon(self) -> int:
        return self.to_dict()["horizon"]

    @property
    def goal_id(self) -> str:
        return self.to_dict()["goal_id"]

    def recompute_query_id(self) -> str:
        document = self.to_dict()
        document.pop("query_id")
        return logical_id("query", document)


@dataclass(frozen=True)
class PortableRegistry:
    """Ephemeral bridge between construction objects and portable IDs."""

    state_records: tuple[tuple[Hashable, str], ...]
    cell_records: tuple[tuple[Hashable, str], ...]
    semantic_action_records: tuple[tuple[Hashable, Hashable, str], ...]
    ground_action_records: tuple[tuple[Hashable, Hashable, str], ...]

    def state_id(self, state: Hashable) -> str:
        for candidate, identifier in self.state_records:
            if candidate == state:
                return identifier
        raise KeyError(f"unknown construction state {state!r}")

    def cell_id(self, cell: Hashable) -> str:
        for candidate, identifier in self.cell_records:
            if candidate == cell:
                return identifier
        raise KeyError(f"unknown construction cell {cell!r}")

    def semantic_action_id(self, cell: Hashable, action: Hashable) -> str:
        for candidate_cell, candidate_action, identifier in self.semantic_action_records:
            if candidate_cell == cell and candidate_action == action:
                return identifier
        raise KeyError(f"unknown construction semantic action {cell!r}/{action!r}")

    def ground_action_id(self, state: Hashable, action: Hashable) -> str:
        for candidate_state, candidate_action, identifier in self.ground_action_records:
            if candidate_state == state and candidate_action == action:
                return identifier
        raise KeyError(f"unknown construction ground action {state!r}/{action!r}")

    def decode_policy(self, portable_policy: Any) -> dict[tuple[int, Hashable], Hashable]:
        """Decode a portable policy into the caller's original cell/action objects."""

        cells = {identifier: cell for cell, identifier in self.cell_records}
        actions = {
            (identifier, action_id): action
            for cell, identifier in self.cell_records
            for candidate_cell, action, action_id in self.semantic_action_records
            if candidate_cell == cell
        }
        result: dict[tuple[int, Hashable], Hashable] = {}
        for decision in portable_policy.decisions:
            try:
                cell = cells[decision.cell_id]
                action = actions[(decision.cell_id, decision.action_id)]
            except KeyError as error:
                raise ValueError("portable policy is incompatible with this registry") from error
            result[(decision.remaining, cell)] = action
        return result


@dataclass(frozen=True)
class PortableSerializedAdapter:
    """Ground-object bridge whose action supports come from serialized kappa."""

    model: PortableRAPM
    registry: PortableRegistry

    def _cell(self, state: Hashable) -> tuple[Hashable, str]:
        state_id = self.registry.state_id(state)
        cell_by_id = {identifier: cell for cell, identifier in self.registry.cell_records}
        for record in self.model.to_dict()["partition"]:
            if state_id in record["member_state_ids"]:
                return cell_by_id[record["cell_id"]], record["cell_id"]
        raise ValueError("state is absent from the serialized portable partition")

    def labels(self, _kernel: Any, state: Hashable) -> tuple[Hashable, ...]:
        cell, _ = self._cell(state)
        return tuple(
            sorted(
                (
                    action
                    for candidate_cell, action, _ in self.registry.semantic_action_records
                    if candidate_cell == cell
                ),
                key=repr,
            )
        )

    def concretize(
        self, _kernel: Any, state: Hashable, semantic_action: Hashable
    ) -> tuple[tuple[Fraction, Hashable], ...]:
        cell, cell_id = self._cell(state)
        state_id = self.registry.state_id(state)
        action_id = self.registry.semantic_action_id(cell, semantic_action)
        ground_by_id = {
            identifier: action
            for candidate_state, action, identifier in self.registry.ground_action_records
            if candidate_state == state
        }
        for record in self.model.to_dict()["concretizer_registry"]:
            if (
                record["state_id"] == state_id
                and record["cell_id"] == cell_id
                and record["action_id"] == action_id
            ):
                try:
                    return tuple(
                        (
                            fraction_from_json(
                                support["probability"],
                                field="serialized concretizer probability",
                            ),
                            ground_by_id[support["ground_action_id"]],
                        )
                        for support in record["support"]
                    )
                except KeyError as error:
                    raise ValueError(
                        "serialized concretizer cannot be decoded by this registry"
                    ) from error
        raise ValueError("serialized concretizer has no state/action entry")


@dataclass(frozen=True)
class PortableBuildResult:
    model: PortableRAPM
    registry: PortableRegistry

    def query_from_spec(self, query: Any) -> PortableQuery:
        normalizer = Fraction(query.normalizer)
        if normalizer <= 0:
            raise ValueError("query normalizer must be positive")
        cell_by_state = dict(self.model_partition_assignments())
        initial: dict[str, Fraction] = {}
        for probability, state in query.initial_distribution:
            try:
                cell = cell_by_state[state]
            except KeyError as error:
                raise ValueError(
                    f"query state {state!r} lies outside portable model coverage"
                ) from error
            cell_id = self.registry.cell_id(cell)
            initial[cell_id] = initial.get(cell_id, Fraction(0)) + Fraction(probability)
        return PortableQuery.from_cells(
            self.model,
            tuple((probability, cell_id) for cell_id, probability in initial.items()),
            int(query.horizon),
            tuple((name, Fraction(weight)) for name, weight in query.reward_weights),
            normalizer,
            str(query.normalizer_proof_id),
            str(query.goal),
            Fraction(query.delta),
        )

    def model_partition_assignments(self) -> tuple[tuple[Hashable, Hashable], ...]:
        cell_by_id = {identifier: cell for cell, identifier in self.registry.cell_records}
        state_by_id = {identifier: state for state, identifier in self.registry.state_records}
        assignments: list[tuple[Hashable, Hashable]] = []
        for record in self.model.to_dict()["partition"]:
            cell = cell_by_id[record["cell_id"]]
            assignments.extend((state_by_id[state_id], cell) for state_id in record["member_state_ids"])
        return tuple(assignments)

    def decode_policy(self, portable_policy: Any) -> dict[tuple[int, Hashable], Hashable]:
        return self.registry.decode_policy(portable_policy)

    def serialized_adapter(self) -> PortableSerializedAdapter:
        return PortableSerializedAdapter(self.model, self.registry)


def _source_id(source: IdSource, value: Hashable, field: str) -> str:
    try:
        identifier = source(value) if callable(source) else source[value]
    except (KeyError, TypeError) as error:
        raise ValueError(f"missing stable {field} for {value!r}") from error
    return _require_string(identifier, field)


def _state_kind(
    source: StateKindSource | None,
    envelope: Any,
    state: Hashable,
) -> str:
    if source is None:
        # Every authoritative active V0 state has at least one semantic action;
        # terminal states have none.  The portable builder later rejects an
        # active cell whose labels have an empty common intersection.
        kind = "active" if tuple(envelope.semantic_action_provider(state)) else "terminal"
    else:
        try:
            kind = source(state) if callable(source) else source[state]
        except (KeyError, TypeError) as error:
            raise ValueError(f"missing planning kind for {state!r}") from error
    kind = _require_string(kind, "planning kind")
    if kind not in STATE_KINDS:
        raise ValueError(f"unsupported planning kind {kind!r}")
    return kind


def _reward_document(items: Iterable[tuple[str, Fraction]]) -> list[JsonObject]:
    return [
        {"name": str(name), "value": fraction_to_json(value)}
        for name, value in sorted(items)
    ]


def _successor_document(items: Iterable[tuple[str, Fraction]]) -> list[JsonObject]:
    return [
        {"cell_id": cell_id, "probability": fraction_to_json(probability)}
        for cell_id, probability in sorted(items)
        if probability > 0
    ]


def build_portable_rapm(
    models: QuotientModels,
    *,
    state_ids: IdSource,
    semantic_action_ids: IdSource,
    ground_action_ids: IdSource,
    normalizer_rules: Iterable[Mapping[str, Any]],
    state_kinds: StateKindSource | None = None,
    goal_ids: Iterable[str] = ("default",),
    coverage: Mapping[str, Any] | None = None,
) -> PortableBuildResult:
    """Freeze one in-memory quotient and its concretizer into portable JSON.

    ``state_ids`` and both action-ID sources supply stable, domain-owned keys.
    Cell IDs are hashes of member state IDs; semantic action IDs are hashes of
    their source key scoped by the cell; ground action IDs are similarly scoped
    by state.  This prevents accidental aliasing when a label is reused.
    """

    nominal = models.nominal
    envelope = models.envelope
    if nominal.partition != envelope.partition or nominal.horizon != envelope.horizon:
        raise ValueError("nominal model and envelope do not describe the same quotient")
    partition = nominal.partition
    portable_goal_ids = sorted(set(goal_ids))
    if not portable_goal_ids or any(
        not isinstance(goal_id, str) or not goal_id for goal_id in portable_goal_ids
    ):
        raise ValueError("portable goal IDs must be nonempty strings")

    state_records = tuple(
        (state, _source_id(state_ids, state, "state ID")) for state in partition.states
    )
    all_state_ids = [identifier for _, identifier in state_records]
    if len(set(all_state_ids)) != len(all_state_ids):
        raise ValueError("stable state IDs must be globally unique")
    state_id_by_state = dict(state_records)
    state_kind_by_state = {
        state: _state_kind(state_kinds, envelope, state)
        for state in partition.states
    }
    coverage_document: JsonObject = (
        {
            "mode": "explicit_state_catalog",
            "covered_state_ids": sorted(all_state_ids),
            "reuse_outside_coverage_forbidden": True,
        }
        if coverage is None
        else json.loads(canonical_json(dict(coverage)))
    )
    if coverage_document.get("covered_state_ids") != sorted(all_state_ids):
        raise ValueError("portable coverage does not match the supplied quotient states")
    coverage_id = logical_id("coverage", coverage_document)

    cell_records_list: list[tuple[Hashable, str]] = []
    partition_document: list[JsonObject] = []
    for cell in partition.cell_ids:
        members = sorted(state_id_by_state[state] for state in partition.members(cell))
        cell_id = logical_id("cell", {"member_state_ids": members})
        cell_records_list.append((cell, cell_id))
        partition_document.append({"cell_id": cell_id, "member_state_ids": members})
    cell_records = tuple(cell_records_list)
    cell_id_by_cell = dict(cell_records)

    semantic_records_list: list[tuple[Hashable, Hashable, str]] = []
    semantic_catalog: list[JsonObject] = []
    semantic_source_seen: dict[tuple[str, str], Hashable] = {}
    envelope_entry_by_key = {(entry.cell, entry.action): entry for entry in envelope.entries}
    nominal_entry_by_key = {(entry.cell, entry.action): entry for entry in nominal.entries}
    if set(envelope_entry_by_key) != set(nominal_entry_by_key):
        raise ValueError("nominal and envelope semantic action sets differ")
    for cell, action in sorted(envelope_entry_by_key, key=lambda item: (repr(item[0]), repr(item[1]))):
        cell_id = cell_id_by_cell[cell]
        source_id = _source_id(semantic_action_ids, action, "semantic action ID")
        scoped_key = (cell_id, source_id)
        incumbent = semantic_source_seen.get(scoped_key)
        if incumbent is not None and incumbent != action:
            raise ValueError("semantic action source IDs collide within a quotient cell")
        semantic_source_seen[scoped_key] = action
        action_id = logical_id(
            "semantic-action", {"cell_id": cell_id, "source_action_id": source_id}
        )
        semantic_records_list.append((cell, action, action_id))
        semantic_catalog.append(
            {"action_id": action_id, "cell_id": cell_id, "source_action_id": source_id}
        )
    semantic_records = tuple(semantic_records_list)
    semantic_id_by_key = {
        (cell, action): identifier for cell, action, identifier in semantic_records
    }

    reward_features = sorted(
        {
            name
            for entry in envelope.entries
            for realization in entry.realizations
            for name, _ in realization.reward_features
        }
        | {
            name
            for entry in nominal.entries
            for name, _ in entry.model.reward_features
        }
    )
    normalizer_rule_document = json.loads(
        canonical_json(list(normalizer_rules))
    )
    _validate_normalizer_rules(normalizer_rule_document, set(reward_features))

    nominal_document: list[JsonObject] = []
    envelope_document: list[JsonObject] = []
    concretizer_document: list[JsonObject] = []
    ground_records_list: list[tuple[Hashable, Hashable, str]] = []
    ground_catalog_by_id: dict[str, JsonObject] = {}
    ground_source_seen: dict[tuple[str, str], Hashable] = {}

    for key in sorted(envelope_entry_by_key, key=lambda item: (repr(item[0]), repr(item[1]))):
        cell, action = key
        cell_id = cell_id_by_cell[cell]
        action_id = semantic_id_by_key[key]
        nominal_model = nominal_entry_by_key[key].model
        nominal_document.append(
            {
                "cell_id": cell_id,
                "action_id": action_id,
                "model": {
                    "reward_features": _reward_document(nominal_model.reward_features),
                    "successor_probabilities": _successor_document(
                        (cell_id_by_cell[successor], probability)
                        for successor, probability in nominal_model.successor_probabilities
                    ),
                    "failure_probability": fraction_to_json(
                        nominal_model.failure_probability
                    ),
                    "termination_probability": fraction_to_json(
                        nominal_model.termination_probability
                    ),
                    "realization_count": nominal_model.realization_count,
                },
            }
        )
        realization_documents: list[JsonObject] = []
        entry = envelope_entry_by_key[key]
        for realization in sorted(entry.realizations, key=lambda item: state_id_by_state[item.state]):
            state = realization.state
            state_id = state_id_by_state[state]
            realization_documents.append(
                {
                    "state_id": state_id,
                    "reward_features": _reward_document(realization.reward_features),
                    "successor_probabilities": _successor_document(
                        (cell_id_by_cell[successor], probability)
                        for successor, probability in realization.successor_probabilities
                    ),
                    "failure_probability": fraction_to_json(
                        realization.failure_probability
                    ),
                    "termination_probability": fraction_to_json(
                        realization.termination_probability
                    ),
                }
            )

            raw_support = tuple(envelope.concretizer(state, action))
            if not raw_support:
                raise ValueError("frozen concretizer returned empty support")
            support_by_ground_id: dict[str, Fraction] = {}
            for probability, ground_action in raw_support:
                probability_value = Fraction(probability)
                if probability_value <= 0:
                    raise ValueError("frozen concretizer probabilities must be positive")
                source_id = _source_id(
                    ground_action_ids, ground_action, "ground action ID"
                )
                scoped_key = (state_id, source_id)
                incumbent = ground_source_seen.get(scoped_key)
                if incumbent is not None and incumbent != ground_action:
                    raise ValueError("ground action source IDs collide within a state")
                ground_source_seen[scoped_key] = ground_action
                ground_id = logical_id(
                    "ground-action",
                    {"state_id": state_id, "source_action_id": source_id},
                )
                support_by_ground_id[ground_id] = (
                    support_by_ground_id.get(ground_id, Fraction(0)) + probability_value
                )
                if ground_id not in ground_catalog_by_id:
                    ground_catalog_by_id[ground_id] = {
                        "ground_action_id": ground_id,
                        "state_id": state_id,
                        "source_action_id": source_id,
                    }
                    ground_records_list.append((state, ground_action, ground_id))
            if sum(support_by_ground_id.values(), Fraction(0)) != 1:
                raise ValueError("frozen concretizer probabilities must sum to one")
            concretizer_document.append(
                {
                    "state_id": state_id,
                    "cell_id": cell_id,
                    "action_id": action_id,
                    "support": [
                        {
                            "ground_action_id": ground_id,
                            "probability": fraction_to_json(probability),
                        }
                        for ground_id, probability in sorted(support_by_ground_id.items())
                    ],
                }
            )
        envelope_document.append(
            {
                "cell_id": cell_id,
                "action_id": action_id,
                "realizations": realization_documents,
            }
        )

    # Canonical order is by portable identifiers, not Python repr.  This makes
    # the logical model independent of construction-object ordering.
    partition_document.sort(key=lambda record: record["cell_id"])
    semantic_catalog.sort(key=lambda record: record["action_id"])
    nominal_document.sort(key=lambda record: (record["cell_id"], record["action_id"]))
    envelope_document.sort(key=lambda record: (record["cell_id"], record["action_id"]))
    concretizer_document.sort(key=lambda record: (record["state_id"], record["action_id"]))
    ground_catalog = sorted(
        ground_catalog_by_id.values(), key=lambda record: record["ground_action_id"]
    )

    payload = {
        "schema": MODEL_SCHEMA,
        "horizon": nominal.horizon,
        "coverage_id": coverage_id,
        "coverage": coverage_document,
        "state_catalog": [
            {
                "state_id": state_id,
                "planning_kind": state_kind_by_state[state],
            }
            for state, state_id in sorted(state_records, key=lambda record: record[1])
        ],
        "partition": partition_document,
        "reward_features": reward_features,
        "normalizer_rules": normalizer_rule_document,
        "goal_ids": portable_goal_ids,
        "semantic_action_catalog": semantic_catalog,
        "ground_action_catalog": ground_catalog,
        "nominal": nominal_document,
        "envelope": envelope_document,
        "concretizer_registry": concretizer_document,
    }
    model = PortableRAPM.from_payload(payload)
    registry = PortableRegistry(
        state_records,
        cell_records,
        semantic_records,
        tuple(ground_records_list),
    )
    return PortableBuildResult(model, registry)


def dump_model(model: PortableRAPM, path: str | Path) -> None:
    Path(path).write_text(canonical_json(model.to_dict()) + "\n", encoding="utf-8")


def load_model(path: str | Path) -> PortableRAPM:
    return PortableRAPM.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))


def dump_query(query: PortableQuery, path: str | Path) -> None:
    Path(path).write_text(canonical_json(query.to_dict()) + "\n", encoding="utf-8")


def load_query(path: str | Path, model: PortableRAPM | None = None) -> PortableQuery:
    return PortableQuery.from_dict(
        json.loads(Path(path).read_text(encoding="utf-8")), model
    )


__all__ = [
    "MODEL_SCHEMA",
    "QUERY_SCHEMA",
    "STATE_KINDS",
    "StateKindSource",
    "PortableBuildResult",
    "PortableQuery",
    "PortableRAPM",
    "PortableRegistry",
    "PortableSerializedAdapter",
    "build_portable_rapm",
    "canonical_json",
    "dump_model",
    "dump_query",
    "fraction_from_json",
    "fraction_to_json",
    "load_model",
    "load_query",
    "logical_id",
]
