import pytest

from acfqp.generic_portable_certificate_query_priority_v44 import (
    GenericPortableCertificateQueryPriorityV44Error,
    compile_portable_certificate_query_priority_v44,
    run_portable_priority_certificate_episode_v44,
    verify_portable_certificate_query_priority_v44,
)
from acfqp.generic_reusable_version_space_certificate_planner_v43 import (
    run_reusable_version_space_certificate_episode_v43,
)
from acfqp.generic_atomic_expression_world_model_v4 import FlatRawActionV4
from test_generic_reusable_version_space_certificate_planner_v43 import (
    _Adapter,
    _source_fixture,
)


def test_v44_priority_verifier_rejects_foreign_values():
    with pytest.raises(GenericPortableCertificateQueryPriorityV44Error):
        verify_portable_certificate_query_priority_v44({})


def test_v44_compiles_canonical_priority_and_maps_permuted_action_keys():
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
    priority = compile_portable_certificate_query_priority_v44(source, candidate)
    assert priority["raw_action_key_reused_across_occurrences"] is False
    target_catalogue = (
        FlatRawActionV4(9, (1, 2)),
        FlatRawActionV4(8, (2, 3)),
    )
    adapter = _Adapter(target_catalogue)
    derived = run_portable_priority_certificate_episode_v44(
        adapter,
        candidate,
        (),
        reusable_model=model,
        portable_query_priority=priority,
        model_source_episode_index=0,
        episode_index=2,
        maximum_abstract_depth=2,
        maximum_execution_steps=8,
    )
    strict = run_portable_priority_certificate_episode_v44(
        adapter,
        candidate,
        (),
        reusable_model=None,
        portable_query_priority=None,
        model_source_episode_index=0,
        episode_index=2,
        maximum_abstract_depth=2,
        maximum_execution_steps=8,
    )
    assert derived["portable_priority_ordering_accepted_count"] > 0
    assert derived["target_certificate_local_ground_support_labels"] <= strict[
        "target_certificate_local_ground_support_labels"
    ]
    assert derived["all_ground_queries_followed_failed_certificates"] is True
    assert derived["query_local_exact_overlay_exclusively_used_for_safety"] is True
    assert derived["reusable_artifacts_used_as_safety_authority"] is False
