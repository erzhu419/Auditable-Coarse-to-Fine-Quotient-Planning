"""Fresh V49r1 generic-atomic campaign after the preserved V49 failure."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from functools import lru_cache
import hashlib
from typing import Any, Callable, Mapping, NoReturn

from acfqp import construction_k7_atomic_composition_preregistration_v49r1 as pre
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
    missing_relation_values_v4,
    plan_generic_atomic_program_v4,
    synthesize_generic_atomic_program_v4,
    target_binding_from_initial_vector_v4,
)
from acfqp.phase3e_ids import canonical_json_bytes, content_id, loads_canonical_json


SCHEMA_VERSION = "49.1.0"
CAMPAIGN_ID = "0" * 64
EXPECTED_CANONICAL_BYTE_COUNT = 0
EXPECTED_CANONICAL_SHA256 = "0" * 64


class ConstructionK7AtomicCompositionCampaignV49R1Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7AtomicCompositionCampaignV49R1Error(message)


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
            seed * 100 + edge.source,
            seed * 100 + edge.destination,
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
        status_name = (
            "A"
            if state.status is StochasticModularStatus.ACTIVE
            else "S"
            if state.status is StochasticModularStatus.SUCCESS
            else "F"
        )
        semantic = (
            seed * 100 + state.node,
            state.phase,
            state.resource,
            state.steps,
            pre.SHARED_TERMINAL_TOKENS[status_name],
            kernel.modulus,
            kernel.capacity,
            kernel.goal_phase,
            seed * 100 + kernel.goal_node,
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


def _source_occurrence(
    occurrence: int, seed: int
) -> tuple[
    tuple[FlatRawActionV4, ...],
    tuple[FlatRawTransitionV4, ...],
    dict[str, Any],
]:
    kernel, witness = generate_stochastic_modular_routing(**pre.SOURCE_SPEC, seed=seed)
    del witness
    catalogue, encode, layout_id = _raw_interface(seed, kernel)
    initial = kernel.initial_distribution()[0][1]
    queue = deque([initial])
    seen = {initial}
    rows = []
    labels = 0
    while queue:
        state = queue.popleft()
        legal = kernel.actions(state)
        for action in legal:
            labels += 1
            for outcome in kernel.step(state, action):
                successor = outcome.next_state
                legal_after = kernel.actions(successor)
                rows.append(
                    FlatRawTransitionV4(
                        occurrence,
                        len(rows),
                        encode(state),
                        tuple(row.edge for row in legal),
                        catalogue[action.edge],
                        encode(successor),
                        tuple(row.edge for row in legal_after),
                        None
                        if legal_after
                        else successor.status is StochasticModularStatus.SUCCESS,
                    )
                )
                if successor.status is StochasticModularStatus.ACTIVE and successor not in seen:
                    seen.add(successor)
                    queue.append(successor)
    if labels > pre.MAX_SOURCE_LABELS_PER_OCCURRENCE:
        _fail("V49r1 source acquisition exceeded its frozen cap")
    payload = {
        "schema": "acfqp.atomic_composition_raw_observation.v49r1",
        "occurrence": occurrence,
        "seed": seed,
        "opaque_layout_id": layout_id,
        "anonymous_action_catalogue": [row.to_document() for row in catalogue],
        "raw_transitions": [row.to_document() for row in rows],
        "source_support_labels": labels,
        "raw_outcome_rows": len(rows),
        "reachable_active_state_count": len(seen),
        "generation_witness_accessed": False,
        "source_policy": "WITNESS_BLIND_EXHAUSTIVE_REACHABLE_FRONTIER_ALL_LEGAL_ACTION_SUPPORTS",
    }
    return (
        catalogue,
        tuple(rows),
        {
            **payload,
            "raw_observation_id": content_id(
                pre.FUTURE_DOMAINS["observation"], payload
            ),
        },
    )


def _required_relations(program: Mapping[str, Any]) -> dict[str, list[list[int]]]:
    encoded = canonical_json_bytes(
        [row["expression"] for row in program["compiled_assignments"]]
    ).decode("utf-8")
    return {
        name: rows
        for name, rows in program["occurrence_bindings"][0]["relations"].items()
        if f'"{name}"' in encoded
    }


def _relation_modulus(
    program: Mapping[str, Any],
    relation_name: str,
    binding: Mapping[str, Any],
    raw_state: tuple[int, ...],
) -> int:
    values: set[int] = set()

    def contains(expression: Any) -> bool:
        if type(expression) is not list:
            return False
        if len(expression) >= 2 and expression[0] == "E04" and expression[1] == relation_name:
            return True
        return any(contains(item) for item in expression)

    def visit(expression: Any) -> None:
        if type(expression) is not list:
            return
        if len(expression) == 3 and expression[0] == "E06" and contains(expression[1]):
            denominator = expression[2]
            if type(denominator) is list and denominator[:1] == ["E03"]:
                values.add(binding["constants"][denominator[1]])
            elif type(denominator) is list and denominator[:1] == ["E00"]:
                values.add(raw_state[denominator[1]])
        for item in expression:
            visit(item)

    for assignment in program["compiled_assignments"]:
        visit(assignment["expression"])
    if len(values) != 1:
        _fail("V49r1 could not derive one anonymous modulus from E00/E03")
    value = next(iter(values))
    if type(value) is not int or not 3 <= value <= 256:
        _fail("V49r1 anonymous modulus escaped the frozen finite search")
    return value


def _recover_local_value(
    program: Mapping[str, Any],
    binding: Mapping[str, Any],
    raw_state: tuple[int, ...],
    action: FlatRawActionV4,
    actual_support: set[tuple[int, ...]],
    relation_name: str,
    relation_input: int,
    overlay: Mapping[str, Mapping[int, int]],
) -> int:
    matches = []
    for candidate in range(
        _relation_modulus(program, relation_name, binding, raw_state)
    ):
        trial = {name: dict(rows) for name, rows in overlay.items()}
        trial.setdefault(relation_name, {})[relation_input] = candidate
        try:
            predicted = set(
                execute_generic_atomic_support_v4(
                    program,
                    raw_state,
                    action,
                    binding,
                    relation_overlay=trial,
                )
            )
        except GenericAtomicExpressionWorldModelV4Error:
            continue
        if predicted == actual_support:
            matches.append(candidate)
    if len(matches) != 1:
        _fail("V49r1 local raw-support recovery was not unique")
    return matches[0]


def _strict_choice(
    kernel: StochasticModularKernel,
    state: StochasticModularState,
    cache: dict[tuple[StochasticModularState, int], tuple[StochasticModularState, ...]],
) -> tuple[int, int]:
    choices: dict[StochasticModularState, int] = {}

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

    if not solve(state) or state not in choices:
        _fail("V49r1 strict direct-ground planner found no robust continuation")
    return choices[state], solve.cache_info().currsize


def _episode(
    seed: int,
    arm: str,
    actions: list[int],
    tapes: list[str],
    final_state: StochasticModularState,
    planning_compute: int,
    peak_cache: int,
    labels: int,
    failures: int,
    local_labels: int,
    overlay_reuses: int,
) -> dict[str, Any]:
    payload = {
        "schema": "acfqp.atomic_composition_receding_episode.v49r1",
        "seed": seed,
        "arm": arm,
        "action_keys": actions,
        "outcome_tape_sha256": tapes,
        "execution_steps": len(actions),
        "planning_compute_events": planning_compute,
        "peak_planning_cache_entries": peak_cache,
        "ground_support_labels": labels,
        "failed_certificate_count": failures,
        "local_ground_support_labels": local_labels,
        "immutable_overlay_reuse_count": overlay_reuses,
        "final_status": final_state.status.value,
        "success": final_state.status is StochasticModularStatus.SUCCESS,
    }
    return {
        **payload,
        "episode_id": content_id(pre.FUTURE_DOMAINS["episode"], payload),
    }


def _build_campaign_document() -> dict[str, Any]:
    prereg = pre.verify_atomic_composition_preregistration_v49r1(
        pre.freeze_atomic_composition_preregistration_v49r1()
    )
    all_rows = []
    catalogues = {}
    archives = []
    source_labels = 0
    for occurrence, seed in enumerate(pre.SOURCE_SEEDS):
        catalogue, rows, archive = _source_occurrence(occurrence, seed)
        catalogues[occurrence] = catalogue
        all_rows.extend(rows)
        archives.append(archive)
        source_labels += archive["source_support_labels"]
    program = synthesize_generic_atomic_program_v4(
        tuple(all_rows),
        catalogues,
        program_domain=pre.FUTURE_DOMAINS["program"],
    )
    support = derive_atomic_dependency_support_v4(
        program,
        tuple(all_rows),
        catalogues,
        support_domain=pre.FUTURE_DOMAINS["support"],
    )
    if {"E06", "E07", "E12"} - set(program["used_opcode_names"]):
        _fail("V49r1 program omitted a registered atomic composition")
    source_relations = _required_relations(program)

    partial_payload = {
        "schema": "acfqp.atomic_composition_partial_dynamics.v49r1",
        "program_id": program["program_id"],
        "finite_successor_support_authority_present": True,
        "exact_probability_authority_present": False,
        "maximum_observed_support_cardinality": 2,
        "robust_all_successor_planning_required": True,
        "higher_order_multistep_branching_evaluated": True,
    }
    partial = {
        **partial_payload,
        "partial_dynamics_id": content_id(pre.FUTURE_DOMAINS["partial"], partial_payload),
    }

    overlay: dict[str, dict[int, int]] = {}
    failures = []
    distinctions = []
    structural_episodes = []
    strict_episodes = []
    overlay_reuses = 0
    structural_planning = 0
    strict_planning = 0
    structural_steps = 0
    strict_steps = 0
    strict_labels = 0

    for episode_index, seed in enumerate(pre.TARGET_SEEDS):
        kernel, witness = generate_stochastic_modular_routing(
            **pre.TARGET_SPEC, seed=seed, require_last_mode=True
        )
        del witness
        catalogue, encode, _layout = _raw_interface(seed, kernel)
        by_key = {row.key: row for row in catalogue}
        state = kernel.initial_distribution()[0][1]
        binding = target_binding_from_initial_vector_v4(
            program,
            encode(state),
            base_relations=source_relations,
            terminal_tokens=pre.SHARED_TERMINAL_TOKENS,
        )
        actions: list[int] = []
        tapes: list[str] = []
        planning = 0
        peak = 0
        episode_failures = 0
        episode_local = 0
        episode_reuses = 0
        decision = 0
        while state.status is StochasticModularStatus.ACTIVE:
            raw_state = encode(state)
            missing = sorted(
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
            if missing:
                relation_name, relation_input = missing[0]
                failure_payload = {
                    "schema": "acfqp.atomic_composition_failed_certificate.v49r1",
                    "seed": seed,
                    "episode_index": episode_index,
                    "decision_index": decision,
                    "program_id": program["program_id"],
                    "missing_relation_name": relation_name,
                    "missing_anonymous_value": relation_input,
                    "ground_query_performed_before_failure": False,
                    "outcome": "FAILED_CERTIFICATE_MISSING_LOCAL_RELATION",
                }
                failure = {
                    **failure_payload,
                    "failed_certificate_id": content_id(
                        pre.FUTURE_DOMAINS["failed_certificate"], failure_payload
                    ),
                }
                failures.append(failure)
                episode_failures += 1
                query_action = next(
                    action
                    for action in kernel.actions(state)
                    if (relation_name, relation_input)
                    in missing_relation_values_v4(
                        program,
                        by_key[action.edge],
                        binding,
                        relation_overlay=overlay,
                    )
                )
                actual_support = {
                    encode(row.next_state) for row in kernel.step(state, query_action)
                }
                output = _recover_local_value(
                    program,
                    binding,
                    raw_state,
                    by_key[query_action.edge],
                    actual_support,
                    relation_name,
                    relation_input,
                    overlay,
                )
                distinction_payload = {
                    "schema": "acfqp.atomic_composition_local_distinction.v49r1",
                    "failed_certificate_id": failure["failed_certificate_id"],
                    "program_id": program["program_id"],
                    "seed": seed,
                    "anonymous_pre_vector": list(raw_state),
                    "anonymous_action": by_key[query_action.edge].to_document(),
                    "anonymous_successor_support": [list(row) for row in sorted(actual_support)],
                    "relation_name": relation_name,
                    "relation_input_value": relation_input,
                    "relation_output_value": output,
                    "ground_support_labels": 1,
                    "query_after_failed_certificate": True,
                }
                distinction = {
                    **distinction_payload,
                    "local_distinction_id": content_id(
                        pre.FUTURE_DOMAINS["distinction"], distinction_payload
                    ),
                }
                distinctions.append(distinction)
                episode_local += 1
                overlay = {
                    **overlay,
                    relation_name: {
                        **overlay.get(relation_name, {}),
                        relation_input: output,
                    },
                }
            elif overlay:
                overlay_reuses += 1
                episode_reuses += 1

            plan, evaluations, cache_size = plan_generic_atomic_program_v4(
                program,
                raw_state,
                catalogue,
                binding,
                relation_overlay=overlay,
            )
            if not plan:
                _fail("V49r1 structural planner returned an empty active plan")
            action_key = plan[0]
            outcomes = kernel.step(state, StochasticModularAction(action_key))
            predicted = set(
                execute_generic_atomic_support_v4(
                    program,
                    raw_state,
                    by_key[action_key],
                    binding,
                    relation_overlay=overlay,
                )
            )
            if predicted != {encode(row.next_state) for row in outcomes}:
                _fail("V49r1 compiled support disagreed with target kernel")
            selected, tape = select_seeded_stochastic_modular_outcome_v1(
                outcomes,
                seed=seed,
                episode_index=episode_index,
                decision_index=decision,
            )
            state = selected.next_state
            actions.append(action_key)
            tapes.append(tape)
            planning += evaluations
            peak = max(peak, cache_size)
            decision += 1
        if state.status is not StochasticModularStatus.SUCCESS:
            _fail("V49r1 structural episode failed")
        structural_episodes.append(
            _episode(
                seed,
                pre.ARMS[0],
                actions,
                tapes,
                state,
                planning,
                peak,
                episode_local,
                episode_failures,
                episode_local,
                episode_reuses,
            )
        )
        structural_planning += planning
        structural_steps += len(actions)

        direct_state = kernel.initial_distribution()[0][1]
        direct_cache: dict[
            tuple[StochasticModularState, int], tuple[StochasticModularState, ...]
        ] = {}
        direct_actions: list[int] = []
        direct_tapes: list[str] = []
        direct_compute = 0
        direct_peak = 0
        direct_decision = 0
        while direct_state.status is StochasticModularStatus.ACTIVE:
            action_key, cache_size = _strict_choice(kernel, direct_state, direct_cache)
            outcomes = kernel.step(direct_state, StochasticModularAction(action_key))
            selected, tape = select_seeded_stochastic_modular_outcome_v1(
                outcomes,
                seed=seed,
                episode_index=episode_index,
                decision_index=direct_decision,
            )
            direct_state = selected.next_state
            direct_actions.append(action_key)
            direct_tapes.append(tape)
            direct_compute += cache_size
            direct_peak = max(direct_peak, len(direct_cache))
            direct_decision += 1
        if direct_state.status is not StochasticModularStatus.SUCCESS:
            _fail("V49r1 strict episode failed")
        strict_labels += len(direct_cache)
        strict_episodes.append(
            _episode(
                seed,
                pre.ARMS[1],
                direct_actions,
                direct_tapes,
                direct_state,
                direct_compute,
                direct_peak,
                len(direct_cache),
                0,
                0,
                0,
            )
        )
        strict_planning += direct_compute
        strict_steps += len(direct_actions)

    if len(failures) != 1 or len(distinctions) != 1 or overlay_reuses <= 0:
        _fail("V49r1 certificate-local-recovery closure changed")
    composed_labels = source_labels + len(distinctions)
    if composed_labels >= strict_labels:
        _fail("V49r1 did not reduce the matched registered support-label tax")
    average_strict = strict_labels / len(pre.TARGET_SEEDS)
    break_even = max(1, int(source_labels // max(1.0, average_strict)) + 1)
    sample_payload = {
        "schema": "acfqp.atomic_composition_sample_tax.v49r1",
        "offline_source_support_labels": source_labels,
        "target_local_support_labels": len(distinctions),
        "composed_total_registered_support_labels": composed_labels,
        "strict_target_support_labels": strict_labels,
        "registered_support_label_savings": strict_labels - composed_labels,
        "sample_tax_reduced_on_frozen_campaign": True,
        "diagnostic_break_even_occurrences": break_even,
        "official_N_break_even": None,
        "planning_compute_not_counted_as_sample_labels": True,
    }
    sample_tax = {
        **sample_payload,
        "sample_tax_id": content_id(pre.FUTURE_DOMAINS["sample_tax"], sample_payload),
    }
    acquisition_payload = {
        "schema": "acfqp.atomic_composition_adaptive_acquisition.v49r1",
        "arms": list(pre.ARMS),
        "source_raw_observation_ids": [row["raw_observation_id"] for row in archives],
        "failed_certificate_ids": [row["failed_certificate_id"] for row in failures],
        "local_distinction_ids": [row["local_distinction_id"] for row in distinctions],
        "failed_certificate_precedes_every_local_label": True,
        "overlay_reuse_count": overlay_reuses,
        "matched_target_seed_ids": list(pre.TARGET_SEEDS),
    }
    acquisition = {
        **acquisition_payload,
        "adaptive_acquisition_id": content_id(
            pre.FUTURE_DOMAINS["acquisition"], acquisition_payload
        ),
    }
    ood_payload = {
        "schema": "acfqp.atomic_composition_ood_rejection.v49r1",
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
        "offline_source_support_labels": source_labels,
        "target_local_support_labels": len(distinctions),
        "structural_execution_steps": structural_steps,
        "strict_execution_steps": strict_steps,
        "atomic_derivation_compute_events": program["atomic_expression_evaluations"],
        "structural_planning_compute_events": structural_planning,
        "strict_planning_compute_events": strict_planning,
        "certificate_compute_events": support["candidate_dependency_count"],
        "peak_structural_cache_entries": max(
            row["peak_planning_cache_entries"] for row in structural_episodes
        ),
        "all_axes_separate": True,
    }
    payload = {
        "schema": "acfqp.atomic_composition_campaign.v49r1",
        "schema_version": SCHEMA_VERSION,
        "preregistration_id": prereg.preregistration_id,
        "preregistration_canonical_sha256": hashlib.sha256(prereg.canonical_bytes).hexdigest(),
        "preserved_v49_failure_id": pre.V49_FAILURE_ID,
        "source_archives": archives,
        "compiled_program": program,
        "dependency_support": support,
        "partial_dynamics": partial,
        "failed_certificates": failures,
        "local_distinctions": distinctions,
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
class AtomicCompositionCampaignV49R1:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    campaign_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("V49r1 campaign is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict or canonical_json_bytes(document) != self.canonical_bytes:
            _fail("V49r1 campaign bytes changed")
        payload = {
            key: value
            for key, value in document.items()
            if key != "atomic_composition_campaign_id"
        }
        if (
            document.get("atomic_composition_campaign_id") != self.campaign_id
            or content_id(pre.FUTURE_DOMAINS["campaign"], payload) != self.campaign_id
        ):
            _fail("V49r1 campaign identity changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


def run_atomic_composition_campaign_v49r1() -> AtomicCompositionCampaignV49R1:
    document = _build_campaign_document()
    raw = canonical_json_bytes(document)
    identity = document["atomic_composition_campaign_id"]
    if CAMPAIGN_ID != "0" * 64 and (
        identity != CAMPAIGN_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V49r1 campaign changed")
    return AtomicCompositionCampaignV49R1(_ISSUER, raw, identity)


def verify_atomic_composition_campaign_v49r1(
    value: AtomicCompositionCampaignV49R1,
) -> AtomicCompositionCampaignV49R1:
    if type(value) is not AtomicCompositionCampaignV49R1:
        _fail("V49r1 campaign rejects foreign values")
    value.__post_init__()
    if (
        value.campaign_id != CAMPAIGN_ID
        or len(value.canonical_bytes) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(value.canonical_bytes).hexdigest()
        != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V49r1 campaign identity changed")
    return value


__all__ = (
    "AtomicCompositionCampaignV49R1",
    "CAMPAIGN_ID",
    "EXPECTED_CANONICAL_BYTE_COUNT",
    "EXPECTED_CANONICAL_SHA256",
    "run_atomic_composition_campaign_v49r1",
    "verify_atomic_composition_campaign_v49r1",
)
