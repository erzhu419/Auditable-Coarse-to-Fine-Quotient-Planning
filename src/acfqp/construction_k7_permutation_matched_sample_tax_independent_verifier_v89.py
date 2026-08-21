"""Producer-free verification of the frozen V89 matched sample-tax campaign."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v89 as domains
from acfqp.generic_coordinate_alignment_independent_replay_v61 import (
    rederive_coordinate_alignment_v61,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "00e954daeda5823e22a4c489dbf72a207570f36b8ad008488cd38d649d90aaed"
CAMPAIGN_BYTE_COUNT = 2_444_947
CAMPAIGN_SHA256 = "277a28d516d4c73c01f1e5d58441d7d74775a2fe3caac80e885d90dcf578f21d"
PREREGISTRATION_ID = "e463074f1155bc9510feda4c128c86f7652a8a8719e04ced80a94a2661d770b4"
V87_FAILED_CAMPAIGN_ID = "e5432505db2bf911324d3d719986493bfa81aa131439ee31367da9329cc2b0d8"
V87R1_CAMPAIGN_ID = "33e9d49933e8b2d94169911170732b178095ce55fe52258c6ccfb9d425990739"
V87R1_VERIFICATION_ID = "9a5fdb135fcebe2e4a31077e7a542d9af2338ecb1c2d76eda1e3f4f72eedd29d"
V88_CAMPAIGN_ID = "041f758ee32cb6fdef0b1218a23bdbfe47a115781ef1fc8f9c557a79a7b065b2"
V88_VERIFICATION_ID = "e176b3b775511c2c98e650e99fdb183555833ca5c4638bc7fc5d4b6f998be327"
PROJECTED_MODEL_ARTIFACT_ID = "c069fb2a39fee3b9dc7dc847fef15369cf8d65c5d6322bbaae1bbceb924a476e"
APPLICABILITY_MODEL_ARTIFACT_ID = "07ee765058797bc083db3180bb26952a79a224f8e8aef2f8f284237f87137f77"
SOURCE_MODEL_ID = "401693d9b6f3a50ec3581f0878181955cc804324cad003e23635b6af2e9bb1db"
APPLICABILITY_PROGRAM_ID = "956edacfc94e1312a3a6efa42e0fc2b91bf3266f61a06b3a3a5b8a1f03d38ef0"
TARGET_SEEDS = (929_101, 929_102, 929_103, 929_104, 929_105, 929_106)
VERIFICATION_ID = "6dd9d5c1dab579ef7e0192bc64d486b82468e56a28d1d7a92595505c77dc8f39"
EXPECTED_CANONICAL_BYTE_COUNT = 2_450
EXPECTED_CANONICAL_SHA256 = "c1aa93536aa715076ef90b536582ca5527e87a103c8899d8f89c95a2f3be8f99"

_ROOT = Path(__file__).resolve().parents[2]
_PROJECTED_PATH = _ROOT / "artifacts/world_model/v86_projected_disagreement_model.json"
_PROJECTED_BYTES = 136_251
_PROJECTED_SHA = "30c5b8775ae05039a971c20c52450efb29fcc8b57d81a38f70c9567fd9ef2bec"
_APPLICABILITY_PATH = _ROOT / "artifacts/world_model/v87_action_applicability_model.json"
_APPLICABILITY_BYTES = 2_978
_APPLICABILITY_SHA = "b564c19963692a593f38c8b64520643b71d28fb2c274d998fcd439553d1f7fd4"
_PERMUTATION_DOMAIN = b"acfqp:generic-action-key-permutation:v62\x00"
_V59_DOMAIN = b"acfqp:construction-k7-true-bit-symmetric-acquisition:v59\x00"
_OUTER_ABLATION_DOMAIN = b"acfqp:generic-coordinate-aligned-ablation:v60\x00"
_INNER_ABLATION_DOMAIN = b"acfqp:generic-applicability-ablation:v59\x00"
_EPISODE_DOMAIN = b"acfqp:generic-applicability-certificate-episode:v59\x00"


class ConstructionK7PermutationMatchedSampleTaxIndependentVerifierV89Error(
    ValueError
):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7PermutationMatchedSampleTaxIndependentVerifierV89Error(
        message
    )


def _content(value: Mapping[str, Any], key: str, domain: bytes, label: str) -> None:
    payload = {name: row for name, row in value.items() if name != key}
    if value.get(key) != hashlib.sha256(
        domain + canonical_json_bytes(payload)
    ).hexdigest():
        _fail(f"V89 {label} content identity changed")


def _load_models() -> tuple[dict[str, Any], dict[str, Any]]:
    projected_raw = _PROJECTED_PATH.read_bytes()
    applicability_raw = _APPLICABILITY_PATH.read_bytes()
    if (
        len(projected_raw) != _PROJECTED_BYTES
        or hashlib.sha256(projected_raw).hexdigest() != _PROJECTED_SHA
        or len(applicability_raw) != _APPLICABILITY_BYTES
        or hashlib.sha256(applicability_raw).hexdigest() != _APPLICABILITY_SHA
    ):
        _fail("V89 source model artifact bytes changed")
    projected = loads_canonical_json(projected_raw)
    applicability = loads_canonical_json(applicability_raw)
    if (
        type(projected) is not dict
        or type(applicability) is not dict
        or canonical_json_bytes(projected) != projected_raw
        or canonical_json_bytes(applicability) != applicability_raw
        or projected.get("model_artifact_id") != PROJECTED_MODEL_ARTIFACT_ID
        or applicability.get("model_artifact_id") != APPLICABILITY_MODEL_ARTIFACT_ID
    ):
        _fail("V89 source model artifact identity changed")
    model = projected.get("projected_disagreement_successor_model")
    program = applicability.get("action_applicability_program")
    if (
        type(model) is not dict
        or type(program) is not dict
        or model.get("projected_disagreement_successor_model_id") != SOURCE_MODEL_ID
        or program.get("action_applicability_program_id")
        != APPLICABILITY_PROGRAM_ID
    ):
        _fail("V89 embedded model/program changed")
    return model, program


def _verify_permutation(
    value: Any, seed: int, catalogue: Any
) -> tuple[int, str]:
    if type(value) is not dict or type(catalogue) is not list or len(catalogue) < 2:
        _fail("V89 action permutation inventory changed")
    width = len(catalogue)
    seed_bytes = seed.to_bytes(16, "big", signed=False)
    new_to_old = tuple(
        sorted(
            range(width),
            key=lambda old: hashlib.sha256(
                _PERMUTATION_DOMAIN
                + seed_bytes
                + old.to_bytes(8, "big", signed=False)
            ).digest(),
        )
    )
    old_to_new = [-1] * width
    for new, old in enumerate(new_to_old):
        old_to_new[old] = new
    if any(
        type(row) is not dict
        or set(row) != {"action_key", "anonymous_fields"}
        or row.get("action_key") != new
        or type(row.get("anonymous_fields")) is not list
        for new, row in enumerate(catalogue)
    ):
        _fail("V89 permuted action catalogue changed")
    source_catalogue = [None] * width
    for new, old in enumerate(new_to_old):
        source_catalogue[old] = {
            "action_key": old,
            "anonymous_fields": catalogue[new]["anonymous_fields"],
        }
    payload = {
        "schema": "acfqp.generic_action_key_permutation.v62",
        "family": "BALANCED_BATCH_REFINEMENT",
        "seed": seed,
        "algorithm": "SHA256_RANK_SEED_AND_OLD_KEY",
        "algorithm_domain_hex": _PERMUTATION_DOMAIN.hex(),
        "action_count": width,
        "old_to_new": old_to_new,
        "new_to_old": list(new_to_old),
        "source_catalogue_sha256": hashlib.sha256(
            canonical_json_bytes(source_catalogue)
        ).hexdigest(),
        "permuted_catalogue_sha256": hashlib.sha256(
            canonical_json_bytes(catalogue)
        ).hexdigest(),
        "anonymous_descriptor_fields_preserved_exactly": True,
        "ground_action_identity_preserved_through_inverse_map": True,
        "state_encoding_and_kernel_unchanged": True,
        "transition_outcomes_accessed_to_select_permutation": False,
        "semantic_action_names_accessed": False,
        "safety_authority_present": False,
    }
    expected = {
        **payload,
        "permutation_id": hashlib.sha256(
            _PERMUTATION_DOMAIN + canonical_json_bytes(payload)
        ).hexdigest(),
    }
    if value != expected:
        _fail("V89 outcome-blind permutation reconstruction diverged")
    return width, expected["permutation_id"]


def _verify_partial(
    acquisition: Any, seed: int, labels: int
) -> tuple[dict[str, Any], str, int]:
    if type(acquisition) is not dict or type(acquisition.get("candidate")) is not dict:
        _fail("V89 partial acquisition changed")
    for value, key in (
        (acquisition, "acquisition_id"),
        (acquisition["candidate"], "candidate_id"),
    ):
        payload = {name: row for name, row in value.items() if name != key}
        if value.get(key) != hashlib.sha256(
            _V59_DOMAIN + canonical_json_bytes(payload)
        ).hexdigest():
            _fail(f"V89 {key} changed")
    candidate = acquisition["candidate"]
    if (
        acquisition.get("schema") != "acfqp.true_bit_partial_acquisition.v59"
        or acquisition.get("arm") != "ANONYMOUS_FACTOR_PRIOR_ON"
        or acquisition.get("family") != "BALANCED_BATCH_REFINEMENT"
        or acquisition.get("seed") != seed
        or acquisition.get("ground_support_labels") != labels
        or acquisition.get("factor_prior_enabled") is not True
        or acquisition.get("complete_world_model_claimed") is not False
        or acquisition.get("symmetric_minimum_common_prefix_post_audit") is not True
        or candidate.get("schema") != "acfqp.generic_partial_factor_candidate.v15"
        or candidate.get("target_bindings_derived_from_raw_observations") is not True
        or candidate.get("semantic_names_used") is not False
        or candidate.get("planning_authority_present") is not False
        or candidate.get("complete_world_model_claimed") is not False
    ):
        _fail("V89 partial acquisition contract changed")
    return (
        candidate,
        acquisition["raw_transition_sha256"],
        acquisition["raw_transition_count"],
    )


def _verify_episode(
    episode: Any, arm: str, seed: int, projected_candidate_id: str
) -> None:
    if type(episode) is not dict:
        _fail("V89 episode changed")
    _content(episode, "episode_id", _EPISODE_DOMAIN, "episode")
    derived = arm == "APPLICABILITY_CONDITIONED_WORLD_MODEL"
    if (
        episode.get("schema")
        != "acfqp.generic_applicability_certificate_episode.v59"
        or episode.get("arm") != arm
        or episode.get("seed") != seed
        or episode.get("episode_index") != 12
        or episode.get("partial_candidate_id") != projected_candidate_id
        or episode.get("projected_disagreement_successor_model_id")
        != (SOURCE_MODEL_ID if derived else None)
        or episode.get("action_applicability_program_id")
        != (APPLICABILITY_PROGRAM_ID if derived else None)
        or episode.get("success") is not True
        or episode.get("all_ground_queries_followed_failed_certificates") is not True
        or episode.get("query_local_exact_overlay_exclusively_used_for_safety")
        is not True
        or episode.get(
            "reusable_abstract_model_or_applicability_used_as_safety_authority"
        )
        is not False
    ):
        _fail("V89 episode contract changed")
    if (
        type(episode.get("action_keys")) is not list
        or episode["execution_steps"] != len(episode["action_keys"])
        or episode["execution_steps"] <= 1
        or len(episode["outcome_tape_sha256"]) != episode["execution_steps"]
    ):
        _fail("V89 execution trace changed")
    failures = episode.get("failed_certificates")
    distinctions = episode.get("local_distinctions")
    if (
        type(failures) is not list
        or type(distinctions) is not list
        or len(failures) != len(distinctions)
    ):
        _fail("V89 certificate trace changed")
    labels = 0
    transitions = []
    transition_queries = 0
    for index, (failure, distinction) in enumerate(
        zip(failures, distinctions, strict=True)
    ):
        if (
            failure.get("failure_index") != index
            or failure.get("ground_query_performed_before_failure") is not False
            or distinction.get("failure_index") != index
            or distinction.get("query_after_failed_certificate") is not True
            or distinction.get("raw_state") != failure.get("raw_state")
            or distinction.get("ground_support_labels") != 1
        ):
            _fail("V89 certificate-before-query order changed")
        labels += 1
        if distinction.get("distinction_kind") == "QUERY_LOCAL_EXACT_TRANSITION_SUPPORT":
            rows = distinction.get("raw_transition_rows")
            if type(rows) is not list or not rows:
                _fail("V89 local transition support changed")
            transitions.extend(rows)
            transition_queries += 1
        elif distinction.get("distinction_kind") != "QUERY_LOCAL_LEGAL_ACTION_SET":
            _fail("V89 local distinction kind changed")
    if (
        labels != episode["target_certificate_local_ground_support_labels"]
        or transitions != episode["raw_local_transition_rows"]
        or transition_queries != episode["queried_state_action_count"]
    ):
        _fail("V89 certificate accounting changed")
    if derived:
        if (
            episode["abstract_plan_attempt_count"] <= 0
            or episode["abstract_plan_success_count"]
            != episode["abstract_plan_attempt_count"]
            or episode["abstract_plan_abstention_count"] != 0
            or episode["abstract_model_ordering_accepted_count"]
            != episode["abstract_plan_success_count"]
            or episode["applicability_relation_evaluations"] <= 0
            or episode["inapplicable_action_branch_evaluations_avoided"] <= 0
        ):
            _fail("V89 abstract planning counters changed")
    elif any(
        episode[key] != 0
        for key in (
            "abstract_plan_attempt_count",
            "abstract_plan_success_count",
            "abstract_plan_abstention_count",
            "abstract_model_ordering_accepted_count",
            "abstract_planning_compute_events",
            "applicability_relation_evaluations",
            "inapplicable_action_branch_evaluations_avoided",
        )
    ):
        _fail("V89 strict arm consumed abstract planning")


def _verify_ablation(
    ablation: Any,
    seed: int,
    candidate_id: str,
    alignment: Mapping[str, Any],
) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
    if type(ablation) is not dict:
        _fail("V89 ablation changed")
    _content(ablation, "ablation_id", _OUTER_ABLATION_DOMAIN, "outer ablation")
    inner = ablation.get("underlying_matched_ablation")
    if type(inner) is not dict:
        _fail("V89 inner ablation changed")
    _content(inner, "ablation_id", _INNER_ABLATION_DOMAIN, "inner ablation")
    if (
        ablation.get("schema")
        != "acfqp.generic_coordinate_aligned_applicability_ablation.v60"
        or ablation.get("seed") != seed
        or ablation.get("target_partial_candidate_id") != candidate_id
        or ablation.get("coordinate_alignment") != alignment
        or ablation.get("coordinate_alignment_id")
        != alignment["coordinate_alignment_id"]
        or ablation.get("arms") != inner.get("arms")
        or ablation.get("alignment_frozen_before_target_episode") is not True
        or ablation.get("target_episode_outcomes_used_to_select_alignment") is not False
        or ablation.get("coordinate_alignment_or_model_used_as_safety_authority")
        is not False
    ):
        _fail("V89 ablation contract changed")
    arms = ablation["arms"]
    derived = arms["APPLICABILITY_CONDITIONED_WORLD_MODEL"]
    strict = arms["STRICT_NO_REUSABLE_MODEL"]
    projected = ablation["projected_partial_candidate_id"]
    _verify_episode(derived, "APPLICABILITY_CONDITIONED_WORLD_MODEL", seed, projected)
    _verify_episode(strict, "STRICT_NO_REUSABLE_MODEL", seed, projected)
    for key in (
        "family",
        "seed",
        "episode_index",
        "partial_candidate_id",
        "action_keys",
        "outcome_tape_sha256",
        "execution_steps",
    ):
        if derived[key] != strict[key]:
            _fail("V89 matched ground execution diverged")
    derived_labels = derived["target_certificate_local_ground_support_labels"]
    strict_labels = strict["target_certificate_local_ground_support_labels"]
    if (
        derived_labels > strict_labels
        or inner.get("derived_target_certificate_local_ground_support_labels")
        != derived_labels
        or inner.get("strict_target_certificate_local_ground_support_labels")
        != strict_labels
        or inner.get("derived_minus_strict_target_labels")
        != derived_labels - strict_labels
        or inner.get("actual_target_sample_reduction_observed")
        != (derived_labels < strict_labels)
        or ablation.get("derived_target_certificate_local_ground_support_labels")
        != derived_labels
        or ablation.get("strict_target_certificate_local_ground_support_labels")
        != strict_labels
    ):
        _fail("V89 matched label measurement changed")
    return derived, strict


def verify_permutation_matched_sample_tax_campaign_bytes_v89(raw: bytes) -> bytes:
    if (
        type(raw) is not bytes
        or len(raw) != CAMPAIGN_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != CAMPAIGN_SHA256
    ):
        _fail("V89 campaign bytes changed")
    document = loads_canonical_json(raw)
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail("V89 campaign canonical form changed")
    payload = {key: value for key, value in document.items() if key != "campaign_id"}
    if (
        document.get("campaign_id") != CAMPAIGN_ID
        or domains.extension_content_id_v89(
            domains.CONSTRUCTION_K7_PERMUTATION_MATCHED_CAMPAIGN_V89_DOMAIN,
            payload,
        )
        != CAMPAIGN_ID
    ):
        _fail("V89 campaign content identity changed")
    fixed = {
        "schema": "acfqp.permutation_matched_sample_tax_campaign.v89",
        "preregistration_id": PREREGISTRATION_ID,
        "v87_failed_campaign_id": V87_FAILED_CAMPAIGN_ID,
        "v87r1_campaign_id": V87R1_CAMPAIGN_ID,
        "v87r1_verification_id": V87R1_VERIFICATION_ID,
        "v88_campaign_id": V88_CAMPAIGN_ID,
        "v88_verification_id": V88_VERIFICATION_ID,
        "projected_model_artifact_id": PROJECTED_MODEL_ARTIFACT_ID,
        "applicability_model_artifact_id": APPLICABILITY_MODEL_ARTIFACT_ID,
        "source_model_id": SOURCE_MODEL_ID,
        "action_applicability_program_id": APPLICABILITY_PROGRAM_ID,
        "predecessor_identities_preserved": True,
        "target_episode_outcomes_used_to_select_permutation_alignment_or_refit_models": False,
        "multi_step_abstract_ordering_primary_observed": True,
        "certificate_failure_only_local_ground_recovery_observed": True,
        "query_local_exact_overlay_only_safety_authority": True,
        "sample_tax_reduction_verified": True,
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
    if any(document.get(key) != value for key, value in fixed.items()):
        _fail("V89 campaign claim boundary changed")
    model, program = _load_models()
    occurrences = document.get("target_occurrences")
    if (
        type(occurrences) is not list
        or [row.get("target_seed") for row in occurrences] != list(TARGET_SEEDS)
    ):
        _fail("V89 target identity schedule changed")
    derived_rows = []
    strict_rows = []
    alignments = []
    occurrence_ids = []
    permutation_ids = []
    common_labels = 0
    raw_transition_count = 0
    for row in occurrences:
        occurrence_payload = {
            key: value for key, value in row.items() if key != "occurrence_id"
        }
        if row.get("occurrence_id") != domains.extension_content_id_v89(
            domains.CONSTRUCTION_K7_PERMUTATION_MATCHED_OCCURRENCE_V89_DOMAIN,
            occurrence_payload,
        ):
            _fail("V89 occurrence identity changed")
        if (
            row.get("schema")
            != "acfqp.permutation_matched_sample_tax_occurrence.v89"
            or row.get("target_episode_index") != 12
            or row.get("status")
            != "TARGET_PERMUTATION_MATCHED_EPISODES_COMPLETED"
            or row.get("failure_reason") is not None
            or row.get(
                "raw_alignment_inputs_and_permutation_frozen_before_target_episode"
            )
            is not True
            or row.get(
                "target_episode_outcomes_used_to_select_permutation_alignment_or_refit_models"
            )
            is not False
            or row.get("query_local_exact_overlay_only_safety_authority") is not True
        ):
            _fail("V89 occurrence contract changed")
        candidate, raw_sha, raw_count = _verify_partial(
            row["target_common_partial_acquisition"],
            row["target_seed"],
            row["target_common_partial_ground_support_labels"],
        )
        raw_rows = row.get("target_common_partial_raw_transition_rows")
        catalogue = row.get("target_common_partial_action_catalogue")
        if (
            type(raw_rows) is not list
            or type(catalogue) is not list
            or len(raw_rows) != raw_count
            or hashlib.sha256(canonical_json_bytes(raw_rows)).hexdigest() != raw_sha
        ):
            _fail("V89 embedded raw alignment inputs changed")
        _, permutation_id = _verify_permutation(
            row.get("outcome_blind_action_key_permutation"),
            row["target_seed"],
            catalogue,
        )
        replayed = rederive_coordinate_alignment_v61(
            model, program, candidate, raw_rows, catalogue
        )
        if (
            replayed != row.get("coordinate_alignment")
            or row.get("coordinate_alignment_id")
            != replayed["coordinate_alignment_id"]
        ):
            _fail("V89 independent alignment reconstruction diverged")
        derived, strict = _verify_ablation(
            row["matched_ablation"],
            row["target_seed"],
            candidate["candidate_id"],
            replayed,
        )
        ood = row.get("incompatible_schema_ood_control")
        if ood != {
            "status": "INCOMPATIBLE_SCHEMA_REJECTED_BEFORE_ALIGNMENT_OR_SEARCH",
            "reason": "V60 target is not in the registered structural schema family",
            "ground_transition_accessed_beyond_registered_partial_prefix": False,
        }:
            _fail("V89 strict OOD control changed")
        derived_rows.append(derived)
        strict_rows.append(strict)
        alignments.append(replayed)
        occurrence_ids.append(row["occurrence_id"])
        permutation_ids.append(permutation_id)
        common_labels += row["target_common_partial_ground_support_labels"]
        raw_transition_count += raw_count
    derived_labels = sum(
        row["target_certificate_local_ground_support_labels"] for row in derived_rows
    )
    strict_labels = sum(
        row["target_certificate_local_ground_support_labels"] for row in strict_rows
    )
    reduced_count = sum(
        left["target_certificate_local_ground_support_labels"]
        < right["target_certificate_local_ground_support_labels"]
        for left, right in zip(derived_rows, strict_rows, strict=True)
    )
    gate = {
        "required_target_occurrence_count": 6,
        "actual_target_occurrence_count": 6,
        "minimum_completed_target_count": 6,
        "actual_completed_target_count": 6,
        "every_eligible_target_completed": True,
        "raw_alignment_inputs_embedded": True,
        "outcome_blind_action_key_permutations_clean": True,
        "unique_alignment_on_every_completed_target": True,
        "certificate_failure_only_ground_discipline_clean": True,
        "abstract_model_ordering_clean": True,
        "matched_ground_execution_identical": True,
        "strict_incompatible_schema_no_transfer_verified": True,
        "minimum_reduced_target_occurrence_count": 4,
        "actual_reduced_target_occurrence_count": reduced_count,
        "no_target_label_regressions": True,
        "aggregate_target_sample_reduction_observed": derived_labels < strict_labels,
        "passed": True,
    }
    if document.get("registered_gate") != gate:
        _fail("V89 Gate changed")
    sample = {
        "derived_target_certificate_local_labels": derived_labels,
        "strict_target_certificate_local_labels": strict_labels,
        "derived_minus_strict_target_labels": derived_labels - strict_labels,
        "target_labels_avoided": strict_labels - derived_labels,
        "reduced_target_occurrence_count": reduced_count,
        "actual_target_sample_reduction_observed": derived_labels < strict_labels,
        "reduction_required_for_this_gate": True,
        "same_synthesizer_stopping_rule_and_exact_certificate_engine": True,
        "only_reusable_model_availability_differs_between_episode_arms": True,
    }
    if document.get("sample_tax_measurement") != sample:
        _fail("V89 sample measurement changed")
    accounting = document.get("accounting")
    recomputed = {
        "target_common_partial_labels": common_labels,
        "derived_target_certificate_local_labels": derived_labels,
        "strict_target_certificate_local_labels": strict_labels,
        "derived_target_execution_steps": sum(
            row["execution_steps"] for row in derived_rows
        ),
        "strict_target_execution_steps": sum(
            row["execution_steps"] for row in strict_rows
        ),
        "derived_abstract_planning_compute_events": sum(
            row["abstract_planning_compute_events"] for row in derived_rows
        ),
        "strict_abstract_planning_compute_events": sum(
            row["abstract_planning_compute_events"] for row in strict_rows
        ),
        "derived_queried_state_action_count": sum(
            row["queried_state_action_count"] for row in derived_rows
        ),
        "strict_queried_state_action_count": sum(
            row["queried_state_action_count"] for row in strict_rows
        ),
    }
    if (
        type(accounting) is not dict
        or any(accounting.get(key) != value for key, value in recomputed.items())
        or accounting.get("all_axes_separate") is not True
    ):
        _fail("V89 accounting axes changed")
    verification_payload = {
        "schema": "acfqp.permutation_matched_sample_tax_independent_verification.v89",
        "campaign_id": CAMPAIGN_ID,
        "campaign_byte_count": CAMPAIGN_BYTE_COUNT,
        "campaign_sha256": CAMPAIGN_SHA256,
        "preregistration_id": PREREGISTRATION_ID,
        "target_occurrence_ids": occurrence_ids,
        "action_key_permutation_ids": permutation_ids,
        "coordinate_alignment_ids": [
            row["coordinate_alignment_id"] for row in alignments
        ],
        "target_occurrence_count": 6,
        "embedded_raw_transition_count": raw_transition_count,
        "independently_rederived_permutation_count": 6,
        "independently_rederived_alignment_count": 6,
        "matched_certificate_trace_count": 12,
        "matched_ground_execution_verified": True,
        "certificate_failure_before_every_ground_query_verified": True,
        "actual_target_sample_reduction_observed": derived_labels < strict_labels,
        "derived_target_certificate_local_labels": derived_labels,
        "strict_target_certificate_local_labels": strict_labels,
        "target_labels_avoided": strict_labels - derived_labels,
        "reduced_target_occurrence_count": reduced_count,
        "sample_tax_reduction_verified": True,
        "complete_world_model_synthesized": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    verification = {
        **verification_payload,
        "verification_id": domains.extension_content_id_v89(
            domains.CONSTRUCTION_K7_PERMUTATION_MATCHED_VERIFICATION_V89_DOMAIN,
            verification_payload,
        ),
    }
    result = canonical_json_bytes(verification)
    if VERIFICATION_ID != "0" * 64 and (
        verification["verification_id"] != VERIFICATION_ID
        or len(result) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(result).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V89 verification changed")
    return result


__all__ = ("verify_permutation_matched_sample_tax_campaign_bytes_v89",)
