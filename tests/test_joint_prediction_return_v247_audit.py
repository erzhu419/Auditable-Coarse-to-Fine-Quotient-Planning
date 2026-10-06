from collections import Counter
from copy import deepcopy
from fractions import Fraction as F
import gzip
import json

import pytest

from acfqp.science import joint_prediction_acquisition_v247 as producer
from scripts import audit_joint_prediction_return_v247 as audit


def profiles():
    retained = []
    with gzip.open(audit.PREFIX/'profiles_life_00.jsonl.gz', 'rt') as stream:
        for line in stream:
            retained.append(json.loads(line))
            if len(retained) == 6:
                return retained


def raw_counts(retained):
    return audit.prior.global_audit.embedded_counts(retained[1]['certificate']['projected_counts'])


def unresolved_plan():
    with gzip.open(audit.PREFIX/'records_life_00.jsonl.gz', 'rt') as stream:
        for line in stream:
            row, member = json.loads(line), audit.paid.empty()
            points = [(row['initial_plan'], None)]+[(batch['plan'], batch) for batch in row['batches']]
            for saved, batch in points:
                if batch is not None:
                    for category, count in batch['increments'].items():
                        member[batch['operator']][category] += count
                plan = audit.fractions(saved)
                if ((plan['utility_lower'] >= 2 or plan['goal_impossible'])
                        and not plan['query_ready'] and audit.paid.samples(member) < audit.CAP):
                    maximum = max(reference['profile_id'] for query in ('goal', 'risk')
                                  for reference in plan['query_evidence']['queries'][query]['comparisons'])
                    retained = []
                    with gzip.open(audit.PREFIX/'profiles_life_00.jsonl.gz', 'rt') as profiles_stream:
                        for profile in profiles_stream:
                            retained.append(json.loads(profile))
                            if len(retained) > maximum:
                                return member, plan, retained


def test_full_row_largest_remainder_is_rounded_before_coarsening():
    operator = 'DETOUR_PASS'
    row = dict(DELIVERY=128, LOST=128, RECOVERY=128)
    increments = audit.expected_increment(row, operator)
    assert increments == dict(DELIVERY=6, LOST=5, RECOVERY=5)
    raw = audit.paid.empty()
    raw[operator] = increments
    projected, _ = audit.evidence.named_projection('D_DEL', raw,
        {name: dict.fromkeys(categories, F(1, len(categories)))
         for name, categories in audit.ALPHABETS.items()})
    assert projected['D_DEL'] == dict(DELIVERY=6, OTHER=10)


def test_actual_fixed_cells_update_nu_and_retry_MLE_keep_free_rows():
    retained = profiles()
    proof, case = audit.fractions(retained[0]['certificate']), retained[0]['case']
    counts = raw_counts(retained)
    for operator in ('DETOUR_PASS', 'RECOVERY_RETRY'):
        for category, count in audit.expected_increment(counts[operator], operator).items():
            counts[operator][category] += count
    predicted = producer.predict(proof, case, counts)
    checks = []
    audit.audit_prediction(predicted, proof, case, counts, Counter(),
        lambda name, condition: checks.append((name, condition)))
    assert all(condition for _, condition in checks)
    assert len(predicted['leaf_bounds']) == 32
    finite = [row for row in predicted['leaf_bounds'] if row['log_bad_likelihood_upper'] is not None]
    for row in finite:
        old = proof['leaves'][row['index']]
        assert row['row_nus']['SHORT_PASS'] is None
        assert row['row_nus']['DETOUR_PASS'] == F(old['row_witnesses']['DETOUR_PASS']['nu'])+16
    assert any(row['retry_probability'] != proof['leaves'][row['index']]['retry_likelihood']['probability']
               for row in finite)


@pytest.mark.parametrize('profile_id', (4, 5))
def test_actual_convex_point_and_multiplier_rebuild_new_full_support(profile_id):
    retained = profiles()
    proof, case = audit.fractions(retained[profile_id]['certificate']), retained[profile_id]['case']
    counts = raw_counts(retained)
    for category, count in audit.expected_increment(counts['DETOUR_PASS'], 'DETOUR_PASS').items():
        counts['DETOUR_PASS'][category] += count
    before = deepcopy(proof)
    predicted, checks = producer.predict(proof, case, counts), []
    audit.audit_prediction(predicted, proof, case, counts, Counter(),
        lambda name, condition: checks.append((name, condition)))
    assert all(condition for _, condition in checks)
    assert predicted['engine'] == 'convex_tangent' and not predicted['leaf_bounds']
    assert predicted['fallback'] is None and proof == before


def test_all_current_goal_and_risk_profiles_materialize_before_independent_selection():
    member, saved, retained = unresolved_plan()
    plan = audit.materialize(saved, retained)
    choice = producer.choose(member, plan, audit.paid.samples(member), Counter())
    work, checks = Counter(), []
    independent = audit.choose('JOINT_PREDICTION', member, saved, retained, work, choice,
        lambda name, condition: checks.append((name, condition)))
    assert all(condition for _, condition in checks)
    assert independent == choice
    unfinished = sum(not proof['certified'] for query in ('goal', 'risk')
        for proof in plan['query_evidence']['queries'][query]['comparisons'])
    assert work['joint_prediction_current_comparison_evaluations'] == unfinished
    assert work['joint_prediction_candidate_comparison_evaluations'] == 3*unfinished


def test_independent_bound_detects_inward_aggregate_even_with_consistent_score():
    retained = profiles()
    proof, case = audit.fractions(retained[4]['certificate']), retained[4]['case']
    counts = raw_counts(retained)
    predicted = producer.predict(proof, case, counts)
    predicted['log_bad_likelihood_upper'] -= 1
    predicted['log_e_lower'] = predicted['log_mixture_lower']-predicted['log_bad_likelihood_upper']
    predicted['deficit'] = max(F(0), predicted['log_threshold_upper']-predicted['log_e_lower'])
    failures = []
    audit.audit_prediction(predicted, proof, case, counts, Counter(),
        lambda name, condition: failures.append(name) if not condition else None)
    assert 'prediction_complete_null_or_explicit_unrestricted_MLE_upper' in failures
