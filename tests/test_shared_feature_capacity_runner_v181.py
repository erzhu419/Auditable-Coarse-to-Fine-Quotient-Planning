"""Source coverage must not be inferred from a target oracle potential."""
from scripts import run_controlled_predictive_shared_feature_capacity_v181 as runner


def test_target_only_vertices_are_not_mistaken_for_source_support():
    a, b, c = ([0, i, 0, 0, 0, 0] for i in (1, 2, 3))
    problems = dict(SOURCE=dict(vertices=[dict(features=a), dict(features=b)]),
        TARGET=dict(vertices=[dict(features=b), dict(features=c)], roots=[
            dict(root_id='seen', classes=[dict(features=b)]),
            dict(root_id='unseen', classes=[dict(features=b), dict(features=c)])]))
    result = runner.feature_coverage(problems)
    assert (result['source_vertices'], result['target_vertices'], result['common_vertices']) == (2, 2, 1)
    assert result['target_only_tuples'] == [c]
    assert result['target_roots_all_tuples_seen'] == 1
    assert result['target_root_records'][1]['unseen_tuples'] == [c]
    assert result['work'] == dict(vertex_feature_value_reads=24,
        target_class_feature_value_reads=18, source_membership_tests=3)
