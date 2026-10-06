from copy import deepcopy

import pytest

from acfqp.science import convex_query_qualification_v241 as core

PAIRS = ((0, 42, 42), (0, 54, 54), (0, 58, 58),
         (1, 42, 42), (1, 44, 44), (1, 54, 54), (1, 56, 56),
         (2, 42, 42), (2, 44, 44), (2, 45, 47), (2, 54, 54), (2, 55, 55))
GLOBAL = (2, 44, 'ORACLE_GAP')
COUNTS = {'S': {'DELIVERY': 3, 'LOST': 2},
          'D_DEL': {'DELIVERY': 4, 'OTHER': 5},
          'D_FULL': {'DELIVERY': 4, 'RECOVERY': 2, 'LOST': 3},
          'D_REC': {'RECOVERY': 2, 'OTHER': 7}, 'R': {'DELIVERY': 4, 'LOST': 2}}
FAMILIES = {'S_D_DEL': ('S', 'D_DEL'), 'S_D_FULL': ('S', 'D_FULL'),
            'D_REC_R': ('D_REC', 'R'), 'D_FULL_R': ('D_FULL', 'R'),
            'D_DEL': ('D_DEL',), 'D_FULL': ('D_FULL',)}


def inputs():
    previous = []
    for life, balanced_index, gap_index in PAIRS:
        for index, arm in ((balanced_index, 'ORACLE_BALANCED'), (gap_index, 'ORACLE_GAP')):
            key = life, index, arm
            queries = {'reward': {'policy': 'WAIT', 'certified': True, 'kind': 'known_nonnegative_cost'}}
            for query in ('goal', 'risk'):
                comparisons = []
                for other in ('WAIT', 'SHORT', 'DETOUR_RETRY'):
                    family = ({'WAIT': 'D_DEL', 'SHORT': 'S_D_DEL', 'DETOUR_RETRY': 'D_FULL_R'} if query == 'goal'
                              else {'WAIT': 'D_FULL', 'SHORT': 'S_D_FULL', 'DETOUR_RETRY': 'D_REC_R'})[other]
                    chosen_other = 'DETOUR_RETRY' if index in (44, 47) else 'SHORT'
                    certified = not (key in core.ROSTER and query == 'risk' and other == chosen_other)
                    comparisons.append(dict(query=query, chosen='DETOUR_RETURN', other=other, family=family,
                        projected_counts={name: deepcopy(COUNTS[name]) for name in FAMILIES[family]},
                        threshold=960, regret_threshold='1/20', certified=certified,
                        status='certified' if certified else 'unknown', leaves=[]))
                queries[query] = dict(policy='DETOUR_RETURN', comparisons=comparisons,
                                      certified=all(row['certified'] for row in comparisons))
            previous.append(dict(life=life, index=index, arm=arm, kind='positive' if key == GLOBAL else 'failure',
                case=dict(context='B' if index < 54 else 'A', operating='low',
                          retry_cost='19/20' if index == 44 else '17/20'),
                identity=0, certificate_index=77, fees={'source_paid_samples': 4608}, queries=queries,
                query_ready=all(row['certified'] for row in queries.values()),
                unique_profile_calls=6, profile_cache_hits=0, model_seconds=0.25))
    lookup = {(row['life'], row['index'], row['arm']): row for row in previous}
    classifications = []
    for key in core.ROSTER:
        row = lookup[key]
        comparison = next(item for item in row['queries']['risk']['comparisons'] if not item['certified'])
        classification = {field: deepcopy(row[field]) for field in
                          ('life', 'index', 'arm', 'kind', 'case', 'identity', 'certificate_index', 'fees')}
        classification.update({field: deepcopy(comparison[field]) for field in
                               ('query', 'chosen', 'other', 'family', 'projected_counts')})
        classification['result'] = dict(family=comparison['family'], projected_counts=deepcopy(comparison['projected_counts']),
            threshold=960, regret_threshold='1/20',
            status='global_bad_null_excluded' if key == GLOBAL else 'admitted_bad_kernel',
            global_tangent={'certified': key == GLOBAL},
            repaired_witness={'gap': '50001/1000000', 'feasible': True, 'membership': {'exact_inside': key != GLOBAL}})
        classifications.append(classification)
    return previous, classifications


def test_fixed_nine_are_routed_and_other_135_comparisons_remain_exact():
    previous, classifications = inputs()
    before = deepcopy(previous)
    results = core.qualify(previous, classifications)
    assert previous == before
    replaced, reused, admitted = 0, 0, 0
    for old, row in zip(previous, results):
        assert row['v239_query_ready'] == old['query_ready']
        assert row['qualification_provenance']['v239_work'] == {field: old[field] for field in core.WORK_FIELDS}
        assert all(field not in row for field in core.WORK_FIELDS)
        for query in ('goal', 'risk'):
            for original, current in zip(old['queries'][query]['comparisons'], row['queries'][query]['comparisons']):
                if 'proof_reference' in current:
                    replaced += 1
                    proof = classifications[current['proof_reference']['record_index']]['result']
                    assert current['certified'] == (proof['status'] == 'global_bad_null_excluded'
                                                   and proof['global_tangent']['certified'])
                    if proof['status'] == 'admitted_bad_kernel':
                        admitted += 1
                        assert not current['certified'] and current['status'] == 'unknown'
                        assert current['admitted_witness'] == proof['repaired_witness']
                else:
                    reused += 1
                    assert current == original
    assert (replaced, reused, admitted) == (9, 135, 8)


@pytest.mark.parametrize('blocker_query', ('goal', 'risk'))
def test_one_new_comparison_never_bypasses_other_alternatives_or_queries(blocker_query):
    previous, classifications = inputs()
    target = next(row for row in previous if (row['life'], row['index'], row['arm']) == GLOBAL)
    target['queries'][blocker_query]['comparisons'][0]['certified'] = False
    target['queries'][blocker_query]['certified'] = False
    row = next(row for row in core.qualify(previous, classifications)
               if (row['life'], row['index'], row['arm']) == GLOBAL)
    assert not row['queries'][blocker_query]['certified'] and not row['query_ready']
    repaired = next(item for item in row['queries']['risk']['comparisons'] if 'proof_reference' in item)
    assert repaired['certified']
    assert all(row['queries'][query]['policy'] == target['queries'][query]['policy'] for query in target['queries'])


@pytest.mark.parametrize('mismatch', ('retry_cost', 'fees', 'projected_counts', 'result_counts'))
def test_rejects_a_proof_from_different_costs_or_projected_observations(mismatch):
    previous, classifications = inputs()
    wrong = classifications[5]
    if mismatch == 'retry_cost':
        wrong['case']['retry_cost'] = '17/20'
    elif mismatch == 'fees':
        wrong['fees']['source_paid_samples'] += 16
    elif mismatch == 'projected_counts':
        wrong['projected_counts']['D_REC']['RECOVERY'] += 1
    else:
        wrong['result']['projected_counts']['D_REC']['RECOVERY'] += 1
    with pytest.raises(ValueError):
        core.qualify(previous, classifications)
