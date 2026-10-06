"""Route the nine audited V240 proofs into the frozen V239 qualification.

This integration performs no likelihood optimization or old-certificate
evaluation.  It replaces the declared comparisons, preserves every other
comparison, and recomputes the complete query conjunctions.
"""
from copy import deepcopy
from fractions import Fraction as F

ROSTER = (
    (0, 58, 'ORACLE_BALANCED'), (0, 58, 'ORACLE_GAP'),
    (1, 56, 'ORACLE_BALANCED'), (1, 56, 'ORACLE_GAP'),
    (2, 44, 'ORACLE_BALANCED'), (2, 44, 'ORACLE_GAP'),
    (2, 47, 'ORACLE_GAP'),
    (2, 55, 'ORACLE_BALANCED'), (2, 55, 'ORACLE_GAP'),
)
ENGINE = 'V239_with_V240_fixed_comparisons'
PROOF_ARTIFACT = 'reports/convex_query_null_v240/records.json'
WORK_FIELDS = ('unique_profile_calls', 'profile_cache_hits', 'model_seconds')
POLICIES = ('WAIT', 'SHORT', 'DETOUR_RETURN', 'DETOUR_RETRY')


def _key(row):
    return row['life'], row['index'], row['arm']


def _replacement(previous, classification, record_index):
    result = classification['result']
    family = 'D_REC_R' if classification['index'] in (44, 47) else 'S_D_FULL'
    other = 'DETOUR_RETRY' if family == 'D_REC_R' else 'SHORT'
    if (classification['query'], classification['chosen'], classification['other'], classification['family']) != (
            'risk', 'DETOUR_RETURN', other, family):
        raise ValueError('the nine fixed risk directions and projections must be preserved')
    for field in ('case', 'identity', 'kind', 'certificate_index', 'fees'):
        if previous[field] != classification[field]:
            raise ValueError(f'V239/V240 {field} differs for the fixed comparison')
    query = previous['queries'][classification['query']]
    if query['policy'] != classification['chosen']:
        raise ValueError('V240 must prove the originally selected query policy')
    matching = [position for position, comparison in enumerate(query['comparisons'])
                if all(comparison[field] == classification[field]
                       for field in ('query', 'chosen', 'other', 'family'))]
    if len(matching) != 1:
        raise ValueError('each V240 proof must match exactly one original comparison')
    position = matching[0]
    original = query['comparisons'][position]
    if original['certified']:
        raise ValueError('V240 routes only the nine originally unresolved comparisons')
    if (original['projected_counts'] != classification['projected_counts']
            or result['projected_counts'] != classification['projected_counts']
            or result['family'] != family):
        raise ValueError('V240 must use exactly the same projected counts and region')
    if (original['threshold'] != 960 or result['threshold'] != 960
            or F(original['regret_threshold']) != F(1, 20)
            or F(result['regret_threshold']) != F(1, 20)):
        raise ValueError('the original threshold and regret region are fixed')
    classification_status = result['status']
    certified = (classification_status == 'global_bad_null_excluded'
                 and result['global_tangent']['certified'])
    field = ('result.global_tangent' if classification_status == 'global_bad_null_excluded' else
             'result.repaired_witness' if classification_status == 'admitted_bad_kernel' else 'result')
    comparison = {field: deepcopy(original[field]) for field in
                  ('query', 'chosen', 'other', 'family', 'projected_counts', 'threshold', 'regret_threshold')}
    comparison.update(classification_status=classification_status,
                      status='certified' if certified else 'unknown', certified=certified,
                      proof_reference=dict(artifact=PROOF_ARTIFACT, record_index=record_index, field=field))
    if classification_status == 'admitted_bad_kernel':
        comparison['admitted_witness'] = deepcopy(result['repaired_witness'])
    return position, comparison


def qualify(previous_records, classifications):
    """Return all 24 records with the fixed nine proofs and complete AND rules."""
    if len(previous_records) != 24 or len({_key(row) for row in previous_records}) != 24:
        raise ValueError('V241 retains the full unique 24-case qualification')
    if tuple(_key(row) for row in classifications) != ROSTER:
        raise ValueError('V241 uses exactly the nine audited V240 records in original order')
    previous = {_key(row): row for row in previous_records}
    replacements = {}
    for record_index, classification in enumerate(classifications):
        key = _key(classification)
        position, comparison = _replacement(previous[key], classification, record_index)
        replacements[key] = (position, comparison, record_index)
    results = []
    for record_index, original in enumerate(previous_records):
        row = deepcopy(original)
        row['v239_query_ready'] = original['query_ready']
        indexes = []
        if _key(row) in replacements:
            position, comparison, source_index = replacements[_key(row)]
            row['queries']['risk']['comparisons'][position] = comparison
            indexes.append(source_index)
        if row['queries']['reward']['policy'] != 'WAIT':
            raise ValueError('the original analytic reward policy is WAIT')
        for query in ('goal', 'risk'):
            decision = row['queries'][query]
            if (len(decision['comparisons']) != 3 or
                    {comparison['other'] for comparison in decision['comparisons']}
                    != set(POLICIES)-{decision['policy']}):
                raise ValueError('each query must retain all three distinct alternatives')
            decision['certified'] = all(comparison['certified'] for comparison in decision['comparisons'])
        row['query_ready'] = all(decision['certified'] for decision in row['queries'].values())
        row['qualification_provenance'] = dict(engine=ENGINE, v239_record_index=record_index,
            v240_record_indexes=indexes, reused_comparisons=6-len(indexes), replaced_comparisons=len(indexes),
            v239_work={field: row.pop(field) for field in WORK_FIELDS})
        results.append(row)
    return results
