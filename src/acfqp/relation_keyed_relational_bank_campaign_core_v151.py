"""V151 relational-template utilization on a source-unseen stochastic family."""

from __future__ import annotations

from types import FunctionType

from acfqp import construction_k7_domain_registry_extension_v151 as domains
from acfqp import cross_domain_relational_factor_bank_campaign_core_v149 as v149
from acfqp.certified_planner_abstention_sequence_v150 import (
    run_certified_planner_abstention_sequence_v150,
)
from acfqp.generic_relation_keyed_workflow_adapter_v151 import (
    FAMILY,
    build_relation_keyed_workflow_adapter_v151,
)


TARGET_FAMILIES = (FAMILY,)


def _clone(function, namespace):
    clone = FunctionType(
        function.__code__,
        namespace,
        name=function.__name__,
        argdefs=function.__defaults__,
        closure=function.__closure__,
    )
    clone.__kwdefaults__ = function.__kwdefaults__
    return clone


_OCCURRENCE_GLOBALS = dict(v149.__dict__)
_OCCURRENCE_GLOBALS.update(
    _BUILDERS={FAMILY: build_relation_keyed_workflow_adapter_v151},
    run_certificate_local_relational_overlay_sequence_v144r1=(
        run_certified_planner_abstention_sequence_v150
    ),
)
_BASE_OCCURRENCE = _clone(
    v149.build_cross_domain_relational_factor_bank_occurrence_v149,
    _OCCURRENCE_GLOBALS,
)


def build_relation_keyed_relational_bank_occurrence_v151(*args, **kwargs):
    base = _BASE_OCCURRENCE(*args, **kwargs)
    prior = base["anonymous_relational_factor_prior_acquisition"]
    strict = base["strict_no_prior_acquisition"]
    gate = {
        **base["registered_gate"],
        "relational_artifact_selected_in_prior_arm": prior[
            "relational_artifact_expression_selected_count"
        ]
        > 0,
        "same_relational_expression_available_in_strict_pool": strict[
            "relational_artifact_expression_selected_count"
        ]
        > 0,
    }
    gate["passed"] = all(gate.values())
    abstentions = sum(
        base[key]["incomplete_abstract_plan_abstention_count"]
        for key in (
            "anonymous_relational_factor_prior_owned_sequence",
            "strict_no_prior_owned_sequence",
        )
    )
    payload = {
        **{key: value for key, value in base.items() if key != "occurrence_id"},
        "schema": "acfqp.relation_keyed_relational_bank_occurrence.v151",
        "registered_gate": gate,
        "v150_cross_domain_campaign_preserved": True,
        "relation_binding_derived_from_raw_transition_deltas": True,
        "direct_numeric_increment_field_present": False,
        "incomplete_abstract_path_never_used_as_execution_authority": True,
        "incomplete_abstract_plan_abstention_count": abstentions,
        "relational_template_selection_itself_observed": gate[
            "relational_artifact_selected_in_prior_arm"
        ],
    }
    return {
        **payload,
        "occurrence_id": domains.extension_content_id_v151(
            domains.CONSTRUCTION_K7_OCCURRENCE_V151_DOMAIN, payload
        ),
    }


def _target(args):
    return build_relation_keyed_relational_bank_occurrence_v151(
        args[0],
        family=args[1],
        seed=args[2],
        episode_indices=args[3],
        bank_raw=args[4],
        verification_raw=args[5],
    )


_CAMPAIGN_GLOBALS = dict(v149.__dict__)
_CAMPAIGN_GLOBALS.update(TARGET_FAMILIES=TARGET_FAMILIES, _target=_target)
_BASE_CAMPAIGN = _clone(
    v149.build_cross_domain_relational_factor_bank_campaign_document_v149,
    _CAMPAIGN_GLOBALS,
)


def build_relation_keyed_relational_bank_campaign_document_v151(*args, **kwargs):
    base = _BASE_CAMPAIGN(*args, **kwargs)
    relational = all(
        row["registered_gate"]["relational_artifact_selected_in_prior_arm"]
        for row in base["target_occurrences"]
    )
    gate = {
        **base["registered_gate"],
        "relational_artifact_selected_in_prior_everywhere": relational,
    }
    gate["passed"] = base["registered_gate"]["passed"] and relational
    payload = {
        **{key: value for key, value in base.items() if key != "campaign_id"},
        "schema": "acfqp.relation_keyed_relational_bank_campaign.v151",
        "registered_gate": gate,
        "relational_template_selection_itself_claimed_cross_domain": True,
        "relational_template_selection_claim_scope": (
            "ONLY_THE_PREREGISTERED_V151_RELATION_KEYED_WORKFLOW_COHORT"
        ),
        "v150_campaign_and_verification_preserved": True,
    }
    return {
        **payload,
        "campaign_id": domains.extension_content_id_v151(
            domains.CONSTRUCTION_K7_CAMPAIGN_V151_DOMAIN, payload
        ),
    }


__all__ = (
    "TARGET_FAMILIES",
    "build_relation_keyed_relational_bank_campaign_document_v151",
    "build_relation_keyed_relational_bank_occurrence_v151",
)
