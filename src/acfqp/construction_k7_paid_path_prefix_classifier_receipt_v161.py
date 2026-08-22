"""Producer for the preregistered V161 paid path-prefix classifier."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v161 as domains
from acfqp import construction_k7_paid_path_prefix_source_preregistration_v161 as source_pre
from acfqp.generic_modular_routing_adapter_v128 import (
    FAMILY as MODULAR_FAMILY,
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
from acfqp.paid_path_prefix_query_classifier_core_v161 import (
    build_paid_path_prefix_trace_v161,
    evaluate_progressive_raw_prefix_expression_v160,
    feature_trace_v161,
    synthesize_progressive_raw_prefix_classifier_v160,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


V160_CLASSIFIER_RECEIPT_ID = "27b256a9a26ae86e49214932b77b2e507f34ff87bc3470ba42275330e48a9a12"
V160_CLASSIFIER_BYTE_COUNT = 100_085
V160_CLASSIFIER_SHA256 = "e4335b07345c44cbc07d51ebce33a41c9d23fe7e0b27495350ea8a19403b749d"
V160_FAILED_CAMPAIGN_ID = "38cbf013db9ceb15605807f5aa83564f7b89fc559d793dcfd7a049d7095771c6"
V160_FAILED_CAMPAIGN_BYTE_COUNT = 16_288_802
V160_FAILED_CAMPAIGN_SHA256 = "2e8f573ddedef1963e5c7d5ad3d3545e5900fa509d78f5ebc15e928d7dab282a"
V160_FAILURE_BYTE_COUNT = 1_953
V160_FAILURE_SHA256 = "1d554b56462031920d3573ed1969997eedd8955426bfd024f8355bfab362d3ab"
CLASSIFIER_RECEIPT_ID = "0" * 64
EXPECTED_CANONICAL_BYTE_COUNT = 0
EXPECTED_CANONICAL_SHA256 = "0" * 64
ATTEMPT_TERMINAL_STATE = "UNEXECUTED"


class ConstructionK7PaidPathPrefixClassifierReceiptV161Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7PaidPathPrefixClassifierReceiptV161Error(message)


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
    v160_classifier_raw,
    v160_failed_campaign_raw,
    v160_failure_raw,
):
    source_registration = loads_canonical_json(source_preregistration_raw)
    v160_classifier = loads_canonical_json(v160_classifier_raw)
    failed_campaign = loads_canonical_json(v160_failed_campaign_raw)
    failure = loads_canonical_json(v160_failure_raw)
    if not (
        canonical_json_bytes(source_registration) == source_preregistration_raw
        and source_registration.get("source_preregistration_id")
        == source_pre.SOURCE_PREREGISTRATION_ID
        and len(source_preregistration_raw) == source_pre.EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(source_preregistration_raw).hexdigest()
        == source_pre.EXPECTED_CANONICAL_SHA256
        and canonical_json_bytes(v160_classifier) == v160_classifier_raw
        and v160_classifier.get("classifier_receipt_id")
        == V160_CLASSIFIER_RECEIPT_ID
        and len(v160_classifier_raw) == V160_CLASSIFIER_BYTE_COUNT
        and hashlib.sha256(v160_classifier_raw).hexdigest()
        == V160_CLASSIFIER_SHA256
        and canonical_json_bytes(failed_campaign) == v160_failed_campaign_raw
        and failed_campaign.get("campaign_id") == V160_FAILED_CAMPAIGN_ID
        and len(v160_failed_campaign_raw) == V160_FAILED_CAMPAIGN_BYTE_COUNT
        and hashlib.sha256(v160_failed_campaign_raw).hexdigest()
        == V160_FAILED_CAMPAIGN_SHA256
        and failed_campaign.get("registered_gate", {}).get("passed") is False
        and canonical_json_bytes(failure) == v160_failure_raw
        and len(v160_failure_raw) == V160_FAILURE_BYTE_COUNT
        and hashlib.sha256(v160_failure_raw).hexdigest() == V160_FAILURE_SHA256
        and failure.get("failed_campaign_id") == V160_FAILED_CAMPAIGN_ID
        and failure.get("same_identity_rerun_forbidden") is True
    ):
        _fail("V161 frozen source or V160 failure evidence changed")
    source_config = _source_config()
    modular_config = modular_routing_config_v128()
    builders = {
        POSITIVE_FAMILY: (build_quaternary_relation_workflow_adapter_v153, source_config),
        FALLBACK_FAMILY: (build_relation_fanout_routing_adapter_v154, source_config),
        MODULAR_FAMILY: (build_modular_routing_adapter_v128, modular_config),
    }
    traces = []
    labelled = []
    for source in v160_classifier["source_labelled_raw_prefix_traces"]:
        family = source["family"]
        if family not in builders:
            _fail("V161 unexpected source family")
        builder, config = builders[family]
        label = source["registered_query_policy_label"] == "RELATION_COVERAGE"
        trace = build_paid_path_prefix_trace_v161(builder(source["seed"], config))
        trace["registered_query_policy_label"] = source[
            "registered_query_policy_label"
        ]
        trace["label_evidence"] = source["label_evidence"]
        traces.append(trace)
        labelled.append((feature_trace_v161(trace), label))
    expression, mdl, evaluated, separating = (
        synthesize_progressive_raw_prefix_classifier_v160(labelled)
    )
    horizon = expression["stable_prefix_observation_count"]
    if not all(
        all(
            evaluate_progressive_raw_prefix_expression_v160(
                expression,
                feature_rows,
                prefix_observation_count=prefix_index,
            )[0]
            == ("RELATION_COVERAGE" if label else "PATH_FIRST_SAFE_FALLBACK")
            for prefix_index, feature_rows in enumerate(trace, start=1)
            if prefix_index >= horizon
        )
        for trace, label in labelled
    ):
        _fail("V161 selected expression is not source-stable")
    payload = {
        "schema": "acfqp.paid_path_prefix_classifier_receipt.v161",
        "source_preregistration_id": source_pre.SOURCE_PREREGISTRATION_ID,
        "source_v160_classifier_receipt_id": V160_CLASSIFIER_RECEIPT_ID,
        "failed_v160_campaign_id": V160_FAILED_CAMPAIGN_ID,
        "failed_v160_record_sha256": V160_FAILURE_SHA256,
        "source_labelled_paid_path_prefix_traces": traces,
        "finite_generic_relation_meta_grammar": source_registration[
            "finite_generic_relation_meta_grammar"
        ],
        "selected_expression": expression,
        "selected_expression_mdl_key": mdl,
        "candidate_expression_count_evaluated": evaluated,
        "separating_expression_count": separating,
        "derived_stable_prefix_observation_count": horizon,
        "safe_fallback_resumes_same_path_first_generator": True,
        "classifier_inserts_no_sibling_probe_before_fallback": True,
        "offline_source_observation_labels": sum(
            trace["offline_source_observation_labels"] for trace in traces
        ),
        "fresh_v161_target_labels": 0,
        "fresh_v161_target_outcomes_accessed": False,
        "classifier_derivation_compute_events": evaluated,
        "sample_labels_and_classifier_derivation_compute_separate": True,
        "v160_failure_preserved_not_reclassified": True,
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
        "classifier_receipt_id": domains.extension_content_id_v161(
            domains.CONSTRUCTION_K7_CLASSIFIER_RECEIPT_V161_DOMAIN, payload
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class PaidPathPrefixClassifierReceiptV161:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    classifier_receipt_id: str

    def to_document(self):
        return loads_canonical_json(self.canonical_bytes)


_CACHE = None


def run_paid_path_prefix_classifier_receipt_v161(
    source_preregistration_raw: bytes,
    v160_classifier_raw: bytes,
    v160_failed_campaign_raw: bytes,
    v160_failure_raw: bytes,
):
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if ATTEMPT_TERMINAL_STATE != "UNEXECUTED" or CLASSIFIER_RECEIPT_ID != "0" * 64:
        _fail("frozen V161 source attempt is terminal and will not be rerun")
    document = _document(
        source_preregistration_raw,
        v160_classifier_raw,
        v160_failed_campaign_raw,
        v160_failure_raw,
    )
    raw = canonical_json_bytes(document)
    _CACHE = PaidPathPrefixClassifierReceiptV161(
        _ISSUER, raw, document["classifier_receipt_id"]
    )
    return _CACHE


__all__ = (
    "ATTEMPT_TERMINAL_STATE",
    "CLASSIFIER_RECEIPT_ID",
    "run_paid_path_prefix_classifier_receipt_v161",
)
