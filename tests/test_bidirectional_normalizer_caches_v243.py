"""Equal paired prefixes must not share another arm's exact arithmetic cache."""
from scripts import run_bidirectional_lifecycle_v243 as runner


def test_selected_arm_owns_execution_and_query_normalizers_including_convex_alias(monkeypatch):
    monkeypatch.setattr(runner.execution_joint, 'mixture_normalizer', runner.execution_joint.mixture_normalizer)
    monkeypatch.setattr(runner.query_joint, 'mixture_normalizer', runner.query_joint.mixture_normalizer)
    monkeypatch.setattr(runner.convex, 'mixture_normalizer', runner.convex.mixture_normalizer)
    monkeypatch.setattr(runner.scalar_cs, '_INTERVAL_CACHE', runner.scalar_cs._INTERVAL_CACHE)
    normalizers = runner.normalizer_caches()
    intervals = {arm: {} for arm in runner.ARMS}
    counts = (7, 5)
    expected_execution = runner.execution_joint.mixture_normalizer.__wrapped__(counts)
    expected_query = runner.query_joint.mixture_normalizer.__wrapped__(counts)
    for arm in ('ONE_WAY', 'TWO_WAY'):
        runner.activate_arm_caches(arm, intervals, normalizers)
        assert runner.scalar_cs._INTERVAL_CACHE is intervals[arm]
        assert runner.execution_joint.mixture_normalizer is normalizers[arm]['execution']
        assert runner.query_joint.mixture_normalizer is runner.convex.mixture_normalizer is normalizers[arm]['query']
        assert runner.execution_joint.mixture_normalizer(counts) == expected_execution
        assert runner.query_joint.mixture_normalizer(counts) == expected_query
        assert runner.convex.mixture_normalizer(counts) == expected_query
        execution = normalizers[arm]['execution'].cache_info()
        query = normalizers[arm]['query'].cache_info()
        assert (execution.hits, execution.misses, execution.maxsize) == (0, 1, 4096)
        assert (query.hits, query.misses, query.maxsize) == (1, 1, 256)
    runner.activate_arm_caches('ONE_WAY', intervals, normalizers)
    assert runner.execution_joint.mixture_normalizer(counts) == expected_execution
    assert normalizers['ONE_WAY']['execution'].cache_info().hits == 1
    assert normalizers['TWO_WAY']['execution'].cache_info().hits == 0
    assert normalizers['REBUILD']['execution'].cache_info().misses == 0
    assert normalizers['REBUILD']['query'].cache_info().misses == 0
    fresh_life = runner.normalizer_caches()
    assert all(function.cache_info().currsize == 0 for functions in fresh_life.values()
               for function in functions.values())
