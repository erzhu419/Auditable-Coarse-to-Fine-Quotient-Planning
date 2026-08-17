"""Producer/core-free reconstruction of the frozen V57 campaign."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
import hashlib
import random
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v57 as domains_v57
from acfqp import construction_k7_mdl_adaptive_independent_verifier_v56r1 as prior
from acfqp.domains.stochastic_maintenance_cascade import (
    MaintenanceCascadeAction,
    MaintenanceCascadeState,
    MaintenanceCascadeStatus,
    generate_stochastic_maintenance_cascade,
    select_seeded_maintenance_cascade_outcome_v1,
)
from acfqp.generic_atomic_expression_world_model_v4 import FlatRawActionV4
from acfqp.generic_calibrated_mdl_joint_synthesizer_v12 import (
    calibrated_mdl_predictive_stop_update_v12,
)
from acfqp.generic_mdl_adaptive_joint_synthesizer_v11 import (
    MDLAdaptiveJointCandidateV11,
    exact_candidate_replay_v11,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


EXPECTED_CAMPAIGN_ID = "744e764a35cb7ba4955852fa62c30978b7aac35d0761b7054cb64298be1fd92b"
EXPECTED_CAMPAIGN_BYTE_COUNT = 25_640_858
EXPECTED_CAMPAIGN_SHA256 = "3fc9f09eac87e1ea2180a1b6a5523694aed5c1dc41438a7484e6a9dc9f925588"
EXPECTED_PREREGISTRATION_ID = (
    "2a2ecfb2c41165bea437f1f91b4114d1432e4e690e6bf2775a231b8d88ceb3fd"
)
EXPECTED_V56R1_CAMPAIGN_ID = (
    "0f5032377cd52b021133fe03a4ab4a34613a230bd3ae25efa43e02ca911521a8"
)
EXPECTED_V56R1_VERIFICATION_ID = (
    "8aa9de632593f60ae8ac59cac3f0affa25568caf011211271913d8732e66733f"
)
VERIFICATION_ID = "f38218a0a527dd4411bf1d105162f563eae1800d68bab6d9b821cb0e693d1469"
EXPECTED_CANONICAL_BYTE_COUNT = 2_100
EXPECTED_CANONICAL_SHA256 = "fb79bcfc0e73a44254b9d9db32af0cc8d86293db84871026b59f80737ecbc86d"

_BALANCED_SEEDS = tuple(range(571_101, 571_133))
_COUPLED_SEEDS = tuple(range(572_101, 572_133))
_MAINTENANCE_SEEDS = tuple(range(573_101, 573_133))
_PLANNING_COUNT = 4
_FACTOR_LIBRARY_LABELS = 370
_FACTOR_CREDIT = 16
_INVALIDATED_PENALTY = 16
_GLOBAL_ALPHA_DENOMINATOR = 20
_EPOCH_SPENDING_BASE = 2
_SUCCESS_MULTIPLIER_NUMERATOR = 3
_SUCCESS_MULTIPLIER_DENOMINATOR = 2
_EVIDENCE_CREDIT_PER_BIT = 2
_DOMAINS = {
    "acquisition": (
        domains_v57.CONSTRUCTION_K7_CALIBRATED_MDL_ACQUISITION_V57_DOMAIN
    ),
    "sample_tax": (
        domains_v57.CONSTRUCTION_K7_CALIBRATED_MDL_SAMPLE_TAX_V57_DOMAIN
    ),
    "campaign": domains_v57.CONSTRUCTION_K7_CALIBRATED_MDL_CAMPAIGN_V57_DOMAIN,
    "verification": (
        domains_v57.CONSTRUCTION_K7_CALIBRATED_MDL_VERIFICATION_V57_DOMAIN
    ),
}


class ConstructionK7CalibratedMDLIndependentVerifierV57Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7CalibratedMDLIndependentVerifierV57Error(message)


def _first_difference(expected: Any, actual: Any, path: str = "$") -> str:
    if type(expected) is not type(actual):
        return f"{path}: type {type(expected).__name__} != {type(actual).__name__}"
    if type(expected) is dict:
        if set(expected) != set(actual):
            return (
                f"{path}: keys missing={sorted(set(expected) - set(actual))} "
                f"extra={sorted(set(actual) - set(expected))}"
            )
        for key in expected:
            difference = _first_difference(
                expected[key], actual[key], f"{path}.{key}"
            )
            if difference:
                return difference
        return ""
    if type(expected) is list:
        if len(expected) != len(actual):
            return f"{path}: length {len(expected)} != {len(actual)}"
        for index, (expected_item, actual_item) in enumerate(
            zip(expected, actual, strict=True)
        ):
            difference = _first_difference(
                expected_item, actual_item, f"{path}[{index}]"
            )
            if difference:
                return difference
        return ""
    if expected != actual:
        return f"{path}: {expected!r} != {actual!r}"
    return ""


def _canonical_roundtrip(value: Any) -> Any:
    """Compare against the semantic value decoded from frozen canonical bytes."""
    return loads_canonical_json(canonical_json_bytes(value))


@dataclass(frozen=True, slots=True)
class _MaintenanceAdapter:
    family: str
    seed: int
    kernel: Any
    catalogue: tuple[FlatRawActionV4, ...]
    encode: Any

    def initial(self) -> Any:
        return self.kernel.initial_distribution()[0][1]

    def actions(self, state: Any) -> tuple[Any, ...]:
        return tuple(self.kernel.actions(state))

    def action_key(self, action: Any) -> int:
        return action.task

    def action(self, key: int) -> Any:
        return MaintenanceCascadeAction(key)

    def active(self, state: Any) -> bool:
        return state.status is MaintenanceCascadeStatus.ACTIVE

    def success(self, state: Any) -> bool:
        return state.status is MaintenanceCascadeStatus.SUCCESS

    def probe_state(self, key: int) -> Any:
        rule = self.kernel.rules[key]
        return MaintenanceCascadeState(
            rule.source_zone,
            0,
            0,
            0,
            0,
            rule.source_zone,
            MaintenanceCascadeStatus.ACTIVE,
        )

    def select_outcome(
        self, state: Any, key: int, episode_index: int, decision_index: int
    ) -> tuple[Any, str]:
        return select_seeded_maintenance_cascade_outcome_v1(
            self.kernel.step(state, MaintenanceCascadeAction(key)),
            seed=self.seed,
            episode_index=episode_index,
            decision_index=decision_index,
        )


def _maintenance_adapter(seed: int) -> _MaintenanceAdapter:
    kernel, witness = generate_stochastic_maintenance_cascade(
        zone_count=7, repair_base=2, seed=seed
    )
    state_order = list(range(10))
    action_order = list(range(6))
    random.Random(seed ^ 0x57E61).shuffle(state_order)
    random.Random(seed ^ 0x57F73).shuffle(action_order)
    catalogue = tuple(
        FlatRawActionV4(
            key,
            tuple(
                (
                    seed * 100 + rule.source_zone,
                    seed * 100 + rule.destination_zone,
                    rule.repair_increment,
                    rule.spare_increment,
                    rule.hazard_increment,
                    seed * 10_000 + key,
                )[index]
                for index in action_order
            ),
        )
        for key, rule in enumerate(kernel.rules)
    )

    def encode(state: MaintenanceCascadeState) -> tuple[int, ...]:
        status = prior._TOKENS[
            "A"
            if state.status is MaintenanceCascadeStatus.ACTIVE
            else "S"
            if state.status is MaintenanceCascadeStatus.SUCCESS
            else "F"
        ]
        semantic = (
            seed * 100 + state.zone,
            state.repaired_units,
            state.spare_units,
            state.latent_load,
            state.hazard,
            state.elapsed,
            status,
            kernel.hazard_capacity,
            kernel.repair_target,
            seed * 100 + kernel.goal_zone,
        )
        return tuple(semantic[index] for index in state_order)

    del witness
    return _MaintenanceAdapter(
        "MAINTENANCE_CASCADE", seed, kernel, catalogue, encode
    )


def _adapter(family: str, seed: int):
    if family == "MAINTENANCE_CASCADE":
        return _maintenance_adapter(seed)
    return prior._adapter(family, seed)


def _acquisition_document(
    *,
    adapter: Any,
    arm: str,
    enabled: bool,
    labels: int,
    rows: tuple[Any, ...],
    candidate: MDLAdaptiveJointCandidateV11,
    issued_at: int,
    invalidated: int,
    disagreements: int,
    epoch: int,
    predictive_successes: int,
    history: list[dict[str, Any]],
    stop: Mapping[str, Any],
) -> dict[str, Any]:
    payload = {
        "schema": "acfqp.calibrated_mdl_acquisition.v57",
        "v56r1_campaign_id": EXPECTED_V56R1_CAMPAIGN_ID,
        "family": adapter.family,
        "seed": adapter.seed,
        "arm": arm,
        "factor_prior_enabled": enabled,
        "ground_support_labels": labels,
        "raw_transition_count": len(rows),
        "raw_transition_sha256": prior._raw_sha(rows),
        "candidate": dict(candidate.public_document),
        "candidate_issued_at_support_label": issued_at,
        "invalidated_candidate_count": invalidated,
        "candidate_program_disagreement_count": disagreements,
        "candidate_epoch": epoch,
        "post_issuance_exact_prediction_success_count": predictive_successes,
        "stopping_history": history,
        "terminal_stop_update": dict(stop),
        "stopped_by_calibrated_mdl_predictive_rule": stop["stopped"],
        "candidate_synthesis_attempted_after_every_support_query": True,
        "minimum_candidate_label_floor_consumed": False,
        "confirmation_block_consumed": False,
        "fixed_confidence_reserve_consumed": False,
        "reachable_frontier_exhaustion_input_consumed": False,
        "witness_blind_depth_frontier_policy": True,
        "generation_witness_accessed": False,
        "full_frontier_calibration_consumed": False,
        "same_synthesizer_query_order_mdl_and_confidence_rule": True,
        "only_switched_variable": "REGISTERED_FACTOR_CODE_CREDIT_UNITS",
    }
    return {
        **payload,
        "acquisition_id": domains_v57.extension_content_id_v57(
            _DOMAINS["acquisition"], payload
        ),
    }


def _acquire(adapter: Any) -> dict[str, dict[str, Any]]:
    rows: list[Any] = []
    batches: list[tuple[Any, ...]] = []
    candidate: MDLAdaptiveJointCandidateV11 | None = None
    issued_at = 0
    invalidated = 0
    disagreements = 0
    epoch = 0
    predictive_successes = 0
    previous_fingerprint = None
    pending = {"ANONYMOUS_FACTOR_PRIOR_ON": True, "STRICT_NO_PRIOR": False}
    histories = {arm: [] for arm in pending}
    results = {}
    maximum = {
        "BALANCED_BATCH_REFINEMENT": 128,
        "COUPLED_EXCHANGE": 160,
        "MAINTENANCE_CASCADE": 200,
    }[adapter.family]
    for labels, batch in enumerate(prior._frontier(adapter), 1):
        if labels > maximum:
            break
        rows.extend(batch)
        batches.append(batch)
        reason = "NO_COMPLETE_CANDIDATE_YET"
        replay = None
        if candidate is not None:
            replay = exact_candidate_replay_v11(
                candidate, tuple(rows), adapter.catalogue
            )
            if replay["exact"] is True:
                predictive_successes += 1
                reason = "PREISSUED_CANDIDATE_EXACTLY_PREDICTED_NEW_BATCH"
            else:
                invalidated += 1
                epoch += 1
                predictive_successes = 0
                previous_fingerprint = candidate.public_document[
                    "program_fingerprint_sha256"
                ]
                candidate = None
                reason = "NEW_BATCH_INVALIDATED_PREISSUED_CANDIDATE"
        if candidate is None:
            try:
                candidate = prior._candidate(tuple(rows), adapter.catalogue, labels)
            except Exception:
                for arm in tuple(pending):
                    histories[arm].append(
                        {
                            "support_label_count": labels,
                            "raw_transition_sha256": prior._raw_sha(tuple(rows)),
                            "update_reason": reason,
                            "candidate_available": False,
                        }
                    )
                continue
            issued_at = labels
            fingerprint = candidate.public_document[
                "program_fingerprint_sha256"
            ]
            if previous_fingerprint is not None and fingerprint != previous_fingerprint:
                disagreements += 1
            reason = (
                "FIRST_COMPLETE_CANDIDATE_SYNTHESIZED"
                if invalidated == 0
                else "COUNTEREVIDENCE_TRIGGERED_COMPLETE_RESYNTHESIS"
            )
        for arm, enabled in tuple(pending.items()):
            stop = calibrated_mdl_predictive_stop_update_v12(
                candidate,
                tuple(rows),
                adapter.catalogue,
                factor_prior_enabled=enabled,
                invalidated_candidate_count=invalidated,
                candidate_program_disagreement_count=disagreements,
                candidate_epoch=epoch,
                post_issuance_exact_prediction_success_count=predictive_successes,
                factor_signature_credit_units=_FACTOR_CREDIT,
                invalidated_candidate_penalty_units=_INVALIDATED_PENALTY,
                minimum_reusable_factor_count=3,
                global_alpha_denominator=_GLOBAL_ALPHA_DENOMINATOR,
                epoch_alpha_spending_base=_EPOCH_SPENDING_BASE,
                success_evalue_multiplier_numerator=(
                    _SUCCESS_MULTIPLIER_NUMERATOR
                ),
                success_evalue_multiplier_denominator=(
                    _SUCCESS_MULTIPLIER_DENOMINATOR
                ),
                predictive_evidence_credit_units_per_bit=(
                    _EVIDENCE_CREDIT_PER_BIT
                ),
            )
            histories[arm].append(
                {
                    "support_label_count": labels,
                    "raw_transition_sha256": prior._raw_sha(tuple(rows)),
                    "update_reason": reason,
                    "candidate_available": True,
                    "candidate_id": candidate.public_document["candidate_id"],
                    "exact_replay": replay,
                    "stop_update": stop,
                }
            )
            if stop["stopped"] is not True:
                continue
            document = _acquisition_document(
                adapter=adapter,
                arm=arm,
                enabled=enabled,
                labels=labels,
                rows=tuple(rows),
                candidate=candidate,
                issued_at=issued_at,
                invalidated=invalidated,
                disagreements=disagreements,
                epoch=epoch,
                predictive_successes=predictive_successes,
                history=list(histories[arm]),
                stop=stop,
            )
            results[arm] = {
                "document": document,
                "candidate": candidate,
                "rows": tuple(rows),
                "batches": tuple(batches),
            }
            del pending[arm]
        if not pending:
            prefix = tuple(
                row
                for batch in results["STRICT_NO_PRIOR"]["batches"][
                    : len(results["ANONYMOUS_FACTOR_PRIOR_ON"]["batches"])
                ]
                for row in batch
            )
            if prefix != results["ANONYMOUS_FACTOR_PRIOR_ON"]["rows"]:
                _fail("V57 independent matched prefix changed")
            return results
    _fail(f"V57 independent calibrated stop failed for {adapter.family} {adapter.seed}")


def _verify_occurrence(args: tuple[Any, ...]) -> dict[str, Any]:
    (
        family,
        family_index,
        seed,
        expected_prior,
        expected_no_prior,
        expected_episodes,
        expected_validation,
    ) = args
    adapter = _adapter(family, seed)
    acquisitions = _acquire(adapter)
    actual_prior = _canonical_roundtrip(
        acquisitions["ANONYMOUS_FACTOR_PRIOR_ON"]["document"]
    )
    actual_no_prior = _canonical_roundtrip(
        acquisitions["STRICT_NO_PRIOR"]["document"]
    )
    if actual_prior != expected_prior:
        _fail(
            f"V57 independent prior acquisition changed at {family} {seed}: "
            + _first_difference(expected_prior, actual_prior)
        )
    if actual_no_prior != expected_no_prior:
        _fail(
            f"V57 independent no-prior acquisition changed at {family} {seed}: "
            + _first_difference(expected_no_prior, actual_no_prior)
        )
    failures = []
    distinctions = []
    local = {"ANONYMOUS_FACTOR_PRIOR_ON": 0, "STRICT_NO_PRIOR": 0}
    execution = {arm: 0 for arm in (*local, "STRICT_EXACT_CONTEXT")}
    planning = dict(execution)
    validation_labels = 0
    validation_mismatches = 0
    if family_index < _PLANNING_COUNT:
        rebuilt = {}
        for arm in ("ANONYMOUS_FACTOR_PRIOR_ON", "STRICT_NO_PRIOR"):
            episode, arm_failures, arm_distinctions = prior._abstract_episode(
                adapter, arm, family_index, acquisitions[arm]
            )
            rebuilt[arm] = episode
            failures.extend(arm_failures)
            distinctions.extend(arm_distinctions)
            local[arm] = episode["local_ground_support_labels"]
        rebuilt["STRICT_EXACT_CONTEXT"] = prior._strict_episode(
            adapter, family_index
        )
        if rebuilt != expected_episodes:
            _fail(f"V57 independent episodes changed at {family} {seed}")
        if rebuilt["ANONYMOUS_FACTOR_PRIOR_ON"]["action_keys"] != rebuilt[
            "STRICT_NO_PRIOR"
        ]["action_keys"]:
            _fail("V57 factor-prior switch changed the independent abstract plan")
        if not all(row["success"] for row in rebuilt.values()):
            _fail("V57 independent ground replay failed")
        for arm, row in rebuilt.items():
            execution[arm] = row["execution_steps"]
            planning[arm] = row["planning_compute_events"]
        validation = prior._validation(adapter, acquisitions)
        if validation != expected_validation:
            _fail(f"V57 independent validation changed at {family} {seed}")
        validation_labels = validation["full_frontier_ground_support_labels"]
        validation_mismatches = sum(
            row["support_mismatch_count"]
            for row in validation["arm_replay"].values()
        )
    return {
        "family": family,
        "seed": seed,
        "prior_labels": expected_prior["ground_support_labels"],
        "no_prior_labels": expected_no_prior["ground_support_labels"],
        "prior_local": local["ANONYMOUS_FACTOR_PRIOR_ON"],
        "no_prior_local": local["STRICT_NO_PRIOR"],
        "prior_predictive_successes": expected_prior[
            "post_issuance_exact_prediction_success_count"
        ],
        "no_prior_predictive_successes": expected_no_prior[
            "post_issuance_exact_prediction_success_count"
        ],
        "prior_invalidated": expected_prior["invalidated_candidate_count"],
        "no_prior_invalidated": expected_no_prior["invalidated_candidate_count"],
        "failures": failures,
        "distinctions": distinctions,
        "execution": execution,
        "planning": planning,
        "validation_labels": validation_labels,
        "validation_mismatches": validation_mismatches,
    }


def _sample_tax(campaign: Mapping[str, Any], results: list[dict[str, Any]]):
    prior_labels = sum(row["prior_labels"] for row in results)
    no_prior_labels = sum(row["no_prior_labels"] for row in results)
    prior_local = sum(row["prior_local"] for row in results)
    no_prior_local = sum(row["no_prior_local"] for row in results)
    family_rows = {}
    for family in (
        "BALANCED_BATCH_REFINEMENT",
        "COUPLED_EXCHANGE",
        "MAINTENANCE_CASCADE",
    ):
        rows = [row for row in results if row["family"] == family]
        family_rows[family] = {
            "occurrence_count": len(rows),
            "factor_prior_on_acquisition_labels": sum(
                row["prior_labels"] for row in rows
            ),
            "strict_no_prior_acquisition_labels": sum(
                row["no_prior_labels"] for row in rows
            ),
            "factor_prior_on_terminal_predictive_success_count_sum": sum(
                row["prior_predictive_successes"] for row in rows
            ),
            "strict_no_prior_terminal_predictive_success_count_sum": sum(
                row["no_prior_predictive_successes"] for row in rows
            ),
        }
        family_rows[family]["incremental_label_reduction"] = (
            family_rows[family]["strict_no_prior_acquisition_labels"]
            - family_rows[family]["factor_prior_on_acquisition_labels"]
        )
    curve = []
    prior_running = _FACTOR_LIBRARY_LABELS
    no_prior_running = 0
    break_even = None
    for index, row in enumerate(results, 1):
        prior_running += row["prior_labels"]
        no_prior_running += row["no_prior_labels"]
        reduction = no_prior_running - prior_running
        curve.append(
            {
                "occurrence_count": index,
                "family": row["family"],
                "factor_prior_on_lifetime_labels": prior_running,
                "strict_no_prior_lifetime_labels": no_prior_running,
                "net_label_reduction": reduction,
            }
        )
        if break_even is None and reduction > 0:
            break_even = index
    online = (no_prior_labels + no_prior_local) - (prior_labels + prior_local)
    payload = {
        "schema": "acfqp.calibrated_mdl_sample_tax.v57",
        "v56r1_campaign_id": EXPECTED_V56R1_CAMPAIGN_ID,
        "factor_library_labels_prior_on_only": _FACTOR_LIBRARY_LABELS,
        "factor_prior_on_acquisition_labels": prior_labels,
        "strict_no_prior_acquisition_labels": no_prior_labels,
        "incremental_acquisition_label_reduction": no_prior_labels - prior_labels,
        "factor_prior_on_local_recovery_labels": prior_local,
        "strict_no_prior_local_recovery_labels": no_prior_local,
        "online_label_reduction_including_local_recovery": online,
        "lifetime_label_reduction_after_factor_library_tax": (
            online - _FACTOR_LIBRARY_LABELS
        ),
        "diagnostic_break_even_occurrence_count": break_even,
        "family_projections": family_rows,
        "prefix_curve": curve,
        "same_synthesizer_query_order_mdl_and_calibrated_confidence_rule": True,
        "only_registered_factor_code_credit_switched": True,
        "fixed_minimum_label_floor_consumed": False,
        "fixed_confirmation_block_consumed": False,
        "reachable_frontier_exhaustion_stop_consumed": False,
        "official_break_even_claimed": False,
    }
    expected = {
        **payload,
        "sample_tax_id": domains_v57.extension_content_id_v57(
            _DOMAINS["sample_tax"], payload
        ),
    }
    if campaign["sample_tax"] != expected:
        _fail("V57 independent sample-tax reconstruction changed")
    return expected


def verify_calibrated_mdl_campaign_bytes_v57(raw: bytes) -> dict[str, Any]:
    if (
        type(raw) is not bytes
        or len(raw) != EXPECTED_CAMPAIGN_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CAMPAIGN_SHA256
    ):
        _fail("frozen V57 campaign bytes changed")
    campaign = loads_canonical_json(raw)
    if type(campaign) is not dict or campaign.get("campaign_id") != EXPECTED_CAMPAIGN_ID:
        _fail("frozen V57 campaign identity changed")
    payload = {key: value for key, value in campaign.items() if key != "campaign_id"}
    if (
        domains_v57.extension_content_id_v57(_DOMAINS["campaign"], payload)
        != EXPECTED_CAMPAIGN_ID
    ):
        _fail("V57 campaign content ID changed")
    if (
        campaign.get("preregistration_id") != EXPECTED_PREREGISTRATION_ID
        or campaign.get("v56r1_campaign_id") != EXPECTED_V56R1_CAMPAIGN_ID
        or campaign.get("v56r1_verification_id")
        != EXPECTED_V56R1_VERIFICATION_ID
    ):
        _fail("V57 predecessor or preregistration identity changed")
    if (
        campaign.get("minimum_candidate_label_floor_consumed") is not False
        or campaign.get("confirmation_block_consumed") is not False
        or campaign.get("fixed_confidence_reserve_consumed") is not False
        or campaign.get("reachable_frontier_exhaustion_stop_consumed") is not False
        or campaign.get("full_frontier_target_layout_calibration_consumed")
        is not False
    ):
        _fail("V57 forbidden stop scaffold changed")
    if (
        campaign.get("official_execution_allowed") is not False
        or campaign.get("official_scalar_cost") is not None
        or campaign.get("official_N_break_even") is not None
        or campaign.get("WORKLOAD_ECONOMICS_GATE") != "NOT_RUN"
        or campaign.get("COUNTER_COMPLETENESS_GATE") != "NOT_RUN"
    ):
        _fail("V57 official gate locks changed")
    prior_rows = campaign["acquisitions"]["ANONYMOUS_FACTOR_PRIOR_ON"]
    no_prior_rows = campaign["acquisitions"]["STRICT_NO_PRIOR"]
    specs = [
        ("BALANCED_BATCH_REFINEMENT", index, seed)
        for index, seed in enumerate(_BALANCED_SEEDS)
    ] + [
        ("COUPLED_EXCHANGE", index, seed)
        for index, seed in enumerate(_COUPLED_SEEDS)
    ] + [
        ("MAINTENANCE_CASCADE", index, seed)
        for index, seed in enumerate(_MAINTENANCE_SEEDS)
    ]
    if len(prior_rows) != len(specs) or len(no_prior_rows) != len(specs):
        _fail("V57 occurrence inventory changed")
    episode_by_arm = {
        arm: {(row["family"], row["seed"]): row for row in rows}
        for arm, rows in campaign["episodes"].items()
    }
    validation_by_key = {
        (row["family"], row["seed"]): row
        for row in campaign["isolated_full_frontier_validations"]
    }
    arguments = []
    for position, (family, family_index, seed) in enumerate(specs):
        episodes = (
            {
                arm: episode_by_arm[arm][(family, seed)]
                for arm in (
                    "ANONYMOUS_FACTOR_PRIOR_ON",
                    "STRICT_NO_PRIOR",
                    "STRICT_EXACT_CONTEXT",
                )
            }
            if family_index < _PLANNING_COUNT
            else {}
        )
        arguments.append(
            (
                family,
                family_index,
                seed,
                prior_rows[position],
                no_prior_rows[position],
                episodes,
                validation_by_key.get((family, seed)),
            )
        )
    with ProcessPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(_verify_occurrence, arguments))
    failures = [item for row in results for item in row["failures"]]
    distinctions = [item for row in results for item in row["distinctions"]]
    if failures != campaign["failed_certificates"]:
        _fail("V57 independent certificate reconstruction changed")
    if distinctions != campaign["local_distinctions"]:
        _fail("V57 independent distinction reconstruction changed")
    sample = _sample_tax(campaign, results)
    ood_reusable = prior._verify_ood(campaign)
    accounting = {
        "offline_factor_library_labels": _FACTOR_LIBRARY_LABELS,
        "factor_prior_on_target_acquisition_labels": sample[
            "factor_prior_on_acquisition_labels"
        ],
        "strict_no_prior_target_acquisition_labels": sample[
            "strict_no_prior_acquisition_labels"
        ],
        "factor_prior_on_local_recovery_labels": sample[
            "factor_prior_on_local_recovery_labels"
        ],
        "strict_no_prior_local_recovery_labels": sample[
            "strict_no_prior_local_recovery_labels"
        ],
        "isolated_validation_labels": sum(
            row["validation_labels"] for row in results
        ),
        "factor_prior_on_execution_steps": sum(
            row["execution"]["ANONYMOUS_FACTOR_PRIOR_ON"] for row in results
        ),
        "strict_no_prior_execution_steps": sum(
            row["execution"]["STRICT_NO_PRIOR"] for row in results
        ),
        "direct_execution_steps": sum(
            row["execution"]["STRICT_EXACT_CONTEXT"] for row in results
        ),
        "factor_prior_on_planning_compute_events": sum(
            row["planning"]["ANONYMOUS_FACTOR_PRIOR_ON"] for row in results
        ),
        "strict_no_prior_planning_compute_events": sum(
            row["planning"]["STRICT_NO_PRIOR"] for row in results
        ),
        "direct_planning_compute_events": sum(
            row["planning"]["STRICT_EXACT_CONTEXT"] for row in results
        ),
        "certificate_compute_events": len(failures),
        "all_axes_separate": True,
    }
    if accounting != campaign["accounting"]:
        _fail("V57 independent accounting reconstruction changed")
    return {
        "acquisition_occurrence_count": len(results),
        "family_occurrence_counts": {
            family: sum(row["family"] == family for row in results)
            for family in (
                "BALANCED_BATCH_REFINEMENT",
                "COUPLED_EXCHANGE",
                "MAINTENANCE_CASCADE",
            )
        },
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
        "failed_certificate_count": len(failures),
        "local_distinction_count": len(distinctions),
        "isolated_validation_label_count": accounting[
            "isolated_validation_labels"
        ],
        "isolated_validation_support_mismatch_count": sum(
            row["validation_mismatches"] for row in results
        ),
        "prior_invalidated_candidate_count": sum(
            row["prior_invalidated"] for row in results
        ),
        "no_prior_invalidated_candidate_count": sum(
            row["no_prior_invalidated"] for row in results
        ),
        "ood_reusable_count": ood_reusable,
        "ood_transfer_admitted": False,
    }


def freeze_calibrated_mdl_verification_v57(campaign_bytes: bytes) -> bytes:
    projection = verify_calibrated_mdl_campaign_bytes_v57(campaign_bytes)
    payload = {
        "schema": "acfqp.calibrated_mdl_independent_verification.v57",
        "campaign_id": EXPECTED_CAMPAIGN_ID,
        "campaign_byte_count": EXPECTED_CAMPAIGN_BYTE_COUNT,
        "campaign_sha256": EXPECTED_CAMPAIGN_SHA256,
        "preregistration_id": EXPECTED_PREREGISTRATION_ID,
        "v56r1_campaign_id": EXPECTED_V56R1_CAMPAIGN_ID,
        "v56r1_verification_id": EXPECTED_V56R1_VERIFICATION_ID,
        "producer_module_imported": False,
        "campaign_core_module_imported": False,
        "prior_producer_free_ground_and_planning_primitives_reused": True,
        "raw_three_domain_acquisition_sequences_reconstructed": True,
        "calibrated_eprocess_and_mdl_stops_reconstructed": True,
        "reachable_frontier_exhaustion_stop_consumed": False,
        "receding_abstract_plans_and_outcome_tapes_replayed": True,
        "certificate_failure_only_local_recovery_reconstructed": True,
        "isolated_full_frontier_validations_reconstructed": True,
        "sample_tax_accounting_and_ood_reconstructed": True,
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
        "verification_id": domains_v57.extension_content_id_v57(
            _DOMAINS["verification"], payload
        ),
    }
    raw = canonical_json_bytes(document)
    if VERIFICATION_ID != "0" * 64 and (
        document["verification_id"] != VERIFICATION_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V57 independent verification changed")
    return raw


def verify_calibrated_mdl_verification_bytes_v57(raw: bytes) -> dict[str, Any]:
    if type(raw) is not bytes:
        _fail("V57 verification requires bytes")
    document = loads_canonical_json(raw)
    if type(document) is not dict:
        _fail("V57 verification document changed")
    payload = {
        key: value for key, value in document.items() if key != "verification_id"
    }
    if (
        domains_v57.extension_content_id_v57(_DOMAINS["verification"], payload)
        != document.get("verification_id")
    ):
        _fail("V57 verification content ID changed")
    if VERIFICATION_ID != "0" * 64 and (
        document["verification_id"] != VERIFICATION_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("V57 verification frozen bytes changed")
    return document


__all__ = (
    "EXPECTED_CAMPAIGN_ID",
    "VERIFICATION_ID",
    "freeze_calibrated_mdl_verification_v57",
    "verify_calibrated_mdl_campaign_bytes_v57",
    "verify_calibrated_mdl_verification_bytes_v57",
)
