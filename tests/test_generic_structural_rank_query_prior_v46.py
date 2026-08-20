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
    verify_structural_rank_query_prior_v46,
)
from test_generic_flat_action_adapter_v45 import _DomainAdapter
from test_generic_reusable_version_space_certificate_planner_v43 import (
    _Adapter,
    _source_fixture,
)


def test_v46_translates_source_rank_without_target_transition_outcomes():
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
    prior = verify_structural_rank_query_prior_v46(
        compile_structural_rank_query_prior_v46(
            source, candidate.public_document["layout"], catalogue
        )
    )
    target = normalize_flat_action_adapter_v45(_DomainAdapter(catalogue[::-1]))
    translated = translate_structural_rank_prior_to_initial_v44_priority_v46(
        prior, candidate, target
    )
    receipt = translated["translation_receipt"]
    assert receipt["target_transition_outcomes_used"] is False
    assert receipt["ordering_only"] is True
    assert receipt["safety_authority_present"] is False
    assert translated["portable_priority"]["priority_state_count"] == 1
    episode = run_portable_priority_certificate_episode_v44(
        target,
        candidate,
        (),
        reusable_model=model,
        portable_query_priority=translated["portable_priority"],
        model_source_episode_index=0,
        episode_index=2,
        maximum_abstract_depth=2,
        maximum_execution_steps=8,
    )
    assert episode["portable_priority_ordering_accepted_count"] > 0
    assert episode["query_local_exact_overlay_exclusively_used_for_safety"] is True
