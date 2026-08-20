from acfqp.generic_abstract_agreement_query_filter_v47 import (
    apply_abstract_agreement_query_filter_v47,
)
from acfqp.generic_flat_action_adapter_v45 import normalize_flat_action_adapter_v45
from acfqp.generic_portable_certificate_query_priority_v44 import (
    run_portable_priority_certificate_episode_v44,
)
from acfqp.generic_reusable_version_space_certificate_planner_v43 import (
    run_reusable_version_space_certificate_episode_v43,
)
from acfqp.generic_structural_rank_query_prior_v46 import (
    compile_structural_rank_query_prior_v46,
    translate_structural_rank_prior_to_initial_v44_priority_v46,
)
from test_generic_flat_action_adapter_v45 import _DomainAdapter
from test_generic_reusable_version_space_certificate_planner_v43 import (
    _Adapter,
    _source_fixture,
)


def test_v47_filters_without_target_outcomes_and_keeps_same_v44_engine():
    candidate, rows, catalogue, model = _source_fixture()
    source = run_reusable_version_space_certificate_episode_v43(
        _Adapter(catalogue),
        candidate,
        rows,
        reusable_model=model,
        model_source_episode_index=0,
        episode_index=1,
        maximum_abstract_depth=2,
        maximum_execution_steps=8,
    )
    prior = compile_structural_rank_query_prior_v46(
        source, candidate.public_document["layout"], catalogue
    )
    adapter = normalize_flat_action_adapter_v45(_DomainAdapter(catalogue))
    translated = translate_structural_rank_prior_to_initial_v44_priority_v46(
        prior, candidate, adapter
    )
    filtered = apply_abstract_agreement_query_filter_v47(
        model,
        candidate,
        adapter,
        translated,
        maximum_abstract_depth=2,
        maximum_support_branch_evaluations=1_000_000,
        support_feasible_beam_width=32,
    )
    receipt = filtered["agreement_filter_receipt"]
    assert receipt["target_transition_outcomes_used_for_filter"] is False
    assert receipt["ground_transition_authority_present"] is False
    kwargs = dict(
        reusable_model=model,
        model_source_episode_index=0,
        episode_index=2,
        maximum_abstract_depth=2,
        maximum_execution_steps=8,
    )
    selected = run_portable_priority_certificate_episode_v44(
        adapter,
        candidate,
        (),
        portable_query_priority=filtered["filtered_priority"],
        **kwargs,
    )
    model_only = run_portable_priority_certificate_episode_v44(
        adapter,
        candidate,
        (),
        portable_query_priority=filtered["model_only_inert_priority"],
        **kwargs,
    )
    assert selected["target_certificate_local_ground_support_labels"] == model_only[
        "target_certificate_local_ground_support_labels"
    ]
    assert selected["query_local_exact_overlay_exclusively_used_for_safety"] is True
