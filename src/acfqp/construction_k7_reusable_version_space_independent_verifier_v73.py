"""Producer-free semantic reconstruction of the frozen V73 campaign.

The verifier never imports the V73 producer/core or the V42/V43 compiler and
planner.  It reuses the already producer-free V72r1 acquisition replay,
independently reconstructs each V42 residual version space, then enumerates the
fresh ground kernels to replay every V43 certificate-local row, outcome tape,
and exact-overlay proof closure.
"""

from __future__ import annotations

from collections import deque
import copy
import hashlib
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v73 as domains
from acfqp import construction_k7_reusable_version_space_preregistration_v73 as pre
from acfqp import construction_k7_successor_version_space_independent_verifier_v72r1 as v72_replay
from acfqp import construction_k7_role_free_relational_transfer_preregistration_v70 as v70_pre
from acfqp import true_bit_symmetric_three_domain_campaign_core_v59 as base
from acfqp.construction_k7_residual_factor_library_v62 import (
    freeze_residual_factor_library_v62,
    verify_residual_factor_library_v62,
)
from acfqp.construction_k7_role_free_relational_template_library_v70 import (
    freeze_role_free_relational_template_library_v70,
    verify_role_free_relational_template_library_v70,
)
from acfqp.generic_relational_terminal_program_independent_replay_v32 import (
    verify_source_complete_relational_program_v32,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "5a896a845e4767f78c30e183b11a11e66ecf98a2cad56dabd739fdec11c941be"
CAMPAIGN_BYTE_COUNT = 4_706_817
CAMPAIGN_SHA256 = "ac6698c95f20f65842ffe45ece7dfa941f53e5167938eafdb7bbd5787c5254a9"
PREREGISTRATION_ID = "8d05c4c1c5ec6dfab6be1e3ced0130656acefb729c5b93fc88169f48b45646f7"
V72R1_CAMPAIGN_ID = "2d570b3853f574083cb7e93e2f0ca026a985ca6cd5b2b12475eb4ebc5ead1e80"
V72R1_VERIFICATION_ID = "8d2c9459b3e0ccea9d4b00b5ccc6808cd1e03ac6ac34ff8a97c4227c212287a6"
TEMPLATE_LIBRARY_ARTIFACT_ID = "8657115a19bace2861b3a14ff780a2708b6e76101a2b7468e52e5285a113b2a9"
VERIFICATION_ID = "fdc8e7f5294bc448e7e08986fee62d19ca6811388aa5ab4b66016976169e3cf8"
EXPECTED_CANONICAL_BYTE_COUNT = 1_180
EXPECTED_CANONICAL_SHA256 = "9d4198fe46880d2228e8cb5d757f62d6c0471afd0d449c5101c186908b9671ed"

_SOURCE_EPISODE_DOMAIN = b"acfqp:generic-source-complete-relational-world-model:v31\x00"
_ACQUISITION_BUNDLE_DOMAIN = b"acfqp:relation-covering-learned-successor-acquisition:v41\x00"
_MODEL_DOMAIN = b"acfqp:generic-joint-successor-version-space-model:v42\x00"
_TARGET_EPISODE_DOMAIN = b"acfqp:generic-reusable-version-space-certificate-episode:v43\x00"


class ConstructionK7ReusableVersionSpaceIndependentVerifierV73Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7ReusableVersionSpaceIndependentVerifierV73Error(message)


def _generic_id(domain: bytes, payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(domain + canonical_json_bytes(payload)).hexdigest()


def _content(document: Mapping[str, Any], key: str, domain: str) -> None:
    if type(document) is not dict or type(document.get(key)) is not str:
        _fail(f"V73 {key} inventory changed")
    payload = {name: value for name, value in document.items() if name != key}
    if domains.extension_content_id_v73(domain, payload) != document[key]:
        _fail(f"V73 {key} content identity changed")


def _source_acquisition(
    source: Mapping[str, Any],
    library: Mapping[str, Any],
    residual_id: str,
) -> dict[str, Any]:
    try:
        schedule = v72_replay._schedule(source)  # noqa: SLF001
        ordered = copy.deepcopy(source)
        ordered["raw_transition_rows"] = schedule["scheduled_raw_transition_rows"]
        learned = v72_replay._acquisition(  # noqa: SLF001
            ordered, library, residual_id
        )
    except Exception as error:
        _fail(f"V73 independent source acquisition failed: {type(error).__name__}")
    payload = {
        "schema": "acfqp.relation_covering_learned_successor_acquisition.v41",
        "query_schedule": schedule,
        "learned_successor_acquisition": learned,
        "query_schedule_id": schedule["query_schedule_id"],
        "learned_successor_acquisition_id": learned[
            "learned_successor_acquisition_id"
        ],
        "outcome_witness_used_for_scheduling_or_unacquired_guard": False,
        "retrospective_acquisition_only": True,
        "online_execution_integrated": False,
        "proposal_only_not_safety_authority": True,
    }
    return {
        **payload,
        "relation_covering_acquisition_id": _generic_id(
            _ACQUISITION_BUNDLE_DOMAIN, payload
        ),
    }


def _expected_model(
    occurrence: Mapping[str, Any],
    candidate: Any,
    source: Mapping[str, Any],
    acquisition: Mapping[str, Any],
) -> dict[str, Any] | None:
    learned = acquisition["learned_successor_acquisition"]
    if learned["status"] != "PROPOSAL_ISSUED_HELDOUT_VALIDATED":
        return None
    schedule = acquisition["query_schedule"]
    groups = v72_replay._groups(  # noqa: SLF001
        schedule["scheduled_raw_transition_rows"]
    )
    stop = learned["stopped_physical_ground_support_labels"]
    if type(stop) is not int or not 1 <= stop < len(groups):
        _fail("V73 source stop changed")
    acquired = [copy.deepcopy(row) for group in groups[:stop] for row in group]
    batches = v72_replay._aligned_batches(source["layout"], acquired)  # noqa: SLF001
    terminal = learned["selected_terminal_program"]
    minimal = v72_replay._minimal_program(terminal)  # noqa: SLF001
    terminal_frontier = copy.deepcopy(minimal["decision_tree_candidate_frontier"])
    status_target = terminal["status_target_column"]
    residual_targets = [
        target
        for target in source["unknown_residual_target_columns"]
        if target != status_target
    ]
    spaces = []
    compute = 0
    for target in residual_targets:
        frontier, evaluations = v72_replay._version_space(batches, target)  # noqa: SLF001
        compute += evaluations
        if not frontier:
            return None
        spaces.append(
            {
                "target_column": target,
                "batch_exact_candidate_count": len(frontier),
                "batch_exact_candidate_frontier": frontier,
            }
        )
    state_order = source["layout"]["state_canonical_to_raw"]
    accepting = sorted(
        {
            tuple(row["post_vector"][index] for index in state_order)
            for row in acquired
            if row["terminal_acceptance_after"] is True
        }
    )
    document = candidate.public_document
    payload = {
        "schema": "acfqp.generic_joint_successor_version_space_model.v42",
        "partial_candidate_id": document["candidate_id"],
        "source_relation_covering_acquisition_id": acquisition[
            "relation_covering_acquisition_id"
        ],
        "source_query_schedule_id": schedule["query_schedule_id"],
        "source_learned_successor_acquisition_id": learned[
            "learned_successor_acquisition_id"
        ],
        "source_complete_evidence_sha256": hashlib.sha256(
            canonical_json_bytes(source)
        ).hexdigest(),
        "source_layout": copy.deepcopy(source["layout"]),
        "state_width": document["state_width"],
        "action_field_width": document["action_field_width"],
        "acquisition_prefix_ground_support_labels": stop,
        "acquired_raw_transition_rows": acquired,
        "acquired_raw_transition_row_count": len(acquired),
        "acquired_raw_transition_sha256": hashlib.sha256(
            canonical_json_bytes(acquired)
        ).hexdigest(),
        "known_partial_factor_assignments": copy.deepcopy(
            list(candidate.assignments)
        ),
        "residual_version_spaces": spaces,
        "status_target_column": status_target,
        "mdl_minimal_terminal_candidate_frontier": terminal_frontier,
        "mdl_minimal_terminal_candidate_count": len(terminal_frontier),
        "canonical_accepting_state_prototypes": [list(row) for row in accepting],
        "version_space_selection_compute_events": compute,
        "every_batch_exact_residual_expression_retained": True,
        "multiple_residual_proposals_jointly_compiled": any(
            row["batch_exact_candidate_count"] > 1 for row in spaces
        ),
        "all_state_coordinates_represented": True,
        "only_acquisition_prefix_outcomes_used_to_fit_successor_expressions": True,
        "post_stop_heldout_rows_used_as_successor_expression_inputs": False,
        "post_stop_heldout_validation_and_provenance_identity_present": True,
        "heldout_validation_used_only_as_scientific_gate": True,
        "empirical_version_space_promoted_to_global_exact_dynamics": False,
        "complete_world_model_claimed": False,
        "abstract_plan_safety_authority_present": False,
    }
    return {
        **payload,
        "joint_successor_version_space_model_id": _generic_id(
            _MODEL_DOMAIN, payload
        ),
    }


def _reachable_states(adapter: Any) -> dict[tuple[int, ...], Any]:
    initial = adapter.initial()
    queue = deque([initial])
    by_raw = {adapter.encode(initial): initial}
    while queue:
        state = queue.popleft()
        for action in adapter.actions(state):
            for outcome in adapter.kernel.step(state, action):
                successor = outcome.next_state
                raw = adapter.encode(successor)
                previous = by_raw.get(raw)
                if previous is not None and previous != successor:
                    _fail("V73 raw state encoding is not injective")
                if previous is None:
                    by_raw[raw] = successor
                    if adapter.active(successor):
                        queue.append(successor)
    return by_raw


def _verify_target_episode(
    episode: Mapping[str, Any],
    adapter: Any,
    observed_rows: tuple[Any, ...],
    expected_model_id: str | None,
) -> None:
    if type(episode) is not dict or episode.get("success") is not True:
        _fail("V73 target episode did not succeed")
    payload = {key: value for key, value in episode.items() if key != "episode_id"}
    if (
        _generic_id(_TARGET_EPISODE_DOMAIN, payload) != episode.get("episode_id")
        or episode.get("family") != adapter.family
        or episode.get("seed") != adapter.seed
        or episode.get("episode_index") != pre.TARGET_EPISODE_INDEX
        or episode.get("model_source_episode_index") != pre.SOURCE_EPISODE_INDEX
        or episode.get("joint_successor_version_space_model_id")
        != expected_model_id
    ):
        _fail("V73 target episode identity changed")
    failures = episode.get("failed_certificates")
    distinctions = episode.get("local_distinctions")
    raw_rows = episode.get("raw_local_transition_rows")
    if (
        type(failures) is not list
        or type(distinctions) is not list
        or type(raw_rows) is not list
        or len(failures) != len(distinctions)
        or episode.get("target_certificate_local_ground_support_labels")
        != sum(row.get("ground_support_labels", -1) for row in distinctions)
    ):
        _fail("V73 target certificate ledger changed")
    states = _reachable_states(adapter)
    transition_rows = []
    transition_cache = {}
    transition_queries = 0
    for index, (failure, distinction) in enumerate(
        zip(failures, distinctions, strict=True)
    ):
        if (
            failure.get("failure_index") != index
            or distinction.get("failure_index") != index
            or failure.get("ground_query_performed_before_failure") is not False
            or distinction.get("query_after_failed_certificate") is not True
            or distinction.get("ground_support_labels") != 1
            or failure.get("raw_state") != distinction.get("raw_state")
        ):
            _fail("V73 certificate-before-query ordering changed")
        raw = tuple(failure["raw_state"])
        state = states.get(raw)
        if state is None:
            _fail("V73 target ledger referenced an unreachable state")
        legal = tuple(sorted(adapter.action_key(action) for action in adapter.actions(state)))
        kind = distinction.get("distinction_kind")
        if kind == "QUERY_LOCAL_LEGAL_ACTION_SET":
            if (
                failure.get("failure_kind") != "MISSING_QUERY_LOCAL_LEGALITY_SUPPORT"
                or failure.get("action_key") is not None
                or distinction.get("legal_action_keys") != list(legal)
            ):
                _fail("V73 query-local legality receipt changed")
            continue
        if kind != "QUERY_LOCAL_EXACT_TRANSITION_SUPPORT":
            _fail("V73 local distinction kind changed")
        key = failure.get("action_key")
        if (
            failure.get("failure_kind")
            != "UNSEEN_TRANSITION_SUPPORT_PREVENTS_EXACT_BRANCH_PROOF"
            or type(key) is not int
            or key not in legal
            or distinction.get("action_key") != key
        ):
            _fail("V73 transition certificate receipt changed")
        expected_rows = []
        successors = []
        for offset, outcome in enumerate(
            adapter.kernel.step(state, adapter.action(key))
        ):
            successor = outcome.next_state
            successors.append(adapter.encode(successor))
            legal_after = tuple(
                sorted(
                    adapter.action_key(action)
                    for action in adapter.actions(successor)
                )
            )
            expected_rows.append(
                {
                    "occurrence": 0,
                    "transition_index": (
                        len(observed_rows) + len(transition_rows) + offset
                    ),
                    "pre_vector": list(raw),
                    "legal_action_keys_before": list(legal),
                    "selected_action": adapter.catalogue[key].to_document(),
                    "post_vector": list(adapter.encode(successor)),
                    "legal_action_keys_after": list(legal_after),
                    "terminal_acceptance_after": (
                        None if legal_after else adapter.success(successor)
                    ),
                    "outcome_tape_sha256": None,
                }
            )
        if distinction.get("raw_transition_rows") != expected_rows:
            _fail("V73 target ground transition support changed")
        transition_rows.extend(expected_rows)
        transition_cache[(raw, key)] = tuple(successors)
        transition_queries += 1
    if (
        transition_rows != raw_rows
        or transition_queries != episode.get("queried_state_action_count")
    ):
        _fail("V73 target transition-cache accounting changed")

    memo: dict[tuple[int, ...], bool] = {}
    visiting = set()

    def closes(raw: tuple[int, ...]) -> bool:
        if raw in memo:
            return memo[raw]
        state = states[raw]
        if adapter.success(state):
            memo[raw] = True
            return True
        if not adapter.active(state) or raw in visiting:
            return False
        visiting.add(raw)
        for key in sorted(adapter.action_key(action) for action in adapter.actions(state)):
            successors = transition_cache.get((raw, key))
            if successors is not None and all(closes(successor) for successor in successors):
                visiting.remove(raw)
                memo[raw] = True
                return True
        visiting.remove(raw)
        memo[raw] = False
        return False

    if not closes(adapter.encode(adapter.initial())):
        _fail("V73 target query-local exact overlay did not close a proof")
    state = adapter.initial()
    actions = episode.get("action_keys")
    tapes = episode.get("outcome_tape_sha256")
    if type(actions) is not list or type(tapes) is not list or len(actions) != len(tapes):
        _fail("V73 target execution trace changed")
    for decision, (key, expected_tape) in enumerate(zip(actions, tapes, strict=True)):
        legal = {adapter.action_key(action) for action in adapter.actions(state)}
        if key not in legal:
            _fail("V73 target execution selected an illegal action")
        outcome, tape = adapter.select_outcome(
            state, key, pre.TARGET_EPISODE_INDEX, decision
        )
        if tape != expected_tape:
            _fail("V73 target outcome tape changed")
        state = outcome.next_state
    if (
        len(actions) != episode.get("execution_steps")
        or adapter.active(state)
        or not adapter.success(state)
    ):
        _fail("V73 target execution did not finish in success")
    locks = {
        "target_outcomes_used_to_refit_reusable_model": False,
        "same_exact_query_local_certificate_engine": True,
        "all_ground_queries_followed_failed_certificates": True,
        "query_local_exact_overlay_exclusively_used_for_safety": True,
        "reusable_abstract_model_used_as_safety_authority": False,
        "empirical_version_space_promoted_to_global_exact_dynamics": False,
        "complete_world_model_synthesized": False,
    }
    if any(episode.get(key) != value for key, value in locks.items()):
        _fail("V73 target claim locks changed")
    if expected_model_id is None:
        if (
            episode.get("arm") != "STRICT_NO_REUSABLE_MODEL"
            or episode.get("abstract_plan_attempt_count") != 0
            or episode.get("abstract_plan_success_count") != 0
            or episode.get("abstract_planning_compute_events") != 0
        ):
            _fail("V73 strict target arm received abstract-model work")
    elif (
        episode.get("arm") != "REUSABLE_JOINT_VERSION_SPACE_MODEL"
        or episode.get("abstract_plan_success_count", 0) <= 0
        or episode.get("reusable_model_frozen_before_target_episode") is not True
    ):
        _fail("V73 derived target arm omitted reusable planning")


def _consumed(acquisition: Mapping[str, Any]) -> int:
    value = acquisition.get("stopped_physical_ground_support_labels")
    if value is None:
        value = acquisition.get("full_query_stream_ground_support_labels")
    if type(value) is not int:
        _fail("V73 source-acquisition label accounting changed")
    return value


def verify_reusable_version_space_campaign_bytes_v73(raw: bytes) -> bytes:
    if type(raw) is not bytes:
        _fail("V73 campaign input must be exact bytes")
    document = loads_canonical_json(raw)
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail("V73 campaign bytes are not canonical")
    if (
        len(raw) != CAMPAIGN_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != CAMPAIGN_SHA256
        or document.get("campaign_id") != CAMPAIGN_ID
    ):
        _fail("V73 frozen campaign identity changed")
    _content(
        document,
        "campaign_id",
        domains.CONSTRUCTION_K7_REUSABLE_VERSION_SPACE_CAMPAIGN_V73_DOMAIN,
    )
    if (
        document.get("preregistration_id") != PREREGISTRATION_ID
        or document.get("v72r1_campaign_id") != V72R1_CAMPAIGN_ID
        or document.get("v72r1_verification_id") != V72R1_VERIFICATION_ID
        or document.get("template_library_artifact_id")
        != TEMPLATE_LIBRARY_ARTIFACT_ID
    ):
        _fail("V73 predecessor identity changed")
    template_artifact = verify_role_free_relational_template_library_v70(
        freeze_role_free_relational_template_library_v70()
    )
    residual_artifact = verify_residual_factor_library_v62(
        freeze_residual_factor_library_v62()
    )
    if template_artifact.library_artifact_id != TEMPLATE_LIBRARY_ARTIFACT_ID:
        _fail("V73 template library changed")
    template_document = template_artifact.to_document()
    library = template_document["compiled_template_library"]
    residual_library = residual_artifact.to_document()["compiled_library"]
    residual_id = residual_library["residual_factor_library_id"]
    factor_library = (
        v70_pre.previous.previous.previous.previous.previous.previous.previous.FACTOR_LIBRARY
    )
    config = pre.campaign_config_v73()
    occurrences = document.get("occurrences")
    expected_identities = [
        (family, seed)
        for family, seeds in config["target_seeds"].items()
        for seed in seeds
    ]
    if (
        type(occurrences) is not list
        or len(occurrences) != len(expected_identities)
        or [(row.get("family"), row.get("seed")) for row in occurrences]
        != expected_identities
    ):
        _fail("V73 occurrence identity inventory changed")
    compiled = []
    comparable = []
    source_failed = 0
    target_failures = 0
    ood_rejections = 0
    source_episodes = []
    for occurrence in occurrences:
        _content(
            occurrence,
            "occurrence_id",
            domains.CONSTRUCTION_K7_REUSABLE_VERSION_SPACE_OCCURRENCE_V73_DOMAIN,
        )
        family, seed = occurrence["family"], occurrence["seed"]
        adapter = base.predecessor.predecessor.prior_ground._adapter(  # noqa: SLF001
            family, seed, config
        )
        partial = base.acquire_matched_true_bit_models_v59(
            adapter, factor_library, config
        )["ANONYMOUS_FACTOR_PRIOR_ON"]
        if (
            occurrence.get("common_partial_acquisition_id")
            != partial["document"]["acquisition_id"]
            or occurrence.get("common_partial_ground_support_labels")
            != partial["document"]["ground_support_labels"]
        ):
            _fail("V73 common partial acquisition changed")
        envelope = occurrence.get("source_complete_episode")
        source = occurrence.get("retained_source_evidence")
        if type(envelope) is not dict or type(source) is not dict:
            _fail("V73 retained source changed")
        evidence = envelope.get("terminal_program_source_evidence")
        source_episode = envelope.get("predecessor_v30_episode")
        source_episodes.append(source_episode)
        if source != {
            "layout": evidence.get("layout"),
            "unknown_residual_target_columns": evidence.get(
                "unknown_residual_target_columns"
            ),
            "raw_transition_rows": evidence.get("raw_transition_rows"),
        }:
            _fail("V73 source evidence join changed")
        envelope_payload = {
            key: value for key, value in envelope.items()
            if key != "source_complete_episode_id"
        }
        if (
            _generic_id(_SOURCE_EPISODE_DOMAIN, envelope_payload)
            != envelope.get("source_complete_episode_id")
            or source_episode.get("success") is not True
            or source_episode.get("all_ground_queries_followed_failed_certificates")
            is not True
            or source_episode.get(
                "query_local_exact_overlay_exclusively_used_for_safety"
            )
            is not True
        ):
            _fail("V73 source episode identity or safety changed")
        verify_source_complete_relational_program_v32(
            source, source_episode["final_relational_terminal_program"]
        )
        acquisition = _source_acquisition(source, library, residual_id)
        if acquisition != occurrence.get("source_relation_covering_acquisition"):
            _fail("V73 source acquisition reconstruction changed")
        learned = acquisition["learned_successor_acquisition"]
        source_failed += learned["status"] == (
            "PROPOSAL_ISSUED_HELDOUT_FAILED_NONCERTIFICATE"
        )
        expected_model = _expected_model(
            occurrence, partial["candidate"], source, acquisition
        )
        actual_model = occurrence.get("reusable_joint_successor_version_space_model")
        if expected_model != actual_model:
            _fail("V73 joint successor version-space reconstruction changed")
        if expected_model is None:
            if (
                occurrence.get("target_ablation_arms") is not None
                or occurrence.get("incompatible_schema_ood_control", {}).get("status")
                != "NOT_RUN_SOURCE_MODEL_UNAVAILABLE"
            ):
                _fail("V73 abstained source leaked into target execution")
            continue
        compiled.append(occurrence)
        model_id = expected_model["joint_successor_version_space_model_id"]
        arms = occurrence.get("target_ablation_arms")
        if type(arms) is not dict or set(arms) != {
            "REUSABLE_JOINT_VERSION_SPACE_MODEL",
            "STRICT_NO_REUSABLE_MODEL",
        }:
            _fail("V73 target arm inventory changed")
        if all(arm.get("success") is True for arm in arms.values()):
            comparable.append(occurrence)
        else:
            target_failures += 1
        _verify_target_episode(
            arms["REUSABLE_JOINT_VERSION_SPACE_MODEL"],
            adapter,
            partial["rows"],
            model_id,
        )
        _verify_target_episode(
            arms["STRICT_NO_REUSABLE_MODEL"],
            adapter,
            partial["rows"],
            None,
        )
        ood = occurrence.get("incompatible_schema_ood_control")
        if (
            type(ood) is not dict
            or ood.get("status")
            != "INCOMPATIBLE_SCHEMA_REJECTED_BEFORE_ABSTRACT_SEARCH"
            or ood.get("ground_transition_accessed") is not False
        ):
            _fail("V73 incompatible-schema control changed")
        ood_rejections += 1
    derived_labels = sum(
        row["target_ablation_arms"]["REUSABLE_JOINT_VERSION_SPACE_MODEL"][
            "target_certificate_local_ground_support_labels"
        ]
        for row in comparable
    )
    strict_labels = sum(
        row["target_ablation_arms"]["STRICT_NO_REUSABLE_MODEL"][
            "target_certificate_local_ground_support_labels"
        ]
        for row in comparable
    )
    reduction_count = sum(
        row["target_ablation_arms"]["REUSABLE_JOINT_VERSION_SPACE_MODEL"][
            "target_certificate_local_ground_support_labels"
        ]
        < row["target_ablation_arms"]["STRICT_NO_REUSABLE_MODEL"][
            "target_certificate_local_ground_support_labels"
        ]
        for row in comparable
    )
    sample = {
        "compiled_occurrence_count": len(compiled),
        "matched_successful_target_occurrence_count": len(comparable),
        "target_occurrence_with_strict_reduction_count": reduction_count,
        "derived_target_certificate_local_labels": derived_labels,
        "strict_target_certificate_local_labels": strict_labels,
        "derived_minus_strict_target_labels": derived_labels - strict_labels,
        "fresh_actual_target_sample_reduction_observed": bool(comparable)
        and derived_labels < strict_labels,
        "source_acquisition_cost_amortization_evaluated": False,
        "economics_claimed": False,
    }
    if document.get("sample_tax_comparison") != sample:
        _fail("V73 sample-tax comparison changed")
    accounting = {
        "offline_template_source_labels": template_document[
            "offline_template_source_ground_support_labels"
        ],
        "offline_residual_library_labels": config["offline_library_labels"],
        "source_common_partial_labels": sum(
            row["common_partial_ground_support_labels"] for row in occurrences
        ),
        "source_certificate_local_labels": sum(
            row["local_ground_support_labels"] for row in source_episodes
        ),
        "source_execution_steps": sum(row["execution_steps"] for row in source_episodes),
        "source_partial_planning_compute_events": sum(
            row["partial_planning_compute_events"] for row in source_episodes
        ),
        "source_relational_planning_compute_events": sum(
            row["relational_abstract_support_branch_evaluations"]
            for row in source_episodes
        ),
        "source_acquisition_consumed_labels": sum(
            _consumed(
                row["source_relation_covering_acquisition"][
                    "learned_successor_acquisition"
                ]
            )
            for row in occurrences
        ),
        "target_derived_certificate_local_labels": derived_labels,
        "target_strict_certificate_local_labels": strict_labels,
        "target_derived_execution_steps": sum(
            row["target_ablation_arms"]["REUSABLE_JOINT_VERSION_SPACE_MODEL"][
                "execution_steps"
            ]
            for row in comparable
        ),
        "target_strict_execution_steps": sum(
            row["target_ablation_arms"]["STRICT_NO_REUSABLE_MODEL"][
                "execution_steps"
            ]
            for row in comparable
        ),
        "target_derived_abstract_planning_compute_events": sum(
            row["target_ablation_arms"]["REUSABLE_JOINT_VERSION_SPACE_MODEL"][
                "abstract_planning_compute_events"
            ]
            for row in comparable
        ),
        "target_strict_abstract_planning_compute_events": 0,
        "all_axes_separate": True,
        "source_labels_not_subtracted_from_target_label_comparison": True,
    }
    if document.get("accounting") != accounting:
        _fail("V73 accounting reconstruction changed")
    certificate_clean = all(
        arm["all_ground_queries_followed_failed_certificates"] is True
        and arm["query_local_exact_overlay_exclusively_used_for_safety"] is True
        and arm["reusable_abstract_model_used_as_safety_authority"] is False
        for row in comparable
        for arm in row["target_ablation_arms"].values()
    )
    aggregate_reduction = bool(comparable) and derived_labels < strict_labels
    gate = {
        "source_heldout_failed_noncertificate_count": source_failed,
        "compiled_occurrence_count": len(compiled),
        "required_minimum_compiled_occurrence_count": 3,
        "matched_successful_target_occurrence_count": len(comparable),
        "target_failure_count": target_failures,
        "incompatible_schema_ood_rejection_count": ood_rejections,
        "required_incompatible_schema_ood_rejection_count": len(compiled),
        "certificate_discipline_clean": certificate_clean,
        "aggregate_actual_target_label_reduction_required": True,
        "aggregate_actual_target_label_reduction_observed": aggregate_reduction,
        "minimum_reduced_occurrence_count": 1,
        "actual_reduced_occurrence_count": reduction_count,
        "passed": (
            source_failed == 0
            and len(compiled) >= 3
            and len(comparable) == len(compiled)
            and target_failures == 0
            and ood_rejections == len(compiled)
            and certificate_clean
            and aggregate_reduction
            and reduction_count >= 1
        ),
    }
    if document.get("registered_gate") != gate or gate["passed"] is not True:
        _fail("V73 registered Gate changed")
    locks = {
        "same_exact_target_certificate_engine_in_both_arms": True,
        "only_reusable_model_availability_differs_between_target_arms": True,
        "source_model_frozen_before_every_target_episode": True,
        "target_outcomes_used_to_refit_reusable_models": False,
        "all_ground_queries_followed_failed_certificates": True,
        "query_local_exact_overlay_exclusively_used_for_safety": True,
        "producer_free_verification_present": False,
        "online_adaptive_model_refit_integrated": False,
        "complete_world_model_synthesized": False,
        "global_exact_dynamics_claimed": False,
        "arbitrary_domain_transfer_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    if any(document.get(key) != value for key, value in locks.items()):
        _fail("V73 campaign claim locks changed")
    payload = {
        "schema": "acfqp.reusable_version_space_verification.v73",
        "campaign_id": CAMPAIGN_ID,
        "occurrence_count": len(occurrences),
        "source_relation_covering_acquisitions_reconstructed": len(occurrences),
        "joint_successor_version_space_models_reconstructed": len(compiled),
        "target_certificate_episode_traces_replayed": 2 * len(comparable),
        "target_certificate_local_labels_recomputed": derived_labels + strict_labels,
        "target_exact_overlay_proofs_reclosed": 2 * len(comparable),
        "incompatible_schema_ood_controls_verified": ood_rejections,
        "derived_target_certificate_local_labels": derived_labels,
        "strict_target_certificate_local_labels": strict_labels,
        "derived_minus_strict_target_labels": derived_labels - strict_labels,
        "actual_reduced_occurrence_count": reduction_count,
        "fresh_actual_target_sample_reduction_observed": aggregate_reduction,
        "all_accounting_axes_recomputed": True,
        "v73_campaign_producer_imported": False,
        "v73_campaign_core_imported": False,
        "v42_model_compiler_imported": False,
        "v43_target_planner_imported": False,
        "source_cost_amortization_evaluated": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "status": "PRODUCER_FREE_REUSABLE_VERSION_SPACE_EVIDENCE_VERIFIED",
    }
    verification = {
        **payload,
        "verification_id": domains.extension_content_id_v73(
            domains.CONSTRUCTION_K7_REUSABLE_VERSION_SPACE_VERIFICATION_V73_DOMAIN,
            payload,
        ),
    }
    result = canonical_json_bytes(verification)
    if VERIFICATION_ID != "0" * 64 and (
        verification["verification_id"] != VERIFICATION_ID
        or len(result) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(result).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V73 verification changed")
    return result


__all__ = ("verify_reusable_version_space_campaign_bytes_v73",)
