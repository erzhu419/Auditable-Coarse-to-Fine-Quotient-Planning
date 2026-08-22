"""Fresh reservoir campaign with typed receipts issued inside the orderer."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
import copy
import hashlib
from types import FunctionType, SimpleNamespace

from acfqp import applicable_plan_receipt_set_sequence_v168 as sequence_v168
from acfqp import construction_k7_domain_registry_extension_v172 as domains
from acfqp import fifth_family_total_plan_receipt_set_campaign_core_v168 as v168
from acfqp import fourth_family_sample_tax_transfer_campaign_core_v166 as v166
from acfqp.generic_reservoir_dispatch_adapter_v171 import (
    FAMILY as RESERVOIR_DISPATCH_FAMILY,
    build_reservoir_dispatch_adapter_v171,
    reservoir_dispatch_config_v171,
)
from acfqp.online_typed_plan_receipt_sequence_v172 import (
    TAXONOMY,
    run_online_typed_plan_receipt_sequence_v172,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


TARGET_FAMILIES = (*v168.TARGET_FAMILIES, RESERVOIR_DISPATCH_FAMILY)
V171_CAMPAIGN_ID = "ca284948d3d8886025fb13a84cffbab9bb535c242d292a2a68dd194bef4ed463"
V171_CAMPAIGN_BYTE_COUNT = 14_712_225
V171_CAMPAIGN_SHA256 = "95b2fb332a5813d83a50b4ba192cc5720e054c009e8af4b3e9ce8c93cf99f76a"
V171_VERIFICATION_ID = "422770529178614103624e873a5a1aaf732df6b949fe0bfe50edad3ad2fb78d0"
V171_VERIFICATION_BYTE_COUNT = 1_894
V171_VERIFICATION_SHA256 = "a668ce94f507b62a22c85bdc8c569d39991394a29687069a531c8ac90138014c"


def online_typed_plan_receipt_campaign_config_v172():
    config = v168.fifth_family_total_plan_receipt_set_campaign_config_v168()
    reservoir = reservoir_dispatch_config_v171()
    config["families"][RESERVOIR_DISPATCH_FAMILY] = copy.deepcopy(
        reservoir["families"][RESERVOIR_DISPATCH_FAMILY]
    )
    config["families"][RESERVOIR_DISPATCH_FAMILY][
        "maximum_acquisition_labels"
    ] = 2_048
    return config


_SEQUENCE_SOURCE_PROXY = SimpleNamespace(
    CONSTRUCTION_K7_SEQUENCE_V154_DOMAIN=domains.CONSTRUCTION_K7_SEQUENCE_V172_DOMAIN,
)
_SEQUENCE_OUTPUT_PROXY = SimpleNamespace(
    extension_content_id_v168=domains.extension_content_id_v172,
    CONSTRUCTION_K7_SEQUENCE_V168_DOMAIN=domains.CONSTRUCTION_K7_SEQUENCE_V172_DOMAIN,
)
_ANNOTATOR_GLOBALS = dict(sequence_v168.__dict__)
_ANNOTATOR_GLOBALS.update(
    domains_v154=_SEQUENCE_SOURCE_PROXY,
    domains=_SEQUENCE_OUTPUT_PROXY,
)
_ANNOTATE_V168_SHAPE_V172 = FunctionType(
    sequence_v168.annotate_applicable_plan_receipt_set_sequence_v168.__code__,
    _ANNOTATOR_GLOBALS,
    name="_annotate_online_v168_shape_v172",
)

_V160_DOMAIN_PROXY = SimpleNamespace(
    extension_content_id_v160=domains.extension_content_id_v172,
    CONSTRUCTION_K7_OCCURRENCE_V160_DOMAIN=domains.CONSTRUCTION_K7_OCCURRENCE_V172_DOMAIN,
)
_V160_GLOBALS = dict(v168._BASE_V160_OCCURRENCE_V168.__globals__)  # noqa: SLF001
_V160_GLOBALS.update(
    domains=_V160_DOMAIN_PROXY,
    _BUILDERS={
        **_V160_GLOBALS["_BUILDERS"],
        RESERVOIR_DISPATCH_FAMILY: build_reservoir_dispatch_adapter_v171,
    },
    run_certified_memoized_planner_sequence_v154=(
        run_online_typed_plan_receipt_sequence_v172
    ),
    annotate_applicable_plan_mode_sequence_v157=_ANNOTATE_V168_SHAPE_V172,
)
_BASE_V160_OCCURRENCE = FunctionType(
    v168._BASE_V160_OCCURRENCE_V168.__code__,  # noqa: SLF001
    _V160_GLOBALS,
    name="_base_online_receipt_occurrence_v172",
)

_V166_DOMAIN_PROXY = SimpleNamespace(
    extension_content_id_v166=domains.extension_content_id_v172,
    CONSTRUCTION_K7_OCCURRENCE_V166_DOMAIN=domains.CONSTRUCTION_K7_OCCURRENCE_V172_DOMAIN,
    CONSTRUCTION_K7_CAMPAIGN_V166_DOMAIN=domains.CONSTRUCTION_K7_CAMPAIGN_V172_DOMAIN,
)
_V166_GLOBALS = dict(v166.__dict__)
_V166_GLOBALS.update(
    domains=_V166_DOMAIN_PROXY,
    _BASE_OCCURRENCE=_BASE_V160_OCCURRENCE,
    TARGET_FAMILIES=TARGET_FAMILIES,
)
_BASE_V166_OCCURRENCE = FunctionType(
    v166.build_fourth_family_sample_tax_occurrence_v166.__code__,
    _V166_GLOBALS,
    name="_base_online_receipt_v166_occurrence_v172",
)

_V168_DOMAIN_PROXY = SimpleNamespace(
    extension_content_id_v168=domains.extension_content_id_v172,
    CONSTRUCTION_K7_OCCURRENCE_V168_DOMAIN=domains.CONSTRUCTION_K7_OCCURRENCE_V172_DOMAIN,
)
_V168_GLOBALS = dict(v168.__dict__)
_V168_GLOBALS.update(
    domains=_V168_DOMAIN_PROXY,
    _BASE_V166_OCCURRENCE_V168=_BASE_V166_OCCURRENCE,
    TARGET_FAMILIES=TARGET_FAMILIES,
)
_BASE_V168_OCCURRENCE = FunctionType(
    v168.build_fifth_family_total_plan_receipt_set_occurrence_v168.__code__,
    _V168_GLOBALS,
    name="_base_online_receipt_v168_occurrence_v172",
)


def build_online_typed_plan_receipt_occurrence_v172(
    config,
    *,
    family,
    seed,
    episode_indices,
    bank_raw,
    verification_raw,
    classifier_receipt_raw,
):
    if family != RESERVOIR_DISPATCH_FAMILY:
        raise ValueError("V172 target family is not the registered sixth family")
    base = _BASE_V168_OCCURRENCE(
        config,
        family=family,
        seed=seed,
        episode_indices=episode_indices,
        bank_raw=bank_raw,
        verification_raw=verification_raw,
        classifier_receipt_raw=classifier_receipt_raw,
    )
    sequences = (
        base["progressive_prior_sequence"],
        base["progressive_strict_sequence"],
    )
    gate = {
        key: value
        for key, value in base["registered_gate"].items()
        if key != "passed"
    }
    gate.update(
        all_plan_receipts_issued_online_before_orderer_return=all(
            sequence[
                "every_abstract_plan_receipt_issued_before_orderer_return"
            ]
            is True
            and sequence["online_plan_issuance_receipt_count"]
            == sum(
                len(episode["abstract_plan_receipts"])
                for episode in sequence["episodes"]
            )
            for sequence in sequences
        ),
        every_executed_action_joins_prior_online_receipt=all(
            sequence["every_executed_action_joins_prior_online_receipt"] is True
            and sequence["online_execution_join_receipt_count"]
            == sequence["execution_step_count"]
            for sequence in sequences
        ),
        complete_four_source_online_taxonomy=all(
            set(sequence["online_typed_plan_source_histogram"])
            == set(TAXONOMY.values())
            for sequence in sequences
        ),
        online_receipts_preserve_delegate_plan_bytes=all(
            sequence["delegate_plan_byte_identity_preserved"] is True
            for sequence in sequences
        ),
        online_receipts_do_not_change_planning_or_execution=all(
            sequence["online_receipt_changes_planning_or_execution"] is False
            for sequence in sequences
        ),
        query_local_exact_overlay_remains_only_safety_authority=all(
            sequence[
                "query_local_exact_overlay_remains_only_safety_authority"
            ]
            is True
            and sequence["online_receipt_is_model_or_safety_authority"] is False
            for sequence in sequences
        ),
        factor_prior_strictly_reduces_acquisition_labels=(
            base["factor_prior_sample_reduction_within_progressive_policy"] > 0
        ),
        query_policy_noninferior=(
            base["query_policy_sample_reduction_vs_legacy_path_first"] >= 0
        ),
    )
    gate["passed"] = all(value for value in gate.values() if type(value) is bool)
    histogram = {
        source: sum(
            sequence["online_typed_plan_source_histogram"][source]
            for sequence in sequences
        )
        for source in TAXONOMY.values()
    }
    payload = {
        **{
            key: value
            for key, value in base.items()
            if key not in {"schema", "occurrence_id", "registered_gate"}
        },
        "schema": "acfqp.online_typed_plan_receipt_occurrence.v172",
        "online_typed_plan_source_histogram": histogram,
        "online_plan_issuance_receipt_count": sum(
            sequence["online_plan_issuance_receipt_count"]
            for sequence in sequences
        ),
        "online_execution_join_receipt_count": sum(
            sequence["online_execution_join_receipt_count"]
            for sequence in sequences
        ),
        "registered_gate": gate,
        "sample_tax_claim_scope": "ONLY_THIS_PREREGISTERED_V172_ONLINE_RECEIPT_COHORT",
        "online_receipts_change_planning_or_execution": False,
        "online_receipts_are_model_or_safety_authority": False,
    }
    return {
        **payload,
        "occurrence_id": domains.extension_content_id_v172(
            domains.CONSTRUCTION_K7_OCCURRENCE_V172_DOMAIN, payload
        ),
    }


def _target_v172(args):
    return build_online_typed_plan_receipt_occurrence_v172(
        args[0],
        family=args[1],
        seed=args[2],
        episode_indices=args[3],
        bank_raw=args[4],
        verification_raw=args[5],
        classifier_receipt_raw=args[6],
    )


def _frozen(raw, *, count, digest, identity_key, identity, name):
    document = loads_canonical_json(raw)
    if not (
        canonical_json_bytes(document) == raw
        and len(raw) == count
        and hashlib.sha256(raw).hexdigest() == digest
        and document.get(identity_key) == identity
    ):
        raise ValueError(f"V172 frozen predecessor changed: {name}")
    return document


def build_online_typed_plan_receipt_campaign_v172(
    config,
    *,
    preregistration_id,
    bank_raw,
    verification_raw,
    classifier_receipt_raw,
    v171_campaign_raw,
    v171_verification_raw,
):
    v171_campaign = _frozen(
        v171_campaign_raw,
        count=V171_CAMPAIGN_BYTE_COUNT,
        digest=V171_CAMPAIGN_SHA256,
        identity_key="campaign_id",
        identity=V171_CAMPAIGN_ID,
        name="V171 campaign",
    )
    v171_verification = _frozen(
        v171_verification_raw,
        count=V171_VERIFICATION_BYTE_COUNT,
        digest=V171_VERIFICATION_SHA256,
        identity_key="verification_id",
        identity=V171_VERIFICATION_ID,
        name="V171 verification",
    )
    if not (
        v171_campaign["registered_gate"]["passed"] is True
        and v171_verification[
            "sixth_family_world_model_reuse_independently_verified"
        ]
        is True
        and v171_verification[
            "sixth_family_factor_prior_sample_tax_reduction_independently_verified"
        ]
        is True
    ):
        raise ValueError("V172 predecessor claim boundary changed")
    args = [
        (
            config,
            row["family"],
            row["seed"],
            tuple(config["target_episode_indices"]),
            bank_raw,
            verification_raw,
            classifier_receipt_raw,
        )
        for row in config["target_occurrences"]
    ]
    if config["target_worker_count"] == 1:
        rows = [_target_v172(row) for row in args]
    else:
        with ProcessPoolExecutor(max_workers=config["target_worker_count"]) as executor:
            rows = list(executor.map(_target_v172, args))
    numeric = [
        key for key, value in rows[0]["accounting"].items() if type(value) is int
    ]
    accounting = {
        key: sum(row["accounting"][key] for row in rows) for key in numeric
    }
    accounting.update(
        total_query_policy_labels_avoided_vs_exact_path_first=sum(
            row["query_policy_sample_reduction_vs_legacy_path_first"] for row in rows
        ),
        total_factor_prior_labels_avoided_within_same_query_policy=sum(
            row["factor_prior_sample_reduction_within_progressive_policy"]
            for row in rows
        ),
        online_plan_issuance_receipt_count=sum(
            row["online_plan_issuance_receipt_count"] for row in rows
        ),
        online_execution_join_receipt_count=sum(
            row["online_execution_join_receipt_count"] for row in rows
        ),
        sample_labels_execution_steps_derivation_planning_and_receipt_compute_separate=True,
        scalar_cost_aggregation_performed=False,
    )
    histogram = {
        source: sum(row["online_typed_plan_source_histogram"][source] for row in rows)
        for source in TAXONOMY.values()
    }
    gate = {
        "required_fresh_occurrence_count": config["required_target_occurrence_count"],
        "passed_fresh_occurrence_count": sum(
            row["registered_gate"]["passed"] for row in rows
        ),
        "every_target_is_fresh_reservoir_dispatch": all(
            row["target_family"] == RESERVOIR_DISPATCH_FAMILY for row in rows
        ),
        "v171_frozen_predecessor_preserved": True,
        "every_plan_receipt_issued_online": all(
            row["registered_gate"][
                "all_plan_receipts_issued_online_before_orderer_return"
            ]
            for row in rows
        ),
        "every_execution_joins_prior_online_receipt": all(
            row["registered_gate"][
                "every_executed_action_joins_prior_online_receipt"
            ]
            for row in rows
        ),
        "zero_unknown_online_plan_sources": all(
            set(row["online_typed_plan_source_histogram"])
            == set(TAXONOMY.values())
            for row in rows
        ),
        "factor_prior_strictly_reduces_labels": all(
            row["factor_prior_sample_reduction_within_progressive_policy"] > 0
            for row in rows
        ),
        "query_policy_noninferior": all(
            row["query_policy_sample_reduction_vs_legacy_path_first"] >= 0
            for row in rows
        ),
        "both_arm_receding_plans_succeed": all(
            row["registered_gate"]["both_arm_receding_episodes_succeed"]
            for row in rows
        ),
        "certificate_failure_only_local_ground_distinctions": all(
            row["registered_gate"][
                "certificate_failure_only_local_ground_distinctions"
            ]
            for row in rows
        ),
        "online_receipts_do_not_change_planning_or_execution": all(
            row["online_receipts_change_planning_or_execution"] is False
            for row in rows
        ),
    }
    gate["passed"] = (
        len(rows) == config["required_target_occurrence_count"]
        and gate["passed_fresh_occurrence_count"] == len(rows)
        and all(value for value in gate.values() if type(value) is bool)
    )
    payload = {
        "schema": "acfqp.online_typed_plan_receipt_campaign.v172",
        "preregistration_id": preregistration_id,
        "frozen_v171_campaign_id": V171_CAMPAIGN_ID,
        "frozen_v171_verification_id": V171_VERIFICATION_ID,
        "target_occurrences": rows,
        "target_occurrence_ids": [row["occurrence_id"] for row in rows],
        "online_receipt_accounting": accounting,
        "online_typed_plan_source_histogram": histogram,
        "registered_gate": gate,
        "online_typed_receipt_taxonomy_observed": gate["passed"],
        "factor_prior_sample_tax_reduction_observed": gate[
            "factor_prior_strictly_reduces_labels"
        ],
        "sample_tax_claim_scope": "ONLY_THIS_PREREGISTERED_V172_ONLINE_RECEIPT_COHORT",
        "online_receipts_change_planning_or_execution": False,
        "online_receipts_are_model_or_safety_authority": False,
        "query_local_exact_overlay_remains_only_safety_authority": True,
        "complete_world_model_synthesized": False,
        "arbitrary_unseen_domain_transfer_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    return {
        **payload,
        "campaign_id": domains.extension_content_id_v172(
            domains.CONSTRUCTION_K7_CAMPAIGN_V172_DOMAIN, payload
        ),
    }


__all__ = (
    "RESERVOIR_DISPATCH_FAMILY",
    "build_online_typed_plan_receipt_campaign_v172",
    "build_online_typed_plan_receipt_occurrence_v172",
    "online_typed_plan_receipt_campaign_config_v172",
)
