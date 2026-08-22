"""Producer for the preregistered V160 progressive raw-prefix classifier."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v160 as domains
from acfqp import construction_k7_progressive_raw_prefix_source_preregistration_v160 as source_pre
from acfqp.generic_modular_routing_adapter_v128 import (
    build_modular_routing_adapter_v128,
    modular_routing_config_v128,
)
from acfqp.generic_quaternary_relation_workflow_adapter_v153 import (
    FAMILY as POSITIVE_FAMILY,
    build_quaternary_relation_workflow_adapter_v153,
)
from acfqp.generic_relation_fanout_routing_adapter_v154 import (
    FAMILY as FALLBACK_FAMILY,
    build_relation_fanout_routing_adapter_v154,
    relation_fanout_routing_config_v154,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp.progressive_raw_prefix_query_classifier_core_v160 import (
    build_progressive_raw_prefix_trace_v160,
    evaluate_progressive_raw_prefix_expression_v160,
    synthesize_progressive_raw_prefix_classifier_v160,
)


V157_CAMPAIGN_ID = "51810176bf2ab9d4e51f11cf8a4f73b04bfb76bef116b8ebfce9d08f3fe1ed79"
V157_CAMPAIGN_BYTE_COUNT = 13_671_890
V157_CAMPAIGN_SHA256 = "8674649d85d991d8625d43104cd4a5e07fa75ccd4ffb88236e767cba11ea5284"
V157_VERIFICATION_ID = "61332d6b56b476d960915b182eff944c0a5e67a6dcf8b4782d798b0e46a6d59d"
V157_VERIFICATION_BYTE_COUNT = 17_545
V157_VERIFICATION_SHA256 = "fae743f81b19b45e85c5a96a1ffcf2bcbeee405e8a4651aa937169c635bcb9d4"
V159_CLASSIFIER_RECEIPT_ID = "464febb181620c04c171817ca1b934b3014e7fcc48cdc5a8162bfd5ba23e954a"
V159_CLASSIFIER_RECEIPT_BYTE_COUNT = 10_690
V159_CLASSIFIER_RECEIPT_SHA256 = "cff14491ae87b69ef853cbf55109be0b0122ead9b9045fe3c4407bc574794317"
CLASSIFIER_RECEIPT_ID = "0" * 64
EXPECTED_CANONICAL_BYTE_COUNT = 0
EXPECTED_CANONICAL_SHA256 = "0" * 64
ATTEMPT_TERMINAL_STATE = "UNEXECUTED"


class ConstructionK7ProgressiveRawPrefixClassifierReceiptV160Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7ProgressiveRawPrefixClassifierReceiptV160Error(message)


def _feature_trace(document):
    return tuple(
        tuple(tuple(row) for row in prefix["anonymous_raw_delta_feature_rows"])
        for prefix in document["prefixes"]
    )


def _source_config():
    config = relation_fanout_routing_config_v154()
    config["families"][POSITIVE_FAMILY] = {
        "stage_count": 5,
        "maximum_acquisition_labels": 1_536,
    }
    config["families"][FALLBACK_FAMILY]["maximum_acquisition_labels"] = 1_536
    return config


def _document(
    source_preregistration_raw,
    v157_campaign_raw,
    v157_verification_raw,
    v159_classifier_receipt_raw,
):
    source_registration = loads_canonical_json(source_preregistration_raw)
    campaign = loads_canonical_json(v157_campaign_raw)
    verification = loads_canonical_json(v157_verification_raw)
    v159_classifier = loads_canonical_json(v159_classifier_receipt_raw)
    if not (
        canonical_json_bytes(source_registration) == source_preregistration_raw
        and source_registration.get("source_preregistration_id")
        == source_pre.SOURCE_PREREGISTRATION_ID
        and len(source_preregistration_raw) == source_pre.EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(source_preregistration_raw).hexdigest()
        == source_pre.EXPECTED_CANONICAL_SHA256
        and canonical_json_bytes(campaign) == v157_campaign_raw
        and campaign.get("campaign_id") == V157_CAMPAIGN_ID
        and len(v157_campaign_raw) == V157_CAMPAIGN_BYTE_COUNT
        and hashlib.sha256(v157_campaign_raw).hexdigest() == V157_CAMPAIGN_SHA256
        and canonical_json_bytes(verification) == v157_verification_raw
        and verification.get("verification_id") == V157_VERIFICATION_ID
        and len(v157_verification_raw) == V157_VERIFICATION_BYTE_COUNT
        and hashlib.sha256(v157_verification_raw).hexdigest()
        == V157_VERIFICATION_SHA256
        and verification.get(
            "registered_plan_mode_corrected_margin_evidence_independently_verified"
        )
        is True
        and canonical_json_bytes(v159_classifier) == v159_classifier_receipt_raw
        and v159_classifier.get("classifier_receipt_id")
        == V159_CLASSIFIER_RECEIPT_ID
        and len(v159_classifier_receipt_raw) == V159_CLASSIFIER_RECEIPT_BYTE_COUNT
        and hashlib.sha256(v159_classifier_receipt_raw).hexdigest()
        == V159_CLASSIFIER_RECEIPT_SHA256
        and v159_classifier.get("fresh_v159_target_outcomes_accessed") is False
    ):
        _fail("V160 frozen source evidence changed")
    source_config = _source_config()
    builders = {
        POSITIVE_FAMILY: build_quaternary_relation_workflow_adapter_v153,
        FALLBACK_FAMILY: build_relation_fanout_routing_adapter_v154,
    }
    traces = []
    labelled = []
    for occurrence in campaign["target_occurrences"]:
        family = occurrence["target_family"]
        if family not in builders:
            _fail("V160 unexpected V157 source family")
        acquisition = occurrence["anonymous_relational_factor_prior_acquisition"]
        label = acquisition["guard_decision"] == "RELATION_COVERAGE"
        trace = build_progressive_raw_prefix_trace_v160(
            builders[family](occurrence["seed"], source_config)
        )
        trace["registered_query_policy_label"] = (
            "RELATION_COVERAGE" if label else "PATH_FIRST_SAFE_FALLBACK"
        )
        trace["label_evidence"] = "FROZEN_V157_QUERY_POLICY_OUTCOME"
        traces.append(trace)
        labelled.append((_feature_trace(trace), label))
    modular_config = modular_routing_config_v128()
    for observation in v159_classifier["source_modular_factorization_observations"]:
        if observation["positive_factorization_relation_present"] is not False:
            _fail("V160 modular source label changed")
        trace = build_progressive_raw_prefix_trace_v160(
            build_modular_routing_adapter_v128(observation["seed"], modular_config)
        )
        final_prefix = trace["prefixes"][-1]
        if not (
            final_prefix["raw_transition_rows"]
            == observation["raw_initial_transition_rows"]
            and final_prefix["raw_transition_sha256"]
            == observation["raw_initial_transition_sha256"]
        ):
            _fail("V160 modular raw-source reconstruction changed")
        trace["registered_query_policy_label"] = "PATH_FIRST_SAFE_FALLBACK"
        trace["label_evidence"] = "FROZEN_V159_RAW_FACTORIZATION_OUTCOME"
        traces.append(trace)
        labelled.append((_feature_trace(trace), False))
    expression, mdl, evaluated, separating = (
        synthesize_progressive_raw_prefix_classifier_v160(labelled)
    )
    horizon = expression["stable_prefix_observation_count"]
    if not all(
        all(
            (
                evaluate_progressive_raw_prefix_expression_v160(
                    expression,
                    feature_rows,
                    prefix_observation_count=prefix_index,
                )[0]
                == ("RELATION_COVERAGE" if label else "PATH_FIRST_SAFE_FALLBACK")
            )
            for prefix_index, feature_rows in enumerate(trace, start=1)
            if prefix_index >= horizon
        )
        for trace, label in labelled
    ):
        _fail("V160 selected expression is not source-stable")
    payload = {
        "schema": "acfqp.progressive_raw_prefix_classifier_receipt.v160",
        "source_preregistration_id": source_pre.SOURCE_PREREGISTRATION_ID,
        "source_v157_campaign_id": V157_CAMPAIGN_ID,
        "source_v157_verification_id": V157_VERIFICATION_ID,
        "source_v159_classifier_receipt_id": V159_CLASSIFIER_RECEIPT_ID,
        "source_labelled_raw_prefix_traces": traces,
        "finite_generic_relation_meta_grammar": source_registration[
            "finite_generic_relation_meta_grammar"
        ],
        "selected_expression": expression,
        "selected_expression_mdl_key": mdl,
        "candidate_expression_count_evaluated": evaluated,
        "separating_expression_count": separating,
        "derived_stable_prefix_observation_count": horizon,
        "no_named_initial_or_catalogue_support_primitive": True,
        "full_initial_action_frontier_required_for_decision": False,
        "exact_mdl_then_canonical_tie_break": True,
        "offline_source_observation_labels": sum(
            trace["offline_source_observation_labels"] for trace in traces
        ),
        "fresh_v160_target_labels": 0,
        "fresh_v160_target_outcomes_accessed": False,
        "classifier_derivation_compute_events": evaluated,
        "sample_labels_and_classifier_derivation_compute_separate": True,
        "query_policy_classifier_is_meta_prior_only": True,
        "query_policy_classifier_is_model_planning_or_certificate_authority": False,
        "complete_world_model_claimed": False,
        "arbitrary_unseen_domain_transfer_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    return {
        **payload,
        "classifier_receipt_id": domains.extension_content_id_v160(
            domains.CONSTRUCTION_K7_CLASSIFIER_RECEIPT_V160_DOMAIN, payload
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class ProgressiveRawPrefixClassifierReceiptV160:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    classifier_receipt_id: str

    def to_document(self):
        return loads_canonical_json(self.canonical_bytes)


_CACHE = None


def run_progressive_raw_prefix_classifier_receipt_v160(
    source_preregistration_raw: bytes,
    v157_campaign_raw: bytes,
    v157_verification_raw: bytes,
    v159_classifier_receipt_raw: bytes,
):
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if ATTEMPT_TERMINAL_STATE != "UNEXECUTED" or CLASSIFIER_RECEIPT_ID != "0" * 64:
        _fail("frozen V160 source attempt is terminal and will not be rerun")
    document = _document(
        source_preregistration_raw,
        v157_campaign_raw,
        v157_verification_raw,
        v159_classifier_receipt_raw,
    )
    raw = canonical_json_bytes(document)
    _CACHE = ProgressiveRawPrefixClassifierReceiptV160(
        _ISSUER, raw, document["classifier_receipt_id"]
    )
    return _CACHE


__all__ = (
    "ATTEMPT_TERMINAL_STATE",
    "CLASSIFIER_RECEIPT_ID",
    "run_progressive_raw_prefix_classifier_receipt_v160",
)
