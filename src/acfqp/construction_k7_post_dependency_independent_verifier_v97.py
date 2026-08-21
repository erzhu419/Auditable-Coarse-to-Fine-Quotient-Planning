"""Producer-free verification of the frozen V97 post-dependency campaign."""

from __future__ import annotations

import copy
import hashlib
import math
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v97 as domains
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "b132245b0827898cb497232ed82b911fc17bebc4a30e981a7b080895abc8bf3e"
CAMPAIGN_BYTE_COUNT = 2_361_088
CAMPAIGN_SHA256 = "dc5bd10f193e98038ef2ced4d0ab7558deb35200104195de8299ded1add32afc"
PREREGISTRATION_ID = "99c6ae8e5c71ea1f5b92fc01117d979772d0958a255926beb81d032837b008fa"
SOURCE_LIBRARY_ARTIFACT_ID = "4f0a9592f7d6ba2d7683e9328f76dbd01bd18a3a47a062ea764f7a20012caeba"
STRUCTURE_LIBRARY_ID = "96c18874b88ec9422adf7fc84e9eef8414378a6abe5a0322d933ec51e62c5be6"
V96_CAMPAIGN_ID = "93d3ae84f1a1f2e1a6cb7dac3f72d5e5ef24646b2e9f864657fee3a242443551"
V96_VERIFICATION_ID = "ce1a04b45959e2d34d2ad31b8e84630796dc377c24b7190e74f72e8faed20fca"
TARGET_SEEDS = (999_101, 999_102, 999_103, 999_104)
TARGET_EPISODES = (41, 42, 43)
VERIFICATION_ID = "341b170d9ec3c70ae4ba954f84651cc216dad980cc7e783872a77b33aaae9dac"
EXPECTED_CANONICAL_BYTE_COUNT = 1_295
EXPECTED_CANONICAL_SHA256 = "fdd0555e3caf94b55ef62586b7cb00549096562bbb8ff072568b2bc75477e6f4"

_SEQUENCE_DOMAIN = b"acfqp:generic-persistent-post-dependency-sequence:v97\x00"
_BASE_ACQUISITION_DOMAIN = b"acfqp:generic-multi-residual-acquisition:v24\x00"
_DEPENDENCY_CANDIDATE_DOMAIN = b"acfqp:post-dependency-residual-candidate:v97\x00"
_DEPENDENCY_ACQUISITION_DOMAIN = b"acfqp:post-dependency-multi-residual-acquisition:v97\x00"
_ABSTRACT_PLAN_DOMAIN = b"acfqp:post-dependency-abstract-plan:v97\x00"
_EPISODE_DOMAIN = b"acfqp:generic-preloaded-certificate-receding-episode:v74\x00"


class ConstructionK7PostDependencyIndependentVerifierV97Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7PostDependencyIndependentVerifierV97Error(message)


def _generic_id(domain: bytes, payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(domain + canonical_json_bytes(payload)).hexdigest()


def _check_generic_id(document: Any, key: str, domain: bytes) -> None:
    if type(document) is not dict:
        _fail(f"V97 {key} document type changed")
    payload = {name: value for name, value in document.items() if name != key}
    if document.get(key) != _generic_id(domain, payload):
        _fail(f"V97 {key} content identity changed")


def _check_v97_id(document: Any, key: str, domain: str) -> None:
    if type(document) is not dict:
        _fail(f"V97 {key} document type changed")
    payload = {name: value for name, value in document.items() if name != key}
    if document.get(key) != domains.extension_content_id_v97(domain, payload):
        _fail(f"V97 {key} content identity changed")


def _group_count(rows: Any) -> int:
    if type(rows) is not list:
        _fail("V97 row inventory changed")
    groups = set()
    for row in rows:
        action = row.get("selected_action") if type(row) is dict else None
        if (
            type(row) is not dict
            or type(row.get("pre_vector")) is not list
            or type(action) is not dict
            or type(action.get("action_key")) is not int
        ):
            _fail("V97 transition row schema changed")
        groups.add((tuple(row["pre_vector"]), action["action_key"]))
    return len(groups)


def _signed_bits(value: int) -> int:
    return 1 + 2 * int(math.log2(abs(value) + 1))


def _dependency_candidate(
    posts: list[list[int]],
    *,
    target: int,
    driver: int,
    lower: int,
    upper: int,
    structural_prior_enabled: bool,
) -> dict[str, Any] | None:
    leaves = []
    for band in range(3):
        values = sorted(
            {
                row[target]
                for row in posts
                if (
                    (band == 0 and row[driver] <= lower)
                    or (band == 1 and lower < row[driver] <= upper)
                    or (band == 2 and row[driver] > upper)
                )
            }
        )
        if not values:
            return None
        leaves.append(values)
    excess = sum(
        len(leaves[0 if row[driver] <= lower else 1 if row[driver] <= upper else 2])
        - 1
        for row in posts
    )
    state_bits = max(1, math.ceil(math.log2(max(2, len(posts[0])))))
    support_bits = sum(_signed_bits(value) for leaf in leaves for value in leaf)
    payload = {
        "schema": "acfqp.post_dependency_residual_candidate.v97",
        "candidate_kind": "POST_DEPENDENCY_THREE_BAND_FINITE_SUPPORT",
        "target_column": target,
        "driver_post_column": driver,
        "lower_inclusive_threshold": lower,
        "upper_inclusive_threshold": upper,
        "leaf_supports": leaves,
        "normalized_expression": [
            "PD03",
            ["PD00", driver],
            ["PD01", lower],
            ["PD01", upper],
            [["PD02", *leaf] for leaf in leaves],
        ],
        "predictive_support_excess": excess,
        "description_length_bits": (
            (1 if structural_prior_enabled else 8)
            + 2 * state_bits
            + _signed_bits(lower)
            + _signed_bits(upper)
            + support_bits
        ),
        "structure_prior_enabled": structural_prior_enabled,
        "structure_prior_supplied_driver_thresholds_or_leaf_values": False,
        "fit_on_complete_available_query_pool": True,
        "future_prediction_calibrated": False,
        "proposal_only_not_safety_authority": True,
    }
    return {
        **payload,
        "candidate_id": _generic_id(_DEPENDENCY_CANDIDATE_DOMAIN, payload),
    }


def _derive_acquisition(
    rows: list[dict[str, Any]],
    layout: Mapping[str, Any],
    targets: list[int],
    base: Mapping[str, Any],
    *,
    structural_prior_enabled: bool,
) -> dict[str, Any]:
    _check_generic_id(
        base, "multi_residual_acquisition_id", _BASE_ACQUISITION_DOMAIN
    )
    order = layout.get("state_canonical_to_raw")
    if type(order) is not list:
        _fail("V97 dependency alignment changed")
    posts = []
    for row in rows:
        post = row.get("post_vector") if type(row) is dict else None
        if type(post) is not list or sorted(order) != list(range(len(post))):
            _fail("V97 dependency raw post changed")
        posts.append([post[index] for index in order])
    calibrated = copy.deepcopy(base.get("compilable_candidates"))
    if type(calibrated) is not list:
        _fail("V97 calibrated residual candidates changed")
    calibrated_targets = {row.get("target_column") for row in calibrated}
    completions = []
    evaluation_count = 0
    for target in targets:
        if target in calibrated_targets:
            continue
        candidates = []
        for driver in range(len(posts[0])):
            if driver == target:
                continue
            values = sorted({row[driver] for row in posts})
            for lower_offset in range(len(values) - 2):
                for upper_offset in range(lower_offset + 1, len(values) - 1):
                    evaluation_count += len(posts)
                    candidate = _dependency_candidate(
                        posts,
                        target=target,
                        driver=driver,
                        lower=values[lower_offset],
                        upper=values[upper_offset],
                        structural_prior_enabled=structural_prior_enabled,
                    )
                    if candidate is not None:
                        candidates.append(candidate)
        candidates.sort(
            key=lambda row: (
                row["predictive_support_excess"],
                row["description_length_bits"],
                canonical_json_bytes(row),
            )
        )
        if candidates:
            completions.append(candidates[0])
    all_candidates = sorted(
        [*calibrated, *copy.deepcopy(completions)],
        key=lambda row: row["target_column"],
    )
    payload = {
        "schema": "acfqp.post_dependency_multi_residual_acquisition.v97",
        "base_multi_residual_acquisition": copy.deepcopy(base),
        "base_multi_residual_acquisition_id": base[
            "multi_residual_acquisition_id"
        ],
        "unknown_residual_target_columns": list(targets),
        "shared_physical_ground_support_labels": _group_count(rows),
        "structural_prior_library_id": (
            STRUCTURE_LIBRARY_ID if structural_prior_enabled else None
        ),
        "structural_prior_enabled": structural_prior_enabled,
        "same_finite_grammar_and_binding_search_in_prior_on_off_arms": True,
        "only_prior_code_length_switched": True,
        "post_dependency_candidate_binding_evaluation_count": evaluation_count,
        "calibrated_predecessor_candidates": calibrated,
        "retrospective_post_dependency_candidates": completions,
        "compilable_candidates": all_candidates,
        "compilable_target_columns": [row["target_column"] for row in all_candidates],
        "compilable_candidate_count": len(all_candidates),
        "all_residual_targets_have_compilable_proposals": (
            [row["target_column"] for row in all_candidates] == targets
        ),
        "successor_coordinate_dependency_discovered_from_raw_differences": bool(
            completions
        ),
        "dependency_program_used_as_fallible_action_ordering_heuristic": True,
        "persistent_exact_overlay_exclusively_discharges_safety": True,
        "ground_fact_transfer_present": False,
        "complete_world_model_synthesized": False,
        "global_exact_dynamics_claimed": False,
        "proposal_only_not_safety_authority": True,
    }
    return {
        **payload,
        "multi_residual_acquisition_id": _generic_id(
            _DEPENDENCY_ACQUISITION_DOMAIN, payload
        ),
    }


def _check_query_pairing(document: Mapping[str, Any]) -> None:
    failures = document.get("failed_certificates")
    distinctions = document.get("local_distinctions")
    if (
        type(failures) is not list
        or type(distinctions) is not list
        or len(failures) != len(distinctions)
        or [row.get("failure_index") for row in failures]
        != list(range(len(failures)))
        or [row.get("failure_index") for row in distinctions]
        != list(range(len(distinctions)))
        or any(
            row.get("ground_query_performed_before_failure") is not False
            for row in failures
        )
        or any(
            row.get("query_after_failed_certificate") is not True
            for row in distinctions
        )
    ):
        _fail("V97 certificate-failure-only query pairing changed")


def _check_plan(
    plan: Any,
    *,
    acquisition_id: str,
    dependency_ids: list[str],
) -> tuple[bool, int]:
    if type(plan) is not dict:
        _fail("V97 abstract plan type changed")
    if plan.get("persistent_joint_successor_program_used") is not True:
        return False, 0
    extras = {
        "persistent_joint_successor_program_used",
        "persistent_post_dependency_program_used",
        "post_dependency_candidate_count",
        "persistent_partial_fallback_used",
    }
    payload = {
        key: value
        for key, value in plan.items()
        if key != "abstract_plan_id" and key not in extras
    }
    if (
        plan.get("schema") != "acfqp.post_dependency_abstract_plan.v97"
        or plan.get("abstract_plan_id")
        != _generic_id(_ABSTRACT_PLAN_DOMAIN, payload)
        or plan.get("multi_residual_acquisition_id") != acquisition_id
        or plan.get("dependency_candidate_ids") != dependency_ids
        or plan.get("post_dependency_candidate_count") != len(dependency_ids)
        or plan.get("persistent_post_dependency_program_used")
        is not bool(dependency_ids)
        or plan.get("persistent_partial_fallback_used") is not False
        or plan.get("represented_target_columns")
        != list(range(len(plan.get("represented_target_columns", []))))
        or type(plan.get("initial_action_key")) is not int
        or plan.get("ground_transition_accessed_during_abstract_search") is not False
        or plan.get("abstract_plan_used_as_safety_authority") is not False
        or plan.get("complete_world_model_claimed") is not False
    ):
        _fail("V97 jointly compiled abstract plan changed")
    return True, plan["persistent_post_dependency_program_used"] is True


def _check_episode(
    episode: Any,
    *,
    seed: int,
    episode_index: int,
    acquisition_id: str | None,
    dependency_ids: list[str],
    wrapped: bool,
) -> tuple[int, int, int, int]:
    if type(episode) is not dict:
        _fail("V97 episode type changed")
    extras = (
        {
            "new_certificate_labels_charged_this_episode",
            "paid_certificate_labels_cumulative",
            "persistent_exact_support_group_count",
        }
        if wrapped
        else set()
    )
    payload = {
        key: value
        for key, value in episode.items()
        if key != "episode_id" and key not in extras
    }
    if episode.get("episode_id") != _generic_id(_EPISODE_DOMAIN, payload):
        _fail("V97 episode content identity changed")
    labels = episode.get("incremental_certificate_local_ground_support_labels")
    actions = episode.get("action_keys")
    matches = episode.get("execution_action_matches_abstract_proposal")
    receipts = episode.get("abstract_plan_receipts")
    if (
        episode.get("schema")
        != "acfqp.generic_preloaded_certificate_receding_episode.v74"
        or episode.get("family") != "COUPLED_EXCHANGE"
        or episode.get("seed") != seed
        or episode.get("episode_index") != episode_index
        or type(labels) is not int
        or type(actions) is not list
        or episode.get("execution_steps") != len(actions)
        or type(matches) is not list
        or len(matches) != len(actions)
        or episode.get("execution_action_matches_abstract_proposal_count")
        != sum(matches)
        or type(receipts) is not list
        or episode.get("query_local_exact_overlay_exclusively_used_for_safety")
        is not True
        or episode.get("model_or_alignment_used_as_safety_authority") is not False
        or episode.get("target_episode_outcomes_used_to_refit_model_or_alignment")
        is not False
        or episode.get("complete_world_model_synthesized") is not False
        or episode.get("success") is not True
        or labels
        != sum(
            row.get("ground_support_labels", 0)
            for row in episode.get("local_distinctions", [])
        )
    ):
        _fail("V97 exact receding episode changed")
    _check_query_pairing(episode)
    joint = 0
    dependencies = 0
    if acquisition_id is not None:
        for receipt in receipts:
            if type(receipt) is not dict or type(receipt.get("raw_state")) is not list:
                _fail("V97 abstract plan receipt changed")
            used, dependency = _check_plan(
                receipt.get("abstract_plan"),
                acquisition_id=acquisition_id,
                dependency_ids=dependency_ids,
            )
            joint += used
            dependencies += dependency
    elif receipts:
        _fail("V97 cold-direct arm acquired an abstract plan")
    return labels, len(actions), joint, dependencies


def _check_sequence(
    sequence: Any,
    *,
    seed: int,
    layout: Mapping[str, Any],
    targets: list[int],
    partial_labels: int,
    structural_prior_enabled: bool,
) -> dict[str, int]:
    _check_generic_id(sequence, "sequence_id", _SEQUENCE_DOMAIN)
    first = sequence.get("first_online_multi_residual_episode")
    later = sequence.get("later_persistent_episodes")
    if type(first) is not dict or type(later) is not list or len(later) != 2:
        _fail("V97 sequence episode inventory changed")
    rows = first.get("raw_local_transition_rows")
    base = first.get("final_multi_residual_acquisition")
    if type(rows) is not list or type(base) is not dict:
        _fail("V97 first-episode residual evidence changed")
    expected_acquisition = _derive_acquisition(
        rows,
        layout,
        targets,
        base,
        structural_prior_enabled=structural_prior_enabled,
    )
    acquisition = sequence.get("retained_post_dependency_acquisition")
    if acquisition != expected_acquisition:
        _fail("V97 post-dependency program did not independently reconstruct")
    dependency_ids = [
        row["candidate_id"]
        for row in acquisition["retrospective_post_dependency_candidates"]
    ]
    if (
        sequence.get("schema")
        != "acfqp.generic_persistent_post_dependency_sequence.v97"
        or sequence.get("family") != "COUPLED_EXCHANGE"
        or sequence.get("seed") != seed
        or sequence.get("episode_indices") != list(TARGET_EPISODES)
        or sequence.get("partial_acquisition_ground_support_labels_paid_once")
        != partial_labels
        or sequence.get("retained_post_dependency_candidate_count")
        != len(dependency_ids)
        or sequence.get("retained_joint_residual_candidate_count")
        != len(acquisition["compilable_candidates"])
        or sequence.get("successor_coordinate_dependency_jointly_compiled")
        is not True
        or sequence.get("post_dependency_program_is_fallible_action_ordering_heuristic")
        is not True
        or sequence.get("persistent_exact_overlay_exclusively_discharges_safety")
        is not True
        or sequence.get("complete_world_model_synthesized") is not False
        or sequence.get("official_execution_allowed") is not False
    ):
        _fail("V97 persistent dependency sequence boundary changed")
    _check_query_pairing(first)
    first_labels = first.get("local_ground_support_labels")
    if (
        type(first_labels) is not int
        or first_labels
        != sum(
            row.get("ground_support_labels", 0)
            for row in first.get("local_distinctions", [])
        )
    ):
        _fail("V97 first-episode label accounting changed")
    later_labels = 0
    steps = first.get("execution_steps")
    joint = 0
    dependencies = 0
    for episode, index in zip(later, TARGET_EPISODES[1:], strict=True):
        labels, episode_steps, episode_joint, episode_dependencies = _check_episode(
            episode,
            seed=seed,
            episode_index=index,
            acquisition_id=acquisition["multi_residual_acquisition_id"],
            dependency_ids=dependency_ids,
            wrapped=True,
        )
        if episode.get("new_certificate_labels_charged_this_episode") != labels:
            _fail("V97 later episode charged labels changed")
        later_labels += labels
        steps += episode_steps
        joint += episode_joint
        dependencies += episode_dependencies
    overlay = sequence.get("persistent_exact_overlay_rows")
    if (
        type(overlay) is not list
        or sequence.get("persistent_exact_overlay_sha256")
        != hashlib.sha256(canonical_json_bytes(overlay)).hexdigest()
        or sequence.get("persistent_exact_support_group_count")
        != _group_count(overlay)
        or sequence.get("later_query_ground_support_labels") != later_labels
        or sequence.get("later_joint_abstract_plan_receipt_count") != joint
        or sequence.get("later_post_dependency_abstract_plan_receipt_count")
        != dependencies
        or sequence.get("lifetime_target_ground_support_labels")
        != partial_labels + first_labels + later_labels
        or sequence.get("every_new_ground_query_followed_a_failed_certificate")
        is not True
    ):
        _fail("V97 persistent overlay or sequence accounting changed")
    return {
        "labels": sequence["lifetime_target_ground_support_labels"],
        "later_labels": later_labels,
        "steps": steps,
        "joint_receipts": joint,
        "dependency_receipts": dependencies,
        "dependency_candidates": len(dependency_ids),
    }


def _check_direct(sequence: Any, *, seed: int) -> tuple[int, int]:
    if (
        type(sequence) is not dict
        or sequence.get("schema") != "acfqp.generic_strict_cold_direct_sequence.v96"
        or sequence.get("family") != "COUPLED_EXCHANGE"
        or sequence.get("seed") != seed
        or sequence.get("episode_indices") != list(TARGET_EPISODES)
        or sequence.get("free_target_rows_received") is not False
    ):
        _fail("V97 cold-direct baseline changed")
    labels = 0
    steps = 0
    for episode, index in zip(sequence.get("episodes", []), TARGET_EPISODES, strict=True):
        episode_labels, episode_steps, _joint, _dependencies = _check_episode(
            episode,
            seed=seed,
            episode_index=index,
            acquisition_id=None,
            dependency_ids=[],
            wrapped=False,
        )
        if episode.get("total_target_ground_support_labels") != episode_labels:
            _fail("V97 cold-direct label accounting changed")
        labels += episode_labels
        steps += episode_steps
    if sequence.get("lifetime_target_ground_support_labels") != labels:
        _fail("V97 cold-direct lifetime accounting changed")
    return labels, steps


def _verify_campaign_document(document: Any) -> dict[str, Any]:
    _check_v97_id(
        document,
        "campaign_id",
        domains.CONSTRUCTION_K7_POST_DEPENDENCY_CAMPAIGN_V97_DOMAIN,
    )
    occurrences = document.get("target_occurrences")
    if (
        document.get("schema") != "acfqp.post_dependency_campaign.v97"
        or document.get("campaign_id") != CAMPAIGN_ID
        or document.get("preregistration_id") != PREREGISTRATION_ID
        or document.get("v96_campaign_id") != V96_CAMPAIGN_ID
        or document.get("v96_verification_id") != V96_VERIFICATION_ID
        or document.get("source_library_artifact_id")
        != SOURCE_LIBRARY_ARTIFACT_ID
        or type(occurrences) is not list
        or [row.get("seed") for row in occurrences] != list(TARGET_SEEDS)
    ):
        _fail("V97 campaign identity inventory changed")
    totals = {
        "meta": 0,
        "no_prior": 0,
        "direct": 0,
        "dependency_candidates": 0,
        "dependency_receipts": 0,
        "joint_receipts": 0,
        "later_labels": 0,
    }
    passing = 0
    for occurrence, seed in zip(occurrences, TARGET_SEEDS, strict=True):
        _check_v97_id(
            occurrence,
            "occurrence_id",
            domains.CONSTRUCTION_K7_POST_DEPENDENCY_OCCURRENCE_V97_DOMAIN,
        )
        partial = occurrence.get("common_partial_acquisition")
        candidate = partial.get("candidate") if type(partial) is dict else None
        layout = candidate.get("layout") if type(candidate) is dict else None
        targets = (
            candidate.get("unknown_residual_target_columns")
            if type(candidate) is dict
            else None
        )
        partial_labels = partial.get("ground_support_labels") if type(partial) is dict else None
        if (
            occurrence.get("schema") != "acfqp.post_dependency_occurrence.v97"
            or occurrence.get("family") != "COUPLED_EXCHANGE"
            or occurrence.get("episode_indices") != list(TARGET_EPISODES)
            or type(layout) is not dict
            or type(targets) is not list
            or type(partial_labels) is not int
            or occurrence.get(
                "same_partial_candidate_rows_residual_prior_and_first_episode_between_structure_arms"
            )
            is not True
            or occurrence["meta_prior_persistent_sequence"][
                "first_online_multi_residual_episode"
            ]
            != occurrence["no_structure_prior_persistent_sequence"][
                "first_online_multi_residual_episode"
            ]
            or occurrence.get("only_switched_variable")
            != "POST_DEPENDENCY_STRUCTURE_PRIOR_CODE_LENGTH"
            or occurrence.get("source_structure_prior_supplied_target_bindings")
            is not False
        ):
            _fail("V97 matched occurrence contract changed")
        meta = _check_sequence(
            occurrence["meta_prior_persistent_sequence"],
            seed=seed,
            layout=layout,
            targets=targets,
            partial_labels=partial_labels,
            structural_prior_enabled=True,
        )
        no_prior = _check_sequence(
            occurrence["no_structure_prior_persistent_sequence"],
            seed=seed,
            layout=layout,
            targets=targets,
            partial_labels=partial_labels,
            structural_prior_enabled=False,
        )
        direct, _direct_steps = _check_direct(
            occurrence["strict_cold_direct_sequence"], seed=seed
        )
        gate = occurrence.get("registered_gate")
        if (
            type(gate) is not dict
            or gate.get("passed") is not True
            or gate.get("meta_joint_successor_represents_every_residual_target")
            is not True
            or gate.get("meta_later_joint_abstract_plan_used") is not True
            or gate.get("meta_later_executed_action_matched_abstract_proposal")
            is not True
            or gate.get("meta_lifetime_labels_noninferior_to_no_structure_prior")
            is not True
            or gate.get("meta_lifetime_labels_strictly_below_cold_direct")
            is not True
            or gate.get("certificate_failure_only_query_discipline_clean") is not True
            or meta["labels"] > no_prior["labels"]
            or meta["labels"] >= direct
        ):
            _fail("V97 occurrence Gate changed")
        passing += 1
        totals["meta"] += meta["labels"]
        totals["no_prior"] += no_prior["labels"]
        totals["direct"] += direct
        totals["dependency_candidates"] += meta["dependency_candidates"]
        totals["dependency_receipts"] += meta["dependency_receipts"]
        totals["joint_receipts"] += meta["joint_receipts"]
        totals["later_labels"] += meta["later_labels"]
    accounting = document.get("accounting")
    gate = document.get("registered_gate")
    if (
        totals
        != {
            "meta": 210,
            "no_prior": 210,
            "direct": 387,
            "dependency_candidates": 2,
            "dependency_receipts": 48,
            "joint_receipts": 96,
            "later_labels": 6,
        }
        or type(accounting) is not dict
        or accounting.get("meta_prior_lifetime_target_labels") != totals["meta"]
        or accounting.get("no_structure_prior_lifetime_target_labels")
        != totals["no_prior"]
        or accounting.get("strict_cold_direct_lifetime_target_labels")
        != totals["direct"]
        or accounting.get("strict_minus_meta_prior_lifetime_target_labels")
        != totals["direct"] - totals["meta"]
        or accounting.get("later_post_dependency_abstract_plan_receipt_count")
        != totals["dependency_receipts"]
        or accounting.get("later_joint_abstract_plan_receipt_count")
        != totals["joint_receipts"]
        or accounting.get(
            "source_labels_target_labels_execution_steps_derivation_and_planning_compute_separate"
        )
        is not True
        or accounting.get("scalar_cost_aggregation_performed") is not False
        or type(gate) is not dict
        or gate.get("completed_passing_target_occurrence_count") != passing
        or passing != len(TARGET_SEEDS)
        or gate.get(
            "at_least_one_fresh_target_discovered_post_dependency_program"
        )
        is not True
        or gate.get(
            "at_least_one_fresh_target_used_post_dependency_abstract_plan"
        )
        is not True
        or gate.get("every_target_used_joint_abstract_plan") is not True
        or gate.get("aggregate_meta_labels_noninferior_to_no_structure_prior")
        is not True
        or gate.get("aggregate_meta_labels_strictly_below_cold_direct") is not True
        or gate.get("passed") is not True
        or document.get(
            "successor_coordinate_dependency_synthesized_and_jointly_compiled"
        )
        is not True
        or document.get("persistent_exact_overlay_reduced_repeated_query_sample_tax")
        is not True
        or document.get(
            "structural_prior_sample_tax_advantage_over_same_synthesizer_verified"
        )
        is not False
        or document.get("producer_free_verification_present") is not False
        or document.get("complete_world_model_synthesized") is not False
        or document.get("global_exact_dynamics_claimed") is not False
        or document.get("arbitrary_domain_transfer_claimed") is not False
        or document.get("official_execution_allowed") is not False
        or document.get("official_scalar_cost") is not None
        or document.get("official_N_break_even") is not None
        or document.get("WORKLOAD_ECONOMICS_GATE") != "NOT_RUN"
        or document.get("COUNTER_COMPLETENESS_GATE") != "NOT_RUN"
    ):
        _fail("V97 campaign Gate, accounting, or claim boundary changed")
    return {
        "schema": "acfqp.post_dependency_verification.v97",
        "campaign_id": CAMPAIGN_ID,
        "preregistration_id": PREREGISTRATION_ID,
        "source_library_artifact_id": SOURCE_LIBRARY_ARTIFACT_ID,
        "verification_status": "REGISTERED_POST_DEPENDENCY_JOINT_SUCCESSOR_VERIFIED",
        "verified_accounting": {
            "meta_prior_lifetime_target_labels": totals["meta"],
            "no_structure_prior_lifetime_target_labels": totals["no_prior"],
            "strict_cold_direct_lifetime_target_labels": totals["direct"],
            "later_certificate_local_ground_labels": totals["later_labels"],
            "fresh_post_dependency_candidate_count": totals[
                "dependency_candidates"
            ],
            "post_dependency_abstract_plan_receipt_count": totals[
                "dependency_receipts"
            ],
            "joint_abstract_plan_receipt_count": totals["joint_receipts"],
            "all_axes_separate": True,
        },
        "post_dependency_program_rederived_from_raw_successor_differences": True,
        "held_out_plan_content_identities_replayed": True,
        "certificate_failure_only_local_recovery_verified": True,
        "structural_prior_sample_tax_advantage_over_same_synthesizer_verified": False,
        "complete_world_model_synthesized": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }


def verify_post_dependency_campaign_bytes_v97(raw: bytes) -> dict[str, Any]:
    if (
        type(raw) is not bytes
        or len(raw) != CAMPAIGN_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != CAMPAIGN_SHA256
    ):
        _fail("V97 campaign bytes differ from the frozen campaign")
    document = loads_canonical_json(raw)
    if canonical_json_bytes(document) != raw:
        _fail("V97 campaign bytes are not canonical")
    return _verify_campaign_document(document)


def freeze_post_dependency_verification_v97(raw: bytes) -> bytes:
    payload = verify_post_dependency_campaign_bytes_v97(raw)
    document = {
        **payload,
        "verification_id": domains.extension_content_id_v97(
            domains.CONSTRUCTION_K7_POST_DEPENDENCY_VERIFICATION_V97_DOMAIN,
            payload,
        ),
    }
    result = canonical_json_bytes(document)
    if VERIFICATION_ID != "0" * 64 and (
        document["verification_id"] != VERIFICATION_ID
        or len(result) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(result).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("V97 frozen verification changed")
    return result


__all__ = (
    "VERIFICATION_ID",
    "freeze_post_dependency_verification_v97",
    "verify_post_dependency_campaign_bytes_v97",
)
