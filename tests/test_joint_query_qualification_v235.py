from fractions import Fraction as F
from itertools import product

from acfqp.science import joint_query_evidence_v235 as core
from acfqp.science import kernel_query_profile_v232 as old
from scripts import audit_kernel_query_profile_v232 as independent


def case():
    return {'operating': 'low', 'retry_cost': '17/20'}


def rows(short=('DELIVERY',)*32, detour=('DELIVERY',)*32, retry=('DELIVERY',)*32):
    return dict(zip(core.OPERATORS, (short, detour, retry)))


def test_coarsened_numerator_uses_binary_prior_not_zero_count_three_category_prior():
    observations = rows(detour=('DELIVERY',)*19+('RECOVERY',)*5+('LOST',)*8)
    counts = core.project_counts(observations, 'D_DEL')
    embedded = core.embedded_counts(counts, 'D_DEL')
    assert embedded[core.D] == {'DELIVERY': 19, 'LOST': 13, 'RECOVERY': 0}
    actual = core.mixture_normalizer(tuple(counts['D_DEL'].values()))
    wrong = old.joint.mixture_normalizer(tuple(embedded[core.D].values()))
    assert actual != wrong
    proof = core.certificate(observations, case(), 'goal', 'DETOUR_RETURN', 'WAIT')
    assert proof['log_mixture_lower'] == old._log_bounds(actual)[0]
    assert all(value == 0 for op in (core.S, core.R) for value in proof['embedded_counts'][op].values())


def test_embedded_gap_matches_sufficient_projection_in_every_direction():
    for query, chosen, other in product(('goal', 'risk'), core.POLICIES, core.POLICIES):
        if chosen == other:
            continue
        family = core.canonical_family(query, chosen, other)
        for s, d, r in product((F(0), F(1)), core.ALPHABETS[core.D], (F(0), F(1))):
            kernel = old._kernel(short=s, delivery=F(d == 'DELIVERY'),
                                 recovery=F(d == 'RECOVERY'), retry=r)
            parameters = core.project_parameters(kernel, family)
            counts = {name: {cat: int(value) for cat, value in row.items()}
                      for name, row in parameters.items()}
            embedded = core.embedded_counts(counts, family)
            embedded_kernel = {op: {cat: F(count, sum(row.values())) if sum(row.values()) else F(1, len(row))
                                   for cat, count in row.items()} for op, row in embedded.items()}
            assert old.gap(case(), query, chosen, other, embedded_kernel) == core.gap(
                case(), query, chosen, other, parameters)


def test_bad_mle_is_unknown_and_lies_in_its_one_projected_region():
    proof = core.certificate(rows(), case(), 'goal', 'WAIT', 'SHORT')
    assert proof['status'] == 'unknown' and not proof['certified']
    assert proof['witness_kind'] == 'bad_null_mle' and proof['bad_null_gap'] > F(1, 20)
    parameters = core.project_parameters(proof['bad_null_kernel'], proof['family'])
    assert core.membership(proof['projected_counts'], parameters)['exact_inside']
    assert proof['partitions'] == 0 and not proof['leaves']


def test_nonlinear_cells_cover_full_retry_domain_and_use_valid_endpoints_for_both_signs():
    detour = ('DELIVERY',)*32+('RECOVERY',)*32
    forward = core.certificate(rows(detour=detour, retry=('LOST',)*64), case(),
                               'risk', 'DETOUR_RETURN', 'DETOUR_RETRY')
    reverse = core.certificate(rows(detour=detour, retry=('DELIVERY',)*64), case(),
                               'risk', 'DETOUR_RETRY', 'DETOUR_RETURN')
    for proof in (forward, reverse):
        assert proof['partitions'] == len(proof['leaves']) == 32
        assert [leaf['retry_interval'] for leaf in proof['leaves']] == [
            [F(index, 32), F(index+1, 32)] for index in range(32)]
        endpoint_index = 1 if proof['retry_slope'] >= 0 else 0
        assert all(leaf['gap_endpoint'] == leaf['retry_interval'][endpoint_index] for leaf in proof['leaves'])
        for leaf in proof['leaves']:
            for s, d in product((0, 1), core.ALPHABETS[core.D]):
                endpoint_gap = independent.gap(case(), 'risk', proof['chosen'], proof['other'],
                    independent.corner_kernel(s, d, leaf['gap_endpoint']))
                assert all(endpoint_gap >= independent.gap(case(), 'risk', proof['chosen'], proof['other'],
                    independent.corner_kernel(s, d, r)) for r in leaf['retry_interval'])


def test_global_likelihood_dual_is_independently_valid_and_uses_strict_threshold():
    proof = core.certificate(rows(short=('DELIVERY',)*256), case(), 'goal', 'SHORT', 'WAIT')
    assert proof['witness_kind'] == 'global_likelihood_dual' and proof['certified']
    checks = []
    for leaf in proof['leaves']:
        checked = independent.audit_leaf(case(), 'goal', 'SHORT', 'WAIT', proof['embedded_counts'],
                                         leaf, lambda name, condition: checks.append((name, condition)))
        assert checked == leaf['log_bad_likelihood_upper']
    assert checks and all(condition for _, condition in checks)
    assert proof['log_e_lower'] == proof['log_mixture_lower']-proof['log_bad_likelihood_upper']
    assert proof['log_e_lower'] > proof['log_threshold_upper']


def test_cache_reuses_identical_projection_and_preserves_original_query_policies():
    observations = rows(detour=('DELIVERY',)*256, retry=('DELIVERY',)*256)
    cache, work = {}, {}
    chosen = {'reward': {'policy': 'WAIT'}, 'goal': {'policy': 'DETOUR_RETRY'},
              'risk': {'policy': 'DETOUR_RETURN'}}
    first = core.certificates(observations, case(), chosen, cache, work)
    second = core.certificates(observations, case(), chosen, cache, work)
    assert first == second and len(cache) == 6
    assert work['projected_certificate_calls'] == 12 and work['projected_certificate_cache_hits'] == 6
    assert work['projected_unique_certificates'] == 6
    assert first['queries']['reward'] == {'policy': 'WAIT', 'certified': True, 'kind': 'known_nonnegative_cost'}
    assert {query: row['policy'] for query, row in first['queries'].items()} == {
        query: row['policy'] for query, row in chosen.items()}
    assert len(first['comparison_records']) == 6
    assert first['all_ready'] == all(row['certified'] for row in first['queries'].values())
