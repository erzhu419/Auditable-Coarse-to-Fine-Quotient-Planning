"""Producer-free verification of V174 receipt-driven invalidation evidence.

The verifier reexecutes the registered target outcomes through the retained
V172 independent runner.  It then reconstructs V174 dependency projections,
cache invalidations, retained authorization chains, program-cache closures,
and execution joins from the frozen model and plan documents.  It does not
import the V174 producer, campaign core, or sequence implementation.
"""

from __future__ import annotations

from collections import defaultdict, deque
from concurrent.futures import ProcessPoolExecutor
import hashlib
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v109 as domains_v109
from acfqp import construction_k7_domain_registry_extension_v115 as domains_v115
from acfqp import construction_k7_domain_registry_extension_v174 as domains
from acfqp import construction_k7_online_typed_plan_receipt_independent_verifier_v172r1 as base
from acfqp.generic_packet_batching_adapter_v134 import FAMILY as PACKET_FAMILY
from acfqp.generic_reservoir_dispatch_adapter_v171 import FAMILY as RESERVOIR_FAMILY
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


PREREGISTRATION_ID = "ca6f465efb4c9c33424aeb66b6957d58384d0e46324934fd88ac1e6bf6628705"
PREREGISTRATION_BYTE_COUNT = 3_413
PREREGISTRATION_SHA256 = "798702f1b75dd3d39be72ee11eeb6e57b64fb6f4f3ba6bc391aeefd9e7582559"
CAMPAIGN_ID = "0e5c03c7252ea5b11e5819cbe0b11917ac90722f988969a8b55ef6f446c123ec"
CAMPAIGN_BYTE_COUNT = 54_036_308
CAMPAIGN_SHA256 = "23453500dd9b80213fb01b657eba323a957ef8063503f756bf6df82463754d9a"
V173R1_CAMPAIGN_ID = "418dc59c44243cb96e275539f564b1cd651664c9af19538d75f675093b8f2840"
V173R1_VERIFICATION_ID = "223891b22ccd29e9fb8386b182e6ee1226933b33e5d9e00defe8acf8bdd7a125"
TARGETS = (
    (PACKET_FAMILY, 1_119_851, "GRAPH_AND_COMPILED_DEPENDENCY_INVALIDATION"),
    (PACKET_FAMILY, 1_119_852, "GRAPH_AND_COMPILED_DEPENDENCY_INVALIDATION"),
    (
        RESERVOIR_FAMILY,
        1_129_851,
        "UNAFFECTED_DEPENDENCY_RETENTION_AND_REVALIDATION",
    ),
    (
        RESERVOIR_FAMILY,
        1_129_852,
        "UNAFFECTED_DEPENDENCY_RETENTION_AND_REVALIDATION",
    ),
)
EPISODES = (1_033, 1_034, 1_035, 1_036)
TARGET_WORKERS = 2
V106_PLAN_DOMAIN = "acfqp:generic-legality-conditioned-quotient-plan:v106"
GRAPH_DEPENDENCY = "MINIMAL_QUOTIENT_BFS_DEPENDENCY"
COMPILED_STATE_DEPENDENCY = "EXACT_COMPILED_SUCCESSOR_STATE_DEPENDENCY"
TAXONOMY = {
    (
        "acfqp.generic_legality_conditioned_quotient_plan.v106",
        "OBSERVATION_QUOTIENT_GRAPH",
    ): "OBSERVATION_DERIVED_QUOTIENT_ORDER",
    (
        "acfqp.generic_legality_conditioned_quotient_plan.v106",
        "COMPILED_FACTOR_PROGRAM_FALLBACK",
    ): "DIRECT_COMPILED_PROGRAM_ORDER",
    (
        "acfqp.generic_dependency_revalidated_quotient_heuristic_plan.v109",
        "DEPENDENCY_REVALIDATED_PRIOR_QUOTIENT_ORDER",
    ): "DEPENDENCY_REVALIDATED_QUOTIENT_REUSE",
    (
        "acfqp.generic_projected_program_memo_plan.v115",
        "COMPILED_FACTOR_PROGRAM_MEMOIZED",
    ): "SUCCESSOR_STATE_MEMOIZED_PROGRAM_REUSE",
}
VERIFICATION_ID = "3fbd91146f5eacd92ec309a88634071ea983699ea1efe2d40bd5c078b60593ae"
EXPECTED_CANONICAL_BYTE_COUNT = 2_617
EXPECTED_CANONICAL_SHA256 = "64e01b82ff142a5ed784cb170b73bb016f98949939139ac6e4d339fa3039f0a0"


class ConstructionK7ReceiptDrivenInvalidationIndependentVerifierV174Error(
    ValueError
):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7ReceiptDrivenInvalidationIndependentVerifierV174Error(
        message
    )


def _content_id(domain: str, payload: Any) -> str:
    return hashlib.sha256(
        domain.encode() + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


def _sha(document: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(document)).hexdigest()


def _plan_id(plan: Mapping[str, Any]) -> str:
    payload = {
        key: value
        for key, value in plan.items()
        if key != "legality_conditioned_quotient_plan_id"
    }
    if plan.get("schema") == "acfqp.generic_legality_conditioned_quotient_plan.v106":
        return _content_id(V106_PLAN_DOMAIN, payload)
    if (
        plan.get("schema")
        == "acfqp.generic_dependency_revalidated_quotient_heuristic_plan.v109"
    ):
        return domains_v109.extension_content_id_v109(
            domains_v109.CONSTRUCTION_K7_DEPENDENCY_REVALIDATED_QUOTIENT_PLAN_V109_DOMAIN,
            payload,
        )
    if plan.get("schema") == "acfqp.generic_projected_program_memo_plan.v115":
        return domains_v115.extension_content_id_v115(
            domains_v115.CONSTRUCTION_K7_PROJECTED_PROGRAM_MEMO_PLAN_V115_DOMAIN,
            payload,
        )
    _fail("V174 independent plan schema escaped taxonomy")


def _frozen(raw, *, count, digest, identity_key, identity, name):
    document = loads_canonical_json(raw)
    if not (
        canonical_json_bytes(document) == raw
        and len(raw) == count
        and hashlib.sha256(raw).hexdigest() == digest
        and document.get(identity_key) == identity
    ):
        _fail(f"V174 independent frozen {name} changed")
    return document


def _adjacency(model: Mapping[str, Any]):
    staged: dict[tuple[int, ...], set[tuple[int, tuple[int, ...]]]] = defaultdict(
        set
    )
    for row in model["projected_edge_rows"]:
        staged[tuple(row["projected_pre"])].add(
            (row["action_key"], tuple(row["projected_post"]))
        )
    return {state: tuple(sorted(edges)) for state, edges in staged.items()}


def _terminal_match(state, rules):
    for value, rule in zip(state, rules, strict=True):
        kind = rule["kind"]
        if kind == "EQUAL" and value != rule["value"]:
            return False
        if kind == "AT_LEAST" and value < rule["value"]:
            return False
        if kind == "AT_MOST" and value > rule["value"]:
            return False
        if kind == "OBSERVED_SET" and value not in rule["values"]:
            return False
    return True


def _dependency_receipt(model, source_plan, initial_state):
    if not (
        source_plan.get("schema")
        == "acfqp.generic_legality_conditioned_quotient_plan.v106"
        and source_plan.get("planning_source") == "OBSERVATION_QUOTIENT_GRAPH"
        and source_plan.get("quotient_graph_id") == model.get("quotient_graph_id")
    ):
        _fail("V174 independent dependency source changed")
    legal = tuple(source_plan["exact_legal_action_keys_at_initial_state"])
    rules = tuple(source_plan["embedded_projected_plan"]["terminal_projection_rule"])
    adjacency = _adjacency(model)
    queue = deque((initial_state,))
    predecessor = {initial_state: None}
    popped = []
    goal = None
    evaluations = 0
    while queue:
        state = queue.popleft()
        terminal = _terminal_match(state, rules)
        edges = adjacency.get(state, ())
        popped.append(
            {
                "projected_state": list(state),
                "terminal_match": terminal,
                "outgoing_edges": [
                    {"action_key": key, "projected_post": list(post)}
                    for key, post in edges
                ],
            }
        )
        if terminal:
            goal = state
            break
        for key, successor in edges:
            evaluations += 1
            if state == initial_state and key not in legal:
                continue
            if successor not in predecessor:
                predecessor[successor] = (state, key)
                queue.append(successor)
    if goal is None:
        _fail("V174 independent dependency BFS found no goal")
    actions = []
    cursor = goal
    while predecessor[cursor] is not None:
        parent, key = predecessor[cursor]
        actions.append(key)
        cursor = parent
    actions.reverse()
    if not (
        actions == source_plan["projected_action_path"]
        and evaluations == source_plan["abstract_support_branch_evaluations"]
    ):
        _fail("V174 independent dependency BFS differs from source plan")
    payload = {
        "schema": "acfqp.generic_quotient_plan_dependency_receipt.v109",
        "source_quotient_plan_id": source_plan[
            "legality_conditioned_quotient_plan_id"
        ],
        "source_quotient_graph_id": model["quotient_graph_id"],
        "partial_candidate_id": source_plan["partial_candidate_id"],
        "initial_projected_state": list(initial_state),
        "exact_legal_action_keys": list(legal),
        "terminal_projection_rule": [dict(row) for row in rules],
        "ordered_bfs_dependency_rows": popped,
        "source_projected_action_path": actions,
        "source_initial_action_key": actions[0],
        "source_branch_evaluations": evaluations,
        "dependency_row_count": len(popped),
        "dependency_validation_check_count": sum(
            1 + len(row["outgoing_edges"]) for row in popped
        ),
        "only_dequeued_pre_goal_states_and_the_first_goal_retained": True,
        "unrelated_quotient_edges_deliberately_excluded": True,
        "receipt_is_ordering_dependency_not_safety_authority": True,
        "query_local_exact_certificate_remains_only_safety_authority": True,
    }
    return {
        **payload,
        "dependency_receipt_id": domains_v109.extension_content_id_v109(
            domains_v109.CONSTRUCTION_K7_DEPENDENCY_REVALIDATED_QUOTIENT_DEPENDENCY_V109_DOMAIN,
            payload,
        ),
    }


def _models_by_id(sequence):
    result = {}
    for model in (
        *sequence["quotient_models_before_each_episode"],
        *sequence["quotient_models_after_each_episode"],
    ):
        identity = model["quotient_graph_id"]
        prior = result.get(identity)
        if prior is not None and canonical_json_bytes(prior) != canonical_json_bytes(model):
            _fail("V174 independent quotient graph identity collision")
        result[identity] = model
    return result


def _graph_dependency_for_plan(plan, projection, models):
    if plan["planning_source"] == "OBSERVATION_QUOTIENT_GRAPH":
        source_plan = plan
    else:
        source_plan = plan.get("source_legality_conditioned_quotient_plan")
    states = projection.get("ordered_projected_state_dependencies")
    model = models.get(projection.get("source_quotient_graph_id"))
    if type(states) is not list or not states or model is None:
        _fail("V174 independent graph dependency inventory changed")
    dependency = _dependency_receipt(model, source_plan, tuple(states[0]))
    if plan["planning_source"] != "OBSERVATION_QUOTIENT_GRAPH" and (
        canonical_json_bytes(plan.get("quotient_plan_dependency_receipt"))
        != canonical_json_bytes(dependency)
    ):
        _fail("V174 independent embedded dependency receipt changed")
    return dependency


def _expected_projection(plan, wrapper, projection, models, state_before, chains):
    typed = TAXONOMY.get((plan.get("schema"), plan.get("planning_source")))
    if typed is None:
        _fail("V174 independent projection escaped taxonomy")
    plan_id = _plan_id(plan)
    legal = tuple(plan["exact_legal_action_keys_at_initial_state"])
    if typed in {
        "OBSERVATION_DERIVED_QUOTIENT_ORDER",
        "DEPENDENCY_REVALIDATED_QUOTIENT_REUSE",
    }:
        dependency = _graph_dependency_for_plan(plan, projection, models)
        if typed == "OBSERVATION_DERIVED_QUOTIENT_ORDER":
            chain = []
            current_graph = dependency["source_quotient_graph_id"]
            if dependency["source_quotient_plan_id"] != plan_id:
                _fail("V174 independent observation dependency source changed")
        else:
            validation = plan["dependency_revalidation"]
            chain = validation["epoch_authorization_chain"]
            expected_chain = chains.get(dependency["dependency_receipt_id"], [])
            if not (
                canonical_json_bytes(chain) == canonical_json_bytes(expected_chain)
                and validation["dependency_receipt_id"]
                == dependency["dependency_receipt_id"]
                and validation["per_hit_dependency_rescan_performed"] is False
                and validation["dependency_validation_check_count"] == 0
            ):
                _fail("V174 independent incremental authorization chain changed")
            current_graph = validation["current_quotient_graph_id"]
        states = [
            row["projected_state"]
            for row in dependency["ordered_bfs_dependency_rows"]
        ]
        payload = {
            "schema": "acfqp.online_plan_dependency_projection.v174",
            "dependency_kind": GRAPH_DEPENDENCY,
            "typed_plan_source": typed,
            "source_plan_id": plan_id,
            "partial_candidate_id": plan["partial_candidate_id"],
            "current_quotient_graph_id": current_graph,
            "exact_legal_action_keys_sha256": _sha(list(legal)),
            "quotient_dependency_receipt_id": dependency["dependency_receipt_id"],
            "dependency_source_plan_id": dependency["source_quotient_plan_id"],
            "source_quotient_graph_id": dependency["source_quotient_graph_id"],
            "ordered_projected_state_dependencies": states,
            "ordered_projected_state_dependencies_sha256": _sha(states),
            "terminal_projection_rule_sha256": _sha(
                dependency["terminal_projection_rule"]
            ),
            "epoch_authorization_chain_ids": [
                row["epoch_transition_receipt_id"] for row in chain
            ],
            "minimal_dependency_projection_excludes_unrelated_graph_edges": True,
            "dependency_projection_is_ordering_not_safety_authority": True,
            "query_local_exact_overlay_remains_only_safety_authority": True,
        }
    elif typed == "DIRECT_COMPILED_PROGRAM_ORDER":
        rules = plan["embedded_projected_plan"]["terminal_projection_rule"]
        payload = {
            "schema": "acfqp.online_plan_dependency_projection.v174",
            "dependency_kind": COMPILED_STATE_DEPENDENCY,
            "typed_plan_source": typed,
            "source_plan_id": plan_id,
            "partial_candidate_id": plan["partial_candidate_id"],
            "current_quotient_graph_id": plan["quotient_graph_id"],
            "exact_legal_action_keys_sha256": _sha(list(legal)),
            "source_compiled_program_plan_id": plan_id,
            "source_successor_state_id": state_before,
            "current_successor_state_id": state_before,
            "terminal_projection_rule_sha256": _sha(rules),
            "exact_compiled_state_change_invalidates_program_memo": True,
            "dependency_projection_is_ordering_not_safety_authority": True,
            "query_local_exact_overlay_remains_only_safety_authority": True,
        }
    else:
        payload = {
            "schema": "acfqp.online_plan_dependency_projection.v174",
            "dependency_kind": COMPILED_STATE_DEPENDENCY,
            "typed_plan_source": typed,
            "source_plan_id": plan_id,
            "partial_candidate_id": plan["partial_candidate_id"],
            "current_quotient_graph_id": plan["quotient_graph_id"],
            "exact_legal_action_keys_sha256": _sha(list(legal)),
            "source_compiled_program_plan_id": plan[
                "source_compiled_factor_program_plan_id"
            ],
            "source_successor_state_id": plan["source_successor_state_id"],
            "current_successor_state_id": plan["current_successor_state_id"],
            "terminal_projection_rule_sha256": plan[
                "terminal_projection_rule_sha256"
            ],
            "exact_compiled_state_change_invalidates_program_memo": True,
            "dependency_projection_is_ordering_not_safety_authority": True,
            "query_local_exact_overlay_remains_only_safety_authority": True,
        }
    expected = {
        **payload,
        "dependency_projection_id": domains.extension_content_id_v174(
            domains.CONSTRUCTION_K7_DEPENDENCY_PROJECTION_V174_DOMAIN, payload
        ),
    }
    if canonical_json_bytes(expected) != canonical_json_bytes(projection):
        _fail("V174 independent dependency projection reconstruction changed")
    return expected


def _expected_issuance(wrapper, plan, projection, ordinal):
    plan_id = _plan_id(plan)
    legal = plan["exact_legal_action_keys_at_initial_state"]
    wrapper_bytes = canonical_json_bytes(wrapper)
    plan_bytes = canonical_json_bytes(plan)
    payload = {
        "schema": "acfqp.online_dependent_abstract_plan_issuance_receipt.v174",
        "issuance_ordinal": ordinal,
        "plan_schema": plan["schema"],
        "planning_source": plan["planning_source"],
        "typed_plan_source": TAXONOMY[(plan["schema"], plan["planning_source"])],
        "source_plan_id": plan_id,
        "source_plan_wrapper_sha256": hashlib.sha256(wrapper_bytes).hexdigest(),
        "raw_state_sha256": _sha(wrapper["raw_state"]),
        "exact_legal_action_keys": legal,
        "exact_legal_action_keys_sha256": _sha(legal),
        "legality_support_source": plan["legality_support_source"],
        "legality_failure_index": plan["legality_failure_index"],
        "initial_action_key": plan["initial_action_key"],
        "dependency_kind": projection["dependency_kind"],
        "dependency_projection_id": projection["dependency_projection_id"],
        "delegate_plan_sha256_before_receipt": hashlib.sha256(plan_bytes).hexdigest(),
        "receipt_issued_before_orderer_return": True,
        "caller_has_not_received_plan_at_receipt_issuance": True,
        "delegate_plan_returned_byte_exact": True,
        "receipt_drives_future_cache_authorization": True,
        "receipt_changes_selected_action_order": False,
        "receipt_is_model_or_safety_authority": False,
        "query_local_exact_overlay_remains_only_safety_authority": True,
    }
    return {
        **payload,
        "online_plan_issuance_receipt_id": domains.extension_content_id_v174(
            domains.CONSTRUCTION_K7_ONLINE_PLAN_ISSUANCE_V174_DOMAIN, payload
        ),
    }


def _transition_expected(
    previous_model,
    current_model,
    rules,
    active,
    dependencies,
    projection_ids,
    graph_events,
):
    same = previous_model["quotient_graph_id"] == current_model["quotient_graph_id"]
    if same:
        changed = ()
        changed_rows = []
        diff_checks = 0
        invalidated = set()
    else:
        before = _adjacency(previous_model)
        after = _adjacency(current_model)
        states = tuple(sorted(set(before) | set(after)))
        changed = tuple(
            state for state in states if before.get(state, ()) != after.get(state, ())
        )
        changed_rows = [
            {
                "projected_state": list(state),
                "previous_outgoing_edges": [
                    {"action_key": key, "projected_post": list(post)}
                    for key, post in before.get(state, ())
                ],
                "current_outgoing_edges": [
                    {"action_key": key, "projected_post": list(post)}
                    for key, post in after.get(state, ())
                ],
            }
            for state in changed
        ]
        diff_checks = sum(
            1 + len(before.get(state, ())) + len(after.get(state, ()))
            for state in states
        ) + 2 * len(rules)
        changed_set = set(changed)
        invalidated = {
            identity
            for identity in active
            if {
                tuple(row["projected_state"])
                for row in dependencies[identity]["ordered_bfs_dependency_rows"]
            }
            & changed_set
        }
    retained = set(active) - invalidated
    affected_receipts = sorted(
        receipt["online_plan_issuance_receipt_id"]
        for receipt, dependency_id in graph_events
        if dependency_id in invalidated
    )
    retained_receipts = sorted(
        receipt["online_plan_issuance_receipt_id"]
        for receipt, dependency_id in graph_events
        if dependency_id in retained
    )
    payload = {
        "schema": "acfqp.receipt_driven_model_epoch_transition.v174",
        "previous_quotient_graph_id": previous_model["quotient_graph_id"],
        "current_quotient_graph_id": current_model["quotient_graph_id"],
        "quotient_graph_identity_equal": same,
        "identity_short_circuit_applied": same,
        "previous_terminal_projection_rule": [dict(row) for row in rules],
        "current_terminal_projection_rule": [dict(row) for row in rules],
        "terminal_projection_rule_changed": False,
        "changed_projected_state_rows": changed_rows,
        "changed_projected_state_count": len(changed_rows),
        "cache_entry_ids_before_transition": sorted(active),
        "dependency_projection_ids_by_dependency_receipt_id": {
            identity: sorted(projection_ids[identity]) for identity in sorted(active)
        },
        "invalidated_dependency_receipt_ids": sorted(invalidated),
        "retained_dependency_receipt_ids": sorted(retained),
        "invalidated_online_plan_issuance_receipt_ids": affected_receipts,
        "retained_online_plan_issuance_receipt_ids": retained_receipts,
        "model_epoch_identity_checks": 1,
        "full_model_epoch_diff_checks": diff_checks,
        "reverse_dependency_index_lookups": len(changed),
        "receipt_dependency_projection_checks": sum(
            len(dependencies[identity]["ordered_bfs_dependency_rows"])
            for identity in active
        ),
        "same_content_address_skips_full_graph_and_dependency_scan": same,
        "changed_content_address_uses_exact_declared_dependency_delta": not same,
        "receipt_dependency_projection_drove_invalidation": True,
        "reverse_index_used_only_as_matched_consistency_control": True,
        "unaffected_dependency_receipts_retained_without_per_hit_rescan": True,
        "epoch_transition_is_ordering_evidence_not_safety_authority": True,
    }
    receipt = {
        **payload,
        "epoch_transition_receipt_id": domains.extension_content_id_v174(
            domains.CONSTRUCTION_K7_EPOCH_TRANSITION_V174_DOMAIN, payload
        ),
    }
    return receipt, invalidated, retained


def _program_expected(previous_state, current_state, direct_events):
    keys = set()
    source_plan_ids = []
    receipt_ids = []
    for wrapper, receipt in direct_events:
        key = (
            tuple(wrapper["raw_state"]),
            tuple(receipt["exact_legal_action_keys"]),
        )
        if key in keys:
            _fail("V174 independent program cache key is not unique in frozen cohort")
        keys.add(key)
        source_plan_ids.append(receipt["source_plan_id"])
        receipt_ids.append(receipt["online_plan_issuance_receipt_id"])
    payload = {
        "schema": "acfqp.receipt_driven_program_cache_invalidation.v174",
        "previous_successor_state_id": previous_state,
        "current_successor_state_id": current_state,
        "compiled_program_cache_entry_count_before": len(keys),
        "invalidated_source_plan_ids": sorted(source_plan_ids),
        "authorizing_online_plan_issuance_receipt_ids": sorted(receipt_ids),
        "program_cache_entry_count_after": 0,
        "exact_declared_successor_state_changed": True,
        "receipt_dependency_projection_drove_invalidation": True,
        "invalidation_is_cache_maintenance_not_safety_authority": True,
    }
    return {
        **payload,
        "program_invalidation_receipt_id": domains.extension_content_id_v174(
            domains.CONSTRUCTION_K7_PROGRAM_INVALIDATION_V174_DOMAIN, payload
        ),
    }


_EPISODE_OUTCOME_KEYS = (
    "episode_index",
    "family",
    "seed",
    "success",
    "action_keys",
    "execution_steps",
    "outcome_tape_sha256",
    "raw_incremental_transition_rows",
    "failed_certificates",
    "local_distinctions",
    "queried_state_action_count",
    "incremental_certificate_local_ground_support_labels",
    "paid_certificate_labels_cumulative",
    "total_target_ground_support_labels",
)


def _operational_projection(sequence):
    return {
        "family": sequence["family"],
        "seed": sequence["seed"],
        "episode_indices": sequence["episode_indices"],
        "execution_step_count": sequence["execution_step_count"],
        "lifetime_target_ground_support_labels": sequence[
            "lifetime_target_ground_support_labels"
        ],
        "persistent_exact_overlay_rows": sequence["persistent_exact_overlay_rows"],
        "persistent_exact_overlay_sha256": sequence[
            "persistent_exact_overlay_sha256"
        ],
        "quotient_models_before_each_episode": sequence[
            "quotient_models_before_each_episode"
        ],
        "quotient_models_after_each_episode": sequence[
            "quotient_models_after_each_episode"
        ],
        "episodes": [
            {key: episode[key] for key in _EPISODE_OUTCOME_KEYS}
            for episode in sequence["episodes"]
        ],
    }


def _verify_sequence(sequence, replayed):
    payload = {key: value for key, value in sequence.items() if key != "sequence_id"}
    if sequence.get("sequence_id") != domains.extension_content_id_v174(
        domains.CONSTRUCTION_K7_SEQUENCE_V174_DOMAIN, payload
    ):
        _fail("V174 independent sequence identity changed")
    if canonical_json_bytes(_operational_projection(sequence)) != canonical_json_bytes(
        _operational_projection(replayed)
    ):
        _fail("V174 independent target outcome reexecution changed")
    projections = {
        row["dependency_projection_id"]: row
        for row in sequence["online_dependency_projections"]
    }
    if len(projections) != len(sequence["online_dependency_projections"]):
        _fail("V174 independent dependency projection identity collision")
    models = _models_by_id(sequence)
    receipts = sequence["online_plan_issuance_receipts"]
    if len(receipts) != sum(
        len(episode["abstract_plan_receipts"]) for episode in sequence["episodes"]
    ):
        _fail("V174 independent plan/receipt cardinality changed")
    active = set()
    dependencies = {}
    projection_ids = defaultdict(set)
    chains = defaultdict(list)
    graph_events = []
    expected_receipts = []
    expected_transitions = []
    expected_program = []
    direct_events = []
    ordinal = 0
    program_state = sequence["episodes"][0][
        "standalone_model_state_id_before_episode"
    ]
    transition_rows = sequence["receipt_driven_model_epoch_transition_receipts"]
    for episode_offset, episode in enumerate(sequence["episodes"]):
        state_before = episode["standalone_model_state_id_before_episode"]
        if state_before != program_state:
            expected_program.append(
                _program_expected(program_state, state_before, direct_events)
            )
            direct_events = []
            program_state = state_before
        for wrapper in episode["abstract_plan_receipts"]:
            receipt = receipts[ordinal]
            plan = wrapper["abstract_plan"]
            projection = projections.get(receipt.get("dependency_projection_id"))
            if projection is None:
                _fail("V174 independent issuance lacks dependency projection")
            expected_projection = _expected_projection(
                plan,
                wrapper,
                projection,
                models,
                state_before,
                chains,
            )
            expected_receipt = _expected_issuance(
                wrapper, plan, expected_projection, ordinal
            )
            if canonical_json_bytes(expected_receipt) != canonical_json_bytes(receipt):
                _fail("V174 independent online issuance reconstruction changed")
            expected_receipts.append(expected_receipt)
            typed = expected_receipt["typed_plan_source"]
            if typed in {
                "OBSERVATION_DERIVED_QUOTIENT_ORDER",
                "DEPENDENCY_REVALIDATED_QUOTIENT_REUSE",
            }:
                dependency = _graph_dependency_for_plan(plan, projection, models)
                identity = dependency["dependency_receipt_id"]
                prior_dependency = dependencies.get(identity)
                if prior_dependency is not None and canonical_json_bytes(
                    prior_dependency
                ) != canonical_json_bytes(dependency):
                    _fail("V174 independent graph dependency identity collision")
                dependencies[identity] = dependency
                projection_ids[identity].add(projection["dependency_projection_id"])
                if typed == "OBSERVATION_DERIVED_QUOTIENT_ORDER":
                    active.add(identity)
                    chains.setdefault(identity, [])
                elif identity not in active:
                    _fail("V174 independent revalidated dependency is not live")
                graph_events.append((expected_receipt, identity))
            elif typed == "DIRECT_COMPILED_PROGRAM_ORDER":
                direct_events.append((wrapper, expected_receipt))
            ordinal += 1
        if episode_offset < len(sequence["episodes"]) - 1:
            if not active:
                _fail("V174 independent transition has no live graph dependency")
            rules_set = {
                canonical_json_bytes(dependencies[identity]["terminal_projection_rule"])
                for identity in active
            }
            if len(rules_set) != 1:
                _fail("V174 independent live terminal rules are ambiguous")
            rules = dependencies[next(iter(active))]["terminal_projection_rule"]
            expected, invalidated, retained = _transition_expected(
                sequence["quotient_models_before_each_episode"][episode_offset],
                sequence["quotient_models_after_each_episode"][episode_offset],
                rules,
                active,
                dependencies,
                projection_ids,
                graph_events,
            )
            actual = transition_rows[episode_offset]
            if canonical_json_bytes(expected) != canonical_json_bytes(actual):
                _fail("V174 independent minimal invalidation reconstruction changed")
            expected_transitions.append(expected)
            for identity in retained:
                chains[identity].append(expected)
            for identity in invalidated:
                active.remove(identity)
                chains.pop(identity, None)
    if ordinal != len(receipts) or len(transition_rows) != len(expected_transitions):
        _fail("V174 independent lifecycle ordinal changed")
    if canonical_json_bytes(expected_program) != canonical_json_bytes(
        sequence["receipt_driven_program_cache_invalidation_receipts"]
    ):
        _fail("V174 independent program invalidation reconstruction changed")
    joins = []
    index = {}
    cursor = 0
    for episode in sequence["episodes"]:
        for wrapper in episode["abstract_plan_receipts"]:
            key = (episode["episode_index"], canonical_json_bytes(wrapper))
            if key in index:
                _fail("V174 independent issuance wrapper identity is ambiguous")
            index[key] = expected_receipts[cursor]
            cursor += 1
    for execution in sequence["all_actual_legality_conditioned_execution_receipts"]:
        issuance = index.get(
            (
                execution["episode_index"],
                canonical_json_bytes(execution["quotient_plan_receipt"]),
            )
        )
        if issuance is None:
            _fail("V174 independent execution lacks prior issuance")
        source_payload = {
            key: value
            for key, value in execution.items()
            if key != "actual_dependency_revalidated_execution_receipt_id"
        }
        source_id = domains_v109.extension_content_id_v109(
            domains_v109.CONSTRUCTION_K7_DEPENDENCY_REVALIDATED_QUOTIENT_EXECUTION_RECEIPT_V109_DOMAIN,
            source_payload,
        )
        payload = {
            "schema": "acfqp.online_dependent_plan_execution_join.v174",
            "source_sequence_id": sequence["source_v154_shape_sequence_id"],
            "execution_join_ordinal": len(joins),
            "episode_index": execution["episode_index"],
            "decision_index": execution["decision_index"],
            "source_v109_execution_receipt_id": source_id,
            "online_plan_issuance_receipt_id": issuance[
                "online_plan_issuance_receipt_id"
            ],
            "dependency_projection_id": issuance["dependency_projection_id"],
            "typed_plan_source": issuance["typed_plan_source"],
            "chosen_action_key": execution["chosen_action_key"],
            "quotient_proposed_action_key": execution["quotient_proposed_action_key"],
            "chosen_action_matches_admitted_quotient_proposal": execution[
                "chosen_action_matches_admitted_quotient_proposal"
            ],
            "receipt_was_issued_before_plan_return": True,
            "receipt_dependency_authorized_cache_path": True,
            "receipt_is_model_or_safety_authority": False,
            "query_local_exact_overlay_remains_only_safety_authority": True,
        }
        joins.append(
            {
                **payload,
                "online_execution_join_receipt_id": domains.extension_content_id_v174(
                    domains.CONSTRUCTION_K7_ONLINE_EXECUTION_JOIN_V174_DOMAIN,
                    payload,
                ),
            }
        )
    if canonical_json_bytes(joins) != canonical_json_bytes(
        sequence["online_execution_join_receipts"]
    ):
        _fail("V174 independent execution join reconstruction changed")
    histogram = {
        source: sum(row["typed_plan_source"] == source for row in expected_receipts)
        for source in TAXONOMY.values()
    }
    invalidations = sum(
        len(row["invalidated_dependency_receipt_ids"])
        for row in expected_transitions
    )
    retentions = sum(
        len(row["retained_dependency_receipt_ids"])
        for row in expected_transitions
    )
    program_invalidations = sum(
        row["compiled_program_cache_entry_count_before"] for row in expected_program
    )
    incremental = histogram["DEPENDENCY_REVALIDATED_QUOTIENT_REUSE"]
    if not (
        sequence["online_plan_issuance_receipt_count"] == len(expected_receipts)
        and sequence["online_execution_join_receipt_count"] == len(joins)
        and sequence["online_typed_plan_source_histogram"] == histogram
        and sequence["receipt_driven_graph_dependency_invalidation_count"]
        == invalidations
        and sequence["receipt_driven_graph_dependency_retention_count"] == retentions
        and sequence["receipt_driven_compiled_program_invalidation_count"]
        == program_invalidations
        and sequence["incrementally_revalidated_plan_receipt_count"] == incremental
        and sequence["every_abstract_plan_receipt_issued_before_orderer_return"] is True
        and sequence["every_executed_action_joins_prior_online_receipt"] is True
        and sequence[
            "every_live_graph_cache_entry_has_prior_online_dependency_projection"
        ]
        is True
        and sequence["only_receipt_declared_dependencies_drive_graph_invalidation"]
        is True
        and sequence[
            "unaffected_graph_dependencies_reauthorized_without_per_hit_rescan"
        ]
        is True
        and sequence[
            "compiled_program_memo_invalidated_only_on_exact_successor_state_change"
        ]
        is True
        and sequence[
            "incremental_revalidation_chain_issued_before_reused_plan_return"
        ]
        is True
        and sequence["receipt_dependency_lifecycle_changes_selected_action_order"]
        is False
        and sequence["receipt_dependency_lifecycle_is_model_or_safety_authority"]
        is False
        and sequence["query_local_exact_overlay_remains_only_safety_authority"]
        is True
    ):
        _fail("V174 independent sequence accounting or claim boundary changed")
    return {
        "histogram": histogram,
        "issuance": len(expected_receipts),
        "joins": len(joins),
        "graph_invalidations": invalidations,
        "graph_retentions": retentions,
        "program_invalidations": program_invalidations,
        "incremental": incremental,
    }


def _replay(args):
    config, family, seed, bank_raw, verification_raw, classifier_raw = args
    return base._BASE_V168(  # noqa: SLF001
        config,
        family=family,
        seed=seed,
        episode_indices=EPISODES,
        bank_raw=bank_raw,
        verification_raw=verification_raw,
        classifier_receipt_raw=classifier_raw,
    )


def verify_receipt_driven_invalidation_campaign_v174(
    preregistration_raw: bytes,
    campaign_raw: bytes,
    classifier_raw: bytes,
    bank_raw: bytes,
    bank_verification_raw: bytes,
):
    preregistration = _frozen(
        preregistration_raw,
        count=PREREGISTRATION_BYTE_COUNT,
        digest=PREREGISTRATION_SHA256,
        identity_key="preregistration_id",
        identity=PREREGISTRATION_ID,
        name="preregistration",
    )
    campaign = _frozen(
        campaign_raw,
        count=CAMPAIGN_BYTE_COUNT,
        digest=CAMPAIGN_SHA256,
        identity_key="campaign_id",
        identity=CAMPAIGN_ID,
        name="campaign",
    )
    campaign_payload = {
        key: value for key, value in campaign.items() if key != "campaign_id"
    }
    if not (
        campaign["campaign_id"]
        == domains.extension_content_id_v174(
            domains.CONSTRUCTION_K7_CAMPAIGN_V174_DOMAIN, campaign_payload
        )
        and campaign["preregistration_id"] == preregistration["preregistration_id"]
        and campaign["frozen_v173r1_campaign_id"] == V173R1_CAMPAIGN_ID
        and campaign["frozen_v173r1_verification_id"] == V173R1_VERIFICATION_ID
        and preregistration["frozen_predecessors"][0]["campaign_id"]
        == V173R1_CAMPAIGN_ID
        and preregistration["frozen_predecessors"][1]["verification_id"]
        == V173R1_VERIFICATION_ID
        and preregistration["target_worker_count"] == TARGET_WORKERS
        and preregistration["target_episode_indices"] == list(EPISODES)
    ):
        _fail("V174 independent campaign ancestry changed")
    config = base._config()  # noqa: SLF001
    args = [
        (config, family, seed, bank_raw, bank_verification_raw, classifier_raw)
        for family, seed, _ in TARGETS
    ]
    with ProcessPoolExecutor(max_workers=TARGET_WORKERS) as executor:
        replayed = list(executor.map(_replay, args))
    rows = campaign["target_occurrences"]
    if len(rows) != len(replayed) or len(rows) != len(TARGETS):
        _fail("V174 independent target cardinality changed")
    histogram = {source: 0 for source in TAXONOMY.values()}
    totals = {
        "issuance": 0,
        "joins": 0,
        "graph_invalidations": 0,
        "graph_retentions": 0,
        "program_invalidations": 0,
        "incremental": 0,
    }
    factor_avoided = query_avoided = 0
    occurrence_ids = []
    roles = set()
    for (family, seed, role), replay, row in zip(
        TARGETS, replayed, rows, strict=True
    ):
        if not (
            row["target_family"] == family
            and row["seed"] == seed
            and row["episode_indices"] == list(EPISODES)
            and row["registered_dependency_role"] == role
            and canonical_json_bytes(row["progressive_prior_acquisition"])
            == canonical_json_bytes(replay["progressive_prior_acquisition"])
            and canonical_json_bytes(row["progressive_strict_acquisition"])
            == canonical_json_bytes(replay["progressive_strict_acquisition"])
            and row["factor_prior_sample_reduction_within_progressive_policy"]
            == replay["factor_prior_sample_reduction_within_progressive_policy"]
            and row["query_policy_sample_reduction_vs_legacy_path_first"]
            == replay["query_policy_sample_reduction_vs_legacy_path_first"]
        ):
            _fail("V174 independent occurrence target replay changed")
        prior_summary = _verify_sequence(
            row["progressive_prior_sequence"], replay["progressive_prior_sequence"]
        )
        strict_summary = _verify_sequence(
            row["progressive_strict_sequence"], replay["progressive_strict_sequence"]
        )
        summary = {
            key: prior_summary[key] + strict_summary[key]
            for key in prior_summary
            if key != "histogram"
        }
        row_histogram = {
            source: prior_summary["histogram"][source]
            + strict_summary["histogram"][source]
            for source in histogram
        }
        row_payload = {
            key: value for key, value in row.items() if key != "occurrence_id"
        }
        if not (
            row["occurrence_id"]
            == domains.extension_content_id_v174(
                domains.CONSTRUCTION_K7_OCCURRENCE_V174_DOMAIN, row_payload
            )
            and row["online_typed_plan_source_histogram"] == row_histogram
            and row["online_plan_issuance_receipt_count"] == summary["issuance"]
            and row["online_execution_join_receipt_count"] == summary["joins"]
            and row["receipt_driven_graph_dependency_invalidation_count"]
            == summary["graph_invalidations"]
            and row["receipt_driven_graph_dependency_retention_count"]
            == summary["graph_retentions"]
            and row["receipt_driven_compiled_program_invalidation_count"]
            == summary["program_invalidations"]
            and row["incrementally_revalidated_plan_receipt_count"]
            == summary["incremental"]
            and row["registered_gate"]["passed"] is True
            and row["receipt_dependency_lifecycle_changes_selected_action_order"]
            is False
            and row["receipt_dependency_lifecycle_is_model_or_safety_authority"]
            is False
        ):
            _fail("V174 independent occurrence accounting changed")
        for source in histogram:
            histogram[source] += row_histogram[source]
        for key in totals:
            totals[key] += summary[key]
        factor_avoided += row[
            "factor_prior_sample_reduction_within_progressive_policy"
        ]
        query_avoided += row["query_policy_sample_reduction_vs_legacy_path_first"]
        occurrence_ids.append(row["occurrence_id"])
        roles.add(role)
    accounting = campaign["accounting"]
    if not (
        campaign["target_occurrence_ids"] == occurrence_ids
        and campaign["online_typed_plan_source_histogram"] == histogram
        and accounting["online_plan_issuance_receipt_count"] == totals["issuance"]
        and accounting["online_execution_join_receipt_count"] == totals["joins"]
        and accounting["graph_dependency_invalidations"]
        == totals["graph_invalidations"]
        and accounting["graph_dependency_retentions"] == totals["graph_retentions"]
        and accounting["compiled_program_invalidations"]
        == totals["program_invalidations"]
        and accounting["incrementally_revalidated_plan_receipts"]
        == totals["incremental"]
        and accounting["factor_prior_labels_avoided"] == factor_avoided
        and accounting["query_policy_labels_avoided"] == query_avoided
        and roles
        == {
            "GRAPH_AND_COMPILED_DEPENDENCY_INVALIDATION",
            "UNAFFECTED_DEPENDENCY_RETENTION_AND_REVALIDATION",
        }
        and all(histogram[source] > 0 for source in histogram)
        and totals["graph_invalidations"] > 0
        and totals["graph_retentions"] > 0
        and totals["program_invalidations"] > 0
        and totals["incremental"] > 0
        and factor_avoided > 0
        and query_avoided >= 0
        and campaign["registered_gate"]["passed"] is True
        and campaign["receipt_driven_minimal_invalidation_observed"] is True
        and campaign["factor_prior_sample_tax_reduction_observed"] is True
        and campaign["receipt_dependency_lifecycle_changes_selected_action_order"]
        is False
        and campaign["receipt_dependency_lifecycle_is_model_or_safety_authority"]
        is False
        and campaign["query_local_exact_overlay_remains_only_safety_authority"]
        is True
        and campaign["complete_world_model_synthesized"] is False
        and campaign["arbitrary_unseen_domain_transfer_claimed"] is False
        and campaign["official_execution_allowed"] is False
        and campaign["official_scalar_cost"] is None
        and campaign["official_N_break_even"] is None
        and campaign["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
        and campaign["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
    ):
        _fail("V174 independent aggregate or claim boundary changed")
    verification_payload = {
        "schema": "acfqp.receipt_driven_invalidation_verification.v174",
        "preregistration_id": PREREGISTRATION_ID,
        "campaign_id": CAMPAIGN_ID,
        "preserved_v173r1_campaign_id": V173R1_CAMPAIGN_ID,
        "preserved_v173r1_verification_id": V173R1_VERIFICATION_ID,
        "verified_target_families": [family for family, _, _ in TARGETS],
        "verified_target_seeds": [seed for _, seed, _ in TARGETS],
        "verified_occurrence_ids": occurrence_ids,
        "verified_online_plan_issuance_receipt_count": totals["issuance"],
        "verified_online_execution_join_receipt_count": totals["joins"],
        "verified_online_typed_plan_source_histogram": histogram,
        "verified_graph_dependency_invalidations": totals["graph_invalidations"],
        "verified_graph_dependency_retentions": totals["graph_retentions"],
        "verified_compiled_program_invalidations": totals["program_invalidations"],
        "verified_incrementally_revalidated_plan_receipts": totals["incremental"],
        "verified_factor_prior_labels_avoided": factor_avoided,
        "verified_query_policy_labels_avoided": query_avoided,
        "producer_free_target_outcome_reexecution": True,
        "producer_free_dependency_projection_reconstruction": True,
        "producer_free_minimal_invalidation_reconstruction": True,
        "producer_free_unaffected_dependency_retention_reconstruction": True,
        "producer_free_program_invalidation_reconstruction": True,
        "producer_free_incremental_revalidation_chain_reconstruction": True,
        "producer_free_online_issuance_and_execution_join_reconstruction": True,
        "receipt_dependency_lifecycle_action_order_invariance_verified": True,
        "factor_prior_sample_tax_reduction_independently_verified": True,
        "receipt_dependency_lifecycle_is_model_or_safety_authority": False,
        "query_local_exact_overlay_remains_only_safety_authority": True,
        "complete_world_model_claimed": False,
        "arbitrary_unseen_domain_transfer_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    document = {
        **verification_payload,
        "verification_id": domains.extension_content_id_v174(
            domains.CONSTRUCTION_K7_VERIFICATION_V174_DOMAIN,
            verification_payload,
        ),
    }
    raw = canonical_json_bytes(document)
    if VERIFICATION_ID != "0" * 64 and not (
        document["verification_id"] == VERIFICATION_ID
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    ):
        _fail("V174 frozen independent verification changed")
    return document


__all__ = (
    "VERIFICATION_ID",
    "verify_receipt_driven_invalidation_campaign_v174",
)
