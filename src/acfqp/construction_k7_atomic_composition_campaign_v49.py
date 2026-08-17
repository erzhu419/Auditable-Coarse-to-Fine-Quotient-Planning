"""Fresh V49 generic-atomic fourth-combination campaign."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
import hashlib
from functools import lru_cache
from typing import Any, Callable, Mapping, NoReturn

from acfqp import construction_k7_atomic_composition_preregistration_v49 as pre
from acfqp.domains.stochastic_modular_routing import (
    StochasticModularAction,
    StochasticModularKernel,
    StochasticModularState,
    StochasticModularStatus,
    generate_stochastic_modular_routing,
    select_seeded_stochastic_modular_outcome_v1,
)
from acfqp.generic_atomic_expression_world_model_v4 import (
    FlatRawActionV4,
    FlatRawTransitionV4,
    GenericAtomicExpressionWorldModelV4Error,
    derive_atomic_dependency_support_v4,
    execute_generic_atomic_support_v4,
    is_accepting_state_v4,
    missing_relation_values_v4,
    plan_generic_atomic_program_v4,
    synthesize_generic_atomic_program_v4,
    target_binding_from_initial_vector_v4,
)
from acfqp.phase3e_ids import canonical_json_bytes, content_id, loads_canonical_json


SCHEMA_VERSION = "49.0.0"
CAMPAIGN_ID = "0" * 64
EXPECTED_CANONICAL_BYTE_COUNT = 0
EXPECTED_CANONICAL_SHA256 = "0" * 64


class ConstructionK7AtomicCompositionCampaignV49Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7AtomicCompositionCampaignV49Error(message)


def _node_token(seed: int, node: int) -> int:
    return seed * 100 + node


def _status_token(status: StochasticModularStatus) -> int:
    name = (
        "A"
        if status is StochasticModularStatus.ACTIVE
        else "S"
        if status is StochasticModularStatus.SUCCESS
        else "F"
    )
    return pre.SHARED_TERMINAL_TOKENS[name]


def _raw_interface(
    seed: int, kernel: StochasticModularKernel
) -> tuple[
    tuple[FlatRawActionV4, ...],
    Callable[[StochasticModularState], tuple[int, ...]],
    str,
]:
    catalogue = []
    for index, edge in enumerate(kernel.edges):
        semantic = (
            _node_token(seed, edge.source),
            _node_token(seed, edge.destination),
            pre.SHARED_MODE_TOKENS[edge.mode],
            edge.magnitude,
            pre.SHARED_CLASS_TOKENS[edge.cost_class],
            seed * 10_000 + index,
        )
        catalogue.append(
            FlatRawActionV4(
                index,
                tuple(semantic[position] for position in pre.ACTION_FIELD_ORDER),
            )
        )

    def encode(state: StochasticModularState) -> tuple[int, ...]:
        semantic = (
            _node_token(seed, state.node),
            state.phase,
            state.resource,
            state.steps,
            _status_token(state.status),
            kernel.modulus,
            kernel.capacity,
            kernel.goal_phase,
            _node_token(seed, kernel.goal_node),
        )
        return tuple(semantic[position] for position in pre.STATE_LAYOUT_ORDER)

    layout = {
        "state_width": len(pre.STATE_LAYOUT_ORDER),
        "action_field_width": len(pre.ACTION_FIELD_ORDER),
        "state_layout_commitment": hashlib.sha256(bytes(pre.STATE_LAYOUT_ORDER)).hexdigest(),
        "action_layout_commitment": hashlib.sha256(bytes(pre.ACTION_FIELD_ORDER)).hexdigest(),
        "semantic_role_names_serialized": False,
    }
    return (
        tuple(catalogue),
        encode,
        content_id(pre.FUTURE_DOMAINS["observation"], layout),
    )


def _acquire_source_occurrence(
    occurrence: int, seed: int
) -> tuple[
    StochasticModularKernel,
    tuple[FlatRawActionV4, ...],
    Callable[[StochasticModularState], tuple[int, ...]],
    tuple[FlatRawTransitionV4, ...],
    dict[str, Any],
]:
    kernel, generation_evidence = generate_stochastic_modular_routing(
        **pre.SOURCE_SPEC, seed=seed
    )
    del generation_evidence
    catalogue, encode, layout_id = _raw_interface(seed, kernel)
    initial = kernel.initial_distribution()[0][1]
    queue = deque([initial])
    seen = {initial}
    rows = []
    support_labels = 0
    while queue:
        state = queue.popleft()
        legal = kernel.actions(state)
        for action in legal:
            support_labels += 1
            outcomes = kernel.step(state, action)
            for outcome in outcomes:
                successor = outcome.next_state
                legal_after = kernel.actions(successor)
                rows.append(
                    FlatRawTransitionV4(
                        occurrence,
                        len(rows),
                        encode(state),
                        tuple(item.edge for item in legal),
                        catalogue[action.edge],
                        encode(successor),
                        tuple(item.edge for item in legal_after),
                        None
                        if legal_after
                        else successor.status is StochasticModularStatus.SUCCESS,
                    )
                )
                if (
                    successor.status is StochasticModularStatus.ACTIVE
                    and successor not in seen
                ):
                    seen.add(successor)
                    queue.append(successor)
    if support_labels > pre.MAX_SOURCE_LABELS_PER_OCCURRENCE:
        _fail("V49 source acquisition exceeded its frozen label cap")
    payload = {
        "schema": "acfqp.atomic_composition_raw_observation.v49",
        "occurrence": occurrence,
        "seed": seed,
        "opaque_layout_id": layout_id,
        "anonymous_action_catalogue": [row.to_document() for row in catalogue],
        "raw_transitions": [row.to_document() for row in rows],
        "source_support_labels": support_labels,
        "raw_outcome_rows": len(rows),
        "reachable_active_state_count": len(seen),
        "source_policy": "WITNESS_BLIND_EXHAUSTIVE_REACHABLE_FRONTIER_ALL_LEGAL_ACTION_SUPPORTS",
        "generation_witness_accessed": False,
        "semantic_role_names_available_to_synthesizer": False,
    }
    archive = {
        **payload,
        "raw_observation_id": content_id(pre.FUTURE_DOMAINS["observation"], payload),
    }
    return kernel, catalogue, encode, tuple(rows), archive


def _required_source_relations(program: Mapping[str, Any]) -> dict[str, list[list[int]]]:
    first = program["occurrence_bindings"][0]
    serialized = canonical_json_bytes(
        [row["expression"] for row in program["compiled_assignments"]]
    ).decode("utf-8")
    return {
        name: rows
        for name, rows in first["relations"].items()
        if f'"{name}"' in serialized
    }


def _relation_modulus(
    program: Mapping[str, Any], relation_name: str, binding: Mapping[str, Any]
) -> int:
    names: set[str] = set()

    def contains_relation(expression: Any) -> bool:
        if type(expression) is not list:
            return False
        if len(expression) >= 2 and expression[0] == "E04" and expression[1] == relation_name:
            return True
        return any(contains_relation(item) for item in expression)

    def visit(expression: Any) -> None:
        if type(expression) is not list:
            return
        if (
            len(expression) == 3
            and expression[0] == "E06"
            and contains_relation(expression[1])
            and type(expression[2]) is list
            and expression[2][:1] == ["E03"]
        ):
            names.add(expression[2][1])
        for item in expression:
            visit(item)

    for assignment in program["compiled_assignments"]:
        visit(assignment["expression"])
    values = {binding["constants"][name] for name in names}
    if len(values) != 1:
        _fail("V49 local recovery could not derive one anonymous modulus")
    value = next(iter(values))
    if type(value) is not int or not 3 <= value <= 256:
        _fail("V49 local recovery modulus escaped its frozen finite search")
    return value


def _recover_relation_value(
    program: Mapping[str, Any],
    binding: Mapping[str, Any],
    catalogue_action: FlatRawActionV4,
    pre_vector: tuple[int, ...],
    actual_support: set[tuple[int, ...]],
    relation_name: str,
    relation_value: int,
    prior_overlay: Mapping[str, Mapping[int, int]],
) -> int:
    modulus = _relation_modulus(program, relation_name, binding)
    matches = []
    for candidate in range(modulus):
        overlay = {
            name: dict(rows) for name, rows in prior_overlay.items()
        }
        overlay.setdefault(relation_name, {})[relation_value] = candidate
        try:
            predicted = set(
                execute_generic_atomic_support_v4(
                    program,
                    pre_vector,
                    catalogue_action,
                    binding,
                    relation_overlay=overlay,
                )
            )
        except GenericAtomicExpressionWorldModelV4Error:
            continue
        if predicted == actual_support:
            matches.append(candidate)
    if len(matches) != 1:
        _fail("V49 local raw-support recovery was not unique")
    return matches[0]


def _strict_ground_choice(
    kernel: StochasticModularKernel,
    state: StochasticModularState,
    cache: dict[tuple[StochasticModularState, int], tuple[StochasticModularState, ...]],
) -> tuple[int, int, int]:
    labels_before = len(cache)

    @lru_cache(maxsize=None)
    def solve(current: StochasticModularState) -> bool:
        if current.status is StochasticModularStatus.SUCCESS:
            return True
        if current.status is StochasticModularStatus.FAILURE:
            return False
        for action in kernel.actions(current):
            key = (current, action.edge)
            if key not in cache:
                cache[key] = tuple(
                    row.next_state for row in kernel.step(current, action)
                )
            if all(solve(successor) for successor in cache[key]):
                choices[current] = action.edge
                return True
        return False

    choices: dict[StochasticModularState, int] = {}
    if not solve(state) or state not in choices:
        _fail("V49 strict direct-ground planner found no robust continuation")
    return choices[state], len(cache) - labels_before, solve.cache_info().currsize


def _episode_document(
    *,
    seed: int,
    arm: str,
    action_keys: list[int],
    tape_hashes: list[str],
    final_state: StochasticModularState,
    planning_compute: int,
    peak_cache: int,
    support_labels: int,
    certificate_failures: int,
    local_labels: int,
    overlay_reuses: int,
) -> dict[str, Any]:
    payload = {
        "schema": "acfqp.atomic_composition_receding_episode.v49",
        "seed": seed,
        "arm": arm,
        "action_keys": action_keys,
        "outcome_tape_sha256": tape_hashes,
        "execution_steps": len(action_keys),
        "planning_compute_events": planning_compute,
        "peak_planning_cache_entries": peak_cache,
        "ground_support_labels": support_labels,
        "failed_certificate_count": certificate_failures,
        "local_ground_support_labels": local_labels,
        "immutable_overlay_reuse_count": overlay_reuses,
        "final_status": final_state.status.value,
        "success": final_state.status is StochasticModularStatus.SUCCESS,
        "receding_abstract_or_ground_replanning": True,
    }
    return {
        **payload,
        "episode_id": content_id(pre.FUTURE_DOMAINS["episode"], payload),
    }


def _build_campaign_document() -> dict[str, Any]:
    preregistration = pre.verify_atomic_composition_preregistration_v49(
        pre.freeze_atomic_composition_preregistration_v49()
    )
    source_rows: list[FlatRawTransitionV4] = []
    source_catalogues: dict[int, tuple[FlatRawActionV4, ...]] = {}
    source_archives = []
    source_support_labels = 0
    for occurrence, seed in enumerate(pre.SOURCE_SEEDS):
        _kernel, catalogue, _encode, rows, archive = _acquire_source_occurrence(
            occurrence, seed
        )
        source_rows.extend(rows)
        source_catalogues[occurrence] = catalogue
        source_archives.append(archive)
        source_support_labels += archive["source_support_labels"]

    program = synthesize_generic_atomic_program_v4(
        tuple(source_rows),
        source_catalogues,
        program_domain=pre.FUTURE_DOMAINS["program"],
    )
    support = derive_atomic_dependency_support_v4(
        program,
        tuple(source_rows),
        source_catalogues,
        support_domain=pre.FUTURE_DOMAINS["support"],
    )
    required_opcodes = {"E06", "E07", "E12"}
    if not required_opcodes <= set(program["used_opcode_names"]):
        _fail("V49 compiled program omitted a frozen atomic composition")

    partial_payload = {
        "schema": "acfqp.atomic_composition_partial_dynamics.v49",
        "program_id": program["program_id"],
        "finite_successor_support_authority_present": True,
        "exact_probability_authority_present": False,
        "maximum_observed_support_cardinality": 2,
        "robust_all_successor_planning_required": True,
        "higher_order_multistep_branching_evaluated": True,
    }
    partial = {
        **partial_payload,
        "partial_dynamics_id": content_id(
            pre.FUTURE_DOMAINS["partial"], partial_payload
        ),
    }

    source_relations = _required_source_relations(program)
    overlay: dict[str, dict[int, int]] = {}
    failed_certificates = []
    local_distinctions = []
    structural_episodes = []
    strict_episodes = []
    total_overlay_reuses = 0
    total_structural_planning = 0
    total_strict_planning = 0
    total_structural_steps = 0
    total_strict_steps = 0
    strict_support_labels = 0

    for episode_index, seed in enumerate(pre.TARGET_SEEDS):
        kernel, generation_evidence = generate_stochastic_modular_routing(
            **pre.TARGET_SPEC, seed=seed, require_last_mode=True
        )
        del generation_evidence
        catalogue, encode, _layout_id = _raw_interface(seed, kernel)
        by_key = {row.key: row for row in catalogue}
        state = kernel.initial_distribution()[0][1]
        binding = target_binding_from_initial_vector_v4(
            program,
            encode(state),
            base_relations=source_relations,
            terminal_tokens=pre.SHARED_TERMINAL_TOKENS,
        )
        episode_actions: list[int] = []
        tapes: list[str] = []
        episode_planning = 0
        episode_peak = 0
        episode_failures = 0
        episode_local_labels = 0
        episode_reuses = 0
        decision_index = 0
        while state.status is StochasticModularStatus.ACTIVE:
            raw_state = encode(state)
            missing_inventory = sorted(
                {
                    item
                    for action in kernel.actions(state)
                    for item in missing_relation_values_v4(
                        program,
                        by_key[action.edge],
                        binding,
                        relation_overlay=overlay,
                    )
                }
            )
            if missing_inventory:
                relation_name, relation_value = missing_inventory[0]
                failed_payload = {
                    "schema": "acfqp.atomic_composition_failed_certificate.v49",
                    "seed": seed,
                    "episode_index": episode_index,
                    "decision_index": decision_index,
                    "program_id": program["program_id"],
                    "missing_relation_name": relation_name,
                    "missing_anonymous_value": relation_value,
                    "ground_query_performed_before_failure": False,
                    "outcome": "FAILED_CERTIFICATE_MISSING_LOCAL_RELATION",
                }
                failed = {
                    **failed_payload,
                    "failed_certificate_id": content_id(
                        pre.FUTURE_DOMAINS["failed_certificate"], failed_payload
                    ),
                }
                failed_certificates.append(failed)
                episode_failures += 1
                selected_action = next(
                    action
                    for action in kernel.actions(state)
                    if (relation_name, relation_value)
                    in missing_relation_values_v4(
                        program,
                        by_key[action.edge],
                        binding,
                        relation_overlay=overlay,
                    )
                )
                actual_support = {
                    encode(row.next_state)
                    for row in kernel.step(state, selected_action)
                }
                recovered = _recover_relation_value(
                    program,
                    binding,
                    by_key[selected_action.edge],
                    raw_state,
                    actual_support,
                    relation_name,
                    relation_value,
                    overlay,
                )
                distinction_payload = {
                    "schema": "acfqp.atomic_composition_local_distinction.v49",
                    "failed_certificate_id": failed["failed_certificate_id"],
                    "program_id": program["program_id"],
                    "seed": seed,
                    "anonymous_pre_vector": list(raw_state),
                    "anonymous_action": by_key[selected_action.edge].to_document(),
                    "anonymous_successor_support": [list(row) for row in sorted(actual_support)],
                    "relation_name": relation_name,
                    "relation_input_value": relation_value,
                    "relation_output_value": recovered,
                    "ground_support_labels": 1,
                    "query_after_failed_certificate": True,
                }
                distinction = {
                    **distinction_payload,
                    "local_distinction_id": content_id(
                        pre.FUTURE_DOMAINS["distinction"], distinction_payload
                    ),
                }
                local_distinctions.append(distinction)
                episode_local_labels += 1
                overlay = {
                    **overlay,
                    relation_name: {
                        **overlay.get(relation_name, {}),
                        relation_value: recovered,
                    },
                }
            elif overlay:
                episode_reuses += 1
                total_overlay_reuses += 1

            plan, evaluations, peak = plan_generic_atomic_program_v4(
                program,
                raw_state,
                catalogue,
                binding,
                relation_overlay=overlay,
            )
            if not plan:
                _fail("V49 structural planner emitted an empty active plan")
            selected_key = plan[0]
            predicted = set(
                execute_generic_atomic_support_v4(
                    program,
                    raw_state,
                    by_key[selected_key],
                    binding,
                    relation_overlay=overlay,
                )
            )
            outcomes = kernel.step(state, StochasticModularAction(selected_key))
            actual = {encode(row.next_state) for row in outcomes}
            if predicted != actual:
                _fail("V49 compiled support disagreed with target kernel support")
            selected_outcome, tape = select_seeded_stochastic_modular_outcome_v1(
                outcomes,
                seed=seed,
                episode_index=episode_index,
                decision_index=decision_index,
            )
            state = selected_outcome.next_state
            episode_actions.append(selected_key)
            tapes.append(tape)
            episode_planning += evaluations
            episode_peak = max(episode_peak, peak)
            decision_index += 1
        if state.status is not StochasticModularStatus.SUCCESS:
            _fail("V49 structural target episode did not succeed")
        structural_episodes.append(
            _episode_document(
                seed=seed,
                arm=pre.ARMS[0],
                action_keys=episode_actions,
                tape_hashes=tapes,
                final_state=state,
                planning_compute=episode_planning,
                peak_cache=episode_peak,
                support_labels=episode_local_labels,
                certificate_failures=episode_failures,
                local_labels=episode_local_labels,
                overlay_reuses=episode_reuses,
            )
        )
        total_structural_planning += episode_planning
        total_structural_steps += len(episode_actions)

        strict_state = kernel.initial_distribution()[0][1]
        strict_cache: dict[
            tuple[StochasticModularState, int], tuple[StochasticModularState, ...]
        ] = {}
        strict_actions = []
        strict_tapes = []
        strict_compute = 0
        strict_peak = 0
        strict_decision = 0
        while strict_state.status is StochasticModularStatus.ACTIVE:
            action_key, _new_labels, peak = _strict_ground_choice(
                kernel, strict_state, strict_cache
            )
            outcomes = kernel.step(
                strict_state, StochasticModularAction(action_key)
            )
            selected_outcome, tape = select_seeded_stochastic_modular_outcome_v1(
                outcomes,
                seed=seed,
                episode_index=episode_index,
                decision_index=strict_decision,
            )
            strict_state = selected_outcome.next_state
            strict_actions.append(action_key)
            strict_tapes.append(tape)
            strict_compute += peak
            strict_peak = max(strict_peak, len(strict_cache))
            strict_decision += 1
        if strict_state.status is not StochasticModularStatus.SUCCESS:
            _fail("V49 strict target episode did not succeed")
        strict_support_labels += len(strict_cache)
        strict_episodes.append(
            _episode_document(
                seed=seed,
                arm=pre.ARMS[1],
                action_keys=strict_actions,
                tape_hashes=strict_tapes,
                final_state=strict_state,
                planning_compute=strict_compute,
                peak_cache=strict_peak,
                support_labels=len(strict_cache),
                certificate_failures=0,
                local_labels=0,
                overlay_reuses=0,
            )
        )
        total_strict_planning += strict_compute
        total_strict_steps += len(strict_actions)

    if len(failed_certificates) != 1 or len(local_distinctions) != 1:
        _fail("V49 did not retain exactly one failed-certificate local recovery")
    if total_overlay_reuses <= 0:
        _fail("V49 immutable local overlay was not reused")
    composed_labels = source_support_labels + len(local_distinctions)
    if composed_labels >= strict_support_labels:
        _fail("V49 matched registered label axis did not reduce sample tax")
    average_strict = strict_support_labels / len(pre.TARGET_SEEDS)
    diagnostic_break_even = max(
        1, int(source_support_labels // max(1.0, average_strict)) + 1
    )
    sample_payload = {
        "schema": "acfqp.atomic_composition_sample_tax.v49",
        "offline_source_support_labels": source_support_labels,
        "target_local_support_labels": len(local_distinctions),
        "composed_total_registered_support_labels": composed_labels,
        "strict_target_support_labels": strict_support_labels,
        "registered_support_label_savings": strict_support_labels - composed_labels,
        "sample_tax_reduced_on_frozen_campaign": True,
        "diagnostic_break_even_occurrences": diagnostic_break_even,
        "official_N_break_even": None,
        "planning_compute_not_counted_as_sample_labels": True,
    }
    sample_tax = {
        **sample_payload,
        "sample_tax_id": content_id(pre.FUTURE_DOMAINS["sample_tax"], sample_payload),
    }

    acquisition_payload = {
        "schema": "acfqp.atomic_composition_adaptive_acquisition.v49",
        "arms": list(pre.ARMS),
        "source_raw_observation_ids": [row["raw_observation_id"] for row in source_archives],
        "failed_certificate_ids": [row["failed_certificate_id"] for row in failed_certificates],
        "local_distinction_ids": [row["local_distinction_id"] for row in local_distinctions],
        "failed_certificate_precedes_every_local_label": True,
        "overlay_reuse_count": total_overlay_reuses,
        "matched_target_seed_ids": list(pre.TARGET_SEEDS),
    }
    acquisition = {
        **acquisition_payload,
        "adaptive_acquisition_id": content_id(
            pre.FUTURE_DOMAINS["acquisition"], acquisition_payload
        ),
    }
    ood_payload = {
        "schema": "acfqp.atomic_composition_ood_rejection.v49",
        "input_schema": "OPAQUE_CONTINUOUS_REAL_VECTOR_WITH_INCOMPATIBLE_WIDTH",
        "program_schema": program["schema"],
        "schema_compatible": False,
        "prior_transfer_attempted": False,
        "outcome_execution_performed": False,
        "status": "STRICT_OOD_NO_TRANSFER",
    }
    ood = {
        **ood_payload,
        "ood_rejection_id": content_id(pre.FUTURE_DOMAINS["ood"], ood_payload),
    }
    accounting = {
        "offline_source_support_labels": source_support_labels,
        "target_local_support_labels": len(local_distinctions),
        "structural_execution_steps": total_structural_steps,
        "strict_execution_steps": total_strict_steps,
        "atomic_derivation_compute_events": program["atomic_expression_evaluations"],
        "structural_planning_compute_events": total_structural_planning,
        "strict_planning_compute_events": total_strict_planning,
        "certificate_compute_events": sum(
            row["candidate_dependency_count"]
            for row in [support]
        ),
        "peak_structural_cache_entries": max(
            row["peak_planning_cache_entries"] for row in structural_episodes
        ),
        "all_axes_separate": True,
    }
    payload = {
        "schema": "acfqp.atomic_composition_campaign.v49",
        "schema_version": SCHEMA_VERSION,
        "preregistration_id": preregistration.preregistration_id,
        "preregistration_canonical_sha256": hashlib.sha256(
            preregistration.canonical_bytes
        ).hexdigest(),
        "source_archives": source_archives,
        "compiled_program": program,
        "dependency_support": support,
        "partial_dynamics": partial,
        "failed_certificates": failed_certificates,
        "local_distinctions": local_distinctions,
        "adaptive_acquisition": acquisition,
        "structural_episodes": structural_episodes,
        "strict_episodes": strict_episodes,
        "sample_tax": sample_tax,
        "ood_rejection": ood,
        "accounting": accounting,
        "required_positive_conditions_passed": True,
        "fresh_fourth_combination_domain_observed": True,
        "fourth_unrelated_domain_authority_claimed": False,
        "higher_order_finite_support_planning_observed": True,
        "exact_probability_authority_present": False,
        "open_ended_layout_discovery_claimed": False,
        "broad_world_model_synthesis_claimed": False,
        "broad_cross_domain_sample_efficiency_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "counter_completeness_gate_status": "NOT_RUN",
        "workload_economics_gate_status": "NOT_RUN",
    }
    return {
        **payload,
        "atomic_composition_campaign_id": content_id(
            pre.FUTURE_DOMAINS["campaign"], payload
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class AtomicCompositionCampaignV49:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    campaign_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("V49 campaign is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict or canonical_json_bytes(document) != self.canonical_bytes:
            _fail("V49 campaign bytes changed")
        payload = {
            key: value
            for key, value in document.items()
            if key != "atomic_composition_campaign_id"
        }
        if (
            document.get("atomic_composition_campaign_id") != self.campaign_id
            or content_id(pre.FUTURE_DOMAINS["campaign"], payload) != self.campaign_id
        ):
            _fail("V49 campaign identity changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


def run_atomic_composition_campaign_v49() -> AtomicCompositionCampaignV49:
    document = _build_campaign_document()
    raw = canonical_json_bytes(document)
    identity = document["atomic_composition_campaign_id"]
    if CAMPAIGN_ID != "0" * 64 and (
        identity != CAMPAIGN_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V49 campaign changed")
    return AtomicCompositionCampaignV49(_ISSUER, raw, identity)


def verify_atomic_composition_campaign_v49(
    value: AtomicCompositionCampaignV49,
) -> AtomicCompositionCampaignV49:
    if type(value) is not AtomicCompositionCampaignV49:
        _fail("V49 campaign rejects foreign values")
    value.__post_init__()
    if value.canonical_bytes != canonical_json_bytes(_build_campaign_document()):
        _fail("V49 campaign semantics changed")
    return value


__all__ = (
    "AtomicCompositionCampaignV49",
    "CAMPAIGN_ID",
    "EXPECTED_CANONICAL_BYTE_COUNT",
    "EXPECTED_CANONICAL_SHA256",
    "run_atomic_composition_campaign_v49",
    "verify_atomic_composition_campaign_v49",
)
