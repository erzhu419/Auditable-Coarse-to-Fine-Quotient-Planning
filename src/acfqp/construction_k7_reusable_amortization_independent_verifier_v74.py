"""Producer-free semantic reconstruction of the frozen V74 campaign.

The verifier does not import or call the V74 campaign producer/core, V42 model
compiler, or V43 planner.  It reuses the frozen V73 producer-free reconstruction
primitives, reconstructs each source model from retained observations, enumerates
the ground kernel, and replays every V74 target certificate/overlay/execution
trace before recomputing the incremental sample-amortization ledger.
"""

from __future__ import annotations

from collections import deque
import hashlib
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v74 as domains
from acfqp import construction_k7_reusable_version_space_independent_verifier_v73 as v73_replay
from acfqp import construction_k7_reusable_version_space_preregistration_v73 as v73_pre
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


CAMPAIGN_ID = "a60009b54923558baca3dd26af35c298b6618a86c3c4ec64639d7efa4c7a76f4"
CAMPAIGN_BYTE_COUNT = 16_861_847
CAMPAIGN_SHA256 = "c71d4cd434e40a2f4e8a6d19a5442e11b35a13c0026a2d93eae7ba02a94c7669"
PREREGISTRATION_ID = "9eb5e746c44fd34632b959c41c9037193accfe3ce71f322a49b04f2062044c9d"
V73_CAMPAIGN_ID = "5a896a845e4767f78c30e183b11a11e66ecf98a2cad56dabd739fdec11c941be"
V73_VERIFICATION_ID = "fdc8e7f5294bc448e7e08986fee62d19ca6811388aa5ab4b66016976169e3cf8"
TEMPLATE_LIBRARY_ARTIFACT_ID = "8657115a19bace2861b3a14ff780a2708b6e76101a2b7468e52e5285a113b2a9"
TARGET_EPISODE_INDICES = tuple(range(2, 34))
VERIFICATION_ID = "c43f1028c19871433bd0470fa37f5f2977a20bb1f31f94d3b0005db8d30f877f"
EXPECTED_CANONICAL_BYTE_COUNT = 1_121
EXPECTED_CANONICAL_SHA256 = "2aa67e5ecea669787b511919e95101054e0787c199934a3a3294c6a107bb6869"

_SOURCE_EPISODE_DOMAIN = b"acfqp:generic-source-complete-relational-world-model:v31\x00"
_TARGET_EPISODE_DOMAIN = b"acfqp:generic-reusable-version-space-certificate-episode:v43\x00"


class ConstructionK7ReusableAmortizationIndependentVerifierV74Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7ReusableAmortizationIndependentVerifierV74Error(message)


def _generic_id(domain: bytes, payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(domain + canonical_json_bytes(payload)).hexdigest()


def _content(document: Mapping[str, Any], key: str, domain: str) -> None:
    if type(document) is not dict or type(document.get(key)) is not str:
        _fail(f"V74 {key} inventory changed")
    payload = {name: value for name, value in document.items() if name != key}
    if domains.extension_content_id_v74(domain, payload) != document[key]:
        _fail(f"V74 {key} content identity changed")


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
                    _fail("V74 raw state encoding is not injective")
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
    expected_episode_index: int,
    states: Mapping[tuple[int, ...], Any],
) -> None:
    if type(episode) is not dict or episode.get("success") is not True:
        _fail("V74 target episode did not succeed")
    payload = {key: value for key, value in episode.items() if key != "episode_id"}
    if (
        _generic_id(_TARGET_EPISODE_DOMAIN, payload) != episode.get("episode_id")
        or episode.get("family") != adapter.family
        or episode.get("seed") != adapter.seed
        or episode.get("episode_index") != expected_episode_index
        or episode.get("model_source_episode_index") != v73_pre.SOURCE_EPISODE_INDEX
        or episode.get("joint_successor_version_space_model_id")
        != expected_model_id
    ):
        _fail("V74 target episode identity changed")
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
        _fail("V74 target certificate ledger changed")
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
            _fail("V74 certificate-before-query ordering changed")
        raw = tuple(failure["raw_state"])
        state = states.get(raw)
        if state is None:
            _fail("V74 target ledger referenced an unreachable state")
        legal = tuple(sorted(adapter.action_key(action) for action in adapter.actions(state)))
        kind = distinction.get("distinction_kind")
        if kind == "QUERY_LOCAL_LEGAL_ACTION_SET":
            if (
                failure.get("failure_kind") != "MISSING_QUERY_LOCAL_LEGALITY_SUPPORT"
                or failure.get("action_key") is not None
                or distinction.get("legal_action_keys") != list(legal)
            ):
                _fail("V74 query-local legality receipt changed")
            continue
        if kind != "QUERY_LOCAL_EXACT_TRANSITION_SUPPORT":
            _fail("V74 local distinction kind changed")
        key = failure.get("action_key")
        if (
            failure.get("failure_kind")
            != "UNSEEN_TRANSITION_SUPPORT_PREVENTS_EXACT_BRANCH_PROOF"
            or type(key) is not int
            or key not in legal
            or distinction.get("action_key") != key
        ):
            _fail("V74 transition certificate receipt changed")
        expected_rows = []
        successors = []
        for offset, outcome in enumerate(adapter.kernel.step(state, adapter.action(key))):
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
                    "transition_index": len(observed_rows) + len(transition_rows) + offset,
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
            _fail("V74 target ground transition support changed")
        transition_rows.extend(expected_rows)
        transition_cache[(raw, key)] = tuple(successors)
        transition_queries += 1
    if (
        transition_rows != raw_rows
        or transition_queries != episode.get("queried_state_action_count")
    ):
        _fail("V74 target transition-cache accounting changed")

    memo: dict[tuple[int, ...], bool] = {}
    visiting: set[tuple[int, ...]] = set()

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
        _fail("V74 target query-local exact overlay did not close a proof")
    state = adapter.initial()
    actions = episode.get("action_keys")
    tapes = episode.get("outcome_tape_sha256")
    if type(actions) is not list or type(tapes) is not list or len(actions) != len(tapes):
        _fail("V74 target execution trace changed")
    for decision, (key, expected_tape) in enumerate(zip(actions, tapes, strict=True)):
        legal = {adapter.action_key(action) for action in adapter.actions(state)}
        if key not in legal:
            _fail("V74 target execution selected an illegal action")
        outcome, tape = adapter.select_outcome(
            state, key, expected_episode_index, decision
        )
        if tape != expected_tape:
            _fail("V74 target outcome tape changed")
        state = outcome.next_state
    if (
        len(actions) != episode.get("execution_steps")
        or adapter.active(state)
        or not adapter.success(state)
    ):
        _fail("V74 target execution did not finish in success")
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
        _fail("V74 target claim locks changed")
    if expected_model_id is None:
        if (
            episode.get("arm") != "STRICT_NO_REUSABLE_MODEL"
            or episode.get("abstract_plan_attempt_count") != 0
            or episode.get("abstract_plan_success_count") != 0
            or episode.get("abstract_planning_compute_events") != 0
        ):
            _fail("V74 strict target arm received abstract-model work")
    elif (
        episode.get("arm") != "REUSABLE_JOINT_VERSION_SPACE_MODEL"
        or episode.get("abstract_plan_success_count", 0) <= 0
        or episode.get("reusable_model_frozen_before_target_episode") is not True
    ):
        _fail("V74 derived target arm omitted reusable planning")


def verify_reusable_amortization_campaign_bytes_v74(raw: bytes) -> bytes:
    if type(raw) is not bytes:
        _fail("V74 campaign input must be exact bytes")
    document = loads_canonical_json(raw)
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail("V74 campaign bytes are not canonical")
    if (
        len(raw) != CAMPAIGN_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != CAMPAIGN_SHA256
        or document.get("campaign_id") != CAMPAIGN_ID
    ):
        _fail("V74 frozen campaign identity changed")
    _content(
        document,
        "campaign_id",
        domains.CONSTRUCTION_K7_REUSABLE_AMORTIZATION_CAMPAIGN_V74_DOMAIN,
    )
    if (
        document.get("preregistration_id") != PREREGISTRATION_ID
        or document.get("v73_campaign_id") != V73_CAMPAIGN_ID
        or document.get("v73_verification_id") != V73_VERIFICATION_ID
        or document.get("template_library_artifact_id")
        != TEMPLATE_LIBRARY_ARTIFACT_ID
    ):
        _fail("V74 predecessor identity changed")
    template_artifact = verify_role_free_relational_template_library_v70(
        freeze_role_free_relational_template_library_v70()
    )
    residual_artifact = verify_residual_factor_library_v62(
        freeze_residual_factor_library_v62()
    )
    if template_artifact.library_artifact_id != TEMPLATE_LIBRARY_ARTIFACT_ID:
        _fail("V74 template library changed")
    template_document = template_artifact.to_document()
    template_library = template_document["compiled_template_library"]
    residual_library = residual_artifact.to_document()["compiled_library"]
    residual_id = residual_library["residual_factor_library_id"]
    factor_library = (
        v70_pre.previous.previous.previous.previous.previous.previous.previous.FACTOR_LIBRARY
    )
    config = v73_pre.campaign_config_v73()
    config["amortization_target_episode_indices"] = TARGET_EPISODE_INDICES
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
        _fail("V74 occurrence identity inventory changed")

    compiled = []
    source_episodes = []
    source_failed = 0
    target_failures = 0
    replayed_traces = 0
    exact_overlay_proofs = 0
    for occurrence in occurrences:
        _content(
            occurrence,
            "occurrence_id",
            domains.CONSTRUCTION_K7_REUSABLE_AMORTIZATION_OCCURRENCE_V74_DOMAIN,
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
            _fail("V74 common partial acquisition changed")
        envelope = occurrence.get("source_complete_episode")
        source = occurrence.get("retained_source_evidence")
        if type(envelope) is not dict or type(source) is not dict:
            _fail("V74 retained source changed")
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
            _fail("V74 source evidence join changed")
        envelope_payload = {
            key: value
            for key, value in envelope.items()
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
            _fail("V74 source episode identity or safety changed")
        verify_source_complete_relational_program_v32(
            source, source_episode["final_relational_terminal_program"]
        )
        acquisition = v73_replay._source_acquisition(  # noqa: SLF001
            source, template_library, residual_id
        )
        if acquisition != occurrence.get("source_relation_covering_acquisition"):
            _fail("V74 source acquisition reconstruction changed")
        learned = acquisition["learned_successor_acquisition"]
        source_failed += learned["status"] == (
            "PROPOSAL_ISSUED_HELDOUT_FAILED_NONCERTIFICATE"
        )
        expected_model = v73_replay._expected_model(  # noqa: SLF001
            occurrence, partial["candidate"], source, acquisition
        )
        actual_model = occurrence.get("reusable_joint_successor_version_space_model")
        if expected_model != actual_model:
            _fail("V74 joint successor version-space reconstruction changed")
        targets = occurrence.get("target_episode_ablations")
        if expected_model is None:
            if targets != [] or occurrence.get("source_model_frozen_once_before_all_target_episodes") is not False:
                _fail("V74 abstained source leaked into target execution")
            continue
        compiled.append(occurrence)
        model_id = expected_model["joint_successor_version_space_model_id"]
        if (
            type(targets) is not list
            or [row.get("target_episode_index") for row in targets]
            != list(TARGET_EPISODE_INDICES)
        ):
            _fail("V74 target episode inventory changed")
        states = _reachable_states(adapter)
        for target in targets:
            episode_index = target["target_episode_index"]
            arms = target.get("arms")
            if type(arms) is not dict or set(arms) != {
                "REUSABLE_JOINT_VERSION_SPACE_MODEL",
                "STRICT_NO_REUSABLE_MODEL",
            }:
                _fail("V74 target arm inventory changed")
            target_failures += sum(
                arm.get("success") is not True for arm in arms.values()
            )
            _verify_target_episode(
                arms["REUSABLE_JOINT_VERSION_SPACE_MODEL"],
                adapter,
                partial["rows"],
                model_id,
                episode_index,
                states,
            )
            _verify_target_episode(
                arms["STRICT_NO_REUSABLE_MODEL"],
                adapter,
                partial["rows"],
                None,
                episode_index,
                states,
            )
            replayed_traces += 2
            exact_overlay_proofs += 2

    source_investment = sum(
        row["source_complete_episode"]["predecessor_v30_episode"][
            "local_ground_support_labels"
        ]
        for row in compiled
    )
    episode_rows = []
    cumulative = 0
    break_even = None
    for ordinal, episode_index in enumerate(TARGET_EPISODE_INDICES, 1):
        matching = [
            episode
            for row in compiled
            for episode in row["target_episode_ablations"]
            if episode["target_episode_index"] == episode_index
        ]
        derived = sum(
            episode["arms"]["REUSABLE_JOINT_VERSION_SPACE_MODEL"][
                "target_certificate_local_ground_support_labels"
            ]
            for episode in matching
        )
        strict = sum(
            episode["arms"]["STRICT_NO_REUSABLE_MODEL"][
                "target_certificate_local_ground_support_labels"
            ]
            for episode in matching
        )
        savings = strict - derived
        cumulative += savings
        if break_even is None and cumulative >= source_investment:
            break_even = ordinal
        episode_rows.append(
            {
                "episode_ordinal": ordinal,
                "target_episode_index": episode_index,
                "matched_compiled_occurrence_count": len(matching),
                "derived_target_labels": derived,
                "strict_target_labels": strict,
                "episode_label_savings": savings,
                "cumulative_target_label_savings": cumulative,
                "incremental_source_model_label_investment": source_investment,
                "incremental_source_investment_repaid": cumulative
                >= source_investment,
            }
        )
    positive_each = bool(episode_rows) and all(
        row["episode_label_savings"] > 0 for row in episode_rows
    )
    expected_amortization = {
        "incremental_source_model_label_investment": source_investment,
        "target_episode_rows": episode_rows,
        "target_episode_count": len(episode_rows),
        "every_target_episode_has_positive_aggregate_savings": positive_each,
        "empirical_incremental_break_even_episode_ordinal": break_even,
        "incremental_break_even_observed_within_registered_horizon": break_even
        is not None,
        "shared_partial_acquisition_cost_excluded_as_common_to_both_arms": True,
        "offline_prior_library_cost_excluded": True,
        "planning_compute_excluded_from_sample_break_even": True,
        "official_N_break_even_claimed": False,
        "economics_claimed": False,
    }
    if document.get("incremental_sample_amortization") != expected_amortization:
        _fail("V74 incremental sample-amortization ledger changed")
    accounting = {
        "offline_template_source_labels": template_document[
            "offline_template_source_ground_support_labels"
        ],
        "offline_residual_library_labels": config["offline_library_labels"],
        "source_common_partial_labels": sum(
            row["common_partial_ground_support_labels"] for row in occurrences
        ),
        "source_certificate_local_labels_all_occurrences": sum(
            row["local_ground_support_labels"] for row in source_episodes
        ),
        "incremental_source_model_labels_compiled_occurrences": source_investment,
        "source_execution_steps": sum(row["execution_steps"] for row in source_episodes),
        "source_relational_planning_compute_events": sum(
            row["relational_abstract_support_branch_evaluations"]
            for row in source_episodes
        ),
        "target_derived_certificate_local_labels": sum(
            row["derived_target_labels"] for row in episode_rows
        ),
        "target_strict_certificate_local_labels": sum(
            row["strict_target_labels"] for row in episode_rows
        ),
        "target_derived_execution_steps": sum(
            episode["arms"]["REUSABLE_JOINT_VERSION_SPACE_MODEL"]["execution_steps"]
            for row in compiled
            for episode in row["target_episode_ablations"]
        ),
        "target_strict_execution_steps": sum(
            episode["arms"]["STRICT_NO_REUSABLE_MODEL"]["execution_steps"]
            for row in compiled
            for episode in row["target_episode_ablations"]
        ),
        "target_derived_abstract_planning_compute_events": sum(
            episode["arms"]["REUSABLE_JOINT_VERSION_SPACE_MODEL"][
                "abstract_planning_compute_events"
            ]
            for row in compiled
            for episode in row["target_episode_ablations"]
        ),
        "target_strict_abstract_planning_compute_events": 0,
        "all_axes_separate": True,
    }
    if document.get("accounting") != accounting:
        _fail("V74 accounting reconstruction changed")
    certificate_clean = all(
        arm["all_ground_queries_followed_failed_certificates"] is True
        and arm["query_local_exact_overlay_exclusively_used_for_safety"] is True
        and arm["reusable_abstract_model_used_as_safety_authority"] is False
        for row in compiled
        for episode in row["target_episode_ablations"]
        for arm in episode["arms"].values()
    )
    expected_target_count = len(compiled) * len(TARGET_EPISODE_INDICES)
    gate = {
        "source_heldout_failed_noncertificate_count": source_failed,
        "compiled_occurrence_count": len(compiled),
        "required_minimum_compiled_occurrence_count": 3,
        "expected_matched_target_episode_count": expected_target_count,
        "actual_matched_target_episode_count": sum(
            len(row["target_episode_ablations"]) for row in compiled
        ),
        "target_arm_failure_count": target_failures,
        "certificate_discipline_clean": certificate_clean,
        "positive_aggregate_savings_required_in_every_target_episode": True,
        "positive_aggregate_savings_observed_in_every_target_episode": positive_each,
        "incremental_break_even_required_within_registered_horizon": True,
        "incremental_break_even_observed_within_registered_horizon": break_even
        is not None,
        "passed": (
            source_failed == 0
            and len(compiled) >= 3
            and target_failures == 0
            and sum(len(row["target_episode_ablations"]) for row in compiled)
            == expected_target_count
            and certificate_clean
            and positive_each
            and break_even is not None
        ),
    }
    if document.get("registered_gate") != gate or gate["passed"] is not True:
        _fail("V74 registered Gate changed")
    locks = {
        "source_model_frozen_once_before_all_target_episodes": True,
        "fresh_exact_overlay_for_every_arm_episode": True,
        "all_ground_queries_followed_failed_certificates": True,
        "query_local_exact_overlay_exclusively_used_for_safety": True,
        "producer_free_verification_present": False,
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
        _fail("V74 campaign claim locks changed")
    payload = {
        "schema": "acfqp.reusable_amortization_verification.v74",
        "campaign_id": CAMPAIGN_ID,
        "occurrence_count": len(occurrences),
        "source_relation_covering_acquisitions_reconstructed": len(occurrences),
        "joint_successor_version_space_models_reconstructed": len(compiled),
        "target_certificate_episode_traces_replayed": replayed_traces,
        "target_certificate_local_labels_recomputed": sum(
            row["derived_target_labels"] + row["strict_target_labels"]
            for row in episode_rows
        ),
        "target_exact_overlay_proofs_reclosed": exact_overlay_proofs,
        "incremental_source_model_label_investment": source_investment,
        "empirical_incremental_break_even_episode_ordinal": break_even,
        "final_cumulative_target_label_savings": cumulative,
        "all_32_episode_amortization_rows_recomputed": len(episode_rows) == 32,
        "all_accounting_axes_recomputed": True,
        "v74_campaign_producer_imported_or_called": False,
        "v74_campaign_core_imported_or_called": False,
        "v42_model_compiler_called": False,
        "v43_target_planner_called": False,
        "official_economics_verified": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "status": "PRODUCER_FREE_REUSABLE_AMORTIZATION_EVIDENCE_VERIFIED",
    }
    verification = {
        **payload,
        "verification_id": domains.extension_content_id_v74(
            domains.CONSTRUCTION_K7_REUSABLE_AMORTIZATION_VERIFICATION_V74_DOMAIN,
            payload,
        ),
    }
    result = canonical_json_bytes(verification)
    if VERIFICATION_ID != "0" * 64 and (
        verification["verification_id"] != VERIFICATION_ID
        or len(result) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(result).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V74 verification changed")
    return result


__all__ = ("verify_reusable_amortization_campaign_bytes_v74",)
