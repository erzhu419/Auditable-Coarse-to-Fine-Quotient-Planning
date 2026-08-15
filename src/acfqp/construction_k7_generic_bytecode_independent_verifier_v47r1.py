"""Producer-free reconstruction of the V47r1 generic-bytecode campaign."""

from __future__ import annotations

from collections import Counter
from functools import lru_cache
from fractions import Fraction
import hashlib
import random
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_generic_bytecode_successor_preregistration_v47r1 as pre
from acfqp.domains.matching_buffer import (
    LMBAction,
    LMBKernel,
    LMBState,
    LMBStatus,
    generate_solvable_lmb,
)
from acfqp.domains.stochastic_routing import (
    StochasticRoutingAction,
    StochasticRoutingKernel,
    StochasticRoutingState,
    StochasticRoutingStatus,
    generate_stochastic_routing,
    select_seeded_routing_outcome_v1,
)
from acfqp.generic_bytecode_world_model_v2 import (
    RawActionV1,
    RawTransitionV1,
    bind_scalar_categorical_target_v2,
    bind_vector_set_target_v1,
    derive_compiled_dependency_support_v2,
    execute_scalar_categorical_bytecode_v2,
    execute_vector_set_bytecode_v2,
    plan_scalar_categorical_v1,
    plan_vector_set_v1,
    synthesize_generic_program_v1,
)
from acfqp.phase3e_ids import canonical_json_bytes, content_id, loads_canonical_json


SCHEMA_VERSION = "47.1.0"
VERIFICATION_ID = "57027df9ed5cbb02d044b3a38d8c4f53ecb38f00fdb26c15bc9c8cbbe5cab0b1"
EXPECTED_CANONICAL_BYTE_COUNT = 2112
EXPECTED_CANONICAL_SHA256 = "f381bbefd0eb335517943eb1f2dd3e80b016c6939cd8ee0db794449cd746312c"


class ConstructionK7GenericBytecodeIndependentVerifierV47R1Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7GenericBytecodeIndependentVerifierV47R1Error(message)


def _token(seed: int, namespace: int, value: int) -> int:
    return seed * 10_000_000 + namespace * 10_000 + value


def _permutation(width: int, seed: int, salt: int) -> tuple[int, ...]:
    values = list(range(width))
    random.Random(seed ^ salt).shuffle(values)
    return tuple(values)


def _lmb_raw(
    seed: int, kernel: LMBKernel
) -> tuple[tuple[RawActionV1, ...], Any, str]:
    field_order = _permutation(4, seed, pre.ACTION_FIELD_SALT)
    state_order = _permutation(kernel.type_count + 3, seed, pre.FLAT_LAYOUT_SALT)
    type_tokens = tuple(_token(seed, 11, index) for index in range(kernel.type_count))
    status_tokens = {
        LMBStatus.ACTIVE: _token(seed, 12, 1),
        LMBStatus.FAILURE: _token(seed, 12, 101),
        LMBStatus.SUCCESS: _token(seed, 12, 201),
    }
    catalogue = []
    for tile in range(kernel.tile_count):
        semantic = (
            1 << tile,
            sum(1 << blocker for blocker in kernel.blockers[tile]),
            type_tokens[kernel.tile_types[tile]],
            _token(seed, 13, tile),
        )
        catalogue.append(RawActionV1(tile, tuple(semantic[index] for index in field_order)))

    def encode(state: LMBState) -> tuple[int, ...]:
        semantic = (state.removed_mask, *state.buffer, kernel.capacity, status_tokens[state.status])
        return tuple(semantic[index] for index in state_order)

    layout = {
        "state_width": kernel.type_count + 3,
        "action_field_width": 4,
        "state_permutation_sha256": hashlib.sha256(bytes(state_order)).hexdigest(),
        "action_permutation_sha256": hashlib.sha256(bytes(field_order)).hexdigest(),
        "semantic_role_names_serialized": False,
    }
    return tuple(catalogue), encode, content_id(pre.FUTURE_DOMAINS["observation"], layout)


def _routing_raw(
    seed: int, kernel: StochasticRoutingKernel
) -> tuple[tuple[RawActionV1, ...], Any, str]:
    field_order = _permutation(5, seed, pre.ACTION_FIELD_SALT)
    state_order = _permutation(4, seed, pre.FLAT_LAYOUT_SALT)
    node_tokens = tuple(_token(seed, 21, index) for index in range(kernel.node_count))
    class_tokens = tuple(_token(seed, 22, index) for index in range(3))
    status_tokens = {
        StochasticRoutingStatus.ACTIVE: _token(seed, 23, 1),
        StochasticRoutingStatus.FAILURE: _token(seed, 23, 101),
        StochasticRoutingStatus.SUCCESS: _token(seed, 23, 201),
    }
    catalogue = []
    for edge_index, edge in enumerate(kernel.edges):
        semantic = (
            node_tokens[edge.source],
            node_tokens[edge.destination],
            edge.magnitude,
            class_tokens[edge.cost_class],
            _token(seed, 24, edge_index),
        )
        catalogue.append(RawActionV1(edge_index, tuple(semantic[index] for index in field_order)))

    def encode(state: StochasticRoutingState) -> tuple[int, ...]:
        semantic = (node_tokens[state.node], state.resource, status_tokens[state.status], kernel.capacity)
        return tuple(semantic[index] for index in state_order)

    layout = {
        "state_width": 4,
        "action_field_width": 5,
        "state_permutation_sha256": hashlib.sha256(bytes(state_order)).hexdigest(),
        "action_permutation_sha256": hashlib.sha256(bytes(field_order)).hexdigest(),
        "semantic_role_names_serialized": False,
    }
    return tuple(catalogue), encode, content_id(pre.FUTURE_DOMAINS["observation"], layout)


def _action(document: Mapping[str, Any]) -> RawActionV1:
    if set(document) != {"action_key", "anonymous_fields"}:
        _fail("raw action schema changed")
    return RawActionV1(document["action_key"], tuple(document["anonymous_fields"]))


def _transition(document: Mapping[str, Any]) -> RawTransitionV1:
    expected = {
        "occurrence",
        "transition_index",
        "pre_vector",
        "legal_action_keys_before",
        "selected_action",
        "post_vector",
        "legal_action_keys_after",
        "outcome_tape_sha256",
    }
    if set(document) != expected:
        _fail("raw transition schema changed")
    return RawTransitionV1(
        document["occurrence"],
        document["transition_index"],
        tuple(document["pre_vector"]),
        tuple(document["legal_action_keys_before"]),
        _action(document["selected_action"]),
        tuple(document["post_vector"]),
        tuple(document["legal_action_keys_after"]),
        document["outcome_tape_sha256"],
    )


def _verify_source_archives(
    archives: list[dict[str, Any]],
) -> tuple[
    dict[str, dict[int, tuple[RawActionV1, ...]]],
    dict[str, tuple[RawTransitionV1, ...]],
]:
    catalogues: dict[str, dict[int, tuple[RawActionV1, ...]]] = {"D00": {}, "D01": {}}
    rows: dict[str, list[RawTransitionV1]] = {"D00": [], "D01": []}
    expected_seeds = {"D00": set(pre.LMB_SOURCE_SEEDS), "D01": set(pre.ROUTING_SOURCE_SEEDS)}
    seen_seeds = {"D00": set(), "D01": set()}
    for archive in archives:
        if set(archive) != {
            "schema",
            "anonymous_family",
            "seed",
            "opaque_layout_id",
            "anonymous_action_catalogue",
            "raw_transitions",
            "source_transition_labels",
            "source_environment_steps",
            "synthesis_probe_count",
            "generation_witness_accessed",
            "semantic_role_names_available_to_synthesizer",
            "raw_observation_id",
        }:
            _fail("raw observation top-level schema changed")
        payload = {key: value for key, value in archive.items() if key != "raw_observation_id"}
        if content_id(pre.FUTURE_DOMAINS["observation"], payload) != archive.get("raw_observation_id"):
            _fail("raw observation identity changed")
        family = archive.get("anonymous_family")
        if family not in catalogues:
            _fail("raw observation family changed")
        seed = archive.get("seed")
        seen_seeds[family].add(seed)
        parsed = tuple(_transition(row) for row in archive["raw_transitions"])
        if not parsed:
            _fail("raw observation archive is empty")
        occurrence = parsed[0].occurrence
        if any(row.occurrence != occurrence for row in parsed):
            _fail("raw archive crossed occurrence identities")
        catalogue = tuple(_action(row) for row in archive["anonymous_action_catalogue"])
        if archive["source_transition_labels"] != len(parsed) or archive["source_environment_steps"] != len(parsed):
            _fail("source label/step accounting changed")
        if archive["generation_witness_accessed"] is not False or archive["semantic_role_names_available_to_synthesizer"] is not False:
            _fail("source raw interface leaked forbidden evidence")
        catalogues[family][occurrence] = catalogue
        rows[family].extend(parsed)
    if seen_seeds != expected_seeds:
        _fail("fresh source seed inventory changed")
    return catalogues, {key: tuple(value) for key, value in rows.items()}


def _direct_lmb(
    kernel: LMBKernel,
    initial: LMBState,
    cache: dict[tuple[LMBState, int], LMBState],
) -> tuple[tuple[int, ...], int, int, int]:
    before = len(cache)
    compute = 0
    peak = 0

    @lru_cache(maxsize=None)
    def solve(state: LMBState) -> tuple[int, ...] | None:
        nonlocal compute, peak
        if state.status is LMBStatus.SUCCESS:
            return ()
        if state.status is LMBStatus.FAILURE:
            return None
        ranked = []
        for action in kernel.actions(state):
            key = (state, action.tile)
            if key not in cache:
                cache[key] = kernel.step(state, action)[0].next_state
            successor = cache[key]
            compute += 1
            ranked.append(((-int(sum(successor.buffer) < sum(state.buffer)), sum(successor.buffer), action.tile), action.tile, successor))
        for _score, key, successor in sorted(ranked):
            suffix = solve(successor)
            if suffix is not None:
                peak = max(peak, solve.cache_info().currsize)
                return (key, *suffix)
        peak = max(peak, solve.cache_info().currsize)
        return None

    result = solve(initial)
    if result is None:
        _fail("producer-free direct D00 planner failed")
    return result, len(cache) - before, compute, peak


def _direct_routing(
    kernel: StochasticRoutingKernel,
    initial: StochasticRoutingState,
    cache: dict[tuple[StochasticRoutingState, int], tuple[Any, ...]],
) -> tuple[tuple[int, ...], int, int, int]:
    before = len(cache)
    compute = 0

    @lru_cache(maxsize=None)
    def solve(state: StochasticRoutingState) -> tuple[int, ...] | None:
        nonlocal compute
        if state.status is StochasticRoutingStatus.SUCCESS:
            return ()
        if state.status is StochasticRoutingStatus.FAILURE:
            return None
        ranked = []
        for action in kernel.actions(state):
            key = (state, action.edge)
            if key not in cache:
                cache[key] = kernel.step(state, action)
            worst = max(cache[key], key=lambda row: row.next_state.resource).next_state
            compute += 1
            ranked.append(((worst.status is StochasticRoutingStatus.FAILURE, worst.resource, action.edge), action.edge, worst))
        for _score, key, successor in sorted(ranked):
            suffix = solve(successor)
            if suffix is not None:
                return (key, *suffix)
        return None

    result = solve(initial)
    if result is None:
        _fail("producer-free direct D01 planner failed")
    return result, len(cache) - before, compute, solve.cache_info().currsize


def _verify_lmb_episode(episode: Mapping[str, Any], program: Mapping[str, Any]) -> dict[str, int]:
    seed = episode["seed"]
    kernel, witness = generate_solvable_lmb(seed=seed, **pre.LMB_TARGET_SPEC)
    del witness
    catalogue, encode, layout = _lmb_raw(seed, kernel)
    state = kernel.initial_distribution()[0][1]
    if episode["opaque_layout_id"] != layout or episode["initial_vector"] != list(encode(state)):
        _fail("D00 target raw layout changed")
    if episode["anonymous_action_catalogue"] != [row.to_document() for row in catalogue]:
        _fail("D00 target catalogue changed")
    binding = bind_vector_set_target_v1(encode(state), tuple(action.tile for action in kernel.actions(state)), catalogue)
    if episode["target_binding"] != binding:
        _fail("D00 target binding changed")
    vm = (binding["initial_vm_state"]["q0"], tuple(binding["initial_vm_state"]["q1"]), 0)
    cache: dict[tuple[LMBState, int], LMBState] = {}
    totals = {"meta": 0, "strict": 0, "labels": 0, "certificate": 0, "meta_peak": 0, "strict_peak": 0}
    for index, recorded in enumerate(episode["decisions"]):
        if set(recorded) != {
            "decision_index",
            "pre_vector",
            "meta_receding_plan",
            "strict_receding_plan",
            "selected_action",
            "post_vector",
            "certificate_status",
            "meta_local_ground_labels",
            "strict_new_exact_context_labels",
        }:
            _fail("D00 decision schema changed")
        meta_plan, meta_compute, meta_peak = plan_vector_set_v1(vm, catalogue, binding)
        direct_plan, labels, strict_compute, strict_peak = _direct_lmb(kernel, state, cache)
        if recorded["decision_index"] != index or recorded["pre_vector"] != list(encode(state)):
            _fail("D00 decision predecessor changed")
        if recorded["meta_receding_plan"] != list(meta_plan[: pre.RECEDING_HORIZON]) or recorded["strict_receding_plan"] != list(direct_plan[: pre.RECEDING_HORIZON]):
            _fail("D00 receding plan changed")
        selected = meta_plan[0]
        if recorded["selected_action"] != catalogue[selected].to_document() or selected != direct_plan[0]:
            _fail("D00 selected action changed")
        simulated = vm
        for key in meta_plan:
            simulated = execute_vector_set_bytecode_v2(simulated, catalogue[key], binding)
            totals["certificate"] += 1
        if simulated[2] != 2 or recorded["certificate_status"] != "PASSED_NO_GROUND_LABEL":
            _fail("D00 certificate changed")
        state = kernel.step(state, LMBAction(selected))[0].next_state
        vm = execute_vector_set_bytecode_v2(vm, catalogue[selected], binding)
        if recorded["post_vector"] != list(encode(state)) or recorded["strict_new_exact_context_labels"] != labels or recorded["meta_local_ground_labels"] != 0:
            _fail("D00 successor or local accounting changed")
        totals["meta"] += meta_compute
        totals["strict"] += strict_compute
        totals["labels"] += labels
        totals["meta_peak"] = max(totals["meta_peak"], meta_peak)
        totals["strict_peak"] = max(totals["strict_peak"], strict_peak)
    if state.status is not LMBStatus.SUCCESS:
        _fail("D00 replay did not terminate successfully")
    return totals


def _verify_routing_episode(episode: Mapping[str, Any], program: Mapping[str, Any]) -> dict[str, int]:
    seed = episode["seed"]
    kernel, witness = generate_stochastic_routing(seed=seed, **pre.ROUTING_TARGET_SPEC)
    del witness
    catalogue, encode, layout = _routing_raw(seed, kernel)
    state = kernel.initial_distribution()[0][1]
    if episode["opaque_layout_id"] != layout or episode["initial_vector"] != list(encode(state)):
        _fail("D01 target raw layout changed")
    if episode["anonymous_action_catalogue"] != [row.to_document() for row in catalogue]:
        _fail("D01 target catalogue changed")
    binding = bind_scalar_categorical_target_v2(encode(state), tuple(action.edge for action in kernel.actions(state)), catalogue)
    if episode["target_binding"] != binding:
        _fail("D01 target binding changed")
    vm = (binding["initial_vm_state"]["q0"], binding["initial_vm_state"]["q1"], 0)
    cache: dict[tuple[StochasticRoutingState, int], tuple[Any, ...]] = {}
    totals = {"meta": 0, "strict": 0, "labels": 0, "certificate": 0, "meta_peak": 0, "strict_peak": 0}
    for index, recorded in enumerate(episode["decisions"]):
        if set(recorded) != {
            "decision_index",
            "pre_vector",
            "meta_receding_plan",
            "strict_receding_plan",
            "selected_action",
            "post_vector",
            "outcome_tape_sha256",
            "certificate_status",
            "meta_local_ground_labels",
            "strict_new_exact_context_labels",
        }:
            _fail("D01 decision schema changed")
        meta_plan, meta_compute, meta_peak = plan_scalar_categorical_v1(vm, catalogue, binding)
        direct_plan, labels, strict_compute, strict_peak = _direct_routing(kernel, state, cache)
        if recorded["decision_index"] != index or recorded["pre_vector"] != list(encode(state)):
            _fail("D01 decision predecessor changed")
        if recorded["meta_receding_plan"] != list(meta_plan[: pre.RECEDING_HORIZON]) or recorded["strict_receding_plan"] != list(direct_plan[: pre.RECEDING_HORIZON]):
            _fail("D01 receding plan changed")
        selected = meta_plan[0]
        if selected != direct_plan[0] or recorded["selected_action"] != catalogue[selected].to_document():
            _fail("D01 selected action changed")
        before_vector = encode(state)
        outcome, tape = select_seeded_routing_outcome_v1(kernel.step(state, StochasticRoutingAction(selected)), seed=seed, episode_index=0, decision_index=index)
        state = outcome.next_state
        post_vector = encode(state)
        vm = execute_scalar_categorical_bytecode_v2(vm, catalogue[selected], binding, pre_vector=before_vector, post_vector=post_vector)
        if recorded["post_vector"] != list(post_vector) or recorded["outcome_tape_sha256"] != tape or recorded["strict_new_exact_context_labels"] != labels or recorded["meta_local_ground_labels"] != 0:
            _fail("D01 residual or local accounting changed")
        if recorded["certificate_status"] != "PASSED_ROBUST_SUPPORT_NO_GROUND_LABEL":
            _fail("D01 certificate changed")
        totals["meta"] += meta_compute
        totals["strict"] += strict_compute
        totals["labels"] += labels
        totals["certificate"] += len(meta_plan)
        totals["meta_peak"] = max(totals["meta_peak"], meta_peak)
        totals["strict_peak"] = max(totals["strict_peak"], strict_peak)
    if state.status is not StochasticRoutingStatus.SUCCESS:
        _fail("D01 replay did not terminate successfully")
    return totals


def _expected_partial(program: Mapping[str, Any], rows: tuple[RawTransitionV1, ...]) -> dict[str, Any]:
    bindings = {row["occurrence"]: row for row in program["occurrence_bindings"]}
    counts: dict[int, Counter[int]] = {}
    occurrences: dict[int, set[int]] = {}
    for row in rows:
        binding = bindings[row.occurrence]
        state_roles = binding["state_roles"]
        action_roles = binding["action_roles"]
        magnitude = row.action.fields[action_roles["A2"]]
        delta = row.post[state_roles["R1"]] - row.pre[state_roles["R1"]]
        counts.setdefault(magnitude, Counter())[delta] += 1
        occurrences.setdefault(magnitude, set()).add(row.occurrence)
    support = []
    for magnitude, observed in sorted(counts.items()):
        total = sum(observed.values())
        support.append({
            "anonymous_magnitude": magnitude,
            "source_occurrence_count": len(occurrences[magnitude]),
            "observed_support": sorted(observed),
            "empirical_rational": [
                {"delta": delta, "empirical_probability": Fraction(count, total)}
                for delta, count in sorted(observed.items())
            ],
            "conservative_probability_interval": [0, 1],
        })
    payload = {
        "schema": "acfqp.generic_stochastic_partial.v47r1",
        "program_id": program["program_id"],
        "support_rows": support,
        "exact_probability_authority": False,
        "support_complete_on_registered_source": all(len(row["observed_support"]) == 2 for row in support),
        "planner_probability_input": "NONE_ROBUST_WORST_SUPPORT",
    }
    return {**payload, "partial_model_id": content_id(pre.FUTURE_DOMAINS["stochastic"], payload)}


def verify_generic_bytecode_campaign_bytes_v47r1(campaign_bytes: bytes) -> dict[str, Any]:
    if type(campaign_bytes) is not bytes:
        _fail("campaign verifier requires exact bytes")
    document = loads_canonical_json(campaign_bytes)
    if type(document) is not dict or canonical_json_bytes(document) != campaign_bytes:
        _fail("campaign bytes are noncanonical")
    payload = {key: value for key, value in document.items() if key != "generic_cross_domain_campaign_id"}
    campaign_id = document.get("generic_cross_domain_campaign_id")
    if content_id(pre.FUTURE_DOMAINS["campaign"], payload) != campaign_id:
        _fail("campaign content identity changed")
    if set(document) != {
        "schema",
        "schema_version",
        "preregistration_id",
        "failed_v47_identity_preserved",
        "source_archives",
        "programs",
        "dependency_support_signatures",
        "stochastic_partial_model",
        "episodes",
        "sample_tax",
        "strict_ood_control",
        "accounting_axes",
        "one_generic_synthesizer_two_programs",
        "compiled_template_opcodes",
        "lmb_named_primitive_in_compiled_bytecode",
        "typed_adapter_abstract_state_consumed_by_planner",
        "all_local_ground_labels_follow_failed_certificates",
        "successful_certificate_local_ground_label_count",
        "exact_stochastic_probability_authority",
        "producer_free_verification_status",
        "broad_world_model_synthesis_claimed",
        "official_execution_allowed",
        "official_scalar_cost",
        "official_N_break_even",
        "counter_completeness_gate_status",
        "workload_economics_gate_status",
        "generic_cross_domain_campaign_id",
    }:
        _fail("campaign top-level schema changed")
    if (
        document.get("schema") != "acfqp.generic_cross_domain_campaign.v47r1"
        or document.get("schema_version") != SCHEMA_VERSION
        or document.get("failed_v47_identity_preserved") is not True
        or document.get("one_generic_synthesizer_two_programs") is not True
        or document.get("compiled_template_opcodes") != ["T00", "T01"]
        or document.get("lmb_named_primitive_in_compiled_bytecode") is not False
        or document.get("typed_adapter_abstract_state_consumed_by_planner") is not False
        or document.get("all_local_ground_labels_follow_failed_certificates") is not True
        or document.get("successful_certificate_local_ground_label_count") != 0
        or document.get("exact_stochastic_probability_authority") is not False
        or document.get("producer_free_verification_status") != "NOT_RUN"
        or document.get("broad_world_model_synthesis_claimed") is not False
    ):
        _fail("campaign scientific claim locks changed")
    prereg = pre.freeze_generic_bytecode_successor_preregistration_v47r1()
    if document.get("preregistration_id") != prereg.preregistration_id:
        _fail("campaign preregistration identity changed")

    catalogues, source_rows = _verify_source_archives(document["source_archives"])
    expected_programs = [
        synthesize_generic_program_v1(source_rows["D00"], catalogues["D00"], program_domain=pre.FUTURE_DOMAINS["program"]),
        synthesize_generic_program_v1(source_rows["D01"], catalogues["D01"], program_domain=pre.FUTURE_DOMAINS["program"]),
    ]
    if document["programs"] != expected_programs:
        _fail("producer-free synthesized programs changed")
    expected_support = [
        derive_compiled_dependency_support_v2(program, support_domain=pre.FUTURE_DOMAINS["distinction"])
        for program in expected_programs
    ]
    if document["dependency_support_signatures"] != expected_support:
        _fail("compiled dependency support changed")
    expected_partial = _expected_partial(expected_programs[1], source_rows["D01"])
    if document["stochastic_partial_model"] != expected_partial:
        _fail("partial dynamics reconstruction changed")

    episodes = document["episodes"]
    expected_episode_inventory = [("D00", seed) for seed in pre.LMB_TARGET_SEEDS] + [("D01", seed) for seed in pre.ROUTING_TARGET_SEEDS]
    if [(row.get("anonymous_family"), row.get("seed")) for row in episodes] != expected_episode_inventory:
        _fail("target episode inventory changed")
    totals = {"meta": 0, "strict": 0, "labels": 0, "certificate": 0, "meta_peak": 0, "strict_peak": 0, "steps": 0}
    for episode in episodes:
        expected_episode_keys = {
            "schema",
            "anonymous_family",
            "seed",
            "opaque_layout_id",
            "program_id",
            "initial_vector",
            "anonymous_action_catalogue",
            "target_binding",
            "decisions",
            "terminal_status",
            "execution_steps_per_arm",
            "meta_target_local_labels",
            "strict_target_ground_labels",
            "meta_planning_compute_events",
            "strict_planning_compute_events",
            "certificate_compute_events",
            "meta_peak_cache_entries",
            "strict_peak_cache_entries",
            "typed_adapter_abstract_state_consumed_by_planner",
            "episode_id",
        }
        if set(episode) != expected_episode_keys:
            _fail("target episode schema changed")
        if (
            episode["schema"] != "acfqp.generic_receding_episode.v47r1"
            or episode["terminal_status"] != "SUCCESS"
            or episode["meta_target_local_labels"] != 0
            or episode["typed_adapter_abstract_state_consumed_by_planner"] is not False
        ):
            _fail("target episode claim locks changed")
        result = _verify_lmb_episode(episode, expected_programs[0]) if episode["anonymous_family"] == "D00" else _verify_routing_episode(episode, expected_programs[1])
        episode_payload = {key: value for key, value in episode.items() if key != "episode_id"}
        if content_id(pre.FUTURE_DOMAINS["episode"], episode_payload) != episode.get("episode_id"):
            _fail("episode identity changed")
        if episode["strict_target_ground_labels"] != result["labels"] or episode["meta_planning_compute_events"] != result["meta"] or episode["strict_planning_compute_events"] != result["strict"] or episode["certificate_compute_events"] != result["certificate"] or episode["meta_peak_cache_entries"] != result["meta_peak"] or episode["strict_peak_cache_entries"] != result["strict_peak"]:
            _fail("episode compute/accounting changed")
        for key in ("meta", "strict", "labels", "certificate"):
            totals[key] += result[key]
        totals["meta_peak"] = max(totals["meta_peak"], result["meta_peak"])
        totals["strict_peak"] = max(totals["strict_peak"], result["strict_peak"])
        totals["steps"] += episode["execution_steps_per_arm"]

    source_labels = len(source_rows["D00"]) + len(source_rows["D01"])
    strict_labels = totals["labels"]
    break_even = None
    cumulative = 0
    for index, episode in enumerate(episodes, 1):
        cumulative += episode["strict_target_ground_labels"]
        if break_even is None and source_labels < cumulative:
            break_even = index
    sample = document["sample_tax"]
    if set(sample) != {
        "schema",
        "offline_source_labels",
        "meta_target_local_labels",
        "strict_target_ground_labels",
        "meta_total_labels_including_offline",
        "strict_total_labels",
        "registered_label_saving",
        "diagnostic_episode_break_even",
        "official_N_break_even",
        "positive_registered_condition_passed",
        "broad_cross_domain_sample_efficiency_claimed",
        "total_operational_work_saving_claimed",
        "sample_tax_id",
    }:
        _fail("sample-tax schema changed")
    if sample["meta_total_labels_including_offline"] != source_labels or sample["strict_target_ground_labels"] != strict_labels or sample["registered_label_saving"] != strict_labels - source_labels or sample["diagnostic_episode_break_even"] != break_even or sample["positive_registered_condition_passed"] is not True or sample["official_N_break_even"] is not None:
        _fail("sample-tax arithmetic changed")
    if (
        sample["schema"] != "acfqp.generic_sample_tax.v47r1"
        or sample["meta_target_local_labels"] != 0
        or sample["strict_total_labels"] != strict_labels
        or sample["broad_cross_domain_sample_efficiency_claimed"] is not False
        or sample["total_operational_work_saving_claimed"] is not False
    ):
        _fail("sample-tax claim locks changed")
    sample_payload = {key: value for key, value in sample.items() if key != "sample_tax_id"}
    if content_id(pre.FUTURE_DOMAINS["sample_tax"], sample_payload) != sample.get("sample_tax_id"):
        _fail("sample-tax identity changed")

    accounting = document["accounting_axes"]
    if accounting != {
        "offline_source_labels": source_labels,
        "target_local_labels_meta": 0,
        "target_ground_labels_strict": strict_labels,
        "source_environment_steps": source_labels,
        "target_execution_steps_meta": totals["steps"],
        "target_execution_steps_strict": totals["steps"],
        "synthesis_compute_events": source_labels + sum(row["synthesis_probe_count"] for row in document["source_archives"]),
        "planning_compute_events_meta": totals["meta"],
        "planning_compute_events_strict": totals["strict"],
        "certificate_compute_events": totals["certificate"],
        "peak_program_cache_entries": max(totals["meta_peak"], totals["strict_peak"]),
        "labels_steps_compute_and_peak_kept_separate": True,
    }:
        _fail("campaign accounting axes changed")
    if document["strict_ood_control"] != {
        "schema": "OPAQUE_CONTINUOUS_REAL_VECTOR",
        "registered_integer_grammar_compatible": False,
        "decision": "OOD_SCHEMA_REJECTED_NO_TRANSFER",
        "prior_access_count": 0,
        "environment_outcome_count": 0,
        "environment_step_count": 0,
    }:
        _fail("strict OOD no-transfer control changed")
    if document.get("official_execution_allowed") is not False or document.get("official_scalar_cost") is not None or document.get("official_N_break_even") is not None or document.get("counter_completeness_gate_status") != "NOT_RUN" or document.get("workload_economics_gate_status") != "NOT_RUN":
        _fail("official claim locks changed")

    verification_payload = {
        "schema": "acfqp.generic_cross_domain_verification.v47r1",
        "schema_version": SCHEMA_VERSION,
        "campaign_id": campaign_id,
        "campaign_sha256": hashlib.sha256(campaign_bytes).hexdigest(),
        "program_ids": [row["program_id"] for row in expected_programs],
        "episode_ids": [row["episode_id"] for row in episodes],
        "source_transition_count": source_labels,
        "strict_ground_label_count": strict_labels,
        "registered_label_saving": strict_labels - source_labels,
        "diagnostic_episode_break_even": break_even,
        "programs_reconstructed_from_raw_observations": True,
        "target_bindings_and_plans_reconstructed": True,
        "partial_support_reconstructed_without_exact_probability_authority": True,
        "accounting_reconstructed": True,
        "strict_ood_no_transfer_reconstructed": True,
        "producer_module_imported": False,
        "status": "PRODUCER_FREE_GENERIC_CROSS_DOMAIN_EVIDENCE_VERIFIED",
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "counter_completeness_gate_status": "NOT_RUN",
        "workload_economics_gate_status": "NOT_RUN",
    }
    return {
        **verification_payload,
        "generic_cross_domain_verification_id": content_id(pre.FUTURE_DOMAINS["verification"], verification_payload),
    }


def freeze_generic_bytecode_verification_v47r1(campaign_bytes: bytes) -> bytes:
    document = verify_generic_bytecode_campaign_bytes_v47r1(campaign_bytes)
    raw = canonical_json_bytes(document)
    if VERIFICATION_ID != "0" * 64 and (document["generic_cross_domain_verification_id"] != VERIFICATION_ID or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256):
        _fail("frozen V47r1 verification changed")
    return raw


__all__ = (
    "EXPECTED_CANONICAL_BYTE_COUNT",
    "EXPECTED_CANONICAL_SHA256",
    "VERIFICATION_ID",
    "freeze_generic_bytecode_verification_v47r1",
    "verify_generic_bytecode_campaign_bytes_v47r1",
)
