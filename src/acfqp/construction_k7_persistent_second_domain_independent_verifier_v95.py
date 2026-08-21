"""Producer-free verification of the frozen V95 persistent campaign."""

from __future__ import annotations

import copy
import hashlib
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v95 as domains
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "7d23704aa7d6513182d59e6f782417d99c7b9f1dc467fe84f9fba30722ee5eb4"
CAMPAIGN_BYTE_COUNT = 1_887_696
CAMPAIGN_SHA256 = "e9331415cee57536e4816b0582f28200c4f216c43e650065f5f12c3deeb19ae7"
PREREGISTRATION_ID = "e6bebdef1c6a4bae2569fd370282b94655e8168e83f6da14f057cbad02630e67"
V94_CAMPAIGN_ID = "8fcb91339c02f818ef9ff829e99ab1ac000fbc6940888d700c31c461fafabde8"
V94_VERIFICATION_ID = "bfd308d496f9e07ea00b2d7f55e0ae2230a4c41f543d704987bfc732cb32be5a"
PROJECTED_MODEL_ARTIFACT_ID = "c069fb2a39fee3b9dc7dc847fef15369cf8d65c5d6322bbaae1bbceb924a476e"
APPLICABILITY_MODEL_ARTIFACT_ID = "07ee765058797bc083db3180bb26952a79a224f8e8aef2f8f284237f87137f77"
SOURCE_MODEL_ID = "401693d9b6f3a50ec3581f0878181955cc804324cad003e23635b6af2e9bb1db"
SOURCE_APPLICABILITY_PROGRAM_ID = "956edacfc94e1312a3a6efa42e0fc2b91bf3266f61a06b3a3a5b8a1f03d38ef0"
TARGET_SEEDS = (982_101, 982_102)
TARGET_EPISODES = (15, 16)
VERIFICATION_ID = (
    "15e4e8e1a636d297015a94f1d7061a6770b1e9b29bd38c1074c53a36c0e2743b"
)
EXPECTED_CANONICAL_BYTE_COUNT = 2_320
EXPECTED_CANONICAL_SHA256 = (
    "f5c15724f01f7ff12dc9a2a776f0c01a5db3caf2df13c6bd2a0b8455e82bd8fc"
)

_PERMUTATION_DOMAIN = b"acfqp:generic-action-key-permutation:v62\x00"
_ALIGNMENT_DOMAIN = b"acfqp:generic-coordinate-alignment:v60\x00"
_EPISODE_DOMAIN = b"acfqp:generic-preloaded-certificate-receding-episode:v74\x00"
_SEQUENCE_DOMAIN = b"acfqp:generic-projected-persistent-sequence:v78\x00"
_OVERLAY_DOMAIN = b"acfqp:generic-persistent-exact-overlay-epoch:v78\x00"


class ConstructionK7PersistentSecondDomainIndependentVerifierV95Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7PersistentSecondDomainIndependentVerifierV95Error(message)


def _generic_id(domain: bytes, payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(domain + canonical_json_bytes(payload)).hexdigest()


def _check_generic_id(document: Any, key: str, domain: bytes) -> None:
    if type(document) is not dict:
        _fail(f"V95 {key} document type changed")
    payload = {name: value for name, value in document.items() if name != key}
    if _generic_id(domain, payload) != document.get(key):
        _fail(f"V95 {key} content identity changed")


def _check_v95_id(document: Any, key: str, domain: str) -> None:
    if type(document) is not dict:
        _fail(f"V95 {key} document type changed")
    payload = {name: value for name, value in document.items() if name != key}
    if domains.extension_content_id_v95(domain, payload) != document.get(key):
        _fail(f"V95 {key} content identity changed")


def _groups(rows: Any) -> int:
    if type(rows) is not list:
        _fail("V95 transition rows changed type")
    keys = set()
    for row in rows:
        selected = row.get("selected_action") if type(row) is dict else None
        pre = row.get("pre_vector") if type(row) is dict else None
        key = selected.get("action_key") if type(selected) is dict else None
        if (
            type(pre) is not list
            or any(type(value) is not int for value in pre)
            or type(key) is not int
        ):
            _fail("V95 transition grouping inventory changed")
        keys.add((tuple(pre), key))
    return len(keys)


def _check_permutation(
    document: Any,
    catalogue: list[dict[str, Any]],
    *,
    seed: int,
) -> None:
    if type(document) is not dict or type(catalogue) is not list:
        _fail("V95 action permutation inventory changed")
    width = len(catalogue)
    seed_bytes = seed.to_bytes(16, "big", signed=False)
    new_to_old = sorted(
        range(width),
        key=lambda old: hashlib.sha256(
            _PERMUTATION_DOMAIN
            + seed_bytes
            + old.to_bytes(8, "big", signed=False)
        ).digest(),
    )
    old_to_new = [-1] * width
    for new, old in enumerate(new_to_old):
        old_to_new[old] = new
    expected_catalogue = []
    for new, row in enumerate(catalogue):
        if (
            type(row) is not dict
            or row.get("action_key") != new
            or type(row.get("anonymous_fields")) is not list
            or any(type(value) is not int for value in row["anonymous_fields"])
        ):
            _fail("V95 permuted action catalogue changed")
        expected_catalogue.append(
            {"action_key": new, "anonymous_fields": row["anonymous_fields"]}
        )
    source_catalogue = [
        {
            "action_key": old,
            "anonymous_fields": catalogue[old_to_new[old]]["anonymous_fields"],
        }
        for old in range(width)
    ]
    payload = {
        "schema": "acfqp.generic_action_key_permutation.v62",
        "family": "BALANCED_BATCH_REFINEMENT",
        "seed": seed,
        "algorithm": "SHA256_RANK_SEED_AND_OLD_KEY",
        "algorithm_domain_hex": _PERMUTATION_DOMAIN.hex(),
        "action_count": width,
        "old_to_new": old_to_new,
        "new_to_old": new_to_old,
        "source_catalogue_sha256": hashlib.sha256(
            canonical_json_bytes(source_catalogue)
        ).hexdigest(),
        "permuted_catalogue_sha256": hashlib.sha256(
            canonical_json_bytes(expected_catalogue)
        ).hexdigest(),
        "anonymous_descriptor_fields_preserved_exactly": True,
        "ground_action_identity_preserved_through_inverse_map": True,
        "state_encoding_and_kernel_unchanged": True,
        "transition_outcomes_accessed_to_select_permutation": False,
        "semantic_action_names_accessed": False,
        "safety_authority_present": False,
    }
    if document != {
        **payload,
        "permutation_id": _generic_id(_PERMUTATION_DOMAIN, payload),
    }:
        _fail("V95 outcome-blind action permutation did not replay")


def _check_stopping(acquisition: Mapping[str, Any]) -> None:
    labels = acquisition.get("ground_support_labels")
    issuance = acquisition.get("candidate_issued_at_ground_support_label")
    crossing = acquisition.get("confidence_crossing_ground_support_label")
    epoch = acquisition.get("candidate_epoch")
    odds = acquisition.get("source_meta_prior_odds")
    confidence = acquisition.get("confidence_denominator")
    successes = acquisition.get("post_issuance_exact_prediction_success_count")
    history = acquisition.get("prequential_history")
    if (
        type(labels) is not int
        or type(issuance) is not int
        or type(crossing) is not int
        or type(epoch) is not int
        or type(odds) is not int
        or type(confidence) is not int
        or type(successes) is not int
        or type(history) is not list
        or len(history) != labels
        or [row.get("ground_support_label") for row in history]
        != list(range(1, labels + 1))
        or not 1 <= issuance <= crossing == labels
        or acquisition.get("target_predictive_confirmation_count") != successes
        or successes != crossing - issuance
        or history[-1].get("stopped") is not True
        or history[-1].get("candidate_epoch") != epoch
        or history[-1].get("post_issuance_exact_prediction_success_count")
        != successes
    ):
        _fail("V95 adaptive stopping coordinates changed")
    issued = [
        row
        for row in history
        if row.get("candidate_epoch") == epoch
        and row.get("candidate_issued") is True
    ]
    threshold = confidence * (epoch + 1) * (epoch + 2)
    if len(issued) != 1 or issued[0].get("ground_support_label") != issuance:
        _fail("V95 final candidate issuance changed")
    if successes == 0:
        if (
            odds < threshold
            or acquisition.get("source_meta_prior_only_stop_at_issuance") is not True
            or history[-1].get("source_meta_prior_only_crossing") is not True
        ):
            _fail("V95 prior-only stopping arithmetic changed")
    else:
        first = next(
            (
                count
                for count in range(1, successes + 1)
                if (2 ** (count + 1) - 1) * odds
                >= (count + 1) * threshold
            ),
            None,
        )
        if (
            first != successes
            or acquisition.get("source_meta_prior_only_stop_at_issuance")
            is not False
        ):
            _fail("V95 predictive stopping arithmetic changed")


def _check_candidate(
    candidate: Any,
    rows: list[dict[str, Any]],
    *,
    labels: int,
    domain: str,
) -> None:
    _check_v95_id(candidate, "candidate_id", domain)
    layout = candidate.get("layout")
    assignments = candidate.get("compiled_factor_assignments")
    residual = candidate.get("unknown_residual_target_columns")
    width = candidate.get("state_width")
    if (
        candidate.get("schema") != "acfqp.generic_partial_factor_candidate.v15"
        or candidate.get("raw_transition_count_at_issuance") != len(rows)
        or candidate.get("raw_transition_sha256")
        != hashlib.sha256(canonical_json_bytes(rows)).hexdigest()
        or candidate.get("support_label_count_at_issuance") != labels
        or type(layout) is not dict
        or type(assignments) is not list
        or not assignments
        or type(residual) is not list
        or not residual
        or type(width) is not int
        or sorted(
            {row.get("target_column") for row in assignments} | set(residual)
        )
        != list(range(width))
        or candidate.get("target_bindings_derived_from_raw_observations") is not True
        or candidate.get("target_slot_inventory_supplied_by_prior") is not False
        or candidate.get("semantic_names_used") is not False
        or candidate.get("planning_authority_present") is not False
        or candidate.get("complete_world_model_claimed") is not False
    ):
        _fail("V95 projected candidate evidence changed")


def _check_alignment(
    alignment: Any,
    *,
    candidate_id: str,
    row_count: int,
    row_sha256: str,
) -> None:
    _check_generic_id(alignment, "coordinate_alignment_id", _ALIGNMENT_DOMAIN)
    if (
        alignment.get("schema") != "acfqp.generic_coordinate_alignment.v60"
        or alignment.get("source_model_id") != SOURCE_MODEL_ID
        or alignment.get("source_applicability_program_id")
        != SOURCE_APPLICABILITY_PROGRAM_ID
        or alignment.get("target_partial_candidate_id") != candidate_id
        or alignment.get("target_raw_transition_count") != row_count
        or alignment.get("target_raw_transition_sha256") != row_sha256
        or sorted(alignment.get("source_state_to_target_canonical", []))
        != list(range(alignment.get("state_width", -1)))
        or sorted(alignment.get("source_action_to_target_canonical", []))
        != list(range(alignment.get("action_field_width", -1)))
        or alignment.get("target_exact_applicability_binding_count") != 1
        or alignment.get("alignment_derived_only_from_target_common_partial_observations")
        is not True
        or alignment.get("target_episode_outcomes_used") is not False
        or alignment.get("source_model_or_applicability_refit") is not False
        or alignment.get("alignment_used_as_safety_authority") is not False
        or alignment.get("complete_world_model_claimed") is not False
    ):
        _fail("V95 coordinate alignment boundary changed")


def _check_acquisition(
    acquisition: Any,
    *,
    meta_prior: bool,
    seed: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    domain = (
        domains.CONSTRUCTION_K7_PERSISTENT_SECOND_DOMAIN_META_ACQUISITION_V95_DOMAIN
        if meta_prior
        else domains.CONSTRUCTION_K7_PERSISTENT_SECOND_DOMAIN_NO_PRIOR_ACQUISITION_V95_DOMAIN
    )
    _check_v95_id(acquisition, "applicability_id", domain)
    rows = acquisition.get("raw_transition_rows")
    catalogue = acquisition.get("action_catalogue")
    labels = acquisition.get("ground_support_labels")
    if (
        acquisition.get("schema")
        != "acfqp.generic_projected_low_label_applicability.v76"
        or acquisition.get("family") != "BALANCED_BATCH_REFINEMENT"
        or acquisition.get("seed") != seed
        or acquisition.get("source_model_id") != SOURCE_MODEL_ID
        or acquisition.get("source_applicability_program_id")
        != SOURCE_APPLICABILITY_PROGRAM_ID
        or type(rows) is not list
        or type(catalogue) is not list
        or _groups(rows) != labels
        or acquisition.get("raw_transition_sha256")
        != hashlib.sha256(canonical_json_bytes(rows)).hexdigest()
        or acquisition.get("action_catalogue_sha256")
        != hashlib.sha256(canonical_json_bytes(catalogue)).hexdigest()
        or acquisition.get("source_meta_prior_odds") != (16 if meta_prior else 1)
        or acquisition.get("source_meta_prior_enabled") is not meta_prior
        or acquisition.get("witness_blind_depth_stream_used") is not True
        or acquisition.get("terminal_witness_used_to_schedule_queries") is not False
        or acquisition.get("fixed_label_floor_used") is not False
        or acquisition.get("fixed_confirmation_block_used") is not False
        or acquisition.get("same_constructor_projection_replay_and_stopping_rule_in_prior_on_off_arms")
        is not True
        or acquisition.get("target_episode_outcomes_used") is not False
        or acquisition.get("source_model_or_applicability_refit") is not False
        or acquisition.get("projection_promoted_to_global_applicability_fact")
        is not False
        or acquisition.get("proposal_used_as_safety_authority") is not False
        or acquisition.get("complete_world_model_claimed") is not False
    ):
        _fail("V95 matched acquisition evidence changed")
    for row in rows:
        selected = row["selected_action"]
        key = selected["action_key"]
        if (
            not 0 <= key < len(catalogue)
            or selected != catalogue[key]
            or any(not 0 <= value < len(catalogue) for value in row["legal_action_keys_before"])
            or any(not 0 <= value < len(catalogue) for value in row["legal_action_keys_after"])
        ):
            _fail("V95 acquisition action projection changed")
    _check_stopping(acquisition)
    candidate = acquisition.get("projected_target_candidate")
    _check_candidate(candidate, rows, labels=labels, domain=domain)
    alignment = acquisition.get("coordinate_alignment")
    _check_alignment(
        alignment,
        candidate_id=candidate["candidate_id"],
        row_count=len(rows),
        row_sha256=hashlib.sha256(canonical_json_bytes(rows)).hexdigest(),
    )
    if acquisition.get("coordinate_alignment_id") != alignment["coordinate_alignment_id"]:
        _fail("V95 acquisition alignment join changed")
    return rows, candidate


def _project_rows(
    rows: list[dict[str, Any]],
    candidate: Mapping[str, Any],
    alignment: Mapping[str, Any],
) -> list[dict[str, Any]]:
    state_layout = candidate["layout"]["state_canonical_to_raw"]
    action_layout = candidate["layout"]["action_canonical_to_raw"]
    state_mapping = alignment["source_state_to_target_canonical"]
    action_mapping = alignment["source_action_to_target_canonical"]
    result = []
    for row in rows:
        canonical_pre = [row["pre_vector"][index] for index in state_layout]
        canonical_post = [row["post_vector"][index] for index in state_layout]
        canonical_action = [
            row["selected_action"]["anonymous_fields"][index]
            for index in action_layout
        ]
        projected = copy.deepcopy(row)
        projected["occurrence"] = 0
        projected["pre_vector"] = [canonical_pre[index] for index in state_mapping]
        projected["post_vector"] = [canonical_post[index] for index in state_mapping]
        projected["selected_action"]["anonymous_fields"] = [
            canonical_action[index] for index in action_mapping
        ]
        result.append(projected)
    return result


def _check_episode(
    episode: Any,
    *,
    seed: int,
    episode_index: int,
    candidate_id: str,
    transfer: bool,
) -> None:
    if type(episode) is not dict:
        _fail("V95 episode type changed")
    extras = {
        "preexisting_persistent_exact_support_labels",
        "new_certificate_labels_charged_this_episode",
        "cumulative_unique_target_labels_after_episode",
        "resulting_overlay_epoch_id",
    }
    identity_payload = {
        key: value
        for key, value in episode.items()
        if key != "episode_id" and key not in extras
    }
    if _generic_id(_EPISODE_DOMAIN, identity_payload) != episode.get("episode_id"):
        _fail("V95 episode content identity changed")
    failures = episode.get("failed_certificates")
    distinctions = episode.get("local_distinctions")
    rows = episode.get("raw_incremental_transition_rows")
    steps = episode.get("execution_steps")
    matches = episode.get("execution_action_matches_abstract_proposal")
    if (
        episode.get("schema")
        != "acfqp.generic_preloaded_certificate_receding_episode.v74"
        or episode.get("family") != "BALANCED_BATCH_REFINEMENT"
        or episode.get("seed") != seed
        or episode.get("episode_index") != episode_index
        or episode.get("target_candidate_id") != candidate_id
        or episode.get("success") is not True
        or type(failures) is not list
        or type(distinctions) is not list
        or type(rows) is not list
        or len(failures) != len(distinctions)
        or rows
        != [
            row
            for distinction in distinctions
            if distinction.get("distinction_kind")
            == "QUERY_LOCAL_EXACT_TRANSITION_SUPPORT"
            for row in distinction["raw_transition_rows"]
        ]
        or episode.get("incremental_certificate_local_ground_support_labels")
        != sum(row.get("ground_support_labels", -1) for row in distinctions)
        or type(steps) is not int
        or len(episode.get("action_keys", [])) != steps
        or len(episode.get("outcome_tape_sha256", [])) != steps
        or type(matches) is not list
        or len(matches) != steps
        or episode.get("execution_action_matches_abstract_proposal_count")
        != sum(value is True for value in matches)
        or episode.get("total_target_ground_support_labels")
        != episode.get("preloaded_acquisition_ground_support_labels")
        + episode.get("incremental_certificate_local_ground_support_labels")
        or episode.get("all_incremental_ground_queries_followed_failed_certificates")
        is not True
        or episode.get("preloaded_exact_rows_reused_without_reacquisition") is not True
        or episode.get("query_local_exact_overlay_exclusively_used_for_safety")
        is not True
        or episode.get("model_or_alignment_used_as_safety_authority") is not False
        or episode.get("target_episode_outcomes_used_to_refit_model_or_alignment")
        is not False
        or episode.get("same_exact_engine_implementation_for_transfer_and_strict_arms")
        is not True
        or episode.get("complete_world_model_synthesized") is not False
    ):
        _fail("V95 exact episode evidence or accounting changed")
    for index, (failure, distinction) in enumerate(
        zip(failures, distinctions, strict=True)
    ):
        if (
            failure.get("failure_index") != index
            or distinction.get("failure_index") != index
            or failure.get("raw_state") != distinction.get("raw_state")
            or failure.get("action_key") != distinction.get("action_key")
            or failure.get("ground_query_performed_before_failure") is not False
            or distinction.get("query_after_failed_certificate") is not True
            or distinction.get("distinction_kind")
            not in {
                "QUERY_LOCAL_EXACT_TRANSITION_SUPPORT",
                "QUERY_LOCAL_LEGAL_ACTION_SET",
            }
        ):
            _fail("V95 certificate-failure-only query discipline changed")
        if distinction["distinction_kind"] == "QUERY_LOCAL_EXACT_TRANSITION_SUPPORT":
            if type(distinction.get("raw_transition_rows")) is not list:
                _fail("V95 exact transition distinction changed")
        elif (
            failure.get("action_key") is not None
            or type(distinction.get("legal_action_keys")) is not list
        ):
            _fail("V95 legal-action distinction changed")
    if transfer:
        receipts = episode.get("abstract_plan_receipts")
        if (
            episode.get("arm") != "PROJECTED_PERSISTENT_LOW_LABEL_TRANSFER"
            or episode.get("abstract_model_used_only_for_action_ordering") is not True
            or type(receipts) is not list
            or not receipts
            or episode.get("abstract_plan_success_count") != len(receipts)
            or episode.get("new_certificate_labels_charged_this_episode")
            != episode.get("incremental_certificate_local_ground_support_labels")
            or any(
                distinction.get("distinction_kind")
                != "QUERY_LOCAL_EXACT_TRANSITION_SUPPORT"
                for distinction in distinctions
            )
        ):
            _fail("V95 abstract-primary transfer episode changed")
        for receipt in receipts:
            plan = receipt.get("abstract_plan")
            if (
                type(plan) is not dict
                or plan.get("schema")
                != "acfqp.generic_applicability_conditioned_plan.v58"
                or plan.get("projected_disagreement_successor_model_id")
                != SOURCE_MODEL_ID
                or plan.get("action_applicability_program_id")
                != SOURCE_APPLICABILITY_PROGRAM_ID
                or plan.get("target_partial_candidate_id") != candidate_id
                or plan.get("support_feasible_receding_plan_found") is not True
                or plan.get("ground_transition_accessed_during_abstract_search")
                is not False
                or plan.get("applicability_or_abstract_plan_used_as_safety_authority")
                is not False
                or plan.get("complete_world_model_claimed") is not False
            ):
                _fail("V95 abstract plan receipt changed")
    elif (
        episode.get("arm") != "STRICT_COLD_DIRECT_GROUND"
        or episode.get("preloaded_acquisition_ground_support_labels") != 0
        or episode.get("abstract_plan_receipts") != []
        or episode.get("abstract_planning_compute_events") != 0
        or episode.get("abstract_model_used_only_for_action_ordering") is not False
    ):
        _fail("V95 strict cold-direct control received transfer work")


def _deduplicate_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    unique: dict[tuple[Any, ...], dict[str, Any]] = {}
    for row in rows:
        key = (
            tuple(row["pre_vector"]),
            row["selected_action"]["action_key"],
            tuple(row["post_vector"]),
        )
        unique[key] = row
    return [unique[key] for key in sorted(unique)]


def _check_sequence(
    sequence: Any,
    acquisition: Mapping[str, Any],
    rows: list[dict[str, Any]],
    candidate: Mapping[str, Any],
    *,
    seed: int,
) -> tuple[int, int, int, int, int]:
    _check_generic_id(sequence, "sequence_id", _SEQUENCE_DOMAIN)
    alignment = acquisition["coordinate_alignment"]
    projected_rows = _project_rows(rows, candidate, alignment)
    overlays = sequence.get("overlay_epochs")
    transfers = sequence.get("transfer_episodes")
    strict = sequence.get("strict_cold_direct_episodes")
    labels = acquisition["ground_support_labels"]
    if (
        sequence.get("schema") != "acfqp.generic_projected_persistent_sequence.v78"
        or sequence.get("family") != "BALANCED_BATCH_REFINEMENT"
        or sequence.get("seed") != seed
        or sequence.get("target_episode_indices") != list(TARGET_EPISODES)
        or sequence.get("source_model_id") != SOURCE_MODEL_ID
        or sequence.get("source_applicability_program_id")
        != SOURCE_APPLICABILITY_PROGRAM_ID
        or sequence.get("target_candidate_id") != candidate["candidate_id"]
        or sequence.get("coordinate_alignment") != alignment
        or sequence.get("coordinate_alignment_id") != alignment["coordinate_alignment_id"]
        or type(overlays) is not list
        or len(overlays) != len(TARGET_EPISODES) + 1
        or type(transfers) is not list
        or type(strict) is not list
        or len(transfers) != len(TARGET_EPISODES)
        or len(strict) != len(TARGET_EPISODES)
        or sequence.get("acquisition_ground_support_labels_paid_once") != labels
        or sequence.get("acquisition_and_certificate_rows_immutable_and_reused_across_queries")
        is not True
        or sequence.get("every_new_ground_query_followed_a_failed_certificate") is not True
        or sequence.get("no_ground_query_repeated_across_transfer_episodes") is not True
        or sequence.get("query_local_exact_overlay_exclusively_used_for_safety")
        is not True
        or sequence.get("model_alignment_or_applicability_used_as_safety_authority")
        is not False
        or sequence.get("complete_world_model_synthesized") is not False
        or sequence.get("official_execution_allowed") is not False
        or sequence.get("official_scalar_cost") is not None
        or sequence.get("WORKLOAD_ECONOMICS_GATE") != "NOT_RUN"
        or sequence.get("COUNTER_COMPLETENESS_GATE") != "NOT_RUN"
    ):
        _fail("V95 persistent sequence boundary changed")
    persistent_rows = projected_rows
    certificate_labels = 0
    seen_queries = set()
    for epoch, overlay in enumerate(overlays):
        _check_generic_id(overlay, "overlay_epoch_id", _OVERLAY_DOMAIN)
        if (
            overlay.get("schema")
            != "acfqp.generic_persistent_exact_overlay_epoch.v78"
            or overlay.get("overlay_epoch") != epoch
            or overlay.get("acquisition_ground_support_labels_paid_once") != labels
            or overlay.get("persisted_certificate_ground_support_labels_paid_once")
            != certificate_labels
            or overlay.get("total_unique_ground_support_labels_paid")
            != _groups(persistent_rows)
            or overlay.get("exact_transition_rows") != persistent_rows
            or overlay.get("exact_transition_sha256")
            != hashlib.sha256(canonical_json_bytes(persistent_rows)).hexdigest()
            or overlay.get("immutable_append_only") is not True
            or overlay.get("future_query_safety_authority_claimed") is not False
            or overlay.get("query_local_exact_evidence_only") is not True
        ):
            _fail("V95 persistent overlay replay changed")
        if epoch == len(transfers):
            continue
        transfer = transfers[epoch]
        direct = strict[epoch]
        episode_index = TARGET_EPISODES[epoch]
        projected_candidate_id = sequence.get("projected_target_candidate_id")
        _check_episode(
            transfer,
            seed=seed,
            episode_index=episode_index,
            candidate_id=projected_candidate_id,
            transfer=True,
        )
        _check_episode(
            direct,
            seed=seed,
            episode_index=episode_index,
            candidate_id=projected_candidate_id,
            transfer=False,
        )
        queries = {
            (tuple(row["raw_state"]), row["action_key"])
            for row in transfer["local_distinctions"]
        }
        if seen_queries & queries:
            _fail("V95 persistent sequence repeated a ground query")
        seen_queries |= queries
        if (
            transfer["preexisting_persistent_exact_support_labels"]
            != _groups(persistent_rows)
            or transfer["preloaded_acquisition_ground_support_labels"]
            != _groups(persistent_rows)
        ):
            _fail("V95 preexisting overlay accounting changed")
        certificate_labels += transfer[
            "new_certificate_labels_charged_this_episode"
        ]
        persistent_rows = _deduplicate_rows(
            [*persistent_rows, *transfer["raw_incremental_transition_rows"]]
        )
        cumulative = labels + certificate_labels
        if (
            _groups(persistent_rows) != cumulative
            or transfer["cumulative_unique_target_labels_after_episode"] != cumulative
            or transfer["resulting_overlay_epoch_id"]
            != overlays[epoch + 1]["overlay_epoch_id"]
        ):
            _fail("V95 overlay append accounting changed")
    transfer_lifetime = labels + certificate_labels
    strict_lifetime = sum(row["total_target_ground_support_labels"] for row in strict)
    if (
        transfers[1]["new_certificate_labels_charged_this_episode"] != 0
        or sequence.get("persistent_certificate_ground_support_labels_paid_once")
        != certificate_labels
        or sequence.get("transfer_lifetime_unique_target_ground_support_labels")
        != transfer_lifetime
        or sequence.get("strict_cold_direct_lifetime_target_ground_support_labels")
        != strict_lifetime
        or sequence.get("strict_minus_transfer_lifetime_target_labels")
        != strict_lifetime - transfer_lifetime
        or sequence.get("lifetime_target_sample_reduction_observed")
        is not (transfer_lifetime < strict_lifetime)
    ):
        _fail("V95 lifetime sample accounting changed")
    return (
        transfer_lifetime,
        strict_lifetime,
        certificate_labels,
        sum(row["execution_steps"] for row in transfers),
        sum(row["abstract_planning_compute_events"] for row in transfers),
    )


def _strict_projection(episode: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in episode.items()
        if key not in {"episode_id", "target_candidate_id"}
    }


def _check_occurrence(row: Any, *, seed: int) -> dict[str, int]:
    _check_v95_id(
        row,
        "occurrence_id",
        domains.CONSTRUCTION_K7_PERSISTENT_SECOND_DOMAIN_OCCURRENCE_V95_DOMAIN,
    )
    if (
        row.get("schema") != "acfqp.persistent_second_domain_occurrence.v95"
        or row.get("family") != "BALANCED_BATCH_REFINEMENT"
        or row.get("target_seed") != seed
        or row.get("target_episode_indices") != list(TARGET_EPISODES)
        or row.get("source_model_id") != SOURCE_MODEL_ID
        or row.get("source_applicability_program_id")
        != SOURCE_APPLICABILITY_PROGRAM_ID
        or row.get("status")
        != "TARGET_PERSISTENT_META_NO_PRIOR_AND_DIRECT_SEQUENCES_COMPLETED"
        or row.get("failure_reason") is not None
        or row.get("same_constructor_projection_stop_rule_query_identities_and_exact_engine")
        is not True
        or row.get("only_source_meta_prior_odds_differs_between_acquisition_arms")
        is not True
        or row.get("persistent_exact_overlay_shared_only_within_each_arm_not_across_arms")
        is not True
        or row.get("source_prior_model_alignment_and_applicability_used_as_safety_authority")
        is not False
        or row.get("official_execution_allowed") is not False
    ):
        _fail("V95 occurrence claim boundary changed")
    meta_rows, meta_candidate = _check_acquisition(
        row["meta_prior_acquisition"], meta_prior=True, seed=seed
    )
    no_rows, no_candidate = _check_acquisition(
        row["no_prior_acquisition"], meta_prior=False, seed=seed
    )
    if row["meta_prior_acquisition"]["action_catalogue"] != row[
        "no_prior_acquisition"
    ]["action_catalogue"]:
        _fail("V95 matched arms used different action catalogues")
    _check_permutation(
        row["outcome_blind_action_key_permutation"],
        row["meta_prior_acquisition"]["action_catalogue"],
        seed=seed,
    )
    meta = _check_sequence(
        row["meta_prior_persistent_sequence"],
        row["meta_prior_acquisition"],
        meta_rows,
        meta_candidate,
        seed=seed,
    )
    no_prior = _check_sequence(
        row["no_prior_persistent_sequence"],
        row["no_prior_acquisition"],
        no_rows,
        no_candidate,
        seed=seed,
    )
    meta_strict = [
        _strict_projection(episode)
        for episode in row["meta_prior_persistent_sequence"][
            "strict_cold_direct_episodes"
        ]
    ]
    no_strict = [
        _strict_projection(episode)
        for episode in row["no_prior_persistent_sequence"][
            "strict_cold_direct_episodes"
        ]
    ]
    ood = row.get("strict_incompatible_model_ood_control")
    if (
        meta_strict != no_strict
        or meta[1] != no_prior[1]
        or type(ood) is not dict
        or ood.get("status")
        != "INCOMPATIBLE_MODEL_REJECTED_BEFORE_TARGET_OBSERVATION"
        or ood.get("target_ground_support_labels_consumed") != 0
        or ood.get("target_episode_executed") is not False
        or not row["meta_prior_acquisition"]["ground_support_labels"]
        < row["no_prior_acquisition"]["ground_support_labels"]
        or not meta[0] <= no_prior[0]
        or not meta[0] <= meta[1]
    ):
        _fail("V95 matched-arm or OOD Gate evidence changed")
    return {
        "meta_acquisition": row["meta_prior_acquisition"]["ground_support_labels"],
        "no_prior_acquisition": row["no_prior_acquisition"]["ground_support_labels"],
        "meta_certificate": meta[2],
        "no_prior_certificate": no_prior[2],
        "meta_lifetime": meta[0],
        "no_prior_lifetime": no_prior[0],
        "strict_lifetime": meta[1],
        "meta_execution": meta[3],
        "no_prior_execution": no_prior[3],
        "strict_execution": sum(
            episode["execution_steps"]
            for episode in row["meta_prior_persistent_sequence"][
                "strict_cold_direct_episodes"
            ]
        ),
        "meta_derivation": row["meta_prior_acquisition"][
            "projection_derivation_compute_events"
        ],
        "no_prior_derivation": row["no_prior_acquisition"][
            "projection_derivation_compute_events"
        ],
        "meta_planning": meta[4],
        "no_prior_planning": no_prior[4],
    }


def _sum(rows: list[dict[str, int]], key: str) -> int:
    return sum(row[key] for row in rows)


def _verify_campaign_document(document: Any) -> dict[str, Any]:
    _check_v95_id(
        document,
        "campaign_id",
        domains.CONSTRUCTION_K7_PERSISTENT_SECOND_DOMAIN_CAMPAIGN_V95_DOMAIN,
    )
    if (
        document.get("schema") != "acfqp.persistent_second_domain_campaign.v95"
        or document.get("campaign_id") != CAMPAIGN_ID
        or document.get("preregistration_id") != PREREGISTRATION_ID
        or document.get("v94_campaign_id") != V94_CAMPAIGN_ID
        or document.get("v94_verification_id") != V94_VERIFICATION_ID
        or document.get("projected_model_artifact_id")
        != PROJECTED_MODEL_ARTIFACT_ID
        or document.get("applicability_model_artifact_id")
        != APPLICABILITY_MODEL_ARTIFACT_ID
        or document.get("source_model_id") != SOURCE_MODEL_ID
        or document.get("source_applicability_program_id")
        != SOURCE_APPLICABILITY_PROGRAM_ID
        or document.get("fresh_target_identities_executed_without_selection") is not True
        or document.get("v94_identity_preserved") is not True
    ):
        _fail("V95 campaign predecessor or identity contract changed")
    occurrences = document.get("target_occurrences")
    if (
        type(occurrences) is not list
        or [row.get("target_seed") for row in occurrences] != list(TARGET_SEEDS)
    ):
        _fail("V95 target occurrence inventory changed")
    rows = [
        _check_occurrence(occurrence, seed=seed)
        for occurrence, seed in zip(occurrences, TARGET_SEEDS, strict=True)
    ]
    expected_accounting = {
        "meta_prior_target_acquisition_labels": _sum(rows, "meta_acquisition"),
        "no_prior_target_acquisition_labels": _sum(rows, "no_prior_acquisition"),
        "meta_prior_persistent_certificate_labels": _sum(rows, "meta_certificate"),
        "no_prior_persistent_certificate_labels": _sum(rows, "no_prior_certificate"),
        "meta_prior_lifetime_unique_target_labels": _sum(rows, "meta_lifetime"),
        "no_prior_lifetime_unique_target_labels": _sum(rows, "no_prior_lifetime"),
        "strict_cold_direct_lifetime_target_labels": _sum(rows, "strict_lifetime"),
        "strict_minus_meta_prior_lifetime_target_labels": (
            _sum(rows, "strict_lifetime") - _sum(rows, "meta_lifetime")
        ),
        "no_prior_minus_meta_prior_lifetime_target_labels": (
            _sum(rows, "no_prior_lifetime") - _sum(rows, "meta_lifetime")
        ),
        "meta_prior_execution_steps": _sum(rows, "meta_execution"),
        "no_prior_execution_steps": _sum(rows, "no_prior_execution"),
        "strict_execution_steps": _sum(rows, "strict_execution"),
        "meta_prior_projection_derivation_compute_events": _sum(rows, "meta_derivation"),
        "no_prior_projection_derivation_compute_events": _sum(rows, "no_prior_derivation"),
        "meta_prior_abstract_planning_compute_events": _sum(rows, "meta_planning"),
        "no_prior_abstract_planning_compute_events": _sum(rows, "no_prior_planning"),
        "strict_abstract_planning_compute_events": 0,
        "source_target_labels_execution_derivation_certificate_and_planning_compute_separate": True,
        "scalar_cost_aggregation_performed": False,
    }
    gate = document.get("registered_gate")
    if (
        document.get("accounting") != expected_accounting
        or expected_accounting["meta_prior_lifetime_unique_target_labels"] != 78
        or expected_accounting["no_prior_lifetime_unique_target_labels"] != 90
        or expected_accounting["strict_cold_direct_lifetime_target_labels"] != 310
        or type(gate) is not dict
        or set(gate.values()) != {True, 2}
        or gate.get("required_target_occurrence_count") != 2
        or gate.get("completed_target_occurrence_count") != 2
        or gate.get("passed") is not True
        or document.get("sample_tax_reduction_replicated_in_second_registered_domain")
        is not True
        or document.get("sample_tax_reduction_generalized_beyond_two_registered_domain_families")
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
        _fail("V95 campaign Gate, accounting, or claim boundary changed")
    return expected_accounting


def verify_persistent_second_domain_campaign_bytes_v95(raw: bytes) -> dict[str, Any]:
    if (
        type(raw) is not bytes
        or len(raw) != CAMPAIGN_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != CAMPAIGN_SHA256
    ):
        _fail("V95 frozen campaign bytes changed")
    document = loads_canonical_json(raw)
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail("V95 campaign is not canonical JSON")
    accounting = _verify_campaign_document(document)
    payload = {
        "schema": "acfqp.persistent_second_domain_verification.v95",
        "campaign_id": CAMPAIGN_ID,
        "campaign_byte_count": CAMPAIGN_BYTE_COUNT,
        "campaign_sha256": CAMPAIGN_SHA256,
        "preregistration_id": PREREGISTRATION_ID,
        "verification_status": (
            "REGISTERED_PERSISTENT_SECOND_DOMAIN_SAMPLE_TAX_REDUCTION_VERIFIED"
        ),
        "verified_target_seeds": list(TARGET_SEEDS),
        "verified_target_episode_indices": list(TARGET_EPISODES),
        "verified_accounting": accounting,
        "outcome_blind_action_permutations_independently_replayed": True,
        "raw_observation_projection_independently_replayed": True,
        "adaptive_stopping_arithmetic_independently_replayed": True,
        "persistent_overlay_epochs_independently_replayed": True,
        "certificate_failure_only_ground_queries_independently_replayed": True,
        "second_query_zero_new_label_result_independently_replayed": True,
        "strict_cold_direct_restart_and_ood_controls_independently_replayed": True,
        "sample_tax_reduction_replicated_in_second_registered_domain": True,
        "sample_tax_reduction_generalized_beyond_two_registered_domain_families": False,
        "complete_world_model_synthesized": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    return {
        **payload,
        "verification_id": domains.extension_content_id_v95(
            domains.CONSTRUCTION_K7_PERSISTENT_SECOND_DOMAIN_VERIFICATION_V95_DOMAIN,
            payload,
        ),
    }


def freeze_persistent_second_domain_verification_v95(raw: bytes) -> bytes:
    document = verify_persistent_second_domain_campaign_bytes_v95(raw)
    result = canonical_json_bytes(document)
    if VERIFICATION_ID != "0" * 64 and (
        document["verification_id"] != VERIFICATION_ID
        or len(result) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(result).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("V95 frozen verification changed")
    return result


__all__ = (
    "VERIFICATION_ID",
    "freeze_persistent_second_domain_verification_v95",
    "verify_persistent_second_domain_campaign_bytes_v95",
)
