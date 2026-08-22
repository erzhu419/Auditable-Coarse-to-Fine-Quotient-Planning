"""Keep incomplete abstract plans as abstentions, then use exact certification."""

from __future__ import annotations

from types import FunctionType

from acfqp import certificate_local_relational_overlay_sequence_v144r1 as v144
from acfqp import construction_k7_domain_registry_extension_v150 as domains
from acfqp import standalone_generic_owned_sequence_v126 as v126


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


# V144R1 changed the local exception class used by the cloned V126 planner.
# That accidentally escaped V126's documented planner-abstention boundary.  V150
# restores the V126 error class only inside the fallible abstract orderer; all
# model/sequence invariants retain V144R1's fail-closed error.
_PLAN_GLOBALS = dict(v126.__dict__)
_PLAN_GLOBALS.update(
    verify_standalone_generic_model_state_v125=v144._verify_state,  # noqa: SLF001
    _observation_graph_plan=v144._observation_graph_plan,  # noqa: SLF001
    _fail=v126._fail,  # noqa: SLF001
)
_PLAN = _clone(v126._plan_with_branch_cache_v126, _PLAN_GLOBALS)  # noqa: SLF001
_ORDERER_GLOBALS = dict(v126.__dict__)
_ORDERER_GLOBALS.update(
    _plan_with_branch_cache_v126=_PLAN,
    _fail=v126._fail,  # noqa: SLF001
)
_ORDERER = _clone(v126._owned_orderer, _ORDERER_GLOBALS)  # noqa: SLF001
_RUN_GLOBALS = dict(v126.__dict__)
_RUN_GLOBALS.update(
    initialize_standalone_generic_model_v125=v144._initialize,  # noqa: SLF001
    advance_standalone_generic_model_v125=v144._advance,  # noqa: SLF001
    verify_standalone_generic_model_full_rebuild_v125=v144._full_rebuild,  # noqa: SLF001
    _owned_orderer=_ORDERER,
    _fail=v144._fail,  # noqa: SLF001
)
_RUN = _clone(v126.run_standalone_generic_owned_sequence_v126, _RUN_GLOBALS)


def run_certified_planner_abstention_sequence_v150(*args, **kwargs):
    historical = _RUN(*args, **kwargs)
    payload = {
        **{
            key: value
            for key, value in historical.items()
            if key not in {"schema", "sequence_id"}
        },
        "schema": "acfqp.certified_planner_abstention_sequence.v150",
        "query_local_relational_overlay_model_present": True,
        "incomplete_abstract_action_path_treated_as_abstention": True,
        "incomplete_abstract_plan_abstention_count": sum(
            episode["abstract_plan_abstention_count"]
            for episode in historical["episodes"]
        ),
        "certified_legal_search_remains_fallback_authority": True,
        "source_partial_program_mutated_after_certificate_failure": False,
        "every_uncompiled_edge_is_certificate_local": all(
            model["all_overlay_rows_acquired_after_failed_certificate"] is True
            for model in historical["quotient_models_after_each_episode"]
        ),
        "total_query_local_exact_overlay_edge_count": max(
            model["query_local_exact_overlay_edge_count"]
            for model in historical["quotient_models_after_each_episode"]
        ),
        "overlay_promoted_to_global_dynamics": False,
        "query_local_overlay_used_as_safety_authority": False,
        "complete_ground_world_model_synthesized": False,
    }
    return {
        **payload,
        "sequence_id": domains.extension_content_id_v150(
            domains.CONSTRUCTION_K7_SEQUENCE_V150_DOMAIN, payload
        ),
    }


__all__ = ("run_certified_planner_abstention_sequence_v150",)
