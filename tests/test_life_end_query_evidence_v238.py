from fractions import Fraction as F

from acfqp.science import life_end_query_evidence_v238 as core
from acfqp.science import source_predictive_evidence_v236 as prior
from scripts import audit_kernel_query_profile_v232 as independent


def case():
    return {'operating': 'low', 'retry_cost': '17/20'}


def rows(short=('DELIVERY',)*128, detour=('DELIVERY',)*128, retry=('DELIVERY',)*128):
    return dict(zip(prior.OPERATORS, (short, detour, retry)))


def test_source_is_only_in_predictive_numerator_and_linear_dual_is_independently_valid():
    training, validation = rows(short=('DELIVERY',)*384), rows(short=('DELIVERY',)*32)
    proof = core.certificate(training, validation, case(), 'goal', 'SHORT', 'WAIT')
    assert proof['training_counts'] == {'S': {'DELIVERY': 384, 'LOST': 0}}
    assert proof['validation_counts'] == {'S': {'DELIVERY': 32, 'LOST': 0}}
    assert proof['embedded_counts'][prior.OPERATORS[0]] == {'DELIVERY': 32, 'LOST': 0}
    assert all(sum(proof['embedded_counts'][operator].values()) == 0 for operator in prior.OPERATORS[1:])
    predictive = prior.predictive_normalizer((384, 0), (32, 0))
    assert proof['log_predictive_lower'] == core.profile._log_bounds(predictive)[0]
    assert proof['certified'] and proof['witness_kind'] == 'global_likelihood_dual'
    checks = []
    for leaf in proof['leaves']:
        upper = independent.audit_leaf(case(), 'goal', 'SHORT', 'WAIT', proof['embedded_counts'],
            leaf, lambda name, valid: checks.append((name, valid)))
        assert upper == leaf['log_bad_likelihood_upper']
    assert checks and all(valid for _, valid in checks)
    assert proof['log_e_lower'] == proof['log_predictive_lower']-proof['log_bad_likelihood_upper']
    assert proof['log_e_lower'] > proof['log_threshold_upper']


def test_bad_validation_mle_is_unknown_even_when_training_favors_opposite_outcomes():
    training = rows(short=('LOST',)*384)
    validation = rows(short=('DELIVERY',)*32)
    proof = core.certificate(training, validation, case(), 'goal', 'WAIT', 'SHORT')
    assert proof['status'] == 'unknown' and not proof['certified']
    assert proof['witness_kind'] == 'bad_null_mle' and proof['bad_null_gap'] >= core.REGRET
    parameters = prior.project_parameters(proof['bad_null_kernel'], proof['family'])
    assert prior.membership(proof['training_counts'], proof['validation_counts'], parameters,
                            threshold=1)['exact_inside']
    assert proof['partitions'] == 0 and proof['leaves'] == []


def test_cache_distinguishes_training_and_validation_when_combined_counts_are_equal():
    cache, work = {}, {}
    training, validation = rows(short=('DELIVERY',)*16), rows(short=('DELIVERY',)*16)
    first = core.certificate(training, validation, case(), 'goal', 'SHORT', 'WAIT', cache, work)
    second = core.certificate(rows(short=('DELIVERY',)*17), validation, case(),
                              'goal', 'SHORT', 'WAIT', cache, work)
    third = core.certificate(training, rows(short=('DELIVERY',)*17), case(),
                             'goal', 'SHORT', 'WAIT', cache, work)
    again = core.certificate(training, validation, case(), 'goal', 'SHORT', 'WAIT', cache, work)
    assert again is first and len(cache) == 3
    assert second['log_predictive_lower'] != third['log_predictive_lower']
    assert work['predictive_certificate_calls'] == 4
    assert work['predictive_certificate_cache_hits'] == 1
    assert work['predictive_unique_certificates'] == 3


def test_nonlinear_certificate_covers_all_retry_cells_using_validation_counts():
    training = rows(detour=('RECOVERY',)*128, retry=('DELIVERY',)*384)
    validation = rows(detour=('DELIVERY',)*32+('RECOVERY',)*32, retry=('LOST',)*64)
    proof = core.certificate(training, validation, case(), 'risk', 'DETOUR_RETURN', 'DETOUR_RETRY')
    assert proof['partitions'] == len(proof['leaves']) == 32
    assert proof['validation_counts'] == {'D_REC': {'RECOVERY': 32, 'OTHER': 32},
                                         'R': {'DELIVERY': 0, 'LOST': 64}}
    assert proof['embedded_counts'][prior.OPERATORS[2]] == {'DELIVERY': 0, 'LOST': 64}
    assert [leaf['retry_interval'] for leaf in proof['leaves']] == [
        [F(index, 32), F(index+1, 32)] for index in range(32)]
    endpoint = 1 if proof['retry_slope'] >= 0 else 0
    assert all(leaf['gap_endpoint'] == leaf['retry_interval'][endpoint] for leaf in proof['leaves'])
    finite = [leaf['log_bad_likelihood_upper'] for leaf in proof['leaves']
              if leaf['log_bad_likelihood_upper'] is not None]
    assert proof['log_bad_likelihood_upper'] == max(finite)


def test_original_policies_and_all_comparison_conjunctions_are_preserved():
    queries = {'reward': {'policy': 'WAIT'}, 'goal': {'policy': 'SHORT'}, 'risk': {'policy': 'SHORT'}}
    result = core.certificates(rows(), rows(), case(), queries)
    assert {name: decision['policy'] for name, decision in result['queries'].items()} == {
        name: decision['policy'] for name, decision in queries.items()}
    assert result['queries']['reward'] == {'policy': 'WAIT', 'certified': True,
                                          'kind': 'known_nonnegative_cost'}
    assert len(result['comparison_records']) == 6
    for query in ('goal', 'risk'):
        decision = result['queries'][query]
        assert len(decision['comparisons']) == 3
        assert decision['certified'] == all(row['certified'] for row in decision['comparisons'])
    assert result['all_ready'] == all(row['certified'] for row in result['queries'].values())
