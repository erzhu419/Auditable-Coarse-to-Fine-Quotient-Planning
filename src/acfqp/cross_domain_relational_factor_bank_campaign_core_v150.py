"""V150 cross-domain bank campaign with certified abstract abstention."""

from __future__ import annotations

from types import FunctionType

from acfqp import construction_k7_domain_registry_extension_v150 as domains
from acfqp import cross_domain_relational_factor_bank_campaign_core_v149 as v149
from acfqp.certified_planner_abstention_sequence_v150 import (
    run_certified_planner_abstention_sequence_v150,
)


TARGET_FAMILIES = v149.TARGET_FAMILIES


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
    run_certificate_local_relational_overlay_sequence_v144r1=(
        run_certified_planner_abstention_sequence_v150
    ),
)
_BASE_OCCURRENCE = _clone(
    v149.build_cross_domain_relational_factor_bank_occurrence_v149,
    _OCCURRENCE_GLOBALS,
)


def build_cross_domain_relational_factor_bank_occurrence_v150(*args, **kwargs):
    base = _BASE_OCCURRENCE(*args, **kwargs)
    abstentions = sum(
        base[key]["incomplete_abstract_plan_abstention_count"]
        for key in (
            "anonymous_relational_factor_prior_owned_sequence",
            "strict_no_prior_owned_sequence",
        )
    )
    payload = {
        **{key: value for key, value in base.items() if key != "occurrence_id"},
        "schema": "acfqp.cross_domain_relational_factor_bank_occurrence.v150",
        "v149_failed_predecessor_preserved": True,
        "planner_action_path_failure_correction": (
            "INCOMPLETE_ABSTRACT_PATH_ABSTAINS_TO_CERTIFIED_LEGAL_SEARCH"
        ),
        "incomplete_abstract_path_never_used_as_execution_authority": True,
        "incomplete_abstract_plan_abstention_count": abstentions,
    }
    return {
        **payload,
        "occurrence_id": domains.extension_content_id_v150(
            domains.CONSTRUCTION_K7_OCCURRENCE_V150_DOMAIN, payload
        ),
    }


def _target(args):
    return build_cross_domain_relational_factor_bank_occurrence_v150(
        args[0],
        family=args[1],
        seed=args[2],
        episode_indices=args[3],
        bank_raw=args[4],
        verification_raw=args[5],
    )


_CAMPAIGN_GLOBALS = dict(v149.__dict__)
_CAMPAIGN_GLOBALS.update(_target=_target)
_BASE_CAMPAIGN = _clone(
    v149.build_cross_domain_relational_factor_bank_campaign_document_v149,
    _CAMPAIGN_GLOBALS,
)


def build_cross_domain_relational_factor_bank_campaign_document_v150(*args, **kwargs):
    base = _BASE_CAMPAIGN(*args, **kwargs)
    abstentions = sum(
        row["incomplete_abstract_plan_abstention_count"]
        for row in base["target_occurrences"]
    )
    gate = {
        **base["registered_gate"],
        "v149_preserved_failure_exercised_action_path_boundary": True,
        "fresh_v150_incomplete_abstract_path_abstention_observed": (
            abstentions > 0
        ),
    }
    gate["passed"] = base["registered_gate"]["passed"]
    payload = {
        **{key: value for key, value in base.items() if key != "campaign_id"},
        "schema": "acfqp.cross_domain_relational_factor_bank_campaign.v150",
        "registered_gate": gate,
        "preserved_v149_failure_kind": "PREREGISTERED_PLANNER_ACTION_PATH_FAILURE",
        "v149_identity_rerun": False,
        "certified_abstract_abstention_correction_applied": True,
        "incomplete_abstract_plan_abstention_count": abstentions,
    }
    return {
        **payload,
        "campaign_id": domains.extension_content_id_v150(
            domains.CONSTRUCTION_K7_CAMPAIGN_V150_DOMAIN, payload
        ),
    }


__all__ = (
    "TARGET_FAMILIES",
    "build_cross_domain_relational_factor_bank_campaign_document_v150",
    "build_cross_domain_relational_factor_bank_occurrence_v150",
)
