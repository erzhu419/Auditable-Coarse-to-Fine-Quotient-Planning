"""Producer-free semantic reconstruction of frozen V54r1 evidence."""

from __future__ import annotations

from collections import deque
from functools import lru_cache
import hashlib
import random
from typing import Any, Mapping, NoReturn

from acfqp.domains.stochastic_balanced_batch_refinement import generate_stochastic_balanced_batch_refinement
from acfqp.domains.stochastic_batch_refinement import (
    BatchRefinementAction,
    BatchRefinementState,
    BatchRefinementStatus,
    select_seeded_batch_refinement_outcome_v1,
)
from acfqp.generic_atomic_expression_world_model_v4 import (
    FlatRawActionV4,
    FlatRawTransitionV4,
    GenericAtomicExpressionWorldModelV4Error,
    execute_generic_atomic_support_v4,
    missing_relation_values_v4,
    plan_generic_atomic_program_v4,
    target_binding_from_initial_vector_v4,
)
from acfqp.generic_joint_factor_residual_world_model_v9 import synthesize_joint_factor_residual_world_model_v9
from acfqp.generic_layout_factorized_world_model_v5 import (
    align_generic_occurrence_v5,
    discover_generic_layout_v5,
    match_generic_layout_meta_prior_v5,
)
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_CAMPAIGN_V54_DOMAIN,
    CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_EPISODE_V54_DOMAIN,
    CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_FAILED_CERTIFICATE_V54_DOMAIN,
    CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_LAYOUT_V54_DOMAIN,
    CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_LOCAL_DISTINCTION_V54_DOMAIN,
    CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_MODEL_V54_DOMAIN,
    CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_OOD_REJECTION_V54_DOMAIN,
    CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_PROGRAM_V54_DOMAIN,
    CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_RAW_OBSERVATION_V54_DOMAIN,
    CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_SUPPORT_V54_DOMAIN,
    CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_VERIFICATION_V54_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
)


EXPECTED_CAMPAIGN_ID = "48f49e489e1cc5dfc98ec14c23565f66edfa93d51e15ca23f66f4668cc377223"
EXPECTED_CAMPAIGN_BYTE_COUNT = 129_902
EXPECTED_CAMPAIGN_SHA256 = "9bf6f766b95fb18a81a7b69df037f9b61dba2f342579356636cc784d6955cfd9"
VERIFICATION_ID = "a4d71d1f6517c032e8f7f14b4fd8b2e6ab9560ca96bd4741e2d5874ad06b5acc"
EXPECTED_CANONICAL_BYTE_COUNT = 1_407
EXPECTED_CANONICAL_SHA256 = "110a27f75bc293776d3daece348bdae020128d67bea29dc235c3d81263565a70"

_DOMAINS = {
    "observation": CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_RAW_OBSERVATION_V54_DOMAIN,
    "layout": CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_LAYOUT_V54_DOMAIN,
    "program": CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_PROGRAM_V54_DOMAIN,
    "support": CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_SUPPORT_V54_DOMAIN,
    "joint_model": CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_MODEL_V54_DOMAIN,
    "failed_certificate": CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_FAILED_CERTIFICATE_V54_DOMAIN,
    "distinction": CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_LOCAL_DISTINCTION_V54_DOMAIN,
    "episode": CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_EPISODE_V54_DOMAIN,
    "ood": CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_OOD_REJECTION_V54_DOMAIN,
    "campaign": CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_CAMPAIGN_V54_DOMAIN,
}
_TOKENS = {"A": 9_001, "F": 9_007, "S": 9_011}
_SOURCE_SEEDS = (542_101, 542_102, 542_103)
_TARGET_SEEDS = tuple(range(542_201, 542_209))
_LIBRARY = {
    "factor_library_id": "46aa60cc33ca61238612342ed9fe73e91cfa7bfb639b4a8f0afa29c491428162",
    "cross_schema_subprograms": [
        {"signature_sha256": "012651c74d7a2c07190817603bc2aeb9a069c8c1dc5a3f9d828518a03aeb367e", "source_schema_pairs": [[7, 5], [9, 6]]},
        {"signature_sha256": "16fcf756e4d606282a0f656f4ab960069273f8f895d8a0abcf7f0d530c07a072", "source_schema_pairs": [[7, 5], [9, 6]]},
        {"signature_sha256": "c2fe69a54e58afa7f6c68992e4ea16eb6aa5800b6543d9c1022729dc6ebc52b5", "source_schema_pairs": [[7, 5], [9, 6]]},
    ],
}


class ConstructionK7JointFactorResidualIndependentVerifierV54R1Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7JointFactorResidualIndependentVerifierV54R1Error(message)


def _interface(seed: int, kernel: Any):
    state_order = list(range(6))
    action_order = list(range(5))
    random.Random(seed ^ 0x54A17).shuffle(state_order)
    random.Random(seed ^ 0x54B29).shuffle(action_order)
    catalogue = tuple(
        FlatRawActionV4(
            key,
            tuple(
                (
                    rule.source_stage,
                    rule.anonymous_advance_class,
                    rule.unit_increment,
                    rule.risk_increment,
                    1,
                )[index]
                for index in action_order
            ),
        )
        for key, rule in enumerate(kernel.rules)
    )

    def encode(state: BatchRefinementState) -> tuple[int, ...]:
        status = _TOKENS[
            "A"
            if state.status is BatchRefinementStatus.ACTIVE
            else "S"
            if state.status is BatchRefinementStatus.SUCCESS
            else "F"
        ]
        semantic = (
            state.stage,
            state.units,
            state.risk,
            status,
            kernel.risk_capacity,
            kernel.goal_stage,
        )
        return tuple(semantic[index] for index in state_order)

    return catalogue, encode


def _observe(occurrence: int, kernel: Any, catalogue, encode):
    queue = deque([kernel.initial_distribution()[0][1]])
    seen = set(queue)
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
                        tuple(row.rule for row in legal),
                        catalogue[action.rule],
                        encode(successor),
                        tuple(row.rule for row in legal_after),
                        None if legal_after else successor.status is BatchRefinementStatus.SUCCESS,
                    )
                )
                if successor.status is BatchRefinementStatus.ACTIVE and successor not in seen:
                    seen.add(successor)
                    queue.append(successor)
    return tuple(rows), labels, len(seen)


def _archive(occurrence, seed, catalogue, rows, labels, reachable):
    payload = {
        "schema": "acfqp.joint_factor_residual_raw_observation.v54r1",
        "family_token": "OPAQUE_BALANCED_STOCHASTIC_BATCH_REFINEMENT",
        "occurrence": occurrence,
        "seed": seed,
        "anonymous_action_catalogue": [row.to_document() for row in catalogue],
        "raw_transitions": [row.to_document() for row in rows],
        "source_support_labels": labels,
        "reachable_active_state_count": reachable,
        "generation_witness_accessed": False,
        "semantic_layout_names_serialized": False,
        "policy": "WITNESS_BLIND_EXHAUSTIVE_REACHABLE_FRONTIER_ALL_LEGAL_SUPPORTS",
    }
    return {**payload, "raw_observation_id": content_id(_DOMAINS["observation"], payload)}


def _relations(program):
    encoded = canonical_json_bytes([row["expression"] for row in program["compiled_assignments"]]).decode()
    return {name: rows for name, rows in program["occurrence_bindings"][0]["relations"].items() if f'"{name}"' in encoded}


def _relation_fields(program):
    result = {}
    def visit(value):
        if type(value) is not list:
            return
        if len(value) >= 3 and value[0] == "E04" and type(value[2]) is list and value[2][:1] == ["E01"]:
            result[value[1]] = value[2][1]
        for child in value:
            visit(child)
    for assignment in program["compiled_assignments"]:
        visit(assignment["expression"])
    return result


def _recover(program, binding, state, action, actual, name, relation_input, overlay):
    suffix = name.rsplit("_", 1)[-1]
    cap = 64
    if suffix.isdigit() and 0 < state[int(suffix)]:
        cap = min(cap, state[int(suffix)] - 1)
    matches = []
    for candidate in range(cap + 1):
        trial = {key: dict(rows) for key, rows in overlay.items()}
        trial.setdefault(name, {})[relation_input] = candidate
        try:
            predicted = set(execute_generic_atomic_support_v4(program, state, action, binding, relation_overlay=trial))
        except (GenericAtomicExpressionWorldModelV4Error, ZeroDivisionError):
            continue
        if predicted == actual:
            matches.append(candidate)
    if len(matches) != 1:
        _fail("independent V54r1 relation recovery was not unique")
    return matches[0]


def _strict_choice(kernel, state, cache):
    choices = {}
    labels = 0
    @lru_cache(maxsize=None)
    def solve(current):
        nonlocal labels
        if current.status is BatchRefinementStatus.SUCCESS:
            return True
        if current.status is BatchRefinementStatus.FAILURE:
            return False
        for action in kernel.actions(current):
            key = (current, action.rule)
            if key not in cache:
                cache[key] = tuple(row.next_state for row in kernel.step(current, action))
                labels += 1
            if all(solve(successor) for successor in cache[key]):
                choices[current] = action.rule
                return True
        return False
    if not solve(state):
        _fail("independent V54r1 direct planner failed")
    return choices[state], solve.cache_info().currsize, labels


def _episode(seed, arm, actions, tapes, planning, peak, labels, layout_labels, local_labels, failures, success):
    payload = {
        "schema": "acfqp.joint_factor_residual_receding_episode.v54r1",
        "seed": seed,
        "arm": arm,
        "action_keys": actions,
        "outcome_tape_sha256": tapes,
        "execution_steps": len(actions),
        "planning_compute_events": planning,
        "peak_planning_cache_entries": peak,
        "ground_support_labels": labels,
        "target_layout_support_labels": layout_labels,
        "local_ground_support_labels": local_labels,
        "failed_certificate_count": failures,
        "success": success,
    }
    return {**payload, "episode_id": content_id(_DOMAINS["episode"], payload)}


def _ood_rows():
    catalogue = tuple(FlatRawActionV4(index, (bit, 1)) for index, bit in enumerate((1, 2, 4)))
    rows = []
    for mask in (0, 1, 2):
        for key, bit in enumerate((1, 2, 4)):
            successor = mask | bit
            status = "F" if successor & 4 else "S" if successor == 3 else "A"
            rows.append(FlatRawTransitionV4(0, len(rows), (mask, _TOKENS["A"], 3, 4, 1), (0, 1, 2), catalogue[key], (successor, _TOKENS[status], 3, 4, 1), () if status != "A" else (0, 1, 2), None if status == "A" else status == "S"))
    return tuple(rows), catalogue


def _reconstruct(campaign: Mapping[str, Any]) -> dict[str, Any]:
    rows_by_occurrence = {}
    catalogues = {}
    archives = []
    source_labels = 0
    for occurrence, seed in enumerate(_SOURCE_SEEDS):
        kernel, _ = generate_stochastic_balanced_batch_refinement(stage_count=6, unit_base=3, seed=seed)
        catalogue, encode = _interface(seed, kernel)
        rows, labels, reachable = _observe(occurrence, kernel, catalogue, encode)
        rows_by_occurrence[occurrence] = rows
        catalogues[occurrence] = catalogue
        archives.append(_archive(occurrence, seed, catalogue, rows, labels, reachable))
        source_labels += labels
    joint = synthesize_joint_factor_residual_world_model_v9(
        rows_by_occurrence,
        catalogues,
        _LIBRARY,
        layout_domain=_DOMAINS["layout"],
        program_domain=_DOMAINS["program"],
        support_domain=_DOMAINS["support"],
        factor_domain=_DOMAINS["joint_model"],
        result_domain=_DOMAINS["joint_model"],
        minimum_reusable_factor_count=3,
    )
    program = joint["target_world_model"]["compiled_program"]
    reference_rows = rows_by_occurrence[0]
    reference_catalogue = catalogues[0]
    reference_layout = discover_generic_layout_v5(reference_rows, reference_catalogue, layout_domain=_DOMAINS["layout"])
    base_relations = _relations(program)
    relation_fields = _relation_fields(program)
    calibrations = []
    failures = []
    distinctions = []
    structural = []
    strict = []
    overlay = {}
    for episode_index, seed in enumerate(_TARGET_SEEDS):
        kernel, _ = generate_stochastic_balanced_batch_refinement(stage_count=7, unit_base=4, seed=seed)
        catalogue, encode = _interface(seed, kernel)
        calibration_rows, layout_labels, reachable = _observe(0, kernel, catalogue, encode)
        layout = match_generic_layout_meta_prior_v5(reference_rows, reference_catalogue, reference_layout, calibration_rows, catalogue, layout_domain=_DOMAINS["layout"])
        calibrations.append({"seed": seed, "support_labels": layout_labels, "raw_transition_count": len(calibration_rows), "reachable_active_state_count": reachable, "layout": layout.to_document(), "policy": "WITNESS_BLIND_FULL_FRONTIER_THEN_UNIQUE_STRUCTURAL_MATCH", "generation_witness_accessed": False, "relation_outputs_consumed_for_target_binding": False})
        _, aligned_catalogue = align_generic_occurrence_v5(calibration_rows, catalogue, layout, canonical_occurrence=0)
        initial = kernel.initial_distribution()[0][1]
        raw_initial = encode(initial)
        canonical_initial = tuple(raw_initial[index] for index in layout.state_canonical_to_raw)
        binding = target_binding_from_initial_vector_v4(program, canonical_initial, base_relations=base_relations, terminal_tokens=_TOKENS)
        actions = []
        tapes = []
        planning = 0
        peak = 0
        local_labels = 0
        episode_failures = 0
        state = initial
        decision = 0
        while state.status is BatchRefinementStatus.ACTIVE:
            raw_state = encode(state)
            canonical_state = tuple(raw_state[index] for index in layout.state_canonical_to_raw)
            missing = sorted({item for action in aligned_catalogue for item in missing_relation_values_v4(program, action, binding, relation_overlay=overlay)})
            for name, relation_input in missing:
                failure_payload = {"schema": "acfqp.joint_factor_residual_failed_certificate.v54r1", "seed": seed, "episode_index": episode_index, "decision_index": decision, "program_id": program["program_id"], "missing_relation_name": name, "missing_relation_input": relation_input, "ground_query_performed_before_failure": False, "outcome": "FAILED_COMPILED_RELATION_SUPPORT_CERTIFICATE"}
                failure = {**failure_payload, "failed_certificate_id": content_id(_DOMAINS["failed_certificate"], failure_payload)}
                failures.append(failure)
                episode_failures += 1
                field = relation_fields[name]
                aligned_action = next(row for row in aligned_catalogue if row.fields[field] == relation_input)
                rule = kernel.rules[aligned_action.key]
                probe = BatchRefinementState(rule.source_stage, 0, 0, 0, BatchRefinementStatus.ACTIVE)
                raw_probe = encode(probe)
                canonical_probe = tuple(raw_probe[index] for index in layout.state_canonical_to_raw)
                actual = {tuple(encode(outcome.next_state)[index] for index in layout.state_canonical_to_raw) for outcome in kernel.step(probe, BatchRefinementAction(aligned_action.key))}
                value = _recover(program, binding, canonical_probe, aligned_action, actual, name, relation_input, overlay)
                overlay.setdefault(name, {})[relation_input] = value
                distinction_payload = {"schema": "acfqp.joint_factor_residual_local_distinction.v54r1", "failed_certificate_id": failure["failed_certificate_id"], "relation_name": name, "relation_input": relation_input, "relation_output": value, "query_after_failed_certificate": True, "ground_support_labels": 1}
                distinctions.append({**distinction_payload, "local_distinction_id": content_id(_DOMAINS["distinction"], distinction_payload)})
                local_labels += 1
            plan, evaluations, cache_size = plan_generic_atomic_program_v4(program, canonical_state, aligned_catalogue, binding, relation_overlay=overlay)
            key = plan[0]
            outcome, tape = select_seeded_batch_refinement_outcome_v1(kernel.step(state, BatchRefinementAction(key)), seed=seed, episode_index=episode_index, decision_index=decision)
            state = outcome.next_state
            actions.append(key)
            tapes.append(tape)
            planning += evaluations
            peak = max(peak, cache_size)
            decision += 1
        structural.append(_episode(seed, "JOINT_DISCOVERED_ABSTRACT_WORLD_MODEL", actions, tapes, planning, peak, layout_labels + local_labels, layout_labels, local_labels, episode_failures, state.status is BatchRefinementStatus.SUCCESS))
        strict_actions = []
        strict_tapes = []
        strict_planning = 0
        strict_peak = 0
        strict_labels = 0
        strict_state = initial
        strict_cache = {}
        strict_decision = 0
        while strict_state.status is BatchRefinementStatus.ACTIVE:
            key, compute, labels = _strict_choice(kernel, strict_state, strict_cache)
            outcome, tape = select_seeded_batch_refinement_outcome_v1(kernel.step(strict_state, BatchRefinementAction(key)), seed=seed, episode_index=episode_index, decision_index=strict_decision)
            strict_state = outcome.next_state
            strict_actions.append(key)
            strict_tapes.append(tape)
            strict_planning += compute
            strict_peak = max(strict_peak, compute)
            strict_labels += labels
            strict_decision += 1
        strict.append(_episode(seed, "STRICT_EXACT_CONTEXT", strict_actions, strict_tapes, strict_planning, strict_peak, strict_labels, 0, 0, 0, strict_state.status is BatchRefinementStatus.SUCCESS))
    ood_rows, ood_catalogue = _ood_rows()
    ood_model = synthesize_joint_factor_residual_world_model_v9({0: ood_rows}, {0: ood_catalogue}, _LIBRARY, layout_domain=_DOMAINS["layout"], program_domain=_DOMAINS["program"], support_domain=_DOMAINS["support"], factor_domain=_DOMAINS["joint_model"], result_domain=_DOMAINS["joint_model"], minimum_reusable_factor_count=3)
    ood_payload = {"schema": "acfqp.joint_factor_residual_ood_rejection.v54r1", "joint_model_id": ood_model["joint_model_id"], "factorable_reusable_count": ood_model["factorable_reusable_count"], "minimum_reusable_factor_count": 3, "complete_ood_program_synthesized_from_raw_observations": True, "prior_transfer_attempted": False, "ood_outcome_execution_performed": False, "outcome": "STRICT_SIGNATURE_THRESHOLD_OOD_NO_TRANSFER"}
    ood = {**ood_payload, "ood_rejection_id": content_id(_DOMAINS["ood"], ood_payload)}
    expected_accounting = {
        "historical_factor_library_labels": 370,
        "fresh_source_support_labels": source_labels,
        "target_layout_support_labels": sum(row["target_layout_support_labels"] for row in structural),
        "local_ground_support_labels": sum(row["local_ground_support_labels"] for row in structural),
        "structural_execution_steps": sum(row["execution_steps"] for row in structural),
        "strict_execution_steps": sum(row["execution_steps"] for row in strict),
        "full_program_atomic_synthesis_compute_events": program["atomic_expression_evaluations"],
        "dependency_classification_count": len(joint["assignment_classifications"]),
        "structural_planning_compute_events": sum(row["planning_compute_events"] for row in structural),
        "strict_planning_compute_events": sum(row["planning_compute_events"] for row in strict),
        "certificate_compute_events": len(failures),
        "all_axes_separate": True,
    }
    expected = {
        "source_archives": archives,
        "joint_world_model": joint,
        "target_layout_calibrations": calibrations,
        "failed_certificates": failures,
        "local_distinctions": distinctions,
        "relation_overlay": {name: [[key, value] for key, value in sorted(rows.items())] for name, rows in sorted(overlay.items())},
        "structural_episodes": structural,
        "strict_episodes": strict,
        "ood_rejection": ood,
        "accounting": expected_accounting,
    }
    for key, value in expected.items():
        if campaign.get(key) != value:
            _fail("producer-free V54r1 reconstruction changed: " + key)
    return {
        "joint_model_id": joint["joint_model_id"],
        "program_id": program["program_id"],
        "factorable_reusable_count": joint["factorable_reusable_count"],
        "factorable_novel_count": joint["factorable_novel_count"],
        "residual_schema_bound_count": joint["residual_schema_bound_count"],
        "source_support_labels": source_labels,
        "target_layout_support_labels": expected_accounting["target_layout_support_labels"],
        "local_ground_support_labels": len(distinctions),
        "failed_certificate_count": len(failures),
        "held_out_episode_count": len(structural),
        "matched_execution_steps": expected_accounting["structural_execution_steps"],
        "ood_reusable_count": ood_model["factorable_reusable_count"],
        "ood_transfer_admitted": ood_model["transfer_admitted"],
    }


def verify_joint_factor_residual_campaign_bytes_v54r1(raw: bytes) -> dict[str, Any]:
    if type(raw) is not bytes or len(raw) != EXPECTED_CAMPAIGN_BYTE_COUNT or hashlib.sha256(raw).hexdigest() != EXPECTED_CAMPAIGN_SHA256:
        _fail("frozen V54r1 campaign bytes changed")
    campaign = loads_canonical_json(raw)
    if type(campaign) is not dict or campaign.get("campaign_id") != EXPECTED_CAMPAIGN_ID:
        _fail("frozen V54r1 campaign identity changed")
    payload = {key: value for key, value in campaign.items() if key != "campaign_id"}
    if content_id(_DOMAINS["campaign"], payload) != EXPECTED_CAMPAIGN_ID:
        _fail("V54r1 campaign content ID changed")
    if campaign.get("v51_target_program_consumed") is not False or campaign.get("v51_reused_factor_slot_inventory_consumed") is not False:
        _fail("V54r1 forbidden target predecessor input changed")
    if campaign.get("official_execution_allowed") is not False or campaign.get("official_scalar_cost") is not None or campaign.get("official_N_break_even") is not None or campaign.get("WORKLOAD_ECONOMICS_GATE") != "NOT_RUN" or campaign.get("COUNTER_COMPLETENESS_GATE") != "NOT_RUN":
        _fail("V54r1 locked official gates changed")
    return _reconstruct(campaign)


def freeze_joint_factor_residual_verification_v54r1(campaign_bytes: bytes) -> bytes:
    projection = verify_joint_factor_residual_campaign_bytes_v54r1(campaign_bytes)
    payload = {
        "schema": "acfqp.joint_factor_residual_independent_verification.v54r1",
        "campaign_id": EXPECTED_CAMPAIGN_ID,
        "campaign_byte_count": EXPECTED_CAMPAIGN_BYTE_COUNT,
        "campaign_sha256": EXPECTED_CAMPAIGN_SHA256,
        "producer_module_imported": False,
        "campaign_core_module_imported": False,
        "raw_source_observations_reconstructed": True,
        "complete_anonymous_program_reconstructed": True,
        "factorable_residual_classification_reconstructed": True,
        "held_out_layouts_plans_certificates_and_local_distinctions_reconstructed": True,
        "strict_ood_program_and_rejection_reconstructed": True,
        "scientific_projection_exact": True,
        "projection": projection,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    document = {**payload, "verification_id": content_id(CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_VERIFICATION_V54_DOMAIN, payload)}
    raw = canonical_json_bytes(document)
    if VERIFICATION_ID != "0" * 64 and (
        document["verification_id"] != VERIFICATION_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V54r1 independent verification changed")
    return raw


def verify_joint_factor_residual_verification_bytes_v54r1(raw: bytes) -> dict[str, Any]:
    if type(raw) is not bytes:
        _fail("V54r1 verification requires bytes")
    document = loads_canonical_json(raw)
    if type(document) is not dict:
        _fail("V54r1 verification document changed")
    payload = {key: value for key, value in document.items() if key != "verification_id"}
    if content_id(CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_VERIFICATION_V54_DOMAIN, payload) != document.get("verification_id"):
        _fail("V54r1 verification content ID changed")
    if VERIFICATION_ID != "0" * 64 and (
        document["verification_id"] != VERIFICATION_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("V54r1 verification frozen bytes changed")
    return document


__all__ = (
    "EXPECTED_CAMPAIGN_ID",
    "VERIFICATION_ID",
    "freeze_joint_factor_residual_verification_v54r1",
    "verify_joint_factor_residual_campaign_bytes_v54r1",
    "verify_joint_factor_residual_verification_bytes_v54r1",
)
