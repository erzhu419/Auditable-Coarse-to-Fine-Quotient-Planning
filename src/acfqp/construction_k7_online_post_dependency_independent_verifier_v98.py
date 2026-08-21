"""Producer-free verification of the frozen V98 activation campaign."""

from __future__ import annotations

import copy
import hashlib
import math
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v98 as domains
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "0c81232368a76e987b9921e3312fa70653eb5cdbf18e077c8c482aa7bd827f6b"
CAMPAIGN_BYTE_COUNT = 2_818_317
CAMPAIGN_SHA256 = "102a3cbd116d09b793ecce9e3cb7172ea1044ca1d9cd5ba29186cd78b683a8c3"
PREREGISTRATION_ID = "81b87ce48c3b4159e4e0e869228dbb34b02d06adf1b5ad7c2359ef2c8fa0e452"
SOURCE_LIBRARY_ARTIFACT_ID = "4f0a9592f7d6ba2d7683e9328f76dbd01bd18a3a47a062ea764f7a20012caeba"
STRUCTURE_LIBRARY_ID = "96c18874b88ec9422adf7fc84e9eef8414378a6abe5a0322d933ec51e62c5be6"
V97_CAMPAIGN_ID = "b132245b0827898cb497232ed82b911fc17bebc4a30e981a7b080895abc8bf3e"
V97_VERIFICATION_ID = "341b170d9ec3c70ae4ba954f84651cc216dad980cc7e783872a77b33aaae9dac"
TARGET_SEEDS = (1_003_101, 1_003_102, 1_003_103, 1_003_104)
TARGET_EPISODES = (61, 62, 63)
VERIFICATION_ID = "f7b01805fb8b0192dee4137e416313eb05e9626925a2e49609cd70079f120dfb"
EXPECTED_CANONICAL_BYTE_COUNT = 1_483
EXPECTED_CANONICAL_SHA256 = "31db5428f98cf146f6e689874a1f807c7f87832de59391c3a63c5f95c5001efd"

_SEQUENCE_DOMAIN = b"acfqp:generic-persistent-online-post-dependency-sequence:v98\x00"
_ONLINE_EPISODE_DOMAIN = b"acfqp:online-post-dependency-certificate-episode:v98\x00"
_PRELOADED_EPISODE_DOMAIN = b"acfqp:generic-preloaded-certificate-receding-episode:v74\x00"
_BASE_ACQUISITION_DOMAIN = b"acfqp:generic-multi-residual-acquisition:v24\x00"
_DEPENDENCY_CANDIDATE_DOMAIN = b"acfqp:post-dependency-residual-candidate:v97\x00"
_DEPENDENCY_ACQUISITION_DOMAIN = b"acfqp:post-dependency-multi-residual-acquisition:v97\x00"
_ABSTRACT_PLAN_DOMAIN = b"acfqp:post-dependency-abstract-plan:v97\x00"


class ConstructionK7OnlinePostDependencyIndependentVerifierV98Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7OnlinePostDependencyIndependentVerifierV98Error(message)


def _generic_id(domain: bytes, payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(domain + canonical_json_bytes(payload)).hexdigest()


def _check_generic_id(document: Any, key: str, domain: bytes) -> None:
    if type(document) is not dict:
        _fail(f"V98 {key} document type changed")
    payload = {name: value for name, value in document.items() if name != key}
    if document.get(key) != _generic_id(domain, payload):
        _fail(f"V98 {key} content identity changed")


def _check_v98_id(document: Any, key: str, domain: str) -> None:
    if type(document) is not dict:
        _fail(f"V98 {key} document type changed")
    payload = {name: value for name, value in document.items() if name != key}
    if document.get(key) != domains.extension_content_id_v98(domain, payload):
        _fail(f"V98 {key} content identity changed")


def _group_count(rows: Any) -> int:
    if type(rows) is not list:
        _fail("V98 transition row inventory changed")
    groups = set()
    for row in rows:
        action = row.get("selected_action") if type(row) is dict else None
        if (
            type(row) is not dict
            or type(row.get("pre_vector")) is not list
            or type(row.get("post_vector")) is not list
            or type(action) is not dict
            or type(action.get("action_key")) is not int
        ):
            _fail("V98 transition row schema changed")
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
    if type(order) is not list or not rows:
        _fail("V98 dependency alignment or row pool changed")
    posts = []
    for row in rows:
        post = row.get("post_vector") if type(row) is dict else None
        if type(post) is not list or sorted(order) != list(range(len(post))):
            _fail("V98 dependency raw post changed")
        posts.append([post[index] for index in order])
    calibrated = copy.deepcopy(base.get("compilable_candidates"))
    if type(calibrated) is not list:
        _fail("V98 calibrated residual candidates changed")
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


def _projection(acquisition: Mapping[str, Any]) -> list[dict[str, Any]]:
    result = []
    for candidate in acquisition["compilable_candidates"]:
        if candidate.get("candidate_kind") == "POST_DEPENDENCY_THREE_BAND_FINITE_SUPPORT":
            result.append(
                {
                    "kind": candidate["candidate_kind"],
                    "target_column": candidate["target_column"],
                    "driver_post_column": candidate["driver_post_column"],
                    "lower_inclusive_threshold": candidate[
                        "lower_inclusive_threshold"
                    ],
                    "upper_inclusive_threshold": candidate[
                        "upper_inclusive_threshold"
                    ],
                    "leaf_supports": candidate["leaf_supports"],
                }
            )
        else:
            result.append(
                {
                    "kind": "CALIBRATED_PREDECESSOR",
                    "target_column": candidate["target_column"],
                    "candidate_id": candidate["candidate_id"],
                }
            )
    return result


def _check_pairing(episode: Mapping[str, Any]) -> None:
    failures = episode.get("failed_certificates")
    distinctions = episode.get("local_distinctions")
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
        _fail("V98 certificate-failure-only query pairing changed")


def _check_history(first: Mapping[str, Any]) -> tuple[int | None, int, int]:
    history = first.get("adaptive_stopping_history")
    distinctions = first.get("local_distinctions")
    rows = []
    running_labels = 0
    history_offset = 0
    previous_sha = None
    previous_activated = False
    candidate_changes = 0
    active_revisions = 0
    issued_at = None
    first_activation = None
    if type(history) is not list or type(distinctions) is not list:
        _fail("V98 adaptive stopping evidence changed")
    for distinction in distinctions:
        labels = distinction.get("ground_support_labels")
        if type(labels) is not int or labels != 1:
            _fail("V98 distinction label accounting changed")
        running_labels += labels
        batch = distinction.get("raw_transition_rows")
        if batch is None:
            continue
        if type(batch) is not list or history_offset >= len(history):
            _fail("V98 model update batch changed")
        rows.extend(batch)
        item = history[history_offset]
        history_offset += 1
        evidence_labels = _group_count(rows)
        dependency_count = item.get("dependency_candidate_count")
        complete = item.get("all_residual_targets_have_compilable_proposals")
        required = (
            6
            if complete is True and dependency_count == 0
            else 6 + first["structure_prior_code_units"]
        )
        activated = complete is True and evidence_labels >= required
        projection_sha = item.get("candidate_projection_sha256")
        if (
            item.get("ground_support_labels") != running_labels
            or item.get("model_evidence_ground_support_labels") != evidence_labels
            or item.get("required_model_evidence_ground_support_labels") != required
            or item.get("activated") is not activated
            or type(projection_sha) is not str
            or len(projection_sha) != 64
            or type(dependency_count) is not int
            or type(complete) is not bool
        ):
            _fail("V98 MDL/confidence stopping rule did not replay")
        if previous_sha != projection_sha:
            if previous_sha is not None:
                candidate_changes += 1
                if previous_activated:
                    active_revisions += 1
            issued_at = running_labels
        if item.get("candidate_issued_at_label") != issued_at:
            _fail("V98 candidate issuance history changed")
        if activated and first_activation is None:
            first_activation = running_labels
        previous_sha = projection_sha
        previous_activated = activated
    if history_offset != len(history):
        _fail("V98 adaptive stopping history cardinality changed")
    return first_activation, candidate_changes, active_revisions


def _check_first_episode(
    first: Any,
    *,
    seed: int,
    structural_prior_enabled: bool,
    partial: Mapping[str, Any],
) -> tuple[int, int, int]:
    _check_generic_id(first, "episode_id", _ONLINE_EPISODE_DOMAIN)
    expected_arm = (
        "POST_DEPENDENCY_STRUCTURE_META_PRIOR_ON"
        if structural_prior_enabled
        else "STRICT_NO_POST_DEPENDENCY_STRUCTURE_META_PRIOR"
    )
    expected_units = 1 if structural_prior_enabled else 8
    rows = first.get("raw_local_transition_rows")
    final = first.get("final_post_dependency_acquisition")
    active = first.get("active_post_dependency_acquisition")
    if (
        first.get("schema")
        != "acfqp.online_post_dependency_certificate_episode.v98"
        or first.get("family") != "COUPLED_EXCHANGE"
        or first.get("seed") != seed
        or first.get("episode_index") != TARGET_EPISODES[0]
        or first.get("arm") != expected_arm
        or first.get("structure_prior_code_units") != expected_units
        or first.get("confidence_penalty_units") != 6
        or first.get("required_post_dependency_model_evidence_labels")
        != 6 + expected_units
        or first.get("same_synthesizer_and_stopping_rule_between_prior_arms")
        is not True
        or first.get("only_switched_variable")
        != "POST_DEPENDENCY_STRUCTURE_DESCRIPTION_CODE_UNITS"
        or first.get(
            "activation_is_fallible_mdl_proposal_not_exact_dynamics_authority"
        )
        is not True
        or first.get("all_ground_queries_followed_failed_certificates") is not True
        or first.get("query_local_exact_overlay_exclusively_used_for_safety")
        is not True
        or first.get("abstract_model_used_only_for_action_ordering") is not True
        or first.get("complete_world_model_synthesized") is not False
        or first.get("success") is not True
        or type(rows) is not list
        or not rows
        or type(final) is not dict
    ):
        _fail("V98 first online episode boundary changed")
    _check_pairing(first)
    activation, changes, revisions = _check_history(first)
    base = final.get("base_multi_residual_acquisition")
    candidate = partial.get("candidate")
    if type(candidate) is not dict:
        _fail("V98 partial candidate evidence changed")
    derived = _derive_acquisition(
        rows,
        candidate["layout"],
        candidate["unknown_residual_target_columns"],
        base,
        structural_prior_enabled=structural_prior_enabled,
    )
    if derived != final:
        _fail("V98 final post-dependency model did not rederive from raw successors")
    final_history = first["adaptive_stopping_history"][-1]
    final_projection_sha = hashlib.sha256(
        canonical_json_bytes(_projection(final))
    ).hexdigest()
    if (
        final_history.get("candidate_projection_sha256") != final_projection_sha
        or first.get("candidate_activated_at_ground_support_label") != activation
        or first.get("candidate_change_count") != changes
        or first.get("active_candidate_revision_count") != revisions
        or first.get("candidate_invalidation_count") != 0
        or active != (final if final_history.get("activated") is True else None)
        or first.get("local_ground_support_labels")
        != sum(row["ground_support_labels"] for row in first["local_distinctions"])
        or first.get("queried_state_action_count") != _group_count(rows)
    ):
        _fail("V98 final activation projection or accounting changed")
    return (
        first["local_ground_support_labels"],
        activation,
        len(final["retrospective_post_dependency_candidates"]),
    )


def _check_plan(plan: Any, acquisition_id: str) -> tuple[bool, bool]:
    if type(plan) is not dict:
        _fail("V98 abstract plan type changed")
    if plan.get("persistent_online_model_used") is not True:
        if (
            plan.get("schema")
            != "acfqp.generic_persistent_online_partial_fallback_plan.v98"
            or plan.get("persistent_partial_fallback_used") is not True
            or plan.get("persistent_post_dependency_program_used") is not False
            or plan.get("abstract_plan_used_as_safety_authority") is not False
        ):
            _fail("V98 partial fallback changed")
        return False, False
    extras = {
        "persistent_online_model_used",
        "persistent_post_dependency_program_used",
        "persistent_partial_fallback_used",
    }
    payload = {
        key: value
        for key, value in plan.items()
        if key != "abstract_plan_id" and key not in extras
    }
    dependency_ids = plan.get("dependency_candidate_ids")
    if (
        plan.get("schema") != "acfqp.post_dependency_abstract_plan.v97"
        or plan.get("abstract_plan_id") != _generic_id(_ABSTRACT_PLAN_DOMAIN, payload)
        or plan.get("multi_residual_acquisition_id") != acquisition_id
        or type(dependency_ids) is not list
        or plan.get("persistent_post_dependency_program_used")
        is not bool(dependency_ids)
        or plan.get("persistent_partial_fallback_used") is not False
        or plan.get("ground_transition_accessed_during_abstract_search") is not False
        or plan.get("abstract_plan_used_as_safety_authority") is not False
        or plan.get("complete_world_model_claimed") is not False
    ):
        _fail("V98 persistent abstract plan changed")
    return True, bool(dependency_ids)


def _check_later_episode(
    episode: Any,
    *,
    seed: int,
    episode_index: int,
    acquisition_id: str,
) -> tuple[int, int, int]:
    if type(episode) is not dict:
        _fail("V98 later episode type changed")
    wrapper_fields = {
        "new_certificate_labels_charged_this_episode",
        "paid_certificate_labels_cumulative",
        "persistent_exact_support_group_count",
    }
    episode_payload = {
        key: value
        for key, value in episode.items()
        if key != "episode_id" and key not in wrapper_fields
    }
    if episode.get("episode_id") != _generic_id(
        _PRELOADED_EPISODE_DOMAIN, episode_payload
    ):
        _fail("V98 later episode content identity changed")
    if (
        episode.get("schema")
        != "acfqp.generic_preloaded_certificate_receding_episode.v74"
        or episode.get("family") != "COUPLED_EXCHANGE"
        or episode.get("seed") != seed
        or episode.get("episode_index") != episode_index
        or episode.get("arm") != "PERSISTENT_ONLINE_POST_DEPENDENCY_TRANSFER"
        or episode.get("preloaded_exact_rows_reused_without_reacquisition") is not True
        or episode.get("query_local_exact_overlay_exclusively_used_for_safety")
        is not True
        or episode.get("model_or_alignment_used_as_safety_authority") is not False
        or episode.get("target_episode_outcomes_used_to_refit_model_or_alignment")
        is not False
        or episode.get("same_exact_engine_implementation_for_transfer_and_strict_arms")
        is not True
        or episode.get("complete_world_model_synthesized") is not False
        or episode.get("success") is not True
        or episode.get("new_certificate_labels_charged_this_episode")
        != episode.get("incremental_certificate_local_ground_support_labels")
    ):
        _fail("V98 later persistent episode changed")
    _check_pairing(episode)
    online = 0
    dependency = 0
    receipts = episode.get("abstract_plan_receipts")
    if type(receipts) is not list:
        _fail("V98 abstract receipt inventory changed")
    for receipt in receipts:
        if type(receipt) is not dict or type(receipt.get("raw_state")) is not list:
            _fail("V98 abstract receipt changed")
        used, used_dependency = _check_plan(
            receipt.get("abstract_plan"), acquisition_id
        )
        online += used
        dependency += used_dependency
    if (
        episode.get("abstract_plan_success_count") != len(receipts)
        or episode.get("execution_action_matches_abstract_proposal_count")
        != sum(episode.get("execution_action_matches_abstract_proposal", []))
    ):
        _fail("V98 later planning accounting changed")
    return (
        episode["incremental_certificate_local_ground_support_labels"],
        online,
        dependency,
    )


def _check_sequence(
    sequence: Any,
    *,
    seed: int,
    structural_prior_enabled: bool,
    partial: Mapping[str, Any],
) -> tuple[int, int, int, int, int]:
    _check_generic_id(sequence, "sequence_id", _SEQUENCE_DOMAIN)
    expected_arm = (
        "POST_DEPENDENCY_STRUCTURE_META_PRIOR_ON"
        if structural_prior_enabled
        else "STRICT_NO_POST_DEPENDENCY_STRUCTURE_META_PRIOR"
    )
    first = sequence.get("first_online_post_dependency_episode")
    later = sequence.get("later_persistent_episodes")
    retained = sequence.get("retained_active_post_dependency_acquisition")
    rows = sequence.get("persistent_exact_overlay_rows")
    if (
        sequence.get("schema")
        != "acfqp.generic_persistent_online_post_dependency_sequence.v98"
        or sequence.get("family") != "COUPLED_EXCHANGE"
        or sequence.get("seed") != seed
        or sequence.get("episode_indices") != list(TARGET_EPISODES)
        or sequence.get("arm") != expected_arm
        or type(later) is not list
        or len(later) != len(TARGET_EPISODES) - 1
        or type(retained) is not dict
        or type(rows) is not list
        or sequence.get("persistent_exact_overlay_sha256")
        != hashlib.sha256(canonical_json_bytes(rows)).hexdigest()
        or sequence.get("persistent_exact_support_group_count") != _group_count(rows)
        or sequence.get("post_dependency_model_is_fallible_action_ordering_heuristic")
        is not True
        or sequence.get("persistent_exact_overlay_exclusively_discharges_safety")
        is not True
        or sequence.get("complete_world_model_synthesized") is not False
        or sequence.get("official_execution_allowed") is not False
    ):
        _fail("V98 persistent sequence boundary changed")
    first_labels, activation, dependency_count = _check_first_episode(
        first,
        seed=seed,
        structural_prior_enabled=structural_prior_enabled,
        partial=partial,
    )
    if retained != first["active_post_dependency_acquisition"]:
        _fail("V98 retained online model changed")
    acquisition_id = retained["multi_residual_acquisition_id"]
    later_labels = 0
    online_receipts = 0
    dependency_receipts = 0
    for episode, index in zip(later, TARGET_EPISODES[1:], strict=True):
        labels, online, dependency = _check_later_episode(
            episode,
            seed=seed,
            episode_index=index,
            acquisition_id=acquisition_id,
        )
        later_labels += labels
        online_receipts += online
        dependency_receipts += dependency
    partial_labels = partial.get("ground_support_labels")
    right_censored = activation if type(activation) is int else first_labels + 1
    if (
        type(partial_labels) is not int
        or sequence.get("partial_acquisition_ground_support_labels_paid_once")
        != partial_labels
        or sequence.get("post_dependency_model_activation_observed")
        is not (type(activation) is int)
        or sequence.get("post_dependency_model_activation_local_ground_support_label")
        != activation
        or sequence.get("post_dependency_model_activation_label_with_right_censoring")
        != right_censored
        or sequence.get(
            "target_model_activation_ground_support_labels_with_right_censoring"
        )
        != partial_labels + right_censored
        or sequence.get("later_online_model_abstract_plan_receipt_count")
        != online_receipts
        or sequence.get("later_post_dependency_abstract_plan_receipt_count")
        != dependency_receipts
        or sequence.get("later_query_ground_support_labels") != later_labels
        or sequence.get("certificate_ground_support_labels_paid_once")
        != first_labels + later_labels
        or sequence.get("lifetime_target_ground_support_labels")
        != partial_labels + first_labels + later_labels
        or sequence.get("every_new_ground_query_followed_a_failed_certificate")
        is not True
    ):
        _fail("V98 persistent activation or sample accounting changed")
    return (
        sequence["lifetime_target_ground_support_labels"],
        sequence["target_model_activation_ground_support_labels_with_right_censoring"],
        dependency_count,
        online_receipts,
        dependency_receipts,
    )


def _verify_campaign_document(document: Any) -> dict[str, Any]:
    _check_v98_id(
        document,
        "campaign_id",
        domains.CONSTRUCTION_K7_ONLINE_POST_DEPENDENCY_CAMPAIGN_V98_DOMAIN,
    )
    occurrences = document.get("target_occurrences")
    if (
        document.get("schema") != "acfqp.online_post_dependency_campaign.v98"
        or document.get("campaign_id") != CAMPAIGN_ID
        or document.get("preregistration_id") != PREREGISTRATION_ID
        or document.get("v97_campaign_id") != V97_CAMPAIGN_ID
        or document.get("v97_verification_id") != V97_VERIFICATION_ID
        or document.get("source_library_artifact_id") != SOURCE_LIBRARY_ARTIFACT_ID
        or type(occurrences) is not list
        or len(occurrences) != len(TARGET_SEEDS)
        or [row.get("seed") for row in occurrences] != list(TARGET_SEEDS)
    ):
        _fail("V98 campaign identity inventory changed")
    totals = {
        "meta": 0,
        "no_prior": 0,
        "direct": 0,
        "meta_activation": 0,
        "no_prior_activation": 0,
        "dependency_occurrences": 0,
        "dependency_receipts": 0,
    }
    for occurrence, seed in zip(occurrences, TARGET_SEEDS, strict=True):
        _check_v98_id(
            occurrence,
            "occurrence_id",
            domains.CONSTRUCTION_K7_ONLINE_POST_DEPENDENCY_OCCURRENCE_V98_DOMAIN,
        )
        partial = occurrence.get("common_partial_acquisition")
        if (
            occurrence.get("schema") != "acfqp.online_post_dependency_occurrence.v98"
            or occurrence.get("family") != "COUPLED_EXCHANGE"
            or occurrence.get("episode_indices") != list(TARGET_EPISODES)
            or type(partial) is not dict
            or occurrence.get(
                "same_partial_candidate_rows_residual_prior_and_outcome_schedule_between_arms"
            )
            is not True
            or occurrence.get(
                "same_synthesizer_and_mdl_confidence_stopping_rule_between_arms"
            )
            is not True
            or occurrence.get("only_switched_variable")
            != "POST_DEPENDENCY_STRUCTURE_DESCRIPTION_CODE_UNITS"
            or occurrence.get("model_activation_is_fallible_proposal_not_safety_authority")
            is not True
            or occurrence.get("persistent_exact_overlay_exclusively_used_for_safety")
            is not True
            or occurrence.get("source_structure_prior_supplied_target_bindings")
            is not False
            or occurrence.get("complete_world_model_synthesized") is not False
            or occurrence.get("official_execution_allowed") is not False
        ):
            _fail("V98 matched occurrence boundary changed")
        meta, meta_activation, dependency_count, online_receipts, dep_receipts = (
            _check_sequence(
                occurrence.get("meta_prior_persistent_sequence"),
                seed=seed,
                structural_prior_enabled=True,
                partial=partial,
            )
        )
        no_prior, no_prior_activation, _no_dep, _no_online, _no_dep_receipts = (
            _check_sequence(
                occurrence.get("no_structure_prior_persistent_sequence"),
                seed=seed,
                structural_prior_enabled=False,
                partial=partial,
            )
        )
        direct_sequence = occurrence.get("strict_cold_direct_sequence")
        direct_episodes = (
            direct_sequence.get("episodes")
            if type(direct_sequence) is dict
            else None
        )
        if (
            type(direct_episodes) is not list
            or len(direct_episodes) != len(TARGET_EPISODES)
            or direct_sequence.get("episode_indices") != list(TARGET_EPISODES)
            or direct_sequence.get("free_target_rows_received") is not False
            or direct_sequence.get("lifetime_target_ground_support_labels")
            != sum(
                row["total_target_ground_support_labels"]
                for row in direct_episodes
            )
        ):
            _fail("V98 strict cold-direct accounting changed")
        for direct_episode, direct_index in zip(
            direct_episodes, TARGET_EPISODES, strict=True
        ):
            _check_generic_id(
                direct_episode, "episode_id", _PRELOADED_EPISODE_DOMAIN
            )
            _check_pairing(direct_episode)
            if (
                direct_episode.get("arm") != "STRICT_COLD_DIRECT_GROUND"
                or direct_episode.get("seed") != seed
                or direct_episode.get("episode_index") != direct_index
                or direct_episode.get("preloaded_acquisition_ground_support_labels")
                != 0
                or direct_episode.get("abstract_plan_receipts") != []
                or direct_episode.get("incremental_certificate_local_ground_support_labels")
                != sum(
                    row["ground_support_labels"]
                    for row in direct_episode["local_distinctions"]
                )
                or direct_episode.get("total_target_ground_support_labels")
                != direct_episode.get(
                    "incremental_certificate_local_ground_support_labels"
                )
            ):
                _fail("V98 strict cold-direct episode changed")
        direct = direct_sequence["lifetime_target_ground_support_labels"]
        expected_advantage = dependency_count > 0 and meta_activation < no_prior_activation
        gate = occurrence.get("registered_gate")
        accounting = occurrence.get("accounting")
        if (
            occurrence.get("post_dependency_candidate_count") != dependency_count
            or occurrence.get("dependency_occurrence_has_strict_activation_advantage")
            is not expected_advantage
            or type(gate) is not dict
            or gate.get("passed") is not True
            or gate.get("online_model_activated_in_meta_arm") is not True
            or gate.get("retained_model_covers_every_residual_target") is not True
            or gate.get("later_persistent_abstract_planning_used")
            is not bool(online_receipts)
            or gate.get("meta_activation_not_later_than_no_prior")
            is not (meta_activation <= no_prior_activation)
            or gate.get("dependency_occurrence_has_strict_activation_advantage")
            is not (expected_advantage if dependency_count > 0 else True)
            or gate.get("meta_lifetime_labels_noninferior_to_no_prior")
            is not (meta <= no_prior)
            or gate.get("meta_lifetime_labels_strictly_below_cold_direct")
            is not (meta < direct)
            or gate.get("certificate_failure_only_query_discipline_clean") is not True
            or type(accounting) is not dict
            or accounting.get("meta_model_activation_target_labels_with_right_censoring")
            != meta_activation
            or accounting.get("no_prior_model_activation_target_labels_with_right_censoring")
            != no_prior_activation
            or accounting.get("meta_lifetime_target_labels") != meta
            or accounting.get("no_prior_lifetime_target_labels") != no_prior
            or accounting.get("strict_cold_direct_lifetime_target_labels") != direct
            or accounting.get(
                "sample_labels_execution_steps_synthesis_and_planning_compute_separate"
            )
            is not True
            or accounting.get("scalar_cost_aggregation_performed") is not False
        ):
            _fail("V98 occurrence Gate or accounting changed")
        totals["meta"] += meta
        totals["no_prior"] += no_prior
        totals["direct"] += direct
        totals["meta_activation"] += meta_activation
        totals["no_prior_activation"] += no_prior_activation
        totals["dependency_occurrences"] += dependency_count > 0
        totals["dependency_receipts"] += dep_receipts
    accounting = document.get("accounting")
    gate = document.get("registered_gate")
    if (
        type(accounting) is not dict
        or accounting.get("meta_model_activation_target_labels_with_right_censoring")
        != totals["meta_activation"]
        or accounting.get("no_prior_model_activation_target_labels_with_right_censoring")
        != totals["no_prior_activation"]
        or accounting.get("meta_lifetime_target_labels") != totals["meta"]
        or accounting.get("no_prior_lifetime_target_labels") != totals["no_prior"]
        or accounting.get("strict_cold_direct_lifetime_target_labels")
        != totals["direct"]
        or accounting.get("target_labels_execution_steps_synthesis_and_planning_compute_separate")
        is not True
        or accounting.get("scalar_cost_aggregation_performed") is not False
        or (
            totals["meta_activation"],
            totals["no_prior_activation"],
            totals["meta"],
            totals["no_prior"],
            totals["direct"],
        )
        != (178, 206, 278, 278, 441)
        or type(gate) is not dict
        or gate.get("required_target_occurrence_count") != 4
        or gate.get("passed_target_occurrence_count") != 4
        or gate.get("post_dependency_occurrence_count")
        != totals["dependency_occurrences"]
        or gate.get("aggregate_model_activation_sample_tax_strictly_reduced")
        is not True
        or gate.get("all_dependency_occurrences_strictly_reduce_activation_labels")
        is not True
        or gate.get("meta_lifetime_task_labels_noninferior_to_no_prior") is not True
        or gate.get("meta_lifetime_task_labels_strictly_below_cold_direct") is not True
        or gate.get("passed") is not True
        or document.get(
            "same_synthesizer_stopping_rule_partial_rows_and_outcome_schedule_matched"
        )
        is not True
        or document.get("only_structure_description_code_units_switched") is not True
        or document.get(
            "structural_prior_model_activation_sample_tax_advantage_verified"
        )
        is not True
        or document.get(
            "structural_prior_total_task_label_advantage_over_same_synthesizer_verified"
        )
        is not False
        or document.get(
            "persistent_abstract_planning_with_certificate_failure_only_local_recovery_verified"
        )
        is not True
        or document.get("complete_world_model_synthesized") is not False
        or document.get("global_exact_dynamics_claimed") is not False
        or document.get("arbitrary_domain_transfer_claimed") is not False
        or document.get("official_execution_allowed") is not False
        or document.get("official_scalar_cost") is not None
        or document.get("official_N_break_even") is not None
        or document.get("WORKLOAD_ECONOMICS_GATE") != "NOT_RUN"
        or document.get("COUNTER_COMPLETENESS_GATE") != "NOT_RUN"
    ):
        _fail("V98 aggregate Gate, accounting, or claim boundary changed")
    return {
        "schema": "acfqp.online_post_dependency_verification.v98",
        "campaign_id": CAMPAIGN_ID,
        "preregistration_id": PREREGISTRATION_ID,
        "source_library_artifact_id": SOURCE_LIBRARY_ARTIFACT_ID,
        "verification_status": "REGISTERED_ONLINE_POST_DEPENDENCY_ACTIVATION_GATE_VERIFIED",
        "verified_accounting": {
            "meta_model_activation_target_labels_with_right_censoring": totals[
                "meta_activation"
            ],
            "no_prior_model_activation_target_labels_with_right_censoring": totals[
                "no_prior_activation"
            ],
            "activation_label_reduction": (
                totals["no_prior_activation"] - totals["meta_activation"]
            ),
            "meta_lifetime_target_labels": totals["meta"],
            "no_prior_lifetime_target_labels": totals["no_prior"],
            "strict_cold_direct_lifetime_target_labels": totals["direct"],
            "post_dependency_occurrence_count": totals["dependency_occurrences"],
            "post_dependency_abstract_plan_receipt_count": totals[
                "dependency_receipts"
            ],
            "all_axes_separate": True,
        },
        "post_dependency_program_rederived_from_raw_successor_differences": True,
        "mdl_confidence_activation_rule_replayed_from_query_order": True,
        "held_out_content_identities_replayed": True,
        "certificate_failure_only_local_recovery_verified": True,
        "structural_prior_model_activation_sample_tax_advantage_verified": True,
        "structural_prior_total_task_label_advantage_verified": False,
        "complete_world_model_synthesized": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }


def verify_online_post_dependency_campaign_bytes_v98(raw: bytes) -> dict[str, Any]:
    if (
        type(raw) is not bytes
        or len(raw) != CAMPAIGN_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != CAMPAIGN_SHA256
    ):
        _fail("V98 campaign bytes differ from the frozen campaign")
    document = loads_canonical_json(raw)
    if canonical_json_bytes(document) != raw:
        _fail("V98 campaign bytes are not canonical")
    return _verify_campaign_document(document)


def freeze_online_post_dependency_verification_v98(raw: bytes) -> bytes:
    payload = verify_online_post_dependency_campaign_bytes_v98(raw)
    document = {
        **payload,
        "verification_id": domains.extension_content_id_v98(
            domains.CONSTRUCTION_K7_ONLINE_POST_DEPENDENCY_VERIFICATION_V98_DOMAIN,
            payload,
        ),
    }
    result = canonical_json_bytes(document)
    if VERIFICATION_ID != "0" * 64 and (
        document["verification_id"] != VERIFICATION_ID
        or len(result) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(result).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("V98 frozen verification changed")
    return result


__all__ = (
    "VERIFICATION_ID",
    "freeze_online_post_dependency_verification_v98",
    "verify_online_post_dependency_campaign_bytes_v98",
)
