"""Outcome-free preregistration for V158 novel-signature transfer."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v158 as domains
from acfqp.anonymous_query_classifier_receipt_v158 import CLASSIFIER_RECEIPT_ID, EXPECTED_CANONICAL_BYTE_COUNT as CLASSIFIER_RECEIPT_BYTE_COUNT, EXPECTED_CANONICAL_SHA256 as CLASSIFIER_RECEIPT_SHA256
from acfqp.novel_signature_campaign_core_v158 import FALLBACK_FAMILY, POSITIVE_FAMILY, novel_signature_campaign_config_v158
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


IMPLEMENTATION_COMMITS = (
    "39db45b751a99a2cedd97a34a8ff114a4b9322d8",
    "cb8a9b6706eacf8ef070dbc04b1bd37068c518bc",
    "ca5b4d27969bd0ca84beeb4035629ed52581f738",
)
PREREGISTRATION_ID = "52fb493325ad0abfc00f4d5a1a186dbc982d837224915320193b250bc75f6800"
EXPECTED_CANONICAL_BYTE_COUNT = 5_345
EXPECTED_CANONICAL_SHA256 = "a65518df8a7ed50c4fc369744495c3bdf9eb5c83f754fd4bb3ed4ce821e77045"
TARGET_OCCURRENCES = tuple(
    [(POSITIVE_FAMILY, seed) for seed in range(1_047_921, 1_047_925)]
    + [(FALLBACK_FAMILY, seed) for seed in range(1_047_931, 1_047_935)]
)
TARGET_EPISODE_INDICES = (761, 762, 763, 764)
TARGET_WORKER_COUNT = 2
REQUIRED_TARGET_OCCURRENCE_COUNT = 8
MAXIMUM_ACQUISITION_LABELS = 1_536
SOURCE_ROOT = Path(__file__).resolve().parents[2]
FROZEN_SOURCE_FACTS = (
    ("src/acfqp/construction_k7_domain_registry_extension_v158.py", 1_562, "010926ddfb6486d17ee199728e036f41bf1db668c95f50251291ca19934d8eb9"),
    ("src/acfqp/anonymous_query_classifier_receipt_v158.py", 7_414, "fd963baf6bb0f03c08dbe82556a2c2a8995128d191636ed2a7a5982291e5009a"),
    ("src/acfqp/generic_novel_signature_adapters_v158.py", 2_685, "9f65998bf7d658a090b55839d5da8395c70fbf56b65bcbdb57a6c6575644a677"),
    ("src/acfqp/classifier_guarded_acquisition_operator_v158.py", 4_006, "0fa57d4be526b2bc097201c217639ddc60bd512696f716c4e4d0e2a00aefcbc6"),
    ("src/acfqp/novel_signature_campaign_core_v158.py", 14_193, "e849019b1ab0bda78745046cc377d1c9f2583eac449f773c10e4ae065d506c64"),
    ("src/acfqp/applicable_plan_mode_sequence_v157.py", 2_671, "7040847c5dc63741ee6eb0c17facdb0473c12423c0a1bbb2193149ae1a3ce40b"),
    ("src/acfqp/certified_memoized_planner_sequence_v154.py", 6_600, "60c6b6409bf604385c6fc3f90182841485bd1561b4e06766fda2858154db5cfb"),
    ("src/acfqp/anonymous_relational_factor_bank_acquisition_v148.py", 26_160, "3094d26ef86aa2fde1c4932cb8872a666e4cbdeec0c8c24a23a973a6e1b12a84"),
)


class ConstructionK7NovelSignaturePreregistrationV158Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7NovelSignaturePreregistrationV158Error(message)


def campaign_config_v158():
    config = novel_signature_campaign_config_v158()
    for family, _seed in TARGET_OCCURRENCES:
        config["families"][family]["maximum_acquisition_labels"] = MAXIMUM_ACQUISITION_LABELS
    config.update(target_occurrences=[{"family": family, "seed": seed} for family, seed in TARGET_OCCURRENCES], target_episode_indices=TARGET_EPISODE_INDICES, target_worker_count=TARGET_WORKER_COUNT, required_target_occurrence_count=REQUIRED_TARGET_OCCURRENCE_COUNT)
    return config


def _document(classifier_receipt_raw: bytes):
    classifier = loads_canonical_json(classifier_receipt_raw)
    if canonical_json_bytes(classifier) != classifier_receipt_raw or len(classifier_receipt_raw) != CLASSIFIER_RECEIPT_BYTE_COUNT or hashlib.sha256(classifier_receipt_raw).hexdigest() != CLASSIFIER_RECEIPT_SHA256 or classifier.get("classifier_receipt_id") != CLASSIFIER_RECEIPT_ID or classifier.get("fresh_v158_target_outcomes_accessed") is not False:
        _fail("V158 frozen classifier receipt changed")
    source_facts = [{"relative_path": path, "byte_count": len(raw := (SOURCE_ROOT / path).read_bytes()), "sha256": hashlib.sha256(raw).hexdigest()} for path, _count, _digest in FROZEN_SOURCE_FACTS]
    if source_facts != [{"relative_path": path, "byte_count": count, "sha256": digest} for path, count, digest in FROZEN_SOURCE_FACTS]:
        _fail("V158 frozen implementation source changed")
    config = campaign_config_v158()
    payload = {
        "schema": "acfqp.novel_signature_preregistration.v158",
        "implementation_commits": list(IMPLEMENTATION_COMMITS),
        "frozen_implementation_source_facts": source_facts,
        "frozen_classifier_receipt": classifier,
        "target_occurrences": config["target_occurrences"], "target_episode_indices": list(TARGET_EPISODE_INDICES), "target_worker_count": TARGET_WORKER_COUNT,
        "required_target_occurrence_count": REQUIRED_TARGET_OCCURRENCE_COUNT, "maximum_acquisition_labels": MAXIMUM_ACQUISITION_LABELS,
        "registered_gate": {
            "fresh_target_identities_with_unseen_exact_signatures": True,
            "classifier_receipt_frozen_before_target_outcomes": True,
            "classifier_expression_must_be_rederived_from_finite_grammar": True,
            "exact_source_signature_registry_must_not_be_consulted": True,
            "positive_classifier_gain_and_fallback_zero_regression_required": True,
            "factor_prior_noninferior_everywhere_and_positive_in_aggregate": True,
            "both_applicable_plan_modes_and_v109_receipts_required": True,
            "both_arms_receding_planning_and_certificate_recovery_required": True,
            "nonrelational_ood_rejection_before_bank_access_required": True,
            "producer_free_verification_required": True,
            "frozen_two_worker_resource_schedule": True,
        },
        "claim_boundary": {
            "target_outcomes_accessed": False, "grammar_synthesized_classifier_novel_signature_transfer_observed": False,
            "classifier_is_model_planning_or_certificate_authority": False, "complete_world_model_claimed": False, "arbitrary_unseen_domain_transfer_claimed": False,
            "official_execution_allowed": False, "official_scalar_cost": None, "official_N_break_even": None, "WORKLOAD_ECONOMICS_GATE": "NOT_RUN", "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        },
    }
    return {**payload, "preregistration_id": domains.extension_content_id_v158(domains.CONSTRUCTION_K7_PREREGISTRATION_V158_DOMAIN, payload)}


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class NovelSignaturePreregistrationV158:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


def freeze_novel_signature_preregistration_v158(classifier_receipt_raw: bytes):
    document = _document(classifier_receipt_raw); raw = canonical_json_bytes(document)
    if PREREGISTRATION_ID != "0" * 64 and (document["preregistration_id"] != PREREGISTRATION_ID or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256):
        _fail("V158 frozen preregistration changed")
    return NovelSignaturePreregistrationV158(_ISSUER, raw, document["preregistration_id"])


__all__ = ("PREREGISTRATION_ID", "campaign_config_v158", "freeze_novel_signature_preregistration_v158")
