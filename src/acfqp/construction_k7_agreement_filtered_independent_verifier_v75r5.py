"""Producer-free verifier for the frozen V75r5 sample-tax evidence."""

from __future__ import annotations

from collections import deque
import hashlib
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v75r4 as domains_v75r4
from acfqp import construction_k7_domain_registry_extension_v75r5 as domains
from acfqp import construction_k7_reusable_version_space_preregistration_v73 as v73_pre
from acfqp import construction_k7_role_free_relational_transfer_preregistration_v70 as v70_pre
from acfqp import true_bit_symmetric_three_domain_campaign_core_v59 as base
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "09f60884721e863b864b539ff95e9e82a5de60de2755995fbf49cd1905b1ed5a"
CAMPAIGN_BYTE_COUNT = 2_736_048
CAMPAIGN_SHA256 = "e9f82b2a8b4bb43e911f8138b208a2951aa4f622b2ee9d7f83ca1ce5355b2809"
PREREGISTRATION_ID = "e3cd3b61db376a9e3a3addd0767300c6dda350a98d2853142992c6ba33e47a92"
TEMPLATE_LIBRARY_ARTIFACT_ID = "8657115a19bace2861b3a14ff780a2708b6e76101a2b7468e52e5285a113b2a9"
SOURCE_SEEDS = {"COUPLED_EXCHANGE": 752_102, "MAINTENANCE_CASCADE": 753_101}
TARGET_SEEDS = {
    "COUPLED_EXCHANGE": (766_201, 766_202),
    "MAINTENANCE_CASCADE": (766_301, 766_302),
}
TARGET_EPISODE_INDEX = 6
VERIFICATION_ID = "0" * 64
EXPECTED_CANONICAL_BYTE_COUNT = 0
EXPECTED_CANONICAL_SHA256 = "0" * 64

_MODEL_DOMAIN = b"acfqp:generic-joint-successor-version-space-model:v42\x00"
_V43_EPISODE_DOMAIN = b"acfqp:generic-reusable-version-space-certificate-episode:v43\x00"
_V44_EPISODE_DOMAIN = b"acfqp:generic-portable-priority-certificate-episode:v44\x00"
_V46_PRIOR_DOMAIN = b"acfqp:generic-structural-rank-query-prior:v46\x00"
_V46_TRANSLATION_DOMAIN = b"acfqp:generic-structural-rank-query-translation:v46\x00"
_V47_FILTER_DOMAIN = b"acfqp:generic-abstract-agreement-query-filter:v47\x00"

UNFILTERED = "UNFILTERED_STRUCTURAL_RANK_AND_MODEL"
FILTERED = "AGREEMENT_FILTERED_STRUCTURAL_RANK_AND_MODEL"
MODEL_ONLY = "MODEL_ONLY_WITH_INERT_MATCHED_PRIORITY"
STRICT = "STRICT_NO_MODEL_OR_PRIORITY"
ARMS = (UNFILTERED, FILTERED, MODEL_ONLY, STRICT)


class ConstructionK7AgreementFilteredIndependentVerifierV75R5Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7AgreementFilteredIndependentVerifierV75R5Error(message)


def _generic_id(domain: bytes, payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(domain + canonical_json_bytes(payload)).hexdigest()


def _content(document: Mapping[str, Any], key: str, domain: str, version: int) -> None:
    if type(document) is not dict or type(document.get(key)) is not str:
        _fail(f"V75r5 {key} inventory changed")
    payload = {name: value for name, value in document.items() if name != key}
    actual = (
        domains.extension_content_id_v75r5(domain, payload)
        if version == 5
        else domains_v75r4.extension_content_id_v75r4(domain, payload)
    )
    if actual != document[key]:
        _fail(f"V75r5 {key} content identity changed")


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
                    _fail("V75r5 raw encoding is not injective")
                if previous is None:
                    by_raw[raw] = successor
                    if adapter.active(successor):
                        queue.append(successor)
    return by_raw


def _verify_model(model: Mapping[str, Any]) -> str:
    if type(model) is not dict:
        _fail("V75r5 model changed")
    payload = {
        key: value for key, value in model.items()
        if key != "joint_successor_version_space_model_id"
    }
    identity = model.get("joint_successor_version_space_model_id")
    if (
        _generic_id(_MODEL_DOMAIN, payload) != identity
        or model.get("complete_world_model_claimed") is not False
        or model.get("abstract_plan_safety_authority_present") is not False
        or model.get("empirical_version_space_promoted_to_global_exact_dynamics")
        is not False
    ):
        _fail("V75r5 model identity or claim lock changed")
    return identity


def _rank_vector(
    selected: Mapping[str, Any],
    legal_keys: list[int],
    catalogue: tuple[Any, ...],
    action_order: list[int],
) -> list[int]:
    by_key = {row.key: row for row in catalogue}
    key = selected.get("action_key")
    if type(key) is not int or key not in by_key or any(value not in by_key for value in legal_keys):
        _fail("V75r5 source action rank inventory changed")
    canonical = {
        value: tuple(by_key[value].fields[index] for index in action_order)
        for value in legal_keys
    }
    chosen = canonical[key]
    return [
        sorted({row[index] for row in canonical.values()}).index(value)
        for index, value in enumerate(chosen)
    ]


def _state_signature(raw: list[int], state_order: list[int]) -> dict[str, Any]:
    state = tuple(raw[index] for index in state_order)
    return {
        "zero_mask": [index for index, value in enumerate(state) if value == 0],
        "equality_predecessors": [
            [right for right in range(left) if state[left] == state[right]]
            for left in range(len(state))
        ],
    }


def _verify_source(source: Mapping[str, Any], adapter: Any) -> tuple[str, str]:
    _content(
        source,
        "source_id",
        domains.CONSTRUCTION_K7_AGREEMENT_FILTERED_SOURCE_V75R5_DOMAIN,
        5,
    )
    predecessor = source.get("predecessor_v75r4_source")
    if type(predecessor) is not dict:
        _fail("V75r5 predecessor source changed")
    _content(
        predecessor,
        "source_id",
        domains_v75r4.CONSTRUCTION_K7_STRUCTURAL_RANK_SOURCE_V75R4_DOMAIN,
        4,
    )
    model = source.get("reusable_joint_successor_version_space_model")
    model_id = _verify_model(model)
    if model != predecessor.get("reusable_joint_successor_version_space_model"):
        _fail("V75r5 source model join changed")
    priority_source = predecessor.get("predecessor_v75r1_source")
    episode = priority_source.get("priority_source_episode") if type(priority_source) is dict else None
    if type(episode) is not dict or episode.get("success") is not True:
        _fail("V75r5 priority source episode changed")
    episode_payload = {key: value for key, value in episode.items() if key != "episode_id"}
    if (
        _generic_id(_V43_EPISODE_DOMAIN, episode_payload) != episode.get("episode_id")
        or episode.get("all_ground_queries_followed_failed_certificates") is not True
        or episode.get("query_local_exact_overlay_exclusively_used_for_safety") is not True
    ):
        _fail("V75r5 priority source identity changed")
    layout = model.get("source_layout")
    state_order = layout.get("state_canonical_to_raw") if type(layout) is dict else None
    action_order = layout.get("action_canonical_to_raw") if type(layout) is dict else None
    if type(state_order) is not list or type(action_order) is not list:
        _fail("V75r5 source layout changed")
    rules = []
    for distinction in episode.get("local_distinctions", []):
        if distinction.get("distinction_kind") != "QUERY_LOCAL_EXACT_TRANSITION_SUPPORT":
            continue
        rows = distinction.get("raw_transition_rows")
        raw_state = distinction.get("raw_state")
        if type(rows) is not list or not rows or type(raw_state) is not list:
            _fail("V75r5 source query row changed")
        first = rows[0]
        rule = {
            "source_query_index": len(rules),
            "source_state_signature": _state_signature(raw_state, state_order),
            "selected_action_rank_vector": _rank_vector(
                first["selected_action"],
                first["legal_action_keys_before"],
                adapter.catalogue,
                action_order,
            ),
            "source_legal_action_count": len(first["legal_action_keys_before"]),
        }
        if rule not in rules:
            rules.append(rule)
    prior = source.get("structural_rank_query_prior")
    prior_payload = {
        "schema": "acfqp.generic_structural_rank_query_prior.v46",
        "source_episode_id": episode["episode_id"],
        "source_joint_successor_version_space_model_id": episode[
            "joint_successor_version_space_model_id"
        ],
        "state_width": len(state_order),
        "action_field_width": len(action_order),
        "source_rules": rules,
        "fallback_selected_action_rank_vector": rules[0][
            "selected_action_rank_vector"
        ],
        "source_query_order_only": True,
        "target_transition_outcomes_used": False,
        "ground_transition_authority_present": False,
        "safety_authority_present": False,
    }
    expected_prior = {
        **prior_payload,
        "structural_rank_query_prior_id": _generic_id(_V46_PRIOR_DOMAIN, prior_payload),
    }
    if prior != expected_prior:
        _fail("V75r5 structural-rank prior reconstruction changed")
    return source["source_id"], model_id


def _verify_episode(
    episode: Mapping[str, Any],
    adapter: Any,
    observed_rows: tuple[Any, ...],
    states: Mapping[tuple[int, ...], Any],
    expected_model_id: str | None,
    expected_priority_id: str | None,
) -> None:
    if type(episode) is not dict or episode.get("success") is not True:
        _fail("V75r5 target episode did not succeed")
    payload = {key: value for key, value in episode.items() if key != "episode_id"}
    if (
        _generic_id(_V44_EPISODE_DOMAIN, payload) != episode.get("episode_id")
        or episode.get("family") != adapter.family
        or episode.get("seed") != adapter.seed
        or episode.get("episode_index") != TARGET_EPISODE_INDEX
        or episode.get("joint_successor_version_space_model_id") != expected_model_id
        or episode.get("portable_query_priority_id") != expected_priority_id
    ):
        _fail("V75r5 target episode identity changed")
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
        _fail("V75r5 certificate ledger changed")
    by_key = {row.key: row for row in adapter.catalogue}
    local_rows = []
    transition_cache: dict[tuple[tuple[int, ...], int], tuple[tuple[int, ...], ...]] = {}
    for index, (failure, distinction) in enumerate(zip(failures, distinctions, strict=True)):
        if (
            failure.get("failure_index") != index
            or distinction.get("failure_index") != index
            or failure.get("ground_query_performed_before_failure") is not False
            or distinction.get("query_after_failed_certificate") is not True
            or distinction.get("ground_support_labels") != 1
            or failure.get("raw_state") != distinction.get("raw_state")
        ):
            _fail("V75r5 certificate-before-query ordering changed")
        raw = tuple(failure["raw_state"])
        state = states.get(raw)
        if state is None:
            _fail("V75r5 target ledger referenced unreachable state")
        legal = tuple(sorted(adapter.action_key(action) for action in adapter.actions(state)))
        if distinction.get("distinction_kind") == "QUERY_LOCAL_LEGAL_ACTION_SET":
            if distinction.get("legal_action_keys") != list(legal):
                _fail("V75r5 legality receipt changed")
            continue
        if distinction.get("distinction_kind") != "QUERY_LOCAL_EXACT_TRANSITION_SUPPORT":
            _fail("V75r5 distinction kind changed")
        key = failure.get("action_key")
        if type(key) is not int or key not in legal or key not in by_key:
            _fail("V75r5 transition query action changed")
        expected = []
        successors = []
        for offset, outcome in enumerate(adapter.kernel.step(state, adapter.action(key))):
            successor = outcome.next_state
            successor_raw = adapter.encode(successor)
            successors.append(successor_raw)
            legal_after = tuple(
                sorted(adapter.action_key(action) for action in adapter.actions(successor))
            )
            expected.append(
                {
                    "occurrence": 0,
                    "transition_index": len(observed_rows) + len(local_rows) + offset,
                    "pre_vector": list(raw),
                    "legal_action_keys_before": list(legal),
                    "selected_action": by_key[key].to_document(),
                    "post_vector": list(successor_raw),
                    "legal_action_keys_after": list(legal_after),
                    "terminal_acceptance_after": (
                        None if legal_after else adapter.success(successor)
                    ),
                    "outcome_tape_sha256": None,
                }
            )
        if distinction.get("raw_transition_rows") != expected:
            _fail("V75r5 exact transition support changed")
        local_rows.extend(expected)
        transition_cache[(raw, key)] = tuple(successors)
    if local_rows != raw_rows or len(transition_cache) != episode.get("queried_state_action_count"):
        _fail("V75r5 transition-cache accounting changed")
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
            if successors is not None and all(closes(value) for value in successors):
                visiting.remove(raw)
                memo[raw] = True
                return True
        visiting.remove(raw)
        memo[raw] = False
        return False

    if not closes(adapter.encode(adapter.initial())):
        _fail("V75r5 query-local overlay did not close a proof")
    state = adapter.initial()
    actions = episode.get("action_keys")
    tapes = episode.get("outcome_tape_sha256")
    if type(actions) is not list or type(tapes) is not list or len(actions) != len(tapes):
        _fail("V75r5 execution trace changed")
    for decision, (key, expected_tape) in enumerate(zip(actions, tapes, strict=True)):
        outcome, tape = adapter.select_outcome(state, key, TARGET_EPISODE_INDEX, decision)
        if tape != expected_tape:
            _fail("V75r5 outcome tape changed")
        state = outcome.next_state
    if adapter.active(state) or not adapter.success(state):
        _fail("V75r5 execution did not terminate in success")
    locks = {
        "target_outcomes_used_to_refit_source_artifacts": False,
        "same_exact_query_local_certificate_engine": True,
        "all_ground_queries_followed_failed_certificates": True,
        "query_local_exact_overlay_exclusively_used_for_safety": True,
        "reusable_artifacts_used_as_safety_authority": False,
        "portable_priority_used_only_for_query_ordering": True,
        "complete_world_model_synthesized": False,
    }
    if any(episode.get(key) != value for key, value in locks.items()):
        _fail("V75r5 target claim locks changed")


def verify_agreement_filtered_campaign_bytes_v75r5(raw: bytes) -> bytes:
    if type(raw) is not bytes:
        _fail("V75r5 input must be exact bytes")
    document = loads_canonical_json(raw)
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail("V75r5 campaign is not canonical")
    if (
        len(raw) != CAMPAIGN_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != CAMPAIGN_SHA256
        or document.get("campaign_id") != CAMPAIGN_ID
    ):
        _fail("V75r5 frozen campaign identity changed")
    _content(
        document,
        "campaign_id",
        domains.CONSTRUCTION_K7_AGREEMENT_FILTERED_CAMPAIGN_V75R5_DOMAIN,
        5,
    )
    if (
        document.get("preregistration_id") != PREREGISTRATION_ID
        or document.get("template_library_artifact_id") != TEMPLATE_LIBRARY_ARTIFACT_ID
    ):
        _fail("V75r5 predecessor identity changed")
    config = v73_pre.campaign_config_v73()
    config.update(
        source_seed_by_family=dict(SOURCE_SEEDS),
        fresh_target_seeds=dict(TARGET_SEEDS),
        target_episode_index=TARGET_EPISODE_INDEX,
    )
    factor_library = (
        v70_pre.previous.previous.previous.previous.previous.previous.previous.FACTOR_LIBRARY
    )
    sources = document.get("sources")
    targets = document.get("targets")
    if (
        type(sources) is not list
        or type(targets) is not list
        or len(sources) != 2
        or len(targets) != 4
    ):
        _fail("V75r5 source/target cardinality changed")
    source_by_family = {}
    for source in sources:
        family = source.get("family")
        seed = SOURCE_SEEDS.get(family)
        if seed != source.get("source_seed"):
            _fail("V75r5 source identity changed")
        adapter = base.predecessor.predecessor.prior_ground._adapter(  # noqa: SLF001
            family, seed, config
        )
        source_id, model_id = _verify_source(source, adapter)
        source_by_family[family] = (source_id, model_id)
    labels = {arm: 0 for arm in ARMS}
    filter_enabled = 0
    reduced = 0
    replayed = 0
    for target in targets:
        _content(
            target,
            "target_id",
            domains.CONSTRUCTION_K7_AGREEMENT_FILTERED_TARGET_V75R5_DOMAIN,
            5,
        )
        family = target.get("family")
        seed = target.get("target_seed")
        if seed not in TARGET_SEEDS.get(family, ()):
            _fail("V75r5 target identity changed")
        source_id, model_id = source_by_family[family]
        if target.get("source_id") != source_id or target.get("source_model_id") != model_id:
            _fail("V75r5 source-target join changed")
        adapter = base.predecessor.predecessor.prior_ground._adapter(  # noqa: SLF001
            family, seed, config
        )
        partial = base.acquire_matched_true_bit_models_v59(
            adapter, factor_library, config
        )["ANONYMOUS_FACTOR_PRIOR_ON"]
        if (
            target.get("target_common_partial_acquisition_id")
            != partial["document"]["acquisition_id"]
            or target.get("target_common_partial_ground_support_labels")
            != partial["document"]["ground_support_labels"]
        ):
            _fail("V75r5 target partial acquisition changed")
        translation = target.get("structural_rank_query_translation")
        translation_payload = {
            key: value for key, value in translation.items() if key != "translation_id"
        }
        if (
            _generic_id(_V46_TRANSLATION_DOMAIN, translation_payload)
            != translation.get("translation_id")
            or translation.get("target_transition_outcomes_used") is not False
            or translation.get("safety_authority_present") is not False
        ):
            _fail("V75r5 target translation changed")
        filter_row = target.get("abstract_agreement_filter")
        filter_payload = {
            key: value for key, value in filter_row.items() if key != "agreement_filter_id"
        }
        if (
            _generic_id(_V47_FILTER_DOMAIN, filter_payload)
            != filter_row.get("agreement_filter_id")
            or filter_row.get("target_transition_outcomes_used_for_filter") is not False
            or filter_row.get("safety_authority_present") is not False
            or filter_row.get("source_priority_enabled")
            is not (
                filter_row.get("abstract_model_initial_action_key") is not None
                and filter_row.get("abstract_model_initial_action_key")
                == filter_row.get("source_rank_selected_action_key")
            )
        ):
            _fail("V75r5 agreement-filter decision changed")
        filter_enabled += filter_row["source_priority_enabled"] is True
        expected_priorities = {
            UNFILTERED: filter_row["unfiltered_priority_id"],
            FILTERED: filter_row["filtered_priority_id"],
            MODEL_ONLY: filter_row["model_only_inert_priority_id"],
            STRICT: None,
        }
        states = _reachable_states(adapter)
        arms = target.get("target_arms")
        if type(arms) is not dict or set(arms) != set(ARMS):
            _fail("V75r5 target arm inventory changed")
        for arm in ARMS:
            _verify_episode(
                arms[arm],
                adapter,
                partial["rows"],
                states,
                None if arm == STRICT else model_id,
                expected_priorities[arm],
            )
            labels[arm] += arms[arm]["target_certificate_local_ground_support_labels"]
            replayed += 1
        if (
            arms[FILTERED]["action_keys"] != arms[MODEL_ONLY]["action_keys"]
            or arms[FILTERED]["target_certificate_local_ground_support_labels"]
            != arms[MODEL_ONLY]["target_certificate_local_ground_support_labels"]
        ):
            _fail("V75r5 filtered/model-only matched result changed")
        reduced += (
            arms[FILTERED]["target_certificate_local_ground_support_labels"]
            < arms[STRICT]["target_certificate_local_ground_support_labels"]
        )
        if (
            target.get("incompatible_schema_ood_control", {}).get("status")
            != "INCOMPATIBLE_SCHEMA_REJECTED_BEFORE_GROUND_QUERY"
        ):
            _fail("V75r5 OOD control changed")
    expected_labels = {
        UNFILTERED: 142,
        FILTERED: 138,
        MODEL_ONLY: 138,
        STRICT: 142,
    }
    if labels != expected_labels or filter_enabled != 0 or reduced != 1:
        _fail("V75r5 reconstructed sample ledger changed")
    sample = document.get("sample_tax_comparison")
    gate = document.get("registered_gate")
    if (
        sample.get("labels_by_arm") != labels
        or sample.get("filtered_minus_unfiltered_labels") != -4
        or sample.get("filtered_minus_model_only_labels") != 0
        or sample.get("filtered_minus_strict_labels") != -4
        or sample.get("operator_controls_priority_sample_tax") is not True
        or gate.get("passed") is not True
        or gate.get("certificate_discipline_clean") is not True
        or document.get("target_transition_outcomes_used_to_filter_priority") is not False
        or document.get("producer_free_verification_present") is not False
        or document.get("official_execution_allowed") is not False
        or document.get("official_scalar_cost") is not None
        or document.get("official_N_break_even") is not None
        or document.get("WORKLOAD_ECONOMICS_GATE") != "NOT_RUN"
        or document.get("COUNTER_COMPLETENESS_GATE") != "NOT_RUN"
    ):
        _fail("V75r5 campaign Gate or claim boundary changed")
    payload = {
        "schema": "acfqp.agreement_filtered_independent_verification.v75r5",
        "campaign_id": CAMPAIGN_ID,
        "preregistration_id": PREREGISTRATION_ID,
        "source_structural_rank_priors_reconstructed": len(sources),
        "target_partial_acquisitions_reconstructed": len(targets),
        "target_priority_translations_replayed": len(targets),
        "abstract_agreement_filter_receipts_replayed": len(targets),
        "target_certificate_episode_traces_replayed": replayed,
        "query_local_exact_overlay_proofs_replayed": replayed,
        "target_labels_by_arm": labels,
        "agreement_filter_enabled_target_count": filter_enabled,
        "filtered_reduced_target_occurrence_count": reduced,
        "operator_controls_priority_sample_tax_verified": True,
        "filtered_matches_model_only_verified": True,
        "cross_occurrence_model_reduction_verified": True,
        "v75r5_campaign_producer_imported_or_called": False,
        "v75r5_campaign_core_imported_or_called": False,
        "v44_episode_runner_called": False,
        "v46_priority_compiler_called": False,
        "v47_agreement_filter_called": False,
        "complete_world_model_synthesized": False,
        "arbitrary_domain_transfer_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        "status": "PRODUCER_FREE_V75R5_SAMPLE_TAX_CONTROL_EVIDENCE_VERIFIED",
    }
    result = {
        **payload,
        "verification_id": domains.extension_content_id_v75r5(
            domains.CONSTRUCTION_K7_AGREEMENT_FILTERED_VERIFICATION_V75R5_DOMAIN,
            payload,
        ),
    }
    encoded = canonical_json_bytes(result)
    if VERIFICATION_ID != "0" * 64 and (
        result["verification_id"] != VERIFICATION_ID
        or len(encoded) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(encoded).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("V75r5 frozen verification changed")
    return encoded


__all__ = (
    "CAMPAIGN_ID",
    "VERIFICATION_ID",
    "verify_agreement_filtered_campaign_bytes_v75r5",
)
