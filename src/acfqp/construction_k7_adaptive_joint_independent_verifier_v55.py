"""Producer/core-free semantic verification of the frozen V55 campaign."""

from __future__ import annotations

from collections import deque
from concurrent.futures import ProcessPoolExecutor
from functools import lru_cache
import hashlib
import heapq
import random
from typing import Any, Iterator, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v55 as domains_v55
from acfqp.domains.stochastic_balanced_batch_refinement import (
    generate_stochastic_balanced_batch_refinement,
)
from acfqp.domains.stochastic_batch_refinement import (
    BatchRefinementAction,
    BatchRefinementState,
    BatchRefinementStatus,
    select_seeded_batch_refinement_outcome_v1,
)
from acfqp.generic_adaptive_joint_factor_residual_synthesizer_v10 import (
    adaptive_stop_update_v10,
    exact_candidate_replay_v10,
    synthesize_adaptive_joint_candidate_v10,
)
from acfqp.generic_atomic_expression_world_model_v4 import (
    FlatRawActionV4,
    FlatRawTransitionV4,
)
from acfqp.generic_joint_factor_residual_world_model_v9 import (
    synthesize_joint_factor_residual_world_model_v9,
)
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_LAYOUT_V54_DOMAIN,
    CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_MODEL_V54_DOMAIN,
    CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_PROGRAM_V54_DOMAIN,
    CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_SUPPORT_V54_DOMAIN,
    canonical_json_bytes,
    loads_canonical_json,
)


EXPECTED_CAMPAIGN_ID = "ea85860f499ac631a7f3e6b306974be2a2d7c9de88cde3cf492380ebd59ec589"
EXPECTED_CAMPAIGN_BYTE_COUNT = 2_027_913
EXPECTED_CAMPAIGN_SHA256 = "38363f222d1b4047e4ce6f2fd5e6c4aea595709b473e9aed44d90fd54245128a"
VERIFICATION_ID = "ec6fe8ee01a663030ffdd146613d1f4231000f27bae0773f47c15b6d398fd1f6"
EXPECTED_CANONICAL_BYTE_COUNT = 1_470
EXPECTED_CANONICAL_SHA256 = "4f09b2f96c970465a531e80e14827ae228ccd45460a297c893f43542229905ed"

_TOKENS = {"A": 9_001, "F": 9_007, "S": 9_011}
_SEEDS = tuple(range(551_101, 551_229))
_PLANNING_COUNT = 8
_FACTOR_LIBRARY_LABELS = 370
_LIBRARY = {
    "factor_library_id": "46aa60cc33ca61238612342ed9fe73e91cfa7bfb639b4a8f0afa29c491428162",
    "cross_schema_subprograms": [
        {
            "signature_sha256": signature,
            "source_schema_pairs": [[7, 5], [9, 6]],
        }
        for signature in (
            "012651c74d7a2c07190817603bc2aeb9a069c8c1dc5a3f9d828518a03aeb367e",
            "16fcf756e4d606282a0f656f4ab960069273f8f895d8a0abcf7f0d530c07a072",
            "c2fe69a54e58afa7f6c68992e4ea16eb6aa5800b6543d9c1022729dc6ebc52b5",
        )
    ],
}
_GENERIC_DOMAINS = {
    "layout": CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_LAYOUT_V54_DOMAIN,
    "program": CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_PROGRAM_V54_DOMAIN,
    "support": CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_SUPPORT_V54_DOMAIN,
    "model": CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_MODEL_V54_DOMAIN,
}
_DOMAINS = {
    "candidate": domains_v55.CONSTRUCTION_K7_ADAPTIVE_JOINT_CANDIDATE_V55_DOMAIN,
    "acquisition": domains_v55.CONSTRUCTION_K7_ADAPTIVE_JOINT_ACQUISITION_V55_DOMAIN,
    "failed_certificate": domains_v55.CONSTRUCTION_K7_ADAPTIVE_JOINT_FAILED_CERTIFICATE_V55_DOMAIN,
    "distinction": domains_v55.CONSTRUCTION_K7_ADAPTIVE_JOINT_LOCAL_DISTINCTION_V55_DOMAIN,
    "episode": domains_v55.CONSTRUCTION_K7_ADAPTIVE_JOINT_EPISODE_V55_DOMAIN,
    "validation": domains_v55.CONSTRUCTION_K7_ADAPTIVE_JOINT_ISOLATED_VALIDATION_V55_DOMAIN,
    "ood": domains_v55.CONSTRUCTION_K7_ADAPTIVE_JOINT_OOD_REJECTION_V55_DOMAIN,
    "sample_tax": domains_v55.CONSTRUCTION_K7_ADAPTIVE_JOINT_SAMPLE_TAX_V55_DOMAIN,
    "campaign": domains_v55.CONSTRUCTION_K7_ADAPTIVE_JOINT_CAMPAIGN_V55_DOMAIN,
    "verification": domains_v55.CONSTRUCTION_K7_ADAPTIVE_JOINT_VERIFICATION_V55_DOMAIN,
}


class ConstructionK7AdaptiveJointIndependentVerifierV55Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7AdaptiveJointIndependentVerifierV55Error(message)


def _interface(seed: int, kernel: Any):
    state_order = list(range(6))
    action_order = list(range(5))
    random.Random(seed ^ 0x55A17).shuffle(state_order)
    random.Random(seed ^ 0x55B29).shuffle(action_order)
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


def _batch(kernel, catalogue, encode, state, action, index):
    legal = tuple(kernel.actions(state))
    rows = []
    for offset, outcome in enumerate(kernel.step(state, action)):
        successor = outcome.next_state
        legal_after = tuple(kernel.actions(successor))
        rows.append(
            FlatRawTransitionV4(
                0,
                index + offset,
                encode(state),
                tuple(row.rule for row in legal),
                catalogue[action.rule],
                encode(successor),
                tuple(row.rule for row in legal_after),
                None
                if legal_after
                else successor.status is BatchRefinementStatus.SUCCESS,
            )
        )
    return tuple(rows)


def _frontier(kernel, catalogue, encode) -> Iterator[tuple[FlatRawTransitionV4, ...]]:
    initial = kernel.initial_distribution()[0][1]
    heap = [(0, 0, initial)]
    seen = {initial}
    ordinal = 1
    pending = deque()
    index = 0
    while heap or pending:
        if not pending:
            negative_depth, _rank, state = heapq.heappop(heap)
            depth = -negative_depth
            legal = tuple(kernel.actions(state))
            pending.extend((state, action, depth) for action in legal)
        state, action, depth = pending.popleft()
        rows = _batch(kernel, catalogue, encode, state, action, index)
        index += len(rows)
        for row, outcome in zip(rows, kernel.step(state, action), strict=True):
            successor = outcome.next_state
            if row.terminal_acceptance_after is None and successor not in seen:
                seen.add(successor)
                heapq.heappush(heap, (-(depth + 1), ordinal, successor))
                ordinal += 1
        yield rows


def _raw_sha(rows) -> str:
    return hashlib.sha256(
        canonical_json_bytes([row.to_document() for row in rows])
    ).hexdigest()


def _candidate(rows, catalogue, labels, cache):
    key = (labels, _raw_sha(rows))
    if key not in cache:
        cache[key] = synthesize_adaptive_joint_candidate_v10(
            rows,
            catalogue,
            _LIBRARY,
            support_label_count=labels,
            generic_domains=_GENERIC_DOMAINS,
            candidate_domain=_DOMAINS["candidate"],
            candidate_content_id=domains_v55.extension_content_id_v55,
            minimum_reusable_factor_count=3,
        )
    return cache[key]


def _acquire(seed, prior, kernel, catalogue, encode, cache):
    rows = []
    candidate = None
    issued = None
    resets = 0
    history = []
    stream = _frontier(kernel, catalogue, encode)
    for labels in range(1, 129):
        rows.extend(next(stream))
        if labels < 80:
            continue
        reason = "EXISTING_CANDIDATE_EXACT_REPLAY"
        replay = None
        if candidate is None:
            try:
                candidate = _candidate(tuple(rows), catalogue, labels, cache)
            except Exception:
                continue
            issued = labels
            reason = "FIRST_JOINT_CANDIDATE_SYNTHESIZED"
        else:
            replay = exact_candidate_replay_v10(candidate, tuple(rows), catalogue)
            if replay["exact"] is not True:
                candidate = _candidate(tuple(rows), catalogue, labels, cache)
                issued = labels
                resets += 1
                reason = "COUNTEREVIDENCE_TRIGGERED_FULL_JOINT_RESYNTHESIS"
        stop = adaptive_stop_update_v10(
            candidate,
            factor_prior_enabled=prior,
            confirming_support_labels=labels - issued,
            confirmation_block_size=4,
            factor_prior_weight=64,
            exact_likelihood_block_weight=64,
            stopping_weight=64,
            minimum_reusable_factor_count=3,
        )
        history.append(
            {
                "support_label_count": labels,
                "raw_transition_sha256": _raw_sha(tuple(rows)),
                "candidate_id": candidate.public_document["candidate_id"],
                "update_reason": reason,
                "exact_replay": replay,
                "stop_update": stop,
            }
        )
        if stop["stopped"]:
            arm = "ANONYMOUS_FACTOR_PRIOR_ON" if prior else "STRICT_NO_PRIOR"
            payload = {
                "schema": "acfqp.adaptive_joint_acquisition.v55",
                "seed": seed,
                "arm": arm,
                "factor_prior_enabled": prior,
                "ground_support_labels": labels,
                "raw_transition_count": len(rows),
                "raw_transition_sha256": _raw_sha(tuple(rows)),
                "candidate": dict(candidate.public_document),
                "candidate_issued_at_support_label": issued,
                "candidate_reset_count": resets,
                "stopping_history": history,
                "witness_blind_depth_first_frontier_policy": True,
                "generation_witness_accessed": False,
                "full_frontier_calibration_consumed": False,
                "same_synthesizer_query_order_exact_likelihood_and_stop_formula": True,
                "only_switched_variable": "ANONYMOUS_FACTOR_SIGNATURE_INITIAL_WEIGHT",
            }
            document = {
                **payload,
                "acquisition_id": domains_v55.extension_content_id_v55(
                    _DOMAINS["acquisition"], payload
                ),
            }
            return document, candidate, tuple(rows), labels
    _fail("independent V55 acquisition crossed its cap")


def _strict_actions(seed, kernel):
    state = kernel.initial_distribution()[0][1]
    cache = {}
    actions = []
    tapes = []
    decision = 0
    while state.status is BatchRefinementStatus.ACTIVE:
        choices = {}

        @lru_cache(maxsize=None)
        def solve(current):
            if current.status is BatchRefinementStatus.SUCCESS:
                return True
            if current.status is BatchRefinementStatus.FAILURE:
                return False
            for action in kernel.actions(current):
                key = (current, action.rule)
                if key not in cache:
                    cache[key] = tuple(
                        row.next_state for row in kernel.step(current, action)
                    )
                if all(solve(successor) for successor in cache[key]):
                    choices[current] = action.rule
                    return True
            return False

        if not solve(state):
            _fail("independent V55 strict planner failed")
        key = choices[state]
        outcome, tape = select_seeded_batch_refinement_outcome_v1(
            kernel.step(state, BatchRefinementAction(key)),
            seed=seed,
            episode_index=seed - _SEEDS[0],
            decision_index=decision,
        )
        state = outcome.next_state
        actions.append(key)
        tapes.append(tape)
        decision += 1
    return actions, tapes, state.status is BatchRefinementStatus.SUCCESS


def _verify_episode_document(document):
    payload = {key: value for key, value in document.items() if key != "episode_id"}
    if domains_v55.extension_content_id_v55(_DOMAINS["episode"], payload) != document.get("episode_id"):
        _fail("V55 episode content ID changed")


def _verify_occurrence(args):
    index, seed, prior_expected, no_prior_expected, common_expected, episodes, validation = args
    kernel, _ = generate_stochastic_balanced_batch_refinement(
        stage_count=9, unit_base=5, seed=seed
    )
    catalogue, encode = _interface(seed, kernel)
    cache = {}
    prior, prior_candidate, prior_rows, prior_labels = _acquire(
        seed, True, kernel, catalogue, encode, cache
    )
    no_prior, no_prior_candidate, no_prior_rows, no_prior_labels = _acquire(
        seed, False, kernel, catalogue, encode, cache
    )
    if prior != prior_expected or no_prior != no_prior_expected:
        _fail(f"producer-free V55 acquisition changed at seed {seed}")
    if tuple(no_prior_rows[: len(prior_rows)]) != prior_rows:
        _fail("V55 common raw prefix changed")
    if _raw_sha(prior_rows) != common_expected:
        _fail("V55 common-prefix hash changed")
    validation_labels = 0
    validation_support_mismatches = 0
    steps = 0
    local = {"ANONYMOUS_FACTOR_PRIOR_ON": 0, "STRICT_NO_PRIOR": 0}
    if index < _PLANNING_COUNT:
        strict_actions, strict_tapes, success = _strict_actions(seed, kernel)
        if not success:
            _fail("V55 independent strict replay failed")
        for arm in (
            "ANONYMOUS_FACTOR_PRIOR_ON",
            "STRICT_NO_PRIOR",
            "STRICT_EXACT_CONTEXT",
        ):
            row = episodes[arm]
            _verify_episode_document(row)
            if row["action_keys"] != strict_actions or row["outcome_tape_sha256"] != strict_tapes or row["success"] is not True:
                _fail(f"V55 held-out episode replay changed at seed {seed}")
            steps += row["execution_steps"]
            if arm in local:
                local[arm] = row["local_ground_support_labels"]
        full_batches = tuple(_frontier(kernel, catalogue, encode))
        full_rows = tuple(row for batch in full_batches for row in batch)
        arms = {
            "ANONYMOUS_FACTOR_PRIOR_ON": {
                **exact_candidate_replay_v10(
                    prior_candidate, full_rows, catalogue
                ),
                "candidate_id": prior_candidate.public_document["candidate_id"],
            },
            "STRICT_NO_PRIOR": {
                **exact_candidate_replay_v10(
                    no_prior_candidate, full_rows, catalogue
                ),
                "candidate_id": no_prior_candidate.public_document["candidate_id"],
            },
        }
        payload = {
            "schema": "acfqp.adaptive_joint_isolated_validation.v55",
            "seed": seed,
            "full_frontier_ground_support_labels": len(full_batches),
            "full_frontier_raw_transition_count": len(full_rows),
            "full_frontier_raw_transition_sha256": _raw_sha(full_rows),
            "arm_replay": arms,
            "validation_rows_consumed_for_acquisition": False,
            "validation_rows_consumed_for_binding": False,
            "validation_rows_consumed_for_planning": False,
            "honest_partial_dynamics_reported": True,
        }
        expected_validation = {
            **payload,
            "isolated_validation_id": domains_v55.extension_content_id_v55(
                _DOMAINS["validation"], payload
            ),
        }
        if expected_validation != validation:
            _fail(f"V55 isolated validation changed at seed {seed}")
        validation_labels = len(full_batches)
        validation_support_mismatches = sum(
            row["support_mismatch_count"] for row in arms.values()
        )
    return {
        "prior_labels": prior_labels,
        "no_prior_labels": no_prior_labels,
        "prior_resets": prior["candidate_reset_count"],
        "no_prior_resets": no_prior["candidate_reset_count"],
        "prior_local": local["ANONYMOUS_FACTOR_PRIOR_ON"],
        "no_prior_local": local["STRICT_NO_PRIOR"],
        "validation_labels": validation_labels,
        "validation_support_mismatches": validation_support_mismatches,
        "episode_steps_all_arms": steps,
    }


def _verify_content_rows(campaign):
    failures = {}
    for row in campaign["failed_certificates"]:
        payload = {
            key: value for key, value in row.items() if key != "failed_certificate_id"
        }
        identity = domains_v55.extension_content_id_v55(
            _DOMAINS["failed_certificate"], payload
        )
        if row.get("failed_certificate_id") != identity or identity in failures:
            _fail("V55 failed-certificate identity changed")
        if row.get("ground_query_performed_before_failure") is not False:
            _fail("V55 ground query preceded its certificate failure")
        failures[identity] = row
    distinctions = {}
    for row in campaign["local_distinctions"]:
        payload = {
            key: value for key, value in row.items() if key != "local_distinction_id"
        }
        identity = domains_v55.extension_content_id_v55(
            _DOMAINS["distinction"], payload
        )
        if row.get("local_distinction_id") != identity or identity in distinctions:
            _fail("V55 local-distinction identity changed")
        if row.get("failed_certificate_id") not in failures or row.get("query_after_failed_certificate") is not True:
            _fail("V55 local distinction escaped certificate-first recovery")
        distinctions[identity] = row
    if len(failures) != len(distinctions):
        _fail("V55 failure/distinction cardinality changed")
    return len(failures)


def _verify_sample_tax(campaign, results):
    prior_labels = sum(row["prior_labels"] for row in results)
    no_prior_labels = sum(row["no_prior_labels"] for row in results)
    prior_local = sum(row["prior_local"] for row in results)
    no_prior_local = sum(row["no_prior_local"] for row in results)
    curve = []
    prior_running = _FACTOR_LIBRARY_LABELS
    no_prior_running = 0
    break_even = None
    for index, row in enumerate(results, start=1):
        prior_running += row["prior_labels"]
        no_prior_running += row["no_prior_labels"]
        reduction = no_prior_running - prior_running
        curve.append(
            {
                "occurrence_count": index,
                "factor_prior_on_lifetime_labels": prior_running,
                "strict_no_prior_lifetime_labels": no_prior_running,
                "net_label_reduction": reduction,
            }
        )
        if break_even is None and reduction > 0:
            break_even = index
    online = (no_prior_labels + no_prior_local) - (prior_labels + prior_local)
    payload = {
        "schema": "acfqp.adaptive_joint_sample_tax.v55",
        "factor_library_labels_prior_on_only": _FACTOR_LIBRARY_LABELS,
        "factor_prior_on_acquisition_labels": prior_labels,
        "strict_no_prior_acquisition_labels": no_prior_labels,
        "incremental_acquisition_label_reduction": no_prior_labels - prior_labels,
        "factor_prior_on_local_recovery_labels": prior_local,
        "strict_no_prior_local_recovery_labels": no_prior_local,
        "online_label_reduction_including_local_recovery": online,
        "lifetime_label_reduction_after_factor_library_tax": online
        - _FACTOR_LIBRARY_LABELS,
        "diagnostic_break_even_occurrence_count": break_even,
        "prefix_curve": curve,
        "same_synthesizer_and_stopping_formula": True,
        "only_factor_prior_initial_weight_switched": True,
        "isolated_validation_labels_excluded_from_online_acquisition_and_reported_separately": True,
        "official_break_even_claimed": False,
    }
    expected = {
        **payload,
        "sample_tax_id": domains_v55.extension_content_id_v55(
            _DOMAINS["sample_tax"], payload
        ),
    }
    if campaign["sample_tax"] != expected:
        _fail("V55 sample-tax reconstruction changed")
    return expected


def _verify_ood(campaign):
    catalogue = tuple(
        FlatRawActionV4(index, (bit, 1))
        for index, bit in enumerate((1, 2, 4))
    )
    rows = []
    for mask in (0, 1, 2):
        for key, bit in enumerate((1, 2, 4)):
            successor = mask | bit
            status = "F" if successor & 4 else "S" if successor == 3 else "A"
            rows.append(
                FlatRawTransitionV4(
                    0,
                    len(rows),
                    (mask, _TOKENS["A"], 3, 4, 1),
                    (0, 1, 2),
                    catalogue[key],
                    (successor, _TOKENS[status], 3, 4, 1),
                    () if status != "A" else (0, 1, 2),
                    None if status == "A" else status == "S",
                )
            )
    model = synthesize_joint_factor_residual_world_model_v9(
        {0: tuple(rows)},
        {0: catalogue},
        _LIBRARY,
        layout_domain=_GENERIC_DOMAINS["layout"],
        program_domain=_GENERIC_DOMAINS["program"],
        support_domain=_GENERIC_DOMAINS["support"],
        factor_domain=_GENERIC_DOMAINS["model"],
        result_domain=_GENERIC_DOMAINS["model"],
        minimum_reusable_factor_count=3,
    )
    payload = {
        "schema": "acfqp.adaptive_joint_ood_rejection.v55",
        "joint_model_id": model["joint_model_id"],
        "factorable_reusable_count": model["factorable_reusable_count"],
        "minimum_reusable_factor_count": 3,
        "complete_ood_program_synthesized_from_raw_observations": True,
        "prior_transfer_attempted": False,
        "ood_outcome_execution_performed": False,
        "outcome": "STRICT_SIGNATURE_THRESHOLD_OOD_NO_TRANSFER",
    }
    expected = {
        **payload,
        "ood_rejection_id": domains_v55.extension_content_id_v55(
            _DOMAINS["ood"], payload
        ),
    }
    if campaign["ood_rejection"] != expected or model["transfer_admitted"] is not False:
        _fail("V55 OOD reconstruction changed")
    return model["factorable_reusable_count"]


def verify_adaptive_joint_campaign_bytes_v55(raw: bytes) -> dict[str, Any]:
    if type(raw) is not bytes or len(raw) != EXPECTED_CAMPAIGN_BYTE_COUNT or hashlib.sha256(raw).hexdigest() != EXPECTED_CAMPAIGN_SHA256:
        _fail("frozen V55 campaign bytes changed")
    campaign = loads_canonical_json(raw)
    if type(campaign) is not dict or campaign.get("campaign_id") != EXPECTED_CAMPAIGN_ID:
        _fail("frozen V55 campaign identity changed")
    payload = {key: value for key, value in campaign.items() if key != "campaign_id"}
    if domains_v55.extension_content_id_v55(_DOMAINS["campaign"], payload) != EXPECTED_CAMPAIGN_ID:
        _fail("V55 campaign content ID changed")
    if campaign.get("full_frontier_target_layout_calibration_consumed") is not False or campaign.get("shared_residual_scaffold_consumed") is not False or campaign.get("predeclared_reusable_factor_slots_consumed") is not False:
        _fail("V55 forbidden scaffold or full-frontier input changed")
    if campaign.get("official_execution_allowed") is not False or campaign.get("official_scalar_cost") is not None or campaign.get("official_N_break_even") is not None or campaign.get("WORKLOAD_ECONOMICS_GATE") != "NOT_RUN" or campaign.get("COUNTER_COMPLETENESS_GATE") != "NOT_RUN":
        _fail("V55 locked official gates changed")
    prior_rows = campaign["acquisitions"]["ANONYMOUS_FACTOR_PRIOR_ON"]
    no_prior_rows = campaign["acquisitions"]["STRICT_NO_PRIOR"]
    if len(prior_rows) != len(_SEEDS) or len(no_prior_rows) != len(_SEEDS):
        _fail("V55 acquisition occurrence count changed")
    episode_by_arm = {
        arm: {row["seed"]: row for row in campaign["episodes"][arm]}
        for arm in campaign["episodes"]
    }
    validation_by_seed = {
        row["seed"]: row for row in campaign["isolated_full_frontier_validations"]
    }
    arguments = []
    for index, seed in enumerate(_SEEDS):
        episodes = (
            {arm: episode_by_arm[arm][seed] for arm in episode_by_arm}
            if index < _PLANNING_COUNT
            else {}
        )
        arguments.append(
            (
                index,
                seed,
                prior_rows[index],
                no_prior_rows[index],
                campaign["common_prefix_sha256"][index],
                episodes,
                validation_by_seed.get(seed),
            )
        )
    with ProcessPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(_verify_occurrence, arguments))
    failure_count = _verify_content_rows(campaign)
    sample = _verify_sample_tax(campaign, results)
    ood_reusable = _verify_ood(campaign)
    return {
        "acquisition_occurrence_count": len(results),
        "factor_prior_on_acquisition_labels": sample[
            "factor_prior_on_acquisition_labels"
        ],
        "strict_no_prior_acquisition_labels": sample[
            "strict_no_prior_acquisition_labels"
        ],
        "incremental_acquisition_label_reduction": sample[
            "incremental_acquisition_label_reduction"
        ],
        "online_label_reduction_including_local_recovery": sample[
            "online_label_reduction_including_local_recovery"
        ],
        "lifetime_label_reduction_after_factor_library_tax": sample[
            "lifetime_label_reduction_after_factor_library_tax"
        ],
        "diagnostic_break_even_occurrence_count": sample[
            "diagnostic_break_even_occurrence_count"
        ],
        "planning_episode_count_all_arms": sum(
            len(rows) for rows in campaign["episodes"].values()
        ),
        "failed_certificate_count": failure_count,
        "isolated_validation_label_count": sum(
            row["validation_labels"] for row in results
        ),
        "isolated_validation_support_mismatch_count": sum(
            row["validation_support_mismatches"] for row in results
        ),
        "prior_candidate_reset_count": sum(row["prior_resets"] for row in results),
        "no_prior_candidate_reset_count": sum(
            row["no_prior_resets"] for row in results
        ),
        "ood_reusable_count": ood_reusable,
        "ood_transfer_admitted": False,
    }


def freeze_adaptive_joint_verification_v55(campaign_bytes: bytes) -> bytes:
    projection = verify_adaptive_joint_campaign_bytes_v55(campaign_bytes)
    payload = {
        "schema": "acfqp.adaptive_joint_independent_verification.v55",
        "campaign_id": EXPECTED_CAMPAIGN_ID,
        "campaign_byte_count": EXPECTED_CAMPAIGN_BYTE_COUNT,
        "campaign_sha256": EXPECTED_CAMPAIGN_SHA256,
        "producer_module_imported": False,
        "campaign_core_module_imported": False,
        "raw_acquisition_sequences_reconstructed": True,
        "joint_candidates_and_stop_points_reconstructed": True,
        "matched_plans_and_outcome_tapes_replayed": True,
        "isolated_full_frontier_validations_reconstructed": True,
        "sample_tax_and_ood_reconstructed": True,
        "scientific_projection_exact": True,
        "projection": projection,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    document = {
        **payload,
        "verification_id": domains_v55.extension_content_id_v55(
            _DOMAINS["verification"], payload
        ),
    }
    raw = canonical_json_bytes(document)
    if VERIFICATION_ID != "0" * 64 and (
        document["verification_id"] != VERIFICATION_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V55 independent verification changed")
    return raw


def verify_adaptive_joint_verification_bytes_v55(raw: bytes) -> dict[str, Any]:
    if type(raw) is not bytes:
        _fail("V55 verification requires bytes")
    document = loads_canonical_json(raw)
    if type(document) is not dict:
        _fail("V55 verification document changed")
    payload = {
        key: value for key, value in document.items() if key != "verification_id"
    }
    if domains_v55.extension_content_id_v55(_DOMAINS["verification"], payload) != document.get("verification_id"):
        _fail("V55 verification content ID changed")
    if VERIFICATION_ID != "0" * 64 and (
        document["verification_id"] != VERIFICATION_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("V55 verification frozen bytes changed")
    return document


__all__ = (
    "EXPECTED_CAMPAIGN_ID",
    "VERIFICATION_ID",
    "freeze_adaptive_joint_verification_v55",
    "verify_adaptive_joint_campaign_bytes_v55",
    "verify_adaptive_joint_verification_bytes_v55",
)
